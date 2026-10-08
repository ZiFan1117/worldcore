# `scripts/` —— 这一夹里有什么、谁在跑它

> **本件是索引，不是交付物**：文档集（S0–S7 那套编号件）是封闭的，本件不属于它。
> ★ **本件不复述计数**——件数与接线状态一律**现取**，每个判据后面给命令。**写死的数必烂**。
> ★★ **本件今天【没有判据盯着】**——★★ **口径必须写出来**，否则同一条断言会给出两种答案
> （2026-10-08 复核 F-07）：
>   · 「**作为输入读**」口径（判据真的把本件读进去）⇒ **零处** ← **本条结论用的是这个口径**；
>   · 「**逐字 grep**」口径 ⇒ **有命中**：`scripts/verify/spec_bridge.py:897` 的**注释**里写了本件名
>     （它说的是"表体同形"，**不是输入**）——★ 命中数随注释增长，故此处**不复述条数**。
>   · 另一个相关命中是 `scope_check.py` 的 `ALWAYS_ALLOWED`：那是**文件名白名单**，不是判据。
>   ⇒ 按本仓 §八「**不被判据盯住的派生表会静静地烂**」，**本件不自带门禁、会漂**，
>   读者**以命令现取为准，不要以本件为权威**。复核命令（逐字口径；工作目录＝仓根）：
>   `Select-String -Path (Get-ChildItem -Recurse -Filter *.py).FullName -SimpleMatch 'scripts/README.md'`
> 要让它变权威，只有一条路：**给它配一条会红的判据**（"本件列的件名集合 ≡ `scripts/` 实际"＋反例），
> 那属 `scripts/**` 的改动（SENSITIVE），须走流程 ⇒ **登记为待办，不冒充已解决**。

## 〇、路径口径（2026-10-07 随顶层收敛订正）

| 什么 | 住哪 | 权威 |
|---|---|---|
| 判据（会红） | `scripts/verify/*.py` | 本件 ＋ 各件文件头 |
| 生成器（改输入、重跑） | `scripts/gen/*.py` | 本件 |
| 集成测试（Rust） | `scripts/test/*.rs`（`Cargo.toml` 里显式 `[[test]] path`） | `AGENTS.md` |
| 载体侧脚本（发给主机跑） | `scripts/release/`、`scripts/collab/` | 本件 |
| 工程域（**只装档案**） | `ninedim/` | `ninedim/_索引-工程域结构与命名.md` |
| 料（不入版本控制） | `.refs/` | `AGENTS.md` |

**★ 一条订正（本席 2026-10-07 现取）**：本件旧版通篇按 `tools/` 写（含 `tools/README.md`、
`ls tools | wc -l`、`grep -ro 'tools/' world-core openspec`），那是**布局迁移前**的坐标——
判据脚本已随顶层收敛分进 `scripts/<用途>/`（9 类）。本席把件内旧路径**逐件核存在性**后随迁：
`tools/<件>` → `scripts/<用途>/<件>`、`docs/…` → `ninedim/…`、旧 CI 名 `world-core-gate` → `gate`。

## 一、判据（**会红**的那种）

件数**不写死**，命令现取：`Get-ChildItem scripts/verify -File -Filter *.py | Measure-Object`

