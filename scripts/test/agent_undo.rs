//! **动手前的载体撤销点** —— 会红的断言（原 Go `agentd/internal/snapshot` 的 Rust 侧对应面）。
//!
//! ## 这一件补的是**断言**，不是行为
//!
//! 「高风险 ＋ 撤销策略为动手前 ⇒ 先做撤销点；做不成 ⇒ 拒绝动手」这条**行为已经在**
//! `src/carrier/providers.rs` 的 `execute()` 里（第 5 步，`undo_marker` 那个口子）。
//! 但它**没有一条断言**盯着"调用几次、什么顺序、失败会怎样、以及撤销点不是世界回滚"——
//! 而"没有断言的实现"正是本项目反复吃亏的形态（改名、顺序调换都不会有东西变红）。
//! ⇒ 本文件**不改 `providers.rs` 一个字节**，只把那条行为钉住。
//!
//! ## 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `u01` | `providers.rs::execute` 里 `if cap.needs_undo() { … }` **整段删掉** ⇒ **红**（撤销编排零次调用）；把这一段挪到 `undo_ref` 之后的下方（即动手**之后**才做撤销点）⇒ **红**（顺序反了） |
//! | `u02` | 把 `Err(e) => return Outcome::refused(...)` 改成 `Err(_) => {}`（撤销点失败也照动手）⇒ **红**（副作用发生了） |
//! | `u03` | 把 `if cap.needs_undo()` 改成恒真 ⇒ **红**（不需要撤销的策略也去编排） |
//! | `u04` | 让载体撤销点顺手往世界写一条"回滚"记录（或让读模型按撤销点改字段）⇒ **红**（账本多了回滚、或字段被撤销点带走） |
//!
//! ## 正控（钉住"不该红的"）
//!
//! | 用例 | 它钉什么 |
//! |---|---|
//! | `u03` | **不需要撤销的策略**编排次数必须是 **0**——否则"按策略编排"会退化成"凡high-risk都编排" |
//! | `u01` 的后半段 | **确认未通过**时撤销编排也必须是 **0**（"拒绝的动作不配拥有快照"） |
//! | `u04` | 它同时核**读模型的字段确实变了**——否则"撤销点不是回滚"会退化成"什么都没发生" |

use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::carrier::capd::Manifest;
use world_core::carrier::provider::Provider;
use world_core::carrier::providers::{execute, Registry};
use world_core::carrier::{outcome, Invocation};
use world_core::{common::event, World};

/// 一个**记录被调用**的执行器（只有它碰载体）。
struct Recording {
    log: Arc<Mutex<Vec<String>>>,
    fail: bool,
}

impl Provider for Recording {
    fn name(&self) -> &'static str {
        "rec"
    }
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["pkg.install"]
    }
    fn call(&self, verb: &str, _params: &Value) -> Result<Value, String> {
        self.log.lock().unwrap().push(format!("call:{verb}"));
        if self.fail {
            return Err("ext.world.Carrier.ProviderFailed: 执行器故意失败".to_string());
        }
        Ok(json!({ "did": verb }))
    }
}

fn manifest(raw: &str) -> Manifest {
    let c = Manifest::parse(raw, std::path::Path::new("t.json")).unwrap();
    Manifest::from_caps(vec![c])
}

fn inv(rid: &str) -> Invocation {
    Invocation {
        capability: "pkg.install".to_string(),
        verb: "install".to_string(),
        request_id: rid.to_string(),
        params: json!({}),
    }
}

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-agundo-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

const HIGH_BEFORE_EACH: &str = r#"{"capability":"pkg.install","provider":"rec","verbs":["install"],
               "risk":"high","undo":"before-each","confirm":"required"}"#;
const HIGH_NEVER: &str = r#"{"capability":"pkg.install","provider":"rec","verbs":["install"],
                             "risk":"high","undo":"never","confirm":"never"}"#;
const LOW_BEFORE_EACH: &str = r#"{"capability":"pkg.install","provider":"rec","verbs":["install"],
                                  "risk":"low","undo":"before-each","confirm":"never"}"#;

