#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的 ontology function / 内建 action 验收（真总线、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/functions_live_test.py
"""
import json
import subprocess
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

    def _wait(self, box, rid, timeout=15):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in box:
                return box[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def query(self, rid, kind, ticket=None, timeout=20, **extra):
        msg = {"id": rid, "kind": kind}
        msg.update(extra)
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_QUERY, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.queries, rid, timeout)

    def ask(self, rid, action, params, ticket=None, timeout=20):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.asks, rid, timeout)

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def grep_count(pattern):
    try:
        out = subprocess.run(["grep", "-ac", pattern, "/var/lib/aios/ontology/ledger.jsonl"],
                             capture_output=True, text=True).stdout.strip()
        return int(out or 0)
    except Exception:                                          # noqa: BLE001
        return 0


def ledger_rows():
    try:
        out = subprocess.run(["wc", "-l", "/var/lib/aios/ontology/ledger.jsonl"],
                             capture_output=True, text=True).stdout.split()
        return int(out[0]) if out else 0
    except Exception:                                          # noqa: BLE001
        return 0


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:220]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:180] if detail else ""))

    try:
        a = bus.ask("fn-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        before = ledger_rows()
        provider_before = grep_count("PROVIDER_NOT_DECLARED")

        def fn(rid, name, ticket=None, params=None):
            return bus.query("q" + rid, "function", ticket=ticket, name=name,
                             params=params or {})

        ov = fn("fn-ov", "fn.world.overview")
        r = (ov.get("data") or {}).get("result") or {}
        check("fn.world.overview", bool(ov.get("ok")) and r.get("classes") == 27
              and r.get("functions") == 8,
              "classes=%r functions=%r individuals=%r" % (r.get("classes"), r.get("functions"), r.get("individuals")))
        cc = fn("fn-cc", "fn.world.class_counts")
        counts = ((cc.get("data") or {}).get("result") or {}).get("classes") or {}
        check("fn.world.class_counts", bool(cc.get("ok")) and sum(counts.values()) == r.get("individuals"),
              "sum=%r" % (sum(counts.values()),))
        ls = fn("fn-ls", "fn.ledger.stats")
        lr = (ls.get("data") or {}).get("result") or {}
        check("fn.ledger.stats", bool(ls.get("ok")) and lr.get("rows", 0) >= before,
              "rows=%r last_at=%r" % (lr.get("rows"), lr.get("last_at")))
        ac = fn("fn-ac", "fn.action.stats")
        ar = (ac.get("data") or {}).get("result") or {}
        check("fn.action.stats", bool(ac.get("ok")) and ar.get("world_actions") == 212,
              "world_actions=%r registry=%r" % (ar.get("world_actions"), ar.get("registry_actions")))
        fs = fn("fn-fs", "fn.file.stats")
        check("fn.file.stats", bool(fs.get("ok")),
              str((fs.get("data") or {}).get("result"))[:120])
        wfs = fn("fn-wfs", "fn.worldfs.stats")
        wr = (wfs.get("data") or {}).get("result") or {}
        check("fn.worldfs.stats", bool(wfs.get("ok")) and "wpath" in wr,
              str(wr)[:140])

        no_ticket = fn("fn-find-no", "fn.object.find", params={"class": "file"})
        check("读函数无票被拒", no_ticket.get("ok") is False,
              str(no_ticket.get("why"))[:120])
        with_ticket = fn("fn-find", "fn.object.find", ticket=tk,
                         params={"class": "file", "where": {"name": "ledger.jsonl"}})
        rows = ((with_ticket.get("data") or {}).get("result") or {}).get("rows") or []
        check("读函数带票可查", bool(with_ticket.get("ok")) and len(rows) >= 1,
              "rows=%d" % len(rows))
        fn_rids = grep_count('"rid": "qfn-')
        check("function 查询只读（账里没有 function 查询行）", fn_rids == 0,
              "qfn-* ledger rows=%d" % fn_rids)

        # 内建动作（带票）
        m1 = bus.ask("act-mute", "notice.mute", {"subject": "act"}, ticket=tk)
        check("notice.mute", bool(m1.get("ok")), str((m1.get("body") or {}))[:120])
        j1 = bus.ask("act-job", "job.start", {"subject": "live-demo"}, ticket=tk)
        jid = (j1.get("body") or {}).get("job_id")
        check("job.start", bool(j1.get("ok")) and bool(jid), "job=%r" % jid)
        j2 = bus.ask("act-job2", "job.finish", {"subject": jid}, ticket=tk)
        check("job.finish", bool(j2.get("ok")) and (j2.get("body") or {}).get("state") == "finished",
              "state=%r" % ((j2.get("body") or {}).get("state"),))
        u1 = bus.ask("act-unsup", "ledger.compact", {"subject": "x"}, ticket=tk)
        check("ledger.compact 显式 UNSUPPORTED",
              u1.get("ok") is False and u1.get("code") == "UNSUPPORTED",
              "code=%r why=%r" % (u1.get("code"), str(u1.get("why"))[:80]))
        rows = subprocess.run(["grep", "-a", "UNSUPPORTED",
                               "/var/lib/aios/ontology/ledger.jsonl"],
                              capture_output=True, text=True).stdout.splitlines()
        check("UNSUPPORTED 已落账", len(rows) >= 1, "hits=%d" % len(rows))
        provider_after = grep_count("PROVIDER_NOT_DECLARED")
        check("无新 PROVIDER_NOT_DECLARED（内建动作接上）",
              provider_after <= provider_before,
              "before=%d after=%d（历史行不计）" % (provider_before, provider_after))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
