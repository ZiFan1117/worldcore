#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""signoff_guard.py —— 两个枢纽的**签字面**判据（标准 §二「两个枢纽各是一道真闸」）。

出处（逐字为准）：
  · `11-ninedim/standard/双环与四种循环.md` §二（枢纽 A：未批不许动手；枢纽 B：未签不算完）
  · `11-ninedim/standard/分层与双环.md` §二（「未批 → 不许进入执行」「未签 → 不算完成」）
  · `ninedim/02-枢纽A-前置闸/_索引.md` 引的铁律二（**未签字的评审记录等于未评审**）

两条判据（都会红）：
  S-A  枢纽 A（`ninedim/02-枢纽A-前置闸/`）**没出「批准」**（结论＝通过／有条件通过／批准，
       且同表有**人**签署）⇒ **执行环（`ninedim/03-执行环/**`）不许有产物**（`_索引.md` 不算产物）。
  S-B  枢纽 B 未签 ⇒ 变更不许进 `ninedim/06-变更/archive/`：每个归档目录必须有**已签的评审面**
       （目录内的评审件，或 `04-枢纽B-后置闸/` 里点名了它的已签评审件）；结论为「退回」却归档了 ⇒ 红。

射程（如实声明，不粉饰）：
  · 本件判**面在不在**，不判**时序**（"批准发生在产物之前"这一步判据读不出来，故不冒充）；
  · "签字"只认**表结构**：同一行里既有结论值、又有非 AI 的人名；`<待人工>`／空／`（AI 不签字）`一律算未签；
  · 结论的读法复用 `check_loops.py` 的唯一实现（**不复制第二份**）：只认 `☑` 标在哪个选项上。

三档结局（**不许混**；口径与同轮 `scripts/verify/check_loops.py` 的 `[OK]／[EMPTY]／[RED]` 一致）：
  `[OK]`    判过且无红；
  `[EMPTY]` 判过：该闸的**条目集为空**或**扫描面读不到**——**不是绿**。此时末行打 `STATUS=SKIP`、
            **不许出现 `STATUS=PASS`**（"没东西可判／读不到"≠"关得住"）；
  `[RED]`   有红（详情逐条打印）。

★ 为什么空集单列（2026-10-08 修；复核席 F-02a）：修前 `archives()` 取不到 `ninedim/06-变更/archive/`
  就返回 `[]`，于是"已归档 0 个"照样打 `S-B [OK]` ＋ `STATUS=PASS` ⇒ **空集被读成绿**。
  可达性不是假想：本轮自己就搬过 `generated/`→`ninedim/records/生成物/`、`deploy/`→`scripts/release/`；
  `archive/` 一旦随迁，`check.sh` ⑦h 会打 ✅ 而**什么都没判**。`--self-test` 有两条正控钉住它
  （删掉 `archive/` 整块 ⇒ 不许 PASS；`archive/` 在但 0 个变更夹 ⇒ 同）。

