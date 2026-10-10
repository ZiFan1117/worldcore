#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""junk_boundary.py —— 废料夹的两条口径，做成会红的判据：**越界（内容两处）** ＋ **登记**。

口径的权威出处
--------------
`ninedim/99-废料/_索引.md`：
* §三（逐字）：「**同一条内容既在本夹、又在正文件／记录里出现 ⇒ 红**」——
  ① **防"两处真相"**：同一事实两个载体 ⇒ 读者不知道信哪一份；
  ② **防"把正件藏进废料"**：正文件不许借"废料"这个口袋躲开 `01-意图环/**` 的判据面
     （⑧无修订记录／⑯撤回说法、`spec_shape`、`module_size_guard` 面② 等）。
* §一（逐字）：「**进夹规矩**：**每件必须在本索引登记一行**（**件名 ｜ 谁的 ｜ 为什么留 ｜ 什么时候该清**）
  ——**没登记就不许进**」＋「**清之前先在本索引写一行**（不许静默删）」。
  ★ 这一半**今天没有执行体 ⇒ 那句是装饰**（本仓口径：不会红的判据只配当返工项）⇒ 本件把它补上。

三条判据（各自可判真假；`--self-test` 先证明它真会红且**指名到件/到行**）
------------------------------------------------------------------------
* **J-01 整件重复**：废料件的**规范化全文 sha256** 与某个正文件／记录件相同 ⇒ 红。
  规范化＝逐行 `rstrip`、丢空行、`\\n` 连接（⇒ 只差行尾空格/多余空行的副本仍认得出）。
* **J-02 逐行重复**：废料件里某条**实质行**（规范化后 ≥ `SUBSTANTIVE_MIN_LEN` 字符）在正文件／记录里
  也出现 ⇒ 红。为什么必须有：J-01 只抓"整件副本"，而"**把正件的一段粘进废料的长件里**"
  同样造成两处真相（§三 要防的正是这个）。
* **J-03 登记面**（§一 前半句）：
  · **有件未登记** ⇒ 红（指名那件）；
  · **缺栏** ⇒ 红：登记行必须**四栏俱全**（`件名 ｜ 谁的 ｜ 为什么留 ｜ 什么时候该清`），
    否则"登记"会退化成只写个件名；
  · **同名重复登记** ⇒ 红；
  · **缺 `_索引.md` 而有件** ⇒ 红（本夹是**唯一索引**，没有它"登记过没有"无从判）。
* **J-04 清空面**（§一 后半句；作者裁 2026-10-08 批准补）：
  · 索引里有「**已清（时点／谁）**」的留痕、而**件仍在盘上** ⇒ **红**（自己打自己脸）；
  · 件**已不在盘上**、而**没有任何一行**留了「已清（时点／谁）」⇒ **红**（**静默删**——本仓最恨的形态）。
  · ★★ **口径（作者要求逐字写进件头，免得下一个人以为闸能替他判时机）**：
    「**机器只能判『清前留没留一行』，判不了『到没到期』（到期由人判）**」。
    该清时点写在登记表第四栏、由**人**判；本件判的只是**留痕**。
  · 「已清」的**形态关**：须带**括号说明或日期**（`已清（2026-10-09／张三）`／`已清 2026-10-09`）；
    只写「已清」两个字**不算**留痕（否则"写两个字过关"会把这半边口径架空）。

★ 射程（如实写，别读成"废料夹已清净"）
--------------------------------------
* **被检面**＝`ninedim/99-废料/**` 的**在册废料件**（除索引 `_索引.md`）**＋ 索引件自身**
  （拿索引当"正件的口袋"同样要抓）。**空集判据挂在"在册件"上**：只有索引、没有在册件 ⇒
  `[EMPTY]` ＋ `STATUS=SKIP`（**未校验 ≠ 通过**，不许 PASS）——真仓今天就是这个状态。
  ★ 但**命中优先于空集**：索引里若真抄了一份正件、或真登记/清空得不实，那是真违规，
  **不许**被"空集"折成 ⏭。
