#!/usr/bin/env python3
"""★ 把本体【从代码导出】成 JSON —— 构建产物，不是源。

★★ 2026-10-18 作者令（逐字）：「本体数据现在我们代码中不是实现了吗？为什么要推这个呢？」
   ★★ 事实：`ontology_process.py` L77 `self.ontology = build_aios_ontology()` ——
   ★ **运行时用的是 Python 代码，不读 JSON**。
   ★ 所以 JSON 是【导出物／存档】，★ 不是源，★ 不进 git。

用法：
  python scripts/release/export-ontology.py              # 写到 src/ontology/data/ontology.json
  python scripts/release/export-ontology.py --out X.json # 写到别处
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src", "ontology"))
sys.path.insert(0, os.path.join(ROOT, "src"))

from law.ontology_definition import build_aios_ontology  # noqa: E402

import dataclasses


def _json_default(o):
    """★ 枚举／dataclass 之类 json 不认的，转成它的名字。"""
    if hasattr(o, "value"):
        return o.value
    if hasattr(o, "name"):
        return o.name
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    return str(o)


def _ser(v):
    """★ 把 dataclass 序列化成 dict（ObjectType/ActionType/LinkType 都是 dataclass，没有 to_dict）。"""
    try:
        return dataclasses.asdict(v)
    except Exception:
        try:
            return {k: (v2 if isinstance(v2, (str, int, float, bool, type(None), list, dict)) else str(v2))
                    for k, v2 in vars(v).items()}
        except Exception:
            return {}


def main(argv):
    out = os.path.join(ROOT, "src", "ontology", "data", "ontology.json")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    o = build_aios_ontology()
    doc = {
        "world": (o.metadata or {}).get("world", 1),
        "envelope": (o.metadata or {}).get("envelope") or {},
        "families": (o.metadata or {}).get("families") or {},
        "flags": (o.metadata or {}).get("flags") or [],
        "objects": {k: _ser(v) for k, v in o.object_types.items()},
        "links": {k: _ser(v) for k, v in o.link_types.items()},
        "interfaces": {k: _ser(v) for k, v in o.interfaces.items()},
        "actions": {k: _ser(v) for k, v in o.action_types.items()},
        "functions": {k: _ser(v) for k, v in o.functions.items()},
        "permissions": (o.metadata or {}).get("permissions") or {},
        "governance": (o.metadata or {}).get("governance") or {},
        "notes": (o.metadata or {}).get("notes") or {},
    }
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, default=_json_default)
    print("★ 导出 %s" % out)
    print("  类 %d / 关系 %d / 动作 %d / 函数 %d"
          % (len(o.object_types), len(o.link_types), len(o.action_types), len(o.functions)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
