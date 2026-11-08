# -*- coding: utf-8 -*-
"""★ 委托监督面板（步骤 3）—— 一文件一块：帧 ＋ 混入（同 delegation_frame／progress_frame 的形态）。

★★ 它是什么（既定结构）：人类模式＝操作台、委托模式＝监督台、混合模式＝交接台。
  ⇒ ★ GUI 在世界这一侧的角色是【监督面板】：**搬功能，不搬 DOM**。
  ★ 为什么不做 iframe／WebView 嵌入（不绕、不搬）：
    · DSH Desktop 的 web 界面**现取回 401（未经授权）**；它是否允许被 iframe 也**未核**；
    · 不绕别人的认证、不搬别人的界面 ⇒ 把「功能」（任务／确认／进度／入口）搬进世界，
      不把别人的页面嵌进来；世界与 DSH 各自是各自的面。

★ 数据从哪来（★ 面板不是第二个数据库，也不是第二个执行器）：
  · 当前任务：`world/query kind=history` 回话里的 `job.*` 行（★ 只画查回来的；0 条 ⇒「还没有任务」）；
  · 最近事件：`world/query kind=events` 回话里的最近 5 条（拒绝也画，带拒绝码／类别）；
  · 待确认：★ 直接读 `space_process` 已有的确认队列（`confirm_window.ConfirmMixin.confirm_queue`），
    ★ 不为面板另造一套计数；
  · 「打开 DSH」：★ `world/ask app.open_url`（`world.json` 现取：参数名 `url`，许可给 `world://user`，
    执行归计算机）；★ 地址只从环境变量 `WORLDCORE_DSH_URL` 读，★ 空 ⇒「未配置」且不出按钮（不可用），
    ★ 不许写死地址。

★ 与 C125 两块画布同源（一条事实一个载体）：
  · 行过滤复用 `delegation_frame.task_rows`（本文件再收窄到 `job.*`）；
  · 一行字复用 `delegation_frame.task_line`／`progress_frame.event_line`；
  · 帧仍过 `src/presentation/frame_schema.py` 的整帧校验（basic catalog），目录 id 复用 `delegation_frame.CATALOG_ID`。
"""
import os

from window_frame import wrap_window
from space_util import query_world
from delegation_frame import (CATALOG_ID, EMPTY_TEXT as TASK_EMPTY, task_line,
                              task_rows)
from progress_frame import EMPTY_TEXT as EVENT_EMPTY, event_line

SID_PREFIX = "space/delegation-panel-"
# ★ 入口地址的唯一来源：环境变量（★ 变量名在本文件只出现这一次）
DSH_ENV = "WORLDCORE_DSH_URL"
# ★ 要请世界办的动作（与 world.json 现取一致）
DSH_ACTION = "app.open_url"
DSH_EVENT = "space.open_dsh"
REFRESH_EVENT = "space.delegation_panel_refresh"
PANEL_TITLE = "委托"
TASK_SECTION = "dp_tasks"
EVENT_SECTION = "dp_events"
PANEL_RECT = [40, 120, 700, 600]
MAX_EVENTS = 5
LAYOUT_RECT = PANEL_RECT


def dsh_url():
    """★ DSH 入口地址：★ 只从环境变量读（不写死；没配 ⇒ 空串）。"""
    return str(os.environ.get(DSH_ENV) or "").strip()


def panel_job_rows(rows):
    """★ 当前任务：只留 history 回话里的 `job.*` 行（★ 复用任务卡的过滤口径再收窄）。"""
    return [r for r in task_rows(rows) if str(r.get("action") or "").startswith("job.")]


def panel_recent_events(events):
    """★ 最近事件：只取回话里的最后 MAX_EVENTS 条（顺序＝回话顺序，不自己排序）。"""
    evs = [e for e in (events or []) if isinstance(e, dict)]
    return evs[-MAX_EVENTS:]


def _button(bid, label, event, context=None):
    """★ 一个按钮 ＝ 文字子件 ＋ Button（A2UI：Button 必须 child=文本 id）。"""
    return [
        {"id": bid + "_t", "component": "Text", "text": label},
        {"id": bid, "component": "Button", "child": bid + "_t",
         "action": {"event": {"name": event, "context": dict(context or {})}}},
    ]


