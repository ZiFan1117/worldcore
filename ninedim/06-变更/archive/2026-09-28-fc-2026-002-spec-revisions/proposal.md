# Proposal

FC: WC-FC-2026-002

> **变更号出处**：本号取自上一 change 立项时对框架变更编号段的登记（`ninedim/06-变更/fc-2026-001-openspec-into-cm/boundary.md` §2.1「S7 运维与回归」行把 change 定为运维期变更的载体）；`fc-2026-00N` 段由人在 `fc-2026-001` 命名时开启，本 change 沿序号取 **002**。**agent 不自造号**——若评审席另有裁定，改号即可，`ninedim/records/openspec-流程件/schemas/opsx-swe-gb/schema.yaml:14` 逐字「**号由人给，agent 不自己编号**」。

## Why

`fc-2026-001` 对现有 6 份主规格做了一次逐条审计，结论是一句话：**机械层是诚实的，语义层不是。**
40 条证据行**逐条存在**（40/40 命中）、**逐条实跑通过**，但按「断言是否真是 Scenario 说的那件事」核对后共 **46 条**问题：
**严重 15 / 重要 12 / 一般 14 / 提示 5**（`ninedim/06-变更/fc-2026-001-openspec-into-cm/audit.md:9`）。

**不改的后果（分三条，每条后果不同 ⇒ 它们是同一件事的三面，不是三件事）：**

