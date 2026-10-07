//! 结构化审计留痕 —— **一条记录恒占一帧，字段名是固定集合**。
//!
//! ## 它回答的问题
//!
//! Agent 在无人看管时动手，事后有人要能**逐条复盘**。复盘靠的是留痕的**结构与顺序**，
//! 不是散文字符串：如果"意图"与"动作"混在同一段人话里，读的人就得靠猜；
//! 如果字段名随改动漂移，任何按字段取的检索都会在某一次改名之后**静默失效**。
//!
//! ⇒ 本模块把两件事写成结构：
//!
//! | 口径 | 落成什么 | 反着做会怎样 |
//! |---|---|---|
//! | **字段名是固定集合** | [`FIELDS`] 是唯一全集；[`off_contract_fields`] 报出越界的名字 | 改了名 ⇒ 按字段取的检索静默失效（**不会红**，所以要有个判据盯着） |
//! | **一条记录恒占一帧** | [`to_journal_frame`] 把值里的换行**就地替换** | 值里一个裸换行 ⇒ 按行分帧的读端把**一条**记录读成**两条** |
//!
//! ## 为什么"出口"是一个 trait 而不是一个函数
//!
//! 留痕的去处不止一个（journald 文本协议、文件回退、内存用于测试），
//! 而**一个出口坏了不该让另一个出口也收不到**——审计是事实的副本，
//! 副本之间不该互为单点。[`Multi`] 就是这条口径的落点：**每个出口都调用**，
//! 返回**第一个**失败（不吞错，也不因为一个坏就先中断）。
//!
//! ## 边界（如实声明）
//!
//! 本模块**只负责把记录写出去**：它**不裁决**任何事，也**不改世界**。
//! 它**不保证**投递成功（journald 不可达就是不可达）；它保证的是
//! **失败会以 `Err` 的形式被调用方看见**，而不是静默丢弃。

use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

/// `MESSAGE`：这条记录是**意图**还是**动作**（取值 `intent`／`action`）。
pub const F_MESSAGE: &str = "MESSAGE";
/// `INTENT`：意图的完整名，形如 `<能力>.<动词>`。
pub const F_INTENT: &str = "INTENT";
/// `CAPABILITY`：能力名。
pub const F_CAPABILITY: &str = "CAPABILITY";
/// `VERB`：动词。
pub const F_VERB: &str = "VERB";
/// `PARAMS`：参数（序列化成一个字符串，故**换行必须被替换**）。
pub const F_PARAMS: &str = "PARAMS";
/// `SNAPSHOT`：载体撤销点的位置（**不是世界回滚**）。
pub const F_SNAPSHOT: &str = "SNAPSHOT";
/// `GRANTED_BY`：这次动作以谁的名义放行。
pub const F_GRANTED_BY: &str = "GRANTED_BY";
/// `OUTCOME`：结果（`admitted`／`ok`／`failed`／`denied-by-user`／`snapshot-failed`…）。
pub const F_OUTCOME: &str = "OUTCOME";
/// `DURATION_MS`：动作耗时（毫秒）。
pub const F_DURATION_MS: &str = "DURATION_MS";
/// `JOB_ID`：长活儿标识。
pub const F_JOB_ID: &str = "JOB_ID";
/// `_TIMESTAMP`：时间戳（文件回退形态必带）。
pub const F_TIMESTAMP: &str = "_TIMESTAMP";

/// 约定字段名**全集**。任何一条记录的字段名都必须落在这里面。
pub const FIELDS: &[&str] = &[
    F_MESSAGE,
    F_INTENT,
    F_CAPABILITY,
    F_VERB,
    F_PARAMS,
    F_SNAPSHOT,
    F_GRANTED_BY,
    F_OUTCOME,
    F_DURATION_MS,
    F_JOB_ID,
    F_TIMESTAMP,
];

/// 一条记录：字段 → 值（**都用字符串**，与 journald 文本协议一致）。
///
/// 用 `BTreeMap`（键有序）而不是 `HashMap`：同一批字段两次写出的**帧逐字节相同**，
/// 于是"逐字节比对"这类判据才有意义。
pub type Fields = BTreeMap<String, String>;

