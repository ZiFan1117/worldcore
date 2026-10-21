# -*- coding: utf-8 -*-
"""★ worldfs 的存储核心：内容寻址 blob + 不可变版本 + 路径指针。

★ 作者令（2026-10-21）：「这个文件系统不记帐，都在本体里面」。
所以这里**没有本地账**：没有 txns 表、没有 created_by/intent/updated_by 等审计列；
actor/intent/时间/结果只在 world/ask、world/exec/result 与本体 ledger 里。
存储只保留技术索引（内容/版本/路径）。

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

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS objects (
      obj_id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      state TEXT NOT NULL,
      current_seq INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS versions (
      ver_id TEXT PRIMARY KEY,
      obj_id TEXT NOT NULL,
      seq INTEGER NOT NULL,
      blob_sha256 TEXT NOT NULL,
      size INTEGER NOT NULL,
      UNIQUE(obj_id, seq)
    );
    CREATE TABLE IF NOT EXISTS paths (
      path TEXT PRIMARY KEY,
      obj_id TEXT NOT NULL,
      seq INTEGER NOT NULL,
      kind TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_versions_obj ON versions(obj_id, seq);
    CREATE INDEX IF NOT EXISTS idx_paths_obj ON paths(obj_id);
    """

    def _init_db(self):
        fresh = not os.path.exists(self.db_path)
        with self._conn() as c:
            if fresh:
                c.executescript(self._SCHEMA)
                c.execute("PRAGMA user_version=2")
                return
            cols = {r["name"] for r in c.execute("PRAGMA table_info(versions)")}
            has_txns = c.execute("SELECT 1 FROM sqlite_master"
                                 " WHERE type='table' AND name='txns'").fetchone()
            if "created_by" not in cols and not has_txns:
                c.executescript(self._SCHEMA)
                c.execute("PRAGMA user_version=2")
                return
            # v1 → v2：只搬技术列，不搬任何账/审计列；txns 直接删
            c.executescript("""
            CREATE TABLE objects_v2 (
              obj_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
              state TEXT NOT NULL, current_seq INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE versions_v2 (
              ver_id TEXT PRIMARY KEY, obj_id TEXT NOT NULL, seq INTEGER NOT NULL,
              blob_sha256 TEXT NOT NULL, size INTEGER NOT NULL, UNIQUE(obj_id, seq));
            CREATE TABLE paths_v2 (
              path TEXT PRIMARY KEY, obj_id TEXT NOT NULL, seq INTEGER NOT NULL,
              kind TEXT NOT NULL);
            INSERT INTO objects_v2(obj_id,kind,state,current_seq)
              SELECT obj_id,kind,state,current_seq FROM objects;
            INSERT INTO versions_v2(ver_id,obj_id,seq,blob_sha256,size)
              SELECT ver_id,obj_id,seq,blob_sha256,size FROM versions;
            INSERT INTO paths_v2(path,obj_id,seq,kind)
              SELECT path,obj_id,seq,kind FROM paths;
            DROP TABLE objects;
            DROP TABLE versions;
            DROP TABLE paths;
            DROP TABLE IF EXISTS txns;
            ALTER TABLE objects_v2 RENAME TO objects;
            ALTER TABLE versions_v2 RENAME TO versions;
            ALTER TABLE paths_v2 RENAME TO paths;
            CREATE INDEX IF NOT EXISTS idx_versions_obj ON versions(obj_id, seq);
            CREATE INDEX IF NOT EXISTS idx_paths_obj ON paths(obj_id);
            """)
            c.execute("PRAGMA user_version=2")
            print("[worldfs] 本地账已撤：v1→v2（txns 删除，技术数据保留）")

    def _ensure_root(self):
        with self._conn() as c:
            row = c.execute("SELECT * FROM paths WHERE path=?", (NS_ROOT,)).fetchone()
            if row:
                return
            obj, ver = _uid("wobj_"), _uid("wver_")
            c.execute("INSERT INTO objects(obj_id,kind,state,current_seq)"
                      " VALUES(?,?,?,?)", (obj, "dir", "active", 1))
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size)"
                      " VALUES(?,?,?,?,?)", (ver, obj, 1, "", 0))
            c.execute("INSERT INTO paths(path,obj_id,seq,kind)"
                      " VALUES(?,?,?,?)", (NS_ROOT, obj, 1, "dir"))

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
    # ★ 没有 _txn：本地不记账。actor/intent/结果只在本体 ledger 里。

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
                    "size": v["size"], "obj_state": r["obj_state"]}

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
                "text": blob.decode("utf-8", "replace")}

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
                        "obj_id": r["obj_id"], "seq": r["seq"], "kind": r["kind"]} for r in rows]
            return {"path": path, "kind": "dir", "count": len(entries), "limit": lim,
                    "entries": entries}

    def versions(self, path):
        st = self.stat(path)
        with self._conn() as c:
            rows = c.execute("SELECT * FROM versions WHERE obj_id=? ORDER BY seq",
                             (st["obj_id"],)).fetchall()
            return {"path": path, "obj_id": st["obj_id"],
                    "versions": [{"ver_id": r["ver_id"], "seq": r["seq"],
                                  "blob_sha256": r["blob_sha256"],
                                  "size": r["size"]} for r in rows]}

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
                c.execute("INSERT INTO objects(obj_id,kind,state,current_seq)"
                          " VALUES(?,?,?,?)", (obj, "file", "active", seq))
            ver = _uid("wver_")
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size)"
                      " VALUES(?,?,?,?,?)", (ver, obj, seq, sha, len(data)))
            c.execute("INSERT OR REPLACE INTO paths(path,obj_id,seq,kind)"
                      " VALUES(?,?,?,?)", (path, obj, seq, "file"))
            c.execute("UPDATE objects SET current_seq=?, state='active' WHERE obj_id=?", (seq, obj))
            return {"path": path, "obj_id": obj, "seq": seq, "ver_id": ver,
                    "blob_sha256": sha, "size": len(data), "before_seq": before,
                    "dedup": dedup}

    def mkdir(self, path, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（建目录必须说明意图）")
        with self._conn() as c:
            self._parent_dir(c, path)
            if c.execute("SELECT 1 FROM paths WHERE path=?", (path,)).fetchone():
                raise WorldFSError("已存在：%s" % path)
            obj, ver = _uid("wobj_"), _uid("wver_")
            c.execute("INSERT INTO objects(obj_id,kind,state,current_seq)"
                      " VALUES(?,?,?,?)", (obj, "dir", "active", 1))
            c.execute("INSERT INTO versions(ver_id,obj_id,seq,blob_sha256,size)"
                      " VALUES(?,?,?,?,?)", (ver, obj, 1, "", 0))
            c.execute("INSERT INTO paths(path,obj_id,seq,kind)"
                      " VALUES(?,?,?,?)", (path, obj, 1, "dir"))
            return {"path": path, "obj_id": obj, "seq": 1, "kind": "dir"}

    def remove(self, path, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（删除必须说明意图）")
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
            return {"path": path, "obj_id": r["obj_id"], "removed_seq": before, "kind": r["kind"]}

    def rename(self, old_path, new_path, actor, intent):
        """★ 改名/移动：只移动路径指针，对象身份不变；目录连同子树路径一起移动。"""
        old_path = validate_path(old_path)
        new_path = validate_path(new_path)
        if old_path == new_path:
            raise WorldFSError("新旧路径相同")
        if new_path.startswith(old_path.rstrip("/") + "/"):
            raise WorldFSError("不能把目录移到它自己里面")
        if not intent:
            raise WorldFSError("缺 intent（改名/移动必须说明意图）")
        with self._conn() as c:
            r = self._row(c, old_path)
            self._parent_dir(c, new_path)
            if c.execute("SELECT 1 FROM paths WHERE path=?", (new_path,)).fetchone():
                raise WorldFSError("目标已存在：%s" % new_path)
            rows = c.execute("SELECT * FROM paths ORDER BY length(path)").fetchall()
            moved = []
            if r["kind"] == "dir":
                pref = old_path.rstrip("/") + "/"
                for x in rows:
                    if x["path"] == old_path or x["path"].startswith(pref):
                        moved.append(x)
            else:
                moved = [r]
            targets = []
            for x in moved:
                suffix = x["path"][len(old_path):]
                targets.append((x, new_path + suffix))
            for _x, tgt in targets:
                if c.execute("SELECT 1 FROM paths WHERE path=?", (tgt,)).fetchone():
                    raise WorldFSError("目标子树有冲突：%s" % tgt)
            for x, tgt in targets:
                c.execute("UPDATE paths SET path=? WHERE path=?", (tgt, x["path"]))
            return {"old_path": old_path, "path": new_path, "obj_id": r["obj_id"],
                    "seq": r["seq"], "kind": r["kind"], "moved": len(targets)}

    def restore(self, path, seq, actor, intent):
        path = validate_path(path)
        if not intent:
            raise WorldFSError("缺 intent（回滚必须说明意图）")
        try:
            seq = int(seq)
        except (TypeError, ValueError):
            raise WorldFSError("seq 必须是整数")
        with self._conn() as c:
            r = self._row(c, path)
            v = self._version(c, r["obj_id"], seq)
            if v["blob_sha256"]:
                self.get_blob(v["blob_sha256"], v["size"])       # 回滚前验 blob 完好
            before = r["seq"]
            c.execute("UPDATE paths SET seq=? WHERE path=?", (seq, path))
            return {"path": path, "obj_id": r["obj_id"], "seq": seq,
                    "before_seq": before, "ver_id": v["ver_id"]}
