//! **声明以外的字段不许落账**（书第五章 §5.3 判红）。
//!
//! ## 这一格原来红在哪（2026-09-27 的实测，逐字可核）
//!
//! 书 §5.3 逐字：「向账本写一条记录，主体是一个从未声明过的名字
//! （`world://never-declared-entity/42`），字段是一个从未声明过的名字
//! （`never_declared_field`）。结果 `rc=0`，账本落笔」。原因同节逐字：
//! 「那份声明压根没有被读过。在 `world-core/src/` 全目录检索 `concepts` 这个键，
//! 零命中」。
//!
//! 本文件把那一幕**照原样**变成会红的断言：同一条命令、同一个主体名、同一个字段名。
//!
//! ## 每条断言的"会红"条件（改坏哪一行会打红哪一条）
//!
//! - `b01` / `b02` / `b05` ← `src/ontology_definition/mod.rs` 的 `Ontology::check_concepts`：
//!   把 `UndeclaredEntity` / `UndeclaredField` 两个 `Err` 分支删掉（或让函数恒 `Ok`）
//!   ⇒ 三条一起变红（未声明的实体与字段又能落账）。
//! - `b03` ← 后果相反的方向：把 `check_concepts` 改成"什么都拒"
//!   （例如 `known_entities()` 恒为空、或字段表恒为空集）⇒ 已声明的写入被误拒 ⇒ `b03` 变红。
//!   有这条对照，`b01`/`b02` 才不是"因为什么都拒"而通过。
//! - `b04` 是**登记项**（见下），它断言的是今天的边界，不是"已做到"。

use serde_json::json;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::{event, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-declonly-{tag}-{n}"));
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

fn factory_ontology() -> PathBuf {
    manifest_dir().join("src/ontology_definition/ontology.json")
}

fn factory_policy() -> PathBuf {
    manifest_dir().join("src/gate/policy.json")
}

fn open_world(tag: &str) -> (PathBuf, PathBuf, World) {
    let d = tmpdir(tag);
    let lp = d.join("ledger.jsonl");
    let w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    (d, lp, w)
}

/// **b01**：写一个**未声明的实体** ⇒ 拒，且**不落笔**。
///
/// 主体名与字段名照抄书 §5.3 那次实测。
#[test]
fn b01_undeclared_entity_is_refused_and_nothing_lands() {
    let (_d, _lp, mut w) = open_world("b01");
    let before = w.ledger().read_all().unwrap().len();
    assert_eq!(before, 0);

    let e = w
        .commit(
            "change",
            "world://user",
            event::change_body(
                "world://never-declared-entity/42",
                "never_declared_field",
                json!(null),
                json!("y"),
            ),
        )
        .expect_err("未声明的实体必须被拒");

    assert!(
        e.contains("ext.world.Ontology.UndeclaredEntity"),
        "错误里要有可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("never-declared-entity"),
        "错误里必须读得出**是哪个实体**没声明：{e}"
    );
    assert!(
        e.contains("notice") && e.contains("job"),
        "错误里要顺带说出已声明的实体（否则只说了不行、没说怎么办）：{e}"
    );

    // 不落笔：账本条数未变，读模型里也没有它
    let after = w.ledger().read_all().unwrap().len();
    assert_eq!(after, before, "被拒的写入不得落笔（账本条数必须未变）");
    assert!(
        w.read_model()
            .unwrap()
            .get("world://never-declared-entity/42", "never_declared_field")
            .is_none(),
        "被拒的写入不得出现在状态里"
    );
}

/// **b02**：写一个**未声明的字段**（实体是声明过的）⇒ 拒，且**不落笔**。
#[test]
fn b02_undeclared_field_is_refused_and_nothing_lands() {
    let (_d, _lp, mut w) = open_world("b02");
    let before = w.ledger().read_all().unwrap().len();

    let e = w
        .commit(
            "change",
            "world://user",
            event::change_body(
                "world://notice/n-1",
                "never_declared_field",
                json!(null),
                json!("y"),
            ),
        )
        .expect_err("未声明的字段必须被拒");

    assert!(
        e.contains("ext.world.Ontology.UndeclaredField"),
        "错误里要有可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("never_declared_field"),
        "错误里必须读得出**是哪个字段**没声明：{e}"
    );
    assert!(
        e.contains("notice") && e.contains("muted"),
        "错误里要说明 `notice` 已声明的字段（这里是 `muted`）：{e}"
    );

    let after = w.ledger().read_all().unwrap().len();
    assert_eq!(after, before, "被拒的写入不得落笔（账本条数必须未变）");
    assert!(w
        .read_model()
        .unwrap()
        .get("world://notice/n-1", "never_declared_field")
        .is_none());
}

/// **b03**：已声明的实体 + 已声明的字段 ⇒ **照常落账**（防"什么都拒"的假通过）。
///
/// 出厂 `concepts` 只声明两格：`notice.muted` 与 `job.status`。
/// 两条都走一遍真写入路径，并核状态。
#[test]
fn b03_declared_entity_and_field_still_land() {
    let (_d, _lp, mut w) = open_world("b03");

    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    )
    .expect("已声明的实体与字段必须能落账");

    w.commit(
        "change",
        "world://user",
        event::change_body("world://job/j-1", "status", json!(null), json!("doing")),
    )
    .expect("已声明的实体与字段必须能落账");

    let s = w.read_model().unwrap();
    assert_eq!(s.get("world://notice/n-1", "muted"), Some(&json!(true)));
    assert_eq!(s.get("world://job/j-1", "status"), Some(&json!("doing")));
    assert_eq!(w.ledger().read_all().unwrap().len(), 2);
}

