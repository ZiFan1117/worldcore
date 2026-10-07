# envelope-validation Specification

## Purpose
规定"一件事写下来只有一种形式"这一层对外可核的行为：信封的必填字段被逐字段强制、
三类话之外一律被拒、法律（本体与策略）损坏时拒绝启动而不是带病运行。
这一能力服务"只固定意思的形式"这条边界——它校验形状，不校验含义。

## Requirements

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
      —— **⚠ `world` 一轮的"报出字段名"是恒真断言**（`src/ontology_definition/mod.rs:32` 的前缀自带 `world`）
      ⇒ 该轮要成为"指名报出"的证据 ⇒ 需补断言（列进 tasks）。

### Requirement: 信封字段的类型按本体的声明判（**读路径也判**）

系统 SHALL 按本体 `envelope.fields` 的**声明**校验信封字段的**类型**（声明串**首词即类型**：
`integer` / `number` / `string` / `array` / `object` / `bool`）；不符即拒，码 SHALL 为
`ext.world.Ontology.BadFieldType`，并 SHALL **点名那一格**。

本条 SHALL NOT 被读成"形状已查全"：只判**声明过且值在场**的**信封**字段——
**缺格**另有其主（读侧 `ext.world.ReadModel.MissingCell`、`seq` 由 `ext.world.Ledger.MissingSeq`）、
**枚举值**另有其主（家族查找报 `ext.world.Ontology.UnknownKind` 并点名）、
`body` **内部**字段不属本条。

两条边界：① **不认得的声明词一律放行**（不替本体发明类型系统）；
② **`null` 算"在场"**⇒ 判类型不符（与"键不写"不是一回事）。

#### Scenario: 读路径上类型不符的信封被拒且点名那一格

- **WHEN** 打开一份账本，其中的事件把某一格写成与声明不符的类型（`world` 写成字符串、`actor` 写成整数）
- **THEN** 打开被拒，错误码为 `ext.world.Ontology.BadFieldType`，且**点名那一格**；同形但类型合规的账本必须打得开（正控）
- **证据**：`scripts/test/contract.rs::c34_envelope_field_types_are_checked_on_the_read_path`
      （两处反例 ＋ 一处正控）。**写入路径的次序不变**：`world` 写成字符串时写侧仍先报 `BadVersion`，
      本判据**不抢**它——那条既有契约钉在 `scripts/test/contract.rs::c02_every_required_envelope_field_is_enforced`。

#### Scenario: 声明之外的词一律放行（边界固定）

- **WHEN** 本体把某格的类型声明改成一个**不认得的词**（如 `weird`），而事件里该格的值类型不符
- **THEN** 不判类型、放行 —— 本判据**不替本体发明类型系统**
- **证据（待补）**：**本条尚无断言**（列进 tasks）。落点：`scripts/test/contract.rs` 里加一条用例
      （另造一份把某格声明写成 `weird` 的坏本体，喂一条该格类型不符的事件，断言**打开成功**）。
      该边界**已被独立实测确认**（独立评审席自造 12 组账本里的 `weird` 一组：`actor: 123` ⇒ rc=0），
      但**仓内今天没有会红的断言**——故照实标"待补"，**不拿实测当断言**。

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

### Requirement: 错误码契约的已知边界

系统 SHALL 逐条登记**已知的无码失败出口**，使"凡失败路径都带码"这一全称句不成立：

- 静态墙的三条断言：拒绝符号链接、拒绝 group/other 可写（文件与目录）、属主断言未通过；
- 门禁策略版本不支持（`policy != 1`）。

上述出口报的是中文散文，**不带 `ext.world.` 前缀**。
系统 SHALL NOT 把本能力的覆盖声明写成"所有失败路径都已带码"。

#### Scenario: 静态墙三条断言无错误码（边界固定）

