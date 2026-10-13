# 判读：`record`（记录）与 `ledger`（账本）—— 作者判断的三条现取支持

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 ／ 六 规格 | **0.1（判读·待裁）** |

> **作者原话（逐字）**：「这记忆，这个**记录也很不应该是一个单独的类**吧？它是**一个动作或者是什么**吧？那个**你要说是账本，可以说是单独的一个类，这个可以**，它就算是**文件的一种形式**吧……可能最后**整个计算机里头只有这么一处**，但是你要是说**它记录是一个，那不太行吧**。」
> **件性质**：**判读件** —— ★ 只给现取依据与判读；★ **两处待裁不代定**。

---

## §一 ★★★ 三条现取事实（支持作者判断）

### 事实一：`record` 的字段**就是账本信封的字段**（本体自己登记过改名的由来）

`_objects.record._2026-10-12_字段改名之由` **逐字**：

> 「★ **2026-10-12 改名**：本类第一版的字段是 `kind`／`seq`／`at`／`actor` —— **四个全是信封核心字段名**，Rust 装载器当场报 `ext.world.Ontology.CoreC…`」

⇒ ★★ **即：「一条记录」就是 `envelope`（账本信封）里的那一条** —— ★ **而 `envelope` 是**顶层键的格式规定**，不是「类」**。
⇒ ★ 作者说"记录不该是单独的类"，**这一条是硬依据**。

### 事实二：`record` 的锚点是「信息内容实体」

`_objects.record._meta.anchor_note` **逐字**：

> 「照形状取自 BFO 2020：**`generically dependent continuant`** —— **记录**是账本里的一行：`change`／`act`／`notice` 在实现上都是它」

⇒ ★ 它锚的是**信息内容实体**（不是独立连续体）⇒ ★ 与"世界里一个独立的东西"**不同**。

### 事实三：「账本」今天**没有名分**，却被到处引用（＝先前登记的 T-33）

| 位置 | 现取 |
|---|---|
| `_actions.ledger.compact.parameters[0].param_type` | ★ **`ref(ledger)`** —— ★ **引用了"一个不存在的类"** |
| `_functions.entries.fn.ledger.compact.inputs.subject` | ★ **`ref(ledger)`** |
| `_functions.entries.fn.ledger.compact._note` | ★ 逐字「**output_type 未定：前置名 `ledger` 不在 `_objects` 里**」 |
| `envelope.fields.seq` | ★ 逐字「integer # **在账本中的位置**，全局单增，由世界分配」 |
| `_pending_tables.clock_and_timezone` | ★ 提到「同一**账本**在任何时区折叠出同一状态」 |

⇒ ★★ **作者说「账本可以是单独的一个类」—— 这正好补上这个缺口**；★ 且"整个计算机里只有这么一处"与"**账本唯一**"**一致**。

## §二 ★★ 判读（逐项）

| 项 | 作者判断 | 现取支持 | ★ 本席判读 |
|---|---|---|---|
| **`record`（一条记录）** | ★ **不该是单独的类** | ★★ **三条事实全支持** | ★★ **撤** —— ★ 「一条记录」＝`envelope` 里的一条；★ 而 `envelope` 是**格式**不是类；★ 它的"类别"已由 `families` 承载 |
| **`ledger`（账本）** | ★ **可以是单独的类** | ★ **支持**（唯一、被引用、无名分） | ★★ **补** —— ★ 它是**唯一的那个东西**；★ 补它**顺手解决 T-33 的 `ref(ledger)`** |
| ★ 「记录是**一个动作**」 | 作者猜测 | ★ **不成立** | ★ 「记录」不是动作 —— ★ 它是**账本里的一条**（★ 动作是往账本里写的那一刻） |

## §三 ★★ 两处待裁（本席不代定）

### 待裁一：撤 `record` 后，那 **10 处 `ref(record)`** 改成什么

| 现取（10 处） | 说明 |
|---|---|
| `_actions.notice.mute/.unmute.subject`、`job.start/.finish/.cancel.subject` | ★ **5 条动作的"作用面"** 现在写 `ref(record)` |
| `_functions.fn.notice.mute/.unmute`、`fn.job.start/.finish/.cancel` 的 `inputs.subject` 与 `output_type` | ★ **5 条函数的出入类型** 现在写 `record` |

| 选项 | 做法 | 本席判读 |
|---|---|---|
| **甲** | ★ 改成 **`ref(ledger)`** | ★ **语义不对**（动作不作用在"账本"上） |
| ★ **乙** | ★ **改成"取值域"**：参数类型改为一个**非类的取值**（如 `record_kind = enum(change,act,notice,job)`） | ★★ **本席倾向** —— ★ 因为"一条记录"的类别**本来就是值** |
| **丙** | ★ **删掉这些参数** | ★ 动作就没作用面了 ⇒ ★ 不妥 |

### 待裁二：`ledger` 补进 `_objects` 时，它是什么形状

| 问 | 说明 |
|---|---|
| ★ 它有哪个"指认格"？ | ★ 若"整个计算机里只有一处" ⇒ ★ 它可能是 **`instance_mode: one`**（唯一）还是 `many`（多世界多账本）？ |
| ★ 它的字段？ | ★ 现有素材：`envelope.fields.seq`（在账本中的位置）／`ledger.compact`（压实，不可逆）／`_pending_tables.clock_and_timezone` |

