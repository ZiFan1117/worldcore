#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""module_graph.py —— 机核层的守卫：把 `WC-ATOM-001` §四 机核清单的四条做成**会真红的东西**。

为什么需要它
------------
`WC-ATOM-001`（原子化编程约定，本项目**强制**）§四 机核清单逐条给了判据，
但它的今日状态栏自己写着第 1–4 条 **「未建」/「未建闸」**：

| # | 断言 | 落点 |
|---|---|---|
| 1 | 每个原子有且只有一句 `intent` | 本脚本判据① |
| 2 | 每原子的实现／测试／契约三件齐备 | 本脚本判据③ |
| 3 | `deps == import` 且无环 | 本脚本判据② |
| 4 | 原子档字段齐备且取值真（登记表每一行的原子化栏位） | 本脚本判据④ |
| 5 | 生成物与源一致（`WC-MODREG-001`） | **仍未建闸**——本脚**不**声称它在管这条 |

**一个从不失败的检查不是装饰，是假证**——本项目既有口径（`tools/spec_bridge.py` 文件头）。
本脚本是 §四 第 1–3 条（原子侧）的**执行者**：任一条不成立即非零退出，
且 `--self-test` 为**每条判据各造一个反例**，反例不变红即判该守卫是装饰、拒绝合入。

⚠️ **上表第 5 条的如实口径**：`WC-ATOM-001` §二 A-5 要求「生成物不许手编」，而它自己 §三
把 `WC-MODREG-001` 写作「生成物，勿手编」。**本仓到今天为止没有任何生成器产出该表**——
那份登记表是**手编**的。故本脚本**不**把 A-5 列入自己的判据（把它写成已建闸就是假证）；
`WC-ATOM-001` §五 与 `WC-MODREG-001` §3.1 按「无生成器即不称生成物」在本轮就地更正，
**A-5 的真实落点仍只有 `ninedim/records/生成物/BRIDGE.md` 那一族生成物**（判据⑪⑫⑬ 管它）。

判据（与 `WC-ATOM-001` §二 六条约定的 A-1/A-2/A-3/A-4 逐条对应）
------------------------------------------------------------------
① **A-1 单意图原子性**（`WC-ATOM-001` §二 A-1）
   每个模块**有且只有一句** `intent`，且 ≤30 字；出现并列两事（`与`/`和`/`及`）⇒ 报为可疑并列出。
   **数据源**：`WC-MODREG-001` §2 模块登记表（`M01`–`M10`）。
   **字段落点（如实声明，不许假装）**：登记表**没有** `intent` 列，最接近的是
   **「职责（一句话）」**列（`设计-WC-MODREG-001-v0.1.md:28` 表头逐字）。故本判据按
   `--intent-column` 指定的列名取值，**默认 `职责`**；占位符（`待补`/`—`/空）与超过 30 字
   同样判红。若日后登记表补出 `intent` 列，用 `--intent-column intent` 即可切换，**判据不变**。

② **A-4 依赖单向 DAG 且 `deps == import`**（`WC-ATOM-001` §二 A-4）
   **怎么抽依赖**（逐条写死口径，避免"看起来建了图"）：
     · 建**模块树**：`src/lib.rs` 的 `pub mod X;` ＋ `src/<dir>/mod.rs` 的 `pub mod Y;`
       ⇒ `X → src/X.rs`（或 `src/X/mod.rs`）、`Y → src/<dir>/Y.rs`；`crate::` 即根。
     · 解析**到模块**，不是解析到"首段"：`crate::A::B::C::…` 取**模块树里最长的真模块前缀**
       （`world_core::project::language::parse` ⇒ 模块是 `project::language`，`parse` 是函数）。
       该模块的**宿主 .rs 文件**登记在哪个模块号下 ⇒ 得到一条**模块间边**
       （`use crate::gate::…` 是 M05 内部，不是跨模块边，故**不产边**——这是"兄弟模块集"的字面口径）。
     · **花括号里的每一项都解析**：`use world_core::project::{self, language, visual};`
       ⇒ `self`＝`project` 本身，`language`／`visual` 各自落到 `project::language`／`project::visual`。
       只取首段会把 `visual`(M07) 丢掉，于是 `M04` 明明 import 了 M07、却被报成"声明了但代码里没有"。
     · **共同模块不作边目标**：`WC-MODREG-001` §2.1 登记为「**不占号**」的文件（`src/event.rs`、
       `src/project/mod.rs` 这类）**不产生依赖边**。理由：A-4 判的是**模块号之间**的 DAG，
       一个显式声明不占号的文件按定义落在这个映射之外；把它当边目标时**归属是任意的**
       （`project/mod.rs` 横跨 M06/M07，工具挑 M06 ⇒ `M07` 里一句 `use crate::project::{…}`
       被记成"依赖 M06"——凭空一条边）。**跳过不静默**：逐条列在报告里
       （正跑单独打印一段、JSON 有 `import_edges_skipped_shared`），只是**不算 offender**。
     · **两处都抽**：① 行首 `use …`；② **行内全限定路径**（`crate::guard::assert_not_other_writable(…)`
       ——Rust 不写 `use` 也能直接用全路径，本仓 `src/ontology.rs:134`、`src/channel.rs:184` 就是这么写的）。
       只抽 ① 会把**真的依赖**判成「声明了但代码里没有」⇒ 逼人把真依赖从登记表里删掉：
       那不是"报得严"，是**拿关卡去改坏唯一数据源**（A-4 判的是"声明集 ≡ 真实依赖集"）。
     · **注释与字符串不算**：整行 `//`／`///`／`//!` 里的 `crate::…` 是文档链接（`src/delivery.rs:21`、
       `src/event.rs:9` 这类），字符串字面量里的 `crate::…` 是数据；抽了它们，一句 `//!` 或一个字符串
       就能凭空造出一条跨模块边。**只抽代码里真会被解析的路径。**
       （已知边界：嵌套花括号 `use a::{b::{c, d}};` 只展开外层——本仓实测 0 处；
       内层名字解析不到模块 ⇒ 不产边，宁少不错。）
     · **只抽生产路径**：`#[cfg(test)]` 起始的 `mod` 块内的 `use` **不计入**（`WC-MODREG-001`
       §4.2 自己就是这么划界的：「两条看似回边、实为测试内」）。`tests/*.rs` 整文件视为测试侧，
       是 `WC-ATOM-001` §三 的「测试」落点，不是实现依赖面。
     · 无环：对**真实 import 边**与**声明边 ∪ 真实边**分别跑 Kahn 拓扑排序（排不完即有环），
       再用**强连通分量**把**每一条**真环各打印一条逐段可验的环路径（不是因为"报不出路径"才退化成节点集合）。
       并集那一条是**设计面**的环：环上凡有「只在登记表里、源码里找不到」的边，**逐条标出来**——
       那种环**改代码消不掉**（要先补实现或改声明），**不许混进"源码 import 环"**。
     · `deps == import`：登记表「依赖模块」列 → `{模块号: 出边集}`，与真实 import 边集**逐模块相等**；
       不一致时分别列出「声明了但代码里没有」与「代码里有但没声明」。
       **目录型模块（`src/carrier/` → M10）也逐边核对**：只要它的实现文件（目录下真实的 `.rs`）
       在磁盘上，就按同一套口径抽边、比对——**不整条跳过**（跳过＝"有声明、没人看"，
       而环检测却照样拿它的声明边去凑环）。实现文件一个都没有才跳过（那是 A-2「实现缺」的事）。

③ **A-2 四件同夹**（`WC-ATOM-001` §二 A-2）
   登记表里每个模块，其**实现／测试／契约**三者都要有落点（本仓 `tests/` 与 `src/` 不同夹——
   登记表自己说"部分（测试在 `tests/*.rs`，与 src 不同夹）"——故按**可指认**判，不按同目录判）：
     · **实现** ＝ 登记表「源码路径」列列出的文件在磁盘上真实存在（`src/**`）；
       登记表列了「计划路径」而源码未落成 ⇒ 报「实现缺」。
     · **测试** ＝ `tests/*.rs` 里能**指到该模块**的用例：该文件 `use world_core::<seg>` 里的 `<seg>`
       经模块树归属到本模块 ⇒ 该文件的用例算它的；一个锚点都不指 ⇒ 报「测试缺」。
       （`tests/*.rs` 整文件 `use world_core;` 而无具名子模块者——即 CLI 端到端用例——
       归 `src/main.rs` 的宿主模块，即「运行时入口」；理由写在 `test_anchor()`。）
     · **契约** ＝ 文档或规格里有落点：`docs/S2-设计/设计-WC-IC-001-v0.1.md`（接口契约**一册**）
       里有一条**含本模块号的标题**（形如 `### §5.1 \`M01\` …`），
       **或** `ninedim/01-意图环/04-规格/**/spec.md` 里有 Requirement 的证据行指到本模块的测试锚点
       （`WC-ATOM-001` §三：「规格条目（一条 Requirement）＋ `WC-IC-001` 里的模块接口契约节」）。
       **2026-09-27 改**：原按 `docs/S2-设计/WC-IC-M<NN>-*.md` **分册存在**判 —— 那 11 册已按
       「文档不要太散」**并入 `WC-IC-001` 一册**（每模块一节），故判据改为
       **「在 `WC-IC-001` 里找得到该模块的节」**；判据强度不变：**找不到该模块号即仍报「契约缺」**。
     另有**覆盖面**一项：`src/**/*.rs` 里**没有任何模块号认领**的文件（`WC-MODREG-001` §4.3 #1
       自己登记的缺口就是 `src/error.rs`）逐条列出。

④ **A-3 契约字段齐 · 原子档栏位**（`WC-ATOM-001` §二 A-3 的**模块级**落点，**与 `WC-ATOM-001` §五 互为落点**）
   A-3 要求 `intent / input / output / side_effects` 必写。**模块这一级的载体是 `WC-MODREG-001` §2**：
   登记表**为每一行**给出下列栏位，本判据**逐行查、逐栏查**——缺一栏即指名报红。
   **为什么要有它**：A-3 原文只钉在"`design.md` 的原子表"上（那是 change 件，**归档后就不在树里**），
   于是"四个字段必写"这件事在**常驻文档**里没有任何人管；这条判据就是补上那个常驻落点。

   | 栏位（表头逐字） | 查什么 |
   |---|---|
   | `intent（一句话）` | 列**在**、取值**非占位**、一句话（同一套口径：剥强调与空白后 ≤%d 字）、**无并列两事** |
   | `deps 机核` | 列在、取值非空（登记表在这一格里自述"声明的依赖集必须与真实 import 集逐条相等"，且**点名本工具**） |
   | `契约锚点（WC-IC-001）` | 列在、取值非空；**逐个 `IF-0xx` 必须在 `WC-IC-001` 里真出现**（数字不得凭空写） |
   | `四件同夹证据` | 列在、取值非空；**每个 `tests/…::fn` token 必须是真存在的 `#[test]` 函数**（复用判据③的锚点面）；**至少要有一个**——一个都没有就是"只有声明、没有测试落点" |
   | `side_effects` | 列在、取值非空（A-3：**不写副作用＝声明无副作用**，但不许留空） |

   **取值真不真，不只查"非空"**：`契约锚点` 的 `IF-0xx` 与 `四件同夹证据` 的测试 token 都**回源核对**——
   否则"填一格看着像"的假话照样过关（本项目对"搜字样 ≠ 认结构"有既有血泪口径）。
   **⚠ 本判据的边界（如实说，不许含糊）**：它**不**判 `side_effects` 那句**内容对不对**
   （机器读不出"这个模块有没有没写出来的副作用"⇒ **那一条只有人核**），
   也不判 `契约锚点` 指的**那一节写得好不好**。它判的是"这一格填了、且填的号码/测试**真存在**"。

   **语义口径**：`intent` 与表内既有的**「职责（一句话）」列同义**（那一列就是 A-1 的 `intent`，见判据①）。
   本判据**要求两处都在、且逐字相同**——两处不一致即报红（同一件事两个说法，正是 A-1 要消灭的形态）。
   **列序不得动**：本判据要求的栏位**一律加在表末**（`依赖模块` 之后）。
   理由：`deps == import` 的取格是**按下标**（`cells[4]`）走的，`tools/ic_books_check.py` 同款——
   在它前面插列会让两个门禁**读错列**，那种红是"改坏了门禁"，会被读成"世界坏了"。

⑤ **自己也要自证**（`--self-test`）
   照 `tools/spec_bridge.py --self-test` 的结构与输出风格：搭一个**完好沙盒**做正控（四条应全绿），
   再**为每条判据各造一个反例**，反例不变红即判该守卫是装饰 ⇒ rc=1。
   正控与反例都打印逐字结果，并带"恢复后回到绿"的第二正控。

用法
----
    python3 tools/module_graph.py [--repo <world-core 或仓库根>] [--json]
    python3 tools/module_graph.py --self-test     # 每条判据一个反例，全红才 rc=0

