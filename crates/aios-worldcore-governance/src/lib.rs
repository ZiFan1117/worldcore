//! 面⑧：**治理** —— 谁能看、谁能改、谁能做。
//!
//! 参考 Palantir：`governance/permissions.py` 的 `can_read`／`can_write`／`can_execute`、
//! `governance/roles.py` 的 `Role`／`User`，以及 `markings.py` 的 `Marking`。
//!
//! ★ 本体的两节就是它：`permissions`（谁能把某个能力授给谁）＋ `governance`（角色与标记）。

use std::collections::{BTreeMap, BTreeSet};

use aios_worldcore_shared::{Admit, Reason, Refuse, Who};

/// 治理表：谁是什么角色 ＋ 谁能用什么能力。
#[derive(Debug, Default)]
pub struct Governance {
    role_of: BTreeMap<String, BTreeSet<String>>,
    grants: BTreeMap<String, BTreeSet<String>>,
}

impl Governance {
    /// 空表。
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// 给谁一个角色。
    pub fn assign_role(&mut self, who: &Who, role: impl Into<String>) {
        self.role_of
            .entry(who.name().to_string())
            .or_default()
            .insert(role.into());
    }

    /// 把某个能力授给谁。
    pub fn grant(&mut self, who: &Who, capability: impl Into<String>) {
        self.grants
            .entry(who.name().to_string())
            .or_default()
            .insert(capability.into());
    }

    /// 他有没有这个角色。
    #[must_use]
    pub fn has_role(&self, who: &Who, role: &str) -> bool {
        self.role_of
            .get(who.name())
            .is_some_and(|s| s.contains(role))
    }

    /// ★ 能不能做（本内核口径：**默认拒** —— 没授过的能力一律不许）。
    pub fn can_execute(&self, who: &Who, capability: &str) -> Admit<()> {
        if self
            .grants
            .get(who.name())
            .is_some_and(|s| s.contains(capability))
        {
            return Ok(());
        }
        Err(Refuse::new(
            Reason::NotPermitted {
                capability: capability.to_string(),
            },
            who.name().to_string(),
        ))
    }

    /// 能不能读（今天与 `can_execute` 同口径；标记面将来再细分）。
    pub fn can_read(&self, who: &Who, capability: &str) -> Admit<()> {
        self.can_execute(who, capability)
    }

    /// 能不能写（同上）。
    pub fn can_write(&self, who: &Who, capability: &str) -> Admit<()> {
        self.can_execute(who, capability)
    }
}
