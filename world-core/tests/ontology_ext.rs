//! **本体：极小核心 ＋ 命名空间扩展**（`REQ-F-030`）＋ **未知旗标必须忽略**（`REQ-F-029`）。
//!
//! ## 这一格原来红在哪（2026-09-27 的实测，逐字可核）
//!
//! `world-core/tools/s1_sys_probe.sh` 的 `TC-049` ⑦ 当时是**登记项**（`⛔`），逐字：
//! 「反例②**现状为红**：扩展项与核心信封字段重名（concepts 里叫 body）竟**被接受**（rc=0）
//! —— 本体加载器只查形状、不查重名 ⇒ REQ-F-030 判据② **不成立**」。
//! `TC-048` ⑦ 同样登记着边界，逐字：「出厂本体 flags = **空数组**（实测长度 0）
//! ⇒ 「未知旗标」在**本体内没有任何已定义旗标可比对**；① 之所以能跑，靠的是**手写账本行**
//! 而非公开写入入口。该边界如实登记，不读作「已完备」」。
//!
//! 本文件把那两幕照原样变成**会红的断言**，并把仍然敞着的那一半**如实登记**（见 `e05`）。
//!
//! ## 依据（逐字，三处）
//!
//! | 出处 | 逐字 |
//! |---|---|
//! | `world-core/src/ontology_definition/ontology.json:20` | `"flags": "array  # 能力旗标；未知旗标必须忽略"` |
//! | 书 §2.7（合订本 `:305`） | 「领域里的概念，诸如订单、曲目、告警、工序，都不属于这一层，各自在自己的命名空间里往上长」 |
//! | 书 §2.7（合订本 `:313`） | 「核心之外由命名空间扩展，各方在自己的空间里定义自己的概念；核心之内不取交集，也不做删减」 |
//! | `WC-FMT-001` §「未知家族 / 未知字段 / 未知旗标」 | 「**不认识的语义拒绝，不认识的附加信息忽略**」 |
//!
//! ## 每条断言的"会红"条件（改坏哪一行 ⇒ 打红哪一条；逐条在 VM 上做过）
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `e01` | `src/common/event.rs::read_flags` 的 `Some(f) => out.ignored.push(f)` 改成 `out.known.push(f)` ⇒ `e01` 红（正控与本题同时红） |
//! | `e02` | `src/ontology_definition/mod.rs::Ontology::validate` 改成"旗标不认识就拒"（把**对偶**弄反）⇒ `e02`/`e04` 红，而 `e03` 仍绿 |
//! | `e03` | `src/ontology_definition/mod.rs::validate` 的家族查表放宽（回退到任一已知家族）⇒ `e03` 红，而 `e01`/`e02` 仍绿 |
//! | `e04` | `src/common/event.rs::with_flag` 改成空实现（旗标不落账）⇒ `e04` 红 |
//! | `x01` | `src/ontology_definition/mod.rs::load` 里 `check_extension_names(&concepts, &core_fields)?;` 改成 `let _ = …;` ⇒ `x01` 红（且 `s1_sys_probe.sh` 的 `TC-049` ⑦ 退回红） |
//! | `x02` | `src/ontology_definition/mod.rs::core_field_names` 把**家族信纸字段**也算进核心 ⇒ 纯加法的本体被拒 ⇒ `x02` 红（且 `TC-046`/`TC-049` ⑥ 一起红） |
//!
//! ## 诚实边界（不许读成"已完备"）
//!
//! - **任意未知旗标（如 `future.flag`）经公开写入入口落笔**：2026-09-28 上午**还做不到**
//!   （`World::commit`／CLI `append` 都没有旗标参数），本文件当天据此立了一条**登记项**；
//!   同日工区 F 把 `--flag` 落进 CLI `append` ⇒ 那条登记**如期变红**，已按登记时的处置
//!   改成端到端断言（见 `e05` 的文档）。**登记项不是用来长期挂着的**。
//! - **仍在册**：出厂本体顶层 `flags` 是**空数组**（`ontology.json:49`）⇒「未知旗标」在本体侧
//!   **没有已定义旗标可比对**（`TC-048` ⑦／`WC-SCMP-001` §8.4 的 `G-83`）。
//! - `src/` 里**读** `flags` 的点，今天只有本工区新增的 `event::read_flags`
//!   （`WC-LFMT-001` 的「不担保-10」逐字登记过"`src/` 内没有任何代码读 `flags`"——
//!   那句话在本改动之后**已过期**，须由文档侧同步，见交付说明）。

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::ontology_definition::Ontology;
use world_core::ontology_instance::readmodel::State;
use world_core::{common::event, World};

