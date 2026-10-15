#!/usr/bin/env python3
"""C9 —— **降级分支必须显式、不许静默**：每一处**静默兜底**都要**登记在册**（H13 的判据面）。

红＝上游件里出现**未登记**的静默兜底臂：形如 `Some("X" | _) | None => …`（认不得就当某个默认值）。

为什么（口径来源）：
· ★ 来源2-A13 借的是**纪律**：aios-fs `05_namespace_layout.md:518` 逐字「Failure modes — all fail closed:」；
  要的是「**凡降级分支，必须显式返回一个码，不许静默放行**」。
· ★ 上游 `crates/aios-fs/src/in_memory.rs` 里**已知有**这种臂（我们登记过一处注释，见
  `verify/allowed_upstream_edits.txt` 的 T-30 行）；本判据把它变成**机器可判**的一件事：
  **每一处都要点名**，新的不许悄悄出现。
· ★ **登记 ≠ 判违规**（照测试席 G-08 的口径）：本判据只判「**有没有点名**」，不判「该不该改」。

用法：
  python verify/c9_silent_fallbacks_registered.py              跑真仓库
  python verify/c9_silent_fallbacks_registered.py --self-test  反例自检
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ★ 射程写死在一个件上（今天**已知有**静默兜底的就是它）；扩射程要另开口，不悄悄扩。
SCANNED = os.path.join("crates", "aios-fs", "src", "in_memory.rs")
REGISTRY = os.path.join("verify", "c9_known_silent_fallbacks.txt")
PATTERN = re.compile(r"\|\s*_\)\s*\|\s*None\s*=>")
NAME = "C9 静默兜底必须登记在册"


def judge(lines):
    """纯函数：[(行号, 行文本)] ⇒ [静默兜底所在行号]。"""
    return [n for n, text in lines if PATTERN.search(text)]


def collect():
    with open(SCANNED, "r", encoding="utf-8") as fh:
        return [(i + 1, line) for i, line in enumerate(fh.read().splitlines())]


def known():
    out = set()
    if os.path.exists(REGISTRY):
        with open(REGISTRY, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    out.add(int(line.split("#")[0].strip()))
    return out


def self_test():
    fallback = '        Some("SENSITIVE" | _) | None => PrivacyClass::Sensitive,'
    plain = '        Some("USER") => ScopeKind::User,'
    cases = [
        ("反例1 认不得就当默认值（两处同形）",
         len(judge([(1, fallback), (2, plain), (3, '        Some("SYSTEM" | _) | None => ScopeBinding {')])), 2),
        ("反例2 正常分支不算",
         judge([(1, plain)]), []),
        ("正控 没有兜底臂 ⇒ 空",
         judge([(1, "        let x = 1;")]), []),
    ]
    bad = [(n, g, w) for n, g, w in cases if g != w]
    if bad:
        for n, g, w in bad:
            print("  [SELF-TEST FAIL] %s：期望 %r，实得 %r" % (n, w, g))
        return 1
    print("  [SELF-TEST OK] 反例 2 条；正控 1 条")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        lines = collect()
    except OSError as exc:
        print("  [ENV] 读不到被扫件：%s（环境问题，不是判断）" % exc)
        return 2
    found = judge(lines)
    registered = known()
    new = [n for n in found if n not in registered]
    print("  现取：被扫 %s；静默兜底 %d 处；已登记 %d 处"
          % (SCANNED, len(found), len(registered)))
    if new:
        print("  [RED] 出现**未登记**的静默兜底（认不得就当默认值）：")
        for n in new:
            print("        %s:%d" % (SCANNED, n))
        return 1
    print("  [GREEN] %d 处静默兜底全部点名在册（见 %s）" % (len(found), REGISTRY))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
