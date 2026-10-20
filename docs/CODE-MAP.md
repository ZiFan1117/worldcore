# worldcore 代码导航（我想改 X，看哪里）

> 现取：2026-10-20。配套总览图：`docs/ARCHITECTURE.md`。
> 规矩：一进程一夹（`src/<进程>/`）；改完跑 `python scripts/test/check.py`（66 条判据，红不许绕）。

## 一、目录地图（带注释）

```
13-aios-worldcore/
├─ src/
│  ├─ ontology/                 ★ 本体（入口在根；功能分 4 个子夹）
│  │  ├─ ontology_process.py    入口：消息循环 / 个体 / 账 / 事件
│  │  ├─ world.json             法（唯一权威）
│  │  ├─ law/                   法：law_loader / law_dump / ontology_definition / sysknife_actions / grants
│  │  ├─ gate/                  闸：ask_path / action_contract / identity / permit / world_codes
│  │  ├─ query/                 查询：world_query
│  │  ├─ ingest/                数据管道（本体接收侧）：appear.py（收 appear → 建/更新个体 → 落账）
│  │  └─ govern/                治理：governance（确认/委托/策略/审计）
│  ├─ computer/                 ★ 执行器：156 条系统命令 + 文件机制 + app.open_url + 实时指标上报
│  ├─ presentation/             ★ 呈现：合成画布 + A2UI 帧校验 + Flutter 渲染器源码
│  ├─ space/                    ★ 个人空间：桌面/窗口/场景/确认弹窗/本体窗口/事件回放
│  ├─ agent/                    ★ 智能体：DSH 接入（心跳、回放、规划、world_cli 桥）
│  ├─ guard/                    ★ 权限：PDP 决定（gate_process）＋ Landlock 执行（guard_exec）＋ guardctl
│  ├─ web/                      ★ 语义浏览器桥：HTTP/SSE/A2UI 渲染/确认弹窗/语义浏览
│  ├─ foundry_ontology/         上游借来的本体库（ObjectStore/Ontology 引擎，尽量不改）
│  └─ legacy/                   旧料归档（不部署）
├─ scripts/
│  ├─ test/                     ★ 判据（C1–C66 ＋ check.py ＋ 每条的 --self-test 反例）
│  └─ release/                  ★ 发布/运维工具（deploy/status/snapshot/worldfs/guardctl/systemd/monitor）
├─ docs/                        ★ 本目录（架构图 / 代码导航）
├─ ninedim/                     工程域档案（变更登记/索引；只装档案）
├─ README.md                    前门（世界是什么、怎么跑、判据多少条）
└─ AGENTS.md / CLAUDE.md        给接手者的硬约束与指针
```

## 二、本体文件（`src/ontology/` 下 4 个子夹，先把这 7 个读了）

| 文件 | 行数 | 什么时候看它 |
|---|---|---|
| `ontology_process.py`（根） | 372 | 消息循环、报到（appear）、注册（register）、落账、推事件、个体 ObjectStore —— **入口** |
| `gate/ask_path.py` | 223 | 八道闸、委托放行、guard 弹窗（`CONFIRM_REQUIRED`）、执行凭证签发 —— **改权限/闸** |
| `query/world_query.py` | 258 |
| `ingest/appear.py` | ~120 | **本体内部数据管道**：收 world/appear → 校验 → 个体不存在就建/已存在就更新（带 before 落账） | 所有查询（overview/types/type/one/actions/history/events） —— **改查询/界面数据** |
| `govern/governance.py` | 180 | 人确认 / 委托四格 / 策略 / 审计回账（本地执行，不外转） —— **改确认/委托/审计** |
| `gate/identity.py` / `gate/permit.py` | 130 / 194 | 票（登录）／一次性执行凭证（HMAC、绑动作+参数） —— **改认证/凭证** |
| `gate/action_contract.py` | 113 | 参数校验、前置条件、`route_for()` 多态路由 —— **改动作契约/路由** |
| `gate/world_codes.py` | 66 | 拒绝码闭集、参数脱敏、变更类动作清单（guard 弹窗用） |
| `law/sysknife_actions.py` | 53 | 把 `sysknife-command-map.json` 的 156 条命令装成 `sys.*` 动作 |
| `law/law_loader.py` / `law/law_dump.py` | 234 / 124 | 法（`world.json`）的解析/校验/建本体 与 导出对账 |
| `law/ontology_definition.py` | 39 | 只调 `load_law()`（定义不在代码里手写，C35） |
| `law/grants.py` | 17 | 许可口径辅助 |

