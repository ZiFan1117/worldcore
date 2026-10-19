# 长城任务交接页（更新：2026-10-20 03:3x Asia/Shanghai / 21:1x CEST）

> 给「06:00 以后接手的人或 agent」：目标链到 **06:00 Asia/Shanghai（00:00 CEST）** 自动全停。
> 本页只写**现有什么、怎么查、怎么停、怎么救、还缺什么、06:00 核对清单**；过程在 `ninedim/06-变更/…/改动对照.md`。

## 一、现在有什么（现取口径）

| 件 | 状态 | 位置 |
|---|---|---|
| 目标链 `aios-dsh-goal.timer` | 每 **30 分钟**一轮（高权限 optimize） | — |
| 进化链 `aios-dsh-evolve.timer` | 每 **6 小时**（只提案） | — |
| 自优化链 `aios-dsh-optimize.timer` | 每 **12 小时**（快照＋验收＋回滚） | — |
| 看门狗 `aios-watchdog.timer` | 每 **3 分钟**（7 单元/法一致/资源/失败即停/脚本自愈） | — |
| 世界快照 `aios-world-snapshot.timer` | 每 **1 小时**；保留 24 份；`fork` 可出平行世界 | `/var/backups/aios/world-snapshots/` |
| 轮次评估 `aios-goal-eval.timer` | 每 **15 分钟**：`rounds.jsonl`＋人读 `rounds.md` | `/root/aios-goals/` |
| 世界文件 `aios-worldfs.timer` | 每 **15 分钟**：账→`events/`、画布→`scenes/` | `/var/lib/aios/world/` |
| 截止停链 `aios-goal-stop.timer` | **2026-10-20 00:00:00 CEST** 强停三条 DSH timer | — |
| **guard（权限决定）** | 独立进程 `aios-guard`；Unix socket `/run/aios/guard.sock`；与本体 `can_execute` 同口径 | `src/guard/guard_process.py` |
| **guard-exec（权限执行）** | Landlock 给子进程限文件访问；`--dry-run`/`--apply` | `src/guard/guard_exec.py`，策略 `scripts/release/guard-exec-policy.json` |
| **语音浏览器** | 独立进程 `aios-web`：`GET /` 页面、`/events` SSE、`/cmd`、`/render` 静态预览、`/agent` 心跳；支持 `?user=&secret=` 自动登录与 `Last-Event-ID` 断线补漏 | `src/web/`，端口 8765 |
| 游标/补推 | 空间/agent 回放带 `since`；`/var/lib/aios/cursors/*.json` | — |
| 场景文件 | 每次出画布落 `/var/lib/aios/scenes/<surface>.json` | — |
| agent 心跳 | `/run/aios/agent-heartbeat.json`（pid/last_at/events/round） | — |
| 判据护栏 | `scripts/test/check.py`（**56 条**，本地不推） | VM 副本 `/root/aios-work/scripts/test/`；`bash /usr/local/bin/aios-gate.sh /root/aios-work` |

★ 单元共 **9 个**：bus/ontology/guard/web/computer/presentation/render/space/agent。

## 二、怎么查（一行命令）

```sh
python3 /root/aios/scripts/release/status.py        # ★ 一屏看全（快照/进度/轮次摘要/游标/场景/世界文件/guard/单元）
python3 /root/aios/scripts/release/status.py --json # 机读
python3 /root/aios/scripts/release/dsh/goal/final_report.py --out /root/aios-goal-reports/FINAL.md  # ★ 06:00 终报
```

