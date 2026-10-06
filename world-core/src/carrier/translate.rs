//! **外部变化 → 世界消息**（书 §4.5）—— 前值必须带上；翻不出来就报错，不许猜。
//!
//! ## 它在写侧管哪一半
//!
//! 书 §4.5 把"外面发生的事怎么写成一条消息"分成两半：**设备的动作**变成消息（`act`，
//! 见 [`crate::carrier::run`] 与 [`crate::carrier::capd`]），与**旧系统的状态**变成消息（`change`）。
//! 本模块是后者：把外面告诉我们的"哪一处变了"翻成世界里的一条 `change` 信纸。
//!
//! ## 书 §4.5 逐字（`docs/理论/语义世界-理论书-第一版-合订.md:595`）
//!
//! > 旧系统的状态变成消息，难点在前值。旧系统知道自己现在是什么样，不知道原来是什么样；
//! > 文件系统能告诉你某个文件昨天被改过，告诉不了你改的是哪个字段、原来是什么值。
//! > 写侧要做的是把"某个文件的一行变了"翻成"某个对象的某个字段从旧值变成新值"，
//! > 前值必须带上。少了前值，撤销与复盘各缺一半材料。
//!
//! 同节 `:597` 逐字：
//!
//! > 翻的时候还有一条要守：写侧不许替世界补意思。翻不出来就报错，
//! > 不许猜一个近似的字段名填上去。猜出来的字段名会进账本，进去以后就成了"事实"，
//! > 而它从来没被任何人说过。
//!
//! ## 两条硬口径（都写成了结构，不是注释）
//!
//! | 口径 | 落成什么 | 反着做会怎样 |
//! |---|---|---|
//! | **前值必须带上** | [`ExternalChange::before`] 是 `Option<Value>`：`None` ⇒ **报错**；显式的 `null` 前值是**合法**的前值 | 拿 `null`／新值顶 ⇒ 账本里出现一个**没人说过**的旧值 |
//! | **翻不出来不许猜** | [`translate`] 只认**逐字相等**的 (主体, 字段)；不在声明里 ⇒ **报错** | 猜一个相近的名字 ⇒ 那个名字进账本变成"事实" |
//!
//! ⚠️ 「没有前值」与「前值是空」是**两件事**（与 `src/common/event.rs:141-147` 的 `with_trace`
//! 同一口径：`None` 与"指向空"不同）。故这里用 `Option` 而不是"拿 `Value::Null` 兼作缺省"。
//!
//! ## 为什么 `Declared` 是个**窄接口**（而不是直接收一份本体）
//!
//! 本模块只需要知道**一件事**：某个 (主体, 字段) 在出厂声明里吗。把宽度压到这一处，
//! 与 `src/bus/mod.rs` 的 `RequestSink` 是同一手法——**收方只需回答一个问题**。
//! 还有一条硬理由：`M10` 与 `M01`／`M05` 之间**不得新增 import 边**
//! （`M05 → M10` 已存在：`src/gate/mod.rs:32` 读载体清单）；反向再连即**成环**，
//! `WC-ATOM-001` §二 A-4 不许，`tools/module_graph.py` 判据② 会红。

use serde_json::{json, Value};

/// 世界里"某个 (主体, 字段) 有没有被声明"——**写侧需要的唯一一条世界侧知识**。
///
/// 实现方（装配层）应当拿**真正的声明**来回答；本模块**不**自带任何字段表，
/// 因为"世界里的名字"只有一个权威载体（出厂本体），在写侧再抄一份就是第二份事实。
pub trait Declared {
    /// 世界里存在 `subject` 这个对象的 `path` 字段吗（**逐字相等**，不做近似匹配）。
    fn is_declared(&self, subject: &str, path: &str) -> bool;
}

/// 一处**外部变化**（外面告诉我们的样子，尚未与世界对齐）。
#[derive(Debug, Clone, PartialEq)]
pub struct ExternalChange {
    /// 哪一处外部（报错与复盘时点名：文件／表／设备）。
    pub source: String,
    /// 世界里的主体（名字对齐由**声明**保证，不由写侧猜）。
    pub subject: String,
    /// 世界里的字段路径。
    pub path: String,
    /// **前值**。`None` = 外部系统给不出旧值 ⇒ [`translate`] 报错。
    pub before: Option<Value>,
    /// 新值。
    pub after: Value,
}

impl ExternalChange {
    /// 造一处外部变化。
    pub fn new(
        source: &str,
        subject: &str,
        path: &str,
        before: Option<Value>,
        after: Value,
    ) -> Self {
        ExternalChange {
            source: source.to_string(),
            subject: subject.to_string(),
            path: path.to_string(),
            before,
            after,
        }
    }

    /// 人读的一处定位（报错里点名"是哪一处翻不出来"）。
    pub fn at(&self) -> String {
        format!("{}（{} 的 {}）", self.source, self.subject, self.path)
    }
}

