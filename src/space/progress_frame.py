# -*- coding: utf-8 -*-
"""★ 进度／事件流画布 —— 一文件一块：帧 ＋ 混入。

★ 口径：
  · 数据只从 `world/query kind=events` 来（读闸已按身份/空间过滤，见 `world_query.handle`）；
  · 一行 ＝ 一条事件：时间 ｜ actor ｜ 动作 ｜ 类别 ｜ 结果；
    ★ 被拒的也画（`ok=false` ⇒ 「✗ 拒绝（码／类别）」）——★ 不许把红藏起来；
  · 查询回 0 条 ⇒ 画「还没有事件」（空态也是帧）；
  · 按钮只做一件事：重新查（`world/ui/act ⇒ space.progress_refresh ⇒ world/query`）；
    ★ 画布不改本地状态、不直接改执行器。
  · 帧过 `src/presentation/frame_schema.py` 的整帧校验（basic catalog）。

★ 与「活动」窗口（`activity.py`，C45）的分工（★ 一处事实一个载体）：
  · 活动窗口：`world/event` 实时推来的事件，只活在内存里（实时）；
  · 本画布：`world/query kind=events` 从【账】翻出来的快照（掉线以后也看得到、可刷新）。
  ★ 所以本画布不订阅事件、不自己攒状态 —— 它画什么，完全由查询回话决定。
"""
from window_frame import wrap_window
from space_util import query_world

SID_PREFIX = "space/progress-"
CATALOG_ID = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
EMPTY_TEXT = "还没有事件"
LAYOUT_RECT = [700, 120, 520, 520]
MAX_ROWS = 40


def _clock(at):
    s = str(at or "")
    return s[11:19] if len(s) >= 19 and s[10] == "T" else s


def _actor(actor):
    s = str(actor or "")
    return s[len("world://"):] if s.startswith("world://") else s


def event_result(ev):
    """★ 这一条事件的结果：成了／被拒（带码）／只是受理了（不带 ok 的那种）。

    ★ 现取（world_query kind=events）：**拒绝行是 `kind_of=reject` ＋ `code`**，它的 `ok` 是 `null`
      —— 所以先认 `kind_of`，再看 `ok`（只认 `ok` 会把拒绝画成「已提交」）。
    """
    kind = str(ev.get("kind_of") or "")
    ok = ev.get("ok")
    code = str(ev.get("code") or "")
    cat = str(ev.get("category") or "")
    if kind == "reject" or ok is False:
        return "✗ 拒绝（%s／%s）" % (code or "?", cat or "?")
    if ok is True:
        return "✓ 成功"
    if kind == "notice":
        return "人的动作"
    return "…已提交"


def event_line(ev):
    """★ 一条事件 ⇒ 一行字（时间／谁／动作／类别／结果）。"""
    return "%s ｜ %s ｜ %s ｜ %s ｜ %s" % (
        _clock(ev.get("at")), _actor(ev.get("actor")) or "（无 actor）",
        str(ev.get("action") or ev.get("ui_action") or "（无动作）"),
        str(ev.get("kind_of") or ""), event_result(ev))


def _button(bid, label, event):
    return [
        {"id": bid + "_t", "component": "Text", "text": label},
        {"id": bid, "component": "Button", "child": bid + "_t",
         "action": {"event": {"name": event, "context": {}}}},
    ]


def progress_frame(surface_id, events):
    """★ 进度／事件流的 A2UI 帧（basic catalog；空态也是帧）。"""
    evs = [e for e in (events or []) if isinstance(e, dict)][-MAX_ROWS:]
    comps = [
        {"id": "root", "component": "Column",
         "children": ["pg_t", "pg_src", "pg_d1", "pg_list", "pg_d2", "pg_btns"]},
        {"id": "pg_t", "component": "Text", "text": "**进度 · 事件流**"},
        {"id": "pg_src", "component": "Text",
         "text": "来源：world/query kind=events ｜ 最近 %d 条（拒绝也画）" % len(evs)},
        {"id": "pg_d1", "component": "Divider"},
        {"id": "pg_list", "component": "Column", "children": []},
        {"id": "pg_d2", "component": "Divider"},
        {"id": "pg_btns", "component": "Row", "children": ["pg_refresh_b"]},
    ]
    comps.extend(_button("pg_refresh_b", "刷新事件", "space.progress_refresh"))
    listing = []
    for i, ev in enumerate(evs):
        rid = "pg_r%d" % i
        listing.append(rid)
        comps.append({"id": rid, "component": "Text", "text": event_line(ev)})
    if not listing:                       # ★ 空态也是帧：查询回 0 条 ⇒ 明说「还没有事件」
        listing.append("pg_empty")
        comps.append({"id": "pg_empty", "component": "Text", "text": EMPTY_TEXT})
    for c in comps:
        if c["id"] == "pg_list":
            c["children"] = listing
            break
    return {"version": "v1.0", "name": "进度 · 事件流", "messages": [
        {"version": "v1.0", "createSurface": {
            "surfaceId": surface_id, "sendDataModel": True, "catalogId": CATALOG_ID}},
        {"version": "v1.0", "updateComponents": {
            "surfaceId": surface_id,
            "components": wrap_window("进度 · 事件流", comps, surface_id)}},
    ]}


class ProgressMixin:
    """★ 混入 Space：进度画布的取数（用 self.s / self.pending / self.own / self.draw）。"""

    def _progress_sid(self):
        return SID_PREFIX + self.user

    def open_progress(self):
        """★ 打开／刷新进度画布：★ 先向本体查（`world/query kind=events`），★ 回话到了才出帧。"""
        rid = query_world(self, "events", 60, "progress")
        print("[个人空间] ② 查进度事件（world/query kind=events，id=%s）" % rid, flush=True)

    def on_progress_result(self, data):
        """★ 查询回话 ⇒ 用【回话里的事件】出帧（★ 不在这里造事件）。"""
        sid = self._progress_sid()
        evs = (data or {}).get("events") or []
        self.own[sid] = {"frame": progress_frame(sid, evs), "rect": list(LAYOUT_RECT)}
        print("[个人空间] ② 进度事件画布 ⇒ 出（画 %d 条／查询共 %s 条）"
              % (min(len(evs), MAX_ROWS), (data or {}).get("count")), flush=True)
        self.draw()
