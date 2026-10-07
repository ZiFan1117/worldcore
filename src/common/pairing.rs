//! 请求与应答的配对（`request_id`）—— **给定请求号，把它的意图与结果成对取回**。
//!
//! ## 它补的是哪一格（这本书里逐字怎么写）
//!
//! 书 §4.6 逐字：「请求与结果的配对靠两处对齐：同一个请求编号，以及"因为哪一条"那一格
//! 指回提出这件事的那条记录。两处都在账本上，配对因此可以在事后核对，
//! 不必依赖当时在场的谁记得。」
//!
//! 书 §4.5 逐字：「请求进来，过闸，执行，然后把结果写成一条记录落账。结果本身也是记录，
//! 这一条在三个家族里已经定好：一件事被请求之后成没成，要写下来。
//! **结果只交回给请求方而没有落账的情形，事后无从查起。**」
//!
//! ⇒ 配对是**账本的事后核对**，不是"当时谁记得"：两边都得在账本里，且两处对齐都要可核。
//!
//! ## 两处对齐各自怎么读（口径逐条可判）
//!
//! | 对齐处 | 落在哪 | 本模块怎么读 |
//! |---|---|---|
//! | 同一个请求编号 | `body.request_id`（`act` 信纸**必填**，`ontology.json:33`） | [`request_id_of`]：`act` 家族的信纸字段，空串视为未给 |
//! | "因为哪一条" | 信封的 `trace`（`ontology.json:19`：因果：引发本条的那条事件的 `id`） | [`Pair::trace_agrees`]：`trace` 缺省 = 无从判（**不算不一致**，`REQ-F-031` 的 v1 口径不校验引用完整性）；写了就必须**逐字等于**意图的 `id` |
//!
//! ## 谁算"意图"、谁算"结果"
//!
//! 判据是**机械的**：`act` 信纸的 `params.result` —— 带它的那条是结果，不带的才是意图
//! （三态取值见 [`RESULTS`]，与载体适配器写结果时的口径同源）。
//!
//! ⚠️ 这一条判据本模块与孤儿请求恢复（[`crate::carrier::recover`]）**共用同一份实现**：
//! 从前它写在 `recover.rs` 里，于是"什么算结果"在项目里有两个说法；现在只有一个。
//!
//! ## 今天还没做的（登记，不假装已成立）
//!
//! - **不去重**：同一个 `request_id` 出现两条意图（或两条结果）**不报错**——
//!   它是账本里的事实，本模块如实把两条都列进 [`Pair`]，由调用方自己处置；
//!   "按请求号去重"属幂等键语义（`WC-IC-001` `IF-D-05`：调用方的责任），**本条不做**；
//! - **引用完整性不校验**：`trace` 指向一个不在账本里的 `id` 不导致拒绝
//!   （`REQ-F-031` 的 v1 口径）。因此"结果指向了别处的意图"只能靠
//!   [`Pair::trace_agrees`] 判**不一致**，不能靠它判"世界坏了"。

use serde_json::Value;

/// `act` 结果的 `params.result` 三态取值（与载体适配器写结果时同源）。
pub const RESULTS: [&str; 3] = ["ok", "failed", "refused"];

/// 一条 `act` 声明的请求号。
///
/// `act` 信纸的 `request_id` 是**必填**（`ontology.json:33`），但本函数仍把
/// "缺字段 / 非字符串 / 空串"一并按**未给**处理：读侧不该因为一条读不出请求号的记录
/// 而把整本账判成坏账——那件事由本体校验在写入侧负责报。
pub fn request_id_of(ev: &Value) -> Option<&str> {
    ev.get("body")
        .and_then(|b| b.get("request_id"))
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
}

/// 这条事件是不是一次 `act`（`act` 家族之外的信纸没有请求号，不参与配对）。
pub fn is_act(ev: &Value) -> bool {
    ev.get("kind").and_then(Value::as_str) == Some("act")
}

