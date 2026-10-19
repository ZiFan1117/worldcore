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
