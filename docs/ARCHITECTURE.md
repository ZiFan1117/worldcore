# worldcore 架构图（总览）

> 现取：2026-10-20。类 14 ／ 接口 4 ／ 关系 5 ／ 在册动作 189（sys 156 ＋ 世界 33）／ 函数 9 ／ 判据 66 条 ／ 常驻单元 9 个。
> 图里所有进程都是独立 systemd 单元；所有消息走 zenoh 总线话题 `world/*`。

## 一、四层总览

```mermaid
flowchart TB
  subgraph L1[① 定义面 · 法]
    LAW["world.json<br/>14 类 / 4 接口 / 5 关系<br/>世界动作 33 ＋ sys 156 / 函数 9"]
    LOADER["law_loader.py<br/>解析 → 校验 → 建本体"]
    EXPORT["export-law.py --check<br/>声明件 ≡ 运行中的法（C35）"]
    LAW --> LOADER
    LOADER --> EXPORT
  end

  subgraph L2[② 本体 · src/ontology（只做三件事：认、判、记）]
    PROC["ontology_process.py<br/>消息循环 / 个体(ObjectStore) / 记账 / 推事件"]
    GATE["ask_path.py<br/>八道闸：认名→参数→票→身份→可核→许可→前置→路由"]
    QUERY["world_query.py<br/>overview/types/type/actions/history/events"]
    GOV["governance.py<br/>人确认 / 委托四格 / 策略 / 审计回账"]
    ID["identity.py 票 ＋ permit.py 一次性凭证"]
    AC["action_contract.py<br/>参数 / 前置 / 多态路由"]
    PROC --> GATE --> AC
    PROC --> QUERY
    PROC --> GOV
    GATE --> ID
  end

  BUS[("zenoh 总线<br/>world/appear · register · ask · exec ·<br/>exec/result · ask/result · query · event · notice · ui/*")]

  subgraph L3[③ 提供者进程（一进程一夹 · 9 个单元）]
    COMP["computer<br/>执行 156 条命令 / app.open_url<br/>实时指标采集上报（数据管道）"]
    PRES["presentation ＋ presentation-render<br/>合成画布 / Flutter 渲染（A2UI）"]
    SPACE["space<br/>桌面 / 窗口 / 场景 / 确认弹窗 / 本体窗口"]
    AGENT["agent<br/>DSH 接入：心跳 / 回放 / 规划"]
    GUARD["guard<br/>PDP 判决（socket）＋ guard_exec（Landlock）"]
    WEB["web<br/>语义浏览器：HTTP/SSE/A2UI/确认弹窗"]
    BUSUNIT["bus<br/>aios-bus（zenoh）"]
  end

  subgraph L4[④ 界面 / 接入]
    FLUTTER["Flutter 桌面<br/>genui 渲染 A2UI 帧"]
    BROWSER["语义浏览器<br/>自写 A2UI 渲染器"]
  end

  L2 <--> BUS
  BUS <--> COMP
  BUS <--> PRES
  BUS <--> SPACE
  BUS <--> AGENT
  BUS <--> GUARD
  BUS <--> WEB
  BUS --- BUSUNIT
  PRES --> FLUTTER
  WEB --> BROWSER
  SPACE --> PRES
  FLUTTER -. "人点击（world/ui/act）" .-> PRES
```

## 二、数据面（东西存在哪）

| 面 | 路径 | 谁的权威 |
|---|---|---|
| 法（定义） | `src/ontology/world.json` | 唯一权威；`export-law --check` 对账 |
| 个体（A 盒） | `/var/lib/aios/ontology/objects.db`（SQLite） | 本体 ObjectStore |
| 证据（账） | `/var/lib/aios/ontology/ledger.jsonl`（只追加） | 本体（唯一一支笔） |
| 注册表 | `/var/lib/aios/ontology/registry.jsonl` | 提供者注册的动作 |
| 一次性凭证 | `/var/lib/aios/ontology/permits.jsonl` | 本体签发/核销 |
| 事件回放 / 界面 | `/var/lib/aios/{cursors,scenes}` | 空间/浏览器游标、场景文件 |
| 世界文件 | `/var/lib/aios/world/`（worldfs 导出） | 账→文件树的只读镜像 |
| 快照 | `/var/backups/aios/world-snapshots/`（含 forks） | 定时快照进程 |

