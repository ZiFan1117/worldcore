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

import json
import os
import sys
import time
import urllib.request
import uuid

import zenoh

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_HERE)
for _p in (os.path.join(_SRC, "ontology"), os.path.join(_SRC, "presentation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import permit  # noqa: E402  ★ agent 也是执行者：窗口动作要验本体凭证
from window_frame import wrap_window  # noqa: E402  ★ 统一窗口壳

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


class Agent:
    def __init__(self, session):
        self.s = session
        self.ask_results = {}
        self.query_results = {}
        self.launched = False      # ★ 窗口是否已打开（点图标经本体批准后才置 True）
        self.events = []           # ★（P8）世界推来的事件（最近 30 条）

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

    def register(self):
        """★ 谁启动谁注册：窗口动作由 agent 提供 ⇒ 本体把 agent.launch/close 转给我。"""
        for aid in ("agent.launch", "agent.close"):
            self.s.put(T_REGISTER, json.dumps({
                "action": aid,
                "function": aid.split(".", 1)[-1],
                "registered_by": "agent/" + NAME,
                "registered_by_kind": "agent",
                "required_roles": ["agent"],
                "kind": "invoke",
                "why": "应用窗口：谁启动谁注册",
            }, ensure_ascii=False))
        log("① 注册应用动作：agent.launch／agent.close（route=agent）")

    def build_launch_frame(self):
        """★ 启动时先出一张【静态窗口】（不用等模型）：标题栏＋一行说明。"""
        return build_frame([
            {"id": "root", "component": "Column", "children": ["a_title", "a_line"]},
            {"id": "a_title", "component": "Text", "text": "**智能体已启动**（经本体批准）"},
            {"id": "a_line", "component": "Text",
             "text": "我是 agent/" + NAME + "：每 45 秒看一次世界，结果画在这扇窗里。点右上角 × 关闭。"},
        ])


SYS_PLAN = (
    "你是 worldcore 世界里的【机器之眼】—— 一台 openSUSE 机器上的 agent。\n"
    "你的使命：★ 每轮【查一件对人有用的系统状态】，★ 并把它讲清楚。\n"
    "例：内存够不够、磁盘满不满、服务有没有挂、进程有没有失控。\n"
    "★ 你【不执行命令】—— 只能通过【世界】做事：从 available_actions 里挑一个。\n"
    "★ available_actions 是【完整且已核实】的清单（本机真能跑的）；清单外的不要挑。\n"
    "★ 只读动作（Get*／List*）随时可做；变更类会被人确认拦下。\n"
    "★ screen 是【此刻屏上有什么】（surfaces／layout，来自呈现与空间，经本体）；可据此决定帮人做什么。\n"
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
    session = zenoh.open(conf)
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
    boot = a.query(kind="events", limit=20)
    for e in (boot.get("data") or {}).get("events") or []:
        a._remember_dict(e)
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
        if aid not in ("agent.launch", "agent.close"):
            return
        params = d.get("params") or {}
        ok, why = permit.verify(d.get("permit"), aid, params)
        if ok:
            ok, why = permit.consume_via_ontology(session, d.get("permit"), aid, params)
        if not ok:
            log("★ 窗口动作 %s 没凭证/凭证不能用：%s" % (aid, why))
            return
        if aid == "agent.launch":
            a.launched = True
            a.notice(a.build_launch_frame(), "智能体窗口（启动）")
            log("★ 收到 agent.launch（凭证过）⇒ 出窗口")
        else:
            a.launched = False
            log("★ 收到 agent.close ⇒ 停画（画布由呈现撤回，理由随账）")

    session.declare_subscriber(T_EXEC, on_exec)
    session.declare_subscriber(T_EVENT, a._remember_event)   # ★（P8）实时事件
    a.register()
    rnd = 0
    while True:
        if not a.launched:                 # ★ 没被点开之前不画（窗口由点击打开）
            time.sleep(1.0)
            continue
        rnd += 1
        log("———— 第 %d 轮 ————" % rnd)
        world = a.query(kind="world")
        acts = a.query(kind="actions")
        screen = a.screen_state()      # ★ 问界面：此刻屏上有什么（经本体，不用截图）
        log("① 问世界：ok=%s；看屏：surfaces=%s"
            % (world.get("ok"),
               str((screen.get("surfaces") or {}))[:120]))
        acts_data = acts.get("data") or {}
        # ★★★ 只把【本机可用】的动作给模型（★ 不截断！截断了它会以为清单不全而拒绝动手）
        avail = acts_data.get("available") or []
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
        }
        ctx = json.dumps(ctx_obj, ensure_ascii=False)
        plan, err = ask_llm(SYS_PLAN, ctx)
        if err:
            log("② 模型失手：%s" % err)
            time.sleep(ROUND)
            continue
        action = (plan or {}).get("action") or ""
        log("② 模型决定：%s  params=%s  why=%s" % (action, plan.get("params"), plan.get("why")))
        result = None
        if action:
            result = a.act(action, plan.get("params") or {})
            log("③ 做了 %s ⇒ ok=%s" % (action, result.get("ok")))
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
        log("④ 发帧（★ 经本体 world/notice）：%d 个组件" % len(comps))
        time.sleep(ROUND)


if __name__ == "__main__":
    main()
