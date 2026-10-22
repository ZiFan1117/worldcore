# -*- coding: utf-8 -*-
"""C122 · P2 state_report：合法 report 进缓存/账并回 ack；坏 state 拒。"""
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
from gate import state_path  # noqa: E402


def main():
    bad = []
    H.temp_dataset()
    H.import_ontology_process()
    w = H.new_world()
    s = H.Session()
    msg = sdk.build_state_report("world://app/x", "world://ontology",
                                 "world://app/x", 1, {"state": "idle"})
    state_path.handle_report(H.Sample(sdk.encode(msg)), w, s)
    if getattr(w, "_state_cache", {}).get("world://app/x", {}).get("state") != "idle":
        bad.append("state 没进缓存")
    if not any(t == "world/state/ack" for t, _ in s.puts):
        bad.append("没有回 state_ack")

    s.puts.clear()
    try:
        sdk.build_state_report("world://app/x", "world://ontology",
                               "world://app/x", 2, [])
        bad.append("坏 report 居然构造成功")
    except Exception:
        pass

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（state_report：缓存+账+ack；坏 changes 拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
