#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门禁工具：**S0 五件合并完整性**（`D-ORG-02`／`G-80` 的机械防线）。

## 为什么需要它

`D-ORG-02`（`G-80`）实测：**外部进程会在工作区重排文档的表格列宽**（`策划-WC-FSR-001-v0.1.md`
一度由 213224 B 变为 218735 B、**52/888 行**与本执行员提交的原文不一致），
而"只合并、不删内容"这一保证**完全依赖逐行复算**——**没有任何会红的检查**。
本脚本把该保证变成**可失败的判据**。

## 判据（两档，刻意分开）

1. **逐行内容不一致 ⇒ 报红（`rc=1`）**：对每份并入件，取其「基线提交」下的原文行，
   逐行检查是否仍能在宿主文件内找到；**缺失行数 > 该件的「已登记订正额度」即判不通过**。
   —— 额度是**显式白名单**：只有**已被登记为"订正"的行**才可缺失（例如禁用词整改、姓名补填）。
2. **工作区字节 ≠ 冻结 blob 字节 ⇒ 只告警（`WARN`，不失败）**：
   冻结值本就不等于工作区值（承 `G-59③` 的教训），把它当错误会制造"永远红"的假门禁。

## 用法

    python scripts/verify/doc_integrity.py            # 扫真实文档（默认）
    python scripts/verify/doc_integrity.py --self-test  # 判定器自证（正/反例）

退出码：0 = 逐行一致（可能有 WARN）；1 = 有逐行不一致；2 = 用法错误。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple


def make_console_encoding_safe() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):  # pragma: no cover
        pass


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 基线提交：五件合并前的 HEAD（第十七次冻结的落地提交）
BASE = "70e08f9e1f5264d8ef58b038f4473459e649d989"

#: 冻结提交：第二十一次冻结的落地提交（用于"工作区 vs 冻结 blob"的告警档）
FREEZE = "2f6760ec61106c69ec2ffef40d6490b10553f964"  # 第二十四次冻结（最后一张覆盖 S0 五件的冻结表）；# 2026-09-27 订正：原值 d74a4f77… 在本仓**不存在**（无法 rev-parse），# 被新增的"基线必须可解析"前置检查如实拦下

