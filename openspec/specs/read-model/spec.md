# read-model Specification

## Purpose
规定"读法可以有若干份，但说法只有一份"这一层对外可核的行为：读模型必须能由账本百分之百重算、
检查点只是缓存可以随时丢弃。**它不是"唯一"的自动化检验面**——另有**摘要链**一条独立检验
（`world-core/tests/contract.rs` 的 `c19`／`c20`／`c21`，由 `check.sh` 整跑 `--test contract` 执行）。
⚠ **不把"投影同源"算作这一层的检验面**：它**只证同源、证不了同一件事**（见 `projections` 能力，书第五章判它红）。
⚠ **措辞出处**：「**唯一**自动化检验」这句原出自**流程侧** `WC-SQAP-001-v0.1.md:536`，**不是书的原话**
（书里检索 `一个真相`／`检验面` 均 0 命中）；本能力的更正依据是 `fc-2026-002-spec-revisions` 里**待并入**的条文。


**信封各格的"读得到"与"不进状态"**（`1.1` 的裁定落点；与上面那条 Requirement 的边界同口径）：

**逐格说清"不进状态"与"读得到"**（两件事一起说，否则读者会把"不进状态"读成"没人读得到"）：

| 信封格 | 为什么**不进** `state` | 它的**可读面**（读得到的那个读法） |
|---|---|---|
| `world` | 法律级**常量**（词表版本），不属于世界状态的任何一格 | **投影头部**（`world=`） |
| `id` | **逐事件**的身份；状态按 `(主体, 路径)` 折叠 ⇒ 没有处置放它 | **逐条读事件**（CLI `read` 的 JSON Lines） |
| `at` | **逐事件**的辅助量（顺序由 `seq` 决定，`at` 只作辅助）⇒ 放进状态会诱人拿它当顺序 | 同上 |
| `actor` | **逐事件**身份——"谁做的"是**账本级**的事实，不是某一格的值 | 同上 |
| `flags` | **能力旗标**：未知旗标必须**忽略** ⇒ 它不改状态 | 同上 |

- **另 5 格同样如此**：`kind`／`seq`／`body`／`to`／`trace` **不进** `state`，它们的可读面同样是**逐条读事件**——
  上表只列 `1.1` 点名的那 5 格；**判据本身不按这张表**（`c36` 的清单**从本体派生**：`required ∪ optional`，新加一格自动进判据）。
- **证据**：`world-core/tests/contract.rs::c36_every_declared_envelope_cell_is_readable_from_some_read_view`
      （逐格断言"某一读法读得到"＋同时断言"`state` 里读不到"；**两条反向验证**：把头部 `world=` 拿掉 ⇒ 该用例红；
      把 `actor` 混进状态 ⇒ 该用例红）。

## Requirements

### Requirement: 读模型是可丢弃的缓存

"现在是什么样" SHALL 由账本重算得出，SHALL NOT 作为与账本并行的第二份原件存在。
删掉读模型（及其持久形态）之后 SHALL 能从账本重算出完全一致的结果。

系统 SHALL NOT 声称"账本内容损坏一律拒绝产出"这一全称命题。
已实测的拒绝面 SHALL 被逐类写明：① 序号断裂、② 旧值说谎（`change` 的 `before` 与当前值不符）、
③ 未知事件家族。
**边界 SHALL 被如实声明**：末尾半行在进入折叠**之前**就已被账本层截掉
（`world-core/src/ledger/mod.rs:276-289`），故它**不是**读模型的拒绝面；
读模型对"解析失败的行"不承担拒绝责任。

#### Scenario: 删掉读模型后重算结果一致

