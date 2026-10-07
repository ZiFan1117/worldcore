//! **行分隔的结构化请求／应答** —— 一行一问一答；坏字节不许吞下一条。
//!
//! ## 它回答的问题
//!
//! 调用方要的是一个**能按码分支**的结果，而不是一段要人去读的人话。
//! 若应答是散文，任何自动化的分支都会退化成字符串匹配；若一行坏字节能让整条连接断掉，
//! 一个打字错误就会**吞掉它后面那条合法请求**——而调用方只会看到"超时"，
//! **看不出真正的原因**。
//!
//! ⇒ 本模块把两件事写成结构：
//!
//! | 口径 | 落成什么 | 反着做会怎样 |
//! |---|---|---|
//! | **一问一答、顺序一致** | [`serve`] 逐行读、逐行写 | 攒一批再回 ⇒ 调用方无法把应答与请求对上 |
//! | **坏字节不吞下一条** | [`handle_line`] 回一条协议错应答后**继续读** | 一行坏字节 ⇒ 后面那条合法请求**没有应答**，调用方只看到超时 |
//!
//! ## 为什么应答的字段是这四个
//!
//! `ok` 回答"成了没有"，`err_code` 回答"**为什么**没成"（机器可读），
//! `err_msg` 给人看，`data` 带成功的载荷。
//! **`ok==true` 时不准带 `err_code`**：同时说"成功"和"错误码是 X"是一种自相矛盾，
//! 而下游一定会有人只看其中一个 ⇒ 两种读法给出两个结论。
//!
//! ## 边界（如实声明）
//!
//! 本模块**只做分帧与结构化**：它**不裁决**任何事，也**不碰载体**。
//! 一行多大算超限由**调用方**的读端决定（`BufRead` 的语义），本模块不设上限。

use serde_json::{json, Value};

/// 协议类错误码（请求无法解析时用它）。
pub const E_PROTOCOL: &str = "ext.world.Agent.Protocol";

/// 一次调用的请求（一行 JSON）。
#[derive(Debug, Clone, PartialEq)]
pub struct Request {
    /// 能力名。
    pub capability: String,
    /// 动词。
    pub verb: String,
    /// 参数（缺省为空对象）。
    pub args: Value,
}

impl Request {
    /// 造一个请求。
    pub fn new(capability: impl Into<String>, verb: impl Into<String>, args: Value) -> Self {
        Request {
            capability: capability.into(),
            verb: verb.into(),
            args,
        }
    }

    /// 转成一行 JSON（**不含**换行）。
    pub fn to_line(&self) -> String {
        serde_json::to_string(&json!({
            "capability": self.capability,
            "verb": self.verb,
            "args": self.args,
        }))
        .unwrap_or_else(|_| "{}".to_string())
    }

    /// 从一行解析。对不上形态 ⇒ `Err`（**不猜**）。
    pub fn from_line(s: &str) -> Result<Self, String> {
        let v: Value =
            serde_json::from_str(s).map_err(|e| format!("{E_PROTOCOL}: 请求不是合法 JSON：{e}"))?;
        let capability = v
            .get("capability")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("{E_PROTOCOL}: 请求缺 capability"))?
            .to_string();
        let verb = v
            .get("verb")
            .and_then(Value::as_str)
            .ok_or_else(|| format!("{E_PROTOCOL}: 请求缺 verb"))?
            .to_string();
        let args = v.get("args").cloned().unwrap_or_else(|| json!({}));
        Ok(Request {
            capability,
            verb,
            args,
        })
    }
}

/// 结构化应答（一行 JSON）：`ok=false` 时 `err_code` 必须非空。
#[derive(Debug, Clone, PartialEq)]
pub struct Response {
    /// 成了没有。
    pub ok: bool,
    /// 成功的载荷。
    pub data: Option<Value>,
    /// 机器可读的错误码（`ok=false` 时必须非空）。
    pub err_code: Option<String>,
    /// 给人看的错误说明。
    pub err_msg: Option<String>,
}

