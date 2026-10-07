# write-side-adaptation Specification

## Purpose
规定"世界外面的事怎么变成一条消息"这一层对外可核的行为：**写侧只写、不裁决**，前值必须带上，翻不出来就报错，且这只手**以被管者身份运行、对账本与规则都没有写权限**。这一层原来在 OpenSpec 里**零落点**（书 §4.5 整节没有对应规格），本 delta 把它建档；覆盖面见下表。

**本 delta 覆盖书 §4.5 的哪三条、不覆盖哪一条**（不覆盖的也写在这里，免得被读成"整节已落"）：

| 书 §4.5 的那一段 | 本 delta |
|---|---|
| `:585` 只写不裁决（准不准问 4.2 那道闸） | **覆盖**（第一条 Requirement；`act` 那一半的既有落点见 `WC-IRS-001` §3.12 的 `IF-011-R01`／`R08`） |
| `:595`／`:597` 前值必须带上；翻不出来就报错、不许猜 | **覆盖**（第二条 Requirement；这一格此前**零落点**） |
| `:601` 以被管者身份运行，对账本与规则都没有写权限 | **覆盖**（第三条 Requirement；静态墙的既有落点在 `src/gate/guard.rs`，跨 uid 实测在 `scripts/test/con01-no-bypass.sh`） |
| `:599` 大对象不进主干道，主干道上只留一个内容指纹 | **不覆盖**：**货运道与内容指纹**今天**零落点**（既没有那条并行通道，也没有"以内容引用当字段值"的实现与断言）。⚠️ 同句的前半「主干道上的每一条记录都短」**另有落点**（`policy.json` 的 `channel_limits.max_line_bytes`，见 `src/bus/mod.rs` 的 `Limits::from_policy`）——那是通道的单行上限，不是货运道，两者不得互相冒充 |

## Requirements

### Requirement: 〔无号·待流程侧增补〕写侧只写，不裁决

写侧 SHALL 只负责把世界外面发生的事翻成一条消息；**准不准做 SHALL 一律交给门禁判定**，写侧 SHALL NOT 自行裁决。
（书 §4.5 逐字：「它们与世界要的形式之间隔着一只手，这只手在写侧，它的纪律只有一条：只写，不裁决。准不准做，一律问 4.2 那道闸。」）

写侧的"不裁决"在实现里是**结构**，不是措辞，三处可逐字核：

- `src/carrier/run.rs`：`act` 那一半的顺序不可交换（先问内核 → 内核说不行就一次都不动 → 才执行 → 结果带因果回写）；
- `src/carrier/providers.rs`：执行序列**只能拒绝，永远不能放行**（放行只发生在"问过门禁之后"）；
- `src/carrier/writeside.rs`：`change` 那一半的提交**原样**交给内核，内核说拒就照原话转述（`Submitted::Refused`），写侧不重判。

#### Scenario: 写侧不放过、也不拦下任何一条

- **WHEN** 向写侧提交一件按出厂策略**不该放行**的事
- **THEN** 写侧**原样提交**、由**门禁**拒绝并留下流水；写侧自己**不做**放行或拦截的判定
- **证据**：`scripts/test/write_side.rs::w01_the_write_side_submits_verbatim_and_never_adjudicates`
      （写侧交出去的那一行**逐字段**等于翻出来的信纸，信封里只有 `kind`／`body`——**没有身份**；判词带门禁那一族的错误码）
- **证据**：`scripts/test/write_side.rs::w02_a_gate_refusal_leaves_a_trail_and_nothing_lands`
      （真内核：门禁拒 ⇒ 账本里只有一条 `gate.write-rejected` 流水，那条 `change` 一次都没落笔）
- **证据（正控）**：`scripts/test/write_side.rs::w03_the_same_change_lands_when_the_world_allows_it`
      （同一条变化，世界允许时**必须**落笔，且落笔的 `actor` 来自内核的套接字映射）
- **证据（既有系统级）**：`scripts/test/carrier_acceptance.sh`（C-04／C-04b：真实二进制上"门禁不放行 ⇒ 一次都没动 ＋ 留痕"）

### Requirement: 〔无号·待流程侧增补〕前值必须带上；翻不出来就报错、不许猜

写侧 SHALL 把"外面的一处变化"翻成"**某个对象的某个字段从旧值变成新值**"，**前值 SHALL 随记录带上**；写侧 SHALL NOT 在翻不出来时猜一个近似的字段名填上去，**翻不出来 SHALL 报错并拒绝写入**。

两条口径各有可核的落点（`src/carrier/translate.rs`）：

- **前值**：外部变化里的前值是 `Option<Value>`；`None`（外部系统给不出旧值）⇒ 报错 `ext.world.Carrier.NoPreviousValue`。**没有兜底分支**——不拿 `null`、也不拿新值顶上。⚠️ 显式的 `null` 前值是**合法**的前值（「没有前值」与「前值是空」是两件事）。
- **名字**：只认**逐字相等**的 (主体, 字段)，由声明回答（`Declared` 窄接口）；不在声明里 ⇒ 报错 `ext.world.Carrier.UnmappableField`。近似名（`mute` 之于 `muted`）**同样拒绝**。

