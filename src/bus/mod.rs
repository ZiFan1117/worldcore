//! 通道（`M09`/`IF-006`）—— **跨进程入口，身份由内核给出，不由请求自称**。
//!
//! ## 它解决的那个洞
//!
//! 此前唯一入口是 CLI，而 CLI 的 `actor` 是**命令行参数**——被管者只要自称
//! `world://user` 就能冒充最高权主体（`WC-RV-R2-001` **FIND-06** / 假设 `A-06`）。
//! 门禁的白名单因此只在"没人说谎"的前提下成立。
//!
//! 本模块把身份来源换成**内核**：每个监听套接字绑定一个 `uid → actor` 映射，
//! 连接建立后用 `peer_cred()` 取对端 uid，**与本套接字允许的 uid 比对**；
//! 请求体里若写了别的 `actor`，**直接拒绝**——身份不可自称。
//!
//! ## 身份是怎么被强制的（以及为什么不需要 libc）
//!
//! **实测事实**：`UnixStream::peer_cred()` 在 `rustc 1.98.1` 上仍是
//! **不稳定 API**（`error[E0658]: use of unstable library feature
//! peer_credentials_unix_socket`）——原设计打算用它，编译直接把该假设否掉了。
//!
//! 改用**更强也更简单**的机制：**一个套接字对应一个身份**。
//! `bind()` 在创建套接字后就地 `chown` 给该身份的目标 uid、`chmod 0600`，
//! 并拒绝在"对 group/other 可写"的目录里创建。于是：
//!
//! - **只有那个 uid 连得上**——内核在 `connect()` 时就挡住别人，
//!   **比"连上来再问你是谁"更早、更硬**；
//! - 身份来源不再依赖任何"取对端凭证"的 API，故**零新增依赖**
//!   （只用 `std::os::unix::fs::chown`，它是 std 稳定 API），符合 `REQ-N-002`。
//!
//! ⚠️ 代价：套接字文件的权限与目录权限成为**安全前提**（与法律/账本同一类保证），
//! 故 `bind()` 会像静态墙一样检查目录，并把 mode 收紧到 `0600`。
//!
//! ## 协议（纯文本、语言无关：一行请求 → 一行应答）
//!
//! ```text
//! 请求: {"kind":"act","body":{...}}        （**不含** actor；含则必须与内核身份一致）
//! 应答: {"ok":true,"event":{…}}            / {"ok":false,"error":"…"}
//! ```
//!
//! ## 配置（纯文本 JSON，`channel.json`）
//!
//! ```json
//! { "channel": 1,
//!   "listeners": [ { "socket": "/run/world/agent-1.sock", "actor": "world://agent/1", "uid": 1001 } ] }
//! ```
//!
//! ## 四个资源边界（`REQ-F-026`）
//!
//! 「一条连接就能拖垮世界」是这个入口的固有风险，故四个边界各有数值、各有超限行为，
//! 且超限**拒得可核**（点名错误码 ＋ 上限的**当前值**，并回一行给对端）：
//!
//! | 边界 | 数值从哪来 | 超限错误码 | 可核形态 |
//! |---|---|---|---|
//! | 并发连接数 | `Limits::max_connections`（出厂配置；v1 只能为 1） | `Channel.TooManyConnections` | 与服务重叠期间到达的连接被拒 |
//! | 单条消息字节 | `Limits::max_line_bytes` | `Channel.LineTooLong` | 读到超限那一刻即停，**不无限缓冲** |
//! | 每秒消息数 | `Limits::max_msgs_per_sec`（**每身份**，跨连接累计） | `Channel.RateLimited` | 同一秒内第 n+1 条被拒 |
//! | 空闲超时 | `Limits::idle_timeout_ms`（读一行 / 写一行共用） | `Channel.IdleTimeout` | 连上不发请求即被断开 |
//!
//! 四个数**只**来自出厂配置——本模块**没有**这四个数的任何缺省值：
//! 由 `Limits::from_policy` 读出；读不到即拒启——「通道的资源边界没有数值就不许受理」，
//! 与「策略空表不许上电」同一条纪律。
//!
//! 四者**都不落笔**（世界状态不变）；**都不留账本流水**（理由见 `Limits::from_policy`
//! 与出厂配置 `channel_limits._not_logged` 一栏：M09 按 `IF-006-R04` 不持有账本写句柄）。
//!
//! ## v1 的局限（不假装满足）
//!
//! - 只在 **Unix** 上可用（`cfg(unix)`）；
//! - **顺序受理**：一次只服务一个连接。故 `max_connections` **只能为 1**——
//!   给更大的值即拒启（`Channel.BadConcurrency`）。真正的并发受理需要多线程服务端
//!   与单写者串行化（书 §6.4「序号由唯一写账者分配」），本轮**未做**，
//!   也不假装做到了；
//! - 库内裸原语 `serve_once`／`serve_n` 是**显式不设界**的（`Limits::none()`）：
//!   它们是"一次一连接"的原语、不是产品入口，且被 `scripts/test/contract.rs::c14` 直调
//!   （该文件不在本工区的文件面内）。**产品入口**（`world-core … channel accept|serve`）
//!   一律经 `Limits::from_policy` 取四个数值，取不到即拒启。⇒ 裸原语这条口子
//!   **如实登记**，未合上；
//! - 不做鉴权之外的传输保护（本机 Unix 套接字 + 文件权限即其边界）。

