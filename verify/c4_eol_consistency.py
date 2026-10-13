#!/usr/bin/env python3
"""C4 —— 行尾一致性（三段，防「改一行、整文件被换行尾」）。

段一（工作树）：已改动文件里，「**归一化行尾后与 HEAD 相同、而原始字节不同**」＝纯行尾差异 ⇒ 红。
★ 段二（提交后 · 与上游比）：**我方登记改过的上游文件**，其 **HEAD blob 的 CRLF 计数**必须与
   **上游同名 blob** 一致。不同 ⇒ 红（＝我们把它整文件换了行尾）。
   ★ 来历（2026-10-13 第四次踩）：编辑工具把 5 个上游文件整文件写成 CRLF，
     `git add` 把 CRLF **存进了仓库**（`core.autocrlf=false`）⇒ 段一**看不见**
     （HEAD 也是 CRLF ⇒ 两边"无纯行尾差异"）⇒ 整笔提交变成 3,656 行删除的假象。
     段二就是为这个盲区建的：**拿上游当基准**，而不是拿 HEAD 当基准。
段三：无（段一＋段二已覆盖工作树与提交两侧）。

用法：
  python verify/c4_eol_consistency.py              跑真仓库
  python verify/c4_eol_consistency.py --self-test  反例自检
"""
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UPSTREAM_REF = "babedc9eb8ee5ce57ba65a89607fb63cad8565ef"
# 我方自有件（上游没有，或整棵是我方的）——段二不比它们
OWN = ("ninedim/", "verify/", "PROVENANCE.md", ".gitattributes", "crates/aios-ontology/")
NAME = "C4 行尾一致性"


def count_crlf(data):
    """纯函数：数 CRLF 出现次数。"""
    return data.count(b"\r\n")


def normalize(data):
    return data.replace(b"\r\n", b"\n")


def judge_worktree(pairs):
    """段一（纯函数）。"""
    return [p for p, head, work in pairs if head != work and normalize(head) == normalize(work)]


def judge_vs_upstream(triples):
    """段二（纯函数）：triples = [(path, upstream_bytes, head_bytes)]。"""
    return [(p, count_crlf(u), count_crlf(h)) for p, u, h in triples if count_crlf(u) != count_crlf(h)]


def git_bytes(args):
    return subprocess.run(["git"] + args, capture_output=True, shell=False).stdout


def collect_worktree():
    names = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False,
    ).stdout.split()
    pairs = []
    for path in names:
        if not os.path.exists(path):
            continue
        head = git_bytes(["cat-file", "blob", "HEAD:" + path])
        if not head:
            continue
        with open(path, "rb") as fh:
            work = fh.read()
        if b"\x00" in work[:8192]:
            continue
        pairs.append((path, head, work))
    return pairs


def collect_vs_upstream():
    names = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", UPSTREAM_REF, "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False,
    ).stdout.split()
    triples = []
    for path in names:
        if path.startswith(OWN):
            continue
        up = git_bytes(["cat-file", "blob", UPSTREAM_REF + ":" + path])
        head = git_bytes(["cat-file", "blob", "HEAD:" + path])
        if not up or not head:
            continue
        triples.append((path, up, head))
    return triples


def self_test():
    cases = [
        ("反例1 工作树纯行尾差异", len(judge_worktree([("a.rs", b"x\ny\n", b"x\r\ny\r\n")])), 1),
        ("正控1 工作树真改动", len(judge_worktree([("a.rs", b"x\ny\n", b"x\nz\n")])), 0),
        ("反例2 提交后与上游行尾不同", len(judge_vs_upstream([("a.rs", b"x\ny\n", b"x\r\ny\r\n")])), 1),
        ("正控2 提交后与上游一致", len(judge_vs_upstream([("a.rs", b"x\ny\n", b"x\ny2\n")])), 0),
    ]
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 2 条各 1；正控 2 条各 0")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        pairs = collect_worktree()
        triples = collect_vs_upstream()
    except OSError as exc:
        print("  [ENV] 取不到 git 数据：%s（环境问题，不是判断）" % exc)
        return 2
    bad1 = judge_worktree(pairs)
    bad2 = judge_vs_upstream(triples)
    if bad1:
        print("  [RED] 段一：%d 件工作树是纯行尾差异（共查 %d 件已改动）" % (len(bad1), len(pairs)))
        for p in bad1[:8]:
            print("        - %s" % p)
    if bad2:
        print("  [RED] 段二：%d 件**提交进仓库的上游文件被整文件换了行尾**（共查 %d 件）：" % (len(bad2), len(triples)))
        for p, u, h in bad2[:8]:
            print("        - %s  上游 CRLF=%d  我方 HEAD CRLF=%d" % (p, u, h))
        print("        ⇒ 修法：把该文件转回上游的行尾形态后**重新提交**（工作树改回没用，要进仓库）")
    if bad1 or bad2:
        return 1
    print("  [GREEN] 段一 %d 件工作树干净；段二 %d 件我方改过的上游文件行尾与上游一致" % (len(pairs), len(triples)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
