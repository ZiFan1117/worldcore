# Tasks

> **坐标口径（2026-09-28 补，评审席建议项 ④ 的整改）**：本件正文里的 `path:line` 是**写下时的 as-of 坐标**（各条目正文注明了时点/提交），**权威定位子是"函数名／用例名／步骤名"**——它们**不随行号漂移**。
> **要复现某条证据**：先按函数名／用例名 `grep`（如 `grep -n "fn cli08_" scripts/test/cli.rs`），再读那一段；**不要照抄行号**。
> **为什么不逐处改成"命令＋步骤名"**：本件有 **80 处 `path:line`、涉及 63 行**，机械重写**风险高于收益**（改错一处就把真证据改坏）；而函数名／用例名在这些条目里**绝大多数本来就有**（评审席抽查 10 条，**全部能按函数名定位**）。**这是取舍，不是遗漏。**
> **来源**：`fc-2026-002-spec-revisions/tasks.md` 的组 2–6（34 条），逐条转出；**其中若干条在本件里被改写过**（`design.md` 自己写着 `3.3`／`3.4`「先重写再补」——★ 2026-09-28 订正：原写"未改判据"与实情矛盾）。
> **每条都必须有自己的变异证明**（"改坏哪一行 ⇒ 它变红"）；没有变异点的条目**不算完成**。


## 1. 接缝：`fc-2026-002` 转出到本件的「46 条对账表」（**未落笔，如实登记**）

- [x] 1.1 `fc-2026-002-spec-revisions/tasks.md` 的 `1.8` 逐字写着「把 46 条的**对账表**随本 change 一并提交——**★ 已转出**（**不是已完成**；去向 `fc-2026-004-assertions`）」，而**本件四个文件里 `对账表` 0 命中** ⇒ **它没有落点**（同一份 fc-002 的审计表逐字「| 1.8 | **未勾** | 46 条对账表**在本 change 目录里不存在**」）。
      **★ 已结账（2026-09-28，按签署人指示）**：本条验收给了**两条出路**，取**第二条**——**逐字写明"那张表不在本件、去向何处"**：`fc-2026-002` 的 `1.8` 要的是「46 条的**对账表**」，**而本件没有另立那张表**；它的**断言面**由**本件各条的「断言在哪／变异怎么变红」两栏逐条承担**（**断言类各条**都有这两栏；门禁／过程项——`4.8`／`5.6`／`6.1`–`6.8`——**不带变异栏**，各自另有验收读数；**条数现取**：`grep -c '变异怎么变红'`。**不必外引**）。
      **★ 一处口径订正（2026-09-28，评审席第十二轮指出）**：我上一版在这里写「34＋8＋4＝46」，**那是把两个量纲混了**——**46 条是 `fc-2026-001/audit.md` 的审计条目**（`fc-2026-002/design.md:7` 逐字「查出 **46 条语义差错**（严重 15／重要 12／一般 14／提示 5）」，行号形态 `^(C|E|G|L|P|R)\d+$`，见该件 `tasks.md:30`／`:180`），与"**本件 34 条断言任务**"**不是同一个量纲**；而 `fc-2026-002/design.md:134` 逐字说那 46 条里 **13 条**属"行为是真的、但没有任何断言为它变红"。⇒ 本件**不产出**那张 46 行表，且**它今天不存在于任何件**（`fc-2026-002/tasks.md:180` 逐字"46 条对账表**在本 change 目录里不存在**…命中 0 行"）；**要产出就另立件，以 `audit.md` 的 46 个编号为行**。**这条去向就是这句**——**不再用"8 条＋其余 4 条"去凑 46**。
  **验收**：要么在本件产出那份 46 条对账表（逐条给"断言 ↔ 实现 ↔ 变异点"），要么**逐字写明它不在本件范围、去向 X**——**不许用"已并入别处"掩盖"它其实不在那儿"**（skill §七）。
  **现状**：**未落笔**（本条由 2026-09-28 评审席判「不通过」的第三项暴露出来）。

## 2. 补断言 · 通道身份与信封（依 delta 的"需补断言"标注）

- [x] 2.1 在 `scripts/test/contract.rs` 的 `c14` 内补一条断言：`serve_once` 路径**不读对端凭证**（例如断言 `Listener` 的 `uid` 字段在受理路径上不参与判定）。**验收**：新增断言会随"受理层改为读对端凭证"的变异**变红**（先证会红）。
      **断言在哪**：`scripts/test/contract.rs:792`（判据 4 的夹具：把映射里的 `uid` 换成 `me+12345`）＋ `:808` 的 `.expect("受理路径不得读对端凭证：uid 对不上也必须受理（uid 只在 bind() 用）")`；非空夹具前提在 `:798`（`assert_ne!(alien.uid, me)`）。
      **变异怎么变红**：在 `src/channel.rs` 的 `serve_once` 里（`let mut out = stream;` 之后）插一句对端 uid 比对（读 `/proc/self/status`）。原始输出：`test c14_channel_takes_identity_from_kernel_not_from_request ... FAILED` ／ `panicked at tests/contract.rs:808: 受理路径不得读对端凭证：uid 对不上也必须受理（uid 只在 bind() 用）: "ext.world.Channel.Impersonation: 对端 uid 0 与本套接字身份 uid 12345 不符，拒绝"` ／ `MUT_RC=101`。

- [x] 2.2 在 `scripts/test/cli.rs` 补一条断言：`channel bind` 对**不在身份映射里**的套接字报 `ext.world.Channel.NotConfigured` 且 `rc=2`。**验收**：`cargo test --locked --test cli` 通过；变异（删掉 `None` 分支的拒绝）⇒ 变红。
      **★ 分清（2026-09-28 补，评审席建议项 ⑦）**：下面记的那次红**同时有两类原因**——① **变异造成的**：`NotConfigured` 那条不再报（这正是本条要证明的）；② **环境造成的**：报告尾部那句 `[FAIL] 通道目录 不可绕过检查未通过：所在目录 /tmp 的权限为 777` ——那是**我把账本/通道目录放在 `/tmp`** 触发了世界自己的静态墙（`/tmp` 是 777），**与变异无关**。⇒ **判"变异有没有打上"只看 ①**：`NotConfigured` 消失 ＋ 落到 `bind` 的另一条错上；② 只是伴随现象。

      **断言在哪**：`scripts/test/cli.rs:327`（`cli08_channel_bind_refuses_socket_not_in_identity_map`）＋ `:353` 的 `assert_eq!(code, 2, "不在身份映射里的套接字必须拒绝（rc=2）…")`、其后 `err.contains("ext.world.Channel.NotConfigured")` 与 `!unmapped.exists()`。
      **变异怎么变红**：把 `src/main.rs` 的 `cmd_channel` 里 `None` 分支的拒绝改成 `None => conf.listeners()[0].clone(),`。原始输出：`test cli08_channel_bind_refuses_socket_not_in_identity_map ... FAILED` ／ `panicked at tests/cli.rs:355: 拒绝理由必须点名错误码，读流水的人才能程序判定；stderr=[FAIL] 通道目录 不可绕过检查未通过：所在目录 /tmp 的权限为 777…`（`NotConfigured` 这句**没了**，落到了 `bind` 的另一条错上）／ `MUT_RC=101`。

