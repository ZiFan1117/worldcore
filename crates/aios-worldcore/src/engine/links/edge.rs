//! 关系面的**两端指认**与**一条边**。
//!
//! ★ 与面②（实例登记）同口径：本内核里一个实例的指认＝**类型名 ＋ 名字**
//!   （行以 `name` 为键，见 `engine/instances.rs`）。
//! ★ 本件**不判**任何规矩（在不在册、对不对得上声明）—— 那是 `engine/links.rs` 的 `connect`。

use std::fmt;

/// 一个**实例**的指认：它是哪一类 ＋ 它叫什么。
///
/// ★ 本类型是**内存里的指认**，不是本体声明；本体的实例表示在 `objects.<类>.fields`。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    /// 类型名（必须在 `objects` 里在册）。
    pub kind: String,
    /// 名字（本内核里是唯一指认格）。
    pub name: String,
}

impl Node {
    /// 造一个指认（不做校验；校验在 `Links::connect`）。
    #[must_use]
    pub fn new(kind: impl Into<String>, name: impl Into<String>) -> Self {
        Self {
            kind: kind.into(),
            name: name.into(),
        }
    }

    /// `类型:名字` —— 与面② 实例表的键**同口径**（一处口径，两处不各写一份）。
    #[must_use]
    pub fn key(&self) -> String {
        format!("{}:{}", self.kind, self.name)
    }
}

impl fmt::Display for Node {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.key())
    }
}

/// 世界里的一条边：哪条**命名边** ＋ 两端指认。
///
/// ★ 本体 `links._declared_gaps` 逐字：世界**没有**「从 `change` 折出关系实例」这条推断规则
///   ⇒ 本类型的实例**不是**从账本折出来的，是**直接登记在内存里**的（照实登记，不当结论）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    /// 命名边（本体 `links` 下的键）。
    pub link: String,
    /// 源端（对得上该声明的 `from`）。
    pub from: Node,
    /// 目标端（对得上该声明的 `to`）。
    pub to: Node,
}

impl Edge {
    /// 这条边的**另一端**：问「它连了谁」时用（不在两端 ⇒ `None`）。
    #[must_use]
    pub fn other(&self, node: &Node) -> Option<&Node> {
        if self.from == *node {
            Some(&self.to)
        } else if self.to == *node {
            Some(&self.from)
        } else {
            None
        }
    }
}