退出码：0 = 全通过；1 = 有判据不成立（含自证失败）；2 = 用法错误。
"""

from __future__ import annotations

import argparse
import builtins
import io
import json
import os
import re
import shutil
import sys
import tempfile

#: 登记表相对于 world-core 根的路径（唯一数据源，`WC-ATOM-001` §二 A-1 判据指定的数据源）。
MODREG_REL = os.path.join("ninedim", "01-意图环", "03-设计", "设计-WC-MODREG-001-v0.1.md")
SRC_REL = "src"
TESTS_REL = os.path.join("scripts", "test")
IC_DIR_REL = os.path.join("ninedim", "01-意图环", "03-设计")
#: 接口契约**一册**（`WC-ATOM-001` §三 的模块契约落点；`M01`–`M10` 各一节，判据③ 按节标题找模块号）。
IC_BOOK_REL = os.path.join("ninedim", "01-意图环", "03-设计", "设计-WC-IC-001-v0.1.md")
SPECS_REL = os.path.join("openspec", "specs")

#: A-1 的字数上限。出处＝`WC-ATOM-001` **§二 A-1 的对照表**；⚠ **但「≤30 字」是本项目自定的阈值**——
#: 该件 `:24` 逐字声明「（"≤30 字"是本项目的自定阈值，参照仓无此数……不许把它说成参照仓的要求）」，
#: 而 §二 A-1 格内、§四 机核清单第 1 行**都没有**这五个字。
#: ⇒ 本常量是**项目自定判据**，不许在输出或文档里写成外部标准的要求。
#: 口径：**计 Unicode 字符数**，不计字节；判定前剥掉 Markdown 强调与空白（`**`／空白不算字）。
INTENT_MAX_CHARS = 30
#: 并列两事的连接词（A-1：「出现并列两事 ⇒ 拆」）。只取这三个字面，不猜别的词。
PARALLEL_MARKERS = ("与", "和", "及")
#: 取值单元格里的占位符：等于这些值即视为"没写"。
PLACEHOLDERS = ("", "—", "-", "–", "待补", "待定", "n/a", "N/A", "<待人工>", "待人工指派")
#: ★ 2026-09-28 加：「**指针式**填法」不算读数。
#: 为什么：`WC-MODREG-001` §2 的「机核读数」列**十二行逐字相同**——
#:   「以判据②（deps == import）现场读数为准」。它**点了名、也含 `deps == import`**，
#:   于是过了原来的第⑦步，可是**一个读数都没有**（评审席判"已经 10/10 空转"）。
#: 这一栏要的是**命令与原始输出**（`WC-ATOM-001` §四：机核读数＝贴命令与原始输出），
#: 不是"去哪看"。⇒ 命中本表任一标记即判红，并要求该格**含反引号包起来的命令**。
MACHINE_POINTER_MARKERS = ("以判据", "现场读数为准", "以…为准", "以命令输出为准", "见主规格")

#: 模块号形态（判定面唯一编号口径，`WC-MODREG-001` §3：「`M` + 两位数字，左补零」）。
M_RE = re.compile(r"M\d{2}")

#: 判据④ 要求的**原子档栏位**：{内部键: (报告名, 可接受的表头写法…)}。
#: 取值按**表头**认列（不按下标）——表头被改名/漏字 ⇒ 报"列缺失"，不静默。
#: ⚠️ 后缀 `（…）` 是**可选**的：表头写 `intent` 或 `intent（一句话）` 都认。
ATOM_FIELDS = {
    "a_intent":     ("intent（一句话）",     ("intent", "意图")),
    "a_deps":       ("deps 机核",            ("deps 机核", "依赖机核")),
    "a_anchor":     ("契约锚点",             ("契约锚点",)),
    "a_evidence":   ("四件同夹证据",         ("四件同夹证据", "同夹证据")),
    "a_side":       ("side_effects",         ("side_effects", "副作用")),
    "a_machine":    ("机核读数",             ("机核读数",)),
}
#: ⚠️ 认列是**前缀＋边界**匹配（见 `_atom_col_map`），故别名之间**不许互为前缀**：
#: 早先 `deps` 能匹配到 `deps 机核`，但它同时也能匹配到……任何以 `deps ` 开头的格；
#: 真正的坑在反向——别名越短越容易被隔壁那格撞上。别名的形态与**真表表头逐字**一致最稳。
#: 依赖栏位必须点名的工具（"本列由谁判"不许含糊）。
ATOM_DEPS_TOOL = "module_graph.py"
#: 机器读数列必须点名的判据（本工具自己那一条）。
ATOM_MACHINE_MARK = "deps == import"
#: 判据④ 第⑦步要求「机核读数」格里**含命令**。认三种形态（与仓内既有写法对齐）：
#: 反引号包起来的、或含 `python`／`cargo`／`bash` 之类命令名。
ATOM_MACHINE_CMD_RE = re.compile(r"`[^`]+`|\b(?:python3?|cargo|bash|sh|pwsh|npx|openspec)\b")


# 非 UTF-8 控制台（Windows GBK/cp936）下，中文与记号会让 print 抛 UnicodeEncodeError
# —— 那会变成"门禁自己崩了"的假失败。按本项目既有口径（`tools/spec_bridge.py:44-51`）：
# **只重配 errors，不改 encoding**（UTF-8 环境下逐字节等价）；记号一律用 ASCII。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except Exception:
        pass


# ────────────────────────── 工具 ──────────────────────────
def find_worldcore(start):
    """从 start 往上找 ``（判据面以它为准：`tools/` 的父目录）。"""
    p = os.path.abspath(start)
    for cand in [p] + list(_parents(p)):
        if os.path.isfile(os.path.join(cand, MODREG_REL)):
            return cand
    return None


def _parents(p):
    out = []
    cur = os.path.dirname(p)
    while True:
        out.append(cur)
        nxt = os.path.dirname(cur)
        if nxt == cur:
            return out
        cur = nxt


def rel(base, p):
    try:
        return os.path.relpath(p, base).replace("\\", "/")
    except Exception:
        return str(p)


def read_text(p):
    """按项目编码纪律读文件：UTF-8、`errors="replace"`（坏字节不使门禁崩，而由编码闸单独判）。"""
    try:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def norm_cell(s):
    """单元格归一：去 Markdown 强调、去首尾空白与全角空格。"""
    return (s or "").replace("**", "").replace("`", "").strip().strip("\u3000").strip()


def is_placeholder(s):
    return norm_cell(s) in PLACEHOLDERS


def visual_len(s):
    """判据用的"字数"：剥掉 Markdown 强调与全部空白后计 Unicode 字符数。"""
    return len(re.sub(r"\s+", "", (s or "").replace("**", "").replace("`", "")))


# ────────────────────────── 登记表解析 ──────────────────────────
def _atom_col_map(text):
    """`WC-MODREG-001` 全文里**每个原子档表块**的表头 → `{内部键: 下标}`。

    为什么按表头认列而**不写死下标**：判据④（A-3 原子档栏位）要求的那几栏是**加在表末**的，
    而 `deps == import` 的取格是按下标走的（本文件 `cells[4]`、`tools/ic_books_check.py` 同款）。
    按表头认列 ⇒ 栏位顺序可以变、栏位可以增删，判据**只认名字**；
    名字被改掉时它报"列缺失"，而不是悄悄取到隔壁那一格的文字
    （本项目既有血泪口径：**搜字样 ≠ 认结构**、**判据不许取文件里第一处字样**）。

    只认**表头行**（第一格逐字等于 `模块号`）。同一份文档里有多个表块（§2 主表、§2.1、附录 A 旧表…）
    时逐块记一次；数据行按"最近一次见到的表头"归属。这样 §2 主表与附录 A 的旧表各按各的表头算。

    ★ **下标必须与 `read_registry` 的数据行同口径**（血泪，本轮踩了）：
    数据行走的是 `re.match(r"^\\|\\s*\\*{0,2}(M\\d{2})\\*{0,2}\\s*\\|(.*)$")` ＋ `m.group(2).split("|")`，
    而 `(M\\d{2})` 后面那个 `\\s*` 会**吃掉模块号格与其后管道之间的空格**，`group(2)` 于是**不再**
    以空格开头 ⇒ 它的 `cells[0]` 就是「模块名」，**比表头的 `line.split("|")[1:-1]` 少一格**。
    表头按自身下标给出 `a_intent→6`，数据行同一栏却在 `cells[5]` ⇒ **每条原子判据都去读隔壁那一格**，
    而输出看起来像"判据抓到了错"。故表头下标一律**减 1**（`i - 1`），与数据行对齐；
    对齐关系写死在 `_atom_col_map` 的返回值里，由 `j_a0_atom_fields` 的回源核对兜底。
    """
    out, cur = [], None
    for line in (text or "").split("\n"):
        if not line.lstrip().startswith("|"):
            continue
        cells = [norm_cell(c) for c in line.split("|")[1:-1]]
        if not cells or cells[0] != "模块号":
            continue
        cur = {}
        for key, (_label, aliases) in ATOM_FIELDS.items():
            for i, c in enumerate(cells):
                # 认列口径：**别名 ＋ 边界**。边界＝行尾／`（`／空格。
                # 为什么要有边界：`deps` 必须认到 `deps 机核`（别名后跟空格），
                # 但一旦有人另加一列叫「证据」，无边界的 `startswith` 会把它和
                # `四件同夹证据` 之外的名字混起来——认列必须按**边界**取，不按"像"取。
                if any((c == a) or c.startswith(a + "（") or c.startswith(a + " ") for a in aliases):
                    cur[key] = i - 1          # ← 与数据行的 `cells` 口径对齐（见 docstring ★）
                    break
        out.append(cur)
    return out


def read_registry(wc):
    """返回 (path, text, {模块号: {line, name, intent, src_cell, ifs, deps, deps_cell, atom}})。

    只在 `## §2 模块登记表` 这一节内取表（附录 A 是**旧表**、口径不同，
    混取会让判据失去意义——同 `tools/ic_books_check.py:80-91` 的口径）。

    `atom` ＝ 该行**原子档栏位**的取值（键见 `ATOM_FIELDS`）。取不到的键**不出现**在 `atom` 里
    ——判据④ 就是靠"键在不在"来判"列缺失"，而不是靠"取到了空串"。
    """
    p = os.path.join(wc, MODREG_REL)
    if not os.path.isfile(p):
        return p, "", {}
    text = read_text(p)
    atom_cols = _atom_col_map(text)
    sec = re.search(r"(?ms)^##\s*§2\s*模块登记表(.*?)(?=^##\s|\Z)", text)
    rows = {}
    if not sec:
        return p, text, rows
    lines = sec.group(1).split("\n")
    # 该节的绝对行号偏移（报错必须给**文件里的真行号**）
    off = text[: sec.start(1)].count("\n")
    cur_atom = {}
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|"):
            cells_h = [norm_cell(c) for c in line.split("|")[1:-1]]
            if cells_h and cells_h[0] == "模块号":
                # ★ 本轮修（E8）：**删掉"回落到第一个表块"那条静默兜底**。
                #   旧实现在表头没有全部原子列时，`next((a for a in atom_cols), {})`
                #   会把**文档里第一个表块**当成 §2 的表头 —— 于是判据④ 可能拿着一份
                #   **别的表**的列名去判本表的行，而它看起来像"判据在正常工作"。
                #   现在取不到「全六列」的表头就**留空** ⇒ 每行的 `atom` 为空 ⇒
                #   `j_a0_atom_fields` 以「**原子档栏位整组缺失**」逐行报红（**不静默**）。
                cur_atom = next((a for a in atom_cols if all(
                    a.get(k) is not None for k in ("a_intent", "a_deps", "a_anchor",
                                                   "a_evidence", "a_side", "a_machine"))), {})
        m = re.match(r"^\|\s*\*{0,2}(M\d{2})\*{0,2}\s*\|(.*)$", line)
        if not m:
            continue
        cells = m.group(2).split("|")
        if len(cells) < 5:
            continue
        mid = m.group(1)
        src_cell = norm_cell(cells[2])
        # 源码路径列：取 `src/...` 形态的路径。**目录那一条保留尾斜杠**（`src/carrier/`）——
        # 去掉尾斜杠会让"目录存在"冒充"实现文件存在"（`os.path.exists('src/carrier')` 为真）。
        src_all = []
        for raw in re.findall(r"src/[A-Za-z0-9_./-]+", src_cell):
            raw = raw.rstrip("/")                         # 去掉 re 可能吃进的尾斜杠
            if re.search(re.escape(raw) + r"/", src_cell):
                raw = raw + "/"                           # 原格写的是目录 ⇒ 还原目录形态
            if raw not in src_all:
                src_all.append(raw)
        # 原子档栏位：按**表头下标**取值；下标越界 ⇒ 该键不出现（判据④ 报"列缺失"）
        atom = {}
        for key, idx in cur_atom.items():
            if 0 <= idx < len(cells):
                atom[key] = (cells[idx] or "").strip()
        rows[mid] = {
            "line": off + i + 1,
            "name": norm_cell(re.sub(r"（[^）]*）\s*$", "", cells[0])),
            "intent": norm_cell(cells[1]),
            "intent_raw": (cells[1] or "").strip(),
            "src_cell": src_cell,
            "src_all": src_all,
            "src_files": [s for s in src_all if s.endswith(".rs")],
            "src_dirs": [s for s in src_all if s.endswith("/")],
            "ifs": sorted(set(re.findall(r"IF-\d{3}", "|".join(cells[3:-1])))),
            "deps_cell": norm_cell(cells[4]),
            "deps": set(M_RE.findall(cells[4])),
            "atom": atom,
            "atom_cols_seen": bool(cur_atom),
        }
        # 「计划路径」的判据：登记表在这一行里自己声明了"尚未落成 / 计划"（M10 行的字面口径）。
        rows[mid]["planned"] = ("计划" in src_cell) or ("尚未落成" in src_cell)
    return p, text, rows


#: `WC-MODREG-001` §2.1「共同模块、未登记文件与模块号边界」表的行。
SHARED_ROW_RE = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|(.*)$")


def read_shared_modules(text):
    """`WC-MODREG-001` §2.1 表 → {源码路径: 归属模块号}。

    为什么必须读它：`src/event.rs`、`src/project/mod.rs` 是登记表自己声明的**共同模块**
    （`设计-WC-MODREG-001-v0.1.md:49-50`：「不占号，属 M01 的机制面」／「横跨 M06/M07」）。
    不读它，`use crate::event;` 就会被判成"宿主文件没有被任何模块号登记"——
    那是**判据自己造出来的假告警**，不是项目缺陷。归属按行内出现的第一个模块号取。
    """
    out = {}
    sec = re.search(r"(?ms)^###\s*§2\.1(.*?)(?=^###\s|^##\s|\Z)", text)
    if not sec:
        return out
    for line in sec.group(1).split("\n"):
        m = SHARED_ROW_RE.match(line)
        if not m:
            continue
        path = m.group(1).strip()
        if not path.startswith("src/"):
            continue
        ids = M_RE.findall(m.group(2))
        # ★ 2026-09-28 修：**共同模块可以不只有一个归属，也可以没有单一归属**。
        #   原来 `if ids:` ⇒ 那行里没有 `Mxx` 就整行跳过 ⇒ `src/error.rs`（登记为"横跨全部模块"）
        #   仍被判成"没有被任何模块号登记"，而它**明明已在 §2.1 登记**——
        #   那是**判据自己造出来的假告警**（登记表里写着"不占号"，工具却当它不存在）。
        #   ⇒ 无单一归属时记空串：**它是已登记的共同模块，但不作任何模块的边目标**（也不归属任何模块号）。
        out.setdefault(path, ids[0] if ids else "")
    return out


# ────────────────────────── 源码面：模块树与边 ──────────────────────────
MOD_DECL_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;")
CFG_TEST_RE = re.compile(r"^\s*#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]")
#: `use` 的四种形态都收：
#:  ① `use crate::gate::Decision;`        ② `use world_core::readmodel::State;`
#:  ③ `use gate::{Decision, Policy};`（**根级裸名**，2018 之后合法：`src/lib.rs:23-26` 就是这么写的）
#:  ④ `use super::*;` / `use self::x;`（不是兄弟模块面，解析时丢弃）
#: `kind` 为 None ⇔ 根级裸名 ⇒ 只有首段**真在 `crate::` 作用域里**（见 `crate_mod_names`）才算边。
IMPORT_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?use\s+"
    r"(?:(?P<kind>crate|world_core|super|self)\s*::|::\s*)?"
    r"(?P<rest>[A-Za-z_][A-Za-z0-9_:{}, \t]*)"
)
#: **行内全限定路径**（`use` 以外的地方写的 `crate::A…` / `world_core::A…`）：
#:   `crate::guard::assert_not_other_writable(dir, "通道目录")?;`（`src/channel.rs:184`）
#:   `let client = world_core::carrier::kernel::KernelClient::new(sock);`（`src/main.rs:877`）
#: 为什么要它：Rust 允许不用 `use` 直接写全路径，而 A-4 判的是**真实依赖面**——
#: 不抽它，`src/ontology.rs:134`／`src/channel.rs:184` 两条**真的**跨模块调用就不产边，
#: 于是登记表里 `M01 → M05`、`M09 → M05` 两条**真声明**被判成"声明了但代码里没有"。
#: 抓到的是**整条路径**（`carrier::recover::orphans`），再由 `_mod_candidate` 取模块树里最长的真模块前缀。
INLINE_PATH_RE = re.compile(
    r"\b(?:crate|world_core)\s*::\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*::\s*[A-Za-z_][A-Za-z0-9_]*)*)")
#: 整行注释（`//`、`///`、`//!`）：里面的 `crate::…` 是**文档链接**，不是依赖。
COMMENT_LINE_RE = re.compile(r"^\s*//")
#: `#[test]` 行（含 `#[tokio::test]`、带参数形态；与 `#[cfg(unix)]` 等其它属性无关）。
TEST_ATTR_RE = re.compile(r"^\s*#\s*\[\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*::\s*)*test\s*[\]\(]")
#: 根级条目声明（`pub struct World {` / `pub enum X` / `pub trait T` / `pub fn f` / `pub type A`）。
ROOT_ITEM_RE = re.compile(
    r"^\s*pub\s+(?:struct|enum|trait|fn|type|const|static|union)\s+([A-Za-z_][A-Za-z0-9_]*)")
#: `fn name(` 行（测试函数名判据）。
FN_RE = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*[(<]")


def walk_rs(root):
    """递归列出 `root` 下的 `.rs`（排序，跳过 target/.git）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in (".git", "target", "node_modules", "__pycache__")
        )
        for f in sorted(filenames):
            if f.endswith(".rs"):
                out.append(os.path.join(dirpath, f))
    return out


def crate_mod_names(text, extra=()):
    """`crate::` 的作用域里有哪些名字：根模块的 `mod` 声明 ＋ 根文件里 `use` 的首段。

    为什么把 `use` 首段也算进来：`src/lib.rs` 里 `use gate::{Decision, Policy};`（`src/lib.rs:23`）
    与 `main.rs` 里 `use world_core::World;` 的 `World`（定义在 `src/lib.rs`）都不是
    `pub mod` 声明出来的名字，却是真实的 `crate::` 名字；只认 `mod` 声明会把这些
    "根级再导出"漏成"解析不到"。
    """
    names = dict(extra)
    for i, line in enumerate(text.split("\n"), 1):
        m = MOD_DECL_RE.match(line)
        if m:
            names.setdefault(m.group(1), i)
            continue
        # 根级**条目**声明：`use world_core::World;` 的 `World` 来自 `src/lib.rs:59`
        # `pub struct World {`——它不是 mod、也不在任何 use 里，只认前两者会漏成"解析不到"。
        m = ROOT_ITEM_RE.match(line)
        if m:
            names.setdefault(m.group(1), i)
            continue
        m = IMPORT_RE.match(line)
        if m and m.group("kind") == "crate":
            seg = re.split(r"[:{]", m.group("rest"), 1)[0].strip()
            if seg:
                names.setdefault(seg, i)
    return names


def build_module_tree(wc, files):
    """建模块树：{模块路径（`a::b`）: 承载它的 .rs 文件}；返回 (tree, test_only_mods)。

    · 根：`src/lib.rs`（库根）与 `src/main.rs`（bin 根）都挂在 `crate::` 上。
    · `src/<dir>/mod.rs` ⇒ 模块路径为 `<dir>`；其内的 `pub mod Y;` ⇒ `<dir>::Y`。
    · `#[cfg(test)]` 之后紧跟的 `mod X;` 记进 `test_only_mods`（该模块只在测试编译单元里存在）。
    """
    tree, test_only = {}, set()
    by_rel = {rel(wc, f): f for f in files}

    def visit(relpath, modpath):
        f = os.path.join(wc, relpath)
        tree[modpath] = f
        text = read_text(f)
        d = os.path.dirname(relpath).replace("\\", "/")
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            m = MOD_DECL_RE.match(line)
            if not m:
                continue
            child = m.group(1)
            child_rel = "%s/%s.rs" % (d, child) if d else "src/%s.rs" % child
            if child_rel not in by_rel:
                if "%s/mod.rs" % child_rel[: -len(".rs")] in by_rel:
                    child_rel = "%s/mod.rs" % child_rel[: -len(".rs")]
                else:
                    continue
            prev = lines[i - 2] if i >= 2 else ""
            if CFG_TEST_RE.match(prev or ""):
                test_only.add(child_rel)
                continue
            visit(child_rel, "%s::%s" % (modpath, child) if modpath else child)

    for root in ("src/lib.rs", "src/main.rs"):
        if root in by_rel:
            visit(root, "")
    return tree, test_only


def _in_string(line, idx):
    """`idx` 这个位置是不是落在**字符串字面量**里（数它前面有多少个未转义的双引号）。

    够用的粗判：路径不会跨行，`r"…"` 也照数引号。为什么需要它：
    `let s = "crate::readmodel::State";` 是**数据**，把它当依赖就凭空多一条边。
    """
    n, i = 0, 0
    while i < idx:
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            n += 1
        i += 1
    return n % 2 == 1


def _longest_module(tree, path):
    """把 `a::b::c` 解析成模块树里**最长的那个真模块前缀**（都没有则返回 `""`）。

    为什么要"最长"而不是"首个路径段"：Rust 的路径可以一路写到**条目名**
    （`world_core::project::language::parse`：模块是 `project::language`，`parse` 是函数）。
    取最长真模块前缀 ⇒ ① 不会把函数/类型名当成模块（它们不在模块树里）；
    ② `a::b::c` 与 `a::b` 得到**同一条**边；③ `use world_core::project::{self, language, visual};`
    里花括号的每一项都能各自落到**它自己的**模块上（⑦ 的判据面）。
    """
    parts = [p for p in path.split("::") if p]
    for k in range(len(parts), 0, -1):
        cand = "::".join(parts[:k])
        if cand in tree:
            return cand
    return ""


