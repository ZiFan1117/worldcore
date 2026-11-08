# -*- coding: utf-8 -*-
"""★ 委托任务画布（任务卡）—— 一文件一块：帧 ＋ 混入（同 confirm_window.py 的形态）。

★ 口径（照作者「界面就是消息」）：
  · 画布上每一条都必须能指回【世界账里真有的一行】：`world/query kind=history` 回的
    `job.*` / `delegate.*` / `agent.*` 记录（★ 动作名以 `world.json` 为准；判据 C125 现取核）；
  · 查询回 0 行 ⇒ 画「还没有任务」（★ 空态也是帧，不是空白）；
  · 按钮只做两件事：★ 重新查（`world/query`）／★ 请世界办事（`world/ask job.start|job.finish|job.cancel`）；
    ★ 点击一律经 `world/ui/act` ⇒ 个人空间 ⇒ 本体；★ 画布不改本地状态、不直接调执行器。
  · 帧过 `src/presentation/frame_schema.py` 的整帧校验（basic catalog）。

★ 数据形状（现取 `world_query.handle` 的 kind=history 分支，2026-11-08）：
  行 ＝ {at, family, kind_of, action, actor, rid, params:{subject,…}, route, code, category, …}
  ★ 结果行（`kind_of=result`）**没有 actor** ⇒ 读闸不向普通人公开（现取）；
    ⇒ 这里只画能看到的那部分，**不替世界补字段、不跨行猜状态**。
"""
from window_frame import wrap_window
from space_util import query_world

SID_PREFIX = "space/delegation-"
CATALOG_ID = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
# ★ 画布认哪些动作：以 world.json 为准（判据 C125 现取核一遍这些前缀下的动作名都在册）
TASK_ACTION_PREFIXES = ("job.", "delegate.", "agent.")
# ★ 按钮让世界办的事（★ 全是 world.json 里在册的动作）
JOB_ACTIONS = {"space.job_start": "job.start",
               "space.job_finish": "job.finish",
               "space.job_cancel": "job.cancel"}
EMPTY_TEXT = "还没有任务"
LAYOUT_RECT = [40, 120, 660, 500]
MAX_ROWS = 40
_PREFIX_LABEL = {"job.": "任务", "delegate.": "委托", "agent.": "智能体"}


def task_rows(rows):
    """★ 只留世界账里真有的 `job.` / `delegate.` / `agent.` 记录（别的动作一律不画）。"""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        act = str(r.get("action") or "")
        if act.startswith(TASK_ACTION_PREFIXES):
            out.append(r)
    return out[-MAX_ROWS:]


def _label(action):
    for prefix, name in _PREFIX_LABEL.items():
        if action.startswith(prefix):
            return name
    return "记录"


def _subject(row):
    p = row.get("params") if isinstance(row.get("params"), dict) else {}
    return str(p.get("subject") or p.get("to") or "")


def _status(row):
    """★ 状态只从【这一行自己的字段】读；★ 不跨行猜（结果行对普通人不公开，见模块头）。"""
    kind = str(row.get("kind_of") or "")
    code = str(row.get("code") or "")
    if kind == "reject":
        return "被拒（%s）" % (code or "?")
    if kind == "result":
        return "完成" if row.get("ok") is True else "被拒（%s）" % (code or "?")
    if kind == "ask":
        return "已提交（本体受理）"
    if kind == "notice":
        return "人的动作"
    return kind or "?"


def _clock(at):
    s = str(at or "")
    return s[11:19] if len(s) >= 19 and s[10] == "T" else s


def _actor(actor):
    s = str(actor or "")
    return s[len("world://"):] if s.startswith("world://") else s


def task_line(row):
    """★ 一条记录 ⇒ 画布上的一行字（时间／谁／动作／对象／结果）。"""
    act = str(row.get("action") or "")
    return "%s ｜ %s ｜ %s ｜ %s ｜ %s ｜ %s" % (
        _label(act), _clock(row.get("at")), _actor(row.get("actor")) or "（无 actor）",
        act or "（无动作）", _subject(row) or "（无 subject）", _status(row))


