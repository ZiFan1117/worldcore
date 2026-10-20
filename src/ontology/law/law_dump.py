# -*- coding: utf-8 -*-
"""★ 把「本体这份法」导成**声明件**（2026-10-19；照借书平台的定义方式）。

★ 为什么要有它：定义方式抄借书平台 ⇒ **声明件是唯一权威载体**，代码只负责解析、校验、生成。
  · `world.json` 是法（人可审、可 diff、可单独校验）；
  · 代码（`law_loader.py`）读它；`手册`／`OWL`／`导出的 ontology.json` 都是生成物。

★ 本件只做「本体 → 声明件」这一向（构建产物；不手改）。反向的「声明件 → 本体」在 `law_loader.py`。
"""
# 本体里由【运行时】补出来的东西（sys.* 动作）不写进法里：它们来自映射表，本身也是声明件。
_RUNTIME_IMPL = "sysknife"


def _prop(p):
    return {
        "name": p.name,
        "label": p.display_name or p.name,
        "type": getattr(getattr(p, "property_type", None), "name", "STRING"),
        "required": bool(getattr(p, "required", False)),
        "primary": bool(getattr(p, "is_primary_key", False)),
        "options": getattr(p, "options", None),
        "description": getattr(p, "description", "") or "",
    }


def _param(p):
    return {
        "name": p.name,
        "type": getattr(getattr(p, "param_type", None), "name", "STRING"),
        "required": bool(getattr(p, "required", False)),
        "options": getattr(p, "options", None),
        "description": getattr(p, "description", "") or "",
    }


def _action_meta(at):
    md = dict(getattr(at, "metadata", None) or {})
    return {
        "kind": md.pop("kind", None),
        "implemented": md.pop("implemented", None),
        "reversible": md.pop("reversible", None),
        "on_failure": md.pop("on_failure", "reject"),
        "effects": md.pop("effects", []),
        "preconditions": md.pop("preconditions", []),
        "applies_to": md.pop("applies_to", None),
        "metadata": md,          # 剩下的是各动作自己的补充（如 not_roles／what）
    }


def dump_law(o, interfaces=None):
    """★ 本体 → 声明件（纯数据）。`interfaces` 不给时从本体取。"""
    grants = ((o.metadata or {}).get("permissions") or {}).get("grants") or {}
    world = dict(o.metadata or {})
    permissions = dict(world.get("permissions") or {})
    permissions.pop("grants", None)        # ★ 许可条文跟动作走，不散在世界元数据里
    world["permissions"] = permissions

    if interfaces is None:
        interfaces = [{
            "id": i.interface_id,
            "label": i.display_name or i.interface_id,
            "description": i.description or "",
            "required": [_prop(p) for p in (i.required_properties or [])],
        } for i in (o.interfaces or {}).values()]

    types = []
    for tid, ot in o.object_types.items():
        md = dict(getattr(ot, "metadata", None) or {})
        authority = md.pop("_authority", None)
        provider = md.pop("provider", None)
        types.append({
            "id": tid,
            "label": getattr(ot, "display_name", "") or tid,
            "description": getattr(ot, "description", "") or "",
            "primary_key": getattr(ot, "primary_key", "") or "",
            "interfaces": list(getattr(ot, "interfaces", None) or []),
            "provider": provider,
            "authority": authority,
            "metadata": md,
            "properties": [_prop(p) for p in (getattr(ot, "properties", None) or {}).values()],
        })

    links = [{
        "id": lt.link_id,
        "label": getattr(lt, "display_name", "") or lt.link_id,
        "source": getattr(lt, "source_type", ""),
        "target": getattr(lt, "target_type", ""),
        "cardinality": getattr(getattr(lt, "cardinality", None), "value", None),
    } for lt in o.link_types.values()]

    actions = []
    for aid, at in o.action_types.items():
        meta = _action_meta(at)
        if meta["implemented"] == _RUNTIME_IMPL:
            continue                       # sys.* 由映射表补，不进法
        g = grants.get(aid) or {}
        actions.append({
            "id": aid,
            "label": getattr(at, "display_name", "") or aid,
            "description": getattr(at, "description", "") or "",
            "required_roles": list(getattr(at, "required_roles", None) or []),
            "applies_to": meta["applies_to"],
            **{k: meta[k] for k in ("kind", "implemented", "reversible",
                                    "on_failure", "effects", "preconditions")},
            "parameters": [_param(p) for p in (getattr(at, "parameters", None) or [])],
            "grant": {"who": list(g.get("who") or []), "scope": list(g.get("scope") or []),
                      "why": g.get("why") or ""},
            "metadata": meta["metadata"],
        })

    functions = [{
        "id": fn.function_id,
        "label": getattr(fn, "display_name", "") or fn.function_id,
        "description": getattr(fn, "description", "") or "",
        "input_types": {k: getattr(v, "name", str(v)) for k, v in
                        (getattr(fn, "input_types", None) or {}).items()},
        "output_type": getattr(getattr(fn, "output_type", None), "name", None),
        "implementation": getattr(fn, "implementation", None),
        "metadata": dict(getattr(fn, "metadata", None) or {}),
    } for fn in o.functions.values()]

    return {
        "law_version": 1,
        "ontology": {"id": o.ontology_id, "label": o.display_name, "version": str(o.version)},
        "world": world,
        "interfaces": interfaces,
        "object_types": types,
        "links": links,
        "actions": actions,
        "functions": functions,
    }