/// 把一处外部变化翻成一条 `change` 信纸。**翻不出来就报错**——本函数不返回"近似值"。
///
/// 两条判据（顺序即书 §4.5 的顺序：`:595` 先讲前值、`:597` 再讲字段名）：
///
/// 1. **前值**：`before == None` ⇒ `ext.world.Carrier.NoPreviousValue`；
/// 2. **字段名**：`(subject, path)` 不在声明里 ⇒ `ext.world.Carrier.UnmappableField`。
///
/// 两条都不做"兜底"：**没有 fallback 分支**，因为任何一个兜底都会往账本里塞一个
/// 从来没人说过的值或名字（书 §4.5 `:597`）。
pub fn translate(ext: &ExternalChange, declared: &dyn Declared) -> Result<Value, String> {
    let before = match &ext.before {
        Some(b) => b.clone(),
        None => {
            return Err(format!(
                "ext.world.Carrier.NoPreviousValue: 外部变化 {} 没有前值——\
                 写侧不许替世界补意思：**翻不出来就报错，不许猜**。\n\
                 \x20 为什么不能拿 null 或新值顶上：少了前值，撤销与复盘各缺一半材料（书 §4.5）；\n\
                 \x20 而顶上来的那个值会进账本，进去以后就成了「事实」，它却从来没被任何人说过。\n\
                 \x20 处置：回那处外部系统把旧值取出来再提交；取不到就**不要提交**这一处变化",
                ext.at()
            ))
        }
    };

    if !declared.is_declared(&ext.subject, &ext.path) {
        return Err(format!(
            "ext.world.Carrier.UnmappableField: 外部变化 {} 翻不出来——\
             声明里没有这个 (主体, 字段)。\n\
             \x20 写侧**不许猜**一个近似的字段名填上去（书 §4.5）：猜出来的字段名会进账本，\n\
             \x20 进去以后就成了「事实」，而它从来没被任何人说过。\n\
             \x20 处置：在声明里把这个名字对齐，或改外部侧的字段名；\
             **不要**改写成相近的名字再提交",
            ext.at()
        ));
    }

    // 信纸形状与 `src/common/event.rs:168` 的 `change_body` 逐字一致：
    // `subject` / `path` / `before` / `after` 四项，一个不多一个不少。
    Ok(json!({
        "subject": ext.subject,
        "path": ext.path,
        "before": before,
        "after": ext.after,
    }))
}

#[cfg(test)]
mod unit {
    use super::*;

    /// 一份**测试用**的声明面（真装配用出厂本体回答，见 `tests/write_side.rs` 的 `Book`）。
    struct Book(Vec<(&'static str, &'static str)>);

    impl Declared for Book {
        fn is_declared(&self, subject: &str, path: &str) -> bool {
            self.0.iter().any(|(s, p)| *s == subject && *p == path)
        }
    }

    fn book() -> Book {
        Book(vec![("world://notice/1", "muted")])
    }

    #[test]
    fn a_change_with_a_previous_value_translates_verbatim() {
        let ext = ExternalChange::new(
            "/etc/old-system/state.tsv:12",
            "world://notice/1",
            "muted",
            Some(json!(false)),
            json!(true),
        );
        let body = translate(&ext, &book()).unwrap();
        assert_eq!(
            body,
            json!({"subject":"world://notice/1","path":"muted","before":false,"after":true})
        );
        // 四个字段一个不多一个不少（形状与 `event::change_body` 同）
        let keys: Vec<&String> = body.as_object().unwrap().keys().collect();
        assert_eq!(keys, vec!["after", "before", "path", "subject"]);
    }

    #[test]
    fn a_missing_previous_value_is_refused_and_never_filled_in() {
        // 外部系统只知道"现在是什么样"——这正是书 §4.5 `:595` 说的那个难点
        let ext = ExternalChange::new(
            "/etc/old-system/state.tsv:12",
            "world://notice/1",
            "muted",
            None,
            json!(true),
        );
        let e = translate(&ext, &book()).unwrap_err();
        assert_eq!(
            crate::common::error::code_of(&e),
            Some("ext.world.Carrier.NoPreviousValue"),
            "{e}"
        );
        // 不许"顺手填一个"：错误里要能读出是哪一处
        assert!(e.contains("state.tsv:12"), "{e}");
        assert!(e.contains("不许猜"), "{e}");
    }

    #[test]
    fn an_explicit_null_previous_value_is_still_a_previous_value() {
        // 「没有前值」与「前值是空」是两件事（与 `event::with_trace` 同一口径）
        let ext = ExternalChange::new(
            "/etc/old-system/state.tsv:13",
            "world://notice/1",
            "muted",
            Some(Value::Null),
            json!(true),
        );
        let body = translate(&ext, &book()).unwrap();
        assert_eq!(body["before"], Value::Null);
        assert!(body.as_object().unwrap().contains_key("before"));
    }

    #[test]
    fn a_similar_but_undeclared_field_name_is_refused_not_guessed() {
        // 外部那台机器叫 `mute`，世界里声明的是 `muted` —— **近似不等于对齐**
        let ext = ExternalChange::new(
            "/etc/old-system/state.tsv:14",
            "world://notice/1",
            "mute",
            Some(json!(false)),
            json!(true),
        );
        let e = translate(&ext, &book()).unwrap_err();
        assert_eq!(
            crate::common::error::code_of(&e),
            Some("ext.world.Carrier.UnmappableField"),
            "{e}"
        );
        assert!(e.contains("不许猜"), "{e}");
        assert!(
            !e.contains("muted"),
            "错误正文里不得出现被猜出来的名字：{e}"
        );
    }

    #[test]
    fn an_undeclared_subject_is_refused_too() {
        let ext = ExternalChange::new(
            "/etc/old-system/state.tsv:15",
            "world://nowhere/1",
            "muted",
            Some(json!(false)),
            json!(true),
        );
        assert!(translate(&ext, &book()).is_err());
    }
}
