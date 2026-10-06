# -*- coding: utf-8 -*-
"""从 openspec/generated/specmap.json 生成 openspec/generated/BRIDGE.md —— 编号桥映射表（判据④ 的受检对象）。

判据④（spec_bridge.py）：openspec/generated/BRIDGE.md 必须覆盖规格树下**每一条** Requirement——
有号的挂号，取不到号的显式标「无号」。**未手抄**：数据源是 build_specmap.py 抽出的同一份。
"""
import json, io
from collections import defaultdict
from pathlib import Path

# ⚠ 输入/输出一律**按本脚本位置推导**（仓内受控）；**不读仓外那份**
#   `D:\Code\_specmap\openspec/generated/specmap.json`——两份会分叉（2026-09-27 已明确：**仓内这份为准**）。
SRC = str(Path(__file__).resolve().parent.parent / "generated/specmap.json")
OUT = str(Path(__file__).resolve().parent.parent / "generated/BRIDGE.md")
d = json.load(io.open(SRC, encoding="utf-8"))
srs = {s["id"]: s for s in d["srs"]}
flag = {"green": "已实现", "half": "部分", "red": "未实现"}

rows = []

# ── 标题**一律现取规格树**（2026-09-27 修）────────────────────────────────
# 为什么：此前标题取自 `openspec/generated/specmap.json` 的快照，而它的抽取器 `build_specmap.py` **在仓外、且不在版本控制里**
# ⇒ **改规格里的标题，BRIDGE 却还是旧标题**（实测：判据④ 报「闸读得到风险等级…不在编号桥映射表里」，
#   而 `openspec/generated/specmap.json` 里仍留着旧标题——**只重跑生成器修不好它**）。
# 规矩：**标题的权威是规格树**（`openspec/specs/<能力>/spec.md` 的 `### Requirement:`）；
#       `openspec/generated/specmap.json` 只负责"**哪个号**"的映射，不再负责"**标题怎么写**"。
# 对不齐时（数量不符）**退回快照并打印告警**——宁可吵，也不静默用错标题。
def _spec_titles(repo, cap):
    p = Path(repo) / "openspec" / "specs" / cap / "spec.md"
    if not p.is_file():
        return []
    return [ln[len("### Requirement:"):].strip()
            for ln in p.read_text(encoding="utf-8", errors="replace").split("\n")
            if ln.startswith("### Requirement:")]


_REPO = Path(__file__).resolve().parent.parent.parent
_MISMATCH = []
for c in d["caps"]:
    _live = _spec_titles(_REPO, c["cap"])
    if len(_live) != len(c["reqs"]):
        _MISMATCH.append("%s：规格树 %d 条 vs 快照 %d 条" % (c["cap"], len(_live), len(c["reqs"])))
        _live = [r["title"] for r in c["reqs"]]          # 退回快照
    for _i, r in enumerate(c["reqs"]):
        rows.append((c["cap"], _live[_i], d["req_map"].get(r["title"], [])))

if _MISMATCH:
    print("⚠ 标题数与快照不符（已退回快照标题，请核）：" + "；".join(_MISMATCH))

claim = defaultdict(list)
for cap, req, ids in rows:
    for i in ids:
        claim[i].append(req)
unmapped = [(cap, req) for cap, req, ids in rows if not ids]
collide = {k: v for k, v in claim.items() if len(v) > 1}
srs_no_req = [s for s in d["srs"] if s["id"] not in claim]

GOV = ["默认走融合档", "一个 change 的产物链完整，归档硬前置",
       "证据行必须指向真实存在的测试或脚本", "新增需求必须带流程侧号",
       "能力覆盖完整，未实现的在册不停工"]

L = []
L.append("# 编号桥映射表（BRIDGE）")
L.append("")
L.append("> **本件是规格层的受控件**，位置固定在 `openspec/generated/BRIDGE.md`——守卫 `world-core/tools/spec_bridge.py`")
L.append("> 的**判据④** 读它：**规格树下每一条 Requirement，都必须在本表里在册**（有号，或显式标「无号」）。")
L.append("> 没有本表、或本表漏掉任何一条，守卫**非零退出**。")
L.append("")
L.append("> **为什么需要它**：融合档原写法要求「每条 Requirement 的标题必须以 REQ 号开头」。真挂一遍后发现")
L.append("> 两边是**两种切法**：一条承诺可能对上多条需求、多条承诺也可能抢同一个号（**撞号 %d 处**）。" % len(collide))
L.append("> 标题只能带一个号 ⇒ 硬塞会造出**重号** ⇒ 破坏「编号是主键」本身。故桥改落本表：")
L.append("> **内容不复制，靠编号对齐；一条对多条在这里表达得出来。**")
L.append("")
L.append("---")
L.append("")
L.append("## 一、规格承诺 ↔ 流程侧需求号（%d 行）" % len(rows))
L.append("")
L.append("| # | 能力 | 承诺（Requirement 标题，逐字） | 流程侧需求号 | 那边状态 |")
L.append("|---|---|---|---|---|")
for i, (cap, req, ids) in enumerate(rows, 1):
    if ids:
        cell = "<br>".join("`%s` %s" % (x, srs[x]["title"] if x in srs else "?") for x in ids)
        st = "<br>".join(flag.get(srs[x]["status"], "?") if x in srs else "?" for x in ids)
    else:
        cell, st = "**无号**（见 §二）", "—"
    L.append("| %d | `%s` | %s | %s | %s |" % (i, cap, req, cell, st))
