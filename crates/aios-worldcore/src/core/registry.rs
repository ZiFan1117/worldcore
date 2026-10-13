//! 面①：**注册** —— 本体里「有哪几类东西」。
//!
//! 参考 Palantir：`core/ontology.py` 的 `register_object_type`／`register_link_type`／
//! `register_action_type`／`register_function`／`register_interface` ＋ `get_linked_types`。
//!
//! ★ 本实现不照抄上游 AIOS 的 crate：本体的**唯一权威**是 `aios-ontology` 装载的那份 JSON；
//! 本面只把它「有哪些类型」读出来，供其余各面查表（**其余各面不许自带清单**）。

use std::collections::BTreeSet;

use crate::core::types::{Reason, Refuse};

/// 已注册的类型表（从本体现取；不缓存到别处，免得漂）。
#[derive(Debug)]
pub struct Registry {
    kinds: BTreeSet<String>,
    actions: BTreeSet<String>,
    capabilities: BTreeSet<String>,
    families: BTreeSet<String>,
}

impl Registry {
    /// 从本体 JSON 文本建表。★ 五节缺一 ⇒ 由 `aios-ontology` 拒（`OntologyNotLoaded`）。
    pub fn load(text: &str) -> Result<Self, Refuse> {
        let doc: serde_json::Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        if aios_ontology::Ontology::load_str(text).is_err() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
        }
        Ok(Self {
            kinds: keys(&doc, "objects"),
            actions: keys(&doc, "actions"),
            capabilities: keys(&doc, "interfaces"),
            families: keys(&doc, "families"),
        })
    }

    /// 世界里有哪些类（升序）。
    #[must_use]
    pub fn kinds(&self) -> Vec<&str> {
        self.kinds.iter().map(String::as_str).collect()
    }

    /// 动作名（升序）。
    #[must_use]
    pub fn action_kinds(&self) -> Vec<&str> {
        self.actions.iter().map(String::as_str).collect()
    }

    /// 能力名（升序）。
    #[must_use]
    pub fn capability_kinds(&self) -> Vec<&str> {
        self.capabilities.iter().map(String::as_str).collect()
    }

    /// 记录四族（升序）。
    #[must_use]
    pub fn families(&self) -> Vec<&str> {
        self.families.iter().map(String::as_str).collect()
    }

    /// ★ 这个类型名在册吗（其余各面查表用这一条）。
    #[must_use]
    pub fn has_kind(&self, kind: &str) -> bool {
        self.kinds.contains(kind)
    }

    /// ★ 未在册 ⇒ 给一个「拒」（**不静默收下**）。
    #[must_use]
    pub fn refuse_unknown_kind(&self, kind: &str) -> Option<Refuse> {
        if self.has_kind(kind) {
            None
        } else {
            Some(Refuse::new(Reason::UnknownKind, kind))
        }
    }
}

fn keys(doc: &serde_json::Value, section: &str) -> BTreeSet<String> {
    doc.get(section)
        .and_then(serde_json::Value::as_object)
        .map(|m| m.keys().filter(|k| !k.starts_with('_')).cloned().collect())
        .unwrap_or_default()
}
/// ★ 装载本体的便捷入口（= `Registry::load`）。
///
/// ★ 为什么单独给一个自由函数：★ 原先门面 crate 里有 `load_ontology`，★ 门面取消后
/// 调用方（含 `tests/`）改一句就用得上；★ 名字与语义照 Palantir 的 `Ontology` 装载入口。
pub fn load_ontology(text: &str) -> Result<Registry, Refuse> {
    Registry::load(text)
}
impl Registry {
    /// ★ 别名：动作名是否在册（与本体装载器的 `has_action` 同名同义，调用方少记一个名字）。
    #[must_use]
    pub fn has_action(&self, action: &str) -> bool {
        self.actions.contains(action)
    }

    /// ★ 别名：动作名（升序）。
    #[must_use]
    pub fn action_names(&self) -> Vec<&str> {
        self.actions.iter().map(String::as_str).collect()
    }
}
