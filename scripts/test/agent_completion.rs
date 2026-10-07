//! **完工通告（不是登记簿）** —— 会红的断言（原 Go `agentd/internal/job` 的 Rust 侧对应面）。
//!
//! ## 这一件为什么与旧实现不同（**本项目已裁定的口径**）
//!
//! 旧实现自己维护一本**落盘登记簿**（重启后标记"丢了"）。本项目**明确拒绝**它，逐字见
//! `src/carrier/recover.rs` 与 `src/carrier/providers.rs` 的 `Job` 头注：
//! 「登记簿要回答的"哪些活还没干完"，由**账本折叠**回答」。
//! ⇒ 本文件不核"登记簿对不对"（那种东西不该存在），核的是
//! **"待办的答案不依赖任何文件"** 与 **"完工是账本上一条可读回的通告"**。
//!
//! ## 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `j01` | `Completion::notice_body()` 的 `type` 改成别的词（或 `subject` 不带 `world://job/`）⇒ **红**（读不回来） |
//! | `j02` | `Status::from_wait(None)` 改成 `Status::Running` ⇒ **红**（启动失败会被读成"还在跑"，待办永不消） |
//! | `j03` | `pending()` 改成"读一个登记簿文件"来回答 ⇒ **红**（把文件删掉后答案就变了） |
//! | `j04` | `completions_in()` 改成"顺手把事件写回盘"（不再是叶子）⇒ **红**（两次折叠的字节不再相同） |
//!
//! ## 正控（钉住"不该红的"）
//!
//! | 用例 | 它钉什么 |
//! |---|---|
//! | `j03` 的后半段 | **全部完工** ⇒ 待办必须是**空**（否则"待办"会退化成"永远有活没干完"） |
//! | `j01` | 非通告事件（`change`／别人的 `notice`）**不许**被判成完工通告（不猜） |

use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::agent::completion::{completions_in, pending, Completion, Status, NOTICE_TYPE};
use world_core::{common::event, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-agdone-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

fn ontology() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/ontology_definition/ontology.json")
}

fn policy() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json")
}

/// `j01` —— **活儿结束 ⇒ 账本里读得到它的完工通告**。
///
/// 走的是**唯一写入口** `World::commit`（本模块自己**不许**写账本）：
/// 这正是"一个写入口"那条贯穿纪律的落点。
#[test]
fn j01_completion_is_a_ledger_notice() {
    let d = tmpdir("j01");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // 两个活儿：一个正常结束（0），一个非零退出（3）
    let done = Completion::from_wait("j-1", Some(0));
    let failed = Completion::from_wait("j-2", Some(3));
    for c in [&done, &failed] {
        w.commit("notice", "world://agent/1", c.notice_body())
            .unwrap_or_else(|e| panic!("完工通告必须能落笔（{}）：{e}", c.job_id));
    }

    // 读回**账本原文**（不是内存里的对象）：通告真的在账本上
    let raw = fs::read_to_string(&lp).unwrap();
    let events: Vec<Value> = raw
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).expect("账本每行都是合法 JSON"))
        .collect();
    let got = completions_in(&events);

    assert_eq!(got.len(), 2, "两个完工 ⇒ 两条通告；实得 {got:?}");
    assert!(
        got.contains(&done) && got.contains(&failed),
        "两条通告的终态与退出码必须原样读回；实得 {got:?}"
    );

    // 终态与退出码的口径：非零退出 ⇒ failed
    let f = got.iter().find(|c| c.job_id == "j-2").unwrap();
    assert_eq!(f.status, Status::Failed);
    assert_eq!(f.exit_code, 3);
    let o = got.iter().find(|c| c.job_id == "j-1").unwrap();
    assert_eq!(o.status, Status::Done);
    assert_eq!(o.exit_code, 0);

    // 主题与类型是对外口径（读的人按它们取）
    let ev = &events[0];
    assert_eq!(ev.get("kind").and_then(Value::as_str), Some("notice"));
    assert_eq!(
        ev.get("body")
            .and_then(|b| b.get("type"))
            .and_then(Value::as_str),
        Some(NOTICE_TYPE)
    );
    assert_eq!(
        ev.get("body")
            .and_then(|b| b.get("subject"))
            .and_then(Value::as_str),
        Some("world://job/j-1")
    );

    // **正控**：别的家族／别人的通告不许被认成完工通告
    assert_eq!(Completion::from_event(&json!({ "kind": "change" })), None);
    assert_eq!(
        Completion::from_event(&json!({
            "kind": "notice",
            "body": event::notice_body("something.else", "world://job/j-1", json!({}))
        })),
        None,
        "type 不是 job.completed ⇒ 不许当成完工通告（不猜）"
    );

    let _ = fs::remove_dir_all(&d);
}

/// `j02` —— **启动失败也留可读回的事实**（不许只在内存里报告）。
#[test]
fn j02_start_failure_still_leaves_a_notice() {
    let d = tmpdir("j02");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // 启动失败：没能等到退出码 ⇒ None
    let c = Completion::from_wait("j-boom", None);
    assert_eq!(
        c.status,
        Status::Failed,
        "没能跑起来 ⇒ 终态是失败，**不许**读成「还在跑」（那会让待办永远不消）"
    );
    assert_eq!(c.exit_code, -1, "负值表示「没能跑起来」（与旧实现同口径）");

    w.commit("notice", "world://agent/1", c.notice_body())
        .expect("启动失败也必须留下可读回的事实");

    let events: Vec<Value> = fs::read_to_string(&lp)
        .unwrap()
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let got = completions_in(&events);
    assert_eq!(
        got.len(),
        1,
        "账本上必须真有一条（不是只在内存里）：{got:?}"
    );
    assert_eq!(got[0], c);

    let _ = fs::remove_dir_all(&d);
}