L.append("")
L.append("## 二、无号的承诺（%d 条，逐条在册；**不许自造号、不许拿相近号硬凑**）" % len(unmapped))
L.append("")
L.append("| # | 能力 | 承诺（逐字） | 处置 |")
L.append("|---|---|---|---|")
for i, (cap, req) in enumerate(unmapped, 1):
    L.append("| %d | `%s` | %s | 无号·待流程侧增补 |" % (i, cap, req))
L.append("")
L.append("## 三、规格层自身能力的承诺（`spec-governance`——**由 `fc-2026-001` 引入，归档时并入主规格**）")
L.append("")
L.append("> ⚠ **主规格里今天还没有这个能力**（`openspec list --specs` 为 **6** 条）：OpenSpec 的 delta 在 change **归档时**才并入主规格，而 `fc-2026-001` 尚未归档（等评审签字）。本节登记的是**该 change 的承诺**，不是「已并入的事实」。")
L.append("> ⚠ **不要**为了让本节看起来成立而手动把它塞进 `openspec/specs/`——那会让 `archive fc-2026-001` 报 `ADDED already exists` 而**永远归不了档**（`fc-2026-002` 今天正是这个病，守卫判据⑩ 抓的 10 处就是它）。")
L.append("> 而流程侧今天没有对应需求 ⇒ **逐条登记为「无号·待流程侧增补」**（这是新规矩的第一次适用）。")
L.append("")
L.append("| # | 承诺（逐字，`specs/spec-governance/spec.md` 的 Requirement 标题） | 号 |")
L.append("|---|---|---|")
# 标题**现取 delta**（2026-09-27 修）：写死的 GOV 会与 delta 脱节——与"标题现取规格树"同一条规矩。
_gov_delta = _REPO / "openspec/changes/fc-2026-001-openspec-into-cm/specs/spec-governance/spec.md"
if _gov_delta.is_file():
    GOV = [ln[len("### Requirement:"):].strip()
           for ln in _gov_delta.read_text(encoding="utf-8", errors="replace").split("\n")
           if ln.startswith("### Requirement:")]
# 前缀**按需加**：源标题（delta 的 `### Requirement:`）本身可能已经带这个标记
# —— 硬前置过一次，实测 §三 五行全成「〔无号·待流程侧增补〕〔无号·待流程侧增补〕…」。
# 规矩：**标记只此一处、且由生成器去重**；源标题改回不带标记时也照旧成立。
for i, t in enumerate(GOV, 1):
    _pfx = "" if t.startswith("〔无号·待流程侧增补〕") else "〔无号·待流程侧增补〕"
    L.append("| %d | %s%s | 无号（待流程侧增补） |" % (i, _pfx, t))
L.append("")
# ── 在办 change 引入的能力承诺（**主规格树里还没有这个能力**）──────────────
# 为什么要有这一节：判据④ 只扫主规格树（`openspec/specs/**/spec.md`），
#   而 OpenSpec 的规矩是 delta 在 change **归档时**才并入主规格 ⇒ 新能力在归档前
#   **不在判据④ 的扫描面里**，等于它在编号桥里没有在册面。
#   openspec/generated/BRIDGE.md 是**生成物**（判据⑪ 逐字节核）⇒ 这个在册面必须由生成器**现取**，不许手编。
_pending = []
_changes_dir = _REPO / "openspec" / "changes"
if _changes_dir.is_dir():
    for _cd in sorted(_changes_dir.iterdir()):
        if not _cd.is_dir() or _cd.name == "archive":
            continue
        _sd = _cd / "specs"
        if not _sd.is_dir():
            continue
        for _capd in sorted(_sd.iterdir()):
            _sp = _capd / "spec.md"
            if not _sp.is_file():
                continue
            _cap = _capd.name
            if _cap == "spec-governance":            # 它有专属 §三，不在此重复
                continue
            if (_REPO / "openspec" / "specs" / _cap / "spec.md").is_file():
                continue                             # 已并入主规格 ⇒ 归 §一／§二
            for _ln in _sp.read_text(encoding="utf-8", errors="replace").split("\n"):
                if _ln.startswith("### Requirement:"):
                    _pending.append((_cd.name, _cap, _ln[len("### Requirement:"):].strip()))
