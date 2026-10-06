//! **写侧适配**（书 §4.5）—— 会红的断言。
//!
//! 这一格原来红在哪：书 §4.5 在规格与源码里**只有一半落点**——
//! 设备的**动作**那一半（`act`：`capd`／`providers`／`run`）早就在；
//! 旧系统的**状态**那一半（`change`：前值、名字对齐、写侧自查边界）**一处都没有**。
//! 本文件把那三条变成可判的断言，判据出处逐条写在各用例的文档里。
//!
//! 三条（`openspec/changes/cover-unimplemented-capabilities/tasks.md` 11.1）：
//! ① 只写不裁决 ② 前值必须带上、翻不出来就报错、不许猜 ③ 以被管者身份运行、对账本与规则没有写权限。
//!
//! # 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `w01` | `src/carrier/writeside.rs::submit_change_body` 里加一句「先本地判一下准不准」（判完就返回、不提交）⇒ 假内核一个连接都收不到 ⇒ 红；提交时给自己塞身份（`Some(actor)`）⇒ 「信封只许有 `kind`/`body`」那条红 |
//! | `w02` | `src/carrier/writeside.rs` 把内核的 `Refused` 吞掉改报 `Admitted` ⇒ 判词那条红；`src/lib.rs` 的 `gate.write-rejected` 流水不写 ⇒ 账本 0 行 ⇒ 红 |
//! | `w03` | 正控（不该红的）：把 `before` 从信纸里删掉 ⇒ 本体必拒 ⇒ 红 |
//! | `w04` | `src/carrier/translate.rs` 在缺前值时改用 `Value::Null` 顶上（"猜一个空值"）⇒ 世界收下 ⇒ 账本 0→1 ⇒ 红 |
//! | `w05` | 同上：字段名翻不出来时退回"取一个相近的已声明字段"⇒ 世界收下 ⇒ 账本 0→1 ⇒ 红 |
//! | `w06` | 同上，改在**假内核**上看：猜出来的名字一旦交出去，`w06` 立刻红 |
//! | `w07` | `src/carrier/boundary.rs` 删掉 `mode & 0o022` 那一判 ⇒ 0666 那条红；删掉属主那一判 ⇒ 改属主那条红 |
//!
//! ⚠️ 本文件的判据全部落在 **Unix 权限位与 Unix 套接字**上。本项目构建与运行都在
//! Linux（`src/gate/guard.rs:35` 逐字「本项目构建与运行都在 Linux VM 内」），CI 也是
//! `ubuntu-latest`（`.github/workflows/world-core-gate.yml:136`）⇒ 本文件按 `cfg(unix)` 整文件门控。
//! 这不是"静默跳过"：非 Unix 上这些能力**根本不存在**（`src/carrier/kernel.rs:166-175`
//! 逐字「通道只在 Unix 上可用（v1 局限），**不假装可用**」），在那里判"通过"才是假证。
#![cfg(unix)]

use serde_json::{json, Value};
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::thread::JoinHandle;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use world_core::carrier::kernel::KernelClient;
use world_core::carrier::translate::{Declared, ExternalChange};
use world_core::carrier::{boundary, recover, writeside};
use world_core::common::error::code_of;
use world_core::ontology_definition::Ontology;

// ────────────────────────── 夹具 ──────────────────────────

/// 一次性目录（0700：guard 要求法律／真相所在目录不得对 group/other 可写）。
fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-writeside-{tag}-{n}"));
    let _ = fs::remove_dir_all(&d);
    fs::create_dir_all(&d).unwrap();
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    d
}

fn manifest() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// 本进程 uid（不引 libc：读 `/proc/self/status`，与 `tests/cli.rs:23-37` 同法）。
fn this_uid() -> u32 {
    let s = fs::read_to_string("/proc/self/status").unwrap_or_default();
    for line in s.lines() {
        if let Some(rest) = line.strip_prefix("Uid:") {
            if let Some(first) = rest.split_whitespace().next() {
                return first.parse().unwrap_or(0);
            }
        }
    }
    0
}

