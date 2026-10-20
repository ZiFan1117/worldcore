# 二期报告：底层进程落地 + DSH 融入语义世界

> 现取：2026-10-20 夜（截止 2026-10-21 02:00 Asia/Shanghai）。
> 范围：repo `13-aios-worldcore`（08 不参与）。全部改动已提交推送；判据不推。
> 本报告只写**做到了什么、怎么验的、没做到什么**——四要素（命令/输出/rc/时间）见各笔提交与证据文件。

## 一、目标

作者口径（逐字）：「建立一个目标，寻找有意义的进程，最好是我们底层缺的底层进程，看看现在的 aios 有什么可以借鉴的，而且可以完善我们的 dsh，融入语义世界。最晚执行到明天两点。」

拆成三件：
1. 盘点现有进程与缺口，读仓里 AI-OS 规格（`001/002/003`，`crates/` 已删）找可借形状；
2. 选有意义的底层进程，做成可跑骨架（一进程一夹＋法＋单元＋判据＋VM 验证）；
3. 把 DSH 更好地融进语义世界（身份/心跳/事件/查询/动作桥/可观测）。

## 二、结果总览（现取）

| 项 | 基线（二期前） | 二期后（现取） |
|---|---|---|
| 常驻单元 | 9 | **13**（+fs、+clock、+recovery、+network） |
| 法 | 14 类 / 189 动作 | **21 类 / 200 动作**（世界 44＋sys 156）/ 9 函数 / 4 接口 / 5 关系 |
| 判据 | 71（本目标开始时） | **73**（+C72 network、+C73 agent 回话） |
| VM | 9 单元 active | **13 单元全 active**；法一致；只读进程全部验过 |
| DSH | 能问世界/做动作（但看不到/挑不中新进程） | 心跳可观测、清单含新动作、**真实轮次挑中并做成** `clock.now`、`file.list` |

## 三、落地的四个底层进程（全部只读 v1）

| 进程 | 借鉴 AI-OS | 法（类/动作） | 安全边界 | 判据 | VM 现取 |
|---|---|---|---|---|---|
| **fs 文件** | L2 AIOS-FS（文件=带版本语义对象；v1 只做只读） | `file`/`fs`；`file.stat/list/hash/read_text`、`fs.state` | 白名单根 `/var/lib/aios:/root/aios:/etc/aios`；realpath 防符号链接逃逸；秘密/隐藏文件拒读；32KB 截断；**不写文件** | C69 | 11 项 PASS：list/stat/hash/read_text 截断/越界拒/秘密拒/registry 4 个/file 个体 3 个/账 |
| **clock 时间面** | S28 Constitutional Time Plane（单调/不可回拨/可审计） | `clock`；`clock.now/state` | 只读；**没有 clock.set**；返回时区/偏移/单调秒/boot_id | C70 | 8 项 PASS：now/offset/单调 137322→137323/boot_id/state/clock.set 拒/个体/账 |
| **recovery 恢复边界** | L1 Recovery boundary（可独立 inspect） | `snapshot`/`recovery`；`recovery.list/state` | 只读；**无 restore**；无外进程；读快照 `meta.json` | C71 | 7 项 PASS：快照 5 份/分叉 1 个/rows=11603/state 24 快照/restore 拒/snapshot 个体 5/账 |
| **network 网络面** | L8 Network/Hardware/Devices（接口是对象） | `link`/`network`；`network.list/state` | 只读；**没有 set_ip**；无 subprocess/ip 命令；读 `/sys/class/net`＋`/proc/net/dev` | C72 | 8 项 PASS：enp0s3/lo、kind/计数器、state 2 口/up 1、set_ip 拒、link 个体 2、账 |

共同形状：`world/appear` 报到 → `world/register` 注册动作 → 订 `world/exec`（route=进程名）→ 验 permit＋核销 → 执行 → 回 `world/exec/result`；读到的对象（file/snapshot/link）再报成个体（`ingest` 接收、upsert、落账、推事件）。