- [x] 2.3 在 `scripts/test/contract.rs` 的 `c02` 内补一条**反假**断言：`field == "world"` 那一轮必须靠"报出字段名"之外的方式判真（例如断言错误串里 `MissingField` 之后紧邻的字段名 token 等于 `world`），使该轮不再是 `contains` 恒真。**验收**：把 `src/ontology.rs:32` 的 `{field}` 删掉 ⇒ 该断言变红。
      **断言在哪**：`scripts/test/contract.rs:105`（`fn named_field_in`：定位「缺少必填字段 \`<名字>\`」的反引号之间）＋ `:147` 的 `assert_eq!(named_field_in(&msg), field, …)`；反假对照在 `:154-174`（删 `seq` 时错误串**照样**含 `world`，因为码前缀 `ext.world.` 自带它 ⇒ `contains("world")` 恒真）。
      **变异怎么变红**：把 `src/ontology.rs` 的 `MissingField` 显示串里 `` `{field}` `` 删掉（现文件 `:56`，任务原写 `:32` 是旧行号）。原始输出：`test c02_every_required_envelope_field_is_enforced ... FAILED` ／ `panicked at tests/contract.rs:109:28`（`named_field_in` 的"没有点名缺失字段的标记"分支）／ `MUT_RC=101`。

- [x] 2.4 在 `scripts/test/acceptance.rs` 的 `t5` 内补"状态未被改动"的断言（照同文件 `:87-92` 的既有写法读回读模型比对）。**验收**：`cargo test --locked --test acceptance -- t5_` 通过；变异（让被拒事件仍落笔）⇒ 变红。
      **断言在哪**：`scripts/test/acceptance.rs:250`（快照取自**两次被拒之前**）＋ `:267-278`（`s.get("world://notice/n","muted") == None`、`s.seen() == 0`、`assert_eq!(before, s.to_json().to_string(), "被拒的提交不得改动状态（逐字节比对，不是只看条数）")`）；正控在 `:300-310`。
      **变异怎么变红**：在 `src/lib.rs` 的 `commit_verbatim` 里，让本体校验失败的事件**仍落笔**（`if let Err(e) = self.ontology.validate(&ev) { let _ = self.ledger.append(ev.clone()); return Err(e.to_string()); }`）。原始输出：`test t5_law_rejects_and_does_not_write ... FAILED` ／ `panicked at tests/acceptance.rs:267: called Result::unwrap() on an Err value: "ext.world.ReadModel.UnknownKind: 未知事件家族 \`bogus\`（seq=1）…"`（被拒的那条真进了账本 ⇒ 读模型拒绝折叠）／ `MUT_RC=101`。

- [x] 2.5 为"策略文件缺失"与"本体软链"各补一条断言（放入 `c03`/`c09` 或新增用例）。**验收**：两类各有一条会红的断言；`scripts/test/system_acceptance.sh --self-test` rc=0 不变。
      **断言在哪**：`scripts/test/contract.rs:247`（`c03` 第 ⑥ 类）＋ `:250` 的 `assert!(e.contains("无法读取") && e.contains("no-such-policy.json"), …)`；② 本体软链 ⇒ `scripts/test/contract.rs:490`（`c09` 内：`World::open(&ont_link, …).expect_err("指向别处的本体软链必须被拒绝")` ＋ 理由含「符号链接」「本体」），真实文件对照在 `:495-500`。
      **变异怎么变红**：① 把 `src/gate.rs` 的 `Policy::load` 读文件失败吞掉（`.map_err(...)?` ⇒ `.unwrap_or_else(|_| "{}".to_string())`）⇒ 原始输出 `panicked at tests/contract.rs:249: 策略文件缺失必须报「无法读取 <路径>」，实得: 门禁策略缺少 \`policy\` 版本号`；② 删掉 `src/ontology.rs` 里 `crate::guard::assert_not_other_writable(path, "本体（法律·形状）")?;` 那一行 ⇒ 原始输出 `panicked at tests/contract.rs:490: 指向别处的本体软链必须被拒绝: World { … }`（软链本体竟然开起来了）。两条都 `MUT_RC=101`。
      **另**：`bash tools/system_acceptance.sh --self-test` 在本工区改动前后均 `rc=0`（本工区只改 `tests/**`，不动该脚本）。

- [x] 2.6 为"已知无码出口"补断言：静态墙三条（符号链接／mode 位／属主）与策略版本不符，各自断言错误串**不含** `ext.world.` 前缀。**验收**：断言存在且当前为绿（它们固定的是边界，不是缺陷）；若某出口**确实**带码，该断言变红并据此改规格。
      **断言在哪**：`scripts/test/contract.rs:1472`（新用例 `c24_known_codeless_outlets_carry_no_ext_world_prefix`）＋ `:1521` 的 `assert!(!has_code(msg), "{what} 今天**不带** \`ext.world.\` 码…")` 与 `:1527` 的 `assert!(!msg.contains("ext.world."))`；同用例 `:1544-1546` 是带码出口的**对照**（防"什么都判成无码"）。
      **变异怎么变红**：给「策略版本不符」这条出口加上码（`"门禁策略版本不支持：…"` ⇒ `"ext.world.Gate.BadVersion: 门禁策略版本不支持：…"`）。原始输出：`panicked at tests/contract.rs:1521: ④ 策略版本不符 今天**不带** \`ext.world.\` 码（已知无码出口，任务 2.6）…实得：ext.world.Gate.BadVersion: 门禁策略版本不支持：期望 1，实得 2…` —— **红的正是 ④**，①②③ 仍绿（三条出口没被这次变异碰到）／ `MUT_RC=101`。

