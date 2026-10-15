//! 面④（实例存储）的判据 —— ★ 每一条对着一条规矩；**先写会红反例**（红的是什么写在注释里）。
//!
//! 跑法（★ 宿主无 cargo，只能在 VM 上跑）：cargo test -p aios-worldcore store
//! ★ **已跑过**（2026-10-15 · T-162）：VM `leap16`／cargo 1.98.0，
//! `CARGO_TARGET_DIR=/root/.ct-fs cargo test -p aios-worldcore --offline` ⇒ 本件 13 条**全绿**。
//! ★ 原写「本席没跑过」的那一句**对本笔的 head 已过期**，现改为上面的现取读数。

use crate::core::types::{EventSeq, Lifecycle, Reason, Registration, Who};

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

/// ★★ 会红反例 1：**写＝只追加**。若 create 只是往一张表里塞（旧形状），
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

/// ★ 序号全局单增、**永不复用**（本体 envelope.fields.seq 逐字）。
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

/// ★★ 会红反例 6：count／search_by_kind／keys 若读的是「一共写过几笔」
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

// ==== 新规矩（按类索引／现状指纹）—— 每条一条会红反例 ======================

/// ★★ 会红反例 7（**按类索引**）：更正**换了类** ⇒ 旧类桶里必须没有它。
/// 让它红的改法：折叠只往新桶加、忘了摘旧桶 ⇒ search_by_kind("application") 还给这一条 ⇒ 红。
#[test]
fn t10_the_kind_index_follows_a_kind_change() {
    let mut s = seed();
    s.update_as(&who(), "application:htop", reg("surface", "htop"))
        .expect("更正在册的键该成");
    assert!(
        s.search_by_kind("application").is_empty(),
        "旧类桶里不许留它"
    );
    assert_eq!(
        s.search_by_kind("surface"),
        ["application:htop"],
        "键不动，类变了"
    );
    assert_eq!(s.keys(), ["application:htop"]);
    assert_eq!(s.get("application:htop"), Some(&reg("surface", "htop")));
}

/// ★★ 会红反例 8（**现状指纹**）：指纹只认**现状**，不认「一共写过几笔」。
/// 让它红的改法：不给指纹（本用例编译不过）／把历史长度也算进指纹 ⇒ 第二段断言红。
#[test]
fn t11_the_fingerprint_is_the_now_not_the_history() {
    let mut a = Store::new();
    a.create_as(&who(), "application:x", reg("application", "x"))
        .expect("该成");
    a.delete_as(&who(), "application:x", "撤")
        .expect("立碑该成");

    let mut b = Store::new();
    b.create_as(&who(), "service:y", reg("service", "y"))
        .expect("该成");
    b.delete_as(&who(), "service:y", "撤").expect("立碑该成");

    assert_eq!(a.count(), 0);
    assert_eq!(
        a.project().fingerprint(),
        b.project().fingerprint(),
        "★ 两份序列内容不同、折出来的现状都是空 ⇒ 指纹相同"
    );

    // ★ 由序列重折（replay）⇒ 指纹逐字相同。
    let rebuilt = Store::replay(a.rows());
    assert_eq!(rebuilt.project().fingerprint(), a.project().fingerprint());

    // 现状一变 ⇒ 指纹就变（空现状 vs 活着一条）。
    let mut c = Store::new();
    c.create_as(&who(), "application:x", reg("application", "x"))
        .expect("该成");
    assert_ne!(c.project().fingerprint(), a.project().fingerprint());
}

/// 带分级的一封「信纸」（H08：本体 governance.markings.levels 三级闭集）。
fn reg_marked(kind: &str, name: &str, marking: &str) -> Registration {
    let mut fields = serde_json::Map::new();
    fields.insert("name".to_string(), serde_json::json!(name));
    fields.insert("marking".to_string(), serde_json::json!(marking));
    Registration::new(kind, fields)
}

/// ★★ 会红反例 9（H08 · 标记**不可降级**）：现行 `INTERNAL`、新一版写 `PUBLIC` ⇒ **必须拒**，
/// 且**原值一字不变**、**序列上也不许多一行**。
///
/// 依据（来源1-①.3 逐字）：「写口比较「新一版标记」与「现行那一版标记」，**降级 ⇒ 拒**，
/// 理由码 `worldcore.Refuse.MarkingDowngrade`（**照它的夹具形状**：拒、原值不变）」；
/// 级名闭集＝本体 `governance.markings.levels`（PUBLIC／INTERNAL／CONFIDENTIAL）。
///
/// 让它红的改法：去掉 `update_as` 里的降级检查 ⇒ `expect_err` 那一步红。
#[test]
fn t12_a_marking_downgrade_is_refused_and_the_value_stays() {
    let mut s = Store::new();
    s.create_as(
        &who(),
        "application:alpha",
        reg_marked("application", "alpha", "INTERNAL"),
    )
    .expect("首笔该成");

    let e = s
        .update_as(
            &who(),
            "application:alpha",
            reg_marked("application", "alpha", "PUBLIC"),
        )
        .expect_err("降级必须拒");

    assert_eq!(e.code(), "worldcore.Refuse.MarkingDowngrade");
    assert_eq!(
        s.get("application:alpha")
            .and_then(|r| r.get_str("marking")),
        Some("INTERNAL"),
        "被拒的那一笔不许动原值"
    );
    assert_eq!(s.rows().len(), 1, "被拒 ⇒ 序列上也不许多一行");
}

