# -*- coding: utf-8 -*-
"""★★ 真 agent —— ★ 模型在环里：★ 它【自己决定】做什么、★ 自己决定画什么。

★ 作者令（逐字）：「我现在就是要一个智能体，然后让他渲染界面用 A2UI」「而且是要经过我的本体」
「我现在需要把这模型填进去」

★ 一轮四步（★ 每步都过本体，★ 一步都不绕过）：
  ① 问本体：★ `world/query` ⇒ 「世界有什么」（类／个体数／动作清单）
  ② 问模型：★ 「看着这个世界，你下一步要做什么？」⇒ 返回 `{"action": ..., "params": {...}}`
  ③ 做事：★ `world/ask` ⇒ 本体 ⇒ 计算机 ⇒ 结果
  ④ 问模型：★ 「结果是这样，画成 A2UI」⇒ 返回组件 JSON ⇒ `world/notice` ⇒ 本体 ⇒ GUI

★ 安全：★ 模型【只能】从【本体给的动作清单】里挑 ⇒ 挑了不在册的 ⇒ 本体拒（★ 有实测）。
★ 它不执行任何命令（★ 计算机执行）、不判许可（★ 本体判）、不自己发帧（★ 经 world/notice）。
"""

import datetime
import json
import os
import sys
import time
import urllib.request
import uuid

