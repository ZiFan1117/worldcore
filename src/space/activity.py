# -*- coding: utf-8 -*-
"""★ 活动窗口（P8 事件流）—— 从 `space_process.py` 拆出（C27：一个文件一块）。

★ 作者（逐字整理）：「状态变的时候，两个位置都应该推」「不能是静态的」。
★ 这里只做：收本空间事件 ⇒ 活动窗口实时重画；窗口开关由 space_process 的图标处理。
"""
import json


class ActivityMixin:
    """★ 混入 Space：用 self.events / self.activity_open / self.user / self.own / self._ask。"""

    def on_event(self, sample):
        """★（P8）世界推来的事件：只收本空间的；活动窗口开着就实时重画。"""
        try:
            e = json.loads(sample.payload.to_string())
        except Exception:
            return
        sp = e.get("space") or ""
        if sp and sp != "space:" + self.user:
            return
        self.events.append(e)
        self.events = self.events[-40:]
        if self.activity_open:
            self._draw_activity()

    def _draw_activity(self):
        sid = "space/activity-" + self.user
        lines = ["**活动 · 实时**（世界推来的事件）"]
        for e in self.events[-12:]:
            tail = "ok" if e.get("ok") is True else str(e.get("code") or "")
            lines.append("%s ｜ %s ｜ %s ｜ %s" % (str(e.get("at") or "")[11:19],
                                                   e.get("kind_of") or "",
                                                   e.get("action") or "", tail))
        if len(lines) == 1:
            lines.append("（还没有事件）")
        self.own[sid] = {"frame": self._own_window_frame(sid, "活动 · 实时", lines),
                         "rect": [40, 300, 560, 420]}
        self.draw()

    def toggle_activity(self):
        """★ 点「活动」图标：开/关活动窗口（关窗带理由撤画布）。"""
        self.activity_open = not getattr(self, "activity_open", True)
        if self.activity_open:
            self._draw_activity()
            return
        sid = "space/activity-" + self.user
        self.own.pop(sid, None)
        self._ask("presentation.retract_surface",
                  {"surface": sid, "reason": "关闭活动窗口"}, "retract")
        self.draw()
