# VM 上的 DeepSeek Harness（DSH）—— 本体的「读」与「进化提案」

> ★ 范围：**只在 VM（openSUSE Leap 16，`/root/aios`）里**的一套 DSH 配置；不进 GUI，不改本仓运行时代码。
> ★ 作者口径（逐字整理）：「DeepSeek harness 应该是最新版；能读我们的本体；能改变改动我们的本体；能持续不断地进化」。

## 一、装了什么（现取）

| 件 | 位置 | 现取 |
|---|---|---|
| DSH CLI | `npm -g`：`@deepseek-ai/dsh@0.2.1-rc.2`（npm `latest` 同为此版） | `dsh --version` ⇒ 0.2.1-rc.2 |
| LLM 凭证 | `/root/.dsh/env.dsh`（`DEEPSEEK_API_KEY`，600） | 不进仓、不进账、不打印 |
| `headless` profile | `/root/.dsh/profiles/headless` | 世界 agent：带 `dsh-plugin-aios-world`（world_query / world_ask / world_ui，全部经本体） |
| `evolve` profile | `/root/.dsh/profiles/evolve` | 编码 agent：bash＋fs 都开（改本体、跑验证要动手） |
| 世界插件 | `/root/aios/dsh-plugins/aios-world`（本仓 `scripts/dsh-plugins/`，不入库） | 桥：`src/agent/world_cli.py`（本仓） |
| 进化仓 | `/root/aios-work`（GitHub 公开仓 clone，非部署副本） | 已 clone 到 `3a84c0d` |
| 进化循环 | `/root/aios-dsh-evolve.sh` ＋ `aios-dsh-evolve.{service,timer}` | 每 6 小时一轮；产物 `/root/aios-proposals/<stamp>.md` |

## 二、怎么装（幂等）

```sh
# 0) 前提：node/npm、全局 dsh、/root/.dsh/env.dsh、headless/evolve profile、/root/aios-work clone
# 1) 桥（本仓 src/agent/world_cli.py）随 deploy.sh 进 /usr/lib/aios/src/agent/
sudo bash scripts/release/deploy.sh
# 2) 进化链
install -m 755 scripts/release/dsh/evolve.sh /root/aios-dsh-evolve.sh
install -m 644 scripts/release/dsh/aios-dsh-evolve.service \
              scripts/release/dsh/aios-dsh-evolve.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now aios-dsh-evolve.timer
```

## 三、它怎么工作

1. **读本体（活的世界）**：headless profile 里 `world_query` ⇒ 桥 `world_cli.py` ⇒ `world/query` ⇒ 本体答（实测：kind=actions 答「22 个注册动作」）。
2. **读本体（法的源文件）**：evolve profile 有 fs 工具，读 `/root/aios-work/src/ontology/world.json`（实测：答「24 个动作」）。
3. **改本体**：evolve profile 可改 `world.json`，改完跑 `python3 scripts/release/export-law.py --check` 验（实测：改 `space.state` 描述 → check 绿 → `git checkout` 还原 → 仓库干净）。
4. **持续进化**：timer 每 6 小时跑一轮，DSH 从**账里真实拒绝码**出发写提案（含动机/改哪个动作/diff/风险/验证命令/是否触及「只有人定法」），**不落法、不改仓库、不提交、不推送**；人（作者）读提案后自己签。

## 四、限度（如实）

- 只做**提案**：法由人定（硬约束「正式结论与签字只有人能下」）；循环绝不自动改仓库；
- 每轮会调用 LLM（token 成本），默认 6 小时一轮；不要时 `systemctl disable --now aios-dsh-evolve.timer`；
- **没有 GUI**（按作者吩咐先不做界面）；
- `world_ask`（做事）在 headless profile 里可用，但本轮只验了查询/读文件/改法，**未正式验 world_ask**；
- 插件源 `scripts/dsh-plugins/` 被 .gitignore 忽略（本仓不入库），VM 上是单独拷进去的；
- 提案是「账证驱动」的：账里没有证据的改动不该提；账里票据明文已在 T-398 脱敏。
