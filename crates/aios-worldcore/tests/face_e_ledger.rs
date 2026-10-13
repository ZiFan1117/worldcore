//! 面⑥（账）：**只追加** ＋ **序号全局单增**。
//!
//! ★ 口径逐字来自本体 envelope：`seq` 「在账本中的位置，全局单增，由世界分配」。

use aios_worldcore::core::registry::Registry;
use aios_worldcore::core::types::{Admit, Event, EventSeq, Reason, Refuse, Registration, Who};
use aios_worldcore::engine::execute::{DryRun, Exec, Executor};
use aios_worldcore::engine::instances::Instances;
use aios_worldcore::engine::ledger::Ledger;
use aios_worldcore::engine::query::Query;
use aios_worldcore::engine::store::Store;
use aios_worldcore::engine::validate::{check_enum, check_refs, check_required, check_shape};
use aios_worldcore::governance::Governance;
use serde_json::{json, Map, Value};

const ONT: &str = include_str!("../../../crates/aios-ontology/data/ontology.json");

fn doc() -> Value {
    serde_json::from_str(ONT).expect("ontology.json 该能解析")
}

fn fields(pairs: &[(&str, Value)]) -> Map<String, Value> {
    let mut m = Map::new();
    for (k, v) in pairs {
        m.insert(k.to_string(), v.clone());
    }
    m
}

fn section_keys(section: &str) -> Vec<String> {
    let d = doc();
    let mut out = Vec::new();
    if let Some(map) = d[section].as_object() {
        for k in map.keys() {
            if !k.starts_with('_') {
                out.push(k.clone());
            }
        }
    }
    out
}

fn who() -> Who {
    Who::new("world://user/zhang")
}

/// ★★ 反例⑥：**只追加 ＋ 序号严格单增**。
/// 让它红的改法：让 append 复用序号、或者回头改老账 ⇒ 本用例红。
#[test]
fn ledger_is_append_only_with_strictly_increasing_seq() {
    let mut l = Ledger::new();
    let who = who();
    let a = l.append(&who, "act", "job.start", Map::new());
    let b = l.append(&who, "notice", "job.completed", Map::new());
    assert_eq!((a.0, b.0), (1, 2), "序号由账自己发，全局单增");
    let snapshot = l.export_csv();
    let c = l.append(&who, "change", "application.create", Map::new());
    let d = l.append(&who, "job", "job.finish", Map::new());
    assert_eq!((c.0, d.0), (3, 4));
    let after = l.export_csv();
    assert!(after.starts_with(&snapshot), "★ 反例：只追加 —— 老账必须原样");
    assert_eq!(l.all().len(), 4);
    let seqs: Vec<u64> = l.all().iter().map(|e| e.seq.0).collect();
    assert_eq!(seqs, [1, 2, 3, 4], "★ 反例：序号不许回退／重复");
}

/// 逐笔读得回来；族内查询按序号升序。
#[test]
fn ledger_reads_back_by_seq_and_by_family() {
    let mut l = Ledger::new();
    let who = who();
    let s1 = l.append(&who, "act", "job.start", fields(&[("subject", json!("application:htop"))]));
    l.append(&who, "notice", "job.completed", Map::new());
    let s3 = l.append(&who, "act", "ledger.compact", Map::new());
    let e = l.get(s1).expect("按序号该取得回");
    assert_eq!(e.what, "job.start");
    assert_eq!(e.who.name(), "world://user/zhang");
    assert_eq!(e.param("subject").and_then(Value::as_str), Some("application:htop"));
    let acts = l.query_family("act");
    assert_eq!(acts.len(), 2);
    assert_eq!(acts[0].seq, s1);
    assert_eq!(acts[1].seq, s3, "族内也按序号升序");
    assert!(l.query_family("frobnicator").is_empty(), "★ 反例：没有的族 ⇒ 空，不许全收");
    assert!(l.all().windows(2).all(|w| w[0].seq < w[1].seq), "★ 反例：全账序号严格单增");
}

/// 族名必须指得回本体 families 里的一条。
#[test]
fn ledger_records_the_declared_family() {
    let mut l = Ledger::new();
    let who = who();
    let seq = l.append(&who, "act", "job.start", Map::new());
    let e = l.get(seq).expect("该取得回");
    assert!(e.family_is_declared(), "act 是本体四族之一");
    let declared = section_keys("families");
    assert!(declared.iter().any(|f| f == &e.family), "族名该来自本体");
    let bogus = l.append(&who, "frobnicator", "x", Map::new());
    let b = l.get(bogus).expect("该取得回");
    assert!(!b.family_is_declared(), "★ 反例：四族之外必须判 false");
}

/// 导出 CSV：表头对、每笔一行。
#[test]
fn ledger_export_csv_has_header_and_one_row_per_event() {
    let mut l = Ledger::new();
    let who = who();
    l.append(&who, "act", "job.start", Map::new());
    l.append(&who, "notice", "job.completed", Map::new());
    let csv = l.export_csv();
    let lines: Vec<&str> = csv.lines().collect();
    assert_eq!(lines[0], "seq,who,family,what");
    assert_eq!(lines.len(), 3, "表头 ＋ 每笔一行");
    assert!(lines[1].starts_with("1,world://user/zhang,act,job.start"));
}

/// ★★ **会红反例（未登记即拒的缺口）**：账**不查族是否在册**。
/// 本体只声明四族（change／act／notice／job）；今天 append 收下任何族名。
/// 实现补上「未登记族即拒」后：本用例由红转绿，并删掉 ignore。
#[test]
#[ignore = "会红反例：账不查族在册 —— family=\"frobnicator\" 今天照收"]
fn undeclared_family_is_refused_by_the_ledger() {
    let mut l = Ledger::new();
    let who = who();
    let seq = l.append(&who, "frobnicator", "x", Map::new());
    let e = l.get(seq).expect("该取得回");
    assert!(e.family_is_declared(), "★ 今天这里是红的：frobnicator 不在四族里");
}
