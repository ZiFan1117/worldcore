# gate-enforcement Specification

## Purpose
规定"谁可以做什么"这一层对外可核的行为：每一个写动作都要过门禁、被拒的动作不能靠另一类话偷渡、
拒绝本身也要留下说清理由的流水。
**摩擦挂在动作的不可逆等级上，不挂在执行者的身份上**（书第五章 5.5 要的正是这一条；身份只决定白名单外的主体加摩擦到拒绝），
书第五章 5.5 判红的三件事（闸读不到风险等级／两处出厂配置无互校／摩擦挂在执行者身份上）在本能力已逐条落地，
落点与断言见本能力"闸读得到风险等级…"与"不可逆动作只允许白名单主体并加摩擦"两条 Requirement；
**仍在册的缺口**（通告的闸：通告按主体收窄授权）登记在 `openspec/changes/archive/2026-09-28-cover-unimplemented-capabilities/`。
这一能力服务 `管`，判据是"一个越界声明能否被拦下，并留下一条人能读懂的流水"。

## Requirements

### Requirement: 每一个写动作都过门禁

系统 SHALL 在落笔之前对每一条写入做门禁裁决；未在策略中声明的能力 SHALL 被拒绝，
且拒绝 SHALL 作为一条通告落账，而不是仅返回错误。

#### Scenario: 未声明的能力被拒且留下流水

- **WHEN** 以未在策略中声明的能力提交一条 `act`
- **THEN** 提交被拒，账本中新增一条说明该次拒绝的通告
- **证据**：`tests/acceptance.rs::t9_gate_rejects_undeclared_capability_and_records_notice`
      （**今天不在 `world-core/check.sh` 任何一步内被选跑**，仅在全量 `cargo test` 时执行）

### Requirement: `act` 的效果不能靠 `change` 偷渡

系统 SHALL 对 `change` 同样执行写权限裁决；当某一主体无权执行某动作时，
它 SHALL NOT 能通过提交一条 `change` 达到同等效果。

#### Scenario: 越权者用 change 达成静音效果被拒

- **WHEN** 主人先成功写入一条 `change`；随后一个不在白名单的主体提交一条效果相同（静音）
      的 `change`
- **THEN** 第二次提交被拒（错误含"门禁拒绝写入"），状态仍为原值，
      且账本里除那条合法 `change` 外只多一条 `gate.write-rejected` 通告
- **证据**：`tests/contract.rs::c01_change_is_gated_and_cannot_smuggle_an_act`
      （由 `world-core/check.sh` 第 ③b 步执行）

### Requirement: 不可逆动作只允许白名单主体并加摩擦

对声明为不可逆（`reversible: false`）的能力，系统 SHALL 执行以下口径，且该口径 SHALL 被如实声明：

- 可逆动作 ⇒ 免检（`Allow`），不带摩擦旗标，但 `act` SHALL 落账（免检 ≠ 不记）；
- 不可逆、主体**在** `irreversible_actors` 内 ⇒ 放行，**且事件 SHALL 带摩擦旗标**
  （`gate.friction:<等级>`，等级取自载体清单 `risk`，无清单取 `unlisted`），旗标随事件落账；
- 不可逆、主体**不在**该白名单内 ⇒ `AwaitApproval`（加摩擦到拒绝执行）：SHALL 落一条
  `gate.awaiting-approval` 通告，理由 SHALL 明说 v1 **没有审批通道**、不要等批准，并写出风险等级。

摩擦的落点是**动作的不可逆等级**，不是执行者身份：`friction` 只看能力是否可逆，**与请求者是谁无关**；
身份只在下一步决定后果（放行并留旗标／拒绝执行）。**本口径 SHALL NOT 被读成"有审批环节"。**

#### Scenario: 不可逆能力触发摩擦

- **WHEN** 一个**不在** `irreversible_actors` 内的主体提交一个不可逆能力
- **THEN** 门禁加摩擦路径被触发，落一条 `gate.awaiting-approval` 通告，理由明说 v1 无审批通道
- **证据**：`tests/acceptance.rs::t10_gate_adds_friction_for_irreversible_capability`
      与 `tests/atom_reversibility.rs::a05_non_whitelisted_actor_gets_friction_and_the_level_shows_in_the_flow`
      —— **⚠** 原证据行的原话"提交一个不可逆能力"未限定主体，会读出"任何主体都被加摩擦"；
      今天的口径是**白名单内放行且必加摩擦旗标、白名单外加摩擦到拒绝执行**——
      前者由 `tests/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`
      断言（同一主体 `world://user`，可逆不带旗标、不可逆带 `gate.friction:high` 且随事件落账）。

#### Scenario: 同一个主体对不可逆动作必加摩擦

