"""门禁工具：改动范围检查（scope check）。

用途：在一次变更中，检查被修改的文件是否**超出了变更声明所覆盖的范围**。
这是"受控变更"的机器化闸门——防止静默改框架、防止顺手重构、防止越界改动。

依据：docs/04-配置与版本/配置管理与版本化.md（变更控制八步）、
      docs/01-流程与阶段/框架与模块共演化.md（R5 框架变更评审）。
      ★ 2026-10-08 注：`docs/**` 已于提交 `a7bb4fe` **整树删除**、内容并入 `ninedim/`；
        上面两条是**历史坐标**（现落点见 `ninedim/01-意图环/03-设计/设计-落位契约.md`），
        本处按"只引不复述"留存，**不代表盘上有那个路径**。

用法：
    # 用变更声明文件限定范围（**CI 就是这一条**）
    python scripts/verify/scope_check.py --base main --scope .scope-declaration.json

    # 直接给允许的路径前缀
    python scripts/verify/scope_check.py --base HEAD~1 --allow src/ --allow tests/

    # 演示模式（无需 git 变更）
    python scripts/verify/scope_check.py --demo

    # 自证模式（每条判据各造一个**会红**的反例；含"判定器蒙眼"探针）
    python scripts/verify/scope_check.py --self-test

退出码：0 = 范围合规；1 = 越界（门禁不通过）；2 = **未能校验**
        （未声明任何范围／声明文件缺失／声明为空／环境不可用 —— **不是通过**）。

★ fail-closed 口径（2026-10-08 修，对应 `WC-RV-R0-001` 的 **C-04** 与复核 F-11）：
  **"没有声明"曾走 rc=0**（打两条 `[WARN] …跳过范围校验` 就放行）——那是
  "未能校验被读成校验通过"，与仓内纪律『未能校验 ≠ 通过』相反。
  现在：**缺声明 ⇒ rc=2**（`--scope` 指定了却不在盘上、`allowed` 为空数组，一律同办）；
  只有"**读到声明 且 判过**"才可能给 rc=0。★ CI 的 `scope` 作业对任何非零都阻断。

────────────────────────────────────────────────────────────────────────────
本文件对上游模板（06-swe-gb/tools/scope_check.py）的**必要改动**及其证据
────────────────────────────────────────────────────────────────────────────
上游模板假定"项目 == 仓库根"。本项目不是：world-core 位于仓库
07-agent-native-os 的**子目录**，且仓库根还有 agentd/（Go）、00-总纲.md 等
非本子项目内容。原样照搬会得到**一个永远红、且红得没有意义**的门禁。

2026-09-26 复现（在  内，完全照 CI 的调用方式）：

    $ python scripts/verify/scope_check.py --base HEAD~3 --scope .scope-declaration.json
    [越界] "docs/S0-/347/253/213/351/241/271/策划-WC-FSR-001-v0.1.md"
    [越界] src/main.rs
    ...
    门禁结论：不通过 —— 存在越界改动
    $ echo $?   → 1

三个路径口径缺陷（互相独立，任一个都足以让门禁失效）：

  D-1 `git diff --name-only` 默认输出**仓库根相对**路径，于是每个路径都带
      `` 前缀，声明里的 `src/` / `tests/` **永远匹配不上**。
      （对照：`git ls-files` 默认输出**当前目录相对**路径——同一工具内两套口径。）
  D-2 git 默认 `core.quotepath=true`，非 ASCII 路径被八进制转义并加引号，
      路径变成 `"docs/S0-/347/253/..."`，中文目录的文档**必然越界**。
  D-3 `git status --porcelain` 的路径是**仓库根相对**（porcelain 格式不受
      `status.relativePaths` 影响），与 D-1 同类不同源。

处置：本工具改为**子目录布局感知**——
  * 先 `rev-parse --show-toplevel` 求仓库根，再算出本项目的相对前缀（本处为
    `world-core`；若项目就在仓库根，前缀为空串，行为与上游模板一致）；
  * 所有 git 调用统一在**仓库根**执行，并加 `-c core.quotepath=false` 与 `-z`
    （NUL 分隔、不转义），于是路径口径唯一：**仓库根相对、原始 UTF-8**；
  * 再把前缀剥掉，得到项目根相对路径，与声明文件里的 `src/` 等**同口径**；
  * 落在前缀之外的变更**不当越界**，而是单独列为「另属他门」并打印出来——
    不静默丢弃（静默丢弃等于悄悄扩大门禁的豁免面）。
  * 例外是 `JOINT_JURISDICTION` 里那几个：它们虽在仓库根、却属于本项目的**框架契约**
    （门禁工作流本身、PR 模板）——把它们拉回管辖，否则会出现
    "**改门禁不需要任何声明**"这种最不该有的漏洞。原因见该常量的注释。

如此，CI 的 `working-directory: world-core` + `--scope .scope-declaration.json`
**无需改动**即可正确工作（门禁自身 gate.yml 因此不必变更，避开 R5 绕行）。

⚠️ 本文件的常量（ALWAYS_ALLOWED / SENSITIVE_PATHS）已从上游的示例项目
重新实例化为 world-core 的**真实契约面**，改它等于改门禁语义。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple


def make_console_encoding_safe() -> None:
    r"""让本脚本在**非 UTF-8 控制台**（Windows 默认 GBK/cp936）下**不再崩溃**。

    病灶（2026-09-27 实测）：本脚本的提示串含 `⚠`(U+26A0)/`→`(U+2192)/`─`(U+2500) 等
    GBK 编不出的符号，`print()` 抛 `UnicodeEncodeError` ⇒ **rc=1 假失败**——
    对 `scope_check.py` 尤其危险：它的 rc=1 语义是"**越界，阻断**"，
    于是一次编码崩溃会被读成一次真实的越界判定（**结论失真**）。
    修法（取题目所给两案中的 ②）：把 **`stdout`** 的 `errors` 重配为 `replace`（**不改 encoding**）
    ⇒ GBK 下中文仍按 GBK 输出、只有编不出的符号降级为 `?`，**判据文字一字不删**；UTF-8 下逐字节等价。
    ⚠ **`stderr` 不动**：Python 3.5+ 起 `sys.stderr` 默认就是 `backslashreplace` —— 本脚本的
    `[ERROR] … ⚠️ 注意` 一行正是走 stderr，**实测 GBK 下本来就不崩**（打印出 `\u26a0\ufe0f`）；
    改成 `replace` 反而把可复原的 `\u26a0` 变成不可复原的 `?`（信息更少），故不改。
    不取 ①（逐字符换 ASCII）的理由见 `scripts/verify/trace_matrix.py` 同名函数：白名单会随新符号复发。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:  # 非 TextIOWrapper（被捕获/重定向）时跳过
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):  # pragma: no cover - 不可重配的流
        pass

