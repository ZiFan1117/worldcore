#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门禁工具：S0 准出证据准入隔离（admission evidence isolation）。

## 本工具要挡的是什么

`06-swe-gb/docs/评审类/01-阶段评审记录.md` **铁律一**（逐字）：

> **没有准出结论，不进入下一阶段。**"先做着，评审后补"**明令禁止**；
> 没有本记录中的书面准出结论，**下一阶段的一切工作都属于未授权开工，其产出不进入基线**。

⇒ 罚则是"**产出不进入基线**"，**不是**"产物不存在"。故本项目**不搬迁**
那 16 份阶段外产物（搬它们会连带改配置项路径与门禁默认路径，且 `WC-SCMP-001`
是签署对象 ⇒ 再冻一次，收益为零）。本工具把该罚则落成**会红的机器判据**。

## 判据（必须会红）

**S0 的准出证据集合 ⊆ {FSR, SDP, SQAP, SCMP, 风险清单载体, R0 阶段评审记录}。**

凡在 **R0 材料 / R0 评审记录**（`WC-RV-R0-001`，**已含原 `WC-R0-DS-001` 决议单为并入件**）里，
出现**把 S1–S5 产物当作 S0 准出依据**
的引用（形如"因 `WC-HLD-001` 已编制故…"），判 **rc=1**。

⚠ **本工具的已知边界（必须与结论同读）**：
  · 它是**形态匹配**，不是语义理解。规则表见 `RULES`（逐条给出正则与理由）。
  · 它**只判"被禁止的引用形态"**，不判"R0 是否该通过"——后者是人的职责（`EV-08`/`EV-09`）。
  · **正例侧允许**：把阶段外产物写成"现状事实 / 缺口 / 风险 / 不得作判据"是**合法**的
    （`WC-RV-R0-001` §十一之六/§十一之七 就大量这样做），本工具**不得**因它们报红。

## 反例自证（`--self-test`）

一个从不失败的检查不是检查，是装饰。`--self-test` 会用**内置的正例/反例样本**证明：
  ① 反例样本（含被禁形态引用）**必须报红**（rc=1）；
  ② 正例样本（合法现状陈述）**必须不报红**（rc=0）。
任一不成立 ⇒ 本工具自身判不通过。

## 用法

    python tools/admission_evidence.py --repo-root ..        # 扫真实文档
    python tools/admission_evidence.py --self-test          # 判定器自证（正反例）
    python tools/admission_evidence.py --scan <路径>...      # 只扫指定文件（供自证用）

退出码：0 = 通过；1 = 不通过（或本工具自证失败）；2 = 用法错误。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Tuple


