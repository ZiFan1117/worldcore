# -*- coding: utf-8 -*-
"""★ 桌面的确认弹窗（C27 拆分：一文件一块；混入 Space：用 self.own/self.draw/self.pending_confirmation）。

★ 作者（逐字整理）：「不是在语义浏览器上头，再桌面上，你也可以出确认呀」。
★ 窗口帧与语义浏览器同一份确认数据（动作/请求者/摘要/请求号）；三个按钮事件是 `confirm.decide`，
  点了之后由 Space.on_act 以人的身份带票回本体 `confirm.resolve`——桌面不自己发许可。

★★ 队列（2026-11-08 补）：原来一个 `pending_confirmation` 顶掉前一条 —— 两条 confirm.request
  挨着到，第一条的窗口就【消失】了，而本体里它仍是 pending（**静默丢失，最坏的一类**）。
  现在：待确认的按到达顺序排队，窗口显示最新一条并注明「还有 N 条待确认」；签完一条自动换下一条。
  ★ 这个队列只是【界面上的排队】，不是裁决：每条仍然要人点、仍然回本体 `confirm.resolve`（带票）。
"""
from window_frame import wrap_window

SID_PREFIX = "space/confirm-"


def confirm_window_frame(sid, c, waiting=0):
    """★ 桌面的确认弹窗（统一窗口壳 ＋ 动作/请求者/摘要 ＋ 三个按钮）。"""
    name = str(c.get("name") or "")
    body = "动作：%s\n请求者：%s\n摘要：%s\n请求：%s" % (
        c.get("action"), c.get("for_actor"), c.get("summary"), name)
    if waiting:                     # ★ 还有几条在排队：说出来，别让它们悄悄消失
        body += "\n还有 %d 条待确认（签完这条自动换下一条）" % waiting
    comps = [
        {"id": "root", "component": "Column",
         "children": ["cf_title", "cf_body", "cf_btns"]},
        {"id": "cf_title", "component": "Text", "text": "**guard 请求确认：要不要允许？**"},
        {"id": "cf_body", "component": "Text", "text": body},
        {"id": "cf_btns", "component": "Row",
         "children": ["cf_deny_b", "cf_once_b", "cf_deleg_b"]},
    ]
    for bid, tid, label, decision in (
            ("cf_deny_b", "cf_deny_t", "拒绝", "deny"),
            ("cf_once_b", "cf_once_t", "允许一次", "allow_once"),
            ("cf_deleg_b", "cf_deleg_t", "允许并委托", "allow_delegation")):
        comps.append({"id": tid, "component": "Text", "text": label})
        comps.append({"id": bid, "component": "Button", "child": tid,
                      "action": {"event": {
                          "name": "confirm.decide",
                          "context": {"confirmation": name, "decision": decision}}}})
    return {"version": "v1.0", "name": "guard 确认", "messages": [
        {"version": "v1.0", "createSurface": {"surfaceId": sid}},
        {"version": "v1.0", "updateComponents": {
            "surfaceId": sid,
            "components": wrap_window("guard 确认", comps, sid)}}]}


class ConfirmMixin:
    """★ 混入 Space：桌面确认窗口的显示与排队；点击处理在 Space.on_act（要拼 _ask/票）。"""

    def confirm_queue(self):
        """★ 待确认队列（按到达顺序；同一条请求号只排一次）。"""
        q = getattr(self, "_confirm_queue", None)
        if q is None:
            q = self._confirm_queue = []
        return q

    def show_confirm(self, c):
        """★ 收到一条 confirm.request：排队 ⇒ 画（★ 最新那条在上）。"""
        name = str((c or {}).get("name") or "")
        if not name:
            return
        q = self.confirm_queue()
        if not any(str(x.get("name") or "") == name for x in q):
            q.append(c)
        self._draw_confirm()

    def _draw_confirm(self):
        """★ 按队列画：有就画最新一条（带排队数），没有就撤窗口。"""
        sid = SID_PREFIX + self.user
        q = self.confirm_queue()
        if not q:
            self.pending_confirmation = None
            if self.own.pop(sid, None) is not None:
                self.draw()
            self._refresh_panel()
            return
        c = q[-1]
        self.pending_confirmation = {"name": str(c.get("name") or ""), "confirmation": c, "sid": sid}
        self.own[sid] = {"frame": confirm_window_frame(sid, c, waiting=len(q) - 1),
                         "rect": [340, 120, 600, 300]}
        self.draw()
        self._refresh_panel()

    def _refresh_panel(self):
        """★ 委托监督面板开着就叫它重画（待确认条数变了要看得见）；没开就什么都不做。"""
        refresh = getattr(self, "refresh_panel_if_open", None)
        if callable(refresh):
            refresh()

    def resolve_confirmation(self, name, decision):
        """★ 人点了一条：★ 以人的身份、带票回本体 `confirm.resolve`（★ 桌面不自己发许可），再换下一条。"""
        name = str(name or "")
        q = self.confirm_queue()
        self._confirm_queue = [x for x in q if str(x.get("name") or "") != name]
        self.pending_confirmation = None
        if name:
            rid = self._ask("confirm.resolve",
                            {"name": name, "decision": decision, "reason": "桌面弹窗确认"},
                            "cf")
            self.pending[rid] = {"kind": "confirm"}
        self._draw_confirm()
        return name
