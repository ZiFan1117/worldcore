//! 治理面之补：**审批凭证**（T-243）。
//!
//! ★ 作者令（逐字）：「**要推送给界面，然后让人来点授权**」＋「**每次调用都带一个……凭证**」。
//!
//! ★★★ **本件最要紧的一句**：
//!   **凭证不许由「要做事的那一方」自己产生** —— ★ 否则「人审批」就变成「请求方自己盖章」，
//!   而账上还记着「有人批过」（★ 那是**假的痕迹**，比没有痕迹更坏）。
//! ★★ 结构性堵法：★ `Permit` 的**字段全私有**，★ **只有一个构造口 `by_interface`** ——
//!   调用方**造不出**一个凭证，★ 只能**拿着**界面那一路给出的那一个（★ 类型系统给的保证，不是嘱咐）。
//!   ★ 另有一半靠判据 C21 钉：★ **生产路径里只许 `engine/execute.rs` 的审批那一段调它**。
//!
//! ★ 三条属性（★ 评审席乙 方案v2 必闭3 给的）：
//!   ① **绑「动作 ＋ 参数」** ⇒ 防挪用（★ 人批「调暗 10%」，不许拿去「调亮 100%」）；
//!   ② **号进正文** ⇒ 账上记它的号（★ 不在正文里就事后改不掉被抓）；
//!   ③ **有效期 ＋ 可撤销**。

use std::collections::BTreeSet;
use std::sync::Mutex;

use crate::core::types::{Admit, IdentitySource, Reason, Refuse, Who};

/// 一张审批凭证。
///
/// ★ 字段**全私有**：★ 外面**造不出来**（★ 只能从 `by_interface` 那条路得到）。
#[derive(Debug, Clone)]
pub struct Permit {
    id: String,
    action: String,
    params_fingerprint: String,
    trace: String,
    /// 谁批的（★ 人）。
    issued_by: Who,
    /// 到什么时候作废（★ UNIX 秒）。
    expires_at: u64,
}

impl Permit {
    // ★ clippy 说参数多（8 个）—— ★ 这 8 样各自是一处来历（界面／来源／人／动作／参数指纹／因果号／号／有效期），
    //   ★ 少一样就少一条要绑的东西 ⇒ ★ 本仓**保持八个**，这里如实允过。
    #[allow(clippy::too_many_arguments)]
    /// ★★ **唯一的构造口 —— 界面那一路**。
    ///
    /// ★ 要求：① 界面自己的身份必须是**系统发的**（★ 自填 ⇒ 拒）；
    ///   ② 批的人必须是**人**（★ 本仓：名字以 `world://user` 开头 —— 与 `permissions.grants` 的 `who` 同形）。
    pub fn by_interface(
        interface: &Who,
        interface_source: IdentitySource,
        human: &Who,
        action: &str,
        params_fingerprint: &str,
        trace: &str,
        id: &str,
        expires_at: u64,
    ) -> Admit<Self> {
        if interface_source != IdentitySource::Issued {
            return Err(Refuse::new(Reason::IdentitySelfDeclared, interface.name()));
        }
        if !human.name().starts_with("world://user") {
            return Err(Refuse::new(
                Reason::NotPermitted {
                    capability: "permit.issue".to_string(),
                },
                format!("<批的人不是人：{}>", human.name()),
            ));
        }
        Ok(Self {
            id: id.to_string(),
            action: action.to_string(),
            params_fingerprint: params_fingerprint.to_string(),
            trace: trace.to_string(),
            issued_by: human.clone(),
            expires_at,
        })
    }

    /// 它的号（★ 账上要记的就是它）。
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    /// 谁批的。
    #[must_use]
    pub fn issued_by(&self) -> &Who {
        &self.issued_by
    }

    /// 绑的哪一次（因果号）。
    #[must_use]
    pub fn trace(&self) -> &str {
        &self.trace
    }

    /// ★ 过期了没有。
    #[must_use]
    pub fn is_expired(&self, now: u64) -> bool {
        now > self.expires_at
    }

    /// ★★ **它罩得住这一次调用吗**（★ ① 绑动作 ＋ 参数）。
    #[must_use]
    pub fn covers(&self, action: &str, params_fingerprint: &str) -> bool {
        self.action == action && self.params_fingerprint == params_fingerprint
    }
}

