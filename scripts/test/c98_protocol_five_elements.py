# -*- coding: utf-8 -*-
"""C98 · 五要素注册协议 —— 协议定义必须和代码同源，非法注册必须拒。

反例：
  · 缺 objects/links/interfaces/actions/functions 任一节
  · action id 不合命名
  · 同一包内重复 id
  · 关系 source/target 引用不存在的对象类型
  · 接口 required 字段形状不对
断言颜色：上述任一没被拒 ⇒ 红；全部被拒且合法包通过 ⇒ 绿。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.descriptor import validate_bundle  # noqa: E402


def valid_bundle():
    return {
        "protocol": "world.protocol.v1",
        "provider": "world://fs/leap16",
        "objects": [{
            "id": "File",
            "label": "文件",
            "primary_key": "path",
            "properties": [
                {"name": "path", "type": "STRING", "required": True},
            ],
        }],
        "links": [{
            "id": "contained-in",
            "label": "包含于",
            "source": "File",
            "target": "Directory",
            "cardinality": "one_to_many",
        }],
        "interfaces": [{
            "id": "Readable",
            "label": "可读",
            "description": "能读文本",
            "required": [{"name": "path", "type": "STRING"}],
        }],
        "actions": [{
            "id": "fs.read",
            "label": "fs.read",
            "kind": "invoke",
            "required_roles": ["fs"],
            "parameters": [{"name": "path", "type": "STRING", "required": True}],
            "effects": [{"kind": "forward"}, {"kind": "ledger"}],
        }],
        "functions": [{
            "id": "fn:fs.read",
            "entry": "fs.read",
            "provider": "world://fs/leap16",
        }],
        "objects_extra": [{"id": "Directory", "label": "目录", "properties": []}],
    }


def check_reject(bundle, needle):
    why = validate_bundle(bundle)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []

    b = valid_bundle()
    b["objects"].extend(b.pop("objects_extra"))
    why = validate_bundle(b)
    if why:
        bad.append("合法包被拒：%s" % "；".join(why))

    for key in ("objects", "links", "interfaces", "actions", "functions"):
        x = valid_bundle()
        x["objects"].extend(x.pop("objects_extra"))
        x.pop(key)
        msg = check_reject(x, "MISSING_SECTION")
        if msg:
            bad.append("%s：%s" % (key, msg))

    x = valid_bundle()
    x["objects"].extend(x.pop("objects_extra"))
    x["actions"][0]["id"] = "Fs Read"
    msg = check_reject(x, "BAD_ACTION_ID")
    if msg:
        bad.append("action id：" + msg)

    x = valid_bundle()
    x["objects"].extend(x.pop("objects_extra"))
    x["objects"].append({"id": "File", "label": "重复", "properties": []})
    msg = check_reject(x, "DUPLICATE_ID")
    if msg:
        bad.append("重复：" + msg)

    x = valid_bundle()
    x["objects"].extend(x.pop("objects_extra"))
    x["links"][0]["target"] = "NoSuchType"
    msg = check_reject(x, "LINK_TARGET_UNKNOWN")
    if msg:
        bad.append("link target：" + msg)

    x = valid_bundle()
    x["objects"].extend(x.pop("objects_extra"))
    x["interfaces"][0]["required"] = "path"
    msg = check_reject(x, "BAD_INTERFACE_REQUIRED")
    if msg:
        bad.append("interface：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（五要素注册协议：合法通过，六类反例均拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
