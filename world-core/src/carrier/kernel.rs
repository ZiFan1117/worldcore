//! 内核客户端 —— 载体适配器**唯一的写世界通道**。
//!
//! ## 为什么必须走这一条
//!
//! 载体适配器跑在被管者身份下，**对账本零写权限**。它要让世界知道"我要做什么"、
//! "我做完了"，只能做一件事：**向内核提交请求**。请求走的是与其它任何主体完全相同的路
//! （本体校验 → 门禁裁决 → 落笔），**没有任何特权**。
//!
//! ## 协议（纯文本、一行一帧）
//!
//! ```text
//! 请求: {"kind":"act","body":{…}}          ← **不含 actor**；含则必须与内核身份一致
//! 应答: {"ok":true,"event":{…}}            / {"ok":false,"error":"ext.world.…"}
//! ```
//!
//! **身份由内核按套接字给出**（一个套接字一个身份，权限即身份），
//! 请求体里没有任何地方可以自称——这是"身份不可自称"在客户端一侧的落点。
//!
//! ## 一次完整的往返（本模块只负责其中两次提交）
//!
//! ```text
//! ① submit(意图) ──► 内核：裁决 → 通过则落笔，应答里带回**意图事件**
//! ② （调用方执行；本模块不碰载体）
//! ③ submit(结果, trace=①的事件 id) ──► 内核：落笔，因果链就此闭合
//! ```

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

/// 内核客户端。
pub struct KernelClient {
    socket: PathBuf,
}

/// 内核的应答。
#[derive(Debug, Clone, PartialEq)]
pub struct Reply {
    /// 通过与否。
    pub ok: bool,
    /// 通过时的事件（含 `id`——它就是结果的因果锚点）。
    pub event: Option<Value>,
    /// 不通过时的错误码正文。
    pub error: Option<String>,
}

impl Reply {
    /// 从一行应答文本解析。
    pub fn parse(line: &str) -> Result<Self, String> {
        let v: Value = serde_json::from_str(line)
            .map_err(|e| format!("ext.world.Carrier.BadReply: 内核应答不是合法 JSON：{e}"))?;
        let ok = v
            .get("ok")
            .and_then(Value::as_bool)
            .ok_or_else(|| "ext.world.Carrier.BadReply: 内核应答缺 ok 字段".to_string())?;
        Ok(Reply {
            ok,
            event: v.get("event").cloned(),
            error: v.get("error").and_then(Value::as_str).map(str::to_string),
        })
    }

    /// 应答里那条事件的 id（结果的因果锚点）。
    pub fn event_id(&self) -> Option<&str> {
        self.event
            .as_ref()
            .and_then(|e| e.get("id"))
            .and_then(Value::as_str)
    }

    /// 出错时**必须带可判定的错误码**，否则说明内核违约。
    pub fn error_code(&self) -> Option<&str> {
        self.error
            .as_deref()
            .and_then(crate::common::error::code_of)
    }
}

impl KernelClient {
    /// 指向某个套接字。
    pub fn new(socket: &Path) -> Self {
        KernelClient {
            socket: socket.to_path_buf(),
        }
    }

    /// 套接字路径。
    pub fn socket(&self) -> &Path {
        &self.socket
    }

    /// 提交一条事件，读回一行应答（**一次一连接**，与内核的 v1 通道口径一致）。
    ///
    /// 失败一律**拒绝**：连不上就是连不上，**不做本地降级**——
    /// 手没有法就不许动。
    #[cfg(unix)]
    pub fn submit(
        &self,
        kind: &str,
        body: Value,
        claimed_actor: Option<&str>,
    ) -> Result<Reply, String> {
        self.submit_full(kind, body, claimed_actor, None)
    }

    /// 提交一条**带因果**的事件（结果事件用这个，`trace` 指向意图事件的 id）。
    ///
    /// 为什么要单独一个入口：`trace` 是**信封字段**（与世界层同级），不是信纸字段。
    /// 把它放进 `body` 会污染信纸契约；放在信封上，它与 `seq`/`id`/`actor` 同级，
    /// 才是"因果"该有的位置。
    #[cfg(unix)]
    pub fn submit_with_trace(
        &self,
        kind: &str,
        body: Value,
        trace: Option<&str>,
    ) -> Result<Reply, String> {
        self.submit_full(kind, body, None, trace)
    }

