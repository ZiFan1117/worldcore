#!/usr/bin/env python3
"""C12 —— **本体里的文本不许有「坏转义」**（控制字符）。

红＝本体的字符串里出现控制字符转义 \\u00XX（XX ≤ 1F），**除了** 制表／换行／回车这三样
（\\u0009／\\u000a／\\u000d —— 它们是有意义的空白）。

★ 2026-10-18 改造（作者令「把这两个问题解决」）：
  登记面**从【行号】改成【内容指纹】**——原来登记行号，每次改本体 json 行号就漂，
  一天之内重登了 4 次（10841→10869→10878→10898→11112→10993→10978→10972）。
  ⇒ 现在登记一条**上下文指纹**（那一行里必然出现的一段文字）：
     · json 重排、行号漂移 ⇒ **指纹不漂，判据照常绿**；
     · 文本真被改掉 ⇒ 指纹对不上 ⇒ **红**（还是能看见）。

为什么要有这条判据（来历 · 2026-10-15 作者点出「怎么还有转义」）：
· ★ 现取：本体的 _2026-10-12_字段改名之由 那条注记里，本该是「kind」／「seq」／「at」／「actor」，
  实际写成 \\kind\\／\\seq\\／\\u0007t\\／\\u0007ctor\\ —— ★ **反引号被打成 \\、字母 a 被打成控制字符
  \\u0007（BEL）** ⇒ 那是**文本被转义处理坏过**，不是命名机制。
· ★ **登记 ≠ 判违规**：已点名的按登记放行（见 verify/c12_known_bad_escapes.txt），
  新的不许悄悄出现 —— 修不修是人的话（★ 本体「只增不改」）。

用法：
  python verify/c12_ontology_text_has_no_bad_escapes.py              跑真仓库
  python verify/c12_ontology_text_has_no_bad_escapes.py --self-test  反例自检
"""
import os
import re
import sys

# ★ 2026-10-18：判据从 verify/ 挪到 scripts/test/ —— 登记面按【本文件所在目录】找
_HERE_ = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONTOLOGY = os.path.join("crates", "aios-ontology", "data", "ontology.json")
REGISTRY = os.path.join(_HERE_, "c12_known_bad_escapes.txt")
PATTERN = re.compile(r"\\\\u00[01][0-9a-fA-F]")
ALLOWED = ("\\\\u0009", "\\\\u000a", "\\\\u000d")  # 制表／换行／回车：有意义的空白
NAME = "C12 本体文本不许有坏转义"


def judge(text_lines):
    """纯函数：本体的行 ⇒ [(行号, 坏转义, 整行)]（空白三样不算）。"""
    out = []
    for i, line in enumerate(text_lines, start=1):
        hits = [h.lower() for h in PATTERN.findall(line) if h.lower() not in ALLOWED]
        if hits:
            out.append((i, hits, line))
    return out


def known():
    """★ 登记面：一串【内容指纹】——不是行号。"""
    out = []
    if os.path.exists(REGISTRY):
        with open(REGISTRY, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                marker = line.split("#")[0].strip()
                if marker:
                    out.append(marker)
    return out


def judge_registered(found, markers):
    """纯函数：每一条坏转义所在的**行**，必须命中【至少一条】已登记指纹，否则红。"""
    red = []
    for lineno, hits, line in found:
        if not any(m in line for m in markers):
            red.append((lineno, hits, line))
    return red


def self_test():
    cases = [
        ("反例1 BEL 混在注记里", len(judge(['  "x": "a\\\\u0007t"'])), 1),
        ("反例2 NUL 也一样", len(judge(['  "x": "\\\\u0000"'])), 1),
        ("正控 换行／制表不算", len(judge(['  "x": "a\\\\u000ab\\\\u0009c"'])), 0),
        ("正控 干净文本 ⇒ 0", len(judge(['  "x": "at_seq"'])), 0),
    ]
    bad = [(n, g, w) for n, g, w in cases if g != w]
    if bad:
        for n, g, w in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, w, g))
        return 1
    # ★ 指纹登记：行号被挪动，指纹还在 ⇒ 绿
    found = judge(['  "x": "a\\\\u0007t"', '  "y": "ok"'])
    if judge_registered(found, ["a\\\\u0007t"]) != []:
        print("  [SELF-TEST FAIL] 指纹命中应绿")
        return 1
    if len(judge_registered(found, ["别的指纹"])) != 1:
        print("  [SELF-TEST FAIL] 指纹不命中应红")
        return 1
    print("  [SELF-TEST OK] 反例 2 条；正控 2 条；指纹登记 2 条")
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
    markers = known()
    red = judge_registered(found, markers)
    print("  现取：坏转义 %d 处，落在 %d 行；已登记指纹 %d 条"
          % (sum(len(h) for _, h, _ in found), len(found), len(markers)))
    if red:
        print("  [RED] 出现**未登记**的坏转义（控制字符混进本体文本）：")
        for lineno, hits, line in red:
            print("        %s:%d  %s" % (ONTOLOGY, lineno, "、".join(sorted(set(hits)))))
            print("        该行前 80 字：%s" % line.strip()[:80])
        return 1
    print("  [GREEN] 坏转义全部点名在册（指纹登记，见 %s）" % REGISTRY)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