/// 这条 `act` 是不是**结果**（而不是**意图**）。
///
/// 判据唯一且机械：结果的信纸里**带 `params.result` 这个键**。
/// - 取值 ∈ [`RESULTS`] ⇒ 结果；
/// - **带了这个键、取值读不出来（不是字符串）⇒ 仍算结果**——这一条是关键：
///   把它算成"意图"会让一条写坏了的请求**换个样子藏起来**（从"结果写坏了"变成"有意图、无结果"），
///   而 `params.result: 7` 恰恰是"结果写坏了"的证据，不该被藏；
/// - 没有这个键 ⇒ 意图。
///
/// **只看这个键在不在，不猜别的**——猜"看起来像结果"才会掩盖事实。
///
/// ⚠️ **与旧实现在这一格上不同**（旧实现是
/// `and_then(Value::as_str).map(|r| r == "ok" || …).unwrap_or(false)`：取值读不出来时算**意图**；
/// `params.result` = `7`／`null`／`{}` 三种形态实测：旧 false、新 true；
/// 同一账本经 `carrier::recover::orphans` 判出的孤儿数 2 vs 1）。
/// ⇒ **这一格有两层守卫**：本模块的 `a_broken_result_value_is_still_a_result` 直接钉住 `is_result` 本身；
/// 另一层在**真正消费它的那条路径**上——`scripts/test/write_side.rs` 与
/// `src/carrier/recover.rs` 的 `a_result_whose_value_is_unreadable_still_closes_the_pair`。
/// 本节文档与实现对同一件事的说法必须一致（原来写的是"且取值 ∈ RESULTS"，与代码矛盾）。
pub fn is_result(ev: &Value) -> bool {
    match result_tag(ev) {
        ResultTag::Named(r) => RESULTS.contains(&r),
        ResultTag::Absent => false,
        // 带 `params.result` 但不认得 ⇒ 它是**结果**（带了这个键），只是取值不认识。
        ResultTag::Unreadable => true,
    }
}

/// 「结果」这个键在不在、取值读不读得出来（[`is_result`] 的中间形态）。
enum ResultTag<'a> {
    /// 没有 `params.result` 键 ⇒ 这条不是结果。
    Absent,
    /// 有 `params.result`，且是字符串。
    Named(&'a str),
    /// 有 `params.result`，但不是可读的字符串（形态问题）。
    Unreadable,
}

fn result_tag(ev: &Value) -> ResultTag<'_> {
    match ev
        .get("body")
        .and_then(|b| b.get("params"))
        .and_then(|p| p.get("result"))
    {
        None => ResultTag::Absent,
        Some(Value::String(s)) => ResultTag::Named(s),
        Some(_) => ResultTag::Unreadable,
    }
}

/// **配对的原判据**：两条事件是不是同一个请求的两半（请求号逐字相等）。
///
/// ⚠️ 它只说"同一个请求"，不说"一条是意图、一条是结果"——那是 [`is_result`] 的事。
/// 两条**都是**意图（或都是结果）时本条照样为真：本模块不替账本掩盖这种事。
pub fn same_request(a: &Value, b: &Value) -> bool {
    match (request_id_of(a), request_id_of(b)) {
        (Some(x), Some(y)) => x == y,
        _ => false,
    }
}

/// 一个请求号的**登记项**：意图与结果各自成列（多出一条也不掩盖）。
#[derive(Debug, Clone, PartialEq)]
pub struct Pair {
    /// 请求号（两半共用的配对键）。
    pub request_id: String,
    /// 带这个请求号的**意图**事件（`act`，不带 `params.result`），按账本序。
    pub intents: Vec<Value>,
    /// 带这个请求号的**结果**事件（`act`，带 `params.result`），按账本序。
    pub results: Vec<Value>,
}

impl Pair {
    /// 结果里 `trace` 逐字指向最后一条意图的 `id`（缺省 `trace` = 无从判，返回 `None`）。
    ///
    /// 为什么以**最后一条**意图为准：同一个请求号出现两条意图本身就是异常，
    /// 这里取"最近的那条请求"来判"结果在回答哪一次"——第一次意图是否被回答，
    /// 由调用方看 [`Pair::intents`] 自己判，本函数不替它下结论。
    pub fn trace_agrees(&self) -> Option<bool> {
        let (intent, result) = (self.intents.last()?, self.results.first()?);
        // 缺省 trace：**无从判**（不是"不一致"）——`REQ-F-031` 的 v1 口径。
        result
            .get("trace")
            .and_then(Value::as_str)
            .map(|t| Some(t) == intent.get("id").and_then(Value::as_str))
    }

