# 实测（作者令）：出向 channel 跑通 —— 意图 ⇒ 本体 ⇒ 执行 ⇒ 结果回界面

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S3 | 执行 | 五 证据 | **1.0（出向链路通；GUI 真按钮点击待接）** |

> **作者令（逐字）**：「**继续做呀，下一步继续做**」

---

## 一、★★★ 这一步顺带补上了四进程里缺的那个 —— ① 本体进程

| # | 进程 | 现状 |
|---|---|---|
| **①** | ★★★ **本体进程** | ★★★ **本轮新增：`/root/bus/src/bin/worldcore.rs`（90 行）** ⇒ 订 `world/intent` ⇒ 过本体 ⇒ 执行（记一笔）⇒ 结果发回 ✓ |
| **②** | 总线进程 | `zenohd`（`tcp/127.0.0.1:7447`） |
| **③** | 业务软件进程 | `individual`（产 A2UI 帧） |
| **④** | GUI 进程 | Flutter 3.47.7 ＋ 官方 `genui 0.10.4`（`/root/gui`） |

## 二、★★★ 协议（两个 topic）

    ★ 出向：GUI ⇒ 本体进程   topic = world/intent
            {"action":"job.start","surfaceId":"world/system","by":"wc_gui"}
    ★ 入向：本体进程/个体 ⇒ GUI   topic = world/system/gui/frames（v0.9 口径）
    ★ 反向文件桥：GUI 追加写 /root/gui/intents.jsonl ⇒ intent_bridge 轮询 ⇒ publish 到 world/intent
       （Dart 侧没有 zenoh 客户端；两边各写各的目录，不撞车）

## 三、★★★★ 实测输出（逐字）

    === 1. 起本体进程 ===
    [本体进程] 装上：类 9 动作 9 函数 9
    [本体进程] 在册动作：job.cancel, job.finish, job.start, ledger.compact, notice.mute,
                  notice.unmute, presence.report, world.migrate, world.rekey
    [本体进程] 订 world/intent ⇒ 过本体 ⇒ 结果发回 world/system/gui/frames

    === 4. 模拟 GUI 点按钮：写两条意图（一条在册、一条不在册）===  2026-10-15T12:25:18+02:00
    === 5. 本体进程的反应 ===
    --- 第 1 条意图：{"action":"job.start","surfaceId":"world/system","by":"wc_gui"}
      ├ 动作 = job.start ｜ 来自 = wc_gui
      ├ [本体过] 在册；函数 = fn.job.start
      ├ [执行] 受理并记一笔（账只追加）
      └ [回帧] 已发回 world/system/gui/frames
    --- 第 2 条意图：{"action":"frobnicator.dance","surfaceId":"world/system","by":"wc_gui"}
      ├ 动作 = frobnicator.dance ｜ 来自 = wc_gui
      └ [本体拒] frobnicator.dance 不在册 ⇒ 不执行

    === 6. 结果帧（GUI 会收到）===
    [桥] 第 1 条已写入（526 字节）／第 2 条（461 字节）

### ★★★ 两条结果帧（逐字，GUI 直接显示）

| 情况 | 帧内容 |
|---|---|
| ★★ **过了本体** | `已受理（过了本体）` ＋ 明细：动作：`job.start`／函数：`fn.job.start`／来自：`wc_gui`／结果：已记一笔（账只追加） |
| ★★★ **没过本体** | `已拒（未登记即拒）` ＋ 明细：动作：`frobnicator.dance`／理由：不在本体在册表里／来自：`wc_gui` |

## 四、★★★ 三条定性

1. ★★★ **在册的：过本体 ⇒ 才执行**（且执行前先查出 `fn.job.start`）；
2. ★★★ **不在册的：连执行都没进**（打印的是"本体拒"而不是"执行失败"）；
3. ★★★ **拒也回帧**（不是静默丢弃）⇒ 正是本仓"不静默放行"的口径 ✓

## 五、★★ 完整闭环（现在的样子）

    ★★ 线 A（入向，上轮已通）：
       业务软件 individual ⇒ 产 v0.9 帧 ⇒ 总线 ⇒ 桥 ⇒ frames.jsonl ⇒ GUI 渲染 ⇒ 窗口变
    ★★★ 线 B（出向，本轮新通）：
       GUI 点按钮 ⇒ intents.jsonl ⇒ intent_bridge ⇒ world/intent
            ⇒ ★【本体进程】过本体（在册吗／给不给函数）
            ⇒ 执行（受理并记一笔）
            ⇒ ★ 结果帧回 world/system/gui/frames ⇒ GUI 显示结果

## 六、★ 仍未做（如实）

1. ★★★ **GUI 侧的真按钮点击还没接** —— 本轮出向是我**手写 `intents.jsonl` 模拟**的；智能体正在做 Dart 侧；
2. ★★ **"执行"目前只到"受理并记一笔"** —— 没有真效应器（`Executor` 口仍是我们留的）；也没有真的写进账结构；
3. ★★ **"有权吗"这一格没做** —— 今天只有"在册吗"（治理面仍是我们留的口）；
4. ★ **入参与出参校验没做**；
5. ★ **工程都住在 VM（`/root/bus`、`/root/gui`）** ⇒ 尚未进本仓 `crates/`。
