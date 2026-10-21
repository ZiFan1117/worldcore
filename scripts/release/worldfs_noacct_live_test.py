#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：worldfs 不记账，账都在本体（2026-10-21 作者令）。

用法（VM）：python3 /root/aios/scripts/release/worldfs_noacct_live_test.py
"""
import sys
import json
import os
import sqlite3
import subprocess
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
DB = "/var/lib/aios/worldfs/worldfs.db"
LEDGER = "/var/lib/aios/ontology/ledger.jsonl"
MOUNT = "/aios/worldfs"


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

    def ask(self, rid, action, params, ticket=None, timeout=15):
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


def rows():
    out = []
    if not os.path.exists(LEDGER):
        return out
    with open(LEDGER, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    try:
        before = len(rows())
        a = bus.ask("noacct-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        # 本地库：没有账本表/审计列
        c = sqlite3.connect(DB)
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        check("本地库无 txns 表", "txns" not in tables, sorted(tables))
        for t in ("objects", "versions", "paths"):
            cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % t)}
            bad = [x for x in ("created_at", "created_by", "intent", "updated_at", "updated_by")
                   if x in cols]
            check("%s 无审计列" % t, not bad, "cols=%r bad=%r" % (sorted(cols), bad))
        c.close()

        st = bus.ask("noacct-state", "worldfs.state", {}, ticket=tk)
        check("state 无 txns 账项", bool(st.get("ok")) and "txns" not in (st.get("body") or {}),
              str(st.get("body"))[:160])

        path = "/worldfs/noacct-live.txt"
        w = bus.ask("noacct-write", "worldfs.write",
                    {"path": path, "text": "no-local-ledger",
                     "intent": "C85 live: 验证账只在本体"}, ticket=tk)
        check("worldfs.write 成功", bool(w.get("ok")),
              str(w.get("error") or w.get("body"))[:160])
        r = bus.ask("noacct-read", "worldfs.read", {"path": path}, ticket=tk)
        check("worldfs.read 内容", bool(r.get("ok")) and
              (r.get("body") or {}).get("text") == "no-local-ledger",
              str((r.get("body") or {}).get("text"))[:80])

        # FUSE 只读投影能看到；写/删仍被拒
        cat = subprocess.run(["cat", MOUNT + "/noacct-live.txt"], capture_output=True, text=True)
        check("FUSE 读到新内容", cat.returncode == 0 and cat.stdout.strip() == "no-local-ledger",
              cat.stdout[:80])
        wt = subprocess.run(["bash", "-c", "echo x > %s/noacct-write-reject" % MOUNT],
                            capture_output=True, text=True)
        check("FUSE 写被拒（只读）", wt.returncode != 0 and "Read-only" in (wt.stderr or ""),
              (wt.stderr or "")[:100])

        # 账只在 ontology：新增 ask/result 有 worldfs.write 与 actor/intent
        after = rows()
        new = after[before:]
        asks = [x for x in new if x.get("kind_of") == "ask" and x.get("action") == "worldfs.write"]
        results = [x for x in new if x.get("kind_of") == "result"
                   and x.get("action") == "worldfs.write" and x.get("ok") is True]
        check("本体账新增 worldfs.write ask", bool(asks),
              "asks=%d" % len(asks))
        check("本体账新增 worldfs.write 成功结果", bool(results),
              "results=%d" % len(results))
        check("本体账 ask 带 actor/intent",
              any(x.get("actor") == "world://user/zhang" and
                  (x.get("params") or {}).get("intent") == "C85 live: 验证账只在本体"
                  for x in asks),
              str(asks[-1] if asks else None)[:220])
        # 本地不出现 ledger 文件
        local = subprocess.run(["bash", "-c",
                                "find /var/lib/aios/worldfs -iname '*ledger*' -print"],
                               capture_output=True, text=True).stdout.strip()
        check("worldfs 本地无 ledger 文件", local == "", local[:120])

        # 版本接口不带审计字段（审计去本体账）
        vs = bus.ask("noacct-vers", "worldfs.versions", {"path": path}, ticket=tk)
        vers = ((vs.get("body") or {}).get("versions") or [])
        check("versions 不带 created_by/intent",
              bool(vs.get("ok")) and vers and
              all("created_by" not in v and "intent" not in v for v in vers),
              str(vers[-1] if vers else None)[:180])

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
