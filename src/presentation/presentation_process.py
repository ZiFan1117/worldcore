# -*- coding: utf-8 -*-
"""AIOS 呈现进程 —— ★ 呈现（presentation）＋ 画布（surface，内部表）。

★ 作者令（逐字，2026-10-18）：
  ·「呈现和画布要不合到一个进程里边吧……反正都是干呈现这件事儿，我想让你们合一合」
  ·「至于说这个注册的个体也可以有两个嘛」
  ·「在一个个体里头，这个画布又不可能无限的增长……但是我现在需要多个画布，这是事实，
     而且是不同人的画布」
  ·「我们只用 A2UI，不用 GTK」／「Python 多个桥不行」／「我们就用普通的 TCP 可以吗」

★★ 三个决定：
  ① **一个进程**：presentation 与 space 合在一起（★ 都是"给人看"这件事）。
  ② **两个个体**：presentation/<屏名> ＋ space/<用户名>（★ 每人一个 space 个体）。
  ③ **画布【瞬时】**：只走 show → retract，★ 不注册、★ 不累积、★ 换人就 retract。
      （提案逐字：「画布是瞬时的：不注册，只走 show → retract；新建/删除是常态。」）

★★ 分模块（C27：单文件 ≤ 500 行）：
  · login_frame.py   —— 登录画布（呈现出）
  · desktop_frame.py —— 桌面画布（space 出）
  · 本文件           —— 连总线／报个体／订阅／合成／TCP 桥

★★ 分工（文档四归属）：脸归提供者／摆放归个人空间／合成归呈现／口归接入（未做，呈现代）。
"""
import json
import os
import socket
import sys
import threading
import time

import zenoh

from login_frame import login_frame
from frame_schema import A2UI_COMPONENTS, A2UI_WHITELIST_FROM, validate_frame  # noqa: F401

# ★★ 本体发的审批凭据（与计算机同一把钥匙）—— 收 world/exec 前必须验。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
from permit import verify, consume_via_ontology  # noqa: E402

