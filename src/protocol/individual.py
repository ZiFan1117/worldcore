# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P1 个体注册。

只给 law 已有对象类型赋值；不新增 object_type；属性元数据只能指向已声明属性。
"""
import json
import os
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "individual.schema.json")
BAD_FIELDS = {"new_object_type", "world_action", "transport", "mcp"}
AUTHORITIES = {"software", "ontology"}


class IndividualError(ValueError):
    """个体注册不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _semantic(x: Any) -> list:
    errors = []
    if not isinstance(x, dict):
        return ["BAD_INDIVIDUAL"]
    for key in BAD_FIELDS:
        if key in x:
            errors.append("BAD_FIELD:%s" % key)
    for key in ("protocol", "individual"):
        if key not in x:
            errors.append("MISSING:%s" % key)
    if errors:
        return errors
    if x.get("protocol") != "world.individual.v1":
        errors.append("BAD_PROTOCOL")
    ind = x.get("individual")
    if not isinstance(ind, dict):
        errors.append("BAD_INDIVIDUAL")
        return errors
    iid = ind.get("id")
    if not isinstance(iid, str) or not iid.startswith("world://"):
        errors.append("BAD_INDIVIDUAL_ID:%s" % iid)
    if not isinstance(ind.get("object_type"), str) or not ind.get("object_type"):
        errors.append("BAD_OBJECT_TYPE")
    props = ind.get("properties")
    if not isinstance(props, dict):
        errors.append("BAD_PROPERTIES")
    if "interfaces" in ind and not isinstance(ind["interfaces"], list):
        errors.append("BAD_INTERFACES")
    meta = x.get("property_meta")
    if meta is not None and not isinstance(meta, dict):
        errors.append("BAD_PROPERTY_META")
    elif isinstance(meta, dict) and isinstance(props, dict):
        for name, m in meta.items():
            if name not in props:
                errors.append("UNKNOWN_PROPERTY:%s" % name)
            if not isinstance(m, dict) or m.get("authority") not in AUTHORITIES:
                errors.append("BAD_AUTHORITY:%s" % name)
    if "external_interfaces" in x and not isinstance(x["external_interfaces"], list):
        errors.append("BAD_EXTERNAL_INTERFACES")
    return errors


def validate_individual(x: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(x)
    if errors:
        return errors
    _validate(x, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_individual(x: Any) -> None:
    errors = validate_individual(x)
    if errors:
        raise IndividualError("；".join(errors))
