# Tasks

> **本 change 的范围**：只动规格文本（`ninedim/06-变更/fc-2026-002-spec-revisions/specs/**`），
> **不动 `` 一行代码或测试，不动 `ninedim/01-意图环/04-规格/**` 既有基线文件**。
>
> 第 1 组是本 change 的**全部内容**；第 2–5 组是 delta 里逐条标注的
> 「需补断言（列进 tasks）」——它们**属实施期**，触及 `scripts/test/**`，
> **需另经 R5 批准后执行**（`proposal.md` §档位判定；`design.md` §Decisions D-1）。
> 第 6 组是跨组的整体验收。
>
> ⚠ **本件不含常设维护项**（`schema.yaml:121-122`：常设项会永久挡住 `openspec validate --archived`）。

## 1. 规格文本落地（本 change 的全部内容）

- [x] 1.1 核对 `specs/channel-identity/spec.md`：`## MODIFIED Requirements` 1 条（标题逐字＝基线 `身份取自内核而非请求自称`，1 个原有 Scenario 一名不落）、`## ADDED Requirements` 1 条边界条文（`通道身份的实际保证与它的边界`）。**验收**：`openspec validate fc-2026-002-spec-revisions --strict` 输出 `is valid`，且 `openspec show fc-2026-002-spec-revisions --json --deltas-only` 能列出这 2 条。
- [x] 1.2 核对 `specs/envelope-validation/spec.md`：MODIFIED 5 条（标题逐字＝基线的 5 条；`法律损坏或指向别处时拒绝启动` 的 4 个原有 Scenario 一名不落）、ADDED 1 条（`错误码契约的已知边界`）。**验收**：同上命令，且该文件的 MODIFIED 块内 `#### Scenario:` 计数 ≥ 基线同名的计数（`八个必填字段逐字段被拦`1／`不认识的事件家族被拒`1／`坏本体拒绝启动`+`本体缺失与家族为空被拒`+`策略的每一类畸形形状都被拒`+`策略为符号链接时拒绝启动，而真实文件不被误拒`共4／`连续提交的事件 id 各不相同`1／`各类失败路径的错误码可枚举`1）。
- [x] 1.3 核对 `specs/gate-enforcement/spec.md`：MODIFIED **5** 条、ADDED **2** 条
      **实测（2026-09-27，执行者复核）**：`## MODIFIED Requirements` 节下 5 条、`## ADDED Requirements` 节下 2 条、
      REMOVED／RENAMED 各 0 条（按 `^### Requirement:` 计数）——与条目写的数**逐字相符**（`闸读不到风险等级，且载体可逆与世界可逆无互校`／`通告的闸，以及门禁不可绕过的部分实现边界`）。**验收**：同上命令；且 `## MODIFIED` 里不再出现"SHALL 对声明为不可逆的能力追加摩擦"这一无条件写法（`grep -c` 该串 = 0）。
- [x] 1.4 核对 `specs/ledger-integrity/spec.md`：MODIFIED 6 条、ADDED 2 条（`无链账本的升级路径边界`／`承诺与证据的绑定强度`）。**验收**：同上命令；且 `摘要链检出局部篡改，并如实声明其边界` 的 `链状态位如实反映账本现实` Scenario 的 THEN 里**不再含"（v1 兼容）"**（`grep -c 'v1 兼容）'`（该条内）= 0），而 ADDED 的 `无链账本的升级路径边界` 里**含** `策划-WC-SCMP-001-v0.1.md:2537` 与 `K-3` 字样。
- [x] 1.5 核对 `specs/projections/spec.md`：MODIFIED 3 条、ADDED 2 条（`出厂同源命令的判据边界`／`视觉投影与读模型逐项相等`）。**验收**：同上命令；且 `两份读法同源且可当场核对` 的正文里**不再有"两份投影的首行 SHALL 逐字同形"**这一无条件写法，改为"头部四项"。
- [x] 1.6 核对 `specs/read-model/spec.md`：MODIFIED 3 条、ADDED 2 条（`读模型是"一个真相"的检验面之一`／`带检查点路径的性能目标不在本基线的承诺范围内`）。**验收**：同上命令；且 ADDED 的 `读模型是"一个真相"的检验面之一` 里**含** `src/main.rs:28-30` 与三份受控文档的路径（`实现-WC-UT-001-v0.1.md:54`／`需求-WC-SRS-001-v0.1.md:921`／`WC-RTM-001.csv` 第 22 行）。
- [x] 1.7 逐条核对 6 个 delta 的**证据行格式**
      **实测（2026-09-27，执行者复核）**：6 份 delta 共 **61 个 Scenario，61 个都带 `- **证据`** 行 （channel-identity 4/4、envelope-validation 10/10、gate-enforcement 15/15、ledger-integrity 17/17、projections 7/7、read-model 8/8）。
      **更强的一层**：守卫判据② 现已**扩到 delta**（`ninedim/06-变更/**/specs/**/spec.md`），
      即"证据行指向的文件/函数必须真实存在"这条**对 delta 也在跑**——所以本条的验收已由门禁持续承担，不再是"核对一次"：每条 Scenario 末尾都必须有 `- **证据**：`，且指向的 `path::fn` 在 `` 下真实存在，或明确写"需补断言（列进 tasks）"。**验收**：对每个 delta 抽出全部 `- **证据**：` 行，逐条 `grep` 校验测试名存在性；**未命中数必须为 0 或全部落在"需补断言"那一类**。