/// `u01` —— **高风险＋动手前 ⇒ 编排出一次撤销点，且顺序在人确认之后**。
#[test]
fn u01_undo_happens_once_and_after_the_confirmation() {
    let log: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let mut reg = Registry::new();
    reg.add(Box::new(Recording {
        log: Arc::clone(&log),
        fail: false,
    }));

    let undo_log = Arc::clone(&log);
    let undo = move |_rid: &str| -> Result<Value, String> {
        undo_log.lock().unwrap().push("undo".to_string());
        Ok(json!({ "kind": "carrier-undo", "path": "/tmp/undo/1" }))
    };
    let confirm_log = Arc::clone(&log);
    let confirm = move |_c: &str, _p: &Value| -> bool {
        confirm_log.lock().unwrap().push("confirm".to_string());
        true
    };

    let m = manifest(HIGH_BEFORE_EACH);
    let o = execute(&m, &reg, &inv("r-u01"), &confirm, &undo);

    assert_eq!(o.result, outcome::OK, "确认通过 ＋ 撤销点成功 ⇒ 应当执行");
    let calls = log.lock().unwrap().clone();
    assert_eq!(
        calls.iter().filter(|c| c.as_str() == "undo").count(),
        1,
        "撤销编排必须**恰好一次**；实得调用序列 = {calls:?}"
    );
    assert_eq!(
        calls,
        vec![
            "confirm".to_string(),
            "undo".to_string(),
            "call:install".to_string()
        ],
        "顺序必须是 **确认 → 撤销点 → 动手**（顺序不可交换）；实得 = {calls:?}"
    );

    // 撤销点的位置必须**可观察地**交给调用方（不是内部消化掉）
    let uref = o.undo_ref.expect("撤销点位置必须交出来（可观察）");
    assert_eq!(
        uref.get("path").and_then(Value::as_str),
        Some("/tmp/undo/1"),
        "交出来的应当是撤销点自己的引用：{uref}"
    );

    // **正控**：确认未通过时，撤销编排必须是 0（"拒绝的动作不配拥有快照"）
    let log2: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let mut reg2 = Registry::new();
    reg2.add(Box::new(Recording {
        log: Arc::clone(&log2),
        fail: false,
    }));
    let undo_log2 = Arc::clone(&log2);
    let undo2 = move |_r: &str| -> Result<Value, String> {
        undo_log2.lock().unwrap().push("undo".to_string());
        Ok(json!({ "path": "/tmp/undo/2" }))
    };
    let no = |_c: &str, _p: &Value| false;
    let o2 = execute(
        &manifest(HIGH_BEFORE_EACH),
        &reg2,
        &inv("r-u01b"),
        &no,
        &undo2,
    );
    assert_eq!(o2.result, outcome::REFUSED, "确认未通过 ⇒ 拒绝");
    assert_eq!(
        log2.lock().unwrap().iter().filter(|c| *c == "undo").count(),
        0,
        "确认未通过时**不许**先做撤销点"
    );
    assert!(o2.undo_ref.is_none(), "被拒的动作不该带撤销点");
}

/// `u02` —— **撤销点失败 ⇒ 不执行**（"没有退路就不动手"）。
#[test]
fn u02_undo_failure_blocks_the_action() {
    let log: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let mut reg = Registry::new();
    reg.add(Box::new(Recording {
        log: Arc::clone(&log),
        fail: false,
    }));

    let undo_log = Arc::clone(&log);
    let undo = move |_r: &str| -> Result<Value, String> {
        undo_log.lock().unwrap().push("undo".to_string());
        Err("ext.world.Carrier.UndoFail: 做不出撤销点".to_string())
    };
    let yes = |_c: &str, _p: &Value| true;

    let o = execute(
        &manifest(HIGH_BEFORE_EACH),
        &reg,
        &inv("r-u02"),
        &yes,
        &undo,
    );

    assert_eq!(
        o.result,
        outcome::REFUSED,
        "撤销点做不成 ⇒ **拒绝**（不是 failed、也不是 ok）；实得 {:?} = {}",
        o.result,
        o.detail
    );
    assert!(
        o.detail.to_string().contains("撤销点做不成，故不动手"),
        "拒绝的理由必须点名「撤销点做不成」；实得 {}",
        o.detail
    );
    let calls = log.lock().unwrap().clone();
    assert_eq!(
        calls.iter().filter(|c| c.starts_with("call:")).count(),
        0,
        "**副作用必须是零**：一次都不许调执行器；实得 = {calls:?}"
    );
    assert_eq!(o.exit_code, 0, "拒绝不是「执行了但失败」");
}

