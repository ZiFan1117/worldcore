# ledger-integrity Specification

## Purpose
规定"一本账"对外可核的行为：所有事实落在同一处、只往后加、不回头改；同一本账同时只有一个写者；
历史可被检出被改过，且如实声明检出的边界在哪里。这一能力服务 `存`，是"可复盘"的底座——
它不主张结果正确，只主张"当时写的是什么"可以核。

## Requirements

### Requirement: 事件按序落账并可跨进程读回

系统 SHALL 把每一条语义事件按 `seq` 升序追加进同一本账，且该账 SHALL 以纯文本 JSON Lines 落盘，
使事件在写入进程退出后仍然可读。

**跨进程**读回 SHALL 由**独立进程**的证据承担，
SHALL NOT 以"同进程内 drop 后 reopen"充当跨进程证据。

#### Scenario: 追加后按序读回

- **WHEN** 打开世界并连续提交 3 条 `change`
- **THEN** 按序读回得到 3 条事件，`seq` 从 1 连续递增，信封带词表版本，各条 `kind` 与 `body.before` 正确
- **证据**：`tests/acceptance.rs::t1_append_then_read_back`（由 `world-core/check.sh` 第 ③ 步执行）
      —— **⚠ 本证据今天只到"字段抽样比对"**：`actor`／`id`／`at`／`flags`／`body.subject`／
      `body.path`／`body.after` 未被断言（`world-core/tests/acceptance.rs:69-80`）
      ⇒ "逐字段一致"要成立 ⇒ 需补断言（列进 tasks）。

#### Scenario: 事件在新进程里仍存在

- **WHEN** 写入若干事件后结束写入方，再打开同一本账
- **THEN** 先前写入的事件全部可读回，条数与内容不变
- **证据**：`tests/acceptance.rs::t2_events_survive_restart`（由 `world-core/check.sh` 第 ③ 步执行）
      —— **⚠ 本证据是"同进程 drop + reopen"，不是"新进程"**（`world-core/tests/acceptance.rs:85-104`）；
      "新进程"这一层由 `world-core/tools/s1_sys_probe2.sh` 的 `TC-070` 承担
      （由 `world-core/check.sh` **第 ⑥ 步**执行——**写步骤名、不写行号**：行号会烂）。

### Requirement: 同一本账同时只有一个写者

系统 SHALL 拒绝第二个写者打开同一本账，且拒绝理由 SHALL 说明这是"单写者"约束；
持锁进程正常退出后锁 SHALL 被释放；持有者已不存在的陈旧锁 SHALL 被自动回收。

已知前提 SHALL 被如实声明：锁文件**只记录持有者的 pid 号**，其"是否存活"的判据是
`/proc/<pid>` 是否存在 ⇒ 本机制的正确性**依赖**：同机、同一 PID 命名空间、`/proc` 可读。
在共享存储或独立 PID 命名空间下，存活写者的锁会被当作陈旧锁回收，从而出现两个写者；
反之 pid 号被复用时持有者已不存在却不会被回收（假锁死）。
此边界 SHALL NOT 被读成"锁在所有形态下成立"。

#### Scenario: 第二个写者被拒且理由说清单写者

- **WHEN** 已经有一个写者打开了某本账，再用同一本体与策略打开同一本账
- **THEN** 打开失败，错误串包含 `Ledger.Locked` 与"单写者"
- **证据**：`tests/contract.rs::c07_second_writer_is_refused`（由 `world-core/check.sh` 第 ③b 步执行）

#### Scenario: 锁随第一个写者退出而释放

- **WHEN** 释放第一个写者（Drop）后再次打开同一本账
- **THEN** 打开成功
- **证据**：`tests/contract.rs::c07_second_writer_is_refused`

#### Scenario: 陈旧锁被回收且锁文件记录新持有者

