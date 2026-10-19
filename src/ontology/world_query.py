# -*- coding: utf-8 -*-
"""★ 查世界（`world/query`）—— ★ 从 `ontology_process.py` 拆出来（C27：一文件一块）。

★ 作者令（逐字整理）：「**查世界状态也要过本体**」「**查历史也要过本体**」；
  「有几个个体，有哪些 action，它们的关系是什么等等」。

★ 它是本体的一个【问法】，不是第二个本体：只读 `w.ontology` / `w.store` / `w.registry`，
  **不改世界、不记账、不转发动作**。
"""
import json


def handle(smp, w, session, log=print):
    """处理一条 `world/query`：按 `kind` 答，答在 `world/query/result`。"""
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    rid = msg.get("id")
    kind = msg.get("kind") or "world"
    try:
        if kind == "world":
            data = {"types": {}, "actions": sorted(w.ontology.action_types.keys()),
                    "registry": len(w.registry), "instances": {}}
            for tid in w.ontology.object_types:
                n = w.store.count(tid)
                data["types"][tid] = len(w.ontology.object_types[tid].properties)
                data["instances"][tid] = n
        elif kind == "actions":
            data = {"ontology": sorted(w.ontology.action_types.keys()),
                    "registry": sorted(w.registry.keys()),
                    # ★★ 计算机报的可用性（★ 模型据此只挑能跑的）
                    "available": sorted(w.computer_caps.get("available") or []),
                    "unsupported": sorted(w.computer_caps.get("unsupported") or []),
                    "reported_by": w.computer_caps.get("by")}
        elif kind == "types":
            data = {tid: sorted(ot.properties.keys()) for tid, ot in w.ontology.object_types.items()}
        elif kind == "type":
            tid = msg.get("type") or ""
            if tid not in w.ontology.object_types:
                raise ValueError("类型不在册：%s" % tid)
            rows = w.store.search(tid)
            data = [{"id": r.instance_id, "properties": r.properties} for r in rows]
        elif kind == "one":
            iid = msg.get("id_of") or msg.get("instance") or ""
            inst = w.store.get(iid)
            if inst is None:
                raise ValueError("个体不存在：%s" % iid)
            data = {"id": inst.instance_id, "type": inst.object_type_id,
                    "properties": inst.properties, "links": inst.links,
                    "created_by": inst.created_by}
        elif kind == "link":
            tid = msg.get("type") or ""
            lk = msg.get("link") or ""
            from foundry_ontology.engine.query_engine import OntologyQuery
            rows = OntologyQuery(w.store, tid).navigate(lk).all()
            data = {"link": lk, "count": len(rows),
                    "targets": [{"id": r.instance_id, "properties": r.properties} for r in rows]}
        else:
            raise ValueError("不认识的 kind：%s" % kind)
        out = {"id": rid, "kind": kind, "ok": True, "data": data}
        log("查世界 %s ⇒ ok（%d 字节）" % (kind, len(json.dumps(data, ensure_ascii=False))))
    except Exception as e:
        out = {"id": rid, "kind": kind, "ok": False, "why": str(e)}
        log("查世界 %s ⇒ 拒：%s" % (kind, e))
    session.put("world/query/result", json.dumps(out, ensure_ascii=False))
