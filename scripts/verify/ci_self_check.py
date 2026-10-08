"""门禁自检：确保门禁没有被"悄悄削弱"。

放在 CI 里跑。检查的是**门禁本身**的完整性，不是业务代码。

为什么需要它（2026-09-21 的真实事故）：
    `.github/workflows/` 下的门禁工作流里，scope 作业曾带 `continue-on-error: true`，
    导致它**无论退出码为何都不阻断**。而它是唯一的"受控变更"机器闸门——
    也就是说，静默改框架、越界重构完全没有拦截。
    更糟的是同一时期 `.scope-declaration.json` 不是合法 JSON，
    所以即便去掉 continue-on-error 也会失败。

    这类问题无法靠"读一遍代码"发现，因为**门禁看起来是配好的**。
    所以要用一个脚本盯住它。

用法：
    python scripts/verify/ci_self_check.py        # 退出码 0 = 通过

退出码：0 = 通过；1 = 发现问题。

────────────────────────────────────────────────────────────────────────────
本文件对上游模板（06-swe-gb/tools/ci_self_check.py）的**必要改动**及证据
────────────────────────────────────────────────────────────────────────────
上游把工作流路径写死为 `<项目根>/.github/workflows/gate.yml`。本项目不成立，
而且不成立的方式是**致命的**：

  **GitHub Actions 只发现 `<仓库根>/.github/workflows/` 下的工作流。**
  本项目 `` 是仓库的子目录，工作流原先放在
  `.github/workflows/gate.yml` —— **GitHub 根本看不见它**。
  2026-09-26 实测：`gh run list --limit 10` 输出为空，且仓库根下不存在
  `.github/workflows/`。也就是说，CI **不是"没跑过"，而是"结构上不可能跑"**。

  同一个根因（把"项目 == 仓库根"当成前提）在本项目已经出现过三次：
  `scripts/verify/scope_check.py` 的路径口径（WC-SCMP-001 §8.4 G-09）、
  本文档所述的**工作流位置**（G-11）、以及 PR 模板的位置（同 G-11）。

处置：工作流与 PR 模板移到**仓库根** `.github/`；本脚本改为**向上定位仓库根**
并扫描其 `.github/workflows/*.yml`，因此无论从 ``（CI 的
`working-directory`）还是从仓库根运行都能找到它。同时把检查面从"单文件"扩到
"全部工作流"——这样将来若有人把某个作业搬到别的工作流里偷偷去掉
`continue-on-error` 的约束，也照样会被抓住。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

def make_console_encoding_safe() -> None:
    r"""让本脚本在**非 UTF-8 控制台**（Windows 默认 GBK/cp936）下**不再崩溃**。

    病灶（2026-09-27 实测）：本脚本输出的 `⇒`(U+21D2)/`⚠`(U+26A0)/`✅`(U+2705) 在 GBK 下
    编不出，`print()` 抛 `UnicodeEncodeError`；更糟的是**它调用的子进程同样会崩**
    （见 `CHILD_ENV`），于是本脚本把"工具自身崩了"报成"判定器自证失败 / 准入隔离不通过"
    ⇒ **rc=1 假失败**（把"工具坏了"误报成"项目违规"）。

    修法（取题目所给两案中的 ②）：`stdout` 的 `errors` 置 `replace`（**不改判据、一字不删告警文字**），
    并沿用本脚本**既有的显式 UTF-8** 口径（CI 与 pwsh 均按 UTF-8 解码它的输出；题目 ② 明列
    "`errors='replace'` 或 UTF-8"，二者本脚本同时具备）。UTF-8 环境下逐字节等价，既有证据不受影响。
    ⚠ **`stderr` 不动**：Python 3.5+ 起 `sys.stderr` 默认就是 `backslashreplace`（本来就不崩、
    且保留字符身份）；改成 `replace` 反而减少信息，故不改。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:  # 非 TextIOWrapper（被捕获/重定向）时跳过
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):  # pragma: no cover - 不可重配的流
        pass


make_console_encoding_safe()

