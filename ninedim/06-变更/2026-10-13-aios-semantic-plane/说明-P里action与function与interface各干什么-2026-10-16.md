# 说明：**P 里 action／function／interface（＋「能力」）各干什么** —— 逐字罗列（2026-10-16）

> ★ **作者问（逐字）**：「**action 和 function 它们俩的逻辑关系是什么？它们俩分别要干什么事儿？还有那个接口和能力，他们是干什么？你来罗列一下**」。
> ★ 本件**逐字现取**：P（`foundry-ontology-open`）的 `docs/architecture.md` ＋ `core/{action_type,function,interface,ontology}.py`。

---

## §一 ★★★ P 自己的三层模型（`docs/architecture.md` 逐字）

> 「foundry-ontology-open follows Palantir Foundry's **three-layer Ontology architecture**」

| 层 | 逐字：里面有什么 |
|---|---|
| ★ **Semantic Layer**（语义层） | `ObjectType`: Schema for entities (Asset, Technician, etc.) ｜ `Property`: Fields with types ｜ `LinkType`: Typed relationships with cardinality ｜ ★★ **`Interface`: Polymorphic shapes implemented by multiple ObjectTypes** |
| ★★ **Kinetic Layer**（动能层） | ★ **`ActionType`: Executable actions with parameters, validation rules, and effects** ｜ ★ **`OntologyFunction`: Server-side business logic (e.g., get_high_risk_assets)** ｜ `ActionExecutor`: **Runs actions with validation and audit** ｜ `ValidationRule`: **Python expressions evaluated at runtime** |
| ★ **Dynamic Layer**（动态层） | `Roles & Permissions`（RBAC）｜ `Markings`（PUBLIC／INTERNAL／CONFIDENTIAL）｜ `AuditLog`: **Immutable trail of all actions** |

★ **Data Flow 五步（逐字）**：★ ① Define Ontology (schema) → ② Create instances in ObjectStore → ③ Query via OntologyQuery → ④ ★ **Execute actions via ActionExecutor** → ⑤ Export to OWL／SHACL。

---

## §二 ★★★ 三件各干什么（逐字 ＋ 字段）

### 1. `Interface`（**语义层**·不是能力）

| 项 | 现取 |
|---|---|
| ★ 自述（逐字） | ★「**Shared shape that multiple ObjectTypes can implement.**」（`interface.py:14`） |
| ★ 字段 | ★ `interface_id`／`display_name`／`description`／★ **`required_properties: list[Property]`** |
| ★ 方法 | ★ `check_compliance(object_type) -> bool`（★ 检查某 ObjectType 是否具备全部必需属性）｜★ `get_implementors(ontology) -> list[ObjectType]` |
| ★★ **它管什么** | ★★ **「谁长得像这个形状」** —— ★ **对象的形状契约**；★ **与「能做什么」无关** |

### 2. `ActionType`（**动能层**·改世界那一类）

| 项 | 现取 |
|---|---|
| ★ 自述（逐字） | ★「**An action that can be executed with validation and effects.**」 |
| ★ 字段 | ★ `action_id`／`display_name`／`description`／**`parameters: list[ActionParameter]`**／**`validation_rules: list[ValidationRule]`**／**`effects: list[ActionEffect]`**／**`required_roles: list[str]`**／**`audit_enabled: bool = True`** |
| ★ 方法 | ★ `validate(context)`（★ 查必填参数 ＋ 逐条跑 rules）｜★ `describe()`（★ 逐字「**JSON-serializable description for agents**」） |
| ★★ **它管什么** | ★★ **「一件可执行的事」**：★ 要什么参数／什么条件下不许做／做完**世界怎么变**（`effects`）／谁有权（`required_roles`）／要不要审计 |

### 3. `OntologyFunction`（**动能层**·算值那一类）

| 项 | 现取 |
|---|---|
| ★ 自述（逐字） | ★「**Server-side business logic — equivalent to Foundry's @Function() decorator.**」 |
| ★ 字段 | ★ `function_id`／`display_name`／`description`／**`input_types`**／**`output_type`**／**`implementation: Callable`** |
| ★ 方法 | ★ `execute(**kwargs)`（★ 逐字：★ 没有实现就 `raise RuntimeError`）｜★ `describe()`（★ 逐字「**for MCP tool listing**」） |
| ★★ **它管什么** | ★★ **「一段服务端逻辑」**（★ 输入 → 输出）；★ **它不改本体、不落审计** |

---

## §三 ★★★ 三者的**逻辑关系**（★ 这是你问的）

```
★ Semantic Layer（语义层）—— 管「世界里有什么」
   ObjectType ──► LinkType（对象之间的边）
   Interface  ★ 多个 ObjectType 共同实现的形状（required_properties）
        │
        │ ★ 关系：Interface 是【对象的形状】，不是【能做的事】
        ▼
★ Kinetic Layer（动能层）—— 管「能做什么」
   ┌─ ActionType      ★ 改世界那一类：parameters／validation_rules／effects／required_roles／audit
   └─ OntologyFunction ★ 算值那一类：input_types／output_type／implementation
        ★★ 两者【并列】，【不互指】—— ActionType 里没有 function_id，Function 里没有 action_id
        │
        ▼
   ActionExecutor  ★ 只执行 ActionType（validation ＋ effects ＋ audit）
   ★★★ 它【不执行】OntologyFunction（★ 逐行 grep：0 处）
```

