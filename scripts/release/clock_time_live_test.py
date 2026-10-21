#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：clock 时间统一（ledger 用 clock 快照）。"""
import json
import sys
import time

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import zenoh  # noqa: E402
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
CLOCK_STATE = "/var/lib/aios/clock/state.json"
LEDGER = "/var/lib/aios/ontology/ledger.jsonl"


class Bus:
    def __init__(self):
        conf = zenoh.Config()
        conf.insert_json5("mode", '"client"')
        conf.insert_json5("scouting/multicast/enabled", "false")
        conf.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
        self.z = open_bus(conf)
        self.asks = {}
        self.z.declare_subscriber(T_ASK_RESULT, self._on)

    def _on(self, m):
        try:
            d = json.loads(m.payload.to_string())
        except Exception:
            return
        self.asks[d.get("id")] = d

    def ask(self, rid, action, params=None, ticket=None, timeout=15):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in self.asks:
                return self.asks[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def _clock():
    try:
        with open(CLOCK_STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _ledger_tail(n=5):
    rows = []
    try:
        with open(LEDGER, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    except OSError:
        pass
    return rows[-n:]


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    try:
        a = bus.ask("clock-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        c1 = _clock()
        check("clock 快照存在", bool(c1.get("now")), "now=%r" % c1.get("now"))
        time.sleep(2)
        c2 = _clock()
        check("clock 快照每秒更新", c2.get("now") != c1.get("now"),
              "%r → %r" % (c1.get("now"), c2.get("now")))

        r = bus.ask("clock-now", "clock.now", {}, ticket=tk)
        body = r.get("body") or {}
        check("clock.now 可读", bool(r.get("ok")) and bool(body.get("now")),
              "now=%r" % body.get("now"))

        # 一次写 ⇒ 最新 ledger at 应接近 clock 快照（≤5s）
        w = bus.ask("clock-write", "worldfs.write",
                    {"path": "/worldfs/clock-live.txt", "text": "clock-unity",
                     "intent": "clock time live test"}, ticket=tk)
        check("worldfs.write 成功", bool(w.get("ok")), str(w.get("error") or w.get("body"))[:120])
        c3 = _clock()
        rows = _ledger_tail(10)
        target = None
        for row in reversed(rows):
            if row.get("at") and str(row.get("at")) >= str(c3.get("now", ""))[:19]:
                target = row
                break
        if target is None and rows:
            target = rows[-1]
        at = str((target or {}).get("at") or "")
        ok_time = bool(at) and at[:19] == str(c3.get("now") or "")[:19]
        check("ledger at 用 clock 快照时间", ok_time,
              "at=%r clock=%r" % (at, c3.get("now")))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
