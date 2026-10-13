# 实读：AI-Native Linux 四面实读汇总（它干了什么 × 我们带什么）

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 六 规格 | **0.1** |

> **件性质**：实读件，**只读取证**；未改 AIOS 任何一行。
> **读法**：四席并行实读（核心执行链／其余实现面与发行系统／开发过程与治理／相冲点专项）＋ 主持人自读。
> ★ **口径**：否定式断言写明**射程**；**未读到 ≠ 没有**；**未跑任何构建**（宿主无 cargo／rustc）。

---

## 一、★★★ 一句话结论（第四席带来的，最重要）

> **AIOS 的问题不是「缺想法」，而是「合同写了、类型有了、门禁立了，但关键路径上的线普遍没接」。**
> ★ 现取：**「执行」目前只到状态机迁移——没有任何一处真正调用适配器**。

| # | 未接的线 | 现取 |
|---|---|---|
| 1 | ★ **适配器没有执行接口** | `AdapterHandle` **只有 `dispatch_kind()`，没有 `execute()`**（`aios-capability-runtime/src/runtime.rs:76-81`）；`step_execute` 只做 `Queued→Executing` 迁移（`pipeline.rs:1959-1986`）；`step_verify` 默认 `EXECUTING→VERIFYING→SUCCEEDED` **两跳直通**（`:1995-1999`）；gRPC `ExecuteAction` 最终就是 `submit_action`（`service/server.rs:320-325`） |
| 2 | ★ **策略包的规则不参与裁决** | 12 步里 **第 6/7 步（bundle 作用域 DENY/ALLOW）是 stub**（`aios-policy/src/pipeline.rs:330-342`）；`GetPolicyEngineInfo` 的 `rules_in_active_bundle` **硬编码 0**（`service/server.rs:567`）⇒ **不命中硬拒/覆盖一律 DefaultDeny** |
| 3 | ★ **运行时证据与 L0 账本是两条互不相通的链** | 运行时唯一入口 `EvidenceSink::append_signed`（`evidence_emit.rs:105-119`），已实现后端是 **`InMemoryEvidenceSink`**（进程内）；`RemoteEvidenceSink` **1 命中且是文档注释**（`:131`，自称 T-033 补、**未补**）⇒ **运行时的证据只进内存** |
| 4 | ★ **证据发射是可选槽** | 不调 `with_evidence_emitter` ⇒ `submit_action` 走 baseline 分支，**一条证据都不发**（`runtime.rs:997-1016`） |
| 5 | ★ **翻译产出零校验** | `aios-cognitive` 里 `CapabilityCatalog｜action_kind` ⇒ **0 调用点**；全仓 `validate_action_name` 类函数 **0 命中**；`ActionErrorCode::InvalidActionName` 有变体（`aios-action/src/error.rs:98`）**但无实现**；`step_validate` **只判 action 是否为空串**（`pipeline.rs:1481-1487`） |
| 6 | ★ **沙箱六源合并没接** | `SandboxRuntimeAdapter::compose_for_action` **把 6 个 source 全传 None**（`runtime_adapter.rs:46-58`）⇒ 事实上只产出 `new_strict` 默认档 |
| 7 | ★ **策略约束没被消费** | 写入方 `pipeline.rs:976,991,1250,1270`；**唯一读取口 `runtime.rs:355` 在 src 内无调用者**（9 命中里 8 处在 `tests/policy_integration.rs`）⇒ 没有 step 消费它 |
| 8 | **校验意图两边没接上** | 认知侧把 `verification_intent := Some(parsed.reasoning)`（LLM 自由文本，`translator_engine.rs:332`）；运行时却从 `request.target.verification_intent` 取（`pipeline.rs:250-257`）—— **字段名相同、根本没接** |

★ **它自己的取向（逐字）**：`002.../NEXT_SESSION.md:127-132` 记着「Bulgarian chat, English artifacts. **Implementation plans are not requested by this user — write contracts, not build sequences.**」⇒ **「骨架多、运行体少」是它的方法，不是意外。**

---

## 二、它干了什么（现取）

