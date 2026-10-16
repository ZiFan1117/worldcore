//! 面⑥账新规矩的**会红反例**（★ 本席写域内，不占 crates/aios-worldcore/tests/）。
//!
//! ★ **如实登记**：宿主**无 cargo** ⇒ 本席**没跑过**这些测试；「会红」是按旧实现推断的：
//!   旧 Ledger 只有正文一份，没有链节、没有 verify、没有二级索引 ⇒
//!   本文件里凡提到 seals／by_family／verify 的断言，在旧实现下**连编译都过不去**（那些名字不存在）。
//!
//! 每条新规矩一条：
//! - ① 创世 ＋ 逐笔接链 ⇒ chain_starts_at_genesis_and_every_seal_holds_the_previous
//! - ② 只追加、被拒不留账 ⇒ a_refused_append_touches_nothing ／ export_csv_is_append_only_...
//! - ③ 防篡改 ⇒ 三条 tampering_*
//! - ④ 数据怎么摆（位次取／族索引）⇒ get_reads_by_position... ／ family_index_is_append_ordered...
//! - 正控 ⇒ a_healthy_chain_verifies ／ an_empty_ledger_has_nothing_to_verify

use super::*;

use serde_json::{json, Map, Value};

/// 本体全文（族的权威清单从它现取）。
const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

fn ledger() -> Ledger {
    Ledger::load(ONT).expect("本体该装得上")
}

fn who() -> Who {
    Who::new("world://user/zhang")
}

fn params(pairs: &[(&str, Value)]) -> Map<String, Value> {
    let mut m = Map::new();
    for (k, v) in pairs {
        m.insert(String::from(*k), v.clone());
    }
    m
}

/// 装一本四笔的账（act／notice／change／job 各一）。
fn four() -> (Ledger, [EventSeq; 4]) {
    let mut l = ledger();
    let w = who();
    let a = l
        .append(
            &w,
            "act",
            "job.start",
            params(&[("subject", json!("application:htop"))]),
        )
        .expect("在册族该收下");
    let b = l
        .append(&w, "notice", "job.completed", Map::new())
        .expect("在册族该收下");
    let c = l
        .append(&w, "change", "application.register", Map::new())
        .expect("在册族该收下");
    let d = l
        .append(&w, "job", "job.finish", Map::new())
        .expect("在册族该收下");
    (l, [a, b, c, d])
}

/// ★ 正控：健康的链查得过，且链尾就落在最后一节上。
#[test]
fn a_healthy_chain_verifies() {
    let (l, want) = four();
    l.verify().expect("新账该是健康的");
    assert_eq!(want, [EventSeq(1), EventSeq(2), EventSeq(3), EventSeq(4)]);
    assert_eq!(l.seals.len(), 4, "正文一笔、链节一节");
    let tail = l.seals[3].hash();
    assert_eq!(
        l.head.as_deref(),
        Some(tail.as_str()),
        "链尾＝最后一节的封条"
    );
}

/// ★★ 反例③-e：**封条是 BLAKE3-256**（64 位小写十六进制）。
/// 让它红的改法：把封条退回 16 位短指纹、或截断成 32 位 ⇒ 本用例红。
#[test]
fn a_seal_is_a_full_length_blake3_hash() {
    let (l, _) = four();
    for seal in &l.seals {
        let h = seal.hash();
        assert_eq!(h.len(), 64, "BLAKE3-256 ⇒ 64 位十六进制");
        assert!(
            h.chars().all(|c| c.is_ascii_hexdigit()),
            "封条该是十六进制：{h}"
        );
    }
}

/// ★★ 反例③-a：**改动老账的正文** ⇒ 重算指纹对不上 ⇒ 指出**第一处**坏在第 2 笔。
/// 让它红的改法：verify 直接 Ok(())、只查链尾、或者报错不指位次。
#[test]
fn tampering_with_an_old_row_is_caught_at_its_own_position() {
    let (mut l, _) = four();
    l.rows[1].what = "job.completed.forged".to_string();
    let e = l.verify().expect_err("改过正文的账不能算健康");
    assert_eq!(e.code(), "worldcore.Refuse.BadValue");
    let why = &e.reason;
    let Reason::BadValue { field, .. } = why else {
        panic!("该报出位次，实际报的是 {why:?}");
    };
    assert_eq!(field.as_str(), "seal[1]");
}

