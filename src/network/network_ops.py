# -*- coding: utf-8 -*-
"""★ 网络面进程的纯函数（只读；借鉴 AI-OS L8 Network/Hardware/Devices）。

★ 读什么：/sys/class/net/<if>/（operstate/address/mtu/statistics）＋ /proc/net/dev 计数器。
★ 不做什么：不配网、不改路由、不起外进程；只把接口报成世界对象。
"""
import datetime
import os

DEFAULT_SYS = "/sys/class/net"
DEFAULT_DEV = "/proc/net/dev"
NAME = os.environ.get("AIOS_NETWORK_NAME") or "network0"


def sys_dir():
    return os.environ.get("AIOS_NET_SYS") or DEFAULT_SYS


def dev_file():
    return os.environ.get("AIOS_NET_DEV") or DEFAULT_DEV


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return default


def _int(path):
    s = _read(path, "")
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def _kind(name):
    if name == "lo":
        return "lo"
    if name.startswith("wl") or name.startswith("wlan"):
        return "wifi"
    if name.startswith(("eth", "en", "eno", "ens", "enp")):
        return "eth"
    if name.startswith(("veth", "docker", "br-", "virbr")):
        return "veth"
    return "other"


def dev_counters():
    """★ /proc/net/dev：接口 → {rx_bytes,tx_bytes,rx_packets,tx_packets,rx_errors,tx_errors}。"""
    out = {}
    for line in _read(dev_file(), "").splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        parts = rest.split()
        if not name or name == "Inter-|" or len(parts) < 16:
            continue
        try:
            nums = [int(x) for x in parts[:16]]
        except ValueError:
            continue
        out[name] = {"rx_bytes": nums[0], "rx_packets": nums[1], "rx_errors": nums[2],
                     "tx_bytes": nums[8], "tx_packets": nums[9], "tx_errors": nums[10]}
    return out


def interfaces():
    """★ 列接口（只读）。读不到 /sys 就返回空（不编造）。"""
    d = sys_dir()
    if not os.path.isdir(d):
        return True, {"sys": d, "count": 0, "up": 0, "interfaces": [],
                      "note": "接口目录不存在（空列表）"}
    counters = dev_counters()
    items = []
    for name in sorted(os.listdir(d)):
        base = os.path.join(d, name)
        if not os.path.isdir(base):
            continue
        oper = _read(os.path.join(base, "operstate"), "unknown").lower()
        state = "up" if oper == "up" else ("down" if oper == "down" else "unknown")
        e = {"name": name, "kind": _kind(name), "state": state,
             "mac": _read(os.path.join(base, "address"), ""),
             "mtu": _int(os.path.join(base, "mtu")),
             "ifindex": _int(os.path.join(base, "ifindex"))}
        c = counters.get(name) or {}
        for k, v in c.items():
            e[k] = v
        items.append(e)
    up = sum(1 for i in items if i.get("state") == "up")
    return True, {"sys": d, "dev": dev_file(), "count": len(items), "up": up,
                  "interfaces": items}


def state():
    ok, d = interfaces()
    ifaces = d.get("interfaces") or []
    total_rx = sum(int(i.get("rx_bytes") or 0) for i in ifaces)
    total_tx = sum(int(i.get("tx_bytes") or 0) for i in ifaces)
    return True, {"name": NAME, "state": "running", "interfaces": len(ifaces),
                  "up": d.get("up", 0), "rx_bytes": total_rx, "tx_bytes": total_tx,
                  "collected_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


def dispatch(action, params=None):
    if action == "network.list":
        return interfaces()
    if action == "network.state":
        return state()
    return False, "不认识的动作：%s" % action