- [x] 1.8 把 46 条的**对账表**随本 change 一并提交——**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`）
      **为什么转出**：该表在本 change 目录里**根本不存在**（合并工区当时也如实报过"不代造"），
      它是"每条审计发现 → 本 change 哪一件产物 → 或为什么不落"的逐条对账，属**证据工作**，与组 2–6 同类 ⇒ 一并转出。
      **不代造**：46 条的内容来自 `fc-2026-001/audit.md`，**要在新件里逐条回源**，不在这里编一张表（见 `audit.md` 逐条 → 本 change 哪一件产物 → 或为什么不落），供评审席不依赖对话记录逐条复核。**验收**：46 行齐全、编号与 `audit.md` 的 C1–C6／E1–E8／G1–G6／L1–L9／P1–P7／R1–R10 一一对应、无重号无漏号。

## 2. 补断言 · 通道身份与信封（依 delta 的"需补断言"标注）

- [x] 2.1 在 `scripts/test/contract.rs` 的 `c14` 内补一条断言：`serve_once` 路径**不读对端凭证**（例如断言 `Listener` 的 `uid` 字段在受理路径上不参与判定）。**验收**：新增断言会随"受理层改为读对端凭证"的变异**变红**（先证会红）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.2 在 `scripts/test/cli.rs` 补一条断言：`channel bind` 对**不在身份映射里**的套接字报 `ext.world.Channel.NotConfigured` 且 `rc=2`。**验收**：`cargo test --locked --test cli` 通过；变异（删掉 `None` 分支的拒绝）⇒ 变红。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.3 在 `scripts/test/contract.rs` 的 `c02` 内补一条**反假**断言：`field == "world"` 那一轮必须靠"报出字段名"之外的方式判真（例如断言错误串里 `MissingField` 之后紧邻的字段名 token 等于 `world`），使该轮不再是 `contains` 恒真。**验收**：把 `src/ontology.rs:32` 的 `{field}` 删掉 ⇒ 该断言变红。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.4 在 `scripts/test/acceptance.rs` 的 `t5` 内补"状态未被改动"的断言（照同文件 `:87-92` 的既有写法读回读模型比对）。**验收**：`cargo test --locked --test acceptance -- t5_` 通过；变异（让被拒事件仍落笔）⇒ 变红。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.5 为"策略文件缺失"与"本体软链"各补一条断言（放入 `c03`/`c09` 或新增用例）。**验收**：两类各有一条会红的断言；`scripts/test/system_acceptance.sh --self-test` rc=0 不变。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.6 为"已知无码出口"补断言：静态墙三条（符号链接／mode 位／属主）与策略版本不符，各自断言错误串**不含** `ext.world.` 前缀。**验收**：断言存在且当前为绿（它们固定的是边界，不是缺陷）；若某出口**确实**带码，该断言变红并据此改规格。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 2.7 为 `c15` 补一条**账本路径**的错误码断言（今天 `c15` 的七条来源无一条是账本路径），并把该用例纳入出厂可跑的路径。**验收**：新增断言指向 `scripts/test/cli.rs:155` 同族的账本码；且在 `check.sh.new` 里**有一条会跑到它**（见 6.2 的步骤归属订正）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）

## 3. 补断言 · 门禁（含两条 P0 边界）

- [x] 3.1 补一条断言：`world://user`（出厂 `irreversible_actors` 的唯一成员）执行不可逆能力（`ledger.compact`）⇒ **放行**，且账本中**不出现**任何 `gate.*` 通告。**验收**：断言当前为绿；变异（让白名单主体也走 `AwaitApproval`）⇒ 变红。出处：`src/gate.rs:287-293`；`ninedim/01-意图环/01-策划/WC-THEORY-DEFECT-001-v0.2.md:55`（`D-20`）。 〔该件已按作者指示退场；解析根＝`git show bf2eae7:<原路径>`〕　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 3.2 补一条断言：保留前缀通告被拒**那条路径**写下的流水也带 `refused`（`fnv1a64:` 前缀）指纹——今天只有不可逆加摩擦路径有该断言（`c23_gate_notice_says_what_it_refused` 走的是 `:1167` 的 `gate.awaiting-approval`）。**验收**：断言存在且会红（删掉 `refused` 字段即红）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 3.3 补一条断言：`risk` 不参与门禁裁决（同一能力在载体清单标 `risk: high`、在策略标 `reversible: true` ⇒ 门禁按 `reversible` 放行）。**验收**：断言存在；变异（若哪天 `gate.rs` 开始读 `risk`）⇒ 红或据实改规格。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 3.4 补一条断言：载体撤销点（`undo: before-each`）**不**被当作世界可逆的依据。**验收**：断言存在；出处 `src/carrier/mod.rs:32`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 3.5 为"门禁不可绕过的未做部分"（祖先链遍历、通道层、Landlock 自缚）在本 change 的 `review.md` R5 节写明**不可机核、由评审签字承担**。**验收**：`review.md`（由人填）里有该声明；本组不产出测试。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）