    #[cfg(unix)]
    fn submit_full(
        &self,
        kind: &str,
        body: Value,
        claimed_actor: Option<&str>,
        trace: Option<&str>,
    ) -> Result<Reply, String> {
        let mut req = json!({ "kind": kind, "body": body });
        if let Some(o) = req.as_object_mut() {
            if let Some(a) = claimed_actor {
                o.insert("actor".to_string(), json!(a));
            }
            if let Some(t) = trace {
                if !t.is_empty() {
                    o.insert("trace".to_string(), json!(t));
                }
            }
        }
        let line = serde_json::to_string(&req)
            .map_err(|e| format!("ext.world.Carrier.EncodeFail: {e}"))?;

        let stream = std::os::unix::net::UnixStream::connect(&self.socket).map_err(|e| {
            format!(
                "ext.world.Carrier.KernelUnreachable: 连不上内核 {}：{e}（**拒绝执行**：手没有法不许动）",
                self.socket.display()
            )
        })?;
        let mut w = stream
            .try_clone()
            .map_err(|e| format!("ext.world.Carrier.KernelFail: {e}"))?;
        w.write_all(line.as_bytes())
            .and_then(|_| w.write_all(b"\n"))
            .and_then(|_| w.flush())
            .map_err(|e| format!("ext.world.Carrier.KernelFail: 写不进内核：{e}"))?;

        let mut reader = BufReader::new(stream);
        let mut buf = String::new();
        reader
            .read_line(&mut buf)
            .map_err(|e| format!("ext.world.Carrier.KernelFail: 读不到内核应答：{e}"))?;
        if buf.trim().is_empty() {
            return Err("ext.world.Carrier.KernelFail: 内核没给应答（连接被关）".to_string());
        }
        Reply::parse(buf.trim())
    }

    /// 非 Unix 平台：通道只在 Unix 上可用（v1 局限），**不假装可用**。
    #[cfg(not(unix))]
    pub fn submit(
        &self,
        _kind: &str,
        _body: Value,
        _claimed: Option<&str>,
    ) -> Result<Reply, String> {
        Err("ext.world.Carrier.KernelUnreachable: 通道只在 Unix 上可用（v1 局限）".to_string())
    }

    /// 非 Unix 平台：同上。
    #[cfg(not(unix))]
    pub fn submit_with_trace(
        &self,
        _kind: &str,
        _body: Value,
        _trace: Option<&str>,
    ) -> Result<Reply, String> {
        Err("ext.world.Carrier.KernelUnreachable: 通道只在 Unix 上可用（v1 局限）".to_string())
    }
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn parses_a_successful_reply() {
        let r = Reply::parse(r#"{"ok":true,"event":{"id":"e-1","seq":3}}"#).unwrap();
        assert!(r.ok);
        assert_eq!(r.event_id(), Some("e-1"));
        assert!(r.error.is_none());
    }

    #[test]
    fn parses_a_refusal_with_a_machine_readable_code() {
        let r =
            Reply::parse(r#"{"ok":false,"error":"ext.world.Gate.Rejected: 门禁拒绝：能力未声明"}"#)
                .unwrap();
        assert!(!r.ok);
        assert_eq!(r.error_code(), Some("ext.world.Gate.Rejected"));
    }

    #[test]
    fn rejects_a_malformed_reply() {
        assert!(Reply::parse("not json").is_err());
        assert!(Reply::parse(r#"{"event":{}}"#).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn refuses_loudly_when_the_kernel_is_not_there() {
        let c = KernelClient::new(Path::new("/definitely/not/here.sock"));
        let e = c.submit("act", serde_json::json!({}), None).unwrap_err();
        assert!(e.contains("KernelUnreachable"), "{e}");
        assert!(e.contains("拒绝执行"), "{e}");
    }
}