def make_console_encoding_safe() -> None:
    r"""让本脚本在**非 UTF-8 控制台**（Windows 默认 GBK/cp936）下**不再崩溃**。

    病灶（2026-09-27 实测）：本脚本输出含 `⇒`(U+21D2)/`⚠`(U+26A0) 等 GBK 编不出的符号，
    `print()` 抛 `UnicodeEncodeError` ⇒ **rc=1 假失败**（"自证通过"被误报成"判定器是装饰"，
    与"隐藏缺陷"方向相反、危害同级）。CI 在 Linux（UTF-8）不受影响，但开发者本机默认控制台
    就是 GBK —— **一个只在 CI 里活着的检查不是检查**。

    修法（在题目给定的两案里取 ②）：把 **`stdout`** 的 `errors` 重配为 `replace`（**不改 encoding**）
    ⇒ GBK 下中文仍按 GBK 输出、只有编不出的符号降级为 `?`，**告警文字一字不删**；UTF-8 下逐字节等价。
    ⚠ **`stderr` 不动**：Python 3.5+ 起 `sys.stderr` 默认就是 `backslashreplace`（本来就不崩、
    且保留字符身份 —— 实测 GBK 下打印 `⚠️` 得到 `\u26a0\ufe0f` 而不抛异常）；改成 `replace`
    反而把可复原的 `\u26a0` 变成不可复原的 `?`（信息更少），故不改。
    不取 ①（逐字符换 ASCII 等价物）的理由：① 要维护一张"危险字符"清单，清单外的新符号会把
    门禁**再打崩一次**——那是把"假定"当"保证"（同族：`G-13`/`G-68`）；② 是入口一次性兜底。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:  # 非 TextIOWrapper（被捕获/重定向）时跳过
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):  # pragma: no cover - 不可重配的流
        pass

# ---------------------------------------------------------------- 常量

#: S0 允许作为准出证据的集合（判据的右半边，写死、可核）
S0_EVIDENCE_ALLOWED: Tuple[str, ...] = (
    "WC-FSR-001",       # 可行性研究报告
    "WC-SDP-001",       # 项目开发计划（含裁剪说明）
    "WC-SQAP-001",      # 软件质量保证计划
    "WC-SCMP-001",      # 软件配置管理计划
    "风险清单载体",      # 并入 WC-SDP-001（无独立模板）
    "R0 阶段评审记录",   # WC-RV-R0-00x（归 S0 技术评审组织者）
)

#: S1–S5 阶段外产物（**不得**作为 S0 准出依据）
OUT_OF_PHASE: Tuple[str, ...] = (
    "WC-SRS-001", "WC-IRS-001", "WC-RTM-001",                    # S1
    "WC-HLD-001", "WC-MODREG-001", "WC-IC-001",
    "WC-LFMT-001", "WC-PFMT-001", "WC-CKFMT-001", "WC-ONT-001",  # S2
    "WC-SK-001",                                                  # S3
    "WC-LLD-001", "WC-UT-001",                                    # S4
    "WC-TP-001", "WC-TS-001", "WC-TR-001",                        # S5
)

#: 被扫描的文件（R0 材料 / R0 评审记录 / WC-R0-DS-001 三件已合并为一份）
#: ⚠ 2026-09-26 **S0 文档合并轮**：原三份（`WC-RV-R0-001` 材料与逐条核查 /
#: `WC-R0-DS-001` 决议单 / `WC-RV-R0-002` 阶段评审记录）已按
#: `templates/06-评审类/01-阶段评审记录.md:13`「**每次评审一份**」合并为
#: **一份**《R0 阶段评审记录》＝ `docs/评审/评审-后置-WC-RV-R0-001-v0.1.md`（决议单为**附件 A**、
#: 阶段评审记录为**附件 B**，两者原文逐字保留在同一文件内）。
#: ⇒ 扫描面**不缩小**：原两份被扫文件的全部字节都在下面这一份里。
SCAN_TARGETS: Tuple[str, ...] = (
    "docs/评审/评审-后置-WC-RV-R0-001-v0.1.md",
)

#: 违反形态规则表：(规则名, 正则, 为什么它被禁, 是否需要同时出现阶段外产物编号)
#: 标 `False` 的规则是**通用形态**（其本身即"无据宣布准出"的形态，不依赖具体产物编号）。
#: 标 `True` 的规则必须**同时**命中"阶段外产物编号"，故不会误伤
#: "把阶段外产物写成现状事实/缺口/不得作判据"的合法写法。
RULES: Tuple[Tuple[str, str, str, bool], ...] = (
    (
        "R1-已编制故",
        r"(?:因|由于)[^。；\n]{0,80}已(?:编制|成文|完成)[^。；\n]{0,40}故",
        "以\"某阶段外产物已编制\"为由推出结论——铁律一禁止把产出当准出依据",
        True,
    ),
    (
        "R2-产物作准出依据",
        r"阶段外产物[^。；\n]{0,20}(?:作为|当作)[^。；\n]{0,20}准出(?:依据|判据)",
        "把阶段外产物直接当成准出依据",
        False,
    ),
    (
        "R3-上游已过",
        r"(?:既已|既然|既然已)[^。；\n]{0,60}(?:编制|成文|完成)[^。；\n]{0,40}(?:说明|可见|则|即)[^。；\n]{0,30}(?:已过|准出|通过)",
        "以\"上游产物已成文\"推出\"某门禁已过\"",
        True,
    ),
    (
        "R4-故某门禁已通过",
        r"(?:^|[\s。；，、>|*`）)])故[^。；\n]{0,30}(?:R\d|立项|阶段)[^。；\n]{0,20}(?:已通过|已准出|通过|已完成)",
        "以阶段外产物为由宣布某门禁已通过",
        True,
    ),
    (
        "R5-已具备准出条件",
        r"(?:已具备|满足)[^。；\n]{0,20}准出条件",
        "宣布已具备准出条件（须由人作出，且不得以阶段外产物为据）",
        False,
    ),
    (
        "R6-视为立项完成",
        r"(?:视为|等同|视同)[^。；\n]{0,20}(?:立项已完成|立项已准出|S0 已完成)",
        "把阶段外产物等同于立项完成",
        True,
    ),
)

#: 合法写法白名单（出现这些词的行**豁免**上述规则）——它们正是本项目
#: `WC-RV-R0-001` §十一之六/§十一之七 与 `G-20` 所要求的"如实登记"形态。
WHITELIST = (
    "不得作", "不构成", "不得作为", "不进入基线", "未授权开工",
    "缺口", "风险", "错位", "禁止", "违反", "反例", "应当失败",
    "不算证", "自证", "不构成本阶段", "不等于",
)


def _compile_rules() -> List[Tuple[str, "re.Pattern[str]", str, bool]]:
    out = []
    for name, pattern, why, needs_artifact in RULES:
        out.append((name, re.compile(pattern), why, needs_artifact))
    return out


def compile_artifact_re() -> "re.Pattern[str]":
    return re.compile("|".join(re.escape(x) for x in OUT_OF_PHASE))


def scan_text(path: str, text: str) -> List[Tuple[int, str, str, str]]:
    """返回 [(行号, 规则名, 命中片段, 理由)]。

    判定顺序（两条正交的过滤）：
      ① 白名单：行内出现 `WHITELIST` 任一"如实登记"词 ⇒ **整行豁免**
         （这正是 `WC-RV-R0-001` §十一之六/§十一之七 与 `G-20` 要求的写法）；
      ② 需要产物编号的规则（`needs_artifact=True`）必须先在该行看到 S1–S5 产物编号，
         否则不判——避免误伤与产物无关的一般性表述。
    """
    rules = _compile_rules()
    art = compile_artifact_re()
    hits: List[Tuple[int, str, str, str]] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if any(w in line for w in WHITELIST):
            continue
        has_artifact = bool(art.search(line))
        for name, rx, why, needs_artifact in rules:
            if needs_artifact and not has_artifact:
                continue
            m = rx.search(line)
            if m:
                hits.append((lineno, name, m.group(0), why))
                break
    return hits


def check_repo(repo_root: str) -> Tuple[int, List[str]]:
    """扫真实文档。返回 (问题数, 报告行)。"""
    report: List[str] = []
    total = 0
    for rel in SCAN_TARGETS:
        path = os.path.join(repo_root, rel)
        if not os.path.isfile(path):
            report.append(f"  [SKIP ] {rel}（文件不存在——\"未校验\"要说出来）")
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        hits = scan_text(path, text)
        if hits:
            total += len(hits)
            report.append(f"  [违规 ] {rel}：{len(hits)} 处")
            for lineno, name, frag, why in hits:
                report.append(f"          :{lineno} [{name}] {frag!r}")
                report.append(f"                    ↳ {why}")
        else:
            report.append(f"  [通过 ] {rel}")
    return total, report


# ---------------------------------------------------------------- 自证

GOOD_SAMPLE = """# 正例样本（合法写法：现状事实 / 缺口 / 不得作判据）

