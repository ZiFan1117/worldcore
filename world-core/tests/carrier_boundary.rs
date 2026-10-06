//! **载体 vs 世界**——把作者刚定的口径钉成判据（本批新增，不换词表身份）。
//!
//! ## 已成立的口径（**不改**，只在这里当判据的依据引用）
//!
//! - **同级不同物**：`systemd` 管**资源**，世界管**说法**；
//! - 架构上内核与 `systemd` 同属第 1 层（内部两截：内核→`systemd`），**语义世界是第 2 层**；
//! - 「系统级／应用级」量的是**依赖轴**，「谁起谁」是**运行轴**——**两条轴不许混**；
//! - 世界**不是应用**（书序逐字：「不能是一个库，不能是一个协议，**不能是一个应用**」）。
//!
//! ## 本文件判什么
//!
//! | 组 | 判据 | 落点 |
//! |---|---|---|
//! | ①a | 本体里（**参与身份**的那一半）不许出现载体专有串 ⇒ 拒启 | **生产代码**：`src/ontology_definition/mod.rs::check_carrier_independence`（用例见 `tests/ontology_elements.rs::m15`） |
//! | ①b | **换掉载体，说法不变**：世界的行为**不取决于 unit 的内容** | 本文件（静态：`src/**` 不引用载体件；动态：换一份诱饵 `deploy/` ⇒ 输出逐字节不变） |
//! | ②a | `deploy/*.service`／`*.socket` 的依赖**不许指向具体应用**（只许自身／内核侧／基础 target） | 本文件（含**反例**：合成一份指向应用的 unit ⇒ 必被点名） |
//! | ②b | **正控**：把所有**应用**都停掉，世界照常 `check` 与折叠 | 本文件（等价形态：**没有任何载体件在场**时，`check` rc=0 且 `state --json` 逐字节相同） |
//! | ④-i | **不许用载体机制表达许可**的一个**可判**切片：`SocketMode`／`SocketUser`／`SocketGroup` **只许**出现在 `.socket`（不许出现在 `.service`） | 本文件 |
//!
//! ## 本文件**判不了**的（如实登记，不假装；详见 `docs/证据/EV-009.md`）
//!
//! - **"把 unit 的依赖顺序当因果用"**：这是**语义**判断。机器只能查到"顺序依赖指向了
//!   **应用单元**"这一**形态**——而那已被 ②a 覆盖。⇒ 更深的"用顺序担保某条世界语义"
//!   **无法判定**（原因：同一条 `After=` 既可读作资源排序、也可被**人**读作因果，
//!   两者的**字面形态完全相同**）。
//! - **"把 socket 权限当许可用"**：同一条 `SocketMode=` 有两种读法（"谁能连" vs "能干什么"），
//!   **字面形态完全相同** ⇒ 除了上面 ④-i 那条形态判据，其余**无法判定**
//!   （本仓口径：套接字权限表达"谁能连"，**"连上能干什么"由服务端按角色判定**——
//!   见 `deploy/README.md` 与 `policy.json` 的授权面）。

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-carrier-{tag}-{n}"));
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

fn deploy_dir() -> PathBuf {
    manifest_dir().join("deploy").join("units")
}

/// 读一个 unit 文件里的**指令行**：`键=值`（忽略注释与空行）。
fn directives(text: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    for ln in text.lines() {
        let s = ln.trim();
        if s.is_empty() || s.starts_with('#') || s.starts_with(';') {
            continue;
        }
        if let Some((k, v)) = s.split_once('=') {
            out.push((k.trim().to_string(), v.trim().to_string()));
        }
    }
    out
}

