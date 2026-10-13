#!/usr/bin/env python3
"""C4 —— 纯行尾差异检测（防「改一行、diff 一个文件」）。

红＝某个**已改动件**满足：**把 CRLF 归一成 LF 之后，工作树与 HEAD 的内容相同，但原始字节不同**
   ⇒ 那就是「**差异纯粹来自行尾**」⇒ diff 会显示整文件重写、真改动被噪声淹没。

★ 为什么用这个判据（本判据改了三版，两个假红都是自检抓的）：
  · v0.1 比 CRLF 计数 ⇒ 碰巧能用，但基准（工作树）本身不可靠；
  · v0.2 比「工作树字节 vs HEAD 字节」⇒ ★ **假红 1260 件**：实测 **工作树是 CRLF、仓库内是 LF 是
    git 正常的 eol 行为**（`git checkout-index -a -f` 重写工作树后 `.gitignore` 仍是 1312 字节、
    HEAD blob 是 1255，且 `git status` 干净）⇒ **拿工作树字节当基准是错的**；
  · v0.3 比「差异行数占比」⇒ ★ **两个假红**：纯新增的大文件（全部是新增行）被误判；重写判据自己也被判。
  · ★ v0.4（本版）：**只判「归一化后相同、原始不同」** —— 真改动（归一化后仍不同）不误伤，
    纯行尾差异一定红。**它不依赖工作树形态当基准**。

用法：
  python verify/c4_eol_consistency.py              跑真仓库
  python verify/c4_eol_consistency.py --self-test  反例自检
"""
import os
import subprocess
import sys

# ★ 输出归一：本机（简中 Windows）默认 stdout 编码是 GBK，印中文会 UnicodeEncodeError 崩掉；
#   判据必须在「没有 PYTHONUTF8 / PYTHONIOENCODING」的机器上也能跑（2026-10-13 被 teammate b 抓到）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


NAME = "C4 纯行尾差异检测"


def normalize(data):
    """把 CRLF 归一成 LF（纯函数）。"""
    return data.replace(b"\r\n", b"\n")


def judge(pairs):
    """纯函数：pairs = [(path, head_bytes, work_bytes)]，返回违规清单。"""
    bad = []
    for path, head, work in pairs:
        if head != work and normalize(head) == normalize(work):
            bad.append(path)
    return bad


def collect():
    names = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False,
    ).stdout.split()
    pairs = []
    for path in names:
        if not os.path.exists(path):
            continue                      # 删除件由别的判据管
        head = subprocess.run(["git", "cat-file", "blob", "HEAD:" + path],
                              capture_output=True, shell=False).stdout
        if not head:
            continue                      # 新增件（HEAD 里没有）⇒ 不算「重写」
        with open(path, "rb") as fh:
            work = fh.read()
        if b"\x00" in work[:8192]:
            continue
        pairs.append((path, head, work))
    return pairs


def self_test():
    cases = [
        ("反例 纯行尾差异（LF → CRLF）", judge([("a.rs", b"x\ny\n", b"x\r\ny\r\n")]), 1),
        ("反例 纯行尾差异（CRLF → LF）", judge([("a.rs", b"x\r\ny\r\n", b"x\ny\n")]), 1),
        ("正控 真改动", judge([("a.rs", b"x\ny\n", b"x\nz\n")]), 0),
        ("正控 完全相同", judge([("a.rs", b"x\ny\n", b"x\ny\n")]), 0),
        ("正控 真改动＋行尾（归一后仍不同）", judge([("a.rs", b"x\ny\n", b"x\r\nz\r\n")]), 0),
    ]
    bad = [(n, got, want) for n, got, want in cases if len(got) != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, len(got)))
        return 1
    print("  [SELF-TEST OK] 反例 2 条各 1；正控 3 条各 0")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        pairs = collect()
    except OSError as exc:
        print("  [ENV] 取不到 git 数据：%s（环境问题，不是判断）" % exc)
        return 2
    bad = judge(pairs)
    if bad:
        print("  [RED] %d 件是「纯行尾差异」（共查 %d 件已改动文件）：" % (len(bad), len(pairs)))
        for path in bad[:10]:
            print("        - %s（归一化行尾后与 HEAD 相同，原始字节不同）" % path)
        return 1
    print("  [GREEN] %d 件已改动文件，没有一件是纯行尾差异" % len(pairs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