- **WHEN** 锁文件内容是一个不存在的 pid（伪造崩溃遗留），再打开该账本
- **THEN** 打开成功，`last_seq` 为 0，且锁文件内容被改写为当前进程 pid
- **证据**：`tests/contract.rs::c08_stale_lock_is_reclaimed`

### Requirement: 残缺的尾部被丢弃，`seq` 空洞拒绝启动

系统 SHALL 在启动读账本时把文件**截到最后一个换行符**（只追加模型下唯一可能残缺的位置），
且当 `seq` 出现空洞时 SHALL 拒绝启动，而不是静默接受。

**边界 SHALL 被如实声明**：本判据是"**截到最后一个换行**"，**不是**"丢弃解析失败的最后一行"。
一条内容完整、合法的 JSON 事件，只要其末尾换行缺失，就会被一并截掉并在下次写入时被物理删除、
其 `seq` 被复用。此边界 SHALL NOT 被读成"只丢残缺的半行"。

#### Scenario: 半行被丢弃

- **WHEN** 账本最后一行是残缺的 JSON（或末尾换行缺失）
- **THEN** 该行被截掉，其余事件正常读回
- **证据**：`tests/acceptance.rs::t3_partial_line_is_discarded`
      —— **⚠ 实测判据是"截到最后一个 `\n`"**（`world-core/src/ledger/mod.rs:276-279`），
      **不看该行能否解析** ⇒ "完整事件因末尾换行缺失被静默删除"这一形态 ⇒ 需补断言（列进 tasks）。

#### Scenario: `seq` 有空洞时拒绝启动

- **WHEN** 账本中存在 `seq` 不连续的事件
- **THEN** 打开失败并报出 `SeqGap`
- **证据**：`tests/acceptance.rs::t4_seq_gap_refuses_to_start`
      —— **⚠ 本条在生产路径上由账本层更早拦截**：`world-core/src/ledger/mod.rs:304` 逐字
      `if seq != last + 1 {` ⇒ 本断言**不构成**端到端证明（防线冗余，非缺陷）。

### Requirement: 账本文件恒以行边界收尾

系统 SHALL 保证写出的账本文件始终以换行符结束，
使"每行一条事件"这一分帧约定在任何时刻都成立。

#### Scenario: 每次写入后文件都以换行收尾

- **WHEN** 任意次提交之后检查账本文件的最后一个字节
- **THEN** 最后一个字节是换行符，不存在"半行挂在末尾"的中间态
- **证据**：`tests/contract.rs::c22_file_always_ends_on_a_line_boundary`
      （由 **`world-core/check.sh`** 第 ③b 步执行——仓根另有一个同名 `check.sh`，它不涉及 `world-core`）

### Requirement: 摘要链检出局部篡改，并如实声明其边界

系统 SHALL 为每条写出的事件带上摘要链，并把链的核验接在**启动路径**上：
账本被局部改写、重排或插入时 SHALL 拒绝启动。

系统 SHALL 明确声明第一条边界：无密钥的链**不能**检出"整文件重写并重算链"，
此边界 SHALL 被测试固定，不得被表述为"防篡改"。

系统 SHALL 另外明确声明第二条边界：**无链（v1）账本不具备平滑升级路径**。
`append` **无条件**把 `chain` 插进事件，而 `load_chain` 对无链账本返回 `false` 后
**不改变写入行为** ⇒ 无链账本上做**一次合法 `append`** 即产生"部分有链、部分没有"的账本，
下次打开判 `MixedChain` 并拒绝使用。此边界 SHALL NOT 被表述为"v1 兼容"或"可平滑升级"。

#### Scenario: 改写、重排、插入中间事件均被检出

- **WHEN** 对一条合法链分别做三种操作：改中间某条的内容、交换相邻两条、按攻击者算好的链插入一条
- **THEN** 三种情形都报 `ChainMismatch`
- **证据**：`tests/contract.rs::c16_chain_detects_local_tampering`

#### Scenario: 无链与混用被显式区分，不得静默通过

