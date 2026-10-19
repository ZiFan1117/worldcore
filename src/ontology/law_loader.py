# -*- coding: utf-8 -*-
"""★ 声明件的 **解析 ＋ 校验 ＋ 建本体**（2026-10-19；定义方式抄借书平台）。

★ 唯一权威载体 = `src/ontology/world.json`（可用 `AIOS_LAW` 指向别处）。
★ 本件干三件事，顺序不许换：
  ① **解析**：读声明件（JSON，零外部依赖 —— 借书平台用 yaml/odl，我们用等价的数据件；
     换来的是**目标机不用装任何解析库**，与「能自足的不外引」一致）；
  ② **校验**：引用完整性、类型、接口符合性、动作契约（参数/前置条件/效果）、许可条文；
     **坏法必须在装载时报错**（不是运行到一半才发现）；
  ③ **建本体**：把声明件装成 foundry_ontology 的 Ontology 对象。
★ 生成物（手册／OWL／导出的 ontology.json）都从**同一份声明件**派生；改定义＝改声明件，不改正本代码。
"""
import json
import os

from foundry_ontology.core import (
    Ontology, ObjectType, Property, LinkType, Cardinality,
    ActionType, ActionParameter, OntologyFunction, Interface,
)
from foundry_ontology.core.data_types import PropertyType

from action_contract import EFFECT_KINDS, ON_FAILURE, PRECONDITION_KINDS

DEFAULT_LAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world.json")
PROPERTY_TYPES = {name: getattr(PropertyType, name) for name in (
    "STRING", "INTEGER", "FLOAT", "BOOLEAN", "OBJECT_REFERENCE")}
PROVIDER_KINDS = ("space", "presentation", "computer", "agent")
# ★ 前置条件：可判的（本体转发前真跑）／声明式（由执行器自检，进手册与账）
EVALUABLE = ("param_present", "param_in", "subject_exists", "provider_declared")


class LawError(Exception):
    """声明件不合法：装载即失败（坏法不许带病上岗）。"""


def law_path():
    return os.environ.get("AIOS_LAW") or DEFAULT_LAW


def load_law(path=None):
    """★ 读声明件 → 校验 → 建本体；坏法抛 LawError（列出全部错，不是第一条）。"""
    path = path or law_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            law = json.load(f)
    except FileNotFoundError:
        raise LawError("声明件不存在：%s（定义必须有一份声明件；见 src/ontology/world.json）" % path)
    except Exception as e:
        raise LawError("声明件不是合法 JSON：%s（%s）" % (path, e))
    errors = validate_law(law)
    if errors:
        raise LawError("声明件不合法（%d 处）：\n- %s" % (len(errors), "\n- ".join(errors)))
    return build_law(law)