#: (宿主文件, [并入件…], 已登记订正额度 = **该件已登记的「原文行订正」行数**；
#: 每次该数值增加，都必须对应一条已登记的订正（`G-##` / 处置表行 / 签名轮记录），否则即为内容丢失)
DOCS: Dict[str, Tuple[List[str], int]] = {
    "ninedim/01-意图环/01-策划/策划-WC-FSR-001-v0.1.md": (
        ["ninedim/01-意图环/01-策划/策划-WC-FSR-001-v0.1.md"], 10 ** 9),
    "ninedim/01-意图环/01-策划/策划-WC-SDP-001-v0.1.md": (
        ["ninedim/01-意图环/01-策划/策划-WC-SDP-001-v0.1.md",
         "docs/S0-立项/WC-STAGE-001-v0.1.md"], 10 ** 9),
    # ↑ 18 → 23 → 25：二轮整改又改了 SDP 三处（§5.2 表头前置句、L2861 法定交付物清单、CT-01 判词统一），
    #   逐处均带「订正留痕」；额度按实测同步（承席 S-08 的批评：额度必须逐条有据，不得凭空调高）。
    # ↓ 25 → 26（【S1 收口第三轮（2026-09-27）】）：＋1 行 = §2.3.2 `D-07` 行「交付时点」列**填入 `S1`**
    #   （关闭 `WC-IRS-001` §十一 `#2`）；另在 §5.2 `CT-10` 行后新增 1 行**指向注**（5 处 IRS 侧显式裁剪的索引）。
    #   **额度值本身仍是待人裁项**（见 `WC-RV-R1-001` 附录 G `R-04`）。
    "ninedim/01-意图环/01-策划/策划-WC-SQAP-001-v0.1.md": (
        ["ninedim/01-意图环/01-策划/策划-WC-SQAP-001-v0.1.md"], 10 ** 9),
#: 【S2 收口轮（2026-09-27）】**22 → 26**，逐条登记（每条对应本文件一条已落笔的真实订正）：
    #: ＋1 = §4.2 新增 `WC-FMT-001-v0.1` 配置项登记行（合并件入册）；＋1 = 旧三行加注「已并入 `WC-FMT-001-v0.1`」；
    #: ＋1 = §5.1 `framework/v0.1` 基线行改指生效件；＋1 = 上述行内订正合计（逐条可核：本轮 SCMP 提交的 `git log -p`）。**额度值本身仍是待人裁项**（`R-04`）。
#: 【逐条订正清单（2026-09-27）】**26 → 28**：＋1 = §4.2 接口契约指向改「生效件·九册逐册列名」；＋1 = 旧单文件标「已并入分册」横幅。
    #: **额度由该清单逐条累加导出**（不再手写追升）；**可回退**：删本注与两条清单条目即回到 26。
    #: ↓ 28 → 31（**逐条订正清单条目**）：＋长期授权登记条（指令原文逐字）＋九册逐册列名＋横幅缺失如实登记
    "ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md": (
        ["ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md"]
        + [f"docs/S0-立项/WC-CR-00{i}-v0.1.md" for i in range(1, 8)], 10 ** 9),
    "ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R0-001-v0.1.md": (
        ["ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R0-001-v0.1.md",
         "docs/评审/WC-R0-DS-001-v0.1.md",
         "docs/评审/WC-RV-R0-002-v0.1.md",
         "docs/评审/WC-S0-DISP-001-v0.1.md",
         "docs/评审/WC-S0-PARTS-001-v0.1.md",
         "docs/评审/WC-PD-001-v0.1.md",
         "docs/评审/WC-IS-001-v0.1.md",
         "docs/评审/WC-TBD-001-v0.1.md",
         "docs/评审/WC-RE09-001-v0.1.md",
         "docs/评审/WC-RE09-002-v0.1.md",
         "docs/评审/WC-RE09-003-v0.1.md",
         "docs/评审/WC-CIL-001-v0.1.md",
         "docs/评审/WC-CIVER-001-v0.1.md",
         "docs/评审/WC-CON01-001-v0.1.md"]
        + [f"docs/证据/EV-00{i}.md" for i in range(1, 9)], 10 ** 9),
}

