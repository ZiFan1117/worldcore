//! 面⑨：**恢复面** —— 只用 L1／L2 就能把世界看清楚。
//!
//! ★ 学的是它那条**理念**（不是它的代码）：`01_object_model.md:390-400` 逐字
//! 「The recovery path depends on **L1 and L2 only**. No L3+ services, no LLM, no Web UI, no KDE session.」
//! ⇒ 我们落成：**一个纯读数的恢复出口** ＋ **一条机器判据**（依赖闭包里不许有 L3+ 件）。
//!
//! ★ 恢复模式闭集照它 `00_overview.md:30` 那五个词：Normal／SafeReadonly／Repair／Quarantine／Reindex。
//!   ★ **今天只落 Normal 与 SafeReadonly 的读数**，另三档**登记为未落**（不许读成「五档都有了」）。
//!
//! ★ 恢复七件里，我们今天**做得出**的（照来源1-⑨.2 的对照）：
//!   ① Enumerate objects ＝ `Store::keys`／`count`；② Verify chunk hashes（＝查账完整性）＝ `Ledger::verify`；
//!   ③ Rebuild semantic indexes ＝ `Store::project`；★ 另四件要 H02／H03／H06。
//!
//! ★ 本面**不许**出现：LLM／渲染器／桌面／网络。★ 判据 C11 盯着这条（写死在 `verify/` 里）。

use crate::core::types::Lifecycle;
use crate::engine::ledger::Ledger;
use crate::engine::store::{Op, Store};

/// 恢复模式 —— **闭集五档**（照它 `00_overview.md:30` 逐字那五个词）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecoveryMode {
    /// 正常（可读可写）。
    Normal,
    /// ★ 只读（恢复面今天**只用这一档**：纯读数不改世界）。
    SafeReadonly,
    /// 修复（★ 未落）。
    Repair,
    /// 隔离（★ 未落 —— 要 H06）。
    Quarantine,
    /// 重建索引（★ 未落）。
    Reindex,
}

impl RecoveryMode {
    /// 它的码（与本体／规格同一风格；日志与判据认它）。
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Normal => "normal",
            Self::SafeReadonly => "safe_readonly",
            Self::Repair => "repair",
            Self::Quarantine => "quarantine",
            Self::Reindex => "reindex",
        }
    }
}

/// 一次体检的**读数**（★ 纯读数：不带 LLM、不带 UI、不依赖任何 L3+ 件）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryReport {
    /// 用哪个模式读的。
    pub mode: RecoveryMode,
    /// 现状里**活着**几条（＝ Enumerate objects 那一件）。
    pub objects: usize,
    /// 已退役／已清除几条（含碑与 stub —— 我们只追加，历史里都读得到）。
    pub retired: usize,
    /// 账上「**指针搬回**」几笔（H02 落地之后读得出来）。
    pub pointers_rolled_back: usize,
    /// 账的链节自检过不过（＝ Verify chunk hashes 那一件）。
    pub ledger_ok: bool,
    /// ★ **今天读不出来**的那几项（如实列，**不许编 0 充数**）。
    pub not_yet: Vec<&'static str>,
}

/// ★ 体检：把恢复面今天读得出来的东西读一遍（**纯函数式的读**，不改世界）。
#[must_use]
pub fn inspect(store: &Store, ledger: &Ledger, mode: RecoveryMode) -> RecoveryReport {
    // 走过的键（含已立碑／已清除的 —— 只追加序列里全在）。
    let mut keys: Vec<&str> = store.rows().iter().map(|r| r.key.as_str()).collect();
    keys.sort_unstable();
    keys.dedup();
    let retired = keys
        .iter()
        .filter(|key| {
            matches!(
                store.lifecycle_of(key),
                Some(Lifecycle::Retired | Lifecycle::Purged)
            )
        })
        .count();
    RecoveryReport {
        mode,
        objects: store.count(),
        retired,
        pointers_rolled_back: store.rows().iter().filter(|r| r.op == Op::Rollback).count(),
        ledger_ok: ledger.verify().is_ok(),
        not_yet: vec!["quarantined（要 H06）", "txns_aborted（要 H03）"],
    }
}

#[cfg(test)]
mod tests {
    use crate::core::types::{Registration, Who};
    use crate::engine::ledger::Ledger;
    use crate::engine::store::Store;

    use super::{inspect, RecoveryMode};

    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    fn reg(name: &str) -> Registration {
        let mut fields = serde_json::Map::new();
        fields.insert("name".to_string(), serde_json::json!(name));
        Registration::new("application", fields)
    }

    /// ★★ 会红反例 1（**读不出来的要如实列，不许编 0 充数**）：
    /// `quarantined`／`txns_aborted` 今天读不出来 ⇒ 必须在 `not_yet` 里点名。
    /// 让它红的改法：把 not_yet 清空（或给这两项填 0）⇒ 本用例红。
    #[test]
    fn the_report_names_what_it_cannot_read_yet() {
        let store = Store::new();
        let ledger = Ledger::load(ONT).expect("族的权威清单从本体来");
        let report = inspect(&store, &ledger, RecoveryMode::SafeReadonly);
        assert_eq!(report.objects, 0);
        assert!(
            !report.ledger_ok,
            "★ **空账不叫健康**（既有口径：没有链节可查 ⇒ verify 报坏，不报好）"
        );
        assert_eq!(report.not_yet.len(), 2, "★ 两项读不出来就要点两项名");
        assert!(report.not_yet.iter().any(|s| s.contains("H06")));
        assert!(report.not_yet.iter().any(|s| s.contains("H03")));
    }

    /// ★★ 会红反例 2（**恢复面读得出现在有什么**）：活着／退役／指针搬回各算得出来。
    #[test]
    fn the_report_counts_the_living_the_retired_and_the_rolled_back() {
        let mut store = Store::new();
        let who = Who::new("world://user/zhang");
        store
            .create_as(&who, "application:a", reg("a"))
            .expect("该成");
        store
            .create_as(&who, "application:b", reg("b"))
            .expect("该成");
        store
            .promote_as(
                &who,
                "application:b",
                crate::core::types::EventSeq(2),
                reg("b2"),
            )
            .expect("该成");
        store
            .rollback_as(
                &who,
                "application:b",
                crate::core::types::EventSeq(2),
                "退回",
            )
            .expect("该成");
        store
            .delete_as(&who, "application:a", "不用了")
            .expect("该成");
        let mut ledger = Ledger::load(ONT).expect("族的权威清单从本体来");
        // ★ 正控：账上真有一笔 ⇒ 链节自检该过（空账那一条在上一用例里）。
        ledger
            .append(&who, "notice", "recovery.probe", serde_json::Map::new())
            .expect("记一笔该成");

        let report = inspect(&store, &ledger, RecoveryMode::Normal);
        assert!(report.ledger_ok, "有链节可查 ⇒ 该过");
        assert_eq!(report.objects, 1, "b 还活着（回滚后仍在册）");
        assert_eq!(report.retired, 1, "a 已退役");
        assert_eq!(report.pointers_rolled_back, 1);
        assert_eq!(report.mode.code(), "normal");
    }
}