/// 一次性世界：本体与策略**复制进沙箱**（不碰仓里的出厂件），账本路径一并给出。
fn world_files(d: &Path) -> (PathBuf, PathBuf, PathBuf) {
    let ledger = d.join("ledger.jsonl");
    let onto = d.join("src/ontology_definition/ontology.json");
    let pol = d.join("src/gate/policy.json");
    fs::copy(
        manifest().join("src/ontology_definition/ontology.json"),
        &onto,
    )
    .unwrap();
    fs::copy(manifest().join("src/gate/policy.json"), &pol).unwrap();
    (ledger, onto, pol)
}

/// 一个**真内核**进程（`channel serve <socket> <n>`：一次连接一条请求；`n` 必须 ≥ 1）。
struct Kernel {
    child: Child,
    sock: PathBuf,
    log: PathBuf,
}

fn start_kernel(d: &Path, ledger: &Path, onto: &Path, pol: &Path, actor: &str, n: usize) -> Kernel {
    // 套接字放在**沙箱的子目录**里：`bus::bind` 会走 guard 的静态墙，
    // 而那条墙会**连它所在目录的上一级一起判**（`src/gate/guard.rs` 的 `assert_not_other_writable`）。
    // /tmp 是 1777 ⇒ 套接字若直接放在沙箱根下，上一级就是 /tmp ⇒ 必被拒（那是**墙在正常工作**）。
    // 子目录 `run/`（0755，无 go-w）＋ 沙箱（0700，无 go-w）⇒ 两级都成立。
    let run = d.join("run");
    fs::create_dir_all(&run).unwrap();
    let sock = run.join("kernel.sock");
    let chan = d.join("channel.json");
    fs::write(
        &chan,
        json!({"channel":1,
               "listeners":[{"socket":sock.display().to_string(),
                             "actor":actor,
                             "uid":this_uid()}]})
        .to_string(),
    )
    .unwrap();
    // ★ T1／AC-1：受理路径按**法律**（`--policy` 的 `listeners`）判"渲染物每一条在不在册"。
    //   夹具的口是**临时路径** ⇒ 夹具必须把它写进**自己的法律**里（否则世界**正确地**拒启）。
    //   ⚠ 这不是"把判据改松"：**判据的会红条件一字未动**；变的是**夹具的法律**，不是判据。
    //   用 append 而非覆盖：`start_kernel` 可能在同一个沙箱里被调用多次。
    let mut polv: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(pol).unwrap()).unwrap();
    let mut decl = polv["listeners"].as_array().cloned().unwrap_or_default();
    decl.push(json!({"socket":sock.display().to_string(),
                     "actor":actor,
                     "owner":"fixture"}));
    polv["listeners"] = serde_json::Value::Array(decl);
    fs::write(pol, polv.to_string()).unwrap();
    let log = d.join("kernel.log");
    let out = fs::File::create(&log).unwrap();
    let child = Command::new(env!("CARGO_BIN_EXE_world-core"))
        .arg("--ontology")
        .arg(onto)
        .arg("--ledger")
        .arg(ledger)
        .arg("--policy")
        .arg(pol)
        .arg("--channel")
        .arg(&chan)
        .arg("channel")
        .arg("serve")
        .arg(&sock)
        .arg(n.to_string())
        .stdin(Stdio::null())
        .stdout(Stdio::from(out.try_clone().unwrap()))
        .stderr(Stdio::from(out))
        .spawn()
        .expect("起不了真内核进程");

    // 就绪判据两条都要：① 套接字出现（`bus::bind` 在 `World::open` **之前**）；
    // ② 账本出现（`World::open` 在 `serve_n` 之前 ⇒ 账本在了才谈得上"会话已开、可以落笔"）。
    // 少了 ②，后面"账本 0 行"的断言会撞上"文件还没建"的竞态（那是夹具的错，不是被测对象的错）。
    let deadline = Instant::now() + Duration::from_secs(20);
    while !(sock.exists() && ledger.exists()) {
        if Instant::now() > deadline {
            panic!(
                "20 秒内没等到内核就绪（套接字 {} 存在={}；账本 {} 存在={}）；内核日志：\n{}",
                sock.display(),
                sock.exists(),
                ledger.display(),
                ledger.exists(),
                fs::read_to_string(&log).unwrap_or_default()
            );
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    Kernel { child, sock, log }
}

impl Kernel {
    /// 收摊：等它自己收满连接退出；超时就杀掉（**并把日志带回来**，便于判断是"没连上"还是"真出错"）。
    fn finish(mut self) -> String {
        let deadline = Instant::now() + Duration::from_secs(20);
        loop {
            match self.child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) => {
                    if Instant::now() > deadline {
                        let _ = self.child.kill();
                        let _ = self.child.wait();
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(50));
                }
                Err(_) => break,
            }
        }
        fs::read_to_string(&self.log).unwrap_or_default()
    }
}