- **WHEN** **同一个在册主体**（`world://user`，出厂不可逆白名单里唯一那一个）分别提交一件可逆动作与一件不可逆动作
- **THEN** 可逆动作免检且事件不带摩擦旗标（但照样落账）；不可逆动作放行且事件带 `gate.friction:high`，
      该旗标随事件落进账本
- **证据**：`tests/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`
      —— 变异：把 `world-core/src/gate/mod.rs:572-584` 的 `Policy::verdict` 改成按主体身份判摩擦 ⇒ 本条变红。

#### Scenario: 拒绝流水必须说清它拒绝了什么

- **WHEN** 一个**不在允许名单**的主体提交带保留前缀的通告
- **THEN** 被拒，且门禁写下的通告里含被拒内容的指纹字段
- **证据**：`tests/contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders`
      与 `tests/contract.rs::c23_gate_notice_says_what_it_refused`
      —— **⚠ 两段证据不是同一件事**（`audit.md` **G4** 的张冠李戴）：
      `world-core/tests/contract.rs:1095-1118` 的
      `c23_notice_with_reserved_prefix_is_refused_for_outsiders` **只查错误码与理由**
      （`:1106-1109` 断言 `ext.world.Gate.NoticeNotAllowed`、`:1110` 断言含"内核保留前缀"），
      **不查 `refused` 指纹**；
      而 `world-core/tests/contract.rs:1152-1175` 的 `c23_gate_notice_says_what_it_refused`
      走的是**不可逆加摩擦**路径（`:1157` 逐字 `// 触发一条真实的内核裁决流水：agent 请求不可逆动作 ⇒ 加摩擦`，
      `:1167` 逐字 `.find(|ev| ev["body"]["type"] == json!("gate.awaiting-approval"))`）。
      ⇒ "保留前缀被拒路径也要带 `refused` 指纹"这一条今天**没有断言**（列进 tasks）。
- **证据**：上面那条结论**已被推翻**（★ 2026-09-28 订正）：`world-core/tests/contract.rs:1291` 的 `c23_notice_with_reserved_prefix_is_refused_for_outsiders` 里**已经补上了这条断言**——逐字见 `:1316` 的注释「判据③（任务 3.2）：**这条路径写下的流水也带 `refused` 指纹**」与 `:1322-1332` 的 `.expect("保留前缀拒绝流水同样必须带 `refused` 字段（D-14）")` ＋ `assert!(refused.starts_with("fnv1a64:"), …)`（**这正是 `fc-2026-004` 的任务 3.2 补的那条**）⇒ 原文那句「本条尚无断言」**今天不成立**。`refused` 指纹的落点是
      `world-core/src/lib.rs::gate_refusal`（`:436` 逐字 `let refused = Self::refused_digest(actor, act_body);`，
      `:449` 逐字 `"refused": refused,`）；
      今天的两条 `c23` 用例一条只查错误码与理由、一条走的是不可逆加摩擦路径，都不查该指纹。

### Requirement: 门禁配置在被管者不可写的域

系统 SHALL 在启动时检查**法律与账本文件的权限 mode 位及其所在目录的权限**；
当法律可被 group/other 写、或账本可被 group/other 写（含其所在目录）时 SHALL 拒绝启动。

同一道静态墙 SHALL 覆盖**载体侧执行清单**（`cap.d/` 目录及其下每份清单文件）：
它们今天参与"拒启"这个决定（两处互校），故与策略同权——被管者不得能改
（否则改清单就能把世界弄成起不来，或把互校糊过去）；可被 group/other 写时 SHALL 拒绝启动。

系统 SHALL NOT 声称启动时会自动检查**属主**：属主断言是**部署方自证工具**，
只在显式传入 `--owner-uid` 时运行，不传即不运行。

#### Scenario: 法律可被他人写时拒绝启动

- **WHEN** 本体文件的权限使他人可写
- **THEN** 世界拒绝启动
- **证据**：`tests/acceptance.rs::t11_world_refuses_to_start_when_law_is_writable_by_others`

#### Scenario: 账本可被他人写时拒绝启动

- **WHEN** 账本文件的权限使他人可写
- **THEN** 世界拒绝启动
- **证据**：`tests/acceptance.rs::t12_world_refuses_start_when_ledger_is_writable_by_others`

#### Scenario: 属主断言能识别错误属主

- **WHEN** 显式以与预期不符的属主运行属主断言
- **THEN** 断言报错而不是放行
- **证据**：`tests/contract.rs::c10_owner_assertion_detects_wrong_owner`
      —— **⚠ 它不证明"启动时会检查属主"**：不传 `--owner-uid` 即不运行
      （`world-core/docs/S2-设计/WC-IC-001-v0.1.md:355`）。

### Requirement: 运行中的世界不重读策略

系统 SHALL 在启动时装载一次策略；运行期间 SHALL NOT 重新读取策略文件，
使"这一次裁决依据的是哪一版法律"是确定的。