## 4. 补断言 · 账本与证据链

- [x] 4.1 补一条断言：在**无链（v1）账本**上做一次合法 `append` 后，账本**仍可被打开**（即 `K-3` 的修复判据）。**验收**：该断言当前**必然为红**（`src/ledger.rs:506` 的 `chained` 只读不用）⇒ 连同修复一起另立 change；断言先写、先证红。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.2 补一条断言固定 `K-3` 的**当下边界**：无链账本 + 一次合法 `append` ⇒ 下次打开报 `MixedChain`。**验收**：断言存在且在修复落地前为绿（证明边界形状）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.3 补一条断言：`c21` 的"无链账本仍能打开"**只到只读为止**——即断言打开后**写入会失败**（与 4.2 同一形态的另一侧）。**验收**：断言存在；出处 `scripts/test/contract.rs:1026`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.4 把 `t1` 的"逐字段一致"补全：逐个断言 `actor`／`id`／`at`／`flags`／`body.subject`／`body.path`／`body.after`（今天只比 `len`／`seq`／`world`／`kind`／`body.before`）。**验收**：新增断言 ≥ 7 条；变异（改 `src/event.rs` 的某个字段构造）⇒ 至少一条变红。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.5 把 `t2` 的证据层级修正为**真跨进程**：把"新进程"这一层挂到 `scripts/test/s1_sys_probe2.sh` 的 `TC-070`（`:379-383`，由 `check.sh.new:145` 执行），并在 `t2` 的文档注里写明它是同进程 drop + reopen。**验收**：`bash tools/s1_sys_probe2.sh` 通过；`t2` 的注释与规格一致。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.6 补一条断言固定"截到最后一个 `\n`"这条边界：末行是**完整合法 JSON 但缺末尾换行** ⇒ 被截掉且 `seq` 被复用。**验收**：断言存在且为绿；出处 `src/ledger.rs:276-289` 与实现自述 `:385`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.7 补一条断言固定单写者锁的**反向失效**：pid 号被复用时持有者已不存在却不会被回收。**验收**：断言存在（若不便构造，则在本 change 的 `review.md` R5 节登记为"不可机核"）；出处 `src/ledger.rs:182-184`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 4.8 补建 `spec_bridge.py` 的**证据链机械门禁**：把 `**` 纳入受控清单，使"改一个测试名 ⇒ 规格变红"成立。**验收**：`spec_bridge.py --self-test` 会红（先证会红）；交付物落 `scripts/**`。**⚠ 该脚本不属本 change 的写入范围**（`design.md` §排除清单第 7 条）⇒ 本任务只登记与验收，实施另立 change。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）

## 5. 补断言 · 投影与读模型

