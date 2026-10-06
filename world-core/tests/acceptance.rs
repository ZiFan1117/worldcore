//! 项目 Step 1（账本）+ 项目 Step 2（读模型）的**验收测试**。
//!
//! 覆盖 `07/4-计划/04-模块清单与实现顺序.md` §六 的三条专属验收测试：
//! - 追加 → 读回（t1）
//! - 重启进程 → 事件还在（t2）
//! - ★ **删掉读模型 → 重算一致**（t7）
//!
//! 其余为**工程纪律**与**坏输入**的防线：半行丢弃（t3）、缺号拒启（t4）、
//! 违法不落笔（t5）、坏本体拒启（t6）、读模型拒绝坏账本（t8）。
//!
//! **不依赖 sleep、不依赖网络、不依赖外部服务**——确定性可复现
//! （教训来自 `07-agent-native-os` 的"完工铃丢铃"竞态）。
//!
//! 每个测试用**一次性沙箱目录**（临时目录），**绝不触碰真实账本**
//! ——依 `06-swe-gb` 的幂等口径修订：命令必须幂等，数据操作天然不幂等。

use serde_json::json;
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::{event, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-accept-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    d
}

fn ontology() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/ontology_definition/ontology.json")
}

/// 出厂门禁策略（法律之权限）。
fn policy() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json")
}

/// 验收测试 1：**追加 → 读回**（账本本身对不对）
#[test]
fn t1_append_then_read_back() {
    let d = tmpdir("t1");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-42", "muted", json!(false), json!(true)),
    )
    .unwrap();
    w.commit(
        "act",
        "world://user",
        event::act_body("notice.mute", "do", "r-1", json!({})),
    )
    .unwrap();
    w.commit(
        "notice",
        "world://core",
        event::notice_body("job.done", "world://job/t-7", json!({ "exit": 0 })),
    )
    .unwrap();

    let evs = w.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 3, "应有 3 条事件");
    for (i, ev) in evs.iter().enumerate() {
        assert_eq!(ev["seq"], json!(i as u64 + 1), "seq 必须从 1 连续递增");
        assert_eq!(ev["world"], json!(1), "信封必须带词表版本");
    }
    assert_eq!(evs[0]["kind"], json!("change"));
    assert_eq!(
        evs[0]["body"]["before"],
        json!(false),
        "change 必带 before —— 这是回滚的依据"
    );
    assert_eq!(evs[2]["kind"], json!("notice"));

    // ── `4.4`（`fc-2026-004-assertions`）：**逐字段**一致 ─────────────────────
    // 此前只比 len / seq / world / kind / body.before。为什么逐字段比、而不是「整行字节比」：
    // 整行比在**任何**字段变化时都会红，但红了不知道去哪查；逐字段才是「一条断言一个事实」。
    //
    // ① `actor`：三家族各带各的发起者（**不是常量**）
    assert_eq!(evs[0]["actor"], json!("world://user"), "① change 的 actor");
    assert_eq!(evs[1]["actor"], json!("world://user"), "① act 的 actor");
    assert_eq!(
        evs[2]["actor"],
        json!("world://core"),
        "① notice 的 actor —— 必须与上面两条**不同**，否则 actor 是常量"
    );
    // ② `id`：事件身份 —— 非空、以 `e` 开头（`e<纳秒>-<计数>`），且三条**互不相同**
    let ids: Vec<&str> = evs
        .iter()
        .map(|e| e["id"].as_str().expect("id 必须是字符串"))
        .collect();
    for (i, id) in ids.iter().enumerate() {
        assert!(!id.is_empty(), "② 第 {} 条的 id 不得为空", i + 1);
        assert!(id.starts_with('e'), "② 第 {} 条的 id 形状不对：{id}", i + 1);
    }
    assert_eq!(
        ids.iter().collect::<std::collections::BTreeSet<_>>().len(),
        3,
        "② 三条事件的 id 必须互不相同（同 id 再提交即为重复提交，W-01）：{ids:?}"
    );
    // ③ `at`：落在**本次测试**的时间窗口内（不是 0、不是常量、不是别的单位）
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    for (i, ev) in evs.iter().enumerate() {
        let at = ev["at"].as_u64().unwrap_or(0);
        assert!(
            at > 1_700_000_000 && at <= now + 60,
            "③ 第 {} 条的 at={at} 不在合理窗口内（now={now}）",
            i + 1
        );
    }
    // ④ `flags`：这三条都不带摩擦 ⇒ 必须是**空数组**（不是缺字段、不是 null）
    for (i, ev) in evs.iter().enumerate() {
        assert_eq!(
            ev["flags"],
            json!([]),
            "④ 第 {} 条的 flags 必须是空数组",
            i + 1
        );
    }
    // ⑤ `body.subject`（change 改的是谁 / notice 关于谁）
    assert_eq!(
        evs[0]["body"]["subject"],
        json!("world://notice/n-42"),
        "⑤ change 的 body.subject"
    );
    assert_eq!(
        evs[2]["body"]["subject"],
        json!("world://job/t-7"),
        "⑤ notice 的 body.subject"
    );
    // ⑥ `body.path`
    assert_eq!(
        evs[0]["body"]["path"],
        json!("muted"),
        "⑥ change 的 body.path"
    );
    // ⑦ `body.after`
    assert_eq!(
        evs[0]["body"]["after"],
        json!(true),
        "⑦ change 的 body.after"
    );
}

