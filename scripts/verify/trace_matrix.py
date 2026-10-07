"""门禁工具：需求追溯矩阵（RTM）完整性校验。

依据：GB/T 8567-2006（文档编制规范）、GB/T 38634.3-2020（测试文档）。

这个工具把「需求覆盖率 100%」这类门禁条件从人工核对变成 CI 自动判定。

双向追溯校验项：
  正向  需求 → 设计模块 → 测试用例
  反向  测试用例 → 需求（用例引用的需求必须存在）
  交叉  引用的模块号必须在模块登记表中存在

用法：
    python tools/trace_matrix.py                                   # 校验**本项目真实产物**（默认输入）
    python tools/trace_matrix.py --matrix <RTM.csv> --srs <SRS.md>
    python tools/trace_matrix.py --matrix <RTM.csv> --srs <SRS.md> --strict
    python tools/trace_matrix.py --sample                          # **仅**工具可用性自证（非本项目样例）

退出码：0 = 通过；1 = 未通过（门禁不通过；**真实输入缺失**同样为 1）。
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Set


def make_console_encoding_safe() -> None:
    r"""让本脚本在**非 UTF-8 控制台**（如 Windows 默认 GBK/cp936）下**不再崩溃**。

    病灶（2026-09-27 实测）：本文件的提示串含 `⚠`(U+26A0) 等字符，GBK 编不出 ⇒
    `print()` 抛 `UnicodeEncodeError` ⇒ **门禁 rc=1 假失败**（"通过"被误报成"不通过"，
    与"不通过被误报成通过"同属**结论失真**）。CI 跑在 Linux（UTF-8）不受影响，
    但开发者本机默认控制台就是 GBK —— **一个只在 CI 里活着的检查不是检查**。

    修法（二选一，取 ②）：把 **`stdout`** 的 `errors` 重配为 `replace`（**不改 encoding**）
    ⇒ GBK 控制台仍按 GBK 输出（中文不乱码），只有编不出的符号降级为 `?`，**告警文字一字不删**；
    UTF-8 下 `replace` 永不触发 ⇒ **逐字节等价**（已实测：与原版对照 IDENTICAL）。
    ⚠ **`stderr` 不动**：Python 3.5+ 起 `sys.stderr` 的默认错误处理器就是 `backslashreplace`
    —— 它**本来就不崩、且保留字符身份**（实测：GBK 下往 stderr 打印 `⚠️` 得到 `\u26a0\ufe0f`，
    不抛异常）；改成 `replace` 反而把可复原的 `\u26a0` 变成不可复原的 `?`（**信息更少**），故不改。
    为什么取 ② 而不是 ①（逐字符换 ASCII 等价物）：
      ① 要维护一张"危险字符"清单，清单外的字符随时会把门禁再打崩 ——
         **同一个缺陷族会随每一次新增符号复发**（与 `G-13`/`G-68` 同族：
         把"假定"当成"保证"）；
      ② 是**入口处一次性兜底**，对任何字符、任何非 UTF-8 编码都成立。
    ② 在 UTF-8 控制台/CI 下**逐字节等价**（`utf-8` 下 `replace` 永不触发），
    故既有证据与冻结口径不受影响；在 GBK 控制台下保留控制台原生编码，
    中文正常显示、只有少数符号变 `?`（不产生乱码）。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:  # 被重定向成非 TextIOWrapper（如 pytest 捕获）时跳过
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):  # pragma: no cover - 不可重配的流
        pass


