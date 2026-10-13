//! 面⑧ 治理的会红反例（从 `mod.rs` 拆出 —— 让主文件回到 300 行以内）。
//!
//! ★ 拆出的只是**测试**：主文件的字一句未改。

// ★ Lead 代改：拆件时误加了一个重复的 `use super::*;` ⇒ clippy 报 `unused import`。
//   保留**一个**（测试要用 Governance／Who／Reason／Step —— 都从 `super` 来）。
use super::*;

const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

/// 拿真本体改一处（只动 permissions.default）当反例夹具。
fn law_with_default(value: &str) -> String {
    let mut doc: serde_json::Value = serde_json::from_str(ONT).expect("本体该能解析");
    doc["permissions"]["default"] = serde_json::Value::String(value.to_string());
    doc.to_string()
}

/// ★★ 反例①：**地板默认拒**。让它红的改法：删掉地板那一级 ⇒ 本用例红。
#[test]
fn floor_denies_when_nothing_was_granted() {
    let gov = Governance::new();
    let who = Who::new("world://user/zhang");
    let e = gov
        .can_execute(&who, "package.install")
        .expect_err("没授过必须拒");
    assert_eq!(
        e.reason,
        Reason::NotPermitted {
            capability: "package.install".into()
        }
    );
    assert_eq!(e.code(), "worldcore.Refuse.NotPermitted");
    let log = gov.rulings();
    assert_eq!(log.len(), 1, "每答一次留一条裁定");
    assert_eq!(log[0].step, Step::Floor);
    assert!(!log[0].allowed);
}

/// ★★ 反例②：**法律没显式写 deny ⇒ 装载即拒**（本体 _default_closed）。
/// 让它红的改法：from_ontology 不查 permissions.default ⇒ 本用例红。
#[test]
fn law_without_explicit_deny_is_refused() {
    let e = Governance::from_ontology(&law_with_default("allow")).expect_err("allow 不安全");
    assert_eq!(e.code(), "worldcore.Refuse.BadValue");
    assert_eq!(e.what, "allow");
    let mut doc: serde_json::Value = serde_json::from_str(ONT).expect("本体该能解析");
    doc["permissions"]["default"].take();
    assert_eq!(
        Governance::from_ontology(&doc.to_string())
            .expect_err("缺 ⇒ 拒")
            .what,
        "<缺>"
    );
}

/// ★★ 反例③：**出厂法条那一级真的在判**。让它红的改法：删掉第二级 ⇒ 本用例红。
#[test]
fn declared_scope_decides_and_class_prefix_matches() {
    let gov = Governance::from_ontology(ONT).expect("出厂本体该装得上");
    assert!(gov
        .can_execute(&Who::new("world://presence/omarchy"), "notice.mute")
        .is_ok());
    assert!(
        gov.can_execute(&Who::new("world://user/zhang"), "notice.mute")
            .is_ok(),
        "段前缀"
    );
    assert!(
        gov.can_execute(&Who::new("world://nobody"), "notice.mute")
            .is_err(),
        "地板拒"
    );
    assert!(
        gov.can_execute(&Who::new("world://agent/dsh"), "job.start")
            .is_err(),
        "无此项"
    );
    assert_eq!(gov.rulings()[0].step, Step::Declared);
}

/// ★★ 反例④：**角色不是许可**（本体逐字：授权授在能力上）。
/// 让它红的改法：让 has_role 冒充 can_execute ⇒ 本用例红。
#[test]
fn a_role_is_not_a_grant() {
    let gov = Governance::from_ontology(ONT).expect("出厂本体该装得上");
    let zhang = Who::new("world://user/zhang");
    assert!(
        gov.has_role(&zhang, "human"),
        "roster 写 world://user ⇒ human"
    );
    assert!(
        gov.can_execute(&zhang, "job.start").is_err(),
        "有角色不等于有权"
    );
}

/// ★ 正控：运行时授过 ⇒ 第一级，且**逐主体逐能力**。
#[test]
fn grant_is_the_first_step_and_is_exact() {
    let mut gov = Governance::new();
    let zhang = Who::new("world://user/zhang");
    let li = Who::new("world://user/li");
    gov.grant(&zhang, "job.start");
    assert!(gov.can_execute(&zhang, "job.start").is_ok(), "授过该放行");
    assert!(gov.can_execute(&li, "job.start").is_err(), "授甲不等于授乙");
    assert!(
        gov.can_execute(&zhang, "world.rekey").is_err(),
        "授一个不等于授全部"
    );
    let log = gov.rulings();
    assert_eq!(log[0].step, Step::Granted);
    assert_eq!(log[0].code, "worldcore.Allow.Granted");
}
