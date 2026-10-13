//! 面④（实例存储）的判据 —— ★ 每一条对着一条规矩；**先写会红反例**（红的是什么写在注释里）。
//!
//! 跑法（★ 宿主无 cargo，只能在 VM 上跑）：`cargo test -p aios-worldcore store`

use crate::core::types::{EventSeq, Reason, Registration, Who};

use super::{fold, Op, Store, NO_PREDECESSOR};

const ZHANG: &str = "world://user/zhang";

fn who() -> Who {
    Who::new(ZHANG)
}

fn reg(kind: &str, name: &str) -> Registration {
    let mut fields = serde_json::Map::new();
    fields.insert("name".to_string(), serde_json::json!(name));
    Registration::new(kind, fields)
}

fn seed() -> Store {
    let mut s = Store::new();
    s.create_as(&who(), "application:htop", reg("application", "htop"))
        .expect("首笔该成");
    s
}

/// ★★ 会红反例 1：**写＝只追加**。若 `create` 只是往一张表里塞（旧形状），
/// 序列上就没有这一行 ⇒ 红。
#[test]
fn t01_create_is_an_append_not_an_insert() {
    let s = seed();
    assert_eq!(s.rows().len(), 1, "一笔写 ⇒ 序列上正好一行");
    let row = &s.rows()[0];
    assert_eq!(row.seq, EventSeq(1), "序号由本面发，从 1 起");
    assert_eq!(row.op, Op::Create);
    assert_eq!(row.at_seq, NO_PREDECESSOR, "新立的一条没有前身");
    assert_eq!(row.who.name(), ZHANG, "「谁」要落在账上");
    assert_eq!(row.key, "application:htop");
    assert_eq!(s.count(), 1);
}

/// ★★ 会红反例 2：**折出来的是最后一版**。若折叠取第一版（或后写不覆盖）⇒ 红。
#[test]
fn t02_the_now_is_the_last_version() {
    let mut s = seed();
    s.update_as(&who(), "application:htop", reg("application", "htop-2"))
        .expect("更正在册的键该成");
    assert_eq!(s.rows().len(), 2, "旧版不动：新一版是追加的");
    assert_eq!(
        s.get("application:htop"),
        Some(&reg("application", "htop-2"))
    );
}

/// ★★ 会红反例 3：**删了还能查到 ⇒ 红**。
#[test]
fn t03_a_deleted_key_is_gone_from_now_but_still_on_the_ledger() {
    let mut s = seed();
    let created = s.rows()[0].seq;
    let buried = s
        .delete_as(&who(), "application:htop", "误装，撤回")
        .expect("立碑该成");
    assert_eq!(buried, EventSeq(2));
    assert_eq!(s.rows().len(), 2, "删是追加一笔，不是抹掉一行");
    assert_eq!(s.rows()[1].op, Op::Tombstone);
    assert_eq!(s.rows()[1].at_seq, created, "碑上写清哪一条被立了碑");
    assert_eq!(s.rows()[1].who.name(), ZHANG, "碑上写清谁立的");
    assert_eq!(s.rows()[1].note, "误装，撤回", "碑上写清为什么");
    assert!(s.get("application:htop").is_none(), "删了还能查到 ⇒ 红");
    assert_eq!(s.count(), 0, "折出来的是现状：已立碑的不算活着");
    assert_eq!(s.history_of("application:htop").len(), 2, "两笔都还在账上");
    assert_eq!(s.rows()[0].op, Op::Create, "第一行一字未动");
}

/// ★ 立碑之后还能再立（碑是历史里的一笔，不是「这键永久封死」）。
#[test]
fn t04_a_key_can_be_created_again_after_its_tombstone() {
    let mut s = seed();
    s.delete("application:htop").expect("旧口径的删该成");
    let again = s
        .create_as(&who(), "application:htop", reg("application", "htop-3"))
        .expect("立碑之后该能再立");
    assert_eq!(again, EventSeq(3), "★ 序号不复用");
    assert_eq!(s.rows().len(), 3);
    assert_eq!(s.count(), 1);
    assert_eq!(
        s.get("application:htop"),
        Some(&reg("application", "htop-3"))
    );
}

