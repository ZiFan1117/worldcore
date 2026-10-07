# ontology-extensibility Specification

## Purpose
规定"本体怎么长大而不把核心改坏"：出厂本体是极小核心，扩展只能经命名空间加入，核心字段的含义永不因扩展而变；信封里的 `trace` 作为因果字段保留并可在入口写入。这一层今天只有草稿、没有实现，本 delta 把它建档。

## Requirements

### Requirement: REQ-F-030 本体：极小核心 ＋ 命名空间扩展

本体 SHALL 采用**极小核心 ＋ 命名空间扩展**的结构：出厂本体只定义三家族信封与最小概念集；扩展项 SHALL 落在命名空间内，**SHALL NOT 与核心字段重名**；换一份**只加扩展**的本体，同一账本的折叠结果 SHALL 不变。
（核心字段 = `envelope.required` ∪ `envelope.optional`；重名在**装载期**即拒启并点名撞上的那一项——
重名是"法律自相矛盾"，与 `load` 的其余错误同一处置。）

往上长的方式**只有加法**，本条 SHALL 按此**双向**声明：① 核心之外 SHALL 只经命名空间**加**（已在上段）；
② **核心之内 SHALL NOT 取交集、SHALL NOT 做删减**——即**任何扩展都不得改写、收缩或重定义核心字段的含义**。
（这一句此前**只有正向那一半**落进规格：正向＝"扩展走命名空间"，反向＝"核心不许被改"**没有明文**；
它的可核形态就是上段的"重名即拒 ＋ 只加扩展则折叠逐字节不变"两条 Scenario——**含义被改，折叠必变**。）

#### Scenario: 扩展与核心字段重名必须被拒

- **WHEN** 造一份"扩展项与核心字段重名"（例如扩展里再叫 `body`）的本体
- **THEN** 加载**被拒**（错误码 `ext.world.Ontology.CoreCollision`）并指出重名的那一项；
  **对照**：只加扩展的本体（新家族 ＋ 同名下的新概念）SHALL 照常加载
- **证据**：`scripts/test/ontology_ext.rs::x01_an_extension_item_colliding_with_a_core_field_is_refused_at_load`

#### Scenario: 换一份只加扩展的本体，同一账本的折叠结果不变

- **WHEN** 用同一份账本，分别以出厂本体与"只加扩展"的本体读（过法律 + 折叠）
- **THEN** 两次折叠结果**逐字节相同**，且词表身份**必须已变**（否则"换本体"没发生，相等是同义反复）；
  **对照**：把**核心**语义改掉的本体读同一条旧事件 SHALL 失败
- **证据**：`scripts/test/ontology_ext.rs::x02_a_pure_extension_keeps_the_fold_byte_identical`

### Requirement: REQ-F-031 `trace`（信封因果字段）

信封的 `trace` SHALL 保留为需求：一条事件 SHALL 能声明"它由哪一条事件引起"，且该字段 SHALL 能从**写入入口**给出。
（**2026-09-28 起端到端可执行验证面已在**：库侧 `World::commit_requested` 一直有 `trace`；命令行这一级由
`append … [--trace <id>] [--flag <名>]...` 补上——原文"`World::commit` 与 CLI `append` 都没有 `trace` 参数"**已过期**。）

#### Scenario: 带 trace 的事件可写可读

- **WHEN** 从写入入口提交一条带 `trace` 的事件，再读回
- **THEN** `trace` 原样落账且可读回；`trace` 指向一条不存在的事件时，行为有明文规定（接受或拒绝，二者择一并写死）
- **证据**：`scripts/test/trace_notice.rs::f61_append_with_trace_lands_and_reads_back_byte_for_byte`（逐字节读回）、
  `::f62`（不带 ⇒ **不写 `trace` 键**）、`::f63`（空串按未给）、`::f64`（结果经账本追回意图）、
  `::f65`（**悬空 `id` 仍被接受**——判据 (4) 按"会失败的检查"写：实现若开始拒绝，本条即红）、`::f66`（缺值即用法错误 rc=1 且不落笔）
