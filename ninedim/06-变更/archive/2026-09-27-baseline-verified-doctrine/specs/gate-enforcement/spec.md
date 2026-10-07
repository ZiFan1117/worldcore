# Spec Delta

## Purpose

规定"谁可以做什么"这一层对外可核的行为：每一个写动作都要过门禁、被拒的动作不能靠另一类话偷渡、
不可逆动作只允许白名单主体并加摩擦、拒绝本身也要留下说清理由的流水。这一能力服务 `管`，
判据是"一个越界声明能否被拦下，并留下一条人能读懂的流水"。

## ADDED Requirements

### Requirement: 每一个写动作都过门禁

系统 SHALL 在落笔之前对每一条写入做门禁裁决；未在策略中声明的能力 SHALL 被拒绝，
且拒绝 SHALL 作为一条通告落账，而不是仅返回错误。

#### Scenario: 未声明的能力被拒且留下流水

- **WHEN** 以未在策略中声明的能力提交一条 `act`
- **THEN** 提交被拒，账本中新增一条说明该次拒绝的通告
- **证据**：`scripts/test/acceptance.rs::t9_gate_rejects_undeclared_capability_and_records_notice`（`check.sh` 步骤 ③）

### Requirement: `act` 的效果不能靠 `change` 偷渡

系统 SHALL 对 `change` 同样执行写权限裁决；当某一主体无权执行某动作时，
它 SHALL NOT 能通过提交一条 `change` 达到同等效果。

#### Scenario: 越权者用 change 达成静音效果被拒

- **WHEN** 主人先成功写入一条 `change`；随后一个不在白名单的主体提交一条效果相同（静音）
      的 `change`
- **THEN** 第二次提交被拒（错误含"门禁拒绝写入"），状态仍为原值，
      且账本里除那条合法 `change` 外只多一条 `gate.write-rejected` 通告
- **证据**：`scripts/test/contract.rs::c01_change_is_gated_and_cannot_smuggle_an_act`

### Requirement: 不可逆动作只允许白名单主体并加摩擦

系统 SHALL 对声明为不可逆的能力追加摩擦，并只允许策略白名单中的主体执行；
被拒时的错误信息 SHALL 如实说明拒绝理由，不得给出与事实不符的说法。

#### Scenario: 不可逆能力触发摩擦

- **WHEN** 提交一个不可逆能力
- **THEN** 门禁追加摩擦路径被触发
- **证据**：`scripts/test/acceptance.rs::t10_gate_adds_friction_for_irreversible_capability`

#### Scenario: 拒绝流水必须说清它拒绝了什么

- **WHEN** 一个不在允许名单的主体提交带保留前缀的通告
- **THEN** 被拒，且门禁写下的通告里含被拒内容的指纹字段
- **证据**：`scripts/test/contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders`
      与 `c23_gate_notice_says_what_it_refused`

### Requirement: 门禁配置在被管者不可写的域

系统 SHALL 在启动时检查法律与账本的属主与权限；当法律可被他人写、或账本可被他人写时
SHALL 拒绝启动——否则门禁只是一道纸门禁。

#### Scenario: 法律可被他人写时拒绝启动

- **WHEN** 本体文件的权限使他人可写
- **THEN** 世界拒绝启动
- **证据**：`scripts/test/acceptance.rs::t11_world_refuses_to_start_when_law_is_writable_by_others`

#### Scenario: 账本可被他人写时拒绝启动

- **WHEN** 账本文件的权限使他人可写
- **THEN** 世界拒绝启动
- **证据**：`scripts/test/acceptance.rs::t12_world_refuses_start_when_ledger_is_writable_by_others`

#### Scenario: 属主断言能识别错误属主

- **WHEN** 以与预期不符的属主运行属主断言
- **THEN** 断言报错而不是放行
- **证据**：`scripts/test/contract.rs::c10_owner_assertion_detects_wrong_owner`

### Requirement: 运行中的世界不重读策略

系统 SHALL 在启动时装载一次策略；运行期间 SHALL NOT 重新读取策略文件，
使"这一次裁决依据的是哪一版法律"是确定的。

#### Scenario: 运行中改动策略文件不影响本次运行

- **WHEN** 世界运行期间改动策略文件，再提交一个该改动本应影响的动作
- **THEN** 裁决结果与启动时装载的策略一致
- **证据**：`scripts/test/acceptance.rs::t13_running_world_does_not_reread_policy`
