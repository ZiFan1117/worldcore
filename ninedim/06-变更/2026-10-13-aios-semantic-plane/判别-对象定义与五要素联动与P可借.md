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
---

## §六 ★★ 那四处"待裁"到底是什么性质（作者问："是要我做决策吗？是和人家的库有冲突吗？这是定义的个体类型吗？"）

### 六.1 先立一个词：什么叫"定义个体类型"

> ★ **`_objects` 里的一类 ＝ 一种「个体类型」**（例：`notice` 是**类型**；一条具体的通告是它的一个**个体**）。
> ⇒ ★ **"定义个体类型" ＝ 决定「这个世界里允许存在哪几种东西」** —— 这是**世界观**，不是技术选型。

### 六.2 那四处的性质：**不是冲突，是"我们自己的边界没定"**

| 性质 | 例子 | 说明 |
|---|---|---|
| ★★ **真冲突（方向相反）** | `current_pointer_id`（**指针＝事实源** vs 我们"个体由本体得出、账本只是记录"）／P 的 `can_execute` **默认放行** vs 我们 `default = deny`／上游 runtime **不挂 kernel 就放行** | ★ **这几处必须按我们改** |
| ★ **不是冲突：我们内部的概念边界** | ① `project↔job` ② `memory↔record` ③ `package↔application/service` ④ `config` 算不算个体 | ★ **上游/别人的库对这些「什么都没说」**（它的类没有定义、没有关系边、没有约束）⇒ **不存在"和它冲突"，只存在"我们自己没定"** |
| **可借（补强）** | P 的 13 类字段类型／`ValueType`／`Marking`／`Role`／`AuditEntry` | 不是冲突 |

★★ **所以：这四处要你拍，不是因为"人家那样、我们这样"，而是因为「只有人能定正式结论」（硬约束 6），而它们恰好是世界观。**

### 六.3 逐件：问题是什么、两个选项、选错的后果

| # | 一句话问题 | 甲选项 | 乙选项 | 选错的后果 |
|---|---|---|---|---|
| **①** | **"项目"和"活计"是两种东西，还是同一种（一大一小）？** | **同一种** ⇒ 删掉 `project`，把上游 `Project` 的语义并进 `job`（我们只剩 24 类） | **两种** ⇒ 留 `project`，★ 并**必须加一条边**（`project` —包含→ `job`），否则两个类互不相干 | 若"两种但没边" ⇒ ★ **建出来的项目与活计谁也不管谁**（这就是"五要素没联动"的活样本） |
| **②** | **"记住什么"和"记录发生了什么"是两种吗？** | **同一种** ⇒ 并入 `record` | ★ **两种**（客观记录 vs 主观记忆）⇒ 留 `memory`，★ 但**必须让它引用 `record`**（它已带 `at_seq`） | 若 `memory` 变成"第二个事实源" ⇒ ★ **违背"账本只是记录"** |
| **③** | **"装的东西（包）"和"跑的东西（应用/服务）"是两种吗？** | 合并 | ★ **两种**（一个包可装出 0..N 个服务；一个服务可来自多个包）⇒ 留 `package` ＋ **加边**（`package` —提供→ `application`/`service`） | 若合并 ⇒ ★ **"装了但没跑"这件事就说不清** |
| **④** | ★★ **"配置"算不算一个「东西」？**（能在世界里被指着说"这就是那个配置"） | ★ **不算** ⇒ 配置**只是账本里的一串 `change` 事件**（读出来才知道现值）⇒ 删 `config` 类 | ★ **算**（有身份、可被引用、可被授权）⇒ 留 `config`，其字段值由事件折出 | ★ 甲则"配置"没有名分、不能被权限管；乙则**多一种个体类型**（世界变宽） |

★ **我的判读（供参考，不是结论）**：
- ① ★ **看用途**：若"一个项目下多个活计"真实存在 ⇒ 乙（留 `project` ＋ 加边）；若我们的世界只需要"活计" ⇒ 甲（删）。
- ② ★ **倾向乙**（两种）：`record` 是**客观记录**、`memory` 是**主观记忆**；★ 但**必须有一条 `memory` → `record` 的边**。
- ③ ★ **倾向乙**（两种）：上游自己也是 `Package` 与 `Application` **分着**的 ⇒ ★ **我们分开与它一致**；★ 缺的只是那条边。
- ④ ★★ **这一件才是真需要你拍的**：★ **它不是"和谁冲突"，是"这个世界里要不要有『配置』这种个体"**。
  ★ 我的判读：**乙（算）更合我们口径** —— 我们的 `notice`／`job` **也都是"由本体给出类型与形状、其状态从账本事件读出来"的个体**；
  「**个体由本体得出**」与「**账本只是记录**」两者不矛盾（★ 个体**不是**账本的派生物，但它的**当前值**是从事件里读出来的）⇒ **`config` 可以是合法的个体类型**。

### 六.4 ★ 反过来：真正"和人家冲突"的只有三处（那三处**不必你选**，按我们改即可）

| # | 冲突 | 处置 |
|---|---|---|
| 1 | 上游 fs **不认识的对象类型静默降级成 `File`** | ★ 改成**拒**（T-30） |
| 2 | 上游 runtime **不挂策略核就放行** | ★ **强制挂载**（判据 C5 已立，现状 10 件已登记） |
| 3 | P 的 `can_execute` **默认放行**（动作没写角色＝人人可做） | ★ **借形状、改默认**（我们 `default = deny` 不动） |
---

## §七 ★★ 已按令补齐 / 借入（本笔执行，四要素在下）

