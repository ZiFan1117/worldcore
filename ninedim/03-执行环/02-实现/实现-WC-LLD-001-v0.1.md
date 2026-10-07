# WC-LLD-001 软件详细设计说明（M01–M09）

| 项 | 内容 |
|---|---|
| 文档编号 | `WC-LLD-001-v0.1` |
| 适用阶段 | S4 实现 |
| 编制人 / 日期 | AI（DeepSeek Harness）/ 2026-09-26 |
| 审核 / 批准 | `<待人工>` / — |
| 依据 | `WC-HLD-001-v0.1`（概要设计）、`WC-IC-001-v0.1`（接口契约）、`WC-MODREG-001-v0.1`（M01–M09）、`WC-SRS-001-v0.1` |
| 基线归属 | **产品基线**（R2 后随框架基线冻结，R4 逐模块准出） |
| ⛔ 份数口径（2026-09-27 订正） | 本文件为**单文件覆盖全部模块**。`WC-SCMP-001` §4.2 原登记 `WC-LLD-M01…M06`（每模块一份）。**该偏离与 `WC-CR-002` D1（接口契约合并为 1 份）同源同因——而 `WC-CR-002` D1 已被项目负责人否决**（原话：「接口文档要单独呀，现在只是说接口少，不代表以后接口少」）⇒ **"单文件"这一形态与 D1 一道被否决**，本文件亦**须按模块独立成文**；在拆分完成前，本文件的"单文件"形态**不生效**。依 `WC-R4-DISP-001` §二 E 组（"`WC-MODREG-001:130` 的合并主张须与 **IC/LLD 头部**的'待批'口径对齐"）与 D 组第 1 行订正。拆分形态（按模块分册／按接口分册／先做最小版）与时间点 **⚠ 待人工裁定**（`WC-R4-DISP-001` §三 **E-3**） |

> **裸 `Step N` 视为无效引用**——本文件引用 Step 处一律写「项目 Step N」或「上游 Step N」；对照表唯一权威处 = `WC-MODREG-001` §2.2，其他文档只引用、不复写对照表。

> **本文件不设修订记录**：历次改动的「为什么改、依据哪一条」写在 **git 提交信息**里；正文只写**现在是什么**。

> **本文件与 HLD 的分工**：HLD 回答"分几层、为什么这么分"；LLD 回答
> "**每个模块里具体是什么数据结构、每个函数做什么、错了怎么办**"。
> 因此本文不重复架构理由，只写可实现、可复核的细节，并**逐条挂到测试**——
> 写不出测试的细节，是设计没想清楚，不是测试没写。

---

## 〇、原子表（**原子化设计在本文件里的落点**）

> **栏位口径**照项目工作流的原子表六栏（出处：`ninedim/records/openspec-流程件/schemas/opsx-swe-gb-atom/templates/design.md`
> 的「原子表」节；约定本身出处 `WC-ATOM-001` §二）。**每个模块一行，逐栏非空**；
> `intent` 里出现「与／和／及」并列两事 ⇒ 拆。
>
> **⚠ 本表不是宣言**：最后两栏是**命令与读数**，不是结论。读数现取——
> `python scripts/verify/module_graph.py`（**以该命令输出为准，本表不复述通过数**）。
>
> **本表与 `WC-MODREG-001` §2 的分工（防止同一事实两处漂）**：
> 本表的 `intent` 与 `deps` 两栏**逐字取自** `WC-MODREG-001` §2 的同名列，
> **该册是唯一权威**；两处不一致时**以 `WC-MODREG-001` §2 为准**（本条没有机核判据，**只有人核**）。

