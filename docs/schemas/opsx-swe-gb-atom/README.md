# opsx-swe-gb-atom · 项目级 OpenSpec 工作流（原子档）

**它是谁**：一套 OpenSpec 1.13.2 工作流（schema）。产物链仍是 OpenSpec 的五件——
`proposal → specs ∥ design → tasks → review`；它比既有的 `opsx-swe-gb` 多两样**可核的门禁面**：
`WC-ATOM-001` §四 的**最小原子化**（原子表**逐栏非空**；**栏数以 `templates/design.md` 的表头为准**）与**这一程踩过的经验**（每条给会红的执行者）。

**为什么这样定**：`opsx-swe-gb` 把流程侧要件收成了件内栏位，但它对"原子化"与"经验"只有**要求**、
没有**落点**——要求写在件里而没有栏位承接，就会退化成口号（skill §五：**没有反例的判据是装饰**）。
本档的做法是：**把这两样各落成模板里的必填栏位 ＋ 一个能跑出读数的命令**，让"没做到"在形态上就看得见。

落在 `docs/schemas/opsx-swe-gb-atom/`。用法：

```
npx --yes @fission-ai/openspec@1.13.2 new change <name> --schema opsx-swe-gb-atom
npx --yes @fission-ai/openspec@1.13.2 status --change <name>
```

⚠ **本档不替换默认档**：`docs/openspec-config.yaml` 的 `schema:` 现取仍是 `opsx-swe-gb`
（`spec_bridge.py` 判据③ 盯这一格）。要用本档，逐 change 加 `--schema`。
**把默认档改成 `opsx-swe-gb-atom` 属"改默认口径"**，要作者裁——见本件 §六。

---

## 〇、与书的关系（**上位规则**）

> **《语义世界》这本书是本项目一切规章制度的上位标准。** 三层关系与冲突处置沿用
> `docs/schemas/README.md` §〇 的现行口径（**书 ＞ 规格 ＞ 流程**），本件**不另立一套**——
> 一个事实只有一个权威载体（skill §八）。

本档在书这一层上的**唯一增量**是一条**栏位**：`templates/design.md` 的 **L5 覆盖边界**表
把「规格已定、只是今天没做到」的东西与「规格本身还没定」的东西分开放
（**能判红绿的进 L5、判不了红绿的进排除清单**——这就是书的 L5 与 L6 的分界，出处 `WC-ATOM-001` §四末注）。
**这一节不得被读成「能力已成立」**，它登记的正是「还没成立」。

**任何一次「不按书来」的处置，必须写全让路三要素**（让的是哪一条 `path:line` ＋逐字引文／为什么要让／谁批的）；
**半写＝不写**。执行者：`scripts/verify/spec_bridge.py` 判据⑦（按**件整体**判，三要素可分布在 proposal／design／tasks 里）。
本档把它做成 `templates/proposal.md` 的**必填栏**，没有让路处置时写「无」，**不许省掉栏位**。

---

## 一、判据：谁管什么（沿用三条）

1. **OpenSpec 有的 → 跟 OpenSpec。**
2. **OpenSpec 没有的 → 跟流程。**
3. **两边都有的 → 形态随 OpenSpec、内容随流程。**

出处：`docs/schemas/README.md` §一（本件**引用不复述**该节的表）。
本档与 `opsx-swe-gb` 的差别只在：**把第 2、3 条里"原子化"与"经验"这两块补上落点**。

### 1.1 与规格层的分工（一句话）

**规格写「世界必须怎样」，流程文档写「这个项目怎么干」。**
规格在 `ninedim/01-意图环/04-规格/`（一个能力一份 `spec.md`），change 在 `ninedim/06-变更/`。
本档**不往 `ninedim/01-意图环/04-规格/**` 里加任何新格式**：它只规定**写 delta 时**要遵守什么
（编号从流程侧取、证据行两形态、改完重跑生成链）。

### 1.2 与流程层的分工（一句话）

**流程侧管「责任、证据与边界」，本档管「一次改动的形状与生命周期」。**
流程侧的 S0–S7 交付物、R0–R8 评审、覆盖率门槛、H-01…H-26 硬条款，**内容权威仍在流程文档**；
本档只把其中**与一次改动直接相关的那几栏**变成 change 上的必填栏位，**载体是 `review.md`／`design.md`／`proposal.md`**。

---

## 二、四样融合各落在哪一条（**逐条给文件与命令**）

