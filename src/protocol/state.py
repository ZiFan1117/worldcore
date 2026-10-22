# -*- coding: utf-8 -*-
"""worldcore protocol v1 · state 同步规则。

state_report/apply 只作用于已声明属性：
  · report：authority 必须是 software；
  · apply：authority=ontology 且 mutable=true；
  · ack：rev/ok 必填。
"""
from typing import Any

AUTHORITIES = {"software", "ontology"}


class StateError(ValueError):
    """状态同步不符合规则。"""


def validate_state(msg: Any, property_meta: dict | None = None) -> list:
    errors = []
    if not isinstance(msg, dict):
        return ["BAD_STATE_MESSAGE"]
    mtype = msg.get("type")
    data = msg.get("data")
    if not isinstance(data, dict):
        return ["BAD_STATE_DATA"]
    if mtype == "state_ack":
        if not isinstance(data.get("rev"), int):
            errors.append("STATE_REV")
        if not isinstance(data.get("ok"), bool):
            errors.append("STATE_ACK_OK")
        return errors
    if mtype not in ("state_report", "state_apply"):
        return ["BAD_STATE_TYPE"]
    changes = data.get("changes")
    if not isinstance(changes, dict) or not changes:
        errors.append("STATE_CHANGES")
    if not isinstance(data.get("rev"), int):
        errors.append("STATE_REV")
    if property_meta is None:
        return errors
    for name in (changes or {}):
        meta = property_meta.get(name)
        if not isinstance(meta, dict):
            errors.append("UNKNOWN_PROPERTY:%s" % name)
            continue
        if meta.get("authority") not in AUTHORITIES:
            errors.append("BAD_AUTHORITY:%s" % name)
        if mtype == "state_report" and meta.get("authority") != "software":
            errors.append("REPORT_NOT_SOFTWARE:%s" % name)
        if mtype == "state_apply":
            if meta.get("authority") != "ontology":
                errors.append("APPLY_NOT_ONTOLOGY:%s" % name)
            if not meta.get("mutable"):
                errors.append("APPLY_NOT_MUTABLE:%s" % name)
    return errors


def require_state(msg: Any, property_meta: dict | None = None) -> None:
    errors = validate_state(msg, property_meta)
    if errors:
        raise StateError("；".join(errors))
