# 判词 · ② 载荷与头（Zenoh `Sample` ＋ CloudEvents）

部分：② 载荷与头（Zenoh `Sample` ＋ CloudEvents）

独立性档：★ **丙**（同一执行体 ＋ 全新上下文）—— ★ 如实说明：席位表 `评审-总线选型-材料包与席位表.md:71` 登记本席为「乙（独立执行体）」，★ 但本席**给不出**"另一执行体"的证据：`list_agents` 现取——本席 `rev-payload` 与 `lead` 的 `model` 同为 `deepseek-flash`、同在 `13-aios-worldcore` 这一个文件系统、同一工具链 ⇒ ★ 按 `nd-review` §四，本席只能登记为**丙：只是隔离，不是独立**。
★ 补偿（`nd-review` §四硬要求：出题／执行／判卷至少交出一样）：★ **出题＝Lead（另一上下文）／执行＝写者（Lead ＋ 已被停的实现席，非本席）／判卷＝本席** ⇒ ★ **判卷与写者不同一**，该硬要求成立；★ 但「乙」这一档**不成立**，★ **须由 Lead／作者处置**（本席不冒充乙）。

结论：★ **有条件通过**（★ 条件 C1–C6 与期限见本节末）。

## 结论附：条件与期限

★ **期限的口径**：本席**不写日历承诺**——★ 落在条件上的期限是**里程碑硬边界**（可核、可判逾期），★ 参照读数是宿主钟（见文末附录）。★ 判"逾期"的命令在每条里给出。

| # | ★ 条件（必须落成件） | ★ 期限（里程碑硬边界） | ★ 逾期怎么判 |
|---|---|---|---|
| **C1** | ★★ **声明"替换"还是"叠加"**：逐条写清 Zenoh `Sample`／`SampleBuilder` 的槽与本体 `envelope.required／optional`（8＋2 格）的关系。★ 若判为**替换**（即核心格改由别人的槽承载）⇒ ★ 那是改 `envelope.fields` ⇒ **换 `vocab_hash`** ⇒ ★ **必须先走框架变更**（`ontology-extensibility.spec.md:28-30` 的 `CoreCollision` 口径同理） | ★ 在**任何一行接 Zenoh／cloudevents 的代码或依赖进仓之前**；并**不晚于**材料下一版（v0.2）与 `评审-总线选型-材料包与席位表.md` 同一提交 | `git diff --stat`（或 `git grep -n "zenoh\|cloudevents" -- Cargo.toml crates/ verify/`）里出现该依赖而 C1 件不在 ⇒ 逾期 |
| **C2** | ★★ **先声明形状再装**（`worldcore-sdd` §十五 F 处置逐字）：把"三张通行证"的**字段名／类型／必填性**写进本体（`crates/aios-ontology/data/ontology.json`）并走评审 ⇒ 然后才允许放进 `attachment`／CE 扩展属性 | 同 C1 窗；★ 与 C1 可同一提交，★ 但**不得晚于**它 | `attachment`／扩展属性里出现通行证字段名，而本体里查不到该声明 ⇒ 逾期 |
| **C3** | ★★ **"谁发的"这一格不取 `source_info`**：仍取我们信封的 `actor`（`world://<ns>/<name>`），并保留"每帧 `actor` 非空且等于该连接绑定主体"这条**会红**判据 | 同 C1 窗 | 设计件里 `actor` 的取值来源写成 `source_info`／Zenoh entity id ⇒ 逾期 |
| **C4** | ★★ **名字映射要单射 ＋ 不含禁字**：给出"本体名字 → Zenoh keyexpr"的改写规则，配**会红**判据（含 `//`、含 `* $ ? #`、两个不同名字映到同一 key）＋ ★ 发布侧用**非通配** key 类型 | 同 C1 窗 | 该判据不在 `verify/`（且无 `--self-test` 反例）⇒ 逾期 |
| **C5** | ★★ **落点进原子登记面**：把"信封载体／进总线前校验层"作为原子登记进 `原子登记-语义面.md`（硬约束 1：我方新增 crate 名单的**唯一出处**＝本件）＋ 在 `改动对照.md` 追加一行 | 同 C1 窗 | `原子登记-语义面.md` 里查不到该原子 ⇒ 逾期（★ 硬约束 1 直接不成立） |
| **C6** | ★ **现取重取 ＋ 标弱项**：T-130 §一 的现取对象改成**送**的那一方（`SampleBuilder`／`Publisher`／`Session::put`）；把 `source_info`／`reliability` 的 `unstable` 门标出来；★ CloudEvents 字段表**先核再引**（材料自己已写"要引前必须核"） | 交材料下一版（v0.2）时 | 该件里查不到 `SampleBuilder` 与 `unstable` 字样 ⇒ 逾期（现取＝`grep`） |

★ **本档不能证明的事**：★ 本席**没有**实测 Zenoh／CloudEvents 的任何 API（宿主无 cargo、本席未上 VM）⇒ ★ 本判词里关于 API 的每一句都是**现取官方文档**（URL ＋ 逐字引文，见文末附录），★ **不是**"我引过、编过、跑过"。★ 也**没有**人签（硬约束 6）。

---

## 理念张力裁决

★ **两者可兼容** —— ★ 甲（能自足的不外引）管的是【文档正文自足】；★ 乙（能用人家的尽量用人家的）管的是【工程依赖与传输实现】⇒ ★ **射程不同，不冲突**。

### 判断依据（三条，条条可核）

1. ★ **甲的原出处自带射程**：`worldcore-sdd` §三「文档里写什么、不写什么」项下，逐字：**「写：这件事是什么、判据是什么、谁负责、什么算通过。能自足的就写全，不要外引。」** ⇒ ★ 甲约束的是**正文**（禁链式外引），★ **不是**"禁引外部库／协议"。★ 同一节「不写」表里点名的也是「"参考某某文档 §x"的链式外引」——**文档**形态。
2. ★ **材料包把甲抽离了射程**：`评审-总线选型-材料包与席位表.md:61-64` 把甲与乙并列对置，★ 但甲那一格只写「能自足的不外引」＋出处 `worldcore-sdd`，**没带"它在 §三 文档节下"这一射程** ⇒ ★ 这正是 `worldcore-sdd` §五「**读数的射程 ≠ 它被读成的射程**」点名的形态：射程被读宽了。
3. ★ **乙的落点是实现，不含"定义"**：`决策-机制借Zenoh载荷自定.md:15` 逐字「★★ 乙：借机制的实现，★ 载荷是我们自己的」；`决策-载荷与机制都用现成的.md:7-8` 是作者令逐字（皮／内容都借）。★ 而作者另一条令③「**用我们的定义，装它的干活逻辑**」（`令-定义以我们为准.md`）把"定义"留在我们手里 ⇒ ★ **乙的射程不含"形状声明权"与"名字权威"**。

