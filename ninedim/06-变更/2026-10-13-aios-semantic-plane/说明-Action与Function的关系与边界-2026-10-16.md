# 说明：**Action 与 Function 的关系、以及边界划在哪**（2026-10-16）

> ★ **作者问（逐字）**：「**Function 和 action 的关系，和它 function 和 action 的这个边界划分**」。
> ★ **一句答**：★★★ **边界就一条：有没有 `effects`（副作用）。** ★ 有 ⇒ **Action**；★ 没有 ⇒ **Function**。

---

## §一 ★★★ 边界表（逐维度 · 每条给依据）

| 维度 | ★★ `ActionType` | ★★ `OntologyFunction` | 依据 |
|---|---|---|---|
| **有没有副作用** | ★★ **有** —— `effects` | ★★ **没有** —— 字段里**没有** effects | ★ 字段对照（`action_type.py` vs `function.py`） |
| **改不改世界** | ★ **改**（`effects` 就是「世界怎么变」） | ★ **不改**（`execute()` 只返回一个值） | ★ `docs/architecture.md`：★ Action = "…**and effects**"；★ Function = "**business logic**" |
| **谁执行** | ★ **`ActionExecutor`** | ★ **`OntologyFunction.execute()`**（★ 谁调都行） | ★ `ActionExecutor` 逐行 grep：★ **0 处**提到 function |
| **落不落审计** | ★★ **落**（`audit_enabled=True`；返回里有 `audit_entry_id`） | ★★ **不落**（字段里没有 audit） | ★ `ActionResult{success, action_id, effects_applied, validation_errors, **audit_entry_id**, timestamp}` |
| **谁有权** | ★ 有 **`required_roles: list[str]`** | ★★ **没有**（无权限字段） | ★ 字段对照 |
| **参数校验** | ★ 有 **`validation_rules`**（执行期 `eval()`） | ★★ **没有**校验 | ★ `tests/test_function.py:31` 逐字承认：「(Execution **does not auto-validate types**; the impl would fail if wrong)」 |
| **返回什么** | ★ `ActionResult`（success／effects_applied／validation_errors／audit_entry_id） | ★ **一个值**（`output_type`；★ `implementation` 的返回值） | ★ 两件的方法签名 |
| **对外的面** | ★ `describe()` 逐字「**description for agents**」 | ★ `describe()` 逐字「**for MCP tool listing**」 | ★ 两处 docstring |
| ★★ **MCP 里暴露成什么** | ★★ **有工具** `execute_action`（★ 走 `executor.execute(...)`） | ★★★ **没有对应工具** | ★ 我读完了 `mcp_server.py` **全 103 行**：★ 工具只有 `list_object_types`／`search_objects`／`get_object`／`get_linked_objects`／**`execute_action`**／`list_actions`／`describe_ontology` ＋ 一个 resource —— ★ **没有 `execute_function`** |

---

## §二 ★★★ 一句话判据（★ 一眼分开）

> ★★★ **有没有 `effects`：有 ⇒ Action；没有 ⇒ Function。**

★ 展开成**三问**（★ 这是「该做成哪个」的实用判断法）：

| # | 问 | 是 ⇒ |
|---|---|---|
| **1** | ★ 做完，**世界变了吗**？ | ★ **Action** |
| **2** | ★ 要不要**留痕**（谁批的、谁做的）？ | ★ **Action** |
| **3** | ★ 要不要**权限**（谁配做）？ | ★ **Action** |
| ★ | ★ **三问全否** | ★★ **Function** |

★ **用 P 那个例子的两个东西试一下**：

| 东西 | 三问 | ★ 所以它是 |
|---|---|---|
| ★ `EscalateAsset`（升级一台资产） | ★ 世界变了（`MaintenanceEvent` 状态 → completed）／要留痕／要权限（Technician、Engineer） | ★★ **Action** ✓ |
| ★ `get_high_risk_assets`（列出高风险资产） | ★ 世界没变／不用留痕／不用权限 | ★★ **Function** ✓ |

---

## §三 ★★★ 两者**关系**：P 里是「**并列、互不指**」

