#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 世界快照（P4 第一刀）—— 把这个世界「此刻的事实＋法」打包，能验、能回滚。

★ 作者令（逐字整理）：「整个世界要不断进化」；os-gaps：世界快照/回放/分叉是自进化的基础。

用法：
  python3 world_snapshot.py save [--out DIR]       # 打包：账＋注册表＋对象库＋法源＋meta
  python3 world_snapshot.py list [--dir DIR]       # 列表（每份的 law hash / 账行数）
  python3 world_snapshot.py verify --snap DIR      # 验：文件齐、meta 齐、law hash 对得上
  python3 world_snapshot.py prune [--keep 24]       # 只留最近 N 份（定时快照用）
  python3 world_snapshot.py fork --snap DIR --name NAME [--dir FORKDIR]
      # 分叉：从一份快照拷出一个「平行世界」（不改原件）；fork.json 记 parent
  python3 world_snapshot.py timeline [--dir DIR]    # 时间线：快照＋分叉（谁从谁分出来）
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

import worldfs_manifest  # noqa: E402  worldfs manifest 边车

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)) if os.path.basename(HERE) == "release" else os.getcwd()
LAW = os.environ.get("AIOS_LAW_JSON", os.path.join(ROOT, "src", "ontology", "world.json"))
LEDGER = os.environ.get("AIOS_LEDGER", "/var/lib/aios/ontology/ledger.jsonl")
REGISTRY = os.environ.get("AIOS_REGISTRY", "/var/lib/aios/ontology/registry.jsonl")
STORE = os.environ.get("AIOS_STORE_DB", "/var/lib/aios/ontology/objects.db")
DEFAULT_DIR = os.environ.get("AIOS_SNAPSHOT_DIR", "/var/backups/aios/world-snapshots")
META = "meta.json"
PAUSE_UNITS = ("aios-worldfs-fuse", "aios-worldfs", "aios-ontology")


def _pause_units():
    """★ 快照/恢复前停 worldfs+ontology，保证账和文件系统同一刀切。"""
    if not shutil.which("systemctl"):
        return []
    done = []
    for u in PAUSE_UNITS:
        r = subprocess.run(["systemctl", "stop", u], capture_output=True, text=True)
        if r.returncode == 0:
            done.append(u)
    return done


def _resume_units(units):
    if not shutil.which("systemctl"):
        return
    for u in units or PAUSE_UNITS:
        subprocess.run(["systemctl", "start", u], capture_output=True, text=True)


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
    paused = _pause_units()
    try:
        os.makedirs(out, exist_ok=False)
        wfs = None
        if os.path.isfile(worldfs_manifest.DB):
            try:
                wfs = worldfs_manifest.capture(out)
            except Exception as e:                              # noqa: BLE001
                print("拒：worldfs manifest 打包失败：%s" % e)
                return 1
        files = {"ledger.jsonl": LEDGER, "registry.jsonl": REGISTRY,
                 "objects.db": STORE, "world.json": LAW}
        meta = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                "host": os.uname().nodename if hasattr(os, "uname") else "?",
                "law": {"path": LAW, "sha256": _sha(LAW) if os.path.exists(LAW) else None},
                "ledger_rows": _rows(LEDGER) if os.path.exists(LEDGER) else 0,
                "worldfs": wfs,
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
        print("law_sha256=%s ledger_rows=%d worldfs_epoch=%s worldfs_root=%s"
              % (meta["law"]["sha256"], meta["ledger_rows"],
                 (wfs or {}).get("epoch"), str((wfs or {}).get("root_sha"))[:12]))
        return 0
    finally:
        _resume_units(paused)


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


