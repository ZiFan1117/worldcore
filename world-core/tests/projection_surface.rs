//! 屏面投影（`M12`）——集成用例。
//!
//! 三条，各自可判真假：
//! * **s01 只给屏幕那一面**：混进别类主体（`notice`／`job`）⇒ **红**；
//! * **s02 带位点**：首行与 JSON 里都必须有 `last_seq`（拿这份读数的人要能判断自己落后没落后）；
//! * **s03 三份投影同源**：`language`／`visual`／`surface` 两两互验 —— 这是评审要的
//!   **"两条独立腿"**（只比 language↔visual 时两者共用同一份折叠 ⇒ 断言近乎恒真）。
//!
//! ★ 本件是 `M12` 的**测试件**（四件同夹的第三件）；实现＝`src/gui_projection/surface.rs`，
//! 契约＝`WC-IC-001` §5.12，登记＝`WC-MODREG-001` 的 `M12` 行。

use serde_json::{json, Value};
use world_core::common::event;
use world_core::gui_projection::{assert_same_source, language, surface, visual};
use world_core::ontology_instance::readmodel::State;

fn chg(seq: u64, subj: &str, path: &str, after: Value) -> Value {
    event::new_event(
        seq,
        "change",
        "world://test",
        event::change_body(subj, path, json!(null), after),
    )
}

fn st(evs: Vec<Value>) -> State {
    State::fold(&evs).unwrap()
}

fn one_surface_one_cell() -> State {
    st(vec![
        chg(1, "world://surface/main", "name", json!("报销业务系统")),
        chg(2, "world://cell/c0", "owner", json!("world://surface/main")),
        chg(3, "world://cell/c0", "style", json!("title")),
        chg(4, "world://cell/c0", "label", json!("报销单 · 2026-10")),
    ])
}

/// **s01**：屏面投影**只**倒 `world://surface/*` 与 `world://cell/*`。
///
/// 这是"只给屏幕那一面"这条边界的可判形态：混进别类主体 ⇒ 本用例红。
#[test]
fn s01_only_screen_facing_types_come_out() {
    let s = st(vec![
        chg(1, "world://surface/main", "name", json!("面")),
        chg(2, "world://notice/n-1", "muted", json!(true)),
        chg(3, "world://job/j-1", "status", json!("doing")),
    ]);
    let out = surface::render(&s, 1, "fnv1a64:aaaa");
    assert!(out.contains("world://surface/main"), "面应在输出里：{out}");
    assert!(
        !out.contains("world://notice"),
        "通告**不该**进屏面投影：{out}"
    );
    assert!(
        !out.contains("world://job"),
        "作业**不该**进屏面投影：{out}"
    );
}

/// **s02**：带位点 —— 首行同源头里与 JSON 正文里**都要有**。
#[test]
fn s02_carries_a_position() {
    let s = one_surface_one_cell();
    let out = surface::render(&s, 1, "fnv1a64:aaaa");
    assert!(out.contains("last_seq=4"), "首行应带位点：{out}");
    assert!(out.contains("\"last_seq\": 4"), "JSON 也应带位点：{out}");
    assert!(
        out.contains("projection=surface"),
        "首行应是本投影的同源头：{out}"
    );
}

/// **s03**：三份投影两两同源（**两条独立腿**）。
///
/// ★ 反例面：把 `surface` 换成落后一个事件的 `State` ⇒ 同源判定必须**红**。
#[test]
fn s03_the_three_readings_are_same_source() {
    let s = one_surface_one_cell();
    let (a, b, c) = (
        language::render(&s, 1, "fnv1a64:aaaa"),
        visual::render(&s, 1, "fnv1a64:aaaa"),
        surface::render(&s, 1, "fnv1a64:aaaa"),
    );
    assert!(assert_same_source(&a, &b).is_ok(), "语言↔视觉应同源");
    assert!(assert_same_source(&a, &c).is_ok(), "语言↔屏面应同源");
    assert!(assert_same_source(&b, &c).is_ok(), "视觉↔屏面应同源");

    // 反例：屏面落后一个事件 ⇒ 必须被抓到
    let s2 = st(vec![
        chg(1, "world://surface/main", "name", json!("面")),
        chg(2, "world://cell/c0", "owner", json!("world://surface/main")),
        chg(3, "world://cell/c0", "style", json!("title")),
        chg(4, "world://cell/c0", "label", json!("旧")),
        event::new_event(
            5,
            "change",
            "world://test",
            event::change_body("world://cell/c0", "label", json!("旧"), json!("新")),
        ),
    ]);
    let lagging = surface::render(&s2, 1, "fnv1a64:aaaa");
    assert!(
        assert_same_source(&a, &lagging).is_err(),
        "屏面投影落后一个事件，同源判定必须红"
    );
}