1. **规格把已知缺陷写成已成立，读者会据此做部署决策。** 最重的一条是 `ledger-integrity`
   的「v1 无链账本仍可打开（v1 兼容）」：项目自己把这条路径登记为**【高】级自杀缺陷**——
   `ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md:2537` 逐字
   「### K-3【高】在 v1（无链）账本上做一次正常 `append` 会把世界锁死 —— 升级路径自杀」，
   同件 `:2542` 逐字「**触发场景不是攻击，是升级**：任何历史账本在升级后的第一次提交都会命中」。
   而 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md:111` 把它写成「无链的旧账本仍能打开（v1 兼容）」——
   **读者读到的是"平滑升级"，实际是"升级即锁死"。** 同类还有 `gate-enforcement` 与 `projections` 两处。
2. **规格与证据不是一件事，归档后失效无人能察觉。** 例：`ninedim/01-意图环/04-规格/envelope-validation.spec.md:78`
   要求「触发**法律、门禁、账本、读模型**四类失败路径」，而被引的
   `scripts/test/contract.rs::c15_errors_carry_machine_readable_codes` 的七条码来源
   （`scripts/test/contract.rs:714/718/728/738/748/758/767`）**没有一条是账本路径**；
   全仓唯一的账本码断言在 `scripts/test/cli.rs:155`，而 `check.sh.new` **从不跑 `--test cli`**
   （`check.sh.new:98` 逐字 `cargo test --locked --test acceptance -- t1_ t2_ t7_`、
   `:103` 逐字 `cargo test --locked --test contract`）。**归档后这条要求的"证据"是空的。**
3. **不改就没有任何机制会变红。** 本项目的证据行只到「测试名存在」这一级：
   `fc-2026-001` 的 `tasks.md:16/17`、`design.md:121` 自报的口径逐字是「证据行指向真实存在的测试名」
   「6 份规格 / 40 条证据 / 0 条未命中」。**名字存在 ≠ 断言的真是那件事**——
   这 46 条正好落在这个差值里，且没有任何脚本会因它们变红。

**为什么这 46 条是一个变更而不是 46 个**：它们**不改任何行为、不改任何代码、不改任何测试**，
只改规格文本；46 条的「不改的后果」是同一句话——**规格基线把未定的、错的、缺的说成了已定**。
按 `schema.yaml:8-9` 的判据（「若两处改动的不改的后果不同，就是两个变更」），后果相同 ⇒ 一个变更。

## What Changes

**只动 `ninedim/06-变更/fc-2026-002-spec-revisions/specs/**` 下的 delta 文本。**
不动 `` 下任何一行代码或测试，不动 `ninedim/01-意图环/04-规格/` 下的既有基线文件（delta 在归档时才合并），
不动 `fc-2026-001` 的任何一件产物。

按 `audit.md` 的分类，改动类型**限定为四类**，逐条可核：

| 类型 | 含义 | 本 change 里的例子（出处） |
|---|---|---|
| ① 措辞**写宽** | 要求强于断言 | `gate-enforcement`：`spec.md:54` 写「属主与权限」，实现只看 mode 位（`src/guard.rs:31`） |
| ② 措辞**写窄** | 实现有、规格无 | `channel-identity`：缺省拒绝 `ext.world.Channel.NotConfigured`、空 `listeners` 拒载（`src/channel.rs:89-94`）无落点 |
| ③ **证据错位** | 挂的测试断言的不是那件事 | `envelope-validation`：t5 的证据行写「`check.sh` 步骤 ③」，而该步只跑 `t1_ t2_ t7_`（`check.sh.new:98`） |
| ④ **与项目文档冲突** | 规格把已知缺陷写成已成立 | `ledger-integrity`：v1 兼容 vs K-3【高】（`策划-WC-SCMP-001-v0.1.md:2537`） |

**不新增能力。** 所有 delta 走 `## MODIFIED Requirements`，改的是既有能力的既有 Requirement，
**每条贴出完整 Requirement 块**（从 `### Requirement:` 到其下全部 Scenario），
只贴改动部分会在归档时丢细节（`schema.yaml:59`）。

**R5 必做的三处方向改写**（P0，逐条见 §`design.md` 的排除清单与方案对比）：
把与实测和项目文档冲突的写法改成一致，**并把该能力的边界写成正式 Requirement/Scenario，而不是注意事项**——
照 `ledger-integrity` 对摘要链 `c18` 那条的既有写法（`ninedim/01-意图环/04-规格/ledger-integrity.spec.md:101-106`
「整本重写按设计检不出（边界固定）」）。

## Capabilities

### New Capabilities

无。本 change **不新增任何能力**。

### Modified Capabilities

逐条与 `ninedim/01-意图环/04-规格/` 下已存在的路径完全一致（6 份全中）：

| capability-path | 覆盖什么 | 本 change 落的条目（`audit.md` 编号） |
|---|---|---|
| `channel-identity` | 身份取自内核而非请求自称 | C1 C2 C3 C4 C5 C6 |
| `envelope-validation` | 信封必填字段 / 三类话 / 法律损坏拒启 / 事件 id 唯一 / 错误码 | E1 E2 E3 E4 E5 E6 E7 E8 |
| `gate-enforcement` | 每个写动作过闸 / change 不偷渡 / 不可逆 / 配置在被管者不可写的域 / 不重读策略 | G1 G2 G3 G4 G5 G6 |
| `ledger-integrity` | 按序落账 / 单写者 / 尾部与 seq / 行边界 / 摘要链 / 回滚 | L1 L2 L3 L4 L5 L6 L7 L8 L9 |
| `projections` | 两份读法同源 / 语言投影与读模型 / 排版契约 | P1 P2 P3 P4 P5 P6 P7 |
| `read-model` | 可丢弃的缓存 / 增量=全量 / 检查点 | R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 |

## 档位判定

| 项 | 判定 | 依据 |
|---|---|---|
| **A/B 档** | **B 档** | 三条判据逐条命中：① 有第二个人需要交接——评审席要按 `review.md` 复核 46 条；② 有外部交付物与验收责任——`ninedim/01-意图环/04-规格/**` 是需求内容的机读权威载体（`boundary.md` §一），改它即改对外承诺；③ 失效后果不可接受——把 K-3【高】读成"平滑升级"会让历史账本在升级后锁死。三条全不命中才可 A 档，故 B 档 |
| **评审档位** | **R5**（框架变更） | 触及敏感路径 `ninedim/01-意图环/04-规格/**`（6 份全中）。按 `schema.yaml:23-24` 判据「触及契约 / 门禁 / 工具 / 工作流 → 框架变更 → R5」 |
| **命中的敏感路径** | `ninedim/01-意图环/04-规格/**`（6 个能力目录全部）；另**间接**触及 `check.sh.new`（仅作为证据锚点被引用，**不改它**）；`ninedim/records/openspec-流程件/openspec-config.yaml` 未触及；`tools/**` 未触及；`.github/workflows/**` 未触及 | 逐条列出，见上一行 |

**R5 触发条件**：**FC-3（假设被推翻）** 为主，**FC-1（契约不足）** 为辅。

- **FC-3**：规格的措辞建立在若干**已被实测推翻**的假设上——「v1 无链账本可平滑升级」（K-3 推翻）、
  「摩擦挂在动作的不可逆等级上」（`gate.rs:287-293` 推翻）、「两份读法同源可当场核对」（`project/mod.rs:124-145` 推翻）。
- **FC-1**：契约不足以表达边界——`openapi` 式的正例条款写不出「这条能力在哪一刻不成立」，
  故必须补边界条款（照 `c18` 那条的写法）。
- **FC-6（个人偏好）不适用**：本 change 的每一条都有实测或受控文档出处，**无一条是"这样更优雅"**。

**现象证据**（逐条可复算，全部为**读源码/读受控文档**级证据；带「实跑」字样的为 `audit.md` 在 VM 内实跑留档）：

| # | 触发条件 | 现象证据（文件路径 + 行号 + 逐字引文 / 命令与 rc） |
|---|---|---|
| 1 | FC-3 | `ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md:2537` 逐字「### K-3【高】在 v1（无链）账本上做一次正常 `append` 会把世界锁死 —— 升级路径自杀」；同件 `:2541` 逐字「**后果（EV-11b）**：无链账本 → `check` 警告但 `READY`（**设计意图是兼容**）→ 一次合法 `append` 成功 → 下次打开 `Ledger.MixedChain … 拒绝使用`」 |
| 2 | FC-3 | `src/gate.rs:287-293` 逐字 `Some(c) if !c.reversible => { if self .irreversible_actors .iter() .any(\|a\| pattern_matches(a, actor)) { Decision::Allow }` ⇒ **白名单主体执行不可逆动作时判 `Allow`、不加摩擦**；而 `ninedim/01-意图环/04-规格/gate-enforcement.spec.md:36` 逐字写「系统 SHALL 对声明为不可逆的能力追加摩擦」 |
| 3 | FC-3 | `src/project/mod.rs:124-145` 是 `assert_same_source`，其三个不等分支在 `project check` 里**结构上不可达**——`src/main.rs:408-409` 逐字 `let a = language::render(&state, world, vocab);`／`let b = visual::render(&state, world, vocab);` 两份投影**共用同一个 `state` 与 `vocab`** |
| 4 | FC-1 | `ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md:736` 逐字「**绿而无效**。命令跑得通（`world-core project check`），只比头部四项（`src/project/mod.rs` 第 124 行），两份还是它自己渲染的（`src/main.rs` 第 394–397 行，2026-09-27 读）。按"能不能证明"判，这一格是红的」 |
| 5 | FC-1 | `scripts/test/contract.rs:120-123` 逐字 `assert!( msg.contains("MissingField") && msg.contains(field), "删除 \`{field}\` 应被拒且指明字段，实得: {msg}" );`，而 `src/ontology.rs:32` 的错误前缀自带 `ext.world.` ⇒ `field=="world"` 那一轮**恒真** |
| 6 | FC-3 | 门禁**读不到风险等级**：`src/gate.rs:44-48` 的结构只有 `pub reversible: bool` 一个字段（`ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md:721` 逐字「闸读的那份评级里只有一个布尔值」）；而 `cap.d/*.json` 逐项写 `risk`，`risk` 只被 `src/carrier/capd.rs:186` 读 |

**环境指纹**：本 change 的**起草**在主机 `D:\Code\08-worldcore-openspec`（Windows）完成，
源码与文档证据逐条用 `read` 工具就地读取；**实施（补断言）与验收只在 VM `world` 内做**，
VM 实测可用（`ssh world` rc=0、`Linux world 7.2.6-arch2-1`、`cargo 1.98.1 (797e8a9bc 2026-08-05)`）。
主机**无 Rust 工具链** ⇒ 本 change 的**任何 cargo 断言都不得在主机上声称跑过**。

## Impact

- **代码**：无。`` 下一行不改。
- **测试**：无既存测试被改；**新增断言**是 `tasks.md` 里的一组任务（补 C6/L5/L6/E3/E5/G4/R5 等缺失断言），
  但那些断言属**实施期**工作，且按用户口径「若该证据今天不存在，不得编造」——
  本 change 的 delta 对不存在的断言**逐条写"需补断言（列进 tasks）"**。
- **API / 依赖 / 系统**：无。
- **规格基线**：6 个能力目录全部被 MODIFIED；归档时 delta 合并入 `ninedim/01-意图环/04-规格/**`。
  合并后**基线文本会变**，故本 change 归档即等于**框架基线的一次更新**。
- **使用方（需通知）**：① 评审席（按 `review.md` 逐条复核 46 条）；② 依赖 `ninedim/01-意图环/04-规格/**`
  作为"这台东西今天承诺什么"的读者（`boundary.md` §一）；③ 流程侧的 SRS/RTM 维护者——
  本 change 会让「规格说 A、SRS 说 B」的若干处**收敛到 SRS 与实测那一侧**（如 C1：SRS:266/268/383、RTM:29/31 写「拒绝且不落笔」）。
- **文档**：不改任何流程侧文档。规格与流程的编号桥**本 change 不动**（编号补齐另立 change，
  见 `design.md` 排除清单）。
