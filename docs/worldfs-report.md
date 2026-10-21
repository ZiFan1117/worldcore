# worldfs P1 报告：语义文件系统（独立进程）

> 现取：2026-10-21 晚。作者：「好的，那就专门建一个语义文件系统」「文件系统，单独进程」。
> 设计件：[`worldfs-design.md`](worldfs-design.md)；本报告只写**做到了什么、怎么验、没做到什么**。

## 一、交付

| 件 | 现取 |
|---|---|
| 独立进程 | `src/worldfs/`（`aios-worldfs`，**第 16 个单元**）——不混 computer、不写宿主文件 |
| 存储 | `/var/lib/aios/worldfs/`：`blobs/sha256/<前2>/<sha>`（内容寻址，原子写、只读）+ `worldfs.db`（SQLite：objects/versions/paths，WAL+FULL） |
| 语义 | 路径是视图，对象身份 `wobj_…` 与路径解耦；版本 `wver_…` 不可变；**本地无账，账在本体** |
| 法 | 4 类（`worldfs`/`wfile`/`wversion`/`wpath`）；10 动作（读 5；写 5：write/mkdir/remove/restore/rename） |
| 写保护 | 4 个写动作进 `CONFIRM_ACTIONS`；读 scope 人+agent，写 scope 只给人；permit 一号一用；每次写落账 |
| 本地账 | **无**：没有 txns/审计表；actor/intent/时间/许可/结果只在本体 ledger |
| 判据 | **C76**（先写会红反例，`--self-test` 绿）：路径越界/相对/根写/根删/非空目录/坏 blob/缺 intent/未知动作全拒；写→blob+版本+指针；覆盖 seq+1；旧版本可回滚；同内容去重；对象身份稳定；写动作在 CONFIRM_ACTIONS；进程/单元/deploy/看门狗；接收端联动 |
| 本机 | `python scripts/test/check.py` → **76/76 全绿**；法 **27 类 / 211 动作**（世界 55＋sys 156）/ 9 函数 |

## 二、VM 验收（`worldfs_live_test.py`，17/17 PASS）

```
PASS 登录拿票
PASS worldfs.state 可读（root=/var/lib/aios/worldfs）
PASS worldfs.mkdir /worldfs/notes
PASS worldfs.write 第一版（seq=1，blob sha 64 位）
PASS 写入返回 blob/版本（ver=wver_…）
PASS worldfs.read 内容 == hello world
PASS stat 对象身份稳定（obj=wobj_…）
PASS 覆盖产生 seq+1 且对象身份不变（seq=2，同 obj）
PASS 版本历史 [1,2]
PASS 回滚到旧版本且内容恢复（seq=1，text=hello world）
PASS 同内容去重（blobs 2→2，dedup=true）
PASS list 含 hello/dup
PASS 删除后不可读（不存在）
PASS 缺 intent 被拒（PARAM_MISSING）
PASS 重启后数据仍在（text=hello world）
PASS world/query kind=type 能查到 wpath（3 个）
PASS 账里有 worldfs.write 成功记录（5 行）
{"ok": true}
```

VM 现取：`aios-worldfs` **active**；16 单元全 active；存储根 384K；blobs 2 个；`aios-fs`/`aios-worldfs` 是两个独立单元。

## 三、测出并修的真问题

| 项 | 内容 |
|---|---|
| 现象 | 首次部署 `aios-worldfs` 起不来：`status=226/NAMESPACE`，`Failed to set up mount namespacing: /var/lib/aios/worldfs: No such file or directory` |
| 根因 | `ReadWritePaths=/var/lib/aios/worldfs` 要求该路径在 **命名空间建立前就存在**；ExecStartPre 在命名空间之后才跑，救不了 |
| 修复 | `ReadWritePaths=/var/lib/aios`（父目录已存在且可写）＋ `ExecStartPre=install -d /var/lib/aios/worldfs`；单元注释写明原因；VM 重启后 active |

## 四、没做到的（如实）

1. **没有 FUSE/POSIX 挂载**：现在只能通过 `world/ask worldfs.*` 访问，不是能 `cd/ls` 的挂载点（P2）；
2. 文本 ≤1MB、单进程、无分块/压缩/加密/GC/配额；已有 rename/move；目录不递归删；无二进制/大文件；
3. 写动作目前**只给人**（agent 写会被权限拒；agent 若将来要写，先走确认+委托）；
4. 人类直接 `world/ask worldfs.write` 视为“本人在场”，不会再弹一次确认；agent 请求才会走 `CONFIRM_ACTIONS` 的弹窗/委托路径；
5. 账里 `worldfs.write` 的 `text` 参数未脱敏（P1 文本；后续按 privacy class 处理）。

