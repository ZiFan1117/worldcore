#!/usr/bin/env python3
"""C14 —— **函数入口表里不许出现命令字面量**（上位＝本体自己那条规矩）。

红＝ `crates/aios-ontology/data/ontology.json` 的 `functions.entries` 里出现：
  (a) 命中 `functions._registered_host_commands` 里已登记的宿主命令名（全字段扫）；
  (b) `function_id` 或机制类字段（`implementation`／`command`／`mechanism`／`program`／`args`）里
      出现【带空格】【带 `/` 的路径】【带引号】三者任一（★ 只扫这两处，不扫 description／display_name）。

为什么（口径来源，逐字）：
· ★ 本体 `functions._no_command_literal` 逐字：「★ 判据：入口表里出现**命令字面量**（带空格、带 `/` 的路径、
  带引号，或**已登记的宿主包管理器命令名**）⇒ 红（`ext.world.Ontology.FunctionLiteralNotAllowed`）。
  ★ 理由：命令今天硬编码在 Rust 里（`src/carrier/**`），把 `pacman` 这类字面量抄进本体等于让本体长出
  **第二份**可执行事实。」
· ★ 本体 `functions._comment` 逐字：「**代码不进本体**」。

★ 收窄的理由（照 C11 那次**假红**的教训）：`description`／`display_name` 是人读的说明，
  里面本来就会出现空格与「不抄 implementation」这类**引文** ⇒ 扫它们必然假红。

用法：
  python verify/c14_no_command_literal.py              跑真仓库
  python verify/c14_no_command_literal.py --self-test   反例自检（红例必须红、绿例必须绿）
"""
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONT = os.path.join("crates", "aios-ontology", "data", "ontology.json")
NAME = "C14 函数入口表不许出现命令字面量"
MECH_FIELDS = ("implementation", "command", "mechanism", "program", "args")


def load(path=None):
    with open(path or ONT, "r", encoding="utf-8") as f:
        return json.load(f)


def scan(doc):
    """返回违规清单（每条一个字符串）。"""
    fns = doc.get("functions", {})
    entries = fns.get("entries", {}) or {}
    hosts = fns.get("_registered_host_commands", []) or []
    bad = []
    for key, val in entries.items():
        # (a) 全字段扫：已登记的宿主命令名
        blob = json.dumps(val, ensure_ascii=False) + " " + key
        for h in hosts:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(h) + r"(?![A-Za-z0-9_])", blob):
                bad.append("%s：出现已登记的宿主命令名 %r" % (key, h))
        # (b) function_id ＋ 机制类字段：空格／路径／引号
        parts = [("function_id(键)", key)]
        if isinstance(val, dict):
            if "function_id" in val:
                parts.append(("function_id(值)", str(val["function_id"])))
            for f in MECH_FIELDS:
                if f in val:
                    parts.append((f, json.dumps(val[f], ensure_ascii=False)))
        for label, text in parts:
            if " " in text.strip():
                bad.append("%s.%s：带空格（疑命令字面量）：%r" % (key, label, text))
            if "/" in text:
                bad.append("%s.%s：带 `/`（疑路径）：%r" % (key, label, text))
            if ("\"" in text) or ("'" in text):
                bad.append("%s.%s：带引号：%r" % (key, label, text))
    return bad


def run(path=None, label="真仓库"):
    doc = load(path)
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
    """★ 硬约束 9：每条判据必须自带会红的反例。"""
    ok = True
    # 绿例：真仓库（应当绿）
    rc_real = run(label="绿例·真仓库")
    if rc_real != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    # 红例 1：宿主命令名
    red1 = {"functions": {"_registered_host_commands": ["pacman", "apt", "systemctl"],
                          "entries": {"fn.bad.one": {"function_id": "fn.bad.one",
                                                     "display_name": "坏的例子",
                                                     "description": "用 pacman 装东西（应当被 C14 判红）"}}}}
    b1 = scan(red1)
    print("=== 红例1（宿主命令名写在描述里）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 应当命中，却绿")
        ok = False
    # 红例 2：机制类字段带空格 + 路径
    red2 = {"functions": {"_registered_host_commands": ["pacman"],
                          "entries": {"fn.bad.two": {"function_id": "fn.bad.two",
                                                     "command": "pacman -S neovim"}}}}
    b2 = scan(red2)
    print("=== 红例2（command 里写命令）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 应当命中，却绿")
        ok = False
    # 绿例 2：正常的入口名（不应当红）
    green = {"functions": {"_registered_host_commands": ["pacman"],
                           "entries": {"fn.notice.mute": {"function_id": "fn.notice.mute",
                                                          "display_name": "把一条通告静音",
                                                          "description": "动作 notice.mute 的实现面；不抄 implementation",
                                                          "inputs": {"subject": "enum(change,act,notice,job)"},
                                                          "output_type": "enum(change,act,notice,job)"}}}}
    b3 = scan(green)
    print("=== 绿例2（正常入口名 ＋ 说明里带空格与引文）⇒ 命中 %d 处 ===" % len(b3))
    if b3:
        print("[自检失败] 绿例2 不该命中（说明字段允许空格）：%r" % b3)
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、绿例会绿）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())