| 件 | 一句话（照抄它自己的抬头） | 谁执行它（现取：在 `check.sh`／`gate.yml` 里点名） |
|---|---|---|
| `verify/carrier_contract.py` | 载体契约门禁：把「生成关系」做成会红的判据（12 条） | `check.sh` 第 ⑥c 步 ＋ `release/install.sh` |
| `verify/check_loops.py` | 双循环落地判据 | `check.sh` |
| `verify/ci_self_check.py` | 检查**门禁本身**的完整性，不是业务代码 | CI（`gate.yml`）＋ `ci_rehearsal.sh` ＋ `s1_sys_probe2.sh` |
| `verify/cross_contract.py` | 两件不许互相矛盾（`ontology.json` × `policy.json`），C-01…C-08 | `check.sh` 第 ⑦c／⑦d |
| `verify/grant_path_guard.py` | 本体里声称的「授权路」，程序里必须真的读它 | `check.sh` ⑦e（**登记型**）＋ `release/install.sh` |
| `verify/ic_books_check.py` | 接口契约**一册**的守卫 | `check.sh` |
| `verify/kind_guard.py` | 架构件里的三类话 vs 帧上方法名 | `check.sh` 第 ⑦b 步 |
| `verify/module_graph.py` | `WC-ATOM-001` §二 机核判据（单意图／`deps==import`／四件同夹） | `check.sh` 第 ⑨ 步 ＋ CI |
| `verify/plain_text_audit.py` | `REQ-N-001`（语言无关）与 `AC-07`（纯文本审计） | `check.sh` 第 ⑤ 步 ＋ CI ＋ `s1_sys_probe2.sh` |
| `verify/scope_check.py` | 「受控变更」的机器化闸门：防静默改框架／顺手重构／越界改动 | **CI**（`check.sh` 里没有，这是有意分工） |
| `verify/signoff_guard.py` | 两枢纽签字面：**S-A 枢纽A 未批不许动手**／**S-B 枢纽B 未签不进 archive**（★「归档签字链」只是 **S-B** 的射程——原表把它当整件的名字，是把两闸说成一闸，F-10） | `check.sh` 第 ⑦h 步 |
| `verify/socket_uid_guard.py` | 盘上那个口的属主 ≡ 法律里那条 uid | `check.sh` 第 ⑦g 步 |
| `verify/spec_bridge.py` | 规格层的守卫（16 条：①…⑯） | `check.sh` 第 ⑧ 步 ＋ CI |
| `verify/spec_shape.py` | 规格形态（Requirement／Scenario／WHEN／THEN 齐备） | `check.sh` 第 ⑧ 步 ＋ CI |
| `verify/step_marker.py` | 判 `check.sh` 每步的结局标记（`PASS/SKIP/FAIL/REG`） | `check.sh` |
| `verify/table_width_audit.py` | 任一表块的体行格数必须 == 该表头格数（转义感知） | `check.sh` |
| `verify/trace_matrix.py` | 需求追溯矩阵（GB/T 8567／38634.3 口径） | `check.sh` ＋ CI ＋ `ci_rehearsal.sh` |
| `verify/value_shape_guard.py` | J1：世界里的每一个值，都必须落在一个**已声明的格**上 | `check.sh` 第 ⑦f 步（**登记型**） |
| `verify/visual_layout_audit.py` | 视觉投影**排版契约**的独立审计器 | `check.sh` ＋ 两份 probe |
| `test/carrier_acceptance.sh` | 载体适配器（M10）系统级验收 | `check.sh` 第 ⑥b 步（非 root ⇒ ⏭） |
| `test/system_acceptance.sh` | 系统级验收（L3/L4 之间的端到端） | `check.sh` ＋ CI ＋ `ci_rehearsal.sh` |
| `test/s1_sys_probe.sh`／`s1_sys_probe2.sh` | S1 需求验证面补建（两轮） | `check.sh` 第 ⑦ 步 |
| `test/ci_rehearsal.sh` | 在 VM 内**本地预演** GitHub Actions 的作业 | 手工（它就是"彩排"那个执行体） |
| `test/con01-no-bypass.sh` | `CON-01` 原型（v2）：门禁不可绕过（跨 uid 实测） | 由 `carrier_acceptance.sh` 调 |

## 二、★ 接线台账：**有守卫 · 无执行体**（**已成史，留档不删**）

复核命令（换 `<件名>` 即可）：

```powershell
Select-String -Path check.sh,.github/workflows/gate.yml,scripts/test/ci_rehearsal.sh -SimpleMatch '<件名>'
```

**★ 状态订正（2026-10-08，复核 F-12 的返工项）**：下面那 6 件里 **5 件已接进 `check.sh`**
（`⑦i` `doc_integrity`／`⑦j` `admission_evidence`／`⑦k` `projection_guard`／`⑦l` `chown_plus_guard`／
`⑦m` `last_seen_guard`）；`spec_length_audit.py` **按结论不接**（它红不了）。
⇒ 本节以下三列（"自己是判据却没有任何门禁在跑"＋**2026-10-07 的本席实跑颜色**）**是那一刻的读数**，
**以 `check.sh` 与各件当场输出为准**；接线形态见 §四 的状态行。

下列 6 件在 2026-10-07 时**自己是判据、却没有任何门禁／CI 在跑**——按本仓 §九「闸不在门禁里等于没有闸」，
那时它们**只能算「有守卫 · 无执行体」**。**下表颜色是 2026-10-07 逐件实跑取的原读数**（不改写、留档）：

