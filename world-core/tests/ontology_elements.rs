//! **本体五要素**（对象／关系／接口·能力／动作／函数）的判据与反例。
//!
//! ## 本文件判什么（逐条对到五要素）
//!
//! | 组 | 判据 | 反例（必须红） | 恢复（必须绿） |
//! |---|---|---|---|
//! | ① | **五要素节存在性**：任一节缺 ⇒ `Ontology::load` 拒启（`MissingSection`） | 逐节删（五节各一次） | 原本体 |
//! | ② | **对象**：字段的**值类型**参与校验（含 `enum` **闭集**、`ref(<类型>)`）。★ **`kind` 除外**：`envelope.kind` 是**家族名**，走家族查找报 `UnknownKind` 并点名那个值——**不是**闭集（依据：`openspec/specs/envelope-validation/spec.md` 逐字「枚举值另有其主（家族查找报 `ext.world.Ontology.UnknownKind` 并点名）」；`openspec/BOOK/冲突总账.md` 逐字「`enum(...)` 明确豁免」。理由全文见 `src/ontology_definition/mod.rs::Ontology::validate_types` 的文档） | 给 `muted` 写整数；给 `status` 写越界值；`ref` 指向别的类型 | 写对 |
//! | ③ | **关系**：命名关系的**两端类型必须已声明** | `from`/`to` 指向未声明的类型 | 指回已声明的类型 |
//! | ④ | **内嵌**：声明式内嵌标记（`nested`＋`part_of`）——实例路径必须是 `world://<父>/<父实例>/<本类型>/<本实例>` | 内嵌类型写成两段（未声明实体）／写成三段的**错父** | 写成正确的四段 |
//! | ⑤ | **按类型的实例计数**：声明为单实例的类型，fold 后实例数 > 1 ⇒ 红（`TooManyInstances`） | 上限 1 而写两个实例 | 只写一个 |
//! | ⑥ | **许可归位**：授权只许授在**能力**上；`default` 必须显式 `deny` | 授在具体类型／具体对象上；`default` 缺失或写成 `allow` | 授在能力上 |
//! | ⑦ | **动作引用能力**：动作引用了不存在的能力 ⇒ 红（本体侧与策略侧各一条） | `_actions.<动作>.capability` 指向不存在的能力；策略侧同上 | 指回已声明的能力 |
//! | ⑧ | **函数入口表只有入口名**：出现命令字面量 ⇒ 红 | `entries` 里写 `pacman`／`/usr/bin/pacman`／`pacman -S` | 只写入口名 |
//! | ⑨ | **两处对象声明不得各说各话**：`_objects`（读路径）与 `concepts`（身份）同名字段的类型声明必须逐字一致 ⇒ 不一致即拒启（`ConceptsDrift`） | 只改一处（两个方向各一次） | 两处一起改到同一个值 |
//! | ⑩ | **十二节的归属写死**：`_section_map` 声明的 `_` 分节键集合 == 文件里实际的 `_` 分节键集合（`SectionMapDrift`） | 新加一个 `_` 分节不列名／表里指错键／`home` 不在封闭表／`keys` 空又没 `_where` | 原本体 |
//! | ⑪ | **结构性死声明与悬空引用**：死入口（`DeadFunctionEntry`）／悬空入口引用（`DanglingFunctionRef`）／死能力（`DeadCapability`） | 入口没人引用／动作指向不存在的入口／能力既无动作又无许可 | 让动作引用它／指回已声明入口／给它动作或授予 |
//! | ⑫ | **`usage` 是「只报告、不拒启」**（**不是判据**）：声明了但账本零使用 ⇒ **必须 rc=0** | ——（**它不许红**；本组只有正控） | 造"零使用"的本体 ⇒ rc=0 ＋ 打印清单 |
//! | ⑬ | **载体无关性（判据①a）**：本体**参与身份**的那一半（非 `_` 键）不许出现载体专有串（`CarrierSpecificInOntology`） | 非 `_` 键/值里写 `.service`／`/run/`／`systemd` | 去掉；或把同样的话写进 **`_` 键**（那是指路，**必须能加载**） |
//! | ⑭ | **关系的基数与方向性只许声明世界真执行的取值**（Lead 裁 · 甲）：`card` 只许 `"many"`、`bidirectional` 只许 `false`，或**整格不写**；声明别的、或**形状写错**（不可判读）⇒ 拒启（`BadField`）——**"声明了没执行"比"没声明"更坏**（读者会以为有约束） | `card` 写 `"one"`／写 `3`；`bidirectional` 写 `true`／写 `"no"` | 写回 `"many"`／`false`；或把那一格删掉（＝不声明） |
//!
//! ## 两处**刻意不动**的口径（它们是既有契约，有断言钉着）
//!
//! 1. `Ontology::entity_of` 的"**取首段**"口径：`world://s` ⇒ `None`、
//!    `world://notice/n-1` ⇒ `Some("notice")`（`tests/atom_declared_only.rs` 两条断言）。
//!    本文件 ④ 组的判据**不依赖**它变宽——内嵌走的是 `nested_parent_of`（四段形态）＋
//!    `_objects.<类型>.part_of` 的**声明式标记**，而**不是**靠三段式 `world://a/b/c`。
//! 2. **裸主体**（`world://<名字>`）的约束**保持**登记项形态（本批**不许**把它变成会红的判据）：
//!    几十处既有用例依赖它。⇒ 本文件不碰它。
//!
//! ## 反例为什么**不是**自证通过
//!
//! 每一组都是"**改坏 ⇒ 必须红；改回 ⇒ 必须绿**"成对出现（`red_then_green`），
//! 且 ① 组的红还**经 CLI** 跑了一遍（`world-core check` ⇒ rc≠0）——
//! 那是本批第一批的原始验收口径（"删掉一节 ⇒ `world-core check` 必须 rc≠0"）。

use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::ontology_definition::Ontology;

// ────────────────────────── 夹具 ──────────────────────────

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-elem-{tag}-{n}"));
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

fn chmod600(p: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(p, fs::Permissions::from_mode(0o600)).unwrap();
    }
    let _ = p;
}

fn factory_json() -> Value {
    serde_json::from_str(&fs::read_to_string(factory_ontology()).unwrap()).unwrap()
}

/// 造一份临时本体（**从出厂本体起改**，改法与出厂同形）。
fn write_ontology(dir: &Path, name: &str, edit: impl FnOnce(&mut Value)) -> PathBuf {
    let mut v = factory_json();
    edit(&mut v);
    let p = dir.join(name);
    fs::write(
        &p,
        format!("{}\n", serde_json::to_string_pretty(&v).unwrap()),
    )
    .unwrap();
    chmod600(&p);
    p
}

/// 造一份临时策略（**从出厂策略起改**）。
fn write_policy(dir: &Path, name: &str, edit: impl FnOnce(&mut Value)) -> PathBuf {
    let mut v: Value =
        serde_json::from_str(&fs::read_to_string(factory_policy()).unwrap()).unwrap();
    edit(&mut v);
    let p = dir.join(name);
    fs::write(
        &p,
        format!("{}\n", serde_json::to_string_pretty(&v).unwrap()),
    )
    .unwrap();
    chmod600(&p);
    p
}

/// **本批的核对器**：同一条改动，改坏 ⇒ 必须红、改回 ⇒ 必须绿。
///
/// 为什么写成对：单看"改坏会红"分不清"判据有效"与"这份本体本来就起不来"；
/// 单看"改回会绿"分不清"判据没生效"。两条一起才说明**是那一格在承重**。
fn red_then_green(tag: &str, dir: &Path, bad: impl FnOnce(&mut Value), must_say: &str) {
    let bad_path = write_ontology(dir, &format!("{tag}-bad.json"), bad);
    let e = Ontology::load(&bad_path)
        .err()
        .unwrap_or_else(|| panic!("[{tag}] 反例必须被拒，实得：加载成功（判据是装饰）"));
    assert!(
        e.contains(must_say),
        "[{tag}] 拒绝理由必须点名 `{must_say}`，实得：{e}"
    );
    // 恢复：不改那一格 ⇒ 必须能加载（防"什么都拒"的假绿）
    let good = write_ontology(dir, &format!("{tag}-good.json"), |_| {});
    Ontology::load(&good).unwrap_or_else(|e| panic!("[{tag}] 原本体必须能加载，实得：{e}"));
}

/// **CLI 跑一次**（第一批的原始验收口径：删掉一节 ⇒ `world-core check` 必须 rc≠0）。
///
/// 返回 `(退出码, stdout+stderr)`。
fn cli_check(ont: &Path, dir: &Path) -> (i32, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let lp = dir.join("cli-ledger.jsonl");
    let out = Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("--ledger")
        .arg(&lp)
        .arg("--policy")
        .arg(factory_policy())
        .arg("check")
        .output()
        .expect("跑得起来 world-core check");
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), txt)
}

// ────────────────────── ① 五要素节存在性 ──────────────────────

/// **①-a**：每一节**逐个**删掉 ⇒ `Ontology::load` **拒启**、点名缺的是哪一要素；
/// 恢复 ⇒ 必须能加载。**五节各来一次**（不是抽查一节）。
///
/// 判据面与装载面同源（都读 `src/ontology_definition/mod.rs` 的 `SECTIONS` 表）⇒
/// "补一节忘了加判据"不可能发生；本用例再**逐节**把它钉一遍。
#[test]
fn m01_every_missing_element_section_refuses_to_load_but_the_intact_one_loads() {
    let dir = tmpdir("m01");
    // 正控：出厂本体必须能加载（否则下面五条可能只是"什么都拒"）
    Ontology::load(&factory_ontology()).expect("出厂本体必须能加载（五节齐备）");

    // 五节的（要素名, 顶层键）——与 `SECTIONS` 同口径，但**独立列一遍**：
    // 若哪天装载器漏了一节，本表会当场发现（而不是跟着它一起漏）。
    let sections: [(&str, &str); 5] = [
        ("对象（Object）", "_objects"),
        ("关系（Link）", "_links"),
        ("接口·能力（Interface）", "_interfaces"),
        ("动作（Action）", "_actions"),
        ("函数（Function）", "_functions"),
    ];
    for (element, key) in sections {
        // 对象那一节有两个键（`_objects` 优先、`concepts` 退回）⇒ 必须**两个都删**才算缺。
        let bad = write_ontology(&dir, &format!("missing-{key}.json"), |v| {
            v.as_object_mut().unwrap().remove(key);
            if key == "_objects" {
                v.as_object_mut().unwrap().remove("concepts");
            }
        });
        let e = Ontology::load(&bad)
            .err()
            .unwrap_or_else(|| panic!("缺 `{key}` 必须拒启，实得：加载成功（判据是装饰）"));
        assert!(
            e.contains("ext.world.Ontology.MissingSection"),
            "缺 `{key}` 的理由要带可判定的错误码，实得：{e}"
        );
        assert!(
            e.contains(element),
            "缺 `{key}` 的理由必须**点名缺的是哪一要素**（{element}），实得：{e}"
        );
        // 恢复：只恢复这一节 ⇒ 必须能加载
        let good = write_ontology(&dir, &format!("restored-{key}.json"), |_| {});
        Ontology::load(&good).unwrap_or_else(|e| panic!("恢复 `{key}` 后必须能加载，实得：{e}"));
    }
}

/// **①-b（CLI，第一批的原始口径）**：删掉一节 ⇒ `world-core check` **rc≠0**；
/// 恢复 ⇒ **rc=0**。
///
/// 为什么要走 CLI 再钉一遍：库层"加载失败"与**命令层"拒绝启动"**之间隔着装配
/// （`main` 的退出码映射）——两处都可能单独出错。第一批的验收原话是
/// 「删掉一节 ⇒ `world-core check` 必须 rc≠0；恢复 ⇒ 必须 rc=0」。
#[test]
fn m02_cli_check_refuses_when_an_element_section_is_missing_and_passes_when_restored() {
    let dir = tmpdir("m02");
    // 恢复那一半：出厂本体 ⇒ rc=0
    let (rc_ok, out_ok) = cli_check(&factory_ontology(), &dir);
    assert_eq!(rc_ok, 0, "出厂本体下 check 必须 rc=0，实得：{out_ok}");

    // 反例：删掉「接口·能力」那一节（五节里最靠中间的一节）
    for key in [
        "_objects",
        "_links",
        "_interfaces",
        "_actions",
        "_functions",
    ] {
        let bad = write_ontology(&dir, &format!("cli-missing-{key}.json"), |v| {
            v.as_object_mut().unwrap().remove(key);
            if key == "_objects" {
                v.as_object_mut().unwrap().remove("concepts");
            }
        });
        let (rc, out) = cli_check(&bad, &dir);
        assert_ne!(
            rc, 0,
            "缺 `{key}` 时 check 必须 rc≠0，实得 rc={rc}；输出：{out}"
        );
        assert!(
            out.contains("ext.world.Ontology.MissingSection"),
            "缺 `{key}` 时 check 的原始输出要点名那条错误码，实得：{out}"
        );
    }
}

// ────────────────────── ② 对象：值类型 ──────────────────────

