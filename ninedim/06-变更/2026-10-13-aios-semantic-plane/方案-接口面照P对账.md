# 方案（待签）：接口面照 P（Palantir foundry-ontology）对账 —— 不是 4 个，是八个面

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 三 结构 ／ 六 规格 | **0.1（方案·待签）** |

> **作者令（逐字）**：「有个问题，就是说**这 4 个接口对吗？就 4 个接口吗？是不是还需要其他的**？我们可以，**参考一下那个 pal 的，它的实现方法就 4 个嘛**。」

---

## §一 ★★ 现取：P 的接口面**不是 4 个**（是八个面、35+ 个方法）

| 面 | P 的件 | ★ 它的方法（现取） |
|---|---|---|
| **① 注册** | `core/ontology.py` | `register_object_type`／`register_link_type`／`register_action_type`／`register_function`／`register_interface` |
| **② 校验** | `core/ontology.py` ＋ 各类 `validate` | `validate_ontology`／`ObjectType.validate_value`／`validate_instance`／`ActionType.validate`／`ValueType.validate` |
| **③ 实例存储** | `engine/object_store.py` | `create`／`get`／`update`／`delete`／`search`／`create_link`／`get_linked`／`count`／`get_all_instances` |
| **④ 查询** | `engine/query_engine.py` | `filter`／`navigate`／`order_by`／`take`／`all`／`first`／`count` |
| **⑤ 审计（账）** | `engine/audit_log.py` | `append`／`get`／`query`／`export_csv` |
| **⑥ 执行** | `engine/action_executor.py` | `execute`（＋ `core/function.py` 的 `OntologyFunction.execute`） |
| **⑦ 治理** | `governance/` | `can_read`／`can_write`／`can_execute`／`has_role`／`Marking` |
| **⑧ 导出／接口自省** | `export/`（4 件）＋ `ontology.py` | `owl_exporter`／`shacl_generator`／`json_exporter`／`ontoguard_bridge`／`summary`／`to_dict`／`Interface.check_compliance`／`get_implementors`／`get_linked_types` |
| ★ 另 | `mcp/mcp_server.py`／`cli.py` | ★ MCP 服务面／命令行 |

⇒ ★★ **合计 35+ 个方法、15 个类** ⇒ **"就 4 个"不成立** —— ★ 本席先前给的 4 个是**"挂上游那 4 个口的最小闸"**，★ 不是完整接口面 ✓

## §二 ★★★ 照 P 的八个面对账：**我们有没有**

| P 的面 | ★ 我们有没有 | ★ 住在哪 |
|---|---|---|
| **① 注册** | ★ **有（是数据，没有注册 API）** | ★ 本体 JSON 的五节：`objects`／`links`／`interfaces`／`actions`／`functions` |
| **② 校验** | ★★ **有** | ★ `verify/check.py`（C1–C7）＋ 装载器（`SECTIONS`／`Reject` 逐条错误码） |
| **③ 实例存储** | ★ **有** | ★ 载体 `aios-fs`（＋ `aios-ontology` 的 `instance_limit`） |
| **④ 查询** | ★ **有** | ★ `aios-fs` 的 `query_eval` ＋ `aios-sgr` |
| **⑤ 审计（账）** | ★ **有** | ★ 账本 `aios-evidence`（＋ 本体的 `envelope`／`families`） |
| **⑥ 执行** | ★ **有** | ★ `aios-capability-runtime` ＋ `aios-policy` |
| **⑦ 治理** | ★ **有** | ★ `aios-policy` ＋ 本体的 `permissions`／`governance` |
| **⑧ 导出／自省** | ★★ **没有** | ★ —（★ 禁区 **B-3**：不接 RDF/OWL **运行时**；★ **"只导出、不推理"** ⇒ ★ 导出这一面**可以做**） |
| ★ 另：MCP | ★ **没有** | ★ — |

⇒ ★★★ **八字结论**：★ **P 的八个面，我们有七个（各自住在不同 crate 里，彼此不认账）；缺"导出"和"MCP"两个** ✓

## §三 ★★ 所以适配器该提供什么（重写后的接口清单）

★ **原则不变**（见 `方案-最小内核怎么分与怎么勾挂.md` §二：★ 先"丙"外层包，★ 上游一行不改），★ 但**接口面照 P 补全到八个面**：

| 面 | ★ 适配器 `aios-worldcore` 该给的接口 | ★ 它背后调谁 |
|---|---|---|
| **① 注册／装载** | `load()` —— 装载本体；★ **装不上 ⇒ 起不来** | ★ `aios-ontology` |
| **② 校验** | ★ `check_action(name)`／★ **`check_kind(kind)`**／`check_permission(who,cap)` | ★ 本体 ＋ 生成表 |
| **③ 实例** | `create/get/update/delete/search/link` | ★ `aios-fs` |
| **④ 查询** | `filter/navigate/order_by/take/first/count` | ★ `aios-fs`／`aios-sgr` |
| **⑤ 账** | `record(event)`／`events()` | ★ `aios-evidence` |
| **⑥ 执行** | `execute(action, params)` | ★ `aios-capability-runtime` ＋ `aios-policy` |
| **⑦ 治理** | `can_read/can_write/can_execute/has_role` | ★ `aios-policy` ＋ `permissions` |
| **⑧ 导出／自省** | `summary()`／`to_dict()`／`export()`（★ **只导出，不推理** —— 守 B-3） | ★ 本体 |

⇒ ★★ **即：★ 适配器不是"4 个接口"，是"八个面的门面"** ✓
★ 而★ **每个面背后都是上游现成的件**（★ 我们**只是加一层"本体口径"的检查**）✓

## §四 ★ 与"5 个挂点"的关系（两层，不冲突）

| 层 | 是什么 | 数量 |
|---|---|---|
| ★★ **挂点（口）** | ★ **上游代码在哪儿被拦住/被记账**（★ 改动面最小） | ★ **5 个**（①动作名②类型名⑤启动 ＋ ③权限④记账） |
| ★★ **接口面（门面）** | ★ **适配器对外提供什么 API**（★ 照 P 补齐） | ★ **8 个面** |

⇒ ★ **挂点管"改动面"；★ 接口面管"能力面"** ⇒ ★ 两回事 ✓

## §五 本件没做的事（如实）

1. ★ **没读** P 的 `export/` 四个件的实现（★ 只按名字与类名说）；
2. ★ **没定** 适配器要不要做"MCP 面"（★ 待裁）；
3. ★ **没动**任何代码。
