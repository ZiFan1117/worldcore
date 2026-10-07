//! **每个实例必须指回定义面**（书 §5.3 的**读侧**那一半）。
//!
//! ## 这一格原来红在哪（实测，不是推的）
//!
//! **写侧**早有执行体（`Ontology::check_concepts` 的 `UndeclaredEntity`），**读侧没有**：
//! 拿真二进制跑过两遍（那两次读数落在 `语义世界-架构\证据-本体-2026-10-05.md`）——
//!
//! | 侧 | 命令 | 结局 |
//! |---|---|---|
//! | 写 | `world-core … append change '{"subject":"world://never-declared-entity/42", …}'` | **rc=2**、点名 `ext.world.Ontology.UndeclaredEntity`、**账本 0 字节** |
//! | 读 | 把**同一行**直接放进账本（＝恢复／迁移／手工修复那三条路）后 `state --json` | **rc=0**，且 `objects` 里**就有那个主体** |
//!
//! ⇒ **同一本账、同一件事，读写两侧给了两个答案**（"同一个事实两个答案"）。
//! 本文件把"读侧"那一半补成**会红的断言**，并配正控（见下）。
//!
//! ## 每条断言的"会红"条件（改坏哪一行 ⇒ 打红哪一条）
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `i01`／`i02` | `readmodel::State::fold_declared` 里那段"逐主体判类型段"**整段删掉／注掉** ⇒ 两条一起变红（违规又能折进状态） |
//! | `i01`／`i02` | `src/lib.rs::read_model` 里 `.with_declared_entities(…)` **这一行删掉** ⇒ 这一半**没接** ⇒ 两条一起变红（**接线点**自断言） |
//! | `i03`／`i04`／`i05`／`i06` | 把判据改成"什么都拒"（例：`declared` 直接当空集用、或裸主体也判）⇒ 四条里对应的那条变红（**防"因为什么都拒"而通过**） |
//! | `i07` | 把 `declared.is_empty()` 那段"空表即拒"改成默默放行 ⇒ `i07` 变红 |
//! | `i08` | 把"`None`（没接）⇒ 不判"改成"`None` 也判" ⇒ 既有直接装配点（`DeclaredCells::new`）当场被误拒 ⇒ `i08` 变红 |
//!
//! ## 射程（如实声明，不许读成更宽）
//!
//! - 只判**有字段写进去**的主体；**裸主体不判**（`world://<名字>` 不是实例引用，
//!   见 `scripts/test/atom_declared_only.rs::b04` 那条**已登记缺口**——本文件不顺手收紧它）；
//! - **不判身份**（`actor`／`to`）：它们不是对象实例；
//! - **不判实例名唯一性**（登记在 `ontology.json` 的 `_pending_tables.identity_and_naming`）；
//! - **不判"内嵌形态对不对"**：四段形态里第 3 段**不是**按 `part_of` 声明的内嵌类型时，
//!   本层退回首段（与 `Ontology::entity_of` 同口径）；"错内嵌形态"由**写侧**
//!   （`UndeclaredEmbeddedMarker`）判——**本层不抢它的错**；
//! - **不判定义面**（"定义面里不许出现实例数据"是另一条，落点在 `src/ontology_definition/mod.rs`）。

use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::ontology_definition::Ontology;
use world_core::ontology_instance::readmodel::{DeclaredCells, State};
use world_core::{common::event, World};

// ────────────────────────── 夹具 ──────────────────────────

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-ontinst-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

#[cfg(unix)]
fn chmod600(p: &Path) {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(p, fs::Permissions::from_mode(0o600)).unwrap();
}

#[cfg(not(unix))]
fn chmod600(_p: &Path) {}

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn factory_ontology() -> PathBuf {
    manifest_dir().join("src/ontology_definition/ontology.json")
}

fn factory_policy() -> PathBuf {
    manifest_dir().join("src/gate/policy.json")
}

/// 造一份临时本体：读出厂本体 → 按 `edit` 改 → 落盘（`0600`，静态墙要求）。
fn write_ontology(dir: &Path, name: &str, edit: impl FnOnce(&mut Value)) -> PathBuf {
    let text = fs::read_to_string(factory_ontology()).unwrap();
    let mut v: Value = serde_json::from_str(&text).unwrap();
    edit(&mut v);
    let p = dir.join(name);
    let body = serde_json::to_string_pretty(&v).unwrap();
    fs::write(&p, format!("{body}\n")).unwrap();
    chmod600(&p);
    p
}

