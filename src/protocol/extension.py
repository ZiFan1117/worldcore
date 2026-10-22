# -*- coding: utf-8 -*-
"""worldcore protocol v1 · 动作/函数扩展包校验器。

固定世界模型：对象类型、接口、关系类型不随软件安装扩展。
只开放 action/function；参数/返回只能引用已有类型或基本类型。
协议源：spec/v1/action_extension.schema.json
"""
import json
import os
import re
from typing import Any

from .descriptor import _validate

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "action_extension.schema.json")
ACTION_ID_RE = re.compile(r"^ext\.[a-z0-9_]+\.[a-z0-9_]+\.[a-z][a-z0-9_]*$")
PRIMITIVES = {"STRING", "INTEGER", "NUMBER", "BOOLEAN", "OBJECT", "OBJECT_REFERENCE", "ARRAY", "NULL"}
CLOSED_SECTIONS = ("objects", "links", "interfaces")


class ExtensionError(ValueError):
    """动作/函数扩展包不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _type_ref_ok(ref: Any, known_types: set | None) -> str | None:
    if not isinstance(ref, str) or not ref:
        return "UNKNOWN_TYPE_REF:%r" % (ref,)
    if ref in PRIMITIVES:
        return None
    if ref.startswith("world://type/"):
        name = ref[len("world://type/"):]
        if known_types is None or name not in known_types:
            return "UNKNOWN_TYPE_REF:%s" % ref
        return None
    return "UNKNOWN_TYPE_REF:%s" % ref


def _semantic(bundle: Any, known_types: set | None) -> list:
    errors = []
    if not isinstance(bundle, dict):
        return ["BAD_BUNDLE"]
    for section in CLOSED_SECTIONS:
        if section in bundle:
            errors.append("CLOSED_MODEL:%s" % section)
    for section in ("actions", "functions"):
        if not isinstance(bundle.get(section), list):
            errors.append("MISSING_SECTION:%s" % section)
    if errors:
        return errors
    if bundle.get("protocol") != "world.action-extension.v1":
        errors.append("BAD_PROTOCOL")
    namespace = bundle.get("namespace")
    provider = bundle.get("provider")
    if not isinstance(namespace, str) or not namespace:
        errors.append("BAD_NAMESPACE")
    if not isinstance(provider, str) or not provider:
        errors.append("BAD_PROVIDER")

    action_ids = set()
    for action in bundle["actions"]:
        if not isinstance(action, dict):
            continue
        aid = action.get("id")
        if not isinstance(aid, str) or not ACTION_ID_RE.match(aid):
            errors.append("BAD_ACTION_ID:%s" % aid)
            continue
        if isinstance(namespace, str) and not aid.startswith(namespace + "."):
            errors.append("BAD_NAMESPACE:%s" % aid)
        if aid in action_ids:
            errors.append("DUPLICATE_ACTION:%s" % aid)
        action_ids.add(aid)
        types = []
        for param in action.get("parameters") or []:
            if isinstance(param, dict):
                types.append(param.get("type"))
        result = action.get("result")
        if isinstance(result, dict):
            types.append(result.get("type"))
            for prop in result.get("properties") or []:
                if isinstance(prop, dict):
                    types.append(prop.get("type"))
        for ref in types:
            why = _type_ref_ok(ref, known_types)
            if why:
                errors.append(why)
        grant = action.get("grant") or {}
        who = grant.get("who") if isinstance(grant, dict) else None
        if not isinstance(who, list) or not who:
            errors.append("EMPTY_GRANT:%s" % aid)
        else:
            for principal in who:
                if not isinstance(principal, str) or "*" in principal:
                    errors.append("WILDCARD_GRANT:%s" % aid)

    fn_ids = set()
    bound_actions = set()
    for fn in bundle["functions"]:
        if not isinstance(fn, dict):
            continue
        fid = fn.get("id")
        if fid in fn_ids:
            errors.append("DUPLICATE_FUNCTION:%s" % fid)
        fn_ids.add(fid)
        entry = fn.get("entry")
        if entry not in action_ids:
            errors.append("FUNCTION_ENTRY_UNKNOWN:%s" % entry)
        else:
            bound_actions.add(entry)
        if fn.get("provider") != provider:
            errors.append("FUNCTION_PROVIDER_MISMATCH:%s" % fn.get("provider"))
    for aid in action_ids - bound_actions:
        errors.append("ACTION_WITHOUT_FUNCTION:%s" % aid)
    return errors


def validate_extension(bundle: Any, known_types: set | None = None) -> list:
    """返回错误码列表；空列表＝合法。known_types 为已存在对象类型 id 集合。"""
    errors = _semantic(bundle, known_types)
    if errors:
        return errors
    _validate(bundle, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_extension(bundle: Any, known_types: set | None = None) -> None:
    errors = validate_extension(bundle, known_types=known_types)
    if errors:
        raise ExtensionError("；".join(errors))


if __name__ == "__main__":
    import sys
    try:
        require_extension(json.loads(sys.stdin.read()))
    except Exception as exc:
        print("REJECT:", exc)
        raise SystemExit(1)
    print("ACCEPT")
