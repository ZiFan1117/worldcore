//! 投递（`to`）—— **一条记录给谁**：带 `to` 只送该收件人，无 `to`（或 `to` 为空）= 广播。
//!
//! ## 它补的是哪一格（这本书里逐字怎么写）
//!
//! 书 §4.6 逐字：「另一半是提醒。每条记录的信封里有一个"给谁"的格子，写明这条消息是给谁的；
//! 格子空着表示广播。谁该知道一件事，就把这件事提醒给谁。」
//!
//! 本体（`ontology.json:18`）逐字：`"to": "string  # 目的地；空 = 广播"`。
//! 规格（`ninedim/06-变更/cover-unimplemented-capabilities/specs/delivery-and-resources/spec.md:11`）
//! 逐字：「事件 SHALL 支持指定收件人：带 `to` 时只送该收件人，不带 `to` 时按广播处理」。
//!
//! ## 为什么这是一层**读侧派生**，而不是账本或折叠的一个开关
//!
//! 书 §4.6 把"送到"分三层，第一层逐字：「第一层，落笔即发布。记录一落账就可以被读，
//! 读的人不必等谁来通知他。这一层保证的是，只要有人读，内容就在那里。」
//!
//! 于是：
//!
//! - **账本不因投递而少一条**——收件人是"提醒"去往何处，不是"这条记录算不算存在"。
//!   按收件人过滤账本，等于让"没人被提醒"变成"这件事没发生过"；
//! - **折叠结果不因投递而变**——`state = fold(账本)`（[`crate::ontology_instance::readmodel`]）。收件人若参与折叠，
//!   同一个世界就会折出两份状态，"一份说法"当场破掉（书 §4.1「防两本账」）。
//!
//! 所以本模块**只有纯函数**：不给 [`crate::World`] 加字段、不写盘、不持有游标。
//! 「我读到第几条」是**收件人自己**记着的数（书 §4.6 第二层），本模块给的是
//! [`outbox`]——按收件人过滤后的那一串事件；两半的分工因此与书同形。
//!
//! ## 与"同一条记录送两次"的分工
//!
//! 书 §4.6 第三层是"重传不重复"，其判据是记录自身的身份（`id`）。
//! 本模块**不**做去重、也**不**声称做了：`outbox` 是账本的**保序子序列**——
//! 一条广播在它里面出现一次，因为它在账本里本来就只有一条。
//!
//! ## 今天还没做的（登记，不假装已成立）
//!
//! - **没有收件人名单**：`to` 不做"这个名字存不存在"的校验。写一个不存在的收件人
//!   **不算错**（书 §4.6 只说"写给谁"，没有说"必须是在册的谁"）；因此"超范围收件人
//!   的拒绝形态"（`WC-SRS-001` §五 `TC-043` 行）**今天仍无标的物**；
//! - **没有跨进程投递出口**：CLI（`src/main.rs`）七个命令都不读 `to`
//!   （`append` 的入口是 [`crate::World::commit`]，它不带 `to`）；
//!   经公开 API 可指定 `to` 的入口只有 [`crate::World::commit_requested`]。
//!   跨进程面的落点是通道（`REQ-F-026`，本 change tasks 第 2 组），不在本条内。

use serde_json::Value;

/// 一条事件声明的收件人。
///
/// 口径（三值，各自可判）：
/// - **没有 `to` 键** ⇒ `None`（广播）；
/// - **`to` 是空串** ⇒ `None`（广播）——本体逐字「空 = 广播」，
///   于是"空"与"没写"在这里**必须**同义，否则同一句话会有两种读法；
/// - **`to` 是非空字符串** ⇒ `Some(收件人)`；
/// - **`to` 存在但值不是字符串**（如 `null`）⇒ `None`，即按广播处理：
///   本函数**不报错**（形态问题由本体校验负责报，见 [`crate::ontology_definition::Ontology::validate`]），
///   而绝不把一条读不出收件人的记录**悄悄丢给某一个人**。
pub fn recipient_of(ev: &Value) -> Option<&str> {
    ev.get("to")
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
}