> 名字对照：`schema.yaml` 的 `artifacts[].id`（proposal／specs／design／tasks／review）、
> `templates/<id>.md`、以及 `schema.yaml` 的 `apply:` 段。

### 2.1 第 1 样 · **OpenSpec 整个体系**

| 落在哪一条 | 文件 ＋ 字段 | 复算命令 |
|---|---|---|
| 五件产物链与依赖（specs／design 由 proposal 阻塞；tasks 由 specs＋design 阻塞；review 由 tasks 阻塞） | `schema.yaml` 的 `artifacts:` 五条 `id`／`generates`／`requires` | `openspec status --change <name>` ⇒ 应见 `0/5 artifacts complete` 与逐条 `blocked by:` |
| 模板真的被解析到（不是写着好看） | `artifacts[].template` | `openspec instructions <id> --change <name> --json` ⇒ `template` **非空**（**长度不写死**——它随模板逐次变化；现取五个非空即可） |
| 形态门禁（delta 四个操作头、每 Requirement ≥1 个 `#### Scenario`） | `templates/spec.md` ＋ `schema.yaml` 的 `specs.instruction` | `openspec validate <name> --strict` |
| **默认档由 `config.yaml` 决定**（不是由 schema 存放位置的优先级） | `docs/openspec-config.yaml` 的 `schema:` | `spec_bridge.py` **判据③** 盯这一格 |
| **归档时没有任何东西会拦你**——`archive` 不是门禁 | `schema.yaml` 的 `tasks.instruction`／`review.instruction`／`apply.instruction` 三处都写明 | 实测：tasks 未全勾时 `archive --yes` 仍 `rc=0`，**且已把 delta 合并进主规格** |
| tasks 全勾这一条由**事后 lint** 复查（不是门禁） | `templates/tasks.md` 头注 ＋ `tasks.instruction` | `openspec validate --archived` ⇒ 未勾件报 `N incomplete tasks (x/y completed)` 并 rc=1，**红了要回退** |
| **`--skip-specs` 的边界**：纯文档／工具类 change 无 delta 时，须在 `.openspec.yaml` 写 `skip_specs: true` | `.openspec.yaml`（CLI 生成，**不手改**） | 不写 ⇒ `validate --strict` 报 `Change must have at least one delta` rc=1；写了 ⇒ rc=0 |
| ★ **precedence**：形式／机制按 OpenSpec；与流程冲突时**让给 OpenSpec** | `schema.yaml` 的 `fusion` 第 1 条（`source: openspec`）的 `evidence` 段内（含让路三要素） | 三要素齐；登记处 `docs/理论/冲突总账.md` 的同名新节（标题含`让路三要素`） |

### 2.2 第 2 样 · **国际软件开发流程（06-swe-gb 那套）**

判据现口径的**仓内可达**载体：`ninedim/06-变更/fc-2026-001-openspec-into-cm/boundary.md`
（⚠ 融合 skill 的 `SKILL.md` 本身**不在版本控制内**——本仓 `.agents/skills/` 下 git 只跟踪 `worldcore-sdd` 与 **6 个** `openspec-*` 技能；这一格已登记进 §六第 3 格）。
⚠ 旧版那句「同址双读／流程侧只留一行指针／每条 Requirement 标题带 REQ 号」**已作废**。