/// 内核进程的日志：它**会**打印一行抬头，**也会**把被拒的请求打成 `[FAIL] …`
/// （门禁拒绝走的就是这条路，见 `src/main.rs` 的 `channel serve`：
/// `World` 拒一条请求即 `eprintln!("[FAIL] {e}")`）——**那不是夹具坏了**。
/// 夹具坏了只有一种形态：panic。
fn assert_kernel_did_not_panic(log: &str) {
    assert!(!log.contains("panicked"), "内核进程崩了：\n{log}");
}

/// 一个**假内核**：收一条连接、把原始请求行原样交回、回一行固定应答；
/// 20 秒内没有任何连接 ⇒ 交回 `None`（**"写侧根本没提交"这件事必须可观测**）。
fn fake_kernel(sock: PathBuf, reply: String) -> JoinHandle<Option<String>> {
    let listener = UnixListener::bind(&sock).unwrap();
    listener.set_nonblocking(true).unwrap();
    std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(20);
        loop {
            match listener.accept() {
                Ok((stream, _)) => {
                    let mut reader = BufReader::new(stream.try_clone().unwrap());
                    let mut line = String::new();
                    reader.read_line(&mut line).unwrap();
                    let mut w = stream;
                    w.write_all(reply.as_bytes()).unwrap();
                    w.write_all(b"\n").unwrap();
                    w.flush().unwrap();
                    return Some(line);
                }
                Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    if Instant::now() > deadline {
                        return None;
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }
                Err(e) => panic!("假内核 accept 失败：{e}"),
            }
        }
    })
}

/// 写侧要的那**一条**世界侧知识：由**真正的本体**回答（不另抄一份字段表）。
///
/// ⚠️ 生产装配该由 `impl Declared for Ontology` 提供（一行，落在 M04 的装配点
/// `src/lib.rs`——**本工区的文件面之外**，已如实登记为待补）；测试里直接拿本体当实现。
struct Book(Ontology);

impl Declared for Book {
    fn is_declared(&self, subject: &str, path: &str) -> bool {
        match Ontology::entity_of(subject) {
            Some(entity) => self
                .0
                .declared_fields(entity)
                .map(|f| f.contains_key(path))
                .unwrap_or(false),
            // 裸主体（`world://<名字>`）：它不是"某个对象"，写侧判**翻不出来**
            // （书 §4.5 要的是"某个对象的某个字段"）。这与本体侧那条**已登记的缺口**
            // （`src/ontology_definition/mod.rs` 的 `check_concepts`：裸主体今天仍可落账）不冲突——
            // 写侧不据此放宽。
            None => false,
        }
    }
}

fn book() -> Book {
    Book(Ontology::load(&manifest().join("src/ontology_definition/ontology.json")).unwrap())
}

fn book_at(onto: &Path) -> Book {
    Book(Ontology::load(onto).unwrap())
}

fn ledger_lines(path: &Path) -> Vec<Value> {
    recover::read_ledger_readonly(path).unwrap()
}

/// 一件**合规**的外部变化（字段 `muted` 在 `concepts.notice.fields` 里声明过）。
fn a_declared_change() -> ExternalChange {
    ExternalChange::new(
        "old-system:state.tsv:12",
        "world://notice/1",
        "muted",
        Some(json!(false)),
        json!(true),
    )
}

