//! 第 6 组（`trace` 语义）＋第 7 组（通告的闸）的**写入入口**用例，
//! 以及第 4 组「未知旗标必须忽略」的**落笔**那一半（`REQ-F-029`：旗标也要能从入口给出）。
//!
//! ## 为什么单立一个文件（不并进 `contract.rs` / `delivery.rs`）
//!
//! 本文件的两组判据都只在**命令行写入入口**这一级成立，与既有用例不是同一个面：
//!
//! | 既有用例 | 它测的面 | 它绿而本文件的判据仍可以红的情形 |
//! |---|---|---|
//! | `contract.rs::c23*` | 库级（直调 `World::commit`） | `--trace` 这个参数**根本没人解析**；`append` 的接线整段没写 |
//! | `delivery.rs::d05/d06` | 库级配对（直调 `World::commit_requested`） | 同上——库里有入口，命令行没有 |
//!
//! ⇒ **库里能过不等于用户能用**。本文件跑的是真二进制（`CARGO_BIN_EXE_world-core`）。
//!
//! ## 书与规格的逐字依据
//!
//! - 书 §4.2（通告的闸）逐字：「通告另有一道窄闸。凡是以"世界拦下过什么"为名的通告，
//!   只许世界自己写；其余通告的写信人必须先在主体名单里。这条守的是审计的根：
//!   如果"世界拒绝过这件事"这句话任何人都能替世界说，那么账本里每一句"世界说过"
//!   都不再可信。」
//! - 书 §4.6 逐字：「请求与结果的配对靠两处对齐：同一个请求编号，以及"因为哪一条"
//!   那一格指回提出这件事的那条记录。两处都在账本上，配对因此可以在事后核对，
//!   不必依赖当时在场的谁记得。」
//! - `REQ-F-031` 判据 (2)：带 `trace` 的事件必须被接受并落笔；**不带** `trace` 的事件
//!   同样必须被接受并落笔；判据 (3)：`read` 读回时 `trace` 的**值类型与字节**与落笔时
//!   逐字节相同；判据 (4)：`trace` 指向**不存在的 `id`** 时必须被接受并落笔。
//! - 任务出处：`openspec/changes/cover-unimplemented-capabilities/tasks.md` 第 6 组、
//!   第 7 组（第 7 组无需求号，其条文即上面书 §4.2 那一段），以及第 4 组 4.1 的
//!   「必须**被接受、落笔**」半条（`REQ-F-029`；书 §2.11「未知的标记不碍事」那一侧）。
//!
//! ## 配对与 `trace` **不是一回事**（口径对齐，不重复造）
//!
//! 配对键是 `act` 信纸**必填**的 `request_id`（`src/common/pairing.rs` 头注：`trace` 是"因为哪一条"
//! 的引用，`pairing` 是"请求号配对"）。本文件只断言"两件事没有混成一件"，
//! 配对本身的各种形态由 `tests/delivery.rs::d05/d06` 负责。

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::{json, Value};
use world_core::{common::event, Envelope, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-trace-notice-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    d
}

fn manifest() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// 跑一次被测二进制：`--ontology` / `--policy` 固定取出厂件，`--ledger` 指向本用例的临时账本。
///
/// 返回 `(退出码, stdout, stderr)`——**三个都要**：只看退出码会漏掉"rc=0 但没落笔"
/// 与"rc=2 但拒绝理由不对"这两类。
fn run(d: &Path, args: &[&str]) -> (i32, String, String) {
    let mut argv: Vec<String> = vec![
        "--ontology".into(),
        manifest()
            .join("src/ontology_definition/ontology.json")
            .display()
            .to_string(),
        "--policy".into(),
        manifest()
            .join("src/gate/policy.json")
            .display()
            .to_string(),
        "--ledger".into(),
        d.join("ledger.jsonl").display().to_string(),
    ];
    argv.extend(args.iter().map(|s| (*s).to_string()));
    let out = Command::new(env!("CARGO_BIN_EXE_world-core"))
        .args(&argv)
        .output()
        .expect("无法启动被测二进制");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

/// 账本**原文**（字节，不是解析后的值）——判据 (3) 要的是**逐字节**，故必须按字节读。
fn ledger_bytes(d: &Path) -> Vec<u8> {
    fs::read(d.join("ledger.jsonl")).unwrap_or_default()
}

/// 字节级子串查找（不引新依赖）。空针视为"没找到"，免得空串恒真。
fn has_bytes(hay: &[u8], needle: &str) -> bool {
    let n = needle.as_bytes();
    !n.is_empty() && hay.windows(n.len()).any(|w| w == n)
}

/// 账本里的全部事件（一行一条；空行跳过）。
fn events(d: &Path) -> Vec<Value> {
    let raw = ledger_bytes(d);
    String::from_utf8_lossy(&raw)
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| serde_json::from_str(l).expect("账本每一行都必须是合法 JSON"))
        .collect()
}

fn kinds(d: &Path, notice_type: &str) -> usize {
    events(d)
        .iter()
        .filter(|e| e["body"]["type"] == json!(notice_type))
        .count()
}