- [x] 2.7 为 `c15` 补一条**账本路径**的错误码断言（今天 `c15` 的七条来源无一条是账本路径），并把该用例纳入出厂可跑的路径。**验收**：新增断言指向 `scripts/test/cli.rs:155` 同族的账本码；且在 `check.sh.new` 里**有一条会跑到它**（见 6.2 的步骤归属订正）。
      **断言在哪**：`scripts/test/contract.rs:841`（`c15`，来源由 7 条增至 9 条）—— ⑧ 缺号账本在 `:922`＋`:923` 的 `assert_eq!(code_of(&gap_err), Some("ext.world.Ledger.SeqGap"), …)`；⑨ 无链账本在 `:939`＋`:940-943` 的 `assert_eq!(code_of(&noc), Some("ext.world.Ledger.NoChain"), "…（与 tests/cli.rs:155 同码）…")`；聚合判据在 `:962-969`（账本域至少两个码）。
      **变异怎么变红**：把 `src/ledger.rs` 里 `ext.world.Ledger.SeqGap` 那句的码去掉（改成「账本缺号：…」）。原始输出：`panicked at tests/contract.rs:923: assertion left == right failed: 缺号账本必须报账本域的点名码，实得: 账本缺号：第 2 行 seq=3，期望 2` ／ `left: None` ／ `right: Some("ext.world.Ledger.SeqGap")` ／ `MUT_RC=101`。
      **出厂路径**：`check.sh.new:119` 的**步骤 ③b** 跑的是整个 `cargo test --locked --test contract`（无过滤器）⇒ `c15` 在内（本工区不新增步骤号）。

## 3. 补断言 · 门禁（含两条 P0 边界）

- [x] 3.1 补一条断言：`world://user`（出厂 `irreversible_actors` 的唯一成员）执行不可逆能力（`ledger.compact`）⇒ **放行**（账本里**不出现**任何 `gate.*` 通告），且那条 `act` 事件**必带** `gate.friction:<等级>` 旗标——等级取自载体清单 `cap.d/ledger.compact.json` 的 `risk`（出厂为 `high`）。**验收**：断言当前为绿；变异（让白名单主体也走 `AwaitApproval`）⇒ 变红。出处：`src/gate.rs` 的 `Friction`／`Policy::verdict`（摩擦挂在**动作的不可逆等级**上）；`ninedim/01-意图环/01-策划/WC-THEORY-DEFECT-001-v0.2.md:55`（`D-20`）。 〔该件已按作者指示退场；解析根＝`git show bf2eae7:<原路径>`〕
      **断言在哪**：`scripts/test/cli.rs:389`（`cli09_whitelisted_actor_may_run_irreversible_and_the_event_carries_friction`，走**真实二进制 ＋ 真实账本文件**）＋ `:410` 的 `assert_eq!(code, 0, "白名单主体执行不可逆动作必须**放行**…")`、`:428` 的 `assert_eq!(lines.len(), 1, "① 放行 ⇒ 账本里只该有那一条 act…")`、`:444` 的 `assert!(flags.iter().any(|f| f == &want_flag), "② …**必带**摩擦旗标…")`（`want_flag` 由 `cap.d/ledger.compact.json` 的 `risk` 在 `:424` 现算）。
      **变异怎么变红**：把 `src/gate.rs` 的 `decide` 里那条白名单放行改成 `if false`（白名单主体也走 `AwaitApproval`）。原始输出：`panicked at tests/cli.rs:410: assertion left == right failed: 白名单主体执行不可逆动作必须**放行**（v1 无审批通道，否则该能力是死号）；stderr=[FAIL] ext.world.Gate.AwaitingApproval: 门禁加摩擦：能力 \`ledger.compact\` **不可逆**（verb=do；载体清单声明的风险等级：high），而 \`world://user\` 不在 irreversible_actors 白名单内。` ／ `left: 2` ／ `right: 0` ／ `MUT_RC=101`。

- [x] 3.2 补一条断言：保留前缀通告被拒**那条路径**写下的流水也带 `refused`（`fnv1a64:` 前缀）指纹——今天只有不可逆加摩擦路径有该断言（`c23_gate_notice_says_what_it_refused` 走的是 `:1167` 的 `gate.awaiting-approval`）。**验收**：断言存在且会红（删掉 `refused` 字段即红）。
      **断言在哪**：`scripts/test/contract.rs:1290` 的 `c23_notice_with_reserved_prefix_is_refused_for_outsiders` **判据③**（`:1321-1336`）：从账本里找出 `gate.notice-not-allowed` 那条流水，断言 `payload.refused` 以 `fnv1a64:` 开头、`payload.refused_subject == "world://user"`，并在 `:1338-1360` 复算第二次尝试的指纹必须**相同**。
      **变异怎么变红**：删掉 `src/lib.rs` 的 `record_gate_notice` 里 `"refused": refused,` 那一行。原始输出：`test c23_notice_with_reserved_prefix_is_refused_for_outsiders ... FAILED` ／ `panicked at tests/contract.rs:1327`（`.expect("保留前缀拒绝流水同样必须带 \`refused\` 字段（D-14）")`）／ `MUT_RC=101`。

- [x] 3.3 **重写后**：断言 `risk` 的**实际角色**——它**不**单独决定放行/拒绝（那由 `reversible` 与 `irreversible_actors` 裁决），但**决定摩擦的轻重与拒绝流水里的等级**（`gate.friction:low/medium/high/unlisted`）。
      **为什么不是原措辞**：原条目写「`risk` 不参与门禁裁决」，而实现已改为"参与摩擦、不参与放行"（`gate.rs:574-582`）；照搬会写成一条与实现相反的断言。
      **验收**：断言存在且会红（变异：把 `:544` 的 `level` 换成常量 ⇒ 变红）
      **断言在哪**：`scripts/test/atom_reversibility.rs:351`（`a06_risk_sets_friction_weight_but_not_the_verdict`，判别性夹具：`notice.mute` 可逆+low ／ `ledger.compact` 不可逆+low ／ `world.migrate` 不可逆+high）——「摩擦轻重由 risk 定」在 `:382`／`:400`／`:410`，「risk 相同而结论相反」在 `:386-393`，「reversible 相同而等级不同」在 `:438`／`:443`（且各自断言**不含**对方的等级），等级落进账本在 `:458`／`:466`／`:476`。
      **变异怎么变红**：把 `src/gate.rs` 的 `decide` 里 `level = self.level_name(c)` 换成 `level = "常量"`（现文件 `:546`，任务原写 `:544`）。原始输出：`panicked at tests/atom_reversibility.rs:438: 实得：能力 \`ledger.compact\` **不可逆**（verb=do；载体清单声明的风险等级：常量），而 \`world://agent/1\` 不在 irreversible_actors 白名单内。` ／ `MUT_RC=101`。

