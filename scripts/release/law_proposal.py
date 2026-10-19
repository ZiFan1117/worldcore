#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 法提案校验器（待签草案 → 可合并的片段）——把《提案-记忆系统》《提案-人确认与委托》变成机器可查的 JSON 草案。

★ 作者令：「法只有人能签」；本工具**不改法**，只校验草案：
  - id 不与现行法冲突；对象字段类型/接口/主键合法；动作的 kind/roles/effects/preconditions/parameters/grant 合法。
★ 用法：
  python3 law_proposal.py --check src/ontology/proposals/memory.proposal.json
  # rc=0 表示「这份草案与现行法同构，作者签了就能合并」；rc=1 有错误清单。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LAW = os.environ.get("AIOS_LAW_JSON", os.path.join(ROOT, "src", "ontology", "world.json"))

PROP_TYPES = {"STRING", "INTEGER", "OBJECT_REFERENCE"}
ROLES = {"agent", "human", "user", "space", "computer", "presentation", "presence", "device",
         "port", "application", "service", "workflow", "ledger", "memory"}
EFFECT_KINDS = {"forward", "ledger", "state_change", "notify"}
PRECOND_KINDS = {"param_present"}
KINDS = {"invoke", "config"}
AUTH_KINDS = {"reported", "signed", "derived", "observed"}


def load_law(path=None):
    with open(path or LAW, encoding="utf-8") as f:
        return json.load(f)


def check(proposal, law):
    bad = []
    ot_ids = {o.get("id") for o in law.get("object_types") or []}
    ac_ids = {a.get("id") for a in law.get("actions") or []}
    ifaces = {i.get("id") for i in law.get("interfaces") or []}
    p_ot = proposal.get("object_types") or []
    p_ac = proposal.get("actions") or []
    seen = set()
    for o in p_ot:
        oid = o.get("id") or "?"
        if oid in ot_ids:
            bad.append("对象类型 id 与现行法冲突：%s" % oid)
        if oid in seen:
            bad.append("对象类型 id 在草案里重复：%s" % oid)
        seen.add(oid)
        pk = o.get("primary_key")
        props = o.get("properties") or []
        names = [p.get("name") for p in props]
        if pk not in names:
            bad.append("%s 的 primary_key=%r 不在 properties 里" % (oid, pk))
        if not any(p.get("primary") for p in props):
            bad.append("%s 没有 primary 字段" % oid)
        for p in props:
            if p.get("type") not in PROP_TYPES:
                bad.append("%s.%s 类型不合法：%r" % (oid, p.get("name"), p.get("type")))
            if not p.get("name"):
                bad.append("%s 有属性缺 name" % oid)
        for i in o.get("interfaces") or []:
            if i not in ifaces:
                bad.append("%s 接口不在现行法里：%s" % (oid, i))
        auth = o.get("authority") or {}
        if auth.get("kind") and auth["kind"] not in AUTH_KINDS:
            bad.append("%s authority.kind 不合法：%r" % (oid, auth["kind"]))
    for a in p_ac:
        aid = a.get("id") or "?"
        if aid in ac_ids:
            bad.append("动作 id 与现行法冲突：%s" % aid)
        if aid in seen:
            bad.append("动作 id 在草案里重复：%s" % aid)
        seen.add(aid)
        if a.get("kind") not in KINDS:
            bad.append("%s kind 不合法：%r" % (aid, a.get("kind")))
        if not a.get("implemented"):
            bad.append("%s 没写 implemented" % aid)
        for r in a.get("required_roles") or []:
            if r not in ROLES:
                bad.append("%s required_roles 不合法：%r" % (aid, r))
        g = a.get("grant") or {}
        if not (g.get("who") or []):
            bad.append("%s grant.who 为空" % aid)
        if not (g.get("scope") or []):
            bad.append("%s grant.scope 为空（没生效许可）" % aid)
        for p in a.get("parameters") or []:
            if p.get("type") not in PROP_TYPES:
                bad.append("%s.%s 参数类型不合法：%r" % (aid, p.get("name"), p.get("type")))
        for e in a.get("effects") or []:
            if e.get("kind") not in EFFECT_KINDS:
                bad.append("%s effect.kind 不合法：%r" % (aid, e.get("kind")))
        for pc in a.get("preconditions") or []:
            if pc.get("kind") not in PRECOND_KINDS:
                bad.append("%s precondition.kind 不合法：%r" % (aid, pc.get("kind")))
        if a.get("reversible") not in (True, False, None):
            bad.append("%s reversible 不是布尔" % aid)
        if a.get("on_failure") not in ("reject", None):
            bad.append("%s on_failure 不合法：%r" % (aid, a.get("on_failure")))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="law proposal checker")
    ap.add_argument("--check", required=True, dest="path")
    ap.add_argument("--law")
    a = ap.parse_args(argv)
    try:
        with open(a.path, encoding="utf-8") as f:
            proposal = json.load(f)
    except Exception as e:
        print("拒：读不了草案 %s（%s）" % (a.path, e))
        return 1
    law = load_law(a.law)
    bad = check(proposal, law)
    print("proposal=%s object_types=%d actions=%d errors=%d"
          % (proposal.get("proposal") or os.path.basename(a.path),
             len(proposal.get("object_types") or []), len(proposal.get("actions") or []),
             len(bad)))
    for b in bad:
        print("  [红] " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