fn flow(d: &Path, notice_type: &str) -> Value {
    events(d)
        .iter()
        .find(|e| e["body"]["type"] == json!(notice_type))
        .cloned()
        .unwrap_or_else(|| panic!("账本里必须有 `{notice_type}` 这条流水：{:?}", events(d)))
}

// ═══════════════════════════════════════════════════════════════════════════
// 第 6 组 —— `trace` 语义（`REQ-F-031` 判据 (2)(3)(4)）经**命令行写入入口**
// ═══════════════════════════════════════════════════════════════════════════

/// **f61**（任务 6.1 ＋ 判据 (2) 正向、(3)）：`trace` 能从写入入口给出，落账，读回**逐字节**不变。
///
/// 取值刻意带非 ASCII：这样"逐字节"才是**真的字节判据**，而不是"解析回来相等"
/// （后者在值被 `\uXXXX` 转义或被重新编码时**照样绿**）。
///
/// 变异（本轮实测的**红名单**）：① 把 `src/lib.rs` 里 `event::with_trace(&mut ev, trace);`
/// 那一行删掉 ⇒ 红（`trace` 一个字都写不进去；`f64`／`f65` 同红，`f62`／`f63` 仍绿）；
/// ② 把 `src/main.rs` 里 `--trace` 的接线摘掉（回到 `w.commit(kind, &actor, body)`）
/// ⇒ 红名单**逐条相同**；③ 给它加"引用完整性"校验（即 `f65` 那条变异）⇒ 本条也红——
/// 因为本用例的取值本身就指向一个**不存在**的 `id`（v1 明文允许，见判据 (4)）。
#[test]
fn f61_append_with_trace_lands_and_reads_back_byte_for_byte() {
    let d = tmpdir("f61");
    let traced = "e-意图-001";

    let (code, out, err) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"job.done","subject":"world://job/1","payload":{"exit":0}}"#,
            "world://user",
            "--trace",
            traced,
        ],
    );
    assert_eq!(
        code, 0,
        "带 trace 的事件必须被接受并落笔（判据 (2) 正向）；stderr={err}"
    );
    assert!(
        out.contains("\"trace\":\"e-意图-001\""),
        "append 的 stdout 里必须原样出现 trace；stdout={out}"
    );

    // ── 判据 (3)：三处字节必须一致：落笔行 / append 的 stdout / read 的 stdout ──
    let raw = ledger_bytes(&d);
    assert!(
        has_bytes(&raw, "\"trace\":\"e-意图-001\""),
        "账本**原文**必须逐字节保留 trace；账本={}",
        String::from_utf8_lossy(&raw)
    );

    let (rc_read, read_out, read_err) = run(&d, &["read"]);
    assert_eq!(rc_read, 0, "read 必须能读回本条；stderr={read_err}");
    let landed = String::from_utf8_lossy(&raw)
        .lines()
        .next()
        .unwrap_or_default()
        .to_string();
    let read_line = read_out.lines().next().unwrap_or_default().to_string();
    assert_eq!(
        read_line, landed,
        "read 的输出行必须与账本落笔行**逐字节**相同（判据 (3)）"
    );

    // 类型也是判据的一部分（判据 (3) 说的是"值类型与字节"）
    let evs = events(&d);
    assert_eq!(evs.len(), 1, "只应落一条事件：{evs:?}");
    assert_eq!(
        evs[0]["trace"],
        json!(traced),
        "读回来必须是同一个字符串（不得改型、不得丢弃）"
    );
}

/// **f62**（判据 (2) 的另一个方向）：不写 `--trace` ⇒ 照样接受并落笔，且**不写该键**。
///
/// 为什么两个方向都要：只测"带了能写"时，把 `trace` 写成恒有（例如恒写空串）
/// 的实现照样绿——而"没有因果"与"因果指向空"是两件事。
///
/// 变异：把 `src/lib.rs` 的 `event::with_trace(&mut ev, trace);` 换成
/// `ev["trace"] = Value::String(trace.unwrap_or("").to_string());` ⇒ 本条红而 `f61` 仍绿。
#[test]
fn f62_append_without_trace_writes_no_trace_key_and_still_lands() {
    let d = tmpdir("f62");

    let (code, out, err) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"job.done","subject":"world://job/1","payload":{"exit":0}}"#,
            "world://user",
        ],
    );
    assert_eq!(
        code, 0,
        "不带 trace 的事件同样必须被接受并落笔（判据 (2) 反向）；stderr={err}"
    );
    assert!(
        !out.contains("trace"),
        "没给 trace 就不许写该键（不写 null）；stdout={out}"
    );
    let raw = ledger_bytes(&d);
    assert!(
        !has_bytes(&raw, "trace"),
        "账本原文里不得出现 trace 键；账本={}",
        String::from_utf8_lossy(&raw)
    );

    // 反假：事件**必须真的落了**，否则"不带也接受"是空话
    let evs = events(&d);
    assert_eq!(evs.len(), 1, "事件必须真的落笔：{evs:?}");
    assert_eq!(evs[0]["seq"], json!(1), "落笔位置号从 1 起：{evs:?}");
    assert_eq!(
        evs[0]["body"]["type"],
        json!("job.done"),
        "信纸必须完整：{evs:?}"
    );
}

