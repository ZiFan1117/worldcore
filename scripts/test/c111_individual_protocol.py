# -*- coding: utf-8 -*-
"""C111 · P1 个体注册协议 —— 只给已有类型赋值，不新增类型；属性带可变性/权威。

反例：缺 individual/id/object_type/properties；property_meta 指向未声明属性；authority 非法；
新增对象类型字段；external_interfaces 不是数组。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.individual import validate_individual  # noqa: E402


def valid():
    return {
        "protocol": "world.individual.v1",
        "individual": {
            "id": "world://app/calculator",
            "object_type": "Application",
            "properties": {"version": "1.0", "state": "idle"},
            "interfaces": ["Launchable"],
        },
        "property_meta": {
            "version": {"mutable": False, "authority": "software"},
            "state": {"mutable": True, "authority": "ontology", "read_only": False},
        },
        "external_interfaces": [],
    }


def reject(x, needle):
    why = validate_individual(x)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_individual(valid())
    if why:
        bad.append("合法个体被拒：%s" % "；".join(why))

    for key in ("protocol", "individual"):
        x = valid(); x.pop(key)
        msg = reject(x, "MISSING:" + key)
        if msg:
            bad.append(key + "：" + msg)

    x = valid(); x["individual"]["id"] = "http://x"
    msg = reject(x, "BAD_INDIVIDUAL_ID")
    if msg:
        bad.append("id：" + msg)

    x = valid(); x["individual"]["object_type"] = ""
    msg = reject(x, "BAD_OBJECT_TYPE")
    if msg:
        bad.append("type：" + msg)

    x = valid(); x["individual"]["properties"] = []
    msg = reject(x, "BAD_PROPERTIES")
    if msg:
        bad.append("props：" + msg)

    x = valid(); x["property_meta"]["nope"] = {"mutable": True, "authority": "software"}
    msg = reject(x, "UNKNOWN_PROPERTY")
    if msg:
        bad.append("meta：" + msg)

    x = valid(); x["property_meta"]["state"]["authority"] = "nobody"
    msg = reject(x, "BAD_AUTHORITY")
    if msg:
        bad.append("authority：" + msg)

    x = valid(); x["new_object_type"] = "x"
    msg = reject(x, "BAD_FIELD:new_object_type")
    if msg:
        bad.append("new type：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P1 个体：已有类型赋值 + 属性元数据；新类型/坏 authority 拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