/// ★ **判据②a**：一份 unit 的**依赖边**里，指向"具体应用"的那些。
///
/// 允许的目标（**白名单要写理由**）：
/// 1. **它自己**——`PartOf=world-core.service` 之于 `world-core.socket` 等；
/// 2. **内核侧单元**（本仓 `deploy/` 里给出的内核定义）：`world-core.service`／`world-core.socket`；
/// 3. **systemd 的标准 target／slice**（`*.target`／`*.slice`／`-.mount`）——它们是**资源轴**的
///    汇合点，不是某个应用。
///
/// 其余的一律算"指向具体应用" ⇒ 红。**为什么这么划**：「谁起谁」是**运行轴**、
/// 「系统级／应用级」是**依赖轴**；一个单元去 `Requires=`／`After=` 某个**应用**，
/// 就是把**应用间的依赖**写进了载体层——而载体层的本分是**管资源**，不是编排应用。
fn app_dependencies(
    name: &str,
    text: &str,
    kernel_units: &BTreeSet<String>,
) -> Vec<(String, String)> {
    const DEP_KEYS: &[&str] = &[
        "Requires",
        "Requisite",
        "Wants",
        "BindsTo",
        "PartOf",
        "After",
        "Before",
        "Conflicts",
    ];
    let mut bad = Vec::new();
    for (k, v) in directives(text) {
        if !DEP_KEYS.contains(&k.as_str()) {
            continue;
        }
        for target in v.split_whitespace() {
            if target == name {
                continue; // 它自己
            }
            if kernel_units.contains(target) {
                continue; // 内核侧
            }
            if target.ends_with(".target") || target.ends_with(".slice") || target == "-.mount" {
                continue; // systemd 标准汇合点（资源轴）
            }
            bad.push((k.clone(), target.to_string()));
        }
    }
    bad
}

/// 本仓 `deploy/` 里给出的**内核侧**单元名（从文件名推，**不写死两份副本**）。
fn kernel_units_from(dir: &Path) -> BTreeSet<String> {
    let mut s = BTreeSet::new();
    if let Ok(rd) = fs::read_dir(dir) {
        for e in rd.flatten() {
            let n = e.file_name().to_string_lossy().to_string();
            if n.starts_with("world-core.") && (n.ends_with(".service") || n.ends_with(".socket")) {
                s.insert(n);
            }
        }
    }
    s
}

/// ★ **判据④-i**：`SocketMode`／`SocketUser`／`SocketGroup` **只许**出现在 `.socket`。
fn socket_perm_directives_outside_socket_units(name: &str, text: &str) -> Vec<String> {
    const PERM_KEYS: &[&str] = &["SocketMode", "SocketUser", "SocketGroup"];
    if name.ends_with(".socket") {
        return Vec::new(); // `.socket` 里是**合法**用法（白名单，理由见文件头 ④-i）
    }
    directives(text)
        .into_iter()
        .filter(|(k, _)| PERM_KEYS.contains(&k.as_str()))
        .map(|(k, _)| k)
        .collect()
}

/// 跑一次 CLI，返回 `(rc, stdout+stderr)`。
fn run_cli(args: &[&str]) -> (i32, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = Command::new(bin).args(args).output().expect("跑得起来");
    let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
    txt.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), txt)
}

// ───────────────────────── 判据②a：反向验证 ＋ 扫真件 ─────────────────────────

