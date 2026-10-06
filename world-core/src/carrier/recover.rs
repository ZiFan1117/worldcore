//! 孤儿请求恢复 —— **"上次那个活干到哪儿了"必须能回答**。
//!
//! ## 它回答的问题
//!
//! 跨进程的"请求—结果"是两段：意图先落账本，结果后落账本。若适配器在**中间**崩了
//! （执行完了没来得及回写、或执行到一半），账本里就会留下**有意图、无结果**的请求。
//!
//! **这不是缺陷，这是诚实**：世界如实显示"有一条请求没有结果"，
//! 而不是补写一条假的成功。这里要做的只是**把这件事查出来并说清楚**。
//!
//! ## 为什么不需要一本"登记簿"
//!
//! 旧实现在载体侧自己维护一本完工铃登记簿（落盘、重启后标记"丢了"）。
//! 现在**那本登记簿是多余的**：登记簿要回答的"哪些活还没干完"，
//! 由**账本折叠**回答——一条有意图、无结果的请求就是"还没干完"。
//! 这样"待办清单"不会成为第二份真相。
//!
//! ## 恢复口径（刻意保守）
//!
//! 对孤儿请求**只报告、不重试**。理由：重放一个有副作用的动作，必须由**人**判断
//! （那条请求到底做没做、做到哪一步），而不是由一个自动程序猜。
//! 本模块给出的 `hint` 只说明"需要人工判断"，**不构成"可以安全重试"的结论**。

use crate::common::pairing::is_result;
use serde_json::Value;
use std::path::Path;

/// **独立只读**地读一份账本（不取锁、不截断、不改一个字节）。
///
/// ## 为什么要单独一份读法，而不复用账本模块的打开流程
///
/// 载体适配器**对账本零写权限**，而账本模块的"可写口径"会取单写者锁、
/// 并丢弃残缺末行——那是**写者**该做的事。作为只读消费者，它必须满足两条：
///
/// 1. **不产生任何文件副作用**：只读打开，不取锁、不截断（否则"恢复"动作会改世界）；
/// 2. **坏账本要说清楚**：逐行解析失败即点名第几行，**不静默跳过**——
///    "读不到"与"读到了没问题"是两件事。
///
/// ⚠️ 它**不替代**账本模块的校验（序号连续、摘要链、身份唯一那套属于内核的启动自检）。
/// 它只做一件事：把账本**如实**读成一串事件，供只读分析用。
pub fn read_ledger_readonly(path: &Path) -> Result<Vec<Value>, String> {
    let raw = std::fs::read(path)
        .map_err(|e| format!("ext.world.Carrier.LedgerReadFail: {}：{e}", path.display()))?;
    let mut out = Vec::new();
    for (i, line) in raw.split(|b| *b == b'\n').enumerate() {
        if line.is_empty() {
            continue;
        }
        let v: Value = serde_json::from_slice(line).map_err(|e| {
            format!(
                "ext.world.Carrier.LedgerCorrupt: {} 第 {} 行不是合法 JSON：{e}",
                path.display(),
                i + 1
            )
        })?;
        out.push(v);
    }
    Ok(out)
}

/// 一条孤儿请求。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Orphan {
    /// 请求号（意图与结果本应配对的键）。
    pub request_id: String,
    /// 能力名。
    pub capability: String,
    /// 动词。
    pub verb: String,
    /// 意图事件的 id（结果的因果锚点应当指向它）。
    pub intent_id: String,
    /// 意图事件的序号。
    pub intent_seq: u64,
    /// 意图事件的时间戳（Unix 秒）。
    pub intent_at: u64,
    /// 距今多少秒（以账本末条事件的时间为准，故**可复算**）。
    pub age_secs: u64,
}

impl Orphan {
    /// 给运维看的一句话。（**不给"可以重试"的结论。**）
    pub fn hint(&self) -> String {
        format!(
            "请求 {} （{} {}）有意图、无结果：**不得自动重试**，\
             须人工判断它到底做没做、做到哪一步，再决定补记结果还是记一条放弃",
            self.request_id, self.capability, self.verb
        )
    }
}

