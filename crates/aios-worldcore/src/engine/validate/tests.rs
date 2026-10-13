//! 面③「照本体逐格校」的**会红反例**与正控。
//!
//! ★ **如实登记**：宿主**无 cargo**（`Get-Command cargo` 取不到）⇒ 本席**没跑过**这些测试。
//!   每条的「会红」是**按旧代码推断**的：旧 `Instances::register` 只查「类型名在册 ＋ 有 name」，
//!   **一格都不校** ⇒ 下面 1–7 条断言在旧实现下必红；转绿由 Lead 在 VM 上取数。

use serde_json::{json, Map, Value};

use crate::core::types::{Reason, Refuse, Registration};

use super::{FieldType, ObjectSpec};

/// 真本体（★ 权威；本仓判据与测试都以它为唯一来源）。
const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

/// 出厂**合成本体**：只为**证机制会咬** —— 真本体今天没有任何一格写 `required: true`。
const SYNTHETIC: &str = r#"{
  "objects": {
    "widget": {
      "fields": { "name": "string", "order": "integer", "note": "一句自由度说明文字" },
      "_field_meta": { "order": { "required": true } }
    }
  },
  "links": {}, "interfaces": {}, "actions": {}, "functions": {}
}"#;

fn instance(kind: &str, fields: &[(&str, Value)]) -> Registration {
    let mut m = Map::new();
    for (k, v) in fields {
        m.insert((*k).to_string(), v.clone());
    }
    Registration::new(kind, m)
}

fn real() -> ObjectSpec {
    ObjectSpec::load(ONT).expect("本体该装得上")
}

fn synthetic() -> ObjectSpec {
    ObjectSpec::load(SYNTHETIC).expect("合成本体该装得上")
}

fn bad_field(e: &Refuse) -> String {
    match &e.reason {
        Reason::BadValue { field, .. } => field.clone(),
        other => panic!("期望 BadValue，实得 {other:?}"),
    }
}

fn bad_rule(e: &Refuse) -> String {
    match &e.reason {
        Reason::BadValue { rule, .. } => rule.clone(),
        other => panic!("期望 BadValue，实得 {other:?}"),
    }
}

fn missing_field(e: &Refuse) -> String {
    match &e.reason {
        Reason::MissingField { field } => field.clone(),
        other => panic!("期望 MissingField，实得 {other:?}"),
    }
}

/// 正控：在册的类就是从本体 `objects` 的非 `_` 键现取（★ 不另立清单）。
#[test]
fn kinds_come_from_the_ontology() {
    let s = real();
    assert!(s.has_kind("application"));
    assert!(!s.has_kind("frobnicator"));
    assert!(s.kinds().len() >= 9, "{:?}", s.kinds());
}

/// 正控：本体里那几种写法都认得（★ 含带尾注的 `integer  # UNIX 秒`）。
#[test]
fn declarations_are_read_as_the_ontology_writes_them() {
    let s = real();
    let human = s.fields_of("human").expect("human 该在册");
    assert_eq!(human["name"].field_type, FieldType::Str);
    assert_eq!(human["last_seen"].field_type, FieldType::Integer);
    let port = s.fields_of("port").expect("port 该在册");
    assert_eq!(
        port["state"].field_type.declaration(),
        "enum(declared,listening,retired)"
    );
    let device = s.fields_of("device").expect("device 该在册");
    assert_eq!(
        device["bound_to"].field_type,
        FieldType::Ref("human".to_string())
    );
    let surface = s.fields_of("surface").expect("surface 该在册");
    assert_eq!(surface["cells"].field_type, FieldType::Array);
    assert_eq!(surface["visible"].field_type, FieldType::Bool);
}

/// ★ 反例1：类不在册 ⇒ `UnknownKind`（不是静默收下、也不是偷偷当别的类）。
#[test]
fn unknown_kind_is_refused() {
    let s = real();
    let fields = [("name", json!("x"))];
    let e = s
        .check_instance(&instance("frobnicator", &fields))
        .unwrap_err();
    assert_eq!(e.code(), Reason::UnknownKind.code());
}

