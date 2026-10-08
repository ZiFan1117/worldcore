//! **投递与应答**（`REQ-F-023`）—— 会红的断言。
//!
//! 这一格原来红在哪（本仓实测，逐字可核）：`to` 与 `request_id` 的配对**都没有实现**。
//!
//! - `to`：本体（`ontology.json:18`）逐字 `"string  # 目的地；空 = 广播"`，
//!   而 `src/` 里**没有任何一处读它**——它只是个被写进信封、谁也不看的格子；
//! - `request_id`：只有"同一条连接＝一次请求应答"这层在场配对
//!   （`WC-IC-001` §2.6 逐字「v1 没有线上配对字段」），**事后从账本里按请求号取回两半**这件事没有。
//!
//! 本文件把这两件事变成可判的断言。判据的出处逐条列在每条用例的文档里。
//!
//! # 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `d01` `d04` | `src/common/delivery.rs` 的 `filter(\|ev\| delivered_to(ev, recipient))` 换成 `filter(\|_\| true)`（把 `to` 当装饰）⇒ 两条一起红（`to` 指定的那条会出现在**别人的**出口上） |
//! | `d07` | `src/common/delivery.rs` 的 `filter(\|s\| !s.is_empty())` 删掉 ⇒ **账本原文里**写着 `"to": ""` 的那条不再是广播 ⇒ 红 |
//! | `d03` | `src/common/event.rs` 的 `with_to` 改成"空串也写进去"（`if !t.is_empty()` 删掉）⇒ 写侧落下 `"to": ""` ⇒ 红 |
//! | `d05` `d06` | `src/common/pairing.rs` 的 `is_result` 改成恒 `false`（凡 `act` 都算意图）⇒ 结果被算成第二条意图 ⇒ 两条一起红 |
//! | `d06` | `src/common/pairing.rs` 的 `Outcome::Mistraced` 分支并入 `Complete`（即不看 `trace`）⇒ 红 |
//! | `d02` `d04` | 是**正控**：它们钉住"不该红的"——把投递判据改成"只送广播"（`delivered_to` 恒等于 `broadcast(ev)`）⇒ 这两条红，而 `d03`/`d07` 仍绿 |
//!
//! 逐条变异都在 VM 上真做过（改坏 → 红 → 恢复 → 绿），原始输出见本 change 的执行记录。

use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::common::pairing;
use world_core::{
    common::{delivery, event},
    World,
};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-delivery-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn open_world(tag: &str) -> World {
    let d = tmpdir(tag);
    World::open(
        &manifest_dir().join("src/ontology_definition/ontology.json"),
        &d.join("ledger.jsonl"),
        &manifest_dir().join("src/gate/policy.json"),
    )
    .unwrap()
}

/// `act` 的**意图**（不带 `params.result`）。
fn act_intent(rid: &str) -> Value {
    event::act_body("notice.mute", "do", rid, json!({ "note": rid }))
}

/// `act` 的**结果**（带 `params.result`；载体适配器写结果时就是这个形状）。
fn act_result(rid: &str, outcome: &str) -> Value {
    event::act_body(
        "notice.mute",
        "do",
        rid,
        json!({ "result": outcome, "exit_code": 0 }),
    )
}

/// **d01**：带 `to` ⇒ **只有该收件人看得到**（别人那一份里没有它）。
///
/// 判据出处：规格 `ninedim/06-变更/archive/2026-09-28-cover-unimplemented-capabilities/specs/delivery-and-resources/spec.md:16-17` 逐字
/// 「**WHEN** 写入一条带 `to` 的事件，再分别用两个收件人的读法取账本／
/// **THEN** 该事件只出现在 `to` 指定的那一份读法里，另一份里没有它」。
#[test]
fn d01_a_tagged_event_reaches_only_the_named_recipient() {
    let mut w = open_world("d01");
    let (a, b) = ("world://agent/1", "world://agent/2");

    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(a),
    )
    .expect("带 `to` 的事件必须被接受（本体把 `to` 列为可选字段，不填或填了都不该报错）");

    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 1, "账本必须有且只有这一条");

    assert!(
        delivery::delivered_to(&evs[0], a),
        "指定的收件人必须收到：to={:?}",
        evs[0].get("to")
    );
    assert!(
        !delivery::delivered_to(&evs[0], b),
        "**没被指定的收件人不得收到**——这一条就是'把 `to` 当装饰'的反假断言"
    );

    // 两份"读法"各自的样子（出口是账本的保序子序列）
    assert_eq!(delivery::outbox(&evs, a).len(), 1, "{} 的出口应有这一条", a);
    assert!(delivery::outbox(&evs, b).is_empty(), "{} 的出口应为空", b);

    // 而且**账本本身一条不少**：投递不改事实（书 §4.6 第一层「落笔即发布」）
    assert_eq!(
        w.ledger().read_all().unwrap().len(),
        1,
        "按收件人过滤是**读侧派生**，不得动账本"
    );
}