/// **f63**：`--trace ""`（给了空串）按**未给**处理 ⇒ 不写该键。
///
/// 口径出处：`src/common/event.rs::with_trace` 逐字「空串视为未给（否则会写出一个指不到
/// 任何事件的 `trace`）」。
///
/// 变异：把 `src/common/event.rs::with_trace` 里的 `if !t.is_empty()` 去掉（有值就写）
/// ⇒ 本条红而 `f61`／`f62` 仍绿——这正是"空串"这一格**只有本用例在守**的证据。
#[test]
fn f63_empty_trace_is_treated_as_absent() {
    let d = tmpdir("f63");
    let (code, out, err) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"job.done","subject":"world://job/1","payload":{}}"#,
            "world://user",
            "--trace",
            "",
        ],
    );
    assert_eq!(code, 0, "空串 trace 不得导致拒绝；stderr={err}");
    assert!(
        !out.contains("trace"),
        "空串按未给处理 ⇒ 不许写该键；stdout={out}"
    );
    let raw = ledger_bytes(&d);
    assert!(
        !has_bytes(&raw, "trace"),
        "账本原文里不得出现 trace 键；账本={}",
        String::from_utf8_lossy(&raw)
    );
    assert_eq!(events(&d).len(), 1, "事件必须照样落笔");
}

/// **f64**（任务 6.2 的"可追"面）：带 `trace` 的结果**从账本能追回**它指的那条意图。
///
/// 断言三处（书 §4.6 的两处对齐）：
/// ① 配对键 = 同一个 `request_id`（`src/common/pairing.rs`，本文件不重复造配对判据）；
/// ② 结果的 `trace` **逐字等于**意图的 `id`；
/// ③ `pairs()` 里**只有一个**请求号——`trace` 没有自己造出第二个配对键（"不是一回事"）。
///
/// 变异：删掉 `src/lib.rs` 的 `event::with_trace` 调用 ⇒ 结果不带 `trace` ⇒
/// `trace_agrees()` 由 `Some(true)` 变 `None`，本条红。
#[test]
fn f64_a_traced_result_can_be_traced_back_from_the_ledger() {
    let d = tmpdir("f64");

    // ① 意图先落账，取回它的 `id`——`trace` 要指的就是它
    let (c1, o1, e1) = run(
        &d,
        &[
            "append",
            "act",
            r#"{"capability":"job.start","verb":"do","request_id":"r-f64","params":{}}"#,
            "world://agent/1",
        ],
    );
    assert_eq!(c1, 0, "意图必须落账；stderr={e1}");
    let intent: Value = serde_json::from_str(o1.trim()).expect("append 的 stdout 是一条事件 JSON");
    let intent_id = intent["id"].as_str().expect("事件必须带 id").to_string();

    // ② 结果带 `trace` 指回意图
    let (c2, _o2, e2) = run(
        &d,
        &[
            "append",
            "act",
            r#"{"capability":"job.start","verb":"do","request_id":"r-f64","params":{"result":"ok"}}"#,
            "world://agent/1",
            "--trace",
            intent_id.as_str(),
        ],
    );
    assert_eq!(c2, 0, "带 trace 的结果必须落账；stderr={e2}");

    // ③ 事后核对：只用账本
    let evs = events(&d);
    assert_eq!(evs.len(), 2, "两半都要在账本上：{evs:?}");
    let pair = match world_core::common::pairing::find_pair(&evs, "r-f64") {
        world_core::common::pairing::Outcome::Complete(p) => p,
        other => panic!("两半都在账本上，应当成对，实得 {other:?}"),
    };
    assert_eq!(pair.intents[0]["id"], json!(intent_id.clone()));
    assert_eq!(
        pair.results[0]["trace"],
        json!(intent_id.clone()),
        "因果那一格必须指回提出这件事的那条记录（书 §4.6 第二处对齐）"
    );
    assert_eq!(
        pair.trace_agrees(),
        Some(true),
        "两处对齐都要成立（请求号 ＋ 因为哪一条）"
    );

    // ④ `trace` 不是配对键：账本里的配对登记只有一个请求号
    let ids: Vec<String> = world_core::common::pairing::pairs(&evs)
        .iter()
        .map(|p| p.request_id.clone())
        .collect();
    assert_eq!(
        ids,
        vec!["r-f64".to_string()],
        "配对键是 `request_id`；`trace` 不得自己造出第二个配对键"
    );
}