/// ★ 正控（同一条规矩的另一半）：**升格必须放行**（`INTERNAL → CONFIDENTIAL`）——
/// 若为了拦降级把升格也拦了，本用例红。
#[test]
fn t13_a_marking_upgrade_is_allowed() {
    let mut s = Store::new();
    s.create_as(
        &who(),
        "application:alpha",
        reg_marked("application", "alpha", "INTERNAL"),
    )
    .expect("首笔该成");
    s.update_as(
        &who(),
        "application:alpha",
        reg_marked("application", "alpha", "CONFIDENTIAL"),
    )
    .expect("升格该放行");
    assert_eq!(
        s.get("application:alpha")
            .and_then(|r| r.get_str("marking")),
        Some("CONFIDENTIAL")
    );
}

/// ★★ 会红反例 10（H04 **砖一 · CAS**）：期望的那一版**对不上** ⇒ **拒**，且**一处不留**。
///
/// 依据（`01_object_model.md:226` 逐字「Pointer moves use **atomic compare-and-swap** on
/// (pointer_id, expected_current_version_id)」；来源1-⑧.5 逐字「只先吃砖一（CAS 那一块，几乎零成本）」）。
/// 让它红的改法：去掉 `promote_as` 里的 expected 比对 ⇒ `expect_err` 那一步红。
#[test]
fn t14_a_promote_with_a_stale_expected_is_refused_and_nothing_lands() {
    let mut s = seed();
    let e = s
        .promote_as(
            &who(),
            "application:htop",
            EventSeq(7),
            reg("application", "htop-2"),
        )
        .expect_err("期望对不上必须拒");
    assert_eq!(e.code(), "worldcore.Refuse.ConflictDetected");
    assert_eq!(s.rows().len(), 1, "被拒的那一笔一处不留");
    assert_eq!(
        s.get("application:htop"),
        Some(&reg("application", "htop")),
        "现行一字不动"
    );
}

/// ★ 正控（同一条规矩的另一半）：期望**就是现行** ⇒ 放行，且**指针搬动**（现行 ＋ 上一版都指得出）。
#[test]
fn t15_a_promote_with_the_right_expected_moves_the_pointer() {
    let mut s = seed();
    let now = s.pointer_of("application:htop").expect("首版该有指针");
    assert_eq!(now.current, EventSeq(1));
    assert_eq!(now.previous, None, "首版没有上一版");
    let to = s
        .promote_as(
            &who(),
            "application:htop",
            now.current,
            reg("application", "htop-2"),
        )
        .expect("期望对上该成");
    assert_eq!(to, EventSeq(2));
    let moved = s.pointer_of("application:htop").expect("搬完该有指针");
    assert_eq!(moved.current, EventSeq(2));
    assert_eq!(moved.previous, Some(EventSeq(1)), "上一版指得出来");
}

/// ★★ 会红反例 11（H02 · **回滚搬的是指针，不是正文**）：搬到历史某一版 ⇒ 现状回到那一版，
/// ★ **历史一行不改**（只多一笔 Rollback）。
///
/// 依据（`00_overview.md:13` 逐字「rollback moves a pointer to a previous verified version」；
/// 来源2-A02 逐字「指针搬动只改指针那一栏，正文一行不改」）。
/// 让它红的改法：把回滚做成「再写一遍旧内容」⇒ 第三与第四条断言红（行的形状不对）。
#[test]
fn t16_a_rollback_moves_the_pointer_back_without_touching_the_rows() {
    let mut s = seed();
    let first = EventSeq(1);
    s.promote_as(
        &who(),
        "application:htop",
        first,
        reg("application", "htop-2"),
    )
    .expect("该成");
    assert_eq!(
        s.get("application:htop"),
        Some(&reg("application", "htop-2"))
    );
    let rows_before = s.rows().len();

    s.rollback_as(&who(), "application:htop", first, "那一版有毛病")
        .expect("回滚该成");

    assert_eq!(
        s.get("application:htop"),
        Some(&reg("application", "htop")),
        "现状回到旧那一版"
    );
    assert_eq!(
        s.rows().len(),
        rows_before + 1,
        "★ 只多一笔「指针搬动」，正文一行不加"
    );
    assert_eq!(s.rows()[rows_before].op, Op::Rollback);
    assert_eq!(
        s.pointer_history("application:htop"),
        [EventSeq(1), EventSeq(2), EventSeq(1)],
        "指针走过三个位次"
    );
}

