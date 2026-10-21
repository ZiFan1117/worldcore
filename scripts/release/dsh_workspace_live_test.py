#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：DSH 完整 Agent 工作台（workspace steps）。"""
import json
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, "/usr/lib/aios/src/ontology")
import zenoh  # noqa: E402
from bus_auth import open_bus  # noqa: E402

BASE = "http://127.0.0.1:8765"
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

    def ask(self, rid, action, params=None, ticket=None, timeout=30):
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


def main():
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    with urllib.request.urlopen(BASE + "/dsh", timeout=20) as r:
        html = r.read().decode("utf-8", "replace")
    check("/dsh 是 Agent 工作台", "Agent 工作台" in html and "agent.workspace" in html,
          "bytes=%d" % len(html))
    check("页面有任务/步骤/检查器", all(x in html for x in
          ('id="taskInput"', 'id="steps"', 'id="inspector"', 'data-view="workflow"')))

    bus = Bus()
    try:
        a = bus.ask("ws-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        sl = bus.ask("ws-space", "space.login", {"user": "zhang", "ticket": tk}, ticket=tk)
        check("space.login", bool(sl.get("ok")), str(sl.get("why"))[:80])
        w = bus.ask("ws-w0", "agent.workspace", {}, ticket=tk)
        body = (w.get("body") or {}) if w.get("ok") else {}
        check("agent.workspace 可读", bool(w.get("ok")) and isinstance(body.get("steps"), list),
              "steps=%d" % len(body.get("steps") or []))
        la = bus.ask("ws-launch", "agent.launch", {}, ticket=tk)
        check("agent.launch", bool(la.get("ok")), str(la.get("body"))[:80])
        g = bus.ask("ws-guide", "agent.guide",
                    {"instruction": "先看世界状态和屏上有什么，再决定下一步。"}, ticket=tk)
        check("agent.guide", bool(g.get("ok")), str(g.get("body"))[:80])
        time.sleep(55)   # 一轮 45s，等 workspace 有步骤
        w2 = bus.ask("ws-w1", "agent.workspace", {}, ticket=tk)
        b2 = (w2.get("body") or {}) if w2.get("ok") else {}
        steps = b2.get("steps") or []
        kinds = {s.get("kind") for s in steps}
        check("workspace 出现 agent 步骤", bool(steps), "steps=%d kinds=%r" % (len(steps), kinds))
        check("步骤含观察/计划/动作", bool({"observe", "plan"} & kinds),
              "kinds=%r" % kinds)
        units = ["aios-bus", "aios-ontology", "aios-guard", "aios-web", "aios-computer",
                 "aios-presentation", "aios-presentation-render", "aios-space", "aios-agent",
                 "aios-fs", "aios-clock", "aios-recovery", "aios-network", "aios-vault",
                 "aios-worldfs", "aios-worldfs-fuse"]
        n = 0
        for u in units:
            r = subprocess.run(["systemctl", "is-active", u], capture_output=True, text=True)
            if r.stdout.strip() == "active":
                n += 1
        check("16 单元 active", n == 16, "active=%d" % n)
        out["ok"] = all(c["ok"] for c in out["checks"])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
