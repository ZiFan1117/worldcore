//! 面①：**注册** —— 本体里「有哪几类东西」。
//!
//! 参考 Palantir：`core/ontology.py` 的 `register_object_type`／`register_link_type`／
//! `register_action_type`／`register_function`／`register_interface` ＋ `get_linked_types`。
//!
//! ★ 本实现不照抄上游 AIOS 的 crate：本体的**唯一权威**是 `aios-ontology` 装载的那份 JSON；
//! 本面只把它「有哪些类型」读出来，供其余各面查表（**其余各面不许自带清单**）。

use std::collections::{BTreeMap, BTreeSet};

use crate::core::types::{Reason, Refuse};

/// 已注册的类型表（从本体现取；不缓存到别处，免得漂）。
#[derive(Debug)]
pub struct Registry {
    kinds: BTreeSet<String>,
    actions: BTreeSet<String>,
    capabilities: BTreeSet<String>,
    families: BTreeSet<String>,
    functions: BTreeSet<String>,
    action_function: BTreeMap<String, String>,
    /// ★ 建表时收到的那份**本体原文**（只留一份，供其余各面按同一条入口再读，不许各自带清单）。
    source: String,
}

impl Registry {
    /// 从本体 JSON 文本建表。★ 五节缺一 ⇒ 由 `aios-ontology` 拒（`OntologyNotLoaded`）。
    ///
    /// ★ 原文**留着**（`source()`）—— 其余各面要按同一条入口再读时取它，免得本体出现第二份。
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
            functions: functions_of(&doc),
            action_function: action_functions_of(&doc),
            source: text.to_string(),
        })
    }

    /// ★★★ **世界里有哪些【类】** —— ★★ **只有本体给，注册插不进来**。
    ///
    /// ★ 作者裁（逐字整理）：「★ **不是这些东西就各是各的，你不要混在一起**」⇒
    ///   ★ 层与层分开：★ **类**只由本体给（封闭）；★ **动作**才是「本体那 9 条 ＋ 注册那 N 条」，
    ///   ★ 而且**两份各是各的**、查的时候先本体再注册（★ 不合成）。
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

    /// ★ 建表时收到的那份**本体原文**（逐字；★ 不解析、不改写）。
    ///
    /// ★ 给谁用：其余各面要按**同一条入口**（`load(text)`）再读一遍本体时，取它 ——
    ///   这样「本体只有一份」这条不靠调用方各自保管文本。
    #[must_use]
    pub fn source(&self) -> &str {
        &self.source
    }

    /// ★ 本体 `functions.entries` 的全部入口名（升序）—— 函数面（面⑤）的第一处查表口。
    ///
    /// ★ 这里**只给名字**：函数的声明（`inputs`／`output_type`）由面⑤ `Functions` 读 ——
    ///   两处读的是**同一份本体**，本件不另立清单。
    #[must_use]
    pub fn functions(&self) -> Vec<&str> {
        self.functions.iter().map(String::as_str).collect()
    }

    /// ★ 这个动作认的是哪条函数（本体 `actions.<动作>.function` 逐字，例：
    /// `"function": "fn.presence.report"`）；动作不在册或没写这一项 ⇒ `None`。
    ///
    /// ★ 为什么要有它：**「动作 → 函数」的映射是本体给的**，不是 `fn.<动作名>` 这条约定 ——
    ///   约定会随本体改而悄悄失效，读本体那一项不会。
    #[must_use]
    pub fn function_of_action(&self, action: &str) -> Option<&str> {
        self.action_function.get(action).map(String::as_str)
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

/// 读本体 `functions.entries` 的入口名（★ `_` 键是说明／登记的缺口，不是函数）。
fn functions_of(doc: &serde_json::Value) -> BTreeSet<String> {
    doc.get("functions")
        .and_then(|f| f.get("entries"))
        .and_then(serde_json::Value::as_object)
        .map(|m| m.keys().filter(|k| !k.starts_with('_')).cloned().collect())
        .unwrap_or_default()
}

/// 读本体 `actions.<动作>.function`（★ 没写这一项的动作不进表 —— 不替它猜）。
fn action_functions_of(doc: &serde_json::Value) -> BTreeMap<String, String> {
    let mut out = BTreeMap::new();
    let Some(actions) = doc.get("actions").and_then(serde_json::Value::as_object) else {
        return out;
    };
    for (action, body) in actions {
        if action.starts_with('_') {
            continue;
        }
        if let Some(function) = body.get("function").and_then(serde_json::Value::as_str) {
            out.insert(action.clone(), function.to_string());
        }
    }
    out
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
#[cfg(test)]
mod tests {
    use super::Registry;

    /// 真本体（★ 权威；本仓测试与判据都以它为唯一来源）。
    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    /// 正控：**原文留着**，且两个读口都逐字对着同一份本体（★ 不另立清单）。
    #[test]
    fn read_ports_come_from_the_same_source() {
        let reg = Registry::load(ONT).expect("本体该装得上");
        assert_eq!(reg.source(), ONT, "本体原文要一字不动地留着");
        assert_eq!(reg.functions().len(), 9);
        assert!(reg.functions().contains(&"fn.notice.mute"));
        assert_eq!(
            reg.function_of_action("notice.mute"),
            Some("fn.notice.mute")
        );
        assert_eq!(
            reg.function_of_action("presence.report"),
            Some("fn.presence.report")
        );
        assert_eq!(reg.function_of_action("frobnicator"), None);
        // ★ 在册动作各写着它的实现面，且那个函数号也在册（★ 本体给映射，不猜 fn.<动作名>）。
        for action in reg.action_kinds() {
            let f = reg.function_of_action(action).expect("动作该写着实现面");
            assert!(reg.functions().contains(&f), "{action} → {f} 不在函数表里");
        }
    }
}