use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::io::{BufRead, BufReader, ErrorKind, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

/// **通道对内核提出的唯一要求**：把一条已经验明身份的请求交给世界落笔。
///
/// 为什么要有这一层（而不是直接 `use crate::World`）：`M09`（通道）与 `M04`（运行时）
/// 若互相 `use`，模块号图上就是一条**双向边**，而 `WC-ATOM-001` §二 A-4 要求依赖**单向 DAG**。
/// 事实本来也是单向的——**运行时驱动通道**（`src/main.rs:622 use world_core::bus::…`），
/// 通道只在"这条请求交给谁"上需要一个**受方**。用一个窄接口把这件事写进类型：
/// 通道**不认识 `World`**，只认识"能收下这条请求的东西"。
///
/// 接口宽度刻意压到**一处**（`commit_requested`），签名与 `World::commit_requested`
/// **逐字相同**；`impl` 是**纯转发**，不改变"唯一写入口"的任何语义
/// （取号 → 造事件 → 法律 → 门禁 → 落笔 仍在 `M04` 一条路上）。
pub trait RequestSink {
    /// 落一条**已经验明身份**的请求：`actor` 由套接字映射给出，**不取自请求体**。
    fn commit_requested(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        trace: Option<&str>,
        to: Option<&str>,
    ) -> Result<Value, String>;
}

/// 一条监听项：套接字路径 ↔ 身份。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Listener {
    pub socket: PathBuf,
    pub actor: String,
    pub uid: u32,
}

/// 通道配置。
#[derive(Debug, Clone)]
pub struct ChannelConfig {
    listeners: Vec<Listener>,
}

impl ChannelConfig {
    /// 从纯文本 JSON 加载。
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Channel.ReadFail: {}: {e}", path.display()))?;
        let v: Value = serde_json::from_str(&text)
            .map_err(|e| format!("ext.world.Channel.BadJson: {}: {e}", path.display()))?;
        let ver = v
            .get("channel")
            .and_then(Value::as_u64)
            .ok_or_else(|| "ext.world.Channel.NoVersion: 缺 `channel` 版本号".to_string())?;
        if ver != 1 {
            return Err(format!("ext.world.Channel.BadVersion: 期望 1，实得 {ver}"));
        }
        let arr = v
            .get("listeners")
            .and_then(Value::as_array)
            .ok_or_else(|| "ext.world.Channel.NoListeners: 缺 `listeners`".to_string())?;
        if arr.is_empty() {
            return Err(
                "ext.world.Channel.NoListeners: listeners 为空——没有身份映射的通道等于无门之门"
                    .to_string(),
            );
        }
        let mut listeners = Vec::new();
        for item in arr {
            let socket = item
                .get("socket")
                .and_then(Value::as_str)
                .ok_or_else(|| "ext.world.Channel.BadListener: 缺 socket".to_string())?;
            let actor = item
                .get("actor")
                .and_then(Value::as_str)
                .ok_or_else(|| "ext.world.Channel.BadListener: 缺 actor".to_string())?;
            let uid = item
                .get("uid")
                .and_then(Value::as_u64)
                .ok_or_else(|| "ext.world.Channel.BadListener: 缺 uid".to_string())?;
            listeners.push(Listener {
                socket: PathBuf::from(socket),
                actor: actor.to_string(),
                uid: uid as u32,
            });
        }
        Ok(ChannelConfig { listeners })
    }

    pub fn listeners(&self) -> &[Listener] {
        &self.listeners
    }

    /// 按套接字路径找监听项（服务端据它决定"这条连接代表谁"）。
    pub fn listener_for(&self, socket: &Path) -> Option<&Listener> {
        self.listeners.iter().find(|l| l.socket == socket)
    }

    /// 加载渲染物**并逐条对回在册**——「身份映射只许有一处权威」在**受理期**的落点。
    ///
    /// ## 它解决的那个洞（本模块今天最要紧的一条）
    ///
    /// **受理路径只读渲染物**：`serve` 从继承来的 fd 取套接字路径 → [`Self::load`] →
    /// [`Self::listener_for`]；而**法律那份 `listeners` 在运行路径上零读者**。
    /// 于是渲染物事实上是**第二在册**：往它里面凭空加一行映射，口就能起、
    /// 账本里就会多出一个法律里没有的身份，而**没有任何东西会红**。
    /// `policy.json._listeners_note` 自己写着「总线上**不得**凭另一份配置文件自行定义映射」——
    /// 本函数就是那句话的执行体。
    ///
    /// ## 口径（四条，都可判真假）
    ///
    /// - 对账键是 **(socket, actor) 同时相同**：只对 socket 不够——同一个口换个身份也是账外口；
    /// - 法律读不出来 ⇒ **拒启**（[`declared_listeners`] 的 `Channel.NoDeclaredListeners`）：
    ///   没有在册表就没有对账基准，而「基准缺失」**不许**被读成「没有账外口」；
    /// - 账外口 ⇒ **拒启**（`Channel.UndeclaredListener`），并**点名**那一条；
    /// - 它**不判**「在册未上线」（法律里登记了、今天没起）：那是合法状态
    ///   （法律的本分是「先声明、后使用」），**单独报、不在这里红**。
    ///
    /// 反例（必红）：往渲染物里加一行 `{socket: …/ghost.sock, actor: world://ghost, uid: …}`
    /// ⇒ `cmd_serve` 在**受理之前** rc=2 退出（见 `scripts/test/channel_bounds.rs::l07`）。
    pub fn load_checked(cfg: &Path, policy: &Path) -> Result<Self, String> {
        let conf = Self::load(cfg)?;
        let law = declared_listeners(policy)?;
        for l in &conf.listeners {
            let hit = law
                .iter()
                .any(|d| d.socket == l.socket && d.actor == l.actor);
            if !hit {
                return Err(format!(
                    "ext.world.Channel.UndeclaredListener: 渲染物 {} 里的口 {} → `{}` \
                     在法律 {} 的 `listeners` 里解析不到——**账外口一律拒启**。\n\
                     \x20 身份映射只许有一处权威（法律）；渲染物只是它的渲染物。\n\
                     \x20 处置：往法律那一节补上这条绑定（改法律走 R5），\
                     或用 tools/render_channel.py 按法律重新渲染。",
                    cfg.display(),
                    l.socket.display(),
                    l.actor,
                    policy.display()
                ));
            }
        }
        Ok(conf)
    }
}

