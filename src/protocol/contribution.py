# -*- coding: utf-8 -*-
"""worldcore protocol v1 · P1 外部贡献协议。

外部软件向世界贡献三类能力：
  data_sources  数据源（产生已有对象类型的个体/属性）
  functions     无副作用可调用计算
  actions       有副作用的外部操作（仍需本体许可）
它们都不是 world action/function 定义。
"""
import json
import os
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "external_contributions.schema.json")
SECTIONS = ("data_sources", "functions", "actions")
BAD_TOP_KEYS = {"world_action", "visibility", "kind", "transport", "mcp", "server", "auth"}
NAME_RE = __import__("re").compile(r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")


class ContributionError(ValueError):
    """外部贡献不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _semantic(bundle: Any) -> list:
    errors = []
    if not isinstance(bundle, dict):
        return ["BAD_BUNDLE"]
    for key in BAD_TOP_KEYS:
        if key in bundle:
            errors.append("BAD_FIELD:%s" % key)
    for section in SECTIONS:
        if not isinstance(bundle.get(section), list):
            errors.append("MISSING_SECTION:%s" % section)
    if errors:
        return errors
    if bundle.get("protocol") != "world.external-contributions.v1":
        errors.append("BAD_PROTOCOL")
    if not isinstance(bundle.get("provider"), str) or not bundle.get("provider").startswith("world://"):
        errors.append("BAD_PROVIDER")

    names = set()
    for ds in bundle["data_sources"]:
        if not isinstance(ds, dict):
            continue
        sid = ds.get("id")
        if not isinstance(sid, str) or not sid:
            errors.append("SOURCE_ID")
        if not isinstance(ds.get("object_type"), str) or not ds.get("object_type"):
            errors.append("SOURCE_OBJECT_TYPE")
        if not isinstance(ds.get("mapping"), dict):
            errors.append("SOURCE_MAPPING")
    for fn in bundle["functions"]:
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            errors.append("FUNCTION_NAME:%s" % name)
        if name in names:
            errors.append("DUPLICATE_NAME:%s" % name)
        names.add(name)
        if "side_effects" in fn:
            errors.append("FUNCTION_SIDE_EFFECTS:%s" % name)
    for act in bundle["actions"]:
        if not isinstance(act, dict):
            continue
        name = act.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            errors.append("ACTION_NAME:%s" % name)
        if name in names:
            errors.append("DUPLICATE_NAME:%s" % name)
        names.add(name)
        effects = act.get("side_effects")
        if not isinstance(effects, list) or not effects:
            errors.append("ACTION_SIDE_EFFECTS:%s" % name)
    return errors


def validate_contributions(bundle: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(bundle)
    if errors:
        return errors
    _validate(bundle, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_contributions(bundle: Any) -> None:
    errors = validate_contributions(bundle)
    if errors:
        raise ContributionError("；".join(errors))