def delegation_panel_frame(surface_id, rows, events, waiting=0, url="", errors=None):
    """★ 委托总览的 A2UI 帧（basic catalog；空态也是帧）。

    ★ `rows`／`events` 必须是 `world/query` 回话里的原样数据（本函数不造数据）；
    ★ `waiting` 是确认队列里的条数（由调用方从已有队列读）；
    ★ `url` 空 ⇒「打开 DSH」只画成一行说明（未配置），★ 不出按钮。
    """
    jobs = panel_job_rows(rows)
    evs = panel_recent_events(events)
    errs = [str(e) for e in (errors or []) if str(e)]
    url = str(url or "").strip()
    status = ("状态：任务 %d 条 ｜ 待确认 %d 条 ｜ 最近事件 %d 条 ｜ 来源 world/query"
              % (len(jobs), int(waiting or 0), len(evs)))
    if not url:
        status += " ｜ DSH 入口未配置"
    if errs:
        status += " ｜ 查询失败：%s" % "、".join(errs)
    comps = [
        {"id": "root", "component": "Column",
         "children": ["dp_t", "dp_status", "dp_d1", "dp_task_t", TASK_SECTION,
                      "dp_d2", "dp_wait_t", "dp_wait", "dp_d3", "dp_ev_t",
                      EVENT_SECTION, "dp_d4", "dp_btns"]},
        {"id": "dp_t", "component": "Text", "text": "**" + PANEL_TITLE + "**"},
        {"id": "dp_status", "component": "Text", "text": status},
        {"id": "dp_d1", "component": "Divider"},
        {"id": "dp_task_t", "component": "Text", "text": "**当前任务**"},
        {"id": TASK_SECTION, "component": "Column", "children": []},
        {"id": "dp_d2", "component": "Divider"},
        {"id": "dp_wait_t", "component": "Text", "text": "**待确认**"},
        {"id": "dp_wait", "component": "Text",
         "text": "待确认：%d 条（来源：桌面确认队列）" % int(waiting or 0)},
        {"id": "dp_d3", "component": "Divider"},
        {"id": "dp_ev_t", "component": "Text", "text": "**最近事件**"},
        {"id": EVENT_SECTION, "component": "Column", "children": []},
        {"id": "dp_d4", "component": "Divider"},
        {"id": "dp_btns", "component": "Row", "children": []},
    ]
    comps.extend(_button("dp_refresh_b", "刷新", REFRESH_EVENT))
    btn_children = ["dp_refresh_b"]
    if url:                                # ★ 配了地址 ⇒ 才出「打开 DSH」按钮
        comps.extend(_button("dp_dsh_b", "打开 DSH", DSH_EVENT))
        btn_children.append("dp_dsh_b")
    else:                                  # ★ 没配 ⇒ 明说「未配置」，且【不可用】（不出按钮）
        comps.append({"id": "dp_dsh_t", "component": "Text",
                      "text": "打开 DSH（未配置）"})
        btn_children.append("dp_dsh_t")
    task_ids, event_ids = [], []
    for i, row in enumerate(jobs):
        cid = "dp_task_%d" % i
        task_ids.append(cid)
        comps.append({"id": cid, "component": "Text", "text": task_line(row)})
    if not task_ids:                       # ★ 空态也是帧：0 条 ⇒ 明说「还没有任务」
        task_ids.append("dp_task_empty")
        comps.append({"id": "dp_task_empty", "component": "Text", "text": TASK_EMPTY})
    for i, ev in enumerate(evs):
        cid = "dp_ev_%d" % i
        event_ids.append(cid)
        comps.append({"id": cid, "component": "Text", "text": event_line(ev)})
    if not event_ids:                      # ★ 空态也是帧：0 条 ⇒ 明说「还没有事件」
        event_ids.append("dp_ev_empty")
        comps.append({"id": "dp_ev_empty", "component": "Text", "text": EVENT_EMPTY})
    for c in comps:                        # ★ 容器的 children 最后一次性接上
        if c["id"] == TASK_SECTION:
            c["children"] = task_ids
        elif c["id"] == EVENT_SECTION:
            c["children"] = event_ids
        elif c["id"] == "dp_btns":
            c["children"] = btn_children
    return {"version": "v1.0", "name": PANEL_TITLE, "messages": [
        {"version": "v1.0", "createSurface": {
            "surfaceId": surface_id, "sendDataModel": True, "catalogId": CATALOG_ID}},
        {"version": "v1.0", "updateComponents": {
            "surfaceId": surface_id,
            "components": wrap_window(PANEL_TITLE, comps, surface_id)}},
    ]}


