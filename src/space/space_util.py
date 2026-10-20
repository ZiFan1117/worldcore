# -*- coding: utf-8 -*-
"""★ 个人空间的小工具（C27 拆分：一文件一块）——动作上下文 / 画布 surfaceId 的取值。"""


def act_context(action):
    """★ 取界面动作的上下文：两种形态都认 —— 渲染器实际发的是 {name, context}（平铺）；
    我们旧格式是 {event: {name, context}}。★ 这是「点击没反应」的根因：只认了后者。"""
    if not isinstance(action, dict):
        return {}
    ev = action.get("event")
    if isinstance(ev, dict) and isinstance(ev.get("context"), dict):
        return ev["context"]
    if isinstance(action.get("context"), dict):
        return action["context"]
    return {}


def surface_of(frame):
    """★ 从一帧 A2UI 里取 surfaceId（同呈现的取法）。"""
    if not isinstance(frame, dict):
        return None
    for m in (frame.get("messages") or []):
        cs = m.get("createSurface") or m.get("updateComponents") or {}
        if cs.get("surfaceId"):
            return cs.get("surfaceId")
    return None
