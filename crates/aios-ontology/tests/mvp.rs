//! MVP 判据：AIOS 的 action_name 由本体说了算（含会红的反例）。

use aios_ontology::{Ontology, Reject, CODE_ACTION_UNKNOWN};

const OUR_ONTOLOGY: &str = include_str!("../data/ontology.json");

fn our() -> Ontology {
    Ontology::load_str(OUR_ONTOLOGY).expect("我们的本体应当装载得起来")
}

fn doc() -> serde_json::Value {
    serde_json::from_str(OUR_ONTOLOGY).expect("本体是合法 JSON")
}

#[test]
fn loads_our_ontology_and_sees_9_actions() {
    let ontology = our();
    assert_eq!(ontology.action_names().len(), 9, "现取 9 条动作");
    assert_eq!(ontology.capability_names().len(), 9, "现取 9 个能力");
}

#[test]
fn accepts_a_declared_action() {
    let ontology = our();
    let verdict = ontology
        .validate_translation(r#"{"action_name":"notice.mute","parameters":{"subject":"world://notice/1"},"confidence":0.95,"reasoning":"用户要求静音"}"#)
        .expect("notice.mute 是本体的动作，应当过");
    assert_eq!(verdict.capability, "notice.mute");
    assert!(verdict.missing_required_parameters.is_empty());
}

#[test]
fn rejects_aios_prompt_example_file_read() {
    let ontology = our();
    let err = ontology
        .validate_translation(r#"{"action_name":"file.read","parameters":{},"confidence":1.0,"reasoning":"AIOS 提示词里的例子"}"#)
        .expect_err("file.read 不在我们本体里，必须拒");
    assert_eq!(
        err,
        Reject::UnknownActionName {
            action_name: "file.read".to_string()
        }
    );
    assert_eq!(err.code(), CODE_ACTION_UNKNOWN);
}

#[test]
fn rejection_is_driven_by_the_ontology_not_hardcoded() {
    // 牙齿：把 file.read 声明进本体（动作 + 能力），同一个调用必须从拒变过。
    let mut value = doc();
    value["_actions"]["file.read"] = serde_json::json!({
        "capability": "file.read",
        "reversible": false,
        "parameters": [{"name": "path", "required": true}]
    });
    value["_interfaces"]["file.read"] = serde_json::json!({"kind": "invoke", "what": "读一个文件"});
    let ontology = Ontology::load_str(&value.to_string()).expect("改造后的本体仍应装载");
    let verdict = ontology
        .validate_translation(
            r#"{"action_name":"file.read","parameters":{"path":"/etc/hostname"}}"#,
        )
        .expect("声明进本体之后，同一个调用必须过");
    assert_eq!(verdict.capability, "file.read");
}

#[test]
fn missing_section_is_refused() {
    let mut value = doc();
    value.as_object_mut().expect("是对象").remove("_actions");
    let err = Ontology::load_str(&value.to_string()).expect_err("缺 _actions 必须拒启");
    assert_eq!(
        err,
        Reject::MissingSection {
            section: "_actions".to_string()
        }
    );
}

#[test]
fn command_literal_in_entry_table_is_refused() {
    let mut value = doc();
    value["_functions"]["entries"] = serde_json::json!({"pacman": {"what": "装包"}});
    let err = Ontology::load_str(&value.to_string()).expect_err("入口表里放命令字面量必须红");
    assert!(matches!(err, Reject::FunctionLiteralNotAllowed { .. }));
}

#[test]
fn unknown_capability_is_refused() {
    let mut value = doc();
    value["_actions"]["notice.mute"]["capability"] = serde_json::json!("nonexistent.cap");
    let ontology = Ontology::load_str(&value.to_string()).expect("装载照旧");
    let err = ontology
        .validate_translation(r#"{"action_name":"notice.mute"}"#)
        .expect_err("引用了不存在的能力必须拒");
    assert!(matches!(err, Reject::ActionCapabilityUnknown { .. }));
}

#[test]
fn empty_function_table_is_reported_as_a_gap() {
    let ontology = our();
    assert_eq!(ontology.function_entry_count(), 0, "现取：入口表是空的");
    assert!(
        ontology
            .declared_gaps()
            .iter()
            .any(|g| g.contains("零实例")),
        "空入口表必须被如实报成缺口，不许当成已立"
    );
}
