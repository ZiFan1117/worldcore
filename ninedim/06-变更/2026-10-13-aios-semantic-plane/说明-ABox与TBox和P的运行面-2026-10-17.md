# **ABox / TBox** 和 P 的「运行面」 —— 以及我们差在哪（2026-10-17）

> ★ **作者问（逐字整理）**：「P 开源版里头所谓的就是它那个**运行面是干了哪些事儿**呢？因为我们之前一直说 **ABox、TBox** 和这个是什么关系呢？」

---

## §一 ★★★ 先给结论：P 的运行面干【四件事】

| # | ★ 件 | ★ 文件（现取） | ★ 和 ABox/TBox 的关系 |
|---|---|---|---|
| **1** | ★★ **存 ABox**（世界里实际有什么） | ★ `engine/object_store.py`（**223 行**） | ★★★ **它就是 ABox** |
| **2** | ★★ **改 ABox**（动作的 effects） | ★ `engine/action_executor.py`（**163 行**） | ★ **不是 ABox** —— 它是「世界怎么变」 |
| **3** | ★★ **记变更**（谁改了什么） | ★ `engine/audit_log.py`（**90 行**） | ★ **不是 ABox** —— 它是「变更的账」 |
| **4** | ★ **读 ABox**（查询） | ★ `engine/query_engine.py`（**113 行**） | ★ **不是 ABox** —— 它是「读 ABox 的方法」 |

★★★ **⇒ 一句话**：★ **`engine/` ＝ 一个 ABox 存储 ＋ 三个对它的操作（改／记／读）。**

---

## §二 ★★★ ABox / TBox 到底对应什么（★ 逐字）

### §二·1 ★★ TBox（术语箱）＝ `core/`

★ P 的 `core/` 七件：★ `ontology.py`（5 个 `register_*`）／`object_type`／`link_type`／`action_type`／`function`／`interface`／`data_types`。
★★ **⇒ TBox ＝ 「这个世界允许什么形状」**：★ 有哪些类、哪些关系、哪些动作、哪些函数、哪些接口。★ **全是【声明】，一条实例都没有** ✓

### §二·2 ★★★ ABox（断言箱）＝ `object_store.py` 里的 `ObjectInstance`

★ **逐字**（`object_store.py:14-25`）：

```python
@dataclass
class ObjectInstance:
    """An instance of an ObjectType."""
    instance_id: str
    object_type_id: str                                    ← ★ 它是【哪一类】的实例
    properties: dict[str, Any] = field(default_factory=dict)  ← ★ 它的【属性值】
    links: dict[str, list[str]] = field(default_factory=dict) ← ★ 它和别的实例的【关系】
    created_at / updated_at: datetime
    created_by: str = ""
    version: int = 1
```

★ 而 `ObjectStore` 的方法：★ `create`／`get`／`update`／`delete`／`search`／`create_link`／`get_linked`／`count`／`get_all_instances`
★★ **⇒ ABox ＝ 「这个世界里实际有什么」**：★ 一条条实例（★ 属性 ＋ 关系 ＋ 版本 ＋ 谁建的）✓

### §二·3 ★★★ 所以 ABox/TBox 的图是

```
★ TBox（core/）        ：类／关系／动作／函数／接口  —— 【声明】世界允许什么形状
        │
        │ ★ 实例化（instance of）
        ▼
★★ ABox（engine/object_store.py）：ObjectInstance —— 【断言】世界实际有什么
        ▲
        │ ★ 改（effects）／记（audit）／读（query）
  engine 的另外三个文件
```

★★★ **⇒ engine 的四个文件里，★ 只有 `object_store` 是 ABox；★ 另外三个是【对 ABox 的操作】。**

---

## §三 ★★★★ 我们的对照（★ 一好四坏）

| ★ 层 | ★ P | ★★ 我们 | ★ 状态 |
|---|---|---|---|
| ★ **TBox** | ★ `core/`（5 个 register_*） | ★ `core/registry.rs` ＋ `crates/aios-ontology/`（★ 9 类 ／ 9 动作 ／ 3 关系 ／ 9 函数） | ★★ **有** ✓ |
| ★★ **ABox** | ★ `ObjectInstance`（★ **8 格**：instance_id／object_type_id／**properties**／**links**／created_at／updated_at／**created_by**／**version**） | ★★ **两套**（★ 见 §四） | ★★ **有两套，用错了那套** ✗ |
| ★ **改 ABox** | ★ `action_executor._apply_effect`（★ create／edit／delete／link／notification） | ★★ **没有** ✗ | ★★ **缺** ✗ |
| ★ **记变更** | ★ `audit_log`（★ 90 行，★ 在跑） | ★ `engine/ledger.rs`（★ 有实现）★ 但**没接进任何进程** | ★ **有没接** ◐ |
| ★ **读 ABox** | ★ `query_engine`（★ 113 行，★ filter／navigate／order_by／count） | ★★ **没有**（★ `Individuals.present()` 只列名单） | ★★ **缺** ✗ |

