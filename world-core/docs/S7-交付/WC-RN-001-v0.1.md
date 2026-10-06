# WC-RN-001 版本说明

> 这份文档管**"这一版是什么、怎么跑起来、它今天还不能做什么"**。

## 一、当前版本

产品版本号写在源码里（**唯一出处**）：`world-core/src/common/event.rs` 的
`pub const WORLD_VERSION: u64 = 1;`，随每条事件落账（`world` 字段）。

怎么读出来（**现取**）：
```
cd world-core && ./target/release/world-core --ontology ontology.json --policy policy.json \
                            --ledger ledger.jsonl state --json
# 二进制名＝包名 `world-core`（`Cargo.toml` 无 `[[bin]]`）；三个路径参数是**必填**的，故从仓根直接写
# `world-core/target/release/world-core state --json` 会因找不到 `ontology.json` 而 rc=2
# 或直接看常量：Select-String world-core\src\event.rs -Pattern WORLD_VERSION
```

## 二、出厂形态（怎么构建、怎么跑）

```
cd world-core
cargo build --locked --release
./target/release/world-core --help
```
- **依赖锁定**：一律 `--locked`；
- **环境**：Rust `1.98.1`（`cargo`／`rustc` 同版）；**主机没有 Rust 工具链 ⇒ 构建与测试只在 VM**（见 `WC-ST-001` §二）；
- **数据的三个落点**：本体 `ontology.json`、策略 `policy.json`、账本 `ledger.jsonl`（路径由命令行给出）；
- **出厂门禁**：`bash check.sh`（清单与判据见 `WC-AT-001`）。

## 三、今天还不能做的（**如实**）

| 限制 | 在册处 |
|---|---|
| **机核层守卫（`WC-ATOM-001` §四）今天通过**：真源码环 `M04 ↔ M09` 已按"消回边、保留合法方向"改成 DAG（`src/bus/mod.rs` 用窄接口 `RequestSink`，`src/lib.rs` 为 `World` 实现）——**读数以 `bash check.sh` 与 `python world-core/tools/module_graph.py` 的输出为准，本节不复述数字** | `openspec/BOOK/冲突总账.md` 的"里程碑"一节 |
| 一批"规格已写、断言未写"的条目：转出到 `openspec/changes/fc-2026-004-assertions/`，**未勾完** | 该 change 的 `tasks.md` |
| **这一批 change 尚未归档**（它承载的九组能力**已落地并有会红的断言**：投递与应答、通道资源边界、家族演进与向前兼容、未知旗标与本体命名空间、`trace` 语义、通告的闸、写侧适配、读法是叶子、读模型缺格）——"落地"与"归档"是两件事，**本表说的是后者** | `openspec/changes/cover-unimplemented-capabilities/tasks.md` |
| `S5/S6/S7` 之外**没有**别的流程侧文档（文档集封闭，见 skill §二） | — |

**这些限制不是"待办的杂事"，是"这一版不能承诺的事"**——把没做到写成做到，是本项目最忌的一条。

## 四、权威在哪（同一件事只有一个出处）

| 问题 | 权威 |
|---|---|
| 世界必须怎样 | `openspec/specs/<能力>/spec.md` |
| 模块的契约（接口、依赖、不变量） | `world-core/docs/S2-设计/WC-IC-001-v0.1.md`（一册） |
| 模块号与源码的对应 | `world-core/docs/S2-设计/WC-MODREG-001-v0.1.md` |
| 规格承诺 ↔ 流程侧需求号 | `openspec/BRIDGE.md`（数值**现算**） |
| 这一轮改了什么、谁判的、谁签的 | `openspec/BOOK/冲突总账.md` |

## 五、这份文档不覆盖的

- **不写"某次发布的变更清单"**——那是 git 历史（提交信息即变更说明）；
- **不复述读数与条数**（会给命令）；
- **不承诺未来**——只写"今天是什么"。