/// **f65**（判据 (4) 经写入入口）：`trace` 指向**不存在**的 `id` ⇒ 必须被接受并落笔。
///
/// v1 **不做**引用完整性校验；这一条是**反假条款**——哪天实现开始拒绝，本条即变红。
/// 既有的可执行面（`tools/s1_sys_probe.sh` 的 TC-052）只用手写账本行，**不经过入口**；
/// 本用例补的正是"经入口"这一半。
///
/// 变异：在 `src/lib.rs` 的 `commit_verbatim` 里给 `trace` 加一段引用完整性校验
/// （账本里找不到那个 `id` 即拒）⇒ 本条红（`f61` 同红——它的取值也指向不存在的 `id`；
/// `f62`／`f63`／`f64` 仍绿，因为那三条要么不写 `trace`、要么指向真事件）。
#[test]
fn f65_a_trace_pointing_at_a_nonexistent_id_is_still_accepted() {
    let d = tmpdir("f65");
    let dangling = "e-这条事件不在账本里";

    let (code, out, err) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"job.done","subject":"world://job/1","payload":{}}"#,
            "world://user",
            "--trace",
            dangling,
        ],
    );
    assert_eq!(
        code, 0,
        "v1 不做引用完整性校验：指向不存在的 id 不得导致拒绝（判据 (4)）；stderr={err}"
    );

    let evs = events(&d);
    assert_eq!(evs.len(), 1, "必须真的落笔：{evs:?}");
    assert_eq!(
        evs[0]["trace"],
        json!(dangling),
        "取值必须原样落账；stdout={out}"
    );
    // 反假：账本里**确实**没有那个 id，否则本条是空转
    assert!(
        evs.iter().all(|e| e["id"] != json!(dangling)),
        "这个 id 必须在账本里不存在，否则'指向不存在'这句话不成立：{evs:?}"
    );
}

