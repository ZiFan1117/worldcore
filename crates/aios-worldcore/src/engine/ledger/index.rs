//! 二级索引：**族 → 序号**。
//!
//! ★ 学 「crates/aios-evidence」 的 record_type_index 那条组织法：**复合键 (维度, 位次)**，
//!   值不重要 —— 查的时候按前缀扫一段，扫出来天生就是**追加序**，不用回头排。
//! ★ 与它一致的一条纪律：索引**也只往里加**（正文只追加 ⇒ 索引行一旦写下就不再改）。
//! ★ 与它不同：它落在列族里、键是字节；我们今天是一棵 BTreeSet。

use std::collections::BTreeSet;

use crate::core::types::EventSeq;

/// 族到序号的二级索引（复合键 (族, 序号)）。
#[derive(Debug, Default)]
pub(super) struct FamilyIndex {
    /// 复合键表：按 (族, 序号) 排序 ⇒ 同族的挨在一起、且同族内按序号升序。
    pub(super) keys: BTreeSet<(String, EventSeq)>,
}

impl FamilyIndex {
    /// 记一行索引（★ 只加不改）。
    pub(super) fn insert(&mut self, seq: EventSeq, family: &str) {
        self.keys.insert((family.to_string(), seq));
    }

    /// 某一族的全部序号（升序）—— 一次前缀扫，扫到别族就停。
    pub(super) fn positions(&self, family: &str) -> Vec<EventSeq> {
        self.keys
            .range((family.to_string(), EventSeq(0))..)
            .take_while(|(f, _)| f.as_str() == family)
            .map(|(_, seq)| *seq)
            .collect()
    }
}