/// ★★ 会红反例 4：**被拒的写不落账**（若先落账再判 ⇒ 红）。
#[test]
fn t05_refused_writes_append_nothing() {
    let mut s = seed();
    let before = s.rows().len();

    let dup = s
        .create_as(&who(), "application:htop", reg("application", "again"))
        .expect_err("键已存在该拒");
    assert_eq!(
        dup.reason,
        Reason::DanglingRef {
            target: "application:htop".to_string()
        }
    );

    let absent = s
        .update_as(&who(), "application:nope", reg("application", "nope"))
        .expect_err("不在册的键改不动");
    assert_eq!(
        absent.reason,
        Reason::DanglingRef {
            target: "application:nope".to_string()
        }
    );

    let gone = s
        .delete_as(&who(), "application:nope", "本来就没有")
        .expect_err("不在册的键立不了碑");
    assert_eq!(
        gone.reason,
        Reason::DanglingRef {
            target: "application:nope".to_string()
        }
    );

    let no_reason = s
        .delete_as(&who(), "application:htop", "   ")
        .expect_err("碑上不写为什么该拒");
    assert_eq!(
        no_reason.reason,
        Reason::MissingField {
            field: "reason".to_string()
        }
    );

    assert_eq!(s.rows().len(), before, "四笔被拒 ⇒ 序列一行不长");
}

/// ★★ 会红反例 5：**现状是派生物**。若真身是那张表、序列只是影子 ⇒
/// 只拿序列重建的读法会与原件对不上 ⇒ 红。
#[test]
fn t06_the_now_is_a_disposable_projection_of_the_log() {
    let mut s = Store::new();
    s.create_as(&who(), "application:a", reg("application", "a"))
        .expect("首笔该成");
    s.create_as(&who(), "surface:omarchy", reg("surface", "omarchy"))
        .expect("首笔该成");
    s.update_as(&who(), "application:a", reg("application", "a2"))
        .expect("更正在册的键该成");
    s.delete_as(&who(), "surface:omarchy", "换界面")
        .expect("立碑该成");

    // ① 把现状整份丢掉（只拿序列重建）；② 重折 ⇒ 逐项一致。
    let rebuilt = Store::replay(s.rows());
    assert_eq!(rebuilt.keys(), s.keys());
    assert_eq!(rebuilt.count(), s.count());
    assert_eq!(rebuilt.get("application:a"), s.get("application:a"));
    assert_eq!(rebuilt.project(), s.project(), "由序列重折 ⇒ 逐项相同");
    // ③ 折是纯函数：同一份序列折两次相同。
    assert_eq!(fold(s.rows()), s.project());
    assert_eq!(s.count(), 1, "三笔写、一块碑 ⇒ 现状一条");
}

/// ★ 序号全局单增、**永不复用**（本体 `envelope.fields.seq` 逐字）。
#[test]
fn t07_seq_is_global_monotonic_and_never_reused() {
    let mut s = Store::new();
    s.create_as(&who(), "application:a", reg("application", "a"))
        .expect("首笔该成");
    s.delete_as(&who(), "application:a", "撤")
        .expect("立碑该成");
    s.create_as(&who(), "application:a", reg("application", "a-again"))
        .expect("立碑之后该能再立");
    let seqs: Vec<u64> = s.rows().iter().map(|r| r.seq.0).collect();
    assert_eq!(seqs, [1, 2, 3], "连号、升序、不复用");
    assert_eq!(s.last_write_seq("application:a"), Some(EventSeq(3)));
}

/// ★★ 会红反例 6：`count`／`search_by_kind`／`keys` 若读的是「一共写过几笔」
/// 而不折现状 ⇒ 红。
#[test]
fn t08_reads_fold_the_now_not_the_history() {
    let mut s = Store::new();
    s.create_as(&who(), "application:a", reg("application", "a"))
        .expect("首笔该成");
    s.create_as(&who(), "application:b", reg("application", "b"))
        .expect("首笔该成");
    s.create_as(&who(), "surface:s", reg("surface", "s"))
        .expect("首笔该成");
    s.delete_as(&who(), "application:b", "不用了")
        .expect("立碑该成");

    assert_eq!(s.count(), 2, "三笔写、一块碑 ⇒ 现状两条");
    assert_eq!(s.keys(), ["application:a", "surface:s"]);
    assert_eq!(s.search_by_kind("application"), ["application:a"]);
    assert_eq!(s.search_by_kind("surface"), ["surface:s"]);
    assert_eq!(s.rows().len(), 4, "历史四行，一行不少");
}

/// ★ 更正／立碑都要指得出**哪一条**（本体碑形第一样）。
#[test]
fn t09_update_and_tombstone_name_the_row_they_replace() {
    let mut s = seed();
    let first = s.rows()[0].seq;
    let amended = s
        .update_as(&who(), "application:htop", reg("application", "v2"))
        .expect("更正在册的键该成");
    assert_eq!(s.rows()[1].at_seq, first, "更正要对准被更正那条");
    assert_eq!(s.last_write_seq("application:htop"), Some(amended));

    let buried = s
        .delete_as(&who(), "application:htop", "撤")
        .expect("立碑该成");
    assert_eq!(s.rows()[2].at_seq, amended, "立碑要对准被立碑那条");
    assert_eq!(s.rows()[2].op, Op::Tombstone);
    assert_eq!(buried, EventSeq(3));
}