### ⇒ 由裁决推出的那条分界线（本席的主张，供人签）

★ **借**＝传输／编码／工程实现；★ **不借**＝形状声明／名字权威／判据。
★ 落到本席这一部分：★★ **"协议头用人家的、载荷也用别人的"本身不与甲冲突**；★★ **但它一旦把"通行证落在谁的槽里"读成"形状也归别人"，撞上是作者令③＋`CLAUDE.md` 语义口径＋禁区 1，不是甲**（见逐条 §三／§四）。

### ★ 一处必须点名的内部矛盾（不是甲×乙，是乙×乙）

★ `调研-内容与机制分不分得开.md:31-33` 逐字判过：「★ 丙：全借（连载荷也用它的）｜用它的 header 当信封｜★ **不行**（★ **本体通行证没地方放**，★ 且被厂商绑死）」，其收口逐字（`:72`）：「★★ **借机制、不借载荷**」。
★ 而 `决策-载荷与机制都用现成的.md`（标题即「**载荷**与机制**都用现成的**」）§三 逐字：「★★★★★ 于是我们真正要写的，只剩**一件**」——★ **把 `调研-载荷协议与总线功能面.md:87-92` 与 `方案-两个面怎么分工与两套协议.md:84` 都写着的"我们要自己写的两件"（其中第一件＝**本体信封的字段表（含三张通行证）**）从清单里删掉了**。
⇒ ★★ **待评对象不是一份自洽的方案**：★ 两份**同在材料包 §一 逐件点名之内**（`评审-总线选型-材料包与席位表.md:16`）。★ 这一条**不是印象**，是两份件自己的字。

---

## 逐条

### §一 · 硬约束（`AGENTS.md` §二，逐字基准见材料包 §二·甲）

| 条款 | 判 | ★ 证据 |
|---|---|---|
| **1 一个原子一个夹**（名单唯一出处＝`原子登记-语义面.md`） | ★ **不符合** | ★ 现取 `原子登记-语义面.md:25-26`：登记表**只有两个原子**——`A-SEM-01`（`crates/aios-ontology/`）／`A-SEM-02`（`crates/aios-cognitive/...`）。★ 逐字（`:7`）：「★ **本件是我方在 13 仓的原子登记面**……**模块号唯一出处＝本件**」。⇒ ★ 待评方案的核心动作（"进总线前按本体校验"＋信封载体）**在本登记面里没有原子**；★ 而 `决策-载荷与机制都用现成的.md:59-65` 把它写成"我们真正要写的只剩一件" ⇒ ★ **落点缺失**（记入缺口 G9） |
| **2 承诺写进 `ninedim/01-意图环/04-规格/<能力>.spec.md`** | ★ **不符合** | ★ 现取 `ninedim/01-意图环/04-规格/` 9 份 `.spec.md`（`channel-identity`／`delivery-and-resources`／**`envelope-validation`**／`gate-enforcement`／`ledger-integrity`／`ontology-extensibility`／`projections`／`read-model`／`write-side-adaptation`）——★ **没有"总线"这一节**（此判断与 `设计-总线该实现什么-合并清单-v0.1.md:451` 逐字一致：「而这三处今天都还没有"总线"这一节」）。★ 更硬的一点：★ **信封的承诺早已存在**——`envelope-validation.spec.md:32-33` 逐字「系统 SHALL 对每一条写入事件逐字段校验信封必填项 `world` / `kind` / `id` / `seq` / `at` / `actor` / `flags` / `body`」；★ 而**10 件待评方案里 `envelope` 一词 0 命中**（现取 `grep`，见附录）⇒ ★ 新方案与既存承诺**零引用** |
| **3 正文不许写过程** | ★ 符合 | ★ 11 件都在 `ninedim/06-变更/2026-10-13-aios-semantic-plane/`（过程域）之内，★ 现取目录清单即证 |
| **4 改完同批更新 `改动对照.md`** | ★ **无法判定** | ★ 本席**没核**这 10 件的每一笔是否有对应行；★ `改动对照.md` 有 8 处"会红"命中，但★ 本席未逐笔对账（记入"本席没做的事"） |
| **5 生成物只改输入、重跑生成器** | ★ **无法判定** | ★ 待评方案声明 `决策-载荷与机制都用现成的.md:89`「★ **没写**任何代码（★ 本件只定口径）」⇒ ★ 无生成物可判；★ 但★ 这不等于合规，★ 只等于**这一条今天无对象** |
| **6 正式结论与签字只有人能下** | ★ 符合 | ★ `评审-总线选型-材料包与席位表.md:7` 逐字「★ **本件不是结论** —— ★ 按硬约束 6，**正式结论与签字只有人能下**」；`:75` 结论栏留空；`:106` 逐字「★★ **没有结论**（★ 结论栏留空，★ 等人签）」。★ 本席判词同样不写"批准／驳回" |
| **7 提交前跑 `python verify/check.py`；红了不许绕过** | ★ 符合（★ 这是对**现状**的读数，不是对方案的判） | ★ 实测（附录 A1）：命令 `python verify/check.py`（workdir＝`D:\Code\13-aios-worldcore`）⇒ `=== 结论：全绿（rc=0）===`；★ 7 条判据全 `[GREEN]`，★ `c3_action_name_gate.py` 报「翻译链已查表并可拒（扫 30 件）」 |
| **8 判据住 `verify/`；`ninedim/` 只装档案** | ★ 无法判定（无对象） | ★ 本席未审待评方案是否往 `ninedim/` 加脚本；★ 现取 `python verify/check.py` 的 `c2_domain_files_only.py` 报「共扫 135 件，全为档案」⇒ ★ 现状绿，★ 但"将来会加什么"无法据现状判 |
| **9 加判据先写会红的反例** | ★★ **不符合** | ★★ 现取 `grep`（附录 A2）：对材料包 §一 逐件点名的**10 件待评方案**扫 `会红`／`反例`／`self-test` ⇒ ★ **三个词各 0 命中**；★ 唯一命中落在**材料包自身**（`会红` 3 处，且都是复述硬约束 7/9）。⇒ ★ **10 件方案里没有任何一条会红的判据** |

### §二 · 禁区（`AGENTS.md` §四）

