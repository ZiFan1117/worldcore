//! 函数表 —— 本体 `functions.entries` 装成一张表，外加一个「干活的」。
//!
//! ★ 表与「干活的」**分开两样**：声明从本体来，「干活的」由注入 ——
//!   本件不替谁发明实现，也不把实现塞进表（本体 `functions._comment`：
//!   「本表**只收入口名**：它是一张**引用表**，代码不进本体」）。
//! ★ 口径详见母件 `functions.rs` 的模块头。

use std::collections::BTreeMap;

use serde_json::{Map, Value};

use crate::core::types::{Admit, Reason, Refuse};
use crate::engine::validate::FieldType;

use super::entry::Function;

/// 「干活的」—— 函数声明之外**那一段真代码**（本体：代码不进本体）。
pub trait Doer {
    /// 真的去做；交回来的东西进 `Called::value`。
    fn do_it(&self, function: &Function, args: &Map<String, Value>) -> Admit<Value>;
}

/// 闭包也能当「干活的」（省得为一个口子单开一个类型）。
impl<F> Doer for F
where
    F: Fn(&Function, &Map<String, Value>) -> Admit<Value>,
{
    fn do_it(&self, function: &Function, args: &Map<String, Value>) -> Admit<Value> {
        self(function, args)
    }
}

/// 只报不干活的「干活的」（本仓默认；★ 别读成「已经会装了」）。
#[derive(Debug, Default)]
pub struct DryDoer;

impl Doer for DryDoer {
    fn do_it(&self, function: &Function, _args: &Map<String, Value>) -> Admit<Value> {
        Ok(Value::String(format!("dry-run:{}", function.id())))
    }
}

/// 一次调用的结果。
#[derive(Debug, Clone, PartialEq)]
pub struct Called {
    /// 调的是哪条函数。
    pub function_id: String,
    /// 它声明的出参类型（★ 未定的三条照原样是空串）。
    pub output_type: FieldType,
    /// 「干活的」交回来的东西。
    pub value: Value,
}

/// 函数表（本体 `functions.entries` 的现取）＋ 一个「干活的」。
#[derive(Debug)]
pub struct Functions<D: Doer = DryDoer> {
    entries: BTreeMap<String, Function>,
    doer: D,
}

impl Functions<DryDoer> {
    /// 从本体 JSON **文本**建表（默认挂「只报不干活」的那一件）。
    ///
    /// ★ 收的是文本（不是已解析的值）—— 与面① `Registry::load`／面③ `ObjectSpec::load`
    ///   同一条入口。想挂真「干活的」用 `load_with`。
    pub fn load(text: &str) -> Admit<Self> {
        Self::load_with(text, DryDoer)
    }
}

impl<D: Doer> Functions<D> {
    /// 从本体 JSON **文本**建表，并把「干活的」一起挂上。
    ///
    /// ★ 与面①／面③ **同一条口径**：本体没装载（不是合法 JSON／五节缺一）⇒ `OntologyNotLoaded`。
    /// ★ 多一道**命令字面量**审查（本体 `functions._no_command_literal` 逐字）：
    ///   入口名含空格／`/`／`"`，或等于 `functions._registered_host_commands` 里已登记的
    ///   宿主命令名 ⇒ `BadName`。★ **如实登记**：本体那件的码是
    ///   `ext.world.Ontology.FunctionLiteralNotAllowed`，本内核的 `Reason` 里没有这一条
    ///   （本席的写域不含 `core/types.rs`）⇒ 本件映射到语义最近的 `BadName`，不擅自加码。
    /// ★ 表以 `function_id` 为键：条目名与 `function_id` 不一致 ⇒ `BadName`。
    pub fn load_with(text: &str, doer: D) -> Admit<Self> {
        // ★ 本体装载闸（与面①／面③ 同一句）：缺节 / 不是合法 JSON ⇒ 谁都别想动。
        match aios_ontology::Ontology::load_str(text) {
            Ok(_) => {}
            Err(aios_ontology::Reject::MissingSection { .. }) => {
                return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
            }
            // ★ 它其余的拒（入口表里的命令字面量）⇒ 落到本件下面**逐条**给更准的理由。
            Err(_) => {}
        }
        let doc: Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        // ★ `functions` 节在而 `entries` 缺 ⇒ 也当「没装载全」拒（本内核的严格读法；
        //   真实本体恒有 `entries`）。
        let entries = entries_of(&doc)
            .ok_or_else(|| Refuse::new(Reason::OntologyNotLoaded, "<functions.entries 缺>"))?;
        let host_commands = host_commands_of(&doc);
        let mut table = BTreeMap::new();
        for (key, entry) in entries {
            if key.starts_with('_') {
                continue; // ★ `_` 键是说明／登记的缺口，不是函数。
            }
            let function = Function::load(entry)?;
            if function.id() != key.as_str() {
                return Err(Refuse::new(Reason::BadName, key.clone()));
            }
            if host_commands.iter().any(|c| c == key) {
                return Err(Refuse::new(Reason::BadName, key.clone()));
            }
            table.insert(key.clone(), function);
        }
        Ok(Self {
            entries: table,
            doer,
        })
    }

    /// 按函数名取（★ 不在册 ⇒ `None`；「未登记即拒」由 `call` 发）。
    #[must_use]
    pub fn get(&self, function_id: &str) -> Option<&Function> {
        self.entries.get(function_id)
    }

    /// 在册的函数名（升序）。
    #[must_use]
    pub fn ids(&self) -> Vec<&str> {
        self.entries.keys().map(String::as_str).collect()
    }

    /// 在册几条。
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// 空表吗。
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// ★★ 调用一条函数：① 查在册 ⇒ ② 逐条校入参 ⇒ ③ 才交给「干活的」。
    ///
    /// ★ 三步的次序与面⑦ `Exec::execute` 同一条道理：**被拒的调用碰不到「干活的」那一层**。
    /// ★ 这里**不查治理** —— 本体逐字「『有没有许可』不在这里定」（见母件顶部③）。
    pub fn call(&self, function_id: &str, args: &Map<String, Value>) -> Admit<Called> {
        let Some(function) = self.get(function_id) else {
            return Err(Refuse::new(Reason::UnknownKind, function_id));
        };
        function.check_args(args)?;
        let value = self.doer.do_it(function, args)?;
        Ok(Called {
            function_id: function.id().to_string(),
            output_type: function.output_type().clone(),
            value,
        })
    }
}

/// 本体 `functions.entries`（★ 不是对象 ⇒ `None`）。
fn entries_of(doc: &Value) -> Option<&Map<String, Value>> {
    doc.get("functions")?.get("entries")?.as_object()
}

/// 本体 `functions._registered_host_commands`（缺／不是数组 ⇒ 空表）。
fn host_commands_of(doc: &Value) -> Vec<String> {
    doc.get("functions")
        .and_then(|f| f.get("_registered_host_commands"))
        .and_then(Value::as_array)
        .map(|list| {
            list.iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}