/// 验收测试 2：**重启进程 → 事件还在**（持久化真的生效）
///
/// ## ⚠️ 证据层级（`4.5` 订正：把「真跨进程」那一层挂到 `TC-070`）
///
/// 本用例里的「重启」是**同一进程内** `drop(world)` 再 `World::open` —— 它证明的是
/// 「事件落了盘、重开能读回」，**不是**「换一个进程还能读到」（同进程的文件句柄与
/// 页缓存状态都可能掩盖问题）。**不要把这条当成跨进程证据。**
///
/// **真跨进程那一层由 `tools/s1_sys_probe2.sh` 的 `TC-070`（`REQ-F-022`）承担**：
/// 那一步用**两个独立的 `world-core read` 进程**读同一本账（本工程的命令一条一个新进程），
/// 断言 ① 两次读回的事件序列**逐字节相同**、② 条数与账本行数一致、③ `seq` 严格递增无缺号；
/// 它由 `check.sh` 的**步骤 ⑦**（`S1 需求验证面补建` 里 `run_tail … bash tools/s1_sys_probe2.sh`）执行。
/// 复现：`cd world-core && bash tools/s1_sys_probe2.sh`。
#[test]
fn t2_events_survive_restart() {
    let d = tmpdir("t2");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/a", "muted", json!(false), json!(true)),
        )
        .unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/b", "muted", json!(false), json!(true)),
        )
        .unwrap();
    } // ← World 落地 = 进程"重启"

    let w2 = World::open(&ontology(), &lp, &policy()).unwrap();
    assert_eq!(w2.ledger().last_seq(), 2, "重启后应看到 2 条");
    assert_eq!(w2.ledger().next_seq(), 3, "next_seq 必须接着 3，不能重号");
    let evs = w2.ledger().read_all().unwrap();
    assert_eq!(evs.len(), 2);
    assert_eq!(evs[1]["body"]["subject"], json!("world://notice/b"));
}

/// 工程纪律 3：**末尾半行必须被丢弃**（模拟"写一行写到一半断电"）
#[test]
fn t3_partial_line_is_discarded() {
    let d = tmpdir("t3");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/x", "muted", json!(false), json!(true)),
        )
        .unwrap();
    }
    // 手工追加"半行"：无结尾换行、JSON 也不完整
    let mut s = fs::read_to_string(&lp).unwrap();
    s.push_str("{\"world\":1,\"kind\":\"change\",\"seq\":2,\"bod");
    fs::write(&lp, s).unwrap();

    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    assert_eq!(w.ledger().last_seq(), 1, "半行必须被丢弃，只剩 1 条");
    assert_eq!(
        w.ledger().next_seq(),
        2,
        "next_seq 回到 2（该号未落笔，可复用）"
    );
}

/// 工程纪律 1：**seq 必须连续**——缺号即损坏，**拒绝启动**（fail loud）
#[test]
fn t4_seq_gap_refuses_to_start() {
    let d = tmpdir("t4");
    let lp = d.join("ledger.jsonl");
    fs::write(&lp, "{\"world\":1,\"seq\":1}\n{\"world\":1,\"seq\":3}\n").unwrap();
    let err = World::open(&ontology(), &lp, &policy()).unwrap_err();
    assert!(err.contains("SeqGap"), "应报 SeqGap，实得: {err}");
}

