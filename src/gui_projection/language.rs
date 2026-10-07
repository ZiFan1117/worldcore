//! 语言投影（`M06`）—— **结构化出口**，给程序读。
//!
//! 纯文本、逐行 JSON（JSON Lines）：任何语言都能解析，不需要本项目在场
//! （`WC-SRS-001` REQ-N-001 语言无关）。
//!
//! 输出形状（**契约**，改动需走 R5）：
//!
//! ```text
//! #world-core projection=language world=1 vocab=fnv1a64:… last_seq=3 state=fnv1a64:…
//! {"subject":"world://notice/n-1","fields":{"muted":false}}
//! ```
//!
//! - 第 1 行：同源头（见 [`crate::gui_projection`]）；
//! - 其后每行一个主体，`fields` 是"字段路径 → 当前值"；
//! - **不输出未发生的事**：只反映账本折叠出的状态，不猜测、不补默认值。

use crate::gui_projection::{group_by_subject, header_line};
use crate::ontology_instance::readmodel::State;
use serde_json::{json, Map, Value};

/// 渲染语言投影。
pub fn render(state: &State, world: u64, vocab: &str) -> String {
    let mut out = String::new();
    out.push_str(&header_line("language", world, vocab, state));
    out.push('\n');
    for (subject, fields) in group_by_subject(state) {
        let mut obj = Map::new();
        for (path, value) in fields {
            obj.insert(path, value);
        }
        let line = json!({ "subject": subject, "fields": Value::Object(obj) });
        out.push_str(&line.to_string());
        out.push('\n');
    }
    out
}

/// 从语言投影里取回 `(主体, 字段路径, 值)` 三元组。
///
/// 存在的意义：让"同源"可以被**机器核对**——把语言投影解析回来，
/// 与读模型逐项比对，而不是靠"看起来一样"。
pub fn parse(text: &str) -> Result<Vec<(String, String, Value)>, String> {
    let mut out = Vec::new();
    for (idx, line) in text.lines().enumerate() {
        if idx == 0 || line.trim().is_empty() {
            continue;
        }
        let v: Value = serde_json::from_str(line)
            .map_err(|e| format!("语言投影第 {} 行不是合法 JSON：{e}", idx + 1))?;
        let subject = v
            .get("subject")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("语言投影第 {} 行缺 subject", idx + 1))?;
        let fields = v
            .get("fields")
            .and_then(Value::as_object)
            .ok_or_else(|| format!("语言投影第 {} 行缺 fields", idx + 1))?;
        for (path, value) in fields {
            out.push((subject.to_string(), path.clone(), value.clone()));
        }
    }
    Ok(out)
}