| # | 补什么 | 读数 |
|---|---|---|
| **1** | ★ **101 个字段全部补 `base_type`**（照 P 的 `ValueType`：`name + base_type + constraints + validate`） | 填了 **101** 条 |
| **2** | ★ **借入 P 的 `PropertyType` 13 类**（新节 `_property_types`） | 13 类；★ **有用的 6 类**；★ **今天没用上的 7 类**：`DECIMAL`／`DATE`／`DATETIME`／`GEOHASH`／`GEOSHAPE`／`ATTACHMENT`／`MARKING` |
| **3** | ★★ **两处"我们比 P 宽"（如实）** | ① `enum(...)` —— ★ **P 没有 ENUM**（我们用 `STRING + constraints{options}` 顶上）；② ★ **`array(string)` —— P 的类型系统根本没有数组** |
| **4** | ★ **互斥口径统一**（新节 `_disjoint_policy`） | 口径：**本体的类两两互斥**；`disjointWith` 只是**逐类投影**；★ **未列即互斥** ⇒ 「7 个元类缺表」**不再是缺口**（那是按口径省略，已逐类显式标注 `_disjoint_note`） |

**读数（四要素）**：`cd /root/aios && CARGO_TARGET_DIR=/root/.ct-fs cargo test -p aios-ontology --offline` ⇒ `test result: ok. 8 passed; 0 failed` ⇒ **rc=0** ⇒ 2026-10-13（VM `leap16`）。

---

## §八 ★★★ 世界观提案：**这个世界该有哪几类东西**（作者问「你认为哪几类东西吗？别人也提出了自己的想法」）

### 八.1 我的提案：按"东西的角色"分**六组**（26 类）

| 组 | 类 | 为什么在一组 |
|---|---|---|
| ★ **① 发生**（occurrent：有始有终） | `notice`／`job`／`action`／`workflow` | 都是"会发生、会结束"的东西 |
| ★ **② 记录**（信息内容：被保存/被引用） | `record`／`memory`／`file`／`model`／`package` | 都是"存下来、可被引用"的东西 |
| ★ **③ 主体**（谁） | `human`／`agent`／`identity`／`permission`／`capability` | "谁能做什么" |
| ★ **④ 使能**（零件与刻度） | `application`／`service`／`device`／`port`／`clock`／`unit` | "让它跑起来的东西" |
| ★ **⑤ 界面**（给人看的） | `surface`／`cell`／`presence` | "看得见的" |
| ★ **⑥ 容器/归属** | `project`／`config` | "把别的圈起来" |

★ **`config` 在提案里归「⑥ 容器/归属」** ⇒ ★ **意味着我支持它是个体（乙）**：它圈住的是"某作用域下的一组值"。
★ **`project` 归「⑥ 容器」** ⇒ ★ 它**天然该有一条包含边**（`project` —包含→ `job`）⇒ ★ 这正是"五要素联动"里缺的那条。

### 八.2 ★ 对照"别人的想法"（三类，性质完全不同）

| 来源 | 它给的是什么 | 拿它当"世界观"会怎样 |
|---|---|---|
| **上游 AIOS-FS（10 个抽屉）** | **按"存储用途"凑的 10 类**：`Project`／`Application`／`File`／`Memory`／`Policy`／`Model`／`Package`／`EvidenceRef`／`Workspace`／`Config` | ★ **它的世界比我们窄**：我们 25 类里 **18 类它一个都没有**；★ 而且它那 10 个里有 **3 个其实不是"东西的种类"而是"角色"**：`Policy`＝我们的 `_permissions` 那一节、`EvidenceRef`＝`record` 的一个用法、`Workspace`＝`surface` |
| **P（`foundry-ontology-open`）** | ★ **元模型**：`ObjectType`／`LinkType`／`ActionType`／`OntologyFunction`／`Interface`（＋`ValueType`／`Marking`／`Role`） | ★ **它给"怎么描述"，不给"有什么"** ⇒ ★ **不能拿它当名单**；★ **但它的形状（尤其 `ValueType` 的约束面、`Marking` 的密级、`Role` 的 RBAC）可以整块借** |
| ★ **BFO**（我们 `_meta.anchor` 用的） | **顶层范畴**：`continuant`／`occurrent`／`process`… | ★ 正是"**发生 vs 连续体**"这个分法的出处 ⇒ ★ **我们的六组里，①发生 与 ②–⑥ 的分界就是从它来的** |

⇒ ★★ **一句话**：**上游给"存储抽屉"、P 给"描述形状"、BFO 给"顶层范畴"；★ 只有我们自己要给"名单"。**

### 八.3 ★ 附带一处发现（关于"通告算不算个体"，作者问的那个）

| 层 | 是什么 | 例 |
|---|---|---|
| **类型** | `notice`（本体的一类） | "通告"这一**类**东西 |
| **个体** | 该类型的一个实例（`instance_mode: many`） | "2026-10-13 那条通告（seq=7）" |

★ **你的直觉抓到了一处真张力，而且本体自己早登记过**：`notice._meta.definition` 逐字里有
「另有『**它是一条记录**（信息内容实体）』这一读法（判词 · 形式本体 **Y-2**）……**提案值·待裁-1**：若取那一读法，锚点应改 `BFO_0000031 generically dependent continuant`」
⇒ ★ 即：**"一条通告"在实现上就是账本里的一行** ⇒ **"那一类发生"与"那条记录"贴得极近** ⇒ ★ 这是**已挂着的待裁-1**，本件不新增结论。
