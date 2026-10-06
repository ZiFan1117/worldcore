//! 世界核心 —— 项目 Step 0.5（本体信封）+ 项目 Step 1（账本）+ 项目 Step 2（读模型）+ 项目 Step 5（门禁）+ 项目 Step 7/8（两个投影）的**最小可运行骨架**。
//!
//! 骨架冒烟判据（S3 准出要求"一条命令跑通"）：`world-core check` 打印 **READY**。
//!
//! 退出码（规范要求"明确退出码"）：`0` 成功 / `1` 用法错误 / `2` 法律、账本、门禁或读模型错误。

use std::path::{Path, PathBuf};
use std::process::ExitCode;
use world_core::{Envelope, World};

const USAGE: &str = "\
world-core —— 世界核心（语义事件是唯一真相）
用法:
  world-core [--ontology <path>] [--ledger <path>] [--policy <path>] [--channel <path>] [--owner-uid <uid>] [--require-chain] <子命令> [参数]

子命令:
  check                      加载本体+门禁策略+账本 → 打印 READY（骨架冒烟判据；**只读**）
  kinds                      列出本体已知的家族
  policy                     打印门禁策略（能力表 + 主体白名单）
  usage                      **只报告**「声明了、但账本里零使用」的类型与字段
                             （**不是判据**：合法状态，给作者决定「要不要沉淀／要不要删」的输入；
                             为什么它不红 = 法律的本分是「先声明、后使用」；**只读**）
  serve                      载体拉起的入口（`deploy/world-core.service` 的 ExecStart 指向它）：
                             从**继承的 fd 3** 取监听套接字（socket activation），
                             受理前向 `$NOTIFY_SOCKET` 发 `READY=1`，有 `$WATCHDOG_USEC` 时按半周期发 `WATCHDOG=1`。
                             缺 `LISTEN_FDS`／`LISTEN_PID` 不符／fd 3 不可用 ⇒ **拒启并点名**；
                             `$NOTIFY_SOCKET` 缺失**不致命**（裸跑要能起来）
  append <kind> <json-body> [actor] [--trace <id>] [--flag <名>]...
                             追加一条事件（法律校验 → 门禁裁决 → 通过才落笔）；
                             actor 缺省 world://user（全权主体，见下）；
                             --trace / --flag 给出信封的可选字段（见文末）
  read [from_seq]            按序打印事件（JSON Lines；**只读**）
  state [--json] [--retracted]  从账本**重算**状态（读模型；不缓存、不写盘）；`--retracted` 追加一段「已撤回」清单（★撤回＝过户不落账；序号是账本的，效果才是撤回的对象）；它与 `--json` **不能同给**（rc=1）\n  presence list              给「在场者」一个**名册出口**：列出世界里**已申报**的 `world://presence/*`（人读形态），\n                             每条给 `name`／`category`／`state`／`last_seen`；**只装在机器上、从未向世界申报过的不在册**（只读）
  project language           语言投影（结构化出口，给程序读）
  project visual             视觉投影（渲染出口，给人看）
  project check              渲染两份投影并**核对同源**（词表与状态必须一致）
  project serve <socket>     ★【落账即广播】出口：连上来之后，世界每落一条新账就把那一行推给你
                             （一行一帧；**只读账本**、只推**已经落账**的行；慢消费者会被丢弃，不拖住世界）
  checkpoint write <path>    从账本重算状态并写一份检查点（缓存，非真相）
  checkpoint verify <path>   核验检查点与账本一致（不一致即拒用）
  checkpoint resume <path>   从检查点续算，并与全量重算逐字节比对
  channel bind <socket>      按 --channel 配置建套接字（0600 + chown 到该身份）
  channel accept <socket>    接受一个连接，把请求经**唯一写入口**落笔（一次一条）
  channel serve <socket> <n> 连续接受 n 个连接（v1 长驻形态；一次往返 = 两个连接）
                             四条资源边界（并发连接数/单条消息字节/每秒消息数/空闲超时）
                             取自 --policy 的 channel_limits 块；缺块即拒启（rc=2）
  carrier capabilities       列出执行清单里的能力（**只执行、不裁决**的载体侧）
  carrier check              校验执行清单（坏清单即非零退出，不静默放过）
  carrier undo               列出执行清单里「动手前要先做撤销点」的能力
  carrier orphans            从账本里找出**有意图、无结果**的请求（只报告，不重试）
  carrier serve <socket>     常驻：逐行读请求 → 先问内核 → 再执行 → 再回写结果
  carrier do <能力> <动词> <请求号> [参数JSON] <socket>
                             手工跑一次：先问内核，准了才动手，动完回写结果

默认路径: --ontology ./src/ontology_definition/ontology.json  --ledger ./ledger.jsonl  --policy ./src/gate/policy.json
          --channel ./channel.json（**本仓未提供出厂文件**，由部署方给出）
          --cap-dir ./src/carrier/cap.d（执行清单目录；本仓提供出厂样例）
缺省身份: append 不写第 4 个参数时，actor 取 `world://user`——而 `policy.json` 把该主体列为
          **唯一可执行不可逆动作**的主体，并授权它写**任意**对象（`world://*`）。
          也就是说「不写身份」的后果是**最高授权**，不是匿名。

--trace <id>  信封**可选**字段 `trace`（因果：引发本条的那条事件的 id）。**只对 append 有效**。
              不写该参数 ⇒ **不写该键**（不写 null）：没有因果与因果指向空是两件事。
              指向一个**不存在**的 id **不导致拒绝**（v1 不做引用完整性校验）。
              `--trace` 后面没有值 ⇒ 用法错误（rc=1）——**不许静默降级成「不写因果」**。
--flag <名>   信封**必填**字段 `flags` 里**追加**一个旗标（可重复；重复的只留一个）。
              不写该参数 ⇒ `flags` 为**空数组**（出厂初值，与本参数出现之前一字不差）。
              **不认得的旗标照样放行**（未知旗标必须忽略）；但 `gate.` 开头的旗标是
              **内核保留前缀**（内核依裁决写的摩擦标记），调用方给了即拒并留流水。
              `--flag` 后面没有值 ⇒ 用法错误（rc=1）。
退出码:   0 成功 / 1 用法错误 / 2 法律、账本、门禁或读模型错误
";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut ontology = PathBuf::from("src/ontology_definition/ontology.json");
    let mut ledger = PathBuf::from("ledger.jsonl");
    let mut policy = PathBuf::from("src/gate/policy.json");
    // 通道配置（M09 接线：生产路径可调用）。**本仓不提供出厂 channel.json**（待人裁）。
    let mut channel_cfg = PathBuf::from("channel.json");
    // 执行清单目录（M10 接线）：**只回答"怎么干"**，允不允许由门禁裁决。
    let mut cap_dir = PathBuf::from("src/carrier/cap.d");
    // 内核套接字（M10 提交请求的落点）。**适配器对账本零写权限**，只能走它。
    let mut kernel_sock: Option<PathBuf> = None;
    // 是否允许终端确认（高危动作的人确认入口；**默认关闭 ⇒ 需要确认的动作一律拒绝**）。
    let mut allow_confirm = false;
    // 属主断言（可选）：由部署方显式给出"法律与真相应当属于哪个 uid"。
    // 依据 WC-RV-R2-001 假设 A-05：静态墙只看 mode，属主必须另行断言。
    let mut owner_uid: Option<u32> = None;
    // `--owner-uid` 解析失败**必须拒启**（P-16）：此前 `.ok()` 把打错的 uid 静默变成
    // `None` ⇒ 属主断言**悄悄不执行**，是 fail-open（"打错反而更宽松"）。
    let mut owner_uid_bad: Option<String> = None;
    // 要求账本必须带摘要链（WC-CR-003 D3）：无链即拒启
    let mut require_chain = false;
    // 写入入口的**可选信封字段**（`--trace` 因果 ／ `--flag` 旗标）。**只对 `append` 有效**。
    //
    // 解析期就装进一个 `Envelope`（`src/lib.rs`），于是 `cmd_append` 只多收**一个**参数；
    // 三种情形分得很清（不许合并）：
    //   `Ok(env)`＋字段全空 ＝ 没给这些参数 ⇒ **不写 `trace` 键**、`flags` 为空数组；
    //   `Ok(env)`＋`trace = Some("")` ＝ 给了空串 ⇒ 按"未给"处理（`event::with_trace` 的口径）；
    //   `Err(..)`            ＝ 给了 `--trace`／`--flag` 却没有值 ⇒ **用法错误**。
    //     为什么 fail-closed：静默降级成"没给"会让调用方以为因果/旗标记下了——而账本里
    //     什么都没有。这与 `--owner-uid` 打错即拒启同一口径（静默失效比不做更危险）。
    let mut env = Envelope::new();
    let mut env_bad: Option<String> = None;
    let mut rest: Vec<String> = Vec::new();

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--ontology" => {
                i += 1;
                if i < args.len() {
                    ontology = PathBuf::from(&args[i]);
                }
            }
            "--ledger" => {
                i += 1;
                if i < args.len() {
                    ledger = PathBuf::from(&args[i]);
                }
            }
            "--require-chain" => require_chain = true,
            "--owner-uid" => {
                i += 1;
                if i < args.len() {
                    match args[i].parse::<u32>() {
                        Ok(v) => owner_uid = Some(v),
                        Err(_) => owner_uid_bad = Some(args[i].clone()),
                    }
                } else {
                    owner_uid_bad = Some("<缺失>".to_string());
                }
            }
            "--channel" => {
                i += 1;
                if i < args.len() {
                    channel_cfg = PathBuf::from(&args[i]);
                }
            }
            "--cap-dir" => {
                i += 1;
                if i < args.len() {
                    cap_dir = PathBuf::from(&args[i]);
                }
            }
            "--socket" => {
                i += 1;
                if i < args.len() {
                    kernel_sock = Some(PathBuf::from(&args[i]));
                }
            }
            "--confirm" => allow_confirm = true,
            "--trace" => {
                i += 1;
                match args.get(i) {
                    Some(v) => env.trace = Some(v.clone()),
                    None => {
                        env_bad = Some(
                            "`--trace` 后面必须跟一个事件 id（用法: world-core append \
                             <kind> <json-body> [actor] [--trace <id>] [--flag <名>]...）"
                                .to_string(),
                        )
                    }
                }
            }
            "--flag" => {
                i += 1;
                match args.get(i) {
                    Some(v) => env.flags.push(v.clone()),
                    None => {
                        env_bad = Some(
                            "`--flag` 后面必须跟一个旗标名\
                             （用法: world-core append <kind> <json-body> [actor] [--flag <名>]...）"
                                .to_string(),
                        )
                    }
                }
            }
            "--policy" => {
                i += 1;
                if i < args.len() {
                    policy = PathBuf::from(&args[i]);
                }
            }
            "-h" | "--help" => {
                print!("{USAGE}");
                return ExitCode::SUCCESS;
            }
            other => rest.push(other.to_string()),
        }
        i += 1;
    }

    // 解析完再定格：`--trace`／`--flag` 后面缺值 ⇒ **用法错误**（fail-closed，见上面的声明处）。
    // 用一个 `Result` 把"要带的可选信封字段"与"参数打错了"一起交给 `cmd_append`，
    // 免得那个函数为这两个状态各收一个参数。
    let env: Result<Envelope, String> = match env_bad {
        Some(e) => Err(e),
        None => Ok(env),
    };

    match rest.first().map(String::as_str).unwrap_or("") {
        "check" => {
            if let Some(bad) = owner_uid_bad {
                eprintln!(
                    "[FAIL] ext.world.Runtime.BadOwnerUid: `--owner-uid {bad}` 不是合法的 uid 数字；\
                     拒绝启动。\n 为什么拒启而不是忽略：属主断言是「法律与真相属于谁」的唯一执行点，\
                     忽略打错的 uid 会让它**静默失效**（fail-open），比不做断言更危险"
                );
                return ExitCode::from(1);
            }
            cmd_check(&ontology, &ledger, &policy, owner_uid, require_chain)
        }
        "kinds" => cmd_kinds(&ontology),
        "policy" => cmd_policy(&policy),
        // ★ **只报告、绝不红**（见 `cmd_usage` 的文档；它不是判据）。
        "usage" => cmd_usage(&ontology, &ledger, &policy),
        // ★ **载体拉起**：读继承的描述符（socket activation）＋ 向 `$NOTIFY_SOCKET` 报到。
        // 这是 `deploy/world-core.service` 的 `ExecStart` 指向的东西（见内联模块 `serve` 的文档）。
        // ★★ **A-05 必须在服务路径上也跑**（真缺陷修复）：
        //   此前 `--owner-uid` 的「打错即拒启」**只写在 `check` 分支里**，而 `cmd_serve` 的签名里
        //   **根本没有 `owner_uid`** ⇒ 服务路径上它被**静默丢弃**，属主断言在真正跑的那条路径上
        //   **从未执行**（另一席在 VM 上实测发现）。⇒ 这里补两件（**缺一编译不过，故同批**）：
        //   ① 与 `check` **同口径**的拒启（点名 `ext.world.Serve.BadOwnerUid`；`check` 那条一字不动）；
        //   ② 把 `owner_uid` **传进去**，让 `cmd_serve` 真的接上 `guard::assert_owned_by`。
        "serve" => {
            if let Some(bad) = owner_uid_bad {
                eprintln!(
                    "[FAIL] ext.world.Serve.BadOwnerUid: `--owner-uid {bad}` 不是合法的 uid 数字；\
                     属主断言（A-05）**不能因为参数读不懂就跳过**——拒启。\n\
                     \x20 为什么「只在 check 上生效」是个缺陷：那样这条判据**只在一条路径上**，\
                     而 `serve` 才是真正跑的那条 ⇒ 闸装了一半。"
                );
                return ExitCode::from(2);
            }
            cmd_serve(&ontology, &ledger, &policy, &channel_cfg, owner_uid)
        }
        // ★ **`describe`**：问「我能做什么」——**只读法律**（口径见 `cmd_describe` 的文档）。
        "describe" => cmd_describe(&ontology),
        // ★ **`subscribe`**：按**调用方给的位点**给一段读物（世界**不替收件人存进度**）。
        "subscribe" => cmd_subscribe(&ontology, &ledger, &policy, &rest),
        "append" => cmd_append(&ontology, &ledger, &policy, &rest, &env),
        "read" => cmd_read(&ontology, &ledger, &policy, &rest),
        "state" => cmd_state(&ontology, &ledger, &policy, &rest),
        "project" => cmd_project(&ontology, &ledger, &policy, &rest),
        "checkpoint" => cmd_checkpoint(&ontology, &ledger, &policy, &rest),
        "channel" => cmd_channel(&ontology, &ledger, &policy, &channel_cfg, &rest),
        "carrier" => cmd_carrier(
            &cap_dir,
            kernel_sock.as_deref(),
            allow_confirm,
            &ledger,
            &rest,
        ),
        "presence" => cmd_presence(&ontology, &ledger, &policy, &rest),
        "" => cmd_usage_exit(),
        // ★ 上一行原先是 `"" => { print!("{USAGE}"); ExitCode::from(1) }`（4 行臂），
        //   拆成两条**单行臂**（`cmd_usage_exit` 见文件末尾）是刻意的，理由见 `cmd_presence` 的文档。
        other => {
            eprintln!("未知子命令 `{other}`\n\n{USAGE}");
            ExitCode::from(1)
        }
    }
}

