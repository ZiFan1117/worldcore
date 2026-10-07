#![cfg(unix)]
//! 通道四个**资源边界**的独立断言（`REQ-F-026`；`cover-unimplemented-capabilities` 第 2 组）。
//!
//! ## 为什么不并进 `scripts/test/contract.rs::c14`
//!
//! `c14` 管的是**身份**（"落笔的 `actor` 取自内核映射、请求自称无效"），
//! 本文件管的是**资源**（并发连接数 / 单条消息字节 / 每秒消息数 / 空闲超时）。
//! 两件事各有各的守卫：谁红了，指向的毛病不该混在一起。
//!
//! ## 本文件证得到什么、证不到什么
//!
//! - **证得到**：四个边界各自的**超限即拒**、拒绝里**点名错误码与上限的当前值**、
//!   以及"被拒的那条**没有落笔**"（`Recorder::commits` 长度不变）。
//! - **证不到**：真账本上的行数（这里刻意不碰真账本）。
//!   端到端的账本比对面在 `tools/s1_sys_probe2.sh` 的 `TC-076`（真二进制 ＋ 真账本）。
//!
//! ## 每个用例的变异点（改坏哪一行 ⇒ 哪条红）
//!
//! | 用例 | 边界 | 改坏这里 ⇒ 本用例红 |
//! |---|---|---|
//! | `l01` | 单行上限 | `src/bus/mod.rs::read_line_bounded` 的 `content > max - buf.len()` |
//! | `l02` | 并发上限 | `src/bus/mod.rs::serve_n_with` 里对 `refuse_pending` 的调用 |
//! | `l03` | 空闲超时 | `src/bus/mod.rs::serve_stream` 里的 `set_read_timeout` 一行 |
//! | `l04` | 每秒消息数 | `src/bus/mod.rs::Session::admit` 的 `win.1 > max_msgs_per_sec` |
//! | `l05` | 四个数值的来源 | `src/bus/mod.rs::Limits::from_policy` 的三个 fail-closed 分支 |
//! | `l06` | 出厂配置 | `src/gate/policy.json` 的 `channel_limits` 块 |

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use world_core::bus::{self, Limits, Listener, RequestSink, Session};

/// 记录落笔调用的**假收方**（不碰真账本）。
///
/// "世界状态不变（不落笔）"在这里的可核形态就是：`commits` 的长度没变。
#[derive(Default)]
struct Recorder {
    commits: Vec<Value>,
}

impl RequestSink for Recorder {
    fn commit_requested(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        trace: Option<&str>,
        to: Option<&str>,
    ) -> Result<Value, String> {
        self.commits.push(json!({
            "kind": kind, "actor": actor, "body": body, "trace": trace, "to": to
        }));
        Ok(json!({"seq": self.commits.len(), "kind": kind}))
    }
}

