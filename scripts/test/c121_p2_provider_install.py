# -*- coding: utf-8 -*-
"""C121 · P2 exec 接线清单：fs/clock/network/recovery/vault/worldfs/space/presentation 都有 P2 exec。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FILES = [
    ("src/fs/fs_process.py", "on_p2_exec"),
    ("src/clock/clock_process.py", "install_p2("),
    ("src/network/network_process.py", "install_p2("),
    ("src/recovery/recovery_process.py", "install_p2("),
    ("src/vault/vault_process.py", "install_p2("),
    ("src/worldfs/worldfs_process.py", "install_p2("),
    ("src/space/space_process.py", "install_p2("),
    ("src/presentation/presentation_process.py", "install_p2("),
]


def main():
    bad = []
    for rel, needle in FILES:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        if needle not in text:
            bad.append("%s 缺 %s" % (rel, needle))
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（8 个 provider 都有 P2 exec 接线）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
