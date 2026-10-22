# -*- coding: utf-8 -*-
"""C105 · P1 动作契约 —— 世界动作只在本体 law；契约字段/效果/权限/参数可验。

反例：缺 id/required_roles/parameters/effects/grant；action 名非法；effect 越界；
grant 为空；参数类型非法；夹带 world_action/transport。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.contract import validate_action_contract  # noqa: E402


def valid():
    return {
        "id": "file.read_text",
        "version": 1,
        "label": "file.read_text",
        "description": "读文本",
        "required_roles": ["fs"],
        "applies_to": None,
        "kind": "invoke",
        "implemented": "has_entry",
        "reversible": True,
        "on_failure": "reject",
        "effects": [{"kind": "forward"}, {"kind": "ledger"}],
        "preconditions": [{"kind": "param_present", "name": "path"}],
        "parameters": [{"name": "path", "type": "STRING", "required": True}],
        "grant": {"who": ["world://user"], "scope": ["world://user/zhang"]},
        "metadata": {},
    }


def reject(x, needle):
    why = validate_action_contract(x)
    if not why:
        return "应拒未拒（%s）" % needle
    if needle not in " ".join(why):
        return "拒因不含 %r：%s" % (needle, "；".join(why))
    return None


def main():
    bad = []
    why = validate_action_contract(valid())
    if why:
        bad.append("合法动作被拒：%s" % "；".join(why))

    for key in ("id", "required_roles", "parameters", "effects", "grant"):
        x = valid(); x.pop(key)
        msg = reject(x, "MISSING:" + key)
        if msg:
            bad.append(key + "：" + msg)

    x = valid(); x["id"] = "Bad Action"
    msg = reject(x, "BAD_ACTION_ID")
    if msg:
        bad.append("id：" + msg)

    x = valid(); x["effects"] = [{"kind": "execute_anything"}]
    msg = reject(x, "BAD_EFFECT")
    if msg:
        bad.append("effect：" + msg)

    x = valid(); x["grant"] = {"who": [], "scope": ["x"]}
    msg = reject(x, "BAD_GRANT")
    if msg:
        bad.append("grant：" + msg)

    x = valid(); x["parameters"] = [{"name": "path", "type": "MAGIC"}]
    msg = reject(x, "BAD_PARAM_TYPE")
    if msg:
        bad.append("param：" + msg)

    x = valid(); x["world_action"] = "x"
    msg = reject(x, "BAD_FIELD:world_action")
    if msg:
        bad.append("world_action：" + msg)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（P1 动作契约：合法通过，缺格/坏 id/effect/grant/param/MCP 字段拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
