# 对源：`AI-Native-Linux-Icebreaker`（只借理念，不抄代码）

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 六 规格 | **0.1** |

> **件性质**：对源件。**只读取证**（未改任何文件、未跑构建）。
> ★ **作者令（逐字）**：「**先抄理念，不抄代码，OK**」。
> ★ **射程**：本次只读了 `README.md`（9,852 字符）与 `Patent_Prep_2_Technical_Architecture.txt`（33,036 字符）两件，外加仓根**列名**；**其余目录与文件未读**。
> ★ **本文一切否定式断言，射程只到这两件 ＋ 仓根列名。**

---

## 〇、法律面先说清（这是「不抄代码」的第一条理由）

| 项 | 现取 |
|---|---|
| 许可 | **Apache-2.0**（仓内 `LICENSE` 11,357 B） |
| ★ **它已在起草专利** | `Patent_Prep_2_…txt` 首行逐字：「**Invention Disclosure for Patent Drafting**」；「**Status: CONFIDENTIAL — attorney work-product intended; not for public disclosure**」；发明人 **Aditya（`abhimava@andrew.cmu.edu`）**，日期 **2026-06-09** |
| ★ **它自己列出了权利要求种子** | §14「**Candidate Inventive Concepts and Claim Seeds**」逐字：「**These are starting points for counsel, not finished claims**」，编号 **CI-1…CI-6** |

⇒ **口径**：**借它的「问题与不变量」是安全的；照搬它「CI-1…CI-6 指向的具体机制组合」不行**（既是专利风险，也是我们本来就不同的制裁链）。

---

## 一、它是谁（现取）

| 项 | 现取 |
|---|---|
| 仓 | `a-bhimava/AI-Native-Linux-Icebreaker`（★ 与我们的底座 `ai-os-dot-net/AI-Native-Linux` **无血缘**：`fork=false`、无 parent、不同作者） |
| star／fork／issues | **31 ／ 0 ／ 0** |
| 建仓／最后 push | **2026-05-26 ／ 2026-09-27**（**还在动**） |
| 语言／底座 | **Python 主体**（`mcpd` 是 **Rust**）／**Ubuntu 24.04** |
| 形态 | ★ **可引导的系统 ＋ 双 ISO**（ARM64 给 UTM/Apple silicon；AMD64 给 QEMU/VirtualBox） |
| 工具面 | 逐字「**23 governed system tools** for files, processes, services, packages, networking, and machine state」＋「**24 GUI/RPA tools**, vision …」 |
| 自述 | 「**The AI-native operating system built around a security boundary no prompt can talk its way across.**」 |

---

## 二、它的架构（四层 ＋ 单向信任梯度）

```
You
 │
 ▼
QUARANTINED BRAIN          懂语言与不可信内容；无特权工具；不能执行
 │   schema-validated Intent Object
 ▼
CONTROLLER                 非 AI：schema 校验 → 风险分级 → HITL 门 → 存意图、发不透明 UUID
 │   opaque intent reference
 ▼
PRIVILEGED BRAIN           执行脑：无原始对话；语法约束的 MCP 调用
 │
 ▼
mcpd                       Rust daemon：stdio JSON-RPC only；逐调用 schema 校验
 │                          fork 子进程 → 在 execve 之前上 Landlock ＋ seccomp-BPF；COW dry-run
 ▼
Linux 内核                 内核强制访问控制 ＝ 最终强制
```

★ **它的定义性质（逐字，本件最重要的一句）**：

> 「The defining property is that **no single component simultaneously possesses (a) exposure to untrusted text and (b) the capability to execute**. The Quarantined Brain has (a) without (b); the Privileged Brain has (b) without (a). The Controller … mediates the crossing through a validated, opaque channel.」

★ 另有：**append-only 审计日志记录每一条意图（含被拒的），带外于模型**。

---

## 三、它的 8 条不变量（逐字摘要；它自称「在代码里强制、在 CI 里断言」）

