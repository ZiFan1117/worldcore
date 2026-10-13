#!/usr/bin/env python3
"""C2 —— 工程域只装档案。

红＝ninedim/ 下出现**可执行脚本或二进制**（.py/.sh/.js/.bat/.ps1/.exe/.dll/.so/.bin/.iso…），
或出现**含 NUL 字节**的文件。

用法：
  python verify/c2_domain_files_only.py              跑真仓库
  python verify/c2_domain_files_only.py --self-test  反例自检（必须红）
"""
import os
import sys

DOMAIN = "ninedim"
BAD_EXT = (".py", ".sh", ".js", ".bat", ".ps1", ".cmd", ".exe", ".dll", ".so", ".dylib",
           ".bin", ".iso", ".img", ".o", ".rlib", ".class", ".jar")

NAME = "C2 工程域只装档案"


def judge(paths, nul_paths):
    """纯函数：返回违规清单。"""
    bad = []
    for p in paths:
        low = p.lower()
        if low.endswith(BAD_EXT):
            bad.append((p, "可执行脚本/二进制扩展名"))
    for p in nul_paths:
        bad.append((p, "含 NUL 字节（二进制）"))
    return bad


def walk(root):
    paths, nuls = [], []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, os.getcwd()).replace(os.sep, "/")
            paths.append(rel)
            try:
                with open(full, "rb") as fh:
                    if b"\x00" in fh.read(65536):
                        nuls.append(rel)
            except OSError:
                pass
    return paths, nuls


def self_test():
    fake = ["ninedim/a.md", "ninedim/tools/run.sh", "ninedim/data.json"]
    bad = judge(fake, ["ninedim/blob.dat"])
    if len(bad) != 2:
        print("  [SELF-TEST FAIL] 期望 2 条，实得 %d：%s" % (len(bad), bad))
        return 1
    ok = judge(["ninedim/a.md", "ninedim/b.json", "ninedim/c.csv"], [])
    if ok:
        print("  [SELF-TEST FAIL] 正控被误报：%s" % ok)
        return 1
    print("  [SELF-TEST OK] 反例抓到 2 条（.sh 与 NUL）；正控 0 条")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not os.path.isdir(DOMAIN):
        print("  [ENV] 找不到 %s/（环境问题，不是判断）" % DOMAIN)
        return 2
    paths, nuls = walk(DOMAIN)
    bad = judge(paths, nuls)
    if bad:
        print("  [RED] %d 件违规（共扫 %d 件）：" % (len(bad), len(paths)))
        for p, why in bad[:10]:
            print("        - %s  ← %s" % (p, why))
        return 1
    print("  [GREEN] 共扫 %d 件，全为档案" % len(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