## 三、提供者进程（改哪个功能进哪个目录）

| 我想改… | 去哪里 | 关键入口 |
|---|---|---|
| 执行系统命令 / 跑 sys.* | `src/computer/computer_process.py` | `run_action()` / `handle_exec()`；命令表在 `scripts/release/computer/command-map-sysknife.jsonl` |
| 打开 URL / 起浏览器 | `src/computer/computer_process.py` | `_open_url()`（出向只许这里，C19） |
| 本体接收管道（appear→更新个体） | `src/ontology/ingest/appear.py` | `ingest_appear()`（ontology_process 只做入口委派） |
| computer 实时指标 | `src/computer/pipeline/metrics.py`（独立子夹） | `collect_metrics / metrics_changed / should_report / metrics_loop`；`computer_process.py` 只负责导入并起线程 |
| 桌面画布 / 图标 | `src/space/desktop_frame.py` | `desktop_frame()`、`ICONS` |
| 桌面窗口 / 点击处理 | `src/space/space_process.py` | `on_act() / dispatch() / draw()` |
| 本体窗口（页签/分页/实时） | `src/space/ontology_window.py` | `open_ontology / _content / _draw_ontology_window / _start_ont_autorefresh` |
| 确认弹窗（桌面） | `src/space/confirm_window.py` ＋ `space_process.on_act` | `ConfirmMixin.show_confirm` |
| 事件回放 / 活动窗口 | `src/space/activity.py` | `on_event / request_replay / apply_replay` |
| 画布合成 / A2UI 校验 | `src/presentation/presentation_process.py`、`frame_schema.py` | `dispatch()`、`validate_frame()` |
| 渲染器外观（颜色/字体） | `src/presentation/render_main.dart` | Flutter/genui 主题与 `_feed()` |
| 语义浏览器 | `src/web/web_process.py` ＋ `browser.html` | HTTP 路由 / `/events` SSE / `/cmd`（login、ui、browse、frames、confirm_resolve） |
| 人确认/委托/策略/审计 | `src/ontology/govern/governance.py` ＋ `world.json` 的动作 | `dispatch()`、`confirm.* / delegate.* / policy.* / audit.record` |
| 权限决定 / Landlock | `src/guard/guard_process.py`、`guard_exec.py`、`guardctl.py` | `Guard.check()`、Landlock 规则 |
| 智能体接入 | `src/agent/agent_llm.py`、`world_cli.py` | 心跳、回放游标、world/query 桥 |

## 四、我要做一件具体的事（任务 → 文件/命令）

| 任务 | 步骤 |
|---|---|
| **加一个对象类** | 改 `src/ontology/world.json` 的 `object_types` → `python scripts/release/export-law.py`（生成物）→ 跑 `python scripts/test/check.py`（C35/C36/C37 会核） |
| **加一个世界动作** | 同上加 `actions`（含 params/preconditions/effects/grant）→ 在提供者 `dispatch()` 里实现 → 提供者 `ACTIONS`/注册处登记 → 判据（C3/C36） |
| **加一条系统命令** | `scripts/release/computer/command-map-sysknife.jsonl` 加一行（156 条口径受 C22/C23 盯，慎改） |
| **新进程（新服务）** | 建 `src/<名字>/`（一进程一夹，C28）→ 写入口/说明 → 加 `scripts/release/systemd/aios-<名字>.service` → 加进 `deploy.sh` 与 `monitor/watchdog.sh` 的单元列表 → 加判据 |
| **加判据** | `scripts/test/cNN_*.py`（**先写会红的反例＋`--self-test`**）→ 加进 `check.py` 列表 → README 条数同步 |
| **改界面（桌面）** | 帧由 `src/space/*` 生成 → `world/notice a2ui.frame` → `presentation` 合成 → `render_main.dart` 画 |
| **改界面（浏览器）** | `src/web/browser.html`＋`web_process.py`（静态页，无需重编） |
| **改法**（只有人能签） | 改 `world.json` → `export-law` → 机器校验；智能体只能出 `src/ontology/proposals/*.proposal.json` 草案 |
| **部署到 VM** | `bash scripts/release/deploy.sh`（会拷 src/数据、导法、重启单元；`/root/aios` 是源码副本，`/usr/lib/aios` 是运行副本） |
| **看世界状态** | `python3 scripts/release/status.py`；快照 `world_snapshot.py`；世界文件 `worldfs.py` |