def _button(bid, label, event, context):
    """★ 一个按钮 ＝ 文字子件 ＋ Button（A2UI：Button 必须 child=文本 id）。"""
    return [
        {"id": bid + "_t", "component": "Text", "text": label},
        {"id": bid, "component": "Button", "child": bid + "_t",
         "action": {"event": {"name": event, "context": context}}},
    ]


def delegation_frame(surface_id, rows):
    """★ 任务卡的 A2UI 帧（basic catalog；空态也是帧）。"""
    kept = task_rows(rows)
    comps = [
        {"id": "root", "component": "Column",
         "children": ["dl_t", "dl_src", "dl_d1", "dl_form", "dl_d2",
                      "dl_list", "dl_d3", "dl_btns"]},
        {"id": "dl_t", "component": "Text", "text": "**委托任务**"},
        {"id": "dl_src", "component": "Text",
         "text": "来源：world/query kind=history ｜ 在册记录 %d 条（job.*／delegate.*／agent.*）"
                 % len(kept)},
        {"id": "dl_d1", "component": "Divider"},
        {"id": "dl_form", "component": "Column",
         "children": ["dl_f_subject", "dl_f_start", "dl_f_job", "dl_f_end"]},
        # ★ TextField 的 value 绑到 dataModel 路径；按钮 context 里给同一个路径 ⇒ 点了才拿得到值
        {"id": "dl_f_subject", "component": "TextField",
         "label": "新任务名（job.start 的 subject）", "value": {"path": "/delegation/subject"}},
        {"id": "dl_f_start", "component": "Row", "children": ["dl_start_b"]},
        {"id": "dl_f_job", "component": "TextField",
         "label": "作业号（job.finish／job.cancel 的 subject）", "value": {"path": "/delegation/job"}},
        {"id": "dl_f_end", "component": "Row", "children": ["dl_finish_b", "dl_cancel_b"]},
        {"id": "dl_d2", "component": "Divider"},
        {"id": "dl_list", "component": "Column", "children": []},
        {"id": "dl_d3", "component": "Divider"},
        {"id": "dl_btns", "component": "Row", "children": ["dl_refresh_b"]},
    ]
    for args in (
            ("dl_start_b", "开始任务", "space.job_start",
             {"subject": {"path": "/delegation/subject"}}),
            ("dl_finish_b", "完成", "space.job_finish",
             {"job": {"path": "/delegation/job"}}),
            ("dl_cancel_b", "取消", "space.job_cancel",
             {"job": {"path": "/delegation/job"}}),
            ("dl_refresh_b", "刷新任务", "space.delegation_refresh", {}),
    ):
        comps.extend(_button(*args))
    listing = []
    for i, row in enumerate(kept):
        rid = "dl_r%d" % i
        listing.append(rid)
        comps.append({"id": rid, "component": "Text", "text": task_line(row)})
    if not listing:                       # ★ 空态也是帧：查询回 0 行 ⇒ 明说「还没有任务」
        listing.append("dl_empty")
        comps.append({"id": "dl_empty", "component": "Text", "text": EMPTY_TEXT})
    for c in comps:
        if c["id"] == "dl_list":
            c["children"] = listing
            break
    return {"version": "v1.0", "name": "委托任务", "messages": [
        {"version": "v1.0", "createSurface": {
            "surfaceId": surface_id, "sendDataModel": True, "catalogId": CATALOG_ID}},
        {"version": "v1.0", "updateComponents": {
            "surfaceId": surface_id,
            "components": wrap_window("委托任务", comps, surface_id)}},
        {"version": "v1.0", "updateDataModel": {
            "surfaceId": surface_id, "path": "/delegation/subject", "value": ""}},
        {"version": "v1.0", "updateDataModel": {
            "surfaceId": surface_id, "path": "/delegation/job", "value": ""}},
    ]}