- [x] 3.4 断言**载体撤销点（`undo: before-each`）不参与互校**、也不被当作世界可逆的依据（`src/carrier/mod.rs:32`；互校的载体侧由 `risk`/`confirm` 导出）。
      **验收**：断言存在且会红（变异：把 `gate.rs:270` 的判据换成读 `undo` ⇒ 变红）
      **断言在哪**：`scripts/test/atom_reversibility.rs:511`（`a07_carrier_undo_is_neither_cross_checked_nor_a_proof_of_world_reversibility`）—— 两份清单**只差 `undo`**（`before-each` / `never`），断言：`:539` 夹具 A 的 `undo` 字段、`:541` 夹具 B 的、`:543` 两者**确实不同**（防"两份其实一样"）、`:534` 两份**都能启动**、`:554`／`:560` 两份给出的 `risk`／`decision`／`friction` **完全相同**（世界可不可逆由 `policy.json` 说了算）。
      **变异怎么变红**：把 `src/gate.rs` 的 `cross_check_reversibility` 判据从 `risk`/`confirm` 换成读 `undo`（`let carrier_says_reversible = m.undo == crate::carrier::capd::Undo::BeforeEach;`，现文件 `:272`，任务原写 `:270`）。原始输出：`panicked at tests/atom_reversibility.rs:537: 世界侧可逆 + 载体侧不留撤销点 ⇒ 同样必须能启动: "ext.world.Gate.ReversibilityMismatch: 出厂配置**两处对不上**，拒绝启动。… 能力 \`job.start\`：… 载体侧（…job.start.json）声明 risk=low、confirm=never⇒ 推出载体侧不可逆。…"` ／ `MUT_RC=101`。

- [x] 3.5 为"门禁不可绕过的未做部分"（祖先链遍历、通道层、Landlock 自缚）在本 change 的 `review.md` R5 节写明**不可机核、由评审签字承担**。**验收**：`review.md`（由人填）里有该声明；本组不产出测试。
      **★ 已结账（2026-09-28，按签署人指示）**：本条验收逐字要求「`review.md`（**由人填**）里有该声明」——**已满足**：`review.md` 的 **§5.1** 三行齐（祖先链遍历／通道层／Landlock 自缚：各给"为什么不可机核"＋"由本档签字承担"），且该件**已由 `ZiFan` 于 `2026-09-28` 签署**（`8fc243c`，四处同填）。
      **未做（截至本工区交件时点，如实登记）**：`ninedim/06-变更/fc-2026-004-assertions/review.md` **尚不存在**——`openspec status --change fc-2026-004-assertions` 现文逐字 `[ ] review`。**缺的就是它**：三句话（祖先链遍历／通道层／Landlock 自缚各一句「不可机核、由评审签字承担」）写进 `review.md` 的 R5 节后本条才可勾。该件**由人备料与签署**（本仓口径：签字只在评审通过后、按作者指示落笔），本工区**不代建、不代签**。**★ 现值（2026-09-28）**：该状态已改变——`review.md` **已在**，且已由 `ZiFan` 签署（`8fc243c`，四处同填）；本条**已勾**。**上面那段是"当时"的登记。**


      **★ 订正（2026-09-28，评审席裁定后；与 `5.6` **同法**——上一轮只改了 `5.6`、漏了本条，这是同一轮里的第二例）**：原文那句「**不代建、不代签**」**理由不成立**——评审席查了仓内既有做法：`archive/2026-09-28-fc-2026-002-spec-revisions/review.md` **正是 agent 在 `2669173` 建的**，其正文逐字「**本件先由执行者备料，结论栏留人**」／「**本档由谁备料** | 执行者（AI）；**评审与批准均为人的职责**」。
      ⇒ 正确口径：**备料可做**（建 `review.md`、把三句话说全），**判定与签署不可替**（批准人与结论留空，等人）。（**当时**）**保持未勾是对的**（本条验收逐字写着"由人填"）。**★ 现值（2026-09-28）：已由签署人勾**（见本条上方的「★ 已结账」）。
      ⇒ **并且它不是归档前置**：前置是 `review.md` **这份件**（守卫判据① 只对**归档目录**查它）。
## 4. 补断言 · 账本与证据链

> **读数环境（2026-09-28）**：主机无 Rust 工具链，全部读数取自 VM `world`（Arch Linux，cargo 1.98.1）的**隔离树** `/root/wc-b` ＝ `git archive HEAD`（`05a1acd`）＋本工区测试补丁（工作区当时正被并行工区改 `src/**` 与**同一批** `tests/**`，直测会拿到别人的半成品污染过的读数）；变异在 `/tmp/mut-b` 副本上做。基线：`cargo test --locked --test contract` ＝ `29 passed; 0 failed; 1 ignored`（rc=0）、`--test cli` ＝ `12 passed`（rc=0）、`--test acceptance` ＝ `17 passed`（rc=0）。
> **工作区坐标（2026-09-28 补测：第二个坐标，防「只在我挑的树上成立」）**：整树同步后在 VM `/root/world` 上跑同三条命令 ⇒ `--test contract` ＝ `30 passed; 0 failed; 1 ignored`（rc=0）、`--test cli` ＝ `14 passed`（rc=0）、`--test acceptance` ＝ `17 passed`（rc=0）；`cargo test --locked --test contract -- --ignored c29_` ⇒ `FAILED. 0 passed; 1 failed`（rc=101，`panicked at tests/contract.rs:1633`）。⇒ 隔离树与工作区**两个坐标结论一致**（隔离树 `c29` 的 panic 在 `tests/contract.rs:1283`，是同一断言在两棵树里的不同行号）。

- [x] 4.1 补一条断言：在**无链（v1）账本**上做一次合法 `append` 后，账本**仍可被打开**（即 `K-3` 的修复判据）。**验收**：该断言当前**必然为红**（`src/ledger.rs:506` 的 `chained` 只读不用）⇒ 连同修复一起另立 change；断言先写、先证红。
      - **断言**：`scripts/test/contract.rs:1613`（`fn c29_k3_chainless_ledger_survives_one_legal_append`；取 **`#[ignore]` ＋ 理由** 形态，判据**原样留着**）。**变异（反向：按 `K-3` 的修复形状改）**：`src/ledger.rs` 的加链改成「只有 `chained` 账本才加」⇒ `cargo test --locked --test contract -- --ignored c29_` 由 `FAILED. 0 passed; 1 failed`（rc=101）转 `ok. 1 passed`（rc=0）；恢复后复红（rc=101）。
        **基线红的原始输出**：`panicked at tests/contract.rs:1283:9: K-3 未修：无链账本做一次合法 append 之后，账本**仍应可被打开**；实得拒绝：ext.world.Ledger.MixedChain: 部分事件有 `chain`、部分没有——…拒绝使用`

- [x] 4.2 补一条断言固定 `K-3` 的**当下边界**：无链账本 + 一次合法 `append` ⇒ 下次打开报 `MixedChain`。**验收**：断言存在且在修复落地前为绿（证明边界形状）。
      - **断言**：`scripts/test/contract.rs:1647`（`fn c30_k3_boundary_chainless_ledger_plus_one_append_reports_mixed_chain`）。**变异**：`src/ledger.rs` 的混用判定 `if !has.iter().all(|b| *b)` 前加 `false &&` ⇒ `--test contract -- c30_` rc=101（`FAILED. 0 passed; 1 failed`，`panicked at tests/contract.rs:1323`）；恢复后 rc=0（`ok. 1 passed`）。

