#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：world_snapshot 带 worldfs manifest，restore 不再两套事实。"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import zenoh  # noqa: E402
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
SNAP = "/root/snapshot-worldfs-live"
SCRIPT = "/root/aios/scripts/release/world_snapshot.py"


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

    def ask(self, rid, action, params=None, ticket=None, timeout=20):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in self.asks:
                return self.asks[rid]
            time.sleep(0.1)
        return {"ok": False, "why": "timeout"}

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    if os.path.isdir(SNAP):
        import shutil
        shutil.rmtree(SNAP, ignore_errors=True)
    r = sh(["python3", SCRIPT, "save", "--out", SNAP])
    check("world_snapshot save", r.returncode == 0, (r.stdout or r.stderr)[-160:])
    check("快照含 worldfs_manifest", os.path.isfile(os.path.join(SNAP, "worldfs_manifest.json")))
    check("快照含 worldfs.db", os.path.isfile(os.path.join(SNAP, "worldfs.db")))
    try:
        m = json.load(open(os.path.join(SNAP, "worldfs_manifest.json"), encoding="utf-8"))
    except Exception as e:
        m = {}
        check("manifest 可读", False, str(e))
    check("manifest 有 epoch/root", bool(m.get("epoch")) and len(str(m.get("root_sha") or "")) == 64,
          "epoch=%r" % m.get("epoch"))
    v = sh(["python3", SCRIPT, "verify", "--snap", SNAP])
    check("verify 绿", v.returncode == 0 and "verify=ok" in (v.stdout or ""),
          (v.stdout or v.stderr)[-120:])

    time.sleep(8)   # save 会停/起 ontology，等它重新订上总线
    bus = Bus()
    try:
        a = bus.ask("snap-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        path = "/worldfs/snapshot-live.txt"
        w = bus.ask("snap-write", "worldfs.write",
                    {"path": path, "text": "after-snapshot", "intent": "snapshot live test"},
                    ticket=tk)
        check("快照后写新文件", bool(w.get("ok")), str(w.get("error") or w.get("body"))[:120])
        r = bus.ask("snap-read", "worldfs.read", {"path": path}, ticket=tk)
        check("新文件可读", bool(r.get("ok")), str((r.get("body") or {}).get("text"))[:60])
        bus.close()
        # restore（脚本会停/起 worldfs+ontology）
        rr = sh(["python3", SCRIPT, "restore", "--snap", SNAP, "--yes", "--restart"])
        check("restore 成功", rr.returncode == 0, (rr.stdout or rr.stderr)[-180:])
        check("restore 日志含 worldfs restored", "worldfs restored" in (rr.stdout or ""),
              (rr.stdout or "")[-160:])
        time.sleep(8)
        bus = Bus()
        a = bus.ask("snap-auth2", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        r2 = bus.ask("snap-read2", "worldfs.read", {"path": path}, ticket=tk)
        check("restore 后新文件消失", r2.get("ok") is False,
              str(r2.get("error") or r2.get("code"))[:100])
        old = bus.ask("snap-old", "worldfs.read", {"path": "/worldfs/notes/hello.txt"}, ticket=tk)
        check("restore 后旧内容在", old.get("ok") and
              (old.get("body") or {}).get("text") == "hello world",
              str((old.get("body") or {}).get("text"))[:40])
        st = bus.ask("snap-state", "worldfs.state", {}, ticket=tk)
        check("restore 后 worldfs root == manifest",
              bool(st.get("ok")) and (st.get("body") or {}).get("root_sha") == m.get("root_sha"),
              "root=%r" % str((st.get("body") or {}).get("root_sha"))[:12])
        units = ["aios-bus", "aios-ontology", "aios-clock", "aios-web", "aios-fs",
                 "aios-network", "aios-recovery", "aios-vault", "aios-worldfs",
                 "aios-worldfs-fuse", "aios-computer", "aios-presentation",
                 "aios-presentation-render", "aios-space", "aios-agent", "aios-guard"]
        n = sum(1 for u in units if sh(["systemctl", "is-active", u]).stdout.strip() == "active")
        check("restore 后 16 单元 active", n == 16, "active=%d" % n)
    finally:
        bus.close()
    ok = all(c["ok"] for c in out["checks"])
    out["ok"] = ok
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
