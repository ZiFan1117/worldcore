//! 面③之补：**投影到 A2UI**（T-247）—— ★ **界面由本体投影出来**（确定性，不是 agent 自由生成）。
//!
//! ★ 作者口径（两处，逐字）：
//!   · 「**按照他们的理念，我们要生成这个，就是 GUI，按照他们的理念**」；
//!   · ★★ 更正：「**不是说是把本体变为 A2UI 这个生成器**，就是说**本体里头，比如说有些软件啥的，
//!     它会执行一些动作呀，函数什么的，它会生成 A2UI**」⇒ ★ **是【运行时的产出】**。
//!
//! ★★★ 红线（本仓「不许借」第 13 条，逐字）：
//!   ★「A2UI 的『由 agent 生成界面』那一层 —— **主体是 agent**；★ **只借「目录白名单 ＋
//!     没相容目录就不发」**」⇒ ★ 所以本面**借的正是那两样**：★ **白名单**（catalog 的 18 个元件）
//!     ＋ ★ **不在白名单 ⇒ 拒**（★ 不是静默过滤掉那个元件 —— 过滤会把「目录不对」藏起来）。
//!
//! ★ 投影规则（与实测件一致）：
//!   · 一个**类** ⇒ **Card**（标题 ＋ 它的字段各一个 Text）；
//!   · 一个**在册动作** ⇒ **Button**（挂 _action ＝ 动作名、_function ＝ 本体给的函数入口名）；
//!   · **不在册 ⇒ 根本不生成**（★ 界面里没有那个按钮）。
//!
//! ★ 形状（照 A2UI v1.0 的样例逐字）：
//!   version v1.0 ＋ messages: [ createSurface(surfaceId, catalogId, sendDataModel),
//!                              updateComponents(surfaceId, components[...]) ]

use serde_json::{json, Map, Value};

use crate::core::registry::Registry;
use crate::core::types::{Admit, Reason, Refuse};

/// ★ 载体的名字（本仓的 surface 说法）。
pub const SURFACE_ID: &str = "world/system";

/// ★ 从 catalog 取**元件白名单**（★ 借的是它的目录，不是它的代码）。
fn whitelist(catalog_json: &str) -> Admit<Vec<String>> {
    let doc: Value = serde_json::from_str(catalog_json)
        .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<catalog 不是合法 JSON>"))?;
    let names: Vec<String> = doc
        .get("components")
        .and_then(Value::as_object)
        .map(|m| m.keys().cloned().collect())
        .unwrap_or_default();
    if names.is_empty() {
        return Err(Refuse::new(
            Reason::MissingField {
                field: "components".to_string(),
            },
            "<catalog 里没有元件清单>",
        ));
    }
    Ok(names)
}

/// 取 catalogId（★ 那一格必须跟着 catalog 走，不许自己编）。
fn catalog_id(catalog_json: &str) -> Admit<String> {
    let doc: Value = serde_json::from_str(catalog_json)
        .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<catalog 不是合法 JSON>"))?;
    doc.get("catalogId")
        .and_then(Value::as_str)
        .map(str::to_string)
        .ok_or_else(|| {
            Refuse::new(
                Reason::MissingField {
                    field: "catalogId".to_string(),
                },
                "<catalog 没写 catalogId>",
            )
        })
}