* **比较面**（只给 J-01／J-02 用）＝`ninedim/**` **减去** `99-废料/`（被检面）**减去**
  `06-变更/`／`07-待审/`（**过程件**：它们在 `design.md`／`tasks.md` 里**引用**废料口径与内容是**合法**的）。
  ⇒ 本判据**不**覆盖"废料件与某个过程件重复"这一格（由人读；如实登记，不冒充覆盖）。
* **实质行过滤**＝"规范化后 ≥ `SUBSTANTIVE_MIN_LEN` 字符"。它会**漏掉**"两处只重复一句短话"的形态；
  也会把长而通用的句子判成命中——**阈值是旋钮**，`--min-len N` 可调，改动要配反例。
* **只比 `ninedim/**`**：废料件与 `src/**`／`scripts/**`／`README.md` 的重复**不在**本件面内。
* **J-04 只判留痕、不判时机**（如实写）：闸**判不了**"该清时点到没到期"——那是**人**的事；
  它也**不判**"清得对不对"（件该不该留证）。**别把它读成"废料都清干净了"**。
* ★ **J-04 的一个如实缺口**：**件与它的登记行一起删掉**（连一行 已清 都没留、登记行也没了）⇒
  本件**判不了**——盘上与索引里都**没有残留**可比（没有任何"曾存在过"的痕迹）。
  那一半只能靠 **git 历史**（`git log --diff-filter=D -- ninedim/99-废料/`）与审计去追；
  本件**不冒充覆盖**它。★ 同理，"已清痕"须与**件名同行**（同一行同时出现件名与已清痕）才算留痕——
  只写一句不点名的"已清"没有归属，等于没留（口径在 `cleaned_names()` 的 docstring 里）。

用法
----
    python scripts/verify/junk_boundary.py                # 判真仓
    python scripts/verify/junk_boundary.py --min-len 32   # 调实质行阈值（默认 24；与反例配套）
    python scripts/verify/junk_boundary.py --self-test    # 正控 ＋ 逐条反例（反例必红且指名）

退出码
------
    0 = 无违规，**或**显式 `STATUS=SKIP`（在册件为空 ⇒ **未校验 ≠ 通过**）
    1 = 有违规（J-01／J-02／J-03／J-04 任一命中）
    2 = 用法错、仓根错
