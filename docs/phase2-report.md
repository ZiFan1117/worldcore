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
| 常驻单元 | 9 | **14**（+fs、+clock、+recovery、+network、+vault） |
| 法 | 14 类 / 189 动作 | **23 类 / 202 动作**（世界 46＋sys 156）/ 9 函数 / 4 接口 / 5 关系 |
| 判据 | 71（本目标开始时） | **75**（+C72 network、+C73 agent 回话、+C74 动作记忆、+C75 vault） |
| VM | 9 单元 active | **14 单元全 active**；法一致；只读进程全部验过 |
| DSH | 能问世界/做动作（但看不到/挑不中新进程） | 心跳可观测、清单含新动作、**真实轮次挑中并做成** `clock.now`、`file.list` |

## 三、落地的五个底层进程（全部只读 v1）

| 进程 | 借鉴 AI-OS | 法（类/动作） | 安全边界 | 判据 | VM 现取 |
|---|---|---|---|---|---|
| **fs 文件** | L2 AIOS-FS（文件=带版本语义对象；v1 只做只读） | `file`/`fs`；`file.stat/list/hash/read_text`、`fs.state` | 白名单根 `/var/lib/aios:/root/aios:/etc/aios`；realpath 防符号链接逃逸；秘密/隐藏文件拒读；32KB 截断；**不写文件** | C69 | 11 项 PASS：list/stat/hash/read_text 截断/越界拒/秘密拒/registry 4 个/file 个体 3 个/账 |
| **clock 时间面** | S28 Constitutional Time Plane（单调/不可回拨/可审计） | `clock`；`clock.now/state` | 只读；**没有 clock.set**；返回时区/偏移/单调秒/boot_id | C70 | 8 项 PASS：now/offset/单调 137322→137323/boot_id/state/clock.set 拒/个体/账 |
| **recovery 恢复边界** | L1 Recovery boundary（可独立 inspect） | `snapshot`/`recovery`；`recovery.list/state` | 只读；**无 restore**；无外进程；读快照 `meta.json` | C71 | 7 项 PASS：快照 5 份/分叉 1 个/rows=11603/state 24 快照/restore 拒/snapshot 个体 5/账 |
| **vault 保险库** | L4 Policy/Identity/Vault（三分家；值从不进世界） | `vault`/`secret`；`vault.list/state` | 只读元数据；**许可只给人**；不读秘密值文件；无 `vault.get` | C75 | 8 项 PASS：条目 2、active=2、不含值/路径、secret 个体 2、vault.get 拒、账 |
| **network 网络面** | L8 Network/Hardware/Devices（接口是对象） | `link`/`network`；`network.list/state` | 只读；**没有 set_ip**；无 subprocess/ip 命令；读 `/sys/class/net`＋`/proc/net/dev` | C72 | 8 项 PASS：enp0s3/lo、kind/计数器、state 2 口/up 1、set_ip 拒、link 个体 2、账 |

共同形状：`world/appear` 报到 → `world/register` 注册动作 → 订 `world/exec`（route=进程名）→ 验 permit＋核销 → 执行 → 回 `world/exec/result`；读到的对象（file/snapshot/link）再报成个体（`ingest` 接收、upsert、落账、推事件）。

## 四、DSH 融入语义世界

| 边 | 做了什么 | 现取 |
|---|---|---|
| 身份 | agent 以 `agent/dsh` 报到（`world://agent/dsh`） | 账里 appear 持续 |
| 心跳/可观测 | `/run/aios/agent-heartbeat.json`；unit 加 `PYTHONUNBUFFERED=1`（之前日志缓冲，误以为卡死）；另修 `ReadWritePaths=-/run/aios` 竞态（加 `ExecStartPre` 先建目录） | `{"launched": true, "events": 30}`；VM 心跳文件持续更新，日志无 EROFS |
| 查询/动作 | `available_actions` 并入 `file.*/clock.now/recovery.*/network.*`（registry）；提示词加「新只读能力优先」「路径白名单」 | 真实轮次：第 1 轮 `clock.now` ok，第 3 轮 `file.list /var/lib/aios` **ok=True** |
| 事件/帧 | 订 `world/event` 回放；A2UI 帧走 `world/notice`（经本体） | 每轮发 9–23 个组件帧 |
| 回话修复 | 测出 `agent.on_exec` 从不回 `world/exec/result` ⇒ ask 等 20s 超时；已修（成功/失败都回） | `agent.launch` 回 `{"ok": true, "body": {"launched": true}, "by": "agent/dsh"}` |
| 动作记忆 | agent 记 `recent_actions`（最近 30 个，给上下文 8 个），提示词「尽量换一个没做过的」 | 连续三轮换三动作：`clock.now` → `file.list` → `recovery.list` 全 ok=True |

