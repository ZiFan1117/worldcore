# -*- coding: utf-8 -*-
"""C114 · P2 register 的 binding 必须先过 P1 binding 校验（不只看 action 在 law）。

反例：binding.required_roles=[]（消息层允许，P1 binding 应拒）⇒ BINDING_INVALID，不进 registry。
正控：roles 非空 ⇒ 进 registry。
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


def msg(bindings):
    return sdk.build_register(
        "world://fs/fs0", "world://ontology",
        {"id": "world://fs/fs0", "object_type": "fs"},
        bindings=bindings,
    )


def main():
    bad = []
    H.temp_dataset()
    op = H.import_ontology_process()
    w = H.new_world()

    w.on_register(H.Sample(sdk.encode(msg([
        {"action": "file.stat", "function": "stat", "required_roles": ["fs"]},
    ]))))
    if "file.stat" not in w.registry:
        bad.append("roles 非空的正控没进 registry")

    w.on_register(H.Sample(sdk.encode(msg([
        {"action": "file.list", "function": "list", "required_roles": []},
    ]))))
    if "file.list" in w.registry:
        bad.append("roles 空的 binding 进了 registry")
    if not any(row.get("code") == "BINDING_INVALID"
               for row in H.read_jsonl(op.LEDGER_PATH)[0]):
        bad.append("账上没有 BINDING_INVALID")

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P2 binding 先过 P1 校验；roles 空拒并落 BINDING_INVALID）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
