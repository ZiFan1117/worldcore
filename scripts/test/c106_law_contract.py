# -*- coding: utf-8 -*-
"""C106 · 本体 law 全部动作必须过 P1 动作契约（不是另写一份契约）。

断言：world.json 的 actions 全量 validate_action_contract 无错；
注入一个坏 effect 必须被拒。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.contract import validate_action_contract  # noqa: E402

WORLD = os.path.join(ROOT, "src", "ontology", "world.json")


def main():
    bad = []
    with open(WORLD, "r", encoding="utf-8") as f:
        world = json.load(f)
    actions = world.get("actions") or []
    if not actions:
        bad.append("world.json 没有 actions")
    for a in actions:
        why = validate_action_contract(a)
        if why:
            bad.append("%s：%s" % (a.get("id"), "；".join(why)))

    sample = dict(actions[0]) if actions else {}
    sample = json.loads(json.dumps(sample, ensure_ascii=False))
    sample["id"] = "c106.bad.effect"
    sample["effects"] = [{"kind": "execute_anything"}]
    if not validate_action_contract(sample):
        bad.append("坏 effect 应拒未拒")

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad[:20]:
            print("  - " + line)
        return 1
    print("=== 结论：绿（world.json %d 个动作全过 P1 契约；坏 effect 拒）===" % len(actions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
