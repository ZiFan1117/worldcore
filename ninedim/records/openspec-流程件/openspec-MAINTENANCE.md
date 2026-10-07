# 规格层维护清单（MAINTENANCE）

> **本件的用途**：规格层自己的**常设维护项**落在这里——**不进任何 change 的 `tasks.md`**。
> **为什么必须移出来**：`tasks.md` 的归档门禁要求**全勾**，常设项天生做不完，
> 挂在里面会**永久挡住** `openspec validate --archived`（融合档 `schema.yaml:121-123` 逐字预言过这个形态，
> 而它真的在 `2026-09-27-baseline-verified-doctrine` 上发生了：`✗ 2 incomplete tasks (18/20 completed)`）。
> **本件不进任何规格树**，不是规格、不是 change 产物；守卫 `spec_bridge.py` 不读它。

> **目录分工**：`` 里"哪样东西放哪"的口径**只有一处载体**——**`ninedim/records/openspec-流程件/openspec-README.md`**（源／生成物／生成器／工作区四条线）。
> 本件只讲**维护项**；位置变动时改那一页，别在这里复述（**一个事实一个载体**）。

---

## 一、从归档 change 移出的常设项

> 移出时点：`2026-09-27`（由 `fc-2026-001` 的 task 4.2 落笔）。
> 来源：`ninedim/06-变更/archive/2026-09-27-baseline-verified-doctrine/tasks.md` §6「基线之后的维护」。
> **原处留痕**（移出说明 ＋ 原逐字），**不是静默删除**。

| # | 常设项 | 出处（原逐字） | 谁执行 | 什么时候 |
|---|---|---|---|---|
| 1 | **测试改名或 `check.sh` 步骤号变动时，同步修订对应 `证据：` 行** | 「测试改名或 `check.sh` 步骤号变动时，同步修订对应 `证据：` 行」 | 改动者本人（谁改名谁改证据行） | 与改名**同一次改动**里 |
| 2 | **VM 离线期间禁止声称基线已复验** | 「VM 离线期间禁止声称基线已复验」 | 任何写结论的人 | 持续有效 |

> **第 1 条现在有守卫兜着**：`spec_bridge.py` 判据② 会查出"证据行指向的函数不存在"并**非零退出**——
> 但它只保证**发现**，不保证**改对**；改对仍靠人。

---

## 二、规格层自己的维护规则