- **WHEN** 对一份完全无链的账本、以及一份部分带链的账本做核验
- **THEN** 无链报 `NoChain` 并说明"不可检出"；混用报 `MixedChain` 并说明"比无链更危险"
- **证据**：`tests/contract.rs::c17_chain_distinguishes_absent_and_mixed`

#### Scenario: 篡改一行即拒绝启动

- **WHEN** 直接改写账本中间一行的 `body.after` 而保留原 `chain`，再打开世界
- **THEN** 打开失败，错误串包含 `ChainMismatch`，且理由提到"唯一真相"
- **证据**：`tests/contract.rs::c20_startup_refuses_a_tampered_ledger`

#### Scenario: 整本重写按设计检不出（边界固定）

- **WHEN** 攻击者改写一条事件的值，并把链整条重算（知道算法与创世种子）
- **THEN** 核验**通过**——这是无密钥链的极限，本断言证明的是边界而不是实现缺陷；
      同时不重算链的局部篡改仍必须被检出
- **证据**：`tests/contract.rs::c18_chain_cannot_detect_a_full_rewrite`

#### Scenario: 链状态位如实反映账本现实

- **WHEN** 分别对"新写入的带链账本""空账本""手工造的无链账本"读取链状态
- **THEN** 依次为 true / false / false，且**无链账本可以被打开**
- **证据**：`tests/contract.rs::c21_is_chained_reflects_reality`
      —— **⚠ 原文括注"（v1 兼容）"已删**：本证据只到"能打开"为止
      （`world-core/tests/contract.rs:1026`），它**不**断言"打开后还能正常写下去"；
      该边界见下一条 `## ADDED` 里的 `K-3` 条文。

### Requirement: 回滚是追加补偿事件，不是改写历史

系统 SHALL 以"追加一条补偿事件"的方式实现回滚，
SHALL NOT 修改或删除已经写下的事件。

系统 SHALL NOT 声称提供"回滚操作"或"回滚子命令"：v1 没有回滚 API，
回滚由调用方**再提交一条普通 `change`** 完成。

#### Scenario: 回滚后历史里两条都在

- **WHEN** 提交一条 `change` 后对其执行回滚（即再提交一条互换新旧值的 `change`）
- **THEN** 账本中同时存在原事件与补偿事件，没有任何一条被改写或删除，且状态回到原处
- **证据**：`tests/acceptance.rs::t17_rollback_is_an_appended_compensating_event`
      —— **⚠ 回滚动作由该测试自己提交，不是系统命令**；载体侧的"撤销"是另一件事：
      `world-core/src/carrier/mod.rs:32` 逐字
      `| **载体撤销**（本模块） | 文件系统的字节 | **不是世界状态**；只作工程兜底，**不得**用于满足"坏了能回滚" |`。

### Requirement: 无链账本的升级路径边界

系统 SHALL 保证：在**无链（v1）账本**上做一次合法 `append` 之后，
该账本 SHALL 仍可被打开——即"整本无链"是一个**稳定态**，
或者启动时即拒写并给出迁移指引。
系统 SHALL NOT 使"无链账本 → 一次合法 `append` → 下次打开被 `MixedChain` 拒绝"成为可能。

在此之前，系统 SHALL 在规格里**不声称**无链账本可平滑升级：
"v1 兼容"这一说法 SHALL 被限定为"**只读兼容**"。
此边界 SHALL 被测试固定，SHALL NOT 被表述为实现缺陷或注意事项。

#### Scenario: 无链账本上一次合法 append 后仍可打开（升级路径不自锁）