/// 一件**近似但没对齐**的外部变化：外部那台机器叫 `mute`，世界里声明的是 `muted`。
fn a_misnamed_change() -> ExternalChange {
    ExternalChange::new(
        "old-system:state.tsv:14",
        "world://notice/1",
        "mute",
        Some(json!(false)),
        json!(true),
    )
}

// ────────────────────────── ① 只写不裁决 ──────────────────────────

/// **w01**：写侧**原样提交**、**不自己裁决**，判词是内核的。
///
/// 判据出处：书 §4.5 `:585` 逐字「它们与世界要的形式之间隔着一只手，这只手在写侧，
/// 它的纪律只有一条：只写，不裁决。准不准做，一律问 4.2 那道闸。」；
/// `:601` 逐字「它要写世界，只能经通道提交请求，走的是和别的任何主体完全相同的那条路」。
///
/// 与既有落点的分工：`tools/carrier_acceptance.sh` 的 C-04／C-04b 在**真实二进制**上
/// 断言"门禁不放行 ⇒ 一次都没动 ＋ 留痕"；本条补的是**写侧交出去的那一行本身**——
/// 字段一个不差、信封里**没有身份**、判词逐字来自内核。
#[test]
fn w01_the_write_side_submits_verbatim_and_never_adjudicates() {
    let d = tmpdir("w01");
    let sock = d.join("fake.sock");
    let h = fake_kernel(
        sock.clone(),
        r#"{"ok":false,"error":"ext.world.Gate.WriteRejected: 门禁拒绝写入：主体 world://agent/1 无权写 world://notice/1"}"#
            .to_string(),
    );

    let client = KernelClient::new(&sock);
    let got = writeside::submit_external_change(&client, &a_declared_change(), &book()).unwrap();

    // ① 判词是**内核**的：写侧只转述，不重判
    assert!(!got.admitted(), "内核说拒，写侧不许说自己准了：{got:?}");
    assert_eq!(
        code_of(got.verdict().unwrap()),
        Some("ext.world.Gate.WriteRejected"),
        "判词必须逐字来自内核（带内核的错误码）：{got:?}"
    );

    // ② 写侧到底交出去了什么：**原样**、**不带身份**
    let line = h
        .join()
        .unwrap()
        .expect("写侧必须真的把这条变化交给内核——本地自己裁决就等于它自己当了裁决者");
    let req: Value = serde_json::from_str(line.trim()).unwrap();
    let keys: Vec<String> = req.as_object().unwrap().keys().cloned().collect();
    assert_eq!(
        keys,
        vec!["body".to_string(), "kind".to_string()],
        "信封里只许有 kind 与 body —— **不许自称身份**（身份由内核按套接字给出）：{req}"
    );
    assert_eq!(req["kind"], "change");
    assert_eq!(
        req["body"],
        json!({"subject":"world://notice/1","path":"muted","before":false,"after":true}),
        "提交的信纸必须与翻出来的**逐字段相同**（原样：不多一字、不少一字、不改一个值）"
    );
    let _ = fs::remove_dir_all(&d);
}