> 库内实况：本仓库在 S0 期间已经存在下游阶段的文档——`WC-HLD-001`、`WC-LLD-001`、`WC-TR-001`。

> ⇒ 这些文档在 S0 的地位只有两条：① 它们是支撑证据；② 它们**不等于** S1／S2 的准出。

> **反例（应当失败）**：把 `WC-HLD-001`「已编制」当作"R2 已通过" ⇒ 必须判**准出依据不足**。

> `WC-RTM-001.csv` 与 `WC-SRS-001` 是提前起草产物，**其产出不进入基线**。

> 超前产出共 11 份，**未授权开工**状态下产出，已登记为缺口。
"""

BAD_SAMPLES: Tuple[Tuple[str, str], ...] = (
    ("R1-已编制故", "因 `WC-HLD-001` 已编制故 R0 具备准出依据。\n"),
    ("R2-产物作准出依据", "把阶段外产物作为准出依据提交评审。\n"),
    ("R3-上游已过", "既然 `WC-SRS-001` 已成文，则可见 R1 已过。\n"),
    ("R4-故某门禁已通过", "`WC-HLD-001` 已编制，故 R0 已通过立项评审。\n"),
    ("R5-已具备准出条件", "本项目已具备准出条件。\n"),
    ("R6-视为立项完成", "`WC-TR-001` 已编制，视为立项已完成。\n"),
)


def self_test() -> int:
    print("=" * 74)
    print("判定器自证（admission_evidence --self-test）")
    print("=" * 74)

    ok = True

    print("\n① 正例样本（合法现状陈述）——期望：**不报红**（0 命中）")
    good_hits = scan_text("<GOOD_SAMPLE>", GOOD_SAMPLE)
    if good_hits:
        ok = False
        print(f"  [FAIL] 正例被误判 {len(good_hits)} 处（本工具会误伤合法写法）：")
        for lineno, name, frag, why in good_hits:
            print(f"          :{lineno} [{name}] {frag!r}")
    else:
        print("  [ OK ] 正例 0 命中 ⇒ 合法写法未被误伤")

    print("\n② 反例样本（被禁形态引用）——期望：**逐条报红**")
    for expect, sample in BAD_SAMPLES:
        hits = scan_text("<BAD_SAMPLE>", sample)
        got = {name for _, name, _, _ in hits}
        if expect in got:
            print(f"  [ OK ] {expect:<18} 命中 ⇒ {sorted(got)}")
        else:
            ok = False
            print(f"  [FAIL] {expect:<18} 未命中（该判据是装饰！）实际={sorted(got)}")

    print("\n③ 判据右半边（S0 允许的证据集合）——打印以便人工核对")
    print("  S0 准出证据集合 = {" + ", ".join(S0_EVIDENCE_ALLOWED) + "}")
    print(f"  S1–S5 阶段外产物 = {len(OUT_OF_PHASE)} 项（不得作为 S0 准出依据）")

    print()
    if ok:
        print("自证结论：通过 —— 判定器会红（反例全中）、不误伤（正例零命中）")
        return 0
    print("自证结论：不通过 —— 判定器本身有缺陷，不得据它下结论")
    return 1


# ---------------------------------------------------------------- main


def main(argv: List[str] | None = None) -> int:
    make_console_encoding_safe()

    parser = argparse.ArgumentParser(
        description="S0 准出证据准入隔离（把阶段外产物当准出依据即报红）"
    )
    parser.add_argument(
        "--repo-root",
        default="..",
        help="world-core 仓库子树根（默认 ..，即从 tools/ 往上一级）",
    )
    parser.add_argument("--self-test", action="store_true", help="判定器正反例自证")
    parser.add_argument(
        "--scan",
        nargs="*",
        default=None,
        help="只扫指定文件（供自证/临时探针用）",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    print("=" * 74)
    print("门禁校验：S0 准出证据准入隔离")
    print("=" * 74)
    print("判据：S0 准出证据集合 ⊆ {" + ", ".join(S0_EVIDENCE_ALLOWED) + "}")
    print(f"被扫对象：{len(SCAN_TARGETS)} 份（R0 材料 / R0 评审记录 / WC-R0-DS-001）")
    print()

    if args.scan:
        total = 0
        for path in args.scan:
            if not os.path.isfile(path):
                print(f"  [SKIP ] {path}（不存在）")
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                hits = scan_text(path, fh.read())
            total += len(hits)
            print(f"  {'[违规 ]' if hits else '[通过 ]'} {path}：{len(hits)} 处")
            for lineno, name, frag, why in hits:
                print(f"          :{lineno} [{name}] {frag!r}")
    else:
        root = os.path.abspath(args.repo_root)
        total, report = check_repo(root)
        for line in report:
            print(line)

    print()
    if total:
        print(f"门禁结论：不通过 —— 有 {total} 处把 S1–S5 阶段外产物当作 S0 准出依据")
        print("（铁律一：没有准出结论，不进入下一阶段；未授权开工的产出不进入基线）")
        return 1
    print("门禁结论：通过 —— 未发现把阶段外产物当作 S0 准出依据的引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