// ────────────────────────── 夹具 ──────────────────────────

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-ontext-{tag}-{n}"));
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

/// **只加扩展**（纯加法）：新增一个家族 ＋ 在同一个名下新增一个概念。
/// 与 `tools/s1_sys_probe.sh` 的 `ontology-ext.json` 同形态。
fn add_pure_extension(v: &mut Value) {
    v["families"]["audit"] = json!({
        "_comment": "纯加法扩展家族：不得影响既有三家族的语义",
        "required": ["scope", "result"],
        "optional": []
    });
    v["_objects"]["audit"] = json!({ "fields": { "result": "enum(pass,fail)" } });
}

fn flags_of(ev: &Value) -> Vec<String> {
    ev.get("flags")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}

/// 一个**读者**的路：先过法律（`validate`），再折叠。两条都不许对未知旗标有意见。
fn read_with(ont: &Ontology, lines: &[Value]) -> Result<State, String> {
    let mut st = State::new();
    for ev in lines {
        ont.validate(ev).map_err(|e| e.to_string())?;
        st.apply(ev)?;
    }
    Ok(st)
}

/// 落一本基础账：一条 `change`（已声明的实体与字段）＋ 一条 `act`。
fn base_ledger(dir: &Path) -> (PathBuf, Vec<Value>) {
    let lp = dir.join("base.jsonl");
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    )
    .unwrap();
    w.commit(
        "act",
        "world://user",
        event::act_body("notice.mute", "do", "r-x02", json!({})),
    )
    .unwrap();
    let lines = w.ledger().read_all().unwrap();
    (lp, lines)
}

// ────────────────── 第 4 组：未知旗标必须忽略（REQ-F-029）──────────────────

/// **e01**：带未知旗标的事件**被接受**；读者**按自己认得的那部分继续**。
///
/// 反假（同一条用例内）：同一个 `read_flags`，换一个"什么都认得"的读者 ⇒
/// 两个旗标必须落到 `known`。否则 `ignored` 就是"什么都往里塞"的恒真实现。
#[test]
fn e01_unknown_flags_are_ignored_and_the_reader_continues_with_what_it_knows() {
    let _dir = tmpdir("e01");
    let ont = Ontology::load(&factory_ontology()).unwrap();

    let mut ev = event::new_event(
        1,
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    );
    event::with_flag(&mut ev, "future.flag");
    event::with_flag(&mut ev, "another.flag");

    // ① 必须被接受（注意方向与"未知家族"那条相反）
    ont.validate(&ev)
        .expect("带未知旗标的合法事件必须被接受（ontology.json:20）");

    // ② 出厂读法：两个都不认得 ⇒ 全进 ignored，一个也不进 known
    let f = ont.read_flags(&ev, event::is_factory_flag);
    assert_eq!(
        f.known,
        Vec::<&str>::new(),
        "出厂本体未声明任何旗标（`flags: []`）⇒ 出厂读法一个都不认得，实得 {:?}",
        f.known
    );
    assert_eq!(
        f.ignored,
        vec!["future.flag", "another.flag"],
        "不认得的旗标必须按**原顺序**如实列进 ignored（不是丢掉、不是只记一个）"
    );
    assert_eq!(f.not_string, 0, "两项都是字符串，不该落到 not_string");

    // ③ 正控（反假）：换一个"什么都认得"的读者 ⇒ 同一批旗标必须落到 known
    let knows_all = ont.read_flags(&ev, |_| true);
    assert_eq!(
        knows_all.known,
        vec!["future.flag", "another.flag"],
        "分类必须真的按判据分——否则 ignored 是恒真实现"
    );
    assert!(knows_all.ignored.is_empty());

    // ④ 不解释取值：非字符串项如实计数，既不静默修补、也不据此拒收
    let mut odd = ev.clone();
    odd["flags"] = json!(["future.flag", 123]);
    let f2 = ont.read_flags(&odd, event::is_factory_flag);
    assert_eq!(f2.ignored, vec!["future.flag"]);
    assert_eq!(f2.not_string, 1, "非字符串项要数出来（不静默修补）");
}