| 落在哪一条 | 文件 ＋ 字段 | 出处／复算命令 |
|---|---|---|
| **阶段与产物 S0–S7** | 不在本档内；本档只消费其**交付物编号** | `ninedim/01-意图环/01-策划/策划-WC-SDP-001-v0.1.md` |
| **评审 R0–R8** | `templates/review.md` §一 档位栏 ＋ §八 结论栏；`schema.yaml` 的 `review.instruction` | `ninedim/01-意图环/01-策划/策划-WC-SQAP-001-v0.1.md`；结论形式出处 `附件三-评审与门禁.md` 的「结论形式」列（**不引行号**：R4 三种／R5 两种） |
| **R5 ＝ 前置闸／R4 ＝ 后置闸** | `schema.yaml` 的 `review.instruction` 与 `apply.instruction` | `review` 的 `requires: [tasks]`、`apply.requires: [tasks]` |
| **签署（谁签、AI 不得代签）** | `templates/review.md` 的签署栏与执行者／批准者分离声明 | `spec_bridge.py` **判据⑥**（结论 ∈ 批准／通过／有条件通过 ∪ 驳回，且**批准人非空**）；**判据①**（归档目录必须有 `review.md`） |
| **基线（需求／框架／产品）** | 本档**不立基线**（不新增册子）；`templates/design.md` 的 Open Questions 要求把"只能由作者落笔"的事（签字／裁定／追认）明写谁做什么、落点指向登记者 | 无机器判据；基线三律的出处是 `附件五-配置与版本.md` |
| **配置管理与变更控制（CR／R5）** | `templates/proposal.md`：变更号**独占文档头的 `CR:` 一行**（**标题之下第 3 行**——第 2 行是空行；**不是**一张属性表）；一个 change 目录＝一份 CR | `spec_bridge.py` 编号桥；`ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md` |
| **追溯 RTM** | `templates/spec.md`：编号从流程侧取，取不到写「无号·待增补」 | `ninedim/01-意图环/02-需求/WC-RTM-001.csv`（现取 **14 列**，第 14 列「备注」是附录等价物）；`scripts/verify/trace_matrix.py` |
| **编号桥（互相指、不互相抄）** | `templates/spec.md` 的编号条 ＋ `generated/BRIDGE.md` | `spec_bridge.py` **判据④**（`generated/BRIDGE.md` 必须覆盖规格树下**每一条** Requirement） |
| ★ **precedence**：流程按 06-swe-gb；**机制／形式这一面的争执让给 OpenSpec** | `schema.yaml` 的 `fusion` 第 2 条（`source: international-process`）的 `evidence` 段内（含让路三要素） | 三要素齐；登记处 `docs/理论/冲突总账.md` 的同名新节（标题含`让路三要素`） |

> ⚠ **仓层面一处必须先说的实测**：`.openspec.yaml` 的 `skip_specs` **不改变** `review` 那条闸。
> `openspec archive --yes` 在任何情况下都不读 `review.md`。**唯一会拦的两条是 `spec_bridge.py` 判据①（归档目录必须有 `review.md`）与判据⑥（已签）**，
> 而它们**必须由人在归档前跑一次**才起拦阻作用；`archive` 动作本身**不带闸**。

### 2.3 第 3 样 · **最小原子化**（`WC-ATOM-001` §四，**落成可核的门禁项**）

按 `WC-ATOM-001` §四（A-1…A-6）**逐条落进原子表的一栏**。**栏数以 `templates/design.md` 的表头为准**
（原子／intent／四件同夹／deps == import／生成物／**机核读数**）：

| 约定 | 落在原子表的哪一栏 | 谁执行（**逐条人工执行并把读数贴进第 6 栏**） |
|---|---|---|
| **A-1 单意图原子性** | 第 2 栏 `intent`（一句话；出现「与／和／及」并列两事即拆） | 人工判；旁证 `WC-MODREG-001` 登记表的 `intent` 由 `python scripts/verify/module_graph.py` 核（**读数按上面那条命令现取，本表不复述**），但它**不看本表** |
| **A-2 一个原子一个文件夹（契约＋实现＋测试同夹）** | 第 3 栏「四件同夹」——三件都要写**真实路径或用例名** | 人工判；旁证同上（`module_graph.py` 判据②核的是 `src/` 登记面） |
| **A-3 契约字段齐** | 第 3 栏的"契约"格（规格条目／`WC-IC-001`） | 人工判 |
| **A-4 `deps == import` 且无环** | 第 4 栏 `deps == import` | `python scripts/verify/module_graph.py`（**读数现取，本处不复述**；自证 `--self-test`）＋人工贴读数 |
| **A-5 生成物不许手编** | 第 5 栏「生成物（重跑命令 / 无）」 | `spec_bridge.py` **判据⑪⑫⑬**（`generated/BRIDGE.md`／`generated/specmap.json`／`节对齐.md` 逐字节一致） |
| **A-6 UTF-8 无 BOM** | **第 6 栏「机核读数」**（编码这一个读数就写在这里） | `python scripts/verify/plain_text_audit.py --self-test` ⇒ 现取**含 BOM 反例判红 OK**；也可对单件跑同一条命令 |

**★ 两件必须说清的事（免得把这条读成"已落成自动门禁"）**：
1. **本档没有新增任何机器判据。** `module_graph.py` 读的是 **`WC-MODREG-001` 登记表**，
   **与 `design.md` 的原子表没有自动连接** ⇒ 原子表各栏是**人工执行 ＋ 贴读数**，
   不是一条会红的自动闸。会红的那些是**既有脚本**（`module_graph.py`／`plain_text_audit.py`／`spec_bridge.py`）会红。
