# Spec Delta

## Purpose

规定"一本账"对外可核的行为：所有事实落在同一处、只往后加、不回头改；同一本账同时只有一个写者；
历史可被检出被改过，且如实声明检出的边界在哪里。这一能力服务 `存`，是"可复盘"的底座——
它不主张结果正确，只主张"当时写的是什么"可以核。

## ADDED Requirements

### Requirement: 事件按序落账并可跨进程读回

系统 SHALL 把每一条语义事件按 `seq` 升序追加进同一本账，且该账 SHALL 以纯文本 JSON Lines 落盘，
使事件在写入进程退出后仍然可读。

#### Scenario: 追加后按序读回

- **WHEN** 打开世界并连续提交 3 条 `change`
- **THEN** 按序读回得到 3 条事件，内容与提交时逐字段一致
- **证据**：`scripts/test/acceptance.rs::t1_append_then_read_back`（`check.sh` 步骤 ③）

#### Scenario: 事件在新进程里仍存在

- **WHEN** 写入若干事件后结束进程，再以新进程打开同一本账
- **THEN** 先前写入的事件全部可读回，条数与内容不变
- **证据**：`scripts/test/acceptance.rs::t2_events_survive_restart`（`check.sh` 步骤 ③）

### Requirement: 同一本账同时只有一个写者

系统 SHALL 拒绝第二个写者打开同一本账，且拒绝理由 SHALL 说明这是"单写者"约束；
持锁进程正常退出后锁 SHALL 被释放；持有者已不存在的陈旧锁 SHALL 被自动回收。

#### Scenario: 第二个写者被拒且理由说清单写者

- **WHEN** 已经有一个写者打开了某本账，再用同一本体与策略打开同一本账
- **THEN** 打开失败，错误串包含 `Ledger.Locked` 与"单写者"
- **证据**：`scripts/test/contract.rs::c07_second_writer_is_refused`（`check.sh` 步骤 ③b）

#### Scenario: 锁随第一个写者退出而释放

- **WHEN** 释放第一个写者（Drop）后再次打开同一本账
- **THEN** 打开成功
- **证据**：`scripts/test/contract.rs::c07_second_writer_is_refused`

#### Scenario: 陈旧锁被回收且锁文件记录新持有者

- **WHEN** 锁文件内容是一个不存在的 pid（伪造崩溃遗留），再打开该账本
- **THEN** 打开成功，`last_seq` 为 0，且锁文件内容被改写为当前进程 pid
- **证据**：`scripts/test/contract.rs::c08_stale_lock_is_reclaimed`

### Requirement: 残缺的尾部被丢弃，`seq` 空洞拒绝启动

系统 SHALL 在启动读账本时丢弃解析失败的最后一行（只追加模型下唯一可能残缺的位置），
且当 `seq` 出现空洞时 SHALL 拒绝启动，而不是静默接受。

#### Scenario: 半行被丢弃

- **WHEN** 账本最后一行是残缺的 JSON
- **THEN** 该行被丢弃，其余事件正常读回
- **证据**：`scripts/test/acceptance.rs::t3_partial_line_is_discarded`

#### Scenario: `seq` 有空洞时拒绝启动

- **WHEN** 账本中存在 `seq` 不连续的事件
- **THEN** 打开失败并报出 `SeqGap`
- **证据**：`scripts/test/acceptance.rs::t4_seq_gap_refuses_to_start`

### Requirement: 账本文件恒以行边界收尾

系统 SHALL 保证写出的账本文件始终以换行符结束，使"每行一条事件"这一分帧约定在任何时刻都成立。

#### Scenario: 每次写入后文件都以换行收尾

- **WHEN** 任意次提交之后检查账本文件的最后一个字节
- **THEN** 最后一个字节是换行符，不存在"半行挂在末尾"的中间态
- **证据**：`scripts/test/contract.rs::c22_file_always_ends_on_a_line_boundary`

### Requirement: 摘要链检出局部篡改，并如实声明其边界

系统 SHALL 为每条写出的事件带上摘要链，并把链的核验接在**启动路径**上：
账本被局部改写、重排或插入时 SHALL 拒绝启动。同时系统 SHALL 明确声明：
无密钥的链**不能**检出"整文件重写并重算链"，此边界 SHALL 被测试固定，不得被表述为"防篡改"。

#### Scenario: 改写、重排、插入中间事件均被检出

- **WHEN** 对一条合法链分别做三种操作：改中间某条的内容、交换相邻两条、按攻击者算好的链插入一条
- **THEN** 三种情形都报 `ChainMismatch`
- **证据**：`scripts/test/contract.rs::c16_chain_detects_local_tampering`

#### Scenario: 无链与混用被显式区分，不得静默通过

- **WHEN** 对一份完全无链的账本、以及一份部分带链的账本做核验
- **THEN** 无链报 `NoChain` 并说明"不可检出"；混用报 `MixedChain` 并说明"比无链更危险"
- **证据**：`scripts/test/contract.rs::c17_chain_distinguishes_absent_and_mixed`

#### Scenario: 篡改一行即拒绝启动

- **WHEN** 直接改写账本中间一行的 `body.after` 而保留原 `chain`，再打开世界
- **THEN** 打开失败，错误串包含 `ChainMismatch`，且理由提到"唯一真相"
- **证据**：`scripts/test/contract.rs::c20_startup_refuses_a_tampered_ledger`

#### Scenario: 整本重写按设计检不出（边界固定）

- **WHEN** 攻击者改写一条事件的值，并把链整条重算（知道算法与创世种子）
- **THEN** 核验**通过**——这是无密钥链的极限，本断言证明的是边界而不是实现缺陷；
      同时不重算链的局部篡改仍必须被检出
- **证据**：`scripts/test/contract.rs::c18_chain_cannot_detect_a_full_rewrite`

#### Scenario: 链状态位如实反映账本现实

- **WHEN** 分别对"新写入的带链账本""空账本""手工造的无链账本"读取链状态
- **THEN** 依次为 true / false / false，且无链的旧账本仍能打开（v1 兼容）
- **证据**：`scripts/test/contract.rs::c21_is_chained_reflects_reality`

### Requirement: 回滚是追加补偿事件，不是改写历史

系统 SHALL 以"追加一条补偿事件"的方式实现回滚，SHALL NOT 修改或删除已经写下的事件。

#### Scenario: 回滚后历史里两条都在

- **WHEN** 提交一条 `change` 后对其执行回滚
- **THEN** 账本中同时存在原事件与补偿事件，没有任何一条被改写或删除
- **证据**：`scripts/test/acceptance.rs::t17_rollback_is_an_appended_compensating_event`
