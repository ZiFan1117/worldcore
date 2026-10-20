# -*- coding: utf-8 -*-
"""★ 恢复边界进程的纯函数（只读；借鉴 AI-OS L1「Recovery boundary」）。

★ 读什么：快照根目录下的每份快照的 `meta.json`（at / ledger_rows / law.sha256 / files），
  以及 `forks/<name>/` 的分叉（fork.json 有 parent 就记）。**不写、不恢复、不起外进程**。
"""
import datetime
import json
import os

DEFAULT_ROOT = "/var/backups/aios/world-snapshots"
NAME = os.environ.get("AIOS_RECOVERY_NAME") or "recovery0"


def root():
    return os.environ.get("AIOS_SNAPSHOT_DIR") or DEFAULT_ROOT


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (OSError, ValueError) as e:
        return None, str(e)


def _snapshot_entry(dirpath, name, kind):
    meta, err = _read_json(os.path.join(dirpath, "meta.json"))
    if not isinstance(meta, dict):
        return None
    files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
    total = sum(int((v or {}).get("bytes") or 0) for v in files.values())
    law = meta.get("law") if isinstance(meta.get("law"), dict) else {}
    e = {"name": name, "path": dirpath, "kind": kind,
         "at": meta.get("at"), "ledger_rows": meta.get("ledger_rows"),
         "law_sha256": law.get("sha256"), "bytes": total,
         "files_count": len(files)}
    if kind == "fork":
        fj, _ = _read_json(os.path.join(dirpath, "fork.json"))
        if isinstance(fj, dict):
            e["parent"] = fj.get("parent") or fj.get("from") or fj.get("snapshot")
    return e


def list_snapshots(limit=50):
    r = root()
    if not os.path.isdir(r):
        return True, {"root": r, "count": 0, "forks": 0, "entries": [],
                      "note": "快照根不存在（空列表）"}
    try:
        lim = max(1, min(int(limit or 50), 500))
    except (TypeError, ValueError):
        lim = 50
    snaps, bad = [], 0
    for name in sorted(os.listdir(r), reverse=True):
        if name == "forks":
            continue
        d = os.path.join(r, name)
        if not os.path.isdir(d):
            continue
        e = _snapshot_entry(d, name, "snapshot")
        if e is None:
            bad += 1
            continue
        snaps.append(e)
        if len(snaps) >= lim:
            break
    forks = []
    fdir = os.path.join(r, "forks")
    if os.path.isdir(fdir):
        for name in sorted(os.listdir(fdir), reverse=True):
            d = os.path.join(fdir, name)
            if not os.path.isdir(d):
                continue
            e = _snapshot_entry(d, name, "fork")
            if e is not None:
                forks.append(e)
    return True, {"root": r, "count": len(snaps), "forks": len(forks),
                  "bad_meta": bad, "entries": snaps,
                  "fork_entries": forks[:20]}


def state():
    ok, d = list_snapshots(500)
    snaps = d.get("entries") or []
    latest = snaps[0].get("name") if snaps else ""
    st = {"name": NAME, "state": "running", "root": root(),
          "snapshots": d.get("count", 0), "forks": d.get("forks", 0),
          "latest": latest,
          "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    return True, st


def dispatch(action, params=None):
    params = params if isinstance(params, dict) else {}
    if action == "recovery.list":
        return list_snapshots(params.get("limit"))
    if action == "recovery.state":
        return state()
    return False, "不认识的动作：%s" % action
