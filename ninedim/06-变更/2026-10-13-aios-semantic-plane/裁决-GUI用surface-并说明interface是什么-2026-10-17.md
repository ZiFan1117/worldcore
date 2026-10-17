# 裁决：**GUI 用 `surface`** ＋ 说明：**`interface` 是什么意思**（2026-10-17）

> ★ **作者裁（逐字）**：「**用 surface**」。
> ★ **作者问（逐字）**：「**interface 是什么意思**」。

---

## §一 ★★★ `interface` 是什么意思（★ 逐字）

★ **本体里的定义**（`ontology.json` 的 `interfaces._element`）**逐字**：

> ★「**接口·能力（Interface）—— 可读／可配／可调**」

★ **同段的 `_comment` 逐字**：

> ★「『这类东西能被怎样对待』。条文落在**能力**上（不是落在具体类型／具体对象上）—— 授权只在 `permissions` 里按**能力名**给。」

★★ **⇒ 在【我们这套】里，`interface` 不是「图形界面」的意思，★ 是「接口·能力」—— ★ 一种【能被怎样对待】的声明面** ✓

### §一·1 ★★★ 而它作为【注册者类别】用时，含义是【谁注册的】

★ `registered_by_kind` 的注释**逐字**（`core/registration.rs`）：

> ★「★ **哪一类注册者**：world／system／app／interface（★ 本体 C16 的闭集）」

★★ **四类 = 四种「谁」**：

| ★ 类别 | ★ 谁是 | ★ 现取例子 |
|---|---|---|
| ★ `world` | ★ **世界自己** | ★★ **本体里那 9 条动作全是它**（★ 现取 `{"world": 9}`） |
| ★ `system` | ★ **系统**（★ 这台机器） | ★ `fs.list`（`ls`）／`service.start`（`systemctl`）／`pkg.install`（`apt`）… **8 条** |
| ★ `app` | ★ **应用** | ★ `app.download.start`（`curl`） |
| ★★ **`interface`** | ★★ **界面** | ★★ `interface.ask_permission`／`interface.notify` —— ★ **`program` 是空串 `""`**（★ **不跑命令**） |

### §一·2 ★★★ 所以 `interface` 的动作**长什么样**（★ 现取，最有说服力）

★ **映射表现取 11 行**：

```
fs.list                    kind=system     program="ls"
fs.stat                    kind=system     program="stat"
service.start              kind=system     program="systemctl"
service.stop               kind=system     program="systemctl"
pkg.install                kind=system     program="apt"
proc.list                  kind=system     program="ps"
device.eject               kind=system     program="eject"
device.brightness.set      kind=system     program="brightnessctl"
★ interface.ask_permission  kind=interface  program=""   ← ★ 不跑命令
★ interface.notify          kind=interface  program=""   ← ★ 不跑命令
app.download.start         kind=app        program="curl"
```

★★★ **⇒ `interface` 那两条是【跟人打交道】的动作**：★ **问授权**（`ask_permission`）／**通知人**（`notify`）★ —— ★ **它们没有命令可跑，★ 因为它们的「执行」就是【在人面前出现】** ✓

---

## §二 ★★★ 那 `interface` 和 `surface` 有什么区别（★ 两个不同的轴）

| ★ | ★ `surface` | ★★ `interface` |
|---|---|---|
| ★ 它是哪一【轴】 | ★★ **对象类**（`objects` 里的一员） | ★★ **注册者类别**（`registered_by_kind` 四类之一） |
| ★ 逐字定义 | ★「一块可被指向、可被撤回的持续体（continuant）：★ **它是屏幕那一面**，不是世界状态的另一份载体。」 | ★「**接口·能力（Interface）—— 可读／可配／可调**」 |
| ★ 回答什么问题 | ★★ **「屏幕是什么东西」** | ★★ **「这个动作是谁交上来的」** |
| ★ 能成为个体吗 | ★★ **能** ✓ | ★★ **不能**（★ 它不是类）✗ |
| ★ 今天有人用吗 | ★ 没有（★ GUI 还没写） | ★ 有 —— ★ 那两条 `interface.*` 动作 |

★★★ **⇒ 一句话**：★ **`surface` 是 GUI 作为【一个东西】的类；★ `interface` 是 GUI 作为【动作提供方】的类别** ✓

---

## §三 ★★★ 你的裁决落到哪：「用 surface」

★ **裁决：GUI 进程成为个体时，用 `surface` 类** ✓

```
★ GUI 进程（A2UI 渲染）
   │
   │ ① 【成为个体】★ surface/a2ui        ← ★ 你的裁决：用 surface
   │    （★ 因为 surface 的逐字定义就是「屏幕那一面」）
   │
   │ ② 【报它的动作】★ registered_by_kind = "interface"
   │    ★ 例：interface.ask_permission（问人要不要批）、interface.notify（通知人）
   │    ★ ★ 这两个动作【没有 program】—— 它们的「执行」就是在人面前出现
   ▼
★ 整个显示由它出
```

★★★ **⇒ 两者【不冲突，而是配套】**：★ **`surface` 说「它是屏幕」，★ `interface` 说「它交上来的动作是跟人打交道的那些」** ✓

### §三·1 ★★ 顺带解释一处旧疑点

★ `core/command_bridge.rs:302` 有一条测试**逐字**：

```rust
table.appear(&ont, "interface", "a2ui", "started").is_err()
```

★★ **⇒ 那是「拿 `interface` 当【类】去让 a2ui 成为个体」⇒ 会拒** ★ —— ★ **那条测试是对的** ✓（★ `interface` 不是类）
★★★ **⇒ 现在有了正确写法**：★ **`appear(&ont, "surface", "a2ui", "started")`** ✓

---

## §四 ★★ 一句话记住

> ★★★ **`surface` 是【屏幕那一面】（一个对象类）；★ `interface` 是【接口·能力】（一种注册者类别，★ 它的动作不跑命令、只跟人打交道）。**
> ★★ **GUI 的「东西」那一半用 `surface`；★ 它的「动作」那一半用 `interface`。**

---

## §五 ★ 本件不能证明的事（如实）

- ★ `interfaces._element` 与 `_comment` 的逐字、★ `registered_by_kind` 的注释逐字、★ 映射表 11 行、★ 本体 `{"world": 9}` —— 都是**现取**；
- ★★ **「`interface` 的动作是跟人打交道的」是我的解读** —— ★ 逐字只说到「接口·能力——可读／可配／可调」；★ 我**从「`program` 是空串」推出「不跑命令」**（★ 这一条是硬的：★ `check()` 对 interface 类放行无 program）★ —— ★ 但 **「所以它是跟人交互」那一层是我的话，★ 不是我引的** ✗；
- ★★ **「GUI 成为 `surface`」现在是【你的裁决】** ✓ ★ —— ★ 但★ **「GUI 的动作 kind 是 `interface`」那是我的推断**（★ 你说的是「用 surface」）★ —— ★ **这条要你再确认**（★ 也可能 GUI 的动作是 `app` 类）✗；
- ★ 本件**没改代码、没改本体** ⇒ ★ 门禁 **C1–C26 全绿**。
