#!/usr/bin/env python3
"""C12 —— **本体里的文本不许有「坏转义」**（控制字符）。

红＝本体的字符串里出现控制字符转义 \\u00XX（XX ≤ 1F），**除了** 制表／换行／回车这三样
（\\u0009／\\u000a／\\u000d —— 它们是有意义的空白）。

为什么（来历 · 2026-10-15 作者点出「怎么还有转义」）：
· ★ 现取：本体的 _2026-10-12_字段改名之由 那条注记里，本该是「kind」／「seq」／「at」／「actor」，
  实际写成 \\kind\\／\\seq\\／\\u0007t\\／\\u0007ctor\\ —— ★ **反引号被打成 \\、字母 a 被打成控制字符
  \\u0007（BEL）** ⇒ 那是**文本被转义处理坏过**，不是命名机制。
· ★ 本判据把它变成机器可判的：**控制字符不许出现在本体的文本里**（除了空白三样）。
· ★ **登记 ≠ 判违规**：已点名的按登记放行（见 verify/c12_known_bad_escapes.txt），
  新的不许悄悄出现 —— 修不修是人的话（★ 本体「只增不改」）。

用法：
  python verify/c12_ontology_text_has_no_bad_escapes.py              跑真仓库
  python verify/c12_ontology_text_has_no_bad_escapes.py --self-test  反例自检
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONTOLOGY = os.path.join("crates", "aios-ontology", "data", "ontology.json")
REGISTRY = os.path.join("verify", "c12_known_bad_escapes.txt")
PATTERN = re.compile(r"\\u00[01][0-9a-fA-F]")
ALLOWED = ("\\u0009", "\\u000a", "\\u000d")  # 制表／换行／回车：有意义的空白
NAME = "C12 本体文本不许有坏转义"


def judge(text_lines):
    """纯函数：本体的行 ⇒ [(行号, 坏转义)]（空白三样不算）。"""
    out = []
    for i, line in enumerate(text_lines, start=1):
        for hit in PATTERN.findall(line):
            if hit.lower() not in ALLOWED:
                out.append((i, hit.lower()))
    return out


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
    cases = [
        ("反例1 BEL 混在注记里", len(judge(["  \"x\": \"a\\u0007t\""])), 1),
        ("反例2 NUL 也一样", len(judge(["  \"x\": \"\\u0000\""])), 1),
        ("正控 换行／制表不算", len(judge(["  \"x\": \"a\\u000ab\\u0009c\""])), 0),
        ("正控 干净文本 ⇒ 0", len(judge(["  \"x\": \"at_seq\""])), 0),
    ]
    bad = [(n, g, w) for n, g, w in cases if g != w]
    if bad:
        for n, g, w in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, w, g))
        return 1
    print("  [SELF-TEST OK] 反例 2 条；正控 2 条")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        with open(ONTOLOGY, "r", encoding="utf-8") as fh:
            text_lines = fh.read().splitlines()
    except OSError as exc:
        print("  [ENV] 读不到本体：%s（环境问题，不是判断）" % exc)
        return 2
    found = judge(text_lines)
    registered = known()
    lines_hit = sorted({n for n, _ in found})
    new = [n for n in lines_hit if n not in registered]
    print("  现取：坏转义 %d 处，落在 %d 行；已登记 %d 行" % (len(found), len(lines_hit), len(registered)))
    if new:
        print("  [RED] 出现**未登记**的坏转义（控制字符混进本体文本）：")
        for n in new:
            hit = [h for ln, h in found if ln == n]
            print("        %s:%d  %s" % (ONTOLOGY, n, "、".join(sorted(set(hit)))))
        return 1
    print("  [GREEN] 坏转义全部点名在册（见 %s）" % REGISTRY)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