def _mod_candidate(tree, path):
    """路径 → 产边候选名：**树里最长的真模块前缀**优先，否则退回**首个路径段**。

    退回首段是为了根级名字（`use world_core::World;` 的 `World` 是 `src/lib.rs` 的条目、
    不是模块树里的模块）——它由 `seg_owner` 的第 ②③ 级落点接住。
    """
    hit = _longest_module(tree, path)
    if hit:
        return hit
    return path.split("::")[0].strip()


def _brace_members(rest):
    """`use` 路径原文里花括号列表的成员名（去 `as` 别名、去空白；`self` 原样保留由调用方丢弃）。

    只展开**一层**花括号：`use a::b::{c, d as e};` ⇒ `["c", "d"]`。
    嵌套形态（`use a::{b::{c, d}, e};`）**不展开内层**——本仓实测 0 处；
    遇到时内层名字解析不到模块 ⇒ 不产边（保守方向：宁可少一条，也不少错一条）。
    """
    m = re.search(r"\{(.*)", rest or "")
    if not m:
        return []
    body = m.group(1).split("}")[0]
    out = []
    for item in body.split(","):
        item = item.strip()
        if item:
            out.append(re.split(r"\s+as\s+", item)[0].strip())
    return out


def file_use_edges(path, text, tree, test_only, crate_names):
    """单个 .rs 文件 → (生产边集, 测试边集)，元素为**模块名**（`gate` / `World` / `project::language`…）。

    · 行级状态机：`#[cfg(test)]` 之后紧跟的 `mod NAME {` 起始的整块计入"测试边"，
      其余计入"生产边"（`WC-MODREG-001` §4.2 的划界口径：测试内的 use 不是发布产物里的边）。
    · 行首 `use` 与**行内全限定路径**（`crate::guard::f(…)`）**两处都抽**——口径与理由见文件头；
      整行注释与字符串字面量里的路径**不算**（那是文档链接与数据，不是依赖）。
    · `use a::b::{self, c};` 里**花括号的每一项都解析**：`c` 落到 `a::b::c`（⑦ 的判据面）。
    · 根级裸名（`use gate::{…};`）在 `crate_names` 里查到名字才算边；查不到即丢弃
      （不会把 `use serde_json::…` 误算成兄弟模块边）。
    """
    prod, tests = set(), set()
    in_test = 0
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        if in_test and re.match(r"^\s*\}\s*$", line):
            in_test -= 1
            continue
        if CFG_TEST_RE.match(line):
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r"^\s*(?:pub\s+)?mod\s+\w+\s*\{", lines[j]):
                in_test += 1
            continue
        if COMMENT_LINE_RE.match(line):
            continue                                  # 注释行（`///`／`//!`）里的路径是文档链接
        dest = tests if in_test else prod
        m = IMPORT_RE.match(line)
        if m:
            kind, rest = m.group("kind"), (m.group("rest") or "")
            if kind not in ("super", "self"):         # 模块内部，不是"兄弟模块"面
                head = re.split(r"[{,\s]", rest, 1)[0].strip().rstrip(":")
                mod = _mod_candidate(tree, head)
                if mod and (kind is not None or _longest_module(tree, head) or mod in crate_names):
                    dest.add(mod)
                    for mem in _brace_members(rest):
                        if mem in ("", "self", "*"):
                            continue
                        deep = _longest_module(tree, "%s::%s" % (head, mem))
                        if deep and deep != mod:
                            dest.add(deep)            # 花括号里的**模块**项：各归各的模块
                # 根级裸名但不在 crate 作用域里 ⇒ 外部 crate，丢弃
        for im in INLINE_PATH_RE.finditer(line):
            if _in_string(line, im.start()):
                continue
            cand = _mod_candidate(tree, re.sub(r"\s+", "", im.group(1)))
            if cand:
                dest.add(cand)
    return prod, tests


def index_source(wc):
    """把 `src/**/*.rs` 过一遍，返回一份"源码面"字典。"""
    src = os.path.join(wc, SRC_REL)
    files = walk_rs(src)
    tree, test_only = build_module_tree(wc, files)
    # `crate::` 作用域的名字：根文件的 mod 声明与 use 首段 ＋ **树上每个路径的首段**。
    # 前者覆盖"根级再导出"（`World`），后者覆盖"根级裸名 use"（`use readmodel::State;`，
    # 2018 之后它与 `use crate::readmodel::State;` 同义，`src/lib.rs:23-26` 就是裸名写法）。
    crate_names = {}
    for root_rel in ("src/lib.rs", "src/main.rs"):
        p = os.path.join(wc, root_rel)
        if os.path.isfile(p):
            crate_names = crate_mod_names(read_text(p), crate_names)
    for modpath in tree:
        first = modpath.split("::")[0]
        if first:
            crate_names.setdefault(first, 0)
    # 根级再导出的**承载文件**：`src/lib.rs` 里 `use crate::gate::{…};` ⇒ `Decision` 等
    # 根级名字的宿主是 lib.rs。`use world_core::World;` 因此能落到 M04，而不是"解析不到"。
    root_exports, root_items = {}, {}
    for root_rel in ("src/lib.rs", "src/main.rs"):
        p = os.path.join(wc, root_rel)
        if not os.path.isfile(p):
            continue
        for line in read_text(p).split("\n"):
            m = ROOT_ITEM_RE.match(line)             # `pub struct World {`（`src/lib.rs:59`）
            if m:
                root_items.setdefault(m.group(1), p)
            m = IMPORT_RE.match(line)
            if m and m.group("kind") == "crate":
                seg = re.split(r"[:{]", m.group("rest") or "", 1)[0].strip()
                if seg:
                    root_exports.setdefault(seg, p)
    info = {}
    for f in files:
        text = read_text(f)
        prod, tests = file_use_edges(f, text, tree, test_only, crate_names)
        info[rel(wc, f)] = {"prod_segs": prod, "test_segs": tests, "text": text}
    return {"files": files, "tree": tree, "test_only": test_only, "info": info,
            "crate_names": crate_names, "root_exports": root_exports, "root_items": root_items}


def owning_module(wc, rows, f):
    """某 .rs 文件登记在哪个模块号下（按登记表「源码路径」列的字面前缀归属）。

    `src/carrier/` 这类**目录**路径按前缀归属（`src/carrier/run.rs` 属 `M10`）；
    `src/ontology.rs` 这类**文件**路径要求逐字相等。
    """
    r = rel(wc, f)
    hits = []
    for mid, row in rows.items():
        for sp in row["src_all"]:
            if sp.endswith("/"):
                if r.startswith(sp):
                    hits.append(mid)
                    break
            elif r == sp:
                hits.append(mid)
                break
    if not hits:
        return None, 0
    return sorted(hits)[0], len(hits)


def seg_owner(wc, rows, source, seg, shared=None):
    """`crate::<seg>` / 根级裸名 `<seg>::` 解析到哪个模块号（模块树 → 宿主文件 → 登记行）。

    三级落点（都写死，不做"看起来像"）：
      ① 模块树里的 `<seg>`（`src/<seg>.rs` / `src/<dir>/mod.rs` 的 `pub mod` 声明；
         多段路径 `project::language` 也走这一级——`seg` 由 `_mod_candidate` 取最长真模块前缀）；
      ② 根级再导出的承载文件（`src/lib.rs` 里 `use crate::<seg>::…;`）；
      ③ 同名文件 `src/<seg>.rs`。
    宿主文件 → 模块号：查登记表「源码路径」列；落在 `§2.1` 声明的**共同模块**上则**跳过**（见下）。

    返回 `(模块号, 告警, 跳过原因)`（后两者互斥、都可能为空串）：
      · `模块号 is None` ＋ `告警` 非空 ⇔ **解析不到 / 没登记**（调用方按"依赖抽取告警"报，不静默）；
      · `模块号 is None` ＋ `跳过原因` 非空 ⇔ 解析到了**共同模块**（`§2.1` 显式登记"不占号"）——
        按口径**不作依赖边目标**（调用方同样逐条报出来，不静默）。

    **为什么共同模块不作边目标**（口径由执行者裁定，机核工区照做）：
    A-4 判的是**模块号之间**的单向 DAG；一个显式声明"不占号"的文件按定义就落在这个映射之外。
    把它当边目标时**归属是任意的**——`src/project/mod.rs` 横跨 M06/M07，工具挑 M06，
    于是 `M07` 里一句 `use crate::project::{…}` 被记成"依赖 M06"（**凭空一条边**）；
    `src/event.rs`（属 M01 的机制面）同理把 `src/gate.rs:581` 记成"依赖 M01"。
    这两条假边正是 2026-09-28 那两条新 offender 的**唯一**来源。

    **不做"模块内部引用"的过滤**：那属于调用方（`build_edges` 按导入文件的归属模块过滤）。
    在这里过滤会让"从测试文件里解析兄弟模块"（没有导入方模块号可比）一律返回 None——
    那正是 A-2「测试」件判据被静默判红的根因。
    """
    shared = shared or {}
    path = None
    for modpath, f in source["tree"].items():
        if modpath == seg:
            path = f
            break
    if path is None and "::" not in seg:
        path = source.get("root_items", {}).get(seg)   # ② 根级条目（`pub struct World`）
    if path is None and "::" not in seg:
        path = source.get("root_exports", {}).get(seg)
    if path is None and "::" not in seg:
        cand = os.path.join(wc, SRC_REL, seg + ".rs")
        if os.path.isfile(cand):
            path = cand
    if path is None:
        return None, "解析不到 `%s` 的宿主文件（模块树里没有它）" % seg, ""
    mid, n = owning_module(wc, rows, path)
    if mid is None:
        # `WC-MODREG-001` §2.1 明示的共同模块（"不占号"）：**不作边目标**（理由见 docstring）
        if rel(wc, path) in shared:
            _owner = shared[rel(wc, path)]
            return None, "", ("共同模块 `%s`（§2.1 登记「不占号」；%s）不作边目标"
                              % (rel(wc, path),
                                 ("名义归属 %s" % _owner) if _owner else "**无单一归属**（横跨全部模块）"))
        return None, "`%s` 的宿主文件 %s 没有被任何模块号登记" % (seg, rel(wc, path)), ""
    if n > 1:
        return mid, "`%s` 的宿主文件 %s 同时命中多个登记行" % (seg, rel(wc, path)), ""
    return mid, "", ""


def build_edges(wc, rows, source, shared=None):
    """真实 import 边：{模块号: 出边集}（生产面）；返回 (生产边, 测试边, 解析告警, 按口径跳过的边)。"""
    prod_edges = {mid: set() for mid in rows}
    test_edges = {mid: set() for mid in rows}
    warn, skipped = [], []
    for r, d in sorted(source["info"].items()):
        owner, n = owning_module(wc, rows, os.path.join(wc, r))
        if owner is None:
            continue                                  # 未登记文件（含共同模块自身）：A-2 的覆盖面单独报
        for bucket, segs in (("prod", d["prod_segs"]), ("test", d["test_segs"])):
            for seg in sorted(segs):
                tgt, why, skip = seg_owner(wc, rows, source, seg, shared)
                if tgt is None:
                    if why:
                        warn.append("%s: `%s`：%s" % (r, seg, why))
                    elif skip:
                        # **不静默**：跳过要能数得出来、指得出是哪一行（与"依赖抽取告警"同一风格）
                        skipped.append("%s: `%s`：%s" % (r, seg, skip))
                    continue
                if tgt == owner:
                    continue                          # 模块**内部**引用，不构成跨模块边
                (prod_edges if bucket == "prod" else test_edges)[owner].add(tgt)
    return prod_edges, test_edges, warn, sorted(set(skipped))


# ────────────────────────── 环检测 ──────────────────────────
def _sccs(nodes, adj):
    """Tarjan 强连通分量（**迭代版**，不吃递归深度），返回各分量（分量内节点升序、分量间按首节点升序）。

    为什么要 SCC：Kahn 排不完时剩下的节点＝**环上的节点 ∪ 环的下游节点**。
    直接把这堆节点当"环上模块"报，是**多报**——实测本仓真环只有 `M04 ↔ M09`，
    而剩余节点是 9 个（`M01,M02,M03,M04,M05,M06,M08,M09,M10`），读者会读成"这 9 个互相成环"。
    """
    nodeset = set(nodes)
    index, low, on_stack, stack, out = {}, {}, set(), [], []
    counter = 0
    for root in nodes:
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(sorted(v for v in adj.get(root, ()) if v in nodeset)))]
        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(sorted(x for x in adj.get(w, ()) if x in nodeset))))
                    advanced = True
                    break
                if w in on_stack:
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                out.append(sorted(comp))
    return sorted(out)


def _walk_cycle(comp, adj):
    """在一个强连通分量里走出一条环（自 `comp[0]` 起，沿字典序首个后继）。

    为什么走得出来：分量大小 ≥2（或自环）时，**分量内每个节点在分量内的出度 ≥1**，
    于是"沿后继一直走"必然回到走过的点；回到哪一点，就从哪一点截出环。
    走不到后继时返回 `None`（理论上不可达）——守住"没验过的不许叫环"。
    """
    inset = set(comp)
    path, pos, cur = [], {}, comp[0]
    while cur not in pos:
        pos[cur] = len(path)
        path.append(cur)
        nxt = [v for v in sorted(adj.get(cur, ())) if v in inset]
        if not nxt:
            return None
        cur = nxt[0]
    return path[pos[cur]:] + [cur]


def find_cycles(nodes, edges, label_edges=None):
    """Kahn 拓扑排序；排不完 ⇒ 有环。返回 `(是否有环, [环路径…]（或剩余节点集合）, 是否每条都逐段验过)`。

    ★ 2026-09-28 修（评审席·乙 发现）：旧实现在"走不下去"时 `break`，
    于是 `path=[cur]` 会退化成 **自环**（打印成 `M01 → M01`，而图上根本没有这条边）。
    此后改为"只在路径首尾确实相接时才算环路径，否则退化为环上节点集合"。

    ★ 本轮修（机核工区）：上面那条退化**本身仍是错的**，两处：
      ① **只报一条**环：图里同时有多条环时，读者只看到碰巧先走到的那条
         （实测：工作区里 `M02→M05→M10→M02` 与 `M04→M09→M04` 两条真环同时存在，
         旧输出只打印前者 ⇒「源码 import 环」这句话**漏了 `M04 ↔ M09`**）；
      ② **退化时报的"节点集合"含环外节点**（环的下游全在内），读者会读成"这些模块互相成环"。
    现在改为：**先求强连通分量，每个真环各走出一条环路径，逐段验证后全部打印**；
    一条都验不出来时才退回"剩余节点集合"并标注"路径未定"。
    """
    nodes = sorted(nodes)
    indeg = {n: 0 for n in nodes}
    adj = {n: set() for n in nodes}
    for u in nodes:
        for v in edges.get(u, ()):
            if v in indeg and v not in adj[u]:
                adj[u].add(v)
                indeg[v] += 1
    queue = [n for n in nodes if indeg[n] == 0]
    seen = 0
    while queue:
        u = queue.pop()
        seen += 1
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if seen == len(nodes):
        return False, [], False
    left = [n for n in nodes if indeg[n] > 0]
    cycles = []
    for comp in _sccs(left, adj):
        if len(comp) == 1 and comp[0] not in adj.get(comp[0], ()):
            continue                                  # 单点且无自环 ⇒ 只是环的下游，不在环上
        cyc = _walk_cycle(comp, adj)
        # ★ 验一遍：每段都真有边、且收尾相接——**没验过的不许叫"环"**
        if cyc and len(cyc) >= 2 and all(cyc[i + 1] in adj.get(cyc[i], ()) for i in range(len(cyc) - 1)):
            cycles.append(cyc)
    if cycles:
        return True, cycles, True
    return True, left, False          # 找不到可打印的真环 ⇒ 只报节点集合，并标注"路径未定"


def _find_cycles_old(nodes, edges):
    """Kahn 拓扑排序；排不完 ⇒ 有环（报出环上模块号）。返回 (是否有环, 环上节点列表)。"""
    nodes = sorted(nodes)
    indeg = {n: 0 for n in nodes}
    adj = {n: set() for n in nodes}
    for u in nodes:
        for v in edges.get(u, ()):
            if v in indeg and v not in adj[u]:
                adj[u].add(v)
                indeg[v] += 1
    queue = [n for n in nodes if indeg[n] == 0]
    seen = 0
    while queue:
        u = queue.pop()
        seen += 1
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if seen == len(nodes):
        return False, []
    left = [n for n in nodes if indeg[n] > 0]
    # 从剩余节点里走出一条真环，便于人看（自环也覆盖）
    path, cur = [], left[0]
    while cur not in path:
        path.append(cur)
        nxt = [v for v in sorted(adj[cur]) if indeg[v] > 0]
        if not nxt:
            break
        cur = nxt[0]
    if cur in path:
        path = path[path.index(cur):] + [cur]
    return True, path


# ────────────────────────── 测试锚点与契约条目 ──────────────────────────
ANCHOR_RE = re.compile(r"`([^`]+?)::([A-Za-z_][A-Za-z0-9_]*)`")
REQ_RE = re.compile(r"^###\s+Requirement:\s*(.+?)\s*$")


def _test_fns(text):
    """`tests/*.rs` → [(fn名, 函数体起始行号, 函数体文本)]，只取 `#[test]` 标注的函数。

    `#[test]` 与 `fn` 之间允许夹 `#[cfg(unix)]` 等属性行；函数体按**大括号配平**截取
    （不靠缩进猜，故多行字符串里的括号会被计入——这是保守方向：宁可多截一点，
    也不要把后续用例误算进前一个用例）。
    """
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        m = FN_RE.match(line)
        if not m:
            continue
        j = i - 1
        is_test = False
        while j >= 0 and (lines[j].strip().startswith("#[") or not lines[j].strip()):
            if TEST_ATTR_RE.match(lines[j]):
                is_test = True
                break
            j -= 1
        if not is_test:
            continue
        depth, buf, started = 0, [], False
        for k in range(i, len(lines)):
            cur = lines[k]
            buf.append(cur)
            depth += cur.count("{") - cur.count("}")
            if "{" in cur:
                started = True
            if started and depth <= 0:
                break
        out.append((m.group(1), i + 1, "\n".join(buf)))
    return out