/// **e02**：带未知旗标的事件**落笔后**，同一账本的**折叠结果逐字节不变**。
///
/// 走的是**真账本文件**：写盘 → `World::open_readonly` 读回 → 折叠。
/// 于是这一条同时钉住三件事：旗标**原样保留**、事件**被折进去了**（不是被跳过）、
/// 结论**与不带该旗标时逐字节相同**。
#[test]
fn e02_a_landed_ledger_line_with_unknown_flags_folds_byte_identically() {
    let dir = tmpdir("e02");
    let (_base_lp, base) = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();

    // 参考折叠：不带任何旗标
    let base_line = read_with(&ont, &base).unwrap();
    let base_bytes = base_line.to_json().to_string();
    assert!(
        !base_bytes.is_empty() && base_bytes.len() > 2,
        "折叠结果不能是空的（否则下面的『逐字节相同』是同义反复）：{base_bytes}"
    );

    // 同一条账本，只把每一行的 flags 换成**这个读法不认得**的旗标。
    // ⚠️ 必须同时**去掉 `chain`**：改一个字节而留着摘要，账本会以
    // `ext.world.Ledger.ChainMismatch` 拒绝打开 —— 那拒的是"摘要不符"，不是"未知旗标"，
    // 拿它当本用例的红会**判错了病因**（与 `tools/s1_sys_probe.sh` 的 `mk_bad` 同口径）。
    let mut flagged = base.clone();
    for ev in &mut flagged {
        ev["flags"] = json!(["future.flag", "another.flag"]);
        ev.as_object_mut().unwrap().remove("chain");
    }
    let fp = dir.join("flagged.jsonl");
    let text = flagged
        .iter()
        .map(|e| serde_json::to_string(e).unwrap())
        .collect::<Vec<_>>()
        .join("\n");
    fs::write(&fp, format!("{text}\n")).unwrap();
    chmod600(&fp);

    // ① 读者读回：旗标**原样保留**在账本里（不是被内核顺手抹掉）
    let w2 = World::open_readonly(&factory_ontology(), &fp, &factory_policy()).unwrap();
    let back = w2.ledger().read_all().unwrap();
    assert_eq!(back.len(), base.len(), "账本行数没变");
    for ev in &back {
        assert_eq!(
            flags_of(ev),
            vec!["future.flag", "another.flag"],
            "读回的 flags 必须保留原值"
        );
    }

    // ② 法律面：每一行都必须被接受（方向与"未知家族"相反）
    for ev in &back {
        ont.validate(ev)
            .expect("带未知旗标的账本行必须被接受：不得因为一个附加标记拒收整条事件");
    }

    // ③ 折叠结果与不带旗标时**逐字节相同**，且那行**确实被折进去了**
    let flagged_state = w2.read_model().unwrap();
    assert_eq!(
        flagged_state.to_json().to_string(),
        base_bytes,
        "同一账本的折叠结果必须与不带该旗标时逐字节相同"
    );
    assert_eq!(
        flagged_state.get("world://notice/n-1", "muted"),
        Some(&json!(true)),
        "那条带未知旗标的 change 必须**被折进状态**（不是被跳过——跳过也会『结果相同』）"
    );
    assert_eq!(
        flagged_state.seen() as usize,
        base.len(),
        "每一行都被折叠过"
    );
}