/// **d02**：不带 `to` ⇒ **广播**（正控：钉住"不该红的"）。
///
/// 判据出处：规格 `spec.md:17` 后半逐字「不带 `to` 的事件两份都在」；
/// 本体 `ontology.json:18` 逐字「空 = 广播」。
///
/// 这条同时是**正控**：若有人把投递判据改成"只送广播"（收件人指定的那条谁也不送），
/// `d01` 与 `d04` 会红，而本条仍绿 ⇒ 两条断言互不冒充。
#[test]
fn d02_an_untagged_event_is_broadcast_to_every_recipient() {
    let mut w = open_world("d02");
    let (a, b) = ("world://agent/1", "world://agent/2");

    // ① 收件人 a 各收一条（一条指定、一条广播）
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(a),
    )
    .unwrap();
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(b),
    )
    .unwrap();
    // ② 无 `to`：广播
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        None,
    )
    .unwrap();

    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 3);

    let broadcast_ev = evs.last().unwrap();
    assert!(
        broadcast_ev.get("to").is_none(),
        "未指定收件人时**不得写出 `to` 键**（`None` ⇒ 不写该键，不写 `null`）：{broadcast_ev}"
    );
    for r in [a, b, "world://user", "world://nobody"] {
        assert!(
            delivery::delivered_to(broadcast_ev, r),
            "广播必须送到每一个收件人，实缺：{r}"
        );
        assert!(
            delivery::outbox(&evs, r).iter().any(|e| e == broadcast_ev),
            "广播必须出现在 {r} 的出口上"
        );
    }
}

/// **d03**：`to` 为**空串**＝广播（本体逐字「空 = 广播」）；`to` 有名字才收窄。
///
/// 这条把"空"与"没写"钉成**同一个意思**：否则同一句话会有两种读法。
#[test]
fn d03_an_empty_to_is_a_broadcast_and_a_name_narrows_it() {
    let mut w = open_world("d03");
    let (a, b) = ("world://agent/1", "world://agent/2");

    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(""),
    )
    .expect("`to` 为空串必须被接受（空 = 广播，本体逐字）");
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(a),
    )
    .unwrap();

    let evs = w.ledger().read_all().unwrap();
    assert_eq!(
        evs[0].get("to"),
        None,
        "空串与未给同义 ⇒ `with_to` **不写该键**，否则账本里会出现两种写法表达同一个意思"
    );
    assert!(
        delivery::delivered_to(&evs[0], b),
        "空 `to` 必须当广播：{} 也该收到",
        b
    );
    assert!(
        !delivery::delivered_to(&evs[1], b),
        "非空 `to` 必须收窄：{} 不得收到给 {} 的那一条",
        b,
        a
    );
}

