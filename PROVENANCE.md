# PROVENANCE · 本仓是什么

> 本件是本仓的**出生证明**：说自己从哪来、按谁的许可、与哪一盒同链。

## 一、本仓是什么

**`13-aios-worldcore`** —— 以 **`AI-Native-Linux (AIOS)`** 为**底座**的世界核（worldcore）产品仓。
作者 2026-10-13 定：**底座换成 AIOS ＋ 产品另立一仓**；本仓**不装** 08 仓的工程域与历史。

## 二、底座从哪来（可复算）

| 项 | 值 |
|---|---|
| 上游 | `https://github.com/ai-os-dot-net/AI-Native-Linux.git` |
| 取的那一版 | `babedc9eb8ee5ce57ba65a89607fb63cad8565ef`（2026-07-19 13:08:14 +0300，`Merge branch 'feature/r13.8-support-lifecycle' into 'main'`） |
| 许可 | **Apache-2.0**（上游 `LICENSE` 随树进来，未改） |
| 本地怎么来的 | 08 仓 `.refs/依赖仓/AI-Native-Linux` 的 checkout **去掉 `.git` 后整树拷贝** |
| ★ 一件要紧事实 | **那份 clone 是 shallow（`depth 1`／`rev-list --count HEAD = 1`）** ⇒ **本仓不带上游历史**；联网后要历史就 `git remote add upstream https://github.com/ai-os-dot-net/AI-Native-Linux.git && git fetch upstream` |

## 三、与 08 仓同链

| 项 | 值 |
|---|---|
| 决定这件事的盒 | `D:\Code\08-worldcore-openspec\ninedim\06-变更\2026-10-13-adopt-aios\` |
| 作者原话 | 「**首先，现在就是轮到AI OS.**」「**还有一个就是旧代码是要留的，是压缩一下**」 |
| 自研代码留档 | 08 仓 `.refs/退役-自研-2026-10-13/`（`worldcore-自研-2026-10-13.zip` ＋ `MANIFEST.md`，110 件逐件 sha256） |

## 四、本仓要加的是什么（只三处，见 08 仓 `2026-10-13-方案-AIOS-缝合图纸.md`）

1. `crates/aios-cognitive/src/intent.rs`：加**三档目标记账**（`planned`／`needs-input`／`unsupported`）；
2. `crates/aios-cognitive`：加**约束协商**（`confidence` 低时要有回路）；
3. ★ **加本体层**：把 `action_name` 从 `translator_system_prompt.txt` 的自由字符串，接到本体声明的入口表（本仓要带过来的就是 08 仓那一层）。

**AIOS 自己留好的接线钩子**：`002.AI-OS.NET--SPECREV.2/L7_Interaction_Renderers/02_shared_ui_schema.md` 的 §6.1／§6.2／§7.2。

## 五、没做到的（如实）

- **本仓尚未构建**：宿主 `D:\Code` 无 `cargo`／`rustc`（现取 `Get-Command` 皆空）⇒ 「骨架跑通」这一步要 Arch VM `newworld`，**未跑**；
- **上游历史未取**（shallow clone，见 §二）；
- **本体层尚未接进来**（第 3 处，未做）。