| 条款 | 判 | ★ 证据 |
|---|---|---|
| **禁区 1：上游安全底线**（`INV-001..034`／AI 只提议不执行／**证据只追加**／`ObjectKind` 闭枚举与不可变版本链） | ★ **不符合（就"证据只追加"这一支）** | ★ 现取 `SampleKind` 变体逐字只有 `Delete`／`Put`（docs.rs `zenoh/1.10.1/.../sample/enum.SampleKind.html`），且 `SampleBuilder::delete(key_expr)` 是一等构造器。★ 而本仓红线逐字（`设计-总线该实现什么-合并清单-v0.1.md` §7.2）：「**不许用删除代替撤回**——不许 `rm` 字节、不许删最后一行、不许 compaction／截断来"救"坏记录」；★ 同件 §3 #24 逐字「**撤回=再写一条** `change`」。⇒ ★ **`kind=Delete` 是一条"删除"的现成口子**；★ 10 件方案里**没有一句**说校验层拒它（记入缺口 G5） |
| **禁区 2：上游 8 道企业出口门不许软化** | ★ 无法判定 | ★ 10 件方案里**未触及**这 8 道门（★ 本席未核到任何一处点名）⇒ ★ 属"本席没读到"，★ 不是"没有"（★ 记入"本席没做的事"） |
| **禁区 3：B-3 不接 RDF/OWL 运行时** | ★ 符合 | ★ `决策-载荷与机制都用现成的.md:48-55` 的候选表逐条（CloudEvents／Zenoh `Sample`／W3C Trace Context／JSON Schema／AsyncAPI／JWT-JWS）**无 RDF/OWL 推理**；★ 本仓现状旁证：`原子登记-语义面.md:40` 逐字「全仓 `TBox｜ABox｜RDF｜OWL｜SHACL｜SPARQL` 六个目录命中数为 **0**」⇒ ★ 本方案不带推理运行时 |

### §三 · 语义口径（`CLAUDE.md` 逐字：动作名的权威来源＝本体 ⇒ 未登记即拒）

★ **判：符合** —— ★ 证据是**方案自己写下的那半句**：`决策-载荷与机制都用现成的.md:73` 逐字「★★★ **③ 名字查表（未登记即拒）** ｜ ★★★ `key_expr`（名字就是 key）**＋ 校验层查表**」。★ 有"＋ 校验层查表"⇒ ★ 权威**仍在我们的查表层**，★ 没有被挪到 key 空间。
★ 但★ **前提是那半句不能被读丢**：★ `key_expr` 本身**答不了"在册吗"**——★ Zenoh 官方手册（`zenoh.io/docs/manual/abstractions/`）逐字：Key Expression「denotes a **set of keys**」，「a small regular language to match sets of keys」⇒ ★ 它是**集合／模式**语言，不是名册。
⇒ ★ **这一条给"符合"，但把"读丢那半句"列为缺口**（G4：本席要求一条会红判据守住"查表在进 key 之前"，★ 今天 0 条）。
★ 附一条**现取**的旁证，说明"未登记即拒"今天**住在哪一层**：`verify/c3_action_name_gate.py:6-8` 自述逐字「★ **本条是文本级代理**：它只能证明「查表的符号与拒绝的符号同时出现在构造 Request 的那个文件里」，**不能**证明它编得过、也不能证明拒真的发生」⇒ ★ 它是一个**文本级代理**，真证在 VM 上的 `crates/aios-cognitive/tests/action_catalog_gate.rs`。★ 结论：★ **"未登记即拒"是"我们的查表层＋写路径"的性质，与总线是谁无关**；★ 换总线既不增也不减它。

### §四 · 作者历条令（材料包 §二·丁）

| 令 | 判 | ★ 证据 |
|---|---|---|
| ① 围着本体转 | ★ 符合 | ★ `决策-载荷与机制都用现成的.md:61-65` 把"进总线前按本体校验"列为"我们的活" |
| ② 分层乙（上游更新我们手动搬） | ★ 无法判定 | ★ 10 件方案未涉及上游搬运口径（本席未核到） |
| ③ **用我们的定义，装它的干活逻辑** | ★★ **不符合** | ★ 见上文"乙×乙 内部矛盾"：`调研-内容与机制分不分得开.md:31-33` 判「全借……**不行**」＋`:72` 收口「**借机制、不借载荷**」；★ 而 `决策-载荷与机制都用现成的.md:59` 逐字「★★★★★ 于是我们真正要写的，只剩**一件**」⇒ ★ 把"本体信封的字段表（含三张通行证）"从"我们的活"里**删掉**了 |
| ④ 能用人家的尽量用人家的 | ★ 符合 | ★ `决策-载荷与机制都用现成的.md:7-8` 作者令逐字：「我认为**这个协议头啥的用人家的就挺好的**，**能用人家的肯定尽量用人家的**」；★ 方案整体落在这一侧 |
| ⑤-a **能自足的不外引** | ★ 符合（★ 按 §理念张力裁决 的射程） | ★ 甲的原出处射程＝文档自足（同上逐字）；★ 而★ 依赖侧**材料自己也判了"不引"**：`方案-总线借市面上的什么.md:47` 逐字「★★ **先不引**（只是形状）」；`核对-三个候选与三层协议格式.md:15` 逐字「★ **我们只需它的字段表，不必引 SDK**」⇒ ★ 与甲相容。★ 记一条**边界**：★ 若真引 `cloudevents-sdk` 只为借字段形状，★ 那就撞上甲（记入缺口 G10） |
| ⑤-b 不做"探针"这类额外件 | ★ 符合 | ★ 方案提的"进总线前按本体校验"是**门禁**（有判据、进版本控制），★ 依 `worldcore-sdd` §四末条不属"探针"；★ 10 件方案未另造探针件 |
| ⑤-c **每条判据都必须会红** | ★★ **不符合** | ★ 现取 `grep`（附录 A2）：10 件方案 `会红`／`反例`／`self-test` **各 0 命中** |
| ⑤-d 读数必须带四要素 | ★ **部分符合**（两处判不同） | ★ **可复算的一处**：`核对-三个候选与三层协议格式.md:15` 写 `cloudevents-sdk` ★ **0.9.0**／★ **1,616,950** 下载；★ 本席现取 crates.io API（`crates.io/api/v1/crates/cloudevents-sdk`）复核：`"newest_version":"0.9.0"`／`"downloads":1616950` ⇒ ★ **逐字相符**。★ **不可复算的一处**：`决策-载荷与机制都用现成的.md:12-29` 的"现取方法名列表"★ **未给时点**，★ 且引的是**收**的一方（见 §五-B-1） |
| ⑤-e 绝不把"没做到"写成"做到了" | ★ 符合 | ★ 逐件都有"本件没做的事（如实）"：`决策-机制借Zenoh载荷自定.md:62-67`（4 条，含"没核 Windows 上 `shared-memory`"）／`决策-载荷与机制都用现成的.md:84-89`（4 条）／`调研-载荷协议与总线功能面.md:96-101`／`调研-内容与机制分不分得开.md:76-81`／`核对-三个候选与三层协议格式.md:59-63`（含逐字「★ **CloudEvents 官网正文没抓到**……★ **要引前必须核**」）／`对照-上游的总线是怎么做的.md:69-73`／`方案-两个面怎么分工与两套协议.md:105-109`／`方案-总线借市面上的什么.md:64-68`／`方案-总线与本体强相关.md:90-94`／`对照-架构五块与我们的位置.md:56-59,102-105` |