/// **照装配处的体例**把法律递成纯数据（与 `src/lib.rs::read_model` 同一行口径）。
fn cells_for(ont: &Ontology) -> DeclaredCells {
    DeclaredCells::new(ont.envelope_required(), ont.family_required())
        .with_instance_limits(ont.instance_limits())
        .with_declared_entities(
            ont.known_entities()
                .into_iter()
                .map(str::to_string)
                .collect(),
            ont.nested_types(),
        )
}

/// 落一本**真账本**（走唯一写入口），返回它的行。`subject`／`path` 由调用方给。
fn ledger_with(dir: &Path, tag: &str, subject: &str, path: &str) -> Vec<Value> {
    let lp = dir.join(format!("{tag}.jsonl"));
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    w.commit(
        "change",
        "world://user",
        event::change_body(subject, path, json!(null), json!(true)),
    )
    .unwrap();
    w.ledger().read_all().unwrap()
}

// ────────────── 反例：实例的类型段没在定义面里 ──────────────

/// **i01（反例 A，端到端）**：出厂本体写一本账 ⇒ 换一本**不声明该类型**的法律读**同一本账** ⇒ **拒**。
///
/// 这条同时是**接线点自断言**：`src/lib.rs::read_model` 里 `.with_declared_entities(…)`
/// 那一行若删掉，本断言当场变红（读侧不判 ⇒ 我们又回到"违规被读成正常"）。
#[test]
fn i01_an_instance_whose_type_is_not_declared_is_refused_by_the_read_side() {
    let dir = tmpdir("i01");
    // ① 用**出厂本体**写一条 `presence` 的实例（`presence` 在 `_objects` 里声明过）。
    let lp = dir.join("ledger.jsonl");
    {
        let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://presence/oi-1", "name", json!(null), json!("oi")),
        )
        .unwrap();
        assert!(w.read_model().is_ok(), "正控：出厂本体读自己的账本必须绿");
    }
    // ② 造本体 B ＝ 出厂本体**删掉 `presence` 的类型声明**（`_objects` 与 `concepts` 两处；
    //    能力/动作/许可一字不动）。★ **关系那一节也要跟着挪**——`_links` 里凡引用
    //    `presence` 的关系（如 `runs-on`）必须一并去掉，否则装载器以
    //    `ext.world.Ontology.UndeclaredRelationEndpoint` **拒启** ⇒ **本反例就空了**
    //    （实测撞到过）。★ 关系的端点完整性是**装载器**判的（`ontology.rs`），不是读侧；
    //    本反例要证的是**读侧**（`with_declared_entities`）那根线，故只清掉挡路的关系，
    //    **判据一字未改**。
    let ont_b = write_ontology(&dir, "no-presence.json", |v| {
        v["_objects"].as_object_mut().unwrap().remove("presence");
        v["concepts"].as_object_mut().unwrap().remove("presence");
        if let Some(ls) = v["_links"].as_object_mut() {
            ls.retain(|_, r| {
                let f = r.get("from").and_then(|x| x.as_str()).unwrap_or("");
                let t = r.get("to").and_then(|x| x.as_str()).unwrap_or("");
                f != "presence" && t != "presence"
            });
        }
    });
    let ont = Ontology::load(&ont_b).expect("本体 B 必须能开（否则本反例是空的）");
    assert!(
        !ont.known_entities().contains(&"presence"),
        "夹具：本体 B 里 `presence` 必须已不在实体表里"
    );

    // ③ 用本体 B 读**同一本账** ⇒ 必须拒，且**点名类型与主体**。
    let w = World::open(&ont_b, &lp, &factory_policy()).expect("起得来（法律合法，是账本违规）");
    let e = w
        .read_model()
        .expect_err("读侧必须拒：这个实例的类型段指不回定义面");
    assert!(
        e.contains("ext.world.ReadModel.EntityNotDeclared"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("`presence`"),
        "理由必须**点名**那个类型段，实得：{e}"
    );
    assert!(
        e.contains("world://presence/oi-1"),
        "理由必须**点名**那个主体，实得：{e}"
    );
}