# ── ① 校验 ──
def validate_law(law):
    """★ 纯函数：返回错误清单（空＝合法）。判据 C35 用它造反例。"""
    e = []
    if not isinstance(law, dict) or law.get("law_version") != 1:
        return ["law_version 必须是 1"]
    ometa = law.get("ontology") or {}
    if not ometa.get("id"):
        e.append("ontology.id 缺（本体要有身份）")

    # 接口
    ifaces = {i.get("id"): i for i in (law.get("interfaces") or [])}
    for iid, i in ifaces.items():
        if not iid:
            e.append("接口缺 id")
            continue
        for p in (i.get("required") or []):
            if p.get("type") not in PROPERTY_TYPES:
                e.append("接口 %s 的必需属性 %s：类型 %r 不在册" % (iid, p.get("name"), p.get("type")))

    # 对象类型
    types = {t.get("id"): t for t in (law.get("object_types") or [])}
    for tid, t in types.items():
        if not tid:
            e.append("对象类型缺 id")
            continue
        props = {p.get("name"): p for p in (t.get("properties") or [])}
        pk = t.get("primary_key")
        if not pk or pk not in props:
            e.append("%s：primary_key %r 不在属性里" % (tid, pk))
        for pn, p in props.items():
            if p.get("type") not in PROPERTY_TYPES:
                e.append("%s.%s：类型 %r 不在册" % (tid, pn, p.get("type")))
            if p.get("options") is not None and not isinstance(p.get("options"), list):
                e.append("%s.%s：options 不是数组" % (tid, pn))
        for iface in (t.get("interfaces") or []):
            spec = ifaces.get(iface)
            if spec is None:
                e.append("%s：实现了一个不存在的接口 %r" % (tid, iface))
                continue
            for rp in (spec.get("required") or []):
                got = props.get(rp.get("name"))
                if got is None or got.get("type") != rp.get("type"):
                    e.append("%s：接口 %s 要求属性 %s(%s)，但它没有/类型不符"
                             % (tid, iface, rp.get("name"), rp.get("type")))
        provider = t.get("provider")
        if provider is not None and provider not in PROVIDER_KINDS:
            e.append("%s：provider %r 不是已声明的执行者（%s）" % (tid, provider, PROVIDER_KINDS))
        auth = t.get("authority") or {}
        if auth and auth.get("kind") != "reported":
            e.append("%s：authority.kind=%r（今天只认 reported）" % (tid, auth.get("kind")))
        for r in (auth.get("reporters") or []):
            cls = r[len("world://"):].partition("/")[0] if isinstance(r, str) and r.startswith("world://") else ""
            if cls not in types:
                e.append("%s：提供者 %r 的类不在册" % (tid, r))

    # 关系
    for lt in (law.get("links") or []):
        if lt.get("source") not in types:
            e.append("关系 %s：source %r 不在册" % (lt.get("id"), lt.get("source")))
        if lt.get("target") not in types:
            e.append("关系 %s：target %r 不在册" % (lt.get("id"), lt.get("target")))
        if lt.get("cardinality") not in ("one_to_one", "one_to_many", "many_to_many"):
            e.append("关系 %s：cardinality %r 不在册" % (lt.get("id"), lt.get("cardinality")))

    # 动作
    seen = set()
    for a in (law.get("actions") or []):
        aid = a.get("id")
        if not aid or aid in seen:
            e.append("动作 id 缺/重复：%r" % (aid,))
            continue
        seen.add(aid)
        pnames = set()
        for p in (a.get("parameters") or []):
            pnames.add(p.get("name"))
            if p.get("type") not in PROPERTY_TYPES:
                e.append("%s：参数 %s 类型 %r 不在册" % (aid, p.get("name"), p.get("type")))
        at = a.get("applies_to")
        if isinstance(at, dict):
            if at.get("interface") and at["interface"] not in ifaces:
                e.append("%s：applies_to.interface %r 不在册" % (aid, at["interface"]))
            if at.get("class") and at["class"] not in types:
                e.append("%s：applies_to.class %r 不在册" % (aid, at["class"]))
        if a.get("on_failure") not in ON_FAILURE:
            e.append("%s：on_failure=%r 不在闭集 %s" % (aid, a.get("on_failure"), ON_FAILURE))
        for pre in (a.get("preconditions") or []):
            k = pre.get("kind")
            if k not in PRECONDITION_KINDS:
                e.append("%s：前置条件 kind=%r 不在册（%s）" % (aid, k, PRECONDITION_KINDS))
            elif k in ("param_present", "param_in") and pre.get("name") not in pnames:
                e.append("%s：前置条件引用了没声明的参数 %r" % (aid, pre.get("name")))
            elif k == "subject_implements" and pre.get("interface") not in ifaces:
                e.append("%s：subject_implements 的接口 %r 不在册" % (aid, pre.get("interface")))
            elif k == "provider_checks" and not pre.get("statement"):
                e.append("%s：provider_checks 必须写 statement（执行器自检什么）" % aid)
        for eff in (a.get("effects") or []):
            k = eff.get("kind")
            if k not in EFFECT_KINDS:
                e.append("%s：效果 kind=%r 不在册（%s）" % (aid, k, EFFECT_KINDS))
            elif k == "state_change" and not eff.get("of"):
                e.append("%s：state_change 必须写 of（改的是谁）" % aid)
        g = a.get("grant") or {}
        if not (g.get("who") and g.get("scope")):
            e.append("%s：许可条文 who/scope 必须都在（各非空）" % aid)

    # 函数
    fseen = set()
    for fn in (law.get("functions") or []):
        if not fn.get("id") or fn["id"] in fseen:
            e.append("函数 id 缺/重复：%r" % (fn.get("id"),))
        fseen.add(fn.get("id"))
        for k, v in (fn.get("input_types") or {}).items():
            if v not in PROPERTY_TYPES:
                e.append("函数 %s：入参 %s 类型 %r 不在册" % (fn.get("id"), k, v))
    return e