```sh
# 进度 / 报告 / 摘要 / 商量板
tail -5 /root/aios-goals/progress.md
ls -lt /root/aios-goal-reports/ | head
head -20 /root/aios-goals/rounds.md
tail -30 /root/aios-goals/board.md
# 健康
tail -2 /var/log/aios-watchdog.jsonl
systemctl list-timers 'aios-*' --no-pager
for u in aios-bus aios-ontology aios-guard aios-web aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do echo "$u=$(systemctl is-active $u)"; done
# 判据
bash /usr/local/bin/aios-gate.sh /root/aios-work; echo "gate_rc=$?"
# 世界文件 / 快照 / 分叉
ls /var/lib/aios/world/events | tail -3
python3 /root/aios/scripts/release/world_snapshot.py list | tail -5
python3 /root/aios/scripts/release/world_snapshot.py timeline | tail -5
# 权限 / 浏览器
python3 /root/aios/src/guard/guard_process.py --check world://user/zhang sys.GetMemoryInfo
curl -s http://127.0.0.1:8765/agent
```

## 三、怎么停（任何时候）

```sh
systemctl stop aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer
# 到点自动：aios-goal-stop.timer 做同样的事，并写 /root/aios-goals/DONE
```

## 四、出问题怎么救

| 症状 | 先看 | 处置 |
|---|---|---|
| 轮次没报告 | 该轮 `.log` 末尾 / `rounds.md` | 常见是 DSH **10 步预算**耗尽；把任务压成一步（health 预跑）或拆小 |
| 验收红 / 回滚 | 报告 `gate_rc` / `/tmp/aios-gate.log` | 修好再起一轮；不许绕判据 |
| 定时器被看门狗停 | `/var/log/aios-watchdog.log`、`/root/aios-goals/ALERT` | 修好后 `systemctl start aios-*` |
| 单元写盘报 `Read-only file system` | 单元 `ReadWritePaths` 与目录是否存在 | `deploy.sh` 已先建 `/var/lib/aios/{cursors,scenes}`；缺目录时 ReadWritePaths 不生效 |
| 本体装不起来 | `export-law.py --check` | 看门狗用 `/var/backups/aios/lastgood.tar.gz` 恢复 |
| 世界数据坏了 | `world_snapshot.py list/verify` | `restore --snap <DIR> --yes`（先备份；**真账回滚建议维护窗口**） |
| 浏览器打不开 | `systemctl is-active aios-web`；`curl /agent` | DNS/隧道问题；页面隧道：`ssh -L 8765:127.0.0.1:8765` |

## 五、还缺什么（如实，别当已完成）

1. **两份法草案没合并**：`src/ontology/proposals/{memory,delegation}.proposal.json`（机器校验 `law_proposal.py --check` 全绿），**等人签**；签后要改 `world.json`＋实现动作＋判据；
2. **场景只能落盘，不能加载/切换**；**世界分叉只能看，不能在上面跑**（要维护窗口）；
3. **真账 restore 未演练**（只在临时副本演习过）；
4. **真人语音**（Web Speech 说/听）未验，要人拿 Chrome/Edge 点；
5. **安全债**：VM 里 DSH 仍 `danger-full-access`；bus 无 ACL；旧账有明文票（无效但仍需清理）；
6. **判据不推**（本地副本）；VM `/root/aios-work` 的 agent 本地提交不 push（by design）。

## 六、06:00 核对清单

```sh
python3 /root/aios/scripts/release/status.py     # ★ 一屏状态（含非 active 单元）
python3 /root/aios/scripts/release/dsh/goal/final_report.py --out /root/aios-goal-reports/FINAL.md  # ★ 终报
cat /root/aios-goals/DONE                        # 到点停链的标记
systemctl is-active aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer   # 应 inactive
tail -10 /root/aios-goals/progress.md            # 最后几轮
head -20 /root/aios-goals/rounds.md              # 轮次质量
ls -lt /root/aios-goal-reports/ | head           # 各轮报告
tail -2 /var/log/aios-watchdog.jsonl             # 最后健康读数
ls -dt /var/backups/aios/world-snapshots/*/ | head -3  # 最后快照
```

**判成功不看你「觉得」**：看 `DONE`、timer 是否停、报告里有没有证据、账里拒绝码有没有恶化。
