//! 面⑧：**治理** —— 谁能看、谁能改、谁能做。
//!
//! ★ 干活口径学 AIOS 的策略核（crates/aios-policy：pipeline.rs 的十二步决策流水线、
//! kernel.rs 的那个默认内存策略核、decision.rs 的决策记录）—— **学它怎么组织这件事，
//! 不用它的名字**。三条：① **闭阶梯、逐步短路**（它的 PipelineState 只有 Continue 与
//! ShortCircuit 两个值，没有第三种）；② **地板默认拒**（它 S2.3 §11 —— 没有更早的一级
//! 定下结论时**一定**产出默认拒；本仓对应本体 permissions.default 逐字 deny）；
//! ③ **每答必留痕**（每次评估产出一条记录，带理由码与哪一级定的）。
//!
//! ★ 本仓的名字与格：阶梯三级 ＝ **运行时授过**（grant）／**出厂法条命中**
//! （permissions.grants.<能力>.scope）／**地板**（permissions.default）；
//! 角色读 governance.roles.subject_to_role。
//!
//! ★ 两处**如实登记**（不许读成「已经安全了」）：① 本体 governance.read_allow 的 default 是
//! allow，本件**不按它判读** —— 本体自己写着那一格「今天没有任何读闸……它是**缺口**，不是
//! **决定**」⇒ 照它判等于把缺口读成决定；本内核今天 can_read 与 can_execute **同阶梯**。
//! ② 本体 permissions.grants.<能力>.who（「谁能授给谁」）本件**不读** —— 本体 _declared_gaps ①
//! 登记它「无读者」；我们**不发明**第二个读法（同一事实不许长出两处真相）。
//!
//! ★【条文命中口径】见 hits。★ 现取：本仓 crates 下**没有**上游那句 gate::pattern_matches
//! 的实件（0 命中）⇒ 不许声称与它同口径。

use std::collections::{BTreeMap, BTreeSet};
use std::sync::Mutex;

use crate::core::types::{Admit, Reason, Refuse, Who};

/// 许可阶梯上的一级（★ 闭集：要加一级得改法，不是加个字符串）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Step {
    /// ① 运行时授过（逐主体、逐能力，精确）。
    Granted,
    /// ② 出厂法条命中（permissions.grants.<能力>.scope 里的主体条文）。
    Declared,
    /// ③ 地板：法条没授过的一律拒（permissions.default 逐字 deny）。
    Floor,
}

/// 一条**裁定**（谁／哪一项能力／放行吗／哪一级定的／理由码）—— 学它「每次评估必产出决策」。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ruling {
    pub who: String,
    pub capability: String,
    pub allowed: bool,
    pub step: Step,
    pub code: &'static str,
}

/// 治理面：角色表 ＋ 运行时授权表 ＋ 出厂法条 ＋ 只追加的裁定台账。
#[derive(Debug, Default)]
pub struct Governance {
    role_of: BTreeMap<String, BTreeSet<String>>,
    grants: BTreeMap<String, BTreeSet<String>>,
    law: BTreeMap<String, Vec<String>>,
    rulings: Mutex<Vec<Ruling>>,
}

