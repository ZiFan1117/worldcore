# WC-ST-001 系统测试

> 这份文档管**"系统测试怎么跑、在哪跑、读数怎么取"**。它不写"某次跑出多少"，那属**现取**（见 §四）。

## 一、测试面（**§一 的两张表都是权威清单，由判据⑮ `j15_doc_lists_match_reality` 盯着**——表里少了／多了测试件、或少了／多了 `tools/` 下的脚本，守卫会红）

**测试二进制**（`scripts/test/`，`cargo test --locked` 逐个跑）：

| 文件 | 管什么 |
|---|---|
| `acceptance.rs` | 端到端验收用例（`t*`）：真实二进制的写入—折叠—读出链 |
| `contract.rs` | 接口契约用例（`c*`）：按 `WC-IC-001` 的模块契约逐条钉 |
| `cli.rs` | 命令行面（`cli*`）：子命令、错误码、`--help` 清单 |
| `atom_reversibility.rs` | 可逆性与两处配置互校（`a*`） |
| `atom_declared_only.rs` | 声明以外不许落账（`b*`） |
| `delivery.rs` | 投递与应答（`to` 的语义、`request_id` 配对） |
| `ontology_ext.rs` | 本体扩展面（未知旗标忽略／扩展项与核心重名须拒／只加扩展则折叠不变） |
| `trace_notice.rs` | `trace` 的写入入口与读回／通告的闸（两条拒绝路径不许互相冒充） |
| `perf.rs` | 性能面（带检查点路径的目标） |
| `channel_bounds.rs` | 通道四条资源边界（`REQ-F-026`）：单行上限／每秒上限／空闲超时／并发上限（含"正好等于上限必须放行"的正控） |
| `family_readmodel.rs` | 家族演进与向前兼容（`REQ-F-027`）＋ 读模型侧的缺格即报错（`REQ-F-032`） |
| `ontology_elements.rs` | **本体五要素**（对象／关系／接口·能力／动作／函数，`m*`）：节存在性（库层＋CLI 两层）／字段值类型（含 `enum` 闭集与 `ref`，**`kind` 除外**）／关系两端类型／声明式内嵌标记／按类型实例计数与单实例上限／许可只授在能力上／动作引用能力（本体侧＋策略侧＋交叉）／函数入口表不许出现命令字面量／**分节挂 `_` 键 ⇒ 词表身份不变**／`_objects`（读路径）与 `concepts`（身份）**同名字段的类型声明不得各说各话**（`ConceptsDrift`）／**十二节归属表 ＝ 实际 `_` 分节**（`SectionMapDrift`）／**结构性死声明**（死入口 `DeadFunctionEntry`／悬空引用 `DanglingFunctionRef`／死能力 `DeadCapability`）／**载体专有串不进本体身份面**（`CarrierSpecificInOntology`）／**`usage` 只报告不拒启**（正控） |
| `carrier_boundary.rs` | **载体 vs 世界**（`c*`）：world 源码不读载体件（静态面，**认结构不搜字样**）／换一份诱饵 `deploy/` ⇒ `state --json` **逐字节不变**（判据①b）／unit 依赖**不许指向具体应用**（判据②a，含合成反例）／**应用全停** ⇒ `check` rc=0 且折叠同源（判据②b 正控）／socket 权限指令**只许出现在 `.socket`**（判据④-i） |
| `carrier_serve.rs` | **载体拉起 `serve`**（`s*`）：缺 `LISTEN_FDS` ⇒ 拒启并点名（且**不许**拿 `NOTIFY_SOCKET` 缺失当致命）／`LISTEN_PID` 不是本进程或缺 ⇒ 拒启并点名／fd 3 不可用 ⇒ 拒启并点名且**不许**变成 `fatal runtime error`／通知变量坏了**不许**掩盖 `LISTEN_FDS` 那一格；`READY=1` 在受理**之前**（结构缝，真投递）＋ 看门狗半周期由 `src/main.rs` 内联模块 `serve` 的单元用例钉住 |
| `projection_leaf.rs` | 读法是叶子（书 §4.4）：几份读法之间不互相调用、不持有状态 |
| `projection_surface.rs` | 屏面投影（`M12`）：**只给屏幕那一面**／**带位点**／**三份投影两两同源**（"两条独立腿"）；含落后一反例 |
| `write_side.rs` | 写侧适配（书 §4.5）：只写不裁决／前值必须带上／对被管者 uid 的写权限边界 |
| `agent_audit.rs` | Agent 运行时的**结构化审计留痕**（`g*`）：一条记录恒占一帧／文件回退是 JSON Lines 且带时间戳／多路出口的失败隔离／字段名是固定集合 |
| `agent_protocol.rs` | Agent 运行时的**行分隔结构化请求／应答**（`p*`）：一问一答顺序一致／坏字节不吞下一条请求／拒绝必须带机器可读的码 |
| `agent_completion.rs` | Agent 运行时的**完工通告**（`j*`）：完工是账本上一条可读回的通告／启动失败也留痕／待办只由账本折叠回答（**不靠第二本登记簿**）／读回幂等 |
| `agent_undo.rs` | Agent 运行时的**动手前载体撤销点**（`u*`）：编排出一次且顺序在人确认之后／撤销点失败即不执行／不需要撤销的策略不编排／**载体撤销点不是世界回滚** |
| `ontology_instance.rs` | **每个实例必须指回定义面**（书 §5.3 的**读侧**那一半，`i*`）：换一本不声明该类型的法律读同一本账 ⇒ 拒（`EntityNotDeclared`，点名类型段与主体）／恢复·迁移那一行 ⇒ 拒／正控四条（已声明照常、纯加法读旧账、裸主体不判、内嵌四段按第 3 段）／空实体集 ⇒ 拒折（`NoDeclaredEntities`）／"没接"由 `None` 显式表达（既有直接装配点不受影响） |
| `return_vocabulary.rs` | **回来方向的对账**（一条**会红**的判据）：账本里出现过的通告类型（去掉内核保留前缀 `gate.` 之后剩下的**每一种**）**世界侧必须有一处"认它"的读法**；认不得 ⇒ 红。落点在 `scripts/test/` 而**不**落 `src/carrier/**`——后者会新增模块边，与 `WC-ATOM-001` §二 A-4 的 `deps == import` 冲突 |