/// ★ 参数指纹：★ 键名升序 ＋ 带长度压平（★ 与账的封条同法 —— 不带长度就能伪造出同一串）。
#[must_use]
pub fn fingerprint_params(params: &serde_json::Map<String, serde_json::Value>) -> String {
    let mut keys: Vec<&String> = params.keys().collect();
    keys.sort_unstable();
    let mut buf = String::new();
    for k in keys {
        let v = params.get(k).map_or_else(String::new, |v| v.to_string());
        buf.push_str(&format!("{}:{}|{}:{}|", k.len(), k, v.len(), v));
    }
    buf
}

/// ★ 用过的凭证号（★ ② **一号一用**）。
#[derive(Debug, Default)]
pub struct PermitBook {
    used: Mutex<BTreeSet<String>>,
}

impl PermitBook {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// ★ 用掉一张：★ 过期 ⇒ 拒；★ 已经用过 ⇒ 拒（★ 一号一用）。
    pub fn consume(
        &self,
        permit: &Permit,
        action: &str,
        params_fingerprint: &str,
        now: u64,
    ) -> Admit<()> {
        if permit.is_expired(now) {
            return Err(Refuse::new(
                Reason::NotPermitted {
                    capability: action.to_string(),
                },
                "<凭证已过期>",
            ));
        }
        if !permit.covers(action, params_fingerprint) {
            return Err(Refuse::new(
                Reason::NotPermitted {
                    capability: action.to_string(),
                },
                "<凭证绑的是另一次调用（★ 不许挪用）>",
            ));
        }
        let mut used = self.used.lock().expect("锁没坏");
        if !used.insert(permit.id().to_string()) {
            return Err(Refuse::new(
                Reason::NotPermitted {
                    capability: action.to_string(),
                },
                "<这张凭证已经用过（★ 一号一用）>",
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn iface() -> Who {
        Who::new("world://interface/a2ui")
    }
    fn human() -> Who {
        Who::new("world://user/zhang")
    }
    fn params(pairs: &[(&str, serde_json::Value)]) -> serde_json::Map<String, serde_json::Value> {
        let mut m = serde_json::Map::new();
        for (k, v) in pairs {
            m.insert(String::from(*k), v.clone());
        }
        m
    }

    fn permit(action: &str, fp: &str) -> Permit {
        Permit::by_interface(
            &iface(),
            IdentitySource::Issued,
            &human(),
            action,
            fp,
            "trace-1",
            "p-1",
            1_000,
        )
        .expect("界面那一路该造得出来")
    }

    #[test]
    fn a_self_declared_interface_cannot_issue() {
        let got = Permit::by_interface(
            &iface(),
            IdentitySource::SelfDeclared,
            &human(),
            "device.x",
            "fp",
            "t",
            "p-9",
            1_000,
        );
        assert!(got.is_err(), "★ 自填身份的界面 ⇒ 不许发凭证");
    }

    #[test]
    fn a_machine_cannot_be_the_one_who_approved() {
        let bot = Who::new("world://agent/dsh");
        let got = Permit::by_interface(
            &iface(),
            IdentitySource::Issued,
            &bot,
            "device.x",
            "fp",
            "t",
            "p-8",
            1_000,
        );
        assert!(got.is_err(), "★ 批的人必须是人（机器不许代签 —— 硬约束 6）");
    }

    #[test]
    fn a_permit_cannot_be_repurposed() {
        let dim = fingerprint_params(&params(&[("percent", json!(10))]));
        let bright = fingerprint_params(&params(&[("percent", json!(100))]));
        let p = permit("device.brightness.set", &dim);
        let book = PermitBook::new();
        assert!(
            book.consume(&p, "device.brightness.set", &bright, 1)
                .is_err(),
            "★ 人批「调暗 10%」不许拿去「调亮 100%」"
        );
        assert!(
            book.consume(&p, "device.brightness.set", &dim, 1).is_ok(),
            "★ 绑的那一次该罩得住"
        );
    }

    #[test]
    fn a_permit_is_single_use_and_expires() {
        let fp = fingerprint_params(&params(&[("percent", json!(10))]));
        let p = permit("device.brightness.set", &fp);
        let book = PermitBook::new();
        assert!(
            book.consume(&p, "device.brightness.set", &fp, 1).is_ok(),
            "第一次该成"
        );
        assert!(
            book.consume(&p, "device.brightness.set", &fp, 2).is_err(),
            "★ 一号一用：第二次必须拒"
        );
        let p2 = permit("device.brightness.set", &fp);
        let book2 = PermitBook::new();
        assert!(
            book2
                .consume(&p2, "device.brightness.set", &fp, 9_999)
                .is_err(),
            "★ 过期必须拒"
        );
    }
}