- **WHEN** 记录当前读模型，删除其持久形态，再由账本重算
- **THEN** 重算结果与删除前逐项一致
- **证据**：`tests/acceptance.rs::t7_read_model_is_disposable_and_reproducible`
      —— **⚠ 原证据行括注的"（`check.sh` 步骤 ③）"写法有歧义**：仓里有两个同名脚本，
      仓根 `check.sh` 完全不碰 `world-core`（`audit.md` **L8** 后半）
      ⇒ 本 change 一律写全 **`world-core/check.sh`** 并注明步骤号；
      本节该步确实执行 `t7`（由 `world-core/check.sh` 的 **③ 三条专属验收测试**那一步执行，命令逐字
      `cargo test --locked --test acceptance -- t1_ t2_ t7_`）。

#### Scenario: 坏账本不得产出"看起来正常"的读模型

- **WHEN** 账本内容损坏（序号断裂／旧值说谎／未知事件家族）
- **THEN** 读模型拒绝产出，而不是给出部分结果
- **证据**：`tests/acceptance.rs::t8_read_model_refuses_broken_ledger`
      —— **⚠ 本证据今天只覆盖上述三类**；"末尾半行"由账本层在折叠前截掉，**不属于**本拒绝面。

### Requirement: 增量折叠等价于全量折叠

系统 SHALL 保证"逐条增量应用"与"从头全量折叠"得到同一个结果，
否则读模型就成了一本会漂移的第二本账。

#### Scenario: 增量与全量结果相同

- **WHEN** 对同一批事件分别做增量应用与全量折叠
- **THEN** 两者结果相同
- **证据**：`tests/contract.rs::c06_incremental_apply_equals_full_fold`（由 `world-core/check.sh` 第 ③b 步执行）
      —— **⚠ 本条是防线冗余的**：生产路径上缺号由账本层 `world-core/src/ledger/mod.rs:304` 先拒，
      故本断言**不构成**端到端证明。

### Requirement: 检查点是缓存，可丢弃且必须自洽

检查点 SHALL 只作为重放的加速形态存在；它 SHALL 可被丢弃而不影响正确性；
坏检查点 SHALL 被拒绝而不是被静默采用。

系统 SHALL 明确声明"自洽"的可判定含义，SHALL NOT 留作未定义词：
检查点的**核验**判据只有两项——① 快照自称的 `base_seq` 能对上账本前若干条；
② 用账本重算前 `base_seq` 条得到的指纹等于快照自称的 `digest`。

系统 SHALL 另外声明：CLI 的 `checkpoint resume` 走的是**未核验**续算路径，
其"缓存未成为第二真相"由**事后**的"续算 ≡ 全量"逐字节比对承担
（不一致即 `ResumeMismatch` 拒用），**不是**由使用前的 `verify` 承担。

检查点格式版本不符时 SHALL 拒绝使用；该约束 SHALL 有断言。

#### Scenario: 检查点可丢弃

- **WHEN** 生成检查点后再丢弃它，由账本重新重放
- **THEN** 结果与使用检查点时一致
- **证据**：`tests/contract.rs::c12_checkpoint_is_a_cache_and_disposable`

#### Scenario: 坏检查点被拒

- **WHEN** 检查点内容被破坏
- **THEN** 被拒绝
- **证据**：`tests/contract.rs::c13_bad_checkpoints_are_refused`
      —— **⚠ 其覆盖面不含"格式版本不符"这一分支**（`world-core/src/ontology_instance/checkpoint.rs:94-99`）
      ⇒ 需补断言（列进 tasks）。

### Requirement: 读模型是"一个真相"的检验面之一

读模型 SHALL 是可丢弃的缓存，"现在是什么样"由账本重算得出。

本能力 SHALL NOT 被表述为"一个真相"这条纪律的**唯一**自动化检验面：
同仓另有**摘要链核验**一条独立检验（`c19`/`c20`/`c21`/`cli02`）。
⚠ **投影同源核对（`t16`）不计入本能力的检验面**：它属 `projections` 能力，且**只证同源、证不了"两份记录说的是同一件事"**（书第五章判它红）。

