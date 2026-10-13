# 总账：37 个 crate 的关联、"必须吗"、以及与本体重复的真相

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 | **0.1（现取总账·待裁）** |

> **作者问（逐字）**：「我感觉他的这 36 个和**我们一是本体有冲突**，二是**他这 36 个都是必须的嘛**……**你这 36 个哪些是相互关联的**？……**我们的那个和这个核心底座里面的好多个都重复了，和这个存储和运行也重复了，和认知与 SDK 好像也重复了。这该怎么办**」
> **★ 先更正一个数**：★ **实际是 37 个**（★ 上游原有 **36** ＋ 我方新增 **1**（`aios-ontology`））—— ★ 本席先前沿用上游文档的"36"**没核**，认。

---

## §一 ★★ 关联：三层（现取：谁被多少 crate 依赖）

| 层 | crate | 被依赖数 |
|---|---|---|
| ★★ **真底座** | `aios-action`／`aios-evidence`／`aios-policy` | ★ **32**／**32**／**26** |
| ★ **中坚** | `aios-sandbox`(12)／`aios-capability-runtime`(11)／`aios-cognitive`(9)／`aios-recovery`(7)／`aios-apps`(7)／`aios-distribution`(6)／`aios-vault`(6)／`aios-fs`(5)／`aios-sgr`(4) | 4–12 |
| ★ **顶层**（大量依赖别人、几乎不被依赖） | `aios-integration`（**依赖 21 个**）／`aios-renderer-cli`(12)／`aios-autonomous`(9)／`aios-backup`(9)／`aios-recovery`(8)／`aios-sgr`(8)／`aios-container`(7)／`aios-renderer-web`(7) | — |

★ **孤立 crate（不依赖 aios-* 也没被依赖）＝ 0 个** ⇒ ★ **都连在同一张图上**。
★ **`aios-ontology` 的位次**：★ **不被任何 crate 依赖**（＝ 两席早先查到的「**0 读者**」）⇒ ★ **它今天是"挂着的"**。

## §二 ★★ "37 个都是必须的吗" —— 数据说：不都是

| 现象 | 现取 |
|---|---|
| ★ **一个测试都没有的 crate** | ★ **14 个**：`aios-fleet`／`aios-autonomous`／`aios-container`／`aios-ebpf`／`aios-terminal`／`aios-sdk`／`aios-renderer-voice`／`aios-hardening`／`aios-marketplace`／`aios-control-center`／`aios-eval`／`aios-mobile`／`aios-backup`／`aios-time` |
| ★ **很薄的**（< 6000 行） | ★ **16 个**（最小 `aios-ontology` 512 行 ← 我们的；`aios-time` 870；`aios-backup` 963；`aios-mobile` 966；`aios-eval` 1061；`aios-control-center` 1129；`aios-marketplace` 1486；`aios-design-tokens` 1490…） |
| ★ **很厚的** | ★ `aios-capability-runtime` **43,853 行**／320 个 pub 项；`aios-distribution` 18,556；`aios-integration` 18,329；`aios-apps` 17,844；`aios-evidence` 17,093；`aios-cognitive` 17,005 |
| **合计** | ★ **327,490 行**／**2,457 个 pub 项** |

⇒ ★★ **结论（本席判读）**：★ **不是"都必须"** —— ★ 承重的是**底座 3 个 ＋ 中坚 9 个**；★ **其余多是"按规格建好的骨架"**（★ 14 个连测试都没有）。
⇒ ★ **但"砍不砍"不是我们能随手定的**：★ 它们是**上游按 S1–S28 规格建的产品骨架**，★ 且作者原话说「**其他的人家都验证过了**……看其他的能不能全部运行起来」⇒ ★★ **我们的路是"接进去"，不是"砍掉"** ✓

## §三 ★★★ "重复"的真相（你要的硬证据）

### 证据一：真·同名重复**很少**（3 个）

| 名字 | 出现在几个 crate | 是哪几个 |
|---|---|---|
| `SubjectRef` | **6** | `aios-apps`／`aios-cognitive`／`aios-fs`／`aios-sandbox`／`aios-vault`／`aios-verification` |
| `EvidenceReceipt` | **4** | `aios-evidence`／`aios-hardware`／`aios-integration`／`aios-network` |
| `SecurityProfile` | **3** | `aios-capability-runtime`／`aios-fleet`／`aios-integration` |

★ 全仓 **1610** 个 pub struct/enum 里，跨 crate 同名的只有这 3 个 ⇒ ★ **"上游自己之间"的真重复不多**。

### 证据二：★ **同概念、各 crate 各定义一遍**（这才是你说的"重复"）