| 原子（真实路径） | intent（一句话） | 四件同夹（契约／实现／测试各在哪） | deps == import | 生成物（重跑命令／无） | 机核读数 |
|---|---|---|---|---|---|
| `src/ontology_definition/mod.rs`（`M01`） | 世界的**法律**：事件形状、合法变更的判据。 | 契约：`WC-IC-001` §5.1＋§3.5 的 `IF-005`；实现：本文件；测试：`scripts/test/contract.rs::c04_ontology_load_rejects_missing_file_and_empty_families`、`scripts/test/acceptance.rs::t6_bad_ontology_refuses_to_start` | 声明 `M05`＝真实 import `M05`（**逐边相等**） | 无 | 判据② 该模块 `deps_judged=True`、`deps_declared_unverified=∅`、`deps_undeclared=∅` |
| `src/ledger/mod.rs`（`M02`） | 世界的**事实**：只追加的语义事件日志，分配 `seq`，处理崩溃尾迹。 | 契约：`WC-IC-001` §5.2＋§3.1 的 `IF-001`；实现：本文件；测试：`scripts/test/contract.rs::c22_file_always_ends_on_a_line_boundary`、`scripts/test/acceptance.rs::t2_events_survive_restart` | 声明 `M05`＝真实 `M05` | 无 | 同上（该模块） |
| `src/ontology_instance/readmodel.rs`（`M03`） | **状态 = fold(账本)**：纯派生物，可随时删掉重算。 | 契约：`WC-IC-001` §5.3＋§3.9 的 `IF-009`；实现：本文件；测试：`scripts/test/contract.rs::c06_incremental_apply_equals_full_fold`、`scripts/test/acceptance.rs::t8_read_model_refuses_broken_ledger` | 声明 **无**＝真实**无**（生产代码零出边） | 无 | 同上（该模块） |
| `src/lib.rs`、`src/main.rs`（`M04`） | 装配启动，持有**唯一写入口** `World::commit`。 | 契约：`WC-IC-001` §5.4＋§3.8 的 `IF-008`；实现：本两文件；测试：`scripts/test/contract.rs::c15_errors_carry_machine_readable_codes`、`scripts/test/atom_declared_only.rs::b05_cli_append_of_an_undeclared_entity_is_refused` | 声明 `M01,M02,M03,M05,M06,M07,M08,M09,M10`（9 边）＝真实 9 边 | 无 | 同上（该模块） |
| `src/gate/mod.rs`、`src/gate/guard.rs`（`M05`） | 一件事**现在能不能做**：默认拒绝，按不可逆性加摩擦。 | 契约：`WC-IC-001` §5.5＋§3.2 的 `IF-002`；实现：本两文件；测试：`scripts/test/contract.rs::c11_irreversible_is_owner_only_and_the_refusal_does_not_lie`、`scripts/test/atom_reversibility.rs::a06_risk_sets_friction_weight_but_not_the_verdict` | 声明 `M10`＝真实 `M10` | 无 | 同上（该模块） |
| `src/gui_projection/language.rs`（`M06`） | 结构化出口：逐行 JSON，给程序读。 | 契约：`WC-IC-001` §5.6＋§3.3 的 `IF-003`；实现：本文件；测试：`scripts/test/acceptance.rs::t14_language_projection_matches_read_model`、`scripts/test/projection_leaf.rs::p01_language_alone_is_complete_and_the_other_reading_never_runs` | 声明 `M03`＝真实 `M03` | 无 | 同上（该模块） |
| `src/gui_projection/visual.rs`（`M07`） | 渲染出口：终端可读，**排版仍可被审计**。 | 契约：`WC-IC-001` §5.7＋§3.4 的 `IF-004`；实现：本文件；测试：`scripts/test/acceptance.rs::t15_visual_projection_is_human_readable_yet_auditable`、`scripts/test/projection_leaf.rs::p02_visual_alone_is_complete_and_the_other_reading_never_runs` | 声明 `M03`＝真实 `M03` | 无 | 同上（该模块） |
| `src/ontology_instance/checkpoint.rs`（`M08`） | **带 `base_seq` 的缓存**，非真相；删掉后重算结果必须相同。 | 契约：`WC-IC-001` §5.8＋§3.10 的 `IF-010`；实现：本文件；测试：`scripts/test/cli.rs::cli15_usage_lists_three_checkpoint_subcommands`、`scripts/test/cli.rs::cli17_checkpoint_resume_falls_back_to_post_hoc_comparison` | 声明 `M03,M05`＝真实 `M03,M05` | 无 | 同上（该模块） |
| `src/bus/mod.rs`（`M09`） | 跨进程入口：**一个套接字一个身份**，权限即身份。 | 契约：`WC-IC-001` §5.9＋§3.6 的 `IF-006`；实现：本文件；测试：`scripts/test/contract.rs::c14_channel_takes_identity_from_kernel_not_from_request`、`scripts/test/channel_bounds.rs::l02_the_second_simultaneous_connection_is_refused` | 声明 `M05`＝真实 `M05` | 无 | 同上（该模块） |
| `src/carrier/`（`M10`，**目录型**：10 个 `.rs`） | **载体侧的手**：按清单调载体，只执行不裁决。 | 契约：`WC-IC-001` §5.10 的 `IF-011`；实现：该目录下 10 个文件；测试：`scripts/test/atom_reversibility.rs::a07_carrier_undo_is_neither_cross_checked_nor_a_proof_of_world_reversibility` | 声明 **无**＝真实**无** | 无 | 同上（该模块；目录型也**逐边核对**，不整条跳过） |

**A-1…A-6 在本文件里各落在哪一栏（逐条给落点，不写"本文件遵循原子化"）**：

| 约定 | 落点 |
|---|---|
| **A-1 单意图** | 上表 `intent` 列**每行一句**（机器面在 `WC-MODREG-001` §2，判据①） |
| **A-2 一个原子一个文件夹，四件同夹** | 上表「四件同夹」列**逐行给出三处落点**。⚠ **本仓的测试不在 `src/` 同夹**（在 `scripts/test/`）⇒ 按**可指认**判、不按同目录判，口径与判据③ 一致 |
| **A-3 契约字段齐** | `intent`／`input`／`output` 见下文各模块节的「关键结构」与「不变量」；`side_effects` 的模块级落点是 `WC-MODREG-001` §2 的 `side_effects` 列 |
| **A-4 `deps == import` 且无环** | 上表 `deps == import` 列（判据② 逐模块逐边相等；环按强连通分量逐条打印） |
| **A-5 生成物不许手编** | **本文件不是生成物**；上表「生成物」列对十个模块**一律为"无"**。本仓由判据⑪⑫⑬ 管的生成物是 `generated/BRIDGE.md`／`generated/specmap.json`／`generated/节对齐.md` 那一族 |
| **A-6 UTF-8 无 BOM** | 本文件自身（`python scripts/verify/plain_text_audit.py <本文件>`） |

> **覆盖口径（如实登记）**：上表**十行＝`M01`–`M10`**，与 `WC-MODREG-001` §2 的十行**同行数**。
> 本文件正文的逐模块细节节**只写 `M01`–`M09`**（`M10` 的实现细节在 `src/carrier/` 各文件头注与
> `WC-IC-001` §5.10）——那是**正文覆盖面**的既知状态，不是"`M10` 已在此详述"。

---

## 一、`M01` 本体（法律·形状）—— `src/ontology_definition/mod.rs` / `ontology.json`