/// 法律里的一条在册绑定（`policy.json.listeners` 的 `socket`／`actor`）。
///
/// **它就是「对账基准」的形状**：渲染物每一条都必须能在这些对里解析到。
/// `owner`（名字）不进这里——把名字换成 uid 是**部署面**的事（那台机器上谁是这个用户），
/// 本模块不读用户库。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Declared {
    pub socket: PathBuf,
    pub actor: String,
}

/// 从**法律**读在册表（`policy.json` 的 `listeners`）——身份映射的唯一权威。
///
/// fail-closed：文件读不出／不是 JSON／没有 `listeners`／它是空的／某条缺 `socket` 或 `actor`
/// ⇒ 一律 `Channel.NoDeclaredListeners` **拒启**并点名。理由与 `ChannelConfig::load`
/// 对空 `listeners` 的口径同源：**没有身份映射的通道等于无门之门**；
/// 而这里多一条——**没有在册表就没有对账基准**，报绿就等于"没查"。
pub fn declared_listeners(policy: &Path) -> Result<Vec<Declared>, String> {
    let text = std::fs::read_to_string(policy)
        .map_err(|e| format!("ext.world.Channel.ReadFail: {}: {e}", policy.display()))?;
    let v: Value = serde_json::from_str(&text)
        .map_err(|e| format!("ext.world.Channel.BadJson: {}: {e}", policy.display()))?;
    let arr = v
        .get("listeners")
        .and_then(Value::as_array)
        .ok_or_else(|| {
            format!(
                "ext.world.Channel.NoDeclaredListeners: {} 里没有 `listeners` 段——\
                 法律是身份映射的唯一权威，它缺了这一节就没有对账基准",
                policy.display()
            )
        })?;
    if arr.is_empty() {
        return Err(format!(
            "ext.world.Channel.NoDeclaredListeners: {} 的 `listeners` 是空的——\
             没有身份映射的通道等于无门之门",
            policy.display()
        ));
    }
    let mut out = Vec::new();
    for item in arr {
        let socket = item.get("socket").and_then(Value::as_str).ok_or_else(|| {
            format!(
                "ext.world.Channel.NoDeclaredListeners: {} 的某条 listeners 缺 `socket`",
                policy.display()
            )
        })?;
        let actor = item.get("actor").and_then(Value::as_str).ok_or_else(|| {
            format!(
                "ext.world.Channel.NoDeclaredListeners: {} 的某条 listeners 缺 `actor`",
                policy.display()
            )
        })?;
        out.push(Declared {
            socket: PathBuf::from(socket),
            actor: actor.to_string(),
        });
    }
    Ok(out)
}

/// **四个资源边界的数值**（`REQ-F-026`）。
///
/// | 字段 | 边界 | 单位 | 超限错误码 |
/// |---|---|---|---|
/// | `max_connections` | 并发连接数 | 条 | `Channel.TooManyConnections` |
/// | `max_line_bytes` | 单条消息字节数（**不含**行尾换行） | 字节 | `Channel.LineTooLong` |
/// | `max_msgs_per_sec` | 每秒消息数（**每身份**，跨连接） | 条/秒 | `Channel.RateLimited` |
/// | `idle_timeout_ms` | 空闲超时（读一行请求 / 写一行应答共用） | 毫秒 | `Channel.IdleTimeout` |
///
/// ⚠️ **代码里没有这四个数的缺省值**：它们只来自出厂配置（`from_policy`）。
/// 这一条不是文风问题——一有缺省值，"数值是多少"就有了第二个权威载体，
/// 而配置改不动行为时**没有任何东西会红**。机器判据：配置里缺 `channel_limits`
/// 块 ⇒ `Channel.NoLimits` 拒启（见 `scripts/test/channel_bounds.rs::l05`）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    pub max_connections: usize,
    pub max_line_bytes: usize,
    pub max_msgs_per_sec: u32,
    pub idle_timeout_ms: u64,
}