#: 子进程的标准流编码**显式契约**：父进程按 `encoding="utf-8"` 解码子进程输出，
#: 故必须让子进程按 UTF-8 写（`PYTHONIOENCODING`），否则在 GBK 控制台上
#: 子进程写 GBK 字节、父进程按 UTF-8 解 ⇒ 报错文本变乱码（**诊断证据失真**）。
#: ⚠️ 这不是"用环境变量绕过缺陷"：子进程自身的崩溃已由各自的
#: `make_console_encoding_safe()` 修掉；这里补的是**父子进程间的编码契约**。
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

# ★ 2026-10-07 修（现取病灶）：本文件在 `scripts/verify/` ⇒ 仓根＝**上三级**。
#   原来 `dirname(dirname(...))` 只上溯两级 = `scripts/` ⇒ 三条检查全打在 `scripts/` 底下：
#     ① 找 `scripts/.scope-declaration.json`（真件在仓根）⇒ 假报「缺少」；
#     ② 找 `scripts/Cargo.toml`（crate 在仓根）⇒ 假报「找不到」；
#     ③ 找 `scripts/scripts/verify/admission_evidence.py` ⇒ 假报「判据不存在」。
#   ⇒ 裸跑 rc=1，且**每一条都是假红**（判据在、只是根算错了一层）。
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 仓根
SCOPE_JSON = os.path.join(ROOT, ".scope-declaration.json")

# 必须存在的作业（少一个都意味着某道门禁没了）
# ★ 2026-09-28 补三个：本清单原为 5 项（`smoke/unit-test/gate-self-test/traceability/scope`），
#   而 `gate.yml` 在 2026-09-27 另加了三个门禁作业
#   （`openspec-validate` 形态门禁 / `spec-bridge` 规格层守卫 / `module-graph` 原子化机核）。
#   ⇒ **原来的清单看不见它们**：`check_jobs` 的规则是"含必需作业的文件必须含全部必需作业"，
#   于是**整个 `spec-bridge` 作业被删掉，本检查也不报错**（＝那三道门禁在 CI 层没有守卫）。
#   补进清单后，删任何一个都会红。**本改动属"改门禁自身"，按本仓口径须走 R5 并说明理由。**
REQUIRED_JOBS = (
    "smoke",
    "unit-test",
    "gate-self-test",
    "traceability",
    "scope",
    "openspec-validate",
    "spec-bridge",
    "module-graph",
)

# 允许用环境变量显式指定工作流（多个用 os.pathsep 分隔）——本地排查用
ENV_WORKFLOW = "GATE_WORKFLOW"


def _git_toplevel() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def find_workflow_files() -> list[str]:
    """定位门禁工作流：**仓库根**的 `.github/workflows/*.yml`。

    为什么不是 `<项目根>/.github/workflows/`：GitHub 只认仓库根。详见文件头说明。
    """
    env = os.environ.get(ENV_WORKFLOW, "").strip()
    if env:
        return [p for p in env.split(os.pathsep) if p and os.path.isfile(p)]

    search_roots: list[str] = []
    top = _git_toplevel()
    if top:
        search_roots.append(os.path.abspath(top))
    # 回退：从 ROOT 逐级向上（无 git 时，例如 VM 的 work-tree-only 签出区）
    cur = os.path.abspath(ROOT)
    for _ in range(6):
        search_roots.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    found: list[str] = []
    seen: set[str] = set()
    for base in search_roots:
        wf_dir = os.path.join(base, ".github", "workflows")
        if not os.path.isdir(wf_dir):
            continue
        for name in sorted(os.listdir(wf_dir)):
            if not name.endswith((".yml", ".yaml")):
                continue
            path = os.path.abspath(os.path.join(wf_dir, name))
            if path not in seen:
                seen.add(path)
                found.append(path)
    return found


def check_continue_on_error(path: str, text: str) -> list[str]:
    """找**活动的** `continue-on-error:` 指令。

    只认 YAML 键的形式（可带 `- ` 前缀），不认：
      - 注释行（`# ...`）
      - 字符串字面量（如集成在脚本里的 echo）
    """
    problems: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # YAML 键：可选 "- " 前缀 + continue-on-error + 冒号
        if re.match(r"^-?\s*continue-on-error\s*:", stripped):
            problems.append(
                f"{path}:{i} 出现活动的 `continue-on-error`：{stripped}\n"
                "        这会让该作业无论退出码为何都不阻断，门禁形同虚设。"
            )
    return problems