| 项 | 细节 |
|---|---|
| 关键结构 | `Ontology { world: u64, required: Vec<String>, optional: Vec<String>, families: BTreeMap<String, Family>, vocab_hash: String }`；`Violation` 为**类型化**枚举：`NotAnObject` / `MissingField{at,field}` / `BadVersion{expected,got}` / `UnknownKind{kind}` |
| 加载算法 | 读文件（`ReadFail`）→ 解析 JSON（`BadJson`）→ **静态墙 `guard::assert_not_other_writable`**（`src/ontology_definition/mod.rs:81`）→ 取 `world`（`NoVersion`）→ 取 `envelope.{required,optional}`（`NoEnvelope` / `BadField`）→ 取 `families`（`NoFamilies`）→ 逐家族取 `required/optional`（**跳过 `_` 开头的键**）→ 家族列表为空即 `NoFamilies`（`:113`）→ 算 `vocab_hash`。⚠ **订正**：原设计把静态墙画在"家族为空检查**之后**"，实测位置是**解析成功之后、取 `world` 之前**（`:72-86`）。"在读取成功之后"这个顺序是刻意的——先读成功、再查权限，否则"文件不存在"会被报成权限问题（`c04` 实测抓到，`src/ontology_definition/mod.rs:77-80` 注释） |
| 静态墙的**三道检查**（依 `WC-R4-DISP-001` §二 F 组第 5 行与 `guard.rs` 对齐） | `assert_not_other_writable` 内部**依次**做三道：① **`assert_not_symlink`**——用 `symlink_metadata`（lstat 语义）拒绝**符号链接**（`src/gate/guard.rs:53`、实现 `:105`）；② **文件本身** `mode & 0o022 == 0`（`:58`）；③ **所在目录** `mode & 0o022 == 0`（`:77`）。⚠ **原设计只写"静态墙"一词，漏了第 ① 道**——而它正是"检查的是 A、用的是 B"这条绕过路径的封堵（`WC-RV-R2-001` FIND-04 / S-05）。三道中任一失败即 `Err` ⇒ **拒绝启动**。另：**属主断言 `assert_owned_by` 不在本路径内**——它只由部署方 `--owner-uid` 显式触发，且只在 `check` 子命令的 `World::open` **之后**执行（`src/main.rs:111-122`，`DEBT-02`） |
| `vocab_hash` | 对**规范化 JSON**（紧凑序列化、键有序）**剔除 `_` 键**后求 FNV-1a ⇒ 改注释不换 hash、改语义必换 hash |
| 校验算法 | 对象性 → 逐信封必填字段 → `world` 版本 → 家族存在性 → 逐家族信纸必填字段 |
| 错误路径 | 6 类加载错误 + 4 类 `Violation`（见 `WC-IC-001` §三） |
| 不变量 | 加载失败**必须**导致拒绝启动；`vocab_hash` 只由语义内容决定 |
| 测试 | `c02`（8 字段逐字段）、`c04`（缺文件/空家族）、`ontology::unit::*`（hash 口径）、`t6`（坏本体拒启） |
| 技术债 | 无 |

## 二、`M02` 账本（事实）—— `src/ledger/mod.rs`

| 项 | 细节 |
|---|---|
| 关键结构 | `Ledger { path, sink: Box<dyn Sink>（私有）, next_seq, poisoned: Option<String>, _lock: LockGuard, last_chain, chained }` |
| 打开算法 | **取单写者锁** → 不存在则创建（并过墙）→ 存在则过墙 → **丢弃末尾半行**（截到最后一个 `\n`）→ 逐行解析并校验 `seq` 连续 → `next_seq = last + 1` |
| **I/O 缝** | `Sink`（`pub(crate)`，4 个原语：`byte_len` / `put`（写+flush）/ `sync`（fsync）/ `truncate`）。生产实现**只有** `FileSink`；测试替身 `FlakySink` 在 `#[cfg(test)]` 内，**不进发布产物**。缝里**只有 I/O 原语**——不含取号、摘要链、本体校验、门禁裁决，故注入故障只改 I/O 结果、**不改 `append` 的决策路径**；`sink` 为私有字段且生产代码无 setter ⇒ **不构成新的绕过路径**（2026-09-27 加） |
| 追加算法 | 若 `poisoned` 拒写 → 校验 `seq == next_seq` → 算链并写入 `chain` → 序列化整行 → 记 `pre_len`（`sink.byte_len`）→ `sink.put` → 失败则**回滚到 `pre_len`**（`sink.truncate`；回滚再失败 ⇒ 标记污染）→ `sink.sync` → `next_seq += 1`、`last_chain = chain` |
| 单写者锁 | `OpenOptions::create_new(true)` 建 `*.lock`；已存在则读 pid，看 `/proc/<pid>` 是否存活；**陈旧锁回收**；`Drop` 删锁 |
| 错误路径 | 前缀一律 `ext.world.Ledger.`，**共 19 个叶子码**（2026-09-27 从源码逐条读出；判据与处置见 `WC-IC-001` §3.1）：`CreateFail`(`src/ledger/mod.rs:175`) / `OpenFail`(`:237`) / `ReadFail`(`:196`/`:401`/`:404`) / `TruncateFail`(`:207`) / `StatFail`(`:321`) / `SeqGap`(`:225`) / `Corrupt`(`:218`/`:409`) / `MissingSeq`(`:222`/`:298`) / `SeqMismatch`(`:301`) / `EncodeFail`(`:315`/`:437`/`:497`) / `WriteFail`（含回滚结果，`:352`/`:359`/`:629`/`:677`）/ `SyncFail`(`:333`/`:710`) / `Poisoned`(`:289`/`:693`/`:722`) / `Locked`(`:139`) / `LockFail`(`:149`/`:156`) / `NoChain`(`:465`) / `MixedChain`(`:470`) / `MissingChain`(`:481`) / `ChainMismatch`(`:484`) |
| 落笔能力字段（依 `WC-R4-DISP-001` §二 F 组第 2 行） | 字段名**现为 `sink`**（`src/ledger/mod.rs:79`），且**私有**、**无 setter** ⇒ "一个写入口"是**类型级**保证。⚠ `Ledger.file` 是**过期措辞**，仍存在于两处**不在本文件内**的地方：`WC-HLD-001:66`（该行由 F 组第 2 行负责回灌）与 `src/ledger/mod.rs:13` 的**文档注释**（"`file` 字段私有 ⇒ 全 crate 只有 `Ledger::append` 能改账本"）。**本文件 §二 早已写作 `sink`，无需改动**，此处仅登记另两处以免再被引用 |
| 不变量 | 只追加；文件**必须以 `\n` 结尾**；`fsync` 成功后才推进 `next_seq`；污染后**拒绝再写** |
| 测试 | `t1`/`t2`/`t3`/`t4`、`c07`（第二个写者被拒）、`c08`（陈旧锁回收）、`c16`–`c22`（摘要链）、**`U20`–`U22`（故障注入：写失败→回滚 / 回滚失败→污染 / `fsync` 失败→污染）** |
| 技术债 | `DEBT-05`（无摘要链 ⇒ 能写账本者能伪造自洽历史） |