/// 值里的换行／回车**就地替换成空格**。
///
/// 为什么是替换而不是转义：journald 的文本协议**按换行分帧**；把它转义成两个字符
/// （`\n`）会让读端拿到一个**被改过的值**，而读的人无从知道原文是什么。
/// 替换成空格是**有损但透明**的：帧数对得上，且"值里有换行"不会伪装成"有两条记录"。
fn sanitize(v: &str) -> String {
    v.replace(['\n', '\r'], " ")
}

/// 把任意 JSON 值序列化成 `PARAMS` 那一格用的字符串。
///
/// **一律走 `serde_json`**（包括字符串值）：这样 `PARAMS` 的**格式与值无关**——
/// 一个字符串参数与一个对象参数写出来都是合法 JSON。
/// ⚠ **不要**给字符串值开"原样返回"的短路：那会让
/// 「一个裸字符串里带换行」绕过 JSON 转义、直接落到 [`sanitize`] 上，
/// 于是同一格的内容随"传的是字符串还是对象"而变——那是**两个口径**，
/// 而本模块只要一个。
fn as_text(v: &Value) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "null".to_string())
}

/// **意图**记录：先留意图、再动手。
///
/// `granted_by` 的口径是"这次动作以谁的名义放行"（形如 `<会话名>@<auto|user-consent-pending>`），
/// **不是**"允不允许"——那是门禁的事（`crate::carrier` 的纪律：只执行、不裁决）。
pub fn intent_fields(capability: &str, verb: &str, params: &Value, granted_by: &str) -> Fields {
    let mut f = Fields::new();
    f.insert(F_MESSAGE.into(), "intent".into());
    f.insert(F_INTENT.into(), format!("{capability}.{verb}"));
    f.insert(F_CAPABILITY.into(), capability.into());
    f.insert(F_VERB.into(), verb.into());
    f.insert(F_PARAMS.into(), as_text(params));
    f.insert(F_GRANTED_BY.into(), granted_by.into());
    f.insert(F_OUTCOME.into(), "admitted".into());
    f
}

/// **动作**记录：做完之后留痕（耗时是必填）。
///
/// `undo` 是载体撤销点的位置。`None` ⇒ **不写这一格**，而不是写空串：
/// 「没有做过撤销点」与「撤销点在空字符串处」是两件事。
pub fn action_fields(
    capability: &str,
    verb: &str,
    outcome: &str,
    duration_ms: u64,
    undo: Option<&str>,
) -> Fields {
    let mut f = Fields::new();
    f.insert(F_MESSAGE.into(), "action".into());
    f.insert(F_CAPABILITY.into(), capability.into());
    f.insert(F_VERB.into(), verb.into());
    f.insert(F_OUTCOME.into(), outcome.into());
    f.insert(F_DURATION_MS.into(), duration_ms.to_string());
    if let Some(p) = undo {
        f.insert(F_SNAPSHOT.into(), p.into());
    }
    f
}

/// 报出记录里**不在** [`FIELDS`] 里的字段名（判据用：越界即红）。
///
/// 它是「字段名是固定集合」这条口径的**执行者**：没有它，改名不会有任何东西变红。
pub fn off_contract_fields(f: &Fields) -> Vec<String> {
    f.keys()
        .filter(|k| !FIELDS.contains(&k.as_str()))
        .cloned()
        .collect()
}

/// 一个留痕出口。
pub trait Sink {
    /// 记一条。失败**必须**返回 `Err`（不许静默丢弃）。
    fn record(&self, f: &Fields) -> Result<(), String>;
}

/// 把一条记录转成**行协议的一帧**：`K=V` 逐行，末尾**不带**换行。
///
/// ⇒ 「一帧里的行数 ≡ 字段数」这条判据，就是"值里的换行被替换掉了"的机械形态。
pub fn to_journal_frame(f: &Fields) -> String {
    let mut out = String::new();
    for (k, v) in f {
        if k.is_empty() || v.is_empty() {
            continue; // journald 口径：空值字段不写
        }
        out.push_str(k);
        out.push('=');
        out.push_str(&sanitize(v));
        out.push('\n');
    }
    while out.ends_with('\n') {
        out.pop();
    }
    out
}

