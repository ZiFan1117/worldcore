# -*- coding: utf-8 -*-
"""C101 · P1 外部贡献协议 —— data source / function / action 三类，不是 world 定义。

反例：
  · 夹带 world_action / visibility / MCP transport
  · function 声明 side_effects（function 应无副作用）
  · action 没有 side_effects
  · data source 缺 object_type / mapping
  · 外部贡献重名 / provider 非法
断言颜色：合法包过；反例任一没被拒 ⇒ 红。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.contribution import validate_contributions  # noqa: E402


def valid():
    return {
        "protocol": "world.external-contributions.v1",
        "provider": "world://app/calculator",
        "data_sources": [{
            "id": "calculator.history",
            "object_type": "Calculation",
            "sync": "pull",
            "provenance": "calculator",
            "mapping": {"id": "id", "value": "result"},
        }],
        "functions": [{
            "name": "add",
            "description": "两个数相加",
            "args": ["number", "number"],
            "result": "number",
        }],
        "actions": [{
            "name": "reset",
            "description": "重置计算器",
            "args": [],
            "result": "ok",
            "side_effects": ["last_result", "state"],
        }],
    }


def reject(x, needle):
    why = validate_contributions(x)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_contributions(valid())
    if why:
        bad.append("合法包被拒：%s" % "；".join(why))

    for key in ("data_sources", "functions", "actions"):
        x = valid(); x.pop(key)
        msg = reject(x, "MISSING_SECTION")
        if msg:
            bad.append(key + "：" + msg)

    x = valid(); x["world_action"] = "x"
    msg = reject(x, "BAD_FIELD:world_action")
    if msg:
        bad.append("world_action：" + msg)

    x = valid(); x["functions"][0]["side_effects"] = ["x"]
    msg = reject(x, "FUNCTION_SIDE_EFFECTS")
    if msg:
        bad.append("function effects：" + msg)

    x = valid(); del x["actions"][0]["side_effects"]
    msg = reject(x, "ACTION_SIDE_EFFECTS")
    if msg:
        bad.append("action effects：" + msg)

    x = valid(); del x["data_sources"][0]["object_type"]
    msg = reject(x, "SOURCE_OBJECT_TYPE")
    if msg:
        bad.append("source type：" + msg)

    x = valid(); x["data_sources"][0]["mapping"] = []
    msg = reject(x, "SOURCE_MAPPING")
    if msg:
        bad.append("source mapping：" + msg)

    x = valid(); x["actions"].append(dict(x["actions"][0]))
    msg = reject(x, "DUPLICATE_NAME")
    if msg:
        bad.append("duplicate：" + msg)

    x = valid(); x["provider"] = "http://example.com"
    msg = reject(x, "BAD_PROVIDER")
    if msg:
        bad.append("provider：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P1 外部贡献：三类合法通过，世界定义/MCP/副作用分类反例均拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
