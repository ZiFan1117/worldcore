#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""world_snapshot 的 worldfs manifest 边车（P4）。

把 worldfs 的 epoch/root/paths/versions/path_events/blob 清单打进快照；
restore 时按同一 manifest 把 worldfs 的 db/blob 也退回那一刻。
★ 不含账：worldfs 没账（C85）；这里只是内容/版本/路径状态。
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess

WORLDFS_ROOT = os.environ.get("AIOS_WORLDFS_ROOT") or "/var/lib/aios/worldfs"
DB = os.environ.get("AIOS_WORLDFS_DB") or os.path.join(WORLDFS_ROOT, "worldfs.db")
BLOBS = os.environ.get("AIOS_WORLDFS_BLOBS") or os.path.join(WORLDFS_ROOT, "blobs", "sha256")
MANIFEST = "worldfs_manifest.json"
UNITS = ("aios-worldfs-fuse", "aios-worldfs")


def _has_systemctl():
    return bool(shutil.which("systemctl"))


def pause():
    """★ 快照/恢复前停 worldfs，保证账和文件系统同一刀切。无 systemd 返回 []。"""
    if not _has_systemctl():
        return []
    done = []
    for u in UNITS:
        r = subprocess.run(["systemctl", "stop", u], capture_output=True, text=True)
        if r.returncode == 0:
            done.append(u)
    return done


def resume(units):
    if not _has_systemctl():
        return
    for u in units or UNITS:
        subprocess.run(["systemctl", "start", u], capture_output=True, text=True)


def _conn(path=None, ro=False):
    p = path or DB
    if ro:
        c = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    else:
        c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


def _rows(c, sql):
    return [dict(r) for r in c.execute(sql)]


def _root(paths, versions):
    blob = {v["ver_id"]: v for v in versions}
    payload = []
    for p in sorted(paths, key=lambda x: x["path"]):
        v = blob.get(p.get("ver_id")) or {}
        payload.append([p["path"], p["obj_id"], p["seq"], p["kind"],
                        v.get("blob_sha256") or "", int(v.get("size") or 0)])
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _db_state(c, path=None):
    paths = _rows(c, """
        SELECT p.path, p.obj_id, p.seq, p.kind,
               COALESCE(v.ver_id,'') AS ver_id, COALESCE(v.blob_sha256,'') AS blob_sha256,
               COALESCE(v.size,0) AS size
        FROM paths p LEFT JOIN versions v ON v.obj_id=p.obj_id AND v.seq=p.seq
        ORDER BY p.path
    """)
    versions = _rows(c, "SELECT * FROM versions ORDER BY obj_id,seq")
    events = _rows(c, "SELECT * FROM path_events ORDER BY event_id")
    meta = {r["key"]: r["value"] for r in c.execute("SELECT * FROM meta")}
    return {"epoch": int(meta.get("epoch") or 0),
            "root_sha": _root(paths, versions),
            "paths": paths, "versions": versions, "path_events": events}


