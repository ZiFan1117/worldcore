# -*- coding: utf-8 -*-
"""★ computer 的实时数据管道（独立子夹：采集 → 变化判定 → 上报本体）。

★ 作者（逐字整理）：「他的值改变了，然后再上报」「computer 这个个体要实时地有数据，打通上报本体，数据管道」。
★ 它做什么：
  · `collect_metrics()` 采集底层事实（/proc/uptime、loadavg、meminfo、os-release、cpu）；
  · `metrics_changed()` 判「值变没变」（uptime 不参与；负载 >0.1／内存 ≥64MB／其余不等）；
  · `should_report()` 判「这轮要不要报」（首次/变化/300 秒心跳）；
  · `metrics_loop()` 周期跑上面三步，真报时 `world/appear`（状态所有权在 computer）。
★ 它不是什么：不裁决、不记账、不注册动作；进程仍是 computer（aios-computer）。
"""
import datetime
import json
import os
import time

def collect_metrics(log=print):
    """★ 底层事实（数据管道的采集端）：uptime/load/mem/cpu/os；读不到就留空。"""
    m = {}
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            m["uptime_seconds"] = int(float(f.read().split()[0]))
    except Exception as e:                                  # noqa: BLE001
        log("采集 uptime 失败：%s" % e)
    try:
        with open("/proc/loadavg", encoding="utf-8") as f:
            p = f.read().split()
            m["load1"] = float(p[0])
            m["load5"] = float(p[1])
    except Exception as e:                                  # noqa: BLE001
        log("采集 loadavg 失败：%s" % e)
    try:
        info = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                k, _, rest = line.partition(":")
                info[k] = int(rest.strip().split()[0])   # kB
        m["mem_total_mb"] = int(info["MemTotal"] / 1024)
        m["mem_available_mb"] = int(info.get("MemAvailable", 0) / 1024)
    except Exception as e:                                  # noqa: BLE001
        log("采集 meminfo 失败：%s" % e)
    m["cpu_count"] = os.cpu_count() or 0
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    m["os_name"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception as e:                                  # noqa: BLE001
        log("采集 os-release 失败：%s" % e)
    return m


# ★ 变化上报口径：uptime 是单调量、不参与「值变没变」的判定；
#   负载变化 > 0.1、可用内存变化 ≥ 64MB、其余属性变了才算「真有变化」。
SIG_KEYS = ("state", "hostname", "cpu_count", "os_name",
            "load1", "load5", "mem_total_mb", "mem_available_mb")


def metrics_sig(m):
    return {"state": m.get("state"), "hostname": m.get("hostname"),
            "cpu_count": m.get("cpu_count"), "os_name": m.get("os_name"),
            "load1": round(float(m.get("load1") or 0.0), 2),
            "load5": round(float(m.get("load5") or 0.0), 2),
            "mem_total_mb": m.get("mem_total_mb"),
            "mem_available_mb": m.get("mem_available_mb")}


def metrics_changed(prev, cur):
    """★ 值变了吗？（阈值防抖：负载 0.1／内存 64MB）"""
    if prev is None:
        return True
    for k in SIG_KEYS:
        a, b = prev.get(k), cur.get(k)
        if k in ("load1", "load5"):
            if abs(float(b or 0) - float(a or 0)) > 0.1:
                return True
        elif k == "mem_available_mb":
            if abs(int(b or 0) - int(a or 0)) >= 64:
                return True
        elif a != b:
            return True
    return False


def should_report(prev, cur, since_last, heartbeat=300.0):
    """★ 只有【值变了】或【心跳到点】才上报（心跳用来证明还活着）。"""
    if prev is None:
        return True
    if metrics_changed(prev, cur):
        return True
    return float(since_last) >= float(heartbeat)


def metrics_loop(session, me, topic, name, every=10, log=print):
    """★ 数据管道的【上报端】：值变了才上报；300 秒心跳兜底。"""
    last_sig, last_at = None, 0.0
    while True:
        try:
            me.update(collect_metrics(log=log))
            sig = metrics_sig(me)
            now = time.time()
            since = now - last_at
            if should_report(last_sig, sig, since):
                me["metrics_at"] = datetime.datetime.now().astimezone().isoformat(
                    timespec="seconds")
                me["reporter"] = "world://computer/" + name
                session.put(topic, json.dumps(me, ensure_ascii=False))
                _why = ("首次" if last_sig is None
                        else ("变化" if metrics_changed(last_sig, sig) else "心跳"))
                log("★ 上报本体（%s）：uptime=%ss load1=%s mem=%s/%sMB"
                    % (_why, me.get("uptime_seconds"), me.get("load1"),
                       me.get("mem_available_mb"), me.get("mem_total_mb")))
                last_sig, last_at = sig, now
        except Exception as e:                              # noqa: BLE001
            log("★ 上报本体失败：%s" % e)
        time.sleep(every)



