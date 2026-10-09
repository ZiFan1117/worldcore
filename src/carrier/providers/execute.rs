use super::Registry;
use crate::carrier::provider::Outcome;
use serde_json::{json, Value};

/// 执行一次调用：**清单 → 动词 → 执行器 → 结果**。
///
/// 顺序固定，且**每一步失败都不进入下一步**：
///
/// 1. 清单里没有这项能力 ⇒ **拒绝**（根本不动手）；
/// 2. 清单里没有这个动词 ⇒ **拒绝**；
/// 3. 没有对应执行器 ⇒ **拒绝**（并点名"注册表里没有"）；
/// 4. **执行器自报的能力里没有这一项 ⇒ 拒绝**（`cap.d` 与执行器两套词表对不上，见 [`cross_check`]）；
/// 5. 需要人确认 ⇒ 问确认入口；确认未给或入口不可用 ⇒ **拒绝**；
/// 6. 需要载体撤销点 ⇒ 先做撤销点；做不成 ⇒ **拒绝**（不带着"撤不回去"的风险动手）；
/// 7. 执行；
/// 8. 组装结果（成功/失败）。
///
/// ⚠️ **本函数不做"允不允许"的裁决**：它能做的只有"拒绝"，永远不能"放行"——
/// 放行由调用方在**问过门禁之后**才走到这里。
pub fn execute(
    manifest: &crate::carrier::capd::Manifest,
    registry: &Registry,
    inv: &crate::carrier::Invocation,
    confirm: &dyn Fn(&str, &Value) -> bool,
    undo_marker: &dyn Fn(&str) -> Result<Value, String>,
) -> Outcome {
    let cap = match manifest.lookup(&inv.capability) {
        Some(c) => c,
        None => {
            return Outcome::refused(json!({
                "reason": "能力不在执行清单里",
                "capability": inv.capability,
                "manifest": manifest.names(),
            }))
        }
    };
    if !cap.allows(&inv.verb) {
        return Outcome::refused(json!({
            "reason": "动词未被该能力授权",
            "capability": inv.capability,
            "verb": inv.verb,
            "allowed": cap.verbs,
        }));
    }
    let provider = match registry.get(&cap.provider) {
        Some(p) => p,
        None => {
            return Outcome::refused(json!({
                "reason": "没有对应的执行器",
                "provider": cap.provider,
                "registered": registry.names(),
            }))
        }
    };
    // ★ 第 4 步：**执行器自报的能力里必须有这一项**（2026-10-04 接上那一格）。
    //   与第 3 步分开写是刻意的：**"没注册"与"注册了但不会这个"是两件事**，
    //   拒绝的理由要各说各的，否则复盘时分不清是"没装"还是"装错了"。
    if !provider.capabilities().iter().any(|c| *c == cap.name) {
        return Outcome::refused(json!({
            "reason": "执行器自报的能力里没有这一项（两套词表对不上）",
            "capability": cap.name,
            "provider": cap.provider,
            "provider_capabilities": provider.capabilities(),
        }));
    }
    if cap.needs_confirm() && !confirm(&inv.capability, &inv.params) {
        return Outcome::refused(json!({
            "reason": "需要人确认而未获确认（默认拒绝）",
            "capability": inv.capability,
        }));
    }
    let mut undo_ref = None;
    if cap.needs_undo() {
        match undo_marker(&inv.request_id) {
            Ok(u) => undo_ref = Some(u),
            Err(e) => {
                return Outcome::refused(json!({
                    "reason": "撤销点做不成，故不动手",
                    "error": e,
                }))
            }
        }
    }
    match provider.call(&inv.verb, &inv.params) {
        Ok(data) => {
            let o = Outcome::ok(data);
            match undo_ref {
                Some(u) => o.with_undo(u),
                None => o,
            }
        }
        Err(e) => {
            let code =
                crate::common::error::code_of(&e).unwrap_or("ext.world.Carrier.ProviderFailed");
            if code.ends_with("UnknownVerb") || code.ends_with("BadParam") {
                // 参数/动词层面的错属于"根本没动手"。
                let mut o = Outcome::refused(json!({ "reason": e }));
                if let Some(u) = undo_ref {
                    o = o.with_undo(u);
                }
                o
            } else {
                let mut o = Outcome::failed(-1, json!({ "reason": e }));
                if let Some(u) = undo_ref {
                    o = o.with_undo(u);
                }
                o
            }
        }
    }
}