- **WHEN** 以符号链接作为法律路径、或以对 group/other 可写的文件作为法律路径打开世界
- **THEN** 拒绝启动，但错误串**不含** `ext.world.` 码——本断言证明的是**边界**而不是实现缺陷
- **证据**：`scripts/test/contract.rs` 的 **`c24`（「已知无码出口」，任务 2.6）**——其头注的表逐字列三行**标签**「① 静态墙·**符号链接**」「② 静态墙·**mode 位**」「③ 静态墙·**属主**」（三行的实现分别是 `src/gate/guard.rs` 里的 `assert_not_symlink`／`assert_not_other_writable`／`assert_owned_by`；★ 2026-09-28：本处**初版把表里那三个简写原样引进引文**，判据② 当场按"文件路径"校验而报红 ⇒ 现把它们移出引文、写成**带路径**的形式），并逐字写明「**c24**：四条**已知无码出口**的错误串**不含** `ext.world.` 前缀——这是**边界**，不是缺陷」＋为什么"没有码"也要有断言（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**）——实现侧为 `src/gate/guard.rs::assert_not_other_writable`（:43）
      与同文件的符号链接断言；文档出处为 `ninedim/01-意图环/03-设计/设计-WC-IC-001-v0.1.md:350-352`，
      三行末列逐字都写「⚠ **无码**」。

#### Scenario: 策略版本不符出口无错误码（边界固定）

- **WHEN** 以 `policy` 版本号不为 1 的策略打开世界
- **THEN** 拒绝启动，错误串为散文，**不含** `ext.world.` 码
- **证据**：`scripts/test/contract.rs` 的 **`c24`** 第 **④** 行（表内逐字「④ 策略**版本不符**」＋实现是 `src/gate/mod.rs` 里 `Policy` 的装载函数（`load`）＋逐字「门禁策略版本不支持：期望 1，实得 2」）；`:1504` 逐字注释「④ 策略版本不符：其余一切都合法，只有 `policy` 不是 1」，`:1516` 把它纳入逐条断言）（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**）——实现侧为 `src/gate/mod.rs`:113-117。

### Requirement: REQ-F-027 家族演进与向前兼容

事件一旦追加**不可改**，故演进 SHALL 是**加法**：`world` 声明词表版本，**只加 `flags`、永不改这个数的含义**；
新家族／新字段的引入 SHALL NOT 让旧事件读不懂。家族演进的形态 SHALL 逐层写死为下面三条：

1. **新家族怎么加**：SHALL 只**新增** `families.<名>` 与同名 `concepts.<名>`；SHALL NOT 删改既有家族的必填格、
   SHALL NOT 改信封字段。既有家族与信封的必填格**一格未变**，是"纯加法"的判据；
2. **旧读法怎么读新账本**：账本只用旧家族的格 ⇒ SHALL 照读；账本若出现读法**没有语义**的家族 ⇒ SHALL **拒**，
   并**点名**那个家族（写入侧 `ext.world.Ontology.UnknownKind`、折叠侧 `ext.world.ReadModel.UnknownKind`），
   SHALL NOT 静默跳过——**不认识的语义拒绝**（与本 change `REQ-F-029` 对偶）；
3. **新读法怎么读旧账本**：同一本旧账本在新旧两套法律与读法下，折叠结果 SHALL **逐字节相同**
   。

已知家族里新增一格时，两半 SHALL 分开判，SHALL NOT 合成一句"加法演进"：

- 加**可选**格 ⇒ 旧账本 SHALL 照读、折叠结果 SHALL 逐字节不变（不认识的**附加信息**忽略）；
- 加**必填**格 ⇒ 旧账本行 SHALL 读不过去，且**点名**缺的那一格（把某一格加成必填是**破坏性**的）。

**边界（SHALL NOT 被读成全称成立）**：读法认得哪些家族，今天是**编译进读模型**的三家族；
只往本体里加家族而不动读法时，读模型 SHALL 拒（上面第 2 条即此）。把家族表也变成数据是另一件事，本条不含。

