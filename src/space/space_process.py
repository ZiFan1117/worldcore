# -*- coding: utf-8 -*-
"""AIOS 个人空间进程 —— ★ 人的地盘；★ 它出【画布（surface）】。

★ 作者令（逐字，2026-10-18）：
  ·「我们要实现的是【成像】和【surface】，按照我们的逻辑来实现，包括 space」
  ·「呈现和画布是说和画布 surface」（★ 合并的是【呈现＋画布】，★ 不是【呈现＋空间】）
  ·「个人空间下面是不是要有一套（布局）……这个应该有一套」⇒ ★ 布局【它自己给】
  ·「我需要多个画布，这是事实，而且是不同人的画布」

★★ 它是什么（本体 space 定义逐字）：
  「人的地盘（归属与激活状态）。一人一份、在册≠激活：登录只把当前人的空间置 active；
    布局/壁纸/偏好等细节【不进本体】。」

★★ 它干什么：
  ① 报个体 space/<user>（owner = human/<user>，state = active/inactive）
  ② 出【桌面画布】surface/desktop-<user>（★ 带 layout：摆放归它）
  ③ 收 world/ui/act（★ 人的动作，经本体转来）

★★ 它不是什么：不画像素、不合成、不裁决 —— 那些是【呈现】的事。
"""
import json
import os
import sys
import time

import zenoh

from desktop_frame import desktop_frame
from activity import ActivityMixin   # ★ 活动窗口（P8 事件流；C27 拆文件）
from lifecycle import LifecycleMixin   # ★ 生命周期（退出；C27 拆文件）
from scenes import save_scene   # ★ P3 场景文件化（C27 拆文件）

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "presentation"))
from window_frame import wrap_window  # noqa: E402
from confirm_window import ConfirmMixin  # noqa: E402
from space_util import act_context, surface_of  # noqa: E402


# ★★ 本体发的审批凭据（与计算机同一把钥匙）—— 收 world/exec 前必须验。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
from permit import verify, consume_via_ontology  # noqa: E402

T_NOTICE = "world/notice"
T_EVENT = "world/event"
T_ACT = "world/ui/act"
T_ASK = "world/ask"
T_REGISTER = "world/register"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"
T_QUERY = "world/query"
T_ASK_RESULT = "world/ask/result"
T_QUERY_RESULT = "world/query/result"


# ★★ 测试账号（作者令 2026-10-18：「先设定一个测试的用户名和密码吧，密码就是一个 0 就行」）

# ★★ 个人空间对外的三个动作（★ 登录入口 ＋ 布局；摆放归它）
ACTIONS = [
    {"action": "space.login",      "kind": "write", "why": "登录：验人、置空间 active、出桌面画布"},
    {"action": "space.set_layout", "kind": "write", "why": "改布局（摆放归个人空间）"},
    {"action": "space.get_layout", "kind": "read",  "why": "读布局"},
    # ★ 2026-10-19：注册时就预留「读桌面状态」动作
    {"action": "space.state",      "kind": "read",  "why": "读桌面状态（用户/状态/画布/窗口/成员）"},
]

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
# ★ 客画布上限：0 ＝ 不设上限（★ 作者更正：不许写死「只摆四张」）
MAX_GUESTS = int(os.environ.get("AIOS_GUESTS_MAX") or "0")
USER = os.environ.get("AIOS_USER") or "zhang"
STATE = os.environ.get("AIOS_SPACE_STATE") or "active"

ME = {"class": "space", "name": USER, "owner": USER, "state": STATE,
      "reporter": "world://space/" + USER}


def log(*a):
    print("[个人空间]", *a, flush=True)


