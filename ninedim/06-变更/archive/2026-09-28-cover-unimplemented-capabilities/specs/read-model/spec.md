# Spec Delta

## ADDED Requirements

### Requirement: 〔无号·待流程侧增补〕声明以外的字段不许落账

写入侧 SHALL 按出厂本体 `ontology.json` 的 `concepts` 校验实体与字段：**未声明的实体**与**未声明的字段** SHALL 被拒；读模型侧 SHALL 对缺格报错，SHALL NOT 静默接受。
（书第五章 5.3 实测的那条命令今天非零退出且账本 0 行：执行者是 `src/ontology.rs::check_concepts`。）

**读模型侧的缺格**（`REQ-F-032` 判据②「缺格即报错」，书第五章 5.6 表 5.2 行逐字
「每个已声明的字段至少有一份读法可读，缺格就报错」）SHALL 逐格可判：

- **"已声明"可机械枚举**：`envelope.required`／`envelope.optional`／三家族各自的 `required`／`concepts`，
  逐项从本体原文现取（条数由该文件现算，本处不复述）；
- **缺格即报错**：一行账本少了**已声明的必填格** ⇒ 读法 SHALL 拒，错误里 SHALL 读出**哪一层**的**哪一格**
  （`ext.world.ReadModel.MissingCell`），以及该层已声明的必填格清单；补回那一格后结论 SHALL 与基线**逐字节相同**；
- **可选格不是缺格**：`to`／`trace`／`params`／`payload` 没写是这份法律允许的形态，SHALL NOT 报缺格；
- **空清单不是"检查通过"**：读法拿不到"已声明格"清单时 SHALL 拒（`ext.world.ReadModel.NoDeclaredCells`）——
  "一个格都没查"与"每个格都查过了"在读数上一样、在结论上相反；
- **缺格与"未知家族" SHALL NOT 互相冒充**：不认识的家族报 `ext.world.ReadModel.UnknownKind` 并点名那个家族
  （与本 change `REQ-F-029` 对偶），它的错误里 SHALL NOT 出现"缺格"的说法。

**边界（SHALL NOT 被读成全称成立）**：读模型**不渲染**信封的 `id`／`at`／`actor`／`world`／`flags`——
它们今天**被读**（缺了即拒，就是上面那条判据），但**不进入状态**（`state --json` 里读不到它们）；
读法认得哪些家族，今天是**编译进读模型**的三家族（`REQ-F-027` 的边界同此）。

系统 SHALL 如实声明本条的两处边界，SHALL NOT 被读成全称成立：

- **裸主体不受约束**：`world://<名字>`（没有实体／实例那一段）今天**照样能落账**——留下它不是口径而是代价
  （既有出厂用例以这种形态写槽位，一律拒绝会把它们打红）。⇒ 书 §5.3 的"世界的边界由声明定"
  在**实体引用**这一半成立，在**裸主体**那一半**仍未成立**；
- **本段只管 `change`**：三家族里只有 `change` 改状态，`act` / `notice` 的信纸由家族必填项管；
  `notice.subject` 的语义是"这条通告关于谁"，不是"改了哪一格"，拿字段表去查它是查错了对象。

#### Scenario: 已声明的格可机械枚举，且与本体原文逐字一致

- **WHEN** 直读出厂本体的信封与三家族声明，与读法侧的清单逐项比对
- **THEN** 信封必填／可选、三家族必填、`concepts` 的实体与字段逐项相同，且本体身份（内容寻址）与出厂值一致
- **证据**：`scripts/test/family_readmodel.rs::h07_the_declared_inventory_is_mechanically_enumerable`

#### Scenario: 缺格即报错，且点名缺的那一格

- **WHEN** 把账本某一行**已声明必填**的那一格删掉（信封的 `actor`，或家族信纸的 `request_id`）
- **THEN** 折叠被拒，错误码是 `ext.world.ReadModel.MissingCell`，错误里读出**哪一层**、**哪一格**、该层该有哪些格；
  补回那一格后结论与基线**逐字节相同**
- **证据**：`scripts/test/family_readmodel.rs::h04_a_missing_declared_cell_is_refused_with_that_cell_named`

#### Scenario: 空清单不许被读成宽松

- **WHEN** 读法收到一份空的"已声明格"清单
- **THEN** 拒绝折叠并给出 `ext.world.ReadModel.NoDeclaredCells`，SHALL NOT 默默放行
- **证据**：`scripts/test/family_readmodel.rs::h06_an_empty_declared_cell_list_is_not_read_as_lenient`

#### Scenario: 命令这一级也拒（缺格即报错的可执行形态）

- **WHEN** 用一本删掉必填字段 `actor` 的账本跑 `state --json`
- **THEN** `rc=2`，错误里读出 `ext.world.ReadModel.MissingCell` 并**点名** `actor`；把那一格补回去后 `rc=0`
- **证据**：`scripts/test/family_readmodel.rs::h05_the_cli_read_path_refuses_a_missing_declared_cell_end_to_end`
      与 `scripts/test/s1_sys_probe.sh` 的 `TC-047` ⑨

#### Scenario: 未声明的实体与字段都被拒

- **WHEN** 分别写入一个未声明的实体、一个未声明的字段
- **THEN** 两次都被拒、都不落笔，且错误里能读出**是哪个实体 / 哪个字段**没有声明
- **证据**：`scripts/test/atom_declared_only.rs::b01_undeclared_entity_is_refused_and_nothing_lands`
      与 `scripts/test/atom_declared_only.rs::b02_undeclared_field_is_refused_and_nothing_lands`
      —— 反"什么都拒"对照：`scripts/test/atom_declared_only.rs::b03_declared_entity_and_field_still_land`；
      走真二进制的同一条命令：`scripts/test/atom_declared_only.rs::b05_cli_append_of_an_undeclared_entity_is_refused`
      （断言 `rc=2` 且账本逐字为空）；
      登记在册的缺口：`scripts/test/atom_declared_only.rs::b04_bare_subject_is_a_registered_gap_not_a_declared_entity`
      （裸主体今天仍可落账，它断言的是边界而不是"已做到"）。
