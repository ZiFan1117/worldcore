# 底层进程候选清单（二期目标：找有意义的进程 · 借鉴 AI-OS · 把 DSH 融入语义世界）

> 现取：2026-10-20 深夜。截止：**2026-10-21 02:00 Asia/Shanghai**（到点停）。
> 目的：给 worldcore 补**底层缺的进程**，只借 AI-OS 的**形状/职责**（不搬 Rust 代码，AI-OS 的 `crates/` 已从本仓删除，设计在 `001…003` 规格里）。

## 一、现状：我们已有的 9 个进程（含总线）

| # | 进程 | 目录 | 对应 AI-OS 层 |
|---|---|---|---|
| 1 | 总线 | 外部 zenoh（`aios-bus`） | L3 传输面（我们自建） |
| 2 | 本体 | `src/ontology/`（entry＋law/gate/query/govern/ingest） | L4 策略/身份记录 + L9 账 |
| 3 | 计算机 | `src/computer/`（156 命令 + 指标管道） | L3 执行面 + L8 边缘 |
| 4 | 呈现 | `src/presentation/` ＋ Flutter 渲染 | L7 交互面 |
| 5 | 个人空间 | `src/space/`（桌面/窗口/场景/确认/本体窗口） | L7 交互面 |
| 6 | 智能体 | `src/agent/`（DSH 接入） | L5 认知面（外接 DSH） |
| 7 | guard | `src/guard/`（PDP＋Landlock） | L4 策略执行点 |
| 8 | web | `src/web/`（语义浏览器） | L7/L10 入口 |
| 9 | （渲染器） | `aios-presentation-render` | L7 渲染实现 |

**缺口（对着 AI-OS 层看）**：

