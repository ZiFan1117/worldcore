//! 面②：**实例注册** —— 把「具体的东西」登记进世界。
//!
//! 参考 Palantir：`engine/object_store.py` 的 `ObjectStore.create`（类型名 ＋ 各格 ⇒ 一条实例）。
//!
//! ★ 作者令（逐字）：「软件安装啥的，这个注册，包括那个刚才说的**界面啥的那些东西都要注册，必须注册**。」
//! ⇒ 本面硬规矩：**未在册的类型 ⇒ 拒**（★ 不是静默收下，也不是偷偷当别的类）。

use std::collections::BTreeMap;

use aios_worldcore_registry::Registry;
use aios_worldcore_shared::{Admit, EventSeq, Reason, Refuse, Registration, Who};

/// 已登记的实例：键 ⇒（类型名，各格）。
#[derive(Debug, Default)]
pub struct Instances {
    rows: BTreeMap<String, (String, serde_json::Map<String, serde_json::Value>)>,
    next_seq: u64,
}

impl Instances {
    /// 空的实例表。
    #[must_use]
    pub fn new() -> Self {
        Self {
            rows: BTreeMap::new(),
            next_seq: 1,
        }
    }

    /// ★★ 注册一个实例。三条规矩，逐条可验：
    ///
    /// 1. **类型名必须在册**（查 `Registry`）⇒ 不在册 ⇒ `UnknownKind`；
    /// 2. **必须有名字**（本内核的最小指认格）⇒ 缺 ⇒ `MissingField{name}`；
    /// 3. **同名不许重复**（更新走面④）。
    pub fn register(
        &mut self,
        registry: &Registry,
        who: &Who,
        reg: &Registration,
    ) -> Admit<EventSeq> {
        if let Some(r) = registry.refuse_unknown_kind(&reg.kind) {
            return Err(r);
        }
        let name = reg.get_str("name").ok_or_else(|| {
            Refuse::new(
                Reason::MissingField {
                    field: "name".to_string(),
                },
                reg.kind.clone(),
            )
        })?;
        if name.trim().is_empty() {
            return Err(Refuse::new(Reason::BadName, reg.kind.clone()));
        }
        let key = format!("{}:{}", reg.kind, name);
        if self.rows.contains_key(&key) {
            return Err(Refuse::new(
                Reason::DanglingRef { target: key },
                "同名实例已存在",
            ));
        }
        self.rows
            .insert(key, (reg.kind.clone(), reg.fields.clone()));
        let seq = EventSeq(self.next_seq);
        self.next_seq += 1;
        let _ = who; // ★ 谁登记的：面⑥会把它写进账（本面只发序号）
        Ok(seq)
    }

    /// 在册的实例数。
    #[must_use]
    pub fn count(&self) -> usize {
        self.rows.len()
    }

    /// 按名字取（名字在本内核里是唯一指认格）。
    #[must_use]
    pub fn get(&self, name: &str) -> Option<(&str, &serde_json::Map<String, serde_json::Value>)> {
        self.rows
            .values()
            .find(|(_, f)| f.get("name").and_then(serde_json::Value::as_str) == Some(name))
            .map(|(k, f)| (k.as_str(), f))
    }

    /// 在册的全部键（升序）。
    #[must_use]
    pub fn keys(&self) -> Vec<&str> {
        self.rows.keys().map(String::as_str).collect()
    }
}
