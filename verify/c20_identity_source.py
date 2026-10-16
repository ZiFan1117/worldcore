#!/usr/bin/env python3
"""C20 —— **身份不许自填**：门要有一个「带来源」的判定口。

★ 形态：**判文本**（★ 与本仓 C3／C18 同族）—— 因为**行为**要在 VM 上跑 cargo 才能验（★ 宿主无 cargo）。
★ 本判据能判什么、不能判什么，写在下面「限度」一节里（★ 不夸大）。

为什么（口径来源）：
· ★ 评审席乙（方案v2 必闭4）逐字：★「六批里**没有任何一批负责身份面**；今天 `Who` 类型在、来源缺」；
· ★ 作者令：「**开始实施烟囱式的执行**」⇒ 七件事第五件（身份面）。
· 
· 红＝
·   (a) `core/types.rs` 里没有 `IdentitySource`（来源这一格）⇒ 红；
·   (b) `governance/mod.rs` 里没有 `can_execute_with`（带来源的判定口）⇒ 红；
·   (c) 那个口里**没有**把非 `Issued` 的挡下来（★ 只加口不挡 = 白加）⇒ 红。

限度（★ 如实）：
· ★ 判文本 ⇒ ★ **证不了运行时行为**（那要靠 VM 上的 `cargo test`）；
· ★ 它证的是：★ **这几处形状在、且没有被绕过**。

用法：
  python verify/c20_identity_source.py              跑真仓库
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
NAME = "C20 身份不许自填"
TYPES = os.path.join(WS, "core", "types.rs")
GOV = os.path.join(WS, "governance", "mod.rs")


def scan(types_text, gov_text):
    bad = []
    if "pub enum IdentitySource" not in types_text:
        bad.append("core/types.rs：没有 IdentitySource（身份的来源这一格）")
    if "can_execute_with" not in gov_text:
        bad.append("governance/mod.rs：没有 can_execute_with（带来源的判定口）")
    else:
        i = gov_text.find("pub fn can_execute_with(")
        body = gov_text[i:i + 700]
        if "IdentitySource::Issued" not in body:
            bad.append("governance/mod.rs：can_execute_with 里没有把非 Issued 挡下来")
    return bad


def run(label="真仓库"):
    return report(NAME, scan(read(TYPES), read(GOV)), label)


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    b1 = scan("nothing", read(GOV))
    print("=== 红例1（types 里没有 IdentitySource）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    b2 = scan(read(TYPES), "pub fn can_execute_with(&self, a: &Who) -> Admit<()> { self.can_execute(a, b) }")
    print("=== 红例2（只加口、不挡）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())