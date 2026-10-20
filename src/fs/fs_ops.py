# -*- coding: utf-8 -*-
"""★ 语义文件进程的**纯函数**（只读 v1；好测，不连总线）。

★ 借鉴 AI-OS L2「AIOS-FS」的形状（文件＝语义对象、路径是视图、写要版本/证据）——
  我们 v1 只做**只读**：stat / list / hash / read_text；白名单根 + 符号链接逃逸防护 + 秘密文件拒读。
★ 对应动作（在法里）：file.stat / file.list / file.hash / file.read_text / fs.state。
"""
import datetime
import hashlib
import os

DEFAULT_ROOTS = "/var/lib/aios:/root/aios:/etc/aios"
MAX_READ = 32768
MAX_LIST = 500
_SECRET_HINTS = ("secret", "credential", "password", "passwd", "token",
                 "apikey", "api_key", "private", "id_rsa", "id_ed25519",
                 ".key", ".pem", ".p12", ".pfx", ".env")


def roots():
    """★ 白名单根：环境变量里按当前平台的 pathsep 分隔（Linux 是 ":"，Windows 是 ";"；
    避免 Windows 盘符 "C:" 被当成分隔符）。"""
    raw = os.environ.get("AIOS_FS_ROOTS", DEFAULT_ROOTS)
    if os.pathsep in raw:
        sep = os.pathsep
    elif os.name == "nt":
        sep = ";"          # Windows 单路径也按 ";"（盘符里的 ":" 不拆）
    else:
        sep = ":"
    return [r for r in raw.split(sep) if r]


def _under(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def resolve_path(path):
    """★ 绝对路径 → 真实路径 + 命中的白名单根；越界/相对路径一律拒（realpath 防符号链接逃逸）。"""
    if not isinstance(path, str) or not path.strip():
        return None, None, "缺 path"
    if not os.path.isabs(path):
        return None, None, "path 要绝对路径"
    real = os.path.realpath(path)
    for r in roots():
        rr = os.path.realpath(r)
        if _under(real, rr):
            return real, rr, None
    return None, None, "越界：%r 不在白名单根 %s" % (path, roots())


def _is_secret_name(name):
    low = str(name or "").lower()
    if low.startswith("."):
        return True
    return any(h in low for h in _SECRET_HINTS)


def _kind_of(path):
    if os.path.islink(path):
        return "link"
    if os.path.isdir(path):
        return "dir"
    return "file"


def sha256_file(real_path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(real_path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _meta(real, root, path_for_show):
    st = os.stat(real)
    kind = _kind_of(path_for_show)
    m = {"path": path_for_show, "name": os.path.basename(real) or real,
         "size": int(st.st_size), "kind": kind, "root": root,
         "mtime": datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")}
    if kind == "file":
        try:
            m["sha256"] = sha256_file(real)
        except OSError:
            pass
    return m


def stat_file(path):
    real, root, err = resolve_path(path)
    if err:
        return False, err
    try:
        return True, _meta(real, root, path)
    except OSError as e:
        return False, "stat 失败：%s" % e


def hash_file(path):
    real, root, err = resolve_path(path)
    if err:
        return False, err
    if not os.path.isfile(real):
        return False, "不是普通文件：%s" % path
    try:
        return True, {"path": path, "sha256": sha256_file(real),
                      "name": os.path.basename(real), "size": os.path.getsize(real),
                      "root": root, "kind": "file"}
    except OSError as e:
        return False, "hash 失败：%s" % e


def list_dir(path, limit=200):
    real, root, err = resolve_path(path)
    if err:
        return False, err
    if not os.path.isdir(real):
        return False, "不是目录：%s" % path
    try:
        lim = max(1, min(int(limit or 200), MAX_LIST))
    except Exception:
        lim = 200
    items = []
    try:
        with os.scandir(real) as it:
            for e in it:
                if len(items) >= lim:
                    break
                try:
                    st = e.stat(follow_symlinks=False)
                    items.append({"name": e.name, "path": os.path.join(real, e.name),
                                  "kind": "link" if e.is_symlink() else ("dir" if e.is_dir() else "file"),
                                  "size": int(st.st_size)})
                except OSError:
                    continue
    except OSError as e:
        return False, "list 失败：%s" % e
    items.sort(key=lambda x: x["name"])
    return True, {"path": path, "root": root, "count": len(items),
                  "limit": lim, "entries": items}


def read_text(path, max_bytes=MAX_READ):
    real, root, err = resolve_path(path)
    if err:
        return False, err
    if not os.path.isfile(real):
        return False, "不是普通文件：%s" % path
    name = os.path.basename(real)
    if _is_secret_name(name):
        return False, "拒绝读秘密/隐藏文件：%s" % name
    try:
        lim = max(1, min(int(max_bytes or MAX_READ), MAX_READ))
    except Exception:
        lim = MAX_READ
    try:
        total = os.path.getsize(real)
        with open(real, "rb") as f:
            raw = f.read(lim + 1)
        truncated = len(raw) > lim
        blob = raw[:lim]
        text = blob.decode("utf-8", "replace")
        return True, {"path": path, "root": root, "name": name,
                      "total_size": total, "bytes_read": len(blob),
                      "max_bytes": lim, "truncated": truncated, "text": text,
                      "kind": "file"}
    except OSError as e:
        return False, "read 失败：%s" % e


def state():
    return True, {"name": os.environ.get("AIOS_FS_NAME", "fs0"),
                  "state": "running", "roots": roots(),
                  "max_read": MAX_READ, "max_list": MAX_LIST,
                  "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


def dispatch(action, params, name="fs0"):
    """★ 动作 → 纯函数。返回 (ok, body)。"""
    params = params if isinstance(params, dict) else {}
    try:
        if action == "file.stat":
            return stat_file(params.get("path"))
        if action == "file.list":
            return list_dir(params.get("path"), params.get("limit"))
        if action == "file.hash":
            return hash_file(params.get("path"))
        if action == "file.read_text":
            return read_text(params.get("path"), params.get("max_bytes"))
        if action == "fs.state":
            return state()
    except Exception as e:                                  # noqa: BLE001
        return False, "执行异常：%s" % e
    return False, "不认识的动作：%s" % action
