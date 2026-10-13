#!/usr/bin/env python3
"""C1 —— 本仓与上游的差异，必须只有「我方自有件」。

红＝差分里出现任何**非我方自有件**的路径（内容或 mode 差异）。
  · 今天它是干嘛的：上一轮实测抓到 76 件假差异（64 个脚本丢了执行位），本条就是那次的判据化。
  · 我方自有件：路径以 ALLOWED 之一开头。

用法：
  python verify/c1_upstream_parity.py              跑真仓库
  python verify/c1_upstream_parity.py --self-test  反例自检（喂假 diff，必须红）
"""
import subprocess
import sys

UPSTREAM_REF = "babedc9eb8ee5ce57ba65a89607fb63cad8565ef"   # 我们声明的基线（PROVENANCE.md）
ALLOWED = ("ninedim/", "verify/", ".gitattributes", "PROVENANCE.md")

NAME = "C1 上游一致性"


def judge_names(changed):
    """纯函数：给定差分路径列表，返回违规项。"""
    return [p for p in changed if not p.startswith(ALLOWED)]


def judge_modes(summary_lines):
    """纯函数：mode 变化里，非我方自有件即违规。"""
    bad = []
    for line in summary_lines:
        if "mode change" in line:
            path = line.strip().split()[-1]
            if not path.startswith(ALLOWED):
                bad.append(path)
    return bad


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    return [l for l in p.stdout.splitlines() if l.strip()], p.returncode


def real():
    # ★ 必须关 core.quotepath：非 ASCII 路径默认会被加引号 + 八进制转义，前缀匹配会全失效（2026-10-13 实测）
    base = ["git", "-c", "core.quotepath=false", "diff"]
    names, rc1 = run(base + ["--name-only", UPSTREAM_REF, "HEAD"])
    summary, rc2 = run(base + ["--summary", UPSTREAM_REF, "HEAD"])
    if rc1 != 0 or rc2 != 0:
        return None, "git diff 取不到（rc %s/%s）——环境问题，不是判断" % (rc1, rc2)
    bad = judge_names(names) + judge_modes(summary)
    return bad, "差分 %d 件" % len(names)


def self_test():
    """反例：假 diff 里放一个上游文件（distro/...）与一个 mode 变化，必须被判红。"""
    fake_names = ["ninedim/01-意图环/_索引.md", "distro/installer/aios-installer.sh"]
    fake_summary = [" mode change 100755 => 100644 distro/build/build-aios-iso.sh"]
    bad = judge_names(fake_names) + judge_modes(fake_summary)
    expect = 2
    if len(bad) != expect:
        print("  [SELF-TEST FAIL] 反例未被抓到：期望 %d 条违规，实得 %d 条 %s" % (expect, len(bad), bad))
        return 1
    # 正控：只有我方自有件 ⇒ 不许报违规
    ok = judge_names(["ninedim/a.md", "verify/c1.py", "PROVENANCE.md", ".gitattributes"])
    if ok:
        print("  [SELF-TEST FAIL] 正控被误报：%s" % ok)
        return 1
    print("  [SELF-TEST OK] 反例抓到 2 条；正控 0 条")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    bad, note = real()
    if bad is None:
        print("  [ENV] %s" % note)
        return 2
    if bad:
        print("  [RED] %s 件非我方自有件的差异（%s）：" % (len(bad), note))
        for p in bad[:10]:
            print("        - %s" % p)
        if len(bad) > 10:
            print("        … 另有 %d 件" % (len(bad) - 10))
        return 1
    print("  [GREEN] %s，且全部落在我方自有件内" % note)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
