//! 为什么 —— 拒绝的理由（机器认的码）。
//!
//! 本体里对应：`aios-ontology` 的 `Reject`（逐条错误码，如 `ext.world.Ontology.ActionUnknown`）。

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
