//! **行分隔的结构化请求／应答** —— 会红的断言（原 Go `agentd/internal/server` 的 Rust 侧对应面）。
//!
//! ## 每条断言"改坏哪一行会红"
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `p01` | `serve()` 里"逐行读、逐行写"改成"攒起来最后一起写"（或把 `trim_end_matches` 删掉，让空行也产生应答）⇒ **红**（条数或顺序对不上） |
//! | `p02` | `serve()` 里解析不了的分支从"写一条协议错**然后继续**"改成 `return Err(..)`（中止）⇒ **红**（坏行后面那条好请求**收不到应答**） |
//! | `p03` | `Response::refused` 的 `err_code` 改成 `None`（拒绝不给码）⇒ **红**（调用方无法只按码分支） |
//!
//! ## 正控（钉住"不该红的"）
//!
//! | 用例 | 它钉什么 |
//! |---|---|
//! | `p03` 的前半段 | `ok==true` 的应答**不许**带 `err_code`——否则"成功"与"错误码"同时出现，两种读法会给出两个结论 |
//! | `p01` | 空行**不产生**应答：三行输入（含一空行）只能出**两条**应答 |
//!
//! ## 逐字的依据
//!
//! 原 Go 侧 `internal/server` 的形态是"一行请求、一行应答"（`bufio` ＋ `json.Decoder`），
//! 且"请求无法解析时回一条结构化错误"（`writeErr`）。本文件把它写成**会红**的断言。

use serde_json::json;
use world_core::agent::protocol::{
    call, handle_line, protocol_error, serve, Request, Response, E_PROTOCOL,
};

/// 一个只认 `a.b`／`do` 的处理器（拒绝时**必须**带码）。
fn handler(req: &Request) -> Response {
    if req.capability == "a.b" && req.verb == "do" {
        Response::ok(json!({ "echo": req.args, "capability": req.capability }))
    } else {
        Response::refused(
            "ext.world.Agent.Denied.UnknownCapability",
            "能力不在声明里（判据：拒绝要给码，不给散文）",
        )
    }
}

/// `p01` —— **一问一答，顺序一致**。
#[test]
fn p01_one_request_one_response_in_order() {
    // 两行请求，中间夹一个空行（填充）：**空行不产生应答**
    let input = concat!(
        "{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{\"n\":1}}\n",
        "\n",
        "{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{\"n\":2}}\n"
    );
    let mut out: Vec<u8> = Vec::new();
    serve(input.as_bytes(), &mut out, &handler).unwrap();
    let text = String::from_utf8(out).unwrap();

    let lines: Vec<&str> = text.lines().collect();
    assert_eq!(
        lines.len(),
        2,
        "两个请求 ⇒ 恰好两条应答（空行不产生应答）；实得：\n{text}"
    );

    // 顺序一致：第一条对应 n=1，第二条对应 n=2
    let a = Response::from_line(lines[0]).unwrap();
    let b = Response::from_line(lines[1]).unwrap();
    assert!(a.ok && b.ok, "两条都该成功：{text}");
    assert_eq!(
        a.data.unwrap().get("echo").unwrap().get("n"),
        Some(&json!(1)),
        "第一条应答必须对应第一个请求（顺序不许换）"
    );
    assert_eq!(
        b.data.unwrap().get("echo").unwrap().get("n"),
        Some(&json!(2)),
        "第二条应答必须对应第二个请求"
    );

    // 每条应答都是**一行**（不含换行）
    for l in &lines {
        assert!(!l.contains('\n'), "一帧就是一帧");
        assert!(Response::from_line(l).is_ok(), "每行都是合法应答：{l}");
    }
}

