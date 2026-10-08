//! **载体拉起（`serve`）**的判据与反例——**socket activation ＋ sd_notify**。
//!
//! ## 为什么单列一个测试件
//!
//! `scripts/release/units/world-core.service` 逐字是 `Type=notify` ＋ `ExecStart=… serve`，
//! 而 `scripts/release/units/world-core.socket` 逐字写着「监听套接字归载体所有；内核进程通过**继承的
//! 描述符**拿到它（`sd_listen_fds` 语义）」。⇒ 内核这一侧**必须有**对应实现，
//! 否则单元装上也起不来。本文件钉的就是**它拒启的那三格**与**报到顺序**。
//!
//! ## 判据（逐条对到 `src/main.rs` 的内联模块 `serve`）
//!
//! | # | 判据 | 反例（必须红／必须不致命） |
//! |---|---|---|
//! | ① | 缺 `LISTEN_FDS` ⇒ **拒启并点名** | 裸跑 `serve`（不带该变量） ⇒ `ext.world.Serve.NoListenFds`，rc≠0 |
//! | ① | `LISTEN_PID` 不是本进程 ⇒ **拒启并点名** | 把 `LISTEN_PID` 设成一个别的 pid ⇒ `ListenPidMismatch`，rc≠0 |
//! | ① | `LISTEN_FDS` 声明了但 **fd 3 不可用** ⇒ **拒启并点名** | 用 `exec` 保同一 pid、但**不传 fd 3** ⇒ `ListenFdUnusable`，rc≠0 |
//! | ④ | `NOTIFY_SOCKET` **缺失不许当致命** | 上面三条的失败理由里**不得**出现通知相关的码（它只因 LISTEN_* 而拒） |
//! | ② | `READY=1` **在开始受理之前**发出 | 单元用例 `ready_is_sent_before_accepting`（结构缝，投递是真的） |
//! | ③ | 有 `WATCHDOG_USEC` ⇒ 按**半周期**发 `WATCHDOG=1` | 单元用例（半周期算术与 0 的处理） |
//!
//! ## ★ 一处**如实登记的"未测"**
//!
//! **端到端**（真由 systemd 传 fd 3）在本仓**测不了**：`std` 没有 `dup2`，
//! 测试进程无法把监听套接字塞进子进程的 **fd 3** 并清掉 `CLOEXEC`（那需要 `libc`，
//! 而本仓只许 `serde_json` 一个依赖）。⇒ 本文件测的是**可测的那几格**
//! （环境变量拒启 ＋ 报到顺序 ＋ 报文真实投递），**不假装**测过端到端。
//! 见 `ninedim/03-执行环/05-验证证据/证据-EV-009.md` 的登记。

use std::path::PathBuf;
use std::process::Command;

fn tmpdir(tag: &str) -> PathBuf {
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-serve-{tag}-{n}"));
    std::fs::create_dir_all(&d).unwrap();
    d
}

/// 跑一次 `serve`，把 `LISTEN_*` / `NOTIFY_SOCKET` 交给调用方控制。
///
/// ⚠️ 三条反例**都在打开世界之前**发生（环境检查在前）⇒ 本体/账本/策略给不存在的路径
/// 反而能把判据**隔离**出来：失败理由只能是环境那一格。
fn run_serve(tag: &str, env: &[(&str, &str)]) -> (i32, String) {
    let d = tmpdir(tag);
    let bin = env!("CARGO_BIN_EXE_world-core");
    let mut c = Command::new(bin);
    c.arg("--ontology")
        .arg(d.join("nope-ontology.json"))
        .arg("--ledger")
        .arg(d.join("ledger.jsonl"))
        .arg("--policy")
        .arg(d.join("nope-policy.json"))
        .arg("--channel")
        .arg(d.join("nope-channel.json"))
        .arg("serve");
    // 先把「可能从测试进程继承来的」两个变量清掉，再由调用方按需设。
    c.env_remove("LISTEN_FDS")
        .env_remove("LISTEN_PID")
        .env_remove("NOTIFY_SOCKET")
        .env_remove("WATCHDOG_USEC");
    for (k, v) in env {
        c.env(k, v);
    }
    let out = c.output().expect("跑得起来 world-core serve");
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), txt)
}

/// **①缺 `LISTEN_FDS`** ⇒ 拒启并点名；且**不许**因为 `NOTIFY_SOCKET` 缺失而报错（口径④）。
#[test]
fn s01_serve_without_listen_fds_is_refused_and_names_the_code() {
    let (rc, out) = run_serve("s01", &[]);
    assert_ne!(rc, 0, "缺 `LISTEN_FDS` 必须拒启；实得 rc={rc}\n{out}");
    assert!(
        out.contains("ext.world.Serve.NoListenFds"),
        "拒绝理由必须**点名**那条错误码，实得：\n{out}"
    );
    // 口径④：`NOTIFY_SOCKET` **缺失**不许当致命 ⇒ 它不能是这条失败的理由。
    assert!(
        !out.contains("BadNotifySocket"),
        "`NOTIFY_SOCKET` 缺失**不是**致命（裸跑要能起来）⇒ 拒绝理由里不许出现它，实得：\n{out}"
    );
    // 也不许把"没有 LISTEN_FDS"读成"那我自己 bind 一个"——理由里要写清为什么不自建。
    assert!(
        out.contains("不自己 `bind`"),
        "拒绝理由要说清「为什么不退化成本地 bind」，实得：\n{out}"
    );
}

