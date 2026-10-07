# Spec Delta

## MODIFIED Requirements

### Requirement: 两份读法同源且可当场核对

系统 SHALL 提供语言投影（给程序读）与视觉投影（给人看）两份读法；
两者 SHALL 由**同一读模型与同一词表**派生；
系统 SHALL 提供一条出厂命令当场核对两者首行的**头部四项**一致
（`world` / `vocab` / `last_seq` / `state` 指纹）。

系统 SHALL NOT 把该命令表述为"能证明两份记录说的是同一件事"。

#### Scenario: `project check` 报同源

- **WHEN** 在出厂状态下运行 `world-core project check`
- **THEN** 退出码为 0，stdout 含「同源」与「✅」
- **证据**：`scripts/test/cli.rs::cli05_project_check_reports_same_source`
      —— **⚠ 本断言只到"命令跑通并自报同源"**，既不比对投影内容，也不涉及两份独立来源；
      该命令的判据边界见下一条 `## ADDED`。
      **⚠ 且原证据行括注的「（`check.sh` 步骤 ④）」不成立**：`check.sh.new` 全文
      **不跑 `--test cli`**（`:98` 只选 `t1_ t2_ t7_`、`:103` 只跑 `--test contract`）
      ⇒ `cli05` **不在出厂任何一步里执行**（`audit.md` **P3**）；已删该括注，
      并把"让它在出厂路径上可执行或被替代"登记进 `tasks.md`（第 6.6 条）。

#### Scenario: 换词表能被检出

- **WHEN** 在词表变更后比对两份投影
- **THEN** 同源核对能报出不同源（错误串含"词表不同"）
- **证据**：`tests/acceptance.rs::t16_two_projections_are_same_source_and_vocab_change_is_detected`
      —— **⚠ 这是测试自己构造的 `lang_other`**（`scripts/test/acceptance.rs:718`），
      **`project check` 命令走不到这个分支**（`src/main.rs:408-409` 两份投影共用同一 `state` 与 `vocab`）。

### Requirement: 语言投影与读模型逐项相等

语言投影 SHALL 由读模型派生；把投影逐行解析出的三元组集合与读模型逐项比对，
两者 SHALL **完全相等**（既不得添加状态源里没有的事实，也不得省略状态源里已有的事实）。

#### Scenario: 投影与读模型逐项相等

- **WHEN** 把语言投影逐行解析为 `(主体, 路径, 值)` 三元组，与读模型 `entries()` 比对
- **THEN** 两个集合完全相等
- **证据**：`tests/acceptance.rs::t14_language_projection_matches_read_model`

### Requirement: 视觉投影的排版是可审计契约

视觉投影 SHALL 采用**固定排版契约**（不只是缩进两条），该契约 SHALL 至少包含下列 11 条，
且该契约 SHALL 有**独立于渲染实现本身**的审计器逐条检验：

1. 首行是同源头，严格匹配 `^#world-core projection=visual world=<int> vocab=<tok> last_seq=<int> state=<tok>$`（无多余空格）；
2. 第 2 行是标题，逐字 `世界状态（视觉投影）`；
3. 分隔线只由 `U+2500` 组成且长度 **= 44**；
4. 摘要行格式固定；空状态时为固定的一句话；
5. 收尾分隔线同为 44 个 `U+2500`，**空状态只有 4 行**（无收尾线）；
6. 主体行为**恰好 2 个空格** ＋ `world://…`；
7. 字段行为**恰好 6 个空格** ＋ `路径 = JSON值`，且值必须能被 `json.loads`；
8. **任何字段行不得出现在首个主体行之前**；
9. 全部行**必须被分类**（未分类行数 = 0）；
10. 正文不得含裸控制字符；含换行的值必须被转义；
11. 文件以 **LF** 结尾且无 CR。

#### Scenario: 排版审计对变异必报红、对期望样本必常绿

- **WHEN** 用独立审计器检验 3 份字节级期望样本，并施加 12 个变异
- **THEN** 3 份样本全部通过，12 个变异全部报红
- **证据**：`scripts/verify/visual_layout_audit.py --self-test`（由 `check.sh.new` 第 ⑦ 步执行）

## ADDED Requirements

### Requirement: 出厂同源命令的判据边界

出厂同源命令 `world-core project check` 的判据边界 SHALL 被如实声明为**正式条文**：

① 该命令**自己渲染两份再自己比**——两份投影由**同一个读模型、同一个词表**派生
⇒ `assert_same_source` 的三个不等分支在该命令路径上**结构上不可达**，对任何输入只会报绿；
② 它**只比较头部四项**（`world` / `vocab` / `last_seq` / `state` 指纹），**不比较内容**；
③ 它**从未比过两份由不同一方独立生成的投影**。

系统 SHALL NOT 把该命令表述为"能证明两份记录说的是同一件事"。
跨来源比对（两份由不同一方独立生成）SHALL 被列为**尚未实现**，
其落点 SHALL 由人裁定，SHALL NOT 由本 change 自造编号。

#### Scenario: 出厂命令的判据只有头部四项（边界固定）

- **WHEN** 让两份投影在**内容**上不一致（例如一方少渲一半主体）、而头部四项相同
- **THEN** `project check` **仍然报绿** —— 本断言证明的是**边界**而不是实现缺陷；
      它把该命令的覆盖限定为"同一份输入下的身份一致性核对"
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `src/project/mod.rs:124-145`；
      文档出处为 `docs/理论/语义世界-理论书-第一版-合订.md:736`。

#### Scenario: 该命令的三个不等分支在命令路径上不可达（边界固定）

- **WHEN** 检查 `src/main.rs` 的 `project check` 分支如何构造两份投影
- **THEN** 两份投影取自**同一个 `state` 与同一个 `vocab`** ⇒ 命令路径上不可能出现"世界版本不同／
      词表不同／状态不同"三种不同源
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `src/main.rs:408-410`
      逐字 `let a = language::render(&state, world, vocab);`／`let b = visual::render(&state, world, vocab);`。

### Requirement: 视觉投影与读模型逐项相等

视觉投影 SHALL 由读模型派生；把视觉投影解析出的 `(主体, 路径, 值)` 三元组集合与读模型逐项比对，
两者 SHALL **完全相等**（视觉投影只能改变画法，不得增删世界状态里的事实）。

#### Scenario: 视觉投影与读模型逐项相等

- **WHEN** 把视觉投影解析为 `(主体, 路径, 值)` 三元组，与读模型 `entries()` 比对
- **THEN** 两个集合完全相等
- **证据**：`tests/acceptance.rs::t15_visual_projection_is_human_readable_yet_auditable`
      —— **⚠ 本断言的解析器与渲染器同模块**（`src/project/visual.rs::parse()`）；
      独立于渲染实现的验证面由 `scripts/verify/visual_layout_audit.py` 承担。
