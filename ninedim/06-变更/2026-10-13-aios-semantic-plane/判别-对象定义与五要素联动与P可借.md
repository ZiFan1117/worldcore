# 判别：我们 25 类的定义到底缺什么 ＋ 五要素联动现状 ＋ 从 P 能借什么

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 ／ 六 规格 | **0.1** |

> **件性质**：**详细判别件** —— 只出读数与判词；**处置不代签**。
> **作者令（逐字）**：「这个东西再详细地判别一下……**之前对象的定义有没有那个那啥的需要**……**5 个要素在弄个体的时候……一起弄**……**你还要发现一些东西**……**参考一下 P 那个开源的那个库里面，不是有一些更丰富的枚举什么的那些策略啊，我们也借鉴他**。」

---

## §一 ★★ 我们 25 类自己的定义：哪里缺（逐项读数）

| # | 发现 | 读数 | 判 |
|---|---|---|---|
| **1** | ★★ **字段元数据「有位置、没内容」** | `_field_meta` 共 **139** 条；★ **三位（`required`／`options`／`is_primary_key`）全 `null` 的 = 93**；★ **有 `required` 的 = 0** | ★ **必填/主键/选项一律没填** ⇒ 这是"我们原有对象定义最缺的一格" |
| **2** | ★ **`_field_meta` 形状不纯** | 139 条里 ★ **38 条的值是字符串**（例：`notice._照谁`／`notice._P 的 Property 有八样`）—— **说明性键与字段名混在同一个字典里** | ★ **遍历时会踩到非字段键**（本席写审计脚本时**当场被它绊倒**：`AttributeError: str has no attribute get`）⇒ 该分家 |
| **3** | ★ **7 个"元类"没有互斥表** | 缺 `disjointWith` 的 = `record`／`capability`／`action`／`permission`／`clock`／`unit`／`identity` | ★ 这 7 个**正是与本体自己的分节对应的元类** |
| **4** | ★ **新旧互斥表口径不一** | 既有 19 类：**12 类有 5 个**；★ 新补 6 类：**一律 6 个** | ★ 同一种东西两个数 ⇒ 须统一 |
| **5** | ★★ **新 6 类与其余四要素零联动** | `project`／`file`／`memory`／`model`／`package`／`config`：**关系边=无；`_interfaces`=False；`_actions`=False；`_functions`=False** | ★★ **这正是「五要素要一起弄」的反证** |

## §二 ★★ 与上游/P 一对照：**它有三样比我们"实"**

| 项 | 上游 `Object` 外壳 | 我们 | 判 |
|---|---|---|---|
| `created_at`／`created_by` | **有实值**（每条对象必带） | ★ 只有 `record.at_time`／`who`，**类级公共格缺** | ★ **它实** |
| `privacy_class` | **有实值**（5 级，默认 `Sensitive`） | ★ **完全没有** | ★ **它实** |
| `scope_binding` | **有实值**（SYSTEM/GROUP/USER ＋ id） | ★ **完全没有** | ★ **它实** |
| `metadata` | 有，但**上游自己规定永远非权威** | — | ✓ 一致 |
| `current_pointer_id` | 有（**指针＝它的事实源**） | ★ 我们口径「个体由本体得出、账本只是记录」 | ★★ **冲突：不进我们语义面** |

## §三 ★★ 从 P（`foundry-ontology-open`）能借什么 —— 逐项（**这是"更丰富的枚举与策略"的所在**）

| # | P 里有什么（逐字/现取） | 我们现状 | 可借什么 |
|---|---|---|---|
| **1** | ★ **`PropertyType` 13 类**：`STRING`／`INTEGER`／`FLOAT`／**`DECIMAL`**／`BOOLEAN`／**`DATE`**／**`DATETIME`**／**`TIMESTAMP`**／**`GEOHASH`**／**`GEOSHAPE`**／**`ATTACHMENT`**／★ **`MARKING`**／★ **`OBJECT_REFERENCE`** | 我们用 `string`／`integer`／`bool`／`number`／`ref(...)`／`array(string)`／`enum(...)` —— ★ **日期/时间不分、没有附件、没有密级类型** | ★ **借类型系统**（尤其 DATE/DATETIME/TIMESTAMP 三分、ATTACHMENT、MARKING） |
| **2** | ★★ **`ValueType`**（逐字 `Semantic wrapper around PropertyType with metadata and constraints`，带 `constraints` ＋ **`validate(value)`**） | ★ 我们的 `_field_meta` 是**空壳**（§一-1） | ★★ **借"语义包装＋约束"** ⇒ **正是空壳的解法** |
| **3** | ★ **`governance/markings.py`**：`Marking{marking_id, level（越高越受限）, display_name}`（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED） | ★ **我们没有密级** | ★ 借 MLS（★ 比上游硬编码 5 级 `PrivacyClass` **更可扩展**） |
| **4** | ★ **`governance/roles.py`**：`Permission{permission_id, display_name, scope}`／`Role{role_id, …, permissions}`／`User{user_id, roles, markings}` | 我们只有 `permission{who,what,scope}` ＋ `_permissions.default=deny` | ★ 借 **RBAC**（`Role` 作为对象类；`User.markings` 把密级与角色接上） |
| **5** | ★★ **`PermissionCheck.can_execute` 逐字：`if not action_type.required_roles: return True`** | ★ **我们 `_permissions.default = deny`** | ★★ **冲突：P 默认放行（动作没写角色＝人人可做）** ⇒ **借形状、改默认**（第二处"默认方向相反"，第一处是上游 runtime 不挂 kernel） |
| **6** | ★ **`engine/audit_log.py`**：`AuditEntry{entry_id, timestamp, action_type_id, executed_by, parameters, effects, success, error_message}` | 我们 `record{of_kind, at_seq, at_time, who}` | ★ 借 **"动作／参数／结果／错误"四格** ⇒ 账本条就能回答"这次动作成没成" |
| **7** | **`engine/object_store.py`**(9 KB)／**`query_engine.py`**(4.6 KB)／**`action_executor.py`**(6.6 KB) | 我们/上游各有自己的实现 | ★ **对照件**（未读，属下一笔） |
| **8** | **`export/shacl_generator.py`**／`owl_exporter.py` | ★ 我们 **B-3**：只导出、不推理 | ★ **一致** ✓（可借它的导出形状，但**不引运行时**） |

## §四 五要素联动现状（把"一起弄"变成一张矩阵）

| 类 | `_objects` | `_links`（边） | `_interfaces`（能力） | `_actions`（动作） | `_functions`（函数） |
|---|---|---|---|---|---|
| 既有 19 类 | ✅ 有 | 部分（17 条边连到部分类） | 9 个能力 | 9 条动作 | 9 条函数 |
| ★ **新 6 类** | ✅ 有 | ★ **无** | ★ **无** | ★ **无** | ★ **无** |

⇒ ★ **所以"一起弄"要补的是**：给新 6 类（以及将来每一类）**同时**给出**边／能力／动作／函数**；**只补对象类 = 只补五分之一**。

## §五 本笔没做的事（如实）

1. **没有改任何数据**（判词与可借清单都只到"发现"；处置待人裁）；
2. **P 的 `engine/object_store.py`／`query_engine.py`／`action_executor.py` 未读**（只列名）；
3. **没估**"把 93 条 `_field_meta` 填实"的代价；
4. ★ **本席的一处失误如实登记**：审计脚本第一版**被 §一-2 的形状不纯绊倒**（`AttributeError: str has no attribute get`）⇒ 那 38 条字符串值**是脚本报错才暴露出来的**（意外收获）。