| 号 | 不变量 | 强制点 |
|---|---|---|
| **INV-1** | **脑中隔离**：隔离脑**零工具连接、零执行**；特权脑**零访问**原始用户输入或外部文档内容；**只有结构化 Intent Object 跨界，且降为不透明 UUID** | backends/base.py 守卫；session.py；intent_store.py |
| **INV-2** | **控制器 schema 强制**：拒绝越 schema 或**含 shell 元字符**的 Intent；**脑中之间从不传原始文本**，只传不透明引用 ID | intent_schema.py；schemas/intent.json |
| **INV-3** | **mcpd 网络隔离**：**只用 stdio**；不开 TCP/UDP/UNIX 监听；★ **CI 断言零开放端口** | server.rs；seccomp 拒 listen/accept |
| **INV-4** | **执行前参数校验**：每个工具调用参数对 JSON Schema 校验；无未转义 shell 元字符 | schema.rs；server.rs |
| **INV-5** | ★ **无沙箱不许执行**：Landlock ＋ seccomp-BPF 在 **execve 之前**应用；**若 Landlock 不可用（内核 < 5.13）则报错退出，而不是无约束运行** | sandbox/landlock.rs；sandbox/seccomp.rs |
| **INV-6** | **破坏性操作先 COW**：家目录外的 `fs.delete`／`fs.write` 走 **copy-on-write dry-run** 先给用户看；★ **Approve 按钮禁用 ≥ 3 秒** | sandbox/cow.rs；tools/fs.rs；hitl.py |
| **INV-7** | **模型权重完整性**：启动时对每个模型文件验 SHA-256（对 manifest），**不一致就拒启** | daemon 启动；models/checksums.sha256 |
| **INV-8** | **审计日志完整性**：append-only（`O_APPEND`）；**记录每一条意图，含被拒的**，带时间戳／ID／风险级／用户／结局；**模型不可写** | audit.rs |

---

## 四、★ 与我们逐条对照

| 维度 | Icebreaker | 我们的底座／我们（worldcore） | 判 |
|---|---|---|---|
| 核心不变量 | 「**没有任何单一组件同时具备 (a) 看不可信文本 与 (b) 能执行**」 | **INV-002：AI 提议、绝不执行**（只保证「不能执行」，**没保证「脏的那一角色看不到执行面」**） | ★ **它的更强；照出我方一处缺口（见 §五-1）** |
| 底座／语言 | Ubuntu 24.04 ／ Python（＋Rust `mcpd`） | openSUSE Leap 16 ／ **Rust 36 crate** | 不同 |
| 控制面 | **typed control plane**（`Intent Object` schema 校验） | **typed envelope**（`aios.action.v1alpha1`）＋ 6 边 FSM | **同向** |
| 沙箱强制 | **Landlock ＋ seccomp-BPF**（用户态 daemon 自己上） | **SELinux ＋ dm-verity ＋ 8 道企业门** | 不同机制、**同一哲学：不能强制就不跑** |
| 审批 | **HITL**（Approve 禁用 ≥3 秒） | `approval_gate`／`BLOCKED_AWAITING_APPROVAL` | **同向**，它的「加摩擦」更具体 |
| 审计 | **append-only，含被拒意图，模型不可写** | **append-only 证据链**（BLAKE3＋Ed25519，427 RecordType） | **同向**；★ 它多一条：**被拒的也记** |
| 网络面 | ★ **零监听端口，CI 断言** | 「唯一入口」只有**规矩，没有判据** | ★ **可借（§五-3）** |
| 参数校验 | ★ **逐参数**（JSON Schema） | 只到**动作名**（`action_name` 查表） | ★ **可借加强（§五-4）** |
| 模型完整性 | ★ **模型权重 SHA-256，不一致拒启** | **没有**（只校验本体与账本） | ★ **可借（§五-2）** |
| 有没有「共同依赖的说法」 | ✗ 没有：意义仍由**它自己的 `Intent Object` schema 与 MCP 语法**承担 | **这是我们要补的那一格** | ★ **我们的位置仍然空着** |

---

## 五、★ 借哪些理念（5 条；只借问题与不变量，不借实现）

