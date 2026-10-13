//! 面⑨：**关系面** —— 「这两类东西之间允许存在什么连接」＋「某一条边今天连着谁」。
//!
//! 本体 `links`（五要素之二）逐字：『哪两类对象之间允许存在什么连接』，且
//! 『两端的类型必须已在 `objects` 里声明，否则 `ext.world.Ontology.UndeclaredRelationEndpoint`』。
//! 本面把这句话落成三件：
//! ① **装载**（[`Links::load`]：读 `links` 一节，逐条校两端）；
//! ② **校验**（[`Links::connect`]：两端不在 `objects` 在册 ⇒ `Refuse(DanglingRef)`）；
//! ③ **查询**（[`Links::outgoing`]／[`Links::incoming`]／[`Links::neighbors`]：按 `from`／`to` 找）。
//!
//! ★ 参考 Palantir：`core/ontology.py` 的 `register_link_type` 与 `get_linked_types`
//!   （后者＝「这个类参与哪些已声明的边」，本面落在 [`Links::decls_of_kind`]）。
//!
//! ★ **一处如实登记**（照本体的自陈，不当结论）：
//! · 本体 `links._declared_gaps` 逐字：「世界**不执行**基数与方向性，也**没有**『从 `change`
//!   折出关系实例』这条推断规则」⇒ 本面的边是**直接登记在内存里**的，**不是**从账本折出来的；
//!   本面也**不执行**任何基数上限（声明侧见 `decl.rs`）。
//! · 出厂本体今天 **3** 条边（`device-bound-to-human`／`service-runs-on-device`／
//!   `application-speaks-on-port`）；★ 条数以本体**现取**为准，本注释不权威。
//! · 本面今天**只做内存实现**：边不留账、不落盘（留账与落盘分别由面⑥ `ledger` 与面④ `store` 担）。

mod decl;
mod edge;

#[cfg(test)]
mod tests;

pub use decl::EdgeDecl;
pub use edge::{Edge, Node};

use std::collections::{BTreeMap, BTreeSet};

use serde_json::Value;

use crate::core::registry::Registry;
use crate::core::types::{Admit, Reason, Refuse};

/// 「引用了一个不存在的东西」的那一个拒（★ 边名不在册、端点类型不在册，**都是它**）。
fn dangling(target: &str, what: impl Into<String>) -> Refuse {
    Refuse::new(
        Reason::DanglingRef {
            target: target.to_string(),
        },
        what,
    )
}

/// 关系面：已声明的边表（本体 `links`）＋ 已登记的边（内存）。
#[derive(Debug)]
pub struct Links {
    decls: BTreeMap<String, EdgeDecl>,
    edges: Vec<Edge>,
}