    /// 两半齐全（至少一条意图、至少一条结果）。
    pub fn is_complete(&self) -> bool {
        !self.intents.is_empty() && !self.results.is_empty()
    }

    /// 缺结果（有意图、无结果）——即"上次那个活干到哪儿了"的回答面。
    pub fn is_orphan(&self) -> bool {
        !self.intents.is_empty() && self.results.is_empty()
    }
}

/// `request_id` 在账本里的**全部**配对登记（按请求号有序 ⇒ 同输入必得同输出）。
///
/// 只收 `act` 家族：`change` / `notice` **没有**配对字段（`WC-IC-001` §2.6 的口径），
/// 它们信纸里就算出现同名的键也不参与配对。
pub fn pairs(events: &[Value]) -> Vec<Pair> {
    let mut intents: std::collections::BTreeMap<String, Vec<Value>> =
        std::collections::BTreeMap::new();
    let mut results: std::collections::BTreeMap<String, Vec<Value>> =
        std::collections::BTreeMap::new();
    for ev in events {
        if !is_act(ev) {
            continue;
        }
        let Some(rid) = request_id_of(ev) else {
            continue;
        };
        if is_result(ev) {
            results.entry(rid.to_string()).or_default().push(ev.clone());
        } else {
            intents.entry(rid.to_string()).or_default().push(ev.clone());
        }
    }

    // 键集合 = 两类之和（只出现过结果的请求号也要在册：那是"结果没有请求"这件事实）。
    let mut ids: std::collections::BTreeSet<String> = intents.keys().cloned().collect();
    ids.extend(results.keys().cloned());

    ids.into_iter()
        .map(|rid| Pair {
            intents: intents.remove(&rid).unwrap_or_default(),
            results: results.remove(&rid).unwrap_or_default(),
            request_id: rid,
        })
        .collect()
}

/// **给定请求号，取回它的两半**（`REQ-F-023` 的"应答能追回它的请求"）。
///
/// 四种形态各自可判，**不合并成一句"查到了/没查到"**——
/// 因为它们要处置的事完全不同：没来过 / 还在办 / 因果错 / 齐了。
#[derive(Debug, Clone, PartialEq)]
pub enum Outcome {
    /// 账本里没有这个请求号：这件事**从未出现过**。
    Untraced,
    /// 有意图、**无结果**（含"有意图但 `request_id` 缺失"这条不在此列——那条根本进不来）：
    /// 请求还在办，或结果没落账（书 §4.5：结果只交回给请求方而没落账的情形，事后无从查起）。
    Unpaired {
        /// 最后一条意图事件。
        intent: Value,
        /// 这个请求号下意图的**全部**条数（>1 即异常，由调用方处置）。
        intent_count: usize,
    },
    /// 有结果、**无意图**：结果指向一个账本里没有的请求。
    Unrequested {
        /// 第一条结果事件。
        result: Value,
    },
    /// 两半齐全，但结果的 `trace` **不等于**意图的 `id`：
    /// "同一个请求编号"对上了，"因为哪一条"没对上 ⇒ 两处对齐只成立一处。
    Mistraced {
        /// 最后一条意图事件。
        intent: Value,
        /// 第一条结果事件。
        result: Value,
    },
    /// 两半齐全且 `trace` 指回意图（**含缺省 `trace`**：缺省 = 无从判，按成立处理，见 `REQ-F-031`）。
    Complete(Pair),
}