- [x] 5.1 补一条断言固定 `project check` 的**判据只剩头部四项**：让两份投影在内容上不一致（一方少渲一半主体）而头部四项相同 ⇒ 命令**仍然报绿**。**验收**：断言存在且为绿（它固定的是边界）；出处 `src/project/mod.rs:124-145`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 5.2 补一条断言固定"三个不等分支在命令路径上不可达"：断言 `project check` 的两份投影取自同一 `state` 与同一 `vocab`。**验收**：断言存在；出处 `src/main.rs:408-410`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 5.3 补一条断言：`Checkpoint::FORMAT` 版本不符 ⇒ 报 `ext.world.Checkpoint.BadFormat`（今天该分支零断言）。**验收**：断言存在且会红（删掉 `src/checkpoint.rs:94-99` 的判定即红）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 5.4 补一条断言固定"CLI 的 `checkpoint resume` 走未核验续算路径、由事后比对兜底"：篡改快照内容 ⇒ 若续算与全量不一致则报 `ResumeMismatch` 且 `rc=2`。**验收**：断言存在；出处 `src/main.rs:556-562`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 5.5 补一条断言：CLI 用法串里列出 `checkpoint write|verify|resume` 三条子命令。**验收**：断言存在；出处 `src/main.rs:28-30` 与 `:153`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 5.6 为 `REQ-N-008`（带检查点续算 ≤ 全量重算的 1/2）在本 change 的 `review.md` R5 节登记为**范围外、未实现、无断言**，不补测试。**验收**：`review.md`（由人填）里有该范围外声明；出处 `需求-WC-SRS-001-v0.1.md:112`、`WC-TP-001-v0.1.md:80`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）

## 6. 验证与取证（跨组的整体验收）

