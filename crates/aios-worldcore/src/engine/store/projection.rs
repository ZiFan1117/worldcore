//! 折出现状 —— 把只追加序列**折**成「现在是什么样」，同批折出**按类索引**与**现状指纹**。
//!
//! ★ 干活口径学自上游那套对象模型的读法（只学它怎么干活；名字／类型全是我们的）：
//! ① 它把状态摊在**几个各自键控的目录**里，而不是一张大表 ⇒ 我们折现状时**同批**折出三件：
//!    current（键 ⇒ 现行信纸）／last_write（键 ⇒ 现行那一行的 seq）／
//!    kind_index（类 ⇒ 该类的键，升序）；
//! ② 它用一份**状态指纹**（把目录折成排序 entry 串再哈希）核对「两份状态是否逐项一致」
//!    ⇒ 我们折出 fingerprint（crate 内可见，**只给机核用**，不是对外接口）；
//! ③ 「对象 → 指针 → 版本」那层间接 ⇒ 我们「键 ⇒ 现行 seq ⇒ 序列里的那一行」。
//!
//! ★ 折的口径（**后写覆盖前写**，按 seq 升序逐行应用）：
//! - Create／Update ⇒ 记下那一版（同键后写盖掉先写；★ **类换了要摘旧桶**）；
//! - Tombstone ⇒ 从**现状**里摘掉（**历史不动**，账上两行都在）。
//!
//! ★ 现状是**派生物**：整份丢掉也能由序列原样重折（fold 是纯函数）。
//! 照 read-model.spec.md「个体是可丢弃的缓存」：「「现在是什么样」SHALL 由账本重算得出，
//! SHALL NOT 作为与账本并行的第二份原件存在」—— 本模块就是那个「重算」。
//!
//! ★ **将来接哪个 AIOS 件**（照作者令：内存实现可以，但要点名）：重折的读侧将来接
//! 上游的对象存储那一层；本模块今天只吃内存 &[Row]。

use std::collections::{BTreeMap, BTreeSet};

use crate::core::types::{EventSeq, Registration};

use super::row::{Op, Row};

/// 折出来的现状 ＋ 每条键**最后一笔信纸**落在哪个 seq ＋ **按类索引**。
///
/// 后两者给立碑／更正／按类查用：碑上要写清「**哪一条**被更正了」（本体碑形第一样）；
/// 按类查走索引，不每次全扫现状表。
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Projection {
    current: BTreeMap<String, Registration>,
    last_write: BTreeMap<String, EventSeq>,
    kind_index: BTreeMap<String, BTreeSet<String>>,
}

impl Projection {
    /// 某键的现状（已立碑或从未写过 ⇒ None）。
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

    /// 某一类还在现状里的键（升序）—— ★ 走**索引**。
    #[must_use]
    pub fn by_kind(&self, kind: &str) -> Vec<&str> {
        match self.kind_index.get(kind) {
            Some(keys) => keys.iter().map(String::as_str).collect(),
            None => Vec::new(),
        }
    }

    /// 某键**最后一笔信纸**落在哪个 seq（Tombstone 不改它 ⇒ 碑立了也指得出被立碑那条）。
    #[must_use]
    pub fn last_write_seq(&self, key: &str) -> Option<EventSeq> {
        self.last_write.get(key).copied()
    }

    /// ★ 现状指纹：把现状折成**排序 entry 串**再哈希（学它「状态指纹」那一手）。
    ///
    /// ★ 只在 crate 内可见：这是**机核用**的读法（由同一份序列重折 ⇒ 指纹必须逐字相同；
    /// 现状一变 ⇒ 指纹就变），不是对外接口。
    #[must_use]
    #[allow(dead_code)] // ★ Lead 代改：机核读法，测试与将来对账用；今天无调用者不是错
    pub(super) fn fingerprint(&self) -> String {
        let mut entries: Vec<String> = self
            .current
            .iter()
            .map(|(key, reg)| {
                let seq = self.last_write.get(key).map_or(0, |s| s.0);
                format!("{key}|{}|{seq}", reg.kind)
            })
            .collect();
        entries.sort_unstable();
        format!("{:016x}", fnv1a64(&entries.join("\n")))
    }
}

/// ★ 纯函数：从**只追加序列**折出现状。
///
/// log 必须是只追加序列的本序（按 seq 升序，即 Vec 的推入顺序）。
#[must_use]
pub fn fold(log: &[Row]) -> Projection {
    let mut folded = Projection::default();
    for row in log {
        match row.op {
            // 立碑：从**现状**里摘掉；账上那一行照旧。
            Op::Tombstone => folded.retire(&row.key),
            // 立／更正：后写覆盖前写。
            Op::Create | Op::Update => {
                if let Some(reg) = &row.reg {
                    folded.publish(row.key.clone(), reg.clone(), row.seq);
                }
            }
        }
    }
    folded
}

impl Projection {
    /// 把一个键的**现行版**换成一版新的（后写覆盖前写）＋ 同批改索引。
    fn publish(&mut self, key: String, reg: Registration, seq: EventSeq) {
        let previous_kind = self.current.get(&key).map(|old| old.kind.clone());
        if let Some(old_kind) = previous_kind {
            // ★ 更正**换了类** ⇒ 旧桶里必须摘掉（否则「旧类也查得到它」⇒ 与现状不符）。
            if old_kind != reg.kind {
                self.unbucket(&old_kind, &key);
            }
        }
        self.bucket(&reg.kind, &key);
        self.current.insert(key.clone(), reg);
        self.last_write.insert(key, seq);
    }

    /// 立碑：从**现状**里摘掉（历史那一行不动）＋ 同批改索引。
    fn retire(&mut self, key: &str) {
        if let Some(reg) = self.current.remove(key) {
            let kind = reg.kind;
            self.unbucket(&kind, key);
        }
    }

    /// 记进类的桶（桶内键升序）。
    fn bucket(&mut self, kind: &str, key: &str) {
        self.kind_index
            .entry(kind.to_string())
            .or_default()
            .insert(key.to_string());
    }

    /// 从类的桶里摘掉；桶空了就把桶删掉（免得留空桶）。
    fn unbucket(&mut self, kind: &str, key: &str) {
        let emptied = match self.kind_index.get_mut(kind) {
            Some(keys) => {
                keys.remove(key);
                keys.is_empty()
            }
            None => false,
        };
        if emptied {
            self.kind_index.remove(kind);
        }
    }
}

/// FNV-1a 64 位 —— 一个不引外部依赖、跨次运行确定的小哈希（只为机核，不为安全）。
#[allow(dead_code)] // ★ Lead 代改：机核读法（见 fingerprint），今天无调用者
fn fnv1a64(text: &str) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in text.as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}