impl Limits {
    /// 从**出厂策略**文件读四个数值（本仓的落点是 `src/gate/policy.json` 的
    /// `channel_limits` 块）。
    ///
    /// 为什么落在这里而不是新立一份出厂 `channel.json`：该文件本仓不存在，
    /// 且「是否补一份出厂 `channel.json`」在 `WC-SCMP-001` §8.4 **`G-28`** 记着
    /// **待人裁定**（本工区不代选）；`ontology.json` 受词表身份约束（动一个非 `_` 键
    /// 就换掉 `fnv1a64` 身份）。⇒ 四个数放在已受控的那份出厂配置里。
    ///
    /// **fail-closed**：缺块、缺项、取 0、或并发上限 ≠ 1，一律**拒启**
    /// （`Channel.NoLimits` / `Channel.BadLimits` / `Channel.BadConcurrency`），
    /// 并**点名**是哪一项、当前值是多少。「没写」不许被读成「不设界」——
    /// 与 `ChannelConfig::load` 对空 `listeners` 的口径同源（那里的错误码是
    /// `Channel.NoListeners`，理由逐字为「没有身份映射的通道等于无门之门」）。
    pub fn from_policy(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Channel.ReadFail: {}: {e}", path.display()))?;
        let v: Value = serde_json::from_str(&text)
            .map_err(|e| format!("ext.world.Channel.BadJson: {}: {e}", path.display()))?;
        let blk = v.get("channel_limits").ok_or_else(|| {
            format!(
                "ext.world.Channel.NoLimits: {} 里没有 `channel_limits` 块——\
                 通道的四个资源边界（并发连接数/单条消息字节/每秒消息数/空闲超时）没有数值，\
                 就不许受理（REQ-F-026）",
                path.display()
            )
        })?;
        let num = |k: &str| -> Result<u64, String> {
            blk.get(k).and_then(Value::as_u64).ok_or_else(|| {
                format!(
                    "ext.world.Channel.BadLimits: {} 的 channel_limits.{k} 缺失或不是非负整数",
                    path.display()
                )
            })
        };
        let max_connections = num("max_connections")?;
        let max_line_bytes = num("max_line_bytes")?;
        let max_msgs_per_sec = num("max_msgs_per_sec")?;
        let idle_timeout_ms = num("idle_timeout_ms")?;
        for (k, n) in [
            ("max_connections", max_connections),
            ("max_line_bytes", max_line_bytes),
            ("max_msgs_per_sec", max_msgs_per_sec),
            ("idle_timeout_ms", idle_timeout_ms),
        ] {
            if n == 0 {
                return Err(format!(
                    "ext.world.Channel.BadLimits: {} 的 channel_limits.{k} = 0——\
                     本版不提供「不设界」的配置写法：边界要么有值，要么不许上电",
                    path.display()
                ));
            }
        }
        // v1 是**顺序受理**（一次一连接）⇒ 并发上限只能是 1。
        // 给更大的值 = 要求"真正的并发受理"，而 v1 做不到 ⇒ **拒启，不许假装**。
        if max_connections != 1 {
            return Err(format!(
                "ext.world.Channel.BadConcurrency: {} 的 channel_limits.max_connections = {max_connections}，\
                 而 v1 是顺序受理（一次一连接）⇒ 只支持 1。\
                 真正的并发受理需要多线程服务端与单写者串行化（书 §6.4），本轮未做",
                path.display()
            ));
        }
        if max_msgs_per_sec > u64::from(u32::MAX) {
            return Err(format!(
                "ext.world.Channel.BadLimits: {} 的 channel_limits.max_msgs_per_sec = {max_msgs_per_sec} 超出上界",
                path.display()
            ));
        }
        Ok(Self {
            max_connections: max_connections as usize,
            max_line_bytes: max_line_bytes as usize,
            max_msgs_per_sec: max_msgs_per_sec as u32,
            idle_timeout_ms,
        })
    }

    /// **显式不设界**（哨兵值，**不是**四个数的缺省值）。
    ///
    /// 只给库内裸原语 `serve_once`／`serve_n` 用：它们是"一次一连接"的**原语**
    /// （`scripts/test/contract.rs::c14` 直调，该文件不在本工区文件面内），
    /// 而 `scripts/test/contract.rs::c14` 要验的是"身份来自内核"这件事。
    /// 产品入口一律经 `from_policy`——**这条口子如实登记在模块文档的「v1 的局限」里**。
    pub fn none() -> Self {
        Self {
            max_connections: usize::MAX,
            max_line_bytes: usize::MAX,
            max_msgs_per_sec: u32::MAX,
            idle_timeout_ms: 0,
        }
    }

    /// 是否是不设界的哨兵（`none()`）。
    pub fn is_none(&self) -> bool {
        *self == Self::none()
    }
}

/// 一条通道的**会话状态**：限流窗口（每身份一份）。
///
/// 为什么不放在一次 `serve_once` 的局部：一次跨进程往返天然是**两个连接**
/// （先交意图、后交结果，见 `serve_n` 的文档），而"每秒消息数"要跨连接累计才成立。
pub struct Session {
    limits: Limits,
    windows: BTreeMap<String, (Instant, u32)>,
}

impl Session {
    pub fn new(limits: Limits) -> Self {
        Self {
            limits,
            windows: BTreeMap::new(),
        }
    }

    pub fn limits(&self) -> Limits {
        self.limits
    }

    /// 记一次请求并按**每秒消息数上限**裁决（固定窗口：1 秒）。
    ///
    /// 超限 ⇒ `Channel.RateLimited` 并**点名上限与当前计数**。
    /// 计数在裁决**之前**自增：被拒的那一条也占窗口，否则"每秒上限"挡不住连打。
    fn admit(&mut self, actor: &str, now: Instant) -> Result<(), String> {
        let win = self.windows.entry(actor.to_string()).or_insert((now, 0));
        if now.duration_since(win.0) >= Duration::from_secs(1) {
            *win = (now, 0);
        }
        win.1 += 1;
        if win.1 > self.limits.max_msgs_per_sec {
            return Err(format!(
                "ext.world.Channel.RateLimited: 每秒消息数上限 max_msgs_per_sec={}（本秒第 {} 条）",
                self.limits.max_msgs_per_sec, win.1
            ));
        }
        Ok(())
    }
}

