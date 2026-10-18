# ontology-extensibility Specification

## Purpose
规定"本体怎么长大而不把核心改坏"：出厂本体是极小核心，扩展只能经命名空间加入，核心字段的含义永不因扩展而变；信封里的 `trace` 作为因果字段保留并可在入口写入。这一层今天只有草稿、没有实现，本 delta 把它建档。

## 这一件说的是七格里哪几格

> **七格**（逐字出处＝本册 `ledger-integrity.spec.md` 的「〔无号·待流程侧增补〕一个说法要回答的七个问题」一条）：
> **① 谁做的；② 对什么做的；③ 从什么变成什么；④ 因为什么才发生；⑤ 排在第几位；⑥ 谁允许的；⑦ 什么单位。**
> **本件只列它真正管的格**；七格的**全表与逐格现状**在 `ledger-integrity.spec.md`，本件**不复述**（一个事实只有一个权威载体）。
> **★ 措辞口径**：第三栏一律写「**照形状取自**」，**不写"符合"**——且 `IAO-lsw报告.html` 用的是 **BFO 1.1** 的 IRI
> （`ifomis.org/bfo/1.1/…`），与本轮锚定的 **BFO 2020／ISO 21838-2 不是同一版** ⇒ **只借词与形状，不借号**。

| 格 | 本件里现在的说法（逐字） | **照形状取自**（出处：件 ＋ 行） | 我们今天的落点 |
|---|---|---|---|
| **发生了本身** | 「新家族／新字段的引入 SHALL NOT 让旧事件读不懂」 | **`Process`** —— `IAO-lsw报告.html:170` 逐字「A processual entity … that is a maximally connected spatiotemporal whole and has bona fide beginnings and endings corresponding to real discontinuities」 | `families.<名>` ＋同名 `concepts.<名>` |
| ② 对什么做的 | 「扩展项 SHALL 落在命名空间内，SHALL NOT 与核心字段重名」 | **`Object`** —— `:270` 逐字「An independent continuant … that is spatially extended, maximally self-connected and self-contained」 | `envelope.required` ∪ `envelope.optional`（核心字段面） |
| ①③④⑤⑥⑦ | **本件不管这六格** | —— | —— |


## Requirements

### Requirement: REQ-F-030 本体：极小核心 ＋ 命名空间扩展

- **属于哪一类话**：**跨三类**（`change`＋`act`＋`notice`） —— 本体是三类话共同的装载面
- **状态**：`PARTIAL` —— ★ 本件 `Purpose` 自陈「这一层今天只有草稿、**没有实现**」，而同件证据 `x01`／`x02` 在册 ⇒ **两处相抵，需人核**（本轮不代裁）

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

- **属于哪一类话**：**跨三类**（`change`＋`act`＋`notice`） —— `trace` 是三类话共用的信封格
- **状态**：`REAL` —— `f61`–`f66` 在册；2026-09-28 起端到端可执行验证面已在

信封的 `trace` SHALL 保留为需求：一条事件 SHALL 能声明"它由哪一条事件引起"，且该字段 SHALL 能从**写入入口**给出。
（**2026-09-28 起端到端可执行验证面已在**：库侧 `World::commit_requested` 一直有 `trace`；命令行这一级由
`append … [--trace <id>] [--flag <名>]...` 补上——原文"`World::commit` 与 CLI `append` 都没有 `trace` 参数"**已过期**。）

#### Scenario: 带 trace 的事件可写可读

- **WHEN** 从写入入口提交一条带 `trace` 的事件，再读回
- **THEN** `trace` 原样落账且可读回；`trace` 指向一条不存在的事件时，行为有明文规定（接受或拒绝，二者择一并写死）
- **证据**：`scripts/test/trace_notice.rs::f61_append_with_trace_lands_and_reads_back_byte_for_byte`（逐字节读回）、
  `::f62`（不带 ⇒ **不写 `trace` 键**）、`::f63`（空串按未给）、`::f64`（结果经账本追回意图）、
  `::f65`（**悬空 `id` 仍被接受**——判据 (4) 按"会失败的检查"写：实现若开始拒绝，本条即红）、`::f66`（缺值即用法错误 rc=1 且不落笔）
