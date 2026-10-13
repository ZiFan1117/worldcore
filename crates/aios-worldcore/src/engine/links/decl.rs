//! 关系面的**声明**：从本体 JSON 读 `links` 一节，并**逐条校两端**。
//!
//! 本体 `links._comment` 逐字：「两端的类型必须已在 `objects` 里声明，
//! 否则 `ext.world.Ontology.UndeclaredRelationEndpoint`」—— 本件就是这一条。
//!
//! ★ 参考 Palantir：`core/ontology.py` 的 `register_link_type`（声明一条命名边）。
//! ★ **不在本件**：基数、方向性。本体 `links._declared_gaps` 逐字「世界**不执行**基数与方向性」
//!   ⇒ 本件**不读、不判、不默认** `card`／`bidirectional`（★ 「声明了没执行」比「没声明」更坏，
//!   故这里**不替本体发明**这两样语义）。

use std::collections::{BTreeMap, BTreeSet};

use serde_json::Value;

use crate::core::types::{Admit, Reason, Refuse};

/// 一条**已声明**的边：名字 ＋ 两端类型。
///
/// ★ 两端在装载时**已经**是 `objects` 里在册的类名（见 `read`）⇒ 本类型自身不再判在不在册。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EdgeDecl {
    /// 边名（本体 `links` 下的键）。
    pub name: String,
    /// 源端**类型名**（已声明）。
    pub from: String,
    /// 目标端**类型名**（已声明）。
    pub to: String,
}

/// 读 `links` 一节：边名 ⇒ 两端。★ 任一端不在 `objects` 在册 ⇒ `DanglingRef`（**整份拒**）。
///
/// `_` 前缀的键是说明／登记缺口，不是边（与 `objects`／`interfaces` 同口径）。
pub fn read(doc: &Value) -> Admit<BTreeMap<String, EdgeDecl>> {
    let Some(objects) = doc.get("objects").and_then(Value::as_object) else {
        return Err(Refuse::new(Reason::OntologyNotLoaded, "<objects 缺>"));
    };
    let known: BTreeSet<&str> = objects
        .keys()
        .filter(|k| !k.starts_with('_'))
        .map(String::as_str)
        .collect();
    let Some(links) = doc.get("links").and_then(Value::as_object) else {
        return Err(Refuse::new(Reason::OntologyNotLoaded, "<links 缺>"));
    };
    let mut out = BTreeMap::new();
    for (name, body) in links {
        if name.starts_with('_') {
            continue;
        }
        let from = endpoint(body, "from", name)?;
        let to = endpoint(body, "to", name)?;
        for (side, end) in [("from", &from), ("to", &to)] {
            if !known.contains(end.as_str()) {
                return Err(Refuse::new(
                    Reason::DanglingRef {
                        target: end.clone(),
                    },
                    format!("links.{name}.{side}"),
                ));
            }
        }
        out.insert(
            name.clone(),
            EdgeDecl {
                name: name.clone(),
                from,
                to,
            },
        );
    }
    Ok(out)
}

/// 取一端（`from`／`to`）：缺、或不是非空字符串 ⇒ 拒（★ **不可判读的声明不许当「没那一项」**）。
fn endpoint(body: &Value, side: &str, name: &str) -> Admit<String> {
    let raw = body.get(side).and_then(Value::as_str).unwrap_or_default();
    if raw.trim().is_empty() {
        return Err(Refuse::new(
            Reason::MissingField {
                field: side.to_string(),
            },
            format!("links.{name}"),
        ));
    }
    Ok(raw.to_string())
}
