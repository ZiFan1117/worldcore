//! 最小内核的端到端用例（先写会红的反例，再让它绿）。

use aios_worldcore::core::registry::Registry;
use aios_worldcore::core::types::{Reason, Registration, Who};
use aios_worldcore::engine::execute::{DryRun, Exec};
use aios_worldcore::engine::instances::{register_capability, Instances, RegisterEnv};
use aios_worldcore::engine::ledger::Ledger;
use aios_worldcore::engine::validate::ObjectSpec;
use aios_worldcore::governance::Governance;
use serde_json::json;

const ONT: &str = include_str!("../../../crates/aios-ontology/data/ontology.json");

fn reg(kind: &str, name: &str) -> Registration {
    let mut f = serde_json::Map::new();
    f.insert("name".to_string(), json!(name));
    Registration::new(kind, f)
}

#[test]
fn registry_reads_the_ontology() {
    let r = Registry::load(ONT).expect("本体该装得上");
    assert!(r.kinds().len() >= 9, "至少九类：{:?}", r.kinds());
    assert!(r.has_kind("application"), "application 该在册");
    assert!(!r.has_kind("frobnicator"), "没登记的东西不该在册");
}

/// ★★ 反例：**未登记的类型必须被拒**（这是本内核的第一条硬规矩）。
#[test]
fn unregistered_kind_is_refused() {
    let r = Registry::load(ONT).unwrap();
    let spec = ObjectSpec::load(ONT).unwrap();
    let mut gov = Governance::new();
    let who = Who::new("world://user/zhang");
    // ★ 治理先问：不先授「frobnicator.register」，这里会先拿到 NotPermitted、走不到「查在册」那一条。
    gov.grant(&who, register_capability("frobnicator"));
    let mut led = Ledger::load(ONT).unwrap();
    let mut env = RegisterEnv::new(&r, &spec, &gov, &mut led);
    let mut inst = Instances::new();
    let e = inst
        .register(&mut env, &who, &reg("frobnicator", "x"))
        .unwrap_err();
    assert_eq!(e.reason, Reason::UnknownKind);
    assert_eq!(inst.count(), 0, "被拒的东西不该留在册上");
    assert_eq!(led.all().len(), 0, "被拒的登记不许留账");
}

/// 正控：已登记的类型收下，并给一个序号。
#[test]
fn registered_kind_is_admitted() {
    let r = Registry::load(ONT).unwrap();
    let spec = ObjectSpec::load(ONT).unwrap();
    let mut gov = Governance::new();
    let who = Who::new("world://user/zhang");
    gov.grant(&who, register_capability("application"));
    let mut led = Ledger::load(ONT).unwrap();
    let mut inst = Instances::new();
    let seq = {
        let mut env = RegisterEnv::new(&r, &spec, &gov, &mut led);
        inst.register(&mut env, &who, &reg("application", "htop"))
            .unwrap()
    };
    assert_eq!(seq.0, 1, "序号由账发 ⇒ 第一笔就是 1");
    assert_eq!(inst.count(), 1);
    assert_eq!(inst.get("htop").map(|(k, _)| k), Some("application"));
    let line = led.get(seq).expect("成功登记必须同批记一笔账");
    assert_eq!(line.family, "change");
    assert_eq!(line.what, "application.register");
}

/// 缺名字 ⇒ 拒。
#[test]
fn missing_name_is_refused() {
    let r = Registry::load(ONT).unwrap();
    let spec = ObjectSpec::load(ONT).unwrap();
    let mut gov = Governance::new();
    let who = Who::new("world://user/zhang");
    gov.grant(&who, register_capability("application"));
    let mut led = Ledger::load(ONT).unwrap();
    let mut env = RegisterEnv::new(&r, &spec, &gov, &mut led);
    let mut inst = Instances::new();
    let empty = Registration::new("application", serde_json::Map::new());
    let e = inst.register(&mut env, &who, &empty).unwrap_err();
    assert_eq!(
        e.reason,
        Reason::MissingField {
            field: "name".to_string()
        }
    );
    assert_eq!(led.all().len(), 0, "被拒的登记不许留账");
}

/// 治理：**默认拒** —— 没授过的能力不许做。
#[test]
fn governance_denies_by_default() {
    let mut g = Governance::new();
    let who = Who::new("world://user/zhang");
    assert!(
        g.can_execute(&who, "package.install").is_err(),
        "没授过 ⇒ 拒"
    );
    g.grant(&who, "package.install");
    assert!(
        g.can_execute(&who, "package.install").is_ok(),
        "授过 ⇒ 放行"
    );
}

/// 执行：未登记的动作 ⇒ 拒；在册的 ⇒ 交给执行体（今天是 dry-run）。
#[test]
fn execute_refuses_unknown_action() {
    let r = Registry::load(ONT).unwrap();
    let who = Who::new("world://user/zhang");
    let known = r.action_kinds()[0].to_string();
    // ★ 执行面现在也先问治理 ⇒ 两条路都得先授，否则先拿到 NotPermitted、分不清「未登记」与「没授权」。
    let mut gov = Governance::new();
    gov.grant(&who, "frobnicate");
    gov.grant(&who, known.clone());
    let ex = Exec::new(&r, &gov, DryRun);
    let p = serde_json::Map::new();
    assert!(ex.execute("frobnicate", &who, &p).is_err(), "未登记 ⇒ 拒");
    assert!(ex.execute(&known, &who, &p).is_ok(), "在册 ⇒ 放行");
}

/// 账：只追加；序号全局单增；能按族查。
#[test]
fn ledger_appends_and_queries() {
    let mut l = Ledger::load(ONT).unwrap();
    let who = Who::new("world://user/zhang");
    let a = l
        .append(&who, "act", "package.install", serde_json::Map::new())
        .unwrap();
    let b = l
        .append(&who, "notice", "job.completed", serde_json::Map::new())
        .unwrap();
    assert_eq!((a.0, b.0), (1, 2));
    assert_eq!(l.query_family("act").len(), 1);
    assert!(l.export_csv().starts_with("seq,who,family,what"));
}