/// **e03**（**对偶**）：未知**家族**必须被拒，且**两处**都拒：写入侧（法律）与折叠侧（读模型）。
///
/// 与 `e01`/`e02` 的方向**相反**——两条断言不许互相冒充：
/// 「有未知旗标」不得被读成「家族不认识」，「家族不认识」也不得被读成「旗标不认识」。
#[test]
fn e03_unknown_family_is_refused_on_both_sides_of_the_dual() {
    let ont = Ontology::load(&factory_ontology()).unwrap();

    let mut ev = event::new_event(
        1,
        "bogus",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    );
    // 顺带带上未知旗标：**旗标那半不救它、也不害它**——被拒的理由只能是家族
    event::with_flag(&mut ev, "future.flag");

    // ① 写入侧（法律）：拒，且**点名**那个家族
    let e = ont.validate(&ev).expect_err("未知家族必须被拒");
    let msg = e.to_string();
    assert!(
        msg.contains("ext.world.Ontology.UnknownKind"),
        "错误码要可判定，实得：{msg}"
    );
    assert!(msg.contains("bogus"), "错误要点名是哪个家族不认识：{msg}");

    // ② 折叠侧（读模型）：也拒（"拒绝猜测其语义"），与写入侧同一个方向
    let fold = State::fold(std::slice::from_ref(&ev)).expect_err("读模型也必须拒绝未知家族");
    assert!(
        fold.contains("ext.world.ReadModel.UnknownKind"),
        "折叠侧的拒绝要有自己的错误码（两处不许混写成一句话）：{fold}"
    );
    assert!(fold.contains("bogus"), "折叠侧同样要点名：{fold}");

    // ③ 不许互相冒充：方向相反的两条，各自在自己的判据上成立
    let mut ok = ev.clone();
    ok["kind"] = json!("change");
    assert!(
        ont.validate(&ok).is_ok(),
        "同一条事件只把 kind 换成已知家族 ⇒ 必须被接受（含那个未知旗标）"
    );
    let mut ok2 = ev.clone();
    ok2["flags"] = json!([]);
    assert!(
        ont.validate(&ok2).is_err(),
        "同一条事件只把 flags 清空 ⇒ 仍然被拒（拒它的理由是家族，不是旗标）——\
         否则『未知家族』这条判据会被旗标冒充"
    );
}