/// 一条请求的解析结果。
#[derive(Debug, PartialEq)]
pub struct Request {
    pub kind: String,
    pub body: Value,
    /// 请求**自称**的 actor（可选）。存在时必须与内核身份一致，否则拒绝。
    pub claimed_actor: Option<String>,
    /// 因果（可选）：引发本条的那条事件的 `id`。
    ///
    /// 跨进程的"请求—结果"配对靠它闭环：结果的 `trace` 指向意图的 `id`。
    /// **不做引用完整性校验**（`REQ-F-031` 的 v1 口径）。
    pub trace: Option<String>,
}

/// 解析一行请求。
pub fn parse_request(line: &str) -> Result<Request, String> {
    let v: Value = serde_json::from_str(line)
        .map_err(|e| format!("ext.world.Channel.BadRequest: 不是合法 JSON：{e}"))?;
    let kind = v
        .get("kind")
        .and_then(Value::as_str)
        .ok_or_else(|| "ext.world.Channel.BadRequest: 缺 kind".to_string())?
        .to_string();
    let body = v.get("body").cloned().unwrap_or(Value::Null);
    let claimed_actor = v.get("actor").and_then(Value::as_str).map(str::to_string);
    // 空串视为未给：否则会写出一条指不到任何事件的 trace。
    let trace = v
        .get("trace")
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .map(str::to_string);
    Ok(Request {
        kind,
        body,
        claimed_actor,
        trace,
    })
}

/// 处理**一个**连接（v1：一次一条）。
///
/// 身份规则（本模块的全部意义所在）：连接能建立这件事本身**已经**证明了对端 uid
/// （套接字权限由 `bind()` 收紧，见其文档）；请求若自称 actor，必须与
/// `listener.actor` 一致，否则拒绝；落笔时的 `actor` 一律取自**身份映射**，
/// **绝不取请求里的字符串**。
/// 按监听项创建套接字：**权限即身份**。
///
/// 步骤：删掉可能存在的陈旧套接字文件 → 拒绝在"对 group/other 可写"的目录里建
/// （否则套接字可被替换，与法律/账本同理）→ `bind` 后立刻 `chmod 0600`
/// 并 `chown` 给该身份的目标 uid ⇒ **只有那个 uid 能 connect**
/// （内核在连接时就挡住别人）。
#[cfg(unix)]
pub fn bind(expect: &Listener) -> Result<std::os::unix::net::UnixListener, String> {
    use std::os::unix::fs::PermissionsExt;

    if let Some(dir) = expect.socket.parent() {
        crate::gate::guard::assert_not_other_writable(dir, "通道目录")?;
    }
    let _ = std::fs::remove_file(&expect.socket);
    let listener = std::os::unix::net::UnixListener::bind(&expect.socket).map_err(|e| {
        format!(
            "ext.world.Channel.BindFail: {}: {e}",
            expect.socket.display()
        )
    })?;
    std::fs::set_permissions(&expect.socket, std::fs::Permissions::from_mode(0o600))
        .map_err(|e| format!("ext.world.Channel.ChmodFail: {e}"))?;
    std::os::unix::fs::chown(&expect.socket, Some(expect.uid), None).map_err(|e| {
        format!(
            "ext.world.Channel.ChownFail: {}: {e}",
            expect.socket.display()
        )
    })?;
    // **把套接字留在文件系统里**（刻意）：
    //
    // `UnixListener` 的 `Drop` 会把 socket 文件删掉。若照默认行为走，
    // "起一个监听者 → 收一个连接 → 退出"就会**把套接字一起带走**，
    // 下一个连接只会得到 `Connection refused`——而这是**监听者的生命周期**
    // 问题，不该表现成"服务没了"。
    //
    // 这一步把它转成原始描述符：进程退出后**描述符关闭、文件留下**，
    // 于是"再起一个监听者接着收"是可行的（世界核心 v1 一次一连接的分帧方式）。
    // 文件残留由下一次 `bind` 开头的 `remove_file` 负责清理（与原先同口径）。
    let raw = std::os::unix::io::IntoRawFd::into_raw_fd(listener);
    // SAFETY：`raw` 来自刚 `bind` 成功的监听套接字，所有权随此次转换移交给我们，
    // 之后不再有第二个所有者会关闭它（`FromRawFd` 只在同一处使用一次）。
    let listener = unsafe {
        <std::os::unix::net::UnixListener as std::os::unix::io::FromRawFd>::from_raw_fd(raw)
    };
    Ok(listener)
}

/// **连续收 `n` 个连接**（v1 的"长驻"形态）—— `serve_n_with` 的**不设界**薄壳。
///
/// 为什么需要它：一次跨进程往返天然是**两个连接**（先交意图、后交结果）。
/// 每次调用方都自己 `bind` 一遍，就等于把套接字反复删建——那既不是"总线"该有的样子，
/// 也会把正在排队的连接一起弄丢。
///
/// 口径：**收满 `n` 个就把监听者交还给调用方**（不自己退出），
/// 由调用方决定还要不要继续收。任一连接处理失败**不中止后续**——
/// 一次坏请求不该让总线停摆；但错误会如实打印。
///
/// ⚠️ 本函数传 `Limits::none()`：**不受四个资源边界约束**。它是库内裸原语；
/// **产品入口**走 `serve_n_with` ＋ `Limits::from_policy`（见 `src/main.rs` 的
/// `cmd_channel`）。这条口子如实登记在模块文档的「v1 的局限」里。
#[cfg(unix)]
pub fn serve_n(
    sink: &mut impl RequestSink,
    listener: &std::os::unix::net::UnixListener,
    expect: &Listener,
    n: usize,
) -> Result<usize, String> {
    serve_n_with(sink, listener, expect, &mut Session::new(Limits::none()), n)
}