/// **d04**：**反假**——把 `to` 当装饰（不看它）**必须**变红。
///
/// 做法：把"两个收件人的出口"逐条对出来——指定给 a 的那一条**只能**在 a 的出口上，
/// 且 b 的出口必须**恰好**只有广播那一条（数目也要对）。
///
/// 若投递判据被改成"谁都收到"（`filter(|_| true)`），b 的出口会多出一条 ⇒ 红；
/// 若被改成"只送广播"，a 的出口会少一条 ⇒ 红。⇒ 本条把两个方向**同时**钉住。
#[test]
fn d04_a_decorative_to_would_turn_this_red() {
    let mut w = open_world("d04");
    let (a, b) = ("world://agent/1", "world://agent/2");

    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(a),
    )
    .unwrap();
    w.commit_requested(
        "notice",
        b,
        event::notice_body("job.done", b, json!({})),
        None,
        Some(b),
    )
    .unwrap();
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        None,
    )
    .unwrap();
    // 第三个收件人：**没被点名，也没有广播以外的东西**
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some(a),
    )
    .unwrap();

    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 4, "账本四条（投递不删账本）");

    let box_a = delivery::outbox(&evs, a);
    let box_b = delivery::outbox(&evs, b);
    let box_c = delivery::outbox(&evs, "world://agent/3");

    assert_eq!(box_a.len(), 3, "a：两条点名的 ＋ 一条广播");
    assert_eq!(box_b.len(), 2, "b：一条点名的 ＋ 一条广播");
    assert_eq!(box_c.len(), 1, "从没被点名的收件人只该拿到广播那一条");

    // 逐条把"谁看得到什么"写成可读的断言（红的时候能一眼看出多/少了哪一条）
    let want = |idx: &[usize]| -> Vec<Value> { idx.iter().map(|i| evs[*i].clone()).collect() };
    assert_eq!(box_a, want(&[0, 2, 3]), "a 的出口逐条");
    assert_eq!(box_b, want(&[1, 2]), "b 的出口逐条");
    assert_eq!(box_c, want(&[2]), "未点名者的出口逐条");

    // 两半的分工：投递不丢账本 ⇒ 每个收件人的出口都是账本的**子序列**
    for (name, bx) in [(a, &box_a), (b, &box_b), ("world://agent/3", &box_c)] {
        assert!(
            bx.iter().all(|e| evs.contains(e)),
            "{name} 的出口里出现了账本里没有的事件——投递不得新增事实"
        );
    }
}

/// **d05**：应答能按 `request_id` 追回它的请求（两半都是**落到账本上**的事件）。
///
/// 判据出处：书 §4.6 逐字「请求与结果的配对靠两处对齐：**同一个请求编号**，
/// 以及"因为哪一条"那一格指回提出这件事的那条记录。两处都在账本上，
/// 配对因此可以在**事后核对**，不必依赖当时在场的谁记得。」
///
/// ⇒ 断言的落点是**账本**：先写意图、再写结果（带 `trace` 指回意图），
/// 然后只用账本把两半取回来。
#[test]
fn d05_an_answer_can_be_traced_back_to_its_request_by_request_id() {
    let mut w = open_world("d05");
    let actor = "world://agent/1";

    let intent = w
        .commit_requested("act", actor, act_intent("r-delivery-1"), None, None)
        .expect("意图落账");
    let intent_id = intent
        .get("id")
        .and_then(Value::as_str)
        .expect("意图要有 id")
        .to_string();

    let answer = w
        .commit_requested(
            "act",
            actor,
            act_result("r-delivery-1", "ok"),
            Some(&intent_id),
            None,
        )
        .expect("结果落账");
    assert_ne!(json!(intent_id), answer["id"], "请求与应答是**两条**事件");

    // ── 事后核对：只用账本 ──
    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 2, "两半都要在账本上");
    match pairing::find_pair(&evs, "r-delivery-1") {
        pairing::Outcome::Complete(pair) => {
            assert_eq!(
                pair.request_id, "r-delivery-1",
                "配对键 = 同一个 request_id"
            );
            assert_eq!(pair.intents.len(), 1);
            assert_eq!(pair.results.len(), 1);
            assert!(pair.is_complete());
            assert_eq!(pair.intents[0]["id"], json!(intent_id));
            assert_eq!(pair.results[0]["id"], answer["id"]);
            assert_eq!(
                pair.results[0]["trace"],
                json!(intent_id),
                "因果那一格必须**指回提出这件事的那条记录**（书 §4.6 第二处对齐）"
            );
            assert_eq!(pair.trace_agrees(), Some(true));
        }
        other => panic!("应答应当能追回它的请求，实得 {other:?}"),
    }

    // 反假：**换了请求号就追不回**——否则说明配对键根本不是 `request_id`
    assert_eq!(
        pairing::find_pair(&evs, "r-别的"),
        pairing::Outcome::Untraced
    );
    // 而配对键**不是** `trace`：同一条 trace，另一个请求号照样取不到
    assert_eq!(
        pairing::pairs(&evs)
            .iter()
            .map(|p| p.request_id.clone())
            .collect::<Vec<_>>(),
        vec!["r-delivery-1".to_string()]
    );
}