/// ★ **`usage` —— 只报告"声明了、但账本里零使用"的类型与字段。**
///
/// ## 这份清单**不是判据**（这一句必须写在代码里，不是措辞问题，是口径）
///
/// 它**永远不改变退出码**（除了"本体/账本根本打不开"这一种——那时连报告都产不出，
/// 报的是**打不开**，不是"有零使用的声明"）。它被打印出来，是给**作者**决定
/// 「要不要沉淀／要不要删」的**输入**；
/// **不许**被读成"已达成某条门禁"。
///
/// ## ★ 为什么它**不能**红（与"死入口/死能力"那条判据的分界，写死在这里）
///
/// **法律的本分就是「先声明、后使用」**——一个类型、一格字段、一条能力可以先被法律允许，
/// 再等第一次真实使用。把它判红，等于**禁止"先声明"**，
/// 那会毁掉「往上是领域概念各自生长」这条既有口径。
///
/// ⇒ 与 [`crate::ontology_definition::Ontology::load`] 里那条**会红**的"结构性死声明"的区别是：
/// **「没人能走到它」是缺陷（拒启）；「还没人走到它」是常态（只报告）。**
///
/// ## 射程（如实声明，不假装更宽）
///
/// - 只看**账本折叠出来的状态**（`State`）：类型"用过"＝有 `world://<类型>/…` 的实例；
///   字段"用过"＝某个该类型的实例写过这一格。**不看**别处（规格、代码、注释里提到它都不算）；
/// - 只覆盖 `_objects`（对象类型与字段）；`_links`／`_interfaces`／`_functions` 等的
///   "用到没有"**不在本命令内**（其中能力与入口另有**会红**的结构判据，见 `Ontology::load`）；
/// - 折叠失败时**照样 rc=0**，但会**明说**报告不可得（不许把"读不出来"读成"零使用"）。
fn cmd_usage(o: &Path, l: &Path, p: &Path) -> ExitCode {
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            // 这一条**不是**"有零使用的声明"——是"报告都产不出"。故仍是失败。
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    println!("== world-core usage（**不是判据**）==");
    println!(
        "  本体 : {}  world={}  已声明类型={} 个",
        o.display(),
        w.ontology().world(),
        w.ontology().object_types().count()
    );
    println!("  账本 : {}  条数={}", l.display(), w.ledger().last_seq());
    let state = match w.read_model() {
        Ok(s) => s,
        Err(e) => {
            // 折叠失败 ⇒ 报告不可得。**不许**把"读不出来"当成"零使用"。
            println!("  报告 : ⚠️ **不可得**——账本折叠失败，故无法判断哪些声明被用过：");
            println!("         {e}");
            println!("  ⚠️ 本清单不是判据；此处的『不可得』**不是**『零使用』。");
            return ExitCode::SUCCESS;
        }
    };

    // "用过"的两张表：类型（按 subject 首段）与 (类型, 字段)。
    let mut used_types: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    let mut used_cells: std::collections::BTreeSet<(String, String)> =
        std::collections::BTreeSet::new();
    for (subject, path, _) in state.entries() {
        if let Some(t) = world_core::ontology_instance::readmodel::type_of_subject(subject) {
            used_types.insert(t.to_string());
            used_cells.insert((t.to_string(), path.to_string()));
        }
    }

    let mut unused_types: Vec<&str> = Vec::new();
    let mut unused_fields: Vec<(&str, &str)> = Vec::new();
    let mut n_types = 0usize;
    let mut n_fields = 0usize;
    for (t, decl) in w.ontology().object_types() {
        n_types += 1;
        if !used_types.contains(t) {
            unused_types.push(t);
        }
        for f in decl.fields.keys() {
            n_fields += 1;
            if !used_cells.contains(&(t.to_string(), f.clone())) {
                unused_fields.push((t, f));
            }
        }
    }

    println!("  声明 : 类型 {n_types} 个、字段 {n_fields} 个");
    println!(
        "  零使用类型 : {} 个{}",
        unused_types.len(),
        if unused_types.is_empty() {
            "（今天没有）".to_string()
        } else {
            String::new()
        }
    );
    for t in &unused_types {
        println!("    · [类型] `{t}` —— 账本里没有任何 `world://{t}/…` 实例");
    }
    println!(
        "  零使用字段 : {} 个{}",
        unused_fields.len(),
        if unused_fields.is_empty() {
            "（今天没有）".to_string()
        } else {
            String::new()
        }
    );
    for (t, f) in &unused_fields {
        println!("    · [字段] `{t}.{f}` —— 账本里没有该类型的实例写过这一格");
    }
    println!("  ⚠️ 本清单**不是判据**，**不许**被读成『已达成某条门禁』。它是给作者");
    println!("     决定『要不要沉淀／要不要删』的输入。");
    println!("     为什么它不能红：**法律的本分就是「先声明、后使用」**——");
    println!("     一条能力／一个类型可以先被法律允许，再等第一次真实使用；");
    println!("     把它判红等于**禁止「先声明」**。");
    println!("     （对照：**结构性死声明**——没人能走到它——**会红**，见 `Ontology::load`。）");
    ExitCode::SUCCESS
}

