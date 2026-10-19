# 这份 Python 代码不是我们写的

★ 来源：**foundry-ontology-open**（`https://github.com/cloudbadal007/foundry-ontology-open`）
★ 许可证：**MIT**（全文见 `LICENSE-foundry-ontology-open`）
★ 版权：**Copyright (c) 2025 Pankaj Kumar (cloudbadal007)**

## 我们动了什么

★ **只拿了 `core/` ＋ `engine/` 两个夹**；`cli.py`／`export/`／`governance/`／`mcp/` **没拿**。
★ **我们改了 3 处**（MIT 允许改，都是为了把 AIOS 的机制装进 P）：

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `core/action_type.py` | 给 `ActionType` 加一格 `metadata: dict` | P 原本没有；我们的「动作约束」（`not_roles`／`kind`／`implemented`／`reversible`）必须挂在动作上 |
| `core/ontology.py` | 给 `Ontology` 加一格 `metadata: dict` | P 原本没有；我们的世界机制（`envelope`／`families`／`permissions`／`governance`／`value_types`／`flags`／`world`／`base_types`）必须有个地方放 |
| `core/function.py` | 给 `OntologyFunction` 加一格 `metadata: dict`（`None` 风格 ＋ `__post_init__` 初始化，与该文件其它格一致） | P 原本没有；我们的函数只有入口名 ＋ `transport`／`endpoint`，没有 `implementation` |

★ 其余 **一行没改**。三格都是「**加一格**」，不改任何既有格、不改任何逻辑。

## 为什么只拿两个夹

★ `core/` ＋ `engine/` 的外部依赖是**零**（只要 `sqlite3`，标准库）—— 实测过。
★ `export/` 要 `rdflib`／`owlready2`／`pyshacl`；`cli.py` 要 `click`／`rich`；`mcp/` 要 `mcp` —— 这些我们不要。
## ★ 我方对 P 源码的改动（2026-10-17，逐条记）

| # | 文件 | 改动 | 为什么 |
|---|---|---|---|
| **1** | `foundry_ontology/core/action_type.py` | 加 `metadata: dict` | 装我们的 `kind`／`not_roles`／`实现状态` |
| **2** | `foundry_ontology/core/ontology.py` | 加 `metadata: dict` | 装世界机制（envelope／families／permissions／governance） |
| **3** | `foundry_ontology/core/function.py` | 加 `metadata: dict = None` ＋ `__post_init__` | 装 `transport`／`endpoint` |
| **4** | ★ `foundry_ontology/engine/object_store.py` | `sqlite3.connect(..., check_same_thread=False)` ＋ `threading.Lock()` | **本体在主线程建 store，而 zenoh 回调在别的线程跑** ⇒ 不放开就报「SQLite objects created in a thread…」 |
| **5** | ★ `foundry_ontology/engine/object_store.py` | `create()`：`instance_id` 撞车（→ 已存在同 id、**不同类**）时，把【类型】加进 id | ★ 借来的代码是**全局 instance_id**（上游同一缺陷，见 `_scratch/palantir-open-source/code-notes/02-cloudbadal.md` §0 第 6 条）：`human/zhang` 与 `space/zhang` 同 id ⇒ 后者**悄悄覆盖**前者 ＝ 假账。判据 **C30** 钉住它。 |
