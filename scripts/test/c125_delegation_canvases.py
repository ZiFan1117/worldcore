#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C125 —— **委托模式的三块世界侧画布**：任务卡／确认／进度流（全部 A2UI 帧）。

★ 口径（作者「界面就是消息」「查历史也要过本体」）：
  画布不是第二个数据库 —— **画什么，只能由 `world/query` 的回话决定**；
  按钮不是第二个执行器 —— **点什么，只能变成 `world/ask`（带票、以人的身份）**。

判的是【事实侧】（真造帧、真走 `Space`、真查一次真账）：
  (a) 三块画布都是 A2UI 帧，**整帧**过 `src/presentation/frame_schema.py`（basic catalog）；
  (b) 任务卡（`src/space/delegation_frame.py`）：开卡**先发** `world/query kind=history`（带票），
      回话到了才出帧；★ 帧里的每一行都要能指回回话里的 `job.*` / `delegate.*` / `agent.*` 行，
      ★ 回 0 行 ⇒ 必须画「还没有任务」；★ 画了查询结果里没有的动作 ⇒ 红（硬编码假任务）；
  (c) 进度流（`src/space/progress_frame.py`）：同上，只是 `kind=events`；★ 回 0 条 ⇒「还没有事件」；
      ★ 被拒的事件必须画出来（带码）—— 不许把红藏起来；
  (d) 按钮只经本体：`space.job_start/job_finish/job_cancel` ⇒ `world/ask job.start/job.finish/job.cancel`
      （带票、`actor=world://user/…`）；★ 没发 `world/ask`（直接改本地 state／直接调执行器）⇒ 红；
  (e) 确认画布（`src/space/confirm_window.py`）：`confirm.request` ⇒ 帧合目录、三按钮是 `confirm.decide`；
      人点 ⇒ 以人的身份带票发 `world/ask confirm.resolve`；★ 两条排队不丢（签完一条换下一条）；
  (f) 动作名以 `world.json` 为准：画布里出现的 `job.*` / `delegate.*` / `agent.*` / `confirm.*` 都在册。

限度（★ 如实）：
  · 本判据在**宿主**上跑：账本、注册表、对象库都指到临时处（`_proc_helper.temp_dataset`），不碰真机数据面；
  · 它判**帧/取数/按钮去向**这三段；**屏上画成什么样**（Flutter／浏览器的像素）要 VM 上的真截图，另算；
  · 它不判渲染器是否解析按钮 `context` 里的 `{path}`（那是 genui 的事）—— 取不到值时个人空间
    **不发**、也不拿本地状态顶（这条在 `delegation_frame.draw_job` 里，见自检红例2）。

用法：
  python scripts/test/c125_delegation_canvases.py              跑真仓库
  python scripts/test/c125_delegation_canvases.py --self-test  反例自检
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import _proc_helper as H  # noqa: E402

NAME = "C125 委托模式的三块画布（任务卡／确认／进度流，全 A2UI 帧）"
JSON_ACTIONS = os.path.join(H.SRC, "ontology", "world.json")
# ★ 画布上要出现的动作族（以 world.json 为准，见 judge_actions_declared）
WANT_DECLARED = ("job.start", "job.finish", "job.cancel",
                 "delegate.grant", "delegate.revoke", "delegate.list",
                 "confirm.request", "confirm.resolve")


# ── 取件的小工具 ─────────────────────────────────────────────
def frame_texts(frame):
    """★ 帧里所有 Text 的 text（判「画布上到底写了什么」只看这个）。"""
    out = []
    for m in (frame or {}).get("messages") or []:
        for c in (m.get("updateComponents") or {}).get("components") or []:
            if isinstance(c, dict) and c.get("component") == "Text":
                out.append(str(c.get("text") or ""))
    return out


def frame_buttons(frame):
    """★ 帧里所有按钮：id -> (事件名, context)。"""
    out = {}
    for m in (frame or {}).get("messages") or []:
        for c in (m.get("updateComponents") or {}).get("components") or []:
            if not isinstance(c, dict) or c.get("component") != "Button":
                continue
            ev = ((c.get("action") or {}).get("event") or {})
            out[c.get("id")] = (ev.get("name"), ev.get("context") or {})
    return out


