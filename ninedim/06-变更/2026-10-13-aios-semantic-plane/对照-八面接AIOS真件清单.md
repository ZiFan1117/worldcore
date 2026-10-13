# 核对（作者令）：八面还没接 AIOS 真件 —— 清单与抄法

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S3 | 执行 | 五 证据 | **1.0（现取核对）** |

> **作者令（逐字）**：「你**核对一下**，就是按照我们那个源码，就是 **AI native OS 的这个没有实现的功能**，就是我们代码现在**新写的代码没有实现的功能，全部都实现了**。按照他的**直接抄就行**……**他该哪个东西是怎么样子的，该抄就抄就行**，就按那个什么**执行啊**，什么等等等等方面啊，抄进去就行。然后呢，我说的**不是说其他的啊，就是围绕本体它有的这几块直接抄就行**。」

---

## §一 ★★★ 核对结果：**接口在（照 P），背后没接 AIOS 的真件**

| 我们的面 | ★ 现状（现取） | ★ AIOS 的真实现（现取关键 pub 类型） |
|---|---|---|
| **② 实例注册** | ★ 内存 `BTreeMap`（`Instances`） | ★ `aios-fs`：**`AiosFs`**／`AiosFsService`／`FsContext`／`FsEnumerator`／`FsError` |
| **③ 校验** | ★ 内存规格表（`ObjectSpec`） | ★ `aios-policy`：**`Decision`**／`DecisionPipeline`／`DecisionCache`／`DecisionLog` |
| **④ 实例存储** | ★ 内存 `Vec<Row>` ＋ 折出现状 | ★ `aios-fs`：**`AiosFsService`**／`FsContext`（版本链） |
| **⑤ 查询** | ★ 内存过滤／排序／取前 N | ★ `aios-fs`：**`FsEnumerator`**（＋ `query_eval`） |
| **⑥ 账** | ★ 内存 `Vec<Event>` | ★ `aios-evidence`：**`ReceiptChain`**／`ReceiptBuilder`／`InMemoryEvidenceLog`／`RocksDbEvidenceLog`／`CompactionPolicy` |
| **⑦ 执行** | ★ 只有 `DryRun`（**明写"不是已经会做了"**） | ★ `aios-capability-runtime`：**`ActionDispatcher`**／`ActionFabric`／`ActionLifecyclePipeline`／`ActionContext`／`ActionIntent`（74 个关键类型） |
| **⑧ 治理** | ★ 内存角色／授权表 | ★ `aios-policy`：**`DecisionPipeline`**／`Namespace`（＋ `aios-vault` 的角色） |
| **翻译** | ★ **已接**（`gate_action_name`） | ★ `aios-cognitive`：`RoutingDecision`／`IntentCapability` |

⇒ ★★★ **即：★ 作者说的"没有实现的功能"，就是"接口在、真件没接"** ✓

## §二 ★★★ "抄"的正确落法（结论：接口照 P、实现照 AIOS）

| 做法 | 结果 | 判 |
|---|---|---|
| **甲** 只加依赖、把 60,000 行全拉进来 | 依赖极重 | ★ 不行 |
| **乙** 把 AIOS 的类型定义在本仓重写一份 | ★ **又是重复**（作者先前点出的病） | ★ 不行 |
| ★★ **丙：加依赖 ＋ 只包必要的那几个真件** | ★ **`aios-fs` 的 `AiosFs`／`aios-evidence` 的 `ReceiptChain`／`aios-policy` 的 `DecisionPipeline`／`aios-capability-runtime` 的 `ActionDispatcher`** | ★★★ **取这个** |

⇒ ★★★ **一句话**：★ **接口照 P（名字与语义）；实现照 AIOS（用它现成的件）** ✓
⇒ ★ 这正是作者上一条澄清（`澄清-两个参考源.md`）的同一条道理 ✓

## §三 ★ 逐面的"接法"（第一批，待实现）

| 面 | ★ 接谁 | 怎么接（薄包装） |
|---|---|---|
| ② 实例注册 | `aios-fs::AiosFs` | ★ `Instances` 内部持一个 `AiosFs`；`register` 走它的写入口 |
| ③ 校验 | `aios-policy::Decision` | ★ 校验结果用 `Decision` 表示（而不是自造） |
| ④ 存储 | `aios-fs::AiosFsService` | ★ `Store` 内部持它；只追加与版本链用它现成的 |
| ⑤ 查询 | `aios-fs::FsEnumerator` | ★ `Query` 转成它的枚举口 |
| ⑥ 账 | `aios-evidence::ReceiptChain` | ★ `Ledger` 内部持它；`append` 走 `ReceiptBuilder` |
| ⑦ 执行 | `aios-capability-runtime::ActionDispatcher` | ★ `Exec` 把 `Executor` 的实现换成它 |
| ⑧ 治理 | `aios-policy::DecisionPipeline` | ★ `Governance::can_execute` 转成它的判定 |

★ **接口不变**（★ 八面对外的 API 照 P 用）★ ⇒ ★ **调用方不用改** ✓

## §四 本件没做的事（如实）

1. ★ **没写**任何"接 AIOS"的代码（★ 本件只出清单与接法）；
2. ★ **没核**每个真件的**具体构造与入参**（★ 那是逐面接的时候要读的）；
3. ★ **没定**各面是否需要新加依赖（★ 例如 `aios-policy` 会不会拉进一堆东西）—— ★ 要一个个试。
