# 纲领-上位语义体系-分类树-03-与 BFO 逐条对照

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 | v0.1 |

> **本件是《纲领-上位语义体系-分类树》的第 3／6 部分**：与 BFO 逐条对照（§5）。
> 总纲、件清单与「从哪读起」见 `纲领-上位语义体系-分类树.md`。

## §5 与 BFO 的逐条对照

### 5.1 BFO 原文坐标（逐字）

出处＝本地料 `.refs/bfo-2020/21838-2/owl/bfo-core.owl`（**不入版本控制** ⇒ 跨机复取用 IRI）。下表每条都逐字读到。

| BFO 类／属性 | IRI | 原文（逐字） | 行 |
|---|---|---|---|
| continuant | `BFO_0000002` | `(Elucidation) A continuant is an entity that persists, endures, or continues to exist through time while maintaining its identity` | :935 |
| occurrent | `BFO_0000003` | `(Elucidation) An occurrent is an entity that unfolds itself in time or it is the start or end of such an entity or it is a temporal or spatiotemporal region` | :947 |
| （两侧互斥） | — | continuant 上 `owl:disjointWith` 指向 occurrent（发生侧无反向声明） | :932 |
| independent continuant | `BFO_0000004` | `b is an independent continuant =Def b is a continuant & there is no c such that b specifically depends on c or b generically depends on c` | :965 |
| specifically dependent continuant | `BFO_0000020` | `b is a specifically dependent continuant =Def b is a continuant & there is some independent continuant c which is not a spatial region & which is such that b specifically depends on c` | :1165 |
| generically dependent continuant | `BFO_0000031` | `(Elucidation) A generically dependent continuant is an entity that exists in virtue of the fact that there is at least one of what may be multiple copies which is the content or the pattern that multiple copies would share` | :1318 |
| realizable entity | `BFO_0000017` | `(Elucidation) A realizable entity is a specifically dependent continuant that inheres in some independent continuant which is not a spatial region & which is of a type some instances of which are realized in processes of a correlated type` | :1123 |
| quality | `BFO_0000019` | `(Elucidation) A quality is a specifically dependent continuant that, in contrast to roles and dispositions, does not require any further process in order to be realized` | :1153 |
| disposition | `BFO_0000016` | `(Elucidation) A disposition b is a realizable entity such that if b ceases to exist then its bearer is physically changed & b's realization occurs when and because this bearer is in some special physical circumstances & this realization occurs in virtue of the bearer's physical make-up` | :1110 |
| function | `BFO_0000034` | `(Elucidation) A function is a disposition that exists in virtue of its bearer's physical make-up & this physical make-up is something the bearer possesses because it came into being either through evolution (in the case of natural biological entities) or through intentional design (in the case of artefacts) in order to realize processes of a certain sort` | :1330 |
| role | `BFO_0000023` | `(Elucidation) A role b is a realizable entity such that b exists because there is some single bearer that is in some special physical, social, or institutional set of circumstances in which this bearer does not have to be & b is not such that, if it ceases to exist, then the physical make-up of the bearer is thereby changed` | :1179 |
| process | `BFO_0000015` | `(Elucidation) p is a process means p is an occurrent that has some temporal proper part and for some time t, p has some material entity as participant` | :1096 |
| process boundary | `BFO_0000035` | `p is a process boundary =Def p is a temporal part of a process & p has no proper temporal parts` | :1380 |
| temporal region | `BFO_0000008` | `(Elucidation) A temporal region is an occurrent over which processes can unfold` | :1007 |
| material entity | `BFO_0000040` | `(Elucidation) A material entity is an independent continuant that at all times at which it exists has some portion of matter as continuant part` | :1445 |
| realizes | `BFO_0000055` | domain＝process（:158）、range＝realizable entity（:159）；定义（:162）：`realizes is a relation between a process b and realizable entity c such that c inheres in some d & for all t, if b has participant d then c exists & the type instantiated by b is correlated with the type instantiated by c` | :157-163 |
| participates in ／ has participant | `BFO_0000056`／`BFO_0000057` | `has participant`：domain＝process（:200）；range 是三类之并——specifically dependent continuant、generically dependent continuant、"非空间区域的 independent continuant"（:204-213） | :200-215 |

