# 判据护栏（VM 侧）—— 让自优化的 agent 能自己跑判据

> ★ 作者令：「我们主要做一个监测，别让他系统自己跑崩了」；`os-gaps.md` 里把「判据护栏」列为最缺口。
> ★ 硬规矩：**判据不推**——`scripts/test/` 在 `.gitignore` 里（VM 仓是 ignored 的本地副本），
>   我们从主机 scp 过去只给 agent 自验，**不进 git、不推远端**。

## 一、为什么要它

没有判据时，agent 改完只跑 `export-law --check`，看不到 45 条判据（C4 行尾、C9 静默兜底、C27 行数、
C45 事件流契约……）。一改就可能把已做好的东西弄坏而不自知。

## 二、怎么装（主机 → VM，一次性）

```sh
# 主机
tar -czf /tmp/aios-tests.tgz scripts/test
scp -i D:\vm\keys\vm_ed25519 -P 2223 /tmp/aios-tests.tgz root@127.0.0.1:/root/
# VM
cd /root/aios-work && rm -rf scripts/test && tar -xzf /root/aios-tests.tgz && rm -f /root/aios-tests.tgz
```

装好后 `/root/aios-work/scripts/test/check.py` 可跑；`git status` 不会把它算进去（ignored）。

## 三、怎么跑

```sh
bash /usr/local/bin/aios-gate.sh /root/aios-work   # 0=绿；1=红；2=环境
```

## 四、目标链怎么用它（已接）

`aios-goal-run.sh` 在**验收**一步，如果：

1. `scripts/test/check.py` 在（本机副本在）；
2. 工作副本**已经和 `origin/main` 对齐**（`git rev-list --count origin/main..HEAD` == 0），

才跑判据；**红 ⇒ 记 `gate-red` 并回滚**（与法/单元验收同级）；没对齐就只记 `gate-skip:drift`（等合并后再启用）。

## 五、现取（2026-10-20 凌晨，已实跑）

- VM 工作副本与 `origin/main` 合并后，`bash /usr/local/bin/aios-gate.sh /root/aios-work` ⇒ **全绿（45/45，rc=0）**；
- 关键一条：**VM 上 `/usr/lib/aios` 有 `sysknife-command-map.json`，host 判据环境没有**。不清掉它，
  `build_aios_ontology()` 会把 156 条 `sys.*` 收进来、C17 报「未授权」；清空 `AIOS_SYSKNIFE_MAP=""`
  后与 host 判定一致。★ 这不是绕过：`sys.*` 的 `required_roles` 是真议题，属「作者定法」的范围，已记入
  改动对照 T-407，不擅自改。
- 对齐判断改为 `git merge-base --is-ancestor origin/main HEAD`（合并后仍 ahead，但已含主机全部提交）。

## 六、事故与自愈（2026-10-20 凌晨）

- **事故**：18:30 那轮 agent 想优化自己（health.sh 预跑、changed 计数），直接改了 `/usr/local/bin/aios-goal-run.sh`，
  改出**语法错**（`unexpected EOF while looking for matching '"'`，systemd `status=127`）。看门狗按设计停掉三条定时器，等人看。
- **处置**：从本仓 `scripts/release/dsh/goal/run.sh`（T-407 版）装回 `/usr/local/bin`；`bash -n` 两脚本通过；
  三条 timer 恢复；立刻起一轮验证。
- **加固**：看门狗新增 ②b——`bash -n /usr/local/bin/aios-goal-run.sh` / `aios-gate.sh` 不过就从 `/root/aios` 恢复；
  `GUARDRAIL.md` 规矩：**agent 要改 runner，只能改 `/root/aios-work` 里的副本并交人安装，不许直接改 `/usr/local/bin`**。

