#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：provider 消息签名（appear）。

用法（VM）：python3 /root/aios/scripts/release/appear_auth_live_test.py
"""
import json
import os
import subprocess
import sys
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
from bus_auth import open_bus  # noqa: E402
os.environ.setdefault("AIOS_BUS_USER", "aios-clock")  # provider 用户过 topic ACL

sys.path.insert(0, "/usr/lib/aios/src/ontology")
from provider_auth import provider_auth as PA  # noqa: E402

T_APPEAR = "world/appear"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"


class Bus:
    def __init__(self, signed=False):
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

    def _wait(self, box, rid, timeout=15):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in box:
                return box[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def ask(self, rid, action, params=None, timeout=15):
        self.z.put(T_ASK, json.dumps({"id": rid, "action": action,
                                      "params": params or {}}, ensure_ascii=False))
        return self._wait(self.asks, rid, timeout)

    def query(self, rid, kind, timeout=15, **kw):
        msg = {"id": rid, "kind": kind}
        msg.update(kw)
        self.z.put(T_QUERY, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.queries, rid, timeout)

    def appear(self, payload):
        self.z.put(T_APPEAR, json.dumps(payload, ensure_ascii=False))

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def ledger_rows():
    out = []
    try:
        with open("/var/lib/aios/ontology/ledger.jsonl", encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except OSError:
        pass
    return out


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    try:
        before = ledger_rows()
        # 1) 无签名伪造：必须拒
        bus.appear({"class": "clock", "name": "forged-unsigned",
                    "reporter": "world://clock/forged-unsigned",
                    "state": "running", "now": "2026-10-21T00:00:00+00:00",
                    "timezone": "UTC", "utc_offset": 0, "boot_id": "x",
                    "monotonic_seconds": 1})
        time.sleep(1.5)
        new = ledger_rows()[len(before):]
        rejected = [r for r in new if r.get("kind_of") == "reject"
                    and r.get("code") in ("BAD_SIGNATURE", "UNKNOWN_KEY")]
        check("无签名 appear 被拒", bool(rejected),
              "rejects=%d" % len(rejected))
        check("伪造未建个体",
              not any(r.get("kind_of") == "appear" and "forged-unsigned" in str(r)
                      for r in new), "no fake appear")

        # 2) 冒名：clock 的 key 签 vault reporter → 拒
        PA._SEEN.clear()
        forged = PA.sign_message("world/appear", {
            "class": "vault", "name": "forged-cross",
            "reporter": "world://vault/forged-cross", "state": "running",
            "secrets": 0, "active": 0}, kind="clock")
        bus.appear(forged)
        time.sleep(1.5)
        new2 = ledger_rows()[len(before):]
        rej2 = [r for r in new2 if r.get("kind_of") == "reject"
                and r.get("code") == "REPORTER_KEY_MISMATCH"]
        check("冒名 reporter 被拒", bool(rej2), "rejects=%d" % len(rej2))

        # 3) 重放：同一签名消息两次 → 第二次 REPLAY
        PA._SEEN.clear()
        m = PA.sign_message("world/appear", {
            "class": "agent", "name": "auth-live", "did": "did:aios:agent:auth-live",
            "reporter": "world://agent/auth-live", "state": "running"})
        bus.appear(m)
        time.sleep(1.2)
        bus.appear(m)
        time.sleep(1.5)
        new3 = ledger_rows()[len(before):]
        rej3 = [r for r in new3 if r.get("kind_of") == "reject"
                and r.get("code") == "REPLAY"]
        check("重放 appear 被拒", bool(rej3), "rejects=%d" % len(rej3))
        check("签名 appear 真被收下",
              any(r.get("kind_of") == "appear" and "agent/auth-live" in str(r.get("subject"))
                  for r in new3), "accepted")

        # 3b) 无签名 register / result 也被拒
        bus.z.put("world/register", json.dumps({
            "action": "clock.forged", "function": "forged",
            "registered_by": "clock/forged", "registered_by_kind": "clock",
            "required_roles": ["clock"]}, ensure_ascii=False))
        bus.z.put("world/exec/result", json.dumps({
            "id": "forged-result", "action": "clock.now", "ok": True,
            "body": {"forged": True}, "by": "clock/forged"}, ensure_ascii=False))
        time.sleep(1.5)
        new4 = ledger_rows()[len(before):]
        rej4 = [r for r in new4 if r.get("kind_of") == "reject"
                and r.get("code") == "BAD_SIGNATURE"]
        check("无签名 register/result 被拒", len(rej4) >= 2,
              "rejects=%d" % len(rej4))

        # 4) 真 provider 仍在：clock 个体在
        a = bus.ask("auth-ticket", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        q = bus.query("auth-clock", "type", ticket=tk, type="clock")
        data = q.get("data")
        rows = (data.get("individuals") if isinstance(data, dict) else data) or []
        check("真 clock 个体仍在", bool(q.get("ok")) and len(rows) >= 1,
              "clock individuals=%d" % len(rows))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
