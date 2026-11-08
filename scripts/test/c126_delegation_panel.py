#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C126 —— **委托监督面板**（步骤 3；「打开 DSH」入口，不做 iframe／WebView 嵌入）。

★ 口径（既定结构：人类模式＝操作台、委托模式＝监督台、混合模式＝交接台）：
  · DSH Desktop 的 web 界面现取回 **401（未经授权）**，它是否允许被 iframe **未核**
    ⇒ 不绕别人的认证、不搬别人的界面；**把功能搬进世界，不搬 DOM**；
    GUI 在世界这一侧的角色是【监督面板】。
  · 面板不是第二个数据库：当前任务只来自 `world/query kind=history` 的 `job.*` 行，
    最近事件只来自 `world/query kind=events`；待确认条数只来自桌面确认队列（已有机制）。
  · 「打开 DSH」只经本体：`world/ask app.open_url`（参数名 `url`，`world.json` 现取；
    许可给 `world://user`，执行归计算机）；地址只从环境变量 `WORLDCORE_DSH_URL` 读
    （★ 写死 ⇒ 红）；空 ⇒ 显示「未配置」且不出按钮（不可用）。

判的是【事实侧】（真造帧、真走 Space、真查一次真账、真点一次按钮）：
  (1) 面板数据必须来自查询：开面板先发 `world/query kind=history` ＋ `kind=events`（带票），
      两路都回话才出帧；★ 本地拼假任务／假事件 ⇒ 红；
  (2) 地址只从 `WORLDCORE_DSH_URL` 读；★ 源码里写死地址（URL 字面量）⇒ 红；用环境变量 ⇒ 绿（正控）；
  (3) 「打开 DSH」必须发 `world/ask app.open_url`（带票、人的身份、`url` 参数对）；
      ★ 绕过本体（直接调执行器／本地开）⇒ 红；空地址 ⇒ 不出按钮、点了也不发；
  (4) 空态（0 条说「还没有任务」「还没有事件」）与整帧过 `frame_schema`；
      ★ 缺空态／帧不合目录 ⇒ 红；正常帧 ⇒ 绿（正控）；
  (5) 最近事件只画最近 5 条；`history` 里的 `delegate.*`／`agent.*` 不进「当前任务」；
      待确认条数随确认队列变（面板开着就重画）。

限度（★ 如实）：
  · 本判据在**宿主**上跑：账本／注册表／对象库指到临时处（`_proc_helper.temp_dataset`），不碰真机数据面；
  · 它判【帧／取数／按钮去向／空态】；**屏上画成什么样**（像素）与 DSH 那侧真起没起，
    要 VM 上的真截图与真机 e2e，另算；
  · 它**不判** `WORLDCORE_DSH_URL` 指向的服务是否可用（那是 DSH 的事，本判据不替它说话），
    也不判 DSH 的 401 是否解除（本步骤不绕认证）。

用法：
  python scripts/test/c126_delegation_panel.py              跑真仓库
  python scripts/test/c126_delegation_panel.py --self-test  反例自检
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import _proc_helper as H  # noqa: E402

NAME = "C126 委托监督面板（任务／待确认／最近事件／「打开 DSH」入口）"
JSON_ACTIONS = os.path.join(H.SRC, "ontology", "world.json")
DP_SRC = os.path.join(H.SRC, "space", "delegation_panel.py")
EMPTY_TASK = "还没有任务"
EMPTY_EVENT = "还没有事件"
DSH_ENV = "WORLDCORE_DSH_URL"
DSH_EVENT = "space.open_dsh"
# ★ 判据自己用的假地址（只在自检里用；被测源码里不许出现字面量）
FAKE_DSH = "http://dsh.example.invalid:51026/"


# ── 取件的小工具 ─────────────────────────────────────────────
def frame_components(frame):
    """★ 帧里 id -> 组件（判「面板上到底写了什么」按结构取，不按字符串第一处取）。"""
    out = {}
    for m in (frame or {}).get("messages") or []:
        for c in (m.get("updateComponents") or {}).get("components") or []:
            if isinstance(c, dict) and c.get("id"):
                out[c["id"]] = c
    return out