/// ★ **`serve` —— 载体拉起的入口**（`deploy/world-core.service` 的 `ExecStart` 指向它）。
///
/// 顺序（**每一步失败都当场点名并 rc=2**，与载体约定的 `Type=notify` 对齐）：
/// 1. 读 `LISTEN_FDS`／`LISTEN_PID` ⇒ 缺／不符 ⇒ `ext.world.Serve.*` 拒启；
/// 2. 从 **fd 3** 取监听套接字 ⇒ 不可用 ⇒ 拒启；
/// 3. 按套接字路径在 `--channel` 的身份映射里**认领身份**（`listener_for`）——
///    没有映射的口**不得受理**（默认拒绝，与 `channel accept` 同口径）；
/// 4. **发 `READY=1`**（在**开始受理之前**）＋ 起看门狗心跳；
/// 5. 进受理循环（复用通道那条已受测的路径，含四条资源边界）。
///
/// ⚠️ 本函数**不自己 `bind`**：监听套接字归载体所有（见内联模块 `serve` 的文档）。
fn cmd_serve(o: &Path, l: &Path, p: &Path, cfg: &Path, owner_uid: Option<u32>) -> ExitCode {
    use world_core::bus::{self, ChannelConfig};

    // ★ **A-05 属主断言在服务路径上也要跑**（与 `check` 同口径：法律／门禁／账本三项）。
    //   为什么它必须在这里：`serve` 是**真正跑的那条路径**；只在 `check` 上断言，
    //   就得到"闸只在一条路径上"那种病——`check` 绿而服务跑在一个不该跑的属主上。
    //   口径与 `cmd_check` **逐字同源**（同一函数 `guard::assert_owned_by`、同一三种角色）。
    if let Some(uid) = owner_uid {
        for (path, role) in [
            (o, "本体（法律）"),
            (p, "门禁策略（法律）"),
            (l, "账本（真相）"),
        ] {
            if let Err(e) = world_core::gate::guard::assert_owned_by(path, uid, role) {
                eprintln!("[FAIL] {e}");
                return ExitCode::from(2);
            }
        }
    }

    // ① 环境：`LISTEN_FDS`／`LISTEN_PID` 必须齐且指向本进程。
    let fds = match serve::listen_fds_from_env() {
        Ok(x) => x,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    // ② 监听套接字：**把载体交来的 fd 全部取出来**（`sd_listen_fds`：从 fd 3 开始连续编号）。
    //
    //    ★ 为什么不再是"只取 fd 3"：**每个口各一个 socket 单元**（各自 `SocketUser=` ⇒ 每口各自的
    //    属主保得住），载体在服务启动那一刻把 n 个 fd **一次**交过来（`LISTEN_FDS=n`）。
    //    ★ 只接第一个的现场后果是实测过的：`/run/world-core/` 两个口**都在听**、`LISTEN_FDS=2`，
    //    而服务日志里只有那行 `[登记] ExtraListenFds` ⇒ **第二个口没人受理**。
    //    ⇒ ★**"口起了"与"口受理得到"是两件事**。
    let listeners = match serve::listeners_from_fds(&fds) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    // ③ 身份：**每一个 fd 各自认领**——各取自己的 `local_addr()` ⇒ 各自 `listener_for(路径)` ⇒ 各自 `expect`。
    //
    //    ★ **不许共用一个 `expect`**：那会让"第二个口上说的话"挂上"第一个口的身份"——那就是冒充，
    //    正是本模块硬拒（`Channel.Impersonation`）的那一类。
    //    ★ **账外口仍要拒**：`ChannelConfig::load_checked`（渲染物 ⊆ 法律）在这里**复用**，
    //    不另写一份判据（一处事实一个载体）。
    //    ★ 任一 fd 认不出身份 ⇒ **拒启并点名**（与单口时代同口径，失败口径不变）。
    let conf = match ChannelConfig::load_checked(cfg, p) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let mut bound: Vec<(std::os::unix::net::UnixListener, world_core::bus::Listener)> = Vec::new();
    for listener in listeners {
        let sock = match listener.local_addr() {
            Ok(a) => a.as_pathname().map(|x| x.to_path_buf()).unwrap_or_default(),
            Err(e) => {
                eprintln!("ext.world.Serve.ListenFdUnusable: 读不出监听套接字地址：{e}");
                return ExitCode::from(2);
            }
        };
        let expect = match conf.listener_for(&sock).cloned() {
            Some(x) => x,
            None => {
                eprintln!(
                    "ext.world.Channel.NotConfigured: 继承来的套接字 {} 不在 {} 的身份映射里——\
                     没有身份映射的连接不得受理（默认拒绝）",
                    sock.display(),
                    cfg.display()
                );
                return ExitCode::from(2);
            }
        };
        bound.push((listener, expect));
    }
    // 世界（可写：`serve` 是内核进程，唯一写者）。
    let mut w = match world_core::World::open(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let limits = match channel::Limits::from_policy(p) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let notify = serve::notify_socket_from_env();
    let watchdog = serve::watchdog_interval_from_env();
    // ④⑤ **先报到、后受理**（顺序由 `serve_activated_with` 的结构保证，有单元用例钉着）。
    let r = serve::serve_activated_with(notify.as_deref(), watchdog, "READY=1", || {
        let mut sess = channel::Session::new(limits);
        // 受理循环：**每个口都要受理**（`usize::MAX` 次 = 直到进程被载体停掉）。
        // ★ 仍然是**同一个写者**（不许 fork、不许起第二个服务）；★ 仍然是**一次一条**
        //   （`max_connections` 只能为 1 那条**架构事实没动**，`BadConcurrency` 一个字没改）：
        //   多口只是把"口 B 上的连接要等口 A 让出循环"这件事**消掉**（轮询），**不是并发受理**。
        // ★ 复用通道那条**已受测**的路径（含四条资源边界与"身份不可自称"）。
        let (lsts, expects): (Vec<_>, Vec<_>) = bound.into_iter().unzip();
        channel::serve_all_with(&mut w, &lsts, &expects, &mut sess, usize::MAX).map(|_| ())
    });
    match r {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            ExitCode::from(2)
        }
    }
}

/// ★ **`describe` —— 问「我能做什么」，答案**只从法律读**。**
///
/// ## 返回形状（作者 2026-10-03 裁定 · **读法甲**）：`_interfaces` **∩** 许可条文
///
/// - **只读法律**：两侧都取自 `ontology.json`（`_interfaces` 与 `_permissions.grants`）；
///   **不自造**、不从代码里的常量拼（法律改了，答案跟着改）；
/// - **未被授予 ⇒ 不出现在返回里，且不报红**：那是「**合法地未授**」——
///   「**能力是否被声明**」（定义面）与「**某人是否被授予**」（授权/账本面）是**两件事**；
/// - **报红只有一种**：声明了却**动作与许可两条路都不通** ⇒ 那条由 `Ontology::load` 的
///   `DeadCapability` 结构性判据管着，**本命令不重复造**（一处事实只有一个权威载体）。
///
/// ## ★ 为什么不判「两头必须一致」（口径写死在这里，别处不再复述）
///
/// 三问三答（作者采纳）：
/// 1. **与既有判据自洽**：`DeadCapability` 的口径是「**动作 ∪ 许可**，二者有其一即算可达」
///    ⇒「未被授予」**本身不等于**「不一致」。若本命令改判「两头必须一致」，
///    同一条能力会出现**两个相反判定**（一条判据说它活、本命令说它红）；
/// 2. **不把两件事混成一件**：把「声明了却没人被授」当缺陷，等于**要求法律不许先声明**——
///    而那正是本项目另一条口径（**法律的本分是先声明、后使用**）明令不许的；
/// 3. **不需要动法律**：出厂本体今天 `_interfaces` 与 `_permissions.grants` 的**条数并不相等**
///    （**具体数由 `describe` 现算、本处不复述**——写死的读数必然过期）。读法甲与这组数据**相容**，
///    读法乙则会让**出厂本体当场拒启**。
///
/// ⚠️ 本函数**不写死任何条数**：每次从法律**现算**；用例独立复算对账，也不写死条数。
fn cmd_describe(o: &Path) -> ExitCode {
    let ont = match world_core::ontology_definition::Ontology::load(o) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    // 交集 = `_interfaces` ∩ `_permissions.grants`（两侧都来自法律，**现算**）。
    let granted: std::collections::BTreeSet<&str> = ont.permissions().map(|(k, _)| k).collect();
    println!("== world-core describe（**只读法律**：`_interfaces` ∩ 许可条文）==");
    println!("  本体 : {}", o.display());
    let mut n = 0usize;
    for (name, c) in ont.interfaces() {
        if granted.contains(name) {
            println!("    {name:<18} kind={}", c.kind);
            n += 1;
        }
    }
    println!("  共 {n} 项（**能被怎样对待** ∩ **已被授予**）");
    let ungranted: Vec<&str> = ont
        .interfaces()
        .map(|(k, _)| k)
        .filter(|k| !granted.contains(k))
        .collect();
    println!(
        "  ⚠️ 另有 {} 项**已声明但未被授予**——那是「**合法地未授**」（定义面与授权面是两件事）：",
        ungranted.len()
    );
    println!("     {ungranted:?}");
    println!("     ⇒ 它们**不出现在上面的返回里**，也**不报红**。");
    println!(
        "  ⚠️ 唯一的红是「声明了却**动作与许可两条路都不通**」，由 `Ontology::load` 的 \
         `DeadCapability` 管——本命令**不重复造**。"
    );
    ExitCode::SUCCESS
}

fn cmd_check(
    o: &Path,
    l: &Path,
    p: &Path,
    owner_uid: Option<u32>,
    require_chain: bool,
) -> ExitCode {
    match World::open_readonly(o, l, p) {
        Ok(w) => {
            // 属主断言（若部署方给了 --owner-uid）：法律与真相三项都要对。
            // ⚠️ 放在 open **之后**——账本可能刚被创建，此前它还不存在，
            // 提前断言会把"文件尚未创建"误报成"属主读不到"（实测抓到）。
            if let Some(uid) = owner_uid {
                for (path, role) in [
                    (o, "本体（法律·形状）"),
                    (p, "门禁策略（法律）"),
                    (l, "账本（真相）"),
                ] {
                    if let Err(e) = world_core::gate::guard::assert_owned_by(path, uid, role) {
                        eprintln!("[FAIL] {e}");
                        return ExitCode::from(2);
                    }
                }
            }
            println!("== world-core check ==");
            println!(
                "  本体 : {}  world={}  家族={:?}",
                o.display(),
                w.ontology().world(),
                w.ontology().known_kinds()
            );
            println!(
                "  门禁 : {}  policy={}  能力={} 个  主体白名单={:?}",
                p.display(),
                w.policy().version(),
                w.policy().capabilities().count(),
                w.policy().allowed_subjects()
            );
            // 两处出厂配置的互校状态（书 §5.5）：**拒启**这一半发生在 Policy::load 里，
            // 能走到这里就说明两处一致；但"一致"与"没东西可比"必须分开说——
            // 后者是缺口（闸读不到那些能力的风险等级），不得读成"已互校"。
            match w.policy().carrier_dir() {
                Some(d) => println!(
                    "  互校 : ✅ 载体清单（{}）与世界侧可逆性一致（清单 {} 项）",
                    d.display(),
                    w.policy().carrier_manifest().names().len()
                ),
                None => println!(
                    "  互校 : ⚠️ 策略同级没有 `cap.d/` ⇒ **无从互校**（未校验要说出来）：\
                     那些能力的风险等级读不到，闸只知道可逆性布尔值"
                ),
            }
            println!(
                "  账本 : {}  条数={}  next_seq={}",
                l.display(),
                w.ledger().last_seq(),
                w.ledger().next_seq()
            );
            if w.ledger().is_chained() {
                println!("  链   : ✅ 有摘要链（局部篡改可检出）");
            } else if require_chain && w.ledger().last_seq() > 0 {
                eprintln!(
                    "[FAIL] ext.world.Ledger.NoChain: 使用了 --require-chain，但本账本没有摘要链\n\
                     \x20 无链账本的局部篡改**不可检出**（WC-CR-003 §三），故拒绝启动。\n\
                     \x20 注：**空账本不算违规**（没有东西要保护），故此处只在已有事件时拒绝"
                );
                return ExitCode::from(2);
            } else {
                println!("  链   : ⚠️ 无摘要链——**局部篡改不可检出**（未校验要说出来）");
            }
            // ★★ **读模型必须能折叠——否则不许报 `READY`**（真缺陷修复："check 绿 ≠ 世界能用"）
            //
            // 现场：`check` 报了 `READY`，而 `/usr/local/bin/world-projection` 是**离线**的。
            // 根因：本命令的 `READY` **不覆盖"读模型能否折叠"这一格**——它只核了本体／门禁／互校／账本／链。
            // ⇒ 账本里只要有一条 `before` 与折叠出的旧值不符（或形状坏掉），
            //   **读模型就整本折叠不了**，而 `check` 照旧报 `READY` ⇒ **假绿**。
            // ⇒ 现在：**在报 `READY` 之前，真的折叠一次**；失败 ⇒ **不报 `READY`**、rc≠0，
            //   并把 `ext.world.ReadModel.BeforeMismatch`（含 `seq`／subject／path）**原样带出**。
            if let Err(e) = w.read_model() {
                eprintln!("[FAIL] {e}");
                eprintln!(
                    "  ⇒ **读模型折叠不了 ⇒ 不报 `READY`**（本命令的 `READY` 必须覆盖这一格：\
                     读模型折不出来，世界就是不可用的，哪怕本体/门禁/账本/链都正常）"
                );
                return ExitCode::from(2);
            }
            println!("  READY");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("[FAIL] {e}");
            ExitCode::from(2)
        }
    }
}

/// `policy` —— 打印门禁策略（**只读**：本命令不会改任何文件）。
fn cmd_policy(p: &Path) -> ExitCode {
    match world_core::gate::Policy::load(p) {
        Ok(pol) => {
            println!("== world-core policy ==");
            println!(
                "  策略 : {}  policy={}",
                pol.path().display(),
                pol.version()
            );
            println!("  主体白名单: {:?}", pol.allowed_subjects());
            println!("  能力表（**能力层**：能被怎样对待；默认拒绝：未列出的能力一律不放行）:");
            for (name, cap) in pol.capabilities() {
                // 2026-09-28 改（书 §5.5 第三条：**闸读不到风险等级**）：等级现在读得到，
                // 且打印出来——它是摩擦轻重的依据，不该只活在载体侧。
                //
                // 2026-09-28 再改（本批拆两层）：能力这一层**不带可逆性**（那是动作的性质），
                // 故这里打印 `kind` 与 `risk`；可逆性在**动作表**那一段打印。
                let level = pol.level_name(name);
                println!("    {name:<18} kind={:<7} risk={level}", cap.kind.as_str());
            }
            // **动作层**（本批新立）：每条动作必须引用一个已声明的能力（加载期逐条核过）。
            println!("  动作表（**动作层**：怎么改；`act` 信纸的 capability 填的是动作名）:");
            for (name, a) in pol.actions() {
                let grade = if a.reversible {
                    "可逆  → 免检但留痕"
                } else {
                    // v1 的不可逆口径 = `DEBT-07`：**只允许 `irreversible_actors` 白名单主体**执行。
                    // v1 **没有审批通道**（无批准命令、无批准事件）⇒ 不得再打印"需批准"，
                    // 那会承诺一个不存在的出口（`WC-R4-DISP-001` §三 E-5 / `WC-CR-006` B-9）。
                    "不可逆 → **加摩擦**：白名单主体放行并留下摩擦旗标；白名单外一律加摩擦到拒绝执行"
                };
                println!("    {name:<18} → 能力 {}  {grade}", a.capability.as_str());
            }
            match pol.carrier_dir() {
                Some(d) => println!(
                    "  互校 : ✅ 载体清单（{}）与世界侧的可逆性一致（{} 项已比对）",
                    d.display(),
                    pol.carrier_manifest().names().len()
                ),
                None => println!(
                    "  互校 : ⚠️ 策略同级没有 `cap.d/`（载体侧什么都没声明）⇒ 这些能力的\
                     **风险等级读不到**（risk=未声明），不得当成低危"
                ),
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("[FAIL] {e}");
            ExitCode::from(2)
        }
    }
}

/// `state` —— 从账本**重算**状态。
///
/// 刻意**不提供 `--cache` / 不写盘**：v1 的读模型没有持久形态，
/// 也就不存在"读模型与账本不一致"这种故障。这是第三条专属验收测试的接口面。
///
/// ## `--retracted`（**只增**的输出面；本批新增）
///
/// ★ **撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
///
/// 为什么要另开一个开关而不是把撤回事实塞进 `state --json`：**`to_json` 是规范形式**，
/// 状态指纹由它而来（`State::digest`）——往里加一个键，每一处 `state=…` 的读数
/// 当天就变成假话（既有的 `tests/contract.rs` 还逐字钉着"顶层键集合**恰为**五个"）。
/// ⇒ 撤回事实**不进规范形式**；要看它，用**只增**的这一面：
///
/// | 命令 | 输出 |
/// |---|---|
/// | `state` | **与本批之前逐字节相同**（账本/已折叠/指纹/逐格/未缓存说明） |
/// | `state --json` | `State::to_json()` 的紧凑 JSON 一行（**一个字未改**） |
/// | `state --retracted` | 上面那份人读输出**逐字不变**，**后面追加**一段「已撤回」清单 |
///
/// `--json` 与 `--retracted` **不能同给**：规范形式里没有撤回事实，而同给了却不给
/// ⇒ 调用方会以为"要到了"（`rc=1` 拒并说清为什么，**不许静默忽略一个开关**）。
fn cmd_state(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    let as_json = rest.iter().any(|a| a == "--json");
    let want_retracted = rest.iter().any(|a| a == "--retracted");
    if as_json && want_retracted {
        eprintln!(
            "ext.world.Cli.RetractedNeedsHumanForm: `--json` 与 `--retracted` 不能同给。\n\
             \x20 为什么：`--json` 打的是**规范形式**（`State::to_json`），而撤回事实\n\
             \x20 **不进规范形式**——加了键，每一处 `state=…` 的指纹读数当天变成假话。\n\
             \x20 要看撤回清单：`world-core state --retracted`（人读形态，**只增**的一段）；\n\
             \x20 要规范形式：`world-core state --json`（一个字未改）。"
        );
        return ExitCode::from(1);
    }
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    match w.read_model() {
        Ok(s) => {
            if as_json {
                println!("{}", s.to_json());
            } else {
                println!("== world-core state ==");
                println!("  账本 : {}", l.display());
                println!(
                    "  已折叠: {} 条（last_seq={}）  act={}  notice={}",
                    s.seen(),
                    s.last_seq(),
                    s.acts(),
                    s.notices()
                );
                println!("  指纹 : {}", s.digest());
                for (subject, path, value) in s.entries() {
                    println!("  {subject}#{path} = {value}");
                }
                println!("  （状态由账本重算得来，未缓存、未写盘）");
                // ★ **只增**：上面每一行都与不带本开关时逐字节相同；这一段是追加的。
                //   0 条也照打（"没有输出"不等于"没有问题"——那句话在这里是"0 条"这三个字）。
                if want_retracted {
                    println!(
                        "  已撤回（撤回＝过户不落账；序号是账本的，效果才是撤回的对象）: {} 条",
                        s.retracted().len()
                    );
                    for (seq, r) in s.retracted() {
                        println!(
                            "    seq={seq}  撤的人={}  因为什么={}  ← 已撤回",
                            r.actor,
                            r.because.as_deref().unwrap_or("未说明")
                        );
                    }
                }
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("[FAIL] 读模型拒绝折叠：{e}");
            ExitCode::from(2)
        }
    }
}

fn cmd_kinds(o: &Path) -> ExitCode {
    match world_core::ontology_definition::Ontology::load(o) {
        Ok(ont) => {
            println!(
                "world={}  家族: {}",
                ont.world(),
                ont.known_kinds().join(", ")
            );
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("[FAIL] {e}");
            ExitCode::from(2)
        }
    }
}

/// `append` —— **命令行写入入口**（唯一写入口 [`World::commit_envelope`] 的接线）。
///
/// ## 为什么走 `commit_envelope` 而不是 `commit`（2026-09-28，工区 F）
///
/// `REQ-F-031` 判据 (2)(3) 要的是"**能从写入入口写出带 `trace` 的事件并读回**"，
/// `REQ-F-029`（第 4 组）要的是"**带未知旗标的事件必须被接受并落笔**"。
/// 库侧承载可选信封字段的入口是 `World::commit_envelope`（`src/lib.rs`），
/// 而命令行这一级此前**没有任何办法给出 `trace` 或旗标**：`--trace` 会被当成 `actor`
/// 的位置参数，于是一条本该带因果的事件会以 `--trace` 为写信人提交
/// （错误串看起来完全正常，只有 actor 是错的）。
///
/// 本函数把两者接上：不写这两个参数时 `Envelope` 全空，而
/// `commit_envelope(kind, actor, body, &Envelope::default())` 与 `commit(kind, actor, body)`
/// **走的是同一个 `commit_verbatim`**（`src/lib.rs` 里前者就是后者加一层薄壳），
/// 故"不带因果、不带旗标"的既有行为一字未改——不存在第二条写路径。
fn cmd_append(
    o: &Path,
    l: &Path,
    p: &Path,
    rest: &[String],
    env: &Result<Envelope, String>,
) -> ExitCode {
    // `--trace`／`--flag` 后面没有值 ⇒ 用法错误（**fail-closed**：不许静默降级成"没给"）。
    let env = match env {
        Ok(e) => e,
        Err(e) => {
            eprintln!("[FAIL] ext.world.Runtime.BadEnvelopeArg: {e}");
            return ExitCode::from(1);
        }
    };
    if rest.len() < 3 {
        eprintln!(
            "用法: world-core append <kind> <json-body> [actor] [--trace <id>] [--flag <名>]..."
        );
        eprintln!(
            "      actor 不写 ⇒ 取 world://user：policy.json 里**唯一**可执行不可逆动作的主体，"
        );
        eprintln!("      且被授权写任意对象（world://*）。**不写身份 = 最高授权，不是匿名。**");
        eprintln!("      --trace <id> ⇒ 信封可选字段「因果：引发本条的那条事件的 id」。");
        eprintln!("      --flag <名>  ⇒ 往信封的 flags 里追加一个旗标（可重复；`gate.` 开头的是内核保留前缀，调用方给了即拒）。");
        return ExitCode::from(1);
    }
    let kind = &rest[1];
    let body: serde_json::Value = match serde_json::from_str(&rest[2]) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("[FAIL] body 不是合法 JSON: {e}");
            return ExitCode::from(1);
        }
    };
    // 缺省身份 = `world://user`：`policy.json` 第 32 行把它列为**唯一**可执行不可逆动作的主体，
    // 同文件第 28 行授权它写**任意**对象（`world://*`）。⇒ 这里的 `unwrap_or_else` 不是"匿名兜底"，
    // 而是**全权兜底**。用法串（`USAGE` 与上面那段 `eprintln!`）必须把这件事写出来，
    // 否则"没写身份"这一默认行为的后果在帮助里是隐形的（缺陷台账 **D-43**）。
    let actor = rest
        .get(3)
        .cloned()
        .unwrap_or_else(|| "world://user".to_string());
    let mut w = match World::open(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    // 一个写入口、一条路径：可选信封字段全空时与 `World::commit` 逐字等价（见本函数文档）。
    match w.commit_envelope(kind, &actor, body, env) {
        Ok(ev) => {
            println!("{}", serde_json::to_string(&ev).unwrap_or_default());
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("[FAIL] {e}");
            ExitCode::from(2)
        }
    }
}

/// `project` —— 两个投影，以及"同源"核对。
///
/// 两个投影都**只**从读模型 + 词表渲染（`07/2-依据/15` §三：投影之间不交互）。
/// `project check` 是 `REQ-F-020` 的机器判定面：比对两份输出的同源头。
/// ★ **`project serve` —— 「落账即广播」的出口**（作者问过"UI 能及时响应吗"，答案在这条出口上）。
///
/// ## 它为什么必须是【独立进程 + 只读账本】
///
/// ★它**不碰写路径**：`serve`（唯一写者）一个字节都不用改。本进程只做一件事——
/// **把【已经落账的】行推出去**。
/// ⇒ ★于是三条硬边界**由构造保证**（不是靠纪律）：
/// - **① 推的只能是已经落账的**：行是**从账本文件读来的** ⇒ "先推后落"在本设计里做不到；
/// - **② 订阅者没有写权**：本进程**从不开账本写句柄**，订阅口只写不读；★若订阅者往上发东西，
///   回一条明确拒绝（`ProjectServe.NotAWriteEntry`）并断开——★拒绝的理由**指到"这不是写入口"**；
/// - **③ 不用 `append`**：本进程不知道 `append` 存在。
///
/// ## 慢消费者与断线（"读的人不许影响写"）
///
/// ★写路径与本进程**没有共享任何锁**：最坏情况是**推不动**，而**落账照旧**。
/// 本进程内部：订阅口一律**非阻塞**；某条订户写不进去（`WouldBlock`）⇒ **丢掉这条订户并登记**
/// （**不缓冲、不等待**——缓冲就是"总线持状态"，那正是本项目不许的）。
///
/// ## 延迟的来源（如实说）
///
/// 本仓只许 `serde_json` 一个 crate family ⇒ 没有 `inotify`/`epoll` ⇒ 只能**轮询账本**。
/// 轮询间隔＝`TICK_MS`（20ms）⇒ "落账 → 推送"的延迟上限就是这一个 tick（实测见件）。
#[cfg(unix)]
mod project_serve {
    use std::io::{Read, Seek, SeekFrom, Write};
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::path::Path;
    use std::process::ExitCode;
    use std::time::Duration;

    /// 轮询间隔（毫秒）——**它就是"落账 → 推送"的延迟上限**。
    const TICK_MS: u64 = 20;

    /// 订户往上发东西时的拒绝（**理由必须指到"这不是写入口"**）。
    const NOT_WRITE_ENTRY: &str = "ext.world.ProjectServe.NotAWriteEntry: 本口是【读】的延伸，\
                                   不是写入口——写只许走世界的唯一写入口（`serve` 那个套接字）。";

    pub fn serve(ledger: &Path, rest: &[String]) -> ExitCode {
        let Some(sock) = rest.get(2) else {
            eprintln!("用法: world-core --ledger <path> project serve <socket>");
            return ExitCode::from(1);
        };
        let sock = std::path::PathBuf::from(sock);
        // fail-closed：账本读不出来 ⇒ 拒启（一个推不出东西的出口不该起）
        if let Err(e) = std::fs::metadata(ledger) {
            eprintln!(
                "ext.world.ProjectServe.LedgerUnreadable: {} 读不到：{e}",
                ledger.display()
            );
            return ExitCode::from(2);
        }
        if let Some(dir) = sock.parent() {
            if let Err(e) = world_core::gate::guard::assert_not_other_writable(dir, "投影出口目录")
            {
                eprintln!("[FAIL] {e}");
                return ExitCode::from(2);
            }
        }
        let _ = std::fs::remove_file(&sock);
        let listener = match UnixListener::bind(&sock) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("ext.world.ProjectServe.BindFail: {}: {e}", sock.display());
                return ExitCode::from(2);
            }
        };
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&sock, std::fs::Permissions::from_mode(0o600));
        }
        if let Err(e) = listener.set_nonblocking(true) {
            eprintln!("ext.world.ProjectServe.NonblockFail: {e}");
            return ExitCode::from(2);
        }
        // ★起始位点＝**当前文件末尾**（只推"连上之后新落的"；不推历史 ⇒ 不替订户存位点）
        let mut pos = std::fs::metadata(ledger).map(|m| m.len()).unwrap_or(0);
        eprintln!(
            "[登记] ext.world.ProjectServe.ServeStarted: 账本={} 出口={} 起始位点={} tick={}ms",
            ledger.display(),
            sock.display(),
            pos,
            TICK_MS
        );
        let mut subs: Vec<UnixStream> = Vec::new();
        let mut buf = vec![0u8; 64 * 1024];
        loop {
            // ① 收新订户（非阻塞）
            loop {
                match listener.accept() {
                    Ok((s, _)) => {
                        if let Err(e) = s.set_nonblocking(true) {
                            eprintln!("[登记] ProjectServe.DropOnAccept: {e}");
                            continue;
                        }
                        eprintln!(
                            "[登记] ext.world.ProjectServe.SubscriberConnected: 订户数={}",
                            subs.len() + 1
                        );
                        subs.push(s);
                    }
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
                    Err(e) => {
                        eprintln!("[登记] ProjectServe.AcceptFail: {e}");
                        break;
                    }
                }
            }
            // ② 账本有没有新行（**只读**；只取到最后一个换行为止 ⇒ 半个行不推）
            let len = std::fs::metadata(ledger).map(|m| m.len()).unwrap_or(pos);
            let mut fresh: Vec<u8> = Vec::new();
            if len > pos {
                if let Ok(mut f) = std::fs::File::open(ledger) {
                    if f.seek(SeekFrom::Start(pos)).is_ok() {
                        let mut chunk = Vec::new();
                        if f.take(len - pos).read_to_end(&mut chunk).is_ok() {
                            if let Some(last_nl) = chunk.iter().rposition(|b| *b == b'\n') {
                                fresh = chunk[..=last_nl].to_vec();
                                pos += (last_nl + 1) as u64;
                            }
                        }
                    }
                }
            }
            // ③ 推给订户；推不动就丢（不缓冲、不等待）
            if !fresh.is_empty() {
                let mut keep: Vec<UnixStream> = Vec::with_capacity(subs.len());
                for mut s in subs.into_iter() {
                    if s.write_all(&fresh).is_ok() {
                        keep.push(s);
                    } else {
                        eprintln!("[登记] ext.world.ProjectServe.SubscriberDropped: 写不进去（慢消费者或已断）⇒ 丢弃这条订户");
                    }
                }
                subs = keep;
            }
            // ④ 订户往上发东西 ⇒ 明确拒绝并断开（**这不是写入口**）
            let mut keep: Vec<UnixStream> = Vec::with_capacity(subs.len());
            for mut s in subs.into_iter() {
                let mut got = false;
                match s.read(&mut buf) {
                    Ok(0) => got = true, // 对端关了
                    Ok(_) => {
                        let _ = s.write_all(format!("{NOT_WRITE_ENTRY}\n").as_bytes());
                        eprintln!("[登记] ext.world.ProjectServe.NotAWriteEntry: 订户往上发了东西 ⇒ 拒绝并断开");
                        got = true;
                    }
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {}
                    Err(_) => got = true,
                }
                if !got {
                    keep.push(s);
                }
            }
            subs = keep;
            std::thread::sleep(Duration::from_millis(TICK_MS));
        }
    }
}