1. ★★ **「看」与「做」必须分属不同角色**（照出我方一处真实缺口）：
   我方今天**同一个认知核既读不可信文本、又起草动作**（INV-002 只保证它不能执行）⇒ **一旦被注入，它可以起草出「合法但恶意」的动作，再等人批**。
   ⇒ **建议加一格**：**这条意图接触过哪些不可信源**（来源可信度），随意图一路带到审批面。★ 这正对在我方「**谁做的**」那一格旁边。
2. ★ **把「不能强制就不许跑」写成判据**：我方已有「拒启」传统（账本可写⇒拒启；法律／真相可写⇒拒启），**它把同一条推广到沙箱与模型权重**。⇒ 借这条**形式**（而非它的 Landlock 实现）。
3. ★ **「零开放端口」做成会红的 CI 断言**：我方「唯一入口」今天**只有规矩、没有判据**。⇒ 借「**把不许开口子做成 CI 断言**」这个形状。
4. ★ **校验推到「每个参数」**：我方今天只到**动作名**（且实读证明 AIOS 连动作名都没接）。⇒ 借「**逐参数对 schema 校验**」这个目标（实现用**我们自己的** schema 来源＝本体）。
5. ★ **被拒的也要入账 ＋「加摩擦」要具体**（Approve 禁用 ≥3 秒）：⇒ 值得核我方账本**今天记不记被拒的请求**；「加摩擦」也应有**可判的秒数／档位**，不是形容词。

---

## 六、★ 不借哪些（它的发明点指向**具体机制组合**）

> 它自己列的 **CI-1…CI-6**（逐字「starting points for counsel, not finished claims」）指向的是**组合**。术语与组合我们**不照搬**：

| 种子 | 它主张的组合（**不照搬**） |
|---|---|
| **CI-1** | 多模型分角色（perception 无执行／execution 无不可信输入）＋ **非模型控制器经 schema 校验意图＋不透明标识**调解全部跨模型通信 ＋ 执行由**内核 MAC 在 execve 前**约束的工具进程完成 |
| **CI-2** | 隔离脑的无执行由 **构造期守卫 ＋ 禁止子类覆写 model-completion ＋ 出站载荷审计器**强制 |
| **CI-3** | 不透明标识引用的已存意图：(a) schema 校验含 **shell 元字符 denylist**，(b) **TTL**，(c) **恰好一个允许工具**，(d) **单锁原子修订且不得引入新 schema 字段** |
| **CI-4** | **Landlock ruleset ＋ seccomp-BPF ＋ no-new-privs**，在 execve 前，**无法强制则拒绝执行** |
| **CI-5** | TOCTOU-safe：用户态路径校验 ＋ 内核 **openat2 RESOLVE_BENEATH｜RESOLVE_NO_SYMLINKS** |
| **CI-6** | **graduated determinism**：按风险分级 |

★ 另有一条**结构性差异**：它的制裁链是 **它自己的 `mcpd` daemon**；我方的链条是 **AIOS 的 envelope ＋ Capability Runtime ＋ SELinux**。⇒ **机制层本来就不该抄。**

---

## 七、对我方的落法（建议，进提案待审；**未批不动手**）

| # | 落法 | 落点 |
|---|---|---|
| 1 | **新增一格「意图的输入来源可信度」** | 我方本体（`_objects` 加格）＋ 提案接线清单新增一条；对应 Icebreaker INV-1（**借不变量，不借它的脑后守卫实现**） |
| 2 | **新增一条会红判据：「不许开监听口子」** | 我方判据族（对应 INV-3 的 CI 断言形状） |
| 3 | **核我方账本今天记不记「被拒的请求」** | 查我方 `read-model`／账本家族；若没有 ⇒ 作为待补项（对应 INV-8） |

---

## 八、出处（可复核）

