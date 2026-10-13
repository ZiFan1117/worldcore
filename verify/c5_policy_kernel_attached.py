#!/usr/bin/env python3
"""C5 —— 生产路径必须挂策略核（★ 本轮烟囱实测抓出的洞；本版是**回归守卫**）。

红＝生产面（`crates/*/src/**/*.rs`，不含 tests）里出现**新**的「未挂策略核」命中，且没登记在
     `verify/c5_known_unattached.txt` 里。

两段口径（分开报）：
  · **段一（构造点）**：同件里出现 `InMemoryCapabilityRuntime::new(` 而**没有** `with_policy_kernel`；
  · **段二（提交点）**：同件里出现 `submit_action` 而**没有** `with_policy_kernel`。

为什么：T-A 烟囱实测 —— 裸 runtime（未挂 kernel）`submit_action` ⇒ **`status=Succeeded`**；
挂上 kernel 才 `PolicyDenied`。⇒ **「默认拒」在 policy kernel 里，不在 runtime 里**；
⇒ **谁不挂 kernel，谁就能交动作并成功**。
★ 而 `crates/aios-capability-runtime/src/runtime.rs` 逐字写着 T-027 出厂时把
  「adapter registry(T-028)／dispatch queue(T-029)／**policy kernel(T-030)**……」留作后继任务
  ⇒ **这条线是上游文档化的未接项**；但**后果一样**。

★ **为什么用登记面而不是直接判红**：现状有 ~10 件生产件未挂（含 gRPC 服务端），
  改它们属**阶段二「重梳理」**；⇒ 本判据先做**「防新增」的回归守卫**：
  **已登记的现状可见（判据会把它们打印出来）**，**未登记的新命中才红**。
★ 口径限制：文本级近似 —— 命中的件要**逐件人工核**（挂载未必在同一件里）。

用法：
  python verify/c5_policy_kernel_attached.py              跑真仓库
  python verify/c5_policy_kernel_attached.py --self-test  反例自检（未登记的新命中 ⇒ 红）
"""
import os
import sys

# ★ 输出归一：本机默认 stdout 是 GBK，印中文会崩；判据不许依赖环境（2026-10-13 教训）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CRATES = "crates"
REGISTRY = os.path.join("verify", "c5_known_unattached.txt")
CONSTRUCT = "InMemoryCapabilityRuntime::new("
SUBMIT = "submit_action"
ATTACH = "with_policy_kernel"
NAME = "C5 生产路径必须挂策略核"
SKIP_DIRS = ("tests", "target", "benches", "examples")


def load_registry(path=REGISTRY):
    known = set()
    if not os.path.exists(path):
        return known
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            known.add(line.split("#")[0].strip())
    return known


def judge(files):
    """纯函数：files = [(rel_path, text)] ⇒ (段一命中, 段二命中)。"""
    stage1, stage2 = [], []
    for path, text in files:
        if ATTACH in text:
            continue
        if CONSTRUCT in text:
            stage1.append(path)
        if SUBMIT in text:
            stage2.append(path)
    return stage1, stage2


def collect():
    files = []
    for dirpath, dirnames, filenames in os.walk(CRATES):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        norm = dirpath.replace(os.sep, "/")
        if "/src" not in norm:
            continue
        for fn in filenames:
            if not fn.endswith(".rs"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, os.getcwd()).replace(os.sep, "/")
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    files.append((rel, fh.read()))
            except OSError:
                pass
    return files


def self_test():
    known = {"crates/known/src/x.rs"}
    s1, s2 = judge([
        # ★ 反例要**同时**含构造与提交，才会在两段都命中（第一版自检就是漏了 submit_action 才假失败）
        ("crates/new/src/a.rs", "let r = InMemoryCapabilityRuntime::new(); r.submit_action(e, c);"),
        ("crates/known/src/x.rs", "let r = InMemoryCapabilityRuntime::new(); r.submit_action(e, c);"),
        ("crates/ok/src/b.rs", "let r = InMemoryCapabilityRuntime::new().with_policy_kernel(k); r.submit_action(e, c);"),
    ])
    new1 = [p for p in s1 if p not in known]
    new2 = [p for p in s2 if p not in known]
    problems = []
    if new1 != ["crates/new/src/a.rs"]:
        problems.append("段一未登记命中判定不对：%s" % new1)
    if new2 != ["crates/new/src/a.rs"]:
        problems.append("段二未登记命中判定不对：%s" % new2)
    if [p for p in s2 if p in known] != ["crates/known/src/x.rs"]:
        problems.append("已登记项没有出现在段二命中里")
    if problems:
        for p in problems:
            print("  [SELF-TEST FAIL] " + p)
        return 1
    print("  [SELF-TEST OK] 未登记的新命中会红；已登记项照常命中但不报红")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        files = collect()
        known = load_registry()
    except OSError as exc:
        print("  [ENV] 取不到源码：%s（环境问题，不是判断）" % exc)
        return 2
    stage1, stage2 = judge(files)
    new1 = [p for p in stage1 if p not in known]
    new2 = [p for p in stage2 if p not in known]
    print("  已登记现状：段一 %d 件／段二 %d 件（共扫 %d 件 src/*.rs）" % (len(stage1), len(stage2), len(files)))
    if new1 or new2:
        print("  [RED] 出现**未登记**的未挂策略核命中：")
        for p in new1:
            print("        段一（构造点）：%s" % p)
        for p in new2:
            print("        段二（提交点）：%s" % p)
        return 1
    print("  [GREEN] 没有新出现的未挂策略核命中（已登记现状：段一 %d 件／段二 %d 件；登记面 %s）"
          % (len(stage1), len(stage2), REGISTRY))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
