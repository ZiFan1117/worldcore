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


# ── deep read-only：地址/路由/DNS/连接（仍然只读，不出向）──
import ipaddress
import socket as _socket
import struct as _struct


def _net_path(name, default):
    return os.environ.get(name) or default


def _ipv4(hex_le):
    try:
        return _socket.inet_ntoa(_struct.pack("<I", int(hex_le, 16)))
    except (TypeError, ValueError, OSError):
        return None


def _ipv6(hex32):
    try:
        return _socket.inet_ntop(_socket.AF_INET6, bytes.fromhex(hex32))
    except (TypeError, ValueError, OSError):
        return None


def addresses():
    items = []
    for line in _read(_net_path("AIOS_NET_IF6", "/proc/net/if_inet6"), "").splitlines():
        f = line.split()
        if len(f) < 6:
            continue
        ip = _ipv6(f[0])
        if not ip:
            continue
        try:
            prefix, scope = int(f[2], 16), int(f[3], 16)
        except ValueError:
            prefix, scope = None, None
        items.append({"family": "ipv6", "address": ip, "prefix": prefix,
                      "scope": scope, "interface": f[5]})
    cur = None
    exact = False
    for line in _read(_net_path("AIOS_NET_FIB", "/proc/net/fib_trie"), "").splitlines():
        s = line.strip()
        if "|--" in s:
            tok = s.split("|--", 1)[1].strip()
            if tok:
                exact = "/" not in tok
                cur = tok.split("/", 1)[0]
            continue
        if cur and exact and s.startswith("/32 host LOCAL"):
            try:
                ipaddress.IPv4Address(cur)
            except ValueError:
                continue
            items.append({"family": "ipv4", "address": cur, "prefix": 32,
                          "scope": "host", "interface": None})
            cur = None
    return True, {"count": len(items), "addresses": items}


def routes():
    items = []
    for i, line in enumerate(_read(_net_path("AIOS_NET_ROUTE", "/proc/net/route"), "").splitlines()):
        f = line.split()
        if i == 0 or len(f) < 11:
            continue
        dst, gw = _ipv4(f[1]), _ipv4(f[2])
        if not dst:
            continue
        try:
            flags = int(f[3], 16)
            mask = _ipv4(f[7])
            metric = int(f[6])
        except (ValueError, TypeError):
            flags, mask, metric = None, None, None
        items.append({"family": "ipv4", "destination": dst, "gateway": gw,
                      "mask": mask, "interface": f[0], "metric": metric,
                      "flags": flags})
    for line in _read(_net_path("AIOS_NET_ROUTE6", "/proc/net/ipv6_route"), "").splitlines():
        f = line.split()
        if len(f) < 10:
            continue
        dst = _ipv6(f[0])
        if not dst:
            continue
        try:
            plen, metric = int(f[1], 16), int(f[5], 16)
        except ValueError:
            plen, metric = None, None
        items.append({"family": "ipv6", "destination": dst, "prefix": plen,
                      "interface": f[9], "metric": metric,
                      "gateway": _ipv6(f[4])})
    return True, {"count": len(items), "routes": items}


def dns():
    p = _net_path("AIOS_NET_RESOLV", "/etc/resolv.conf")
    names, search, options = [], [], []
    for line in _read(p, "").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        parts = line.split()
        if parts[0] == "nameserver" and len(parts) > 1:
            names.append(parts[1])
        elif parts[0] == "search":
            search.extend(parts[1:])
        elif parts[0] == "options":
            options.extend(parts[1:])
    return True, {"count": len(names), "nameservers": names,
                  "search": search, "options": options, "source": p}


_TCP_STATE = {"01": "ESTABLISHED", "02": "SYN_SENT", "03": "SYN_RECV",
              "04": "FIN_WAIT1", "05": "FIN_WAIT2", "06": "TIME_WAIT",
              "07": "CLOSE", "08": "CLOSE_WAIT", "09": "LAST_ACK",
              "0A": "LISTEN", "0B": "CLOSING"}


def _conn_file(path, proto, family):
    rows = []
    for line in _read(path, "").splitlines()[1:]:
        f = line.split()
        if len(f) < 4:
            continue
        try:
            l_ip, l_port = f[1].split(":")
            r_ip, r_port = f[2].split(":")
            lp, rp = int(l_port, 16), int(r_port, 16)
        except (ValueError, IndexError):
            continue
        conv = _ipv4 if family == "ipv4" else _ipv6
        rows.append({"proto": proto, "family": family,
                     "local": "%s:%d" % (conv(l_ip), lp),
                     "remote": "%s:%d" % (conv(r_ip), rp),
                     "state": _TCP_STATE.get(str(f[3]).upper(), str(f[3])),
                     "uid": int(f[7]) if len(f) > 7 and f[7].isdigit() else None})
    return rows


def connections():
    specs = (("tcp", "ipv4", "AIOS_NET_TCP", "/proc/net/tcp"),
             ("tcp6", "ipv6", "AIOS_NET_TCP6", "/proc/net/tcp6"),
             ("udp", "ipv4", "AIOS_NET_UDP", "/proc/net/udp"),
             ("udp6", "ipv6", "AIOS_NET_UDP6", "/proc/net/udp6"))
    rows = []
    for proto, fam, env, default in specs:
        rows.extend(_conn_file(_net_path(env, default), proto, fam))
    return True, {"count": len(rows), "limit": 200, "connections": rows[:200]}


def dispatch_deep(action):
    if action == "network.addresses":
        return addresses()
    if action == "network.routes":
        return routes()
    if action == "network.dns":
        return dns()
    if action == "network.connections":
        return connections()
    return None


def dispatch(action, params=None):
    if action == "network.list":
        return interfaces()
    if action == "network.state":
        return state()
    deep = dispatch_deep(action)
    if deep is not None:
        return deep
    return False, "不认识的动作：%s" % action
