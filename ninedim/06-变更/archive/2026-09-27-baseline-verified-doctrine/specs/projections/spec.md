# Spec Delta

## Purpose

规定"同一份账，各按自己要用的方式读"这一层对外可核的行为：语言投影与视觉投影必须同源、
同源核对必须接在出厂命令上、词表变更必须能被检出、投影只能省略不能添加。
这一能力服务 `显`，判据是"人看到的和 agent 读到的是同一份状态"。

## ADDED Requirements

### Requirement: 两份读法同源且可当场核对

系统 SHALL 提供语言投影（给程序读）与视觉投影（给人看）两份读法；
两者的首行 SHALL 逐字同形，仅 `projection=` 字段不同；系统 SHALL 提供一条出厂命令当场核对同源。

#### Scenario: `project check` 报同源

- **WHEN** 在出厂状态下运行 `world-core project check`
- **THEN** 两份投影的首行逐字一致（仅 `projection=` 不同），命令输出"同源 ✅"
- **证据**：`scripts/test/cli.rs::cli05_project_check_reports_same_source`（`check.sh` 步骤 ④）

#### Scenario: 换词表能被检出

- **WHEN** 在词表变更后比对两份投影
- **THEN** 同源核对能报出不同源
- **证据**：`scripts/test/acceptance.rs::t16_two_projections_are_same_source_and_vocab_change_is_detected`

### Requirement: 语言投影与读模型逐项相等

语言投影 SHALL 由读模型派生；把投影逐行解析出的三元组集合与读模型逐项比对，
两者 SHALL 完全相等（投影只能省略，不能添加状态源里没有的事实）。

#### Scenario: 投影与读模型逐项相等

- **WHEN** 把语言投影逐行解析为 `(主体, 路径, 值)` 三元组，与读模型 `entries()` 比对
- **THEN** 两个集合完全相等
- **证据**：`scripts/test/acceptance.rs::t14_language_projection_matches_read_model`

### Requirement: 视觉投影的排版是可审计契约

视觉投影 SHALL 采用固定排版约定（2 空格缩进为主体行、6 空格缩进加 `路径 = JSON值` 为字段行），
且该约定 SHALL 有独立于渲染实现本身的审计器逐条检验其排版契约。

#### Scenario: 排版审计对变异必报红、对期望样本必常绿

- **WHEN** 用独立审计器检验 3 份字节级期望样本，并施加 12 个变异
- **THEN** 3 份样本全部通过，12 个变异全部报红
- **证据**：`scripts/verify/visual_layout_audit.py --self-test`（`check.sh` 步骤 ⑦）