| 件 | 一句话 | 现取颜色（本席实跑） | 能不能接／为什么 |
|---|---|---|---|
| `verify/doc_integrity.py` | 并入件原文章节**逐行仍在**宿主文件内（订正额度内） | **rc=0 绿**：五件的并入件原文章节逐行仍在 | **2026-10-08 已接线**（`check.sh` **⑦i**，**显式分岔**：有 `.git` 工作树 ⇒ `run_tail` 真跑；VM 镜像无 `.git` ⇒ 显式 ⏭）。★ 它按纪律 **fail-closed**：无 `.git` 时 **rc=1**（实测）⇒ **裸 `run_tail` 会把 VM 上的全闸当场停住**，故不许裸接。见 §四 第 1 条 |
| `verify/admission_evidence.py` | 不许把**阶段外**产物当作 S0 准出依据 | **rc=0 绿**：被扫 1 份＝`ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R0-001-v0.1.md`，0 违规；★**扫描面 0 份 ⇒ rc=2「未能校验」**（2026-10-08 现取） | **可接**（★**2026-10-08 起**才成立）。本席 2026-10-07 只修了两处（扫描面路径、`--repo-root` 缺省按脚本位置推），**没修 fail-closed**：被扫件被删／仓根指错时，它**自己打印"未校验"、紧接着判"通过"**（rc=0）——**那是假绿**（独立复核席 2026-10-08 F-01 ＝ 仓内 `ninedim/04-枢纽B-后置闸/评审-后置-WC-RV-R0-001-v0.1.md` 的 **C-04**）。**同轮已修**：`scanned == 0` ⇒ rc=2 ＋ 结论串不再写「通过」；`--self-test` 补 3 条**真件级**反例/正控（空扫描面 ⇒ rc≠0、真件含被禁形态 ⇒ rc=1、真件干净 ⇒ rc=0）。★**2026-10-08 已接线**（`check.sh` **⑦j**，**阻断式**——它 fail-closed，缺输入 rc=2 ⇒ 全闸当场阻断，见 §四 第 2 条） |
| `verify/projection_guard.py` | 「界面＝世界的投影」这一面的判据（P1–P10） | **rc=1 红 1 条 ＋ WEAK 2 条**：P10 说 `scripts/release/world-projection.sh` 登记 `same` 而仓内 sha ≠ 表里 VM 值（`4c7728c15cd404ac` ≠ `a10b5abf283e806c`）＝**清单过期** | **2026-10-08 已按登记型接入**（`check.sh` **⑦k**，`run_registered`）。★ 本席已修掉"按 `tools/world-*` 取到 0 件"的**假红**（界面件现取在 `scripts/release/` ∪ `scripts/collab/`） |
| `verify/spec_length_audit.py` | 逐能力「改前改后计数相等」三列 | **rc=0（恒 0）**：它只**报表**、没有红/绿分支 ⇒ **它今天不是判据**，是审计表 | **不该当闸接**（**它红不了**，接上去就是装饰）。★ 本席已修它的输入面（原按 `openspec/specs/**/spec.md` 取 ⇒ 合计恒 0；现取 9 能力／49 Requirement／87 Scenario） |
| `verify/chown_plus_guard.py` | 落地用的 `chown` 必须带那个 `+`；盘上要有、仓里也要有 | `--repo .`：**rc=0，STATUS=SKIP**（P-01/P-04 判过：`release/units/world-core.service:45-46` 两条都带 `+`、都点名具体口；**P-02/P-03 未校验**——缺 `--live`）。裸跑仍 rc=2 | **2026-10-08 已接线**（`check.sh` **⑦l**，`run_registered 8 … --repo .`）。★ 盘上那一面要 root＋宿主 systemd 目录 ⇒ 只有 VM 判得了（**未校验 ≠ 通过**）。本席已修两处：扫描面非递归打到空目录（"仓内 0 ＝ 盘上 0"的**空集绿**）、缺一面被折成 `[]` 的**假红** |
| `verify/last_seen_guard.py` | `presence list` 的 `last_seen` 必须有【账本出处】 | **rc=2**：`[FAIL] 需要 --ledger 与 --presence ⇒ **不是通过**` | **2026-10-08 已按 ⑦g 的两岔写法接入**（`check.sh` **⑦m**：有账本＋`presence list` 落盘件 ⇒ `run_registered`；缺任一面 ⇒ 显式 ⏭） |

> ⚠ 接任何一条进 `check.sh` 之前，**先问它能不能红**（§五「每条判据都必须会红，否则它是装饰」）：
> `spec_length_audit.py` 就是反例——**审计表，恒 rc=0，接上去就是装饰**。

## 三、生成器（**改输入、重跑它**；输出不手编）

