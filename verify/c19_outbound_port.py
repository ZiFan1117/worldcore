#!/usr/bin/env python3
"""C19 —— **出向口唯一**：执行必须经过那一个口，不许有第二条路。

★ 形态：**判文本**（★ 与本仓 C3／C18 同族）—— 因为**行为**要在 VM 上跑 cargo 才能验（★ 宿主无 cargo）。
★ 本判据能判什么、不能判什么，写在下面「限度」一节里（★ 不夸大）。

为什么（口径来源）：
· ★ 评审席甲（方案v2 必闭1）逐字：★「批一红例『把总线断开 ⇒ 调用必须失败』**无法构造** —— 载体 A 里根本没有总线」⇒ 改成**结构判据**；
· ★ 作者令：「**开始实施烟囱式的执行**」⇒ 七件事第二件（出向口）。
· 
· 红＝ `crates/aios-worldcore/src/**` 里，调执行体的地方（`.run(` 且是 `executor.run` 形状）**不止一处**。
· ★ 今天现取：★ **只有 `engine/execute.rs` 那一处**（⑤ 五步全过才交给执行体）。

限度（★ 如实）：
· ★ 判文本 ⇒ ★ **证不了运行时行为**（那要靠 VM 上的 `cargo test`）；
· ★ 它证的是：★ **这几处形状在、且没有被绕过**。

用法：
  python verify/c19_outbound_port.py              跑真仓库
  python verify/<SELF> --self-test   反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WS = os.path.join("crates", "aios-worldcore", "src")


def walk(root):
    out = []
    for base, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".rs"):
                out.append(os.path.join(base, f))
    return out


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def report(name, bad, extra=""):
    print("=== %s（%s）===" % (name, extra or "真仓库"))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0
NAME = "C19 出向口唯一"


def calls(text):
    """数『把活交给执行体』的调用点（按行）。"""
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if s.startswith("//") or s.startswith("///") or s.startswith("*"):
            continue
        # ★ 只数【交给执行体】的那一个形状（★ `Query::…run()` 那种不是执行体 —— 别误判）
        if "executor.run(" in s:
            hits.append((i, s))
    return hits


def scan(root):
    bad = []
    total = []
    for p in walk(root):
        for i, s in calls(read(p)):
            total.append("%s:%d: %s" % (p, i, s))
    if len(total) != 1:
        bad.append("★ 交给执行体的口有 %d 处（必须恰好 1 处）：%s" % (len(total), total))
    return bad, total


def run(label="真仓库"):
    bad, total = scan(WS)
    rc = report(NAME, bad, label)
    print("  现取：口 %d 处 %s" % (len(total), total[:1]))
    return rc


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    red = calls("fn a() { self.executor.run(x, y, z) }\nfn b() { self.executor.run(x, y, z) }")
    print("=== 红例（两处调用）⇒ 命中 %d 处 ===" % len(red))
    if len(red) != 2:
        print("[自检失败] 红例该数到 2 处")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())