def jobs_of(path: str, text: str) -> set[str]:
    """取顶层 `jobs:` 下的作业名（2 空格缩进的键）。"""
    m = re.search(r"^jobs:\s*$", text, re.MULTILINE)
    if not m:
        return set()
    tail = text[m.end() :]
    return set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", tail, re.MULTILINE))


def check_jobs(workflows: dict[str, str]) -> list[str]:
    """确认必需的作业都还在。

    规则：**任何一个"承载了门禁作业"的工作流，都必须承载全部必需作业**。
    这样既允许仓库将来有多个工作流，又不允许把门禁拆散、悄悄少掉一个。
    """
    problems: list[str] = []
    required = set(REQUIRED_JOBS)
    gate_files = {p: t for p, t in workflows.items() if jobs_of(p, t) & required}
    if not gate_files:
        return [
            "没有任何工作流包含必需作业 "
            f"{sorted(required)} —— 门禁整体缺失。\n"
            f"        已扫描：{sorted(workflows)}\n"
            "        ⚠️ 注意：GitHub **只**发现仓库根 `.github/workflows/` 下的工作流。"
        ]
    for path, text in sorted(gate_files.items()):
        found = jobs_of(path, text)
        for job in REQUIRED_JOBS:
            if job not in found:
                problems.append(
                    f"{path} 缺少必需作业 `{job}`。\n"
                    f"        该文件的作业：{sorted(found)}\n"
                    "        删掉一个门禁作业等于取消该门禁——须走 R5 评审并说明理由。"
                )
    return problems


def check_ps1_bom(repo_root: str) -> list[str]:
    r"""确认所有 `.ps1` 都带 UTF-8 BOM。

    为什么这条属于"门禁自检"而不是编码风格：**本机默认 shell 是 Windows
    PowerShell 5.1**，它对无 BOM 的 .ps1 按系统 ANSI 代码页解码；含中文注释的
    脚本会被解成乱码字节并**解析失败**，而报错行号会指向正则字面量之类的地方——
    "错误信息指向错误的地方"。2026-09-26 实测踩到（`scripts/build/rustfmt.ps1`）。

    该纪律只针对 .ps1：`.sh` / `.py` 是 UTF-8 原生，且 `bash` 会把 BOM 当命令。

    ⚠️ 扫描范围**只到本项目根**（``），不是整个仓库根，更不是磁盘上的
    兄弟目录。理由（2026-09-26 实测踩到）：本机 `D:\Code` 下还有别的项目
    （`01-dsh/`、`02-bazidiy/`，含 `.venv` 与 worktree），把扫描范围放到 `D:\Code`
    会捞出一堆**不属于本项目**的 .ps1 并全部报错——在 CI 里它们根本不存在，
    于是本地红、CI 绿，门禁又开始说两种话。
    **门禁的扫描范围必须与它的管辖区一致。**

    ★ 2026-10-07 补（同一句话的第二次适用）：料夹 **`.refs/`** 也必须挡在外面。
    它是**上游源码快照／标准料库**（`AGENTS.md`：料统一住 `.refs/`，**不入版本控制**），
    里面成百件上游 `.ps1` 本来就没有 BOM，也**不是本项目的件**——不挡就会在宿主上
    一次报出 5+ 条"缺少 UTF-8 BOM"，全是**假红**（在 CI 里 `.refs/` 根本不存在）。
    这与上一条「扫描范围必须与管辖区一致」是同一条规矩，不是放宽判据：
    **本项目自己的 `.ps1`（今天：`scripts/build/rustfmt.ps1`）照判，一条不减。**
    """
    problems: list[str] = []
    bom = b"\xef\xbb\xbf"
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # `.refs`＝料夹（不入版本控制）；`refs`＝它的旧名（迁移前的残名，一并挡）
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".refs", "refs", "target", "node_modules", "__pycache__")]
        for name in sorted(filenames):
            if not name.endswith(".ps1"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "rb") as fh:
                head = fh.read(3)
            if head != bom:
                problems.append(
                    f"{os.path.relpath(path, repo_root)} 缺少 UTF-8 BOM。\n"
                    "        Windows PowerShell 5.1 会按 ANSI(GBK) 解码无 BOM 的 .ps1，\n"
                    "        含中文的脚本将解析失败（报错行号还会指向别处）。\n"
                    "        处置：以 UTF-8 **带 BOM** 重新保存。"
                )
    return problems