def capture(out):
    """在 out 下写 manifest + worldfs.db + worldfs_blobs/；返回给 snapshot meta 的摘要。"""
    if not os.path.isfile(DB):
        raise RuntimeError("worldfs DB 不存在：%s" % DB)
    c = _conn(ro=True)
    try:
        st = _db_state(c)
    finally:
        c.close()
    manifest = {"schema": "worldfs-manifest-1", "epoch": st["epoch"],
                "root_sha": st["root_sha"], "paths": st["paths"],
                "versions": st["versions"], "path_events": st["path_events"]}
    with open(os.path.join(out, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    # DB 用 SQLite backup（不裸拷 WAL）
    dst = os.path.join(out, "worldfs.db")
    src = _conn()
    outdb = sqlite3.connect(dst)
    try:
        src.backup(outdb)
    finally:
        outdb.close()
        src.close()
    # 只带 manifest 引用到的 blob；内容寻址，缺一个就拒
    bdir = os.path.join(out, "worldfs_blobs", "sha256")
    os.makedirs(bdir, exist_ok=True)
    blobs = sorted({v["blob_sha256"] for v in st["versions"] if v.get("blob_sha256")})
    for sha in blobs:
        s = os.path.join(BLOBS, sha[:2], sha)
        if not os.path.isfile(s):
            raise RuntimeError("worldfs blob 缺失：%s" % s)
        d = os.path.join(bdir, sha[:2], sha)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
    return {"epoch": st["epoch"], "root_sha": st["root_sha"],
            "paths": len(st["paths"]), "versions": len(st["versions"]),
            "path_events": len(st["path_events"]), "blobs": len(blobs),
            "manifest": MANIFEST}


def verify(snap):
    """返回 (ok, bad[], info)。验 manifest root、blob、DB 副本 root 一致性。"""
    bad = []
    mp = os.path.join(snap, MANIFEST)
    if not os.path.isfile(mp):
        return False, ["缺 %s（老快照没带 worldfs）" % MANIFEST], {}
    try:
        m = json.load(open(mp, encoding="utf-8"))
    except Exception as e:                                      # noqa: BLE001
        return False, ["manifest 读不出：%s" % e], {}
    root = _root(m.get("paths") or [], m.get("versions") or [])
    if root != m.get("root_sha"):
        bad.append("manifest root 不符：%r ≠ %r" % (root, m.get("root_sha")))
    for v in m.get("versions") or []:
        sha = v.get("blob_sha256") or ""
        if not sha:
            continue
        p = os.path.join(snap, "worldfs_blobs", "sha256", sha[:2], sha)
        if not os.path.isfile(p):
            bad.append("缺 blob：%s" % sha[:12])
            continue
        if _sha_file(p) != sha:
            bad.append("blob sha 不符：%s" % sha[:12])
    dbp = os.path.join(snap, "worldfs.db")
    if not os.path.isfile(dbp):
        bad.append("缺 worldfs.db 副本")
    else:
        c = _conn(dbp, ro=True)
        try:
            st = _db_state(c)
        finally:
            c.close()
        if st["root_sha"] != m.get("root_sha"):
            bad.append("快照 DB root 与 manifest 不符")
    return not bad, bad, m


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def restore(snap):
    """把 worldfs DB/blob 退回快照；返回 (ok, why)。调用方负责停/起单元。"""
    ok, bad, m = verify(snap)
    if not ok:
        return False, "worldfs 快照不可用：" + "; ".join(bad)
    ts = os.path.basename(snap.rstrip("/")) or "snap"
    # 旧 DB 备份
    for suffix in ("", "-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            shutil.copy2(p, p + ".pre-restore-" + ts)
    src = os.path.join(snap, "worldfs.db")
    if os.path.isfile(src):
        tmp = DB + ".restore-tmp"
        shutil.copy2(src, tmp)
        os.replace(tmp, DB)
    for suffix in ("-wal", "-shm"):
        try:
            os.remove(DB + suffix)
        except OSError:
            pass
    # 补 blob（同 sha 已存在就跳）
    for v in m.get("versions") or []:
        sha = v.get("blob_sha256") or ""
        if not sha:
            continue
        s = os.path.join(snap, "worldfs_blobs", "sha256", sha[:2], sha)
        d = os.path.join(BLOBS, sha[:2], sha)
        if not os.path.isfile(d) or _sha_file(d) != sha:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    # 恢复后复核
    c = _conn(DB, ro=True)
    try:
        st = _db_state(c)
    finally:
        c.close()
    if st["root_sha"] != m.get("root_sha"):
        return False, "恢复后 DB root 不符（%r ≠ %r）" % (st["root_sha"], m.get("root_sha"))
    return True, "worldfs restored：epoch=%r root=%r" % (m.get("epoch"), m.get("root_sha"))