## 三、`M03` 读模型（状态）—— `src/ontology_instance/readmodel.rs`

| 项 | 细节 |
|---|---|
| 关键结构 | `State { last_seq, seen, acts, notices, objects: BTreeMap<String, BTreeMap<String, Value>> }` —— **字段全私有** |
| 折叠算法 | `apply`：`seq == last_seq + 1` 否则 `Err`；按 `kind` 分派：`change` → 核对 `before` 与当前值一致后写入 `after`；`act`/`notice` → 计数；未知家族 → `Err` |
| 关键设计 | `change` **首次出现某 path 时不核 `before`**（此前无当前值可比）——这是**自洽检查**而非防篡改，见 `DEBT-05` |
| 规范形式 | `to_json()` 键有序 ⇒ 同样账本渲染同样字节；`digest()` = 规范形式串的 FNV-1a（**非加密**） |
| `from_json` | 从规范形式重建 `State`；因字段私有，**只有本模块**能构造 ⇒ "从快照恢复"也必须经过这里。⚠ **它同时是构造 `State` 的第二条路径**（第一条是 `fold`/`apply`）——`WC-IC-001 §2.3 不变量①` 原文"只能由 `fold`/`apply` 产生"**与实现不符**，已按 `WC-R4-DISP-001` §二 F 组第 8 行订正为"三条路径：`fold`/`apply`/`from_json`"。它**必须**校验三条，缺一即 `ext.world.ReadModel.BadState`：① `last_seq`/`seen`/`acts`/`notices` 存在且为非负整数（`src/ontology_instance/readmodel.rs:171-175`）；② `objects` **若存在**必须是对象（`:177-180`；⚠ 整个缺失时**不报错**、按空对象处理——这是实现事实，不是允许省略）；③ `objects[主体]` 必须是对象（`:182-184`）。**它不校验**"该状态是某个账本前缀的折叠结果"——那只能由 `Checkpoint::verify` 的指纹比对给出（§七） |
| 测试 | `t7`（★ 可删掉重算）、`t8`（三类坏账本）、`c06`（增量 == 全量）、`readmodel::unit::*` |
| 技术债 | `DEBT-05` |

## 四、`M04` 运行时（唯一写入口）—— `src/lib.rs` / `src/main.rs`

| 项 | 细节 |
|---|---|
| 关键结构 | `World { ontology: Ontology, policy: Policy, ledger: Ledger }` —— **字段全私有**，外部只有 `&` 访问器 |
| `open` 顺序 | 本体 → 策略 → 账本 → **版本一致性断言**（`event::WORLD_VERSION == ontology.world()`，不符即拒启） |
| `commit` 顺序 | 取号 → 造事件 → **本体校验** → **门禁裁决**（`act` 用 `decide`，`change` 用 `authorize_write`）→ 落笔。**顺序不可交换** |
| 拒绝路径 | 拒绝时**不写原事件**，改记 `notice`（`gate.rejected` / `gate.awaiting-approval` / `gate.write-rejected`）；**流水写失败也必须把拒绝理由送达调用方** |
| 编译期保证 | `pub` 面只有 `&` 访问器 + `commit`；`lib.rs` 带 **`compile_fail` doctest** 锁死"外部无法 `&mut w.ledger`" |
| CLI | 子命令 `check` / `kinds` / `policy` / `append` / `read` / `state` / `project`；退出码 `0/1/2`；`--owner-uid` 为可选属主断言 |
| 测试 | `t5`（违法不落笔）、`c01`（`change` 过闸）、doctest、`check.sh` |
| 技术债 | `DEBT-01`（错误为中文散文，机器需匹配子串） |

## 五、`M05` 门禁（治理）—— `src/gate/mod.rs` + `src/gate/guard.rs` + `policy.json`