/// **①`LISTEN_PID` 不是本进程** ⇒ 拒启并点名（fd 的归属不许猜）。
#[test]
fn s02_serve_with_a_foreign_listen_pid_is_refused() {
    // 挑一个几乎不可能是本进程的 pid。
    let (rc, out) = run_serve("s02", &[("LISTEN_FDS", "1"), ("LISTEN_PID", "999999")]);
    assert_ne!(
        rc, 0,
        "`LISTEN_PID` 不是本进程必须拒启；实得 rc={rc}\n{out}"
    );
    assert!(
        out.contains("ext.world.Serve.ListenPidMismatch"),
        "必须点名那条错误码，实得：\n{out}"
    );
    assert!(
        out.contains("999999"),
        "理由里要写出**实得**的 pid（否则读的人不知道是谁的 fds），实得：\n{out}"
    );
}

/// **①`LISTEN_FDS` 有但 `LISTEN_PID` 缺** ⇒ 同样拒启（不许"反正只有我一个进程"就收下）。
#[test]
fn s03_serve_without_listen_pid_is_refused() {
    let (rc, out) = run_serve("s03", &[("LISTEN_FDS", "1")]);
    assert_ne!(rc, 0, "缺 `LISTEN_PID` 必须拒启；实得 rc={rc}\n{out}");
    assert!(
        out.contains("ext.world.Serve.ListenPidMismatch"),
        "实得：\n{out}"
    );
}

/// **①`LISTEN_FDS` 声明了但 fd 3 不可用** ⇒ 拒启并点名。
///
/// 用 `sh -c '… LISTEN_PID=$$ exec <bin> … serve'`：`exec` **保持同一个 pid**
/// ⇒ `LISTEN_PID` 校验能过，而 fd 3 **没有被传进来** ⇒ 正好打在"fd 3 不可用"那一格。
#[cfg(unix)]
#[test]
fn s04_serve_with_an_unusable_fd3_is_refused() {
    let d = tmpdir("s04");
    let bin = env!("CARGO_BIN_EXE_world-core");
    // 用 env(1) 设变量、用 $$ 取 sh 自己的 pid，然后 exec（pid 不变）。
    let script = format!(
        "LISTEN_FDS=1 LISTEN_PID=$$ exec '{}' --ontology '{}' --ledger '{}' --policy '{}' --channel '{}' serve",
        bin,
        d.join("nope-ontology.json").display(),
        d.join("ledger.jsonl").display(),
        d.join("nope-policy.json").display(),
        d.join("nope-channel.json").display(),
    );
    let out = Command::new("sh")
        .arg("-c")
        .arg(&script)
        .env_remove("NOTIFY_SOCKET")
        .env_remove("WATCHDOG_USEC")
        .output();
    let Ok(out) = out else {
        eprintln!("[登记] 本机没有 `sh` ⇒ s04 跑不了（不把'读不到'读成'没有违规'）");
        return;
    };
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    let rc = out.status.code().unwrap_or(-1);
    assert_ne!(rc, 0, "fd 3 不可用必须拒启；实得 rc={rc}\n{txt}");
    assert!(
        !txt.contains("fatal runtime error"),
        "拒启**不许**变成 `fatal runtime error`（那连退出码都给不出，载体只看到'进程崩了'）——\
         必须是一条**可判定、可点名**的拒绝。实得：\n{txt}"
    );
    assert!(
        txt.contains("ext.world.Serve.ListenFdUnusable"),
        "必须点名那条错误码，实得：\n{txt}"
    );
    assert!(
        txt.contains("fd 3"),
        "理由要**点名 fd 3**（`sd_listen_fds` 的约定），实得：\n{txt}"
    );
}

/// **④`NOTIFY_SOCKET` 缺失不许致命**——正控：把变量设成一个**用不了的**值，
/// 而 `LISTEN_FDS` 也缺 ⇒ 失败理由仍**只**该是 `LISTEN_FDS`（不是通知那一格）。
///
/// 这条同时钉住**检查顺序**：环境里最基础的那一格先判，不许被通知变量带跑。
#[test]
fn s05_a_bad_notify_socket_does_not_mask_the_listen_fds_refusal() {
    let (rc, out) = run_serve("s05", &[("NOTIFY_SOCKET", "/nonexistent/dir/notify.sock")]);
    assert_ne!(rc, 0, "缺 `LISTEN_FDS` 仍必须拒启；实得 rc={rc}\n{out}");
    assert!(
        out.contains("ext.world.Serve.NoListenFds"),
        "先判的必须是 `LISTEN_FDS` 那一格，实得：\n{out}"
    );
}
