//! 面⑨「关系面」的**会红反例**与正控：**装载校两端 → 连边三问 → 按 `from`／`to` 查**。
//!
//! ★ **如实登记**：宿主**无 cargo** ⇒ 本席**没跑过**这些测试。
//!   「会红」的口径是**当场可判**的两条：① `links.rs` 是**新增件** —— 本面之前**不存在**
//!   （`store.rs` 里只有一句注释提过 link）⇒ 下面**每一条**在旧代码下都无从通过；
//!   ② 每条断言判的是**读出来的事实**（拒的码／拒的目标／查出来的是谁），不是形式。
//!   转绿由 Lead 在 VM 上取数。

use crate::core::registry::Registry;
use crate::core::types::{Reason, Refuse};

use super::{Links, Node};

/// 真本体（★ 权威；本仓判据与测试都以它为唯一来源）。
const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

/// 合成本体：`links.from` 指着**不在 `objects` 的类**（★ 「不可判读的声明」那一形态）。
const FROM_DANGLING: &str = r#"{
  "objects": { "human": { "fields": { "name": "string" } } },
  "links": { "human-bound-to-ghost": { "from": "ghost", "to": "human" } },
  "interfaces": {}, "actions": {}, "functions": {}
}"#;

/// 合成本体：`links.to` 指着**不在 `objects` 的类**（★ 与上一条**分开**：证两端**都**判）。
const TO_DANGLING: &str = r#"{
  "objects": { "device": { "fields": { "name": "string" } } },
  "links": { "device-bound-to-ghost": { "from": "device", "to": "ghost" } },
  "interfaces": {}, "actions": {}, "functions": {}
}"#;

/// 合成本体：声明**缺 `to`**（★ 缺项不许当「没那一项」）。
const TO_MISSING: &str = r#"{
  "objects": { "device": { "fields": { "name": "string" } } },
  "links": { "device-bound-to-human": { "from": "device" } },
  "interfaces": {}, "actions": {}, "functions": {}
}"#;

fn registry() -> Registry {
    Registry::load(ONT).expect("册该装得上")
}

fn links() -> Links {
    Links::load(ONT).expect("关系面该装得上")
}

fn node(kind: &str, name: &str) -> Node {
    Node::new(kind, name)
}

/// 拒的**目标**（`DanglingRef.target`）；不是这一种就当场炸（★ 免得断言被别的码蒙混过去）。
fn target_of(e: &Refuse) -> String {
    match &e.reason {
        Reason::DanglingRef { target } => target.clone(),
        other => panic!("期望 DanglingRef，实得 {other:?}"),
    }
}

/// 拒的**格名**（`MissingField.field`）。
fn field_of(e: &Refuse) -> String {
    match &e.reason {
        Reason::MissingField { field } => field.clone(),
        other => panic!("期望 MissingField，实得 {other:?}"),
    }
}

// ── 正控：出厂本体那三条边，逐条对上（★ 条数以本体现取为准，这里只钉名字与两端） ──

#[test]
fn real_ontology_declares_the_three_named_edges() {
    let l = links();
    for (name, from, to) in [
        ("device-bound-to-human", "device", "human"),
        ("service-runs-on-device", "service", "device"),
        ("application-speaks-on-port", "application", "port"),
    ] {
        let d = l.decl(name).unwrap_or_else(|| panic!("{name} 该在册"));
        assert_eq!(
            (d.from.as_str(), d.to.as_str()),
            (from, to),
            "{name} 的两端"
        );
    }
}

// ── 反例1／2：两端任一端不在 objects 在册 ⇒ 装载即拒 ──

#[test]
fn dangling_from_endpoint_is_refused_at_load() {
    let e = Links::load(FROM_DANGLING).unwrap_err();
    assert_eq!(e.code(), Reason::DanglingRef { target: String::new() }.code());
    assert_eq!(target_of(&e), "ghost");
    assert_eq!(e.what, "links.human-bound-to-ghost.from");
}

#[test]
fn dangling_to_endpoint_is_refused_at_load() {
    let e = Links::load(TO_DANGLING).unwrap_err();
    assert_eq!(e.code(), Reason::DanglingRef { target: String::new() }.code());
    assert_eq!(target_of(&e), "ghost");
    assert_eq!(e.what, "links.device-bound-to-ghost.to");
}

/// 反例3：声明缺 `to` ⇒ 拒（`MissingField{to}`），**不许**当成「没那一项」放行。
#[test]
fn missing_endpoint_is_refused_at_load() {
    let e = Links::load(TO_MISSING).unwrap_err();
    assert_eq!(e.code(), Reason::MissingField { field: String::new() }.code());
    assert_eq!(field_of(&e), "to");
}

