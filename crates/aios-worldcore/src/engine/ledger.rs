//! 面⑥：**账** —— 只追加地记下发生的事（不删、不改、不留回头路）。
//!
//! ★ 学的是 「crates/aios-evidence」 那一套**干活口径**（不是它的名字，也不是它的 crate）：
//!   ① **创世 ＋ 逐笔接链**：第一笔没有前驱；此后每一笔都要接住上一笔的封条；
//!   ② **只追加**：公开口只有「往后加一笔」；没有改一笔／删一笔／插一笔的口；
//!   ③ **防篡改**：封条压的是**整笔正文**（序号／谁／族／做了什么／参数全在内），
//!      老账被改动一处 ⇒ 重算对不上 ⇒ 「verify」指出**第一处**坏在哪个位次；
//!   ④ **数据怎么摆**：正文一份（只追加，位次 ＋ 1 即序号）＋ 与正文等长的**链节**（平行结构）
//!      ＋ 一张 **(族, 序号) 复合键**的二级索引（前缀一扫 ＝ 追加序，不用回头排）。
//!
//! ★ 与它**不一样**的地方（如实写，不含糊）：
//!   · 它压链用 BLAKE3-256 ＋ Ed25519 签名；我们的**封条用同一个 BLAKE3-256**
//!     （本 workspace 早就有的第三方依赖，**零新增**）⇒ 抗碰撞成立；
//!     它那层 **Ed25519 签名没接** —— 签名要一套密钥主体，我们的账今天只登记「谁」（Who）；
//!   · 它把链节／索引落进列族（RocksDB）；我们今天全在内存；
//!   · 它的查询带 limit 与隐私天花板；我们的 query_family 签名里没有这两样（接口不许改）。
//!
//! ★ 接口一个字没动（load／families／append／get／query_family／all／export_csv），
//!   append 仍拒不在册的族。本席只**加了**一个口：verify（③ 那条学过来总得有处落）。
//!
//! ★ 为什么族的权威清单由 load 读进来、而不是账自己偷偷读本体（★ 同登记面那条道理）：
//!   清单**从账自己身上过一遍**，调用点就没法「顺手换个族」绕过闸。

mod emit;
mod index;
mod seal;

#[cfg(test)]
mod tests;

use std::collections::BTreeSet;
use std::io::Write as _;

use serde::{Deserialize, Serialize};

use crate::core::types::{Admit, Event, EventSeq, Reason, Refuse, Who};
use index::FamilyIndex;
use seal::Seal;

/// 一本账：只追加。
#[derive(Debug)]
pub struct Ledger {
    /// 正文（只追加；第 i 笔的序号就是 i ＋ 1）。
    rows: Vec<Event>,
    /// 与正文**等长**的链节（正文被改动 ⇒ 链节对不上）。
    seals: Vec<Seal>,
    /// 链尾封条；空账是 None。
    head: Option<String>,
    /// 在册的族（本体 families 的键）。
    families: BTreeSet<String>,
    /// 二级索引：(族, 序号)。
    by_family: FamilyIndex,
}

/// ★ **落盘的一行**（T-242 批零）：**正文 ＋ 当笔封条**。
///
/// ★ 为什么把封条一起落：★ 只落正文、起来时重算 ⇒ 重算的链**永远与正文一致**
///   ⇒ `verify()` 恒绿 ⇒ ★★ **篡改不可察**（那等于把防篡改关掉）。
/// ★ 落的是**当时的**封条 ⇒ 起来时是**核对**它，不是重算它。
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Record {
    seq: u64,
    who: String,
    family: String,
    what: String,
    params: serde_json::Map<String, serde_json::Value>,
    /// 正文的指纹（落盘时算好的那一个）。
    seal_content: String,
    /// 上一节的封条值；创世是 None。
    seal_prev: Option<String>,
}

impl Record {
    fn of(row: &Event, node: &Seal) -> Self {
        Self {
            seq: row.seq.0,
            who: row.who.name().to_string(),
            family: row.family.clone(),
            what: row.what.clone(),
            params: row.params.clone(),
            seal_content: node.content.clone(),
            seal_prev: node.prev.clone(),
        }
    }

    fn into_event(self) -> (Event, Seal) {
        let row = Event {
            seq: EventSeq(self.seq),
            who: Who::new(self.who),
            family: self.family,
            what: self.what,
            params: self.params,
        };
        let node = Seal {
            content: self.seal_content,
            prev: self.seal_prev,
        };
        (row, node)
    }
}