/// **若干出口一起用**：每个出口都调用；返回**第一个**失败。
///
/// 为什么不是"一个坏了就停"：审计是事实的副本，副本之间不该互为单点——
/// journald 不可达不该让文件回退也收不到这条记录。
pub struct Multi(pub Vec<Box<dyn Sink + Send + Sync>>);

impl Multi {
    /// 空的多出口（什么都不做，但也不算失败）。
    pub fn new() -> Self {
        Multi(Vec::new())
    }

    /// 追加一个出口。
    pub fn push(&mut self, s: Box<dyn Sink + Send + Sync>) {
        self.0.push(s);
    }
}

impl Default for Multi {
    fn default() -> Self {
        Self::new()
    }
}

impl Sink for Multi {
    fn record(&self, f: &Fields) -> Result<(), String> {
        let mut first: Option<String> = None;
        for s in &self.0 {
            if let Err(e) = s.record(f) {
                if first.is_none() {
                    first = Some(e);
                }
            }
        }
        match first {
            Some(e) => Err(e),
            None => Ok(()),
        }
    }
}

/// 文件回退：**JSON Lines**（一行一条、逐行可解析），每条自动补时间戳。
pub struct FileSink {
    path: PathBuf,
}

impl FileSink {
    /// 指向一个文件。**不在这里建目录**：父目录不存在时 `record` 会如实报错。
    pub fn new(path: impl Into<PathBuf>) -> Self {
        FileSink { path: path.into() }
    }

    /// 这个出口写哪个文件。
    pub fn path(&self) -> &Path {
        &self.path
    }
}

/// 当前时间戳（UTC，`YYYY-MM-DDTHH:MM:SSZ`）。
///
/// 为什么要自己算：本工程的依赖纪律只允许 `serde_json` 一个 crate family
/// （`Cargo.toml` 逐字），`chrono` 不在其中。这里只用 `SystemTime` 的秒数
/// 做**民用历换算**，不引入任何依赖。它**不是**高精度时钟，够"每条记录能排序"用。
pub fn now_timestamp() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let days = secs.div_euclid(86_400);
    let rem = secs.rem_euclid(86_400);
    let (h, mi, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    // 民用历：把 1970-01-01 起的天数换成 Y-M-D。
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

impl Sink for FileSink {
    fn record(&self, f: &Fields) -> Result<(), String> {
        let mut f = f.clone();
        f.entry(F_TIMESTAMP.into()).or_insert_with(now_timestamp);
        let line = serde_json::to_string(&f)
            .map_err(|e| format!("ext.world.Agent.AuditEncode: 记录编不成 JSON：{e}"))?;
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|e| {
                format!(
                    "ext.world.Agent.AuditWriteFail: 打不开 {}：{e}",
                    self.path.display()
                )
            })?;
        file.write_all(line.as_bytes())
            .and_then(|_| file.write_all(b"\n"))
            .and_then(|_| file.flush())
            .map_err(|e| {
                format!(
                    "ext.world.Agent.AuditWriteFail: 写不进 {}：{e}",
                    self.path.display()
                )
            })
    }
}

/// 读回一份 JSON Lines 审计（测试与查询用）。
///
/// 读不到文件 ⇒ `Err`：**「读不到」与「读到了没问题」是两件事**，不许都返回空表。
/// 空行跳过；解析不了的行**点名第几行**报错，不静默跳过。
pub fn read_lines(path: &Path) -> Result<Vec<Fields>, String> {
    let raw = std::fs::read_to_string(path)
        .map_err(|e| format!("ext.world.Agent.AuditReadFail: {}：{e}", path.display()))?;
    let mut out = Vec::new();
    for (i, line) in raw.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let v: Fields = serde_json::from_str(line).map_err(|e| {
            format!(
                "ext.world.Agent.AuditCorrupt: {} 第 {} 行不是合法 JSON：{e}",
                path.display(),
                i + 1
            )
        })?;
        out.push(v);
    }
    Ok(out)
}

/// 只在内存里留痕（测试与"只要计数"的场合）。
#[derive(Default)]
pub struct Memory {
    rows: Mutex<Vec<Fields>>,
}

impl Memory {
    /// 空的内存出口。
    pub fn new() -> Self {
        Self::default()
    }

