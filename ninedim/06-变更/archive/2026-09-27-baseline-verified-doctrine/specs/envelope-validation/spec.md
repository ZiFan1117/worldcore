# Spec Delta

## Purpose

规定"一件事写下来只有一种形式"这一层对外可核的行为：信封的必填字段被逐字段强制、
三类话之外一律被拒、法律（本体与策略）损坏时拒绝启动而不是带病运行。
这一能力服务"只固定意思的形式"这条边界——它校验形状，不校验含义。

## ADDED Requirements

### Requirement: 信封的必填字段被逐字段强制

系统 SHALL 对每一条写入事件逐字段校验信封必填项 `world` / `kind` / `id` / `seq` / `at` /
`actor` / `flags` / `body`；任一字段缺失时 SHALL 拒绝该事件，且错误信息 SHALL 报出**缺失的是哪个字段**。

#### Scenario: 八个必填字段逐字段被拦

- **WHEN** 依次构造 8 条事件，每条分别删掉一个必填字段
- **THEN** 每条都被校验拒绝，且错误信息里出现被删掉的字段名
- **证据**：`scripts/test/contract.rs::c02_every_required_envelope_field_is_enforced`（`check.sh` 步骤 ③b）

### Requirement: 三类话之外一律被拒

系统 SHALL 只接受本体声明的三个家族（变更 / 请求与结果 / 通告）；出现未知家族时 SHALL 拒绝，
SHALL NOT 猜测其含义。

#### Scenario: 不认识的事件家族被拒

- **WHEN** 以本体未声明的 `kind` 提交事件
- **THEN** 提交失败，状态未被改动，且不落笔该事件
- **证据**：`scripts/test/acceptance.rs::t5_law_rejects_and_does_not_write`（`check.sh` 步骤 ③）

### Requirement: 法律损坏或指向别处时拒绝启动

本体与门禁策略 SHALL 在世界打开时装载并校验；文件缺失、家族为空、字段形状非法时 SHALL
拒绝启动；法律文件是**符号链接**时 SHALL 拒绝启动，以免"检查的"与"真正读的"不是同一个文件。

#### Scenario: 坏本体拒绝启动

- **WHEN** 本体文件内容损坏
- **THEN** 打开失败，不打印 `READY`
- **证据**：`scripts/test/acceptance.rs::t6_bad_ontology_refuses_to_start`

#### Scenario: 本体缺失与家族为空被拒

- **WHEN** 本体文件不存在，或 `families` 为空
- **THEN** 装载失败
- **证据**：`scripts/test/contract.rs::c04_ontology_load_rejects_missing_file_and_empty_families`

#### Scenario: 策略的每一类畸形形状都被拒

- **WHEN** 以 5 类畸形形状分别装载门禁策略
- **THEN** 每一类都被拒，不存在"静默接受一个畸形策略"的路径
- **证据**：`scripts/test/contract.rs::c03_policy_load_rejects_every_malformed_shape`

#### Scenario: 策略为符号链接时拒绝启动，而真实文件不被误拒

- **WHEN** 以指向别处的软链作为策略路径打开世界；对照组用真实文件
- **THEN** 软链被拒且错误信息含"符号链接"；真实文件正常打开
- **证据**：`scripts/test/contract.rs::c09_symlinked_law_is_refused`

### Requirement: 事件身份在进程内唯一

系统 SHALL 保证同一进程内分配的事件 `id` 不重复。

#### Scenario: 连续提交的事件 id 各不相同

- **WHEN** 在同一进程内连续提交多条事件
- **THEN** 所有事件的 `id` 互不相同
- **证据**：`scripts/test/contract.rs::c05_event_ids_are_unique_within_a_process`

### Requirement: 错误携带机器可读的错误码

系统 SHALL 在失败路径上给出机器可读的错误码（如 `ext.world.*`），使调用方按码判定，
SHALL NOT 要求调用方去匹配中文散文措辞。

#### Scenario: 各类失败路径的错误码可枚举

- **WHEN** 触发法律、门禁、账本、读模型四类失败路径
- **THEN** 每条错误都带稳定的错误码
- **证据**：`scripts/test/contract.rs::c15_errors_carry_machine_readable_codes`
