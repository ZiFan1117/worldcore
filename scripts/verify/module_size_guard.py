#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""module_size_guard.py —— 「**模块化**」的尺寸判据：**六七百行的件，谁看得懂**。

为什么有这一件（作者口径，逐字）
--------------------------------
作者 2026-10-07：「**六七百行谁看得懂；应该是几十行**」。
⇒ 「一个原子一个夹」（`WC-ATOM-001` §二 A-2）只保证了**原子性**，**不保证模块化**：
现取真仓里既有 **2312 行**的 `src/main.rs`、**2538 行**的集成测试，也有
**「整夹只有一件、而那一件 2215 行」**（`src/ontology_definition/`）这种形状——
后者正是「**只原子化、没模块化**」：夹是对的，模块化没做。
⇒ 本判据把这个差做成**会红**的东西。**四面，各自可判真假。**

四面（每条都有反例；`--self-test` 先证明它真会红且**指名到件**）
----------------------------------------------------------------
* **面① 代码**：`src/**/*.rs` 与 `scripts/test/**/*.rs` 超硬顶 ⇒ 红。
* **面② 文档**：`ninedim/**/*.md` 的**正文件**超硬顶 ⇒ 红（排除面见下）。
* **面③ 结构**：**「一个夹里只有 1 件、而这一件超【目标】」** ⇒ **另报并判红**。
  为什么单列（**这就是本判据的存在理由**）：面① 只问「这一件多不多」，面③ 问
  「**这个夹有没有被真的拆开**」。两者不是一件事——
  一夹 10 件、每件 100 行 ⇒ ①绿 ③不报；一夹 1 件、200 行 ⇒ **①绿（未超硬顶）而 ③红**。
  ★ 面③ **只对代码面（面①）判**：工程域 `ninedim/` 的命名规矩本来就是
  「第 3 层**只放件、不再建夹**」⇒ 那边「一夹一件」是**规定动作**，**不许**当成"没模块化"。
* **面④ 判据脚本**：`scripts/**/*.py` **与** `scripts/**/*.sh` 超硬顶 ⇒ 红。
  **为什么判据也要量**（作者裁 2026-10-08）：**判据也是代码**——
  现取 `scripts/verify/module_graph.py` **2484 行**，与 `src/` 的巨件**同病**；
  只量产品、放过门禁自己，等于给自己开口子。**本件自己也在这一面里**（现取 570 行 ⇒ 红），
  如实报、**不豁免**。
  ★ `.sh` 并入面④的现取基线（作者裁 2026-10-08，**只作说明、不作判据**）：
  `scripts/**/*.sh` **9 件、>250 行 5 件**，最大 **908** `scripts/test/s1_sys_probe2.sh`
  （次 576 `s1_sys_probe.sh`／392 `system_acceptance.sh`／321 `release/install.sh`／282 `carrier_acceptance.sh`）。
  ★ 与面① **分开报数**（两批整改节奏不同），但阈值与三档判定**同一把尺子**。

阈值表（**唯一权威载体**；依据＝上面那段作者口径，逐字）
-------------------------------------------------------
* **目标 150 行**：「几十行」的上沿——留得下文件头注释、判据表与 `use`／`import` 块；
* **硬顶 250 行**：**超过它即红**。
* 为什么两档：150 是**整改目标**（黄／WARN，该拆），250 是**红线**（红／FAIL，必须拆）。
* `--max N` 覆盖**硬顶**（并把目标夹到 `min(目标, N)`，保证 目标 ≤ 硬顶 不矛盾）。

面② 的**排除面**（作者裁 2026-10-08；一处写死，依据逐条在常量处）
------------------------------------------------------------------
记录件／过程件／未批候选**天然长**，且它们的"长度"不是模块化问题 ⇒ 不量：
`DOC_EXCLUDE_PARTS`（**仅限 `ninedim/` 顶层的环夹名**）＋ `DOC_EXCLUDE_PREFIXES`（件名前缀）
＋ 单列的合订本豁免。**其余正文件（规格／设计／需求／计划／测试／验收／澄清等）照判。**

