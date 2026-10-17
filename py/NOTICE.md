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
