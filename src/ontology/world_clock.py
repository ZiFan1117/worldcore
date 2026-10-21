# -*- coding: utf-8 -*-
"""★ 本体 ledger 的统一时间源：优先读 clock 进程写的权威快照。

clock 进程每秒写 `/var/lib/aios/clock/state.json`；本体内 ledger/事件用它当 `at`。
读不到（启动早期/时钟未起）才回退系统时间；不在本体里另造时间权威。
"""
import datetime
import json
import os

STATE_PATH = os.environ.get("AIOS_CLOCK_STATE") or "/var/lib/aios/clock/state.json"


def state(path=None):
    p = path or os.environ.get("AIOS_CLOCK_STATE") or STATE_PATH
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and d.get("now"):
            datetime.datetime.fromisoformat(str(d["now"]))
            return d
    except (OSError, ValueError, TypeError):
        pass
    return None


def now(path=None):
    d = state(path)
    if d:
        return str(d["now"])
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="microseconds")


def boot_id(path=None):
    d = state(path)
    if d and d.get("boot_id"):
        return str(d["boot_id"])
    try:
        with open("/proc/sys/kernel/random/boot_id", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""