def load_world_actions():
    """★ 动作名的唯一出处：`src/ontology/world.json`（不是本判据里的一张表）。"""
    with open(JSON_ACTIONS, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return {a.get("id") for a in (doc.get("actions") or []) if a.get("id")}


# ── 纯函数判据（自带红例可喂）────────────────────────────────
def judge_frame_valid(frame, fs):
    """(a) 整帧校验：不合目录 ⇒ 列出来（★ 不静默过滤）。"""
    return ["帧过不了 frame_schema：%s" % p for p in fs.validate_frame(frame)]


def judge_empty_state(texts, n_rows, empty_token):
    """(b)(c) 空态：0 条要有「还没有…」，有条就不该再写空态。"""
    bad = []
    present = any(empty_token in t for t in texts)
    if n_rows == 0 and not present:
        bad.append("查询回 0 条却缺空态「%s」（★ 空态也是帧）" % empty_token)
    if n_rows > 0 and present:
        bad.append("有 %d 条记录却还写着空态「%s」（画布与查询不符）" % (n_rows, empty_token))
    return bad


def judge_provenance(texts, rows, known_actions, only_task=False):
    """★ 每一行都要能被查询回来的行解释；★ 画了行外动作 ⇒ 硬编码。"""
    bad = []
    blob = "\n".join(texts)
    acts = {str(r.get("action") or "") for r in rows if isinstance(r, dict)}
    for r in rows:
        act = str(r.get("action") or "")
        clock = str(r.get("at") or "")[11:19]
        if act and act not in blob:
            bad.append("查询回来的行没画出来：%s（%s）" % (act, r.get("at")))
        elif clock and clock not in blob:
            bad.append("查询回来的时间没画出来：%s（%s）" % (clock, act))
    for act in known_actions:
        if act not in acts and act in blob:
            bad.append("画布画了查询结果里没有的动作 %s（★ 硬编码假任务）" % act)
    if only_task:
        for act in sorted(acts):
            if not act.startswith(("job.", "delegate.", "agent.")) and act in blob:
                bad.append("任务卡画了不属于任务的记录：%s" % act)
    return bad


def judge_actions_declared(mod, world_actions):
    """(f) 画布里用的动作名必须在 world.json 里在册。"""
    bad = []
    for act in sorted(set(mod.JOB_ACTIONS.values()) | set(WANT_DECLARED)):
        if act not in world_actions:
            bad.append("画布用了不在 world.json 的动作名：%s" % act)
    for act in mod.JOB_ACTIONS.values():
        if not act.startswith(mod.TASK_ACTION_PREFIXES):
            bad.append("%s 不在任务卡认的前缀 %r 里（自己画不出来自己）"
                       % (act, mod.TASK_ACTION_PREFIXES))
    return bad


# ── 行为判据（要一个真 Space／假 Space）──────────────────────
def open_canvas(sp, opener, want_kind):
    """★ 开画布 ⇒ (查询消息, 问题清单)：**先查再画**，查要带票、kind 要对。"""
    bad = []
    before = len(sp.s.puts)
    own_before = set(getattr(sp, "own", None) or {})
    opener(sp)
    outs = sp.s.puts[before:]
    qs = [json.loads(p) for t, p in outs if t == "world/query"]
    if not qs:
        bad.append("开画布没有发 world/query（★ 数据不是查询来的）")
        return None, bad
    q = qs[-1]
    if q.get("kind") != want_kind:
        bad.append("查询 kind=%r ≠ %r" % (q.get("kind"), want_kind))
    if not q.get("ticket"):
        bad.append("查询没带票（★ 匿名翻不了账，读闸会拒）")
    if set(getattr(sp, "own", None) or {}) - own_before:
        bad.append("查询回话还没到就出了帧（★ 帧必须用回话里的数据画）")
    return q, bad


def judge_canvas(sp, opener, want_kind, data_key, empty_token, sid,
                 rows_used, fs, rows, known_actions, only_task):
    """(b)(c) 一趟走完：开卡 ⇒ 空回话 ⇒ 真回话。"""
    bad = []
    q, b = open_canvas(sp, opener, want_kind)
    bad += b
    if q is None:
        return bad
    # 空回话 ⇒ 空态帧
    sp.on_query_result(H.Sample({"id": q["id"], "ok": True, "data": {data_key: []}}))
    if sid not in sp.own:
        bad.append("查询回话到了却没出帧（%s）" % sid)
        return bad
    empty_frame = sp.own[sid]["frame"]
    bad += judge_frame_valid(empty_frame, fs)
    bad += judge_empty_state(frame_texts(empty_frame), 0, empty_token)
    bad += judge_provenance(frame_texts(empty_frame), [], known_actions, only_task)
    # 真回话 ⇒ 数据帧
    q, b = open_canvas(sp, opener, want_kind)
    bad += b
    if q is None:
        return bad
    sp.on_query_result(H.Sample({"id": q["id"], "ok": True, "data": {data_key: rows}}))
    frame = sp.own[sid]["frame"]
    used = rows_used(rows) if rows_used else rows
    bad += judge_frame_valid(frame, fs)
    bad += judge_empty_state(frame_texts(frame), len(used), empty_token)
    bad += judge_provenance(frame_texts(frame), used, known_actions, only_task)
    return bad


def judge_job_buttons(spm, Hh, world_actions):
    """(d) 任务卡的三个按钮：★ 只发 world/ask（带票、以人的身份、参数对）。"""
    bad = []
    sp = spm.Space(Hh.Session())
    sp.draw = lambda: None
    sp.ticket = "tk-c125"
    for event, want, ctx, key in (
            ("space.job_start", "job.start", {"subject": "写报告"}, "subject"),
            ("space.job_finish", "job.finish", {"job": "job-c125"}, "job"),
            ("space.job_cancel", "job.cancel", {"job": "job-c125"}, "job")):
        before = len(sp.s.puts)
        sp.on_act(Hh.Sample({"action": {"event": {"name": event, "context": ctx}}}))
        asks = [json.loads(p) for t, p in sp.s.puts[before:] if t == "world/ask"]
        hit = [a for a in asks if a.get("action") == want]
        if not hit:
            bad.append("%s 没发 world/ask %s（★ 按钮不经本体）" % (event, want))
            continue
        a = hit[-1]
        if want not in world_actions:
            bad.append("%s 不在 world.json（画布自造动作名）" % want)
        if not a.get("ticket"):
            bad.append("%s 没带票（★ 空间不能自己发许可）" % event)
        if not str(a.get("actor") or "").startswith("world://user/"):
            bad.append("%s 不是人的身份：%r" % (event, a.get("actor")))
        if (a.get("params") or {}).get("subject") != ctx[key]:
            bad.append("%s 的参数不对：%r（★ 该发 subject=%r）"
                       % (event, a.get("params"), ctx[key]))
    # ★ 取不到参数 ⇒ 不发、不拿本地状态顶
    before = len(sp.s.puts)
    sp.on_act(Hh.Sample({"action": {"event": {"name": "space.job_start",
                                              "context": {"subject": {"path": "/x"}}}}}))
    if [p for t, p in sp.s.puts[before:] if t == "world/ask"]:
        bad.append("参数是没解析的 {path} 时仍然发了 world/ask（★ 拿空值/旧值顶了）")
    return bad


def judge_confirm(spm, Hh, fs):
    """(e) 确认画布：帧合目录、三按钮是 confirm.decide、点 ⇒ 带票 world/ask confirm.resolve、排队不丢。"""
    bad = []
    sp = spm.Space(Hh.Session())
    sp.draw = lambda: None
    sp.ticket = "tk-cf"
    sid = "space/confirm-" + sp.user

    def _req(name, summary):
        return Hh.Sample({"kind": "confirm.request", "by": "world://guard",
                          "confirmation": {"name": name, "for_actor": "world://agent/dsh",
                                           "action": "sys.AptInstall", "summary": summary}})

    sp.on_frame(_req("cf-1", "s1"))
    if sid not in sp.own:
        bad.append("confirm.request 没出确认画布")
        return bad
    frame = sp.own[sid]["frame"]
    bad += judge_frame_valid(frame, fs)
    btn = frame_buttons(frame)
    for bid, dec in (("cf_deny_b", "deny"), ("cf_once_b", "allow_once"),
                     ("cf_deleg_b", "allow_delegation")):
        name = (btn.get(bid) or (None, {}))[0]
        ctx = (btn.get(bid) or (None, {}))[1]
        if name != "confirm.decide":
            bad.append("%s 的事件名不是 confirm.decide：%r" % (bid, name))
        elif ctx.get("decision") != dec:
            bad.append("%s 的 decision 不是 %r" % (bid, dec))
    # ★ 第二条不丢：窗口仍在、并说出还有几条
    sp.on_frame(_req("cf-2", "s2"))
    if sid not in sp.own:
        bad.append("第二条 confirm.request 把窗口顶没了")
    elif "还有 1 条待确认" not in "\n".join(frame_texts(sp.own[sid]["frame"])):
        bad.append("第二条到了却没标「还有 1 条待确认」（★ 排队丢失）")
    # 人点最新一条 ⇒ 带票回本体
    before = len(sp.s.puts)
    sp.on_act(Hh.Sample({"action": {"event": {"name": "confirm.decide",
                                              "context": {"confirmation": "cf-2",
                                                          "decision": "allow_once"}}}}))
    asks = [json.loads(p) for t, p in sp.s.puts[before:] if t == "world/ask"]
    hit = [a for a in asks if a.get("action") == "confirm.resolve"]
    if not hit:
        bad.append("点确认没发 world/ask confirm.resolve（★ 桌面上不能自己发许可）")
    else:
        a = hit[-1]
        if not a.get("ticket"):
            bad.append("confirm.resolve 没带票")
        if not str(a.get("actor") or "").startswith("world://user/"):
            bad.append("confirm.resolve 不是人的身份：%r" % (a.get("actor")))
        if (a.get("params") or {}).get("name") != "cf-2":
            bad.append("签的不是被点的那一条：%r" % (a.get("params"),))
    # ★ 签完换下一条（cf-1 还在，仍可签）
    if sid not in sp.own:
        bad.append("签完最新一条后，排队里的 cf-1 没被换出来（★ 丢了）")
    else:
        sp.on_act(Hh.Sample({"action": {"event": {"name": "confirm.decide",
                                                  "context": {"confirmation": "cf-1",
                                                              "decision": "deny"}}}}))
        if sid in sp.own:
            bad.append("两条都签完了窗口还在（没撤下）")
    return bad


# ── 真数据：真世界真账，再从 world/query 把行取回来 ─────────
def real_rows_and_events(op):
    """★ 在本体里真跑几条 job/delegate 动作（含一条被拒），再真查一次。"""
    w = H.new_world()
    s0 = H.Session()
    op._ask_and_forward(H.Sample({"id": "c125-auth", "action": "identity.authenticate",
                                  "params": {"user": "zhang", "secret": "0"},
                                  "actor": "world://surface/s0"}), w, s0)
    body = (json.loads(s0.last_on(op.T_ASK_RESULT) or "{}").get("body") or {})
    ticket = body.get("ticket") or ""

    def _ask(mid, action, params):
        s = H.Session()
        op._ask_and_forward(H.Sample({"id": mid, "action": action, "params": params,
                                      "actor": "world://user/zhang",
                                      "ticket": ticket}), w, s)
        return json.loads(s.last_on(op.T_ASK_RESULT) or "{}")

    _ask("c125-j1", "job.start", {"subject": "写报告"})
    _ask("c125-j2", "job.finish", {"subject": "job-not-there"})   # ★ 这一笔会被拒（要画出来）
    expires = (datetime.datetime.now().astimezone()
               + datetime.timedelta(hours=1)).isoformat(timespec="seconds")
    _ask("c125-d1", "delegate.grant", {"to": "world://agent/dsh", "action": "sys.AptInstall",
                                       "expires": expires, "max_uses": 1})
    out = {}
    for kind, key in (("history", "rows"), ("events", "events")):
        s = H.Session()
        op.world_query.handle(H.Sample({"id": "c125-" + kind, "kind": kind,
                                        "ticket": ticket, "limit": 100}), w, s)
        d = json.loads(s.last_on("world/query/result") or "{}")
        if not d.get("ok"):
            raise RuntimeError("查 %s 失败：%r" % (kind, d.get("why")))
        out[key] = (d.get("data") or {}).get(key) or []
    return out["rows"], out["events"], ticket


def run():
    H.temp_dataset()
    op = H.import_ontology_process()
    H.add_paths("space", "presentation")
    import frame_schema as fs  # noqa: E402
    import delegation_frame as dl  # noqa: E402
    import progress_frame as pg  # noqa: E402
    import space_process as spm  # noqa: E402

    world_actions = load_world_actions()
    rows, events, ticket = real_rows_and_events(op)
    bad = judge_actions_declared(dl, world_actions)

    sp = spm.Space(H.Session())
    sp.draw = lambda: None
    sp.ticket = ticket
    bad += judge_canvas(sp, lambda s: s.open_delegation(), "history", "rows",
                        dl.EMPTY_TEXT, dl.SID_PREFIX + sp.user,
                        dl.task_rows, fs, rows, world_actions, True)
    sp2 = spm.Space(H.Session())
    sp2.draw = lambda: None
    sp2.ticket = ticket
    bad += judge_canvas(sp2, lambda s: s.open_progress(), "events", "events",
                        pg.EMPTY_TEXT, pg.SID_PREFIX + sp2.user,
                        None, fs, events, world_actions, False)
    # ★ 拒绝必须画出来（带码）—— 进度流里那笔 job.finish 的拒绝
    if "space/progress-" + sp2.user in sp2.own:
        blob = "\n".join(frame_texts(sp2.own["space/progress-" + sp2.user]["frame"]))
        if "JOB_NOT_FOUND" not in blob:
            bad.append("进度流没画被拒的那笔（缺 JOB_NOT_FOUND）—— ★ 拒绝也要显示")
    # ★ 任务卡上也要看得见「被拒」这一笔
    if "space/delegation-" + sp.user in sp.own:
        blob = "\n".join(frame_texts(sp.own["space/delegation-" + sp.user]["frame"]))
        if "被拒" not in blob:
            bad.append("任务卡没标出被拒的记录")
    bad += judge_job_buttons(spm, H, world_actions)
    bad += judge_confirm(spm, H, fs)

    print("=== %s（真仓库·临时数据面 ＋ 真 Space）===" % NAME)
    print("  现取：任务卡行 %d／事件 %d 条（真查）；动作名在册 %d 个；画布按钮 3 类 ⇒ world/ask"
          % (len(dl.task_rows(rows)), len(events), len(world_actions)))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿（帧合目录／数据只从查询来／空态在／拒绝也画／按钮经本体／确认排队不丢）===")
    return 0


# ── 自检：四个红例 ＋ 正控 ─────────────────────────────────
class _HardCanvas:
    """★ 红例1 的替身：画布自己拼了一张卡，不查世界。"""

    def __init__(self):
        self.s = H.Session()
        self.own = {}
        self.user = "zhang"

    def open_delegation(self):
        self.own["space/delegation-zhang"] = {"frame": {"messages": []}, "rect": []}


class _BypassModule:
    """★ 红例2 的替身：按钮直接改本地 state，不经过本体。"""

    class Space:
        def __init__(self, session):
            self.s = session
            self.ticket = "tk"
            self.draw = lambda: None
            self.state = {}

        def on_act(self, sample):
            self.state["job"] = "done"          # ★ 直接改本地状态


def self_test():
    ok = True
    if run() != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    H.temp_dataset()
    H.add_paths("space", "presentation")
    import frame_schema as fs  # noqa: E402
    import delegation_frame as dl  # noqa: E402
    world_actions = load_world_actions()

    # 红例1：画布数据不是来自查询/事件（本地拼的卡 ＋ 回 0 行却画出了任务）
    q, b1 = open_canvas(_HardCanvas(), lambda s: s.open_delegation(), "history")
    fake_texts = ["任务 ｜ 22:30:51 ｜ user/zhang ｜ job.start ｜ 假任务 ｜ 已提交"]
    b1 += judge_provenance(fake_texts, [], world_actions, True)
    b1 += judge_empty_state(fake_texts, 0, dl.EMPTY_TEXT)
    print("=== 红例1（画布数据不是来自查询：硬编码假任务）⇒ 命中 %d 处 ===" % len(b1))
    for x in b1:
        print("      " + x)
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False

    # 红例2：按钮动作不经本体（直接改本地 state）
    b2 = judge_job_buttons(_BypassModule, H, world_actions)
    print("=== 红例2（按钮不经本体：直接改本地 state）⇒ 命中 %d 处 ===" % len(b2))
    for x in b2[:3]:
        print("      " + x)
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False

    # 红例3：空态缺失／帧过不了 frame_schema
    b3 = judge_empty_state(["来源：world/query kind=history ｜ 在册记录 0 条"], 0, dl.EMPTY_TEXT)
    bad_frame = {"messages": [
        {"createSurface": {"surfaceId": "x"}},
        {"updateComponents": {"surfaceId": "x", "components": [
            {"id": "root", "component": "EvilBox", "children": ["no_such_id"]}]}}]}
    b3 += judge_frame_valid(bad_frame, fs)
    print("=== 红例3（空态缺失／帧过不了 frame_schema）⇒ 命中 %d 处 ===" % len(b3))
    for x in b3:
        print("      " + x)
    if not b3:
        print("[自检失败] 红例3 该命中")
        ok = False

    # 红例4：画布自造不在 world.json 的动作名
    class _FakeMod:
        JOB_ACTIONS = {"space.job_start": "job.teleport"}
        TASK_ACTION_PREFIXES = ("job.",)

    b4 = judge_actions_declared(_FakeMod, world_actions)
    print("=== 红例4（画布自造世界动作名）⇒ 命中 %d 处 ===" % len(b4))
    for x in b4[:3]:
        print("      " + x)
    if not b4:
        print("[自检失败] 红例4 该命中")
        ok = False

    # 正控：真帧（空／有数据）都不许红
    good = dl.delegation_frame("space/delegation-zhang", [])
    g = judge_frame_valid(good, fs) + judge_empty_state(frame_texts(good), 0, dl.EMPTY_TEXT)
    print("=== 正控（真帧：空态合法）⇒ 命中 %d 处 ===" % len(g))
    if g:
        for x in g:
            print("      " + x)
        print("[自检失败] 正控不该红")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、正控不红）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