- **WHEN** 对一份无链（v1）账本做一次合法 `append`，再重新打开该账本
- **THEN** 打开成功，`last_seq` 为 2，且账本未变成"部分有链、部分没有"
- **证据（★ 2026-09-28 订正：原写「本条尚无断言」——**那句与实物不符**）**：**案例在册、但被 `#[ignore]` 钉住**——`world-core/tests/contract.rs:1615` 的 `c29_k3_chainless_ledger_survives_one_legal_append`，其上一行逐字`#[ignore = "K-3 未修（src/ledger/mod.rs:146 的 chained 只写不读）：无链账本 append 一条后被判 MixedChain、世界拒启；修复落地后去掉本 ignore 即应转绿"]` ⇒ **它今天不是"没有断言"，是"有一条钉住缺口的、去掉 ignore 就该红的断言"**。本条是 K-3 的**修复判据**，实现侧今天为 `world-core/src/ledger/mod.rs`:506
      （chained 只读不用）与 `world-core/src/lib.rs`:105（load_chain()?; 丢弃返回值）。
      **⚠ 且修复本身不属本 change**：本 change 只交规格文本，`world-core/` 一行不改
      （`design.md` §排除清单第 2 条）；断言先写、先证红，与修复同批另立 change。

#### Scenario: v1 兼容只到只读为止（边界固定）

- **WHEN** 在修复落地之前，对一份无链账本做一次合法 `append` 后再打开
- **THEN** 打开失败并报 `MixedChain` —— 本断言证明的是**边界的真实形状**，不是实现缺陷；
      它把"v1 兼容"限定为"**只读兼容**"，SHALL NOT 被读成"可平滑升级"
- **证据**：`world-core/tests/contract.rs:1648` 的 **`c30_k3_boundary_chainless_ledger_plus_one_append_reports_mixed_chain`**（**live**，其上一行是 `#[test]`；其头注逐字「判据不止比错误串：还要**逐行看账本文件**，确认「半链」这个机制成立」）（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**）——缺陷出处为 `world-core/docs/S0-立项/WC-SCMP-001-v0.1.md`:2537（K-3）与 :2541（后果链）。

### Requirement: 承诺与证据的绑定强度

本规格的每一条 Scenario 末尾的证据行 SHALL 指向**真实存在**的测试函数。

系统 SHALL 明确声明的边界：**证据行只到"测试名存在"这一级**，
它 SHALL NOT 被读成"该测试断言的正是本 Scenario 那句话"。
后者的判定 SHALL 由评审承担并留下签字，SHALL NOT 由机械门禁冒充。

#### Scenario: 证据行的存在性可机核、内容相符性不可机核

- **WHEN** 核对某条 Scenario 的证据行所指向的测试函数是否存在
- **THEN** 可机械判定；而当该测试函数的断言与 Scenario 说的不是同一件事时，
      **机械门禁不会变红**（这是本边界的定义）
- **证据**：`world-core/tools/spec_bridge.py`
      —— 判据②（`world-core/tools/spec_bridge.py::j2_evidence`）全称判定证据行指向的函数名是否真实存在，
      其反例在 `world-core/tools/spec_bridge.py --self-test` 的反例②（把证据指向 `::no_such_fn` ⇒ 必红）；
      而它**不读断言文本**，故"相符性"无机械判据。另一半边界由
      `world-core/tools/doc_integrity.py` 的受控清单里 `openspec` 零命中承担。

### Requirement: 〔无号·待流程侧增补〕这本账的能力上限（三句，逐句判）

这一层 SHALL 按三句上限**逐句**对外声明它管到什么为止：**能消灭"查无此申请"**；**消灭不了"查无此后果"**；**消灭不了"查无此人可担此责"**。三句 SHALL 各自可判（各有一个能被检验的标的），且 SHALL NOT 被合并成一句笼统的"可追责"。
（书 §5.1 逐字：「把『没有记录』变成『有记录』，**能消灭『查无此申请』，消灭不了『查无此后果』，也消灭不了『查无此人可担此责』**。这三句话是这一层的天花板，逐句判。」）

#### Scenario: 三句各自可判，且不许互相冒充

