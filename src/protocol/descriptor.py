# -*- coding: utf-8 -*-
"""worldcore protocol v1 · 五要素注册包校验器。

协议源：spec/v1/five_elements.schema.json
本模块直接执行这份 JSON Schema 的一个严格子集；语义闭包（重名、引用）
另做检查。协议与代码同源：字段/类型/枚举从 schema 读，不在各进程另抄一份。
"""
import json
import os
import re
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(ROOT, "spec", "v1", "five_elements.schema.json")
SECTIONS = ("objects", "links", "interfaces", "actions", "functions")
ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class ProtocolError(ValueError):
    """注册包不符合协议。"""


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SCHEMA = load_schema()


def _type_ok(value: Any, want: Any) -> bool:
    if isinstance(want, list):
        return any(_type_ok(value, one) for one in want)
    if want == "object":
        return isinstance(value, dict)
    if want == "array":
        return isinstance(value, list)
    if want == "string":
        return isinstance(value, str)
    if want == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if want == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if want == "boolean":
        return isinstance(value, bool)
    if want == "null":
        return value is None
    return True


def _resolve_ref(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ProtocolError("只允许本地 $ref：%r" % ref)
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(instance: Any, schema: dict, root: dict, path: str, errors: list) -> None:
    if not isinstance(schema, dict):
        return
    if "$ref" in schema:
        _validate(instance, _resolve_ref(root, schema["$ref"]), root, path, errors)
        return
    if "const" in schema and instance != schema["const"]:
        errors.append("SCHEMA:%s:const" % path)
        return
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("SCHEMA:%s:enum" % path)
        return
    if "type" in schema and not _type_ok(instance, schema["type"]):
        errors.append("SCHEMA:%s:type" % path)
        return
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("SCHEMA:%s:minLength" % path)
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("SCHEMA:%s:pattern" % path)
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("SCHEMA:%s:minimum" % path)
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("SCHEMA:%s:minItems" % path)
        if "items" in schema:
            for i, item in enumerate(instance):
                _validate(item, schema["items"], root, "%s[%d]" % (path, i), errors)
    if isinstance(instance, dict):
        required = schema.get("required") or []
        for key in required:
            if key not in instance:
                errors.append("SCHEMA:%s:missing:%s" % (path, key))
        props = schema.get("properties") or {}
        for key, value in instance.items():
            if key in props:
                _validate(value, props[key], root, "%s.%s" % (path, key), errors)
            elif schema.get("additionalProperties") is False:
                errors.append("SCHEMA:%s:extra:%s" % (path, key))


def _semantic(bundle: Any) -> list:
    errors = []
    if not isinstance(bundle, dict):
        return ["BAD_BUNDLE"]
    for section in SECTIONS:
        if not isinstance(bundle.get(section), list):
            errors.append("MISSING_SECTION:%s" % section)
    if errors:
        return errors
    if bundle.get("protocol") != "world.protocol.v1":
        errors.append("BAD_PROTOCOL")
    if not isinstance(bundle.get("provider"), str) or not bundle["provider"]:
        errors.append("BAD_PROVIDER")

    object_ids = set()
    for obj in bundle["objects"]:
        if not isinstance(obj, dict):
            continue
        oid = obj.get("id")
        if isinstance(oid, str) and oid in object_ids:
            errors.append("DUPLICATE_ID:%s" % oid)
        object_ids.add(oid)

    link_ids = set()
    for link in bundle["links"]:
        if not isinstance(link, dict):
            continue
        lid = link.get("id")
        if lid in link_ids:
            errors.append("DUPLICATE_ID:%s" % lid)
        link_ids.add(lid)
        if link.get("source") not in object_ids:
            errors.append("LINK_SOURCE_UNKNOWN:%s" % link.get("source"))
        if link.get("target") not in object_ids:
            errors.append("LINK_TARGET_UNKNOWN:%s" % link.get("target"))

    if_ids = set()
    for iface in bundle["interfaces"]:
        if not isinstance(iface, dict):
            continue
        iid = iface.get("id")
        if iid in if_ids:
            errors.append("DUPLICATE_ID:%s" % iid)
        if_ids.add(iid)
        if not isinstance(iface.get("required"), list):
            errors.append("BAD_INTERFACE_REQUIRED:%s" % iid)
            continue
        for prop in iface["required"]:
            if not isinstance(prop, dict) or not prop.get("name") or not prop.get("type"):
                errors.append("BAD_INTERFACE_REQUIRED:%s" % iid)

    action_ids = set()
    for action in bundle["actions"]:
        if not isinstance(action, dict):
            continue
        aid = action.get("id")
        if not isinstance(aid, str) or not ACTION_ID_RE.match(aid):
            errors.append("BAD_ACTION_ID:%s" % aid)
            continue
        if aid in action_ids:
            errors.append("DUPLICATE_ID:%s" % aid)
        action_ids.add(aid)

    fn_ids = set()
    for fn in bundle["functions"]:
        if not isinstance(fn, dict):
            continue
        fid = fn.get("id")
        if fid in fn_ids:
            errors.append("DUPLICATE_ID:%s" % fid)
        fn_ids.add(fid)
        entry = fn.get("entry")
        if entry and entry not in action_ids:
            errors.append("FUNCTION_ENTRY_UNKNOWN:%s" % entry)
    return errors


def validate_bundle(bundle: Any) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = _semantic(bundle)
    if errors:
        return errors
    _validate(bundle, SCHEMA, SCHEMA, "$", errors)
    return errors


def require_bundle(bundle: Any) -> None:
    errors = validate_bundle(bundle)
    if errors:
        raise ProtocolError("；".join(errors))


if __name__ == "__main__":
    import sys
    raw = sys.stdin.read()
    try:
        require_bundle(json.loads(raw))
    except Exception as exc:
        print("REJECT:", exc)
        raise SystemExit(1)
    print("ACCEPT")
