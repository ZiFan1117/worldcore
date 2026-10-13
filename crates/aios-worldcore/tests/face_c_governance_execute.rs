//! 面⑧（治理）＋面⑦（执行）：**未授权即拒**、**未登记动作即拒**。
//!
//! ★ 治理的口径取自本体 permissions 的 `_default_closed`：默认闭。
//!   本内核落法：**没授过 ⇒ 拒**（不是「没授过 ⇒ 放行」）。

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

fn who() -> Who {
    Who::new("world://user/zhang")
}

/// ★★ 反例④：**治理未授权即拒**。
/// 让它红的改法：把 Governance::can_execute 的默认改成「放行」⇒ 本用例红。
#[test]
fn unpermitted_capability_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    assert!(r.capability_kinds().contains(&"job.start"), "能力名该在册");
    let gov = Governance::new();
    let got = gov.can_execute(&who(), "job.start");
    let e = got.expect_err("没授过必须拒");
    let want = Reason::NotPermitted { capability: "job.start".to_string() };
    assert_eq!(e.reason, want);
    assert_eq!(e.code(), "worldcore.Refuse.NotPermitted");
}

/// 正控：授过 ⇒ 放行；且授权是**逐个能力、逐个主体**的。
#[test]
fn grant_is_per_capability_and_per_who() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let mut gov = Governance::new();
    let zhang = Who::new("world://user/zhang");
    let li = Who::new("world://user/li");
    gov.grant(&zhang, "job.start");
    assert!(gov.can_execute(&zhang, "job.start").is_ok(), "授过该放行");
    assert!(gov.can_execute(&li, "job.start").is_err(), "授甲不等于授乙");
    assert!(gov.can_execute(&zhang, "world.rekey").is_err(), "授一个不等于授全部");
    assert!(r.capability_kinds().contains(&"world.rekey"), "夹具失效：能力名该在册");
}

/// ★ 反例：**有角色 ≠ 有权**（授权授在能力上，本体 permissions 逐字）。
#[test]
fn a_role_is_not_a_grant() {
    let mut gov = Governance::new();
    let who = who();
    gov.assign_role(&who, "operator");
    assert!(gov.has_role(&who, "operator"), "角色该记下了");
    let got = gov.can_execute(&who, "job.start");
    assert!(got.is_err(), "有角色不等于有权");
}

/// ★★ 反例⑤：**未登记的动作即拒**。
#[test]
fn unregistered_action_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let ex = Exec::new(&r, DryRun);
    let params = Map::new();
    let got = ex.execute("frobnicate", &who(), &params);
    assert_eq!(got.expect_err("未登记动作必须拒").reason, Reason::UnknownKind);
}

/// 正控：在册动作 ⇒ 交给执行体；★ 今天交出的是 dry-run（不是「已经会做了」）。
#[test]
fn registered_action_goes_to_the_executor() {
    let r = Registry::load(ONT).expect("本体该装得上");
    assert!(r.action_kinds().contains(&"job.start"), "夹具失效：动作该在册");
    let ex = Exec::new(&r, DryRun);
    let mut params = Map::new();
    params.insert("subject".to_string(), json!("application:htop"));
    let got = ex.execute("job.start", &who(), &params);
    assert_eq!(got.expect("在册该放行"), "dry-run:job.start");
}

/// 只读核对：动作表与四族都取自真实本体（八面都不许自带清单）。
#[test]
fn action_and_family_tables_come_from_the_real_ontology() {
    let r = Registry::load(ONT).expect("本体该装得上");
    for a in section_keys("actions") {
        assert!(r.action_kinds().contains(&a.as_str()), "本体里的动作该在册：{a}");
    }
    let mut got = r.families();
    let mut want = section_keys("families");
    got.sort_unstable();
    want.sort_unstable();
    assert_eq!(got, want, "四族该与本体一致");
}

/// ★★ **会红反例（连挂缺口）**：治理面与执行面**今天没有连挂**。
/// 治理面已经拒了（第一句断言过），可是把同一笔交给执行面，**照样执行**。
/// 实现把「执行前查治理」接上后：本用例由红转绿，并删掉 ignore。
#[test]
#[ignore = "会红反例：Exec 不查 Governance —— 未授权者执行在册动作照样成功"]
fn unauthorized_execute_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let who = Who::new("world://user/nobody");
    let gov = Governance::new();
    let denied = gov.can_execute(&who, "job.start");
    assert!(denied.is_err(), "治理面已经拒了");
    let ex = Exec::new(&r, DryRun);
    let got = ex.execute("job.start", &who, &Map::new());
    assert!(got.is_err(), "★ 今天这里是红的：未授权也能执行，实得 {got:?}");
}
