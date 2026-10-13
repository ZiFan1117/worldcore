# 补：W3C 取件补齐（RDF 1.1 ＋ SKOS）——三层划分与「概念 vs 类 vs 个体」

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 ／ 六 规格 | **0.1** |

> **件性质**：**取件补齐**（承前件 `对照-W3C划分与我们25类重排.md` 里自认"RDF 1.1 与 SKOS 原文未取到"那一处）。
> ★ 本席**现取原文**；**取不到的一律如实标注**，不补写。

---

## §一 RDF 1.1 Concepts（W3C REC）——**"值"的定义**（本席现取逐字）

| 项 | 逐字原文 |
|---|---|
| **Literal（值）** | 「**Literals are used for values such as strings, numbers, and dates.**」 |
| **值的构成** | 「a **lexical form**… a **datatype IRI**… which **determines how the lexical form maps to a literal value**」 |
| **值类型也由 IRI 标识** | §5.4 逐字：「**Datatypes are identified by IRIs.**」「Recognized IRIs have **fixed referents**.」 |
| 目录骨架 | `3.1 Triples`／`3.2 IRIs`／★ **`3.3 Literals`**／`3.4 Blank Nodes`／`5 Datatypes`（含 `5.1 XML Schema Built-in Datatypes`） |

⇒ ★★ **两条要紧结论**：
1. ★ **"值"＝词法形式 ＋ 数据类型** ⇒ ★ **这正是我们 `fields` 那一格**（`muted: bool`、`at_time: timestamp`…）；
2. ★★ **"值类型"和"个体"都是被 IRI 标识的** ⇒ ★ **不能用"有没有 IRI"区分个体与值**；
　 ★ **区分在用法**：★ **个体是"被描述的主语"（句子的主词）；值是描述里的字面量（宾位上的东西）**。
　 ⇒ ★ 由此**重申**：`clock`（一台时钟）／`unit`（一个单位）是**主语** ⇒ **个体**；`epoch`／`code` 是**字面量** ⇒ **值**。

## §二 SKOS Reference（W3C REC）——**"概念"是第三层**

| 项 | 本席现取 |
|---|---|
| 类清单 | `skos:Collection`／★ **`skos:Concept`**／`skos:ConceptScheme`／`skos:OrderedCollection` |
| 属性（部分） | `prefLabel`／`altLabel`／**`definition`**／`broader`／`narrower`／`related`／`inScheme`／`notation`／`note`／`scopeNote`… |
| ★ **概念体系是"类"** | §4.3 逐字：「**S2 `skos:ConceptScheme` is an instance of `owl:Class`.**」 |
| ★★ **关键节（标题已取到）** | 目录里 **`3.5.1 SKOS Concepts, OWL Classes and OWL Properties`** —— ★ **这一节正是"概念 vs 类 vs 个体"的官方说明**；★ **本席只取到标题，正文未取到**（如实登记） |
| 另一相关节 | `4.6.2 SKOS Concept Schemes and OWL Ontologies` |

## §三 ★★ 合起来：W3C 给的是**三层 ＋ 两类附属**（这是"重新梳理"的尺子）

| 层 | 是什么 | 逐字依据 |
|---|---|---|
| ★ **Individual（个体）** | 有独立身份的实例；"被描述的主语" | OWL：「Mary **belongs to** the class of all persons」 |
| ★ **Class（类）** | **用来 group individuals** 的东西 | OWL：「classes are used to **group individuals**…in order to refer to them」 |
| ★★ **Concept（概念）** | ★ **另一层**：SKOS 的"概念"（知识组织体系里的单元） | SKOS：`skos:Concept` 是一个类；`skos:ConceptScheme` 是 `owl:Class` |
| **Literal／Datatype（值）** | 描述里的字面量（词法形式 ＋ 数据类型） | RDF 1.1 §3.3 |
| **Property（属性/关系）** | 连接上述各层 | OWL 的 `ObjectProperty`／`DatatypeProperty`；我们的 `_links` |

## §四 ★★ 用这把尺子看我们 25 个"类"——**它们混了两层**

| 我们的类 | 按 W3C 它是哪一层 | 说明 |
|---|---|---|
| `human`／`agent`／`application`／`service`／`device`／`file`／`model`／`package`／`config`／`project`／`port`／`capability`／`permission`／`unit`／`clock`／`identity` | ★ **Class**（能 group individuals 的类型） | ✓ 这些是"能给个体分组"的类 |
| ★★ `notice`／`job`／`action`／`memory` | ★ **更像 Concept（类别名）**，而不是 Class | ★ **"通告/作业/动作"是"类别标签"** ⇒ ★ 与作者令「通告不能作为一个单独的个体类型」**同一判** |
| `surface`／`cell`／`presence` | ★ **更不是 Class**：它们是**从记录读出来的视图**（投影） | ★ 既非个体也非类 |
| 各字段（`muted: bool`…） | ★ **Literal／Datatype（值）** | RDF 1.1 §3.3 |

⇒ ★★ **这就是"重新梳理"的结论（依据是 W3C，不是本席自造）**：
> **我们那 25 个"类"里，只有一部分是真正的 Class（用来给个体分组的类型）；**
> **`notice`/`job`/`action`/`memory` 更像 SKOS 意义上的 Concept（类别标签）；**
> **`surface`/`cell`/`presence` 是读出来的视图；**
> **值（各字段）是 Literal。**
> ⇒ ★ **"通告不能作为一个单独的个体类型"由此得到 W3C 层面的支撑**：★ **它是个体（某条通告），"通告"是它所带的类别标签（Concept），而不是给它分组的那个 Class。**

## §五 本件取件状态（如实）

| 件 | 状态 |
|---|---|
| W3C **RDF 1.1 Concepts** | ★ 已取到 §3.3 Literals 逐字、§5.4 Datatype IRIs 逐字、目录骨架 |
| W3C **SKOS Reference** | ★ 已取到类/属性清单、§4.3 的 `S2` 逐字、**`3.5.1` 的标题**；★ **`3.5.1` 正文未取到** |
| W3C **OWL 2 Primer** | 已取到（前件）：类/个体逐字、**类成员不互斥**逐字、目录 `4.3 Class Disjointness`／`4.8 Datatypes` |
| W3C **PROV-O** | 已取到（前件）：`Entity`／`Activity`／`Agent` 三分与关系词 |
| BFO | 我们 `_meta.anchor` 已在用；★ 本件未另取 |