/// **②**：字段的**值类型**参与校验（本批从"值只是自由文本"升级成"机器可读"）。
///
/// ★ **`enum` 闭集有一处字段级豁免**：`envelope.kind` **不进**这条判据——它是**家族名**，
/// 由家族查找报 `ext.world.Ontology.UnknownKind` 并**点名那个值**（依据：上位规格
/// `openspec/specs/envelope-validation/spec.md` 逐字「**枚举值**另有其主（**家族查找报
/// `ext.world.Ontology.UnknownKind` 并点名**）」＋ `openspec/BOOK/冲突总账.md` 逐字
/// 「`enum(...)` 明确豁免」）。**理由全文**见 `src/ontology_definition/mod.rs::Ontology::validate_types`
/// 的文档（本处只指路，不复述）。⇒ 本用例判的是**别的** enum 字段（如 `status`）。
///
/// 三格各一条反例：
/// - `notice.muted`（`bool`）写成整数 ⇒ 红；
/// - `job.status`（`enum(todo,doing,done)`）写成**越界值** ⇒ 红（**闭集**）；
/// - `ref(<类型>)` 指向**别的**类型 ⇒ 红。
///
/// 恢复那一半在 `red_then_green` 里（原本体必须能加载）。
#[test]
fn m03_field_value_types_are_checked_including_closed_enums_and_refs() {
    let dir = tmpdir("m03");
    let lp = dir.join("ledger.jsonl");
    let mut w =
        world_core::World::open(&factory_ontology(), &lp, &factory_policy()).expect("出厂本体能起");

    // 正控：写对的值 ⇒ 必须落笔（否则下面三条只是"什么都拒"）
    w.commit(
        "change",
        "world://user",
        world_core::common::event::change_body(
            "world://notice/n-1",
            "muted",
            json!(null),
            json!(true),
        ),
    )
    .expect("`muted: bool` 写 `true` 必须落笔");
    w.commit(
        "change",
        "world://user",
        world_core::common::event::change_body(
            "world://job/j-1",
            "status",
            json!(null),
            json!("doing"),
        ),
    )
    .expect("`status: enum(todo,doing,done)` 写 `doing` 必须落笔");

    // 反例①：`muted` 写整数（本体声明 `bool`）
    let e = w
        .commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://notice/n-2",
                "muted",
                json!(null),
                json!(1),
            ),
        )
        .expect_err("`muted: bool` 写整数必须被拒");
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType")
            && e.contains("`muted`")
            && e.contains("bool"),
        "理由要点名那一格与两侧类型，实得：{e}"
    );

    // 反例②：枚举**闭集**——越界值必须红
    let e = w
        .commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://job/j-2",
                "status",
                json!(null),
                json!("cancelled"),
            ),
        )
        .expect_err("`status` 的越界值必须被拒（enum 是闭集）");
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("`status`"),
        "越界值的理由要点名那一格，实得：{e}"
    );

    // 反例③：`ref(<类型>)` 指向**别的**类型 ⇒ 红；指向对的类型 ⇒ 绿
    let ref_ok = write_ontology(&dir, "ref-ok.json", |v| {
        v["_objects"]["job"]["fields"]["owner"] = json!("ref(notice)");
    });
    let ok = Ontology::load(&ref_ok).expect("`ref(notice)` 是合法声明");
    assert!(
        ok.declared_fields("job").unwrap().contains_key("owner"),
        "新字段必须被登记"
    );
    let lp2 = dir.join("ref-ledger.jsonl");
    let mut w2 = world_core::World::open(&ref_ok, &lp2, &factory_policy()).expect("起得来");
    w2.commit(
        "change",
        "world://user",
        world_core::common::event::change_body(
            "world://job/j-1",
            "owner",
            json!(null),
            json!("world://notice/n-1"),
        ),
    )
    .expect("`ref(notice)` 写一个 notice 的实例引用必须落笔");
    let e = w2
        .commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://job/j-2",
                "owner",
                json!(null),
                json!("world://job/j-1"),
            ),
        )
        .expect_err("`ref(notice)` 写一个 job 的实例引用必须被拒");
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("ref(notice)"),
        "理由要点名声明的类型，实得：{e}"
    );
}

// ────────────────────── ③ 关系：两端类型 ──────────────────────

/// **③**：命名关系的**两端类型必须已声明**——未声明 ⇒ 红（`UndeclaredRelationEndpoint`）。
///
/// 两条反例（`from` 一侧与 `to` 一侧各一次）＋ 恢复。
#[test]
fn m04_relation_endpoints_must_be_declared_types() {
    let dir = tmpdir("m04");
    // 正控：出厂关系 `part-of`（notice → job）必须能加载
    Ontology::load(&factory_ontology()).expect("出厂关系两端都是已声明的类型");
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let links: Vec<(&str, &str, &str, &str)> = ont
        .links()
        .map(|(n, l)| (n, l.from.as_str(), l.to.as_str(), l.card.as_str()))
        .collect();
    assert!(
        links
            .iter()
            .any(|(n, f, t, _)| *n == "part-of" && *f == "notice" && *t == "job"),
        "出厂关系必须可枚举（`_links` 被装载器读到），实得：{links:?}"
    );

    red_then_green(
        "m04-from",
        &dir,
        |v| {
            v["_links"]["part-of"]["from"] = json!("no-such-type");
        },
        "ext.world.Ontology.UndeclaredRelationEndpoint",
    );
    red_then_green(
        "m04-to",
        &dir,
        |v| {
            v["_links"]["part-of"]["to"] = json!("ghost-type");
        },
        "ext.world.Ontology.UndeclaredRelationEndpoint",
    );
}

// ────────────────────── ④ 内嵌：声明式标记 ──────────────────────

/// **④**：**内嵌**用声明式标记表达（`_objects.<类型>` 的 `nested: true` ＋ `part_of`），
/// **不是**靠三段式 `world://a/b/c`。
///
/// ## 取舍（写清楚，不许含糊）
///
/// `Ontology::entity_of` 的"**取首段**"口径**本批一字未改**（两条既有断言钉着它）：
/// `world://a/b/c` ⇒ `Some("a")`——首段**永远是类型**。于是三段式表达不出
/// "c 是嵌在 b 里的另一类东西"：若 `a` 已声明，`b/c` 只是同一类型的两个实例名段。
/// ⇒ 内嵌走**声明式标记**，实例路径固定为 `world://<父类型>/<父实例>/<本类型>/<本实例>`。
///
/// ## 与那两条既有断言的相容性
///
/// - `world://s` ⇒ `None`：本组**不碰**裸主体（它仍是登记项，不是判据）；
/// - `world://notice/n-1` ⇒ `Some("notice")`：本组的两段形态照旧走这条口径；
/// - 内嵌那一格由 `nested_parent_of`（**四段**形态）与 `part_of` 声明判，
///   与 `entity_of` 正交 ⇒ 不改它也能判内嵌。
#[test]
fn m05_embedded_types_are_declared_not_expressed_by_three_segment_paths() {
    let dir = tmpdir("m05");

    // 出厂本体里 `notice` **不是**内嵌类型（`part_of` 缺省）⇒ 两段实例照旧合法。
    let ont = Ontology::load(&factory_ontology()).unwrap();
    assert_eq!(
        ont.object_type("notice").unwrap().part_of,
        None,
        "出厂 `notice` 不在 `part_of` 里 ⇒ 它今天不受内嵌形态约束"
    );
    assert_eq!(
        Ontology::entity_of("world://a/b/c"),
        Some("a"),
        "取首段的口径本批一字未改（`tests/atom_declared_only.rs` 钉着它）"
    );

    // 造一份**把 `notice` 声明为内嵌在 `job` 里**的本体。
    let embedded = write_ontology(&dir, "nested.json", |v| {
        v["_objects"]["notice"]["nested"] = json!(true);
        v["_objects"]["notice"]["part_of"] = json!("job");
    });
    let ont_e = Ontology::load(&embedded).expect("声明式内嵌标记必须能加载");
    assert_eq!(
        ont_e.object_type("notice").unwrap().part_of.as_deref(),
        Some("job"),
        "内嵌标记必须被装载器读到"
    );

    let lp = dir.join("nested-ledger.jsonl");
    let mut w = world_core::World::open(&embedded, &lp, &factory_policy()).expect("起得来");

    // 正控：**正确的内嵌形态**（`world://job/<父实例>/notice/<本实例>`）⇒ 落笔
    w.commit(
        "change",
        "world://user",
        world_core::common::event::change_body(
            "world://job/j-1/notice/n-1",
            "muted",
            json!(null),
            json!(true),
        ),
    )
    .expect("正确的内嵌路径必须落笔");

    // 反例①：两段形态 ⇒ 红（声明为内嵌后，两段不再是它的合法形态）
    let e = w
        .commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://notice/n-9",
                "muted",
                json!(null),
                json!(true),
            ),
        )
        .expect_err("声明为内嵌的类型，两段形态必须被拒");
    assert!(
        e.contains("ext.world.Ontology.UndeclaredEmbeddedMarker"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(e.contains("job"), "理由要点名**声明的父类型**，实得：{e}");

    // 反例②：四段形态但**父类型不对** ⇒ 红
    let e = w
        .commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://notice/x/notice/n-9",
                "muted",
                json!(null),
                json!(true),
            ),
        )
        .expect_err("四段形态但父类型不是 `job` 必须被拒");
    assert!(
        e.contains("ext.world.Ontology.UndeclaredEmbeddedMarker"),
        "实得：{e}"
    );

    // 恢复那一半：把内嵌标记去掉 ⇒ 两段形态又合法（防"内嵌判据把两段一律打死"）
    let plain_path = write_ontology(&dir, "nested-off.json", |_| {});
    assert!(
        Ontology::load(&plain_path)
            .unwrap()
            .object_type("notice")
            .unwrap()
            .part_of
            .is_none(),
        "不带标记 ⇒ 不是内嵌类型"
    );
    let lp3 = dir.join("plain-ledger.jsonl");
    let mut w3 = world_core::World::open(&plain_path, &lp3, &factory_policy()).expect("起得来");
    w3.commit(
        "change",
        "world://user",
        world_core::common::event::change_body(
            "world://notice/n-9",
            "muted",
            json!(null),
            json!(true),
        ),
    )
    .expect("去掉内嵌标记后，两段形态必须重新合法（证明上面的红**是那一格造成的**）");
}

// ────────────────────── ⑤ 按类型的实例计数 ──────────────────────

/// **⑤**：**按类型的实例计数**（`State::type_counts`）＋「声明为单实例的类型
/// fold 后实例数 > 1 ⇒ 红」（`TooManyInstances`）。
///
/// ## 为什么这条判据今天才立得起来
///
/// 折叠层此前**没有类型这个概念**：`objects` 以 subject **字符串**为键
/// （`"world://notice/n-1"`）⇒ "这个类型现在有几个实例"在读数面上问不出来。
/// 本批加了 `type_counts()`（**读数**）与 `DeclaredCells::with_instance_limits`（**判据面**）。
#[test]
fn m06_instance_counts_by_type_are_exposed_and_single_instances_are_enforced() {
    let dir = tmpdir("m06");

    // ① 出厂：两个类型都声明 `instance_mode: "many"` ⇒ 无上限 ⇒ 多实例照常
    let ont = Ontology::load(&factory_ontology()).unwrap();
    assert!(
        ont.instance_limits().is_empty(),
        "出厂类型都是 `many` ⇒ 上限表为空（这不等于'实例可以无限'，是'法律今天没写上限'）"
    );
    let lp = dir.join("many.jsonl");
    let mut w = world_core::World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    for (i, n) in ["n-1", "n-2", "n-3"].iter().enumerate() {
        w.commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                &format!("world://notice/{n}"),
                "muted",
                json!(null),
                json!(i % 2 == 0),
            ),
        )
        .unwrap();
    }
    let counts = w.read_model().unwrap().type_counts();
    assert_eq!(
        counts.get("notice").copied(),
        Some(3),
        "**按类型的实例计数**必须读得出来（本批新开的读数面），实得：{counts:?}"
    );

    // ② 反例：把 `notice` 声明成单实例（`instance_mode: "single"` ⇒ 上限 1）
    //    同一批事件（3 个 notice 实例）⇒ fold **必须红**
    let single = write_ontology(&dir, "single.json", |v| {
        v["_objects"]["notice"]["instance_mode"] = json!("single");
    });
    assert_eq!(
        Ontology::load(&single)
            .unwrap()
            .instance_limits()
            .get("notice"),
        Some(&1),
        "`single` 必须派生成上限 1"
    );
    let lp2 = dir.join("single.jsonl");
    let bad_path = write_ontology(&dir, "single-ont.json", |v| {
        v["_objects"]["notice"]["instance_mode"] = json!("single");
    });
    // 用**同一份**文件建世界（避免两份夹具互相不一致）
    let _ = single;
    let mut w2 = world_core::World::open(&bad_path, &lp2, &factory_policy()).unwrap();
    let mut err = None;
    for n in ["n-1", "n-2"] {
        let r = w2.commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                &format!("world://notice/{n}"),
                "muted",
                json!(null),
                json!(true),
            ),
        );
        if let Err(e) = r {
            err = Some(e);
            break;
        }
    }
    // 两条 `true` 会撞 `before` 不符吗？不会：两条写的是**不同实例**（各自首见，不核 before）。
    // 但第二条的 `muted` 前值在**本实例**上不存在 ⇒ 仍走"首见不核"。
    // 若写入侧没拦住，读侧（折叠）必须拦住——两条路都要判：
    let folded = w2.read_model();
    let from_fold = folded.err();
    let whichever = err.or(from_fold);
    let msg = whichever.unwrap_or_else(|| {
        panic!(
            "声明为单实例（上限 1）而写了两条 `world://notice/*` ⇒ 必须有一处报红\
             （写入侧或折叠侧），实得：两处都通过了"
        )
    });
    assert!(
        msg.contains("ext.world.ReadModel.TooManyInstances"),
        "理由要带可判定的错误码，实得：{msg}"
    );
    assert!(msg.contains("notice"), "理由要点名那个类型，实得：{msg}");
}

// ────────────────────── ⑥ 许可归位 ──────────────────────