★ **一并说明**：★ `instance_mode` 今天现取**全是 `many`**（11 个类），★ 若 `ledger` 是 `one`，★ 那将是**本体的第一个 `one`** ⇒ ★ 值得单独裁。

## §四 本件没做的事（如实）

1. ★ **没有动本体**（撤 `record`／补 `ledger` 都没做 —— ★ 等 §三 两处裁）；
2. ★ **没核** `instance_mode` 的取值域（★ 本体只用了 `many`，★ 有没有 `one` 的合法值未查）；
3. ★ **没估**撤 `record` 与补 `ledger` 的连带面（★ 已知 `ref(record)` 10 处、`_property_types` 4 处、`_storage_class_map` 5 处）。
---

## §五 附：「取值域」是什么（作者问过；本席补上，免得再问）

### 一句话

> ★★ **「取值域」＝ 某个空格上「允许填哪几个值」的清单。**

### 例（本仓现成的）

| 那个格 | 只能填 | 这是它的取值域 |
|---|---|---|
| `job.status` | `todo`／`doing`／`done` | 三个值（★ 已撤的 job，取值域留在 `families.job`） |
| `presence.state` | `installed`／`registered`／`running`／`stopped`／`retired` | 五个值 |
| 设备种类（上游 `DeviceClass`） | `Cpu`／`Memory`／`NetworkWifi`／…（16 个） | 十六个值 |

### ★★ 与「类」的区别（这是关键）

| | 大白话 | 例 |
|---|---|---|
| ★ **类** | ★ **名词的目录**（世界里有哪几种东西） | `human`／`device` —— 世界里有**很多个体**装在筐里 |
| ★ **取值域** | ★ **填空题的可选项**（某个空只能填这几个字之一） | `job.status` 只能填 `todo`/`doing`/`done` |

### 本仓为什么这次用「取值域」

★ 撤 `record` 之后，那 10 处原写 `ref(record)`（＝「这个参数是一条记录」）；★ `record` 不再是筐 ⇒ **不能再说"这个参数是个记录"**。
★ 但那些地方仍要填东西（★ 例如 `notice.mute` 要说清「对哪一类记录做」）⇒ ★ 那成了一个**填空题**：只能填 `change`／`act`／`notice`／`job` 之一 ⇒ ★ **这就是「改成取值域」**。
★ 一句话：★ **「一条记录」不是一个筐，它是贴在筐上的标签**；★ **标签的清单就是取值域**。

### ★ 取值域有三档（顺带说清）

| 档 | 意思 | 例 |
|---|---|---|
| **闭枚举** | 值**全列出来**，不能增加 | `enum(todo,doing,done)` |
| ★ **开值域** | 契约**允许往后加** | 上游 `RecordType`：`1..=427` ＋ **保留区 `1000..=9999`（前向增长）** |
| **带约束的值** | 类型 ＋ 约束（格式／范围） | P 的 `ValueType`（`name + base_type + constraints`；★ `_types` 抄的就是它的面） |

★ **标准对照**：★ RDF 1.1 逐字「**Literals are used for values** such as strings, numbers, and dates」＋「词法形式 ＋ datatype」—— ★ 说的就是这个「值」。

### 本笔实际写进去的（给作者看形状）

```json
_types.value_types.record_kind = {
  "base_type": "string",
  "options": ["change", "act", "notice", "job"],
  "_依据": "撤 record 后，ref(record) 的 10 处改为本取值域；四值＝families 四键"
}
```
★ 而那 10 处现在写的是内联形式：`param_type = "enum(change,act,notice,job)"`（★ 直接内联，不引新语法）。
### ★★ 补：全仓现在有 **20 个格子**带取值范围（现取）

| 在哪 | 几个 | 例 |
|---|---|---|
| ★ **对象字段** | **5** | `presence.state`＝`enum(installed,registered,running,stopped,retired)`；`port.state`＝`enum(declared,listening,retired)`；`agent.state`／`application.state`＝`enum(installed,running,retired)`；`service.state`＝`enum(running,stopped,retired)` |
| ★ **动作参数** | **5** | `notice.mute/.unmute.subject`、`job.start/.finish/.cancel.subject` ＝ **`enum(change,act,notice,job)`** |
| ★ **函数出入** | **10** | 同上 5 条函数的 `inputs.subject` 与 `output_type` |
| ★ **命名的取值域** | **1** | `_types.value_types.record_kind` |

⇒ ★ 合计 **20 个格子**；★ 其中 **5 个是"对象字段"**（★ 就是作者说的那种），**15 个是"动作参数／函数出入"**。
⇒ ★★ **所以准确说**：★ **凡是"要填值的格子"都有取值范围** —— ★ 不只是对象里的字段。

### ★ 顺带更正一处过时的话（现取）

| 位置 | 原文 | 现取 |
|---|---|---|
| `_types.value_types._本仓今天` | 「★ **一条都没有** —— 本仓没有任何具名值类型面」 | ★ **已加 1 条**（`record_kind`）⇒ 原文是"加它之前"的现取，**已更正** |
| `_types.value_types._要加` | 「在 `_` 键下加条目＋**配会红判据**；本批只建面」 | ★ **条目已加**；★★ **会红判据仍未配** —— ★ **C7 的九路射程不读 `_types.value_types`** ⇒ **本格今天无人守**（待人裁） |
