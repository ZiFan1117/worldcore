#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""junk_boundary.py —— 废料夹的**越界判据**：**同一条内容既在 `99-废料/`、又在正文件／记录里 ⇒ 红**。

口径的权威出处
--------------
`ninedim/99-废料/_索引.md` §三（逐字）：
「**同一条内容既在本夹、又在正文件／记录里出现 ⇒ 红**」，两条理由——
① **防"两处真相"**：同一事实两个载体 ⇒ 读者不知道信哪一份；
② **防"把正件藏进废料"**：正文件不许借"废料"这个口袋躲开 `01-意图环/**` 的判据面
   （⑧无修订记录／⑯撤回说法、`spec_shape`、`module_size_guard` 面② 等）。
⇒ 本件就是它的执行者；**兑现方式**（同 §三）：按**内容指纹**（规范化 sha256／逐行集合）
与「正文件 ＋ 记录」比，命中 ⇒ 红。

两条判据（各自可判真假；`--self-test` 先证明它真会红且**指名到件**）
------------------------------------------------------------------
* **J-01 整件重复**：废料件的**规范化全文 sha256** 与某个正文件／记录件**相同** ⇒ 红。
  规范化＝逐行 `rstrip`、丢空行、以 `\\n` 连接（⇒ 只差行尾空格/多余空行的副本仍能被认出）。
* **J-02 逐行重复**：废料件里某条**实质行**（规范化后长度 ≥ `SUBSTANTIVE_MIN_LEN`）在正文件／记录里
  也出现 ⇒ 红。为什么必须有这一条：J-01 只抓"整件副本"，而"**把正件的一段粘进废料的长件里**"
  同样造成两处真相（`_索引.md` §三 要防的正是这个）。

★ 射程（如实写，别读成"废料夹已清净"）
--------------------------------------
* **被检面**＝`ninedim/99-废料/**` 的**在册废料件**（除索引 `_索引.md` 以外）**＋ 索引件自身**
  （拿索引当"正件的口袋"同样要抓）。**空集判据挂在"在册件"上**：只有索引、没有在册件 ⇒
  `[EMPTY]` ＋ `STATUS=SKIP`（**未校验 ≠ 通过**，不许 PASS）——真仓今天就是这个状态。
  ★ 但**命中优先于空集**：索引件里若真抄了一份正件，那是真违规，**不许**被"空集"折成 ⏭。
* **比较面**＝`ninedim/**` **减去** `99-废料/`（被检面）**减去** `06-变更/`／`07-待审/`（**过程件**：
  它们在 `design.md`／`tasks.md` 里**引用**废料口径与内容是**合法**的，扫进来只会得到假红）。
  ⇒ 本判据**不**覆盖"废料件与某个过程件重复"这一格（那一格由人读；如实登记，不冒充覆盖）。
* **实质行过滤**＝"规范化后 ≥ `SUBSTANTIVE_MIN_LEN` 个字符"。它会**漏掉**"两处只重复一句短话"的形态；
  也会把长而通用的句子（如国标表格骨架）判成命中——**阈值是旋钮**，`--min-len N` 可调，改动要配反例。
* **只比 `ninedim/**`**：废料件与 `src/**`／`scripts/**`／`README.md` 的重复**不在**本件面内。
* **不判**"登记"那一半口径（`_索引.md` §一「**每件必须在本索引登记一行**——没登记就不许进」）：
  本件只判**越界（内容两处）**；登记面**今天无执行体**，已在报告里登记为缺口。

用法
----
    python scripts/verify/junk_boundary.py                # 判真仓
    python scripts/verify/junk_boundary.py --min-len 32   # 调实质行阈值（默认 24；与反例配套）
    python scripts/verify/junk_boundary.py --self-test    # 正控 ＋ 逐条反例（反例必红且指名）