/// **法律在前、落笔在后**：校验不过绝不写账本，也不消耗 seq。
///
/// 判据（任务 2.4 补的那一条）：**被拒的写入不得改动状态**——
/// 把读模型**读回来比对**，而不是只断言"账本条数没变"。
/// 两者不是一回事：`seq` 没前进而状态被改，账本照样"看起来没写"。
#[test]
fn t5_law_rejects_and_does_not_write() {
    let d = tmpdir("t5");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // ★ 状态未被改动（任务 2.4）：基准快照取自**两次被拒之前**。
    //
    // ⚠️ 顺序刻意如此：下面"词表版本不符"那一段里有一条**合法** `change` 会真的落笔
    //（它写的正是 `world://notice/n#muted` 这一格），快照晚取一步，
    // 这条断言就会把"合法写入"算成"被拒却改了状态"——那是我夹具写错了，不是实现错。
    let before = w.read_model().unwrap().to_json().to_string();

    // 未知家族
    let e1 = w.commit("bogus", "world://user", json!({})).unwrap_err();
    assert!(e1.contains("UnknownKind"), "实得: {e1}");

    // change 缺必填字段 before
    let e2 = w
        .commit(
            "change",
            "world://user",
            json!({ "subject": "world://notice/n", "path": "muted", "after": true }),
        )
        .unwrap_err();
    assert!(e2.contains("MissingField"), "实得: {e2}");

    // 两次被拒之后：读模型必须**逐字节**还是原来的状态，而且那一格仍是"没有值"。
    let s = w.read_model().unwrap();
    assert_eq!(
        s.get("world://notice/n", "muted"),
        None,
        "两次被拒的提交都不得改动状态（尤其那条缺 before 的 change：它写的正是这一格）"
    );
    assert_eq!(s.seen(), 0, "被拒的事件不得进入读模型");
    assert_eq!(
        before,
        s.to_json().to_string(),
        "被拒的提交不得改动状态（逐字节比对，不是只看条数）"
    );

    // 词表版本不符
    let mut bad = w
        .commit(
            "change",
            "world://user",
            event::change_body("world://notice/n", "muted", json!(false), json!(true)),
        )
        .unwrap();
    bad["world"] = json!(999);
    let e3 = w.ontology().validate(&bad).unwrap_err();
    assert!(
        format!("{e3}").contains("BadVersion"),
        "应报 BadVersion，实得: {e3}"
    );

    // 三次都被拒 ⇒ 账本一条都没写（只有第 3 条通过校验并落笔）
    assert_eq!(w.ledger().last_seq(), 1, "被拒的事件绝不允许落笔");

    // 正控：那条合法 change **确实**改了状态——否则上面那句"没改"
    // 可能只是因为读模型什么都不做（假绿）。
    let ok = w.read_model().unwrap();
    assert_eq!(
        ok.get("world://notice/n", "muted"),
        Some(&json!(true)),
        "合法的 change 必须真的改状态（正控）"
    );
    assert_ne!(
        before,
        ok.to_json().to_string(),
        "合法写入前后的状态必须**不同**（否则这条读模型比对没有判别力）"
    );
}

/// 本体文件缺失 / 损坏 ⇒ 拒绝启动（法律不对，带病跑比不跑更危险）
#[test]
fn t6_bad_ontology_refuses_to_start() {
    let d = tmpdir("t6");
    let lp = d.join("ledger.jsonl");
    let bad = d.join("bad.json");
    fs::write(&bad, "{ not json").unwrap();
    assert!(
        World::open(&bad, &lp, &policy()).is_err(),
        "坏本体必须拒绝启动"
    );

    let empty = d.join("empty.json");
    fs::write(&empty, "{}").unwrap();
    assert!(
        World::open(&empty, &lp, &policy()).is_err(),
        "缺版本号必须拒绝启动"
    );
}

// ───────────────────────── 项目 Step 2：读模型（M03）─────────────────────────

