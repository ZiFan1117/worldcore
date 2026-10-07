//! **「读法是叶子」的断言面**（书 §4.4；本 change `tasks.md` 第 11.2 条）。
//!
//! ## 条文与出处（逐字）
//!
//! 书 §4.4（`docs/理论/语义世界-理论书-第一版-合订.md:565`）：
//! 「不互相调用的意思是，没有一份要问另一份"你那里是什么"，也没有一份可以把自己的输出当作
//! 另一份的输入。它们都是账本的读法。**读法是叶子，只负责往外给。**」
//! 同节 `:577`：「**读法不持有状态。** 读法可以有自己的显示偏好，比如排序、折叠、配色，
//! 这些偏好不影响它摆出来的内容；读法一旦开始记自己那一份状态，它就有了自己的说法。」
//!
//! 本仓今天落成的读法就是两个出口（`WC-MODREG-001` §2 的 `M06`／`M07`，二者依赖列都只有 `M03`）：
//! 命令行 `project language`（结构化出口）与 `project visual`（渲染出口）。
//!
//! ## 三条验收各自变成什么（哪条会红）
//!
//! | 验收 | 断言在哪 | 它怎么变红 |
//! |---|---|---|
//! | 拔掉一份，另一份照常工作 | `p01`／`p02`：各自**只跑一份**，另一份在本用例里一次都没跑过 | 产出缺主体／头部对不上／另一份被夹带 ⇒ 红 |
//! | 各自的产出只依赖账本 | `p03`（同一账本两次**逐字节**相同、且一处文件都不留）＋ `p04`（账本多一条 ⇒ `last_seq`／`state` 指纹／正文随之变） | 缓存、常量、把状态藏在 cwd ⇒ 红 |
//! | 几份读法之间不互相调用 | `p05`（落后的那一份不影响另一份，落后只在头部暴露）＋ `p06`（两份出口互不夹带对方的形态，**带正控**） | 一份去渲染另一份 ⇒ 红 |
//!
//! **结构面**那条另有常驻守卫：`scripts/verify/module_graph.py` 的判据②（`A-4`：
//! `deps == import` 且无环）——`M06` 与 `M07` 之间一旦出现 `use` 边即判红。
//!
//! ## "另一份不在场"是**可观测**的，不是注释里的一句话
//!
//! `p01`／`p02` 在跑之前与跑之后各取一次**账本目录逐件快照**（文件名 ＋ 字节）：
//! 那份产出**不可能**来自另一份读法的输出文件——目录里根本没有这样的文件，
//! 跑完也没有多出任何一件。两条断言（快照相同 ＋ 正文与**独立折叠**逐项相符）
//! 合起来才是"另一份缺席而这一份照常工作"。
//!
//! ⚠️ 边界（如实写）：`Ledger::open_mode` 在**账本文件不存在**时，连只读口径也会**创建**它
//! （`src/ledger/mod.rs:237-245`）⇒ 本文件的夹具一律**先 `append` 把账本建出来**；
//! 这里断言的是「不写**已有**账本、不产**新**文件」，不是"任何情况下都不碰文件系统"。

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::{json, Value};
use world_core::gui_projection::{assert_same_source, language, parse_header, visual};
use world_core::ontology_instance::readmodel::State;
use world_core::World;

/// 一条 `(主体, 字段路径, 值)`。
type Triple = (String, String, Value);

// ───────────────────────── 夹具 ─────────────────────────

fn manifest() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-leaf-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    d
}

/// 一次命令行调用的原始结果（stdout 保**字节**，好做"逐字节"比较）。
struct Out {
    code: i32,
    stdout: Vec<u8>,
    stderr: String,
}

impl Out {
    fn text(&self) -> String {
        String::from_utf8_lossy(&self.stdout).to_string()
    }

    /// rc 必须为 0（**它只是最低要求**，不是断言的全部）。
    fn ok(&self, what: &str) {
        assert_eq!(self.code, 0, "{what} 必须成功；stderr={}", self.stderr);
    }
}

