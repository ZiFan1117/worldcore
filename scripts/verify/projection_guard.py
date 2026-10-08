#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projection_guard.py —— 「界面＝世界的投影」这一面的判据（P1–P10）。

## 为什么需要它

界面层那些脚本（`world-projection` / `world-toggle-mute` …）在 `D:\\Code` 全树零命中
⇒ 「界面」这件事**没有可立判据的地方**：改坏了不会红，改好了也没有证据。
本脚本把界面变成**可判读的一面**：输入面 ＝ 仓内 `scripts/release/world-*` ∪ `scripts/collab/wc_submit.py`（只读），
每条判据都配**同形态反例**，`--self-test` 先咬自己（正控必绿、反例必红）。

## 十条判据

| # | 判什么 | 真实违规形态（反例） |
|---|---|---|
| P1 | 界面面**解析非空**（≥1 件、可读、非空） | 界面件一件都不在仓里 ⇒ RED，**不许判绿**（空集判绿是假绿） |
| P2 | 界面**只发 `act`**，且写路径真的存在 | 把点击的 `"kind":"act"` 改成 `"kind":"change"`；或整条写路径被删掉 |
| P3 | 界面**不碰文件**（零缓存／零直读／零落盘） | 加一行 `cat <缓存>`；加一行 `open('/var/lib/world-ui/last','w')`；加一行 `> /var/lib/world-ui/last` |
| P4 | 界面点名的投影名 ⊆ **投影名集合**（从 `src/main.rs` 现算，再**减去不是投影的那一臂** `check`） | 把默认投影名改成 `table`；或改成 `check`（那是核对命令，不是一份投影） |
| P5 | 世界读不到时界面有**「离线」出口**（不许回退旧值） | 删掉离线分支、改成回退上一份读数 |
| P6 | 读世界**之前**先判「账本读得到吗」（界面**不制造真相文件**） | 去掉那次 `-r` 判定（世界在账本不存在时会建一个 0 字节账本） |
| P7 | 发世界的件必须走**界面自己的口**（`omarchy.sock`），**不许**走内核口 `world.sock` | 把 `omarchy.sock` 改回 `world.sock`（⇒ 作者永远叫 `world://core`，"谁点的"查不出来） |
| P8 | 请求体**不许自称** actor（身份由内核按键给出） | 在 `body` 里加 `"actor":"world://presence/omarchy"` |
| P9 | 发世界**之前真调一次**世界（`describe`）：可点项来自世界 | 把那次 `describe` 调用删掉、改成脚本自己列能力（★ 只在给**人看**的提示语里提一句不算） |
| P10 | **部署清单自洽**（E6 两档）：`same` 的必须与表中 VM `sha256` 一致；`pending` 的必须**确实还不一致**；每件界面件都要在清单里点得出来 | 清单写 `same` 却对不上；清单写 `pending` 而仓内**已经**等于 VM 值（清单过期）；界面件漏登记 |

## ★ 本判据**不判**什么（如实登记，别当已覆盖）

1. **世界侧没有「有哪些投影」的声明面** ⇒ 「声明集 ≡ 可达集」这条今天**无标的物**。
   本件只能判「**界面用到的名字 ⊆ 代码可达名**」；判**不到**「可达名 ⊆ 世界声明」
   （那一条要动法律，属《方案-投影协议-2026-10-05.md》问 2 的裁点）。
2. **VM 上那份界面件与仓内件是不是同一份**（名同、sha 同）—— 本件**只扫宿主仓树**，不含 VM。
   ⇒ 界面件在 VM 上被改坏、仓里没改（或反过来），本件**读不到**。
3. **动态传参的投影名**（例：`world-projection.sh "$1"`）本件抽不到；只抽「静态字面量」与
   「环境变量默认值」两种形态。⇒ 界面若完全靠外部传名，本件的 P4 对该件覆盖不到（标 WEAK）。
4. **值的语义**：本件不判 `project` 输出里的值对不对（那是同源核对与排版审计的活）。

用法：
  python3 scripts/verify/projection_guard.py                 # 判真件（仓树）
  python3 scripts/verify/projection_guard.py --repo <目录>
  python3 scripts/verify/projection_guard.py --sandbox <目录>  # --self-test 的夹具根（缺省＝私有临时目录）
  python3 scripts/verify/projection_guard.py --self-test     # 正控必绿、每条判据的反例必红
退出码：0 全过；1 有判据红；2 用法错误／输入面解析不出（输入面读不到时**不许**rc=0）。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

