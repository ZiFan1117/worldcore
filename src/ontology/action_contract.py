# -*- coding: utf-8 -*-
"""★ 动作契约：**参数校验** ＋ **失败策略**（2026-10-19；借自订单样板的「参数 schema → 机器可读拒绝码」）。

★ 借来的口径（`_scratch/palantir-open-source/code-notes/01-gura105.md` §D）：
  · 订单样板执行动作的顺序：**校验参数 → 鉴权 → 前置条件 → 效果 → 预演 → 提交**；
    「拒绝码是给机器看的」；参数不合就先拒，不往下走。
  · 我们上一版**根本没有参数级校验**（本体只认名字、判许可，参数原样转给执行器）——
    执行器再发现「缺参数」时，账上已经记了一笔 ask，责任也模糊。
★ 本件只做第一层（参数）：必填齐、取值域、粗类型；**不拒多余参数**（不比 zod 严）。
★ `on_failure`：失败策略闭集（今天只有 `reject`）；`effects`：效果清单（今天留空，逐个动作定＝待人裁）。
"""
# ★ 失败策略闭集：今天只有「拒」；补偿/重试/忽略 要人裁后才加。
ON_FAILURE = ("reject",)

# ★★ 前置条件与效果：也是动作契约的一部分（借自订单样板：条件/效果写在动作上，不是散在执行器里）
#   · 可判的（本体在转发前真跑）：参数在不在、取值、对象在不在、该类有没有执行者；
#   · 声明式的（由执行器自检，写进手册与账）：provider_checks／actor_*／ticket 细节。
PRECONDITION_KINDS = ("param_present", "param_in", "subject_implements", "subject_exists",
                      "provider_declared", "actor_in_scope", "actor_appeared", "provider_checks")
EVALUABLE_PRECONDITIONS = ("param_present", "param_in", "subject_implements", "subject_exists", "provider_declared")
EFFECT_KINDS = ("forward", "ledger", "state_change", "provider_report", "ticket_issued", "notify")

# ★ 按【类型名】查表（不 import foundry —— 本模块会被多个进程在 path 未就绪时导入）
_TYPE_CHECKS = {
    "STRING": (str,),
    "INTEGER": (int,),
    "FLOAT": (int, float),
    "BOOLEAN": (bool,),
}


def load_action_contracts(o):
    """给每个动作补声明：`on_failure`（闭集，默认 reject）＋ `effects`（默认空表）。"""
    for at in o.action_types.values():
        md = dict(getattr(at, "metadata", None) or {})
        md.setdefault("on_failure", "reject")
        md.setdefault("effects", [])
        md.setdefault("preconditions", [])
        at.metadata = md


def validate_params(at, params):
    """★ 参数校验（本体侧、转发之前）：必填齐、取值域、粗类型。

    ★ 返回 (True, None, None) 或 (False, 为什么, 拒绝码)。
    ★ 不拒「多余参数」（zod 默认 strip）；不查深层结构 —— 限度写清，不夸大。
    """
    params = params or {}
    if not isinstance(params, dict):
        return False, "params 不是对象", "PARAM_INVALID"
    declared = list(getattr(at, "parameters", None) or [])
    missing = [p.name for p in declared
               if getattr(p, "required", False) and p.name not in params]
    if missing:
        return False, "缺必填参数：%s" % missing, "PARAM_MISSING"
    for p in declared:
        if p.name not in params:
            continue
        v = params[p.name]
        opts = getattr(p, "options", None)
        if opts and v not in opts:
            return False, "参数 %s=%r 不在 %s 里" % (p.name, v, opts), "PARAM_INVALID"
        _pt = getattr(getattr(p, "param_type", None), "name", getattr(p, "param_type", None))
        types = _TYPE_CHECKS.get(_pt)
        if types and not isinstance(v, types):
            return False, ("参数 %s 类型不对（要 %s，实得 %s）"
                           % (p.name, "/".join(t.__name__ for t in types), type(v).__name__)), "PARAM_INVALID"
    return True, None, None


def _split_subject(params):
    """`subject` 参数写成 <类>/<名>（如 space/zhang）。"""
    s = (params or {}).get("subject") or ""
    cls, _, name = s.partition("/")
    return cls, name


def check_preconditions(at, world, params):
    """★ 前置条件求值（转发之前）。

    ★ 返回 (ok, why, code, declared)：`declared` ＝ 声明式条件（由执行器自检；进账/手册）。
    ★ 可判的四类真跑；其余只登记，不假装判过（限度写在这里，不写进报告）。
    """
    declared = []
    preconds = (getattr(at, "metadata", None) or {}).get("preconditions") or []
    for pre in preconds:
        kind = pre.get("kind")
        if kind == "param_present":
            if (params or {}).get(pre.get("name")) in (None, ""):
                return False, "前置条件不成立：缺参数 %s" % pre.get("name"), "PARAM_MISSING", declared
        elif kind == "param_in":
            v = (params or {}).get(pre.get("name"))
            if v not in (pre.get("values") or []):
                return False, ("前置条件不成立：%s=%r 不在 %s"
                               % (pre.get("name"), v, pre.get("values"))), "PRECONDITION_FAILED", declared
        elif kind == "subject_implements":
            cls, _name = _split_subject(params)
            iface = pre.get("interface")
            ot = world.ontology.object_types.get(cls)
            if ot is None or iface not in (getattr(ot, "interfaces", None) or []):
                return False, ("「%s」不实现接口 %s（不能当它用）" % (cls, iface)), \
                    "INTERFACE_NOT_IMPLEMENTED", declared
        elif kind == "subject_exists":
            cls, name = _split_subject(params)
            if not cls or not name:
                return False, "前置条件不成立：subject 要写成 <类>/<名>", "PRECONDITION_FAILED", declared
            if not world.store.search(cls, {"name": name}):
                return False, "前置条件不成立：世界没有 %s/%s" % (cls, name), "PRECONDITION_FAILED", declared
        elif kind == "provider_declared":
            cls, _name = _split_subject(params)
            ot = world.ontology.object_types.get(cls) if cls else None
            provider = ((getattr(ot, "metadata", None) or {}).get("provider") if ot else None)
            if not provider:
                return False, "「%s」没有声明执行者（provider）" % (cls,), "PROVIDER_NOT_DECLARED", declared
        else:
            declared.append(pre)          # 声明式：provider_checks／actor_*（由执行器或既有闸自检）
    return True, None, None, declared


def route_for(world, action_id, reg, params):
    """★ 多态路由：动作声明了 `applies_to.interface` ⇒ 按【对象类型】的执行者走，不看注册路由。

    ★ 返回 {"kind", "polymorphic", "subject_class", "subject"}。
    """
    at = world.ontology.action_types.get(action_id)
    applies = ((getattr(at, "metadata", None) or {}).get("applies_to") if at else None) or {}
    if isinstance(applies, dict) and applies.get("interface"):
        subject = (params or {}).get("subject") or ""
        cls, _, _name = subject.partition("/")
        ot = world.ontology.object_types.get(cls)
        provider = ((getattr(ot, "metadata", None) or {}).get("provider") if ot else None)
        return {"kind": provider, "polymorphic": True, "subject_class": cls, "subject": subject}
    return {"kind": (reg or {}).get("registered_by_kind"), "polymorphic": False}
