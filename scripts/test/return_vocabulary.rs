//! **回来方向的对账** —— 一条**会红**的判据：**执行者写进世界的通告，世界侧读得懂吗**。
//!
//! 规格落点：《规程-转换》§0 与 §6.1／§6.2／§6.3（架构夹 `语义世界-架构-退役-2026-10-06\规程-转换.md`）。
//! 判据一句话：**凡账本里出现过的、去掉内核保留前缀（`gate.`）之后剩下的每一种通告类型，
//! 世界侧必须有一处"认它"的读法**；认不得 ⇒ 红。
//!
//! ## 这条判据治的现取读数（四坐标）
//!
//! | 坐标 | 值 |
//! |---|---|
//! | 哪棵树 | VM 活账本 `/var/lib/world-core/ledger.jsonl`（**不是仓内树**；仓内没有账本） |
//! | 什么口径 | 按 `notice.body.type` 去重计数；世界侧读法口径 ＝ [`NOTICE_TYPE`] 与 `Completion::from_event` |
//! | 什么时点 | VM 钟 `2026-10-04T18:19:56Z` |
//! | 什么命令 | 脚本 → `scp` → `sh`；`PYTHONIOENCODING=utf-8 /usr/bin/python3 <scratch>/probe_return.py`（只读账本；脚本已按"临时件用完即清"清掉） |
//!
//! 那次读数：账本 403 条事件／0 坏行；`notice.type` 实有 `job.finished`（**执行者写的**）
//! 与 `gate.rejected`／`gate.awaiting-approval`（**内核自己写的**）；
//! 而世界侧唯一读法只认 `job.completed` ⇒ **可折叠 0 条、读不懂 1 条**。
//!
//! ## 这条判据为什么落 `tests/` 而**不**落 `src/carrier/**`
//!
//! `src/carrier/**` 里 `use crate::agent::completion` 会**新增一条模块边**，而 `WC-ATOM-001` §二 A-4
//! 要求 `deps == import` 且图**无环**（`scripts/verify/module_graph.py` 判）⇒ 一旦 `agent` 反过来 import
//! `carrier`，当场成环。放 `tests/`（L3 集成测试）**不产生模块边**，而 `check.sh` 第 ④ 步跑的
//! `cargo test --locked` 会**自动把它带进闸** ⇒ 既"会红"，又不碰原子化那张图。
//! （"判据放哪"不是风格问题，是**它会挪动哪张表**的问题。）
//!
//! ## 每条断言"改坏什么 ⇒ 红"
//!
//! | 断言 | 改坏什么 ⇒ 红 |
//! |---|---|
//! | `rv01` | 执行者写的那套信纸**哪天被世界侧认了**（`NOTICE_TYPE` 改成 `job.finished`，或执行者改写成 `job.completed`）⇒ **红**：逼改动的人**同时更新那条登记**（不许缺陷悄悄消失、也不许登记悄悄过期） |
//! | `rv02` | 把 `NOTICE_TYPE` 改掉 ⇒ **红**（**正控**：内核自己那套信纸必须读得回来） |
//! | `rv03` | 把 `gate.` 保留前缀的豁免去掉 ⇒ **红**（**正控**：内核自己的通告不许被判成"回来读不懂"） |
//! | `rv04` | 把判据短路成"恒认" ⇒ **红**（证 `rv01` 的红来自判据本身，不是外壳崩出来的） |
//!
//! ## 本件**不能证明**的事（如实声明，不许读成"已覆盖"）
//!
//! 1. 它**不能**证明"执行者今天在 VM 上写的还是 `job.finished`" —— 执行者的源码**不在仓内**
//!    （见《规程-转换》§6.8），仓里拿不到它。本件把**那一刻现取的那一格**钉成夹具；
//!    **执行者若改了字面量，夹具就过期了，而本件不会因此变红**（只有真值变绿才变红）。
//! 2. ⇒ 要判"执行者现在写的是什么"，**只能到 VM 上取现取读数**（《规程-转换》§3 第 ⑦ 条）。
//! 3. 它**不判** `_` 前缀键 —— 那些键不进身份，本件**不假装扫过**（见《规程-转换》§4 落法 5）。

use serde_json::{json, Value};
use world_core::agent::completion::{Completion, NOTICE_TYPE};

/// **世界侧认的通告类型** —— ★ 从**唯一权威载体**现取，**不在本文件里再抄一份**
/// （抄一份就是第二份事实：读法一改，夹具与读法会各说各话）。
fn world_accepts(t: &str) -> bool {
    t == NOTICE_TYPE
}

/// **内核保留前缀** —— 内核自己写的通告**不在标的内**（拿它判红就是假红）。
fn kernel_reserved(t: &str) -> bool {
    t.starts_with("gate.")
}

/// 判据本体：把**世界侧读不懂的通告类型**挑出来（空 = 绿）。
///
/// `skip_reserved = false` 用来做**正控的反面**：证明那条豁免是**承重的**，不是摆设。
fn unreadable(events: &[Value], skip_reserved: bool) -> Vec<String> {
    let mut bad = Vec::new();
    for e in events {
        if e.get("kind").and_then(Value::as_str) != Some("notice") {
            continue;
        }
        let ty = match e
            .get("body")
            .and_then(|b| b.get("type"))
            .and_then(Value::as_str)
        {
            Some(t) => t,
            None => continue,
        };
        if skip_reserved && kernel_reserved(ty) {
            continue;
        }
        if !world_accepts(ty) {
            bad.push(ty.to_string());
        }
    }
    bad.sort();
    bad.dedup();
    bad
}

