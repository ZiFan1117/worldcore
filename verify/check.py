#!/usr/bin/env python3
"""我方判据入口（13-aios-worldcore）。

★ 本目录 verify/ 是**我方新增**（非上游；上游的检查在 distro/build/tests/ 与 .gitlab-ci.yml）。
跑法：
  python verify/check.py            跑全部判据
  python verify/check.py --self-test 只跑各判据的反例自检
退出码：0 全绿 ／ 1 有红 ／ 2 有环境问题（★ 未校验 ≠ 通过）
"""
import os
import subprocess
import sys

# ★ 输出与子进程都强制 UTF-8：本机默认 GBK，否则入口自己印中文就崩（2026-10-13 实测）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

HERE = os.path.dirname(os.path.abspath(__file__))
CRITERIA = [
    "c1_upstream_parity.py",
    "c2_domain_files_only.py",
    "c3_action_name_gate.py",
    "c4_eol_consistency.py",
    "c5_policy_kernel_attached.py",
    "c6_class_has_identity.py",
]


def main(argv):
    self_test = "--self-test" in argv
    rows = []
    worst = 0
    for name in CRITERIA:
        path = os.path.join(HERE, name)
        cmd = [sys.executable, path] + (["--self-test"] if self_test else [])
        p = subprocess.run(cmd, capture_output=True, text=True, env=CHILD_ENV,
                           encoding="utf-8", errors="replace")
        out = (p.stdout or "").strip()
        rows.append((name, p.returncode, out))
        if p.returncode == 1:
            worst = 1
        elif p.returncode != 0 and worst == 0:
            worst = 2
    print("=== 13-aios-worldcore · 我方判据（%s）===" % ("反例自检" if self_test else "实跑"))
    for name, rc, out in rows:
        mark = {0: "GREEN", 1: "RED  ", 2: "ENV  "}.get(rc, "?    ")
        print("[%s] %s" % (mark, name))
        for line in out.splitlines():
            print("        " + line)
    print("=== 结论：%s（rc=%d）===" % ({0: "全绿", 1: "有红", 2: "有环境问题（未校验）"}.get(worst, "?"), worst))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
