//! 导出 —— 把账原样倒成 CSV。
//!
//! ★ 学它的口径：**只导出、不推理**（不改一笔、不补一格、不按谁的眼睛裁）。
//! ★ 表头逐字沿用我方既有件（seq,who,family,what）—— 接口不许变。

use crate::core::types::Event;

/// 账的 CSV：表头 ＋ 每笔一行（追加序）。
pub(super) fn csv(rows: &[Event]) -> String {
    let mut s = String::from("seq,who,family,what");
    for e in rows {
        s.push('\n');
        s.push_str(&e.seq.0.to_string());
        s.push(',');
        s.push_str(e.who.name());
        s.push(',');
        s.push_str(&e.family);
        s.push(',');
        s.push_str(&e.what);
    }
    s
}