口径（可复核）
--------------
* **行数** ＝ `read_text().splitlines()` 的长度（**物理行**；末尾换行不额外算一行）。
* 排除：`.git`／`.refs`／`target`／`node_modules`／`__pycache__`（料夹与构建产物**不是本仓的件**）。
* **空集不许判绿**：面① 一份 `.rs` 都扫不到 ⇒ **rc=2**（本仓纪律；`spec_shape.py:71-72` 同条）。
* ★★ **读数纪律（写死在此，比报任何单个数都有用）**：
  **只引同一次运行的成对读数；跨运行不可相减。**
  为什么（两席各踩过一次）：`impl-rust`／`spec-doc` 在**并行拆件**，同一命令几分钟内
  面① 的件数就能从 56 → 66 → 67、面② 从 165 → 185 → 85——**件数在涨而红在降**是"正在整改"的正常形态；
  拿"上一轮的红 71"减"这一轮的红 73"会得出**反的结论**（红变多不是因为拆坏了，是因为**面④ 新并入**
  了 23 件判据脚本）。⇒ 要比较，只能在**同一次运行**里取"对"（如"面① 红／面① 件数"），
  跨运行的比值与差值**一律不可算**。本句由 `--self-test` 钉住（删了它就红）。

用法
----
    python scripts/verify/module_size_guard.py                 # 判真仓（仓根按脚本位置上推三级）
    python scripts/verify/module_size_guard.py --max 200       # 临时收紧/放宽硬顶
    python scripts/verify/module_size_guard.py --repo <仓根>
    python scripts/verify/module_size_guard.py --self-test     # 正控 ＋ 逐条反例（反例必红且指名）

退出码
------
    0 = 全绿 ／ 1 = 有红（任一面超硬顶，或面③命中） ／ 2 = 用法错、仓根错、或**扫描面为空**