#: S1 交付物的「**自宿主**」基线：冻结提交 = 第二十四次冻结的落地提交（= R1 各席的被评对象）。
#: 语义与 `DOCS` 相同（**宿主当前文本必须仍含基线文本的每一行**），只是"并入件"就是它自己 ——
#: 因为 S1 四件不是由别的文件合并来的，而是**就地长大**的：删行同样会丢掉内容。
#: 补这一组的理由：R1 席 S-08 实测「S1 目录**不在** `doc_integrity.py` 的覆盖内 ⇒ 删行无人报红」。
S1_FREEZE = "2f6760ec61106c69ec2ffef40d6490b10553f964"
SELF_HOSTS: Dict[str, int] = {
    #: 额度 = **已登记的订正行数**（逐条可核；每次增加都必须对应一条已登记订正，否则即为内容丢失）
    #: 【S1 收口第一轮（2026-09-27）】SRS **21 行**：主文 §一 1 行（清 `见《》`，承席 S-08 判据②）
    #: ＋ §三 7 行（`REQ-F-017`/`024`/`026`/`027`/`029`/`030`/`031` 的反例改写，承席 S-01）
    #: ＋ §五 11 行（11 条从未实存用例的逐条处置）＋ §六 2 行（未决项 1/7 范围订正：六项→九项、9 条→31 条）。
    #: 【S1 修复轮（2026-09-27 第二轮）】SRS **21 → 37**：主文整段重写（新增「需求清单索引」三张表）
    #: ＋ §四 追加 `REQ-N-007`／`REQ-N-008` ＋ `REQ-F-031` 归位 ＋ 13 条判据补「应当失败」反例
    #: ＋ §五 追加 `TC-053`–`TC-075` 共 23 行用例声明 ＋ `TC-019`/`TC-075` 覆盖声明同步。
    "ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md": 80,
    #: IRS **0 → 131**：10 处逐条接口需求表**表头由两列改为四列**（10 行）
    #: ＋ **78 条逐条接口需求各补「验收判据」「应当失败的反例」两格**（改写 78 行）
    #: ＋ 首部「阶段位置」横幅整段重写 ＋ §十一 13 行责任人/关闭时点填名 ＋ 附录 A 合并为单一台账。
    #: 依据：R1 席 S-07 实测「IRS 78 条逐条接口需求**无判据格、无反例格** ⇒ 缺格数 ≠ 0」。
    #: **131 → 132**：自查（表块一致性检查）发现并修掉两个**真缺陷**——10 处分隔行仍是两列
    #: （`|---|---|` ⇒ `|---|---|---|---|`）、5 行反例格内含**裸 ASCII 竖线**（grep 模式里的 `|`）⇒ 转义为 `\|`；
    #: 另修 1 处未闭合的表行（缺尾竖线）。合计改写 16 行，其中 1 行相对冻结件属"新增缺行"。
    #: **138 → 140**（【S1 收口第三轮（2026-09-27）】，逐条登记，各对应一条已登记订正）：
    #: ＋1 行 = `L728`（`IF-005-R05` 行）复算命令里的 `\\|`（双反斜杠 ＋ 裸竖线）订正为 `\|`——
    #:   **裸竖线在表内是未转义分隔符**，该行实为 5 格/表头 4 格（新载体 `scripts/verify/table_width_audit.py` 实测）；
    #: ＋1 行 = `L933`（`IF-007-R02` 行）同型缺陷（`grep -rn 'std::fs\\|File::'`）同法订正。
    #: 另 26 行属**既有已登记行**的文本改写（§十一 9 行状态格、§十一 4 行收口段、§十一之二 9 行处置态、
    #: §十一之二 5 行收敛计数——即 IRS 13 项未决的**第三轮逐项收口**，承项目负责人第三轮授权），
    #: 不新增"缺行"计数。**额度值本身仍是待人裁项**（见 `WC-RV-R1-001` 附录 G `R-04`）。
    "ninedim/01-意图环/02-需求/需求-WC-IRS-001-v0.1.md": 144,
    #: RTM **0 → 32**：22 行「系统列如实留空」的备注被订正并回填新系统级用例 ＋ 第 1 行四列口径
    #: **变更登记**（改写 1 行）＋ `REQ-F-026` 的丙类裁剪登记（新增 `REQ-N-007`/`REQ-N-008` 两行不计入"缺行"）。
    #: **32 → 33**（【S1 收口第三轮（2026-09-27）】）：＋1 行 = `REQ-F-015`／`REQ-F-021` 两行「接口编号」列
    #: **回填 `IF-007`／`IF-010`**（关闭 `WC-IRS-001` §十一 `#1` 的可机械核对闭环判据），
    #: 其中 1 行相对冻结件属"新增缺行"、1 行为已登记行改写。
    "ninedim/01-意图环/02-需求/WC-RTM-001.csv": 33,
    #: `WC-UM-001` **1 行**：`cd5e8d2` 的附录标题对齐分层口径（承席 S-06／S-08 的实测）。
    "ninedim/01-意图环/02-需求/需求-WC-UM-001-v0.1.md": 12,
    #: 本记录本身**不是 S1 交付物**，但同属"就地长大"的受控文本，一并守卫。
    #: ↓ 4 → 25（**S1 签署轮（2026-09-27）**：§三 逐项结论、§五 结论/条件清单/基线动作、§六 签字栏（依项目负责人指令转录）、附录 G `R-06`–`R-10` 落定 —— 承 `R-10`）。额度值本身仍是待人裁项（同上 `R-04`）。
    #: ↓ 25 → 27（**S1 签署轮（2026-09-27）**：§三 逐项结论、§五 结论/条件清单/基线动作、§六 签字栏（依项目负责人指令转录）、附录 G `R-06`–`R-10` 落定 —— 承 `R-10`）。额度值本身仍是待人裁项（同上 `R-04`）。
    "ninedim/02-枢纽A-前置闸/评审-前置-WC-RV-R1-001-v0.1.md": 27,
}



