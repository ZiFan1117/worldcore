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
    /// ★ 数据分级**不许降级**（本体 `governance.markings.levels`「只升不降」；来源1-①.3 逐字给的码）。
    MarkingDowngrade {
        /// 现行那一版的分级（本体 levels 的键）。
        from: &'static str,
        /// 想写进去的那一版（比 from 低）。
        to: &'static str,
    },
    /// ★ **CAS 没对上**：写口拿的 expected 与现行指针不符（H02／H04 砖一）。
    ConflictDetected {
        /// 期望的那一版（调用方给的）。
        expected: u64,
        /// 现读到的指针（真正的现行）。
        current: u64,
    },
    /// ★ 这一条高过了主体的天花板（H08 读侧那条真闸）。
    AboveCeiling {
        /// 这一条自己的分级。
        marking: &'static str,
        /// 主体的可见天花板。
        ceiling: &'static str,
    },
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
            Self::MarkingDowngrade { .. } => "worldcore.Refuse.MarkingDowngrade",
            Self::AboveCeiling { .. } => "worldcore.Refuse.AboveCeiling",
            Self::ConflictDetected { .. } => "worldcore.Refuse.ConflictDetected",
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

/// ★ **生命周期**（H07）—— 闭集三档。
///
/// ★ 为什么是我们折出来的一条：本体里 **9 类中 4 类**已经有 `state=enum(…,retired)`、其余没有
/// （现取），而「作废」与「退役」今天混在墓碑一处 ⇒ ★ 折出一条**统一的生命周期**，
/// **不动本体**（照作者裁决：本体只增不改，本批没增）。
///
/// ★ 与类自己的 `state`（running／stopped…）**不是一回事**：那是**运行态**，这是**生命周期**。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Lifecycle {
    /// 活着（读得到、写得进）。
    Active,
    /// 已退役（＝今天的「立碑」）：★ 审计可读、写不许。
    Retired,
    /// 已清除：★ 我们**只追加** ⇒ 正文一行不动，只记一笔声明 ＋ 留审计 stub。
    Purged,
}

impl Lifecycle {
    /// 它的码（与本体 `retired` 那个词同形；判据与日志认它）。
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Active => "ACTIVE",
            Self::Retired => "RETIRED",
            Self::Purged => "PURGED",
        }
    }
}

/// 数据分级 —— **闭集三级**（本体 `governance.markings.levels` 逐字
/// PUBLIC／INTERNAL／CONFIDENTIAL；照 Palantir 开源复刻件逐字
/// 「Data classification (PUBLIC, INTERNAL, CONFIDENTIAL)」）。
///
/// ★ 序是**死的**（Public < Internal < Confidential）：只有这个序才判得出「升／降级」。
/// ★ 不许「认不得就当最松」：不在闭集 ⇒ 拒（见 `Registration::marking`）。
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Marking {
    /// 可对外（本体逐字：本仓今天一件都没有）。
    Public,
    /// 仓内可读（本体逐字：今天所有类都落这一档）。
    Internal,
    /// 受控（本体逐字：本仓今天一件都没有）。
    Confidential,
}

impl Marking {
    /// 它的码（与本体 `levels` 的键逐字同形）。
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Public => "PUBLIC",
            Self::Internal => "INTERNAL",
            Self::Confidential => "CONFIDENTIAL",
        }
    }

    /// 从文本认一级（大小写不敏感；**不在闭集 ⇒ None**）。
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text.to_ascii_uppercase().as_str() {
            "PUBLIC" => Some(Self::Public),
            "INTERNAL" => Some(Self::Internal),
            "CONFIDENTIAL" => Some(Self::Confidential),
            _ => None,
        }
    }
}

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

    /// ★ 这一条的分级 —— 缺格 ⇒ **本体自陈的默认** `INTERNAL`
    /// （`markings.levels.INTERNAL` 逐字「今天所有类都落这一档」）；
    /// ★ 写了但**不在闭集** ⇒ 拒（不许「认不得就当最松」）。
    pub fn marking(&self) -> Admit<Marking> {
        match self.get_str("marking") {
            Some(text) => Marking::parse(text).ok_or_else(|| {
                Refuse::new(
                    Reason::BadValue {
                        field: "marking".to_string(),
                        rule: "PUBLIC|INTERNAL|CONFIDENTIAL".to_string(),
                    },
                    text.to_string(),
                )
            }),
            None => Ok(Marking::Internal),
        }
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
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct EventSeq(pub u64);

// ★ `Default` ＝ 0：与 `NO_PREDECESSOR` 同一取值 —— 意思都是「**没有**」
//   （空账折出来的水位线就是 0）。★ 序号从 1 起（本体 envelope.fields.seq 逐字「全局单增，由世界分配」），
//   所以 0 永远不是一笔真账 ⇒ 当「没有」用不会撞上真值。

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
