# -*- coding: utf-8 -*-
"""★ 个人空间的小工具（C27 拆分：一文件一块）——动作上下文／画布 surfaceId 的取值／向本体查一次。"""
import json
import time


def query_world(sp, kind, limit, tag):
    """★ 向本体查一次（任务卡／进度流／委托总览**共用这一条取数方式**，不许各造一套）。

    ★ 一律带票（匿名翻不了账）；`pending[rid]` 记下这是哪一路回话；
    ★ 只把请求发出去：**回话到了才画**（谁画谁负责，本函数不碰帧）。
    """
    rid = "sp-%s-%d" % (tag, int(time.time() * 1000))
    sp.pending[rid] = {"kind": tag}
    q = {"id": rid, "kind": kind, "limit": limit}
    if getattr(sp, "ticket", ""):
        q["ticket"] = sp.ticket
    sp.s.put("world/query", json.dumps(q, ensure_ascii=False))
    return rid


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


def own_window_frame(sid, title, lines):
    """★ 空间自己的一扇窗（统一窗口壳；内容＝几行字）—— 从 space_process 挪来（C27 行数）。"""
    from window_frame import wrap_window
    comps = [{"id": "root", "component": "Column",
              "children": ["o_%d" % i for i in range(len(lines))]}]
    for i, line in enumerate(lines):
        comps.append({"id": "o_%d" % i, "component": "Text", "text": line})
    return {"version": "v1.0", "name": title, "messages": [
        {"version": "v1.0", "createSurface": {"surfaceId": sid}},
        {"version": "v1.0", "updateComponents": {
            "surfaceId": sid, "components": wrap_window(title, comps, sid)}}]}