/// **⑥**：许可**条文**并入本体；**授权只许授在能力上**；`default` 必须**显式** `deny`。
///
/// 三条反例：① 授在**具体类型**上；② 授在**具体对象**上；③ `default` 缺失／写成别的词。
/// ＋ 恢复（出厂条文必须能加载）＋ **条文的可枚举性**（授权项必须逐条读得出来）。
#[test]
fn m07_permissions_live_in_the_ontology_and_may_only_be_granted_on_capabilities() {
    let dir = tmpdir("m07");
    let ont = Ontology::load(&factory_ontology()).expect("出厂许可条文必须能加载");
    assert_eq!(ont.permission_default(), "deny", "出厂口径：默认显式拒绝");
    let granted: Vec<&str> = ont.permissions().map(|(k, _)| k).collect();
    assert!(
        !granted.is_empty() && granted.iter().all(|g| g.contains('.')),
        "授权项必须**只**是能力名（形如 `notice.mute`），实得：{granted:?}"
    );

    red_then_green(
        "m07-type",
        &dir,
        |v| {
            v["_permissions"]["grants"]["notice"] = json!({ "who": ["world://user"] });
        },
        "ext.world.Ontology.GrantNotOnCapability",
    );
    red_then_green(
        "m07-object",
        &dir,
        |v| {
            v["_permissions"]["grants"]["world://notice/n-1"] = json!({ "who": ["world://user"] });
        },
        "ext.world.Ontology.GrantNotOnCapability",
    );
    red_then_green(
        "m07-default",
        &dir,
        |v| {
            v["_permissions"]["default"] = json!("allow");
        },
        "ext.world.Ontology.PermissionDefaultOpen",
    );
    // `default` **缺失**也算默认允许的形态（与写成 `allow` 同判、不同措辞）
    let missing = write_ontology(&dir, "m07-default-missing.json", |v| {
        v["_permissions"].as_object_mut().unwrap().remove("default");
    });
    let e = Ontology::load(&missing).expect_err("缺 `default` 必须被拒（默认允许不是安全默认）");
    assert!(
        e.contains("ext.world.Ontology.PermissionDefaultOpen"),
        "实得：{e}"
    );
}

// ────────────────────── ⑦ 动作引用能力 ──────────────────────

/// **⑦**：**动作引用了不存在的能力 ⇒ 红**——本体侧与策略侧**各一条**（两处各自成判）。
///
/// - 本体侧：`_actions.<动作>.capability` 指不到 `_interfaces`；
/// - 策略侧：`policy.json` 的 `actions.<动作>.capability` 指不到 `capabilities`；
/// - **交叉**：闸侧的能力名必须在本体 `_interfaces` 里（`World::open` 逐项核）。
#[test]
fn m08_actions_referencing_unknown_capabilities_are_refused_on_both_sides() {
    let dir = tmpdir("m08");

    // 本体侧：正控（出厂 `_actions` 逐条指得到 `_interfaces`）
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let acts: Vec<(String, String)> = ont
        .actions()
        .map(|(n, a)| (n.to_string(), a.capability.clone()))
        .collect();
    assert!(!acts.is_empty(), "出厂必须声明动作（动作是唯一写入通道）");
    let ifaces: Vec<&str> = ont.interfaces().map(|(k, _)| k).collect();
    for (name, cap) in &acts {
        assert!(
            ifaces.contains(&cap.as_str()),
            "出厂动作 `{name}` 引用 `{cap}`，而它不在 `_interfaces` 里"
        );
    }

    red_then_green(
        "m08-ontology",
        &dir,
        |v| {
            v["_actions"]["notice.mute"]["capability"] = json!("no.such.capability");
        },
        "ext.world.Ontology.ActionCapabilityUnknown",
    );

    // 策略侧：`Policy::load` 单独跑（不经 `World::open`）
    let bad_pol = write_policy(&dir, "dangling-policy.json", |v| {
        v["actions"]["notice.mute"]["capability"] = json!("no.such.capability");
    });
    let e =
        world_core::gate::Policy::load(&bad_pol).expect_err("策略侧的动作引用不存在的能力必须被拒");
    assert!(
        e.contains("ext.world.Gate.ActionCapabilityUnknown") && e.contains("no.such.capability"),
        "实得：{e}"
    );

    // 交叉：闸侧声明了一项**本体里没有**的能力 ⇒ `World::open` 必须拒
    let hack_pol = write_policy(&dir, "hack-policy.json", |v| {
        v["capabilities"]["world.hack"] = json!({ "kind": "invoke" });
        v["actions"]["world.hack"] = json!({ "capability": "world.hack", "reversible": true });
    });
    let lp = dir.join("hack.jsonl");
    let e = world_core::World::open(&factory_ontology(), &lp, &hack_pol)
        .expect_err("闸侧多出一项本体里没有的能力必须拒启（两个权威不许各说各话）");
    assert!(
        e.contains("ext.world.Gate.CapabilityNotInOntology") && e.contains("world.hack"),
        "实得：{e}"
    );

    // 反例方向二：闸侧**声明了一项能力却没有任何动作引用它** ⇒ 死声明，拒启
    let dead_pol = write_policy(&dir, "dead-policy.json", |v| {
        v["capabilities"]["notice.mute"] = json!({ "kind": "invoke" });
        v["capabilities"]["notice.unmute"] = json!({ "kind": "invoke" });
        // `notice.unmute` 能力在 `_interfaces` 里有（出厂），但策略里删掉它的动作
        v["actions"]
            .as_object_mut()
            .unwrap()
            .remove("notice.unmute");
    });
    let e = world_core::gate::Policy::load(&dead_pol)
        .expect_err("声明了能力却没有任何动作引用它 ⇒ 死声明，必须拒载");
    assert!(
        e.contains("ext.world.Gate.CapabilityWithoutAction") && e.contains("notice.unmute"),
        "实得：{e}"
    );
}

// ────────────────────── ⑧ 函数入口表 ──────────────────────

/// **⑧**：**函数入口表里只有入口名**——出现**命令字面量** ⇒ 红
/// （`FunctionLiteralNotAllowed`）。命令今天硬编码在 Rust 里（`src/carrier/**`）。
///
/// 三条反例（含空白／含路径分隔／逐字等于已登记的宿主命令）＋ 恢复。
#[test]
fn m09_function_entries_admit_only_entry_names_never_command_literals() {
    let dir = tmpdir("m09");
    let ont = Ontology::load(&factory_ontology()).expect("出厂函数入口表必须能加载");
    let entries: Vec<&str> = ont.functions().map(|(k, _)| k).collect();
    assert!(
        entries.is_empty(),
        "出厂入口表今天为空（**如实登记**：无声明 = 没有可跑的入口引用），实得：{entries:?}"
    );

    for (tag, entry) in [
        ("plain", "pacman"),
        ("path", "/usr/bin/pacman"),
        ("flags", "pacman -S"),
        ("quoted", "sh -c 'true'"),
        ("backslash", "C:\\Windows\\cmd.exe"),
    ] {
        red_then_green(
            &format!("m09-{tag}"),
            &dir,
            |v| {
                v["_functions"]["entries"][entry] = json!({ "what": "夹具" });
            },
            "ext.world.Ontology.FunctionLiteralNotAllowed",
        );
    }

    // 正控：**入口名**（不带命令字面量）必须能加载。
    // ⚠️ 本批新判据（`DeadFunctionEntry`：入口必须被某条动作引用）生效后，**光声明入口不够**——
    //    这里同时给它一条**引用边**（`_actions.<动作>.function`），否则它会红成"死入口"
    //    （这正是新判据在起作用：**它把"声明"与"有人用"绑在一起**）。
    let good = write_ontology(&dir, "m09-entry-name.json", |v| {
        v["_functions"]["entries"]["carrier.apply_plan"] =
            json!({ "what": "把一份执行计划落到载体上（入口名，代码在 src/carrier/**）" });
        v["_actions"]["job.start"]["function"] = json!("carrier.apply_plan");
    });
    let o = Ontology::load(&good).expect("被动作引用的入口名必须能加载");
    assert_eq!(
        o.functions().map(|(k, _)| k).collect::<Vec<_>>(),
        vec!["carrier.apply_plan"],
        "入口名必须被装载器读到"
    );
    assert_eq!(
        o.actions()
            .find(|(n, _)| *n == "job.start")
            .and_then(|(_, a)| a.function.clone())
            .as_deref(),
        Some("carrier.apply_plan"),
        "引用边必须被装载器读到（**入口「活着」的判据就在这条边上**）"
    );
}

// ────────────────────── 附：出厂身份的**不变式** ──────────────────────

/// **附**：**分节挂 `_` 键 ⇒ 身份不变**这条**规律**仍成立（下面用一个「改名」变异钉住它）；
/// 但★**身份本身已经变过三次**（R5 加 `retract_seq`；第 12 轮加统一类型 `presence`；
/// 第 13 轮把 `presence` 的**语义**写进声明——`state` 闭集／`did` 元素形态／`last_seen` 口径）
/// ⇒ 现值为 `fnv1a64:6a96abfa9a969462`
/// （上一次改前 `fnv1a64:232f0902897632ad`，再上一次 `fnv1a64:8fd52bc278110ce8`，再再上一次 `fnv1a64:4bf7b75573fee475`）。
/// ★（2026-10-05 批注：该结论**第三次被本批变更推翻**——本批把 `presence` 的**语义**写进声明（`state` 由 `string` 收成闭集 `enum(...)`、`did` 由 `array` 收成 `array(string)`），而 `concepts` 是非 `_` 键 ⇒ 进身份 ⇒ 身份由 `fnv1a64:232f0902897632ad` 变为 `fnv1a64:6a96abfa9a969462`；**判据本身未放宽**。）
///
/// 这一条与 `tests/family_readmodel.rs` 的 `assert_eq!` **同源**（都钉出厂身份），
/// 但**角度不同**：那里钉"身份没变"，这里钉"**加 `_` 键**这件事是身份不变的原因"——
/// ★（2026-10-05 批注：该结论**第三次被本批变更推翻**——本批把 `presence` 的**语义**写进声明（`state` 由 `string` 收成闭集 `enum(...)`、`did` 由 `array` 收成 `array(string)`），而 `concepts` 是非 `_` 键 ⇒ 进身份 ⇒ 身份由 `fnv1a64:232f0902897632ad` 变为 `fnv1a64:6a96abfa9a969462`；**判据本身未放宽**。）
/// 把分节从 `_` 键挪到非 `_` 键（哪怕内容一模一样）⇒ 本用例当场红。
#[test]
fn m10_five_element_sections_live_under_underscore_keys_so_the_vocabulary_identity_is_unchanged() {
    let raw = factory_json();
    // ① 五要素分节**都在** `_` 前缀顶层键下
    for key in [
        "_objects",
        "_links",
        "_interfaces",
        "_actions",
        "_functions",
    ] {
        assert!(key.starts_with('_'), "五要素分节必须挂 `_` 键（本批定案）");
        assert!(
            raw.get(key).and_then(Value::as_object).is_some(),
            "出厂本体必须有 `{key}` 这一节"
        );
    }
    // ② 身份**跟着本体走**（★原写「逐字不变」——身份已先后变过**三次**，见下方批注）
    // ★（2026-10-05 批注：该结论**第三次被本批变更推翻**——本批把 `presence` 的**语义**写进声明（`state` 由 `string` 收成闭集 `enum(...)`、`did` 由 `array` 收成 `array(string)`），而 `concepts` 是非 `_` 键 ⇒ 进身份 ⇒ 身份由 `fnv1a64:232f0902897632ad` 变为 `fnv1a64:6a96abfa9a969462`；**判据本身未放宽**。）
    let ont = Ontology::load(&factory_ontology()).unwrap();
    assert_eq!(
        ont.vocab_hash(),
        "fnv1a64:6a96abfa9a969462",
        "分节挂 `_` 键这条**规律**不变（★身份本身已先后变过三次，见上方批注）"
    );
    // ③ 反例（**反向验证的机器版**）：把 `_links` 改名成非 `_` 键 `links`
    //    （内容一字不改）⇒ 身份**必变**。这就是"挂 `_` 键"承重的证据。
    //
    // ⚠️ 这里比的是 **`vocab_hash_of(原始 JSON)`**（不是 `Ontology::load().vocab_hash()`）：
    // 改名之后那条**存在性判据**会先拒启（装载器只找 `_links`）——那是对的，但它挡住的是
    // 本组要量**身份**这件事。⇒ 用纯函数直接对同一份 JSON 求值，把"键名 → 身份"这条因果
    // 单独量出来（`vocab_hash_of` 与装载器读的是**同一个函数**，见 `Ontology::load` 的尾部）。
    let renamed_raw = {
        let mut v = factory_json();
        let o = v.as_object_mut().unwrap();
        let links = o.remove("_links").unwrap();
        o.insert("links".to_string(), links);
        v
    };
    assert_ne!(
        world_core::ontology_definition::vocab_hash_of(&renamed_raw),
        "fnv1a64:6a96abfa9a969462",
        "把分节从 `_` 键挪到非 `_` 键（内容一字不改）⇒ 身份**必变**——\
         这正是『挂 `_` 键』这条口径承重的证据"
    );
    // 而**没改名**的那一份（同一份出厂 JSON）⇒ 身份逐字不变（正控：上面的变化不是噪声）
    assert_eq!(
        world_core::ontology_definition::vocab_hash_of(&factory_json()),
        "fnv1a64:6a96abfa9a969462",
        "出厂本体的身份必须逐字不变"
    );
    // ④ 而只改**说明文字**（`_` 键里的值）不该变（避免假警报）
    let dir = tmpdir("m10");
    let comment = write_ontology(&dir, "comment-only.json", |v| {
        v["_five_elements"]["_why_underscore"] = json!("换了一段说明文字，语义没动");
    });
    assert_eq!(
        Ontology::load(&comment).unwrap().vocab_hash(),
        "fnv1a64:6a96abfa9a969462",
        "只改 `_` 键里的说明文字不该换身份"
    );
    // ⑤ 顺便钉住"按类型实例计数"这个读数面在**纯数据**上也成立（不依赖 `World`）
    let cells = world_core::ontology_instance::readmodel::DeclaredCells::new(
        vec!["world".into()],
        BTreeMap::new(),
    );
    assert!(cells.instance_limit("notice").is_none());
}

// ──────────── ⑨ 两处对象声明不许各说各话（`_objects` ↔ `concepts`）────────────

