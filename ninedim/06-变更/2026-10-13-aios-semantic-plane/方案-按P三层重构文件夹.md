# 方案（作者令）：按 Palantir 的三层文件夹重构 —— 3 个顶层 ＋ engine 下一堆子文件夹

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 三 结构 | **1.0（作者令，即刻执行）** |

> **作者令（逐字）**：「**我们应该按照这个文件夹呀，建立 3 个文件夹就行**……**有 8 个直接用 3 个文件夹**，然后**第二个里头有一堆子文件夹**，就完事了。**就按照他这个文件夹数的结构就行了**。」

---

## §一 ★★★ 目标结构（照 P 的三个目录）

```
crates/aios-worldcore/                ← ★ 一个 crate（不再拆成 10 个）
  src/
    lib.rs            门面：pub use 各面
    core/             ★ ① 定义层（照 P 的 core/）
      mod.rs
      types.rs        ★ 共同类型：Who / Reason / Refuse / Registration / Event
      registry.rs     ★ 面① 注册（本体里有哪些类型）
    engine/           ★★ ② 运行层（照 P 的 engine/）—— ★ **这个里头有一堆子文件夹**
      mod.rs
      instances.rs    面② 实例注册（装了啥／哪块界面）
      validate.rs     面③ 校验（进门安检）
      store.rs        面④ 实例存储
      query.rs        面⑤ 查询
      ledger.rs       面⑥ 账
      execute.rs      面⑦ 执行
    governance/       ★ ③ 治理（照 P 的 governance/）
      mod.rs          面⑧ 治理（权限 × 角色 × 标记）
```

⇒ ★★ **3 个顶层文件夹 ＋ `engine/` 下 6 个子文件夹** ✓（★ 正是作者说的形状）

## §二 ★★ 与现状的差（要重构的地方）

| 现状 | ★ 目标 |
|---|---|
| ★ **10 个 crate**（shared／registry／instances／validate／store／query／ledger／execute／governance／门面） | ★★ **1 个 crate**：`aios-worldcore` |
| ★ 共同类型在单独的 `aios-worldcore-shared` | ★★ **搬进 `src/core/types.rs`** |
| ★ 八面各一个 crate | ★★ **搬进 `core/`（1 面）／`engine/`（6 面）／`governance/`（1 面）** |

★ **为什么要合**：★ 作者令「**就按照他这个文件夹数的结构就行了**」—— ★★ **文件夹数照 P（3 个），不照"一个面一个 crate"** ✓
★ **代价（如实）**：★ 合并后**面与面之间不再有编译器的 crate 边界**（★ 只有模块边界）⇒ ★ **边界靠自觉 ＋ 判据**（★ 这是本令的代价，作者已知情）✓

## §三 ★★ 三席的活怎么办（他们正在写那 10 个 crate）

| 席 | 正在写 | ★ 处置 |
|---|---|---|
| `impl-a` | `-instances/` ＋ `-validate/` | ★ **写完就停**（★ 代码会被搬到 `engine/instances.rs`／`engine/validate.rs`，★ **内容照用**） |
| `impl-b` | `-store/` | ★ 同上（★ 搬到 `engine/store.rs`） |
| `impl-c` | `-tests/` | ★ 同上（★ 搬到 `tests/`） |

⇒ ★★ **他们的成果不浪费**：★ **Lead 合并时按 §一 的位置搬** ✓
★ **但他们在写期间不许提交**（★ 已约定）✓

## §四 执行顺序（Lead 做）

| 步 | 做什么 |
| **1** | ★ 等三席 complete（★ 或叫停） |
| **2** | ★ 建 `crates/aios-worldcore/src/{core,engine,governance}/` |
| **3** | ★ 把 10 个 crate 的 `src/*.rs` 按 §一 搬进去（★ 改 `mod` 与 `use` 路径） |
| **4** | ★ 删掉那 9 个 crate ＋ 根 `Cargo.toml` 的 members ＋ 登记面改成一条前缀 |
| **5** | ★ VM `cargo test -p aios-worldcore` ＋ `cargo fmt --all -- --check` ＋ `python verify/check.py` |
| **6** | ★ **每个文件仍 < 300 行**（★ 作者令） |

## §五 本件没做的事（如实）

1. ★ **还没动**结构（★ 等三席交件，免得冲突）；
2. ★ **没定** `core/types.rs` 是否要再拆（★ 现在 5 个类型合在一个文件，★ 约 200 行 ⇒ 可以）。
---

## §六 ★★ 更正（作者指着 `lib.rs` 那一行问）：**不要门面**

★ **`lib.rs` 是什么**：★ Rust 规定**每个 crate 必须有** `src/lib.rs`（或 `src/main.rs`）—— ★ **它是 crate 的入口，跑不掉**（★ 不是本席想加的东西）。

### ★★ 但"门面"那一段可以不要

| | ★ 甲：有门面（`pub use` 一堆） | ★★ 乙：**不要门面**（只三行 `pub mod`） |
|---|---|---|
| `lib.rs` 长什么样 | ★ `pub use engine::instances::Instances;` …（几十行导出表） | ★★ 只有三行：`pub mod core;`／`pub mod engine;`／`pub mod governance;` |
| 外面怎么用 | ★ `aios_worldcore::Instances`（★ 短） | ★★ `aios_worldcore::engine::instances::Instances`（★ **与文件夹一致**） |
| 好处 | ★ 调用路径短 | ★★ **结构一目了然；`lib.rs` 不会再长；东西住哪一眼就看见** |
| 坏处 | ★ 要维护一份导出表（★ 加面就得改它） | ★ 路径长一点 |

★★ **作者要的是"就照他的文件夹结构"** ⇒ ★ **那路径就该照文件夹走** ⇒ ★★ **取乙（不要门面）** ✓
★ 而 `lib.rs` 仍在，★ 但它**只当"根节点"**，★ 不再是"前厅"。

### ★ 顺带：P 那边对应的是什么

★ P 是 Python ⇒ ★ 它的"门面"是 `foundry_ontology/__init__.py`（★ 也有导出）⇒ ★ 但★ **P 的目录结构才是主角**（★ `core/`／`engine/`／`governance/`）✓

### ★★★ 修正后的目标结构

```
crates/aios-worldcore/
  src/
    lib.rs            ★ 只三行：pub mod core; pub mod engine; pub mod governance;
    core/
      mod.rs          pub mod types; pub mod registry;
      types.rs        ★ 共同类型
      registry.rs     面①
    engine/
      mod.rs          pub mod instances; pub mod validate; pub mod store; pub mod query; pub mod ledger; pub mod execute;
      instances.rs    面②
      validate.rs     面③
      store.rs        面④
      query.rs        面⑤
      ledger.rs       面⑥
      execute.rs      面⑦
    governance/
      mod.rs          （面⑧ 就在 mod.rs 里，或再开 rbac.rs／markings.rs）
```
