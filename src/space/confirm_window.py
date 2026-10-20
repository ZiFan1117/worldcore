# -*- coding: utf-8 -*-
"""★ 桌面的确认弹窗（C27 拆分：一文件一块；混入 Space：用 self.own/self.draw/self.pending_confirmation）。

★ 作者（逐字整理）：「不是在语义浏览器上头，再桌面上，你也可以出确认呀」。
★ 窗口帧与语义浏览器同一份确认数据（动作/请求者/摘要/请求号）；三个按钮事件是 `confirm.decide`，
  点了之后由 Space.on_act 以人的身份带票回本体 `confirm.resolve`——桌面不自己发许可。
"""
from window_frame import wrap_window


def confirm_window_frame(sid, c):
    """★ 桌面的确认弹窗（统一窗口壳 ＋ 动作/请求者/摘要 ＋ 三个按钮）。"""
    name = str(c.get("name") or "")
    body = "动作：%s\n请求者：%s\n摘要：%s\n请求：%s" % (
        c.get("action"), c.get("for_actor"), c.get("summary"), name)
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
    return {"version": "v0.9", "name": "guard 确认", "messages": [
        {"version": "v0.9", "createSurface": {"surfaceId": sid}},
        {"version": "v0.9", "updateComponents": {
            "surfaceId": sid,
            "components": wrap_window("guard 确认", comps, sid)}}]}


class ConfirmMixin:
    """★ 混入 Space：桌面确认窗口的显示；点击处理在 Space.on_act（要拼 _ask/票）。"""

    def show_confirm(self, c):
        name = str((c or {}).get("name") or "")
        if not name:
            return
        sid = "space/confirm-" + self.user
        self.pending_confirmation = {"name": name, "confirmation": c, "sid": sid}
        self.own[sid] = {"frame": confirm_window_frame(sid, c),
                         "rect": [340, 120, 600, 280]}
        self.draw()