- [x] 4.3 补一条断言：`c21` 的"无链账本仍能打开"**只到只读为止**——即断言打开后**写入会失败**（与 4.2 同一形态的另一侧）。**验收**：断言存在；出处 `scripts/test/contract.rs` 的 **`fn c21_is_chained_reflects_reality`**（★ 订正：原写 `:1026`——那里落在 **`fn c16_chain_detects_local_tampering`** 里，**是指错了用例、不是行号漂移**）。
      - **断言**：`scripts/test/contract.rs:1688`（`fn c31_chainless_ledger_opens_readonly_and_refuses_writes`）。**变异**：`src/ledger.rs` 的 `open_readonly` 内部改回 `OpenMode::ReadWrite` ⇒ `--test contract -- c31_` rc=101（`panicked at tests/contract.rs:1349`）；恢复后 rc=0。

- [x] 4.4 把 `t1` 的"逐字段一致"补全：逐个断言 `actor`／`id`／`at`／`flags`／`body.subject`／`body.path`／`body.after`（今天只比 `len`／`seq`／`world`／`kind`／`body.before`）。**验收**：新增断言 ≥ 7 条；变异（改 `src/event.rs` 的某个字段构造）⇒ 至少一条变红。
      - **断言**：`scripts/test/acceptance.rs:82`（`t1` 内新增 **12 条** `assert*!` 语句（现算：`grep -c '^\s*assert'` 该块 ＝ 12），覆盖 `actor`×3／`id`×3／`at`／`flags`／`body.subject`×2／`body.path`／`body.after`；其中 `id`／`at`／`flags` 三条在循环里对每条事件各执行一次）。**变异**：`src/event.rs` 的 `json!(actor)` 改成常量 `"world://user"` ⇒ `--test acceptance -- t1_` rc=101（`panicked at tests/acceptance.rs:89`）；恢复后 rc=0。

- [x] 4.5 把 `t2` 的证据层级修正为**真跨进程**：把"新进程"这一层挂到 `scripts/test/s1_sys_probe2.sh` 的 `TC-070`（`:379-383`，由 `check.sh.new:145` 执行），并在 `t2` 的文档注里写明它是同进程 drop + reopen。**验收**：`bash tools/s1_sys_probe2.sh` 通过；`t2` 的注释与规格一致。
      - **落点**：`scripts/test/acceptance.rs:157`（`t2` 的文档注：写明它是**同进程** `drop` ＋ `reopen`，真跨进程那一层挂到 `TC-070`；**刻意不写行号**——任务书给的两处行号实测都对不上）。**承担者**：`scripts/test/s1_sys_probe2.sh` 的 `TC-070`（`REQ-F-022`：① 两次**独立进程**读回逐字节相同 ② 条数＝账本行数 ③ `seq` 无缺号）。**验收读数**：`bash tools/s1_sys_probe2.sh` **rc=0**（`== 汇总：断言通过 117 项，断言失败 0 项；另行**登记**（现状为红、如实记录）2 项 ==`、`== 结论：断言全通过（TC-053 – TC-076 端到端）==`）。**变异**：`src/main.rs` 的 `cmd_read` 每行尾部加 `#pid=<本进程 pid>` ⇒ TC-070 ① 变红；恢复后 ①②③ 复绿、rc=0。⚠ 首次变异**假绿**：漏了 `cargo build`（探针跑的是**已构建**的二进制）⇒ 读的是旧二进制；补上构建即红——这正是「假证形态①：脚本根本没跑」的实例，故记在这里。
      **★ 行号订正（2026-09-28，断言工区 B 实测）**：`TC-070` 在 `scripts/test/s1_sys_probe2.sh:413-422`（原写 `:379-383` 落在 `TC-067` 里），由 `check.sh.new:161`（**步骤 ⑦**）执行（原写 `:145` 是步骤 ⑥ 的注释行）。⇒ **引用写"命令 ＋ 步骤名 或 函数名/用例名"**；**确需行号时，必须同时给出函数名／用例名并注明时点**（行号只作参考，**会烂**——本件已有 1–8 行的漂移实测；★ 2026-09-28 按实修正：原写"一律不写行号"，而同件 2.1–5.5 实际有 80 处，**原措辞与实情不符**）。
- [x] 4.6 补一条断言固定"截到最后一个 `\n`"这条边界：末行是**完整合法 JSON 但缺末尾换行** ⇒ 被截掉且 `seq` 被复用。**验收**：断言存在且为绿；出处 `src/ledger.rs:276-289` 与实现自述 `:385`。
      - **断言**：`scripts/test/contract.rs:1728`（`fn c32_last_line_without_trailing_newline_is_cut_and_seq_is_reused`）。**变异**：`src/ledger.rs` 的 `keep` 从「最后一个换行之后」改成 `raw.len()` ⇒ `--test contract -- c32_` rc=101（`panicked at tests/contract.rs:1418`）；恢复后 rc=0。

- [x] 4.7 补一条断言固定单写者锁的**反向失效**：pid 号被复用时持有者已不存在却不会被回收。**验收**：断言存在（若不便构造，则在本 change 的 `review.md` R5 节登记为"不可机核"）；出处 `src/ledger.rs:182-184`。
      - **断言**：`scripts/test/contract.rs:1830`（`fn c33_stale_lock_with_a_reused_live_pid_is_never_reclaimed`；含正控：**已结束子进程**的 pid ⇒ 陈锁必须被回收）。**变异**：`src/ledger.rs` 的 `alive` 恒 `false` ⇒ `--test contract -- c33_` rc=101（`panicked at tests/contract.rs:1498`）；恢复后 rc=0。

- [x] 4.8 **证据链机械门禁 —— 已由 `spec_bridge.py` 判据② 承担**（2026-09-28 核）
      **实测**：`def j2_evidence`（`scripts/verify/spec_bridge.py:165`）扫 `ninedim/01-意图环/04-规格/**` **＋ 所有 delta**（`ninedim/06-变更/**/specs/**/spec.md`），判"证据行的 token 必须指向真实存在的函数/脚本"；
      `spec_bridge.py --self-test` 里两条反例逐字：`反例②a（**主规格**证据函数不存在 => 判据② 应红）：已红 OK`、`反例②b（**delta** 证据行指向不存在的函数 => 判据② 应红）：已红 OK` ⇒ **"改一个测试名 ⇒ 规格变红"当天即成立，"先证会红"亦有反例**。
      **★ 订正**：本条原引「`design.md` §排除清单第 7 条」——**该条不存在**（该节只有 2 条：不改 `src/**` 行为／不动书与规格），系**假引用**（由断言工区 B 实测发现，执行者复核成立）。**故本条不是"范围外而搁置"，而是"已由判据② 承担"。**
      **验收**：`python scripts/verify/spec_bridge.py --self-test` ⇒ rc=0 且含上列两条反例；`spec_bridge.py` 正跑判据② **[OK]**。

