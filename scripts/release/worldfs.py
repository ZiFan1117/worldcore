#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 世界＝文件（P3 第一刀，借 sen-core／Gnowsis 的「语义桌面」理念）——把账**导出成目录树**，人可 grep、agent 可读。

★ 作者（逐字）：「有没有什么有用的东西」；sen-core 把语义核心贴在文件系统上，Gnowsis 把桌面对象做成树。
★ 这里先做最稳的一半：**只读导出**（世界历史 → `events/<日期>/<小时>.jsonl` ＋ `INDEX.md`），写路径仍只走本体。
★ 安全：只导**公开字段白名单**（at/family/kind_of/action/actor/ok/code/category/subject/notice_kind/ui_action/route），
  **绝不导 params/body/why/ticket**——旧账里有明文票的教训（T-398）不能被导出放大。

用法：
  python3 worldfs.py export [--out DIR]      # 导出（默认 /var/lib/aios/world）
  python3 worldfs.py query --action X [--kind K] [--limit N]   # 在导出的树里查
"""
import argparse
import collections
import datetime
import json
import os
import sys

LEDGER = os.environ.get("AIOS_LEDGER", "/var/lib/aios/ontology/ledger.jsonl")
DEFAULT_OUT = os.environ.get("AIOS_WORLDFS", "/var/lib/aios/world")
KEEP = ("at", "family", "kind_of", "action", "actor", "ok", "code", "category",
        "subject", "notice_kind", "ui_action", "route")
HIDDEN = ("params", "body", "why", "ticket", "secret", "password")


def _rows(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _safe(row):
    ev = {}
    for k in KEEP:
        if k in row and row[k] is not None:
            ev[k] = row[k]
    for k in HIDDEN:
        ev.pop(k, None)
    return ev


def _hour_key(at):
    s = str(at or "")
    # ISO: 2026-10-19T19:00:00+02:00
    if "T" in s and len(s) >= 16:
        return s[:10], s[11:13]
    return "unknown", "00"


def cmd_export(args):
    out = args.out or DEFAULT_OUT
    rows = _rows(args.ledger)
    by_kind = collections.Counter()
    by_action = collections.Counter()
    buckets = collections.defaultdict(list)
    for r in rows:
        ev = _safe(r)
        if not ev:
            continue
        by_kind[ev.get("kind_of") or "?"] += 1
        if ev.get("action"):
            by_action[ev["action"]] += 1
        d, h = _hour_key(ev.get("at"))
        buckets[(d, h)].append(ev)
    for (d, h), evs in buckets.items():
        p = os.path.join(out, "events", d)
        os.makedirs(p, exist_ok=True)
        with open(os.path.join(p, h + ".jsonl"), "w", encoding="utf-8") as f:
            for ev in evs:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    os.makedirs(out, exist_ok=True)
    idx = ["# worldcore · 世界文件索引", "",
           "- 导出时间：%s" % datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "- 源账：`%s`（只读导出；写路径仍只走本体）" % args.ledger,
           "- 行数：**%d**" % sum(by_kind.values()), "",
           "## 按 kind", ""]
    for k, n in by_kind.most_common():
        idx.append("- `%s`：%d" % (k, n))
    idx += ["", "## 动作 Top 20", ""]
    for a, n in by_action.most_common(20):
        idx.append("- `%s`：%d" % (a, n))
    idx += ["", "## 目录", "", "- `events/<日期>/<小时>.jsonl`：一行一事件（公开字段）", ""]
    with open(os.path.join(out, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx) + "\n")
    print("worldfs=%s  files=%d  events=%d" % (out, len(buckets), sum(by_kind.values())))
    return 0


def cmd_query(args):
    root = os.path.join(args.out or DEFAULT_OUT, "events")
    n = 0
    if not os.path.isdir(root):
        print("没有导出的世界：%s" % root)
        return 1
    for d in sorted(os.listdir(root)):
        dp = os.path.join(root, d)
        if not os.path.isdir(dp):
            continue
        for fn in sorted(os.listdir(dp)):
            if not fn.endswith(".jsonl"):
                continue
            with open(os.path.join(dp, fn), encoding="utf-8") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if args.action and ev.get("action") != args.action:
                        continue
                    if args.kind and ev.get("kind_of") != args.kind:
                        continue
                    print(line.rstrip())
                    n += 1
                    if args.limit and n >= args.limit:
                        print("…（到 limit=%d）" % args.limit)
                        return 0
    print("matched=%d" % n)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="world as files (read-only export)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--out")
    e.add_argument("--ledger", default=LEDGER)
    e.set_defaults(func=cmd_export)
    q = sub.add_parser("query")
    q.add_argument("--out")
    q.add_argument("--action")
    q.add_argument("--kind")
    q.add_argument("--limit", type=int, default=50)
    q.set_defaults(func=cmd_query)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