退出码
------
    0 = 无越界，**或**显式 `STATUS=SKIP`（废料夹空／比较面空 ⇒ **未校验 ≠ 通过**）
    1 = 有越界（J-01 或 J-02 命中）
    2 = 用法错、仓根错
"""
import argparse
import contextlib
import hashlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except Exception:
        pass

# 被检面（废料夹）与比较面（正文件 ＋ 记录）
JUNK_TOP = "99-废料"
NINEDIM = "ninedim"
#: 比较面**排除**的顶层（理由见文件头"射程"）：过程件／未批候选里引用废料内容是合法的。
COMPARE_EXCLUDE_TOPS = (JUNK_TOP, "06-变更", "07-待审")
SKIP_DIRS = {".git", ".refs", "target", "node_modules", "__pycache__"}
#: 实质行阈值（规范化后字符数）——低于它的一律不算"同一条内容"（表格骨架／短标题会大量误报）。
SUBSTANTIVE_MIN_LEN = 24

OK, FAIL, EMPTY = "OK", "FAIL", "EMPTY"


# ────────────────────────── 工具 ──────────────────────────
def find_repo(start):
    """从 start 往上找含 `ninedim` 与 `scripts/verify` 的那一层（＝仓根）。"""
    p = Path(start).resolve()
    for cand in [p] + list(p.parents):
        if (cand / NINEDIM).is_dir() and (cand / "scripts" / "verify").is_dir():
            return cand
    return None


def rel(repo, p):
    return str(Path(p).resolve().relative_to(Path(repo).resolve())).replace("\\", "/")


def read_text(p):
    with io.open(p, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def _files(root, exts=None):
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if exts and not f.endswith(exts):
                continue
            out.append(Path(dp) / f)
    return sorted(out)


def junk_files(repo):
    """被检面：`ninedim/99-废料/**` 的全部件（**含 `_索引.md` 自身**——索引件也是本夹的一份字节，
    拿它当"正件的口袋"同样要被抓；自证 `反例⑧` 钉着这一条）。"""
    return _files(Path(repo) / NINEDIM / JUNK_TOP)


#: 废料夹的**索引件**名（每夹一份，是"登记表"不是"在册废料件"）。
JUNK_INDEX_NAME = "_索引.md"


def junk_items(repo):
    """**在册废料件**：`99-废料/**` 里除索引件以外的件。

    ★ 为什么把"空集判据"挂在**这一面**上：索引件是**每夹必备的登记表**（`_索引.md`），
    它的存在不等于"本夹有废料件"——今天真仓就是"只有索引、在册件为 (空)"。
    若拿"索引在不在"当非空判据，本判据就会在一个**没有废料件**的夹上打 PASS（假绿）。
    """
    return [p for p in junk_files(repo) if p.name != JUNK_INDEX_NAME]


def junk_index(repo):
    """废料夹的索引件（可能不存在）。它**仍进比较面**（防"拿索引当口袋"），但不计入"在册件"。"""
    p = Path(repo) / NINEDIM / JUNK_TOP / JUNK_INDEX_NAME
    return p if p.is_file() else None


def compare_files(repo):
    """比较面：`ninedim/**` 减去 `COMPARE_EXCLUDE_TOPS` 命中的**顶层**。"""
    root = Path(repo) / NINEDIM
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        parts = Path(dp).relative_to(root).parts
        if parts and parts[0] in COMPARE_EXCLUDE_TOPS:
            dn[:] = []
            continue
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            out.append(Path(dp) / f)
    return sorted(out)


def norm_text(t):
    """规范化：逐行 `rstrip`、丢空行、`\\n` 连接（只差行尾空格／多余空行的副本仍认得出）。"""
    return "\n".join(ln.rstrip() for ln in t.split("\n") if ln.strip())


def fingerprint(t):
    return hashlib.sha256(norm_text(t).encode("utf-8")).hexdigest()


def substantive_lines(t, min_len):
    """实质行：规范化（strip ＋ 内部空白折叠）后长度 ≥ `min_len` 的行 → {规范化行: 首个行号}。"""
    out = {}
    for i, ln in enumerate(t.split("\n"), 1):
        s = " ".join(ln.split())
        if len(s) >= min_len and s not in out:
            out[s] = i
    return out


# ────────────────────────── 判定 ──────────────────────────
def evaluate(repo, min_len):
    """返回 (rows, j01, j02, empty_reason)：rows＝被检件逐件（在册件 ＋ 索引件）；
    `empty_reason` 非空 ⇒ **空集**（没有可判的在册件／比较面为空）⇒ 不许判 PASS。"""
    items, idx = junk_items(repo), junk_index(repo)
    targets = ([("item", p) for p in items]
               + ([("index", idx)] if idx is not None else []))
    cf = compare_files(repo)
    if not items and not targets:
        return [], [], [], "废料夹不存在或为空（`%s/%s/` 下连索引件都没有）" % (NINEDIM, JUNK_TOP)
    if not items:
        empty_reason = ("废料夹**没有在册废料件**（只有索引 `%s`）——被检面为空"
                        % JUNK_INDEX_NAME) if idx is not None else "废料夹没有在册件"
    else:
        empty_reason = ""
    if not cf:
        return [], [], [], "比较面为空（`%s/**` 减掉 %s 后没有件）" % (NINEDIM, "／".join(COMPARE_EXCLUDE_TOPS))

    # 比较面索引：规范化指纹 → 件；实质行 → 件集合
    fp_index, line_index = {}, {}
    for p in cf:
        t = read_text(p)
        fp_index.setdefault(fingerprint(t), []).append(rel(repo, p))
        for s in substantive_lines(t, min_len):
            line_index.setdefault(s, set()).add(rel(repo, p))

    rows, j01, j02 = [], [], []
    for kind, p in targets:
        t = read_text(p)
        r = rel(repo, p)
        fp = fingerprint(t)
        rows.append({"path": r, "kind": kind, "lines": len(t.splitlines()), "fp": fp[:12],
                     "verdict": FAIL if fp in fp_index else OK})
        for other in fp_index.get(fp, []):
            j01.append((r, other))
        for s, ln in sorted(substantive_lines(t, min_len).items(), key=lambda kv: kv[1]):
            for other in sorted(line_index.get(s, ())):
                j02.append((r, ln, s, other))
    return rows, j01, j02, empty_reason


def run(repo, min_len, out=None):
    out = out if out is not None else sys.stdout
    rows, j01, j02, empty_reason = evaluate(repo, min_len)
    items, idx = junk_items(repo), junk_index(repo)
    print("== junk_boundary —— 废料夹越界判据（同一条内容两处 ⇒ 红）==", file=out)
    print("   仓根：%s" % repo, file=out)
    print("   被检面：`%s/%s/**`（在册件 %d 件；索引件 %s）｜比较面：`%s/**` 减 %s（%d 件）"
          "｜实质行阈值＝%d 字符"
          % (NINEDIM, JUNK_TOP, len(items), ("有" if idx is not None else "无"), NINEDIM,
             "／".join(COMPARE_EXCLUDE_TOPS), len(compare_files(repo)), min_len), file=out)

    if rows:
        print("   %-5s %-52s %-7s %6s %14s"
              % ("判定", "件", "类别", "行数", "规范化sha256前12"), file=out)
        for r in sorted(rows, key=lambda x: x["path"]):
            print("   %-5s %-52s %-7s %6d %14s"
                  % (r["verdict"], r["path"], r["kind"], r["lines"], r["fp"]), file=out)
        print("", file=out)
        print("── J-01 整件重复（规范化全文 sha256 相同）%d 条 ──" % len(j01), file=out)
        for a, b in j01:
            print("   [RED] `%s` ≡ `%s`（同一份内容两处 ⇒ 两处真相／把正件藏进废料）" % (a, b), file=out)
        print("── J-02 逐行重复（实质行 ≥%d 字符）%d 条 ──" % (min_len, len(j02)), file=out)
        for a, ln, s, b in j02:
            print("   [RED] `%s:%d` 的实质行也出现在 `%s` ⇒ %s"
                  % (a, ln, b, ("「%s」" % s[:60]) + ("…" if len(s) > 60 else "")), file=out)
        print("", file=out)
        print("── 汇总（现算）──", file=out)
        print("   被检件 %d 件（在册 %d ＋ 索引 %d）；J-01 %d 条 ＋ J-02 %d 条 ⇒ 红合计 %d"
              % (len(rows), len(items), 1 if idx is not None else 0,
                 len(j01), len(j02), len(j01) + len(j02)), file=out)

    # ★ 顺序要紧：**命中优先于空集**——索引件里若真抄了一份正件，那是真违规，不许被"空集"折成 ⏭。
    if j01 or j02:
        print("STATUS=FAIL", file=out)
        print("结论 = **红**：同一份内容在两处出现 ⇒ 要么删废料件、要么删正件里的那一份"
              "（**不许两处真相**；正文件不许借废料夹躲开判据面）", file=out)
        return 1
    if empty_reason:
        print("   [EMPTY] %s" % empty_reason, file=out)
        print("   ⇒ 按本仓口径**空集不许判绿**（不许出现「全校验通过」那一档字样）——"
              "本件打印 `STATUS=SKIP`（**未校验 ≠ 通过**），且不阻断全闸。", file=out)
        print("STATUS=SKIP", file=out)
        print("结论 = **未校验**（空集；**不是通过**）", file=out)
        return 0
    print("STATUS=PASS", file=out)
    print("结论 = 绿（废料夹里没有与正文件／记录重复的内容）", file=out)
    return 0


# ────────────────────────── 自证 ──────────────────────────
def _mk(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


#: 正控用的正文件（含一条 ≥24 字符的实质行）
GOOD_DOC = ("# 需求-沙盒\n\n"
            "系统 SHALL 在被请求时返回当前状态，且不得回放上一次的读数。\n")


def _base(tmp):
    _mk(tmp / "ninedim/01-意图环/02-需求/需求-沙盒.md", GOOD_DOC)
    _mk(tmp / "ninedim/records/台账-沙盒.md", "# 台账\n\n另起一行的记录内容，与本件无关。\n")
    _mk(tmp / "ninedim/99-废料/一次性-沙盒-2026-10-08.md",
        "# 一次性产物\n\n这是一份只此一处的临时导出，内容独一无二、不与任何正件重复。\n")
    (tmp / "scripts" / "verify").mkdir(parents=True, exist_ok=True)


def _run_on(root, min_len=SUBSTANTIVE_MIN_LEN):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run(root, min_len, out=buf)
    return rc, buf.getvalue()


def self_test():
    print("== junk_boundary --self-test ==")
    cases = []

    def case(label, setup, want_rc, must_in=None, must_not=None, min_len=SUBSTANTIVE_MIN_LEN):
        with tempfile.TemporaryDirectory(prefix="junk-") as d:
            tmp = Path(d)
            _base(tmp)
            if setup:
                setup(tmp)
            rc, output = _run_on(tmp, min_len)
        checks = ["rc=%d（期望 %d）" % (rc, want_rc)]
        ok = (rc == want_rc)
        if must_in:
            hit = must_in in output
            ok = ok and hit
            checks.append("输出%s `%s`" % ("含" if hit else "**缺**", must_in))
        if must_not:
            gone = must_not not in output
            ok = ok and gone
            checks.append("输出%s `%s`" % ("不含" if gone else "**竟含**", must_not))
        cases.append((label, ok, "；".join(checks)))
        return output

    # ── 正控：废料一件（唯一内容）、正件一件 ⇒ 不红 ──
    case("正控（废料件内容独一无二；与正件/记录都不重复）⇒ 绿", None, 0,
         must_in="STATUS=PASS")

    # ── 反例① 整件复制 ⇒ J-01 红，且**指名两件** ──
    def _copy(t):
        _mk(t / "ninedim/99-废料/抄件-沙盒.md", GOOD_DOC)
    case("反例①（J-01：把正文件整件抄进废料夹）⇒ 红且指名两件",
         _copy, 1, must_in="ninedim/99-废料/抄件-沙盒.md")

    # ── 反例② 逐行重复（长件里粘一段正件）⇒ J-02 红，且指名该行 ──
    def _line(t):
        _mk(t / "ninedim/99-废料/长件-沙盒.md",
            "# 临时长件\n\n" + "与本判据无关的第一段。\n\n"
            "系统 SHALL 在被请求时返回当前状态，且不得回放上一次的读数。\n\n"
            "与本判据无关的第二段。\n")
    case("反例②（J-02：废料长件里粘了一整条正件的实质行）⇒ 红",
         _line, 1, must_in="ninedim/99-废料/长件-沙盒.md")

    # ── 对照③ 只在废料夹一处 ⇒ 不红（正控已覆盖，再钉一条"独立内容"）──
    def _solo(t):
        _mk(t / "ninedim/99-废料/独一份-沙盒.md",
            "# 独一份\n\n这段话只在本夹里出现过一次，正文件与记录里都没有它。\n")
    case("对照③（内容只在废料夹一处）⇒ 不红", _solo, 0, must_in="STATUS=PASS")

    # ── 对照④ 只在正文件一处 ⇒ 不红 ──
    def _only_doc(t):
        _mk(t / "ninedim/01-意图环/02-需求/另加.md",
            "# 另加\n\n这段话只在正文件里出现，废料夹里一个字都没有，不应被判红。\n")
    case("对照④（内容只在正文件一处）⇒ 不红", _only_doc, 0, must_in="STATUS=PASS")

    # ── 反例⑤ 空集：**只有索引、没有在册件** ⇒ `[EMPTY]` ＋ `STATUS=SKIP`，不许 `STATUS=PASS` ──
    def _empty(t):
        shutil.rmtree(t / "ninedim/99-废料")
        _mk(t / "ninedim/99-废料/_索引.md", "# 99-废料 · 索引\n\n（空）—— 本夹刚建，尚无在册件。\n")
    out5 = case("反例⑤（废料夹只有在册件为空：只剩索引）⇒ `[EMPTY]`／`STATUS=SKIP`（**未校验 ≠ 通过**）",
                _empty, 0, must_in="STATUS=SKIP", must_not="STATUS=PASS")
    cases.append(("反例⑤b（空集时输出里必须出现 `[EMPTY]` 字样，且写明不是通过）",
                  ("[EMPTY]" in out5) and ("不是通过" in out5),
                  "含 `[EMPTY]` 与「不是通过」"))

    # ── 对照⑥ 短行／表格骨架／短标题重复 ⇒ 不红（实质行阈值在起作用）──
    #   ★ 夹具要点：两件的**骨架相同、全文不同**（废料件多出一段独有长文）——
    #     若整件内容一模一样，那命中 J-01（整件重复）是**对的**，测不到"阈值过滤"这件事。
    def _skeleton(t):
        _mk(t / "ninedim/99-废料/骨架-沙盒.md",
            "# 沙盒\n\n| 项 | 值 |\n|---|---|\n| 甲 | 乙 |\n\n"
            "本夹件的独有尾段：这段文字只出现在废料夹这一件里，与正件不重复。\n")
        _mk(t / "ninedim/01-意图环/02-需求/骨架正件.md",
            "# 沙盒\n\n| 项 | 值 |\n|---|---|\n| 甲 | 乙 |\n\n"
            "正件件的独有尾段：这段文字只出现在正文件这一件里，与废料夹不重复。\n")
    case("对照⑥（只有表格骨架／短标题重复 ⇒ 不红；阈值 %d 字符在起作用）" % SUBSTANTIVE_MIN_LEN,
         _skeleton, 0, must_in="STATUS=PASS")

    # ── 反例⑦ 仓根错 ⇒ rc=2 ──
    with tempfile.TemporaryDirectory(prefix="junk-") as d:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc7 = main(["--repo", str(Path(d) / "no-such")])
    cases.append(("反例⑦（`--repo` 指到不存在的仓根）⇒ rc=2", rc7 == 2, "rc=%d（期望 2）" % rc7))

    # ── 反例⑧ **索引件也在被检面内**：只在索引里抄一份正件（在册件为空）⇒ **仍须红** ──
    #   ★ 这一条同时钉住"**命中优先于空集**"：若把空集折成 SKIP 而不看索引，拿索引当口袋就能躲过去。
    def _via_index(t):
        shutil.rmtree(t / "ninedim/99-废料")
        _mk(t / "ninedim/99-废料/_索引.md", GOOD_DOC)
    case("反例⑧（只在索引里抄正件：在册件为空但索引命中）⇒ **仍须红**（命中优先于空集）",
         _via_index, 1, must_in="ninedim/99-废料/_索引.md", must_not="STATUS=SKIP")

    # ── 对照⑨ **比较面排除过程件**：`06-变更/` 里引用废料件的原文 ⇒ 不红 ──
    def _in_change(t):
        _mk(t / "ninedim/06-变更/2026-01-01-x/design.md",
            "# Design\n\n这段话只在本夹里出现过一次，正文件与记录里都没有它。\n")
    case("对照⑨（相同内容在 `06-变更/`（过程件）里 ⇒ 不红：过程件引用是合法的）",
         _in_change, 0, must_in="STATUS=PASS")

    bad = 0
    for label, ok, detail in cases:
        print("  %s %s ⇒ %s" % ("✅" if ok else "❌", label, detail))
        if not ok:
            bad += 1
    print("  自证：%d/%d 例通过" % (len(cases) - bad, len(cases)))
    if bad:
        print("  => 自证**不通过**：%d 例不符；按本仓口径，这条守卫是装饰，拒绝合入。" % bad)
        return 1
    print("  => 自证通过：正控绿 ＋ 反例逐条红且**指名到件/到行**"
          "（J-01 整件重复／J-02 逐行重复／索引件当口袋／空集 SKIP／阈值过滤／仓根错）")
    print("     （「不应红」的对照 4 处：只在废料一处、只在正件一处、只有骨架短行重复、"
          "相同内容在过程件 `06-变更/` 里）")
    return 0


# ────────────────────────── 入口 ──────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="废料夹越界判据（同一条内容既在 99-废料/、又在正文件／记录里 ⇒ 红）")
    ap.add_argument("--repo", default=None, help="仓根；默认从本脚本位置向上找（含 ninedim 与 scripts/verify）")
    ap.add_argument("--min-len", type=int, default=SUBSTANTIVE_MIN_LEN,
                    help="实质行阈值（规范化后字符数；默认 %d）" % SUBSTANTIVE_MIN_LEN)
    ap.add_argument("--self-test", action="store_true", help="正控 ＋ 逐条反例（反例必红且指名）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.min_len < 1:
        print("* `--min-len` 必须是正整数。", file=sys.stderr)
        print("STATUS=ERROR", file=sys.stderr)
        return 2
    repo = Path(args.repo) if args.repo else find_repo(Path(__file__).parent)
    if not repo or not Path(repo).is_dir():
        print("* 仓根错／找不到（要有 `ninedim/` 与 `scripts/verify/`）；用 `--repo` 指定。", file=sys.stderr)
        print("STATUS=ERROR", file=sys.stderr)
        return 2
    return run(repo, args.min_len)


if __name__ == "__main__":
    sys.exit(main())