# ── 输入面：**本项目真实产物** vs **非本项目样例**（批次七修复，2026-09-27）────────
# 回归（批次六引入，实测）：默认输入被改到 `_非本项目样例/` ⇒ 裸跑**不再校验本项目**，
#   改去校验 4 行电商样例数据并打印「门禁结论：通过 —— 覆盖率 100%」。
#   同一提交还把模块登记表路径改到已空置的 `docs/S2-设计/` ⇒ `WC-MODREG-001` 的
#   模块号存在性校验**静默失效**（`known_modules` 为空集时该判据整条不触发）。
#   根因与 `G-13`/`G-68` 同族：**校验的输入面 ≠ 它声称的语义**。
# 现行口径（三条，缺一不可）：
#   ① 默认输入 = **本项目真实产物**（下面三条路径）；
#   ② 真实输入缺失 ⇒ **显式判不通过（rc=1）并打印 `真实输入缺失：<路径>`**，**不得回落样例**；
#   ③ 样例数据**只能被显式索取**（`--sample`），其结论**不得**写成「覆盖率 100%」；
#      未显式索取而输入落在样例目录内 ⇒ **直接判不通过**（"悄悄顶替"这条路封死）。
PROJECT_MATRIX = os.path.join("docs", "S1-需求", "WC-RTM-001.csv")
PROJECT_SRS = os.path.join("docs", "S1-需求", "需求-WC-SRS-001-v0.1.md")
SAMPLE_DIR = os.path.join("docs", "阶段外-待启用", "_非本项目样例")
SAMPLE_MATRIX = os.path.join(SAMPLE_DIR, "需求追溯矩阵.csv")
SAMPLE_SRS = os.path.join(SAMPLE_DIR, "软件需求规格说明.md")
# 模块登记表所在目录（S2 产物；批次六整体移入阶段外暂存区，路径随之同步）
#: 2026-09-27 **纠偏**（R2 席 S2-02／S2-06 实测：原常量指向 `docs/阶段外-待启用/S2-设计`，该目录内已无 `WC-MODREG-*`，
    #: 使模块号存在性校验**静默失效**、门禁在「模块登记表: 尚未建立」时仍打印「通过」）。
#: 本改动是**缺陷纠偏**（把工具指向它自述要读的文件），不是门禁强度提升；强度仍为默认（`--strict` 未默认开启）。
PROJECT_MODREG_DIR = os.path.join("docs", "S2-设计")

REQUIRED_COLUMNS: Sequence[str] = (
    "需求编号",
    "需求名称",
    "优先级",
    "需求基线版本",
    "设计模块号",
    "设计文档章节",
    "接口编号",
    "实现代码位置",
    "单元测试用例",
    "集成测试用例",
    "系统测试用例",
    "验收测试用例",
    "状态",
    "备注",
)

CASE_COLUMNS: Sequence[str] = (
    "单元测试用例",
    "集成测试用例",
    "系统测试用例",
    "验收测试用例",
)

MODULE_ID_PATTERN = re.compile(r"\bM\d{2}\b")
REQ_ID_PATTERN = re.compile(r"\bREQ-[FN]-\d{3}\b")

# 用例编号：支持两种写法（与 templates/05-测试类/02-软件测试说明与用例.md §1.3 一致）
#   ① 无前缀：TC-001、TC-101      —— demo 与 03-需求追溯矩阵.csv 用的是这种
#   ② 带类型前缀：TC-F-001、TC-B-001、TC-P-001 等
# 前缀含义：F 功能 / B 边界 / E 异常 / P 性能 / C 并发 / R 恢复 / S 安全 / M 兼容 / U 易用
# 规则：用例编号全域唯一、一经分配永不复用
CASE_ID_PATTERN = re.compile(r"TC-(?:[A-Z]-)?\d{3}")

# 允许的优先级取值（与模板一致）
VALID_PRIORITIES = {"P0", "P1", "P2"}


def split_multi(value: str) -> List[str]:
    """拆分多值单元格。

    分隔符约定：**分号 ;**（主） / 逗号 , 、顿号 、（兼容）。
    注意：多值字段若用逗号分隔，**必须给整个单元格加双引号**，
    否则裸逗号会被 CSV 解析器当作列分隔符，导致整行右移一列。
    本工具会对字段数不匹配的行直接报错（见 check_matrix 的结构完整性校验），
    避免这种错位被静默放过。
    """
    if not value:
        return []
    parts = re.split(r"[;；,，、]+", value.strip())
    return [p.strip() for p in parts if p.strip()]