import zenoh

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_SRC = os.path.dirname(_HERE)
for _p in (os.path.join(_SRC, "ontology"), os.path.join(_SRC, "presentation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from provider_auth import open_signed_session  # noqa: E402
from gate import permit  # noqa: E402  ★ agent 也是执行者：窗口动作要验本体凭证
from window_frame import wrap_window  # noqa: E402  ★ 统一窗口壳
from agent_status import status as _status, guide_ack_frame as _guide_ack_frame  # noqa: E402
from agent_status import launch_frame as _launch_frame  # noqa: E402
from agent_chat import ask_chat as _ask_chat, chat_reply as _chat_reply  # noqa: E402
from agent_workspace import step as _step_ev, workspace as _workspace  # noqa: E402
from agent_register import register as _register  # noqa: E402
ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
NAME = os.environ.get("AIOS_AGENT_NAME", "dsh")
DID = os.environ.get("AIOS_AGENT_DID", "did:aios:agent:" + NAME)
ROUND = int(os.environ.get("AIOS_AGENT_ROUND", "45"))
LLM_URL = os.environ.get("AIOS_LLM_URL", "https://api.deepseek.com/chat/completions")
LLM_MODEL = os.environ.get("AIOS_LLM_MODEL", "deepseek-chat")
LLM_KEY = os.environ.get("AIOS_LLM_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
T_APPEAR = "world/appear"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"
T_NOTICE = "world/notice"
T_EVENT = "world/event"
T_EXEC = "world/exec"
T_EXEC_RESULT = "world/exec/result"   # ★ ask 的回话要回本体，本体再回请求方
T_REGISTER = "world/register"
def log(*a):
    print("[agent/llm]", *a, flush=True)
def ask_llm(system, user, max_tokens=900):
    """★ 调模型。★ 只认 JSON 回来。"""
    if not LLM_KEY:
        return None, "没有 AIOS_LLM_KEY"
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(LLM_URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + LLM_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        txt = data["choices"][0]["message"]["content"]
        return json.loads(txt), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:200])
HB = os.environ.get("AIOS_AGENT_HB", "/run/aios/agent-heartbeat.json")
class Agent:
    def __init__(self, session):
        self.s = session
        self.ask_results = {}
        self.query_results = {}
        self.launched = False      # ★ 窗口是否已打开（点图标经本体批准后才置 True）
        self.recent_actions = []   # ★ 最近挑过的动作（给模型看，促使换着来）
        self.events = []           # ★（P8）世界推来的事件（最近 30 条）
        self.guide = ""          # ★ 人通过控制台给的引导（经本体到 agent）
        self.chat_log = []       # ★ web 对话记录（仅进程内存；不落账）
        self.steps = []          # ★ Agent 工作台：观察/计划/动作/渲染步骤
        self.hb_path = HB          # ★（P7）进程可观测：心跳文件
        self.started_at = time.time()
        self.round = 0           # ★ 最近一轮（status 用，不被心跳覆盖）
        self._write_heartbeat()
    def _write_heartbeat(self, extra=None):
        """★（P7）把「agent 进程还活着/在做什么」写到一个可读文件（给人/浏览器看）。"""
        try:
            os.makedirs(os.path.dirname(self.hb_path) or ".", exist_ok=True)
            hb = {
                "pid": os.getpid(),
                "name": NAME,
                "started_at": datetime.datetime.fromtimestamp(self.started_at).astimezone()
                .isoformat(timespec="seconds"),
                "last_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                "events": len(self.events),
                "launched": self.launched,
            }
            if extra:
                hb.update(extra)
            with open(self.hb_path, "w", encoding="utf-8") as f:
                json.dump(hb, f, ensure_ascii=False)
        except Exception as e:
            log("⚠ 心跳写失败：%s" % e)
    def appear(self):
        self.s.put(T_APPEAR, json.dumps({
            "class": "agent", "name": NAME, "did": DID,
            "reporter": "world://agent/" + NAME,
            "manifest": "src/agent/agent_llm.py（模型驱动；★ 全走本体）", "state": "running"}))
        log("① 发 appear：agent/%s" % NAME)
    def query(self, **kw):
        rid = "l-" + uuid.uuid4().hex[:8]
        kw["id"] = rid
        kw.setdefault("actor", "world://agent/" + NAME)   # ★ 读闸要核身份
        self.s.put(T_QUERY, json.dumps(kw, ensure_ascii=False))
        for _ in range(100):
            if rid in self.query_results:
                return self.query_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "查询超时"}
    def act(self, action, params=None, timeout=25):
        rid = "l-" + uuid.uuid4().hex[:8]
        self.s.put(T_ASK, json.dumps({
            "id": rid, "action": action, "actor": "world://agent/" + NAME,
            "params": params or {}}, ensure_ascii=False))
        for _ in range(int(timeout * 10)):
            if rid in self.ask_results:
                return self.ask_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "动作超时"}
    def screen_state(self):
        """★ 问界面「现在屏上有什么」——★ 经本体问呈现与空间（不用截图）。
        ★ 作者口径：「如果 A 想知道界面上有哪些东西，可以直接请求这个界面、界面返回现在的状态给他」。
        ★ 返回 {"surfaces": …, "layout": …}；被拒就把原因带回来（不假装知道）。
        """
        r = self.act("presentation.state", {}, timeout=8)     # ★ 界面注册时预留的读状态动作
        if not r.get("ok"):
            r = self.act("presentation.list_surfaces", {}, timeout=8)   # 兼容旧提供者
        if not r.get("ok"):
            # ★ 被拒就把原因带回来（不假装知道）
            return {"surfaces": {"why": r.get("why") or r.get("code")}, "layout": None}
        b = r.get("body") or {}
        return {"surfaces": {"count": b.get("count"), "surfaces": b.get("surfaces")},
                "layout": b.get("layout"), "screen": b.get("screen")}
    def _cursor_path(self):
        d = os.environ.get("AIOS_CURSOR_DIR", "/var/lib/aios/cursors")
        return os.path.join(d, "agent-dsh.json")
    def _read_cursor(self):
        try:
            with open(self._cursor_path(), encoding="utf-8") as f:
                return json.load(f).get("cursor")
        except Exception:
            return None

    def _write_cursor(self, cur):
        if not cur:
            return
        try:
            p = self._cursor_path()
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"cursor": cur}, f, ensure_ascii=False)
        except Exception:
            pass

    def _remember_dict(self, e):
        """★ 去重后记一条（实时推与回放可能重复）。"""
        ev = {k: e.get(k) for k in
              ("at", "kind_of", "action", "actor", "ok", "code", "space")}
        key = (ev.get("at"), ev.get("kind_of"), ev.get("action"), ev.get("actor"))
        if any((x.get("at"), x.get("kind_of"), x.get("action"), x.get("actor")) == key
               for x in self.events[-20:]):
            return False
        self.events.append(ev)
        self.events = self.events[-30:]
        self._write_cursor(ev.get("at"))
        self._write_heartbeat()
        return True

    def _remember_event(self, sample):
        """★（P8）订阅 world/event：把世界正在发生的事记下来（给规划上下文用）。"""
        try:
            e = json.loads(sample.payload.to_string())
        except Exception:
            return
        self._remember_dict(e)

    def recent_events(self, n=8):
        return self.events[-n:]

    def notice(self, frame, about):
        self.s.put(T_NOTICE, json.dumps({
            "kind": "a2ui.frame", "by": "world://agent/" + NAME,
            "about": about, "frame": frame}, ensure_ascii=False))

    def status(self):
        return _status(self, NAME, DID)

    def guide_ack_frame(self):
        return _guide_ack_frame(self, build_frame)

    def _chat_ask(self, system, history):
        return _ask_chat(system, history, LLM_URL, LLM_KEY, LLM_MODEL)

    def chat_reply(self, message):
        return _chat_reply(self, message, self._chat_ask)

    def _step(self, kind, **kw):
        return _step_ev(self, kind, **kw)

    def workspace(self):
        return _workspace(self, _status, NAME, DID)

    def register(self):
        _register(self.s, NAME, T_REGISTER)
        log("① 注册应用动作：launch／close／state／guide／chat／workspace（route=agent）")

    def build_launch_frame(self):
        return _launch_frame(build_frame)

