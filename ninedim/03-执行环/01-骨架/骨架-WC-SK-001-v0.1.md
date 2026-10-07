# WC-SK-001 骨架跑通验证记录

| 项 | 内容 |
|---|---|
| 文档编号 | `WC-SK-001-v0.1` |
| 适用阶段 | S3 骨架 |
| 编制人 / 日期 | AI（DeepSeek Harness）/ 2026-09-26 |
| 审核 / 批准 | `<待人工>` / — （**R3 骨架跑通评审的输入，非结论**） |
| 覆盖范围 | **项目 Step 0.5 / 1 / 2 / 5 / 7 / 8**（骨架一次跑通；项目 Step 3 检查点、项目 Step 6 通道未做） |
| 代码版本 | **`b1d4b923d19c1aef8dcdf93ebb5c5782c71c96bc`**（R2 签署提交；`framework/v0.1` 附注标签指向它） |
| 入口 | **`bash check.sh.new`**（本条即 `REQ-N-004` 的验收判据 `TC-022`） |
| 执行环境 | VM `newworld`：Linux `7.2.6-arch2-1`；`cargo 1.98.1` |

> **裸 `Step N` 视为无效引用**——本文件引用 Step 处一律写「项目 Step N」或「上游 Step N」；对照表唯一权威处 = `WC-MODREG-001` §2.2，其他文档只引用、不复写对照表。

> **S3 准出的判据是"干净环境一条命令跑通"**（`WC-SQAP-001` §6 S3 行）。
> 本记录给出那条命令与它的原始输出；**结论由 R3 人工评审作出**。

---

## 一、（**⚠ 本节所载输出已过期**）

> **标注（2026-09-27，承独立核实 N5）**：本节留档是**旧版 `check.sh` 的输出**；现行 `check.sh` 为 **121 行**、步骤 ①–④＋③b/⑤/⑥/⑦，**以本文档「附：骨架跑通实测」节与提交号复算为准**（`cd world-core && bash check.sh`）。本节**只增不减**，原文保留。

## 一、原文如下

一条命令及其原始输出

```
$ cd /root/world/world-core && bash check.sh
== world-core check.sh ==
  目录 : /root/world/world-core
  主机 : Linux 7.2.6-arch2-1
  工具 : cargo 1.98.1 (797e8a9bc 2026-08-05)

── ① 构建（--locked）────────────────────────────────────────
  ✅ 构建通过

── ② 骨架冒烟（沙箱账本：/tmp/tmp.XXXXXXXX）──────────────────
  == world-core check ==
    本体 : .../ontology.json  world=1  家族=["act", "change", "notice"]
    门禁 : .../policy.json  policy=1  能力=8 个  主体白名单=["world://user", "world://agent/*"]
    账本 : .../ledger.jsonl  条数=0  next_seq=1
    READY
  ✅ READY（本体/门禁/账本三项都开得起来）

── ③ 三条专属验收测试（WC-SQAP-001 §2.4）─────────────────
  running 3 tests
  test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 14 filtered out
  ✅ 追加→读回 / 重启→还在 / ★删读模型→重算一致

── ④ 投影与同源核对（REQ-F-018/019/020）──────────────────
  语言投影首行: #world-core projection=language world=1 vocab=fnv1a64:6a96abfa9a969462 last_seq=2 state=fnv1a64:a2093a927e613f43
  视觉投影首行: #world-core projection=visual world=1 vocab=fnv1a64:6a96abfa9a969462 last_seq=2 state=fnv1a64:a2093a927e613f43
  == world-core project check ==
    词表 : fnv1a64:6a96abfa9a969462（世界版本 1）
    状态 : last_seq=2 指纹=fnv1a64:a2093a927e613f43
    同源 : ✅ 语言投影与视觉投影一致（同一读模型 + 同一词表）

== 结论：全通过（构建 / 冒烟 / 三条专属测试 / 投影同源）==
```

**沙箱账本路径被刻意保留成 `/tmp/tmp.XXXXXXXX`**：它是 `mktemp -d` 产物、退出即删，
每次不同——**不是**可比的稳定指纹（对比 `WC-RE09-003` §四 对账本哈希的同一说明）。

---

## 二、这条命令**证明了什么**（逐项对应需求）

| 步骤 | 证明了 | 需求 |
|---|---|---|
| ① 构建 | 锁依赖可复现构建（`--locked`） | `REQ-N-002`（依赖纪律） |
| ② 冒烟 | **本体 + 门禁 + 账本三者都能起来**，并打印 `READY`；沙箱账本由核心自己创建（顺带过静态墙） | `REQ-N-003`、`REQ-F-003` |
| ③ 三条专属测试 | 追加→读回 / 重启→事件还在 / ★删读模型→重算一致 | `REQ-F-001/003/010/011/012/022` |
| ④ 投影同源 | 两份投影**逐字一致的同源头**（同一 `vocab` + 同一 `state`），`project check` 判定通过 | `REQ-F-018/019/020` |
| 入口本身 | **干净环境一条命令跑通** ⇒ `REQ-N-004` 的判据 | `REQ-N-004`（`TC-022`） |

---

## 三、纪律声明（这个脚本**不**做什么）

1. **绝不触碰真实账本**：全程只用 `mktemp -d` 的一次性沙箱，`trap ... EXIT` 退出即删
   （依 `06-swe-gb` 幂等口径修订：命令幂等，数据操作天然不幂等）；