2. **原子表不是宣言。** 第 6 栏要求把**命令与原始输出**贴上；写「无环」而没跑过那个命令
   ＝ 把没做到写成做到了（skill §七）。
   `scripts/verify/module_graph.py` **已在版本控制内**（`git ls-files` 可见）——skill §九「闸在版本控制之外等于没有闸」。

### 2.4 第 4 样 · **我们的经验**（逐条变约束）

**权威载体是源件，本件引用不复述**：`.agents/skills/worldcore-sdd/SKILL.md` §一–§十四、
`docs/openspec-MAINTENANCE.md` 16 条、`docs/理论/冲突总账.md` §7.8–§7.16。

按"**有没有会红的执行者**"分三档落进本档（skill §五：**没有反例的判据是装饰**）：

**(a) 有机器判据的**——已做成栏位或由既有守卫承担：

| 经验 | 落在哪一条 | 执行者 |
|---|---|---|
| 让路三要素（半写＝不写） | `templates/proposal.md` 必填栏 | `spec_bridge.py` 判据⑦ |
| 判据必须会红（一判据一反例＋正控） | `templates/tasks.md` 的**变异三栏**（断言在哪／变异怎么变红／正控） | `spec_bridge.py --self-test`；`module_graph.py --self-test` |
| 搜字样 ≠ 认结构（不取第一处字样） | `templates/spec.md` 的**证据行两形态硬规矩** | `spec_bridge.py` 判据② |
| 生成物不许手编；改了源重跑生成链 | `schema.yaml` 的 `specs.instruction` 末段 | `spec_bridge.py` 判据⑪⑫⑬；重跑 `python scripts/gen/gen_specmap.py` → `python scripts/gen/gen_bridge_md.py` |
| 绝不把「没做到」写成「做到了」 | `templates/design.md` 排除清单 ＋ L5 覆盖边界 | `spec_bridge.py` 判据②（形态）＋ 评审席（内容） |
| 正文不掺修订记录／改因块 | `templates/design.md` 头注 | `spec_bridge.py` 判据⑧⑨ |
| 一个事实只有一个权威载体；读数现取 | `templates/design.md` L5 表第 ② 格要求"命令＋输出＋时点＋对象" | `spec_bridge.py` 判据⑪⑫⑬⑮ |
| 归档前必须有已签评审；不代签 | `templates/review.md` 的签署栏与分离声明 | `spec_bridge.py` 判据①⑥ |

**(b) 只有人核、没有机器判据的**——做成**必填栏位**，逼它出现在评审材料里（**未建机器判据，如实标**）：

| 经验 | 落在哪一条 | 谁在哪个环节核 |
|---|---|---|
| 文档集封闭（不许新增／拆册，要加先经作者） | `templates/design.md` Open Questions ＋ 排除清单的出处栏 | 评审席按 skill §二 逐件核 |
| 不做「探针」这类额外件（检查并进既有门禁） | `templates/tasks.md` 头注（检查写进既有脚本，不另立件） | 评审席核「有没有为了检查另造第三个对象」 |
| 引用写「命令＋步骤名」不写行号；标「逐字」就一字不差 | `templates/review.md` 的引用纪律栏 | 评审席逐条核 |
| 中文串里用「」不用 ASCII 双引号 | 全模板沿用既有 `opsx-swe-gb` 的形态 | **本条无机器判据、至今未生效**——实测本档七件里与中日韩字符相邻的 ASCII `"` 仍有 200 余处，既有 `opsx-swe-gb` 七件同样如此（不是本档新引入的退步）；`scripts/verify/table_width_audit.py` 只管表宽，不管引号 |
| 件看方向、态只要留账；改一件要连带改别处并回读核 | `templates/proposal.md` Impact 栏 ＋ `design.md` 影响分析 | 评审席核 `git status --porcelain` 逐字交件 |
| 条目数取 `test result:` 的 totals 行、不按 token 数 | `templates/tasks.md` 验证与取证组 | 评审席核读数出处 |
| 先取 sha 再读件（`git show <sha>:<path>`） | `templates/review.md` 环境指纹栏 | 评审席 |

**(c) 本档不承担的**：**并发作业的边界**（一个工区独占一组文件）**不在本 schema 里**——
它是作业纪律，运行在**多人／多智能体同仓**这个层面，载体是 skill §十四 ＋ 交件回报，
写成 schema 栏位只会变成一句谁都不看的声明。**如实登记为"不落本档"。**

---

## 三、两个评审档位的时机（**硬约定，沿用**）

