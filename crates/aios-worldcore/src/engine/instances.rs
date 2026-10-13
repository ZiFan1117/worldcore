//! 面②：**实例注册** —— 把「具体的东西」登记进世界。
//!
//! 参考 Palantir：`engine/object_store.py` 的 `ObjectStore.create`
//! （★ 它的次序：类型名不在 ⇒ 拒 → `validate_instance` 逐格校 → 才落表）。
//!
//! ★ 作者令（逐字）：「软件安装啥的，这个注册，包括那个刚才说的**界面啥的那些东西都要注册，必须注册**。」
//! ⇒ 本面硬规矩：**未在册的类型 ⇒ 拒**（★ 不是静默收下，也不是偷偷当别的类）。
//!
//! ★ 2026-10-13 接线三条（本面从「只查类型名」进到「真闸」）：
//! ① **先问治理**：`Governance::can_execute(who, "<类>.register")`，没授过 ⇒ `NotPermitted`（默认拒）；
//! ② **照本体逐格校**：`ObjectSpec::check_instance`（缺必填／值类型／取值域 ⇒ 拒）；
//! ③ **登记成功同批记一笔账**：族 `change`／`what` `<类>.register`／参数带 `name`（序号由账发）。
//! ★ 三条都在**落表之前**：被拒的登记**不长在册上、也不留账**。
//!
//! ★ 一处**如实登记**：本体的 `interfaces`（能力表）里今天**没有** `register` 这一类能力
//! （现取只有 `notice.*`／`job.*`／`ledger.compact`／`world.rekey`／`world.migrate`／`presence.report`）。
//! 本内核把「登记某类实例」当成一项**由类名派生**的能力（`<类>.register`）交给治理面查 ——
//! 派生自本体的类名，**不是**自由字符串。

use std::collections::BTreeMap;

use aios_worldcore_governance::Governance;
use aios_worldcore_ledger::Ledger;
use crate::core::registry::Registry;
use crate::core::types::{Admit, EventSeq, Reason, Refuse, Registration, Who};
use aios_worldcore_validate::{check_shape, ObjectSpec};

/// ★ 登记某类实例所需的能力名：`<类>.register`。
#[must_use]
pub fn register_capability(kind: &str) -> String {
    format!("{kind}.register")
}

/// 一次登记要用的四个协作面：册（面①）／本体格（面③）／治理（面⑧）／账（面⑥）。
pub struct RegisterEnv<'a> {
    /// 本体里有哪些类型（面①）。
    pub registry: &'a Registry,
    /// 本体里每一类有哪几格（面③）。
    pub spec: &'a ObjectSpec,
    /// 谁能做（面⑧）。
    pub governance: &'a Governance,
    /// 只追加的账（面⑥）。
    pub ledger: &'a mut Ledger,
}

impl<'a> RegisterEnv<'a> {
    /// 凑齐四个协作面。
    #[must_use]
    pub fn new(
        registry: &'a Registry,
        spec: &'a ObjectSpec,
        governance: &'a Governance,
        ledger: &'a mut Ledger,
    ) -> Self {
        Self {
            registry,
            spec,
            governance,
            ledger,
        }
    }
}

/// 已登记的实例：键 ⇒（类型名，各格）。
#[derive(Debug, Default)]
pub struct Instances {
    rows: BTreeMap<String, (String, serde_json::Map<String, serde_json::Value>)>,
}

impl Instances {
    /// 空的实例表。
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// ★★ 注册一个实例。五条规矩，逐条可验（★ 前四条都在落表之前）：
    ///
    /// 1. **治理先问**（默认拒）：`<类>.register` 没授过 ⇒ `NotPermitted`；
    /// 2. **类型名在册**（查 `Registry`）⇒ 不在册 ⇒ `UnknownKind`；
    /// 3. **照本体逐格校**：缺必填 ⇒ `MissingField`；值类型／取值域不对 ⇒ `BadValue`；
    ///    本体没声明的格也拒（不许偷偷多塞一格）；
    /// 4. **本内核最小指认格**：行以 `name` 为键 ⇒ 缺 ⇒ `MissingField{name}`；同名不许重复（更新走面④）；
    /// 5. **成功 ⇒ 同批记一笔账**，返回**账上的序号**（族 `change`／`what` `<类>.register`）。
    pub fn register(
        &mut self,
        env: &mut RegisterEnv<'_>,
        who: &Who,
        reg: &Registration,
    ) -> Admit<EventSeq> {
        // ① 先问治理：没授过就不许做（★ 先问人，再问册 —— 未登记的类型也给这一条）。
        let capability = register_capability(&reg.kind);
        env.governance.can_execute(who, &capability)?;
        // ② 类型名在册 ＋ 格名／名字形状（借面③的小件，不另抄一份）。
        check_shape(env.registry, reg)?;
        // ③ 照本体 `objects.<类>.fields` 逐格校。
        env.spec.check_instance(reg)?;
        // ④ 本内核最小指认格：缺（或不是字符串）⇒ MissingField{name}。
        let name = reg.get_str("name").ok_or_else(|| {
            Refuse::new(
                Reason::MissingField {
                    field: "name".to_string(),
                },
                reg.kind.clone(),
            )
        })?;
        let key = format!("{}:{}", reg.kind, name);
        if self.rows.contains_key(&key) {
            return Err(Refuse::new(Reason::DanglingRef { target: key }, "同名实例已存在"));
        }
        // ⑤ 落表 ＋ 同批记一笔账（★ 返回的序号＝账上的位置）。
        self.rows.insert(key, (reg.kind.clone(), reg.fields.clone()));
        let mut params = serde_json::Map::new();
        params.insert("name".to_string(), serde_json::Value::String(name.to_string()));
        Ok(env.ledger.append(who, "change", format!("{}.register", reg.kind), params))
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
