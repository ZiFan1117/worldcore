# -*- coding: utf-8 -*-
"""★ DSH 动作注册（从 agent_llm 拆出，C27）。"""
import json

ACTIONS = ("agent.launch", "agent.close", "agent.state", "agent.guide",
           "agent.chat", "agent.workspace")


def register(session, name, topic):
    for aid in ACTIONS:
        session.put(topic, json.dumps({
            "action": aid,
            "function": aid.split(".", 1)[-1],
            "registered_by": "agent/" + name,
            "registered_by_kind": "agent",
            "required_roles": ["agent"],
            "kind": ("read" if aid in ("agent.state", "agent.workspace") else "invoke"),
            "why": "DSH 控制台/工作台动作（谁启动谁注册）",
        }, ensure_ascii=False))
