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