impl Ledger {
    /// ★ **从本体文本装一本账：族的权威清单＝本体 families 的键（缺 ⇒ OntologyNotLoaded，
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
            seals: Vec::new(),
            head: None,
            families,
            by_family: FamilyIndex::default(),
        })
    }

    /// 在册的族（升序）。
    #[must_use]
    pub fn families(&self) -> Vec<&str> {
        self.families.iter().map(String::as_str).collect()
    }

    /// ★ 追加一笔：序号由账自己发（全局单增 —— 本体 envelope.fields.seq 逐字）；
    /// ★ **族不在册 ⇒ 拒**（不静默收下 —— 这是「未登记即拒」在账面的落法）。
    ///
    /// ★ 次序学它：**先封存、后入链** —— 封条与链尾都算好了才动正文，
    ///   被拒的那一笔在正文／链节／索引上**一处都不留**。
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
        let row = Event {
            seq,
            who: who.clone(),
            family,
            what: what.into(),
            params,
        };
        // ★ 这一笔的封条：接住链尾（首笔接创世），指纹压的是整笔。
        let node = Seal::next(self.head.as_deref(), seal::fingerprint(&row));
        let link = node.hash();
        // ★ 索引也只往里加：正文一落，索引跟着落。
        self.by_family.insert(seq, &row.family);
        self.rows.push(row);
        self.seals.push(node);
        self.head = Some(link);
        Ok(seq)
    }

    /// 按序号取一笔（★ 学它 chain_index：序号直接算位次，不再把账扫一遍）。
    #[must_use]
    pub fn get(&self, seq: EventSeq) -> Option<&Event> {
        self.row_at(seq)
    }

    /// 按族查（升序）。★ 走二级索引（(族, 序号) 前缀扫），不把全账过一遍。
    #[must_use]
    pub fn query_family(&self, family: &str) -> Vec<&Event> {
        self.by_family
            .positions(family)
            .into_iter()
            .filter_map(|seq| self.row_at(seq))
            .collect()
    }

    /// 全部（按序号升序）。
    #[must_use]
    pub fn all(&self) -> &[Event] {
        &self.rows
    }

    /// 导出 CSV（只导出、不推理）。
    #[must_use]
    pub fn export_csv(&self) -> String {
        emit::csv(&self.rows)
    }

    /// ★ **查篡改**（本席新加的一个口 —— ③ 那条学过来总得有处落）。
    ///
    /// 逐笔重算指纹 ＋ 逐节核对前驱；**第一处**对不上就返回，并把位次写进 field
    /// （seal[3] ⇒ 第 3 笔的正文被改过；seal[3].prev ⇒ 第 3 笔接错了前驱）。
    /// 空账**不叫健康**：没有链节可查，单独报（学它把空链与一条的健康链分开）。
    pub fn verify(&self) -> Admit<()> {
        seal::check_chain(&self.rows, &self.seals)
    }

    /// ★★ **从本体文本 ＋ 盘上一本账装回来**（T-242 批零新加的口 —— **既有接口一字未动**）。
    ///
    /// ★ 文件不在 ⇒ **空账**（首次运行，★ 不是错误）。
    /// ★ 盘上每一行都**核对**：① 正文的指纹对不对得上落盘时那一个；② 这一节接的前驱对不对。
    /// ★★ 对不上 ⇒ **整本拒**（★ 不静默跳过那一行 —— 跳过＝把篡改藏起来）。
    pub fn load_file(text: &str, path: &str) -> Admit<Self> {
        let mut me = Self::load(text)?;
        let body = match std::fs::read_to_string(path) {
            Ok(b) => b,
            Err(_) => return Ok(me),
        };
        let mut prev: Option<String> = None;
        for (i, line) in body.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let rec: Record = serde_json::from_str(line).map_err(|_| {
                Refuse::new(
                    Reason::BadValue {
                        field: format!("row[{i}]"),
                        rule: "<合法 JSON，一行一笔>".to_string(),
                    },
                    line.chars().take(40).collect::<String>(),
                )
            })?;
            let (row, node) = rec.into_event();
            // ① 正文动过没有（★ 核对落盘时的指纹，不是重算链）。
            let got = seal::fingerprint(&row);
            if got != node.content {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: format!("row[{i}].seal_content"),
                        rule: node.content.clone(),
                    },
                    got,
                ));
            }
            // ② 这一节接的前驱对不对。
            if node.prev != prev {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: format!("row[{i}].seal_prev"),
                        rule: prev.unwrap_or_else(|| seal::genesis().to_string()),
                    },
                    node.prev.unwrap_or_else(|| seal::genesis().to_string()),
                ));
            }
            prev = Some(node.hash());
            me.by_family.insert(row.seq, &row.family);
            me.rows.push(row);
            me.seals.push(node);
        }
        me.head = prev;
        Ok(me)
    }

    /// ★★ **追加一笔并落一行到盘上**（T-242 批零新加的口 —— **既有接口一字未动**）。
    ///
    /// ★ 次序学 `append` 那条：**先算好、先落盘、落成了才入内存** ——
    ///   写盘失败 ⇒ **内存也不收这一笔**（★ 一处都不留，与「被拒的那一笔不留痕」同族）。
    pub fn append_persisting(
        &mut self,
        path: &str,
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
        let row = Event {
            seq,
            who: who.clone(),
            family,
            what: what.into(),
            params,
        };
        let node = Seal::next(self.head.as_deref(), seal::fingerprint(&row));
        let line = serde_json::to_string(&Record::of(&row, &node)).map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: path.to_string(),
                },
                "<这一笔写不成一行 JSON>",
            )
        })?;
        let mut fh = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|_| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: path.to_string(),
                    },
                    "<打不开账文件>",
                )
            })?;
        writeln!(fh, "{line}").map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: path.to_string(),
                },
                "<这一行没写下去>",
            )
        })?;
        // ★ 落盘成了 ⇒ 才入内存。
        self.by_family.insert(row.seq, &row.family);
        self.rows.push(row);
        self.seals.push(node.clone());
        self.head = Some(node.hash());
        Ok(seq)
    }

    /// 位次取一笔：序号从 1 起 ⇒ 位次 ＝ 序号 − 1；越界或序号对不上都不给。
    fn row_at(&self, seq: EventSeq) -> Option<&Event> {
        let i = usize::try_from(seq.0).ok()?.checked_sub(1)?;
        self.rows.get(i).filter(|e| e.seq == seq)
    }
}
