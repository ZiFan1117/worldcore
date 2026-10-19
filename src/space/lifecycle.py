# -*- coding: utf-8 -*-
"""★ 空间生命周期（退出登录）—— 从 `space_process.py` 拆出（C27：一个文件一块）。"""
import json


class LifecycleMixin:
    """★ 混入 Space：用 self.ticket / self.state / self.guests / self.own / self.s / self._ask。"""

    def logout(self):
        """★ 退出：销票（经本体）⇒ 空间 inactive ⇒ 请呈现回登录画布（经本体转）。"""
        if self.ticket:
            self._ask("identity.revoke", {"ticket": self.ticket}, "revoke")
        self.ticket = ""
        self.state = "inactive"
        self.guests.clear()
        self.own.clear()
        self.events.clear()
        self.activity_open = False
        self.s.put("world/appear", json.dumps({
            "class": "space", "name": self.user, "owner": self.user, "state": "inactive",
            "reporter": "world://space/" + self.user}, ensure_ascii=False))
        self.s.put("world/notice", json.dumps({
            "kind": "space.logout", "by": "world://space/" + self.user,
            "about": "退出登录"}, ensure_ascii=False))
        print("[个人空间] ③ 退出：票已销、空间 inactive、请呈现回登录画布", flush=True)
