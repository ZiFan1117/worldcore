//! 面⑥：**账** —— 只追加地记下发生的事（不删、不改）。
//!
//! 参考 Palantir：`engine/audit_log.py` 的 `append`／`get`／`query`／`export_csv`。
//! 本体口径见 `envelope`（信封）与 `families`（四族 change／act／notice／job）。

use aios_worldcore_shared::{Event, EventSeq, Who};

/// 一本账：只追加。
#[derive(Debug, Default)]
pub struct Ledger {
    rows: Vec<Event>,
}

impl Ledger {
    /// 空账。
    #[must_use]
    pub fn new() -> Self {
        Self { rows: Vec::new() }
    }

    /// ★ 追加一笔：序号由账自己发（全局单增 —— 本体 `envelope.fields.seq` 逐字）。
    pub fn append(
        &mut self,
        who: &Who,
        family: impl Into<String>,
        what: impl Into<String>,
        params: serde_json::Map<String, serde_json::Value>,
    ) -> EventSeq {
        let seq = EventSeq(self.rows.len() as u64 + 1);
        self.rows.push(Event {
            seq,
            who: who.clone(),
            family: family.into(),
            what: what.into(),
            params,
        });
        seq
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
