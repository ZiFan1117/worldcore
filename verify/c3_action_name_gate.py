#!/usr/bin/env python3
"""C3 —— 未登记的动作名必须被拒（语义面第一条真判据）。

要判的是：**AIOS 认知核的翻译链，在把 action_name 塞进 Request 之前，查过能力表、且表里没有就拒。**

三条同时成立才算绿（今天三条都不成立 ⇒ 本条**应当先红**，接线之后转绿）：
  A. crates/aios-cognitive/src 里出现**能力表**符号（CapabilityCatalog / action_kind）
  B. 同域里出现**拒绝语义**（UnknownAction / UNKNOWN_ACTION / REJECTED / invalid_action）
  C. **构造 Request 的那个文件**里同时出现 A 与 B（= 在构造前查表并可能拒）

用法：
  python verify/c3_action_name_gate.py              跑真仓库
  python verify/c3_action_name_gate.py --self-test  反例自检（喂假内容：先红后绿都要验）
"""
import os
import re
import sys

TARGET = os.path.join("crates", "aios-cognitive", "src")
TABLE_SYMS = ("CapabilityCatalog", "action_kind", "declared_actions")
# ★ 只认「针对动作名的拒绝」——不认泛泛的 rejected（英文注释里到处是，会假命中）
REJECT_SYMS = ("UnknownAction", "UNKNOWN_ACTION", "UNKNOWN_ACTION_KIND", "ActionUnknown", "invalid_action", "ActionNotDeclared")
BUILD_SYMS = ("Request::new", "Request {")

NAME = "C3 未登记动作名即拒"


def judge(files):
    """纯函数：files = [(rel_path, text)]，返回 (是否过, 三条明细)。"""
    a_hit = [(p, [s for s in TABLE_SYMS if s in t]) for p, t in files]
    a_hit = [(p, s) for p, s in a_hit if s]
    b_hit = [(p, [s for s in REJECT_SYMS if s in t]) for p, t in files]
    b_hit = [(p, s) for p, s in b_hit if s]
    c_hit = []
    for p, t in files:
        if any(s in t for s in BUILD_SYMS):
            ok_a = any(s in t for s in TABLE_SYMS)
            ok_b = any(s in t for s in REJECT_SYMS)
            c_hit.append((p, ok_a, ok_b))
    c_ok = [x for x in c_hit if x[1] and x[2]]
    detail = {
        "A 能力表符号": a_hit,
        "B 拒绝语义": b_hit,
        "C 构造 Request 的文件里同时有 A 与 B": c_ok,
    }
    passed = bool(a_hit) and bool(b_hit) and bool(c_ok)
    return passed, detail


def load(root):
    files = []
    for dirpath, _d, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".rs"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, os.getcwd()).replace(os.sep, "/")
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as fh:
                        files.append((rel, fh.read()))
                except OSError:
                    pass
    return files


def self_test():
    """反例：未接线的翻译链必须判红；接线后的假内容必须判绿。"""
    red_case = [("crates/aios-cognitive/src/translator_engine.rs",
                 "let req = Request::new(parsed.action_name, v);")]
    green_case = [("crates/aios-cognitive/src/translator_engine.rs",
                   "let catalog: CapabilityCatalog = load();\n"
                   "let kind = catalog.resolve(name).ok_or(Error::UnknownAction)?;\n"
                   "let req = Request::new(kind, v);")]
    ok_red, d_red = judge(red_case)
    ok_green, d_green = judge(green_case)
    if ok_red:
        print("  [SELF-TEST FAIL] 未接线的反例没有被判红")
        return 1
    if not ok_green:
        print("  [SELF-TEST FAIL] 接线后的正控没有判绿：%s" % d_green)
        return 1
    print("  [SELF-TEST OK] 反例红、正控绿")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not os.path.isdir(TARGET):
        print("  [ENV] 找不到 %s/（环境问题，不是判断）" % TARGET)
        return 2
    files = load(TARGET)
    passed, detail = judge(files)
    if passed:
        print("  [GREEN] 翻译链已查表并可拒（扫 %d 件）" % len(files))
        return 0
    print("  [RED] 翻译链未接能力表校验（扫 %d 件）—— 明细：" % len(files))
    for k, v in detail.items():
        print("        %s：%d 处" % (k, len(v)))
    print("        ⇒ 这正是 T-14 第 1 条要接的那根线（未登记即拒）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
