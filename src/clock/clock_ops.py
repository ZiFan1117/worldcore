# -*- coding: utf-8 -*-
"""★ 时间面进程的纯函数（只读；借鉴 AI-OS S28「Constitutional Time Plane」）。

★ 口径：世界时间＝本地钟（带 UTC 偏移）；另给 **单调秒**（time.monotonic，只增不减）
  和 **boot_id**（区分本次开机）。★ 只读：不改系统钟、不回拨。
"""
import datetime
import json
import os
import time

NAME = os.environ.get("AIOS_CLOCK_NAME") or "clock0"


def boot_id():
    """本次开机 id；读不到就空串（不编造）。"""
    try:
        with open("/proc/sys/kernel/random/boot_id", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def timezone_name():
    tz = os.environ.get("TZ") or ""
    if tz:
        return tz
    try:
        with open("/etc/timezone", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def now():
    """当前世界时间（只读）。"""
    dt = datetime.datetime.now().astimezone()
    off = dt.strftime("%z")
    off = (off[:3] + ":" + off[3:]) if len(off) == 5 else off
    return {
        "name": NAME, "state": "running",
        "now": dt.isoformat(timespec="seconds"),
        "utc_offset": off,
        "timezone": timezone_name(),
        "boot_id": boot_id(),
        "monotonic_seconds": int(time.monotonic()),
    }


def state():
    d = now()
    d["source"] = "clock"
    d["pid"] = os.getpid()
    return d


def dispatch(action, params=None):
    """动作 → 纯函数；返回 (ok, body)。"""
    if action == "clock.now":
        return True, now()
    if action == "clock.state":
        return True, state()
    return False, "不认识的动作：%s" % action


def state_path():
    return os.environ.get("AIOS_CLOCK_STATE") or "/var/lib/aios/clock/state.json"


def write_state(path=None):
    """★ 把时钟权威快照写给本体（ledger 时间统一用）；原子写，失败不抛。"""
    path = path or state_path()
    d = now()
    d["written_at"] = d["now"]
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except OSError:
        return False
