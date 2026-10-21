#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：DSH 桌面控制台（界面→本体→agent→本体→界面）。"""
import json
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
        msg = {"action": {"event": {"name": name, "context": context or {}}}}
        self.z.put(T_ACT, json.dumps(msg, ensure_ascii=False))

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def main():
    bus = Bus()
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    try:
        a = bus.ask("ds-ui-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])

        st = bus.ask("ds-state0", "agent.state", {}, ticket=tk)
        b = st.get("body") or {}
        check("agent.state 可读", bool(st.get("ok")) and b.get("name") is not None,
              "state=%r launched=%r" % (b.get("state"), b.get("launched")))

        g = bus.ask("ds-guide", "agent.guide",
                    {"instruction": "先看世界和屏上有什么，再决定下一步；不要重复最近动作。"},
                    ticket=tk)
        check("agent.guide 被本体收下", bool(g.get("ok")), str(g.get("body"))[:140])
        time.sleep(1)
        st2 = bus.ask("ds-state1", "agent.state", {}, ticket=tk)
        b2 = st2.get("body") or {}
        check("agent.state 看到引导", bool(st2.get("ok")) and
              "先看世界" in str(b2.get("guide") or ""),
              "guide=%r" % b2.get("guide"))

        # 通过本体把空间置活动（拿票后才能点控制台）
        sl = bus.ask("ds-space-login", "space.login", {"user": "zhang", "ticket": tk}, ticket=tk)
        check("space.login", bool(sl.get("ok")), str(sl.get("error") or sl.get("why"))[:100])

        # 模拟点「智能体」图标：world/ui/act → Space → agent.launch/state
        bus.act("space.icon_clicked", {"icon": "ic_agent"})
        time.sleep(2)
        # 模拟控制台刷新按钮：world/ui/act → Space → world/ask agent.state
        bus.act("space.agent_ctl", {"op": "state"})
        time.sleep(2)
        ps = bus.ask("ds-pres", "presentation.state", {}, ticket=tk)
        surf = (ps.get("body") or {}).get("surfaces") or []
        names = [((x or {}).get("surface") or "") for x in surf if isinstance(x, dict)]
        check("桌面出现 DSH 控制台", any("space/agent-console-zhang" in n for n in names),
              "surfaces=%r" % names[-8:])
        check("智能体窗口出现", any("agent/dsh" in n for n in names), "surfaces=%d" % len(names))

        units = ["aios-bus", "aios-ontology", "aios-space", "aios-agent",
                 "aios-presentation", "aios-presentation-render", "aios-computer",
                 "aios-web", "aios-guard", "aios-fs", "aios-clock", "aios-network",
                 "aios-recovery", "aios-vault", "aios-worldfs", "aios-worldfs-fuse"]
        n = 0
        for u in units:
            import subprocess
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
