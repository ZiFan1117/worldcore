# Spec Delta

## Purpose

规定 **Agent 运行时**（世界核心「管」那一层在执行侧的那一半）里**今天还没有落点**的四件事：
**① 结构化审计记录**（意图与动作的字段集、一条记录恒占一行、可回退到文件）；
**② 行分隔的结构化请求／应答通道**（一行一问一答、坏字节不吞下一条）；
**③ 完工后的通告**（活儿结束了，世界得说得出"它结束了"，而**不再另立一本完工铃登记簿**）；
**④ 可观察的载体撤销点编排**（动手前的退路：编排出命令、失败即不执行、位置可判）。

> **本能力为什么只有这四条**（本件是**修正后**的第一版，理由逐字落在下面）：
> 原 Go `agentd/` 的 8 个包，**4 个在 `src/carrier/`（M10）里已经有对应实现**
> 并且已有**会红的断言**（逐条对账见 `design.md` 的落位表）。
> 若把这 4 条也写成新 Requirement，就是**同一件事的第二个权威载体**——
> 那不是"补齐"，那是**重复实现**（`WC-ATOM-001` §二 A-1「单意图」要拆的正是这种并列）。
> 更硬的一条：Go 侧 `internal/job` 的**落盘登记簿**被本项目**明确拒绝**——
> `src/carrier/recover.rs` 头注逐字「旧实现在载体侧自己维护一本完工铃登记簿
> （落盘、重启后标记"丢了"）。现在**那本登记簿是多余的**：登记簿要回答的"哪些活还没干完"，
> 由**账本折叠**回答」；`src/carrier/providers.rs` 的 `Job` 头注同文。
> ⇒ **那本登记簿不许被带回来**；带回来的话，世界上就有了第二份"待办真相"。
>
> **本能力的 Requirement 号**：按本项目现行规矩，新写的 Requirement 必须有流程侧号；
> 流程侧今天没有对应需求 ⇒ **逐条登记为「无号·待流程侧增补」**，**不造号、不拿相近号硬凑**。
>
> **在册面**：本 change 尚未归档 ⇒ 按 OpenSpec 的规矩，这份 delta 在**归档时**才并入主规格。
> 归档之前，本能力的 Requirement 逐条登记在 `ninedim/records/生成物/BRIDGE.md` 的
> 「在办 change 引入的能力承诺」那一节（由生成器现取；判据④ 只扫主规格树，故那一节是它的补丁）。

## ADDED Requirements

### Requirement: 〔无号·待流程侧增补〕结构化审计记录：字段固定，一条记录恒占一行

Agent 每一次意图与每一次动作 SHALL 以**字段集**的形式留痕，字段名 SHALL 取自固定的约定集合
（`MESSAGE`／`INTENT`／`CAPABILITY`／`VERB`／`PARAMS`／`SNAPSHOT`／`GRANTED_BY`／
`OUTCOME`／`DURATION_MS`／`JOB_ID`），SHALL NOT 把两个不同含义塞进同一个字段。
转到**文本行协议**（journald 那一层）时，字段值里的换行 SHALL 被**就地替换**，
使**一条记录恒占一帧**——否则按行分帧的读端会把一条记录读成两条。
文件回退形态 SHALL 是 **JSON Lines**（一行一条、逐行可解析），且每条 SHALL 带一个非空的时间戳字段。
同时挂多个审计出口时，一个出口失败 SHALL NOT 阻止其余出口收到该记录。

#### Scenario: 值里的换行不撕裂记录

- **WHEN** 一条审计记录的某个字段值里含换行符，必须转成行协议的一帧
- **THEN** 那一帧里 SHALL NOT 出现裸换行，且**帧数**与写入次数相等（记录条数不因值里的换行而变多）
- **证据**：`scripts/test/agent_audit.rs::g01_newline_in_value_does_not_split_the_frame`

#### Scenario: 文件回退是 JSON Lines 且带时间戳

- **WHEN** 用文件回退形态记录两条，再按行读回
- **THEN** 读回 SHALL 得到两条，每条的字段与写入一致，且每条都带时间戳字段（非空）
- **证据**：`scripts/test/agent_audit.rs::g02_file_fallback_is_jsonl_with_timestamp`

#### Scenario: 多路出口：一路失败不阻塞另一路

- **WHEN** 同时挂两个出口，第一个返回失败
- **THEN** 第二个 SHALL 仍然收到这条记录，且调用方拿到的错误 SHALL 是**第一个**失败的错
- **证据**：`scripts/test/agent_audit.rs::g03_multi_sink_isolates_failures`

#### Scenario: 字段名是固定集合，不许改名

- **WHEN** 任何一条意图或动作记录被构造
- **THEN** 它用到的字段名 SHALL 落在约定集合内（含 `MESSAGE` 与 `OUTCOME`），
  且意图记录带 `INTENT`、动作记录带 `DURATION_MS`——**改名即变红**
