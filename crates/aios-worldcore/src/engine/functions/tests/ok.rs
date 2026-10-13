//! 面⑤「函数」的正控（转绿那一半）：查在册 ⇒ 逐条校入参 ⇒ 才交给「干活的」，都成了。
//!
//! ★ 与母件 `tests.rs`（会红反例）同批；★ 拆开只为**每文件 < 300 行**。

use serde_json::{json, Value};

use super::{args, real};
/// 正控1：真本体 ⇒ **9 条**在册，名字升序，取得到。
#[test]
fn real_ontology_has_nine_functions() {
    let f = real();
    assert_eq!(f.len(), 9);
    assert!(!f.is_empty());
    assert_eq!(
        f.ids(),
        vec![
            "fn.job.cancel",
            "fn.job.finish",
            "fn.job.start",
            "fn.ledger.compact",
            "fn.notice.mute",
            "fn.notice.unmute",
            "fn.presence.report",
            "fn.world.migrate",
            "fn.world.rekey",
        ]
    );
}

/// 正控2：本体那五格都读得回来（`inputs` 是「名 ⇒ 声明」，不是位置参数）。
#[test]
fn function_fields_are_read_back() {
    let f = real();
    let m = f.get("fn.notice.mute").expect("该在册");
    assert_eq!(m.id(), "fn.notice.mute");
    assert_eq!(m.display_name(), "把一条通告静音");
    assert!(!m.description().is_empty());
    assert_eq!(m.inputs().len(), 1);
    assert_eq!(
        m.inputs().get("subject").map(|t| t.declaration()),
        Some("enum(change,act,notice,job)".to_string())
    );
    assert_eq!(m.output_type().declaration(), "enum(change,act,notice,job)");
}

/// 正控3：`describe()` 就是 P 的那五格（给 MCP 那类别单用）。
#[test]
fn describe_has_the_five_fields_of_p() {
    let f = real();
    let d = f.get("fn.presence.report").expect("该在册").describe();
    let obj = d.as_object().expect("describe 该是个对象");
    let mut keys: Vec<&str> = obj.keys().map(String::as_str).collect();
    keys.sort_unstable();
    assert_eq!(
        keys,
        vec![
            "description",
            "display_name",
            "function_id",
            "inputs",
            "output_type"
        ]
    );
    assert_eq!(obj.get("function_id"), Some(&json!("fn.presence.report")));
    assert_eq!(
        obj.get("inputs"),
        Some(&json!({
            "subject": "enum(human,agent,application,service,device,workflow)"
        }))
    );
}

/// 正控4：**少给入参不拒**（本体 `inputs` 没有 `required` 标记）；`null` 也只当没填。
#[test]
fn missing_args_are_not_refused() {
    let f = real();
    assert!(f.call("fn.notice.mute", &args(&[])).is_ok());
    assert!(f
        .call("fn.notice.mute", &args(&[("subject", Value::Null)]))
        .is_ok());
}

/// 正控5：**出参未定**的三条照原样收下（本体 `_note` 逐字：output_type 未定）。
#[test]
fn undecided_output_type_is_kept_as_declared() {
    let f = real();
    for id in ["fn.ledger.compact", "fn.world.rekey", "fn.world.migrate"] {
        let m = f.get(id).expect("该在册");
        assert_eq!(m.output_type().declaration(), "", "{id} 的出参今天未定");
    }
    let job = f.get("fn.job.start").expect("该在册");
    assert_eq!(
        job.output_type().declaration(),
        "enum(change,act,notice,job)"
    );
}

/// 正控6：默认「干活的」只报不干活，交回的值里带函数名（★ 别读成「已经会装了」）。
#[test]
fn dry_doer_reports_but_does_not_do() {
    let f = real();
    let called = f
        .call("fn.job.start", &args(&[("subject", json!("job"))]))
        .expect("该收下");
    assert_eq!(called.value, json!("dry-run:fn.job.start"));
}
