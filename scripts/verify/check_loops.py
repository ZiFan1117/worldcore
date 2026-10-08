#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_loops.py —— 双环·四种循环（L1–L4）＋「九维都有活体」的可机检判据。

出处（逐字为准，不代标准复述）：
  · `11-ninedim/standard/双环与四种循环.md` §三（四种循环）／§五（七条可机检判据）／§六（证据落位）
  · `11-ninedim/standard/工程域-目录与命名.md` §九（九维在本棵树上的活体）＋§十（标准点名的九条判据）
  · `11-ninedim/standard/实现-九维怎么搭配.md` §一（工件 × 九维）

判据（八条，每条都会红；`--self-test` 逐条给反例）：
  ① 打回必有处置表        枢纽B 结论「退回」⇒ 必须有一张 L3 处置表，且其行点到那份评审
  ② 分流必须写理由        L3 处置表每行：分流判断 ∈ {回执行环, 回意图环}（恰一个）＋ 依据栏非空
  ③ 回执行环不得改规格     分流＝回执行环 ⇒ 该行「规格基线」指纹 == 现取规格指纹
  ④ 回意图环必须更新追溯矩阵 分流＝回意图环 ⇒ 该行「追溯矩阵指纹」== 现取 RTM 指纹
  ⑤ L4 必须递增版本＋追加 CHANGELOG 条目：每个归档目录在版本台账里有行、版本号合式且严格递增、CHANGELOG 点名它
  ⑥ 返工必有复跑读数       L1 返工台账每行：复跑命令非空 ＋ 退出码为数字
  ⑦ 澄清不得留两版         `ninedim/**` 不许出现 `*-旧`／`*-v1`／`*-copy`／`*.bak` 副本
  ⑧ 九维都有活体           每维 ≥1 活体件 ＋ ≥1 条「指得准的判据」（脚本在 ∧ 锚在 ∧ 真被 `check.sh` 调用）；**空集判红**

判据的输入是**台账件**（`ninedim/records/` 下的 `台账-*.md`；§六 落位的三件若日后搬到
`03-执行环/05-验证证据/`、`01-意图环/06-澄清记录/`、`04-枢纽B-后置闸/`，本脚本两处都认）。
台账件必须写一行 `条目计数：N`，且**表体真实条目数必须等于 N**（台账不许自欺）。

三档结局（**不许混**）：
  `[OK]`    判过且无红；
  `[EMPTY]` 判过：该判据的条目集**显式为空**（台账写 `条目计数：0`）——是"空集"，**不是"没跑"**；
  `[RED]`   有红（详情逐条打印）。

射程（如实声明，不粉饰）：
  · 本件判**痕迹与留证**，不判"结论对不对"（结论只有人能下）；
  · ③④ 用的是"落笔时的指纹"，故只能判"分流之后规格/矩阵动没动"；指纹由台账持有，台账失真则判不出；
  · ⑧ 的"指得准"＝静态三合一（脚本在 ∧ 锚在 ∧ 被 `check.sh` 调用），**不含**该判据当下的红绿
    （那由 `check.sh` 各自的步骤报，不在这里冒充）。