impl Response {
    /// 成功。
    pub fn ok(data: Value) -> Self {
        Response {
            ok: true,
            data: Some(data),
            err_code: None,
            err_msg: None,
        }
    }

    /// 拒绝：**必须**给码（没有码的拒绝等于让人从散文里猜）。
    pub fn refused(code: &str, msg: &str) -> Self {
        Response {
            ok: false,
            data: None,
            err_code: Some(code.to_string()),
            err_msg: Some(msg.to_string()),
        }
    }

    /// 转成一行 JSON（**不含**换行）。
    ///
    /// `ok==true` 时**不写** `err_code`／`err_msg`（见模块头注：同时说成功与错误是自相矛盾）。
    pub fn to_line(&self) -> String {
        let mut o = serde_json::Map::new();
        o.insert("ok".into(), Value::Bool(self.ok));
        if let Some(d) = &self.data {
            o.insert("data".into(), d.clone());
        }
        if !self.ok {
            if let Some(c) = &self.err_code {
                o.insert("err_code".into(), Value::String(c.clone()));
            }
            if let Some(m) = &self.err_msg {
                o.insert("err_msg".into(), Value::String(m.clone()));
            }
        }
        serde_json::to_string(&Value::Object(o)).unwrap_or_else(|_| "{\"ok\":false}".to_string())
    }

    /// 从一行解析。形态不合法 ⇒ `Err`。
    pub fn from_line(s: &str) -> Result<Self, String> {
        let v: Value =
            serde_json::from_str(s).map_err(|e| format!("{E_PROTOCOL}: 应答不是合法 JSON：{e}"))?;
        let ok = v
            .get("ok")
            .and_then(Value::as_bool)
            .ok_or_else(|| format!("{E_PROTOCOL}: 应答缺 ok"))?;
        Ok(Response {
            ok,
            data: v.get("data").cloned(),
            err_code: v
                .get("err_code")
                .and_then(Value::as_str)
                .map(str::to_string),
            err_msg: v.get("err_msg").and_then(Value::as_str).map(str::to_string),
        })
    }
}

/// 一条协议错应答。
pub fn protocol_error(msg: &str) -> Response {
    Response::refused(E_PROTOCOL, msg)
}

/// 处理一行。
///
/// 返回 `(应答, 该行是否是可解析的请求)`：
/// `false` 表示这行是**协议错**——调用方**必须继续读下一行**，不许因此收摊。
pub fn handle_line(line: &str, handler: &dyn Fn(&Request) -> Response) -> (Response, bool) {
    match Request::from_line(line) {
        Ok(req) => (handler(&req), true),
        Err(why) => (protocol_error(&why), false),
    }
}

/// 常驻：逐行读、逐行回，**顺序严格一一对应**。
///
/// - **空行跳过**（行协议里空行是填充，不是请求）⇒ 不为它产生应答；
/// - 解析不了的行 ⇒ 写一条协议错应答，**然后继续读**（这是"坏字节不吞下一条"的落点）；
/// - 读到 EOF ⇒ `Ok(())`。
pub fn serve<R: std::io::BufRead, W: std::io::Write>(
    mut reader: R,
    mut writer: W,
    handler: &dyn Fn(&Request) -> Response,
) -> Result<(), String> {
    let mut line = String::new();
    loop {
        line.clear();
        let n = reader
            .read_line(&mut line)
            .map_err(|e| format!("ext.world.Agent.ReadFail: 读一行失败：{e}"))?;
        if n == 0 {
            return Ok(()); // EOF
        }
        let trimmed = line.trim_end_matches(['\n', '\r']);
        if trimmed.trim().is_empty() {
            continue; // 填充行：不产生应答
        }
        let (res, _parsed) = handle_line(trimmed, handler);
        writer
            .write_all(res.to_line().as_bytes())
            .and_then(|_| writer.write_all(b"\n"))
            .and_then(|_| writer.flush())
            .map_err(|e| format!("ext.world.Agent.WriteFail: 写一帧失败：{e}"))?;
    }
}