## 四、DSH 融入语义世界

| 边 | 做了什么 | 现取 |
|---|---|---|
| 身份 | agent 以 `agent/dsh` 报到（`world://agent/dsh`） | 账里 appear 持续 |
| 心跳/可观测 | `/run/aios/agent-heartbeat.json`；unit 加 `PYTHONUNBUFFERED=1`（之前日志缓冲，误以为卡死） | `{"launched": true, "events": 30}` |
| 查询/动作 | `available_actions` 并入 `file.*/clock.now/recovery.*/network.*`（registry）；提示词加「新只读能力优先」「路径白名单」 | 真实轮次：第 1 轮 `clock.now` ok，第 3 轮 `file.list /var/lib/aios` **ok=True** |
| 事件/帧 | 订 `world/event` 回放；A2UI 帧走 `world/notice`（经本体） | 每轮发 9–23 个组件帧 |
| 回话修复 | 测出 `agent.on_exec` 从不回 `world/exec/result` ⇒ ask 等 20s 超时；已修（成功/失败都回） | `agent.launch` 回 `{"ok": true, "body": {"launched": true}, "by": "agent/dsh"}` |

证据（本地，`scripts/release/evidence/` 按 `.gitignore` 设计不推）：
`t492-dsh-rounds.txt`、`t497-dsh-file-success.txt`、`t489-clock-live-test.txt`、`t491-recovery-live-test.txt`、`t495-network-live-test.txt`、`t487-fs-live-test.txt`。

## 五、判据与门禁

- `python scripts/test/check.py`：**73/73 全绿**（每条带 `--self-test` 会红反例；C69–C73 为二期新增）；
- 法对账：`export-law.py --check` = 声明件 ≡ 运行中的法；
- 部署：`deploy.sh` 管理 13 单元与看门狗 `/root/aios-watchdog.sh`（UNITS 已含四新进程）；
- 架构图：`docs/architecture.png`（v3，13 单元）＋ `docs/ARCHITECTURE.md`＋`docs/CODE-MAP.md`。

## 六、没做到的（如实）

1. 四个新进程都是**只读 v1**：fs 不写文件、recovery 不 save/restore、network 不配网、clock 不改钟；
2. `vault`（L4 秘密）**没做**——安全成本高，宁可空着也不做半吊子；
3. **appear 通道仍可伪造**：上报者身份只靠 `reporter` 字符串、总线无 ACL（此前测试已证）；需要提供者签名/ACL；
4. DSH 模型**不总按「没挑过」轮换**（会连续挑 clock.now）；`network.*`/`recovery.*` 没被模型真实挑中；
5. 证据文件按 `.gitignore` **本地留、不推**；报告里的读数来自本地运行。

## 七、怎么复跑

```bash
# 本机全量判据（含 C69–C73）
python scripts/test/check.py
# 法对账
python scripts/release/export-law.py --check
# VM（在 13 单元部署后）
python3 /root/aios/scripts/release/fs_live_test.py
python3 /root/aios/scripts/release/clock_live_test.py
python3 /root/aios/scripts/release/recovery_live_test.py
python3 /root/aios/scripts/release/network_live_test.py
```

## 八、下一期建议（按优先级）

1. **appear 签名/ACL**（安全，最高优先；当前可伪造）；
2. **vault**（L4：秘密进世界，账里只留引用）；
3. **recovery.save/restore/fork 做成动作**（人确认＋写路径）；
4. **fs 写路径**（内容寻址/版本/指针，借 L2）；
5. DSH 动作轮换/结果回看（把「挑过的动作」记进上下文）。

## 九、提交（repo 侧）

`T-485` 候选清单 → `T-486/487` fs → `T-488/489` clock → `T-490/491` recovery → `T-492/493` DSH 轮次 → `T-494/495` network → `T-496` 架构图 v3 → `T-497` DSH file.list 成功 → `T-498` agent 回话修复/C73 → 本报告（`T-499`）。
