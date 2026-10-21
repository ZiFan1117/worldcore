#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的时间面进程验收（真总线、真动作、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/clock_live_test.py
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
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:160] if detail else ""))

    try:
        a = bus.ask("clk-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        t1 = bus.ask("clk-now1", "clock.now", {}, ticket=tk, actor="world://user/zhang")
        b1 = t1.get("body") or {}
        check("clock.now 返回时间", bool(t1.get("ok")) and bool(b1.get("now")),
              "now=%r" % (b1.get("now"),))
        check("clock.now 带 utc_offset/单调秒/boot_id",
              bool(b1.get("utc_offset")) and isinstance(b1.get("monotonic_seconds"), int)
              and "boot_id" in b1,
              "off=%r mono=%r boot=%s…" % (b1.get("utc_offset"),
                                           b1.get("monotonic_seconds"),
                                           str(b1.get("boot_id"))[:8]))

        time.sleep(1.2)
        t2 = bus.ask("clk-now2", "clock.now", {}, ticket=tk, actor="world://user/zhang")
        b2 = t2.get("body") or {}
        check("单调秒不倒退", bool(t2.get("ok"))
              and int(b2.get("monotonic_seconds") or 0) >= int(b1.get("monotonic_seconds") or 0),
              "%r → %r" % (b1.get("monotonic_seconds"), b2.get("monotonic_seconds")))

        st = bus.ask("clk-state", "clock.state", {}, ticket=tk, actor="world://user/zhang")
        sb = st.get("body") or {}
        check("clock.state 带 source/pid", st.get("ok") and sb.get("source") == "clock"
              and isinstance(sb.get("pid"), int), "pid=%r" % (sb.get("pid"),))

        bad = bus.ask("clk-set", "clock.set", {"now": "2000-01-01"},
                      ticket=tk, actor="world://user/zhang")
        check("clock.set 不存在（只读不变量）", bad.get("ok") is False,
              str(bad.get("code") or bad.get("error"))[:120])

        ty = bus.query("clk-type", "type", ticket=tk, type="clock")
        raw = ty.get("data")
        rows = (raw.get("individuals") if isinstance(raw, dict) else raw) or []
        check("world/query kind=type 能查到 clock 个体", len(rows) >= 1,
              "clock 个体数=%d" % len(rows))

        import subprocess
        led = subprocess.run(
            ["grep", "-a", "clock.now", "/var/lib/aios/ontology/ledger.jsonl"],
            capture_output=True, text=True).stdout.splitlines()
        ok_led = any('"ok": true' in ln or '"ok":true' in ln for ln in led[-8:])
        check("账里有 clock.now 成功记录", ok_led, "命中 %d 行" % len(led))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