/// `u03` —— **不需要撤销的策略不编排**（正控：防"凡 high-risk 都编排"）。
#[test]
fn u03_no_undo_policy_means_zero_undo_calls() {
    // ① 高风险 ＋ undo=never ⇒ 0 次
    for (tag, raw) in [
        ("高风险但策略是 never", HIGH_NEVER),
        ("低风险但策略是 before-each", LOW_BEFORE_EACH),
    ] {
        let log: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
        let mut reg = Registry::new();
        reg.add(Box::new(Recording {
            log: Arc::clone(&log),
            fail: false,
        }));
        let undo_log = Arc::clone(&log);
        let undo = move |_r: &str| -> Result<Value, String> {
            undo_log.lock().unwrap().push("undo".to_string());
            Ok(json!({ "path": "/tmp/undo/none" }))
        };
        let yes = |_c: &str, _p: &Value| true;
        let o = execute(&manifest(raw), &reg, &inv("r-u03"), &yes, &undo);
        assert_eq!(o.result, outcome::OK, "{tag} ⇒ 应当执行；实得 {}", o.detail);
        let n = log.lock().unwrap().iter().filter(|c| *c == "undo").count();
        assert_eq!(
            n, 0,
            "{tag} ⇒ 撤销编排必须 **0** 次（策略说不用就是不用）；实得 {n} 次"
        );
        assert!(o.undo_ref.is_none(), "{tag} ⇒ 没做撤销点就不许交出引用");
    }
}

/// `u04` —— **载体撤销点不是"世界可回滚"的证据**（口径分界）。
///
/// 撤销点撤的是**文件系统的字节**；世界状态的回滚是**追加补偿事件**，另一件事。
/// 本用例把这条分界钉成可判的两半：
/// ① 做了一次载体撤销点之后，**账本里不许**因此多出一条"回滚"记录；
/// ② 读模型里的字段**仍然反映那次已经做过的动作**（撤销点没有把它悄悄撤回去）。
#[test]
fn u04_carrier_undo_is_not_world_rollback() {
    let d = tmpdir("u04");
    let lp = d.join("ledger.jsonl");
    let onto =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/ontology_definition/ontology.json");
    let pol = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json");
    let mut w = World::open(&onto, &lp, &pol).unwrap();

    // 先做一次**载体撤销点**（编排成功）
    let log: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let mut reg = Registry::new();
    reg.add(Box::new(Recording {
        log: Arc::clone(&log),
        fail: false,
    }));
    let undo_log = Arc::clone(&log);
    let undo = move |_r: &str| -> Result<Value, String> {
        undo_log.lock().unwrap().push("undo".to_string());
        Ok(json!({ "kind": "carrier-undo", "path": "/tmp/undo/u04" }))
    };
    let yes = |_c: &str, _p: &Value| true;
    let o = execute(
        &manifest(HIGH_BEFORE_EACH),
        &reg,
        &inv("r-u04"),
        &yes,
        &undo,
    );
    assert_eq!(o.result, outcome::OK);
    assert!(o.undo_ref.is_some(), "撤销点确实做了");

    // 世界侧照常落一条 change（世界状态由账本决定，与撤销点无关）
    w.commit(
        "change",
        "world://user",
        event::change_body(
            "world://notice/muted-flag",
            "muted",
            json!(false),
            json!(true),
        ),
    )
    .unwrap();

    // ① 账本里不许出现"回滚"这一类记录
    let raw = fs::read_to_string(&lp).unwrap();
    let events: Vec<Value> = raw
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    let kinds: Vec<String> = events
        .iter()
        .map(|e| {
            e.get("kind")
                .and_then(Value::as_str)
                .unwrap_or("?")
                .to_string()
        })
        .collect();
    assert!(
        !kinds.iter().any(|k| k == "rollback"),
        "载体撤销点**不许**在世界里产生一条回滚记录；实得 kind 序列 = {kinds:?}"
    );
    assert_eq!(
        kinds,
        vec!["change".to_string()],
        "账本里就该只有那条 change"
    );

    // ② 读模型里字段**仍然是改后的值**（撤销点没有把它撤回去）
    let s = w.read_model().unwrap();
    assert_eq!(
        s.get("world://notice/muted-flag", "muted"),
        Some(&json!(true)),
        "载体撤销点**不是**世界回滚：读模型必须仍反映那条已经落笔的 change"
    );

    let _ = fs::remove_dir_all(&d);
}
