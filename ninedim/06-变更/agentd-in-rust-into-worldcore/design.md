# Design

## Context

起点：`1b58dc0`（作者三句裁定已登记在册 `docs/理论/冲突总账.md` §7.15，未立件）。

塑造做法的现状与约束，**逐条都是读出来的、不是猜的**：

1. **世界核心里已经有一只"手"**：`src/carrier/`（`M10` 载体适配器，9 个模块）。
   它的纪律只有一条：**只执行、不裁决**（`src/carrier/mod.rs` 头注）。
   ⇒ 任何"Agent 面"的落地**必须先做一遍对账**，否则就是重复实现。
2. **依赖纪律锁死实现选择**：`Cargo.toml` 逐字「**只允许 `serde_json` 一个 crate family**」，
   并且**不引入 `serde_yaml`**（Go 侧 `capd` 用 `gopkg.in/yaml.v3`）。
   ⇒ 声明的承载格式只能是 JSON，**这一条已经是既成事实**（`src/carrier/capd.rs` 头注逐字「为什么不用 YAML」）。
3. **本项目已明确拒绝 Go 侧 `internal/job` 的落盘登记簿**：
   `src/carrier/recover.rs` 头注逐字「旧实现在载体侧自己维护一本完工铃登记簿（落盘、重启后标记"丢了"）。
   现在**那本登记簿是多余的**：登记簿要回答的"哪些活还没干完"，由**账本折叠**回答」。
   `src/carrier/providers.rs` 的 `Job` 头注同文。⇒ **不许把那本登记簿带回来。**
4. **本机没有 cargo**（`cargo` 不在 PATH、`~/.cargo` 不存在）⇒ Rust 侧读数**只能上 VM 取**
   （`ssh world`；`check.sh.new` 与 `cargo test --locked` 是既有入口）。
5. **规格层的一道真缺口**：`spec_bridge.py` 判据④ 只扫**主规格树**（`ninedim/01-意图环/04-规格/**/spec.md`），
   而 OpenSpec 的规矩是 **delta 在 change 归档时才并入主规格** ⇒ 新能力在归档前
   **不在判据④ 的扫描面里**，主规格树里也没有它的标题 ⇒ 判据④ 对它**永远绿**，
   即它在编号桥里**没有在册面**。而 `generated/BRIDGE.md` 是**生成物**（判据⑪ 逐字节核）⇒ **不许手编**。
   （这一条是**前两次立件失败的根因**，册 §7.15 记着那两次都当场撤回。）

## Goals / Non-Goals

**Goals:**

- **捋清并固化**「原 Go 8 个包 ↔ 世界核心既有落点」的对账：**有主的不重写**，**没主的才是本件的工作**。
- 让**新能力有在册面**，且**不动生成物的手编禁令**：给生成器加一节，由它**现取**在办 change 的承诺。
- 把 Agent 面**真正缺失的那 4 件事**实现成 Rust 模块，**每件带会红的断言**（含变异证明）。
- **文档口径**：把被三句裁定推翻的 5 件 28 处措辞逐条改写，每条留**让路三要素**。
- **仓根 Go 退场**：`agentd/` 不再作独立组件，连带归位 6 处引用点。

**Non-Goals:**

- **不重写 `src/carrier/**`**（它已成立且在服务中）：本件不改它一个字节的行为，
  只在 delta 里**登记它的落点与既有断言**。发现它的问题**只登记、不动手**。
- **不引入任何新依赖**：不加 crate、不加 npm 包。
- **不把 Go 的 `internal/job` 登记簿带回来**（本项目已裁定它是多余的）。
- **不碰 `docs/schemas/**`**（那是**另一条并行线的文件面**）。

## 影响分析

