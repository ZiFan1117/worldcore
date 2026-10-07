# Spec Delta

## Purpose

规定"读法可以有若干份，但说法只有一份"这一层对外可核的行为：读模型必须能由账本百分之百重算、
检查点只是缓存可以随时丢弃。这一能力是"一个真相"这条纪律的唯一自动化检验所在。

## ADDED Requirements

### Requirement: 读模型是可丢弃的缓存

"现在是什么样" SHALL 由账本重算得出，SHALL NOT 作为与账本并行的第二份原件存在。
删掉读模型（及其持久形态）之后 SHALL 能从账本重算出完全一致的结果。

#### Scenario: 删掉读模型后重算结果一致

- **WHEN** 记录当前读模型，删除其持久形态，再由账本重算
- **THEN** 重算结果与删除前逐项一致
- **证据**：`scripts/test/acceptance.rs::t7_read_model_is_disposable_and_reproducible`（`check.sh` 步骤 ③）

#### Scenario: 坏账本不得产出"看起来正常"的读模型

- **WHEN** 账本内容损坏
- **THEN** 读模型拒绝产出，而不是给出部分结果
- **证据**：`scripts/test/acceptance.rs::t8_read_model_refuses_broken_ledger`

### Requirement: 增量折叠等价于全量折叠

系统 SHALL 保证"逐条增量应用"与"从头全量折叠"得到同一个结果，
否则读模型就成了一本会漂移的第二本账。

#### Scenario: 增量与全量结果相同

- **WHEN** 对同一批事件分别做增量应用与全量折叠
- **THEN** 两者结果相同
- **证据**：`scripts/test/contract.rs::c06_incremental_apply_equals_full_fold`（`check.sh` 步骤 ③b）

### Requirement: 检查点是缓存，可丢弃且必须自洽

检查点 SHALL 只作为重放的加速形态存在；它 SHALL 可被丢弃而不影响正确性；
坏检查点 SHALL 被拒绝而不是被静默采用。

#### Scenario: 检查点可丢弃

- **WHEN** 生成检查点后再丢弃它，由账本重新重放
- **THEN** 结果与使用检查点时一致
- **证据**：`scripts/test/contract.rs::c12_checkpoint_is_a_cache_and_disposable`

#### Scenario: 坏检查点被拒

- **WHEN** 检查点内容被破坏
- **THEN** 被拒绝
- **证据**：`scripts/test/contract.rs::c13_bad_checkpoints_are_refused`
