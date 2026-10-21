# -*- coding: utf-8 -*-
"""★ ontology 的只读 function 层（P1：该读的读、该统计的统计）。

这些函数**只读**：不写世界、不落账、不转发动作；由 `world/query kind="function"` 调用。
统计类函数不要求票（只返回计数/汇总）；对象读类函数要求票/已报到身份。
"""
import collections
import os

NEEDS_VIEWER = frozenset(("fn.object.get", "fn.object.find"))


def _ledger_rows(w):
    rows, bad = [], 0
    path = getattr(getattr(w, "ledger", None), "name", "") or ""
    if not path or not os.path.exists(path):
        return rows, bad
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                import json
                rows.append(json.loads(line))
            except Exception:                                   # noqa: BLE001
                bad += 1
    return rows, bad


def _instances(w):
    out = {}
    for tid in w.ontology.object_types:
        try:
            out[tid] = w.store.count(tid)
        except Exception:                                       # noqa: BLE001
            out[tid] = 0
    return out


def fn_world_overview(w, params=None, viewer=None):
    rows, bad = _ledger_rows(w)
    inst = _instances(w)
    return True, {
        "classes": len(w.ontology.object_types),
        "interfaces": len(w.ontology.interfaces),
        "links": len(w.ontology.link_types),
        "world_actions": len(w.ontology.action_types),
        "functions": len(w.ontology.functions),
        "registry_actions": len(w.registry),
        "individuals": sum(inst.values()),
        "instances": inst,
        "ledger_rows": len(rows),
        "bad_lines": bad,
        "last_ledger_at": (rows[-1].get("at") if rows else None),
    }


def fn_class_counts(w, params=None, viewer=None):
    inst = _instances(w)
    return True, {"count": len(inst),
                  "classes": {k: v for k, v in sorted(inst.items())}}


def fn_ledger_stats(w, params=None, viewer=None):
    rows, bad = _ledger_rows(w)
    fam = collections.Counter(r.get("family") for r in rows)
    kinds = collections.Counter(r.get("kind_of") for r in rows)
    codes = collections.Counter(r.get("code") for r in rows if r.get("kind_of") == "reject")
    return True, {
        "rows": len(rows), "bad_lines": bad,
        "first_at": (rows[0].get("at") if rows else None),
        "last_at": (rows[-1].get("at") if rows else None),
        "families": dict(fam),
        "kinds": dict(kinds),
        "reject_codes": dict(codes.most_common(20)),
    }


def fn_action_stats(w, params=None, viewer=None):
    avail = sorted(w.computer_caps.get("available") or [])
    unsup = sorted(w.computer_caps.get("unsupported") or [])
    return True, {
        "world_actions": len(w.ontology.action_types),
        "registry_actions": len(w.registry),
        "available": len(avail), "unsupported": len(unsup),
        "reported_by": w.computer_caps.get("by"),
    }


def fn_object_get(w, params=None, viewer=None):
    if viewer is None:
        return False, "查对象要带票或已报到身份"
    params = params if isinstance(params, dict) else {}
    cls = str(params.get("class") or params.get("type") or "")
    name = str(params.get("name") or params.get("id") or "")
    if not cls or not name:
        return False, "缺 class/name"
    if cls not in w.ontology.object_types:
        return False, "类不在册：%s" % cls
    inst = w.store.get(name) or w.store.get("%s/%s" % (cls, name))
    if inst is None:
        rows = [r for r in w.store.search(cls) if r.properties.get("name") == name]
        inst = rows[0] if rows else None
    if inst is None:
        return False, "对象不存在：%s/%s" % (cls, name)
    if inst.object_type_id != cls:
        return False, "对象类型不符：%s" % inst.object_type_id
    return True, {"id": inst.instance_id, "class": cls, "properties": inst.properties}


def fn_object_find(w, params=None, viewer=None):
    if viewer is None:
        return False, "查对象要带票或已报到身份"
    params = params if isinstance(params, dict) else {}
    cls = str(params.get("class") or params.get("type") or "")
    if cls not in w.ontology.object_types:
        return False, "类不在册：%s" % cls
    where = params.get("where") or params.get("filter") or {}
    if not isinstance(where, dict):
        return False, "where 要是对象"
    try:
        lim = max(1, min(int(params.get("limit") or 50), 100))
    except (TypeError, ValueError):
        lim = 50
    rows = []
    for inst in w.store.search(cls):
        if all(inst.properties.get(k) == v for k, v in where.items()):
            rows.append({"id": inst.instance_id, "properties": inst.properties})
            if len(rows) >= lim:
                break
    return True, {"class": cls, "count": len(rows), "limit": lim, "rows": rows}


def fn_file_stats(w, params=None, viewer=None):
    rows = [i for i in w.store.search("file")]
    kinds = collections.Counter(i.properties.get("kind") for i in rows)
    roots = collections.Counter(i.properties.get("root") for i in rows)
    total = sum(int(i.properties.get("size") or 0) for i in rows)
    return True, {"objects": len(rows), "kinds": dict(kinds),
                  "roots": dict(roots), "bytes": total}


def fn_worldfs_stats(w, params=None, viewer=None):
    out = {}
    for cls in ("wfile", "wversion", "wpath"):
        if cls not in w.ontology.object_types:
            out[cls] = {"count": 0, "missing_class": True}
            continue
        rows = list(w.store.search(cls))
        item = {"count": len(rows)}
        if cls == "wfile":
            item["kinds"] = dict(collections.Counter(r.properties.get("kind") for r in rows))
            item["states"] = dict(collections.Counter(r.properties.get("state") for r in rows))
            item["bytes"] = sum(int(r.properties.get("size") or 0) for r in rows)
        out[cls] = item
    return True, out


FUNCTIONS = {
    "fn.world.overview": fn_world_overview,
    "fn.world.class_counts": fn_class_counts,
    "fn.ledger.stats": fn_ledger_stats,
    "fn.action.stats": fn_action_stats,
    "fn.object.get": fn_object_get,
    "fn.object.find": fn_object_find,
    "fn.file.stats": fn_file_stats,
    "fn.worldfs.stats": fn_worldfs_stats,
}


def dispatch(w, name, params=None, viewer=None):
    fn = FUNCTIONS.get(name)
    if fn is None:
        return False, "函数不在册：%s" % name
    try:
        return fn(w, params or {}, viewer)
    except Exception as e:                                      # noqa: BLE001
        return False, "函数执行异常：%s" % e