| 项 | 内容 |
|---|---|
| **受影响模块** | 新增 `src/agent/{mod,audit,protocol,completion}.rs`；新增 `scripts/test/agent_{audit,protocol,completion,undo}.rs`；**改一行** `src/lib.rs`（加 `pub mod agent;`）；改 `scripts/gen/gen_bridge_md.py`（加一节发现逻辑）＋ 重跑 ⇒ 改 `generated/BRIDGE.md`；改 5 件流程文档的 28 处措辞；**退场** 仓根 `agentd/**` 并归位 6 处引用点 |
| **受影响需求** | 本件引入的新能力 `agent-runtime`（4 条 Requirement，逐条「无号·待流程侧增补」）。流程侧影响面：`WC-FSR-001`／`WC-SDP-001`／`WC-SCMP-001`／`WC-IRS-001`／`WC-SQAP-001`（口径改写）；`REQ-F-016`／`REQ-F-017`（门禁与不可逆性）**不动**——本件不裁决，只留痕与执行 |
| **需重跑的测试** | ① `cargo test --locked`（16 个 target，VM 上跑）② 新增 4 个 target ③ `python scripts/verify/spec_bridge.py` ④ `npx --yes @fission-ai/openspec@1.13.2 validate --all --strict` ⑤ `python scripts/gen/gen_specmap.py` → `gen_bridge_md.py` ⑥ `python scripts/verify/table_width_audit.py <改过的 .md>` ⑦ `python scripts/verify/plain_text_audit.py`（编码闸） |
| **回归范围** | **R-A（只读）**：既有 9 个能力与 `carrier/**` 的行为**不变**——本件不 `use` 它们内部实现、不改它们一行 ⇒ 既有断言必须全绿（这是**正控**：若它们变红，说明我越界了）。**R-B（双向）**：`gen_bridge_md.py` 的改动必须**在没有在办新能力时输出逐字节不变**（已验证：挪走本 change ⇒ sha256 相等）。**R-C（单点）**：`lib.rs` 一行 `pub mod agent;`。**R-D（不适用）**：不改运行中的世界（新模块是库，不接进 `main` 的既有分支） |
| **工作量估算** | 3–4 人日：对账与立件 1 日、4 件实现＋断言＋变异 1.5 日、28 处口径改写 0.5 日、退场与归位 0.5 日、评审与收口 0.5 日 |
| **需通知的使用方** | **只有本仓自己**（仓根 `README.md`、仓根 `check.sh`、`.github/workflows/world-core-gate.yml`）。**BREAKING**：`agentd/` 的入口形态从"仓根一个独立 Go 程序"变为"`world-core` 内的 Rust 模块" ⇒ 随本件一并改这三处 |

**R5 触发条件**：**FC-1**（契约不足）＋ **FC-3**（假设被推翻）。

**现象证据**（命令 ＋ 输出，起点 `1b58dc0`）：

- **FC-3 的直接证据**（假设被推翻）：册 `冲突总账.md` §7.15 逐字记着前两次立件
  「delta 挂**新建能力**」与「delta 改挂**既有能力** `gate-enforcement`」**两种挂法都在同两处判红**
  ⇒ 「新能力能不能进在册面」这个假设**被实测推翻**。
  本轮实测到的**机制**：判据④ 只扫主规格树（`j4_bridge_coverage` 逐行只遍历
  `ninedim/01-意图环/04-规格/**/spec.md`）⇒ 它对 delta 里的新能力**结构上不可达**。
- **FC-1 的证据**：`` 下 `.go` 文件数 **0**、`src/` 下 Agent 面模块 **0**；
  而 `agentd/` 下 `.go` 文件 **21**（8 个包的实现与测试）。
- **既有的对口断言**（"有主"那 5 件不是空口）：`scripts/test/atom_reversibility.rs::a07_carrier_undo_is_neither_cross_checked_nor_a_proof_of_world_reversibility`、
  `::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`、`::a05_…`、`::a06_…`；
  `scripts/test/write_side.rs::w01_the_write_side_submits_verbatim_and_never_adjudicates`…`w05_…`。

## 方案对比

### 方案甲 · **先把 Go 8 个包逐包对账，只补真缺口**（**选**）