def split_cases(value: str) -> List[str]:
    """从测试用例单元格中提取用例编号，并过滤掉代码路径等非用例内容。

    同一个单元格里允许混写代码位置（如 `skeleton/modules.py::OrderService.submit_order`）
    与用例编号（如 `TC-001`），本函数只取后者。
    """
    cases: List[str] = []
    for part in split_multi(value):
        # 含路径分隔符或双冒号限定的，视为代码位置而非用例编号
        if "/" in part or "\\" in part or "::" in part:
            continue
        cases.append(part)
    return cases


@dataclass
class Issue:
    level: str  # "ERROR" | "WARN"
    requirement: str
    message: str


@dataclass
class CheckResult:
    requirements: int = 0
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "WARN"]


def load_known_modules(repo_root: str) -> Set[str]:
    """从**本项目的模块登记表**中提取已登记的模块号。

    ⚠️ 2026-09-26 修正（WC-SCMP-001 §8.4 G-13）——原实现读的是
    `templates/03-设计类/02-模块清单与模块号登记表.md`，那是**上游通用模板**，
    里面全是**示例与分层区间占位**（`<M01>`、`M20`–`M39`…），后果有两个，
    方向相反、都不好：**假通过**（示例号被点头）与**假失败**（本项目真实模块号被判"不存在"）。
    故改为只认本项目 S2 产出物 `docs/阶段外-待启用/S2-设计/WC-MODREG-*.md`。

    ⚠️ 2026-09-26 再修正（G-15）——**只认表格行里的模块号**：
    原实现用 `\\bM\\d{2}\\b` 扫**全文**，于是文件里任何位置出现的别人的 M 号
    （例如说明文字里引用模板的分层区间 `M20`–`M39`）都会被当成"已登记"，
    把这一项校验**悄悄放宽**。根因与 G-13 同族：**校验的输入面比它的语义宽**。
    现在的口径是"登记表的**每一行**以 `| Mxx |` 开头才算登记"。
    """
    known: Set[str] = set()
    design_dir = os.path.join(repo_root, PROJECT_MODREG_DIR)
    registry_files: List[str] = []
    if os.path.isdir(design_dir):
        registry_files = sorted(
            os.path.join(design_dir, name)
            for name in os.listdir(design_dir)
            if name.startswith("WC-MODREG-") and name.endswith(".md")
        )
    # 表格行：`| **M01** | …` 或 `| M01 | …`
    row_pattern = re.compile(r"^\|\s*\**\s*(M\d{2})\s*\**\s*\|", re.MULTILINE)
    for path in registry_files:
        with open(path, "r", encoding="utf-8") as fh:
            known.update(row_pattern.findall(fh.read()))
    return known


def registry_status(repo_root: str) -> str:
    """返回模块登记表的定位说明（供报告打印，明示"校验了/没校验"）。"""
    design_dir = os.path.join(repo_root, PROJECT_MODREG_DIR)
    if os.path.isdir(design_dir):
        found = [
            name
            for name in os.listdir(design_dir)
            if name.startswith("WC-MODREG-") and name.endswith(".md")
        ]
        if found:
            return "已建立（" + "、".join(sorted(found)) + "）"
    return "尚未建立（S2 产出 WC-MODREG-001 后本项自动生效）"


