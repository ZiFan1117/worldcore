# -*- coding: utf-8 -*-
"""C118 · 注册幂等：同一 binding 重复注册不重复写 registry.jsonl。"""
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


def main():
    bad = []
    H.temp_dataset()
    op = H.import_ontology_process()
    w = H.new_world()
    reg = {"action": "file.stat", "function": "stat",
           "registered_by": "world://fs/fs0", "registered_by_kind": "fs",
           "required_roles": ["fs"]}
    w.on_register(H.Sample(reg))
    w.on_register(H.Sample(dict(reg)))
    rows, _bad = H.read_jsonl(op.REG_PATH)
    if len(rows) != 1:
        bad.append("registry 行数=%d，期望 1" % len(rows))
    if "file.stat" not in w.registry:
        bad.append("registry 内存缺 file.stat")
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（同 binding 重复注册只写一次 registry）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
