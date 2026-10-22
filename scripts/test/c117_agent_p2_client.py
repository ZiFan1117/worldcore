# -*- coding: utf-8 -*-
"""C117 · agent P2 client：file./fs. 动作发 world/call 信封，不走旧 world/ask。"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology"),
          os.path.join(ROOT, "src", "agent")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _proc_helper as H  # noqa: E402
import agent_p2  # noqa: E402
from protocol import sdk  # noqa: E402


def main():
    bad = []
    s = H.Session()
    agent = types.SimpleNamespace(s=s, p2_results={}, p2_name="dsh")
    r = agent_p2.act(agent, "file.stat", {"path": "/etc/hostname"}, timeout=0)
    if r.get("ok") is not False:
        bad.append("timeout=0 应返回失败")
    if not s.puts:
        bad.append("没有 put")
    else:
        topic, payload = s.puts[0]
        if topic != "world/call":
            bad.append("topic=%r" % topic)
        msg = sdk.parse(payload)
        if msg.get("type") != "call":
            bad.append("type=%r" % msg.get("type"))
        if msg["data"].get("fn") != "file.stat":
            bad.append("fn=%r" % msg["data"].get("fn"))
        if msg["data"].get("args") != {"path": "/etc/hostname"}:
            bad.append("args=%r" % msg["data"].get("args"))
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（agent P2 client：file.stat 发 world/call，参数原样）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
