# worldfs 设计：worldcore 的语义文件系统（P1）

> 作者 2026-10-21 裁决：「专门建一个语义文件系统」。
> 本文是 **P1 的设计件**：自有命名空间 + 内容寻址 blob + 不可变版本 + 路径指针 + 人确认写 + 回滚。
> FUSE/POSIX 挂载、分块/GC/配额放 P2/P3（见 §12）。
> 借鉴 AI-OS `002…/L2_AIOS_FS/` 的**形状**（对象/版本/chunk/指针/事务），不搬代码、不做 RDF/OWL。

## 1. 定位与边界

- **是什么**：一个新的底层进程 `src/worldfs/`（单元 `aios-worldfs`，第 15 个单元）——
  一个**以对象身份而非路径为主**的语义文件系统；文件内容按 sha256 内容寻址；每次写产生不可变版本；
  路径只是指向某个版本的**指针/视图**；写操作必须人确认并落账。
- **不是什么**：
  - 不是 POSIX/FUSE 挂载（P2 才做只读挂载）；
  - 不是宿主机文件树的写代理（宿主机只读桥仍是 `src/fs/` 的 `file.*` v1）；
  - 不混进 computer（computer 是系统管理执行器，保持广权限边界）；
  - 不做分块/去重块级/GC（P3）。

## 2. 不变量（P1 必须成立）

| # | 不变量 | 怎么验 |
|---|---|---|
| I1 | **内容不可变**：版本一旦创建不修改；同内容 = 同 blob（sha256 去重） | 两次写同内容，blob 文件数不增；旧版本按 seq 仍可读 |
| I2 | **路径是视图**：路径指针 move 不创建新对象；对象身份 `wobj_…` 稳定 | 覆盖/回滚后对象 id 不变 |
| I3 | **写必须人确认**：`worldfs.write/mkdir/remove/restore` 属于 `CONFIRM_ACTIONS` | 无确认的 ask 被 `CONFIRM_REQUIRED` 拒 |
| I4 | **写必落账**：每次写/回滚都有 `worldfs.*` 动作账（ask/result/permit-use） | 账里能按 path 查历史 |
| I5 | **命名空间封闭**：只接受 `/worldfs/...` 绝对路径；`..//.`、相对路径、NUL、超长段全拒 | 反例全红 |
| I6 | **不碰宿主路径**：所有 blob/db 都在 `/var/lib/aios/worldfs/`；世界路径不带宿主 /etc /root | 静态 + 行为 |

## 3. 命名空间

- 世界根：`/worldfs`（P1 固定根，不允许别的根）；
- 路径规则：绝对、以 `/worldfs` 开头、段数 ≤32、每段 1..128、禁止 `.` `..`、禁止 `//`、禁止 NUL/控制字符；
- 根目录 `/worldfs` 是目录，不能写内容、不能删除；
- P1 不实现 rename/move（P2 再谈）；对象身份与路径解耦，为将来 move 留位。

示例：`/worldfs/notes/hello.txt`、`/worldfs/docs/`。

## 4. 存储布局

```
/var/lib/aios/worldfs/
├─ blobs/sha256/<前2位>/<完整sha256>     # 内容寻址，原子写（temp+fsync+rename）
├─ worldfs.db                            # SQLite（WAL）
└─ tmp/                                  # 临时文件（同分区 rename）
```

### 4.1 SQLite 表

```sql
-- 逻辑对象（身份稳定；与路径无关）
CREATE TABLE objects (
  obj_id TEXT PRIMARY KEY,          -- wobj_<uuidhex>
  kind TEXT NOT NULL,               -- file | dir
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  state TEXT NOT NULL,              -- active | retired
  current_seq INTEGER NOT NULL DEFAULT 0
);

-- 不可变版本（只 INSERT，不 UPDATE/DELETE）
CREATE TABLE versions (
  ver_id TEXT PRIMARY KEY,          -- wver_<uuidhex>
  obj_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  blob_sha256 TEXT NOT NULL,        -- 文件内容；dir 为空串
  size INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  intent TEXT,
  UNIQUE(obj_id, seq)
);

-- 路径指针（可变；一个路径 → 对象 + 版本）
CREATE TABLE paths (
  path TEXT PRIMARY KEY,            -- /worldfs/...
  obj_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  kind TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);

-- 事务（崩溃恢复/审计辅助；世界账仍是权威）
CREATE TABLE txns (
  txn_id TEXT PRIMARY KEY,          -- wtxn_<uuidhex>
  at TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  path TEXT,
  obj_id TEXT,
  seq INTEGER,
  before_seq INTEGER,
  intent TEXT
);
```

## 5. 法（world.json）

### 5.1 类

| 类 | 关键属性 | 报告者 |
|---|---|---|
| `worldfs`（进程个体） | name/state/root/objects/paths | `world://worldfs` |
| `wfile`（逻辑对象） | obj_id（主键）/name/kind(file,dir)/state/current_seq/blob_sha256/size/updated_at | `world://worldfs` |
| `wversion`（不可变版本） | ver_id（主键）/obj_id/seq/blob_sha256/size/created_at/created_by/intent | `world://worldfs` |
| `wpath`（路径视图） | path（主键）/obj_id/seq/kind/updated_at | `world://worldfs` |

### 5.2 动作

