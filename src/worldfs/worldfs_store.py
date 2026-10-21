# -*- coding: utf-8 -*-
"""★ worldfs 的存储核心（P1）：内容寻址 blob + 不可变版本 + 路径指针 + 事务。

不变量：
  · 内容不可变：版本一旦写就不改；同内容 = 同 blob（sha256）；
  · 路径是视图：paths 表把路径指向 (obj_id, seq)，对象身份与路径解耦；
  · 写先落 blob 再提交 DB；读时校验 sha256/size（坏 blob 不返回内容）；
  · 只写 root 下：blobs/sha256/、worldfs.db、tmp/。

用法：
  w = WorldFS(root)          # root 默认 /var/lib/aios/worldfs
  w.write("/worldfs/a.txt", "...", actor="world://user/zhang", intent="...")
  w.read("/worldfs/a.txt")
"""
import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DEFAULT_ROOT = "/var/lib/aios/worldfs"
NS_ROOT = "/worldfs"
MAX_TEXT = 1024 * 1024          # P1 文本上限 1MB
MAX_SEGMENT = 128
MAX_DEPTH = 32


class WorldFSError(Exception):
    """worldfs 的业务错误（路径/越权/坏 blob/不存在…）。"""


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="microseconds")


def _uid(prefix):
    return prefix + uuid.uuid4().hex


def validate_path(path, allow_root=False):
    """★ 命名空间校验：/worldfs 下的绝对路径；返回规范化路径或抛 WorldFSError。"""
    if not isinstance(path, str) or not path:
        raise WorldFSError("缺 path")
    if any(ord(c) < 32 or ord(c) == 0 for c in path):
        raise WorldFSError("path 含控制字符")
    if not path.startswith(NS_ROOT):
        raise WorldFSError("path 必须以 %s 开头" % NS_ROOT)
    if path == NS_ROOT:
        if allow_root:
            return path
        raise WorldFSError("根目录 /worldfs 不是文件")
    rest = path[len(NS_ROOT):]
    if not rest.startswith("/"):
        raise WorldFSError("path 必须是 %s/... 形式" % NS_ROOT)
    body = rest[1:]
    if body.endswith("/"):
        raise WorldFSError("path 不能以 / 结尾")
    segs = body.split("/")
    if len(segs) > MAX_DEPTH:
        raise WorldFSError("path 段数超过 %d" % MAX_DEPTH)
    for s in segs:
        if s in ("", ".", ".."):
            raise WorldFSError("path 段非法：%r" % s)
        if len(s) > MAX_SEGMENT:
            raise WorldFSError("path 段过长（>%d）" % MAX_SEGMENT)
    return path


def parent_of(path):
    p = path.rsplit("/", 1)[0]
    return p or NS_ROOT


