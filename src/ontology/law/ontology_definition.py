# -*- coding: utf-8 -*-
"""AIOS 世界的本体定义 —— ★ **定义＝声明件**（`src/ontology/world.json`），本件只负责「装载」。

★ 定义方式（作者 2026-10-19 裁决）：抄**借书平台** —— 声明式文件 → 解析 → 校验 → 生成。
  · **法**：`src/ontology/world.json`（唯一权威载体；人可审、可 diff；由 `law_loader` 校验后才上岗）；
  · **生成物**：导出的 `ontology.json`／`手册`／`OWL`（改法＝改声明件，不改正本代码）；
  · **代码**：本件只做装载（声明件 → 本体；再从 sysknife 映射表补 sys.*；补动作契约默认值；许可条文归一）。

★ 坏法不带病上岗：`law_loader.load_law()` 校验不过 ⇒ 装载即失败（不是运行到一半才发现）。

★ 改本体的正确姿势（2026-10-19 起）：
  ① 改 `src/ontology/world.json`（要人审）；
  ② `python scripts/release/export-law.py --check` 确认声明件与运行中的法一致；
  ③ 跑 `python scripts/test/check.py`（C35 判「定义在声明件里」、C36 判动作契约、C37 判接口/多态）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # .../ontology/law
ONTO = os.path.dirname(HERE)                               # .../ontology
SRC = os.path.dirname(ONTO)                                # .../src（foundry_ontology 在这）
for _p in (SRC, ONTO, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from law.law_loader import load_law                      # noqa: E402
from law.sysknife_actions import load_sysknife_actions    # noqa: E402
from gate.action_contract import load_action_contracts    # noqa: E402
from law.grants import normalize_grants                  # noqa: E402


def build_aios_ontology():
    """★ 装载：声明件 → 本体；再从映射表补 sys.*；补契约默认值；许可条文归一。"""
    o = load_law()
    load_sysknife_actions(o)
    load_action_contracts(o)
    normalize_grants(o)
    return o


if __name__ == "__main__":
    o = build_aios_ontology()
    print("对象类型:", len(o.object_types), list(o.object_types))
    print("接口    :", len(o.interfaces), list(o.interfaces))
    print("关系类型:", len(o.link_types), list(o.link_types))
    print("动作类型:", len(o.action_types), list(o.action_types)[:8], "…")
    print("函数    :", len(o.functions), list(o.functions))