/// ★ 反例2：值类型不对（本体写 `integer`，给了字符串）⇒ `BadValue{last_seen}`。
#[test]
fn wrong_value_type_is_refused() {
    let s = real();
    let fields = [("name", json!("zhang")), ("last_seen", json!("昨天"))];
    let e = s.check_instance(&instance("human", &fields)).unwrap_err();
    assert_eq!(bad_field(&e), "last_seen");
    assert_eq!(bad_rule(&e), "integer");
}

/// ★ 反例3：取值域不对（`port.state` 只许 declared／listening／retired）⇒ `BadValue{state}`。
#[test]
fn value_out_of_enum_domain_is_refused() {
    let s = real();
    let fields = [("name", json!("p1")), ("state", json!("bogus"))];
    let e = s.check_instance(&instance("port", &fields)).unwrap_err();
    assert_eq!(bad_field(&e), "state");
    assert_eq!(bad_rule(&e), "enum(declared,listening,retired)");
}

/// ★ 反例4：本体没声明的格 ⇒ 拒（★ 不许偷偷多塞一格）。
#[test]
fn undeclared_field_is_refused() {
    let s = real();
    let fields = [("name", json!("htop")), ("sneaky", json!(1))];
    let e = s
        .check_instance(&instance("application", &fields))
        .unwrap_err();
    assert_eq!(bad_field(&e), "sneaky");
}

/// ★ 反例5：引用格必须是字符串（`device.bound_to` 是 `ref(human)`）。
#[test]
fn reference_must_be_a_string() {
    let s = real();
    let fields = [("name", json!("d1")), ("bound_to", json!(7))];
    let e = s.check_instance(&instance("device", &fields)).unwrap_err();
    assert_eq!(bad_field(&e), "bound_to");
    assert_eq!(bad_rule(&e), "ref(human)");
}

/// ★ 反例6（合成本体）：本体**显式**写了 `required: true` 而没填 ⇒ `MissingField{order}`。
#[test]
fn declared_required_missing_is_refused() {
    let s = synthetic();
    let fields = [("name", json!("w1"))];
    let e = s.check_instance(&instance("widget", &fields)).unwrap_err();
    assert_eq!(missing_field(&e), "order");
}

/// 正控：合成本体那个必填格填了 ⇒ 收下。
#[test]
fn declared_required_present_passes() {
    let s = synthetic();
    let fields = [("name", json!("w1")), ("order", json!(3))];
    assert!(s.check_instance(&instance("widget", &fields)).is_ok());
}

/// 正控：★ 本体 `objects._comment` 逐字「不是这几种写法的自由度说明文字一律放行」。
#[test]
fn freeform_declaration_is_passed() {
    let s = synthetic();
    let note = json!({ "任意": [1, 2] });
    let fields = [("name", json!("w1")), ("order", json!(1)), ("note", note)];
    assert!(s.check_instance(&instance("widget", &fields)).is_ok());
}

/// 正控：本体声明的格／类型都对 ⇒ 收下。
#[test]
fn good_instance_passes() {
    let s = real();
    let fields = [
        ("name", json!("htop")),
        ("did", json!("world://app/htop")),
        ("state", json!("running")),
    ];
    assert!(s.check_instance(&instance("application", &fields)).is_ok());
}

/// ★ 反例7：本体没装载（不是 JSON／五节缺一）⇒ `OntologyNotLoaded`（★ 谁都别想动）。
#[test]
fn unloaded_ontology_is_refused() {
    let a = ObjectSpec::load("not json").unwrap_err();
    assert_eq!(a.code(), Reason::OntologyNotLoaded.code());
    let b = ObjectSpec::load(r#"{"objects": {}}"#).unwrap_err();
    assert_eq!(b.code(), Reason::OntologyNotLoaded.code());
}
