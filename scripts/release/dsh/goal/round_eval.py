#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 长程闭环评估（P6）—— 把每轮报告/提交扫成 `rounds.jsonl`（证据/回滚/提交是否齐）。

★ 作者（逐字整理）：「整个世界不断进化」；os-gaps P6：轨迹要变成下一轮的改进信号。

用法：
  python3 round_eval.py [--reports DIR] [--progress FILE] [--workdir DIR] [--out FILE]

输出（默认写到 --out，缺省 /root/aios-goals/rounds.jsonl）：
  {"stamp":"20261019-190015","report_bytes":8039,"has_evidence":true,
   "has_rollback":true,"commit_seen":true,"report_exists":true}
★ 不改任何东西；只读报告/进度/本地提交，写一行 JSONL。
"""
import argparse
import json
import os
import re
import subprocess

STAMP_RE = re.compile(r"round=(\d{8}-\d{6})")


def quality(text):
    """报告质量：有没有「证据/验证」、有没有「回滚」。"""
    has_ev = ("证据" in text) or ("验证" in text)
    has_rb = "回滚" in text
    return bool(has_ev), bool(has_rb)


def stamps_in_progress(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return STAMP_RE.findall(f.read())


def commits(workdir):
    if not workdir or not os.path.isdir(os.path.join(workdir, ".git")):
        return []
    p = subprocess.run(["git", "-C", workdir, "log", "--format=%s", "-80"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln for ln in (p.stdout or "").splitlines() if ln.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="round evaluation (P6)")
    ap.add_argument("--reports", default="/root/aios-goal-reports")
    ap.add_argument("--progress", default="/root/aios-goals/progress.md")
    ap.add_argument("--workdir", default="/root/aios-work")
    ap.add_argument("--out", default="/root/aios-goals/rounds.jsonl")
    ap.add_argument("--md", default="", help="另写一份人读的 rounds.md（给作者看）")
    a = ap.parse_args(argv)
    reps = []
    if os.path.isdir(a.reports):
        reps = [n[:-3] for n in os.listdir(a.reports)
                if n.endswith(".md") and re.match(r"\d{8}-\d{6}\.md$", n)]
    msgs = commits(a.workdir)
    rows = []
    for stamp in sorted(set(stamps_in_progress(a.progress)) | set(reps)):
        rp = os.path.join(a.reports, stamp + ".md")
        text = ""
        if os.path.isfile(rp):
            with open(rp, encoding="utf-8", errors="replace") as f:
                text = f.read()
        has_ev, has_rb = quality(text)
        rows.append({"stamp": stamp, "report_exists": bool(text),
                     "report_bytes": len(text.encode("utf-8")),
                     "has_evidence": has_ev, "has_rollback": has_rb,
                     "commit_seen": any(stamp in m for m in msgs)})
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if a.md:
        lines = ["# 目标链轮次摘要（自动生成）", "",
                 "- 轮次数：%d" % len(rows),
                 "- 缺报告：%d" % len([r for r in rows if not r["report_exists"]]),
                 "- 弱报告（缺证据/回滚）：%d" % len([r for r in rows if not (r["has_evidence"] and r["has_rollback"])]),
                 "- 看不到本地提交：%d" % len([r for r in rows if not r["commit_seen"]]),
                 "", "| 轮次 | 报告 | 证据 | 回滚 | 本地提交 |", "|---|---|---|---|---|"]
        for r in rows[-15:]:
            lines.append("| %s | %s | %s | %s | %s |" % (
                r["stamp"], "✓" if r["report_exists"] else "✗",
                "✓" if r["has_evidence"] else "✗", "✓" if r["has_rollback"] else "✗",
                "✓" if r["commit_seen"] else "✗"))
        try:
            with open(a.md, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("md=%s" % a.md)
        except Exception as e:
            print("md 写失败：%s" % e, file=sys.stderr)
    missing = [r["stamp"] for r in rows if not r["report_exists"]]
    weak = [r["stamp"] for r in rows if not (r["has_evidence"] and r["has_rollback"])]
    no_commit = [r["stamp"] for r in rows if not r["commit_seen"]]
    print("rounds=%d missing_report=%d weak_report=%d no_commit=%d"
          % (len(rows), len(missing), len(weak), len(no_commit)))
    print("out=%s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
