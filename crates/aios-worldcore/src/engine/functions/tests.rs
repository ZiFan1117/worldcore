//! 面⑤「函数」的**会红反例**与正控：**查在册 ⇒ 逐条校入参 ⇒ 才交给「干活的」**。
//!
//! ★ **如实登记**：宿主**无 cargo** ⇒ 本席**没跑过**这些测试。「会红」按旧代码推断：
//!   旧 worldcore **没有函数面**（`engine/` 里没有 `functions` 这一件）⇒ 本文件在旧代码下
//!   **编译不过 ＝ 必红**；转绿由 Lead 在 VM 上取数。

use std::cell::RefCell;
use std::rc::Rc;

use serde_json::{json, Map, Value};

use crate::core::types::{Admit, Reason, Refuse};

use super::{Doer, DryDoer, Function, Functions};

/// 真本体（★ 权威；本仓测试与判据都以它为唯一来源）。
const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

/// 出厂**合成本体**：只为**证机制会咬**（真本体九条入口名都是干净的）。
fn synth(entries: Value) -> String {
    json!({
        "objects": {},
        "links": {},
        "interfaces": {},
        "actions": {},
        "functions": {
            "_registered_host_commands": ["pacman", "systemctl"],
            "entries": entries,
        },
    })
    .to_string()
}

fn args(pairs: &[(&str, Value)]) -> Map<String, Value> {
    let mut m = Map::new();
    for (k, v) in pairs {
        m.insert((*k).to_string(), v.clone());
    }
    m
}