def all_test_tokens(wc):
    """`tests/**/*.rs` 里**真实存在的** `#[test]` 函数锚点集合（`tests/x.rs::fn`）。

    用途：规格证据行只算"有效证据"——它指向的用例必须真的在 `tests/` 里存在
    （这条口径与 `tools/spec_bridge.py` 判据②「证据存在性」同源）。
    """
    real = set()
    tests_dir = os.path.join(wc, TESTS_REL)
    if not os.path.isdir(tests_dir):
        return real
    for f in walk_rs(tests_dir):
        r = rel(wc, f)
        for fn, _line, _body in _test_fns(read_text(f)):
            real.add("%s::%s" % (r, fn))
    return real


def module_tokens(rows, body):
    """函数体里出现了哪些模块（按登记源码路径的**文件名词干 / 目录名**标识符指认）。

    可指认的名字：`src/readmodel.rs` ⇒ `readmodel`；`src/project/language.rs` ⇒ `language`；
    `src/carrier/` ⇒ `carrier`；并补上 `main`（程序入口）与 `lib`（运行时装配）。
    用词边界匹配，避免 `readmodel` 命中 `readmodel_x` 这类别的标识符。
    """
    hits = set()
    for mid, row in rows.items():
        names = set()
        for sp in row["src_all"]:
            if sp.endswith("/"):
                names.add(sp.rstrip("/").split("/")[-1])
            elif os.path.basename(sp) == "mod.rs":
                # ★ `src/X/mod.rs` ⇒ 标识符取**目录名** `X`。
                # 取文件名会得到 `mod`（Rust 关键字，认不出任何用例）⇒ 该模块的测试锚点**塌掉而判据仍绿**。
                # 实测（2026-10-07，仓外副本）：`src/ledger.rs` → `src/ledger/mod.rs` 后
                # `anchors_total` 303→195、`M02` 锚点 111→3，而判据③ 仍报 4/0。
                parent = os.path.dirname(sp).rstrip("/").split("/")[-1]
                if parent:
                    names.add(parent)
            else:
                names.add(os.path.basename(sp)[: -len(".rs")])
        # 模块名里的关键段（`src/project/language.rs` ⇒ `language` 已在上列；`src/lib.rs` ⇒ `lib`）
        for name in names:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", body):
                hits.add(mid)
                break
    return hits


def index_specs(wc, base=None):
    """`ninedim/01-意图环/04-规格/**/spec.md` → 证据锚点 {`tests/x.rs::fn`: [(spec_rel, line, 需求标题)]}。

    `WC-ATOM-001` §三 把「契约文档」钉在「规格条目（一条 Requirement）」与
    「`WC-IC-M*` 模块接口契约」两处，本索引就是前者的判定面。
    `base` = 仓库根（默认 world-core 的上一级）；自证沙盒会显式传入自己的根。
    """
    idx = {}
    base = base or os.path.dirname(os.path.abspath(wc.rstrip("\\/")))
    specs_root = os.path.join(base, SPECS_REL)
    if not os.path.isdir(specs_root):
        return idx
    for dirpath, dirnames, filenames in os.walk(specs_root):
        dirnames[:] = sorted(dirnames)
        for fn in sorted(filenames):
            if fn != "spec.md":
                continue
            p = os.path.join(dirpath, fn)
            cur = ""
            for i, line in enumerate(read_text(p).split("\n"), 1):
                m = REQ_RE.match(line)
                if m:
                    cur = m.group(1)
                if "证据" not in line:
                    continue
                for tok, fnn in ANCHOR_RE.findall(line):
                    key = "%s::%s" % (tok.strip(), fnn)
                    idx.setdefault(key, []).append((rel(base, p), i, cur))
    return idx


def test_anchor(wc, rows, source, spec_idx, real_tokens=None):
    """模块号 → 测试锚点列表 [{file, fn, line, module, used_by}]。

    指认规则（写死，不做"看起来像"）：
      ① **函数体级**：`tests/*.rs` 里每个 `#[test]` 函数的**函数体**内出现 `world_core::<seg>`、
         或出现该模块登记源码路径的**文件名/目录名标识符**（`readmodel` / `language` / `visual` /
         `carrier` …）⇒ 该用例算这个模块的。
         `#[test]` 的函数体里一般没有 `use`，故**必须**按标识符指认；只按"文件级 use"指认
         会把同一文件里所有用例判给所有被 import 的模块（那种指认查不出"某模块一个用例都没有"）。
      ② **CLI 端到端**：函数体里出现 `Command` / `env!("CARGO_BIN_EXE_` ⇒ 它是打二进制的端到端用例，
         归 `src/main.rs` 的宿主模块（程序入口）。这不是"猜"：这些用例的全部证据都指向产物入口。
    """
    out = {mid: [] for mid in rows}
    tests_dir = os.path.join(wc, TESTS_REL)
    if not os.path.isdir(tests_dir):
        return out
    main_owner = None
    for mid, row in rows.items():
        if any(sf.endswith("src/main.rs") for sf in row["src_files"]):
            main_owner = mid
    for f in walk_rs(tests_dir):
        r = rel(wc, f)
        fns = _test_fns(read_text(f))
        for fn, line_no, body in fns:
            owners = module_tokens(rows, body)
            if main_owner and ("Command" in body or 'env!("CARGO_BIN_EXE_' in body):
                owners.add(main_owner)
            for mid in sorted(owners):
                out[mid].append({"file": r, "fn": fn, "line": line_no, "used_by": []})
    for mid, items in out.items():
        for it in items:
            tok = "%s::%s" % (it["file"], it["fn"])
            # 只有**真实存在**的用例才算有效证据（证据行指向不存在的函数 ⇒ 不算契约落点）
            if real_tokens is not None and tok not in real_tokens:
                continue
            it["used_by"] = [u for u in spec_idx.get(tok, [])]
    for mid in out:
        out[mid].sort(key=lambda x: (x["file"], x["line"]))
    return out


# ────────────────────────── 判据④：原子档栏位（A-3 的模块级落点） ──────────────────────────
def j_a0_atom_fields(wc, rows, reg_path, anchors=None, real_tokens=None):
    """④ A-3 契约字段齐：登记表每一行的**原子档栏位**都在，且取值**回源为真**。

    「在」＝按表头认到了这一列（见 `_atom_col_map`）；「真」＝逐项回源核对：
      · `契约锚点` 里的每个 `IF-0xx` 必须在 `WC-IC-001` 里真出现（数字不得凭空写）；
      · `四件同夹证据` 里的每个 `tests/…::fn` 必须是真存在的 `#[test]` 函数，且**至少一个**；
      · `intent` 必须与「职责（一句话）」列**逐字相同**（同一件事两个说法 ⇒ 报红）。

    **本判据不判的事（如实说）**：`side_effects` 的**内容对不对**机器读不出 ⇒ **那一档只有人核**。
    本判据只判它"填了"。凡把它写成"已机核"的地方都是假证。
    """
    bad = []
    if not rows:
        return ["%s —— §2 模块登记表取不到行，原子档栏位**无从判定**" % rel(wc, reg_path)]
    anchors = anchors or {}
    real_tokens = real_tokens or set()
    book = os.path.join(wc, IC_BOOK_REL)
    book_text = read_text(book) if os.path.isfile(book) else ""
    # `WC-IC-001` 里**真出现**的接口号（回源面；为空即整套锚点判据无判定面）
    ic_ids = set(re.findall(r"IF-\d{3}", book_text))
    for mid, row in sorted(rows.items()):
        loc = "%s:%d" % (rel(wc, reg_path), row["line"])
        atom = row.get("atom") or {}

        def cell(key):
            return norm_cell(atom.get(key, ""))

        def miss(label, why):
            bad.append("%s —— %s 的原子档栏位 `%s` %s" % (loc, mid, label, why))

        # ① 六列都在（表头认得到）
        if not row.get("atom_cols_seen"):
            bad.append("%s —— %s 的**原子档栏位整组缺失**：§2 表的表头里一个原子列都认不到"
                       "（表头被改名/被删/换成了别的表）——不得因取不到而静默通过" % (loc, mid))
            continue
        for key, (label, _aliases) in ATOM_FIELDS.items():
            if key not in atom:
                miss(label, "**整列不存在**（表头里没有这一栏）——A-3 要求它必写")
        if any(k not in atom for k in ATOM_FIELDS):
            continue

        # ② intent：非占位／≤30 字／无并列两事／与「职责」列逐字相同
        val = cell("a_intent")
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_intent"][0], "取值=%r，属占位符/空" % val)
        else:
            n = visual_len(val)
            if n > INTENT_MAX_CHARS:
                miss(ATOM_FIELDS["a_intent"][0], "不是一句话：%d 字 > 上限 %d 字；逐字=%r"
                     % (n, INTENT_MAX_CHARS, val))
            hits = [mk for mk in PARALLEL_MARKERS if mk in val]
            if hits:
                miss(ATOM_FIELDS["a_intent"][0], "出现**并列两事**（连接词 %s）⇒ 拆；逐字=%r"
                     % ("/".join("`%s`" % h for h in hits), val))
            # ⚠️ 比较的两边必须**同口径**：`row["intent"]` 是剥过强调与反引号的，
            #    故这边也走 `norm_cell`。踩过的坑：拿**原样格**去比 ⇒ 格里凡是带
            #    `**` 强调的都被判"不一致"——**误红**（判据比事实更严，同"判据不许取第一处字样"）。
            if norm_cell(val) != row["intent"]:
                miss(ATOM_FIELDS["a_intent"][0],
                     "与「职责（一句话）」列**不一致**（两处=%r / %r）：同一件事只能有一个说法"
                     "（那一列就是 A-1 的 `intent`，见判据①）" % (norm_cell(val), row["intent"]))

        # ③ deps 机核：非空且点名了判它的工具
        val = cell("a_deps")
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_deps"][0], "取值=%r，属占位符/空" % val)
        elif ATOM_DEPS_TOOL not in val:
            miss(ATOM_FIELDS["a_deps"][0], "没有点名判它的工具（须含 `%s`）；逐字=%r"
                 % (ATOM_DEPS_TOOL, val))

        # ④ 契约锚点：非空，且每个 IF-0xx **在 `WC-IC-001` 里真出现**
        val = cell("a_anchor")
        ids = re.findall(r"IF-\d{3}", val)
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_anchor"][0], "取值=%r，属占位符/空" % val)
        elif not ids:
            miss(ATOM_FIELDS["a_anchor"][0], "一个 `IF-0xx` 都没有；逐字=%r" % val)
        elif not book_text:
            miss(ATOM_FIELDS["a_anchor"][0], "**判定面缺失**：`%s` 读不到 ⇒ 接口号无从回源核对"
                 % rel(wc, book))
        else:
            for iid in sorted(set(ids)):
                if iid not in ic_ids:
                    miss(ATOM_FIELDS["a_anchor"][0],
                         "写了 `%s`，但 `%s` 里**找不到这个号**（凭空写的号不算契约锚点）"
                         % (iid, rel(wc, book)))

        # ⑤ 四件同夹证据：非空，且每个 <测试夹>/…::fn **是真存在的 #[test]**
        val = cell("a_evidence")
        TESTS_TOKEN = TESTS_REL.replace(os.sep, "/")
        toks = re.findall(r"`([^`]*?%s/[^`]*?)`" % re.escape(TESTS_TOKEN), atom.get("a_evidence", "") or "")
        toks = [t.strip() for t in toks if "::" in t]
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_evidence"][0], "取值=%r，属占位符/空" % val)
        elif not toks:
            miss(ATOM_FIELDS["a_evidence"][0],
                 "没有一个 `tests/…::fn` token（A-2 的「测试」件在这一行没有落点）；逐字=%r" % val)
        elif not real_tokens:
            miss(ATOM_FIELDS["a_evidence"][0],
                 "**判定面缺失**：`%s/` 下取不到任何 `#[test]` ⇒ token 无从回源核对" % TESTS_REL)
        else:
            for t in sorted(set(toks)):
                if t not in real_tokens:
                    miss(ATOM_FIELDS["a_evidence"][0],
                         "写了 `%s`，但**这个用例不存在**（`%s/` 里没有该 `#[test]`）"
                         "——形态上等于声称存在" % (t, TESTS_REL))

        # ⑥ side_effects：非空（**只判填没填**；内容对不对机器读不出 ⇒ 只有人核，见 docstring）
        val = cell("a_side")
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_side"][0],
                 "取值=%r，属占位符/空（A-3：不写副作用＝声明「无副作用」，但不许留空）" % val)

        # ⑦ 机核读数：**必须有命令**，且点名本工具管的那一条判据。
        #   ★ 2026-09-28 收紧：原来只要求"非占位 ∧ 含 `deps == import`"，
        #     于是「以判据②（deps == import）现场读数为准」这种**指针式**填法全过——
        #     而那一格要的是**读数**（命令＋原始输出），不是"去哪看"。
        #     现取实测：`WC-MODREG-001` §2 该列 12 行逐字相同，全是这种指针 ⇒ 本收紧会让它们变红，
        #     而**它们红得对**（评审席判"那一列已经 10/10 空转"）。
        val = cell("a_machine")
        ptr = [mk for mk in MACHINE_POINTER_MARKERS if mk in val]
        if is_placeholder(val):
            miss(ATOM_FIELDS["a_machine"][0], "取值=%r，属占位符/空" % val)
        elif ptr:
            miss(ATOM_FIELDS["a_machine"][0],
                 "是**指针式**填法（命中 %s）：这一格要的是**读数**（命令＋原始输出），"
                 "不是「去哪看」；逐字=%r" % ("／".join("「%s」" % p for p in ptr), val))
        elif ATOM_MACHINE_CMD_RE.search(val) is None:
            miss(ATOM_FIELDS["a_machine"][0],
                 "**没有命令**：这一格要贴命令（反引号包起来的，或含 `python`／`cargo`／`bash`）；"
                 "逐字=%r" % val)
        elif ATOM_MACHINE_MARK not in val:
            miss(ATOM_FIELDS["a_machine"][0],
                 "没有点名本工具管的那条判据（须含 `%s`）；逐字=%r" % (ATOM_MACHINE_MARK, val))
    return bad


# ────────────────────────── 四条判据 ──────────────────────────
def j_a1_intent(wc, rows, reg_path, reg_text):
    """① A-1 单意图原子性：每个模块有且只有一句 `intent`（≤30 字），并列两事即报可疑。"""
    bad = []
    names = {}
    if not rows:
        return ["%s —— §2 模块登记表里一个 `| M0x |` 行都取不到（表被清空/格式被改/文件缺失）："
                "**空登记表不得被当作「一致」**" % rel(wc, reg_path)]
    for mid, row in sorted(rows.items()):
        loc = "%s:%d" % (rel(wc, reg_path), row["line"])
        raw, val = row["intent_raw"], row["intent"]
        if is_placeholder(val):
            bad.append("%s —— %s 的 `intent` **不是一句**（取值=%r，属占位符/空）"
                       % (loc, mid, val))
            continue
        n = visual_len(val)
        if n > INTENT_MAX_CHARS:
            bad.append("%s —— %s 的 `intent` **不是「一句话」**：%d 字 > 上限 %d 字；逐字=%r"
                       % (loc, mid, n, INTENT_MAX_CHARS, val))
        hits = [mk for mk in PARALLEL_MARKERS if mk in val]
        if hits:
            bad.append("%s —— %s 的 `intent` 出现**并列两事**（连接词 %s）：一句里塞了两件事 ⇒ 拆；逐字=%r"
                       % (loc, mid, "/".join("`%s`" % h for h in hits), val))
        key = re.sub(r"\s+", "", val)
        if key in names:
            bad.append("%s —— %s 与 %s 的 `intent` **逐字相同**（%r）：一句意图只能对一个模块，"
                       "复制即不成立" % (loc, mid, names[key], val))
        else:
            names[key] = mid
    return bad


def module_impl_files(wc, row, source):
    """某模块**落在磁盘上的实现文件**（登记表「源码路径」列 → 真实的 `.rs`，路径相对 world-core 根）。

    ★ 为什么需要它（本轮修 ⑤）：判据② 原来只看 `row["src_files"]`（列里**逐字写成 `.rs`** 的那些），
    于是 `src/carrier/` 这种**目录列法** ⇒ 列表为空 ⇒ 模块被**整条跳过**：
    声明一条都不核对，而环检测照样拿它的声明边去凑环——**"有声明、没人看"**。
    现在：目录型模块按**前缀**收它底下的 `.rs`（与 `owning_module` 同一套归属规则），
    列了 `.rs` 的按**文件存在**收；一个实现文件都没有时才跳过
    （那种情况是"尚未落成"，归 A-2「实现缺」报，不在此重复）。
    """
    out = []
    for sp in row["src_all"]:
        if sp.endswith("/"):
            for f in source["files"]:
                r = rel(wc, f)
                if r.startswith(sp):
                    out.append(r)
        elif os.path.isfile(os.path.join(wc, sp)):
            out.append(sp)
    return sorted(set(out))