def frame_texts(frame):
    """★ 帧里所有 Text 的 text。"""
    return [str(c.get("text") or "") for c in frame_components(frame).values()
            if c.get("component") == "Text"]


def section_texts(frame, container):
    """★ 某一节（容器的 children）里画出来的字 —— 分节取，避免两节互相串。"""
    comps = frame_components(frame)
    kids = (comps.get(container) or {}).get("children") or []
    out = []
    for k in kids:
        c = comps.get(k)
        if isinstance(c, dict) and c.get("component") == "Text":
            out.append(str(c.get("text") or ""))
    return out


def frame_buttons(frame):
    """★ 帧里所有按钮：id -> (事件名, context)。"""
    out = {}
    for cid, c in frame_components(frame).items():
        if c.get("component") != "Button":
            continue
        ev = ((c.get("action") or {}).get("event") or {})
        out[cid] = (ev.get("name"), ev.get("context") or {})
    return out


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_world_actions():
    """★ 动作名的唯一出处：`src/ontology/world.json`。"""
    with open(JSON_ACTIONS, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return {a.get("id") for a in (doc.get("actions") or []) if a.get("id")}


# ── 纯函数判据（自带红例可喂）────────────────────────────────
def judge_frame_valid(frame, fs):
    """(4) 整帧校验：不合目录 ⇒ 列出来（★ 不静默过滤）。"""
    return ["帧过不了 frame_schema：%s" % p for p in fs.validate_frame(frame)]


def judge_empty_state(texts, n_rows, token):
    """(4) 空态：0 条要有「还没有…」，有条就不该再写空态。"""
    bad = []
    present = any(token in t for t in texts)
    if n_rows == 0 and not present:
        bad.append("0 条却缺空态「%s」（★ 空态也是帧）" % token)
    if n_rows > 0 and present:
        bad.append("有 %d 条却还写着空态「%s」（画布与查询不符）" % (n_rows, token))
    return bad


def judge_provenance(task_texts, event_texts, job_rows, recent_events, known_actions):
    """(1)(5) 每一行都要能指回查询回话；★ 画了回话里没有的动作 ⇒ 硬编码。"""
    bad = []
    task_blob = "\n".join(task_texts)
    event_blob = "\n".join(event_texts)
    shown = set()
    for r in job_rows:
        act = str(r.get("action") or "")
        clock = str(r.get("at") or "")[11:19]
        shown.add(act)
        if act and act not in task_blob:
            bad.append("查询回来的任务没画出来：%s" % act)
        elif clock and clock not in task_blob:
            bad.append("查询回来的任务时间没画出来：%s（%s）" % (clock, act))
    for ev in recent_events:
        act = str(ev.get("action") or ev.get("ui_action") or "")
        shown.add(act)
        if act and act not in event_blob:
            bad.append("查询回来的事件没画出来：%s" % act)
        code = str(ev.get("code") or "")
        if code and code not in event_blob:
            bad.append("被拒事件没画出拒绝码：%s（★ 拒绝也要显示）" % code)
    for act in sorted(known_actions):
        if act in task_blob and act not in shown:
            bad.append("「当前任务」画了查询结果里没有的动作 %s（★ 硬编码假任务）" % act)
        if act in event_blob and act not in shown:
            bad.append("「最近事件」画了查询结果里没有的动作 %s（★ 硬编码假事件）" % act)
    return bad


def judge_task_scope(task_texts):
    """(5) 「当前任务」只画 `job.*`：history 里的 delegate.*／agent.* 不许混进来。"""
    bad = []
    for prefix in ("delegate.", "agent."):
        hit = [t for t in task_texts if prefix in t]
        if hit:
            bad.append("「当前任务」画了不属于 job.* 的记录：%s" % hit[0])
    return bad


def judge_event_window(event_texts, events, limit=5):
    """(5) 最近事件只画最近 5 条：更老的几条不许出现。"""
    bad = []
    evs = [e for e in (events or []) if isinstance(e, dict)]
    for ev in evs[:-limit]:
        clock = str(ev.get("at") or "")[11:19]
        if clock and any(clock in t for t in event_texts):
            bad.append("「最近事件」画了超过最近 %d 条的老事件（%s）" % (limit, clock))
    return bad


def judge_url_source(text):
    """(2) 地址不许写死：源码里出现 URL 字面量 ⇒ 红；没有从环境变量读 ⇒ 红。"""
    bad = []
    if "http" in (text or "").lower():
        bad.append("源码里出现 URL 字面量（★ DSH 地址不许写死）")
    if DSH_ENV not in (text or ""):
        bad.append("没有从环境变量 %s 读 DSH 地址" % DSH_ENV)
    return bad


def judge_declared(mod, world_actions):
    """(3) 面板要请世界办的动作必须在 `world.json` 在册；环境变量名必须是约定的那一个。"""
    bad = []
    act = getattr(mod, "DSH_ACTION", "")
    if act not in world_actions:
        bad.append("面板用了不在 world.json 的动作名：%r" % (act,))
    if getattr(mod, "DSH_ENV", "") != DSH_ENV:
        bad.append("面板读的环境变量不是 %s：%r" % (DSH_ENV, getattr(mod, "DSH_ENV", "")))
    return bad


# ── 行为判据（要一个真 Space／假 Space）──────────────────────
def judge_panel_open(sp, opener, sid):
    """(1) 开面板 ⇒ 两路查询（history＋events，带票）；回话没到不许出帧。"""
    bad = []
    before = len(sp.s.puts)
    own_before = set(getattr(sp, "own", None) or {})
    opener(sp)
    qs = [json.loads(p) for t, p in sp.s.puts[before:] if t == "world/query"]
    if not qs:
        bad.append("开面板没有发 world/query（★ 数据不是查询来的）")
        return qs, bad
    kinds = {q.get("kind") for q in qs}
    for want in ("history", "events"):
        if want not in kinds:
            bad.append("面板没查 kind=%s（★ 任务与事件各一路）" % want)
    for q in qs:
        if not q.get("ticket"):
            bad.append("查询 kind=%r 没带票（★ 匿名翻不了账，读闸会拒）" % q.get("kind"))
        if q.get("limit") is None:
            bad.append("查询 kind=%r 没给 limit" % q.get("kind"))
    if set(getattr(sp, "own", None) or {}) - own_before:
        bad.append("查询回话还没到就出了帧（★ 帧必须用回话里的数据画）")
    return qs, bad


def judge_dsh_ask(puts, want_url, world_actions):
    """(3) 点了「打开 DSH」：★ 只许发 `world/ask app.open_url`（带票、人的身份、url 对）。"""
    bad = []
    asks = [json.loads(p) for t, p in puts if t == "world/ask"]
    hit = [a for a in asks if a.get("action") == "app.open_url"]
    if not hit:
        bad.append("点了「打开 DSH」没发 world/ask app.open_url（★ 绕过本体直接开）")
        return bad
    a = hit[-1]
    if "app.open_url" not in world_actions:
        bad.append("app.open_url 不在 world.json（★ 面板自造动作名）")
    if (a.get("params") or {}).get("url") != want_url:
        bad.append("app.open_url 的 url 参数不对：%r（★ 该发环境变量里的 %r）"
                   % ((a.get("params") or {}).get("url"), want_url))
    if not a.get("ticket"):
        bad.append("app.open_url 没带票（★ 空间不能自己发许可）")
    if not str(a.get("actor") or "").startswith("world://user/"):
        bad.append("app.open_url 不是人的身份：%r" % (a.get("actor"),))
    return bad


def judge_dsh_button(frame):
    """(2)(3) 「打开 DSH」按钮：配了地址才出，事件名对。"""
    bad = []
    btns = frame_buttons(frame)
    ev = (btns.get("dp_dsh_b") or (None, {}))[0]
    if ev != DSH_EVENT:
        bad.append("配了地址却没有「打开 DSH」按钮（或事件名不是 %s：%r）" % (DSH_EVENT, ev))
    return bad


def judge_unconfigured(frame):
    """(2)(3) 地址空：★ 必须写「未配置」，且【不出】可点的「打开 DSH」按钮。"""
    bad = []
    if "未配置" not in "\n".join(frame_texts(frame)):
        bad.append("地址没配却没说「未配置」")
    names = {n for n, _ in frame_buttons(frame).values()}
    if DSH_EVENT in names:
        bad.append("地址没配却仍出了「打开 DSH」按钮（★ 不可用要真不可用）")
    return bad


def _reply(sp, qs, rows, events):
    for q in qs or []:
        key = "rows" if q.get("kind") == "history" else "events"
        data = rows if key == "rows" else events
        sp.on_query_result(H.Sample({"id": q.get("id"), "ok": True, "data": {key: data}}))


def _ask_and_reply(op, w, mid, action, params, actor, ticket):
    s = H.Session()
    op._ask_and_forward(H.Sample({"id": mid, "action": action, "params": params,
                                  "actor": actor, "ticket": ticket}), w, s)
    return json.loads(s.last_on(op.T_ASK_RESULT) or "{}")


# ── 真数据：真世界真账，再从 world/query 把行／事件取回来 ─────
def real_rows_and_events(op):
    """★ 在本体里真跑几条 job/delegate 动作（含一条被拒），再真查 history／events。"""
    w = H.new_world()
    s0 = H.Session()
    op._ask_and_forward(H.Sample({"id": "c126-auth", "action": "identity.authenticate",
                                  "params": {"user": "zhang", "secret": "0"},
                                  "actor": "world://surface/s0"}), w, s0)
    body = (json.loads(s0.last_on(op.T_ASK_RESULT) or "{}").get("body") or {})
    ticket = body.get("ticket") or ""
    who = "world://user/zhang"
    _ask_and_reply(op, w, "c126-j1", "job.start", {"subject": "写报告"}, who, ticket)
    _ask_and_reply(op, w, "c126-j2", "job.finish", {"subject": "job-not-there"}, who, ticket)
    expires = (datetime.datetime.now().astimezone()
               + datetime.timedelta(hours=1)).isoformat(timespec="seconds")
    _ask_and_reply(op, w, "c126-d1", "delegate.grant",
                   {"to": "world://agent/dsh", "action": "sys.AptInstall",
                    "expires": expires, "max_uses": 1}, who, ticket)
    out = {}
    for kind, key in (("history", "rows"), ("events", "events")):
        s = H.Session()
        op.world_query.handle(H.Sample({"id": "c126-" + kind, "kind": kind,
                                        "ticket": ticket, "limit": 100}), w, s)
        d = json.loads(s.last_on("world/query/result") or "{}")
        if not d.get("ok"):
            raise RuntimeError("查 %s 失败：%r" % (kind, d.get("why")))
        out[key] = (d.get("data") or {}).get(key) or []
    return out["rows"], out["events"], ticket


def _set_env(key, value):
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


def run():
    H.temp_dataset()
    op = H.import_ontology_process()
    H.add_paths("space", "presentation")
    import frame_schema as fs  # noqa: E402
    import delegation_panel as dp  # noqa: E402
    spm = H.import_space_process()

    old_env = os.environ.get(DSH_ENV)
    _set_env(DSH_ENV, None)
    try:
        world_actions = load_world_actions()
        bad = judge_url_source(read_text(DP_SRC)) + judge_declared(dp, world_actions)
        rows, events, ticket = real_rows_and_events(op)
        job_rows = dp.panel_job_rows(rows)
        sp = spm.Space(H.Session())
        sp.draw = lambda: None
        sp.ticket = ticket
        sid = dp.SID_PREFIX + sp.user

        # (1)(4) 两路空回话 ⇒ 空态帧（★ 回话之前不许出帧）
        qs, b = judge_panel_open(sp, lambda s: s.open_delegation_panel(), sid)
        bad += b
        _reply(sp, qs, [], [])
        if sid not in sp.own:
            bad.append("两路回话都到了却没出帧")
            empty = None
        else:
            empty = sp.own[sid]["frame"]
            bad += judge_frame_valid(empty, fs)
            bad += judge_empty_state(section_texts(empty, dp.TASK_SECTION), 0, EMPTY_TASK)
            bad += judge_empty_state(section_texts(empty, dp.EVENT_SECTION), 0, EMPTY_EVENT)

        # 确认队列：两条待确认 ⇒ 面板要如实写 2 条（队列是已有机制）
        for i in (1, 2):
            sp.on_frame(H.Sample({"kind": "confirm.request", "by": "world://guard",
                                  "confirmation": {"name": "c126-cf-%d" % i,
                                                   "for_actor": "world://agent/dsh",
                                                   "action": "sys.AptInstall",
                                                   "summary": "s%d" % i}}))
        # (1)(5) 真回话 ⇒ 数据帧
        qs, b = judge_panel_open(sp, lambda s: s.open_delegation_panel(), sid)
        bad += b
        _reply(sp, qs, rows, events)
        if sid not in sp.own:
            bad.append("真回话到了却没出帧")
            frame = None
        else:
            frame = sp.own[sid]["frame"]
            task_texts = section_texts(frame, dp.TASK_SECTION)
            event_texts = section_texts(frame, dp.EVENT_SECTION)
            recent = dp.panel_recent_events(events)
            bad += judge_frame_valid(frame, fs)
            bad += judge_empty_state(task_texts, len(job_rows), EMPTY_TASK)
            bad += judge_empty_state(event_texts, len(recent), EMPTY_EVENT)
            bad += judge_provenance(task_texts, event_texts, job_rows, recent, world_actions)
            bad += judge_task_scope(task_texts)
            if len(task_texts) != len(job_rows):
                bad.append("「当前任务」画了 %d 条，查询回 %d 条 job.*（★ 多画／少画）"
                           % (len(task_texts), len(job_rows)))
            if len(event_texts) != len(recent):
                bad.append("「最近事件」画了 %d 条，最近 5 条里只有 %d 条"
                           % (len(event_texts), len(recent)))
            if "待确认：2 条" not in "\n".join(frame_texts(frame)):
                bad.append("面板没写出「待确认：2 条」（★ 条数要来自确认队列）")
            # 第三条确认 ⇒ 面板开着就该重画（计数是活的，不是快照）
            sp.on_frame(H.Sample({"kind": "confirm.request", "by": "world://guard",
                                  "confirmation": {"name": "c126-cf-3",
                                                   "for_actor": "world://agent/dsh",
                                                   "action": "sys.AptInstall",
                                                   "summary": "s3"}}))
            if "待确认：3 条" not in "\n".join(frame_texts(sp.own[sid]["frame"])):
                bad.append("第三条确认到了，面板仍写旧条数（★ 计数没跟确认队列走）")

        # (2)(3) 地址空：写「未配置」、无按钮、点了也不发
        sp.draw_delegation_panel()
        frame = sp.own[sid]["frame"]
        bad += judge_unconfigured(frame)
        before = len(sp.s.puts)
        sp.on_act(H.Sample({"action": {"event": {"name": DSH_EVENT, "context": {}}}}))
        if [1 for t, _ in sp.s.puts[before:] if t == "world/ask"]:
            bad.append("地址没配，点「打开 DSH」却发了 world/ask（★ 该不可用）")

        # (2)(3) 配上地址 ⇒ 出按钮；点 ⇒ world/ask app.open_url（带票、人的身份、url 对）
        _set_env(DSH_ENV, FAKE_DSH)
        if dp.dsh_url() != FAKE_DSH:
            bad.append("dsh_url() 没读环境变量 %s：%r" % (DSH_ENV, dp.dsh_url()))
        sp.draw_delegation_panel()
        frame = sp.own[sid]["frame"]
        bad += judge_frame_valid(frame, fs)
        bad += judge_dsh_button(frame)
        before = len(sp.s.puts)
        sp.on_act(H.Sample({"action": {"event": {"name": DSH_EVENT, "context": {}}}}))
        bad += judge_dsh_ask(sp.s.puts[before:], FAKE_DSH, world_actions)

        # 刷新按钮 ⇒ 再查两路（★ 数据仍只从查询来）
        before = len(sp.s.puts)
        sp.on_act(H.Sample({"action": {"event": {"name": dp.REFRESH_EVENT, "context": {}}}}))
        qs2 = [json.loads(p) for t, p in sp.s.puts[before:] if t == "world/query"]
        if {q.get("kind") for q in qs2} != {"history", "events"}:
            bad.append("刷新按钮没有重查 history＋events：%r"
                       % sorted({q.get("kind") for q in qs2}))

        print("=== %s（真仓库·临时数据面 ＋ 真 Space ＋ 真确认队列）===" % NAME)
        print("  现取：history 回 %d 条（job.* %d 条）／events 回 %d 条／确认队列 %d 条／DSH 地址来源 %s"
              % (len(rows), len(job_rows), len(events), len(sp.confirm_queue()), DSH_ENV))
        if bad:
            for x in bad:
                print("  [红] " + x)
            print("=== 结论：红（%d 处）===" % len(bad))
            return 1
        print("=== 结论：绿（数据只从查询来／空态在／最近 5 条／待确认取自队列／"
              "URL 取自环境变量／打开 DSH 经 world/ask app.open_url）===")
        return 0
    finally:
        _set_env(DSH_ENV, old_env)


# ── 自检：四个红例 ＋ 正控 ─────────────────────────────────
class _HardPanel:
    """★ 红例1 的替身：面板自己拼了一张卡，不查世界。"""

    def __init__(self):
        self.s = H.Session()
        self.own = {}
        self.user = "zhang"
        self.pending = {}

    def open_delegation_panel(self):
        self.own["space/delegation-panel-zhang"] = {"frame": {"messages": []}, "rect": []}


class _LocalOpen:
    """★ 红例3 的替身：点「打开 DSH」在本地直接开，不经过本体。"""

    class Space:
        def __init__(self, session):
            self.s = session
            self.opened = False

        def on_act(self, sample):
            self.opened = True          # ★ 直接本地开（没发 world/ask）


def self_test():
    ok = True
    if run() != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    H.temp_dataset()
    H.add_paths("space", "presentation")
    import frame_schema as fs  # noqa: E402
    import delegation_panel as dp  # noqa: E402
    world_actions = load_world_actions()

    # 红例1：面板数据不是查询来的（不查世界 ＋ 硬编码假任务 ＋ 缺空态）
    fake = _HardPanel()
    _, b1 = judge_panel_open(fake, lambda s: s.open_delegation_panel(),
                             "space/delegation-panel-zhang")
    fake_texts = ["任务 ｜ 22:30:51 ｜ user/zhang ｜ job.start ｜ 假任务 ｜ 已提交"]
    b1 += judge_provenance(fake_texts, [], [], [], world_actions)
    b1 += judge_empty_state(fake_texts, 0, EMPTY_TASK)
    b1 += judge_task_scope(["委托 ｜ 22:30:52 ｜ user/zhang ｜ delegate.grant ｜ 是"])
    print("=== 红例1（面板数据不是查询来的：硬编码假任务／假事件）⇒ 命中 %d 处 ===" % len(b1))
    for x in b1:
        print("      " + x)
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False

    # 红例2：URL 写死（字面量地址）
    b2 = judge_url_source('DSH_URL = "%s"\n' % FAKE_DSH)
    print("=== 红例2（地址写死：URL 字面量）⇒ 命中 %d 处 ===" % len(b2))
    for x in b2:
        print("      " + x)
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False

    # 红例3：绕过 world/ask（本地直接开）
    bypass = _LocalOpen.Space(H.Session())
    bypass.on_act(H.Sample({"action": {"event": {"name": DSH_EVENT, "context": {}}}}))
    b3 = judge_dsh_ask(bypass.s.puts, FAKE_DSH, world_actions)
    print("=== 红例3（绕过 world/ask：本地直接开）⇒ 命中 %d 处 ===" % len(b3))
    for x in b3:
        print("      " + x)
    if not b3:
        print("[自检失败] 红例3 该命中")
        ok = False

    # 红例4：空态缺失／帧过不了 frame_schema
    bad_frame = {"messages": [
        {"createSurface": {"surfaceId": "x"}},
        {"updateComponents": {"surfaceId": "x", "components": [
            {"id": "root", "component": "EvilBox", "children": ["no_such_id"]}]}}]}
    b4 = judge_empty_state(["状态：任务 0 条 ｜ 最近事件 0 条"], 0, EMPTY_TASK)
    b4 += judge_frame_valid(bad_frame, fs)
    print("=== 红例4（空态缺失／帧过不了 frame_schema）⇒ 命中 %d 处 ===" % len(b4))
    for x in b4:
        print("      " + x)
    if not b4:
        print("[自检失败] 红例4 该命中")
        ok = False

    # 正控1：URL 从 WORLDCORE_DSH_URL 读 ⇒ 不许红（合法写法 ＋ 真源码两档）
    good_src = 'DSH = os.environ.get("%s") or ""\n' % DSH_ENV
    g1 = judge_url_source(good_src) + judge_url_source(read_text(DP_SRC))
    print("=== 正控1（URL 从 %s 读）⇒ 命中 %d 处 ===" % (DSH_ENV, len(g1)))
    for x in g1:
        print("      " + x)
    if g1:
        print("[自检失败] 正控1 不该红")
        ok = False
    # 正控2：真帧（空态／配了地址）过 frame_schema、空态在、按钮对、点了发 world/ask
    old_env = os.environ.get(DSH_ENV)
    try:
        _set_env(DSH_ENV, None)
        f0 = dp.delegation_panel_frame("space/delegation-panel-zhang", [], [], 0, "")
        g2 = (judge_frame_valid(f0, fs)
              + judge_empty_state(section_texts(f0, dp.TASK_SECTION), 0, EMPTY_TASK)
              + judge_empty_state(section_texts(f0, dp.EVENT_SECTION), 0, EMPTY_EVENT)
              + judge_unconfigured(f0)
              + judge_url_source(read_text(DP_SRC)))
        _set_env(DSH_ENV, FAKE_DSH)
        f1 = dp.delegation_panel_frame("space/delegation-panel-zhang", [], [], 0, dp.dsh_url())
        g2 += judge_frame_valid(f1, fs) + judge_dsh_button(f1)
    finally:
        _set_env(DSH_ENV, old_env)
    print("=== 正控2（真帧：空态合法／配了地址出按钮）⇒ 命中 %d 处 ===" % len(g2))
    for x in g2:
        print("      " + x)
    if g2:
        print("[自检失败] 正控2 不该红")
        ok = False

    # 正控3：最近 5 条（合成的 7 条，最后 5 条里外分明）
    evs = [{"at": "2026-11-08T22:00:%02d+08:00" % i, "action": "job.start",
            "kind_of": "result", "ok": True} for i in range(7)]
    fr = dp.delegation_panel_frame("x", [], evs, 0, "")
    g3 = judge_event_window(section_texts(fr, dp.EVENT_SECTION), evs)
    g3 += judge_empty_state(section_texts(fr, dp.EVENT_SECTION), 5, EMPTY_EVENT)
    print("=== 正控3（最近事件只画最近 5 条）⇒ 命中 %d 处 ===" % len(g3))
    for x in g3:
        print("      " + x)
    if g3:
        print("[自检失败] 正控3 不该红")
        ok = False

    # 正控4：history 里的 delegate.* 不进「当前任务」（过滤后 0 条 ⇒ 空态）
    extra = {"at": "2026-11-08T22:00:09+08:00", "action": "delegate.grant", "kind_of": "ask"}
    fr2 = dp.delegation_panel_frame("x", [extra], [], 0, "")
    g4 = judge_task_scope(section_texts(fr2, dp.TASK_SECTION))
    g4 += judge_empty_state(section_texts(fr2, dp.TASK_SECTION), 0, EMPTY_TASK)
    print("=== 正控4（delegate.* 不进「当前任务」）⇒ 命中 %d 处 ===" % len(g4))
    for x in g4:
        print("      " + x)
    if g4:
        print("[自检失败] 正控4 不该红")
        ok = False

    print("=== 自检结论：%s ===" % ("全绿（红例会红、正控不红）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
