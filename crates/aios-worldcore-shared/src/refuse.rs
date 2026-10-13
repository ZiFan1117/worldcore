//! 拒 —— 系统说「不行」时返回的那个东西。
//!
//! 本体里对应：`Reject`（逐条带错误码）。这里多带一样：**被拒的那笔**（便于报给人和记账）。

use crate::reason::Reason;

/// 一次拒绝：为什么不许 ＋ 被拒的是哪件事。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Refuse {
    /// 为什么。
    pub reason: Reason,
    /// 被拒的那笔（类型名／动作名／字段路径；自由文本，供人看）。
    pub what: String,
}

impl Refuse {
    /// 造一个拒。
    #[must_use]
    pub fn new(reason: Reason, what: impl Into<String>) -> Self {
        Self {
            reason,
            what: what.into(),
        }
    }

    /// 它的码（转发 `Reason::code`）。
    #[must_use]
    pub fn code(&self) -> &'static str {
        self.reason.code()
    }
}

impl std::fmt::Display for Refuse {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}：{}", self.code(), self.what)
    }
}

impl std::error::Error for Refuse {}

/// 本内核各处统一的结果别名（省得每面各写一套）。
pub type Admit<T> = Result<T, Refuse>;