| 说法 | 出处 |
|---|---|
| 它是谁（star／许可／底座／工具面） | `README.md`（9,852 字符）＋ GitHub API 仓元数据 |
| 四层信任梯度、定义性质、mcpd 沙箱、带外审计 | `Patent_Prep_2_Technical_Architecture.txt` §1（33,036 字符） |
| 8 条不变量 INV-1…INV-8 | 同件 §3「Architectural Invariants (the Security Contract)」 |
| 权利要求种子 CI-1…CI-6 | 同件 §14「Candidate Inventive Concepts and Claim Seeds」 |
| 专利准备与保密状态 | 同件首行「Invention Disclosure for Patent Drafting」／「CONFIDENTIAL — attorney work-product intended」 |

---

## 十、二轮实读（2026-10-13 **拉取到本地之后**新增）

**拉到哪**：`D:\Code\_refs\AI-Native-Linux-Icebreaker`（★ 宿主到 GitHub 现在通了；`git ls-remote` 出 refs）。

| 项 | 现取 |
|---|---|
| HEAD／提交数 | **`adfe33e` ／ 424 个提交** |
| 最后提交 | **2026-09-27** `Merge pull request #38 … docs/apache-2-license` |
| 工作树 | **850 件 ／ 233.7 MB** |
| ★ 提交按月 | **2026-05: 17 ／ 06: 133 ／ 07: 237 ／ 08: 26 ／ 09: 11** |
| 最大目录 | `privileged-brain` 90 件／**92.2 MB**；`icebreaker-claude-state` 97 件／26.2 MB；`docs` 69 件／13.8 MB；`dual-brain` 386 件／3.4 MB |

**二轮读了**：`AI_Native_OS_Whitepaper.md` §2／§3／§8／§12 ＋ `CLAUDE.md`（全文，35 KB）＋ `incremental/GROUND_TRUTH.md` §1／§2。

### 十.1 ★★ 最值得借的一条：**「不许重复回归」＋ 失败总账 ＋ 三步强制**

它 `CLAUDE.md` 的 **BP-13** 逐字：

> 「**Two prior month-long sprints on this project failed because bugs kept resurfacing across rebuilds**; … a lesson learned on Vn **must be in code, tests, and gates before Vn+1 ships**.」
> 「**A bug that gets fixed without steps 1-3 is a bug we will find again. That is the definition of the failure mode this project exists to kill.**」

**三步（逐字摘要）**：① **回归测试**（先对修复前的代码失败）；② **失败账条目**（症状 → 根因 → 修复 → 版本 → **回归守卫的名字**）；③ **复现验证**（**重跑原始症状**，不只是测试套件）。

★ **与我方对照**：我方有「加判据先写会红的反例」（`AGENTS.md` 硬约束 9）与「旧值作废不抹」，**但没有**：
1. **一条修复必须命名它的「回归守卫」**；
2. **一份专门的「真实失败总账」**（`incremental/GROUND_TRUTH.md` **167 KB**，且逐字「**That ledger is not cleaned up for marketing.**」）；
3. **重跑原始症状**（而非只跑测试套件）这一条**强制**。
⇒ **建议整体借这一条**（借形式；「失败账」是工程纪律，不是它的发明点）。

### 十.2 ★ 新增可借（6 条，逐条带它的原话）

| # | 借什么 | 它的原话（摘要） | 为什么对我方有用 |
|---|---|---|---|
| 1 | ★ **外部影响文本必须消毒**（BP-3） | 「Strip ANSI escapes and C0/C1 control characters and neutralize CR/LF before rendering it to a TTY or log. Raw model/document text rendered to a terminal is a **prompt-spoofing vector**（**it can redraw an approval prompt**）」 | ★ **我方没想到这一格**：我们的投影／渲染面若把模型文本原样渲染，**审批提示可被重画** |
| 2 | ★ **人类闸门的完整性**（BP-4） | 「flush the input buffer before reading（**no pre-buffered/pasted bytes may decide**）、require a single intentional keypress、enforce the approval lockout on a **monotonic clock**、default to **deny** on timeout / non-TTY / interrupt、reserve an always-available deny key（Esc）」 | 我方有「按不可逆性加摩擦」，但**没有这五条具体的闸门完整性** |
| 3 | ★ **风险只能升不能降，且做成运行时断言**（BP-5） | 「An ML/LLM/policy pass may **raise** an operation's risk tier; it may **never lower** the rule-based floor. **Encode this as a runtime assertion, not a convention.**」 | 与我方「AI 不许造权威」同源，但**落成运行时断言** |
| 4 | ★ **安全决策只用结构化事实**（BP-6） | 「the fields a human relies on … come from validated schema and the sandbox COW preview. **Model-authored free-text … must never be the basis of the risk label or the decision**」 | ★ 我方「七问」里若某些格子**来自模型自由文本**，就不许当判据基础 |
| 5 | ★ **延迟预算不可谈判** | 「Landlock <1ms／Seccomp <1ms／COW overlay <5ms／MCP 往返 <5ms／**总额外开销 <10ms**／**Tier 0/1 全链路 p95 <100ms**」 | ★ **正好补我方「性能无读数」那一格**：先有预算，再有读数 |
| 6 | ★ **测试后门不许在发布二进制里** | 「cargo feature 默认 **off**；生产二进制里 `MCPD_FS_TEST_ROOTS` 的出现次数必须为 **0**（CI 用 strings 断言）」 | ★ 可借形状：**用 `strings` 断言生产二进制里没有测试后门** |

