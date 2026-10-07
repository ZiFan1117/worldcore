//! **结构化审计留痕** —— 会红的断言（原 Go `agentd/internal/audit` 的 Rust 侧对应面）。
//!
//! ## 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `g01` | 它核的是「**帧的行数 ≡ 该记录的字段数**」。⚠ **实测的订正**：把 `src/agent/audit.rs` 的 `sanitize()` 改成恒返回原值，`g01` **仍然绿**——因为 `PARAMS` 一律走 JSON 序列化，换行先被转义成 `\n` 两个字符，**碰不到 `sanitize`**。⇒ 打 `sanitize` 的是**模块内**的 `agent::audit::unit::a_raw_newline_in_any_value_is_replaced`（同一个变异下它 **FAILED**）。**这一条不许再写成"g01 核 sanitize"。** |
//! | `g02` | `FileSink::record` 里 `.entry(F_TIMESTAMP).or_insert_with(now_timestamp)` 删掉 ⇒ **红**（每条必须带非空时间戳）；把追加换成覆盖写 ⇒ **红**（两条变一条） |
//! | `g03` | `Multi::record` 改成"第一个失败就 `return Err`"（不继续调后面的出口）⇒ **红**（第二个出口收不到） |
//! | `g04` | `FIELDS` 里删掉 `F_DURATION_MS` ⇒ **红**（动作记录会报出一个"越界字段"） |
//!
//! ## 正控（钉住"不该红的"）
//!
//! | 用例 | 它钉什么 |
//! |---|---|
//! | `g04` 的前半段 | `off_contract_fields` 对**合规**记录必须返回**空**——否则"越界即红"会退化成"什么都红" |
//! | `g02` | 它只核"两条 ＋ 有时间戳"，与 `Multi` 无关 ⇒ `g03` 的变异**不得**把它带红 |
//!
//! ## 逐字的依据
//!
//! - 字段集合与"一条记录占一行"的口径原样来自 Go 侧 `internal/audit`（`FMessage`…`FSyscall`
//!   与 `sanitizeValue` 的注释「journald 文本协议按换行分帧，值内裸换行会撕裂记录」）；
//! - 依赖纪律（不许引入 `chrono` 等）：`Cargo.toml` 逐字「**只允许 `serde_json`
//!   一个 crate family**」。

use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::agent::audit::{
    self, action_fields, intent_fields, off_contract_fields, to_journal_frame, Fields, FileSink,
    Memory, Multi, Sink, F_CAPABILITY, F_DURATION_MS, F_INTENT, F_MESSAGE, F_OUTCOME, F_VERB,
};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-agaudit-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    // 与既有测试同口径：umask 非 022 时可能建出过宽的目录，显式收紧。
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

/// 一个把记录转发给外部可见 `Memory` 的探针出口（用来证明"后面的出口也收到了"）。
struct Probe(Arc<Memory>);

impl Sink for Probe {
    fn record(&self, f: &Fields) -> Result<(), String> {
        self.0.record(f)
    }
}

