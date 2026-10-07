# `scripts/` —— 这一夹里有什么、谁在跑它

> **本件是索引，不是交付物**：文档集（S0–S7 那套编号件）是封闭的，本件不属于它。
> ★ **本件不复述计数**——条数与接线状态一律**现取**，每个判据后面给命令。**写死的数必烂**。
> ★★ **本件今天【没有判据盯着】**（现取：全仓 `*.py` 里**零处**读 `tools/README.md`；唯一命中
> `scope_check.py` 的 `ALWAYS_ALLOWED` 是文件名白名单，不是判据）⇒ 按本仓 §八「**不被判据盯住的派生表会静静地烂**」，
> **本件不自带门禁、会漂**，读者**以命令现取为准，不要以本件为权威**。
> 要让它变权威，只有一条路：**给它配一条会红的判据**（"本件列的件名集合 ≡ `tools/` 实际"＋反例），
> 那属 `tools/**` 的改动（SENSITIVE），须走流程 ⇒ **登记为待办，不冒充已解决**。

## 为什么"路径一字不动"

这一夹**件数不写死**（现取：`Get-ChildItem tools -File | Measure-Object`）——
★ 本件初稿把件数写死成「39」，**而写下它那一个动作本身就让它成了 40**（`README.md` 自己）。
⇒ 这正是本仓那条「**计数不写死；给命令**」的现成例子。夹里**四类东西混放**：判据（会红）／生成器／数据与生成物／载体侧与手工件。
**为什么不分成子夹**：这一夹被全仓**按路径**大量引用，**改一处要跟着改一片**。
★ **本件不写那个数**，只给复核命令（口径自选，写清即可）：
`grep -ro 'tools/' world-core openspec .github | wc -l`（或按件名逐个 `grep -c`）。
★ **一处订正（经独立复核）**：本件初稿写「约 1327 处引用，其中很大一部分落在**归档件**与**上游 process-source**」——
2026-10-07 由**独立评审席丙**复核：**该数在任何口径、任何提交上都复现不出来**（现取 1369 逐行／1541 出现次数／
1307 活件出现次数），且「大块在归档」**被证伪**（现取**活件占 84.3%**，归档件＋上游件合计 15.7%）。
⇒ **结论不变（路径不动），理由照实改**：**活件引用面本身就很大**；归档件与上游件**不许改写**这条纪律仍然成立，
但它**不是**本件不搬家的主要理由。
（本仓 §八「改名字 ≠ 修引用」；归档件是历史）。⇒ 物理搬家会把**可解析**变成**不可解析**。
⇒ 处置：**路径不动，改成"一眼可数"**（本件）。

## 一、判据（**会红**的那种）

| 件 | 一句话（照抄它自己的抬头） | 谁执行它（现取） |
|---|---|---|
| `carrier_acceptance.sh` | 载体适配器（M10）的系统级验收：真实二进制／真实内核／真实账本 | `check.sh` 第 ⑥b 步（非 root ⇒ 显式 ⏭） |
| `carrier_contract.py` | 载体契约门禁：把「生成关系」做成会红的判据（12 条，判 `deploy/`） | `check.sh` 第 ⑥c 步 |
| `cross_contract.py` | 两件不许互相矛盾（`ontology.json` × `policy.json`），C-01…C-08 | `check.sh` 第 ⑦c（cross）／⑦d（instance） |
| `grant_path_guard.py` | 本体里声称的「授权路」，程序里必须真的读它 | `check.sh` |
| `ic_books_check.py` | 接口契约**一册**的守卫（曾实测"删掉一册 ⇒ 六道门禁零反应"） | `check.sh` |
| `kind_guard.py` | 架构件里的三类话 vs 帧上方法名 | `check.sh` 第 ⑦b 步（扫描根不在 ⇒ ⏭） |
| `module_graph.py` | 把 `WC-ATOM-001` §四 机核清单四条做成会真红的东西（单意图／`deps==import`／四件同夹／契约字段齐） | `check.sh` 第 ⑨ 步 ＋ CI |
| `plain_text_audit.py` | `REQ-N-001`（语言无关）与 `AC-07`（纯文本审计） | `check.sh` 第 ⑤ 步 ＋ CI |
| `socket_uid_guard.py` | 盘上那个口的属主，必须 ≡ 法律里那条的 uid | `check.sh` 第 ⑦g 步 |
| `spec_bridge.py` | 规格层的守卫：把「应当有人拦」的判据做成会真红的东西（①…⑯） | `check.sh` 第 ⑮ 步 ＋ CI |
| `step_marker.py` | 判 `check.sh` 每步的结局标记（此前"无论结局都打 ✅"） | `check.sh` |
| `system_acceptance.sh` | 系统级验收用例（L3/L4 之间的端到端），跑真实二进制 | `check.sh` ＋ CI ＋ `ci_rehearsal.sh` |
| `table_width_audit.py` | 任一表块的体行格数必须 == 该表头格数（转义感知） | `check.sh` |
| `trace_matrix.py` | 需求追溯矩阵（GB/T 8567／38634.3 口径） | `check.sh` ＋ CI |
| `value_shape_guard.py` | J1：世界里的每一个值，都必须落在一个**已声明的格**上 | `check.sh` |
| `visual_layout_audit.py` | 视觉投影**排版契约**的独立审计器（`TC-051`／`REQ-F-019` 判据④） | `check.sh`（并由两份 probe 调用） |
| `s1_sys_probe.sh` | S1 需求验证面补建（系统级；真实二进制端到端） | `check.sh` ＋ `s1_sys_probe2.sh` |
| `s1_sys_probe2.sh` | S1 需求验证面补建（第二轮）：RTM「系统测试用例」列 | `check.sh` |
| `ci_rehearsal.sh` | 在 VM 内**本地预演** GitHub Actions 的作业 | 手工（它就是"彩排"那个执行体） |
| `scope_check.py` | 「受控变更」的机器化闸门：防静默改框架／顺手重构／越界改动 | **CI**（`check.sh` 里没有，这是有意分工） |
| `ci_self_check.py` | 检查**门禁本身**的完整性，不是业务代码 | **CI**（并由 `s1_sys_probe2.sh` 调） |