1. **十一层 L0–L10 全部标 `REAL`**（`002.../00_MASTER_INDEX.md:21-31`）。
2. **19 个里程碑 ＋ M20 全关**（`MILESTONES.md:15-17`）：19 crate／**4475 workspace 测试 0 failed**／四道 cargo 门全绿（2026-05-29；★ 当时 19 crate，**今天 36**）。
3. **36 个 crate**（`Cargo.toml:3-40` 现取 36 member）：执行主干 7＋认知 1＋存储 1＋密钥 1＋界面 8＋网络硬件 2＋应用兼容 4＋发行生态 4＋运维系统 8。
4. **发行面 `distro/` 149 件**：ISO 总装 12 步（`build-aios-iso.sh` ≈2280 行）／装机 14 阶段（LUKS2＋TPM2 PCR0/1/7＋verity＋SELinux enforcing）／首启 15 phase（`aios-first-boot` 1940 行）／`systemd` **23 个 `aios-*.service`＋Hybrid 模型**（一个 `aios-system` 承载所有槽位）／签名更新＋原子回滚（300s 未确认即回滚）／云镜像 4 家／**8 道企业出口门 8/8 阻断**（`.gitlab-ci.yml` 里 `allow_failure: true` **一处都没有**）。
5. **最新一波（2026-07-14→07-19）＝企业化**：UEFI 安全启动实测／TPM 2.0 measured-boot／气隙签名通道（R13.5）／签名应答文件＋恢复模式＋`FirstBootComplete` 证据（R13.6）／门禁豁免与审计件（R13.7）／支持生命周期＋合规导出（R13.8）。
6. **过程与治理**：Apache-2.0；**GitLab CI 是唯一真源**（GitHub 仅镜像、Actions 禁用）；ADR **`DEC-001…056` 无缺号、追加不删**；`INV-001..024`（Rev.3 再补 `025..034`）封闭枚举；状态词八值／证据级 `E0–E5`；`.ai/tasks.json` 是机器可读真相；`.ai/progress.log` **1164 行**。

---

## 三、★ 它已经有的（别当缺、别重复造）

| # | 它已有 | 现取 |
|---|---|---|
| 1 | **权威语义对象文件系统** | `002.../L2_AIOS_FS/01_object_model.md:14` 逐字「AIOS-FS is the authoritative semantic filesystem rooted at /aios」；「POSIX paths are projections; object identity is not the path」 |
| 2 | **个体身份／类别／版本／视图／事务** | `ObjectId`＝`obj_<ULID>`（`object.rs:20`）；`ObjectKind` **闭枚举 10 值**（`:74-95`）；`VersionId`＋`parent_version_ids`（`version.rs:23,89`）；`PointerKind` 5 值；`ConsistencyClass` 3 值 |
| 3 | **全仓唯一那份只追加证据账本** | `aios-evidence`：**37 个 crate 依赖**；`lib.rs:5-6` 逐字「INV-005 encoded at the Rust type level」；`segment_chain.rs:12`「append is the sole mutator」；**427 个 `RecordType` 封闭表**；6 个 RocksDB CF＋每次写 `set_sync(true)` |
| 4 | **能力名字表**（表在、闸空） | `CapabilityCatalog`（`action_fabric.rs:40-42`）＋ `AdapterActionDeclaration.action_kind`（`adapter_manifest.rs:25-51`）＋ 保留命名空间 `/aios/system/capabilities`（`namespace.rs:77`） |
| 5 | **唯一 Supervisor 口** | `DAEMON-ARCHITECTURE.md:22-31` 逐字「a single `aios-system` binary … Every AIOS-owned daemon unit invokes exactly that binary」 |
| 6 | **受目录约束的翻译器（合同级）** | `DEC-004:57-61` 逐字「catalog-bound compiler … unknown actions and free-form shell execution are rejected」；状态 `CONTRACT` |
| 7 | ★ **AI 只提议不执行的机械强制** | `DEC-038` 逐字「the proposing pipeline … has NO execute path … The structure of the FSM IS the enforcement」；运行时侧 `step_validate_with_provenance`：AI 信封必须带 `cognitive_provenance`，否则 `CREATED→FAILED/AdapterRefused`（`pipeline.rs:1505-1526`）；SIM-D 审计 **ZERO findings** |
| 8 | **信封与生命周期（合同级）** | `DEC-003`：五段顶层；14 个 ID 前缀（ULID）；幂等键 24h TTL；`parent_action_id` 因果＋环检测；**6 边 FSM、终态封闭**；`conditions` 单调性；**BLAKE3**；**JCS(RFC 8785)**；gRPC 单一入口 `SubmitAction` |
| 9 | **渲染面** | 4 个 renderer（cli/kde/web/voice）＋mobile/terminal/control-center；共享 schema `aios.ui.v1alpha1`，**`NodeKind` 闭枚举 19 值**（`aios-renderer-kde/src/node_kind.rs:15`） |
| 10 | **门禁与合规** | 8 道阻断门；`[spec-locked]` 与 `[operational]` 两档；**导出不许编造**（`aios-compliance-export.py` docstring）；`exception-register.json` |

