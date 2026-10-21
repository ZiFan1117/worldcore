#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的 worldfs FUSE 验收（真挂载、只读、与 worldfs 动作一致）。

用法（VM）：
  python3 /root/aios/scripts/release/worldfs_fuse_live_test.py
"""
import sys
import json
import os
import subprocess
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
from bus_auth import open_bus  # noqa: E402

MOUNT = "/aios/worldfs"
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


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:220]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:180] if detail else ""))

    try:
        st = sh(["systemctl", "is-active", "aios-worldfs-fuse"]).stdout.strip()
        check("aios-worldfs-fuse active", st == "active", st)
        mounts = sh(["mount"]).stdout
        check("宿主可见 fuse 挂载", "worldfs on /aios/worldfs type fuse.worldfs" in mounts,
              [ln for ln in mounts.splitlines() if "aios/worldfs" in ln][:1])
        check("ro 挂载选项", "ro," in mounts or "(ro" in mounts,
              [ln for ln in mounts.splitlines() if "aios/worldfs" in ln][:1][0][:120])

        ls = sh(["ls", "-la", MOUNT + "/notes"])
        check("ls /notes", ls.returncode == 0 and "hello.txt" in ls.stdout,
              ls.stdout[:160])
        cat = sh(["cat", MOUNT + "/notes/hello.txt"])
        check("cat hello.txt", cat.returncode == 0 and cat.stdout.strip() == "hello world",
              cat.stdout[:80])

        # 写入 worldfs 动作 → FUSE 立刻可见（只读视图跟 store 走）
        a = bus.ask("fuse-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        w = bus.ask("fuse-write", "worldfs.write",
                    {"path": "/worldfs/fuse-live.txt", "text": "hello-from-worldfs",
                     "intent": "fuse live test"}, ticket=tk)
        check("worldfs.write 新文件", bool(w.get("ok")), str(w.get("error") or w.get("body"))[:120])
        cat2 = sh(["cat", MOUNT + "/fuse-live.txt"])
        check("FUSE 读到 worldfs 动作写的内容",
              cat2.returncode == 0 and cat2.stdout.strip() == "hello-from-worldfs",
              cat2.stdout[:80])

        wt = sh(["bash", "-c", "echo x > %s/nope.txt" % MOUNT])
        check("FUSE 写被拒（只读）", wt.returncode != 0 and "Read-only" in (wt.stderr or ""),
              (wt.stderr or "")[:100])
        rm = sh(["rm", "-f", MOUNT + "/fuse-live.txt"])
        check("FUSE 删被拒（只读）", rm.returncode != 0 and "Read-only" in (rm.stderr or ""),
              (rm.stderr or "")[:100])

        # 重启服务：卸载/重挂，读还在
        sh(["systemctl", "restart", "aios-worldfs-fuse"])
        time.sleep(4)
        cat3 = sh(["cat", MOUNT + "/fuse-live.txt"])
        check("服务重启后挂载恢复且数据仍在",
              cat3.returncode == 0 and cat3.stdout.strip() == "hello-from-worldfs",
              cat3.stdout[:80])

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
