//! 语义事件的构造。
//!
//! 唯一原语是**语义事件**（`07/2-依据/14-总线词表v0.md`），三个家族：
//! - `change` **变更**：主体 + 字段路径 + 旧值 + 新值
//! - `act`    **动作**：能力 + 动词 + 请求号（结果本身也是一条事件）
//! - `notice` **通告**：类型 + 主体（完工铃等）
//!
//! 信封字段里的 `seq` **由账本分配**，所以 [`new_event`] 要求调用者先取号
//! （见 [`crate::World::commit`]）——这是"法律要求信封含 seq"与"账本分配 seq"的接缝。

use serde_json::{json, Map, Value};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// 出厂词表版本。**只加 flags，永不改这个数的含义**。
pub const WORLD_VERSION: u64 = 1;

/// 已定义的能力旗标。未知旗标**必须忽略**（本体纪律）。
///
/// ⚠️ 这个常量同时是**新事件的 `flags` 初值**（见 [`new_event`]）：往这里加一项，
/// **每一条事件**都会带上它。故它只装"出厂即带"的旗标（今天为空）。
/// 由某次裁决**临时**加上去的旗标（例如闸的摩擦标记）另用 [`with_flag`]，
/// 名字常量另立（[`FLAG_FRICTION`]）。
pub const FLAGS: [&str; 0] = [];

/// **摩擦旗标**（闸加在不可逆动作上的可核流水）。
///
/// 依据：书第五章 §5.5 逐字「摩擦本该挂在动作的不可逆等级上：可逆处放手，不可逆处加摩擦」。
/// 加摩擦这件事必须**在账本上留下可核的痕迹**，否则"加过摩擦"只是一句注释。
/// 形式：`gate.friction:<等级>`（等级取自载体执行清单的 `risk`；无清单 ⇒ `gate.friction:unlisted`）。
///
/// 为什么落在信封的 `flags` 上：信封的 `flags` 就是"随事件走的旗标"，
/// 且本体纪律要求**未知旗标必须忽略** ⇒ 旧读法读到它不会坏，新读法能从它核出摩擦发生过。
pub const FLAG_FRICTION: &str = "gate.friction";

/// 给一条已造好的事件补一个**能力旗标**（去重；`flags` 不是数组时**原样放过**，不静默修补）。
pub fn with_flag(ev: &mut Value, flag: &str) {
    let Some(obj) = ev.as_object_mut() else {
        return;
    };
    let entry = obj
        .entry("flags".to_string())
        .or_insert_with(|| Value::Array(Vec::new()));
    let Some(arr) = entry.as_array_mut() else {
        return;
    };
    if !arr.iter().any(|v| v.as_str() == Some(flag)) {
        arr.push(Value::String(flag.to_string()));
    }
}

/// 一个**读者**从一条事件的 `flags` 里读出来的东西（`REQ-F-029`）。
///
/// 依据（逐字）：`src/ontology_definition/ontology.json:20` ——
/// `"flags": "array  # 能力旗标；未知旗标必须忽略"`。
/// 分界线（`WC-FMT-001` §「未知家族 / 未知字段 / 未知旗标」逐字）：
/// 「**不认识的语义拒绝，不认识的附加信息忽略**」。
///
/// 三个格子各自可判：
/// - [`Flags::known`]：**这个读者认得**的旗标 ⇒ 他按这部分继续处理；
/// - [`Flags::ignored`]：**这个读者不认得**的 ⇒ **一律忽略**，不得因此拒收整条事件；
/// - [`Flags::not_string`]：不是字符串的项（如 `123`）⇒ **如实计数**，既不静默修补、也不据此拒收
///   （形状归本体校验；`WC-ONT-001` §八 逐字登记"不校验 `flags` 是不是数组、不校验取值"）。
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Flags<'a> {
    /// 认得的旗标（按它们在事件里的原顺序）。
    pub known: Vec<&'a str>,
    /// 不认得的旗标（同样按原顺序）——**必须忽略**，不得据此拒收。
    pub ignored: Vec<&'a str>,
    /// 不是字符串的项数（不静默修补，也不据此拒收）。
    pub not_string: usize,
}

/// 「出厂读法」认得哪些旗标：只有 [`FLAGS`]（今天为空）。
///
/// ⚠️ 这**不等于**"世界里只会有这些旗标"：`gate.friction:*` 由**内核自己**写
/// （见 [`FLAG_FRICTION`]），而出厂读法**不认得**它——正因为"未知旗标必须忽略"，
/// 带摩擦旗标的事件才照样读得下去（本文件 [`FLAG_FRICTION`] 的文档里那句
/// 「旧读法读到它不会坏」在这里成为**可执行的**事实，而不只是一句注释）。
pub fn is_factory_flag(flag: &str) -> bool {
    FLAGS.contains(&flag)
}

