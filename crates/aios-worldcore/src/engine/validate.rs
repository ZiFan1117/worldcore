//! 面③：**校验** —— 进门安检：「你交上来的东西，合不合本体定的规矩？」
//!
//! 参考 Palantir：`ObjectType.validate_value`／`validate_instance`、`Ontology.validate_ontology`。
//!
//! ★ 校六样（每样都能指回本体或本内核的一处）：
//! ① 类型名在册；② 格名合法；③ 必填齐；④ 值的类型对；⑤ 取值域对；⑥ 引用不悬空。
//!
//! ★ **真正的门**是 `spec::ObjectSpec::check_instance`（照本体 `objects.<类>.fields` **逐格**校），
//! 由面②的 `Instances::register` 调用；下面那四个 `check_*` 是**可单独调用的小件**（各校一样，
//! 别的面／别的调用点要用就取这一件 —— 门面按名字再导出，故这四个名字与签名一字不动）。
//!
//! ★ 一处**如实登记**：本体 `_field_meta.<格>.required` 今天全是 `null` ⇒ 「必填」这一样
//! **在本体上不咬**（只有显式 `true` 才算必填）。「必须有 name」是本内核自己的规矩
//! （面②的行以 name 为键），**不是**本体声明的必填 —— 两者在面②里分开判，不混成一条。

pub mod field;
pub mod spec;

use crate::core::registry::Registry;
use crate::core::types::{Admit, Reason, Refuse, Registration};

pub use field::FieldType;
pub use spec::{FieldSpec, ObjectSpec};

/// 校「形状」：① 类型名在册 ② 格名合法 ③ 名字合法。
pub fn check_shape(registry: &Registry, reg: &Registration) -> Admit<()> {
    if let Some(r) = registry.refuse_unknown_kind(&reg.kind) {
        return Err(r);
    }
    for f in reg.field_names() {
        if f.trim().is_empty() {
            return Err(Refuse::new(Reason::BadName, reg.kind.clone()));
        }
    }
    if let Some(name) = reg.get_str("name") {
        if name.trim().is_empty() || name.contains(' ') || name.contains('/') {
            return Err(Refuse::new(Reason::BadName, "name".to_string()));
        }
    }
    Ok(())
}

/// 校「必填齐」（`required` 是本体给那一类的必填格）。
pub fn check_required(reg: &Registration, required: &[&str]) -> Admit<()> {
    for r in required {
        if reg.get(r).is_none() {
            return Err(Refuse::new(
                Reason::MissingField {
                    field: (*r).to_string(),
                },
                reg.kind.clone(),
            ));
        }
    }
    Ok(())
}

/// 校「取值域」：本体里 `enum(a,b,…)` 那种格，值只能在列出的那几个里。
pub fn check_enum(reg: &Registration, field: &str, options: &[&str]) -> Admit<()> {
    let Some(v) = reg.get_str(field) else {
        return Ok(());
    };
    if options.contains(&v) {
        return Ok(());
    }
    Err(Refuse::new(
        Reason::BadValue {
            field: field.to_string(),
            rule: options.join("|"),
        },
        reg.kind.clone(),
    ))
}

/// 校「引用不悬空」：格里的值若是 `world://…` 形状，必须能在全表里找到。
pub fn check_refs(reg: &Registration, known: &[&str]) -> Admit<()> {
    for (k, v) in &reg.fields {
        let Some(s) = v.as_str() else { continue };
        if !s.starts_with("world://") {
            continue;
        }
        if !known.contains(&s) {
            return Err(Refuse::new(
                Reason::DanglingRef {
                    target: s.to_string(),
                },
                format!("{}.{}", reg.kind, k),
            ));
        }
    }
    Ok(())
}