/// **②a**：依赖指向**具体应用** ⇒ 必被点名；指向**自身／内核侧／标准 target** ⇒ 不点名。
///
/// 反例（合成夹具）＋ 正控（合成夹具）＋ **扫本仓真实 `deploy/`** 三件一起。
#[test]
fn c01_unit_dependencies_must_not_point_at_applications() {
    let kernel: BTreeSet<String> = [
        "world-core.service".to_string(),
        "world-core.socket".to_string(),
    ]
    .into_iter()
    .collect();

    // 反例①：依赖一个**应用**单元 ⇒ 必被点名
    let bad = "\
[Unit]
Description=夹具：把一个应用的依赖写进了载体层
Requires=some-app.service
After=some-app.service

[Service]
ExecStart=/bin/true
";
    let hits = app_dependencies("fixture.service", bad, &kernel);
    assert!(
        hits.iter()
            .any(|(k, t)| k == "Requires" && t == "some-app.service"),
        "指向应用的 `Requires=` 必须被点名，实得：{hits:?}"
    );
    assert!(
        hits.iter()
            .any(|(k, t)| k == "After" && t == "some-app.service"),
        "指向应用的 `After=` 必须被点名，实得：{hits:?}"
    );

    // 正控①：指向**自身** ⇒ 不点名（`world-core.socket` 的 `PartOf=world-core.service` 同形）
    let own = "[Unit]\nPartOf=world-core.service\n";
    assert!(
        app_dependencies("world-core.service", own, &kernel).is_empty(),
        "指向**自身**不该被点名"
    );

    // 正控②：指向**内核侧**与**标准 target** ⇒ 不点名
    let ok = "\
[Unit]
Requires=world-core.socket
After=world-core.socket network.target sysinit.target
Wants=world-core.service
";
    let h = app_dependencies("world-core-actd.service", ok, &kernel);
    assert!(
        h.is_empty(),
        "内核侧单元与标准 target 不该被点名（**两条轴不许混**：资源轴的目标是汇合点），实得：{h:?}"
    );

    // 扫**本仓真实** `deploy/`：今天指得到应用的 ⇒ 红。
    // ⚠️ 若 `deploy/` 不在（那是**他人在飞**的目录，可能被移走）⇒ **如实说明并只跑合成夹具**，
    //    不把"读不到"读成"没有违规"。
    let dd = deploy_dir();
    if !dd.is_dir() {
        eprintln!(
            "[登记] 本仓 `{}` 不存在 ⇒ ②a **扫不了真实载体件**（只跑了合成夹具）。\
             这不是『没有违规』，是『无件可扫』。",
            dd.display()
        );
        return;
    }
    let kernel_units = kernel_units_from(&dd);
    assert!(
        !kernel_units.is_empty(),
        "`deploy/` 里必须能认出内核侧单元（`world-core.service`／`.socket`）；否则白名单是空的"
    );
    let mut offenders = Vec::new();
    for e in fs::read_dir(&dd).unwrap().flatten() {
        let p = e.path();
        let n = e.file_name().to_string_lossy().to_string();
        if !(n.ends_with(".service") || n.ends_with(".socket")) {
            continue;
        }
        let text = fs::read_to_string(&p).unwrap();
        for (k, t) in app_dependencies(&n, &text, &kernel_units) {
            offenders.push(format!("{n}: {k}={t}"));
        }
    }
    assert!(
        offenders.is_empty(),
        "载体件的依赖**不许指向具体应用**（运行轴与依赖轴不许混）：{offenders:?}"
    );
}

