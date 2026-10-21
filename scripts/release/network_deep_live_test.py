#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：network 深度只读（地址/路由/DNS/连接）。"""
import json
import sys
import time

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import zenoh  # noqa: E402
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"


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


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    try:
        a = bus.ask("netdeep-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        for aid, key in (("network.addresses", "addresses"),
                         ("network.routes", "routes"),
                         ("network.dns", "nameservers"),
                         ("network.connections", "connections")):
            r = bus.ask("netdeep-" + aid, aid, {}, ticket=tk)
            body = r.get("body") or {}
            check(aid, bool(r.get("ok")) and key in body,
                  "count=%r" % body.get("count") if key != "nameservers" else "ns=%r" % body.get("nameservers"))
        r = bus.ask("netdeep-setip", "network.set_ip", {"iface": "lo"}, ticket=tk)
        check("network.set_ip 仍不存在", r.get("ok") is False,
              str(r.get("error") or r.get("code"))[:100])
        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