UI_GLOB_PREFIX = "world-"
# ★ 2026-10-07 修（现取病灶）：界面件原来按 `tools/` 取——`tools/` 已随布局迁移拆成
#   `scripts/release/`（载体侧脚本＋清单）与 `scripts/collab/`（`wc_submit.py`）
#   （权威：`ninedim/_索引-工程域结构与命名.md` §四「脚本住 `scripts/`」）。
#   旧口径下 `ui_files()` **恒返 0 件** ⇒ 判据 P1 报"界面面解析出 0 件"——**假红**
#   （界面件全在，只是取的夹子过期了）；而 P2–P10 十条判据**一条都没跑**。
UI_DIRS = (os.path.join("scripts", "release"), os.path.join("scripts", "collab"))
UI_DIR = UI_DIRS[0]                                  # 夹具与清单用的"界面主夹"
MAIN_REL = os.path.join("src", "main.rs")
MANIFEST_REL = os.path.join(UI_DIR, "deployment-manifest.json")

# ★ `project` 的 `match` 里有**不是投影名**的那一臂：`check` 是"渲染两份并核对同源"的**核对命令**，
#   不是一份投影（口径：Lead 2026-10-05 裁 ＋ change-surface 独立复核"可达 ＝ {language, visual}"）。
#   ⇒ 判据 P4 的"投影名"集合 ＝ `match` 各臂 **减去** 这一个；界面**点名 `check`** 视作"点名了非投影"。
NON_PROJECTION_ARMS = {"check"}

# 账本三家族（法律件 `ontology.json.envelope.fields.kind` 的 enum）。**界面只许发 act。**
LEDGER_FAMILIES = ("change", "act", "notice")


# ─────────────────────────── 输入面 ───────────────────────────

def find_repo(start):
    """从 start 往上找 `src/main.rs` 所在的那一层（＝ world-core 树）。"""
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, MAIN_REL)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


# ★ 界面面 ＝ `tools/world-*`（界面脚本）∪ 这几件（界面层的**唯一写入口**：
#   它不在 `world-*` 命名里，但"作者叫什么"这条纪律**必须钉到它头上**——
#   它的缺省口一改回去，调用方不给口时作者就静默变回 `world://core`）。
# ★ 界面面 ＝ `scripts/release/world-*`（界面脚本）∪ 这几件（界面层的**唯一写入口**：
#   它不在 `world-*` 命名里，但"作者叫什么"这条纪律**必须钉到它头上**——
#   它的缺省口一改回去，调用方不给口时作者就静默变回 `world://core`）。
#   件名一律**仓根相对路径**（与布局迁移后的真身同形；原来是裸文件名 + `tools/` 夹）。
EXTRA_UI_FILES = (os.path.join("scripts", "collab", "wc_submit.py"),)


def ui_files(repo):
    """界面件：`UI_DIRS` 下**非递归**的 `world-*` 普通文件 ∪ `EXTRA_UI_FILES`（仓根相对，排序确定）。

    ⚠ 只认**非递归**：`scripts/release/units/` 下的 `world-core*.service`／`*.socket` **不是界面脚本**
    （它们是部署单元），若递归取会被算成"界面件" ⇒ 十一条判据全打在 unit 文件上（假红）。
    """
    out = []
    for rel_dir in UI_DIRS:
        d = os.path.join(repo, rel_dir)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if name.startswith(UI_GLOB_PREFIX) and os.path.isfile(p):
                out.append(p)
    for rel in EXTRA_UI_FILES:
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            out.append(p)
    return sorted(out)


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", "replace")


def strip_comment_lines(text):
    """去掉整行注释（`^\\s*#`）；行尾注释不剥。

    为什么只剥整行：本判据要抓的是「脚本真去读了一份文件」，
    而注释里写「不许 cat 缓存」不该被当成违规（也不该因此放过真违规）。
    """
    keep = []
    for line in text.split("\n"):
        if line.lstrip().startswith("#"):
            continue
        keep.append(line)
    return "\n".join(keep)


