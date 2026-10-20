#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""14 单元 + 世界收口 soak（只读采样；每 5 分钟一行 JSONL）。

用法（VM）：
  nohup python3 /root/aios/scripts/release/soak_13units.py --minutes 90 \
      > /root/soak.out 2>&1 &
  # 读：cat /root/soak-13units.jsonl
"""
import argparse
import collections
import json
import os
import subprocess
import time

LEDGER = "/var/lib/aios/ontology/ledger.jsonl"
OUT = "/root/soak-13units.jsonl"
UNITS = ["aios-bus", "aios-ontology", "aios-guard", "aios-web", "aios-computer",
         "aios-presentation", "aios-presentation-render", "aios-space", "aios-agent",
         "aios-fs", "aios-clock", "aios-recovery", "aios-network", "aios-vault"]


def sh(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception as e:                                      # noqa: BLE001
        return "ERR:%s" % e


def units_state():
    return {u: sh(["systemctl", "is-active", u]) for u in UNITS}


def ledger_stats():
    rows = []
    try:
        with open(LEDGER, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except OSError:
        pass
    classes = collections.Counter(r.get("class") for r in rows if r.get("kind_of") == "appear")
    comp = [r for r in rows if r.get("kind_of") == "appear"
            and str(r.get("subject") or "").startswith("computer/")]
    last = comp[-1].get("after") if comp else {}
    return {"rows": len(rows), "appear_classes": dict(classes),
            "last_computer_at": comp[-1].get("at") if comp else None,
            "last_computer_load1": last.get("load1"),
            "last_computer_mem_avail": last.get("mem_available_mb")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=90)
    ap.add_argument("--every", type=float, default=300)
    args = ap.parse_args()
    end = time.time() + args.minutes * 60
    while time.time() < end:
        rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "units": units_state(), "ledger": ledger_stats(),
               "agent_heartbeat": sh(["cat", "/run/aios/agent-heartbeat.json"]),
               "fs_log_tail": sh(["journalctl", "-u", "aios-fs", "--no-pager", "-n", "2"]),
               "errors": sh(["journalctl", "-u", "aios-fs", "-u", "aios-clock",
                              "-u", "aios-recovery", "-u", "aios-network",
                              "--since", "-6min", "--no-pager"])[-800:]}
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
