# -*- coding: utf-8 -*-
"""C115 · P2 call 竖切（ontology 侧）：call → call_exec；result → call_result。

不启真 provider；只验 ontology 的转发/回话/账。
反例：未知 action ⇒ 回 UNKNOWN_ACTION，不转发。
"""
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
    op = H.import_ontology_process()
    w = H.new_world()
    w.on_register(H.Sample({
        "action": "file.stat", "function": "stat",
        "registered_by": "world://fs/fs0", "registered_by_kind": "fs",
        "required_roles": ["fs"],
    }))
    s = H.Session()
    call = sdk.build_call("world://user/zhang", "world://ontology",
                          "file.stat", {"path": "/etc/hostname"})
    p2_call.handle_call(H.Sample(sdk.encode(call)), w, s)
    execs = [p for t, p in s.puts if t == "world/call/exec"]
    if not execs:
        bad.append("没有发 call_exec")
    else:
        ex = sdk.parse(execs[0])
        if ex["data"].get("route") != "fs":
            bad.append("route=%r" % ex["data"].get("route"))
        if not ex["data"].get("permit"):
            bad.append("call_exec 缺 permit")
        if ex["id"] != call["id"]:
            bad.append("id 不一致")

    res = sdk.build_result("world://fs/fs0", "world://ontology", call["id"], True,
                           result={"path": "/etc/hostname", "size": 1})
    p2_call.handle_result(H.Sample(sdk.encode(res)), w, s)
    reps = [p for t, p in s.puts if t == "world/call/result"]
    if not reps:
        bad.append("没有发 call_result")
    else:
        rep = sdk.parse(reps[-1])
        if rep["data"].get("result", {}).get("size") != 1:
            bad.append("call_result 结果不对")

    bad_call = sdk.build_call("world://user/zhang", "world://ontology",
                              "no.such.action", {})
    p2_call.handle_call(H.Sample(sdk.encode(bad_call)), w, s)
    if not any(t == "world/call/result" for t, p in s.puts):
        bad.append("未知 action 没有错误回话")

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P2 call：call→exec 带 permit/route；result→call_result；未知 action 回错）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