件数现取：`Get-ChildItem scripts/gen -File -Filter *.py | Measure-Object`

| 件 | 生成什么 | 谁跑它（现取） |
|---|---|---|
| `gen/gen_owner_uid.py` | 部署面映射：`owner`（名字）→ `uid`（数字） | `release/install.sh` |
| `gen/render_channel.py` | 渲染链：在册表（法律）＋ 部署面 uid ⇒ `channel.json` | `release/install.sh` |
| `gen/gen_specmap.py` | 抽取规格／SRS／书章节 ⇒ `ninedim/records/生成物/specmap.json` | **手工**（生成链的**第一跳**，见下） |
| `gen/gen_bridge_md.py` | `specmap.json` ⇒ `ninedim/records/生成物/BRIDGE.md`（判据④ 的受检对象） | **手工**（第二跳） |
| `gen/gen_secmap.py` | `specmap.json` ＋ 落点件 ⇒ `ninedim/records/生成物/节对齐.md` | **手工**（第三跳） |
| `gen/fetch_bfo_terms.py` | BFO 术语薄层：读本地整包 → `gen/bfo-terms.json` | 手工 |
| `gen/audit_checked_refs.py` | 反假勾审计：`cover-*` 已勾条目的引用是否真存在 | 手工 |
| `gen/collect_evidence.py` | 证据收集 | 手工 |

### ★ 生成链的顺序（**不许颠倒**；2026-10-07 本席实跑三跳 rc 全 0）

```sh
python scripts/gen/gen_specmap.py       # → ninedim/records/生成物/specmap.json
python scripts/gen/gen_bridge_md.py     # → ninedim/records/生成物/BRIDGE.md
python scripts/gen/gen_secmap.py        # → ninedim/records/生成物/节对齐.md
```

**为什么顺序是承重的**：`gen_bridge_md.py`／`gen_secmap.py` **读** `specmap.json`；
而判据⑫ 核 `specmap.json` 里记的 `_generator_sha256`、判据⑪ 核 `BRIDGE.md` ≡ 生成器当前输出、
判据⑬ 核 `节对齐.md` 首部记的两个来源哈希 ⇒ **跳一步、或改了生成器不重跑，⑪⑫⑬ 当场红**。

**现取病灶（2026-10-07，本席修）**：`gen_specmap.py` 仍按旧形态 `<能力>/spec.md` 取，而主规格已改成
平铺的 `<能力>.spec.md`（权威：`ninedim/_索引-工程域结构与命名.md` §二）⇒ `caps` **静默为 0**
⇒ `BRIDGE.md` 空 ⇒ ④⑪⑫⑬ 全红。已修：两形态照实况取平铺、**空集／零 Requirement 当场报错退出**
（不许再静默产出空件）、产物落回 `ninedim/records/生成物/specmap.json`（原来落 `REPO/generated/`——
那个夹随迁移已不存在）、`tests/` 键 → `scripts/test/`。

## 四、★ `check.sh` 接线清单（**已成史，留档不删**）

> **★ 状态（2026-10-08 现取）**：下表第 **1–5** 条**已落**进 `check.sh` 的 **⑦i／⑦j／⑦k／⑦l／⑦m**
> 五步（由另一席落笔；本节的"锚点行号"已漂，**认字面不认行号**）。第 6 条**仍是结论**（不接，理由不变）。
> ★ 落地时**第 1 条改了形态**（理由逐字如下）：
>   · 第 1 条**不是裸 `run_tail`**：`doc_integrity.py` 无 `.git` 时 **rc=1**（fail-closed），
>     而 VM 镜像按 `sync-vm.ps1` **排除 `.git`** ⇒ 裸接会**在 VM 上把全闸停在 ⑦i**（实测）。⇒ 取**显式分岔**
>     （有 git 工作树 ⇒ `run_tail`；没有 ⇒ 显式 ⏭）。
>   · 第 2 条按原文用**阻断式** `run_tail`（fail-closed 是它要的形态），插在 ⑦ 段末（⑦j）。
> 复核命令（现取）：`Select-String -Path check.sh -Pattern '^step "'`（认字面，不认行号）。

