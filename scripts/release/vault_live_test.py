#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的保险库进程验收（只读元数据；真总线、真动作、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/vault_live_test.py
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
        a = bus.ask("vault-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        st = bus.ask("vault-state", "vault.state", {}, ticket=tk, actor="world://user/zhang")
        sb = st.get("body") or {}
        check("vault.state 条目数/active", st.get("ok")
              and isinstance(sb.get("secrets"), int) and isinstance(sb.get("active"), int),
              "secrets=%r active=%r" % (sb.get("secrets"), sb.get("active")))

        r = bus.ask("vault-list", "vault.list", {"limit": 10}, ticket=tk,
                    actor="world://user/zhang")
        body = r.get("body") or {}
        items = body.get("secrets") or []
        check("vault.list 返回元数据", bool(r.get("ok")) and len(items) >= 1,
              "count=%r" % (body.get("count"),))
        blob = json.dumps(body, ensure_ascii=False)
        check("元数据不含值/路径", "value" not in blob and "/etc/" not in blob
              and "/root/" not in blob, "forbidden fields absent")
        first = items[0] if items else {}
        check("条目带 provider/state/rotated_at",
              bool(first.get("provider")) and bool(first.get("state"))
              and "rotated_at" in first,
              "id=%r provider=%r state=%r" % (first.get("name"), first.get("provider"),
                                              first.get("state")))

        ty = bus.query("vault-type", "type", ticket=tk, type="secret")
        raw = ty.get("data")
        rows = (raw.get("individuals") if isinstance(raw, dict) else raw) or []
        check("world/query kind=type 能查到 secret 个体", len(rows) >= 1,
              "secret 个体数=%d" % len(rows))

        bad = bus.ask("vault-get", "vault.get", {"id": "llm-api-key"},
                      ticket=tk, actor="world://user/zhang")
        check("vault.get 不存在（值不返回）", bad.get("ok") is False,
              str(bad.get("code") or bad.get("error"))[:120])

        import subprocess
        led = subprocess.run(
            ["grep", "-a", "vault.list", "/var/lib/aios/ontology/ledger.jsonl"],
            capture_output=True, text=True).stdout.splitlines()
        ok_led = any('"ok": true' in ln or '"ok":true' in ln for ln in led[-8:])
        check("账里有 vault.list 成功记录", ok_led, "命中 %d 行" % len(led))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
