# -*- coding: utf-8 -*-
"""★ DSH 动作注册（从 agent_llm 拆出，C27）。"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_HERE)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from protocol import sdk as protocol_sdk  # noqa: E402

ACTIONS = ("agent.launch", "agent.close", "agent.state", "agent.guide",
           "agent.chat", "agent.workspace")


def register(session, name, topic):
    bindings = [{
        "action": aid,
        "function": aid.split(".", 1)[-1],
        "required_roles": ["agent"],
        "registered_by_kind": "agent",
    } for aid in ACTIONS]
    msg = protocol_sdk.build_register(
        "world://agent/" + name,
        "world://ontology",
        {"id": "world://agent/" + name, "object_type": "agent"},
        bindings=bindings,
    )
    session.put(topic, protocol_sdk.encode(msg))
