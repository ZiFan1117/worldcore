# projections Specification

## Purpose
规定"同一份账，各按自己要用的方式读"这一层对外可核的行为：语言投影与视觉投影必须同源、
同源核对必须接在出厂命令上、词表变更必须能被检出、投影只能省略不能添加。
**同源核对只证"同源"，证不了"两份记录说的是同一件事"**——书第五章（合订本 `:659`）逐字：这一格的**当日结果**是"绿而无效"，
而**按"能不能证明两份记录说的是同一件事"来判，这一格是红的**；书同时把"当日结果与结论色压在一列"**点名为缺陷**（合订本 `:1819` M-12）。
书的**通过条件**是「**判定能看内容，且两份由不同一方生成**」（合订本 `:736`）；**今天只做到"头部四项一致"**（`src/gui_projection/mod.rs:124` 的 `assert_same_source`；书自己也写「第 124 行」），
即书判红的那一半。今天的实测边界见 `ninedim/06-变更/archive/2026-09-28-cover-unimplemented-capabilities/` 与本 change 的 `audit.md` P1／P2 两条。
这一能力服务 `显`。

## Requirements

### Requirement: 两份读法同源且可当场核对

系统 SHALL 提供语言投影（给程序读）与视觉投影（给人看）两份读法；
两者 SHALL 由**同一读模型与同一词表**派生；
系统 SHALL 提供一条出厂命令当场核对两者首行的**头部四项**一致
（`world` / `vocab` / `last_seq` / `state` 指纹）。

系统 SHALL NOT 把该命令表述为"能证明两份记录说的是同一件事"。

#### Scenario: `project check` 报同源

- **WHEN** 在出厂状态下运行 `world-core project check`
- **THEN** 退出码为 0，stdout 含「同源」与「✅」
- **证据**：`tests/cli.rs::cli05_project_check_reports_same_source`
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
- **证据**：`scripts/test/cli.rs` 的 **`cli13_project_check_criterion_reads_only_the_header`**（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**，该用例正是这条 Scenario 的断言，其头注逐字「这不是想要的行为，而是**当下边界**：本用例把它固定成会红的检查 —— 谁把正文也纳入判据，这里立刻红，且规格要同步改（不许偷偷放宽）」）——实现侧为 `src/gui_projection/mod.rs`:124-145；
      文档出处为 `docs/理论/语义世界-理论书-第一版-合订.md:736`。

#### Scenario: 该命令的三个不等分支在命令路径上不可达（边界固定）

- **WHEN** 检查 `src/main.rs` 的 `project check` 分支如何构造两份投影
- **THEN** 两份投影取自**同一个 `state` 与同一个 `vocab`** ⇒ 命令路径上不可能出现"世界版本不同／
      词表不同／状态不同"三种不同源
- **证据**：`scripts/test/cli.rs` 的 **`cli14_project_check_feeds_both_projections_the_same_state_and_vocab`**（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**，该用例正是这条 Scenario 的断言，其头注逐字「出处：`src/main.rs:408-410` —— `cmd_project` 里同一次 `open_readonly`、同一次 `read_model`、同一个 `vocab_hash`，两个渲染函数各拿一份**只读**引用 ⇒ 结构上没有「传不同状态」的余地」）——实现侧为 `src/main.rs`:408-410
      逐字 `let a = language::render(&state, world, vocab);`／`let b = visual::render(&state, world, vocab);`。

### Requirement: 视觉投影与读模型逐项相等

视觉投影 SHALL 由读模型派生；把视觉投影解析出的 `(主体, 路径, 值)` 三元组集合与读模型逐项比对，
两者 SHALL **完全相等**（视觉投影只能改变画法，不得增删世界状态里的事实）。

#### Scenario: 视觉投影与读模型逐项相等

- **WHEN** 把视觉投影解析为 `(主体, 路径, 值)` 三元组，与读模型 `entries()` 比对
- **THEN** 两个集合完全相等
- **证据**：`tests/acceptance.rs::t15_visual_projection_is_human_readable_yet_auditable`
      —— **⚠ 本断言的解析器与渲染器同模块**（`src/gui_projection/visual.rs::parse()`）；
      独立于渲染实现的验证面由 `scripts/verify/visual_layout_audit.py` 承担。

### Requirement: 〔无号·待流程侧增补〕读法是叶子：几份读法之间不互相调用、不持有状态

