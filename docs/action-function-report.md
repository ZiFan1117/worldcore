# ontology action / function 补全报告（P1）

> 作者 2026-10-21：「本体里头的 action 和 function……必须补全，该读的读，该统计的统计」。
> 范围：`13-aios-worldcore`（08 不参与）。判据 C77/C78。

## 一、action：从“声明了但没执行者”到“能跑/能回/能落账”

| 动作 | 之前 | 现在 |
|---|---|---|
| `notice.mute` / `notice.unmute` | 在册但无路由 ⇒ PROVIDER_NOT_DECLARED | 本体内建执行；静音写入 `world.muted_notice_kinds`，`_notice_and_forward` 记账但不转发 |
| `job.start` / `job.finish` / `job.cancel` | 同上 | 本体内建作业表（job_id/state/actor/时间），状态机 running→finished/cancelled |
| `presence.report` | 同上 | 本体内建在场记录（actor→subject/时间） |
| `ledger.compact` / `world.rekey` / `world.migrate` | 无路由（或权限拒后才暴露） | **显式 `UNSUPPORTED` + 原因**：账只增不改 / 不可逆，P1 不做；落账，不再伪装“路由不存在” |

实现：`src/ontology/ontology_builtins.py`；`ask_path` 在参数/票/身份/许可/前置校验之后接内建分支，回 `world/ask/result` 并落 ask/result 或 reject 账。

## 二、function：从 metadata-only 占位到可执行只读函数

旧的 9 个函数 `implementation=null`，只是“动作实现面”的占位。现替换为 **8 个可执行只读函数**：

| 函数 | 做什么 | 隐私 |
|---|---|---|
| `fn.world.overview` | 类/接口/关系/动作/函数/个体/账行统计 | 公开 |
| `fn.world.class_counts` | 每个类的个体计数 | 公开 |
| `fn.ledger.stats` | 账行/家族/种类/拒绝码/首末时间 | 公开 |
| `fn.action.stats` | 本体动作/注册表/计算机可用/不支持计数 | 公开 |
| `fn.file.stats` | 宿主 file 个体的种类/根/总字节 | 公开（只统计） |
| `fn.worldfs.stats` | wfile/wversion/wpath 计数/状态/字节 | 公开（只统计） |
| `fn.object.get` | 按类+name 读一个对象 | **要票/已报到身份** |
| `fn.object.find` | 按类+等值条件查对象（≤100） | **要票/已报到身份** |

执行：`world/query kind="function"`（`name` + `params` + 可选 `ticket`）；函数只读，不写世界、不落账。
实现：`src/ontology/world_functions.py`；`world_query.py` 的 `function` 分支。

## 三、判据与现取

| 判据 | 覆盖 |
|---|---|
| **C77** | 8 函数法登记/implementation/endpoint；统计函数可执行且与本体/对象库一致；读函数无票拒、带票能读；未知函数拒；查询只读（账行数不变） |
| **C78** | 内建动作直接执行与 ask_path 带票执行；静音生效；参数错误码；不支持动作显式 `UNSUPPORTED`；ask_path 不再出现 `PROVIDER_NOT_DECLARED` |

本机：`python scripts/test/check.py` → **78/78 全绿**；法 **27 类 / 211 动作 / 8 函数**。

## 三半、VM 现取（2026-10-21 20:05 +08:00，16/16 PASS）

```
15/15 单元 active（aios-ontology、aios-worldfs 都在）
PASS fn.world.overview：classes=27 functions=8 individuals=74
PASS fn.world.class_counts：sum=74
PASS fn.ledger.stats：rows=26320（last_at 现取）
PASS fn.action.stats：world_actions=211 registry=44
PASS fn.file.stats：file 4（3 file + 1 dir），bytes=3859035
PASS fn.worldfs.stats：wfile 3 / wversion 3 / wpath 3
PASS 读函数无票被拒；带票可查（rows=1）
PASS function 查询只读（账里 qfn-* 查询行=0）
PASS notice.mute / job.start / job.finish
PASS ledger.compact ⇒ code=UNSUPPORTED（账只增不改；已落账 3 行）
PASS 无新 PROVIDER_NOT_DECLARED（历史 1 行，前后不增）
```

## 四、没做到的（如实）

1. 作业/在场/静音是**本体内存状态**，不持久化（重启清空）；P2 可落对象/账恢复；
2. 函数只做统计/读取；复杂聚合/查询语言/权限分级（privacy class）未做；
3. `ledger.compact/world.rekey/world.migrate` 按不变量**明确不做**；
4. 函数结果不落账（只读，OK）；UI 暂未单列 functions 面板（overview 已列名字）。

## 五、复跑

```bash
python scripts/test/c77_functions.py --self-test
python scripts/test/c78_builtin_actions.py --self-test
python scripts/test/check.py
```
