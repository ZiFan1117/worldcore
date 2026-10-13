//! 折出现状 —— 把只追加序列**折**成「现在是什么样」。
//!
//! ★ 折的口径（**后写覆盖前写**，按 `seq` 升序逐行应用）：
//!
//! - `Create`／`Update` ⇒ 记下那一版（同一键后写的盖掉先写的）；
//! - `Tombstone` ⇒ 把那一条从**现状**里摘掉（**历史不动**，账上两行都在）。
//!
//! ★ 现状是**派生物**：整份丢掉也能由序列原样重折（`fold` 是纯函数）。
//! 照 `read-model.spec.md`「个体是可丢弃的缓存」：删除其持久形态后，
//! 由账本重算 SHALL 得到逐项一致的结果 —— 本模块就是那个「重算」。
//!
//! ★ **将来接哪个 AIOS 件**（照作者令）：重折的读侧将来接 `crates/aios-fs` 的
//! 对象视图（`InMemoryAiosFs` 是它今天的替身）；本模块今天只吃内存 `&[Row]`。

use std::collections::BTreeMap;

use crate::core::types::{EventSeq, Registration};

use super::row::{Op, Row};

/// 折出来的现状 ＋ 每条键**最后一笔信纸**落在哪个 `seq`。
///
/// 后者给立碑／更正用：碑上要写清「**哪一条**被更正了」（本体碑形第一样）。
#[derive(Debug, Clone, PartialEq)]
pub struct Projection {
    current: BTreeMap<String, Registration>,
    last_write: BTreeMap<String, EventSeq>,
}

impl Projection {
    /// 某键的现状（已立碑或从未写过 ⇒ `None`）。
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&Registration> {
        self.current.get(key)
    }

    /// 现状里还在的键（升序）。
    #[must_use]
    pub fn keys(&self) -> Vec<&str> {
        self.current.keys().map(String::as_str).collect()
    }

    /// 现状里还有几条（★ 已立碑的**不算**）。
    #[must_use]
    pub fn count(&self) -> usize {
        self.current.len()
    }

    /// 某一类还在现状里的键（升序）。
    #[must_use]
    pub fn by_kind(&self, kind: &str) -> Vec<&str> {
        self.current
            .iter()
            .filter(|(_, r)| r.kind == kind)
            .map(|(k, _)| k.as_str())
            .collect()
    }

    /// 某键**最后一笔信纸**落在哪个 `seq`（`Tombstone` 不改它 ⇒ 碑立了也指得出被立碑那条）。
    #[must_use]
    pub fn last_write_seq(&self, key: &str) -> Option<EventSeq> {
        self.last_write.get(key).copied()
    }
}

/// ★ 纯函数：从**只追加序列**折出现状。
///
/// `log` 必须是只追加序列的本序（按 `seq` 升序，即 `Vec` 的推入顺序）。
#[must_use]
pub fn fold(log: &[Row]) -> Projection {
    let mut current: BTreeMap<String, Registration> = BTreeMap::new();
    let mut last_write: BTreeMap<String, EventSeq> = BTreeMap::new();
    for row in log {
        match row.op {
            // 立碑：从**现状**里摘掉；账上那一行照旧。
            Op::Tombstone => {
                current.remove(&row.key);
            }
            // 立／更正：后写覆盖前写。
            Op::Create | Op::Update => {
                if let Some(reg) = &row.reg {
                    current.insert(row.key.clone(), reg.clone());
                    last_write.insert(row.key.clone(), row.seq);
                }
            }
        }
    }
    Projection {
        current,
        last_write,
    }
}