"""
import argparse
import contextlib
import hashlib
import io
import os
import re
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
#: 索引件名（每夹一份）与登记表的**四栏**（§一 逐字：件名｜谁的｜为什么留｜什么时候该清）
JUNK_INDEX_NAME = "_索引.md"
REG_SECTION_KEY = "在册件"
REG_COLS = ("件名", "谁的", "为什么留", "什么时候该清")
#: 登记表里**合法的空表占位**（不是件名）
REG_PLACEHOLDERS = ("（空）", "—", "-", "")

OK, FAIL = "OK", "FAIL"


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


def _files(root):
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            out.append(Path(dp) / f)
    return sorted(out)


def junk_files(repo):
    """被检面：`ninedim/99-废料/**` 的全部件（**含 `_索引.md` 自身**——索引也是本夹的一份字节）。"""
    return _files(Path(repo) / NINEDIM / JUNK_TOP)


def junk_items(repo):
    """**在册废料件**：除索引件以外的件。

    ★ 为什么"空集判据"挂在**这一面**上：索引件是**每夹必备的登记表**，它的存在不等于"本夹有废料件"——
    今天真仓就是"只有索引、在册件为 (空)"。拿"索引在不在"当非空判据 ⇒ 本判据会在没有废料件的夹上打 PASS。
    """
    return [p for p in junk_files(repo) if p.name != JUNK_INDEX_NAME]


def junk_index(repo):
    """废料夹的索引件（可能不存在）。它**仍进 J-01/J-02 比较面**（防"拿索引当口袋"），但不计入在册件。"""
    p = Path(repo) / NINEDIM / JUNK_TOP / JUNK_INDEX_NAME
    return p if p.is_file() else None


def compare_files(repo):
    """比较面：`ninedim/**` 减去 `COMPARE_EXCLUDE_TOPS` 命中的**顶层**（只给 J-01／J-02 用）。"""
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


# ────────────────────────── J-03 登记面 ──────────────────────────
def parse_registry(idx_text):
    """解析 `_索引.md` 的「在册件」表；返回 (rows, problem)：
    rows＝[(行号, [四栏…])]（已滤掉表头／分隔行／`（空）` 占位）；problem≠None ⇒ **找不到该节**。"""
    lines = idx_text.split("\n")
    start = next((i for i, ln in enumerate(lines)
                  if ln.lstrip().startswith("#") and REG_SECTION_KEY in ln), None)
    if start is None:
        return None, "索引里**找不到「%s」节**（登记表的落点没有 ⇒ 无从判「登记过没有」）" % REG_SECTION_KEY
    rows = []
    for i in range(start + 1, len(lines)):
        s = lines[i].strip()
        if s.startswith("#"):
            break                                    # 下一个标题 ⇒ 本节结束
        if not s.startswith("|"):
            continue
        cells = [c.strip().strip("`* 　") for c in s.strip("|").split("|")]
        if not cells or all((not c) or set(c) <= set("-: ") for c in cells):
            continue                                 # 分隔行 `|---|---|`
        if cells[0] == REG_COLS[0] or cells[0] in REG_PLACEHOLDERS:
            continue                                 # 表头／空表占位
        rows.append((i + 1, cells))
    return rows, None


#: 「已清（时点／谁）」的**形态关**：须带**括号说明**（≥2 字）或**日期**——只写"已清"两字不算留痕。
CLEAN_MARK_RE = re.compile(r"已清\s*(?:[（(][^）)]{2,}[)）]|\d{4}-\d{2}-\d{2})")


def cleaned_names(idx_text, names):
    """索引里**留了「已清（时点／谁）」痕**的件名集合。

    判法（**认结构不认字样**，与本仓同族口径一致）：逐行看——那一行**既有**已清痕、**又出现**某件名，
    才把该件算作"已留痕"。⇒ 支持两种写法：登记行第四栏里写已清，或**另起一行**写
    `- 已清（2026-10-09／张三）：`某件.md``（口径原文正是"先在本索引**写一行**"）。
    """
    out = set()
    for ln in idx_text.split("\n"):
        if not CLEAN_MARK_RE.search(ln):
            continue
        for nm in names:
            if nm in ln:
                out.add(nm)
    return out


def check_registry(repo):
    """登记面 ＋ 清空面。返回 (j03, j04)：j03＝登记违规；j04＝清空留痕违规。

    ★ J-04 的口径（写死）：**机器只能判『清前留没留一行』，判不了『到没到期』（到期由人判）**。
    """
    j03, j04 = [], []
    items = junk_items(repo)
    idx = junk_index(repo)
    if idx is None:
        if items:
            j03.append("缺 `%s`（本夹是**唯一索引**）：有 %d 件在册废料件、却没有任何登记表 ⇒ "
                       "「每件必须在本索引登记一行」无从满足" % (JUNK_INDEX_NAME, len(items)))
        return j03, j04
    idx_text = read_text(idx)
    rows, problem = parse_registry(idx_text)
    if problem:
        return ["`%s` —— %s" % (rel(repo, idx), problem)], j04
    registered, seen = [], {}
    for ln, cells in rows:
        if len(cells) < len(REG_COLS) or any(not c for c in cells[:len(REG_COLS)]):
            j03.append("`%s:%d` —— 登记行**缺栏**：须四栏俱全（`%s`），实得 %d 栏 %s"
                       % (rel(repo, idx), ln, " ｜ ".join(REG_COLS), len(cells), cells))
            continue
        name = cells[0]
        if name in seen:
            j03.append("`%s:%d` —— **同名重复登记**（`%s` 已在第 %d 行登记过）"
                       % (rel(repo, idx), ln, name, seen[name]))
        seen[name] = ln
        registered.append((ln, name))
    have = {p.name for p in items}
    reg = {n for _, n in registered}
    for name in sorted(have - reg):
        j03.append("`%s/%s` —— **有件未登记**（§一：没登记就不许进；请在 `%s` 的「%s」表补一行四栏）"
                   % (JUNK_TOP, name, JUNK_INDEX_NAME, REG_SECTION_KEY))

    # ── J-04 清空面：**件在 ↔ 留痕**必须对得上（两个方向各判一条）──
    cleaned = cleaned_names(idx_text, have | reg)
    for name in sorted(have & cleaned):
        j04.append("`%s/%s` —— **件仍在盘上，索引里却写了「已清（…）」** ⇒ 登记与盘上不符"
                   "（要么把件清掉、要么把那行已清痕撤掉）" % (JUNK_TOP, name))
    for ln, name in sorted(registered, key=lambda x: x[0]):
        if name not in have and name not in cleaned:
            j04.append("`%s:%d` —— 登记了件 `%s`，而它**已不在盘上**、索引里**没有任何一行**写"
                       "「已清（时点／谁）」 ⇒ **静默删**（§一：清之前先写一行，不许静默删）"
                       % (rel(repo, idx), ln, name))
    return j03, j04


# ────────────────────────── 判定 ──────────────────────────
def evaluate(repo, min_len):
    """返回 (rows, j01, j02, j03, j04, empty_reason)。

    rows＝被检件（在册件 ＋ 索引件）；j01/j02＝越界命中；j03＝登记面；j04＝清空面；
    `empty_reason` 非空 ⇒ **在册件为空**（不许判 PASS）——但**命中优先于空集**。
    """
    items, idx = junk_items(repo), junk_index(repo)
    targets = [("item", p) for p in items] + ([("index", idx)] if idx is not None else [])
    j03, j04 = check_registry(repo)
    empty_reason = ""
    if not items:
        empty_reason = ("废料夹**没有在册废料件**（只有索引 `%s`）——被检面为空" % JUNK_INDEX_NAME
                        if idx is not None else "废料夹没有在册件")
    cf = compare_files(repo)
    j01, j02 = [], []
    if cf:
        fp_index, line_index = {}, {}
        for p in cf:
            t = read_text(p)
            fp_index.setdefault(fingerprint(t), []).append(rel(repo, p))
            for s in substantive_lines(t, min_len):
                line_index.setdefault(s, set()).add(rel(repo, p))
        for kind, p in targets:
            t = read_text(p)
            r = rel(repo, p)
            fp = fingerprint(t)
            for other in fp_index.get(fp, []):
                j01.append((r, other))
            for s, ln in sorted(substantive_lines(t, min_len).items(), key=lambda kv: kv[1]):
                for other in sorted(line_index.get(s, ())):
                    j02.append((r, ln, s, other))
    elif not j03 and not j04:
        empty_reason = empty_reason or ("比较面为空（`%s/**` 减掉 %s 后没有件）"
                                        % (NINEDIM, "／".join(COMPARE_EXCLUDE_TOPS)))
    rows = [{"path": rel(repo, p), "kind": kind, "lines": len(read_text(p).splitlines()),
             "fp": fingerprint(read_text(p))[:12]} for kind, p in targets]
    return rows, j01, j02, j03, j04, empty_reason


def run(repo, min_len, out=None):
    out = out if out is not None else sys.stdout
    rows, j01, j02, j03, j04, empty_reason = evaluate(repo, min_len)
    items, idx = junk_items(repo), junk_index(repo)
    print("== junk_boundary —— 废料夹判据（越界 J-01/J-02 ＋ 登记 J-03 ＋ 清空 J-04）==", file=out)
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
                  % (FAIL if (r["path"] in [a for a, _ in j01]) else OK,
                     r["path"], r["kind"], r["lines"], r["fp"]), file=out)

    print("", file=out)
    print("── J-01 整件重复（规范化全文 sha256 相同）%d 条 ──" % len(j01), file=out)
    for a, b in j01:
        print("   [RED] `%s` ≡ `%s`（同一份内容两处 ⇒ 两处真相／把正件藏进废料）" % (a, b), file=out)
    print("── J-02 逐行重复（实质行 ≥%d 字符）%d 条 ──" % (min_len, len(j02)), file=out)
    for a, ln, s, b in j02:
        print("   [RED] `%s:%d` 的实质行也出现在 `%s` ⇒ %s"
              % (a, ln, b, ("「%s」" % s[:60]) + ("…" if len(s) > 60 else "")), file=out)
    print("── J-03 登记面（每件须在本索引登记一行：%s）%d 条 ──" % (" ｜ ".join(REG_COLS), len(j03)),
          file=out)
    for x in j03:
        print("   [RED] %s" % x, file=out)
    print("── J-04 清空面（机器只判「清前留没留一行」，判不了「到没到期」）%d 条 ──" % len(j04),
          file=out)
    for x in j04:
        print("   [RED] %s" % x, file=out)

    print("", file=out)
    print("── 汇总（现算）──", file=out)
    print("   被检件 %d 件（在册 %d ＋ 索引 %d）；J-01 %d ＋ J-02 %d ＋ J-03 %d ＋ J-04 %d ⇒ 红合计 %d"
          % (len(rows), len(items), 1 if idx is not None else 0,
             len(j01), len(j02), len(j03), len(j04),
             len(j01) + len(j02) + len(j03) + len(j04)), file=out)

    # ★ 顺序要紧：**命中优先于空集**——索引里真抄了正件、或真登记/清空得不实，那是真违规，
    #   不许被"在册件为空"折成 ⏭（否则"拿索引当口袋"与"空登记／静默删"都能躲过判据）。
    if j01 or j02 or j03 or j04:
        print("STATUS=FAIL", file=out)
        print("结论 = **红**：%d 条（越界 %d ＋ 登记 %d ＋ 清空 %d）⇒ 两处真相／把正件藏进废料／"
              "登记不实／静默删，按 `ninedim/%s/_索引.md` §一§三 处置"
              % (len(j01) + len(j02) + len(j03) + len(j04), len(j01) + len(j02),
                 len(j03), len(j04), JUNK_TOP), file=out)
        return 1
    if empty_reason:
        print("   [EMPTY] %s" % empty_reason, file=out)
        print("   ⇒ 按本仓口径**空集不许判绿**（不许出现「全校验通过」那一档字样）——"
              "本件打印 `STATUS=SKIP`（**未校验 ≠ 通过**），且不阻断全闸。", file=out)
        print("STATUS=SKIP", file=out)
        print("结论 = **未校验**（空集；**不是通过**）", file=out)
        return 0
    print("STATUS=PASS", file=out)
    print("结论 = 绿（无越界；在册件与登记表双向一致、四栏俱全）", file=out)
    return 0


# ────────────────────────── 自证 ──────────────────────────
def _mk(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


#: 正控用的正文件（含一条 ≥24 字符的实质行）
GOOD_DOC = ("# 需求-沙盒\n\n"
            "系统 SHALL 在被请求时返回当前状态，且不得回放上一次的读数。\n")


def _index_text(names):
    """造一份合口径的 `_索引.md`：`names` 为空 ⇒ 用 `（空）` 占位行。"""
    head = ("# 99-废料 · 索引\n\n## 二、%s\n\n| %s |\n|---|---|---|---|\n"
            % (REG_SECTION_KEY, " | ".join(REG_COLS)))
    if not names:
        return head + "| （空） | — | — | — |\n"
    return head + "".join("| `%s` | 沙盒 | 反例夹具 | 判完即清 |\n" % n for n in names)


def _base(tmp):
    """正控底子：废料夹 1 件（**已登记、四栏俱全**）＋ 正文件 1 件 ＋ 记录 1 件，内容互不相同。"""
    name = "一次性-沙盒-2026-10-08.md"
    _mk(tmp / ("ninedim/99-废料/" + name),
        "# 一次性产物\n\n这是一份只此一处的临时导出，内容独一无二、不与任何正件重复。\n")
    _mk(tmp / "ninedim/99-废料/_索引.md", _index_text([name]))
    _mk(tmp / "ninedim/01-意图环/02-需求/需求-沙盒.md", GOOD_DOC)
    _mk(tmp / "ninedim/records/台账-沙盒.md", "# 台账\n\n另起一行的记录内容，与本件无关。\n")
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

    # ── 正控：越界面无命中 ＋ 登记面双向一致 ⇒ 绿 ──
    case("正控（废料件已登记四栏俱全；内容独一无二）⇒ 绿", None, 0, must_in="STATUS=PASS")

    # ── 反例① J-01 整件复制 ⇒ 红且**指名两件**（该件也登记了 ⇒ 只让 J-01 红，测单一面）──
    def _copy(t):
        _mk(t / "ninedim/99-废料/抄件-沙盒.md", GOOD_DOC)
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "抄件-沙盒.md"]))
    case("反例①（J-01：把正文件整件抄进废料夹）⇒ 红且指名两件",
         _copy, 1, must_in="ninedim/99-废料/抄件-沙盒.md")

    # ── 反例② J-02 逐行重复（长件里粘一段正件）⇒ 红 ──
    def _line(t):
        _mk(t / "ninedim/99-废料/长件-沙盒.md",
            "# 临时长件\n\n" + "与本判据无关的第一段。\n\n"
            "系统 SHALL 在被请求时返回当前状态，且不得回放上一次的读数。\n\n"
            "与本判据无关的第二段。\n")
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "长件-沙盒.md"]))
    case("反例②（J-02：废料长件里粘了一整条正件的实质行）⇒ 红",
         _line, 1, must_in="ninedim/99-废料/长件-沙盒.md")

    # ── 对照③／④ 内容只在一处 ⇒ 不红 ──
    def _solo(t):
        _mk(t / "ninedim/99-废料/独一份-沙盒.md",
            "# 独一份\n\n这段话只在本夹里出现过一次，正文件与记录里都没有它。\n")
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "独一份-沙盒.md"]))
    case("对照③（内容只在废料夹一处）⇒ 不红", _solo, 0, must_in="STATUS=PASS")
    case("对照④（内容只在正文件一处）⇒ 不红",
         lambda t: _mk(t / "ninedim/01-意图环/02-需求/另加.md",
                       "# 另加\n\n这段话只在正文件里出现，废料夹里一个字都没有，不应被判红。\n"),
         0, must_in="STATUS=PASS")

    # ── 反例⑤ 空集：**只有索引、没有在册件** ⇒ `[EMPTY]` ＋ `STATUS=SKIP`，不许 PASS ──
    def _empty(t):
        shutil.rmtree(t / "ninedim/99-废料")
        _mk(t / "ninedim/99-废料/_索引.md", _index_text([]))
    out5 = case("反例⑤（在册件为空：只剩索引）⇒ `[EMPTY]`／`STATUS=SKIP`（**未校验 ≠ 通过**）",
                _empty, 0, must_in="STATUS=SKIP", must_not="STATUS=PASS")
    cases.append(("反例⑤b（空集时输出里必须出现 `[EMPTY]`，且写明不是通过）",
                  ("[EMPTY]" in out5) and ("不是通过" in out5), "含 `[EMPTY]` 与「不是通过」"))

    # ── 对照⑥ 短行／表格骨架重复 ⇒ 不红（实质行阈值在起作用）──
    #   ★ 两件**骨架相同、全文不同**（各有一段独有长文）——若整件一模一样，命中 J-01 是对的，测不到阈值。
    def _skeleton(t):
        _mk(t / "ninedim/99-废料/骨架-沙盒.md",
            "# 沙盒\n\n| 项 | 值 |\n|---|---|\n| 甲 | 乙 |\n\n"
            "本夹件的独有尾段：这段文字只出现在废料夹这一件里，与正件不重复。\n")
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "骨架-沙盒.md"]))
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

    # ── 反例⑧ **索引件也在越界面内**：只在索引里抄一份正件（在册件为空）⇒ 仍须红 ──
    def _via_index(t):
        shutil.rmtree(t / "ninedim/99-废料")
        _mk(t / "ninedim/99-废料/_索引.md", GOOD_DOC)
    case("反例⑧（只在索引里抄正件：在册件为空但索引命中）⇒ **仍须红**（命中优先于空集）",
         _via_index, 1, must_in="ninedim/99-废料/_索引.md", must_not="STATUS=SKIP")

    # ── 对照⑨ **J-01/J-02 的比较面排除过程件**：`06-变更/` 里出现同样内容 ⇒ 不红 ──
    case("对照⑨（相同内容在 `06-变更/`（过程件）里 ⇒ 不红：过程件引用是合法的）",
         lambda t: _mk(t / "ninedim/06-变更/2026-01-01-x/design.md",
                       "# Design\n\n这段话只在本夹里出现过一次，正文件与记录里都没有它。\n"),
         0, must_in="STATUS=PASS")

    # ══ J-03 登记面（§一）══
    # ── 反例⑩ **有件未登记** ⇒ 红并指名那件 ──
    def _unreg(t):
        _mk(t / "ninedim/99-废料/没登记-沙盒.md", "# 没登记\n\n这是一件没有在索引里登记过的废料件。\n")
    case("反例⑩（J-03：有件但索引里**没登记**）⇒ 红并指名那件",
         _unreg, 1, must_in="ninedim/99-废料/没登记-沙盒.md")

    # ── 对照⑪ 全部登记 ⇒ 不红（正控已覆盖；再钉一条"多件全登记"）──
    def _all_reg(t):
        _mk(t / "ninedim/99-废料/第二件-沙盒.md", "# 第二件\n\n第二件独有内容，与别处都不重复。\n")
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "第二件-沙盒.md"]))
    case("对照⑪（两件**全部登记**、四栏俱全）⇒ 不红", _all_reg, 0, must_in="STATUS=PASS")

    # ── 反例⑫ **登记了盘上没有的件、且没有已清痕**（＝静默删的形态）⇒ 红并指名那行 ──
    def _ghost(t):
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "幽灵件-沙盒.md"]))
    case("反例⑫（J-03/J-04：索引里登记了一个**盘上不存在**且**无已清痕**的件）⇒ 红",
         _ghost, 1, must_in="幽灵件-沙盒.md")

    # ── 反例⑬ **登记行缺栏**（只写件名）⇒ 红（否则"登记"会退化成只写个件名）──
    def _short(t):
        _mk(t / "ninedim/99-废料/_索引.md",
            "# 99-废料 · 索引\n\n## 二、%s\n\n| %s |\n|---|---|---|---|\n"
            "| `一次性-沙盒-2026-10-08.md` | 沙盒 |\n" % (REG_SECTION_KEY, " | ".join(REG_COLS)))
    case("反例⑬（J-03：登记行**缺栏**——只写件名与『谁的』）⇒ 红",
         _short, 1, must_in="缺栏")

    # ── 反例⑭ **同名重复登记** ⇒ 红 ──
    def _dup(t):
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "一次性-沙盒-2026-10-08.md"]))
    case("反例⑭（J-03：同名**重复登记**）⇒ 红", _dup, 1, must_in="重复登记")

    # ── 反例⑮ **缺索引而有件** ⇒ 红（本夹是唯一索引）──
    def _no_index(t):
        (t / "ninedim/99-废料/_索引.md").unlink()
    case("反例⑮（J-03：**缺 `_索引.md`** 却有在册件）⇒ 红", _no_index, 1, must_in="唯一索引")

    # ══ J-04 清空面（§一 后半句）══
    # ── 反例⑯ **件仍在盘上、登记却标了「已清（…）」** ⇒ 红并指名（自己打自己脸）──
    #    ★ 夹具要点：登记行**四栏俱全**（J-03 干净）⇒ 让**只有 J-04** 这一条红，测的是单一面。
    def _cleaned_but_present(t):
        _mk(t / "ninedim/99-废料/_索引.md", _index_text(["一次性-沙盒-2026-10-08.md"]) + "\n"
            "- 已清（2026-10-09／沙盒）：`一次性-沙盒-2026-10-08.md`\n")
    case("反例⑯（J-04：件**仍在盘上**、索引里却写了「已清（时点／谁）」）⇒ 红并指名",
         _cleaned_but_present, 1, must_in="一次性-沙盒-2026-10-08.md")

    # ── 反例⑰ **件已不在盘上、登记行没有已清痕**（＝静默删）⇒ 红 ──
    def _silent_delete(t):
        (t / "ninedim/99-废料/一次性-沙盒-2026-10-08.md").unlink()   # 件删了，索引那一行照旧（无已清痕）
    case("反例⑰（J-04：件**已不在盘上**、索引里**没有**「已清（…）」痕迹）⇒ 红（静默删）",
         _silent_delete, 1, must_in="静默删")

    # ── 反例⑱ **只写「已清」两个字不算留痕**（形态关）⇒ 等同静默删 ⇒ 红 ──
    #    ★ 夹具要点：**登记行仍在**（否则"静默删"根本无从判——件名都不在册了）；
    #      删的是盘上的件 ＋ 只留一句不合成语（无括号/无日期）的「已清」。
    def _bare_cleaned(t):
        (t / "ninedim/99-废料/一次性-沙盒-2026-10-08.md").unlink()
        _mk(t / "ninedim/99-废料/_索引.md", _index_text(["一次性-沙盒-2026-10-08.md"]) + "\n"
            "- 已清：`一次性-沙盒-2026-10-08.md`\n")
    case("反例⑱（J-04：「已清」**不带括号说明或日期** ⇒ 不算留痕、等同静默删）⇒ 红",
         _bare_cleaned, 1, must_in="静默删")

    # ── 对照⑲ **件不在 + 留了「已清（时点／谁）」**（正常清理）⇒ 不红 ──
    def _proper_clean(t):
        (t / "ninedim/99-废料/一次性-沙盒-2026-10-08.md").unlink()
        _mk(t / "ninedim/99-废料/_索引.md", _index_text([]) + "\n"
            "- 已清（2026-10-09／沙盒）：`一次性-沙盒-2026-10-08.md`\n")
    case("对照⑲（J-04：件不在 ＋ 写了「已清（2026-10-09／沙盒）」＝正常清理）⇒ 不红",
         _proper_clean, 0, must_in="STATUS=SKIP")

    # ── 对照⑳ **件在 + 无已清痕**（正常在册）⇒ 不红；且**已清痕按件归属**（别件的痕不误伤本件）──
    def _attribution(t):
        _mk(t / "ninedim/99-废料/第二件-沙盒.md", "# 第二件\n\n第二件独有内容，与别处都不重复。\n")
        _mk(t / "ninedim/99-废料/_索引.md",
            _index_text(["一次性-沙盒-2026-10-08.md", "第二件-沙盒.md"]))
        (t / "ninedim/99-废料/第二件-沙盒.md").unlink()          # 第二件清了、且留痕
        _mk(t / "ninedim/99-废料/_索引.md", _index_text(["一次性-沙盒-2026-10-08.md", "第二件-沙盒.md"])
            + "\n- 已清（2026-10-09／沙盒）：`第二件-沙盒.md`\n")
    case("对照⑳（J-04：已清痕**按件归属**——只有第二件标了已清，第一件仍在册无痕）⇒ 不红",
         _attribution, 0, must_in="STATUS=PASS")

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
          "（J-01 整件重复／J-02 逐行重复／索引当口袋／空集 SKIP／阈值过滤／仓根错／"
          "**J-03 未登记／登记幽灵件／缺栏／重复登记／缺索引**／"
          "**J-04 件在却标已清／静默删／只写「已清」两字不算留痕**）")
    print("     （「不应红」的对照 %d 处——**由上面逐条打印的行现算**，此处不写死）"
          % sum(1 for label, _, _ in cases if "对照" in label))
    return 0


# ────────────────────────── 入口 ──────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="废料夹判据：越界（同一条内容既在 99-废料/、又在正文件／记录里 ⇒ 红）"
                    "＋ 登记（每件须在索引登记一行，四栏俱全）＋ 清空（清前须留痕）")
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
