//! ★ **我方新增（非上游）**：worldcore 本体的对象类，能否在 AIOS-FS 里成为「个体类型」。
//!
//! 口径：**语义权威在我们本体**（`crates/aios-ontology/data/ontology.json` 的 `_objects`），
//! AIOS-FS 的 `ObjectKind` 只承担**存储实现**。本件验的是：我们的两个对象类
//! （`notice`／`job`）已经**成为可用的个体类型**（可序列化／可往返）。
//!
//! ★ 本件**先于实现**写（nd-tdd 用法 A）：在 `ObjectKind` 加变体之前，它编译不过。
#![forbid(unsafe_code)]

use aios_fs::object::ObjectKind;

/// 我们的类型在线上名字应当是 SCREAMING_SNAKE_CASE（与上游既有 10 类同形）。
#[test]
fn our_kinds_use_screaming_snake_names() {
    let n = serde_json::to_string(&ObjectKind::Notice).expect("序列化 notice");
    let j = serde_json::to_string(&ObjectKind::Job).expect("序列化 job");
    assert_eq!(n, "\"NOTICE\"");
    assert_eq!(j, "\"JOB\"");
}

/// 往返：我们的类型序列化后能再读回来（同一个体类型）。
#[test]
fn our_kinds_round_trip() {
    for k in [ObjectKind::Notice, ObjectKind::Job] {
        let s = serde_json::to_string(&k).expect("序列化");
        let back: ObjectKind = serde_json::from_str(&s).expect("反序列化");
        assert_eq!(k, back);
    }
}