#### Scenario: 新家族按加法加，新读法照读旧账本

- **WHEN** 取一份只新增家族与同名概念的新本体，与出厂本体分别读**同一本旧账本**
- **THEN** 词表身份**改变**（"换本体"确实发生）、既有三家族的必填格一格未变、旧账本每一行仍合法，
  且两套读法的折叠结果**逐字节相同**
- **证据**：`scripts/test/family_readmodel.rs::h01_a_new_family_is_added_by_addition_and_the_new_reader_reads_the_old_ledger`

#### Scenario: 读法没有语义的家族被拒且点名

- **WHEN** 账本里出现一条**新家族**的行
- **THEN** 写入侧与折叠侧两处都**拒**、各自**点名**那个家族；把那一行去掉后，新旧两套读法**都照读**
- **证据**：`scripts/test/family_readmodel.rs::h02_a_reader_refuses_a_ledger_that_uses_a_family_it_does_not_know`

#### Scenario: 加可选格无害、加必填格破坏性

- **WHEN** 给**已知家族**加一格可选、再把它加成必填，两次都读同一本旧账本
- **THEN** 前者照读且折叠结果逐字节不变；后者读不过去并点名那一格（写入侧与折叠侧各报一次）
- **证据**：`scripts/test/family_readmodel.rs::h03_a_new_optional_cell_is_ignored_while_a_new_required_cell_is_refused`

#### Scenario: 两个方向各有一条会红的断言

- **WHEN** 分别造出"不认识的家族"与"不认识的旗标"两条事件
- **THEN** 前者被**拒**且不落笔；后者被**接受**、落笔，且不影响后续折叠
- **证据**：`scripts/test/ontology_ext.rs::e02_a_landed_ledger_line_with_unknown_flags_folds_byte_identically`
      与 `scripts/test/ontology_ext.rs::e03_unknown_family_is_refused_on_both_sides_of_the_dual`

### Requirement: REQ-F-029 未知旗标必须忽略

系统 SHALL 忽略任何不认识的旗标，并按它认得的那些继续处理；SHALL NOT 因为出现未知旗标而拒收。
（依据逐字：出厂本体 `src/ontology_definition/ontology.json:20` —— `"flags": "array  # 能力旗标；未知旗标必须忽略"`。）

本条与「未知**家族** SHALL 被拒」**对偶**，两条 SHALL NOT 互相冒充：分界线是
**不认识的语义拒绝，不认识的附加信息忽略**。「这条事件带着我不认得的旗标」SHALL NOT 被读成
「这个家族我不认识」；「这个家族我不认识」SHALL NOT 被读成「有旗标不认识」。
**第三情形**另立条文，SHALL NOT 被并入本条、也 SHALL NOT 被并入家族那一条：
扩展项与**核心字段重名** ⇒ SHALL 被拒（见本 change 的 `REQ-F-030`）——
它不属于「未知」那一类，而属于「与核心冲突」那一类。

#### Scenario: 未知旗标不影响受理

- **WHEN** 提交一条带未知旗标的事件
- **THEN** 该事件被接受、落笔，读回的 `flags` 保留原值；同一账本的折叠结果与不带该旗标时**相同**
- **证据**：`scripts/test/ontology_ext.rs::e02_a_landed_ledger_line_with_unknown_flags_folds_byte_identically`

#### Scenario: 未知旗标与未知家族不许互相冒充

- **WHEN** 取同一条合法事件，分别只把它的 `flags` 换成未知旗标、只把它的 `kind` 换成未知家族
- **THEN** 前者被接受、落笔、折叠结果逐字节不变；后者被拒且**不落笔**——写入侧（`UnknownKind`）与折叠侧（`ReadModel.UnknownKind`）**两处都拒**，且各自点名那个家族
- **证据**：`scripts/test/ontology_ext.rs::e03_unknown_family_is_refused_on_both_sides_of_the_dual`