/// **w02**：写侧**原样提交**一件不该放行的事 ⇒ **由门禁拒**并**留流水**，那条变化一次都没落笔。
///
/// 判据出处：书 §4.5 `:585`（只写、不裁决，准不准问那道闸）；`tasks.md` 11.1 的验收①。
///
/// 与 C-04／C-04b 的分工：那两条在**真实二进制 + 真适配器进程**上跑同一条口径；
/// 本条在**库层 + 真内核进程**上跑"写侧提交 → 闸拒 → 流水落账"的整条链，
/// 以便把"改坏哪一行会红"钉在写侧自己的代码上（见文件头的变异表）。
#[test]
fn w02_a_gate_refusal_leaves_a_trail_and_nothing_lands() {
    let d = tmpdir("w02");
    let (ledger, onto, pol) = world_files(&d);
    // 身份 `world://agent/1`：出厂策略 `writes` 里 `world://agent/*` 是**空数组** ⇒ 一律不放行
    let k = start_kernel(&d, &ledger, &onto, &pol, "world://agent/1", 1);
    let client = KernelClient::new(&k.sock);

    let got =
        writeside::submit_external_change(&client, &a_declared_change(), &book_at(&onto)).unwrap();
    assert!(!got.admitted(), "不该放行的事必须由门禁拒：{got:?}");
    assert_eq!(
        code_of(got.verdict().unwrap()),
        Some("ext.world.Gate.WriteRejected"),
        "拒的判词必须点名门禁那一族错误码（不是写侧自造的）：{got:?}"
    );

    let log = k.finish();
    assert_kernel_did_not_panic(&log);
    assert!(
        log.contains("ext.world.Gate.WriteRejected"),
        "内核自己的日志必须点名是**门禁**拒的（写侧只是转述）：\n{log}"
    );

    let evs = ledger_lines(&ledger);
    assert_eq!(evs.len(), 1, "账本里只该有门禁的**流水**一条：{evs:?}");
    assert_eq!(
        evs[0]["kind"], "notice",
        "流水是通告，不是那条 change：{evs:?}"
    );
    assert_eq!(
        evs[0]["body"]["type"], "gate.write-rejected",
        "流水类型必须点名「写侧这次提交被拒」：{evs:?}"
    );
    assert_eq!(
        evs[0]["body"]["payload"]["refused_subject"], "world://notice/1",
        "流水里必须能看出它在拒绝什么：{evs:?}"
    );
    assert!(
        evs.iter().all(|e| e["kind"] != "change"),
        "门禁不放行 ⇒ **这条 change 一次都没落笔**：{evs:?}"
    );
    let _ = fs::remove_dir_all(&d);
}

/// **w03**：**正控**——同一条变化，世界允许时**必须落笔**，且落笔的身份来自内核映射。
///
/// 这条钉住"不该红的"：若有人把写侧改成"凡 `change` 一律不提交"（或把边界判成永远拒），
/// `w02` 仍绿而本条**必红** ⇒ 两条断言互不冒充。
/// 顺带钉住"身份不可自称"：落笔的 `actor` 是套接字映射给出的 `world://core`，
/// 而写侧交出去的请求里**没有**任何身份字段（`w01` 已断言信封只有 `kind`/`body`）。
#[test]
fn w03_the_same_change_lands_when_the_world_allows_it() {
    let d = tmpdir("w03");
    let (ledger, onto, pol) = world_files(&d);
    let k = start_kernel(&d, &ledger, &onto, &pol, "world://core", 1);
    let client = KernelClient::new(&k.sock);

    let got =
        writeside::submit_external_change(&client, &a_declared_change(), &book_at(&onto)).unwrap();
    assert!(got.admitted(), "世界允许时必须落笔：{got:?}");
    assert!(got.verdict().is_none(), "通过了就没有判词：{got:?}");

    let log = k.finish();
    assert_kernel_did_not_panic(&log);

    let evs = ledger_lines(&ledger);
    assert_eq!(evs.len(), 1, "{evs:?}");
    assert_eq!(evs[0]["kind"], "change");
    assert_eq!(
        evs[0]["actor"], "world://core",
        "身份由内核按套接字给出（写侧没有自称）"
    );
    assert_eq!(
        evs[0]["body"],
        json!({"subject":"world://notice/1","path":"muted","before":false,"after":true}),
        "落笔的信纸必须与提交的逐字段相同（含**前值**）"
    );
    let _ = fs::remove_dir_all(&d);
}

// ────────────────────────── ② 前值必须带上 ──────────────────────────