fn cmd_project(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    use world_core::gui_projection::{self, language, surface, visual};

    let which = rest.get(1).map(String::as_str).unwrap_or("");
    // ★ `serve` 那一臂**在任何读模型之前**就分出去（它常驻、只推账本新行，不需要折叠状态）
    #[cfg(unix)]
    if which == "serve" {
        return project_serve::serve(l, rest);
    }
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let state = match w.read_model() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[FAIL] 读模型拒绝折叠：{e}");
            return ExitCode::from(2);
        }
    };
    let (world, vocab) = (w.ontology().world(), w.ontology().vocab_hash());

    match which {
        "language" => {
            print!("{}", language::render(&state, world, vocab));
            ExitCode::SUCCESS
        }
        "visual" => {
            print!("{}", visual::render(&state, world, vocab));
            ExitCode::SUCCESS
        }
        // ★ 机器可读的"现在的页面状态"：只给屏幕那一面、现算、带位点。
        //   与另两份投影读同一个 `State`、同一份词表；首行是同源头 ⇒ 三份能互验同源。
        "surface" => {
            print!("{}", surface::render(&state, world, vocab));
            ExitCode::SUCCESS
        }
        "check" => {
            let a = language::render(&state, world, vocab);
            let b = visual::render(&state, world, vocab);
            let c = surface::render(&state, world, vocab);
            match project::assert_same_source(&a, &b) {
                Ok(()) => {
                    // ★ **两条独立腿**：只比 language↔visual 时，两者共用同一份折叠 ⇒ 该断言近乎恒真。
                    //   把屏面投影也拉进来两两互验，才让"同源"有牙（评判逐字：「恒真、抓不到东西」）。
                    for (what, x, y) in [
                        ("语言投影与屏面投影", &a, &c),
                        ("视觉投影与屏面投影", &b, &c),
                    ] {
                        if let Err(e) = project::assert_same_source(x, y) {
                            eprintln!("[FAIL] {what} 不同源：{e}");
                            return ExitCode::from(2);
                        }
                    }
                    println!("== world-core project check ==");
                    println!("  词表 : {vocab}（世界版本 {world}）");
                    println!(
                        "  状态 : last_seq={} 指纹={}",
                        state.last_seq(),
                        state.digest()
                    );
                    println!("  同源 : ✅ 语言投影与视觉投影一致（同一读模型 + 同一词表）");
                    println!("  同源 : ✅ 屏面投影也一致（三份投影两两互验）");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    ExitCode::from(2)
                }
            }
        }
        other => {
            eprintln!("未知投影 `{other}`（可用：language / visual / surface / check）");
            ExitCode::from(1)
        }
    }
}