def load_srs_case_map(srs_path: str) -> Dict[str, Set[str]]:
    r"""从 SRS 的「需求 → 测试用例 映射」表读出 **用例 → 它声明覆盖的需求**。

    为什么需要它（2026-09-26 补，见 `WC-RV-R2-001` **FIND-09 / T-03 / F-24**）：
    原实现只校验用例编号**格式合法**，从不校验"这条用例是否真的声明覆盖这条需求"。
    后果是**错位永远绿灯**：把 `TC-030`（投影同源用例）填在"视觉投影"行、
    把 `TC-007`（信纸缺 `before` 的用例）填在"信封字段"行，门禁照样通过——
    于是 `已实现` 变成一个**门禁查不出真假**的字段。

    解析形如 `| \`TC-013\` | … | REQ-F-015 | 已实现 |` 的行；
    需求列支持缩写（`REQ-F-001/003/022` 展开为三条）。
    """
    if not srs_path or not os.path.isfile(srs_path):
        return {}
    mapping: Dict[str, Set[str]] = {}
    with open(srs_path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 3:
                continue
            case_ids = re.findall(r"TC-(?:[A-Z]-)?\d{3}", cells[0])
            if len(case_ids) != 1:
                continue  # 只认"一行一个用例"；表头与说明行自然被跳过
            expanded: Set[str] = set()
            for token in re.split(r"[;；,，、/\s]+", cells[2]):
                token = token.strip()
                if not token:
                    continue
                if REQ_ID_PATTERN.fullmatch(token):
                    expanded.add(token)
                elif re.fullmatch(r"\d{3}", token) and expanded:
                    # 缩写 REQ-F-001/003 → 继承已出现编号的前缀
                    prefix = sorted(expanded)[0].rsplit("-", 1)[0]
                    expanded.add(f"{prefix}-{token}")
            if expanded:
                mapping.setdefault(case_ids[0], set()).update(expanded)
    return mapping


def load_srs_requirement_ids(srs_path: str) -> Set[str]:
    """从 SRS 文档中提取需求编号（用于校验 RTM 与 SRS 一致）。"""
    if not srs_path or not os.path.isfile(srs_path):
        return set()
    with open(srs_path, "r", encoding="utf-8") as fh:
        return set(REQ_ID_PATTERN.findall(fh.read()))


def check_matrix(
    matrix_path: str,
    srs_path: str = "",
    known_modules: Set[str] | None = None,
    strict: bool = False,
) -> CheckResult:
    result = CheckResult()
    known_modules = known_modules or set()

    if not os.path.isfile(matrix_path):
        result.issues.append(Issue("ERROR", "-", f"追溯矩阵文件不存在：{matrix_path}"))
        return result

    with open(matrix_path, "r", encoding="utf-8-sig", newline="") as fh:
        # --- 结构完整性校验：字段数必须与列数一致 ---
        #
        # 这是最重要的一道防线。若某单元格的多值字段用了裸逗号（未加引号），
        # CSV 解析器会把它当作列分隔符，导致**整行右移一列**：
        # 值会串到错误的列上，校验结果看似"通过"，实则数据已经错位。
        # 门禁静默放过 = 门禁失效，所以必须在此直接报错。
        raw_rows = list(csv.reader(fh))
        if not raw_rows:
            result.issues.append(Issue("ERROR", "-", "追溯矩阵文件为空"))
            return result
        header = raw_rows[0]
        expected_cols = len(header)
        misaligned = [
            (line_no, len(row))
            for line_no, row in enumerate(raw_rows[1:], start=2)
            if row and len(row) != expected_cols
        ]
        for line_no, actual in misaligned:
            result.issues.append(
                Issue(
                    "ERROR",
                    "-",
                    f"第 {line_no} 行字段数为 {actual}，应为 {expected_cols} 列"
                    "——整行可能因裸逗号错位。多值字段请用分号分隔，"
                    "或给整个单元格加双引号",
                )
            )
        if misaligned:
            return result

        fh.seek(0)
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            result.issues.append(
                Issue("ERROR", "-", "追溯矩阵缺少必需列：" + "、".join(missing))
            )
        # 2026-09-27 补（承 R1 二轮席 S-05 的实测）：模板 §二 逐字要求「共 14 列，列名
        # **不可改名、不可调序、不可增删**」，而原实现**只查"缺列"、不查"多列"**
        # ⇒ 追加第 15 列「反向追溯」（新增反向列，正是模板禁止的"增列"）门禁**仍 rc=0**，
        # 于是 P-05 判据①「列数 = 14」**不可机械核对**，其自带的「多列探针」**不成立**。
        # 此处补齐：多列 / 空表头列 / 调序 一律 ERROR。（只增不减：非严格路径不会由绿转红
        # 的本项目数据——本文件当前恰为 14 列且逐字有序。）
        extra = [c for c in header if c not in REQUIRED_COLUMNS]
        if extra:
            result.issues.append(
                Issue("ERROR", "-", "追溯矩阵存在**模板外列**（模板 §二 逐字禁止增列）："
                      + "、".join(repr(c) for c in extra))
            )
        blank = [i for i, c in enumerate(header) if not (c or "").strip()]
        if blank:
            result.issues.append(
                Issue("ERROR", "-", "追溯矩阵存在**空列名的列**（第 %s 列）"
                      % "、".join(str(i + 1) for i in blank))
            )
        names = [c for c in header if (c or "").strip()]
        if not missing and not extra and names != list(REQUIRED_COLUMNS):
            result.issues.append(
                Issue("ERROR", "-", "追溯矩阵的**列序与模板不一致**（模板 §二 逐字要求不可调序）："
                      "实得 " + "、".join(names))
            )
            return result
        rows = [r for r in reader if (r.get("需求编号") or "").strip()]

    result.requirements = len(rows)
    if not rows:
        result.issues.append(Issue("ERROR", "-", "追溯矩阵为空，没有任何需求记录"))
        return result

    seen_ids: Dict[str, int] = {}
    srs_ids = load_srs_requirement_ids(srs_path)
    srs_cases = load_srs_case_map(srs_path)

    for line_no, row in enumerate(rows, start=2):
        req_id = (row.get("需求编号") or "").strip()
        seen_ids[req_id] = seen_ids.get(req_id, 0) + 1

        def add(level: str, message: str) -> None:
            result.issues.append(Issue(level, req_id, f"第 {line_no} 行：{message}"))

        # --- 编号格式 ---
        if not REQ_ID_PATTERN.fullmatch(req_id):
            add("ERROR", f"需求编号 {req_id!r} 不符合规则 REQ-F-xxx / REQ-N-xxx")

        # --- 名称与优先级 ---
        if not (row.get("需求名称") or "").strip():
            add("ERROR", "需求名称为空")
        priority = (row.get("优先级") or "").strip()
        if priority not in VALID_PRIORITIES:
            add("ERROR", f"优先级 {priority!r} 非法，必须为 P0/P1/P2")

        # --- 基线版本 ---
        if not (row.get("需求基线版本") or "").strip():
            add("ERROR", "需求基线版本为空——未纳入基线的需求不可追溯")

        # --- 正向：需求 → 设计模块 ---
        modules = split_multi(row.get("设计模块号") or "")
        if not modules:
            add("ERROR", "未映射到任何设计模块（正向追溯断裂：需求 → 设计）")
        for module_id in modules:
            if not MODULE_ID_PATTERN.fullmatch(module_id):
                add("ERROR", f"模块号 {module_id!r} 格式非法")
            elif known_modules and module_id not in known_modules:
                add("ERROR", f"模块号 {module_id} 在模块登记表中不存在")

        if not (row.get("设计文档章节") or "").strip():
            add("WARN", "未标注设计文档章节")

        if not (row.get("实现代码位置") or "").strip():
            add("ERROR", "未标注实现代码位置（正向追溯断裂：设计 → 代码）")

        # --- 正向：需求 → 测试用例（门禁核心）---
        case_total = 0
        for column in CASE_COLUMNS:
            cases = split_cases(row.get(column) or "")
            case_total += len(cases)
            for case_id in cases:
                # 语义层追溯（2026-09-26 补）：用例必须**在 SRS 里声明覆盖这条需求**。
                # 只查格式会让"张冠李戴"永远绿灯（WC-RV-R2-001 T-03）。
                if srs_cases and case_id not in srs_cases.get("__none__", set()):
                    declared = srs_cases.get(case_id)
                    if declared is None:
                        add(
                            "ERROR",
                            f"{column} 引用了用例 {case_id}，但 SRS §五 里没有它的声明"
                            "（用例必须先在 SRS 中登记覆盖哪些需求）",
                        )
                    elif req_id not in declared:
                        add(
                            "ERROR",
                            f"{column} 的用例 {case_id} 在 SRS §五 中声明的覆盖范围是 "
                            f"{sorted(declared)}，**不含 {req_id}**"
                            "——用例与需求对不上（门禁此前只查编号格式，故这类错位查不出来）",
                        )
                if not CASE_ID_PATTERN.fullmatch(case_id):
                    add(
                        "ERROR",
                        f"{column} 中的用例编号 {case_id!r} 格式非法"
                        "（应为 TC-xxx，或带类型前缀的 TC-F-xxx / TC-B-xxx 等）",
                    )
        if case_total == 0:
            add(
                "ERROR",
                "没有任何关联测试用例——写不出测试用例的需求 = 不合格需求"
                "（见 docs/03-测试与回归/测试体系与缺陷管理.md）",
            )
        if not split_multi(row.get("系统测试用例") or "") and not split_multi(
            row.get("验收测试用例") or ""
        ):
            add("WARN", "缺少系统级/验收级测试用例，仅有单元或集成测试覆盖")

        # --- 状态 ---
        status = (row.get("状态") or "").strip()
        if not status:
            add("ERROR", "状态为空")
        if strict and status not in {"已实现", "已测试", "已验收"}:
            add("ERROR", f"严格模式下状态 {status!r} 未达到可交付状态")

        # --- 与 SRS 一致性 ---
        if srs_ids and req_id not in srs_ids:
            add("ERROR", f"需求 {req_id} 在 SRS 文档中不存在（RTM 与 SRS 不一致）")

    # --- 重复编号 ---
    for req_id, count in seen_ids.items():
        if count > 1:
            result.issues.append(
                Issue("ERROR", req_id, f"需求编号重复出现 {count} 次——编号必须唯一")
            )

    # --- SRS 中未被 RTM 覆盖的需求 ---
    if srs_ids:
        uncovered = sorted(srs_ids - set(seen_ids))
        for req_id in uncovered:
            result.issues.append(
                Issue("ERROR", req_id, "SRS 中已定义但 RTM 中缺失（需求未被追溯）")
            )

    return result


def print_report(
    result: CheckResult,
    matrix_path: str,
    srs_path: str,
    registry: str = "",
    sample_mode: bool = False,
) -> None:
    print("=" * 74)
    print("门禁校验：需求追溯矩阵（RTM）完整性")
    print("=" * 74)
    print(f"追溯矩阵: {matrix_path}")
    if srs_path:
        print(f"SRS 文档: {srs_path}")
    print(f"需求条目: {result.requirements}")
    if registry:
        print(f"模块登记表: {registry}")
    print()

    if result.warnings:
        print(f"警告 {len(result.warnings)} 项：")
        for issue in result.warnings:
            print(f"  [WARN ] {issue.requirement}  {issue.message}")
        print()

    if result.errors:
        print(f"错误 {len(result.errors)} 项：")
        for issue in result.errors:
            print(f"  [ERROR] {issue.requirement}  {issue.message}")
        print()
        print("门禁结论：不通过 —— 不得通过需求评审 / 测试准出评审")
    elif sample_mode:
        # ⚠️ 样例数据**永远不得**被打成"覆盖率 100%"：那句话会被读成对本项目的结论。
        print(
            "自证结论：工具链可用（样例数据，**非本项目产物**）"
            "—— 本结论**不构成**本项目的追溯门禁结论"
        )
    else:
        print("门禁结论：通过 —— 需求双向追溯完整，覆盖率 100%")
        if result.warnings:
            print("（存在警告项，建议在评审记录中说明处置）")


def main(argv: Sequence[str] | None = None) -> int:
    make_console_encoding_safe()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        return _selftest()


    parser = argparse.ArgumentParser(
        description="需求追溯矩阵完整性校验（CI 门禁工具）"
    )
    parser.add_argument(
        "--matrix",
        default=None,
        help="追溯矩阵 CSV 路径（**缺省 = 本项目真实产物** "
        f"`{PROJECT_MATRIX}`；`--sample` 时为非本项目样例）",
    )
    parser.add_argument(
        "--srs",
        default=None,
        help="SRS 文档路径（用于一致性校验；**缺省 = 本项目真实产物** "
        f"`{PROJECT_SRS}`；传空字符串或 `--no-srs` 表示跳过该项校验）",
    )
    parser.add_argument(
        "--no-srs",
        action="store_true",
        help="跳过 SRS 一致性校验（等价于 --srs 传空；⚠ 跳过即失去"
        "「用例必须声明覆盖该需求」的语义校验，只能用于输入面不含 SRS 的场合）",
    )
    parser.add_argument("--repo-root", default=".", help="仓库根目录")
    parser.add_argument(
        "--no-registry",
        action="store_true",
        help="跳过模块号存在性校验（用于**工具可用性自证**：`docs/阶段外-待启用/_非本项目样例/` 的示例数据"
        "不属于本项目，不得拿本项目的模块登记表去判它）",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="**【自证模式】显式使用非本项目样例数据**（`docs/阶段外-待启用/_非本项目样例/`）"
        "验证工具链可用；本模式的结论**不构成**本项目的追溯门禁结论，"
        "输出**不会**出现「门禁结论：通过……覆盖率 100%%」",
    )
    parser.add_argument(
        "--strict", action="store_true", help="严格模式：状态必须为已实现/已测试/已验收"
    )
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)

    def resolve(p: str) -> str:
        """相对路径按 repo_root 解析；绝对路径原样使用。

        注意：不能无条件 os.path.join(repo_root, p)——
        当 p 是绝对路径时，Windows 下 join 会得到
        'D:\\Code\\D:\\Code\\...' 这种坏路径。
        """
        if not p:
            return ""
        return p if os.path.isabs(p) else os.path.join(repo_root, p)

    # ── 输入面装配：默认＝本项目真实产物；`--sample`＝显式索取样例 ──────────────
    matrix_path = resolve(args.matrix if args.matrix is not None
                          else (SAMPLE_MATRIX if args.sample else PROJECT_MATRIX))
    if args.no_srs or args.srs == "":
        srs_path = ""
    elif args.srs is not None:
        srs_path = resolve(args.srs)
    else:
        srs_path = resolve(SAMPLE_SRS if args.sample else PROJECT_SRS)

    def under_sample_dir(path: str) -> bool:
        if not path:
            return False
        root = os.path.normcase(os.path.abspath(resolve(SAMPLE_DIR))) + os.sep
        return os.path.normcase(os.path.abspath(path)).startswith(root)

    # 守则③：**样例不得悄悄顶替真实输入** —— 未显式索取 --sample 却把输入指到样例目录，直接判不通过。
    intrusive = [
        p for p in (matrix_path, srs_path) if (not args.sample) and under_sample_dir(p)
    ]
    if intrusive:
        print("=" * 74)
        print("门禁校验：需求追溯矩阵（RTM）完整性")
        print("=" * 74)
        for path in intrusive:
            print(f"样例数据不得顶替真实输入：{path}")
        print()
        print("门禁结论：不通过 —— 该路径属于**非本项目样例**，其通过与否都不是本项目的追溯结论；")
        print("           如确要用样例数据做**工具可用性自证**，请显式加 --sample。")
        return 1

    # 守则②：真实输入缺失 ⇒ 显式判不通过（rc=1），**绝不回落样例**。
    missing = [p for p in (matrix_path, srs_path) if p and not os.path.isfile(p)]
    if missing:
        print("=" * 74)
        print("门禁校验：需求追溯矩阵（RTM）完整性")
        print("=" * 74)
        label = "样例输入缺失" if args.sample else "真实输入缺失"
        for path in missing:
            print(f"{label}：{path}")
        print()
        print(
            "门禁结论：不通过 —— 输入缺失即**未能校验**；「未能校验」不得当成「通过」，"
            "也不得回落到样例数据。"
        )
        return 1

    # 自证模式（--sample）与"显式指定非默认输入"都要在结论之前亮明身份，
    # 避免任何一次"裸跑"的绿灯被误读成本项目的追溯结论。
    if args.sample:
        print("=" * 74)
        print("⚠️ 自证模式（--sample）：本次校验用的是**非本项目样例**"
              f"（`{SAMPLE_DIR}` 目录），**不是本项目产物**。")
        print("   样例里的模块号/需求号与 `WC-MODREG-001`/`WC-SRS-001` 无关，")
        print("   故其结论**不构成**本项目的门禁结论；本项目自查直接裸跑即可（默认即真实产物）。")
    else:
        explicit = args.matrix is not None or args.srs is not None
        is_project = (
            os.path.normcase(os.path.abspath(matrix_path))
            == os.path.normcase(os.path.abspath(resolve(PROJECT_MATRIX)))
        )
        if explicit and not is_project:
            print("=" * 74)
            print(f"⚠️ 注意：本次校验用的是**显式指定的非默认输入**（{matrix_path}），")
            print(f"   本项目的默认输入是 `{PROJECT_MATRIX}`；上述结论只对该输入成立。")

    result = check_matrix(
        matrix_path=matrix_path,
        srs_path=srs_path,
        known_modules=set()
        if (args.no_registry or args.sample)
        else load_known_modules(repo_root),
        strict=args.strict,
    )
    if args.sample or args.no_registry:
        registry = "（已跳过：样例数据/显式 --no-registry 不属于本项目）"
    else:
        registry = registry_status(repo_root)
    print_report(
        result,
        matrix_path=matrix_path,
        srs_path=srs_path,
        registry=registry,
        sample_mode=args.sample,
    )
    return 1 if result.errors else 0