| 项 | 细节 |
|---|---|
| `gate.rs` 结构 | `Policy { version, caps: BTreeMap<String, Capability>, allow: Vec<String>, writes: BTreeMap<String, Vec<String>>, irreversible_actors: Vec<String>, path }` |
| `decide`（`act`） | 缺 `capability` → `Reject`；主体不在 `subjects.allow` 白名单 → `Reject`；能力未声明 → `Reject`（**默认拒绝**）；`!reversible` 且主体**在 `irreversible_actors` 内** → **`Allow`**；`!reversible` 且主体**不在 `irreversible_actors` 内** → `AwaitApproval`（理由明说 **v1 无审批通道**）；`reversible` → `Allow`。⚠⚠ **关键订正（依 `WC-R4-DISP-001` §二 F 组第 1 行）**：原文写"`!reversible` 且主体**在白名单** → 放行"，**指代不明**——照它实现会得到"**任何白名单主体都可执行不可逆动作**"。实现事实（`src/gate/mod.rs:292-309`）判的是 **`irreversible_actors`**，而它与 `subjects.allow` 是**两个不同的清单**：出厂 `policy.json` 的 `subjects.allow = ["world://user","world://core","world://agent/*","world://presence/*"]`、`irreversible_actors = ["world://user"]` ⇒ `world://agent/1` **在白名单内、但不在不可逆白名单内**，对它**必须** `AwaitApproval`（`t10`/`c11` 断言的就是这个行为） |
| `requires_approval` 的角色（**R0 已裁定：删字段**；`WC-R4-DISP-001` §三 **E-5**） | ✅ **字段已删除，且已执行**（提交 `1217c8f`，2026-09-27）：`policy.json` 三处键、`gate.rs` 的字段 / 加载期自检 / `summary()` 序列化键、`main.rs` 的打印分支、`scripts/test/contract.rs` 的"可逆 + 需批准 ⇒ 拒载"用例**一并移除**。**删除不影响裁判**——它本**不参与裁决**（`decide` 只读 `reversible`）⇒ 属"承诺与实现不符"的消除（`DEBT-07`：v1 无审批通道，不可逆只允许 `irreversible_actors` 白名单主体）。**兼容性**：`gate.rs` 用 `serde_json::Value` 手工取值、无 `deny_unknown_fields` ⇒ **多余/未知键一律忽略**，旧策略文件带该键**仍可加载**（`scripts/test/contract.rs` 的「对照②」即为该回归） |
| `authorize_write`（`change`） | 主体白名单 → `writes` 里有该主体 → 其模式匹配 `subject` 才放行；否则拒。**默认拒绝** |
| 模式匹配 | 结尾 `*` = 前缀匹配，否则全等（`pattern_matches`，两处共用同一实现） |
| `guard.rs` 三道检查 | ① **符号链接**拒绝（`symlink_metadata`）；② mode：文件与**所在目录**均不得对 group/other 可写；③ `assert_owned_by`（部署方 `--owner-uid` 显式断言） |
| 不变量 | 策略**启动一次读入**、运行中不重读；拒绝必留痕且理由必达 |
| 测试 | `t9`–`t13`、`c01`、`c03`（6 类拒启）、`c09`（软链）、`c10`（属主）、`c11`（不可逆）、`con01-no-bypass.sh`（跨 uid 14 项） |
| 技术债 | `DEBT-02`（属主断言是工具、非自动）、`DEBT-04`（流水可伪造） |

## 六、`M06` / `M07` 两个投影（出口）—— `src/gui_projection/*`

| 项 | 细节 |
|---|---|
| 共同结构 | 每份输出**首行**为同源头：`#world-core projection=<名> world=<n> vocab=<hash> last_seq=<n> state=<hash>` |
| `mod.rs` | `header_line` / `parse_header` / `assert_same_source`（只比身份四项，**不比排版**）；`group_by_subject`（**两投影共用**的纯函数——"同源"在代码层的体现） |
| `language.rs` | 渲染：逐行 JSON（每主体一行，`fields` 为路径→值）；`parse()` 反向解析供核对 |
| `visual.rs` | 渲染：2 空格主体行 + 6 空格 `路径 = JSON值` 字段行（**排版是可审计契约**）；`parse()` 按同一规则反向解析 |
| 不变量 | 渲染函数只接受 `(&State, world, vocab)`、返回 `String`——**不持状态、不互相调用** |
| 测试 | `t14`/`t15`（各自与读模型逐项相等）、`t16`（同源 + 换词表可检出 + 落后可检出） |
| **期望渲染样本（字节级基准）**（依 `WC-R4-DISP-001` §二 F 组第 7 行补） | 三个样本全部由**源码字面量**决定；⚠ 凡出现指纹值的地方都是**运行产生**的，写进用例时**必须**以实跑输出为准（下方标【待验证】） |
| 样本 ① 「**空账本**」（`seen == 0`） | 视觉投影**共 4 行、无空行**（`src/gui_projection/visual.rs:31-39`）：<br>L1 `#world-core projection=visual world=1 vocab=<V> last_seq=0 state=<S>`<br>L2 `世界状态（视觉投影）`<br>L3 **44 个 `─`（U+2500）**<br>L4 `  （账本为空：这个世界还没有发生过任何事）`<br>——**到此结束**：**无**统计行、**无**第二个分隔线。语言投影同为空账本时**只有 1 行**（首行同源头，`src/gui_projection/language.rs:22-25`） |
| 样本 ② 「**普通值**」 | 账本 = 一条 `change(world://s, p, null → 1)`：视觉投影 L1–L3 同上，L4 `  已折叠 1 条事件（最近序号 1）｜动作 0 条｜通告 0 条`，L5 44 个 `─`，L6 `  world://s`（**2 空格**），L7 `      p = 1`（**6 空格** + `路径 = 值`；值是**紧凑 JSON**，`1` 前后无空格）。同一状态下语言投影 L2 为 `{"fields":{"p":1},"subject":"world://s"}`——⚠ **键序**为 `fields` 在 `subject` 之前：依据 `Cargo.toml:13` 的 `serde_json = "1"`（**未启用 `preserve_order`**）⇒ `serde_json::Map` 默认为 `BTreeMap` ⇒ **字典序**。【待验证：本机无 `cargo`，未实跑】 |
| 样本 ③ 「**含换行/控制字符的值**」 | 取值行的值是 `serde_json::Value` 的 `Display`（`src/gui_projection/visual.rs:53`），字符串会被**转义** ⇒ 值里的 `\n` 渲染为**字面反斜杠 + n**，**不产生真实换行**，故渲染输出**仍是单行**、与账本"内容不得出现真实换行"的行分隔约定一致（`src/ledger/mod.rs:4`）。【待验证：本条是对 `serde_json` 转义行为的推断，**未实跑**；验证方法：造一条 `after` 含 `\n` 的 `change`，跑 `world-core project visual`，再用 `od -c` 核对取值行**不含 0x0A**】 |
| **渲染样本的验证面缺口（如实登记）** | 上述样本**目前还没有独立于本模块 `parse()` 的用例**——`WC-R4-DISP-001` §二 G 组第 2 行要求"增**独立于同模块 `parse()`** 的排版用例（字节级期望样本，最好放 L3）"，并"在 `WC-UT-001 §三` 显式登记'排版契约无验证面'"。**本轮不在本文件范围内**，不得声称已完成 |