- **证据**：`scripts/test/agent_audit.rs::g04_field_names_come_from_the_fixed_set`

### Requirement: 〔无号·待流程侧增补〕行分隔的结构化请求与应答：一问一答，坏字节不吞下一条

Agent 运行时 SHALL 以**行分隔的 JSON** 暴露一次调用：**一行请求进、一行应答出**。
应答 SHALL 是结构化的（`ok` ＋ 失败时的机器可读 `err_code`），SHALL NOT 要求调用方从散文里猜结果。
请求无法解析时，SHALL 回一条 `ok=false` 的应答并点名**协议类错误码**，
且 SHALL NOT 让那串坏字节吞掉**其后**的合法请求。同一连接上的应答顺序 SHALL 与请求到达顺序一致。

#### Scenario: 一问一答，顺序一致

- **WHEN** 在一个连接上依次发两条合法请求
- **THEN** 两条各收到一条与之对应的应答，且应答顺序与请求顺序一致
- **证据**：`scripts/test/agent_protocol.rs::p01_one_request_one_response_in_order`

#### Scenario: 不可解析的请求不吞掉下一条

- **WHEN** 先发一串无法解析成 JSON 的字节，紧接着发一条合法请求
- **THEN** 坏的那条收到 `ok=false` 且 `err_code` 点名协议错误，**紧跟的合法那条仍被正常处置**并给出成功应答
- **证据**：`scripts/test/agent_protocol.rs::p02_bad_bytes_do_not_swallow_the_next_request`

#### Scenario: 失败也结构化，不靠散文

- **WHEN** 一条合法请求被处置而结果是拒绝
- **THEN** 应答的 `ok` 为假且 `err_code` 非空——调用方 SHALL 能只按 `err_code` 分支
- **证据**：`scripts/test/agent_protocol.rs::p03_refusals_are_structured_not_prose`

### Requirement: 〔无号·待流程侧增补〕完工发通告，但不另立登记簿

一项长活儿结束时，世界 SHALL 有一条**可读回的完工事实**：它 SHALL 以**通告**（`notice`）的形式
落进账本，带活儿的标识、终态与退出码。完工这件事 SHALL NOT 由**第二本登记簿**回答——
"哪些活还没干完" SHALL 由**账本折叠**回答（一条有意图、没有完工通告的请求就是"还没干完"），
否则"待办清单"会成为第二份真相。活儿的**启动失败** SHALL 同样留下可读回的事实（语义是失败），
SHALL NOT 静默。

#### Scenario: 活儿结束 ⇒ 账本里读得到它的完工通告

- **WHEN** 一个活儿被启动并结束（含非零退出）
- **THEN** 从账本折叠出的读模型里 SHALL 找得到一条以该活儿标识为主题的完工通告，
  其终态与实际结果一致（非零退出 ⇒ 终态为失败且退出码非零）
- **证据**：`scripts/test/agent_completion.rs::j01_completion_is_a_ledger_notice`

#### Scenario: 启动失败也留可读回的事实

- **WHEN** 一个活儿因为命令无法启动而失败
- **THEN** 账本里 SHALL 仍有一条以该活儿标识为主题的完工通告，终态为失败，
  且 SHALL NOT 只在进程内存里报告
- **证据**：`scripts/test/agent_completion.rs::j02_start_failure_still_leaves_a_notice`

#### Scenario: 待办不靠第二本登记簿（正控：删掉登记簿，答案不变）

- **WHEN** 把任何载体侧的"登记簿"文件删掉（或压根不建），再从账本折叠回答"哪些活没干完"
- **THEN** 答案 SHALL 不变——**"还没干完"的判据是"有意图、无完工通告"，与登记簿无关**
- **证据**：`scripts/test/agent_completion.rs::j03_pending_comes_from_the_ledger_not_a_registry`

#### Scenario: 完工通告的读回是幂等的

- **WHEN** 同一个账本被折叠两次
- **THEN** 两次得到的完工通告**逐字节相同**（读法是叶子，不持有状态、不写盘）
- **证据**：`scripts/test/agent_completion.rs::j04_reading_completion_is_idempotent`

### Requirement: 〔无号·待流程侧增补〕动手前的载体撤销点：编排可观察，失败即不执行

当一项能力被声明为**高风险**且撤销策略为**动手前**时，运行时 SHALL 在动手**之前**取得一次
**载体撤销点**，并把它的位置交给调用方（可观察）。撤销点 SHALL NOT 在**人确认之前**取得。
撤销点失败时 SHALL **拒绝执行**，并把失败如实报出——**没有退路就不动手**，
这条 SHALL NOT 被读成"尽力而为"。
**口径分界 SHALL 保持**：载体撤销点撤的是**文件系统的字节**，**不是世界状态**；
它 SHALL NOT 被当作"世界可以回滚"的证据（世界状态的回滚是**追加补偿事件**，另一件事）。