# ────────────────────── 自证（每条判据配反例，反例必红） ──────────────────────
_SELF_HEADER = ("需求编号,需求名称,优先级,需求基线版本,设计模块号,设计文档章节,接口编号,"
                "实现代码位置,单元测试用例,集成测试用例,系统测试用例,验收测试用例,状态,备注")

def _selftest() -> int:
    """`--self-test`：**造一对"坏的／好的"输入，证明这条判据会红也会绿**。

    **射程（如实写，不冒充考了全部）**：本自证只考**矩阵内部一致性**里的核心那一条——
    「需求 → 测试用例」正向不断裂（跑时用 `--no-srs --no-registry` 关掉与外部输入有关的两项）。
    其余校验项（与 SRS 的一致性、模块号存在性）**不在本自证射程内**。
    """
    import subprocess
    import tempfile
    rows_common = ("REQ-F-901,自证用需求,P0,v1,M01,HLD-1,IF-001,src/x.rs::f,")
    # 反例：四个测试用例列**全空** ⇒ 正向断裂 ⇒ 必须红
    broken = _SELF_HEADER + "\n" + rows_common + ",,,,未测试,\n"
    # 正控：补齐四个测试用例 ⇒ 必须绿
    # ⚠ 用例号格式由工具校验：必须 `TC-xxx`（三位数）或带类型前缀（`TC-F-xxx` 等）。
    #   第一版我写成 `TC-1…TC-4` ⇒ **正控被判红**——那是**夹具写错**，不是工具没牙（如实留痕）。
    good = _SELF_HEADER + "\n" + rows_common + "TC-101,TC-201,TC-301,TC-401,已测试,\n"

    failures = []
    with tempfile.TemporaryDirectory(prefix="rtm-selftest-") as tmp:
        for tag, body, want_rc, want_word in (
            ("反例（某条需求没有任何测试用例 ⇒ 应红）", broken, 1, None),
            ("正控（补齐四个测试用例 ⇒ 应绿）", good, 0, None),
        ):
            p = os.path.join(tmp, "m.csv")
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(body)
            r = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--matrix", p, "--no-srs", "--no-registry"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            ok = (r.returncode == want_rc)
            print("  %s：rc=%d（期望 %d）%s" % (tag, r.returncode, want_rc, "OK" if ok else "*不符"))
            if not ok:
                failures.append(tag)
                for ln in ((r.stdout or "") + (r.stderr or "")).strip().split("\n")[-4:]:
                    print("      " + ln[:150])
            if tag.startswith("反例") and ok:
                hit = "REQ-F-901" in (r.stdout or "")
                print("      反例是否点名那条需求：%s" % ("是" if hit else "*否"))
                if not hit:
                    failures.append("反例未点名需求")
    if failures:
        print("  => 自证不通过：%s" % "；".join(failures))
        print("  => 按本项目口径：**这条守卫是装饰，拒绝合入**。")
        return 1
    print("  => 自证通过：这条判据在反例下变红、在正控下变绿（**射程见函数文档：只考矩阵内部一致性的核心那一条**）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
