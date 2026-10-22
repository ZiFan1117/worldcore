# -*- coding: utf-8 -*-
"""C102 · P3 许可协议 —— permit 的格式/期限/绑定字段；不是 MCP token。

反例：
  · 缺 v/id/action/fp/actor/at/exp/sig
  · fp/sig 不是合法长度
  · exp <= at
  · actor 不是 world://
  · action 名非法
断言颜色：合法 permit 过；反例任一没被拒 ⇒ 红。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.permit import validate_permit  # noqa: E402

FP = "a" * 64
SIG = "b" * 64


def valid():
    return {
        "v": 1,
        "id": "permit-1",
        "action": "file.read_text",
        "fp": FP,
        "actor": "world://agent/a",
        "at": 1000,
        "exp": 2000,
        "sig": SIG,
    }


def reject(x, needle):
    why = validate_permit(x)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_permit(valid())
    if why:
        bad.append("合法 permit 被拒：%s" % "；".join(why))

    for key in ("v", "id", "action", "fp", "actor", "at", "exp", "sig"):
        x = valid(); x.pop(key)
        msg = reject(x, "MISSING:" + key)
        if msg:
            bad.append(key + "：" + msg)

    x = valid(); x["fp"] = "short"
    msg = reject(x, "BAD_FP")
    if msg:
        bad.append("fp：" + msg)

    x = valid(); x["sig"] = "short"
    msg = reject(x, "BAD_SIG")
    if msg:
        bad.append("sig：" + msg)

    x = valid(); x["exp"] = 1000
    msg = reject(x, "BAD_EXP")
    if msg:
        bad.append("exp：" + msg)

    x = valid(); x["actor"] = "http://x"
    msg = reject(x, "BAD_ACTOR")
    if msg:
        bad.append("actor：" + msg)

    x = valid(); x["action"] = "bad action"
    msg = reject(x, "BAD_ACTION")
    if msg:
        bad.append("action：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P3 permit：合法通过，缺格/坏 fp/sig/期限/actor/action 全拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