/// **d06**：`request_id` 是**真配对键**——配对键坏掉/缺失时必须变红，且三种"没配成"各自可判。
///
/// 判据出处：书 §4.6 两处对齐**都要成立**；`WC-IC-001` §2.6 逐字
/// 「`change` / `notice` **没有**配对字段」。
#[test]
fn d06_the_pairing_key_is_request_id_and_a_broken_key_is_visible() {
    let mut w = open_world("d06");
    let actor = "world://agent/1";

    let intent = w
        .commit_requested("act", actor, act_intent("r-pair-1"), None, None)
        .unwrap();
    let intent_id = intent.get("id").unwrap().as_str().unwrap().to_string();

    // ① 应答用**别的**请求号 ⇒ 原请求仍是"有意图、无结果"
    w.commit_requested(
        "act",
        actor,
        act_result("r-pair-2", "ok"),
        Some(&intent_id),
        None,
    )
    .unwrap();
    let evs = w.ledger().read_all().unwrap();

    match pairing::find_pair(&evs, "r-pair-1") {
        pairing::Outcome::Unpaired { intent_count, .. } => assert_eq!(intent_count, 1),
        other => panic!("请求号对不上就不算配对，实得 {other:?}"),
    }
    assert!(matches!(
        pairing::find_pair(&evs, "r-pair-2"),
        pairing::Outcome::Unrequested { .. }
    ));
    assert_eq!(
        pairing::find_pair(&evs, "r-从未出现"),
        pairing::Outcome::Untraced
    );

    // ② 配对键在、因果那一格**指错**⇒ 只对上一处，必须与"两处都对上"分开判
    let mut w2 = open_world("d06b");
    let i2 = w2
        .commit_requested("act", actor, act_intent("r-pair-3"), None, None)
        .unwrap();
    let i2_id = i2.get("id").unwrap().as_str().unwrap().to_string();
    w2.commit_requested(
        "act",
        actor,
        act_result("r-pair-3", "ok"),
        Some("e-并不存在"),
        None,
    )
    .unwrap();
    let evs2 = w2.ledger().read_all().unwrap();
    match pairing::find_pair(&evs2, "r-pair-3") {
        pairing::Outcome::Mistraced { intent, result } => {
            assert_eq!(intent["id"], json!(i2_id));
            assert_eq!(result["trace"], json!("e-并不存在"));
        }
        other => panic!("因果指错必须单独成一态，实得 {other:?}"),
    }

    // ③ `change` / `notice` 不参与配对（它们没有配对字段）
    let mut w3 = open_world("d06c");
    w3.commit_requested(
        "notice",
        actor,
        event::notice_body("job.done", actor, json!({ "request_id": "r-pair-1" })),
        None,
        None,
    )
    .unwrap();
    let evs3 = w3.ledger().read_all().unwrap();
    assert!(
        pairing::pairs(&evs3).is_empty(),
        "信纸里出现同名的键不算配对字段：notice 不参与配对"
    );
    assert_eq!(
        pairing::find_pair(&evs3, "r-pair-1"),
        pairing::Outcome::Untraced
    );
}

