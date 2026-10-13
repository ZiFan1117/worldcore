//! 面②：**实例注册** —— 把「具体的东西」登记进世界。
//!
//! 参考 Palantir：engine/object_store.py 的 ObjectStore.create
//! （★ 它的次序：类型名不在 ⇒ 拒 → validate_instance 逐格校 → 才落表）。
//!
//! ★ 干活口径另学上游那套对象模型（只学怎么干活；名字／类型全是我们的）：
//! ① 它把在册的东西摊在**按命名空间分层的目录**里，而不是一条线性的表 ⇒ 我们落成
//!    **主目录**（全键升序）＋**名字目录**（名字 ⇒ 全键）＋**类目录**（类 ⇒ 该类的键）；
//! ② 它的每一道拒都在**动目录之前**（先核在册／父版本，才写状态）⇒ 被拒的登记
//!    不长在册上、也不留账。
//!
//! ★ 作者令（逐字）：「软件安装啥的，这个注册，包括那个刚才说的**界面啥的那些东西都要注册，
//! 必须注册**。」⇒ 本面硬规矩：**未在册的类型 ⇒ 拒**（★ 不是静默收下，也不是偷偷当别的类）。
//!
//! ★ 2026-10-13 接线四条（本面从「只查类型名」进到「真闸」）：
//! ① **先问治理**：Governance::can_execute(who, "<类>.register")，没授过 ⇒ NotPermitted（默认拒）；
//! ② **照本体逐格校**：ObjectSpec::check_instance（缺必填／值类型／取值域 ⇒ 拒）；
//! ③ **本体口径的唯一性**：ObjectSpec::instance_mode == "one" 的类**已有一个 ⇒ 第二个 ⇒ 拒**
//!    （Reason::OverInstanceLimit{limit:1}；"many" 不限）；
//! ④ **登记成功同批记一笔账**：族 change／what <类>.register／参数带 name（序号由账发）。
//! ★ 四条都在**落表之前**：被拒的登记**不长在册上、也不留账**。
//!
//! ★ 一处**如实登记**：本体的 interfaces（能力表）里今天**没有** register 这一类能力
//! （现取只有 notice.*／job.*／ledger.compact／world.rekey／world.migrate／presence.report）。
//! 本内核把「登记某类实例」当成一项**由类名派生**的能力（<类>.register）交给治理面查 ——
//! 派生自本体的类名，**不是**自由字符串。
//!
//! ★ 另一处**如实登记（缺口，接不上）**：本体说 ledger 是唯一的类（objects.ledger.instance_mode=one），
//! 可**本体没给 ledger 声明 name 格**（现取 fields = path／compaction_seq／entries_total／retract_seq），
//! 而本内核的行以 name 为键 ⇒ 第一个 ledger 就进不去（带 name ⇒ BadValue{name}；不带 ⇒ MissingField{name}）
//! ⇒ 「唯一性」这条闸在**真本体的 ledger 上今天咬不到**（闸本身已可证，见 instances/tests.rs）。
//!
//! ★ 这一处将来接 **AIOS 的**哪几件（★ 作者令：P 管语义形状，AIOS 最新代码管 OS 的真实现）：
//! · 「装了啥」→ 能力适配器在册表；
//! · 「哪台设备／哪块界面」→ 硬件面与渲染面的 surface 注册；
//! · 本件今天**只做内存实现**（三张目录），落盘由面④ store 与面⑥ ledger 担。

use std::collections::{BTreeMap, BTreeSet};

use crate::core::registry::Registry;
use crate::core::types::{Admit, EventSeq, Reason, Refuse, Registration, Who};
use crate::engine::ledger::Ledger;
use crate::engine::validate::{check_shape, ObjectSpec};
use crate::governance::Governance;

/// ★ 登记某类实例所需的能力名：<类>.register。
#[must_use]
pub fn register_capability(kind: &str) -> String {
    format!("{kind}.register")
}

/// 一次登记要用的四个协作面：册（面①）／本体格（面③）／治理（面⑧）／账（面⑥）。
///
/// ★ 为什么要把四件凑成一件交给 register：★ 作者令「登记前**先问治理**」「成功要**同批记账**」
/// ⇒ 这两件**不能在调用点各自记着**，必须**从登记口自己身上**过一遍（否则就是可绕过的旁路）。
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

/// 一条在册实例：它是哪一类 ＋ 填了哪些格。
#[derive(Debug, Clone, PartialEq)]
struct Instance {
    kind: String,
    fields: serde_json::Map<String, serde_json::Value>,
}

/// 已登记的实例：**主目录**（全键升序）＋ **名字目录**（名字 ⇒ 全键）＋ **类目录**（类 ⇒ 键，升序）。
#[derive(Debug, Default)]
pub struct Instances {
    rows: BTreeMap<String, Instance>,
    by_name: BTreeMap<String, String>,
    by_kind: BTreeMap<String, BTreeSet<String>>,
}