### 十.3 ★ 一条反面教材（**对我方直接适用**）

它的 `GROUND_TRUTH.md §1` 状态板里有一条 **RED**（V6.3）逐字：

> 「**RED — SIGSYS in fs.write** — **29/29 automated gates PASS** but UTM boot 2026-07-07: `# create Hello.txt` → mcpd killed by SIGSYS in `__GI_fsync()`. Root cause: seccomp allowlist missing `SYS_fsync`; **the QEMU gate never exercised fs.write**.」

⇒ ★★ **「自动门全绿、真机一跑就红」** —— **这正是我方的风险**：我方判据也全是「自动门」，**端到端／真机路径没跑过**（本会话四席实读也证明：AIOS 的执行面根本没接线）。⇒ **这一条要写进我方提案的「风险」栏。**

### 十.4 他的诚实机制（两条，逐字）

1. `GROUND_TRUTH.md` 开头：「**This document is the single source of truth for the incremental rebuild.** If code, chat history, or memory disagrees with this file — **this file wins**.」
2. 白皮书有专节 **§10.5 Audit acknowledgment (2026-07-10)**（文档诚实性说明）。

⇒ 与我方「**以件为准，不以叙述为准**」同源；但**他明确规定「文件赢了」**（连聊天记录与记忆都要让路）——★ **这个优先级写法可直接借**。

### 十.5 二轮新增未读面（如实）

1. 白皮书**其余章节未读**（§1／§4–§7／§9／§10／§11／§13／§14）；
2. `docs/IMPLEMENTATION_PLAN.md`（60 KB）／`docs/ARCHITECTURE.md`（37 KB）／`ai_terminal_design.md`（64 KB）**未读**；
3. `GROUND_TRUTH.md` **仅读 §1–§2**（全文含 Failure Log 与 Version Ladder V6–V6.x）；
4. **源码未读**：`src/mcpd/`（66 件）、`dual-brain/`（386 件）、`cx-distro/`（56 件）；
5. **未跑任何构建／测试**（只是克隆到本地）。

---

## 九、未读面（如实）

1. **白皮书 `AI_Native_OS_Whitepaper.md`（64,838 B）未读**；PDF 未读；`Multi_Brain_OS_Architecture_Enhancements.txt`／`Patent_Prep_1_Plain_Language_Explanation.txt` 未读。
2. **`dual-brain/`、`privileged-brain/`、`src/`（含 `mcpd` Rust daemon）、`cx-distro/`、`config/`、`docs/`、`shell/`、`tests/`、`Testing_Reports/`、`incremental/`、`models/`、`manual_check/` 全部未读**。
3. **未跑任何构建／测试**；★ **未能拉取到本地**（宿主到 GitHub 不通：`api.github.com` 与 `codeload` HTTP 均失败、`git ls-remote` rc=128）⇒ 本件全靠**取件通道逐件读**。
4. **未核**它与任何其他项目的关系（本轮只核了 `fork=false`／无 parent／不同作者）。