def j_a4_dag_deps(wc, rows, reg_path, prod_edges, test_edges, unres, source=None, judged_out=None):
    """② A-4 依赖单向 DAG，且 `deps == import`（逐模块逐边相等）。

    **目录型模块也逐边核对**（`src/carrier/` → M10）：只要它的实现文件真的在磁盘上，
    声明集就与真实 import 集逐边比——**不再整条跳过**（跳过＝"有声明、没人看"）。
    `judged_out`（可选集合）：把**本次真的核对过**的模块号记进去。报告里的 `deps_judged`
    直接读它、**不另算一遍**——否则"报告写已核对、判据其实跳过了"这种假绿没人发现
    （实测：变异体 N1 就是靠这条漏过正控附条⑤ 的）。
    「按口径跳过的边」（共同模块不作边目标）**不进这里**：它是口径、不是缺陷——
    算成 offender 会让"红"失去意义。它由 `check()` 收进报告、正跑单独打印一段（不静默）。
    """
    bad = []
    if not rows:
        return ["%s —— §2 模块登记表取不到行，「依赖模块」列**一条边都取不到**："
                "依赖判据不得因取不到而静默通过" % rel(wc, reg_path)]
    source = source or {"files": []}
    judged = set()
    for mid, row in sorted(rows.items()):
        col = row["deps"]
        for d in sorted(col):
            if d not in rows:
                bad.append("%s:%d —— %s 的「依赖模块」列写了 %s，但登记表里没有这一行"
                           % (rel(wc, reg_path), row["line"], mid, d))
        if not module_impl_files(wc, row, source):
            continue                                   # 实现文件一个都没有：归 A-2「实现缺」，不在此重复报
        judged.add(mid)
        real = prod_edges.get(mid, set())
        missing = sorted(col - real)
        extra = sorted(real - col)
        if missing:
            bad.append("%s:%d —— %s：**声明了但代码里没有**（%s）—— 声明集 %s vs 真实 import 集 %s"
                       % (rel(wc, reg_path), row["line"], mid, ",".join(missing),
                          "{%s}" % ",".join(sorted(col)) or "{}",
                          "{%s}" % ",".join(sorted(real)) or "{}"))
        if extra:
            bad.append("%s:%d —— %s：**代码里有但没声明**（%s）—— 声明集 %s vs 真实 import 集 %s"
                       % (rel(wc, reg_path), row["line"], mid, ",".join(extra),
                          "{%s}" % ",".join(sorted(col)) or "{}",
                          "{%s}" % ",".join(sorted(real)) or "{}"))
    if judged_out is not None:
        judged_out.update(judged)
    # 无环：**分别**判「真实 import 边」与「声明边 ∪ 真实边」，并把每条边的来源标出来。
    # ★ 2026-09-28 修（评审席·乙 发现）：
    #   旧实现只报并集环，读者极易把它读成"源码循环依赖"；且它**漏报**真实源码环（`M04 ↔ M09`）。
    #   现在两条线各报一次，并给"来自未校验声明边"的边打标——那种环**改代码也消不掉**。
    # ★ 上一轮修：两条线都改成**列出全部真环**（强连通分量分解），不再"只报碰巧先走到的那一条"。
    # ★ 本轮修（⑤）：并集环里**逐条标出"未印证的声明边"**——那种环不是源码环，
    #   是"照声明算出来的设计环"，它**改代码消不掉**（要先补实现或改声明），不许混进"真环"里。
    nodes = sorted(rows)
    real_only = {mid: set(prod_edges.get(mid, set())) for mid in nodes}
    cyc_real, cycles_real, real_is_cycle = find_cycles(nodes, real_only)
    union = {mid: set(rows[mid]["deps"]) for mid in nodes}
    for mid in nodes:
        union.setdefault(mid, set())
        union[mid] |= prod_edges.get(mid, set())
    cyc, cycles_union, is_cycle = find_cycles(nodes, union)

    def _edge_src(u, v):
        """这条边从哪来：真实 import ／ 声明 ／ 两者都有。"""
        r = v in prod_edges.get(u, set())
        d = v in rows[u]["deps"]
        return "真实" if (r and not d) else ("声明" if (d and not r) else ("真实＋声明" if (r and d) else "?"))

    def _unproven(cycle):
        """这条环上**没有代码印证**的边（只在「依赖模块」列里、源码里找不到）。"""
        return [(cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1)
                if cycle[i + 1] not in prod_edges.get(cycle[i], set())]

    def _fmt(items, verified):
        """把环列表印成人能核的样子：`M04-[真实]-> M09 → M09-[真实]-> M04`（逐段标来源）。

        `verified=False` 时 `items` 是"剩余节点集合"（不是环路径）⇒ 必须**写明它不是环路径**，
        否则读者会把环的下游节点也当成环上模块。
        """
        if not items:
            return "—"
        if not verified:
            return ("节点集合 " + "、".join(items)
                    + "（⚠ 工具未能打印出逐段可验的环路径：这些是 Kahn 剩余节点，**含环的下游**，不等于环上模块）")
        out = []
        for c in items:
            seg = " → ".join("%s-[%s]-> %s" % (c[i], _edge_src(c[i], c[i + 1]), c[i + 1])
                             for i in range(len(c) - 1))
            # ★ 本轮修（⑤）：并集环**逐条标出**"没有代码印证的声明边"——
            #   这种环不是源码环（`真环` 那一行里不会出现它），它**改代码消不掉**。
            un = _unproven(c)
            if un:
                seg += ("　⚠ **这条环靠「未印证的声明边」才成立**："
                        + "、".join("%s-[声明·代码里没有]-> %s" % e for e in un)
                        + "　⇒ 先补实现或改声明；**改代码消不掉它**")
            else:
                seg += "　（环上每条边都有代码印证）"
            out.append(seg)
        return "；".join(out)

    _cyc_note = []
    if cyc_real:
        _cyc_note.append("**源码 import 环**（只看真实 import 边，工具独立判定）："
                         + _fmt(cycles_real, real_is_cycle))
    _cyc_note.append("**声明边 ∪ 真实边 的环**（设计面：照登记表算会不会成环）："
                     + _fmt(cycles_union, is_cycle))

    if cyc:
        # 环的两种口径都写进 offender（评审席·乙 的建议④）
        path_desc = " ／ ".join(_cyc_note)
        bad.append("依赖图**有环**（Kahn 拓扑排序排不完 ⇒ 至少一个强连通分量在环上）：%s —— "
                   "`WC-ATOM-001` §二 A-4 要求单向 DAG" % path_desc)
    for w in unres:
        bad.append("依赖抽取告警（不静默跳过）：%s" % w)
    # 按口径跳过的边（共同模块不作边目标）：**不静默**，但**不算 offender**——
    # 它是口径本身（`WC-MODREG-001` §2.1），不是缺陷；把它算成红会让"红"失去意义。
    # 这一项随报告一起出（正跑会单独打印一段，JSON 里有 `import_edges_skipped_shared`）。
    return bad


def j_a2_four_in_one(wc, rows, reg_path, source, anchors, spec_idx, shared=None):
    """③ A-2 每模块的实现／测试／契约三件齐备（＋未登记源码文件的覆盖面）。"""
    shared = shared or {}
    bad = []
    if not rows:
        return ["%s —— §2 模块登记表取不到行，三件齐备**无从判定**" % rel(wc, reg_path)]
    for mid, row in sorted(rows.items()):
        loc = "%s:%d" % (rel(wc, reg_path), row["line"])
        # 实现
        present = [p for p in row["src_all"] if os.path.exists(os.path.join(wc, p))]
        missing = [p for p in row["src_all"] if not os.path.exists(os.path.join(wc, p))]
        if not row["src_all"]:
            bad.append("%s —— %s **实现缺**：登记表「源码路径」列一个 `src/…` 路径都没写"
                       % (loc, mid))
        elif not present:
            if row.get("planned"):
                bad.append("%s —— %s **实现缺**：登记表列的是**计划路径** %s，磁盘上不存在"
                           "（本行已自述「尚未落成」——未落成不得当作已实现）"
                           % (loc, mid, "、".join(row["src_all"])))
            else:
                bad.append("%s —— %s **实现缺**：登记表「源码路径」列的 %s 磁盘上不存在"
                           % (loc, mid, "、".join(row["src_all"])))
        elif missing:
            bad.append("%s —— %s **实现缺**：登记表列了 %s，磁盘上不存在"
                       % (loc, mid, "、".join(missing)))
        # 测试
        if not anchors.get(mid):
            bad.append("%s —— %s **测试缺**：`%s/` 下没有任何用例能指到它"
                       "（判据＝该用例函数体内出现本模块源码路径的文件名/目录名标识符，"
                       "或 `world_core::<子模块>`；CLI 端到端用例归程序入口）"
                       % (loc, mid, TESTS_REL))
        # 契约：`WC-IC-001`（一册）里**含本模块号的标题** ⇒ 有落点
        book = os.path.join(wc, IC_BOOK_REL)
        hits = []
        if os.path.isfile(book):
            hits = [i for i, ln in enumerate(read_text(book).split("\n"), 1)
                    if ln.lstrip().startswith("#") and ("`%s`" % mid) in ln]
        cited = []
        for a in anchors.get(mid, []):
            cited.extend(a["used_by"])
        if not hits and not cited:
            bad.append("%s —— %s **契约缺**：`%s` 里没有任何含 `%s` 的标题（模块接口契约节），"
                       "也没有 `ninedim/01-意图环/04-规格/**/spec.md` 里任何 Requirement 的证据行指向它的测试锚点"
                       % (loc, mid, rel(wc, book), mid))
    # 覆盖面：src 下没有任何模块号认领、也**不在 §2.1 共同模块声明里**的 .rs
    unclaimed = []
    for f in source["files"]:
        r = rel(wc, f)
        if r in shared:
            continue                                      # §2.1 已显式声明归属
        mid, n = owning_module(wc, rows, f)
        if mid is None or n > 1:
            unclaimed.append(r)
    for r in sorted(unclaimed):
        bad.append("覆盖面 —— `src/` 下的 `%s` **没有被任何模块号认领**："
                   "它既不在登记表里，也不在「共同模块」两行内（`WC-MODREG-001` §4.3 的登记缺口口径）" % r)
    return bad


# ────────────────────────── 报告 ──────────────────────────
def check(wc, intent_column="职责", base=None):
    """跑四条判据（本文件是判据③的**执行者**，故 ①–④ 全跑）。返回 report 字典。"""
    reg_path, reg_text, rows = read_registry(wc)
    shared = read_shared_modules(reg_text)
    source = index_source(wc)
    spec_idx = index_specs(wc, base)
    real_tokens = all_test_tokens(wc)
    anchors = test_anchor(wc, rows, source, spec_idx, real_tokens)
    prod_edges, test_edges, unres, skipped = build_edges(wc, rows, source, shared)

    # 判据② 真核对了哪些模块：**由判据自己填**（`judged_out`），报告只读它——
    # 见 `j_a4_dag_deps` docstring（"报告说已核对、判据其实跳过了"是实测踩过的假绿）。
    a4_judged = set()
    judgments = [
        ("④ A-3 契约字段齐 · 原子档栏位（登记表每行的 intent／deps 机核／契约锚点／"
         "四件同夹证据／side_effects／机核读数 逐栏齐备且取值回源为真）",
         "a0_atom_fields", j_a0_atom_fields(wc, rows, reg_path, anchors, real_tokens)),
        ("① A-1 单意图原子性（每模块有且只有一句 intent，≤%d 字，无并列两事）" % INTENT_MAX_CHARS,
         "a1_intent", j_a1_intent(wc, rows, reg_path, reg_text)),
        ("② A-4 依赖单向 DAG 且 deps == import（逐模块逐边相等）",
         "a4_dag_deps", j_a4_dag_deps(wc, rows, reg_path, prod_edges, test_edges, unres, source, a4_judged)),
        ("③ A-2 四件同夹（实现／测试／契约三件齐备，＋源码文件全覆盖）",
         "a2_four_in_one", j_a2_four_in_one(wc, rows, reg_path, source, anchors, spec_idx, shared)),
    ]

    res = []
    for title, key, bad in judgments:
        res.append({"judgment": title, "key": key, "ok": not bad, "offenders": bad})

    modules = []
    for mid, row in sorted(rows.items()):
        present = [p for p in row["src_all"] if os.path.exists(os.path.join(wc, p))]
        impl = module_impl_files(wc, row, source)
        modules.append({
            "id": mid,
            "line": row["line"],
            "name": row["name"],
            "intent": row["intent"],
            "intent_chars": visual_len(row["intent"]),
            "src_declared": row["src_all"],
            "impl_present": present,
            # 实现文件（目录型模块＝目录下真实的 .rs）：空 ⇔ 判据② 不逐边核对（归 A-2「实现缺」）
            "impl_files": impl,
            "ifs": row["ifs"],
            "deps_declared": sorted(row["deps"]),
            "deps_import": sorted(prod_edges.get(mid, set())),
            # **逐边**的两侧：声明了但代码里没有／代码里有但没声明（机器可读，便于登记表订正）
            "deps_declared_unverified": sorted(row["deps"] - prod_edges.get(mid, set())),
            "deps_undeclared": sorted(prod_edges.get(mid, set()) - row["deps"]),
            "deps_judged": mid in a4_judged,
            "deps_import_tests_only": sorted(test_edges.get(mid, set()) - prod_edges.get(mid, set())),
            "test_anchors": anchors.get(mid, []),
            # 原子档栏位（判据④ 的取值面）：**逐栏原样带上**，便于"报告说齐了、其实缺一栏"被当场看见
            "atom_cells": dict(row.get("atom") or {}),
            "atom_cols_present": sorted(row.get("atom") or {}),
            "atom_cols_required": sorted(ATOM_FIELDS),
        })
    unclaimed = []
    for f in source["files"]:
        r = rel(wc, f)
        if r in shared:
            continue                                      # §2.1 已显式声明归属
        mid, n = owning_module(wc, rows, f)
        if mid is None or n > 1:
            unclaimed.append(r)
    return {
        "world_core": wc,
        "intent_column": intent_column,
        "registry": rel(wc, reg_path),
        "shared_modules": shared,
        "judgments": res,
        "modules": modules,
        "files_unclaimed": sorted(unclaimed),
        # 按口径跳过的边（共同模块不作边目标）：**逐条列出**，不静默、也不算 offender。
        "import_edges_skipped_shared": sorted(skipped),
        "test_only_modules": sorted(source["test_only"]),
        "planned_modules": sorted(m for m, r in rows.items() if not any(
            os.path.exists(os.path.join(wc, p)) for p in r["src_all"])),
        "anchors_total": sorted(
            "%s::%s" % (a["file"], a["fn"]) for m in anchors for a in anchors[m]
        ),
        "import_edges_production": {m: sorted(prod_edges.get(m, set())) for m in sorted(rows)},
        "import_edges_test_only": {m: sorted(test_edges.get(m, set())) for m in sorted(rows)},
    }


# ────────────────────────── 自证：每条判据各造一个反例 ──────────────────────────
#: 沙盒登记表的**取值行**：每行 6 格，格序与 `WC-MODREG-001` §2 表同结构：
#: 模块名 | 职责（一句话） | 源码路径 | 提供接口 | 依赖模块 | 原子档（后 6 格拼在它里面）。
#: ★ **格位由构造决定，不由手写决定**（血泪）：`read_registry` 按 `|` 切格，
#:   格位＝管道符个数。仓内既有写法**行首不带管道**（`| a | b |` ⇒ 切成 [a, b]），
#:   而手写 "| a | b | c |" 会多出首尾两个空格 ⇒ deps 落到 cells[3]、intent 落到 cells[5]，
#:   于是**每条原子判据都在读隔壁那一格**，输出看起来却像"判据抓到了错"。
#:   故这里一律用 `" | ".join(...)`，表头与体行同一函数产出。
SANDBOX_COLS = ("模块名", "职责（一句话）", "源码路径", "提供接口", "依赖模块",
                "intent（一句话）", "deps 机核", "契约锚点（WC-IC-001）",
                "四件同夹证据", "side_effects", "机核读数")


def _sandbox_row(mid, name, duty, src, iface, deps,
                 anchor, ev, side, machine=None):
    """一行的 11 格（**不含**模块号格；`read_registry` 从行首正则吃掉的正是它）。"""
    return [name, duty, src, iface, deps,
            duty,                                        # intent ＝「职责」列逐字
            "由 `module_graph.py` 判 deps == import",
            anchor, ev, side,
            # ★ 2026-09-28 改：原夹具写「以判据② 现场读数为准（判 deps == import）」——
            #   那是**指针式**填法（新规则要判红）。正控件的这一格必须是**真读数**（含命令）。
            machine or "`python scripts/verify/module_graph.py` → 判据② deps == import：通过"]


def _table_row(cells):
    """按仓内既有写法拼一行：`| ` ＋ 各格 ＋ ` |`。

    ⇒ `row.split("|")` 得到 `["", c0, c1, …, ""]`，`read_registry` 用
    `m.group(2).split("|")` 拿到的正是 `[c0, c1, …]`（**格位与逐个下标对齐**）。
    """
    return "| " + " | ".join(cells) + " |"


SANDBOX_ROWS = [
    ("**M01**", _sandbox_row("**M01**", "本体", "词表身份的唯一出处", "`src/ontology.rs`",
                             "**IF-005**", "无",
                             "`WC-IC-001` §5.1 的 `IF-005` 一节",
                             "`scripts/test/contract.rs::c02_ontology_loads`", "只读不写盘")),
    ("**M02**", _sandbox_row("**M02**", "门禁", "现在能不能做的裁决",
                             "`src/gate.rs`、`src/guard.rs`", "**IF-002**", "`M01`",
                             "`WC-IC-001` §5.2 的 `IF-002` 一节",
                             "`scripts/test/contract.rs::c01_gate_refuses`",
                             "拒绝必留痕，经 `M04` 请求")),
    ("**M03**", _sandbox_row("**M03**", "读模型", "状态由账本折叠而来", "`src/readmodel.rs`",
                             "**IF-009**", "`M02`",
                             "`WC-IC-001` §5.3 的 `IF-009` 一节",
                             "`scripts/test/contract.rs::c03_readmodel_folds`",
                             "无（生产代码不写盘）")),
    ("**M04**", _sandbox_row("**M04**", "运行时", "运行时的组装入口",
                             "`src/lib.rs`、`src/main.rs`", "**IF-008**", "`M02`、`M03`、`M05`",
                             "`WC-IC-001` §5.4 的 `IF-008` 一节",
                             "`scripts/test/cli.rs::cli01_entry_smoke`",
                             "经唯一写入口写账本")),
    ("**M05**", _sandbox_row("**M05**", "投影", "出口只有一种说法",
                             "`src/project/visual.rs`", "**IF-004**", "`M01`",
                             "`WC-IC-001` §5.5 的 `IF-004` 一节",
                             "`scripts/test/contract.rs::c04_visual_renders`",
                             "只读，不写任何东西")),
    ("**M06**", _sandbox_row("**M06**", "载体", "只执行不裁决", "`src/carrier/`",
                             "**IF-011**", "`M01`",
                             "`WC-IC-001` §5.6 的 `IF-011` 一节",
                             "`scripts/test/contract.rs::c05_carrier_runs`",
                             "动载体，对账本零写权限")),
]


