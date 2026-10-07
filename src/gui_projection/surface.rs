//! 屏面投影（`M12`）—— **机器可读的"现在的页面状态"**。
//!
//! ## 它为什么存在（三位评审一致指向的那一格）
//!
//! 作者的要求逐字：「**改天又来一个业务软件，怎么样能知道现在页面的状态就 OK 了**……
//! **不需要知道就是我之前点了哪些东西怎么样怎么样**，我**只知道现在的状态**就 OK 了。」
//!
//! 今天没有任何一个出口能兑现它：
//!
//! | 出口 | 为什么不够 |
//! |---|---|
//! | `project language` / `project visual` | **顶点投影**：把整个世界的状态都倒出来，要看屏幕得自己从排版里挑格子 |
//! | `project serve` | 它是**叫醒**（`B10`），推的是**账本行**——那是**历史**，不是**现在的状态** |
//! | `state --json` | 同病更隐蔽：不含撤回事实，也不区分"屏幕那一面" |
//! | 界面规划**快照文档** | ★ 落盘即**第二本账**（缓存不是真相；`C11`） |
//!
//! ## 它的四条纪律
//!
//! - **机器可读**：正文是一段 JSON（不是给人看的排版）；
//! - **只给屏幕那一面**：只倒 `world://surface/*` 与 `world://cell/*`，别的类型**一个都不进来**；
//! - **现算不落盘**：纯函数，读的是**折叠态**，**不写任何缓存**；
//! - **带位点**：首行是同源头（`last_seq` ＋ `state` 指纹），JSON 里也各带一份 ——
//!   拿这份读数的人**能判断它是不是落后了**。
//!
//! ## 它与另外两份投影的关系
//!
//! 三份投影读的是**同一个** `State`、**同一份**词表，谁也不读谁的输出、谁也不持状态。
//! 首行是同源头 ⇒ **它们能互相验"同源"**（[`crate::gui_projection::assert_same_source`]）——
//! 这就是"两条独立腿"：同一条结论由两条各自独立的路走出来，再比对。
//!
//! ## 输出形状（**契约**，改动需走 `R5`）
//!
//! ```text
//! #world-core projection=surface world=1 vocab=fnv1a64:… last_seq=811 state=fnv1a64:…
//! 屏面投影（机器可读）—— 只给屏幕那一面：world://surface/* 与 world://cell/*
//! ────────────────────────────────────────────
//! {
//!   "last_seq": 811,
//!   "surfaces": [
//!     { "id": "world://surface/main",
//!       "name": "报销业务系统",
//!       "cells": [ { "id": "world://cell/c0", "style": "title", "label": "…", "order": 0 } ] } ]
//! }
//! ```
//!
//! 首行的 `projection=surface` 与另两份**只有这一个字段不同**（`header_line` 保证）。

use crate::gui_projection::{group_by_subject, header_line};
use crate::ontology_instance::readmodel::State;
use serde_json::{json, Map, Value};

/// 本投影倒哪两类主体。别的一律不进 —— "只给屏幕那一面"是一个**可判**的边界。
const SURFACE: &str = "surface";
const CELL: &str = "cell";

/// 从主体取类型：`world://<类型>/<实例>` → `<类型>`。
///
/// 与 `readmodel::type_of_subject` 同口径，但这里**只认前两段**：
/// 本投影不猜内嵌类型，认不出的类型**不进来**（宁缺勿滥）。
fn type_of(subject: &str) -> Option<&str> {
    let rest = subject.strip_prefix("world://")?;
    let mut it = rest.splitn(3, '/');
    let ty = it.next()?;
    // 必须**有实例名**（`world://cell/c1`），光是 `world://core` 这类主体不是对象实例
    it.next()?;
    Some(ty)
}

/// 把 `[(路径, 值)]` 收成一个 JSON 对象。路径有序（`State::entries` 保证）⇒ 结果确定。
fn fields_to_json(subject: &str, fields: &[(String, Value)]) -> Value {
    let mut m = Map::new();
    m.insert("id".to_string(), Value::String(subject.to_string()));
    for (k, v) in fields {
        m.insert(k.clone(), v.clone());
    }
    Value::Object(m)
}

