# -*- coding: utf-8 -*-
"""C113 · provider_register 统一构造 P2 信封（clock/network/recovery/vault/worldfs 共用）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _proc_helper as H  # noqa: E402
from protocol import sdk  # noqa: E402
from protocol.registration import provider_register  # noqa: E402


def main():
    bad = []
    s = H.Session()
    actions = [{"action": "network.list", "kind": "read", "why": "x"},
               {"action": "network.state", "kind": "read", "why": "x"}]
    provider_register(s, "world/register", "network", "network0", actions)
    if len(s.puts) != 1:
        bad.append("应只 put 一条，实得 %d" % len(s.puts))
    else:
        topic, payload = s.puts[0]
        msg = sdk.parse(payload)
        if topic != "world/register":
            bad.append("topic=%r" % topic)
        if msg.get("type") != "register":
            bad.append("type=%r" % msg.get("type"))
        data = msg.get("data") or {}
        if (data.get("individual") or {}).get("id") != "world://network/network0":
            bad.append("individual=%r" % data.get("individual"))
        if len(data.get("bindings") or []) != 2:
            bad.append("bindings=%r" % data.get("bindings"))
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（provider_register：一条 P2 信封，individual=world://network/network0，2 bindings）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
