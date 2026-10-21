# -*- coding: utf-8 -*-
"""★ worldfs 语义边界（C91）：全局 epoch/root、append-only path_events、对象/版本引用。

从 worldfs_store 拆出（C27 一文件一块）；store 只留技术读写。
"""
import hashlib
import json


def parent_of(path):
    p = path.rsplit("/", 1)[0]
    return p or "/worldfs"


def root_of(c):
    rows = c.execute("""
        SELECT p.path, p.obj_id, p.seq, p.kind,
               COALESCE(v.blob_sha256, ''), COALESCE(v.size, 0)
        FROM paths p LEFT JOIN versions v
          ON v.obj_id=p.obj_id AND v.seq=p.seq
        ORDER BY p.path
    """).fetchall()
    payload = [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()


def init_v3(c, schema):
    c.executescript(schema)
    meta = {r["key"]: r["value"] for r in c.execute("SELECT * FROM meta")}
    if not meta.get("epoch"):
        epoch = 1
        root = root_of(c)
        c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('epoch',?)", (str(epoch),))
        c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('root_sha',?)", (root,))
        if not c.execute("SELECT 1 FROM path_events LIMIT 1").fetchone():
            for r in c.execute("SELECT path,obj_id,seq,kind FROM paths ORDER BY path"):
                c.execute("INSERT INTO path_events(epoch,path,obj_id,seq,kind,state)"
                          " VALUES(?,?,?,?,?,'active')",
                          (epoch, r["path"], r["obj_id"], r["seq"], r["kind"]))
    c.execute("PRAGMA user_version=3")


def meta(c):
    d = {r["key"]: r["value"] for r in c.execute("SELECT * FROM meta")}
    return int(d.get("epoch") or 0), d.get("root_sha") or ""


def bump(c, events):
    epoch, _root = meta(c)
    epoch += 1
    root = root_of(c)
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('epoch',?)", (str(epoch),))
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('root_sha',?)", (root,))
    for path, obj_id, seq, kind, state in events:
        c.execute("INSERT INTO path_events(epoch,path,obj_id,seq,kind,state)"
                  " VALUES(?,?,?,?,?,?)", (epoch, path, obj_id, seq, kind, state))
    return epoch, root


def history(c, path):
    rows = c.execute("SELECT * FROM path_events WHERE path=? ORDER BY event_id",
                     (path,)).fetchall()
    return {"path": path, "count": len(rows),
            "events": [{"event_id": r["event_id"], "epoch": r["epoch"],
                        "path": r["path"], "obj_id": r["obj_id"],
                        "seq": r["seq"], "kind": r["kind"],
                        "state": r["state"]} for r in rows]}


def snapshot(st):
    return {"kind": "snapshot", "epoch": st.get("epoch"),
            "root_sha": st.get("root_sha"), "objects": st.get("objects"),
            "versions": st.get("versions"), "paths": st.get("paths"),
            "blobs": st.get("blobs")}


def get_ref(c, ref, seq=None):
    ref = str(ref or "")
    if ref.startswith("world://wversion/"):
        vid = ref[len("world://wversion/"):]
        v = c.execute("SELECT * FROM versions WHERE ver_id=?", (vid,)).fetchone()
        if not v:
            raise ValueError("版本引用不存在：%s" % ref)
        paths = [r["path"] for r in c.execute(
            "SELECT path FROM paths WHERE obj_id=? ORDER BY path", (v["obj_id"],))]
        return {"ref": ref, "kind": "version", "ver_id": vid,
                "obj_id": v["obj_id"], "seq": v["seq"],
                "blob_sha256": v["blob_sha256"], "size": v["size"],
                "paths": paths}
    if ref.startswith("world://wfile/"):
        oid = ref[len("world://wfile/"):]
        o = c.execute("SELECT * FROM objects WHERE obj_id=?", (oid,)).fetchone()
        if not o:
            raise ValueError("对象引用不存在：%s" % ref)
        use_seq = int(seq) if seq is not None else o["current_seq"]
        v = c.execute("SELECT * FROM versions WHERE obj_id=? AND seq=?",
                      (oid, use_seq)).fetchone()
        if not v:
            raise ValueError("版本不存在：%s seq=%s" % (oid, use_seq))
        paths = [r["path"] for r in c.execute(
            "SELECT path FROM paths WHERE obj_id=? ORDER BY path", (oid,))]
        return {"ref": ref, "kind": "object", "obj_id": oid,
                "object_kind": o["kind"], "state": o["state"],
                "seq": use_seq, "ver_id": v["ver_id"],
                "blob_sha256": v["blob_sha256"], "size": v["size"],
                "paths": paths}
    raise ValueError("不是世界对象引用：%s" % ref)