## 三、一条 `world/ask` 怎么走（八道闸）

```mermaid
sequenceDiagram
  participant U as 人/Agent
  participant BUS as 总线
  participant W as 本体
  participant P as 提供者（computer/space/…）
  U->>BUS: world/ask {action, params, actor/ticket}
  BUS->>W: 转发
  W->>W: ①认名 ②参数 ②b验票 ③身份 ③b可核 ④许可 ⑤前置 ⑥路由
  alt 人确认类（变更动作）
    W-->>BUS: world/notice kind=confirm.request
    BUS-->>U: 界面弹窗（桌面/浏览器）
    U->>W: world/ask confirm.resolve（带票）
    W->>W: 落账（人签了什么）→ 放行或写委托
  end
  W->>W: 落账 kind_of=ask（发 permit）
  W->>BUS: world/exec {route, permit, params}
  BUS->>P: 只接自己那一类
  P->>P: 验 permit ＋ 向本体核销（一号一用）
  P->>P: 执行（computer 才许起进程，C19）
  P->>BUS: world/exec/result
  BUS->>U: world/ask/result
  W-->>BUS: world/event（公开字段）→ 界面/agent 实时
```

## 四、实时数据管道（computer → 本体 → 界面）

```mermaid
flowchart LR
  SYS["操作系统底层<br/>/proc/uptime · loadavg · meminfo<br/>/etc/os-release"]
  COL["computer.collect_metrics()<br/>每 10 秒采集"]
  CHG["metrics_changed() / should_report()<br/>uptime 不参与判定<br/>负载 >0.1 / 内存 ≥64MB / 其余属性不等<br/>300 秒心跳兜底"]
  APP["world/appear<br/>（提供者上报，状态所有权在 computer）"]
  ONTO["本体 on_appear<br/>更新个体属性 ＋ 落账 appear 行 ＋ 推 world/event"]
  UI["桌面「本体→机器」页<br/>每 5 秒重查 ＋ appear 事件触发刷新"]
  SYS --> COL --> CHG --> APP --> ONTO --> UI
```

## 五、权限 / 人确认 / guard

```mermaid
flowchart TB
  A["agent 请求变更类动作"] --> B["本体闸：有有效委托？"]
  B -- 有 --> C["放行（used+1 落账）"]
  B -- 没有 --> D["guard 判 decision=confirm<br/>本体发 confirm.request ＋ 推通知"]
  D --> E["界面弹窗（桌面 / 语义浏览器）"]
  E -- 人点/说「签」 --> F["world/ask confirm.resolve（带票）"]
  F --> G["本体核票/核请求 → 落账 → 放行或写委托四格"]
  G --> A2["动作执行"]
  H["guard（PDP）<br/>与本体同口径决定 allow/deny/confirm"] -.-> D
  I["guard_exec（Landlock）<br/>执行前限文件访问"] -.-> A2
```

## 六、运行面（systemd 单元与数据流）

| 单元 | 作用 |
|---|---|
| `aios-bus` | zenoh 总线（7447） |
| `aios-ontology` | 本体：闸/账/事件/查询 |
| `aios-computer` | 执行器＋系统事实上报 |
| `aios-presentation` | 画布合成（A2UI） |
| `aios-presentation-render` | Flutter/genui 渲染器 |
| `aios-space` | 个人空间（桌面/窗口/场景/确认/本体窗口） |
| `aios-agent` | DSH 智能体接入 |
| `aios-guard` | 权限决定（socket `/run/aios/guard.sock`） |
| `aios-web` | 语义浏览器桥（8765） |

> 定时器：看门狗（3 分钟）、世界快照（每小时）、worldfs（15 分钟）等（不属于 9 个常驻进程）。

## 七、设计口径（三句话）

1. **定义与实现分家**：法 `world.json` 是唯一权威，代码只装载它；改法=改声明件。
2. **本体只做三件事**：认（闸）、判（许可/凭证）、记（账）；**不执行、不渲染、不碰机器**。
3. **一进程一夹**：每个进程有独立目录/单元/动作注册/回账；**出向只许 computer**（C19）。

---

*本图与 `docs/CODE-MAP.md` 配套；判据见 `scripts/test/check.py`（66 条，每条自带会红的反例）。*
