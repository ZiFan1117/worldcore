# Spec Delta

## ADDED Requirements

### Requirement: 〔无号·待流程侧增补〕读法是叶子：几份读法之间不互相调用、不持有状态

几份读法之间 SHALL NOT 互相调用——没有一份要问另一份"你那里是什么"，也没有一份可以把自己的输出当作另一份的输入；读法 SHALL NOT 持有自己那一份状态（显示偏好不算状态）。
（书 §4.4 逐字：「不互相调用的意思是，没有一份要问另一份『你那里是什么』，也没有一份可以把自己的输出当作另一份的输入。它们都是账本的读法。**读法是叶子，只负责往外给。**」／「**读法不持有状态。** 读法可以有自己的显示偏好，比如排序、折叠、配色，这些偏好不影响它摆出来的内容；读法一旦开始记自己那一份状态，它就有了自己的说法，而这一层只允许一份说法。」）

#### Scenario: 拔掉一份读法，另一份照常工作

- **WHEN** 让其中一份读法**不可用**（或让它落后若干个事件）
- **THEN** 另一份读法**不受影响**（不因对方缺席而失败、也不去问对方要数据）；两份读法各自的产出**只依赖账本**
- **证据**：`scripts/test/projection_leaf.rs::p01_language_alone_is_complete_and_the_other_reading_never_runs`（**拔掉视觉投影**：本用例**只**跑语言投影一次，断言同源头四项与独立折叠逐项相符、正文「1 头部 ＋ 3 主体」行数齐、三元组与**真正落账的那三条**逐项相符、账本目录跑前跑后件名与字节都不许变）、`scripts/test/projection_leaf.rs::p02_visual_alone_is_complete_and_the_other_reading_never_runs`（对称：**只**跑视觉投影，统计行必须与独立折叠一致、取值行按可审计排版）、`scripts/test/projection_leaf.rs::p03_same_ledger_same_bytes_twice_and_no_state_kept_anywhere`（**同一账本 ⇒ 两次输出逐字节相同**，第二次另设工作目录）、`scripts/test/projection_leaf.rs::p04_ledger_grows_so_does_each_reading`（**账本多一条 ⇒ 两份各自的 `last_seq` ＋1、状态指纹随之变**，且与独立折叠一致）、`scripts/test/projection_leaf.rs::p05_a_lagging_reading_neither_breaks_nor_bleeds_into_the_other`（**让一份落后若干事件**：另一份照常给出完整正确产出，落后只在同源头上暴露）、`scripts/test/projection_leaf.rs::p06_the_two_exits_do_not_carry_each_others_shapes`（两份出口互不夹带对方形态，每条「没有」都配正控）。
  **「不互相调用」的结构面常驻守卫**：`scripts/verify/module_graph.py` 的判据②（`A-4`：`deps == import` 且无环）——`M06`／`M07` 之间一旦出现 `use` 边即判红；`ninedim/01-意图环/03-设计/设计-WC-MODREG-001-v0.1.md` §2 的依赖列逐字：`M06` 行「`M03`」、`M07` 行「`M03`」，与工具抽出的真实 import 边一致；同件 §2.2 层表 `L4 出口` 行逐字「读 L2 与 L1 的元信息；**彼此不交互**；**不得**写任何东西」。**该守卫实测会红**（私有副本上真做一次）：让 `src/project/language.rs` 去调 `src/project/visual.rs` ⇒ 判据② 报「`M06`：**代码里有但没声明**（`M07`）—— 声明集 {`M03`} vs 真实 import 集 {`M03`,`M07`}」、`通过 2 / 失败 1`；同一棵树上**行为面 6 条仍全绿**——这正是"几份读法互不调用"只能靠结构面常驻守卫、行为面看不出来的实证。
  **变异证明**（五条，各自在 VM 的**私有副本**上真做一次：改坏 ⇒ 红 ⇒ 恢复 ⇒ 绿）：① `src/main.rs` 的语言投影那一支改成渲染**视觉投影** ⇒ 5 条红（`p02` 绿）；② `src/project/language.rs` 的正文少给一个主体 ⇒ 3 条红（`p01`／`p05`／`p06`）；③ `src/project/mod.rs` 的同源头 `last_seq` 写死 ⇒ 5 条红（`p06` 绿）；④ 语言投影顺手在账本旁写一份自己的状态 ⇒ `p01`／`p03` 的目录快照断言红；⑤ 语言投影去调视觉投影 ⇒ 判据② 红（同树行为面仍绿）。**恢复后复跑 6/6 绿**（同一条 `cargo test --locked --no-fail-fast`）。