def check_phase_switch(workflows: dict[str, str]) -> list[str]:
    """确认"阶段开关"常量还在——因为它的缺失会**永久**失去一项门禁强度。

    背景（WC-SCMP-001 §8.4 G-14）：追溯门禁原为硬编码 `--strict`，
    而 S1–S4 的需求大多未实现，严格模式**永远无法通过**——
    "永远红的门禁等于没有门禁"。修法是引入 `RTM_STRICT` 阶段开关：
    S1–S4 为 `"false"`，S5 起必须改 `"true"`。

    为什么由自检脚本盯住它：把开关**删掉**是最隐蔽的"放宽门禁"——
    工作流照样跑、CI 照样绿，但严格模式再也不可能启用。
    故凡出现 `RTM_STRICT` 使用处，就必须有定义处；反之亦然。
    """
    problems: list[str] = []
    joined = "\n".join(workflows.values())
    used = "RTM_STRICT" in joined
    if not used:
        problems.append(
            "工作流中找不到阶段开关 `RTM_STRICT`。\n"
            "        该常量承载「追溯门禁在 S5 起转严格」这一能力；删掉它等于\n"
            "        永久放弃严格模式（且不会以任何方式报错）。\n"
            "        处置：恢复该常量，或走 R5 评审说明为何不再需要严格模式。"
        )
    else:
        for path, text in sorted(workflows.items()):
            if "RTM_STRICT" not in text:
                continue
            has_def = re.search(r"^\s*RTM_STRICT\s*:", text, re.MULTILINE) is not None
            if not has_def:
                problems.append(
                    f"{path} 使用了 `RTM_STRICT` 但没有定义它——\n"
                    "        未定义时 shell 拿到空串，严格模式被静默降级为关闭。"
                )
    return problems


def check_phase_switch_value(workflows: dict[str, str]) -> list[str]:
    """阶段开关的**当前取值**是否已到该翻转的时点——**只告警，不失败**。

    为什么用告警而不是失败（2026-09-27）：S5 起 `RTM_STRICT` 应为 `"true"`，
    但实测翻转会被**多条人工状态判定**阻塞（见 `WC-SCMP-001` §8.4 **G-16**/**G-43**；
    ⚠ **2026-09-26 订正：原写"两条"是 RTM 还是 27 行时的陈旧值——实测 37 行下为 10 条**）。
    在这里判失败 = 要求 AI 替人做状态判定（越权）；
    什么都不说 = "该翻转而没翻转"可能被永远遗忘（本项目最反对的失败模式）。
    故：打在每次 CI 日志里，并点名阻塞项。
    """
    warns: list[str] = []
    for path, text in sorted(workflows.items()):
        m = re.search(r'^\s*RTM_STRICT\s*:\s*"?([^"\n]*)"?', text, re.MULTILINE)
        if not m:
            continue
        value = m.group(1).strip().strip('"')
        if value.lower() != "true":
            warns.append(
                f'{path}: RTM_STRICT="{value}" —— **S5 起应为 "true"**，'
                "但严格模式当前仍被**12 条人工状态判定（2026-09-27 订正：原写 10 条，实测 `--strict` 为 12 ERROR）**阻塞"
                "（⚠ 订正：原写\"两条\"是 27 行时代的陈旧值）："
                "`REQ-F-015`/`REQ-F-023`/`REQ-F-025`/`REQ-F-026`/`REQ-F-027`/"
                "`REQ-F-029`/`REQ-F-030`/`REQ-F-031`、`REQ-N-005`/`REQ-N-006`；"
                "确切报错见 `WC-TR-001` §四-10 / `WC-SCMP-001` §8.4 G-16/G-43。"
                "**翻转之前不得声称「追溯门禁已按 S5 强度生效」**"
            )
    return warns