### §五 · ★★ 核心：逐条对"现取材料里的方法名是否足以支撑我们的需求"

★ **现取源**：`https://docs.rs/zenoh/1.10.1/zenoh/sample/struct.Sample.html`（HTTP 200）、`.../struct.SampleBuilder.html`（200）、`.../struct.SourceInfo.html`（200）、`.../enum.SampleKind.html`（200）；★ 规则面的现取源是 Zenoh 官方手册 `https://zenoh.io/docs/manual/abstractions/`（200）。★ 全部逐字引文见文末附录 B。

#### A. ★ 先说一个**前提性**的现取事实（它决定整张表怎么读）

★ docs.rs `Sample` 页首逐字：**「The Sample structure is the data unit **received** by Subscriber or Querier or Session::get. It contains the payload and all metadata associated with the data.」**
★ `SampleBuilder` 页首逐字：**「As the Sample struct is **not mutable**, the SampleBuilder can be used to create or modify an existing Sample instance or to create a new one from scratch for storing it for later use.」**
★ 现取 `Sample` 的写法字段：`pub struct Sample { /* private fields */ }` ＋ `#[non_exhaustive]`；★ 方法表里**没有 `new`**（`grep id="method\."` 得 36 个，其中与数据有关的正是 T-130 引的那 14 个，其余是 `Clone`／`Sink`／blanket）。
⇒ ★ **T-130 §一 引的是"收"的那一方**，而"皮一个槽都不用自己造"这句要成立，★ 引的应当是**送**的那一方 `SampleBuilder`（`put`／`delete`／`keyexpr`／`payload`／`timestamp`／`source_info`／`attachment`／`encoding`／`priority`／`congestion_control`／`express`／`reliability`／`timestamp_instrumentation`）。
★ **结论方向**：★ 对（Builder 上的槽与 Sample 同名同义）；★ **但现取对象错了一半**，★ 且这一错**有后果**：★ 只有看了 Builder 才知道 `attachment` 的签名是 `<U: Into<OptionZBytes>>`（★ **可选**），`source_info` 是 `<S: Into<Option<SourceInfo>>>`（★ **可选**）⇒ ★ **皮对通行证是"可选"的**（见 B-6）。
★ 现取（附录 A2）：★ 10 件方案里 `SampleBuilder` 一词 **0 命中**。

#### B. T-130 §一 那张"我们要的 × 现成槽"表，逐条对

★ 下表**左栏＝T-130 §一 的原话**，**右栏＝本席现取读数**。

| # | T-130 的映射（逐字） | ★ 本席判 | ★ 现取证据 |
|---|---|---|---|
| 1 | **名字（在册吗）** ← `key_expr` | ★ **不符合** | ★ `Sample::key_expr(&self) -> &KeyExpr<'static>` 存在（stable）——★ 但 `key_expr` **不是名字**，是**集合**。Zenoh 官方手册逐字：Key Expression「denotes a **set of keys**」；★ 且对 key 的约束逐字：「It is a `/`-joined list of **non-empty** UTF-8 chunks. This implies that leading and trailing `/` are forbidden, as well as the **`//` pattern**.」「An individual key may not contain the characters `*`, `$`, `?`, `#`.」★ 而我们的名字逐字是 `world://<ns>/<name>`（`crates/aios-worldcore/src/core/types.rs:13` 逐字「主体：一个在册的名字（`world://<ns>/<name>` 形状）」）★ **含 `//`** ⇒ ★ 必须改写；★ 材料只给了 T-129 §四 一条"拿掉 `://`"的示意，★ **没有单射性证明、没有禁字约束、没有判据**。★ 另：★ KE 还能 `*`／`$`*／`**` 通配 ⇒ ★ **"名字"与"订阅模式"必须在类型上分开**（★ 现取：crate 里有 `nonwild_keyexpr`／`OwnedNonWildKeyExpr` 两个类型，★ 材料**未提**） |
| 2 | **谁发的** ← `source_info` | ★★ **不符合** | ★ 三条：★① 语义不对——`SourceInfo` 页逐字：「Information on the **source of a zenoh Sample**… contains the unique identifier of the **zenoh entity** that published the sample… and a sequence number」⇒ ★ 是**传输身份**（`EntityGlobalId`＋`SourceSn`），不是本体在册主体（我们的 `envelope.fields.actor` 逐字「string  # 世界内身份，如 `world://user`」）。★② 不是信任锚——同页逐字：「**It is the sender's responsibility to include SourceInfo when desired and to assign the entity identifier and sequence number.** The base zenoh primitives only transmit SourceInfo **without any additional processing or validation**.」★③ 是 unstable——`Sample::source_info`／`SampleBuilder::source_info` 两处都标「**Available on crate feature unstable only**」＋「This API has been marked as unstable: it works as advertised, but it **may be changed in a future release**」。⇒ ★ **正面回答任务那一问：会因为"头是别人的"而丢掉本体对名字的权威——只要把 `actor` 的取值来源挪到 `source_info`。**★ 且本仓**已有**这条口径的载体：`设计-总线该实现什么-合并清单-v0.1.md` §3 #5（口→主体绑定）／#7（逐字「**每帧 `actor` 非空且等于该连接绑定主体**」）＋ §6 判据 1／2／3（三条都会红） |
| 3 | **什么时候** ← `timestamp` | ★ **无法判定**（★ 缺一句"替换还是叠加"） | ★ `Sample::timestamp() -> Option<&Timestamp>`／`SampleBuilder::timestamp<U: Into<Option<Timestamp>>>` 都在（stable）——★ 但**类型不同**：Zenoh 用 `uhlc`（现取依赖表：`uhlc ^0.8.0`），我们的 `at` 逐字是「integer  # 时间戳，Unix 秒。**顺序由 `seq` 决定，`at` 只作辅助**」；★ 而 T-124 §三 又把同一格映到 CloudEvents 的 `time`（RFC3339 字符串）。⇒ ★ **同一格三种类型** ⇒ ★ 若"替换"⇒ 与 `envelope-validation.spec.md:53-55`（按本体声明判类型，码 `ext.world.Ontology.BadFieldType`）**直接冲突**；★ 若"叠加"⇒ 无冲突。★ **方案没说**（缺口 G1） |
| 4 | **载荷** ← `payload`（任意字节） | ★ **符合** | ★ 同页 `payload(&self) -> &ZBytes`；★ `SampleBuilder::put<IntoKeyExpr, IntoZBytes>(key_expr, payload)` ⇒ `Into<ZBytes>`；★ 现取 Zenoh 1.10.1 依赖表含 `bytes ^1.11.0` ⇒ ★ **任意字节**成立（与 `调研-内容与机制分不分得开.md:31` 的现取一致） |
| 5 | **载荷是什么格式** ← `encoding` | ★ **符合**（★ 但**不承载词表版本**） | ★ `Sample::encoding(&self) -> &Encoding`（stable）／`SampleBuilder::encoding(...)` ⇒ 可声明 `application/json` 一类；★ 它只说**媒体类型**，★ 词表版本要另找落点（见 6） |
| 6 | **我们自己的通行证（`world`／`vocab_hash` 等）** ← `attachment` | ★★ **不符合** | ★ 三条：★① **皮不要求**——`Sample::attachment() -> Option<&ZBytes>`；`SampleBuilder::attachment` 逐字「Sets an **optional** attachment… accepts both `Into<ZBytes>` and `Option<Into<ZBytes>>`」⇒ ★ `Option` ⇒ ★ **"对不上即拒"不可能由皮承担**。★② **形状无载体**——`attachment` 是"任意字节"，★ 这正是 `worldcore-sdd` §十五 F 逐字点名的形态：「**借一个"形状不由本体声明"的格来装新语义 ⇒ 它读不出来、漂了也不会红**」，处置逐字：「**要装新语义，先问"它的形状有没有载体"；没有 ⇒ 先声明形状（走评审），再往里面放。**」★ 本仓**已有同形态现场**：`crates/aios-ontology/data/ontology.json:55` 逐字「`payload` 的形状本体**不声明**」。★③ **同词两义**——本仓本体 `fields` 表里**已经有一个叫 `attachment` 的字段名**（`crates/aios-ontology/data/ontology.json:1200`，`"本仓写法": null`，`状态: ★ 非原子（今天没有对应写法）`）⇒ ★ `worldcore-sdd` §八「**同词不许两义**」点名形态 |
| 7 | **QoS（可靠／优先／拥塞／快速）** ← `reliability`／`priority`／`congestion_control`／`express` | ★ **部分不符合** | ★ `priority`／`congestion_control`／`express`（`Sample::express(&self) -> bool`）**stable**；★ `reliability` **unstable-only**（`Sample::reliability` 与 `SampleBuilder::reliability` 两处都带「Available on crate feature unstable only」＋"may be changed"）。⇒ ★ T-130 把四件**并列**成"现成的槽"而**未标其中一个是 unstable** ⇒ ★ **叙述强于读数**（缺口 G3） |
| 8 | **撤回（不是发）** ← `kind`（Put／Delete） | ★ **无法判定**（材料未声明约束） | ★ 现取 `SampleKind` 变体逐字只有 `Delete`／`Put`；★ `Sample::kind(&self) -> SampleKind`；★ `SampleBuilder::put`／`SampleBuilder::delete`。★ **两处相撞**：★① **同词两义**——我们的 `envelope.fields.kind` 逐字是「enum(change, act, notice)  # 三个家族」⇒ ★ 家族名 vs 发布/撤回，**一个词两个意思**；★② **红线接触面**——`设计-总线该实现什么-合并清单-v0.1.md` §7.2 逐字「**不许用删除代替撤回**」⇒ ★ 若 `kind=Delete` 能落在 `world/**` 上而不经我们的撤回形态，★ 那就是禁区 1「证据只追加」的现成口子（缺口 G5） |

