# -*- coding: utf-8 -*-
"""★ 人侧动作的许可条文 ＋ who/scope 归一（2026-10-19 从 `ontology_definition.py` 拆出，C27：一文件一块）。

★ 为什么拆：`ontology_definition.py` 到了 C27 的行数上限；这两块是**独立职责**：
  · `load_human_side_grants(o)`：人侧动作（呈现／空间／认证）的许可条文；
  · `normalize_grants(o)`：把借来的「who/scope 同词两义」归一（who＝授权者、scope＝生效许可）。
"""
from foundry_ontology.core import ActionType, ActionParameter
from foundry_ontology.core.data_types import PropertyType


def load_human_side_grants(o):
    """★ 2026-10-18：人侧动作的【许可条文】。

    ★ 口径（书 §4.2）：没条文 ⇒ `permissions.default = deny` ⇒ **默认拒绝**。
    ★ 这些动作的 ActionType 不写进 `actions`——由【提供者进程】注册（`registered_by_kind` 决定转给谁）；
      这里只补许可条文，否则 `can_execute` 一律拒。
    ★ 登录 / Permit 未实现 ⇒ 目前是【占位条文】（标“占位”），待人裁后收紧。
    """
    # ★★ 2026-10-18：呈现对外四个动作 ＋ 个人空间三个动作（画布已进呈现内部）
    for _aid, _desc, _params, _roles in [
        ("presentation.show_surface", "给一帧 A2UI ⇒ 画布出现/更新（同一 surfaceId 覆盖）",
         [("surface", PropertyType.STRING, True), ("frame", PropertyType.STRING, True)],
         ["user", "agent", "presence"]),
        ("presentation.retract_surface", "撤下一张画布（★ 凡清除必留证：必须写 reason）",
         [("surface", PropertyType.STRING, True), ("reason", PropertyType.STRING, True)],
         ["user", "agent"]),
        ("presentation.list_surfaces", "查此刻有哪几张画布（只读）",
         [], ["user", "agent"]),
        ("presentation.get_surface", "查某一张的画布内容（只读）",
         [("surface", PropertyType.STRING, True)], ["user", "agent"]),
        # ★★★ 认证 ＝ 本体的事（★ 本体四件第一件就是「认」）
        #    ★ 作者令（逐字）：「这个密码啥的是不是在本体空间中更合适呢？登录的这个是给个人那啥吗？
        #      当确定登录了以后，再给这个个人空间这块留个信息吧」
        #    ★ 模型学 PAM／OIDC：★ 认证（你是谁）和授权（你能干什么）分开；
        #      ★ 认过 ⇒ 发【票】；★ 别人【只看票，不碰密码】。
        ("identity.authenticate", "认人：验身份凭据，通过则发一张票（★ 密码归本体，不归空间）",
         [("user", PropertyType.STRING, True), ("secret", PropertyType.STRING, False)],
         ["user", "presence"]),
        ("identity.session", "查票：这张票是谁、什么时候过期（只读）",
         [("ticket", PropertyType.STRING, True)], ["user", "agent", "presence"]),
        ("identity.revoke", "销票：主动作废（比如退出）",
         [("ticket", PropertyType.STRING, True)], ["user"]),
        ("space.login", "凭【票】进空间：认过了才给开（★ 不再验密码 —— 密码归本体）",
         [("ticket", PropertyType.STRING, True)], ["user", "presence"]),
        ("space.set_layout", "改布局（摆放归个人空间）",
         [("layout", PropertyType.STRING, True)], ["user", "agent"]),
        ("space.get_layout", "读布局（只读）", [], ["user", "agent"]),
    ]:
        o.register_action_type(ActionType(
            action_id=_aid, description=_desc,
            parameters=[ActionParameter(n, t, required=r) for n, t, r in _params],
            validation_rules=[], effects=[],
            metadata={"kind": "invoke", "implemented": "presentation_process.py / space_process.py",
                      "reversible": True},
            required_roles=_roles,
        ))

    grants = o.metadata.setdefault("permissions", {}).setdefault("grants", {})
    rows = {
        "space.status":         {"who": ["world://user", "world://agent"], "why": "只读状态（占位）"},
        "space.activate":       {"who": ["world://user"], "why": "登录/切换时由接入触发（登录未实现，占位）"},
        "space.deactivate":     {"who": ["world://user"], "why": "登出/切换（登录未实现，占位）"},
        "space.set_wallpaper":  {"who": ["world://user"], "why": "改自己的地盘（占位）"},
        # ★★ 2026-10-18 作者令「撤销画布这个类」⇒ 画布进【呈现内部的一张表】，
        #    ★ 对外只开四个动作（同一 surfaceId 覆盖 ＝ 改）。
        "presentation.show_surface":    {"who": ["world://user", "world://agent", "world://presence", "world://surface"],
                                         "why": "给一帧 A2UI ⇒ 画布出现/更新（占位）"},
        "presentation.retract_surface": {"who": ["world://user", "world://agent"],
                                         "why": "撤下一张画布（占位）"},
        "presentation.list_surfaces":   {"who": ["world://user", "world://agent"],
                                         "why": "查此刻有哪几张（只读；占位）"},
        "presentation.get_surface":     {"who": ["world://user", "world://agent"],
                                         "why": "查某一张的画布内容（只读；占位）"},
        # ★ 个人空间：登录入口 ＋ 布局（摆放归它）
        # ★★★ 认证：★ 谁都能【试图】认（不然登不进去）；★ 但【认过才发票】。
        "identity.authenticate": {"who": ["world://user", "world://presence", "world://surface"],
                                  "why": "认人（★ 谁都可能来认；★ 通过才发票）"},
        "identity.session":      {"who": ["world://user", "world://agent", "world://presence"],
                                  "why": "查票（只读）"},
        "identity.revoke":       {"who": ["world://user"], "why": "销票（退出）"},
        # ★ 进空间要【票】—— ★ 空间【不碰密码】
        "space.login":          {"who": ["world://user", "world://presence", "world://surface"],
                                 "why": "凭票进空间（★ 票由 identity.authenticate 发）"},
        "space.set_layout":     {"who": ["world://user", "world://agent"],
                                 "why": "改布局（摆放归个人空间；占位）"},
        "space.get_layout":     {"who": ["world://user", "world://agent"],
                                 "why": "读布局（只读；占位）"},
        "presentation.retract": {"who": ["world://user", "world://agent"], "why": "撤自己的表达（占位）"},
        "presentation.notify":  {"who": ["world://user", "world://agent"], "why": "向人通知（占位）"},
        "presentation.confirm": {"who": ["world://user"], "why": "人确认（占位）"},
    }
    for name, g in rows.items():
        grants.setdefault(name, g)


def normalize_grants(o):
    """★ 2026-10-19 修「who/scope 同词两义」：借来的条文里 `who`＝授权者、`scope`＝生效许可。

    ★ 13 自己新增的行（人侧＋sysknife 只读）原来只有 `who`（当时当「被允许的主体」用）
      ⇒ 这里补 `scope`，`who` 归位成授权者（占位：今天没有授权动作；who 只作条文）。
    ★ 必须在【两个装载器都跑完】之后调用（人侧 ＋ sysknife）。
    """
    grants = (o.metadata.setdefault("permissions", {})).setdefault("grants", {})
    for name, g in grants.items():
        if name.startswith("_") or not isinstance(g, dict) or g.get("scope"):
            continue
        g["scope"] = list(g.get("who") or [])
        g["who"] = ["world://user"]
        g["_note"] = "who＝授权者（占位）；scope＝生效许可（can_execute 读 scope）"