def cmd_fork(args):
    """★ 分叉：从快照拷出一个平行世界（只读源；不改原件）。"""
    if not os.path.isdir(args.snap):
        print("拒：快照不存在 %s" % args.snap)
        return 1
    src_meta = os.path.join(args.snap, META)
    if not os.path.isfile(src_meta):
        print("拒：%s 不是快照（没有 %s）" % (args.snap, META))
        return 1
    base = args.dir or os.path.join(os.path.dirname(os.path.abspath(args.snap)), "forks")
    name = args.name or _stamp()
    dst = os.path.join(base, name)
    if os.path.exists(dst) and not args.yes:
        print("拒：分叉已存在 %s（要覆盖加 --yes）" % dst)
        return 1
    os.makedirs(base, exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(args.snap, dst)
    with open(src_meta, encoding="utf-8") as f:
        m = json.load(f)
    fork = {"name": name, "parent": os.path.basename(os.path.abspath(args.snap)),
            "parent_path": os.path.abspath(args.snap),
            "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "law": m.get("law"), "ledger_rows": m.get("ledger_rows"),
            "files": m.get("files")}
    with open(os.path.join(dst, "fork.json"), "w", encoding="utf-8") as f:
        json.dump(fork, f, ensure_ascii=False, indent=2)
    print("fork=%s" % dst)
    print("parent=%s  ledger_rows=%s" % (fork["parent"], fork["ledger_rows"]))
    return 0


def cmd_timeline(args):
    """★ 时间线：快照（根目录）＋分叉（forks 子目录），标出 parent。"""
    d = args.dir or DEFAULT_DIR
    rows = []
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            mp = os.path.join(d, name, META)
            if os.path.isfile(mp):
                try:
                    m = json.load(open(mp, encoding="utf-8"))
                except Exception:
                    continue
                rows.append(("snapshot", name, "-", m.get("at"), m.get("ledger_rows")))
    fdir = os.path.join(d, "forks")
    if os.path.isdir(fdir):
        for name in sorted(os.listdir(fdir)):
            fp = os.path.join(fdir, name, "fork.json")
            if not os.path.isfile(fp):
                continue
            try:
                f = json.load(open(fp, encoding="utf-8"))
            except Exception:
                continue
            rows.append(("fork", name, f.get("parent") or "-", f.get("at"),
                         f.get("ledger_rows")))
    for kind, name, parent, at, n in rows:
        print("%-8s %-28s parent=%-24s at=%s rows=%s"
              % (kind, name, parent, at, n))
    print("total=%d" % len(rows))
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
        bad.append("快照的法与当前法不一致（旧快照；恢复前要想清楚）")
    info = {}
    if (os.path.isfile(os.path.join(args.snap, worldfs_manifest.MANIFEST))
            or os.path.isfile(worldfs_manifest.DB)):
        ok, wbad, info = worldfs_manifest.verify(args.snap)
        bad += wbad
    if bad:
        for b in bad:
            print("[红] " + b)
        return 1
    print("verify=ok  files=%d  law=%s  worldfs_epoch=%s worldfs_root=%s"
          % (len(m.get("files") or {}), (m.get("law") or {}).get("sha256", "")[:12],
             info.get("epoch"), str(info.get("root_sha"))[:12]))
    return 0


def cmd_restore(args):
    if not args.yes:
        print("拒：restore 必须带 --yes（会覆盖当前账/注册表/对象库/worldfs）")
        return 1
    has_wfs = os.path.isfile(os.path.join(args.snap, worldfs_manifest.MANIFEST))
    info = {}
    if has_wfs or os.path.isfile(worldfs_manifest.DB):
        ok, wbad, info = worldfs_manifest.verify(args.snap)
        if not ok:
            print("拒：worldfs 快照不可用（不能还原成两套事实）：")
            for b in wbad:
                print("  - " + b)
            return 1
    ts = _stamp()
    paused = _pause_units()
    try:
        pairs = {"ledger.jsonl": LEDGER, "registry.jsonl": REGISTRY, "objects.db": STORE}
        for name, dst in pairs.items():
            src = os.path.join(args.snap, name)
            if not os.path.isfile(src):
                print("拒：快照缺 %s" % name)
                return 1
            if os.path.exists(dst):
                shutil.copy2(dst, dst + ".pre-restore-" + ts)
            shutil.copy2(src, dst)
        if has_wfs:
            wok, wwhy = worldfs_manifest.restore(args.snap)
            if not wok:
                print("拒：worldfs 恢复失败：%s" % wwhy)
                return 1
            print("restored=%s（旧文件已备份为 *.pre-restore-%s）" % (args.snap, ts))
            print(wwhy)
        else:
            print("restored=%s（旧文件已备份为 *.pre-restore-%s；旧快照不带 worldfs，按 ontology-only 恢复）"
                  % (args.snap, ts))
        return 0
    finally:
        _resume_units(paused)
        if args.restart and shutil.which("systemctl"):
            for u in ("aios-space", "aios-agent", "aios-presentation"):
                subprocess.run(["systemctl", "restart", u], check=False)
            print("restarted: aios-space/agent/presentation")


def main(argv=None):
    ap = argparse.ArgumentParser(description="world snapshot: save/list/verify/restore")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("--out")
    s.set_defaults(func=cmd_save)
    l = sub.add_parser("list")
    l.add_argument("--dir")
    l.set_defaults(func=cmd_list)
    fk = sub.add_parser("fork")
    fk.add_argument("--snap", required=True)
    fk.add_argument("--name", required=True)
    fk.add_argument("--dir")
    fk.add_argument("--yes", action="store_true")
    fk.set_defaults(func=cmd_fork)
    tl = sub.add_parser("timeline")
    tl.add_argument("--dir")
    tl.set_defaults(func=cmd_timeline)
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