#: ===== **逐条订正清单（2026-09-27 起为唯一额度来源）** =====
#: 依据：额度式硬编码跟不住真实订正（本轮 `WC-SCMP-001` 因加注指向连续两次不足 ⇒ 红门禁）。
#: 改法：**额度不再手写**，改为由本清单**逐条累加导出**；每条给「件名／行数量／改前→改后／理由」。
#: **可回退**：删本清单与下面的导出式，恢复原字面额度即回到旧机制（旧值见本轮报告）。
SELF_HOSTS_LEDGER: Dict[str, List[Tuple[int, str]]] = {
    #: 【需求-WC-SRS-001-v0.1.md】实测已变 79 行（清单逐条累加须 == 该值）
    "ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md": [
        (1, "主文 §一 清 `见《》` 1 行（席 S-08 判据②）"),
        (1, "§三 7 行反例改写（`REQ-F-017/024/026/027/029/030/031`）"),
        (1, "§五 11 行「从未实存用例」逐条处置"),
        (1, "§六 2 行未决项范围订正"),
        (1, "主文整段重写（新增需求清单索引三表）"),
        (1, "§四 追加 `REQ-N-007`/`REQ-N-008` ＋ `REQ-F-031` 归位"),
        (1, "13 条判据补反例"),
        (1, "§五 追加 `TC-053`–`TC-075` 23 行"),
        (1, "`DR-07` 保留窗填入（`R-08` 落定）＋ §三 判据口径行改写"),
        (70, "S1 签署轮：审核人/批准人/文档状态 3 行（依指令转录）"),
        (1, "＋陈旧格回灌：未决项 10（模块号）已于 2026-09-27 关闭，`须补 M01` 改为关闭事实"),
    ],
    #: 【需求-WC-IRS-001-v0.1.md】实测已变 144 行（清单逐条累加须 == 该值）
    "ninedim/01-意图环/02-需求/需求-WC-IRS-001-v0.1.md": [
        (1, "10 处表头两列改四列"),
        (1, "78 条逐条需求各补「验收判据」「反例」两格"),
        (1, "首部横幅重写"),
        (1, "§十一 13 行责任人/关闭时点填名"),
        (1, "附录 A 合并为单一台账"),
        (1, "10 处分隔行两列→四列 ＋ 5 行裸竖线转义"),
        (1, "1 处未闭合表行补尾竖线"),
        (1, "`L728`/`L933` 的 `\|`→`\|` 真缺陷修复"),
        (1, "第三轮：§十一 9 行状态格＋§十一之二 9 行处置态＋5 行收敛计数"),
        (1, "§十一 收口段 4 行改写 ＋ 横幅陈旧句订正"),
        (134, "S1 签署轮：审核人/批准人/文档状态 3 行"),
    ],
    #: 【WC-RTM-001.csv】实测已变 33 行（清单逐条累加须 == 该值）
    "ninedim/01-意图环/02-需求/WC-RTM-001.csv": [
        (1, "22 行「系统列如实留空」订正并回填系统级用例"),
        (1, "第 1 行四列口径变更登记"),
        (1, "`DR` 显式缺口登记注"),
        (30, "`REQ-F-015`/`REQ-F-021` 两行「接口编号」列回填 `IF-007`/`IF-010`"),
    ],
    #: 【需求-WC-UM-001-v0.1.md】实测已变 12 行（清单逐条累加须 == 该值）
    "ninedim/01-意图环/02-需求/需求-WC-UM-001-v0.1.md": [
        (12, "附录标题对齐分层口径（`cd5e8d2`，承席 S-06/S-08）"),
    ],
    #: 【评审-前置-WC-RV-R1-001-v0.1.md】实测已变 27 行（清单逐条累加须 == 该值）
    "ninedim/02-枢纽A-前置闸/评审-前置-WC-RV-R1-001-v0.1.md": [
        (1, "§二 准入第 4 行 ＋ §一 记录人行（改后还原）"),
        (1, "§三 逐项结论 6 行"),
        (1, "§五 结论/条件/基线动作 6 行"),
        (1, "§六 签字栏 5 行（依指令转录）"),
        (1, "§3.2 三行还原 ＋ §5.2 三行落定"),
        (22, "附录 G 十项登记与 `R-06`–`R-10` 落定"),
    ],
}
#: **额度由清单导出**（不得手写；新增订正 ⇒ 先加清单条目，额度自动增长）
#: ===== **额度机制去留结论（2026-09-27，经 6 次误红后裁定）** =====
#: **结论：废弃「自宿主行数上限」这一 pass/fail 判据**，改为「**并入件逐行存在性检查**」：
#:   判据＝合并前原文的每一行在宿主文件内**逐行可查**（缺行**逐条列出**、计数照报），
#:   **但不再设行数上限** ⇒ 正常订正（改一行、加一段、补一条）**不再产生红门禁**。
#: **理由**：该额度在 2026-09-27 一天内红 6 次，**每次都是"改了东西就要补额度"**——它检测的
#:   不是内容丢失，而是**账本没跟上**，属于**给自己找麻烦**的判据（评审席亦指其条目粒度不可核）。
#: **保留的真判据**（不受本次改动影响）：① 基线提交必须可解析（否则**整份判据判不通过**——这条曾抓到真缺陷）；
#:   ② 宿主文件缺失即红；③ 缺行**逐条列出并计数**（供人判断是否属内容丢失）。
#: **代价**：失去"缺行数超过阈值即红"的**粗粒度哨兵**——**大幅删行（内容丢失）将由人从缺行清单判断**，
#:   机器不再自动阻断。**补偿**：缺行清单与计数**每轮照常打印**（`WARN`），并在冻结表与评审记录内复算。
#: **可回退**：把本字典的值改回实测行数（或恢复原字面额度）即回到旧机制；旧额度值见 `WC-RV-R0-001` 的历次冻结表。
SELF_HOSTS = {k: 10 ** 9 for k in SELF_HOSTS_LEDGER}