# 无论什么变更都允许修改的路径（元数据类，不构成范围越界）
#
# ⚠️ 为什么必须包含 .scope-declaration.json 本身：
# 该文件是"声明"的载体。若它自己不在允许范围内，就会出现死循环——
# 「为了让改动合规，你得先改声明；但改声明本身就违规」。
#
# 说明性/法律性文档同理：README、CONTRIBUTING、NOTICE、LICENSE
# 是**跟着任何变更走**的元数据，不该成为越界。
ALWAYS_ALLOWED: Sequence[str] = (
    "CHANGELOG.md",
    ".gitignore",
    ".scope-declaration.json",
    "README.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "LICENSE",
    "LICENSE-MIT",
    "LICENSE-APACHE",
)

# 敏感路径：改动这些一律需要显式声明（框架契约与门禁自身）
#
# 本项目里"框架契约"= 世界的法律与账本语义，具体是：
#   ontology.json  词表/本体——改它等于改世界的法律，所有投影共用这一份
#   src/lib.rs     唯一写入口 commit()
#   src/event.rs   信封与事件构造（world/kind/id/seq/at/actor/flags/body）
#   src/ontology.rs 法律执行者（校验）
#   src/ledger.rs  账本落笔（只追加、纯文本）
#   tests/         证据本身——改测试以求通过是最经典的作弊路径
#   tools/         门禁工具
#   .github/workflows/ 门禁自身
SENSITIVE_PATHS: Sequence[str] = (
    "src/ontology_definition/ontology.json",
    "src/gate/policy.json",
    "src/lib.rs",
    "src/common/event.rs",
    "src/ontology_definition/mod.rs",
    "src/ledger/mod.rs",
    "scripts/test/",
    "scripts/",
    ".github/workflows/",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "ninedim/02-枢纽A-前置闸/",
)