#### Scenario: 高风险＋动手前 ⇒ 编排出一次撤销点且顺序在人确认之后

- **WHEN** 一项高风险、撤销策略为动手前的能力被调用，而人确认通过
- **THEN** 撤销编排 SHALL 被调用**恰好一次**，且该次调用 SHALL 发生在人确认**之后**；
  交给调用方的撤销点位置 SHALL 非空
- **证据**：`scripts/test/agent_undo.rs::u01_undo_happens_once_and_after_the_confirmation`

#### Scenario: 撤销点失败 ⇒ 不执行

- **WHEN** 撤销编排返回失败
- **THEN** 执行 SHALL 不发生（可观察的副作用为零），且失败被如实报出（不是静默跳过）
- **证据**：`scripts/test/agent_undo.rs::u02_undo_failure_blocks_the_action`

#### Scenario: 不需要撤销的策略不编排

- **WHEN** 能力的撤销策略不是"动手前"，或风险不是高风险
- **THEN** 撤销编排 SHALL NOT 被调用（调用次数为零）
- **证据**：`scripts/test/agent_undo.rs::u03_no_undo_policy_means_zero_undo_calls`

#### Scenario: 载体撤销点不是"世界可回滚"的证据

- **WHEN** 一次载体撤销点成功并被执行
- **THEN** 世界的账本 SHALL NOT 因此多出一条"回滚"记录，
  且读模型里该对象的字段 SHALL 仍反映**已经被做过的那次动作**——
  **撤销点不是补偿事件**
- **证据**：`scripts/test/agent_undo.rs::u04_carrier_undo_is_not_world_rollback`

## 与既有能力的边界（**本件不重复认领，逐条给出既有落点**）

> 这一节是**规格正文**，不是注释：它把"Go 那 8 个包的能力面"里**已经有人在管**的部分
> 逐条指到既有载体上，使读者不会以为它们"没有落点"，也**不会**把它们再写一遍。

| 原 Go 包的能力面 | 今天的既有落点（实现） | 已有的会红断言 |
|---|---|---|
| 能力声明解析（`internal/capd`）：白名单、动词收窄、风险／撤销／确认三栏、非法声明拒载 | `src/carrier/capd.rs`（`Manifest::parse`／`Manifest::load_dir`／`Capability`） | `src/carrier/capd.rs` 模块内 `#[cfg(test)] mod unit` 的 `parses_a_wellformed_manifest`／`high_risk_with_before_each_needs_undo`／`a_manifest_may_omit_the_optional_columns` |
| provider 契约（`internal/provider`） | `src/carrier/provider.rs`（`Provider` trait／`Outcome`） | `scripts/test/atom_reversibility.rs::a07_carrier_undo_is_neither_cross_checked_nor_a_proof_of_world_reversibility`（经 `providers` 的执行面） |
| 内置 provider（backlight／package／job） | `src/carrier/providers.rs`（`Backlight`／`Package`／`Job`） | `scripts/test/atom_reversibility.rs::a07_…`；`Job` 的完工面由本件 `agent_completion.rs::j01`–`j04` 接管 |
| 路由器处置顺序（`internal/router`）：查表 → 意图 → 确认 → 撤销点 → 转发 → 动作 | `src/carrier/run.rs`（`Adapter::attempt`／`manifest_precheck`） | `scripts/test/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`、`a05_non_whitelisted_actor_gets_friction_and_the_level_shows_in_the_flow`、`a06_risk_sets_friction_weight_but_not_the_verdict` |
| 行分隔 JSON-RPC 服务（`internal/server`） | **本件新增** `src/agent/protocol.rs` | 本件 `p01`／`p02`／`p03` |
| 完工铃登记簿（`internal/job`） | **本件按本项目裁定改为"完工通告 ＋ 账本折叠"**，落 `src/agent/completion.rs`；**登记簿不许带回来** | 本件 `j01`–`j04` |
| 结构化审计（`internal/audit`） | **本件新增** `src/agent/audit.rs` | 本件 `g01`–`g04` |
| btrfs 快照／回滚编排（`internal/snapshot`） | **行为已在** `src/carrier/providers.rs::execute`（第 5 步，`undo_marker` 那个口子）；**本件只补可观察断言**，落 `scripts/test/agent_undo.rs`。⚠ **不新增 `src/agent/undo.rs`**——该文件**不存在、也不打算存在**（本件**不改** `providers.rs` 一个字节） | 本件 `u01`–`u04` |

> **"组成里有它"与"本次不重写"可以同时为真**：上表前四行的能力面**已经在世界核心里**，
> 本件**不重写**它们，只登记它们的落点与既有断言——这不是缺席，是**已经有主**。