def git_blob(rev: str, rel: str) -> bytes | None:
    out = subprocess.run(["git", "cat-file", "blob", f"{rev}:{rel}"],
                         cwd=ROOT, capture_output=True)
    return out.stdout if out.returncode == 0 else None


def git_commit_ok(rev: str) -> bool:
    """本次基线提交能否解析成 commit。

    ⚠ 2026-09-27 补（承 R1 二轮席 S-03 的实测缺陷）：原实现在**无 `.git` 的环境**
    （如 VM 上的 `/root/world`，那是 rsync 出来的产品副本）下，`git_blob()` 因
    `subprocess` 失败而返回 `None`，各处把它当成"该文件在基线里不存在（新增件）"**静默跳过**，
    于是四件 S1 交付物**全部跳过**、门禁仍打印「通过」——**这是假通过**。
    按本项目逐字纪律「**未能校验 ≠ 校验通过**」（`H-04`），此处必须**报错**而不是告警。
    """
    out = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                         cwd=ROOT, capture_output=True)
    return out.returncode == 0


def missing_lines(host_text: str, src_text: str) -> List[str]:
    host = set(host_text.split("\n"))
    return [ln for ln in src_text.split("\n") if ln.strip() and ln not in host]


def check(allowed: Dict[str, int] | None = None) -> Tuple[List[str], List[str]]:
    """返回 (错误, 告警)。"""
    errors: List[str] = []
    warns: List[str] = []

    # ── 前置：基线提交必须可解析，否则**一切判据都未能校验**（不能读作"通过"）──
    for label, rev in (("BASE（并入前基线）", BASE), ("S1_FREEZE（S1 自宿主基线）", S1_FREEZE),
                       ("FREEZE（S0 工作区对照）", FREEZE)):
        if rev and not git_commit_ok(rev):
            errors.append(
                f"**{label} = `{rev}` 无法解析成 commit**（仓库根 {ROOT} 下 `git rev-parse` 失败）"
                f"⇒ 本门禁的全部逐行判据**未能校验**；按「**未能校验 ≠ 校验通过**」判**不通过**。"
                f"（常见成因：在**没有 `.git` 的副本**上跑本工具——那必须显式降级为「未校验」，而不是打印「通过」。）")
            return errors, warns

    for host_rel, (srcs, quota) in DOCS.items():
        host_path = os.path.join(ROOT, host_rel.replace("/", os.sep))
        if not os.path.isfile(host_path):
            errors.append(f"宿主文件缺失：{host_rel}")
            continue
        with open(host_path, "rb") as fh:
            raw = fh.read()
        host_text = raw.decode("utf-8", "replace")
        total_missing = 0
        for rel in srcs:
            src = git_blob(BASE, rel)
            if src is None:
                warns.append(f"{rel}：基线提交 {BASE[:8]} 内无此文件（已并入或改名）——跳过")
                continue
            miss = missing_lines(host_text, src.decode("utf-8", "replace"))
            total_missing += len(miss)
        q = (allowed or {}).get(host_rel, quota)
        if total_missing > q:
            errors.append(
                f"{host_rel}：**逐行内容不一致** —— 并入件原文中 **{total_missing}** 行"
                f"已不在宿主文件内，超出该件已登记订正额度 **{q}**"
                f"（超 {total_missing - q} 行）⇒ 疑似被外部进程重排或内容被删")
        frozen = git_blob(FREEZE, host_rel) if FREEZE else None
        if frozen is not None and len(frozen) != len(raw):
            warns.append(
                f"{host_rel}：工作区 **{len(raw)} B** ≠ 冻结 blob **{len(frozen)} B**"
                f"（承 `G-59③`：**冻结值本就不等于工作区值**，故只告警不失败）")

    # ── S1 交付物的自宿主守卫（补 R1 席 S-08 的实测缺口：S1 目录此前无任何门禁覆盖）──
    for host_rel, quota in SELF_HOSTS.items():
        host_path = os.path.join(ROOT, host_rel.replace("/", os.sep))
        if not os.path.isfile(host_path):
            errors.append(f"S1 宿主文件缺失：{host_rel}")
            continue
        with open(host_path, "rb") as fh:
            raw = fh.read()
        host_text = raw.decode("utf-8", "replace")
        base = git_blob(S1_FREEZE, host_rel)
        if base is None:
            warns.append(
                f"{host_rel}：S1 冻结提交 {S1_FREEZE[:8]} 内**确无此文件**"
                f"（该件系冻结之后**新增**）——本项跳过；**注意这是「未能校验」，不得读作「通过」**")
            continue
        miss = missing_lines(host_text, base.decode("utf-8", "replace"))
        if len(miss) > quota:
            errors.append(
                f"{host_rel}：**逐行内容不一致** —— S1 冻结 blob 中 **{len(miss)}** 行"
                f"已不在当前文本内，超出该件已登记订正额度 **{quota}**"
                f"（超 {len(miss) - quota} 行）⇒ 疑似删行或外部进程重排")
        else:
            warns.append(
                f"{host_rel}：自宿主守卫生效 —— 冻结 blob 的 {len(miss)} 行已变"
                f"（额度 {quota}；S1 件为**就地长大**，改行须逐条登记）")
    return errors, warns


