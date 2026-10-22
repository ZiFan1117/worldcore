# -*- coding: utf-8 -*-
"""C99 · 动作/函数扩展协议 —— 对象/接口/关系封闭，只开放 action/function。

反例：
  · 夹带 objects/links/interfaces（世界模型不许随软件安装改）
  · action 不在 ext.* 命名空间 / 命名空间与包不符
  · 动作引用不存在的对象类型
  · function entry 指向不存在的 action
  · grant 用通配符给自己授权
断言颜色：上述任一没被拒 ⇒ 红；合法包通过且反例全拒 ⇒ 绿。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.extension import validate_extension  # noqa: E402


def valid_bundle():
    return {
        "protocol": "world.action-extension.v1",
        "package": "com.example.calculator",
        "namespace": "ext.example.calculator",
        "provider": "world://app/calculator",
        "actions": [{
            "id": "ext.example.calculator.compute",
            "version": 1,
            "label": "calculator.compute",
            "required_roles": ["calculator"],
            "parameters": [
                {"name": "expr", "type": "STRING", "required": True},
            ],
            "result": {"type": "NUMBER"},
            "errors": ["BAD_EXPR"],
            "effects": [{"kind": "forward"}, {"kind": "ledger"}],
            "grant": {"who": ["world://user/zhang"]},
        }],
        "functions": [{
            "id": "fn:calculator.compute",
            "entry": "ext.example.calculator.compute",
            "provider": "world://app/calculator",
        }],
    }


def reject(bundle, needle, known=None):
    why = validate_extension(bundle, known_types=known)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_extension(valid_bundle())
    if why:
        bad.append("合法包被拒：%s" % "；".join(why))

    x = valid_bundle()
    x["objects"] = []
    msg = reject(x, "CLOSED_MODEL")
    if msg:
        bad.append("objects：" + msg)

    x = valid_bundle()
    x["interfaces"] = []
    msg = reject(x, "CLOSED_MODEL")
    if msg:
        bad.append("interfaces：" + msg)

    x = valid_bundle()
    x["actions"][0]["id"] = "core.file.read"
    msg = reject(x, "BAD_ACTION_ID")
    if msg:
        bad.append("core id：" + msg)

    x = valid_bundle()
    x["actions"][0]["id"] = "ext.other.app.compute"
    msg = reject(x, "BAD_NAMESPACE")
    if msg:
        bad.append("namespace：" + msg)

    x = valid_bundle()
    x["actions"][0]["parameters"][0]["type"] = "world://type/NoSuch"
    msg = reject(x, "UNKNOWN_TYPE_REF", known={"File"})
    if msg:
        bad.append("type ref：" + msg)

    x = valid_bundle()
    x["functions"][0]["entry"] = "ext.example.calculator.nope"
    msg = reject(x, "FUNCTION_ENTRY_UNKNOWN")
    if msg:
        bad.append("function entry：" + msg)

    x = valid_bundle()
    x["actions"][0]["grant"]["who"] = ["*"]
    msg = reject(x, "WILDCARD_GRANT")
    if msg:
        bad.append("wildcard：" + msg)

    x = valid_bundle()
    x["actions"].append(dict(x["actions"][0]))
    msg = reject(x, "DUPLICATE_ACTION")
    if msg:
        bad.append("duplicate：" + msg)

    x = valid_bundle()
    x["functions"][0]["provider"] = "world://app/other"
    msg = reject(x, "FUNCTION_PROVIDER_MISMATCH")
    if msg:
        bad.append("function provider：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（动作/函数扩展协议：合法通过，对象/接口/关系封闭，反例全拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
