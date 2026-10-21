#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：点桌面「智能体」⇒ 经本体 app.open_url 弹出完整 DSH 界面。"""
import json
import subprocess
import sys
import time

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import zenoh  # noqa: E402
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_ACT = "world/ui/act"


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

    def act(self, name, context=None):
        self.z.put(T_ACT, json.dumps({"action": {"event": {
            "name": name, "context": context or {}}}}, ensure_ascii=False))

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

    bus = Bus()
    try:
        a = bus.ask("dk-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        r = bus.ask("dk-space", "space.login", {"user": "zhang", "ticket": tk}, ticket=tk)
        check("space.login", bool(r.get("ok")), str(r.get("why"))[:80])
        # 清一下日志时间基线，模拟点击桌面图标
        t0 = time.time()
        bus.act("space.icon_clicked", {"icon": "ic_agent"})
        time.sleep(5)
        j = sh(["journalctl", "-u", "aios-computer", "--since", "@%d" % int(t0 - 2),
                "--no-pager"])
        log = (j.stdout or "") + (j.stderr or "")
        check("计算机日志出现 app.open_url", "app.open_url" in log, log[-200:])
        check("打开的是 /dsh", "/dsh" in log, [ln for ln in log.splitlines() if "app.open_url" in ln][-2:])
        p = sh(["pgrep", "-af", "firefox"])
        check("浏览器进程带 /dsh", "/dsh" in ((p.stdout or "") + (p.stderr or "")),
              ((p.stdout or "") + (p.stderr or ""))[-200:])
        st = bus.ask("dk-state", "agent.state", {}, ticket=tk)
        body = (st.get("body") or {}) if st.get("ok") else {}
        check("点击同时启动 agent", bool(st.get("ok")) and bool(body.get("name")),
              "launched=%r" % body.get("launched"))
        units = ["aios-bus", "aios-ontology", "aios-guard", "aios-web", "aios-computer",
                 "aios-presentation", "aios-presentation-render", "aios-space", "aios-agent",
                 "aios-fs", "aios-clock", "aios-recovery", "aios-network", "aios-vault",
                 "aios-worldfs", "aios-worldfs-fuse"]
        n = sum(1 for u in units if sh(["systemctl", "is-active", u]).stdout.strip() == "active")
        check("16 单元 active", n == 16, "active=%d" % n)
        out["ok"] = all(c["ok"] for c in out["checks"])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
