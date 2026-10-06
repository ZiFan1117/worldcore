#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_evidence.py —— **取证器**（不是判据、不是门禁）。

它只做一件事：把"这一轮的门禁读数"连同**四要素**（时点／命令／原始输出／提交号）一次收齐，
供直接粘进 change 的 `review.md` §五（环境指纹）或台账。

为什么需要它
------------
本项目对"读数"的纪律是：**每个数字都要能复现**——带时点、带命令、带原始输出、带提交号
（H-07 数字三要素、H-09 证据四要素）。而这件事此前靠手搓：抄读数、抄提交号、抄时点，
**抄漏一次就是一次假证**（本轮已发生过：一条"逐字节可复现"其实是脚本没跑）。

**它不是判据**：它**从不**判"通过／不通过"——判词归 `spec_bridge.py`（规格层）与 `module_graph.py`（机核层）。
它只**收**读数，并把每条命令的退出码原样抄回来。

用法
----
    python3 openspec/gen/collect_evidence.py            # 打印 markdown 证据块
    python3 openspec/gen/collect_evidence.py --out <file>   # 同时写入文件
    python3 openspec/gen/collect_evidence.py --json     # 结构化输出
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")     # 非 UTF-8 控制台不崩（同 spec_bridge 口径：只重配 errors）
    except Exception:
        pass


def find_repo(start):
    p = Path(start).resolve()
    for cand in [p] + list(p.parents):
        if (cand / "openspec" / "specs").is_dir():
            return cand
    return None


def pick_python():
    """挑一个能跑 tools/*.py 的解释器：优先当前解释器（它显然能跑）。"""
    return sys.executable or "python3"


def resolve_exe(name):
    """把命令名解析成**可被 subprocess 直接执行**的路径。

    Windows 上 `openspec` 是 `.ps1`/`.cmd` 壳：`subprocess.run(["openspec", ...])` 会 FileNotFoundError。
    这里显式解析；解析不到就返回 None（调用方据此报"命令不存在"，**不静默跳过**）。
    """
    p = shutil.which(name)
    if p:
        return p
    for ext in (".cmd", ".bat", ".exe", ".ps1"):
        p = shutil.which(name + ext)
        if p:
            return p
    return None


def child_env():
    """给子进程钉 UTF-8 输出。

    不带这个，Python 子进程在 Windows 上按 GBK 写 stdout，而本脚本按 UTF-8 解 ⇒ **读到的全是乱码、
    正则一条也匹配不上**（2026-09-27 实测：六条命令的"末行读数"全成 "—"，看着有输出其实没读到）。
    """
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    return e


def run(cmd, cwd, timeout=300):
    t0 = time.time()
    cmd = list(cmd)
    exe = resolve_exe(cmd[0])
    if exe is None:
        return {"cmd": " ".join(cmd), "rc": None, "out": "★ 命令不存在（%s）" % cmd[0], "sec": 0.0}
    cmd[0] = exe
    argv = ["cmd", "/c", exe] + cmd[1:] if exe.lower().endswith((".cmd", ".bat", ".ps1")) else cmd
    try:
        p = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=child_env())
        rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return {"cmd": " ".join(cmd), "rc": None, "out": "★ 命令不存在", "sec": 0.0}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd), "rc": None, "out": "★ 超时", "sec": round(time.time() - t0, 1)}
    return {"cmd": " ".join(cmd), "rc": rc, "out": out.strip(), "sec": round(time.time() - t0, 1)}


def tail(text, n=6):
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines[-n:]) if lines else "（无输出）"


def main(argv=None):
    ap = argparse.ArgumentParser(description="取证器：把门禁读数连同四要素一次收齐（**不判通过与否**）")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None, help="把 markdown 证据块写进这个文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve() if args.repo else find_repo(Path(__file__).parent)
    if not repo:
        print("★ 找不到仓库根（向上找不到含 openspec/specs 的目录）")
        return 1

    py = pick_python()
    now = time.strftime("%Y-%m-%d %H:%M:%S %z")
    head = run(["git", "rev-parse", "HEAD"], repo)
    head_sha = head["out"].strip() if head["rc"] == 0 else "（非 git 仓）"
    dirty = run(["git", "status", "--porcelain"], repo)
    dirty_n = len([l for l in dirty["out"].splitlines() if l.strip()]) if dirty["rc"] == 0 else -1

    cmds = [
        ["openspec", "validate", "--all", "--strict"],
        ["openspec", "validate", "--archived"],
        [py, "world-core/tools/spec_bridge.py"],
        [py, "world-core/tools/spec_bridge.py", "--self-test"],
    ]
    mg = repo / "world-core/tools/module_graph.py"
    if mg.is_file():
        cmds += [[py, "world-core/tools/module_graph.py"],
                 [py, "world-core/tools/module_graph.py", "--self-test"]]

    results = [run(c, repo) for c in cmds]

    summary = []
    for r in results:
        verdict = ""
        m = re.search(r"Totals:\s*([0-9]+ passed,\s*[0-9]+ failed[^\n]*)", r["out"])
        if m:
            verdict = m.group(1)
        else:
            m2 = re.search(r"通过\s*([0-9]+)\s*/\s*失败\s*([0-9]+)", r["out"])
            if m2:
                verdict = "通过 %s / 失败 %s" % (m2.group(1), m2.group(2))
            elif "自证通过" in r["out"]:
                verdict = "自证通过"
            elif "自证不通过" in r["out"]:
                verdict = "★自证不通过"
        summary.append({"cmd": r["cmd"], "rc": r["rc"], "verdict": verdict,
                        "tail": tail(r["out"]), "sec": r["sec"]})

    env = {
        "时点": now,
        "提交号": head_sha,
        "未提交改动件数": dirty_n,
        "主机": platform.node(),
        "系统": "%s %s" % (platform.system(), platform.release()),
        "Python": platform.python_version(),
        "解释器": py,
        "仓库": str(repo),
    }

    if args.json:
        print(json.dumps({"env": env, "readings": summary}, ensure_ascii=False, indent=1))
        return 0

    L = []
    L.append("<!-- 由 openspec/gen/collect_evidence.py 生成；**它只收读数，不判通过与否** -->")
    L.append("### 门禁读数（四要素：时点／命令／原始输出／提交号）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    for k, v in env.items():
        L.append("| %s | `%s` |" % (k, v))
    L.append("")
    L.append("| 命令 | 退出码 | 末行读数 | 耗时 |")
    L.append("|---|---|---|---|")
    for s in summary:
        L.append("| `%s` | **%s** | %s | %ss |" % (s["cmd"], s["rc"], s["verdict"] or "—", s["sec"]))
    L.append("")
    L.append("<details><summary>各命令原始输出（末 6 行）</summary>")
    L.append("")
    for s in summary:
        L.append("**`%s`** ⇒ rc=%s" % (s["cmd"], s["rc"]))
        L.append("")
        L.append("```text")
        L.append(s["tail"])
        L.append("```")
        L.append("")
    L.append("</details>")
    L.append("")
    text = "\n".join(L)

    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
        print("\n（已写入 %s）" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