- [x] 5.1 补一条断言固定 `project check` 的**判据只剩头部四项**：让两份投影在内容上不一致（一方少渲一半主体）而头部四项相同 ⇒ 命令**仍然报绿**。**验收**：断言存在且为绿（它固定的是边界）；出处 `src/project/mod.rs` 的 `assert_same_source`。
      - **断言**：`scripts/test/cli.rs:495`（`fn cli13_project_check_criterion_reads_only_the_header`）。**变异**：`src/project/mod.rs` 的 `assert_same_source` 增加「正文行数必须相同」⇒ `--test cli -- cli13_` rc=101（`panicked at tests/cli.rs:361`）；恢复后 rc=0。
      **断言在哪**：`scripts/test/cli.rs:495`（`cli13_project_check_criterion_reads_only_the_header`）——正文取自命令自己的 `project language` 输出、砍掉一半主体行、头部一字不动 ⇒ `assert_same_source(&a,&b).is_ok()`；另配正控（改 `state=` ⇒ 必报「状态不同」）。
      **变异怎么变红**：在 `src/project/mod.rs` 的 `assert_same_source` 里加一条正文/行数比较 ⇒ 该用例变红。
      **★ 本条曾被我误删**：执行者在 `26fcd6a` 改 4.8 时把它连同相邻行一起吃掉，由断言工区 A 发现（"`tasks.md` 的 5.1 不见了"），**现按 `2669173` 的原文逐字恢复**——删条目与删代码一样是损坏，**必须留痕**。
- [x] 5.2 补一条断言固定"三个不等分支在命令路径上不可达"：断言 `project check` 的两份投影取自同一 `state` 与同一 `vocab`。**验收**：断言存在；出处 `src/main.rs:408-410`。
      - **断言**：`scripts/test/cli.rs:552`（`fn cli14_project_check_feeds_both_projections_the_same_state_and_vocab`）。**变异**：`src/main.rs` 的 `project visual` 喂假 `vocab` ⇒ `--test cli -- cli14_` rc=101（`panicked at tests/cli.rs:402`）；恢复后 rc=0。

- [x] 5.3 补一条断言：`Checkpoint::FORMAT` 版本不符 ⇒ 报 `ext.world.Checkpoint.BadFormat`（今天该分支零断言）。**验收**：断言存在且会红（删掉 `src/checkpoint.rs:94-99` 的判定即红）。
      - **断言**：`scripts/test/cli.rs:638`（`fn cli16_checkpoint_format_mismatch_is_named`）。**变异**：`src/checkpoint.rs` 的版本判定 `if fmt != Self::FORMAT` 前加 `false &&` ⇒ `--test cli -- cli16_` rc=101（`panicked at tests/cli.rs:505`）；恢复后 rc=0。

- [x] 5.4 补一条断言固定"CLI 的 `checkpoint resume` 走未核验续算路径、由事后比对兜底"：篡改快照内容 ⇒ 若续算与全量不一致则报 `ResumeMismatch` 且 `rc=2`。**验收**：断言存在；出处 `src/main.rs:556-562`。
      - **断言**：`scripts/test/cli.rs:698`（`fn cli17_checkpoint_resume_falls_back_to_post_hoc_comparison`；三段：正控／只改 `digest` ⇒ `verify` 红而 `resume` **绿**（证明它**不核验**）／只改 `state` ⇒ `verify` **绿**而 `resume` 报 `ResumeMismatch`（证明**事后比对**兜底））。**变异**：`src/main.rs` 的事后比对 `if fast.to_json() != full.to_json()` 前加 `false &&` ⇒ `--test cli -- cli17_` rc=101（`panicked at tests/cli.rs:602`）；恢复后 rc=0。

- [x] 5.5 补一条断言：CLI 用法串里列出 `checkpoint write|verify|resume` 三条子命令。**验收**：断言存在；出处 `src/main.rs:28-30` 与 `:153`。
      - **断言**：`scripts/test/cli.rs:610`（`fn cli15_usage_lists_three_checkpoint_subcommands`）。**变异**：删掉 `src/main.rs` USAGE 里的 `checkpoint resume <path>` 那一行 ⇒ `--test cli -- cli15_` rc=101（`panicked at tests/cli.rs:453`）；恢复后 rc=0。

- [x] 5.6 **待人填**（作者／评审席）：为 `REQ-N-008`（带检查点续算 ≤ 全量重算的 1/2）在 `fc-2026-004-assertions` 的 `review.md` R5 节登记为**范围外、未实现、无断言**。
      **★ 已结账（2026-09-28，按签署人指示）**：本条验收逐字要求「`review.md`（由人填）里有该**范围外**声明」——**已满足**：`review.md` 的 **§5.2** 已把 `REQ-N-008` 登记为**范围外 · 未实现 · 无断言**（并写明"不得被读成已实现/已达标"）。
      **★ 订正（2026-09-28）**：本条原文自己写着「`review.md`（**由人填**）」——而该 change 目录下**没有 `review.md`**（只有 `.openspec.yaml`／`design.md`／`proposal.md`／`tasks.md`），且评审记录按本仓口径**由人备料与签署**。
      **★ 再订正（2026-09-28，评审席裁定后）**：原文那句「**不代建、不代签**」**理由不成立**——评审席查了仓内既有做法：`archive/2026-09-28-fc-2026-002-spec-revisions/review.md` **正是 agent 在 `2669173` 建的**，其正文逐字「**本件先由执行者备料，结论栏留人**」／「**本档由谁备料** | 执行者（AI）；**评审与批准均为人的职责**」。
      ⇒ 正确口径是：**备料可做**（建 `review.md`、把三句话说全、把 `REQ-N-008` 登记进去），**判定与签署不可替**（批准人与结论留空，等人）。（**当时**）**保持未勾是对的**——两条的验收逐字都写着"由人填"。**★ 现值（2026-09-28）：已由签署人勾**（见上方「★ 已结账」）。
      ⇒ **并且它们不是归档前置**：前置是 `review.md` **这份件**（守卫判据① 只对**归档目录**查它）。
      ⇒ **它不是 agent 能完成的活**：（**当时**）**保持未勾**，等人在 `review.md` 落笔后由签署人勾。**不许代填。** **★ 现值（2026-09-28）：人已在 `review.md` 落笔（`ZiFan`，`8fc243c`）⇒ 本条已由签署人勾。**

## 5. 补断言 · 投影与读模型（★ 2026-09-28 补标题：原缺，5.1–5.6 六条实际落在 `## 4.` 名下，按组做机器统计会记错组）

（本组六条见下，逐条为"补断言"；组号以条目号为准。）

## 6. 验证与取证（跨组的整体验收）