/// **收 `n` 个连接**，**四个资源边界真的生效**的那一条路（`REQ-F-026`）。
///
/// 与 `serve_n` 的差别**只有一处**：界限从 `session` 来（产品入口由出厂配置填），
/// 于是四条边界的判定只有**一份实现**（`serve_stream` 与 `refuse_pending`）。
///
/// 并发上限怎么落地（v1 顺序受理，故 `max_connections` 只能为 1）：
/// 服务一条连接**期间**到达的连接，都是"同时受理"的违反者 ⇒
/// **每次服务结束、下一次阻塞受理之前**，把此刻还在队列里的连接逐条拒掉
/// （`refuse_pending`），再继续等下一条。这样"同时开两条 ⇒ 第二条被拒"是
/// 可判定的，而不是"取决于调度"。
#[cfg(unix)]
pub fn serve_n_with(
    sink: &mut impl RequestSink,
    listener: &std::os::unix::net::UnixListener,
    expect: &Listener,
    session: &mut Session,
    n: usize,
) -> Result<usize, String> {
    let mut ok = 0usize;
    while ok < n {
        let (stream, _) = listener
            .accept()
            .map_err(|e| format!("ext.world.Channel.AcceptFail: {e}"))?;
        match serve_stream(&mut *sink, stream, expect, session) {
            Ok(_) => ok += 1,
            Err(e) => eprintln!("[FAIL] {e}"),
        }
        let refused = refuse_pending(listener, session.limits())?;
        if refused > 0 {
            eprintln!(
                "[FAIL] ext.world.Channel.TooManyConnections: 并发上限 max_connections={}，\
                 服务期间到达的 {refused} 条连接一并拒绝",
                session.limits().max_connections
            );
        }
    }
    Ok(ok)
}

/// 多口轮询时"所有口都空"的等待间隔（毫秒）。
///
/// 为什么要有它：本仓只许 `serde_json` 一个 crate family ⇒ 没有 `poll(2)`/`epoll` 可用，
/// 于是"同时等多个口"只能**非阻塞轮询 ＋ 短睡**。10ms 是取舍：口空闲时每 10ms 醒一次
/// （可忽略的 CPU），而一次点击的响应延迟上限就是这 10ms（对人手不可感知）。
const MULTI_LISTEN_TICK_MS: u64 = 10;

/// **一次受理多个口**（`(甲-e)`：载体把 n 个 fd **一次**交过来，**每个口各自的 socket 单元**带自己的身份）。
///
/// ## 它解决的那个洞（现场实测过）
///
/// `serve_n_with` 一次只服务**一个** `UnixListener`。多口若各起一个循环串行跑，
/// **口 A 上的一条连接会让口 B 的连接一直等在队列里**——而"空闲超时"是**口上**的边界，
/// 于是用户看到的是"另一个口坏了"，不是"它在排队"。⇒ 本函数用**单线程轮询**把它消掉。
///
/// ## ★ 它**不是**并发受理（口径不许被读大）
///
/// - **仍然是同一个写者**（不许 fork、不许起第二个服务）；
/// - **仍然是一次一条**：`max_connections` 只能为 1 那条**架构事实没动**、
///   `BadConcurrency` 一个字没改；本函数只把"要等谁让出循环"消掉；
/// - 代价（如实登记）：所有口空闲时按 `MULTI_LISTEN_TICK_MS` 空转一次。
///
/// ## 判据（会红）
///
/// - **每个口各自认领身份**：`expects[i]` 必须是第 `i` 个口**自己的**绑定（调用方按该 fd 的
///   `local_addr()` 取）⇒ 反例（真实违规的形态）：给两个口传**同一个** `expect`
///   ⇒ 第二个口上落的话会挂在第一个口的身份下（那就是冒充）；
/// - 口与身份**必须一一对应且非空** ⇒ 否则 `Channel.BadListeners` 拒（不静默按第一个凑）；
/// - 任一连接的坏请求**不中止**其余口（与 `serve_n_with` 同口径：一次坏请求不该让总线停摆）。
#[cfg(unix)]
pub fn serve_all_with(
    sink: &mut impl RequestSink,
    listeners: &[std::os::unix::net::UnixListener],
    expects: &[Listener],
    session: &mut Session,
    n: usize,
) -> Result<usize, String> {
    if listeners.is_empty() || listeners.len() != expects.len() {
        return Err(format!(
            "ext.world.Channel.BadListeners: 口与身份映射必须一一对应且非空（实得 {} 个口 / {} 个身份）",
            listeners.len(),
            expects.len()
        ));
    }
    let lim = session.limits();
    for l in listeners {
        l.set_nonblocking(true)
            .map_err(|e| format!("ext.world.Channel.AcceptFail: 设非阻塞失败：{e}"))?;
    }
    let mut served = 0usize;
    while served < n {
        let mut did_work = false;
        for (i, l) in listeners.iter().enumerate() {
            match l.accept() {
                Ok((s, _)) => {
                    did_work = true;
                    s.set_nonblocking(false)
                        .map_err(|e| format!("ext.world.Channel.AcceptFail: 恢复阻塞失败：{e}"))?;
                    match serve_stream(&mut *sink, s, &expects[i], session) {
                        Ok(_) => served += 1,
                        Err(e) => eprintln!("[FAIL] {e}"),
                    }
                    let refused = refuse_pending(l, lim)?;
                    if refused > 0 {
                        eprintln!(
                            "[FAIL] ext.world.Channel.TooManyConnections: 并发上限 max_connections={}，\
                             服务期间到达的 {refused} 条连接一并拒绝",
                            lim.max_connections
                        );
                    }
                    // ★ `refuse_pending` 收尾会把监听者设回**阻塞** ⇒ 这里必须再设回非阻塞，
                    //   否则下一轮的 `accept()` 会阻塞在**第一个**口上，多口轮询当场失效。
                    l.set_nonblocking(true)
                        .map_err(|e| format!("ext.world.Channel.AcceptFail: 设非阻塞失败：{e}"))?;
                }
                Err(e) if e.kind() == ErrorKind::WouldBlock => {}
                Err(e) => return Err(format!("ext.world.Channel.AcceptFail: {e}")),
            }
        }
        if !did_work {
            std::thread::sleep(Duration::from_millis(MULTI_LISTEN_TICK_MS));
        }
    }
    Ok(served)
}