/// **d07**：**从账本原文读**的时候，显式写着 `"to": ""` 的条目也必须是广播。
///
/// 为什么要有这一条（实测教训，2026-09-27）：经 `World::commit_requested` 写进去的空串
/// **根本不会落成 `to` 键**（`event::with_to` 就不写），于是 `d03` 只钉住了写入侧的口径，
/// **钉不住读侧**：把 `delivery::recipient_of` 里那句 `filter(|s| !s.is_empty())` 删掉，
/// `d03` 照样绿（实测：变异 m2 的第一次读数就是"7 passed"，是**假绿**）。
///
/// 读侧为什么必须自己也判：账本是**纯文本 JSON Lines**，别处（另一种语言的写侧、手写、
/// 旧版本）完全可能写出 `"to": ""` 这个字面量。读法不得依赖"写侧从不写空串"这个假设——
/// 那正是"两处各自成立"这句话的反面（本体逐字：空 = 广播；`""` 就是空）。
#[test]
fn d07_an_explicit_empty_to_in_the_raw_ledger_is_also_a_broadcast() {
    let d = tmpdir("d07raw");
    let lp = d.join("ledger.jsonl");
    // 手写两行账本：第一行**显式**写 `"to": ""`，第二行点名一个收件人。
    // 刻意不经 `World::commit_requested` —— 本条要测的正是"读别人写下的账本"。
    let raw = concat!(
        r#"{"world":1,"kind":"notice","id":"e-1","seq":1,"at":100,"actor":"world://agent/1","#,
        r#""to":"","flags":[],"body":{"type":"job.done","subject":"world://agent/1","payload":{}}}"#,
        "\n",
        r#"{"world":1,"kind":"notice","id":"e-2","seq":2,"at":101,"actor":"world://agent/1","#,
        r#""to":"world://agent/9","flags":[],"body":{"type":"job.done","subject":"world://agent/1","payload":{}}}"#,
        "\n",
    );
    fs::write(&lp, raw).unwrap();

    let w = World::open_readonly(
        &manifest_dir().join("src/ontology_definition/ontology.json"),
        &lp,
        &manifest_dir().join("src/gate/policy.json"),
    )
    .expect("工厂本体/策略 + 手写账本应当可以只读打开");
    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 2);

    // 空串 = 广播（实现口径：`recipient_of` 把它读成"没有收件人"，
    // 因此它**不占** `recipients()` 里的一个名字）
    assert!(
        delivery::recipients(&evs) == vec!["world://agent/9".to_string()],
        "只有非空的 to 才算收件人，实得 {:?}",
        delivery::recipients(&evs)
    );

    // ★ 这条才是"读侧判空串"的会红断言：指名给 agent/9 的那条**不得**出现在 agent/1 的出口上，
    //   而"空串那条"必须在。读侧若不判空串，agent/1 的出口里会**一条不剩**。
    let box1 = delivery::outbox(&evs, "world://agent/1");
    assert_eq!(
        box1.len(),
        1,
        "agent/1 的出口应当只有『空串那条』（手写账本里的广播），实得 {} 条",
        box1.len()
    );
    assert_eq!(box1[0]["id"], json!("e-1"), "留下的必须是那条空串广播");
    let box9 = delivery::outbox(&evs, "world://agent/9");
    assert_eq!(box9.len(), 2, "agent/9 应当两条都收到");
    assert_eq!(
        box9[1]["id"],
        json!("e-2"),
        "明细：第一条是空串广播、第二条才是点名给它的"
    );
}

/// **登记项**（不是"已做到"）：投递的边界今天在哪。
///
/// 三条**仍然没有**的东西，逐条写清楚——不许把"没做到"读成"做到了"：
///
/// 1. **没有收件人名单**：`to` 写一个不存在的收件人**不算错**（书 §4.6 没有要求
///    "必须是在册的谁"）⇒ `WC-SRS-001` §五 `TC-043` 行要的"超范围收件人的拒绝形态"
///    **今天仍无标的物**；
/// 2. **没有跨进程投递出口**：CLI（`src/main.rs`）七个命令都不读 `to`；
///    经公开 API 可指定 `to` 的入口只有 `World::commit_requested`；
/// 3. **投递是读侧派生**：它**不是**"谁订阅了什么"的服务端登记，也没有游标——
///    "我读到第几条"由收件人自己记着（书 §4.6 第二层）。
///
/// 谁合上 1／2，本用例会红（它把现状钉住了）。
#[test]
fn d08_registered_boundaries_of_delivery_today() {
    let mut w = open_world("d07");
    let a = "world://agent/1";

    // ① 不存在的收件人：照样被接受、照常落账（不是"发送失败"）
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        Some("world://不存在的收件人"),
    )
    .expect("登记：收件人名单今天不存在 ⇒ 不校验、不报错");
    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 1, "它只送到那个名字上，但账本照样有一条");
    assert_eq!(delivery::recipients(&evs), vec!["world://不存在的收件人"]);
    assert!(delivery::outbox(&evs, a).is_empty(), "别人收不到它");

    // ② 投递不产生新事件：写 N 条 ⇒ 账本就是 N 条，出口之和 ≥ N（广播按人头重复计数）
    let before = evs.len();
    w.commit_requested(
        "notice",
        a,
        event::notice_body("job.done", a, json!({})),
        None,
        None,
    )
    .unwrap();
    assert_eq!(
        w.ledger().read_all().unwrap().len(),
        before + 1,
        "投递本身**不写账本**：它只是读侧的一个判据"
    );

    // ③ 没有收件人的账本：出口全空而账本不空
    let mut w2 = open_world("d07b");
    w2.commit(
        "notice",
        a,
        event::notice_body("job.done", a, json!({ "note": "无 to" })),
    )
    .unwrap();
    let evs2 = w2.ledger().read_all().unwrap();
    assert!(delivery::recipients(&evs2).is_empty(), "广播不占任何收件人");
    assert_eq!(delivery::outbox(&evs2, a).len(), 1, "但它落到每个出口上");
}