/// 渲染屏面投影。
pub fn render(state: &State, world: u64, vocab: &str) -> String {
    let mut out = String::new();
    out.push_str(&header_line("surface", world, vocab, state));
    out.push('\n');
    out.push_str("屏面投影（机器可读）—— 只给屏幕那一面：world://surface/* 与 world://cell/*\n");
    out.push_str("────────────────────────────────────────────\n");

    if state.seen() == 0 {
        out.push_str("  （账本为空：这个世界还没有发生过任何事）\n");
        return out;
    }

    let grouped = group_by_subject(state);

    // 先把面收起来，格按 `owner` 挂回去；指不回任何面的格**单列**（不塞给谁、也不丢）。
    let mut surfaces: Vec<(String, Value)> = Vec::new();
    let mut cells: Vec<(String, Option<String>, Value)> = Vec::new();

    for (subject, fields) in &grouped {
        match type_of(subject) {
            Some(t) if t == SURFACE => {
                surfaces.push((subject.clone(), fields_to_json(subject, fields)))
            }
            Some(t) if t == CELL => {
                let owner = fields
                    .iter()
                    .find(|(k, _)| k == "owner")
                    .and_then(|(_, v)| v.as_str())
                    .map(str::to_string);
                cells.push((subject.clone(), owner, fields_to_json(subject, fields)));
            }
            _ => {}
        }
    }

    let mut surface_docs: Vec<Value> = Vec::new();
    let mut claimed: Vec<usize> = Vec::new();
    for (sid, sdoc) in &surfaces {
        let mut mine: Vec<Value> = Vec::new();
        for (i, (_cid, owner, cdoc)) in cells.iter().enumerate() {
            if owner.as_deref() == Some(sid.as_str()) {
                mine.push(cdoc.clone());
                claimed.push(i);
            }
        }
        let mut m = sdoc.as_object().cloned().unwrap_or_default();
        m.insert("cells".to_string(), Value::Array(mine));
        surface_docs.push(Value::Object(m));
    }

    // ★ 指不回任何面的格：**明说**，不许静默丢掉（静默丢＝把"没做到"写成"做到了"）。
    let mut orphans: Vec<Value> = Vec::new();
    for (i, (cid, owner, cdoc)) in cells.iter().enumerate() {
        if claimed.contains(&i) {
            continue;
        }
        let mut m = cdoc.as_object().cloned().unwrap_or_default();
        m.insert(
            "why".to_string(),
            Value::String(format!(
                "这一格指不回任何面（owner={}）",
                owner
                    .clone()
                    .unwrap_or_else(|| "（这一格没有 owner）".to_string())
            )),
        );
        m.insert("id".to_string(), Value::String(cid.clone()));
        orphans.push(Value::Object(m));
    }

    let doc = json!({
        "last_seq": state.last_seq(),
        "state": state.digest(),
        "world": world,
        "vocab": vocab,
        "surfaces": surface_docs,
        "orphans": orphans,
    });

    match serde_json::to_string_pretty(&doc) {
        Ok(s) => {
            out.push_str(&s);
            out.push('\n');
        }
        Err(e) => {
            // 序列化失败**必须说出来**，不许印一段空 JSON 让人以为"世界是空的"
            out.push_str(&format!("  （屏面投影序列化失败：{e}）\n"));
        }
    }
    out
}

#[cfg(test)]
mod unit {
    use super::*;
    use crate::common::event;
    use crate::gui_projection::assert_same_source;
    use serde_json::json;

    fn st(evs: Vec<Value>) -> State {
        State::fold(&evs).unwrap()
    }

    fn chg(seq: u64, subj: &str, path: &str, after: Value) -> Value {
        event::new_event(
            seq,
            "change",
            "world://test",
            event::change_body(subj, path, json!(null), after),
        )
    }

    /// 带前值的一条 change。★ 反例里**必须给真前值** —— 给 `null` 会被读模型
    /// 以 `BeforeMismatch` 拒折（这正是世界的写入侧判据在干活，实测撞到过）。
    fn chg_from(seq: u64, subj: &str, path: &str, before: Value, after: Value) -> Value {
        event::new_event(
            seq,
            "change",
            "world://test",
            event::change_body(subj, path, before, after),
        )
    }

    fn world_with_one_surface_and_cell() -> State {
        st(vec![
            chg(1, "world://surface/main", "name", json!("报销业务系统")),
            chg(2, "world://cell/c0", "owner", json!("world://surface/main")),
            chg(3, "world://cell/c0", "style", json!("title")),
            chg(4, "world://cell/c0", "label", json!("报销单 · 2026-10")),
        ])
    }