def check_declared_dependencies(root: str) -> list[str]:
    """确认直接依赖只有允许清单里的那些（`REQ-N-002` 的**会失败的证据**）。

    为什么补这一条（2026-09-26，见 `WC-RV-R2-001` **T-17**）：
    `REQ-N-002`（零外部依赖纪律）此前记为"已实现"，但它的判据是
    "`Cargo.toml` 逐条核对"——一个**人工审计过程**，没有任何会失败的机器检查。
    "现状符合"与"纪律被守住"是两件事。

    实现上不引 toml 库（那会为了检查"零依赖"而引入依赖 😅）：
    只解析 `[dependencies]` 段里的裸键行。
    """
    allowed = {"serde_json"}
    cargo = os.path.join(root, "Cargo.toml")
    problems: list[str] = []
    if not os.path.isfile(cargo):
        return [f"找不到 {cargo}"]
    in_deps = False
    found: list[str] = []
    with open(cargo, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("["):
                in_deps = s == "[dependencies]"
                continue
            if not in_deps or not s or s.startswith("#"):
                continue
            name = s.split("=")[0].strip()
            if name:
                found.append(name)
    extra = sorted(set(found) - allowed)
    if extra:
        problems.append(
            f"Cargo.toml 的直接依赖超出允许清单：{extra}（允许：{sorted(allowed)}）。"
            " 新增依赖须走评审（REQ-N-002）——本断言就是为了让这条纪律**会失败**。"
        )
    return problems


def check_admission_evidence(root: str) -> list[str]:
    """S0 准出证据准入隔离（**同时验证判定器自身会红**）。

    依据：`.refs/_料/process-source/06-swe-gb/docs/评审类/01-阶段评审记录.md` **铁律一**——"没有准出结论，
    不进入下一阶段；……下一阶段的一切工作都属于未授权开工，**其产出不进入基线**"。

    两件事一起做，缺一不可：
      ① 扫真实文档（R0 材料 / R0 评审记录 —— 自 2026-09-26 **S0 五件合并轮**起，
          `WC-R0-DS-001` 决议单为 `WC-RV-R0-001` 的**并入件**，无需单列），
         凡把 S1–S5 产物**当作 S0 准出依据**的引用 ⇒ 报错；
      ② **跑一次 `--self-test`**：若判定器自己不会红（反例不命中）或误伤（正例命中），
         同样报错——**否则这就是"装饰"**（本项目反复栽过的形态：G-27/G-42/G-49）。

    ⚠️ 本项是 2026-09-26 新增，登记于 `WC-SCMP-001` §8.4 **`G-53`**（`WC-SCR-011`）。
    """
    problems: list[str] = []
    tool = os.path.join(root, "scripts", "verify", "admission_evidence.py")
    if not os.path.isfile(tool):
        return [
            f"缺少 {os.path.relpath(tool, root)}——S0 准出证据准入隔离判据不存在。\n"
            "        ⚠️ 该判据缺失时，'把阶段外产物当准出依据'无人拦，且**不会有人发现**。"
        ]

    # ② 先证判定器自身会红（最要紧的一步：一个从不失败的检查不是检查）
    try:
        proc = subprocess.run(
            [sys.executable, tool, "--self-test"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=root,
            env=CHILD_ENV,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return [f"admission_evidence.py --self-test 无法执行：{exc}"]
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").strip().split("\n")[-6:])
        problems.append(
            "admission_evidence.py **自证失败**：判定器不会红或误伤 ⇒ 该判据是装饰。\n"
            f"        原始输出（末 6 行）：\n{tail}"
        )

    # ① 再扫真实文档
    try:
        proc = subprocess.run(
            [sys.executable, tool, "--repo-root", root],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=root,
            env=CHILD_ENV,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return [f"admission_evidence.py 无法执行：{exc}"]
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").strip().split("\n")[-10:])
        problems.append(
            "S0 准出证据准入隔离**不通过**：R0 材料/记录中把 S1–S5 产物当作 S0 准出依据。\n"
            f"        原始输出（末 10 行）：\n{tail}"
        )
    else:
        print(
            "  ✅ S0 准出证据准入隔离：判定器自证通过（反例会红）＋ 真实文档 0 违规"
        )
    return problems


def check_scope_json() -> list[str]:
    """确认范围声明文件是合法 JSON 且非空。

    事故复盘：该文件曾含 `#` 注释，导致 json.load 抛异常、scope 作业永久失败。
    """
    problems: list[str] = []
    if not os.path.isfile(SCOPE_JSON):
        return [f"缺少 {SCOPE_JSON}"]
    try:
        with open(SCOPE_JSON, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        return [
            f"{SCOPE_JSON} 不是合法 JSON：{exc}\n"
            "        ⚠️ JSON 不支持注释。说明性文字请写进文档，不要写进本文件。\n"
            "        该文件解析失败会让 scope 作业永久红灯。"
        ]
    if isinstance(data, dict):
        allowed = data.get("allowed")
    elif isinstance(data, list):
        allowed = data
    else:
        allowed = None
    if not allowed:
        problems.append(f"{SCOPE_JSON} 的 allowed 列表为空——等于没有声明范围")
    return problems


def main() -> int:
    print("=" * 70)
    print("门禁自检（CI self check）")
    print("=" * 70)

    paths = find_workflow_files()
    if not paths:
        print(
            "[ERROR] 找不到任何工作流文件。\n"
            "        已查找：环境变量 GATE_WORKFLOW、git 仓库根、以及从本目录向上的各级\n"
            "        `.github/workflows/*.yml`。\n"
            "        ⚠️ GitHub 只发现**仓库根**的 `.github/workflows/`；放在子目录等于没有。",
            file=sys.stderr,
        )
        return 1

    workflows: dict[str, str] = {}
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            workflows[path] = fh.read()

    print(f"  已扫描 {len(workflows)} 个工作流文件：")
    base_dir = _git_toplevel() or ROOT
    for path in sorted(workflows):
        rel = os.path.relpath(path, base_dir).replace("\\", "/")
        print(f"    - {rel}  作业={sorted(jobs_of(path, workflows[path]))}")
    print()

    problems: list[str] = []
    for path, text in sorted(workflows.items()):
        problems += check_continue_on_error(path, text)
    problems += check_jobs(workflows)
    problems += check_phase_switch(workflows)
    problems += check_scope_json()
    problems += check_declared_dependencies(ROOT)
    problems += check_ps1_bom(ROOT)
    problems += check_admission_evidence(ROOT)
    warnings = check_phase_switch_value(workflows)

    if problems:
        print(f"\n发现 {len(problems)} 个问题：\n", file=sys.stderr)
        for p in problems:
            print(f"  [ERROR] {p}\n", file=sys.stderr)
        print(
            "门禁结论：不通过 —— 门禁自身存在缺陷。\n"
            "  处置：修复上述问题。**不得**通过删除检查来让它通过。",
            file=sys.stderr,
        )
        return 1

    print("  ✅ 无活动的 continue-on-error")
    print(f"  ✅ 必需作业齐备：{', '.join(REQUIRED_JOBS)}")
    print("  ✅ 阶段开关 RTM_STRICT 有定义（严格模式能力未被删除）")
    print("  ✅ 范围声明文件是合法 JSON 且非空")
    print("  ✅ 全部 .ps1 均带 UTF-8 BOM（PowerShell 5.1 可正确解码）")
    print("  ✅ 直接依赖未超出允许清单（零外部依赖纪律有会失败的检查）")
    for w in warnings:
        print(f"  [WARN] {w}")
    print("\n门禁结论：通过 —— 门禁完整，未被削弱")
    if warnings:
        print(f"  ⚠️ 但有 {len(warnings)} 条告警（见上）：严格模式尚未生效——**该翻转而没翻转**要说出来")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