/// **⑨**：`concepts`（**身份**认它、非 `_` 键）与 `_objects`（**读路径**认它、`_` 键）里
/// **同名字段的类型声明必须逐字一致**；不一致 ⇒ 拒启（`ext.world.Ontology.ConceptsDrift`）。
///
/// ## 为什么需要它（本批补的那条缝）
///
/// 上一版实现里我把两处说成"**两份不会给出不同答案**"——**那句不成立**：
/// 身份取 `concepts`、读路径取 `_objects` ⇒
/// **只改 `_objects` 则身份不变而读到的语义变了；只改 `concepts` 则读到的语义不变而身份变了。**
/// 本用例把这条缝**钉成会红的判据**：只改其中一处 ⇒ 必须拒启。
///
/// ## 射程（与本判据的 doc 同一口径，不许被读成"两处完全等价"）
///
/// 只判"**两处都有**的那个字段的类型声明"。新字段只声明在 `_objects` 里 ⇒ 不判；
/// 类型只在一处出现 ⇒ 不判；`instance_mode`／`nested`／`part_of` 不同步 ⇒ 不判（那三样只长在 `_objects`）。
#[test]
fn m11_the_two_object_declarations_must_not_contradict_each_other() {
    let dir = tmpdir("m11");

    // 正控①：出厂本体两处逐字一致 ⇒ 必须能加载
    Ontology::load(&factory_ontology()).expect("出厂本体：两处同名字段的类型声明逐字一致");

    // 正控②：**只往 `_objects` 加一个新字段**（`concepts` 里没有它）⇒ 不判，必须能加载
    //（射程表第 3 行：新字段本该只声明一次）
    let new_field = write_ontology(&dir, "new-field-only.json", |v| {
        v["_objects"]["job"]["fields"]["owner"] = json!("ref(notice)");
    });
    Ontology::load(&new_field).expect("只在 `_objects` 里新增字段不得被判成'各说各话'");

    // 反例①：**只改 `_objects`**（读到的语义变了、身份没变）⇒ 必须拒启
    let only_modern = write_ontology(&dir, "only-modern.json", |v| {
        v["_objects"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
    });
    let e = Ontology::load(&only_modern)
        .expect_err("只改 `_objects` ⇒ 两处各说各话，必须拒启（不许静默取一处当准）");
    assert!(
        e.contains("ext.world.Ontology.ConceptsDrift"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("`job`") && e.contains("`status`"),
        "理由要**点名**是哪个类型、哪个字段，实得：{e}"
    );
    assert!(
        e.contains("enum(todo,doing,done)") && e.contains("enum(todo,doing,done,cancelled)"),
        "理由要把**两处各写了什么**都摆出来（否则读的人不知道该改哪一处），实得：{e}"
    );

    // 反例②：**只改 `concepts`**（身份变了、读到的语义没变）⇒ 同样必须拒启
    let only_frozen = write_ontology(&dir, "only-frozen.json", |v| {
        v["concepts"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
    });
    let e2 = Ontology::load(&only_frozen)
        .expect_err("只改 `concepts` ⇒ 两处各说各话，同样必须拒启（两个方向都要判）");
    assert!(
        e2.contains("ext.world.Ontology.ConceptsDrift") && e2.contains("`status`"),
        "实得：{e2}"
    );

    // 反例③：改的是**另一个类型/字段**（`notice.muted`）⇒ 一样判（不是只盯 `job.status` 这一格）
    let only_muted = write_ontology(&dir, "only-muted.json", |v| {
        v["_objects"]["notice"]["fields"]["muted"] = json!("string");
    });
    let e3 = Ontology::load(&only_muted).expect_err("换一个类型/字段同样必须被拒");
    assert!(
        e3.contains("ext.world.Ontology.ConceptsDrift") && e3.contains("`muted`"),
        "实得：{e3}"
    );

    // 恢复那一半：**两处一起改成同一个值** ⇒ 必须能加载（防"什么都拒"的假绿）
    let both = write_ontology(&dir, "both-changed.json", |v| {
        v["_objects"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
        v["concepts"]["job"]["fields"]["status"] = json!("enum(todo,doing,done,cancelled)");
    });
    let o = Ontology::load(&both).expect("两处一起改到同一个值 ⇒ 必须能加载");
    assert!(
        o.declared_fields("job")
            .unwrap()
            .get("status")
            .is_some_and(|t| t.contains("cancelled")),
        "读路径必须看到改后的声明（否则'一起改'是假的）"
    );
    // 且这时**身份确实变了**（`concepts` 参与 `vocab_hash`）——把两处的关系说全：
    assert_ne!(
        o.vocab_hash(),
        "fnv1a64:6a96abfa9a969462",
        "两处一起改 ⇒ 身份必变（身份取 `concepts`）——这正是'只改 `_objects` 不改身份'的另一面"
    );
}

// ──────────── ⑩ 十二节的归属写死（`_section_map` ↔ 实际 `_` 分节）────────────

/// **⑩**：`_section_map`（十二节归属的**权威**）声明的 `_` 分节键集合，必须**逐项等于**
/// 文件里**实际存在**的 `_` 分节键集合 ⇒ 不一致即拒启（`ext.world.Ontology.SectionMapDrift`）。
///
/// ## 为什么这条判据必须存在
///
/// 光把归属**写进**本体是**装饰**：文件里新加一个 `_` 分节、或表里指错一个键，
/// 都不会有东西变红 ⇒ "归属已定"那句话会**悄悄变成假话**。
/// ⇒ 本用例钉的是**双向**：表里多一处、文件里多一处，两个方向都必须红。
///
/// ## 射程（不许被读成"归属选得对不对"）
///
/// 它判**集合**，**不判**"某节该算元层还是接入层"——那是人的判断（`attach: "out"` 的节
/// 到底归哪一层，机器判不了，表里写死供人读）。
#[test]
fn m12_the_twelve_sections_attribution_table_must_match_the_real_underscore_sections() {
    let dir = tmpdir("m12");

    // 正控①：出厂本体（表与文件一致）⇒ 必须能加载
    Ontology::load(&factory_ontology()).expect("出厂本体：归属表与 `_` 分节集合一致");

    // 正控②：表本身**可读**——十二节、每节都有 `home` 与（`keys` 或 `_where`）
    let raw = factory_json();
    let secs = raw["_section_map"]["sections"]
        .as_object()
        .expect("出厂本体必须有 `_section_map.sections`");
    let named: Vec<&String> = secs.keys().filter(|k| !k.starts_with('_')).collect();
    assert_eq!(
        named.len(),
        12,
        "归属表必须把**十二节**写全，实得：{named:?}"
    );
    for (name, def) in secs {
        if name.starts_with('_') {
            continue;
        }
        assert!(
            def.get("home").and_then(Value::as_str).is_some(),
            "分节 `{name}` 必须写 `home`（归属）"
        );
        assert!(
            def.get("attach").and_then(Value::as_str).is_some(),
            "分节 `{name}` 必须写 `attach`（整挂／半挂／挂不进）"
        );
    }

    // 反例①：**新加一个 `_` 分节而不在表里列名** ⇒ 必须拒启（这条最强：分节不许悄悄长出来）
    let new_section = write_ontology(&dir, "new-section.json", |v| {
        v["_scratch"] = json!({ "anything": 1 });
    });
    let e = Ontology::load(&new_section)
        .expect_err("新加 `_` 分节而不在归属表里列名 ⇒ 必须拒启（否则'归属已定'是假话）");
    assert!(
        e.contains("ext.world.Ontology.SectionMapDrift"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("_scratch"),
        "理由必须**点名**那个没被归属的分节，实得：{e}"
    );

    // 反例②：表里把一个分节指到**别的**分节（`_links` 于是没人认领）⇒ 必须拒启
    let wrong_key = write_ontology(&dir, "wrong-key.json", |v| {
        v["_section_map"]["sections"]["关系"]["keys"] = json!(["_actions"]);
    });
    let e2 = Ontology::load(&wrong_key).expect_err("表里指错键 ⇒ `_links` 无人认领，必须拒启");
    assert!(
        e2.contains("ext.world.Ontology.SectionMapDrift") && e2.contains("_links"),
        "理由要点名没人认领的那个分节，实得：{e2}"
    );

    // 反例③：表里声明一个**文件里没有**的分节 ⇒ 必须拒启（空指针方向）
    let phantom = write_ontology(&dir, "phantom.json", |v| {
        v["_section_map"]["sections"]["关系"]["keys"] = json!(["_no_such_section"]);
    });
    let e3 = Ontology::load(&phantom).expect_err("表里声明了文件里没有的分节 ⇒ 必须拒启");
    assert!(
        e3.contains("ext.world.Ontology.SectionMapDrift") && e3.contains("_no_such_section"),
        "实得：{e3}"
    );

    // 反例④：`home` 不在 `_homes` 封闭表里 ⇒ 必须拒启（归属不许自由发挥）
    let bad_home = write_ontology(&dir, "bad-home.json", |v| {
        v["_section_map"]["sections"]["关系"]["home"] = json!("随便哪一层");
    });
    let e4 = Ontology::load(&bad_home).expect_err("`home` 必须取自封闭表");
    assert!(
        e4.contains("ext.world.Ontology.SectionMapDrift") && e4.contains("随便哪一层"),
        "实得：{e4}"
    );

    // 反例⑤：既没 `keys` 也没 `_where`（归属留空）⇒ 必须拒启
    let no_carrier = write_ontology(&dir, "no-carrier.json", |v| {
        v["_section_map"]["sections"]["订阅形状"]
            .as_object_mut()
            .unwrap()
            .remove("_where");
    });
    let e5 = Ontology::load(&no_carrier).expect_err("归属表不许留空（要么给 keys、要么给 _where）");
    assert!(
        e5.contains("ext.world.Ontology.SectionMapDrift") && e5.contains("订阅形状"),
        "实得：{e5}"
    );

    // 反例⑥：`attach` 写成三值之外 ⇒ 必须拒启
    let bad_attach = write_ontology(&dir, "bad-attach.json", |v| {
        v["_section_map"]["sections"]["关系"]["attach"] = json!("mostly");
    });
    let e6 = Ontology::load(&bad_attach).expect_err("`attach` 只认 full／half／out");
    assert!(
        e6.contains("ext.world.Ontology.SectionMapDrift") && e6.contains("mostly"),
        "实得：{e6}"
    );

    // 恢复那一半：**只加说明文字**（在 `_not_domain_sections` 里列名）⇒ 必须能加载
    //（防"什么都拒"的假绿：说明类 `_` 键是合法增补，只要**列名**）
    let listed = write_ontology(&dir, "listed-annotation.json", |v| {
        v["_section_map"]["_not_domain_sections"]["_my_note"] = json!("一条说明");
        v["_my_note"] = json!("一条说明");
    });
    Ontology::load(&listed).expect("已在 `_not_domain_sections` 里列名的说明键 ⇒ 必须能加载");

    // 并钉住：这条判据判的是**集合**，不是"归属选得对不对"——出厂表里 4 节 `attach: "out"`
    let out_count = secs
        .iter()
        .filter(|(k, d)| {
            !k.starts_with('_') && d.get("attach").and_then(Value::as_str) == Some("out")
        })
        .count();
    assert_eq!(
        out_count, 4,
        "出厂归属表：**挂不进五要素**的必须是 4 节（接入映射／读法定义／旁道与收据与缓存／验法），实得 {out_count}"
    );
}

// ───── ⑪ 结构性死声明与悬空引用（会红）／⑫ usage 只报告（不许红）─────

/// **⑪**：**结构性死声明与悬空引用** ⇒ 拒启。
///
/// 三条判据（`src/ontology_definition/mod.rs::check_structural_liveness`）：
/// 1. `_functions.entries` 里的入口**必须被至少一条动作引用**（`DeadFunctionEntry`）；
/// 2. 动作声明的 `function` **必须真的在** `_functions.entries` 里（`DanglingFunctionRef`）；
/// 3. `_interfaces` 里的能力**必须至少被动作或许可之一引用**（`DeadCapability`）。
///
/// ## ★ 与"声明了但零使用"的分界（本用例第 ⑫ 组钉的是那一半）
///
/// 本组判的是**结构性不可达**（没有任何引用边 ⇒ 永远走不到）；
/// 第 ⑫ 组判的是"实例还没用上"——**法律的本分是先声明后使用**，那一半**不许红**。
/// 一句记法：**"没人能走到它"是缺陷；"还没人走到它"是常态。**
#[test]
fn m13_dead_entries_dangling_refs_and_dead_capabilities_are_refused() {
    let dir = tmpdir("m13");

    // 正控①：出厂本体——入口表为空、能力全被动作引用 ⇒ 必须能加载
    Ontology::load(&factory_ontology()).expect("出厂本体：无死入口、无悬空引用、无死能力");
    let ont = Ontology::load(&factory_ontology()).unwrap();
    assert_eq!(
        ont.functions().count(),
        0,
        "出厂入口表今天为空（**如实**：还没有任何入口被声明过）"
    );
    // 出厂**每一项**能力都能指到一条动作（这是"无死能力"的可枚举形态；
    // ⚠️ **不写死条数**——条数由 `ont.interfaces().count()` 现取，本体一改就不会过期）
    for (name, _) in ont.interfaces() {
        assert!(
            ont.actions().any(|(_, a)| a.capability == name),
            "出厂能力 `{name}` 必须至少被一条动作引用"
        );
    }

    // 反例①：**死入口**——声明一个入口，没有任何动作引用它 ⇒ 拒启
    let dead_entry = write_ontology(&dir, "dead-entry.json", |v| {
        v["_functions"]["entries"]["carrier.apply_plan"] = json!({ "what": "夹具" });
    });
    let e = Ontology::load(&dead_entry).expect_err("没人引用的入口 ⇒ 必须拒启（结构性不可达）");
    assert!(
        e.contains("ext.world.Ontology.DeadFunctionEntry") && e.contains("carrier.apply_plan"),
        "理由要带码并**点名**那个入口，实得：{e}"
    );
    // 恢复绿：让某条动作引用它 ⇒ 必须能加载（证明上面红的是**这一格**）
    let live_entry = write_ontology(&dir, "live-entry.json", |v| {
        v["_functions"]["entries"]["carrier.apply_plan"] = json!({ "what": "夹具" });
        v["_actions"]["job.start"]["function"] = json!("carrier.apply_plan");
    });
    let o = Ontology::load(&live_entry).expect("被动作引用的入口 ⇒ 必须能加载");
    assert_eq!(
        o.actions()
            .find(|(n, _)| *n == "job.start")
            .and_then(|(_, a)| a.function.clone())
            .as_deref(),
        Some("carrier.apply_plan"),
        "引用边必须被装载器读到（否则本判据是空的）"
    );

    // 反例②：**悬空引用**——动作指向一个不存在的入口 ⇒ 拒启
    let dangling = write_ontology(&dir, "dangling.json", |v| {
        v["_actions"]["job.start"]["function"] = json!("no.such.entry");
    });
    let e2 = Ontology::load(&dangling).expect_err("动作引用不存在的入口 ⇒ 必须拒启");
    assert!(
        e2.contains("ext.world.Ontology.DanglingFunctionRef")
            && e2.contains("no.such.entry")
            && e2.contains("job.start"),
        "理由要点名动作与入口两侧，实得：{e2}"
    );

    // 反例③：**死能力**——加一项能力，既无动作、又不在许可里 ⇒ 拒启
    let dead_cap = write_ontology(&dir, "dead-cap.json", |v| {
        v["_interfaces"]["job.pause"] = json!({ "kind": "invoke", "what": "夹具：没人能用到它" });
    });
    let e3 =
        Ontology::load(&dead_cap).expect_err("既无动作、又无许可的能力 ⇒ 必须拒启（法律上不可达）");
    assert!(
        e3.contains("ext.world.Ontology.DeadCapability") && e3.contains("job.pause"),
        "理由要带码并**点名**那个能力，实得：{e3}"
    );

    // ★ 反例③的**两半必须分开判**（否则这条判据的射程说不清）：
    //   甲半：**只**给它一条动作 ⇒ 绿（动作那一半够用）
    let by_action = write_ontology(&dir, "cap-by-action.json", |v| {
        v["_interfaces"]["job.pause"] = json!({ "kind": "invoke", "what": "夹具" });
        v["_actions"]["job.pause"] = json!({ "capability": "job.pause", "reversible": true });
    });
    Ontology::load(&by_action).expect("有动作引用它 ⇒ 必须能加载（动作那一半够用）");
    //   乙半：**只**给它一项许可（不给动作）⇒ 同样绿（许可那一半也够用）
    let by_perm = write_ontology(&dir, "cap-by-perm.json", |v| {
        v["_interfaces"]["job.pause"] = json!({ "kind": "invoke", "what": "夹具" });
        v["_permissions"]["grants"]["job.pause"] = json!({ "who": ["world://user"] });
    });
    let o2 = Ontology::load(&by_perm).expect(
        "有许可授予它 ⇒ 必须能加载（**许可那一半也算可达**——这正是与策略侧那条判据的分工）",
    );
    assert!(
        o2.permissions().any(|(k, _)| k == "job.pause"),
        "许可条文必须被装载器读到"
    );
}

/// **⑫**：`world-core usage` 是**「只报告、绝不红」**——这条用例是**正控**
/// （它证明那份清单**不会**误红），不是"某条门禁已达成"。
///
/// ## 为什么它必须 rc=0（口径，不是妥协）
///
/// **法律的本分就是「先声明、后使用」**：一个类型、一格字段可以先被法律允许，
/// 再等第一次真实使用。把它判红，等于**禁止"先声明"**，
/// 那会毁掉「往上是领域概念各自生长」这条既有口径。
///
/// ⇒ 本用例造一份"**声明了、但账本里零使用**"的本体（新增类型与字段，一行账本都不写），
/// 断言 **rc=0** 且清单**确实把那些名字印出来**（否则"不红"可能只是"清单是空的"）。
#[test]
fn m14_usage_lists_unused_declarations_but_never_fails() {
    let dir = tmpdir("m14");

    // 造本体：加一个**从不使用**的类型 `audit`（带一格从不使用的字段）。
    // ⚠️ 同时要在归属表里给它一条记录（否则 `SectionMapDrift` 会先红）——
    //    这不是"顺手加"，是新判据逼出来的**法律完备性**。
    let ont_path = write_ontology(&dir, "with-unused.json", |v| {
        v["_objects"]["audit"] = json!({ "fields": { "who": "string" }, "instance_mode": "many" });
        v["_section_map"]["sections"]["类型（对象）"]["keys"] = json!(["_objects"]);
    });
    // 账本：只写 `notice` 那一格——`audit` 类型与它的 `who` 字段**零使用**。
    let lp = dir.join("ledger.jsonl");
    {
        let mut w = world_core::World::open(&ont_path, &lp, &factory_policy())
            .expect("这份本体是合法的（它只是'声明得多、用得少'）");
        w.commit(
            "change",
            "world://user",
            world_core::common::event::change_body(
                "world://notice/n-1",
                "muted",
                json!(null),
                json!(true),
            ),
        )
        .unwrap();
    }

    // ★ 正控：**必须 rc=0**（这一条就是"它不误红"的判据）
    let (rc, out) = cli_usage(&ont_path, &lp, &factory_policy());
    assert_eq!(
        rc, 0,
        "`usage` 是**只报告**：'声明了但零使用'是**合法状态** ⇒ 必须 rc=0。实得 rc={rc}\n{out}"
    );
    // 清单必须**真的印出来**那些名字（否则上面那句 rc=0 可能只是因为清单是空的）
    assert!(
        out.contains("audit"),
        "清单必须点名零使用的类型 `audit`，实得：\n{out}"
    );
    assert!(
        out.contains("who"),
        "清单必须点名零使用的字段 `who`，实得：\n{out}"
    );
    // 且它必须**自称不是判据**（口径要写在输出里，不能只写在代码注释里）
    assert!(
        out.contains("不是判据"),
        "输出里必须写明'这不是判据'，实得：\n{out}"
    );
    assert!(
        out.contains("先声明、后使用"),
        "输出里必须写明它为什么不能红（法律的本分是先声明后使用），实得：\n{out}"
    );
    // 对照：**用过**的那一格不该被列进零使用清单
    assert!(
        !out.contains("[字段] `notice.muted`"),
        "`notice.muted` 已经被写过 ⇒ **不得**被列进零使用清单，实得：\n{out}"
    );
    // 把清单原文带回来（VM 轮的原始输出另见 EV-009）
    println!("---- usage 清单原文 ----\n{out}");
}

/// **⑭（第 2 件 · `describe`）**：返回形状＝**`_interfaces` ∩ 许可条文**
/// （作者 2026-10-03 裁定·**读法甲**），**只读法律**、**不自造**。
///
/// ## 口径（写死在两处：`cmd_describe` 的文档 ＋ 本用例）
///
/// - **未被授予 ⇒ 不出现在返回里，且不报红**（那是「**合法地未授**」：定义面与授权面是两件事）；
/// - **报红只有一种**：声明了却**动作与许可两条路都不通** ⇒ 由 `Ontology::load` 的
///   `DeadCapability` 管，`describe` **不重复造**（故本条**不**给 `describe` 造红判据）；
/// - ★ **为什么不判「两头必须一致」**：那会与 `DeadCapability` 的「动作 ∪ 许可」口径**互相矛盾**，
///   且等于**要求法律不许先声明**——正是另一条口径（法律的本分是先声明后使用）明令不许的。
///
/// ## 反例与正控（本条会红的两处）
///
/// - **反例**：**未授予**的能力出现在返回里 ⇒ 红；
/// - **正控**：**已授予**的能力**必须**在返回里 ⇒ 缺了也红。
/// - 两侧都**现算**，**不写死条数**（写死的读数必然过期）。
#[test]
fn m16_describe_returns_the_intersection_of_interfaces_and_grants() {
    use std::collections::BTreeSet;
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let inter: BTreeSet<&str> = ont.interfaces().map(|(k, _)| k).collect();
    let granted: BTreeSet<&str> = ont.permissions().map(|(k, _)| k).collect();
    assert!(
        !inter.is_empty(),
        "出厂本体必须声明了能力（否则本用例是空转）"
    );
    assert!(
        inter.is_superset(&granted),
        "许可授予的能力必须先在 `_interfaces` 里声明（装载期那条判据管着）"
    );
    // 反例要**非空**才有意义：未授予的那部分必须真的存在（否则下面那条断言是空转）
    assert!(
        granted.len() < inter.len(),
        "出厂本体今天确有「已声明未授予」的能力（否则下面那条反例是空转）"
    );

    let out = cli_describe(&factory_ontology());
    // 正控：**已授予的必须在**（缺了 ⇒ 红）
    for g in &granted {
        assert!(
            out.contains(&format!("    {g}")),
            "已授予的能力 `{g}` **必须**出现在 `describe` 的返回里，实得：\n{out}"
        );
    }
    // ★ 反例：**未授予的不得出现**（出现了 ⇒ 红）
    for u in inter.difference(&granted) {
        assert!(
            !out.contains(&format!("    {u}")),
            "**未授予**的能力 `{u}` **不得**出现在返回里（那是「合法地未授」，不是错误）：\n{out}"
        );
    }
    // 口径要求：未授予的那部分要**如实说明**，不能被读成「世界没有这项能力」
    assert!(
        out.contains("合法地未授"),
        "返回里必须写明未授予的是「合法地未授」：\n{out}"
    );
    assert!(
        out.contains("不重复造"),
        "返回里必须写明唯一的红由 `DeadCapability` 管、本命令不重复造：\n{out}"
    );
    println!("---- describe 返回原文 ----\n{out}");
    println!(
        "（**现取**读数，不写死：已声明 {} 项、已授予 {} 项）",
        inter.len(),
        granted.len()
    );
}

/// **⑮（第 2 件 · `read` 实例面＋前值）**：把「从什么变成什么」的**前值摆到出口上**。
///
/// ## 口径出自书 `:70`（逐字）
///
/// 「（这是它要做到的样子。今天能证明的还只是"各方读的是同一份输入"；
/// **"从什么变成什么"里的前值，还没有出现在任何一份出口上**。）」
/// ⇒ 要的是「**出现在出口上**」，**不是**"藏在事件 JSON 里让人自己翻"。
///
/// ## 两条判据（都会红）
///
/// - **①前值可直读**：拿**真账本**里一条既有 `change` 去问「这个字段原来是什么」⇒
///   实例面上答出的 `原来=<值>` 必须**与账本里那条 `before` 逐字相同**；
///   答不出、或**答成当前值** ⇒ **红**；
/// - **②正控**：**既有事件面输出逐字节不变** ⇒ 变了即红。
///
/// ## 为什么正控是"逐字节"
///
/// 「只增不改」**只有逐字节比对才可判**；近似比对会把"我改了默认输出"这种真违规放过去。
#[test]
fn m17_read_instance_face_shows_the_prior_value_and_the_default_output_is_unchanged() {
    use world_core::common::event::change_body;
    let dir = tmpdir("m17");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    // 真账本：先 `muted=false`，再 `muted=true` ⇒ 第二条的 `before` 是 `false`（前值）
    {
        let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(null), json!(false)),
        )
        .unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(false), json!(true)),
        )
        .unwrap();
    }
    // 账本里那条 `before` 的**逐字**值（**以账本为准**，不以我的实现在准）
    let raw = std::fs::read_to_string(&lp).unwrap();
    let last_before = raw
        .lines()
        .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
        .filter_map(|v| {
            v.pointer("/body/before")
                .or_else(|| v.get("before"))
                .cloned()
        })
        .next_back()
        .expect("账本里必须有 `before`（否则本用例是空转）");
    assert_eq!(
        last_before,
        json!(false),
        "夹具自检：最后一条 `change` 的 `before` 应当是 `false`"
    );

    // ①前值可直读
    let inst = cli_read(&ont, &lp, &pol, &["--instances"]);
    assert!(
        inst.contains("原来=false"),
        "实例面上必须**直接**答得出「原来=false」——这正是书 `:70` 要的『前值出现在出口上』：\n{inst}"
    );
    assert!(
        inst.contains("现在=true"),
        "实例面同时要给出「现在=true」：\n{inst}"
    );
    assert!(
        !inst.contains("原来=true"),
        "**答成当前值 ⇒ 红**：前值不是当前值：\n{inst}"
    );

    // ②正控：**默认调用（不带 `--instances`）逐字节等于"只打事件"**
    let default_out = cli_read(&ont, &lp, &pol, &[]);
    let only_events: String = raw
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| {
            let v: serde_json::Value = serde_json::from_str(l).unwrap();
            format!("{}\n", serde_json::to_string(&v).unwrap())
        })
        .collect();
    assert_eq!(
        default_out, only_events,
        "**正控（只增不改）**：不带 `--instances` 时输出必须与『一行一条事件 JSON』**逐字节相同**"
    );
    assert!(
        !default_out.contains("实例面"),
        "默认输出里**不许**混进实例面（那就是改了既有形状）：\n{default_out}"
    );
    println!("---- read --instances 原文 ----\n{inst}");
}