几份读法之间 SHALL NOT 互相调用——没有一份要问另一份"你那里是什么"，也没有一份可以把自己的输出当作另一份的输入；读法 SHALL NOT 持有自己那一份状态（显示偏好不算状态）。
（书 §4.4 逐字：「不互相调用的意思是，没有一份要问另一份『你那里是什么』，也没有一份可以把自己的输出当作另一份的输入。它们都是账本的读法。**读法是叶子，只负责往外给。**」／「**读法不持有状态。** 读法可以有自己的显示偏好，比如排序、折叠、配色，这些偏好不影响它摆出来的内容；读法一旦开始记自己那一份状态，它就有了自己的说法，而这一层只允许一份说法。」）

#### Scenario: 拔掉一份读法，另一份照常工作

- **WHEN** 让其中一份读法**不可用**（或让它落后若干个事件）
- **THEN** 另一份读法**不受影响**（不因对方缺席而失败、也不去问对方要数据）；两份读法各自的产出**只依赖账本**
- **证据**：`scripts/test/projection_leaf.rs::p01_language_alone_is_complete_and_the_other_reading_never_runs`（**拔掉视觉投影**：本用例**只**跑语言投影一次，断言同源头四项与独立折叠逐项相符、正文「1 头部 ＋ 3 主体」行数齐、三元组与**真正落账的那三条**逐项相符、账本目录跑前跑后件名与字节都不许变）、`scripts/test/projection_leaf.rs::p02_visual_alone_is_complete_and_the_other_reading_never_runs`（对称：**只**跑视觉投影，统计行必须与独立折叠一致、取值行按可审计排版）、`scripts/test/projection_leaf.rs::p03_same_ledger_same_bytes_twice_and_no_state_kept_anywhere`（**同一账本 ⇒ 两次输出逐字节相同**，第二次另设工作目录）、`scripts/test/projection_leaf.rs::p04_ledger_grows_so_does_each_reading`（**账本多一条 ⇒ 两份各自的 `last_seq` ＋1、状态指纹随之变**，且与独立折叠一致）、`scripts/test/projection_leaf.rs::p05_a_lagging_reading_neither_breaks_nor_bleeds_into_the_other`（**让一份落后若干事件**：另一份照常给出完整正确产出，落后只在同源头上暴露）、`scripts/test/projection_leaf.rs::p06_the_two_exits_do_not_carry_each_others_shapes`（两份出口互不夹带对方形态，每条「没有」都配正控）。
  **「不互相调用」的结构面常驻守卫**：`scripts/verify/module_graph.py` 的判据②（`A-4`：`deps == import` 且无环）——`M06`／`M07` 之间一旦出现 `use` 边即判红；`ninedim/01-意图环/03-设计/设计-WC-MODREG-001-v0.1.md` §2 的依赖列逐字：`M06` 行「`M03`」、`M07` 行「`M03`」，与工具抽出的真实 import 边一致；同件 §2.2 层表 `L4 出口` 行逐字「读 L2 与 L1 的元信息；**彼此不交互**；**不得**写任何东西」。**该守卫实测会红**（私有副本上真做一次）：让 `src/gui_projection/language.rs` 去调 `src/gui_projection/visual.rs` ⇒ 判据② 报「`M06`：**代码里有但没声明**（`M07`）—— 声明集 {`M03`} vs 真实 import 集 {`M03`,`M07`}」、`通过 2 / 失败 1`；同一棵树上**行为面 6 条仍全绿**——这正是"几份读法互不调用"只能靠结构面常驻守卫、行为面看不出来的实证。
  **变异证明**（五条，各自在 VM 的**私有副本**上真做一次：改坏 ⇒ 红 ⇒ 恢复 ⇒ 绿）：① `src/main.rs` 的语言投影那一支改成渲染**视觉投影** ⇒ 5 条红（`p02` 绿）；② `src/gui_projection/language.rs` 的正文少给一个主体 ⇒ 3 条红（`p01`／`p05`／`p06`）；③ `src/gui_projection/mod.rs` 的同源头 `last_seq` 写死 ⇒ 5 条红（`p06` 绿）；④ 语言投影顺手在账本旁写一份自己的状态 ⇒ `p01`／`p03` 的目录快照断言红；⑤ 语言投影去调视觉投影 ⇒ 判据② 红（同树行为面仍绿）。**恢复后复跑 6/6 绿**（同一条 `cargo test --locked --no-fail-fast`）。