/// **读出**一条事件的旗标：认得的进 [`Flags::known`]，不认得的一律进 [`Flags::ignored`]。
///
/// 这是"未知旗标一律忽略并按已知部分继续"的实现点：读的人拿 `known` 继续办事，
/// `ignored` 只作登记。**没有 `Result`**——"出现了不认得的旗标"不是一种错误。
///
/// 口径（三条，都可判真假）：
/// - 没有 `flags` 键、或 `flags` 不是数组 ⇒ 返回**空视图**（形状不归这里判：
///   信封必填与家族信纸归 [`crate::ontology_definition::Ontology::validate`]）；
/// - **原顺序**保留（旗标是有序数组，重排会让"同一条事件"读出两种样子）；
/// - **不解释旗标的取值**（`gate.friction:` 后面跟什么等级，是写它的人的事）。
pub fn read_flags<F>(ev: &Value, knows: F) -> Flags<'_>
where
    F: Fn(&str) -> bool,
{
    let mut out = Flags::default();
    let Some(arr) = ev.get("flags").and_then(Value::as_array) else {
        return out;
    };
    for item in arr {
        match item.as_str() {
            Some(f) if knows(f) => out.known.push(f),
            Some(f) => out.ignored.push(f),
            None => out.not_string += 1,
        }
    }
    out
}

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// 造一条事件（**不含 seq 的现实值以外的一切都已就位**）。
///
/// `seq` 由调用者从 [`crate::ledger::Ledger::next_seq`] 取。
pub fn new_event(seq: u64, kind: &str, actor: &str, body: Value) -> Value {
    let mut m = Map::new();
    m.insert("world".to_string(), json!(WORLD_VERSION));
    m.insert("kind".to_string(), json!(kind));
    m.insert("id".to_string(), json!(new_id()));
    m.insert("seq".to_string(), json!(seq));
    m.insert("at".to_string(), json!(unix_secs()));
    m.insert("actor".to_string(), json!(actor));
    m.insert("flags".to_string(), json!(FLAGS.to_vec()));
    m.insert("body".to_string(), body);
    Value::Object(m)
}

/// 给一条已造好的事件补上**可选**信封字段（`trace` 因果 / `to` 目的地）。
///
/// 为什么需要它（`M10` 接线，2026-09-27）：`trace` 是本体里**早就定义**的可选字段
/// （`ontology.json` 的 `envelope.optional`），但此前**没有任何写入路径会填它**——
/// 于是"为什么会变成这样"这条追问在 v1 里没有落点（`WC-FMT-001` 记为待办）。
/// 现在由"请求—结果"配对填它：**结果事件的 `trace` = 引发它的那条意图事件的 `id`**。
///
/// 口径（刻意）：
/// - `None` 即**不写该键**，不写 `null`——"没有因果"与"因果指向空"是两件事；
/// - 空串视为未给（否则会写出一个指不到任何事件的 `trace`）；
/// - 非对象的事件**原样放过**（形态问题由本体校验负责报，不在这里静默修补）。
pub fn with_trace(ev: &mut Value, trace: Option<&str>) {
    if let (Some(t), Some(obj)) = (trace, ev.as_object_mut()) {
        if !t.is_empty() {
            obj.insert("trace".to_string(), json!(t));
        }
    }
}

/// 给一条已造好的事件补上 `to`（目的地；空 = 广播）。
///
/// 与 [`with_trace`] 同口径：`None`/空串 ⇒ 不写该键。
pub fn with_to(ev: &mut Value, to: Option<&str>) {
    if let (Some(t), Some(obj)) = (to, ev.as_object_mut()) {
        if !t.is_empty() {
            obj.insert("to".to_string(), json!(t));
        }
    }
}

/// 事件身份。不引入 uuid crate：**纳秒 + 进程内计数器**已足够唯一。
pub fn new_id() -> String {
    let c = COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("e{}-{}", unix_nanos(), c)
}

/// `change` 的信纸：**`before` 必带**——回滚所需的信息当场留下
/// （RFC 6902 的 patch 没有逆操作，不记旧值就回不去）。
pub fn change_body(subject: &str, path: &str, before: Value, after: Value) -> Value {
    json!({ "subject": subject, "path": path, "before": before, "after": after })
}

/// `act` 的信纸。
pub fn act_body(capability: &str, verb: &str, request_id: &str, params: Value) -> Value {
    json!({
        "capability": capability,
        "verb": verb,
        "request_id": request_id,
        "params": params
    })
}

/// `notice` 的信纸。
pub fn notice_body(kind: &str, subject: &str, payload: Value) -> Value {
    json!({ "type": kind, "subject": subject, "payload": payload })
}

fn unix_nanos() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0)
}

fn unix_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}