fn run(args: &[&str]) -> Out {
    run_in(None, args)
}

/// 跑一次 CLI；`dir` 给出时另设**工作目录**（用来抓"把状态藏在 cwd"的形态）。
fn run_in(dir: Option<&Path>, args: &[&str]) -> Out {
    let mut c = Command::new(env!("CARGO_BIN_EXE_world-core"));
    c.args(args);
    if let Some(d) = dir {
        c.current_dir(d);
    }
    let o = c.output().expect("无法启动被测二进制");
    Out {
        code: o.status.code().unwrap_or(-1),
        stdout: o.stdout,
        stderr: String::from_utf8_lossy(&o.stderr).to_string(),
    }
}

fn args_for(lp: &Path, tail: &[&str]) -> Vec<String> {
    let mut v = vec![
        "--ontology".to_string(),
        manifest()
            .join("src/ontology_definition/ontology.json")
            .display()
            .to_string(),
        "--policy".to_string(),
        manifest()
            .join("src/gate/policy.json")
            .display()
            .to_string(),
        "--ledger".to_string(),
        lp.display().to_string(),
    ];
    v.extend(tail.iter().map(|s| s.to_string()));
    v
}

fn as_refs(v: &[String]) -> Vec<&str> {
    v.iter().map(String::as_str).collect()
}

/// 目录的**逐件快照**（文件名 ＋ 全部字节，按名排序）。
///
/// 用来把「读法是叶子，只负责往外给」钉成会红的断言：读法跑完，账本目录必须**一字未动、一件未增**。
fn snapshot(dir: &Path) -> Vec<(String, Vec<u8>)> {
    let mut v: Vec<(String, Vec<u8>)> = fs::read_dir(dir)
        .expect("目录必须可读")
        .map(|e| e.expect("目录项"))
        .filter(|e| e.file_type().map(|t| t.is_file()).unwrap_or(false))
        .map(|e| {
            (
                e.file_name().to_string_lossy().to_string(),
                fs::read(e.path()).expect("读文件"),
            )
        })
        .collect();
    v.sort();
    v
}

/// 「这一处一个字都不许动」：先比**件名**（失败时判词短、一眼看得出多了/少了哪一件），
/// 再逐件比**字节**（既有件被改写也抓得到，判词只印出问题的那一件）。
fn assert_dir_unchanged(before: &[(String, Vec<u8>)], after: &[(String, Vec<u8>)], what: &str) {
    let names = |v: &[(String, Vec<u8>)]| -> Vec<String> {
        v.iter().map(|(n, _)| n.clone()).collect::<Vec<_>>()
    };
    assert_eq!(
        names(after),
        names(before),
        "{what}：件名不许增、不许减、不许改名"
    );
    for ((n, x), (_, y)) in after.iter().zip(before.iter()) {
        assert_eq!(x, y, "{what}：`{n}` 的字节必须一字未动");
    }
}

fn tri(subject: &str, path: &str, value: Value) -> Triple {
    (subject.to_string(), path.to_string(), value)
}

/// 排序键（不用 `Value: Ord`，避免依赖 `serde_json` 的排序口径）。
fn sorted(mut v: Vec<Triple>) -> Vec<Triple> {
    v.sort_by_key(|(s, p, val)| format!("{s}\u{1}{p}\u{1}{val}"));
    v
}

/// 经**唯一写入口**往账本写一条 `change`（主体与字段都在出厂本体里声明过）。
fn append_one(lp: &Path, subject: &str, path: &str, after: Value) {
    let body = json!({
        "subject": subject,
        "path": path,
        "before": Value::Null,
        "after": after,
    })
    .to_string();
    let a = args_for(lp, &["append", "change", &body]);
    let o = run(&as_refs(&a));
    assert_eq!(
        o.code, 0,
        "夹具：append 必须成功（body={body}）；stderr={}",
        o.stderr
    );
}