2. **不做"全绿宣传"**：它跑的是**可失败**的检查——构建失败、未打印 `READY`、
   任一专属测试失败、同源判定失败，**任一步即 exit 非 0**（与 CI 同为阻断式）；
3. **不替代 CI**：它是**本地/VM 侧**的同一批判定；CI 的 `smoke`/`unit-test`/`traceability`
   由 `.github/workflows/world-core-gate.yml` 执行，两侧互为印证（见 `WC-CIVER-001`）。

---

## 四、遗留（不假装满足）

| # | 事项 | 现状 |
|---|---|---|
| 1 | **项目 Step 3 检查点（`M08`）** 未实现 | 骨架覆盖到 项目 Step 8，但检查点仍是空号（`WC-MODREG-001` §二 标 ⛔） |
| 2 | **项目 Step 6 通道** 未实现 | `IF-006` 待建；因此 CLI 仍是**唯一**入口，也是唯一"未验证的通道" |
| 3 | **`linux.ps1` 未入库** | `WC-SCMP-001` §8.4 **G-07** 仍未关闭（`check.sh` 已入库，`linux.ps1` 在仓库外 `D:\Code\`） |
| 4 | 覆盖率未度量 | `WC-SQAP-001` TBD-08 |
| 5 | 本记录**未经人工审核** | R3 骨架跑通评审须由人作出准出结论 |

---

## 五、追溯

| 方向 | 条目 |
|---|---|
| 上游 | `WC-SQAP-001` §6（S3 准出判据④"干净环境一条命令跑通"）、§2.4（三条专属测试）、§7.3（RE-09）；`WC-SDP-001` §3.4；`WC-HLD-001` |
| 下游 | **R3 骨架跑通评审**；`WC-RE09-003`（逐条用例结果）；`WC-CIVER-001`（CI 侧证据） |
| 产物 | `check.sh.new`、`tests/{acceptance,contract}.rs`、`src/**` |

---

## 附：**骨架跑通实测**（S3 判据「**一条命令在干净环境跑通**·CI 可复现」）

> **本节四要素齐**（命令／原始输出／环境版本／提交号）；**全部在 Linux VM（`ssh world`）真跑**，本机无 `cargo` 故不作数。

### 环境版本（element ③）

| 项 | 实测值 |
|---|---|
| `rustc --version` | `rustc 1.98.1 (48a229cea 2026-09-01)` |
| `cargo --version` | `cargo 1.98.1 (797e8a9bc 2026-08-05)` |
| 内核 / 架构 | `Linux 7.2.6-arch2-1` / 8 核 |
| VM 工作副本 | `/root/world`（由 `vm` 远端推送同步；**工作副本本身非 git 仓库**，故提交号取本地并已双远端回读同值） |

### 提交号（element ④）

`b1d4b923d19c1aef8dcdf93ebb5c5782c71c96bc`（R2 签署提交；`framework/v0.1` 附注标签指向它，标签对象 `b0360d4593b0d884a7e55d66d236cdd4abdea181`）

### 命令与原始输出（element ①②；**本节为节选**，完整输出见下注）

> **口径订正（依 R3 席 S3-02／S3-05 实测）**：本节**是节选而非全量**；`bash check.sh` 现行 **121 行**、步骤 ①–④＋③b/⑤/⑥/⑦，其**末行结论**为「…契约测试 / 纯文本审计 / 系统级验收 / S1 验证面补建）==」。若需全量，请按「提交号取树 → `cd world-core && bash check.sh`」自行复算。**前置依赖（补登记）**：`bash`、`python3`（步 ⑤/⑦ 用）、`cargo`／`rustc`；**构建需可联网取包**（空 `CARGO_HOME` ＋ `--offline` 实测 rc=101），锁定文件 `Cargo.lock` **已入库**（依赖仅 `serde_json` 及其传递闭包）。

```
$ cd $HOME/world/world-core && cargo build --release --locked
   Compiling memchr v2.8.3
   Compiling itoa v1.0.18
   Compiling world-core v0.1.0 (/root/world/world-core)
    Finished `release` profile [optimized] target(s) in 6.61s

$ ls -l target/release/world-core
605032 target/release/world-core

$ ./target/release/world-core project language | head -3
#world-core projection=language world=1 vocab=fnv1a64:6a96abfa9a969462 last_seq=0 state=fnv1a64:bfe5a6d1cc805a56
rc=0

$ bash check.sh
check.sh rc=0
== 结论：全通过（构建 / 冒烟 / 三条专属测试 / 契约测试 / 投影同源 / 纯文本审计 / 系统级验收 / S1 验证面补建）==
```

### CI 可复现（判据第二条）

`.github/workflows/world-core-gate.yml` 的 5 个作业（gate-self-test / scope / smoke / traceability / unit-test）与上表命令同源；工作流在 `working-directory: world-core` 下执行，**与 VM 实测同一组命令**。⚠ **RTM 严格模式仍为 `"false"`**（`ci_self_check.py` 每轮报此告警）——**该翻转属独立事项，未静默改**。

### 阶段依据（**国标无独立 S3 阶段，如实标注**）

`GB/T 8567-2006` **未设**「骨架跑通」独立阶段；本阶段的**依据是流程库**（`06-swe-gb` 的 S3 骨架跑通评审：准入＝框架基线已建立、骨架代码已提交含构建脚本；准出＝一条命令在干净环境跑通、CI 可复现）。**引用级别：仅 MD 层（无页码锚点）**——标准正文本库为无文本层重排件，按纪律**不冒充页码锚点**。
