#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ guard-exec —— **权限的执行层**：用 Landlock 给「子进程」限文件访问。

★ 作者（逐字整理）：「做一个权限……LSM 有接口吗？做个权限，单独做个进程」。
★ 为什么是 Landlock：LSM 是内核框架，用户态不能自己注册 LSM；**Landlock 是用户态能直接用的
  LSM（内核 ≥5.13）**——进程在 exec 子进程前给自己套规则，内核执行。guard（决定）＋ guard-exec（执行）分工。

用法：
  python3 guard_exec.py --policy policy.json --dry-run -- cmd args...   # 只打印计划
  python3 guard_exec.py --policy policy.json --apply   -- cmd args...   # 真套 Landlock 再 exec

策略 JSON：
  {"read_only": ["/usr", "/lib", "/etc"], "read_write": ["/tmp"]}
  （read_only ＝ 可读/可执行；read_write ＝ 额外可写/建/删）
★ 限度：只限文件访问（Landlock 的 ABI 决定能力）；不拦网络、不拦系统调用参数。
"""
import ctypes
import errno
import json
import os
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_POLICY = os.environ.get(
    "AIOS_GUARDEXEC_POLICY", os.path.join(ROOT, "scripts", "release", "guard-exec-policy.json"))

# Landlock 常量（linux/landlock.h）
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38

FS = {
    "EXECUTE": 1 << 0, "WRITE_FILE": 1 << 1, "READ_FILE": 1 << 2, "READ_DIR": 1 << 3,
    "REMOVE_DIR": 1 << 4, "REMOVE_FILE": 1 << 5, "MAKE_CHAR": 1 << 6, "MAKE_DIR": 1 << 7,
    "MAKE_REG": 1 << 8, "MAKE_SOCK": 1 << 9, "MAKE_FIFO": 1 << 10, "MAKE_BLOCK": 1 << 11,
    "MAKE_SYM": 1 << 12, "REFER": 1 << 13, "TRUNCATE": 1 << 14,
}
SYS = {"x86_64": (444, 445, 446), "aarch64": (444, 445, 446)}
SYS_LANDLOCK_CREATE_RULESET, SYS_LANDLOCK_ADD_RULE, SYS_LANDLOCK_RESTRICT_SELF = SYS.get(
    platform.machine(), (444, 445, 446))

try:
    libc = ctypes.CDLL(None, use_errno=True) if os.name == "posix" else None
except Exception:
    libc = None


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def landlock_abi():
    """★ 返回内核支持的 Landlock ABI 版本；不支持则 -1。"""
    if libc is None or not sys.platform.startswith("linux"):
        return -1
    try:
        v = libc.syscall(SYS_LANDLOCK_CREATE_RULESET, None, ctypes.c_size_t(0),
                         ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION))
    except Exception:
        return -1
    return int(v)


def _bits_for_abi(abi):
    """★ 按 ABI 取能用的 handled 位（老内核不认新位）。"""
    names = ["EXECUTE", "WRITE_FILE", "READ_FILE", "READ_DIR", "REMOVE_DIR", "REMOVE_FILE",
             "MAKE_CHAR", "MAKE_DIR", "MAKE_REG", "MAKE_SOCK", "MAKE_FIFO", "MAKE_BLOCK",
             "MAKE_SYM"]
    if abi >= 2:
        names.append("REFER")
    if abi >= 3:
        names.append("TRUNCATE")
    handled = 0
    for n in names:
        handled |= FS[n]
    return handled


def apply_landlock(policy, log=print):
    """★ 在当前进程里套规则（之后 exec 的子进程都受它管）。返回 (ok, why)。"""
    abi = landlock_abi()
    if abi < 1 or libc is None:
        return False, "内核没有 Landlock（或本机不是 Linux）"
    handled = _bits_for_abi(abi)
    attr = _RulesetAttr(handled_access_fs=handled)
    fd = libc.syscall(SYS_LANDLOCK_CREATE_RULESET, ctypes.byref(attr),
                      ctypes.c_size_t(ctypes.sizeof(attr)), ctypes.c_uint32(0))
    if fd < 0:
        e = ctypes.get_errno()
        return False, "landlock_create_ruleset 失败：%s" % os.strerror(e)
    ro = policy.get("read_only") or []
    rw = policy.get("read_write") or []
    read_ok = FS["EXECUTE"] | FS["READ_FILE"] | FS["READ_DIR"]
    write_ok = (read_ok | FS["WRITE_FILE"] | FS["REMOVE_DIR"] | FS["REMOVE_FILE"] |
                FS["MAKE_CHAR"] | FS["MAKE_DIR"] | FS["MAKE_REG"] | FS["MAKE_SOCK"] |
                FS["MAKE_FIFO"] | FS["MAKE_BLOCK"] | FS["MAKE_SYM"])
    if abi >= 2:
        write_ok |= FS["REFER"]
    if abi >= 3:
        write_ok |= FS["TRUNCATE"]
    added = 0
    for path, access in [(p, read_ok) for p in ro] + [(p, write_ok) for p in rw]:
        if not os.path.exists(path):
            log("[guard-exec] 跳过不存在的路径：%s" % path)
            continue
        try:
            pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        except OSError as e:
            return False, "打不开路径 %s：%s" % (path, e)
        pb = _PathBeneathAttr(allowed_access=access, parent_fd=pfd)
        r = libc.syscall(SYS_LANDLOCK_ADD_RULE, ctypes.c_int(fd),
                         ctypes.c_int(LANDLOCK_RULE_PATH_BENEATH), ctypes.byref(pb),
                         ctypes.c_uint32(0))
        os.close(pfd)
        if r < 0:
            e = ctypes.get_errno()
            return False, "landlock_add_rule(%s) 失败：%s" % (path, os.strerror(e))
        added += 1
    pr = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    if pr != 0:
        return False, "prctl(NO_NEW_PRIVS) 失败：%s" % os.strerror(ctypes.get_errno())
    r = libc.syscall(SYS_LANDLOCK_RESTRICT_SELF, ctypes.c_int(fd), ctypes.c_uint32(0))
    if r < 0:
        e = ctypes.get_errno()
        return False, "landlock_restrict_self 失败：%s" % os.strerror(e)
    os.close(fd)
    log("[guard-exec] Landlock ABI=%d 已套：%d 条路径规则" % (abi, added))
    return True, None


def load_policy(path):
    with open(path, encoding="utf-8") as f:
        p = json.load(f)
    out = {"read_only": list(p.get("read_only") or []),
           "read_write": list(p.get("read_write") or [])}
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    policy_path = DEFAULT_POLICY
    dry = False
    apply = False
    cmd = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--policy":
            policy_path = argv[i + 1]; i += 2; continue
        if a == "--dry-run":
            dry = True; i += 1; continue
        if a == "--apply":
            apply = True; i += 1; continue
        if a == "--":
            cmd = argv[i + 1:]; break
        cmd = argv[i:]; break
    if not cmd:
        print("用法：guard_exec.py --policy P (--dry-run|--apply) -- cmd args…", file=sys.stderr)
        return 2
    if not os.path.isfile(policy_path):
        print("拒：没有策略文件 %s" % policy_path, file=sys.stderr)
        return 2
    policy = load_policy(policy_path)
    if dry:
        print(json.dumps({"mode": "dry-run", "policy": policy, "cmd": cmd,
                          "landlock_abi": landlock_abi()}, ensure_ascii=False))
        return 0
    if not apply:
        print("拒：要 --dry-run（只看）或 --apply（真套）", file=sys.stderr)
        return 2
    # fork：子进程先套 Landlock 再 exec；父进程等退出码
    pid = os.fork()
    if pid == 0:
        ok, why = apply_landlock(policy, log=lambda m: print(m, file=sys.stderr, flush=True))
        if not ok:
            print("[guard-exec] 没套上：%s" % why, file=sys.stderr, flush=True)
            os._exit(3)
        try:
            os.execvp(cmd[0], cmd)
        except OSError as e:
            print("[guard-exec] exec 失败：%s" % e, file=sys.stderr, flush=True)
            os._exit(127)
    _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 128 + os.WTERMSIG(status)


if __name__ == "__main__":
    sys.exit(main())