/// 夹具：三条事件（三个主体、两个字段），返回**我们真正写进账本**的三元组。
fn seed_ledger(lp: &Path) -> Vec<Triple> {
    let rows: [(&str, &str, Value); 3] = [
        ("world://notice/n-1", "muted", json!(true)),
        ("world://notice/n-2", "muted", json!(false)),
        ("world://job/j-1", "status", json!("doing")),
    ];
    let mut want = Vec::new();
    for (subject, path, after) in rows {
        append_one(lp, subject, path, after.clone());
        want.push(tri(subject, path, after));
    }
    want
}

/// **独立折叠**（库路径，不经任何投影）：`(世界版本, 词表身份, 状态)`。
///
/// 这是"产出只依赖账本"的对照面：读法的头部四项与正文必须与它逐项相符。
fn fold_state(lp: &Path) -> (u64, String, State) {
    let w = World::open_readonly(
        &manifest().join("src/ontology_definition/ontology.json"),
        lp,
        &manifest().join("src/gate/policy.json"),
    )
    .expect("库路径：只读打开世界");
    let world = w.ontology().world();
    let vocab = w.ontology().vocab_hash().to_string();
    let st = w.read_model().expect("库路径：从账本折叠");
    (world, vocab, st)
}

fn state_triples(st: &State) -> Vec<Triple> {
    st.entries().map(|(s, p, v)| tri(s, p, v.clone())).collect()
}

// ───────────────────────── 断言 ─────────────────────────

/// **p01**：拔掉视觉投影 —— 语言投影**一个人**也必须给出**正确且完整**的产出。
///
/// 反假：不断言 rc，而是断言**内容**——
/// ① 头部四项与**独立折叠**逐项相符；② 正文行数齐（1 头部 ＋ 3 主体）；
/// ③ 三元组与我们**真正写进账本**的那三条逐项相符。
#[test]
fn p01_language_alone_is_complete_and_the_other_reading_never_runs() {
    let d = tmpdir("p01");
    let lp = d.join("ledger.jsonl");
    let want = sorted(seed_ledger(&lp));
    let before = snapshot(&d);

    // 本用例里**唯一**一次投影调用：只有语言投影。视觉投影一次都没跑过。
    let o = run(&as_refs(&args_for(&lp, &["project", "language"])));
    o.ok("只跑语言投影");
    let text = o.text();

    // ① 头部四项
    let h = parse_header(&text).expect("首行必须是同源头");
    assert_eq!(h.projection, "language", "这一份必须自报是语言投影：{text}");
    assert!(
        h.vocab.starts_with("fnv1a64:"),
        "词表身份必须是内容寻址指纹：{}",
        h.vocab
    );
    assert!(
        h.state.starts_with("fnv1a64:"),
        "状态指纹必须是内容寻址指纹：{}",
        h.state
    );
    let (fw, fv, st) = fold_state(&lp);
    assert_eq!(h.world, fw, "同源头的 world 必须与本体一致");
    assert_eq!(h.vocab, fv, "同源头的 vocab 必须与本体算出的词表身份一致");
    assert_eq!(h.last_seq, 3, "三条事件 ⇒ 必须算到第 3 条");
    assert_eq!(h.last_seq, st.last_seq(), "必须与独立折叠算到的位置一致");
    assert_eq!(h.state, st.digest(), "状态指纹必须与独立折叠一致");

    // ②③ 正文**齐全**且逐项相符
    assert_eq!(
        text.lines().count(),
        1 + want.len(),
        "正文行数必须齐：\n{text}"
    );
    let got = sorted(language::parse(&text).expect("语言投影必须能被机器解析回三元组"));
    assert_eq!(got, want, "正文必须与真正写进账本的那三条逐项相符");
    assert_eq!(
        got,
        sorted(state_triples(&st)),
        "正文必须与独立折叠的结果逐项相符"
    );

    // 另一份**不在场**：跑完与跑前逐件相同（没有多出任何"另一份的产出/状态"文件）
    assert_dir_unchanged(
        &before,
        &snapshot(&d),
        "读法只许往外给：账本目录一字未动、一件未增",
    );
}