/// **⑯（第 3 件 · `subscribe`）**：位点在**收件人自己**、缺位点必拒、**世界停掉不许显示旧数**。
///
/// ## 三条判据（都会红）
///
/// - **①缺位点必拒**：不带 `--since` ⇒ **rc≠0** 且**点名** `ext.world.Subscribe.NoSinceSeq`；
/// - **②正控**：`--since 2` ⇒ **rc=0**，且输出**只含** `seq ≥ 2` 的事件（`"seq":1` 一条都不许有）；
/// - **③世界停掉后不许显示旧数**：账本**读不到** ⇒ **rc≠0**、**一个事件行都没有**
///   （不许拿缓存／上一次的数冒充现在），并点名 `NoStale`。
///
/// ## 口径出处
///
/// 本体 `_subscribe`（挂 `_` 键，「接口·能力」节认领）：`since_seq.required=true`、
/// 「位点记在收件人自己」「叫醒可漏、由订户按 `seq` 补读」「读不到就说读不到」。
#[test]
fn m18_subscribe_requires_a_cursor_and_never_shows_stale_numbers() {
    use world_core::common::event::change_body;
    let dir = tmpdir("m18");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    {
        let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(null), json!(false)),
        )
        .unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(false), json!(true)),
        )
        .unwrap();
    }

    // ① 缺位点 ⇒ 拒并点名
    let (rc1, out1) = cli_sub_raw(&ont, &lp, &pol, &[]);
    assert_ne!(rc1, 0, "缺 `--since` 必须拒；实得 rc={rc1}\n{out1}");
    assert!(
        out1.contains("ext.world.Subscribe.NoSinceSeq"),
        "必须点名那条错误码，实得：\n{out1}"
    );

    // ② 正控：位点齐 ⇒ rc=0，且**只含** seq ≥ 2
    let (rc2, out2) = cli_sub_raw(&ont, &lp, &pol, &["--since", "2"]);
    assert_eq!(rc2, 0, "位点齐时必须 rc=0；实得 rc={rc2}\n{out2}");
    let lines: Vec<&str> = out2.lines().filter(|l| !l.trim().is_empty()).collect();
    assert!(
        !lines.is_empty(),
        "位点齐时必须给出事件（否则本用例是空转）"
    );
    for l in &lines {
        assert!(
            l.contains("\"seq\":2"),
            "**只**许给 `seq ≥ 2` 的事件；这条不是：{l}"
        );
        assert!(!l.contains("\"seq\":1"), "`seq=1` **不得**出现：{l}");
    }

    // ③ 世界停掉（账本**读不出**）⇒ 拒，且**一个事件行都不许有**（不许显示旧数）
    //
    // ★ **夹具的关键（本轮改的就是它）**：造"读不到"必须用「**存在但读不出**」，
    //   **不能**用"路径不存在"——**空账本＝一个新世界，是合法状态**（实测：指向不存在的
    //   路径 ⇒ `rc=0`，因为世界从头开始）。用不存在的路径造"世界停掉"，就是
    //   「**反例与真实违规不同形态**」⇒ 那一格**验不到**。这里选**目录**（`open` ⇒ EISDIR）。
    // ⚠️ **不许用 `chmod 000` 造这一格**：测试可能**以 root 跑**，而 **root 绕过文件权限**
    //   ⇒ 会造出**假绿**（看着"读不到"，其实读得到）。
    let gone = dir.join("this-is-a-directory-not-a-ledger");
    std::fs::create_dir_all(&gone).unwrap();
    let (rc3, out3) = cli_sub_raw(&ont, &gone, &pol, &["--since", "1"]);
    assert_ne!(rc3, 0, "账本读不到必须拒；实得 rc={rc3}\n{out3}");
    assert!(
        out3.contains("NoStale"),
        "必须点名 `NoStale`（读不到就说读不到），实得：\n{out3}"
    );
    assert!(
        !out3.contains("\"seq\":"),
        "**世界停掉后不许显示旧数**：一个事件行都不许出现，实得：\n{out3}"
    );
    println!("---- subscribe --since 2 原文 ----\n{out2}");
}