/// ★★ 反例③-b：**改动参数**也是改动正文（封条压整笔，不只压「做了什么」那一格）。
#[test]
fn tampering_with_a_param_is_caught_too() {
    let (mut l, _) = four();
    if let Some(v) = l.rows[0].params.get_mut("subject") {
        *v = json!("application:forged");
    }
    let e = l.verify().expect_err("参数被改过，也不算健康");
    let why = &e.reason;
    let Reason::BadValue { field, .. } = why else {
        panic!("该报 seal[0]，实际 {why:?}");
    };
    assert_eq!(field.as_str(), "seal[0]");
}

/// ★★ 反例③-c：**改动链节**（把某节的「前驱」换掉）⇒ 断链，报在那一节的 .prev 上。
#[test]
fn tampering_with_a_link_is_caught() {
    let (mut l, _) = four();
    l.seals[2].prev = Some("f".repeat(64));
    let e = l.verify().expect_err("接错前驱不能算健康");
    let why = &e.reason;
    let Reason::BadValue { field, .. } = why else {
        panic!("该报 seal[2].prev，实际 {why:?}");
    };
    assert_eq!(field.as_str(), "seal[2].prev");
}

/// ★ 反例③-d：**空账不是「健康」**——没有链节可查，得单独报（学它把空链与健康链分开）。
#[test]
fn an_empty_ledger_has_nothing_to_verify() {
    let l = ledger();
    let e = l.verify().expect_err("空账不该报绿");
    assert_eq!(
        e.reason,
        Reason::MissingField {
            field: "seal".to_string()
        }
    );
}

/// ★★ 反例①：**创世 ＋ 逐笔接链**。
/// 让它红的改法：每节都不接前驱（prev 恒 None）、或者接的不是上一节。
#[test]
fn chain_starts_at_genesis_and_every_seal_holds_the_previous() {
    let (l, _) = four();
    assert!(l.seals[0].prev.is_none(), "第一笔是创世：没有前驱");
    for (i, pair) in l.seals.windows(2).enumerate() {
        let want = pair[0].hash();
        assert_eq!(
            pair[1].prev.as_deref(),
            Some(want.as_str()),
            "第 {} 节该接住第 {i} 节",
            i + 1
        );
    }
}

/// ★★ 反例②：**被拒的那一笔不许动账**（先判族、后落账；链尾／链节／索引一处都不许动）。
#[test]
fn a_refused_append_touches_nothing() {
    let (mut l, _) = four();
    let before_head = l.head.clone();
    let before_index = l.by_family.keys.len();
    let refused = l
        .append(&who(), "frobnicator", "x", Map::new())
        .expect_err("四族之外的族必须拒");
    assert_eq!(refused.code(), "worldcore.Refuse.BadValue");
    assert_eq!(l.all().len(), 4, "被拒的那笔不许进正文");
    assert_eq!(l.seals.len(), 4, "也不许留链节");
    assert_eq!(l.head, before_head, "链尾不许动");
    assert_eq!(l.by_family.keys.len(), before_index, "索引不许动");
    l.verify().expect("拒一笔之后，链还是健康的");
}

/// ★★ 反例④-a：**按位次取**（学它 chain_index：序号直接算位次，不瞎扫）；序号 0 不存在。
#[test]
fn get_reads_by_position_not_by_guess() {
    let (l, [s1, s2, ..]) = four();
    assert!(l.get(EventSeq(0)).is_none(), "序号从 1 起，0 不存在");
    assert!(l.get(EventSeq(99)).is_none(), "越界不许瞎给一笔");
    assert_eq!(l.get(s1).expect("该取得回").seq, s1);
    assert!(
        std::ptr::eq(l.get(s2).expect("该取得回"), &l.all()[1]),
        "★ 第 2 笔就该是正文里位次 1 的那一笔（同一个对象）"
    );
}

/// ★★ 反例④-b：**族内按序号升序**、**索引与正文对得上**、**没有的族不许全收**。
#[test]
fn family_index_is_append_ordered_and_does_not_invent_families() {
    let (l, [s1, s2, s3, s4]) = four();
    assert!(l.query_family("frobnicator").is_empty(), "没有的族 ⇒ 空");
    assert_eq!(l.query_family("act")[0].seq, s1);
    assert_eq!(l.query_family("notice")[0].seq, s2);
    assert_eq!(l.query_family("change")[0].seq, s3);
    assert_eq!(l.query_family("job")[0].seq, s4);
    assert_eq!(
        l.by_family.keys.len(),
        l.all().len(),
        "索引行数 ＝ 正文笔数"
    );
    // 再补一笔同族：同族的序号必须还是升序。
    let mut l = l;
    let later = l
        .append(&who(), "act", "job.stop", Map::new())
        .expect("在册族该收下");
    let acts: Vec<EventSeq> = l.query_family("act").iter().map(|e| e.seq).collect();
    assert_eq!(acts, vec![s1, later], "★ 族内按追加序");
}