/// **w04**：外部系统给不出旧值 ⇒ **报错**，且**账本条数不变**；同一件事带上前值就能落笔。
///
/// 判据出处：书 §4.5 `:595` 逐字「写侧要做的是把"某个文件的一行变了"翻成
/// "某个对象的某个字段从旧值变成新值"，前值必须带上。少了前值，撤销与复盘各缺一半材料。」
///
/// 后一半是**正控**（钉住"不该红的"）：证明"世界本来就收得下这件事"——
/// 于是"账本 0 行"不是"世界坏了"，而是**写侧不肯替世界补意思**。
#[test]
fn w04_a_change_without_a_previous_value_is_refused_and_the_ledger_does_not_grow() {
    let d = tmpdir("w04");
    let (ledger, onto, pol) = world_files(&d);
    let k = start_kernel(&d, &ledger, &onto, &pol, "world://core", 1);
    let client = KernelClient::new(&k.sock);
    let book = book_at(&onto);

    // ① 只给新值（外部系统"知道自己现在是什么样，不知道原来是什么样"）⇒ 报错、**一次都没交出去**
    let blind = ExternalChange::new(
        "old-system:state.tsv:12",
        "world://notice/1",
        "muted",
        None,
        json!(true),
    );
    let e = writeside::submit_external_change(&client, &blind, &book).unwrap_err();
    assert_eq!(
        code_of(&e),
        Some("ext.world.Carrier.NoPreviousValue"),
        "{e}"
    );
    assert_eq!(
        ledger_lines(&ledger).len(),
        0,
        "翻不出来 ⇒ **账本条数必须不变**（不是「交了被拒」，是一次都没交）"
    );

    // ② 正控：同一件事，**带上**前值 ⇒ 世界收下
    let got = writeside::submit_external_change(&client, &a_declared_change(), &book).unwrap();
    assert!(
        got.admitted(),
        "带前值就该落笔（否则 ① 的「0 行」说明不了任何事）：{got:?}"
    );

    let log = k.finish();
    assert_kernel_did_not_panic(&log);
    assert_eq!(ledger_lines(&ledger).len(), 1, "正控那条必须真的落笔");
    let _ = fs::remove_dir_all(&d);
}

/// **w05**：**无法映射**的外部变化 ⇒ 报错，且**账本条数不变**；对齐了就能落笔。
///
/// 判据出处：书 §4.5 `:597` 逐字「翻的时候还有一条要守：写侧不许替世界补意思。
/// 翻不出来就报错，不许猜一个近似的字段名填上去。猜出来的字段名会进账本，
/// 进去以后就成了"事实"，而它从来没被任何人说过。」
///
/// 这里的"无法映射"取的正是**最危险的那种**：外部那台机器叫 `mute`，
/// 世界里声明的是 `muted`——**近似，但没有对齐**。
#[test]
fn w05_an_undeclared_field_is_refused_and_never_guessed() {
    let d = tmpdir("w05");
    let (ledger, onto, pol) = world_files(&d);
    let k = start_kernel(&d, &ledger, &onto, &pol, "world://core", 1);
    let client = KernelClient::new(&k.sock);
    let book = book_at(&onto);

    let e = writeside::submit_external_change(&client, &a_misnamed_change(), &book).unwrap_err();
    assert_eq!(
        code_of(&e),
        Some("ext.world.Carrier.UnmappableField"),
        "{e}"
    );
    assert_eq!(
        ledger_lines(&ledger).len(),
        0,
        "翻不出来 ⇒ **账本条数必须不变**（不许猜一个近似的名字再交出去）"
    );

    // 正控：把名字**对齐**（`muted`）⇒ 世界收下（证明上面那 0 行不是"世界坏了"）
    let got = writeside::submit_external_change(&client, &a_declared_change(), &book).unwrap();
    assert!(got.admitted(), "{got:?}");

    let log = k.finish();
    assert_kernel_did_not_panic(&log);
    assert_eq!(ledger_lines(&ledger).len(), 1);
    let _ = fs::remove_dir_all(&d);
}

