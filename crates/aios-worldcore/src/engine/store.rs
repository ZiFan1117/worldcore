//! 面④：**实例存储** —— 存下来、取得出；★ **写是只追加，读是折出现状**。
//!
//! 参考 Palantir：engine/object_store.py 的 create／get／update／delete／search／count；
//! ★ 干活口径另学上游那套对象模型的写侧（只学怎么干活；名字／类型全是我们的）：
//! ① 它只有**一份只追加的原件**＋由它派生的读侧目录（我们：log ＋ Projection）；
//! ② 它的**每一道拒都在动目录之前**（先核在册／父版本，才写状态）；
//! ③ 它**不真删**（把作废的版本退役／隔离，而不是抹掉）⇒ 我们立碑。
//!
//! ## 三条口径（逐条可验）
//!
//! 1. **唯一原件是一个只追加序列**（内部的 Vec<Row>）：每一笔写都往尾部推一行，
//!    带 seq（envelope.fields.seq 逐字「在账本中的位置，全局单增，由世界分配」）／
//!    who（envelope.fields.actor）／at_seq（这一笔**对着哪一条**）；
//! 2. **get／count／search_by_kind 读的是折出来的现状**（后写覆盖前写）——
//!    现状是**派生物**，整份丢掉也能由序列原样重折（Store::replay／Store::project）；
//! 3. **delete 不真删**：追加一笔 Tombstone（本体 governance.tombstone 逐字
//!    「错误靠修正与墓碑，绝不靠沉默」）。
//!
//! ★ **本面只管「存」**；在不在册由面②（注册）与面③（校验）把关（本面不重复判）。
//!
//! ★ **今天没做**（如实）：本体 record.at_time（UNIX 秒）**没有落点** —— 本面无时钟，
//! 折现状只按 seq 排序（本体 envelope.fields.at 自陈「顺序由 seq 决定，at 只作辅助」）。
//!
//! ★ **本件只放写侧**（只追加序列的推入 ＋ 四条拒绝规矩）；**读侧在 read.rs**，
//!   折现在 projection.rs。

mod projection;
mod read;
mod row;

#[cfg(test)]
mod tests;

pub use projection::{fold, Projection};
pub use row::{Op, Row, NO_PREDECESSOR};

use std::cell::OnceCell;
use std::fmt;

use crate::core::types::{Admit, EventSeq, Reason, Refuse, Registration, Who};

/// 没写「谁」时用的系统主体（照 Who::is_system 的 _system: 口径）。
fn system_who() -> Who {
    Who::new("_system:store")
}

/// 「键不在」的那一个拒。
fn missing(key: &str) -> Refuse {
    Refuse::new(
        Reason::DanglingRef {
            target: key.to_string(),
        },
        "键不存在",
    )
}

/// 一笔要追加的写 —— 本面**唯一**那种写的形状（学它「一笔写是一份单子」那一手）。
///
/// ★ 为什么先攒成一份单子再推：★ 写只有**一个入口**（commit），
/// 调用点就没法绕开「序号由本面发／推完让现状缓存失效」这两样。
struct Append {
    /// 谁写的（envelope.fields.actor；★ 本体自陈：这是**自填字符串**，它不证明身份）。
    who: Who,
    /// 这一笔**对着哪一条**（Create ⇒ NO_PREDECESSOR）。
    at_seq: EventSeq,
    /// 哪种写。
    op: Op,
    /// 键（通常＝类型:名字）。
    key: String,
    /// 信纸（Create／Update 有；Tombstone 没有 —— 碑上不写新值）。
    reg: Option<Registration>,
    /// **为什么**（Tombstone 的原因；其余写为空串）。
    note: String,
}

/// 一份存储：一个**只追加序列**（唯一原件）＋ 它的现状（派生缓存）。
///
/// ★ 缓存**不是第二份原件**：它任何时候都可丢掉，下一次读会重折
/// （照 read-model.spec.md「个体是可丢弃的缓存」）。
pub struct Store {
    log: Vec<Row>,
    view: OnceCell<Projection>,
}

impl fmt::Debug for Store {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Store")
            .field("rows", &self.log.len())
            .finish_non_exhaustive()
    }
}

impl Default for Store {
    fn default() -> Self {
        Self::new()
    }
}

impl Store {
    /// 空存储。
    #[must_use]
    pub fn new() -> Self {
        Self {
            log: Vec::new(),
            view: OnceCell::new(),
        }
    }