- **做什么**：先按 `src/carrier/**` 逐个核"这件事有没有主"；有主的
  **只登记落点与既有断言**，**没主**的才写成新 Requirement 并实现。实测结果：
  **5 件有主**（capd 声明解析／provider 契约／内置 provider／处置顺序／撤销点**行为**），
  **4 件没主**（结构化审计留痕／行分隔请求应答／完工通告／撤销点编排的**可观察断言**）。
- **代价**：多做一轮对账（约半天），且要承认"原计划里有一半是重复劳动"。
- **结论**：**选**。理由：`WC-ATOM-001` §二 A-1「单意图原子性」要消灭的正是"同一件事两个载体"；
  而重复实现 `capd` 会产生**两份能力声明解析器**，两份的口径迟早不同——
  **那比不做更坏**。

### 方案乙 · 把 Go 8 个包**逐包**在 Rust 侧重写一遍（原计划）

- **做什么**：`src/agent/` 下建 8 个模块，一一对应 Go 的 8 个包。
- **代价**：约 3 倍工作量；**并且会造出第二份权威**——`Manifest`／`Provider`／`execute`
  各多一份；`internal/job` 的登记簿还会把"第二份待办真相"带回来，
  直接违反本项目已写进代码的裁定（`src/carrier/recover.rs` 头注）。
- **结论**：**不选**。它是"按包名对齐"，不是"按能力对齐"。

### 方案丙 · 最小改：只改规格与文档，**不写 Rust**

- **做什么**：把 5 件 28 处口径改写、把 `agentd/` 退场，规格里把 Agent 面登记为"已有主"。
- **代价**：零实现风险；但作者裁定逐字是「**必须使用 rust 写**」⇒ 只改文档**没有满足裁定**，
  而且那 4 件真缺口（审计留痕／行协议／完工通告／撤销点断言）**依然没有落点**，
  等于把裁定读成"改个措辞"。
- **结论**：**不选**（作为**分期**的第二步是可以的，作为全部不行）。

### 方案丁 · 生成器补丁 vs 手改进 `generated/BRIDGE.md`

- **做什么**：让新能力在编号桥有在册面。
- **两条路**：① 手改 `generated/BRIDGE.md`；② 给 `gen_bridge_md.py` 加一节发现逻辑。
- **代价**：① 零代码，但**违反判据⑪**（生成物不许手编）——而且手改的那一行**下次重跑生成器就没了**；
  ② 要改门禁侧工具（所以**必须送独立评审席**）。
- **结论**：**选 ②**。理由：①不是"省事"，是**把闸绕过去**；skill §九 逐字
  「**闸在版本控制之外等于没有闸**」——这里同理：**手编的生成物等于没有生成链**。

## 原子表

> `WC-ATOM-001` §四。**每个原子一行，六栏逐栏非空**（原子／intent／四件同夹／`deps == import`／生成物／机核读数）；出现「与／和／及」并列两事 ⇒ 拆。
>
> ⚠ **一处立项时的口径修正（独立评审席查出，2026-09-28 登记）**：本行**原写「五栏」**，
> 而本表**实为六栏**（表头逐字如上）——**同一节里自己两处不一致**。
> 那五栏是 `WC-ATOM-001` §四 A-3 要求的**契约字段**（`intent`／`input`／`output`／`side_effects`……
> 在本表里落成 intent／四件同夹／deps／生成物 这几格），而**本表多出的第 6 格是"机核读数"**
> ——它是本项目加的"这格凭什么算数"，所以是**六栏**。**按六栏改**。
> **另登记一条下一笔会撞的口径**（本笔**不改**，因为它属别人的受控面）：
> `proposal.md` 用 `FC:` 行写变更号，而（新档 `opsx-swe-gb-atom/schema.yaml` 逐字要求）
> 变更号**独占文档头 `CR:` 一行**——**下一笔动这个文件时会撞**，此处只登记。
> ⚠ **本表不是宣言**：写「无环」而没跑过 `module_graph.py` ＝ 把没做到写成做到了。