/// **p02**：拔掉语言投影 —— 视觉投影**一个人**也必须给出**正确且完整**的产出。
///
/// 与 `p01` 对称；另外钉住"给人的那一份也要能被机器核对"：统计行必须与独立折叠一致，
/// 取值行必须按可审计排版（6 空格缩进 ＋ `路径 = 值`）给出。
#[test]
fn p02_visual_alone_is_complete_and_the_other_reading_never_runs() {
    let d = tmpdir("p02");
    let lp = d.join("ledger.jsonl");
    let want = sorted(seed_ledger(&lp));
    let before = snapshot(&d);

    // 本用例里**唯一**一次投影调用：只有视觉投影。语言投影一次都没跑过。
    let o = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    o.ok("只跑视觉投影");
    let text = o.text();

    let h = parse_header(&text).expect("首行必须是同源头");
    assert_eq!(h.projection, "visual", "这一份必须自报是视觉投影：{text}");
    assert!(h.state.starts_with("fnv1a64:"));
    let (fw, fv, st) = fold_state(&lp);
    assert_eq!(h.world, fw);
    assert_eq!(h.vocab, fv);
    assert_eq!(h.last_seq, 3, "三条事件 ⇒ 必须算到第 3 条");
    assert_eq!(h.last_seq, st.last_seq());
    assert_eq!(h.state, st.digest());

    assert!(text.contains("世界状态（视觉投影）"), "缺标题：\n{text}");
    let stat = format!(
        "  已折叠 {} 条事件（最近序号 {}）｜动作 {} 条｜通告 {} 条",
        st.seen(),
        st.last_seq(),
        st.acts(),
        st.notices()
    );
    assert!(
        text.contains(&stat),
        "统计行必须与独立折叠一致（找 `{stat}`）：\n{text}"
    );
    assert!(
        text.lines().any(|l| l.starts_with("      muted = true")),
        "取值行必须按可审计排版给出（6 空格缩进 ＋ `路径 = 值`）：\n{text}"
    );

    let got = sorted(visual::parse(&text).expect("视觉投影必须能被审计脚本解析回三元组"));
    assert_eq!(got, want, "正文必须与真正写进账本的那三条逐项相符");
    assert_eq!(
        got,
        sorted(state_triples(&st)),
        "正文必须与独立折叠的结果逐项相符"
    );
    assert_eq!(got.len(), 3, "主体与字段一个都不许少：\n{text}");

    assert_dir_unchanged(
        &before,
        &snapshot(&d),
        "读法只许往外给：账本目录一字未动、一件未增",
    );
}

/// **p03**：同一账本 ⇒ 产出**逐字节**相同（"读法不持有状态"的可核形态）。
///
/// 两次是**两个进程**，第二次还换一个**空的工作目录**跑：若某一份把自己的状态
/// 藏在 cwd，这里立刻露出来（字节不同、或那个目录里多出文件）。
#[test]
fn p03_same_ledger_same_bytes_twice_and_no_state_kept_anywhere() {
    let d = tmpdir("p03");
    let lp = d.join("ledger.jsonl");
    seed_ledger(&lp);
    let before = snapshot(&d);

    for which in ["language", "visual"] {
        let a = run(&as_refs(&args_for(&lp, &["project", which])));
        a.ok(&format!("第一次跑 `project {which}`"));
        let ha = parse_header(&a.text()).expect("首行必须是同源头");
        assert_eq!(ha.projection, which);
        assert_eq!(ha.last_seq, 3, "两次都必须真的读到账本的三条事件");
        assert!(
            !a.stdout.is_empty(),
            "第一次必须有产出（否则下面的『相同』是空话）"
        );

        let cwd2 = tmpdir(&format!("p03-cwd-{which}"));
        let b = run_in(Some(&cwd2), &as_refs(&args_for(&lp, &["project", which])));
        b.ok(&format!("第二次跑 `project {which}`（换工作目录）"));
        assert_eq!(
            b.stdout, a.stdout,
            "同一账本 ⇒ 两次必须**逐字节**相同（读法不持有状态）"
        );
        assert_eq!(
            snapshot(&cwd2).len(),
            0,
            "读法不许在自己脚下留下状态：`project {which}`"
        );
    }

    assert_dir_unchanged(
        &before,
        &snapshot(&d),
        "跑过两份读法之后，账本目录必须一字未变",
    );
}

