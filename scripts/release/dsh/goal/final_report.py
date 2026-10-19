#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 06:00 终报生成器（`final_report.py`）——到点后一条命令写出终报 Markdown。

用法：
  python3 final_report.py [--out FILE] [--reports DIR] [--goals DIR]

★ 只读；不启停任何东西。写出的终报包含：
  - 截止停链现取（DONE 文件、三条 DSH 定时器状态）
  - 一屏状态（快照/进度/轮次摘要/游标/场景/世界文件/guard/单元）
  - 最近轮报告清单（大小＋gate 行）
  - 已知缺口（固定清单，如实）
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.dirname(os.path.dirname(HERE))       # scripts/release（status.py 在那）
for _p in (HERE, REL):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import status as S  # noqa: E402

DSH_TIMERS = ("aios-dsh-goal.timer", "aios-dsh-optimize.timer", "aios-dsh-evolve.timer")


def timer_state():
    out = {}
    for u in DSH_TIMERS:
        try:
            p = subprocess.run(["systemctl", "is-active", u], capture_output=True,
                               text=True, timeout=5)
            out[u] = (p.stdout or "").strip() or "unknown"
        except Exception as e:
            out[u] = "n/a(%s)" % type(e).__name__
    return out


def done_file(goals):
    p = os.path.join(goals, "DONE")
    if os.path.isfile(p):
        return {"present": True, "text": open(p, encoding="utf-8").read()[:400]}
    return {"present": False, "text": ""}


def last_reports(reports_dir, n=8):
    rows = []
    for p in sorted(glob.glob(os.path.join(reports_dir, "*.md")), reverse=True)[:n]:
        gate = ""
        log = p[:-3] + ".log"
        if os.path.isfile(log):
            try:
                txt = open(log, encoding="utf-8", errors="replace").read()
                for line in txt.splitlines():
                    if "gate_rc" in line:
                        gate = line.strip()
            except OSError:
                pass
        rows.append({"name": os.path.basename(p), "bytes": os.path.getsize(p),
                     "gate": gate})
    return rows


def build(reports=None, goals=None):
    reports = reports or os.environ.get("AIOS_GOAL_REPORTS", "/root/aios-goal-reports")
    goals = goals or os.environ.get("AIOS_GOALS_DIR", "/root/aios-goals")
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    st = S.collect()
    lines = ["# worldcore 长城任务 · 终报（%s）" % now, "",
             "> ★ 本报告由 `scripts/release/dsh/goal/final_report.py` 在截止后生成；只读。", ""]
    lines += ["## 一、截止停链现取", ""]
    df = done_file(goals)
    lines.append("- DONE 文件：%s%s" % ("存在" if df["present"] else "**缺失**",
                                       ("：" + df["text"].replace("\n", " ")) if df["text"] else ""))
    ts = timer_state()
    for k, v in ts.items():
        lines.append("- `%s`：**%s**" % (k, v))
    lines += ["", "## 二、一屏状态", ""]
    sn = st["snapshots"]
    lines.append("- 快照：%d 份；最新 `%s`（at=%s rows=%s）"
                 % (sn["count"], (sn["latest"] or {}).get("name"),
                    (sn["latest"] or {}).get("at"), (sn["latest"] or {}).get("ledger_rows")))
    r = st["rounds"]
    lines.append("- 进度：%d 行；rounds.md=%s" % (r["progress_lines"], r["rounds_md_present"]))
    lines.append("- 游标：%s" % (", ".join("%s=%s" % (k, v) for k, v in st["cursors"].items()) or "（无）"))
    lines.append("- 场景：%s" % (", ".join(st["scenes"]) or "（无）"))
    w = st["worldfs"]
    lines.append("- 世界文件：events=%d scenes=%d INDEX=%d 字节"
                 % (w["event_files"], w["scenes"], w["index_bytes"]))
    g = st["guard"]
    if g.get("ok"):
        de = g["describe"]
        lines.append("- guard：actions=%s grants=%s loaded=%s"
                     % (de.get("actions"), de.get("grants"), de.get("loaded")))
    else:
        lines.append("- guard：不可用（%s）" % g.get("why"))
    if "units" in st:
        bad = [u for u, s in st["units"].items() if s != "active"]
        lines.append("- 单元：%d 个；非 active：%s" % (len(st["units"]), ",".join(bad) or "无"))
    lines += ["", "## 三、最近轮报告", ""]
    for row in last_reports(reports):
        lines.append("- `%s`（%d 字节）%s" % (row["name"], row["bytes"],
                                            ("；" + row["gate"]) if row["gate"] else ""))
    lines += ["", "## 四、已知缺口（如实）", "",
              "1. 记忆/委托两份法草案**未合并**（`src/ontology/proposals/*.proposal.json`，机器校验通过，待人签）；",
              "2. 场景只能落盘/查看，**不能加载/切换**；世界分叉只能看，不能在上面跑；",
              "3. **真账 restore 未演练**（只在临时副本演习过）；",
              "4. **真人语音**（Web Speech 说/听）未验，要人拿 Chrome/Edge 点；",
              "5. 安全债：VM 里 DSH 仍 `danger-full-access`；bus 无 ACL；旧账有明文票（需清理）；",
              "6. 判据不推（本地副本）；VM 工作副本的 agent 本地提交不 push（by design）。", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="final report generator")
    ap.add_argument("--out", default="")
    ap.add_argument("--reports", default="")
    ap.add_argument("--goals", default="")
    a = ap.parse_args(argv)
    txt = build(a.reports or None, a.goals or None)
    out = a.out or os.path.join(os.environ.get("AIOS_GOAL_REPORTS", "/root/aios-goal-reports"),
                                "FINAL-%s.md" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)
    print("out=%s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