SYS_PLAN = (
    "你是 worldcore 世界里的【机器之眼】—— 一台 openSUSE 机器上的 agent。\n"
    "你的使命：★ 每轮【查一件对人有用的系统状态】，★ 并把它讲清楚。\n"
    "例：内存够不够、磁盘满不满、服务有没有挂、进程有没有失控。\n"
    "★ 你【不执行命令】—— 只能通过【世界】做事：从 available_actions 里挑一个。\n"
    "★ available_actions 是【完整且已核实】的清单（本机真能跑的）；清单外的不要挑。\n"
    "★ 只读动作（Get*／List*）随时可做；变更类会被人确认拦下。\n"
    "★ screen 是【此刻屏上有什么】（surfaces／layout，来自呈现与空间，经本体）；可据此决定帮人做什么。\n"
    "★ 文件相关：用 file.stat／file.list／file.read_text（只读）问世界，不要自己绕开世界读盘。\n"
    "★ 要时间用 clock.now（世界时间，带时区/单调秒/开机 id）；看网络用 network.list／network.state。\n"
    "★ 要看世界快照用 recovery.list／recovery.state（只读；快照是恢复边界）。\n"
    "★ 硬规则：每轮先从这些只读动作里挑一个【没挑过】的：file.list、file.stat、file.read_text、clock.now、recovery.list；\n"
    "  只有它们都不可用/都挑过了，才回头挑 sys.*。\n"
    "  （file.* 的 path 必须在白名单根里：/var/lib/aios、/root/aios、/etc/aios；别用 /。）\n"
    "★ 上下文里的 recent_actions 是你最近做过的；尽量换一个没做过的（优先 file.*／clock.now／recovery.*／network.*）。\n"
    "★ 别每轮都挑同一个：换着查不同的面。\n"
    "★ 严格输出 JSON：{\"action\": \"动作名\", \"params\": {…}, \"why\": \"一句话\"}\n"
    "★ 实在没有可用动作时，输出 {\"action\": \"\"}。"
)

SYS_DRAW = (
    "你是 worldcore 世界的界面作者。给你【世界状态】和【刚做的那件事的结果】，\n"
    "请输出一帧 A2UI v1.0 的【组件数组】—— 只输出数组本身，不要外层包裹。\n"
    "可用组件（只许这些，名字逐字）：\n"
    "· Text(text) —— 支持 **粗体**\n"
    "· Column(children)／Row(children)／List(children) —— children 是【id 字符串数组】\n"
    "· Card(child) —— child 是【一个 id 字符串】\n"
    "· Divider\n"
    "· Button(child) —— ★ child 必须是【某个 Text 组件的 id】，Button 自己不写文字\n"
    "· Icon(name)\n"
    "★★ 铁律（不合就不发）：children／child 里只许写【组件的 id 字符串】，"
    "绝不许把组件对象内联进去；Button 必须写成 "
    "{\"id\":\"…\",\"component\":\"Button\",\"child\":\"<某个Text的id>\"}。\n"
    "★ 第一个组件必须是 {\"id\":\"root\",\"component\":\"Column\",\"children\":[…]}\n"
    "★ 每个组件 id 唯一。★ 最多 15 个组件。\n"
    "★ 严格输出 JSON：{\"components\": [...]}"
)

def _frame_problems(frame):
    """★ 发之前自己按 A2UI 目录核一遍（与呈现同一份 frame_schema）——不合就不发。

    ★ 核不了（目录件/模块不在）⇒ 也算问题 ⇒ 不发：★ 宁可不画，也不发「不知道合不合」的帧。
    """
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(here), "presentation"))
        import frame_schema  # noqa: E402
        return frame_schema.validate_frame(frame)
    except Exception as e:
        return ["核不了帧（%s: %s）" % (type(e).__name__, str(e)[:120])]

def build_frame(comps):
    """★ 把内容组件包成一帧：surface ＝ agent/<名字>；★ 统一套【窗口壳】（标题栏＋缩放/关闭）。"""
    surface = "agent/%s" % NAME
    comps = wrap_window("智能体 · " + NAME, list(comps), surface)
    return {"version": "v1.0",
            "name": "模型画的界面（★ agent/%s 经本体）" % NAME,
            "messages": [
                {"version": "v1.0", "createSurface": {
                    "surfaceId": surface,
                    "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
                    "sendDataModel": True}},
                {"version": "v1.0", "updateComponents": {
                    "surfaceId": surface, "components": comps}},
            ]}

