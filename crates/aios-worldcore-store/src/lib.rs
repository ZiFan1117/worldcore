//! 面④：**实例存储** —— 存下来、取得出、能改、能删。
//!
//! 参考 Palantir：`engine/object_store.py` 的 `create`／`get`／`update`／`delete`／`search`／`count`。
//!
//! ★ 本面只管「存」；**在不在册**由面②（注册）与面③（校验）把关（本面不重复判）。

use std::collections::BTreeMap;

use aios_worldcore_shared::{Admit, Reason, Refuse, Registration};

/// 一份存储：键 ⇒ 记录。
#[derive(Debug, Default)]
pub struct Store {
    rows: BTreeMap<String, Registration>,
}

impl Store {
    /// 空存储。
    #[must_use]
    pub fn new() -> Self {
        Self {
            rows: BTreeMap::new(),
        }
    }

    /// 存一条（键通常＝`类型:名字`）。键已存在 ⇒ 拒。
    pub fn create(&mut self, key: impl Into<String>, reg: Registration) -> Admit<()> {
        let key = key.into();
        if self.rows.contains_key(&key) {
            return Err(Refuse::new(Reason::DanglingRef { target: key }, "键已存在"));
        }
        self.rows.insert(key, reg);
        Ok(())
    }

    /// 取一条。
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&Registration> {
        self.rows.get(key)
    }

    /// 改一条（不存在 ⇒ 拒）。
    pub fn update(&mut self, key: &str, reg: Registration) -> Admit<()> {
        if !self.rows.contains_key(key) {
            return Err(Refuse::new(
                Reason::DanglingRef {
                    target: key.to_string(),
                },
                "键不存在",
            ));
        }
        self.rows.insert(key.to_string(), reg);
        Ok(())
    }

    /// 删一条（不存在 ⇒ 拒）。
    pub fn delete(&mut self, key: &str) -> Admit<()> {
        self.rows.remove(key).map(|_| ()).ok_or_else(|| {
            Refuse::new(
                Reason::DanglingRef {
                    target: key.to_string(),
                },
                "键不存在",
            )
        })
    }

    /// 按类型名找（升序键）。
    #[must_use]
    pub fn search_by_kind(&self, kind: &str) -> Vec<&str> {
        self.rows
            .iter()
            .filter(|(_, r)| r.kind == kind)
            .map(|(k, _)| k.as_str())
            .collect()
    }

    /// 全部键（升序）。
    #[must_use]
    pub fn keys(&self) -> Vec<&str> {
        self.rows.keys().map(String::as_str).collect()
    }

    /// 一共几条。
    #[must_use]
    pub fn count(&self) -> usize {
        self.rows.len()
    }
}