/// 客户端助手：发一条、收一条。
pub fn call<W: std::io::Write, R: std::io::BufRead>(
    writer: &mut W,
    reader: &mut R,
    req: &Request,
) -> Result<Response, String> {
    writer
        .write_all(req.to_line().as_bytes())
        .and_then(|_| writer.write_all(b"\n"))
        .and_then(|_| writer.flush())
        .map_err(|e| format!("ext.world.Agent.WriteFail: 发不出去：{e}"))?;
    let mut line = String::new();
    let n = reader
        .read_line(&mut line)
        .map_err(|e| format!("ext.world.Agent.ReadFail: 收不回来：{e}"))?;
    if n == 0 {
        return Err("ext.world.Agent.Eof: 连接在对端给出应答之前就结束了".to_string());
    }
    Response::from_line(line.trim_end_matches(['\n', '\r']))
}

#[cfg(test)]
mod unit {
    use super::*;

    /// 一个只认 `a.b`／`do` 的处理器。
    fn handler(req: &Request) -> Response {
        if req.capability == "a.b" && req.verb == "do" {
            Response::ok(json!({ "echo": req.args }))
        } else {
            Response::refused("ext.world.Agent.Denied.UnknownCapability", "不认这项能力")
        }
    }

    #[test]
    fn a_request_round_trips_through_one_line() {
        let r = Request::new("a.b", "do", json!({ "x": 1 }));
        let line = r.to_line();
        assert!(!line.contains('\n'), "一行就是一帧，不许内含换行");
        assert_eq!(Request::from_line(&line).unwrap(), r);
    }

    #[test]
    fn an_ok_response_never_carries_an_error_code() {
        let ok = Response::ok(json!({ "n": 1 }));
        let line = ok.to_line();
        assert!(!line.contains("err_code"), "成功不许同时带错误码：{line}");
        let back = Response::from_line(&line).unwrap();
        assert!(back.ok);
        assert_eq!(back.err_code, None);

        let no = Response::refused("X", "因为");
        let l2 = no.to_line();
        assert!(l2.contains("err_code"), "拒绝必须带码：{l2}");
        assert_eq!(
            Response::from_line(&l2).unwrap().err_code.as_deref(),
            Some("X")
        );
    }

    #[test]
    fn serve_skips_blank_lines_and_keeps_order() {
        let input = "{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{}}\n\n{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{}}\n";
        let mut out: Vec<u8> = Vec::new();
        serve(input.as_bytes(), &mut out, &handler).unwrap();
        let text = String::from_utf8(out).unwrap();
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(
            lines.len(),
            2,
            "两个请求 ⇒ 两条应答（空行不产生应答）：{text}"
        );
        for l in lines {
            assert!(Response::from_line(l).unwrap().ok);
        }
    }

    #[test]
    fn bad_bytes_do_not_swallow_the_next_request() {
        let input = "not json at all\n{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{}}\n";
        let mut out: Vec<u8> = Vec::new();
        serve(input.as_bytes(), &mut out, &handler).unwrap();
        let text = String::from_utf8(out).unwrap();
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(lines.len(), 2, "坏行也要给一条应答，好行照样给：{text}");
        let first = Response::from_line(lines[0]).unwrap();
        assert!(!first.ok, "第一条是协议错");
        assert_eq!(first.err_code.as_deref(), Some(E_PROTOCOL));
        let second = Response::from_line(lines[1]).unwrap();
        assert!(second.ok, "紧跟其后的合法请求**必须**仍被处置：{text}");
    }

    #[test]
    fn a_request_missing_required_fields_is_a_protocol_error() {
        let (res, ok) = handle_line("{\"verb\":\"do\"}", &handler);
        assert!(!ok, "缺 capability ⇒ 不是可解析的请求");
        assert!(!res.ok);
        assert_eq!(res.err_code.as_deref(), Some(E_PROTOCOL));
        assert!(
            res.err_msg.unwrap_or_default().contains("capability"),
            "要点名缺的是哪一个字段"
        );
    }
}