- [x] 6.1 **形态门禁（归档面）**——**原命令已失效，口径已改**：原条目跑 `openspec validate fc-2026-002-spec-revisions --strict`，而**该 change 已于 2026-09-28 归档** ⇒ 改验归档面。**实测（2026-09-28 01:37，HEAD `75dc0d6`）**：
      ```
      openspec validate --archived
        ✓ change/2026-09-27-baseline-verified-doctrine
        ✓ change/2026-09-28-fc-2026-002-spec-revisions
        Totals: 2 passed, 0 failed (2 items)
      ```
      ⇒ **rc=0，两项全过**。
      **★ 2026-09-28 订正（评审席第十一轮真跑 `openspec archive` 后）**：那是**当时**（本件尚未归档）的读数。
      归档后 `validate --archived` 会变 **4 items**，而**本件必须 tasks 全勾**才不红——
      仓内口径逐字（`ninedim/records/openspec-流程件/schemas/opsx-swe-gb/schema.yaml:127`）：「**归档门禁要求 tasks 全勾。** 若某条本来就做不完（常设维护项），
      **不要留在本件里**：它在 `tasks.md` 里会**永久挡住** `openspec validate --archived`。」
      ⇒ 本件归档前已把三条（`1.1`／`3.5`／`5.6`）**逐条结账**（各自的验收已满足，或按验收自带的第二出路**逐字写明去向**），
      **留痕不静默**（照 `fc-2026-001` 的先例）。**归档后的目标读数：`4 passed, 0 failed`，rc=0。**

- [x] 6.2 **产物链状态——命令已失效，口径已改（留痕）**：原命令 `openspec status --change fc-2026-002-spec-revisions` 在该 change 归档后**必然 rc=1**（实测逐字）：
      ```
      × Error: Change 'fc-2026-002-spec-revisions' not found. Available changes:
        cover-unimplemented-capabilities / fc-2026-001-openspec-into-cm / fc-2026-003-doc-consolidation / fc-2026-004-assertions
      ```
      **这不是缺陷**：归档后的 change 不再出现在"在册 change"里。⇒ 该条的验收面**改由 6.1 的归档面覆盖**（`validate --archived` 已含它）。**原命令与改判都逐字留在这里，不许悄悄换判据。**

- [x] 6.3 **不越界取证**：实测 `git status --short -uall` ⇒ **输出为空**（工作区干净、全部已入库）。
      ⇒ **★ 订正（2026-09-28，评审席第二、三轮各判一次后）**：本句原写「**本 change 没有把任何越界改动留在树里**；`ninedim/01-意图环/04-规格/**` 零改动」——**那是假话**。**双坐标（按本仓口径 = 当时 ＋ 现在）**：
      · **当时**（写下本句时，`75dc0d6`）：**成立**——那一刻 `ninedim/01-意图环/04-规格/**` 确实零改动；
      · **现在**：**不成立**——本 change 后来动了主规格的**两处能力**：`ledger-integrity`（`0a77d26`）与 `read-model`（`3ba916f` 起）。**逐提交清单以 `git log --all -- specs` 为准，本处不复述次数**（★ 本处曾写"两次"，在第三轮提交里过期了）。两处的**让路三要素**见 `design.md` 的「**两处**让路登记」。⇒ **结论**：本句只对"当时"成立，**不许被引用为"本 change 未越界"**。
      **时点**：2026-09-28 01:37，HEAD `75dc0d6`。

- [x] 6.4 **出厂判据强度——原验收写 `rc=0`，已按实改成"唯一红项不是本 change 引起"**：
      **★ 订正（2026-09-28，评审席实测后）**：本条原写「`CHECK_RC=1`、25 个 ✅、唯一 ❌ 是第 ⑨ 步」——**那次实测是 `CHECK_RC=0`、41 个 ✅、0 个 ❌、12 步全过**（★ 那是**当时的**读数，**本处只记当时值**——★ 2026-09-28 再订正（评审席第三轮）：本处曾写"现在实测 `43 ✅`／`13 步`"，**那两个数在我写下它们的那一笔提交里就过期了**（`③c` 的日志形态一改，`✅` 行数就变）⇒ 按评审席的方子，**本处不再写任何计数**：**`bash check.sh` 的输出为准**（⚠ **步数、`✅` 数、`❌` 数一律现取**，写死就会烂））（那条真源码环 `M04↔M09` 在本条写下后 **4 分钟**由 `746dff2` 关掉）。⇒ **判据改成"以 `bash check.sh` 的输出为准，本处不复述读数"**，并把当时的读数按双坐标留档如下（它当时是真读数）：
      · **当时**（写下本条时）：`CHECK_RC=1`，**25 个 ✅**，**唯一 ❌ 是第 ⑨ 步机核层守卫**（逐字 `❌ 机核层守卫（WC-ATOM-001 §四：单意图／四件同夹／deps==import 且无环） 失败（rc=1）`），而该步自己的读数是 **`通过 2 / 失败 1`**——那**唯一一条红是真源码环 `M04↔M09`**（在册真缺陷，方案与反例已备）。
      **★ 为什么不写 rc=0**：写了就是"把没做到写成做到了"。**（原判据，已作废，留痕）**：rc=1 **且**逐条核对唯一红项**不是本 change 引起**——它在"第 ⑨ 步仍红"那个时点上是成立的；★ 2026-09-28：**该判据已作废**（⑨ 已转绿、`check.sh` 已 `rc=0`），现行判据见上一条订正（"**以 `bash check.sh` 的输出为准，本处不复述读数**"）。**留此句只为留痕，不得作为现行判据引用。**

- [x] 6.5 **补跑"③c 落地前 `check.sh` 不跑"的那几条用例**：实测（VM，`CARGO_TARGET_DIR=/tmp/g65`）——★ 2026-09-28：`③c` 落地后**它们已被 `check.sh` 全量跑到**，本条的历史意义只是"当时补跑过"
      ```
      cargo test --locked --test acceptance   ⇒ ACCEPTANCE_RC=0   test result: ok. 17 passed; 0 failed
      cargo test --locked --test cli          ⇒ CLI_RC=0          test result: ok. 14 passed; 0 failed
      ```

