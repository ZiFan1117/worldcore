//! 面①（注册）＋面②（实例注册）：**未登记即拒**、**缺必填即拒**。
//!
//! ★ 每条用例都是「会红的反例」：它断言的是**拒**。
//!    谁把规矩删掉（改成静默收下），这里当场红。
//! ★ 本体用**真实件**装载（include_str! 指向 aios-ontology 的 ontology.json）；
//!    夹具也从那份 JSON 现取 —— 本体改了，夹具会自己说话，不会悄悄假绿。

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

fn who() -> Who {
    Who::new("world://user/zhang")
}

fn named(kind: &str, name: &str) -> Registration {
    Registration::new(kind, fields(&[("name", json!(name))]))
}

/// 取一节里的键（去掉 `_` 前缀的注记键）—— 夹具与只读核对共用。
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

/// 必填表从**真实本体**取：`families.<族>.required` 逐字。
fn required_of(family: &str) -> Vec<String> {
    let d = doc();
    let mut out = Vec::new();
    if let Some(list) = d["families"][family]["required"].as_array() {
        for v in list {
            if let Some(s) = v.as_str() {
                out.push(s.to_string());
            }
        }
    }
    out
}

/// ★★ 反例①：**未登记的类型必须被拒** —— 本内核第一条硬规矩。
/// 让它红的改法：把 Instances::register 里查在册那一段删掉 ⇒ 本用例红。
#[test]
fn unregistered_kind_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    assert!(!section_keys("objects").iter().any(|k| k == "frobnicator"));
    let mut inst = Instances::new();
    let want = named("frobnicator", "x");
    let got = inst.register(&r, &who(), &want);
    let e = got.expect_err("未登记类型必须拒");
    assert_eq!(e.reason, Reason::UnknownKind);
    assert_eq!(inst.count(), 0, "被拒的不许留在册上");
}

/// 正控：在册类型收下，并给一个单增序号。
#[test]
fn registered_kind_is_admitted() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let ra = inst.register(&r, &who(), &named("application", "htop"));
    let rb = inst.register(&r, &who(), &named("service", "sshd"));
    let sa = ra.expect("在册类型该收下");
    let sb = rb.expect("在册类型该收下");
    assert_eq!((sa.0, sb.0), (1, 2), "序号该单增");
    assert_eq!(inst.count(), 2);
    assert_eq!(inst.get("htop").map(|(k, _)| k), Some("application"));
}

/// ★★ 反例②：**缺必填即拒**。
/// 必填表不是编的：来自本体 families.change.required。
#[test]
fn missing_required_field_is_refused() {
    let required = required_of("change");
    assert!(required.len() >= 3, "夹具失效：{required:?}");
    let reg = named("application", "htop");
    let refs: Vec<&str> = required.iter().map(String::as_str).collect();
    let got = check_required(&reg, &refs);
    let e = got.expect_err("缺必填必须拒");
    assert_eq!(e.reason, Reason::MissingField { field: required[0].clone() });
}

/// 反例②之二：登记面自己那道「必须有名字」。
#[test]
fn registration_without_name_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let empty = Registration::new("application", Map::new());
    let got = inst.register(&r, &who(), &empty);
    let e = got.expect_err("缺 name 必须拒");
    assert_eq!(e.reason, Reason::MissingField { field: "name".to_string() });
    assert_eq!(inst.count(), 0);
}

/// 反例：空名字是坏名字（不是「缺格」，是「值不可用」）。
#[test]
fn blank_name_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let blank = named("application", "   ");
    let got = inst.register(&r, &who(), &blank);
    assert_eq!(got.expect_err("空名字必须拒").reason, Reason::BadName);
    assert_eq!(inst.count(), 0);
}

/// 反例：本体不是合法 JSON ⇒ 拒（不许装不上还当空表用）。
#[test]
fn broken_ontology_text_is_refused() {
    let got = Registry::load("{ 这不是 JSON }");
    assert_eq!(got.expect_err("不是 JSON 必须拒").reason, Reason::OntologyNotLoaded);
}

/// 反例：五节缺一 ⇒ 拒（与本体 _five_elements 同口径）。
#[test]
fn ontology_missing_a_section_is_refused() {
    let text = "{\"objects\":{},\"links\":{},\"interfaces\":{},\"actions\":{}}";
    let got = Registry::load(text);
    assert_eq!(got.expect_err("缺 functions 节必须拒").reason, Reason::OntologyNotLoaded);
}

/// 只读核对：注册面的类清单必须与本体 objects 键一致（八面都不许自带清单）。
#[test]
fn registry_kinds_come_from_the_real_ontology() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let declared = section_keys("objects");
    assert!(!declared.is_empty());
    for k in &declared {
        assert!(r.has_kind(k), "本体里有的类，注册面必须有：{k}");
    }
    assert!(!r.has_kind("frobnicator"));
}