fn real() -> Functions<DryDoer> {
    Functions::load(ONT).expect("本体该装得上")
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

/// 记名的「干活的」：谁被叫过（★ 只为证「被拒的调用碰不到它」）。
struct Spy {
    seen: Rc<RefCell<Vec<String>>>,
}

impl Doer for Spy {
    fn do_it(&self, function: &Function, _args: &Map<String, Value>) -> Admit<Value> {
        self.seen.borrow_mut().push(function.id().to_string());
        Ok(Value::String("spy".to_string()))
    }
}

/// ★ 反例1：未在册的函数 ⇒ `UnknownKind`（「未登记即拒」在函数面的落法）。
#[test]
fn unknown_function_is_refused() {
    let f = real();
    let e = f
        .call("fn.notice.sing", &args(&[("subject", json!("notice"))]))
        .unwrap_err();
    assert_eq!(e.reason, Reason::UnknownKind);
    assert_eq!(e.code(), "worldcore.Refuse.UnknownKind");
    assert!(f.get("fn.notice.sing").is_none());
}

/// ★ 反例2：入参**类型**不对 ⇒ `BadValue{subject}`，理由串＝本体声明的类型。
#[test]
fn wrong_arg_type_is_refused() {
    let f = real();
    let e = f
        .call("fn.notice.mute", &args(&[("subject", json!(7))]))
        .unwrap_err();
    assert_eq!(bad_field(&e), "subject");
    assert_eq!(bad_rule(&e), "enum(change,act,notice,job)");
}

/// ★ 反例3：**取值域**外的值 ⇒ 拒（`enum(…)` 的取值域算在类型里）。
#[test]
fn value_out_of_domain_is_refused() {
    let f = real();
    let e = f
        .call("fn.presence.report", &args(&[("subject", json!("robot"))]))
        .unwrap_err();
    assert_eq!(bad_field(&e), "subject");
    assert_eq!(
        bad_rule(&e),
        "enum(human,agent,application,service,device,workflow)"
    );
}

/// ★ 反例4：**未声明的入参** ⇒ 拒（本体没写这一条入参）。
#[test]
fn undeclared_arg_is_refused() {
    let f = real();
    let e = f
        .call(
            "fn.job.start",
            &args(&[("subject", json!("job")), ("reason", json!("手动"))]),
        )
        .unwrap_err();
    assert_eq!(bad_field(&e), "reason");
    assert_eq!(bad_rule(&e), "本体未声明该入参");
}

/// ★ 反例5（次序）：被拒的调用**碰不到**「干活的」那一层。
#[test]
fn refused_call_never_reaches_the_doer() {
    let seen = Rc::new(RefCell::new(Vec::new()));
    let f = Functions::load_with(
        ONT,
        Spy {
            seen: Rc::clone(&seen),
        },
    )
    .expect("本体该装得上");
    // ① 未在册 ⇒ 拒；② 入参不对 ⇒ 拒。两条都不许碰到「干活的」。
    let _ = f.call("fn.notice.sing", &args(&[("subject", json!("notice"))]));
    let _ = f.call("fn.notice.mute", &args(&[("subject", json!(7))]));
    assert!(seen.borrow().is_empty(), "被拒的调用不许碰到干活的");
    // 正控：三条都对 ⇒ 才轮到「干活的」，并把它的东西原样带回来。
    let called = f
        .call("fn.notice.mute", &args(&[("subject", json!("notice"))]))
        .expect("该收下");
    assert_eq!(seen.borrow().len(), 1);
    assert_eq!(seen.borrow()[0], "fn.notice.mute");
    assert_eq!(called.function_id, "fn.notice.mute");
    assert_eq!(called.value, json!("spy"));
}

/// ★ 反例6：**宿主命令名**当入口 ⇒ 拒（本体 `functions._no_command_literal` 的整表那一半）。
#[test]
fn host_command_name_as_entry_is_refused() {
    let text = synth(json!({
        "pacman": { "function_id": "pacman", "inputs": {}, "output_type": "" }
    }));
    let e = Functions::load(&text).unwrap_err();
    assert_eq!(e.reason, Reason::BadName);
    assert_eq!(e.code(), "worldcore.Refuse.BadName");
}

/// ★ 反例7：带空格／斜杠的入口名 ⇒ 拒（同一条口径的前一半）。
#[test]
fn entry_name_with_command_literal_is_refused() {
    let text = synth(json!({
        "rm -rf /": { "function_id": "rm -rf /", "inputs": {}, "output_type": "" }
    }));
    assert_eq!(Functions::load(&text).unwrap_err().reason, Reason::BadName);
}

/// ★ 反例8：本体没装载（五节缺一 / 不是合法 JSON）⇒ `OntologyNotLoaded`。
#[test]
fn unloaded_ontology_is_refused() {
    let four_sections = r#"{"objects":{},"links":{},"interfaces":{},"actions":{}}"#;
    assert_eq!(
        Functions::load(four_sections).unwrap_err().reason,
        Reason::OntologyNotLoaded
    );
    assert_eq!(
        Functions::load("not json").unwrap_err().reason,
        Reason::OntologyNotLoaded
    );
}

/// ★ 反例9：条目名与 `function_id` 不一致 ⇒ 拒（表以 `function_id` 为键）。
#[test]
fn entry_key_must_equal_function_id() {
    let text = synth(json!({
        "fn.a": { "function_id": "fn.b", "inputs": {}, "output_type": "" }
    }));
    assert_eq!(Functions::load(&text).unwrap_err().reason, Reason::BadName);
}

/// ★ 反例10：条目不是对象 / 缺 `function_id` ⇒ 拒。
#[test]
fn malformed_entry_is_refused() {
    let not_object = synth(json!({ "fn.a": 3 }));
    assert_eq!(
        Functions::load(&not_object).unwrap_err().reason,
        Reason::BadName
    );
    let no_id = synth(json!({ "fn.a": { "inputs": {} } }));
    assert_eq!(
        Functions::load(&no_id).unwrap_err().reason,
        Reason::MissingField {
            field: "function_id".to_string()
        }
    );
}

// ★ 2026-10-13 Lead 代改：原此处写 `mod ok;` 指向一个**未被创建**的文件，导致
//   `error[E0583]: file not found for module ok`（整 crate 编不过）⇒ 已删。
//   若将来要另开正控件，请建 `functions/ok.rs` 并在这里 `mod ok;`。