    /// 已记下的记录（按写入顺序）。
    pub fn records(&self) -> Vec<Fields> {
        self.rows.lock().map(|r| r.clone()).unwrap_or_default()
    }

    /// 已记下的记录转成的**帧**（用于"帧数 ≡ 写入次数"这类判据）。
    pub fn frames(&self) -> Vec<String> {
        self.records().iter().map(to_journal_frame).collect()
    }

    /// 记了几条。
    pub fn len(&self) -> usize {
        self.rows.lock().map(|r| r.len()).unwrap_or(0)
    }

    /// 一条都没有？
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl Sink for Memory {
    fn record(&self, f: &Fields) -> Result<(), String> {
        let mut r = self
            .rows
            .lock()
            .map_err(|_| "ext.world.Agent.AuditPoisoned: 内存出口被毒化".to_string())?;
        r.push(f.clone());
        Ok(())
    }
}

/// 一个**总是失败**的出口（判据用它证明"一路失败不阻塞另一路"）。
pub struct Failing {
    /// 失败理由（原样带回）。
    pub why: String,
}

impl Failing {
    /// 造一个必失败的出口。
    pub fn new(why: impl Into<String>) -> Self {
        Failing { why: why.into() }
    }
}

impl Sink for Failing {
    fn record(&self, _f: &Fields) -> Result<(), String> {
        Err(self.why.clone())
    }
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    #[test]
    fn a_value_with_a_newline_does_not_add_a_line_to_the_frame() {
        let f = intent_fields(
            "package.install",
            "install",
            &json!({ "note": "第一行\n第二行\r第三行" }),
            "agent@auto",
        );
        let frame = to_journal_frame(&f);
        assert_eq!(
            frame.split('\n').filter(|l| !l.is_empty()).count(),
            f.len(),
            "一帧的行数必须等于字段数：值里的换行必须被就地替换"
        );
        assert!(!frame.contains('\r'), "回车也必须被替换掉");
    }

    /// **直接打 `sanitize` 的那一枪**（变异：`sanitize` 恒返回原值 ⇒ 本用例必红）。
    ///
    /// 为什么要单来一条：`PARAMS` 现在**一律走 JSON 序列化**，换行会被转义成 `\n` 两个字符
    /// ⇒ 上一条用例**其实碰不到 `sanitize`**（本项目实测踩过：变异打上去它照样绿）。
    /// 这一条**手工**把一个含裸换行的值放进记录，才真正证明替换在起作用。
    #[test]
    fn a_raw_newline_in_any_value_is_replaced() {
        let mut f = Fields::new();
        f.insert("K".into(), "a\nb\rc".into());
        let frame = to_journal_frame(&f);
        assert_eq!(
            frame, "K=a b c",
            "裸换行与裸回车必须被就地替换成空格；实得={frame:?}"
        );
        assert_eq!(
            frame.split('\n').filter(|l| !l.is_empty()).count(),
            f.len(),
            "替换之后帧的行数仍等于字段数"
        );
    }

    #[test]
    fn action_without_undo_does_not_carry_the_snapshot_field() {
        let f = action_fields("a.b", "do", "ok", 3, None);
        assert!(
            !f.contains_key(F_SNAPSHOT),
            "没做过撤销点就不写这一格（不写空串）"
        );
        let g = action_fields("a.b", "do", "ok", 3, Some("/run/undo/x"));
        assert_eq!(g.get(F_SNAPSHOT).map(String::as_str), Some("/run/undo/x"));
    }

    #[test]
    fn field_names_off_the_contract_are_reported() {
        let mut f = action_fields("a.b", "do", "ok", 1, None);
        assert!(off_contract_fields(&f).is_empty());
        f.insert("DURATION".into(), "1".into()); // 把 DURATION_MS 写错的形态
        assert_eq!(off_contract_fields(&f), vec!["DURATION".to_string()]);
    }

    #[test]
    fn the_timestamp_is_a_stable_civil_format() {
        let t = now_timestamp();
        assert_eq!(t.len(), 20, "形如 1970-01-01T00:00:00Z：{t}");
        assert!(t.ends_with('Z'));
        assert_eq!(t.as_bytes()[4], b'-');
    }
}
