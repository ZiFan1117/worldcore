# -*- coding: utf-8 -*-
"""C109 · ontology 接收 P2 register 信封（individual + bindings）—— fs 竖切第一步。

正控：合法 register 信封 ⇒ file.stat/file.list 进 registry。
反例：bindings 里夹 law 外 action ⇒ 不进 registry，落 UNKNOWN_ACTION。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

import _proc_helper as H  # noqa: E402
from protocol import sdk  # noqa: E402


def reg_msg(bindings):
    return sdk.build_register(
        "world://fs/fs0",
        "world://ontology",
        {"id": "world://fs/fs0", "object_type": "fs"},
        bindings=bindings,
    )


def main():
    bad = []
    H.temp_dataset()
    op = H.import_ontology_process()
    w = H.new_world()

    good = reg_msg([
        {"action": "file.stat", "function": "stat", "required_roles": ["fs"]},
        {"action": "file.list", "function": "list", "required_roles": ["fs"]},
    ])
    w.on_register(H.Sample(sdk.encode(good)))
    for aid in ("file.stat", "file.list"):
        if aid not in w.registry:
            bad.append("合法绑定没进 registry：%s" % aid)

    evil = reg_msg([
        {"action": "c109.no.such.action", "function": "x", "required_roles": ["fs"]},
    ])
    w.on_register(H.Sample(sdk.encode(evil)))
    if "c109.no.such.action" in w.registry:
        bad.append("law 外绑定进了 registry")
    if not any(row.get("code") == "UNKNOWN_ACTION"
               for row in H.read_jsonl(op.LEDGER_PATH)[0]):
        bad.append("账上没有 UNKNOWN_ACTION")

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P2 register 信封：合法 bindings 进注册表；law 外 action 拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
