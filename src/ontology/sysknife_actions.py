# -*- coding: utf-8 -*-
"""★ 从 sysknife 的映射表动态建 ActionType（2026-10-19 从 `ontology_definition.py` 拆出，C27）。

★ 作者令（10-17）：「我们他这不是有 176 个吗？那我们全部做成 action……」
★ 文件：`AIOS_SYSKNIFE_MAP`（默认 `/usr/lib/aios/sysknife-command-map.json`）；缺文件 ⇒ 跳过（不阻断本体起）。
★ 动作 name 用 `sys.<PascalName>`；**参数表从映射表的 `params` 抄**（借自订单样板：参数是动作契约的一部分）。
"""
import json
import os

from foundry_ontology.core import ActionType, ActionParameter
from foundry_ontology.core.data_types import PropertyType


def load_sysknife_actions(o):
    """★ 建 sys.* ActionType ＋ 只读动作的许可条文；返回建了几个。"""
    path = os.environ.get("AIOS_SYSKNIFE_MAP", "/usr/lib/aios/sysknife-command-map.json")
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0
    n = 0
    grants = o.metadata.setdefault("permissions", {}).setdefault("grants", {})
    for a in data.get("actions", []):
        name = a.get("action") or ""
        if not name or name in o.action_types:
            continue
        try:
            at = ActionType(
                name,
                name,
                description="从 sysknife 抄的动作（MIT）—— 载体执行 %s %s"
                            % (a.get("program", "?"), " ".join(a.get("args") or [])),
                parameters=[ActionParameter(p, PropertyType.STRING, required=True)
                            for p in (a.get("params") or [])],
                effects=[],
                validation_rules=[],
                metadata={
                    "what": "%s" % name,
                    "not_roles": [],
                    "implemented": "sysknife",
                    "program": a.get("program"),
                    "args": a.get("args") or [],
                },
            )
            o.register_action_type(at)
            # ★★ 只读动作（Get*/List*）默认放行：不用人确认（作者裁：批不批归本体）
            # ★ 只读（Get*/List*）免确认；变更类【不给许可】⇒ 默认拒绝 ⇒ 要走人确认
            if name.startswith("sys.Get") or name.startswith("sys.List"):
                grants.setdefault(name, {"who": ["world://user", "world://agent/dsh"],
                                        "why": "只读查询（从 sysknife 抄，MIT）"})
            n += 1
        except Exception:
            continue
    return n
