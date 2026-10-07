# Design

## Context

`fc-2026-001` 把 OpenSpec 引入了本仓，并把 6 份主规格立为基线。
紧接着对那 6 份做的逐条审计（`ninedim/06-变更/fc-2026-001-openspec-into-cm/audit.md`）
在**机械层全绿**的前提下查出 **46 条语义差错**（严重 15 / 重要 12 / 一般 14 / 提示 5）。

塑造做法的现状与约束（逐条带出处，不重述 proposal 的动机）：

1. **本仓的规格树只有描述性标题，没有 REQ 号。** 6 份主规格的全部
   `### Requirement:` 标题（`ninedim/01-意图环/04-规格/*/spec.md`）**无一以 REQ 号开头**；
   而 `ninedim/records/openspec-流程件/schemas/opsx-swe-gb/schema.yaml:44-47` 要求「每条 `### Requirement:` 的标题必须**以 REQ 号开头**」，
   并给了取不到号时的处置：「**取不到号时登记为「无号·待增补」，不许自造、不许拿相近号硬凑。**」
   ⇒ 本 change **不得**靠改标题来"补齐编号"。
2. **`openspec validate --strict` 对 delta 有两条硬约束**（本轮实测得出，见 §Decisions）：
   ① `## MODIFIED` 的标题必须在 `ninedim/01-意图环/04-规格/` 下**逐字存在**，
   否则报 `MODIFIED failed for header "..." - not found`；
   ② `## MODIFIED` **不许漏掉**现规格里的任何一个 Scenario：
   `MODIFIED "..." omits scenario(s) the current spec still has: "..."`。
   ⇒ **不能靠改名或合并来"重写"一条 Requirement**。
3. **主机没有 Rust 工具链**；构建与验收只在 VM `world` 内做
   （`ssh world` rc=0，`Linux world 7.2.6-arch2-1`，`cargo 1.98.1 (797e8a9bc 2026-08-05)`）。
4. **`` 是外部交付物，本 change 一行不改**：它是 `D:\Code\07-agent-native-os` @ `61c95b0` 的逐字节副本。
5. **出厂门禁只有一条单入口**：`check.sh.new`；它的第 ③ 步**只选跑** `t1_ t2_ t7_`
   （`check.sh.new:98`），第 ③b 步跑整个 `--test contract`（`:103`），
   **从不跑 `--test cli`**。
6. **`ninedim/01-意图环/04-规格/**` 不在任何机械门禁的受控清单里**：
   `scripts/verify/doc_integrity.py` 全文检索 `openspec` **零命中**。

## Goals / Non-Goals

**Goals:**

