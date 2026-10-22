# -*- coding: utf-8 -*-
"""C108 · 注册表只登记 law 已有动作 —— 不能在运行时新增 world action。

反例：注册 c108.no.such.action ⇒ 不进入 registry，且账上应有 UNKNOWN_ACTION。
正控：注册 law 里的 file.stat ⇒ 进入 registry。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _proc_helper as H  # noqa: E402


def main():
    bad = []
    H.temp_dataset()
    op = H.import_ontology_process()
    w = H.new_world()

    unknown = "c108.no.such.action"
    w.on_register(H.Sample({
        "action": unknown,
        "function": "fn.c108",
        "registered_by": "c108",
        "registered_by_kind": "system",
        "required_roles": ["human"],
    }))
    if unknown in w.registry:
        bad.append("law 外动作进了注册表：%s" % unknown,
                   )
    if not any(row.get("code") == "UNKNOWN_ACTION"
               for row in H.read_jsonl(op.LEDGER_PATH)[0]):
        bad.append("账上没有 UNKNOWN_ACTION 拒绝")

    known = "file.stat"
    w.on_register(H.Sample({
        "action": known,
        "function": "fn.c11.test",
        "registered_by": "c11",
        "registered_by_kind": "system",
        "required_roles": ["human"],
    }))
    if known not in w.registry:
        bad.append("law 内动作没进注册表：%s" % known)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（law 外动作拒并落 UNKNOWN_ACTION；law 内动作可登记绑定）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
