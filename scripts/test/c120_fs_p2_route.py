# -*- coding: utf-8 -*-
"""C120 · fs 的 P2 exec 必须按 route 过滤（否则会抢 clock/recovery/vault 的 call_exec）。

反例：fs 不判 route ⇒ 任何 provider 的 P2 call 都被 fs 回 “不认识的动作”。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    src = open(os.path.join(ROOT, "src", "fs", "fs_process.py"), encoding="utf-8").read()
    bad = []
    if "def on_p2_exec" not in src:
        bad.append("fs 没有 on_p2_exec")
    if 'route = data.get("route")' not in src:
        bad.append("fs P2 exec 没取 route")
    if 'route != "fs"' not in src:
        bad.append("fs P2 exec 没过滤非 fs route")
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（fs P2 exec 按 route=fs 过滤，不抢其他 provider 的 call_exec）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