- **R5（框架变更评审）＝ 前置闸**：准入是 `proposal.md` ＋ `design.md`。**未获批准不得进入实施。**
- **R4（模块评审）＝ 后置闸**：准入是"代码已提交（含单元测试）、附提交号"。**代码没写完就没什么可审的。**

因此 `review.requires: [tasks]`、`apply.requires: [tasks]`。
**结论不许混**：R4 ＝ 通过／有条件通过／退回；R5 ＝ 批准／驳回。

---

## 四、实测过的门禁顺序（现取）

在**仓外一次性沙盒**（`D:\Code\_schema-atom-sandbox`）里跑完整条链：

```
schema validate opsx-swe-gb-atom      ⇒ ✓ valid            RC=0
new change zz-atom-selftest --schema  ⇒ RC=0
status                                ⇒ 0/5；specs(blocked by proposal)／tasks(blocked by specs, design)／review 待造
archive --yes（tasks 0/2 未勾）        ⇒ RC=0 且已合并 delta   ← archive 不拦
validate --archived                   ⇒ rc=1，2026-09-28-zz-unticked：
                                        2 incomplete tasks (0/2 completed)
validate <name> --strict（无 delta）    ⇒ rc=1  Change must have at least one delta
```

**这张表里最要紧的一行是第 4 行**：`archive --yes` 在 tasks `0/2` 未勾时**仍 rc=0 并把 delta 并进了主规格**
——所以**别拿 `archive` 当门禁**；拦人的是 `spec_bridge.py` 判据①⑥ 与 `validate --archived`。

---

## 五、与主本的关系（**受控面**）