/// **验收测试 3（★ 本项目三条专属测试的最后一条）**：
/// **删掉读模型 → 重算一致**。
///
/// 判据不是"能算出来"，而是三条一起：
/// 1. **不写盘**：折叠前后，账本文件的字节**一个都不变**（读模型是纯派生物）；
/// 2. **可重算且一致**：丢掉算好的状态、重新打开世界重算 ⇒ 规范形式**逐字节相同**、指纹相同；
/// 3. **不是常量**（反假测试）：只折叠账本的**前缀**必须得到**不同**的状态——
///    否则"两次结果一样"可能只是因为函数永远返回同一个东西，而不是因为它忠实于账本。
#[test]
fn t7_read_model_is_disposable_and_reproducible() {
    let d = tmpdir("t7");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
        )
        .unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(true), json!(false)),
        )
        .unwrap();
        w.commit(
            "act",
            "world://agent/1",
            event::act_body("notice.mute", "do", "r-7", json!({})),
        )
        .unwrap();
    }

    let before_bytes = fs::read(&lp).unwrap();

    // 第一次折叠
    let w1 = World::open(&ontology(), &lp, &policy()).unwrap();
    let s1 = w1.read_model().unwrap();
    let j1 = s1.to_json().to_string();
    assert_eq!(s1.last_seq(), 3);
    assert_eq!(s1.seen(), 3);
    assert_eq!(s1.acts(), 1);
    assert_eq!(s1.get("world://notice/n-1", "muted"), Some(&json!(false)));

    // 判据 1：读模型不写盘
    let after_bytes = fs::read(&lp).unwrap();
    assert_eq!(
        before_bytes, after_bytes,
        "折叠读模型**不允许**改动账本——读模型是派生物，不是第二个真相"
    );

    // 判据 2：删掉状态（这里直接丢弃 s1 并重开世界）后重算 ⇒ 逐字节一致
    drop(s1);
    drop(w1);
    let w2 = World::open(&ontology(), &lp, &policy()).unwrap();
    let s2 = w2.read_model().unwrap();
    assert_eq!(j1, s2.to_json().to_string(), "重算结果必须逐字节一致");
    assert_eq!(s1_digest(&j1), s2.digest(), "指纹必须一致");

    // 判据 3：反假测试——只折叠前缀必须给出**不同**结果
    let all = w2.ledger().read_all().unwrap();
    let prefix = world_core::ontology_instance::readmodel::State::fold(&all[..1]).unwrap();
    assert_ne!(
        prefix.to_json().to_string(),
        j1,
        "折叠前缀竟与折叠全量相同 ⇒ 这个读模型没有真的在读账本（假测试）"
    );
    assert_eq!(prefix.last_seq(), 1);
}

/// 读模型**拒绝**坏账本（"账本是唯一真相"不能靠信任维持）。
///
/// 三条独立的拒绝路径：序号断裂 / 旧值说谎 / 未知家族。
/// 反面情形同样重要：一个"什么都接受"的读模型会让上面那条 t7 变成空话。
#[test]
fn t8_read_model_refuses_broken_ledger() {
    use world_core::ontology_instance::readmodel::State;

    // ① 序号断裂：seq 从 2 开始
    let gap = vec![event::new_event(
        2,
        "change",
        "world://user",
        event::change_body("world://s", "p", json!(null), json!(1)),
    )];
    let e = State::fold(&gap).unwrap_err();
    assert!(e.contains("不连续"), "应报序号不连续，实得: {e}");

    // ② 旧值说谎：账本说 p 已是 2，事件却称 before=99
    let lying = vec![
        event::new_event(
            1,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(null), json!(2)),
        ),
        event::new_event(
            2,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(99), json!(3)),
        ),
    ];
    let e = State::fold(&lying).unwrap_err();
    assert!(e.contains("旧值不符"), "应报旧值不符，实得: {e}");

    // ③ 未知家族：本体里没有 `guess`
    let unknown = vec![event::new_event(1, "guess", "world://user", json!({}))];
    let e = State::fold(&unknown).unwrap_err();
    assert!(e.contains("未知事件家族"), "应报未知家族，实得: {e}");
}

/// 小结：`digest` 的口径是"规范形式 JSON 的 FNV-1a"，此处独立重算一遍，
/// 以免测试与实现共用同一个错误（自证陷阱）。
fn s1_digest(canonical_json: &str) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in canonical_json.as_bytes() {
        h ^= u64::from(*b);
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    format!("fnv1a64:{h:016x}")
}

// ──────────────────── 项目 Step 5：门禁不可绕过（M05，AC-05）────────────────────

