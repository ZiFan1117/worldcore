//! 要登记的那样东西 —— 一次注册请求的内容。
//!
//! 本体里对应：`objects.<类>.fields`（每一类有哪几个格）。
//!
//! ★ 与 Palantir 的 `ObjectInstance` 同位置：**类型名 ＋ 各格的值**。

use serde_json::{Map, Value};

/// 一次注册：它是什么类型 ＋ 它填了哪些格。
#[derive(Debug, Clone, PartialEq)]
pub struct Registration {
    /// 类型名（必须在册）。
    pub kind: String,
    /// 各格的值。
    pub fields: Map<String, Value>,
}

impl Registration {
    /// 造一个注册。
    #[must_use]
    pub fn new(kind: impl Into<String>, fields: Map<String, Value>) -> Self {
        Self {
            kind: kind.into(),
            fields,
        }
    }

    /// 取一格。
    #[must_use]
    pub fn get(&self, field: &str) -> Option<&Value> {
        self.fields.get(field)
    }

    /// 取一格的字符串（不是字符串 ⇒ `None`）。
    #[must_use]
    pub fn get_str(&self, field: &str) -> Option<&str> {
        self.fields.get(field).and_then(Value::as_str)
    }

    /// 它填了哪些格（升序）。
    #[must_use]
    pub fn field_names(&self) -> Vec<&str> {
        let mut v: Vec<&str> = self.fields.keys().map(String::as_str).collect();
        v.sort_unstable();
        v
    }
}