#### Scenario: 运行中改动策略文件不影响本次运行

- **WHEN** 世界运行期间改动策略文件，再提交一个该改动本应影响的动作
- **THEN** 裁决结果与启动时装载的策略一致
- **证据**：`tests/acceptance.rs::t13_running_world_does_not_reread_policy`
      （今天不在 `world-core/check.sh` 任何一步内被选跑，仅在全量 `cargo test` 时执行）

### Requirement: 闸读得到风险等级，且载体可逆与世界可逆互校（不一致即拒启）

闸 SHALL **读得到**风险等级（`risk`），取自载体执行清单（与策略同目录的 `cap.d/*.json`），
并 SHALL 用在**摩擦的轻重与拒绝流水**上（`gate.friction:low`/`:medium`/`:high`；无清单 ⇒ `:unlisted`）。
`risk` SHALL NOT 单独决定"准不准做"（仍由 `reversible` 与 `irreversible_actors` 裁决）⇒ 此边界
SHALL NOT 被读成"风险等级不参与门禁"。

两处出厂配置 SHALL **互校**：载体侧可逆性由 `risk: high` **或** `confirm: required` 导出，世界侧由
`capabilities.<能力>.reversible` 给出。两处各说各话时 SHALL 拒绝启动、点名该能力、写出两处各写了什么，
且 SHALL NOT 落笔建账本；互校 SHALL 在装载策略时自动发生（不新增命令行参数）。边界 SHALL 如实声明：

- **没有 `cap.d` 目录不是错误**：载体侧什么都没声明，就没有"两处"可比，互校跳过；该能力的 `risk`
  读为**未声明**（`None`），SHALL NOT 被当成 `low`。代价如实写出：**这些能力的风险等级，闸读不到**；
- 互校只对**两处都声明了**的能力生效；
- **`undo` 不参与互校**：它撤的是文件系统上的字节（只作工程兜底），与世界状态退不退得回来是两个轴，
  谁也不能推出谁（`world-core/src/carrier/mod.rs`）；拿它互校会把正常形态误判成冲突。
⇒ 本边界 SHALL NOT 被读成"留了撤销点的能力在世界里也可逆"。

#### Scenario: 两处配置互校冲突 ⇒ 拒绝启动且不落笔

- **WHEN** 同一能力在世界侧声明 `reversible: false`、在载体执行清单里声明 `risk: low`、`confirm: never`
      （⇒ 载体侧判**可逆**）
- **THEN** 拒绝启动，拒绝理由含 `ext.world.Gate.ReversibilityMismatch` 并点名该能力、
      写出两处各写了什么，且**账本文件根本不被创建**（一个字节都没落）
- **证据**：`world-core/tests/atom_reversibility.rs::a01_conflicting_reversibility_refuses_to_start`
      —— 变异：把 `world-core/src/gate/mod.rs::cross_check_reversibility` 的 `return Err(…)` 删掉
      （或让它恒 `Ok`）⇒ 本条变红（冲突配置竟能启动）。

#### Scenario: 两处一致即正常启动，且闸读得到等级

- **WHEN** 两处对同一能力同向声明（可逆 ↔ `risk: low`/`confirm: never`；不可逆 ↔ `risk: high`/`confirm: required`），
      其中一项世界侧可逆、载体侧却留了撤销点（`undo: before-each`）
- **THEN** 世界正常启动；闸读到的等级与该能力清单里写的 `risk` 一致；**留撤销点不使启动被拒**
- **证据**：`world-core/tests/atom_reversibility.rs::a02_consistent_reversibility_starts_normally`
      与 `world-core/tests/atom_reversibility.rs::a03_gate_reads_the_risk_level_of_the_factory_config`
      —— 反"恒红"对照：没有这两条，`a01` 可能因为"什么都拒"而通过。
      变异：把载体侧可逆性改用 `undo` 导出 ⇒ 出厂 `ledger.compact`（`undo: before-each` ＋ `reversible: false`）
      被误判冲突 ⇒ 两条一起变红。

#### Scenario: 载体可逆不等于世界可逆

- **WHEN** 一项能力在载体侧留了撤销点（`undo: before-each`），而世界侧标 `reversible: false`
- **THEN** 门禁按"世界不可逆"处置（该动作必带摩擦：白名单内放行并留旗标、白名单外加摩擦到拒绝执行），
      载体撤销点**不**被当作世界可逆的依据，**也不**被当作两处冲突的理由
- **证据**：`world-core/tests/atom_reversibility.rs::a02_consistent_reversibility_starts_normally`
      （第三项 `job.start`：世界侧可逆 ＋ 载体侧留撤销点 ⇒ 照样启动）
      与 `world-core/tests/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`
      （不可逆动作必带摩擦旗标）
      —— 变异：把 `world-core/src/gate/mod.rs::cross_check_reversibility` 的载体侧判据换成读 `undo`
      ⇒ `a02` 变红。