T_NOTICE = "world/notice"
T_ACT = "world/ui/act"
T_ASK = "world/ask"

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
SCREEN = os.environ.get("AIOS_SCREEN_NAME") or "screen0"
HOST = os.environ.get("AIOS_COMPUTER_NAME") or socket.gethostname()
LISTEN_HOST = os.environ.get("AIOS_RENDER_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("AIOS_RENDER_PORT", "7450"))
USERS = [u.strip() for u in (os.environ.get("AIOS_USERS") or "zhang").split(",") if u.strip()]
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"

# ★★ 呈现【对外的四个动作】—— 画布是内部表，但别人【通过动作】读它、改它。
#    「改」＝ show_surface 给一帧；同一 surfaceId ⇒ 覆盖。
ACTIONS = [
    {"action": "presentation.show_surface",    "kind": "write", "why": "给一帧 A2UI ⇒ 画布出现/更新"},
    {"action": "presentation.retract_surface", "kind": "write", "why": "撤下一张画布"},
    {"action": "presentation.list_surfaces",   "kind": "read",  "why": "查：此刻有哪几张（★ 作者点名要的）"},
    {"action": "presentation.get_surface",     "kind": "read",  "why": "查：某一张的画布内容"},
]


def log(*a):
    print("[呈现]", *a, flush=True)


# ★★ A2UI 目录白名单与整帧校验在 frame_schema.py（C27：一文件一块）；本文件只用它。
#    ★ 口径：「只借 A2UI 的目录白名单 ＋ 没相容目录就不发」；不合 ⇒ 整帧拒（不静默过滤）。


class Bridge:
    """★ 唯一的那一个桥：本机 TCP，一行一条 JSON。"""

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.conn, self.lock, self.srv = None, threading.Lock(), None
        self.on_act = None
        self.on_connect = None

    def start(self):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((self.host, self.port))
        self.srv.listen(4)
        log("★ 桥已开：%s:%d" % (self.host, self.port))
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            try:
                c, addr = self.srv.accept()
            except OSError:
                return
            log("★ 渲染器连上了（%s）" % (addr,))
            with self.lock:
                old, self.conn = self.conn, c
            if old:
                try:
                    old.close()
                except OSError:
                    pass
            # ★★ 渲染器重连 ⇒ 通知呈现【重推当前合成】（否则它屏上什么都没有）
            if self.on_connect:
                try:
                    self.on_connect()
                except Exception as e:
                    log("重推失败：%s" % e)
            threading.Thread(target=self._read, args=(c,), daemon=True).start()

    def _read(self, c):
        buf = b""
        while True:
            try:
                chunk = c.recv(65536)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except Exception:
                    continue
                if msg.get("t") == "act" and self.on_act:
                    self.on_act(msg)
        log("渲染器断开")

    def send(self, obj):
        line = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            if self.conn is None:
                return False
            try:
                self.conn.sendall(line)
                return True
            except OSError:
                try:
                    self.conn.close()
                except OSError:
                    pass
                self.conn = None
                return False


class Presentation:
    """★★ 一个进程，两个面。"""

    def __init__(self, session, bridge):
        self.s = session
        self.b = bridge
        self.b.on_act = self.on_act
        self.b.on_connect = self.compose   # ★ 渲染器一连上就重推
        self.lock = threading.Lock()
        self.shown = {}
        self.ticket_scope = []   # ★ 我这张票能看谁（★ 登录后填；★ 空＝只看公开）     # surfaceId -> frame（★ 瞬时：show 进、retract 出）
        self.layout = None  # ★ 布局【由空间给】，呈现只按它叠
        self.actives = {}   # user -> {"state": "active"/"inactive", "surface": id}

    # ── 报个体（★ 一个类：呈现；★ 画布不注册，瞬时）─────────────────
    def announce(self):
        self.s.put("world/appear", json.dumps({
            "class": "presentation", "name": SCREEN, "host": HOST,
            "state": "active", "compositor_kind": "flutter",
            "reporter": "world://presentation/" + SCREEN}, ensure_ascii=False))
        log("① 个体：presentation/%s（active／flutter）" % SCREEN)
        log("   ★ 画布【不报个体】—— 提案逐字：画布是瞬时的，不注册，只走 show → retract")

    # ── 登录画布（★ 呈现出；起来就甩）────────────────────────────
    def show_login(self):
        sid = "surface/login-" + SCREEN
        f = login_frame(sid, SCREEN)
        with self.lock:
            self.shown[sid] = f
            self.layout = f["layout"]
        log("② 甩出登录画布 %s（%d 组件）"
            % (sid, len(f["messages"][1]["updateComponents"]["components"])))
        self.compose()

    # ── 注册动作（★ 本体据此把 presentation.* 转给我）──────────────
    def register_actions(self):
        # ★★ 本体 on_register 要的五格：action / function / registered_by / registered_by_kind / required_roles
        #   （现取 ontology_process.py on_register：「missing = [k for k in (...) if not reg.get(k)]」）
        for a in ACTIONS:
            self.s.put("world/register", json.dumps({
                "action": a["action"],
                "function": a["action"].split(".", 1)[-1],
                "registered_by": "presentation/" + SCREEN,
                "registered_by_kind": "presentation",
                "required_roles": ["presentation"],
                "kind": a["kind"],
                "why": a["why"],
            }, ensure_ascii=False))
        log("① 注册动作 %d 个（★ 按本体五格）：%s"
            % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))

    # ── 执行（★ 别人经本体转过来的 presentation.*）───────────────
    def on_exec(self, sample):
        try:
            d = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        # ★★ 本体把动作【广播】到 world/exec，并带 route（= 注册者的 kind）——
        #    ★ 每个进程【只接自己那一类】，否则会互相抢（现取：呈现抢了 space.login）。
        if d.get("route") and d.get("route") != "presentation":
            return
        rid = d.get("id")
        act = d.get("action") or ""
        params = d.get("params") or {}
        _ok, _why = verify(d.get("permit"), act, params)
        if _ok:
            # ★ 一号一用的账在本体：只问一句（执行器不记账）
            _ok, _why = consume_via_ontology(self.s, d.get("permit"), act, params)
        if not _ok:
            log("④ 拒 %s（id=%s）⇒ 没有本体的许可：%s" % (act, rid, _why))
            self.s.put(T_RESULT, json.dumps({
                "id": rid, "action": act, "ok": False, "body": None, "by": "presentation/" + SCREEN,
                "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % _why}, ensure_ascii=False))
            return
        ok, body = self.dispatch(act, params)
        self.s.put(T_RESULT, json.dumps({
            "id": rid, "action": act, "ok": ok, "body": body,
            "by": "presentation/" + SCREEN,
        }, ensure_ascii=False))
        log("④ 执行 %s ⇒ ok=%s（%s）" % (act, ok, str(body)[:60].replace(chr(10), " ")))

    def dispatch(self, act, params):
        if act == "object.retire":      # ★ 多态动作：路由到 presentation 的那一支
            subject = params.get("subject") or ""
            me = "presentation/" + SCREEN
            if subject != me:
                return False, "不是我的对象（我只管 %s）：%s" % (me, subject)
            self.s.put("world/appear", json.dumps({
                "class": "presentation", "name": SCREEN, "host": HOST,
                "state": "locked", "compositor_kind": "flutter",
                "reporter": "world://presentation/" + SCREEN}, ensure_ascii=False))
            return True, {"effect": "retired", "class": "presentation", "subject": me}
        if act == "presentation.show_surface":
            sid = params.get("surface") or ""
            frame = params.get("frame") or {}
            if not sid or not frame:
                return False, "缺参数：surface 和 frame 都要给"
            bad = validate_frame(frame)
            if bad:
                log("④ 画布不合 A2UI 目录 ⇒ ★ 整帧拒（不静默过滤）：%s" % "；".join(bad[:3]))
                return False, "帧不合 A2UI 基本目录：%s" % "；".join(bad[:5])
            with self.lock:
                self.shown[sid] = frame
                if frame.get("layout"):
                    self.layout = frame["layout"]
            self.compose()
            return True, "已显示 %s（%d 字节）；此刻共 %d 张" % (
                sid, len(json.dumps(frame)), len(self.shown))
        if act == "presentation.retract_surface":
            sid = params.get("surface") or ""
            # ★★★ 判据 C10（凡清除必留证）：撤画布必须【写理由】，理由随结果回本体 ⇒ 进账。
            reason = (params.get("reason") or "").strip()
            if not reason:
                return False, "撤下画布要写理由（★ 凡清除必留证：params.reason 不能空）"
            with self.lock:
                had = self.shown.pop(sid, None) is not None
            self.compose()
            return had, ("已撤下 %s（理由：%s）" % (sid, reason) if had
                         else "本来就没有 %s（理由：%s）" % (sid, reason))
        if act == "presentation.list_surfaces":
            with self.lock:
                rows = [{"surface": k, "bytes": len(json.dumps(v)),
                         "name": v.get("name"), "role": v.get("role")}
                        for k, v in self.shown.items()]
            return True, {"count": len(rows), "surfaces": rows}
        if act == "presentation.get_surface":
            sid = params.get("surface") or ""
            with self.lock:
                f = self.shown.get(sid)
            return (f is not None), (f if f is not None else "没有 %s" % sid)
        return False, "不认识的动作 %s" % act

    # ── 收画布 ──────────────────────────────────────────────────
    def on_notice(self, smp):
        """★★ 收【本体转来的】画布 —— ★ 信封上带 `to`（谁该看）；★ 我们拿【自己的票】来对。
        ★ 作者裁（逐字）：「这不是有票吗？票不是决定了是给哪个人的吗？……谁登录进来，你就给谁看呀」
        """
        try:
            env = json.loads(smp.payload.to_string())
        except Exception:
            return
        if env.get("kind") != "a2ui.frame":
            return
        # ★ 票 ⇒ 我在替谁看（★ 没登录时为空 ⇒ 只收【公开】的）
        with self.lock:
            mine = self.ticket_scope
        to = env.get("to") or ""
        if to and to not in (mine or []):
            log("② 画布 %s 是给 %s 的，★ 我的票不含 ⇒ 不收" % (env.get("about"), to))
            return
        f = self._frame_of(env)
        if not f:
            return
        self._absorb(f, env)

    def _frame_of(self, env):
        """★ 从本体信封里取 frame（★ 本体不碰信纸，原样带过来）。"""
        f = env.get("frame")
        return f if isinstance(f, dict) else None

    def _absorb(self, f, env):
        """★★ 收下一张画布 ⇒ 合。★ 桌面画布来了就撤登录画布。

        ★★★ 判据 C24：不合 A2UI 基本目录的帧【整帧拒】—— ★ 不许静默过滤掉不认的元件。
        """
        bad = validate_frame(f)
        if bad:
            log("② 画布不合 A2UI 目录 ⇒ ★ 整帧拒（不静默过滤）：%s" % "；".join(bad[:3]))
            return
        sid = _surface_of(f)
        if not sid:
            return
        role = f.get("role") or ""
        with self.lock:
            if f.get("layout"):
                self.layout = f["layout"]
            self.shown[sid] = f
            login_sid = "surface/login-" + SCREEN
            if role == "desktop" and login_sid in self.shown and login_sid != sid:
                self.shown.pop(login_sid, None)
                log("★ 桌面画布到了 ⇒ 登录画布 %s 已 retract" % login_sid)
        log("② 收到画布 %s（role=%s，by=%s）⇒ 合" % (sid, role or "-", env.get("by") or "-"))
        self.compose()

    def compose(self):
        with self.lock:
            layout, shown = self.layout, dict(self.shown)
        layers = []
        for lay in ((layout or {}).get("layers") or []):
            sid = lay.get("surface")
            f = shown.get(sid)
            if f is None:
                continue
            layers.append({"surface": sid, "z": lay.get("z", 0), "rect": lay.get("rect"),
                           "active": lay.get("active", False), "modal": lay.get("modal", False),
                           "frame": f})
        if not layers and shown:
            sid, f = list(shown.items())[-1]
            layers = [{"surface": sid, "z": 0, "active": True, "frame": f}]
        layers.sort(key=lambda x: x["z"])
        self.b.send({"t": "layout", "layers": layers})
        log("   合成 %d 层 ⇒ 推给渲染器" % len(layers))

    # ── 人点了 ──────────────────────────────────────────────────

    # ── 本体回话（★ 拿到票 ⇒ 凭票进空间）──────────────────────────
    def on_ask_result(self, smp):
        """★★ 认过了（拿到票）⇒ ★ 用票去 space.login；★ 被拒就留脸。"""
        try:
            d = json.loads(smp.payload.to_string())
        except Exception:
            return
        if not d.get("ok"):
            return
        # ★★ 2026-10-18 修：body 不一定是 dict —— ★ 有的动作（如 space.login）
        #    返回【字符串】"登录成功：…" ⇒ 这里曾抛 AttributeError: 'str' object has no attribute 'get'，
        #    ★ 后果：★ 呈现回调炸了，★ 第二次点登录【毫无反应】（★ 现取日志 callback error）。
        b = d.get("body")
        if not isinstance(b, dict):
            return
        tk = b.get("ticket")
        if not tk:
            return
        log("③ 拿到票 %s…（who=%s）⇒ 凭票进空间" % (tk[:10], b.get("who")))
        with self.lock:
            self.ticket_scope = b.get("scope") or []   # ★ 票的 scope ⇒ 我能看谁
        log("③ 我的票能看：%s" % (self.ticket_scope,))
        self.s.put(T_ASK, json.dumps({
            "id": "space-" + str(int(time.time() * 1000)),
            "action": "space.login",
            "params": {"ticket": tk, "user": b.get("user") or ""},
            "actor": "world://surface/" + SCREEN,
        }, ensure_ascii=False))

    def on_act(self, msg):
        # ★★ A2UI Action 格式：{"event": {"name": ..., "context": {...}}}
        _a = msg.get("action") or {}
        if isinstance(_a, dict) and isinstance(_a.get("event"), dict):
            act = _a["event"].get("name") or ""
        else:
            act = _a.get("name") or ""
        if act == "presentation.login":
            # ★★★ 呈现【只出脸、只交凭据、只换脸】—— ★ 不验密码（★ 密码归本体）。
            #    ★ 作者令：「登录的这个是给个人那啥吗？当确定登录了以后，
            #      再给这个个人空间这块留个信息吧」
            #    ★ 学 OIDC：★ 呈现是 client；★ 把凭据交给 authorization endpoint（本体）；
            #      ★ 拿到票后，★ 再用票去 space.login。
            ctx = (_a.get("event") or {}).get("context") or _a.get("context") or {}
            user = ctx.get("user") or ""
            secret = ctx.get("pass")
            # ① 认人（★ 本体验，★ 呈现只转交）
            self.s.put(T_ASK, json.dumps({
                "id": "auth-" + str(int(time.time() * 1000)),
                "action": "identity.authenticate",
                "params": {"user": user, "secret": secret},
                "actor": "world://surface/" + SCREEN,
            }, ensure_ascii=False))
            log("③ 登录 ⇒ world/ask identity.authenticate（user=%s，★ 密码交本体）" % user)
            return

        log("③ 人的动作：%s（comp=%s）" % (act, msg.get("component")))
        # ★★ 2026-10-19：人的动作（点图标/窗口按钮）⇒ 转给【个人空间】处理（谁是桌面主人谁管）
        self.s.put(T_ACT, json.dumps(msg, ensure_ascii=False))


def _surface_of(frame):
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

    bridge = Bridge(LISTEN_HOST, LISTEN_PORT)
    bridge.start()
    p = Presentation(s, bridge)
    p.announce()
    p.register_actions()
    s.declare_subscriber("world/ui/frame", p.on_notice)   # ★ 只收【本体转来的】（★ 不直接抄广播）
    s.declare_subscriber(T_EXEC, p.on_exec)
    # ★★ 本体的回话（★ 认证拿到票后，凭票进空间）
    s.declare_subscriber("world/ask/result", p.on_ask_result)
    log("④ 订 %s ＋ %s" % (T_NOTICE, T_EXEC))
    p.show_login()
    log("★ 呈现起来了 —— 呈现（合成）＋ 画布（内部表，4 动作对外）")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    main()
