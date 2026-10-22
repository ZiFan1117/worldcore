# -*- coding: utf-8 -*-
"""C103 · C1 key/ACL 规范 —— 我们的 key 表是唯一出处，不是 MCP/散字符串。

反例：
  · key 不以 world/ 开头
  · key 重复
  · 缺 publish/subscribe
  · 非 ontology 角色可发 exec/result
  · 夹带 MCP 命名
断言颜色：当前 key 表合法；注入坏 key 必须被拒。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.keys import TOPICS, validate_topics, ROLES  # noqa: E402


def main():
    bad = []
    why = validate_topics(TOPICS)
    if why:
        bad.append("当前 key 表不合法：%s" % "；".join(why))

    for name, spec in TOPICS.items():
        if not spec["topic"].startswith("world/"):
            bad.append("%s 不以 world/ 开头" % name)
        if spec["topic"] != spec["topic"].lower():
            bad.append("%s 含大写" % name)

    broken = dict(TOPICS)
    broken["bad"] = {"topic": "mcp/tools", "publish": ["caller"], "subscribe": ["ontology"]}
    if not validate_topics(broken):
        bad.append("坏 key 应拒未拒")

    broken = dict(TOPICS)
    broken["exec_bad"] = {"topic": "world/call/exec", "publish": ["caller"], "subscribe": ["provider"]}
    if not validate_topics(broken):
        bad.append("非 ontology 发 exec 应拒未拒")

    if set(ROLES) - {"caller", "provider", "ontology", "subscriber"}:
        bad.append("ROLES 含未知角色")

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（C1 key/ACL：唯一 world/ 命名，exec 只 ontology 发，坏 key 拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