/// ★★ 反例②-b：**只追加**：后加的笔不许改动前面的导出（老账原样、表头逐字）。
#[test]
fn export_csv_is_append_only_and_keeps_the_header() {
    let (mut l, _) = four();
    let before = l.export_csv();
    l.append(&who(), "act", "job.stop", Map::new())
        .expect("在册族该收下");
    let after = l.export_csv();
    assert!(after.starts_with(&before), "★ 只追加：老账必须原样在前");
    let lines: Vec<&str> = after.lines().collect();
    assert_eq!(lines[0], "seq,who,family,what");
    assert_eq!(lines.len(), 6, "表头 ＋ 5 笔");
    assert!(lines[1].starts_with("1,world://user/zhang,act,job.start"));
}

// ===================== ★ T-242 批零：**账落盘**（会红反例）=====================
//
// ★ 三条（★ 甲席在评审里给的形状：**库级两步、不需 kill** —— 载体 A 是库，没有进程可 kill）：
//   ① 写一笔 ⇒ **丢开这本账** ⇒ **重开** ⇒ 那一笔**还在**；
//   ② **手改盘上正文一处** ⇒ 重开 ⇒ **整本拒**（★ 不许静默跳过那一行）；
//   ③ 重开后**序号从水位续上**（★ 书：「通知可以漏，序号不会漏」）。
//
// ★ 会红：旧实现里 `load` 只给空账（`ledger.rs:69-75`）⇒ ①③ 必红；
//   ★ 落盘但**不落封条**的实现在 ② 上必红（重算链 ⇒ 篡改不可察）。

fn temp_path(tag: &str) -> String {
    let p = std::env::temp_dir().join(format!("worldcore-ledger-{tag}.jsonl"));
    let _ = std::fs::remove_file(&p);
    p.to_string_lossy().to_string()
}

#[test]
fn account_survives_a_reopen() {
    let path = temp_path("reopen");
    {
        let mut l = ledger();
        l.append_persisting(
            &path,
            &who(),
            "notice",
            "notice.mute",
            params(&[("subject", json!("notice"))]),
        )
        .expect("第一笔该写得下去");
    } // ★ 丢开这本账（相当于进程停了）
    let back = Ledger::load_file(ONT, &path).expect("从盘上该装得回来");
    assert_eq!(
        back.all().len(),
        1,
        "★ 那一笔必须在（落盘的意义就在这一条）"
    );
    assert_eq!(back.all()[0].what, "notice.mute");
    assert!(back.verify().is_ok(), "读回来的链必须是健康的");
    let _ = std::fs::remove_file(&path);
}

#[test]
fn tampered_line_is_refused_on_reopen() {
    let path = temp_path("tamper");
    {
        let mut l = ledger();
        l.append_persisting(
            &path,
            &who(),
            "notice",
            "notice.mute",
            params(&[("subject", json!("notice"))]),
        )
        .expect("第一笔该写得下去");
    }
    // ★ 手改盘上正文一处（把 what 改掉）—— 封条是【当时的】，改一个字就对不上。
    let body = std::fs::read_to_string(&path).expect("该读得到");
    let bad = body.replace("notice.mute", "notice.UNMUTE");
    std::fs::write(&path, bad).expect("该写得下去");
    let got = Ledger::load_file(ONT, &path);
    assert!(got.is_err(), "★ 被改过的账【整本拒】，不许静默跳过那一行");
    let _ = std::fs::remove_file(&path);
}

#[test]
fn appended_seq_continues_after_reopen() {
    let path = temp_path("seq");
    {
        let mut l = ledger();
        l.append_persisting(&path, &who(), "notice", "notice.mute", params(&[]))
            .expect("第一笔");
        l.append_persisting(&path, &who(), "job", "job.start", params(&[]))
            .expect("第二笔");
    }
    let mut back = Ledger::load_file(ONT, &path).expect("该装得回来");
    assert_eq!(back.all().len(), 2);
    let third = back
        .append_persisting(&path, &who(), "notice", "notice.unmute", params(&[]))
        .expect("第三笔该写得下去");
    assert_eq!(
        third.0, 3,
        "★ 序号要从【水位】续上，不许又从 1 开始（书：序号不会漏）"
    );
    assert!(back.verify().is_ok());
    let _ = std::fs::remove_file(&path);
}
