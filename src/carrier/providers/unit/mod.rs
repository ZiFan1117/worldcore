//! 单元测试（随实现同夹）：夹具在面件，用例按「是否引用 `Stub`」切成两件。

mod refusals;
mod stub_provider;

use serde_json::{json, Value};
use std::path::Path;

// ── 各分件公用的夹具（构造 Manifest／Invocation 与几种 confirm／undo 桩）──

use crate::carrier::capd::Manifest;
use crate::carrier::Invocation;

fn manifest(raw: &str) -> Manifest {
    let c = Manifest::parse(raw, Path::new("t.json")).unwrap();
    Manifest::from_caps(vec![c])
}

fn inv(cap: &str, verb: &str, params: Value) -> Invocation {
    Invocation {
        capability: cap.to_string(),
        verb: verb.to_string(),
        request_id: "r-1".to_string(),
        params,
    }
}

fn no_confirm(_: &str, _: &Value) -> bool {
    false
}
fn yes_confirm(_: &str, _: &Value) -> bool {
    true
}
fn no_undo(_: &str) -> Result<Value, String> {
    Err("测试：未配置撤销点".to_string())
}
fn ok_undo(_: &str) -> Result<Value, String> {
    Ok(json!({"kind":"carrier-undo","path":"/tmp/x"}))
}
