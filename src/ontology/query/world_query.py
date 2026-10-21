# -*- coding: utf-8 -*-
"""★ 查世界（`world/query`）—— ★ 从 `ontology_process.py` 拆出来（C27：一文件一块）。

★ 作者令（逐字整理）：「**查世界状态也要过本体**」「**查历史也要过本体**」；
  「有几个个体，有哪些 action，它们的关系是什么等等」。

★ 它是本体的一个【问法】，不是第二个本体：只读 `w.ontology` / `w.store` / `w.registry` / **账**，
  **不改世界、不记账、不转发动作**。

★★ 2026-10-19 补 `kind="history"`：作者令「**查历史也要过本体**」。历史从【账】翻（不另造一份），
  成功与被拒两侧都在（借自订单样板：每次尝试都留痕）。
"""
import json
import os
import time

from gate import identity
from world_functions import NEEDS_VIEWER, dispatch as function_dispatch  # noqa: E402


def read_ledger(path):
    """★ 从账本读回历史（只读；坏行跳过但计数）。"""
    rows, bad = [], 0
    if not path or not os.path.exists(path):
        return rows, bad
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                bad += 1
    return rows, bad


def viewer_of(msg, w):
    """★ 查账也要能核身份：票优先（人），其次已报到的 actor（进程/agent）。

    ★ 返回 (viewer, 自己空间, 失败原因)。★ 匿名查历史/个体 ⇒ 拒（作者：不能让谁都能翻账）。
    """
    tk = msg.get("ticket")
    if not tk and isinstance(msg.get("params"), dict):
        tk = msg["params"].get("ticket")
    if tk:
        t, why = identity.check({"ticket": tk})
        if t is None:
            return None, None, why
        who = t.get("who") or ""
        cls, _, name = who[len("world://"):].partition("/")
        return who, ("space:" + name if cls == "user" else None), None
    actor = msg.get("actor") or ""
    if actor:
        ok, why, _code = identity.actor_ok(actor, False, w.appeared)
        if not ok:
            return None, None, why
        cls, _, name = actor[len("world://"):].partition("/")
        if cls in ("user", "space"):
            return actor, "space:" + name, None
        return actor, None, None
    return None, None, "查账要带票或 actor（★ 不能匿名翻账）"


def row_space(row, w):
    """★ 这一行属于哪个空间：人/空间进程 ⇒ 自己的空间；agent ⇒ 当前登录人的空间（单用户假设）。"""
    actor = row.get("actor") or ""
    if not actor.startswith("world://"):
        return None
    cls, _, name = actor[len("world://"):].partition("/")
    if cls in ("user", "space"):
        return "space:" + name
    if cls == "agent":
        for t in (getattr(identity, "_TICKETS", {}) or {}).values():
            if (t.get("expires_at") or 0) > time.time():
                return "space:" + (t.get("user") or "")
        return None
    return None


def visible_rows(rows, viewer, vspace, w):
    """★ 读闸：只留 viewer 自己的、或 viewer 空间的行。"""
    out = []
    for r in rows:
        if r.get("actor") == viewer:
            out.append(r)
            continue
        s = row_space(r, w)
        if s and s == vspace:
            out.append(r)
    return out


def applied(r):
    """★ 这一笔算「成了」吗？（ask/register/notice 是尝试本身；result 看 ok）"""
    return r.get("kind_of") in ("ask", "register", "notice", "appear") or (
        r.get("kind_of") == "result" and r.get("ok") is True)


