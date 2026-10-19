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

# ★★ 本体发的审批凭据（与计算机同一把钥匙）—— 收 world/exec 前必须验。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
from permit import verify, consume_via_ontology  # noqa: E402

T_NOTICE = "world/notice"
T_ACT = "world/ui/act"
T_ASK = "world/ask"
T_REGISTER = "world/register"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"

# ★★ 测试账号（作者令 2026-10-18：「先设定一个测试的用户名和密码吧，密码就是一个 0 就行」）

# ★★ 个人空间对外的三个动作（★ 登录入口 ＋ 布局；摆放归它）
ACTIONS = [
    {"action": "space.login",      "kind": "write", "why": "登录：验人、置空间 active、出桌面画布"},
    {"action": "space.set_layout", "kind": "write", "why": "改布局（摆放归个人空间）"},
    {"action": "space.get_layout", "kind": "read",  "why": "读布局"},
]

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
# ★ 客画布上限：0 ＝ 不设上限（★ 作者更正：不许写死「只摆四张」）
MAX_GUESTS = int(os.environ.get("AIOS_GUESTS_MAX") or "0")
USER = os.environ.get("AIOS_USER") or "zhang"
STATE = os.environ.get("AIOS_SPACE_STATE") or "active"

ME = {"class": "space", "name": USER, "owner": USER, "state": STATE}


def log(*a):
    print("[个人空间]", *a, flush=True)


class Space:
    def __init__(self, session):
        self.s = session
        self.surface_id = "surface/desktop-" + USER
        self.state = STATE
        self.n_members = 0
        # ★★ 摆放归个人空间：客画布（别的提供者给的 surface）⇒ surfaceId -> rect
        self.guests = {}

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
                "error": "没有本体的许可（凭据校验不过）：%s" % _why}, ensure_ascii=False))
            return
        ok, body = self.dispatch(act, params)
        self.s.put(T_RESULT, json.dumps({
            "id": rid, "action": act, "ok": ok, "body": body, "by": "space/" + USER,
        }, ensure_ascii=False))
        log("④ 执行 %s ⇒ ok=%s（%s）" % (act, ok, str(body)[:60].replace(chr(10), " ")))

    def dispatch(self, act, params):
        if act == "space.login":
            # ★★★ 凭【票】进 —— ★ 空间【不碰密码】（★ 密码归本体；见 src/ontology/identity.py）。
            #    ★ 作者令（逐字）：「这个密码啥的是不是在本体空间中更合适呢？……
            #      当确定登录了以后，再给这个个人空间这块留个信息吧」
            #    ★ 学 OIDC：★ 认证中心（本体）发票；★ 资源方（空间）【只看票】。
            tk = params.get("ticket") or ""
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
                # ★★ 2026-10-18 修：★ human.last_seen 定义是 "integer  # UNIX 秒"（★ ontology.json 现取），
                #    ★ 原来传 ISO 字符串 ⇒ 本体拒（★ 现取报错：
                #    "last_seen: invalid literal for int() with base 10: '2026-10-18T17:19:35'"）。
                #    ★ 后果：★ 登录成功了但【人没成为个体】—— 静默失败，最坏的一类。
                "last_seen": int(time.time()),
            }, ensure_ascii=False))
            self.state = "active"
            self.s.put("world/appear", json.dumps({
                "class": "space", "name": USER, "owner": who, "state": "active",
            }, ensure_ascii=False))
            self.draw()
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

    def draw(self):
        extra = [{"surface": k, "rect": v} for k, v in self.guests.items()]
        f = desktop_frame(self.surface_id, USER, self.n_members, extra)
        n = len(f["messages"][1]["updateComponents"]["components"])
        self.s.put(T_NOTICE, json.dumps({
            "kind": "a2ui.frame",
            "by": "world://space/" + USER,
            "about": "桌面",
            "frame": f,
        }, ensure_ascii=False))
        log("② 出桌面画布 %s（%d 组件，layout %d 层）"
            % (self.surface_id, n, len(f["layout"]["layers"])))

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
                # ★ human.last_seen 是 integer（UNIX 秒）；原来传 ISO 字符串 ⇒ 本体拒。
                "last_seen": int(time.time()),
            }, ensure_ascii=False))
            self.s.put("world/appear", json.dumps({
                "class": "space", "name": USER, "owner": who, "state": "active",
            }, ensure_ascii=False))
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
        sid = _surface_of(frame) if isinstance(frame, dict) else None
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
        if d.get("kind") != "a2ui.frame":
            return
        log("② 收到画布（by=%s）" % d.get("by"))


def _surface_of(frame):
    """★ 从一帧 A2UI 里取 surfaceId（同呈现的取法）。"""
    for m in (frame.get("messages") or []):
        cs = m.get("createSurface") or m.get("updateComponents") or {}
        if cs.get("surfaceId"):
            return cs["surfaceId"]
    return None


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
    log("④ 订 %s ＋ %s ＋ %s ＋ world/ui/frame" % (T_ACT, T_NOTICE, T_EXEC))
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