class DelegationPanelMixin:
    """★ 混入 Space：委托总览的取数与按钮（用 self.s／self.pending／self.own／self.draw）。

    ★ 取数方式与 `DelegationMixin`／`ProgressMixin` 一致：先发 `world/query`（带票），
      回话到了才出帧；★ 本类不订阅事件、不自己攒账。
    """

    def _panel_sid(self):
        return SID_PREFIX + self.user

    def _panel_state(self):
        st = getattr(self, "_delegation_panel", None)
        if st is None:
            st = self._delegation_panel = {"rows": None, "events": None,
                                           "errors": [], "await": {}}
        return st

    def open_delegation_panel(self):
        """★ 打开／刷新总览：★ 两路都先向本体查（history＋events），★ 两路都回话才出帧。"""
        st = self._panel_state()
        st.update({"rows": None, "events": None, "errors": [], "await": {}})
        st["await"]["history"] = query_world(self, "history", 200, "panel-history")
        st["await"]["events"] = query_world(self, "events", 60, "panel-events")
        print("[个人空间] ② 查委托总览（world/query kind=history＋events，id=%s／%s）"
              % (st["await"]["history"], st["await"]["events"]), flush=True)

    def panel_result(self, kind, d):
        """★ 面板两路查询的回话（★ 只用回话里的数据画）。返回 True＝已处理。"""
        if kind not in ("panel-history", "panel-events"):
            return False
        st = self._panel_state()
        which = "history" if kind == "panel-history" else "events"
        key = "rows" if which == "history" else "events"
        if d.get("ok"):
            st[key] = (d.get("data") or {}).get(key) or []
        else:
            st[key] = []
            why = d.get("why") or d.get("code")
            st["errors"].append("%s：%s" % (which, why))
            print("[个人空间] ④ 委托总览的 %s 查询失败：%s" % (which, why), flush=True)
        st["await"].pop(which, None)
        if not st["await"]:                # ★ 两路都到了才出帧（不拿半份数据顶）
            self.draw_delegation_panel()
        return True

    def draw_delegation_panel(self):
        """★ 按【回话数据 ＋ 确认队列】出帧（★ 不在这里查、也不造数据）。"""
        sid = self._panel_sid()
        st = self._panel_state()
        waiting = len(self.confirm_queue())
        url = dsh_url()
        rows = st.get("rows") or []
        events = st.get("events") or []
        self.own[sid] = {"frame": delegation_panel_frame(
            sid, rows, events, waiting, url, st.get("errors")),
            "rect": list(PANEL_RECT)}
        print("[个人空间] ② 委托总览 ⇒ 出（任务 %d 条／待确认 %d 条／事件 %d 条；DSH %s）"
              % (len(panel_job_rows(rows)), waiting, len(panel_recent_events(events)),
                 "已配置" if url else "未配置"), flush=True)
        self.draw()

    def refresh_panel_if_open(self):
        """★ 面板开着 ⇒ 就地重画（待确认条数变了要看得见）；没开就什么都不做。"""
        if self._panel_sid() in self.own:
            self.draw_delegation_panel()

    def open_dsh(self):
        """★ 点「打开 DSH」：★ 只发 `world/ask app.open_url`（经本体；出向归计算机做）。"""
        url = dsh_url()
        if not url:
            print("[个人空间] ③ 打开 DSH：%s 没配 ⇒ 不发（★ 未配置时按钮不可用）" % DSH_ENV,
                  flush=True)
            return False
        rid = self._ask(DSH_ACTION, {"url": url}, "dsh")
        self.pending[rid] = {"kind": "panel-dsh"}
        return True

    def handle_panel_event(self, name, ctx):
        """★ 面板上的按钮：刷新＝再查；打开 DSH＝world/ask。返回 True＝已处理。"""
        if name == REFRESH_EVENT:
            self.open_delegation_panel()
            return True
        if name == DSH_EVENT:
            self.open_dsh()
            return True
        return False

    def on_panel_dsh_result(self, d):
        """★ 「打开 DSH」的回话 ⇒ 如实说出来（成败都不吞）。"""
        print("[个人空间] ④ 打开 DSH 的回话：ok=%s（%s）"
              % (d.get("ok"), d.get("code") or d.get("why") or ""), flush=True)

    def handle_delegation_ask_result(self, kind, d):
        """★ 委托侧请求的回话路由：作业动作（任务卡，C125）＋「打开 DSH」（本面板）。

        ★ C27 一文件一块：路由放这里，space_process 只留一行调用。
        """
        if kind == "job":
            self.on_job_result(d)
            return True
        if kind == "panel-dsh":
            self.on_panel_dsh_result(d)
            return True
        return False
