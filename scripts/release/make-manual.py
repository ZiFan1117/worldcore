#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 生成「应用手册」—— **从本体与许可派生，不手写**（2026-10-19；借自借书平台／OSDK 的「工具面从模型派生」）。

★ 作者口径（逐字整理）：「**应用不需要备一份本体，我提供给他们一个手册**」；
  「**给智能体用：把「能办的事」变成一张清单**」（借书平台/订单样板的共同做法：
  模型是数据 ⇒ 清单是派生的；操作空间＝模型定义的空间，「不存在」本身就是设计）。

★ 产物两份（构建产物，不手改）：
  · `手册.json` —— 机器读：动作名／参数（必填·类型·取值域）／谁能办（scope）／失败策略／拒绝码／话题；
  · `手册.md`   —— 人读：同上，排版成表。
★ 用法：
  python scripts/release/make-manual.py                 # 写到 ./手册/
  python scripts/release/make-manual.py --out-dir D:/x  # 写到别处
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src", "ontology"), os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ontology_definition import build_aios_ontology  # noqa: E402
from world_codes import REJECT_CODES  # noqa: E402

TOPICS = {
    "ask": "world/ask（请求入口；只有本体订）",
    "ask_result": "world/ask/result（本体拒／执行器结果都回这里）",
    "exec": "world/exec（本体转给提供者；带 permit 凭证）",
    "register": "world/register（安装时注册一次）",
    "appear": "world/appear（报到：成为个体；带 reporter）",
    "query": "world/query（查世界／查动作／查历史）",
    "notice": "world/notice（宣告：经本体转给呈现）",
}


def build_manual(ontology=None):
    """★ 从本体生成手册（纯数据）。"""
    o = ontology or build_aios_ontology()
    grants = (o.metadata.get("permissions") or {}).get("grants") or {}
    actions = []
    for name, at in sorted(o.action_types.items()):
        g = grants.get(name) or {}
        md = getattr(at, "metadata", None) or {}
        actions.append({
            "name": name,
            "kind": md.get("kind"),
            "reversible": md.get("reversible"),
            "on_failure": md.get("on_failure"),
            "params": [{
                "name": p.name,
                "required": bool(getattr(p, "required", False)),
                "type": getattr(getattr(p, "param_type", None), "name",
                                str(getattr(p, "param_type", None))),
                "options": getattr(p, "options", None),
            } for p in (getattr(at, "parameters", None) or [])],
            "scope": list(g.get("scope") or []),
        })
    return {
        "world": (o.metadata or {}).get("world", 1),
        "actions": actions,
        "reject_codes": dict(REJECT_CODES),
        "topics": dict(TOPICS),
    }


def to_markdown(manual):
    """★ 人读版：能做哪些事／每件事参数／谁能办／拒绝码／怎么调用。"""
    lines = ["# 应用手册（从本体生成）", "",
             "> ★ 本件是**生成物**（`scripts/release/make-manual.py`），不是手写件；改本体后重跑生成器。",
             "> ★ 应用**不需要备一份本体**——照着这份手册说、照着这份手册接。", "",
             "## 一、能办的事（%d 件）" % len(manual["actions"]), "",
             "| 动作 | 参数 | 谁能办（scope） | 失败策略 |", "|---|---|---|---|"]
    for a in manual["actions"]:
        ps = "；".join(("%s%s" % (p["name"], "" if p["required"] else "（选填）")) for p in a["params"]) or "（无）"
        lines.append("| `%s` | %s | %s | %s |" % (a["name"], ps, "、".join(a["scope"]) or "（无人）",
                                                a["on_failure"] or "?"))
    lines += ["", "## 二、拒绝码（闭集）", ""]
    for code, cat in sorted(manual["reject_codes"].items()):
        lines.append("- `%s` —— %s" % (code, cat))
    lines += ["", "## 三、怎么调用（话题）", ""]
    for k, v in manual["topics"].items():
        lines.append("- **%s**：`%s`" % (k, v))
    lines += ["", "## 四、参数明细", ""]
    for a in manual["actions"]:
        if not a["params"]:
            continue
        lines.append("### `%s`" % a["name"])
        for p in a["params"]:
            opt = ("（取值：%s）" % p["options"]) if p.get("options") else ""
            lines.append("- `%s`：%s%s%s" % (p["name"], p["type"], "" if p["required"] else "（选填）", opt))
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    out_dir = os.path.join(ROOT, "手册")
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    os.makedirs(out_dir, exist_ok=True)
    manual = build_manual()
    with open(os.path.join(out_dir, "手册.json"), "w", encoding="utf-8") as f:
        json.dump(manual, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(out_dir, "手册.md"), "w", encoding="utf-8") as f:
        f.write(to_markdown(manual))
    print("★ 生成 %s（动作 %d 件 / 拒绝码 %d 条）"
          % (out_dir, len(manual["actions"]), len(manual["reject_codes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
