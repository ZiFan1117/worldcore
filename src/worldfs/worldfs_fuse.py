# -*- coding: utf-8 -*-
"""★ worldfs 的 **FUSE 只读挂载**（独立进程/单元 `aios-worldfs-fuse`）。

挂载点 `/aios/worldfs`；内核看到的目录树是 worldfs 命名空间 `/worldfs` 的只读投影。
不依赖第三方 Python FUSE 包：用 ctypes 直接调 libfuse3 的高层 API。

只读：getattr/readdir/open/read/access；写/删/改名等一律由内核按 ro 拒（另 access 也拒）。
"""
import ctypes
import errno
import json
import os
import stat as statmod
import sys
import time

DEFAULT_ROOT = "/var/lib/aios/worldfs"
DEFAULT_MOUNT = "/aios/worldfs"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from worldfs_store import WorldFSError, WorldFS  # noqa: E402


def map_path(fuse_path):
    """★ 挂载内路径 → worldfs 命名空间路径；拒绝 .. / NUL / 相对。"""
    if not isinstance(fuse_path, (str, bytes)):
        raise ValueError("bad path")
    p = fuse_path.decode("utf-8", "strict") if isinstance(fuse_path, bytes) else fuse_path
    if "\x00" in p or ".." in p.split("/"):
        raise ValueError("path traversal")
    if not p.startswith("/"):
        raise ValueError("relative path")
    if p == "/":
        return "/worldfs"
    return "/worldfs" + p.rstrip("/")


def _mtime(st):
    try:
        s = str(st.get("updated_at") or st.get("created_at") or "")
        if s:
            from datetime import datetime
            return datetime.fromisoformat(s).timestamp()
    except Exception:                                              # noqa: BLE001
        pass
    return time.time()


def fill_stat(st, statp):
    """★ 纯函数：worldfs stat 结果 → struct stat 字段（供 FUSE/测试共用）。"""
    is_dir = st.get("kind") == "dir"
    mode = (statmod.S_IFDIR | 0o555) if is_dir else (statmod.S_IFREG | 0o444)
    vals = {
        "st_mode": mode, "st_nlink": 2, "st_size": 0 if is_dir else int(st.get("size") or 0),
        "st_uid": 0, "st_gid": 0, "st_ino": 1, "st_blksize": 4096,
        "st_blocks": 0 if is_dir else (int(st.get("size") or 0) + 511) // 512,
    }
    if statp is not None:
        for k, v in vals.items():
            setattr(statp, k, v)
        for ts in ("st_atim", "st_mtim", "st_ctim"):
            t = statp.__getattribute__(ts)
            t.tv_sec = int(_mtime(st))
            t.tv_nsec = 0
    return vals


# ── ctypes 结构（x86_64 Linux / libfuse3）──
class Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


class Stat(ctypes.Structure):
    _fields_ = [
        ("st_dev", ctypes.c_ulong), ("st_ino", ctypes.c_ulong),
        ("st_nlink", ctypes.c_ulong), ("st_mode", ctypes.c_uint),
        ("st_uid", ctypes.c_uint), ("st_gid", ctypes.c_uint),
        ("__pad0", ctypes.c_int), ("st_rdev", ctypes.c_ulong),
        ("st_size", ctypes.c_long), ("st_blksize", ctypes.c_long),
        ("st_blocks", ctypes.c_long), ("st_atim", Timespec),
        ("st_mtim", Timespec), ("st_ctim", Timespec),
        ("__glibc_reserved", ctypes.c_long * 3),
    ]


FILL_DIR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p,
                            ctypes.POINTER(Stat), ctypes.c_long, ctypes.c_int)
GETATTR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(Stat),
                           ctypes.c_void_p)
READDIR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, FILL_DIR,
                           ctypes.c_long, ctypes.c_void_p, ctypes.c_int)
OPEN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
READ = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t,
                        ctypes.c_long, ctypes.c_void_p)
RELEASE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
ACCESS = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int)


class FuseOperations(ctypes.Structure):
    """libfuse3 `struct fuse_operations` 的字段顺序（未实现的用 void* 占位）。"""
    _fields_ = [
        ("getattr", GETATTR), ("readlink", ctypes.c_void_p),
        ("mknod", ctypes.c_void_p), ("mkdir", ctypes.c_void_p),
        ("unlink", ctypes.c_void_p), ("rmdir", ctypes.c_void_p),
        ("symlink", ctypes.c_void_p), ("rename", ctypes.c_void_p),
        ("link", ctypes.c_void_p), ("chmod", ctypes.c_void_p),
        ("chown", ctypes.c_void_p), ("truncate", ctypes.c_void_p),
        ("open", OPEN), ("read", READ), ("write", ctypes.c_void_p),
        ("statfs", ctypes.c_void_p), ("flush", ctypes.c_void_p),
        ("release", RELEASE), ("fsync", ctypes.c_void_p),
        ("setxattr", ctypes.c_void_p), ("getxattr", ctypes.c_void_p),
        ("listxattr", ctypes.c_void_p), ("removexattr", ctypes.c_void_p),
        ("opendir", OPEN), ("readdir", READDIR), ("releasedir", RELEASE),
        ("fsyncdir", ctypes.c_void_p), ("init", ctypes.c_void_p),
        ("destroy", ctypes.c_void_p), ("access", ACCESS),
        ("create", ctypes.c_void_p), ("lock", ctypes.c_void_p),
        ("utimens", ctypes.c_void_p), ("bmap", ctypes.c_void_p),
        ("ioctl", ctypes.c_void_p), ("poll", ctypes.c_void_p),
        ("write_buf", ctypes.c_void_p), ("read_buf", ctypes.c_void_p),
        ("flock", ctypes.c_void_p), ("fallocate", ctypes.c_void_p),
        ("copy_file_range", ctypes.c_void_p), ("lseek", ctypes.c_void_p),
    ]