## 四半、最终 VM 读数（2026-10-21 19:50 +08:00）

| 项 | 现取 |
|---|---|
| 单元 | **16/16 active**（16 个单元含 aios-worldfs） |
| worldfs 存储 | objects=4、versions=5、paths=3、blobs=2（去重后）；**本地无 txns** |
| 世界个体 | 账里 worldfs 2、wpath 12、wfile 5、wversion 10（进程/路径/对象/版本都成了世界个体） |
| worldfs 动作结果 | 16 行（read/state/write/list/remove 都 ok=True；删后 read ok=False 符合预期） |
| **agent 写拒绝（运行时）** | `world_cli` 以 agent 身份 ask `worldfs.write` ⇒ `CONFIRM_REQUIRED`（confirmation=cf-…）；**路径未创建**（0 行） |
| 人类写 | 走 `world/ask`＋permit＋账；本人直接请求视为在场（不再弹一次确认）；agent 请求才走弹窗/委托 |

## 四又二分之一、2026-10-21 裁决：worldfs 不记账

作者令：「我们这个文件系统你不记帐好吧，都在本体里面」。

| 之前 | 现在 |
|---|---|
| 本地有 `txns` 表 + `_txn()`，记 actor/action/path/seq/intent | **删**；worldfs 只存 blob/objects/versions/paths 技术索引 |
| objects/versions/paths 带 created_at/created_by/intent/updated_at/updated_by | **删**；时间/actor/intent/许可/结果只在 `world/ask`、`world/exec/result`、本体 ledger |
| 读/写成功后 wfile/wversion/wpath 带审计字段 | 只报内容/版本/路径事实；审计查本体账 |
| 旧库 v1 | 自动迁移 v2：保留技术行，删 txns/审计列（C85） |

## 四又四分之三、P2：FUSE 只读挂载（2026-10-21 晚）

| 项 | 现取 |
|---|---|
| 独立进程/单元 | `src/worldfs/worldfs_fuse.py`；`aios-worldfs-fuse.service`（**第 16 单元**） |
| 挂载 | `/aios/worldfs` → worldfs 命名空间 `/worldfs`；内核 `mount` 可见 `fuse.worldfs (ro,...)` |
| 实现 | ctypes 直调 libfuse3（无第三方 Python FUSE 包）；getattr/readdir/open/read/access；dir 0555、file 0444 |
| VM 验收 | **11/11 PASS**：ls/cat；worldfs 动作写的新文件 FUSE 立刻读到；FUSE 写/删被拒（Read-only）；服务重启后挂载恢复且数据仍在 |
| 遇到的坑 | ① opendir 最初复用了 open（对目录返回 EISDIR）→ 单独 opendir；② systemd 的 `PrivateTmp=yes` 会建私有挂载命名空间，FUSE 挂载宿主不可见 → `PrivateTmp=no`；`ProtectSystem` 也会关挂载进私有命名空间 → `ProtectSystem=no` + `PrivateMounts=no` |
| 仍只读 | 写走 worldfs 动作（人确认+permit+账）；挂载是**只读投影**，不做写挂载 |

## 五、怎么复跑

```bash
# 本机
python scripts/test/check.py
python scripts/test/c76_worldfs.py --self-test
# VM（部署后）
python3 /root/aios/scripts/release/worldfs_live_test.py
# 看存储/账
ls -la /var/lib/aios/worldfs
sqlite3 /var/lib/aios/worldfs/worldfs.db 'select count(*) from objects; select count(*) from versions;'
grep -a worldfs.write /var/lib/aios/ontology/ledger.jsonl | tail -3
```

## 六、P2 建议

1. **FUSE 只读挂载** `/worldfs`（能 `ls/cat`；写挂载另议）；
2. 分块/去重块、GC、配额；大文件/二进制；
3. rename/move（对象身份稳定，指针 move）；
4. privacy class / 账参数脱敏；
5. 写确认链路在桌面的实际弹窗验收（agent 写 + 人签）。
