# -*- coding: utf-8 -*-
"""C100 · P2 消息协议 v1 —— 我们的调用/注册/状态同步消息，不是 MCP。

反例：
  · protocol/type/from 缺失或非法
  · call 缺 fn 或 args 不是数组
  · result 缺 ok / ok=false 没 error
  · state_report/state_apply 缺 individual/changes/rev
  · 夹带 MCP 的 jsonrpc/method/params
断言颜色：合法消息全过；上述反例任一没被拒 ⇒ 红。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.message import validate_message  # noqa: E402


def base(msg_type, data, **extra):
    m = {
        "protocol": "world.message.v1",
        "v": 1,
        "type": msg_type,
        "id": "msg-1",
        "from": "world://agent/a",
        "to": "world://ontology",
        "data": data,
    }
    m.update(extra)
    return m


def expect_reject(msg, needle):
    why = validate_message(msg)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    valid = [
        base("call", {"fn": "add", "args": [1, 1]}),
        base("result", {"ok": True, "result": 2}),
        base("result", {"ok": False, "error": {"code": "BAD_ARGS", "detail": "x"}}, id="m2"),
        base("state_report", {"individual": "world://app/calculator", "rev": 7,
                              "changes": {"last_result": 2}, "cause": {"kind": "call", "id": "c1"}}),
        base("state_apply", {"individual": "world://app/calculator", "rev": 8,
                             "changes": {"state": "reset"}, "cause": {"kind": "action", "id": "a1"}}),
        base("state_ack", {"rev": 8, "ok": True}),
        base("register", {"individual": {"id": "world://app/calculator"},
                          "functions": [{"name": "add"}], "actions": [], "data_sources": []}),
        base("event", {"kind": "state_changed", "individual": "world://app/calculator"}),
    ]
    for m in valid:
        why = validate_message(m)
        if why:
            bad.append("合法消息被拒 %s：%s" % (m.get("type"), "；".join(why)))

    x = dict(valid[0]); x["protocol"] = "mcp.v1"
    msg = expect_reject(x, "BAD_PROTOCOL")
    if msg:
        bad.append("protocol：" + msg)

    x = dict(valid[0]); x["type"] = "mcp.tools.call"
    msg = expect_reject(x, "BAD_TYPE")
    if msg:
        bad.append("type：" + msg)

    x = dict(valid[0]); x["from"] = "http://example.com"
    msg = expect_reject(x, "BAD_FROM")
    if msg:
        bad.append("from：" + msg)

    x = dict(valid[0]); x["data"] = {"args": [1]}
    msg = expect_reject(x, "CALL_FN")
    if msg:
        bad.append("call fn：" + msg)

    x = dict(valid[0]); x["data"] = {"fn": "add", "args": {"a": 1}}
    msg = expect_reject(x, "CALL_ARGS")
    if msg:
        bad.append("call args：" + msg)

    x = dict(valid[1]); x["data"] = {"result": 2}
    msg = expect_reject(x, "RESULT_OK")
    if msg:
        bad.append("result ok：" + msg)

    x = dict(valid[2]); x["data"] = {"ok": False}
    msg = expect_reject(x, "RESULT_ERROR")
    if msg:
        bad.append("result error：" + msg)

    x = dict(valid[3]); x["data"] = {"individual": "world://app/calculator", "rev": 7}
    msg = expect_reject(x, "STATE_CHANGES")
    if msg:
        bad.append("state changes：" + msg)

    x = dict(valid[4]); x["data"] = {"individual": "world://app/calculator", "changes": {"state": "x"}}
    msg = expect_reject(x, "STATE_REV")
    if msg:
        bad.append("state rev：" + msg)

    x = dict(valid[0]); x["jsonrpc"] = "2.0"
    msg = expect_reject(x, "MCP_FIELD")
    if msg:
        bad.append("mcp：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P2 消息协议：合法消息通过，MCP/坏字段/坏状态均拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