def _sandbox_modreg(extra_rows=()):
    """沙盒登记表：表头与体行**同一套格位构造**（见 `_table_row` 的血泪注）。

    `extra_rows`：额外的 `(模块号, 格列表)` 行（各反例自备，见反例④b）。
    """
    lines = [_table_row(["模块号"] + list(SANDBOX_COLS)),
             "|" + "---|" * (len(SANDBOX_COLS) + 1)]
    for mid, cells in list(SANDBOX_ROWS) + list(extra_rows):
        assert len(cells) == len(SANDBOX_COLS), (
            "%s 的格数 %d ≠ 表头 %d（格位错位会让判据读隔壁那一格）"
            % (mid, len(cells), len(SANDBOX_COLS)))
        lines.append(_table_row([mid] + cells))
    return ("# WC-MODREG-001 模块清单与模块号登记表\n"
            "\n## §1 目的与范围\n\n沙盒用最小登记表，只为验证守卫会红。\n"
            "\n## §2 模块登记表\n\n" + "\n".join(lines) + "\n"
            "\n### §2.1 共同模块、未登记文件与模块号边界\n\n"
            "| 共同模块 | 占号 | 归属 | 依据 |\n|---|---|---|---|\n"
            "| `src/project/mod.rs` | **不占号** | 属 `M01` 的机制面"
            "（沙盒用；名义归属故意挑一个 M04 **没有** import 的号）"
            " | 用来验共同模块不作边目标这条口径 |\n"
            "\n## §3 模块编号规则\n\n沙盒不展开。\n")


SANDBOX_MODREG = _sandbox_modreg()


SANDBOX_SRC = {
    # ⚠️ `lib.rs` 必须写成**根级裸名 use**（`use gate::{…};`）——这是 `src/lib.rs:23-26` 的
    # 真实形态，也是抽取器最容易漏的一种；沙盒里不写它，就等于没在验这条。
    "src/lib.rs": ("pub mod carrier;\npub mod gate;\npub mod guard;\npub mod ontology;\n"
                   "pub mod project;\npub mod readmodel;\n"
                   "use gate::{Decision, Policy};\nuse readmodel::State;\n"),
    # ⚠️ `main.rs` 里 `use world_core::project::{self, visual};` 是 **⑦ 的判据面**：
    #    · 首段 `project` 指向**共同模块** `src/project/mod.rs`（§2.1 不占号）⇒ 按口径**不产边**
    #      （正控附条④：判据② 不许红，且"M04 的真实集里没有 M01"——若共同模块被当边目标，
    #      它按名义归属记成 M01，而 M04 没声明 M01 ⇒ 立刻红）；
    #    · 花括号里的 `visual` 指向**占号**模块 `M05` ⇒ **必须产边** `M04 → M05`
    #      （反例⑫：把 `visual` 从花括号里删掉 ⇒ `M04` 必报"声明了但代码里没有（M05）"）。
    "src/main.rs": ("fn main() {}\n"
                    "\n"
                    "pub fn cli() {\n"
                    "    use world_core::project::{self, visual};\n"
                    "    let _ = project::shared_helper();\n"
                    "    let _ = visual::render();\n"
                    "}\n"),
    "src/ontology.rs": "use std::collections::BTreeMap;\n",
    "src/guard.rs": "use std::path::Path;\n",
    # 共同模块本体（§2.1「不占号」）：它自己**不占任何模块号**，它的 `pub mod visual;` 让
    # `project::visual` 出现在模块树里（⑦ 要解析的正是这一层）。
    "src/project/mod.rs": ("pub mod visual;\n"
                           "\n"
                           "pub fn shared_helper() -> bool { true }\n"),
    "src/project/visual.rs": "use crate::ontology::Ontology;\n",
    # ⚠️ **目录型模块**（⑤ 的判据面）：`src/carrier/` 是**目录**，登记表里没有逐字的 `.rs`。
    #    它必须能被逐边核对：`kernel.rs` 里那句 `use crate::ontology::Ontology;` 就是 M06→M01 的
    #    唯一证据（正控附条⑤）；删掉登记表里那条声明 ⇒ 必红"代码里有但没声明"（反例⑬）；
    #    在登记表里多写一条代码里没有的 ⇒ 必红"声明了但代码里没有"（反例⑭）。
    "src/carrier/mod.rs": "pub mod kernel;\n",
    "src/carrier/kernel.rs": ("use crate::ontology::Ontology;\n"
                              "\n"
                              "pub fn run(_o: &Ontology) -> bool { true }\n"),
    # ⚠️ `gate.rs` 里指向 `ontology`(M01) 的**唯一**证据必须是**行内全限定路径**——
    #    这个文件里没有、也不许有 `use crate::ontology;`。它就是 ⑥ 的判据面：
    #    · 正控附条②：`M02 → M01` 必须**真的出现在生产边集里**，且判据② 不许红；
    #    · 反例⑨：把那一行删掉，`M02` 声明的 `M01` 立刻变"声明了但代码里没有"（必红）。
    #    只验"不红"是不够的——两边都空也会不红，所以正控附条② 连"边在不在"一起钉。
    "src/gate.rs": ("use crate::guard;\n"                       # 同模块（M02 内部 ⇒ 不产边）
                    "\n"
                    "pub fn check(p: &std::path::Path) -> bool {\n"
                    "    let _ = crate::ontology::Ontology::load(p);\n"
                    "    true\n"
                    "}\n"),
    "src/readmodel.rs": "use crate::gate::Decision;\n",
}

SANDBOX_TESTS = {
    # 函数体里**必须真的提到**被指认的模块（`module_tokens` 按标识符指认；
    # `scripts/test/cli.rs` 那条用 `Command` 走"CLI 端到端 ⇒ 归程序入口"这条规则）。
    "scripts/test/contract.rs": (
        "use world_core::gate::Policy;\n"
        "use world_core::ontology::Ontology;\n"
        "use world_core::readmodel::State;\n"
        "\n"
        "#[test]\n"
        "fn c01_gate_refuses() {\n"
        "    let _p: Option<Policy> = None;\n"
        "    let _ = world_core::gate::Decision::Allow;\n"
        "}\n"
        "\n"
        "#[test]\n"
        "fn c02_ontology_loads() {\n"
        "    let _o: Option<Ontology> = None;\n"
        "    let _ = world_core::ontology::FAMILIES;\n"
        "}\n"
        "\n"
        "#[cfg(unix)]\n"
        "#[test]\n"
        "fn c03_readmodel_folds() {\n"
        "    let _s: Option<State> = None;\n"
        "    let _ = world_core::readmodel::fold;\n"
        "}\n"
        "\n"
        "#[test]\n"
        "fn c04_visual_renders() {\n"
        "    let _ = world_core::project::visual::render();\n"
        "}\n"
        "\n"
        "#[test]\n"
        "fn c05_carrier_runs() {\n"
        "    let _ = world_core::carrier::kernel::run;\n"
        "}\n"
        "\n"
        "fn fixture_helper() {}\n"
    ),
    "scripts/test/cli.rs": (
        "use std::process::Command;\n"
        "\n"
        "#[test]\n"
        "fn cli01_entry_smoke() {\n"
        "    let _c = Command::new(env!(\"CARGO_BIN_EXE_world-core\"));\n"
        "}\n"
    ),
}

SANDBOX_BOOK = """# `WC-IC-001-v0.1` · 模块接口契约（沙盒）

## §5 模块接口契约（一模块一节）

%(sections)s

## §一 接口清单（沙盒）

沙盒接口号总账（判据④ 的 `契约锚点` 回源核对**就查这份清单**）：

| 接口编号 | 名称 | 提供模块 |
|---|---|---|
| `IF-002` | 门禁裁决 | `M02` |
| `IF-004` | 视觉投影出口 | `M05` |
| `IF-005` | 词表身份 | `M01` |
| `IF-008` | 运行时入口（CLI） | `M04` |
| `IF-009` | 状态折叠与重建 | `M03` |
| `IF-011` | 载体动作执行 | `M06` |
"""

SANDBOX_BOOK_SECTION = """### §5.%(k)d `%(mid)s` 沙盒模块 %(mid)s —— 模块接口契约

#### §1 本册范围
- 模块号：**`%(mid)s`**
"""


def _build_sandbox(root, wc_name="world-core"):
    """搭一个完好沙盒（正控必须四条全绿）。返回 `(仓库根, world-core 根)`。"""
    wc = os.path.join(root, wc_name)
    for d in (os.path.join(wc, "docs", "S2-设计"), os.path.join(wc, SRC_REL),
              os.path.join(wc, TESTS_REL), os.path.join(root, SPECS_REL, "cap-a")):
        os.makedirs(d, exist_ok=True)
    _write(os.path.join(wc, MODREG_REL), SANDBOX_MODREG)
    for r, t in SANDBOX_SRC.items():
        _write(os.path.join(wc, r), t)
    for r, t in SANDBOX_TESTS.items():
        _write(os.path.join(wc, r), t)
    _write(
        os.path.join(wc, IC_BOOK_REL),
        SANDBOX_BOOK % {"sections": "\n".join(
            SANDBOX_BOOK_SECTION % {"k": k, "mid": mid}
            for k, mid in enumerate(("M01", "M02", "M03", "M04", "M05", "M06"), start=1))},
    )
    _write(
        os.path.join(root, SPECS_REL, "cap-a", "spec.md"),
        "# cap-a Specification\n\n## Purpose\n沙盒用最小规格。\n\n## Requirements\n\n"
        "### Requirement: 门禁拒绝未声明能力\n\n沙盒正文。\n\n#### Scenario: 沙盒场景\n\n"
        "- **WHEN** 跑沙盒\n- **THEN** 通过\n"
        "- **证据**：`scripts/test/contract.rs::c03_readmodel_folds`\n",
    )
    return root, wc


def _write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _drop_module_section(text, mid):
    """从沙盒契约册里**删掉某个模块的整节**（标题 → 下一个同级/更高级标题）。

    `None` 表示「该模块的节找不到」（调用方必须把它当失败报出来，不许静默）。
    """
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#") and ("`%s`" % mid) in ln:
            start = i
            break
    if start is None:
        return None
    lvl = len(lines[start]) - len(lines[start].lstrip("#"))
    j = start + 1
    while j < len(lines):
        s = lines[j].lstrip()
        if s.startswith("#"):
            l2 = len(s) - len(s.lstrip("#"))
            if l2 <= lvl:
                break
        j += 1
    return "\n".join(lines[:start] + lines[j:])


def _reg_edit(path, old, new, tag, failures):
    """按字面替换改登记表；**改不动就报错**（避免"反例其实没造出来"的假自证）。"""
    text = read_text(path)
    if old not in text:
        failures.append("%s —— 自证材料与登记表脱节：找不到 %r" % (tag, old))
        return False
    _write(path, text.replace(old, new, 1))
    return True