def rejected(r):
    """★ 这一笔算「被拒」吗？（reject 行；或 ok=False 的 result）"""
    return r.get("kind_of") == "reject" or (
        r.get("kind_of") == "result" and r.get("ok") is False)


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
            _v, _s, why_v = viewer_of(msg, w)
            if _v is None:
                raise ValueError("查个体要能核身份：%s" % why_v)
            tid = msg.get("type") or ""
            if tid not in w.ontology.object_types:
                raise ValueError("类型不在册：%s" % tid)
            rows = w.store.search(tid)
            data = [{"id": r.instance_id, "properties": r.properties} for r in rows]
        elif kind == "one":
            _v2, _s2, why_v2 = viewer_of(msg, w)
            if _v2 is None:
                raise ValueError("查个体要能核身份：%s" % why_v2)
            iid = msg.get("id_of") or msg.get("instance") or ""
            inst = w.store.get(iid)
            if inst is None:
                raise ValueError("个体不存在：%s" % iid)
            data = {"id": inst.instance_id, "type": inst.object_type_id,
                    "properties": inst.properties, "links": inst.links,
                    "created_by": inst.created_by}
        elif kind == "link":
            _v3, _s3, why_v3 = viewer_of(msg, w)
            if _v3 is None:
                raise ValueError("沿关系查要能核身份：%s" % why_v3)
            tid = msg.get("type") or ""
            lk = msg.get("link") or ""
            from foundry_ontology.engine.query_engine import OntologyQuery
            rows = OntologyQuery(w.store, tid).navigate(lk).all()
            data = {"link": lk, "count": len(rows),
                    "targets": [{"id": r.instance_id, "properties": r.properties} for r in rows]}
        elif kind == "history":
            # ★★ 查历史（作者令「查历史也要过本体」）：过滤条件取 filter 或顶层同名字段
            flt = msg.get("filter") or {}
            rows, bad_lines = read_ledger(getattr(w.ledger, "name", "") or "")
            # ★★ 读闸：只能看自己的、或自己空间里的事（别人的空间不给看）
            viewer, vspace, why_v = viewer_of(msg, w)
            if viewer is None:
                raise ValueError("查历史要能核身份：%s" % why_v)
            rows = visible_rows(rows, viewer, vspace, w)
            for k in ("actor", "action", "code", "kind_of", "permit", "subject", "category"):
                v = flt.get(k) if k in flt else msg.get(k)
                if v:
                    rows = [r for r in rows if r.get(k) == v]
            since = flt.get("since") or msg.get("since")
            if since:
                rows = [r for r in rows if str(r.get("at") or "") >= str(since)]
            until = flt.get("until") or msg.get("until")
            if until:
                rows = [r for r in rows if str(r.get("at") or "") <= str(until)]
            limit = int(flt.get("limit") or msg.get("limit") or 50)
            limit = max(1, min(limit, 500))
            tail = rows[-limit:]
            data = {"count": len(tail), "total": len(rows), "bad_lines": bad_lines,
                    "viewer": viewer, "space": vspace,
                    "applied": len([r for r in tail if applied(r)]),
                    "rejected": len([r for r in tail if rejected(r)]),
                    "rows": tail}
        elif kind == "events":
            # ★★ 事件回放（P8 补漏）：从账里取最近事件，按身份/空间过滤，缩成事件形状
            viewer, vspace, why_v = viewer_of(msg, w)
            if viewer is None:
                raise ValueError("查事件要能核身份：%s" % why_v)
            rows, bad_lines = read_ledger(getattr(w.ledger, "name", "") or "")
            cand = [r for r in rows
                    if r.get("kind_of") in ("ask", "reject", "result", "appear", "register")
                    or (r.get("kind_of") == "notice" and r.get("notice_kind") == "ui.act")]
            rows = visible_rows(cand, viewer, vspace, w)
            # ★ ui.act 是「人的公开动作」事件（notice 行没有 actor）⇒ 回放时对所有已核身份可见
            rows += [r for r in cand if r not in rows and r.get("notice_kind") == "ui.act"]
            rows.sort(key=lambda r: str(r.get("at") or ""))
            # ★ P8 精确续传（2026-10-20）：since 之后的事件（严格大于，避免重复回放游标那条）
            since = msg.get("since") or (msg.get("filter") or {}).get("since")
            if since:
                rows = [r for r in rows if str(r.get("at") or "") > str(since)]
            limit = int(msg.get("limit") or 50)
            limit = max(1, min(limit, 500))
            tail = rows[-limit:]
            evs = []
            for r in tail:
                evs.append({"at": r.get("at"), "kind_of": r.get("kind_of"),
                            "action": r.get("action") or r.get("ui_action"),
                            "actor": r.get("actor"), "ok": r.get("ok"),
                            "code": r.get("code"), "category": r.get("category"),
                            "space": row_space(r, w)})
            cursor = (tail[-1].get("at") if tail else
                      (rows[-1].get("at") if rows else (since or None)))
            data = {"count": len(evs), "total": len(rows), "bad_lines": bad_lines,
                    "viewer": viewer, "space": vspace, "events": evs,
                    "cursor": cursor}
        elif kind == "function":
            name = str(msg.get("name") or msg.get("function") or
                       (msg.get("params") or {}).get("name") or "")
            if not name:
                raise ValueError("查函数要带 name")
            if name not in w.ontology.functions:
                raise ValueError("函数不在册：%s" % name)
            _viewer = None
            if name in NEEDS_VIEWER:
                _viewer, _vspace, why_v = viewer_of(msg, w)
                if _viewer is None:
                    raise ValueError("这个函数要能核身份：%s" % why_v)
            _ok, _body = function_dispatch(w, name, msg.get("params") or {}, _viewer)
            if not _ok:
                raise ValueError(str(_body))
            data = {"function": name, "result": _body}
        elif kind == "overview":
            # ★★ 本体「一眼看全」：给本体窗口用（类/接口/关系/动作/个体/注册表/账）
            classes = {}
            for tid, ot in w.ontology.object_types.items():
                classes[tid] = {
                    "label": getattr(ot, "display_name", "") or tid,
                    "instances": w.store.count(tid),
                    "interfaces": list(getattr(ot, "interfaces", None) or []),
                    "provider": ((getattr(ot, "metadata", None) or {}).get("provider")),
                }
            rows, bad = read_ledger(getattr(w.ledger, "name", "") or "")
            codes = {}
            for r in rows:
                if r.get("kind_of") == "reject":
                    c = r.get("code") or "?"
                    codes[c] = codes.get(c, 0) + 1
            data = {
                "classes": classes,
                "counts": {
                    "classes": len(w.ontology.object_types),
                    "interfaces": len(w.ontology.interfaces),
                    "links": len(w.ontology.link_types),
                    "world_actions": len(w.ontology.action_types),
                    "registry_actions": len(w.registry),
                    "functions": len(w.ontology.functions),
                    "individuals": sum(v["instances"] for v in classes.values()),
                },
                "interfaces": {
                    iid: {"required": [p.name for p in (getattr(iface, "required_properties", None) or [])],
                          "implementors": [tid for tid, ot in w.ontology.object_types.items()
                                           if iid in (getattr(ot, "interfaces", None) or [])]}
                    for iid, iface in w.ontology.interfaces.items()},
                "ledger": {"rows": len(rows), "bad_lines": bad,
                           "reject_codes": dict(sorted(codes.items(), key=lambda kv: -kv[1])[:8]),
                           "last": rows[-8:]},
                # ★ 2026-10-20：本体窗口要「全部信息」⇒ overview 带关系/函数/法的版本
                "links": [{"id": lid,
                           "source": getattr(lt, "source_type", None),
                           "target": getattr(lt, "target_type", None),
                           "cardinality": str(getattr(lt, "cardinality", ""))}
                          for lid, lt in w.ontology.link_types.items()],
                "functions": sorted(w.ontology.functions.keys()),
                "law_version": getattr(w.ontology, "version", ""),
            }
        else:
            raise ValueError("不认识的 kind：%s" % kind)
        out = {"id": rid, "kind": kind, "ok": True, "data": data}
        log("查世界 %s ⇒ ok（%d 字节）" % (kind, len(json.dumps(data, ensure_ascii=False))))
    except Exception as e:
        out = {"id": rid, "kind": kind, "ok": False, "why": str(e)}
        log("查世界 %s ⇒ 拒：%s" % (kind, e))
    session.put("world/query/result", json.dumps(out, ensure_ascii=False))