/// **i02（反例 B：恢复／迁移／手工修复那一行的真形态）**：账本里有一行未声明实体 ⇒ **拒**。
///
/// ⚠️ **射程**：本条走 `State::fold_declared`（不经 `World::open`）——
/// 因为"无 `chain` 的手造账本"会被**另一条判据**挡下（`ext.world.Ledger.NoChain`），
/// 那是**账本完整性**那一族的事，**本用例不冒充它**。
/// 行的**模板取自真账本**（先经唯一写入口落一条，再把它的主体名与字段名改掉），
/// 这正是"手工修复／恢复"之后账本里那一行长什么样。
#[test]
fn i02_a_recovered_ledger_line_with_an_undeclared_entity_is_refused() {
    let dir = tmpdir("i02");
    let mut evs = ledger_with(&dir, "base", "world://notice/n-1", "muted");
    evs[0]["body"]["subject"] = json!("world://never-declared-entity/42");
    evs[0]["body"]["path"] = json!("never_declared_field");

    let ont = Ontology::load(&factory_ontology()).unwrap();
    let e = State::fold_declared(&cells_for(&ont), &evs)
        .expect_err("读侧必须拒：这一行的实体从未在出厂本体里声明过");
    assert!(
        e.contains("ext.world.ReadModel.EntityNotDeclared"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("world://never-declared-entity/42") && e.contains("`never-declared-entity`"),
        "理由要点名**主体**与那个**类型段**，实得：{e}"
    );
    // ⚠️ **射程**：本判据只判**类型段**，所以它**不**点名"哪一格"（那一格是**写侧**
    //    `UndeclaredField` 的事）。拿"少了字段名"判本判据红，是把两条判据搅成一条。
    assert!(
        !e.contains("ext.world.Ontology.UndeclaredField"),
        "本判据不冒充写侧那一格，实得：{e}"
    );
    assert!(
        e.contains("notice") && e.contains("presence"),
        "理由要顺带说出**已声明的类型**（否则只说了不行、没说怎么办），实得：{e}"
    );
}

// ────────────── 正控：不许"什么都拒" ──────────────

/// **i03（正控 ⓐ）**：出厂本体 ＋ 出厂形态账本 ⇒ **必须绿**，且状态里真读得到那一格。
#[test]
fn i03_declared_instances_still_fold() {
    let dir = tmpdir("i03");
    let evs = ledger_with(&dir, "base", "world://notice/n-1", "muted");
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let s = State::fold_declared(&cells_for(&ont), &evs).expect("已声明的实例必须照常折");
    assert_eq!(
        s.get("world://notice/n-1", "muted"),
        Some(&json!(true)),
        "折出来的状态里必须有那一格（否则'绿'是空转的）"
    );
}

/// **i04（正控 ⓑ）**：**只加**扩展（往 `_objects` 加一个类型）后用新法律读**旧账** ⇒ **必须绿**。
///
/// 「法律的本分是先声明、后使用」——纯加法不许把旧账本打红。
#[test]
fn i04_pure_extension_still_reads_the_old_ledger() {
    let dir = tmpdir("i04");
    let evs = ledger_with(&dir, "base", "world://notice/n-1", "muted");
    let ext = write_ontology(&dir, "ext.json", |v| {
        v["_objects"]["audit"] =
            json!({ "fields": { "result": "string" }, "instance_mode": "many" });
    });
    let ont = Ontology::load(&ext).unwrap();
    assert!(
        ont.known_entities().contains(&"audit"),
        "夹具：新类型必须真被读到"
    );
    let s = State::fold_declared(&cells_for(&ont), &evs).expect("纯加法读旧账必须绿");
    assert_eq!(s.get("world://notice/n-1", "muted"), Some(&json!(true)));
}

/// **i05（正控 ⓒ）**：**裸主体**（`world://s`）⇒ **必须绿**（**已登记缺口，不许顺手收紧**）。
///
/// 既有用例以这种形态写槽位（`scripts/test/cli.rs`／`contract.rs`／`acceptance.rs` 多处），
/// 它们不在本块的改范围内；本用例把"本判据不碰它"钉成**会红**的断言。
#[test]
fn i05_a_bare_subject_is_still_not_judged() {
    let dir = tmpdir("i05");
    let evs = ledger_with(&dir, "base", "world://s", "p");
    let ont = Ontology::load(&factory_ontology()).unwrap();
    State::fold_declared(&cells_for(&ont), &evs)
        .expect("登记：裸主体今天仍可落账、仍可折（缺口③，不许被本判据顺手收紧）");
}

/// **i06（正控 ⓓ）**：**内嵌四段形态**——类型是**第 3 段**，且该类型按 `part_of` 声明 ⇒ **必须绿**。
#[test]
fn i06_nested_four_segment_instances_are_judged_by_their_own_type() {
    let dir = tmpdir("i06");
    let nested = write_ontology(&dir, "nested.json", |v| {
        v["_objects"]["notice"]["nested"] = json!(true);
        v["_objects"]["notice"]["part_of"] = json!("job");
    });
    let ont = Ontology::load(&nested).unwrap();
    assert_eq!(
        ont.nested_types().get("notice").map(String::as_str),
        Some("job"),
        "夹具：内嵌标记必须被读到"
    );
    let lp = dir.join("ledger.jsonl");
    let mut w = World::open(&nested, &lp, &factory_policy()).unwrap();
    w.commit(
        "change",
        "world://user",
        event::change_body(
            "world://job/j-1/notice/n-1",
            "muted",
            json!(null),
            json!(true),
        ),
    )
    .expect("内嵌四段形态：类型＝第 3 段（`notice`，已声明）⇒ 必须落笔");
    let evs = w.ledger().read_all().unwrap();
    let s = State::fold_declared(&cells_for(&ont), &evs).expect("内嵌形态必须绿");
    assert_eq!(
        s.get("world://job/j-1/notice/n-1", "muted"),
        Some(&json!(true))
    );
}

// ────────────── 空表即拒 ＋ "没接"不许冒充"没问题" ──────────────

/// **i07（G1 形态）**：递进来的**已声明实体集是空的** ⇒ **拒绝折叠**，**不许默默放行**。
///
/// 理由与 `NoDeclaredCells`／"空策略不许上电"同一条：**"一个实体都没查"与"每个实体都查过了"
/// 在读数上一样、在结论上相反**。
#[test]
fn i07_an_empty_declared_entity_set_refuses_to_fold() {
    let dir = tmpdir("i07");
    let evs = ledger_with(&dir, "base", "world://notice/n-1", "muted");
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let cells = DeclaredCells::new(ont.envelope_required(), ont.family_required())
        .with_declared_entities(BTreeSet::new(), BTreeMap::new());
    let e = State::fold_declared(&cells, &evs)
        .expect_err("空实体集 ⇒ 这条判据无从成立 ⇒ 必须拒，不许默默放行");
    assert!(
        e.contains("ext.world.ReadModel.NoDeclaredEntities"),
        "理由要带可判定的错误码，实得：{e}"
    );
}

/// **i08（"没接"不等于"没问题"）**：**没调** `with_declared_entities` 的装配点 ⇒ 本层**不判**。
///
/// 为什么这条必须存在、而且必须**绿**：既有调用点（`scripts/test/family_readmodel.rs::declared_cells`
/// 等）直接 `DeclaredCells::new(...)`——它们测的是**别的判据**（缺格／家族演进），
/// 不该被本判据连带打红。⇒ 这半条"没接"由 `declared_entities: Option<..>` 的 `None`
/// **显式**表达，**不靠空表冒充**；而**生产装配点**（`src/lib.rs::read_model`）**已经接上**
/// （由 `i01` 端到端钉住：那一行删掉，`i01` 变红）。
#[test]
fn i08_not_wiring_this_half_means_no_judgment_not_a_pass() {
    let dir = tmpdir("i08");
    let mut evs = ledger_with(&dir, "base", "world://notice/n-1", "muted");
    evs[0]["body"]["subject"] = json!("world://never-declared-entity/42");
    evs[0]["body"]["path"] = json!("never_declared_field");

    let ont = Ontology::load(&factory_ontology()).unwrap();
    let cells = DeclaredCells::new(ont.envelope_required(), ont.family_required());
    assert!(
        cells.declared_entities().is_none(),
        "夹具：`DeclaredCells::new` 装出来的这一半必须是**没接**（`None`），不是空集"
    );
    State::fold_declared(&cells, &evs)
        .expect("没接这一半 ⇒ 本层不判（既有直接装配点不受影响）——'没接'由 `None` 显式表达");
}

// ════════ 声明面 → 实例面：**"声明了，就必须在实例面上看得见"**（本批两条判据）════════
//
// ## 这两条判据为什么**今天就能落**、且**不是空转**
// 它们判的是**实例面自己**（"声明过的那些，在实例面上有没有对应形态"），**不需要定义面先落**：
// 定义面没有那格时，`declared` 侧就是 `None`／空集 ⇒ 按 G1 ⇒ **报 `NotVerified`（不是绿）**。
// ⇒ ★**落的是【判据】，不是【格】** —— 所以今天落它**不空转**；等定义面一落，接上装配点，它当场变真判。
//
// ## 每条断言的"会红"条件（改坏哪一行 ⇒ 打红哪一条）
// | 断言 | 改坏哪一行 ⇒ 变红 |
// |---|---|
// | `i09`／`i10` | 把 `declaration_coverage` 里那两处 `NotVerified` 改成一个 `Green` ⇒ **两条一起红**（G1 的"空集不许判绿"当场失守） |
// | `i11` | 把 `declared.difference(covered)` 写成恒空（判据恒绿）⇒ `i12`／`i13`／`i14` 一起红 |
// | `i12`／`i13` | `Red` 分支去掉**点名**（只给"有缺失"不给名字）⇒ 那两条的"点名"断言红 |
// | `i14` | 把两条判据各写一份实现（违反"一处实现"）⇒ 本文件的两条同形断言会用**同一个函数**钉住它们（★`declaration_coverage` 只有一处） |

/// **i09**：**声明面不存在** ⇒ `NotVerified`（**绝不许是 `Green`**）。
#[test]
fn i09_an_absent_declaration_face_is_not_verified_and_never_green() {
    let covered: BTreeSet<String> = BTreeSet::new();
    let v = world_core::declaration_coverage(None, &covered);
    assert!(
        matches!(v, world_core::Coverage::NotVerified { .. }),
        "声明面不存在 ⇒ 必须报『未校验』，实得：{v:?}"
    );
    assert_ne!(
        v,
        world_core::Coverage::Green,
        "★G1：判不了的时候**不许**判绿（这条路是最危险的一类假绿）"
    );
}

/// **i10**：**声明面为空** ⇒ `NotVerified`（**G1 的正面用法**：一个都没声明 ≠ 一个都不缺）。
#[test]
fn i10_an_empty_declaration_face_is_not_verified_and_never_green() {
    let declared: BTreeSet<String> = BTreeSet::new();
    let covered: BTreeSet<String> = BTreeSet::new();
    let v = world_core::declaration_coverage(Some(&declared), &covered);
    assert!(
        matches!(v, world_core::Coverage::NotVerified { .. }),
        "空声明面 ⇒ 必须报『未校验』（'一个都没声明'与'一个都不缺'读数一样、结论相反），实得：{v:?}"
    );
    assert_ne!(v, world_core::Coverage::Green, "★G1：空集不许判绿");
}

/// **i11（正控）**：声明集**非空**且**每一条都可见** ⇒ `Green`（防"什么都报未校验"的假通过）。
#[test]
fn i11_every_declared_thing_visible_is_green() {
    let declared: BTreeSet<String> = ["a".to_string(), "b".to_string()].into_iter().collect();
    let covered: BTreeSet<String> = ["a".to_string(), "b".to_string(), "c".to_string()]
        .into_iter()
        .collect();
    assert_eq!(
        world_core::declaration_coverage(Some(&declared), &covered),
        world_core::Coverage::Green,
        "声明过的都在 ⇒ 必须绿（否则这条判据是'什么都报未校验'的装饰）"
    );
}

/// **i12（反例）**：声明集非空、**有一条找不着** ⇒ `Red`，并**点名那一条**。
#[test]
fn i12_a_declared_thing_that_is_not_visible_is_red_and_named() {
    let declared: BTreeSet<String> = ["a".to_string(), "b".to_string()].into_iter().collect();
    let covered: BTreeSet<String> = ["a".to_string()].into_iter().collect();
    let v = world_core::declaration_coverage(Some(&declared), &covered);
    match v {
        world_core::Coverage::Red { missing } => {
            assert_eq!(
                missing,
                vec!["b".to_string()],
                "必须点名缺的那一条，实得：{missing:?}"
            )
        }
        other => panic!("找不着的那条必须判红，实得：{other:?}"),
    }
}

/// **i13（本批的实例位判据：`world://presence/omarchy`）**：**声明了 `omarchy`，而世界里没有它的格 ⇒ 红**。
///
/// ★这正是 Lead 点名的"**声明了就必须有可见形态**"在**在场者**这一侧的落法：
/// 定义面把 `omarchy` 写进**实例位键**（`_permissions.grants.<能力>.instances`）之后，
/// **世界里必须有它的格** —— 否则"授权授给了一个世界上不存在的在场者"。
/// ⚠️ **射程**：本用例**不碰定义面**（`ontology.json` 归 `M01`／`ontology-def`）——
/// 它只钉**判据本身**：`declared={omarchy}` 而 `covered={}` ⇒ `Red` 且点名 `omarchy`。
#[test]
fn i13_a_declared_presence_instance_must_have_visible_cells() {
    let declared: BTreeSet<String> = ["world://presence/omarchy".to_string()]
        .into_iter()
        .collect();
    let covered: BTreeSet<String> = ["world://presence/pcmanfm".to_string()]
        .into_iter()
        .collect();
    match world_core::declaration_coverage(Some(&declared), &covered) {
        world_core::Coverage::Red { missing } => assert_eq!(
            missing,
            vec!["world://presence/omarchy".to_string()],
            "声明了 `omarchy` 而世界里没有它的格 ⇒ 必须点名它"
        ),
        other => panic!("必须判红（『声明了却没有可见形态』），实得：{other:?}"),
    }
    // 正控：它的格真在 ⇒ 绿。
    let covered2: BTreeSet<String> = [
        "world://presence/omarchy".to_string(),
        "world://presence/pcmanfm".to_string(),
    ]
    .into_iter()
    .collect();
    assert_eq!(
        world_core::declaration_coverage(Some(&declared), &covered2),
        world_core::Coverage::Green,
        "正控：`omarchy` 的格真在 ⇒ 必须绿"
    );
}

/// **i14（本批的投影判据，同一形状）**：**声明的每一份投影都必须可达**。
///
/// ★今天"世界里有哪些投影"这句话**没有声明面** ⇒ 这条判据跑起来必然 `NotVerified`；
/// **声明面一落**，它就真判。★**两条判据（实例位／投影）共用 `declaration_coverage` 一处实现**
/// —— 不许各写一份（那会让"声明必须兑现"变成两种口径）。
#[test]
fn i14_every_declared_projection_must_be_reachable() {
    let declared: BTreeSet<String> = ["language".to_string(), "visual".to_string()]
        .into_iter()
        .collect();
    let reachable: BTreeSet<String> = ["language".to_string(), "visual".to_string()]
        .into_iter()
        .collect();
    assert_eq!(
        world_core::declaration_coverage(Some(&declared), &reachable),
        world_core::Coverage::Green,
        "两份都可达 ⇒ 绿"
    );
    let reachable2: BTreeSet<String> = ["language".to_string()].into_iter().collect();
    match world_core::declaration_coverage(Some(&declared), &reachable2) {
        world_core::Coverage::Red { missing } => {
            assert_eq!(
                missing,
                vec!["visual".to_string()],
                "必须点名不可达的那一份"
            )
        }
        other => panic!("声明的投影不可达 ⇒ 必须红，实得：{other:?}"),
    }
    // ★本条今天在**装配层**必然走 NotVerified：声明侧还没有装配点（见 `declaration_coverage` 的文档）。
    let v = world_core::declaration_coverage(None, &reachable);
    assert!(
        matches!(v, world_core::Coverage::NotVerified { .. }),
        "声明侧还没接上 ⇒ 今天必须报『未校验』，**不许**因为'没声明'就判绿"
    );
}