| 原子（真实路径） | intent（一句话） | 四件同夹（契约 / 实现 / 测试各在哪） | deps == import | 生成物（重跑命令 / 无） | 机核读数 |
|---|---|---|---|---|---|
| `src/agent/audit.rs` | 把一次意图或动作留成一条字段固定的结构化记录 | 契约：delta 的「结构化审计记录」条 ＋ 本文件头注；实现：本文件；测试：`scripts/test/agent_audit.rs` `g01`–`g04` | 声明 `use serde_json::Value`、`std::collections::BTreeMap`、`std::io::Write`、`std::path`、`std::sync::Mutex` —— **无 crate 内兄弟模块依赖**（∅） | 无 | `module_graph.py`（**本件不声称它覆盖 YAML，只覆盖 `src/**/*.rs`**）；VM 上 `cargo test --locked --test agent_audit` |
| `src/agent/protocol.rs` | 用一行 JSON 一问一答地暴露一次调用 | 契约：delta 的「行分隔的结构化请求与应答」条；实现：本文件；测试：`scripts/test/agent_protocol.rs` `p01`–`p03` | 声明 `serde_json` 与 `std::io` —— ∅ | 无 | 同上，`--test agent_protocol` |
| `src/agent/completion.rs` | 把"活儿干完了"写成一条可读回的通告（**不另立登记簿**） | 契约：delta 的「完工发通告，但不另立登记簿」条；实现：本文件；测试：`scripts/test/agent_completion.rs` `j01`–`j04` | 声明 `use crate::common::event`（既有模块）＋ `serde_json` —— **仅 1 条出边，无环** | 无 | 同上，`--test agent_completion` |
| `src/agent/mod.rs` | 声明 Agent 运行时的模块面与它与 `carrier` 的分工 | 契约：本文件头注（含"登记簿不许带回来"那条裁定）；实现：三行 `pub mod`；测试：由上面三个 target 覆盖 | 声明 `pub mod audit/protocol/completion` —— 出边 3 条，**无回边**（被 `lib.rs` 单向引用） | 无 | 同上 |
| `scripts/test/agent_undo.rs` | 钉住"撤销点在确认之后、失败即不执行、且不是世界回滚" | 契约：delta 的「动手前的载体撤销点」条；实现：**行为已在** `src/carrier/providers.rs::execute`（本件不改它）；测试：本文件 `u01`–`u04` | 声明 `use world_core::carrier::{capd, providers}` —— 仅测试侧出边 | 无 | 同上，`--test agent_undo` |
| `scripts/gen/gen_bridge_md.py`（加一节） | 让在办 change 的新能力进编号桥的在册面 | 契约：本文件头注 ＋ `generated/BRIDGE.md` 该节的自述；实现：本文件新增的发现逻辑；测试：**双向反向验证**（挪走 change ⇒ 输出逐字节不变；放回 ⇒ 出现该节） | 纯 Python 脚本，无 crate 内依赖 | **有生成物**：`generated/BRIDGE.md`；重跑 `python scripts/gen/gen_specmap.py` → `python scripts/gen/gen_bridge_md.py` | `spec_bridge.py` 判据④ 与 ⑪ |

> **A-2 说明（本仓形态）**：本仓 `tests/` 与 `src/` **不同夹**，按"可指认"判——
> 上表每行的测试栏都给了**真实路径 ＋ 用例名**。
> **A-4 说明**：`agent/completion.rs → crate::common::event` 是唯一一条 crate 内出边；
> `event.rs` 不 import `agent` ⇒ **无环**。上表**不声称**已跑过 `module_graph.py`——
> 那个读数在 VM 上取，见 `tasks.md` 第 3 组；**读数未取之前，本栏不写成"已无环"**。
> **A-6**：UTF-8 无 BOM、LF，由 `plain_text_audit.py` 判。

## Decisions

