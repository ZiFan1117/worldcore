> ⚠️ **2026-09-28：原「国标化软件开发流程落地包」仓已并入本项目**
>
> **事情是什么**：原先**单独一份**的 `github.com/ZiFan1117/software-engineering-gb`
> （仓根 README 曾以 `# worldcore` 开头，内容＝worldcore 的 S0–S7 流程物）**已由作者指示废止**：
> 它的流程侧原文**搬进本仓受控面** → `_料/process-source/06-swe-gb/`；
> 标准原文因版权/密级**留在仓外不进 git** → `D:\Code\05-swe-gb-standards\standards\`；
> 其余（`.git`／`tools`／`.venv-ocr` 等）**全量归档** → `D:\Code\heavy-archive\06-swe-gb-retired-2026-09-28\`。
> **旧仓的公开面（`software-engineering-gb` 的 `main`）已被覆盖为"三者融合版"**，
> 它**自己的 5 笔历史**（`1efefde`，2026-09-17）完整保留在该仓分支
> `legacy/international-process-2026-09-17`——**那是它唯一的回退点**。
>
> **融合的是什么**：① **OpenSpec 整个体系**（change 五件产物链 proposal → specs ∥ design → tasks → review）
> ＋ ② **国际／国标软件开发流程**（S0–S7 阶段与交付物、R0–R8 评审、三类基线、RTM 追溯、H-01…H-26 硬条款）
> ＋ ③ **最小原子化**（单意图／一个原子一个夹／`deps == import` 且无环／生成物不手编／UTF-8 无 BOM）。
> 落点为 `openspec/schemas/opsx-swe-gb-atom/`，它是本仓**默认档**
> （由 `openspec/config.yaml` 的 `schema:` 决定，守卫判据③ 盯这一格）。
>
> **两个公开仓现在的关系**：`worldcore` 与 `software-engineering-gb` 内容**同源同笔**（都由本仓 `main` 推出）。
> **没给旧仓改名**是刻意的——改名会断掉既有 URL 与引用；改不改留给作者裁。
>
> **搬迁的完整记录**（完整性判据、改了什么与没改什么、**回退命令**）在
> `openspec/work/06-swe-gb废止与三者融合收敛.md`；
> 搬迁件自己的说明在 `_料/process-source/06-swe-gb/README.md`。
>
> **标准原文不在本仓**：`standards/`（17 份 PDF ＋ 16 份转好的 MD，共 230.73 MB）
> 因**版权与密级**原因**不进任何 git**。仓根 `.gitignore` 已补 `standards/*` 与 `*.pdf` 兜底规则
> （2026-09-28 实测：应挡 7/7、应放行 5/5、已跟踪件零误伤）。
>
> **门禁现状（本说明写下时的读数，以命令输出为准）**：
> `python world-core/tools/spec_bridge.py` ⇒ 通过 16 / 失败 0；
> `python world-core/tools/spec_bridge.py --self-test` ⇒ 16/16 条判据各有 ≥1 个反例；
> `python world-core/tools/module_graph.py` ⇒ 通过 4 / 失败 0；
> `openspec validate --all --strict` ⇒ 13 passed, 0 failed；
> `openspec validate --archived` ⇒ 5 passed, 0 failed。
>
> ---

# worldcore

> 这是一座「**书 → 规格 → 流程**」三层对齐的仓库：
> **书**讲"说法"这一层应当是什么（`world-core/docs/理论/`，现为**一本合订本**），
> **规格**写这台东西对外承诺什么行为（`openspec/specs/`），
> **流程**记谁在什么时候按什么规矩做的、谁签的字（`world-core/docs/`）。
> 三层冲突时的高下与"谁让"纪律见 **§二**。
>
> **仓库**：`github.com/ZiFan1117/worldcore`（private，**唯一活仓**）。
> 旧仓 `github.com/ZiFan1117/agent-native-os` **已归档**，不再维护。
>
> **本件于 2026-09-27 按实测布局重写**：旧版按 `1-理论与哲学/`、`2-依据/`、`3-备选路线/`、
> `4-计划/`、`00-总纲.md` 那套布局描述，而这些来源件**已退场**（见 **§四**）。
> 本件里的每条路径与每个数字都是**当场实测**的，命令与读数随文给出；
> 实测时点：2026-09-27。⚠️ 仓里有多个工区**并行落件**——本次撰写期间 `main` 自 `50f30ac`
> 推进到 `8bf034d`（`git log -1` 可复核）；下面的数字都在落笔前复跑过，会随并行工区变化的量
> （规格条数、勾选数）按最后一次复跑取值。

---

## 〇、代码在哪（**先读这一节**；2026-10-06 增）

> 为什么单列一节：此前"**我要看代码**"这个最简单的问句，在这座仓里**没有一个地方一句话回答**——
> 代码埋在 `world-core/` 之下，而与它并列的还有 4 个**不是代码**的夹子（规格、设计料、上游快照×3）。
> 本节就是那句话。**表里每条都给可复算的落点，不给"大概在那边"。**

| 我想找 | 去哪（一条就够） |
|---|---|
| **世界核心的实现代码** | `world-core/src/`——总装 `lib.rs`／`main.rs`；账本 `ledger.rs`；门禁 `gate.rs`；本体执行者 `ontology.rs`；读模型 `readmodel.rs`；信封 `event.rs`；通道 `channel.rs`；投递 `delivery.rs`；检查点 `checkpoint.rs`；**Agent 运行时** `agent/`；**载体适配** `carrier/`；**投影** `project/` |
| **某个能力的对外承诺** | `openspec/specs/<能力>/spec.md`（**能力数现取**：`openspec list --specs`；`Requirement` 条数以 `openspec/generated/BRIDGE.md` 为准） |
| **某条承诺的证据（哪个测试在作证）** | `openspec/specs/**` 里的 `- **证据**：<path>::<fn>` 行 → 直接落到 `world-core/tests/<file>.rs`；**改名即失锚**，由 `tools/spec_bridge.py` 判据② 盯着 |
| **接口契约（模块之间怎么说话）** | `world-core/docs/S2-设计/WC-IC-001-v0.1.md`（**一册**，每模块一节；依赖列逐边与模块登记表一致） |
| **跑测试／跑门禁** | 在 VM 上 `bash world-core/check.sh`（21 步、阻断式）；仓根 `./check.sh` 是它的**转发入口**。⚠️ 宿主（Windows）没有 cargo/bash，跑不了 |
| **代码结构是否合规（原子化）** | `python world-core/tools/module_graph.py`——单意图／`deps == import` 且无环／四件同夹；它同时是 `check.sh` 的第 ⑨ 步 |
| **流程文档（谁在什么时候按什么规矩做的）** | `world-core/docs/S0-立项/` → `S1-需求/` → `S2-设计/` → `S3-骨架/` → `S4-实现/` → `S5-测试/` → `S6-验收/`（阶段号就是目录号） |
| **书的原文（上位标准）** | `world-core/docs/理论/语义世界-理论书-第一版-合订.md`（**唯一正件**；书 ＞ 规格 ＞ 流程） |
| **设计／评审／规程／研究料** | **在仓内留档、不入库**（作者 2026-10-07：「我们所有内容都放在自己的 08 这个仓里」）→ 仓根 `语义世界-架构/`（76 篇顶层文档 ＋ 研究料，共 93 MB／2 608 件）；`.gitignore` 挡在版外。它是**退役料**（只读；精华见 `world-core/docs/理论-来源/`） |
| **上游供料（只读素材）** | **在仓内留档、不入库** → 仓根 `refs/`（36 个上游标准料目录＋`_standards-PROVENANCE.md`）、`omarchy/`、`omarchy-pkgs/`；`.gitignore`（`:2-4`）挡在版外 |

**三步走（从"一句话需求"到"一行代码"）**：
1. **承诺**：先按能力名去 `openspec/specs/` 找到那条 `Requirement`；
2. **证据**：顺着它的 `- **证据**：…` 找到 `world-core/tests/<file>.rs::<用例名>`——**这就是"它会红"的那条**；
3. **实现**：由用例里的调用点（或 `world-core/docs/S2-设计/WC-MODREG-001-v0.1.md` 的模块登记表）落到 `world-core/src/<模块>.rs`。

> ★ **本节的射程**：它只回答"**在哪**"，不回答"**对不对**"。对不对由 `tools/` 下那些**会红的**守卫回答
> （见 §三：`check.sh` 21 步＝✅18／⏭2／⚠️1 那种读数）。

---

## 一、仓库一层有什么（实测）

> 命令：仓库根 `Get-ChildItem -Force`；版本状态取自 `git ls-files -- <路径>` 的计数。

| 一层条目 | 一句话 | 入库件数（实测） |
|---|---|---|
| **`world-core/`** | **世界核心**：Rust 实现（`src/`＝9 个模块夹＋`lib.rs`／`main.rs`；`tests/`）＋**法律**（`src/ontology_definition/ontology.json`、`src/gate/policy.json`；随原子走）＋**流程文档**（`docs/`）＋**门禁工具**（`tools/`）＋**部署面**（`deploy/`：`units/`＋`install.sh`＋`README.md`）＋出厂门禁 `check.sh` | — |
| **`openspec/`** | **规格层**：`specs/`（对外承诺）＋`changes/`（在办与归档）＋`schemas/`（融合档）＋`gen/`（生成器）＋`generated/`（生成物：`BRIDGE.md`／`specmap.json`／`节对齐.md`）＋`work/`（工作区）＋`README.md`（目录分工）／`MAINTENANCE.md`／`config.yaml`。**书与对照表不在这**：在 `world-core/docs/理论/`（正件＋`落点/`＋`尺子-理念条目.md`＋`冲突总账.md`） | — |
| **`.github/`** | **门禁自身**：`workflows/world-core-gate.yml`（CI 八作业）＋`PULL_REQUEST_TEMPLATE.md`（PR＝一次正式评审的记录） | 2 |
| `语义世界-架构/` | **退役料，在仓内留档、不入库**（作者 2026-10-07：「我们所有内容都放在自己的 08 这个仓里」）：设计／评审／规程／研究料（76 篇顶层文档＋研究料，共 93 MB／2 608 件）；`.gitignore` 挡在版外。★ 它是 `world-core/tools/kind_guard.py` 的扫描面：**现取 184 篇／红 0／`STATUS=PASS`**（`check.sh` ⑦b）。**精华**见 `world-core/docs/理论-来源/` | **0**（不入库；在工作树） |
| ~~`agentd/`~~ | **已退场（2026-10-06）**：Go 参考实现（28 件）按作者裁定移除工作树 —— `WC-FC-2026-005` §3.1「不再作独立组件」；能力面已由 **Rust 版**接替（`world-core/src/agent/` 4 件 ＋ `world-core/tests/agent_*.rs` 4 件，读数见该 change）。**旧件仍在 git 历史**：`git show deafbae:agentd/cmd/agentd/main.go` | **0**（已移出工作树） |
| `omarchy/` | 上游源码快照（73 MB）：**在仓内留档、不入库**（`.gitignore:2-4`） | **0**（不入库；在工作树） |
| `omarchy-pkgs/` | 同上，包构建那一半（9 MB）：**在仓内留档、不入库** | **0**（不入库；在工作树） |
| `refs/` | 上游**标准料库**——36 个子目录（`bfo-2020`／`iao`／`in-toto`／`rekor`／`opa`／`c2sp`／`w3c-trace-context`／`skos`／`prov-o`…）＋`_standards-PROVENANCE.md`，**1.18 GB／63 648 件**（本仓磁盘占用的大头）：**在仓内留档、不入库**。★ 运行时输入：`world-core/tools/fetch_bfo_terms.py` 的缺省 `--owl` 先看仓内 | **0**（不入库；在工作树） |
| `.agents/` | **AI 侧工作流技能**：`worldcore-sdd`／`openspec-swe-gb-fusion` 两篇 `SKILL.md` | 8 |
| `README.md` | 本件（前门，含 **§〇「代码在哪」**） | — |
| `check.sh` | **仓根唯一入口**：**转发**到 `world-core/check.sh`（出厂门禁 **22 步**）。⚠️ 它**自己什么也不跑** —— 只把这一次调用交出去；入口断链时 rc=2，**不报绿** | — |
| `变更记录.md` | 2026-09-25 那次目录重排的**旧编号对照表**；它描述的正是**已退场**的布局（实测 41 处旧路径引用），保留作史料 | — |
| `.gitattributes` | 行尾与 BOM 纪律：`.sh/.rs/.json/.yml/.yaml/.py/.csv/.md` 等一律 `eol=lf`（`:8`、`:16-23`、`:33`）；`*.ps1` **必须带 UTF-8 BOM**（`:24-28`） | — |
| `.gitignore` | **挡在版外但留在工作树**：`omarchy/`、`omarchy-pkgs/`、`refs/`（`:2-4`）、`语义世界-架构/`（`:10`）、`_料/`（`:59-60`＝上游过程料）、`_脚本/`（过程脚本）——按作者 2026-10-07 口径「**东西都在 08 里**」，由本件决定入不入库 | — |

> **`world-core/` 再深一层**（本件用到的三处）：`docs/`＝流程文档、`tools/`＝门禁工具与守卫、
> `src/`＋`tests/`＝Rust 实现与测试；另有 `cap.d/`（能力声明样本）、`deploy/`、`templates/`（七类模板）、
> `NOTICE.md`（许可状态）、`.scope-declaration.json`（改动范围声明）。

---

## 二、三层分工与「§〇 上位规则」

| 层 | 谁（实测） | 它只回答一个问题 | 冲突时 |
|---|---|---|---|
| **1 书（理念）** | `world-core/docs/理论/`——实测**只有 1 件**：合订本 `语义世界-理论书-第一版-合订.md`（433 843 字节／2 572 行／LF／无 BOM；卷首自述"一本把'说法'这一层讲清楚的书"，装配日期 2026-09-27） | 这一层应当是什么、今天做到几分、还剩什么没定 | **书赢** |
| **2 规格（对外承诺）** | `openspec/specs/`——**能力数与各条 `Requirement` 的条数一律现取**（`openspec list --specs`）；★ 本件**不复述这些计数**（复述必烂：此前写死过「6 个能力／33 条」，而现取是 **9 个／49 条**） | 这台东西对外承诺什么行为，每条由哪条会红的测试作证 | 与书冲突 ⇒ **改规格**（除非作者裁定改书） |
| **3 流程（过程证据）** | `world-core/docs/`——实测 `S0-立项` 5／`S1-需求` 5／`S2-设计` 16／`S3-骨架` 2／`S4-实现` 5／`S5-测试` 1／**`S7-交付` 0**、`评审` 9、`阶段外-待启用` 10、`demo` 1、`系统全景图.md`；**无 `S6`** | 谁在什么时候按什么规矩做的、谁签的字 | 与书或规格冲突 ⇒ **改流程文档** |

**§〇 上位规则**（源：`openspec/schemas/README.md` §〇）：**书 > 规格 > 流程**。两条硬规矩：

1. **冲突要写明"谁让"**：任何一次"不按书来"的处置，必须在件里写下**让的是哪一条、为什么让、谁批的**——
   **不写＝违规**。这条 2026-09-27 起已有机器项：`world-core/tools/spec_bridge.py` 的**判据⑦「让路登记」**。
2. **尺子是机抽的摘要，判定冲突必须回原书核逐字**：尺子＝`world-core/docs/理论/尺子-理念条目.md`；
   台账＝`world-core/docs/理论/冲突总账.md`（书 ↔ 规格 ↔ 流程三条边上的冲突逐条登记，带 `path:line`）。
   `world-core/docs/理论/` **只放派生工作件，不放书**——**它不是书，不承担结论**。

---

## 三、怎么跑门禁

四条命令，都在**仓库根**跑。**本表不复述读数**——写死的读数必然过期（本项目为此被独立评审席判过三次）；
每条只给"**怎么判**"，读数一律现取。

| # | 命令 | 管什么 | 怎么判 |
|---|---|---|---|
| 1 | `openspec validate --all --strict` | **形态**：结构、每个 `Scenario` 恰好 4 个 `#`、delta 语法 | **rc=0**；`passed`/`failed` 以该命令自己的 `Totals:` 行为准 |
| 2 | `python world-core/tools/spec_bridge.py` | **规格层守卫**（判据的条数与逐条结论以 `--json` 的 `judgments` 为准） | **rc=0**；有红时命令逐条点名（点不出名字的红不算读数） |
| 3 | `python world-core/tools/spec_bridge.py --self-test` | 守卫**自证会红**：每条判据至少一个反例 | **rc=0**；反例不变红 ⇒ 判该守卫是装饰 |
| 4 | `bash world-core/check.sh` | **出厂门禁**（**步数不手写**：以该脚本自己打印的那份结论清单为准，它由 `STEPS` 现算） | **rc=0**；★它首行的「全通过」**不含**两类：**未校验**（⏭）与**登记型红**（⚠️）——两者在结论区**单独报数**，**未校验 ≠ 通过** |

> **第 4 条的第 ⑧ 步就是第 2 条**：`world-core/check.sh` 的「⑧ 规格层守卫」那一步调 `spec_bridge.py`
> （引用按**步骤名**写，**不写行号**——行号会烂）。
> 也就是说这条守卫**同时**在"一条命令跑通"和 CI 里执行，不是只写在文档里。
> ★ **本机（Windows）没有 Rust 工具链，也没有 `bash`** ⇒ 第 4 条只能在 Linux／VM 侧跑；
> 在哪跑、怎么同步、读数怎么取（四要素），见 `world-core/docs/S5-测试/WC-ST-001-v0.1.md` §二、§四。

### 3.1 判据一览（`world-core/tools/spec_bridge.py`）

> **判据的条数与逐条结论，一律以 `python world-core/tools/spec_bridge.py --json` 的 `judgments` 为准**。
> 本件**不复述条数、也不列全表**——重述权威的表会烂（判据会增，而这份表不会自己跟着变）。
> 下表只**举例**说明它补位的是哪几类**内容侧**的事，**不是全表**；全表请跑上面那条命令。

`openspec validate` 只判**形态**；下表这些是它的**内容侧补位**，任一不成立即非零退出：

| # | 判据 | 一句话 |
|---|---|---|
| ① | 归档硬前置 | 每个 `openspec/changes/archive/*/` 必须有非空 `review.md` |
| ② | 证据存在性 | 规格里 `- **证据**：<path>::<fn>` 的函数／脚本必须真实存在（改名即失锚） |
| ③ | 默认档守卫 | `openspec/config.yaml` 的 `schema:` 必须是 `opsx-swe-gb-atom`（被改回默认档即失败） |
| ④ | 编号桥覆盖 | `openspec/generated/BRIDGE.md` 必须覆盖规格树下**每一条** `Requirement`（有号或显式标「无号」） |
| ⑤ | 覆盖在册 | 至少一个 `cover-*` change **未归档**且 `tasks.md` 仍有未勾项（未实现的能力要有落点） |
| ⑥ | 归档件的评审已签 | 结论 ∈ 批准／通过／有条件通过，且批准人非空、非占位 |
| ⑦ | 让路登记 | 声明了「谁让」的件必须写全：让哪一条／为什么让／谁批的 |

> ★ **上表是举例，不是全表**：全表以 `--json` 的 `judgments` 为准（本仓另有若干条**同族**的判据，
> 例如"两份文档的清单表 ≡ 实际"「值必须落在已声明的格里」那几类）。

> ⚠️ **判据⑥ 的红与绿都如实报**（它管"归档件的评审已签"）：它转红时，
> **不要**注释掉它、加 `continue-on-error`、或放宽判据强度——那正是本项目记过的病；
> 处置台账在 `world-core/docs/理论/冲突总账.md` §五 裁-1（作者指示：**评审通过后**由执行者签署；未过不签）。

### 3.2 CI（`.github/workflows/world-core-gate.yml`）

- **触发**：`push` 与 `pull_request`（分支 `main`、`develop`）＋ `workflow_dispatch`。
- **八个作业，全部阻断式**：`smoke`／`unit-test`／`gate-self-test`／`traceability`／`scope`／
  `openspec-validate`／`spec-bridge`／`module-graph`。任一失败不予合入。
- **无任何密钥**：只用仓库内文件与公开 CLI。OpenSpec CLI 的版本**钉死**在 `@fission-ai/openspec@1.13.2`
  （与本机实测一致；浮动版本会让"同一次提交、两个结论"）。
- ⚠️ **红绿不在这里复述**（写死必过期）：`spec-bridge` 与 `module-graph` 的当前结论以各自作业的命令输出为准。
  门禁自身也被门禁盯着——`world-core/tools/ci_self_check.py` 会扫**全仓**工作流，
  出现 `continue-on-error` 或必需作业缺失即判红。

### 3.3 机核（原子化）门禁

| 工具 | 是什么 | 今天的状态 |
|---|---|---|
| `world-core/tools/module_graph.py` | **原子化机核**（`WC-ATOM-001` §二 A-1 单意图／A-4 `deps == import` 且无环／A-2 四件同夹） | **已入库**（`git ls-files world-core/tools/module_graph.py` 可核）；红绿以 `python world-core/tools/module_graph.py` 的输出为准（**本件不复述**）。它同时接在 `check.sh` 第 ⑨ 步与 CI 的 `module-graph` 作业里 |

---

## 四、旧引用怎么解析（退场件的**唯一**解析根）

**来源件已退场**：`1-理论与哲学/`、`2-依据/`、`3-备选路线/`、`4-计划/`、`00-总纲.md` 与
`world-core/docs/理论/` 的散件，已按作者指示（2026-09-27：「书只留一本合订本，其他文本可能不需要」）
从本仓移除，**其内容并入合订本** `world-core/docs/理论/语义世界-理论书-第一版-合订.md`。

> ### 旧引用一律解析到**本仓 git 历史**（退场前提交 `bf2eae7` 之前的树）——这是它们唯一的解析根。

实测（命令 → 读数）：

| 事实 | 命令 | 读数 |
|---|---|---|
| 这些路径今天**都不存在** | `Test-Path 1-理论与哲学` 等 5 条 | 全 `False` |
| 退场前它们在（共 **31 篇**） | `git ls-tree -r --name-only bf2eae7 -- <路径>` | `1-理论与哲学` 7 ／ `2-依据` 16 ／ `3-备选路线` 3 ／ `4-计划` 4（＝30 篇）＋ `00-总纲.md` **44 169 字节**（＝31 篇） |
| 理论散件也在（**79 件**） | 同上，`world-core/docs/理论` | 79——合订本入仓后，该目录今天只剩 1 件 |
| **取旧件** | `git show bf2eae7:2-依据/15-世界核心的组成与职责.md` | **rc=0**（反例 `git show bf2eae7:9-不存在的文件.md` → **rc=128**） |

`bf2eae7` = `bf2eae72b0df52f5aec0ce276a0826feac35ef13`（2026-09-27，「fix(book): 书名副其实——书不搬进来，只指原址」）。
同一口径另见 `openspec/schemas/README.md:38-40` 与 `world-core/docs/理论/冲突总账.md:172`。

**仍留在文本里的旧引用怎么办**：它们不改写，按上面的解析根去取。实测（`rg`，排除 `refs/`、`omarchy*/`、
`.git/` 与本件）：今天有 **33 个文本件、共 467 处**（`rg -o` 计数）仍在引用退场路径，最多的是
`world-core/docs/理论/…合订.md`（94 处）、`变更记录.md`（41 处，它是那次重排的对照表）、
`world-core/docs/S0-立项/WC-FSR-001-v0.1.md`（32 处）。
**Rust/Go 源码注释里的 `07/2-依据/14`、`07/4-计划/03` 一类引用同理**——`07` 指旧仓的树，也走 git 历史
（`agentd/` 的 Go module 路径仍写 `github.com/ZiFan1117/agent-native-os/agentd`，实测 26 处）。

> **术语表的处置**：旧 README 有一张术语表（"载／存／传／管／显"、"声明即请求"、"语义事件是唯一真相"）。
> 这些说法在今天的合订本里**已查不到**（实测逐一 0 命中，如 `声明即请求` 0、`载、存` 0、`五件事` 0），
> 故本件**不再沿用**——沿用等于把已改的说法写回正文。要术语请读
> `world-core/docs/理论/尺子-理念条目.md`（机抽的尺子），并回书核逐字。

---

## 五、先读哪一件

| 想干什么 | 读哪一件 |
|---|---|
| 想知道"这一层应当是什么" | 书：`world-core/docs/理论/语义世界-理论书-第一版-合订.md` |
| 想按条目核对、或判一处冲突 | 尺子 `world-core/docs/理论/尺子-理念条目.md` ＋ 台账 `world-core/docs/理论/冲突总账.md` |
| 想知道这台东西对外承诺什么 | `openspec/specs/`（能力数现取：`openspec list --specs`）与 `openspec/generated/BRIDGE.md`（承诺 ↔ 流程侧需求号） |
| 想看正在改什么 | `openspec/changes/`：在办 3 件（`cover-unimplemented-capabilities` 未勾 26／`fc-2026-001-openspec-into-cm` 未勾 16·已勾 18／`fc-2026-002-spec-revisions` 未勾 42）＋归档 1 件（`2026-09-27-baseline-verified-doctrine`） |
| 想看开发形态要求 | `world-core/docs/S0-立项/WC-ATOM-001-v0.1.md`（原子化编程：六条约定＋机核清单） |
| 想知道规矩怎么定的 | `openspec/schemas/README.md`（融合档：谁管什么、产物链、评审档位）与 `openspec/MAINTENANCE.md`（规格层维护清单） |
| 要提交改动 | `.github/PULL_REQUEST_TEMPLATE.md`（PR＝评审记录）＋ 跑 §三 的门禁 |