def self_test():
    """正控（全绿）＋ 每条判据各造反例（必红）＋ 恢复后回绿。"""
    # 用例计数：**由打印行现算**，不写死——本仓实测过"总结行写『反例 10』、实际打了 12 条"。
    # 只按**行首**分类（`正控附条…` 必须先于 `正控…` 试，故按 key 长度降序）。
    tally = {"正控": 0, "正控附条": 0, "反例": 0, "恢复后复跑": 0}
    real_print = builtins.print

    def print(*args):                       # noqa: A001 —— 只在本函数内遮蔽，用来按类计数
        text = " ".join(str(a) for a in args)
        for key in sorted(tally, key=len, reverse=True):
            if text.strip().startswith(key):
                tally[key] += 1
                break
        real_print(*args)

    print("== module_graph.py --self-test ==")
    failures = []
    with tempfile.TemporaryDirectory(prefix="modgraph-") as tmp:
        root, wc = _build_sandbox(tmp)
        reg = os.path.join(wc, MODREG_REL)

        # ── 正控：完好沙盒必须四条全绿 ──────────────────────────────────
        base = check(wc, base=root)
        bad = [r["judgment"] for r in base["judgments"] if not r["ok"]]
        print("  正控（完好沙盒 %d 条判据应全绿）：%s"
              % (len(base["judgments"]), "OK" if not bad else "*失败 " + str(bad)))
        if bad:
            failures.append("正控失败：%s" % bad)
            for r in base["judgments"]:
                for o in r["offenders"]:
                    print("       · %s" % o)

        # ── 正控附条①：**测试面不得漏进生产面**（否则 A-4 的 deps==import 会被测试 use 污染）──
        # 沙盒：`src/**` 里指向 M01 的**生产**证据只有 `gate.rs` 那**一行行内路径**
        # （`crate::ontology::Ontology::load(p)`，见 SANDBOX_SRC 注）；
        # 而 `scripts/test/cli.rs` 里有 `use world_core::ontology::…`（M01）＋ `use world_core::{event, World};`。
        # 故 M04 的**生产** import 面必须**不含 M01**（含了就是把测试面算进来了），
        # 且它带裸 `use world_core::{…}`（非子模块名）也必须**不产边、不报错**。
        m04 = [m for m in base["modules"] if m["id"] == "M04"]
        leak = [m["id"] for m in m04 if "M01" in m["deps_import"]]
        print("  正控附条①（`tests/*.rs` 与 `#[cfg(test)]` 的 use 不得算进生产面）：%s"
              % ("OK" if not leak else "*失败 生产面含 M01：%s" % leak))
        if leak:
            failures.append("测试面漏进生产面：%s" % leak)

        # ── 正控附条②：**行内全限定路径**必须产边（⑥ 的判据面）───────────────────
        # 沙盒里 `M02 → M01` **只有** `src/gate.rs` 那句 `crate::ontology::Ontology::load(p)` 作证
        # （该文件里没有 `use crate::ontology;`）。两件事一起钉，缺一不可：
        #   ① 它必须真的**落在生产边集里**——只验"判据②不红"是假绿：两边都取空也会不红；
        #   ② 判据② 在正控下**不许红**（声明的 `M01` 已被这行代码印证）。
        m02 = [m for m in base["modules"] if m["id"] == "M02"][0]
        a4_ok = [r["ok"] for r in base["judgments"] if r["key"] == "a4_dag_deps"][0]
        inline_edge = "M01" in m02["deps_import"]
        print("  正控附条②（行内 `crate::ontology::…` 须产边：M02→M01 已在生产面=%s 且判据②不红=%s）：%s"
              % (inline_edge, a4_ok, "OK" if (inline_edge and a4_ok) else "*失败 ⑥ 的判据面是装饰"))
        if not (inline_edge and a4_ok):
            failures.append("行内全限定路径未产边（M02 → M01 缺失）或判据② 误红")

        def run():
            return check(wc, base=root)

        def is_red(report, key):
            for r in report["judgments"]:
                if r["key"] == key:
                    return (not r["ok"]), r["offenders"]
            return False, []

        # ── 正控附条③：**注释与字符串里的 `crate::…` 不算依赖** ─────────────────
        # 往 M02 的另一个文件（`src/guard.rs`）塞一条文档链接与一条字符串常量，都指向 `M03`：
        # 抽了它们，`M02` 的 import 集就会多出 `M03` ⇒ 判据② 报"代码里有但没声明"。
        # **它不许红**：文档链接是"说"、字符串是数据，都不是依赖。
        guard = os.path.join(wc, "src", "guard.rs")
        _write(guard, "/// 见 [`crate::readmodel::State`]（文档链接，不是依赖）。\n"
                      "pub fn note() -> &'static str { \"crate::readmodel::State\" }\n")
        rep_c = run()
        red_c, off_c = is_red(rep_c, "a4_dag_deps")
        m02c = [m for m in rep_c["modules"] if m["id"] == "M02"][0]
        leak_c = red_c or ("M03" in m02c["deps_import"])
        print("  正控附条③（注释与字符串里的 `crate::readmodel::…` 不产边 ⇒ 判据② 不应红）：%s"
              % ("OK" if not leak_c else "*失败 注释或字符串被当成了依赖"))
        if leak_c:
            failures.append("注释行或字符串字面量里的路径被误算成依赖")
        _write(guard, SANDBOX_SRC["src/guard.rs"])

        # ── 正控附条④：**共同模块（§2.1「不占号」）不作边目标**（本轮执行者裁定的口径）──
        # 沙盒：`src/main.rs` 里 `use world_core::project::{self, visual};`
        #   · 首段 `project` → `src/project/mod.rs`，§2.1 登记"不占号、属 M01 的机制面"。
        #     若把它当边目标，`M04` 的真实集里就会出现 **M01**（而 `M04` 没声明 M01）⇒ 立刻红。
        #   · 花括号里的 `visual` → `src/project/visual.rs`＝**占号 M05** ⇒ 必须产边 `M04 → M05`。
        # **三件一起钉**：判据②不红 ＋ 真实集里没有 M01 ＋ 跳过的那条**要在报告里数得出来**（不静默）。
        m04c = [m for m in base["modules"] if m["id"] == "M04"][0]
        skip_txt = "\n".join(base["import_edges_skipped_shared"])
        no_m01 = "M01" not in m04c["deps_import"]
        has_m05 = "M05" in m04c["deps_import"]
        listed = "project/mod.rs" in skip_txt
        shared_ok = a4_ok and no_m01 and has_m05 and listed
        print("  正控附条④（共同模块不作边目标：判据②不红=%s／M04 真实集无 M01=%s／有占号 M05=%s"
              "／跳过已列出=%s）：%s"
              % (a4_ok, no_m01, has_m05, listed, "OK" if shared_ok else "*失败 口径没生效"))
        if not shared_ok:
            failures.append("共同模块被当成了边目标，或跳过没被列出来（静默跳过）")

        # ── 反例⑨（⑥ 的"改坏⇒红"）：把那唯一一行**行内**证据删掉 ────────────────
        # 期望：`M02` 声明的 `M01` 再也拿不到代码印证 ⇒ 判据② 报"声明了但代码里没有（M01）"。
        # 这同时是正控附条② 的反向验证：证明"不红"不是因为判据根本不看 M02。
        gate = os.path.join(wc, "src", "gate.rs")
        _write(gate, "use crate::guard;\n\npub fn check(_p: &std::path::Path) -> bool {\n    true\n}\n")
        red, off = is_red(run(), "a4_dag_deps")
        hit = any("M02" in x and "声明了但代码里没有" in x and "M01" in x for x in off)
        print("  反例⑨（删掉 gate.rs 里唯一的行内 `crate::ontology::…` ⇒ 判据② 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑨未变红：行内证据删掉后声明仍被当成已印证（⑥ 的判据面是装饰）")
        _write(gate, SANDBOX_SRC["src/gate.rs"])

        # ── 反例⑫（⑦ 的"改坏⇒红"）：把花括号里的 `visual` 删掉 ──────────────────
        # 期望：`M04` 声明的 `M05` 失去唯一证据（`project` 那半是共同模块、按口径本就不产边）
        # ⇒ 判据② 报"M04：声明了但代码里没有（M05）"。这正是本仓 `src/main.rs:411` 的形态。
        mainrs = os.path.join(wc, "src", "main.rs")
        _write(mainrs, SANDBOX_SRC["src/main.rs"].replace(
            "use world_core::project::{self, visual};", "use world_core::project::{self};", 1))
        red, off = is_red(run(), "a4_dag_deps")
        hit = any("M04" in x and "声明了但代码里没有" in x and "M05" in x for x in off)
        print("  反例⑫（删掉 `use world_core::project::{…}` 里的 `visual` ⇒ 判据② 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑫未变红：花括号里的模块项被漏抽（⑦ 的判据面是装饰）")
        _write(mainrs, SANDBOX_SRC["src/main.rs"])

        # ── 正控附条⑤：**目录型模块（`src/carrier/` → M06）也要逐边核对**（⑤ 的判据面）──
        # 沙盒里 M06 的「源码路径」列是**目录**（没有任何逐字的 `.rs`）：旧实现在这里 `continue`，
        # 于是"有声明、没人看"。三件一起钉：
        #   ① 它**真的被核对**（`deps_judged`——这个字段由**判据自己**填，不是报告另算一遍）；
        #   ② 它的真实 import 集**真的抽到了** `M01`（`src/carrier/kernel.rs: use crate::ontology::…`）；
        #   ③ 声明集（`M01`）== 真实集 ⇒ 判据② 不许红。
        # ⚠ 这三件一起才有意义：单独看 ① 会漏掉"判据跳过了、报告却说核对了"（变异体 N1 实测）；
        #   真正兜底的是反例⑬／⑭（声明与代码不一致时**必须**红）。
        m06 = [m for m in base["modules"] if m["id"] == "M06"][0]
        dir_ok = (m06["deps_judged"] and m06["impl_files"] == ["src/carrier/kernel.rs", "src/carrier/mod.rs"]
                  and "M01" in m06["deps_import"] and a4_ok)
        print("  正控附条⑤（目录型模块被逐边核对：已核对=%s／实现文件=%s／真实集含 M01=%s／判据②不红=%s）：%s"
              % (m06["deps_judged"], ",".join(m06["impl_files"]), "M01" in m06["deps_import"], a4_ok,
                 "OK" if dir_ok else "*失败 目录型模块又被整条跳过"))
        if not dir_ok:
            failures.append("目录型模块未被逐边核对（⑤ 未修：有声明、没人看）")

        # ── 反例⑬（⑤ 的"改坏⇒红"之一）：删掉 M06 **真有印证**的那条声明 ──────────
        # 期望：源码里 `use crate::ontology::…` 还在 ⇒ 判据② 报"M06：**代码里有但没声明**（M01）"。
        # 这一条同时证明附条⑤ 的"不红"不是因为 M06 被跳过。
        if _reg_edit(reg, "**IF-011** | `M01` |", "**IF-011** | 无 |", "反例⑬", failures):
            red, off = is_red(run(), "a4_dag_deps")
            hit = any("M06" in x and "代码里有但没声明" in x and "M01" in x for x in off)
            print("  反例⑬（把 M06 真有印证的 `M01` 声明删掉 ⇒ 判据② 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑬未变红：目录型模块的真边删了声明也不报（⑤ 仍是装饰）")
        _write(reg, SANDBOX_MODREG)

        # ── 反例⑭（⑤ 的"改坏⇒红"之二）：给 M06 声明一条**代码里没有**的 ──────────
        if _reg_edit(reg, "**IF-011** | `M01` |", "**IF-011** | `M01`、`M02` |", "反例⑭", failures):
            red, off = is_red(run(), "a4_dag_deps")
            hit = any("M06" in x and "声明了但代码里没有" in x and "M02" in x for x in off)
            print("  反例⑭（给 M06 多写一条代码里没有的 `M02` ⇒ 判据② 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑭未变红：目录型模块的假声明不报（⑤ 仍是装饰）")
        _write(reg, SANDBOX_MODREG)

        # ── 反例⑮：**靠"未印证的声明边"撑起来的环必须单独标出来**（不许混进"真环"）──
        # 造法：`src/gate.rs`(M02) 加一句 `use crate::carrier::kernel::Reply;` ⇒ M02→M06 是**真边**；
        # 而 M06 的登记表写 `M02`（carrier 底下**没有任何文件** import gate）⇒ 那条是**未印证的声明边**。
        # ⇒ 并集图成环 M02↔M06，真实图**无环**。期望：不出现"源码 import 环"，且并集环里逐条标出
        # "M06-[声明·代码里没有]-> M02"。
        keepg2 = read_text(gate)
        _write(gate, keepg2 + "use crate::carrier::kernel::Reply;\n")
        _reg_edit(reg, "**IF-011** | `M01` |", "**IF-011** | `M02` |", "反例⑮", failures)
        rep15 = run()
        red15, off15 = is_red(rep15, "a4_dag_deps")
        txt15 = "\n".join(x for x in off15 if "有环" in x)
        mark15 = "M06-[声明·代码里没有]-> M02" in txt15
        real15 = "源码 import 环" not in txt15
        print("  反例⑮（并集环靠未印证声明边成立 ⇒ 单独标出、且不得报成源码环）：%s"
              "（未混进源码环=%s／已标注=%s）"
              % ("已红 OK" if (red15 and mark15 and real15) else "*没红",
                 real15, mark15))
        if not (red15 and mark15 and real15):
            failures.append("反例⑮：未印证的声明边撑起的环没有被单独标出（混进了'真环'）")
        _write(gate, keepg2)
        _write(reg, SANDBOX_MODREG)

        # ── 反例①：A-1 把 M03 的 intent 改成占位符 ──────────────────────
        if _reg_edit(reg, "| 状态由账本折叠而来 |", "| 待补 |", "反例①", failures):
            red, off = is_red(run(), "a1_intent")
            hit = any("M03" in x and "不是一句" in x for x in off)
            print("  反例①（M03 的 intent 改占位符 => 判据① 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例①未变红或未指名 M03")

        _write(reg, SANDBOX_MODREG)

        # ── 反例②：A-1 造一个**并列两事**的 intent ─────────────────────
        if _reg_edit(reg, "| 词表身份的唯一出处 |", "| 词表身份的出处与校验 |", "反例②", failures):
            red, off = is_red(run(), "a1_intent")
            hit = any("M01" in x and "并列两事" in x for x in off)
            print("  反例②（M01 的 intent 里出现「与」= 并列两事 => 判据① 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例②未变红或未指出并列两事")

        _write(reg, SANDBOX_MODREG)

        # ── 反例③：A-3 违反 A-2 的「实现」件——登记表列一个不存在的源码路径 ──
        if _reg_edit(reg, "`src/readmodel.rs`", "`src/nowhere.rs`", "反例③", failures):
            red, off = is_red(run(), "a2_four_in_one")
            hit = any("M03" in x and "实现缺" in x for x in off)
            print("  反例③（M03 的实现路径改成不存在的文件 => 判据③ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例③未变红或未报「实现缺」")

        _write(reg, SANDBOX_MODREG)

        # ── 反例④：A-2 的「契约」件——删掉 `WC-IC-001` 里 M03 的**节**，并让指向它的证据行**失效** ──
        # 沙盒里 M03 的契约落点原本**两处都在**（契约册里的节 ＋ 规格证据行）：
        # 删节而证据行仍有效 ⇒ 不该红（判据不能比事实更严）；
        # 两处都掉 ⇒ 必须红。
        book = os.path.join(wc, IC_BOOK_REL)
        keepb = read_text(book)
        rump = _drop_module_section(keepb, "M03")
        if rump is None:
            # 自证材料脱节 ⇒ 报失败但**不 return**（后面还有别的反例要跑），并跳过本条
            failures.append("反例④ —— 自证材料脱节：契约册里找不到含 `M03` 的标题（锚与册格式脱节）")
            print("  反例④（删 M03 节且证据行失锚 => 判据③ 应红）：*没跑（材料脱节）")
            rump = keepb
        _write(book, rump)
        rep4a = run()
        not_red_keeps_citation = not is_red(rep4a, "a2_four_in_one")[0]
        spec = os.path.join(root, SPECS_REL, "cap-a", "spec.md")
        keeps = read_text(spec)
        _write(spec, keeps.replace("`scripts/test/contract.rs::c03_readmodel_folds`",
                                   "`scripts/test/contract.rs::c99_not_a_real_test`", 1))
        red, off = is_red(run(), "a2_four_in_one")
        hit = any("M03" in x and "契约缺" in x for x in off)
        print("  反例④（删 `WC-IC-001` 里 M03 的节且证据行失锚 ⇒ 两处契约落点都没了 => 判据③ 应红；"
              "仅删节时不应红=%s）：%s"
              % (not_red_keeps_citation, "已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例④未变红或未报「契约缺」")
        if not not_red_keeps_citation:
            failures.append("反例④附条：仅删节就红了（判据比事实更严）")
        _write(book, keepb)
        _write(spec, keeps)

        # ── 反例④b：A-2 一整行"只有身份、没有落点"（登记表新增 M07，实现/测试/契约都缺）──
        # 这一条正对本项目的今天：`WC-MODREG-001` 登记了 `M10` 而 `src/carrier/` 曾不存在。
        # （号取 M07：沙盒里 M05 已占给投影、M06 已占给目录型载体模块。）
        #
        # ★ 这一行由**登记表构造器**拼，不靠 `.replace()` 插进沙盒全文——
        #   12 列的表行用字符串替换插进去，一旦分隔符数错，红的是**别的判据**，
        #   而那种红会被读成"判据坏了"。原子档栏位**填齐**：本反例要证明的是
        #   「三件落点缺 ⇒ 判据③ 红」，不是「判据④ 红」，两件事不许混。
        _write(reg, _sandbox_modreg(extra_rows=[
            ("**M07**", _sandbox_row("**M07**", "通道", "一个套接字一个身份",
                                     "`src/channel.rs`", "**IF-006**", "无",
                                     "`WC-IC-001` §5.7 的 `IF-006` 一节",
                                     "`scripts/test/contract.rs::c01_gate_refuses`", "不写盘"))]))
        red, off = is_red(run(), "a2_four_in_one")
        hit_impl = any("M07" in x and "实现缺" in x for x in off)
        hit_test = any("M07" in x and "测试缺" in x for x in off)
        hit_cont = any("M07" in x and "契约缺" in x for x in off)
        print("  反例④b（登记表新增 M07 而三件都缺 => 判据③ 应红）：%s（实现缺=%s 测试缺=%s 契约缺=%s）"
              % ("已红 OK" if (red and hit_impl and hit_test and hit_cont) else "*没红",
                 hit_impl, hit_test, hit_cont))
        if not (red and hit_impl and hit_test and hit_cont):
            failures.append("反例④b未三件齐报（实现/测试/契约）")
        _write(reg, SANDBOX_MODREG)

        # ── 反例⑤：A-4「deps == import」——加一条代码里没有的声明边 ───────
        if _reg_edit(reg, "| `src/readmodel.rs` | **IF-009** | `M02` |",
                     "| `src/readmodel.rs` | **IF-009** | `M01`、`M02` |", "反例⑤", failures):
            red, off = is_red(run(), "a4_dag_deps")
            hit = any("M03" in x and "声明了但代码里没有" in x and "M01" in x for x in off)
            print("  反例⑤（把 M01 写进 M03 的依赖列，代码里没有 => 判据② 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑤未变红或未报「声明了但代码里没有」")

        _write(reg, SANDBOX_MODREG)

        # ── 反例⑤b：A-4 另一侧——代码里新加一条没声明的 import ─────────────
        gate = os.path.join(wc, "src", "gate.rs")
        keepg = read_text(gate)
        _write(gate, "use crate::guard;\nuse crate::readmodel::State;\n")
        red, off = is_red(run(), "a4_dag_deps")
        hit = any("M02" in x and "代码里有但没声明" in x and "M03" in x for x in off)
        print("  反例⑤b（gate.rs 新 import readmodel，声明未改 => 判据② 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑤b未变红或未报「代码里有但没声明」")
        _write(gate, keepg)

        # ── 反例⑤c：生产面/测试面**不可混算**——在 `#[cfg(test)] mod unit` 里加 import ──
        # 期望：A-4（deps==import）**不因测试内 use 而红**，但该边必须出现在报告的测试面里
        #（否则"只抽生产路径"就成了"把边悄悄丢掉"）。
        _write(gate, keepg + "\n#[cfg(test)]\nmod unit {\n    use super::*;\n"
                            "    use crate::readmodel::State;\n}\n")
        rep5c = run()
        red5c, off5c = is_red(rep5c, "a4_dag_deps")
        m02 = [m for m in rep5c["modules"] if m["id"] == "M02"][0]
        shown = "M03" in m02["deps_import_tests_only"]
        print("  反例⑤c（测试内 use 不进生产面 => 判据② 不应红；但须在测试面里露出来）：%s"
              % ("OK" if (not red5c and shown) else "*失败 判据②红=%s 测试面含M03=%s" % (red5c, shown)))
        if red5c or not shown:
            failures.append("反例⑤c：测试内 use 被误算进生产面，或该边未在测试面露出来")
        _write(gate, keepg)

        # ── 反例⑥：A-4 的「无环」——造一条真环（ontology 反向 import readmodel）────
        # 沙盒原本已有 M02→M01（`gate.rs: use crate::ontology;`）、M03→M02（`readmodel.rs: use crate::gate…`）；
        # 再加 `ontology.rs: use crate::readmodel;` ⇒ M01→M03→M02→M01 成环。
        onto = os.path.join(wc, "src", "ontology.rs")
        keepo = read_text(onto)
        _write(onto, "use crate::readmodel::State;\n")
        red, off = is_red(run(), "a4_dag_deps")
        hit = any("有环" in x and "M01" in x and "M02" in x and "M03" in x for x in off)
        print("  反例⑥（ontology 反向 import readmodel ⇒ M01→M03→M02→M01 成环 => 判据② 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑥未变红或未报「有环」")
        _write(onto, keepo)

        # ── 反例⑥b：无环的另一面——**根级裸名**（`use <mod>::…;`）也要被抽成边并被抓 ──
        _write(onto, "use readmodel::State;\n")            # 裸名形态（`src/lib.rs:23-26` 的同款）
        _write(os.path.join(wc, "src", "readmodel.rs"), "use gate::Decision;\n")
        red, off = is_red(run(), "a4_dag_deps")
        hit = any("有环" in x and "M01" in x and "M02" in x and "M03" in x for x in off)
        print("  反例⑥b（裸名 `use readmodel::…`＋`use gate::…` ⇒ M01→M03→M02→M01 成环 => 判据② 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑥b未变红或未报跨模块环（裸名形态）")
        _write(onto, keepo)
        _write(os.path.join(wc, "src", "readmodel.rs"), SANDBOX_SRC["src/readmodel.rs"])

        # ── 反例⑩：环路径**必须打印得出来**，且**不得把环外节点算进环** ──────────
        # 这是本仓工作区真实形态的缩小版：真环只有 `M03 ↔ M04`，但两个环上节点的
        # **字典序首位后继**都通向死路 `M01`（`M03→M02→M01`、`M04→M02→M01`）。
        # 旧实现沿首位后继走，从任何起点都走不出环 ⇒ 退化成"节点集合 M01、M02、M03、M04"
        # —— 把**不在环上**的 M01/M02 也报成环上模块（实测本仓真环只有 M04↔M09，它报 9 个节点）。
        rdm = os.path.join(wc, "src", "readmodel.rs")
        keepr = read_text(rdm)
        _write(os.path.join(wc, "src", "lib.rs"),
               SANDBOX_SRC["src/lib.rs"].replace("pub mod readmodel;",
                                                 "pub mod readmodel;\npub struct World;", 1))
        _write(rdm, "use crate::gate::Decision;\nuse crate::World;\n")     # M03→M02、M03→M04
        rep10 = run()
        red10, off10 = is_red(rep10, "a4_dag_deps")
        cyc_txt = "\n".join(x for x in off10 if "有环" in x)
        ok10 = (red10 and "M03" in cyc_txt and "M04" in cyc_txt and "→" in cyc_txt
                and "节点集合" not in cyc_txt and "M01" not in cyc_txt and "M02" not in cyc_txt)
        print("  反例⑩（首位后继是死路时仍须打印真环 M03↔M04，且死路 M01/M02 不得被算成环上模块）：%s"
              % ("已红 OK" if ok10 else "*失败 逐字=%r" % cyc_txt))
        if not ok10:
            failures.append("环路径搜索退化：只报节点集合（含环外节点）或打印不出环")
        _write(rdm, keepr)
        _write(os.path.join(wc, "src", "lib.rs"), SANDBOX_SRC["src/lib.rs"])

        # ── 反例⑪：**两条互不相连的真环必须都打印**（旧实现只报碰巧先走到的那一条）──
        # 实测本仓工作区就是这种图：`M02→M05→M10→M02` 与 `M04→M09→M04` 同时存在 ⇒
        # 只报一条时，「源码 import 环」这句话就是**漏报**。这里用字面图直接钉住 `find_cycles`。
        two = {"M01": {"M02"}, "M02": {"M01"}, "M03": {"M01"},       # M03 是环的下游（死路诱饵）
               "M04": {"M05"}, "M05": {"M04"}}
        has2, cycs2, ok2 = find_cycles(sorted(two), two)
        got2 = sorted(tuple(sorted(set(c))) for c in cycs2) if ok2 else []
        want2 = [("M01", "M02"), ("M04", "M05")]
        print("  反例⑪（两条互不相连的真环 ⇒ 两条都要打印，且不含死路 M03）：%s"
              % ("OK" if (has2 and ok2 and got2 == want2) else "*失败 实得 %s" % (got2,)))
        if not (has2 and ok2 and got2 == want2):
            failures.append("多条环时未全部打印（或把环外节点算进了环）")

        # ── 反例⑦：A-2 的「测试」件——删掉唯一指到 M03 的用例 ─────────────
        # 这里同时验两件事（都是"少了那个用例"的直接后果）：
        #   ① M03 的**测试缺**（函数体里再没有 `readmodel`）；
        #   ② 规格证据行 `scripts/test/contract.rs::c03_readmodel_folds` **失锚** ⇒ 那条证据不再算契约落点。
        ct = os.path.join(wc, TESTS_REL, "contract.rs")
        keepc = read_text(ct)
        _write(ct, keepc.replace("fn c03_readmodel_folds", "fn c03_unrelated_case")
                         .replace("world_core::readmodel::fold", "world_core::ontology::FAMILIES"))
        red, off = is_red(run(), "a2_four_in_one")
        hit_test = any("M03" in x and "测试缺" in x for x in off)
        print("  反例⑦（删掉唯一指到 M03 的用例 ⇒ 测试缺，且证据行失锚 => 判据③ 应红）：%s"
              % ("已红 OK" if (red and hit_test) else "*没红"))
        if not (red and hit_test):
            failures.append("反例⑦未变红或未报「测试缺」")
        _write(ct, keepc)

        # ── 反例⑧：A-2 的覆盖面——新增一个没人认领的 .rs ─────────────────
        orphan = os.path.join(wc, "src", "orphan.rs")
        _write(orphan, "pub fn x() {}\n")
        red, off = is_red(run(), "a2_four_in_one")
        hit = any("orphan.rs" in x and "没有被任何模块号认领" in x for x in off)
        print("  反例⑧（src/orphan.rs 无模块号认领 => 判据③ 应红）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑧未变红或未报未认领文件")
        os.remove(orphan)

        # ══════════ 判据④（A-3 原子档栏位）的反例：**逐条"改坏⇒必红"** ══════════
        # 为什么每条都要单独造：判据④ 查六栏，只造一条反例证明不了另外五栏也在被看
        #（本项目既有口径：**一判据一反例**，自证通过 ≠ 判据有效）。
        # 每条都用 `_reg_edit` 做**字面**替换，改不动即报"自证材料脱节"，不静默跳过。

        # 反例⑯：**整组列缺失** —— 把原子档那 6 列表头整块删掉。
        # 期望：不是"静默通过"，而是指名"原子档栏位整组缺失"。
        #
        # ★ 本轮修（E8）：这条反例**同时也是"删掉那条静默兜底"的反向验证**。
        #   旧实现里，表头取不到「全六列」时会回落到 **`atom_cols[0]`＝文档里第一个表块**；
        #   而本沙盒里只有 §2 一个原子表块 ⇒ 两种实现**都**会红 ⇒ 那条反例**当时根本区分不出**
        #   "兜底还在不在"（**自证通过 ≠ 判据有效**）。现在删除该兜底后，本反例红的原因
        #   明确是「`cur_atom` 留空 ⇒ 每行 atom 为空 ⇒ 整组缺失」，故它与「改对⇒绿／改回⇒红」的
        #   对照一起钉住了那条兜底。**真诱饵**（文档里 §2 之前还有一个"表头首格也是 模块号"的表块）
        #   在真登记表里存在（`WC-HLD-001:156`），在沙盒里不存在 ⇒ **沙盒测不到那一形态**，如实记在评审面上。
        _write(reg, "\n".join(
            (ln.split("| 职责（一句话） |")[0] + " |"
             if ln.lstrip().startswith("| 模块号 ") else ln)
            for ln in SANDBOX_MODREG.split("\n")))
        red, off = is_red(run(), "a0_atom_fields")
        hit = any("M01" in x and "整组缺失" in x for x in off)
        print("  反例⑯（把原子档 6 列表头整块删掉 ⇒ 判据④ 应红，且**不得静默通过**）：%s"
              % ("已红 OK" if (red and hit) else "*没红"))
        if not (red and hit):
            failures.append("反例⑯未变红：原子档栏位整组缺失时未报（判据④ 是装饰）")
        _write(reg, SANDBOX_MODREG)

        # ── 正控附条⑥：**E8 的"删兜底"必须真的删掉了** ─────────────────────
        # 做法：往沙盒登记表**前面**插一个"表头首格也是 `模块号`、但只有前 6 列"的表块（**诱饵**）。
        #   · 若"回落到第一个表块"的兜底**还在** ⇒ `atom_cols[0]`＝这个诱饵 ⇒ 六列全取不到 ⇒ 仍红；
        #   · 若兜底**已删**（本轮修）⇒ 取表头时逐块找"全六列"的那块 ＝ §2 真表头 ⇒ **不红**。
        # 故「不红」正是"兜底已删"的读数；本条与反例⑯（删真表头 ⇒ 红）互为反向验证。
        decoy = ("| 模块号 | 模块名 | 职责（一句话） | 源码路径 | 提供接口 | 依赖模块 |\n"
                 "|---|---|---|---|---|---|\n"
                 "| **M99** | 诱饵 | 诱饵行 | `src/ontology.rs` | **IF-005** | 无 |\n\n")
        _write(reg, decoy + SANDBOX_MODREG)
        rep_d = run()
        red_d, off_d = is_red(rep_d, "a0_atom_fields")
        m01_d = [m for m in rep_d["modules"] if m["id"] == "M01"]
        atom_ok = bool(m01_d) and len(m01_d[0]["atom_cols_present"]) == len(ATOM_FIELDS)
        print("  正控附条⑥（§2 之前插一个「首格也是 模块号、但无原子列」的表块 ⇒ 判据④ **不应红**；"
              "这证明「回落到第一个表块」的兜底已删）：%s（不红=%s／M01 原子列取全=%s）"
              % ("OK" if (not red_d and atom_ok) else "*失败", not red_d, atom_ok))
        if red_d or not atom_ok:
            failures.append("正控附条⑥失败：表头识别仍会回落到别的表块（E8 的兜底没删干净）")
        _write(reg, SANDBOX_MODREG)

        # 反例⑰：**intent 与「职责」列不一致** —— 同一件事两个说法（A-1 要消灭的形态）。
        # ⚠️ 两处坑，都在本反例上踩过：
        #   ① 这两格的字面**恰好相同** ⇒ 替换串必须带前后文，只动 intent 那一格
        #      （短串 `| 词表身份的唯一出处 |` 会先命中「职责」列 ⇒ 反例根本没造出来）；
        #   ② 改的必须是**字词**，不能只加 `**` 强调 —— 判据两边都走 `norm_cell`
        #      （强调与反引号不算字），加个 `**` 不构成"两个说法"，反例于是永远不红。
        if _reg_edit(reg,
                     "| 无 | 词表身份的唯一出处 | 由 `module_graph.py` 判 deps == import |",
                     "| 无 | 词表身份的唯一来处 | 由 `module_graph.py` 判 deps == import |",
                     "反例⑰", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "不一致" in x for x in off)
            print("  反例⑰（intent 与「职责（一句话）」列不一致 ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑰未变红：两处 intent 不一致时未报（同一件事两个说法溜过去了）")
        _write(reg, SANDBOX_MODREG)

        # 反例⑱：**契约锚点写一个不存在的接口号** —— 凭空写的号不算契约锚点（回源核对）。
        if _reg_edit(reg, "`WC-IC-001` §5.1 的 `IF-005` 一节",
                     "`WC-IC-001` §5.1 的 `IF-099` 一节", "反例⑱", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "IF-099" in x and "找不到这个号" in x for x in off)
            print("  反例⑱（契约锚点写不存在的 `IF-099` ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑱未变红：凭空写的接口号被当成契约锚点（回源核对是装饰）")
        _write(reg, SANDBOX_MODREG)

        # 反例⑲：**四件同夹证据指向不存在的用例** —— 「形态上等于声称存在」正是要抓的。
        if _reg_edit(reg, "`scripts/test/contract.rs::c02_ontology_loads`",
                     "`scripts/test/contract.rs::c99_not_a_real_test`", "反例⑲", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "这个用例不存在" in x for x in off)
            print("  反例⑲（同夹证据指向不存在的用例 ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑲未变红：不存在的用例 token 被当成同夹证据")
        _write(reg, SANDBOX_MODREG)

        # 反例⑳：**side_effects 留空** —— A-3「不写副作用＝声明无副作用，但不许留空」。
        #   ★ 2026-09-28 改夹具串：沙盒正控的「机核读数」格已换为真读数（含命令），
        #     故本反例的锚点也要跟着换——**否则它会因"夹具串找不到"而变成假绿**（自证当场报出了这一条）。
        if _reg_edit(reg, "| 只读不写盘 | `python scripts/verify/module_graph.py` → 判据② deps == import：通过",
                     "| — | `python scripts/verify/module_graph.py` → 判据② deps == import：通过",
                     "反例⑳", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "side_effects" in x for x in off)
            print("  反例⑳（side_effects 填成占位符 `—` ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例⑳未变红：副作用栏留空/占位时未报（A-3 那一栏没人看）")
        _write(reg, SANDBOX_MODREG)

        # 反例㉑：**机核读数不点判它的判据** —— 机器读数列必须说清"谁判的哪一条"。
        #   ★ 2026-09-28 改：原来把该格换成"看着没问题"。新增的**指针式**规则会先命中
        #     任何含「以判据」的值，故此处改用一个**有命令、不指针、但缺 `deps == import`** 的值，
        #     让它**只**触发第⑦步的最后一个分支（"没有点名本工具管的那条判据"）。
        if _reg_edit(reg, "`python scripts/verify/module_graph.py` → 判据② deps == import：通过",
                     "`python scripts/verify/module_graph.py` 跑过了，没问题", "反例㉑", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "机核读数" in x and "没有点名" in x for x in off)
            print("  反例㉑（机核读数不点名判据 ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例㉑未变红：机核读数写成一句无判据的感想也过关")
        _write(reg, SANDBOX_MODREG)

        # 反例㉒：**指针式**填法（点了名、却没给读数）—— 2026-09-28 评审席判出的形态。
        #   实盘就是 `WC-MODREG-001` §2 那一列：12 行逐字都是
        #   「以判据②（deps == import）现场读数为准」，**点了名、含 `deps == import`、一个读数都没有**。
        #   旧规则只查"非占位 ∧ 含 `deps == import`" ⇒ 它们全过。
        #   本条即那次收紧的反例；**没有它，这次收紧就是没有反例的判据（＝装饰）**。
        if _reg_edit(reg, "`python scripts/verify/module_graph.py` → 判据② deps == import：通过",
                     "以判据② 现场读数为准（判 deps == import）", "反例㉒", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "机核读数" in x and "指针式" in x for x in off)
            print("  反例㉒（机核读数写成指针式 ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例㉒未变红：把这一格写成「以某判据为准」也能过关")
        _write(reg, SANDBOX_MODREG)

        # 反例㉓：**deps 机核栏不点名工具** —— "由谁判"不许含糊。
        #   （编号原为㉒，与上一条重名；2026-09-28 改为㉓——同名会让输出看起来像"同一条跑了两遍"。）
        if _reg_edit(reg, "由 `module_graph.py` 判 deps == import",
                     "依赖看起来是对的", "反例㉓", failures):
            red, off = is_red(run(), "a0_atom_fields")
            hit = any("M01" in x and "deps 机核" in x and "没有点名" in x for x in off)
            print("  反例㉓（deps 机核栏不点名判它的工具 ⇒ 判据④ 应红）：%s"
                  % ("已红 OK" if (red and hit) else "*没红"))
            if not (red and hit):
                failures.append("反例㉓未变红：依赖机核栏写成一句无工具的断言也过关")
        _write(reg, SANDBOX_MODREG)

        # ── 第二正控：全部恢复后必须回到全绿 ─────────────────────────────
        back = run()
        bad2 = [r["judgment"] for r in back["judgments"] if not r["ok"]]
        print("  恢复后复跑（应回到全绿）：%s" % ("OK" if not bad2 else "*失败 " + str(bad2)))
        if bad2:
            failures.append("恢复后未回绿：%s" % bad2)
            for r in back["judgments"]:
                for o in r["offenders"]:
                    print("       · %s" % o)

    if failures:
        print("  => 自证不通过：%s" % "；".join(failures))
        print("  => 按本项目口径：**这条守卫是装饰，拒绝合入**。")
        return 1
    print("  => 自证通过：**四条判据**逐条在反例下变红、在正控下全绿"
          "（正控 %d ＋ 正控附条 %d ＋ 反例 %d ＋ 恢复后复跑 %d——**数由上面打印的行现算**，不写死）。"
          % (tally["正控"], tally["正控附条"], tally["反例"], tally["恢复后复跑"]))
    return 0


# ────────────────────────── 主程序 ──────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="机核层守卫（WC-ATOM-001 §四 机核清单：单意图 / 四件同夹 / deps==import 且无环）")
    ap.add_argument("--repo", default=None,
                    help="world-core 目录或仓库根；默认从本脚本位置向上找含 %s 的目录" % MODREG_REL)
    ap.add_argument("--repo-base", default=None,
                    help="仓库根（含 specs 的那一级）；默认取 world-core 的上一级")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--intent-column", default="职责",
                    help="A-1 取 intent 的列名（默认 `职责`——登记表暂无 intent 列，口径见文件头）")
    ap.add_argument("--self-test", action="store_true",
                    help="每条判据各造一个反例，验证它们真的会红")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    wc = args.repo or find_worldcore(os.path.dirname(os.path.abspath(__file__)))
    if not wc:
        print("* 找不到 world-core 根（向上找不到含 %s 的目录）；用 --repo 指定。" % MODREG_REL)
        return 2
    wc = os.path.abspath(wc)
    if not os.path.isfile(os.path.join(wc, MODREG_REL)) and \
            os.path.isfile(os.path.join(wc, "world-core", MODREG_REL)):
        wc = os.path.join(wc, "world-core")            # 传进来的是仓库根

    rep = check(wc, args.intent_column, args.repo_base)
    failed = [r for r in rep["judgments"] if not r["ok"]]

    if args.json:
        out = dict(rep)
        out["passed"] = len(rep["judgments"]) - len(failed)
        out["failed"] = len(failed)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("== module_graph.py —— 机核层守卫（WC-ATOM-001 §四 机核清单）==")
        print("   world-core：%s" % wc)
        print("   登记表    ：%s" % rep["registry"])
        print("   A-1 取数列：%s（登记表暂无 intent 列，口径见本脚本文件头）" % rep["intent_column"])
        print("   模块      ：%d 个（%s）；其中源码未落成：%s"
              % (len(rep["modules"]),
                 ",".join(m["id"] for m in rep["modules"]),
                 ",".join(rep["planned_modules"]) or "无"))
        # 目录型模块（「源码路径」列写的是**目录**）：把"它底下的实现文件"逐个数出来——
        # 这是 ⑤ 的可见证据（旧实现整条跳过它，读者连"它有哪些文件"都看不到）。
        for m in rep["modules"]:
            if any(p.endswith("/") for p in m["src_declared"]):
                print("   目录型模块：%-4s ← %s（实现文件 %d 件；判据② %s）"
                      % (m["id"], "、".join(p for p in m["src_declared"] if p.endswith("/")),
                         len(m["impl_files"]),
                         "已逐边核对" if m["deps_judged"] else "**未核对**（实现文件 0 件）"))
        print("   真实 import 边（生产面）：")
        for mid, deps in rep["import_edges_production"].items():
            print("     %s → %s" % (mid, ",".join(deps) or "—"))
        print("   真实 import 边（仅测试面，不计入 deps==import）：")
        for mid, deps in rep["import_edges_test_only"].items():
            if deps:
                print("     %s → %s" % (mid, ",".join(deps)))
        if rep["import_edges_skipped_shared"]:
            print("   按口径跳过（**共同模块不作边目标**，`WC-MODREG-001` §2.1；逐条列出、不静默）：")
            for s in rep["import_edges_skipped_shared"]:
                print("     %s" % s)
        print()
        for r in rep["judgments"]:
            print("  %s %s" % ("[OK]" if r["ok"] else "[FAIL]", r["judgment"]))
            for o in r["offenders"][:40]:
                print("       · %s" % o)
            if len(r["offenders"]) > 40:
                print("       · ……（还有 %d 条同类）" % (len(r["offenders"]) - 40))
        print("  —— 通过 %d / 失败 %d ——" % (len(rep["judgments"]) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