/// **p04**：账本变了 ⇒ **各自的**产出随之变（把"缓存／常量"钉死）。
///
/// 反假：不断言"两次输出不同"就完事（时间戳也能让两次不同），而是断言
/// `last_seq` 恰好 ＋1、状态指纹与**独立折叠**一致、新那一条真的出现在正文里——
/// 两份读法各自独立地做到这一点。
#[test]
fn p04_ledger_grows_so_does_each_reading() {
    let d = tmpdir("p04");
    let lp = d.join("ledger.jsonl");
    seed_ledger(&lp);

    let l1 = run(&as_refs(&args_for(&lp, &["project", "language"])));
    l1.ok("语言投影（账本 3 条）");
    let v1 = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    v1.ok("视觉投影（账本 3 条）");
    let h1 = parse_header(&l1.text()).unwrap();
    let g1 = parse_header(&v1.text()).unwrap();

    append_one(&lp, "world://job/j-2", "status", json!("todo"));

    let l2 = run(&as_refs(&args_for(&lp, &["project", "language"])));
    l2.ok("语言投影（账本 4 条）");
    let v2 = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    v2.ok("视觉投影（账本 4 条）");
    let h2 = parse_header(&l2.text()).unwrap();
    let g2 = parse_header(&v2.text()).unwrap();

    let (_, _, st2) = fold_state(&lp);
    assert_eq!(st2.last_seq(), 4, "夹具：独立折叠也必须看到 4 条");

    // ★ 语言投影随账本变
    assert_eq!(
        h2.last_seq,
        h1.last_seq + 1,
        "账本多一条 ⇒ last_seq 必须 ＋1"
    );
    assert_ne!(
        h2.state, h1.state,
        "状态指纹必须随账本变（不变 ⇒ 它是缓存或常量）"
    );
    assert_eq!(h2.last_seq, st2.last_seq());
    assert_eq!(h2.state, st2.digest(), "必须与独立折叠的状态指纹一致");
    assert_ne!(l2.stdout, l1.stdout, "产出必须随账本变");
    assert!(
        sorted(language::parse(&l2.text()).unwrap())
            .iter()
            .any(|(s, p, val)| s == "world://job/j-2" && p == "status" && val == &json!("todo")),
        "新那一条必须出现在语言投影的正文里：\n{}",
        l2.text()
    );

    // ★ 视觉投影**独立地**同样随账本变（不是靠语言投影告诉它）
    assert_eq!(
        g2.last_seq,
        g1.last_seq + 1,
        "账本多一条 ⇒ last_seq 必须 ＋1"
    );
    assert_ne!(g2.state, g1.state);
    assert_ne!(v2.stdout, v1.stdout, "产出必须随账本变");
    assert!(
        v2.text().contains("world://job/j-2"),
        "新主体必须出现在视觉投影里：\n{}",
        v2.text()
    );

    // 两份读法说的是同一本账（各自的头部四项不比任何一方解释自己）
    assert_eq!(h2.last_seq, g2.last_seq);
    assert_eq!(h2.state, g2.state);
}