/// **执行者写的那套信纸** —— 逐字取现取读数（VM 活账本 `seq=368`）。
///
/// ★ 只抄**判据用得到的那两层**（`kind`／`body`）＋ 现取到的 `seq`／`type`／`subject`／`payload`；
/// `id`／`at`／`actor`／`flags` **本席没有现取到 ⇒ 不编**（本判据用不到它们，
/// 而编一个值进夹具，就是往"事实"里掺没人说过的东西）。
fn executor_bell() -> Value {
    json!({
        "kind": "notice",
        "seq": 368,
        "body": {
            "type": "job.finished",
            "subject": "world://job/world-do-2003097-1791095280",
            "payload": {
                "request_id": "world-do-2003097-1791095280",
                "intent": "list",
                "job": "world://job/world-do-2003097-1791095280",
                "executor": "world://presence/actd",
                "outcome": "ok",
                "text": "作业 world://job/world-do-2003097-1791095280 已完成 —— 列目录，共 1517 项"
            }
        }
    })
}

/// 一条**内核自己写的**通告（保留前缀那一族）。形状取现取读数（VM 活账本 `seq=305`）。
fn gate_bell() -> Value {
    json!({
        "kind": "notice",
        "seq": 305,
        "body": {
            "type": "gate.awaiting-approval",
            "subject": "world://core",
            "payload": { "capability": "ledger.compact", "verb": "install" }
        }
    })
}

/// `rv01` —— ★ **「能出去的，必须能回来」在回来那一半今天是断的**：执行者的完工铃，世界侧读不懂。
///
/// 这条断言**今天绿**（它断言的就是"断着"这件事这一格）；**哪天世界侧认了它 ⇒ 红** ⇒
/// 逼改动的人**同时更新那条登记**（缺陷不许悄悄消失，登记也不许悄悄过期）。
#[test]
fn rv01_the_executors_bell_is_not_understood_by_the_world() {
    let bell = executor_bell();

    // ① 世界侧**自己的读法**说读不懂（用真读法，不在本文件另写一个判据去替它说话）
    assert_eq!(
        Completion::from_event(&bell),
        None,
        "世界侧读法认了执行者的完工铃 ⇒ 请更新《规程-转换》§6.1／§6.2／§6.3 的登记，\
         并把本断言改成'必须认'的正控（不许让登记与实现各说各话）"
    );

    // ② 对账面也说读不懂，且**报得出是哪一个类型**（不是一句"有问题"）
    assert_eq!(
        unreadable(&[bell], true),
        vec!["job.finished".to_string()],
        "执行者写的那个类型必须被点名"
    );

    // ③ 两边确实不是同一个名字 —— 而这**不是拼写错**：真实违规的形态是"两套词表撞车"
    assert_ne!(
        NOTICE_TYPE, "job.finished",
        "两套词表撞车了：世界侧读法与执行者写侧各有一个合法名字"
    );
}

/// `rv02` —— **正控**：内核自己那套信纸，世界侧**必须**读得回来。
#[test]
fn rv02_the_worlds_own_bell_is_understood() {
    let ev = Completion::from_wait("j-1", Some(0)).to_event(7, "world://agent/1");

    assert_eq!(
        ev.get("body")
            .and_then(|b| b.get("type"))
            .and_then(Value::as_str),
        Some(NOTICE_TYPE),
        "内核自己写的类型必须就是世界侧认的那一个"
    );
    assert!(
        Completion::from_event(&ev).is_some(),
        "内核自己那套信纸必须读得回来（否则本条判据把'正控'也判红了 = 假红）"
    );
    assert!(unreadable(&[ev], true).is_empty());
}

/// `rv03` —— **正控 ＋ 承重证明**：`gate.` 保留前缀的豁免**必须承重**。
#[test]
fn rv03_the_kernel_prefix_exemption_carries_weight() {
    let g = gate_bell();

    // 正控：内核自己的通告**不许**被判成"回来读不懂"
    assert!(
        unreadable(std::slice::from_ref(&g), true).is_empty(),
        "内核自己写的通告被当成违规 ⇒ 假红"
    );

    // ★ 承重证明：**把豁免去掉**，同一条事件**当场会被判出** ⇒ 那条豁免不是装饰
    assert_eq!(
        unreadable(&[g], false),
        vec!["gate.awaiting-approval".to_string()],
        "去掉保留前缀豁免后仍然是空 ⇒ 那条豁免是装饰（它不承重）"
    );
}

/// `rv04` 的**短路版**判据：把"世界侧认什么"换成执行者自己写的那个名字 ⇒ 恒绿。
///
/// ★ 它**只**用来证 `rv01` 第一半的红不是外壳崩出来的（**短路验红**），**不是**第二份判据。
fn short_circuited(events: &[Value]) -> Vec<String> {
    let mut bad = Vec::new();
    for e in events {
        let ty = e
            .get("body")
            .and_then(|b| b.get("type"))
            .and_then(Value::as_str)
            .unwrap_or("");
        if !kernel_reserved(ty) && ty != "job.finished" {
            bad.push(ty.to_string());
        }
    }
    bad
}

/// `rv04` —— **短路验红**：把判据本身短路掉，`rv01` 的那条读数**必须跟着变**。
///
/// 短路版把"世界侧认什么"直接换成执行者写的那个名字（等于**把判据改写成恒绿**）⇒
/// 执行者的铃**当场变成绿** ⇒ 证 `rv01` 的红/绿确实是判据算出来的，不是外壳崩出来的。
#[test]
fn rv04_gutting_the_criterion_moves_the_verdict() {
    let bell = executor_bell();

    // 真判据：读不懂，且点名
    assert_eq!(
        unreadable(std::slice::from_ref(&bell), true),
        vec!["job.finished".to_string()]
    );

    assert!(
        short_circuited(&[bell]).is_empty(),
        "短路之后反例仍然被判出 ⇒ 上面那条读数不成立（红不是判据算出来的）"
    );
}
