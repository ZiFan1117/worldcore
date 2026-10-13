//! 读侧 —— ★ 一律**折出现状**，不另存一份「写入时的表」。
//!
//! 口径照 read-model.spec.md「个体是可丢弃的缓存」：
//! 「「现在是什么样」SHALL 由账本重算得出，SHALL NOT 作为与账本并行的第二份原件存在。」
//!
//! ★ 读侧分两段（学上游那套「原件目录／派生目录」分家）：
//! - **原件读**：replay（由序列重建）／rows（只追加序列，含已立碑的）／history_of（一个键的全部历史行）；
//! - **折读**：project（现折、不用缓存）／projection（读时折一次，写后失效）／
//!   get／keys／search_by_kind／count／last_write_seq。
//!
//! ★ 键 ⇒ 现行 seq ⇒ 序列里的那一行：这是「对象 → 指针 → 版本」那层间接在我们这儿的落法
//!   （现行 seq 由 projection().last_write_seq 给，供更正／立碑指认「哪一条」）。
//!
//! ★ **将来接哪个 AIOS 件**（照作者令：内存实现可以，但要点名）：读侧的落盘载体将来接
//! 上游的对象存储那一层；今天本面是内存折。

use std::cell::OnceCell;

use crate::core::types::{EventSeq, Registration};

use super::{fold, Projection, Row, Store};

impl Store {
    // ---- 原件读（只追加序列那一份） --------------------------------

    /// ★ 用**一份只追加序列**重建一份存储（现状由序列**现折**）。
    ///
    /// 这就是「个体是可丢弃的缓存」的落法：把现状整份丢掉，
    /// 由账本重算 SHALL 得到逐项一致的结果。
    #[must_use]
    pub fn replay(log: &[Row]) -> Self {
        Self {
            log: log.to_vec(),
            view: OnceCell::new(),
        }
    }

    /// 只追加序列（按 seq 升序，**含已立碑的**）—— 本面的唯一原件。
    #[must_use]
    pub fn rows(&self) -> &[Row] {
        &self.log
    }

    /// 某一键的全部历史行（**含已立碑的**；升序）—— 学它「一个对象列全部版本」那一手。
    #[must_use]
    pub fn history_of(&self, key: &str) -> Vec<&Row> {
        self.log.iter().filter(|r| r.key == key).collect()
    }

    // ---- 折读（现状是派生物） --------------------------------------

    /// ★ 现从只追加序列折一遍现状（**不用缓存**；给核对与验证用）。
    #[must_use]
    pub fn project(&self) -> Projection {
        fold(&self.log)
    }

    /// 现状：第一次读时从序列折出，之后复用；★ 任何一笔写都让它**失效重折**。
    pub(crate) fn projection(&self) -> &Projection {
        self.view.get_or_init(|| fold(&self.log))
    }

    /// 取一条（**现状**：后写覆盖前写；已立碑 ⇒ None）。
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&Registration> {
        self.projection().get(key)
    }

    /// 现状里还活着的键（升序）。
    #[must_use]
    pub fn keys(&self) -> Vec<&str> {
        self.projection().keys()
    }

    /// 按类型名找（**现状**；升序键）—— ★ 走折出来的按类索引。
    #[must_use]
    pub fn search_by_kind(&self, kind: &str) -> Vec<&str> {
        self.projection().by_kind(kind)
    }

    /// 现状里还有几条（★ 已立碑的**不算**）。
    #[must_use]
    pub fn count(&self) -> usize {
        self.projection().count()
    }

    /// 某键**最后一笔信纸**落在哪个 seq（立碑／更正时「哪一条」就是它）。
    #[must_use]
    pub fn last_write_seq(&self, key: &str) -> Option<EventSeq> {
        self.projection().last_write_seq(key)
    }
}