    /// 往只追加序列尾部推一笔 —— 本面**唯一**的写。★ 序号永不复用。
    fn commit(&mut self, append: Append) -> EventSeq {
        let seq = EventSeq(self.log.len() as u64 + 1);
        self.log.push(Row {
            seq,
            who: append.who,
            at_seq: append.at_seq,
            op: append.op,
            key: append.key,
            reg: append.reg,
            note: append.note,
        });
        self.view = OnceCell::new(); // ★ 缓存失效：下一次读重折
        seq
    }

    /// 现行那一笔落在哪个 seq（键不在 ⇒ 拒）—— 更正／立碑都要指得出**哪一条**。
    ///
    /// ★ 这就是「对象 → 指针 → 版本」那层间接落在本面的样子：先问现状「现行是哪一条」，
    ///   再把它的 seq 写进新那一笔的 at_seq。
    fn predecessor_of(&self, key: &str) -> Admit<EventSeq> {
        self.projection()
            .last_write_seq(key)
            .ok_or_else(|| missing(key))
    }

    /// 存一条（键通常＝类型:名字）。键已存在 ⇒ 拒。
    ///
    /// ★ 本条是**兼容旧调用方**的薄包装：它把「谁」写成系统主体
    /// （_system:store）；**要如实记「谁」请用 create_as**。
    pub fn create(&mut self, key: impl Into<String>, reg: Registration) -> Admit<()> {
        self.create_as(&system_who(), key, reg).map(|_| ())
    }

    /// ★ 如实记「谁」的写入口：新立一条 ⇒ **追加一行**（seq 由本面发）。
    pub fn create_as(
        &mut self,
        who: &Who,
        key: impl Into<String>,
        reg: Registration,
    ) -> Admit<EventSeq> {
        let key = key.into();
        if self.projection().get(&key).is_some() {
            return Err(Refuse::new(Reason::DanglingRef { target: key }, "键已存在"));
        }
        Ok(self.commit(Append {
            who: who.clone(),
            at_seq: NO_PREDECESSOR,
            op: Op::Create,
            key,
            reg: Some(reg),
            note: String::new(),
        }))
    }

    /// 更正一条（不存在 ⇒ 拒）。★ 旧版**不动**：追加一行，折出来才是新的。
    ///
    /// ★ 兼容旧调用方（「谁」＝系统主体）；要如实记「谁」请用 update_as。
    pub fn update(&mut self, key: &str, reg: Registration) -> Admit<()> {
        self.update_as(&system_who(), key, reg).map(|_| ())
    }

    /// ★ 如实记「谁」的更正：at_seq ＝ **被更正那条的 seq**（碑／更正都要指得出哪一条）。
    pub fn update_as(&mut self, who: &Who, key: &str, reg: Registration) -> Admit<EventSeq> {
        let at_seq = self.predecessor_of(key)?;
        Ok(self.commit(Append {
            who: who.clone(),
            at_seq,
            op: Op::Update,
            key: key.to_string(),
            reg: Some(reg),
            note: String::new(),
        }))
    }

    /// 删一条 —— ★ **不真删**：记一笔 Tombstone（本体 governance.tombstone）。
    ///
    /// ★ 兼容旧调用方（「谁」＝系统主体，原因＝「未给原因」）；要如实记
    /// **谁／为什么** 请用 delete_as。
    pub fn delete(&mut self, key: &str) -> Admit<()> {
        self.delete_as(&system_who(), key, "未给原因（旧调用方口径）")
            .map(|_| ())
    }

    /// ★ 立碑：键不存在 ⇒ 拒；**原因为空 ⇒ 拒**（本体碑形第二样：不许写「笔误」了事）。
    ///
    /// 碑行带三样：**哪一条**（at_seq）／**谁**（who）／**为什么**（note）。
    /// ★ 本体碑形还有「什么时候」一样 —— 本面无时钟，**今天没有落点**（如实）。
    pub fn delete_as(&mut self, who: &Who, key: &str, reason: &str) -> Admit<EventSeq> {
        if reason.trim().is_empty() {
            return Err(Refuse::new(
                Reason::MissingField {
                    field: "reason".to_string(),
                },
                key.to_string(),
            ));
        }
        let at_seq = self.predecessor_of(key)?;
        Ok(self.commit(Append {
            who: who.clone(),
            at_seq,
            op: Op::Tombstone,
            key: key.to_string(),
            reg: None,
            note: reason.to_string(),
        }))
    }
}
