# -*- coding: utf-8 -*-
"""AIOS → polkit policy 生成器（★ 第一步：让本体当决策者）。

★ 作者令（逐字）：「**行的，我们先生成，Pocket policy**」（＝ polkit policy）。

★★ 干什么：把本体的 9 个动作，翻译成 polkit 的 `<action>`，写成一个 `.policy` 文件。
★★ 装到 `/usr/share/polkit-1/actions/` 之后，★ `pkaction` 就能看到这 9 个动作。

★ 它【不做】的：不判许可（那是 polkit 的活）、不传输（那是总线的活）。

★ 注：action id 只能用 ASCII 字母数字和 `.`／`-`／`_`（★ polkit 的规矩）。
"""

import os
import sys
import xml.sax.saxutils as sx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ontology_definition import build_aios_ontology

OUT = os.environ.get("AIOS_POLKIT_OUT", "/usr/share/polkit-1/actions/net.ai-os.worldcore.policy")
# ★ 许可条文（★ 谁能做）不在 P 的 metadata 里，★ 直接读本体原件
ONTOLOGY_JSON = os.environ.get("AIOS_ONTOLOGY", "/usr/lib/aios/ontology.json")


def load_grants():
    """★ 从本体原件读 permissions.grants[action].who。"""
    import json
    try:
        with open(ONTOLOGY_JSON, "r", encoding="utf-8") as f:
            o = json.load(f)
        return (o.get("permissions") or {}).get("grants") or {}
    except Exception:
        return {}
VENDOR = "AI-OS.NET"
VENDOR_URL = "https://ai-os.net"


def action_id(name):
    """★ 动作名 → polkit action id（★ 只留 ASCII 字母数字和 . - _）。"""
    safe = "".join(c if (c.isalnum() or c in ".-_") else "-" for c in name)
    return "net.ai-os.worldcore.action." + safe


def one(action_name, at, grants):
    """★ 一个动作 → 一段 <action>。"""
    what = (at.metadata or {}).get("what") or action_name
    not_roles = (at.metadata or {}).get("not_roles") or []
    g = grants.get(action_name) or {}
    who = g.get("who") or []
    implemented = (at.metadata or {}).get("implemented") or "未定"
    aid = action_id(action_name)
    e = sx.escape
    L = [
        "  <action id=\"" + e(aid) + "\">",
        "    <description>" + e(str(what)) + "</description>",
        "    <message>需要授权才能执行 " + e(action_name) + "</message>",
        "    <defaults>",
        "      <allow_any>auth_admin</allow_any>",
        "      <allow_inactive>auth_admin</allow_inactive>",
        "      <allow_active>auth_admin_keep</allow_active>",
        "    </defaults>",
        "    <annotate key=\"net.ai-os.worldcore.action\">" + e(action_name) + "</annotate>",
        "    <annotate key=\"net.ai-os.worldcore.what\">" + e(str(what)) + "</annotate>",
        "    <annotate key=\"net.ai-os.worldcore.not_roles\">" + e("；".join(str(x) for x in not_roles)) + "</annotate>",
        "    <annotate key=\"net.ai-os.worldcore.who\">" + e(",".join(str(x) for x in who)) + "</annotate>",
        "    <annotate key=\"net.ai-os.worldcore.implemented\">" + e(str(implemented)) + "</annotate>",
        "  </action>",
    ]
    return "\n".join(L)


def main():
    ont = build_aios_ontology()
    grants = load_grants()
    print("[polkit] 许可条文 %d 条" % len([k for k in grants if not k.startswith("_")]))
    acts = [(n, a) for n, a in ont.action_types.items()]
    acts.sort(key=lambda x: x[0])
    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE policyconfig PUBLIC',
        ' "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"',
        ' "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">',
        "<policyconfig>",
        "  <vendor>" + VENDOR + "</vendor>",
        "  <vendor_url>" + VENDOR_URL + "</vendor_url>",
    ]
    body = [one(n, a, grants) for n, a in acts]
    xml = "\n".join(head + body + ["</policyconfig>", ""])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(xml)
    print("[polkit] 写了 %d 个 action → %s" % (len(acts), OUT))
    for n, _ in acts:
        print("   " + action_id(n))


if __name__ == "__main__":
    main()
