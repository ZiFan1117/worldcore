#!/usr/bin/env python3
"""C27 —— 一个文件一块：我方代码文件长度上限（作者令 2026-10-18 ／ 2026-10-18 收紧）。

★ 作者令（逐字整理）：「代码一个代码文件不要太长，都保持一[个]块儿就行，
  不能出现 1000 多条的这个代码文件。」
★ 作者令（逐字，2026-10-18 收紧）：「将代码都拆分为不同模块，每个模块代码不要超过500行」

判据（会红）：
  · 我方代码文件（`src/`、`render/`、`dsh-plugins/`、`verify/` 下的 .py/.js/.mjs）
    **单文件 > 500 行** ⇒ 红；超了请拆成同目录小模块（一进程/一职责一块）。
  · 例外必须逐条登记在 `verify/c27_known_long_files.txt`（格式 `<路径>  # <理由>`）。
为什么是 500：作者 2026-10-18 明令「每个模块代码不要超过 500 行」⇒ 硬上限 500。
（此前曾用 800；以本条为准。）

用法：
  python verify/c27_file_length.py              跑真仓库
  python verify/c27_file_length.py --self-test  反例自检（501 行会红、500 行会绿）
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAX_LINES = 500
SCAN_DIRS = ("src", "render", "dsh-plugins", "verify")
EXTS = (".py", ".js", ".mjs")
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv"}
EXC_FILE = os.path.join(HERE, "c27_known_long_files.txt")
NAME = "C27 一个文件一块（我方代码文件 ≤ %d 行）" % MAX_LINES


def load_exceptions():
    exc = {}
    if not os.path.exists(EXC_FILE):
        return exc
    with open(EXC_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                exc[line.replace("\\", "/")] = True
    return exc


def scan(root):
    rows = []
    for base in SCAN_DIRS:
        b = os.path.join(root, base)
        if not os.path.isdir(b):
            continue
        for dp, dns, fns in os.walk(b):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if not fn.endswith(EXTS):
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fh:
                        n = sum(1 for _ in fh)
                except OSError:
                    continue
                rows.append((rel, n))
    return rows


def judge(rows, exceptions):
    """纯函数：超长且未登记的件 = 红。"""
    return [(rel, n) for rel, n in rows if n > MAX_LINES and rel not in exceptions]


def self_test():
    rows = [("ok.py", MAX_LINES), ("bad.py", MAX_LINES + 1)]
    red = judge(rows, {})
    assert red == [("bad.py", MAX_LINES + 1)], red
    assert judge(rows, {"bad.py": True}) == [], "例外登记后应绿"
    print("  自检：%d 行绿；%d 行红；例外登记后绿 ✓" % (MAX_LINES, MAX_LINES + 1))
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    rows = scan(ROOT)
    exc = load_exceptions()
    red = judge(rows, exc)
    print("  扫描 %d 件；上限 %d 行；例外登记 %d 件" % (len(rows), MAX_LINES, len(exc)))
    if red:
        for rel, n in sorted(red, key=lambda x: -x[1]):
            print("  [RED] %s：%d 行（> %d）" % (rel, n, MAX_LINES))
        print("  [RED] %d 件超长 ⇒ 拆成同目录小模块（一个文件一块）" % len(red))
        return 1
    print("  [GREEN] 全部 ≤ %d 行（最大 %d 行）" % (MAX_LINES, max([n for _, n in rows], default=0)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
