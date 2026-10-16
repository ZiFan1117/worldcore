#!/usr/bin/env python3
"""C16 —— **每个在册动作必须回答「它是哪一类注册者注册的」**（三方同构这件事，机器盯着）。

红＝
  (a) `actions.<名>` 缺 `registered_by_kind`（或为空）⇒ 红；
  (b) 值不在闭集内 ⇒ 红。

★ 闭集（四类，逐字依据作者 2026-10-16 令）：
  · `world`     —— ★ **世界自身**的动作（出厂九条属此类）；
  · `system`    —— ★ **底层系统工具**（作者逐字：「**底层的这个底层的系统工具**」）；
  · `app`       —— ★ **开发的上层应用**（作者逐字：「**开发的上层应用**」）；
  · `interface` —— ★ **界面**（作者逐字：「**包括那个 A2UI 的那个 GUI 都是这个逻辑**」）。

为什么（口径来源，逐字）：
· ★ 作者 2026-10-16：「**同样的道理，就是无论是底层的这个底层的系统工具，以及就是开发的上层应用，
  都应该是按照这个逻辑，包括那个 A2UI 的那个 GUI 都是这个逻辑**」；
· ★ 上一轮（T-231）已落 `registered_by`（谁注册的）与 `transport`／`endpoint`（怎么叫它）；
  本判据补的是**类别**这一格 —— ★ **三方同构**由此成为**机器可判**的一件事。

用法：
  python verify/c16_registration_kind.py              跑真仓库
  python verify/c16_registration_kind.py --self-test   反例自检
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONT = os.path.join("crates", "aios-ontology", "data", "ontology.json")
NAME = "C16 注册者类别"
KINDS = ("world", "system", "app", "interface")


def scan(doc):
    bad = []
    for k, v in (doc.get("actions", {}) or {}).items():
        if k.startswith("_"):
            continue
        if not isinstance(v, dict):
            continue
        kind = str(v.get("registered_by_kind", "")).strip()
        if not kind:
            bad.append("actions.%s：缺 registered_by_kind（哪一类注册者）" % k)
        elif kind not in KINDS:
            bad.append("actions.%s：registered_by_kind=%r 不在闭集 %s 内" % (k, kind, list(KINDS)))
    return bad


def run(path=None, label="真仓库"):
    with open(path or ONT, "r", encoding="utf-8") as f:
        doc = json.load(f)
    bad = scan(doc)
    print("=== %s（%s）===" % (NAME, label))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    red1 = {"actions": {"systemctl.start": {"registered_by": "systemctl"}}}
    b1 = scan(red1)
    print("=== 红例1（缺 registered_by_kind）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 应当命中，却绿")
        ok = False
    red2 = {"actions": {"foo.bar": {"registered_by": "x", "registered_by_kind": "magic"}}}
    b2 = scan(red2)
    print("=== 红例2（类别不在闭集内）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 应当命中，却绿")
        ok = False
    green = {"actions": {
        "world.a":  {"registered_by_kind": "world"},
        "sys.a":    {"registered_by_kind": "system"},
        "app.a":    {"registered_by_kind": "app"},
        "ui.a":     {"registered_by_kind": "interface"},
    }}
    b3 = scan(green)
    print("=== 绿例（四类各一）⇒ 命中 %d 处 ===" % len(b3))
    if b3:
        print("[自检失败] 绿例不该命中：%r" % b3)
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、绿例会绿）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())