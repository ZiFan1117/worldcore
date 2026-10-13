//! 只追加账里的**一行** —— 记的是「发生了」，不是「现在是什么样」。
//!
//! 本体里对应：`objects.record`（字段 `of_kind`／`at_seq`／`at_time`／`who`）
//! 与 `envelope.fields.seq` 逐字「integer  # 在账本中的位置，全局单增，由世界分配」。
//!
//! ★★ **本面只有这一种写**：往序列尾部推一行；**永不改、永不删**。
//! 现状是**折出来**的（见 `projection.rs`）——
//! 照 `read-model.spec.md`：「「现在是什么样」SHALL 由账本重算得出，
//! SHALL NOT 作为与账本并行的第二份原件存在」。
//!
//! ★ **将来接哪个 AIOS 件**（照作者令：内存实现可以，但要点名）：
//! 这条序列将来是 `crates/aios-evidence` 的**只追加链**（`ReceiptChain`：
//! 「append-only ordered list with link-hash verification」）—— 今天本面是内存 `Vec<Row>`。

use crate::core::types::{EventSeq, Registration, Who};

/// 这一行是**哪种写**。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Op {
    /// 新立一条（键此前不在）。
    Create,
    /// 更正一条（本体口径的 amendment；键本在）。★ 旧版**不动**，新一版是追加的。
    Update,
    /// 立碑（本体 `governance.tombstone`）—— **不真删**，只记「这一条作废了，为什么」。
    Tombstone,
}

/// 「没有前身」——`at_seq` 的哨兵。
///
/// ★ 照本体「两条时间轴」那格的口径：哨兵要有**独立取值**，不用 `null` 兼表「未定」与「无」。
pub const NO_PREDECESSOR: EventSeq = EventSeq(0);

/// 账本上的一行。★ 它记录**发生**，不记录**现状**。
#[derive(Debug, Clone, PartialEq)]
pub struct Row {
    /// 自己在只追加序列里的位置（全局单增，**永不复用**）—— `envelope.fields.seq`。
    pub seq: EventSeq,
    /// 谁写的 —— `envelope.fields.actor`（★ 本体自陈：这是**自填字符串**，它不证明身份）。
    pub who: Who,
    /// 这一笔**对着哪一条**：`Create` ⇒ `NO_PREDECESSOR`；
    /// `Update` ⇒ 被更正那条的 `seq`；`Tombstone` ⇒ 被立碑那条的 `seq`。
    pub at_seq: EventSeq,
    /// 哪种写。
    pub op: Op,
    /// 键（通常＝`类型:名字`）。
    pub key: String,
    /// 信纸（`Create`／`Update` 有；`Tombstone` 没有 —— 碑上不写新值）。
    pub reg: Option<Registration>,
    /// **为什么**（`Tombstone` 的原因；其余写为空串）。
    /// ★ 本体 `governance.tombstone` 的碑形第二样：「**为什么**（原因，不许写「笔误」了事）」。
    pub note: String,
}

impl Row {
    /// 这一行有没有信纸（折现状时要用的那一半）。
    #[must_use]
    pub fn payload(&self) -> Option<&Registration> {
        self.reg.as_ref()
    }
}
