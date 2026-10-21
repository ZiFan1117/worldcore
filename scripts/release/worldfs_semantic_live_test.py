#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：worldfs 语义边界（epoch/root/墓碑/ref）。"""
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
        import os
        os.environ.setdefault("AIOS_BUS_USER", "aios-clock")
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
        a = bus.ask("wfs-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        st0 = bus.ask("wfs-state0", "worldfs.state", {}, ticket=tk)
        b0 = st0.get("body") or {}
        check("state 有 epoch/root", bool(st0.get("ok")) and b0.get("epoch") and
              len(str(b0.get("root_sha") or "")) == 64,
              "epoch=%r root=%r" % (b0.get("epoch"), str(b0.get("root_sha"))[:12]))

        path = "/worldfs/sem-live.txt"
        w = bus.ask("wfs-w", "worldfs.write",
                    {"path": path, "text": "semantic", "intent": "C91 live"}, ticket=tk)
        b = w.get("body") or {}
        check("write 成功且给 ref", bool(w.get("ok")) and b.get("ref", "").startswith("world://wfile/"),
              "ref=%r" % b.get("ref"))
        st1 = bus.ask("wfs-state1", "worldfs.state", {}, ticket=tk)
        b1 = st1.get("body") or {}
        check("write 后 epoch+1、root 变", b1.get("epoch") == int(b0.get("epoch") or 0) + 1
              and b1.get("root_sha") != b0.get("root_sha"),
              "epoch=%r→%r" % (b0.get("epoch"), b1.get("epoch")))

        h = bus.ask("wfs-hist", "worldfs.history", {"path": path}, ticket=tk)
        ev = (h.get("body") or {}).get("events") or []
        check("history 有 active", any(e.get("state") == "active" for e in ev),
              "events=%d" % len(ev))
        ref = (w.get("body") or {}).get("ref") or ""
        g = bus.ask("wfs-get", "worldfs.get", {"ref": ref}, ticket=tk)
        check("worldfs.get 按 ref 取对象", bool(g.get("ok")) and
              (g.get("body") or {}).get("obj_id") == (w.get("body") or {}).get("obj_id"),
              str(g.get("body"))[:140])
        snap = bus.ask("wfs-snap", "worldfs.snapshot", {}, ticket=tk)
        check("worldfs.snapshot", bool(snap.get("ok")) and
              (snap.get("body") or {}).get("epoch") == b1.get("epoch"),
              str(snap.get("body"))[:140])

        rm = bus.ask("wfs-rm", "worldfs.remove", {"path": path, "intent": "C91 live rm"},
                     ticket=tk)
        h2 = bus.ask("wfs-hist2", "worldfs.history", {"path": path}, ticket=tk)
        states = [e.get("state") for e in ((h2.get("body") or {}).get("events") or [])]
        check("remove 后 history 有墓碑", bool(rm.get("ok")) and "removed" in states,
              "states=%r" % (states,))
        g2 = bus.ask("wfs-get2", "worldfs.get", {"ref": ref}, ticket=tk)
        check("删后旧对象 ref 仍可取", bool(g2.get("ok")),
              str((g2.get("body") or {}).get("state")))

        # 旧内容仍在（迁移/升级后）
        r = bus.ask("wfs-old", "worldfs.read", {"path": "/worldfs/notes/hello.txt"}, ticket=tk)
        check("旧内容仍可读", bool(r.get("ok")) and (r.get("body") or {}).get("text") == "hello world",
              str((r.get("body") or {}).get("text"))[:40])

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
