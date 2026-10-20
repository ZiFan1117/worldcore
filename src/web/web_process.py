#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ worldcore 语义浏览器桥（`src/web/`，一进程一夹）—— 让**浏览器**也能看/说/点这个世界（语义浏览器的服务端）。

★ 作者（逐字整理）：「我们可以做一个浏览器，语音浏览器」。

★ 它是什么：**另一个「呈现」**（HTTP + SSE + POST，不依赖 Flutter）：
  - `GET /`            → 语音浏览器页面（`voice.html`，原生 Web Speech：听写/朗读）
  - `GET /events`      → **SSE**：世界推来的 `a2ui.frame`／`world.event` 一行一条（浏览器直接渲染）
  - `POST /cmd`        → JSON：`{"op":"login","user":..,"secret":..}` /
                          `{"op":"ui","surface":..,"action":{...},"component":..}`（人点按钮）/ `{"op":"ping"}`
★ 它不是什么：不裁决、不记账、不画像素——界面仍由世界给 A2UI 帧，它只转发。
"""
import json
import os
import queue
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import zenoh

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
PORT = int(os.environ.get("AIOS_WEB_PORT", "8765"))
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_NOTICE = "world/notice"
T_EVENT = "world/event"
T_ACT = "world/ui/act"

HTML = os.path.join(HERE, "browser.html")


def log(*a):
    print("[web]", *a, flush=True)


def scenes_dir():
    return os.environ.get("AIOS_SCENES_DIR", "/var/lib/aios/scenes")


def list_scenes():
    """★ P3：列出已落盘的画布文件（人能看世界有哪些场景）。"""
    d = scenes_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.endswith(".json"))


def read_scene(surface):
    """★ 按 surface id 读场景文件（surface/desktop-zhang → surface_desktop-zhang.json）。"""
    name = str(surface or "").replace("/", "_") + ".json"
    p = os.path.join(scenes_dir(), name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def agent_heartbeat(path=None):
    """★（P7）读 agent 心跳（默认 /run/aios/agent-heartbeat.json），返回 (ok, hb, age秒)。"""
    p = path or os.environ.get("AIOS_AGENT_HB", "/run/aios/agent-heartbeat.json")
    try:
        with open(p, encoding="utf-8") as f:
            hb = json.load(f)
        import datetime as _dt
        last = _dt.datetime.fromisoformat(hb.get("last_at") or "")
        age = (_dt.datetime.now().astimezone() - last).total_seconds()
        return True, hb, age
    except Exception:
        return False, None, None


class WebApp:
    """★ 唯一的桥逻辑（好测）：HTTP 层只调用它。"""

    def __init__(self, session):
        self.s = session
        self.ticket = ""
        self.user = ""
        self.clients = []          # 每个 SSE 客户端一个 queue
        self.recent_frames = []    # ★ 最近推过的 A2UI 帧（给 /render 静态预览）
        self.render_wait = float(os.environ.get("AIOS_RENDER_WAIT", "3.0"))
        self.lock = threading.Lock()

    # ── SSE 扇出 ──
    def add_client(self):
        q = queue.Queue()
        with self.lock:
            self.clients.append(q)
        return q

    def drop_client(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def feed(self, obj):
        with self.lock:
            for q in list(self.clients):
                q.put(obj)

    # ── 总线 ──
    def subscribe(self):
        self.s.declare_subscriber(T_NOTICE, self._on_notice)
        self.s.declare_subscriber(T_EVENT, self._on_event)
        log("订上了：%s / %s" % (T_NOTICE, T_EVENT))

    def _on_notice(self, smp):
        try:
            d = json.loads(smp.payload.to_string())
        except Exception:
            return
        if d.get("kind") == "a2ui.frame":
            with self.lock:
                self.recent_frames.append(d.get("frame"))
                self.recent_frames = self.recent_frames[-20:]
            self.feed({"type": "frame", "frame": d.get("frame"), "by": d.get("by")})
        elif d.get("kind") == "confirm.request":
            # ★ 语义浏览器：人确认弹窗的数据（点/说「签」都回到本体 confirm.resolve）
            self.feed({"type": "confirm", "confirmation": d.get("confirmation"),
                       "by": d.get("by")})
        elif d.get("kind") == "space.logout":
            self.ticket = ""
            self.feed({"type": "logout"})

    def _on_event(self, smp):
        try:
            d = json.loads(smp.payload.to_string())
        except Exception:
            return
        self.feed({"type": "event", "event": d})

    def call(self, action, params=None, ticket="", timeout=15.0):
        """★ 一问一答：发 world/ask，等 world/ask/result（同 id）。"""
        rid = "web-" + uuid.uuid4().hex[:10]
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        box, ev = {}, threading.Event()

        def _on(smp):
            try:
                d = json.loads(smp.payload.to_string())
            except Exception:
                return
            if d.get("id") == rid:
                box.update(d)
                ev.set()

        sub = self.s.declare_subscriber(T_ASK_RESULT, _on)
        try:
            self.s.put(T_ASK, json.dumps(msg, ensure_ascii=False))
            if not ev.wait(timeout):
                return {"ok": False, "why": "超时（%ss）" % timeout}
            return box
        finally:
            try:
                sub.undeclare()
            except Exception:
                pass

    def login_and_wait(self, user, secret):
        """★ 服务端登录，并等最近一帧 A2UI 帧（给 /render 同步预览）。"""
        r = self.handle_cmd({"op": "login", "user": user, "secret": secret})
        if not r.get("ok"):
            return r
        deadline = time.time() + self.render_wait
        while time.time() < deadline:
            with self.lock:
                if self.recent_frames:
                    break
            time.sleep(0.05)
        return r

    def query(self, kind, params=None, ticket="", timeout=10.0):
        """★ 查世界（world/query，回话在 world/query/result）。"""
        rid = "webq-" + uuid.uuid4().hex[:10]
        msg = {"id": rid, "kind": kind}
        if params:
            msg.update(params)
        if ticket:
            msg["ticket"] = ticket
        box, ev = {}, threading.Event()

        def _on(smp):
            try:
                d = json.loads(smp.payload.to_string())
            except Exception:
                return
            if d.get("id") == rid:
                box.update(d)
                ev.set()

        sub = self.s.declare_subscriber("world/query/result", _on)
        try:
            self.s.put("world/query", json.dumps(msg, ensure_ascii=False))
            if not ev.wait(timeout):
                return {"ok": False, "why": "查询超时"}
            return box
        finally:
            try:
                sub.undeclare()
            except Exception:
                pass

    def catchup(self, since, limit=100):
        """★ 浏览器重连带 Last-Event-ID ⇒ 补它错过的世界事件（P8）。"""
        if not since or not self.ticket:
            return []
        r = self.query("events", {"since": since, "limit": limit}, ticket=self.ticket)
        return (r.get("data") or {}).get("events") or []

    # ── 浏览器命令 ──
    def handle_cmd(self, d):
        if not isinstance(d, dict):
            return {"ok": False, "why": "不是对象"}
        op = d.get("op") or ""
        if op == "ping":
            return {"ok": True, "what": "worldcore-web", "user": self.user,
                    "has_ticket": bool(self.ticket)}
        if op == "login":
            user = d.get("user") or ""
            secret = d.get("secret") or ""
            r = self.call("identity.authenticate", {"user": user, "secret": secret})
            body = r.get("body") or {}
            tk = body.get("ticket") if isinstance(body, dict) else None
            if not tk:
                return {"ok": False, "why": r.get("why") or "认证失败"}
            r2 = self.call("space.login", {"ticket": tk, "user": user}, ticket=tk)
            if not r2.get("ok"):
                return {"ok": False, "why": r2.get("why") or "进空间失败"}
            self.ticket, self.user = tk, user
            log("登录：%s" % user)
            return {"ok": True, "user": user}
        if op == "ui":
            surface = d.get("surface") or ""
            action = d.get("action") or {}
            comp = d.get("component") or ""
            self.s.put(T_ACT, json.dumps({"t": "act", "surface": surface, "action": action,
                                          "component": comp}, ensure_ascii=False))
            return {"ok": True}
        if op == "ask":
            if not self.ticket:
                return {"ok": False, "why": "先登录"}
            r = self.call(d.get("action") or "", d.get("params") or {}, ticket=self.ticket)
            return {"ok": bool(r.get("ok")), "result": r}
        if op == "confirm_resolve":
            # ★ 人点了弹窗：这条也要经本体（带票）——浏览器不自己发许可
            if not self.ticket:
                return {"ok": False, "why": "先登录"}
            params = {"name": d.get("name") or "",
                      "decision": d.get("decision") or "allow_once",
                      "reason": d.get("reason") or "语义浏览器确认"}
            if d.get("expires"):
                params["expires"] = d["expires"]
            if d.get("max_uses"):
                params["max_uses"] = int(d["max_uses"])
            r = self.call("confirm.resolve", params, ticket=self.ticket)
            return {"ok": bool(r.get("ok")), "result": r}
        return {"ok": False, "why": "不认识的 op：%s" % op}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        app = self.server.app
        path = urlsplit(self.path).path   # ★ 去掉查询串（?user=…&secret=… 仍走页面）
        if path in ("/", "/index.html", "/voice.html"):
            try:
                with open(HTML, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, "voice.html 不在", "text/plain; charset=utf-8")
            return
        if path.startswith("/render"):
            # ★ 静态预览（截图/kiosk/无异步）：服务端先登录，把最近 A2UI 帧注入页面同步渲染
            from urllib.parse import parse_qs
            q = parse_qs(urlsplit(self.path).query)
            user = (q.get("user") or [""])[0]
            secret = (q.get("secret") or [""])[0]
            out = app.login_and_wait(user, secret)
            if not out.get("ok"):
                self._send(400, out, "text/plain; charset=utf-8")
                return
            try:
                with open(HTML, encoding="utf-8") as f:
                    html = f.read()
            except FileNotFoundError:
                self._send(500, "voice.html 不在", "text/plain; charset=utf-8")
                return
            frames = list(app.recent_frames)
            blob = json.dumps(frames, ensure_ascii=False).replace("</", "<\\/")
            tail = ("<script>window.PRELOAD_FRAMES = %s;"
                    "window.PRELOAD_FRAMES.forEach(function (f) { renderFrame(f); });"
                    "</script>" % blob)
            html = html.replace("</body>", tail + "</body>")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path.startswith("/scenes"):
            self._send(200, {"ok": True, "scenes": list_scenes()})
            return
        if path.startswith("/scene/view"):
            # ★ P3：把「文件里的画布」直接渲染出来（不需要登录、不依赖实时 SSE）
            from urllib.parse import parse_qs
            q = parse_qs(urlsplit(self.path).query)
            surface = (q.get("surface") or [""])[0]
            try:
                scene = read_scene(surface)
            except Exception as e:
                self._send(404, {"ok": False, "why": "没有这个场景：%s（%s）" % (surface, e)})
                return
            try:
                with open(HTML, encoding="utf-8") as f:
                    html = f.read()
            except FileNotFoundError:
                self._send(500, "voice.html 不在", "text/plain; charset=utf-8")
                return
            frames = [scene.get("frame")] if scene.get("frame") else []
            blob = json.dumps(frames, ensure_ascii=False).replace("</", "<\\/")
            tail = ("<script>window.PRELOAD_FRAMES = %s;"
                    "window.PRELOAD_FRAMES.forEach(function (f) { renderFrame(f); });"
                    "</script>" % blob)
            html = html.replace("</body>", tail + "</body>")
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path.startswith("/scene"):
            from urllib.parse import parse_qs
            q = parse_qs(urlsplit(self.path).query)
            surface = (q.get("surface") or [""])[0]
            try:
                self._send(200, {"ok": True, "scene": read_scene(surface)})
            except Exception as e:
                self._send(404, {"ok": False, "why": "没有这个场景：%s（%s）" % (surface, e)})
            return
        if path.startswith("/agent"):
            ok, hb, age = agent_heartbeat()
            self._send(200, {"ok": ok, "heartbeat": hb,
                             "age_seconds": (round(age) if age is not None else None)})
            return
        if path.startswith("/events"):
            q = app.add_client()
            # ★ P8：EventSource 重连会带 Last-Event-ID ⇒ 先补它错过的事件（不重复：since 严格大于）
            last_id = self.headers.get("Last-Event-ID") or ""
            if last_id:
                try:
                    for e in app.catchup(last_id):
                        q.put({"type": "event", "event": e})
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(b": connected\n\n")
                while True:
                    try:
                        obj = q.get(timeout=20)
                        lines = []
                        ev = obj.get("event") if isinstance(obj, dict) else None
                        if isinstance(ev, dict) and ev.get("at"):
                            lines.append("id: " + str(ev["at"]))   # ★ 断线重连用
                        lines.append("data: " + json.dumps(obj, ensure_ascii=False))
                        self.wfile.write(("\n".join(lines) + "\n\n").encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                app.drop_client(q)
            return
        self._send(404, {"ok": False, "why": "没有这个路径"})

    def do_POST(self):
        if not self.path.startswith("/cmd"):
            self._send(404, {"ok": False, "why": "没有这个路径"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            self._send(400, {"ok": False, "why": "不是 JSON"})
            return
        out = self.server.app.handle_cmd(d)
        self._send(200, out)


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([BUS]))
    s = zenoh.open(conf)
    app = WebApp(s)
    app.subscribe()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.app = app
    srv.daemon_threads = True
    log("★ 语义浏览器桥起来了：http://0.0.0.0:%d/（SSE /events，命令 POST /cmd）" % PORT)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
