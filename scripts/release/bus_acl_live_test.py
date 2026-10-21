#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：总线 ACL（Zenoh user-password 认证）。

用法（VM）：python3 /root/aios/scripts/release/bus_acl_live_test.py
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import bus_auth  # noqa: E402
from provider_auth import provider_auth as PA  # noqa: E402
import zenoh  # noqa: E402

ENDPOINT = "tcp/127.0.0.1:7447"


def _base_conf():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    return conf


def _try(user=None, password=None, timeout=12):
    conf = _base_conf()
    if user is not None:
        conf.insert_json5("transport/auth/usrpwd/user", json.dumps(user))
        conf.insert_json5("transport/auth/usrpwd/password", json.dumps(password))
    try:
        z = zenoh.open(conf)
        z.close()
        return True, "OPEN_OK"
    except Exception as e:                                      # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def _put_as(user, password, topic, obj):
    conf = _base_conf()
    conf.insert_json5("transport/auth/usrpwd/user", json.dumps(user))
    conf.insert_json5("transport/auth/usrpwd/password", json.dumps(password))
    z = zenoh.open(conf)
    pub = z.declare_publisher(topic)
    time.sleep(0.3)
    pub.put(json.dumps(obj, ensure_ascii=False))
    time.sleep(1.2)
    z.close()


def _ledger():
    rows = []
    try:
        with open("/var/lib/aios/ontology/ledger.jsonl", encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    except OSError:
        pass
    return rows


def main():
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    creds = bus_auth.load_credentials()
    secret = ""
    try:
        with open("/etc/aios/bus-client.secret", encoding="utf-8") as f:
            secret = f.read().strip()
    except OSError:
        pass
    check("凭据文件存在", bool(creds) and bool(secret),
          "user=%r secret_len=%d" % (creds[0] if creds else None, len(secret)))

    units = ["aios-bus", "aios-ontology", "aios-clock", "aios-web", "aios-fs",
             "aios-network", "aios-recovery", "aios-vault", "aios-worldfs",
             "aios-worldfs-fuse", "aios-computer", "aios-presentation",
             "aios-presentation-render", "aios-space", "aios-agent", "aios-guard"]
    n = 0
    for u in units:
        r = subprocess.run(["systemctl", "is-active", u], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            n += 1
    check("16 单元 active", n == 16, "active=%d" % n)

    ok, why = _try()
    check("无凭据连不上", not ok, why)
    ok, why = _try("tests", "wrong-password")
    check("错口令连不上", not ok, why)
    ok, why = _try("tests", secret)
    check("合法凭据可连", ok, why)

    if ok:
        # 合法客户端真收发
        conf = _base_conf()
        conf = bus_auth.configure(conf)
        z = zenoh.open(conf)
        seen = []
        sub = z.declare_subscriber("acl/test/**", lambda s: seen.append(s.payload.to_string()))
        pub = z.declare_publisher("acl/test/x")
        time.sleep(0.5)
        pub.put("acl-ok")
        time.sleep(1.0)
        check("合法客户端可收发", "acl-ok" in seen, "seen=%r" % seen)
        z.close()

    # topic 级 ACL：非 provider 用户发 appear 被总线拒（不到本体账）
    PA._SEEN.clear()
    denied = PA.sign_message("world/appear", {
        "class": "clock", "name": "acl-denied", "state": "running",
        "reporter": "world://clock/acl-denied", "now": "2026-10-21T00:00:00+00:00",
        "timezone": "UTC", "utc_offset": "+00:00", "boot_id": "x", "monotonic_seconds": 1})
    _put_as("tests", secret, "world/appear", denied)
    rows = _ledger()
    check("非 provider（tests）发 appear 被总线拒",
          not any("acl-denied" in str(r) for r in rows), "no ledger row")

    # provider 用户 aios-clock 发签名 appear ⇒ 总线放行、本体收下
    PA._SEEN.clear()
    allowed = PA.sign_message("world/appear", {
        "class": "clock", "name": "acl-allowed", "state": "running",
        "reporter": "world://clock/acl-allowed", "now": "2026-10-21T00:00:00+00:00",
        "timezone": "UTC", "utc_offset": "+00:00", "boot_id": "x", "monotonic_seconds": 1})
    _put_as("aios-clock", secret, "world/appear", allowed)
    rows = _ledger()
    check("provider（aios-clock）发 appear 被收下",
          any(r.get("kind_of") == "appear" and "clock/acl-allowed" in str(r.get("subject"))
              for r in rows), "accepted")

    ok = all(c["ok"] for c in out["checks"])
    out["ok"] = ok
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