/// **②b · 正控**：**把所有应用都停掉**，世界照常 `check` 与折叠。
///
/// 本环境里没有常驻的应用进程可停 ⇒ 用它的**等价形态**（更强）：让世界里
/// **一份载体件都不在场**（诱饵 `deploy/` 里全是垃圾 unit），断言
/// `check` **rc=0**、`state --json` 与"正常 cwd"下**逐字节相同**。
#[test]
fn c02_with_every_application_down_the_world_still_checks_and_folds_the_same() {
    let d = tmpdir("c02");
    let lp = d.join("ledger.jsonl");
    // 先落一条真事件（用出厂配置）
    {
        let ont = manifest_dir().join("src/ontology_definition/ontology.json");
        let pol = manifest_dir().join("src/gate/policy.json");
        let (rc, out) = run_cli(&[
            "--ontology",
            ont.to_str().unwrap(),
            "--ledger",
            lp.to_str().unwrap(),
            "--policy",
            pol.to_str().unwrap(),
            "append",
            "change",
            r#"{"subject":"world://notice/n-1","path":"muted","before":null,"after":true}"#,
        ]);
        assert_eq!(rc, 0, "落一条真事件必须成功：{out}");
    }

    let ont = manifest_dir().join("src/ontology_definition/ontology.json");
    let pol = manifest_dir().join("src/gate/policy.json");
    let args_base: Vec<String> = vec![
        "--ontology".into(),
        ont.display().to_string(),
        "--ledger".into(),
        lp.display().to_string(),
        "--policy".into(),
        pol.display().to_string(),
    ];
    let mut check_args: Vec<&str> = args_base.iter().map(String::as_str).collect();
    check_args.push("check");
    let mut state_args: Vec<&str> = args_base.iter().map(String::as_str).collect();
    state_args.extend(["state", "--json"]);

    // ① 正常 cwd（仓根 `world-core/`）——那里**有**真 `deploy/`
    let (rc1, check1) = run_cli(&check_args);
    let (rc2, state1) = run_cli(&state_args);
    assert_eq!(rc1, 0, "有载体件在场时 `check` 必须 rc=0：{check1}");
    assert_eq!(rc2, 0, "有载体件在场时 `state` 必须 rc=0：{state1}");

    // ② 诱饵 cwd：一份**全是垃圾**的 `deploy/`（应用全停、载体件全换）
    let decoy = tmpdir("c02-decoy");
    // ★ 诱饵沙盒**镜像仓内布局**：单元在 `deploy/units/`
    let dd = decoy.join("deploy").join("units");
    fs::create_dir_all(&dd).unwrap();
    fs::write(
        dd.join("junk.service"),
        "[Unit]\nRequires=some-app.service\n[Service]\nExecStart=/bin/false\n",
    )
    .unwrap();
    fs::write(dd.join("junk.socket"), "[Socket]\nListenStream=/tmp/x\n").unwrap();

    let bin = env!("CARGO_BIN_EXE_world-core");
    let run_in = |cwd: &Path, args: &[&str]| -> (i32, String) {
        let out = Command::new(bin)
            .args(args)
            .current_dir(cwd)
            .output()
            .expect("跑得起来");
        let mut txt = String::from_utf8_lossy(&out.stdout).to_string();
        txt.push_str(&String::from_utf8_lossy(&out.stderr));
        (out.status.code().unwrap_or(-1), txt)
    };
    let (rc3, _check2) = run_in(&decoy, &check_args);
    let (rc4, state2) = run_in(&decoy, &state_args);
    assert_eq!(rc3, 0, "**应用全停／载体件全换**时 `check` 仍必须 rc=0");
    assert_eq!(rc4, 0, "同上，`state` 仍必须 rc=0");

    // ★ 判据①b 的核心：**说法不取决于载体** ⇒ 两次的 `state --json` 必须**逐字节相同**
    assert_eq!(
        state1, state2,
        "换掉载体的内容后 `state --json` **必须逐字节不变**——\
         变了就说明世界的说法取决于载体（同级不同物被混成一条轴）"
    );
}

