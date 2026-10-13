//! 一条函数 —— 本体 `functions.entries.<function_id>` 的现取。
//!
//! ★ 形状照 P 的 `OntologyFunction`：`function_id`／`display_name`／`description`／
//! `inputs`／`output_type`；★ 口径见母件 `functions.rs` 的模块头。

use std::collections::BTreeMap;

use serde_json::{Map, Value};

use crate::core::types::{Admit, Reason, Refuse};
use crate::engine::validate::FieldType;

/// 一条函数（本体 `functions.entries.<function_id>`）。
#[derive(Debug, Clone, PartialEq)]
pub struct Function {
    id: String,
    display_name: String,
    description: String,
    inputs: BTreeMap<String, FieldType>,
    output_type: FieldType,
}

impl Function {
    /// 从本体的一条 `entries.<function_id>` 读。
    ///
    /// ★ 收下**之前**先拒三条：不是对象；缺 `function_id`；`function_id` 是空串或含
    /// 命令字面量（空格／`/`／`"` —— 本体 `functions._no_command_literal` 的前一半）。
    /// ★ 宿主命令名的**整表**审查在 `Functions::load`（那里才拿得到
    /// `_registered_host_commands`）。
    pub fn load(entry: &Value) -> Admit<Self> {
        let Some(map) = entry.as_object() else {
            return Err(Refuse::new(
                Reason::BadName,
                "functions.entries 的条目不是对象",
            ));
        };
        let Some(id) = map.get("function_id").and_then(Value::as_str) else {
            return Err(Refuse::new(
                Reason::MissingField {
                    field: "function_id".to_string(),
                },
                "functions.entries",
            ));
        };
        if id.trim().is_empty() || has_command_literal(id) {
            return Err(Refuse::new(Reason::BadName, id));
        }
        Ok(Self {
            id: id.to_string(),
            display_name: text(map, "display_name"),
            description: text(map, "description"),
            inputs: inputs_of(map),
            output_type: output_of(map),
        })
    }

    /// 它的名字（本体 `function_id`）。
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    /// 给人看的名字。
    #[must_use]
    pub fn display_name(&self) -> &str {
        &self.display_name
    }

    /// 说明文字。
    #[must_use]
    pub fn description(&self) -> &str {
        &self.description
    }

    /// 入参：名 ⇒ 类型声明（读法与面③**同一件** `FieldType`）。
    #[must_use]
    pub fn inputs(&self) -> &BTreeMap<String, FieldType> {
        &self.inputs
    }

    /// 出参类型（★ 未定的三条照原样是空串）。
    #[must_use]
    pub fn output_type(&self) -> &FieldType {
        &self.output_type
    }

    /// ★ 逐条校入参（★ 全部在「交给干活的」**之前**）：
    ///
    /// ① **本体没声明的入参 ⇒ 拒**（与面③「本体没声明的格也拒」同一条口径）；
    /// ② 值的类型／取值域不合 ⇒ 拒（`enum(…)` 的取值域算在类型里）。
    ///
    /// ★ 少给入参**不拒** —— 本体 `inputs` 今天没有 `required` 标记（见母件顶部①）。
    pub fn check_args(&self, args: &Map<String, Value>) -> Admit<()> {
        for (name, value) in args {
            let Some(declared) = self.inputs.get(name) else {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: name.clone(),
                        rule: "本体未声明该入参".to_string(),
                    },
                    self.id.clone(),
                ));
            };
            if value.is_null() {
                continue; // 空值＝没填（必填今天不咬）
            }
            if !declared.accepts(value) {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: name.clone(),
                        rule: declared.declaration(),
                    },
                    self.id.clone(),
                ));
            }
        }
        Ok(())
    }

    /// 把它「列单」出去 —— 照 P 的 `OntologyFunction.describe()` 形状：
    /// `function_id`／`display_name`／`description`／`inputs`（名 ⇒ 声明串）／`output_type`。
    ///
    /// ★ 只描述、不干活（P 的 `describe()` 与 `execute()` 分两件，这里也分两件）。
    #[must_use]
    pub fn describe(&self) -> Value {
        let inputs: Map<String, Value> = self
            .inputs
            .iter()
            .map(|(name, declared)| (name.clone(), Value::String(declared.declaration())))
            .collect();
        let mut out = Map::new();
        out.insert("function_id".to_string(), Value::String(self.id.clone()));
        out.insert(
            "display_name".to_string(),
            Value::String(self.display_name.clone()),
        );
        out.insert(
            "description".to_string(),
            Value::String(self.description.clone()),
        );
        out.insert("inputs".to_string(), Value::Object(inputs));
        out.insert(
            "output_type".to_string(),
            Value::String(self.output_type.declaration()),
        );
        Value::Object(out)
    }
}

/// 取一格说明文字（缺／不是字符串 ⇒ 空串 —— 本体这两格是说明，不是闸）。
fn text(map: &Map<String, Value>, field: &str) -> String {
    map.get(field)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

/// 读 `inputs`（入参名 ⇒ 类型声明串；★ 照面③ `FieldType::parse` 同一条读法）。
fn inputs_of(map: &Map<String, Value>) -> BTreeMap<String, FieldType> {
    let mut out = BTreeMap::new();
    let Some(declared) = map.get("inputs").and_then(Value::as_object) else {
        return out;
    };
    for (name, declaration) in declared {
        out.insert(
            name.clone(),
            FieldType::parse(declaration.as_str().unwrap_or_default()),
        );
    }
    out
}

/// 读 `output_type`（★ 空串照收 —— 本体自己登记了三条未定）。
fn output_of(map: &Map<String, Value>) -> FieldType {
    FieldType::parse(
        map.get("output_type")
            .and_then(Value::as_str)
            .unwrap_or_default(),
    )
}

/// 名字里出现命令字面量的形状吗（本体 `functions._no_command_literal` 的前一半）。
fn has_command_literal(name: &str) -> bool {
    name.contains(' ') || name.contains('/') || name.contains('"')
}
