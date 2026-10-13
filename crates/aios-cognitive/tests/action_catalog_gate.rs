//! ★ 我方新增（非上游）：**未登记动作名即拒** —— 翻译链的本体闸。
//!
//! 先写会红的反例（nd-tdd 用法 A）：本体里没有的动作名必须被拒；
//! 权威来源是本体（A-SEM-01），不是系统提示词里的自由字符串。
#![forbid(unsafe_code)]

use std::path::Path;
use std::sync::Arc;

use aios_cognitive::error::CognitiveError;
use aios_cognitive::router::ModelRouter;
use aios_cognitive::translator_engine::{gate_action_name, TranslatorEngine};
use aios_ontology::Ontology;

fn our_ontology() -> Ontology {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../aios-ontology/data/ontology.json"
    );
    Ontology::load_file(Path::new(path)).expect("本体应能装载")
}

/// 红：AIOS 系统提示词里举的例子（file.read），本体里没有 ⇒ 必须拒。
#[test]
fn unregistered_action_name_is_refused() {
    let ontology = our_ontology();
    let err = gate_action_name(&ontology, "file.read").expect_err("未登记的动作名必须被拒");
    match err {
        CognitiveError::TranslationRefused(msg) => {
            assert!(
                msg.contains("ActionUnknown") || msg.contains("UnknownAction"),
                "拒的理由要带本体的错误码，实得: {msg}"
            );
        }
        other => panic!("拒的形态应当是 TranslationRefused，实得 {other:?}"),
    }
}

/// 正控：本体里已登记的动作名，逐个都不该被拒（证明它不是永远拒）。
#[test]
fn declared_action_names_pass() {
    let ontology = our_ontology();
    let names: Vec<String> = ontology
        .action_names()
        .iter()
        .map(|s| (*s).to_string())
        .collect();
    assert!(!names.is_empty(), "本体动作表不许是空集");
    for name in &names {
        gate_action_name(&ontology, name)
            .unwrap_or_else(|e| panic!("已登记动作 {name} 不该被拒: {e:?}"));
    }
}

/// 未注入本体时，引擎保持原行为（本笔不改变默认路径）。
#[test]
fn engine_without_ontology_keeps_legacy_behaviour() {
    let engine = TranslatorEngine::new(Arc::new(ModelRouter::with_table(vec![])));
    engine
        .validate_action_name("file.read")
        .expect("未注入本体时不得改变原行为");
}

/// 注入本体后，引擎这一层也拒未登记的动作名、放行已登记的。
#[test]
fn engine_with_ontology_gates_action_names() {
    let ontology = Arc::new(our_ontology());
    let first = ontology
        .action_names()
        .first()
        .map(|s| (*s).to_string())
        .expect("本体动作表不许是空集");
    let engine =
        TranslatorEngine::new(Arc::new(ModelRouter::with_table(vec![]))).with_ontology(ontology);
    assert!(
        engine.validate_action_name("file.read").is_err(),
        "未登记必须拒"
    );
    assert!(
        engine.validate_action_name(&first).is_ok(),
        "已登记必须放行"
    );
}