1. **只补 4 件真缺口，不重写有主的 5 件**。考虑过"按 Go 包名一一对齐"（方案乙），
   不选：那会造出第二份能力声明解析器与第二份待办真相。
2. **`agent-runtime` 作新能力**（而非把 4 条挂进 `gate-enforcement`）。
   理由：这 4 件是**执行侧的留痕与长活儿**，与"门禁不可绕过"不同域；
   硬挂进 `gate-enforcement` 会让一条能力里并着两个意图（违反 A-1）。
   ⚠ **这一格册 §7.15 记着"仍待人裁"** ⇒ 本件**选了一条并写明理由**，
   同时**登记为待人裁项**（`Open Questions` 第 2 条）——**不假装它已定**。
3. **在册面走"生成器加一节"**，不走手改（方案丁）。
4. **新节带退化保护**：「一条都没发现就**整节不输出**」⇒ 对本件以外的任何情形，
   生成器输出与改动前**逐字节一致**（这是判据⑪ 的安全阀，已双向验证）。
5. **`completion` 不自己写账本**：它只**造**通告事件（`to_event`），写由既有唯一写入口
   （`World::commit`）做——**一个写入口**是贯穿纪律之一（`src/lib.rs` 头注第 2 条），
   新模块**不许**绕过它。考虑过让 `completion` 直接持 `World`：不选，那会让本模块
   依赖整个世界，且给"第二写入口"留了门。
6. **声明格式以 JSON 为准**（不是新决定，是**确认既成事实**）：`src/carrier/capd.rs` 已经
   是 JSON 口径，delta 里那条 Requirement 是对**已有行为**的追认，让路三要素写在 `proposal.md`。
7. **不改 `docs/openspec-config.yaml`**（默认档不动）：改它会把全仓在办 change 的形态基准一起挪。

## Risks / Trade-offs

- **[把 `carrier` 已有的东西又写一遍]** → 缓解：delta 增「与既有能力的边界」一节，
  逐条给既有实现与**既有会红断言**；评审席按该节逐条复跑。
- **[生成器补丁让判据⑪ 变红]** → 缓解：**双向反向验证**（挪走 ⇒ 逐字节 IDENTICAL；放回 ⇒ CHANGED），
  且新节**有退化保护**（空则整节不输出）。**已实测**。
- **[4 件实现里有的只能在本机写、不能在 VM 上编]** → 缓解：本机无 cargo ⇒
  **所有编译与测试读数一律上 VM**；本机只落文本。**若 VM 不可达，则本件的实现部分标"未做"**，
  **不许**用"本机看起来对"当读数。
- **[`agent/completion.rs` 的 `use crate::common::event` 可能引入环]** → 缓解：先跑
  `python scripts/verify/module_graph.py` 取读数；**有环即停**，不许先合入再修。
- **[28 处口径改写会牵动生成链]** → 缓解：改完**必重跑** `gen_specmap.py` → `gen_bridge_md.py`
  （否则判据⑪ 红）；每笔改动后跑三条门禁。
- **[并行作业：另一条 schema 线在同一棵树里]** → 缓解：**只 `git add` 我自己的具体路径**，
  **禁止 `git add -A`／`git add .`**；`git status --porcelain` 逐字交件。

## 排除清单