### ★ 已知缺口：**判据没有执行体**（现取）

下列 6 件**自己是判据、却没有任何门禁／CI 在跑**——按本仓 §九「闸不在门禁里等于没有闸」，
它们今天**只能算"有守卫 · 无执行体"**（我在 2026-10-06 补过两条同族的：`carrier_acceptance.sh` → ⑥b、`carrier_contract.py` → ⑥c）：

| 件 | 一句话 | 宿主机现取颜色 | 为什么还没接 |
|---|---|---|---|
| `projection_guard.py` | 「界面＝世界的投影」这一面的判据（P1–P10） | **绿**：十条全过（2 条 WEAK） | 可接；**待定** |
| `doc_integrity.py` | 并入件原文章节**逐行仍在**宿主文件内（订正额度内） | **绿**：通过（2 条 WARN） | 可接；**待定** |
| `admission_evidence.py` | 不许把**阶段外**产物当作 S0 准出依据 | **绿**：通过（1 条 SKIP：件不存在） | 可接；**待定** |
| `spec_length_audit.py` | 逐能力「改前改后计数相等」三列 | 只**报表**、恒 rc=0 ⇒ **它今天不是判据**，是审计表 | 不该当闸接（**它红不了**） |
| `chown_plus_guard.py` | 落地用的 `chown` 必须带那个 `+`；盘上要有、仓里也要有 | **rc=2**：要求 `--repo` 或 `--live` | 要**实机**（盘上的口） |
| `last_seen_guard.py` | `presence list` 的 `last_seen` 必须有【账本出处】 | **rc=2**：要求 `--ledger` 与 `--presence` | 要**真实账本**（VM） |

> ⚠ 接任何一条进 `check.sh` 之前，**先问它能不能红**（§五「每条判据都必须会红，否则它是装饰」）：
> `spec_length_audit.py` 就是反例——它是**审计表**，恒 rc=0，**接上去就是装饰**。

## 二、生成器（**改输入、重跑它**；输出不手编）

| 件 | 生成什么 | 谁跑它（现取） |
|---|---|---|
| `gen_owner_uid.py` | 部署面映射：`owner`（名字）→ `uid`（数字） | `deploy/install.sh` |
| `render_channel.py` | 渲染链：在册表（法律）＋部署面 uid ⇒ `channel.json` | `deploy/install.sh` |
| `fetch_bfo_terms.py` | BFO 术语薄层：读本地整包 → `bfo-terms.json` | **手工**（缺省输入现落在归档 `worldcore-上游料-2026-10-06/refs/`） |

## 三、数据与生成物（**不是代码**）

| 件 | 是什么 | 注意 |
|---|---|---|
| `bfo-terms.json` | `fetch_bfo_terms.py` 的生成物（BFO 类集薄层） | 生成物**不手编**；`taken_from` 记的是**当时**的来源读数 |
| `deployment-manifest.json` | 界面层**部署清单**：哪件应与 VM 逐字节相同（`same`）／哪件是有意改动未上线（`pending`） | 它是「**收进仓 ≠ 上线**」那张表的**读数载体** |

## 四、载体侧脚本（**发给主机跑的**，不是本仓的门禁）

| 件 | 一句话 |
|---|---|
| `world-projection.sh` | 界面**唯一**的读路径：读世界**自己的**投影出口 |
| `world-toggle-mute.sh` | 界面**唯一**的写路径：点一下 ⇒ 世界的**一条 `act`** |
| `con01-no-bypass.sh` | `CON-01` 原型（v2）：门禁不可绕过 —— 跨 uid 实测（由 `carrier_acceptance.sh` 调） |

## 五、手工／开发机辅助

| 件 | 一句话 |
|---|---|
| `rustfmt.ps1` | 在 VM 内跑 `rustfmt`，把结果取回本机工作区 |
| `wc_submit.py` | 提交辅助 |
| `business_side.py` | 业务侧（第 4 层）最小样板：点一下 ⇒ 经**唯一写入口**对世界说一句 `act` |
| `case_shell.py` | GUI 侧（最小）：**世界说什么就画什么**——它不认识"第几步""下一步是什么" |

## 六、子夹

| 子夹 | 是什么 |
|---|---|
| `refs/refs/omarchy/` | 界面（Omarchy）那侧的单独一件（现取：1 件） |
| ~~`__pycache__/`~~ | **已清并挡在版外**（2026-10-06：`.gitignore` 增 `__pycache__/`、`*.pyc`；此前它没被挡，`git add -A` 会把 17 件字节码一起收进来） |

---

## 附：本件怎么复核（现取，别信我写的状态）

```bash
# 每件有没有执行体（把 <件名> 换成你要查的）
grep -n '<件名>' check.sh.new .github/workflows/world-core-gate.yml deploy/install.sh
# 这一夹现有几件（条数不写死）
ls tools | wc -l
```