用法：`python check_loops.py [--root <仓根>] [--json]`｜`--self-test`（正控全绿 ＋ 每条各一个反例必红）
退出码：0=全绿（含空集）／1=有红／2=用法错或仓根不在。
"""
import argparse
import fnmatch
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile


def _harden_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_harden_stdout()

_ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_INJECTED = None


def set_root(path):
    """外部注入仓根（自证脚本用；注入优先于命令行与默认值）。"""
    global _ROOT_INJECTED
    _ROOT_INJECTED = path


# ── 台账：判据的输入 ────────────────────────────────────────────────────
# (台账键, 找哪些夹, 文件名关键词, 该台账「条目表」必须有的栏位)
LEDGERS = {
    "L1": (("ninedim/03-执行环/05-验证证据", "ninedim/records"), ("返工",),
           ("红在哪", "复跑命令", "退出码")),
    "L2": (("ninedim/01-意图环/06-澄清记录", "ninedim/records"), ("澄清",),
           ("问题", "结论")),
    "L3": (("ninedim/04-枢纽B-后置闸", "ninedim/records"), ("处置",),
           ("分流判断",)),
    "L4": (("ninedim/records",), ("归档",), ("归档目录", "版本")),
    "D9": (("ninedim/records",), ("九维活体",), ("维", "活体件", "判据脚本")),
}

# ⑦ 旧版副本：标准 §三 L2 逐字「出现 `*-旧`／`*-v1` 即红」
BAD_COPY = re.compile(r"(-旧|-v1(?![\d.])|-copy|\.bak|（旧）|旧版)")

# 占位（＝"没有值"）；★ 退出码列不用它（`0` 是合法退出码）
PLACEHOLDER = {"", "—", "-", "–", "无", "n/a", "na", "待填", "待人工", "未登记", "none"}

SEP = re.compile(r"[；;、,，]")


def _norm(s):
    return re.sub(r"[*`\s]", "", s or "")


def _is_ph(v):
    s = _norm(v)
    return (s in PLACEHOLDER) or ("待人工" in s) or ("待填" in s)


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def _is_sep(cells):
    return bool(cells) and all(re.match(r"^:?-{2,}:?$", c.strip()) for c in cells)


def tables(text):
    """把 markdown 表块切成 [(header, [row_cells, ...])]；表头剥掉 `**`。"""
    out, hdr, rows = [], None, []
    for line in text.splitlines():
        s = line.strip()
        if len(s) > 1 and s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s[1:-1].split("|")]
            if hdr is None:
                if _is_sep(cells):
                    continue
                hdr = [_norm(c) for c in cells]
                rows = []
            elif _is_sep(cells):
                continue
            else:
                rows.append(cells)
        else:
            if hdr is not None:
                out.append((hdr, rows))
            hdr, rows = None, []
    if hdr is not None:
        out.append((hdr, rows))
    return out


def table_with(text, cols):
    """第一张**含齐** cols 的表；没有则 None。"""
    for hdr, rows in tables(text):
        if all(c in hdr for c in cols):
            return hdr, rows
    return None


def cell(hdr, row, key):
    if key not in hdr:
        return None
    i = hdr.index(key)
    return row[i] if i < len(row) else None


def _md_files(d):
    out = []
    for dp, _dn, fn in os.walk(d):
        for f in fn:
            if f.endswith(".md"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def files_named(root, dirs, keywords):
    out = []
    for rel in dirs:
        base = os.path.join(root, *rel.split("/"))
        if not os.path.isdir(base):
            continue
        for p in _md_files(base):
            b = os.path.basename(p)
            if any(k in b for k in keywords):
                out.append(p)
    return sorted(set(out))


def declared_count(text):
    m = re.search(r"^条目计数[：:]\s*(\d+)\s*$", text, re.M)
    return int(m.group(1)) if m else None


def real_rows(rows):
    """表体里的**真条目行**（第一格是占位符的行是"占位/说明行"，不算条目）。"""
    return [r for r in rows if _norm(r[0] if r else "") not in PLACEHOLDER]


def ledger(root, key, res, cid):
    """取某本台账的条目表。返回 [(path, hdr, rows)]；台账不在／自欺 ⇒ 记红。"""
    dirs, kws, cols = LEDGERS[key]
    found = []
    problems = []
    for p in files_named(root, dirs, kws):
        txt = read(p)
        tb = table_with(txt, cols)
        if tb is None:
            continue
        hdr, rows = tb
        n = declared_count(txt)
        rr = real_rows(rows)
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        if n is None:
            problems.append("台账 %s **没写 `条目计数：N`** ⇒ 判不了（判不了 ≠ 通过）" % rel)
        elif n != len(rr):
            problems.append("台账 %s **自欺**：写 `条目计数：%d`，表体真条目实为 %d 条" % (rel, n, len(rr)))
        found.append((p, hdr, rows))
    if not found:
        problems.append("台账不在（找过：%s 下件名带「%s」且含栏 %s 的件）⇒ 判不了（判不了 ≠ 通过）"
                        % ("／".join(dirs), "／".join(kws), "／".join(cols)))
    for x in problems:
        res.red.append("[%s] %s" % (cid, x))
    return found


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def spec_fingerprint(root):
    """`04-规格/*.spec.md` 的聚合指纹（文件名 ＋ 各件 sha256，按名排序）。"""
    d = os.path.join(root, *"ninedim/01-意图环/04-规格".split("/"))
    if not os.path.isdir(d):
        return None
    items = sorted((f, _sha256(os.path.join(d, f))) for f in os.listdir(d) if f.endswith(".spec.md"))
    if not items:
        return None
    h = hashlib.sha256()
    for n, s in items:
        h.update(("%s %s\n" % (n, s)).encode("utf-8"))
    return "sha256:" + h.hexdigest()


def rtm_fingerprint(root):
    """需求追溯矩阵（`WC-RTM-*.csv`）指纹。"""
    d = os.path.join(root, *"ninedim/01-意图环/02-需求".split("/"))
    if not os.path.isdir(d):
        return None
    cs = sorted(f for f in os.listdir(d) if fnmatch.fnmatch(f, "WC-RTM*.csv"))
    if not cs:
        return None
    return "sha256:" + _sha256(os.path.join(d, cs[0]))


# ── 结论／签字 的读法（只认表结构，不认字样出现）────────────────────────
def verdict(celltext):
    """把一格"结论"读成 approve／reject／blank／other。

    三条读法（都是踩出来的）：
      · 有勾选框 ⇒ **只认 ☑ 标在哪个选项上**（`☑ 通过 ／ ☐ 退回` ＝ 通过）；
      · 一个都没勾 ⇒ **blank**（未签），不是"退回"；
      · 没有勾选框 ⇒ **只看结论头**：`（…）` 里的引文／枚举（如「R4 ＝ 通过／有条件通过／退回」）
        **不算结论**——2026-10-08 实测：`归档 …fc-2026-003` 的结论格是 `**批准**（…按 skill §十一
        「…R4 ＝ 通过／有条件通过／退回…」记…）`，早期实现把括号里的枚举读成了「退回」⇒ **假红**。
    """
    if celltext is None:
        return "blank"
    v = _norm(celltext)
    if "待人工" in v or "待签" in v:
        return "blank"
    marks = re.findall(r"☑\s*([^／/|☐☑]*)", celltext)
    if marks:
        t = " ".join(marks)
        if "退回" in t or "驳回" in t or "不通过" in t:
            return "reject"
        if "通过" in t or "批准" in t:
            return "approve"
        return "other"
    if "☐" in celltext:          # 有勾选框、一个都没勾 ⇒ 未签
        return "blank"
    head = re.split(r"[（(——★；;，,。]", v, 1)[0]
    if head in PLACEHOLDER:
        return "blank"
    if "退回" in head or "驳回" in head or "不通过" in head:
        return "reject"
    if "批准" in head or "通过" in head:
        return "approve"
    if head == v and (v == "" or v in PLACEHOLDER):
        return "blank"
    return "other"


def is_person_name(v):
    """签字栏取值是不是**人**（AI 不是人：本仓 `H-13` 逐字"AI 不代签"）。"""
    s = re.sub(r"[\s*`]", "", v or "")
    if len(s) < 2:
        return False
    if re.search(r"(待人工|待填|待签|机器|deepseek|DeepSeek|AI不|AI（|N/A)", s):
        return False
    if s in ("—", "-", "–", "无") or s.upper() == "AI":
        return False
    return bool(re.search(r"[A-Za-z\u4e00-\u9fa5]", s))


CONS_KEYS = ("结论", "结论栏", "评审结论")
SIGN_KEYS = ("签字", "签署", "签署人", "批准人", "主持人签署")


def _is_cons_key(k):
    """栏位名带限定也认（实测：`结论（EV-04 三选一）` 这种表头存在，不许漏读）。"""
    return k in CONS_KEYS or k.startswith("结论")


def _is_sign_key(k):
    return k in SIGN_KEYS or k.startswith("签字") or k.startswith("签署") or k == "批准人"


def _kv_of(hdr, rows):
    """两列表（`| 项 | 内容 |`）的行内键值：把左列当栏位名。"""
    if len(hdr) > 3:
        return None
    kv = {}
    for r in rows:
        if len(r) < 2:
            continue
        kv[_norm(r[0])] = r[1]
    return kv


def signed_verdict(text):
    """一件评审件的签字面：approve／reject／blank／other。

    两种表形态都认（**只认表结构，不认字样出现**）：
      · 栏位形态：表头就是栏位名（`| 角色 | 姓名 | 结论 | 签字 | 日期 |`）；
      · 键值形态：两列表（`| 项 | 内容 |`，左列里写「结论」「批准人」）。
    **同一行/同一表里既有结论、又有非 AI 的人名签字**才算签。
    """
    best = "blank"
    for hdr, rows in tables(text):
        # 形态一：栏位在表头
        for r in rows:
            cons = [verdict(cell(hdr, r, k)) for k in hdr if _is_cons_key(k)]
            signs = [cell(hdr, r, k) for k in hdr if _is_sign_key(k)]
            if not cons or not signs:
                continue
            if not any(is_person_name(s) for s in signs):
                continue
            for c in cons:
                if c in ("approve", "reject"):
                    return c
                if c == "other" and best == "blank":
                    best = "other"
        # 形态二：两列表的键值
        kv = _kv_of(hdr, rows)
        if not kv:
            continue
        cons = [verdict(v) for k, v in kv.items() if _is_cons_key(k)]
        signs = [v for k, v in kv.items() if _is_sign_key(k)]
        if not cons or not signs or not any(is_person_name(s) for s in signs):
            continue
        for c in cons:
            if c in ("approve", "reject"):
                return c
            if c == "other" and best == "blank":
                best = "other"
    return best


# ── 判据 ①–⑧ ─────────────────────────────────────────────────────────
class Res(object):
    def __init__(self, cid, title):
        self.cid, self.title = cid, title
        self.red, self.notes = [], []
        self.empty = None

    @property
    def status(self):
        if self.red:
            return "RED"
        return "EMPTY" if self.empty else "OK"


def _b_reviews(root):
    d = os.path.join(root, *"ninedim/04-枢纽B-后置闸".split("/"))
    if not os.path.isdir(d):
        return []
    return [p for p in _md_files(d) if os.path.basename(p) != "_索引.md"]


def c1(root, res):
    """① 打回必有处置表。"""
    inv, rejected = [], []
    for p in _b_reviews(root):
        st = signed_verdict(read(p))
        inv.append("%s=%s" % (os.path.basename(p), {"approve": "通过", "reject": "退回",
                                                    "blank": "未签/留空", "other": "未见结论"}[st]))
        if st == "reject":
            rejected.append(p)
    res.notes.append("枢纽B 评审件 %d 件：%s" % (len(inv), "；".join(inv) if inv else "一件都没有"))
    tables_l3 = []
    for p, hdr, rows in ledger(root, "L3", res, "①"):
        tables_l3.append((p, hdr, rows))
    if not rejected:
        res.empty = "0 件枢纽B判「退回」"
        return
    for p in rejected:
        base = os.path.basename(p)
        toks = re.findall(r"WC-[A-Za-z0-9-]+", base)
        hit = False
        for _lp, hdr, rows in tables_l3:
            for r in real_rows(rows):
                if any(t in " ".join(r) for t in toks):
                    hit = True
        if not hit:
            res.red.append("[①] %s 结论为「退回」，却查不到处置表（L3 台账里没有一行点到它）"
                           "——标准 §五 判据 1" % base)


def _l3_rows(root, res, cid):
    out = []
    for p, hdr, rows in ledger(root, "L3", res, cid):
        out.append((p, hdr, rows))
    return out


def c2(root, res):
    """② 分流必须写理由。"""
    tabs = _l3_rows(root, res, "②")
    n = 0
    for p, hdr, rows in tabs:
        for i, r in enumerate(real_rows(rows), 1):
            n += 1
            d = cell(hdr, r, "分流判断") or ""
            why = cell(hdr, r, "依据") or ""
            dn = _norm(d)
            has_exec = ("回执行" in dn)
            has_intent = ("回意图" in dn)
            if _is_ph(d):
                res.red.append("[②] %s 第 %d 条：分流判断栏为空 ⇒ 没写分流（标准 §五 判据 2）"
                               % (os.path.basename(p), i))
            elif not (has_exec or has_intent):
                res.red.append("[②] %s 第 %d 条：分流判断「%s」既不是回执行环、也不是回意图环"
                               "（只写「重做」不算分流）" % (os.path.basename(p), i, d[:30]))
            elif has_exec and has_intent:
                res.red.append("[②] %s 第 %d 条：分流判断同时写了回执行环与回意图环 ⇒ 分流不唯一"
                               % (os.path.basename(p), i))
            if _is_ph(why):
                res.red.append("[②] %s 第 %d 条：分流理由（依据栏）为空 ⇒ 只写了往哪退，没写为什么"
                               % (os.path.basename(p), i))
    if n == 0:
        res.empty = "0 条 L3 分流条目"


def c3(root, res):
    """③ 回执行环的不得改规格。"""
    cur = spec_fingerprint(root)
    tabs = _l3_rows(root, res, "③")
    n = 0
    for p, hdr, rows in tabs:
        for i, r in enumerate(real_rows(rows), 1):
            if "回执行" not in _norm(cell(hdr, r, "分流判断") or ""):
                continue
            n += 1
            fp = cell(hdr, r, "规格基线")
            if cur is None:
                res.red.append("[③] %s 第 %d 条：分流＝回执行环，但现取规格指纹取不到"
                               "（`04-规格/*.spec.md` 不在）⇒ 判不了（判不了 ≠ 通过）"
                               % (os.path.basename(p), i))
                continue
            if _is_ph(fp):
                res.red.append("[③] %s 第 %d 条：分流＝回执行环，却没落「规格基线」指纹 ⇒ 规格动没动判不了"
                               "（判不了 ≠ 通过）" % (os.path.basename(p), i))
            elif _norm(fp) != cur:
                res.red.append("[③] %s 第 %d 条：分流＝回执行环，但规格指纹对不上"
                               "（台账 %s ≠ 现取 %s）⇒ 回执行环的分支里规格被改过"
                               % (os.path.basename(p), i, _norm(fp)[:24], cur[:24]))
    if n == 0:
        res.empty = "0 条「回执行环」分流"


def c4(root, res):
    """④ 回意图环的必须更新追溯矩阵。"""
    cur = rtm_fingerprint(root)
    tabs = _l3_rows(root, res, "④")
    n = 0
    for p, hdr, rows in tabs:
        for i, r in enumerate(real_rows(rows), 1):
            if "回意图" not in _norm(cell(hdr, r, "分流判断") or ""):
                continue
            n += 1
            fp = cell(hdr, r, "追溯矩阵指纹")
            if cur is None:
                res.red.append("[④] %s 第 %d 条：分流＝回意图环，但追溯矩阵（`WC-RTM-*.csv`）不在"
                               "⇒ 判不了（判不了 ≠ 通过）" % (os.path.basename(p), i))
                continue
            if _is_ph(fp):
                res.red.append("[④] %s 第 %d 条：分流＝回意图环，却没落「追溯矩阵指纹」⇒ 矩阵更没更新判不了"
                               % (os.path.basename(p), i))
            elif _norm(fp) != cur:
                res.red.append("[④] %s 第 %d 条：分流＝回意图环，但追溯矩阵指纹对不上"
                               "（台账 %s ≠ 现取 %s）⇒ 改了承诺却没更新矩阵"
                               % (os.path.basename(p), i, _norm(fp)[:24], cur[:24]))
    if n == 0:
        res.empty = "0 条「回意图环」分流"


VER = re.compile(r"^v?\d+(?:\.\d+)*$")


def c5(root, res):
    """⑤ L4 必须递增版本并追加 CHANGELOG 条目。"""
    adir = os.path.join(root, *"ninedim/06-变更/archive".split("/"))
    arch = []
    if os.path.isdir(adir):
        arch = sorted(d for d in os.listdir(adir)
                      if os.path.isdir(os.path.join(adir, d)) and d != ".gitkeep")
    cl_path = os.path.join(root, "CHANGELOG.md")
    cl = read(cl_path) if os.path.isfile(cl_path) else None
    res.notes.append("已归档 change %d 个" % len(arch))
    tabs = ledger(root, "L4", res, "⑤")
    rows = []
    for _p, hdr, rws in tabs:
        for r in real_rows(rws):
            rows.append((hdr, r))
    if cl is None:
        res.red.append("[⑤] 仓根 `CHANGELOG.md` 不在 ⇒ 追加变更记录这条判不了（判不了 ≠ 通过）")
    if not arch:
        res.empty = "0 个已归档 change"
        return
    versions = []
    for d in arch:
        matched = None
        for hdr, r in rows:
            if _norm(cell(hdr, r, "归档目录") or "") == d:
                matched = (hdr, r)
                break
        if matched is None:
            res.red.append("[⑤] 归档 `%s` 在 L4 版本台账里**没有行** ⇒ 版本没留证（标准 §五 判据 5）" % d)
            continue
        hdr, r = matched
        raw_ver = cell(hdr, r, "版本")
        ver = _norm(raw_ver or "")
        if not VER.match(ver):
            res.red.append("[⑤] 归档 `%s` 的版本栏是「%s」——不是版本号（§三 L4 要求「版本号递增」）"
                           % (d, raw_ver))
        else:
            versions.append((d, ver))
        if cl is not None:
            num = cell(hdr, r, "变更号") or ""
            hit = (d in cl) or (not _is_ph(num) and _norm(num) in _norm(cl))
            if not hit:
                res.red.append("[⑤] 归档 `%s` 在 `CHANGELOG.md` 里**零命中** ⇒ 归档了却没追加变更记录" % d)
    # 版本严格递增（按归档目录名排序）
    for i in range(1, len(versions)):
        prev, cur = versions[i - 1], versions[i]
        if not _ver_gt(cur[1], prev[1]):
            res.red.append("[⑤] 版本没递增：`%s`=%s 之后 `%s`=%s（标准 §三 L4 要求版本号递增）"
                           % (prev[0], prev[1], cur[0], cur[1]))


def _ver_key(v):
    return tuple(int(x) for x in v.lstrip("v").split("."))


def _ver_gt(a, b):
    try:
        return _ver_key(a) > _ver_key(b)
    except Exception:
        return False


def c6(root, res):
    """⑥ 返工必有复跑读数。"""
    tabs = ledger(root, "L1", res, "⑥")
    n = 0
    for p, hdr, rows in tabs:
        for i, r in enumerate(real_rows(rows), 1):
            n += 1
            cmd = cell(hdr, r, "复跑命令") or ""
            rc = _norm(cell(hdr, r, "退出码") or "")
            if _is_ph(cmd):
                res.red.append("[⑥] %s 第 %d 条：有返工，却没有复跑命令 ⇒ 红在哪改了什么的读数不成立"
                               "（标准 §五 判据 6）" % (os.path.basename(p), i))
            elif not re.search(r"[A-Za-z\u4e00-\u9fa5]", cmd):
                res.red.append("[⑥] %s 第 %d 条：复跑命令「%s」不成一条命令"
                               % (os.path.basename(p), i, cmd[:30]))
            if not re.match(r"^(rc\s*=?\s*)?\d+$", rc):
                res.red.append("[⑥] %s 第 %d 条：退出码栏是「%s」——不是退出码（读不到 ⇒ 判不了）"
                               % (os.path.basename(p), i, cell(hdr, r, "退出码")))
    if n == 0:
        res.empty = "0 条返工记录"


def c7(root, res):
    """⑦ 澄清不得留两版。"""
    eng = os.path.join(root, "ninedim")
    hits = []
    if os.path.isdir(eng):
        for dp, _dn, fn in os.walk(eng):
            for f in fn:
                if BAD_COPY.search(f):
                    hits.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    res.notes.append("扫 `ninedim/**` 全树文件名")
    for h in hits:
        res.red.append("[⑦] 出现旧版／副本 `%s` ⇒ 澄清要就地更新、不留两版（标准 §五 判据 7）" % h)
    if not hits:
        res.empty = "0 处旧版副本"


def _alive(root, spec):
    p = os.path.join(root, *spec.split("/"))
    if os.path.isfile(p):
        return os.path.getsize(p) > 0
    if os.path.isdir(p):
        for dp, _dn, fn in os.walk(p):
            for f in fn:
                if f not in ("_索引.md", ".gitkeep") and not f.endswith(".pyc"):
                    return True
        return False
    return False


def _exists_spec(root, spec):
    """标准点名件在不在：支持 `*`（含**中间层**的 `*`，如 `ninedim/06-变更/*/改动对照.md`）。"""
    if "*" in spec or "?" in spec:
        pat = os.path.join(root, *spec.split("/"))
        return any(os.path.exists(m) for m in glob.glob(pat))
    return os.path.exists(os.path.join(root, *spec.split("/")))


def c8(root, res):
    """⑧ 九维都有活体（每维 ≥1 活体件 ＋ ≥1 条指得准的判据；空集判红）。"""
    tabs = ledger(root, "D9", res, "⑧")
    cs_path = os.path.join(root, "check.sh")
    cs = read(cs_path) if os.path.isfile(cs_path) else ""
    if not cs:
        res.red.append("[⑧] 仓根 `check.sh` 不在 ⇒ 「被判据真调用」这一条判不了（判不了 ≠ 通过）")
    n_ok = 0
    n_clean = 0
    for p, hdr, rows in tabs:
        for r in real_rows(rows):
            before = len(res.red)
            dim = _norm(cell(hdr, r, "维") or "")
            carriers = [x.strip() for x in SEP.split(cell(hdr, r, "活体件") or "") if x.strip()]
            std = (cell(hdr, r, "标准点名件") or "").strip()
            scripts = [x.strip() for x in SEP.split(cell(hdr, r, "判据脚本") or "") if x.strip()]
            anchors = [x.strip() for x in SEP.split(cell(hdr, r, "锚") or "") if x.strip()]
            alive = [c for c in carriers if _alive(root, c)]
            if not carriers or not alive:
                res.red.append("[⑧] %s：**空集**——没有任何活体件在盘上（找过：%s）"
                               "（标准 §九「每一维都要有活体件」）"
                               % (dim, "；".join(carriers) or "（没声明）"))
                continue
            if not _is_ph(std) and not _exists_spec(root, std):
                res.red.append("[⑧] %s：标准点名的活体件 `%s` 不在盘上" % (dim, std))
            if not scripts or all(_is_ph(s) for s in scripts):
                res.red.append("[⑧] %s：有活体件，却**没有一条判据指着它**"
                               "（标准 `工程域-目录与命名.md:172`：某一维只有文档而没判据 ⇒ 红）" % dim)
                continue
            bad = []
            for s in scripts:
                if _is_ph(s):
                    continue
                sp = os.path.join(root, *s.split("/"))
                if not os.path.isfile(sp):
                    bad.append("判据脚本不在：`%s`" % s)
                    continue
                src = read(sp)
                missed = [a for a in anchors if not _is_ph(a) and a not in src]
                if missed:
                    bad.append("判据指不准：`%s` 里找不到锚 %s" % (s, "／".join(missed)))
                if os.path.basename(s) not in cs:
                    bad.append("判据没进 `check.sh`（闸不在门禁里等于没有闸）：`%s`" % s)
            if bad:
                res.red.append("[⑧] %s：%s" % (dim, "；".join(bad)))
            else:
                n_ok += 1
            if len(res.red) == before:
                n_clean += 1
    if not tabs:
        return
    res.notes.append("九维：「活体件＋判据三合一」齐 %d 维，其中**完全无红** %d 维" % (n_ok, n_clean))


CRITERIA = [
    ("①", "打回必有处置表", c1),
    ("②", "分流必须写理由", c2),
    ("③", "回执行环不得改规格", c3),
    ("④", "回意图环必须更新追溯矩阵", c4),
    ("⑤", "L4 必须递增版本并追加 CHANGELOG 条目", c5),
    ("⑥", "返工必有复跑读数", c6),
    ("⑦", "澄清不得留两版", c7),
    ("⑧", "九维都有活体", c8),
]


def run(root, quiet=False):
    res = []
    for cid, title, fn in CRITERIA:
        r = Res(cid, title)
        try:
            fn(root, r)
        except Exception as e:      # 判据自己崩了 ⇒ 红（不许静默当绿）
            r.red.append("[%s] 判据自身异常：%s: %s" % (cid, type(e).__name__, e))
        res.append(r)
    if not quiet:
        print("== check_loops（双环四种循环 L1–L4 ＋ 九维活体）==")
        print("   仓根：%s" % root)
        for r in res:
            print("   %s %-34s [%s]%s" % (r.cid, r.title, r.status,
                                          ("  " + "；".join(r.notes)) if r.notes else ""))
            if r.empty:
                print("        └ 空集：%s（判过了：这一条今天没有可判的条目——**不是没跑**）" % r.empty)
            for x in r.red:
                print("        [RED] %s" % x)
        n_ok = sum(1 for r in res if r.status == "OK")
        n_em = sum(1 for r in res if r.status == "EMPTY")
        n_bad = sum(1 for r in res if r.status == "RED")
        n_red = sum(len(r.red) for r in res)
        print("   —— 判据 8 条：绿 %d／空集 %d／红 %d 条判据（红点 %d 处）——"
              % (n_ok, n_em, n_bad, n_red))
        print("   STATUS=%s" % ("FAIL" if n_bad else "PASS"))
    return (1 if any(r.red for r in res) else 0), res


# ── 自证：正控全绿 ＋ 每条各一个反例 ────────────────────────────────────
def _w(root, rel, body):
    p = os.path.join(root, *rel.split("/"))
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)


DIM_FIX = [("一 理念", "ninedim/01-意图环/01-策划/策划-项目宪法.md"),
           ("二 框架", "ninedim/01-意图环/03-设计/设计-架构说明.md"),
           ("三 原子化", "ninedim/01-意图环/03-设计/设计-模块清单.md"),
           ("四 结构", "ninedim/01-意图环/03-设计/设计-落位契约.md"),
           ("五 流程", "ninedim/01-意图环/05-计划/计划-测试与用例.md"),
           ("六 规格", "ninedim/01-意图环/04-规格/demo.spec.md"),
           ("七 评审", "ninedim/02-枢纽A-前置闸/评审-前置-DEMO-001-v0.1.md"),
           ("八 团队", "ninedim/03-执行环/04-团队分工/分工-demo.md"),
           ("九 文档", "CHANGELOG.md")]


def base_fixture(root):
    """一个"八条判据全绿"的沙盒。"""
    # 判据脚本（每条 dim 一个，锚各自不同）
    for i in range(1, 10):
        _w(root, "scripts/verify/dim_%d.py" % i, "# 锚%d\n" % i)
    chk = "#!/usr/bin/env bash\n"
    for i in range(1, 10):
        chk += "python3 scripts/verify/dim_%d.py\n" % i
    _w(root, "check.sh", chk)
    # 九维活体台账
    rows = ["| 维 | 活体件 | 标准点名件 | 判据脚本 | 锚 | 现取 |", "|---|---|---|---|---|---|"]
    for i, (dim, carrier) in enumerate(DIM_FIX, 1):
        _w(root, carrier, "# %s\n正文\n" % dim)
        rows.append("| %s | %s | — | scripts/verify/dim_%d.py | 锚%d | 沙盒 |" % (dim, carrier, i, i))
    _w(root, "ninedim/records/台账-九维活体-2026-01-01.md",
       "# 九维活体（沙盒）\n\n条目计数：9\n\n" + "\n".join(rows) + "\n")
    # L1 返工（0 条）
    _w(root, "ninedim/records/台账-返工-L1-2026-01-01.md",
       "# L1 返工（沙盒）\n\n条目计数：0\n\n"
       "| # | 红在哪 | 改了什么 | 复跑命令 | 退出码 |\n|---|---|---|---|---|\n"
       "| — | 沙盒里没有返工（0 条） | — | — | — |\n")
    # L2 澄清（0 条）
    _w(root, "ninedim/records/台账-澄清-L2-2026-01-01.md",
       "# L2 澄清（沙盒）\n\n条目计数：0\n\n"
       "| # | 问题 | 结论 | 规格/设计就地更新处 |\n|---|---|---|---|\n"
       "| — | 沙盒里没有澄清（0 条） | — | — |\n")
    # L3 处置（0 条；带分流判断栏）
    _w(root, "ninedim/records/台账-处置-L3-2026-01-01.md",
       "# L3 处置（沙盒）\n\n条目计数：0\n\n"
       "| # | 发现 | 依据 | 分流判断 | 责任人 | 复验结论 | 规格基线 | 追溯矩阵指纹 |\n"
       "|---|---|---|---|---|---|---|---|\n"
       "| — | 沙盒里没有 L3 分流（0 条） | — | — | — | — | — | — |\n")
    # 规格 + RTM（指纹的标的物）
    _w(root, "ninedim/01-意图环/04-规格/demo.spec.md", "## Requirements\n### Requirement: x\n")
    _w(root, "ninedim/01-意图环/02-需求/WC-RTM-001.csv", "req,mod,test\nR-1,M01,t1\n")
    # L4：一个归档 + 版本台账 + CHANGELOG 点名
    arch = "2026-01-01-demo-change"
    _w(root, "ninedim/06-变更/archive/%s/review.md" % arch,
       "# review\n\n| 项 | 内容 |\n|---|---|\n| 变更号 | WC-FC-2026-001 |\n| 批准人 | Demo |\n| 结论 | 批准 |\n")
    _w(root, "ninedim/records/台账-L4-归档与版本-2026-01-01.md",
       "# L4 归档与版本（沙盒）\n\n条目计数：1\n\n"
       "| 归档目录 | 变更号 | 版本 | 版本依据 | CHANGELOG 条目 |\n|---|---|---|---|---|\n"
       "| %s | WC-FC-2026-001 | v1.0 | 沙盒 | 有 |\n" % arch)
    _w(root, "CHANGELOG.md", "# 变更记录\n\n## v1.0 · %s\n" % arch)
    # 枢纽B 一件已签通过（① 的扫描面）
    _w(root, "ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R4-001-v0.1.md",
       "# 后置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
       "| 主持人 | Demo | ☑ 通过 | Demo | 2026-01-01 |\n")


def _cp(src, dst):
    shutil.copytree(src, dst)


def selftest():
    cases = []

    def add(name, mut, want_rc, want_msgs):
        cases.append((name, mut, want_rc, want_msgs))

    add("正控：八条判据全绿", None, 0, [])
    add("反例①：判「退回」而无处置表", lambda d: _w(
        d, "ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R4-001-v0.1.md",
        "# 后置评审\n\n| 角色 | 姓名 | 结论 | 签字 | 日期 |\n|---|---|---|---|---|\n"
        "| 主持人 | Demo | ☑ 退回 | Demo | 2026-01-01 |\n"), 1, ["[①]", "退回"])
    add("反例②：分流只写「重做」、理由空", lambda d: _w(
        d, "ninedim/records/台账-处置-L3-2026-01-01.md",
        "# L3\n\n条目计数：1\n\n"
        "| # | 发现 | 依据 | 分流判断 | 责任人 | 复验结论 | 规格基线 | 追溯矩阵指纹 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | 图少一条边 | 图与实现不符 | 重做 | A | — | — | — |\n"), 1, ["[②]", "既不是回执行环"])
    add("反例②b：分流方向写了、理由（依据）空", lambda d: _w(
        d, "ninedim/records/台账-处置-L3-2026-01-01.md",
        "# L3\n\n条目计数：1\n\n"
        "| # | 发现 | 依据 | 分流判断 | 责任人 | 复验结论 | 规格基线 | 追溯矩阵指纹 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | 图少一条边 | — | 回执行环 | A | — | — | — |\n"), 1, ["[②]", "分流理由"])
    add("反例③：回执行环却改了规格", lambda d: _w(
        d, "ninedim/records/台账-处置-L3-2026-01-01.md",
        "# L3\n\n条目计数：1\n\n"
        "| # | 发现 | 依据 | 分流判断 | 责任人 | 复验结论 | 规格基线 | 追溯矩阵指纹 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | 实现与承诺不符 | 实现错 | 回执行环 | A | 复跑绿 | sha256:deadbeef | — |\n"), 1, ["[③]"])
    add("反例④：回意图环未更新矩阵", lambda d: _w(
        d, "ninedim/records/台账-处置-L3-2026-01-01.md",
        "# L3\n\n条目计数：1\n\n"
        "| # | 发现 | 依据 | 分流判断 | 责任人 | 复验结论 | 规格基线 | 追溯矩阵指纹 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | 承诺写错 | 承诺错 | 回意图环 | A | 已改规格 | — | sha256:deadbeef |\n"), 1, ["[④]"])
    add("反例⑤a：版本同号（未递增）", lambda d: _two_arch(d, "v1.0", True), 1, ["[⑤]", "版本没递增"])
    add("反例⑤b：版本递增但 CHANGELOG 无条目", lambda d: _two_arch(d, "v1.1", False), 1, ["[⑤]", "零命中"])
    add("反例⑥a：返工无复跑命令", lambda d: _w(
        d, "ninedim/records/台账-返工-L1-2026-01-01.md",
        "# L1\n\n条目计数：1\n\n"
        "| # | 红在哪 | 改了什么 | 复跑命令 | 退出码 |\n|---|---|---|---|---|\n"
        "| 1 | 单测红 | 改了一行 | — | 0 |\n"), 1, ["[⑥]", "复跑命令"])
    add("反例⑥b：返工有命令但退出码为空", lambda d: _w(
        d, "ninedim/records/台账-返工-L1-2026-01-01.md",
        "# L1\n\n条目计数：1\n\n"
        "| # | 红在哪 | 改了什么 | 复跑命令 | 退出码 |\n|---|---|---|---|---|\n"
        "| 1 | 单测红 | 改了一行 | cargo test --locked | — |\n"), 1, ["[⑥]", "退出码"])
    add("反例⑦：出现 `*-旧` 副本", lambda d: _w(
        d, "ninedim/01-意图环/04-规格/demo-旧.spec.md", "## Requirements\n"), 1, ["[⑦]"])
    add("反例⑧a：某维载体是空夹（空集）", lambda d: _empty_dir(
        d, "ninedim/01-意图环/05-计划"), 1, ["[⑧]", "空集"])
    add("反例⑧b：某维判据脚本不在盘上", lambda d: _w(
        d, "ninedim/records/台账-九维活体-2026-01-01.md",
        read(os.path.join(d, "ninedim/records/台账-九维活体-2026-01-01.md"))
        .replace("| 四 结构 | ninedim/01-意图环/03-设计/设计-落位契约.md | — | scripts/verify/dim_4.py |",
                 "| 四 结构 | ninedim/01-意图环/03-设计/设计-落位契约.md | — | scripts/verify/check_structure.py |")),
        1, ["[⑧]", "判据脚本不在"])
    add("反例⑧d：某维有载体但一件判据都没声明", lambda d: _w(
        d, "ninedim/records/台账-九维活体-2026-01-01.md",
        read(os.path.join(d, "ninedim/records/台账-九维活体-2026-01-01.md"))
        .replace("| 四 结构 | ninedim/01-意图环/03-设计/设计-落位契约.md | — | scripts/verify/dim_4.py | 锚4 | 沙盒 |",
                 "| 四 结构 | ninedim/01-意图环/03-设计/设计-落位契约.md | — | — | — | 无判据 |")),
        1, ["[⑧]", "没有一条判据指着它"])
    add("反例⑧c：标准点名的活体件不在", lambda d: _w(
        d, "ninedim/records/台账-九维活体-2026-01-01.md",
        read(os.path.join(d, "ninedim/records/台账-九维活体-2026-01-01.md"))
        .replace("| 二 框架 | ninedim/01-意图环/03-设计/设计-架构说明.md | — |",
                 "| 二 框架 | ninedim/01-意图环/03-设计/设计-架构说明.md | "
                 "ninedim/01-意图环/03-设计/设计-接口契约.md |")),
        1, ["[⑧]", "标准点名的活体件"])
    add("反例：台账不在（判不了）", lambda d: os.remove(
        os.path.join(d, "ninedim/records/台账-返工-L1-2026-01-01.md")), 1, ["台账不在"])
    add("反例：台账自欺（计数≠表体）", lambda d: _w(
        d, "ninedim/records/台账-返工-L1-2026-01-01.md",
        "# L1\n\n条目计数：1\n\n"
        "| # | 红在哪 | 改了什么 | 复跑命令 | 退出码 |\n|---|---|---|---|---|\n"
        "| — | 其实一条都没有 | — | — | — |\n"), 1, ["自欺"])
    add("反例：CHANGELOG 不在", lambda d: os.remove(os.path.join(d, "CHANGELOG.md")), 1, ["[⑤]"])

    ok = 0
    with tempfile.TemporaryDirectory(prefix="loops-base-") as base:
        base_fixture(base)
        rc0, res0 = run(base, quiet=True)
        print("== check_loops --self-test（正控 ＋ 每条判据各一个反例）==")
        print("   [%s] %-30s rc=%d（期望 0）红点 %d"
              % ("OK " if rc0 == 0 else "★错", "正控：八条判据全绿", rc0,
                 sum(len(r.red) for r in res0)))
        if rc0 != 0:
            for r in res0:
                for x in r.red:
                    print("        [正控不该有的红] %s" % x)
        ok += 1 if rc0 == 0 else 0
        for name, mut, want, msgs in cases[1:]:
            with tempfile.TemporaryDirectory(prefix="loops-case-") as d:
                root = os.path.join(d, "repo")
                _cp(base, root)
                mut(root)
                rc, res = run(root, quiet=True)
                blob = "\n".join("\n".join(r.red) for r in res)
                miss = [m for m in msgs if m not in blob]
                good = (rc == want) and not miss
                if good:
                    ok += 1
                print("   [%s] %-30s rc=%d（期望 %d）%s"
                      % ("OK " if good else "★错", name, rc, want,
                         "" if good else "  缺：%s" % "，".join(miss)))
        print("   自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def _two_arch(d, ver2, cl_hit):
    """反例⑤：再加一个归档（版本 ver2）；`cl_hit=False` ⇒ CHANGELOG 不点名它。"""
    arch2 = "2026-02-02-demo-change-2"
    _w(d, "ninedim/06-变更/archive/%s/review.md" % arch2,
       "# review\n\n| 项 | 内容 |\n|---|---|\n| 批准人 | Demo |\n| 结论 | 批准 |\n")
    _w(d, "ninedim/records/台账-L4-归档与版本-2026-01-01.md",
       "# L4\n\n条目计数：2\n\n"
       "| 归档目录 | 变更号 | 版本 | 版本依据 | CHANGELOG 条目 |\n|---|---|---|---|---|\n"
       "| 2026-01-01-demo-change | WC-FC-2026-001 | v1.0 | 沙盒 | 有 |\n"
       "| %s | WC-FC-2026-002 | %s | 沙盒 | 有 |\n" % (arch2, ver2))
    cl = "# 变更记录\n\n## v1.0 · 2026-01-01-demo-change\n"
    if cl_hit:
        cl += "\n## %s · 2026-02-02\n" % arch2
    _w(d, "CHANGELOG.md", cl)


def _empty_dir(d, rel):
    p = os.path.join(d, *rel.split("/"))
    if os.path.isdir(p):
        for dp, _dn, fn in os.walk(p):
            for f in fn:
                os.remove(os.path.join(dp, f))
    _w(d, rel + "/_索引.md", "| 件 | 是什么 |\n|---|---|\n| — | 空（待填） |\n")


def find_root():
    if _ROOT_INJECTED is not None:
        return _ROOT_INJECTED
    return None


def main():
    ap = argparse.ArgumentParser(description="NineDim 判据：双环四种循环 ＋ 九维活体")
    ap.add_argument("--root", default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return selftest()
    root = find_root() or a.root or _ROOT_DEFAULT
    if not os.path.isdir(root):
        print("   ★ 仓根不在：%s（读不到＝判不了，rc=2）" % root)
        return 2
    rc, res = run(root, quiet=a.json)
    if a.json:
        print(json.dumps({"root": root, "rc": rc,
                          "criteria": [{"id": r.cid, "title": r.title, "status": r.status,
                                        "empty": r.empty, "red": r.red, "notes": r.notes}
                                       for r in res]}, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    sys.exit(main())