/// **①b（静态面）**：`src/**` 里**不许**把载体目录 `deploy/` **当路径用**。
///
/// ## 判什么（**认结构，不搜字样**——第一版在这里吃过假阳性）
///
/// 第一版把 `".socket"` 当**裸串**扫，结果 `src/carrier/kernel.rs` 的
/// `&self.socket`（**Rust 字段访问**）被当成"代码引用了载体件" ⇒ **假阳性**。
/// ⇒ 今天在判的**只有一条**（执行体＝本件 `walk`）：**同一行**里既出现 `deploy/`
/// 又出现一个"会去读/建路径的调用"（`IO_CALLS`）⇒ 判红；注释里的指路**不判**。
///
/// ## ★ 今天**不判**的那一半（如实登记；不许读成"已覆盖"）
///
/// **机制名**（`systemd`／`.service`／`.socket`／`ListenStream`／`WantedBy`）**只查字符串字面量内部**
/// —— 这一半**今天没有执行体**：`walk` 里没有它；本件的 `string_literals` 是它的**备料**，
/// 今天**未接上线**（只靠一行 `let _ = string_literals;` 保留，不参与判定）。
/// ⇒ **不许**据本判据声称"`src/**` 里连载体机制名都没有"。
/// **为什么没判**：本件**没留下说明**——`walk` 里就是没有这一半（本席**只登记，不猜原因**）。
/// **落点**：`world-core/docs/证据/EV-009.md` §六 第 18 条（「`c03` 的射程（未闭合的那一半）」）
/// 是这一半的既有登记处；⚠️ 该条**今天的文字把这一半写成了"在判"**，与本件现状不符，
/// **订正权在该件**——本件**只登记，不改它**。
///
/// ## 它今天能支撑到哪儿（如实声明）
///
/// 动态面（`c02`）证明"输出不随载体变"；本判据只证"**代码里没有把 `deploy/` 当路径用**"
/// ⇒ 两条合起来**只排除**"读了 `deploy/` 而恰好结果相同"这一支，
/// **不排除**"按载体机制名去读"（那一半今天不判，见上一节）。
///
/// ⚠️ **射程（如实声明）**：它证的是"**没有以 `deploy/` 路径的形式出现**"。
/// 一个**运行时从配置里读来的路径**（例如 `--channel` 指向的渲染件）**不在**本判据内——
/// 那种情形由"接入映射的权威在 `policy.json`"那条既有口径管（见 `EV-009` 的登记）。
#[test]
fn c03_world_sources_never_read_the_carrier_units() {
    /// 一行里所有**字符串字面量**的内容（含 `\"` 转义；不处理原始字符串 `r#"…"#`，
    /// 若将来出现原始字符串，本判据会**漏**——如实登记）。
    fn string_literals(line: &str) -> Vec<String> {
        let mut out = Vec::new();
        let mut cur = String::new();
        let mut inside = false;
        let mut chars = line.chars().peekable();
        while let Some(c) = chars.next() {
            match c {
                '\\' if inside => {
                    if let Some(n) = chars.next() {
                        cur.push(n);
                    }
                }
                '"' => {
                    if inside {
                        out.push(std::mem::take(&mut cur));
                    }
                    inside = !inside;
                }
                _ if inside => cur.push(c),
                _ => {}
            }
        }
        out
    }

    let src = manifest_dir().join("src");

    // ★ **唯一的一处豁免**：`src/ontology_definition/mod.rs` 里那张**载体专有串表**（`const TOKENS`）——
    //   判据要**禁**这些词，就得先**知道**这些词。豁免**只**覆盖那一张表的行区间
    //   （**现算区间**，不写死行号、不写死命中数）；表外再出现一处 ⇒ 必红。
    let guard_file = src.join("ontology_definition/mod.rs");
    let guard_text = fs::read_to_string(&guard_file).unwrap();
    let (tok_lo, tok_hi) = {
        let lines: Vec<&str> = guard_text.lines().collect();
        let lo = lines
            .iter()
            .position(|l| l.contains("const TOKENS: &[&str]"))
            .expect("守卫里必须有那张载体专有串表（否则本豁免是空话）");
        let hi = lines[lo..]
            .iter()
            .position(|l| l.trim() == "];")
            .map(|k| lo + k)
            .expect("那张表必须有配对的 `];`");
        (lo + 1, hi + 1) // 1-based，闭区间
    };

    let mut hits: Vec<String> = Vec::new();
    // ★ **第二处豁免：`src/main.rs` 的 `USAGE` 帮助文本块**（现算行区间，不写死）。
    //   为什么必须豁免：用户在终端里**要看到**"`serve` 是 `deploy/units/world-core.service` 的
    //   `ExecStart` 指向的东西"——那是**说给人听的话**，不是"世界在读那个件"；
    //   而判据的主张是**后者**。⇒ 与本体那张载体串表同一处置：**结构化、现算**的豁免，
    //   而不是"凡字符串字面量都放过"（那会把判据变成空的）。
    let main_file = src.join("main.rs");
    let main_text = fs::read_to_string(&main_file).unwrap();
    let (help_lo, help_hi) = {
        let lines: Vec<&str> = main_text.lines().collect();
        match lines.iter().position(|l| l.contains("const USAGE: &str")) {
            None => (usize::MAX, usize::MAX),
            Some(i) => {
                let lo = i + 1;
                let hi = lines[i..]
                    .iter()
                    .position(|l| l.contains("\";"))
                    .map(|k| i + k + 1)
                    .unwrap_or(lo);
                (lo, hi)
            }
        }
    };

    fn walk(
        dir: &Path,
        guard: &Path,
        span: (usize, usize),
        mainf: &Path,
        help: (usize, usize),
        out: &mut Vec<String>,
    ) {
        for e in fs::read_dir(dir).unwrap().flatten() {
            let p = e.path();
            if p.is_dir() {
                walk(&p, guard, span, mainf, help, out);
                continue;
            }
            if !p.extension().map(|x| x == "rs").unwrap_or(false) {
                continue;
            }
            let rel = p
                .strip_prefix(manifest_dir())
                .unwrap()
                .display()
                .to_string();
            let is_guard = p == *guard;
            let is_main = p == *mainf;
            for (i, ln) in fs::read_to_string(&p).unwrap().lines().enumerate() {
                let n = i + 1;
                // 两处**结构化**豁免：守卫自己那张载体串表；说给人听的帮助文本。
                if is_guard && n >= span.0 && n <= span.1 {
                    continue;
                }
                if is_main && n >= help.0 && n <= help.1 {
                    continue;
                }
                let s = ln.trim_start();
                let is_comment = s.starts_with("//") || s.starts_with("/*") || s.starts_with('*');
                if is_comment {
                    continue;
                }
                // ★ **判据（第三次收窄，如实留痕）**：`deploy/` 出现在**引用它去读的行** ⇒ 红。
                //
                // 三版怎么走到这里的（每一版都是被**自己人**误伤后收窄的，不是"为了好看放宽"）：
                // - v1「裸串扫机制名」⇒ 误伤 `&self.socket`（Rust 字段访问）——**搜字样 ≠ 认结构**；
                // - v2「`deploy/` 不许出现在代码里」⇒ 误伤 `USAGE` 帮助文本与错误消息
                //   （**命名一个件 ≠ 读它**；而 Rust 里"读文件"与"打印路径"**字面都是字符串**）；
                // - v3（本版）：只在**同时出现"会去读/建路径"的调用**时才判 ⇒
                //   这才是"**世界在读载体件**"这条主张的**可判形态**。
                //
                // ⚠️ 如实登记射程：它**不是**数据流分析——若把路径先存进变量再读（`let p = "deploy/x";`
                // 另起一行 `fs::read_to_string(p)`），本判据**抓不到**。那一格**无法判定**（原因：
                // 需要跨行数据流），登记在 `docs/证据/EV-009.md`，**不假装**覆盖。
                const IO_CALLS: &[&str] = &[
                    "read_to_string",
                    "read_dir",
                    "read_link",
                    "File::open",
                    "include_str!",
                    "include_bytes!",
                    "Path::new",
                    "PathBuf::from",
                    "metadata(",
                ];
                let has_path = ln.contains("deploy/") || ln.contains("deploy\\");
                let uses_it = IO_CALLS.iter().any(|c| ln.contains(c));
                if has_path && uses_it {
                    out.push(format!(
                        "{}:{} —— 代码里把载体目录**当路径用**（世界不该读载体件）：{}",
                        rel,
                        n,
                        ln.trim()
                    ));
                }
            }
        }
    }
    walk(
        &src,
        &guard_file,
        (tok_lo, tok_hi),
        &main_file,
        (help_lo, help_hi),
        &mut hits,
    );
    assert!(
        hits.is_empty(),
        "`src/**` 里把**载体目录当路径用**（世界不该读载体件）。\
         射程（如实登记）：只认**同一行**出现「路径 ＋ 会去读/建路径的调用」这一形；\
         跨行数据流（先存变量再读）**抓不到**，那一格登记为**无法判定**。命中：\n{}",
        hits.join("\n")
    );
    // 正控（反假）：判定器**确实会红**，且**确实不会误伤**——两半都用**同一条**判据。
    const IO: &[&str] = &[
        "read_to_string",
        "read_dir",
        "read_link",
        "File::open",
        "include_str!",
        "include_bytes!",
        "Path::new",
        "PathBuf::from",
        "metadata(",
    ];
    let hit = |ln: &str| {
        (ln.contains("deploy/") || ln.contains("deploy\\")) && IO.iter().any(|c| ln.contains(c))
    };
    // 不该红的两形（都是**说给人听**或**注释**，世界没读任何东西）：
    let fake_comment = "// 指路：见 deploy/README.md";
    let fake_msg = "eprintln!(\"为什么：`deploy/units/world-core.socket` 把套接字交给载体\");";
    assert!(!hit(fake_comment), "注释里的指路**不许**被当成违规");
    assert!(
        !hit(fake_msg),
        "**说给人听的文本**（错误消息/帮助）里命名一个件**不许**被当成'世界在读它'"
    );
    // 该红的那一形（世界真的去读它）：
    let fake_bad = "let t = fs::read_to_string(\"deploy/units/world-core.service\").unwrap();";
    assert!(
        hit(fake_bad),
        "判定器必须能抓到合成违规（否则上面那句『0 命中』是恒真实现）"
    );
    let _ = string_literals; // 保留该助手：**今日仅备料、无调用点**（机制名那一半今天没有执行体，见件头）
}