/// **AC-05 之一：越权 100% 拦截**——未声明的能力一律不放行。
///
/// 关键是**三件事同时成立**，缺一条这个门禁就是假的：
/// 1. 调用**返回错误**（不放行）；
/// 2. **没有** `act` 事件落笔（这件事没有发生）；
/// 3. **有一条 `notice` 流水**落笔（拦得住，也记得下）。
#[test]
fn t9_gate_rejects_undeclared_capability_and_records_notice() {
    let d = tmpdir("t9");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    let err = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("world.hack", "do", "r-9", json!({})),
        )
        .unwrap_err();
    assert!(err.contains("门禁拒绝"), "应被门禁拒绝，实得: {err}");
    assert!(
        err.contains("未在门禁策略中声明"),
        "理由必须说清是「能力未声明」，实得: {err}"
    );

    // 判据 2 + 3：act 没落笔，但有一条 notice
    assert_eq!(w.ledger().last_seq(), 1, "被拒的动作不得落笔（它没发生）");
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 1);
    assert_eq!(all[0]["kind"], json!("notice"), "被拒的动作应留下一条流水");
    assert_eq!(
        all[0]["body"]["type"],
        json!("gate.rejected"),
        "流水类型必须可检索"
    );
    assert_eq!(all[0]["body"]["subject"], json!("world://agent/1"));
    assert!(
        all[0]["body"]["payload"]["capability"] == json!("world.hack"),
        "流水里要能看出想做的是什么"
    );
    assert!(
        format!("{}", all[0]["body"]["payload"]["reason"]).contains("未在门禁策略中声明"),
        "流水里要留下拒绝理由"
    );
}

/// **AC-05 之二：不可逆动作加摩擦**——不可逆能力只允许 `irreversible_actors`
/// 白名单主体执行（v1 无审批通道，`DEBT-07`），白名单外的主体走 `AwaitApproval`。
#[test]
fn t10_gate_adds_friction_for_irreversible_capability() {
    let d = tmpdir("t10");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // 可逆 → 放行（免检但留痕：act 本身就落笔了）
    let ok = w
        .commit(
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-10a", json!({})),
        )
        .unwrap();
    assert_eq!(ok["kind"], json!("act"));

    // 不可逆 → 只允许 irreversible_actors 白名单主体（v1 无审批通道）；白名单外 → 加摩擦
    // 不可逆动作：v1 规则 = 只允许 irreversible_actors 白名单里的主体（通常是主人）。
    // 故"加摩擦"这一格必须用**白名单外**的主体来测——用主人测会得到 Allow（2026-09-26 改）。
    let err = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("ledger.compact", "do", "r-10b", json!({})),
        )
        .unwrap_err();
    assert!(err.contains("门禁加摩擦"), "应加摩擦，实得: {err}");
    assert!(
        err.contains("没有审批通道"),
        "理由必须明说 v1 无审批通道（DEBT-07）：{err}"
    );

    // 白名单外的主体 → 拒绝
    let err = w
        .commit(
            "act",
            "world://stranger",
            event::act_body("notice.mute", "do", "r-10c", json!({})),
        )
        .unwrap_err();
    assert!(err.contains("门禁拒绝"), "白名单外应被拒，实得: {err}");
    assert!(
        err.contains("不在门禁白名单内"),
        "理由应指明白名单，实得: {err}"
    );

    // 三次尝试：1 条 act + 2 条 notice
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 3, "实得 {} 条：{all:?}", all.len());
    assert_eq!(all[1]["body"]["type"], json!("gate.awaiting-approval"));
    assert_eq!(all[2]["body"]["type"], json!("gate.rejected"));
}

/// **AC-05 之三：改配置失败（静态墙）**——规则所在之处，被管者不得能写。
///
/// 一个"能被改掉的法律"不是法律。故 `policy.json` 若对 group/other 可写，
/// 世界核心**拒绝启动**。目录可写同样致命（文件权限挡不住"删掉再放一个新的"）。
#[cfg(unix)]
#[test]
fn t11_world_refuses_to_start_when_law_is_writable_by_others() {
    use std::os::unix::fs::PermissionsExt;

    let d = tmpdir("t11");
    let lp = d.join("ledger.jsonl");
    let pol = d.join("src/gate/policy.json");
    fs::copy(policy(), &pol).unwrap();
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();

    // 基线：0644 应当能启动
    fs::set_permissions(&pol, fs::Permissions::from_mode(0o644)).unwrap();
    assert!(
        World::open(&ontology(), &lp, &pol).is_ok(),
        "0644 的策略不应阻止启动"
    );

    // 文件对 group/other 可写 → 拒绝启动
    fs::set_permissions(&pol, fs::Permissions::from_mode(0o666)).unwrap();
    let e = World::open(&ontology(), &lp, &pol).unwrap_err();
    assert!(e.contains("不可绕过检查未通过"), "实得: {e}");
    assert!(e.contains("对 group/other 可写"), "实得: {e}");

    // 文件恢复干净，但**目录**对 other 可写 → 仍拒绝（可被整体替换）
    fs::set_permissions(&pol, fs::Permissions::from_mode(0o644)).unwrap();
    fs::set_permissions(&d, fs::Permissions::from_mode(0o707)).unwrap();
    let e = World::open(&ontology(), &lp, &pol).unwrap_err();
    assert!(e.contains("所在目录"), "实得: {e}");

    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
}

