# Spec Delta

## MODIFIED Requirements

### Requirement: 信封的必填字段被逐字段强制

系统 SHALL 对每一条写入事件逐字段校验信封必填项 `world` / `kind` / `id` / `seq` / `at` /
`actor` / `flags` / `body`；任一字段缺失时 SHALL 拒绝该事件。

系统 SHALL 另外明确声明该断言的边界：错误信息 **SHALL** 报出缺失字段名这一要求，
今天只对 `kind` / `id` / `seq` / `at` / `actor` / `flags` / `body` **七个字段**成立；
`world` 一轮由错误码前缀 `ext.world.` 满足了"含该字段名"的判据，
SHALL NOT 被读成"`world` 缺失也被指名报出"。

#### Scenario: 八个必填字段逐字段被拦

- **WHEN** 依次构造 8 条事件，每条分别删掉一个必填字段
- **THEN** 每条都被校验拒绝
- **证据**：`tests/contract.rs::c02_every_required_envelope_field_is_enforced`
      —— **⚠ `world` 一轮的"报出字段名"是恒真断言**（`src/ontology.rs:32` 的前缀自带 `world`）
      ⇒ 该轮要成为"指名报出"的证据 ⇒ 需补断言（列进 tasks）。

### Requirement: 三类话之外一律被拒

系统 SHALL 只接受本体声明的三个家族（变更 / 请求与结果 / 通告）；出现未知家族时 SHALL 拒绝，
SHALL NOT 猜测其含义，SHALL NOT 落笔该事件，且 SHALL NOT 改动世界状态。

#### Scenario: 不认识的事件家族被拒

- **WHEN** 以本体未声明的 `kind` 提交事件
- **THEN** 提交失败，错误串含 `UnknownKind`，且不落笔该事件（账本 `last_seq` 不前进）
- **证据**：`scripts/test/acceptance.rs::t5_law_rejects_and_does_not_write`
      —— **⚠ 该测试今天不在 `check.sh.new` 的任何一步内被选跑**：
      `:98` 只选 `t1_ t2_ t7_`、`:103` 只跑 `--test contract` ⇒ 仅在全量 `cargo test` 时执行；
      且它**不断言"状态未被改动"** ⇒ 需补断言（列进 tasks）。

### Requirement: 法律损坏或指向别处时拒绝启动

本体与门禁策略 SHALL 在世界打开时装载并校验；文件缺失、家族为空、能力表为空、白名单为空、
`writes` 段缺失时 SHALL 拒绝启动；法律文件是**符号链接**时 SHALL 拒绝启动，
以免"检查的"与"真正读的"不是同一个文件。

系统 SHALL 明确声明该要求的覆盖边界：本规格 SHALL NOT 声称"不存在静默接受一个畸形策略的路径"
——**未知键与多余键一律被忽略**是设计选择，不是畸形。

#### Scenario: 坏本体拒绝启动

- **WHEN** 本体文件内容损坏
- **THEN** 打开失败
- **证据**：`scripts/test/acceptance.rs::t6_bad_ontology_refuses_to_start`

#### Scenario: 本体缺失与家族为空被拒

- **WHEN** 本体文件不存在，或 `families` 为空
- **THEN** 装载失败（`ReadFail` / `NoFamilies`）
- **证据**：`tests/contract.rs::c04_ontology_load_rejects_missing_file_and_empty_families`

#### Scenario: 策略的每一类畸形形状都被拒

- **WHEN** 以 5 类畸形形状分别装载门禁策略（坏 JSON／缺 `policy`／能力表为空／白名单为空／缺 `writes`）
- **THEN** 每一类都被拒；**对照**：合法策略必须能加载
- **证据**：`tests/contract.rs::c03_policy_load_rejects_every_malformed_shape`
      —— **⚠ 原文"不存在静默接受一个畸形策略的路径"是全称句，与同用例的对照②冲突**：
      `scripts/test/contract.rs:207` 逐字
      `let pol = Policy::load(&p).expect("多余键应被忽略，而不是拒载");`
      ⇒ **未知键与多余键是被忽略的**，该全称句已按事实收窄。

#### Scenario: 策略为符号链接时拒绝启动，而真实文件不被误拒

- **WHEN** 以指向别处的软链作为策略路径打开世界；对照组用真实文件
- **THEN** 软链被拒且错误信息含"符号链接"；真实文件正常打开
- **证据**：`tests/contract.rs::c09_symlinked_law_is_refused`
      —— **⚠ 本证据只覆盖"策略"软链**，本体软链无载体。

### Requirement: 事件身份在进程内唯一

系统 SHALL 保证同一进程内分配的事件 `id` 不重复。
系统 SHALL NOT 声称跨进程或跨重启的 `id` 唯一性由本机制保证。

#### Scenario: 连续提交的事件 id 各不相同

- **WHEN** 在同一进程内连续提交多条事件
- **THEN** 所有事件的 `id` 互不相同
- **证据**：`tests/contract.rs::c05_event_ids_are_unique_within_a_process`

### Requirement: 错误携带机器可读的错误码

系统 SHALL 在失败路径上给出机器可读的错误码（如 `ext.world.*`），使调用方按码判定，
SHALL NOT 要求调用方去匹配中文散文措辞。

系统 SHALL 明确声明本条的范围边界：**并非所有失败出口今天都带码**；
已知的无码出口 SHALL 被逐条登记，SHALL NOT 被"凡失败路径都带码"这类全称句遮住。

#### Scenario: 各类失败路径的错误码可枚举

- **WHEN** 触发布局类（本体形状）、门禁类、法律类、通道类、读模型类失败路径
- **THEN** 每条错误都带稳定的错误码 `ext.world.<域>.<原因>`，且错误码区分度 ≥ 6
- **证据**：`tests/contract.rs::c15_errors_carry_machine_readable_codes`
      —— **⚠ 本证据不含任何账本路径**；且"散文式错误必须判为不符合契约"这一反例
      由同函数的 `scripts/test/contract.rs:779` 承担。

## ADDED Requirements

### Requirement: 错误码契约的已知边界

系统 SHALL 逐条登记**已知的无码失败出口**，使"凡失败路径都带码"这一全称句不成立：

- 静态墙的三条断言：拒绝符号链接、拒绝 group/other 可写（文件与目录）、属主断言未通过；
- 门禁策略版本不支持（`policy != 1`）。

上述出口报的是中文散文，**不带 `ext.world.` 前缀**。
系统 SHALL NOT 把本能力的覆盖声明写成"所有失败路径都已带码"。

#### Scenario: 静态墙三条断言无错误码（边界固定）

- **WHEN** 以符号链接作为法律路径、或以对 group/other 可写的文件作为法律路径打开世界
- **THEN** 拒绝启动，但错误串**不含** `ext.world.` 码——本断言证明的是**边界**而不是实现缺陷
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `src/guard.rs:43`（`assert_not_other_writable`）
      与同文件的符号链接断言；文档出处为 `ninedim/01-意图环/03-设计/设计-WC-IC-001-v0.1.md:350-352`，
      三行末列逐字都写「⚠ **无码**」。

#### Scenario: 策略版本不符出口无错误码（边界固定）

- **WHEN** 以 `policy` 版本号不为 1 的策略打开世界
- **THEN** 拒绝启动，错误串为散文，**不含** `ext.world.` 码
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `src/gate.rs:113-117`。