# 明确排除在范围校验之外的路径。
# 本项目当前**没有**需要豁免的路径：连 docs/阶段外-待启用/_非本项目样例/ 也照管（它是模板示例，
# 改它同样要有声明）。留空串表是明确表态，不是遗漏。
SCOPE_EXCLUDED_PREFIXES: Sequence[str] = ()

# 「共同管辖」路径：位于本项目前缀**之外**、却属于本项目框架契约的文件
# （仓库根相对路径）。
#
# 为什么需要这个概念：`gate.yml` 曾经的位置是错的——**GitHub 只发现
# 仓库根 `.github/workflows/` 下的工作流**，放在子目录里等于不存在（WC-SCMP-001
# §8.4 G-11）。修好之后，门禁自身与 PR 模板都在仓库根，于是它们落在本工具的
# "辖区之外"。若不特殊处理，就会出现最荒诞的局面：
# **改门禁不需要任何声明，而且只被当成"另属他门"一笔带过。**
#
# 因此把它们显式拉回管辖：既要**在声明范围内**（改门禁必须写进
# `.scope-declaration.json`），也会**命中 SENSITIVE_PATHS**（触发 R5 评审提示）。
JOINT_JURISDICTION: Sequence[str] = (
    ".github/workflows/gate.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
)


def _matches(path: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/").rstrip("/")
    if not pattern:
        return False
    return path == pattern or path.startswith(pattern + "/")


@dataclass
class ScopeResult:
    changed: List[str] = field(default_factory=list)
    allowed: List[str] = field(default_factory=list)
    in_scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    sensitive_touched: List[str] = field(default_factory=list)
    # 落在本项目前缀之外、因而不由本门禁判定的变更（不静默丢弃，见 D 说明）
    elsewhere: List[str] = field(default_factory=list)


def _git(repo_root: str, args: Sequence[str]) -> str:
    """在指定目录执行 git。

    统一加 `-c core.quotepath=false`：禁止八进制转义路径（缺陷 D-2）。
    调用方需要路径时一律再加 `-z`，用 NUL 分隔以免路径含空格/换行被切碎。
    """
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} 执行失败")
    return proc.stdout


def _split_z(out: str) -> List[str]:
    return [tok for tok in out.split("\0") if tok]


