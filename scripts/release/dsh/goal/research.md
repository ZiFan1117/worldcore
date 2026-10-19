# 外部研究：别人在做什么「有意义的」东西（2026-10-19 夜）

> 用途：给 VM 里的 DSH agent 做「设计点」参考；每点后面写「对我们这套 OS 是否必须」的初判（**可商量，不是命令**）。

## 一、六个可借鉴的东西

1. **String：把 OS 做成「每个应用都是一个 Markdown 文件」的 agentic OS**
   - 来源：https://arxiv-org.ezproxy.obspm.fr/html/2608.28027v1
   - 可借：应用/场景是**可被 agent 读写改的文件**，不是二进制壳；人能看懂、agent 能生成。
   - 对我们的意义：我们的「界面」已经是 A2UI 组件树（数据），可以再往前走一步：**场景/应用定义文件化**。

2. **A2UI v0.9：可移植、框架无关的生成式 UI**
   - 来源：https://developers.googleblog.com/a2ui-v0-9-generative-ui/
   - 可借：UI 是消息（createSurface/updateComponents），渲染器只是宿主。
   - 对我们的意义：我们已经在用；要跟版本目录、把主题/组件目录的兼容性当契约。

3. **Persistent Recursive Worlds：让自主软件演化**
   - 来源：https://export.arxiv.org/pdf/2608.10450
   - 可借：世界要**可持久、可递归迭代**（状态可回放/分叉），软件才能自己演化。
   - 对我们的意义：我们有只追加的账 ＋ 根对象；缺「世界快照/回放/分叉」的显式能力。

4. **LUMOS：面向 agent 的语义 OS 层（accessibility-grounded）**
   - 来源：https://www.semanticscholar.org/paper/LUMOS%3A-A-Semantic-Operating-System-Layer-for-AI-Thota/516a37229eecc8634fb88b87ef182c3be762a9aa
   - 可借：给 agent 一个**语义层**（不是截图/像素）去理解系统与应用。
   - 对我们的意义：`presentation.state`（问界面要状态）就是这一层；可继续把「系统对象」语义化（进程→对象、窗口→对象）。

5. **Agentlas-OS：agent OS 的「执行门控」子系统**
   - 来源：https://github.com/agentlas-ai/Agentlas-OS/blob/main/README.ja.md
   - 可借：agent 的动作要经**门控（gating）**：谁能做、能做什么、何时停。
   - 对我们的意义：我们的本体闸（认名/许可/凭证/记账/路由）就是门控；缺的是「人确认/委托」那一段。

6. **AutoFyn：长程 agent 的「非参数专家迭代」**
   - 来源：https://export.arxiv.org/pdf/2609.05446
   - 可借：长程任务要把**轨迹/结果变成下一轮的改进信号**。
   - 对我们的意义：DSH 目标链每轮报告 ＋ 账本就是轨迹；补「评估→修正」闭环即可。

## 二、设计点与「是否必须」初判

| 点 | 内容 | 初判 |
|---|---|---|
| **P1** | **执行门控**：动作必须过本体（认名/许可/凭证/账/路由），人确认/委托补上 | **必须**（已有大半；人确认/委托四格待作者定） |
| **P2** | **语义状态**：agent 不靠截图，靠 `presentation.state` / `space.state` 这类动作读世界 | **必须**（已有；还缺实时事件/活动流） |
| **P3** | **应用/场景文件化**：应用＝可读可写的定义文件（Markdown/JSON），agent 能生成/改 | 值得（非必须；先做定义格式，不急着做市场） |
| **P4** | **世界快照/回放/分叉**：账本＋快照，让「世界」可回滚、可试分支 | 值得（自进化必需的基础；可先做快照命令） |
| **P5** | **A2UI 跟版**：目录/主题/校验随标准升级 | **必须**（我们是借标准，不能漂） |
| **P6** | **长程闭环**：目标→每轮报告→评估→修正（AutoFyn 式） | **必须**（DSH 目标链已有雏形，补评估） |
| **P7** | **agent 即进程可观测**：agent 与世界个体、PID/cgroup、窗口绑定 | 值得（多 agent 时要；单用户可缓） |
| **P8** | **事件流**：world.event → 人活动流/agent 订阅（实时双向） | **必须**（作者前面点名要的；仍未做） |

## 三、给 VM agent 的优先顺序建议（可商量）

1. **P8 事件流**（最小一块：world/stamp 后发 world.event；空间收来画「活动」窗口）
2. **P2 的补洞**：`world/query kind=activity` 或事件订阅（agent 能读人正在干什么）
3. **P4 快照**：一个 `scripts/release/snapshot.py`（账＋store 快照 + 回放命令）
4. **P1 人确认/委托**（**只写提案，不落法** —— 法由人签）
5. **P5/P6/P3**：跟版、闭环、场景文件（后两者是大块，分轮做）

> ★ 大块原则：**一次一轮只做一块**；每块都要「改了什么、怎么验、回滚点」三样齐；没收益只写报告。
