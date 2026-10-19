#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ worldcore 一屏状态（`status.py`）—— 给 06:00 交接/终报用：一条命令看全。

用法：
  python3 status.py            # 人读
  python3 status.py --json     # 机读
★ 只读：不启动/不停止/不改任何东西。
"""
import argparse
import glob
import json
import os
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GOALS = os.environ.get("AIOS_GOALS_DIR", "/root/aios-goals")
SNAPS = os.environ.get("AIOS_SNAPSHOT_DIR", "/var/backups/aios/world-snapshots")
CURSORS = os.environ.get("AIOS_CURSOR_DIR", "/var/lib/aios/cursors")
SCENES = os.environ.get("AIOS_SCENES_DIR", "/var/lib/aios/scenes")
WORLDFS = os.environ.get("AIOS_WORLDFS", "/var/lib/aios/world")
SOCK = os.environ.get("AIOS_GUARD_SOCK", "/run/aios/guard.sock")
UNITS = ("aios-bus", "aios-ontology", "aios-guard", "aios-web", "aios-computer",
         "aios-presentation", "aios-presentation-render", "aios-space", "aios-agent")


def snapshot_summary(d=SNAPS):
    rows = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        mp = os.path.join(d, name, "meta.json")
        if not os.path.isfile(mp):
            continue
        try:
            m = json.load(open(mp, encoding="utf-8"))
        except Exception:
            continue
        rows.append({"name": name, "at": m.get("at"), "ledger_rows": m.get("ledger_rows")})
    return {"dir": d, "count": len(rows),
            "latest": rows[-1] if rows else None, "rows": rows[-3:]}


def rounds_summary(progress=os.path.join(GOALS, "progress.md"),
                   rounds_md=os.path.join(GOALS, "rounds.md")):
    last = []
    try:
        lines = [ln.rstrip("\n") for ln in open(progress, encoding="utf-8") if ln.strip()]
        last = lines[-3:]
        n = len(lines)
    except Exception:
        n = 0
    md = ""
    try:
        md = open(rounds_md, encoding="utf-8").read()
    except Exception:
        pass
    return {"progress_lines": n, "last_rounds": last,
            "rounds_md_present": bool(md),
            "rounds_md_head": md.splitlines()[:8]}


def cursors_summary(d=CURSORS):
    out = {}
    for p in glob.glob(os.path.join(d, "*.json")):
        try:
            out[os.path.basename(p)] = json.load(open(p, encoding="utf-8")).get("cursor")
        except Exception:
            out[os.path.basename(p)] = "<坏文件>"
    return out


def scenes_summary(d=SCENES):
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, "*.json")))


def worldfs_summary(d=WORLDFS):
    ev = glob.glob(os.path.join(d, "events", "*", "*.jsonl"))
    sc = glob.glob(os.path.join(d, "scenes", "*.json"))
    idx = os.path.join(d, "INDEX.md")
    return {"dir": d, "event_files": len(ev), "scenes": len(sc),
            "index_bytes": os.path.getsize(idx) if os.path.isfile(idx) else 0}


def guard_query(sock=SOCK):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(sock)
        f = s.makefile("rwb")
        f.write(b'{"op":"describe"}\n')
        f.flush()
        out = json.loads(f.readline().decode("utf-8", "replace"))
        s.close()
        return {"ok": True, "describe": out}
    except Exception as e:
        return {"ok": False, "why": "%s: %s" % (type(e).__name__, e)}


def units():
    out = {}
    for u in UNITS:
        try:
            p = subprocess.run(["systemctl", "is-active", u], capture_output=True,
                               text=True, timeout=5)
            out[u] = (p.stdout or "").strip() or "unknown"
        except Exception as e:
            out[u] = "n/a(%s)" % type(e).__name__
    return out


def collect(with_units=True, with_guard=True):
    d = {"snapshots": snapshot_summary(), "rounds": rounds_summary(),
         "cursors": cursors_summary(), "scenes": scenes_summary(),
         "worldfs": worldfs_summary()}
    if with_units:
        d["units"] = units()
    if with_guard:
        d["guard"] = guard_query()
    return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    d = collect()
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    print("=== worldcore 一屏状态 ===")
    sn = d["snapshots"]
    print("快照：%d 份；最新 %s（at=%s rows=%s）"
          % (sn["count"], (sn["latest"] or {}).get("name"), (sn["latest"] or {}).get("at"),
             (sn["latest"] or {}).get("ledger_rows")))
    r = d["rounds"]
    print("进度：%d 行；rounds.md=%s" % (r["progress_lines"], r["rounds_md_present"]))
    for ln in r["last_rounds"]:
        print("  " + ln)
    print("游标：%s" % (", ".join("%s=%s" % (k, v) for k, v in d["cursors"].items()) or "（无）"))
    print("场景文件：%s" % (", ".join(d["scenes"]) or "（无）"))
    w = d["worldfs"]
    print("世界文件：events=%d scenes=%d INDEX=%d 字节"
          % (w["event_files"], w["scenes"], w["index_bytes"]))
    g = d["guard"]
    if g.get("ok"):
        de = g["describe"]
        print("guard：actions=%s grants=%s loaded=%s"
              % (de.get("actions"), de.get("grants"), de.get("loaded")))
    else:
        print("guard：不可用（%s）" % g.get("why"))
    if "units" in d:
        bad = [u for u, st in d["units"].items() if st not in ("active",)]
        print("单元：%d 个；非 active：%s" % (len(d["units"]), ",".join(bad) or "无"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