/// **e04**：一个**出厂读法不认得**的旗标，经**公开写入入口**落笔，且不改折叠结论。
///
/// 这是今天唯一能从公开入口落账的旗标：内核给不可逆动作加的摩擦标记
/// `gate.friction:high`（`src/lib.rs` 的 `event::with_flag` ＋ `src/gate/mod.rs` 的 `Friction::flag`）。
/// 它**不在**出厂本体声明的旗标里（`flags: []`）⇒ 对出厂读法而言它就是"未知旗标"——
/// 「旧读法读到它不会坏」这句话因此**可执行**，而不只是注释。
#[test]
fn e04_a_flag_the_factory_reader_does_not_know_still_lands_and_folds() {
    let dir = tmpdir("e04");
    let lp = dir.join("ledger.jsonl");
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    let ont = Ontology::load(&factory_ontology()).unwrap();

    let ev = w
        .commit(
            "act",
            "world://user",
            event::act_body("ledger.compact", "do", "r-e04", json!({})),
        )
        .expect("白名单主体执行不可逆动作应当放行（并留下摩擦痕迹）");

    let landed = flags_of(&ev);
    assert!(
        landed.iter().any(|f| f == "gate.friction:high"),
        "不可逆动作的摩擦旗标必须随事件落账，实得 {landed:?}"
    );

    // 出厂读法不认得它 —— 出厂本体 `flags: []`，一个旗标都没声明
    assert!(
        landed.iter().all(|f| !event::is_factory_flag(f)),
        "本用例的前提是『出厂读法不认得这个旗标』；实得 {landed:?}"
    );

    // 读回：原样保留（不是内存里的一次性字段）
    let back = w.ledger().read_all().unwrap();
    let same = back
        .iter()
        .find(|e| e["id"] == ev["id"])
        .expect("带旗标的那条 act 必须在账本里");
    assert_eq!(flags_of(same), landed, "摩擦旗标必须随事件落账、读回不变");

    // 读者按认得的那部分继续：known 为空、它进 ignored——**不因此拒收**
    let f = ont.read_flags(same, event::is_factory_flag);
    assert!(f.known.is_empty());
    assert_eq!(
        f.ignored,
        vec!["gate.friction:high".to_string()],
        "不认得的摩擦旗标必须进 ignored"
    );
    ont.validate(same)
        .expect("带不认得旗标的事件必须照样被接受");

    // 折叠不受影响：事件确实被折进去了
    let st = w.read_model().unwrap();
    assert_eq!(st.acts(), 1, "那条 act 必须被折叠");
    assert_eq!(st.seen(), 1);
}