/// ★★ 会红反例 12（H02 · 回滚**不许搬到一个不存在的地方**）：目标不在这个键的历史上 ⇒ 拒。
#[test]
fn t17_a_rollback_to_a_version_that_never_existed_is_refused() {
    let mut s = seed();
    let e = s
        .rollback_as(&who(), "application:htop", EventSeq(9), "乱指")
        .expect_err("那一版不存在 ⇒ 拒");
    assert_eq!(e.code(), "worldcore.Refuse.DanglingRef");
    assert_eq!(s.rows().len(), 1, "被拒的那一笔一处不留");
}

/// ★★ 会红反例 13（H07 · **生命周期**）：ACTIVE → 立碑 RETIRED → 清除 PURGED；
/// ★ 退役后 `get` 不给、**审计读仍给**；清除后**审计 stub 仍在**。
///
/// 依据（`01_object_model.md:77` 逐字「ACTIVE ───retire──▶ RETIRED ───purge_after_retention──▶ PURGED」；
/// 来源1-⑥.3 逐字「get() 默认只给 ACTIVE，get_including_retired() 给审计用」）。
#[test]
fn t18_the_lifecycle_is_active_then_retired_then_purged_and_the_stub_stays() {
    let mut s = seed();
    assert_eq!(s.lifecycle_of("application:htop"), Some(Lifecycle::Active));
    s.delete_as(&who(), "application:htop", "不用了")
        .expect("立碑该成");
    assert_eq!(s.lifecycle_of("application:htop"), Some(Lifecycle::Retired));
    assert_eq!(s.get("application:htop"), None, "退役 ⇒ 现状里没有它");
    assert_eq!(
        s.get_including_retired("application:htop"),
        Some(&reg("application", "htop")),
        "★ 审计读仍给"
    );
    s.purge_as(&who(), "application:htop", "保留期到")
        .expect("清除该成");
    assert_eq!(s.lifecycle_of("application:htop"), Some(Lifecycle::Purged));
    assert_eq!(
        s.get_including_retired("application:htop"),
        Some(&reg("application", "htop")),
        "★ stub 仍在（我们只追加）"
    );
}

/// ★★ 会红反例 14（H07 · **不许从 ACTIVE 直接清**）：先退役才谈得上清除。
#[test]
fn t19_a_purge_before_a_retire_is_refused() {
    let mut s = seed();
    let e = s
        .purge_as(&who(), "application:htop", "直接清")
        .expect_err("没退役不许清");
    assert_eq!(e.code(), "worldcore.Refuse.BadValue");
    assert_eq!(s.rows().len(), 1, "被拒的那一笔一处不留");
}

/// ★★ 会红反例 15（H05 · **快照一致读**）：折到某一个位次为止；★ 同一位置重折 ⇒ `fold_id` 逐字相同；
/// ★ 位次一变 ⇒ 名字就变（时间旅行读的是**那一刻**）。
///
/// 依据（`01_object_model.md:317` 逐字「SNAPSHOT ｜ Reads a consistent snapshot across pointers
/// as of the call's wall time」；来源1-③.3 四条：水位线／fold_id／project_at／一致性契约）。
#[test]
fn t20_a_snapshot_reads_one_moment_and_has_one_name() {
    let mut s = seed();
    let at1 = s.project_at(EventSeq(1));
    assert_eq!(at1.as_of(), EventSeq(1), "水位线 ＝ 折到哪儿");
    assert_eq!(
        at1.get("application:htop"),
        Some(&reg("application", "htop"))
    );
    let name1 = at1.fold_id();
    assert_eq!(
        name1,
        s.project_at(EventSeq(1)).fold_id(),
        "★ 同一位次重折 ⇒ 名字逐字相同"
    );
    s.update_as(&who(), "application:htop", reg("application", "htop-2"))
        .expect("该成");
    assert_eq!(
        s.project_at(EventSeq(1)).as_of(),
        EventSeq(1),
        "旧那一刻还在"
    );
    assert_eq!(
        s.project_at(EventSeq(1)).fold_id(),
        name1,
        "★ 后写不影响旧那一刻"
    );
    assert_ne!(
        s.project_at(EventSeq(2)).fold_id(),
        name1,
        "位次一变 ⇒ 名字就变"
    );
}