### 5.2 四组分法：我们采哪支、为什么不采哪支

#### 5.2.1 continuant／occurrent

- **采**（就是本树的第一刀）。三条理由：
  ① 两侧**互斥**且有明文（`:932`），一次切分不重叠——这正是一棵顶层树要的第一条性质；
  ② **本仓最贵的一类错正好是这一刀没切**：三条家族用**发生的名字**命名**记录**（Y-2，§7.1）；
  ③ 这一刀**不需要先决定"声明算不算世界里的东西"**——它只问"在不在时间里展开"，所以它能在我们另立 C／D 两支之前就把 A 与 B 分开。
- **不采的**：**不采"顶层只有两支"**。BFO 顶层只有 continuant／occurrent；我们另立 C（说法）与 D（层外），理由见 §5.3。
- ★ **采的是切法，不是"我们两边都有东西"**：`temporal region` 在 BFO 里是 occurrent（`:992`），而本仓连一个区间字段都没有（§7.2）。

#### 5.2.2 independent vs dependent

- **采**（本树的第二刀，问②）。
- **采其判据的原文口径**：`independent` 的定义是"**不存在任何 c 使得它 specifically 或 generically 依赖 c**"（`:965`）——一句话就把"必须靠别的东西才在"的东西挡在外面，可核、不用判例。
- **dependent 只有两种**（`BFO_0000020` 依身／`BFO_0000031` 可复制），本仓**不采"两种就够"**：我们在 A 支里放**三目**——A2 依身、A3 外附、A4 可复制。理由不是 BFO 错，而是本仓要判的那件事**更细**：BFO 把 `disposition`（依身）与 `role`（外附）都算 `realizable`，差别写在两条定义里（"承载者的物理构造变不变"，`:1110` 对 `:1179`）；本仓要判的正是"**许可**该不该在承载者的构造之外长期存在"（§7.4），所以把这条差别**提到目的层级**，让它一眼可判。
- **不采的**：**不采"generically dependent 一类就够了"**。`BFO_0000031` 只说"可多份共享的内容"，它**不区分"记录"与"记录所关于的那件事"**——而这一区分正是 Y-2 的缺口。⇒ 我们在 A4 里显式写明"**记录／所关于的事**"这一对，并给它一条判据（§7.1）。

#### 5.2.3 quality／disposition／function／role

- **采 disposition 与 role 的兄弟关系**（两者都 ⊂ `realizable entity`，`:1105` 与 `:1175`）⇒ 对应 A2 与 A3。
- **采 realizable 的必要条件**（逐字 `inheres in some independent continuant`，`:1123`）⇒ 这正是 Y-1 缺口的外部依据（§7.3）。
- **不设 quality 目**：`quality`（`:1153`）逐字"in contrast to roles and dispositions, does not require any further process in order to be realized"。本仓今天**没有这一类**：`job.status`、`presence.state` 是**过程的状态**（状态随事件变，即"要经过过程才落到某个值"），够不上 quality。设一个空目只会让树看起来更全、实际更假。
- **不采 BFO 的 `function` 这个名字**：BFO 的 `function`（`:1330`）是"**长在一个有物理构造的承载者上、且那个构造是为着实现某类过程被有意设计出来的倾向**"；本仓的"函数"逐字是"**只有入口名**（引用到底层函数）"（`ontology.json:149`），出厂 `entries` 现取 `{}`。两者**同名不同物**（判-1.3 同结论）。
  ⇒ 处置照本仓自己那条硬规矩（一个词一个意思）：本仓的"函数"**改名归位**到 **C5 入口引用**；`function` 这个名字在树里**不给格子**。
  ★ **标出来**：若只改 `_functions._element` 的文字（说明"本节的『函数』不是 BFO 意义的 function"）⇒ **零身份代价**；若改**节名或字段名**，且落在 `_` 键下 ⇒ 也零代价；若动到 `concepts`／`_objects` 的**名字**（非 `_` 侧）⇒ **换身份**（§7.6）。