impl Instances {
    /// 空的实例表。
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// ★★ 注册一个实例。六条规矩，逐条可验（★ 前五条都在落表之前）：
    ///
    /// 1. **治理先问**（默认拒）：<类>.register 没授过 ⇒ NotPermitted；
    /// 2. **类型名在册**（查 Registry）⇒ 不在册 ⇒ UnknownKind；
    /// 3. **照本体逐格校**：缺必填 ⇒ MissingField；值类型／取值域不对 ⇒ BadValue；
    ///    本体没声明的格也拒（不许偷偷多塞一格）；
    /// 4. **本体口径的唯一性**：instance_mode == "one" 的类已有一个 ⇒ OverInstanceLimit{1}；
    /// 5. **本内核最小指认格**：行以 name 为键 ⇒ 缺 ⇒ MissingField{name}；同名不许重复（更新走面④）；
    /// 6. **成功 ⇒ 同批记一笔账**（★ 只要族不在册，账先拒 ⇒ 册上就没有这一行），
    ///    返回**账上的序号**（族 change／what <类>.register）。
    ///
    /// ★ 落表时**同批**改名字目录与类目录（否则查名／按类数就查不到这一条）。
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
        // ③ 照本体 objects.<类>.fields 逐格校。
        env.spec.check_instance(reg)?;
        // ④ 本体口径的唯一性：one 的类已有一个 ⇒ 拒（★ 与类名无关的通用闸，读的是本体的 mode）。
        self.check_instance_mode(env.spec, &reg.kind)?;
        // ⑤ 本内核最小指认格：缺（或不是字符串）⇒ MissingField{name}。
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
            return Err(Refuse::new(
                Reason::DanglingRef { target: key },
                "同名实例已存在",
            ));
        }
        // ⑥ **先记账、再落表**：★ 账要是拒了这一笔（族不在册），册上就不许留痕。
        //    返回的序号＝账上的位置（★ 本体 envelope.fields.seq 逐字：序号由世界发）。
        let mut params = serde_json::Map::new();
        params.insert(
            "name".to_string(),
            serde_json::Value::String(name.to_string()),
        );
        let seq = env
            .ledger
            .append(who, "change", format!("{}.register", reg.kind), params)?;
        self.rows.insert(
            key.clone(),
            Instance {
                kind: reg.kind.clone(),
                fields: reg.fields.clone(),
            },
        );
        self.point_name(name, &key);
        self.by_kind
            .entry(reg.kind.clone())
            .or_default()
            .insert(key);
        Ok(seq)
    }

    /// 在册的实例数。
    #[must_use]
    pub fn count(&self) -> usize {
        self.rows.len()
    }

    /// 按名字取（名字在本内核里是唯一指认格）。
    ///
    /// ★ 走**名字目录**（不再全表扫）；目录里记的是**全键序最小**的那一条 ——
    ///   同名跨类时先给谁由全键序定，不由登记先后定（与旧口径逐字一致）。
    #[must_use]
    pub fn get(&self, name: &str) -> Option<(&str, &serde_json::Map<String, serde_json::Value>)> {
        let key = self.by_name.get(name)?;
        let instance = self.rows.get(key)?;
        Some((instance.kind.as_str(), &instance.fields))
    }

    /// 在册的全部键（升序）。
    #[must_use]
    pub fn keys(&self) -> Vec<&str> {
        self.rows.keys().map(String::as_str).collect()
    }

    /// 某类已有几条在册（走类目录，不全表扫）。
    fn count_of_kind(&self, kind: &str) -> usize {
        self.by_kind.get(kind).map_or(0, |keys| keys.len())
    }

    /// ★ 本体口径的唯一性闸：instance_mode == "one" 的类**已有一个 ⇒ 拒**。
    ///
    /// ★ 本体没写 mode（None）＝ **不限**（不替本体发明规矩）。
    fn check_instance_mode(&self, spec: &ObjectSpec, kind: &str) -> Admit<()> {
        if spec.instance_mode(kind) == Some("one") && self.count_of_kind(kind) > 0 {
            return Err(Refuse::new(
                Reason::OverInstanceLimit { limit: 1 },
                kind.to_string(),
            ));
        }
        Ok(())
    }

    /// 名字目录：记**全键序最小**的那一条（旧口径是「全表扫，取键序第一条」）。
    fn point_name(&mut self, name: &str, key: &str) {
        let keep = self
            .by_name
            .get(name)
            .is_some_and(|seen| seen.as_str() <= key);
        if !keep {
            self.by_name.insert(name.to_string(), key.to_string());
        }
    }
}

#[cfg(test)]
mod mode_tests;
#[cfg(test)]
mod tests;
