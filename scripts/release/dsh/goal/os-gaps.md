# 作为「一个 OS」还缺什么 —— 外文/论文对表（2026-10-19 夜）

> 用途：回答作者的问题「作为一个 OS 它还缺什么事」。左边是别人已经写清楚的 OS 职责，右边是我们这套 worldcore 的现状与缺口。
> 来源见文末；「必须/值得/可缓」是我们的初判，可商量。

## 一、对表（OS 职责 → 我们现状 → 缺什么）

| # | OS 该有的 | 我们现状 | 缺什么 | 初判 |
|---|---|---|---|---|
| 1 | **进程/作业管理**：创建、调度、优先级、配额、生命周期 | 7 个常驻单元（bus/ontology/computer/presentation/render/space/agent）；**没有**按需起进程、没有调度器、没有 cgroup 配额 | 按需起进程；作业队列/优先级；每 agent 的资源配额 | **必须（下一步）** |
| 2 | **内存/对象存储**：持久化、GC、版本、大对象 | 本体 store ＋ 只追加账；对象更新/撤下写路径未齐；大对象货运道未做 | 持久化/GC/版本链；大对象（文件/图像）通道 | **必须** |
| 3 | **文件系统/应用包**：命名空间、打包、安装 | 应用＝A2UI 帧（生成式），无应用包/场景文件；DSH 用仓库目录 | 场景/应用定义文件（P3）；安装/版本/回滚 | 值得 |
| 4 | **IPC/总线**：谁能发/收 | zenoh 总线＋`world/*` 话题；**总线 ACL 未配**（任何本机进程可发任意话题） | 总线 ACL；进程身份与话题授权 | **必须** |
| 5 | **身份/权限/审批**：认证、授权、审计 | 票/凭证/许可/账/拒绝码闭环已硬；**人确认四格未定**、委托未做 | 人确认队列；委托（谁授/范围/时限/可撤）；审批也是账行 | **必须** |
| 6 | **安全隔离/沙箱**：内核/用户态、最小权限 | 我们用 DSH `danger-full-access`（为让它自己改环境）；本体闸只是逻辑闸，不是进程隔离 | 每 agent 沙箱（workspace-write 起）；提权走审批；OS 级隔离（容器/微虚拟机） | **必须（安全债）** |
| 7 | **语义状态/可观测**：进程、窗口、对象的状态可读 | `presentation.state`/`space.state` 已可问；账/日志/看门狗有 | **实时事件流（P8）**；活动窗口；指标/追踪（metrics/trace） | **必须** |
| 8 | **恢复/回放/升级**：快照、回滚、OTA | 看门狗＋last-good 快照＋git 回滚；DSH 目标链每轮快照 | **世界级快照/回放/分叉（P4）**；系统升级/迁移 | **必须（P4）** |
| 9 | **时间/事件/定时任务** | DSH 用 systemd timer（外部）；世界里没有定时器/事件订阅 API | 世界内定时器；事件订阅（人/agent 双向） | 值得 |
| 10 | **UI/壳/输入** | A2UI＋genui 渲染；亮色主题；桌面/窗口/登录 | 多用户同屏；输入法/中文输入体验；通知/声音；组件主题打磨 | 值得 |
| 11 | **多用户/并发** | 单用户 `space/zhang`；agent 行算当前空间 | 多 space/多用户；并发写；隔离 | 远期 |
| 12 | **事务/崩溃一致性** | 账只追加；store 无事务；重启恢复靠账 | 状态写事务/回滚；崩溃一致性验证 | 值得 |
| 13 | **自我进化/判据护栏** | DSH 目标链能改代码/法并自验 `export-law --check`；**但 44 条判据只在宿主、VM 上没有 scripts/test** | **判据在 VM 可跑**（或做成「判据服务」经本体请求）；否则 agent 的进化缺护栏 | **必须（最急）** |
| 14 | **记忆/上下文** | 宿主 Hindsight 记忆；VM 靠 goal/research/board 文件 | VM 侧长程记忆（跨轮/跨重启）；任务轨迹沉淀 | 值得 |
| 15 | **设备/驱动** | computer＋sysknife 执行系统动作；设备语义在 08（不参与） | 13 范围内暂不做设备本体 | 可缓 |
| 16 | **网络/跨机** | 仅本机（总线 localhost）；DSH 可访问 GitHub | 跨机/分布式（多 VM 世界） | 远期 |
| 17 | **能耗/电源/安全底线** | 无 | 电源策略；安全底线（INV）落地 | 可缓 |

## 二、按「OS 还缺什么」排的三步（给 VM agent）

1. **最急：判据护栏**——把 `scripts/test/`（或至少 C27/C44 一类）以只读方式放到 VM，让每轮自优化能自己跑判据；否则「改完怎么算好」只靠 export-law 不够。
2. **事件流（P8）**：`world.event` 双向推（人看得见 agent，agent 看得见人）＋活动窗口——这是「OS 可观测」的核心。
3. **安全债**：把 DSH 从 `danger-full-access` 收回到 `workspace-write` ＋ 按需提权（审批）；否则一个 agent 就能绕过本体闸改系统。

## 三、来源（贴近我们理念的文章/件）

- AIOS: LLM Agent Operating System（调度/内存/存储/工具/系统调用）— https://ar5iv.labs.arxiv.org/html/2403.16971v3
- Comprehensive Survey of LLM-based Agent Operating Systems — https://doaj.org/article/b1b5b901008540628ba8fcb0b6318ad4
- AgentiOS: Intent-Oriented Secure OS Architecture for Autonomous AI Agents — https://browse-export.arxiv.org/pdf/2606.21129
- Agent libOS: Library-OS-Inspired Runtime for Long-Running, Capability-Controlled LLM Agents — https://arxiv-org.ezproxy.obspm.fr/html/2606.03895v1
- Redefining Operating System Design: Integrating LLMs as Core Components — https://ieeexplore.ieee.org/document/11115792
- String: An Agentic OS Where Every App Is a Markdown File — https://arxiv-org.ezproxy.obspm.fr/html/2608.28027v1
- A2UI v0.9（Google）— https://developers.googleblog.com/a2ui-v0-9-generative-ui/
- Persistent Recursive Worlds（自主软件演化）— https://export.arxiv.org/pdf/2608.10450
- LUMOS：面向 agent 的语义 OS 层 — https://www.semanticscholar.org/paper/LUMOS%3A-A-Semantic-Operating-System-Layer-for-AI-Thota/516a37229eecc8634fb88b87ef182c3be762a9aa
- Agentlas-OS（执行门控）— https://github.com/agentlas-ai/Agentlas-OS/blob/main/README.ja.md
- AutoFyn（长程专家迭代）— https://export.arxiv.org/pdf/2609.05446


## 四、本仓规矩（作者 2026-10-19 夜）

1. **产品名：`worldcore`**——不叫 AI-OS；界面标题/README/单元描述写 `worldcore`；上游名只留在来源声明。
2. **进程＝独立文件夹**：每做一块（例如事件流）就 `src/<进程名>/`，一进程一夹（C28）；进程内把本体流程走完：**报个体 → 注册动作 → 订阅总线 → 经本体回话/记账**。
3. **大块分轮**：一次一轮只做一个进程/一块；每块都要「改了什么、怎么验、回滚点」。