用法：`python signoff_guard.py [--root <仓根>] [--list]`｜`--self-test`（正控 ＋ 反例必红）
退出码：0=两闸都关得住（绿）或**空集 ⇒ SKIP（不算绿）**／1=有红／2=用法错或仓根不在。
"""
import argparse
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_loops as cl  # noqa: E402 —— 结论／签字的读法只有一份权威载体

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_INJECTED = None


def set_root(path):
    global _ROOT_INJECTED
    _ROOT_INJECTED = path


def _d(root, rel):
    return os.path.join(root, *rel.split("/"))


def _files(root, rel, skip_index=True):
    d = _d(root, rel)
    if not os.path.isdir(d):
        return []
    out = [p for p in cl._md_files(d) if not (skip_index and os.path.basename(p) == "_索引.md")]
    return out


def approvals_a(root):
    """枢纽 A 的批准面：[(件, 状态)]。"""
    return [(p, cl.signed_verdict(cl.read(p))) for p in _files(root, "ninedim/02-枢纽A-前置闸")]


def exec_products(root):
    """执行环产物（`_索引.md` 不算产物）。"""
    d = _d(root, "ninedim/03-执行环")
    out = []
    for dp, _dn, fn in os.walk(d):
        for f in fn:
            if f != "_索引.md":
                out.append(os.path.join(dp, f))
    return sorted(out)


def archives(root):
    """返回 `(归档目录名列表, 扫描面状态)`；状态 ∈ `{"ok","empty","missing"}`。

    ★ 2026-10-08 修（复核席 F-02a）：修前只返回列表，取不到目录与"目录在但一个变更都没有"
       **折成同一个 `[]`** ⇒ 下游照打 `[OK]`／`STATUS=PASS`（空集判绿）。现在把"读不到"与
      "空集"与"有"三分，由 `run()` 单列 `[EMPTY]`／`STATUS=SKIP`。
    """
    d = _d(root, "ninedim/06-变更/archive")
    if not os.path.isdir(d):
        return [], "missing"
    names = sorted(x for x in os.listdir(d)
                   if os.path.isdir(os.path.join(d, x)) and x != ".gitkeep")
    return names, ("ok" if names else "empty")


def _is_review_doc(p):
    """这一份算不算「评审面件」：名字含「评审」或就叫 `review.md`。

    ⚠ 为什么必须筛（F-02b 的近邻坑）：归档夹里除 `review.md` 外还有 `design.md`／`proposal.md`／
      `tasks.md`／`_索引.md`。若把它们也当评审面记出处，一份**没有评审件**的归档会被报成
      「评审面未签（出处：design.md）」——**修一个假话不能靠造第二个假话**。
    """
    b = os.path.basename(p)
    return b == "review.md" or "评审" in b


def b_signed_evidence(root, arch):
    """归档 `arch` 的已签评审面：返回 (状态, 出处)。

    ★ 2026-10-08 修（复核席 F-02b，**第三档分支不可达**）：修前只在 `st == "approve"` 时更新
      `best` ⇒ `src` **恒为 `None`** ⇒ `run()` 三档里 `elif src is None` 永远先命中，
      第三档「评审面**未签**（结论栏留空／签字栏非人）」**永不执行**：盘上明明躺着那份未签的
      `review.md`，报的却是「**一件评审件都没有**」——**红得对、话是假的**（读的人会去"补一件
      评审件"，而该做的是把已有那件签掉）。现在 `blank`／`other` 也记出处（限评审面件），
      把「无件」与「有件未签」两档分开。
    """
    cands = _files(root, "ninedim/06-变更/archive/" + arch, skip_index=False)
    cands += _files(root, "ninedim/04-枢纽B-后置闸")
    best = ("blank", None)
    for p in cands:
        txt = cl.read(p)
        inside = p.startswith(_d(root, "ninedim/06-变更/archive/" + arch))
        if not inside and arch not in txt:
            continue
        st = cl.signed_verdict(txt)
        if st == "reject":
            return "reject", p
        if st == "approve" and best[0] != "approve":
            best = ("approve", p)
        elif best[1] is None and _is_review_doc(p):
            best = (st, p)
    return best


def run(root, quiet=False, list_only=False):
    """返回 `(rc, reds, status)`；`status ∈ {"PASS","SKIP","FAIL"}`（`--list` 时 `"LIST"`）。

    `SKIP` ＝ 有闸**没有可判的条目／扫描面读不到** ⇒ **不判绿**（rc 仍 0，但末行 `STATUS=SKIP`
    会被 `check.sh` 的 `run_tail` 渲染成 ⏭，不会长成 ✅）。
    """
    reds, notes = [], []
    aps = approvals_a(root)
    ok_a = [p for p, st in aps if st == "approve"]
    bad_a = [(p, st) for p, st in aps if st == "reject"]
    prod = exec_products(root)
    arch, arch_face = archives(root)
    signed_b, unsig_b = [], []
    for a in arch:
        st, src = b_signed_evidence(root, a)
        if st == "approve":
            signed_b.append((a, src))
        else:
            unsig_b.append((a, st, src))

    if list_only:
        print("== signoff_guard --list（签字面清单，现取）==")
        print("  枢纽A：%d 件；已签批准 %d 件；判「退回」%d 件" % (len(aps), len(ok_a), len(bad_a)))
        for p, st in aps:
            print("    [%s] %s" % ({"approve": "已签批准", "reject": "退回",
                                    "blank": "未签/留空", "other": "未见结论"}[st],
                                   os.path.relpath(p, root).replace(os.sep, "/")))
        for p in _files(root, "ninedim/04-枢纽B-后置闸"):
            if "评审" not in os.path.basename(p):
                continue
            st = cl.signed_verdict(cl.read(p))
            print("    [枢纽B %s] %s" % ({"approve": "已签通过", "reject": "退回",
                                          "blank": "未签/留空", "other": "未见结论"}[st],
                                         os.path.relpath(p, root).replace(os.sep, "/")))
        print("  执行环产物：%d 件" % len(prod))
        print("  已归档 change：%d 个；已签 %d 个；未签 %d 个%s"
              % (len(arch), len(signed_b), len(unsig_b),
                 "" if arch_face == "ok" else "　← [EMPTY] 归档面%s（**不判绿**）"
                 % ("读不到：`ninedim/06-变更/archive/` 不在盘上" if arch_face == "missing"
                    else "为空：0 个变更夹")))
        for a in arch:
            st, src = b_signed_evidence(root, a)
            print("    [%s] %s%s" % ({"approve": "已签", "reject": "判退回",
                                      "blank": "未签", "other": "未见结论"}[st], a,
                                     "" if not src else "（出处：%s）" % os.path.relpath(src, root).replace(os.sep, "/")))
        return 0, reds, "LIST"

    # ── S-A 枢纽 A 未批不许动手 ─────────────────────────────────────────
    a_empty = None
    if not ok_a:
        if prod:
            reds.append("[S-A] 枢纽A 没有一件「已签的批准结论」（`ninedim/02-枢纽A-前置闸/` 里 %d 件都不是），"
                        "而执行环已有产物 %d 件 ⇒ **未批不许动手**（分层与双环 §二）。样例：%s"
                        % (len(aps), len(prod),
                           "、".join(os.path.relpath(p, root).replace(os.sep, "/") for p in prod[:5])))
        elif not aps:
            # ★ 空集单列（不许判绿）：枢纽A 一件评审件都没有、执行环也没有产物 ⇒ 这一闸**没有可判的面**
            a_empty = ("空集／读不到：`ninedim/02-枢纽A-前置闸/` 里 0 件评审件、执行环也没有产物 ⇒ "
                       "S-A 今天没有可判的条目（判过了——**不是没跑**，但**未校验 ≠ 通过**）")
        else:
            notes.append("枢纽A 未出批准（有 %d 件评审件），但执行环也没有产物 ⇒ 这一闸今天没有该拦的东西（不红）"
                         % len(aps))
    else:
        notes.append("枢纽A 已签批准 %d 件 ⇒ 执行环产物 %d 件在此面之下" % (len(ok_a), len(prod)))

    # ── S-B 枢纽 B 未签不许进 archive ───────────────────────────────────
    for a, st, src in unsig_b:
        if st == "reject":
            reds.append("[S-B] 归档 `%s` 的评审面结论为「退回」，却已经进了 `archive/`（出处：%s）"
                        "⇒ 未签（判退回）不算完" % (a, os.path.relpath(src, root).replace(os.sep, "/") if src else "—"))
        elif src is None:
            reds.append("[S-B] 归档 `%s` **一件评审件都没有**（目录内、`04-枢纽B-后置闸/` 里点名它的都没有）"
                        "⇒ 未签不许进 `archive/`（双环与四种循环 §二）" % a)
        else:
            reds.append("[S-B] 归档 `%s` 的评审面**未签**（结论栏留空／签字栏非人；出处：%s）"
                        "⇒ 未签不许进 `archive/`（铁律二：未签字的评审记录等于未评审）"
                        % (a, os.path.relpath(src, root).replace(os.sep, "/")))
    b_empty = None
    if arch_face == "missing":
        b_empty = ("空集／读不到：`ninedim/06-变更/archive/` **不在盘上** ⇒ S-B 没有可判的归档面"
                   "（判不了 ≠ 通过；**未校验 ≠ 通过**）")
    elif not arch:
        b_empty = "空集：0 个已归档 change（判过了：这一条今天没有可判的条目——**不是没跑**）"
    notes.append("已归档 change %d 个：已签 %d／未签 %d%s"
                 % (len(arch), len(signed_b), len(unsig_b),
                    "" if not b_empty else "（[EMPTY] 归档面%s）"
                    % ("读不到" if arch_face == "missing" else "为空")))

    n_ok = (0 if (any(x.startswith("[S-A]") for x in reds) or a_empty) else 1) + \
           (0 if (any(x.startswith("[S-B]") for x in reds) or b_empty) else 1)
    n_em = (1 if a_empty else 0) + (1 if b_empty else 0)
    n_bad = len(set(x[:5] for x in reds))
    status = "FAIL" if reds else ("SKIP" if n_em else "PASS")

    if not quiet:
        print("== signoff_guard（两个枢纽的签字面）==")
        print("   仓根：%s" % root)
        for n in notes:
            print("   注：%s" % n)
        print("   S-A 枢纽A 未批不许动手   [%s]"
              % ("RED" if any(x.startswith("[S-A]") for x in reds) else ("EMPTY" if a_empty else "OK")))
        print("   S-B 枢纽B 未签不进 archive [%s]"
              % ("RED" if any(x.startswith("[S-B]") for x in reds) else ("EMPTY" if b_empty else "OK")))
        for x in reds:
            print("        [RED] %s" % x)
        for e in (a_empty, b_empty):
            if e:
                print("        └ %s" % e)
        print("   —— 判据 2 条：绿 %d／空集 %d／红 %d 条判据（红点 %d 处）；未签的枢纽B件不算归档面，"
              "另见 `--list` ——" % (n_ok, n_em, n_bad, len(reds)))
        print("   STATUS=%s" % status)
    return (1 if reds else 0), reds, status


# ── 自证 ─────────────────────────────────────────────────────────────
def _w(root, rel, body):
    p = os.path.join(root, *rel.split("/"))
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)


A_OK = ("# 前置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
        "| 主持人 | Demo | ☑ 通过 | Demo | 2026-01-01 |\n")
A_UNSIGNED = ("# 前置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
              "| 主持人 | `<待人工>` | ☐ 通过 ／ ☐ 退回 |  |  |\n")
B_OK = ("# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | Demo |\n| 结论 | 批准 |\n")
B_UNSIGNED = "# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | `<待人工>` |\n| 结论 | 待签 |\n"
B_REJECT = "# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | Demo |\n| 结论 | 驳回 |\n"
B_PLACEHOLDER = "# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | `<待人工>` |\n| 结论 | 批准 |\n"
# ★ 结论头是「批准」、括号里引了「通过／退回」的分档枚举 ⇒ **不许**读成退回（2026-10-08 假红实测）
B_QUOTED_ENUM = ("# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | Demo |\n"
                 "| 结论 | **批准**（按分档「R4 ＝ 通过／有条件通过／退回；R5 ＝ 批准／驳回」记） |\n")
# 表头带限定的结论栏 + 勾选栏留 `<待人工>` ⇒ **未签**（实测形态：R0 的 `| 结论（EV-04 三选一） | 勾选 |`）
B_QUALIFIED = ("# review\n\n| 结论（三选一） | 勾选 | 说明 |\n|---|---|---|\n"
               "| **通过** | `<待人工>` | 未勾 |\n| **退回** | `<待人工>` | 未勾 |\n")
# 同一形态、**已签**：结论栏表头带限定（实测：R0 的 `结论（通过/有条件通过/退回）`）⇒ 必须读成已签
B_QUALIFIED_SIGNED = ("# review\n\n| 角色 | 姓名 | 结论（通过/有条件通过/退回） | 签字 | 日期 |\n"
                      "|---|---|---|---|---|\n"
                      "| 主持人 | Demo | ☐ 通过 ☑ **有条件通过** ☐ 退回 | Demo | 2026-01-01 |\n")


def base_fixture(root):
    _w(root, "ninedim/02-枢纽A-前置闸/评审-前置-DEMO-001-v0.1.md", A_OK)
    _w(root, "ninedim/03-执行环/_索引.md", "| 件 | 是什么 |\n|---|---|\n")
    _w(root, "ninedim/03-执行环/02-实现/实现-DEMO-001-v0.1.md", "# 实现\n")
    _w(root, "ninedim/04-枢纽B-后置闸/评审-后置-DEMO-001-v0.1.md",
       "# 后置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
       "| 主持人 | Demo | ☑ 通过 | Demo | 2026-01-01 |\n")
    _w(root, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_OK)


def _empty_exec(root):
    p = os.path.join(root, *"ninedim/03-执行环/02-实现".split("/"))
    for f in os.listdir(p):
        os.remove(os.path.join(p, f))


def _rm_dir(root, rel):
    shutil.rmtree(os.path.join(root, *rel.split("/")), ignore_errors=True)


def _no_archive(root):
    """归档面**整块不在**（F-02a 的复现形态）。"""
    _rm_dir(root, "ninedim/06-变更/archive")


def _archive_empty(root):
    """归档面在盘、但**0 个变更夹**（真·空集）。"""
    d = os.path.join(root, *"ninedim/06-变更/archive".split("/"))
    for x in os.listdir(d):
        p = os.path.join(d, x)
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)


def _no_a_side(root):
    _rm_dir(root, "ninedim/02-枢纽A-前置闸")


# 复核席 F-02b 的**实盘形态**：归档夹里躺着一份 `review.md`，内容是逐字的
# `| 批准人 | `<待人工>` |` ＋ `| 结论 | 待签 |` ⇒ 必须报「评审面**未签**」，
# **不许**报「一件评审件都没有」（那份件就在目录里）。
REAL_UNSIGNED_ARCH = "9999-01-01-rev-unsigned"


def selftest():
    cases = []

    def add(name, mut, want, msgs, forbid=(), status=None):
        """`want`＝期望 rc；`msgs`＝红文里必须有的子串；`forbid`＝红文里**不许**有的子串
        （专防"红的对、话是假的"）；`status`＝期望的 `STATUS`（`None`＝不查）。"""
        cases.append((name, mut, want, msgs, forbid, status))

    add("正控：A 已签批准、归档件已签", None, 0, [], (), "PASS")
    add("正控：A 未批（有评审件）但执行环也没产物", lambda d: _empty_exec(d), 0, [], (), "PASS")
    add("正控：A 一件评审件都没有且执行环无产物 ⇒ S-A 空集单列，不许 PASS",
        lambda d: (_no_a_side(d), _empty_exec(d)), 0, [], (), "SKIP")
    add("正控：归档面为空集（archive 在盘、0 个变更夹）⇒ 不许 PASS",
        lambda d: _archive_empty(d), 0, [], (), "SKIP")
    add("★正控（F-02a 的钉子）：archive/ **整块不在盘上** ⇒ 不许 PASS（要 [EMPTY]＋SKIP）",
        lambda d: _no_archive(d), 0, [], (), "SKIP")
    add("正控：归档结论头是「批准」、括号里引了「退回」分档枚举（引文不算结论）",
        lambda d: _w(d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_QUOTED_ENUM),
        0, [], (), "PASS")
    add("正控：结论栏表头带限定（`结论（通过/有条件通过/退回）`）而该行已签 ⇒ 必须算已签",
        lambda d: _w(d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_QUALIFIED_SIGNED),
        0, [], (), "PASS")
    add("反例 S-A：A 未签（结论未勾、签字空）＋执行环有产物",
        lambda d: _w(d, "ninedim/02-枢纽A-前置闸/评审-前置-DEMO-001-v0.1.md", A_UNSIGNED),
        1, ["[S-A]"], (), "FAIL")
    add("反例 S-A：A 结论☑通过但签字栏是空",
        lambda d: _w(d, "ninedim/02-枢纽A-前置闸/评审-前置-DEMO-001-v0.1.md",
                     "# 前置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
                     "| 主持人 | `<待人工>` | ☑ 通过 |  |  |\n"), 1, ["[S-A]"], (), "FAIL")
    # ★★ 真实违规同形态（复核席 F-02b）：那份 review.md **在目录里**，只是未签 ⇒
    #    必须说"未签"，**不许**说"一件评审件都没有"。
    add("★反例 S-B（真实形态）：归档夹里那份 review.md 在、只是未签 ⇒ 必须说「未签」",
        lambda d: _w(d, "ninedim/06-变更/archive/%s/review.md" % REAL_UNSIGNED_ARCH, B_UNSIGNED),
        1, ["[S-B]", REAL_UNSIGNED_ARCH, "评审面**未签**"], ("一件评审件都没有",), "FAIL")
    add("反例 S-B：归档件结论「待签」（原夹具件）",
        lambda d: _w(d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_UNSIGNED),
        1, ["[S-B]", "评审面**未签**"], ("一件评审件都没有",), "FAIL")
    add("反例 S-B：归档目录里**一件评审件都没有** ⇒ 只许说「一件评审件都没有」",
        lambda d: os.remove(os.path.join(d, *"ninedim/06-变更/archive/2026-01-01-demo/review.md".split("/"))),
        1, ["[S-B]", "一件评审件都没有"], ("评审面**未签**",), "FAIL")
    add("反例 S-B：归档夹里只有 `design.md`（非评审件）⇒ 仍须说「一件评审件都没有」",
        lambda d: (os.remove(os.path.join(d, *"ninedim/06-变更/archive/2026-01-01-demo/review.md".split("/"))),
                   _w(d, "ninedim/06-变更/archive/2026-01-01-demo/design.md", "# 设计\n")),
        1, ["[S-B]", "一件评审件都没有"], ("评审面**未签**",), "FAIL")
    add("反例 S-B：判「退回」却已归档", lambda d: _w(
        d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_REJECT), 1, ["[S-B]", "退回"], (), "FAIL")
    add("反例 S-B：结论写「批准」但批准人栏是 `<待人工>`", lambda d: _w(
        d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_PLACEHOLDER),
        1, ["[S-B]", "评审面**未签**"], ("一件评审件都没有",), "FAIL")
    add("反例 S-B：结论栏表头带限定、勾选栏留 `<待人工>`（未签）", lambda d: _w(
        d, "ninedim/06-变更/archive/2026-01-01-demo/review.md", B_QUALIFIED),
        1, ["[S-B]", "评审面**未签**"], ("一件评审件都没有",), "FAIL")
    add("反例 S-B：归档目录无评审件、而 04- 有已签件但没点名它",
        lambda d: (os.remove(os.path.join(d, *"ninedim/06-变更/archive/2026-01-01-demo/review.md".split("/"))),
                   _w(d, "ninedim/06-变更/archive/2026-01-02-other/review.md", B_OK),
                   os.remove(os.path.join(d, *"ninedim/06-变更/archive/2026-01-02-other/review.md".split("/")))),
        1, ["[S-B]", "2026-01-02-other"], (), "FAIL")

    ok = 0
    print("== signoff_guard --self-test（正控 ＋ 每条判据各一个反例）==")
    with tempfile.TemporaryDirectory(prefix="signoff-base-") as base:
        base_fixture(base)
        rc0, reds0, st0 = run(base, quiet=True)
        good0 = (rc0 == 0) and st0 == "PASS"
        ok += 1 if good0 else 0
        print("   [%s] %-46s rc=%d／STATUS=%s（期望 0／PASS）%s"
              % ("OK " if good0 else "★错", "正控：A 已签批准、归档件已签", rc0, st0,
                 "" if good0 else "红：" + "；".join(reds0)))
        for name, mut, want, msgs, forbid, status in cases[1:]:
            with tempfile.TemporaryDirectory(prefix="signoff-case-") as d:
                root = os.path.join(d, "repo")
                shutil.copytree(base, root)
                mut(root)
                rc, reds, st = run(root, quiet=True)
                blob = "\n".join(reds)
                miss = [m for m in msgs if m not in blob]
                hit = [f for f in forbid if f in blob]
                good = (rc == want) and not miss and not hit \
                    and (status is None or st == status)
                if good:
                    ok += 1
                print("   [%s] %-46s rc=%d／STATUS=%s（期望 %d／%s）%s"
                      % ("OK " if good else "★错", name, rc, st, want, status or "—",
                         "" if good else "  缺：%s  多：%s  实得：%s"
                         % ("，".join(miss), "，".join(hit), blob[:200])))
        print("   自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def main():
    ap = argparse.ArgumentParser(description="NineDim 判据：两个枢纽的签字面")
    ap.add_argument("--root", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return selftest()
    root = _ROOT_INJECTED or a.root or _ROOT_DEFAULT
    if not os.path.isdir(root):
        print("   ★ 仓根不在：%s（读不到＝判不了，rc=2）" % root)
        return 2
    rc, _, _st = run(root, list_only=a.list)
    return rc


if __name__ == "__main__":
    sys.exit(main())
