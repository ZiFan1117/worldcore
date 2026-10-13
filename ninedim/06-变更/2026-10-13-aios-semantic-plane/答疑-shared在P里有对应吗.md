# 答疑：`aios-worldcore-shared` 在 Palantir 公开库里有没有？必须吗？

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 三 结构 | **0.1（答疑·现取）** |

> **作者问（逐字）**：「`aios-worldcore-shared` 共同类型（谁/拒/为什么/要登记的东西/一件事）**这个在 palantir 的那个公开库里也有吗**？**这个需要吗？必须的吗**？」

---

## §一 ★★★ 现取：P 里"有对应，但没有对应物"

| 我们的类型 | ★ P 里的对应（逐字现取） | 件 |
|---|---|---|
| `Registration` | ★★ `ObjectInstance{instance_id, object_type_id, properties, links, created_at, updated_at, created_by}` | `engine/object_store.py` |
| `Event` | ★★ `AuditEntry{entry_id, timestamp, action_type_id, executed_by, parameters, effects, success, error_message}` | `engine/audit_log.py` |
| `Refuse` | ★★ `ValidationResult{valid: bool, errors: list[str]}` ＋ `ActionResult{success, action_id, effects_applied, validation_errors, audit_entry_id, timestamp}` | `core/object_type.py`／`engine/action_executor.py` |
| `Who` | ★ **没有单独的类** —— ★ P 用**裸字符串**（`AuditEntry.executed_by: str`／`ObjectInstance.created_by: str`） | 同上 |
| `Reason` | ★ **没有单独的类** —— ★ P 用 **`errors: list[str]`** ＋ `ValidationRule{rule_id, expression, message, severity, effect_type, target, changes}` | `core/action_type.py` |
| ★ 我们还多一个 `SharedProperty` 概念 | ★★ **P 有 `SharedProperty{used_by, type_id, display_name, description, properties, primary_key, interfaces}`** | `core/object_type.py` |

⇒ ★★ **结论**：★ 那些类型的**含义 P 里都有**；★ **但 P 没有"一个共用的类型包"**。
⇒ ★★★ **为什么 P 不需要**：★ 它是 **Python** —— 裸 `dict`／裸 `str` 到处传，编译器不管。
⇒ ★★★ **为什么我们要**：★ 它是 **Rust** —— 八面之间传的东西**必须类型一致**，否则**编译不过**。

## §二 ★★ "必须吗"：必须有"一处公共的"，但形式可选

| 做法 | 结果 | 判 |
|---|---|---|
| ★ **甲：独立 crate `aios-worldcore-shared`**（现状） | 八面共 use 一份 | ★★ **推荐** |
| ★ 乙：放进门面 crate `aios-worldcore` | 八面要依赖门面 ⇒ **循环依赖** | ★ **不行** |
| ★ 丙：各面自己定义 | ★ **8 份「拒」、8 份「谁」** | ★ **不行**（正是作者先前点出的重复病） |

⇒ ★★★ **甲是唯一既不循环、又不重复的做法** ⇒ **所以"必须有一个"，且"必须是独立 crate"** ✓

## §三 ★ 顺带：我们的八面与 P 的三个目录正好对上

| P 的目录 | 它装什么（现取件名） | ★ 我们的对应 |
|---|---|---|
| ★ `core/` | ★ **定义层**：`object_type.py`／`link_type.py`／`action_type.py`／`function.py`／`interface.py`／`data_types.py`／`ontology.py` | ★ `aios-ontology`（本体）＋ `aios-worldcore-registry`（① 注册） |
| ★ `engine/` | ★ **运行层**：`object_store.py`／`query_engine.py`／`action_executor.py`／`audit_log.py` | ★ ② 实例注册／③ 校验／④ 存储／⑤ 查询／⑥ 账／⑦ 执行 |
| ★ `governance/` | ★ **治理**：`markings.py`／`roles.py`／`permissions.py` | ★ ⑧ 治理 |
| ★ （另有 `export/`／`mcp/`／`cli.py`） | ★ 导出／MCP／命令行 | ★ 附面（待裁） |

⇒ ★★ **即：我们的"八面"不是自创的**，★ **它照的就是 P 的 `core`＋`engine`＋`governance` 三层** ✓

## §四 本件没做的事（如实）

1. ★ **没读** P 的 `export/`／`mcp/`／`cli.py`（★ 只按件名说）；
2. ★ **没动**任何代码（本件是答疑）。