if _pending:
    L.append("## 三之二、在办 change 引入的能力承诺（**主规格树里还没有这个能力**，归档时并入主规格）")
    L.append("")
    L.append("> ⚠ **本节登记的是「该 change 的承诺」，不是「已并入的事实」**——"
             "OpenSpec 的 delta 在 change **归档时**才并入主规格。")
    L.append("> ⚠ **不要**为了让本节看起来成立而手动把能力塞进 `openspec/specs/`——"
             "那会让 `archive` 报 `ADDED already exists` 而**永远归不了档**。")
    L.append("> 流程侧今天没有对应需求 ⇒ **逐条登记为「无号·待流程侧增补」**"
             "（**不许自造号、不许拿相近号硬凑**）。")
    L.append("")
    L.append("| # | 由哪个 change 引入 | 能力 | 承诺（逐字，Requirement 标题） | 号 |")
    L.append("|---|---|---|---|---|")
    for _i, (_ch, _cap, _t) in enumerate(_pending, 1):
        L.append("| %d | `%s` | `%s` | %s | 无号（待流程侧增补） |" % (_i, _ch, _cap, _t))
    L.append("")
L.append("## 四、没有任何承诺认领的需求（%d 条 → 覆盖缺口）" % len(srs_no_req))
L.append("")
L.append("> 这些是**流程侧登记在册、而规格树里没有落点**的需求。它们由覆盖 change（`openspec/changes/cover-*`）承担；")
L.append("> 守卫**判据⑤** 要求那个 change **未归档且 tasks 仍有未勾项**（＝未实现的东西在册、可见、不装成已成立）。")
L.append("")
L.append("| 需求 | 标题 | 状态 |")
L.append("|---|---|---|")
for s in srs_no_req:
    L.append("| `%s` | %s | %s |" % (s["id"], s["title"], flag.get(s["status"], s["status"])))
L.append("")
L.append("## 五、撞号清单（说明为什么号不能写进标题）")
L.append("")
L.append("| 需求号 | 被这些承诺同时认领 |")
L.append("|---|---|")
for k in sorted(collide):
    L.append("| `%s` | %s |" % (k, "<br>".join(collide[k])))
L.append("")
# ── 规格树下、specmap 里没有的 Requirement（合并进来的新增条）──
import re as _re
from pathlib import Path as _P
_known = set()
for c in d["caps"]:
    for r in c["reqs"]:
        _known.add(r["title"])
_extra = []
_repo = _P(OUT).parents[1]
for _sp in sorted((_repo / "openspec" / "specs").rglob("spec.md")):
    for _ln in _sp.read_text(encoding="utf-8").split("\n"):
        if _ln.startswith("### Requirement:"):
            _t = _ln[len("### Requirement:"):].strip()
            if _t not in _known and _t not in GOV:
                _extra.append((_sp.parent.name, _t))
if _extra:
    L.append("## 六、规格树下、编号桥来源表里没有的 Requirement（**合并进来的新增条，逐条在册**）")
    L.append("")
    L.append("| # | 能力 | Requirement（逐字） |")
    L.append("|---|---|---|")
    for _i, (_cap, _t) in enumerate(_extra, 1):
        L.append("| %d | `%s` | %s |" % (_i, _cap, _t))
    L.append("")
else:
    # ⚠ **空节也要留号**：本节一旦缺号，后面的「数值权威表」就会从 §七 变成 §六，
    #   而四处引用写的是「`openspec/generated/BRIDGE.md` §六 数值权威表」⇒ 节号一跳，那些引用就全指错。
    #   （2026-09-27 实测：合并进来的 10 条已并入 §一／§二，本节变空、§六 整个消失，
    #     评审席据此报「四处引的 §六 不存在」。）⇒ 永远输出本节，空的就写「本期无」。
    L.append("## 六、规格树下、编号桥来源表里没有的 Requirement（**合并进来的新增条，逐条在册**）")
    L.append("")
    L.append("**本期无**：规格树下的每条 Requirement 都已在 §一／§二／§三 在册（编号桥来源表已覆盖全树）。")
    L.append("")
    L.append("> **本节为什么保留空号**：它一旦消失，下一节「数值权威表」的号就会从 §七 变成 §六，"
             "而别处多处引用写的是「§六 数值权威表」——**节号一跳，引用全指错**。")
    L.append("")
# ── 数值权威表：**全部现算**，不许写死（写死过一次，建表那次提交上就错了两个数）
import re as _re2
from pathlib import Path as _P2
def _cnt(path, pat):
    try:
        return len(_re2.findall(pat, _P2(path).read_text(encoding="utf-8", errors="replace")))
    except Exception:
        return -1