⚠️ **本条今天证明到哪一步（如实声明，不许被读成全称成立）**：

- **库层已落成、有断言**：`src/carrier/translate.rs` 与 `src/carrier/writeside.rs`；
- **装配接线待补**：声明面由 `impl Declared for Ontology`（一行）提供，落点是 M04 的装配点 `src/lib.rs`，而 `src/lib.rs` 与 `src/main.rs` **不在本工区的文件面内** ⇒ 今天**没有 CLI 子命令**从命令行走到这条路上；断言走的是库接口。

#### Scenario: 翻不出来的输入被拒，且账本没有多出一条

- **WHEN** 给写侧一件**无法映射**到已声明字段的外部变化
- **THEN** 写侧**报错并拒绝**；读回账本，**条数不变**；错误信息里能读出**是哪一处**翻不出来
- **证据**：`scripts/test/write_side.rs::w04_a_change_without_a_previous_value_is_refused_and_the_ledger_does_not_grow`
      （缺前值 ⇒ `NoPreviousValue`、账本 0 行；后一半是**正控**：同一件事带上前值必须落笔 ⇒ 那个 0 行不是"世界坏了"）
- **证据**：`scripts/test/write_side.rs::w05_an_undeclared_field_is_refused_and_never_guessed`
      （真账本上：近似名被拒、账本 0 行；对齐后落笔 ⇒ 正控）
- **证据**：`scripts/test/write_side.rs::w06_a_similar_field_name_never_reaches_the_kernel`
      （假内核上：翻不出来时**一个连接都没有** ⇒ 排除"交了、只是被拒了"这一种解释）
- **证据（单元级）**：`src/carrier/translate.rs::a_missing_previous_value_is_refused_and_never_filled_in`、
      `src/carrier/translate.rs::an_explicit_null_previous_value_is_still_a_previous_value`、
      `src/carrier/translate.rs::a_similar_but_undeclared_field_name_is_refused_not_guessed`

### Requirement: 〔无号·待流程侧增补〕写侧以被管者身份运行，且对账本与规则没有写权限

写侧 SHALL 以**被管者身份**运行在自己的进程里，**SHALL NOT** 对账本与出厂规则有任何写权限；它要写世界，SHALL 经通道提交请求，走**与任何其他主体完全相同**的那条路（校验、过闸、落笔）。

本条的两半各有归属，SHALL NOT 互相冒充：

- **"对这些路径写不写得到"（文件系统上的事实）**：`src/carrier/boundary.rs::assert_managed_cannot_write` —— 四条判据：不是符号链接、属主不是被管者、文件对 group/other 不可写、**所在目录**对 group/other 不可写且其属主不是被管者。它与 `src/gate/guard.rs` 的静态墙**同一纪律、方向相反**（guard 的 `assert_owned_by` 要求属主**是**核心 uid——那一条要部署方显式传 `--owner-uid` 才运行；本处要求属主**不是**被管者），且刻意**不复用** `guard`：`M05 → M10` 已有一条真实 import 边，反向再连即**成环**（`WC-ATOM-001` §二 A-4）。
- **"本进程现在到底是谁"**：由部署保证（`src/bus/mod.rs` 的 `bind` 一类的"权限即身份"、`runuser`／systemd `User=`），并由**跨 uid 实测**核；本模块不靠自称来证明身份。

⚠️ **本条今天证明到哪一步（如实声明）**：静态墙（`src/gate/guard.rs`）与跨 uid 实拒**早已存在**（`scripts/test/con01-no-bypass.sh`：以 `agent` 身份改配置／替换配置／直写账本三组全被拒，且断言 uid 自证与拒绝原因）；**新补的是写侧自己的那一半**——"对这个被管者 uid，账本与规则写不写得到"的可判函数 ＋ 会红的断言，以及**以被管者身份跑载体自己**的那条系统级实测（C-09）。

#### Scenario: 写侧手里的权限不足以绕过闸

- **WHEN** 让写侧进程**直接**尝试写账本或改出厂规则
- **THEN** 两次尝试**都被拒**（权限不足），写侧唯一能走通的路是**经通道提交**
- **证据**：`scripts/test/carrier_acceptance.sh`（C-09：以被管者身份跑**载体自己**——账本读得到、账本写不到、规则改不了；同组含"放宽 mode 后同一动作**会成功**"的反证，证明判据不是橡皮图章）
- **证据（既有，跨 uid）**：`scripts/test/con01-no-bypass.sh`
- **证据（库层事实面）**：`scripts/test/write_side.rs::w07_the_write_side_boundary_holds_only_when_the_facts_hold`
      （真账本／真规则上，布置合规 ⇒ 通过；放宽 mode／属主改成被管者／放宽目录 ⇒ 逐条被抓）
- **证据（单元级）**：`src/carrier/boundary.rs::a_well_placed_file_passes_and_every_relaxation_is_caught`、
      `src/carrier/boundary.rs::relative_path_maps_to_current_dir`