系统 SHALL 声明检查点路径**已接入生产 CLI**（`checkpoint write|verify|resume`），
SHALL NOT 被表述为"v1 CLI 从不读快照"。

证据链的机械门禁 SHALL 声明其覆盖边界：`world-core/tools/doc_integrity.py` 的受控清单里
`openspec/**` **零命中**，故"改一个测试名，规格不会变红"。
该缺口 SHALL 由 `spec_bridge.py` 的对应检查承担，SHALL NOT 被读成"证据链已被机核"。

#### Scenario: 检查点路径已接入生产 CLI

- **WHEN** 查阅 CLI 的用法串与分发分支
- **THEN** 其中列出 `checkpoint write` / `checkpoint verify` / `checkpoint resume` 三条子命令，
      且 `checkpoint` 分支在 CLI 分发表里有对应项
- **证据**：`world-core/tests/cli.rs:615` 的 **`cli15_usage_lists_three_checkpoint_subcommands`**（★ 2026-09-28 订正：本条原写「**本条尚无断言**（列进 tasks）」——**那句今天不成立**，该用例 live 在册、其头注逐字「为什么单列一条：`src/ontology_instance/checkpoint.rs` 有「整册生产零调用点」的历史（`W-03` / `P-09`）」）——实现侧为 `world-core/src/main.rs`:28-30 与 `world-core/src/main.rs`:153；
      三份仍写相反陈述的受控文档为 `world-core/docs/S4-实现/WC-UT-001-v0.1.md:54`、
      `world-core/docs/S1-需求/WC-SRS-001-v0.1.md:921`、`world-core/docs/S1-需求/WC-RTM-001.csv` 第 22 行。

#### Scenario: 证据链的机械门禁不覆盖 openspec

- **WHEN** 改动 `openspec/specs/` 下某条 Scenario 的证据行所指的测试名
- **THEN** 受控文档一致性脚本**不会变红**（`openspec` 在其受控清单里零命中）；
      该改名的**可核判据由另一件承担**——见下两行的证据行
- **证据**：`world-core/tools/spec_bridge.py`
      —— 判据②（`world-core/tools/spec_bridge.py::j2_evidence`）全称判定证据行指向的函数名是否真实存在，
      其反例在 `world-core/tools/spec_bridge.py --self-test` 的反例②（证据指向 `::no_such_fn` ⇒ 必红）；
      另一半边界由 `world-core/tools/doc_integrity.py` 的受控清单里 `openspec` 零命中承担。

### Requirement: 带检查点路径的性能目标不在本基线的承诺范围内

系统 SHALL 明确声明**范围外**事项，SHALL NOT 被读成已成立：
带检查点路径的性能目标（`REQ-N-008`：走检查点续算 ≤ 全量重算的 1/2，样本 ≥ 20 次取 P95）
在本基线内**未实现、无断言**；`world-core/tests/perf.rs` 的全部用例默认 `#[ignore]`，
只在显式度量时运行。

#### Scenario: 性能目标不在本基线的承诺范围内

- **WHEN** 查阅本能力的覆盖声明
- **THEN** 写明 `REQ-N-008` 未实现、无断言，且 `world-core/tests/perf.rs` 三条用例默认不跑
- **证据**：`world-core/docs/S1-需求/WC-SRS-001-v0.1.md`:112（状态列"未实现"）
      —— 本条**今天没有断言**（"未实现"不可被断言），其载体是流程侧登记与本 change 的 `tasks.md` 范围声明。

### Requirement: 〔无号·待流程侧增补〕声明以外的字段不许落账

写入侧 SHALL 按出厂本体 `ontology.json` 的 `concepts` 校验实体与字段：**未声明的实体**与**未声明的字段** SHALL 被拒；读模型侧 SHALL 对缺格报错，SHALL NOT 静默接受。

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
- **指针（动线）**：本条**逐格**的"为什么不进 `state`／它的可读面是哪个读法"与**证据行**，见**本册 `Purpose`** 的「信封各格的"读得到"与"不进状态"」一节——从本条出发找不到证据就是动线断，故留这一行。