## 七、`M08` 检查点（缓存）—— `src/ontology_instance/checkpoint.rs`

| 项 | 细节 |
|---|---|
| 结构 | `Checkpoint { base_seq, digest, state }`；落盘为 `{checkpoint:1, base_seq, digest, state}` |
| 写 | 序列化 → 写文件 → 过静态墙（缓存也不该被被管者改写） |
| `verify(ledger)` | 取账本中 `seq <= base_seq` 的前缀 → 必须**恰好** `base_seq` 条（否则 `Stale`）→ 重算并比对指纹（不符 `DigestMismatch`，理由明说"**以账本为准**"） |
| `resume_unverified` | 从 `state` 重建 → 折叠 `base_seq` 之后的事件。**名字里带 `unverified` 是刻意的** |
| `read_model_with_checkpoint` | 无快照 → 全量折叠；有快照 → 续算。**两者结果必须逐字节相同** |
| 测试 | `c12`（删掉无后果）、`c13`（篡改/陈旧/坏 JSON 三类必须被拒） |
| **不变量**（依 `WC-R4-DISP-001` §二 F 组第 3 行补） | ① `capture` 时 `base_seq == state.last_seq()`（`src/ontology_instance/checkpoint.rs:52`）；② **`base_seq = 0` 合法**：`verify` 取 `seq <= 0` 的前缀得**空集**，`0 == 0` 通过，再与"空状态指纹"比对 ⇒ `base_seq=0` 的快照**只能**承载空状态；③ `base_seq` **不得**大于账本已有条数（否则 `verify` 报 `Stale`，`resume_unverified` 则可能在 `apply` 处报 `SeqGap`）；④ 落盘形态**不携带** `world` / `vocab_hash`——`write` 只写 `checkpoint`/`base_seq`/`digest`/`state` 四个键（`src/ontology_instance/checkpoint.rs:70-75`）⇒ **同一账本在不同词表下截的快照无法被区分**，`verify` 也发现不了（指纹只覆盖 `state`）。⚠ 这是**已核实的新缺口**（处置待定，见 §十一 #8）；⑤ `load` **不检查** `base_seq == state["last_seq"]`（`:100-117`）——两者不等时：若有 `base_seq` 之后的事件，续算会在 `apply` 处报错；**若没有**后续事件，则**静默**返回一个 `last_seq != base_seq` 的状态 |
| **失败形态与处置**（同上补） | `write`：`Checkpoint.EncodeFail`／`Checkpoint.WriteFail`／静态墙**散文**（无码；过不了墙即 `Err`，**不降级为警告**）。`load`：`ReadFail`／`BadJson`／`NoFormat`／`BadFormat`／`MissingBaseSeq`／`MissingDigest`／`MissingState`。`verify`：`Stale`（账本比快照短）⇒ **拒绝使用**、宁可全量重算；`DigestMismatch` ⇒ **以账本为准**、快照作废并重新生成。`resume_unverified`：`ReadModel.BadState`（`state` 非规范形式）／`MissingSeq`／`SeqGap`／`BeforeMismatch`／`UnknownKind`（续算折叠失败）。**总处置口径**：快照的**任何**失败都不得堵死"从账本全量重算"这条路——`read_model_with_checkpoint(events, None)` 永远可用 |
| **单元测试设计对应表**（模板 `IN-5`，依 F 组第 4 行补） | 见 §七 之后的独立小表 |

**§七 的「单元测试设计对应表」（模板 `IN-5`）**

> ⚠ **口径先说清**：本模块在 `src/ontology_instance/checkpoint.rs` 内**没有任何 `#[test]`**（2026-09-27 实测：`#[test]` 计数 = **0**）。它的行为全部由**契约级用例**在 crate 外驱动（`scripts/test/contract.rs`）——因为要覆盖的核心是"快照与账本矛盾时以谁为准"，那需要真实文件与真实账本。**这不是"没有测试设计"，而是"测试设计落在契约层"**；按 F 组第 4 行给出的第二个选项（"显式声明本模块无单元测试设计 + 理由"）如实登记。