| # | 加在哪 | 现取锚点 | 现状 | 改成 |
|---|---|---|---|---|
| 1 | ⑦ 之后新起一步 | `check.sh:389`（`run_tail 20 "表块行宽审计（转义感知）" …`）之后 | （无此行） | `run_tail 8 "并入件原文章节仍在（doc_integrity.py）" python3 scripts/verify/doc_integrity.py` |
| 2 | 接在第 1 条之后 | 同上 | （无此行） | `run_tail 12 "S0 准出证据准入隔离（不许拿阶段外产物当准出依据）" python3 scripts/verify/admission_evidence.py`（★该件 2026-10-08 起是 **fail-closed**：扫描面 0 份 ⇒ **rc=2**、`run_tail` 会**当场阻断全闸**——这是有意的："读不到"不许折成"通过"；被扫件在盘上时才会给结论） |
| 3 | ⑦e／⑦f 之间或之后 | `check.sh:463`（`run_registered 14 "授权路判据…" …`） | 见该行 | `run_registered 14 "界面＝世界的投影（P1–P10；projection_guard.py）" python3 scripts/verify/projection_guard.py`（★ **必须 `run_registered`**：现取红 1 条＝清单过期，属【该更新清单】，不是"谁改坏了"） |
| 4 | ⑦g 之后 | `check.sh:503-509`（口属主那条的显式分岔）之后 | （无此行） | `run_registered 8 "落地 chown 必带 +（仓内面；盘上面要 VM）" python3 scripts/verify/chown_plus_guard.py --repo .`（现取 `STATUS=SKIP` ⇒ 两种助手都会正确显示 ⏭） |
| 5 | 接在第 4 条之后 | 同上 | （无此行） | 照 ⑦g 的**两岔写法**接 `scripts/verify/last_seen_guard.py --ledger … --presence …`：账本／presence 在 ⇒ `run_registered`；不在 ⇒ 显式打印 ⏭（**未校验 ≠ 通过**） |
| 6 | **不接** | — | — | `spec_length_audit.py` **不接**（恒 rc=0，是审计表不是判据；接了就是装饰） |

> 第 6 条是**结论**，不是遗漏：**"能接的接上、不能接的写明原因"** 里的"不能接"就是它这一条
> （原因：**它不会红**），以及第 5 条的盘上那一面（原因：**要真实账本**）。

## 五、数据与生成物（**不是代码**）

| 件 | 是什么 | 注意 |
|---|---|---|
| `gen/bfo-terms.json` | `fetch_bfo_terms.py` 的生成物（BFO 类集薄层） | 生成物**不手编**；`taken_from` 记的是**当时**的来源读数 |
| `release/deployment-manifest.json` | 界面层**部署清单**：哪件应与 VM 逐字节相同（`same`）／哪件是有意改动未上线（`pending`） | 判据 P10 读它；`host` 一律**仓根相对**（2026-10-07 已随迁） |

## 六、载体侧脚本（**发给主机跑的**，不是本仓的门禁）

| 件 | 一句话 |
|---|---|
| `release/world-projection.sh` | 界面**唯一**的读路径：读世界**自己的**投影出口 |
| `release/world-toggle-mute.sh` | 界面**唯一**的写路径：点一下 ⇒ 世界的**一条 `act`** |
| `release/install.sh` | 装机（单元 ＋ 法律种子 ＋ uid 映射 ＋ 渲染链） |
| `release/units/` | systemd 单元（`*.service`／`*.socket`）——**不是**界面脚本，`projection_guard.py` 不扫它们（只扫非递归的 `world-*`） |
| `collab/wc_submit.py` | 界面层**唯一写入口**的提交件（作者身份由**口**给出） |
| `collab/business_side.py` | 业务侧（第 4 层）最小样板：点一下 ⇒ 经**唯一写入口**对世界说一句 `act` |
| `collab/case_shell.py` | GUI 侧（最小）：**世界说什么就画什么** |

## 七、手工／开发机辅助

| 件 | 一句话 |
|---|---|
| `build/rustfmt.ps1` | 在 VM 内跑 `rustfmt`，把结果取回本机工作区（★ `.ps1` 必须带 UTF-8 BOM，`ci_self_check.py` 判它） |
| `bench/`／`report/`／`maintain/` | 空夹占位（各一份 `_索引.md`） |

## 附：本件怎么复核（现取，别信我写的状态）

```powershell
# 每件有没有执行体（把 <件名> 换成你要查的）
Select-String -Path check.sh,.github/workflows/gate.yml,scripts/test/ci_rehearsal.sh -SimpleMatch '<件名>'
# 这一夹现有几件
(Get-ChildItem scripts -Recurse -File | Measure-Object).Count
# 判据自证（每一件都应 rc=0；不会红的判据只配当返工项）
Get-ChildItem scripts/verify -Filter *.py | ForEach-Object { python $_.FullName --self-test }
```