/// **e05**：**公开写入入口**落一条带**任意未知旗标**的事件 ⇒ 被接受、**落笔**、折叠不受影响。
///
/// ## 这个用例的前身是一条**登记项**，它已经兑现，故按登记时写下的处置改写
///
/// 2026-09-28 上午它断言的是"公开写入入口**没有**旗标参数"（CLI 用法串里读不到 `flag`），
/// 并写明"谁给入口加上旗标参数，本条先红"。**同日工区 F 落了 `--flag`**（`src/main.rs`
/// 的用法串：`append <kind> <json-body> [actor] [--trace <id>] [--flag <名>]...`）
/// ⇒ 该断言**如期变红**，于是按登记时的处置改成**端到端断言**——
/// 登记项不是用来长期挂着的：合上它的那次改动会打红它，就是它存在的全部意义。
///
/// ## 仍然在册的边界（不许被读成"合上了"）
///
/// 出厂本体顶层 `flags` 仍是**空数组**（`world-core/src/ontology_definition/ontology.json:49`）⇒「未知旗标」在本体侧
/// 仍**没有已定义旗标可比对**（`tools/s1_sys_probe.sh` 的 `TC-048` ⑦；`WC-SCMP-001` §8.4 的 `G-83`）。
#[test]
fn e05_the_public_write_entry_lands_an_unknown_flag_end_to_end() {
    let dir = tmpdir("e05");
    let lp = dir.join("flagged.jsonl");
    let lp_plain = dir.join("plain.jsonl");
    let bin = env!("CARGO_BIN_EXE_world-core");
    let body = r#"{"subject":"world://notice/a","path":"muted","before":null,"after":true}"#;

    let append = |ledger: &Path, extra: &[&str]| {
        Command::new(bin)
            .args([
                "--ontology",
                &factory_ontology().display().to_string(),
                "--policy",
                &factory_policy().display().to_string(),
                "--ledger",
                &ledger.display().to_string(),
                "append",
                "change",
                body,
                "world://user",
            ])
            .args(extra)
            .output()
            .expect("无法启动被测二进制")
    };

    // ① 造：经**公开写入入口**提交一条带未知旗标的事件 ⇒ 必须被接受
    let out = append(&lp, &["--flag", "future.flag"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "带未知旗标的事件必须被接受（rc=0，方向与『未知家族』那条相反）；stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );

    // ② 落笔：账本里那一行**原样带着**那个旗标
    let text = fs::read_to_string(&lp).unwrap();
    let ev: Value = serde_json::from_str(text.lines().next().unwrap()).unwrap();
    assert_eq!(
        flags_of(&ev),
        vec!["future.flag"],
        "读回的 flags 必须保留原值（落笔的那一行就带着它）"
    );

    // ③ 反假：不给 `--flag` ⇒ flags 仍是空数组（证明 ② 的旗标确实来自那个参数）
    let out2 = append(&lp_plain, &[]);
    assert_eq!(out2.status.code(), Some(0));
    let text2 = fs::read_to_string(&lp_plain).unwrap();
    let ev2: Value = serde_json::from_str(text2.lines().next().unwrap()).unwrap();
    assert!(
        flags_of(&ev2).is_empty(),
        "不给旗标参数时必须是空数组，实得 {:?}",
        flags_of(&ev2)
    );

    // ④ 不影响后续折叠：两本账（同一条事件，一本带旗标、一本不带）的折叠结果**逐字节相同**
    let s1 = World::open_readonly(&factory_ontology(), &lp, &factory_policy())
        .unwrap()
        .read_model()
        .unwrap()
        .to_json()
        .to_string();
    let s2 = World::open_readonly(&factory_ontology(), &lp_plain, &factory_policy())
        .unwrap()
        .read_model()
        .unwrap()
        .to_json()
        .to_string();
    assert!(
        !s1.is_empty() && s1.len() > 2,
        "折叠结果不能是空的（否则『逐字节相同』是同义反复）：{s1}"
    );
    assert_eq!(s1, s2, "同一账本的折叠结果必须与不带该旗标时逐字节相同");

    // ⑤ 读者：认得的为空、它进 ignored；法律面照样接受
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let f = ont.read_flags(&ev, event::is_factory_flag);
    assert!(f.known.is_empty(), "出厂读法不该认得它，实得 {:?}", f.known);
    assert_eq!(f.ignored, vec!["future.flag"]);
    ont.validate(&ev).expect("带未知旗标的账本行必须被接受");

    // ⑥ 仍在册的边界：出厂两处"旗标表"都是空的（本体侧没有已定义旗标可比对）
    assert!(event::FLAGS.is_empty(), "出厂事件恒带的旗标表为空");
    let raw: Value =
        serde_json::from_str(&fs::read_to_string(factory_ontology()).unwrap()).unwrap();
    assert_eq!(
        raw["flags"].as_array().map(Vec::len),
        Some(0),
        "出厂本体顶层 flags 是空数组（`ontology.json:49`）——『未知旗标』在本体侧无对照面"
    );
}

// ────────────── 第 5 组：极小核心 ＋ 命名空间扩展（REQ-F-030）──────────────

/// **x01（判据②）**：扩展项与核心字段**重名 ⇒ 加载被拒**，且点名撞上的那一项。
///
/// 反例照抄 `tools/s1_sys_probe.sh` 的 `TC-049` ⑦（那份本体现在必须被拒）：
/// `concepts["body-fake"] = {"fields": {"body": "string"}}`。
#[test]
fn x01_an_extension_item_colliding_with_a_core_field_is_refused_at_load() {
    let dir = tmpdir("x01");

    // 正控①：出厂本体必须照常加载（防"什么都拒"）
    Ontology::load(&factory_ontology()).expect("出厂本体必须能加载");

    // 反例①：扩展项里再叫 `body`（与信封字段同名）
    let collide_field = write_ontology(&dir, "collide-field.json", |v| {
        v["_objects"]["body-fake"] = json!({ "fields": { "body": "string" } });
    });
    let e = Ontology::load(&collide_field).expect_err("扩展项与核心字段重名必须被拒");
    assert!(
        e.contains("ext.world.Ontology.CoreCollision"),
        "拒绝理由要带可判定的错误码，实得：{e}"
    );
    assert!(
        e.contains("body-fake") && e.contains("body"),
        "拒绝理由必须**点名**撞上的那一项（实体名与字段名），实得：{e}"
    );
    assert!(
        e.contains("kind") && e.contains("flags"),
        "拒绝理由要顺带列出核心字段集（否则只说了不行、没说怎么办），实得：{e}"
    );

    // 反例②：实体名本身与核心字段同名
    let collide_entity = write_ontology(&dir, "collide-entity.json", |v| {
        v["_objects"]["body"] = json!({ "fields": { "whatever": "string" } });
    });
    let e2 = Ontology::load(&collide_entity).expect_err("实体名与核心字段重名必须被拒");
    assert!(
        e2.contains("ext.world.Ontology.CoreCollision"),
        "实得：{e2}"
    );

    // 拒绝发生在**世界打开**这一步，且**不建账本**（法律不对就不许带病跑）
    let lp = dir.join("collide.jsonl");
    let opened = World::open(&collide_field, &lp, &factory_policy());
    assert!(opened.is_err(), "重名本体必须让世界拒绝启动");
    assert!(!lp.exists(), "法律不对时不得建账本（拒绝发生在落笔之前）");

    // 正控②：**只加扩展**的本体必须照常加载（否则这条检查会把判据③ 一起打死）
    let pure = write_ontology(&dir, "pure-ext.json", add_pure_extension);
    Ontology::load(&pure).expect("只加扩展的本体必须能加载");
}

/// **x02（判据③）**：换一份**只加扩展**的本体 ⇒ 同一账本**折叠结果逐字节不变**，
/// 且新法律**照读**旧账本。
///
/// 反同义反复（两部分）：
/// 1. 词表 hash **必须变**（否则"换本体"没发生，相等是同义反复）；
/// 2. 负控：把**核心**语义改掉（给 `change` 加一个必填字段）⇒ 同一条旧账本行**必须读不过去**
///    ⇒ 这条判据分得清"只加扩展"与"改核心"，不是恒绿。
#[test]
fn x02_a_pure_extension_keeps_the_fold_byte_identical() {
    let dir = tmpdir("x02");
    let (_lp, lines) = base_ledger(&dir);

    let ont = Ontology::load(&factory_ontology()).unwrap();
    let pure_path = write_ontology(&dir, "pure-ext.json", add_pure_extension);
    let ont_ext = Ontology::load(&pure_path).unwrap();

    // ① 反同义反复：本体**确实**换了（内容寻址）
    assert_ne!(
        ont.vocab_hash(),
        ont_ext.vocab_hash(),
        "只加扩展也会换词表身份——若两值相等，说明'换本体'根本没发生"
    );

    // ② 新法律照读旧账本：每一行都必须仍然合法
    for ev in &lines {
        ont_ext
            .validate(ev)
            .expect("只加扩展的法律必须照读旧账本（判据③ 的另一半）");
    }

    // ③ 折叠结果逐字节不变
    let before = read_with(&ont, &lines).unwrap().to_json().to_string();
    let after = read_with(&ont_ext, &lines).unwrap().to_json().to_string();
    assert!(!before.is_empty() && before.len() > 2, "折叠结果不能是空的");
    assert_eq!(
        before, after,
        "换一份只加扩展的本体 ⇒ 同一账本的折叠结果必须逐字节相同"
    );

    // ④ 负控：改**核心**（给 change 家族加一个必填字段）⇒ 旧账本行必须读不过去
    let core_changed = write_ontology(&dir, "core-changed.json", |v| {
        v["families"]["change"]["required"]
            .as_array_mut()
            .unwrap()
            .push(json!("extra_required"));
    });
    let ont_bad = Ontology::load(&core_changed).unwrap();
    let e = ont_bad
        .validate(&lines[0])
        .expect_err("改了核心必填字段后，旧账本行必须读不过去（否则本判据恒绿）");
    assert!(
        e.to_string().contains("ext.world.Ontology.MissingField"),
        "负控的拒绝理由要可判定，实得：{e}"
    );
}