证据（本地，`scripts/release/evidence/` 按 `.gitignore` 设计不推）：
`t492-dsh-rounds.txt`、`t497-dsh-file-success.txt`、`t501-dsh-memory.txt`、`t489-clock-live-test.txt`、`t491-recovery-live-test.txt`、`t495-network-live-test.txt`、`t505-vault-live-test.txt`、`t487-fs-live-test.txt`、`t502-fs-security.txt`。

## 五、判据与门禁

- `python scripts/test/check.py`：**75/75 全绿**（每条带 `--self-test` 会红反例；C69–C75 为二期新增）；
- 法对账：`export-law.py --check` = 声明件 ≡ 运行中的法；
- 部署：`deploy.sh` 管理 14 单元与看门狗 `/root/aios-watchdog.sh`（UNITS 已含五个二期进程：fs/clock/recovery/network/vault）；
- 架构图：`docs/architecture.png`（v4，14 单元）＋ `docs/ARCHITECTURE.md`＋`docs/CODE-MAP.md`。

## 五半、收口验证（T-503，VM 现取）

| 项 | 现取 |
|---|---|
| 单元 | **14/14 active**（bus/ontology/guard/web/computer/presentation/presentation-render/space/agent/fs/clock/recovery/network/vault） |
| 法 | `export-law --check` = 声明件 ≡ 运行中的法：一致 |
| 新进程个体 | 账里 `fs`/`clock`/`recovery`/`network`/`vault` 个体的 appear 行都在；`file`/`snapshot`/`link`/`secret` 个体由对应进程上报 |
| computer 管道 | 最近 `computer/leap16` appear：uptime=139897、load1=0.01、mem_available=14009（变化才报） |
| 新进程周期 | clock 每 60s 报时（单调 139883→140003）、recovery 每 60s 刷新（latest=20261020-170057）、network 每 60s 报 2 接口（up=1） |
| DSH 轮次 | 第 4 轮 `file.stat /var/lib/aios` ok=True；第 5 轮 `file.read_text /etc/aios` ok=False（目录不可读，预期） |
| fs 安全边界（Linux 真符号链接） | 符号链接逃逸拒、`../` 遍历拒、隐藏/秘密文件拒、白名单目录可列（5/5 PASS） |
| soak | `soak_13units.py` 以 transient unit `wcore-soak.service` 跑 68 分钟（14 单元），每 5 分钟一行 `/root/soak-13units.jsonl` |

### 五半.1 soak 进行中（2026-10-21 00:18 现取）

- `wcore-soak.service` 在跑；已有 4 个样本（每 5 分钟一行，`/root/soak-13units.jsonl`）；
- soak 已扩到 **14 单元**（含 vault）并重起；样本里 14/14 全 `active`；账行数持续增长；computer 最近上报照常；
- 样本与结束读数见 §五半.2（收口时补）。

## 六、没做到的（如实）

1. 五个新进程都是**只读 v1**：fs 不写文件、recovery 不 save/restore、network 不配网、clock 不改钟、vault 不取秘密值（`vault.get` 未做）；
2. **appear 通道仍可伪造**：上报者身份只靠 `reporter` 字符串、总线无 ACL（此前测试已证）；需要提供者签名/ACL；
3. DSH 模型**不总按「没挑过」轮换**（动作记忆提高多样性，但不保证）；`network.*` 还没被模型真实挑中；
4. 证据文件按 `.gitignore` **本地留、不推**；报告里的读数来自本地运行。

## 七、怎么复跑

```bash
# 本机全量判据（含 C69–C73）
python scripts/test/check.py
# 法对账
python scripts/release/export-law.py --check
# VM（在 14 单元部署后）
python3 /root/aios/scripts/release/fs_live_test.py
python3 /root/aios/scripts/release/clock_live_test.py
python3 /root/aios/scripts/release/recovery_live_test.py
python3 /root/aios/scripts/release/network_live_test.py
python3 /root/aios/scripts/release/vault_live_test.py
python3 /root/aios/scripts/release/fs_security_test.py
```

## 八、下一期建议（按优先级）

1. **appear 签名/ACL**（安全，最高优先；当前可伪造）；
2. **vault.get**（取秘密值）：必须人确认＋guard/permit，账里只留引用；
3. **recovery.save/restore/fork 做成动作**（人确认＋写路径）；
4. **fs 写路径**（内容寻址/版本/指针，借 L2）；
5. DSH 结果回看/动作轮换（recent_actions 已有，继续做结果记忆）。

## 九、提交（repo 侧）

`T-485` 候选清单 → `T-486/487` fs → `T-488/489` clock → `T-490/491` recovery → `T-492/493` DSH 轮次 → `T-494/495` network → `T-496` 架构图 v3 → `T-497` DSH file.list 成功 → `T-498/499` agent 回话修复/C73 → `T-500/501` DSH 动作记忆/C74 → `T-502` fs 安全实测+soak → `T-503` 收口验证 → `T-504/505` vault/C75+架构图 v4 → `T-506/507/508` soak/文档对齐 → `T-509` 心跳竞态修复 → 终报（`T-510`）。
