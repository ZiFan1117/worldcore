# -*- coding: utf-8 -*-
"""★ DSH 的状态/引导小帧（从 agent_llm 拆出，C27 一文件一块）。"""
import json


def status(agent, name, did):
    hb = {}
    try:
        with open(agent.hb_path, encoding="utf-8") as f:
            hb = json.load(f)
    except Exception:
        pass
    last = agent.recent_actions[-1] if agent.recent_actions else None
    return {"name": name, "did": did, "state": "running" if agent.launched else "idle",
            "launched": bool(agent.launched), "round": hb.get("round"),
            "phase": hb.get("phase"), "at": hb.get("at"),
            "heartbeat": hb, "last_action": last, "guide": agent.guide,
            "recent_actions": agent.recent_actions[-8:]}


def guide_ack_frame(agent, build_frame):
    return build_frame([
        {"id": "root", "component": "Column",
         "children": ["g_t", "g_l"]},
        {"id": "g_t", "component": "Text", "text": "**已收到引导**"},
        {"id": "g_l", "component": "Text", "text": str(agent.guide)[:300]},
    ])
