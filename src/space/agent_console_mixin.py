# -*- coding: utf-8 -*-
"""★ DSH 控制台接进个人空间（从 space_process 拆出，C27 一文件一块）。

★ 链路：A2UI action（space.agent_ctl）→ Space → world/ask → 本体 → agent；
   agent 的回话经 world/ask/result 回 Space，界面再画。
"""
from agent_console import agent_console_frame


class AgentConsoleMixin:
    def _agent_sid(self):
        return "space/agent-console-" + getattr(self, "user", "zhang")

    def open_agent_console(self):
        """★ 点「智能体」图标：开 DSH 控制台（Space 自有 A2UI 窗口）。"""
        sid = self._agent_sid()
        self.own[sid] = {"frame": agent_console_frame(sid, self.agent_status),
                         "rect": [560, 80, 660, 460]}
        self._ask("agent.state", {}, "agent-state")
        self.draw()
        print("[个人空间] ② 开 DSH 控制台 %s（经本体查 agent.state）" % sid, flush=True)

    def refresh_agent_console(self):
        sid = self._agent_sid()
        if sid not in self.own:
            return
        self.own[sid]["frame"] = agent_console_frame(sid, self.agent_status)
        self.draw()

    def handle_agent_ctl(self, name, d, _a):
        """★ 控制台按钮：只发 world/ask（经本体），不直连 agent。"""
        if name != "space.agent_ctl":
            return False
        _ev = _a.get("event") if isinstance(_a, dict) else None
        ctx = (d.get("params") or
               ((_ev or {}).get("context") if isinstance(_ev, dict) else None) or {})
        op = str(ctx.get("op") or "")
        self.agent_status["last_ui"] = op
        if op == "launch":
            self._ask("agent.launch", {}, "agent-launch")
        elif op == "close":
            self._ask("agent.close", {}, "agent-close")
        elif op == "state":
            self._ask("agent.state", {}, "agent-state")
        elif op == "guide":
            ins = str(ctx.get("instruction") or "").strip()
            if ins:
                self._ask("agent.guide", {"instruction": ins}, "agent-guide")
        self.refresh_agent_console()
        return True