#### 5.2.4 process／process boundary

- **采**（B1 与 B2）。
- **采 process 的两条件**（`:1096` 逐字：有 temporal proper part ＋ 有 material entity 作 participant）——★ 采这一刀**正是为了说明本仓的动作够不上 process**：`_actions` 九条每条只有 `capability` ＋ `reversible`，**没有参与者、没有区间、没有边界**（判-3 与本件同结论）。
- **采 process boundary 的判据**（`:1380` 逐字"a temporal part of a process & p has no proper temporal parts"）⇒ 本仓信封的 `at`（Unix 秒）是最接近的候选，但它今天**既没有"属于哪个过程"的声明，也没有"它是边界"的声明**（§7.2）。
- **不采的**：**不采"把 temporal region 并进过程目"**。BFO 把 `temporal region` 也算 occurrent（`:992`），我们采这条（B3 在 B 支内），但**单独立目**——理由：B3 要承载"时长／区间"这一族**今天完全不存在**的格（§7.2），并进 B1 会让这一族缺格在树上看不出来。

### 5.3 我们额外立的两支（BFO 没有这两刀）

| 支 | 为什么另立 | 不立会怎样 |
|---|---|---|
| **C 说法** | 本仓有一条**硬线：法律与事实分开**（`_permissions._grant_via_ledger` 讲"条文面"与"事实"分家，`ontology.json:172`；`_permissions` 在归属表里是 half 挂；`_meta_layers` 明写"挂不进五要素"）。BFO 会把"说法"也放进 generically dependent continuant（＝我们的 A4），**它没有"声明／事实"这一刀**，而本仓的判据、载体、变更程序都按这一刀分（法律改了走评审、事实改了落一条事件）。 | 十二条节里"声明面"与"实例面"会挤进 A 支，读者分不出"改哪一条要评审、改哪一条要落账"。 |
| **D 层外** | 本仓自己已判"十二节里 4 节**挂不进**五要素"（`ontology.json:217`），并逐条写明它们归**元层／接入层**（`:293-319`）。这一族**不是世界图景里的东西**，但**确实在文件里**——不立一支，它们就只能塞进某个领域目，那是"把一个可查的错换成一个不可查的错"。 | 读法、验法、接入映射会被读成"世界里的东西"，§6.3 那处矛盾会永久留着。 |

### 5.4 对照总表

| BFO 分法 | 采不采 | 落在本树哪 | 理由（一句话） |
|---|---|---|---|
| continuant／occurrent | **采切法**，不采"只有两支" | A 支／B 支 | 两侧互斥可核；本仓最贵的错就是这一刀没切（Y-2） |
| independent vs dependent | **采** | 问② 的四条分支 | 定义一句话可核；本仓要判"许可该不该长期存在"，故把 role 与 disposition 的差别提到目级 |
| specifically dependent（依身） | **采** | A2 | 承载者构造变 ⇒ 它没 |
| generically dependent（可复制内容） | **采**，并补"记录／所指"这一对 | A4 | 它只说"可多份共享"，不区分记录与所关于的事（Y-2 的缺口） |
| externally grounded（role） | **采** | A3 | 外部制度给、构造不变 ⇒ 与 A2 分目 |
| realizable 的 `inheres in … bearer` | **采** | A2 的必要条件 | 这是 Y-1 缺口的外部依据 |
| quality | **不采**（不设目） | —— | 本仓今天没有这一类；设空目＝写成做到了 |
| function（BFO 义） | **不采这个名字** | ——（本仓的"函数"归 C5） | 同名不同物：BFO 的 function 有承载者与设计构造 |
| process（两条件） | **采** | B1 | 借它判出"本仓的动作够不上 process" |
| process boundary | **采** | B2 | `at` 是最接近的候选，今天没有它是边界的声明 |
| temporal region | **采**，但单独立目 | B3 | 要承载"时长／区间"这一族今天不存在的格 |
| 顶层无执行语义 | **不采** | 支 C 必须带"改哪条会红" | 本仓要的是一份**能被机器读的法律**，不是只答"是什么"的顶层本体 |

---