#### C. ★ 还有两条**T-130 完全没提**、但对"头是别人的"是致命的

1. ★★ **双头**：★ CloudEvents 的核心属性（`id`／`source`／`type`／`time`／`subject`／`datacontenttype`／`data`）与 Zenoh 的槽（`key_expr`／`source_info`／`timestamp`／`payload`／`encoding`）**语义重叠但不等价** ⇒ ★ "谁发的／什么时候／什么名字"在**同一条事件上有两个可写处** ⇒ ★ 撞 `worldcore-sdd` §八「**一个事实，只有一个权威载体**」＋ `设计-总线该实现什么-合并清单-v0.1.md` §7.7 逐字「**不许用机器的话盖掉世界的话**——不许用对端凭据或核心时钟覆盖 `actor`／`at`」。
2. ★★ **方案与本体已声明的 8＋2 格零引用**：★ 10 件方案 `envelope` 一词 **0 命中**（附录 A2），★ 而本体逐字（`crates/aios-ontology/data/ontology.json:5-18`）已经把 `required`＝`world/kind/id/seq/at/actor/flags/body`、`optional`＝`to/trace` 写死。⇒ ★ 本席在本部分**无法判定**"借来的头"与"我们的头"是**一套**还是**两套**。

---

## 发现的缺口

★ 逐条，带证据。★ 每条都指到一处**件＋行**或一条**命令**。

