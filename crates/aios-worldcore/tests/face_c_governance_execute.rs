//! 面⑧（治理）＋面⑦（执行）：**未授权即拒**、**未登记动作即拒**。
//!
//! ★ 治理的口径取自本体 permissions 的 `_default_closed`：默认闭。
//!   本内核落法：**没授过 ⇒ 拒**（不是「没授过 ⇒ 放行」）。
//! ★ 2026-10-13：**执行面已连挂治理** —— `Exec::execute` 先问 `Governance`（没授过 ⇒ `NotPermitted`）。
//! ★ 将来接哪个 AIOS 件：治理与「执行前查许可」应接
//!   `crates/aios-policy` 的写闸 ＋ `crates/aios-capability-runtime` 的能力运行时；
//!   本文件只按本内核今天的内存实现判。

use aios_worldcore::core::registry::Registry;
use aios_worldcore::core::types::{Reason, Who};
use aios_worldcore::engine::execute::{DryRun, Exec};
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
    let want = Reason::NotPermitted {
        capability: "job.start".to_string(),
    };
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
    assert!(
        gov.can_execute(&zhang, "world.rekey").is_err(),
        "授一个不等于授全部"
    );
    assert!(
        r.capability_kinds().contains(&"world.rekey"),
        "夹具失效：能力名该在册"
    );
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
    let mut gov = Governance::new();
    // ★ 执行先问治理：不先授这一项，拿到的是 NotPermitted、走不到「查在册」那一条。
    gov.grant(&who(), "frobnicate");
    let ex = Exec::new(&r, &gov, DryRun);
    let params = Map::new();
    let got = ex.execute("frobnicate", &who(), &params);
    assert_eq!(
        got.expect_err("未登记动作必须拒").reason,
        Reason::UnknownKind
    );
}

/// 正控：在册动作 ⇒ 交给执行体；★ 今天交出的是 dry-run（不是「已经会做了」）。
#[test]
fn registered_action_goes_to_the_executor() {
    let r = Registry::load(ONT).expect("本体该装得上");
    assert!(
        r.action_kinds().contains(&"job.start"),
        "夹具失效：动作该在册"
    );
    let mut gov = Governance::new();
    gov.grant(&who(), "job.start");
    let ex = Exec::new(&r, &gov, DryRun);
    let mut params = Map::new();
    // ★ Lead 代改（2026-10-13）：原夹具写 `"application:htop"`，**不合本体**
    //   `fn.job.start.inputs.subject = enum(change,act,notice,job)`。
    //   ★ 这一处红，正是「④ 接入函数面、逐条校入参**真的在跑**」的铁证：
    //     `Refuse { BadValue { field: "subject", rule: "enum(change,act,notice,job)" }, what: "fn.job.start" }`。
    //   （发现者＝实现席 rw-exec-gov，它在接最后一跳时先撞到。）
    params.insert("subject".to_string(), json!("job"));
    let got = ex.execute("job.start", &who(), &params);
    assert_eq!(got.expect("在册该放行"), "dry-run:job.start");
}

/// 只读核对：动作表与四族都取自真实本体（八面都不许自带清单）。
#[test]
fn action_and_family_tables_come_from_the_real_ontology() {
    let r = Registry::load(ONT).expect("本体该装得上");
    for a in section_keys("actions") {
        assert!(
            r.action_kinds().contains(&a.as_str()),
            "本体里的动作该在册：{a}"
        );
    }
    let mut got = r.families();
    let mut want = section_keys("families");
    got.sort_unstable();
    want.sort_unstable();
    assert_eq!(got, want, "四族该与本体一致");
}

/// ★★ **未授权即拒（执行面）**：治理面与执行面**已连挂**（2026-10-13，`#[ignore]` 已去掉）。
/// 治理面拒了，同一笔交给执行面也**必须拒**（实得 `NotPermitted`）。
#[test]
fn unauthorized_execute_is_refused() {
    let r = Registry::load(ONT).expect("本体该装得上");
    let who = Who::new("world://user/nobody");
    let gov = Governance::new();
    let denied = gov.can_execute(&who, "job.start");
    assert!(denied.is_err(), "治理面已经拒了");
    let ex = Exec::new(&r, &gov, DryRun);
    let got = ex.execute("job.start", &who, &Map::new());
    let e = got.expect_err("未授权不许执行");
    assert_eq!(
        e.reason,
        Reason::NotPermitted {
            capability: "job.start".to_string()
        }
    );
}