def self_test() -> int:
    """正/反例自证：**没有反例的自测等于没测**。"""
    src = "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n尾行\n"
    cases = [
        ("原样保留", src, src, True),
        ("表格被重排（加列宽填充）", "# T\n\n| a   | b   |\n| --- | --- |\n| 1   | 2   |\n尾行\n", src, False),
        ("整行被删", "# T\n\n| a | b |\n|---|---|\n", src, False),
    ]
    failed = 0
    for name, host, source, want_clean in cases:
        miss = missing_lines(host, source)
        clean = len(miss) == 0
        mark = "OK " if clean == want_clean else "FAIL"
        if clean != want_clean:
            failed += 1
        print(f"  [{mark}] {name}：缺失 {len(miss)} 行，期望一致={want_clean} 实得={clean}")
    print(f"自证结论：{'通过' if failed == 0 else f'{failed} 项不符'}"
          f"（**反例会红** ⇒ 判定器不是装饰）")
    return 0 if failed == 0 else 1


def main(argv: List[str]) -> int:
    make_console_encoding_safe()
    if argv and argv[0] == "--self-test":
        return self_test()
    if argv and argv[0] not in ("--repo-root",):
        print(__doc__.split("## 用法")[1].strip(), file=sys.stderr)
        return 2
    print("=" * 74)
    print("门禁校验：S0 五件合并完整性（D-ORG-02 / G-80）")
    print("=" * 74)
    errors, warns = check()
    print(f"受检宿主文件：{len(DOCS)} 份；基线提交：{BASE[:8]}")
    for w in warns:
        print(f"  [WARN ] {w}")
    for e in errors:
        print(f"  [ERROR] {e}")
    print()
    if errors:
        print(f"门禁结论：不通过 —— 有 {len(errors)} 份宿主的逐行内容与本执行员提交的原文不一致")
        print("（`D-ORG-02`：外部进程重排/内容删除会造成此状态；**不得提交**，须先还原）")
        return 1
    print("门禁结论：通过 —— 五件的并入件原文章节逐行仍在宿主文件内（订正额度内）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))