1. 把 46 条里的**规格文本问题**逐条改到与**实测**和**项目文档**一致，一条不丢（对账表见 `tasks.md`）。
2. 5 条"把已知缺陷写成已成立"的（P0）**改成边界条文**——把边界写成 Requirement/Scenario，
   照 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md:101-106`「整本重写按设计检不出（边界固定）」的既有写法。
3. 每条 delta 自报**问题类别**（"造出来的东西守不守自己的规矩" vs "这一层能力有没有"）
   与**证据是哪条测试的哪个断言**；证据今天不存在的，写"需补断言（列进 tasks）"，**不编造**。
4. 交付一件**可被人逐条复核**的 change：`proposal` / `specs` / `design` / `tasks` 四件，
   `review.md` **不写**（它是人签的闸）。

**Non-Goals:**

1. **不改代码、不改测试、不改既有规格基线文件。** `` 零改动；`ninedim/01-意图环/04-规格/**` 零改动
   （delta 在归档时才合并）。
2. **不新增能力。** 6 个能力目录一个不多；`## ADDED Requirements` 只装**既有能力的边界条文**
   （见 §Decisions 的 D-3）。
3. **不补需求编号。** 见 §排除清单第 1 条：编号桥两头都在、中间没接，属另一个变更。
4. **不修缺陷。** K-3、白名单摩擦落点、同源核对恒绿这三条**都是实现侧的事**；
   本 change 只把它们的**边界**写进规格。修它们各自另立 change。
5. **不补缺失断言。** 缺失断言只**登记**在 `tasks.md`（实施期工作），本 change 不写测试。

## 影响分析

> R5 准入要件。

| 项 | 内容 |
|---|---|
| **受影响模块** | **无代码模块受影响。** 受影响的是规格层：`ninedim/01-意图环/04-规格/channel-identity`、`envelope-validation`、`gate-enforcement`、`ledger-integrity`、`projections`、`read-model`（6/6）。间接被引用（**不改**）：`src/{channel,gate,ledger,guard,lib,main,readmodel,checkpoint,ontology}.rs`、`src/project/mod.rs`、`src/carrier/mod.rs`、`scripts/test/{contract,acceptance,cli}.rs`、`check.sh.new`、`scripts/{system_acceptance.sh,s1_sys_probe2.sh,visual_layout_audit.py,doc_integrity.py}`、`policy.json`、`docs/**`（作为**证据出处**被引用，不改） |
| **受影响需求** | 规格侧：6 个能力的全部 Requirement（23 条）中，本 change 重写 19 条、新增 8 条**边界条文**。流程侧（按 SRS `需求-WC-SRS-001-v0.1.md` 的登记）：`REQ-F-002` 信封字段、`REQ-F-005` 崩溃尾迹、`REQ-F-008` 三家族、`REQ-F-014` 回滚、`REQ-F-015` 门禁不可绕过、`REQ-F-016` 门禁裁决、`REQ-F-017` 不可逆摩擦、`REQ-F-018` 语言投影、`REQ-F-019` 视觉投影、`REQ-F-020` 两投影同源、`REQ-F-021` 检查点、`REQ-F-022` 账本可重放、`REQ-F-023` 投递（边界）、`REQ-F-024` 投影不新增事实（P0）、`REQ-F-025` 主体身份可核、`REQ-N-003` 启动即校验本体、`REQ-N-008` 检查点性能目标。**另有 5 条承诺在流程侧无号**（见 §排除清单第 1 条） |
| **需重跑的测试** | **本 change 本身不需要跑任何测试**（零代码改动）。归档后如需复验基线自洽，需在 VM 内跑：① `cd /root/world/world-core && bash check.sh`（出厂单入口，rc=0 为前提）；② `cargo test --locked`（全量 68 项，含 `t5`/`t9`/`t10`/`t13`——这四个**不在** `check.sh` 的任何一步里）；③ `cargo test --locked --test cli`（含 `cli05`，`check.sh` 从不跑它）；④ `bash tools/system_acceptance.sh`（跨 uid 三条断言，缺 `setpriv` 或非 root 时整段不执行）。**注意**：④ 的"未校验"分支**不得**被当成通过 |
| **回归范围** | 按**流程侧权威四档** R-A／R-B／R-C／R-D 给出（`附件三-评审与门禁.md:265`；**流程侧没有 R-E**）：<br>**R-A · 规格形态**：`openspec validate fc-2026-002-spec-revisions --strict` ⇒ `is valid`；`openspec status --change fc-2026-002-spec-revisions` ⇒ proposal/specs/design/tasks 四件 `done`、`review` 未写。<br>**R-B · delta 的完整性**：6 个 delta 里每条 `## MODIFIED` 都**贴全了**该 Requirement 的原有 Scenario（`validate --strict` 的 `omits scenario(s)` 检查即此项，已实际拦下 4 处，见 §Decisions D-2）。<br>**R-C · 证据锚点存在性**：delta 里引用的每个 `path::fn` 与每个"文件:行号"都在本仓可定位；`git status --short` 只多出本 change 一个目录。<br>**R-D · 不越界**：`git status --short` 的改动清单与本 change 目录之外**无交集**；`` 零命中改动。<br>**R-D 之下的一条验收项**（**原名 `R-E`——流程侧没有此档，故此处不再以 `R-E` 称呼**）**· 出厂判据强度不变**：`bash check.sh` 的 rc 与 `docs/S0-立项/策划-WC-SCMP-001-v0.1.md` §8.4 登记的项数不变（本 change 不改 `check.sh`、不改任何测试）。<br>**★ 留痕（假勾）**：本行原先**在同一个单元格内**并列写着「**流程侧没有 R-E**」与「**R-E** · 出厂判据强度不变」——**同一行自相矛盾**；而 `BOOK/冲突总账.md:209` 早已把 `M6`（指的就是本行）记作「**已关**」⇒ **台账说已关、实际没关，这是一次假勾**。**发现者／时间**：**独立评审席·甲**，`2026-09-27`（第 14–16 轮按冻结对象 `90cfa3d` 复核；逐字证据见 `BOOK/冲突总账.md:303` 第 7 条）。**处置**：档名 `R-E` **去掉**，「出厂判据强度不变」这一**内容原样保留**，改挂在 `R-D` 之下。 |
| **工作量估算** | 起草（本 change 四件产物）≈ **1.5 人日**（已投入）。其中：46 条逐条回源核验 ≈ 0.8 人日（含 6 份规格、~15 个源码/测试文件、9 份受控文档的定位与逐字抄录）；四件产物撰写 ≈ 0.5 人日；`validate`/`status` 收口与对账 ≈ 0.2 人日。**后续（不在本 change 内）**：`tasks.md` 里登记的补断言 ≈ **3–4 人日**（含 VM 内跑测取证）；三条缺陷（K-3、摩擦落点、同源恒绿）的修复 ≈ **5–8 人日**，各自另立 change。 |
| **需通知的使用方** | ① **评审席**（R5 前置闸：按 `review.md` 逐条复核 46 条）；② 把 `ninedim/01-意图环/04-规格/**` 当"这台东西今天承诺什么"读的人（`boundary.md` §一）；③ 流程侧 SRS/RTM 维护者——本 change 使若干「规格说 A、SRS 说 B」收敛到 **SRS 与实测那一侧**（C1：SRS:266/268/383 与 RTM:29/31 都写「拒绝且不落笔」；L7：SRS:257 写「回滚通过追加一条普通 `change` 完成」）；④ `wc-con01-001` 的持有人（C3/C4 的跨 uid 边界与它同源）；⑤ 依赖"检查点未接入 CLI"这一旧陈述的三份受控文档的维护者（R1：`实现-WC-UT-001-v0.1.md:54`、`需求-WC-SRS-001-v0.1.md:921`、`WC-RTM-001.csv:22`）。**破坏性变更**：对**规格文本**是破坏性的（6 个能力的措辞会变），对代码与接口**不是**。

**R5 触发条件**：**FC-3（假设被推翻）** 为主，**FC-1（契约不足）** 为辅（逐条见 `proposal.md` 的 §档位判定）。

**现象证据**：4 条 FC-3 与 2 条 FC-1 的可核事实已逐条列在 `proposal.md` 的
「现象证据」表中（含文件路径、行号、逐字引文）；本件不重复。

## 方案对比

### 方案甲 · 一次性修全部 46 条（含 5 条 P0 边界条文）

- **做什么**：把 46 条按四类（写宽／写窄／证据错位／与文档冲突）逐条落进
  6 个 delta；P0 的 5 条改写成**边界条文**；证据今天不存在的写"需补断言（列进 tasks）"。
- **代价**：单件 delta 体积大（6 份共约 60 KB）；评审席要逐条核 46 条；
  因为 `validate --strict` 要求"贴全 Scenario"，每处修改都要连原有 Scenario 一起搬。
- **结论**：**选**。理由：46 条**不改的后果相同**（`schema.yaml:8-9`：后果不同才是两个变更），
  且其中 5 条 P0 与其余 41 条**同源**——它们都是"基线把未定/错的/缺的说成已定"这同一个根因的实例。
  拆开做会让"规格被读成什么都已定"这个窗口多开几轮。

### 方案乙 · 不改（或只加一份勘误表）

- **做什么**：本 change 只交一份"46 条勘误表"，`ninedim/01-意图环/04-规格/**` 一字不动；
  读者靠勘误表自行折算。
- **代价**：**零**改动成本、零风险。
- **结论**：**不选**。三条理由逐条有据：
  ① 规格是**机读权威载体**（`boundary.md` §一「**这就是需求规格的机读子集**」），
     勘误表不进 `specs/` 就**不产生任何机读效果**：`openspec show` / 任何下游读者都看不到；
  ② 5 条 P0 里最重的一条（K-3）是**安全相关**的：
     `策划-WC-SCMP-001-v0.1.md:2542` 逐字「**触发场景不是攻击，是升级**：任何历史账本在升级后的第一次提交都会命中」
     ⇒ 把"升级即锁死"留在规格里当"v1 兼容"，勘误表改变不了读者的部署决策；
  ③ 本项目**已经**有勘误表这一形态（`audit.md` 本身就是），而它恰恰**没有被任何机械门禁覆盖**
     （`scripts/verify/doc_integrity.py` 里 `openspec` 零命中）⇒ 靠表不靠规格，等于把同一件事再赌一次。

### 方案丙 · 最小改：只修 5 条 P0

- **做什么**：只把 `ledger-integrity` 的 v1 兼容、`gate-enforcement` 的摩擦落点、
  `projections` 的同源恒绿这三处（5 条 P0）改成边界条文，其余 41 条留待以后。
- **代价**：改动面小、评审快。
- **结论**：**不选**。① 5 条 P0 里 `gate-enforcement` 的那两条**必须**与 G3（闸读不到风险等级、
  载体可逆与世界可逆无互校）连着写才自洽——只改摩擦落点而不写"闸读不到风险等级"，
  规格仍会把书稿判红的三条依据漏掉两条；② 41 条里含 9 条**严重**，
  其中 E1（错误码那条的四类路径里没有一类是账本）会让一条要求**归档后证据为空**；
  ③ 甲案的成本主要花在**回源核验**（已投入），改 5 条与改 46 条在核验上是同一遍工。

## Decisions

**D-1 · R5 前置，本 change 不进入实施。**
本 change 触及 `ninedim/01-意图环/04-规格/**`（`schema.yaml:23-24` 判据），判为 R5。
按 `schema.yaml:141-144`：R5 是**前置闸**，`review.md` 的 R5 节在 apply **之前**填、签字；
**未获 R5 批准不得进入实施**。本 change 的 `review.md` **一个字不写**（由人填）。

**D-2 · `## MODIFIED` 必须逐字沿用原标题、且贴全原 Scenario。**
这是本轮**实测**出来的硬约束，不是选择：首版 delta 里我改了 4 处 Scenario 名
（如 `策略的每一类畸形形状都被拒` → `策略的五类畸形形状被拒`），
`validate --strict` 逐条报 `omits scenario(s) the current spec still has: "..."`；
另改了 3 处 Requirement 标题，报 `MODIFIED failed for header "..." - not found`。
⇒ 处置：**改名一律不做**；措辞修正写在该 Scenario 的 `- **THEN**` 与证据行注记里，
不动 `#### Scenario:` 那一行。代价是"场景名与修正后的内容略有张力"，
收益是**不丢细节**（这正是 `schema.yaml:59` 那条要求的用意）。

**D-3 · 新增的边界条文用 `## ADDED Requirements`，并逐条说明为什么不是 MODIFIED。**
`validate --strict` 只接受 `## MODIFIED` 的标题在基线里逐字存在；
而 P0 要求"把边界写成 Requirement/Scenario"，边界**必须是一条新的 Requirement 实体**。
⇒ 用 `## ADDED`，但**不新增能力**：每条 ADDED 都在既有能力目录之下，
并在文件里逐条写明"本节不新增能力，只声明该既有能力的边界"。
**排除的做法**：把边界塞进既有 Requirement 的正文（可行，但会让"哪一条是已定的边界"无法被人一眼核出，
且会与 D-2 的"不动标题"叠加成更难读的文本）。

**D-4 · 证据今天不存在的，一律写"需补断言（列进 tasks）"，不编造测试名。**
`audit.md` 的 46 条里有 13 条属于"行为是真的、但没有任何断言为它变红"
（如 G4 的保留前缀 `refused` 指纹、L6 的 `MixedChain` 启动路径）。
对这些条目，delta 写规格条文 + 明确标注"需补断言"，并把断言登记进 `tasks.md`。
**排除的做法**：把"文档在手"当成"测试在手"（那正是这 46 条的成因）。

**D-5 · 5 条 P0 的改法是"改到与实测一致 + 把边界写成条文"，不是"删掉那句话"。**
逐条：
- `ledger-integrity`：删掉 `spec.md:111` 的"（v1 兼容）"括注，新增边界 Requirement，
  写"无链账本上做一次合法 `append` 后仍可打开"为**修复判据**，
  并写"v1 兼容只到只读为止"为**当下边界**。
- `gate-enforcement`：把"对不可逆能力追加摩擦"改成"白名单内放行、白名单外加摩擦"，
  并把出厂配置下"唯一能做不可逆动作的主体恰是唯一完全免检的主体"写成条文。
- `gate-enforcement`（G3）：新增边界 Requirement，写"闸读不到风险等级""两处无互校"。
- `projections`：把"首行逐字一致"改成"头部四项一致"，新增边界 Requirement，
  写"自己渲染两份再自己比、三个不等分支结构上不可达"。
**排除的做法**：把判红的三处直接写成"红/未实现"——那会让规格变成缺陷台账，
而规格该写的是"**这台东西今天承诺什么**"（`boundary.md` §一），
边界与承诺必须同框出现。

> **★ 事后更正（2026-09-27，上面第 3 条已被推翻；留痕不删）**
> 上面那条 `gate-enforcement`（G3）当时写的"**闸读不到风险等级**""**两处无互校**"，**现在与实现相反**：
> `src/gate.rs:73` 已有 `pub risk: Option<CarrierRisk>,`、`:259 cross_check_reversibility` 两处互校、不一致即拒启
> （评审席·乙 在 VM 上按原 Scenario 的 WHEN 造场景实测：**rc=2、`ext.world.Gate.ReversibilityMismatch`、账本未建**）。
> ⇒ 那条 Requirement 的**正文、Scenario 与标题已整条翻正**：标题由「闸读不到风险等级，且载体可逆与世界可逆无互校」
> 改为「**闸读得到风险等级，且载体可逆与世界可逆互校（不一致即拒启）**」，**主规格与 delta 逐字一致**
> （本次**有意打破"delta 逐字节未动"的既有不变式**——`## MODIFIED` 的标题必须与主规格逐字匹配，否则校验即红）。
> 第 1 条（`ledger-integrity`）与第 3 条的邻居们**不受影响**，仍按当时写法成立。
>
> **为什么留痕而不改写上面那几行**：它们**基于当时的实测**（当时确实读不到、确实无互校），
> 是这张 change 的历史；改它等于把"当时的判断"擦掉。
> **改因写在这里（`design.md`），不写进规格正文**——正文只写"现在是什么"（守卫判据⑨ 会拦）。


**D-6 · 本 change 不补需求编号。** 见 §排除清单第 1 条。

**D-7 · 每条 delta 自报两个问题**（问题类别 + 证据锚点）。
按用户口径与 `boundary.md` §三：**"造出来的东西守不守自己的规矩"** 与
**"这一层能力有没有"** 是两类，不能互相冒充——"把书里判红的东西写成绿"正是第一类的典型。
本 change 的 46 条里，**绝大多数是两类都不是的第三类**：
"**规格说的是不是它自己证据里的那件事**"。
我按用户给的两个选项无法完整表达这一层，故作如下取舍（见 §用户判据的改动）：
每条用「措辞写宽／写窄／证据错位／与文档冲突」四类**之一**标出，
并在需要时说明它**不是**"能力有没有"的问题。

## 从规格正文移出的改因块（正文净化的落点）

> 出处：`.agents/skills/worldcore-sdd/SKILL.md` §三「文档里写什么、不写什么」——**规格正文只写"世界必须怎样"**；
> 改因块是**过程证据**，归本 change 的 `design.md`／`audit.md`。
> 落地：`ninedim/01-意图环/04-规格/**` 六份主规格与 `specs/**` 六份 delta 里的改因块**逐块删除**
> （实测：每棵树 **33 块**、块头行 **76 行**，两棵树的内容逐字节相同）；
> 形态门禁的 `Requirement text is very long` 由 **28 条降到 1 条**，剩下那 1 条是本 change 要求逐条写全的
> 11 条排版契约本身（`projections` 的 `视觉投影的排版是可审计契约`，527 字符），**不是改因块**，
> 故保留在第 2 类阈值之上而不拆条（拆条会新增 Requirement 标题，判据④ 的编号桥随之失配）。
> **删前逐块回源核验**：同一事实已在 `audit.md`（逐条的 C／E／G／L／P／R 编号）／本件 §Decisions D-3／
> `tasks.md` 第 2–5 组／`proposal.md` 现象证据表里的，按**删复述**处置；**别处没有的，整块搬到这里**。

### 一、别处没有对应记载、整块搬来的三块（逐字）

这三块是**唯三**自报「`audit.md` 未单列此条」的块——除规格正文外，本 change 没有任何产物记过它们。
逐字搬来如下（原文同时位于 `ninedim/01-意图环/04-规格/<能力>/spec.md` 与 delta 同名文件的同一位置）：

**① 能力 `envelope-validation` · Requirement `事件身份在进程内唯一` 之下**

```text
> **改的是哪一类问题**：① 措辞写宽后的**范围收窄**——原文已有「同一进程内」限定，
> 本条**只补"跨重启不保证"这半边**，不改结论强度。`audit.md` 未单列此条。
>
> **证据是哪条测试的哪个断言**：`scripts/test/contract.rs:245-248` 逐字
> 「`new_id()` = 纳秒 + 进程内计数器；计数器每次启动从 0 开始，/ 故"跨重启唯一"依赖纳秒不重复——本测试覆盖**同进程内**的唯一性。」
> 断言本体在 `:251-256`：2000 次 `new_event` 收进 `BTreeSet` 后断言无重复。
```

① 自报"只补'跨重启不保证'这半边、不改结论强度"，故 `tasks.md` 未为它立补断言任务；
它带来的边界条文已写进该 Requirement 的正文（`系统 SHALL NOT 声称跨进程或跨重启的 id 唯一性由本机制保证`）。

**② 能力 `gate-enforcement` · Requirement "`act` 的效果不能靠 `change` 偷渡" 之下**

```text
> **改的是哪一类问题**：③ 证据错位（证据行未指名出厂步骤，无法核对是否被跑）。
>
> `audit.md` 未单列此条；本条改动**只为与上一条的引用口径统一**。
> `check.sh.new:103` 逐字 `cargo test --locked --test contract`，`c01` 在其中。
>
> **证据是哪条测试的哪个断言**：`scripts/test/contract.rs::c01_change_is_gated_and_cannot_smuggle_an_act`
> 位于 `--test contract` 全套之内，由 `check.sh.new` 第 ③b 步（`:103`）执行。
```

**③ 能力 `gate-enforcement` · Requirement `运行中的世界不重读策略` 之下**

```text
> **改的是哪一类问题**：③ 证据错位（证据行未给路径，且该测试不在所标步骤内）。
> 本条**内容不改**，只修引用口径。
>
> `audit.md` 未单列此条；`policy.json:8` 逐字
> `    "策略在启动时一次读入内存，运行中不重读：磁盘上改了要重启才生效（消除『运行中改规则』的窗口）",`
> 与本条是同一件事。
>
> **证据是哪条测试的哪个断言**：`scripts/test/acceptance.rs::t13_running_world_does_not_reread_policy`
> ——同样**不在** `check.sh.new` 的步骤 ③ 内（`:98` 只选 `t1_ t2_ t7_`）。
```

② 的 `check.sh:103` 与本件 §Context 第 5 条同源；③ 的"出厂脚本同名两处、步骤号要对上"与
§影响分析「需重跑的测试」③ 同源。三块的结论都已在净化后的正文里成条，搬来的只是**它们的出处与行号**。

### 二、只在该块里出现过的引用（逐条移来，供复核）

下列 `path:line` **只出现在被删的改因块里**：`audit.md`／本件／`proposal.md`／`tasks.md`
与净化后的规格正文都不再含它们。其中多数在 `audit.md` 或本件里以**更宽的行号区间或更粗的指代**记载，
下面保留的是块里的**原始粒度**，以免核验时对不上：

- `scripts/test/contract.rs:245-248`、`:251-256`（见 §一 ①）
- `policy.json:8`（见 §一 ③）
- `scripts/test/contract.rs::c11_irreversible_is_owner_only_and_the_refusal_does_not_lie`
  ——`gate-enforcement` 不可逆那条的**断言侧第二条**（`audit.md` G1／G2 未列该函数名）
- `scripts/test/acceptance.rs:298-299`／`:316-317`／`:321-322`
  ——`t8` 三类拒绝面的**断言行号**（`audit.md` R2 只说"三类"，未给行号）
- `src/main.rs:389-395` —— CLI 把读模型拒绝转成 `rc=2` 的逐字
- `scripts/test/contract.rs:224-227` —— `c04` 只测"缺文件"的那一段（`audit.md` E3② 未给行号）
- `scripts/test/contract.rs:770-776` —— `c15` 的码断言本体（`audit.md` E1 给的是七条码来源的行号）
- `scripts/test/acceptance.rs:158-159` —— `t5` 的断言本体（`audit.md` E2／E5 未给行号）
- `src/ledger.rs:280-289` —— `set_len(keep)` 落盘处（`audit.md` L3 给的是 `276-289`）
- `src/ledger.rs:518-519` —— `is_chained()` 访问器（排除清单第 2 条给的是 `:506`）
- `src/project/mod.rs:126-131` —— 三个不等分支的第一支（`audit.md` P1 给的是 `126-145`）
- `scripts/test/system_acceptance.sh:314`／`:342-344` —— ㉔–㉖ 的 `setpriv` 守卫行与 `else` 分支
  （§影响分析只写"缺 `setpriv` 或非 root 时整段不执行"这一事实，未给行号）
- `scripts/verify/visual_layout_audit.py:17-29` —— 契约表的行号（`audit.md` P6 给的是 `15-32`）
- `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md:2312` —— 框架 5.2 行（`audit.md` P2 引的是第四章 `:192`）
- `policy.json:38` —— `allow` 表（`audit.md` G2 给的是 `policy.json:32`）

**其余 30 块按"删复述"处置**（每块的同一事实在本 change 的产物里都有落点）：

- **改因与问题类别**：`audit.md` 的对应条目（C1–C6／E1–E8／G1–G6／L1–L9／P1–P7／R1–R10，
  每条自带"原文怎么写／实测是什么"与逐字引文）；类别口径见 §Decisions D-7 与
  `proposal.md` §What Changes 的四类表。
- **为什么用 `## ADDED`**：§Decisions D-3（"不新增能力，只声明该既有能力的边界"这一句的权威载体）。
- **"需补断言（列进 tasks）"**：`tasks.md` 第 2–5 组逐条在册。
- **证据与实现的行号**：`audit.md` 各条目；与块里的引文同源，行号粒度的差异已逐条列在 §二。

## Risks / Trade-offs

- **[风险] 改规格措辞而代码不动，会让"规格说 A、实现做 B"** →
  [缓解] 本 change 的每一条都把**实现侧的行号与逐字**写在 delta 里，
  并逐条声明本 change **只改文本、不改行为**；真正的行为修复（K-3、摩擦落点、同源恒绿）
  在 `proposal.md` 的 Impact 与 `tasks.md` 里逐条列为**另立 change**。
- **[风险] 5 条 P0 的规格改完后，实现侧的缺陷仍在（规格与实现短暂不一致，但方向相反了）** →
  [缓解] P0 的改法是"把边界写成条文"而不是"宣布已修"：
  `ledger-integrity` 的 ADDED 里**同时**写了"修复判据"与"当下边界（只读兼容）"两个 Scenario，
  读者不会把边界读成已修。
- **[风险] `validate --strict` 只保证形态，不保证语义** →
  [缓解] 这正是 46 条的成因。本 change 的兜底是：① 每条 delta 自报证据锚点；
  ② `tasks.md` 第 6 组登记"由人逐条复核"；③ `review.md` 留给人签字（`boundary.md` §三）。
- **[风险] 一次改 6 个能力、19 条 Requirement，评审面过大** →
  [缓解] 6 个 delta 各自独立成文件，能力之间无交叉引用；
  评审席可一个能力一个能力签。且 46 条的对账表（`tasks.md`）逐条给出"落在哪件产物"。
- **[风险] `tasks.md` 里的"补断言"被误当成本 change 的实施内容** →
  [缓解] `tasks.md` 的分组按**依赖**编号，第 1 组是"规格文本落地"（本 change 的全部内容），
  第 2–5 组明确标注"**属实施期，需另经 R5 批准后执行**"。
- **[风险] 主机的行号与 VM 内的行号漂移** →
  [缓解] 本轮核验发现一个真实陷阱：PowerShell 的 `(Get-Content).Count` 会**漏数空行**
  （`scripts/test/contract.rs` 实为 **1197** 行，而 `.Count` 报 1075）。
  ⇒ 该文件的所有引用都以 `read` 工具读出的行号为准；本 change 引用的 `contract.rs:1152` 等
  已用 `read` 逐条复核过。**本 change 的任一行号引用不得以 `.Count` 为依据。**

## 排除清单

> **明确不写进 specs 的东西，逐条给出处。** 未定项、待人裁项、已知残余风险都放这里。

| # | 不写入 | 为什么 | 出处 |
|---|---|---|---|
| 1 | **需求编号（把 `### Requirement:` 标题改成 `REQ-F-0xx …`）** | ① 6 份主规格的 Requirement **全部无号**（实测：`ninedim/01-意图环/04-规格/*/spec.md` 的 23 条标题无一以 `REQ` 开头）；② 流程侧确有号（`需求-WC-SRS-001-v0.1.md:69-112` 的 `REQ-F-001…REQ-N-008`），但**编号桥两头都在、中间没接**——`audit.md` 单列这条缺口：「有承诺、无流程侧需求号 **5** 条」；③ 补号是**映射工作**（要给 23 条逐条选定 REQ 号并处理"一号多义"，如 `REQ-F-016` 在 `WC-FSR-001` 与 `WC-SRS-001` 同号不同义，见 `需求-WC-SRS-001-v0.1.md:259`），**属另一个变更**；④ 本 change 不补号**不影响 validate**（`is valid` 已实测） | `ninedim/records/openspec-流程件/schemas/opsx-swe-gb/schema.yaml:44-47`（「取不到号时登记为「无号·待增补」，**不许自造、不许拿相近号硬凑**」）；`audit.md:138/142`；`需求-WC-SRS-001-v0.1.md:259` |
| 2 | **K-3 的修复**（`append` 尊重 `self.chained`） | 本 change **不改 ``**。K-3 是代码缺陷，修它要改 `src/ledger.rs` 的 `append`；本 change 只把它的**边界**写成条文（`ledger-integrity` 的 ADDED「无链账本的升级路径边界」） | `策划-WC-SCMP-001-v0.1.md:2537`（K-3 定位与最小补丁 `:2544`）；`src/ledger.rs:506`（`chained` 只读不用） |
| 3 | **门禁摩擦落点的修复**（把摩擦挂到动作的不可逆等级上） | 同上：那是 `src/gate.rs` 的改法，属 R5 框架变更，另立 change | `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md:717`；`src/gate.rs:287-293`；`ninedim/01-意图环/01-策划/WC-THEORY-DEFECT-001-v0.2.md:44`（`D-02` 严重） 〔该件已按作者指示退场；解析根＝`git show bf2eae7:<原路径>`〕 |
| 4 | **`project check` 的"跨来源比对"实现（含 `IF-003a` 的编号落点）** | ① 实现它要改代码；② 它的编号载体**不属本 change 作者所有**，RTM 明写待人裁定 | `WC-RTM-001.csv:21` 逐字「该用例尚未实现；IF-003a 的编号载体（WC-IC-001）不属本次执行员所有 ⇒ ⚠ 待人工裁定落点。」 |
| 5 | **`REQ-N-008` 的目标值（走检查点续算 ≤ 全量重算的 1/2、样本 ≥ 20 取 P95）** | ① SRS 记「未实现」，`WC-TP-001-v0.1.md:80` 记「六项目标值仍【候选】⇒ **不得声称达标**；数值由人确认后方可判达标」；② 未定值不得写进规格。本 change 只声明它**在范围外**（`read-model` 的 ADDED） | `需求-WC-SRS-001-v0.1.md:112`；`WC-TP-001-v0.1.md:80` |
| 6 | **`IF-003a` / `TC-042` 等编号的落点裁定** | 属编号归属的人裁，`audit.md` 与 `WC-RTM-001.csv:21` 均标「待人工裁定」 | `WC-RTM-001.csv:21`；`audit.md:138` |
| 7 | **`spec_bridge.py` 的实体（脚本本身）** | 本 change 只把"要补这条检查"登记进 `tasks.md`；脚本归 `scripts/**`，不属本 change 的写入范围 | `boundary.md` §四.2（规格层守卫的落点）；`audit.md:130/125`（R9 / E8） |
| 8 | **`channel.rs` 的 `expect.uid` 在 `serve_once` 路径上不被读取这一内部事实** | 它是**实现内部的不可达字段**，没有对外可核的观测面，写进规格会成为"注意事项"而不是要求。判据：无法写成会变红的 Scenario ⇒ 不进规格。其可核的外壳（"受理层不读对端凭证"）已写进 `channel-identity` 的 ADDED | `src/channel.rs:256-257`（自述）；实测量：`channel.rs` 全文 `uid` 只出现在 `:9/10/20/23/42/62/105/106/108/112/169/177/195/256`，`serve_once` 内无读取 |
| 9 | **`REQ-F-023` 的投递/应答配对（`to` 字段）** | SRS 记「部分实现（通道身份 + 一行应答已实现并实测 c14；to 的投递与请求应答配对字段未实现）」⇒ **未实现的能力不进规格**（`schema.yaml:65-66` 逐字「只装"已成立且可复现"的行为。未定的、待裁的、已知残余风险，一律写进 `design.md` 的**排除清单**」） | `需求-WC-SRS-001-v0.1.md:91` |
| 10 | **`REQ-F-026`/`REQ-F-027`/`REQ-F-029`/`REQ-F-030`/`REQ-N-005`/`REQ-N-006`/`REQ-N-007` 等未实现需求** | 同上：SRS 逐条记"未实现"或"部分实现"，未实现的能力不写进规格 | `需求-WC-SRS-001-v0.1.md:94-99/109-111` |
| 11 | **`t8` 用 `State::fold` 直喂向量致 `SeqGap` 在生产路径不可达（R10）** | `audit.md` 自身判它「**不是缺陷，是防线冗余**」；且它是测试设计事实而非规格级行为。本 change 只在 `read-model` 的 MODIFIED 里**加一句注记**，不为它立 Requirement | `audit.md:131-132`（R10）；`src/ledger.rs:304` |
| 12 | **本机的 `cargo` / `check.sh` 实跑结果** | 主机**无 Rust 工具链**；任何 cargo 结论都只能在 VM `world` 内取得。本 change 的**全部**证据都是"读源码/读受控文档"级；带"实测"字样的引文一律**标注其出处为 `audit.md` 在 VM 内的实跑留档**，本 change 不声称自己跑过 | 本件 §Context 第 3 条；`proposal.md` §环境指纹 |

## Migration Plan

**落地步骤**（本 change 只动文本，不动运行中的系统）：

1. **R5 前置**：由人在 `review.md` 的 R5 节逐项核 `proposal.md`（含 FC 触发条件与现象证据）
   与 `design.md`（含 ≥2 方案含不改案、影响分析），签字"批准 / 驳回"。
   **未批准不得进入实施**（`schema.yaml:141-144`）。
2. **实施**：按 `tasks.md` 第 1 组逐条落地 delta 文本（本 change 已起草完成，
   第 1 组的任务即"照本 delta 合并入基线"的确认项）。
3. **补断言**：`tasks.md` 第 2–5 组，在 VM 内补缺失断言并取证。
   **这四组需另经 R5 批准**（它们触及 `scripts/test/**`，属框架变更）。
4. **归档**：`openspec archive` 会把 6 个 delta 合并入 `ninedim/01-意图环/04-规格/**`。
   归档门禁要求 `tasks.md` 全勾（`schema.yaml:121-122`）⇒ 本 change 的 `tasks.md`
   **不含常设维护项**。
5. **R4 后置**：归档前补 `review.md` 的 R4 节并取签字（执行者不得为唯一批准者）。

**回滚策略**：

- **本 change 的文本是纯增量、且不影响任何既有文件**：`ninedim/01-意图环/04-规格/**` 在**归档之前**一字未改。
  ⇒ 回滚＝**删掉 `ninedim/06-变更/fc-2026-002-spec-revisions/` 整个目录**，
  `git status --short` 即回到干净状态；无需任何数据迁移、无需停服。
- **归档之后**若要回滚：delta 已合并入 `ninedim/01-意图环/04-规格/**`，
  回滚＝`git revert` 归档那一次提交（`git revert <归档提交>`），
  或按本项目既有的 change 机制**再立一个 change** 把措辞改回。
  **不得**手工编辑 `ninedim/01-意图环/04-规格/**`——那会绕过 R5 与 `validate`。
- **本 change 不产生任何"运行中的系统"**：无服务、无迁移脚本、无数据变更。

## Open Questions

> 可以延后定、且**不影响**规格 / 做法 / 任务拆分的问题。

1. **`IF-003a`（跨进程/跨时刻投影比对规程）的编号落点归哪份文档。**
   RTM `:21` 明写「⚠ 待人工裁定落点」。本 change 把该项列为排除清单第 6 条，
   `tasks.md` 不依赖它 ⇒ 不影响本 change 的任务拆分。
2. **23 条 Requirement 的 REQ 号映射表由谁出、何时出。**
   见排除清单第 1 条。它决定的是**下一轮**能不能补号，不影响本 change 的任何一条 delta。
3. **`spec_bridge.py` 归哪一个 change。**
   本 change 只登记"要补这条检查"（`tasks.md` 第 4 组）。
   该脚本落 `scripts/**` ⇒ 实施它的 change 判定与排期可延后定。
4. **`channel.json` 是否补出厂文件。**
   `src/main.rs:586-587` 逐字「⚠️ 本仓**不提供出厂 `channel.json`**（`WC-SCMP-001` §8.4 `G-28` 记"是否补出厂文件**待人裁定**"）」。
   本 change 未触及该项（`channel-identity` 的 ADDED 只用它说明"未登记即拒"的边界）。
