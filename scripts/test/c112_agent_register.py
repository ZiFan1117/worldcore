# -*- coding: utf-8 -*-
"""C112 · agent 注册走 P2 register 信封（individual + bindings）—— 不是六条旧五格。

断言：agent_register.register 只 put 一条 world.message.v1 register；bindings 有 6 个；
provider kind 可由 provider_auth 推出为 agent。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology"),
          os.path.join(ROOT, "src", "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _proc_helper as H  # noqa: E402
from protocol import sdk  # noqa: E402
from agent_register import ACTIONS, register  # noqa: E402
from provider_auth.provider_auth import kind_of  # noqa: E402


def main():
    bad = []
    s = H.Session()
    register(s, "dsh", "world/register")
    if len(s.puts) != 1:
        bad.append("应只 put 一条，实得 %d" % len(s.puts))
    else:
        topic, payload = s.puts[0]
        if topic != "world/register":
            bad.append("topic=%r" % topic)
        msg = sdk.parse(payload)
        if msg.get("type") != "register":
            bad.append("type=%r" % msg.get("type"))
        data = msg.get("data") or {}
        bindings = data.get("bindings") or []
        if len(bindings) != len(ACTIONS):
            bad.append("bindings=%d，期望 %d" % (len(bindings), len(ACTIONS)))
        if any(b.get("action") not in ACTIONS for b in bindings):
            bad.append("binding 里有非 agent action")
        if kind_of(msg) != "agent":
            bad.append("provider kind=%r，期望 agent" % kind_of(msg))

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（agent 注册为一条 P2 register 信封；6 bindings；kind=agent）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
