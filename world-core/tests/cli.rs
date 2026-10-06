//! **CLI 层测试**（`M04`/`M09` 的入口）。
//!
//! ## 为什么必须有这一层（第 27 轮的教训）
//!
//! 第 26 轮落地 `--require-chain` 后，CLI 一度把**刚写好、带链的账本报告为"无链"**
//! （`load_chain` 里 `self.chained = true;` 漏了）。当时 **57 项测试全绿**——
//! 因为那些用例断言的是"链写出且自洽""篡改被拒"，**从没走过 CLI 一遍**。
//! 抓到那个 bug 的是**一次真实命令行调用**，不是测试套件。
//! 本文件把那一次的调用**固化成会失败的检查**。
//!
//! `WC-UT-001` §三 早就把 `M04` 标为"无模块内单元测试"，这是它欠的那部分。
//!
//! ## 做法
//!
//! 直接用 `CARGO_BIN_EXE_world-core`（Cargo 给集成测试注入的二进制路径），
//! **零新增依赖**，跑的是**真正编译出来的可执行文件**——不是内存里的函数。

use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use world_core::gui_projection::{assert_same_source, parse_header};

/// 取本进程 uid（不引 libc：用 `/proc/self/status`）。
///
/// 通道映射里要填一个 uid；本文件的用例只关心**套接字路径在不在映射里**，
/// 所以填"当前 uid"即可——这样连"变异实现真去 chown 建了套接字"也能跑通，
/// 让那条变异的表现落在**断言**上（rc / 错误串），而不是落在权限失败上。
#[cfg(unix)]
fn libc_uid() -> u32 {
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

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-cli-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    d
}

