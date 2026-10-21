#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的网络面进程验收（真总线、真动作、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/network_live_test.py
"""
import sys
import json
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"


class Bus:
    def __init__(self):
        conf = zenoh.Config()
        conf.insert_json5("mode", '"client"')
        conf.insert_json5("scouting/multicast/enabled", "false")
        conf.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
        self.z = open_bus(conf)
        self.asks, self.queries = {}, {}
        self.z.declare_subscriber(T_ASK_RESULT, lambda m: self._on(m, self.asks))
        self.z.declare_subscriber(T_QUERY_RESULT, lambda m: self._on(m, self.queries))

    def _on(self, m, box):
        try:
            d = json.loads(m.payload.to_string())
        except Exception:
            return
        box[d.get("id")] = d

    def _wait(self, box, rid, timeout=10):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in box:
                return box[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def ask(self, rid, action, params, ticket=None, actor=None, timeout=12):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        if actor:
            msg["actor"] = actor
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.asks, rid, timeout)

    def query(self, rid, kind, ticket=None, timeout=12, **extra):
        msg = {"id": rid, "kind": kind}
        msg.update(extra)
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_QUERY, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.queries, rid, timeout)

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:220]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:180] if detail else ""))

    try:
        a = bus.ask("net-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        r = bus.ask("net-list", "network.list", {}, ticket=tk, actor="world://user/zhang")
        body = r.get("body") or {}
        ifaces = body.get("interfaces") or []
        check("network.list 返回接口", bool(r.get("ok")) and len(ifaces) >= 1,
              "count=%r up=%r" % (body.get("count"), body.get("up")))
        names = {i.get("name") for i in ifaces}
        check("含 lo 与至少一个 eth/物理口", "lo" in names and len(names) >= 2,
              sorted(names)[:8])
        e0 = ifaces[0] if ifaces else {}
        check("接口项带 kind/state/计数器",
              bool(e0.get("kind")) and isinstance(e0.get("rx_bytes"), int),
              "name=%r kind=%r rx=%r" % (e0.get("name"), e0.get("kind"),
                                         e0.get("rx_bytes")))

        st = bus.ask("net-state", "network.state", {}, ticket=tk, actor="world://user/zhang")
        sb = st.get("body") or {}
        check("network.state 接口数/字节", st.get("ok")
              and isinstance(sb.get("interfaces"), int)
              and isinstance(sb.get("rx_bytes"), int),
              "ifaces=%r up=%r rx=%r" % (sb.get("interfaces"), sb.get("up"),
                                         sb.get("rx_bytes")))

        bad = bus.ask("net-set", "network.set_ip", {"iface": "eth0"},
                      ticket=tk, actor="world://user/zhang")
        check("network.set_ip 不存在（只读不变量）", bad.get("ok") is False,
              str(bad.get("code") or bad.get("error"))[:120])

        ty = bus.query("net-type", "type", ticket=tk, type="link")
        raw = ty.get("data")
        rows = (raw.get("individuals") if isinstance(raw, dict) else raw) or []
        check("world/query kind=type 能查到 link 个体", len(rows) >= 1,
              "link 个体数=%d" % len(rows))

        import subprocess
        led = subprocess.run(
            ["grep", "-a", "network.list", "/var/lib/aios/ontology/ledger.jsonl"],
            capture_output=True, text=True).stdout.splitlines()
        ok_led = any('"ok": true' in ln or '"ok":true' in ln for ln in led[-8:])
        check("账里有 network.list 成功记录", ok_led, "命中 %d 行" % len(led))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