### Requirement: 通告的闸，以及门禁不可绕过的部分实现边界

通告 SHALL 过闸，两条纪律各自可单独判真假：
① 带保留前缀（`gate.`）的通告类型 SHALL 只许内核自己写，外部提交一律拒；
② 非保留前缀的通告，其 `actor` SHALL 已在主体白名单内。

门禁不可绕过 SHALL 只声明**已实测的范围**：进程内唯一写入口、静态墙（mode 位）、
以及**两处出厂配置的互校**（互校判"拒启"，它成立的前提是策略与执行清单同样落在被管者写不到的域）
已在跨 uid 形态下实测；
**祖先链遍历、通道层与 Landlock 自缚在 v1 未做**，此边界 SHALL 被如实声明，
SHALL NOT 被读成"门禁在所有路径上不可绕过"。

已知的不对称 SHALL 被登记：非保留前缀的通告**不检查 `writes` 授权表**、只检查主体白名单。

#### Scenario: 保留前缀通告只许内核自己写

- **WHEN** 一个外部主体提交 `type` 以 `gate.` 开头的通告
- **THEN** 被拒，错误串含 `ext.world.Gate.NoticeNotAllowed`，且伪造通告不落笔
- **证据**：`tests/contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders`

#### Scenario: 不在册主体不得写普通通告，在册主体必须能写

- **WHEN** 一个不在白名单的主体提交普通通告；对照组由在册主体提交同样形状的通告
- **THEN** 前者被拒（`ext.world.Gate.NoticeRejected`），后者通过
- **证据**：`tests/contract.rs::c23_notice_from_unlisted_actor_is_refused`

#### Scenario: 门禁不可绕过的未做部分被如实声明

- **WHEN** 查阅本能力的覆盖声明
- **THEN** 祖先链遍历、通道层与 Landlock 自缚三项标为**未做**
- **证据**：`world-core/docs/S1-需求/WC-SRS-001-v0.1.md`:83（REQ-F-015 状态列）
      —— 该项**今天没有自动化断言**（"未做"不可被断言），其载体是流程侧登记与 `review.md` 的签字。

### Requirement: 〔无号·待流程侧增补〕通告的闸

**通告 SHALL 与变更、动作一样过门禁**：主体只能发它被允许发的通告；不该由它发的通告 SHALL 被拒，拒绝 SHALL 留下可核的流水。
（两条纪律已在实现里落地：① 带保留前缀（`gate.`）的通告类型只许内核自己写；② 非保留前缀的通告，其 `actor` 必须在主体白名单内——执行者是 `world-core/src/lib.rs::adjudicate_notice`。）
**仍在册的缺口**：非保留前缀的通告**不检查 `writes` 授权表**、只检查主体白名单（通告按主体收窄授权属门禁强度变更，须人裁）。

#### Scenario: 越权通告被拒且留痕

- **WHEN** 一个未被允许的主体提交一条本不该由它发的通告
- **THEN** 提交被拒、不落笔，且账本里留下一条说明**拒绝了什么**的流水
- **证据**：`world-core/tests/contract.rs::c23_notice_from_unlisted_actor_is_refused`
      （不在册主体被拒且错误码为 `ext.world.Gate.NoticeRejected`；同用例带在册主体的正例对照）
      与 `world-core/tests/contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders`
      （保留前缀路径）
      —— **⚠ 两条都不查 `refused` 指纹、也不查"伪造通告不落笔"**：前者只查错误码，
      后者的"不落笔"由 `world-core/src/lib.rs::gate_refusal` 的写法承担而无断言
      ⇒ **本条的这两句今天尚无断言**（列进 tasks）。

### Requirement: 〔无号·待流程侧增补〕可逆性判定与出厂配置互校

闸 SHALL 读得到动作的风险等级，并按**动作的不可逆等级**决定是否加摩擦；载体层的撤销点与世界状态的可逆性 SHALL **各自成立且互不冒充**，两处出厂配置冲突时 SHALL 拒绝启动。

#### Scenario: 同一个主体对不可逆动作必加摩擦

- **WHEN** 白名单内的主体对一件声明为不可逆的动作提交请求
- **THEN** **加摩擦**（在账本上留下可核痕迹：事件带 `gate.friction:<等级>` 旗标）；对可逆动作则免检但留痕
- **证据**：`world-core/tests/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`
      （同一主体 `world://user`：可逆不带旗标、不可逆带 `gate.friction:high` 且随事件落账）
      —— **本条的"有待批或确认环节"措辞已按实现改正**：v1 **没有审批通道**，白名单主体的摩擦是
      "必留可核痕迹 ＋ 由预批身份承担"，不是"停下来等人批"。