fn tmpdir(tag: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("wc-chbounds-{tag}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

/// 建一个**测试用**监听者：刻意用 `UnixListener::bind` 而不是 `bus::bind`
/// （后者还要看目录 mode 与 uid——那是 `c14` 与 `tools/system_acceptance.sh` 的面）。
fn bind_in(d: &Path, name: &str) -> (PathBuf, UnixListener) {
    let p = d.join(name);
    let l = UnixListener::bind(&p).unwrap();
    (p, l)
}

fn expect_for(p: &Path) -> Listener {
    Listener {
        socket: p.to_path_buf(),
        actor: "world://agent/1".to_string(),
        uid: 0,
    }
}

/// 造一条**正好 `want` 字节**（不含换行）的合法 `notice` 请求行。
///
/// 用填充 `payload` 的方式凑长度：填充字符是 ASCII，故"字符数 = 字节数"，
/// 边界值（正好等于上限 / 超一个字节）才是**可判定**的。
fn request_line_of(want: usize) -> String {
    let head =
        r#"{"kind":"notice","body":{"type":"l01","subject":"world://notice/l01","payload":""}}"#;
    assert!(want >= head.len(), "want 太小，装不下最小请求");
    let pad = want - head.len();
    let s = format!(
        r#"{{"kind":"notice","body":{{"type":"l01","subject":"world://notice/l01","payload":"{}"}}}}"#,
        "a".repeat(pad)
    );
    assert_eq!(s.len(), want, "夹具自检：造出来的行必须正好 want 字节");
    s
}

/// 一条最小合法请求（落到 `Recorder` 上，故内容只求形状合法）。
fn minimal_request() -> String {
    r#"{"kind":"act","body":{"capability":"notice.mute","verb":"do","request_id":"r-bounds"}}"#
        .to_string()
}

/// 读一行应答。**读不到就返回空串**（不 panic）：这样"服务端没回话"这种变异
/// 会以"断言里的串不对"的形式变红，而不是把一个 IO 错误伪装成测试基础设施故障。
fn read_reply(c: &UnixStream) -> String {
    let mut line = String::new();
    let _ = BufReader::new(c).read_line(&mut line);
    line
}

/// 连上并设**客户端侧**读超时：万一服务端不说话（变异），用例应当**红**，不该**挂住**。
fn client(p: &Path) -> UnixStream {
    let c = UnixStream::connect(p).unwrap();
    c.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
    c
}

fn limits(max_line_bytes: usize, max_msgs_per_sec: u32, idle_timeout_ms: u64) -> Limits {
    Limits {
        max_connections: 1,
        max_line_bytes,
        max_msgs_per_sec,
        idle_timeout_ms,
    }
}

// ────────────────── l01 · 单行上限（REQ-F-026 ④）──────────────────

#[test]
fn l01_a_line_over_the_limit_is_refused_and_nothing_is_committed() {
    let d = tmpdir("l01");
    let lim = limits(256, 100, 3_000);

    // ① **正控**：正好 256 字节的行**必须被受理**。
    //    没有这一条，"把上限实现成一律拒"也能让 ② 变绿——那是恒红，不是判据。
    let (p1, l1) = bind_in(&d, "a.sock");
    let p1c = p1.clone();
    let h1 = std::thread::spawn(move || {
        let expect = expect_for(&p1);
        let mut rec = Recorder::default();
        let mut sess = Session::new(lim);
        let r = bus::serve_once_with(&mut rec, &l1, &expect, &mut sess);
        (rec, r)
    });
    let mut c1 = client(&p1c);
    c1.write_all(request_line_of(256).as_bytes()).unwrap();
    c1.write_all(b"\n").unwrap();
    let reply1 = read_reply(&c1);
    let (rec1, r1) = h1.join().unwrap();
    assert!(r1.is_ok(), "正好等于上限的行必须被受理；实得 {r1:?}");
    assert!(reply1.contains("\"ok\":true"), "应答: {reply1}");
    assert_eq!(rec1.commits.len(), 1, "正控：这一条必须真的落笔");

    // ② **反例**：257 字节 ⇒ 必须被拒、点名单行上限、且**不落笔**。
    let (p2, l2) = bind_in(&d, "b.sock");
    let p2c = p2.clone();
    let h2 = std::thread::spawn(move || {
        let expect = expect_for(&p2);
        let mut rec = Recorder::default();
        let mut sess = Session::new(lim);
        let r = bus::serve_once_with(&mut rec, &l2, &expect, &mut sess);
        (rec, r)
    });
    let mut c2 = client(&p2c);
    // 写失败不算故障：服务端读到超限那一刻就会回绝并关闭，对端再写可能拿到 EPIPE。
    let _ = c2.write_all(request_line_of(257).as_bytes());
    let _ = c2.write_all(b"\n");
    let reply2 = read_reply(&c2);
    let (rec2, r2) = h2.join().unwrap();
    assert!(
        reply2.contains("Channel.LineTooLong"),
        "超限必须**点名**单行上限；实得 {reply2}"
    );
    assert!(
        reply2.contains("max_line_bytes=256"),
        "拒绝里必须能读出上限的**当前值**；实得 {reply2}"
    );
    assert!(r2.is_err(), "超限必须返回 Err；实得 {r2:?}");
    assert_eq!(rec2.commits.len(), 0, "超限不得落笔（REQ-F-026 判据②）");
}

// ────────────────── l02 · 并发连接数上限（REQ-F-026 ③）──────────────────

#[test]
fn l02_the_second_simultaneous_connection_is_refused() {
    let d = tmpdir("l02");
    let (p, l) = bind_in(&d, "c.sock");
    let pc = p.clone();
    let h = std::thread::spawn(move || {
        let expect = expect_for(&p);
        let mut rec = Recorder::default();
        let mut sess = Session::new(limits(4096, 100, 5_000));
        let n = bus::serve_n_with(&mut rec, &l, &expect, &mut sess, 1).unwrap();
        (rec, n)
    });

    // "同时开两条连接"的可判定形态：
    // `#1` 先连上但**先不发请求**（服务端因此停在"读一行"上），
    // `#2` 在 `#1` **还在服务期间**连上 —— 这一条就是并发上限的违反者。
    // 两次 `connect` 都发生在 `#1` 的请求发出之前 ⇒ 判据不依赖调度时序。
    let mut c1 = client(&pc);
    let c2 = client(&pc);
    c1.write_all(minimal_request().as_bytes()).unwrap();
    c1.write_all(b"\n").unwrap();
    let r1 = read_reply(&c1);
    let r2 = read_reply(&c2);
    let (rec, n) = h.join().unwrap();

    assert!(
        r1.contains("\"ok\":true"),
        "第一条必须被正常服务；实得 {r1}"
    );
    assert!(
        r2.contains("Channel.TooManyConnections"),
        "第二条必须被拒并**点名**并发上限；实得 {r2}"
    );
    assert!(
        r2.contains("max_connections=1"),
        "拒绝里必须能读出上限的**当前值**；实得 {r2}"
    );
    assert_eq!(n, 1, "只受理了第一条；被拒的那条不计入已处理数");
    assert_eq!(rec.commits.len(), 1, "被拒的连接绝不可落笔");
}

// ────────────────── l03 · 空闲超时（REQ-F-026 ①）──────────────────

#[test]
fn l03_a_silent_connection_is_cut_at_the_idle_timeout() {
    let d = tmpdir("l03");
    let (p, l) = bind_in(&d, "d.sock");
    let pc = p.clone();
    let h = std::thread::spawn(move || {
        let expect = expect_for(&p);
        let mut rec = Recorder::default();
        let mut sess = Session::new(limits(4096, 100, 300));
        let r = bus::serve_once_with(&mut rec, &l, &expect, &mut sess);
        (rec, r)
    });

    let c = UnixStream::connect(&pc).unwrap();
    c.set_read_timeout(Some(Duration::from_secs(5))).unwrap();
    let t0 = Instant::now();
    let reply = read_reply(&c);
    let dt = t0.elapsed();
    // **先关对端再 join**：万一超时没生效（变异），服务端会一直阻塞在读上——
    // 那时 `join` 会把整个用例**挂住**而不是让它红。关掉连接 ⇒ 服务端读到 EOF 就退出，
    // 于是"超时没生效"表现为下面两条断言当场失败（红），而不是一个卡死的测试。
    drop(c);
    let (rec, r) = h.join().unwrap();

    assert!(
        reply.contains("Channel.IdleTimeout"),
        "静默连接必须被拒并**点名**空闲超时；实得 {reply}"
    );
    assert!(
        reply.contains("idle_timeout_ms=300"),
        "拒绝里必须能读出上限的**当前值**；实得 {reply}"
    );
    assert!(
        dt >= Duration::from_millis(250),
        "必须**等满**上限才动手：把还在等的活连接当空闲拒掉，是另一种错；实得 {dt:?}"
    );
    assert!(dt < Duration::from_secs(5), "必须在时限内断开；实得 {dt:?}");
    assert_eq!(rec.commits.len(), 0, "静默连接没有请求，不得落笔");
    assert!(r.is_err(), "超时必须返回 Err；实得 {r:?}");
}

// ────────────────── l04 · 每秒消息数上限（REQ-F-026 ②）──────────────────

#[test]
fn l04_messages_over_the_per_second_limit_are_refused_across_connections() {
    let d = tmpdir("l04");
    let (p, l) = bind_in(&d, "e.sock");
    let pc = p.clone();
    let h = std::thread::spawn(move || {
        let expect = expect_for(&p);
        let mut rec = Recorder::default();
        // 上限 2 条/秒：三次本机往返在同一个 1 秒窗口内完成（Unix 套接字是微秒级）。
        let mut sess = Session::new(limits(4096, 2, 5_000));
        let mut rs = Vec::new();
        for _ in 0..3 {
            rs.push(bus::serve_once_with(&mut rec, &l, &expect, &mut sess));
        }
        (rec, rs)
    });

    let mut got = Vec::new();
    for _ in 0..3 {
        let mut c = client(&pc);
        c.write_all(minimal_request().as_bytes()).unwrap();
        c.write_all(b"\n").unwrap();
        got.push(read_reply(&c));
    }
    let (rec, rs) = h.join().unwrap();

    assert!(
        got[0].contains("\"ok\":true"),
        "第 1 条必须放行；实得 {}",
        got[0]
    );
    assert!(
        got[1].contains("\"ok\":true"),
        "第 2 条必须放行（上限是 2，不是 1）；实得 {}",
        got[1]
    );
    assert!(
        got[2].contains("Channel.RateLimited"),
        "第 3 条必须被拒并**点名**每秒上限；实得 {}",
        got[2]
    );
    assert!(
        got[2].contains("max_msgs_per_sec=2"),
        "拒绝里必须能读出上限的**当前值**；实得 {}",
        got[2]
    );
    assert_eq!(rec.commits.len(), 2, "只有放行的两条落笔（超限不落笔）");
    assert!(rs[2].is_err(), "超限必须返回 Err；实得 {:?}", rs[2]);
}

// ────────────────── l05 · 四个数值**只**来自配置 ──────────────────

#[test]
fn l05_the_four_numbers_come_only_from_the_config() {
    let d = tmpdir("l05");
    let write = |name: &str, body: &str| -> PathBuf {
        let p = d.join(name);
        std::fs::write(&p, body).unwrap();
        p
    };

    // ① 缺 `channel_limits` 块 ⇒ **拒启**。
    //    这一条就是"代码里没有缺省值"的机器判据：只要 `from_policy` 里给任何一个
    //    `unwrap_or(<数>)`，这里就会**成功**，断言当场红。
    let p1 = write(
        "no-limits.json",
        r#"{"policy":1,"capabilities":{},"subjects":{"allow":["world://user"]},"writes":{},"irreversible_actors":[]}"#,
    );
    let e1 = Limits::from_policy(&p1).unwrap_err();
    assert!(e1.contains("Channel.NoLimits"), "实得：{e1}");

    // ② 齐备 ⇒ **逐字**读回（四个数一个不多一个不少）
    let p2 = write(
        "ok.json",
        r#"{"policy":1,"channel_limits":{"max_connections":1,"max_line_bytes":2048,"max_msgs_per_sec":3,"idle_timeout_ms":700}}"#,
    );
    assert_eq!(
        Limits::from_policy(&p2).unwrap(),
        Limits {
            max_connections: 1,
            max_line_bytes: 2048,
            max_msgs_per_sec: 3,
            idle_timeout_ms: 700
        }
    );

    // ③ 缺一项 ⇒ **点名**缺的那一项
    let p3 = write(
        "missing-one.json",
        r#"{"policy":1,"channel_limits":{"max_connections":1,"max_line_bytes":2048,"idle_timeout_ms":700}}"#,
    );
    let e3 = Limits::from_policy(&p3).unwrap_err();
    assert!(
        e3.contains("max_msgs_per_sec"),
        "缺哪一项就点名哪一项；实得：{e3}"
    );

    // ④ 取 0 ⇒ 拒：「不设界」不许由配置**悄悄**表达（那等于把边界关掉）
    let p4 = write(
        "zero.json",
        r#"{"policy":1,"channel_limits":{"max_connections":1,"max_line_bytes":0,"max_msgs_per_sec":3,"idle_timeout_ms":700}}"#,
    );
    let e4 = Limits::from_policy(&p4).unwrap_err();
    assert!(
        e4.contains("max_line_bytes") && e4.contains("= 0"),
        "拒绝要点名这一项与它的值；实得：{e4}"
    );

    // ⑤ 并发上限 ≠ 1 ⇒ 拒启（v1 顺序受理，不许在配置里假装能并发）
    let p5 = write(
        "concurrency.json",
        r#"{"policy":1,"channel_limits":{"max_connections":4,"max_line_bytes":2048,"max_msgs_per_sec":3,"idle_timeout_ms":700}}"#,
    );
    let e5 = Limits::from_policy(&p5).unwrap_err();
    assert!(e5.contains("Channel.BadConcurrency"), "实得：{e5}");
    assert!(
        e5.contains("max_connections = 4"),
        "拒启理由要点名当前值；实得：{e5}"
    );
}

// ────────────────── l06 · 出厂配置真的带这四个数 ──────────────────

#[test]
fn l06_the_factory_config_really_carries_the_four_numbers() {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json");
    let lim = Limits::from_policy(&p)
        .expect("出厂配置必须给出通道的四个数值（policy.json 的 channel_limits 块）");

    // 只钉**关系**，不复述数值：数值的权威载体是那一份配置本身（一处事实一个载体）。
    assert_eq!(lim.max_connections, 1, "v1 是顺序受理 ⇒ 并发上限只能是 1");
    assert!(
        lim.max_line_bytes >= 1024,
        "单行上限要容得下正常请求（出厂本体下三类最小合法请求实测 66/81/97 字节）；实得 {}",
        lim.max_line_bytes
    );
    assert!(
        lim.max_msgs_per_sec >= 1,
        "每秒消息数上限至少为 1，否则连一条正常请求都过不去；实得 {}",
        lim.max_msgs_per_sec
    );
    // `IF-REQ-04`：**服务方上限 < 调用方超时**。仓内自有的调用方
    // `tools/carrier_acceptance.sh` 用 `timeout 20`（20 000 ms）⇒
    // 出厂值必须小于它，否则那条端到端会先在**调用方**那侧超时。
    assert!(
        lim.idle_timeout_ms < 20_000,
        "空闲超时必须小于仓内调用方的 20 000 ms（IF-REQ-04 的不等式）；实得 {}",
        lim.idle_timeout_ms
    );
}

// ────────────────── l07 · 身份映射只许有一处权威（渲染物 ⊆ 法律）──────────────────
//
// 判的是什么：**受理路径只读渲染物**（`serve` 从继承来的 fd 取路径 → `ChannelConfig::load`
// → `listener_for`），而法律那份 `listeners` 在运行路径上零读者 ⇒ 渲染物事实上是**第二在册**。
// `ChannelConfig::load_checked` 就是那句话的执行体：渲染物每一条都要能在法律里解析到。
//
// 对账键是 **(socket, actor) 同时相同**——只对 socket 不够。
// 反例的形态＝**往渲染物里加一行映射**（真实违规形态），不是造畸形 JSON。

fn write_json(p: &Path, v: &Value) {
    if let Some(d) = p.parent() {
        std::fs::create_dir_all(d).unwrap();
    }
    std::fs::write(p, serde_json::to_string_pretty(v).unwrap()).unwrap();
}

/// 在册表（法律）夹具：一条口 → 一个主体。
fn law_one(sock: &Path, actor: &str) -> Value {
    json!({
        "policy": 1,
        "listeners": [ { "socket": sock.to_str().unwrap(), "actor": actor, "owner": "someone" } ]
    })
}

/// 渲染物夹具：与 `law_one` 对得上的一条。
fn render_one(sock: &Path, actor: &str, uid: u32) -> Value {
    json!({
        "channel": 1,
        "listeners": [ { "socket": sock.to_str().unwrap(), "actor": actor, "uid": uid } ]
    })
}

#[test]
fn l07_the_render_is_checked_against_the_law_before_it_is_used() {
    let d = tmpdir("l07");
    let sock = d.join("world.sock");
    let law = d.join("src/gate/policy.json");
    let render = d.join("channel.json");

    // ── 正控：渲染物与在册逐字对得上 ⇒ 必须过 ──
    write_json(&law, &law_one(&sock, "world://core"));
    write_json(&render, &render_one(&sock, "world://core", 965));
    let conf = bus::ChannelConfig::load_checked(&render, &law)
        .expect("正控：渲染物的每一条都在在册里 ⇒ 必须放行");
    assert!(
        conf.listener_for(&sock).is_some(),
        "正控：放行之后必须还能按路径找到那条绑定"
    );

    // ── 反例 A：渲染物里凭空多一行法律里没有的映射 ⇒ 必须红，且点名那一条 ──
    let ghost = d.join("ghost.sock");
    write_json(
        &render,
        &json!({
            "channel": 1,
            "listeners": [
                { "socket": sock.to_str().unwrap(), "actor": "world://core", "uid": 965 },
                { "socket": ghost.to_str().unwrap(), "actor": "world://ghost", "uid": 965 }
            ]
        }),
    );
    let e = bus::ChannelConfig::load_checked(&render, &law).unwrap_err();
    assert!(
        e.contains("ext.world.Channel.UndeclaredListener"),
        "反例 A：账外口必须点名 `UndeclaredListener`；实得：{e}"
    );
    assert!(
        e.contains(ghost.to_str().unwrap()),
        "反例 A：必须点名是哪一条口；实得：{e}"
    );

    // ── 反例 B：socket 对得上而 **actor 不同** ⇒ 仍必须红 ──
    //    （这一条把"对账键"钉死成 (socket, actor)；只对 socket 就会漏掉"换个身份"。）
    write_json(
        &render,
        &json!({
            "channel": 1,
            "listeners": [ { "socket": sock.to_str().unwrap(), "actor": "world://not-core", "uid": 965 } ]
        }),
    );
    let e = bus::ChannelConfig::load_checked(&render, &law).unwrap_err();
    assert!(
        e.contains("ext.world.Channel.UndeclaredListener"),
        "反例 B：同一个口换个身份也是账外口；实得：{e}"
    );

    // ── 反例 C：**基准缺失** ⇒ 必须红（不许把"没有在册表"读成"没有账外口"）──
    write_json(&law, &json!({ "policy": 1 }));
    write_json(&render, &render_one(&sock, "world://core", 965));
    let e = bus::ChannelConfig::load_checked(&render, &law).unwrap_err();
    assert!(
        e.contains("ext.world.Channel.NoDeclaredListeners"),
        "反例 C：法律里没有 `listeners` ⇒ 必须点名 `NoDeclaredListeners`；实得：{e}"
    );

    // ── 正控二：修回去 ⇒ 必须回绿（证明上面几条红**不是因为环境坏了**）──
    write_json(&law, &law_one(&sock, "world://core"));
    assert!(
        bus::ChannelConfig::load_checked(&render, &law).is_ok(),
        "正控二：把法律修回去之后必须重新放行"
    );

    let _ = std::fs::remove_dir_all(&d);
}

#[test]
fn l08_the_factory_law_really_declares_every_rendered_identity() {
    // 出厂面：**法律里必须真的有在册表**，而且 `declared_listeners` 读得出来。
    // 只钉关系、不复述条数（条数的权威载体是 policy.json 本身）。
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let law = root.join("src/gate/policy.json");
    let got = bus::declared_listeners(&law).expect("出厂法律必须有 listeners 段");
    assert!(
        got.iter().any(|d| d.actor == "world://core"),
        "出厂法律里必须有一条绑定到 world://core（内核自己的口）"
    );
    assert!(
        got.iter().any(|d| d.actor == "world://presence/omarchy"),
        "界面自己的口（world://presence/omarchy）必须在法律的在册表里——\
         新身份靠新口给出，而口→身份只能有一处权威"
    );
    // 每一条都得有 socket 与 actor（形状判据；空串不算）。
    for d in &got {
        assert!(
            !d.socket.as_os_str().is_empty() && !d.actor.is_empty(),
            "在册表里不许出现空的 socket 或 actor"
        );
    }
}
