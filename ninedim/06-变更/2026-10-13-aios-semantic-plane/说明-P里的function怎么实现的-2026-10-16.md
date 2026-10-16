# 说明：**P 里的 function 是怎么实现的**（逐字现取 · 2026-10-16）

> ★ **作者问（逐字）**：「**这个 action 注册了，那那个 P 里面的那个开源代码里头，那 function 是怎么实现的呢**」。
> ★ **一句答**：★★★ **实现就是提供方自己写的一个【普通函数】，注册时用 `implementation=` 挂上去**；★★ 而★ **调用它的地方，只有测试**（★ `ActionExecutor` **不调** function）。
> ★ 本件全部**逐字现取**：`D:\Code\08-worldcore-openspec\.refs\依赖料\foundry-ontology-open\`（★ P 全树 **68 件**）。

---

## §一 ★★★ 实现怎么来（例子逐字：`examples/energy_asset_maintenance/ontology_definition.py:171-182`）

```python
# Function
def get_high_risk_assets(vibration_threshold: float, days_since_maintenance: int):
    return ["asset_1", "asset_2"]  # Simplified

o.register_function(OntologyFunction(
    function_id="get_high_risk_assets",
    display_name="Get High Risk Assets",
    description="Find assets with high vibration and no recent maintenance",
    input_types={"vibration_threshold": PropertyType.FLOAT,
                 "days_since_maintenance": PropertyType.INTEGER},   # ★★ 参数形状【手写声明】
    output_type="list",
    implementation=get_high_risk_assets,                            # ★★★ 挂上实现
))
```

⇒ ★★★ **三步**：★ ① 提供方**写一个普通函数**；★ ② 把它塞进 `OntologyFunction(implementation=…)`；★ ③ **`register_function` 登记**。
★ **同一个例子里 `register_*` 的用法（逐字）**：★ `register_object_type`×6／`register_link_type`×4／`register_interface`×1／`register_action_type`×**3**／`register_function`×**1**。

---

## §二 ★★ 谁调它 —— P 里是**两条路**（★ 而且 function 那条只有测试在走）

| 路 | 入口 | ★ 现取 |
|---|---|---|
| ★★ **动作那条** | ★ `ActionExecutor.execute(action_type_id, params, executed_by, context_resolver, executed_by_roles)` | ★ 逐字（`engine/action_executor.py:1`）：★「**Executes ActionTypes with validation, effects, and audit — the kinetic layer.**」★ 返回 `ActionResult{success, action_id, effects_applied, validation_errors, audit_entry_id, timestamp}` |
| ★★ **函数那条** | ★ `OntologyFunction.execute(**kwargs)` | ★ `tests/test_function.py:21` 逐字：★ `result = fn.execute(threshold=5.0, days=30)` |

★★★ **关键发现**：★ **`ActionExecutor` 里【0 处】提到 `function`／`implementation`**（★ 我逐行 grep 过）⇒ ★ **P 里「动作」与「函数」是两条独立的路** —— ★ **没有「动作内部去调函数」这一跳**。
★ 而★ **调用 `fn.execute()` 的地方，只有测试**：★ `tests/test_function.py` 三处；★ `examples/` 与 `engine/` 里**没有**。

---

## §三 ★★ MCP 那层怎么暴露（★ 你说「像 MCP 一样」—— 有实证）

★ `foundry_ontology/mcp/mcp_server.py` 第 1 行逐字：★「**MCP server exposing ontology as tools for AI agents.**」

```python
mcp = FastMCP(name, instructions="Ontology tools for querying and acting on object types.")
executor = ActionExecutor(ontology, store, audit)      # ★ 动作经执行器

@mcp.tool()                                            # ★★ 逐个注册成 MCP 工具
def list_object_types() -> str: …

@mcp.tool()
def search_objects(type_id: str, filters: Optional[str] = None) -> str: …
```

⇒ ★★★ **「工具由提供方自己注册」这件事，P 在 MCP 层就是这么做的** ✓✓
★ **但（如实）**：★ **函数有没有也挂成 MCP 工具，我只读到第 50 行**（★ 该件 103 行）⇒ ★★ **后 53 行未读**。

---

## §四 ★★★ 与我们的对照（★ 两处 P 的弱点，正好是我们的纪律）

| 项 | ★ P 怎么做 | ★★ 我们（口径） |
|---|---|---|
| 实现放哪 | ★ **挂在 `OntologyFunction` 上**（★ `Callable`） | ★★ **不进本体**（★ 逐字「**代码不进本体**」；★ `_no_command_literal` 有判据） |
| 参数形状 | ★★ **注册时【手写声明】**（★ 与实现签名**两处**） | ★★ **在本体 `inputs`**（★ 一处） |
| 对不上怎么办 | ★★ **没人管** —— ★ `tests/test_function.py:31` 逐字括注：★「(Execution does not auto-validate types; the impl would fail if wrong)」 | ★★ **要有判据**（★ 这是我们的活） |
| 身份 | ★★ **`executed_by`／`executed_by_roles` 是【调用方传进来的参数】** | ★★ **身份不许自填**（★ 我方纪律） |
| 谁调 function | ★ **只有测试**（★ `ActionExecutor` 不调） | ★ 我方 **`functions.call` 已在执行路径上**（★ `execute.rs:21-23`「**第④步已接满**」） |

---

## §五 ★★ 对我们的三条启示

| # | 启示 | 落点 |
|---|---|---|
| **1** | ★★ **注册时「参数形状」与「实现签名」是两处 —— 必须有一条判据盯它们对齐** | ★ 新判据候选（★ 会红的样子：★ 声明 `{x: INTEGER}` 而实现签名是 `y`） |
| **2** | ★★ **「注册了却没人调」是真实存在的状态**（★ P 的函数只有测试在调） | ★★ 我方要**避免**：★ 「在册」≠「接上」 —— ★ **判据要能区分**（★ 与我们 C5 那条「策略核必须挂上」同族） |
| **3** | ★★ **MCP 那层可借的就是「工具由提供方注册」这一形态** | ★ `handbook.spec.md` ＋ 注册面（★ T-225 的待裁第 1 条） |

---

## §六 本件不能证明的事（如实）

- ★★ **`mcp/mcp_server.py` 只读了前 50 行**（★ 共 103 行）⇒ ★ 「函数有没有也挂成 MCP 工具」**未核**；
- ★ **`engine/action_executor.py` 只读了前 45 行** ＋ 对 `function/implementation` 做了全文 grep（★ **0 命中**）；★ 其余行**未逐行读**；
- ★ **`cli.py`／`query_engine.py`／`export/*` 里有没有调 function，我没查** ⇒ ★★ 「**只有测试在调**」这句的射程限于**我查过的那些件**；
- ★ **P 的许可本件没核**（★ 只借形状、不抄代码）；
- ★ **本件没改代码、没跑构建**（★ `check.py` 现取 **C1–C14 rc=0**）。