| 证据 | 现取 |
|---|---|
| ★ `ActionType` 的字段里**没有** `function_id` | ★ 字段：`action_id`／`display_name`／`description`／`parameters`／`validation_rules`／`effects`／`required_roles`／`audit_enabled` |
| ★ `OntologyFunction` 的字段里**没有** `action_id` | ★ 字段：`function_id`／`display_name`／`description`／`input_types`／`output_type`／`implementation` |
| ★ 两者**不在一条执行路径上** | ★ `ActionExecutor` 只跑 ActionType（★ 逐行 grep 0 命中） |
| ★ 但**都在动能层**，★ 且**都靠 `register_*` 登记** | ★ `o.register_action_type(...)`／`o.register_function(...)` |

★★ **所以 P 里它们的关系是**：★ **同层的两种「可调用物」，各走各的路** —— ★ **不是「一个调用另一个」，也不是「一个包装另一个」。**

---

## §四 ★★★ 我方与 P 的**真差别**（★ 这条最要紧）

| | ★ P | ★★ 我方（现取） |
|---|---|---|
| Action 与 Function 的对应 | ★★ **互不相干**（★ `get_high_risk_assets` 与任何 action 都无关） | ★★★ **一一对应**：★ 9 个动作 ↔ 9 个函数，★ **且 `actions.<名>.function` 指向它**（★ 9/9） |
| Function 是什么 | ★ **独立的业务逻辑**（★ 自己算自己的） | ★★ **Action 的「实现入口名」**（★ 命名即 `fn.<动作名>`；★ 本体逐字：★「只收入口名（**引用到底层函数**）」） |
| 谁调它 | ★ 谁都能调（★ 生产侧只有测试在调） | ★ **执行路径上**：★ `execute.rs:21-23` 逐字「**真调 `functions.call(function_id, params)`** ⇒ 逐条校入参也在这里做了」 |

★★★ **一句话**：★ **P 的 Function ＝「另一类可调用物」；★ 我方的 Function ＝「每个动作的实现入口」。**
★ 这解释了为什么我方那 9 条**全叫 `fn.<动作名>`** —— ★ **它们不是独立的业务逻辑，是动作的下半截**。

### §四·1 ★ 那要不要向 P 靠（★ 待你裁）

| 选 | 含义 | 代价 |
|---|---|---|
| **甲：保持一一对应**（现状） | ★ 每个动作有一个实现入口，★ 简单、可判（★ 缺入口 ⇒ 红） | ★ **表达不了「独立的算值逻辑」**（★ 例如「列出高风险资产」这类没有副作用的查询，今天只能硬塞成一个动作） |
| **乙：分成两类**（照 P） | ★ 动作＝改世界；★ 函数＝算值；★ **两者互不指** | ★ 要**动本体**（★ 现有 9 条函数要重新归类）；★ 且**查询类的东西今天没有出路**（★ 它们既不改世界，又要能被调用） |
| **丙：两者都留，动作可选挂函数** | ★ 动作**可以**引用一个入口名（★ 现有 9 条即此）；★ **另有**独立的算值函数 | ★ 本体要加一个「独立函数」的标记；★ 判据要能分开两类 |

★ **我倾向丙**（★ 但这是**我倾向**，不是结论）：★ 因为★ **今天那 9 条确实是动作的实现入口**（★ `_element` 逐字「引用到底层函数」），★ 而★ **「列出高风险资产」那类东西**在我方**确实没有出路** —— ★ 它既不该造一个「假动作」，★ 也不该塞进某个动作里。

---

## §五 本件不能证明的事（如实）

- ★★ **边界表那九行是【归纳】**（★ 依据＝两件的字段 ＋ `architecture.md` 的措辞 ＋ `ActionExecutor` 的 grep）；★ **P 自己没有一句话写「边界是 effects」** ⇒ ★ **这句话是我总结的**；
- ★ **`mcp_server.py` 我读完了 103 行**（★ 两次读：1–50 ＋ 50–103）⇒ 「没有 `execute_function`」这条**是全文核过的**；
- ★ **「P 的 function 只有测试在调」**：★ 我 grep 过 `fn.execute(`（★ 只在 `tests/test_function.py`）⇒ ★ 但 **`cli.py`／`query_engine.py`／`export/*` 我没逐行读** ⇒ ★ 射程有限；
- ★ **§四·1 的甲／乙／丙是我提的三个选项** ⇒ ★ **要不要动本体，只有你能定**；
- ★ **本件没改代码、没跑构建**（★ `check.py` 现取 **C1–C14 rc=0**）。