/// **AC-05 之四：账本不受被管者写入**（真相之墙；与法律之墙同理）。
#[cfg(unix)]
#[test]
fn t12_world_refuses_start_when_ledger_is_writable_by_others() {
    use std::os::unix::fs::PermissionsExt;

    let d = tmpdir("t12");
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    let lp = d.join("ledger.jsonl");
    fs::write(&lp, "").unwrap();
    fs::set_permissions(&lp, fs::Permissions::from_mode(0o666)).unwrap();

    let e = World::open(&ontology(), &lp, &policy()).unwrap_err();
    assert!(e.contains("账本（真相）"), "实得: {e}");
    assert!(e.contains("对 group/other 可写"), "实得: {e}");

    fs::set_permissions(&lp, fs::Permissions::from_mode(0o600)).unwrap();
    assert!(
        World::open(&ontology(), &lp, &policy()).is_ok(),
        "0600 的账本应当能启动"
    );
}

/// **AC-05 之五：运行中改策略不生效**（消除"运行中改规则"的窗口）。
///
/// 策略在启动时一次读入内存、之后不重读。因此把磁盘上的 `policy.json`
/// 改成"什么都允许"，**对已经运行的世界没有任何影响**——
/// 要生效必须重启，而重启会重新过一遍静态墙与加载校验。
#[test]
fn t13_running_world_does_not_reread_policy() {
    let d = tmpdir("t13");
    let lp = d.join("ledger.jsonl");
    let pol = d.join("src/gate/policy.json");
    fs::copy(policy(), &pol).unwrap();

    let mut w = World::open(&ontology(), &lp, &pol).unwrap();

    // 把磁盘上的策略改成"允许一切"（攻击者的做法）
    let tampered = json!({
        "policy": 1,
        "capabilities": { "world.hack": { "reversible": true } },
        "subjects": { "allow": ["*"] }
    });
    fs::write(&pol, serde_json::to_string_pretty(&tampered).unwrap()).unwrap();

    // 已运行的世界仍然拒绝：内存里那份策略没有变
    let err = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("world.hack", "do", "r-13", json!({})),
        )
        .unwrap_err();
    assert!(
        err.contains("未在门禁策略中声明"),
        "运行中改策略不得生效，实得: {err}"
    );
}

// ────────────────── 回滚：追加补偿事件（REQ-F-014）──────────────────

/// **回滚 = 追加补偿事件**，不是修改或删除历史。
///
/// 纯事件溯源里"撤销"根本不存在——存在的只是"再做一件把状态带回原处的事"。
/// 三条判据一起断言：
/// 1. 补偿后状态回到目标值；
/// 2. 账本**只增不减**（原事件还在，历史不可改）；
/// 3. 折叠仍可重算一致（补偿事件只是一条普通 `change`，读模型无需特殊逻辑）。
#[test]
fn t17_rollback_is_an_appended_compensating_event() {
    let d = tmpdir("t17");
    let lp = d.join("ledger.jsonl");
    let subj = "world://notice/n-1";

    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
    // ① 正着做一次：false → true
    w.commit(
        "change",
        "world://user",
        event::change_body(subj, "muted", json!(false), json!(true)),
    )
    .unwrap();
    assert_eq!(
        w.read_model().unwrap().get(subj, "muted"),
        Some(&json!(true))
    );

    // ② 回滚：追加一条**补偿事件**（旧值/新值互换）
    w.commit(
        "change",
        "world://user",
        event::change_body(subj, "muted", json!(true), json!(false)),
    )
    .unwrap();

    // 判据 1：状态回到原处
    let s = w.read_model().unwrap();
    assert_eq!(
        s.get(subj, "muted"),
        Some(&json!(false)),
        "补偿后状态应回到 false"
    );

    // 判据 2：账本只增不减——两条事件都在，历史未被改写
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 2, "回滚必须留下两条事件，而不是抹掉一条");
    assert_eq!(all[0]["body"]["after"], json!(true), "原事件必须原样保留");
    assert_eq!(
        all[1]["body"]["after"],
        json!(false),
        "补偿事件本身就是一条普通 change"
    );
    assert_eq!(s.seen(), 2);

    // 判据 3：重算一致（读模型对回滚无需任何特殊分支）
    let recomputed = world_core::ontology_instance::readmodel::State::fold(&w.ledger().read_all().unwrap()).unwrap();
    assert_eq!(recomputed.to_json().to_string(), s.to_json().to_string());
}

