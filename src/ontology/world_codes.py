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
    "NO_IDENTITY": "identity",             # 没身份
    "HUMAN_NEEDS_TICKET": "identity",      # 自称人但没有票
    "IDENTITY_NOT_REPORTED": "identity",   # 这个身份没报到过
    "IDENTITY_FORMAT_BAD": "input",        # 身份串格式不对
    "BAD_TICKET": "identity",              # 票无效/过期
    "BAD_CREDENTIAL": "identity",          # 认证没通过（密码不对等）
    "TICKET_SCOPE_DENIED": "permission",   # 票里没有这个范围
    "PERMISSION_DENIED": "permission",     # 许可条文不放行
    "PERMIT_DENIED": "permission",         # 执行器验不过本体凭证
}


def reject_category(code):
    """★ 码 → 类别。**不在闭集 ⇒ 返回 None**（调用方按 system 记并留痕；判据 C29 会抓）。"""
    return REJECT_CODES.get(code)


# ── 状态所有权：每类的事实只许它的【提供者】报 ──
#   ★ 空表＝今天没有提供者（谁都不许报，直到给它定一个）。
AUTHORITY_REPORTERS = {
    "human": ["world://space"],          # 人由登录进程报（登录在个人空间里）
    "space": ["world://space"],
    "presentation": ["world://presentation"],
    "computer": ["world://computer"],
    "agent": ["world://agent"],
}


def load_authority(o):
    """★ 把「哪类的事实归谁报」写进每一类的 metadata（`_authority.reporters`）。

    ★ 这是**声明面**；执行面在 `ontology_process.on_appear`（核验函数 `identity.authority_ok`）。
    """
    for tid, ot in o.object_types.items():
        md = dict(getattr(ot, "metadata", None) or {})
        md["_authority"] = {
            "kind": "reported",
            "reporters": list(AUTHORITY_REPORTERS.get(tid, [])),
            "_note": "空表＝今天没有提供者；改这一格＝改法律（走评审）",
        }
        ot.metadata = md