/// 受理并服务**一个**连接 —— `serve_once_with` 的**不设界**薄壳（见 `serve_n` 的同一条说明）。
#[cfg(unix)]
pub fn serve_once(
    sink: &mut impl RequestSink,
    listener: &std::os::unix::net::UnixListener,
    expect: &Listener,
) -> Result<Value, String> {
    serve_once_with(sink, listener, expect, &mut Session::new(Limits::none()))
}

/// 受理并服务**一个**连接，四个资源边界按 `session` 生效。
#[cfg(unix)]
pub fn serve_once_with(
    sink: &mut impl RequestSink,
    listener: &std::os::unix::net::UnixListener,
    expect: &Listener,
    session: &mut Session,
) -> Result<Value, String> {
    let (stream, _) = listener
        .accept()
        .map_err(|e| format!("ext.world.Channel.AcceptFail: {e}"))?;
    serve_stream(sink, stream, expect, session)
}

/// 把此刻**还在队列里**的连接逐条拒掉（`Channel.TooManyConnections`）。
///
/// 只在设了界（`max_connections` ≠ 哨兵）时动手；`Limits::none()` 下直接返回 0，
/// 于是裸原语 `serve_n` 的行为与本改动**之前一字不差**。
///
/// 为什么用非阻塞 `accept` 而不是"数一数"：队列长度没有可移植的读法，
/// 而"此刻还能不能收"只能由 `accept` 自己回答（`WouldBlock` ＝ 队列空了）。
#[cfg(unix)]
fn refuse_pending(
    listener: &std::os::unix::net::UnixListener,
    lim: Limits,
) -> Result<usize, String> {
    if lim.is_none() {
        return Ok(0);
    }
    listener
        .set_nonblocking(true)
        .map_err(|e| format!("ext.world.Channel.AcceptFail: 设非阻塞失败：{e}"))?;
    let mut n = 0usize;
    let out = loop {
        match listener.accept() {
            Ok((mut s, _)) => {
                let _ = s.set_nonblocking(false);
                if lim.idle_timeout_ms > 0 {
                    let d = Duration::from_millis(lim.idle_timeout_ms);
                    let _ = s.set_write_timeout(Some(d));
                }
                let msg = format!(
                    "ext.world.Channel.TooManyConnections: 并发上限 max_connections={}，\
                     本连接到达时已有 1 条在服务（v1 顺序受理：服务期间到达的连接一律拒）",
                    lim.max_connections
                );
                let _ = writeln!(s, "{}", json!({"ok": false, "error": msg}));
                n += 1;
            }
            Err(e) if e.kind() == ErrorKind::WouldBlock => break Ok(n),
            Err(e) => break Err(format!("ext.world.Channel.AcceptFail: {e}")),
        }
    };
    // 无论成败都要把监听者还原成阻塞模式：否则下一轮 `accept` 会空转。
    listener
        .set_nonblocking(false)
        .map_err(|e| format!("ext.world.Channel.AcceptFail: 恢复阻塞失败：{e}"))?;
    out
}