def _porcelain_paths(out: str) -> List[str]:
    """解析 `git status --porcelain -z`。

    -z 下重命名/复制会**多跟一个"原路径"条目**，必须吃掉它，
    否则「原路径」会被当成一个独立变更，产生幽灵越界项。
    """
    toks = _split_z(out)
    paths: List[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        status = tok[:2]
        paths.append(tok[3:])
        i += 2 if status[:1] in ("R", "C") else 1
    return paths


def find_toplevel(repo_root: str) -> str:
    out = _git(repo_root, ["rev-parse", "--show-toplevel"]).strip()
    return os.path.abspath(out).replace("\\", "/")


def project_prefix(toplevel: str, repo_root: str) -> str:
    """项目根相对仓库根的前缀；项目即仓库根时返回空串。"""
    rel = os.path.relpath(os.path.abspath(repo_root), toplevel).replace("\\", "/")
    return "" if rel == "." else rel.rstrip("/")


def _to_project_relative(
    paths: Sequence[str], prefix: str
) -> Tuple[List[str], List[str]]:
    """把仓库根相对路径映射为项目根相对路径，并分出项目之外的路径。"""
    inside: List[str] = []
    outside: List[str] = []
    pfx = f"{prefix}/" if prefix else ""
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        if not path or path.startswith(".."):
            continue
        if not pfx:
            inside.append(path)
        elif path == prefix:
            continue  # 前缀本身是目录，不应作为文件出现
        elif path.startswith(pfx):
            inside.append(path[len(pfx) :])
        else:
            outside.append(path)
    return inside, outside


def git_changed_files(
    base: str, toplevel: str, prefix: str
) -> Tuple[List[str], List[str]]:
    """返回 (项目根相对的变更文件, 项目之外的变更文件)（含未跟踪文件）。"""
    try:
        raw: List[str] = []
        for args in (
            ["diff", "--name-only", "-z", f"{base}...HEAD"],
            ["diff", "--name-only", "-z"],
            ["diff", "--name-only", "-z", "--cached"],
        ):
            raw.extend(_split_z(_git(toplevel, args)))
    except RuntimeError:
        # 可能是首次提交、base 不存在等情况
        raw = _porcelain_paths(_git(toplevel, ["status", "--porcelain", "-z"]))

    untracked = ["ls-files", "--others", "--exclude-standard", "-z"]
    if prefix:
        untracked += ["--", prefix]
    raw.extend(_split_z(_git(toplevel, untracked)))

    inside, outside = _to_project_relative(raw, prefix)
    return sorted(set(inside)), sorted(set(outside))


def evaluate(changed: Sequence[str], allowed: Sequence[str]) -> ScopeResult:
    result = ScopeResult(changed=list(changed), allowed=list(allowed))

    def matches(path: str, pattern: str) -> bool:
        return _matches(path, pattern)

    for path in changed:
        # 排除路径：不参与范围校验
        if any(matches(path, x) for x in SCOPE_EXCLUDED_PREFIXES):
            continue
        if any(matches(path, a) for a in ALWAYS_ALLOWED):
            result.in_scope.append(path)
            continue
        if any(matches(path, a) for a in allowed):
            result.in_scope.append(path)
        else:
            result.out_of_scope.append(path)

        if any(matches(path, s) for s in SENSITIVE_PATHS):
            result.sensitive_touched.append(path)

    return result


def load_scope_declaration(path: str) -> List[str]:
    """读取变更范围声明文件。

    支持两种格式：
      {"allowed": ["src/", "scripts/test/"]}
      或 ["src/", "scripts/test/"]
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        allowed = data.get("allowed", [])
    elif isinstance(data, list):
        allowed = data
    else:
        raise ValueError("范围声明文件必须是数组或含 allowed 字段的对象")
    if not isinstance(allowed, list):
        raise ValueError("allowed 必须是字符串数组")
    return [str(a) for a in allowed]


def print_report(result: ScopeResult, base: str, prefix: str) -> None:
    scope_name = f"{prefix}/" if prefix else "（仓库根）"
    print("=" * 74)
    print("门禁校验：改动范围（scope check）")
    print("=" * 74)
    print(f"基线: {base}")
    print(f"管辖区: {scope_name}")
    print(f"变更文件: {len(result.changed)}    声明范围: {len(result.allowed)} 条")
    print()

    if result.allowed:
        print("声明的允许范围：")
        for item in result.allowed:
            print(f"  - {item}")
        print()

    print(f"范围内文件 {len(result.in_scope)} 个：")
    for path in result.in_scope:
        print(f"  [ OK ] {path}")
    print()

    if result.out_of_scope:
        print(f"越界文件 {len(result.out_of_scope)} 个：")
        for path in result.out_of_scope:
            print(f"  [越界] {path}")
        print()

    if result.elsewhere:
        print(f"管辖区之外的变更 {len(result.elsewhere)} 个（本门禁不判定，另属他门）：")
        for path in result.elsewhere:
            print(f"  [另属] {path}")
        print("  说明：这些路径不属于本子项目，由各自的门禁负责；此处列出以免静默遗漏。")
        print()

    if result.sensitive_touched:
        print("触及敏感路径（框架契约 / 门禁自身）：")
        for path in result.sensitive_touched:
            print(f"  [!] {path}")
        print("  说明：改动这些文件等于修改框架契约或门禁规则，")
        print("        必须走 R5 框架变更评审并更新变更申请与影响分析。")
        print()


def load_demo_allowed() -> List[str]:
    """自证模式用的允许范围：**优先读真实声明**，读不到才退回内置表。"""
    here = os.path.dirname(os.path.abspath(__file__))
    decl = os.path.join(os.path.dirname(here), ".scope-declaration.json")
    try:
        with open(decl, encoding="utf-8") as f:
            data = json.load(f)
        got = [str(x) for x in data.get("allowed", [])]
        if got:
            return got
    except (OSError, ValueError):
        pass
    return ["src/", "scripts/test/", "ontology.json", "NOTICE.md"]


def demo() -> int:
    """**自证模式**：跑一个合规例、一个越界反例，并**断言两者的结论都对**。

    2026-09-27 修（`W-05`）。原实现两例都只**打印**、函数末尾恒 `return 0`——
    连"越界反例 rc=1"都只是**字符串**（原文 `print("…越界反例 rc=1…")`），
    没有任何判定。后果是实测过的：把判定器**蒙上眼**（令 `evaluate` 恒不报越界）之后，
    `--demo` 仍打印"门禁不是橡皮图章"且 rc=0 ⇒ 该自证是装饰。

    现在两条断言都真判：
    - ① 合规例**不得**被判越界；
    - ② 越界反例**必须**被判越界（蒙眼 ⇒ 本条红 ⇒ rc=1）。
    """
    # 允许范围取自**真实声明** `.scope-declaration.json`（同一份判据面），取不到才退回内置表。
    # 为什么不能写死 `["src/","scripts/test/"]`：那样"合规例"里的 `ontology.json` 会被判越界
    # —— 演示里的正例本身就不合规，自证会把**工具没坏**误报成**判定器误伤**。
    allowed = load_demo_allowed()
    failures = []

    print("=" * 74)
    print("演示 1/2：合规例（期望结论：通过）")
    print("=" * 74)
    ok = evaluate(
        [
            "src/ledger.rs",
            "scripts/test/acceptance.rs",
            "ontology.json",
            "NOTICE.md",
        ],
        allowed,
    )
    print_report(ok, base="--demo--", prefix="world-core")
    print(f"→ 结论：{'通过' if not ok.out_of_scope else '不通过'}")
    if ok.out_of_scope:
        failures.append("合规例被判越界：%s（判定器会误伤）" % ok.out_of_scope)
    print()

    print("=" * 74)
    print("演示 2/2：反例（期望结论：不通过——这正是门禁该咬人的地方）")
    print("=" * 74)
    bad = evaluate(["src/ledger.rs", "agentd/internal/job/job.go"], allowed)
    print_report(bad, base="--demo--", prefix="world-core")
    print(f"→ 结论：{'通过' if not bad.out_of_scope else '不通过'}")
    if not bad.out_of_scope:
        failures.append(
            "越界反例**未被**判越界 —— 判定器蒙眼（橡皮图章），本自证拒绝给出绿灯"
        )
    print()

    if failures:
        print("自证结论：**不通过** —— %d 项：" % len(failures))
        for x in failures:
            print("  [FAIL] " + x)
        print("（一个从不失败的检查不是检查，是装饰）")
        return 1
    print("自证结论：通过 —— 合规例 rc=0、越界反例 rc=1，门禁不是橡皮图章。")
    return 0


# ── 自证（`--self-test`）：每条判据各造一个**会红**的反例 ──────────────────────
# 为什么不复用 `demo()`：`demo()` 直接调内部函数，验的是**判定器**；
#   而"缺声明 ⇒ rc=2"这条判据住在 `main()` 的**入口分支**里，只有**跑真入口、看真 rc**
#   才在被证之列（本仓教训：「自证通过 ≠ 判据有效」——签名改了而自证只喂旧形态，照样全绿）。
# 判据清单（与 main() 的分支一一对应）：
#   ① 合规 ⇒ rc=0（正控）                ② 越界 ⇒ rc=1
#   ③ 未声明 ⇒ rc=2                      ④ `--scope` 文件缺失 ⇒ rc=2
#   ⑤ 声明为空数组 ⇒ rc=2                ⑥ 声明存在但坏 JSON ⇒ rc=1（配置错误，阻断）
#   ⑦ 环境不可用（仓根不存在）⇒ rc=2      ⑧ 环境不可用（git 调用抛错）⇒ rc=2
#   ⑨ **蒙眼探针**：把 `evaluate` 弄瞎后，②那条反例**不许**再 rc=1
#      ——它证明②的红**真的来自判定器**，而不是别的什么碰巧给了 1。
def _run_cli(argv: Sequence[str]) -> Tuple[int, str]:
    """跑一次**真入口** `main(argv)`，把 stdout/stderr 一起收回来。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            rc = main(argv)
        except SystemExit as exc:  # argparse 的用法错
            rc = int(exc.code or 2)
    return rc, buf.getvalue()


def _git_init(root: str) -> bool:
    proc = subprocess.run(
        ["git", "init", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode == 0


def self_test() -> int:
    """每条判据一个反例 ＋ 一个蒙眼探针。**反例不变红即判本判定器是装饰。**"""
    failures: List[str] = []
    checks = 0
    cases: List[str] = []

    def expect(name, argv, want_rc, must_contain=None, must_not_contain=None):
        nonlocal checks
        checks += 1
        cases.append(name)
        rc, out = _run_cli(list(argv))
        ok = rc == want_rc
        why = [] if ok else [f"rc={rc}（期望 {want_rc}）"]
        if must_contain and must_contain not in out:
            ok = False
            why.append(f"输出里没有「{must_contain}」")
        if must_not_contain and must_not_contain in out:
            ok = False
            why.append(f"输出里不该有「{must_not_contain}」")
        if ok:
            print(f"[OK ] {name} ⇒ rc={rc}（期望 {want_rc}）")
        else:
            print(f"[FAIL] {name} ⇒ " + "；".join(why))
            failures.append(f"{name}：{'；'.join(why)}")
        return rc, out

    tmp = tempfile.mkdtemp(prefix="scope_check_selftest_")
    try:
        if not _git_init(tmp):
            print("[FAIL] 自证环境不可用：`git init` 跑不起来 ⇒ 本自证**未能校验**（不是通过）")
            return 2
        os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "agentd"), exist_ok=True)
        decl = os.path.join(tmp, ".scope-declaration.json")
        with open(decl, "w", encoding="utf-8") as fh:
            json.dump({"allowed": ["src/"]}, fh)
        with open(os.path.join(tmp, "src", "ledger.rs"), "w", encoding="utf-8") as fh:
            fh.write("// fixture\n")
        outside = os.path.join(tmp, "agentd", "job.go")
        scope_argv = ["--repo-root", tmp, "--scope", ".scope-declaration.json"]

        # ① 正控：全部改动都在声明范围内 ⇒ rc=0
        expect("正控 合规（件全在声明范围内）", scope_argv, 0, must_contain="门禁结论：通过")

        # ② 反例：多一件越界件 ⇒ rc=1
        with open(outside, "w", encoding="utf-8") as fh:
            fh.write("package main\n")
        expect("反例 越界件", scope_argv, 1, must_contain="[越界] agentd/job.go")

        # ⑨ 蒙眼探针：把 evaluate 弄瞎 ⇒ ②必须**不再** rc=1
        real_evaluate = globals()["evaluate"]

        def _blind(changed, allowed):
            return ScopeResult(changed=list(changed), allowed=list(allowed))

        globals()["evaluate"] = _blind
        try:
            checks += 1
            cases.append("蒙眼探针")
            rc_blind, _ = _run_cli(scope_argv)
            if rc_blind == 1:
                print("[FAIL] 蒙眼探针 ⇒ 判定器蒙眼后越界反例**仍然** rc=1 —— 那条红不是判定器给的")
                failures.append("蒙眼探针：越界反例的红不来自 evaluate（自证是装饰）")
            else:
                print(f"[OK ] 蒙眼探针 ⇒ evaluate 蒙眼后不再 rc=1（rc={rc_blind}）⇒ 反例确由判定器产生")
        finally:
            globals()["evaluate"] = real_evaluate
        os.remove(outside)

        # ③ 反例：未声明任何范围 ⇒ rc=2（fail-closed，原为 rc=0）
        expect(
            "反例 未声明（裸跑）",
            ["--repo-root", tmp],
            2,
            must_contain="未能校验",
            must_not_contain="门禁结论：通过",
        )

        # ④ 反例：点了 --scope 而文件不在盘上 ⇒ rc=2（原只打 [WARN] 后继续）
        #    ★ 故意**同时给 `--allow src/`**：这样只有"声明文件缺失"这一条判据能产生 rc=2，
        #      该分支被回退成"WARN 后继续"时，本反例会退回 rc=0（那条判据因此**被测住**）。
        expect(
            "反例 声明文件缺失（同时给了 --allow）",
            ["--repo-root", tmp, "--scope", ".no-such-decl.json", "--allow", "src/"],
            2,
            must_contain="未能校验",
        )

        # ⑤ 反例：声明在、但 allowed 为空数组 ⇒ rc=2（"空声明"＝没声明）
        with open(decl, "w", encoding="utf-8") as fh:
            json.dump({"allowed": []}, fh)
        expect("反例 声明为空数组", scope_argv, 2, must_contain="未能校验")

        # ⑥ 反例：声明在、但 JSON 坏 ⇒ rc=1（配置错误 ⇒ 阻断；不许降级成跳过）
        with open(decl, "w", encoding="utf-8") as fh:
            fh.write("{ this is not json ")
        expect("反例 声明坏 JSON", scope_argv, 1, must_contain="无法解析")

        # ⑦ 反例：仓根不存在 ⇒ rc=2（原实现抛 NotADirectoryError 崩栈）
        expect(
            "反例 仓根不存在",
            ["--repo-root", os.path.join(tmp, "no-such-dir"), "--allow", "src/"],
            2,
            must_contain="未能校验",
        )

        # ⑧ 反例：git 调用抛错（模拟 git 不可用）⇒ rc=2
        with open(decl, "w", encoding="utf-8") as fh:
            json.dump({"allowed": ["src/"]}, fh)
        real_find = globals()["find_toplevel"]

        def _boom(_root):
            raise RuntimeError("模拟：git 不可用")

        globals()["find_toplevel"] = _boom
        try:
            expect("反例 git 不可用", scope_argv, 2, must_contain="未能校验")
        finally:
            globals()["find_toplevel"] = real_find
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print("自证结论：**不通过** —— %d 项（共 %d 条）：" % (len(failures), checks))
        for x in failures:
            print("  [FAIL] " + x)
        print("（一个从不失败的检查不是检查，是装饰）")
        return 1
    print(
        "自证结论：通过 —— %d 条（正控 1 ＋ 反例 7 ＋ 蒙眼探针 1）："
        "每条判据都有会红的反例，且越界那条的红确由判定器产生。" % checks
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    make_console_encoding_safe()

    parser = argparse.ArgumentParser(description="改动范围门禁校验")
    parser.add_argument("--base", default="main", help="比较基线（分支/标签/提交）")
    parser.add_argument("--scope", default="", help="变更范围声明 JSON 文件")
    parser.add_argument(
        "--allow", action="append", default=[], help="允许的路径前缀，可重复"
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="子项目根目录（声明与允许范围都相对它；默认当前目录）",
    )
    parser.add_argument("--demo", action="store_true", help="演示模式，不调用 git")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="自证模式：每条判据各造一个会红的反例（含「判定器蒙眼」探针）",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.demo:
        return demo()

    repo_root = os.path.abspath(args.repo_root)

    allowed: List[str] = list(args.allow)
    if args.scope:
        scope_path = os.path.join(repo_root, args.scope)
        if not os.path.isfile(scope_path):
            # ★ fail-closed（2026-10-08，C-04）：调用方**点名了**宣言文件而它不在盘上
            #   ⇒ 本次校验**不完整** ⇒ rc=2「未能校验」。
            #   原实现只打一条 [WARN] 就继续（有 --allow 时照跑、没有时一路 rc=0）
            #   ⇒ "声明读不到"被折算成"没有越界"，正是本仓禁的那一类。
            print(
                f"[ERROR] 范围声明文件不存在：{scope_path}\n"
                "        ⇒ **未能校验**（rc=2）——声明读不到 ≠ 没有越界。\n"
                "        处置：修正 `--scope` 的路径后重跑；不得为了绕过而删掉 `--scope`。",
                file=sys.stderr,
            )
            return 2
        try:
            allowed.extend(load_scope_declaration(scope_path))
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            # 声明文件存在但读不了 —— 这是**配置错误**，不是"没有声明"。
            # 必须报错退出，不能静默降级为"跳过校验"：
            # 否则一个写坏的声明文件就等于把门禁关掉了。
            print(
                f"[ERROR] 范围声明文件无法解析：{scope_path}\n"
                f"        原因：{exc}\n"
                "        该文件必须是合法 JSON（对象含 allowed 字段，或直接是数组）。\n"
                "        ⚠️ 注意：JSON **不支持注释**。说明性文字请写在 "
                "ninedim/01-意图环/03-设计/设计-落位契约.md 所指的落点，不要写进本文件。\n"
                "        处置：修正该文件后重跑；不得为了绕过而删掉 --scope。",
                file=sys.stderr,
            )
            return 1

    if not allowed:
        # ★ fail-closed（2026-10-08，C-04 后半）：**缺声明 ⇒ rc=2（未能校验）**。
        #   原实现打两条 [WARN] 后 `return 0` —— "没有声明"被读成"没有越界"。
        #   仓根 `.scope-declaration.json` 明明存在，而裸跑却静默放行，等于把门禁关掉。
        print(
            "[ERROR] 未声明任何允许范围（--allow / --scope）⇒ **未能校验**（rc=2）。",
            file=sys.stderr,
        )
        print(
            "        ★ 「没有声明」不等于「没有越界」：缺声明时本门禁**不给通过**。",
            file=sys.stderr,
        )
        print(
            "        处置：填变更范围声明（CI 用的就是 "
            "`--scope .scope-declaration.json`），不要靠删参数绕过。",
            file=sys.stderr,
        )
        return 2

    try:
        toplevel = find_toplevel(repo_root)
        prefix = project_prefix(toplevel, repo_root)
        changed, elsewhere = git_changed_files(args.base, toplevel, prefix)
    except (RuntimeError, OSError) as exc:
        # ★ OSError 一并接住：`--repo-root` 指向不存在的目录时，`subprocess.run(cwd=…)`
        #   抛的是 `NotADirectoryError`（它**不是** RuntimeError）⇒ 原实现直接崩栈，
        #   既没结论串、也说不清是"未能校验"。现在统一折成 rc=2。
        print(f"[ERROR] 无法定位仓库根／执行 git 变更检测：{exc}", file=sys.stderr)
        print("        ⇒ **未能校验**（rc=2）—— 环境不可用 ≠ 通过。", file=sys.stderr)
        return 2

    # 把「共同管辖」的辖区外文件拉回管辖（仓库根相对路径，见 JOINT_JURISDICTION）
    joint = [
        p
        for p in elsewhere
        if any(_matches(p, j) for j in JOINT_JURISDICTION)
    ]
    if joint:
        changed = sorted(set(changed) | set(joint))
        elsewhere = [p for p in elsewhere if p not in joint]

    if not changed:
        print(f"管辖区 {'/'.join([prefix]) if prefix else '（仓库根）'} 内没有检测到变更文件，范围检查通过。")
        if elsewhere:
            print("管辖区之外另有变更（本门禁不判定）：")
            for path in elsewhere:
                print(f"  [另属] {path}")
        return 0

    result = evaluate(changed, allowed)
    result.elsewhere = elsewhere
    print_report(result, base=args.base, prefix=prefix)

    if result.out_of_scope:
        print("门禁结论：不通过 —— 存在越界改动")
        print("  处置：补充变更范围声明，或撤回越界改动，或走变更评审批准扩展范围。")
        return 1
    print("门禁结论：通过 —— 全部改动在声明范围内")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
