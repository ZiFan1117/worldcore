# -*- coding: utf-8 -*-
"""★ 桌面的「本体 · 世界全貌」窗口（C27 拆分：一文件一块；混入 Space）。

★ 作者（逐字整理）：「本体的界面要做得漂亮一点……本体里头的所有信息都要能够看到，
  点击图标以后……最好是桌面的 UI」。
★ 它做什么：点桌面「本体」图标 ⇒ 并行查 world/query（overview/types/actions/history/events）
  ⇒ 把**全部信息**画成一扇带页签（概览/类/接口/关系/动作/账/事件）的桌面窗口。
★ 它不是什么：不裁决、不记账；查询走本体（world/query），窗口只是呈现。
"""
from window_frame import wrap_window

TABS = (("overview", "概览"), ("classes", "类"), ("interfaces", "接口"),
        ("links", "关系"), ("actions", "动作"), ("ledger", "账"), ("events", "事件"))
# ★ 一页放多少行（窗口没有滚动条，用分页保证「所有信息都能看到」）
PAGE_LINES = {"overview": 12, "classes": 10, "interfaces": 12, "links": 12,
              "actions": 12, "ledger": 12, "events": 12}


class OntologyMixin:
    """★ 混入 Space：用 self.s / self.ticket / self.pending / self.own / self.draw。"""

    def open_ontology(self):
        """★ 点「本体」图标：并行查全部信息；到了就画（先到先画，边到边补）。"""
        self.ontology = {}
        self.ontology_tab = "overview"
        self._ont_query("overview", "overview")
        self._ont_query("types", "types")
        self._ont_query("actions", "actions")
        self._ont_query("history", "history", {"limit": 20})
        self._ont_query("events", "events", {"limit": 30})
        log = getattr(self, "log", None)
        if log:
            log("③ 本体窗口：并行查 overview/types/actions/history/events")

    def _ont_query(self, kind, tag, extra=None):
        rid = "sp-o-%s-%d" % (tag, int(__import__("time").time() * 1000))
        self.pending[rid] = {"kind": "ontology-" + tag}
        msg = {"id": rid, "kind": kind}
        if extra:
            msg.update(extra)
        if self.ticket and kind in ("history", "events"):
            msg["ticket"] = self.ticket
        self.s.put("world/query", __import__("json").dumps(msg, ensure_ascii=False))

    def on_ontology_result(self, tag, data):
        self.ontology[tag] = data if isinstance(data, dict) else {}
        self._draw_ontology_window()

    def _tab_row(self, comps):
        children = []
        for tab, label in TABS:
            tid, bid = "ont_tab_%s_t" % tab, "ont_tab_%s_b" % tab
            comps.append({"id": tid, "component": "Text", "text": label})
            comps.append({"id": bid, "component": "Button", "child": tid,
                          "action": {"event": {"name": "space.ontology_tab",
                                               "context": {"tab": tab}}}})
            children.append(bid)
        comps.append({"id": "ont_tabs", "component": "Row", "children": children})
        return "ont_tabs"

    def _lines(self, base, lines):
        ids = []
        for i, line in enumerate(lines):
            cid = "%s_%d" % (base, i)
            comps_line = {"id": cid, "component": "Text", "text": line}
            self_ = getattr(self, "_ont_comps", None)
            if self_ is not None:
                self_.append(comps_line)
            ids.append(cid)
        return ids

    def _content(self):
        """★ 当前页签的内容行（全部信息都从这里能看到）。"""
        d = getattr(self, "ontology", {}) or {}
        ov = d.get("overview") or {}
        c = ov.get("counts") or {}
        lines = []
        tab = getattr(self, "ontology_tab", "overview")
        def short_at(x):
            s = str(x or "")
            return s.split("T")[-1][:8] if "T" in s else s[-8:]

        if tab == "overview":
            lines += [
                "类 %s ／ 接口 %s ／ 关系 %s ／ 在册动作 %s ／ 注册动作 %s ／ 函数 %s ／ 个体 %s"
                % (c.get("classes"), c.get("interfaces"), c.get("links"),
                   c.get("world_actions"), c.get("registry_actions"),
                   c.get("functions"), c.get("individuals")),
            ]
            led = ov.get("ledger") or {}
            codes = led.get("reject_codes") or {}
            lines.append("账 %s 行（坏行 %s）；拒绝码：%s"
                         % (led.get("rows"), led.get("bad_lines"),
                            "、".join("%s×%s" % (k, v) for k, v in codes.items()) or "（无）"))
            for r in (led.get("last") or [])[-8:]:
                lines.append("· %s  %s  %s  %s" % (short_at(r.get("at")), r.get("kind_of"),
                                                    r.get("action") or r.get("kind") or "",
                                                    r.get("actor") or ""))
        elif tab == "classes":
            types = d.get("types") or {}
            for tid, info in (ov.get("classes") or {}).items():
                props = types.get(tid) or []
                lines.append("**%s**  %s 个 ／ 接口 %s ／ provider %s"
                             % (tid, info.get("instances"),
                                "、".join(info.get("interfaces") or []) or "—",
                                info.get("provider") or "—"))
                if props:
                    lines.append("    属性：%s" % "、".join(props))
        elif tab == "interfaces":
            for iid, info in (ov.get("interfaces") or {}).items():
                lines.append("**%s**  必需：%s ／ 实现者：%s"
                             % (iid, "、".join(info.get("required") or []) or "—",
                                "、".join(info.get("implementors") or []) or "—"))
        elif tab == "links":
            for lk in (ov.get("links") or []):
                lines.append("**%s**  %s → %s（%s）"
                             % (lk.get("id"), lk.get("source"), lk.get("target"),
                                lk.get("cardinality")))
        elif tab == "actions":
            a = d.get("actions") or {}
            onto = a.get("ontology") or []
            sysn = [x for x in onto if str(x).startswith("sys.")]
            worldn = [x for x in onto if not str(x).startswith("sys.")]
            lines += ["**在册动作 %s**（sys.* %s ／ 世界 %s）"
                      % (len(onto), len(sysn), len(worldn)),
                      "可用 %s ／ 不支持 %s（计算机报的）"
                      % (len(a.get("available") or []), len(a.get("unsupported") or []))]
            for x in worldn[:18]:
                lines.append("· 世界动作：%s" % x)
            reg = a.get("registry") or []
            lines.append("**注册动作 %s**" % len(reg))
            for x in reg[:18]:
                lines.append("· 注册：%s" % x)
        elif tab == "ledger":
            h = d.get("history") or {}
            lines += ["**账（world/query kind=history）**  本页 %s ／ 总 %s（坏行 %s）"
                      % (h.get("count"), h.get("total"), h.get("bad_lines")),
                      "看账的身份：%s；空间：%s" % (h.get("viewer"), h.get("space"))]
            for r in (h.get("rows") or [])[-20:]:
                lines.append("· %s  %s  %s  %s  %s"
                             % (short_at(r.get("at")), r.get("kind_of"),
                                r.get("action") or "", r.get("actor") or "",
                                r.get("code") or ""))
        elif tab == "events":
            e = d.get("events") or {}
            lines += ["**事件（world/query kind=events）**  %s 条（总 %s）"
                      % (e.get("count"), e.get("total"))]
            for ev in (e.get("events") or [])[-24:]:
                lines.append("· %s  %s  %s  %s"
                             % (short_at(ev.get("at")), ev.get("kind_of"),
                                ev.get("action") or "", ev.get("actor") or ""))
        if not lines:
            lines = ["（数据加载中…）"]
        return lines

    def _page_of(self, tab):
        return int(getattr(self, "ontology_pages", {}).get(tab, 0))

    def on_page_click(self, tab, delta):
        self.ontology_tab = tab
        pages = getattr(self, "ontology_pages", {}) or {}
        pages[tab] = max(0, self._page_of(tab) + int(delta or 0))
        self.ontology_pages = pages
        self._draw_ontology_window()

    def _draw_ontology_window(self):
        d = getattr(self, "ontology", {}) or {}
        ov = d.get("overview") or {}
        c = ov.get("counts") or {}
        sid = "space/ontology-" + self.user
        comps = [
            {"id": "root", "component": "Column", "children": ["ont_head", "ont_sub", "ont_tabs", "ont_body"]},
            {"id": "ont_head", "component": "Text",
             "text": "**🌍 本体 · 世界全貌**（law 在世界里，本窗只读）"},
            {"id": "ont_sub", "component": "Text",
             "text": "类 %s ／ 接口 %s ／ 关系 %s ／ 动作 %s ／ 函数 %s ／ 个体 %s ／ 账 %s 行"
                     % (c.get("classes"), c.get("interfaces"), c.get("links"),
                        c.get("world_actions"), c.get("functions"),
                        c.get("individuals"), (ov.get("ledger") or {}).get("rows"))},
        ]
        self._ont_comps = comps
        self._tab_row(comps)
        tab = getattr(self, "ontology_tab", "overview")
        lines = self._content()
        page_size = PAGE_LINES.get(tab, 14)
        total_pages = max(1, (len(lines) + page_size - 1) // page_size)
        page = min(self._page_of(tab), total_pages - 1)
        pages = getattr(self, "ontology_pages", {}) or {}
        pages[tab] = page
        self.ontology_pages = pages
        body_ids = self._lines("ont_ln", lines[page * page_size:(page + 1) * page_size])
        comps.append({"id": "ont_body", "component": "Card",
                      "child": "ont_body_col"})
        comps.append({"id": "ont_body_col", "component": "Column", "children": body_ids})
        if total_pages > 1:
            comps.append({"id": "ont_page_text", "component": "Text",
                          "text": "第 %d/%d 页" % (page + 1, total_pages)})
            comps.append({"id": "ont_prev_t", "component": "Text", "text": "◀ 上一页"})
            comps.append({"id": "ont_prev_b", "component": "Button", "child": "ont_prev_t",
                          "action": {"event": {"name": "space.ontology_page",
                                               "context": {"tab": tab, "delta": -1}}}})
            comps.append({"id": "ont_next_t", "component": "Text", "text": "下一页 ▶"})
            comps.append({"id": "ont_next_b", "component": "Button", "child": "ont_next_t",
                          "action": {"event": {"name": "space.ontology_page",
                                               "context": {"tab": tab, "delta": 1}}}})
            comps.append({"id": "ont_pager", "component": "Row",
                          "children": ["ont_prev_b", "ont_page_text", "ont_next_b"]})
            comps[0]["children"].append("ont_pager")
        self._ont_comps = None
        frame = {"version": "v0.9", "name": "本体 · 世界全貌", "messages": [
            {"version": "v0.9", "createSurface": {"surfaceId": sid}},
            {"version": "v0.9", "updateComponents": {
                "surfaceId": sid,
                "components": wrap_window("本体 · 世界全貌", comps, sid)}}]}
        self.own[sid] = {"frame": frame, "rect": [120, 84, 1040, 640]}
        self.draw()

    def on_tab_click(self, tab):
        if tab in dict(TABS):
            self.ontology_tab = tab
            self._draw_ontology_window()