| 不写入 | 为什么 | 出处 |
|---|---|---|
| **`WC-IC-001` 契约册逐模块展开** | **★ 已裁定：暂不纳入**（作者 2026-09-28，经上级转来）⇒ **待第 4 件落地后一并评估**。**评估时要给三样**：① **契约节要写什么**（`src/agent/{audit,protocol,completion}` 各自的入参／出参／失败形态与错误码）；② **牵动哪些册**（`WC-IC-001` 新增节；若同时要接口号，则 `WC-IRS-001` 的 `IF-012`；连带 `WC-RTM-001` 追溯面）；③ **代价**（册数与接口号的配置项变更手续、跨册一致性核对工作量） | 作者 2026-09-28 裁定（转录见 `review.md` §一之一）；册 `docs/理论/冲突总账.md` §7.15 末「★ 仍待人裁的一格」 |
| **能力面的挂法（新能力 vs 挂既有能力）** | **★ 已裁定：保留新能力 `agent-runtime`**（作者 2026-09-28；独立评审席对 delta 未提异议）⇒ **不改成挂既有能力** | 同上传录；册 §7.15「★★ 仍待人裁的一格（另一读法）」 |
| **`internal/job` 的落盘登记簿** | 本项目已裁定它多余（"待办"由账本折叠回答）；带回来＝第二份待办真相 | `src/carrier/recover.rs` 头注；`src/carrier/providers.rs` 的 `Job` 头注 |
| **改 `src/carrier/**` 的任何行为** | 它已成立且在服务；发现的问题**只登记不动手**（并行/他人文件面纪律） | skill §十四 |
| **`docs/schemas/**` 的任何改动** | 那是**另一条并行线**的文件面 | 上级裁定（2026-09-28） |
| **`cargo`／`rustc` 的本地读数** | 本机没有 cargo ⇒ 任何"本地编译通过"的说法都是假证 | 实测：`cargo` 不在 PATH、`~/.cargo` 不存在 |
| **变更号拟 `FC: WC-FC-2026-004`（已撤回）** | **按目录名避让**（仓内已有归档目录 `2026-09-28-fc-2026-004-assertions`，**其 `proposal.md` 号栏逐字仍为「〔待作者给〕」** ⇒ 依据是目录名 slug，不声称件内已占号）；**现用号＝`WC-FC-2026-005`**（作者 2026-09-28 裁定） | `templates/proposal.md` 逐字「号由人给，agent 不自己编号」 |

## L5 覆盖边界

> **"规格已定、只是今天没做到"** 的东西放这里。**本节不得被读成"能力已成立"。**
> 四格都要有；第 ② 格的读数**现取**（命令 ＋ 输出 ＋ 时点 ＋ 对象）。

| # | 书里的判据出处 | 今天的实测读数（红／绿 ＋ 命令与输出） | 为什么还没做到 | 落点 |
|---|---|---|---|---|
| 1 | 书 `2-依据/15-世界核心的组成与职责.md:143` 逐字「**门禁** ｜ 按能力 + 不可逆性拦动作、留审计 ｜ `管` ｜ **✅ 有（`agentd`，测试全绿）**」（散件已退场 ⇒ 解析根 `git show 457c954^:"2-依据/15-世界核心的组成与职责.md"`） | **部分绿**：门禁与不可逆性拦动作**已在**世界核心里并有会红断言（`tests/atom_reversibility.rs` 的 `a01`–`a07`）；**留痕**那一半（结构化审计）**红**——仓根 `agentd/internal/audit` 的 Rust 侧对应模块**今天不存在**（`python scripts/verify/spec_bridge.py` 判据② 会点名 `tests/agent_audit.rs` 不存在） | Agent 面按三句裁定从仓根 Go 迁入世界核心，本件是第一步；实现与断言按 `tasks.md` 第 1 组逐件落地 | 本 change `tasks.md` 第 1 组 |
| 2 | 书同节 `:322` 逐字「**管** ｜ 门禁（能力表 + 不可逆分级 + 审计）——**运行时的一部分** ｜ **自造**（`agentd` 是**现成的一半**）」 | **现取**（`1b58dc0`）：`Select-String -Path world-core\src\*.rs,world-core\src\carrier\*.rs -Pattern 'journald\|Auditor'` ⇒ **0 命中**；`-Pattern 'btrfs'` ⇒ **0 命中** ⇒ 审计出口与撤销编排都是**红** | 同上；另：`btrfs` 的**真快照**只能在 Linux 上跑，本机与 VM 的 `/tmp` 都不是 btrfs ⇒ 这条读数**今天取不到**（如实登记，见第 3 行） | 本 change `tasks.md` 第 1 组；真 btrfs 验证落 `cover-remaining-capabilities` |
| 3 | `WC-SQAP-001` 的覆盖率门槛（行 ≥80%、核心分支 ≥90%） | **未取**：本机没有 cargo，覆盖率要在 VM 上跑；**本件不含覆盖率报告** | 覆盖率属 S5／R4 准出材料，不是立件的前置 | `tasks.md` 第 3 组（VM 上取）；缺口登记在 `cover-remaining-capabilities` |
| 4 | 册 §7.15 的两次立件失败（判据④ 与 `validate --all --strict` 均判红） | **已转绿**：`validate agentd-in-rust-into-worldcore --type change --strict` ⇒ rc=0；`python scripts/verify/spec_bridge.py` ⇒ 判据④ `[OK]`。**但判据② 对 4 个尚未落地的测试文件保持"待补"标记**（不是绿，是**明确写成未做**） | 实现未做 | 本 change `tasks.md` 第 1 — 2 组 |