- **WHEN** 逐句核这三条上限的标的：① 唯一写入路径 ＋ 只追加账本能否答出"谁在何时改了哪个字段、前值是什么、因为哪一条"；② **世界外面**产生的效果能否被世界里再写一条记录撤回；③ 出事之后能否指出一个**可担此责的人**
- **THEN** ①的标的**存在且可核**；②的标的**今天不存在**（没有第二本账、没有对账表）；③的标的**今天不存在**（没有归责与损失机制）；三句**各判各的**，任何一句为绿 SHALL NOT 被用来支持另一句
- **证据**：三句标的**逐句核过**（2026-09-28 现取）——① 的编译期证据在 `world-core/src/lib.rs` 的 `compile_fail` 文档测试；②③ 的"今天不存在"由源码零命中证明。命令与读数逐句列在下面：
  - **①**（唯一写入路径 ＋ 只追加账本能否答出"谁在何时改了哪个字段、前值是什么、因为哪一条"）——**标的今天存在且可核**：
    `world-core/src/lib.rs:117` 起是一段 **`compile_fail` 文档测试**（`/// \`\`\`compile_fail`，`:123` 收尾），它把"**唯一写入口**"钉成**编译期事实**：
    绕开 `World::commit*` 直接造事件**编译不过**。取数：`cargo test --locked --doc` ⇒ `test src/lib.rs - World (line 117) - compile fail ... ok`（VM 实测，`rc=0`）。
  - **②**（**世界外面**产生的效果能否被世界里再写一条记录撤回）——**标的今天不存在**：**源码零命中**——
    `git grep -n -E "第二本账|对账表|reconcil" -- world-core/src` ⇒ **rc=1（0 处）**。
    （规格树里 3 处命中**都不是"要求实现"**，且**三处都在 `read-model`**（★ 2026-09-28 评审席纠正：原写 `projections`，而 `openspec/specs/projections/spec.md` **一句都没有**）：`openspec/changes/archive/2026-09-27-baseline-verified-doctrine/specs/read-model/spec.md:30`／`openspec/changes/archive/2026-09-28-fc-2026-002-spec-revisions/specs/read-model/spec.md:38`／`openspec/specs/read-model/spec.md:46` 逐字「否则读模型就成了一本会漂移的第二本账」（**原文无强调，此处照抄**）是**禁止**第二本账，
    方向与②**同向**、不构成②的落点。）
  - **③**（出事之后能否指出一个**可担此责的人**）——**标的今天不存在**：**源码零命中**——
    `git grep -n -E "归责|损失机制|liabilit" -- world-core/src` ⇒ **rc=1（0 处）**。
    （规格树里 2 处命中是**对照句**：逐字「门禁、审计与归责三件事同时失效，因此这一条是 `管` 的前置条件」（**原文无强调，此处照抄**）——它说的是"三件事同时失效会怎样"，**不是**一套归责机制的落点。）
- **不许互相支持（本条的判据本体，不许被读成修辞）**：①为绿**SHALL NOT**被用来支持②或③。**可核的理由**：①的标的是**账本内部**的可答性（"有没有记录"），
  ②的标的是**世界外面**的效果可否被撤回，③的标的是**人**的可归责性——**三者的标的物各不相同**，故①的编译期事实**在逻辑上推不出**②③。
  **反例形态**（会失败的检查）：若哪天有人拿①去论证"所以我们能追责"，本条判据即应交由评审席按"冒充"处置（与 `REQ-F-029` 的"未知旗标／未知家族不许互相冒充"同一形状）。

> **外部印证**（不构成本要求的一部分，只作旁证）：`D:\Code\04-research-ontology\Palantir本体-总览与构件.md` §9.3 第 6 条官方边界逐字「**撤销 ≠ 回滚**：只能撤最新一次编辑，**不撤副作用**」——与第②句同向。

### Requirement: 〔无号·待流程侧增补〕一个说法要回答的七个问题（同一份记录上的七个位置）

写下一件事 SHALL 能回答七个问题：**① 谁做的；② 对什么做的；③ 从什么变成什么；④ 因为什么才发生；⑤ 排在第几位；⑥ 谁允许的；⑦ 什么单位。**

