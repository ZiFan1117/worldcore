#!/usr/bin/env python3
"""C18 —— **账要落盘，且落盘必须【先落盘、后入内存】**（T-242 批零）。

★ 这条判据**判文本**（★ 是本仓判据的常见形态之一：C3「翻译链已查表并可拒」也是判文本）——
  因为**行为**要在 VM 上跑 cargo 才能验（★ 宿主无 cargo ⇒ 行为读数只能在 VM）。

红＝
  (a) `engine/ledger.rs` 里没有**从盘读回**的口（`pub fn load_file(`）⇒ 红；
  (b) 没有**落盘追加**的口（`pub fn append_persisting(`）⇒ 红；
  (c) 落盘追加里 **`writeln!` 出现在 `self.rows.push(` 之后** ⇒ 红
      —— ★★ 那意味着**内存先收下了**、盘没写成就白收了（★ 与「被拒的那一笔不留痕」相反）；
  (d) 从盘读回里**没有核对指纹**（`fingerprint(`）⇒ 红
      —— ★ 只读不算 ＝ 重算链 ＝ **把防篡改关掉**；
  (e) `ledger/tests.rs` 里没有**「重开一本 ⇒ 那一笔还在」**的断言 ⇒ 红。

为什么（口径来源）：
· ★★ 评审席甲（2026-10-16 方案v2 评审，必闭3）：『只落正文不落链节 ⇒ 重启后 verify() 必坏，
  或更坏：静默重链 ⇒ 篡改不可察』；
· ★★ 评审席甲（必闭2）：『kill 进程今天不可执行（载体 A 是库）』⇒ 红例改成**库级两步**；
· ★ 作者令：「**开始实施烟囱式的执行**」⇒ 七件事的第一件＝批零（账落盘）。

用法：
  python verify/c18_ledger_persisted.py              跑真仓库
  python verify/c18_ledger_persisted.py --self-test   反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

LEDGER = os.path.join("crates", "aios-worldcore", "src", "engine", "ledger.rs")
TESTS = os.path.join("crates", "aios-worldcore", "src", "engine", "ledger", "tests.rs")
NAME = "C18 账落盘（先落盘、后入内存）"


def scan(ledger_text, tests_text):
    bad = []
    if "pub fn load_file(" not in ledger_text:
        bad.append("ledger.rs：没有从盘读回的口（load_file）")
    if "pub fn append_persisting(" not in ledger_text:
        bad.append("ledger.rs：没有落盘追加的口（append_persisting）")
    # (c) 先落盘、后入内存
    i_write = ledger_text.find("writeln!(fh,")
    i_push = ledger_text.find("self.rows.push(row);", ledger_text.find("pub fn append_persisting(") if "pub fn append_persisting(" in ledger_text else 0)
    if i_write < 0:
        bad.append("ledger.rs：落盘追加里没有 writeln!(fh, …)（没真写下去）")
    elif i_push < 0:
        bad.append("ledger.rs：落盘追加里没有 self.rows.push（没入内存）")
    elif i_push < i_write:
        bad.append("ledger.rs：★ self.rows.push 出现在 writeln! 之前 —— 内存先收下了")
    # (d) 读回要核对指纹
    i_lf = ledger_text.find("pub fn load_file(")
    if i_lf >= 0 and "seal::fingerprint(&row)" not in ledger_text[i_lf:]:
        bad.append("ledger.rs：从盘读回里没有核对指纹（只读不算 ⇒ 重算链 ⇒ 篡改不可察）")
    # (e) 测试里要有重开断言
    if "load_file(" not in tests_text:
        bad.append("tests.rs：没有「从盘读回」的测试")
    return bad


def run(label="真仓库"):
    with open(LEDGER, "r", encoding="utf-8") as f:
        lt = f.read()
    with open(TESTS, "r", encoding="utf-8") as f:
        tt = f.read()
    bad = scan(lt, tt)
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
    # 红例：先入内存、后落盘
    red = ("pub fn load_file(text: &str, path: &str) -> Admit<Self> { seal::fingerprint(&row) }\n"
           "pub fn append_persisting(\n    ) -> Admit<EventSeq> {\n self.rows.push(row);\n writeln!(fh, x);\n}\n")
    b1 = scan(red, "load_file(")
    print("=== 红例（先 push 后 writeln）⇒ 命中 %d 处 ===" % len(b1))
    if not any("push" in x for x in b1):
        print("[自检失败] 红例该命中「内存先收下」，却没命中")
        ok = False
    # 绿例
    green = (LEDGER_GOOD, "load_file(")
    b2 = scan(green[0], green[1])
    print("=== 绿例（全齐）⇒ 命中 %d 处 ===" % len(b2))
    if b2:
        print("[自检失败] 绿例不该命中：%r" % b2)
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、绿例会绿）" if ok else "有失败"))
    return 0 if ok else 1


LEDGER_GOOD = ("pub fn load_file(text: &str, path: &str) -> Admit<Self> { seal::fingerprint(&row) }\n"
               "pub fn append_persisting(\n    ) -> Admit<EventSeq> {\n writeln!(fh, x);\n self.rows.push(row);\n}\n")


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())