| 本体概念 | 上游散落在哪些 crate | 名字（举例） |
|---|---|---|
| `service`（系统服务） | ★ **5 个 crate** | `capability-runtime`: ServiceClass／ServiceHardeningPolicy；`integration`: ServiceComposition／ServiceDependency／ServiceHealthSummary／ServiceScaffoldStatus；`hardening`: ServiceProbe／ServiceResult；`sgr`: ServiceUnit |
| `device`（设备） | ★ `aios-hardware` 一家 **5 个** | DeviceClass／DeviceId／DeviceLifecycleState／DeviceTrustClass／DeviceQuarantineReason |
| `port`（端口） | ★ 2 个 | `network`: PortPolicy；`container`: PortSpec |
| `surface`（屏面） | ★ 1 个 | `renderer-kde`: SurfaceFilter／SurfaceReleaseReceipt |
| `agent`（智能体） | ★ 2 个 | `autonomous`: AgentBinding／AgentRole；`eval`: AgentRole |

### ★★★ 证据三：**每个 crate 都自己造了一套"种类词表"**（67+ 个）

| crate | 它自己的种类枚举 |
|---|---|
| `aios-fs` | ObjectKind／NamespaceClass／PointerKind／ConsistencyClass／ConflictResolutionKind |
| `aios-apps` | PackageKind／PackageObjectKind／PackageContentKind／FailureClass／KnownIssueClass／EcosystemHonestyClass／RecipeTrustClass／OrchestrationKind |
| `aios-hardware` | DeviceClass／DeviceTrustClass／GpuVendorKind／BusKind／FirmwareUpdateClass |
| `aios-capability-runtime` | ActionDispatchKind／ServiceClass／DriverClass／QueueClass／AvcDecisionKind |
| `aios-network` | AllowlistEntryKind／InboundExposureClass／OutboundDirectiveKind |
| `aios-sgr` | AdapterCapabilityClass／AdapterDispatchKind／ConflictKind／DependencyKind／HealthCheckKind |
| `aios-distribution` | PackageKind／RepositoryKind／ExternalRepoKind |
| `aios-renderer-kde` | NodeKind／NodeSurfaceKind |
| `aios-policy` | ApproverClass／HardDenyClass |
| ★ 其余 | `aios-vault`: CapabilityClass／OverrideClass；`aios-cognitive`: ModelBackendKind／ProviderClass；`aios-sandbox`: IsolationKind；`aios-ebpf`: DesktopEventClass；`aios-terminal`: ProposalRiskClass；`aios-fleet`: RemoteRoutingClass；`aios-hardening`: ProbeClass；`aios-waydroid`: AndroidGPUClass；`aios-eval`: EvaluationMetricKind；`aios-fs`: ObjectKind… |

⇒ ★★★ **即：上游 36 个 crate 各自有"种类清单"，彼此之间没有统一的名词表** —— ★★ **这就是你感觉到的"重复"的真正形态** ✓

## §四 ★★ "该怎么办"（本席的方向建议，待人裁）

★ **先说：不是"合并 crate"、也不是"砍 crate"** —— ★ 重复的形态有三种，处置不同：

| 形态 | 例 | ★ 处置 |
|---|---|---|
| **甲：同名同义（真重复）** | `SubjectRef`(6)／`EvidenceReceipt`(4)／`SecurityProfile`(3) | ★ **收敛到一个底座**（★ 例如 `SubjectRef` 该只有一个家） |
| ★★ **乙：同概念、多名（最普遍）** | `service` 散在 5 个 crate；`device` 散在 hardware 5 个类 | ★★ **这正是"本体该管的事"** —— ★ **本体给统一概念，各 crate 的类当作"实现面"** |
| ★ **丙：各 crate 自己的种类枚举**（67+） | `ObjectKind`／`NodeKind`／`PackageKind`／`DeviceClass`… | ★★ **本体 = 权威名词表**；★ 这些多数是**取值域**（★ 正是我们刚判过的"取值域"概念） |

### ★★ 建议的三步（与已定的线一致）

| 步 | 做什么 | 落在哪个任务 |
| **1** | ★ **出一张"名词总表"**：★ 把 67+ 个 `*Kind`/`*Class` 与本体九类**逐条对照**（哪个是"世界里的东西"、哪个是"取值域"、哪个是"实现细节"） | ★ 新任务（**T-82**） |
| **2** | ★ **定口径**：★ **本体类 = 世界里的东西**；★ **crate 的 `*Kind` = 取值域或实现细节** | ★ 接 `_types.value_types`（★ 我们刚立的 `record_kind` 是第一个样板） |
| **3** | ★ **接进去**：★ 让 crate 的种类枚举**指出**它属于本体哪一类（★ 而不是各说各话） | ★★ **T-28**（闸常开 ＋ 41 条并入本体）／**T-30**（未登记即拒） |

## §五 本件没做的事（如实）

1. ★ **没做"名词总表"**（★ 只给了形态与样例，★ 逐条对照是 T-82）；
2. ★ **没核** 37 个 crate 与 **08 侧**的对应（★ 那是另一仓）；
3. ★ **没判** 67+ 个枚举里哪些"该留哪些该并"（★ 需先有第 1 步的总表）。
