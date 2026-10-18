#!/usr/bin/env python3
"""C10 —— **凡清除必留证**（H12 的判据面）。

红＝我方内核里出现**不带证**的清除动作，即任一条成立：
  ① engine/store.rs 里出现 op: Op::Tombstone, 或 op: Op::Purge, 的构造，
     而**它所在的那个函数**的参数表里**没有** reason；
  ② 同一处构造的**±6 行内没有** note: reason（＝把理由写进那一笔）。

为什么（口径来源）：
· ★ 来源2-A11 逐字借的是**纪律**：「**凡删除必留证**」（它 01_object_model.md:197 逐字
  「GC is **not silent**. Each GC pass writes an evidence record」）；
· ★ 我们已有的落法：delete_as／purge_as **原因为空 ⇒ 拒**（本体碑形第二样：
  「不许写「笔误」了事」）。本判据把这条纪律变成**机器可判**的：清除那一笔必须**带着证**。

★ 它不判「该不该清」，只判「**清了有没有留证**」。

用法：
  python verify/c10_removal_carries_reason.py              跑真仓库
  python verify/c10_removal_carries_reason.py --self-test  反例自检
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCANNED = os.path.join("crates", "aios-worldcore", "src", "engine", "store.rs")
OP = re.compile(r"op:\s*Op::(Tombstone|Purge),")
FN = re.compile(r"^\s*(?:pub\s+)?fn\s+([a-z_0-9]+)\s*\(")
NAME = "C10 凡清除必留证"


def judge(text_lines):
    """纯函数：store.rs 的行 ⇒ [没带证的清除构造所在行号]。

    ★ 判两样：所在的函数有没有 reason 形参 ＋ 构造附近有没有 note: reason。
    """
    bad = []
    for i, text in enumerate(text_lines):
        if not OP.search(text):
            continue
        sig = ""
        for j in range(i, max(-1, i - 30), -1):
            if FN.search(text_lines[j]):
                sig = " ".join(text_lines[j:i + 1])
                break
        nearby = "\n".join(text_lines[max(0, i - 6):i + 7])
        has_reason = "reason" in sig
        has_note = "note: reason" in nearby or "note:reason" in nearby
        if not (has_reason and has_note):
            bad.append(i + 1)
    return bad


def self_test():
    ok = [
        "    pub fn delete_as(",
        "        &mut self,",
        "        who: &Who,",
        "        key: &str,",
        "        reason: &str,",
        "    ) -> Admit<EventSeq> {",
        "        Ok(self.commit(Append {",
        "            op: Op::Tombstone,",
        "            key: key.to_string(),",
        "            reg: None,",
        "            note: reason.to_string(),",
        "        }))",
        "    }",
    ]
    no_note = [("            note: String::new()," if "note:" in l else l) for l in ok]
    no_reason = [l.replace("reason: &str,", "cause: &str,").replace("note: reason", "note: cause") for l in ok]
    cases = [
        ("正控 带 reason ＋ note: reason", judge(ok), []),
        ("反例1 有 reason 但没写进 note", judge(no_note), [8]),
        ("反例2 函数没有 reason 形参", judge(no_reason), [8]),
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
        with open(SCANNED, "r", encoding="utf-8") as fh:
            text_lines = fh.read().splitlines()
    except OSError as exc:
        print("  [ENV] 读不到被扫件：%s（环境问题，不是判断）" % exc)
        return 2
    found = judge(text_lines)
    total = sum(1 for l in text_lines if OP.search(l))
    print("  现取：被扫 %s；清除类构造 %d 处" % (SCANNED, total))
    if found:
        print("  [RED] 有清除动作**没带证**：")
        for n in found:
            print("        %s:%d" % (SCANNED, n))
        return 1
    print("  [GREEN] %d 处清除构造全部带证（reason 形参 ＋ note: reason）" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