| AI-OS 层 | 我们有没有「进程」 | 现状 |
|---|---|---|
| L1 Kernel/Bootstrap/**Recovery** | ❌（只有 `scripts/release/world_snapshot.py` 定时器） | 快照/回滚/分叉是脚本，不是世界成员 |
| **L2 AIOS-FS** | ❌ **完全没有** | 文件只在 POSIX；世界不认「文件对象」 |
| L3 SGR（服务图运行时） | ◐ | 有总线＋注册表，没有服务图对象 |
| L4 Policy/Identity/**Vault** | ◐ | 身份/凭证在本体内部；**vault（密钥/秘密）缺** |
| L5 Cognitive Core | ◐ | DSH 外接；世界没有认知进程 |
| L8 Network/Hardware/Devices | ❌ | 只有 `sys.*` 命令（computer 代跑），没有领域进程 |
| L9 Observability/Admin | ◐ | 看门狗/状态是 shell/定时器，不落世界 |
| S28 Constitutional Time Plane | ❌ | 没有「时间面」进程（世界时间靠系统钟） |

## 二、AI-OS 里值得借「形状」的（读的就是仓里 `001/002/003` 规格）

| 来源 | 可借什么 | 用到哪儿 |
|---|---|---|
| **L2 — AIOS-FS**（`002…/L2_AIOS_FS/`） | 文件＝**带版本的语义对象**：内容寻址、路径是**查询视图**、写有 intent/policy/provenance/rollback/evidence；提交不原地覆盖；指针移动即发布 | 我们的 `file` 类/`fs` 进程：先做**只读语义文件服务**（stat/list/hash/read），把「版本/指针」留到写路径二期 |
| **L4 — Policy/Identity/Vault** | 策略、身份、**保险库**三者分家；秘密不落普通对象 | `vault` 候选（二期）：DSH 凭证/密钥进 vault，账里只留引用 |
| **L9 — Observability/Admin** | 证据只增；失败/拒绝也是证据；verification 是**显式类型**并附在动作上 | 我们账已有；候选 `health` 进程把单元/快照/看门狗读数变成世界对象 |
| **L1 — Recovery** | recovery boundary：可 inspect、可回滚、可 quarantine | `recovery` 候选：把快照/恢复演练做成世界成员动作 |
| **S28 — Constitutional Time Plane** | 时间面是宪法级（单调、不可回拨、可审计） | `clock` 候选：世界时间/心跳/时区进世界 |

## 三、候选打分（截止前 3 小时，选**一**个先落地）

| 候选进程 | 价值 | 缺口 | 可借鉴度 | 风险 | 3h 内可完成 | 结论 |
|---|---|---|---|---|---|---|
| **fs（语义文件）** | 高：作者要文件查询、DSH 要读文件、语义浏览器要浏览 | 10 | 10（L2 全套形状） | 4（只读先做） | 9 | ★ **选它** |
| vault（秘密/凭证） | 高：DSH 凭证、redaction 债 | 10 | 9（L4） | 7（安全） | 5 | 二期 |
| recovery（快照成员） | 高：P4 世界连续性 | 8 | 10（L1） | 4 | 8 | 二期 |
| clock（时间面） | 中：账时间权威 | 8 | 8（S28） | 3 | 9 | 二期 |
| health（可观测成员） | 中：单元/快照/看门狗进世界 | 7 | 6（L9） | 3 | 9 | 二期 |
| network/device | 中：网络/设备状态 | 9 | 7（L8） | 7 | 4 | 二期 |

## 四、二期第一件：`fs` 语义文件进程（v1 只读）

### 4.1 做什么

```
src/fs/                       ← 一进程一夹（C28）
├─ fs_process.py              入口：报到/注册/订阅 ask、执行、回账（只读）
├─ fs_ops.py                  纯函数：resolve_root / list_dir / stat_file / hash_file / read_text（好测）
└─ README.md                  干什么、不干什么、权限边界
```

- 法（`world.json`）新增：
  - 类 `file`：`path`(主键/STRING)，`name`、`size`(INTEGER)、`mtime`(STRING)、`sha256`(STRING)、`kind`(STRING 选项 file/dir/link)、`root`(STRING 选项：aios/root/home…)、`text_preview`(STRING，脱敏/截断)；
  - 动作 `file.stat`、`file.list`、`file.hash`、`file.read_text`（只读；grant scope：人/agent？先 human＋agent/dsh，只读；路径限制在**白名单根**）；
  - 类 `fs`：进程自身个体（name/state/roots），报告者 `world://fs`。
- 进程行为：`world/appear fs` → `world/register file.*` → 订 `world/ask`/`world/exec`（route=fs）→ 执行只读操作 → 回 `world/ask/result`，本体落账/事件；**不写文件**（v1）。
- DSH 融入：agent/DSH 通过 `world/ask file.list/file.read_text` 查文件（不再自己绕开世界读盘）；`world_cli.py` 已能发 ask，补一个 `fs` 查询示例/文档。
- 验收：新判据 **C69**（先写会红反例：越界路径、未知动作、缺参、非只读动作、符号链接逃逸）；VM 部署 `aios-fs.service`，看门狗单元 9→10；现取：appear/register/一次 file.list/一次 file.read_text 的账与返回。

### 4.2 明确不做（v1）

- **不写**文件（写路径＝动作+permit+版本化，二期借 L2 的「内容寻址/指针移动」）；
- 不做完整 AIOS-FS（FUSE/内核投影/CRDT 冲突）；
- 不替换 computer 的 `sys.*` 文件命令（那是系统管理面，fs 是**世界语义面**）。

## 五、下一步（按截止推进）

1. **本轮之后**：写 C69 反例（先红）→ `file`/`fs` 法条目 → `src/fs/` 骨架（纯函数＋入口）→ 本机判据绿；
2. 部署 VM（unit、deploy.sh、watchdog 9→10），现取 appear/register/查询账；
3. DSH 融入：`world_cli` 加 `fs` 用法示例 + agent 提示词补「文件先问世界」；docs 更新；
4. 02:00 前收尾：终报、交接（`docs/process-candidates.md`＋HANDOFF）。

## 六、边界（如实）

- 本清单是**候选与设计**，不是已实现；`fs` 进程是二期第一件，3 小时内只做只读 v1；
- AI-OS 的 `crates/` 已删，我们不能直接搬代码，只借规格里的**职责/不变量/对象模型**；
- 截止到 **2026-10-21 02:00 Asia/Shanghai**；到点停，不再开新进程。