class Fuse:
    def __init__(self, root=None, mountpoint=None):
        self.store = WorldFS(root or os.environ.get("AIOS_WORLDFS_ROOT") or DEFAULT_ROOT)
        self.mountpoint = mountpoint or os.environ.get("AIOS_WORLDFS_MOUNT") or DEFAULT_MOUNT
        self.lib = ctypes.CDLL("libfuse3.so.3")
        self.ops = FuseOperations()
        self._keep = []          # ★ 防 ctypes 回调被回收
        self._bind()

    def _bind(self):
        ops = self.ops
        def trap(fn):
            self._keep.append(fn)
            return fn

        @trap
        def cb_getattr(path, statp, fi):
            try:
                st = self.store.stat(map_path(path))
                fill_stat(st, statp[0])
                return 0
            except (WorldFSError, ValueError):
                return -errno.ENOENT

        @trap
        def cb_readdir(path, buf, filler, offset, fi, flags):
            try:
                d = self.store.list(map_path(path))
            except (WorldFSError, ValueError):
                return -errno.ENOENT
            for name, st in ((".", d), ("..", d)):
                s = Stat()
                fill_stat(st, s)
                if filler(buf, name.encode(), ctypes.byref(s), 0, 0) != 0:
                    return 0
            for e in d.get("entries") or []:
                try:
                    s = self.store.stat(e["path"])
                except (WorldFSError, KeyError, ValueError):
                    continue
                sb = Stat()
                fill_stat(s, sb)
                if filler(buf, str(e.get("name") or "").encode(), ctypes.byref(sb), 0, 0) != 0:
                    return 0
            return 0

        @trap
        def cb_open(path, fi):
            try:
                st = self.store.stat(map_path(path))
            except (WorldFSError, ValueError):
                return -errno.ENOENT
            if st.get("kind") == "dir":
                return -errno.EISDIR
            return 0

        @trap
        def cb_read(path, buf, size, offset, fi):
            try:
                st = self.store.stat(map_path(path))
                if st.get("kind") != "file":
                    return -errno.EISDIR
                data = self.store.get_blob(st["blob_sha256"], st["size"]) if st.get("blob_sha256") else b""
                off = int(offset)
                if off >= len(data):
                    return 0
                chunk = data[off:off + int(size)]
                ctypes.memmove(buf, chunk, len(chunk))
                return len(chunk)
            except (WorldFSError, ValueError):
                return -errno.EIO
            except Exception:                                  # noqa: BLE001
                return -errno.EIO

        @trap
        def cb_release(path, fi):
            return 0

        @trap
        def cb_opendir(path, fi):
            try:
                st = self.store.stat(map_path(path))
            except (WorldFSError, ValueError):
                return -errno.ENOENT
            return 0 if st.get("kind") == "dir" else -errno.ENOTDIR

        @trap
        def cb_releasedir(path, fi):
            return 0

        @trap
        def cb_access(path, mask):
            if mask & os.W_OK:
                return -errno.EACCES
            try:
                self.store.stat(map_path(path))
                return 0
            except (WorldFSError, ValueError):
                return -errno.ENOENT

        ops.getattr = GETATTR(cb_getattr)
        ops.open = OPEN(cb_open)
        ops.read = READ(cb_read)
        ops.release = RELEASE(cb_release)
        ops.opendir = OPEN(cb_opendir)
        ops.readdir = READDIR(cb_readdir)
        ops.releasedir = RELEASE(cb_releasedir)
        ops.access = ACCESS(cb_access)
        self._keep.extend([ops.getattr, ops.open, ops.read, ops.release,
                          ops.opendir, ops.readdir, ops.releasedir, ops.access])

    def run(self):
        os.makedirs(self.mountpoint, exist_ok=True)
        argv = [os.path.basename(sys.argv[0]), self.mountpoint,
                "-f", "-o", "ro", "-o", "fsname=worldfs", "-o", "subtype=worldfs"]
        argc = len(argv)
        arr = (ctypes.c_char_p * argc)(*[a.encode() for a in argv])
        self.lib.fuse_main_real.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p),
                                            ctypes.POINTER(FuseOperations), ctypes.c_size_t,
                                            ctypes.c_void_p]
        self.lib.fuse_main_real.restype = ctypes.c_int
        print("[worldfs-fuse] 挂载 %s → worldfs:/worldfs（只读）" % self.mountpoint, flush=True)
        rc = self.lib.fuse_main_real(argc, arr, ctypes.byref(self.ops),
                                     ctypes.sizeof(self.ops), None)
        print("[worldfs-fuse] 退出 rc=%s" % rc, flush=True)
        return int(rc)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--print-map":
        for p in sys.argv[2:]:
            try:
                print(p, "→", map_path(p))
            except ValueError as e:
                print(p, "→ REJECT", e)
        return 0
    return Fuse().run()


if __name__ == "__main__":
    sys.exit(main())