class DelegationMixin:
    """★ 混入 Space：任务卡的取数与按钮（用 self._ask / self.pending / self.own / self.draw）。"""

    def _delegation_sid(self):
        return SID_PREFIX + self.user

    def open_delegation(self):
        """★ 打开／刷新任务卡：★ 先向本体查（`world/query kind=history`），★ 回话到了才出帧。"""
        rid = query_world(self, "history", 200, "delegation")
        print("[个人空间] ② 查委托任务（world/query kind=history，id=%s）" % rid, flush=True)

    def on_delegation_result(self, data):
        """★ 查询回话 ⇒ 用【回话里的行】出帧（★ 不在这里造任务）。"""
        sid = self._delegation_sid()
        rows = (data or {}).get("rows") or []
        self.own[sid] = {"frame": delegation_frame(sid, rows), "rect": list(LAYOUT_RECT)}
        print("[个人空间] ② 委托任务画布 ⇒ 出（画 %d 条／查询共 %s 条）"
              % (len(task_rows(rows)), (data or {}).get("count")), flush=True)
        self.draw()

    def draw_job(self, event, ctx):
        """★ 任务卡上的按钮：★ 只发 `world/ask`（经本体），★ 不在本地改任何状态。

        ★ 取不到参数时【不拿本地状态顶】—— 什么都不发，并说出来。
        """
        if event not in JOB_ACTIONS:
            return False
        key = "subject" if event == "space.job_start" else "job"
        v = (ctx or {}).get(key)
        val = "" if isinstance(v, dict) else str(v or "")
        if not val:
            print("[个人空间] ③ %s：没拿到参数 %s（★ 画布不改本地状态，也不拿旧值顶）"
                  % (event, key), flush=True)
            return True
        rid = self._ask(JOB_ACTIONS[event], {"subject": val}, "job")
        self.pending[rid] = {"kind": "job"}
        return True

    # ── 接线（★ 从这里挪出来，是为了 space_process 不超 C27 的行数）──
    def open_canvas(self, icon):
        """★ 桌面图标 ⇒ 打开哪块画布（ic_delegation／ic_progress／ic_delegation_panel）。"""
        if icon == "ic_delegation":
            self.open_delegation()
        elif icon == "ic_progress":
            self.open_progress()
        elif icon == "ic_delegation_panel":
            self.open_delegation_panel()

    def handle_canvas_event(self, name, ctx):
        """★ 两块画布的按钮：刷新＝再查；job.* ＝ world/ask。返回 True＝已处理。"""
        if name in JOB_ACTIONS:
            return self.draw_job(name, ctx)
        if name == "space.delegation_refresh":
            self.open_delegation()
            return True
        if name == "space.progress_refresh":
            self.open_progress()
            return True
        return False

    def canvas_result(self, kind, d):
        """★ 两块画布的查询回话（★ 只拿回话里的数据出帧）。返回 True＝已处理。"""
        if kind == "delegation":
            if d.get("ok"):
                self.on_delegation_result(d.get("data") or {})
            else:
                print("[个人空间] ④ 委托任务查询失败：%s"
                      % (d.get("why") or d.get("code")), flush=True)
            return True
        if kind == "progress":
            if d.get("ok"):
                self.on_progress_result(d.get("data") or {})
            else:
                print("[个人空间] ④ 进度事件查询失败：%s"
                      % (d.get("why") or d.get("code")), flush=True)
            return True
        return False

    def on_job_result(self, d):
        """★ 作业动作的回话：画布开着就【再查一次】（★ 数据仍从 world/query 来）。"""
        print("[个人空间] ④ 作业动作回话：ok=%s（%s）"
              % (d.get("ok"), d.get("code") or ""), flush=True)
        if self._delegation_sid() in self.own:
            self.open_delegation()
