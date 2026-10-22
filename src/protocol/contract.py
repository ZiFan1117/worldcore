# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P1 动作契约。

动作只来自本体 law；本模块校验契约字段/效果/权限/参数，不做签发或执行。
"""
import json
import os
import re
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "action_contract.schema.json")
ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
REQUIRED = ("id", "label", "description", "required_roles", "kind", "effects",
            "preconditions", "parameters", "grant", "metadata")
EFFECTS = {"forward", "ledger", "state_change", "provider_report", "ticket_issued", "notify"}
PARAM_TYPES = {"STRING", "INTEGER", "FLOAT", "NUMBER", "BOOLEAN",
               "OBJECT", "OBJECT_REFERENCE", "ARRAY", "NULL"}
BAD_FIELDS = {"world_action", "transport", "mcp", "server", "visibility", "function"}


class ContractError(ValueError):
    """动作契约不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _semantic(a: Any) -> list:
    errors = []
    if not isinstance(a, dict):
        return ["BAD_ACTION_CONTRACT"]
    for key in BAD_FIELDS:
        if key in a:
            errors.append("BAD_FIELD:%s" % key)
    for key in REQUIRED:
        if key not in a:
            errors.append("MISSING:%s" % key)
    if errors:
        return errors
    if not isinstance(a.get("id"), str) or not ACTION_RE.match(a.get("id")):
        errors.append("BAD_ACTION_ID:%s" % a.get("id"))
    if not isinstance(a.get("label"), str) or not a.get("label"):
        errors.append("BAD_LABEL")
    if not isinstance(a.get("required_roles"), list) or not a.get("required_roles"):
        errors.append("BAD_ROLES")
    effects = a.get("effects")
    if not isinstance(effects, list) or not effects:
        errors.append("BAD_EFFECTS")
    else:
        for e in effects:
            if not isinstance(e, dict) or e.get("kind") not in EFFECTS:
                errors.append("BAD_EFFECT:%s" % (e.get("kind") if isinstance(e, dict) else e))
    grant = a.get("grant")
    if not isinstance(grant, dict):
        errors.append("BAD_GRANT")
    else:
        if not isinstance(grant.get("who"), list) or not grant.get("who"):
            errors.append("BAD_GRANT")
        if not isinstance(grant.get("scope"), list) or not grant.get("scope"):
            errors.append("BAD_GRANT")
    for p in a.get("parameters") or []:
        if not isinstance(p, dict):
            errors.append("BAD_PARAM")
            continue
        if p.get("type") not in PARAM_TYPES:
            errors.append("BAD_PARAM_TYPE:%s" % p.get("type"))
    return errors


def validate_action_contract(a: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(a)
    if errors:
        return errors
    _validate(a, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_action_contract(a: Any) -> None:
    errors = validate_action_contract(a)
    if errors:
        raise ContractError("；".join(errors))
