//! 内置执行器 —— **只有这些事需要碰到载体**，所以只有这些事在这里。
//!
//! 三个执行器各自守着自己的边界：
//!
//! | 执行器 | 它碰什么 | 它特意**不**做什么 |
//! |---|---|---|
//! | `backlight` | 读/写背光设备 | 不校验"该不该调"——调之前门禁已经裁决过 |
//! | `package` | 调包管理器；高危动词前先做载体撤销点 | 不做"要不要确认"的判断——那是清单的 `confirm` 栏 |
//! | `job` | 起长任务；完工后**回写一条结果事件** | 不自己维护"待办清单"——状态由账本折叠算出 |
//!
//! ## ★ 执行器的名字分两栏，不许混
//!
//! [`Provider::name`] 是**实现词／设备词**（`backlight`／`package`／`job`）——回答"**怎么实现**"；
//! [`Provider::capabilities`] 是**语义层的名字**（`notice.mute`／`ledger.compact`／`job.start`）——
//! 回答"**叫什么**"，与本体 `_interfaces`、`cap.d` 的 `capability` 同一套词表。
//!
//! 这两栏一旦混用，`cap.d` 与执行器就会**各有一个合法名字、却对不上**，而这一格
//! 在 2026-10-04 之前**从来没有任何调用点读过**（详见 [`cross_check`]）。

// ── 装配面：本夹只做**声明与再导出**，不放实现（一件一职责，见同夹各件）──

mod backlight;
mod cross_check;
mod execute;
mod job;
mod package;
mod registry;

#[cfg(test)]
mod unit;

pub use backlight::Backlight;
pub use cross_check::cross_check;
pub use execute::execute;
pub use job::Job;
pub use package::Package;
pub use registry::Registry;
