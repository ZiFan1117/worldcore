# -*- coding: utf-8 -*-
"""★ DSH Agent 工作台：步骤/工具调用/计划（从 agent_llm 拆出，C27）。"""
import datetime


def step(agent, kind, **kw):
    ev = {"kind": kind, "at": datetime.datetime.now().astimezone()
          .isoformat(timespec="seconds")}
    ev.update(kw)
    agent.steps.append(ev)
    agent.steps = agent.steps[-80:]
    return ev


def workspace(agent, status_fn, name, did):
    st = status_fn(agent, name, did)
    return {"agent": st, "steps": agent.steps[-80:],
            "guide": agent.guide, "launched": bool(agent.launched),
            "available": {"state": ["agent.state"], "guide": ["agent.guide"],
                          "chat": ["agent.chat"], "launch": ["agent.launch"],
                          "close": ["agent.close"]}}
