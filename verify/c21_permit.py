#!/usr/bin/env python3
"""C21 —— **审批凭证**：不许自己造、要绑动作＋参数、要一号一用。

★ 形态：**判文本**（★ 与本仓 C3／C18 同族）—— 因为**行为**要在 VM 上跑 cargo 才能验（★ 宿主无 cargo）。
★ 本判据能判什么、不能判什么，写在下面「限度」一节里（★ 不夸大）。

为什么（口径来源）：
· ★ 评审席乙（方案v2 必闭3）逐字给的属性：★「必须绑『动作＋参数』（否则可挪用）」「凭证号必须进正文」「有效期与撤销」；
· ★ 作者令：「**要推送给界面，然后让人来点授权**」＋「**每次调用都带一个……凭证**」。
· 
· 红＝
·   (a) `governance/permit.rs` 不在 ⇒ 红；
·   (b) `Permit` 的**字段有 `pub` 的** ⇒ 红（★ 那外面就能自己造一个 ⇒ 「请求方自己盖章」）；
·   (c) 有 `pub fn new(` 那种**通用构造口** ⇒ 红（★ 构造口只许 `by_interface` 一个）；
·   (d) `covers(` 里**没有同时比** action 与参数指纹 ⇒ 红（★ 只比一半 ⇒ 可挪用）；
·   (e) 没有 `consume(`（一号一用）或 `is_expired(`（有效期）⇒ 红。

限度（★ 如实）：
· ★ 判文本 ⇒ ★ **证不了运行时行为**（那要靠 VM 上的 `cargo test`）；
· ★ 它证的是：★ **这几处形状在、且没有被绕过**。

用法：
  python verify/c21_permit.py              跑真仓库
  python verify/<SELF> --self-test   反例自检
"""
import os
import re
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
NAME = "C21 审批凭证"
PERMIT = os.path.join(WS, "governance", "permit.rs")


def scan(text):
    bad = []
    if not text:
        return ["governance/permit.rs：不在"]
    if "pub struct Permit" not in text:
        bad.append("permit.rs：没有 Permit")
    # 字段里不许有 pub（★ 只看 Permit 结构体那一段）
    i = text.find("pub struct Permit")
    body = text[i:text.find("}", i)] if i >= 0 else ""
    # ★ 用正则找【字段行】—— 单行样本（struct 与字段同一行）也要能判
    for m in re.finditer(r"(?:^|[{;])\s*(pub\s+\w+\s*:)", body):
        bad.append("permit.rs：Permit 的字段不得是 pub（外面就能自己造）：" + m.group(1))
    if "pub fn new(" in body or "pub fn new(" in text[:i]:
        bad.append("permit.rs：不许有通用构造口 pub fn new（构造口只许 by_interface）")
    if "pub fn by_interface(" not in text:
        bad.append("permit.rs：没有 by_interface（界面那一路的构造口）")
    j = text.find("pub fn covers(")
    if j < 0:
        bad.append("permit.rs：没有 covers（绑没绑这一次）")
    else:
        cbody = text[j:j + 300]
        if "action" not in cbody or "params_fingerprint" not in cbody:
            bad.append("permit.rs：covers 里没有同时比 action 与参数指纹（★ 只比一半 ⇒ 可挪用）")
    if "pub fn consume(" not in text:
        bad.append("permit.rs：没有 consume（一号一用）")
    if "pub fn is_expired(" not in text:
        bad.append("permit.rs：没有 is_expired（有效期）")
    return bad


def run(label="真仓库"):
    p = os.path.join(PERMIT)
    text = read(p) if os.path.exists(p) else ""
    return report(NAME, scan(text), label)


GOOD = "pub struct Permit { id: String }\npub fn by_interface() {}\npub fn covers(&self, action: &str, params_fingerprint: &str) -> bool { true }\npub fn consume() {}\npub fn is_expired() {}"


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    b1 = scan("pub struct Permit { pub id: String }\n" + GOOD.split("\n", 1)[1])
    print("=== 红例1（字段是 pub）⇒ 命中 %d 处 ===" % len(b1))
    if not any("字段" in x for x in b1):
        print("[自检失败] 红例1 该命中字段那条")
        ok = False
    b2 = scan(GOOD.replace("params_fingerprint", "other"))
    print("=== 红例2（covers 只比一半）⇒ 命中 %d 处 ===" % len(b2))
    if not any("covers" in x for x in b2):
        print("[自检失败] 红例2 该命中 covers 那条")
        ok = False
    b3 = scan(GOOD.replace("pub fn consume() {}", "").replace("pub fn is_expired() {}", ""))
    print("=== 红例3（既无 consume 又无 is_expired）⇒ 命中 %d 处 ===" % len(b3))
    if len(b3) < 2:
        print("[自检失败] 红例3 该命中两条")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())