    #[test]
    fn only_screen_facing_types_come_out() {
        // ★ "只给屏幕那一面"是**可判的**：混进来的别类主体必须不出现
        let s = st(vec![
            chg(1, "world://surface/main", "name", json!("面")),
            chg(2, "world://notice/n-1", "muted", json!(true)),
            chg(3, "world://job/j-1", "status", json!("doing")),
        ]);
        let out = render(&s, 1, "fnv1a64:aaaa");
        assert!(out.contains("world://surface/main"), "面应在：{out}");
        assert!(!out.contains("world://notice"), "通告**不该**进来：{out}");
        assert!(!out.contains("world://job"), "作业**不该**进来：{out}");
    }

    #[test]
    fn cell_is_nested_under_its_surface() {
        let s = world_with_one_surface_and_cell();
        let out = render(&s, 1, "fnv1a64:aaaa");
        assert!(out.contains("\"cells\""), "格应挂在面下：{out}");
        assert!(out.contains("world://cell/c0"), "格应在：{out}");
        assert!(out.contains("报销单 · 2026-10"), "值应在：{out}");
    }

    #[test]
    fn orphan_cell_is_declared_not_dropped() {
        // ★ 反例：格指不回任何面 ⇒ 必须**明说**，不许静默丢掉
        let s = st(vec![chg(
            1,
            "world://cell/c9",
            "owner",
            json!("world://surface/nope"),
        )]);
        let out = render(&s, 1, "fnv1a64:aaaa");
        assert!(out.contains("orphans"), "应单列 orphans：{out}");
        assert!(out.contains("指不回任何面"), "应说明为什么：{out}");
    }

    #[test]
    fn carries_a_position() {
        // ★ 带位点：拿这份读数的人能判断它是不是落后了
        let s = world_with_one_surface_and_cell();
        let out = render(&s, 1, "fnv1a64:aaaa");
        assert!(out.contains("last_seq=4"), "首行应带位点：{out}");
        assert!(out.contains("\"last_seq\": 4"), "JSON 里也应带：{out}");
    }

    #[test]
    fn empty_ledger_says_so_and_is_same_source_with_visual() {
        let s = State::new();
        let out = render(&s, 1, "fnv1a64:aaaa");
        assert!(out.contains("账本为空"), "空账本要明说：{out}");
        // 空账本也要能同源比对（首行必须在）
        let v = crate::gui_projection::visual::render(&s, 1, "fnv1a64:aaaa");
        assert!(assert_same_source(&out, &v).is_ok());
    }

    #[test]
    fn same_source_with_visual_and_language() {
        // ★★ "两条独立腿"：同一条结论由两条各自独立的路走出来，再比对
        let s = world_with_one_surface_and_cell();
        let (a, b, c) = (
            crate::gui_projection::language::render(&s, 1, "fnv1a64:aaaa"),
            crate::gui_projection::visual::render(&s, 1, "fnv1a64:aaaa"),
            render(&s, 1, "fnv1a64:aaaa"),
        );
        assert!(assert_same_source(&a, &b).is_ok());
        assert!(
            assert_same_source(&a, &c).is_ok(),
            "屏面投影与语言投影必须同源"
        );
        assert!(
            assert_same_source(&b, &c).is_ok(),
            "屏面投影与视觉投影必须同源"
        );
    }

    #[test]
    fn lagging_surface_is_detected() {
        // 反例：屏面投影落后一个事件 ⇒ 同源判定必须红
        let s1 = world_with_one_surface_and_cell();
        let mut evs = vec![
            chg(1, "world://surface/main", "name", json!("面")),
            chg(2, "world://cell/c0", "owner", json!("world://surface/main")),
            chg(3, "world://cell/c0", "style", json!("title")),
            chg(4, "world://cell/c0", "label", json!("旧")),
        ];
        evs.push(chg_from(
            5,
            "world://cell/c0",
            "label",
            json!("旧"),
            json!("新"),
        ));
        let s2 = st(evs);
        let a = crate::gui_projection::visual::render(&s1, 1, "fnv1a64:aaaa");
        let c = render(&s2, 1, "fnv1a64:aaaa");
        assert!(assert_same_source(&a, &c).is_err(), "落后必须被抓到");
    }
}