★ **它自证与自述互不一致（如实登记，不判谁真）**：crate 数 **19／34／36 三个版本**；README 写安装盘与 CI 都还不存在，而实际 8 门全阻断、日志记 ISO 引导全绿；`site` roadmap 标 Rev.5–10 Planned，`.ai/tasks.json` 记部分完成；`002` 同件内层表 REAL vs 子规格 CONTRACT。

---

## 四、它缺的（四类）

### 第 1 类：运行层 —— **合同＋类型＋测试级，不是系统级跑起来级**（详见 §一 八条）

补充：**crate 自述多为 typed core skeleton**（`aios-sgr`＝「Service Graph Runtime typed core skeleton」同族多件）；**23 个 systemd 单元背后是同一个二进制，每槽写完就阻塞**（`DAEMON-ARCHITECTURE.md:46-50` 逐字「run_service_slot is a resident readiness-state scaffold … the per-slot business logic … is not re-litigated」）；**`with_adapter_registry` 39 处调用 38 处在 tests/**；**全仓只有 1 个 `main.rs`**（`aios-renderer-cli`）；`.ai/progress.log` 自报「dm-verity / SELinux ENFORCING boot proof via QEMU still pending (currently permissive)」。

### 第 2 类：它自己写明的未做档

- **Rev.3 全部 S16–S28（28 份合同）：证据级 `E0`、状态 `CONTRACT`**；`003/01_executive_summary.md:65-74` 逐字「specification-complete … It is not yet REAL」；
- **R13.2 密闭构建四条未做到**（`hermetic/README.md:52-72`）；
- **国防就绪 24 项：REAL 19／PARTIAL 3／CERT-NEEDED 2**（TPM 运行时 PCR quote 校验／**全守护进程进受限 SELinux 域只有 1 个 .te**／egress default-deny 只有策略面；UEFI 信任锚与 **FIPS 140-3** 需外部）；
- **`.ai/tasks.json`**：Rev.6 两项 pending／Rev.7·8 in_progress／**Rev.9 生态市场 pending／Rev.10 自治 pending**；
- **`site` 公开 DEFERRED BY DESIGN 七条**（含「无实测不称认证」「IDL 里开开放词汇」）。

### 第 3 类：产品化与生态（缺得最实）

| 项 | 现取 |
|---|---|
| release／tag | ★ **0 ／ 0** |
| stars／forks／issues | **0／0／0** |
| 维护者 | ★ **单一 primary maintainer** |
| CI | ★ 自建 GitLab ⇒ **外部不可复现** |
| 最后 push | **2026-07-19**（此后两个多月无提交） |
| 治理自述 | `GOVERNANCE.md` 逐字「the repository does not yet ship a production runtime」 |

### 第 4 类：语义层（我们的位置）

**没有形式本体层**：`TBox｜ABox｜RDF｜OWL｜SHACL｜SPARQL` 逐目录 **0**（crates／distro／tools／site／002／003 全 0），全仓 15 命中**全在本仓 `ninedim/`**。★ 但它**自称** authoritative **semantic** filesystem ⇒ 口径写「没有形式本体层」，**不写「没有语义」**。

**另外三处「类型/名字各长各的」**：动作名有 **4 套字符串键**（`CapabilityCatalog`／`AdapterManifest.declared_actions`／硬拒引擎硬编码集合／恢复专用硬编码表，另 `aios-terminal` 还有一套硬编码 `infer_action_name`）；**参数在源头退化成字符串**（`TranslateResponse.parameters: HashMap<String,String>`）；**Rust 侧没有任何 `Plan`／`PlanStep` 类型**（`pub struct Plan` **0 命中**），计划只活在 proto 与 `plans: HashMap<String, proto::Plan>`，`DraftPlan` 造**单步**且 `action_draft_ref := intent_id`，注释自称「honest: does NOT fabricate multi-step AI plans」。

---

## 五、★ 我方「必改」清单 —— 按实读改准（v0.2 ⇒ **接线清单**）

| # | 原写（v0.1） | 实读判定 | **改成** |
|---|---|---|---|
| 1 | `action_name` 自由字符串 ⇒ 加本体闸 | **成立**（无封闭词表；`validate_action_name` 0 命中；step_validate 只判空串） | ★ **接线**：把翻译产出接到**已有的 `AdapterActionDeclaration.action_kind` 词表**（权威源→我们本体），补 `REJECTED` 分支；落点＝`adapter_manifest.rs:21-22` 自认欠的 **T-028** |
| 2 | `L7.2` typed action 无类型来源 | **不成立**（该件 `:9` Consumes ＋ `:318-320` 已写明委托 S0.1／S1.3／S2.1） | 删掉；改成接它已指定的三处 |
| 3 | 它没有语义层 | **成立**（6 个目录全 0） | 保留，限定为「没有形式本体层」；载体用 `namespace.rs:77` 已备好的 `/aios/system/capabilities` |
| 4 | 各 daemon 各自说话 | **不成立**（有唯一 Supervisor 口） | 改成「口已在，槽是空壳」⇒ 往派发点里塞语义层 |
| 5 | `aios-evidence`＋state＝第二份留痕 | **不成立**（`aios-evidence` 是全仓那一份，37 依赖） | ★ 改成「**运行时证据与 L0 账本是两条互不相通的链**（§一-3／4）＋ `ApprovalGate.audit_trail` 进程内轨 ＋ `aios-fleet` 分布式 DAG」 |
| **6** | — | ★ **它自己违反 fail-closed** | **必须裁决**：`adapter_registry.rs:452-467` 的 unknown⇒SUCCEEDED vs `CLAUDE.md` 的 fail closed |
| **7** | — | ★ **恢复不许依赖 L5（INV-001）** | 本体**不许**放 `aios-cognitive`（L5）：恢复模式下无本体可查 ⇒ 会把自己的合法动作拒掉 ⇒ **下沉 L2/L3/L4** |
| **8** | — | ★ **多源真值** | `L3_.../01_unit_manifest.md:396` 逐字「The pointer is the source of truth」＋ `XX_.../01_action_envelope_lifecycle.md:574` 逐字「Capability Runtime is the sole writer」⇒ **必须显式裁决** |
| **9（新增）** | — | ★ **策略规则不参与裁决** | `aios-policy/src/pipeline.rs:330-342` 第 6/7 步 stub ⇒ **规则写进 bundle、载入、验签，都不影响任何裁决** |

### ★ 不许动（10 条）

`ObjectKind` 闭枚举＋不可变版本链｜`metadata` 永远非权威、禁 free-form／embeddings 当语义｜`aios-evidence` 只追加／哈希链／封章／427 封闭 RecordType｜指针＝SGR 回滚事实源（CAS）｜**Capability Runtime 是信封 sole writer**｜**恢复不依赖 L5**（INV-001）｜`is_ai_origin`／`cognitive_provenance` 不可伪造｜**不采纳 RDF/OWL 运行时**（我方 B-3）｜SELinux＋`approval_gate` 只合流不拆｜`distro/` **37,518 行**不动。

★ **加一个新组件要动 11 处**（核心 6）：根 `Cargo.toml` members／`aios_system.rs` 的 `SERVICE_ALIASES`＋`EXTRA_SERVICE_IDS`／`composition_engine.rs` 默认 17 服务组合／`build-aios-iso.sh` Step3 二进制落位白名单／`distro/systemd/<unit>`＋`aios.target`＋写进 `DAEMON-ARCHITECTURE.md`／必需时 `aios-security-score.sh`＋`test-rev13-daemon.sh`（＋新脚本进 `.gitlab-ci.yml` shellcheck 清单）。

---

## 六、我们给它带来什么（五条）

| # | 我们带来 | 补它哪一处 |
|---|---|---|
| 1 | **一份法律**（五要素：对象／关系／接口·能力／动作／函数 ＋ 权限面；自定 JSON、可装载、判据会红、身份 vocab_hash） | 它的**类型**散在 proto/schema、**能力**在 adapter manifest（且动作名有 4 套字符串键）、**许可**在 policy packages ⇒ **没有一份共同依赖的** |
| 2 | **接线**：把 §一 八条线接上（未登记即拒／证据进链／策略规则生效／沙箱六源／约束消费／参数类型） | §一 八条 |
| 3 | **一本账 ＋ 三类话**（变更／请求与结果／通告；只追加、旧值不抹） | 它的信封管动作、evidence 管证据 ⇒ **没有把三类话收成一套** |
| 4 | **七问**（尤其**前值**与**什么单位**） | **Rust 侧无 Plan 类型**；前值与单位没有统一位置 |
| 5 | **会红的语义判据** | 它 8 道门全在**发行/合规**面；**语义一致性今天没有判据** |

★ **只对齐不改的四条**：8 道阻断门／`[spec-locked]` vs `[operational]`／导出不许编造／`exception-register`。

---

## 七、未读的面（如实）

1. `crates/` **651 个非测试 `.rs`**：四席合计逐行精读约 25 件；**未读** `pipeline.rs`（108 KB）、`selinux.rs`（94 KB）、`record.rs`（3993 行中 427 变体逐条）、各 crate `tests/`。
2. `002.../` **52 份子规格正文未逐件读**；`003.../` **28 份合同正文未读**；`001.../`（冻结 Rev.1）一件未读。
3. `distro/`：`systemd/` 细读；`build-aios-iso.sh` 只读 Step1–6；28 个 gate 脚本只细读 1 个；`desktop/**` 全未读；`installer/*.sh` 只读 README。
4. `tools/`、`site/`（只关键词）、`003.GRANT_APPLICATIONS/`、`.opencode/`（2 个 tracker 文件，已读）。
5. ★ **未跑任何构建／测试／门禁**（宿主无 cargo／rustc）⇒ 一切「它做到了」均为**它自己的文件自述**，**未独立复算**。
6. ★ **未取上游 git 历史**（本机 git 协议到 GitHub 不通；仓内 clone 是 shallow）。

---

## 八、出处（可复核）

| 说法 | 出处 |
|---|---|
| 十一层 REAL／36 crate／19 里程碑 | `002.../00_MASTER_INDEX.md:21-31`；`Cargo.toml:3-40`；`MILESTONES.md:15-17` |
| 信封／生命周期／翻译器／认知核 FSM | `002.../02_design_decisions.md` DEC-003（:31-53）／DEC-004（:57-61）／DEC-038（:369-） |
| 适配器无 execute／策略 stub／证据双链／沙箱六源 None／约束无消费 | `runtime.rs:76-81,997-1016,355`；`pipeline.rs:1959-1999,976,991,1250,1270`；`aios-policy/src/pipeline.rs:330-342`；`evidence_emit.rs:105-131`；`runtime_adapter.rs:46-58` |
| 无封闭动作词表／validate 缺失 | 651 个非测试 `.rs` 全扫：`pub enum *Action*` 16 命中（无一为词表）；`validate_action_name` 0 命中；`aios-action/src/error.rs:98` |
| AIOS-FS 自称权威语义文件系统 | `002.../L2_AIOS_FS/01_object_model.md:14,113-125,135,164` |
| 证据账本唯一性与 37 依赖 | `aios-evidence/src/lib.rs:5-6`；`aios-fs/Cargo.toml:14`；`segment_chain.rs:12`；`record.rs:110` |
| 能力表在、闸空 | `action_fabric.rs:37-42,131-134`；`adapter_manifest.rs:21-28`；`adapter_registry.rs:328-329,452-467` |
| 唯一 Supervisor 口与空槽 | `distro/systemd/DAEMON-ARCHITECTURE.md:22-31,42,46-50` |
| 影子审计轨 | `crates/aios-capability-runtime/src/approval_gate.rs:203,215-217,261-264` |
| 多源真值 | `002.../L3_.../01_unit_manifest.md:396`；`002.../XX_Cross_Cutting/01_action_envelope_lifecycle.md:574` |
| 恢复不依赖 L5 | `CLAUDE.md`；`002.../XX_Cross_Cutting/03_mvp_golden_path.md:884` |
| 门禁／生命周期／合规导出／例外登记 | `distro/build/ENTERPRISE-EXIT-GATES.md`；`distro/SUPPORT-LIFECYCLE.md`；`distro/compliance/aios-compliance-export.py` docstring |