- **G1（本席判"有條件通過"的第一因）★ "替换 vs 叠加"未声明**。证据：`决策-载荷与机制都用现成的.md:31-44` 把"我们要的"逐条映到 Zenoh 槽（含"我们自己的通行证→`attachment`"），`:69-73` 又把通行证分落 `key_expr`／`attachment`；★ 全篇**无一句**说这些槽与本体 `envelope.required`（8 格）是替换还是叠加（现取 `grep envelope` 在 10 件方案内 = 0）。★ 后果分叉：替换 ⇒ 撞 `envelope-validation.spec.md:32-33`／`:53-55`；叠加 ⇒ 无冲突。★ 条件 **C1**。
- **G2 ★ 现取对象错了一半**。证据：docs.rs `Sample` 页首逐字「the data unit **received** by Subscriber or Querier or Session::get」；`SampleBuilder` 页首逐字「As the Sample struct is **not mutable**, the SampleBuilder can be used to create or modify an existing Sample instance」；★ `Sample` 无构造器（`/* private fields */`、`#[non_exhaustive]`、方法表无 `new`）；★ 现取 10 件方案 `SampleBuilder` 命中 **0**。★ 条件 **C6**。
- **G3 ★ 两条槽是 unstable**：`Sample::source_info`／`Sample::reliability`／`Sample::timestamp_stack`／`SampleBuilder::source_info`／`SampleBuilder::reliability`／`SampleBuilder::timestamp_instrumentation` 全部标「Available on crate feature **unstable** only」＋"may be changed in a future release"；★ 10 件方案里 `unstable` 命中 **0**。★ 条件 **C6**。
- **G4 ★ 通行证②落 `attachment` 是"形状无载体"的口袋 ＋ 皮不要求它 ＋ 同词两义**。证据：`Sample::attachment() -> Option<&ZBytes>`；`SampleBuilder::attachment` 逐字"optional"；`worldcore-sdd` §十五 F 逐字；`crates/aios-ontology/data/ontology.json:1200` 已有名为 `attachment` 的字段；★ 且 `调研-载荷协议与总线功能面.md:87-92`／`方案-两个面怎么分工与两套协议.md:84` 原本把"本体信封的字段表（含三张通行证）"列为**我们的活**。★ 条件 **C2／C5**。
- **G5 ★ `kind=Delete` 与"不许用删除代替撤回"的接触面未处置**。证据：`SampleKind` 只有 `Delete`／`Put`；`SampleBuilder::delete(key_expr)`；`设计-总线该实现什么-合并清单-v0.1.md` §7.2 逐字；★ 10 件方案无一句约束。★ 条件 **C1**。
- **G6 ★ 双头**（CE 与 Zenoh 各一套"谁发的／什么时候／什么名字"）。证据：`决策-载荷与机制都用现成的.md:48-51`（CE 字段表）＋ `:16-29`（Zenoh 槽）；`worldcore-sdd` §八「一个事实，只有一个权威载体」；`设计-总线该实现什么-合并清单-v0.1.md` §7.7 逐字。★ 条件 **C1**。
- **G7 ★ keyexpr 字符集／单射／通配**：Zenoh 官方手册逐字（`//` 禁；单 key 不得含 `* $ ? #`；canon form 两种写法必须同串）；★ `决策-机制借Zenoh载荷自定.md:66` §六.3 逐字自认「★ **没核** Zenoh 的 **keyexpr 允许的字符集**（★ 我们的名字里有 `://`，★ 要转成 `/`）」；★ 现取 crate 已有 `nonwild_keyexpr`／`OwnedNonWildKeyExpr`，★ 材料未提。★ 条件 **C4**。
- **G8 ★ CloudEvents 字段表未核**（材料自认）。证据：`核对-三个候选与三层协议格式.md:63` 逐字「★ **CloudEvents 官网正文没抓到**（★ `raw.githubusercontent` 那一跳失败）⇒ ★ 本件关于它**字段表**的部分**仍是按已知口径**，★ **要引前必须核**」。★ 本席**也没拿到**（`raw.githubusercontent.com` 与 `github.com` 两次 `fetch failed`；`cdn.jsdelivr` 一跳被拒）⇒ ★ 按 `worldcore-sdd` §六「**"形状取自" ≠ "符合"**」，★ 任何"落在扩展属性"的话**今天只是形状取自**。★ **可能性已收窄到一点**（§六"把'我不知道'从一片收成一点"）：★ 现取 `cloudevents-sdk 0.9.0` 的 API 逐字 `pub fn set_extension<'name, 'event: 'name>(&'event mut self, extension_name: &'name str, …)` ⇒ ★ **名称是自由 `&str`，SDK 的类型面不校验名称**；★ 若规范对扩展属性名有字符约束，★ **它不会在编译期拦住**（★ 我**没有**断定规范一定有此约束——**查不出就写查不出**）。★ 条件 **C6**。
- **G9 ★ 落点不在原子登记面**（硬约束 1）。证据：`原子登记-语义面.md:25-26` 只有 `A-SEM-01`／`A-SEM-02`；`:7` 逐字「**模块号唯一出处＝本件**」；★ 待评方案的核心动作**没有原子号**。★ 条件 **C5**。
- **G10 ★ "我们的活只剩一件"与既存两处口径不符**。证据：`调研-载荷协议与总线功能面.md:87-92` 逐字「我们真正要自己写的只有**两件**」；`方案-两个面怎么分工与两套协议.md:84` 逐字「**本体信封的字段表**（含三张通行证）＋ **取件码的格式**｜★★★ **我们定**」；★ 而 `决策-载荷与机制都用现成的.md:59` 逐字「只剩**一件**」。★ 且★ 本仓**已有**信封的实现面：`crates/aios-worldcore/src/core/types.rs:12` 逐字「本体里对应：`envelope.actor`（信封里的「谁」）」；`:185` 逐字「本体里对应：`envelope`（信封）＋ `families`」。
- **G11 ★ 信封编码三说**。证据：`调研-载荷协议与总线功能面.md:18`（**CBOR 为主 ＋ JSON 调试孪生**，并逐字"生产期 CBOR"）vs `核对-三个候选与三层协议格式.md:34`／`方案-两个面怎么分工与两套协议.md:34,56`（逐字"**JSON 或 protobuf**"）⇒ ★ 同一格三个答案，★ 而 `encoding` 槽只能声明一个。
- **G12 ★ 没有回去引仓内已有的总线口径件**。证据：`ninedim/01-意图环/03-设计/设计-总线该实现什么-合并清单-v0.1.md` 已在仓内（451 行，§3 共 54 条、§6 共 25 条会红判据、§7 共 15 条红线）；★ 10 件方案里**无一处**引它（★ 与本仓 `worldcore-sdd` 动手总则①"先读现状"＋③"**同一个仓里已有的口径，先回去引，别另起一句**"相悖）。★ 举三条直接相关的：§7.3「不许让总线持有状态」／**§7.4「不许总线自持白名单」**／§7.14「不许引一个持有状态的现成 broker 当"总线"」；★ §3 #21「统一线格式 ＋ `plane` 判别」／#45「分帧与行上限」——★ Zenoh 是**自带 line format／routing／可加 storage 插件**的一整套，★ **与这三条的关系必须逐条表态**（★ 本席只登记，★ 机制面的判断归 `rev-mech`）。
- **G13 ★ 有效性的两点如实登记**（不属本席的部分，但本席核到了）：
  - ★ **冻结与现读可对齐（好消息）**：★ 材料包 §一 冻结号是 `de1b480`，★ 而任务书与本席现读的 HEAD 是 `af095ac`。★ 实测：`git rev-list --count de1b480..af095ac` ＝ **1**；`git diff --stat de1b480 af095ac -- ninedim/06-变更/2026-10-13-aios-semantic-plane/` ＝ **1 file changed, 108 insertions(+)**，★ 且变更的**只有材料包本身**（新增）。⇒ ★ **10 件待评方案在 de1b480→af095ac 之间逐字未动**，★ 本席在 af095ac 上的读数对它们**等同于**在冻结号上的读数。
  - ★ **席位表的独立性档与实况不符**：★ 见本件开头"独立性档"。★ `nd-review` §二·8 逐字「**未派的席位如实登记为「未派」**，不许冒充已评（**红线**）」——★ 同一把尺子的另一头是：★ **不许把「丙」登记成「乙」**。★ 请 Lead／作者处置。

---

## 本席没做的事

★ 逐条，如实；★ 不用"已并入别处"这类话遮。