class Space(ActivityMixin, LifecycleMixin, ConfirmMixin):
    def __init__(self, session):
        self.s = session
        self.surface_id = "surface/desktop-" + USER
        self.user = USER          # ★ 活动窗口用（activity.py 的 mixin）
        self.state = STATE
        self.n_members = 0
        # ★★ 摆放归个人空间：客画布（别的提供者给的 surface）⇒ surfaceId -> rect
        self.guests = {}
        self.ticket = ""          # ★ 登录拿到的票（点图标/关窗口时以「人」的身份向本体发请求）
        self.zoomed = {}          # ★ 窗口缩放状态：surface -> True(最大化)/False(还原)
        self.own = {}             # ★ 空间自己出的窗口：surface -> {"frame", "rect"}
        self.pending = {}         # ★ 已发请求：rid -> {"kind"}（回话到了再画窗口）
        self.events = []          # ★（P8）世界推来的事件（实时）
        self.activity_open = False  # ★ 活动窗口开着吗

    def _ask(self, action, params, tag=""):
        """★ 个人空间以【人】的身份向本体发请求：点击/关窗口都必须过本体（许可/凭证/记账）。"""
        rid = "sp-%s-%d" % (tag or "ask", int(time.time() * 1000))
        msg = {"id": rid, "action": action, "actor": "world://user/" + USER,
               "params": params or {}}
        if self.ticket:
            msg["ticket"] = self.ticket
        self.s.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        log("③ 向本体发 %s（id=%s）" % (action, rid))
        return rid

    def announce(self):
        self.s.put("world/appear", json.dumps(ME, ensure_ascii=False))
        log("① 个体：space/%s（owner=%s，%s）" % (ME["name"], ME["owner"], self.state))

    def register_actions(self):
        # ★★ 本体 on_register 要的五格
        for a in ACTIONS:
            self.s.put(T_REGISTER, json.dumps({
                "action": a["action"],
                "function": a["action"].split(".", 1)[-1],
                "registered_by": "space/" + USER,
                "registered_by_kind": "space",
                "required_roles": ["space"],
                "kind": a["kind"],
                "why": a["why"],
            }, ensure_ascii=False))
        log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))

    def on_exec(self, sample):
        try:
            d = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        # ★★ 只接【自己那一类】（本体广播 world/exec，带 route=注册者 kind）
        if d.get("route") and d.get("route") != "space":
            return
        rid, act, params = d.get("id"), d.get("action") or "", d.get("params") or {}
        _ok, _why = verify(d.get("permit"), act, params)
        if _ok:
            # ★ 一号一用的账在本体：只问一句（执行器不记账）
            _ok, _why = consume_via_ontology(self.s, d.get("permit"), act, params)
        if not _ok:
            log("④ 拒 %s（id=%s）⇒ 没有本体的许可：%s" % (act, rid, _why))
            self.s.put(T_RESULT, json.dumps({
                "id": rid, "action": act, "ok": False, "body": None, "by": "space/" + USER,
                "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % _why}, ensure_ascii=False))
            return
        ok, body = self.dispatch(act, params)
        self.s.put(T_RESULT, json.dumps({
            "id": rid, "action": act, "ok": ok, "body": body, "by": "space/" + USER,
        }, ensure_ascii=False))
        log("④ 执行 %s ⇒ ok=%s（%s）" % (act, ok, str(body)[:60].replace(chr(10), " ")))

    def dispatch(self, act, params):
        if act == "space.state":       # ★ 注册时预留的「读桌面状态」动作
            return True, {"user": USER, "state": self.state,
                          "surface": self.surface_id,
                          "guests": dict(self.guests),
                          "own": {k: (v.get("rect") if isinstance(v, dict) else None)
                                  for k, v in self.own.items()},
                          "n_members": self.n_members,
                          "has_ticket": bool(self.ticket),
                          "at": time.time()}
        if act == "object.retire":      # ★ 多态动作：路由到 space 的那一支
            subject = params.get("subject") or ""
            me = "space/" + USER
            if subject != me:
                return False, "不是我的对象（我只管 %s）：%s" % (me, subject)
            self.state = "closed"
            self.s.put("world/appear", json.dumps({
                "class": "space", "name": USER, "owner": USER, "state": "closed",
                "reporter": "world://space/" + USER}, ensure_ascii=False))
            return True, {"effect": "retired", "class": "space", "subject": me}
        if act == "space.login":
            # ★★★ 凭【票】进 —— ★ 空间【不碰密码】（★ 密码归本体；见 src/ontology/identity.py）。
            #    ★ 作者令（逐字）：「这个密码啥的是不是在本体空间中更合适呢？……
            #      当确定登录了以后，再给这个个人空间这块留个信息吧」
            #    ★ 学 OIDC：★ 认证中心（本体）发票；★ 资源方（空间）【只看票】。
            tk = params.get("ticket") or ""
            if tk:
                self.ticket = tk          # ★ 记下票：之后以人的身份点图标/关窗口
            who = params.get("user") or ""
            if not tk:
                log("③ 进空间被拒：没有票")
                return False, "进空间要票（★ 先 identity.authenticate）"
            if not who:
                # ★ 票里带 who；没明说就从票里取（★ 票是本体发的，本体判过）
                who = (params.get("_who") or "")
            log("③ 凭票进空间：ticket=%s…（user=%s）" % (tk[:10], who or "（从票取）"))

            self.s.put("world/appear", json.dumps({
                "class": "human", "name": who,
                "reporter": "world://space/" + USER,
                # ★★ 2026-10-18 修：★ human.last_seen 定义是 "integer  # UNIX 秒"（★ ontology.json 现取），
                #    ★ 原来传 ISO 字符串 ⇒ 本体拒（★ 现取报错：
                #    "last_seen: invalid literal for int() with base 10: '2026-10-18T17:19:35'"）。
                #    ★ 后果：★ 登录成功了但【人没成为个体】—— 静默失败，最坏的一类。
                "last_seen": int(time.time()),
            }, ensure_ascii=False))
            self.state = "active"
            self.s.put("world/appear", json.dumps({
                "class": "space", "name": USER, "owner": who, "state": "active",
                "reporter": "world://space/" + USER,
            }, ensure_ascii=False))
            self.draw()
            self.request_replay()   # ★ P8 掉线补推：登录后回放最近事件（经本体；activity.py）
            return True, "登录成功：human/%s 已报，space/%s ⇒ active，桌面画布已出" % (who, USER)
        if act == "space.set_layout":
            lay = params.get("layout") or {}
            if not lay:
                return False, "缺参数 layout"
            self.layout = lay
            self.draw()
            return True, "布局已改（%d 层），桌面画布重出" % len(lay.get("layers") or [])
        if act == "space.get_layout":
            return True, getattr(self, "layout", None) or {"layers": []}
        return False, "不认识的动作 %s" % act

    def _own_window_frame(self, sid, title, lines):
        """★ 空间自己的一扇窗（这台机器/能做什么）：统一窗口壳，内容＝几行字。"""
        comps = [{"id": "root", "component": "Column",
                  "children": ["o_%d" % i for i in range(len(lines))]}]
        for i, line in enumerate(lines):
            comps.append({"id": "o_%d" % i, "component": "Text", "text": line})
        return {"version": "v1.0", "name": title, "messages": [
            {"version": "v1.0", "createSurface": {"surfaceId": sid}},
            {"version": "v1.0", "updateComponents": {
                "surfaceId": sid, "components": wrap_window(title, comps, sid)}}]}

    def draw(self):
        extra = [{"surface": k, "rect": v} for k, v in self.guests.items()]
        extra += [{"surface": k, "rect": v["rect"]} for k, v in self.own.items()]
        f = desktop_frame(self.surface_id, USER, self.n_members, extra)
        n = len(f["messages"][1]["updateComponents"]["components"])
        save_scene(self.surface_id, f)
        self.s.put(T_NOTICE, json.dumps({
            "kind": "a2ui.frame",
            "by": "world://space/" + USER,
            "about": "桌面",
            "frame": f,
        }, ensure_ascii=False))
        for sid, w in self.own.items():
            self.s.put(T_NOTICE, json.dumps({
                "kind": "a2ui.frame", "by": "world://space/" + USER,
                "about": "空间窗口", "frame": w["frame"]}, ensure_ascii=False))
        log("② 出桌面画布 %s（%d 组件，layout %d 层，自有窗口 %d）"
            % (self.surface_id, n, len(f["layout"]["layers"]), len(self.own)))

    def on_act(self, sample):
        try:
            d = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        _a = d.get("action") or {}
        if isinstance(_a, dict) and isinstance(_a.get("event"), dict):
            name = _a["event"].get("name") or ""
        else:
            name = _a.get("name") or ""
        log("③ 人的动作：%s（comp=%s）" % (name, d.get("component")))
        if name == "space.login":
            # ★ 有人要登录 —— 是谁？★ 我这里是那个人的空间 ⇒ 报 human 并把空间置 active
            # ★★ 2026-10-19 修：原来这里写的 `act.get("params")` —— `act` 在这个函数里【不存在】
            #   （形参是 sample／局部叫 d）⇒ 一点登录就是 NameError，回调直接炸。
            _ev = _a.get("event") if isinstance(_a, dict) else None
            params = d.get("params") or ((_ev or {}).get("context") if isinstance(_ev, dict) else None) or {}
            who = params.get("user") or USER
            log("③ 登录请求 user=%s ⇒ 报 human/%s ＋ 空间 active" % (who, who))
            self.state = "active"
            self.s.put("world/appear", json.dumps({
                "class": "human", "name": who,
                "reporter": "world://space/" + USER,
                # ★ human.last_seen 是 integer（UNIX 秒）；原来传 ISO 字符串 ⇒ 本体拒。
                "last_seen": int(time.time()),
            }, ensure_ascii=False))
            self.s.put("world/appear", json.dumps({
                "class": "space", "name": USER, "owner": who, "state": "active",
                "reporter": "world://space/" + USER,
            }, ensure_ascii=False))
            self.draw()
        # ── ★ 2026-10-19：桌面图标与窗口按钮（★ 上下文取渲染器实际发的平铺形态）──
        ctx = act_context(_a)
        if name == "confirm.decide":
            # ★ 桌面弹窗上点「拒绝/允许一次/允许并委托」⇒ 以人的身份回本体 confirm.resolve（带票）
            cname = str(ctx.get("confirmation") or "")
            decision = str(ctx.get("decision") or "deny")
            sid = "space/confirm-" + USER
            self.own.pop(sid, None)
            self.pending_confirmation = None
            rid = self._ask("confirm.resolve",
                            {"name": cname, "decision": decision, "reason": "桌面弹窗确认"},
                            "cf")
            self.pending[rid] = {"kind": "confirm"}
            log("③ 桌面确认：%s => %s（经本体带票）" % (cname, decision))
            self.draw()
            return
        if name == "space.icon_clicked":
            icon = ctx.get("icon") or d.get("component") or ""
            if icon.endswith("_b"):
                icon = icon[:-2]
            log("③ 点了图标：%s" % icon)
            if icon == "ic_ontology":
                rid = "sp-q-%d" % int(time.time() * 1000)
                self.pending[rid] = {"kind": "overview"}
                self.s.put(T_QUERY, json.dumps({"id": rid, "kind": "overview"},
                                               ensure_ascii=False))
            elif icon == "ic_agent":
                self._ask("agent.launch", {}, "launch")
            elif icon == "ic_computer":
                rid = self._ask("sys.GetHostState", {}, "computer")
                self.pending[rid] = {"kind": "computer"}
            elif icon == "ic_actions":
                rid = "sp-q-%d" % int(time.time() * 1000)
                self.pending[rid] = {"kind": "actions"}
                self.s.put(T_QUERY, json.dumps({"id": rid, "kind": "actions"}, ensure_ascii=False))
            elif icon == "ic_activity":
                self.toggle_activity()
            elif icon == "ic_logout":
                self.logout()
        elif name == "space.window_close":
            sid = ctx.get("surface") or ""
            log("③ 关窗口：%s" % sid)
            if sid == "space/activity-" + USER:
                self.activity_open = False
            if sid:
                self.own.pop(sid, None)
                self.guests.pop(sid, None)
                if sid.startswith("agent/"):
                    self._ask("agent.close", {"surface": sid}, "ac")
                self._ask("presentation.retract_surface",
                          {"surface": sid, "reason": "窗口关闭"}, "retract")
                self.draw()
        elif name == "space.window_zoom":
            sid = ctx.get("surface") or ""
            if sid in self.own:
                r = self.own[sid]["rect"]
                self.own[sid]["rect"] = ([0, 0, 1220, 720] if r != [0, 0, 1220, 720]
                                         else [640, 40, 620, 300])
                self.draw()
            elif sid in self.guests:
                self.zoomed[sid] = not self.zoomed.get(sid)
                self.guests[sid] = ([0, 0, 1220, 720] if self.zoomed[sid]
                                    else [640, 40, 620, 500])
                self.draw()

    def on_ask_result(self, sample):
        """★ 空间发的请求有回话了（这台机器）⇒ 画一扇自己的窗口。"""
        try:
            d = json.loads(sample.payload.to_string())
        except Exception:
            return
        p = self.pending.pop(d.get("id") or "", None)
        if not p:
            return
        if not d.get("ok"):
            log("④ 回话失败：%s（%s）" % (p.get("kind"), d.get("why") or d.get("code")))
            return
        body = d.get("body")
        if p["kind"] == "confirm":
            log("④ 确认已回本体：%s" % str(body)[:120])
            return
        if p["kind"] == "computer":
            text = json.dumps(body, ensure_ascii=False)[:900] if isinstance(body, (dict, list)) \
                else str(body)[:900]
            sid = "space/tools-" + USER
            self.own[sid] = {"frame": self._own_window_frame(
                sid, "这台机器（经本体）", ["**sys.GetHostState 的结果**", text]),
                "rect": [640, 40, 620, 300]}
            log("② 这台机器窗口 ⇒ 出（经本体拿到的结果）")
            self.draw()

    def on_query_result(self, sample):
        """★ 查世界的回话（能做什么）⇒ 画一扇自己的窗口。"""
        try:
            d = json.loads(sample.payload.to_string())
        except Exception:
            return
        p = self.pending.pop(d.get("id") or "", None)
        if not p or not d.get("ok"):
            return
        if p["kind"] == "replay":
            n = self.apply_replay(d.get("data") or {})
            log("② 回放最近事件 %d 条（掉线补漏）" % n)
            return
        if p["kind"] == "overview":
            data = d.get("data") or {}
            c = data.get("counts") or {}
            if isinstance(c.get("individuals"), int):
                self.n_members = c["individuals"]   # ★ 桌面「世界：N 个成员」用真实个体数
            rows = data.get("ledger") or {}
            lines = [
                "**本体空间一眼看全**（world/query kind=overview）",
                "类 %s ／ 接口 %s ／ 关系 %s ／ 在册动作 %s ／ 注册动作 %s ／ 函数 %s"
                % (c.get("classes"), c.get("interfaces"), c.get("links"),
                   c.get("world_actions"), c.get("registry_actions"), c.get("functions")),
                "个体 %s 个" % c.get("individuals"),
                "账 %s 行；被拒码：%s" % (rows.get("rows"),
                                        "、".join("%s×%s" % (k, v) for k, v in
                                                 (rows.get("reject_codes") or {}).items()) or "（无）"),
                "最近事件：" + "；".join(
                    "%s %s" % (r.get("kind_of"), r.get("action") or r.get("kind") or "")
                    for r in (rows.get("last") or [])[-4:]),
            ]
            sid = "space/ontology-" + USER
            self.own[sid] = {"frame": self._own_window_frame(sid, "本体 · 一目了然", lines),
                             "rect": [600, 40, 660, 520]}
            log("② 本体窗口 ⇒ 出（%s 类／%s 动作）" % (c.get("classes"), c.get("world_actions")))
            self.draw()
            return
        data = d.get("data") or {}
        avail = data.get("available") or data.get("actions") or []
        sid = "space/actions-" + USER
        lines = ["**这个世界里在册的动作**（world/query kind=actions）",
                 "可用 %d 个：" % len(avail),
                 "、".join(str(x) for x in avail[:12])]
        self.own[sid] = {"frame": self._own_window_frame(sid, "能做什么", lines),
                         "rect": [640, 40, 620, 300]}
        log("② 能做什么窗口 ⇒ 出（%d 个动作）" % len(avail))
        self.draw()

    def on_envelope(self, sample):
        """★★ 别的提供者给的画布（经本体转来）⇒ ★ 摆放归个人空间：记下并重出桌面（带上它的层）。

        ★ 作者口径：「画面＝提供者的脸／摆放归个人空间」；呈现拿到新 layout 后才合成它。
        """
        try:
            env = json.loads(sample.payload.to_string())
        except Exception:
            return
        if env.get("kind") != "a2ui.frame":
            return
        by = env.get("by") or ""
        if by.startswith("world://space/"):
            return                      # ★ 自己的桌面，不摆
        to = env.get("to") or ""
        if to and to != "space:" + USER:
            return                      # ★ 写给别人的空间，不看
        frame = env.get("frame")
        sid = surface_of(frame) if isinstance(frame, dict) else None
        if not sid or sid == self.surface_id:
            return
        if sid not in self.guests and (MAX_GUESTS <= 0 or len(self.guests) < MAX_GUESTS):
            # ★ 摆放策略（归个人空间）：先给右栏；多张时级联偏移一点，免得完全叠死
            self.guests[sid] = [640, 40 + 16 * (len(self.guests) % 8), 620, 500]
            log("② 收到画布 %s（by=%s）⇒ ★ 摆进桌面（客画布 %d 张）" % (sid, by, len(self.guests)))
            self.draw()

    def on_frame(self, sample):
        """★ 收到别人给的 layout（★ 比如呈现的登录画布）⇒ 记住，★ 自己的画布不抢。"""
        try:
            d = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        if d.get("kind") == "confirm.request":
            # ★ 桌面上也要弹：guard 的确认请求 ⇒ 出一扇「guard 确认」窗口（点按钮回到本体）
            self.show_confirm(d.get("confirmation") or {})
            return
        if d.get("kind") != "a2ui.frame":
            return
        log("② 收到画布（by=%s）" % d.get("by"))


def main():
    log("① 连总线 %s …" % ENDPOINT)
    c = zenoh.Config()
    c.insert_json5("mode", chr(34) + "client" + chr(34))
    c.insert_json5("scouting/multicast/enabled", "false")
    c.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    s = zenoh.open(c)
    log("   连上了")
    sp = Space(s)
    sp.announce()
    sp.register_actions()
    # ★★ 作者令：登录界面先出来 ⇒ 桌面【等登录过了再出】（★ AIOS_SPACE_DRAW_AT_BOOT=1 可让它一启动就出）
    if os.environ.get("AIOS_SPACE_DRAW_AT_BOOT") == "1":
        sp.draw()
    else:
        log("★ 桌面画布【等登录】（★ space.login 通过后才出）")
    s.declare_subscriber(T_ACT, sp.on_act)
    s.declare_subscriber(T_NOTICE, sp.on_frame)
    s.declare_subscriber(T_EXEC, sp.on_exec)
    s.declare_subscriber("world/ui/frame", sp.on_envelope)   # ★ 别人给的画布 ⇒ 我摆
    s.declare_subscriber(T_ASK_RESULT, sp.on_ask_result)     # ★ 空间的请求回话（这台机器）
    s.declare_subscriber(T_QUERY_RESULT, sp.on_query_result) # ★ 查世界的回话（能做什么）
    s.declare_subscriber(T_EVENT, sp.on_event)               # ★（P8）世界推来的事件（实时）
    log("④ 订 %s ＋ %s ＋ %s ＋ world/ui/frame ＋ 回话" % (T_ACT, T_NOTICE, T_EXEC))
    log("★ 个人空间起来了 —— 等登录 ＋ 收人的动作（★ 桌面画布登录后才出）")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    main()
