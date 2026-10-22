# -*- coding: utf-8 -*-
"""C104 · protocol SDK —— 进程只能通过 SDK 构造/解析消息，topic 只能查 C1。

断言：合法消息可编码/解析；非法参数/坏 key 必须拒；MCP 字段不能过 parse。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol import sdk  # noqa: E402


def main():
    bad = []
    try:
        call = sdk.build_call("world://agent/a", "world://calculator", "add", [1, 1])
        raw = sdk.encode(call)
        again = sdk.parse(raw)
        if again != call:
            bad.append("call 编解码不一致")
        if call["type"] != "call" or call["data"]["fn"] != "add":
            bad.append("call 字段不对")
    except Exception as exc:  # noqa: BLE001
        bad.append("call 构造失败：%s" % exc)

    try:
        reg = sdk.build_register(
            "world://app/calculator", "world://ontology",
            {"id": "world://app/calculator", "object_type": "Application"},
            functions=[{"name": "add"}],
        )
        sdk.encode(reg)
    except Exception as exc:  # noqa: BLE001
        bad.append("register 构造失败：%s" % exc)

    try:
        res = sdk.build_result("world://calculator", "world://ontology", "call-1", True, 2)
        sdk.encode(res)
    except Exception as exc:  # noqa: BLE001
        bad.append("result 构造失败：%s" % exc)

    try:
        sdk.build_result("world://calculator", "world://ontology", "call-1", False,
                         error={"code": "X"})
    except Exception as exc:  # noqa: BLE001
        bad.append("失败 result 构造失败：%s" % exc)

    try:
        sdk.topic("call")
        sdk.topic("call_exec")
    except Exception as exc:  # noqa: BLE001
        bad.append("合法 topic 失败：%s" % exc)

    try:
        sdk.topic("mcp/tools")
        bad.append("未知 topic 应拒未拒")
    except KeyError:
        pass

    bad_msg = dict(sdk.build_call("world://agent/a", "world://calculator", "add", [1]))
    bad_msg["jsonrpc"] = "2.0"
    try:
        sdk.parse(bad_msg)
        bad.append("MCP 字段应拒未拒")
    except Exception:
        pass

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（protocol SDK：编解码/topic/register/call/result 全过，坏输入拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
