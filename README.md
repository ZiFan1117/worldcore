> ⚠️ **2026-09-28：原「国标化软件开发流程落地包」仓已并入本项目**
>
> **事情是什么**：原先**单独一份**的 `github.com/ZiFan1117/software-engineering-gb`
> （仓根 README 曾以 `# worldcore` 开头，内容＝worldcore 的 S0–S7 流程物）**已由作者指示废止**：
> 它的流程侧原文**搬进本仓受控面** → `.refs/_料/process-source/06-swe-gb/`（**在仓内留档、不入版本控制**）；
> 标准原文因版权/密级**留在仓外不进 git** → `D:\Code\05-swe-gb-standards\standards\`；
> 其余（`.git`／`tools`／`.venv-ocr` 等）**全量归档** → `D:\Code\heavy-archive\06-swe-gb-retired-2026-09-28\`。
> **旧仓的公开面（`software-engineering-gb` 的 `main`）已被覆盖为"三者融合版"**，
> 它**自己的 5 笔历史**（`1efefde`，2026-09-17）完整保留在该仓分支
> `legacy/international-process-2026-09-17`——**那是它唯一的回退点**。
>
> **融合的是什么**：① **OpenSpec 整个体系**（change 五件产物链 proposal → specs ∥ design → tasks → review）
> ＋ ② **国际／国标软件开发流程**（S0–S7 阶段与交付物、R0–R8 评审、三类基线、RTM 追溯、H-01…H-26 硬条款）
> ＋ ③ **最小原子化**（单意图／一个原子一个夹／`deps == import` 且无环／生成物不手编／UTF-8 无 BOM）。
> 落点为 `ninedim/records/openspec-流程件/schemas/opsx-swe-gb-atom/`，它是本仓**默认档**
> （由 `ninedim/records/openspec-流程件/openspec-config.yaml` 的 `schema:` 决定，守卫判据盯这一格）。
>
> **两个公开仓现在的关系**：`worldcore` 与 `software-engineering-gb` 内容**同源同笔**（都由本仓 `main` 推出）。
> **没给旧仓改名**是刻意的——改名会断掉既有 URL 与引用；改不改留给作者裁。
>
> **搬迁的完整记录**（完整性判据、改了什么与没改什么、**回退命令**）在
> `ninedim/07-待审/06-swe-gb废止与三者融合收敛.md`；
> 搬迁件自己的说明在 `.refs/_料/process-source/06-swe-gb/README.md`。
>
> **标准原文不在本仓**：`standards/`（17 份 PDF ＋ 16 份转好的 MD，共 230.73 MB）
> 因**版权与密级**原因**不进任何 git**。仓根 `.gitignore` 已补 `standards/*` 与 `*.pdf` 兜底规则。
> ⇒ **本件不复述任何红绿读数**：门禁现状一律现取（见 §三）。

---

# worldcore

> 这是一座「**书 → 规格 → 流程**」三层对齐的仓库：
> **书**讲"说法"这一层应当是什么（`ninedim/01-意图环/01-策划/`，现为**一本合订本**），
> **规格**写这台东西对外承诺什么行为（`ninedim/01-意图环/04-规格/`），
> **流程**记谁在什么时候按什么规矩做的、谁签的字（`ninedim/` 的七格：意图环／两枢纽／执行环／尾声／变更／待审 ＋ `records/`）。
> 三层冲突时的高下与"谁让"纪律见 **§二**。
>
> **仓库**：`github.com/ZiFan1117/worldcore`（private，**唯一活仓**）。
> 旧仓 `github.com/ZiFan1117/agent-native-os` **已归档**，不再维护。
>
> ⚠️ **本件里的数一律当场现取、并给命令**（件数、步数、判据条数一概不写死——写死的数必然过期）。
> 上一版（2026-09-27）是按当时的 `docs/` 布局写的；`docs/` 已于提交 `a7bb4fe` 删除、内容全并进 `ninedim/`，
> 本版按**现取布局**重写。**东西该住哪**的权威件是 `ninedim/01-意图环/03-设计/设计-落位契约.md`。

---

## 〇、代码在哪（**先读这一节**）

> 为什么单列一节：此前"**我要看代码**"这个最简单的问句，在这座仓里**没有一个地方一句话回答**。
> 本节就是那句话。**表里每条都给可复算的落点，不给"大概在那边"。**

| 我想找 | 去哪（一条就够） |
|---|---|
| **世界核心的实现代码** | `src/`——**9 个夹原子**（`ontology_definition`／`ledger`／`ontology_instance`／`gate`／`gui_projection`／`bus`／`carrier`／`common`／`agent`；名单的唯一出处＝`ninedim/config.json` 的 `atoms`）＋ crate 根的两个文件 `src/lib.rs`／`src/main.rs`（`M04` 总装与唯一写入口） |
| **某个能力的对外承诺** | `ninedim/01-意图环/04-规格/<能力>.spec.md`（**一个能力一份、扁平不嵌套**；现取件数：`Get-ChildItem ninedim/01-意图环/04-规格 -Filter *.spec.md`） |
| **某条承诺的证据（哪个测试在作证）** | 规格里的 `` - **证据**：`scripts/test/<file>.rs::<fn>` `` 行 → 直接落到 `scripts/test/`；**改名即失锚**，由 `scripts/verify/spec_bridge.py` 的"证据存在性"一族盯着 |
| **接口契约（模块之间怎么说话）** | `ninedim/01-意图环/03-设计/设计-WC-IC-001-v0.1.md`（**一册**，每模块一节） |
| **模块号与源码路径** | `ninedim/01-意图环/03-设计/设计-WC-MODREG-001-v0.1.md`（**模块号的唯一出处**） |
| **跑测试／跑门禁** | 在 **Linux／VM** 上 `bash check.sh`（出厂门禁，步数由脚本自己打印的 `STEPS` 现算）。⚠️ 宿主（Windows）**没有 cargo、没有 bash** ⇒ 这一步在宿主跑不了；宿主能跑的是 `scripts/verify/*.py` 里那几个纯 Python 判据 |
| **代码结构是否合规（原子化）** | `python scripts/verify/module_graph.py`——单意图／`deps == import` 且无环／四件同夹 |
| **流程文档（谁在什么时候按什么规矩做的）** | `ninedim/`：`01-意图环/`（策划→需求→设计→规格→计划→澄清）· `02-枢纽A-前置闸/` · `03-执行环/`（骨架／实现／测试／团队分工／验证证据）· `04-枢纽B-后置闸/` · `05-尾声/` · `06-变更/` · `07-待审/` · `records/`（模板／理论-来源／流程件／生成物／demo） |
| **书的原文（上位标准）** | `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md`（**唯一正件**；书 ＞ 规格 ＞ 流程） |
| **设计／评审／规程／研究料（退役料）** | **在仓内留档、不入库**（作者 2026-10-07：「我们所有内容都放在自己的 08 这个仓里」）→ `.refs/语义世界-架构/`；`.gitignore` 挡在版外。**精华**见 `ninedim/records/理论-来源/` |
| **上游供料（只读素材）** | **在仓内留档、不入库** → `.refs/`（36 个上游标准料目录＋`_standards-PROVENANCE.md`）、`.refs/omarchy/`、`.refs/omarchy-pkgs/`；`.gitignore` 挡在版外 |
| **过程料与过程脚本** | **在仓内留档、不入库** → `.refs/_料/`（退役流程料，如 `process-source/06-swe-gb/`）、`.refs/_脚本/` |

**三步走（从"一句话需求"到"一行代码"）**：
1. **承诺**：先按能力名去 `ninedim/01-意图环/04-规格/` 找到那条 `Requirement`；
2. **证据**：顺着它的 `- **证据**：…` 找到 `scripts/test/<file>.rs::<用例名>`——**这就是"它会红"的那条**；
3. **实现**：由用例里的调用点（或 `ninedim/01-意图环/03-设计/设计-WC-MODREG-001-v0.1.md` 的模块登记表）落到 `src/<原子>/` 里的文件。

> ★ **本节的射程**：它只回答"**在哪**"，不回答"**对不对**"。对不对由 `scripts/verify/*.py` 那些**会红的**守卫回答（见 §三）。

---

## 一、仓库一层有什么（实测）

> 命令：仓根 `Get-ChildItem -Force`（现取 **16 项**，不含 `.git`）；逐项的"装什么／不装什么"见
> `ninedim/01-意图环/03-设计/设计-落位契约.md` §一。

| 一层条目 | 一句话 |
|---|---|
| `src/` | **世界核心的实现**：**9 个夹原子**（一个原子一个夹：实现＋单测＋数据边车）＋ crate 根 `lib.rs`／`main.rs`；法律数据随原子走（`src/ontology_definition/ontology.json`、`src/gate/policy.json`） |
| `ninedim/` | **工程域（只装档案）**：七格（意图环／两枢纽／执行环／尾声／变更／待审）＋ `records/` ＋ `config.json` ＋ `_索引-工程域结构与命名.md`。现取：无 `.py`／`.sh`（硬约束 8） |
| `scripts/` | **可执行脚本，按用途九类**：`build`／`verify`（判据）／`gen`（生成器）／`test`（集成测试与驱动）／`bench`／`release`（装机面）／`maintain`／`collab`／`report` |
| `Cargo.toml`・`Cargo.lock` | **crate 在仓根**（不是子 crate）；`[[test]]` 逐条 `path=` 显式指路（集成测试在 `scripts/test/`） |
| `check.sh` | **仓根唯一入口**：出厂门禁（步数由脚本自己打印的 `STEPS` 现算）。⚠️ 宿主无 bash／cargo ⇒ 只能在 Linux／VM 侧跑 |
| `.github/` | 门禁自身：`workflows/gate.yml`（八作业，全部阻断式）＋ `PULL_REQUEST_TEMPLATE.md`（PR＝一次正式评审） |
| `.agents/` | AI 侧工作流技能：现取 7 个 `SKILL.md`（OpenSpec 6 ＋ `worldcore-sdd`）——**不属九维九项** |
| `.refs/` | **料**（上游源码快照／标准料库／退役料／过程料）：**在仓内留档、不入版本控制**；已在 `ninedim/config.json` 的 `na` 登记 |
| `README.md`・`AGENTS.md`・`CHANGELOG.md`・`NOTICE.md` | 前门／接手规约／版本记录／许可与来源 |
| `.gitignore`・`.gitattributes`・`.scope-declaration.json` | 版本控制口径（含"一次性脚本不入库"与夹内索引 `_索引.md` 的放行）／行尾与 BOM 纪律／改动范围声明（CI `scope` 作业的输入） |

> **本仓没有 `docs/`（有意）**：`docs/` 已删，内容全并进 `ninedim/`。人读说明＝**本件**（前门）＋ **书**（`ninedim/01-意图环/01-策划/`）＋ `ninedim/records/理论-来源/`。**不许再建 `docs/`**。

---

## 二、三层分工与「§〇 上位规则」

| 层 | 谁（现取） | 它只回答一个问题 | 冲突时 |
|---|---|---|---|
| **1 书（理念）** | `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md`（**唯一正件**） | 这一层应当是什么、今天做到几分、还剩什么没定 | **书赢** |
| **2 规格（对外承诺）** | `ninedim/01-意图环/04-规格/<能力>.spec.md`——能力数与各条 `Requirement` 条数**一律现取** | 这台东西对外承诺什么行为，每条由哪条会红的测试作证 | 与书冲突 ⇒ **改规格**（除非作者裁定改书） |
| **3 流程（过程证据）** | `ninedim/` 的七格 ＋ `records/`：策划／需求／设计／规格／计划／澄清记录／评审／骨架／实现／测试／团队分工／验证证据／处置表／变更盒／待审 | 谁在什么时候按什么规矩做的、谁签的字 | 与书或规格冲突 ⇒ **改流程文档** |

**§〇 上位规则**（源：`ninedim/records/openspec-流程件/schemas/README.md` §〇）：**书 > 规格 > 流程**。两条硬规矩：

1. **冲突要写明"谁让"**：任何一次"不按书来"的处置，必须在件里写下**让的是哪一条、为什么让、谁批的**——
   **不写＝违规**。这条有机器项：`scripts/verify/spec_bridge.py` 的**让路登记**判据。
2. **尺子是机抽的摘要，判定冲突必须回原书核逐字**：尺子＝`ninedim/01-意图环/01-策划/策划-尺子-理念条目.md`；
   台账＝`ninedim/01-意图环/01-策划/策划-冲突总账.md`（书 ↔ 规格 ↔ 流程三条边上的冲突逐条登记，带 `path:line`）。
   `ninedim/01-意图环/01-策划/` **只放派生工作件，不放第二本书**——它**不承担结论**。

---

## 三、怎么跑门禁

四条命令，都在**仓库根**跑。**本表不复述读数**——写死的读数必然过期；每条只给"**怎么判**"。

| # | 命令 | 管什么 | 怎么判 |
|---|---|---|---|
| 1 | `python scripts/verify/spec_shape.py` | **形态**：结构、每个 `Scenario` 恰好 4 个 `#`、delta 语法 | **rc=0**；件数与 `Requirement` 条数以它自己的输出为准 |
| 2 | `python scripts/verify/spec_bridge.py` | **规格层守卫**（判据的条数与逐条结论以 `--json` 的 `judgments` 为准） | **rc=0**；有红时命令逐条点名（点不出名字的红不算读数） |
| 3 | `python scripts/verify/spec_bridge.py --self-test` | 守卫**自证会红**：每条判据至少一个反例 | **rc=0**；反例不变红 ⇒ 判该守卫是装饰 |
| 4 | `bash check.sh` | **出厂门禁**（**步数不手写**：以该脚本自己打印的那份结论清单为准，它由 `STEPS` 现算） | **rc=0**；★结论区把**未校验**（⏭）与**登记型红**（⚠️）**单独报数**——**未校验 ≠ 通过** |

> **`openspec` CLI 的地位**：它**不再是任何判据的唯一执行体**——形态门禁由 `scripts/verify/spec_shape.py` 承担
> （CI 的 `openspec-validate` 作业现即跑它）。本机若装了 `openspec`，可作**辅助**的形态检查，但它**不构成判据**。
> **第 ④ 条只能在 Linux／VM 侧跑**（宿主无 `cargo`／`bash`）；在哪跑、怎么同步、读数怎么取（四要素），
> 见 `ninedim/03-执行环/03-测试/测试-WC-ST-001-v0.1.md` §二、§四。

### 3.1 判据一览

> **判据的条数与逐条结论，一律以 `python scripts/verify/spec_bridge.py --json` 的 `judgments` 为准**。
> 本件**不复述条数、也不列全表**——重述权威的表会烂。

`scripts/verify/` 下的守卫（现取件数：`Get-ChildItem scripts/verify -File`）各管一段，其中几类**内容侧**的事由规格层守卫在管：归档硬前置／证据存在性／默认档守卫／编号桥覆盖／覆盖在册／归档件的评审已签／让路登记／**生成物 ≡ 生成器当前输出**／**正文无修订记录**。
★ 任一不成立即非零退出；**红了不许绕过**（禁用 `continue-on-error`、禁注释掉步骤、禁放宽判据强度换绿）。

### 3.2 CI（`.github/workflows/gate.yml`）

- **触发**：`push` 与 `pull_request`（分支 `main`、`develop`）＋ `workflow_dispatch`。
- **八个作业，全部阻断式**：`smoke`／`unit-test`／`gate-self-test`／`traceability`／`scope`／
  `openspec-validate`／`spec-bridge`／`module-graph`。任一失败不予合入。
- **无任何密钥**：只用仓库内文件与公开 CLI。
- ⚠️ **红绿不在这里复述**（写死必过期）：各作业的当前结论以 `check.sh` 与各判据的命令输出为准。
  门禁自身也被门禁盯着——`scripts/verify/ci_self_check.py` 会扫**全仓**工作流，
  出现 `continue-on-error` 或必需作业缺失即判红。

### 3.3 机核（原子化）门禁

| 工具 | 是什么 | 今天的状态 |
|---|---|---|
| `scripts/verify/module_graph.py` | **原子化机核**（单意图／`deps == import` 且无环／四件同夹） | 红绿以 `python scripts/verify/module_graph.py` 的输出为准（**本件不复述**）。它同时接在 `check.sh` 与 CI 的 `module-graph` 作业里 |

---

## 四、旧引用怎么解析（退场件的**唯一**解析根）

**来源件已退场**：`1-理论与哲学/`、`2-依据/`、`3-备选路线/`、`4-计划/`、`00-总纲.md` 与
`ninedim/01-意图环/01-策划/` 的散件，已按作者指示（2026-09-27：「书只留一本合订本，其他文本可能不需要」）
从本仓移除，**其内容并入合订本** `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md`。

> ### 旧引用一律解析到**本仓 git 历史**（退场前提交 `bf2eae7` 之前的树）——这是它们唯一的解析根。

`bf2eae7` = `bf2eae72b0df52f5aec0ce276a0826feac35ef13`（2026-09-27，「fix(book): 书名副其实——书不搬进来，只指原址」）。

**怎么取旧件**：`git show bf2eae7:<旧路径>`（例：`git show bf2eae7:2-依据/15-世界核心的组成与职责.md`）；
反例：`git show bf2eae7:9-不存在的文件.md` ⇒ **rc=128**。
同一口径另见 `ninedim/records/openspec-流程件/schemas/README.md` 与 `ninedim/01-意图环/01-策划/策划-冲突总账.md`。

**仍留在文本里的旧引用怎么办**：它们**不改写**，按上面的解析根去取。
★ **"还有多少处"是带时刻的读数**（2026-09-27 那次现取＝33 个文本件／467 处），**本件不复述为权威**；
要现在的数就自己按 `1-理论与哲学`／`2-依据`／`3-备选路线`／`4-计划`／`00-总纲` 五个记号在仓内统计。
**Rust/Go 源码注释里的 `07/2-依据/14`、`07/4-计划/03` 一类引用同理**——`07` 指旧仓的树，也走 git 历史。

> **术语表的处置**：旧 README 有一张术语表（"载／存／传／管／显"、"声明即请求"、"语义事件是唯一真相"）。
> 这些说法在今天的合订本里**已查不到**，故本件**不再沿用**——沿用等于把已改的说法写回正文。要术语请读
> `ninedim/01-意图环/01-策划/策划-尺子-理念条目.md`（机抽的尺子），并回书核逐字。

---

## 五、先读哪一件

| 想干什么 | 读哪一件 |
|---|---|
| 想知道"东西该住哪" | `ninedim/01-意图环/03-设计/设计-落位契约.md`（四 结构 · 本仓的落位契约） |
| 想知道"这一层应当是什么" | 书：`ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md` |
| 想按条目核对、或判一处冲突 | 尺子 `ninedim/01-意图环/01-策划/策划-尺子-理念条目.md` ＋ 台账 `ninedim/01-意图环/01-策划/策划-冲突总账.md` |
| 想知道这台东西对外承诺什么 | `ninedim/01-意图环/04-规格/`（能力数现取）与 `ninedim/records/生成物/BRIDGE.md`（承诺 ↔ 流程侧需求号） |
| 想看正在改什么 | `ninedim/06-变更/`（在办盒与 `archive/`；盒内四件见 `ninedim/06-变更/_索引.md`） |
| 想看开发形态要求 | `ninedim/01-意图环/01-策划/策划-WC-ATOM-001-v0.1.md`（原子化编程：六条约定＋机核清单） |
| 想知道规矩怎么定的 | `ninedim/records/openspec-流程件/schemas/README.md`（融合档：谁管什么、产物链、评审档位）与 `ninedim/records/openspec-流程件/openspec-MAINTENANCE.md`（规格层维护清单） |
| 要提交改动 | `.github/PULL_REQUEST_TEMPLATE.md`（PR＝评审记录）＋ 跑 §三 的门禁 |
