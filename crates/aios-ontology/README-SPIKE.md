# SPIKE 记录：把本体接进 AIOS（MVP，2026-10-13）

> 分支 `spike/ontology-mvp` ｜ **这是一次一次性验证，不是产品路径**。
> 要证的只有一件事：AIOS 认知核产出的 `action_name`，其权威来源可以不是提示词里的自由字符串，而是**我们的本体**。

## 一、做了什么（**只增件，没动上游**）

| 件 | 是什么 |
|---|---|
| `crates/aios-ontology/data/ontology.json` | 08 仓本体**原样**拷入（**971,997 B**，未改一个字节） |
| `crates/aios-ontology/src/lib.rs` | 装载／校验面：照本体的 `_five_elements._reading_order` 逐节读五节，缺一节即**拒启** |
| `crates/aios-ontology/src/bin/demo.rs` | 演示：把一个动作名喂进去，看它过不过 |
| `crates/aios-ontology/tests/mvp.rs` | **8 条判据**（含会红的反例） |
| `Cargo.toml`（仓根） | `members` **加一行** |

## 二、读数（四要素）

| 项 | 现取 |
|---|---|
| **命令** | `cd /root/aios && cargo test -p aios-ontology` |
| **原始输出** | `8 passed; 0 failed; 0 ignored; finished in 0.05s` |
| **退出码** | **0** |
| **时点** | 2026-10-13，客户机 `leap16`（openSUSE Leap 16.0，8 核） |

**看得见的验收（demo）**：

- `demo` ⇒ 动作 **9** 条／能力 **9** 条／入口表 **0** 条／宿主命令 **12** 条；两条缺口**如实报出**
- `demo notice.mute` ⇒ **过**（命中能力 `notice.mute`，缺的必填参数 `["subject"]`）
- `demo file.read` ⇒ **拒**（错误码 `ext.world.Ontology.ActionUnknown`）

## 三、★ 八条判据

1. `loads_our_ontology_and_sees_9_actions` —— 现取 9 条动作／9 个能力
2. `accepts_a_declared_action` —— `notice.mute` 过
3. ★ `rejects_aios_prompt_example_file_read` —— AIOS 提示词里的**合法例子**，在我们的世界里**不存在** ⇒ 拒
4. ★ `rejection_is_driven_by_the_ontology_not_hardcoded` —— 把 `file.read` 声明进本体后，**同一个调用从拒变过** ⇒ 闸门由本体驱动，不是硬编码
5. `missing_section_is_refused` —— 缺 `_actions` ⇒ 拒启
6. `command_literal_in_entry_table_is_refused` —— 入口表里放 `pacman` ⇒ 红（对应本体的 `_no_command_literal`）
7. `unknown_capability_is_refused` —— 动作引用不存在的能力 ⇒ 拒
8. `empty_function_table_is_reported_as_a_gap` —— 入口表空 ⇒ **如实报缺口，不许当已立**

## 四、证明了什么／**没**证明什么

**证明了**：AIOS 那条「一句话 → 类型化动作」的链，**动作名的闸门可以挂在本体上**，而且**只增件、不改上游**。

**没证明（如实登记，不许读多）**：

1. **还没接进 `aios-cognitive`** —— MVP 校验的是翻译器**产出的形状**，没有真跑模型那一环；
2. **入口表仍是空表** —— MVP 的闸门挂在 `_actions` 那 9 条上；缝合图纸第③处要的 `_functions.entries`（**入口名表**）**还是空的** —— 那是产品活；
3. **没有端到端** —— 渲染器／策略内核／系统测试那一段都没碰。

## 五、下一步（回正式流程）

本 MVP 等于把方案 `2026-10-13-方案-把本体接进AIOS.md` 的 **S2／S3／S4 提前验了一遍**：

- 用本次读数把方案的 S2–S4 判据**写实**（谁红谁绿已经知道）；
- **产品化时把调试用的 `demo` 与这份 spike 说明摘掉**，只留 `lib` ＋ 判据；
- **入口表怎么填**（从 `_actions`／`_interfaces` 出发）是本轮之后最大的一块产品活。