| 用例编号 | 测试对象 | 覆盖功能 | 对应需求 | 输入/条件 | 期望结果 | 路径类型 | 状态 |
|---|---|---|---|---|---|---|---|
| `c12` | `Checkpoint::capture` / `write` / `load` + `read_model_with_checkpoint` | 快照是缓存、可丢弃 | `REQ-F-021` | 有快照续算 **vs** 删掉快照全量折叠 | 两者状态**逐字节相同**（`to_json()` 与 `digest()` 皆相同） | 正常 | 已实现（`scripts/test/contract.rs:466`） |
| `c13` | `Checkpoint::load` / `verify` | 坏快照三类必须被拒 | `REQ-F-021` | ① 篡改 `state` ② `base_seq` 陈旧（账本比它短）③ 坏 JSON | ① `DigestMismatch` ② `Stale` ③ `BadJson`，**三类都不得被采用** | 异常 | 已实现（`scripts/test/contract.rs:538`） |
| `c15`（**不直接覆盖本模块**） | `State::from_json` 的失败路径 | 快照 `state` 非规范形式 | `DEBT-01` | `state` 缺 `last_seq` 等字段 | `ext.world.ReadModel.BadState` 带码 | 异常 | `c15` 走的是**读模型**路径，**不构造坏快照**（`scripts/test/contract.rs:683`）⇒ 本行是**待补用例的占位** |
| **待补（编号由 `WC-TS-001` 分配）** | `Checkpoint::verify` / `load` 的边界 | 上表"不变量"②③⑤ 三条 | `REQ-F-021` | `base_seq = 0`／`base_seq` > 账本长度／`base_seq ≠ state.last_seq` | 与不变量逐条一致 | 边界 | ⚠ **缺失**——本轮**未新增**用例（不在 F 组处置范围内），登记为待补 |

**覆盖率口径**：模板 `IN-5` 要求"行覆盖率 ≥ 80%、核心分支 ≥ 90%"。而覆盖率度量（`cargo-llvm-cov` / `tarpaulin`）**尚未接入**（§十一 #5，`WC-SQAP-001` TBD-08）⇒ 本模块覆盖率**无实测值**，本设计**不填数字**。

## 八、`M09` 通道（跨进程入口）—— `src/bus/mod.rs`

| 项 | 细节 |
|---|---|
| 配置 | `channel.json`：`{channel:1, listeners:[{socket, actor, uid}]}`；`listeners` 为空即拒（"无门之门"） |
| `bind` | 拒在 group/other 可写目录建 → `bind` → `chmod 0600` → `chown` 给目标 uid ⇒ **只有该 uid 连得上** |
| `serve_once` | 接受一个连接 → 读一行 → 解析（`kind` 必填）→ 若请求**自称** actor 则必须等于映射 → `world.commit(kind, 映射里的 actor, body)` → 回一行 JSON |
| 身份来源 | **套接字文件权限**（内核在 `connect()` 时挡人），**不是**请求自称；`peer_cred()` 在本工具链仍不稳定（实测 `E0658`），故未用 |
| 错误路径 | `ReadFail`/`BadJson`/`NoVersion`/`BadVersion`/`NoListeners`/`BadListener`/`BindFail`/`ChmodFail`/`ChownFail`/`AcceptFail`/`Impersonation`/`EmptyRequest`/`BadRequest` |
| 测试 | `channel::unit::*`、`c14`（身份来自内核、冒充被拒且不落笔） |
| 技术债 | **长驻服务与并发未做**（v1 一次一连接）；`DEBT-03`（单写者锁与通道并发的交互待设计） |

---

## 九、跨模块不变量（违反即设计级缺陷）

| # | 不变量 | 由什么守 |
|---|---|---|
| 1 | 改世界只有 `World::commit` | 字段私有 + `pub(crate)` + **`compile_fail` doctest** |
| 2 | 法律在前、落笔在后 | `commit` 内固定顺序 + `t5` |
| 3 | 状态是算出来的（不持久化真相） | `State` 字段私有 + **三条构造路径全在本模块内**（`fold` / `apply` / `from_json`，见 §三；`from_json` 是快照恢复的**唯一**入口）+ `c12`（删掉快照无后果） |
| 4 | 投影不持状态、不互相调用 | 渲染函数签名 + `t16` |
| 5 | 身份来自内核，不来自请求 | `bind()` 权限 + `c14` |
| 6 | 一切跨进程内容为纯文本 | `REQ-N-001`；账本/语言投影为 JSON Lines、视觉投影为文本 |

## 十、测试映射（详细设计 → 用例）

| 模块 | 主要用例 |
|---|---|
| M01 | `c02` `c04` `t6` `ontology::unit::*` |
| M02 | `t1` `t2` `t3` `t4` `c07` `c08` `c16`–`c22` `U20`–`U22` |
| M03 | `t7` `t8` `t17` `c06` `readmodel::unit::*` |
| M04 | `t5` `c01` **`cli01`–`cli06`** doctest `check.sh` |
| M05 | `t9`–`t13` `c01` `c03` `c09`–`c11` + `con01-no-bypass.sh`（14 项） |
| M06/M07 | `t14` `t15` `t16` `project::unit::*` |
| M08 | `c12` `c13` |
| M09 | `c14` `channel::unit::*` |

全量 **68** 项（22 单元 + 17 验收 + 22 契约 + 6 CLI + 1 doctest）——逐条原始输出见 `WC-RE09-003`；用例输入/期望见 `WC-TS-001`。