/// 服务**一条已受理的连接**：读一行 → 限流 → 解析 → 自称核对 → 落笔 → 回一行。
///
/// 顺序是刻意的：**资源边界在前、法律与门禁在后**——
/// 一条超长/超频/静默的连接**根本不是一条请求**，不该走到闸前面去。
/// 身份那一段（自称核对与"actor 取自映射"）**一字未改**：四边界与它无关，
/// 也不得借这 four 条口子放宽它。
///
/// 拒得可核：资源边界的每一条拒绝都**点名**（错误码 ＋ 上限的**当前值**）并**回一行**
/// `{"ok":false,"error":…}` 给对端；**不落笔**（`REQ-F-026` 判据②）。
#[cfg(unix)]
fn serve_stream(
    sink: &mut impl RequestSink,
    stream: std::os::unix::net::UnixStream,
    expect: &Listener,
    session: &mut Session,
) -> Result<Value, String> {
    let lim = session.limits();
    let mut out = stream;

    // ① 空闲超时（`REQ-F-026` ①）：读一行请求 / 写一行应答**各有上限**。
    //    用同一个数：它们是同一条连接的同一段等待宽限。
    if lim.idle_timeout_ms > 0 {
        let d = Duration::from_millis(lim.idle_timeout_ms);
        out.set_read_timeout(Some(d))
            .map_err(|e| format!("ext.world.Channel.ReadFail: 设读超时失败：{e}"))?;
        out.set_write_timeout(Some(d))
            .map_err(|e| format!("ext.world.Channel.WriteFail: 设写超时失败：{e}"))?;
    }

    // ② 读一行请求，**带单行上限**（`REQ-F-026` ④：超限即拒收，而不是无限缓冲）
    let read = {
        let mut r = BufReader::new(&out);
        read_line_bounded(&mut r, lim.max_line_bytes, lim.idle_timeout_ms)
    };
    let line = match read {
        Ok(s) => s,
        Err(e) => {
            let _ = writeln!(out, "{}", json!({"ok": false, "error": e}));
            return Err(e);
        }
    };

    if line.trim().is_empty() {
        return Err("ext.world.Channel.EmptyRequest: 空请求".to_string());
    }

    // ③ 限流（`REQ-F-026` ②）：**每身份**每秒多少条，跨连接累计。
    if let Err(e) = session.admit(&expect.actor, Instant::now()) {
        let _ = writeln!(out, "{}", json!({"ok": false, "error": e}));
        return Err(e);
    }

    let req = parse_request(line.trim())?;

    // ④ 身份已由**套接字文件的权限**保证：只有 expect.uid 连得上（见 bind()）。
    //    因此这里不需要（也无法用）peer_cred——它在本工具链上仍是不稳定 API。
    //    自称必须与内核身份一致（这一段与本改动无关，**不许放宽**）。
    if let Some(claimed) = &req.claimed_actor {
        if claimed != &expect.actor {
            let msg = format!(
                "请求自称 actor=`{claimed}`，而本套接字的内核身份是 `{}`——**身份不可自称**，拒绝",
                expect.actor
            );
            let _ = writeln!(out, "{}", json!({"ok": false, "error": msg}));
            return Err(format!("ext.world.Channel.Impersonation: {msg}"));
        }
    }

    // ⑤ 落笔：actor 取自映射，不取自请求。
    //
    //    `trace`（因果）**透传**：请求里给了就带上信封。跨进程的"请求—结果"配对
    //    靠它闭环——结果事件的 `trace` 指向意图事件的 `id`（`M10` 接线，2026-09-27）。
    //    它**不做引用完整性校验**（`REQ-F-031` 的 v1 口径）：指向不存在的 id 不拒绝。
    match sink.commit_requested(
        &req.kind,
        &expect.actor,
        req.body,
        req.trace.as_deref(),
        None,
    ) {
        Ok(ev) => {
            let _ = writeln!(out, "{}", json!({"ok": true, "event": ev}));
            Ok(ev)
        }
        Err(e) => {
            let _ = writeln!(out, "{}", json!({"ok": false, "error": e}));
            Err(e)
        }
    }
}

/// 读一行，**带单行上限**（`REQ-F-026` ④）。
///
/// 口径：**不含行尾换行**的字节数 ≤ `max`；超过即 `Channel.LineTooLong`，
/// 并在**读到超限的那一刻就停**——剩下的字节不再往内存里搬
/// （判据逐字：「超限即拒收，而不是无限缓冲」）。
///
/// 空闲超时（`WouldBlock`/`TimedOut`）在这里翻译成 `Channel.IdleTimeout`：
/// 这条连接一直没把一行说完，属于"空闲"，不属于"读坏了"。
#[cfg(unix)]
fn read_line_bounded<R: BufRead>(r: &mut R, max: usize, idle_ms: u64) -> Result<String, String> {
    let mut buf: Vec<u8> = Vec::new();
    loop {
        let avail = match r.fill_buf() {
            Ok(a) => a,
            Err(e) if e.kind() == ErrorKind::WouldBlock || e.kind() == ErrorKind::TimedOut => {
                return Err(format!(
                    "ext.world.Channel.IdleTimeout: 空闲超时 idle_timeout_ms={idle_ms}（读一行请求）"
                ));
            }
            Err(e) => return Err(format!("ext.world.Channel.ReadFail: {e}")),
        };
        if avail.is_empty() {
            break; // 对端关闭：把已读到的当成一行（与 read_line 同口径）
        }
        let (used, done) = match avail.iter().position(|b| *b == b'\n') {
            Some(i) => (i + 1, true),
            None => (avail.len(), false),
        };
        let content = if done { used - 1 } else { used };
        if content > max.saturating_sub(buf.len()) {
            return Err(format!(
                "ext.world.Channel.LineTooLong: 单行上限 max_line_bytes={max} 字节，\
                 本行不含换行已达 {} 字节",
                buf.len() + content
            ));
        }
        buf.extend_from_slice(&avail[..used]);
        r.consume(used);
        if done {
            break;
        }
    }
    String::from_utf8(buf).map_err(|e| format!("ext.world.Channel.ReadFail: 不是合法 UTF-8：{e}"))
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn parses_request_and_keeps_claimed_actor() {
        let r = parse_request(
            r#"{"kind":"act","body":{"capability":"notice.mute"},"actor":"world://agent/1"}"#,
        )
        .unwrap();
        assert_eq!(r.kind, "act");
        assert_eq!(r.claimed_actor.as_deref(), Some("world://agent/1"));
        assert!(parse_request("不是 JSON").is_err());
        assert!(parse_request(r#"{"body":{}}"#).is_err(), "缺 kind 应被拒");
    }

    #[test]
    fn empty_listeners_is_refused() {
        let d = std::env::temp_dir().join(format!("wc-ch-{}", std::process::id()));
        std::fs::create_dir_all(&d).unwrap();
        let p = d.join("ch.json");
        std::fs::write(&p, r#"{"channel":1,"listeners":[]}"#).unwrap();
        let e = ChannelConfig::load(&p).unwrap_err();
        assert!(e.contains("listeners 为空"), "实得: {e}");
        let _ = std::fs::remove_dir_all(&d);
    }
}
