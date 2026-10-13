//! 面⑥：**账** —— 只追加地记下发生的事（不删、不改）。
//!
//! 参考 Palantir：`engine/audit_log.py` 的 `append`／`get`／`query`／`export_csv`。
//! 本体口径见 `envelope`（信封）与 `families`（四族 change／act／notice／job）。
//!
//! ★ 2026-10-13 接上一处：**族名必须在册**（本体 `families` 的键）⇒ 不在册 ⇒ `BadValue{family}`。
//! ★ 这一处将来接 **AIOS 的**哪一件：「只追加、不删不改」那条链应接 `crates/aios-evidence`
//!   （EvidenceLog／receipt）；今天只在 worldcore 内存里攒一个 `Vec<Event>`。
//!
//! ★ 为什么族的权威清单由 `load` 读进来、而不是账自己偷偷读本体（★ 同登记面那条道理）：
//!   清单**从账自己身上过一遍**，调用点就没法「顺手换个族」绕过闸。

use std::collections::BTreeSet;

use crate::core::types::{Admit, Event, EventSeq, Reason, Refuse, Who};

/// 一本账：只追加。
#[derive(Debug)]
pub struct Ledger {
    rows: Vec<Event>,
    families: BTreeSet<String>,
}

impl Ledger {
    /// ★ 从本体文本装一本账：族的权威清单＝本体 `families` 的键（缺 ⇒ `OntologyNotLoaded`，
    /// **不静默给一本空表** —— 空表＝什么都记不了，那是个哑闸，不是安全闸）。
    pub fn load(text: &str) -> Admit<Self> {
        let doc: serde_json::Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        if aios_ontology::Ontology::load_str(text).is_err() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
        }
        let families: BTreeSet<String> = doc
            .get("families")
            .and_then(serde_json::Value::as_object)
            .map(|m| m.keys().filter(|k| !k.starts_with('_')).cloned().collect())
            .unwrap_or_default();
        if families.is_empty() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<families 缺>"));
        }
        Ok(Self {
            rows: Vec::new(),
            families,
        })
    }

    /// 在册的族（升序）。
    #[must_use]
    pub fn families(&self) -> Vec<&str> {
        self.families.iter().map(String::as_str).collect()
    }

    /// ★ 追加一笔：序号由账自己发（全局单增 —— 本体 `envelope.fields.seq` 逐字）；
    /// ★ **族不在册 ⇒ 拒**（不静默收下 —— 这是「未登记即拒」在账面的落法）。
    pub fn append(
        &mut self,
        who: &Who,
        family: impl Into<String>,
        what: impl Into<String>,
        params: serde_json::Map<String, serde_json::Value>,
    ) -> Admit<EventSeq> {
        let family = family.into();
        if !self.families.contains(&family) {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "family".to_string(),
                    rule: self.families().join("|"),
                },
                family,
            ));
        }
        let seq = EventSeq(self.rows.len() as u64 + 1);
        self.rows.push(Event {
            seq,
            who: who.clone(),
            family,
            what: what.into(),
            params,
        });
        Ok(seq)
    }

    /// 按序号取一笔。
    #[must_use]
    pub fn get(&self, seq: EventSeq) -> Option<&Event> {
        self.rows.iter().find(|e| e.seq == seq)
    }

    /// 按族查（升序）。
    #[must_use]
    pub fn query_family(&self, family: &str) -> Vec<&Event> {
        self.rows.iter().filter(|e| e.family == family).collect()
    }

    /// 全部（按序号升序）。
    #[must_use]
    pub fn all(&self) -> &[Event] {
        &self.rows
    }

    /// 导出 CSV（只导出、不推理）。
    #[must_use]
    pub fn export_csv(&self) -> String {
        let mut s = String::from("seq,who,family,what");
        for e in &self.rows {
            s.push_str(&format!("\n{},{},{},{}", e.seq, e.who, e.family, e.what));
        }
        s
    }
}