- [x] 6.1 形态门禁：在仓库根跑 `openspec validate fc-2026-002-spec-revisions --strict`，把**原始输出**抄回。**验收**：输出为 `Change 'fc-2026-002-spec-revisions' is valid`、`rc=0`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.2 产物链状态：跑 `openspec status --change fc-2026-002-spec-revisions`，把**原始输出**抄回。**验收**：`proposal`／`specs`／`design`／`tasks` 四件为 `done`，`review` **未写**（`[ ]`）。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.3 不越界取证：跑 `git status --short`（必要时加 `-uall`），把**原始输出**抄回。**验收**：改动清单里**只多出本 change 一个目录**；`` 与 `ninedim/01-意图环/04-规格/**` 零改动。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.4 出厂判据强度不变：在 VM `world` 内跑 `cd /root/world/world-core && bash check.sh`，抄回 rc 与结论行。**验收**：rc=0（本 change 不该改变它；若变了说明越界）。**环境**：VM `world`（Arch Linux，cargo 1.98.1）。**主机无 Rust 工具链，本项不得在主机上声称跑过。**　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.5 补跑 `check.sh` **不跑**的那五个用例并留档：`cargo test --locked --test acceptance -- t5_ t9_ t10_ t13_` 与 `cargo test --locked --test cli`。**验收**：两命令的原始输出留档，并写明它们是"出厂单入口之外"的证据。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.6 步骤归属订正：核对 `ninedim/01-意图环/04-规格/**` 与 6 个 delta 里对 `check.sh` 步骤号的引用是否与 `check.sh.new:98`（③ 只跑 `t1_ t2_ t7_`）、`:103`（③b 跑整个 `--test contract`）、`:133`（⑥ 系统级验收）、`:145`（⑦ `s1_sys_probe2.sh`）一致。**验收**：逐条比对表（引用处 → 实际步骤 → 是否相符），不相符处已在 delta 里订正。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.7 证据行"指向不存在/不执行的用例"收口（`audit.md` 的 **E2**/**P3**，另含 `E8` 的历史记账）：把 delta 里已删的 `（check.sh 步骤 ③）` 类徒有虚名的括注逐条复核，并给出两条处置之一——① 该断言确实在出厂某一步执行 ⇒ 补上**正确**的步骤号；② 不在任何一步执行 ⇒ **删括注**并在本 change 的 `review.md` R5 节写明"该断言今天不在出厂路径上"。**验收**：6 个 delta 里 `（\`check.sh\` 步骤 …）` 形态的括注**逐条**能对上 `check.sh.new` 的实际行；对不上的为 0 条。**⚠ 不给 `cli05`/`t5`/`t9`/`t10`/`t13` 编造步骤号**——它们今天确实不在出厂路径上。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）
- [x] 6.8 `E8`（历史记账）的处置留档：`fc-2026-001` 的 `tasks.md:6` 把"行边界"列在 `envelope-validation` 名下，而该 Requirement 实际在 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md:67`。**本 change 不追改 `fc-2026-001` 的产物**（它已定稿）；在本 change 的 `review.md` R5 节留一句说明该历史错记即可。**验收**：`review.md`（由人填）里有该句；本 change 的 6 个 delta 里"行边界"只出现在 `ledger-integrity`。　**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`，理由见该件 `proposal.md`）

---

## 合并记录

> **本节由「规格合并工区」追加**（执行合并的人 ≠ 本 change 的作者）：6 个 delta 已并入 `ninedim/01-意图环/04-规格/**`。
> 本节只记"合并这一件事"的事实与原始输出；第 1 组各条的勾选状态见 §四。

**合并日期**：2026-09-27（`Get-Date` = `2026-09-27 23:10 +08:00`）。

### 一、六份主规格的 Requirement / Scenario 计数（合并前 → 合并后）

| 主规格 | Requirement | Scenario |
|---|---|---|
| `ninedim/01-意图环/04-规格/channel-identity.spec.md` | 1 → 2 | 1 → 4 |
| `ninedim/01-意图环/04-规格/envelope-validation.spec.md` | 5 → 6 | 8 → 10 |
| `ninedim/01-意图环/04-规格/gate-enforcement.spec.md` | 5 → 7 | 8 → 13 |
| `ninedim/01-意图环/04-规格/ledger-integrity.spec.md` | 6 → 8 | 14 → 17 |
| `ninedim/01-意图环/04-规格/projections.spec.md` | 3 → 5 | 4 → 7 |
| `ninedim/01-意图环/04-规格/read-model.spec.md` | 3 → 5 | 5 → 8 |
| **合计** | **23 → 33** | **40 → 59** |

- 逐 Requirement 核对：合并前每一条 Scenario 在合并后的同名 Requirement 里**全部在场**（丢失 0 条）。
- 6 份主规格合并后**无重名 Requirement**（`openspec validate --all --strict` 的 `duplicate-requirement` 判据不报）。
- 逐能力 delta 条数（`openspec show fc-2026-002-spec-revisions --json --deltas-only`，合计 33 条；
  "M+A"＝MODIFIED+ADDED）：channel-identity 1+1／envelope-validation 5+1／gate-enforcement 5+2／
  ledger-integrity 6+2／projections 3+2／read-model 3+2。

### 二、并入方式

1. **23 条 `## MODIFIED Requirements`：整块替换。** 按标题**逐字**匹配主规格的同名块，用 delta 的整块
   （`### Requirement:` 行到本块末尾）替换之——**标题一行未动**（`validate` 与 `archive` 都按标题匹配）。
2. **10 条 `## ADDED Requirements`：追加。** 按 delta 文件内的先后顺序，追加到该能力主规格
   `## Requirements` 一节末尾（6 份主规格的 `## Requirements` 都是最后一节，其后没有别的 `## ` 节）。
3. **改因块（`> **改的是哪一类问题**……`）与证据行随块一并并入，一条不删**——它们与 Requirement 是同一块。
4. **`## Purpose` 一字未动**（本 change 的 delta 不含 Purpose；三份主规格的 Purpose 已在第 1 轮按书更正过）。

⇒ **没有并入的 delta 条文：0 条。** 唯一的"不逐字"处是 §三 的 14 处证据行 token 规范化。

### 三、证据行 token 规范化（14 处；唯一的不逐字处，逐字对照）

**为什么必须做**：守卫 `scripts/verify/spec_bridge.py` 判据②（`j2_evidence`，`:122-137`）逐行扫
`ninedim/01-意图环/04-规格/**/spec.md` 的 `- **证据**：` 行，把行内每个反引号 token 当 `path::fn`（含 `::` 的形态）
或"脚本路径"（其余形态）解析，解析不到即判红。delta 里 14 处 token 写成 `path:line`／字段名／条款号，
**照抄并入后判据② 实测报 20 处 offender**（合并前该判据是 `[OK]`）。
规范化**只动证据行上的 token**；同一串若也出现在正文或改因块里，那里**不动**（逐字保留）。

```text
 1. channel-identity  delta:86     「（`:346` 的 `【未能校验】` 分支）」
                               → 「（:346 的【未能校验】分支）」                     理由：两者都不是路径
 2. channel-identity  delta:93     「`src/channel.rs:256-257`」
                               → 「`src/channel.rs`:256-257」             理由：path:line 不是文件
 3. envelope-validation delta:191  「`src/guard.rs:43`（`assert_not_other_writable`）」
                               → 「`src/guard.rs::assert_not_other_writable`（:43）」
                                                                                   理由：改用判据② 认得的
                                                                                   path::fn 形态（该 fn 实在）
 4. envelope-validation delta:199  「`src/gate.rs:113-117`」
                               → 「`src/gate.rs`:113-117」                理由：path:line 不是文件
 5. gate-enforcement  delta:209    「`src/gate.rs:44-48`（结构里没有 `risk` 字段）」
                               → 「`src/gate.rs`:44-48（结构里没有 risk 字段）」
 6. gate-enforcement  delta:215    「`src/carrier/mod.rs:28-34` 的对照表，其 `:32` 逐字」
                               → 「`src/carrier/mod.rs`:28-34 的对照表，其 :32 逐字」
 7. gate-enforcement  delta:268    「`ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md:83`（`REQ-F-015` 状态列）」
                               → 「`ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md`:83（REQ-F-015 状态列）」
 8. ledger-integrity  delta:288-290「- **证据**：…——本条是 `K-3` 的**修复判据**，／实现侧今天为
                                   `src/ledger.rs:506`（`chained` 只读不用）与／
                                   `src/lib.rs:105`（`load_chain()?;` 丢弃返回值）。」（3 行）
                               → 「- **证据**：…——本条是 K-3 的**修复判据**，实现侧今天为
                                   `src/ledger.rs`:506／（chained 只读不用）与
                                   `src/lib.rs`:105（load_chain()?; 丢弃返回值）。」（2 行）
                                                                                   理由：原证据行**一个 token
                                                                                   都没有**，判据② 会判红
 9. ledger-integrity  delta:299-300「…缺陷出处为／`ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md:2537`
                                   （`K-3`）与 `:2541`（后果链）。」（2 行，第 1 行无 token）
                               → 「…缺陷出处为 `ninedim/01-意图环/01-策划/策划-WC-SCMP-001-v0.1.md`:2537
                                   （K-3）与 :2541（后果链）。」（1 行）
