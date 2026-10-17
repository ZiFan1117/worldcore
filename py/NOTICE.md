# 这份 Python 代码不是我们写的

★ 来源：**foundry-ontology-open**（`https://github.com/cloudbadal007/foundry-ontology-open`）
★ 许可证：**MIT**（全文见 `LICENSE-foundry-ontology-open`）
★ 版权：**Copyright (c) 2025 Pankaj Kumar (cloudbadal007)**

## 我们动了什么

★ **只拿了 `core/` ＋ `engine/` 两个夹**；`cli.py`／`export/`／`governance/`／`mcp/` **没拿**。
★ **我们改了 1 处**（MIT 允许改）：

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `foundry_ontology/core/action_type.py` | ★ **给 `ActionType` 加了一格 `metadata: dict`**（在 `audit_enabled` 之后，' + 3 行注释） | ★ P 原本的 `ActionType` **没有 metadata 格**，而我们的「动作约束」（`not_roles`／`kind`／`implemented`）必须挂在动作上；★ `ObjectType` 有这格，`ActionType` 没有 |

★ 其余 **一行没改**。

## 为什么只拿两个夹

★ `core/` ＋ `engine/` 的外部依赖是**零**（只要 `sqlite3`，标准库）—— 实测过。
★ `export/` 要 `rdflib`／`owlready2`／`pyshacl`；`cli.py` 要 `click`／`rich`；`mcp/` 要 `mcp` —— 这些我们不要。