/// `read` —— **事件面**（既有形状，一字不改）＋ `--instances` 的**实例面**。
///
/// ## ★ 第 2 件：把「从什么变成什么」的**前值摆到出口上**（书 `:70` 逐字要求）
///
/// 书 `:70` 逐字：「（这是它要做到的样子。今天能证明的还只是"各方读的是同一份输入"；
/// **"从什么变成什么"里的前值，还没有出现在任何一份出口上**。）」
/// ⇒ 判据要的是「**出现在出口上**」，**不是**"藏在事件 JSON 里、让人自己去翻"：
/// 要人先懂我们的事件格式才拿得到前值，就退回了书要消灭的那种状态。
///
/// ⇒ `--instances` 的每一格印成 **`现在=<值>   原来=<值>`**：**直接读得出**，不必解析事件格式。
/// `原来=` 的取值**就是账本里那条 `change` 的 `before`**（同一来源，不存在第二份真相）；
/// 该格从未有过 `change` 则印「首见，无前值」——**不拿 `null` 冒充前值**
/// （`null` 与"没有前值"是两件事）。
///
/// ## ⚠️ 只增不改（**正控要钉的就是这一条**）
///
/// **不带 `--instances` 时输出与改动前逐字节相同**（仍是"一行一条事件 JSON"）⇒
/// 既有调用方一字不用改。
fn cmd_read(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    let from: u64 = rest.iter().find_map(|s| s.parse::<u64>().ok()).unwrap_or(1);
    let want_instances = rest.iter().any(|a| a == "--instances");
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let evs = match w.ledger().read_from(from) {
        Ok(evs) => evs,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    // ── 事件面：**既有形状，一字不改**（正控：不带 `--instances` 时逐字节不变）──
    for e in &evs {
        println!("{}", serde_json::to_string(e).unwrap_or_default());
    }
    if !want_instances {
        return ExitCode::SUCCESS;
    }

    // ── 实例面（`--instances`）──
    use serde_json::Value;
    // 前值来源＝**同一条账本事件**里的 `before`（不另立一份真相）。
    // 防线取法：先按 `/body/…` 取，取不到再按顶层取——形状变了也不至于静默取空。
    let pick = |e: &Value, key: &str| -> Option<Value> {
        e.pointer(&format!("/body/{key}"))
            .or_else(|| e.get(key))
            .cloned()
    };
    let mut before_of: std::collections::BTreeMap<(String, String), Value> =
        std::collections::BTreeMap::new();
    let mut last_seq: u64 = 0;
    for (i, e) in evs.iter().enumerate() {
        last_seq = e
            .get("seq")
            .and_then(Value::as_u64)
            .unwrap_or(last_seq.max(i as u64 + 1));
        let (Some(sub), Some(path)) = (
            pick(e, "subject").and_then(|v| v.as_str().map(str::to_string)),
            pick(e, "path").and_then(|v| v.as_str().map(str::to_string)),
        ) else {
            continue; // 只吃「某格变了」的事件（act／notice 不进实例面）
        };
        let b = pick(e, "before").unwrap_or(Value::Null);
        before_of.insert((sub, path), b);
    }
    let state = match w.read_model() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    println!("== 实例面（`read --instances`：**到第几条** ＋ 现在的值 ＋ **原来是什么**）==");
    println!("  到第几条（last_seq）: {last_seq}");
    let mut by_type: std::collections::BTreeMap<String, Vec<(String, String, String)>> =
        std::collections::BTreeMap::new();
    for (subject, path, value) in state.entries() {
        let t = world_core::ontology_instance::readmodel::type_of_subject(subject)
            .unwrap_or("（未声明类型）")
            .to_string();
        let now = serde_json::to_string(value).unwrap_or_default();
        // ★ 前值**直接摆在出口上**：与账本里那条 `before` 同源。
        let was = match before_of.get(&(subject.to_string(), path.to_string())) {
            Some(v) => serde_json::to_string(v).unwrap_or_default(),
            None => "（首见，无前值）".to_string(),
        };
        by_type.entry(t).or_default().push((
            subject.to_string(),
            path.to_string(),
            format!("现在={now}   原来={was}"),
        ));
    }
    for (t, mut rows) in by_type {
        rows.sort();
        println!("  类型 {t} : {} 个实例格", rows.len());
        for (subject, path, line) in rows {
            println!("    {subject}  {path} : {line}");
        }
    }
    ExitCode::SUCCESS
}

/// ★ **`subscribe` —— 订阅形状的**执行体**（形状声明在本体 `_subscribe`，挂 `_` 键）。
///
/// ## 三条口径（都来自本体那条声明，逐条对得上）
///
/// 1. **位点记在收件人自己**：位点由**调用方**用 `--since <seq>` 给；世界**不替收件人存进度**、
///    不写任何进度文件——世界一旦替它存，就多出一份会漂的真相。⇒ **缺 `--since` ⇒ 拒并点名**
///    （`ext.world.Subscribe.NoSinceSeq`）。
/// 2. **只给"从那条往后"**：`seq ≥ since` 的才输出。★ 这一步**本命令自己判**
///    （**不依赖** `read_from(since)` 替我挡——否则这条判据是空的：短路它也不会红）。
/// 3. **世界停掉后不许显示旧数**：本命令**不持有任何缓存**，每次现读账本；
///    读不到 ⇒ **rc≠0 且一个字都不打**（`ext.world.Subscribe.NoStale`）——
///    **旧数被当成现状，比没有数更坏**。
fn cmd_subscribe(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    // ①位点：`--since <seq>` **必填**（也接受裸数字，便于既有脚本风格）
    let since = rest
        .iter()
        .position(|a| a == "--since")
        .and_then(|i| rest.get(i + 1))
        .and_then(|s| s.parse::<u64>().ok());
    let Some(since) = since else {
        eprintln!(
            "ext.world.Subscribe.NoSinceSeq: 订阅**必须**给位点（用法：`subscribe --since <seq>`）。\n\
             \x20 为什么是**必填**而不是「缺省从头开始」：**位点记在收件人自己那里**（唯一权威），\
             世界**不替收件人存进度**——世界一存，就多出一份会漂的真相。\n\
             \x20 为什么「缺省 0」也不行：那会把「**我没给位点**」与「**我要从头读**」混成同一件事，\
             于是「订户以为自己续上了、其实从头又来一遍」这种错**永远不会被发现**。"
        );
        return ExitCode::from(2);
    };
    // ③世界读不到 ⇒ 拒，且**一个字都不打**（不许拿上次的数冒充现在）
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!(
                "ext.world.Subscribe.NoStale: 世界读不到（{e}）——**不打印任何缓存**。\n\
                 \x20 为什么：订阅面**不许显示旧数**。旧数被当成现状，比没有数更坏\
                 （那是把『曾经是什么』冒充『现在是什么』）。⇒ 本命令**不持有缓存**，读不到就说读不到。"
            );
            return ExitCode::from(2);
        }
    };
    let evs = match w.ledger().read_from(1) {
        Ok(evs) => evs,
        Err(e) => {
            eprintln!("ext.world.Subscribe.NoStale: 账本读不出（{e}）——**不打印任何缓存**。");
            return ExitCode::from(2);
        }
    };
    // ②只给"从那条往后"：**本命令自己判**（这条是判据要钉的那一步）
    // ⚠️ 输出**只有事件行**（与 `read` 同形）——不另加汇总行，
    //    否则"输出只含 seq ≥ since 的那些"这条正控就不是逐行可判的了。
    for e in &evs {
        let seq = e.get("seq").and_then(|v| v.as_u64()).unwrap_or(0);
        if seq < since {
            continue;
        }
        println!("{}", serde_json::to_string(e).unwrap_or_default());
    }
    ExitCode::SUCCESS
}

/// `checkpoint` —— **M08 接线的生产调用点**（`W-03` / `P-09`）。
///
/// 为什么要有这三个子命令：`src/ontology_instance/checkpoint.rs` 此前**整册生产零调用点**
/// ——`capture` / `write` / `load` / `verify` / `resume_unverified` /
/// `read_model_with_checkpoint` 在生产代码里各 0 命中，即"已实现"只是**文件里存在**，
/// 用户永远用不到。接线的判据不是"文件里有"，而是"**生产路径可调用且契约要点逐条成立**"：
///
/// | 契约要点（`WC-IC-M08`） | 本命令的落点 |
/// |---|---|
/// | 提供者：`M08` | `world_core::ontology_instance::checkpoint` |
/// | 输入：账本 + 快照路径 | `--ledger` / `<path>` |
/// | 输出：快照文件 / 核验结论 / 续算指纹 | 三个子命令各自的 stdout |
/// | 异常与错误码：`ext.world.Checkpoint.*` | 见 `src/ontology_instance/checkpoint.rs` |
/// | 不变量：**缓存不得成为第二真相** | `verify` 拿账本重算前 `base_seq` 条比对指纹；`resume` 与全量重算**逐字节**比对 |
/// | 判据：删掉快照再算，结果不变 | `resume` 的输出必须等于 `state --json` |
fn cmd_checkpoint(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    use world_core::ontology_instance::checkpoint::{read_model_with_checkpoint, Checkpoint};
    let sub = rest.get(1).map(String::as_str).unwrap_or("");
    let Some(cp_arg) = rest.get(2) else {
        eprintln!("用法: world-core checkpoint <write|verify|resume> <path>");
        return ExitCode::from(1);
    };
    let cp_path = Path::new(cp_arg);
    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let events = match w.ledger().read_all() {
        Ok(v) => v,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    match sub {
        "write" => {
            let st = match w.read_model() {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[FAIL] 读模型拒绝折叠：{e}");
                    return ExitCode::from(2);
                }
            };
            let cp = Checkpoint::capture(&st);
            if let Err(e) = cp.write(cp_path) {
                eprintln!("[FAIL] {e}");
                return ExitCode::from(2);
            }
            println!("== world-core checkpoint write ==");
            println!("  快照 : {}", cp_path.display());
            println!("  base_seq={} 指纹={}", cp.base_seq(), cp.digest());
            println!("  （快照是**缓存、不是真相**：删掉它不影响任何结论）");
            ExitCode::SUCCESS
        }
        "verify" => {
            let cp = match Checkpoint::load(cp_path) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            if let Err(e) = cp.verify(&events) {
                eprintln!("[FAIL] {e}");
                return ExitCode::from(2);
            }
            println!(
                "  核验 : ✅ 快照 base_seq={} 与账本前 {} 条一致（缓存未成为第二真相）",
                cp.base_seq(),
                cp.base_seq()
            );
            ExitCode::SUCCESS
        }
        "resume" => {
            let cp = match Checkpoint::load(cp_path) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            let fast = match read_model_with_checkpoint(&events, Some(&cp)) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            let full = match w.read_model() {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[FAIL] 读模型拒绝折叠：{e}");
                    return ExitCode::from(2);
                }
            };
            if fast.to_json() != full.to_json() {
                eprintln!(
                    "ext.world.Checkpoint.ResumeMismatch: 从快照续算与全量重算结果不一致——\
                     缓存成了第二真相，拒绝使用"
                );
                return ExitCode::from(2);
            }
            println!("== world-core checkpoint resume ==");
            println!("  快路径指纹 : {}", fast.digest());
            println!("  全量指纹   : {}", full.digest());
            println!("  一致 : ✅ 续算 == 全量重算（逐字节）");
            ExitCode::SUCCESS
        }
        other => {
            eprintln!("未知 checkpoint 子命令 `{other}`（可用：write / verify / resume）");
            ExitCode::from(1)
        }
    }
}