/// 这条事件是不是**送给每一个收件人**的（即"格子空着"）。
///
/// 它只是 [`recipient_of`] 为 `None` 的另一种说法，独立成型是为了让
/// "广播"这件事在调用点**读得出来**，而不必让读者自己把 `None` 再解一遍。
pub fn broadcast(ev: &Value) -> bool {
    recipient_of(ev).is_none()
}

/// **投递判据**：这条事件是否落到 `recipient` 这个出口上。
///
/// 判据只有两句话（与书 §4.6、本体 `to` 的记法逐字同形）：
///
/// 1. 没有收件人（`to` 缺省或为空）⇒ **广播** ⇒ 谁都收到；
/// 2. 有收件人 ⇒ **只送那一个**，`recipient` 与它逐字相等才收到。
///
/// ⚠️ 逐字相等，不做前缀/大小写/通配的近似——与门禁里主体名比对的同一条口径
/// （`policy.json` 的 `world://agent/*` 那种前缀匹配是**授权表**的事，不是投递的事）。
pub fn delivered_to(ev: &Value, recipient: &str) -> bool {
    match recipient_of(ev) {
        None => true,
        Some(r) => r == recipient,
    }
}

/// `recipient` 这个出口上收到的**全部**事件（按账本原序）。
///
/// 它是账本的一个**保序子序列**：不过滤、不改写、不新增、不重排、不去重，
/// 也不丢字段——收件人拿到的就是账本里的那一条本身。
pub fn outbox(events: &[Value], recipient: &str) -> Vec<Value> {
    events
        .iter()
        .filter(|ev| delivered_to(ev, recipient))
        .cloned()
        .collect()
}

/// 账本里出现过的收件人（**有序、去重**）。
///
/// 用途：它给出"有出口的收件人"这个可枚举集合，让"两份读法各不相同"这件事
/// 能被机械核（而不是靠人挑两个人名去试）。广播不计入——广播不属于任何一个收件人。
pub fn recipients(events: &[Value]) -> Vec<String> {
    let mut out: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for ev in events {
        if let Some(r) = recipient_of(ev) {
            out.insert(r.to_string());
        }
    }
    out.into_iter().collect()
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    fn ev(id: &str, to: Option<&str>) -> Value {
        let mut m = serde_json::Map::new();
        m.insert("id".to_string(), json!(id));
        if let Some(t) = to {
            m.insert("to".to_string(), json!(t));
        }
        Value::Object(m)
    }

    #[test]
    fn absent_and_empty_are_both_broadcast() {
        assert_eq!(recipient_of(&ev("e-1", None)), None);
        assert_eq!(recipient_of(&ev("e-2", Some(""))), None);
        assert!(broadcast(&ev("e-3", Some(""))));
        assert!(!broadcast(&ev("e-4", Some("world://agent/1"))));
    }

    #[test]
    fn a_named_recipient_gets_only_its_own() {
        let e = ev("e-1", Some("world://agent/1"));
        assert!(delivered_to(&e, "world://agent/1"));
        assert!(!delivered_to(&e, "world://agent/2"));
    }

    #[test]
    fn outbox_keeps_ledger_order_and_the_event_itself() {
        let evs = vec![
            ev("e-1", Some("world://agent/1")),
            ev("e-2", None),
            ev("e-3", Some("world://agent/2")),
        ];
        let box1 = outbox(&evs, "world://agent/1");
        assert_eq!(box1.len(), 2);
        assert_eq!(box1[0]["id"], json!("e-1"));
        assert_eq!(box1[1]["id"], json!("e-2"));
        // 收件人拿到的就是账本里的那一条本身（不是摘要、不是副本形态）
        assert_eq!(box1[0], evs[0]);
        assert_eq!(recipients(&evs), vec!["world://agent/1", "world://agent/2"]);
    }
}
