# 数据管道测试报告（详细）

> 现取：2026-10-20 晚。测试分两段：**本机判据 C68**（临时数据面，覆盖全部分支/反例/压力）
> ＋ **VM 真总线测试** `scripts/release/pipeline_live_test.py`（真实 computer/本体/账/事件）。
> 结论：**9/9 PASS**；测出并修掉 1 个真 bug；登记 1 个安全缺口（总线 ACL）。

## 一、测什么、怎么测

| 边 | 覆盖 | 结果 |
|---|---|---|
| 采集判定 | `metrics_sig` 取整；负载 0.25 变/0.02 不变；内存 64MB 变/10MB 不变；state/cpu 变；`should_report`：首次必报、同值 10s/299s 不报、300s 心跳报 | C68 全过 |
| 通道 | 本体 `T_APPEAR="world/appear"` + `declare_subscriber(T_APPEAR)`；上报端 `session.put(topic)` | C68 静态断言 |
| 接收端 | 建个体；更新（version++、不重复建、更新账带 before）；同值重报不带 before；caps 能力上报不落字段；`local_id→name` | C68 全过 |
| 反例 | 缺必填 / 多塞 / 取值域 / 未知类 / 权威线违例 / 坏 JSON → 各自落拒绝码 | C68 全过 |
| 压力 | 100 次更新：仍 1 个体，+100 条账，+100 条事件，耗时 0.167s | C68 全过 |
| 事件 | `world/event` 只带公开字段；appear 也推事件 | C68 + VM 均过（见 bug） |
| 可见性 | `world/query kind=overview` 个体计数 = store 实际 | C68 全过 |
| VM 真总线 | 20s 窗口观察 + 注入合成 appear + 错误 reporter + 未知类 + 恢复真实值 | 9 项全 PASS（见下） |

## 二、VM 真总线结果（`pipeline_live_test.py --seconds 20`）

```
PASS 登录拿票 | ticket=tk-ee9911d8c
PASS 变化驱动（窗口内出现次数 < 窗口秒数/5） | new=0          ← 20 秒闲时 0 条真实上报
PASS 注入 appear 后 world/query kind=type 能查到标记值 | load1=3.14
PASS 账里有注入那一笔（带 before/after） | at=2026-10-20T16:51:33.285016+02:00
PASS 事件流收到 appear（本笔修了 family=change 不推事件的 bug） | events=1
PASS 错误 reporter 被拒（AUTHORITY_NOT_OWNER） | 新增 1 条
PASS 未知类被拒（APPEAR_CLASS_UNKNOWN） | 新增 1 条
PASS 恢复真实值（load1 回到本机真实值） | load1=0.21 real=0.21
{'ok': true}
```

完整输出：`scripts/release/evidence/t483-pipeline-live-test.txt`。

## 三、测出的真 bug（已修）

- **现象**：数据管道的 `appear` 一直**不推 `world/event`**；界面事件钩子（`space.on_activity_event`）等于死的，实时只能靠 5 秒轮询。
- **根因**：`World.stamp()` 只在 `family == "act"` 时推事件；`appear/register` 的 family 是 **"change"**。
- **修复**：`family in ("act", "change")`；C68 断言「appear 必推事件」；VM 现取 `events=1` 验证修复。

## 四、登记的安全缺口（如实）

- **上报者身份只靠 `reporter` 字符串**：测试脚本无任何凭证，只要把 reporter 写成 `world://computer/leap16`，
  本体就接受并写库（测试注入 load1=3.14 成功落库）——**总线无 ACL**，字符串可伪造。
- 影响：任何连上总线（tcp/7447）的进程都能伪造 `world/appear` 改对象状态（动作路径有 permit，这条路径没有）。
- 建议下一步：`world/appear` 加**提供者签名**（permit-ts 或新 key），或总线 ACL / mTLS；在法里登记来源身份。

## 五、没测到的（如实）

- 心跳 300s 的**真机长窗口**没等（C68 只测判定函数；VM 20s 窗口内无心跳）；要验可跑 6 分钟；
- 多提供者并发写同一对象（presentation/space/agent 同时）没做压测；
- 外部数据源管道（文件/DB/HTTP）没接，不在本报告范围。

## 六、复跑方式

```bash
# 本机全量判据（含 C68）
python scripts/test/check.py
# VM 真总线（在 VM 上）
python3 /root/aios/scripts/release/pipeline_live_test.py --seconds 20
```
