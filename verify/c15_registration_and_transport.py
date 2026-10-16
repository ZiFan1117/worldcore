#!/usr/bin/env python3
"""C15 —— **每个在册动作必须回答「谁注册的」，每条入口名必须回答「怎么调」。**

红＝
  (a) `actions.<名>` 缺 `registered_by`（或为空）⇒ 红；
  (b) `functions.entries.<fn>` 缺 `transport` **且** 表级也没有 `_transport` ⇒ 红；
  (c) `functions.entries.<fn>` 缺 `endpoint` ⇒ 红。

为什么（口径来源，逐字）：
· ★ 作者 2026-10-16：「**一个软件注册进来以后，它的 action 呀，这些都应该都注册进来的**」；
· ★ 作者 2026-10-16：「**我审批了，你走总线去调用这个东西，不就完事了吗**」；
· ★ 作者 2026-10-16：「**人家本来这个软件就有一些对外的接口**……**我没必要重新说一下我重新再造一套呀**」
  ⇒ ★ 本体只登记**对方的对外接口地址**（`endpoint`），★ **不复制对方的接口**。

用法：
  python verify/c15_registration_and_transport.py              跑真仓库
  python verify/c15_registration_and_transport.py --self-test   反例自检
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONT = os.path.join("crates", "aios-ontology", "data", "ontology.json")
NAME = "C15 注册者与调用方式"


def scan(doc):
    bad = []
    acts = doc.get("actions", {}) or {}
    for k, v in acts.items():
        if k.startswith("_"):
            continue
        if not isinstance(v, dict) or not str(v.get("registered_by", "")).strip():
            bad.append("actions.%s：缺 registered_by（谁注册的）" % k)
    fns = (doc.get("functions", {}) or {})
    entries = fns.get("entries", {}) or {}
    table_transport = str(fns.get("_transport", "")).strip()
    for k, v in entries.items():
        if k.startswith("_"):
            continue
        if not isinstance(v, dict):
            continue
        if not str(v.get("transport", "")).strip() and not table_transport:
            bad.append("functions.entries.%s：缺 transport（怎么调）" % k)
        if not str(v.get("endpoint", "")).strip():
            bad.append("functions.entries.%s：缺 endpoint（对方的对外接口）" % k)
    return bad


def load(path=None):
    with open(path or ONT, "r", encoding="utf-8") as f:
        return json.load(f)


def run(path=None, label="真仓库"):
    bad = scan(load(path))
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
    red1 = {"actions": {"notice.mute": {"function": "fn.notice.mute"}},
            "functions": {"_transport": "走总线", "entries": {"fn.notice.mute": {"transport": "bus", "endpoint": "bus:world.fn.notice.mute"}}}}
    b1 = scan(red1)
    print("=== 红例1（动作缺 registered_by）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 应当命中，却绿")
        ok = False
    red2 = {"actions": {"notice.mute": {"registered_by": "builtin"}},
            "functions": {"entries": {"fn.notice.mute": {"transport": "bus"}}}}
    b2 = scan(red2)
    print("=== 红例2（函数缺 endpoint）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 应当命中，却绿")
        ok = False
    green = {"actions": {"notice.mute": {"registered_by": "builtin"}},
             "functions": {"entries": {"fn.notice.mute": {"transport": "bus", "endpoint": "bus:world.fn.notice.mute"}}}}
    b3 = scan(green)
    print("=== 绿例（三格齐全）⇒ 命中 %d 处 ===" % len(b3))
    if b3:
        print("[自检失败] 绿例不该命中：%r" % b3)
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、绿例会绿）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())