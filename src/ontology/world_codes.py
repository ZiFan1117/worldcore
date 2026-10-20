# -*- coding: utf-8 -*-
"""★ 世界里的两张「闭集表」：拒绝码 ＋ 状态所有权（2026-10-19）。

借自两个「Palantir 开源版」参考件：
  · 拒绝码分类（业务／身份／权限／输入／系统）—— 订单样板 `gura105/operational-ontology` 的做法：
    「拒绝码是给机器看的，不是给人看的」；每类分开，调用方才能判断该改参数、找人授权还是报警。
  · 状态所有权（每类的事实只许它的提供者报）—— 同件的「状态必须有主人」＋ `open-foundry` 的权威线。

★ 为什么单独一个文件：`ontology_definition.py` 已到 C27 的行数上限；这两张表是**闭集**，
  放这里的另一好处是：判据（C29/C30）可以只读这两张表，不必解析整份本体。
"""
# ── 拒绝码闭集 ──
REJECT_CATEGORIES = ("business", "identity", "permission", "input", "system")
REJECT_CODES = {
    "UNKNOWN_ACTION": "business",          # 名字不在册
    "APPEAR_CLASS_UNKNOWN": "input",       # 报到的类不在册
    "APPEAR_FIELDS_INVALID": "input",      # 报到的字段缺/多/取值域不对
    "APPEAR_CREATE_FAILED": "system",      # 建个体失败
    "AUTHORITY_NOT_OWNER": "permission",   # 不是这个类的提供者，不能报它的事实
    "REGISTER_INCOMPLETE": "input",        # 注册缺格
    "BAD_MESSAGE": "input",                # 报文不是 JSON
    "PARAM_MISSING": "input",              # 缺必填参数（借自订单样板）
    "PARAM_INVALID": "input",              # 参数取值/类型不对
    "NO_IDENTITY": "identity",             # 没身份
    "HUMAN_NEEDS_TICKET": "identity",      # 自称人但没有票
    "IDENTITY_NOT_REPORTED": "identity",   # 这个身份没报到过
    "IDENTITY_FORMAT_BAD": "input",        # 身份串格式不对
    "BAD_TICKET": "identity",              # 票无效/过期
    "BAD_CREDENTIAL": "identity",          # 认证没通过（密码不对等）
    "TICKET_SCOPE_DENIED": "permission",   # 票里没有这个范围
    "PERMISSION_DENIED": "permission",     # 许可条文不放行
    "PERMIT_DENIED": "permission",         # 执行器验不过本体凭证
    "PRECONDITION_FAILED": "business",     # 前置条件不成立（借自订单样板）
    "INTERFACE_NOT_IMPLEMENTED": "business",  # 这个类不实现该接口（不能当它用）
    "PROVIDER_NOT_DECLARED": "system",     # 这个类没有声明执行者（路由不了）
    "CONFIRM_REQUIRED": "permission",      # guard 判「变更类动作需要人确认」→ 界面弹窗
}


# ── 变更类动作：agent 请求时 guard 判「需人确认」，界面弹窗；人签的委托是显式放行 ──
CONFIRM_ACTIONS = (
    "sys.AptInstall", "sys.AptRemove", "sys.AptPurge", "sys.AptUpgrade",
    "sys.UpdateSystem", "sys.RebootSystem", "sys.RollbackDeployment",
    "sys.SetHostname", "sys.SetTimezone", "sys.SetDnsServers",
    "sys.UfwEnable", "sys.UfwDisable", "sys.UfwReset",
    "sys.EnablePackageRepository", "sys.AddLayeredPackage", "sys.RebaseSystem",
    "sys.StopService", "sys.RestartService", "sys.SetServiceEnabled", "sys.MaskService",
    "sys.SignalProcess", "sys.LockUserAccount",
)


def needs_confirm(action):
    return action in CONFIRM_ACTIONS


def reject_category(code):
    """★ 码 → 类别。**不在闭集 ⇒ 返回 None**（调用方按 system 记并留痕；判据 C29 会抓）。"""
    return REJECT_CODES.get(code)


# ── 秘密参数不许落明文（2026-10-19，作者担心「账被翻」）──
_SECRET_KEYS = ("ticket", "secret", "pass", "password", "token")
_MASK = "…（已脱敏）"


def redact_params(params):
    """★ 写账前把【票/密码类】参数脱敏：账是证据，不是密码本。

    ★ 只影响【落账的那一份】；转给执行器的参数仍是原样（否则登录就废了）。
    ★ 递归处理嵌套 dict；别的键原样保留。
    """
    if not isinstance(params, dict):
        return params
    out = {}
    changed = False
    for k, v in params.items():
        if k in _SECRET_KEYS and isinstance(v, str) and v:
            out[k] = (v[:6] + _MASK) if len(v) > 6 else _MASK
            changed = True
        elif isinstance(v, dict):
            out[k] = redact_params(v)
            changed = changed or out[k] != v
        else:
            out[k] = v
    if changed:
        out["_redacted"] = True
    return out