## Migration Plan

**落地步骤**（每一笔提交时树都必须是绿的）：

1. **本笔**：change 四件产物齐（proposal／design／tasks／review ＋ delta）＋ 生成器补丁 ＋ 重跑 `generated/BRIDGE.md`。
   此时**不落任何 `src/agent/**`** ⇒ 期望 `spec_bridge.py` **16/0**、`validate --all --strict` rc=0。
2. **逐件落地 4 件缺口**（一件一笔）：同一笔里落**该件的实现 ＋ 会红断言 ＋ 把该件证据行的
   「（待补）」改回真证据** ⇒ 每笔提交后仍 **16/0**。
3. 每笔都跑：`spec_bridge.py`／`validate --all --strict`／`table_width_audit.py <file>`；
   改了生成输入则重跑 `gen_specmap.py` → `gen_bridge_md.py`。
4. **文档口径改写** 28 处（5 件）⇒ 重跑生成链 ⇒ 复跑三条门禁。
5. **仓根 Go 退场** ＋ 6 处连带归位（仓根 `check.sh`／`README.md`／`.gitignore`／
   `.scope-declaration.json`／`REF-07-02` 登记／CI 的 `working-directory`）。
6. **收口**：tasks 全勾 ⇒ 请独立评审 ⇒ **由作者签** ⇒ 归档 ⇒ 复跑 `validate --archived` 与守卫。

**回滚策略**：全部是**新增文件 ＋ 定点文本改动**。
- 退到第 1 步之后：`git revert <该笔>`（生成器补丁有退化保护，退掉它 `generated/BRIDGE.md` 仍自洽）。
- 退到开工前：`git revert` 本 change 的全部提交；`agentd/**` 的退场也在其中
  （旧件**留在 git 历史**，故 `git show <退场前提交>:agentd/<path>` 是它的解析根）。
- **不存在"退到一半"的中间态**：`src/carrier/**` 一个字节都没动。

## Open Questions

1. ~~**变更号由谁给**~~ ⇒ **已定：`WC-FC-2026-005`**（作者 2026-09-28 裁定）。
   沿革：本件曾一律写「〔待作者给号〕」，登记在 `docs/理论/冲突总账.md` §八；**现按裁定填实**。
2. ~~**能力面的挂法**~~ ⇒ **已裁定：保留新能力 `agent-runtime`**（作者 2026-09-28 裁定；
   独立评审席对 delta 未提异议）⇒ **不改挂点**。
3. ~~**内部实现是否纳入 `WC-IC-001` 契约册**~~ ⇒ **已裁定：暂不纳入**（作者 2026-09-28 裁定）；
   **待第 4 件落地后一并评估**（评估要给：契约节写什么／牵动哪些册／代价）。
4. **真 btrfs 快照的验证环境**：`/tmp` 与既有 VM 盘都不是 btrfs ⇒ 撤销编排的**真命令**
   只能在真机上验；本件只验**编排的可观察行为**（调用次数、顺序、失败即不执行）。
   **不影响**规格与任务拆分 ⇒ 留此处。