1. ★ **没实测任何 Zenoh／CloudEvents API**：宿主无 cargo（`原子登记-语义面.md:60` 逐字「宿主有无 cargo ｜ **无**」），★ 本席**未上 VM** ⇒ ★ 本判词关于 API 的每一句都是**现取官方文档**，★ 不是编译／运行读数。★ 因此"皮够不够用"这个判断的强度上限是**文档级**。
2. ★ **没拿到 CloudEvents 规范正文**（`github.com`／`raw.githubusercontent.com` 两次 `fetch failed`）⇒ ★ **扩展属性名的字符约束这一条，本席写"查不出"**，★ 只把可能性收窄（SDK 的 API 面不校验）。
3. ★ **没核 10 件方案的每一笔是否在 `改动对照.md` 有对应行**（硬约束 4）⇒ ★ 该条给"无法判定"，★ 不是"合规"。
4. ★ **没核禁区 2（上游 8 道企业出口门）与本方案的关系** ⇒ ★ 10 件方案里本席未读到点名，★ 但"没读到"≠"没有"。
5. ★ **没做机制选型（Zenoh 本身好不好）的判断** ⇒ ★ 那是 `rev-mech` 的部分；★ 本席只登记 G12（与 §7.3／§7.4／§7.14 的关系须表态），★ **不下结论**。
6. ★ **没判通行证与校验层的可落地方案** ⇒ ★ 那是 `rev-pass` 的部分；★ 本席只判"落在 `attachment`／扩展属性"这一形态对**载荷与头**这一面成不成立。
7. ★ **没测性能、没估工作量、没有数据面读数** ⇒ ★ 那是 `rev-data` 的部分。
8. ★ **没有验证"会红反例"**（本席给不出任何一条自造反例的实跑读数）⇒ ★ 那是**测试席 `rev-test`（有效性②必到）**的部分；★ 本席只报"10 件方案里 0 条会红判据"这一**现取读数**。
9. ★ **没有碰任何代码、任何盒里件**。★ 本席只写 `ninedim/06-变更/2026-10-13-aios-semantic-plane/判词-payload.md` 这一个文件。★ 只读的**三明治**（`sha256`＋字节数）：★ 11 件材料的清单见文末附录 A3（写入前）；★ 写入后本席**复取同 11 件**，读数见附录 A4（★ 它只证"本席在这段时间没写它们"，★ **不证"世界没变"**）。
10. ★ **没有下"批准／驳回"**（框架变更层，硬约束 6 只有人能下）；★ 本席给的是**模块级**枚举（通过／有条件通过／退回）＋ 发现清单。
11. ★ **没有在判词里给出"乙档独立"的证据**，★ 因为拿不到（见开头）。
12. ★ **没核** `决策-载荷与机制都用现成的.md:86` 提的 "`attachment` 的大小上限与性能"／`:88` 提的 "`keyexpr` 字符集"（后者本席**部分补上**：允许集与禁字，见 G7）／`:87` 提的 "cloudevents-sdk 与 `attachment`／`payload` 直接对接"。★ 这三条仍**未核**，★ 只把第 2 条从"未知"收窄到"禁字已明、单射仍缺证据"。

---

## 附录 · 本席读数的四要素

★ **口径**：命令 ／ 原始输出（逐字）／ 环境版本 ／ 提交号。★ 时点一律给，★ 因为读数会过期。

**环境**（同一段读数窗口内现取）：
- 提交号 `af095ac9c72512151d3893b18f6127144f32af22`（`git -C D:\Code\13-aios-worldcore rev-parse HEAD`）
- 宿主：Windows；`python 3.12.10`；工作目录 `D:\Code\13-aios-worldcore`（`pwd` ＝ `D:\Code`，★ 故所有命令显式带仓根）
- 时点：`2026-10-14T19:54:19.7347231+08:00`（宿主钟，`Get-Date -Format o`）★ ★"时点带来源"：**宿主钟**
- 工作树：★ 本席开工时 `git status --porcelain` 有 **1** 项未跟踪（`?? ninedim/06-变更/…/判词-test.md`，★ 别的席正在写，★ **不是本席**）

**A1 · 我方判据基线**
- 命令：`python verify/check.py`（workdir ＝ `D:\Code\13-aios-worldcore`）
- 原始输出（逐字节抄，★ 只抄末三行与关键行）：`[GREEN] c3_action_name_gate.py` → `[GREEN] 翻译链已查表并可拒（扫 30 件）`；★ 末行 `=== 结论：全绿（rc=0）===`；`EXITCODE=0`；★ `c2_domain_files_only.py` 报 `共扫 135 件，全为档案`
- ★ **两条不同时刻的读数，本席不当矛盾**：★ 同一次基线里 `check.py` 自报「工作树：**0** 个未提交改动」，而本席另一条现取（`19:54:19`）读到**1** 件未跟踪 ⇒ ★ 两者**时点不同**（别的席在写盘），★ 按 `worldcore-sdd` §八「**不可比的读数不能相减**」，★ 本席**不**据此推断"谁写了什么"。
- ★ **写入本件之后的第二次跑**（时点 `19:57` 前后）：命令同上 ⇒ ★ 仍 `=== 结论：全绿（rc=0）===`／`EXITCODE=0`；★ `c2_domain_files_only.py` 报「共扫 **140** 件，全为档案」（★ 扫描面变大＝本席与另外两席的判词进盘）；★ `c4_eol_consistency.py` 报「段一 0 件工作树干净」⇒ ★ **本件是 LF、无 BOM**（另测：`CR=0 LF=234 CRLF=0`，首 3 字节＝`35,32,229`＝"# 判"，★ 无 BOM）。

**A2 · 10 件方案里的关键词命中（现取 `grep`）**
- 命令（判据工具＝`grep`，面＝`ninedim/06-变更/2026-10-13-aios-semantic-plane/`，取与材料包 §一 点名的 10 件求交）
- 原始输出：`[会红] total=74  在 10 件待评方案内: ∅`；`[反例] total=104 … ∅`；`[self-test] total=21 … ∅`；`[SampleBuilder] total=0 … ∅`；`[unstable] total=0 … ∅`；`[envelope] total=43 … ∅`
- ★ 射程（扫了什么）：★ 全部扫描面＝该 change 目录下**所有件**；★ "∅"指的是**与那 10 件求交**之后为空（★ 不是全目录为空）。★ 时点同上。

**A3 · 只读三明治 · 写入前**（`sha256`＋字节数；命令＝`Get-FileHash -Algorithm SHA256`）

```
H 6d94320cb5511d169a21d82e73b09654e06ac64d17baadb672755d4e7712e4a6 6831 评审-总线选型-材料包与席位表.md
H a7d6099c0a7d0414990c12f5bd61d390af5ac6d31c2dc17213d3ebd5b9d029cf 3898 决策-机制借Zenoh载荷自定.md
H 44efa4acefbc11573c5108d096c1921062fe6dfaa5d1a4c76ac2218b444931a5 5331 决策-载荷与机制都用现成的.md
H c92533a28cdde30c45eceeac9d40fdabcfa5b82b7a7e8387d1e4d9b2dffdaa1f 7305 调研-载荷协议与总线功能面.md
H b8148080466d6deba95ee07041de241283612f7f62003b01af95ae43fb260aaa 6195 调研-内容与机制分不分得开.md
H 510b221366696a5168ea3d51b474d51ba6b86627f6672d5a705bd58816ca091f 5038 核对-三个候选与三层协议格式.md
H 5cf2e8c32ec2bc6119748fecbca6c7eb09be01aac5833040b8987270e2ad9039 4496 对照-上游的总线是怎么做的.md
H 0ee9e4099b213cfc1de3f97f6674fe724a6de83b89bcd4bcf776d22778bbde8e 7337 方案-两个面怎么分工与两套协议.md
H ab2209dc2745816f848bd63ad6d8faf8e4ee3cfca5db5dd14f06354b8ecaab69 6390 方案-总线借市面上的什么.md
H 2f38a162e9ff2062145a502d310ab72e6bf46925240c534dc4a54c03bc4f5bcc 7141 方案-总线与本体强相关.md
H c5ec96cbf77c5fb0cdd473b923b2eb0232168c963fb90b4922269e8714d966c4 7293 对照-架构五块与我们的位置.md
```