def _nfiles(d, exts):
    try:
        return sum(1 for p in _P2(d).rglob("*") if p.is_file() and p.suffix.lower() in exts)
    except Exception:
        return -1
_srs = _repo / "world-core/docs/S1-需求/WC-SRS-001-v0.1.md"
_rtm = _repo / "world-core/docs/S1-需求/WC-RTM-001.csv"
_docs = _repo / "world-core/docs"
_n_srs = _cnt(_srs, r"REQ-[FN]-\d{3}")
_uniq_srs = len(set(_re2.findall(r"REQ-[FN]-\d{3}", _srs.read_text(encoding="utf-8", errors="replace")))) if _srs.is_file() else -1
_n_rtm = _cnt(_rtm, r"REQ-[FN]-\d{3}")
_n_docs = _nfiles(_docs, {".md", ".csv"})
_n_openspec = 0
if _docs.is_dir():
    for _p in _docs.rglob("*"):
        if _p.is_file() and _p.suffix.lower() in (".md", ".csv"):
            if "openspec" in _p.read_text(encoding="utf-8", errors="replace").lower():
                _n_openspec += 1
_audit = _repo / "openspec/changes/fc-2026-001-openspec-into-cm/audit.md"
_n_findings = _cnt(_audit, r"(?m)^\|\s*\*\*[A-Z]\d+\*\*\s*\|") or _cnt(_audit, r"【严重】|【重要】|【一般】|【提示】")

L.append("## 七、数值权威表（**全部现算，不写死**——每个数带复算命令）")
L.append("")
L.append("> 用途：H-06「每个事实只有一个权威载体，其它文档只引用不复述数值」。")
L.append("> **本表由 `gen_bridge_md.py` 在生成时现算**：写完那次提交上就错过两个数（`133` 实测 56、`0 命中` 实测 1），")
L.append("> 根因是**把数写死了**。⇒ 现在表里的值一律来自当场复算；引用本表即引用复算结果。")
L.append("")
L.append("| # | 事实 | 权威值（现算） | 复算命令 |")
L.append("|---|---|---|---|")
L.append("| 1 | `WC-SRS-001-v0.1.md` 里 `REQ-[FN]-NNN` 的出现次数 | **%d** | `[regex]::Matches((Get-Content -Raw <file>),'REQ-[FN]-\\d{3}').Count` |" % _n_srs)
L.append("| 2 | 同上，**唯一**需求号个数 | **%d** | 同上去重 |" % _uniq_srs)
L.append("| 3 | `WC-RTM-001.csv` 里同模式出现次数 | **%d** | 同上换文件 |" % _n_rtm)
L.append("| 4 | `world-core/docs/` 下 `.md`＋`.csv` 文件数 | **%d** | `Get-ChildItem -Recurse -File world-core/docs` 按扩展名过滤 |" % _n_docs)
L.append("| 5 | 上述文件里**含** `openspec`（不分大小写）的文件数 | **%d** | 逐文件 `read_text().lower()` 检索 |" % _n_openspec)
L.append("| 6 | 规格审计查出的差错条数（`audit.md`） | **%d** | 见 `fc-2026-001` 的 `audit.md` |" % _n_findings)
L.append("| 7 | 规格树下的 Requirement 条数 | **%d** | 逐文件计 `^### Requirement` |" % sum(1 for _sp in (_repo / "openspec" / "specs").rglob("spec.md") for _l in _sp.read_text(encoding="utf-8", errors="replace").split(chr(10)) if _l.startswith("### Requirement:")))
L.append("| 8 | 撞号数／无号数／无人认领需求数 | **%d ／ %d ／ %d** | 见本表 §一／§二／§四 |" % (len(collide), len(unmapped), len(srs_no_req)))
L.append("")
L.append("**已作废的旧值（不得再用）**：`378`、`68`（两个都不可复现）。")
L.append("")
L.append("## 八、维护（谁更新、什么时候）")
L.append("")
L.append("1. **新增 / 改名 / 删除规格里的 Requirement 时，同一次改动里更新本表**（否则判据④ 变红）。")
L.append("2. 取到流程侧号时，把 §二 / §三 的「无号」改成号，并在 §一 补行。")
L.append("3. 本表的**唯一性**：`openspec/generated/BRIDGE.md` 一处；change 内的 `mapping.md` 是它的**历史快照**，随该 change 归档，不再是活件。")
L.append("")

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("written:", OUT)
print("rows=%d unmapped=%d gov=%d srs_no_req=%d collide=%d" % (len(rows), len(unmapped), len(GOV), len(srs_no_req), len(collide)))