## 五、总线话题（`world/*`，所有交互都过这里）

| 话题 | 方向 | 内容 |
|---|---|---|
| `world/appear` | 提供者→本体 | 报到/状态所有权上报（带类字段；computer 实时指标走这里） |
| `world/register` | 提供者→本体 | 注册动作（五格） |
| `world/ask` → `world/ask/result` | 人/agent ⇄ 本体 | 所有请求；结果回请求方 |
| `world/exec` → `world/exec/result` | 本体→提供者 | 带 permit 转发；执行器只接自己 route |
| `world/query` → `world/query/result` | 任意→本体 | 读世界（overview/types/type/actions/history/events） |
| `world/notice` | 任意→界面 | `a2ui.frame`、`confirm.request`、`ui.act`、`space.logout` |
| `world/event` | 本体→订阅者 | 公开字段事件流（P8；支持 since/游标回放） |
| `world/ui/act` / `world/ui/frame` | 呈现/空间 | 人的动作；画布帧 |

## 六、数据与运行路径（VM）

```
/var/lib/aios/ontology/ledger.jsonl    账（只追加；唯一一支笔）
/var/lib/aios/ontology/objects.db      个体（SQLite）
/var/lib/aios/ontology/registry.jsonl  动作注册表
/var/lib/aios/ontology/permits.jsonl   一次性凭证
/var/lib/aios/{cursors,scenes,world}   游标、场景、世界文件树
/var/backups/aios/world-snapshots/     世界快照（含 forks/）
/usr/lib/aios/src/                     运行时源码（部署副本）
/root/aios/                            源码副本（VM 上改这里再 deploy）
```

## 七、常用命令

```bash
# 本机判据（改完必跑）
python scripts/test/check.py
# 法一致性
python scripts/release/export-law.py --check
# 部署到 VM（sudo 上下文）
bash scripts/release/deploy.sh
# 一屏状态 / 快照 / 世界文件
python3 scripts/release/status.py
python3 scripts/release/world_snapshot.py save
python3 scripts/release/worldfs.py export
# 权限进程
python3 src/guard/guardctl.py check world://agent/dsh sys.AptInstall
# 语义浏览器
curl -s http://127.0.0.1:8765/cmd -d '{"op":"ping"}'
```

## 八、调试一件事时的顺序（建议）

1. **先看账**：`grep -a "<动作/actor>" /var/lib/aios/ontology/ledger.jsonl | tail` —— 有没有 ask / reject?code / result / appear。
2. **再看单元日志**：`journalctl -u aios-ontology -n 100`（拒绝原因、路由）、`-u aios-computer`（执行/上报）、`-u aios-space`（窗口/点击）、`-u aios-web`（浏览器）。
3. **再对法**：`export-law.py --check`；动作在不在册、scope 对不对、拒绝码是不是闭集。
4. **最后才改代码**；改完跑判据，红了先看是判据错了还是代码错了（判据自己也要能红）。

## 九、接手先读这 6 个文件（按顺序）

1. `README.md`（世界是什么、怎么跑）
2. `AGENTS.md`（硬约束 11 条＋禁区）
3. `src/ontology/ontology_process.py`（本体消息循环）
4. `src/ontology/gate/ask_path.py`（八道闸：所有请求都从这里过）
5. `src/ontology/world.json`（法：类/动作/许可）
6. `scripts/test/check.py`（判据清单：项目现在承诺什么）