/// 给定请求号，从一串事件里取回两半。
pub fn find_pair(events: &[Value], request_id: &str) -> Outcome {
    let mut intents: Vec<&Value> = Vec::new();
    let mut results: Vec<&Value> = Vec::new();
    for ev in events {
        if !is_act(ev) || request_id_of(ev) != Some(request_id) {
            continue;
        }
        if is_result(ev) {
            results.push(ev);
        } else {
            intents.push(ev);
        }
    }

    if let (Some(intent), Some(result)) = (intents.last(), results.first()) {
        return match result.get("trace").and_then(Value::as_str) {
            Some(t) if Some(t) != intent.get("id").and_then(Value::as_str) => Outcome::Mistraced {
                intent: (*intent).clone(),
                result: (*result).clone(),
            },
            _ => Outcome::Complete(Pair {
                request_id: request_id.to_string(),
                intents: intents.into_iter().cloned().collect(),
                results: results.into_iter().cloned().collect(),
            }),
        };
    }

    // 剩下的三种形态**逐个点名**，不合并成一句"没查到"：
    // 它们要处置的事完全不同（没来过 / 还在办 / 结果没有请求）。
    match (intents.last(), results.first()) {
        (Some(i), None) => Outcome::Unpaired {
            intent: (*i).clone(),
            intent_count: intents.len(),
        },
        (None, Some(r)) => Outcome::Unrequested {
            result: (*r).clone(),
        },
        _ => Outcome::Untraced,
    }
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    fn intent(id: &str, rid: &str) -> Value {
        json!({"kind":"act","id":id,"seq":1,
               "body":{"capability":"package.install","verb":"install","request_id":rid}})
    }

    fn result(id: &str, rid: &str, trace: Option<&str>) -> Value {
        let mut v = json!({"kind":"act","id":id,"seq":2,
               "body":{"capability":"package.install","verb":"install","request_id":rid,
                       "params":{"result":"ok"}}});
        if let Some(t) = trace {
            v["trace"] = json!(t);
        }
        v
    }

    #[test]
    fn a_name_and_its_answer_pair_up() {
        let evs = vec![intent("e-1", "r-1"), result("e-2", "r-1", Some("e-1"))];
        match find_pair(&evs, "r-1") {
            Outcome::Complete(p) => {
                assert_eq!(p.intents.len(), 1);
                assert_eq!(p.results.len(), 1);
                assert_eq!(p.trace_agrees(), Some(true));
                assert!(p.is_complete() && !p.is_orphan());
            }
            other => panic!("应当成对，实得 {other:?}"),
        }
    }

    #[test]
    fn an_answer_pointing_elsewhere_is_not_a_complete_pair() {
        let evs = vec![intent("e-1", "r-1"), result("e-2", "r-1", Some("e-999"))];
        assert!(matches!(find_pair(&evs, "r-1"), Outcome::Mistraced { .. }));
    }

    #[test]
    fn no_trace_is_undecidable_not_disagreement() {
        let evs = vec![intent("e-1", "r-1"), result("e-2", "r-1", None)];
        match find_pair(&evs, "r-1") {
            Outcome::Complete(p) => assert_eq!(p.trace_agrees(), None),
            other => panic!("缺省 trace 不应使配对失败，实得 {other:?}"),
        }
    }

    #[test]
    fn the_three_incomplete_shapes_are_told_apart() {
        assert_eq!(find_pair(&[], "r-x"), Outcome::Untraced);
        assert!(matches!(
            find_pair(&[intent("e-1", "r-1")], "r-1"),
            Outcome::Unpaired { .. }
        ));
        assert!(matches!(
            find_pair(&[result("e-2", "r-1", None)], "r-1"),
            Outcome::Unrequested { .. }
        ));
    }

    #[test]
    fn other_families_do_not_participate() {
        let noise = json!({"kind":"notice","id":"e-9","seq":1,
                           "body":{"type":"t","subject":"s","payload":{"request_id":"r-1"}}});
        let one = std::slice::from_ref(&noise);
        assert_eq!(find_pair(one, "r-1"), Outcome::Untraced);
        assert!(pairs(one).is_empty());
        assert!(!same_request(&noise, &intent("e-1", "r-1")));
    }

    #[test]
    fn a_broken_result_value_is_still_a_result() {
        // 带 `params.result` 但取值不认识 ⇒ 它是结果（不能被算成第二条意图：
        // 那会把"有意图、无结果"这件事实掩盖掉）
        let weird = json!({"kind":"act","id":"e-2","seq":2,
                           "body":{"capability":"c","verb":"v","request_id":"r-1",
                                   "params":{"result":7}}});
        assert!(is_result(&weird));
        assert!(matches!(
            find_pair(&[intent("e-1", "r-1"), weird], "r-1"),
            Outcome::Complete(_)
        ));
    }

    #[test]
    fn two_intents_are_listed_not_hidden() {
        let evs = vec![intent("e-1", "r-1"), intent("e-2", "r-1")];
        assert_eq!(pairs(&evs)[0].intents.len(), 2);
        assert!(matches!(
            find_pair(&evs, "r-1"),
            Outcome::Unpaired {
                intent_count: 2,
                ..
            }
        ));
    }
}