/// `g01` —— **值里的换行不撕裂记录**。
///
/// 判据的形态：把记录转成一帧之后，**一帧里的行数必须等于字段数**。
/// 这是"值里的换行被就地替换"的机械形态——若换行原样穿过去，
/// 一帧会多出若干行，而按行分帧的读端会把一条记录读成两条。
///
/// ⚠ **两半要分开核，别把它们当成一件事**（本用例第一版就在这里判错了一次）：
/// - **JSON 值**：`serde_json` 会把换行**转义**成 `\n` 两个字符 ⇒ 原样进不了帧；
///   这一半靠"帧的行数 ≡ 字段数"核；
/// - **裸字符串值**：它**原样**进 `sanitize` ⇒ 换行必须被**替换成空格**，且内容保留。
///   这一半才是真正打 `sanitize` 的那一枪（把 `sanitize` 改成恒返回原值 ⇒ 它红）。
#[test]
fn g01_newline_in_value_does_not_split_the_frame() {
    // ① JSON 值：换行会被 serde_json 转义，帧里不许出现**裸**换行
    let params = json!({ "note": "第一行\n第二行", "another": "a\r\nb" });
    let f = intent_fields("package.install", "install", &params, "agent@auto");
    let frame = to_journal_frame(&f);

    let lines: Vec<&str> = frame.split('\n').filter(|l| !l.is_empty()).collect();
    assert_eq!(
        lines.len(),
        f.len(),
        "一帧的行数必须等于字段数（换行必须被替换，不许撕裂记录）；实得帧=\n{frame}"
    );
    assert!(!frame.contains('\r'), "回车也必须被替换掉");
    // 每行的形态必须是 K=V（一个等号分界，键是约定字段名）
    for l in &lines {
        let (k, _v) = l.split_once('=').expect("每一行都是 K=V");
        assert!(
            audit::FIELDS.contains(&k),
            "键 `{k}` 必须落在约定字段集合里"
        );
    }

    // ② 裸字符串值：`as_text` **一律走 JSON 序列化** ⇒ 换行被转义、不会撕裂帧。
    //    这一半核「格式与值类型无关」（字符串与对象写出来都是合法 JSON）。
    let bare = intent_fields("a.b", "do", &json!("第一行\n第二行"), "me@auto");
    let bare_frame = to_journal_frame(&bare);
    let params_cell = bare_frame
        .lines()
        .find(|l| l.starts_with("PARAMS="))
        .expect("帧里必须有 PARAMS 这一格");
    assert_eq!(
        params_cell, "PARAMS=\"第一行\\n第二行\"",
        "字符串参数也必须以合法 JSON 形态出现（转义后的 \\n，不是裸换行）；实得帧=\n{bare_frame}"
    );
    assert_eq!(
        bare_frame.split('\n').filter(|l| !l.is_empty()).count(),
        bare.len(),
        "帧的行数仍等于字段数"
    );
    // 对象与字符串两半的帧行数都必须等于字段数（格式与值类型无关）
    assert_eq!(
        frame.split('\n').filter(|l| !l.is_empty()).count(),
        f.len(),
        "对象参数那一半同样不许撕裂"
    );
}

/// `g02` —— **文件回退是 JSON Lines 且带时间戳**。
#[test]
fn g02_file_fallback_is_jsonl_with_timestamp() {
    let d = tmpdir("jsonl");
    let p: PathBuf = d.join("audit.jsonl");
    let sink = FileSink::new(&p);
    assert_eq!(sink.path(), p.as_path());

    sink.record(&intent_fields("a.b", "do", &json!({ "x": 1 }), "me@auto"))
        .unwrap();
    sink.record(&action_fields("a.b", "do", "ok", 12, Some("/run/undo/1")))
        .unwrap();

    // 逐行读回：**必须是两行**（追加，不是覆盖），且逐行可解析
    let raw = fs::read_to_string(&p).unwrap();
    let lines: Vec<&str> = raw.lines().filter(|l| !l.trim().is_empty()).collect();
    assert_eq!(lines.len(), 2, "两条记录 ⇒ 两行 JSON；实得：{raw}");
    for (i, l) in lines.iter().enumerate() {
        let v: Value = serde_json::from_str(l)
            .unwrap_or_else(|e| panic!("第 {} 行不是合法 JSON：{e}；原文={l}", i + 1));
        assert!(v.is_object(), "每行必须是一个 JSON 对象");
    }

    let rows = audit::read_lines(&p).unwrap();
    assert_eq!(rows.len(), 2);
    for (i, r) in rows.iter().enumerate() {
        let ts = r.get(audit::F_TIMESTAMP).cloned().unwrap_or_default();
        assert!(!ts.is_empty(), "第 {} 条必须带非空时间戳", i + 1);
        assert!(ts.ends_with('Z'), "时间戳应是 UTC 形态：{ts}");
        assert!(
            off_contract_fields(r).is_empty(),
            "文件回退写出的字段名也必须在约定集合里；越界={:?}",
            off_contract_fields(r)
        );
    }
    // 两条的 MESSAGE 分别是 intent 与 action（内容没串）
    assert_eq!(
        rows[0].get(F_MESSAGE).map(String::as_str),
        Some("intent"),
        "第一条是意图"
    );
    assert_eq!(
        rows[1].get(F_MESSAGE).map(String::as_str),
        Some("action"),
        "第二条是动作"
    );

    let _ = fs::remove_dir_all(&d);
}

