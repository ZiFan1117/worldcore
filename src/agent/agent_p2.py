# -*- coding: utf-8 -*-
"""agent 的 P2 call 客户端：file./fs. 动作走 world/call，不再用旧 world/ask。

独立模块（C27）：agent_llm 只保留一行分支。
"""
import time
import uuid

from protocol import sdk
from protocol.keys import T


def act(agent, action, params=None, timeout=25):
    rid = "l-" + uuid.uuid4().hex[:8]
    msg = sdk.build_call("world://agent/" + getattr(agent, "p2_name", "dsh"), "world://ontology",
                         action, params or {}, msg_id=rid)
    agent.s.put(T["call"], sdk.encode(msg))
    for _ in range(int(timeout * 10)):
        if rid in agent.p2_results:
            return agent.p2_results.pop(rid)
        time.sleep(0.1)
    return {"ok": False, "why": "P2 动作超时"}


def install(session, agent):
    def on_result(smp):
        d = sdk.parse(smp.payload.to_string())
        data = d.get("data") or {}
        agent.p2_results[d.get("id")] = {
            "ok": bool(data.get("ok")),
            "body": data.get("result"),
            "why": (data.get("error") or {}).get("detail") if not data.get("ok") else None,
            "p2": True,
        }

    session.declare_subscriber(T["call_result"], on_result)
