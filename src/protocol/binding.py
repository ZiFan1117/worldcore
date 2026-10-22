# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P1 provider 绑定。

绑定只引用 law 已有的 action/function；不等于新增 world action/function。
"""
import json
import os
import re
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "binding.schema.json")
ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
REQUIRED = ("action", "function", "registered_by", "registered_by_kind", "required_roles")
BAD_FIELDS = {"world_action", "new_action", "definition", "transport", "mcp"}


class BindingError(ValueError):
    """provider 绑定不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _semantic(b: Any, known_actions: set | None) -> list:
    errors = []
    if not isinstance(b, dict):
        return ["BAD_BINDING"]
    for key in BAD_FIELDS:
        if key in b:
            errors.append("BAD_FIELD:%s" % key)
    for key in REQUIRED:
        if key not in b:
            errors.append("MISSING:%s" % key)
    if errors:
        return errors
    action = b.get("action")
    if not isinstance(action, str) or not ACTION_RE.match(action):
        errors.append("BAD_ACTION_ID:%s" % action)
    elif known_actions is not None and action not in known_actions:
        errors.append("ACTION_NOT_IN_LAW:%s" % action)
    if not isinstance(b.get("function"), str) or not b.get("function"):
        errors.append("BAD_FUNCTION")
    if not isinstance(b.get("registered_by"), str) or not b.get("registered_by").startswith("world://"):
        errors.append("BAD_REGISTERED_BY")
    if not isinstance(b.get("registered_by_kind"), str) or not b.get("registered_by_kind"):
        errors.append("BAD_REGISTERED_BY_KIND")
    roles = b.get("required_roles")
    if not isinstance(roles, list) or not roles:
        errors.append("BAD_ROLES")
    return errors


def validate_binding(b: Any, known_actions: set | None = None) -> list:
    """返回错误码列表；空列表＝合法。known_actions 为 law 动作 id 集合。"""
    errors = _semantic(b, known_actions)
    if errors:
        return errors
    _validate(b, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_binding(b: Any, known_actions: set | None = None) -> None:
    errors = validate_binding(b, known_actions)
    if errors:
        raise BindingError("；".join(errors))
