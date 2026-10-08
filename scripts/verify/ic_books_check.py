#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""接口契约门禁：**模块节齐否 · 每节要点齐否 · 与模块登记表同源否**，缺一即红。

为什么有它：R4S 第 2 轮实测「删掉 `WC-IC-M03` 一册 ⇒ `check.sh` 与六个门禁**零反应**」——
即模块契约在库内**没有任何会红的判据**（"零门禁覆盖"）。这条闸的全部意义就是
**「某一模块的契约没了，必须有人喊」**。

**2026-09-27 改（"并册"连带）**：`WC-IC-M01`–`M10` **十一册已并入 `WC-IC-001` 一册**
（每模块一节 `§5.1`–`§5.10`，节号沿用模块号）。故「契约落点」由**分册文件**改为
**`WC-IC-001` 里该模块的节**；**三条判据的强度一条未降**，只是把"册"读成"节"。

判据（就三条，任一不满足 ⇒ rc=1）：
  ① **模块节齐**：`设计-WC-IC-001-v0.1.md` 里**含模块号的节标题**的模块号集合
     == `WC-MODREG-001` §2 登记表的模块号集合（谁少一节谁被点名）；
  ② **要点齐**：每个模块的节内，六项标签「提供者／输入／输出／异常与错误码／不变量／判据」
     **逐项非空**，且该节含「生效即冻结」字样（并册后这三个字移到节里，判据不放松）；
  ③ **依赖列逐边一致**：每个模块节内 `源码位置与依赖：…（依赖：…）` 的边集
     与 `WC-MODREG-001` §2 登记表「依赖模块」列的边集**逐模块逐边**相等。

2026-09-27 加（`W-08`，**属门禁判据扩张 ⇒ 登记待 R5，见 `WC-RV-R4-001` §九**）：
  ④ **登记集不得为空**（原来 `if reg and set(...) != reg` 在 `reg==空集` 时**静默跳过**
     —— 登记表被清空/格式被改到正则不命中，门禁反而**更绿**）；
  ⑤ **依赖列逐边比对**（见上 ③；原来只比模块号**集合**，改依赖列 ⇒ rc 仍 0）。

2026-09-27 加（`W-07`，**补偿判据；默认关闭**，需 `IC_QUOTA_STRICT=1` 才生效
——"行数额度"废弃后，"宿主字节骤降"没有判据：删 500 行仍 rc=0）：
  ⑥ **`WC-IC-001` 的宿主字节不得低于并册时基线的 70%**（非行数上限的补偿判据）。
     默认关闭的理由：这是一条**新增门禁强度**，按本项目纪律**不得静默实施**；
     改法＋代价＋可回退见 `WC-RV-R4-001` §九，**是否把默认翻成开启待人裁（R5）**。
     ⚠ **口径变更（2026-09-27）**：原来逐**分册**比冻结字节（一张硬编码的 9 行表）；
     并册后逐册表**没有对应物**，故改为**比并册书的宿主字节**，基线 = 被并入 11 册的字节**之和**
     （`19795`；来源与算法逐条写在 `MERGED_BOOK_BASELINE_BYTES` 的注释里，**不是展示数据**）。