★★★ **三句话说完**：

| # | 关系 | 逐字／现取依据 |
|---|---|---|
| **1** | ★★ **Interface 在语义层，与「能做啥」无关** | ★「**Shared shape** that multiple ObjectTypes can implement」；★ 字段只有 `required_properties` |
| **2** | ★★★ **ActionType 与 Function 同在动能层，但并列、不互指** | ★ 两边的字段**没有对方的名字**（★ 我逐字核过） |
| **3** | ★★★ **两者在「有没有副作用／落不落审计」上分开** | ★ ActionType 有 `effects` ＋ `ActionExecutor`「**with validation and audit**」；★ Function **两者都没有**（★ 且只有测试在调） |

---

## §四 ★★★ 「能力」（capability）—— **P 里 0 命中**

| 项 | 现取 |
|---|---|
| ★ P 全树 `.py`／`.md` 里 `capabilit`／「能力」 | ★★ **0 次**（★ 我逐件 grep 过） |
| ★★ 结论 | ★★ **「能力」这个词是【我方】的，不是 P 的** |

### §四·1 ★★ 我方拿 P 的哪一格当了「能力」

| 我方 | 现取 | 对应 P 的哪一格 |
|---|---|---|
| `actions.<名>.capability` | ★ 每个动作**必须引用一个能力** | ★ 疑似 `Interface`（★ 我方 `interfaces` **9 条**） |
| `interfaces` | ★ **9 条**，与 `actions` 九条**名字一一相同** | ★ 照 P 的 `Interface` 抄的形状（★ `_照谁` 有记） |

★★★ **而我方自己早就登记过这个洞**（`actions._declared_gaps` ⑤ 逐字）：

> ★「本节九条与 `interfaces` 九条**名字一一相同** ⇒ 『动作引用一个已声明的能力』在出厂法律里是**零信息边**。」

⇒ ★★ **所以：「能力」在我方今天是一条「零信息的边」** —— ★ 名字一一对应，★ **引用了等于没引用**（★ 判不出任何东西）。

---

## §五 ★ 一张对照表（P ↔ 我方）

| P 的件（逐字） | 在哪一层 | ★★ 我方对应的 | 现取 |
|---|---|---|---|
| `ObjectType`／`Property` | 语义 | ★ `objects`（9 类） | ★ 有 |
| `LinkType`（关系＋基数） | 语义 | ★ `links` | ★ 有（★ 判据 C7 查引用完整性） |
| ★ `Interface`（形状） | 语义 | ★ `interfaces`（9 条） | ★ 有，★ **但被当成了「能力」** |
| ★ `ActionType`（改世界） | 动能 | ★ `actions`（9 条） | ★ 有 |
| ★ `OntologyFunction`（算值） | 动能 | ★ `functions.entries`（9 条） | ★ 有（★ **但只收入口名，不带 implementation**） |
| `ActionExecutor` | 动能 | ★ **执行器** | ★★ **不存在**（我方只有 `Executor` trait ＋ `DryRun`） |
| `ValidationRule`（Python 表达式，运行时 eval） | 动能 | ★ `validation_rules` | ★ **我方裁定不抄**（★「要**形式可判**，不是能推理」）⇒ **九个动作全是 0 条** |
| `Markings`（三级） | 动态 | ★ `governance.markings` | ★ 有（★ 且有 `ceiling_by_role`） |
| `Roles & Permissions` | 动态 | ★ `governance.roles` ＋ `permissions.grants` | ★ 有（★ **生产侧无读者**） |
| `AuditLog`（不可变） | 动态 | ★ `engine/ledger.rs` | ★ 有（★ **只追加、全在内存**） |

---

## §六 本件不能证明的事（如实）

- ★ **`interface.py`／`action_type.py`／`function.py`／`docs/architecture.md` 四件都读了**（★ 分别是 42／101／39／42 行）；★ **`object_type.py`（143 行）与 `ontology.py` 后半未读完**；
- ★ **「P 里 capability 0 命中」是对 `.py`／`.md` 的 grep 结果**（★ 不含 `exported/*.ttl` 那两个 OWL/SHACL 文件）⇒ ★ 若要更严，**得把那两个也扫**；
- ★ **「我方 capability 疑似对应 P 的 Interface」是推的**（★ 依据：我方 `interfaces` 九条与动作同名 ＋ `_照谁` 说照 P 抄）⇒ ★ **待你裁**；
- ★ **「零信息边」那句是【我方本体自己】写的**（★ `_declared_gaps`），★ **不是 P 说的**；
- ★ **本件没改代码、没跑构建**（★ `check.py` 现取 **C1–C14 rc=0**）。
