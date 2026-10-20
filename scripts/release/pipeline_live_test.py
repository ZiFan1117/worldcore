#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 真总线上的数据管道详细测试（跑在 VM 上）。

★ 作者：「好好把这个数据管道测好了，详细地测」。
★ 它测什么：
  1) 真实 computer 上报节奏（窗口内 appear 条数/间隔/值变化）——变化驱动是否生效；
  2) 注入一条合成 appear（computer 身份）⇒ 本体接收、更新个体、账里 before/after、事件流收到；
  3) 权威线反例：用错误 reporter 报 computer ⇒ AUTHORITY_NOT_OWNER（并暴露“字符串可伪造/总线无 ACL”缺口）；
  4) 未知类反例 ⇒ APPEAR_CLASS_UNKNOWN；
  5) 恢复真实值，并回查 world/query kind=type 确认落库值。
用法（VM 上）：
  python3 /root/aios/scripts/release/pipeline_live_test.py --seconds 20
"""
import argparse
import datetime
import json
import os
import socket
import time

import zenoh

LEDGER = "/var/lib/aios/ontology/ledger.jsonl"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"
T_EVENT = "world/event"
T_APPEAR = "world/appear"


def read_ledger():
    rows = []
    if not os.path.exists(LEDGER):
        return rows
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def proc_metrics():
    m = {}
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            m["uptime_seconds"] = int(float(f.read().split()[0]))
        with open("/proc/loadavg", encoding="utf-8") as f:
            p = f.read().split()
            m["load1"], m["load5"] = float(p[0]), float(p[1])
        info = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                k, _, rest = line.partition(":")
                info[k] = int(rest.strip().split()[0])
        m["mem_total_mb"] = int(info["MemTotal"] / 1024)
        m["mem_available_mb"] = int(info.get("MemAvailable", 0) / 1024)
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    m["os_name"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception as e:
        print("采集失败:", e)
    m["cpu_count"] = os.cpu_count() or 0
    return m


class Bus:
    def __init__(self):
        conf = zenoh.Config()
        conf.insert_json5("mode", '"client"')
        conf.insert_json5("scouting/multicast/enabled", "false")
        conf.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
        self.z = zenoh.open(conf)
        self.asks, self.queries, self.events = {}, {}, []
        self.z.declare_subscriber(T_ASK_RESULT, lambda m: self._on(m, self.asks))
        self.z.declare_subscriber(T_QUERY_RESULT, lambda m: self._on(m, self.queries))
        self.z.declare_subscriber(T_EVENT, self._on_event)

    def _on(self, m, box):
        try:
            d = json.loads(m.payload.to_string())
        except Exception:
            return
        box[d.get("id")] = d

    def _on_event(self, m):
        try:
            self.events.append(json.loads(m.payload.to_string()))
        except Exception:
            pass

    def _wait(self, box, rid, timeout=10):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in box:
                return box[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def ask(self, rid, action, params, actor=None, ticket=None, timeout=10):
        msg = {"id": rid, "action": action, "params": params or {}}
        if actor:
            msg["actor"] = actor
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.asks, rid, timeout)

    def query(self, rid, kind, ticket=None, timeout=10, **extra):
        msg = {"id": rid, "kind": kind}
        msg.update(extra)
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_QUERY, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.queries, rid, timeout)

    def appear(self, payload):
        self.z.put(T_APPEAR, json.dumps(payload, ensure_ascii=False))

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0)
    args = ap.parse_args()
    host = socket.gethostname()
    bus = Bus()
    out = {"host": host, "window_seconds": args.seconds, "checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail else ""))

    try:
        # 0) 登录拿票（后面查 kind=type 要身份）
        a = bus.ask("plt-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), "ticket=" + tk[:12])

        # 1) 观察真实上报
        before = [r for r in read_ledger() if r.get("kind_of") == "appear"
                  and str(r.get("subject") or "").startswith("computer/")]
        ev_before = len(bus.events)
        t0 = time.time()
        time.sleep(args.seconds)
        after = [r for r in read_ledger() if r.get("kind_of") == "appear"
                 and str(r.get("subject") or "").startswith("computer/")]
        new = after[len(before):]
        ev_new = [e for e in bus.events[ev_before:] if e.get("kind_of") == "appear"]
        out["observed"] = {"new_appear_rows": len(new),
                           "new_appear_events": len(ev_new),
                           "window": args.seconds}
        print("观察 %.0fs：真实 appear 行 %d 条；事件 %d 条" % (args.seconds, len(new), len(ev_new)))
        # 变化驱动：10 秒一条的话 20s 最多约 2~3 条；给宽松上限
        check("变化驱动（窗口内出现次数 < 窗口秒数/5）", len(new) <= args.seconds / 5.0,
              "new=%d" % len(new))
        if new:
            u0 = int((new[0].get("after") or {}).get("uptime_seconds") or 0)
            u1 = int((new[-1].get("after") or {}).get("uptime_seconds") or 0)
            print("  窗口内 uptime：%s → %s（差 %s）" % (u0, u1, u1 - u0))

        # 2) 注入合成 appear（computer 身份）并验证落库/账/事件
        m = proc_metrics()
        payload = {"class": "computer", "name": host, "hostname": host,
                   "state": "in-service", "reporter": "world://computer/" + host,
                   "metrics_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
        payload.update(m)
        payload["load1"] = 3.14          # 标记值，便于查回来
        bus.appear(payload)
        time.sleep(1.5)
        q = bus.query("plt-type", "type", ticket=tk, type="computer")
        rows = q.get("data") or []
        got = None
        for r in rows:
            p = r.get("properties") or {}
            if p.get("name") == host:
                got = p
        check("注入 appear 后 world/query kind=type 能查到标记值",
              bool(got) and abs(float(got.get("load1") or 0) - 3.14) < 0.001,
              "load1=%r" % (got.get("load1") if got else None))
        led = [r for r in read_ledger() if r.get("subject") == "computer/" + host]
        hit = None
        for r in reversed(led):
            if abs(float((r.get("after") or {}).get("load1") or 0) - 3.14) < 0.001:
                hit = r
                break
        check("账里有注入那一笔（带 before/after）",
              bool(hit) and hit.get("kind_of") == "appear" and "before" in (hit or {}),
              "at=%r" % ((hit or {}).get("at"),))
        ev_hit = [e for e in bus.events if e.get("kind_of") == "appear"
                  and e.get("subject") == "computer/" + host]
        check("事件流收到 appear（本笔修了 family=change 不推事件的 bug）",
              bool(ev_hit), "events=%d" % len(ev_hit))

        # 3) 权威线反例：错误 reporter
        n_rej = len([r for r in read_ledger() if r.get("code") == "AUTHORITY_NOT_OWNER"])
        bus.appear({"class": "computer", "name": host, "hostname": host,
                    "state": "in-service", "reporter": "world://space/zhang",
                    "load1": 1.23})
        time.sleep(1.0)
        rej = [r for r in read_ledger() if r.get("code") == "AUTHORITY_NOT_OWNER"]
        check("错误 reporter 被拒（AUTHORITY_NOT_OWNER）", len(rej) > n_rej,
              "新增 %d 条" % (len(rej) - n_rej))
        out["acl_gap"] = ("上报者身份只靠 reporter 字符串，总线无 ACL ⇒ 能伪造成 world://computer/<host>；"
                          "真实入口应加签名/ACL（已登记为缺口）")

        # 4) 未知类反例
        n_unk = len([r for r in read_ledger() if r.get("code") == "APPEAR_CLASS_UNKNOWN"])
        bus.appear({"class": "no-such-class", "name": "x",
                    "reporter": "world://computer/" + host})
        time.sleep(1.0)
        unk = [r for r in read_ledger() if r.get("code") == "APPEAR_CLASS_UNKNOWN"]
        check("未知类被拒（APPEAR_CLASS_UNKNOWN）", len(unk) > n_unk,
              "新增 %d 条" % (len(unk) - n_unk))

        # 5) 恢复真实值（让 computer 下一轮心跳/变化自然纠正；这里主动报一次真实值）
        real = proc_metrics()
        restore = {"class": "computer", "name": host, "hostname": host,
                   "state": "in-service", "reporter": "world://computer/" + host,
                   "metrics_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
        restore.update(real)
        bus.appear(restore)
        time.sleep(1.0)
        q2 = bus.query("plt-type2", "type", ticket=tk, type="computer")
        got2 = None
        for r in (q2.get("data") or []):
            p = r.get("properties") or {}
            if p.get("name") == host:
                got2 = p
        check("恢复真实值（load1 回到本机真实值）",
              got2 is not None and abs(float(got2.get("load1") or 0) - real["load1"]) < 0.2,
              "load1=%r real=%r" % ((got2 or {}).get("load1"), real.get("load1")))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