用法：`python3 scripts/verify/ic_books_check.py [--repo-root .]`；
`--self-test` 自证（**删掉某一模块的契约节必红**、恢复必绿，另附 ④⑤⑥ 三条各自的反例）。
"""
import io
import os
import re
import sys
import tempfile

#: 六项要点标签（节内表首列；`判据（可机械核对）` 这类后缀由前缀归一化匹配吸收）。
LABELS = ["提供者", "输入", "输出", "异常与错误码", "不变量", "判据"]
#: 模块契约节必须自带的冻结声明（并册后它在**节内**，不在册头部横幅里）。
FREEZE_MARK = "生效即冻结"
#: 模块契约节必须自带的**修订落点声明**（并册前各册头横幅逐字写「本册…生效即冻结」，
#: 并册时把该声明**逐节**下沉；「契约变更记录」属修订记录，按纪律已移出正文、改在 git 提交信息里留痕）。
PROCESS_MARK = "本册不设修订记录"
#: 与 `PROCESS_MARK` 同一条声明的另一半（两段必须同时在节内）。
FREEZE_IN_SECTION = "生效即冻结"

#: 接口契约书（一册）相对仓库根的路径。
#: ★ 2026-10-07 修（现取病灶）：原来是**布局迁移前**的 `docs/S2-设计/…`——`docs/` 已整树搬进
#:   工程域 `ninedim/`（权威：`ninedim/_索引-工程域结构与命名.md`）⇒ `find_root()` 找不到书、
#:   判据落进"材料缺失"分支而**判不了**（假红／空转）。现取真身路径。
BOOK_REL = os.path.join("ninedim", "01-意图环", "03-设计", "设计-WC-IC-001-v0.1.md")
#: 模块登记表相对仓库根的路径。
REG_REL = os.path.join("ninedim", "01-意图环", "03-设计", "设计-WC-MODREG-001-v0.1.md")

#: **并册书宿主字节的基线**（`W-07` 补偿判据的基准，不是展示数据）。
#: 算法：被并入的 **11 册**在并册前一刻的字节数**之和**（`git cat-file -s`，提交 `1d10ef0`，逐条可复算）：
#:   `设计-WC-IC-001-v0.1.md` 93590 ＋ `WC-IC-M01` 2361 ＋ `M02` 2310 ＋ `M03` 2360 ＋ `M04` 2359
#:   ＋ `M05` 2360 ＋ `M06` 2340 ＋ `M07` 2343 ＋ `M08` 2396 ＋ `M09` 2321 ＋ `M10` 3672 = **118412**
#: 并册只删各册的「契约变更记录」节与册头部横幅（共约 9.5 KB），故书的字节数**只会略低于该和**；
#: 低于它的 70% 即判「内容被大幅删除」。
MERGED_BOOK_BASELINE_BYTES = 118412
#: 补偿判据的下限比例（宿主字节 / 基线字节）。低于它即判 ERROR（`W-07`）。
QUOTA_FLOOR = 0.70

#: 模块契约节的标题形态：`### §5.1 \`M01\` 本体与词表（Ontology/Vocab） —— 模块接口契约`。
#: 判据取「**节标题里含模块号**」（含反引号包裹，避免 `M1` 命中 `M10` 这类子串误配）。
def _section_re(mid):
    return re.compile(r"(?m)^#+\s*§5\.\d+\s+`" + re.escape(mid) + r"`")


def _any_section_re():
    return re.compile(r"(?m)^#+\s*§5\.(\d+)\s+`(M\d{2})`")


def read_text(p):
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def find_root(arg=None):
    """仓库根：给了 `--repo-root` 就用它，否则从本脚本位置向上找含契约书的目录。"""
    if arg:
        return os.path.abspath(arg)
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.dirname(here)                     # ``
    for c in (cand, os.path.dirname(cand), here):
        if os.path.isfile(os.path.join(c, BOOK_REL)):
            return c
    return cand


def book_sections(root):
    """`WC-IC-001` → {模块号: 节文本}（按 `### §5.k \\`M<NN>\\`` 切节）。"""
    p = os.path.join(root, BOOK_REL)
    if not os.path.isfile(p):
        return None, {}
    text = read_text(p)
    hits = list(_any_section_re().finditer(text))
    out = {}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out.setdefault(m.group(2), text[m.start():end])
    return text, out


def registry_modules(root):
    """`WC-MODREG-001` §2 模块登记表的模块号集合。"""
    p = os.path.join(root, REG_REL)
    ids = set()
    if os.path.exists(p):
        for m in re.finditer(r"(?m)^\|\s*\*{0,2}(M\d{2})\*{0,2}\s*\|", read_text(p)):
            ids.add(m.group(1))
    return ids


def _deps_of_cell(cell):
    """从依赖单元格里取出模块号边集（`**无**` / `—` ⇒ 空集）。"""
    return set(re.findall(r"M\d{2}", cell or ""))


def registry_edges(root):
    """`WC-MODREG-001` §2 登记表「依赖模块」列 → {模块号: 依赖边集}（`W-08` ④⑤）。

    只在 `## §2 模块登记表` 这一节内取表，避免误取附录 A 的旧表
    （两表口径不同，混取会让判据失去意义）。
    """
    p = os.path.join(root, REG_REL)
    if not os.path.exists(p):
        return {}
    sec = re.search(r"(?ms)^##\s*§2\s*模块登记表(.*?)(?=^##\s|\Z)", read_text(p))
    if not sec:
        return {}
    out = {}
    for line in sec.group(1).split("\n"):
        m = re.match(r"^\|\s*\*{0,2}(M\d{2})\*{0,2}\s*\|(.*)$", line)
        if not m:
            continue
        cells = m.group(2).split("|")
        if len(cells) < 5:
            continue
        # 表头为「模块号|模块名|职责|源码路径|提供接口|依赖模块」⇒ 依赖列 = 第 6 格
        # （`cells` 已去掉行首那一格，故下标 4）。
        out[m.group(1)] = _deps_of_cell(cells[4])
    return out


def section_edges(text):
    """节内 `源码位置与依赖：…（依赖：…）` → 依赖边集（`W-08` ⑤）。找不到返回 `None`。"""
    m = re.search(r"源码位置与依赖[：:](.*)", text or "")
    if not m:
        return None
    return _deps_of_cell(m.group(1))


def check(root):
    """三条判据 → `(节数, 登记数, 问题列表)`。"""
    bad = []
    text, secs = book_sections(root)
    reg = registry_modules(root)

    # ① 模块节齐（含"书不存在"这一情形：**不得静默通过**）
    if text is None:
        bad.append("接口契约书 `%s` 不存在 —— 模块契约的落点整册缺失"
                   % BOOK_REL.replace("\\", "/"))
    elif not secs:
        bad.append("`%s` 里**一个模块契约节都取不到**（标题形态被改/节被删）："
                   "模块契约的落点不得因取不到而静默通过" % BOOK_REL.replace("\\", "/"))

    # ④ 登记集为空即红（`W-08`）：原来 `if reg and …` 会在 `reg` 为空时**静默跳过**
    #    整套集合判据 —— 把登记表清空或改到正则不命中，门禁反而更绿。
    if not reg:
        bad.append(
            "模块登记表**登记集为空**：`WC-MODREG-001` §2/附录 A 里一个 `| M0x |` 行都取不到"
            "（表被清空、格式被改或文件缺失）—— 空登记表不得被当作「一致」"
        )
    elif secs:
        miss = sorted(reg - set(secs))
        extra = sorted(set(secs) - reg)
        if miss:
            bad.append("缺少模块契约节（模块登记表有、`WC-IC-001` 里没有）：%s" % ",".join(miss))
        if extra:
            bad.append("多余模块契约节（`WC-IC-001` 里有、登记表无）：%s" % ",".join(extra))

    # ⑤ 依赖列**逐边**比对（`W-08`）：原来只比模块号集合，改依赖列 ⇒ rc 仍 0。
    edges_reg = registry_edges(root)
    if not edges_reg:
        bad.append(
            "登记表「依赖模块」列**一条边都取不到**（§2 表结构被改或依赖列被删）"
            "—— 依赖判据不得因取不到而静默通过"
        )
    for mid, sec in sorted(secs.items()):
        # ② 节内六项要点逐项非空 ＋ 生效即冻结
        for lab in LABELS:
            m = re.search(r"(?m)^\|\s*" + re.escape(lab) + r"[^|]*\|([^|]*)\|", sec)
            if not m or not m.group(1).strip() or m.group(1).strip() in ("—", "-"):
                bad.append("%s 节的接口契约要点为空或缺：%s" % (mid, lab))
        if FREEZE_MARK not in sec:
            bad.append("%s 节缺「%s」声明" % (mid, FREEZE_MARK))
        if PROCESS_MARK not in sec:
            bad.append("%s 节缺「%s」声明（并册前它在册头横幅里，逐字迁移后必须在节内）"
                       % (mid, PROCESS_MARK))
        # ③ 依赖边逐边一致
        if edges_reg and mid in edges_reg:
            got = section_edges(sec)
            if got is None:
                bad.append("%s 节缺「源码位置与依赖」行 —— 依赖边无法比对" % mid)
            elif got != edges_reg[mid]:
                bad.append(
                    "%s 依赖边与登记表不一致：节内={%s} 登记表={%s}"
                    % (mid, ",".join(sorted(got)) or "无", ",".join(sorted(edges_reg[mid])) or "无")
                )
        elif edges_reg and text is not None:
            bad.append("%s 在登记表的「依赖模块」列里没有行 —— 依赖边无法比对" % mid)
    return len(secs), len(reg), bad


def quota_check(root):
    """⑥ 并册书宿主字节 / 基线 < `QUOTA_FLOOR` ⇒ ERROR（`W-07` 补偿判据）。

    **默认不启用**：只有 `IC_QUOTA_STRICT=1` 时才返回问题。
    理由：这是新增门禁强度，按纪律不得静默实施（改法＋代价＋可回退见 R4 记录 §九）。
    """
    if os.environ.get("IC_QUOTA_STRICT") != "1":
        return None
    p = os.path.join(root, BOOK_REL)
    if not os.path.exists(p):
        return ["`%s` 不存在 —— 宿主字节补偿判据无法评估（按 ERROR 处理）"
                % BOOK_REL.replace("\\", "/")]
    host = os.path.getsize(p)
    floor = int(MERGED_BOOK_BASELINE_BYTES * QUOTA_FLOOR)
    if host < floor:
        return ["`%s` 宿主字节 %d < 并册基线 %d 的 %.0f%%（下限 %d）—— 内容被大幅删除"
                % (BOOK_REL.replace("\\", "/"), host, MERGED_BOOK_BASELINE_BYTES,
                   QUOTA_FLOOR * 100, floor)]
    return []


# ────────────────────────── 自证 ──────────────────────────
def _drop_section(text, mid):
    """把某个模块的整节（标题 → 下一个 §5.x 标题之前）删掉；找不到返回 `None`。"""
    m = _section_re(mid).search(text)
    if not m:
        return None
    nxt = _any_section_re().search(text, m.end())
    return text[:m.start()] + (text[nxt.start():] if nxt else "")


def self_test():
    """自证：删掉某一模块的契约节必红、恢复必绿；④⑤⑥ 各一条反例。"""
    here = os.path.dirname(os.path.abspath(__file__))
    # ★ 2026-10-07 修（现取病灶）：本文件在 `scripts/verify/` ⇒ 仓根＝**上两级**；
    #   原来只上溯一级（得到 `scripts/`）⇒ 自证读不到材料、直接走"材料缺失"分支（自证从未真正跑过）。
    src_root = os.path.dirname(os.path.dirname(here))       # 仓根
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        # ★ 夹具目录必须与 `BOOK_REL`／`REG_REL` **同形**（否则自证读的是"材料缺失"那条岔路）
        d = os.path.join(tmp, os.path.dirname(BOOK_REL))
        os.makedirs(d)
        for rel in (BOOK_REL, REG_REL):
            s = os.path.join(src_root, rel)
            if not os.path.exists(s):
                print("[self-test] *材料缺失：%s（自证无法进行）" % rel)
                return 1
            io.open(os.path.join(d, os.path.basename(rel)), "w",
                    encoding="utf-8", newline="\n").write(read_text(s))

        book = os.path.join(d, os.path.basename(BOOK_REL))
        reg = os.path.join(d, os.path.basename(REG_REL))
        keep_book = io.open(book, encoding="utf-8").read()
        keep_reg = io.open(reg, encoding="utf-8").read()

        n0, r0, b0 = check(tmp)

        # ── 反例（本条闸的本命）：删掉某一模块的契约节 ⇒ 必须报「缺少模块契约节(Mxx)」──
        # ⚠️ 夹具**不许写死模块号**：写死会让"新增模块"或"节号调整"时自证自己失效
        #    （上一版的教训：写死 `range(1,10)`，新增第十册后自证自红）。
        #    故取**当前书里实际存在的第一个模块节**当受害者，并逐字报出抽掉了哪一节。
        mids = sorted({m.group(2) for m in _any_section_re().finditer(keep_book)})
        victim = mids[0] if mids else None
        red_missing = False
        if victim is None:
            failures.append("自证材料问题：书里取不到任何 `§5.x` 模块节标题")
            print("[self-test] *材料脱节：书里取不到任何 `§5.x` 模块节标题")
        else:
            cut = _drop_section(keep_book, victim)
            if cut is None:
                failures.append("自证材料问题：按 `%s` 找不到可删的节（锚与节标题脱节）" % victim)
                print("[self-test] *材料脱节：按 `%s` 找不到可删的节" % victim)
            else:
                io.open(book, "w", encoding="utf-8", newline="\n").write(cut)
                n1, r1, b1 = check(tmp)
                red_missing = any("缺少模块契约节" in x and victim in x for x in b1)
                print("[self-test] 删掉 `%s` 的契约节 ⇒ 模块节 %d（原 %d）/ 登记 %d / 问题 %d，"
                      "含「缺少模块契约节(%s)」= %s" % (victim, n1, n0, r1, len(b1), victim, red_missing))
                io.open(book, "w", encoding="utf-8", newline="\n").write(keep_book)
                n2, r2, b2 = check(tmp)
                print("[self-test] 恢复 ⇒ 模块节 %d、问题 %d（应回到 %d）" % (n2, len(b2), len(b0)))
                if len(b2) != len(b0):
                    failures.append("恢复后问题数未回到初值：%d → %d" % (len(b0), len(b2)))
                if not red_missing:
                    failures.append("删掉 `%s` 的契约节未变红或未点名" % victim)

        # ── 反例④：打散登记表 ⇒ 取不到 M0x 行 ──
        scattered = re.sub(r"(?m)^\|\s*\*\*(M\d{2})\*\*", r"| x\1", keep_reg)
        if scattered == keep_reg:
            failures.append("自证材料问题：打散登记表时一条登记行都没命中（正则与登记表格式脱节）")
        io.open(reg, "w", encoding="utf-8", newline="\n").write(scattered)
        _, _, b_empty = check(tmp)
        red_empty = any("登记集为空" in x for x in b_empty)
        io.open(reg, "w", encoding="utf-8", newline="\n").write(keep_reg)

        # ── 反例⑤：依赖列逐边比对——把 M06 那一节的依赖改成 M09 ⇒ 必须报不一致 ──
        edges = registry_edges(src_root)
        tgt = None
        for mid in sorted(edges):
            m = _section_re(mid).search(keep_book)
            if not m:
                continue
            nxt = _any_section_re().search(keep_book, m.end())
            sec = keep_book[m.start():(nxt.start() if nxt else len(keep_book))]
            mm = re.search(r"(源码位置与依赖[：:][^\n]*)", sec)
            if mm and edges[mid]:
                tgt = (mid, mm.group(1))
                break
        red_edge = False
        if tgt is None:
            failures.append("自证材料问题：找不到一个「节内有依赖行且登记表有边」的模块做反例⑤")
        else:
            mid, line = tgt
            newline = re.sub(r"（依赖[：:][^）]*）", "（依赖：`M09`）", line)
            if newline == line:
                failures.append("自证材料问题：反例⑤ 的替换没生效（依赖行形态与预期不符）：%r" % line)
            else:
                io.open(book, "w", encoding="utf-8", newline="\n").write(
                    keep_book.replace(line, newline, 1))
                _, _, b_edge = check(tmp)
                red_edge = any("依赖边与登记表不一致" in x and mid in x for x in b_edge)
                io.open(book, "w", encoding="utf-8", newline="\n").write(keep_book)
        print("[self-test/W-08④] 打散登记表 ⇒ 含「登记集为空」= %s" % red_empty)
        print("[self-test/W-08⑤] 改 %s 节的依赖边 ⇒ 含「依赖边与登记表不一致(%s)」= %s"
              % (tgt[0] if tgt else "?", tgt[0] if tgt else "?", red_edge))

        # ── 反例⑥：补偿判据（默认关闭）：并册书宿主字节砍半 ⇒ 只有开启时才红 ──
        raw = keep_book.encode("utf-8")
        io.open(book, "wb").write(raw[: len(raw) // 2])
        os.environ.pop("IC_QUOTA_STRICT", None)
        off = quota_check(tmp)
        os.environ["IC_QUOTA_STRICT"] = "1"
        on = quota_check(tmp)
        os.environ.pop("IC_QUOTA_STRICT", None)
        # `quota_check` 在**默认关闭**时返回 `None`（不是空表）——两者含义不同：
        # `None` = 判据未启用；`[]` = 启用且通过。反例要的是"关时不报、开时才报"。
        red_quota = (off is None) and bool(on) and any("宿主字节" in x for x in on)
        print("[self-test/W-07⑥] 并册书宿主字节砍半 ⇒ 默认关闭时判据未启用=%s；"
              "IC_QUOTA_STRICT=1 时报「宿主字节」=%s（砍半后 %d 字节 / 下限 %d）"
              % (off is None, red_quota,
                 os.path.getsize(os.path.join(tmp, BOOK_REL)),
                 int(MERGED_BOOK_BASELINE_BYTES * QUOTA_FLOOR)))
        io.open(book, "w", encoding="utf-8", newline="\n").write(keep_book)   # 恢复（夹具不互相污染）

        print("[self-test] 初始：模块节 %d / 登记 %d / 问题 %d" % (n0, r0, len(b0)))
        if not red_empty:
            failures.append("反例④未变红：打散登记表后没有报「登记集为空」")
        if tgt is not None and not red_edge:
            failures.append("反例⑤未变红：改依赖边后没有报「依赖边与登记表不一致」")
        if not red_quota:
            failures.append("反例⑥未变红：IC_QUOTA_STRICT=1 时砍半宿主字节没有报「宿主字节」")
        if len(b0) != 0:
            failures.append("正控失败：当前库内契约书本身就 %d 个问题" % len(b0))
            for x in b0:
                print("       · " + x)
        if failures:
            print("  => 自证不通过：%s" % "；".join(failures))
            print("  => 按本项目口径：**这条守卫是装饰，拒绝合入**。")
            return 1
    print("  => 自证通过：**删掉某一模块的契约节必红**（本命）＋ ④⑤⑥ 各一条反例必红 ＋ 恢复后回到初值。")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = None
    for i, a in enumerate(argv):
        if a == "--repo-root" and i + 1 < len(argv):
            root = argv[i + 1]
    root = find_root(root)
    n, r, bad = check(root)
    qbad = quota_check(root)
    if qbad:
        bad = bad + ["[补偿判据 IC_QUOTA_STRICT=1] " + x for x in qbad]
    if bad:
        print("[FAIL] 接口契约门禁：模块节 %d / 登记 %d / 问题 %d" % (n, r, len(bad)))
        for x in bad:
            print("        " + x)
        return 1
    quota_note = ("补偿判据已启用（IC_QUOTA_STRICT=1）" if qbad is not None
                  else "补偿判据未启用（IC_QUOTA_STRICT≠1，默认关闭）")
    print(
        "[ OK ] 接口契约门禁：模块节 %d == 登记 %d（`%s` 一册，每模块一节），"
        "六项要点与「生效即冻结」齐备，依赖列逐边一致；%s"
        % (n, r, BOOK_REL.replace("\\", "/"), quota_note)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