class WorldFS:
    def __init__(self, root=None):
        self.root = root or os.environ.get("AIOS_WORLDFS_ROOT") or DEFAULT_ROOT
        self.blob_root = os.path.join(self.root, "blobs", "sha256")
        self.tmp_root = os.path.join(self.root, "tmp")
        self.db_path = os.path.join(self.root, "worldfs.db")
        os.makedirs(self.blob_root, exist_ok=True)
        os.makedirs(self.tmp_root, exist_ok=True)
        self._init_db()
        self._ensure_root()

    # ── sqlite ──
    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS objects (
              obj_id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              state TEXT NOT NULL,
              current_seq INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS versions (
              ver_id TEXT PRIMARY KEY,
              obj_id TEXT NOT NULL,
              seq INTEGER NOT NULL,
              blob_sha256 TEXT NOT NULL,
              size INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              intent TEXT,
              UNIQUE(obj_id, seq)
            );
            CREATE TABLE IF NOT EXISTS paths (
              path TEXT PRIMARY KEY,
              obj_id TEXT NOT NULL,
              seq INTEGER NOT NULL,
              kind TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              updated_by TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS txns (
              txn_id TEXT PRIMARY KEY,
              at TEXT NOT NULL,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              path TEXT,
              obj_id TEXT,
              seq INTEGER,
              before_seq INTEGER,
              intent TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_versions_obj ON versions(obj_id, seq);
            CREATE INDEX IF NOT EXISTS idx_paths_obj ON paths(obj_id);
            """)

    def _ensure_root(self):
        with self._conn() as c:
            row = c.execute("SELECT * FROM paths WHERE path=?", (NS_ROOT,)).fetchone()
            if row:
                return
            now, obj = _now(), _uid("wobj_")
            ver = _uid("wver_")
            c.execute("INSERT INTO objects(obj_id,kind,created_at,created_by,state,current_seq)"
                      " VALUES(?,?,?,?,?,?)", (obj, "dir", now, "world://worldfs", "active", 1))
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size,created_at,created_by,intent)"
                      " VALUES(?,?,?,?,?,?,?,?)", (ver, obj, 1, "", 0, now, "world://worldfs", "init"))
            c.execute("INSERT INTO paths(path,obj_id,seq,kind,updated_at,updated_by)"
                      " VALUES(?,?,?,?,?,?)", (NS_ROOT, obj, 1, "dir", now, "world://worldfs"))
            self._txn(c, "init", NS_ROOT, obj, 1, 0, "ensure root")

    # ── blob ──
    def _blob_path(self, sha):
        return os.path.join(self.blob_root, sha[:2], sha)

    def put_blob(self, data):
        sha = hashlib.sha256(data).hexdigest()
        dst = self._blob_path(sha)
        if os.path.isfile(dst):
            return sha
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = os.path.join(self.tmp_root, uuid.uuid4().hex)
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dst)
        try:
            os.chmod(dst, 0o444)          # 内容不可变：只读文件
        except OSError:
            pass
        return sha

    def get_blob(self, sha, size):
        if not sha:
            return b""
        p = self._blob_path(sha)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError as e:
            raise WorldFSError("blob 读不到：%s" % e)
        if len(data) != int(size):
            raise WorldFSError("blob 大小不符（%d ≠ %d）" % (len(data), size))
        if hashlib.sha256(data).hexdigest() != sha:
            raise WorldFSError("blob sha256 不符（坏块）")
        return data

    # ── helpers ──
    def _txn(self, c, action, path, obj_id, seq, before_seq, intent):
        c.execute("INSERT INTO txns(txn_id,at,actor,action,path,obj_id,seq,before_seq,intent)"
                  " VALUES(?,?,?,?,?,?,?,?,?)",
                  (_uid("wtxn_"), _now(), "world://worldfs", action, path,
                   obj_id, seq, before_seq, intent))

    def _row(self, c, path):
        r = c.execute("SELECT p.*, o.state AS obj_state FROM paths p JOIN objects o"
                      " ON o.obj_id=p.obj_id WHERE p.path=?", (path,)).fetchone()
        if not r:
            raise WorldFSError("不存在：%s" % path)
        return r

    def _version(self, c, obj_id, seq):
        r = c.execute("SELECT * FROM versions WHERE obj_id=? AND seq=?", (obj_id, seq)).fetchone()
        if not r:
            raise WorldFSError("版本不存在：%s seq=%s" % (obj_id, seq))
        return r

    def _parent_dir(self, c, path):
        if path == NS_ROOT:
            raise WorldFSError("根目录不能写/删")
        par = parent_of(path)
        if par != NS_ROOT:
            r = c.execute("SELECT kind FROM paths WHERE path=?", (par,)).fetchone()
            if not r:
                raise WorldFSError("父目录不存在：%s" % par)
            if r["kind"] != "dir":
                raise WorldFSError("父路径不是目录：%s" % par)
        return par

    # ── read API ──
    def stat(self, path):
        path = validate_path(path, allow_root=True)
        with self._conn() as c:
            r = self._row(c, path)
            v = self._version(c, r["obj_id"], r["seq"])
            return {"path": path, "obj_id": r["obj_id"], "kind": r["kind"], "seq": r["seq"],
                    "ver_id": v["ver_id"], "blob_sha256": v["blob_sha256"],
                    "size": v["size"], "created_at": v["created_at"],
                    "created_by": v["created_by"], "intent": v["intent"],
                    "updated_at": r["updated_at"], "updated_by": r["updated_by"],
                    "obj_state": r["obj_state"]}

    def read(self, path, max_bytes=65536):
        st = self.stat(path)
        if st["kind"] != "file":
            raise WorldFSError("不是文件：%s" % path)
        data = self.get_blob(st["blob_sha256"], st["size"])
        try:
            lim = max(1, min(int(max_bytes or 65536), MAX_TEXT))
        except (TypeError, ValueError):
            lim = 65536
        blob = data[:lim]
        return {"path": path, "obj_id": st["obj_id"], "seq": st["seq"],
                "ver_id": st["ver_id"], "blob_sha256": st["blob_sha256"],
                "total_size": st["size"], "bytes_read": len(blob),
                "truncated": len(data) > lim,
                "text": blob.decode("utf-8", "replace"),
                "created_at": st["created_at"], "created_by": st["created_by"],
                "intent": st["intent"]}

    def list(self, path, limit=200):
        path = validate_path(path, allow_root=True)
        try:
            lim = max(1, min(int(limit or 200), 500))
        except (TypeError, ValueError):
            lim = 200
        with self._conn() as c:
            st = self._row(c, path)
            if st["kind"] != "dir":
                raise WorldFSError("不是目录：%s" % path)
            pref = path.rstrip("/") + "/"
            # ★ 用 Python 过滤「直接子项」，避免名字里的 %/_ 干扰 LIKE
            rows = c.execute("SELECT * FROM paths WHERE path LIKE ? ORDER BY path",
                             (pref + "%",)).fetchall()
            rows = [r for r in rows if "/" not in r["path"][len(pref):]][:lim]
            entries = [{"name": r["path"].rsplit("/", 1)[-1], "path": r["path"],
                        "obj_id": r["obj_id"], "seq": r["seq"], "kind": r["kind"],
                        "updated_at": r["updated_at"]} for r in rows]
            return {"path": path, "kind": "dir", "count": len(entries), "limit": lim,
                    "entries": entries}

    def versions(self, path):
        st = self.stat(path)
        with self._conn() as c:
            rows = c.execute("SELECT * FROM versions WHERE obj_id=? ORDER BY seq",
                             (st["obj_id"],)).fetchall()
            return {"path": path, "obj_id": st["obj_id"],
                    "versions": [{"ver_id": r["ver_id"], "seq": r["seq"],
                                  "blob_sha256": r["blob_sha256"], "size": r["size"],
                                  "created_at": r["created_at"], "created_by": r["created_by"],
                                  "intent": r["intent"]} for r in rows]}

    def state(self):
        with self._conn() as c:
            objs = c.execute("SELECT COUNT(*) AS n FROM objects WHERE state='active'").fetchone()["n"]
            paths = c.execute("SELECT COUNT(*) AS n FROM paths").fetchone()["n"]
            vers = c.execute("SELECT COUNT(*) AS n FROM versions").fetchone()["n"]
        blobs = 0
        total = 0
        for dp, _dn, fn in os.walk(self.blob_root):
            for f in fn:
                blobs += 1
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        return {"root": self.root, "objects": objs, "paths": paths, "versions": vers,
                "blobs": blobs, "blob_bytes": total}

    # ── write API ──
    def write(self, path, text, actor, intent, base_seq=None):
        path = validate_path(path)
        if not isinstance(text, str):
            raise WorldFSError("text 要是字符串")
        if not intent:
            raise WorldFSError("缺 intent（写必须说明意图）")
        data = text.encode("utf-8")
        if len(data) > MAX_TEXT:
            raise WorldFSError("文本超过 %d 字节" % MAX_TEXT)
        _sha = hashlib.sha256(data).hexdigest()
        dedup = os.path.isfile(self._blob_path(_sha))
        sha = self.put_blob(data)
        now = _now()
        with self._conn() as c:
            self._parent_dir(c, path)
            old = c.execute("SELECT * FROM paths WHERE path=?", (path,)).fetchone()
            before = old["seq"] if old else 0
            if old:
                if old["kind"] != "file":
                    raise WorldFSError("目标是目录，不能写文件：%s" % path)
                if base_seq is not None and int(base_seq) != int(before):
                    raise WorldFSError("版本冲突：base_seq=%r 当前=%r" % (base_seq, before))
                obj = old["obj_id"]
                seq = c.execute("SELECT COALESCE(MAX(seq),0)+1 AS n FROM versions"
                                " WHERE obj_id=?", (obj,)).fetchone()["n"]
            else:
                obj, seq = _uid("wobj_"), 1
                c.execute("INSERT INTO objects(obj_id,kind,created_at,created_by,state,current_seq)"
                          " VALUES(?,?,?,?,?,?)", (obj, "file", now, actor, "active", seq))
            ver = _uid("wver_")
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size,created_at,created_by,intent)"
                      " VALUES(?,?,?,?,?,?,?,?)", (ver, obj, seq, sha, len(data), now, actor, intent))
            c.execute("INSERT OR REPLACE INTO paths(path,obj_id,seq,kind,updated_at,updated_by)"
                      " VALUES(?,?,?,?,?,?)", (path, obj, seq, "file", now, actor))
            c.execute("UPDATE objects SET current_seq=?, state='active' WHERE obj_id=?", (seq, obj))
            self._txn(c, "write", path, obj, seq, before, intent)
            return {"path": path, "obj_id": obj, "seq": seq, "ver_id": ver,
                    "blob_sha256": sha, "size": len(data), "before_seq": before,
                    "dedup": dedup}

    def mkdir(self, path, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（建目录必须说明意图）")
        now = _now()
        with self._conn() as c:
            self._parent_dir(c, path)
            if c.execute("SELECT 1 FROM paths WHERE path=?", (path,)).fetchone():
                raise WorldFSError("已存在：%s" % path)
            obj, ver = _uid("wobj_"), _uid("wver_")
            c.execute("INSERT INTO objects(obj_id,kind,created_at,created_by,state,current_seq)"
                      " VALUES(?,?,?,?,?,?)", (obj, "dir", now, actor, "active", 1))
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size,created_at,created_by,intent)"
                      " VALUES(?,?,?,?,?,?,?,?)", (ver, obj, 1, "", 0, now, actor, intent))
            c.execute("INSERT INTO paths(path,obj_id,seq,kind,updated_at,updated_by)"
                      " VALUES(?,?,?,?,?,?)", (path, obj, 1, "dir", now, actor))
            self._txn(c, "mkdir", path, obj, 1, 0, intent)
            return {"path": path, "obj_id": obj, "seq": 1, "kind": "dir"}

    def remove(self, path, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（删除必须说明意图）")
        now = _now()
        with self._conn() as c:
            r = self._row(c, path)
            if r["kind"] == "dir":
                pref = path.rstrip("/") + "/"
                all_paths = [x["path"] for x in c.execute("SELECT path FROM paths").fetchall()]
                if any(pth.startswith(pref) for pth in all_paths):
                    raise WorldFSError("目录非空，P1 不递归删：%s" % path)
            before = r["seq"]
            c.execute("DELETE FROM paths WHERE path=?", (path,))
            c.execute("UPDATE objects SET state='retired' WHERE obj_id=?", (r["obj_id"],))
            self._txn(c, "remove", path, r["obj_id"], before, before, intent)
            return {"path": path, "obj_id": r["obj_id"], "removed_seq": before, "kind": r["kind"]}

    def restore(self, path, seq, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（回滚必须说明意图）")
        try:
            seq = int(seq)
        except (TypeError, ValueError):
            raise WorldFSError("seq 必须是整数")
        now = _now()
        with self._conn() as c:
            r = self._row(c, path)
            v = self._version(c, r["obj_id"], seq)
            if v["blob_sha256"]:
                self.get_blob(v["blob_sha256"], v["size"])       # 回滚前验 blob 完好
            before = r["seq"]
            c.execute("UPDATE paths SET seq=?, updated_at=?, updated_by=? WHERE path=?",
                      (seq, now, actor, path))
            self._txn(c, "restore", path, r["obj_id"], seq, before, intent)
            return {"path": path, "obj_id": r["obj_id"], "seq": seq,
                    "before_seq": before, "ver_id": v["ver_id"]}