/// **⑰（A-05 的**服务路径**）**：`serve` 必须与 `check` **同口径**地校验 `--owner-uid`。
///
/// ## 这条补的是什么（真缺陷）
///
/// 「`--owner-uid` 打错即拒启」原先**只写在 `"check"` 分支里**，而 `"serve"` 的调用
/// **签名里没有 `owner_uid`** ⇒ **服务路径上它被静默丢弃**，属主断言 **A-05 在真正跑的那条
/// 路径上从未执行**（另一席在 VM 上实测发现，本席逐行自核成立）⇒ 与"闸只在一条路径上"同族。
///
/// ## 两条判据
///
/// - **①反例（会红）**：非数字 `--owner-uid` 走 `serve` ⇒ **rc≠0 且点名**
///   `ext.world.Serve.BadOwnerUid`（**修复前它是静默通过的**——这就是那条缺陷的现场）；
/// - **②越关**：数字 uid 走 `serve` ⇒ **不出现** `BadOwnerUid`，且理由变成
///   `NoListenFds` 或属主断言（**两者都算"越过了 uid 那一关"**；本条**不假定**它后面必然走到哪一步）。
#[test]
fn m19_serve_refuses_a_non_numeric_owner_uid() {
    let d = tmpdir("m19");
    let bin = env!("CARGO_BIN_EXE_world-core");
    let run = |uid: &str| -> (i32, String) {
        let out = std::process::Command::new(bin)
            .arg("--ontology")
            .arg(d.join("nope-ontology.json"))
            .arg("--ledger")
            .arg(d.join("l.jsonl"))
            .arg("--policy")
            .arg(d.join("nope-policy.json"))
            .arg("--owner-uid")
            .arg(uid)
            .arg("serve")
            // 清掉可能继承来的两个变量：本条判的是 **uid 那一关**，不是 LISTEN_FDS 那一关。
            .env_remove("LISTEN_FDS")
            .env_remove("LISTEN_PID")
            .output()
            .expect("跑得起来 world-core serve");
        let mut t = String::from_utf8_lossy(&out.stdout).to_string();
        t.push_str(&String::from_utf8_lossy(&out.stderr));
        (out.status.code().unwrap_or(-1), t)
    };

    // ① 非数字 ⇒ 拒启并点名（**修复前走 serve 时它是被静默丢弃的**）
    let (rc1, out1) = run("notanumber");
    assert_ne!(
        rc1, 0,
        "非数字 `--owner-uid` 走 serve 必须拒启；实得 rc={rc1}\n{out1}"
    );
    assert!(
        out1.contains("ext.world.Serve.BadOwnerUid"),
        "必须点名 `ext.world.Serve.BadOwnerUid`，实得：\n{out1}"
    );

    // ② 数字 uid ⇒ 越过该关（那条码**不许**出现）
    let (_rc2, out2) = run("965");
    assert!(
        !out2.contains("BadOwnerUid"),
        "数字 uid **不该**触发那条拒启（它应越过 uid 那一关），实得：\n{out2}"
    );
    assert!(
        out2.contains("NoListenFds") || out2.contains("属主"),
        "数字 uid 必须**越过** uid 那一关（走到 `NoListenFds` 或**属主断言**那一步都算——\
         后者在夹具里会报「无法读取 … 的属主」，故这里匹配「属主」二字，不写死整句），实得：\n{out2}"
    );
}

/// **⑱（`check` 的 `READY` 必须覆盖"读模型能否折叠"）**——修一条**假绿**；
/// ★ **第 13 轮起这一格多了一半：写入侧自己就把这种事件拦住了。**
///
/// ## 现场（真缺陷）
///
/// `check` 报了 **`READY`**，而 `/usr/local/bin/world-projection` 是**离线**的。根因：`cmd_check`
/// 只核了"本体／门禁／互校／账本／链"，**从不调用 `w.read_model()`** ⇒ **"读模型能否折叠"**
/// 这一格**不在 `READY` 的覆盖范围内** ⇒ 账本里一条坏事件就让读模型**整本折叠不了**，
/// 而 `check` 照旧 `READY` ⇒ **假绿**（"check 绿 ≠ 世界能用"）。
///
/// ## 判据（两条，条条会红）
///
/// | # | 判据 | 反例（必红） |
/// |---|---|---|
/// | ① | ★**写入侧**：经唯一写入口提交一条 `before` 与账本折叠出的当前值**不符**的 `change` ⇒ **拒**（`ext.world.World.BeforeMismatch`，点名 `subject#path`、声称的 `before`、实际的当前值）；`before` **相符** ⇒ **通** | 把 `World::check_before` 短路 ⇒ 第二段当场红 |
/// | ② | ★**读侧仍要有第二道墙**：账本**被写入侧之外的东西**改过（手造一行、**补上正确的摘要链**）⇒ `check` **不许**打印 `READY`，rc≠0，且**病因必须是 `BeforeMismatch`** | 把 `cmd_check` 那道自检删掉 ⇒ 第三段红 |
///
/// ## ★ 本用例**重做**过两次（留痕；两次都是"反例与真实违规不同形态"）
///
/// ① 初版把那条坏事件**手写**进账本（`std::fs::write` 追加一行裸 JSON）——那一行
/// **没有 `chain` 字段** ⇒ 账本变成"部分有链、部分没有"，`World::open_readonly` **先**以
/// `ext.world.Ledger.MixedChain` 拒开 ⇒ **"读模型折叠不了"这个病因根本没被量到**：
/// 把 `cmd_check` 里那道折叠自检**整段删掉**，本用例**照样绿**。
/// ② 第 13 轮起，写入侧补上了旧值核对 ⇒ 上一版"坏事件**走唯一写入口**落账"这条路
/// **已经不存在**（那正是这一轮修的东西：这种事件**再也进不来**）。
/// ⇒ 本版把两件事**分开判**：写入侧必须拒（第二段），读侧那道墙用**手造但带正确摘要链**
/// 的一行来量（第三段）——那也正是读侧那道墙**今天唯一的对手**。
///
/// ★ 旧帐（历史读数，**未回改**）：第 13 轮之前，这一笔 `commit` 是 **rc=0** 的
/// （`docs/证据/EV-009.md` 当时把它写成断言）；本用例不再断言那件事。
///
/// ## 手造一行必须**补链**
///
/// 摘要算法取自 `world_core::ledger::event_chain`（**与写入侧同源**，不是抄一份）。
/// 不补链 ⇒ 先以 `MixedChain` 拒开 ⇒ 判错病因（初版就是这么倒的）。
fn append_raw_with_chain(lp: &Path, mut ev: Value) {
    let prev = fs::read_to_string(lp)
        .ok()
        .and_then(|t| t.lines().last().map(str::to_string))
        .and_then(|l| serde_json::from_str::<Value>(&l).ok())
        .and_then(|v| v.get("chain").and_then(Value::as_str).map(str::to_string))
        .unwrap_or_else(|| world_core::ledger::CHAIN_GENESIS.to_string());
    let chain = world_core::ledger::event_chain(&prev, &ev).unwrap();
    ev.as_object_mut()
        .unwrap()
        .insert("chain".into(), json!(chain));
    let mut text = fs::read_to_string(lp).unwrap();
    if !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(&serde_json::to_string(&ev).unwrap());
    text.push('\n');
    fs::write(lp, text).unwrap();
}

#[test]
fn m20_write_side_refuses_a_lying_before_and_check_refuses_a_lying_ledger() {
    use world_core::common::event::change_body;
    let dir = tmpdir("m20");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    // ① 先落一条**正常**的 change（此时世界能折叠）
    {
        let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(null), json!(false)),
        )
        .unwrap();
    }
    // 正控：此刻 `check` **必须**报 READY（否则下面的红说明不了什么）
    let (rc_ok, out_ok, err_ok) = cli_check_raw(&ont, &lp, &pol);
    assert_eq!(
        rc_ok, 0,
        "正常账本 `check` 必须 rc=0：\nstdout={out_ok}\nstderr={err_ok}"
    );
    assert!(
        has_ready_line(&out_ok),
        "正常账本 `check` 必须在 **stdout** 上打出 `READY` 那一行：\n{out_ok}"
    );

    // ② ★ **写入侧必须拒**：真旧值是 `false`，这里谎称 `true`
    {
        let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();
        let e = w
            .commit(
                "change",
                "world://user",
                change_body("world://notice/n-1", "muted", json!(true), json!(true)),
            )
            .expect_err("写入侧必须核对 `before`：谎称旧值的一笔**不许**落账");
        assert!(
            e.contains("ext.world.World.BeforeMismatch"),
            "必须点名 `ext.world.World.BeforeMismatch`，实得：{e}"
        );
        assert!(
            e.contains("world://notice/n-1#muted"),
            "必须点名 `subject#path`，实得：{e}"
        );
        assert!(
            e.contains("before=true"),
            "必须点名**声称的** `before`，实得：{e}"
        );
        assert!(
            e.contains("当前值是 false"),
            "必须点名**实际的**当前值，实得：{e}"
        );
    }
    // ②b 正控：`before` 相符 ⇒ **通**
    {
        let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();
        let ev = w
            .commit(
                "change",
                "world://user",
                change_body("world://notice/n-1", "muted", json!(false), json!(true)),
            )
            .expect("`before` 与折叠值相符 ⇒ 必须放行");
        assert_eq!(ev["seq"].as_u64(), Some(2), "相符的那一笔必须落账");
    }
    // ②c 被拒的那一笔**不落账**
    assert_eq!(
        fs::read_to_string(&lp).unwrap().lines().count(),
        2,
        "被拒的事件不许落账（账本只应有：正常一条 ＋ 相符一条）"
    );

    // ③ ★ **读侧那道墙仍在**（对手＝写入侧之外的改写）：手造一行并**补上正确的摘要链**
    let d2 = tmpdir("m20b");
    let lp2 = d2.join("ledger.jsonl");
    {
        let mut w = world_core::World::open(&ont, &lp2, &pol).unwrap();
        w.commit(
            "change",
            "world://user",
            change_body("world://notice/n-1", "muted", json!(null), json!(false)),
        )
        .unwrap();
    }
    let mut bad = world_core::common::event::new_event(
        2,
        "change",
        "world://user",
        change_body("world://notice/n-1", "muted", json!(true), json!(true)),
    );
    bad.as_object_mut()
        .unwrap()
        .insert("id".into(), json!("e-lying-before-2"));
    append_raw_with_chain(&lp2, bad);

    let (rc_bad, out_bad, err_bad) = cli_check_raw(&ont, &lp2, &pol);
    assert_ne!(
        rc_bad, 0,
        "折叠不了时 `check` 必须 rc≠0：\nstdout={out_bad}\nstderr={err_bad}"
    );
    // ⚠️ **按行判，不按子串判**：失败时 stderr 的解释文字里**含 `READY` 这个词**。
    assert!(
        !has_ready_line(&out_bad),
        "**折叠不了 ⇒ stdout 上不许有 `READY` 那一行**（这正是那条假绿）：\n{out_bad}"
    );
    assert!(
        err_bad.contains("ext.world.ReadModel.BeforeMismatch"),
        "拒绝的**病因**必须是「旧值不符」——若变成摘要／缺格／别的码，说明这本账本\n\
         根本没走到折叠那一格：\n{err_bad}"
    );
    println!("---- 折叠不了时的 check 原文 ----\nstdout:\n{out_bad}\nstderr:\n{err_bad}");
}

