#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的恢复边界进程验收（真总线、真动作、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/recovery_live_test.py
"""
import json
import time

import zenoh

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
        self.z = zenoh.open(conf)
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
        a = bus.ask("rec-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        r = bus.ask("rec-list", "recovery.list", {"limit": 5},
                    ticket=tk, actor="world://user/zhang")
        body = r.get("body") or {}
        ents = body.get("entries") or []
        check("recovery.list 返回快照", bool(r.get("ok")) and len(ents) >= 2,
              "count=%r forks=%r" % (body.get("count"), body.get("forks")))
        e = ents[0] if ents else {}
        check("快照项带 at/ledger_rows/law_sha256",
              isinstance(e.get("ledger_rows"), int) and bool(e.get("at"))
              and len(str(e.get("law_sha256") or "")) == 64,
              "name=%r rows=%r" % (e.get("name"), e.get("ledger_rows")))

        st = bus.ask("rec-state", "recovery.state", {}, ticket=tk,
                     actor="world://user/zhang")
        sb = st.get("body") or {}
        check("recovery.state 数量/最新", st.get("ok") and int(sb.get("snapshots") or 0) >= 2
              and bool(sb.get("latest")),
              "snapshots=%r latest=%r" % (sb.get("snapshots"), sb.get("latest")))

        bad = bus.ask("rec-restore", "recovery.restore", {"snap": "x"},
                      ticket=tk, actor="world://user/zhang")
        check("recovery.restore 不存在（只读不变量）", bad.get("ok") is False,
              str(bad.get("code") or bad.get("error"))[:120])

        ty = bus.query("rec-type", "type", ticket=tk, type="snapshot")
        raw = ty.get("data")
        rows = (raw.get("individuals") if isinstance(raw, dict) else raw) or []
        check("world/query kind=type 能查到 snapshot 个体", len(rows) >= 1,
              "snapshot 个体数=%d" % len(rows))

        import subprocess
        led = subprocess.run(
            ["grep", "-a", "recovery.list", "/var/lib/aios/ontology/ledger.jsonl"],
            capture_output=True, text=True).stdout.splitlines()
        ok_led = any('"ok": true' in ln or '"ok":true' in ln for ln in led[-8:])
        check("账里有 recovery.list 成功记录", ok_led, "命中 %d 行" % len(led))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