> **口径（2026-09-27 当场复算）**：22 = `src/**` 内 `#[test]` 计数（`channel` 2 + `error` 2 + `gate` 4 + `guard` 1 + `ledger` 3 + `ontology` 2 + `readmodel` 4 + `project/mod` 4；`checkpoint`/`event`/`lib`/`main`/`project/{language,visual}` 各 0）；17 = `scripts/test/acceptance.rs`；22 = `scripts/test/contract.rs`；6 = `scripts/test/cli.rs`（`cli01`–`cli06`，见上表 `M04` 行）；1 = `lib.rs` 的 `compile_fail` doctest。⚠ **不计** `scripts/test/perf.rs` 的 3 项（`qg01`/`qg02`/`qg05`）——它们**不在 68 项口径内**，但属性能门禁证据（`WC-IC-001` `IF-D-11`）。

## 十一、待决与遗留（**不假装已定**）

| # | 事项 | 时点 |
|---|---|---|
| 1 | ⛔ **本文件"单文件"形态已被否决**——`WC-CR-002` D1（与 `WC-IC-001` 合并同源同因）**已被项目负责人否决** ⇒ 本文件**须按模块独立成文**；拆分形态与时间点 ⚠ **待人工裁定**（`WC-R4-DISP-001` §三 **E-3**；原登记为每模块一份、共 6 份） | R2 前 |
| 2 | `DEBT-01` 结构化错误码（现为中文散文） | R2 前 |
| 3 | `DEBT-05` 账本摘要链（读模型旧值核对只是自洽检查） | R2 后 |
| 4 | 通道长驻服务与并发（含与单写者锁的交互） | 项目 Step 6 后续 |
| 5 | 覆盖率度量（`cargo-llvm-cov` / `tarpaulin`） | S5 前（`WC-SQAP-001` TBD-08） |
| 6 | 本文件**未经人工审核**，逐模块 R4 准出须由人作出结论 | R4 |
| 7 | **I/O 缝注入的是"故障形状"，不是真实磁盘满/EIO**：`U20`–`U22` 证明的是"遇到该形状时 `append` 的处置正确"，**不能**代替真实硬件/文件系统故障实验（后者需 root + `dm-error`/`chmod` 等手段，属 S6 系统测试范围） | S6 系统测试 |
| 8 | **检查点不携带 `world` / `vocab_hash`**（§七 不变量④）：同一账本在不同词表下截的快照**无法被区分**，`verify` 也发现不了（指纹只覆盖 `state`）——**本轮实测发现的新缺口**，处置方式（加字段／随 `WC-CKFMT-001` 的范围外声明一并定案）**待定** | R2 前 |
| 9 | ✅ **已关闭（R0 裁定 + 已执行，提交 `1217c8f`）**：`requires_approval` **删字段**——`policy.json` 三处键、`gate.rs` 字段/自检/摘要、`main.rs` 打印分支、`scripts/test/contract.rs` 矛盾用例**均已移除**；字段本不参与裁决，删除不改变任何判定（`WC-R4-DISP-001` §三 **E-5**） | ✅ **R0 已关闭** |
| 10 | **排版契约的字节级验证面缺失**（§六 样本③之后的缺口行）：须增"独立于本模块 `parse()`"的用例，并在 `WC-UT-001 §三` 显式登记"排版契约无验证面" | S5（`WC-R4-DISP-001` §二 G 组第 2 行） |

## 十二、追溯

| 方向 | 条目 |
|---|---|
| 上游 | `WC-HLD-001-v0.1`、`WC-IC-001-v0.1`、`WC-MODREG-001-v0.1`（**§二 是模块号唯一出处，9 个 `M01`–`M09`**）、`WC-SRS-001-v0.1`、`WC-CR-002`（⛔ **D1 已被否决**，见头部份数口径行） |
| 上游（**格式与需求载体**，本文件**不定义**它们，只引用） | `WC-CKFMT-001`（检查点格式）`docs/S2-设计/WC-CKFMT-001.md`、`WC-PFMT-001-v0.1`（协议/格式）`docs/S2-设计/WC-PFMT-001-v0.1.md`、`WC-LFMT-001-v0.1`（账本格式）`docs/S2-设计/WC-LFMT-001-v0.1.md`、`WC-ONT-001-v0.1`（本体说明/词表身份）`docs/S2-设计/WC-ONT-001-v0.1.md`、`WC-IRS-001-v0.1`（接口**需求**规格说明）`docs/S1-需求/需求-WC-IRS-001-v0.1.md`——**5 份文件 2026-09-27 实测全部实存**（本文件起草期间由并行任务落位）；登记与同号核验见 `WC-IC-001` §七。⚠ 是否已在 `WC-SCMP-001 §4.2` 登记 + `WC-SDP-001` 三处落位，**本文件未核** ⇒ 仍**不声称"格式已受控"** |
| 下游 | `WC-UT-001`（单元测试记录）、`WC-RV-R4-*`（逐模块准出）、`WC-TS-001`（测试用例）、`WC-TR-001`（系统测试报告） |
| 代码 | `src/**`（**实测 14 个文件**：`lib.rs`/`main.rs`/`ledger.rs`/`gate.rs`/`guard.rs`/`ontology.rs`/`readmodel.rs`/`checkpoint.rs`/`channel.rs`/`event.rs`/`error.rs` + `src/gui_projection/{mod,language,visual}.rs`）、`scripts/test/**`（`acceptance.rs`/`contract.rs`/`cli.rs`/`perf.rs`）、`check.sh.new` |

