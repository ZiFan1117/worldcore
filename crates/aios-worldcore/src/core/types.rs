//! **共同类型** —— 八个面共用的同一批说法（谁／拒／为什么／要登记的东西／一件事）。
//!
//! ★ 参考 Palantir foundry-ontology：那些类型散在 `core/` 与 `engine/` 各件里
//! （`ValidationResult` / `ActionResult` / `ObjectInstance` / `AuditEntry` / `User` / `SharedProperty`）。
//! ★ 本项目是 Rust：八面之间传的东西必须类型一致，否则编译不过 ⇒ 合成一处。
//! ★ 每个类型都能指回本体的一处（见各自的注）。

use serde_json::{Map, Value};

/// 谁 —— 做这件事的那个主体。
///
/// 本体里对应：`envelope.actor`（信封里的「谁」）。

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

/// 为什么 —— 拒绝的理由（机器认的码）。
///
/// 本体里对应：`aios-ontology` 的 `Reject`（逐条错误码，如 `ext.world.Ontology.ActionUnknown`）。

/// 拒绝的理由。每一条都能指回本体的一处规矩。
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Reason {
    /// 这个名字（类型名／动作名／能力名）本体里没登记。
    UnknownKind,
    /// 名字本身不合法（空、含空格斜杠引号）。
    BadName,
    /// 缺必填的格。
    MissingField { field: String },
    /// 格的值不合本体的规矩（类型／取值域）。
    BadValue { field: String, rule: String },
    /// 引用了一个本体里不存在的东西。
    DanglingRef { target: String },
    /// 超过本体声明的实例上限。
    OverInstanceLimit { limit: u64 },
    /// 这个人没有这个能力（治理那一面）。
    NotPermitted { capability: String },
    /// 本体没装载（谁都别想动）。
    OntologyNotLoaded,
}

impl Reason {
    /// 它的码（与本体错误码同一风格；判据与日志认它）。
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::UnknownKind => "worldcore.Refuse.UnknownKind",
            Self::BadName => "worldcore.Refuse.BadName",
            Self::MissingField { .. } => "worldcore.Refuse.MissingField",
            Self::BadValue { .. } => "worldcore.Refuse.BadValue",
            Self::DanglingRef { .. } => "worldcore.Refuse.DanglingRef",
            Self::OverInstanceLimit { .. } => "worldcore.Refuse.OverInstanceLimit",
            Self::NotPermitted { .. } => "worldcore.Refuse.NotPermitted",
            Self::OntologyNotLoaded => "worldcore.Refuse.OntologyNotLoaded",
        }
    }
}

/// 拒 —— 系统说「不行」时返回的那个东西。
///
/// 本体里对应：`Reject`（逐条带错误码）。这里多带一样：**被拒的那笔**（便于报给人和记账）。

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

/// 要登记的那样东西 —— 一次注册请求的内容。
///
/// 本体里对应：`objects.<类>.fields`（每一类有哪几个格）。
///
/// ★ 与 Palantir 的 `ObjectInstance` 同位置：**类型名 ＋ 各格的值**。

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

/// 一件事 —— 账本上记的一行。
///
/// 本体里对应：`envelope`（信封）＋ `families`（四族：change／act／notice／job）。
///
/// ★ 与 Palantir 的 `AuditEntry` 同位置：序号 ＋ 谁 ＋ 什么时候 ＋ 做了什么。

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