// ────────────────── 项目 Step 7/8：两个投影（M06/M07，REQ-F-018~020）──────────────────
/// 造一个有多主体、多字段的小世界，供投影测试共用。
fn seed_world(d: &std::path::Path) -> (PathBuf, PathBuf) {
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
        )
        .unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-2", "muted", json!(null), json!(false)),
        )
        .unwrap();
        w.commit(
            "act",
            "world://agent/1",
            event::act_body("notice.mute", "do", "r-700", json!({})),
        )
        .unwrap();
    }
    (lp, d.join("src/gate/policy.json"))
}

/// **语言投影（`M06`）**：结构化出口必须与读模型**逐项一致**，且可被程序解析回来。
#[test]
fn t14_language_projection_matches_read_model() {
    use world_core::gui_projection::language;

    let d = tmpdir("t14");
    let (lp, _) = seed_world(&d);
    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let state = w.read_model().unwrap();
    let text = language::render(&state, w.ontology().world(), w.ontology().vocab_hash());

    // ① 首行是同源头，且带上了词表身份
    assert!(text.starts_with("#world-core projection=language "));
    assert!(
        text.contains(w.ontology().vocab_hash()),
        "语言投影必须声明词表身份"
    );

    // ② 解析回来必须与读模型**逐项相等**（不是"看起来一样"）
    let parsed = language::parse(&text).unwrap();
    let expected: Vec<(String, String, serde_json::Value)> = state
        .entries()
        .map(|(s, p, v)| (s.to_string(), p.to_string(), v.clone()))
        .collect();
    assert_eq!(parsed, expected, "语言投影与读模型必须逐项一致");

    // ③ 纯文本（REQ-N-001）：没有控制字符（除换行），是合法 UTF-8
    assert!(
        text.chars().all(|c| c == '\n' || !c.is_control()),
        "投影必须是纯文本，不得含控制字符"
    );
}

/// **视觉投影（`M07`）**：给人看的，但**也必须能被机器核对**——否则"同源"无法证明。
#[test]
fn t15_visual_projection_is_human_readable_yet_auditable() {
    use world_core::gui_projection::visual;

    let d = tmpdir("t15");
    let (lp, _) = seed_world(&d);
    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let state = w.read_model().unwrap();
    let text = visual::render(&state, w.ontology().world(), w.ontology().vocab_hash());

    // ① 人看得懂：有标题、有分隔线、有主体名
    assert!(text.contains("世界状态（视觉投影）"));
    assert!(text.contains("────────────────"));
    assert!(text.contains("  world://notice/n-1"), "主体应缩进成行");
    assert!(text.contains("      muted = true"), "字段应可读");

    // ② 机器核得动：解析回来与读模型逐项一致
    let parsed = visual::parse(&text).unwrap();
    let expected: Vec<(String, String, serde_json::Value)> = state
        .entries()
        .map(|(s, p, v)| (s.to_string(), p.to_string(), v.clone()))
        .collect();
    assert_eq!(parsed, expected, "视觉投影与读模型必须逐项一致");
}