/// **w06**：翻不出来时，写侧**一次都不许交出去**（猜出来的名字不许到内核跟前）。
///
/// 与 `w05` 的分工：`w05` 看的是"账本条数不变"（真账本），本条看的是
/// "**一个内核连接都没有**"（假内核）——两条一起才排除"交了、只是被拒了"这一种解释。
#[test]
fn w06_a_similar_field_name_never_reaches_the_kernel() {
    let d = tmpdir("w06");
    let sock = d.join("fake.sock");
    let h = fake_kernel(
        sock.clone(),
        r#"{"ok":true,"event":{"id":"e-should-not-happen"}}"#.to_string(),
    );

    let client = KernelClient::new(&sock);
    let e = writeside::submit_external_change(&client, &a_misnamed_change(), &book()).unwrap_err();
    assert_eq!(
        code_of(&e),
        Some("ext.world.Carrier.UnmappableField"),
        "{e}"
    );
    assert!(
        h.join().unwrap().is_none(),
        "翻不出来 ⇒ **一次都不许交出去**（若这里收到一行，说明写侧猜了个名字提交上去了）"
    );
    let _ = fs::remove_dir_all(&d);
}

// ────────────────────────── ③ 身份与权限边界 ──────────────────────────

/// **w07**：写侧自查"**对这个被管者身份**，账本与规则写不写得到"——布置合规才通过，放宽必被抓。
///
/// 判据出处：书 §4.5 `:601` 逐字「写侧这只手跑在自己的进程里，以被管者身份运行，
/// 对账本与规则都没有写权限。」
///
/// ⚠️ **本条证明的是哪一半**：文件系统上的**事实**（属主、mode 位、所在目录）——
/// 它可判、会红、与环境无关。**"以被管者身份真去写、真被拒"**那一半由系统级实测承担：
/// `tools/con01-no-bypass.sh`（跨 uid，含 uid 自证与拒绝原因断言）与
/// `tools/carrier_acceptance.sh` 的 C-09（同一台机器上以被管者身份跑**载体自己**去写）。
/// 两半不互相冒充：少任何一半，"写侧写不到法律与真相"都不算立住。
#[test]
fn w07_the_write_side_boundary_holds_only_when_the_facts_hold() {
    let d = tmpdir("w07");
    let (ledger, onto, pol) = world_files(&d);
    // 先让**真内核**把账本建出来、并真的落一笔（账本必须是世界的那一条，不是测试手造的）
    let k = start_kernel(&d, &ledger, &onto, &pol, "world://core", 1);
    let client = KernelClient::new(&k.sock);
    assert!(
        writeside::submit_external_change(&client, &a_declared_change(), &book_at(&onto))
            .unwrap()
            .admitted()
    );
    let log = k.finish();
    assert_kernel_did_not_panic(&log);
    assert_eq!(ledger_lines(&ledger).len(), 1);

    let managed: u32 = if this_uid() == 65534 { 65533 } else { 65534 };
    for (p, role) in [
        (&ledger, "账本（真相）"),
        (&pol, "门禁策略（法律）"),
        (&onto, "本体（法律·形状）"),
    ] {
        assert!(
            boundary::assert_managed_cannot_write(p, role, managed).is_ok(),
            "布置合规（属主非被管者、mode 无 go-w、目录无 go-w）⇒ 边界成立：{}",
            p.display()
        );
    }

    // 放宽一次 ⇒ **必须**被抓住（判据会变，不是橡皮图章）
    fs::set_permissions(&ledger, fs::Permissions::from_mode(0o666)).unwrap();
    let e = boundary::assert_managed_cannot_write(&ledger, "账本（真相）", managed).unwrap_err();
    assert!(e.contains("BoundaryWritable"), "{e}");
    fs::set_permissions(&ledger, fs::Permissions::from_mode(0o644)).unwrap();

    // 属主若是被管者 ⇒ 拒（mode 再严也没用：属主永远能 chmod u+w）
    let e = boundary::assert_managed_cannot_write(&ledger, "账本（真相）", this_uid()).unwrap_err();
    assert!(e.contains("BoundaryOwned"), "{e}");

    // 所在目录放宽 ⇒ 拒（"删掉再放一个新的"）
    fs::set_permissions(&d, fs::Permissions::from_mode(0o777)).unwrap();
    let e = boundary::assert_managed_cannot_write(&ledger, "账本（真相）", managed).unwrap_err();
    assert!(e.contains("BoundaryDirWritable"), "{e}");
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();

    let _ = fs::remove_dir_all(&d);
}