/// `check` 打到 **stdout** 上的那一行 `READY`（`cmd_check` 里 `println!("  READY")`）。
///
/// **按行判，不按子串判**：`cmd_check` 失败时 stderr 的解释文字里**含 `READY` 这个词**
/// （「…⇒ **读模型折叠不了 ⇒ 不报 `READY`**…」）⇒ 把 stdout 与 stderr 合起来再
/// `contains("READY")`，那条断言**永远为真**（本项目那条「搜字样 ≠ 认结构」的又一例）。
fn has_ready_line(out: &str) -> bool {
    out.lines().any(|l| l.trim() == "READY")
}

/// 跑一次 `world-core check`，返回 `(退出码, stdout, stderr)`。
///
/// ⚠️ **两股必须分开返回**：`READY` 只出现在 stdout，而 stderr 里**会出现 `READY` 这个词**
/// ⇒ 合成一股之后，"有没有报 READY"这件事就**判不出来**了。
fn cli_check_raw(
    ont: &std::path::Path,
    led: &std::path::Path,
    pol: &std::path::Path,
) -> (i32, String, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = std::process::Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("--ledger")
        .arg(led)
        .arg("--policy")
        .arg(pol)
        .arg("check")
        .output()
        .expect("跑得起来 world-core check");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

/// 跑一次 `world-core subscribe`，返回 `(退出码, stdout+stderr)`。
fn cli_sub_raw(
    ont: &std::path::Path,
    led: &std::path::Path,
    pol: &std::path::Path,
    extra: &[&str],
) -> (i32, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = std::process::Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("--ledger")
        .arg(led)
        .arg("--policy")
        .arg(pol)
        .arg("subscribe")
        .args(extra)
        .output()
        .expect("跑得起来 world-core subscribe");
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), txt)
}

/// 跑一次 `world-core read`（`extra` 里给 `--instances` 之类的开关）。
fn cli_read(
    ont: &std::path::Path,
    led: &std::path::Path,
    pol: &std::path::Path,
    extra: &[&str],
) -> String {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = std::process::Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("--ledger")
        .arg(led)
        .arg("--policy")
        .arg(pol)
        .arg("read")
        .args(extra)
        .output()
        .expect("跑得起来 world-core read");
    assert_eq!(
        out.status.code(),
        Some(0),
        "`read` 必须 rc=0；stderr：{}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8_lossy(&out.stdout).to_string()
}

/// 跑一次 `world-core describe`：返回 stdout（rc≠0 直接判红）。
fn cli_describe(ont: &std::path::Path) -> String {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = std::process::Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("describe")
        .output()
        .expect("跑得起来 world-core describe");
    assert_eq!(
        out.status.code(),
        Some(0),
        "`describe` 对出厂本体必须 rc=0；stderr：{}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8_lossy(&out.stdout).to_string()
}

/// 跑一次 `world-core usage`：返回 `(退出码, stdout+stderr)`。
fn cli_usage(ont: &std::path::Path, led: &std::path::Path, pol: &std::path::Path) -> (i32, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = std::process::Command::new(bin)
        .arg("--ontology")
        .arg(ont)
        .arg("--ledger")
        .arg(led)
        .arg("--policy")
        .arg(pol)
        .arg("usage")
        .output()
        .expect("跑得起来 world-core usage");
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), txt)
}

// ──────────── ⑬ 载体无关性：本体里不许出现载体专有物（会红）────────────

/// **⑬（判据①a）**：`ontology.json` 里**参与身份**的那一半（**非 `_` 前缀**键，**与
/// `vocab_hash_of` 的剔法同源**）不许出现**载体专有串**
/// （`systemd`／`.service`／`.socket`／`ListenStream`／`WantedBy`／`Requires=`／`After=`／
/// `Before=`／`PartOf=`／`/run/`）⇒ 命中即拒启（`CarrierSpecificInOntology`）。
///
/// ## 为什么该红
///
/// 本体是**世界的说法**，载体是**某个东西怎么起**——**同级不同物**（载体管资源，世界管说法）。
/// 而本体的身份是**内容寻址**的 ⇒ 载体专有物一旦进了身份面，**换掉载体就得换法律**。
///
/// ## 射程（本用例正控钉住）
///
/// **只**扫参与身份的那一半；`_` 键里的**指路说明**不判——它们不进身份，
/// 而且本来就该能写「接入映射今天落在 `policy.json` 的 `listeners`」这类话。
#[test]
fn m15_carrier_specific_strings_must_not_enter_the_ontology_identity() {
    let dir = tmpdir("m15");

    // 正控①：出厂本体（全部 `_` 键 ＋ 非 `_` 那 7 处）必须能加载
    let ont = Ontology::load(&factory_ontology()).expect("出厂本体必须能加载（没有载体专有串）");
    // 正控②：把边界钉清楚——`_meta_layers` 是**指路**用的，它不进身份
    let raw = factory_json();
    assert!(
        raw.get("_meta_layers").is_some(),
        "出厂本体有 `_meta_layers`（**指路**用；它不进身份）"
    );
    assert_eq!(
        ont.vocab_hash(),
        "fnv1a64:6a96abfa9a969462",
        "顺带钉住：本判据不改变身份（它只在装载期拦，不参与 hash）"
    );

    // 反例①：往**非 `_` 键**里写载体专有串 ⇒ 拒启
    let busy = write_ontology(&dir, "carrier-token.json", |v| {
        v["carrier"] = json!({ "unit": "world-core.service" });
    });
    let e =
        Ontology::load(&busy).expect_err("本体里出现 `.service` ⇒ 必须拒启（换载体就得换法律）");
    assert!(
        e.contains("ext.world.Ontology.CarrierSpecificInOntology"),
        "理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains(".service") && e.contains("carrier.unit"),
        "理由必须**点名**是哪个串、在哪个路径上，实得：{e}"
    );

    // 反例②：换一个 token（`/run/`）与另一种落点 ⇒ 同样拒启
    let run_token = write_ontology(&dir, "carrier-token2.json", |v| {
        v["paths"] = json!({ "sock": "/run/world-core/world.sock" });
    });
    let e2 = Ontology::load(&run_token).expect_err("非 `_` 键里写 `/run/` ⇒ 必须拒启");
    assert!(
        e2.contains("ext.world.Ontology.CarrierSpecificInOntology") && e2.contains("/run/"),
        "实得：{e2}"
    );

    // 反例③：写进**核心信封字段的说明文字**（也是非 `_` 键、也进身份）⇒ 同样拒启
    let in_envelope = write_ontology(&dir, "carrier-token3.json", |v| {
        v["envelope"]["fields"]["actor"] = json!("string  # 由 systemd 的 socket 单元给出");
    });
    let e3 = Ontology::load(&in_envelope).expect_err("信封字段说明文字里写 `systemd` ⇒ 必须拒启");
    assert!(
        e3.contains("ext.world.Ontology.CarrierSpecificInOntology"),
        "实得：{e3}"
    );

    // ★ 正控③（**射程的边界**）：同样的字样写进 **`_` 键**里 ⇒ **必须能加载**
    //   （那不是"往法律里塞载体"，是"在说明里指路"）
    let in_underscore = write_ontology(&dir, "carrier-token-in-underscore.json", |v| {
        v["_meta_layers"]["_note_for_test"] = json!("接入映射今天落在 world-core.service 身上");
    });
    Ontology::load(&in_underscore)
        .expect("`_` 键里的指路说明**不进身份** ⇒ 必须能加载（判据的射程只到身份面）");

    // 恢复那一半：原本体 ⇒ 绿
    let restored = write_ontology(&dir, "restored.json", |_| {});
    Ontology::load(&restored).expect("原本体必须能加载（恢复绿）");
}

// ══════════════════════════════════════════════════════════════════════════
// 第 13 轮新增 · **在场者（`presence`）的语义** ＋ **申报／授权两级** ＋ **写入侧旧值核对**
// ══════════════════════════════════════════════════════════════════════════

/// **㉑（第 13 轮）`presence` 的**语义**：本体不只声明"类型"，还声明"取值域与口径"**。
///
/// ## 判据（三条，条条会红）
///
/// | # | 判据 | 反例（必红） |
/// |---|---|---|
/// | ① | `presence.state` 是**闭集** `enum(installed,registered,running,stopped,retired)`：填闭集外的值 ⇒ **拒**（`ext.world.Ontology.BadFieldValueType`） | 填 `"running-now"` |
/// | ② | `presence.did` 的**元素形态**是字符串（`array(string)`）：非数组 ⇒ 拒；**数组里出现非字符串** ⇒ 也拒 | 填 `"/usr/bin/pcmanfm"`；填 `[1,2]` |
/// | ③ | `presence.last_seen` 是**整数 UNIX 秒**：非整数 ⇒ 拒 | 填 `"1791044558"`／`1.5` |
///
/// ## 三条口径的依据（写清，不替本体发明）
///
/// - **闭集枚举**照本体既有写法：`job.status` 逐字是 `enum(todo,doing,done)`，
///   装载器对 `enum(...)` 按**闭集**判（`Ontology::check_concepts` → `type_ok`）；
///   `state` 的五个取值按"在场者今天可能的处境"定：
///   `installed`（装着）／`registered`（已登记但没跑）／`running`（正在跑）／
///   `stopped`（停了）／`retired`（退场）——真实账本里三条现值都是 `installed`，在闭集内；
/// - **`array(<类型>)` 是本轮新加的写法**，理由是原写法只能写 `array`——"是不是数组"判得了、
///   "数组里装的是什么"判不了，而 `did` 的元素形态（世界主体 ／ 宿主可执行文件 ／
///   发行版包坐标，见真实账本 `seq=18/23/28`）正是要进判据的那一格；
/// - **`last_seen` 的"UNIX 秒"只写在声明的说明文字里**（与 `envelope.at` 的
///   `integer  # 时间戳，Unix 秒` 逐字同口径）——**不**声称四张必配表里的
///   「值的类型与单位」已实现（那一张仍**只登记、未实现**）。
#[test]
fn m21_presence_semantics_are_declared_and_a_value_outside_the_closed_set_is_refused() {
    use world_core::common::event::change_body;
    let dir = tmpdir("m21");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();

    // 正控：闭集内的值 ⇒ 通
    w.commit(
        "change",
        "world://user",
        change_body(
            "world://presence/pcmanfm",
            "state",
            json!(null),
            json!("installed"),
        ),
    )
    .expect("闭集内的 `state` 必须放行");

    // ① 反例：闭集外的值 ⇒ 拒，且点名那一格
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "state",
                json!("installed"),
                json!("running-now"),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("state"),
        "闭集外的 `state` 必须被拒且点名 `state`，实得：{e}"
    );

    // ② 反例：`did` 非数组 ⇒ 拒
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "did",
                json!(null),
                json!("/usr/bin/pcmanfm"),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("did"),
        "`did` 非数组必须被拒且点名 `did`，实得：{e}"
    );
    // ②b 反例：`did` 是数组但**元素不是字符串** ⇒ 也拒（"元素形态"这一格承重）
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "did",
                json!(null),
                json!([1, 2]),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("did"),
        "`did` 的元素不是字符串必须被拒，实得：{e}"
    );
    // 正控：元素形态对 ⇒ 通
    w.commit(
        "change",
        "world://user",
        change_body(
            "world://presence/pcmanfm",
            "did",
            json!(null),
            json!([
                "world://presence/pcmanfm",
                "/usr/bin/pcmanfm",
                "arch:extra/pcmanfm@1.4.0-2"
            ]),
        ),
    )
    .expect("`did` 的三个字符串元素必须放行");

    // ③ 反例：`last_seen` 非整数 ⇒ 拒（字符串与小数各一次）
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "last_seen",
                json!(null),
                json!("1791044558"),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType") && e.contains("last_seen"),
        "`last_seen` 是字符串必须被拒，实得：{e}"
    );
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "last_seen",
                json!(null),
                json!(1.5),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType"),
        "`last_seen` 是小数必须被拒，实得：{e}"
    );
    // 正控：整数 ⇒ 通
    w.commit(
        "change",
        "world://user",
        change_body(
            "world://presence/pcmanfm",
            "last_seen",
            json!(null),
            json!(1791044558),
        ),
    )
    .expect("整数 `last_seen` 必须放行");

    // ④ **被拒的申报一条都不许落账**（形制判据的机器形态：账本行数＝成功的那些）
    let evs = w.ledger().read_all().unwrap();
    assert_eq!(
        evs.len(),
        3,
        "**被拒的申报一条都不许落账**：三格各有一条正控 ⇒ 账本恰为 3 条；\
         实得 {} 条（多出来的就是被拒的那些漏进来了）",
        evs.len()
    );

    // ⑤ **两处声明逐字一致**（`concepts` 是身份面、`_objects` 是读路径面）
    let raw = factory_json();
    assert_eq!(
        raw["concepts"]["presence"]["fields"], raw["_objects"]["presence"]["fields"],
        "`concepts.presence.fields` 与 `_objects.presence.fields` 必须逐字一致（`ConceptsDrift`）"
    );
    println!(
        "---- m21 逐格声明（现取）----\n{}",
        raw["_objects"]["presence"]["fields"]
    );
}

