# 长城任务交接页（2026-10-20 01:0x Asia/Shanghai / 19:0x CEST）

> 给「下次接手的人或 agent」：目标链还在跑，到 **06:00 Asia/Shanghai（00:00 CEST）** 自动全停。
> 本页只写**怎么接、怎么查、怎么停、怎么救**，不写过程（过程在 `ninedim/06-变更/.../改动对照.md`）。

## 一、现在有什么（现取）

| 件 | 状态 |
|---|---|
| 目标链 `aios-dsh-goal.timer` | 每 **30 分钟**一轮（`aios-dsh-goal.service`），高权限 `optimize` profile |
| 进化链 `aios-dsh-evolve.timer` | 每 **6 小时**一轮（只提案，不落法） |
| 自优化链 `aios-dsh-optimize.timer` | 每 **12 小时**一轮（高权限，快照＋验收＋回滚） |
| 看门狗 `aios-watchdog.timer` | 每 **3 分钟**：7 单元、本体可装起、资源、定时器失败即停、脚本语法自愈 |
| 世界快照 `aios-world-snapshot.timer` | 每 **1 小时**（`/var/backups/aios/world-snapshots/`，保留 24 份） |
| 截止停链 `aios-goal-stop.timer` | **2026-10-20 00:00:00 CEST**（=06:00 Asia/Shanghai）强停三条 DSH timer |
| 判据护栏 | VM 工作副本 `/root/aios-work/scripts/test/`（本地副本，**不入 git**）；`bash /usr/local/bin/aios-gate.sh /root/aios-work` |
| 现取 | 7 单元 active；watchdog `fail=0 units_ok=7 law=一致`；目标链一轮正在跑（19:00:15 起） |

## 二、怎么查（一行命令）

```sh
# 进度 / 报告 / 商量板
tail -20 /root/aios-goals/progress.md
ls -lt /root/aios-goal-reports/ | head
tail -30 /root/aios-goals/board.md
# 健康
tail -3 /var/log/aios-watchdog.jsonl
systemctl list-timers 'aios-*' --no-pager
for u in aios-bus aios-ontology aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do echo "$u=$(systemctl is-active $u)"; done
# 判据
bash /usr/local/bin/aios-gate.sh /root/aios-work; echo "gate_rc=$?"
# 快照
python3 /root/aios/scripts/release/world_snapshot.py list | tail -3
```

## 三、怎么停（任何时候）

```sh
systemctl stop aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer
# 到点自动：aios-goal-stop.timer 会做同样的事，并写 /root/aios-goals/DONE
```

## 四、出问题怎么救

| 症状 | 先看 | 处置 |
|---|---|---|
| 轮次没报告（no progress） | 该轮 `.log` 末尾 | 常见是 DSH **10 步预算**耗尽（agent 已自己诊断过）：把任务压成一步（health 预跑）或拆小；也可让下一轮先诊断 |
| 验收红 / 回滚 | 报告里的 `gate_rc` / `bad=` | 看 `/tmp/aios-gate.log` 红条目；修好后再起一轮 |
| 定时器被看门狗停 | `/var/log/aios-watchdog.log`、`/root/aios-goals/ALERT` | 按告警修；修好后 `systemctl start aios-dsh-goal.timer ...` |
| `goal-run` 语法坏 | `bash -n /usr/local/bin/aios-goal-run.sh` | 看门狗会自动从 `/root/aios/scripts/release/dsh/goal/run.sh` 恢复；也可手动装 |
| 本体装不起来 | `python3 /root/aios/scripts/release/export-law.py --check` | 看门狗会用 `/var/backups/aios/lastgood.tar.gz` 恢复 |
| 世界数据坏了 | `world_snapshot.py list` | `restore --snap <DIR> --yes`（先备份；默认不重启，加 `--restart` 才重启；**真账回滚仍建议维护窗口**） |

## 五、交接时的已知缺口（如实）

1. **真账 restore 未演练**（只在临时副本验证过）；
2. `world_ask` 端到端未验；人确认/委托（四格）未定；事件「掉线补推」未做（只有回放）；
3. 场景/应用文件化（P3）、A2UI 跟版（P5）、agent-进程可观测（P7）、世界分叉/时间线（P4 全量）未做；
4. **安全债**：VM 里 DSH 仍是 `danger-full-access`（为自优化临时放开），应收回到 workspace-write＋按需提权；
5. VM 上判据副本是手动 scp 的，重建 clone/重装会丢（需固化安装脚本）；
6. agent 本地提交（`99fe79b` 等）只在 `/root/aios-work`，未 push（by design）；`src/event/` 观察器与主机 T-405 实现是两份（主机为准）；
7. 判据不推；08 不参与。

## 六、06:00 核对清单

```sh
cat /root/aios-goals/DONE                 # 到点停链的标记
systemctl is-enabled/is-active aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer
tail -20 /root/aios-goals/progress.md     # 终报/进度
ls -lt /root/aios-goal-reports/ | head     # 各轮报告
tail -3 /var/log/aios-watchdog.jsonl       # 最后健康读数
```

**判成功不看你"觉得"**：看 `DONE`、timer 是否停、报告里有没有证据、账里拒绝码有没有恶化。