/// **f66**：`--trace`／`--flag` 后面没有值 ⇒ **用法错误**（rc=1），且**不落笔**。
///
/// 为什么单列：静默降级成"没给"会让调用方以为因果/旗标记下了，而账本里什么都没有
/// （与 `--owner-uid` 打错即拒启同一口径：静默失效比不做更危险）。
///
/// 变异：把 `src/main.rs` 里 `--trace` 分支的 `None => env_bad = Some(..)` 改成
/// "没有值就当没给"（`if let Some(v) = args.get(i) { … }`）⇒ 本条红（rc 由 1 变 0，且事件落了笔）。
#[test]
fn f66_a_flag_without_a_value_is_a_usage_error() {
    let body = r#"{"type":"job.done","subject":"world://job/1","payload":{}}"#;

    for dangling in ["--trace", "--flag"] {
        let d = tmpdir("f66");
        let (code, _out, err) = run(&d, &["append", "notice", body, "world://user", dangling]);
        assert_eq!(code, 1, "`{dangling}` 缺值属用法错误；stderr={err}");
        assert!(
            err.contains("BadEnvelopeArg"),
            "用法错误要点名错误码；stderr={err}"
        );
        assert!(
            ledger_bytes(&d).is_empty(),
            "用法错误**不许落笔**（{dangling}）；账本={}",
            String::from_utf8_lossy(&ledger_bytes(&d))
        );
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// 第 4 组 —— 旗标经**写入入口**落笔（`REQ-F-029`「未知旗标必须忽略」的落笔那一半）
//
// 出厂本体 `ontology.json` 的 `flags` 是**空数组**（一个旗标都没声明）⇒ 出厂读法
// **一个旗标都不认得**。于是"本读法不认得的旗标照样落笔、照样折叠"这件事，
// 只能靠"经入口把一个出厂没声明过的旗标写进去"来验——这就是本组三条用例的位置。
// ═══════════════════════════════════════════════════════════════════════════

/// **f67**：旗标能从命令行写入入口给出、落账、读回原样；不给旗标时 `flags` 仍是空数组。
///
/// 四件事（各自可单独变红）：
/// ① **不给** `--flag` ⇒ `flags` 是**空数组**——"加了这个参数"不许改掉既有行为；
/// ② 给两个**出厂没声明过**的旗标 ⇒ 照样落笔，且**按给的顺序**排（顺序是契约的一部分）；
/// ③ 同一个旗标给两次 ⇒ **只留一个**（`event::with_flag` 的口径）；
/// ④ 落笔行里 `flags` 的**字节**与给的逐字相同（判据 (3) 的同一条纪律搬到旗标上）。
///
/// 变异：① 把 `src/lib.rs::commit_verbatim` 里 `for f in flags { event::with_flag(&mut ev, f); }`
/// 整段删掉 ⇒ ②③④ 红而 ① 仍绿；② 把该循环里的 `event::with_flag` 换成直接
/// `arr.push(Value::String(f.clone()))`（去掉去重）⇒ **只**③ 红。
#[test]
fn f67_flags_land_through_the_write_entry_and_unknown_ones_are_kept() {
    let body = r#"{"type":"job.done","subject":"world://job/1","payload":{}}"#;

    // ① 不给旗标 ⇒ 空数组（与这个参数出现之前一字不差）
    let d1 = tmpdir("f67a");
    let (c1, _o1, e1) = run(&d1, &["append", "notice", body, "world://user"]);
    assert_eq!(c1, 0, "不带旗标的写入必须照样成功；stderr={e1}");
    let evs1 = events(&d1);
    assert_eq!(
        evs1[0]["flags"],
        json!([]),
        "不给 `--flag` ⇒ `flags` 必须是空数组（既有行为不许被这个参数改掉）：{evs1:?}"
    );

    // ②③④ 给出厂**没声明过**的旗标：照样落笔、按序、去重、逐字节保留
    let d = tmpdir("f67b");
    let (c2, out, err) = run(
        &d,
        &[
            "append",
            "notice",
            body,
            "world://user",
            "--flag",
            "future.flag",
            "--flag",
            "another.flag",
            "--flag",
            "future.flag",
        ],
    );
    assert_eq!(c2, 0, "不认得的旗标必须放行（REQ-F-029）；stderr={err}");

    let evs = events(&d);
    assert_eq!(evs.len(), 1, "必须真的落笔：{evs:?}");
    assert_eq!(
        evs[0]["flags"],
        json!(["future.flag", "another.flag"]),
        "旗标必须按给的顺序落账，且同一个只留一个（去重）；实得 {}",
        evs[0]["flags"]
    );
    // ④ 字节级：落笔行里 flags 那一段与给的逐字相同
    let raw = ledger_bytes(&d);
    assert!(
        has_bytes(&raw, r#""flags":["future.flag","another.flag"]"#),
        "账本原文里 flags 必须逐字节保留（含顺序）；账本={}",
        String::from_utf8_lossy(&raw)
    );
    assert!(
        out.contains(r#""flags":["future.flag","another.flag"]"#),
        "append 的 stdout 必须原样显示 flags；stdout={out}"
    );
    // 反假：这两个旗标**不在**出厂本体的声明里（`ontology.json` 的 `flags` 是空数组）——
    // 否则本用例验的不是"未知旗标"。
    let ont: Value = serde_json::from_str(
        &fs::read_to_string(manifest().join("src/ontology_definition/ontology.json")).unwrap(),
    )
    .unwrap();
    assert_eq!(
        ont["flags"].as_array().map(Vec::len),
        Some(0),
        "出厂本体一个旗标都没声明——这正是『未知旗标』的对照面"
    );
}

/// **f68**：调用方**不许**用内核保留前缀（`gate.`）给旗标——拒，**且留流水**。
///
/// 为什么必须有这条：信封的 `flags` 里混着**两种作者**——内核依裁决写的那一格
/// （闸的摩擦标记 `gate.friction:<等级>`）与调用方带来的旗标。若调用方能随便写 `gate.`
/// 开头的旗标，他就能**替世界说**"这件事被加过摩擦"；账本里伪造的那一格与真的那一格
/// **逐字同形、事后不可区分**——与 `gate.*` 通告的伪造（`D-13`）同一形状。
///
/// 三件事：
/// ① `--flag gate.friction:high` ⇒ rc=2、点名 `ext.world.Gate.FlagNotAllowed`、**不落笔**；
/// ② **留流水**（书 §4.2「被拦下的请求也要留痕」），且流水的理由**逐字点名那个旗标**；
/// ③ **判定的先后**：保留旗标 ＋ 一个门禁本来就会拒的能力 ⇒ 拿到的是"旗标被拒"，
///    不是"能力被拒"（两条拒绝路径不许互相冒充）。
///
/// 变异：① 把 `commit_verbatim` 里那段前缀检查整段删掉 ⇒ ①②③ 红
/// （事件会带着伪造的摩擦旗标落账）；② 把该段挪到 `self.adjudicate(...)` **之后**
/// ⇒ **只**③ 红（顺序错了，其余不变）。
#[test]
fn f68_a_caller_supplied_reserved_flag_is_refused_and_leaves_a_flow() {
    let d = tmpdir("f68");
    let body = r#"{"type":"job.done","subject":"world://job/1","payload":{}}"#;

    // ① 保留前缀 ⇒ 拒，且事件不落笔
    let (c1, _o1, e1) = run(
        &d,
        &[
            "append",
            "notice",
            body,
            "world://user",
            "--flag",
            "gate.friction:high",
        ],
    );
    assert_eq!(
        c1, 2,
        "内核保留前缀的旗标必须被拒（在册主体也不许替世界署名）；stderr={e1}"
    );
    assert!(
        e1.contains("ext.world.Gate.FlagNotAllowed"),
        "拒绝理由必须点名错误码；stderr={e1}"
    );
    let evs = events(&d);
    assert_eq!(
        evs.iter()
            .filter(|e| e["body"]["type"] == json!("job.done"))
            .count(),
        0,
        "被拒的事件绝不许落笔：{evs:?}"
    );

    // ② 留痕：一条内核自己的流水，理由里逐字点名那个旗标
    let f = flow(&d, "gate.flag-not-allowed");
    let reason = f["body"]["payload"]["reason"].as_str().unwrap_or_default();
    assert!(
        reason.contains("gate.friction:high"),
        "流水的理由必须**逐字点名**被拒的那个旗标（`refused` 指纹只覆盖发起者＋信纸，不含旗标）；f={f}"
    );
    assert!(
        f["body"]["payload"]["refused"]
            .as_str()
            .unwrap_or_default()
            .starts_with("fnv1a64:"),
        "流水同样要带被拒对象的规范形式指纹：{f}"
    );

    // ③ 先后：保留旗标 ＋ 门禁本来就会拒的能力（agent 请求不可逆动作 ⇒ 加摩擦）
    let d2 = tmpdir("f68b");
    let (c2, _o2, e2) = run(
        &d2,
        &[
            "append",
            "act",
            r#"{"capability":"ledger.compact","verb":"do","request_id":"r-f68","params":{}}"#,
            "world://agent/1",
            "--flag",
            "gate.friction:high",
        ],
    );
    assert_eq!(c2, 2, "这条同样必须被拒；stderr={e2}");
    assert!(
        e2.contains("FlagNotAllowed") && !e2.contains("AwaitingApproval"),
        "旗标那一段在门禁裁决**之前**：拿到的是『旗标被拒』，不是『能力被拒』；stderr={e2}"
    );
    assert_eq!(
        kinds(&d2, "gate.awaiting-approval"),
        0,
        "既然拒在旗标那一段，就不该同时留下『能力被拒』的流水（两条路径不许互相冒充）"
    );
    assert_eq!(kinds(&d2, "gate.flag-not-allowed"), 1, "只留旗标那一条流水");

    // 正控：同一本账上，非保留前缀的旗标照样落笔（防"把正常路径一并打死"）
    let (c3, _o3, e3) = run(
        &d2,
        &[
            "append",
            "notice",
            body,
            "world://user",
            "--flag",
            "future.flag",
        ],
    );
    assert_eq!(c3, 0, "非保留前缀的旗标必须放行；stderr={e3}");
}

/// **f69**（库侧入口）：`World::commit_envelope` 能带旗标落笔；
/// `Envelope::default()` 与 `World::commit` 落出来的事件**同形**。
///
/// 为什么要有这一条：命令行那三条验的是产物入口，而**工区 E 的 4.1 要用的是库入口**
/// （它在 `tests/**` 里直调 `World`）。两条入口必须都能给旗标，且"不给"时**键集不变**——
/// 加一个可选字段不许悄悄改掉既有事件的形状。
///
/// 变异：把 `World::commit` 的实现改成带一个默认 `trace` 的薄壳
/// （`commit_verbatim(kind, actor, body, Some("auto"), None, &[])`）⇒ 本条红（键集多出 `trace`）。
#[test]
fn f69_commit_envelope_carries_flags_and_default_equals_commit() {
    fn keys(v: &Value) -> Vec<String> {
        let mut k: Vec<String> = v.as_object().expect("事件是对象").keys().cloned().collect();
        k.sort();
        k
    }
    let notice = || event::notice_body("job.done", "world://job/1", json!({}));
    let open = |tag: &str| {
        let d = tmpdir(tag);
        let lp = d.join("ledger.jsonl");
        (
            World::open(
                &manifest().join("src/ontology_definition/ontology.json"),
                &lp,
                &manifest().join("src/gate/policy.json"),
            )
            .expect("出厂本体与策略应当能打开"),
            d,
        )
    };

    // ① `commit` 与 `commit_envelope(default)`：**键集相同**、都不带 `trace`/`to`
    let (mut wa, _da) = open("f69a");
    let a = wa
        .commit("notice", "world://user", notice())
        .expect("commit 应当成功");
    let (mut wb, _db) = open("f69b");
    let b = wb
        .commit_envelope("notice", "world://user", notice(), &Envelope::default())
        .expect("commit_envelope(default) 应当成功");
    assert_eq!(
        keys(&a),
        keys(&b),
        "`Envelope::default()` 必须与 `commit` 落出**同形**的事件（键集逐字相等）"
    );
    assert!(
        !keys(&a).contains(&"trace".to_string()),
        "没给因果就不许写 trace 键"
    );
    assert!(
        !keys(&a).contains(&"to".to_string()),
        "没给目的地就不许写 to 键"
    );
    assert_eq!(a["flags"], json!([]), "没给旗标就是空数组");

    // ② 库入口给旗标 ⇒ 落账、读回
    let (mut wc, dc) = open("f69c");
    let c = wc
        .commit_envelope(
            "notice",
            "world://user",
            notice(),
            &Envelope::new().with_flag("future.flag"),
        )
        .expect("带未知旗标的写入必须放行");
    assert_eq!(c["flags"], json!(["future.flag"]), "旗标必须落在这条事件上");
    let back = events(&dc);
    assert_eq!(back.len(), 1, "必须真的落笔");
    assert_eq!(back[0]["flags"], json!(["future.flag"]), "读回不变");
}

// ═══════════════════════════════════════════════════════════════════════════
// 第 7 组 —— 通告的闸（书 §4.2 末段；本组**无需求号**）
// ═══════════════════════════════════════════════════════════════════════════

/// **f71**（任务 7.1）：通告**也过闸**——"不该由它发的通告"必须被拒，**且留流水**。
///
/// 两条路径各造一条（书 §4.2 末段的两句话各对应一条），再加一条**正控**：
///
/// | # | 谁发的 | 发的通告 | 应当 |
/// |---|---|---|---|
/// | ① | 在册主体 `world://user` | `type=gate.rejected`（**保留前缀**） | **拒**（保留前缀只许内核自己写） |
/// | ② | **不在册**主体 `world://stranger` | `type=my.own.notice` | **拒**（写信人必须先在本体名单里） |
/// | ③ | 在册主体 `world://agent/1` | `type=my.own.notice` | **通过**（正控：修法不许把正常路径打死） |
///
/// 变异：把 `src/lib.rs` 的 `"notice" => { self.adjudicate_notice(actor, body)?; Ok(None) }`
/// 改回 `"notice" => Ok(None)`（即**撤掉这道闸**）⇒ ①② 都落笔 ⇒ 本条红
/// （`tests/contract.rs` 的 `c23_notice_with_reserved_prefix_is_refused_for_outsiders` 与
/// `c23_notice_from_unlisted_actor_is_refused` 同红——同一个闸，本条补的是**命令行**这一级
/// 与「**留流水**」那一格）。
#[test]
fn f71_notices_that_must_not_be_sent_are_refused_and_leave_a_flow() {
    let d = tmpdir("f71");

    // ① 保留前缀：在册主体也写不了"世界拦下过什么"
    let (c1, _o1, e1) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"gate.rejected","subject":"world://job/9","payload":{"reason":"伪造"}}"#,
            "world://user",
        ],
    );
    assert_eq!(
        c1, 2,
        "保留前缀通告必须被拒（在册也不许冒充世界）；stderr={e1}"
    );
    assert!(
        e1.contains("ext.world.Gate.NoticeNotAllowed"),
        "拒绝理由必须点名错误码；stderr={e1}"
    );

    // ② 非保留前缀，但写信人不在册
    let (c2, _o2, e2) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"my.own.notice","subject":"world://job/1","payload":{}}"#,
            "world://stranger",
        ],
    );
    assert_eq!(c2, 2, "不在册的主体不得写通告；stderr={e2}");
    assert!(
        e2.contains("ext.world.Gate.NoticeRejected"),
        "拒绝理由必须点名错误码；stderr={e2}"
    );

    // ③ 正控
    let (c3, _o3, e3) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"my.own.notice","subject":"world://job/1","payload":{}}"#,
            "world://agent/1",
        ],
    );
    assert_eq!(c3, 0, "在册主体写普通通告应当通过（防恒红）；stderr={e3}");

    // ── 账本原文：被拒的**没落笔**，正控的**落了** ──
    let evs = events(&d);
    assert_eq!(
        kinds(&d, "gate.rejected"),
        0,
        "伪造的内核流水绝不许进账本：{evs:?}"
    );
    let own: Vec<&Value> = evs
        .iter()
        .filter(|e| e["body"]["type"] == json!("my.own.notice"))
        .collect();
    assert_eq!(
        own.len(),
        1,
        "正控的通告必须落笔，被拒的那条不许落笔：{evs:?}"
    );
    assert_eq!(
        own[0]["actor"],
        json!("world://agent/1"),
        "落笔的通告写信人必须是在册主体：{evs:?}"
    );

    // ── 留痕：**两条拒绝各留一条内核自己的流水**（拦得住，也记得下）──
    assert_eq!(
        kinds(&d, "gate.notice-not-allowed"),
        1,
        "保留前缀被拒必须留流水：{evs:?}"
    );
    assert_eq!(
        kinds(&d, "gate.notice-rejected"),
        1,
        "不在册被拒必须留流水：{evs:?}"
    );

    let f1 = flow(&d, "gate.notice-not-allowed");
    let f2 = flow(&d, "gate.notice-rejected");
    for f in [&f1, &f2] {
        assert_eq!(f["kind"], json!("notice"), "流水也是通告（同一家族）：{f}");
        let refused = f["body"]["payload"]["refused"].as_str().unwrap_or_default();
        assert!(
            refused.starts_with("fnv1a64:"),
            "流水必须点名它在拒绝什么（规范形式指纹）；f={f}"
        );
    }
    // 流水记的是**哪一次尝试**：发起人 与 被拒信纸的 subject 是两件事，各占一格
    assert_eq!(
        f1["actor"],
        json!("world://user"),
        "流水主体 = 被拒尝试的发起人：{f1}"
    );
    assert_eq!(
        f1["body"]["payload"]["refused_subject"],
        json!("world://job/9"),
        "`refused_subject` = **被拒信纸**的 subject，不是发起人：{f1}"
    );
    assert_eq!(f2["actor"], json!("world://stranger"), "{f2}");
    assert_eq!(
        f2["body"]["payload"]["refused_subject"],
        json!("world://job/1"),
        "{f2}"
    );
}