系统 SHALL 如实声明本条的两处边界，SHALL NOT 被读成全称成立：

- **裸主体不受约束**：`world://<名字>`（没有实体／实例那一段）今天**照样能落账**——留下它不是口径而是代价
  （既有出厂用例以这种形态写槽位，一律拒绝会把它们打红）。⇒ 书 §5.3 的"世界的边界由声明定"
  在**实体引用**这一半成立，在**裸主体**那一半**仍未成立**；
- **本段只管 `change`**：三家族里只有 `change` 改状态，`act` / `notice` 的信纸由家族必填项管；
  `notice.subject` 的语义是"这条通告关于谁"，不是"改了哪一格"，拿字段表去查它是查错了对象。

#### Scenario: 已声明的格可机械枚举，且与本体原文逐字一致

- **WHEN** 直读出厂本体的信封与三家族声明，与读法侧的清单逐项比对
- **THEN** 信封必填／可选、三家族必填、`concepts` 的实体与字段逐项相同，且本体身份（内容寻址）与出厂值一致
- **证据**：`world-core/tests/family_readmodel.rs::h07_the_declared_inventory_is_mechanically_enumerable`

#### Scenario: 缺格即报错，且点名缺的那一格

- **WHEN** 把账本某一行**已声明必填**的那一格删掉（信封的 `actor`，或家族信纸的 `request_id`）
- **THEN** 折叠被拒，错误码是 `ext.world.ReadModel.MissingCell`，错误里读出**哪一层**、**哪一格**、该层该有哪些格；
  补回那一格后结论与基线**逐字节相同**
- **证据**：`world-core/tests/family_readmodel.rs::h04_a_missing_declared_cell_is_refused_with_that_cell_named`

#### Scenario: 空清单不许被读成宽松

- **WHEN** 读法收到一份空的"已声明格"清单
- **THEN** 拒绝折叠并给出 `ext.world.ReadModel.NoDeclaredCells`，SHALL NOT 默默放行
- **证据**：`world-core/tests/family_readmodel.rs::h06_an_empty_declared_cell_list_is_not_read_as_lenient`

#### Scenario: 命令这一级也拒（缺格即报错的可执行形态）

- **WHEN** 用一本删掉必填字段 `actor` 的账本跑 `state --json`
- **THEN** `rc=2`，错误里读出 `ext.world.ReadModel.MissingCell` 并**点名** `actor`；把那一格补回去后 `rc=0`
- **证据**：`world-core/tests/family_readmodel.rs::h05_the_cli_read_path_refuses_a_missing_declared_cell_end_to_end`
      与 `world-core/tools/s1_sys_probe.sh` 的 `TC-047` ⑨

#### Scenario: 未声明的实体与字段都被拒

- **WHEN** 分别写入一个未声明的实体、一个未声明的字段
- **THEN** 两次都被拒、都不落笔，且错误里能读出**是哪个实体 / 哪个字段**没有声明
- **证据**：`world-core/tests/atom_declared_only.rs::b01_undeclared_entity_is_refused_and_nothing_lands`
      与 `world-core/tests/atom_declared_only.rs::b02_undeclared_field_is_refused_and_nothing_lands`
      —— 反"什么都拒"对照：`world-core/tests/atom_declared_only.rs::b03_declared_entity_and_field_still_land`；
      走真二进制的同一条命令：`world-core/tests/atom_declared_only.rs::b05_cli_append_of_an_undeclared_entity_is_refused`
      （断言 `rc=2` 且账本逐字为空）；
      登记在册的缺口：`world-core/tests/atom_declared_only.rs::b04_bare_subject_is_a_registered_gap_not_a_declared_entity`
      （裸主体今天仍可落账，它断言的是边界而不是"已做到"）。
