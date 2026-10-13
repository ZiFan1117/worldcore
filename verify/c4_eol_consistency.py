#!/usr/bin/env python3
"""C4 —— 行尾一致性：被改动的文件，其 CRLF 形态必须与 HEAD 里的那一份一致。

红＝某个**已改动**文件在工作树里的 CRLF 计数 ≠ HEAD blob 的 CRLF 计数
     ⇒ 那是「整文件被换了行尾」，diff 会变成整文件重写、真改动被噪声淹没。

来历（2026-10-13 实测两次）：本机编辑工具会把整文件写成 CRLF，而上游是 LF；
第一次造成 1348 件内容差异（已 revert），第二次造成 1639 行假改动。

用法：
  python verify/c4_eol_consistency.py              跑真仓库
  python verify/c4_eol_consistency.py --self-test  反例自检（形态不一致 ⇒ 红）
"""
import os
import subprocess
import sys

NAME = "C4 行尾一致性"


def count_crlf(data):
    """纯函数：数 CRLF 出现次数。"""
    return data.count(b"\r\n")


def judge(pairs):
    """纯函数：pairs = [(path, head_bytes, work_bytes)]，返回违规清单。"""
    bad = []
    for path, head, work in pairs:
        if count_crlf(head) != count_crlf(work):
            bad.append((path, count_crlf(head), count_crlf(work)))
    return bad


def collect():
    names = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, shell=False,
    ).stdout.split()
    pairs = []
    for path in names:
        if not os.path.exists(path):
            continue
        try:
            head = subprocess.run(["git", "cat-file", "blob", "HEAD:" + path],
                                  capture_output=True, shell=False).stdout
        except OSError:
            continue
        with open(path, "rb") as fh:
            work = fh.read()
        if b"\x00" in work[:8192]:
            continue
        pairs.append((path, head, work))
    return pairs


def self_test():
    cases = [
        ("反例 整文件换行尾", [("a.rs", b"x\ny\n", b"x\r\ny\r\n")], 1),
        ("正控 行尾一致", [("a.rs", b"x\ny\n", b"x\nz\n")], 0),
        ("正控 都无 CRLF", [("a.md", b"a\n", b"b\n")], 0),
    ]
    bad = [(n, len(judge(p)), want) for n, p, want in cases if len(judge(p)) != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 1 条抓到；正控 2 条 0 误报")
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
        print("  [RED] %d 件行尾形态与 HEAD 不一致（共查 %d 件已改动文件）：" % (len(bad), len(pairs)))
        for path, h, w in bad[:10]:
            print("        - %s  HEAD CRLF=%d  工作树 CRLF=%d" % (path, h, w))
        return 1
    print("  [GREEN] %d 件已改动文件的行尾形态与 HEAD 一致" % len(pairs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