def strip_quotes(text):
    """去掉引号里的内容（单引号／双引号，含反斜杠转义）。

    为什么要它：**"提一句"与"真调一次"是两件事**。P9 判的是"发世界之前真问过世界没有"，
    而脚本里给**人看的那句话**也会写 `describe`（`say "读不到世界的 describe …"`）——
    判据若按字面找词，就会被自己那句提示喂饱（2026-10-05 实盘反向验证咬出，假绿第 3 例）。
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ("'", '"'):
            quote = ch
            i += 1
            while i < n:
                if text[i] == "\\" and quote == '"':
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def reachable_projections(repo):
    """`world-core project <名>` 的**可达名**：从 `src/main.rs::cmd_project` 现算。

    返回 (names, err)：err 非空 ⇒ 解析失败（**不许**当成"没有投影名"）。
    """
    p = os.path.join(repo, MAIN_REL)
    if not os.path.isfile(p):
        return [], "找不到 %s" % MAIN_REL
    text = read_text(p)
    m = re.search(r"fn cmd_project\b", text)
    if not m:
        return [], "%s 里没有 fn cmd_project（判据的标的物不在）" % MAIN_REL
    body = text[m.start():]
    end = re.search(r"\n\}\n", body)
    if end:
        body = body[: end.start()]
    names = sorted(set(re.findall(r'"([A-Za-z_][A-Za-z0-9_.-]*)"\s*=>', body)))
    if not names:
        return [], "cmd_project 的 match 里解析出 0 个可达名（解析失败 ⇒ 见 G1）"
    return names, ""


def kinds_in(text):
    """脚本里声明要发的账本家族名（`"kind":"…"` / `'kind':'…'` / `kind=…`）。"""
    code = strip_comment_lines(text)
    pats = [
        r'"kind"\s*:\s*"([A-Za-z_][A-Za-z0-9_]*)"',
        r"'kind'\s*:\s*'([A-Za-z_][A-Za-z0-9_]*)'",
        r"\bkind=([A-Za-z_][A-Za-z0-9_]*)",
    ]
    out = []
    for pat in pats:
        out.extend(re.findall(pat, code))
    return out


def projection_names_in(text):
    """脚本点名的投影名：静态字面量 `project <名>` ＋ 视图变量的默认值 `:-<名>`。

    默认值只收两种形态（免得把 `${WORLD_SOCK:-/run/…}` 之类的别路默认值误当投影名）：
    - **位置参数**：`${1:-visual}`；
    - **视图变量**：变量名里含 `WHICH`／`PROJECTION`／`VIEW`，例：`${UI_WHICH:-visual}`。
    """
    code = strip_comment_lines(text)
    names = re.findall(r"\bproject\s+[\"']?([A-Za-z_][A-Za-z0-9_.-]*)", code)
    for m in re.finditer(r"\$\{([0-9]+|[A-Za-z_][A-Za-z0-9_]*):-\s*([A-Za-z_][A-Za-z0-9_.-]*)\}", code):
        var, val = m.group(1), m.group(2)
        if var.isdigit() or re.search(r"WHICH|PROJECTION|VIEW", var):
            names.append(val)
    return names


def read_projection_file(repo):
    """界面件里有没有「读投影」这件事（决定 P5 的标的物是否存在）。"""
    hits = []
    for p in ui_files(repo):
        if re.search(r"\bproject\b", strip_comment_lines(read_text(p))):
            hits.append(p)
    return hits


# ─────────────────────────── 判据 ───────────────────────────

def evaluate(repo):
    """返回 (violations, notes)：violations 是 [(判据号, 说明)]；空 = 全过。"""
    v = []
    notes = []

    files = ui_files(repo)
    if not files:
        v.append(("P1", "界面面解析出 0 件（`scripts/release/world-*` 一件都没有）——"
                         "空集不许判绿；界面进版本控制之前，这一面无从判读"))
        return v, notes

    for p in files:
        rel = os.path.relpath(p, repo)
        text = read_text(p)
        if not text.strip():
            v.append(("P1", "%s 是空文件（解析不出内容）" % rel))
        code = strip_comment_lines(text)
        # ★ 是不是 **shell** 件：`>` 重定向、`cat` 这类**只对 shell 成立**
        #   （Python 里 `len(sys.argv) > 1` 是**比较**，不是重定向 —— 2026-10-05 把界面面扩到
        #    `wc_submit.py` 时当场咬出这处**假红**；Python 侧的"落盘"由 `open(` 判）。
        first = text.split("\n", 1)[0] if text else ""
        is_shell = first.startswith("#!") and "sh" in first

        # P2 —— 只发 act；且写路径真的存在
        kinds = kinds_in(text)
        for k in kinds:
            if k not in LEDGER_FAMILIES:
                v.append(("P2", "%s 要发 kind=`%s`：不是账本三家族（%s）"
                                 % (rel, k, "/".join(LEDGER_FAMILIES))))
            elif k != "act":
                v.append(("P2", "%s 要发 kind=`%s`：界面只许发 `act`"
                                 "（`change` 不过能力层与动作层、不产生因果与回执）" % (rel, k)))

        # P3 —— 不碰文件（分三层；★ 2026-10-05 用 **VM 上真件** 校准过：
        #   真件 `world-projection` 用 `cat "$LOCK"` ＋ `cat /proc/<pid>/comm` 判「世界活着吗」。
        #   那是**存活标记**、不是「曾经是什么」⇒ 它的目标**不算违规**；
        #   本判据第一版把 `cat` 一律判红 ⇒ 对真件是**假红**（G18），故拆成三层。）
        #   P3a 落盘／写文件
        if re.search(r"\bopen\s*\(", code):
            v.append(("P3", "%s 里出现 `open(`：界面零存储（不落盘、不读缓存文件）" % rel))
        for m in re.finditer(r">>?\s*([^\s;&|]*)", code):
            if not is_shell:
                break
            tgt = m.group(1)
            if tgt == "" or tgt.startswith("&") or tgt.startswith("/dev/null"):
                continue
            # ★ 只在目标**像路径**时才判红：说明文字里的 `<动词>`／`<JSON对象>` 会带出
            #   `--params`、`}}` 这种"目标"，它们不是文件（口径：目标须以 / ~ . $ 或字母数字下划线起头）。
            if not re.match(r"^[/~.$A-Za-z0-9_]", tgt):
                continue
            v.append(("P3", "%s 里出现文件写重定向（`>%s`）：界面不落盘" % (rel, tgt)))
        #   P3b 直读账本字节（`stat` 与"把账本路径当 CLI 参数"不算）
        for line in code.split("\n"):
            if "LEDGER" not in line:
                continue
            if re.search(r"\b(?:cat|tail|head|dd|od|xxd|strings|less|more|wc)\b", line) or \
               re.search(r"(?<!<)<(?!<)", line):
                if re.search(r"(?:^|\s)-[rf]\b|--ledger", line):
                    continue
                v.append(("P3", "%s 有一行同时出现账本与「读字节」：界面不许直读账本字节"
                                 "（`[ -r ]` 这类 stat、以及把路径交给世界当 CLI 参数，不算）：%s"
                                 % (rel, line.strip())))
        #   P3c 读"存活标记"以外的文件（缓存／位点／上一次的数）——**只对 shell 件**判
        for m in re.finditer(r"(?:^|[;&|]\s*|\s)(cat|head|tail|less|more|od|xxd|strings)\b([^\n]*)", code):
            if not is_shell:
                break
            rest = m.group(2)
            toks = [t for t in rest.split() if not t.startswith("-")]
            if not toks:
                continue
            tgt = toks[0].strip("\"'")
            if tgt.startswith("/dev/null") or "/proc/" in tgt or "LOCK" in tgt:
                continue
            v.append(("P3", "%s 里用 `%s %s` 读文件：界面只许读**存活标记**（锁里的 pid／`/proc`）；"
                             "缓存／位点／账本字节一律不许" % (rel, m.group(1), tgt)))

        # P4 —— 点名的投影名 ⊆ 可达名（可达名现算，且**减去不是投影的那一臂**，见 NON_PROJECTION_ARMS）
        names = projection_names_in(text)
        reach_all, err = reachable_projections(repo)
        reach = [n for n in reach_all if n not in NON_PROJECTION_ARMS]
        if err:
            v.append(("P4", "投影可达名解析失败：%s" % err))
        elif not reach:
            v.append(("P4", "减掉非投影臂（%s）之后，投影名集合为空 ⇒ 解析失败（不许判绿）"
                             % "/".join(sorted(NON_PROJECTION_ARMS))))
        else:
            for n in names:
                if n not in reach:
                    v.append(("P4", "%s 点名投影 `%s`，而投影名里没有它"
                                     "（现算投影名：%s；`match` 全臂：%s）"
                                     % (rel, n, "/".join(reach), "/".join(reach_all))))
            if not names:
                notes.append("P4: %s 没有点名任何投影（完全靠外部传参）⇒ 本判据对该件覆盖不到（WEAK）" % rel)

        # P7／P8／P9 —— P7 的前半对**全部**界面件判，P8／P9 对"要发世界的件"判
        #   ★ 为什么 P7 前半要管全部：把缺省口改回 `world.sock` 的那一刀落在 `wc_submit.py` 上，
        #     而它**没有** `"kind"`（它只是转发）⇒ 若只在发信件上判，这一刀就漏了。
        if "world.sock" in code:
            v.append(("P7", "%s 的代码里出现 `world.sock`：那个口绑的是 `world://core` ⇒ "
                             "经它发的，作者永远不是界面自己（『谁点的』查不出来）" % rel))
        sends = re.search(r'"kind"\s*:', code) is not None
        if sends:
            # P7 作者（谁点的）：必须走**界面自己的口**
            if "omarchy.sock" not in code:
                v.append(("P7", "%s 要发世界，却不在代码里点名**界面自己的口**（`omarchy.sock`）："
                                 "口给出身份 ⇒ 给不出界面自己的口，作者就不是界面自己" % rel))
            # P8 身份不许自称
            if re.search(r'"actor"\s*:', code):
                v.append(("P8", "%s 的请求体里出现 `\"actor\":`：身份由内核按键给出、**不由请求自称**"
                                 "（`src/channel.rs` 逐字），写了会被硬拒" % rel))
            # P9 可点项来自世界：发之前先问世界（describe）
            #   ★ 判**真调一次**（去引号后的代码视图），不判"提一句"：脚本给**人看的那句话**
            #     里也会写 `describe`，按字面找词会被自己那句提示喂饱（假绿第 3 例）。
            if "describe" not in strip_quotes(code):
                v.append(("P9", "%s 发世界之前没有**真调过**世界（`describe`）：『有哪些可点项』必须来自"
                                 "世界（在册 ∩ 已授），不许由外壳配置或脚本自己列"
                                 "（★ 只在提示语里提一句 `describe` 不算）" % rel))

        # P5 —— 离线出口（★ 判**代码视图**，不判注释里的字样：注释里提一句"离线"不算出口。
        #        这一处是 2026-10-05 用**真件字节**做反向验证时咬出来的假绿——自证夹具里没有
        #        注释，所以自证通过；实盘那份的注释里有"离线"⇒ 删了真出口也不红。）
        if re.search(r"\bproject\b", code):
            # ★ 认"**打印了什么**"，不认"有个名字" —— VM 真件里的离线出口是
            #   `offline() { printf '离线'; exit 0; }`，而 `offline` 这个词同时是**函数名**，
            #   会在每一处 `|| offline` 里出现。判据第一版写 `"offline" in code.lower()` ⇒
            #   **删掉真出口也不红**（2026-10-05 用真件字节做反向验证时咬出，假绿第 2 例）。
            if not re.search(r"(?:printf|echo)[^\n]*(?:离线|offline)", code, re.I):
                v.append(("P5", "%s 读投影，却没有「离线」出口：世界读不到时必须显式说读不到，"
                                 "不许回退旧值（**函数名/变量名叫 offline 不算出口**；"
                                 "注释里写一句也不算）" % rel))

        # P6 —— 界面不制造真相文件（读世界之前先 stat 账本）
        #   为什么：世界的只读口径在**账本不存在**时仍会建一个 0 字节账本
        #   （`src/ledger.rs::open_mode` 的 `if !path.exists()` 那一支，只读也走它）
        #   ⇒ 界面若不先判"读得到账本吗"，一次"读"就会在世界上落下一个文件。
        #   ★ 射程：本判据只判**形态**（有没有这次 stat 判定 ＋ 账本变量名），
        #     **不判**它 guard 的是不是正确的那一次调用（那要跑世界才判得了）。
        if re.search(r"\bproject\b", code):
            # ★ 必须**针对账本**的 stat（`[ -r "$LEDGER" ]`／`[ -f "$LEDGER" ]`）；
            #   只写"随便哪个 `-r` 判定"会被别的路径（本体／策略文件）喂饱 ⇒ 那是假绿。
            has_stat = re.search(r"(?:\[|test)\s+!?\s*-[rf]\s+\"?\$?\{?[A-Za-z_]*LEDGER", code) is not None
            if not has_stat:
                v.append(("P6", "%s 读投影前没有判「账本读得到吗」（缺针对 `LEDGER` 的 `-r`／`-f` 判定）："
                                 "世界在账本不存在时会**建一个 0 字节账本**，"
                                 "界面不许让一次『读』在世界里落下文件" % rel))

    all_kinds = [k for p in files for k in kinds_in(read_text(p))]
    if "act" not in all_kinds:
        v.append(("P2", "界面件里没有一条 `act`：点击→世界的写路径不存在"
                         "（族名现取：%s）" % (",".join(sorted(set(all_kinds))) or "无")))

    if not read_projection_file(repo):
        v.append(("P5", "没有任何界面件读投影（`project`）：世界→投影→界面这条读路径不存在"))

    # P10 —— 部署对应（E6 两档）：★把"收进仓 ≠ 上线"变成**读数**，而不是一句话
    #   读侧（应与 VM 逐字节同）／写侧（有意不同 ⇒ 登记 `pending` ⇒ **不判红**，但必须被点得出来）
    v.extend(_judge_manifest(repo))

    return v, notes


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _sha256_of_text(text):
    """夹具文本按 `build_fixture` 的写法（UTF-8 ＋ LF）落盘后的 sha256。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _judge_manifest(repo):
    """P10：部署清单自洽（只读仓内件；**不读 VM** —— VM 那半要在只读窗口里现取）。"""
    v = []
    path = os.path.join(repo, MANIFEST_REL)
    if not os.path.isfile(path):
        v.append(("P10", "没有部署清单 `%s`：『收进仓 ≠ 上线』就没有读数载体（"
                         "哪些件应与 VM 同源、哪些待部署，必须点得出来）" % MANIFEST_REL))
        return v
    try:
        with open(path, "rb") as f:
            doc = json.loads(f.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        v.append(("P10", "部署清单解析失败：%s" % e))
        return v
    files = doc.get("files")
    if not isinstance(files, list) or not files:
        v.append(("P10", "部署清单里 `files` 为空 ⇒ 解析失败（空集不许判绿）"))
        return v
    listed = set()
    for e in files:
        host = e.get("host", "")
        mode = e.get("mode", "")
        listed.add(host)
        hp = os.path.join(repo, host.replace("/", os.sep))
        if not os.path.isfile(hp):
            v.append(("P10", "清单里的 `%s` 在仓内不存在" % host))
            continue
        if mode not in ("same", "pending"):
            v.append(("P10", "清单里 `%s` 的 mode=`%s` 不认识（只许 same／pending）" % (host, mode)))
            continue
        got = _sha256_file(hp)
        want = e.get("vm_sha256", "")
        if mode == "same" and got != want:
            v.append(("P10", "`%s` 登记为 `same`（应与 VM 逐字节同），而仓内 sha 与表中 VM 值不符："
                             "仓内 %s ≠ 表中 %s" % (host, got[:16], want[:16])))
        if mode == "pending" and got == want:
            v.append(("P10", "`%s` 登记为 `pending`（有意不同、待部署），而仓内 sha **已经等于**表中 VM 值："
                             "⇒ 清单过期（要么改成 `same`，要么在只读窗口里重取 VM 读数）" % host))
    for p in ui_files(repo):
        rel = os.path.relpath(p, repo).replace(os.sep, "/")
        if rel not in listed:
            v.append(("P10", "界面件 `%s` 没进部署清单 ⇒ 『上线没有』这件事点不出来" % rel))
    return v


# ─────────────────────────── 自证（正控 ＋ 反例） ───────────────────────────

GOOD_MAIN = """\
fn cmd_project(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    let which = rest.get(1).map(String::as_str).unwrap_or("");
    match which {
        "language" => ExitCode::SUCCESS,
        "visual" => ExitCode::SUCCESS,
        "check" => ExitCode::SUCCESS,
        other => ExitCode::from(1),
    }
}
"""

GOOD_READ = """\
#!/bin/sh
# 世界 -> 投影 -> 界面（读侧夹具；★ 按 VM 上真件的形态写：含"存活标记"读法）
# 读不到就说读不到：世界不在线时显式写「离线」，不许回退上一份读数
set -u
LEDGER=/var/lib/world-core/ledger.jsonl
LOCK=/var/lib/ledger.lock
WHICH="${1:-visual}"
[ -r "$LEDGER" ] || { printf '离线\\n'; exit 0; }
[ -f "$LOCK" ] || { printf '离线\\n'; exit 0; }
pid=$(cat "$LOCK")
[ -d "/proc/$pid" ] || { printf '离线\\n'; exit 0; }
[ "$(cat "/proc/$pid/comm")" = "world-core" ] || { printf '离线\\n'; exit 0; }
if OUT="$(/usr/bin/world-core --ontology /etc/world-core/ontology.json \\
        --ledger "$LEDGER" \\
        --policy /etc/world-core/policy.json project "$WHICH" 2>/dev/null)"; then
    printf '%s\\n' "$OUT"
else
    printf '离线\\n'
fi
exit 0
"""

GOOD_WRITE = """\
#!/bin/sh
# 点击 -> 一条 act（写侧夹具；★ 与仓内真件同形：自己的口 + 问世界 + 不自称）
set -u
SOCK="${WORLD_SOCK:-/run/world-core/omarchy.sock}"
SUB=/usr/local/lib/world-ui/wc_submit.py
desc=$(/usr/bin/world-core --ontology /etc/world-core/ontology.json \\
        --policy /etc/world-core/policy.json describe 2>/dev/null) || exit 3
case "$desc" in *notice.mute*) : ;; *) exit 4 ;; esac
REQ='{"kind":"act","body":{"capability":"notice.mute","verb":"set","request_id":"r","params":{}}}'
printf '%s\\n' "$REQ" | python3 "$SUB" "$SOCK"
"""


def build_fixture(root, main=GOOD_MAIN, read=GOOD_READ, write=GOOD_WRITE,
                  read_name="world-projection.sh", write_name="world-toggle-mute.sh",
                  manifest="auto"):
    tools = os.path.join(root, UI_DIR)
    os.makedirs(tools, exist_ok=True)
    with open(os.path.join(root, "src", "main.rs"), "w", encoding="utf-8", newline="\n") as f:
        f.write(main)
    if read is not None:
        with open(os.path.join(tools, read_name), "w", encoding="utf-8", newline="\n") as f:
            f.write(read)
    if write is not None:
        with open(os.path.join(tools, write_name), "w", encoding="utf-8", newline="\n") as f:
            f.write(write)
    if manifest is not None:
        if manifest == "auto":
            # 正控用：按夹具**实际** sha 生成一份自洽清单（除非用例自己给一份坏清单）
            entries = []
            for name in (read_name, write_name):
                p = os.path.join(tools, name)
                if os.path.isfile(p):
                    entries.append({"host": UI_DIR.replace(os.sep, "/") + "/" + name, "vm": "/x/" + name, "mode": "same",
                                    "vm_sha256": _sha256_file(p), "vm_bytes": os.path.getsize(p)})
            manifest = {"files": entries}
        with open(os.path.join(tools, "deployment-manifest.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    return root


def reds(repo):
    v, _ = evaluate(repo)
    return sorted(set(k for k, _ in v)), v


def _fixture_fingerprint(root):
    """夹具整棵（相对路径 ＋ 内容）的指纹：用来判"改坏到底改上了没有"。"""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            p = os.path.join(dirpath, name)
            h.update(os.path.relpath(p, root).replace(os.sep, "/").encode("utf-8"))
            h.update(b"\0")
            with open(p, "rb") as f:
                h.update(f.read())
            h.update(b"\0")
    return h.hexdigest()


def self_test(sandbox_root):
    """每个用例全新一份夹具（反例不许互相污染）；每条判据：正控必绿、反例必红。"""
    os.makedirs(sandbox_root, exist_ok=True)
    fails = []
    n = [0]

    # 正控夹具的指纹：每个反例都必须**真的与它不同**，否则就是"改坏没生效"
    # （★ 2026-10-05 实测踩到：`GOOD_READ` 里写的是 `project "$WHICH"`，
    #   而反例去替换 `project visual` ⇒ **一个字符都没改**，用例却"看着过了"。）
    _ctl = tempfile.mkdtemp(dir=sandbox_root)
    os.makedirs(os.path.join(_ctl, "src"), exist_ok=True)
    build_fixture(_ctl)
    CONTROL_FP = _fixture_fingerprint(_ctl)
    shutil.rmtree(_ctl, ignore_errors=True)

    def case(name, want_red, expect_changed=True, **kw):
        n[0] += 1
        root = tempfile.mkdtemp(dir=sandbox_root)
        os.makedirs(os.path.join(root, "src"), exist_ok=True)
        build_fixture(root, **kw)
        fp = _fixture_fingerprint(root)
        got, detail = reds(root)
        ok = (got == sorted(set(want_red)))
        if expect_changed and fp == CONTROL_FP:
            ok = False
            print("  [FAIL] %-28s ★反例与正控**逐字节相同** ⇒ 改坏没生效（不是判据过了）" % name)
            fails.append(name)
            shutil.rmtree(root, ignore_errors=True)
            return
        tag = "PASS" if ok else "FAIL"
        print("  [%s] %-28s 期望红=%s 实得红=%s" % (tag, name, sorted(set(want_red)), got))
        if not ok:
            fails.append(name)
            for k, why in detail:
                print("          %s: %s" % (k, why))
        shutil.rmtree(root, ignore_errors=True)

    print("== projection_guard --self-test ==")
    print("正控（该绿时必须绿）:")
    # ★ 这一格与 VM 上真件同形（`cat "$LOCK"`／`cat /proc/<pid>/comm`）⇒ **不许判红**：
    #   它是"存活标记"读法，不是"缓存／位点／账本字节"。第一版判据在这里是假红（G18）。
    case("正控：合规读侧件（含 cat $LOCK 存活标记）", [], expect_changed=False)

    print("反例（每条判据一个，形态＝真实违规形态）:")
    case("P1 界面面为空", ["P1"], read=None, write=None)   # 面空了就先判 P1（P10 在面非空时才判）
    case("P1 界面件是空文件", ["P1", "P5"], read="")   # 空文件也读不了投影 ⇒ P5 是同一个病带出来的，如实收
    case("P2 点击改发 change", ["P2"],
         write=GOOD_WRITE.replace('"kind":"act"', '"kind":"change"'))
    case("P2 写路径被删掉", ["P2"], write="# 只剩注释\nset -u\nexit 0\n")
    case("P3 加一行 cat 缓存", ["P3"],
         read=GOOD_READ.replace('WHICH="${1:-visual}"', 'WHICH="${1:-visual}"\ncat /var/lib/world-ui/last'))
    case("P3 加一行直读账本字节", ["P3"],
         read=GOOD_READ.replace('WHICH="${1:-visual}"', 'WHICH="${1:-visual}"\ntail -1 "$LEDGER"'))
    case("P3 加一行落盘重定向", ["P3"],
         read=GOOD_READ.replace('WHICH="${1:-visual}"', 'WHICH="${1:-visual}"\nprintf x > /var/lib/world-ui/last'))
    case("P3 加一行 open 写文件", ["P3"],
         write=GOOD_WRITE + "\npython3 -c \"open('/var/lib/world-ui/last','w').write('1')\"\n")
    case("P4 投影名不在可达集", ["P4"], read=GOOD_READ.replace(":-visual", ":-table"))
    case("P4 点名非投影臂 check", ["P4"], read=GOOD_READ.replace(":-visual", ":-check"))
    case("P4 可达名解析失败", ["P4"], main="fn cmd_project() {}\n")
    case("P5 删掉离线出口（注释仍在）", ["P5"],
         read=GOOD_READ.replace("printf '离线\\n'", "printf '上次的读数\\n'"))
    case("P6 账本 stat 换成别的路径", ["P6"],
         read=GOOD_READ.replace('[ -r "$LEDGER" ] ||', "[ -r /nonexistent ] ||"))
    case("P7 写侧改回内核口", ["P7"],
         write=GOOD_WRITE.replace("omarchy.sock", "world.sock"))
    case("P8 请求体自称 actor", ["P8"],
         write=GOOD_WRITE.replace('{"kind":"act","body":{',
                                  '{"kind":"act","actor":"world://presence/omarchy","body":{'))
    case("P9 不问世界就发", ["P9"],
         write=GOOD_WRITE.replace('desc=$(/usr/bin/world-core --ontology /etc/world-core/ontology.json \\\n'
                                  '        --policy /etc/world-core/policy.json describe 2>/dev/null) || exit 3\n'
                                  'case "$desc" in *notice.mute*) : ;; *) exit 4 ;; esac\n',
                                  'desc="notice.mute"\n'))
    # P10 三例：同源登记却对不上／待部署却已同源（清单过期）／界面件没进清单
    case("P10 same 登记与仓内不符", ["P10"],
         manifest={"files": [{"host": "scripts/release/world-projection.sh", "vm": "/x/p", "mode": "same",
                              "vm_sha256": "0" * 64, "vm_bytes": 1},
                             {"host": "scripts/release/world-toggle-mute.sh", "vm": "/x/m", "mode": "same",
                              "vm_sha256": _sha256_of_text(GOOD_WRITE), "vm_bytes": 1}]})
    case("P10 pending 却已同源（清单过期）", ["P10"],
         manifest={"files": [{"host": "scripts/release/world-projection.sh", "vm": "/x/p", "mode": "pending",
                              "vm_sha256": _sha256_of_text(GOOD_READ), "vm_bytes": 1},
                             {"host": "scripts/release/world-toggle-mute.sh", "vm": "/x/m", "mode": "pending",
                              "vm_sha256": "0" * 64, "vm_bytes": 1}]})
    case("P10 界面件没进清单", ["P10"],
         manifest={"files": [{"host": "scripts/release/world-projection.sh", "vm": "/x/p", "mode": "same",
                              "vm_sha256": _sha256_of_text(GOOD_READ), "vm_bytes": 1}]})

    total = n[0]
    print("== 自证结论：%d 例，%d 例不符 ==" % (total, len(fails)))
    if fails:
        print("   未过：" + "、".join(fails))
        return 1
    print("   （正控 1 ＋ 反例 %d；每条反例只让【目标】判据变红 —— 唯一例外：`P1 界面件是空文件`"
          "同时带出 P5，那是同一个病，已如实收进期望值）" % (total - 1))
    return 0


# ─────────────────────────── 入口 ───────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description="界面／投影面判据（P1–P10）")
    ap.add_argument("--repo", default="", help="world-core 树（缺省＝从本脚本位置上溯）")
    ap.add_argument("--sandbox", default="", help="--self-test 的夹具根（缺省＝进程私有临时目录）")
    ap.add_argument("--self-test", action="store_true", help="先咬自己：正控必绿、每条反例必红")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args(argv)

    if args.self_test:
        sandbox = args.sandbox or tempfile.mkdtemp(prefix="projguard-")
        try:
            return self_test(sandbox)
        finally:
            if not args.sandbox:
                shutil.rmtree(sandbox, ignore_errors=True)

    repo = args.repo or find_repo(os.path.dirname(os.path.abspath(__file__)))
    if not repo or not os.path.isdir(repo):
        print("用法错误：找不着 world-core 树（用 --repo 指）", file=sys.stderr)
        return 2

    v, notes = evaluate(repo)
    if args.json:
        print(json.dumps({"repo": repo, "red": [{"rule": k, "why": w} for k, w in v],
                          "notes": notes}, ensure_ascii=False, indent=2))
    else:
        print("== projection_guard（界面／投影面）==")
        print("  树   : %s" % repo)
        for p in ui_files(repo):
            print("  界面件: %s" % os.path.relpath(p, repo))
        for note in notes:
            print("  [WEAK] %s" % note)
        if not v:
            print("  ✅ 十条判据全过（P1 面非空／P2 只发 act／P3 不碰文件／P4 名字 ⊆ 投影名／"
                  "P5 有离线出口／P6 读前判账本可读／P7 走界面自己的口／P8 身份不自称／"
                  "P9 可点项问世界／P10 部署清单自洽）")
            print("  ⚠ 本件不含 VM：仓内件与 VM 件是否同一份，本件读不到")
        for k, w in v:
            print("  [RED] %s %s" % (k, w))
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