---

## §四 ★★★★ 真缺口：我们有【两套 ABox】，而本体进程用的是【弱的那套】

| ★ 套 | ★ 在哪 | ★ 存什么 | ★ 谁在用 |
|---|---|---|---|
| **1** | ★ `core/registration.rs::Individual` | ★★ **只有 3 格**：`class`／`local_id`／`state` | ★★ **本体进程在用**（★ `world/appear`） |
| **2** | ★ `engine/instances.rs::Instance`（**232 行**） | ★★ **`kind` ＋ `fields`（任意字段 map）**，★ **照本体逐格校**（★ 六条规矩：缺必填／值类型／取值域 都拒）＋ 三张目录（主／名字／类） | ★★ **没有任何进程在用** ✗ |

★★★ **⇒ 结论**：★ **我们【已经有】一个像样的 ABox**（★ `engine/instances.rs`，★ 232 行，★ 照本体逐格校）★ —— ★ **只是本体进程没接它，接的是 3 格那套** ✗
★★ **⇒ 这就是「本体进程该实现什么框架」的答案里【最实的一格】**。

---

## §五 ★★★ 那本体进程的完整框架（★ 五件）

| # | ★ 件 | ★ P 的对应 | ★ 我们 |
|---|---|---|---|
| **1** | ★★ **TBox（声明面）** | ★ `core/` | ★★ **有** ✓（★ `registry.rs` ＋ `aios-ontology`） |
| **2** | ★★ **ABox（个体面）** | ★ `object_store` | ★★ **有，用错了那套**（★ 该把 `engine/instances.rs` 接进本体进程）✗ |
| **3** | ★★ **改 ABox**（执行结果写进个体） | ★ `action_executor._apply_effect` | ★★ **没有** ✗ |
| **4** | ★★ **记变更**（账） | ★ `audit_log` | ★ **有实现没接** ◐ |
| **5** | ★ **读 ABox**（查询） | ★ `query_engine` | ★★ **没有** ✗ |

★★★ **⇒ 一件好的（TBox），一件有但接错（ABox），一件有没用（账），两件缺（改 ABox／读 ABox）。**

---

## §六 ★★★ 一处【要你裁】的分歧（★ P 和我们不一样）

| ★ 问题 | ★ P 的做法 | ★ 你说的 |
|---|---|---|
| ★★ **「改 ABox」归谁** | ★★ **执行器改**（★ `action_executor` 直接 `store.create/update/delete`） | ★ 你说「**本体只干……执行状态**」★ ⇒ ★ **该由本体改** |

★★ **两者可以统一**：★ **载体执行完 ⇒ 【报给本体】⇒ 本体改 ABox ＋ 记账** ★ —— ★ 这样既符合你说的，★ 也符合 08 逐字「**执行器不能写账本（只能请求内核追加）**」✓

---

## §七 ★ 本件不能证明的事（如实）

- ★ P 的四个文件行数／`ObjectInstance` 8 格／`ObjectStore` 9 个方法／`action_executor` 的方法清单 —— 都是**现取**；
- ★ 我们的 `Individual` 3 格／`Instance`（kind＋fields）／`Instances` 的六条规矩与三张目录 —— 都是**现取**；
- ★★ **「改 ABox 该由本体做」是【按作者话推的】** ★ —— ★ P 的做法相反（★ 执行器直接改）★ ⇒ ★ **这一格要作者确认** ✗；
- ★★ **「本体进程该用 `Instances` 而不是 `Individuals`」是我的判断** ★ —— ★ **我没有核** `Instances` 能不能直接接（★ 它要 `RegisterEnv`：registry／spec／governance／ledger **四个面都在**）✗；
- ★ 本件**没改代码、没改本体** ⇒ ★ 门禁 **C1–C26 全绿**。
