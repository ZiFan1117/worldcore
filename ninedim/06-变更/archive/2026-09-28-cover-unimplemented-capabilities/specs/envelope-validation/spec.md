# Spec Delta

## ADDED Requirements

### Requirement: REQ-F-027 家族演进与向前兼容

事件一旦追加**不可改**，故演进 SHALL 是**加法**：`world` 声明词表版本，**只加 `flags`、永不改这个数的含义**；
新家族／新字段的引入 SHALL NOT 让旧事件读不懂。家族演进的形态 SHALL 逐层写死为下面三条：

1. **新家族怎么加**：SHALL 只**新增** `families.<名>` 与同名 `concepts.<名>`；SHALL NOT 删改既有家族的必填格、
   SHALL NOT 改信封字段（书 §2.7 逐字：「核心之外由命名空间扩展，各方在自己的空间里定义自己的概念；
   核心之内不取交集，也不做删减」）。既有家族与信封的必填格**一格未变**，是"纯加法"的判据；
2. **旧读法怎么读新账本**：账本只用旧家族的格 ⇒ SHALL 照读；账本若出现读法**没有语义**的家族 ⇒ SHALL **拒**，
   并**点名**那个家族（写入侧 `ext.world.Ontology.UnknownKind`、折叠侧 `ext.world.ReadModel.UnknownKind`），
   SHALL NOT 静默跳过——**不认识的语义拒绝**（与本 change `REQ-F-029` 对偶）；
3. **新读法怎么读旧账本**：同一本旧账本在新旧两套法律与读法下，折叠结果 SHALL **逐字节相同**
   （书 §4.1 逐字：「一条记录落进来，折出来的状态跟着变；谁想改世界，只能往账本里加一条」）。

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
（依据逐字：出厂本体 `ontology.json:20` —— `"flags": "array  # 能力旗标；未知旗标必须忽略"`。）

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