/// ★ **同源（REQ-F-020）**：两投影必须互相证明，且**换词表能被检出**。
///
/// 四件事一起断言，缺一条"同源"就只是口号：
/// 1. 同一状态 + 同一词表 ⇒ 同源判定**通过**；
/// 2. 两投影对同一 `(主体, 路径)` 给出的值**完全相同**；
/// 3. 换一份词表 ⇒ 同源判定**失败**，且错误明确指出是词表不同；
/// 4. 一方落后一个事件 ⇒ 同源判定**失败**（状态不同）。
#[test]
fn t16_two_projections_are_same_source_and_vocab_change_is_detected() {
    use world_core::gui_projection::{self, language, visual};

    let d = tmpdir("t16");
    let (lp, pol_copy) = seed_world(&d);
    fs::copy(policy(), &pol_copy).unwrap();
    let w = World::open(&ontology(), &lp, &pol_copy).unwrap();
    let state = w.read_model().unwrap();
    let (world, vocab) = (w.ontology().world(), w.ontology().vocab_hash());

    let lang = language::render(&state, world, vocab);
    let vis = visual::render(&state, world, vocab);

    // 判据 1：同源
    assert!(
        project::assert_same_source(&lang, &vis).is_ok(),
        "同一读模型 + 同一词表必须判为同源"
    );

    // 判据 2：两投影的值必须一致（各自解析回来比对）
    let mut a = language::parse(&lang).unwrap();
    let mut b = visual::parse(&vis).unwrap();
    a.sort_by(|x, y| (&x.0, &x.1).cmp(&(&y.0, &y.1)));
    b.sort_by(|x, y| (&x.0, &x.1).cmp(&(&y.0, &y.1)));
    assert_eq!(a, b, "两投影对同一主体/字段必须给出相同的值");

    // 判据 3：换词表 ⇒ 必须检出
    let other_vocab = "fnv1a64:0000000000000000";
    let lang_other = language::render(&state, world, other_vocab);
    let e = project::assert_same_source(&lang_other, &vis).unwrap_err();
    assert!(e.contains("词表不同"), "换词表必须被检出，实得: {e}");

    // 判据 4：一方落后 ⇒ 必须检出
    let evs = w.ledger().read_all().unwrap();
    let behind = world_core::ontology_instance::readmodel::State::fold(&evs[..2]).unwrap();
    let vis_behind = visual::render(&behind, world, vocab);
    let e = project::assert_same_source(&lang, &vis_behind).unwrap_err();
    assert!(e.contains("状态不同"), "落后一方必须被检出，实得: {e}");

    // 判据 3 的真实版本：真的换一份本体文件 → 词表 hash 必须变
    //
    // ⚠️ **身份与读路径不是同一件事**（本批订正，原先这里写"两处讲的是同一条语义"——那句不成立）：
    //   · **身份**由 `concepts`（**非 `_` 键**）决定 —— 它参与 `vocab_hash`（`vocab_hash_of`
    //     递归剔除 `_` 开头的顶层键）；
    //   · **读路径**只认 `_objects`（`_` 键）—— 它**不**参与身份。
    //   ⇒ 只改 `_objects`：**身份不变、读到的语义变了**；只改 `concepts`：**读到的语义不变、身份变了**。
    //   这两个方向都**不是**本判据要验的东西（本判据验的是"换了词表语义 ⇒ hash 必变"），
    //   故本处**两处都改**，让"读到的语义"与"算出的身份"指向同一件事。
    //   ⚠️ 两者的一致性另有判据盯着：`Ontology::load` 的 `ext.world.Ontology.ConceptsDrift`
    //   （同名字段的类型声明必须逐字一致，不一致即拒启）——本批补的那一条就是为了不让
    //   这两处**各说各话**；本用例改完两处后，正是那条判据放行的形态。
    let alt = d.join("ontology-alt.json");
    let mut raw: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(ontology()).unwrap()).unwrap();
    raw["concepts"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
    raw["_objects"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
    fs::write(&alt, serde_json::to_string_pretty(&raw).unwrap()).unwrap();
    let alt_ont = world_core::ontology_definition::Ontology::load(&alt).unwrap();
    assert_ne!(
        alt_ont.vocab_hash(),
        vocab,
        "改了枚举取值就是改了词表语义，hash 必须变（否则换词表检不出来）"
    );

    // 而只改说明文字，不该变（避免假警报）
    let comment_only = d.join("ontology-comment.json");
    let mut raw2: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(ontology()).unwrap()).unwrap();
    raw2["_comment"] = json!("换了一段说明文字，语义没动");
    fs::write(&comment_only, serde_json::to_string_pretty(&raw2).unwrap()).unwrap();
    let c_ont = world_core::ontology_definition::Ontology::load(&comment_only).unwrap();
    assert_eq!(
        c_ont.vocab_hash(),
        vocab,
        "只改说明文字不该换词表——假警报会训练人忽略这个信号"
    );
}