impl Links {
    /// 从本体 JSON 文本装载 `links` 一节。
    ///
    /// ★ 五节缺一 ⇒ `OntologyNotLoaded`（与面① `Registry`／面③ `ObjectSpec` **同口径**：
    ///   本体没装载，谁都别想动）。
    /// ★ 任一条边的任一端**不在 `objects` 在册** ⇒ `DanglingRef`，被拒的是 `links.<边>.<端>`。
    pub fn load(text: &str) -> Admit<Self> {
        let doc: Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        if aios_ontology::Ontology::load_str(text).is_err() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
        }
        Ok(Self {
            decls: decl::read(&doc)?,
            edges: Vec::new(),
        })
    }

    /// 一张**空边表**（本体已装载，一条边都还没登记）。
    #[must_use]
    pub fn empty() -> Self {
        Self {
            decls: BTreeMap::new(),
            edges: Vec::new(),
        }
    }

    /// 已声明的边名（升序）。
    #[must_use]
    pub fn edge_names(&self) -> Vec<&str> {
        self.decls.keys().map(String::as_str).collect()
    }

    /// 取一条已声明的边（不在册 ⇒ `None`）。
    #[must_use]
    pub fn decl(&self, link: &str) -> Option<&EdgeDecl> {
        self.decls.get(link)
    }

    /// ★ 这个**类**参与哪些已声明的边（`from` 或 `to` 是它）—— Palantir 的 `get_linked_types` 同位置。
    #[must_use]
    pub fn decls_of_kind(&self, kind: &str) -> Vec<&EdgeDecl> {
        self.decls
            .values()
            .filter(|d| d.from == kind || d.to == kind)
            .collect()
    }

    /// ★★ **登记一条边**：三问，逐问可验（★ 三问都在落表**之前**）。
    ///
    /// 1. **边名在册**（查本面装载的声明）⇒ 不在 ⇒ `DanglingRef`；
    /// 2. **两端各是 `objects` 里在册的类**（查面① `Registry`）⇒ 不在 ⇒ `DanglingRef`；
    /// 3. **两端各对得上这条声明的那一端**（`from` 对 `from`、`to` 对 `to`）
    ///    ⇒ 对不上 ⇒ `DanglingRef`（不许拿一条边装另一条边的两端）。
    /// 4. **同一条边（边名 ＋ 两端）不重复登记** ⇒ 已登记 ⇒ `DanglingRef`。
    ///    ★ 这不是基数上限（本体没声明基数）—— 是**同一句话不许算两条**。
    pub fn connect(&mut self, registry: &Registry, link: &str, from: Node, to: Node) -> Admit<()> {
        let Some(d) = self.decls.get(link) else {
            return Err(dangling(link, format!("边 {link} 未声明")));
        };
        if !registry.has_kind(&from.kind) {
            return Err(dangling(
                &from.kind,
                format!("{link}.from 端的类不在 objects 在册"),
            ));
        }
        if !registry.has_kind(&to.kind) {
            return Err(dangling(
                &to.kind,
                format!("{link}.to 端的类不在 objects 在册"),
            ));
        }
        if from.kind != d.from {
            return Err(dangling(
                &from.kind,
                format!("{link}.from 端的类该是 {}", d.from),
            ));
        }
        if to.kind != d.to {
            return Err(dangling(&to.kind, format!("{link}.to 端的类该是 {}", d.to)));
        }
        let edge = Edge {
            link: link.to_string(),
            from,
            to,
        };
        if self.edges.contains(&edge) {
            return Err(dangling(link, format!("边 {link} 的同一对端点已登记")));
        }
        self.edges.push(edge);
        Ok(())
    }

    /// 已登记的边数。
    #[must_use]
    pub fn count(&self) -> usize {
        self.edges.len()
    }

    /// 已登记的全部边（登记次序）。
    #[must_use]
    pub fn edges(&self) -> &[Edge] {
        &self.edges
    }

    /// ★ 这个实例**碰到的全部边**（它在前端或后端）—— 「按 `from`／`to` 找」。
    #[must_use]
    pub fn edges_of(&self, node: &Node) -> Vec<&Edge> {
        self.edges
            .iter()
            .filter(|e| e.from == *node || e.to == *node)
            .collect()
    }

    /// ★ 它作为 `from` 端连出去的（去重，登记次序）。
    #[must_use]
    pub fn outgoing(&self, node: &Node) -> Vec<&Node> {
        uniq(
            self.edges
                .iter()
                .filter(|e| e.from == *node)
                .map(|e| &e.to)
                .collect(),
        )
    }

    /// ★ 它作为 `to` 端被连进来的（去重，登记次序）。
    #[must_use]
    pub fn incoming(&self, node: &Node) -> Vec<&Node> {
        uniq(
            self.edges
                .iter()
                .filter(|e| e.to == *node)
                .map(|e| &e.from)
                .collect(),
        )
    }

    /// ★★ 「**它连了谁**」：两端都算（一条边就算它连着另一头），去重，登记次序。
    ///
    /// ★ 一条边都没碰到它 ⇒ **空表**（不是拒、不是错 —— 世界今天只是没这条边）。
    #[must_use]
    pub fn neighbors(&self, node: &Node) -> Vec<&Node> {
        uniq(self.edges.iter().filter_map(|e| e.other(node)).collect())
    }
}

/// 去重（按 `类型:名字`），**保序**。
fn uniq(items: Vec<&Node>) -> Vec<&Node> {
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut out = Vec::new();
    for n in items {
        if seen.insert(n.key()) {
            out.push(n);
        }
    }
    out
}