/// `j03` —— **待办不靠第二本登记簿**（正控：删掉登记簿，答案不变）。
///
/// 这是本件最要紧的一条：它把"没有第二份真相"变成**可判**的东西。
/// 若哪天有人把 Go 的登记簿带回来、并让 `pending()` 读它，**本用例必红**。
#[test]
fn j03_pending_comes_from_the_ledger_not_a_registry() {
    let d = tmpdir("j03");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    let intents = vec![
        ("j-1".to_string(), "r-1".to_string()),
        ("j-2".to_string(), "r-2".to_string()),
        ("j-3".to_string(), "r-3".to_string()),
    ];

    // 先落一条完工通告（j-1 干完了）
    let c1 = Completion::from_wait("j-1", Some(0));
    w.commit("notice", "world://agent/1", c1.notice_body())
        .unwrap();

    let events: Vec<Value> = fs::read_to_string(&lp)
        .unwrap()
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let completions = completions_in(&events);

    let before = pending(&intents, &completions);
    assert_eq!(
        before,
        vec!["j-2".to_string(), "j-3".to_string()],
        "有意图、没有完工通告 ⇒ 还没干完；实得 {before:?}"
    );

    // ★ 本用例的核心动作：**先放一本"像登记簿"的文件在盘上**，再看答案变不变。
    //
    // 为什么必须先**造出来**（本用例第一版就在这里空了转）：若盘上压根没有那种文件，
    // 那么"把待办改成读那个文件"的实现在**读不到**时会退回空表 ⇒ 答案照旧 ⇒
    // **变异打上去它仍然绿**（本项目实测踩过：第一版 j03 就是这种假绿）。
    // ⇒ 夹具必须让"读它"与"不读它"给出**不同**的答案。
    let fake = d.join("jobs.json");
    let completions_before = completions_in(
        &fs::read_to_string(&lp)
            .unwrap()
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(|l| serde_json::from_str::<Value>(l).unwrap())
            .collect::<Vec<_>>(),
    );
    let before_with_file = pending(&intents, &completions_before);
    assert_eq!(
        before_with_file, before,
        "盘上没有登记簿时，答案只由(意图, 完工通告)决定"
    );

    // 造一本"登记簿"，里面**替 j-2 宣称已完工**
    // ⇒ 任何"读登记簿回答待办"的实现都会把 j-2 从待办里划掉 ⇒ **答案必变** ⇒ 用例红。
    fs::write(&fake, b"j-2").unwrap();
    assert!(fake.exists(), "反例夹具必须真的存在（否则本用例是空转）");

    let after = pending(&intents, &completions);
    assert_eq!(
        after, before,
        "**待办的答案不许依赖任何文件**——它只由(意图, 完工通告)决定。\
         盘上多了一本宣称 j-2 已完工的【登记簿】而答案变了 ⇒ 有人把第二本真相带回来了"
    );

    // 删掉它，答案仍然不变（三个方向都钉住：没有／多了／又没了）
    fs::remove_file(&fake).unwrap();
    assert!(!fake.exists(), "反例夹具必须真的被删掉（防假绿）");
    assert_eq!(
        pending(&intents, &completions),
        before,
        "删掉之后答案还是不变"
    );

    // **正控**：全部完工 ⇒ 待办必须是空（否则"待办"退化成"永远有活没干完"）
    let all = vec![
        Completion::from_wait("j-1", Some(0)),
        Completion::from_wait("j-2", Some(0)),
        Completion::from_wait("j-3", Some(0)),
    ];
    assert!(
        pending(&intents, &all).is_empty(),
        "全部完工之后待办必须为空"
    );
    // 正控的另一半：一条通告都没有 ⇒ 三个都是待办
    assert_eq!(pending(&intents, &[]).len(), 3);

    let _ = fs::remove_dir_all(&d);
}

/// `j04` —— **完工通告的读回是幂等的**（读法是叶子：不写盘、不取锁、不改一个字节）。
#[test]
fn j04_reading_completion_is_idempotent() {
    let d = tmpdir("j04");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
    for (id, code) in [("j-a", 0), ("j-b", 1), ("j-c", 0)] {
        let c = Completion::from_wait(id, Some(code));
        w.commit("notice", "world://agent/1", c.notice_body())
            .unwrap();
    }

    let bytes0 = fs::read(&lp).unwrap();
    let events: Vec<Value> = String::from_utf8(bytes0.clone())
        .unwrap()
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();

    let a = completions_in(&events);
    let b = completions_in(&events);
    assert_eq!(a, b, "同一个账本折叠两次必须得到同一批通告");
    let ja: Vec<Value> = a.iter().map(Completion::stable_json).collect();
    let jb: Vec<Value> = b.iter().map(Completion::stable_json).collect();
    assert_eq!(
        serde_json::to_string(&ja).unwrap(),
        serde_json::to_string(&jb).unwrap(),
        "连**字节**都要相同（读法不许持有状态、不许有随机成分）"
    );

    // 折叠**不许**改账本一个字节（叶子）
    let bytes1 = fs::read(&lp).unwrap();
    assert_eq!(bytes0, bytes1, "读一次就改账本 ⇒ 那不是读法，是写者");

    // 事件数 ≡ 通告数（这一批账本里全是通告）
    assert_eq!(a.len(), 3, "三条完工通告 ⇒ 三条；实得 {a:?}");

    let _ = fs::remove_dir_all(&d);
}
