# 判读：`cell`（格）与 `presence`（在场者）—— 作者判「不是类」，本席查实确认，并修正判据

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S2 | 意图 | 二 框架 ／ 六 规格 | **0.1（判读·待裁）** |

> **作者原话（逐字）**：「`cell`（格）……`presence`（在场者）……**这两个不是类吧，这怎么能成为类**。」
> **件性质**：判读件。★ **结论待人签**；★ 已同步两席（task-9／task-10）复核。

---

## §一 ★★★ 本席查实：作者判对了，而且证据很硬

### `presence`：`_links` 一共 **9 条边，其中 8 条围着它**

| 边 | 两端 |
|---|---|
| `human-declares-presence` | `human` → `presence` |
| `agent-declares-presence` | `agent` → `presence` |
| `application-declares-presence` | `application` → `presence` |
| `service-declares-presence` | `service` → `presence` |
| `device-declares-presence` | `device` → `presence` |
| `workflow-declares-presence` | `workflow` → `presence` |
| `runs-on` | `presence` → `presence` |
| `speaks-on` | `presence` → `port` |

⇒ ★★ **六条边写着「6 种主体各自申报在场」** ⇒ ★★★ **`presence` 就是「那 6 种主体在不在场」的那一格** —— ★ **它不是第 7 种东西**。

### `cell`：它**依附**屏面，且字段全是"界面怎么画"

| 现取 | 说明 |
|---|---|
| `fields.owner = ref(surface)` | ★ **它依附屏面**（`owner` 指回所属屏面） |
| `_links.cell-of: cell → surface` | ★ 边也说明「格属于屏面」 |
| 另 11 个字段：`shown`／`label`／`value`／`tooltip`／`style`／`component`／`agentAction`／`localAction`／`enabled` | ★ **全是界面渲染** |

⇒ ★ `cell` 是**屏面的组成部分**（★ 离开屏面不存在）—— ★ **不是独立的东西**。

## §二 ★★★ 判据修正（本席上一稿漏了这一问，认）

| | 内容 |
|---|---|
| ★ **上一稿（不完整）** | 「有指认格（`name`／`did`／`path`…）⇒ 是类」 |
| ★★ **修正后（两问）** | ★ **① 能指认**（有名字／路径／身份）**＋ ② 能独立存在**（不依附于别的东西）⇒ **才是「东西」（类）**；★ **只满足① ⇒ 它是「别的东西的一部分／一个面」**，不是类 |

**两问套一下**：

| 类 | ① 能指认 | ② 能独立存在 | 判 |
|---|---|---|---|
| `human`／`agent`／`application`／`service`／`device`／`workflow` | ✓ `name`／`did` | ★ **✓ 能** | ★ **是类** |
| `surface`（屏面） | ✓ `name` | ★ ✓ 能（它是"屏幕那一面"） | ★ **是类** |
| `port`（端口） | ✓ `name`／`path` | ★ ✓ 能（"跨进程进出的那一处"） | ★ **是类** |
| ★ `cell`（格） | ✓ `owner` | ★★ **✗ 依附屏面** | ★ **不是类**（屏面的一部分） |
| ★ `presence`（在场者） | ✓ `name`／`did` | ★★ **✗ 依附 6 种主体** | ★ **不是类**（主体的在场状态面） |
| `ledger`（账本） | ✓ `path` | ★ ✓ 能 | ★ **是类** |

## §三 ★★ 代价（比撤 `notice` 大得多）

| 类 | 引用面（现取） |
|---|---|
| ★ `presence` | ★ `_links=17`／`_permissions=9`／`_governance=7`／`_actions=7`／`_functions=6`／`_property_types=5`／`_modules=5`／`_standards=1`／`_storage_class_map=1` |
| ★ `cell` | `_property_types=12`／`_governance=3`／`_modules=3`／`_links=2`／`_storage_class_map=1` |

⇒ ★★ **`presence` 是"枢纽"**（8 条边围着它）⇒ ★ **不能照 `notice` 那样一刀撤** ⇒ ★ **该先出方案**（★ 与那 7 个类的做法一致）。

## §四 两类的落点（★ 待人裁，本席不代定）

| 类 | 候选落点 |
|---|---|
| ★ `cell` | ★ **甲：并进 `surface`**（如 `surface` 加一个 `cells` 格）／★ 乙：**保留但标为"屏面的组成部分"**（★ 不进"独立的类"名单）／★ 丙：撤 |
| ★★ `presence` | ★ **甲：做成一个"状态面"**（★ 比照 `_clock`／`_units` 那种"给判据读的格"）／★ 乙：**并进各主体**（6 个主体各加一个"在场"格）／★ 丙：撤 |

★ **本席倾向（非结论）**：★ `cell` **甲**（它是屏面的格，属性上属于屏面）；★ `presence` **甲**（它是一个**状态面**，且 6 条边可以改成"主体各自带在场格"）。

## §五 本件没做的事（如实）

1. ★ **没动本体**（★ 两个类都还在 `_objects`）；
2. ★ **没估**撤这两个的完整代价（★ 只给了引用面的处数）；
3. ★ **没读** `_permissions`／`_governance` 里围着 `presence` 的那 16 处（★ 只数了数）。
