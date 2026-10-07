#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""表块行宽审计（**转义感知**）——判据：任一表块的体行格数必须 == 该表头格数。

为什么要它：朴素 `s.count("|")` 会把单元格内的 **转义竖线 `\|`**（以及 `\\|`）误计为分隔符，
从而对**本来就正确**的行报「体行行窄」（R1 三轮席 S-07 的 `G-20` 即此类误报）。
本工具按 Markdown 转义规则计数，故 `\|` 不计分隔、`\\` 视为一个字面反斜杠。

用法：
  python3 tools/table_width_audit.py <file.md> [...]   # 逐文件报不符行；有则 rc=1
  python3 tools/table_width_audit.py --self-test       # 自证：注入变异必须报红、样本必须常绿
"""
import io
import re
import sys

SEP = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")


def cells(line):
    """返回该行的「格数」（转义感知）。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    #: 2026-09-27 修：尾定界须判「尾竖线前反斜杠个数的奇偶」——偶数个反斜杠时该竖线**是**分隔符（R4S2-03 G2 误报）。
    if s.endswith("|"):
        k = 0
        while len(s) - 2 - k >= 0 and s[len(s) - 2 - k] == "\\":
            k += 1
        if k % 2 == 1:
            pass
        else:
            s = s[:-1]
        s = s[:-1]
    n, i = 0, 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "|":
            n += 1
        i += 1
    return n + 1


def audit(text, name):
    lines = text.split("\n")
    blocks, cur = [], None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("|"):
            if cur is None:
                cur = []
            cur.append(i)
        else:
            if cur:
                blocks.append(cur)
            cur = None
    if cur:
        blocks.append(cur)
    bad = []
    for idx in blocks:
        if len(idx) < 2:
            continue
        head = cells(lines[idx[0]])
        for i in idx[2:]:
            if SEP.match(lines[i]):
                continue
            n = cells(lines[i])
            if n != head:
                bad.append((i + 1, head, n))
    return len(blocks), bad


def main(argv):
    if "--self-test" in argv:
        sample = (
            "| A | B | C | D |\n"
            "|---|---|---|---|\n"
            "| 1 | 含转义 \\| 竖线的格 | 3 | 4 |\n"      # 正确：4 格
            "| 1 | 2 | 3 | 4 |\n"
            "| 1 | 2 | 3 |\n"                              # 变异：窄一格
        )
        nb, bad = audit(sample, "self-test")
        # 变异在第 5 行；第 3 行含**转义竖线**，必须**不报**——这正是本工具与朴素 `|` 计数的差别。
        ok_green = [b[0] for b in bad] == [5] and cells("| 1 | 含转义 \\| 竖线的格 | 3 | 4 |") == 4
        sample2 = "\n".join(sample.split("\n")[:-2])
        _, bad2 = audit(sample2, "self-test-green")
        ok_red = len(bad2) == 0
        print("[self-test] 变异必报红 = %s（命中行 %s，应=[5]）；转义行必常绿 = %s；正确样本必常绿 = %s"
              % (ok_green, [b[0] for b in bad], cells("| 1 | 含转义 \\| 竖线的格 | 3 | 4 |") == 4, ok_red))
        return 0 if (ok_green and ok_red) else 1
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print("用法：python3 tools/table_width_audit.py <file.md> [...] | --self-test")
        return 2
    rc = 0
    for f in files:
        text = io.open(f, encoding="utf-8", newline="").read()
        nb, bad = audit(text, f)
        if bad:
            rc = 1
            print("[FAIL] %s：表块 %d，行宽不符 %d" % (f, nb, len(bad)))
            for ln, h, n in bad:
                print("        L%-6d 表头 %d 格 / 体行 %d 格" % (ln, h, n))
        else:
            print("[ OK ] %s：表块 %d，行宽不符 0（转义感知）" % (f, nb))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