/// 事件信纸上的请求号——见 [`crate::common::pairing::request_id_of`]。
///
/// 与 [`is_result`] 同上：这两条"什么算一次请求的哪一半"的判据**全项目只有一份实现**
/// （在 [`crate::common::pairing`] 里），本模块只把它们接到原有的调用点上。
fn request_id_of(ev: &Value) -> Option<&str> {
    crate::common::pairing::request_id_of(ev)
}

fn str_field(ev: &Value, name: &str) -> String {
    ev.get("body")
        .and_then(|b| b.get(name))
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string()
}

/// 从未配对的 `act` 事件里找出"有意图、无结果"的请求。
///
/// 口径（逐条都可复算）：
/// - 只看 `act` 家族；`change`/`notice` 不参与配对；
/// - **配对键 = `request_id`**；同一个 `request_id` 先出现的是意图、带 `params.result` 的是结果；
/// - 只算**没有出现过结果**的意图（出现过即已闭合，无论结果成败）；
/// - `age_secs` 以**账本末条事件的 `at`** 为"现在"，故同一份账本必然算出同一个值——
///   不用墙上时钟，是为了"同样的输入给同样的输出"。
pub fn orphans(events: &[Value]) -> Vec<Orphan> {
    let now = events
        .iter()
        .filter_map(|e| e.get("at").and_then(Value::as_u64))
        .max()
        .unwrap_or(0);

    let mut intents: Vec<Orphan> = Vec::new();
    let mut closed: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();

    for ev in events {
        if ev.get("kind").and_then(Value::as_str) != Some("act") {
            continue;
        }
        let rid = match request_id_of(ev) {
            Some(r) => r.to_string(),
            None => continue,
        };
        if is_result(ev) {
            closed.insert(rid);
            continue;
        }
        let at = ev.get("at").and_then(Value::as_u64).unwrap_or(0);
        intents.push(Orphan {
            request_id: rid,
            capability: str_field(ev, "capability"),
            verb: str_field(ev, "verb"),
            intent_id: ev
                .get("id")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string(),
            intent_seq: ev.get("seq").and_then(Value::as_u64).unwrap_or(0),
            intent_at: at,
            age_secs: now.saturating_sub(at),
        });
    }

    intents.retain(|o| !closed.contains(&o.request_id));
    intents
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    fn intent(id: &str, seq: u64, at: u64, rid: &str) -> Value {
        json!({"world":1,"kind":"act","id":id,"seq":seq,"at":at,"actor":"world://agent/1",
               "flags":[],"body":{"capability":"package.install","verb":"install",
               "request_id":rid,"params":{"package":"ripgrep"}}})
    }
    fn result(id: &str, seq: u64, at: u64, rid: &str, outcome: &str) -> Value {
        json!({"world":1,"kind":"act","id":id,"seq":seq,"at":at,"actor":"world://agent/1",
               "flags":[],"body":{"capability":"package.install","verb":"install",
               "request_id":rid,"params":{"result":outcome,"exit_code":0}}})
    }
    fn change(id: &str, seq: u64, at: u64) -> Value {
        json!({"world":1,"kind":"change","id":id,"seq":seq,"at":at,"actor":"world://user",
               "flags":[],"body":{"subject":"world://x","path":"p","before":null,"after":1}})
    }

    #[test]
    fn a_paired_request_is_not_an_orphan() {
        let evs = vec![
            intent("e-1", 1, 100, "r-1"),
            result("e-2", 2, 101, "r-1", "ok"),
        ];
        assert!(orphans(&evs).is_empty());
    }

    #[test]
    fn a_failed_result_still_closes_the_pair() {
        // 失败也是"有结果"：它不需要善后判断，故不算孤儿
        let evs = vec![
            intent("e-1", 1, 100, "r-1"),
            result("e-2", 2, 105, "r-1", "failed"),
        ];
        assert!(orphans(&evs).is_empty());
    }

    #[test]
    fn a_result_whose_value_is_unreadable_still_closes_the_pair() {
        // ★ 这条是**生产路径上的守卫**，由独立评审席实测指出缺它：
        //   `pairing::is_result` 与旧实现（`and_then(Value::as_str).map(|r| r=="ok"||…).unwrap_or(false)`）
        //   在**这一格**上不同——`params.result` 不是字符串时，旧实现算"意图"、新实现算"结果"。
        //   三种实测形态（`7`／`null`／`{}`）里取一种钉住；本条若红，说明"写坏了的结果"被当成了意图，
        //   于是"有意图、无结果"这个假象会把"结果写坏了"这个**真事实**盖掉 —— 那正是本模块要防的。
        for bad in [json!(7), Value::Null, json!({})] {
            let mut r = result("e-2", 2, 101, "r-1", "ok");
            r["body"]["params"]["result"] = bad.clone();
            let evs = vec![intent("e-1", 1, 100, "r-1"), r];
            assert!(
                orphans(&evs).is_empty(),
                "写坏了的结果（params.result = {bad}）仍应关闭配对，而不是被当成意图"
            );
        }
    }

    #[test]
    fn a_refused_result_also_closes_the_pair() {
        let evs = vec![
            intent("e-1", 1, 100, "r-1"),
            result("e-2", 2, 101, "r-1", "refused"),
        ];
        assert!(orphans(&evs).is_empty());
    }

    #[test]
    fn an_intent_without_a_result_is_an_orphan_with_the_right_facts() {
        let evs = vec![change("e-0", 1, 90), intent("e-1", 2, 100, "r-1")];
        let o = orphans(&evs);
        assert_eq!(o.len(), 1);
        assert_eq!(o[0].request_id, "r-1");
        assert_eq!(o[0].capability, "package.install");
        assert_eq!(o[0].verb, "install");
        assert_eq!(o[0].intent_id, "e-1");
        assert_eq!(o[0].intent_seq, 2);
        // 账本末条 at=100 ⇒ 年龄 0（不用墙上时钟，故可复算）
        assert_eq!(o[0].age_secs, 0);
        assert!(o[0].hint().contains("不得自动重试"));
    }

    #[test]
    fn age_is_measured_against_the_last_event_in_the_ledger() {
        let evs = vec![intent("e-1", 1, 100, "r-1"), change("e-2", 2, 460)];
        let o = orphans(&evs);
        assert_eq!(o[0].age_secs, 360);
    }

    #[test]
    fn only_acts_participate_in_pairing() {
        // 一条 change 带着同样的 request_id 也不参与配对
        let evs = vec![
            json!({"kind":"notice","id":"e-1","seq":1,"at":10,"body":{"type":"t","subject":"s","payload":{"request_id":"r-1"}}}),
            intent("e-2", 2, 20, "r-1"),
        ];
        let o = orphans(&evs);
        assert_eq!(o.len(), 1);
        assert_eq!(o[0].intent_id, "e-2");
    }

    #[test]
    fn acts_without_a_request_id_are_ignored() {
        let evs = vec![json!({"kind":"act","id":"e-1","seq":1,"at":10,
                              "body":{"capability":"c","verb":"v","params":{}}})];
        assert!(orphans(&evs).is_empty());
    }

    #[test]
    fn an_empty_or_non_act_ledger_has_no_orphans() {
        assert!(orphans(&[]).is_empty());
        assert!(orphans(&[change("e-1", 1, 10)]).is_empty());
    }

    #[test]
    fn multiple_orphans_keep_ledger_order() {
        let evs = vec![
            intent("e-1", 1, 10, "r-1"),
            intent("e-2", 2, 20, "r-2"),
            result("e-3", 3, 30, "r-1", "ok"),
        ];
        let o = orphans(&evs);
        assert_eq!(o.len(), 1);
        assert_eq!(o[0].request_id, "r-2");
    }
}
