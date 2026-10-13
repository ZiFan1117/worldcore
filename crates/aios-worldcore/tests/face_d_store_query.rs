//! 面④（存储）＋面⑤（查询）：**存得下、取得到、查得准、排得对、取得前 N**。
//!
//! ★ 将来接哪个 AIOS 件（今天**还没接**）：落盘那一层应接 `crates/aios-fs`；
//!   「改了什么要留证据」应接 `crates/aios-evidence`。本文件只判今天的内存实现。

use aios_worldcore::core::types::{Reason, Registration};
use aios_worldcore::engine::query::Query;
use aios_worldcore::engine::store::Store;
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

fn app(name: &str, state: &str) -> Registration {
    Registration::new(
        "application",
        fields(&[("name", json!(name)), ("state", json!(state))]),
    )
}

fn service(name: &str, state: &str) -> Registration {
    Registration::new(
        "service",
        fields(&[("name", json!(name)), ("state", json!(state))]),
    )
}

fn store_with_three() -> Store {
    let mut s = Store::new();
    let a = s.create("application:alpha", app("alpha", "running"));
    let b = s.create("application:beta", app("beta", "installed"));
    let c = s.create("service:sshd", service("sshd", "running"));
    a.expect("该存得下");
    b.expect("该存得下");
    c.expect("该存得下");
    s
}

/// 按 name 升序把命中拼成一行（比 Vec 更好读，也免了借用纠缠）。
fn names_of(q: &Query<'_>) -> String {
    let hits = q.all();
    let mut names: Vec<String> = Vec::new();
    for (_, r) in &hits {
        let n = r.get_str("name").unwrap_or("");
        names.push(n.to_string());
    }
    names.join(",")
}

/// ★ 反例：同一把键**不许重复存**（重复 ⇒ 拒，不是覆盖）。
#[test]
fn store_refuses_duplicate_key() {
    let mut s = Store::new();
    let first = s.create("application:alpha", app("alpha", "running"));
    first.expect("首次该存得下");
    let again = s.create("application:alpha", app("alpha", "running"));
    let e = again.expect_err("同键重复必须拒");
    let want = Reason::DanglingRef {
        target: "application:alpha".to_string(),
    };
    assert_eq!(e.reason, want);
    assert_eq!(s.count(), 1);
}

/// ★ 反例：改／删**不存在的键** ⇒ 拒（不是静默成功）。
#[test]
fn store_refuses_update_and_delete_of_a_missing_key() {
    let mut s = Store::new();
    let upd = s.update("application:nope", app("nope", "running"));
    let e1 = upd.expect_err("改不存在的键必须拒");
    assert_eq!(
        e1.reason,
        Reason::DanglingRef {
            target: "application:nope".into()
        }
    );
    let del = s.delete("application:nope");
    let e2 = del.expect_err("删不存在的键必须拒");
    assert_eq!(
        e2.reason,
        Reason::DanglingRef {
            target: "application:nope".into()
        }
    );
    assert_eq!(s.count(), 0);
}

/// 正控：存 → 改 → 取 → 删，一条走通。
#[test]
fn store_can_update_and_delete() {
    let mut s = Store::new();
    let made = s.create("application:alpha", app("alpha", "installed"));
    made.expect("该存得下");
    let changed = s.update("application:alpha", app("alpha", "running"));
    changed.expect("该改得动");
    let row = s.get("application:alpha").expect("该取得回");
    assert_eq!(row.get_str("state"), Some("running"));
    let gone = s.delete("application:alpha");
    gone.expect("该删得掉");
    assert!(s.get("application:alpha").is_none());
    assert_eq!(s.count(), 0);
}

/// ★ 反例：按类找 —— 没有的类 ⇒ 空，**不许全收**。
#[test]
fn store_search_by_kind_returns_only_that_kind() {
    let s = store_with_three();
    let apps = s.search_by_kind("application");
    assert_eq!(apps, ["application:alpha", "application:beta"]);
    assert!(s.search_by_kind("frobnicator").is_empty(), "没有的类 ⇒ 空");
    assert_eq!(s.count(), 3);
    assert_eq!(s.keys().len(), 3);
}

/// ★★ 反例⑦之一：**filter 对**（类／格都给；不匹配的值必须落空；多条件是「与」）。
#[test]
fn query_filters_by_kind_and_field() {
    let s = store_with_three();
    let mut q = Query::new(&s);
    q = q.filter_kind("application");
    assert_eq!(q.count(), 2, "三条里有两条是应用");
    let q2 = Query::new(&s).filter_field("state", "flying");
    assert_eq!(q2.count(), 0, "★ 反例：不匹配的值必须落空，不许全收");
    let mut q3 = Query::new(&s);
    q3 = q3.filter_kind("application");
    q3 = q3.filter_field("state", "running");
    assert_eq!(q3.count(), 1, "两个条件是「与」");
    let mut q4 = Query::new(&s);
    q4 = q4.filter_kind("application");
    q4 = q4.filter_field("name", "alpha");
    q4 = q4.filter_field("state", "installed");
    assert_eq!(q4.count(), 0, "★ 反例：两个条件必须同时满足");
}

/// ★★ 反例⑦之二：**order_by ＋ take 对**（先排后取前 N；take(0) 必须空）。
#[test]
fn query_orders_by_field_and_takes_the_prefix() {
    let s = store_with_three();
    let q = Query::new(&s).order_by("name");
    assert_eq!(names_of(&q), "alpha,beta,sshd", "按 name 升序");
    let q2 = Query::new(&s).order_by("name").take(2);
    assert_eq!(q2.count(), 2);
    assert_eq!(names_of(&q2), "alpha,beta", "take 取排序后的前 N");
    let q3 = Query::new(&s).take(10);
    assert_eq!(q3.count(), 3, "取超过总数 ⇒ 有多少给多少");
    let q4 = Query::new(&s).take(0);
    assert_eq!(q4.count(), 0, "★ 反例：take(0) 必须空，不许当没设");
}

/// first 与 count 口径一致。
#[test]
fn query_first_agrees_with_count() {
    let s = store_with_three();
    let q = Query::new(&s).order_by("name");
    assert_eq!(q.count(), 3);
    let hit = q.first();
    assert_eq!(
        hit.map(|(k, _)| k),
        Some("application:alpha"),
        "序定后的第一条"
    );
    let mut q2 = Query::new(&s);
    q2 = q2.filter_kind("frobnicator");
    assert_eq!(q2.count(), 0, "没有的类 ⇒ 空");
    assert!(q2.first().is_none());
}

/// 只读核对：本件用到的类名都是真实本体里有的。
#[test]
fn kinds_used_here_are_declared_in_the_ontology() {
    let declared = section_keys("objects");
    assert!(declared.iter().any(|k| k == "application"));
    assert!(declared.iter().any(|k| k == "service"));
}