**脚本面**（★**口径**：`scripts/` 下**递归**的 `*.py`／`*.sh`／`*.ps1`；件名一律写**仓根相对路径**；★本表是**该口径下的全表**；
"管什么"一列**逐件取自各文件自己的头**，不是另写的说法）：

> ★ **本表由判据⑮ `j15_doc_lists_match_reality` 双向盯着**：`scripts/` 下**多一个 `*.py`／`*.sh`／`*.ps1` 而表里没有** ⇒ 红；
> **表里列了而目录里没有** ⇒ 红；**整张表不见了**而 `scripts/` 下确有件 ⇒ 红。跑 `python scripts/verify/spec_bridge.py` 即见分晓。
> ⇒ ★ 它盯的是「**件名 ≡ 实际**」，**不盯**"管什么"这一列写得对不对——那要人读。
> ★ **唯一入口不在此表**：`check.sh`（它**不在** `scripts/` 下，在**仓根**）。

| 脚本 | 管什么 |
|---|---|
| `scripts/build/rustfmt.ps1` | （待补：脚本自述） |
| `scripts/collab/business_side.py` | （待补：脚本自述） |
| `scripts/collab/case_shell.py` | （待补：脚本自述） |
| `scripts/collab/wc_submit.py` | （待补：脚本自述） |
| `scripts/gen/audit_checked_refs.py` | （待补：脚本自述） |
| `scripts/gen/collect_evidence.py` | （待补：脚本自述） |
| `scripts/gen/fetch_bfo_terms.py` | （待补：脚本自述） |
| `scripts/gen/gen_bridge_md.py` | （待补：脚本自述） |
| `scripts/gen/gen_owner_uid.py` | （待补：脚本自述） |
| `scripts/gen/gen_secmap.py` | （待补：脚本自述） |
| `scripts/gen/gen_specmap.py` | （待补：脚本自述） |
| `scripts/gen/render_channel.py` | （待补：脚本自述） |
| `scripts/release/install.sh` | 部署件安装脚本：建身份与目录 → 装四份单元 → 载体系上套接字 → 逐条核对（`--check` 只核对；`--uninstall` **不动账本与法律**） |
| `scripts/release/world-projection.sh` | （待补：脚本自述） |
| `scripts/release/world-toggle-mute.sh` | （待补：脚本自述） |
| `scripts/test/carrier_acceptance.sh` | （待补：脚本自述） |
| `scripts/test/ci_rehearsal.sh` | （待补：脚本自述） |
| `scripts/test/con01-no-bypass.sh` | （待补：脚本自述） |
| `scripts/test/s1_sys_probe.sh` | （待补：脚本自述） |
| `scripts/test/s1_sys_probe2.sh` | （待补：脚本自述） |
| `scripts/test/system_acceptance.sh` | （待补：脚本自述） |
| `scripts/verify/admission_evidence.py` | （待补：脚本自述） |
| `scripts/verify/carrier_contract.py` | （待补：脚本自述） |
| `scripts/verify/check_loops.py` | 双环·四种循环（L1–L4）＋「九维都有活体」的可机检判据（八条，`--self-test` 逐条给反例） |
| `scripts/verify/chown_plus_guard.py` | （待补：脚本自述） |
| `scripts/verify/ci_self_check.py` | （待补：脚本自述） |
| `scripts/verify/cross_contract.py` | （待补：脚本自述） |
| `scripts/verify/doc_integrity.py` | （待补：脚本自述） |
| `scripts/verify/grant_path_guard.py` | （待补：脚本自述） |
| `scripts/verify/ic_books_check.py` | （待补：脚本自述） |
| `scripts/verify/kind_guard.py` | （待补：脚本自述） |
| `scripts/verify/last_seen_guard.py` | （待补：脚本自述） |
| `scripts/verify/module_graph.py` | （待补：脚本自述） |
| `scripts/verify/plain_text_audit.py` | （待补：脚本自述） |
| `scripts/verify/projection_guard.py` | （待补：脚本自述） |
| `scripts/verify/scope_check.py` | （待补：脚本自述） |
| `scripts/verify/signoff_guard.py` | 两个枢纽的**签字面**判据（S-A 枢纽A 未出「批准」⇒ 执行环不许有产物；S-B 枢纽B 未签 ⇒ 变更不许进 `archive/`） |
| `scripts/verify/socket_uid_guard.py` | （待补：脚本自述） |
| `scripts/verify/spec_bridge.py` | （待补：脚本自述） |
| `scripts/verify/spec_length_audit.py` | （待补：脚本自述） |
| `scripts/verify/spec_shape.py` | （待补：脚本自述） |
| `scripts/verify/step_marker.py` | （待补：脚本自述） |
| `scripts/verify/table_width_audit.py` | （待补：脚本自述） |
| `scripts/verify/trace_matrix.py` | （待补：脚本自述） |
| `scripts/verify/value_shape_guard.py` | （待补：脚本自述） |
| `scripts/verify/visual_layout_audit.py` | （待补：脚本自述） |