// ── 反例4～7：连边三问，逐一拒（★ 拒了 ⇒ 表上一行都不留） ──

#[test]
fn unknown_link_is_refused() {
    let reg = registry();
    let mut l = links();
    let e = l
        .connect(&reg, "no-such-edge", node("device", "d1"), node("human", "h1"))
        .unwrap_err();
    assert_eq!(target_of(&e), "no-such-edge");
    assert_eq!(l.count(), 0, "被拒的边不许留痕");
}

#[test]
fn endpoint_kind_not_declared_is_refused() {
    let reg = registry();
    let mut l = links();
    let e = l
        .connect(
            &reg,
            "device-bound-to-human",
            node("frobnicator", "x"),
            node("human", "h1"),
        )
        .unwrap_err();
    assert_eq!(target_of(&e), "frobnicator");
    assert_eq!(l.count(), 0);
}

#[test]
fn wrong_end_kind_is_refused() {
    let reg = registry();
    let mut l = links();
    let e = l
        .connect(
            &reg,
            "device-bound-to-human",
            node("human", "h1"),
            node("human", "h2"),
        )
        .unwrap_err();
    assert_eq!(target_of(&e), "human");
    assert!(e.what.contains("from"), "该指出是哪一端：{}", e.what);
    assert_eq!(l.count(), 0);
}

#[test]
fn duplicate_edge_is_refused() {
    let reg = registry();
    let mut l = links();
    l.connect(
        &reg,
        "device-bound-to-human",
        node("device", "d1"),
        node("human", "h1"),
    )
    .expect("第一笔该收下");
    let e = l
        .connect(
            &reg,
            "device-bound-to-human",
            node("device", "d1"),
            node("human", "h1"),
        )
        .unwrap_err();
    assert_eq!(target_of(&e), "device-bound-to-human");
    assert_eq!(l.count(), 1);
}

// ── 反例8（★ 空集的形态）：查一个**没有边**的实例 ⇒ 空表，不是拒、不是错 ──

#[test]
fn querying_an_instance_without_edges_is_empty() {
    let reg = registry();
    let mut l = links();
    l.connect(
        &reg,
        "application-speaks-on-port",
        node("application", "htop"),
        node("port", "p1"),
    )
    .expect("该收下");
    assert_eq!(l.count(), 1, "★ 先证「不是永远空」：确实有一条边");
    let untouched = node("human", "zhang");
    assert!(l.neighbors(&untouched).is_empty());
    assert!(l.edges_of(&untouched).is_empty());
    assert!(l.outgoing(&untouched).is_empty());
    assert!(l.incoming(&untouched).is_empty());
}

// ── 正控：连上之后，两个方向都查得到 ──

#[test]
fn connect_then_query_both_directions() {
    let reg = registry();
    let mut l = links();
    let d = node("device", "d1");
    let h = node("human", "zhang");
    l.connect(&reg, "device-bound-to-human", d.clone(), h.clone())
        .expect("该收下");
    assert_eq!(l.count(), 1);
    assert_eq!(l.edges().len(), 1);
    assert_eq!(l.edges()[0].other(&d), Some(&h));
    assert_eq!(l.outgoing(&d), vec![&h], "from 端连出去的是谁");
    assert_eq!(l.incoming(&h), vec![&d], "to 端被谁连进来");
    assert_eq!(l.neighbors(&d), vec![&h]);
    assert_eq!(l.neighbors(&h), vec![&d], "★ 反向也查得到");
    assert_eq!(l.edges_of(&h).len(), 1);
}

// ── 正控：一个类参与哪些已声明的边（Palantir 的 `get_linked_types` 同位置） ──

#[test]
fn decls_of_kind_finds_both_roles() {
    let l = links();
    let names: Vec<&str> = l
        .decls_of_kind("device")
        .iter()
        .map(|d| d.name.as_str())
        .collect();
    assert!(names.contains(&"device-bound-to-human"), "device 是 from 端");
    assert!(names.contains(&"service-runs-on-device"), "device 是 to 端");
    let apps: Vec<&str> = l
        .decls_of_kind("application")
        .iter()
        .map(|d| d.name.as_str())
        .collect();
    assert!(apps.contains(&"application-speaks-on-port"));
    assert!(l.decls_of_kind("frobnicator").is_empty());
}

// ── 正控：空边表（本体已装载、一条边都没有） ──

#[test]
fn empty_face_has_no_declarations_and_no_edges() {
    let l = Links::empty();
    assert!(l.edge_names().is_empty());
    assert_eq!(l.count(), 0);
    assert!(l.decl("device-bound-to-human").is_none());
}