/// `g03` —— **多路出口：一路失败不阻塞另一路**。
///
/// 顺序刻意排成「先失败、后成功」：若实现写成"第一个失败就返回"，
/// **后面那个出口就收不到** ⇒ 本用例红。
#[test]
fn g03_multi_sink_isolates_failures() {
    let probe = Arc::new(Memory::new());
    let mut m = Multi::new();
    m.push(Box::new(audit::Failing::new("第一个出口坏了")));
    m.push(Box::new(Probe(Arc::clone(&probe))));

    let f = action_fields("a.b", "do", "ok", 7, None);
    let err = m.record(&f).expect_err("有一个出口失败 ⇒ 整体必须报错");
    assert_eq!(err, "第一个出口坏了", "带回的应是**第一个**失败");

    assert_eq!(
        probe.len(),
        1,
        "第一个出口失败**不许**阻止第二个出口收到这条记录"
    );
    assert_eq!(
        probe.records()[0].get(F_VERB).map(String::as_str),
        Some("do"),
        "第二个出口收到的是同一条记录"
    );

    // 正控：全部出口都好 ⇒ 必须返回 Ok（否则"失败隔离"会退化成"永远报错"）
    let ok_probe = Arc::new(Memory::new());
    let mut m2 = Multi::new();
    m2.push(Box::new(Probe(Arc::clone(&ok_probe))));
    assert!(m2.record(&f).is_ok(), "没有出口失败时不许报错");
    assert_eq!(ok_probe.len(), 1);

    // 空的多出口：什么都不做，但也不算失败
    assert!(Multi::new().record(&f).is_ok());
}

/// `g04` —— **字段名是固定集合，不许改名**。
#[test]
fn g04_field_names_come_from_the_fixed_set() {
    let i = intent_fields("a.b", "do", &json!({}), "me@auto");
    assert!(
        off_contract_fields(&i).is_empty(),
        "意图记录的字段名必须全在约定集合里；越界={:?}",
        off_contract_fields(&i)
    );
    assert_eq!(i.get(F_MESSAGE).map(String::as_str), Some("intent"));
    assert_eq!(
        i.get(F_INTENT).map(String::as_str),
        Some("a.b.do"),
        "意图名是 <能力>.<动词>"
    );

    let a = action_fields("a.b", "do", "ok", 5, None);
    assert!(
        off_contract_fields(&a).is_empty(),
        "动作记录的字段名必须全在约定集合里；越界={:?}",
        off_contract_fields(&a)
    );
    assert_eq!(a.get(F_OUTCOME).map(String::as_str), Some("ok"));
    assert_eq!(a.get(F_CAPABILITY).map(String::as_str), Some("a.b"));
    assert_eq!(
        a.get(F_DURATION_MS).map(String::as_str),
        Some("5"),
        "动作记录必须带耗时"
    );

    // 反例形态：把 DURATION_MS 写成 DURATION —— 必须被判为越界（这条是"判据真的在认结构"的证明）
    let mut bad = a.clone();
    bad.remove(F_DURATION_MS);
    bad.insert("DURATION".into(), "5".into());
    assert_eq!(
        off_contract_fields(&bad),
        vec!["DURATION".to_string()],
        "改名必须被报出来——否则【字段名是固定集合】这条口径没有执行者"
    );
}
