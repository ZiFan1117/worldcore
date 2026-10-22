# -*- coding: utf-8 -*-
"""C107 · P1 provider 绑定协议 —— 只绑 law 已有 action/function，不新增定义。

反例：缺字段、action 不在 law、action 名非法、function 为空、roles 为空、夹带新 action 字段。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.binding import validate_binding  # noqa: E402

KNOWN = {"file.read_text", "file.stat"}


def valid():
    return {
        "action": "file.read_text",
        "function": "fn.file.read_text",
        "registered_by": "world://fs/fs0",
        "registered_by_kind": "fs",
        "required_roles": ["fs"],
    }


def reject(x, needle):
    why = validate_binding(x, KNOWN)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_binding(valid(), KNOWN)
    if why:
        bad.append("合法绑定被拒：%s" % "；".join(why))

    for key in ("action", "function", "registered_by", "registered_by_kind", "required_roles"):
        x = valid(); x.pop(key)
        msg = reject(x, "MISSING:" + key)
        if msg:
            bad.append(key + "：" + msg)

    x = valid(); x["action"] = "no.such.action"
    msg = reject(x, "ACTION_NOT_IN_LAW")
    if msg:
        bad.append("law：" + msg)

    x = valid(); x["action"] = "Bad Action"
    msg = reject(x, "BAD_ACTION_ID")
    if msg:
        bad.append("id：" + msg)

    x = valid(); x["function"] = ""
    msg = reject(x, "BAD_FUNCTION")
    if msg:
        bad.append("function：" + msg)

    x = valid(); x["required_roles"] = []
    msg = reject(x, "BAD_ROLES")
    if msg:
        bad.append("roles：" + msg)

    x = valid(); x["world_action"] = "x"
    msg = reject(x, "BAD_FIELD")
    if msg:
        bad.append("field：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P1 绑定：只绑 law 已有 action，缺格/新 action/坏字段拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
