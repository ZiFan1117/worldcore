//! 一件事 —— 账本上记的一行。
//!
//! 本体里对应：`envelope`（信封）＋ `families`（四族：change／act／notice／job）。
//!
//! ★ 与 Palantir 的 `AuditEntry` 同位置：序号 ＋ 谁 ＋ 什么时候 ＋ 做了什么。

use serde_json::{Map, Value};

use crate::who::Who;

/// 账本上的位置（全局单增，由世界分配；本体 `envelope.fields.seq` 逐字）。
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct EventSeq(pub u64);

impl std::fmt::Display for EventSeq {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// 一件事。
#[derive(Debug, Clone, PartialEq)]
pub struct Event {
    /// 在账本中的位置。
    pub seq: EventSeq,
    /// 谁做的。
    pub who: Who,
    /// 哪一族（本体 `families` 的键：change／act／notice／job）。
    pub family: String,
    /// 做了什么（动作名或词表定义名）。
    pub what: String,
    /// 带的参数。
    pub params: Map<String, Value>,
}

impl Event {
    /// 取一个参数。
    #[must_use]
    pub fn param(&self, name: &str) -> Option<&Value> {
        self.params.get(name)
    }

    /// 它属于哪一族（本体四族之一吗）。
    #[must_use]
    pub fn family_is_declared(&self) -> bool {
        matches!(self.family.as_str(), "change" | "act" | "notice" | "job")
    }
}
