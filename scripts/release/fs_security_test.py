#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的 fs 安全边界验收：符号链接逃逸 / ../ 遍历 / 秘密文件 / 正常目录。

用法（VM）：
  python3 /root/aios/scripts/release/fs_security_test.py
"""
import sys
import json
import os
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
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

    def ask(self, rid, action, params, ticket=None, actor=None, timeout=12):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        if actor:
            msg["actor"] = actor
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
    link = "/var/lib/aios/escape-crit"
    secret = "/var/lib/aios/.fs-secret-crit"
    for p in (link, secret):
        try:
            os.remove(p)
        except OSError:
            pass
    os.symlink("/etc/passwd", link)
    with open(secret, "w", encoding="utf-8") as f:
        f.write("TOKEN=abc")
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:220]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:180] if detail else ""))

    try:
        a = bus.ask("fss-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "")
        check("登录拿票", bool(tk), tk[:14])
        r = bus.ask("fss-list", "file.list", {"path": "/var/lib/aios/ontology", "limit": 3},
                    ticket=tk, actor="world://user/zhang")
        check("正常目录可列（白名单内）", bool(r.get("ok")) and (r.get("body") or {}).get("count") <= 3,
              "count=%r" % ((r.get("body") or {}).get("count"),))
        e = bus.ask("fss-link", "file.stat", {"path": link},
                    ticket=tk, actor="world://user/zhang")
        check("符号链接逃逸被拒", e.get("ok") is False and "越界" in str(e.get("error") or ""),
              str(e.get("error"))[:120])
        t = bus.ask("fss-trav", "file.stat", {"path": "/var/lib/aios/../etc/passwd"},
                    ticket=tk, actor="world://user/zhang")
        check("../ 遍历被拒", t.get("ok") is False and "越界" in str(t.get("error") or ""),
              str(t.get("error"))[:120])
        s = bus.ask("fss-secret", "file.read_text", {"path": secret},
                    ticket=tk, actor="world://user/zhang")
        check("隐藏/秘密文件拒读", s.get("ok") is False and "秘密" in str(s.get("error") or ""),
              str(s.get("error"))[:120])
        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()
        for p in (link, secret):
            try:
                os.remove(p)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
