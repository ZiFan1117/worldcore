//! 本体的「每一类有哪几格、每格什么规格」—— 校验面的权威输入（★ 不另立清单）。
//!
//! 参考 Palantir：`core/object_type.py` 的 `Property.validate_value` 与
//! `ObjectType.validate_instance`（逐格：必填／值类型／取值域；★ 它把**没声明的格**也当错）。
//!
//! ★ 权威只有一处：`objects.<类>.fields` 的类型声明串（怎么读见 `field.rs`）。
//! ★ 本件不替本体发明口径：`_field_meta.<格>.required` 今天**全是 `null`**
//!   （本体逐字：「今天没有依据 ⇒ 填 `null`，**不是『不要』，是『还没定』**」）
//!   ⇒ **只认显式 `true`** 为必填 —— 今天因此一格都不咬；要它咬，得本体自己写。
//!
//! ★ 这一处将来接 **AIOS 的**哪一件：memory 内的这份规格，将来由 AIOS 的**写闸**（`aios-policy`
//!   的 `authorize_write`／`src/gate/policy.json`）在「改世界」之前再过一道；
//!   本件今天只管「这一笔实例合不合本体的格」。

use std::collections::BTreeMap;

use serde_json::Value;

use crate::core::types::{Admit, Reason, Refuse, Registration};

use super::field::FieldType;

/// 一格的规格。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldSpec {
    /// 本体声明的类型。
    pub field_type: FieldType,
    /// 本体是否**显式**声明必填（今天：一格都没有）。
    pub required: bool,
}

/// 一个类的规格：类名 ⇒（格名 ⇒ 规格）。
#[derive(Debug)]
pub struct ObjectSpec {
    kinds: BTreeMap<String, BTreeMap<String, FieldSpec>>,
}

impl ObjectSpec {
    /// 从本体 JSON 文本读「每一类有哪几格」。
    ///
    /// ★ 五节缺一 ⇒ `OntologyNotLoaded`（与 `aios-ontology`／`Registry` 同口径：**本体没装载，谁都别想动**）。
    pub fn load(text: &str) -> Admit<Self> {
        let doc: Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        if aios_ontology::Ontology::load_str(text).is_err() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
        }
        let Some(objects) = doc.get("objects").and_then(Value::as_object) else {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<objects 缺>"));
        };
        let mut kinds = BTreeMap::new();
        for (kind, body) in objects {
            if kind.starts_with('_') {
                continue; // ★ `_` 键是说明／登记的缺口，不是类。
            }
            kinds.insert(kind.clone(), fields_of_class(body));
        }
        Ok(Self { kinds })
    }

    /// 类在册吗。
    #[must_use]
    pub fn has_kind(&self, kind: &str) -> bool {
        self.kinds.contains_key(kind)
    }

    /// 在册的类（升序）。
    #[must_use]
    pub fn kinds(&self) -> Vec<&str> {
        self.kinds.keys().map(String::as_str).collect()
    }

    /// 某一类的格（升序）；类不在册 ⇒ `None`。
    #[must_use]
    pub fn fields_of(&self, kind: &str) -> Option<&BTreeMap<String, FieldSpec>> {
        self.kinds.get(kind)
    }

    /// ★ 逐格校一个实例：缺必填 ⇒ `MissingField`；值类型／取值域不对 ⇒ `BadValue`；类不在册 ⇒ `UnknownKind`。
    ///
    /// ★ **本体没声明的格也拒**（Palantir 的 `Unknown property` 同位置）—— 不许偷偷多塞一格。
    pub fn check_instance(&self, reg: &Registration) -> Admit<()> {
        let Some(fields) = self.kinds.get(&reg.kind) else {
            return Err(Refuse::new(Reason::UnknownKind, reg.kind.clone()));
        };
        for (field, spec) in fields {
            if spec.required && !filled(reg, field) {
                return Err(Refuse::new(
                    Reason::MissingField {
                        field: field.clone(),
                    },
                    reg.kind.clone(),
                ));
            }
        }
        for (field, value) in &reg.fields {
            let Some(spec) = fields.get(field) else {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: field.clone(),
                        rule: "本体未声明该格".to_string(),
                    },
                    reg.kind.clone(),
                ));
            };
            if value.is_null() {
                continue; // 空值＝没填（必填已在上面判过）
            }
            if !spec.field_type.accepts(value) {
                return Err(Refuse::new(
                    Reason::BadValue {
                        field: field.clone(),
                        rule: spec.field_type.declaration(),
                    },
                    reg.kind.clone(),
                ));
            }
        }
        Ok(())
    }
}

/// 读一个类的 `fields`（格名 ⇒ 规格）＋ `_field_meta.<格>.required`。
fn fields_of_class(body: &Value) -> BTreeMap<String, FieldSpec> {
    let mut out = BTreeMap::new();
    let Some(declared) = body.get("fields").and_then(Value::as_object) else {
        return out;
    };
    let meta = body.get("_field_meta").and_then(Value::as_object);
    for (field, declaration) in declared {
        let required = meta
            .and_then(|m| m.get(field))
            .and_then(|m| m.get("required"))
            .and_then(Value::as_bool)
            .unwrap_or(false);
        out.insert(
            field.clone(),
            FieldSpec {
                field_type: FieldType::parse(declaration.as_str().unwrap_or_default()),
                required,
            },
        );
    }
    out
}

/// 这一格算不算填了（缺 或 `null` ⇒ 没填）。
fn filled(reg: &Registration, field: &str) -> bool {
    reg.get(field).is_some_and(|v| !v.is_null())
}