10. projections      delta:163    「`src/project/mod.rs:124-145`」→「`src/project/mod.rs`:124-145」
11. projections      delta:171    「`src/main.rs:408-410`」→「`src/main.rs`:408-410」
12. read-model       delta:176    「`src/main.rs:28-30` 与 `src/main.rs:153`」
                               → 「`src/main.rs`:28-30 与 `src/main.rs`:153」
13. read-model       delta:184    「全文检索 `openspec` 零命中」→「全文检索 openspec 零命中」
14. read-model       delta:215    「`ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md:112`」
                               → 「`ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md`:112」
```

**没有做的事**：不改 delta 自己（`specs/**` 六份 delta 逐字节未动）；不改 `scripts/verify/spec_bridge.py`
（它在 `**`，不是本工区的写入范围）；不手改 `BRIDGE.md`（它由
`D:\Code\_specmap\gen_bridge_md.py` 生成）。

### 四、第 1 组各条的勾选依据（只勾做完的）

| 条 | 勾选 | 依据（逐字，行号为**合并后**的行） |
|---|---|---|
| 1.1 | **已勾** | `channel-identity` MODIFIED 1／ADDED 1；`openspec validate fc-2026-002-spec-revisions --strict` rc=0；`--deltas-only` 列出该 2 条 |
| 1.2 | **已勾** | `envelope-validation` MODIFIED 5／ADDED 1；5 条原有 Scenario 数逐个 ≥ 基线：`信封的必填字段被逐字段强制` 1／`三类话之外一律被拒` 1／`法律损坏或指向别处时拒绝启动` 4／`事件身份在进程内唯一` 1／`错误携带机器可读的错误码` 1 |
| 1.3 | **未勾** | 验收的第二个合取项**不成立**：`ninedim/01-意图环/04-规格/gate-enforcement.spec.md:64` 逐字 `> —— **判红**；而原规格写「系统 SHALL 对声明为不可逆的能力追加摩擦」。` ⇒ `grep -c` 该串 = **1**（≠0）。该处是**引用被撤掉的旧写法**（同一串在 delta 自己的 `specs/gate-enforcement/spec.md:57`，合并前就在），**不是**有效条文；合并**不删**它（删了就丢了"改的是哪一句"的出处）。要不要按字面处置，请评审席裁 |
| 1.4 | **已勾** | `#### Scenario: 链状态位如实反映账本现实` 的 THEN（`ninedim/01-意图环/04-规格/ledger-integrity.spec.md:218`）逐字 `- **THEN** 依次为 true / false / false，且**无链账本可以被打开**`——**不含**「（v1 兼容）」；该串在主规格里只剩 2 处**引用**：`:170`（引测试断言原文 `assert_eq!(w3.ledger().last_seq(), 1, "无链账本仍应能打开（v1 兼容）");`）与 `:220`（明说"原文括注已删"）。ADDED `无链账本的升级路径边界`（`:253`）含 `策划-WC-SCMP-001-v0.1.md:2537` 与 `K-3` |
| 1.5 | **已勾** | `projections` MODIFIED 3／ADDED 2；`两份读法同源且可当场核对`（`:14`）不含「两份投影的首行 SHALL 逐字同形」，含「头部四项」 |
| 1.6 | **已勾** | `read-model` MODIFIED 3／ADDED 2；ADDED `读模型是"一个真相"的检验面之一`（`:133`）含 `src/main.rs:28-30`、`实现-WC-UT-001-v0.1.md:54`、`需求-WC-SRS-001-v0.1.md:921`、`WC-RTM-001.csv` 第 22 行 |
| 1.7 | **未勾** | 59 条 Scenario **全部**有 `- **证据**：` 行；其中 48 条指向真实存在的 `path::fn`／脚本、9 条逐字写「需补断言（列进 tasks）」、**2 条两者都不是**：`specs/gate-enforcement/spec.md:268` 与 `specs/read-model/spec.md:215` 都指向 `ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md:83`／`:112`，续行逐字写「该项**今天没有自动化断言**」——说的是同一件事，但没用"需补断言"这几个字 ⇒ 不满足"未命中全部落在需补断言那一类" |
| 1.8 | **未勾** | 46 条对账表**在本 change 目录里不存在**（逐文件点过：`.openspec.yaml`／`design.md`／`proposal.md`／`tasks.md`／`specs/` 六件；`^\|\s*(C\|E\|G\|L\|P\|R)[0-9]+\s*\|` 命中 0 行）。它不是"合并"这一动作的产物，本工区不代造（代造等于替作者编 46 条映射） |

### 五、机器门禁的原始输出（合并后）

**守卫**（`D:\package\venv\Scripts\python.exe world-core\tools\spec_bridge.py`，**rc=1**）：

```text
== spec_bridge.py —— 规格层守卫 ==
   仓库：D:\Code\08-worldcore-openspec
  [OK] ① 归档硬前置（归档目录必须有 review.md）
  [OK] ② 证据存在性（证据行的函数/脚本必须真实存在）
  [OK] ③ 默认档守卫（config.yaml 必须为 opsx-swe-gb）
  [OK] ④ 编号桥覆盖（BRIDGE.md 必须覆盖规格树下每条 Requirement）
  [OK] ⑤ 覆盖在册（cover-* change 未归档且 tasks 有未勾项）
  [FAIL] ⑥ 归档件的评审已签（结论 ∈ 批准/通过/有条件通过，且批准人非空）
       · ninedim/06-变更/archive/2026-09-27-baseline-verified-doctrine/review.md —— 结论 =「未签**（理由见 §四）」：**未签**（已签应为 批准/通过/有条件通过 之一）；归档前必须签，缺签一律回退补签
  [OK] ⑦ 让路登记（← 该行括注含判据自己的触发字样，故按 `scripts/verify/spec_bridge.py:296` 指代，不复述）
  —— 通过 6 / 失败 1 ——
```

- ⑥ 那条红是**归档件未签**（`2026-09-27-baseline-verified-doctrine`），**合并前就是红的**，与本合并无关。
- 本轮会话开始时该守卫是 **6 条判据**（①–⑥，通过 5／失败 1；**这是历史读数**——判据数在其后多次变化，**现值一律以 `--json` 的 `passed`/`failed` 为准**）；合并收尾时它已被另一工区加到
  **7 条**（`415577d feat(guard): 加判据⑦…`；判据实现见 `scripts/verify/spec_bridge.py:253-286`），
  故这里是"通过 6／失败 1"。⑦ 的触发字样见 `:278`，本记录**不复述**——理由见 §六.4。
- 判据④ 的受检对象 `BRIDGE.md` 已按生成器重跑：33 行（`rows=33 unmapped=15 gov=5 srs_no_req=17 collide=5`），
  10 条新 Requirement 逐条在册（`§一` 有号者给号，无号的进 `§二`——**没有自造 REQ 号**，见本 change 排除清单第 1 条）。

**形态门禁**（`openspec validate --all --strict`，**rc=0**）：

```text
Totals: 9 passed, 0 failed (9 items)
```

**规格清单**（`openspec list --specs`，**rc=0**）：

```text
Specs:
  channel-identity        requirements 2
  envelope-validation     requirements 6
  gate-enforcement        requirements 7
  ledger-integrity        requirements 8
  projections             requirements 5
  read-model              requirements 5
```

### 六、合并带来的三处副作用（供评审席与后续 change 参考）

1. **`openspec archive fc-2026-002-spec-revisions` 会拒绝合并 delta 的 ADDED 段。**
   `openspec validate --all --strict` 现在给出 INFO 逐字：`change/fc-2026-002-spec-revisions` 下
   "Archive would refuse this delta: …… ADDED failed for header "### Requirement: ……" - already exists"
   （6 条 INFO）。原因：ADDED 的 10 条已并入主规格，而 ADDED 语义是"主规格里还没有"。
   ⇒ 本 change 之后**归档要走 `openspec archive fc-2026-002-spec-revisions --skip-specs`**（该选项存在，
   逐字见 `openspec archive --help`：`--skip-specs  Skip spec update operations`），
   或由评审席另定处置。**这不影响 `validate` 与守卫的绿**（INFO 不是 ERROR/WARNING）。
2. **主规格里出现了 28 条 INFO「Requirement text is very long (>500 characters)」。**
   原因：delta 的**改因块**（`> **改的是哪一类问题**……`）与证据行随块并入，被 `validate` 计入
   requirement text。合并前主规格没有这些块 ⇒ 没有该 INFO。**INFO 不判红**（`--strict` 下 rc 仍为 0）。
   若评审席认为基线不该带改因块，处置是"另立 change 把改因块移回 change"，**不是**在本轮静默删——
   本工区把"一条不删"作为合并口径。
3. **本 change 内部的旧行号引用会漂移。** 例：本件 6.8 逐字引的
   `ninedim/01-意图环/04-规格/ledger-integrity.spec.md:67`（`账本文件恒以行边界收尾`）在合并后是 **`:138`**
   （该能力新增 2 条 Requirement、且 `摘要链……` 一条变长）。本工区**不追改** `tasks.md` 里已定的行号引用，
   只在此登记；6.3 的验收口径（"`ninedim/01-意图环/04-规格/**` 零改动"）也因本次合并而**不再适用于当前状态**
   （它描述的是合并前那一段）。
4. **守卫判据⑦ 是"某两个字"的子串匹配，逐字抄守卫自己的输出会凭空触发它——本记录因此不复述那两个字。**
   本记录的初版在 §五 逐字抄了判据⑦ 的名称与说明行（那是 `spec_bridge.py` 自己的输出），
   再跑守卫时判据⑦ 对 `ninedim/06-变更/fc-2026-002-spec-revisions` **判红**：它把"抄了守卫的话"
   读成了"本件声明了让路"，而三要素在本件里本来就没有（本件不是让路件；逐字原文见
   `scripts/verify/spec_bridge.py:283-284` 的两条 `bad.append`）。
   处置：本记录改以 `scripts/verify/spec_bridge.py:254-256`（三要素）与 `:278`（触发串）**指代**，
   修完判据⑦ 回到 `[OK]`。要根除这类误报，应由守卫那一侧把匹配限定在"声明性语句"上
   （`**` 不属本工区，本工区只登记）。


> **★ 转出说明（2026-09-27）**：本件组 2–6 的 37 条"补断言"**原封转出**到 `ninedim/06-变更/fc-2026-004-assertions/`，本件逐条勾上并注明"**已转出（不是已完成）**"。
> 为什么要转出：本件的 delta 已由 `4a4ab4e` 并入主规格 ⇒ 它**归档不了**（`archive --yes` 报 ADDED `already exists`）；
> 而放着 37 条未勾就 `--yes` 归档，等于**把没做完当做完**。转出后本件走 `archive --yes --skip-specs` 归档，断言在新件里继续跟。