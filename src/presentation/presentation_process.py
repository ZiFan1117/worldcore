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
import threading
import time

import zenoh

from login_frame import login_frame

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
        self.shown = {}     # surfaceId -> frame（★ 瞬时：show 进、retract 出）
        self.layout = None  # ★ 布局【由空间给】，呈现只按它叠
        self.actives = {}   # user -> {"state": "active"/"inactive", "surface": id}

    # ── 报个体（★ 一个类：呈现；★ 画布不注册，瞬时）─────────────────
    def announce(self):
        self.s.put("world/appear", json.dumps({
            "class": "presentation", "name": SCREEN, "host": HOST,
            "state": "active", "compositor_kind": "flutter"}, ensure_ascii=False))
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
        ok, body = self.dispatch(act, params)
        self.s.put(T_RESULT, json.dumps({
            "id": rid, "action": act, "ok": ok, "body": body,
            "by": "presentation/" + SCREEN,
        }, ensure_ascii=False))
        log("④ 执行 %s ⇒ ok=%s（%s）" % (act, ok, str(body)[:60].replace(chr(10), " ")))

    def dispatch(self, act, params):
        if act == "presentation.show_surface":
            sid = params.get("surface") or ""
            frame = params.get("frame") or {}
            if not sid or not frame:
                return False, "缺参数：surface 和 frame 都要给"
            with self.lock:
                self.shown[sid] = frame
                if frame.get("layout"):
                    self.layout = frame["layout"]
            self.compose()
            return True, "已显示 %s（%d 字节）；此刻共 %d 张" % (
                sid, len(json.dumps(frame)), len(self.shown))
        if act == "presentation.retract_surface":
            sid = params.get("surface") or ""
            with self.lock:
                had = self.shown.pop(sid, None) is not None
            self.compose()
            return had, ("已撤下 %s" % sid if had else "本来就没有 %s" % sid)
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
    def on_notice(self, sample):
        try:
            d = json.loads(sample.payload.to_bytes())
        except Exception:
            return
        if d.get("kind") != "a2ui.frame":
            return
        f = d.get("frame") or {}
        sid = _surface_of(f)
        if not sid:
            return
        role = f.get("role") or ""
        with self.lock:
            if f.get("layout"):
                self.layout = f["layout"]
            self.shown[sid] = f
            # ★★ 桌面画布来了 ⇒ 【撤登录画布】（★ 画布瞬时：login retract、desktop show）
            login_sid = "surface/login-" + SCREEN
            if role == "desktop" and login_sid in self.shown and login_sid != sid:
                self.shown.pop(login_sid, None)
                log("★ 桌面画布到了 ⇒ 登录画布 %s 已 retract" % login_sid)
        log("② 收到画布 %s（role=%s，%d 字节）⇒ 合" % (sid, role or "-", len(json.dumps(f))))
        self.compose()

    # ── 合成器（★ 我们的；A2UI 规范【没有】这一层）─────────────────
    #   ★ A2UI 只描述【一张画布内部】；★ 多张怎么摞，规范不写 ⇒ 这一层是我们补的。
    #   输入：layout（也是我们的扩展）＋ shown 表；★ 输出：合成清单 ⇒ 渲染器。
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
    def on_act(self, msg):
        # ★★ A2UI Action 格式：{"event": {"name": ..., "context": {...}}}
        _a = msg.get("action") or {}
        if isinstance(_a, dict) and isinstance(_a.get("event"), dict):
            act = _a["event"].get("name") or ""
        else:
            act = _a.get("name") or ""
        if act == "presentation.login":
            # ★★ 值【已经在 action.context 里】—— genui 点了按钮会把 {path} 解析成真值
            dm = msg.get("dataModel") or {}
            # ★ 两种形状都认：{"event":{"name","context"}}（A2UI 帧里）
            #   和扁平 {"name","context"}（渲染器回推给我们时）
            ctx = (_a.get("event") or {}).get("context") or _a.get("context") or {}
            login = dm.get("login") if isinstance(dm.get("login"), dict) else dm
            user = ctx.get("user") or login.get("user") or dm.get("lg_u") or ""
            pw = ctx.get("pass") if ctx.get("pass") is not None else login.get("pass")
            # ★★ 登录是【谁的】—— 不自己判，【问 space】（经本体）
            self.s.put(T_ASK, json.dumps({
                "id": "login-" + str(int(time.time() * 1000)),
                "action": "space.login",
                "params": {"user": user, "pass": pw},
                "actor": "world://surface/" + SCREEN,
            }, ensure_ascii=False))
            log("③ 登录 ⇒ world/ask space.login（问 space，user=%s）" % user)
            # ★ 一步算一步：★ 呈现【不自己切】，等 space 出桌面画布 ⇒ 收到 ⇒ 合
            return
        log("③ 人的动作：%s（comp=%s）" % (act, msg.get("component")))


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
    s.declare_subscriber(T_NOTICE, p.on_notice)
    s.declare_subscriber(T_EXEC, p.on_exec)
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