| 动作 | 类别 | 参数 | 许可 scope |
|---|---|---|---|
| `worldfs.list` | read | path, limit | user + agent/dsh |
| `worldfs.stat` | read | path | user + agent/dsh |
| `worldfs.read` | read | path, max_bytes | user + agent/dsh |
| `worldfs.versions` | read | path | user + agent/dsh |
| `worldfs.state` | read | — | user + agent/dsh |
| `worldfs.write` | **change** | path, text, intent | user |
| `worldfs.mkdir` | **change** | path, intent | user |
| `worldfs.remove` | **change** | path, intent | user |
| `worldfs.restore` | **change** | path, seq, intent | user |

- 所有 change 动作加进 `src/ontology/gate/world_codes.py` 的 `CONFIRM_ACTIONS`；
- 写动作没有 `intent` ⇒ `PARAM_MISSING`；
- 读动作对 agent 开放，写动作 P1 只给人。

## 6. 请求流

### 6.1 读（`worldfs.read`）

```
world/ask → 本体八道闸 → permit → world/exec route=worldfs
→ 进程验 permit/核销 → store.read(path)
→ 路径→(obj,seq)→blob（校验 sha256/大小）→ 返回 text/truncated/ver_id
→ 报 wpath/wfile/wversion 个体（world/appear）→ 回 world/exec/result
```

### 6.2 写（`worldfs.write`，人确认）

```
world/ask → 八道闸：CONFIRM_REQUIRED（人确认弹窗）→ 人签 → 委托/一次性 permit
→ world/exec route=worldfs → 进程验 permit/核销
→ store.write(path, content, actor, intent)：
   ① 内容 sha256 + 原子写 blob（已存在则去重）
   ② BEGIN；对象不存在则建 obj；seq = max(seq)+1；插 version；upsert path→seq；插 txn；COMMIT
→ 报 wpath/wfile/wversion 个体 → 回结果
```

### 6.3 回滚（`worldfs.restore`）

- 校验 path 存在、seq 属于同一对象、blob 仍完好；
- 只把 `paths.seq` 指回旧 seq（对象/版本不动）；记 txn + 世界账；
- 之后的写会在 `max(seq)+1` 生成新版本，不覆盖旧版本。

## 7. 内容寻址与崩溃安全

- blob 写：`tmp/<uuid>` → `fsync` → `rename` 到 `blobs/sha256/<前2>/<sha>`；已存在则丢弃临时文件；
- 先写 blob，后写 db；db 事务提交前崩溃 ⇒ 孤儿 blob（P3 GC 处理，读不受影响）；
- 读时校验 sha256 与 size；不匹配 ⇒ 拒（坏 blob 不返回内容）；
- SQLite `journal_mode=WAL`、`synchronous=FULL`（P1 正确性优先）。

## 8. 进程与部署

- `src/worldfs/`：
  - `worldfs_store.py`：纯存储类（可单测）；
  - `worldfs_ops.py`：路径校验 + 动作 dispatch（不连总线）；
  - `worldfs_process.py`：报到/注册/订 `world/exec`（route=worldfs）/验 permit/回结果/报个体。
- 单元 `scripts/release/systemd/aios-worldfs.service`：
  - `ExecStartPre` 建 `/var/lib/aios/worldfs`；
  - `ReadWritePaths=/var/lib/aios/worldfs`（只写这里；`ProtectSystem=strict`）；
  - `NoNewPrivileges`、`PrivateTmp`；
- deploy.sh / 看门狗加入 `aios-worldfs` ⇒ **15 单元**；
- 不新增出向命令（无 subprocess）⇒ C19 不破。

## 9. 判据（C76 起，先写会红反例）

C76 覆盖：

1. 法：4 类 + 9 动作在册；change 动作在 `CONFIRM_ACTIONS`；许可 scope 正确；
2. 路径：非 `/worldfs` 根、相对、`..`、`//`、NUL、超长、根目录写/删 ⇒ 全拒；
3. 写：`write` 生成 blob/version/path/txn；同内容两路径 **blob 去重**；覆盖产生 seq+1 且旧版本仍可读；
4. 回滚：`restore` 后 head=旧 seq、对象 id 不变、版本历史不丢；
5. 删除：`remove` 后 path 不可读、对象 retired、账有记录；
6. 坏 blob：把 blob 内容改掉 ⇒ `read` 拒（sha 不匹配）；
7. 权限/确认：写动作无确认 ⇒ `CONFIRM_REQUIRED`；agent 写 ⇒ `PERMISSION_DENIED`（P1 只给人）；
8. 进程/部署：单元、deploy、看门狗、注册五格、`world/exec/result` 回话；
9. 接收端：`wfile/wversion/wpath` 个体能建；错误 reporter 拒。

## 10. 验收（P1）

- 本机 `check.py` 全绿（C76 新增，其余不回归）；
- VM：`aios-worldfs` active；真人确认一次写 → blob/版本/指针/账齐；重复内容去重；回滚；越权/穿越拒；
- 证据：`scripts/release/worldfs_live_test.py` 输出 + 账/存储读数。

## 11. 非目标（P1 明确不做）

- FUSE/POSIX 挂载；块级分块/压缩/加密；GC/配额；rename/move/符号链接；目录递归删除；
- 二进制/超大文件（P1 文本 ≤1MB）；多写者并发冲突合并（SQLite 串行 + 单进程）。

## 12. 阶段

| 阶段 | 内容 |
|---|---|
| **P1（本次）** | 本设计 §2–§10：worldfs 进程 + blob + 版本 + 路径指针 + 读写/回滚 + 人确认 + C76 + VM 验证 |
| P2 | FUSE 只读挂载 `/aios`（或 `/worldfs`）；写挂载需另议 |
| P3 | 分块/去重块/GC/配额/大文件/并发冲突 |