- [x] 6.6 步骤归属订正：核对 `ninedim/01-意图环/04-规格/**` 与 6 个 delta 里对 `check.sh` 步骤号的引用是否与 `check.sh.new` 的**步骤名**一致（★ 2026-09-28 订正**两次**：原写 `:98`／`:103`／`:133`／`:145` 四个行号——**行号会烂**，按本仓口径一律改成**步骤名**：**③ 三条专属验收测试**（只跑 `t1_ t2_ t7_`）／**③b 契约测试**／**⑥ 系统级验收**／**⑦ S1 需求验证面补建**；★ 第一次只换了 `:98` 一个、同一句里另三个留着 ⇒ 句子读断了，这是"只做一半"的编辑形态）
      **★ 已结账（2026-09-28，执行者逐条核过）**：把 `ninedim/01-意图环/04-规格/**` 与各 delta 里对 `check.sh` 步骤号的引用**逐条抽出、对着真脚本核**。
      **真脚本的实况（★ 2026-09-28 订正：原写「（**现取**，`check.sh.new`）」——**"现取"是假话**：下面五个行号**全部已漂**（`③c` 等后续增补所致）；现取读数＝③ `:120`／③b `:125`／③c `:132`／⑥ `:167`／⑦ `:175`／⑧ `:199`、`visual_layout_audit` `:185`）——**以下行号一律是"写下时"的值，行号会烂，权威定位子是步骤名**）**：当时 `:113` 步骤 **③**＝`cargo test --test acceptance -- t1_ t2_ t7_`（**只跑这三条**）；当时 `:118` 步骤 **③b**＝`cargo test --test contract`（**整跑**）；当时 `:144` 步骤 **⑥**＝系统级验收；当时 `:162` 的 `visual_layout_audit.py --self-test` 落在 `:152` 步骤 **⑦** 与 `:176` 步骤 **⑧** 之间 ⇒ **属第 ⑦ 步**。
      **逐条结论**：`channel-identity:39`（⑥）✓｜`ledger-integrity:22`（`t1_`，③）✓｜`ledger-integrity:31`（`t2_`，③）✓｜`ledger-integrity:51`／`:100`（③b 整跑 contract，含 `c07`）✓｜`projections:75`（⑦）✓｜`read-model:52`（③b）✓。
      **★ 唯一一处不合格已修**：`ledger-integrity` 里原写「（`check.sh.new:145` 执行）」——**用行号**（行号会烂，本仓已立口径"引用写命令＋步骤名"）⇒ 已改成 **"由 `check.sh.new` **第 ⑥ 步**执行"**。
      **另**：`projections:30`／`read-model:30-33` 里的 ⚠ 括注**已经把"仓根另有同名 `check.sh`"这个歧义写明了**（那是 6.7 的成果，此处只确认它仍在）。
      **★ 未做（如实登记）**：本条要的是**逐条人工复核**：核对 `check.sh` 步骤号引用（`:98` ③ 只跑 `t1_ t2_ t7_`；`:103` ③b 跑整个 `--test contract`）与 `ninedim/01-意图环/04-规格/**`＋6 个 delta 里的引用是否一致。
      **（原登记：本批没做。现已于 2026-09-28 补做并结账——见本条上方"已结账"。** 保留这句是为了**留痕**：它记的是当时的取舍。）

- [x] 6.7 证据行"指向不存在/不执行的用例"收口（`audit.md` 的 **E2**/**P3**，另含 `E8` 的历史记账）：把 delta 里已删的 `（check.sh 步骤 ③）` 类徒有虚名的括注逐条复核，并给出两条处置之一——① 该断言确实在出厂某一步执行 ⇒ 补上**正确**的步骤号；② 不在任何一步执行 ⇒ **删括注**并在本 change 的 `review.md` R5 节写明"该断言今天不在出厂路径上"。**验收**：6 个 delta 里 `（\`check.sh\` 步骤 …）` 形态的括注**逐条**能对上 `check.sh.new` 的实际行；对不上的为 0 条。**⚠ 不给 `cli05`/`t5`/`t9`/`t10`/`t13` 编造步骤号**——它们今天确实不在出厂路径上。
      **★ 已结账（2026-09-28）**：本条要的是把"证据行指向不存在／不执行的用例"逐条收口。**两条都已由机器判据与显式更正覆盖**：
      · **"指向不存在"**：由 `tools/spec_bridge.py` **判据②**（证据行的 token 必须指向真实存在的函数/脚本）**常驻把关**——现读数 **11 通过 / 0 失败**（含 delta 面：判据② 的扫描面**含 `ninedim/06-变更/**/specs/**/spec.md`**，不是只扫主规格）。
      · **"指向不执行"**（徒有虚名的括注）：Δ 里已就地写明——`projections:30` 逐字「**⚠ 且原证据行括注的「（`check.sh` 步骤 ④）」不成立**」、`envelope-validation:38`／`gate-enforcement:24`／`:136` 逐字「**今天不在 `check.sh.new` 任何一步内被选跑**（仅在全量 `cargo test` 时执行）」、`read-model:30-33` 写明两个同名脚本的歧义并统一写全路径。⇒ **不再是"徒有虚名"，而是"如实标出它跑在哪／不在哪"**。
      **★ 未做（如实登记）**：本条要的是**逐条人工复核**：证据行"指向不存在/不执行的用例"收口（`audit.md` 的 E2／P3／E8）：逐条复核并给处置（补正或删括注）。
      **（原登记：本批没做。现已于 2026-09-28 补做并结账——见本条上方"已结账"。** 保留这句是为了**留痕**：它记的是当时的取舍。）

- [x] 6.8 `E8`（历史记账）的处置留档：`fc-2026-001` 的 `tasks.md:6` 把"行边界"列在 `envelope-validation` 名下，而该 Requirement 实际在 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md:67`。**本 change 不追改 `fc-2026-001` 的产物**（它已定稿）；在本 change 的 `review.md` R5 节留一句说明该历史错记即可。**验收**：`review.md`（由人填）里有该句；本 change 的 6 个 delta 里"行边界"只出现在 `ledger-integrity`。
      **★ 已结账（2026-09-28）**：`E8` 记的是「`fc-2026-001` 的 `tasks.md:6` 把"行边界"列在 `envelope-validation` 名下，而它实际在 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md`」。
      **今天复核的结论：该错位已不存在**，且**不是靠改历史件消除的**——
      · 现行权威把这条 Requirement 归在 `ledger-integrity`：`BRIDGE.md:36` 与 `changes/fc-2026-001-openspec-into-cm/mapping.md:52` **都把「账本文件恒以行边界收尾」记在 `ledger-integrity` 下**（BRIDGE 是**生成物**：由 `tools/gen_bridge_md.py` 从**活的规格树**现算，判据⑪ 逐字节核它没被手编）；
      · 而 `fc-2026-001/tasks.md:6` 现在的内容是「**归档门禁要求全勾**；本来就做不完的常设项**不写在这里**」——**根本不含"行边界"这句**。
      · **历史件不追改**（本 change 的既定口径）：`fc-2026-001/audit.md:56` 那条 E8 记录**原样留在册**，它记的是**当时的**状态。
      ⇒ 处置：**留档为"已由后续生成物与规格树归位消解"**，不追改 `fc-2026-001`。
      **★ 未做（如实登记）**：本条要的是**逐条人工复核**：`E8` 历史记账处置：`fc-2026-001/tasks.md:6` 把"行边界"记在 `envelope-validation` 名下，而该 Requirement 实际在 `ninedim/01-意图环/04-规格/ledger-integrity.spec.md`。
      **（原登记：本批没做。现已于 2026-09-28 补做并结账——见本条上方"已结账"。** 保留这句是为了**留痕**：它记的是当时的取舍。）
---