/// **f72**（任务 7.2）：两条拒绝路径**互不冒充**，且 `refused` 指纹必须**随被拒对象变**。
///
/// 三件事（各自可单独变红）：
///
/// ① **判定的先后**：不在册主体提交**保留前缀**通告 ⇒ 必须报"保留前缀"那条错
///    （`NoticeNotAllowed`），**不是**"不在册"（`NoticeRejected`）；
/// ② **流水类型互不相同**：保留前缀路径留 `gate.notice-not-allowed`、
///    不在册路径留 `gate.notice-rejected`——同一个 `refused` 字段、两条不同的路；
/// ③ **指纹随被拒对象变**：同一条路径上换 actor／换信纸 ⇒ 指纹必须不同。
///    为什么单列：只断言"同一次尝试同一指纹"是**不够的**——一个**常量**指纹
///    能同时满足「可复算」与「同一次尝试相同」两条（既有 `contract.rs::c23*` 正是这样），
///    那样的指纹等于没点名。
///
/// 变异：把 `src/lib.rs::adjudicate_notice` 里"保留前缀"与"主体在册"两段的**顺序对调**
/// ⇒ ① 红（`contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders` 同红）；
/// 把 `refused_digest` 改成返回**常量** ⇒ ③ 红而 ①② 仍绿——本轮实测后者**只**让本条红，
/// `contract.rs` 的三条 c23 用例**全绿**（它们只断言"同一次尝试同一指纹"，
/// 而常量指纹恰好满足这一条）。这就是"既有断言抓不住常量指纹"的实测证据。
/// 另一条变异（④ 流水不写 `refused`）⇒ 本条与 `f71` 同红。
#[test]
fn f72_the_two_notice_refusal_paths_do_not_impersonate_each_other() {
    let d = tmpdir("f72");
    let reserved = r#"{"type":"gate.rejected","subject":"world://job/9","payload":{}}"#;
    let ordinary = r#"{"type":"my.own.notice","subject":"world://job/1","payload":{}}"#;

    // ① 不在册 ＋ 保留前缀 ⇒ 报的是"保留前缀"，不是"不在册"
    let (c1, _o1, e1) = run(&d, &["append", "notice", reserved, "world://stranger"]);
    assert_eq!(c1, 2, "保留前缀通告必须被拒；stderr={e1}");
    assert!(
        e1.contains("NoticeNotAllowed") && !e1.contains("NoticeRejected"),
        "保留前缀先判：不在册主体提交保留前缀通告，拿到的必须是 `NoticeNotAllowed`；stderr={e1}"
    );

    // ② 不在册 ＋ 非保留前缀 ⇒ 报"不在册"
    let (c2, _o2, e2) = run(&d, &["append", "notice", ordinary, "world://stranger"]);
    assert_eq!(c2, 2, "{e2}");
    assert!(
        e2.contains("NoticeRejected") && !e2.contains("NoticeNotAllowed"),
        "非保留前缀才轮到在册检查；stderr={e2}"
    );

    // ③ 三次同类被拒：换 actor / 换信纸 / 原样再来一次
    let (c3, _o3, _e3) = run(&d, &["append", "notice", ordinary, "world://stranger2"]);
    assert_eq!(c3, 2, "换一个不在册主体同样被拒");
    let (c4, _o4, _e4) = run(
        &d,
        &[
            "append",
            "notice",
            r#"{"type":"my.own.other","subject":"world://job/2","payload":{}}"#,
            "world://stranger",
        ],
    );
    assert_eq!(c4, 2, "换一份信纸同样被拒");
    let (c5, _o5, _e5) = run(&d, &["append", "notice", ordinary, "world://stranger"]);
    assert_eq!(c5, 2, "同一次尝试再来一次同样被拒");

    // ── 两条路径各自留了**自己类型**的流水（互不冒充）──
    assert_eq!(
        kinds(&d, "gate.notice-not-allowed"),
        1,
        "保留前缀路径的流水"
    );
    assert_eq!(
        kinds(&d, "gate.notice-rejected"),
        4,
        "不在册路径的流水（四次尝试四条）"
    );

    let prints: Vec<String> = events(&d)
        .iter()
        .filter(|e| e["body"]["type"] == json!("gate.notice-rejected"))
        .map(|e| {
            e["body"]["payload"]["refused"]
                .as_str()
                .unwrap_or_default()
                .to_string()
        })
        .collect();
    assert_eq!(prints.len(), 4, "四次被拒各留一条流水：{prints:?}");
    assert_eq!(
        prints[0], prints[3],
        "同一次尝试（同 actor ＋ 同信纸）的指纹必须可复算"
    );
    assert_ne!(
        prints[0], prints[1],
        "换了 actor ⇒ 指纹必须变；否则指纹是个常量，等于没点名"
    );
    assert_ne!(
        prints[0], prints[2],
        "换了信纸 ⇒ 指纹必须变；否则指纹是个常量，等于没点名"
    );
}
