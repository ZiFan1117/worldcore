# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P2 消息协议。

消息类型：register / registered / call / result / state_report / state_apply /
state_ack / event。信封与 MCP 无关；MCP 只被借来描述外部函数清单。
"""
import json
import os
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "message.schema.json")
MCP_KEYS = {"jsonrpc", "method", "params", "resultType", "tools/call"}
TYPES = {"register", "registered", "call", "result", "state_report", "state_apply", "state_ack", "event"}


class MessageError(ValueError):
    """消息不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _is_world_ref(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("world://") and len(value) > len("world://")


def _semantic(msg: Any) -> list:
    errors = []
    if not isinstance(msg, dict):
        return ["BAD_MESSAGE"]
    for key in MCP_KEYS:
        if key in msg:
            errors.append("MCP_FIELD:%s" % key)
    data = msg.get("data")
    if isinstance(data, dict):
        for key in MCP_KEYS:
            if key in data:
                errors.append("MCP_FIELD:data.%s" % key)
    if msg.get("protocol") != "world.message.v1":
        errors.append("BAD_PROTOCOL")
    if msg.get("v") != 1:
        errors.append("BAD_VERSION")
    if msg.get("type") not in TYPES:
        errors.append("BAD_TYPE:%s" % msg.get("type"))
    if not isinstance(msg.get("id"), str) or not msg.get("id"):
        errors.append("BAD_ID")
    if not _is_world_ref(msg.get("from")):
        errors.append("BAD_FROM:%s" % msg.get("from"))
    if not _is_world_ref(msg.get("to")):
        errors.append("BAD_TO:%s" % msg.get("to"))
    if not isinstance(data, dict):
        errors.append("BAD_DATA")

    if errors:
        return errors

    mtype = msg["type"]
    if mtype == "register":
        individual = data.get("individual")
        if not isinstance(individual, dict) or not _is_world_ref(individual.get("id")):
            errors.append("REGISTER_INDIVIDUAL")
        for section in ("functions", "actions", "data_sources"):
            if section in data and not isinstance(data.get(section), list):
                errors.append("REGISTER_%s" % section.upper())
    elif mtype == "registered":
        if not isinstance(data.get("ok"), bool):
            errors.append("REGISTERED_OK")
    elif mtype == "call":
        if not isinstance(data.get("fn"), str) or not data.get("fn"):
            errors.append("CALL_FN")
        if not isinstance(data.get("args"), list):
            errors.append("CALL_ARGS")
    elif mtype == "result":
        if not isinstance(data.get("ok"), bool):
            errors.append("RESULT_OK")
        if data.get("ok") is False and not isinstance(data.get("error"), dict):
            errors.append("RESULT_ERROR")
    elif mtype in ("state_report", "state_apply"):
        if not _is_world_ref(data.get("individual")):
            errors.append("STATE_INDIVIDUAL")
        if not isinstance(data.get("changes"), dict) or not data.get("changes"):
            errors.append("STATE_CHANGES")
        if not isinstance(data.get("rev"), int):
            errors.append("STATE_REV")
    elif mtype == "state_ack":
        if not isinstance(data.get("rev"), int):
            errors.append("STATE_REV")
        if not isinstance(data.get("ok"), bool):
            errors.append("STATE_ACK_OK")
    elif mtype == "event":
        if not isinstance(data.get("kind"), str) or not data.get("kind"):
            errors.append("EVENT_KIND")
    return errors


def validate_message(msg: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(msg)
    if errors:
        return errors
    _validate(msg, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_message(msg: Any) -> None:
    errors = validate_message(msg)
    if errors:
        raise MessageError("；".join(errors))