主本 `D:\Code\10-openspec-swe-gb\schemas\` ↔ 本仓 `docs/schemas/`。
**方向规则沿用 `docs/schemas/README.md` §五：改主本，再同步过来。**
现行判据是「本 README ＋ `opsx-swe-gb/` 六件，**共七件逐文件 sha256 一致**」——**它只覆盖那七件**。

⚠ **本档的加入会让那份清单口径需要人裁**（`MAINTENANCE.md` 规则 5 的"七件"要么改成十二件、
要么改成"七件 ＋ 后加档"两条并列）。**这一格属"放哪／怎么算"的裁定**，
按 skill §十四「别人的文件里发现问题：只登记、不动手」**本档只登记、不改那份口径**。
**登记与选项见本件 §六**。

---

## 六、待人裁的三格（**登记，不代选**）

> 三格都是"**规则条文／口径该放哪**"的裁定，按 skill §十四 与 H-13（AI 不代裁）：**只登记、不动手**。
> 本档只把**选项与代价**写清——**半写＝不写**，故三要素（让哪一条／为什么／谁批的）留待裁定人补。

**第 1 格 · 「七件」清单随新档变化**（选项已在 `docs/schemas/README.md` §五 与 `MAINTENANCE.md` 规则 5）
- 选项甲：主本与本仓**都放**本档，把"七件"改成**十四件**（本档 root ＋ 六件，**两处各 7 件 ⇒ 2×7**）。
  **代价**：主本那一层**没有 `.git`**（现取：`D:\Code\10-openspec-swe-gb\` 下无 `.git`）⇒ 本档在主本那边**没有任何历史**。
- 选项乙：**只放本仓** `docs/schemas/`，主本不动。**代价**：打破"两处逐文件 sha256 一致"这条现行判据，§五 必须同步写明本档是仓内独有。
- 选项丙：**先只放本仓**，另立一件把主本纳入版本控制后再同步。**代价**：多出一件待办，期间本档仍是仓内独有。
- **本轮的取法（保守）**：本档**只落在本仓**（选项乙的形态），且**那七件未被改动**（现取 7/7 SAME）⇒ 现行判据**今天仍成立**。

**第 2 格 · 「受控件的仓外副本必须在版本控制内」要不要成条文**
- **事实（现取）**：主本 `schemas\` 是**仓外件**且**不在版本控制内**；而 skill §九 逐字「**闸在版本控制之外等于没有闸**」。
- 选项甲：写进 `.agents/skills/worldcore-sdd/SKILL.md`（工作方式层）。**代价**：改 skill 属改规则面，要走完整「改 → 评审 → 签」。
- 选项乙：写进 `docs/schemas/README.md` §五（工作流层）。**代价**：与 skill 形成两处表述，须指明哪一处是权威。
- 选项丙：**只登记事实**，条文落点等人定（本档取的形态）。**代价**：洞被点明但没有强制力。
- **§7.10 的先例**：同类动作（改仓外的件）已由评审席升为规矩——**先备份、再写、并把回退办法写进台账**。这一格可循同一条路升格。

**第 3 格 · 融合判据的**权威文本自己在版本控制之外**
- **事实（现取）**：本档引用的判据现口径原件是**.agents/skills/openspec-swe-gb-fusion/SKILL.md**，
  而它在 `1b58dc0` 的 git 里**不存在**（`git cat-file -e 1b58dc0:.agents/skills/openspec-swe-gb-fusion/SKILL.md` ⇒ rc=128）；
  本仓 `.agents/skills/` 下 git 只跟踪 `worldcore-sdd` ＋ **6 个** `openspec-*` 技能（`apply-change`／`archive-change`／`explore`／`propose`／`sync-specs`／`update-change`）。主本在**设备上** `C:\Users\DIY\.agents\skills\`。
  可用的**仓内可达**替代是 `ninedim/06-变更/fc-2026-001-openspec-into-cm/boundary.md`（`git ls-tree 1b58dc0` 可见）。
  ⇒ 与 skill §九 逐字「**闸在版本控制之外等于没有闸**」同形：**判据的文本在一个没有版本控制的面上**。
- 选项甲：**只引仓内可达件**（`boundary.md`）＋把本格登记为"引用面在版本控制外"（**本档取的形态**）。**代价**：`boundary.md` 与 skill 全文是否等价，**无机器判据**。
- 选项乙：把融合 skill **纳入本仓版本控制**（或反过来，让它的主本进一个受控面）。**代价**：改规则面／文档集口径，要走完整「改 → 评审 → 签」，且要作者定"哪一处是权威"。
- 选项丙：维持现状、**不登记**（**不取**——那正是"闸在版本控制之外"被继续放大的形态）。

---

## 七、本件自己不能证明的事（**别把它读成万能背书**）

0. **★ 本版（本档 7 件的字节）落在哪一笔：** 本档的现行文本最后改定于
   **提交 `72c0269`**（该笔的提交消息属另一条线，见 `docs/理论/冲突总账.md` §7.18 的事故台账），
   其后只有台账侧的两笔补记（`冲突总账` 的 §7.18／§7.19），**本档 7 件自 `72c0269` 起未再改**。
   ⚠ **下面第 1 条引的 `1b58dc0` 是"仓根门禁读数"的锚，不是本件字节的锚** ——
   按 `1b58dc0` 去读本档，读到的会是**整改前**的文本。要读本版，请按 **`72c0269`**（或它之后的 HEAD）取件。

1. **仓根两条门禁的读数取决于整棵仓的件，不只是本档。**
   **钉在提交上看**（`1b58dc0` 的 pristine 全树，现取）：`openspec validate --all --strict` ⇒ **`12 passed, 0 failed`**、
   `openspec validate --archived` ⇒ **`4 passed, 0 failed`**。
   ⚠ **但它会随别人的在飞件变**：我在改造期间的工作区里就见过 `12 passed, 1 failed`（另一条线的
   `agentd-in-rust-into-worldcore` 当时只有 `proposal.md`、缺 delta）与 `spec_bridge.py` 非全绿
   （同一件的证据锚点与 `generated/BRIDGE.md`／生成器不一致）。⇒ **别引用任何写死的门禁读数**；
   **以你手上那棵树的命令输出为准**（`python scripts/verify/spec_bridge.py`；`openspec validate --all --strict`）。
   本档自己的三条是稳的：`openspec schema validate opsx-swe-gb-atom` ✓、七件 `table_width_audit.py` 0 红、UTF-8 无 BOM／LF。
2. **模板里的栏位只保证"它出现在材料里"，不保证"填对了"。**
   机器能判形态（证据行有没有 token、结论栏签没签），**判不了"断言是否与声明相符"**——
   那归评审：流程侧有现成的**反面清单 12 条**，落点＝
   `refs/refs/_料/process-source/06-swe-gb/docs/02-评审与门禁/评审门禁与检查单.md` 的「反面清单（"格式对但内容是空的"12 种典型形态）」（**本件不复述其条目**）。
3. **本档没有增加任何新的机器判据**。它复用既有守卫（`spec_bridge.py`／`module_graph.py`／`plain_text_audit.py`）。
   ⇒ 「原子化」那一列的"会红"是**那些脚本会红**，不是**本 schema 会红**——schema 本身不含校验器逻辑。
