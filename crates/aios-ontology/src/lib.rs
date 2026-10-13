//! aios-ontology —— worldcore 本体在 AIOS 侧的装载与校验面。
//!
//! 这是一次 spike（分支 spike/ontology-mvp）：要证的只有一件事 ——
//! AIOS 认知核产出的 action_name，其权威来源可以不是
//! translator_system_prompt.txt 里的自由字符串，而是本体。
//!
//! 本 crate 只读不写：不解析 TTL、不推理、不引新依赖（只有 serde_json）。

use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt;

/// 本体五节缺一 ⇒ 拒启（与本体自己的 _five_elements._reading_order 同口径）。
pub const CODE_MISSING_SECTION: &str = "ext.world.Ontology.MissingSection";
/// 动作名不在本体的 _actions 里。
pub const CODE_ACTION_UNKNOWN: &str = "ext.world.Ontology.ActionUnknown";
/// 动作引用的能力不在 _interfaces 里。
pub const CODE_ACTION_CAPABILITY_UNKNOWN: &str = "ext.world.Ontology.ActionCapabilityUnknown";
/// 入口表里出现命令字面量（本体的 _no_command_literal 判据）。
pub const CODE_FUNCTION_LITERAL_NOT_ALLOWED: &str = "ext.world.Ontology.FunctionLiteralNotAllowed";

/// 五节，照本体 _five_elements._reading_order 逐字：对象 / 关系 / 接口能力 / 动作 / 函数。
const SECTIONS: [&str; 5] = [
    "objects",
    "links",
    "interfaces",
    "actions",
    "functions",
];

/// 拒。每一条都带本仓现成的错误码。
#[derive(Debug, PartialEq)]
pub enum Reject {
    /// 本体缺五节之一。
    MissingSection { section: String },
    /// 翻译器给出的动作名不在本体里。
    UnknownActionName { action_name: String },
    /// 动作引用的能力没有声明。
    ActionCapabilityUnknown {
        action_name: String,
        capability: String,
    },
    /// 入口表里出现命令字面量。
    FunctionLiteralNotAllowed { literal: String },
}

impl Reject {
    /// 错误码（与本体声明的字符串逐字一致）。
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::MissingSection { .. } => CODE_MISSING_SECTION,
            Self::UnknownActionName { .. } => CODE_ACTION_UNKNOWN,
            Self::ActionCapabilityUnknown { .. } => CODE_ACTION_CAPABILITY_UNKNOWN,
            Self::FunctionLiteralNotAllowed { .. } => CODE_FUNCTION_LITERAL_NOT_ALLOWED,
        }
    }
}

impl fmt::Display for Reject {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingSection { section } => {
                write!(f, "{}: 缺节 {}", CODE_MISSING_SECTION, section)
            }
            Self::UnknownActionName { action_name } => {
                write!(
                    f,
                    "{}: 动作名 {} 不在本体里",
                    CODE_ACTION_UNKNOWN, action_name
                )
            }
            Self::ActionCapabilityUnknown {
                action_name,
                capability,
            } => write!(
                f,
                "{}: 动作 {} 引用的能力 {} 未声明",
                CODE_ACTION_CAPABILITY_UNKNOWN, action_name, capability
            ),
            Self::FunctionLiteralNotAllowed { literal } => write!(
                f,
                "{}: 入口表里的 {} 是命令字面量",
                CODE_FUNCTION_LITERAL_NOT_ALLOWED, literal
            ),
        }
    }
}

impl std::error::Error for Reject {}

/// 一条已声明的动作。
#[derive(Debug, Clone)]
pub struct Action {
    /// 它引用的能力（必须在 _interfaces 里）。
    pub capability: String,
    /// 是否存在补偿路径（本体口径）。
    pub reversible: bool,
    /// 已声明的参数名。
    pub parameters: Vec<String>,
}

/// 校验通过时的判词。
#[derive(Debug, PartialEq)]
pub struct Verdict {
    /// 被校验的动作名。
    pub action_name: String,
    /// 它命中的能力。
    pub capability: String,
    /// 翻译器自报的置信度。
    pub confidence: f64,
    /// 本体要求但翻译器没给的参数（只报不拒）。
    pub missing_required_parameters: Vec<String>,
}

/// 本体（只取校验需要的几节）。
#[derive(Debug)]
pub struct Ontology {
    actions: BTreeMap<String, Action>,
    capabilities: Vec<String>,
    entries: serde_json::Map<String, Value>,
    host_commands: Vec<String>,
}

fn literal_violation(name: &str, host_commands: &[String]) -> Option<String> {
    if name.contains(' ') || name.contains('/') || name.contains('"') {
        return Some(name.to_string());
    }
    if host_commands.iter().any(|c| c == name) {
        return Some(name.to_string());
    }
    None
}

