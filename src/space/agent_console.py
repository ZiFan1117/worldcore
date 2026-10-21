# -*- coding: utf-8 -*-
"""★ DSH 的桌面控制台窗口（Space 自有；A2UI 帧）。

★ 交互只走：界面 → A2UI action → presentation → world/ui/act → Space
   → world/ask（agent.state / agent.guide / agent.launch / close）→ 本体 → agent；
   agent 的返回经 world/ask/result 或 world/notice 回界面。
"""
from window_frame import wrap_window


def _btn(bid, label, op, instruction=None):
    ctx = {"op": op}
    if instruction:
        ctx["instruction"] = instruction
    return [
        {"id": bid + "_t", "component": "Text", "text": label},
        {"id": bid, "component": "Button", "child": bid + "_t",
         "action": {"event": {"name": "space.agent_ctl", "context": ctx}}},
    ]


def agent_console_frame(surface_id, status=None):
    st = status or {}
    alive = st.get("state") or "unknown"
    launched = "已启动" if st.get("launched") else "未启动"
    hb = st.get("heartbeat") or {}
    line = "状态：%s ／ 窗口：%s ／ 轮次：%s ／ 心跳：%s" % (
        alive, launched, st.get("round", hb.get("round", "?")), st.get("at", "?"))
    last = st.get("last_action") or "（还没有动作）"
    guide = st.get("guide") or "（没有引导）"
    comps = [
        {"id": "root", "component": "Column",
         "children": ["ac_t", "ac_s", "ac_l", "ac_g", "ac_b1", "ac_b2"]},
        {"id": "ac_t", "component": "Text", "text": "**DSH 智能体控制台**"},
        {"id": "ac_s", "component": "Text", "text": line},
        {"id": "ac_l", "component": "Text", "text": "最近动作：" + str(last)[:180]},
        {"id": "ac_g", "component": "Text", "text": "当前引导：" + str(guide)[:180]},
        {"id": "ac_b1", "component": "Row",
         "children": ["ac_launch", "ac_state", "ac_close"]},
        {"id": "ac_b2", "component": "Row",
         "children": ["ac_g1", "ac_g2", "ac_g3"]},
    ]
    for bid, label, op, ins in (
            ("ac_launch", "启动智能体", "launch", None),
            ("ac_state", "刷新状态", "state", None),
            ("ac_close", "关智能体窗口", "close", None),
            ("ac_g1", "引导：先看世界", "guide",
             "先看世界状态、可用动作和最近事件，再决定下一步；不要重复最近动作。"),
            ("ac_g2", "引导：看文件", "guide", "用 file.* 只读动作看看 /var/lib/aios 与 /root/aios。"),
            ("ac_g3", "引导：看网络", "guide", "用 network.addresses/routes/connections 看看本机网络。"),
    ):
        comps.extend(_btn(bid, label, op, ins))
    return {"version": "v1.0", "name": "DSH 智能体控制台",
            "messages": [
                {"version": "v1.0", "createSurface": {
                    "surfaceId": surface_id, "sendDataModel": True,
                    "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"}},
                {"version": "v1.0", "updateComponents": {
                    "surfaceId": surface_id,
                    "components": wrap_window("DSH 智能体控制台", comps, surface_id)}}]}
