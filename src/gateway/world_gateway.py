#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 世界薄网关（`src/gateway/`，一进程一夹）—— 外部进世界的【唯一门】。

★ 作者口径：「只做协议翻译，不做任何治理」。
★ 收：HTTP ＋ JSON-RPC 2.0（`POST /`，只听 127.0.0.1）。
     · `world.query`  ⇒ 总线 `world/query`（params 原样直传）
     · `world.ask`    ⇒ 总线 `world/ask`（params 原样：action／params／actor／ticket…）
★ 回：等 `world/query/result`／`world/ask/result`，把回话**原样**回给调用方；
     本体给的拒绝码进 JSON-RPC `error.data.world_code`，类别进 `data.category`（照本体闭集表抄）。
★ 它【不】：不校验动作名／参数／许可／凭证；不自己记账；不自造拒绝码；不替调用方造 actor。
  ⇒ 未登记动作、没有身份，一律由本体拒（预期 `UNKNOWN_ACTION`／`NO_IDENTITY` 等等）。

★ 环境：AIOS_BUS（默认 tcp/127.0.0.1:7447）、AIOS_GATEWAY_PORT（默认 8780）、
        AIOS_GATEWAY_ASK_TIMEOUT（默认 110s）、AIOS_GATEWAY_QUERY_TIMEOUT（默认 30s）。
"""
import json
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# ★ 只借本体的【闭集表】把码翻成类别（一个事实一个载体：不在这里另立一张表）
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "ontology")))

import gateway_bus  # noqa: E402
import gateway_rpc as rpc  # noqa: E402
from gate.world_codes import reject_category  # noqa: E402

HOST = "127.0.0.1"                 # ★ 只监听环回：宿主上的插件来敲，不直接对外暴露
DEFAULT_PORT = 8780
PORT = int(os.environ.get("AIOS_GATEWAY_PORT", str(DEFAULT_PORT)))
ASK_TIMEOUT = float(os.environ.get("AIOS_GATEWAY_ASK_TIMEOUT", "110"))
QUERY_TIMEOUT = float(os.environ.get("AIOS_GATEWAY_QUERY_TIMEOUT", "30"))


def log(*a):
    print("[网关]", *a, flush=True)


class App:
    """★ 唯一的翻译逻辑（好测：HTTP 层只调它，判据可注入假总线）。"""

    def __init__(self, bus, category_of=reject_category,
                 ask_timeout=None, query_timeout=None):
        self.bus = bus
        self.category_of = category_of
        self.ask_timeout = ASK_TIMEOUT if ask_timeout is None else ask_timeout
        self.query_timeout = QUERY_TIMEOUT if query_timeout is None else query_timeout

    def call(self, raw):
        """raw：JSON-RPC 请求体（bytes／str）⇒ 响应对象；返回 None 表示「通知，不回话」。"""
        req, err = rpc.parse_request(raw)
        if err is not None:
            return err
        rid = "gw-" + uuid.uuid4().hex[:10]
        put_topic, res_topic, msg = rpc.to_bus_message(req["method"], req["params"], rid)
        timeout = self.ask_timeout if req["method"] == "world.ask" else self.query_timeout
        reply = self.bus.once(put_topic, res_topic, msg, timeout)
        if req["notification"]:
            return None
        return rpc.to_response(req["method"], req["id"], reply, self.category_of)


class Handler(BaseHTTPRequestHandler):
    """★ 传输层：一行一条 JSON-RPC，不解释业务。"""

    server_version = "worldcore-gateway/1"

    def log_message(self, fmt, *args):
        return                          # 日志由 [网关] 自己出，不刷 access log

    def _send(self, code, body):
        raw = b""
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n > 0 else b""
        try:
            out = self.server.app.call(raw)
        except Exception as e:      # ★ 翻译层自己崩了 ⇒ 如实报传输错，不假装是世界的拒绝
            log("翻译出错：%s" % e)
            out = rpc.error(None, rpc.CODE_BUS_ERROR, "网关内部错误：%s" % str(e)[:160])
        if out is None:
            self._send(204, None)
        else:
            self._send(200, out)

    def do_GET(self):
        self._send(405, rpc.error(None, rpc.CODE_INVALID_REQUEST,
                                  "只用 POST /（JSON-RPC 2.0）"))


def main():
    endpoint = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
    log("① 连总线 %s …" % endpoint)
    bus = gateway_bus.connect(endpoint)
    app = App(bus)
    log("② 起 HTTP：http://%s:%d （JSON-RPC 2.0）" % (HOST, PORT))
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    server.app = app
    log("★ 网关起来了 —— 只翻译，不治理")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        server.server_close()
        bus.close()


if __name__ == "__main__":
    main()
