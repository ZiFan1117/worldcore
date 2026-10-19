#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ worldcore 浏览器桥（`src/web/`，一进程一夹）—— 让**浏览器**也能看/说/点这个世界（语音浏览器的服务端）。

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

import zenoh

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
PORT = int(os.environ.get("AIOS_WEB_PORT", "8765"))
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_NOTICE = "world/notice"
T_EVENT = "world/event"
T_ACT = "world/ui/act"

HTML = os.path.join(HERE, "voice.html")


def log(*a):
    print("[web]", *a, flush=True)


class WebApp:
    """★ 唯一的桥逻辑（好测）：HTTP 层只调用它。"""

    def __init__(self, session):
        self.s = session
        self.ticket = ""
        self.user = ""
        self.clients = []          # 每个 SSE 客户端一个 queue
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
            self.feed({"type": "frame", "frame": d.get("frame"), "by": d.get("by")})
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
        if self.path in ("/", "/index.html", "/voice.html"):
            try:
                with open(HTML, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, "voice.html 不在", "text/plain; charset=utf-8")
            return
        if self.path.startswith("/events"):
            q = app.add_client()
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
                        data = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
                        self.wfile.write(data.encode("utf-8"))
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
    log("★ 语音浏览器桥起来了：http://0.0.0.0:%d/（SSE /events，命令 POST /cmd）" % PORT)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
