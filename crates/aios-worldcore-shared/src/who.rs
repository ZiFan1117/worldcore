//! 谁 —— 做这件事的那个主体。
//!
//! 本体里对应：`envelope.actor`（信封里的「谁」）。

use serde_json::Value;

/// 主体：一个在册的名字（`world://<ns>/<name>` 形状）。
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Who(String);

impl Who {
    /// 造一个主体（不做校验；校验在 `validate` 那一面）。
    #[must_use]
    pub fn new(name: impl Into<String>) -> Self {
        Self(name.into())
    }

    /// 它的名字。
    #[must_use]
    pub fn name(&self) -> &str {
        &self.0
    }

    /// 是不是系统自己（本体里 `_system:` 前缀的用法）。
    #[must_use]
    pub fn is_system(&self) -> bool {
        self.0.starts_with("_system:")
    }
}

impl std::fmt::Display for Who {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl From<&str> for Who {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

impl Who {
    /// 从 JSON 取（缺或不是字符串 ⇒ `None`）。
    #[must_use]
    pub fn from_json(v: &Value) -> Option<Self> {
        v.as_str().map(|s| Self(s.to_string()))
    }
}
