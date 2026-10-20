#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的 fs 语义文件进程验收（真总线、真动作、真账）。

用法（VM）：
  python3 /root/aios/scripts/release/fs_live_test.py
"""
import json
import os
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

    def ask(self, rid, action, params, actor=None, ticket=None, timeout=12):
        msg = {"id": rid, "action": action, "params": params or {}}
        if actor:
            msg["actor"] = actor
        if ticket:
            msg["ticket"] = ticket
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
    out_checks = out["checks"]

    def check(name, ok, detail=""):
        out_checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:160] if detail else ""))

    try:
        a = bus.ask("fs-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        r = bus.ask("fs-list", "file.list", {"path": "/var/lib/aios", "limit": 10},
                    ticket=tk, actor="world://user/zhang")
        check("file.list /var/lib/aios", bool(r.get("ok")),
              "count=%r" % ((r.get("body") or {}).get("count"),))
        names = {e.get("name") for e in ((r.get("body") or {}).get("entries") or [])}
        check("列表含 ontology 目录", "ontology" in names, sorted(names)[:8])

        static_file = "/root/aios/scripts/release/systemd/aios-fs.service"
        st = bus.ask("fs-stat", "file.stat", {"path": static_file},
                     ticket=tk, actor="world://user/zhang")
        body = st.get("body") or {}
        check("file.stat 静态文件", bool(st.get("ok")) and int(body.get("size") or 0) > 0,
              "size=%r kind=%r err=%r" % (body.get("size"), body.get("kind"),
                                          st.get("error") or st.get("code")))
        check("file.stat 带 sha256", len(str(body.get("sha256") or "")) == 64,
              str(body.get("sha256"))[:16] + "…")

        h = bus.ask("fs-hash", "file.hash", {"path": static_file},
                    ticket=tk, actor="world://user/zhang")
        hb = h.get("body") or {}
        check("file.hash 一致", h.get("ok") and hb.get("sha256") == body.get("sha256"),
              "stat=%r hash=%r err=%r" % (str(body.get("sha256"))[:12],
                                         str(hb.get("sha256"))[:12], h.get("error") or h.get("code")))

        tx = bus.ask("fs-read", "file.read_text",
                     {"path": "/var/lib/aios/ontology/registry.jsonl", "max_bytes": 200},
                     ticket=tk, actor="world://user/zhang")
        tb = tx.get("body") or {}
        check("file.read_text 截断", bool(tx.get("ok")) and tb.get("bytes_read") <= 200
              and isinstance(tb.get("text"), str), "bytes_read=%r truncated=%r"
              % (tb.get("bytes_read"), tb.get("truncated")))

        bad = bus.ask("fs-out", "file.stat", {"path": "/etc/passwd"},
                      ticket=tk, actor="world://user/zhang")
        check("越界路径被拒（/etc/passwd）", bad.get("ok") is False,
              str(bad.get("error") or bad.get("code"))[:120])

        secret_path = "/var/lib/aios/.fs-secret-crit"
        with open(secret_path, "w", encoding="utf-8") as f:
            f.write("TOKEN=abc")
        try:
            secret = bus.ask("fs-secret", "file.read_text", {"path": secret_path},
                             ticket=tk, actor="world://user/zhang")
        finally:
            try:
                os.remove(secret_path)
            except OSError:
                pass
        check("隐藏/秘密文件拒读（.fs-secret-crit）",
              secret.get("ok") is False and "秘密" in str(secret.get("error") or ""),
              str(secret.get("error") or secret.get("code"))[:120])

        acts = bus.query("fs-actions", "actions")
        raw = acts.get("data") or {}
        reg = set(raw.get("registry") or [])
        ont = set(raw.get("ontology") or [])
        need = {"file.stat", "file.list", "file.hash", "file.read_text"}
        check("注册表有 file.*（world/query actions）", need <= reg and need <= ont,
              "registry file.*=%d ontology file.*=%d"
              % (len([i for i in reg if str(i).startswith("file.")]),
                 len([i for i in ont if str(i).startswith("file.")])))

        ty = bus.query("fs-type", "type", ticket=tk, type="file")
        rawt = ty.get("data")
        rows = (rawt.get("individuals") if isinstance(rawt, dict) else rawt) or []
        check("world/query kind=type 能查到 file 个体",
              any((r.get("properties") or {}).get("path") ==
                  "/var/lib/aios/ontology/ledger.jsonl" for r in rows),
              "file 个体数=%d" % len(rows))

        import subprocess
        led = subprocess.run(
            ["grep", "-a", "file.list", "/var/lib/aios/ontology/ledger.jsonl"],
            capture_output=True, text=True).stdout.splitlines()
        ok_led = any('"ok": true' in ln or '"ok":true' in ln for ln in led[-5:])
        check("账里有 file.list 的成功记录", ok_led, "命中 %d 行" % len(led))

        ok = all(c["ok"] for c in out_checks)
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
