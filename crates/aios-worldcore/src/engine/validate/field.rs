//! 本体的**类型声明串**怎么读、怎么判（`bool`／`string`／…／`ref(<类>)`／`enum(a,b)`）。
//!
//! ★ 口径在 `objects._comment` 逐字：只有那几种写法参与校验；
//!   **不是那几种写法的自由度说明文字一律放行**。
//!
//! ★ 这一处将来接 **AIOS 的**哪一件：本体的类型系统在 AIOS 侧对应
//!   `crates/aios-capability-runtime/src/action_fabric.rs` 那套「动作参数由能力表定形状」的**参数类型**口径
//!   （现取：AIOS 自己没有 JSON 形状的类型枚举 —— 本件只照 worldcore 本体的声明串走，**不替它发明**）。

use serde_json::Value;

/// 一格的类型声明（本体 `fields.<格>` 的那几种写法）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FieldType {
    /// `bool`
    Bool,
    /// `string`
    Str,
    /// `integer`（★ 只收整数：`5.0` 不算）
    Integer,
    /// `number`
    Number,
    /// `array` ／ `array(<元素>)`
    Array,
    /// `object`
    Object,
    /// `ref(<类名>)` —— 值是一条指向实例的**字符串**地址。
    Ref(String),
    /// `enum(a,b,…)` —— 值只能在这几个里。
    Enum(Vec<String>),
    /// 不是上面那几种写法（自由的说明文字）⇒ **放行**（本体 `objects._comment` 逐字）。
    Freeform(String),
}

impl FieldType {
    /// 解析本体里那一格的类型声明串。
    ///
    /// ★ 本体里有的格带尾注（`"integer  # UNIX 秒"`）⇒ 只取 `#` 之前那一段。
    #[must_use]
    pub fn parse(declaration: &str) -> Self {
        let raw = declaration.split('#').next().unwrap_or("").trim();
        let low = raw.to_ascii_lowercase();
        match low.as_str() {
            "bool" => Self::Bool,
            "string" => Self::Str,
            "integer" => Self::Integer,
            "number" => Self::Number,
            "object" => Self::Object,
            _ => parse_compound(raw, &low),
        }
    }

    /// 这个值合不合本格声明的类型（取值域算在类型里：`enum`）。
    #[must_use]
    pub fn accepts(&self, value: &Value) -> bool {
        match self {
            Self::Bool => value.is_boolean(),
            Self::Str => value.is_string(),
            Self::Integer => value.is_i64() || value.is_u64(),
            Self::Number => value.is_number(),
            Self::Array => value.is_array(),
            Self::Object => value.is_object(),
            Self::Ref(_) => value.is_string(),
            Self::Enum(options) => in_domain(value, options),
            Self::Freeform(_) => true,
        }
    }

    /// 它的声明串（照本体逐字；放进 `Reason::BadValue.rule`，人一眼看出该是什么）。
    #[must_use]
    pub fn declaration(&self) -> String {
        match self {
            Self::Bool => "bool".to_string(),
            Self::Str => "string".to_string(),
            Self::Integer => "integer".to_string(),
            Self::Number => "number".to_string(),
            Self::Array => "array".to_string(),
            Self::Object => "object".to_string(),
            Self::Ref(kind) => format!("ref({kind})"),
            Self::Enum(options) => format!("enum({})", options.join(",")),
            Self::Freeform(raw) => raw.clone(),
        }
    }
}

/// 值落在取值域里吗。
fn in_domain(value: &Value, options: &[String]) -> bool {
    value
        .as_str()
        .is_some_and(|s| options.iter().any(|o| o.as_str() == s))
}

/// 认 `array(…)`／`ref(…)`／`enum(…)` 这三种带括号的写法；都不是 ⇒ 自由说明文字。
fn parse_compound(raw: &str, low: &str) -> FieldType {
    if low.starts_with("array(") {
        return FieldType::Array;
    }
    if let Some(kind) = call_arg(raw, low, "ref(") {
        return FieldType::Ref(kind);
    }
    if let Some(inner) = call_arg(raw, low, "enum(") {
        let options = inner
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();
        return FieldType::Enum(options);
    }
    FieldType::Freeform(raw.to_string())
}

/// 形如 `ref(x)`／`enum(a,b)` ⇒ 取括号里那一段（★ 前缀大小写不敏感，取原文）。
fn call_arg(raw: &str, low: &str, prefix: &str) -> Option<String> {
    if !low.starts_with(prefix) || !raw.ends_with(')') {
        return None;
    }
    Some(raw[prefix.len()..raw.len() - 1].trim().to_string())
}