/// **b04（登记项，不是绿）**：**裸主体**不受 `concepts` 约束——今天的边界。
///
/// 依据（都是本仓现状，逐字可核）：
///
/// | 谁 | 写了什么 |
/// |---|---|
/// | `tests/cli.rs:100` | `{"subject":"world://s","path":"p","before":null,"after":1}` ⇒ 断言 `rc=0` |
/// | `tests/cli.rs:230` | `{"subject":"world://s","path":"p","before":null,"after":true}` ⇒ 断言 `rc=0` |
/// | `tests/contract.rs:257`、`:765`、`:803`… | `event::change_body("world://s", "p", …)` 经 `World::commit` 落账 |
/// | `tests/acceptance.rs:296` | 同上（`world://s` + `p`） |
///
/// 这些 subject **没有实例段**（`world://<名字>`），不是"某个实体的一个实例"。
/// 既有用例以这种形态写槽位，而它们**不在本次改动的可改范围**（既有用例不许改）。
/// 于是本次只把"**实体引用**"这一半合上，裸主体这一半**仍然敞着**，并在此**立成登记项**：
/// 谁哪天把这一半合上，这条会红——那时请连同上面几处一起改。
///
/// ⚠️ 与它相邻的另一半（`world://check/probe`、`world://sys/a` 这类**带实例段**的
/// 未声明实体）**已经被拒**，代价是 `world-core/check.sh` 第 89 行与 `tools/` 下的探针
/// 会非零退出——那些文件同属别的工区，本轮未动，已在交付说明里逐条列出。
#[test]
fn b04_bare_subject_is_a_registered_gap_not_a_declared_entity() {
    let (_d, _lp, mut w) = open_world("b04");

    // 它不是实体引用（没有 `<实体>/<实例>` 这一段）⇒ 今天不受 concepts 约束
    assert_eq!(world_core::ontology_definition::Ontology::entity_of("world://s"), None);
    assert_eq!(
        world_core::ontology_definition::Ontology::entity_of("world://notice/n-1"),
        Some("notice")
    );

    w.commit(
        "change",
        "world://user",
        event::change_body("world://s", "p", json!(null), json!(1)),
    )
    .expect("登记：裸主体今天仍可落账（见本用例文档列出的三处既有依赖）");
}

/// **b05**：书 §5.3 实测的**那条命令**，今天必须非零退出且不落笔。
///
/// 走的是真二进制（与书里那次实测同一条路）：`world-core append change …`。
#[test]
fn b05_cli_append_of_an_undeclared_entity_is_refused() {
    let d = tmpdir("b05");
    let lp = d.join("ledger.jsonl");

    let out = Command::new(env!("CARGO_BIN_EXE_world-core"))
        .args([
            "--ontology",
            &factory_ontology().display().to_string(),
            "--policy",
            &factory_policy().display().to_string(),
            "--ledger",
            &lp.display().to_string(),
            "append",
            "change",
            r#"{"subject":"world://never-declared-entity/42","path":"never_declared_field","before":null,"after":"y"}"#,
        ])
        .output()
        .expect("无法启动被测二进制");

    let code = out.status.code().unwrap_or(-1);
    let err = String::from_utf8_lossy(&out.stderr).to_string();
    assert_eq!(
        code, 2,
        "未声明的实体必须非零退出（书 §5.3 实测那次是 rc=0）；stderr={err}"
    );
    assert!(
        err.contains("UndeclaredEntity"),
        "拒绝理由要带错误码；stderr={err}"
    );

    let text = fs::read_to_string(&lp).unwrap_or_default();
    assert!(
        text.trim().is_empty(),
        "被拒的写入不得落笔，账本应仍为空，实得：{text}"
    );
}

/// 顺带钉住一处**口径**：`concepts` 只管 `change`（唯一改状态的原语）。
///
/// `notice.subject` 的语义是"这条通告关于谁"，不是"改了哪一格"——
/// 拿实体字段表去查它是查错了对象。所以这里刻意用一个**未声明的实体名**当通告的
/// `subject`：它必须照样通过。
///
/// 变异：把 `check_concepts` 开头那句 `if kind != "change" { return Ok(()); }` 去掉
/// ⇒ 这条通告被误判成"未声明的实体"而拒 ⇒ 本条变红。
#[test]
fn b06_concepts_gate_only_the_change_family() {
    let (_d, _lp, mut w) = open_world("b06");

    w.commit(
        "notice",
        "world://agent/1",
        event::notice_body(
            "job.done",
            "world://never-declared-entity/42",
            json!({ "exit": 0 }),
        ),
    )
    .expect("通告不是实体写入：它的 subject 只是『关于谁』，不该被 concepts 拦下");

    assert_eq!(w.ledger().read_all().unwrap().len(), 1);
}