"""
import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# 非 UTF-8 控制台（Windows GBK/cp936）下中文与记号会让 print 抛 UnicodeEncodeError
# —— 那会变成「门禁自己崩了」的假失败。按本仓既有口径：**只重配 errors，不改 encoding**。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except Exception:
        pass


# ────────────────────────── 阈值表（唯一权威载体）──────────────────────────
# 依据＝作者 2026-10-07 逐字「**六七百行谁看得懂；应该是几十行**」（写在文件头上，不另立载体）。
# 四面共用同一把尺子（面③ 不查表：它的判红线＝面① 的**目标**）。
LIMITS = {
    "code": {"target": 150, "cap": 250},      # 面①：src/**/*.rs ＋ scripts/test/**/*.rs
    "doc": {"target": 150, "cap": 250},       # 面②：ninedim/**/*.md 的正文件
    "judge": {"target": 150, "cap": 250},     # 面④：scripts/**/*.py
}

# 面① 的取件口径：**夹 ＋ 后缀**（顺序＝报表面顺序）
CODE_SPECS = (("src", ".rs"), (os.path.join("scripts", "test"), ".rs"))
# 面④ 的取件口径：`scripts/**/*.py` ＋ `scripts/**/*.sh`（**判据也是代码**；作者裁 2026-10-08）。
# `.sh` 并入面④的现取基线（只作说明、不作判据）：9 件、>250 行 5 件、最大 908 行
# （`scripts/test/s1_sys_probe2.sh`；次 576／392／321／282）。
JUDGE_SPECS = (("scripts", ".py"), ("scripts", ".sh"))

# 全局排除（料夹与构建产物；与其余判据同一口径）
SKIP_DIRS = {".git", ".refs", "target", "node_modules", "__pycache__"}

# ── 面② 排除面（作者裁 2026-10-08，逐条依据）──
# ★ `DOC_EXCLUDE_PARTS` 是**路径段**排除，但**只限 `ninedim/` 顶层的环夹名**（作者裁 2026-10-08 收紧）：
#   判定时只看路径相对 `ninedim/` 的**第一段**（`ninedim/<环名>/…`）——
#   别处将来若出现同名夹（例：`ninedim/01-意图环/records/`），**不许**被这条排掉（由自证 `对照②i` 钉住）。
# ① `records`：生成物／台账／审计记录（`ninedim/records/**`）——**记录件**，天然长。
# ② `06-变更`：change 的过程件（`proposal/tasks/design/review` 与 delta）——**过程**，不是"现在是什么"。
# ③ `07-待审`：未批候选（`待审/<变更号>/<候选件>`）——**还没批的改法**，同过程件。
DOC_EXCLUDE_PARTS = ("records", "06-变更", "07-待审")
# ④ 按**件名前缀**排除的记录类（标准《工程域的结构与命名》§六 落位把它们放在阶段夹里，
#    但它们**仍是记录件**——"谁在哪天量到了什么"，不是"现在是什么"）：
#    `评审-`（评审记录）／`台账-`（缺陷与变更台账）／`证据-`（验证证据）／
#    `读数-`（现场读数）／`审计-`（审计发现件）／`复核-`（复核件）。
DOC_EXCLUDE_PREFIXES = ("评审-", "台账-", "证据-", "读数-", "审计-", "复核-")
# ⑤ **单列豁免**：上位标准《合订本》（`策划-理论书-*`）——它是**书**，长度由作者定，
#    与"本项目的件该多大"不是一回事（书在别的判据里另有豁免，如 `spec_bridge.py` 的 ⑧/⑯）。
DOC_EXCLUDE_THEORY_BOOK = "策划-理论书-"

# 面③ 只对代码面（面①）判（理由见文件头：工程域「一夹一件」是规定动作）
STRUCTURE_FACES = ("code",)

OK, WARN, FAIL = "OK", "WARN", "FAIL"

# 报表标题（数字与面号一一对应；面③ 由结构统计另出）
FACE_TITLES = {"code": "面① 代码", "doc": "面② 文档", "judge": "面④ 判据脚本"}
FACE_ORDER = ("code", "doc", "judge")


# ────────────────────────── 工具 ──────────────────────────
def find_repo(start):
    """从 start 往上找含 `src` 与 `scripts/verify` 的那一层（＝仓根）；找不到返回 None。"""
    p = Path(start).resolve()
    for cand in [p] + list(p.parents):
        if (cand / "src").is_dir() and (cand / "scripts" / "verify").is_dir():
            return cand
    return None


def rel(repo, p):
    try:
        return str(Path(p).resolve().relative_to(Path(repo).resolve())).replace("\\", "/")
    except Exception:
        return str(p)


def _specs_label(specs):
    """扫描面的展示口径（一律正斜杠；与报表里的路径同形）。"""
    return " ＋ ".join("`%s/**/*%s`" % (d.replace("\\", "/"), s) for d, s in specs)


def count_lines(p):
    """行数 ＝ 物理行数（`splitlines()` 的长度；末尾换行不算空行）。"""
    with io.open(p, "rb") as fh:
        return len(fh.read().decode("utf-8", "replace").splitlines())


def _walk(root, suffix):
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith(suffix):
                out.append(Path(dp) / f)
    return sorted(out)


def _files_by_specs(repo, specs):
    out = []
    for d, suf in specs:
        out += _walk(Path(repo) / d, suf)
    return sorted(out)


def code_files(repo):
    """面①：`CODE_SPECS` 里每个「夹 ＋ 后缀」的全部件（排序确定）。"""
    return _files_by_specs(repo, CODE_SPECS)


def judge_files(repo):
    """面④：`scripts/**/*.py` ＋ `scripts/**/*.sh`（**判据自己也在内**，不豁免）。"""
    return _files_by_specs(repo, JUDGE_SPECS)


def doc_excluded(name, top_part):
    """面② 的排除判定（**顶层环夹名** ∪ 件名前缀 ∪ 单列合订本）；命中返回**原因**，否则 None。

    ★ `top_part` 是路径相对 `ninedim/` 的**第一段**（`ninedim/<top_part>/…`）——
    路径段排除**只认这一层**：嵌套同名夹（`ninedim/01-意图环/records/`）**不**被排掉。
    """
    if top_part in DOC_EXCLUDE_PARTS:
        return "顶层环夹 `ninedim/%s/`（记录件／过程件／未批候选——天然长）" % top_part
    if name.startswith(DOC_EXCLUDE_THEORY_BOOK):
        return "单列豁免：上位标准《合订本》`%s*`（书，长度由作者定）" % DOC_EXCLUDE_THEORY_BOOK
    for pre in DOC_EXCLUDE_PREFIXES:
        if name.startswith(pre):
            return "件名前缀 `%s`（记录类：标准 §六 落位把它放在阶段夹里，但仍是记录件）" % pre
    return None


def doc_files(repo):
    """面②：`ninedim/**/*.md` 的**正文件**（排除面见 `DOC_EXCLUDE_*`；路径段只认顶层）。"""
    root = Path(repo) / "ninedim"
    out = []
    if not root.is_dir():
        return out
    for dp, dn, fn in os.walk(root):
        relparts = Path(dp).relative_to(root).parts
        top = relparts[0] if relparts else ""
        if top in DOC_EXCLUDE_PARTS:                     # ★ 只剪"顶层环夹"这一层
            dn[:] = []
            continue
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith(".md") and doc_excluded(f, top) is None:
                out.append(Path(dp) / f)
    return sorted(out)


# ────────────────────────── 判定 ──────────────────────────
def verdict_of(n, face, limits):
    """单件判定：**判红只卡硬顶**；目标与硬顶之间是 WARN（该拆，未必须拆）。"""
    if n > limits[face]["cap"]:
        return FAIL
    if n > limits[face]["target"]:
        return WARN
    return OK


def evaluate(repo, limits):
    """逐件取数：返回 [{face, dir, path, lines, verdict}]（各面内部按行数降序由调用方排）。"""
    rows = []
    for face, paths in (("code", code_files(repo)), ("doc", doc_files(repo)),
                        ("judge", judge_files(repo))):
        for p in paths:
            n = count_lines(p)
            r = rel(repo, p)
            rows.append({"face": face, "dir": os.path.dirname(r), "path": r, "lines": n,
                         "verdict": verdict_of(n, face, limits)})
    return rows


def structure_hits(rows, limits):
    """面③：**夹内只有 1 件、而这一件超【目标】** ⇒ 命中（**只对 `STRUCTURE_FACES`**）。

    返回 [(夹, 件, 行数)]，按行数降序。★ 条件是「超**目标**」而不是「超硬顶」：
    超硬顶的件面① 已经报了；面③ 要抓的是「**这个夹有没有被真的拆开**」这件独立的事——
    1 件 200 行的夹，面① 绿、面③ **必须红**，否则「只原子化没模块化」就没有判据盯着。
    """
    out = []
    for face in STRUCTURE_FACES:
        by_dir = defaultdict(list)
        for r in rows:
            if r["face"] == face:
                by_dir[r["dir"]].append(r)
        for d, items in sorted(by_dir.items()):
            if len(items) == 1 and items[0]["lines"] > limits[face]["target"]:
                out.append((d, items[0]["path"], items[0]["lines"]))
    out.sort(key=lambda x: -x[2])
    return out


# ────────────────────────── 跑一遍（打印）──────────────────────────
def run(repo, limits, out=None, show_all=True):
    """打印**逐件**「判定｜件｜行数｜目标｜硬顶」＋面③ ＋四面计数 ＋ `STATUS=`；返回 rc。"""
    out = out if out is not None else sys.stdout
    rows = evaluate(repo, limits)
    by_face = {f: [r for r in rows if r["face"] == f] for f in FACE_ORDER}
    code = by_face["code"]

    print("== module_size_guard —— 「模块化」尺寸判据 ==", file=out)
    print("   仓根：%s" % repo, file=out)
    print("   阈值：目标 %d 行／硬顶 %d 行（依据＝作者「六七百行谁看得懂；应该是几十行」）"
          % (limits["code"]["target"], limits["code"]["cap"]), file=out)
    print("   扫描面：面① 代码 %d 件（%s）｜面② 文档 %d 件（`ninedim/**/*.md` 的正文件；"
          "路径段只认 `ninedim/` 顶层环夹）｜面④ 判据脚本 %d 件（%s）"
          % (len(code), _specs_label(CODE_SPECS), len(by_face["doc"]),
             len(by_face["judge"]), _specs_label(JUDGE_SPECS)), file=out)
    # ★ 读数纪律（写进输出，不只写在注释里）：并行拆件期间件数在动，
    #   "上一轮的红"与"这一轮的红"**不可相减**——见文件头「读数纪律」那一段。
    print("   ★ 读数纪律：**只引同一次运行的成对读数；跨运行不可相减**"
          "（对数席正在并行拆件，件数在涨而红在降）", file=out)

    # ── 空集不许判绿（面① 代码）──
    if not code:
        print("", file=out)
        print("   * 面① 一份 `.rs` 都扫不到（`%s`）⇒ **读不到＝判不了**；"
              % _specs_label(CODE_SPECS), file=out)
        print("     按本仓口径**空集不许判绿**（照 `scripts/verify/spec_shape.py:71-72`）。", file=out)
        print("STATUS=NO-INPUT", file=out)
        print("结论 = **rc=2**（空集／读不到；**不是通过**）", file=out)
        return 2

    def face_rows(face, items):
        print("", file=out)
        print("── %s（%d 件；FAIL %d／WARN %d）──"
              % (FACE_TITLES[face], len(items),
                 sum(1 for r in items if r["verdict"] == FAIL),
                 sum(1 for r in items if r["verdict"] == WARN)), file=out)
        print("   %-5s %-62s %6s %5s %5s" % ("判定", "件", "行数", "目标", "硬顶"), file=out)
        shown = items if show_all else [r for r in items if r["verdict"] != OK]
        for r in sorted(shown, key=lambda x: -x["lines"]):
            print("   %-5s %-62s %6d %5d %5d"
                  % (r["verdict"], r["path"], r["lines"],
                     limits[r["face"]]["target"], limits[r["face"]]["cap"]), file=out)
        if not show_all and len(shown) != len(items):
            print("   …（%d 件 OK 未逐件列出；`--all` 可全列）" % (len(items) - len(shown)), file=out)

    face_rows("code", code)
    face_rows("doc", by_face["doc"])

    struct = structure_hits(rows, limits)
    print("", file=out)
    print("── 面③ 结构（夹内只有 1 件、且该件超【目标】）——「只原子化没模块化」的形状 ──", file=out)
    print("   （判据范围＝面① 代码；工程域「一夹一件」是命名规矩的规定动作，不在此列）", file=out)
    if struct:
        print("   %-5s %-52s %6s" % ("判定", "夹 → 件", "行数"), file=out)
        for d, p, n in struct:
            print("   %-5s %-52s %6d" % (FAIL, "%s → %s" % (d, os.path.basename(p)), n), file=out)
    else:
        print("   （无命中）", file=out)

    face_rows("judge", by_face["judge"])

    print("", file=out)
    print("── 汇总（四面计数，现算）──", file=out)
    for face in FACE_ORDER:
        items = by_face[face]
        f = sum(1 for r in items if r["verdict"] == FAIL)
        w = sum(1 for r in items if r["verdict"] == WARN)
        print("   %s：%d 件；红（>%d）%d ／ 黄（>%d）%d ／ 最大 %d 行（%s）"
              % (FACE_TITLES[face], len(items), limits[face]["cap"], f,
                 limits[face]["target"], w,
                 (max(r["lines"] for r in items) if items else 0),
                 (max(items, key=lambda r: r["lines"])["path"] if items else "—")), file=out)
    print("   面③ 结构：命中 %d 个夹（判红条件＝夹内单件超目标）" % len(struct), file=out)

    n_fail = {f: sum(1 for r in by_face[f] if r["verdict"] == FAIL) for f in by_face}
    bad = sum(n_fail.values()) + len(struct)
    if bad:
        print("STATUS=FAIL", file=out)
        print("结论 = **红**：%d 条（面① %d ＋ 面② %d ＋ 面③ %d ＋ 面④ %d）"
              % (bad, n_fail["code"], n_fail["doc"], len(struct), n_fail["judge"]), file=out)
        return 1
    print("STATUS=PASS", file=out)
    print("结论 = 绿（四面：无一份超硬顶；也没有「夹内单件超目标」的夹）", file=out)
    return 0


# ────────────────────────── 自证：先写会红的反例 ──────────────────────────
def _mk(p, n, one="// x\n"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(one * n, encoding="utf-8", newline="\n")


def _run_on(root, limits):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run(root, limits, out=buf)
    return rc, buf.getvalue()


def _base(tmp):
    """正控底子：三面全不超（含「一夹两件」「恰好＝目标 150」「一份判据脚本」）。"""
    _mk(tmp / "src/atom_a/mod.rs", 120)
    _mk(tmp / "src/atom_a/part.rs", 100)
    _mk(tmp / "src/atom_b/one.rs", 150)                  # 恰好＝目标 ⇒ 不算超
    _mk(tmp / "scripts/test/t1.rs", 40)
    _mk(tmp / "scripts/verify/small.py", 100, "# x\n")   # 面④ 的达标件
    _mk(tmp / "ninedim/01-意图环/01-策划/a.md", 150, "- x\n")
    (tmp / "scripts" / "verify").mkdir(parents=True, exist_ok=True)   # 仓根识别要它


def self_test():
    """正控 ＋ 逐条反例：**每条反例都必须能指名是哪一件**（指名不中 ⇒ 自证失败）。"""
    print("== module_size_guard --self-test ==")
    lim = {"code": {"target": 150, "cap": 250}, "doc": {"target": 150, "cap": 250},
           "judge": {"target": 150, "cap": 250}}
    cases = []

    def case(label, setup, want_rc, must_in=None, must_not=None, limits=None):
        with tempfile.TemporaryDirectory(prefix="modsize-") as d:
            tmp = Path(d)
            _base(tmp)
            if setup:
                setup(tmp)
            rc, output = _run_on(tmp, limits or lim)
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

    # ── 正控：三面全不超（有件恰好＝目标 150）⇒ rc=0 ──
    case("正控（面①/②/④ 全不超硬顶；`src/atom_b/one.rs` 恰在目标 150 上）",
         None, 0, must_in="STATUS=PASS")

    # ── 反例① 代码件超硬顶 ⇒ 红，且**指名** ──
    case("反例①（面①：代码件 260 行 > 硬顶 250）",
         lambda t: _mk(t / "src/atom_c/huge.rs", 260), 1, must_in="src/atom_c/huge.rs")

    # ── 反例② 文档件超硬顶 ⇒ 红，且**指名** ──
    case("反例②（面②：正文件 300 行 > 硬顶 250）",
         lambda t: _mk(t / "ninedim/01-意图环/02-需求/long.md", 300, "- x\n"), 1,
         must_in="ninedim/01-意图环/02-需求/long.md")

    # ── 对照②b `records/` 下的巨件**不算**（记录件／生成物天然长）──
    case("对照②b（`ninedim/records/` 下 900 行的生成物 ⇒ **不应红**）",
         lambda t: _mk(t / "ninedim/records/生成物/BIG.md", 900, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="ninedim/records/生成物/BIG.md")

    # ── 对照②c／②d：`06-变更/`（过程件）与 `07-待审/`（未批候选）**不算**（作者裁 2026-10-08）──
    case("对照②c（`ninedim/06-变更/` 下 400 行的过程件 ⇒ **不应红**）",
         lambda t: _mk(t / "ninedim/06-变更/2026-01-01-x/design.md", 400, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="ninedim/06-变更/2026-01-01-x/design.md")
    case("对照②d（`ninedim/07-待审/` 下 400 行的未批候选 ⇒ **不应红**）",
         lambda t: _mk(t / "ninedim/07-待审/候选件.md", 400, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="ninedim/07-待审/候选件.md")

    # ── 对照②e／②f：**件名前缀**记录类（标准 §六 落在阶段夹里，但仍是记录件）⇒ 不红 ──
    case("对照②e（`ninedim/02-枢纽A-前置闸/评审-前置-X.md` 400 行 ⇒ **不应红**：件名前缀 `评审-`）",
         lambda t: _mk(t / "ninedim/02-枢纽A-前置闸/评审-前置-X.md", 400, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="评审-前置-X.md")
    case("对照②f（`ninedim/03-执行环/05-验证证据/证据-X.md` 400 行 ⇒ **不应红**：件名前缀 `证据-`）",
         lambda t: _mk(t / "ninedim/03-执行环/05-验证证据/证据-X.md", 400, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="证据-X.md")

    # ── 对照②g：**单列豁免**《合订本》⇒ 不红 ──
    case("对照②g（`ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md` 900 行 ⇒ **不应红**：单列豁免）",
         lambda t: _mk(t / "ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md", 900, "- x\n"), 0,
         must_in="STATUS=PASS", must_not="策划-理论书-第一版-合订.md")

    # ── 反例②h：**其余正文件照判**（证明排除面没被放宽成"整夹不判"）──
    case("反例②h（`ninedim/03-执行环/03-测试/测试-X.md` 400 行 ⇒ **应红**：正文件照判）",
         lambda t: _mk(t / "ninedim/03-执行环/03-测试/测试-X.md", 400, "- x\n"), 1,
         must_in="ninedim/03-执行环/03-测试/测试-X.md")

    # ── 反例②i：**路径段排除只认 `ninedim/` 顶层**（作者裁 2026-10-08 收紧）──
    #    嵌套同名夹（`ninedim/01-意图环/records/`）**不许**被排掉 ⇒ 400 行**应红**。
    case("反例②i（`ninedim/01-意图环/records/nested.md` 400 行 ⇒ **应红**："
         "同名夹只在顶层才排）",
         lambda t: _mk(t / "ninedim/01-意图环/records/nested.md", 400, "- x\n"), 1,
         must_in="ninedim/01-意图环/records/nested.md")

    # ── 反例③ **面③**：夹内只有 1 件、而它**超目标但未超硬顶**（200 行）⇒ 面③ 自己会红 ──
    #    ★ 这一条是面③ 的**唯一**证明：200 行 < 硬顶 250 ⇒ 面① **不会**红 ⇒ rc=1 只能来自面③。
    case("反例③（面③：`src/atom_d/` 只有 1 件且 200 行 > 目标 150，未超硬顶 ⇒ 只在面③ 红）",
         lambda t: _mk(t / "src/atom_d/only.rs", 200), 1, must_in="src/atom_d/only.rs")

    # ── 对照③b 同夹**再加一件**（＝真的拆开了）⇒ 面③ 不再命中 ⇒ 全绿 ──
    def _two(t):
        _mk(t / "src/atom_d/only.rs", 200)
        _mk(t / "src/atom_d/second.rs", 30)
    case("对照③b（同夹两件 ⇒ 面③ **不应**命中；两件都 ≤ 硬顶 ⇒ 绿）",
         _two, 0, must_in="STATUS=PASS")

    # ── 对照③c **面③ 不判面④**：`scripts/solo/` 只有 1 件且超目标 ⇒ 面③ **不许**命中 ──
    out3c = case("对照③c（面③ **只判面①**：`scripts/solo/` 单件 300 行 ⇒ 红来自面④，面③ 段应「无命中」）",
                 lambda t: _mk(t / "scripts/solo/huge_judge.py", 300, "# x\n"), 1,
                 must_in="scripts/solo/huge_judge.py")
    cases.append(("对照③c-断言（面③ 段印「（无命中）」＝它没把面④ 的单件夹当'没模块化'）",
                  "（无命中）" in out3c, "面③ 段含 `（无命中）`"))

    # ── 反例④ 边界正控：**恰好等于阈值** ⇒ 不红（150＝目标、250＝硬顶都在内）──
    #   ★ 夹具要点：两件都放进 `src/atom_a/`（**已有 2 件的夹**）——若各建一个新夹，
    #     250 那件会**同时命中面③**（夹内单件超目标）⇒ 那测的就成了面③，不是边界。
    def _exact(t):
        _mk(t / "src/atom_a/exact_target.rs", 150)       # 恰好＝目标 ⇒ OK
        _mk(t / "src/atom_a/exact_cap.rs", 250)          # 恰好＝硬顶 ⇒ WARN，**不红**
    out4 = case("反例④（边界：150 恰好＝目标、250 恰好＝硬顶）⇒ **不红**",
                _exact, 0, must_in="STATUS=PASS")
    _lines4 = out4.splitlines()
    cases.append(("反例④b（250 那件应落在 WARN 档而不是 FAIL；150 那件应落在 OK 档）",
                  any(("WARN" in ln and "exact_cap.rs" in ln) for ln in _lines4)
                  and any(("OK" in ln and "exact_target.rs" in ln) for ln in _lines4)
                  and not any(("FAIL" in ln and "exact_cap.rs" in ln) for ln in _lines4),
                  "逐件表里 `exact_cap.rs` 是 WARN 行、`exact_target.rs` 是 OK 行、都不是 FAIL 行"))

    # ── 反例⑤ 扫不到任何 `.rs` ⇒ rc=2（空集不许判绿）──
    def _no_rs(t):
        shutil.rmtree(t / "src")
        shutil.rmtree(t / "scripts" / "test")
    case("反例⑤（面① 一份 `.rs` 都扫不到）", _no_rs, 2, must_in="STATUS=NO-INPUT")

    # ── 反例⑥ `--max` 覆盖硬顶：同一件在收窄到 120 后转红 ──
    case("反例⑥（`--max 120` 收窄：`src/atom_b/one.rs` 150 行 > 硬顶 120 ⇒ 红且指名）",
         None, 1, must_in="src/atom_b/one.rs",
         limits={"code": {"target": 120, "cap": 120}, "doc": {"target": 120, "cap": 120},
                 "judge": {"target": 120, "cap": 120}})

    # ── ★ 反例⑧ **面④**：判据脚本超硬顶 ⇒ 红且指名 ──
    out8 = case("反例⑧（面④：`scripts/verify/big_judge.py` 300 行 > 硬顶 250 ⇒ 红且指名）",
                lambda t: _mk(t / "scripts/verify/big_judge.py", 300, "# x\n"), 1,
                must_in="scripts/verify/big_judge.py")

    def _summary_line(text, face_title):
        for ln in text.splitlines():
            if ln.strip().startswith(face_title + "："):
                return ln
        return ""

    _s8_code = _summary_line(out8, "面① 代码")
    _s8_judge = _summary_line(out8, "面④ 判据脚本")
    cases.append(("反例⑧b（面④ 是**独立一面**：`.py` 只进面④ 的红、**不进**面① 的红）",
                  ("面④ 判据脚本" in out8)
                  and ("红（>250）0" in _s8_code) and ("红（>250）1" in _s8_judge),
                  "面① 汇总行「红 0」、面④ 汇总行「红 1」：%r ／ %r"
                  % (_s8_code.strip()[:60], _s8_judge.strip()[:60])))

    # ── ★ 反例⑩ **面④ 收 `.sh`**（作者裁 2026-10-08 并入）：`.sh` 超硬顶 ⇒ 红且指名 ──
    out10 = case("反例⑩（面④ 收 `.sh`：`scripts/test/big_probe.sh` 300 行 > 硬顶 250 ⇒ 红且指名）",
                 lambda t: _mk(t / "scripts/test/big_probe.sh", 300, "# x\n"), 1,
                 must_in="scripts/test/big_probe.sh")
    cases.append(("反例⑩b（面④ 收 `.sh` 的证据：面④ 汇总行「红 1」、面① 汇总行「红 0」（`.sh` 不进面①））",
                  ("红（>250）1" in _summary_line(out10, "面④ 判据脚本"))
                  and ("红（>250）0" in _summary_line(out10, "面① 代码")),
                  "面④ 红 1／面① 红 0：%r"
                  % _summary_line(out10, "面④ 判据脚本").strip()[:60]))

    # ── ★ 对照⑪ **读数纪律写在输出里**（作者裁 2026-10-08：写死它比报任何单个数都有用）──
    #    删掉那句 ⇒ 本反例红（自证会挡住"把纪律悄悄删掉"）。
    cases.append(("对照⑪（读数纪律必须出现在**输出**里：`只引同一次运行的成对读数；跨运行不可相减`）",
                  "只引同一次运行的成对读数；跨运行不可相减" in out10,
                  "输出含读数纪律那一句"))

    # ── 反例⑨ **本件自己也在面④**（不给自己开口子）：真仓跑一次，输出里必须能见到本件 ──
    real = Path(__file__).resolve().parent.parent.parent
    _, real_out = _run_on(real, lim)
    me = "scripts/verify/module_size_guard.py"
    cases.append(("反例⑨（自省：真仓输出里 `%s` 出现在面④ 逐件表 ⇒ 对自己不豁免）" % me,
                  ("面④ 判据脚本" in real_out) and (me in real_out),
                  "真仓输出含面④ 段且含 `%s`" % me))

    # ── 反例⑦ 仓根错 ⇒ rc=2（走 main，不进扫描）──
    with tempfile.TemporaryDirectory(prefix="modsize-") as d:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc7 = main(["--repo", str(Path(d) / "no-such-repo")])
    cases.append(("反例⑦（`--repo` 指到不存在的仓根）⇒ rc=2",
                  rc7 == 2, "rc=%d（期望 2）" % rc7))

    bad = 0
    for label, ok, detail in cases:
        print("  %s %s ⇒ %s" % ("✅" if ok else "❌", label, detail))
        if not ok:
            bad += 1
    print("  自证：%d/%d 例通过" % (len(cases) - bad, len(cases)))
    if bad:
        print("  => 自证**不通过**：%d 例不符；按本仓口径，这条守卫是装饰，拒绝合入。" % bad)
        return 1
    print("  => 自证通过：正控 rc=0 ＋ 反例逐条变红**且指名到件**"
          "（面①／面②／面③／**面④（含 `.sh`）**／空集 rc=2／`--max` 覆盖／仓根错 rc=2）")
    print("     （「不应红」的对照 9 处：`records/`／`06-变更/`／`07-待审/` 顶层环夹下的巨件、"
          "件名前缀 `评审-`／`证据-`、单列豁免《合订本》、同夹加一件后面③ 不命中、恰好等于阈值；"
          "另 2 处是**必须红**的正控面：嵌套同名夹不算、`.sh` 并入面④）")
    return 0


# ────────────────────────── 入口 ──────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="「模块化」尺寸判据（面①代码／面②文档／面③结构／面④判据脚本；"
                    "依据＝作者「几十行」口径）")
    ap.add_argument("--repo", default=None, help="仓根；默认从本脚本位置向上找（含 src 与 scripts/verify）")
    ap.add_argument("--max", type=int, default=None,
                    help="覆盖**硬顶**行数（并把目标夹到 min(目标, 硬顶)）")
    ap.add_argument("--target", type=int, default=None, help="覆盖**目标**行数（默认 150）")
    ap.add_argument("--all", action="store_true", help="逐件全列（默认已全列；留作显式声明）")
    ap.add_argument("--self-test", action="store_true", help="正控 ＋ 逐条反例（反例必红且指名）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.repo) if args.repo else find_repo(Path(__file__).parent)
    if not repo or not Path(repo).is_dir():
        print("* 仓根错／找不到（要有 `src/` 与 `scripts/verify/`）；用 `--repo` 指定。", file=sys.stderr)
        print("STATUS=ERROR", file=sys.stderr)
        return 2

    limits = {f: dict(LIMITS[f]) for f in LIMITS}
    if args.max is not None:
        if args.max <= 0:
            print("* `--max` 必须是正整数。", file=sys.stderr)
            print("STATUS=ERROR", file=sys.stderr)
            return 2
        for face in limits:
            limits[face]["cap"] = args.max
            limits[face]["target"] = min(limits[face]["target"], args.max)
    if args.target is not None:
        if args.target <= 0:
            print("* `--target` 必须是正整数。", file=sys.stderr)
            print("STATUS=ERROR", file=sys.stderr)
            return 2
        for face in limits:
            limits[face]["target"] = min(args.target, limits[face]["cap"])

    return run(repo, limits, show_all=True)


if __name__ == "__main__":
    sys.exit(main())
