//! 实例面 —— 把账本折成"现在是什么样"。
//!
//! 实例**不是另存的一份料**，而是从账本算出来的（`lib.rs` 硬点④：状态是算出来的 ⇒
//! 不存在"状态与账本不一致"）。本夹两件：`readmodel` 算（`M03`）、`checkpoint` 缓存（`M08`）。
//! 本 `mod.rs` 是**面件**，不占模块号；登记见 `WC-MODREG-001` §2.1 的例外清单。

pub mod checkpoint;
pub mod readmodel;