**测试面的项数一律现数**（不写死）：
```
(cd 到**仓根**再跑；在别处跑会**静默印 0**——路径前缀对不上，但不报错)
python -c "import re,pathlib;print(sum(1 for p in pathlib.Path('scripts/test').glob('*.rs') for l in p.read_text(encoding='utf-8').splitlines() if re.match(r'\s*fn [a-z]+\d', l)))"
```
（口径：测试函数名以字母＋数字开头；**以命令输出为准**。）

**★ 项数不以本表为准（如实登记）**：上面那条命令数出的**项数**（测试函数个数）**不进任何判据**——新增用例而忘了改文档里的数，**没有任何判据会红** ⇒ **项数一律以命令输出为准**。

**件清单**（`scripts/test/*.rs` 与 `scripts/**/*.py`／`*.sh`／`*.ps1`）**进判据⑮**：表里少了／多了件都会红（见 §一 的「测试二进制」表头与「脚本面」表登记）。

## 二、在哪跑（**构建与测试只在 VM**）

主机**没有 Rust 工具链**。一切构建与测试在 VM `world`（Arch Linux）的 `/root/world/world-core`。
推树前**必须镜像同步**——只推不删会让 VM 累积本机早已删掉的件，**读数就不是同一棵树**：

```
& 'D:\Code\sync-vm.ps1'          # 整树单向（本机 → VM），推完删远端多余件
ssh world 'cd /root/world/world-core && bash check.sh'
ssh world 'cd /root/world/world-core && cargo test --locked'
```

## 三、怎么跑（出厂门禁就是测试清单）

`check.sh.new` 是**唯一入口**，它打印的结论清单就是本项目的测试清单（**步数以脚本自己打印的清单为准，本文档不写死**——加一步自动进清单）：

```
bash check.sh          # rc=0 才算全过；任一步 rc≠0，它立刻 exit 1 且不吞失败
```

## 四、读数怎么取（**四要素，不许手抄**）

每条读数必须带：**时点／命令／原始输出／提交号**。取数**一律现跑**：
- 本机：`D:\Code\final_verify.ps1`（主机四闸 ＋ VM 全闸，一次收齐）
- 读数**不许写进文档**——同一个数在一轮之内就会变（实测：判据条数 9→11、`validate` 项数 10→11）。
  **写死的读数必然过期，而过期的读数就是假话**（本项目为此被独立评审席判过三次）。

## 五、什么算失败

- **任一步 rc≠0 即失败**：`check.sh` 的 `run_tail` 遇 rc≠0 立刻 `exit 1`，**不吞失败**；
- **红要如实报红**：本仓允许**如实红**——例如机核层（`scripts/verify/module_graph.py`）今天仍红在三条**在册真缺陷**上。
  **如实红不是缺陷，把红写成绿才是**。判"这条红算不算过"的口径见 `WC-AT-001` §三。
- **每条判据都要能红**：判定器一律带 `--self-test`（每条判据配反例；**反例不变红即判该判定器是装饰**）。

## 六、这份文档不覆盖的

- **不断言"今天多少项通过"**——那是现取读数，见 §四；
- **不规定用例怎么写**——那在 `WC-UT-001`（单元测试）与编码规范 `WC-GSOP-001`；
- **不重复规格**——"世界必须怎样"在 `ninedim/01-意图环/04-规格/`；这份只讲"这个项目怎么跑测试"。