/// ★★ **把在册的东西投影成一帧 A2UI**。
///
/// ★ 输入：在册表（Registry，已合注册表）／本体原文（取类的字段）／catalog 原文（白名单）。
/// ★ 输出：一帧 A2UI（messages）。
/// ★★ 任何一个元件名不在白名单 ⇒ **整帧拒**。
pub fn project(registry: &Registry, source: &str, catalog_json: &str) -> Admit<Value> {
    let allowed = whitelist(catalog_json)?;
    let doc: Value = serde_json::from_str(source)
        .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<本体不是合法 JSON>"))?;
    let cid = catalog_id(catalog_json)?;

    let mut components: Vec<Value> = Vec::new();
    let mut root_children: Vec<String> = Vec::new();

    // ① 一个类 ⇒ 一张 Card（标题 ＋ 字段各一个 Text）。
    let objects = doc
        .get("objects")
        .and_then(Value::as_object)
        .cloned()
        .unwrap_or_default();
    for (class, spec) in &objects {
        if class.starts_with('_') {
            continue;
        }
        let card_id = format!("card_{class}");
        let col_id = format!("col_{class}");
        let title_id = format!("title_{class}");
        components.push(json!({ "id": card_id, "component": "Card", "child": col_id }));
        components
            .push(json!({ "id": title_id, "component": "Text", "text": format!("**{class}**") }));
        let mut col_children = vec![title_id];
        if let Some(fields) = spec.get("fields").and_then(Value::as_object) {
            for (fname, fdecl) in fields {
                if fname.starts_with('_') {
                    continue;
                }
                let fid = format!("f_{class}_{fname}");
                components.push(json!({
                    "id": fid,
                    "component": "Text",
                    "text": format!("{fname}：{}", fdecl.as_str().unwrap_or("?"))
                }));
                col_children.push(fid);
            }
        }
        components.push(json!({ "id": col_id, "component": "Column", "children": col_children }));
        root_children.push(card_id);
    }

    // ② 一个在册动作 ⇒ 一个 Button（挂 _action ＋ _function；不在册 ⇒ 根本不来这里）。
    let mut actions: Vec<String> = registry
        .action_kinds()
        .iter()
        .map(|s| (*s).to_string())
        .collect();
    actions.sort();
    let mut btn_children: Vec<String> = Vec::new();
    for action in &actions {
        let btn_id = format!("btn_{}", action.replace('.', "_"));
        let txt_id = format!("txt_{}", action.replace('.', "_"));
        let mut btn = Map::new();
        btn.insert("id".to_string(), json!(btn_id));
        btn.insert("component".to_string(), json!("Button"));
        btn.insert("child".to_string(), json!(txt_id));
        // ★ 可追溯：动作名 ＋ 本体给的函数入口名（没有函数就不挂 _function）。
        btn.insert("_action".to_string(), json!(action));
        if let Some(f) = registry.function_of_action(action) {
            btn.insert("_function".to_string(), json!(f));
        }
        components.push(Value::Object(btn));
        components.push(json!({ "id": txt_id, "component": "Text", "text": action }));
        btn_children.push(btn_id);
    }
    let col_actions = "col_actions".to_string();
    components.push(json!({ "id": "hdr_actions", "component": "Text", "text": "## 可以做（★ 全部来自在册动作）" }));
    let mut ac: Vec<String> = vec!["hdr_actions".to_string()];
    ac.extend(btn_children);
    components.push(json!({ "id": col_actions, "component": "Column", "children": ac }));
    root_children.push(col_actions);

    // ③ 根 Column。
    let mut root = Map::new();
    root.insert("id".to_string(), json!("root"));
    root.insert("component".to_string(), json!("Column"));
    root.insert("children".to_string(), json!(root_children));
    components.insert(0, Value::Object(root));

    // ★★ 白名单：任何一个元件名不在 catalog 里 ⇒ 整帧拒（「没相容目录就不发」）。
    for c in &components {
        let name = c.get("component").and_then(Value::as_str).unwrap_or("?");
        if !allowed.iter().any(|a| a == name) {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "component".to_string(),
                    rule: allowed.join("|"),
                },
                format!("<{name} 不在 catalog 白名单里>"),
            ));
        }
    }

    Ok(json!({
        "version": "v1.0",
        "name": "worldcore 语义面板（★ 由本体投影生成，不是 agent 自由生成）",
        "messages": [
            { "version": "v1.0",
              "createSurface": { "surfaceId": SURFACE_ID, "catalogId": cid, "sendDataModel": true } },
            { "version": "v1.0",
              "updateComponents": { "surfaceId": SURFACE_ID, "components": components } }
        ]
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");
    const CAT: &str = include_str!("../../../aios-ontology/data/a2ui-catalog-basic.json");

    fn reg() -> Registry {
        Registry::load(ONT).expect("本体该装得上")
    }

    #[test]
    fn the_projection_is_deterministic_and_every_component_is_in_the_catalog() {
        let a = project(&reg(), ONT, CAT).expect("该投得出来");
        let b = project(&reg(), ONT, CAT).expect("该投得出来");
        assert_eq!(a, b, "★ 同一份本体 ⇒ 同一帧（确定性）");
        let comps = a["messages"][1]["updateComponents"]["components"]
            .as_array()
            .expect("该有 components");
        assert!(
            comps.len() > 9,
            "★ 类 ＋ 动作都该进来（现取 {}）",
            comps.len()
        );
        let btns: Vec<&Value> = comps
            .iter()
            .filter(|c| c.get("component").and_then(Value::as_str) == Some("Button"))
            .collect();
        assert_eq!(btns.len(), 9, "★ 9 个在册动作 ⇒ 9 个 Button");
        for b in btns {
            assert!(b.get("_action").is_some(), "★ 按钮必须挂 _action");
        }
    }

    #[test]
    fn a_component_outside_the_catalog_is_refused() {
        // ★ catalog 只留 Text ⇒ 其余的元件名（Card／Column／Button）就在白名单外 ⇒ 整帧拒。
        let tiny = r#"{"catalogId":"x","components":{"Text":{}}}"#;
        let got = project(&reg(), ONT, tiny);
        assert!(got.is_err(), "★ 不在白名单 ⇒ 整帧拒（不是静默过滤）");
    }

    #[test]
    fn a_frame_carries_the_actions_field_and_the_catalog_id() {
        let f = project(&reg(), ONT, CAT).expect("该投得出来");
        assert_eq!(f["version"], "v1.0");
        let cid = f["messages"][0]["createSurface"]["catalogId"]
            .as_str()
            .unwrap_or("");
        assert!(
            cid.contains("a2ui.org"),
            "★ catalogId 必须跟着 catalog（不许自己编）"
        );
        let txt = f.to_string();
        assert!(txt.contains("notice.mute"), "★ 在册的动作该出现在界面里");
        assert!(
            txt.contains("fn.notice.mute"),
            "★ 按钮要挂 _function（可追溯到本体）"
        );
    }
}
