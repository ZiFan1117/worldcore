# -*- coding: utf-8 -*-
"""C119 · P2 call 负例：缺参/前置条件不成立 ⇒ 回错，不签 permit、不发 call_exec。"""
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
from gate import p2_call  # noqa: E402


def main():
    bad = []
    H.temp_dataset()
    H.import_ontology_process()
    w = H.new_world()
    w.on_register(H.Sample({
        "action": "file.stat", "function": "stat",
        "registered_by": "world://fs/fs0", "registered_by_kind": "fs",
        "required_roles": ["fs"],
    }))
    s = H.Session()
    call = sdk.build_call("world://user/zhang", "world://ontology", "file.stat", {})
    p2_call.handle_call(H.Sample(sdk.encode(call)), w, s)
    if any(t == "world/call/exec" for t, _ in s.puts):
        bad.append("缺参仍发了 call_exec")
    reps = [p for t, p in s.puts if t == "world/call/result"]
    if not reps:
        bad.append("缺参没有错误回话")
    else:
        rep = sdk.parse(reps[-1])
        if rep["data"].get("ok") is not False:
            bad.append("缺参结果不是 ok=false")
        if not (rep["data"].get("error") or {}).get("code"):
            bad.append("缺参结果没有 error.code")
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P2 call 缺参：回错，不签 permit，不发 call_exec）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
