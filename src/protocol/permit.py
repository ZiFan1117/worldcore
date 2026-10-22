# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P3 permit 协议。

格式/字段/期限/绑定的协议层校验；签发与验签仍由 ontology.gate.permit 负责。
"""
import json
import os
import re
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "permit.schema.json")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
REQUIRED = ("v", "id", "action", "fp", "actor", "at", "exp", "sig")


class PermitError(ValueError):
    """permit 不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _semantic(p: Any) -> list:
    errors = []
    if not isinstance(p, dict):
        return ["BAD_PERMIT"]
    for key in REQUIRED:
        if key not in p:
            errors.append("MISSING:%s" % key)
    if errors:
        return errors
    if p.get("v") != 1:
        errors.append("BAD_VERSION")
    if not isinstance(p.get("id"), str) or not p.get("id"):
        errors.append("BAD_ID")
    if not isinstance(p.get("action"), str) or not ACTION_RE.match(p.get("action")):
        errors.append("BAD_ACTION:%s" % p.get("action"))
    if not isinstance(p.get("fp"), str) or not HEX64.match(p.get("fp")):
        errors.append("BAD_FP")
    if not isinstance(p.get("sig"), str) or not HEX64.match(p.get("sig")):
        errors.append("BAD_SIG")
    if not isinstance(p.get("actor"), str) or not p.get("actor").startswith("world://"):
        errors.append("BAD_ACTOR")
    if not isinstance(p.get("at"), int) or not isinstance(p.get("exp"), int):
        errors.append("BAD_TIME")
    elif p.get("exp") <= p.get("at"):
        errors.append("BAD_EXP")
    return errors


def validate_permit(p: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(p)
    if errors:
        return errors
    _validate(p, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_permit(p: Any) -> None:
    errors = validate_permit(p)
    if errors:
        raise PermitError("；".join(errors))
