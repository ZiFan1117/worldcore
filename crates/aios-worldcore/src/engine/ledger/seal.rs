//! 链节 —— 一笔的**封条**：正文的指纹 ＋ 上一节的封条。
//!
//! ★ 学 「crates/aios-evidence」 的两条干活口径（**只学活** —— 它的类型名一个不抄、一个不出现）：
//!   ① 封条压的是**整笔**（它压的也是整条收据，不只压 payload）—— 任何一格被改都会变；
//!   ② 第一笔是**创世**（没有前驱），此后每一节都把上一节的封条接进来。
//!
//! ★ 我们的名字／我们的形状：Seal／fingerprint／check_chain —— 它的类型名一个不出现。
//! ★ 如实说：封条用 **BLAKE3-256**（64 位小写十六进制）—— 与它压链用的同一个算法，
//!   且是**本 workspace 早就有的**第三方依赖（零新增依赖）⇒「改一处就断链」成立，
//!   抗碰撞也成立。★ 它那层 **Ed25519 签名我们没接**：签名要一套密钥主体，
//!   我们的账今天只登记「谁」（Who），没有密钥可签 —— 那一段就是没接上。

use std::fmt::Write as _;

use crate::core::types::{Admit, Event, Reason, Refuse};

/// 创世那一笔的「前驱」占位（★ 拿它占住位子 —— 不然首节会和「前驱为空串」撞脸）。
const GENESIS: &str = "<创世>";

/// 一笔的封条。
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Seal {
    /// 这一笔正文的指纹。
    pub(super) content: String,
    /// 上一节的封条；创世是 None。
    pub(super) prev: Option<String>,
}

impl Seal {
    /// 接住上一节，造这一节的封条。
    pub(super) fn next(prev: Option<&str>, content: String) -> Self {
        Self {
            content,
            prev: prev.map(str::to_owned),
        }
    }

    /// 这一节的封条值：**前驱 ＋ 指纹一起压**（接错哪一节，封条就跟着变）。
    pub(super) fn hash(&self) -> String {
        let mut buf = String::new();
        push_field(&mut buf, self.prev.as_deref().unwrap_or(GENESIS));
        push_field(&mut buf, &self.content);
        digest(&buf)
    }
}

/// 一笔正文的指纹：把**整笔**（序号／谁／族／做了什么／参数）按固定次序、**带长度**地压平，
/// 再压成 BLAKE3-256（64 位小写十六进制）。
///
/// ★ 为什么带长度：字段里塞一个分隔符，伪造不出同一串 ⇒ 两笔不同的正文不会压出同一个指纹。
/// ★ 为什么参数要排键：同一堆参数换个书写次序，必须压出同一个指纹（不认插入序）。
pub(super) fn fingerprint(row: &Event) -> String {
    let mut buf = String::new();
    push_field(&mut buf, &row.seq.0.to_string());
    push_field(&mut buf, row.who.name());
    push_field(&mut buf, &row.family);
    push_field(&mut buf, &row.what);
    push_field(&mut buf, &params_canonical(&row.params));
    digest(&buf)
}

/// 参数按**键名升序**压平。
fn params_canonical(params: &serde_json::Map<String, serde_json::Value>) -> String {
    let mut keys: Vec<&String> = params.keys().collect();
    keys.sort_unstable();
    let mut buf = String::new();
    for k in keys {
        push_field(&mut buf, k);
        if let Some(v) = params.get(k) {
            push_field(&mut buf, &render(v));
        }
    }
    buf
}

/// 一格参数值的规范写法（Value 总写得出来；真写不出来也给个占位，**不许 panic**）。
fn render(v: &serde_json::Value) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "<不可序列化>".to_string())
}

/// 把一段话**带长度**地压进缓冲：长度:内容|。
fn push_field(out: &mut String, s: &str) {
    // 写进 String 不会失败（fmt::Error 只可能来自自定义 Formatter）。
    let _ = write!(out, "{}:{}|", s.len(), s);
}

/// 压指纹：**BLAKE3-256** ⇒ 64 位小写十六进制。
///
/// ★ 用的是本 workspace（根 Cargo.toml）里早就有的第三方依赖 blake3 —— **零新增依赖**。
fn digest(s: &str) -> String {
    blake3::hash(s.as_bytes()).to_hex().to_string()
}

/// **查篡改**：正文与链节等长 ⇒ 逐笔重算指纹 ⇒ 逐节核对前驱。
///
/// ★ 学它 verify_integrity 的报法：**第一处**对不上就返回，并把**位次**写进 field。
/// ★ 空账不叫「健康」：没有链节可查，单独报（学它把空链与「一条的健康链」分开）。
pub(super) fn check_chain(rows: &[Event], seals: &[Seal]) -> Admit<()> {
    if seals.is_empty() {
        return Err(Refuse::new(
            Reason::MissingField {
                field: "seal".to_string(),
            },
            "<空账：一条链节都没有，无从查>",
        ));
    }
    if rows.len() != seals.len() {
        return Err(Refuse::new(
            Reason::BadValue {
                field: "seal".to_string(),
                rule: rows.len().to_string(),
            },
            seals.len().to_string(),
        ));
    }
    let mut prev: Option<String> = None;
    for (i, (row, seal)) in rows.iter().zip(seals.iter()).enumerate() {
        // ① 这一笔的正文动过没有。
        let got = fingerprint(row);
        if got != seal.content {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: format!("seal[{i}]"),
                    rule: seal.content.clone(),
                },
                got,
            ));
        }
        // ② 这一节接的前驱对不对（创世那一笔必须是「没有前驱」）。
        if seal.prev.as_deref() != prev.as_deref() {
            let want = prev.as_deref().unwrap_or(GENESIS).to_string();
            let real = seal.prev.as_deref().unwrap_or(GENESIS).to_string();
            return Err(Refuse::new(
                Reason::BadValue {
                    field: format!("seal[{i}].prev"),
                    rule: want,
                },
                real,
            ));
        }
        prev = Some(seal.hash());
    }
    Ok(())
}