| # | 规则 | 落点 / 判据 |
|---|---|---|
| 1 | 规格树下**每条 Requirement** 都必须在 `ninedim/records/生成物/BRIDGE.md` 在册（有号或显式标「无号」） | 守卫判据④ |
| 2 | 归档目录必须有非空 `review.md`；**归档件的结论栏必须已签**（结论 ∈ 批准／通过／有条件通过）**且批准人非空**，代签或占位一律判红 | 守卫判据①（在场）＋ **判据⑥（已签）**；`schema.yaml` 的 R5/R4 硬约定 |
| 3 | `ninedim/records/openspec-流程件/openspec-config.yaml` 的 `schema:` 必须为 **`opsx-swe-gb-atom`**（**2026-09-28 由 `opsx-swe-gb` 切过来**——作者指示"06-swe-gb 废除，只留三者融合版本"。**别让它被改回默认档**——那会让每个新 change 静默退回 4 产物原生链，评审与证据守卫全部消失） | 守卫判据③（判据③ 的比对常量已同步改为 `opsx-swe-gb-atom`） |
| 4 | 承载覆盖缺口的 `cover-*` change **必须存在且未归档**，其 `tasks.md` 保留未勾项（＝未实现的东西在册、可见、不装成已成立） | 守卫判据⑤ |
| 5 | **本仓 `ninedim/records/openspec-流程件/schemas/` 是源**；受控面＝本仓 README ＋ `opsx-swe-gb/` 六件（**共七件**；`opsx-swe-gb-atom/` **另计、只在本仓**）。镜像 `D:\Code\10-openspec-swe-gb\schemas\` **无 `.git`、不进受控面**；**若要动它，先备份并记 sha256、把回退办法写进台账**（循 `冲突总账.md` §7.10 先例） | `ninedim/records/openspec-流程件/schemas/README.md` §五（口径改动与让路三要素已记在该节） |
| 6 | 跑守卫：`python3 scripts/verify/spec_bridge.py`；它自己也要能自证会红：`--self-test`（**每条判据各造反例**＋正控＋"不应红"对照；**反例不变红即判该守卫是装饰**。**判据条数与逐条结论以 `--json` 的 `passed`/`failed` 为准，本件不复述条数**——实测该数本轮之内从 9 涨到 11） | 守卫 `--self-test` |
| 7 | **任何一次"不按书来"的处置，必须写全让路三要素**：让的是哪一条／为什么要让／谁批的。**半写＝不写**（书自己的纪律：「冲突时要说明谁让」） | **守卫判据⑦**（按**件整体**判：三要素可分布在 proposal／design／tasks 里） |
| 8 | **原子化编程**是本项目的强制约定：单意图原子性／一个原子一个文件夹（契约＋实现＋测试同夹）／`deps == import` 且无环／生成物不许手编／编码 UTF-8 无 BOM | `ninedim/01-意图环/01-策划/策划-WC-ATOM-001-v0.1.md`；机核工具 `scripts/verify/module_graph.py`（在建） |
| 9 | **书只留一本合订本**：`ninedim/01-意图环/01-策划/` 下**现取只有 1 件**（`语义世界-理论书-第一版-合订.md`）；**正件与来源散件已退场**（`1-理论与哲学`／`2-依据`／`3-备选路线`／`4-计划`／`00-总纲.md`），旧引用的解析根＝**本仓 git 历史**（退场前提交 `bf2eae7` 之前的树） | `ninedim/01-意图环/01-策划/README.md`；`ninedim/records/openspec-流程件/schemas/README.md` §〇 |
| 10 | **仓库面（2026-09-28 更新，三次）**：本仓**两个公开远端**——`origin` ＝ `github.com/ZiFan1117/worldcore`；`segb` ＝ `github.com/ZiFan1117/software-engineering-gb`（**2026-09-28 起它是"三者融合版"的公开面**，旧的"国标化流程落地包"内容保留在该仓分支 `legacy/international-process-2026-09-17`，那是它唯一的回退点）。`github.com/ZiFan1117/agent-native-os` **私有**（我们的版本库，已归档、只读）。**★ 推完一处必须推另一处**——两个公开远端**内容同源**，只推一个是"分叉"（本轮已发生过一次，`10ae6a2` 时 worldcore 先推、旧仓落后一笔）：`git push origin HEAD:.refs/heads/main && git push segb HEAD:.refs/heads/main`；核法 `git ls-remote origin .refs/heads/main` 与 `git ls-remote segb .refs/heads/main` **必须相等** | 核法：`gh repo view ZiFan1117/worldcore --json visibility`／`…software-engineering-gb…`／`…agent-native-os…`；**公开的独立判据**＝匿名取 API 应得 HTTP 200，私有仓匿名取应得 404 |
| 11 | **BRIDGE 的生成链在仓内**：`scripts/gen/gen_bridge_md.py` ＋ 输入 `ninedim/records/生成物/specmap.json`（**仓内这份为准**，仓外 `D:\Code\_specmap\` 那份只作历史）。改规格后**必须重跑生成器**，不许手改 `ninedim/records/生成物/BRIDGE.md`。**新增或改动 `scripts/test/*.rs` 之后，三件生成器必须按 `python scripts/gen/gen_specmap.py` → `python scripts/gen/gen_secmap.py` → `python scripts/gen/gen_bridge_md.py` 的顺序重跑（先 specmap、再 secmap）；顺序错会让判据⑬（`ninedim/records/生成物/节对齐.md` 记的来源坐标）红**——判据⑬ 核的是该图首部**记下的 `ninedim/records/生成物/specmap.json` 哈希**＝当前值，故**凡是"specmap 重跑过、secmap 没跟着重跑"一律红**；实测两种错序：①先跑 secmap 再跑 specmap ⇒ rc=1、⑬ 红；②先跑 bridge 再跑 specmap ⇒ rc=1、⑬ 红；两种错序下**只补跑 bridge 都不消除它**（补跑 secmap 才转绿）。现取复算：`python scripts/verify/spec_bridge.py`（本条判据的读数以该命令输出为准，**本处不复述条数**；2026-09-28 在 `wt-gate` 树实测：正确顺序 ⇒ 该命令 rc=0，反例「先 secmap 再 specmap」⇒ rc=1 且逐字报「[FAIL] ⑬ 节对齐.md 记录了当前来源坐标（生成物不许手编）」） | 判据④；`scripts/gen/gen_bridge_md.py` 头部注明 |
| 12 | **原子化编程**（同规则 8）：机核**就是** `scripts/verify/module_graph.py` 本身（A-1／A-2／A-4），由 `check.sh.new` 第 ⑨ 步与 CI 的 `module-graph` 作业跑；`module_graph.py` 必须**纳入版本控制**（"闸在控制之外"等于没有闸）。⚠ **本格的落点原写「`cover-*` tasks 第 12 组」——那是一个已归档 change 的组号，在办件 `cover-remaining-capabilities` 里只有第 1–7 组，读者按旧指针翻不到**；故改为直接指向工具本体＋登记表（2026-09-28 改） | `WC-ATOM-001` §四；`WC-MODREG-001` §3.1（本表怎么承担 A-1…A-6） |
| 13 | **流程文档不许有「修订记录」节**（修订记录＝git 提交历史；**书除外**） | 守卫判据⑧；skill §三 |
| 14 | **规格正文不许有「改因块」**（改因属该 change 的 `design.md`／`audit.md`） | 守卫判据⑨；skill §三 |
| 15 | **文档集封闭**：S0–S7 每阶段就那么几份，**不许新增、不许拆册**；要加要拆先经作者批准 | .agents/skills/worldcore-sdd/SKILL.md §二 |
| 16 | **不做「探针」这类额外件**：要检查就在既有门禁脚本里就地做，检查数据必须已声明 | skill §四 |

---

## 三、谁维护

- **执行者**：任何改动规格层的人（改规格、改测试名、改 `check.sh` 步骤号的人）。
- **复核**：评审席在归档前跑一次 `python3 scripts/verify/spec_bridge.py`，把原始输出贴进该 change 的 `review.md` §五。
- **本件的更新方式**：直接改本件即可，**不需要 change**（它不是受控配置项，也不进规格树）。
