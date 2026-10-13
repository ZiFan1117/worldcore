//! 面③（校验）—— **进门安检的六样，每样一条**（会红的反例）。
//!
//! 六样：① 类型名在册 ② 格名合法 ③ 必填齐 ④ 值的类型对 ⑤ 取值域对 ⑥ 引用不悬空。
//! ★ 第④样今天**没有人校**（validate 面没有对应的口）—— 它以 #[ignore] 的会红反例留在这里，
//!   跑 cargo test -- --ignored 就见红；补上实现后那条转绿。

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

fn named(kind: &str, name: &str) -> Registration {
    Registration::new(kind, fields(&[("name", json!(name))]))
}

/// 取值域从**真实本体**取：objects.<类>._field_meta.<格>.options。
fn options_of(kind: &str, field: &str) -> Vec<String> {
    let d = doc();
    let mut out = Vec::new();
    if let Some(list) = d["objects"][kind]["_field_meta"][field]["options"].as_array() {
        for v in list {
            if let Some(s) = v.as_str() {
                out.push(s.to_string());
            }
        }
    }
    out
}

/// ★ 第①样：类型名必须在册（不在册 ⇒ 拒，不是「当别的类收下」）。
#[test]
fn six_1_kind_must_be_registered() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let bad = named("frobnicator", "x");
    let got = check_shape(&r, &bad);
    let e = got.expect_err("未登记类型必须在校验面被拒");
    assert_eq!(e.reason, Reason::UnknownKind);
}

/// ★ 第②样：格名合法 —— 空格名、带空格／斜杠的名字都要拒。
#[test]
fn six_2_field_name_must_be_legal() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let blank_field = Registration::new("application", fields(&[("", json!("x"))]));
    let got = check_shape(&r, &blank_field);
    assert_eq!(got.expect_err("空格名必须拒").reason, Reason::BadName);
    let spaced_name = named("application", "a b");
    let got2 = check_shape(&r, &spaced_name);
    assert_eq!(got2.expect_err("名字带空格必须拒").reason, Reason::BadName);
    let slashed = named("application", "a/b");
    let got3 = check_shape(&r, &slashed);
    assert_eq!(got3.expect_err("名字带斜杠必须拒").reason, Reason::BadName);
}

/// ★ 第③样：必填齐 —— 只缺**一个**（第一个）也要拒。
#[test]
fn six_3_required_fields_must_be_present() {
    let d = doc();
    let mut required: Vec<String> = Vec::new();
    if let Some(list) = d["families"]["change"]["required"].as_array() {
        for v in list {
            if let Some(s) = v.as_str() {
                required.push(s.to_string());
            }
        }
    }
    assert!(required.len() >= 2, "夹具失效：{required:?}");
    let mut m = fields(&[("name", json!("htop"))]);
    for f in required.iter().skip(1) {
        m.insert(f.clone(), json!("x"));
    }
    let reg = Registration::new("application", m);
    let refs: Vec<&str> = required.iter().map(String::as_str).collect();
    let got = check_required(&reg, &refs);
    let e = got.expect_err("缺第一个必填格必须拒");
    assert_eq!(e.reason, Reason::MissingField { field: required[0].clone() });
}

/// ★★ 第④样（**会红反例**）：值的类型对。
///
/// 本体逐字申报 `objects.application.fields.did == "string"`；
/// 今天把整数 42 塞进这一格，**登记面照收**（validate 面没有「值的类型」这一校）。
/// 补上实现后：跑 `cargo test -p aios-worldcore -- --ignored` 由红转绿，并删掉 ignore。
#[test]
#[ignore = "会红反例：第④样「值的类型对」今天无人校 —— 整数塞进 string 格仍被收下"]
fn six_4_declared_value_type_must_match() {
    let d = doc();
    let declared = d["objects"]["application"]["fields"]["did"].as_str();
    assert_eq!(declared, Some("string"), "夹具失效：application.did 该申报 string");
    let r = Registry::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let row = fields(&[("name", json!("htop")), ("did", json!(42))]);
    let bad = Registration::new("application", row);
    let got = inst.register(&r, &who_of("zhang"), &bad);
    assert!(got.is_err(), "★ 今天这里是红的：42 不该塞进 string 格，实得 {got:?}");
}

fn who_of(name: &str) -> Who {
    Who::new(format!("world://user/{name}"))
}

/// ★ 第⑤样：取值域外 ⇒ 拒；域内 ⇒ 放行；格缺席 ⇒ 不归它管（归第③样）。
#[test]
fn six_5_value_must_be_in_the_declared_domain() {
    let opts = options_of("application", "state");
    assert!(opts.len() >= 2, "夹具失效：{opts:?}");
    let refs: Vec<&str> = opts.iter().map(String::as_str).collect();
    let row = fields(&[("name", json!("htop")), ("state", json!("flying"))]);
    let bad = Registration::new("application", row);
    let got = check_enum(&bad, "state", &refs);
    let want = Reason::BadValue { field: "state".to_string(), rule: opts.join("|") };
    assert_eq!(got.expect_err("域外的值必须拒").reason, want);
    let okrow = fields(&[("name", json!("htop")), ("state", json!("running"))]);
    let good = Registration::new("application", okrow);
    assert!(check_enum(&good, "state", &refs).is_ok(), "域内该放行");
    let absent = named("application", "htop");
    assert!(check_enum(&absent, "state", &refs).is_ok(), "格缺席不归取值域管");
}

/// ★ 第⑥样：引用不悬空 —— 指向不存在的东西 ⇒ 拒；不是 world:// 的值 ⇒ 不判。
#[test]
fn six_6_references_must_not_dangle() {
    let d = doc();
    let declared = d["objects"]["device"]["fields"]["bound_to"].as_str();
    assert!(declared.is_some(), "夹具失效：device.bound_to 该有申报");
    let good = fields(&[("name", json!("laptop")), ("bound_to", json!("world://human/zhang"))]);
    let reg = Registration::new("device", good);
    assert!(check_refs(&reg, &["world://human/zhang"]).is_ok(), "指向在册的东西该放行");
    let bad = fields(&[("name", json!("laptop")), ("bound_to", json!("world://human/nobody"))]);
    let reg2 = Registration::new("device", bad);
    let got = check_refs(&reg2, &["world://human/zhang"]);
    let want = Reason::DanglingRef { target: "world://human/nobody".to_string() };
    assert_eq!(got.expect_err("悬空引用必须拒").reason, want);
    let plainrow = fields(&[("name", json!("laptop")), ("cert", json!("CN=lap"))]);
    let plain = Registration::new("device", plainrow);
    assert!(check_refs(&plain, &[]).is_ok(), "非引用值不该被当悬空引用");
}