/// `p02` —— **不可解析的请求不吞掉下一条**。
///
/// 这是本件最要紧的一条：把 `serve` 的坏字节分支改成"中止"，它就红。
#[test]
fn p02_bad_bytes_do_not_swallow_the_next_request() {
    let input = concat!(
        "这不是 JSON\n",
        "{\"capability\":\"a.b\",\"verb\":\"do\",\"args\":{}}\n"
    );
    let mut out: Vec<u8> = Vec::new();
    serve(input.as_bytes(), &mut out, &handler)
        .expect("坏字节【不许】让整条服务中止——那会吞掉后面的合法请求");
    let text = String::from_utf8(out).unwrap();
    let lines: Vec<&str> = text.lines().collect();

    assert_eq!(
        lines.len(),
        2,
        "坏行也要给一条应答，紧跟的好行照样要给：**一行坏字节能吞掉后面那条请求**\
         正是本用例要消灭的形态；实得：\n{text}"
    );

    let bad = Response::from_line(lines[0]).unwrap();
    assert!(!bad.ok, "坏行的应答必须是 ok=false");
    assert_eq!(
        bad.err_code.as_deref(),
        Some(E_PROTOCOL),
        "坏行必须点名协议类错误码；实得：{}",
        lines[0]
    );
    assert!(
        bad.err_msg.as_deref().unwrap_or("").contains("JSON"),
        "错误说明应当指出【不是合法 JSON】这一层；实得：{:?}",
        bad.err_msg
    );

    let good = Response::from_line(lines[1]).unwrap();
    assert!(
        good.ok,
        "紧跟坏行之后的合法请求**必须**仍被处置并成功；实得：{}",
        lines[1]
    );

    // `handle_line` 的第二个返回值就是"这行是不是可解析的请求"
    let (_r1, parsed1) = handle_line("垃圾", &handler);
    let (_r2, parsed2) = handle_line("{\"capability\":\"a.b\",\"verb\":\"do\"}", &handler);
    assert!(!parsed1, "坏行 ⇒ parsed=false");
    assert!(parsed2, "好行 ⇒ parsed=true");
}

/// `p03` —— **失败也结构化，不靠散文**。
#[test]
fn p03_refusals_are_structured_not_prose() {
    // 拒绝：必须有码
    let req = Request::new("no.such", "do", json!({}));
    let res = handler(&req);
    assert!(!res.ok);
    let code = res
        .err_code
        .as_deref()
        .expect("拒绝必须给机器可读的码——没有码，调用方只能从散文里猜");
    assert!(
        code.starts_with("ext.world."),
        "错误码必须带本项目的前缀，读流水的人才能程序判定；实得 {code}"
    );
    // 应答行里真的带了这个码
    let line = res.to_line();
    assert!(line.contains(code), "码必须出现在应答行里：{line}");
    assert_eq!(
        Response::from_line(&line).unwrap().err_code.as_deref(),
        Some(code),
        "往返之后码不许变"
    );

    // **正控**：成功**不许**带码
    let ok = Response::ok(json!({ "fine": true }));
    assert!(
        ok.err_code.is_none(),
        "成功同时带错误码 ⇒ 两种读法给出两个结论，这是自相矛盾"
    );
    let okline = ok.to_line();
    assert!(
        !okline.contains("err_code"),
        "成功那行的 JSON 里不许出现 err_code：{okline}"
    );

    // 协议错也是结构化的（不是一句散文）
    let pe = protocol_error("请求缺 verb");
    assert!(!pe.ok);
    assert_eq!(pe.err_code.as_deref(), Some(E_PROTOCOL));

    // 客户端助手：一发一收，形态一致
    let mut wire: Vec<u8> = Vec::new();
    let mut reader: &[u8] = b"{\"ok\":true,\"data\":{\"x\":1}}\n";
    let got = call(
        &mut wire,
        &mut reader,
        &Request::new("a.b", "do", json!({})),
    )
    .unwrap();
    assert!(got.ok);
    assert_eq!(got.data, Some(json!({ "x": 1 })));
    let sent = String::from_utf8(wire).unwrap();
    assert_eq!(sent.lines().count(), 1, "助手一次只发一行：{sent}");
    assert!(
        Request::from_line(sent.trim()).is_ok(),
        "它发出的必须是一行合法请求：{sent}"
    );
}