# ── ② 建本体 ──
def build_law(law):
    """★ 把（已校验过的）声明件装成 Ontology。"""
    ometa = law.get("ontology") or {}
    o = Ontology(ometa.get("id", "aios_world"), ometa.get("label", ""), str(ometa.get("version", "1")))
    o.metadata = dict(law.get("world") or {})

    for i in (law.get("interfaces") or []):
        o.register_interface(Interface(
            i["id"], i.get("label") or i["id"], i.get("description") or "",
            [Property(p["name"], p.get("label") or p["name"], PROPERTY_TYPES[p["type"]],
                      required=bool(p.get("required")))
             for p in (i.get("required") or [])]))

    for t in (law.get("object_types") or []):
        props = {}
        for p in (t.get("properties") or []):
            props[p["name"]] = Property(
                p["name"], p.get("label") or p["name"], PROPERTY_TYPES[p["type"]],
                required=bool(p.get("required")), description=p.get("description") or "",
                is_primary_key=bool(p.get("primary")), options=p.get("options"))
        md = dict(t.get("metadata") or {})
        if t.get("authority"):
            md["_authority"] = t["authority"]
        if t.get("provider"):
            md["provider"] = t["provider"]
        o.register_object_type(ObjectType(
            t["id"], t.get("label") or t["id"], description=t.get("description") or "",
            primary_key=t.get("primary_key") or "", metadata=md, properties=props,
            interfaces=list(t.get("interfaces") or [])))

    for lt in (law.get("links") or []):
        o.register_link_type(LinkType(
            lt["id"], lt.get("label") or lt["id"],
            source_type=lt["source"], target_type=lt["target"],
            cardinality=Cardinality(lt["cardinality"])))

    grants = o.metadata.setdefault("permissions", {}).setdefault("grants", {})
    for a in (law.get("actions") or []):
        md = dict(a.get("metadata") or {})
        for k in ("kind", "implemented", "reversible", "on_failure", "effects", "preconditions"):
            md[k] = a.get(k)
        if a.get("applies_to") is not None:
            md["applies_to"] = a["applies_to"]
        o.register_action_type(ActionType(
            a["id"], a.get("label") or a["id"], description=a.get("description") or "",
            parameters=[ActionParameter(p["name"], PROPERTY_TYPES[p["type"]],
                                        required=bool(p.get("required")),
                                        description=p.get("description") or "",
                                        options=p.get("options"))
                        for p in (a.get("parameters") or [])],
            validation_rules=[], effects=[], required_roles=list(a.get("required_roles") or []),
            metadata=md))
        g = a.get("grant") or {}
        grants[a["id"]] = {"who": list(g.get("who") or []), "scope": list(g.get("scope") or []),
                           "why": g.get("why") or ""}

    for fn in (law.get("functions") or []):
        o.register_function(OntologyFunction(
            fn["id"], fn.get("label") or fn["id"], description=fn.get("description") or "",
            input_types={k: PROPERTY_TYPES[v] for k, v in (fn.get("input_types") or {}).items()},
            output_type=PROPERTY_TYPES.get(fn.get("output_type")),
            implementation=fn.get("implementation"),
            metadata=dict(fn.get("metadata") or {})))

    # ★ 本体自带的引用完整性校验也要过（借来的库就带这道）
    bad = o.validate_ontology()
    if bad:
        raise LawError("建出来的本体不自洽：\n- %s" % "\n- ".join(bad))
    return o
