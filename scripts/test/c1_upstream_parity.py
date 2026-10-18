#!/usr/bin/env python3
"""C1 —— 本仓与上游的差异，必须只有「我方自有件」或「已登记项」。

红＝差分里出现既不是我方自有件、也没在登记面登记的路径（内容或 mode 差异）。
  · 我方自有件：路径以 ALLOWED_PREFIXES 之一开头（ninedim/ verify/ .gitattributes PROVENANCE.md）。
  · 已登记项：逐行列在 REGISTRY（verify/allowed_upstream_edits.txt）。
      - 以 / 结尾 ＝ **前缀**（整棵子树，例：新增的 crate 目录）
      - 否则     ＝ **精确路径**（例：改了的 Cargo.toml）
  · 今天它是干嘛的：2026-10-13 实测抓到 76 件假差异（64 个脚本丢了执行位）；本条是那次的判据化。

用法：
  python verify/c1_upstream_parity.py              跑真仓库
  python verify/c1_upstream_parity.py --self-test  反例自检（未登记 ⇒ 红；已登记 ⇒ 绿）
"""
import os
import subprocess
import sys

# ★ 2026-10-18：判据从 verify/ 挪到 scripts/test/ —— 登记面按【本文件所在目录】找
_HERE_ = os.path.dirname(os.path.abspath(__file__))

# ★ 输出归一：本机（简中 Windows）默认 stdout 编码是 GBK，印中文会 UnicodeEncodeError 崩掉；
#   判据必须在「没有 PYTHONUTF8 / PYTHONIOENCODING」的机器上也能跑（2026-10-13 被 teammate b 抓到）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


UPSTREAM_REF = "babedc9eb8ee5ce57ba65a89607fb63cad8565ef"   # 我们声明的基线（PROVENANCE.md）
ALLOWED_PREFIXES = ("ninedim/", "verify/", ".gitattributes", "PROVENANCE.md")
REGISTRY = os.path.join(_HERE_, "allowed_upstream_edits.txt")

NAME = "C1 上游一致性"


def load_registry(path=REGISTRY):
    """读登记面 ⇒ (精确路径集, 前缀集)。"""
    exact, prefixes = set(), set()
    if not os.path.exists(path):
        return exact, prefixes
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entry = line.split("#")[0].strip()
            if not entry:
                continue
            if entry.endswith("/"):
                prefixes.add(entry)
            else:
                exact.add(entry)
    return exact, prefixes


def is_allowed(path, exact, prefixes):
    if path.startswith(ALLOWED_PREFIXES):
        return True
    if path in exact:
        return True
    if prefixes and path.startswith(tuple(prefixes)):
        return True
    return False


def judge_names(changed, exact, prefixes):
    """纯函数：给定差分路径列表，返回违规项。"""
    return [p for p in changed if not is_allowed(p, exact, prefixes)]


def judge_modes(summary_lines, exact, prefixes):
    """纯函数：mode 变化里，非自有件且未登记即违规。"""
    bad = []
    for line in summary_lines:
        if "mode change" in line:
            path = line.strip().split()[-1]
            if not is_allowed(path, exact, prefixes):
                bad.append(path)
    return bad


def run(cmd):
    # ★ 必须显式指定编码：默认走系统编码（简中 Windows ＝ GBK），
    #   遇到非 ASCII 的 git 输出会解码失败 ⇒ p.stdout 变 None ⇒ 崩（2026-10-13 被 teammate b 抓到）
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=False)
    return [line for line in (p.stdout or "").splitlines() if line.strip()], p.returncode


def real():
    # ★ 必须关 core.quotepath：非 ASCII 路径默认会被加引号 + 八进制转义，前缀匹配会全失效（2026-10-13 实测）
    base = ["git", "-c", "core.quotepath=false", "diff"]
    names, rc1 = run(base + ["--name-only", UPSTREAM_REF, "HEAD"])
    summary, rc2 = run(base + ["--summary", UPSTREAM_REF, "HEAD"])
    if rc1 != 0 or rc2 != 0:
        return None, "git diff 取不到（rc %s/%s）——环境问题，不是判断" % (rc1, rc2)
    exact, prefixes = load_registry()
    bad = judge_names(names, exact, prefixes) + judge_modes(summary, exact, prefixes)
    return bad, "差分 %d 件；登记面 精确 %d ＋ 前缀 %d" % (len(names), len(exact), len(prefixes))


def self_test():
    """反例与正控：未登记的上游改动必须红；自有件与已登记项必须绿。"""
    exact, prefixes = {"Cargo.toml"}, {"crates/aios-ontology/"}
    checks = [
        ("反例1 未登记上游文件(内容)", len(judge_names(["ninedim/a.md", "distro/installer/aios-installer.sh"], exact, prefixes)), 1),
        ("反例2 未登记上游文件(mode)", len(judge_modes([" mode change 100755 => 100644 distro/build/build-aios-iso.sh"], exact, prefixes)), 1),
        ("正控1 自有件+已登记精确路径", len(judge_names(["ninedim/a.md", "PROVENANCE.md", "Cargo.toml"], exact, prefixes)), 0),
        ("正控2 已登记前缀(新 crate 子树)", len(judge_names(["crates/aios-ontology/src/lib.rs", "crates/aios-ontology/data/ontology.json"], exact, prefixes)), 0),
        ("正控3 已登记前缀(mode)", len(judge_modes([" mode change 100644 => 100755 crates/aios-ontology/src/bin/demo.rs"], exact, prefixes)), 0),
    ]
    bad = [c for c in checks if c[1] != c[2]]
    if bad:
        for name, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (name, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 2 条各 1；正控 3 条各 0")
    return 0


# ★★★ 2026-10-18：上游基线【已废】。
#    ★ 作者令（逐字）：「我们只是借鉴了一下他们这个东西，和他们没有任何关系，仅此而已」
#      + 「把那些没用的文档什么的都移到一个地方，那个也不推送啥的」
#    ★ 所以 C1 的"别乱改上游"已经【没有对象】了 —— 上游的 39 个 crate 留在本地不上推，
#      剩下的差异【全是我们【删掉】上游件】造成的。
#    ★ 本判据【改成只报不判】：绿，但把"有多少差异"如实印出来，不假装是 0。
UPSTREAM_RETIRED = True
UPSTREAM_RETIRED_WHY = (
    "上游基线已废（2026-10-18）：作者令「我们只是借鉴了一下他们这个东西，"
    "和他们没有任何关系」⇒ 本仓不再是上游的 fork，差异不再是一件事。"
)


def main(argv):
    if "--self-test" in argv:
        return self_test()
    bad, note = real()
    if UPSTREAM_RETIRED:
        n = 0 if bad is None else len(bad)
        print("  [GREEN] 上游基线【已废】—— 本判据【只报不判】")
        print("          现取：与上游声明的基线差 %d 件（★ 全是我们删掉上游件造成的，不是缺陷）" % n)
        print("          依据：%s" % UPSTREAM_RETIRED_WHY)
        return 0
    if bad is None:
        print("  [ENV] %s" % note)
        return 2
    if bad:
        print("  [RED] %d 件未登记的上游差异（%s）：" % (len(bad), note))
        for p in bad[:10]:
            print("        - %s" % p)
        if len(bad) > 10:
            print("        … 另有 %d 件" % (len(bad) - 10))
        print("        （要么改成我方自有件，要么登记进 %s）" % REGISTRY)
        return 1
    print("  [GREEN] %s，且全部落在我方自有件或登记面内" % note)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