**A4 · 只读三明治 · 写入后**：见本件末尾"写入后复取"一节（★ 由本席在同一会话内追加，★ 11 件哈希若与 A3 逐字相同 ⇒ 本席在这段时间**未写**它们；★ **不证世界没变**）。

**A5 · 冻结号与现读的对齐（附录 G13 的读数）**
- 命令：`git -C D:\Code\13-aios-worldcore rev-list --count de1b480..af095ac` ⇒ `1`
- 命令：`git -C D:\Code\13-aios-worldcore diff --stat de1b480 af095ac -- 'ninedim/06-变更/2026-10-13-aios-semantic-plane/'` ⇒ `1 file changed, 108 insertions(+)`，★ 文件名＝`评审-总线选型-材料包与席位表.md`

**B · 外部现取（全部 `web_fetch`，HTTP 200）**
- `https://docs.rs/zenoh/1.10.1/zenoh/sample/struct.Sample.html`：★ 页首逐字「The Sample structure is the data unit **received** by Subscriber or Querier or Session::get.」；★ 签名逐字 `pub fn key_expr(&self) -> &KeyExpr<'static>`／`pub fn payload(&self) -> &ZBytes`／`pub fn kind(&self) -> SampleKind`／`pub fn encoding(&self) -> &Encoding`／`pub fn timestamp(&self) -> Option<&Timestamp>`／`pub fn attachment(&self) -> Option<&ZBytes>`／`pub fn source_info(&self) -> Option<&SourceInfo>`（后两条带 unstable 注）
- `https://docs.rs/zenoh/1.10.1/zenoh/sample/struct.SampleBuilder.html`：★ 页首逐字「As the Sample struct is **not mutable**, the SampleBuilder can be used to create or modify an existing Sample instance…」；★ `pub fn put<IntoKeyExpr, IntoZBytes>(key_expr, payload)`／`pub fn delete<IntoKeyExpr>(key_expr)`／`pub fn attachment<U: Into<OptionZBytes>>(self, attachment: U)`（逐字"optional"）／`pub fn source_info<S: Into<Option<SourceInfo>>>`（unstable）
- `https://docs.rs/zenoh/1.10.1/zenoh/sample/struct.SourceInfo.html`：★ 逐字「Information on the source of a zenoh Sample… unique identifier of the **zenoh entity**… **It is the sender's responsibility to include SourceInfo when desired and to assign the entity identifier and sequence number.** The base zenoh primitives only transmit SourceInfo **without any additional processing or validation**.」
- `https://docs.rs/zenoh/1.10.1/zenoh/sample/enum.SampleKind.html`：★ 变体逐字 `Delete` `Put`
- `https://zenoh.io/docs/manual/abstractions/`：★ 逐字「Key Expression denotes a **set of keys**」；「It is a `/`-joined list of **non-empty** UTF-8 chunks. This implies that leading and trailing `/` are forbidden, as well as the **`//` pattern**.」；「An individual key may not contain the characters `*`, `$`, `?`, `#`.」；★ canon 规则逐字「only a **canon** form is allowed for key expressions」
- `https://docs.rs/zenoh-keyexpr/1.10.1/zenoh_keyexpr/index.html`：★ 逐字「⚠️ WARNING ⚠️ This crate is intended for Zenoh's **internal use**.」；★ 逐字提到 `KeFormat`／`kedefine`（★ 可用于把我们的 KE 空间做成编译期格式——★ 材料未提）
- `https://docs.rs/cloudevents-sdk/0.9.0/cloudevents/`：★ 逐字「This crate implements the **CloudEvents Spec for Rust**」；★ 示例逐字 `EventBuilderV10::new().id("my_event.my_application").source("http://localhost:8080").ty("example.demo").time(Utc::now())`
- `https://docs.rs/cloudevents-sdk/0.9.0/cloudevents/event/struct.Event.html`：★ 逐字 `pub fn set_extension<'name, 'event: 'name>(&'event mut self, extension_name: &'name str, extension_value: impl Into<ExtensionValue>)`
- `https://crates.io/api/v1/crates/cloudevents-sdk`：★ 逐字 `"newest_version":"0.9.0"`／`"downloads":1616950`（★ 与 `核对-三个候选与三层协议格式.md:15` 的读数**逐字相符**）

**★ 本附录不能证明的事**：★ 以上都是**文档读数**；★ 哪一条 Zenoh 的 **feature flag** 默认开／关、`unstable` 门怎么打开、`attachment` 的实际尺寸上限，★ **本席一律没测**（宿主无 cargo）。

---

## 写入后复取（附录 A4 的落点）

★ **命令**：`Get-FileHash -Algorithm SHA256` ＋ `Get-Item … .Length`（对 A3 那 11 件逐个复取）
★ **时点**：`2026-10-14T19:56:34.2320317+08:00`（宿主钟）
★ **原始输出**：★ 11 件的 `sha256` 与字节数**与附录 A3 逐字相同**（逐件对照，无一例外）⇒ ★ **只是"本席在这段时间没写它们"**；★ ★**不证"世界没变"**（别人也在写：本席开工时工作树里已有 `判词-test.md` 一件未跟踪件）。
★ **本件自身的读数**：追加本节**之前**，`判词-payload.md` ＝ `sha256 7664a099918ae7d54ca6c285b74aa97d261b7e87b61084c766bb48b6ca6107a2`／`45693` 字节。★ 追加本节后本件的哈希**必然改变** ⇒ ★ **本件的哈希是【带时刻的读数】，不是【它的身份】**（`worldcore-sdd` §八 逐字：「**账本哈希是【带时刻的读数】，不是【账本的身份】**」——同一把尺子）。★ 要复算本件请以**当场命令输出**为准，★ **不要引用本行这个数当身份**。

**★ 本节不能证明的事**：★ 它证不了本席没有在**别的时刻**写别的件；★ 它证不了本席的判词**内容**是对的（那要别人按 §逐条／§发现的缺口 逐条复算）。
