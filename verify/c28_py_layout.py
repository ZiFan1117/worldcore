#!/usr/bin/env python3
"""C28 —— Python 一进程一夹：进程 .py 不许平铺在 `src/` 根（作者令 2026-10-18）。

★ 作者令（逐字整理）：「现在不同的进程是不是在不同的文件夹下面……不同的代码必须在不同的文件夹下面」。
★ 约定：
  · 每个进程/原子一个夹：`src/<进程>/`（如 `src/ontology/`、`src/computer/`、`src/gui/`、`src/agent/`、`src/bridge/`）；
  · 上游料例外：`src/foundry_ontology/`（MIT 第三方，原样保留）；
  · **`src/` 根下不许直接放 .py**（除了以后若真需要 `__init__.py`，也须登记——今天没有）。

判据（会红）：`src/` 根下出现任何 `.py` 文件 ⇒ 红 ⇒ 搬到 `src/<进程>/` 里。
自检：根下 `flat.py` 红；空根绿。

用法：
  python verify/c28_py_layout.py              跑真仓库
  python verify/c28_py_layout.py --self-test  反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = os.path.join(ROOT, "src")
NAME = "C28 Python 一进程一夹（src/ 根不许平铺 .py）"


def scan_flat(root=PY):
    """纯函数：返回 src/ 根下直接放的 .py 文件名列表。"""
    if not os.path.isdir(root):
        return []
    return sorted(f for f in os.listdir(root)
                  if f.endswith(".py") and os.path.isfile(os.path.join(root, f)))


def judge(names):
    """纯函数：扁平 .py = 红（今天不允许任何根级 .py）。"""
    return [n for n in names if n]


def self_test():
    assert judge(["flat.py"]) == ["flat.py"], judge(["flat.py"])
    assert judge([]) == []
    print("  自检：根下 flat.py ⇒ 红；空根 ⇒ 绿 ✓")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    flat = scan_flat()
    if flat:
        for n in flat:
            print("  [RED] src/%s：进程 .py 平铺在 src/ 根" % n)
        print("  [RED] 请搬到 src/<进程>/（一进程一夹）")
        return 1
    dirs = sorted(d for d in os.listdir(PY) if os.path.isdir(os.path.join(PY, d)))
    print("  [GREEN] src/ 根无 .py；子夹：%s" % ", ".join(dirs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