/// **p05**：让一份读法**落后若干事件** —— 另一份照常工作，落后只在**头部**暴露。
///
/// 做法：语言投影先跑一次（它只见过 3 条），账本再往前走一条，
/// 此后**只**跑视觉投影。两份产出各自都是"它读到的那本账"的完整正确产出；
/// 差别只体现在同源头上——**靠结构比对，不靠任何一方解释自己**。
#[test]
fn p05_a_lagging_reading_neither_breaks_nor_bleeds_into_the_other() {
    let d = tmpdir("p05");
    let lp = d.join("ledger.jsonl");
    let want3 = sorted(seed_ledger(&lp));

    let lag = run(&as_refs(&args_for(&lp, &["project", "language"])));
    lag.ok("语言投影（落后的一份：账本 3 条）");

    append_one(&lp, "world://job/j-2", "status", json!("todo"));
    let lead = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    lead.ok("视觉投影（账本 4 条）");

    // ① 落后的那一份**不受影响**：它当时的产出就是那本账的完整正确产出
    let hl = parse_header(&lag.text()).unwrap();
    assert_eq!(hl.last_seq, 3);
    assert_eq!(
        sorted(language::parse(&lag.text()).unwrap()),
        want3,
        "落后的那一份的正文仍是完整的（不许因为对方往前走而少给东西）"
    );

    // ② 领先的那一份**照常工作**：完整正确，且多出那一条
    let hv = parse_header(&lead.text()).unwrap();
    assert_eq!(hv.last_seq, 4);
    let got = sorted(visual::parse(&lead.text()).unwrap());
    assert_eq!(
        got.len(),
        4,
        "视觉投影必须给出 4 条（不多不少）：\n{}",
        lead.text()
    );
    assert!(got
        .iter()
        .any(|(s, p, _)| s == "world://job/j-2" && p == "status"));

    // ③ 落后**暴露在头部**：同一账本、两方各算各的 ⇒ 一比就知道谁落后
    let e = assert_same_source(&lag.text(), &lead.text()).expect_err("一方落后一条 ⇒ 必须报不同源");
    assert!(e.contains("状态不同"), "实得：{e}");

    // 正控：两边读**同一本账**时，同一个判据必须判同源（证明它不是恒 Err）
    let again = run(&as_refs(&args_for(&lp, &["project", "language"])));
    again.ok("语言投影（补跑：账本 4 条）");
    assert!(
        assert_same_source(&again.text(), &lead.text()).is_ok(),
        "同源时不许误报"
    );
}

/// **p06**：两份出口**互不夹带对方的形态**（没有一份把另一份的输出当作自己的输入）。
///
/// 每一条"没有"都配一条**正控**：那些形态标记在对方那里**确实**存在——
/// 否则"语言投影里没有视觉投影的排版"是空话（它本来就不印那个词）。
#[test]
fn p06_the_two_exits_do_not_carry_each_others_shapes() {
    let d = tmpdir("p06");
    let lp = d.join("ledger.jsonl");
    seed_ledger(&lp);

    let l = run(&as_refs(&args_for(&lp, &["project", "language"])));
    l.ok("语言投影");
    let v = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    v.ok("视觉投影");
    let (lt, vt) = (l.text(), v.text());

    // 视觉投影的形态标记：标题、分隔线（**取自它自己的输出**）、取值行
    let rule = vt
        .lines()
        .find(|x| x.starts_with("──"))
        .expect("正控：视觉投影必须有分隔线")
        .to_string();
    for m in ["世界状态（视觉投影）", rule.as_str(), "      muted = true"] {
        assert!(vt.contains(m), "正控：视觉投影里必须真有 `{m}`：\n{vt}");
        assert!(
            !lt.contains(m),
            "语言投影里混进了视觉投影的形态 `{m}`：\n{lt}"
        );
    }

    // 反过来：语言投影的逐行 JSON 形态
    let json_lines = |t: &str| t.lines().filter(|x| x.starts_with("{\"fields\":")).count();
    assert!(
        json_lines(&lt) >= 3,
        "正控：语言投影必须真有逐行 JSON 形态：\n{lt}"
    );
    assert_eq!(
        json_lines(&vt),
        0,
        "视觉投影里不许出现语言投影的 JSON 行：\n{vt}"
    );
}