impl Ontology {
    /// 从 JSON 文本装载。五节缺一 ⇒ 拒。
    pub fn load_str(text: &str) -> Result<Self, Reject> {
        let doc: Value = serde_json::from_str(text).map_err(|_| Reject::MissingSection {
            section: "<不是合法 JSON>".to_string(),
        })?;
        for section in SECTIONS {
            if doc.get(section).is_none() {
                return Err(Reject::MissingSection {
                    section: section.to_string(),
                });
            }
        }

        let mut actions = BTreeMap::new();
        if let Some(map) = doc["actions"].as_object() {
            for (name, body) in map {
                if name.starts_with('_') {
                    continue;
                }
                let capability = body
                    .get("capability")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .to_string();
                let reversible = body
                    .get("reversible")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
                let parameters = body
                    .get("parameters")
                    .and_then(Value::as_array)
                    .map(|list| {
                        list.iter()
                            .filter_map(|p| {
                                p.get("name").and_then(Value::as_str).map(str::to_string)
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                actions.insert(
                    name.clone(),
                    Action {
                        capability,
                        reversible,
                        parameters,
                    },
                );
            }
        }

        let capabilities = doc["interfaces"]
            .as_object()
            .map(|map| {
                map.keys()
                    .filter(|k| !k.starts_with('_'))
                    .cloned()
                    .collect()
            })
            .unwrap_or_default();

        let entries: serde_json::Map<String, Value> = doc["functions"]
            .get("entries")
            .and_then(Value::as_object)
            .cloned()
            .unwrap_or_default();

        let host_commands: Vec<String> = doc["functions"]
            .get("_registered_host_commands")
            .and_then(Value::as_array)
            .map(|list| {
                list.iter()
                    .filter_map(|v| v.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default();

        for name in entries.keys() {
            if let Some(literal) = literal_violation(name, &host_commands) {
                return Err(Reject::FunctionLiteralNotAllowed { literal });
            }
        }

        Ok(Self {
            actions,
            capabilities,
            entries,
            host_commands,
        })
    }

    /// 从文件装载。
    pub fn load_file(path: &std::path::Path) -> Result<Self, Reject> {
        let text = std::fs::read_to_string(path).map_err(|_| Reject::MissingSection {
            section: "<读不到文件>".to_string(),
        })?;
        Self::load_str(&text)
    }

    /// 本体的动作名（升序）。
    #[must_use]
    pub fn action_names(&self) -> Vec<&str> {
        self.actions.keys().map(String::as_str).collect()
    }

    /// ★ 动作名是否已登记（供上游在构造动作前查表）。
    #[must_use]
    pub fn has_action(&self, action_name: &str) -> bool {
        self.actions.contains_key(action_name)
    }

    /// ★ 未登记则给出本体的拒；已登记 ⇒ None。
    #[must_use]
    pub fn reject_unknown_action(&self, action_name: &str) -> Option<Reject> {
        if self.has_action(action_name) {
            None
        } else {
            Some(Reject::UnknownActionName {
                action_name: action_name.to_string(),
            })
        }
    }

    /// 本体的能力名。
    #[must_use]
    pub fn capability_names(&self) -> Vec<&str> {
        self.capabilities.iter().map(String::as_str).collect()
    }

    /// 入口表条数（现取为 0 —— 这是本体自己登记的缺口）。
    #[must_use]
    pub fn function_entry_count(&self) -> usize {
        self.entries.len()
    }

    /// 已登记的宿主包管理器命令数。
    #[must_use]
    pub fn host_command_count(&self) -> usize {
        self.host_commands.len()
    }

    /// 校验一份 AIOS 翻译器的产出（translator_system_prompt.txt 的那个 JSON 形状）。
    pub fn validate_translation(&self, translator_json: &str) -> Result<Verdict, Reject> {
        let value: Value =
            serde_json::from_str(translator_json).map_err(|_| Reject::UnknownActionName {
                action_name: "<不是合法 JSON>".to_string(),
            })?;
        let action_name = value
            .get("action_name")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        let Some(action) = self.actions.get(&action_name) else {
            return Err(Reject::UnknownActionName { action_name });
        };
        if !self.capabilities.iter().any(|c| c == &action.capability) {
            return Err(Reject::ActionCapabilityUnknown {
                action_name,
                capability: action.capability.clone(),
            });
        }
        let supplied: Vec<String> = value
            .get("parameters")
            .and_then(Value::as_object)
            .map(|m| m.keys().cloned().collect())
            .unwrap_or_default();
        let missing_required_parameters = action
            .parameters
            .iter()
            .filter(|p| !supplied.contains(p))
            .cloned()
            .collect();
        Ok(Verdict {
            action_name,
            capability: action.capability.clone(),
            confidence: value
                .get("confidence")
                .and_then(Value::as_f64)
                .unwrap_or(0.0),
            missing_required_parameters,
        })
    }

    /// 本体自己登记的缺口（如实转述，不当结论）。
    #[must_use]
    pub fn declared_gaps(&self) -> Vec<String> {
        let mut out = Vec::new();
        if self.entries.is_empty() {
            out.push("五要素之五零实例：_functions.entries 是空表 ⇒ 名字级通过、节级为空（本体 _functions._declared_gaps 逐字）。".to_string());
        }
        if !self.host_commands.is_empty() {
            out.push(format!(
                "_registered_host_commands 现取 {} 条 —— 这些字面量不许进入口表。",
                self.host_commands.len()
            ));
        }
        out
    }
}