def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    if not LLM_KEY:
        log("★★ 没有 AIOS_LLM_KEY ⇒ 起不来（★ 设环境变量再试）")
        return
    log("★ 模型：%s @ %s" % (LLM_MODEL, LLM_URL))
    a = Agent(session)

    def on_ask(m):
        d = json.loads(m.payload.to_string())
        a.ask_results[d.get("id")] = d

    def on_query(m):
        d = json.loads(m.payload.to_string())
        a.query_results[d.get("id")] = d

    session.declare_subscriber(T_ASK_RESULT, on_ask)
    session.declare_subscriber(T_QUERY_RESULT, on_query)
    time.sleep(1.5)
    a.appear()
    time.sleep(2.0)
    # ★ P8 补漏（2026-10-20）：启动时回放最近事件（掉线期间发生的事，进规划上下文）
    cur = a._read_cursor()
    boot = a.query(kind="events", limit=20, since=cur) if cur else a.query(kind="events", limit=20)
    for e in (boot.get("data") or {}).get("events") or []:
        a._remember_dict(e)
    data = boot.get("data") or {}
    a._write_cursor(data.get("cursor") or (a.events[-1].get("at") if a.events else None))
    log("① 回放最近事件 %d 条（掉线补漏）" % len(a.events))

    def on_exec(m):
        """★ 窗口动作（agent.launch／agent.close）：验本体凭证 ⇒ 开/关窗口。"""
        try:
            d = json.loads(m.payload.to_string())
        except Exception:
            return
        if d.get("route") and d.get("route") != "agent":
            return
        aid = d.get("action") or ""
        if aid not in ("agent.launch", "agent.close", "agent.state", "agent.guide", "agent.chat", "agent.workspace"):
            return
        params = d.get("params") or {}
        ok, why = permit.verify(d.get("permit"), aid, params)
        if ok:
            ok, why = permit.consume_via_ontology(session, d.get("permit"), aid, params)
        if not ok:
            log("★ 窗口动作 %s 没凭证/凭证不能用：%s" % (aid, why))
            session.put(T_EXEC_RESULT, json.dumps({
                "id": d.get("id"), "action": aid, "ok": False, "body": None,
                "by": "agent/" + NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        if aid == "agent.launch":
            a.launched = True
            a.notice(a.build_launch_frame(), "智能体窗口（启动）")
            log("★ 收到 agent.launch（凭证过）⇒ 出窗口")
            result = {"launched": True}
        elif aid == "agent.close":
            a.launched = False
            result = {"launched": False}
            log("★ 收到 agent.close ⇒ 停画（画布由呈现撤回，理由随账）")
        elif aid == "agent.state":
            result = a.status()
        elif aid == "agent.chat":
            result = a.chat_reply(params.get("message") or "")
        elif aid == "agent.workspace":
            result = a.workspace()
        else:
            ins = str(params.get("instruction") or "").strip()
            if not ins:
                session.put(T_EXEC_RESULT, json.dumps({
                    "id": d.get("id"), "action": aid, "ok": False, "body": None,
                    "by": "agent/" + NAME, "code": "INVALID_ARGS",
                    "error": "agent.guide 要 instruction"}, ensure_ascii=False))
                return
            a.guide = ins
            a._write_heartbeat({"phase": "guided", "guide": ins[:120]})
            a.notice(a.guide_ack_frame(), "引导（经本体回界面）")
            log("★ 收到 agent.guide ⇒ 下一轮按引导：%s" % ins[:80])
            result = a.status()
        session.put(T_EXEC_RESULT, json.dumps({
            "id": d.get("id"), "action": aid, "ok": True,
            "body": result, "by": "agent/" + NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    session.declare_subscriber(T_EVENT, a._remember_event)   # ★（P8）实时事件
    a.register()
    a._write_heartbeat({"phase": "started"})
    rnd = 0
    last_idle_hb = 0.0
    while True:
        if not a.launched:                 # ★ 没被点开之前不画（窗口由点击打开）
            now = time.time()
            if now - last_idle_hb >= 30.0:  # ★（P7）空闲也定时写心跳，别让 /agent 显旧
                a._write_heartbeat({"phase": "idle"})
                last_idle_hb = now
            time.sleep(1.0)
            continue
        rnd += 1
        a.round = rnd
        a._write_heartbeat({"round": rnd})
        log("———— 第 %d 轮 ————" % rnd)
        world = a.query(kind="world")
        acts = a.query(kind="actions")
        screen = a.screen_state()      # ★ 问界面：此刻屏上有什么（经本体，不用截图）
        log("① 问世界：ok=%s；看屏：surfaces=%s"
            % (world.get("ok"),
               str((screen.get("surfaces") or {}))[:120]))
        a._step("observe", round=rnd, world_ok=bool(world.get("ok")),
                screen_count=((screen.get("surfaces") or {}).get("count")))
        acts_data = acts.get("data") or {}
        # ★★★ 只把【本机可用】的动作给模型（★ 不截断！截断了它会以为清单不全而拒绝动手）
        avail = list(acts_data.get("available") or [])
        # ★ 2026-10-20（二期）：文件进程的只读动作也进清单 —— DSH 要「文件先问世界」
        _reg = acts_data.get("registry") or []
        for _a in ("file.stat", "file.list", "file.hash", "file.read_text", "fs.state",
                   "clock.now", "recovery.list", "recovery.state",
                   "network.list", "network.state"):
            if _a in _reg and _a not in avail:
                avail.append(_a)
        world_data = world.get("data") or {}
        ctx_obj = {
            "world": {
                "types": world_data.get("types"),
                "instances": world_data.get("instances"),
                "registry_count": world_data.get("registry"),
            },
            "available_actions": avail,
            "unsupported_count": len(acts_data.get("unsupported") or []),
            "screen": screen,          # ★ 屏上有什么（呈现/空间经本体答的）
            "activity": a.recent_events(8),   # ★（P8）世界最近发生的事（实时推来的）
            "recent_actions": a.recent_actions[-8:],  # ★ 最近做过的（别总重复）
            "guide": a.guide or None,
        }
        ctx = json.dumps(ctx_obj, ensure_ascii=False)
        plan, err = ask_llm(SYS_PLAN, ctx)
        if err:
            log("② 模型失手：%s" % err)
            time.sleep(ROUND)
            continue
        action = (plan or {}).get("action") or ""
        log("② 模型决定：%s  params=%s  why=%s" % (action, plan.get("params"), plan.get("why")))
        a._step("plan", round=rnd, action=action, params=plan.get("params"),
                why=plan.get("why"))
        result = None
        if action:
            result = a.act(action, plan.get("params") or {})
            log("③ 做了 %s ⇒ ok=%s" % (action, result.get("ok")))
            a.recent_actions.append({"action": action,
                                     "ok": bool((result or {}).get("ok"))})
            a.recent_actions = a.recent_actions[-30:]
            a._step("action", action=action, params=plan.get("params"),
                    ok=bool((result or {}).get("ok")),
                    body=str((result or {}).get("body") or (result or {}).get("error") or "")[:400])
        payload = json.dumps({"world": world.get("data"),
                              "did": action, "params": plan.get("params"),
                              "ok": (result or {}).get("ok"),
                              "body": str((result or {}).get("body") or (result or {}).get("error") or (result or {}).get("why") or "")[:600]},
                             ensure_ascii=False)[:6000]
        draw, err2 = ask_llm(SYS_DRAW, payload)
        if err2 or not isinstance(draw, dict) or not isinstance(draw.get("components"), list):
            log("④ 模型画不出：%s" % (err2 or "返回不是 components 数组"))
            time.sleep(ROUND)
            continue
        comps = draw["components"]
        frame = build_frame(comps)
        probs = _frame_problems(frame)
        if probs:
            log("④ 帧不合 A2UI 目录 ⇒ ★ 不发（不静默过滤）：%s" % "；".join(probs[:3]))
            # ★ 给模型一次【看见自己错在哪】的机会：把问题回给同一次画帧
            draw2, err3 = ask_llm(
                SYS_DRAW + "\n★★ 你上一次的画被拒，原因：" + "；".join(probs[:3]) +
                "\n严格按铁律重画一帧。", payload)
            if err3 or not isinstance(draw2, dict) or not isinstance(draw2.get("components"), list):
                log("④ 重画失败：%s ⇒ 本轮不发帧" % (err3 or "返回不是 components 数组"))
                time.sleep(ROUND)
                continue
            comps = draw2["components"]
            frame = build_frame(comps)
            probs = _frame_problems(frame)
            if probs:
                log("④ 重画仍不合目录 ⇒ 本轮不发帧：%s" % "；".join(probs[:3]))
                time.sleep(ROUND)
                continue
        a.notice(frame, "模型画的界面")
        a._step("render", components=len(comps))
        log("④ 发帧（★ 经本体 world/notice）：%d 个组件" % len(comps))
        time.sleep(ROUND)

if __name__ == "__main__":
    main()