fn manifest() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// 跑一次 CLI，返回 (退出码, stdout, stderr)。
fn run(args: &[&str]) -> (i32, String, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_world-core"))
        .args(args)
        .output()
        .expect("无法启动被测二进制");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

/// 一次 `check` 的常用参数。
fn check_args(d: &std::path::Path) -> Vec<String> {
    vec![
        "--ontology".into(),
        manifest().join("src/ontology_definition/ontology.json").display().to_string(),
        "--policy".into(),
        manifest().join("src/gate/policy.json").display().to_string(),
        "--ledger".into(),
        d.join("ledger.jsonl").display().to_string(),
        "check".into(),
    ]
}

fn as_refs(v: &[String]) -> Vec<&str> {
    v.iter().map(String::as_str).collect()
}

/// **cli-01**：`check` 在空账本上打印 `READY`，且**如实报告无链**（未校验要说出来）。
#[test]
fn cli01_check_reports_ready_and_chain_status() {
    let d = tmpdir("cli01");
    let args = check_args(&d);
    let (code, out, _) = run(&as_refs(&args));
    assert_eq!(code, 0, "空账本应能打开；stdout={out}");
    assert!(out.contains("READY"), "冒烟判据是打印 READY；stdout={out}");
    assert!(
        out.contains("无摘要链"),
        "空账本无链，必须**明说**不可检出；stdout={out}"
    );
}

/// **cli-02**：写入后 `check` 必须报告**有链**（第 26 轮就是这里错了）。
#[test]
fn cli02_after_append_check_reports_chained() {
    let d = tmpdir("cli02");
    let lp = d.join("ledger.jsonl");
    let base = || -> Vec<String> {
        vec![
            "--ontology".into(),
            manifest().join("src/ontology_definition/ontology.json").display().to_string(),
            "--policy".into(),
            manifest().join("src/gate/policy.json").display().to_string(),
            "--ledger".into(),
            lp.display().to_string(),
        ]
    };

    let mut a = base();
    a.push("append".into());
    a.push("change".into());
    a.push(r#"{"subject":"world://s","path":"p","before":null,"after":1}"#.into());
    let (code, _, err) = run(&as_refs(&a));
    assert_eq!(code, 0, "append 应成功；stderr={err}");

    let mut c = base();
    c.push("check".into());
    let (code, out, _) = run(&as_refs(&c));
    assert_eq!(code, 0);
    assert!(
        out.contains("有摘要链"),
        "写入侧带链，CLI 必须报告有链（第 26 轮真实踩过恒报无链）；stdout={out}"
    );
}

/// **cli-03**：`--require-chain` 对无链账本**拒绝启动**（rc=2），有链则放行。
#[test]
fn cli03_require_chain_refuses_chainless_ledger() {
    let d = tmpdir("cli03");
    let lp = d.join("legacy.jsonl");
    // 手工造一个合法但**无链**的事件行（模拟 v1 账本）
    fs::write(
        &lp,
        concat!(
            r#"{"world":1,"kind":"notice","id":"x","seq":1,"at":1,"actor":"world://user","#,
            r#""flags":[],"body":{"type":"t","subject":"world://s"}}"#,
            "\n"
        ),
    )
    .unwrap();

    let common = || -> Vec<String> {
        vec![
            "--ontology".into(),
            manifest().join("src/ontology_definition/ontology.json").display().to_string(),
            "--policy".into(),
            manifest().join("src/gate/policy.json").display().to_string(),
            "--ledger".into(),
            lp.display().to_string(),
        ]
    };

    // 默认：放行（v1 兼容），但必须警示
    let mut a = common();
    a.push("check".into());
    let (code, out, _) = run(&as_refs(&a));
    assert_eq!(code, 0, "无链账本默认应能打开");
    assert!(out.contains("无摘要链"), "必须警示；stdout={out}");

    // --require-chain：拒绝启动，且理由可编程判定（错误码）
    let mut b = common();
    b.push("--require-chain".into());
    b.push("check".into());
    let (code, _, err) = run(&as_refs(&b));
    assert_eq!(code, 2, "应拒绝启动；stderr={err}");
    assert!(
        err.contains("ext.world.Ledger.NoChain"),
        "拒绝理由须带错误码；stderr={err}"
    );
}

/// **cli-04**：用法错误的退出码是 **1**（与"世界有问题"的 2 区分开）。
#[test]
fn cli04_usage_error_exits_one() {
    let d = tmpdir("cli04");
    let args = check_args(&d);
    let mut bad = args[..args.len() - 1].to_vec();
    bad.push("no-such-subcommand".into());
    let (code, _, err) = run(&as_refs(&bad));
    assert_eq!(code, 1, "未知子命令应 rc=1；stderr={err}");

    // `--help` 也应 rc=0
    let (code, out, _) = run(&["--help"]);
    assert_eq!(code, 0);
    assert!(out.contains("world-core"), "帮助应打印用法；stdout={out}");
}

/// **cli-07**：`append` 的**缺省身份**必须在用法串里如实地看得见（缺陷台账 **D-43**）。
///
/// ## 这条为什么要单独有（它是一处"从不失败的检查"的反面）
///
/// `cmd_append` 从第 4 个参数取 `actor`、缺省 `world://user`；而 `policy.json` 把该主体列为
/// **唯一**可执行不可逆动作、且授权它写**任意**对象。也就是说：**不写身份 = 最高授权**。
/// 在本次修改之前，用法串里**一个字都没提这个参数**，`--help` 里 `actor` 出现 **0 次**——
/// 于是"最省事的用法"恰好是"后果最大的用法"，而这件事在帮助里是隐形的。
///
/// 本测试把"帮助里必须看得见缺省身份"钉成会失败的断言：
/// 谁再把 `[actor]` 或 `world://user` 从用法串里删掉，**这里就会红**。
#[test]
fn cli07_usage_string_discloses_default_actor() {
    let (code, _out, err) = run(&["append"]);
    assert_eq!(code, 1, "参数不足应 rc=1；err={err}");
    assert!(
        err.contains("[actor]"),
        "用法串必须显示身份这个可选参数；stderr={err}"
    );
    assert!(
        err.contains("world://user"),
        "用法串必须显示缺省身份；stderr={err}"
    );

    let (code, out, _) = run(&["--help"]);
    assert_eq!(code, 0);
    assert!(
        out.contains("append <kind> <json-body> [actor]"),
        "帮助里的 append 行必须带上 [actor]；stdout={out}"
    );
    assert!(
        out.contains("world://user"),
        "帮助必须写明缺省身份是 world://user；stdout={out}"
    );
}

/// **cli-05**：两个投影的**同源核对**在 CLI 上真的跑通（`project check`）。
#[test]
fn cli05_project_check_reports_same_source() {
    let d = tmpdir("cli05");
    let lp = d.join("ledger.jsonl");
    let base = || -> Vec<String> {
        vec![
            "--ontology".into(),
            manifest().join("src/ontology_definition/ontology.json").display().to_string(),
            "--policy".into(),
            manifest().join("src/gate/policy.json").display().to_string(),
            "--ledger".into(),
            lp.display().to_string(),
        ]
    };
    let mut a = base();
    a.push("append".into());
    a.push("change".into());
    a.push(r#"{"subject":"world://s","path":"p","before":null,"after":true}"#.into());
    assert_eq!(run(&as_refs(&a)).0, 0);

    let mut c = base();
    c.push("project".into());
    c.push("check".into());
    let (code, out, _) = run(&as_refs(&c));
    assert_eq!(code, 0, "同源核对应通过");
    assert!(
        out.contains("同源") && out.contains("✅"),
        "应报告同源一致；stdout={out}"
    );
}

/// **cli-06**：`--require-chain` 与**空账本**的关系（本轮的修正）。
///
/// 修正前：空账本被判"无链" ⇒ `--require-chain` **第一天就不可用**
/// （新部署一启动就被拒）。修正后：**空账本不算违规**（没有东西要保护），
/// 一旦有了**无链**事件才拒绝。
#[test]
fn cli06_require_chain_allows_empty_but_refuses_chainless_data() {
    let d = tmpdir("cli06");
    let lp = d.join("l.jsonl");
    let base = || -> Vec<String> {
        vec![
            "--ontology".into(),
            manifest().join("src/ontology_definition/ontology.json").display().to_string(),
            "--policy".into(),
            manifest().join("src/gate/policy.json").display().to_string(),
            "--ledger".into(),
            lp.display().to_string(),
            "--require-chain".into(),
            "check".into(),
        ]
    };

    // ① 空账本（文件尚不存在 ⇒ 新建）→ 应放行
    let (code, out, err) = run(&as_refs(&base()));
    assert_eq!(code, 0, "空账本不应被 --require-chain 拒绝；stderr={err}");
    assert!(out.contains("READY"), "stdout={out}");

    // ② 放一条**无链**事件进去 → 应拒绝（理由带错误码）
    let legacy = d.join("legacy.jsonl");
    fs::write(
        &legacy,
        concat!(
            r#"{"world":1,"kind":"notice","id":"x","seq":1,"at":1,"actor":"world://user","#,
            r#""flags":[],"body":{"type":"t","subject":"world://s"}}"#,
            "\n"
        ),
    )
    .unwrap();
    let mut args: Vec<String> = base();
    let pos = args.iter().position(|a| a == "--ledger").unwrap();
    args[pos + 1] = legacy.display().to_string();
    let (code, _, err) = run(&as_refs(&args));
    assert_eq!(code, 2, "有事件但无链 ⇒ 拒绝；stderr={err}");
    assert!(err.contains("NoChain"), "stderr={err}");
}

/// **cli-08**（任务 2.2）：`channel bind` 对**不在身份映射里**的套接字
/// 报 `ext.world.Channel.NotConfigured` 且 `rc=2`。
///
/// ## 为什么这条必须走 CLI
///
/// `channel.rs` 的单元测试只测了"`listeners` 为空被拒"——那是**配置本身坏**。
/// 而"配置是好的、只是**这个套接字**不在映射里"走的是**生产入口**
/// （`main.rs::cmd_channel` 的 `None` 分支），此前**零断言**。
/// 它是「通道的身份来自内核映射」这条纪律的另一半：
/// **映射里没有 ⇒ 连连接点都不该建出来**（默认拒绝）。
///
/// ## 变异
///
/// 删掉 `cmd_channel` 里 `None` 分支的拒绝（改成沿用配置里的第一条身份映射）
/// ⇒ 这条变红：rc 变 0、`unmapped.sock` 那个套接字真被建出来了。
#[cfg(unix)]
#[test]
fn cli08_channel_bind_refuses_socket_not_in_identity_map() {
    let d = tmpdir("cli08");
    let mapped = d.join("mapped.sock");
    let unmapped = d.join("unmapped.sock");
    let cfg = d.join("channel.json");
    // 映射里**只有** mapped.sock；unmapped.sock 不在册。
    fs::write(
        &cfg,
        format!(
            "{{\"channel\":1,\"listeners\":[{{\"socket\":\"{}\",\"actor\":\"world://agent/1\",\"uid\":{}}}]}}",
            mapped.display(),
            libc_uid()
        ),
    )
    .unwrap();

    let (cfg_s, unmapped_s) = (cfg.display().to_string(), unmapped.display().to_string());
    let (code, out, err) = run(&[
        "--channel",
        cfg_s.as_str(),
        "channel",
        "bind",
        unmapped_s.as_str(),
    ]);
    assert_eq!(
        code, 2,
        "不在身份映射里的套接字必须拒绝（rc=2）；stdout={out} stderr={err}"
    );
    assert!(
        err.contains("ext.world.Channel.NotConfigured"),
        "拒绝理由必须点名错误码，读流水的人才能程序判定；stderr={err}"
    );
    assert!(
        err.contains("身份映射"),
        "理由要说清「没有身份映射的连接不得建立」；stderr={err}"
    );
    assert!(
        !unmapped.exists(),
        "被拒的套接字**一个字节都不该落**：没有身份映射就不建连接点（实得它被建了）"
    );
}

/// **cli-09**（任务 3.1，按实现改写后的措辞）：`world://user`（出厂
/// `irreversible_actors` 的**唯一**成员）执行不可逆能力（`ledger.compact`）
/// ⇒ **放行**，且账本里
///
/// ① **没有**任何 `gate.*` 通告（没被拒、也没被"加摩擦到拒绝"）；
/// ② 那条 `act` 事件**必带** `gate.friction:<等级>` 旗标，等级取自
///    载体清单 `cap.d/ledger.compact.json` 的 `risk`（出厂写的是 `high`）。
///
/// ## 为什么把「必带摩擦」也写进来（这一半是**实现改过之后**的口径）
///
/// 书 §5.5：摩擦挂在**动作的不可逆等级**上，不挂在执行者身份上。旧措辞只说
/// "放行且不出现 `gate.*`"，照抄会**漏掉摩擦旗标**——而漏掉它，白名单主体执行
/// 不可逆动作就又回到"零痕迹"那一格了（`gate.rs` 的 `Friction` 文档逐字写着
/// "必留可核痕迹 + 由预批身份承担"）。故本条**两句一起断言**。
///
/// ## 变异
///
/// 让白名单主体也走 `AwaitApproval`（`Policy::decide` 里那条 `Decision::Allow`
/// 改成 `AwaitApproval`）⇒ rc 变 2、`act` 不落笔 ⇒ 本条变红。
#[test]
fn cli09_whitelisted_actor_may_run_irreversible_and_the_event_carries_friction() {
    let d = tmpdir("cli09");
    let lp = d.join("ledger.jsonl");
    let (ont_s, pol_s, lp_s) = (
        manifest().join("src/ontology_definition/ontology.json").display().to_string(),
        manifest().join("src/gate/policy.json").display().to_string(),
        lp.display().to_string(),
    );

    // 不写第 4 个参数 ⇒ actor 取 `world://user`（出厂 irreversible_actors 的唯一成员）。
    let (code, out, err) = run(&[
        "--ontology",
        &ont_s,
        "--policy",
        &pol_s,
        "--ledger",
        &lp_s,
        "append",
        "act",
        r#"{"capability":"ledger.compact","verb":"do","request_id":"r-cli09","params":{}}"#,
    ]);
    assert_eq!(
        code, 0,
        "白名单主体执行不可逆动作必须**放行**（v1 无审批通道，否则该能力是死号）；stderr={err}"
    );
    assert!(
        out.contains("\"kind\":\"act\""),
        "落笔的应是 act；stdout={out}"
    );

    // ── ② 摩擦旗标：等级**取自载体清单**，不是写死在这里 ──
    let cap_manifest = manifest().join("cap.d/ledger.compact.json");
    let cap: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&cap_manifest).unwrap()).unwrap();
    let level = cap["risk"]
        .as_str()
        .expect("出厂清单必须声明 risk（闸读到的等级就来自它）")
        .to_string();
    let want_flag = format!("gate.friction:{level}");

    let text = fs::read_to_string(&lp).unwrap();
    let lines: Vec<&str> = text.lines().collect();
    assert_eq!(
        lines.len(),
        1,
        "① 放行 ⇒ 账本里只该有那一条 act；出现第二条就是写了 `gate.*` 通告（被拒/加摩擦）：{text}"
    );
    let ev: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
    let flags: Vec<String> = ev["flags"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();
    assert!(
        flags.iter().any(|f| f == &want_flag),
        "② 白名单主体执行不可逆动作**必带**摩擦旗标 `{want_flag}`\
         （等级 {level} 取自 {}），实得 flags={flags:?}",
        cap_manifest.display()
    );
    assert!(
        !text.contains("gate.awaiting-approval") && !text.contains("gate.rejected"),
        "① 这条路径**不得**出现任何 `gate.*` 通告（它既没被拒、也没加摩擦到拒绝）：{text}"
    );
}

// ═══════════════════════════════════════════════════════════════════════════
// cli-13 … cli-17 —— **投影与读模型**的命令路径断言（`fc-2026-004-assertions` 组 5）
//
// - `cli-13`（5.1）`project check` 的判据**只剩头部四项**：正文少一半仍判同源（当下边界）
// - `cli-14`（5.2）两个投影**取自同一 state 与同一 vocab**：三个「不等」分支在命令路径不可达
// - `cli-15`（5.5）用法串里列出 `checkpoint write|verify|resume` 三条（且分发侧清单一致）
// - `cli-16`（5.3）`Checkpoint::FORMAT` 版本不符 ⇒ 点名 `ext.world.Checkpoint.BadFormat`
// - `cli-17`（5.4）`checkpoint resume` 走**未核验续算**、由**事后比对**报 `ResumeMismatch`
// ═══════════════════════════════════════════════════════════════════════════

/// 常用参数前缀 ＋ 调用方给的尾巴（账本路径由调用方给）。
fn args_for(lp: &std::path::Path, tail: &[&str]) -> Vec<String> {
    let mut v = vec![
        "--ontology".to_string(),
        manifest().join("src/ontology_definition/ontology.json").display().to_string(),
        "--policy".to_string(),
        manifest().join("src/gate/policy.json").display().to_string(),
        "--ledger".to_string(),
        lp.display().to_string(),
    ];
    v.extend(tail.iter().map(|s| s.to_string()));
    v
}

/// 一条**合法**的 `change`：`world://user` 写 `world://notice/n-1#muted`
/// （主体与字段都在出厂本体/策略里声明过）。
const LEGAL_CHANGE: &str =
    r#"{"subject":"world://notice/n-1","path":"muted","before":null,"after":true}"#;

/// **cli-13**（`5.1`）：`project check` 的判据**只剩头部四项**。
///
/// 判据函数 `project::assert_same_source`（`src/gui_projection/mod.rs:124-145`；`cmd_project`
/// 在 `src/main.rs:442` 调它）只比 `world` / `vocab` / `last_seq` / `state`，**不比正文**
/// ⇒「一方少渲一半主体、头部四项相同」这个形状**在判据下仍然通过**。
/// 这不是想要的行为，而是**当下边界**：本用例把它固定成会红的检查 ——
/// 谁把正文也纳入判据，这里立刻红，且规格要同步改（不许偷偷放宽）。
///
/// 做法：正文取自**命令自己的输出**（`project language`），再删掉一半主体行；头部一字不动。
#[test]
fn cli13_project_check_criterion_reads_only_the_header() {
    let d = tmpdir("cli08");
    let lp = d.join("ledger.jsonl");

    // 夹具：两个主体（否则「少渲一半」无从谈起）
    for body in [
        r#"{"subject":"world://notice/n-1","path":"muted","before":null,"after":true}"#,
        r#"{"subject":"world://notice/n-2","path":"muted","before":null,"after":false}"#,
    ] {
        let a = args_for(&lp, &["append", "change", body]);
        let (code, _, err) = run(&as_refs(&a));
        assert_eq!(code, 0, "夹具：append 应成功；stderr={err}");
    }

    // A = 命令自己的语言投影输出：同源头 ＋ 2 个主体行
    let a_args = args_for(&lp, &["project", "language"]);
    let (code, a, err) = run(&as_refs(&a_args));
    assert_eq!(code, 0, "stderr={err}");
    let a_lines: Vec<&str> = a.lines().collect();
    assert_eq!(a_lines.len(), 3, "同源头 ＋ 2 个主体行；实得：{a}");

    // B = **只留一半主体**、头部四项一字不动
    let b = format!("{}\n{}\n", a_lines[0], a_lines[1]);

    // 夹具自证：两份内容**确实不同**（否则下面那条「仍判同源」是空话）
    assert_ne!(a, b, "夹具：两份文本必须真的不同");
    assert_eq!(a.lines().count(), 3);
    assert_eq!(b.lines().count(), 2);

    // ★ 判据（命令所用者）：正文少一半、头部相同 ⇒ **仍判同源**
    assert!(
        assert_same_source(&a, &b).is_ok(),
        "project check 的判据只剩头部四项：正文少一半也必须**仍判同源**（这是当下边界）"
    );

    // 正控：把头部里的一项（state 指纹）改掉 ⇒ **同一函数**必须报不同源（证明它不是恒 Ok）
    let h = parse_header(&a).expect("命令输出的首行必须是可解析的同源头");
    let broken = b.replace(
        &format!("state={}", h.state),
        "state=fnv1a64:0000000000000000",
    );
    assert_ne!(broken, b, "正控夹具：state 字段必须真的被替换掉");
    let e = assert_same_source(&broken, &a).expect_err("状态指纹不同 ⇒ 必须报不同源");
    assert!(e.contains("状态不同"), "实得: {e}");
}

/// **cli-14**（`5.2`）：`project check` 的两个投影**取自同一 `state` 与同一 `vocab`**
/// ⇒ `assert_same_source` 的三个「不等」分支在**命令路径上不可达**。
///
/// 怎么变成会红的检查（而不是复述代码）：**两个独立进程**分别渲染两份投影
/// （`project language` / `project visual`），把两份输出的**同源头逐字段**比。
/// 只要命令路径给两份投影喂了不同的 `state` 或 `vocab`（例如改 `src/main.rs` 里
/// `visual::render(&state, world, vocab)` 那一行的实参），这里立刻红。
/// 出处：`src/main.rs:408-410` —— `cmd_project` 里同一次 `open_readonly`、同一次
/// `read_model`、同一个 `vocab_hash`，两个渲染函数各拿一份**只读**引用
/// ⇒ 结构上没有「传不同状态」的余地。
#[test]
fn cli14_project_check_feeds_both_projections_the_same_state_and_vocab() {
    let d = tmpdir("cli09");
    let lp = d.join("ledger.jsonl");
    let a = args_for(&lp, &["append", "change", LEGAL_CHANGE]);
    assert_eq!(run(&as_refs(&a)).0, 0, "夹具：append 应成功");

    let (c1, out_l, e1) = run(&as_refs(&args_for(&lp, &["project", "language"])));
    let (c2, out_v, e2) = run(&as_refs(&args_for(&lp, &["project", "visual"])));
    assert_eq!(c1, 0, "stderr={e1}");
    assert_eq!(c2, 0, "stderr={e2}");

    let hl = parse_header(&out_l).expect("语言投影首行必须是同源头");
    let hv = parse_header(&out_v).expect("视觉投影首行必须是同源头");
    assert_eq!(hl.world, hv.world, "① 两个投影的 world 必须相同");
    assert_eq!(
        hl.vocab, hv.vocab,
        "② 两个投影的 vocab 必须相同（不同即「读的不是同一份法律」）"
    );
    assert_eq!(
        hl.last_seq, hv.last_seq,
        "③ last_seq 必须相同（不得有一方落后）"
    );
    assert_eq!(hl.state, hv.state, "④ state 指纹必须相同（不得有两个状态）");

    // 逐字：两行**只差** `projection=` 一项
    let la = out_l
        .lines()
        .next()
        .unwrap()
        .replace("projection=language", "projection=X");
    let lb = out_v
        .lines()
        .next()
        .unwrap()
        .replace("projection=visual", "projection=X");
    assert_eq!(
        la, lb,
        "同源头除 projection 外必须逐字一致；实得\n{la}\n{lb}"
    );

    // 命令自报：project check rc=0，且它打印的状态与上面两份首行**同一个**
    let (c3, out3, e3) = run(&as_refs(&args_for(&lp, &["project", "check"])));
    assert_eq!(c3, 0, "stderr={e3}");
    assert!(out3.contains("同源"), "stdout={out3}");
    assert!(
        out3.contains(&format!("last_seq={}", hl.last_seq)),
        "project check 打印的 last_seq 必须与两份首行一致；stdout={out3}"
    );
    assert!(
        out3.contains(&hl.state),
        "project check 打印的 state 指纹必须与两份首行一致；stdout={out3}"
    );
}

/// **cli-15**（`5.5`）：用法串里**列出** `checkpoint write|verify|resume` 三条子命令。
///
/// 为什么单列一条：`src/ontology_instance/checkpoint.rs` 有「整册生产零调用点」的历史（`W-03` / `P-09`）——
/// 接线之后，「用户能不能从帮助里知道这三条存在」就是接线的最后一段：
/// **帮助里没有的用法等于不存在**。
/// 出处：`src/main.rs:28-30`（`USAGE`）与 `:153`（分发到 `cmd_checkpoint`）。
#[test]
fn cli15_usage_lists_three_checkpoint_subcommands() {
    let (code, out, _) = run(&["--help"]);
    assert_eq!(code, 0, "stdout={out}");
    // 判据不是「出现过 checkpoint 这个词」：三条各自要带 **<path> 参数占位**
    // （否则照抄帮助也用不起来 —— 那是「写了但没用」的另一种装饰）
    for sub in ["write", "verify", "resume"] {
        let want = format!("checkpoint {sub} <path>");
        assert!(out.contains(&want), "用法串必须列出 `{want}`；stdout={out}");
    }
    // 正控：分发侧认的也是这三条（未知子命令的错误串里的清单 = 用法串里的清单）
    let d = tmpdir("cli10");
    let lp = d.join("ledger.jsonl");
    let a = args_for(&lp, &["checkpoint", "no-such-sub", "x"]);
    let (code, _, err) = run(&as_refs(&a));
    assert_eq!(code, 1, "未知 checkpoint 子命令应 rc=1；stderr={err}");
    assert!(
        err.contains("write / verify / resume"),
        "分发侧清单必须与用法串一致（否则帮助说的与实际认的不是一套）；stderr={err}"
    );
}

/// **cli-16**（`5.3`）：`Checkpoint::FORMAT` 版本不符 ⇒ 点名 `ext.world.Checkpoint.BadFormat`。
///
/// 该分支此前**零断言**（`src/ontology_instance/checkpoint.rs:94-99`）。做法：写一份**真快照**，
/// 只把 `checkpoint` 版本号改成 999、其余字段一字不动 ⇒ `verify` 与 `resume`
/// 都必须 rc=2 且点名 `BadFormat`。
/// **正控**：未改动的那一份必须 rc=0（否则「报错」可能只是因为快照根本不可用）。
#[test]
fn cli16_checkpoint_format_mismatch_is_named() {
    let d = tmpdir("cli11");
    let lp = d.join("ledger.jsonl");
    let cp = d.join("cp.json");
    let cp_s = cp.display().to_string();

    let a = args_for(&lp, &["append", "change", LEGAL_CHANGE]);
    assert_eq!(run(&as_refs(&a)).0, 0, "夹具：append 应成功");
    let w = args_for(&lp, &["checkpoint", "write", &cp_s]);
    let (code, out, err) = run(&as_refs(&w));
    assert_eq!(
        code, 0,
        "checkpoint write 应成功；stdout={out} stderr={err}"
    );

    // 正控：未改动的快照 ⇒ 核验通过
    let v = args_for(&lp, &["checkpoint", "verify", &cp_s]);
    let (code, _, err) = run(&as_refs(&v));
    assert_eq!(code, 0, "正控：真快照必须核验通过；stderr={err}");

    // 变异夹具：**只**改版本号
    let text = fs::read_to_string(&cp).unwrap();
    let mut doc: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(
        doc["checkpoint"],
        serde_json::json!(1),
        "出厂 FORMAT 必须是 1（否则本条测的不是「版本不符」）"
    );
    doc["checkpoint"] = serde_json::json!(999);
    fs::write(&cp, doc.to_string()).unwrap();

    for sub in ["verify", "resume"] {
        let a = args_for(&lp, &["checkpoint", sub, &cp_s]);
        let (code, out, err) = run(&as_refs(&a));
        assert_eq!(
            code, 2,
            "`checkpoint {sub}` 对版本不符必须 rc=2；stdout={out} stderr={err}"
        );
        assert!(
            err.contains("ext.world.Checkpoint.BadFormat"),
            "`{sub}` 必须点名 BadFormat；stderr={err}"
        );
        assert!(
            err.contains("实得 999"),
            "理由必须报出实际版本号；stderr={err}"
        );
    }
}

/// **cli-17**（`5.4`）：`checkpoint resume` 走的是**未核验续算**路径，靠**事后比对**兜底。
///
/// 判据三段一起，缺一段这条就是装饰：
/// 1. **正控**：未篡改的快照 ⇒ `resume` rc=0（否则下面两条「报错」可能只是因为快照不可用）；
/// 2. 只改 `digest`（不动 `state`）⇒ `verify` 报 `DigestMismatch`（**核验路径**会看它），
///    而 `resume` **rc=0**：它**不核验** —— 这就是「走未核验续算路径」的实测证据；
/// 3. 只改 `state`（不动 `digest`）⇒ `verify` **rc=0**（它只比指纹，不交叉核对 state），
///    而 `resume` 报 `ext.world.Checkpoint.ResumeMismatch` 且 rc=2
///    —— 这就是「由事后比对兜底」的实测证据：快照自己保证不了的事，由账本重算兜住。
///
/// ⚠️ 本用例固定的是**当下**路径形状。若将来把 `resume` 改成「先核验」，
/// 第 2、3 段的断言会红 —— 那是**要人去改规格**的信号，不是可以放宽的地方。
/// 出处：`src/main.rs:556-562`（`resume` 分支里 `fast.to_json() != full.to_json()` 的比对）。
#[test]
fn cli17_checkpoint_resume_falls_back_to_post_hoc_comparison() {
    let d = tmpdir("cli12");
    let lp = d.join("ledger.jsonl");
    let cp = d.join("cp.json");
    let cp_s = cp.display().to_string();

    let a = args_for(&lp, &["append", "change", LEGAL_CHANGE]);
    assert_eq!(run(&as_refs(&a)).0, 0, "夹具：append 应成功");
    let w = args_for(&lp, &["checkpoint", "write", &cp_s]);
    assert_eq!(run(&as_refs(&w)).0, 0, "夹具：checkpoint write 应成功");
    let pristine = fs::read_to_string(&cp).unwrap();

    // ── 判据 1（正控）：未篡改 ⇒ resume rc=0 且自报「一致」 ──
    let r0 = args_for(&lp, &["checkpoint", "resume", &cp_s]);
    let (code, out, err) = run(&as_refs(&r0));
    assert_eq!(code, 0, "正控：未篡改时必须一致；stdout={out} stderr={err}");
    assert!(out.contains("一致"), "stdout={out}");

    // ── 判据 2：只改 `digest` ⇒ verify 报 DigestMismatch；resume **不报**（它没核验） ──
    let mut doc: serde_json::Value = serde_json::from_str(&pristine).unwrap();
    let real_digest = doc["digest"].as_str().unwrap().to_string();
    doc["digest"] = serde_json::json!("fnv1a64:0000000000000000");
    fs::write(&cp, doc.to_string()).unwrap();

    let v = args_for(&lp, &["checkpoint", "verify", &cp_s]);
    let (code, _, err) = run(&as_refs(&v));
    assert_eq!(code, 2, "verify 对指纹不符必须 rc=2；stderr={err}");
    assert!(
        err.contains("ext.world.Checkpoint.DigestMismatch"),
        "verify 必须点名 DigestMismatch；stderr={err}"
    );

    let r = args_for(&lp, &["checkpoint", "resume", &cp_s]);
    let (code, out, err) = run(&as_refs(&r));
    assert_eq!(
        code, 0,
        "resume **不核验**：快照的 digest 被改它也不看（它只用 state ＋ 账本续算）——\
         若这里变成 rc=2，说明 resume 改成了「先核验」，规格要同步改；stdout={out} stderr={err}"
    );
    assert!(
        !err.contains("DigestMismatch"),
        "未核验路径**不得**报核验类错误；stderr={err}"
    );

    // ── 判据 3：只改 `state`（digest 复原）⇒ verify **检不出**；resume 由事后比对报错 ──
    let mut doc: serde_json::Value = serde_json::from_str(&pristine).unwrap();
    doc["digest"] = serde_json::json!(real_digest);
    let before = doc["state"]["objects"]["world://notice/n-1"]["muted"].clone();
    assert_eq!(
        before,
        serde_json::json!(true),
        "夹具：快照里的 muted 应为 true"
    );
    doc["state"]["objects"]["world://notice/n-1"]["muted"] = serde_json::json!(false);
    fs::write(&cp, doc.to_string()).unwrap();

    let v = args_for(&lp, &["checkpoint", "verify", &cp_s]);
    let (code, _, err) = run(&as_refs(&v));
    assert_eq!(
        code, 0,
        "verify 只比「指纹 vs 账本重算」，**不**交叉核对 state 与指纹 —— 故改 state 它检不出；stderr={err}"
    );

    let r = args_for(&lp, &["checkpoint", "resume", &cp_s]);
    let (code, out, err) = run(&as_refs(&r));
    assert_eq!(
        code, 2,
        "resume 对「续算 ≠ 全量重算」必须 rc=2（事后比对兜底）；stdout={out} stderr={err}"
    );
    assert!(
        err.contains("ext.world.Checkpoint.ResumeMismatch"),
        "必须点名 ResumeMismatch（事后比对）；stderr={err}"
    );
}

// ═══════════════════════════════════════════════════════════════════════════
// cli-18 —— ★「在场者名册出口」`presence list`（第 14 轮新增；**只增**）
// ═══════════════════════════════════════════════════════════════════════════

/// 跑一次 `presence list` 并返回 `(退出码, stdout, stderr)`。
fn presence_list(lp: &std::path::Path) -> (i32, String, String) {
    let a = args_for(lp, &["presence", "list"]);
    run(&as_refs(&a))
}

/// **cli-18**：`presence list` 是**世界的**名册，**不是**载体清单——三条判据，条条会红。
///
/// ## 判据
///
/// | # | 情形 | 期望 |
/// |---|---|---|
/// | ① | 世界里**已申报**的 3 个在场者 | **必须都在册**，且每条给出 `name`／`category`／`state`／`last_seen` |
/// | ② | ★ **只在载体里存在、从未向世界申报**的东西 | **不许出现**（夹具里**真造**一份桌面条目） |
/// | ③ | 名册的**每一条** | **都能在世界里找到出处**：该主体在**账本原文**里有对应事件；且名册集合**恰等于**账本里的在场者主体集合 |
///
/// ## 为什么这三条不是同一条的三个说法
///
/// ① 拦「漏列」；② 拦「把载体侧的东西算进世界」——名册一旦去读桌面目录或包管理器数据库，
/// 它就不再是**世界的**名册（那是"两处真相"）；③ 拦「凭空多一条／条目与账本脱钩」，
/// 而且它**拿账本原文独立复核**，不拿名册自己复核自己。
///
/// ## 反例（必红，原始输出见交付回执）
///
/// - `cmd_presence` 多吐一条只在载体里存在的条目（`foot`）⇒ ② 变红；
/// - `cmd_presence` 少吐一条（只报 2 个）⇒ ① 与 ③ 变红；
/// - `cmd_presence` 列一个账本里没有的主体 ⇒ ③ 变红。
///
/// ## 一处**如实**的边界
///
/// 夹具用 `std::env::temp_dir()` 下的**私有子目录**（既有 `tmpdir()` 口径）——**不是**直接把
/// 账本放进 `/tmp`：世界自己的静态墙只看账本**所在目录**的 mode，`/tmp` 本身是 1777 会拒开。
#[test]
fn cli18_presence_list_is_the_world_roster_not_the_carrier_inventory() {
    let d = tmpdir("cli18");
    let lp = d.join("ledger.jsonl");

    // ── 夹具⓪：世界里申报 3 个在场者（每个 4 格，全部用本体**已声明**的 `presence` 字段）──
    const THREE: [(&str, &str); 3] = [
        ("pcmanfm", "file-manager"),
        ("mousepad", "editor"),
        ("firefox", "browser"),
    ];
    for (name, cat) in THREE {
        let subject = format!("world://presence/{name}");
        let bodies = [
            format!(r#"{{"subject":"{subject}","path":"name","before":null,"after":"{name}"}}"#),
            format!(r#"{{"subject":"{subject}","path":"category","before":null,"after":"{cat}"}}"#),
            format!(
                r#"{{"subject":"{subject}","path":"state","before":null,"after":"installed"}}"#
            ),
            format!(
                r#"{{"subject":"{subject}","path":"last_seen","before":null,"after":1791044558}}"#
            ),
        ];
        for b in &bodies {
            let a = args_for(&lp, &["append", "change", b]);
            let (code, out, err) = run(&as_refs(&a));
            assert_eq!(
                code, 0,
                "夹具⓪：申报必须能落账（{b}）；stdout={out} stderr={err}"
            );
        }
    }

    // ── 夹具②：「装在机器上、却从未向世界申报」的东西**真的存在** ──
    //     在夹具里造一份桌面条目（载体侧真有它），而世界侧**一个字节都没收到过**。
    let carrier = d.join("carrier/usr/share/applications");
    fs::create_dir_all(&carrier).unwrap();
    let ghost = carrier.join("foot.desktop");
    fs::write(&ghost, "[Desktop Entry]\nName=foot\nType=Application\n").unwrap();
    assert!(ghost.is_file(), "夹具②：载体侧的桌面条目必须真的建出来了");

    // 世界侧不许有它——否则②那条反例是**假的**（这一条是反例自身的正控）
    let a = args_for(&lp, &["state", "--json"]);
    let (code, sj, err) = run(&as_refs(&a));
    assert_eq!(code, 0, "夹具：state --json 必须 rc=0；stderr={err}");
    let sjv: serde_json::Value = serde_json::from_str(sj.trim()).unwrap();
    assert!(
        sjv["objects"].get("world://presence/foot").is_none(),
        "夹具②：世界里**不许**有 `world://presence/foot`（本条要判的正是「载体里有、世界没有」）"
    );

    // ── 名册 ──
    let (code, out, err) = presence_list(&lp);
    assert_eq!(
        code, 0,
        "`presence list` 必须 rc=0；stdout={out} stderr={err}"
    );

    // 判据①：3 个都在册，且每条给出四格（值按既有读出口口径＝JSON 原样）
    for (name, cat) in THREE {
        let subject = format!("world://presence/{name}");
        assert!(
            out.contains(&subject),
            "判据①：`{subject}` 必须在册；名册=\n{out}"
        );
        let line = out
            .lines()
            .find(|l| l.contains(&subject))
            .unwrap_or_else(|| panic!("判据①：找不到 `{subject}` 那一行；名册=\n{out}"));
        for (f, want) in [
            ("name", format!("\"{name}\"")),
            ("category", format!("\"{cat}\"")),
            ("state", "\"installed\"".to_string()),
            ("last_seen", "1791044558".to_string()),
        ] {
            assert!(
                line.contains(&format!("{f}={want}")),
                "判据①：`{subject}` 那条必须给 `{f}={want}`；实得：{line}"
            );
        }
    }

    // 名册里 `world://presence/` 的条目行（缩进两格、以主体名开头）
    let listed: Vec<&str> = out
        .lines()
        .filter(|l| l.trim_start().starts_with("world://presence/"))
        .collect();

    // ── 判据②（**排在①的计数形态之前**：让②能独立变红，而不是被计数那条抢先）──
    //    只在载体里存在、从未申报的假在场者 ⇒ **不许出现**
    assert!(
        !out.contains("world://presence/foot"),
        "判据②：名册不许出现未申报的假在场者；\n{out}"
    );
    assert!(
        !out.contains("foot"),
        "判据②：名册里不许出现只在载体里存在的名字（名册**不读**桌面目录／包管理器）；\n{out}"
    );

    // ── 判据③ ──
    //    名册的每一条都能在**账本原文**里找到出处；且名册集合恰等于账本里的在场者主体集合。
    let raw = fs::read_to_string(&lp).unwrap();
    let subj_in_ledger: std::collections::BTreeSet<String> = raw
        .lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
        .filter_map(|v| v["body"]["subject"].as_str().map(str::to_string))
        .collect();
    let roster: std::collections::BTreeSet<String> = listed
        .iter()
        .map(|l| l.split_whitespace().next().unwrap().to_string())
        .collect();
    for s in &roster {
        assert!(
            subj_in_ledger.contains(s),
            "判据③：`{s}` 必须在账本原文里有对应事件（出处可查）；账本里的主体={subj_in_ledger:?}"
        );
    }
    let ledger_presences: std::collections::BTreeSet<String> = subj_in_ledger
        .iter()
        .filter(|s| s.starts_with("world://presence/"))
        .cloned()
        .collect();
    assert_eq!(
        roster, ledger_presences,
        "判据③：名册集合必须**恰等于**账本里的在场者主体集合（`presence list` 是算出来的，不是另记的一份）"
    );

    // ── 判据①（**计数形态**：多一条少一条都红）──
    assert_eq!(
        listed.len(),
        3,
        "判据①：名册恰有 3 条（多一条少一条都红）；实得 {listed:?}\n{out}"
    );
    println!("---- cli18 名册原文（现取）----\n{out}");
}
