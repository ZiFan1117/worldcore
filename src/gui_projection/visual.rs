//! 视觉投影（`M07`）—— **渲染出口**，给人看。
//!
//! ⚠️ **不是"终端版应用"，是"同一份真相的另一种画法"**。它与语言投影
//! 读的是**同一个** `State`、**同一份**词表（见 [`crate::gui_projection`]），
//! 彼此不交互、各自不持有状态。
//!
//! 输出形状（**契约**，改动需走 R5）：
//!
//! ```text
//! #world-core projection=visual world=1 vocab=fnv1a64:… last_seq=3 state=fnv1a64:…
//! 世界状态（视觉投影）
//! ────────────────────────────────────────────
//!   world://notice/n-1
//!       muted = false
//! ```
//!
//! 排版规则（**审计脚本依赖它，不许随意改**）：
//! - **2 空格缩进** = 主体行；
//! - **6 空格缩进** + `路径 = 值` = 字段行；
//! - 别的行（标题、分隔线、空行）审计脚本一律忽略。
//!
//! 为什么给"给人看的东西"定这种死规矩：**给人看的东西也要能被机器核对**。
//! 否则"两个投影同源"就只能靠肉眼比对——那不叫证明，那叫希望。

use crate::gui_projection::{group_by_subject, header_line};
use crate::ontology_instance::readmodel::State;

/// 渲染视觉投影。
pub fn render(state: &State, world: u64, vocab: &str) -> String {
    let mut out = String::new();
    out.push_str(&header_line("visual", world, vocab, state));
    out.push('\n');
    out.push_str("世界状态（视觉投影）\n");
    out.push_str("────────────────────────────────────────────\n");

    if state.seen() == 0 {
        out.push_str("  （账本为空：这个世界还没有发生过任何事）\n");
        return out;
    }

    out.push_str(&format!(
        "  已折叠 {} 条事件（最近序号 {}）｜动作 {} 条｜通告 {} 条\n",
        state.seen(),
        state.last_seq(),
        state.acts(),
        state.notices()
    ));
    out.push_str("────────────────────────────────────────────\n");

    for (subject, fields) in group_by_subject(state) {
        out.push_str(&format!("  {subject}\n"));
        for (path, value) in fields {
            out.push_str(&format!("      {path} = {value}\n"));
        }
    }
    out
}

/// 从视觉投影里取回 `(主体, 字段路径, 值)` 三元组（按上面的排版规则）。
///
/// 存在的意义与 [`crate::gui_projection::language::parse`] 相同：让"同源"可被机器核对。
pub fn parse(text: &str) -> Result<Vec<(String, String, serde_json::Value)>, String> {
    let mut out = Vec::new();
    let mut current: Option<String> = None;
    for line in text.lines().skip(1) {
        // ① 字段行：6 空格缩进 + `路径 = JSON值`
        if let Some(field) = line.strip_prefix("      ") {
            let subject = current
                .clone()
                .ok_or_else(|| format!("视觉投影里字段行出现在主体行之前：{line}"))?;
            let (path, raw) = field
                .split_once(" = ")
                .ok_or_else(|| format!("视觉投影字段行缺少 ` = ` 分隔：{line}"))?;
            let value: serde_json::Value = serde_json::from_str(raw)
                .map_err(|e| format!("视觉投影字段值不是合法 JSON（{raw}）：{e}"))?;
            out.push((subject, path.to_string(), value));
            continue;
        }
        // ② 主体行：2 空格缩进，且不是提示行/统计行
        if let Some(name) = line.strip_prefix("  ") {
            let name = name.trim();
            let is_note = name.is_empty()
                || name.starts_with('（')
                || name.starts_with('─')
                || name.starts_with("已折叠");
            if !is_note {
                current = Some(name.to_string());
            }
        }
        // ③ 其余（标题、分隔线、空行）忽略
    }
    Ok(out)
}