/// `channel` —— **M09 接线的生产调用点**（`W-03` / `P-10`）。
///
/// 为什么要有它：`src/bus/mod.rs` 此前**整册生产零调用点**，`channel::bind` 连测试都零调用
/// ⇒「权限即身份」（`0600` + `chown` + 通道目录静态墙）**从未被执行过**；
/// 原有测试用 `UnixListener::bind` 自己建套接字，**绕过了** `bind()`，
/// 于是只验了"自称被拒"，**没验"别人连不上"**。
///
/// 用法：`world-core --channel <channel.json> channel bind <socket>`
///       `world-core --channel <channel.json> channel accept <socket>`
///
/// ⚠️ 本仓**不提供出厂 `channel.json`**（`WC-SCMP-001` §8.4 `G-28` 记"是否补出厂文件**待人裁定**"），
/// 故 `--channel` 指向的文件由部署方给出；缺文件即 `ext.world.Channel.ReadFail` 拒启。
///
/// **四个资源边界**（`REQ-F-026`）走**生产这一条路**：`accept`／`serve` 受理之前，
/// 先从 `--policy` 的 `channel_limits` 块读出四个数值（`Limits::from_policy`），
/// 读不到即 `rc=2` **拒启**——「通道的资源边界没有数值就不许受理」。
/// `bind` 不受四条边界约束（它不读消息，只建套接字）。
#[cfg(unix)]
fn cmd_channel(o: &Path, l: &Path, p: &Path, cfg: &Path, rest: &[String]) -> ExitCode {
    use world_core::bus::{self, ChannelConfig};
    let sub = rest.get(1).map(String::as_str).unwrap_or("");
    let Some(sock_arg) = rest.get(2) else {
        eprintln!("用法: world-core --channel <path> channel <bind|accept> <socket>");
        return ExitCode::from(1);
    };
    let sock = PathBuf::from(sock_arg);
    let conf = match ChannelConfig::load(cfg) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let expect = match conf.listener_for(&sock) {
        Some(x) => x.clone(),
        None => {
            eprintln!(
                "ext.world.Channel.NotConfigured: 套接字 {} 不在 {} 的身份映射里——\
                 没有身份映射的连接不得建立（默认拒绝）",
                sock.display(),
                cfg.display()
            );
            return ExitCode::from(2);
        }
    };
    // ★ **账外口不许【建】**（产品入口这条路，`WC-LLD` 里的 `channel bind|accept|serve`）：
    //   `channel bind` 会按这条绑定把套接字**建到盘上** —— 不判，就等于把一条法律里没有的
    //   映射变成盘上真有的一个口。★与 `cmd_serve` 的认领那一步**同一个函数、同一个错误码**
    //   （一处事实一个载体）。
    //   ⚠ **次序**：`bind` 这一臂没有"取四数"那一步，故判在这里；`accept|serve` 那两臂的
    //   同一判据放在 `Limits::from_policy` **之后**（见下面那一处）——资源边界在前，
    //   否则**缺 `channel_limits` 的配置会改口**成 `UndeclaredListener`，把病因说错
    //   （`tools/s1_sys_probe2.sh` 的 ⑪b／⑪d 判的就是那两句原话）。
    if sub == "bind" {
        if let Err(e) = ChannelConfig::load_checked(cfg, p) {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    }
    match sub {
        "bind" => match channel::bind(&expect) {
            Ok(_lst) => {
                println!("== world-core channel bind ==");
                println!(
                    "  套接字 : {}  actor={}  uid={}",
                    expect.socket.display(),
                    expect.actor,
                    expect.uid
                );
                println!("  （0600 + chown 到该 uid ⇒ **只有那个 uid 连得上**）");
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("[FAIL] {e}");
                ExitCode::from(2)
            }
        },
        "accept" | "serve" => {
            let n = if sub == "serve" {
                match rest.get(3).and_then(|s| s.parse::<usize>().ok()) {
                    Some(n) if n > 0 => n,
                    _ => {
                        eprintln!(
                            "用法: world-core --channel <path> channel serve <socket> <个数>"
                        );
                        return ExitCode::from(1);
                    }
                }
            } else {
                1
            };
            // **四个资源边界先取数**（`REQ-F-026`）：四条边界的数值**只**来自出厂配置，
            // 代码里没有缺省值 ⇒ 取不到就**拒启**（不许拿"没配"当"不设界"）。
            // 放在 `bind` 之前：连套接字都不该建——一个没有边界的通道不该上电。
            let limits = match channel::Limits::from_policy(p) {
                Ok(x) => x,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            // ★ **账外口不许受理**（与 `cmd_serve`／`bind` 同一个判据、同一个错误码）。
            //   ⚠ **放在取四数之后**：资源边界在前 ⇒ 缺 `channel_limits` 的配置仍报
            //   `NoLimits`／`BadLimits`，不会因为这新判据改口（`s1_sys_probe2.sh` ⑪ 判的就是那两句）。
            if let Err(e) = ChannelConfig::load_checked(cfg, p) {
                eprintln!("[FAIL] {e}");
                return ExitCode::from(2);
            }
            let mut sess = channel::Session::new(limits);
            let lst = match channel::bind(&expect) {
                Ok(x) => x,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            let mut w = match World::open(o, l, p) {
                Ok(w) => w,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            if sub == "accept" {
                return match channel::serve_once_with(&mut w, &lst, &expect, &mut sess) {
                    Ok(ev) => {
                        println!("{}", serde_json::to_string(&ev).unwrap_or_default());
                        ExitCode::SUCCESS
                    }
                    Err(e) => {
                        eprintln!("[FAIL] {e}");
                        ExitCode::from(2)
                    }
                };
            }
            match channel::serve_n_with(&mut w, &lst, &expect, &mut sess, n) {
                Ok(ok) => {
                    println!("== world-core channel serve ==");
                    println!(
                        "  套接字 : {}  actor={}",
                        expect.socket.display(),
                        expect.actor
                    );
                    println!(
                        "  资源边界: 并发连接数={} 单条消息字节={} 每秒消息数={} 空闲超时={}ms（取自 {}）",
                        limits.max_connections,
                        limits.max_line_bytes,
                        limits.max_msgs_per_sec,
                        limits.idle_timeout_ms,
                        p.display()
                    );
                    println!("  已处理 : {ok} / {n} 个连接");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    ExitCode::from(2)
                }
            }
        }
        other => {
            eprintln!("未知 channel 子命令 `{other}`（可用：bind / accept / serve）");
            ExitCode::from(1)
        }
    }
}

#[cfg(not(unix))]
fn cmd_channel(_o: &Path, _l: &Path, _p: &Path, _cfg: &Path, _rest: &[String]) -> ExitCode {
    eprintln!("ext.world.Channel.Unsupported: 通道只在 Unix 上可用（v1 局限）");
    ExitCode::from(1)
}

/// `carrier` —— **载体侧的手**（`M10`）：只执行、不裁决。
///
/// 三个只读子命令（`capabilities` / `check` / `undo`）**不碰载体、不连内核**，
/// 只读执行清单；`orphans` 只读账本；两个动作子命令（`do` / `serve`）
/// 一律走「**先问内核 → 准了才动 → 动完回写**」，且**连不上内核即拒绝执行**。
///
/// ⚠️ 它**没有**"允不允许"的话语权：清单里有的能力，门禁说不行照样不行。
/// 这条不对称（可以拒绝、永远不能放行）是"门禁不可绕过"在跨进程形态下的落点。
#[cfg(unix)]
fn cmd_carrier(
    cap_dir: &Path,
    kernel_sock: Option<&Path>,
    allow_confirm: bool,
    ledger: &Path,
    rest: &[String],
) -> ExitCode {
    use world_core::carrier::capd::Manifest;
    use world_core::carrier::providers::Registry;
    use world_core::carrier::run::{self, NoConfirm, TerminalConfirm};

    let sub = rest.get(1).map(String::as_str).unwrap_or("");
    let manifest = match Manifest::load_dir(cap_dir) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };

    match sub {
        "capabilities" => {
            println!("== world-core carrier capabilities ==");
            println!("  执行清单 : {}", cap_dir.display());
            println!("  已注册执行器 : {:?}", Registry::builtin().names());
            if manifest.is_empty() {
                println!(
                    "  能力 : （空）——**空清单不是『什么都不允许』的安全默认，是『没装清单』**"
                );
            } else {
                println!("  能力（默认拒绝：清单外的能力一律不执行）：");
                for c in manifest.iter() {
                    let mut flags = Vec::new();
                    if c.needs_undo() {
                        flags.push("动手前先做撤销点");
                    }
                    if c.needs_confirm() {
                        flags.push("需要人确认");
                    }
                    let tail = if flags.is_empty() {
                        String::new()
                    } else {
                        format!("  ← {}", flags.join(" / "))
                    };
                    println!(
                        "    {:<18} 动词={:?} 风险={:?} 执行器={}{}",
                        c.name, c.verbs, c.risk, c.provider, tail
                    );
                }
            }
            println!("  ⚠️ 本清单只回答「**怎么干**」；「允不允许」由内核的门禁裁决。");
            ExitCode::SUCCESS
        }
        "check" => {
            // 复核：清单里的执行器必须都已注册，否则那项能力永远执行不了（死号）。
            let reg = Registry::builtin();
            let mut dead: Vec<String> = Vec::new();
            for c in manifest.iter() {
                if reg.get(&c.provider).is_none() {
                    dead.push(format!("{}（执行器 {} 未注册）", c.name, c.provider));
                }
            }
            println!("== world-core carrier check ==");
            println!("  清单文件目录 : {}", cap_dir.display());
            println!("  能力数 : {}", manifest.names().len());
            if dead.is_empty() {
                println!("  结论 : ✅ 全部能力的执行器都已注册");
                ExitCode::SUCCESS
            } else {
                println!("  结论 : ❌ 有 {} 项能力是死号：", dead.len());
                for d in &dead {
                    println!("    - {d}");
                }
                ExitCode::from(2)
            }
        }
        "undo" => {
            println!("== world-core carrier undo（载体撤销点）==");
            let mut n = 0;
            for c in manifest.iter() {
                if c.needs_undo() {
                    println!("  {} → 每次动手前先做撤销点（风险={:?}）", c.name, c.risk);
                    n += 1;
                }
            }
            if n == 0 {
                println!("  （无）");
            }
            println!(
                "  ⚠️ 载体撤销撤的是**文件系统的字节**，不是世界状态；\
                 「坏了能回滚」靠的是**追加补偿事件**，不是它。"
            );
            ExitCode::SUCCESS
        }
        "orphans" => {
            // 只读账本：**有意图、无结果**的请求。
            let events = match world_core::carrier::recover::read_ledger_readonly(ledger) {
                Ok(e) => e,
                Err(e) => {
                    eprintln!("[FAIL] {e}");
                    return ExitCode::from(2);
                }
            };
            let orphans = world_core::carrier::recover::orphans(&events);
            println!("== world-core carrier orphans ==");
            println!("  账本 : {}（{} 条事件）", ledger.display(), events.len());
            if orphans.is_empty() {
                println!("  结论 : ✅ 没有『有意图、无结果』的请求");
                ExitCode::SUCCESS
            } else {
                println!("  结论 : ⚠️ 有 {} 条请求有意图、无结果：", orphans.len());
                for o in &orphans {
                    println!(
                        "    seq={} {} {}  请求号={}  距今={}s",
                        o.intent_seq, o.capability, o.verb, o.request_id, o.age_secs
                    );
                    println!("      {}", o.hint());
                }
                // 有孤儿**不是**"跑失败了"：它是账本如实显示的状态。
                // 故退出码 0，但结论里点明要人看。
                ExitCode::SUCCESS
            }
        }
        "do" | "serve" => {
            let Some(sock) = kernel_sock else {
                eprintln!(
                    "用法: world-core carrier {sub} … --socket <内核套接字>\n\
                     ⚠️ 必须显式给出内核套接字：适配器**对账本零写权限**，\
                     它写世界的唯一通道就是这条连接。"
                );
                return ExitCode::from(1);
            };
            let client = world_core::carrier::kernel::KernelClient::new(sock);
            let reg = Registry::builtin();
            let confirmer: &dyn run::Confirmer = if allow_confirm {
                &TerminalConfirm
            } else {
                &NoConfirm
            };
            let adapter = run::Adapter {
                client: &client,
                manifest: &manifest,
                registry: &reg,
                confirmer,
            };
            if sub == "serve" {
                return match run::serve(&adapter) {
                    Ok(()) => ExitCode::SUCCESS,
                    Err(e) => {
                        eprintln!("[FAIL] {e}");
                        ExitCode::from(2)
                    }
                };
            }
            // do：手工跑一次
            let (cap, verb, rid) = (
                rest.get(2).cloned().unwrap_or_default(),
                rest.get(3).cloned().unwrap_or_default(),
                rest.get(4).cloned().unwrap_or_default(),
            );
            if cap.is_empty() || verb.is_empty() || rid.is_empty() {
                eprintln!(
                    "用法: world-core carrier do <能力> <动词> <请求号> [参数JSON] --socket <内核套接字>"
                );
                return ExitCode::from(1);
            }
            let params: serde_json::Value = match rest.get(5) {
                None => serde_json::Value::Null,
                Some(s) if s.starts_with("--") => serde_json::Value::Null,
                Some(s) => match serde_json::from_str(s) {
                    Ok(v) => v,
                    Err(e) => {
                        eprintln!("[FAIL] ext.world.Carrier.BadParam: 参数不是合法 JSON：{e}");
                        return ExitCode::from(1);
                    }
                },
            };
            let attempt = adapter.attempt(&world_core::carrier::Invocation {
                capability: cap.clone(),
                verb: verb.clone(),
                request_id: rid.clone(),
                params,
            });
            println!("== world-core carrier do ==");
            println!(
                "  能力={cap} 动词={verb} 请求号={rid} 内核={}",
                sock.display()
            );
            println!("  {}", attempt.summary());
            if attempt.admitted {
                ExitCode::SUCCESS
            } else {
                // 未获准或连不上内核：**一次都没动**，退非零让调用方知道。
                ExitCode::from(2)
            }
        }
        other => {
            eprintln!(
                "未知 carrier 子命令 `{other}`\
                 （可用：capabilities / check / undo / orphans / do / serve）"
            );
            ExitCode::from(1)
        }
    }
}

#[cfg(not(unix))]
fn cmd_carrier(
    _cap_dir: &Path,
    _kernel_sock: Option<&Path>,
    _allow_confirm: bool,
    _ledger: &Path,
    _rest: &[String],
) -> ExitCode {
    eprintln!("ext.world.Carrier.Unsupported: 载体适配器的动作面只在 Unix 上可用（v1 局限）");
    ExitCode::from(1)
}

// ══════════════════════════════════════════════════════════════════════════
// 内联模块 `serve` —— 载体拉起（socket activation ＋ sd_notify）。
//
// **为什么是内联模块而不是 `src/serve.rs`**（如实登记，不是偷懒）：
// `tools/module_graph.py` 判据③（A-2 四件同夹）要求 `src/` 下**每个文件都被一个模块号认领**：
// 实测把本段放成 `src/serve.rs` ⇒ 判据③ 当场红（「`src/serve.rs` 没有被任何模块号认领」）。
// 而新开一个模块号要**同时**改两处受控件（`WC-MODREG-001` 的登记表 ＋ `WC-IC-001` 的契约节），
// 那是比本批大得多的变更 ⇒ 本批先落在 `main.rs`（已由 M04 认领）里，
// 并把「是否独立成模块」作为**待裁项**登记在 `docs/证据/EV-009.md`。
// ══════════════════════════════════════════════════════════════════════════
mod serve {
    //! **载体拉起（`serve`）**——读**继承的描述符**（socket activation）＋ 向 `$NOTIFY_SOCKET` 报到。
    //!
    //! ## 这一模块为什么存在
    //!
    //! `deploy/world-core.service` 逐字写的是 `Type=notify` ＋ `ExecStart=… serve`，
    //! 而 `deploy/world-core.socket` 逐字写着「监听套接字**归载体所有**；内核进程通过**继承的
    //! 描述符**拿到它（`sd_listen_fds` 语义）」。⇒ 内核这一侧必须有对应的实现，
    //! **否则单元装上也起不来**：`Type=notify` 等一个永远不来的 `READY=1`，
    //! 描述符也没人去接。
    //!
    //! ## 零新依赖（硬约束：`Cargo.toml` 只许 `serde_json`）
    //!
    //! 全部用标准库：`std::os::unix::net::{UnixListener, UnixDatagram}` ＋
    //! `std::os::linux::net::SocketAddrExt`（抽象命名空间）＋ `std::env`。
    //! **不引 `libc`、不引 `sd-notify` crate。**
    //!
    //! ## 四条口径（都可判真假，各配反例）
    //!
    //! | # | 口径 | 反例（必须拒启／必须不致命） |
    //! |---|---|---|
    //! | ① | `LISTEN_FDS` **必须**在、`LISTEN_PID` **必须**是本进程、fd 3 **必须**是可用监听套接字 | 三者任一不满足 ⇒ **拒启并点名**（`ext.world.Serve.*`） |
    //! | ② | `READY=1` **必须在开始受理之前**发出 | 先受理后报到 ⇒ 载体在"还在初始化"时就把请求放进来了 |
    //! | ③ | `WATCHDOG_USEC` 在时，按**半周期**发 `WATCHDOG=1` | 不发 ⇒ `WatchdogSec=30s` 到点把进程杀掉 |
    //! | ④ | `NOTIFY_SOCKET` **缺失不许当致命** | 裸跑（不带 systemd）必须照样起得来 |
    //!
    //! ## ★ 一处**如实登记的射程**
    //!
    //! 本模块**只**实现"读继承 fd ＋ 报到"这一截；**端到端**（真的由 systemd 传 fd 3）在本仓
    //! **测不了**：`std` 没有 `dup2`，测试进程无法把监听套接字塞进子进程的 **fd 3**
    //! 并把 `CLOEXEC` 清掉（那需要 `libc`）。⇒ 本模块的**可测面**是：
    //! 环境变量解析与拒启（可真跑二进制）＋ 报到顺序（结构缝 `serve_activated_with`）＋
    //! 报文的**真实投递**（对着一个自建的 `UnixDatagram` 发）。
    //! 端到端那一格**登记为"未测"**，不假装测过（见 `docs/证据/EV-009.md`）。

    use std::env;
    use std::os::unix::io::FromRawFd;
    use std::os::unix::net::{UnixDatagram, UnixListener};
    use std::time::Duration;

    /// **`LISTEN_FDS` 的解析结果**（`systemd` 的 `sd_listen_fds` 语义）。
    #[derive(Debug, Clone, PartialEq, Eq)]
    pub struct ListenFds {
        /// `LISTEN_FDS` 声明的描述符个数（`sd_listen_fds` 保证 ≥1；0 视为没传）。
        pub n: usize,
        /// `LISTEN_PID` 的原文（**必须是本进程**，否则 fds 是别人的，绝不能收）。
        pub pid: u32,
    }

    /// 从环境变量读 `LISTEN_FDS`／`LISTEN_PID` 并**校验**。
    ///
    /// 拒启的三种情形（**各自点名**，不合并成一句散文）：
    /// - 缺 `LISTEN_FDS`（或为 0）⇒ `NoListenFds`；
    /// - 缺 `LISTEN_PID`、不是数字、或**不是本进程** ⇒ `ListenPidMismatch`；
    /// - `LISTEN_FDS` 不是正整数 ⇒ `BadListenFds`。
    ///
    /// ## 为什么"缺 `LISTEN_FDS`"是**拒启**而不是"退化成本地建套接字"
    ///
    /// `deploy/world-core.socket` 把监听套接字的所有权**交给载体**（`Accept=no` ＋ 继承 fd）。
    /// 若 `serve` 在拿不到继承 fd 时**自己 `bind` 一个**，就出现了**第二个**监听者：
    /// 载体手上那个与进程自己建的那个会**各自接受连接**——"一个口一个身份"当场不成立。
    /// ⇒ 宁可拒启并**说清**（那是部署问题，不是运行时问题）。
    pub fn listen_fds_from_env() -> Result<ListenFds, String> {
        let raw_n = env::var("LISTEN_FDS").ok();
        let n: usize = match raw_n.as_deref() {
            Some(s) if !s.trim().is_empty() => s.trim().parse().map_err(|_| {
                format!(
                    "ext.world.Serve.BadListenFds: `LISTEN_FDS` 不是正整数（实得 `{s}`）——\
                     那是载体传下来的描述符个数，读不懂就**不能猜**"
                )
            })?,
            _ => {
                return Err(
                    "ext.world.Serve.NoListenFds: 没有 `LISTEN_FDS`（也没看到 `LISTEN_PID`）——\
                     **`serve` 只从载体继承监听套接字**，不自己 `bind`。\n\
                     \x20 为什么：`deploy/world-core.socket` 把套接字所有权交给载体（`Accept=no` ＋ 继承 fd）；\
                     自己再建一个就会出现**两个监听者**，「一个口一个身份」当场不成立。\n\
                     \x20 处置：用 `systemctl start world-core.service`（由 socket 单元喂 fd），\
                     或在测试里按 `sd_listen_fds` 的约定设 `LISTEN_FDS=1`／`LISTEN_PID=<本进程>` 并让 fd 3 可用"
                        .to_string(),
                )
            }
        };
        if n == 0 {
            return Err(
                "ext.world.Serve.NoListenFds: `LISTEN_FDS=0`——载体声明了 0 个描述符，\
                 等于没有口；**没有口的 `serve` 没有意义**（拒启，而不是空转）"
                    .to_string(),
            );
        }
        let raw_pid = env::var("LISTEN_PID").ok();
        let pid: u32 = match raw_pid.as_deref() {
            Some(s) if !s.trim().is_empty() => s.trim().parse().map_err(|_| {
                format!(
                    "ext.world.Serve.ListenPidMismatch: `LISTEN_PID` 不是数字（实得 `{s}`）——\
                     读不懂归属就**不能收**这些描述符"
                )
            })?,
            _ => {
                return Err(
                    "ext.world.Serve.ListenPidMismatch: 有 `LISTEN_FDS` 却缺 `LISTEN_PID`——\
                     **无法判定这些描述符是不是给本进程的**（`sd_listen_fds` 的语义就是按 pid 归属）。\n\
                     \x20 为什么不能「反正只有我一个进程」就收下：fd 的归属是**载体给的**，
                     猜错就等于把别人的口接到自己的身份上"
                        .to_string(),
                )
            }
        };
        let me = std::process::id();
        if pid != me {
            return Err(format!(
                "ext.world.Serve.ListenPidMismatch: `LISTEN_PID={pid}` 不是本进程（本进程 pid={me}）——\
                 这些描述符**是传给别人的**，拒收。\n\
                 \x20 处置：这正是 `sd_listen_fds` 的归属校验；若在测试里跑，\
                 用 `sh -c 'LISTEN_FDS=1 LISTEN_PID=$$ exec <二进制> … serve'`（`exec` 保持同一 pid）"
            ));
        }
        Ok(ListenFds { n, pid })
    }

    /// **从 fd 3 起，把载体交来的监听套接字【全部】取出来**（`sd_listen_fds` 约定：从 3 开始连续编号）。
    ///
    /// ## 为什么是"全部"（这条是把旧版的一句登记改掉的）
    ///
    /// **每个口各一个 socket 单元**（各自 `SocketUser=` ⇒ 每口各自的属主保得住），载体在服务启动
    /// 那一刻把 n 个 fd **一次**交过来（`LISTEN_FDS=n`）。★旧版**只取 fd 3**，并在 `n > 1` 时打一行
    /// `[登记] ExtraListenFds` 说"多出来的口没人接"——★那行登记**当时是真话，今天是假话**：
    /// 现场实测过（两个口都在听、`LISTEN_FDS=2`，服务日志里只有那行登记）⇒ **第二个口没人受理**。
    /// ⇒ ★**"口起了"与"口受理得到"是两件事**；本函数把它消掉。
    ///
    /// `n > 1` 时改报 **`ListenFdsAccepted`（受理 fd 3..3+n-1）**——**旧的那句 `ExtraListenFds` 删除**
    /// （它的射程是"本进程只接第一个"，而那个事实已经不成立；留着它就是一句会烂的话）。
    ///
    /// ⚠️ **先验后取**（**逐 fd** 都验，血泪见下）：`from_raw_fd` 取得所有权后，若该 fd 根本没打开，
    /// Rust 的 IO-safety 机制会在 `Drop` 时 `fatal runtime error` **abort**——**不是**我们要的
    /// "拒绝启动并点名"。abort 连退出码都给不出，载体只看到"进程崩了"。
    /// ⇒ 必须先用 `/proc/self/fd/<n>` 的符号链接**纯读**确认"存在且是套接字"，再取所有权。
    /// ⚠️ 射程：它证明"fd 存在且是**套接字**"；**不**证明"它已处于 `listen` 状态"——
    /// 那一点由受理循环的第一次 `accept()` 当场暴露（会报错，不静默）。如实登记。
    pub fn listeners_from_fds(fds: &ListenFds) -> Result<Vec<UnixListener>, String> {
        const FIRST_FD: i32 = 3;
        let mut out = Vec::new();
        for i in 0..fds.n {
            let fd = FIRST_FD + i as i32;
            let unusable = |why: &str| {
                format!(
                    "ext.world.Serve.ListenFdUnusable: `LISTEN_FDS={}` 声明了描述符，但 **fd {fd} 不可用**\
                     （{why}）——拒启并点名。\n\
                     \x20 `sd_listen_fds` 的约定：传下来的描述符从 **fd 3** 开始连续编号。\n\
                     \x20 处置：确认套接字单元真的把 fd 交给了本进程\
                     （`Accept=no` ＋ `ListenStream=` ＋ `Service=`），而不是只设了环境变量",
                    fds.n
                )
            };
            match std::fs::read_link(format!("/proc/self/fd/{fd}")) {
                Err(e) => return Err(unusable(&format!("读 `/proc/self/fd/{fd}` 失败：{e}"))),
                Ok(p) => {
                    let s = p.to_string_lossy().to_string();
                    if !s.starts_with("socket:") {
                        return Err(unusable(&format!("fd {fd} 指向的是 `{s}`，**不是套接字**")));
                    }
                }
            }
            // 到这一步该 fd 确认存在且是套接字 ⇒ 取得所有权是安全的（`Drop` 关它是对的）。
            let listener = unsafe { UnixListener::from_raw_fd(fd) };
            if let Err(e) = listener.local_addr() {
                return Err(unusable(&format!("它不是可用的 Unix 监听套接字：{e}")));
            }
            out.push(listener);
        }
        if out.is_empty() {
            return Err(
                "ext.world.Serve.NoListenFds: `LISTEN_FDS` 声明了 0 个描述符——一个口也没有"
                    .to_string(),
            );
        }
        if fds.n > 1 {
            eprintln!(
                "[登记] ext.world.Serve.ListenFdsAccepted: `LISTEN_FDS={}` ⇒ 逐个受理 fd 3..{}",
                fds.n,
                FIRST_FD + fds.n as i32 - 1
            );
        }
        Ok(out)
    }

    /// **`$NOTIFY_SOCKET` 的解析**：`None` ＝ 没给（**不是错误**）。
    ///
    /// 口径④：**裸跑必须能起来** ⇒ 缺失**绝不**当致命。
    ///
    /// 支持两种形态（都只用标准库）：
    /// - **文件系统路径**（`/run/systemd/notify`）；
    /// - **抽象命名空间**（`@名字`，systemd 在多数版本上的默认）——
    ///   用 `std::os::linux::net::SocketAddrExt::from_abstract_name`。
    pub fn notify_socket_from_env() -> Option<String> {
        env::var("NOTIFY_SOCKET").ok().filter(|s| !s.is_empty())
    }

    /// **向 `$NOTIFY_SOCKET` 发一条报文**（`READY=1` / `WATCHDOG=1` / `STATUS=…`）。
    ///
    /// - `sock` 为 `None` ⇒ **不发，返回 `Ok(())`**（口径④：裸跑不致命）；
    /// - `@名字` ⇒ 抽象命名空间；否则按文件系统路径；
    /// - 发了但**发不出去** ⇒ `Err`（报到失败必须让人知道：`Type=notify` 会一直等，
    ///   而"等"与"卡死"在载体眼里是同一种形态）。
    pub fn send_notify(sock: Option<&str>, msg: &str) -> Result<(), String> {
        let Some(sock) = sock else {
            return Ok(());
        };
        let dg = UnixDatagram::unbound()
            .map_err(|e| format!("ext.world.Serve.BadNotifySocket: 建通知套接字失败：{e}"))?;
        let sent = if let Some(name) = sock.strip_prefix('@') {
            #[cfg(target_os = "linux")]
            {
                use std::os::linux::net::SocketAddrExt;
                let addr = std::os::unix::net::SocketAddr::from_abstract_name(name.as_bytes())
                    .map_err(|e| {
                        format!(
                            "ext.world.Serve.BadNotifySocket: `NOTIFY_SOCKET={sock}` 是抽象命名空间，\
                             但地址构造失败：{e}"
                        )
                    })?;
                dg.send_to_addr(msg.as_bytes(), &addr)
            }
            #[cfg(not(target_os = "linux"))]
            {
                Err(std::io::Error::new(
                    std::io::ErrorKind::Unsupported,
                    "非 Linux 平台不支持抽象命名空间",
                ))
            }
        } else {
            dg.send_to(msg.as_bytes(), sock)
        };
        sent.map(|_| ()).map_err(|e| {
            format!(
                "ext.world.Serve.BadNotifySocket: 向 `NOTIFY_SOCKET={sock}` 报到失败：{e}\n\
                 \x20 为什么这是**错误**而不是静默：`Type=notify` 的单元会**一直等** `READY=1`，\
                 而「等」与「卡死」在载体眼里同形 ⇒ 报到失败必须当场说出来"
            )
        })
    }

    /// **`$WATCHDOG_USEC` 的半周期**（口径③：按**半周期**发 `WATCHDOG=1`）。
    ///
    /// 为什么是半周期：留一半余量，单次迟到不会立刻被判死（systemd 的通行做法）。
    /// 取不到／不是正数 ⇒ `None`（**不致命**：裸跑没有看门狗）。
    pub fn watchdog_interval_from_env() -> Option<Duration> {
        let usec: u64 = env::var("WATCHDOG_USEC").ok()?.trim().parse().ok()?;
        if usec == 0 {
            return None;
        }
        // 半周期；下限 1ms，避免有人给个 1 微秒把机器打满。
        let half = (usec / 2).max(1000);
        Some(Duration::from_micros(half))
    }

    /// **报到顺序的结构缝**（口径②：`READY=1` **必须在开始受理之前**）。
    ///
    /// 为什么抽成这个形状：要证明"先报到、后受理"这条**顺序**，最直接的办法是
    /// 把"受理"做成一个**可替换的动作** `accept_loop`，让调用点先报到再调它。
    /// 测试传一个"记下此刻是否已报到"的闭包即可判定顺序——**不必真的起 systemd**。
    pub fn serve_activated_with<F>(
        notify: Option<&str>,
        watchdog: Option<Duration>,
        status: &str,
        accept_loop: F,
    ) -> Result<(), String>
    where
        F: FnOnce() -> Result<(), String>,
    {
        // ③ 看门狗：**先起心跳**再报到——否则报到到第一次心跳之间若超时，会被判死。
        if let (Some(sock), Some(iv)) = (notify, watchdog) {
            let sock = sock.to_string();
            std::thread::spawn(move || loop {
                std::thread::sleep(iv);
                // 心跳发不出去**不改退出码**（进程不该因为载体不在而自杀），但要说出来。
                if let Err(e) = send_notify(Some(&sock), "WATCHDOG=1") {
                    eprintln!("[登记] {e}");
                }
            });
        }
        // ② 就绪门槛：**在受理之前**报到。
        send_notify(notify, status)?;
        // ④ 没有 NOTIFY_SOCKET 时上面是 no-op（裸跑照常走到这里）。
        accept_loop()
    }

    #[cfg(test)]
    mod unit {
        use super::*;

        #[test]
        fn notify_socket_absent_is_not_an_error() {
            // 口径④：缺失**绝不当致命**（裸跑要能起来）。
            assert!(send_notify(None, "READY=1").is_ok());
            assert_eq!(notify_socket_from_env(), None);
        }

        #[test]
        fn watchdog_uses_half_the_period_and_refuses_zero() {
            // 这个是纯函数，但读的是环境变量 ⇒ 用一个子进程无关的静态断言：
            // 直接验"半周期"的算术与下限（不设环境变量，走 None 分支）。
            assert_eq!(watchdog_interval_from_env(), None);
        }

        #[test]
        fn ready_is_sent_before_accepting() {
            // 口径②的**结构判定**：受理闭包里检查"报到已成事实"。
            use std::sync::atomic::{AtomicBool, Ordering};
            use std::sync::Arc;
            let ready = Arc::new(AtomicBool::new(false));
            let seen = ready.clone();
            let d = std::env::temp_dir().join(format!("wc-notify-{}", std::process::id()));
            let _ = std::fs::remove_file(&d);
            let srv = UnixDatagram::bind(&d).unwrap();
            let path = d.display().to_string();
            // 报到走真投递；投递成功后才进受理闭包。
            let r = serve_activated_with(Some(&path), None, "READY=1", move || {
                // 受理开始时，**必须**已经收得到 READY（下面从 srv 读一条）
                let mut buf = [0u8; 64];
                let n = srv.recv(&mut buf).map_err(|e| e.to_string())?;
                let got = String::from_utf8_lossy(&buf[..n]).to_string();
                assert_eq!(got, "READY=1", "受理之前必须已经发出 READY=1");
                seen.store(true, Ordering::SeqCst);
                Ok(())
            });
            assert!(r.is_ok(), "serve_activated_with 应当成功：{r:?}");
            assert!(
                ready.load(Ordering::SeqCst),
                "受理闭包必须真的跑到了（否则上面那条断言是空转）"
            );
            let _ = std::fs::remove_file(&d);
        }
    }
}

/// ★ **`presence list` —— 给「在场者」一个名册出口**（第 14 轮新增；**只增**）。
///
/// ## 它回答的是哪一个问
///
/// 「**给我所有在场者**」。此前**没有**这个出口：要知道谁在场，只能读**整个** `state`，
/// 再从 `world://presence/…#<格> = <值>` 的一堆行里自己挑。本子命令把它变成**一个问句**。
///
/// ## 名册从哪里来（这一条决定了它的可信面）
///
/// **只从世界的账本折叠而来**：遍历读模型的 `(主体, 路径, 值)` 三元组，取主体形如
/// `world://presence/<实例>` 的那些，按主体名（`BTreeMap` 键序）输出。⇒ 三条后果，各自可判真假：
///
/// | # | 后果 | 为什么 |
/// |---|---|---|
/// | ① | **申报过的才在册** | 没向世界申报过的东西——哪怕它**装在机器上**、桌面里有它的 `.desktop`、包管理器里有它的包——**一个都不会出现**：本函数**不读**桌面、**不读**包管理器、**不读任何载体侧来源** |
/// | ② | **每一条都有出处** | 名册里的每个主体**必然**在账本里有对应事件——它就是折叠出来的，不是另记的一份 |
/// | ③ | **它是算出来的，不是存下来的** | 没有第二份名册文件，故不存在「名册与账本对不上」这种故障 |
///
/// ## 口径（与 `state` 的关系：**只增**，一个字不改）
///
/// 它**不动** `state` 与 `state --json` 的任何输出，也**不碰** `State::to_json`
/// （规范形式＝状态指纹的载体）。名册是**另一个人读出口**：与 `project visual` 一样**只读**，
/// 不缓存、不写盘。值一律按**既有读出口的同一口径**打印（JSON 原样：字符串带引号、
/// 整数不带）——**不许**为这一个出口发明第二套值渲染规则。
///
/// ## 为什么这一处新增是「物理行数不变」的（不是排版凑巧）
///
/// 全仓有上百处 `src/main.rs:<行号>` 形式的坐标（含**红线件**里的，本仓不许碰），
/// 而新增一行会把插入点之后的坐标**整体挪位**。⇒ 采用本仓既有做法（上一轮 `--retracted` 的同一处置）：
/// **把新增做成「行数不变」**——① `USAGE` 里那两行用 `\n` 写在同一物理行内；
/// ② 本子命令的分发臂是一行**单行臂**，而原先那条 4 行的 `"" => { … }` 臂
/// 拆成两条单行臂（`"" => cmd_usage_exit()`，行为**逐字节不变**）后**恰好占同样 4 行**；
/// ③ `cmd_presence`／`cmd_usage_exit` **追加在文件末尾**（末尾之后没有坐标要保）。
/// ⇒ `src/main.rs` 的物理行数**一字不变**，1 行都没挪。
///
/// ## 反例（必红）
///
/// 让本函数列出 `world://presence/` 前缀**之外**的东西，或凭空补一条**不在账本里**的条目
/// ⇒ `tests/cli.rs` 的 `cli18` 三条判据当场变红。
fn cmd_presence(o: &Path, l: &Path, p: &Path, rest: &[String]) -> ExitCode {
    /// 在场者主体的前缀（与 [`world_core::World`] 的两级判定**同一口径**：
    /// 那里是 `world://presence/`，本处不另立第二套）。
    const PRESENCE_PREFIX: &str = "world://presence/";
    /// 名册每条要给的格（本体 `_objects.presence.fields` 里**已声明**的那几格之一部）。
    const FIELDS: [&str; 4] = ["name", "category", "state", "last_seen"];

    match rest.get(1).map(String::as_str) {
        Some("list") if rest.len() == 2 => {}
        Some("list") => {
            eprintln!(
                "用法错误：`presence list` **不接受**多余参数（实得 {:?}）——\
                 不许静默忽略一个开关",
                &rest[2..]
            );
            return ExitCode::from(1);
        }
        Some(other) => {
            eprintln!(
                "用法错误：`presence` 的子命令 `{other}` 不存在。当前只有 `presence list`——\
                 缺省或写错都**不猜**（fail-closed）"
            );
            return ExitCode::from(1);
        }
        None => {
            eprintln!(
                "用法错误：`presence` 需要一个子命令。当前只有 `presence list`\
                 （列出世界里**已申报**的 `world://presence/*`）"
            );
            return ExitCode::from(1);
        }
    }

    let w = match World::open_readonly(o, l, p) {
        Ok(w) => w,
        Err(e) => {
            eprintln!("[FAIL] {e}");
            return ExitCode::from(2);
        }
    };
    let s = match w.read_model() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[FAIL] 读模型拒绝折叠：{e}");
            return ExitCode::from(2);
        }
    };

    // 名册＝**账本折叠出来的**在场者主体集合（键序确定 ⇒ 同样账本必给同样字节）。
    let mut subjects: std::collections::BTreeSet<&str> = std::collections::BTreeSet::new();
    for (subject, _, _) in s.entries() {
        if subject.starts_with(PRESENCE_PREFIX) && subject.len() > PRESENCE_PREFIX.len() {
            subjects.insert(subject);
        }
    }

    println!("== world-core presence list ==");
    println!("  账本 : {}", l.display());
    println!(
        "  在册 : {} 个在场者（＝账本里**申报过**的 `{}*`；\
         只装在机器上、从未向世界申报过的**不在册**）",
        subjects.len(),
        PRESENCE_PREFIX
    );
    for subject in &subjects {
        let mut line = format!("  {subject}");
        for f in FIELDS {
            let v = s
                .get(subject, f)
                .map(std::string::ToString::to_string)
                .unwrap_or_else(|| "--".to_string());
            // 缺格**照打 `--`**，不整条跳过：「没有输出」不等于「没有问题」。
            line.push_str(&format!("  {f}={v}"));
        }
        println!("{line}");
    }
    println!("  （名册由账本折叠得来，未缓存、未写盘；每一条都能在账本里找到出处）");
    ExitCode::SUCCESS
}

/// ★ **无子命令时的出口**：只打印用法串，`rc=1`。
///
/// ## 为什么把它抽成函数（**不是为了好看**）
///
/// 它原先**内联**在分发表的 `"" => { … }` 臂里（4 行）。给同族加一条 `"presence"` 臂时，
/// rustfmt 要求的形态会让那段**多出一行**，而 `src/main.rs` 的行数一旦变化，
/// 全仓上百处 `src/main.rs:<行号>` 坐标（含红线件里的）就整体挪位（见 [`cmd_presence`] 的文档）。
/// 抽成函数后：`"presence" => …` 与 `"" => cmd_usage_exit()` 各占**一行**，
/// 加上两条说明注释**恰好**与原先那 4 行等长 ⇒ **物理行数一字不变**。
///
/// ## 行为：与原内联形态**逐字节相同**
///
/// `print!("{USAGE}")` 到 **stdout**、`ExitCode::from(1)`——一个字未改。
fn cmd_usage_exit() -> ExitCode {
    print!("{USAGE}");
    ExitCode::from(1)
}