impl Governance {
    /// 空治理面（只有运行时 grant；本体那本出厂法条要用 from_ontology 装）。
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// ★ 装**出厂法条**（本体文本）：① permissions.default **必须显式**写 deny（缺或别的词
    /// ⇒ 拒 —— 本体 _default_closed 逐字：「默认允许不是安全默认，是法律没写全」）；
    /// ② permissions.grants.<能力>.scope ⇒ 第二级；③ governance.roles ⇒ 角色表。
    pub fn from_ontology(text: &str) -> Admit<Self> {
        let doc: serde_json::Value = serde_json::from_str(text)
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, "<不是合法 JSON>"))?;
        if aios_ontology::Ontology::load_str(text).is_err() {
            return Err(Refuse::new(Reason::OntologyNotLoaded, "<五节缺一>"));
        }
        let default = doc
            .pointer("/permissions/default")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("<缺>");
        if default != "deny" {
            let rule = Reason::BadValue {
                field: "permissions.default".to_string(),
                rule: "deny".to_string(),
            };
            return Err(Refuse::new(rule, default.to_string()));
        }
        let law = read_law(&doc);
        Ok(Self {
            role_of: read_roles(&doc),
            grants: BTreeMap::new(),
            law,
            rulings: Mutex::new(Vec::new()),
        })
    }

    /// 给谁一个角色。
    pub fn assign_role(&mut self, who: &Who, role: impl Into<String>) {
        self.role_of
            .entry(who.name().to_string())
            .or_default()
            .insert(role.into());
    }

    /// 把某个能力授给谁（运行时那一级，精确）。
    pub fn grant(&mut self, who: &Who, capability: impl Into<String>) {
        self.grants
            .entry(who.name().to_string())
            .or_default()
            .insert(capability.into());
    }

    /// 他有没有这个角色（运行时 assign_role 与出厂 roster 一起认，条文命中同一口径）。
    #[must_use]
    pub fn has_role(&self, who: &Who, role: &str) -> bool {
        self.role_of
            .iter()
            .any(|(holder, roles)| hits(holder, who.name()) && roles.contains(role))
    }

    /// ★ 能不能做 —— 走阶梯：① 运行时授过 ⇒ 放行；② 出厂法条命中 ⇒ 放行；③ 地板 ⇒ 默认拒。
    /// **每答必留一条裁定**（放行与拒绝都留）。
    pub fn can_execute(&self, who: &Who, capability: &str) -> Admit<()> {
        let name = who.name();
        if self
            .grants
            .get(name)
            .is_some_and(|s| s.contains(capability))
        {
            self.note(
                who,
                capability,
                true,
                Step::Granted,
                "worldcore.Allow.Granted",
            );
            return Ok(());
        }
        let declared = self
            .law
            .get(capability)
            .is_some_and(|pats| pats.iter().any(|p| hits(p, name)));
        if declared {
            self.note(
                who,
                capability,
                true,
                Step::Declared,
                "worldcore.Allow.Declared",
            );
            return Ok(());
        }
        let refused = Refuse::new(
            Reason::NotPermitted {
                capability: capability.to_string(),
            },
            name.to_string(),
        );
        self.note(who, capability, false, Step::Floor, refused.code());
        Err(refused)
    }

    /// 能不能读 —— ★ 今天与 can_execute **同阶梯**（read_allow 那一格未落地，见件头）。
    pub fn can_read(&self, who: &Who, capability: &str) -> Admit<()> {
        self.can_execute(who, capability)
    }

    /// 能不能写 —— 同上。
    pub fn can_write(&self, who: &Who, capability: &str) -> Admit<()> {
        self.can_execute(who, capability)
    }

    /// 裁定台账（只追加；按序）。
    #[must_use]
    pub fn rulings(&self) -> Vec<Ruling> {
        self.rulings
            .lock()
            .map(|log| log.clone())
            .unwrap_or_default()
    }

    /// 记一条裁定。★ 台账是**读数**、不是裁定本身：锁坏了也只少一条痕，不许因此改结论。
    fn note(&self, who: &Who, capability: &str, allowed: bool, step: Step, code: &'static str) {
        if let Ok(mut log) = self.rulings.lock() {
            log.push(Ruling {
                who: who.name().to_string(),
                capability: capability.to_string(),
                allowed,
                step,
                code,
            });
        }
    }
}

/// 读 permissions.grants.<能力>.scope（略过 _ 开头的键）；空 scope 不进阶梯。
fn read_law(doc: &serde_json::Value) -> BTreeMap<String, Vec<String>> {
    let mut law = BTreeMap::new();
    let Some(map) = doc
        .pointer("/permissions/grants")
        .and_then(serde_json::Value::as_object)
    else {
        return law;
    };
    for (cap, body) in map {
        if cap.starts_with('_') {
            continue;
        }
        let arr = body.pointer("/scope").and_then(serde_json::Value::as_array);
        let scope: Vec<String> = arr.map_or_else(Vec::new, |a| a.iter().map(to_text).collect());
        if !scope.is_empty() {
            law.insert(cap.clone(), scope);
        }
    }
    law
}

/// 值是字符串 ⇒ 它的文本；不是 ⇒ 空（★ 空条文不进阶梯，见 read_law）。
fn to_text(value: &serde_json::Value) -> String {
    value.as_str().unwrap_or_default().to_string()
}

/// 读 governance.roles.subject_to_role（主体 → 角色）。
fn read_roles(doc: &serde_json::Value) -> BTreeMap<String, BTreeSet<String>> {
    let mut roles: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let path = "/governance/roles/subject_to_role";
    let Some(map) = doc.pointer(path).and_then(serde_json::Value::as_object) else {
        return roles;
    };
    for (holder, role) in map {
        if holder.starts_with('_') {
            continue;
        }
        if let Some(name) = role.as_str() {
            roles
                .entry(holder.clone())
                .or_default()
                .insert(name.to_string());
        }
    }
    roles
}

/// 【条文命中口径】见件头。★ 三个分支的顺序是死的（先精确，再通配，最后地址段前缀）。
fn hits(declared: &str, subject: &str) -> bool {
    if declared == subject {
        return true;
    }
    if let Some(head) = declared.strip_suffix('*') {
        return subject.starts_with(head);
    }
    subject.starts_with(declared) && subject.as_bytes().get(declared.len()) == Some(&b'/')
}

#[cfg(test)]
mod tests;