/// **㉒（第 13 轮）在场者的**两级分开**：① 申报（依据）→ ② 授权（许可）——顺序是死的**。
///
/// ## ★★ 口径（逐字，作者定的设计）
///
/// > **申报给的是「依据」，授权给的是「许可」。二者不许合并——一旦合并，等于在场者
/// > 自己给自己发许可证，世界就不再管着它。报得再全，也不自动拿到任何能力；
/// > 开放只由许可决定（`_permissions.grants` ＋ `default: deny`）。**
///
/// ## 三条判据（条条会红）
///
/// | # | 情形 | 期望 |
/// |---|---|---|
/// | ① | **没申报**的在场者调用**任何**能力 | **拒**，码 `ext.world.World.PresenceNotDeclared`，话里点名「该在场者未在世界里申报」 |
/// | ② | **申报了但没被授予** | **拒**，码 `ext.world.Gate.CapabilityNotGranted`（**声明存在 ≠ 你有许可**） |
/// | ③ | **申报了且被授予** | **通**（正控） |
///
/// ＋**形制判据**：申报本身**缺必填字段／类型不符 ⇒ 不落账**。
///
/// ## 反例（必红）
///
/// 把 `World::check_presence_levels` 短路成恒 `Ok(())` ⇒ ①②当场变红（`ghost` 会"自报即通行"）。
#[test]
fn m22_presence_report_is_two_levels_declare_then_authorize() {
    use world_core::common::event::{act_body, change_body};
    let dir = tmpdir("m22");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();

    // ── **申报**：给两个在场者各写一格。★ 申报**只给依据**，不给任何能力 ────────
    for who in ["pcmanfm", "mousepad"] {
        w.commit(
            "change",
            "world://user",
            change_body(
                &format!("world://presence/{who}"),
                "state",
                json!(null),
                json!("installed"),
            ),
        )
        .expect("申报（一条 change）必须能落账");
    }

    // ② **申报了但没被授予** ⇒ 拒（`mousepad` 不在 `presence.report` 的 `scope` 里）
    let e = w
        .commit(
            "act",
            "world://presence/mousepad",
            act_body("presence.report", "report", "r-m22-a", json!({})),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Gate.CapabilityNotGranted"),
        "已申报但未被授予必须拒且点名那条码，实得：{e}"
    );
    assert!(
        e.contains("声明存在") && e.contains("许可"),
        "拒绝的话里必须说清「声明存在 ≠ 你有许可」，实得：{e}"
    );

    // ① **没申报的在场者调用任何能力** ⇒ 拒（`ghost` 名下一格都没有）
    let e = w
        .commit(
            "act",
            "world://presence/ghost",
            act_body("presence.report", "report", "r-m22-b", json!({})),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.World.PresenceNotDeclared"),
        "没申报的在场者必须拒且点名那条码，实得：{e}"
    );
    assert!(
        e.contains("未在世界里申报"),
        "拒绝的话里必须点名「该在场者未在世界里申报」，实得：{e}"
    );

    // ③ **申报了且被授予** ⇒ 通（正控）
    let ev = w
        .commit(
            "act",
            "world://presence/pcmanfm",
            act_body("presence.report", "report", "r-m22-c", json!({})),
        )
        .expect("申报过 ＋ 被授予 ⇒ 必须通");
    assert_eq!(
        ev["body"]["capability"],
        json!("presence.report"),
        "落笔的必须是这一条 act 本身：{ev}"
    );

    // ＋ 形制判据①：申报**类型不符**（闭集外的 `state`）⇒ **不落账**
    let e = w
        .commit(
            "change",
            "world://user",
            change_body(
                "world://presence/pcmanfm",
                "state",
                json!("installed"),
                json!("running-now"),
            ),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Ontology.BadFieldValueType"),
        "类型不符的申报必须拒，实得：{e}"
    );
    // ＋ 形制判据②：申报**缺必填字段** ⇒ **不落账**
    let e = w
        .commit(
            "change",
            "world://user",
            json!({ "subject": "world://presence/pcmanfm", "path": "state", "after": "registered" }),
        )
        .unwrap_err();
    assert!(
        e.contains("MissingField") && e.contains("before"),
        "缺 `before` 的申报必须拒且点名那一格，实得：{e}"
    );

    // ★ **不落账的机器形态**：账本里不许出现那两条被拒的**原事件**
    let evs = w.ledger().read_all().unwrap();
    assert!(
        !evs.iter()
            .any(|x| x.get("kind").and_then(Value::as_str) == Some("change")
                && x["body"]["after"] == json!("running-now")),
        "类型不符的申报**不落账**：账本里不许出现它"
    );
    assert!(
        !evs.iter()
            .any(|x| x.get("kind").and_then(Value::as_str) == Some("change")
                && x["body"]["after"] == json!("registered")),
        "缺必填字段的申报**不落账**：账本里不许出现它"
    );
    // ① / ② 被拒的 `act` 也**不落账**（留下的只是内核那条 `gate.*` 流水，**不是原事件**）
    for who in ["world://presence/mousepad", "world://presence/ghost"] {
        assert!(
            !evs.iter()
                .any(|x| x.get("kind").and_then(Value::as_str) == Some("act")
                    && x.get("actor").and_then(Value::as_str) == Some(who)),
            "被拒的 `act` 不许落账（actor={who}）"
        );
    }
    println!(
        "---- m22 账本（现取，{} 条：2 条申报 ＋ 2 条 gate 流水 ＋ 1 条放行的 act）----\n{}",
        evs.len(),
        evs.iter()
            .map(|x| format!("seq={} kind={} actor={}", x["seq"], x["kind"], x["actor"]))
            .collect::<Vec<_>>()
            .join("\n")
    );
}

/// **㉓（第 14 轮）许可收窄：`_permissions.grants.<能力>.scope` 必须点名具体主体，不许通配**。
///
/// ## 为什么这一组独立于 ㉒
///
/// ㉒ 判的是**两级本身**（申报／授权各判真假）；本组判的是**许可条文写得多宽**。
/// 两者会各自红、各自绿：`scope` 写成 `world://*` 时，㉒ 的三条**全绿**
/// （它只要求「命中即授予」），而「在场者能不能调 `notice.mute`」这一问，㉒ 根本问不出来。
///
/// ## 三条判据（条条会红）＋ 一条法律形态判据
///
/// | # | 情形 | 期望 | 短路方式（必红） |
/// |---|---|---|---|
/// | ① | **已申报**的在场者调 `notice.mute` | **拒**，码 `ext.world.Gate.CapabilityNotGranted` | `scope` 匹配恒真 ⇒ ① 变红 |
/// | ② | **正控**：`world://user` 调 `notice.mute` | **通**（它不是在场者，两级**不**适用于它——口径一字未动） | —— |
/// | ③ | **正控**：在场者调**它自己被授予的** `presence.report` | **通** | `scope` 匹配恒假 ⇒ ③ 变红 |
/// | ④ | 法律形态：出厂 `grants` 里 `notice.mute`／`notice.unmute` 的 `scope` | **不得**含 `world://*` | 把 `scope` 改回 `["world://*"]` ⇒ ④ 变红 |
#[test]
fn m23_capability_scope_names_concrete_subjects_not_a_wildcard() {
    use world_core::common::event::{act_body, change_body};
    let dir = tmpdir("m23");
    let lp = dir.join("ledger.jsonl");
    let ont = factory_ontology();
    let pol = factory_policy();
    let mut w = world_core::World::open(&ont, &lp, &pol).unwrap();

    // 申报（只给依据，不给任何能力）：`pcmanfm` 名下有一格 ⇒ 它是「已申报」的在场者。
    w.commit(
        "change",
        "world://user",
        change_body(
            "world://presence/pcmanfm",
            "state",
            json!(null),
            json!("installed"),
        ),
    )
    .expect("申报（一条 change）必须能落账");

    // ① 已申报的在场者调 `notice.mute` ⇒ **拒**
    //    （`scope` 一旦是 `world://*`，这一条就会被判「已授予」——那正是本组要拦的）
    let e = w
        .commit(
            "act",
            "world://presence/pcmanfm",
            act_body("notice.mute", "do", "r-m23-a", json!({})),
        )
        .unwrap_err();
    assert!(
        e.contains("ext.world.Gate.CapabilityNotGranted"),
        "在场者调 `notice.mute` 必须拒且点名那条码，实得：{e}"
    );
    assert!(
        e.contains("notice.mute") && e.contains("world://presence/pcmanfm"),
        "拒绝的话里必须点名能力与主体，实得：{e}"
    );

    // ② 正控：`world://user` 调 `notice.mute` ⇒ **通**
    //    （两级只对在场者生效；收窄 `scope` 不许顺手把 `world://user` 也拦掉）
    let ev = w
        .commit(
            "act",
            "world://user",
            act_body("notice.mute", "do", "r-m23-b", json!({})),
        )
        .expect("`world://user` 调 `notice.mute` 必须通（正控）");
    assert_eq!(
        ev["body"]["capability"],
        json!("notice.mute"),
        "落笔的必须是这条 act 本身：{ev}"
    );

    // ③ 正控：在场者调**它自己被授予的** `presence.report` ⇒ **通**
    let ev = w
        .commit(
            "act",
            "world://presence/pcmanfm",
            act_body("presence.report", "report", "r-m23-c", json!({})),
        )
        .expect("在场者调自己被授予的 `presence.report` 必须通（正控）");
    assert_eq!(
        ev["body"]["capability"],
        json!("presence.report"),
        "落笔的必须是这条 act 本身：{ev}"
    );

    // ④ 法律形态：`scope` 必须点名**具体主体**，不许回到通配
    let raw = factory_json();
    for cap in ["notice.mute", "notice.unmute"] {
        let scope = raw["_permissions"]["grants"][cap]["scope"].clone();
        let scopes = scope.as_array().expect("`scope` 必须是数组");
        assert!(
            !scopes.iter().any(|s| s.as_str() == Some("world://*")),
            "`{cap}` 的 `scope` 必须是**具体主体**，不许通配 `world://*`（实得 {scope}）——\
             通配会让**任何**申报过的在场者都被判「已授予」"
        );
        assert!(
            !scopes.is_empty(),
            "`{cap}` 的 `scope` 不许为空：空 = 谁都没被授予（那不是收窄，那是关闭）"
        );
    }

    // ★ 不落账的机器形态：① 那条被拒的 `act` 不许进账本
    let evs = w.ledger().read_all().unwrap();
    assert!(
        !evs.iter()
            .any(|x| x.get("kind").and_then(Value::as_str) == Some("act")
                && x.get("actor").and_then(Value::as_str) == Some("world://presence/pcmanfm")
                && x["body"]["capability"] == json!("notice.mute")),
        "被拒的 `act` 不许落账"
    );
    println!(
        "---- m23 账本（现取，{} 条：1 条申报 ＋ 1 条 gate 流水 ＋ 2 条放行的 act）----\n{}",
        evs.len(),
        evs.iter()
            .map(|x| format!("seq={} kind={} actor={}", x["seq"], x["kind"], x["actor"]))
            .collect::<Vec<_>>()
            .join("\n")
    );
}

// ────────────── ⑭ 关系的基数与方向性：只许声明世界真执行的取值 ──────────────

/// **⑭**：`_links.<关系>.card` 与 `.bidirectional` —— ★**只许声明世界今天真执行的取值**。
///
/// ## 为什么这一组要存在
///
/// 这两个格被装载器**读进 `LinkDecl`**、也由 `links()` 交给外面，而**世界不执行**基数约束、
/// 也不执行方向性 ⇒ 一旦法律里写 `card = "one"`／`bidirectional = true`，**读法律的人会以为
/// 这条关系有约束**，世界却照旧允许多条、照旧不当双向。这比"没声明"更坏 ——
/// 它把"没做到"写成了"做到了"（铁律⑦）在本体面的形态。
///
/// ## 裁与落法（Lead 2026-10-05 · 选甲）
///
/// **甲**：只许声明世界真执行的取值 ⇒ **声明了没执行 ⇒ 拒启**；缺口如实登记为未实现
/// （本体侧 `_pending_tables` 的登记待三张表门禁解除后补；**在补上之前，`规程-本体定义面.md`
/// §6.1 就是那条登记的落点**）。**乙**（真做基数／方向性校验）留作后续。
///
/// ## 反例（改坏 ⇒ 必须红；改回 ⇒ 必须绿）
///
/// | 反例 | 改哪一格 | 必须点名的理由 |
/// |---|---|---|
/// | 甲-1 | `card = "one"` | **声明了没执行** |
/// | 甲-2 | `card = 3`（形状写错） | **不可判读** |
/// | 甲-3 | `bidirectional = true` | **声明了没执行** |
/// | 甲-4 | `bidirectional = "no"`（形状写错） | **不可判读** |
///
/// ★ 另有一条"不写 ⇒ 必须能加载"（＝不声明，不是违规）：防"把整格删掉也拒"的假红。
#[test]
fn m24_link_cardinality_only_executed_values_or_nothing() {
    let dir = tmpdir("m24");

    // 正控：出厂本体（`card: "many"`、`bidirectional: false`）必须能加载 ——
    // 否则下面四条可能只是"这份本体本来就起不来"。
    Ontology::load(&factory_ontology()).expect("出厂关系的基数是世界真执行的那个取值 ⇒ 必须能加载");

    red_then_green(
        "m24-card-one",
        &dir,
        |v| {
            v["_links"]["part-of"]["card"] = json!("one");
        },
        "声明了没执行",
    );

    red_then_green(
        "m24-card-int",
        &dir,
        |v| {
            v["_links"]["part-of"]["card"] = json!(3);
        },
        "不可判读",
    );

    red_then_green(
        "m24-bidir-true",
        &dir,
        |v| {
            v["_links"]["part-of"]["bidirectional"] = json!(true);
        },
        "声明了没执行",
    );

    red_then_green(
        "m24-bidir-str",
        &dir,
        |v| {
            v["_links"]["part-of"]["bidirectional"] = json!("no");
        },
        "不可判读",
    );

    // 不写 ＝ 不声明 ⇒ 必须能加载（`card`／`bidirectional` 都删掉）
    let absent = write_ontology(&dir, "m24-absent.json", |v| {
        let l = v["_links"]["part-of"].as_object_mut().unwrap();
        l.remove("card");
        l.remove("bidirectional");
    });
    Ontology::load(&absent).expect("不写 `card`／`bidirectional` ＝ 不声明 ⇒ 必须能加载");

    // 显式写"无约束"取值 ⇒ 必须能加载（与"不写"等价，不许一边绿一边红）
    let explicit = write_ontology(&dir, "m24-explicit.json", |v| {
        v["_links"]["part-of"]["card"] = json!("many");
        v["_links"]["part-of"]["bidirectional"] = json!(false);
    });
    Ontology::load(&explicit).expect("显式写 `many`／`false` 必须能加载");
}
