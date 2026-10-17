"""AIOS 世界的本体定义 —— ★ 按 P（foundry-ontology-open，MIT）的格式写。

★ 内容来自 `crates/aios-ontology/data/ontology.json`（★ 那是【法】，人审定）。
★ 这里是它的【Python 形态】—— 供本体进程装载。
★ ★ 改动本体：先改 `ontology.json`（要人审），再同步这一份。
"""

from foundry_ontology.core import (
    Ontology, ObjectType, Property, LinkType, Cardinality,
    ActionType, ActionParameter, ValidationRule,
)
from foundry_ontology.core.data_types import PropertyType


def build_aios_ontology() -> Ontology:
    o = Ontology("aios_world", "AIOS 世界本体", "1.0")

    # ── 对象类型（9 类）──
    o.register_object_type(ObjectType(
        type_id="surface",
        display_name="屏面",
        description="一块可被指向、可被撤回的持续体（continuant）：它是屏幕那一面，不是世界状态的另一份载体。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000004", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "role": Property("role", "role", PropertyType.STRING),
            "order": Property("order", "order", PropertyType.INTEGER),
            "visible": Property("visible", "visible", PropertyType.BOOLEAN),
            "retract_seq": Property("retract_seq", "retract_seq", PropertyType.INTEGER),
            "cells": Property("cells", "cells", PropertyType.STRING, description="array(object)"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="port",
        display_name="端口",
        description="一个独立的持续体（independent continuant）：它有 `path` 与身份，并在 `declared→listening→retired` 之间迁移——它是跨进程进出的那一处。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000006", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "path": Property("path", "path", PropertyType.STRING),
            "identity": Property("identity", "identity", PropertyType.STRING),
            "mode": Property("mode", "mode", PropertyType.STRING),
            "owner_uid": Property("owner_uid", "owner_uid", PropertyType.INTEGER),
            "state": Property("state", "state", PropertyType.STRING, options=["declared","listening","retired"], description="enum"),
            "retract_seq": Property("retract_seq", "retract_seq", PropertyType.INTEGER),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="human",
        display_name="人",
        description="人——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000007", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "last_seen": Property("last_seen", "last_seen", PropertyType.INTEGER, description="UNIX 秒"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="agent",
        display_name="智能体",
        description="智能体——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000008", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "manifest": Property("manifest", "manifest", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["installed","running","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="application",
        display_name="应用",
        description="应用——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000009", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["installed","running","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="service",
        display_name="系统服务",
        description="系统服务——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000010", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "unit": Property("unit", "unit", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["running","stopped","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="device",
        display_name="设备",
        description="设备——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000011", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "cert": Property("cert", "cert", PropertyType.STRING),
            "bound_to": Property("bound_to", "bound_to", PropertyType.OBJECT_REFERENCE, description="ref(human)"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="workflow",
        display_name="工作流",
        description="工作流——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。",
        primary_key="name",
        metadata={"wc_id": "wc:ont00000012", "instance_mode": "many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "wf_id": Property("wf_id", "wf_id", PropertyType.STRING),
            "parent_action": Property("parent_action", "parent_action", PropertyType.STRING),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="ledger",
        display_name="账本",
        description="★ 2026-10-13 **作者裁定补立**：世界里那**唯一的一处**系统性记录 —— 只追加的语义事件文件。★ 依据（作者原话逐字）：「**你要说是账本，可以说是单独的一个类，这个可以**……可能最后**整个计算机里头只有这么一处**」。★ 素材：`envelope.fields.seq` 逐字「integer ",
        primary_key="path",
        metadata={"wc_id": "wc:ont00000030", "instance_mode": "one"},
        properties={
            "path": Property("path", "path", PropertyType.STRING, required=True, is_primary_key=True),
            "compaction_seq": Property("compaction_seq", "compaction_seq", PropertyType.INTEGER),
            "entries_total": Property("entries_total", "entries_total", PropertyType.INTEGER),
            "retract_seq": Property("retract_seq", "retract_seq", PropertyType.INTEGER),
        },
    ))

    # ── 关系类型（3 条）──
    o.register_link_type(LinkType("device-bound-to-human", "device-bound-to-human",
        source_type="device", target_type="human", cardinality=Cardinality.ONE_TO_MANY))
    o.register_link_type(LinkType("service-runs-on-device", "service-runs-on-device",
        source_type="service", target_type="device", cardinality=Cardinality.ONE_TO_MANY))
    o.register_link_type(LinkType("application-speaks-on-port", "application-speaks-on-port",
        source_type="application", target_type="port", cardinality=Cardinality.ONE_TO_MANY))

    # ── 动作类型（9 个）──
    # ★ `effects=[]` 与 `validation_rules=[]` 【故意留空】：
    #   ① 我们的动作用「转」（本体只认/盖章/转/记），不靠 effects 改数据；
    #   ② 我们裁定「要形式可判，不是能推理」⇒ 不抄 P 的 eval() 规则。
    o.register_action_type(ActionType(
        action_id="notice.mute",
        description="把一条通告静音",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="notice.unmute",
        description="解除静音",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["agent"],
    ))
    o.register_action_type(ActionType(
        action_id="job.start",
        description="起一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="job.finish",
        description="结束一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="job.cancel",
        description="取消一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="ledger.compact",
        description="压实账本（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="world.rekey",
        description="换世界的钥匙材料（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="world.migrate",
        description="迁移世界（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="presence.report",
        description="在场者报告自己的状态（**申报面**；「有没有许可」不在这里定，由 `permissions.grants` ＋ `default: deny` 决定）",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[],
        effects=[],
        required_roles=["human"],
    ))
    return o


if __name__ == "__main__":
    o = build_aios_ontology()
    print("对象类型:", list(o.object_types))
    print("关系类型:", list(o.link_types))
    print("动作类型:", list(o.action_types))
