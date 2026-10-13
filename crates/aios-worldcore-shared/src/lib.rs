//! `aios-worldcore-shared` — 最小内核的**共同类型**。
//!
//! 为什么单独一个 crate：八个面都要用这同一批说法（谁／拒／为什么／要登记的东西／一件事）。
//! 若各面各写一份，就会有八份「拒」、八份「谁」—— 那正是重复的来源。
//!
//! ★ 参考 Palantir foundry-ontology 的 `core/data_types.py` 与 `governance/`：
//! 它把「值／标记／角色」这些**跨面共用的说法**放一处，各面只引用。
//!
//! ★ 每个类型都能指回本体的一处（见各文件的 `本体里对应` 注）。

pub mod event;
pub mod reason;
pub mod refuse;
pub mod registration;
pub mod who;

pub use event::{Event, EventSeq};
pub use reason::Reason;
pub use refuse::{Admit, Refuse};
pub use registration::Registration;
pub use who::Who;
