#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 世界快照（P4 第一刀）—— 把这个世界「此刻的事实＋法」打包，能验、能回滚。

★ 作者令（逐字整理）：「整个世界要不断进化」；os-gaps：世界快照/回放/分叉是自进化的基础。

用法：
  python3 world_snapshot.py save [--out DIR]       # 打包：账＋注册表＋对象库＋法源＋meta
  python3 world_snapshot.py list [--dir DIR]       # 列表（每份的 law hash / 账行数）
  python3 world_snapshot.py verify --snap DIR      # 验：文件齐、meta 齐、law hash 对得上
  python3 world_snapshot.py prune [--keep 24]       # 只留最近 N 份（定时快照用）
  python3 world_snapshot.py restore --snap DIR --yes [--restart]
      # 回滚：先备份现文件为 *.pre-restore-<ts>，再覆盖；--restart 才重启本体/空间（默认不重启）

★ 不打包：permit.key、票、密码、params —— 快照是事实包，不是密码本。
★ 路径全部可用环境变量覆盖（与本体一致）：AIOS_LEDGER／AIOS_REGISTRY／AIOS_STORE_DB；
  法源默认 repo 的 src/ontology/world.json；快照目录默认 /var/backups/aios/world-snapshots。
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)) if os.path.basename(HERE) == "release" else os.getcwd()
LAW = os.environ.get("AIOS_LAW_JSON", os.path.join(ROOT, "src", "ontology", "world.json"))
LEDGER = os.environ.get("AIOS_LEDGER", "/var/lib/aios/ontology/ledger.jsonl")
REGISTRY = os.environ.get("AIOS_REGISTRY", "/var/lib/aios/ontology/registry.jsonl")
STORE = os.environ.get("AIOS_STORE_DB", "/var/lib/aios/ontology/objects.db")
DEFAULT_DIR = os.environ.get("AIOS_SNAPSHOT_DIR", "/var/backups/aios/world-snapshots")
META = "meta.json"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _stamp():
    return datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _rows(path):
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def cmd_save(args):
    out = args.out or os.path.join(DEFAULT_DIR, _stamp())
    if os.path.exists(out):
        print("拒：目标已存在 %s" % out)
        return 1
    os.makedirs(out, exist_ok=False)
    files = {"ledger.jsonl": LEDGER, "registry.jsonl": REGISTRY, "objects.db": STORE,
             "world.json": LAW}
    meta = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "host": os.uname().nodename if hasattr(os, "uname") else "?",
            "law": {"path": LAW, "sha256": _sha(LAW) if os.path.exists(LAW) else None},
            "ledger_rows": _rows(LEDGER) if os.path.exists(LEDGER) else 0,
            "files": {}}
    for name, src in files.items():
        if not os.path.exists(src):
            print("拒：缺文件 %s（%s）" % (name, src))
            return 1
        shutil.copy2(src, os.path.join(out, name))
        meta["files"][name] = {"sha256": _sha(src), "bytes": os.path.getsize(src)}
    with open(os.path.join(out, META), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("snapshot=%s" % out)
    print("law_sha256=%s ledger_rows=%d" % (meta["law"]["sha256"], meta["ledger_rows"]))
    return 0


def cmd_list(args):
    d = args.dir or DEFAULT_DIR
    if not os.path.isdir(d):
        print("没有快照目录：%s" % d)
        return 0
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name, META)
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        print("%s  law=%s  ledger_rows=%s  at=%s"
              % (name, (m.get("law") or {}).get("sha256", "")[:12],
                 m.get("ledger_rows"), m.get("at")))
    return 0


def cmd_prune(args):
    """★ 保留最近 N 份快照（时间戳目录名排序），其余删掉。"""
    d = args.dir or DEFAULT_DIR
    if not os.path.isdir(d):
        print("没有快照目录：%s" % d)
        return 0
    snaps = [n for n in sorted(os.listdir(d))
             if os.path.isdir(os.path.join(d, n)) and
             os.path.isfile(os.path.join(d, n, META))]
    keep = max(1, int(args.keep))
    drop = snaps[:-keep] if len(snaps) > keep else []
    for n in drop:
        shutil.rmtree(os.path.join(d, n), ignore_errors=True)
        print("pruned=%s" % n)
    print("kept=%d  pruned=%d" % (min(len(snaps), keep), len(drop)))
    return 0


def cmd_verify(args):
    bad = []
    p = os.path.join(args.snap, META)
    if not os.path.isfile(p):
        print("拒：没有 %s" % p)
        return 1
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    for name, rec in (m.get("files") or {}).items():
        fp = os.path.join(args.snap, name)
        if not os.path.isfile(fp):
            bad.append("缺文件 %s" % name)
            continue
        if _sha(fp) != rec.get("sha256"):
            bad.append("sha 不对 %s" % name)
    if os.path.exists(LAW) and m.get("law", {}).get("sha256") != _sha(LAW):
        bad.append("快照的法和当前法不一致（这是“旧快照”，恢复前要想清楚）")
    if bad:
        for b in bad:
            print("[红] " + b)
        return 1
    print("verify=ok  files=%d  law=%s" % (len(m.get("files") or {}),
                                           (m.get("law") or {}).get("sha256", "")[:12]))
    return 0


def cmd_restore(args):
    if not args.yes:
        print("拒：restore 必须带 --yes（会覆盖当前账/注册表/对象库）")
        return 1
    ts = _stamp()
    pairs = {"ledger.jsonl": LEDGER, "registry.jsonl": REGISTRY, "objects.db": STORE}
    for name, dst in pairs.items():
        src = os.path.join(args.snap, name)
        if not os.path.isfile(src):
            print("拒：快照缺 %s" % name)
            return 1
        if os.path.exists(dst):
            shutil.copy2(dst, dst + ".pre-restore-" + ts)
        shutil.copy2(src, dst)
    print("restored=%s（旧文件已备份为 *.pre-restore-%s）" % (args.snap, ts))
    if args.restart:
        for u in ("aios-ontology", "aios-space", "aios-agent", "aios-presentation"):
            subprocess.run(["systemctl", "restart", u], check=False)
        print("restarted: aios-ontology/space/agent/presentation")
    else:
        print("提示：要生效请重启 aios-ontology 等单元（或加 --restart）")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="world snapshot: save/list/verify/restore")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("--out")
    s.set_defaults(func=cmd_save)
    l = sub.add_parser("list")
    l.add_argument("--dir")
    l.set_defaults(func=cmd_list)
    v = sub.add_parser("verify")
    v.add_argument("--snap", required=True)
    v.set_defaults(func=cmd_verify)
    pr = sub.add_parser("prune")
    pr.add_argument("--keep", type=int, default=24)
    pr.add_argument("--dir")
    pr.set_defaults(func=cmd_prune)
    r = sub.add_parser("restore")
    r.add_argument("--snap", required=True)
    r.add_argument("--yes", action="store_true")
    r.add_argument("--restart", action="store_true")
    r.set_defaults(func=cmd_restore)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