三条口径 SHALL 同时成立（**逐条都是判据，不是修辞**）：
1. **判据是读的人的**：一条记录写得全不全，判据是"**别人能不能不问当事人就读出来**"——"写的人自己是否清楚"**不作数**；
2. **七个位置在**同一份记录上**，不是七份材料**：它们 SHALL 一次答在同一处，SHALL NOT 分散在不同件里让读者自己去凑；
3. **一处缺格即认缺**：SHALL NOT 用"其余六格都在"来含混——缺格要**如实标出来**。

#### Scenario: 逐格核七个位置（哪几格有位置、哪几格没有）

- **WHEN** 对着一条真实记录逐格核这七个位置
- **THEN** 每格**要么**给出"位置在哪、由什么钉住"**要么**如实写"今天没有位置"，SHALL NOT 把缺格写成有格
- **逐格现状（2026-09-28 执行者现取；与书 §2.9 `:361` 自述的格位现状逐条对齐）**：
  | # | 问题 | 落点 | 现状 |
  |---|---|---|---|
  | ① | 谁做的 | 信封 `actor` | **有位置**：`tests/acceptance.rs::t1` 断言三条事件的 `actor` 且**要求它们互不相同**（防"actor 是常量"） |
  | ② | 对什么做的 | 信纸 `body.subject`／`body.path` | **有位置**：同上，`t1` 逐条断言 |
  | ③ | 从什么变成什么 | 信纸 `body.before`／`body.after` | **有位置**：`t1` 断言 `after`；`before` 由 `change` 家族的信封形状钉住 |
  | ④ | 因为什么才发生 | 信封 `trace` | **有位置、但今天不校验**（与书 §2.9 自述一致）：`tests/trace_notice.rs::f61`–`f66`；其中 `f65` 按"**会失败的检查**"写——实现若开始拒绝悬空 `id`，该条即红 |
  | ⑤ | 排在第几位 | 信封 `seq` | **有位置**（★ 2026-09-28 补：原写"由 `tests/contract.rs` 的账本域用例钉住"——**只给"域"、不点名**，与 ①–④⑥ 的写法不一致，调查员把它记为弱处）：`tests/acceptance.rs::t4_seq_gap_refuses_to_start`（缺号 ⇒ 拒启）；`tests/contract.rs` 的 `c15`（`:926` 逐字断言 `ext.world.Ledger.SeqGap`）；`c22_file_always_ends_on_a_line_boundary`（行边界）；`c32_last_line_without_trailing_newline_is_cut_and_seq_is_reused`（末行半行被截 ＋ `seq` 复用）。**实现侧**：`src/ledger/mod.rs` 的 `if seq != last + 1` |
  | ⑥ | 谁允许的 | 门禁裁决的流水（`gate.*` 旗标与通告） | **有位置、但今天不校验**（与书 §2.9 自述一致）：`tests/cli.rs::cli09` 断言不可逆动作**必带** `gate.friction:<等级>`；`tests/trace_notice.rs::f71` 断言被拒的通告**留流水** |
  | ⑦ | 什么单位 | **无字段** | **今天没有位置可填**（与书 §2.9 自述一致）——**如实标缺格，不许含糊成"已答"** |
- **并且**（书 §2.9 `:363` 的边界，**照抄不并轨**）：这七个问题**另有一套"八问"的问法**，两套**名目不同、条数不同、合成不了一套**，**并轨这件事今天还没有结论** ⇒ 本要求 SHALL NOT 被读成"已经把两套并成一套"。
- **证据**：`world-core/tests/acceptance.rs`（`t1` 的逐格断言）、`world-core/tests/trace_notice.rs`（第 ④⑥ 格）、`world-core/tests/cli.rs`（第 ⑥ 格）；缺格的如实登记见 `openspec/changes/archive/2026-09-28-cover-unimplemented-capabilities/tasks.md` 第 11 组。