/// **④-i**：`SocketMode`／`SocketUser`／`SocketGroup` **只许**出现在 `.socket` 单元里。
///
/// **为什么这条可判**：把"权限"写在 `.service` 上，就是拿**载体机制**（unit 指令）去表达
/// **服务的能力面**——而本仓口径是「套接字权限表达**谁能连**；**连上能干什么**由服务端
/// 按角色判定」（`deploy/README.md`）。⇒ 那三个指令的**合法落点只有 `.socket`**。
///
/// **为什么只判这一半**：「同一条 `SocketMode=` 是'谁能连'还是'能干什么'」**字面相同**、
/// 机器分不出 ⇒ 其余**无法判定**（如实登记，见文件头）。
#[test]
fn c04_socket_permission_directives_belong_only_to_socket_units() {
    // 正控：`.socket` 里出现 ⇒ 合法
    let sock = "[Socket]\nListenStream=/run/world-core/world.sock\nSocketMode=0660\nSocketUser=world-core\n";
    assert!(
        socket_perm_directives_outside_socket_units("world-core.socket", sock).is_empty(),
        "`.socket` 里的权限指令是**合法**用法（白名单：它说的正是'谁能连'）"
    );
    // 反例：`.service` 里出现 ⇒ 必被点名
    let svc = "[Service]\nSocketMode=0660\nSocketUser=world-core\nExecStart=/bin/true\n";
    let hits = socket_perm_directives_outside_socket_units("some.service", svc);
    assert!(
        hits.contains(&"SocketMode".to_string()) && hits.contains(&"SocketUser".to_string()),
        "`.service` 里的 socket 权限指令必须被点名，实得：{hits:?}"
    );

    // 扫真件（若在）
    let dd = deploy_dir();
    if !dd.is_dir() {
        eprintln!("[登记] `deploy/` 不存在 ⇒ ④-i **扫不了真实载体件**（只跑了合成夹具）。");
        return;
    }
    let mut offenders = Vec::new();
    for e in fs::read_dir(&dd).unwrap().flatten() {
        let p = e.path();
        let n = e.file_name().to_string_lossy().to_string();
        if !(n.ends_with(".service") || n.ends_with(".socket")) {
            continue;
        }
        let text = fs::read_to_string(&p).unwrap();
        for k in socket_perm_directives_outside_socket_units(&n, &text) {
            offenders.push(format!("{n}: {k}="));
        }
    }
    assert!(
        offenders.is_empty(),
        "socket 权限指令只许出现在 `.socket` 里：{offenders:?}"
    );
}
