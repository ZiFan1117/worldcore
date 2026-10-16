//! 面①之补：**注册面** —— 软件把它的动作交上来（T-243）。
//!
//! ★ 作者令（逐字）：「**一个软件注册进来以后，它的 action 呀，这些都应该都注册进来的**」；
//!   「**注册是直接注册，上一次就不用注册了**」⇒ ★ **一次性的、持久的**。
//!
//! ★★ **本面为什么落在【一份注册表文件】而不是去改那份 11259 行的本体 JSON**：
//!   · 本体是**权威**（谁都不许自带清单）—— 本面**不改它**；
//!   · 注册表是**登记结果**（★ 不注册＝不存在）：本体里那 9 条 ＋ 注册表里的 N 条 ⇒ **合成一张在册表**；
//!   · ★ 且这样**不会每次都改本体**（★ 评审席乙 必闭5 点过：往本体里插条目会让 `C12` 的行号**每次注册都漂**）。
//!
//! ★ 四件规矩（★ 作者裁的）：
//!   ① **重名**：★ 同一个 `registered_by` ⇒ **允许替换自己的**（升级）；★ 别人 ⇒ **拒**（防冒充）；
//!   ② **报到**：★ 启动时报一声 ⇒ 「**在册 ≠ 活着**」有读数；
//!   ③ **注销**：★ **只能人做**（★ 不是软件自己说走就走 —— 否则成了「谁能悄悄抹掉别人的名字」的洞）；
//!   ④ **落盘**：★ 一行一条（JSONL），★ 与账落盘同一套做法。

use crate::core::registry::Registry;
use std::collections::BTreeMap;
use std::io::Write as _;

use serde::{Deserialize, Serialize};

use crate::core::types::{Admit, IdentitySource, Reason, Refuse, Who};

/// 一条注册：★ **谁交的、交了什么**。
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Registration {
    /// 动作名（★ 在册名 —— 它就是被注册进来的那个名字）。
    pub action: String,
    /// 它对应的函数入口名。
    pub function: String,
    /// ★ **谁注册的**（★ 不是「谁可以用」——那是授权面的事）。
    pub registered_by: String,
    /// ★ **哪一类注册者**：world／system／app／interface（★ 本体 C16 的闭集）。
    pub registered_by_kind: String,
    /// ★ 它要求谁才能用（★ 声明；★ **判定仍在门**）。
    pub required_roles: Vec<String>,
}

/// 一本注册表（★ 内存里的那份；★ 盘上是它的一行一条）。
#[derive(Debug, Default)]
pub struct Register {
    by_action: BTreeMap<String, Registration>,
}

impl Register {
    /// ★ 从盘上读回（★ 文件不在 ⇒ 空表 —— 首次运行，不是错误）。
    /// ★ 坏一行 ⇒ **整本拒**（★ 与账同口径：跳过＝把坏东西藏起来）。
    pub fn load(path: &str) -> Admit<Self> {
        let mut me = Self::default();
        let body = match std::fs::read_to_string(path) {
            Ok(b) => b,
            Err(_) => return Ok(me),
        };
        for (i, line) in body.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let r: Registration = serde_json::from_str(line).map_err(|_| {
                Refuse::new(
                    Reason::BadValue {
                        field: format!("registration[{i}]"),
                        rule: "<合法 JSON，一行一条>".to_string(),
                    },
                    line.chars().take(40).collect::<String>(),
                )
            })?;
            me.by_action.insert(r.action.clone(), r);
        }
        Ok(me)
    }

    /// 在册的动作名（升序）。
    #[must_use]
    pub fn actions(&self) -> Vec<&str> {
        self.by_action.keys().map(String::as_str).collect()
    }

    /// ★ 全部（★ 给「合成在册表」用）。
    #[must_use]
    pub fn all(&self) -> Vec<&Registration> {
        self.by_action.values().collect()
    }

    /// ★★ **已经出现过的注册者类别**（★ 三方同构的读数就从这里取 —— 本体那份 JSON 只看得到 world）。
    #[must_use]
    pub fn kinds_present(&self) -> Vec<String> {
        let mut s: Vec<String> = self
            .by_action
            .values()
            .map(|r| r.registered_by_kind.clone())
            .collect();
        s.sort();
        s.dedup();
        s
    }

    /// 取一条。
    #[must_use]
    pub fn get(&self, action: &str) -> Option<&Registration> {
        self.by_action.get(action)
    }

    /// ★★ **注册**（★ 一次性、持久）。
    ///
    /// ★ 规矩：① 新名字 ⇒ 收；② **同名 ＋ 同一个 `registered_by`** ⇒ **替换**（升级）；
    ///   ③ **同名 ＋ 别人** ⇒ **拒**（防冒充）。
    pub fn register(&mut self, path: &str, reg: Registration) -> Admit<()> {
        if let Some(old) = self.by_action.get(&reg.action) {
            if old.registered_by != reg.registered_by {
                return Err(Refuse::new(
                    Reason::NotPermitted {
                        capability: reg.action.clone(),
                    },
                    format!("<这个名字已经是 {} 的>", old.registered_by),
                ));
            }
        }
        // ★ 先落盘、落成了才入内存（★ 与账落盘同次序）。
        let line = serde_json::to_string(&reg).map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: path.to_string(),
                },
                "<这一条写不成一行 JSON>",
            )
        })?;
        let mut fh = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|_| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: path.to_string(),
                    },
                    "<打不开注册表>",
                )
            })?;
        writeln!(fh, "{line}").map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: path.to_string(),
                },
                "<这一行没写下去>",
            )
        })?;
        self.by_action.insert(reg.action.clone(), reg);
        Ok(())
    }

    /// ★★ **注销：只能人做**（★ 作者裁：软件自己说走就走 ⇒ 谁都能悄悄抹掉别人的名字）。
    pub fn retire(&mut self, action: &str, by: &Who, source: IdentitySource) -> Admit<()> {
        if source != IdentitySource::Issued {
            return Err(Refuse::new(Reason::IdentitySelfDeclared, by.name()));
        }
        if !by.is_system() && !by.name().contains("user") {
            return Err(Refuse::new(
                Reason::NotPermitted {
                    capability: "registration.retire".to_string(),
                },
                by.name(),
            ));
        }
        match self.by_action.remove(action) {
            // ★★ 注销 ＝ **真的从在册表里删掉**（★ 作者口径：「卸载的时候再删除」）。
            Some(_) => Ok(()),
            None => Err(Refuse::new(Reason::UnknownKind, action)),
        }
    }
}

/// ★★★ **个体**（T-260）—— ★ **启动了就要成为一个个体**（作者口径，逐字整理：
/// 「**没有个体化，就是意思是启动了要成为个体**」）。
///
/// ★ 它不是「报到一个名字」：★ 报出的是**一个个体** —— ★ **哪一类 ＋ 本地 id ＋ 状态**。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Individual {
    /// ★ 它是**哪一类**（★ 必须是【在册的类】—— ★ 不在册不许成为个体）。
    pub class: String,
    /// ★ **本地 id**（★ 同一类可以有多个个体：两张网卡、三个服务、两个执行体）。
    pub local_id: String,
    /// ★ **状态**（★ 起来就是 started）。
    pub state: String,
}

/// ★★★ **个体表**（第二张表）—— ★ 「现在有哪些个体活着」。
///
/// ★ 与在册表分开（★ 作者裁：「启动的时候是启动表……是一张另一张表」）：
///
/// | | ★ **在册表**（Register） | ★★ **个体表**（本结构） |
/// |---|---|---|
/// | 什么时候写 | ★ **安装时一次** | ★★ **启动时**（成为个体） |
/// | 管什么 | ★ **这东西存在吗** | ★★ **它现在是个活着的个体吗** |
/// | 落盘吗 | ★ **落**（持久） | ★★ **不落**（瞬时） |
/// | 一格是什么 | ★ 一条动作（名字 ＋ 命令 ＋ 权限） | ★★ **一个个体**（类 ＋ 本地 id ＋ 状态） |
#[derive(Debug, Default)]
pub struct Individuals {
    by_key: BTreeMap<String, Individual>,
}

impl Individuals {
    /// ★★ **成为个体** —— ★ 只有【类在册】才准。
    ///
    /// ★★ 这条闸**不是新立的**：desktop.rs 那条逐字就是它 ——
    ///   「★ **[跳过] ghost （类 frobnicator 不在册）⇒ 桌面上不出现**」。
    /// ★ 同一个名字已经是个体 ⇒ **拒**（★ 不静默替换 —— 谁在就是谁在）。
    pub fn appear(
        &mut self,
        registry: &Registry,
        class: &str,
        local_id: &str,
        state: &str,
    ) -> Admit<()> {
        if !registry.has_kind(class) {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "class".to_string(),
                    rule: "类必须在册".to_string(),
                },
                format!("<{class} 不在册 ⇒ 不能成为个体>"),
            ));
        }
        let key = format!("{class}/{local_id}");
        if self.by_key.contains_key(&key) {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "local_id".to_string(),
                    rule: "同名个体只有一个".to_string(),
                },
                format!("<{key} 已经是个体了>"),
            ));
        }
        self.by_key.insert(
            key,
            Individual {
                class: class.to_string(),
                local_id: local_id.to_string(),
                state: state.to_string(),
            },
        );
        Ok(())
    }

    /// ★ **它在不在**（★ 与「在册」是两个问题）。
    #[must_use]
    pub fn is_alive(&self, class: &str, local_id: &str) -> bool {
        self.by_key.contains_key(&format!("{class}/{local_id}"))
    }

    /// ★ **它的状态**（★ 起来是 started）。
    #[must_use]
    pub fn state_of(&self, class: &str, local_id: &str) -> Option<&str> {
        self.by_key
            .get(&format!("{class}/{local_id}"))
            .map(|i| i.state.as_str())
    }

    /// ★ **现在有哪些个体**（★ 排好序，便于读数与比对）。
    #[must_use]
    pub fn present(&self) -> Vec<String> {
        self.by_key.keys().cloned().collect()
    }

    /// ★ 有哪几类在（★ 读「三类铺开」用的那一格）。
    #[must_use]
    pub fn classes_present(&self) -> Vec<&str> {
        let mut v: Vec<&str> = self.by_key.values().map(|i| i.class.as_str()).collect();
        v.sort_unstable();
        v.dedup();
        v
    }

    /// ★ 个体总数。
    #[must_use]
    pub fn count(&self) -> usize {
        self.by_key.len()
    }

    /// ★ **退出**：★ 它不再是活着的个体了。
    pub fn forget(&mut self, class: &str, local_id: &str) -> bool {
        self.by_key.remove(&format!("{class}/{local_id}")).is_some()
    }
}

#[cfg(test)]
mod tests {
    /// ★ 本体原文（判「类在册」要用它）。
    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    use super::*;

    fn temp(tag: &str) -> String {
        let p = std::env::temp_dir().join(format!("worldcore-reg-{tag}.jsonl"));
        let _ = std::fs::remove_file(&p);
        p.to_string_lossy().to_string()
    }

    fn reg(action: &str, by: &str) -> Registration {
        Registration {
            action: action.to_string(),
            function: format!("fn.{action}"),
            registered_by: by.to_string(),
            registered_by_kind: "app".to_string(),
            required_roles: vec!["human".to_string()],
        }
    }

    #[test]
    fn registration_survives_a_reopen_and_the_individuals_table_is_a_second_one() {
        let path = temp("reopen");
        {
            let mut r = Register::load(&path).expect("空表该装得上");
            r.register(&path, reg("demo.ping", "downloader"))
                .expect("该注册得上");
        }
        let back = Register::load(&path).expect("该装得回来");
        assert_eq!(
            back.actions(),
            vec!["demo.ping"],
            "★ 注册过就该一直在（一次性、持久）"
        );
        // ★★ **两张表分开**：★ 在册表落盘且重开后还在；★ 个体表是【另一张】，★ 不落盘。
        let ont = Registry::load(ONT).expect("本体该装得上");
        let mut live = Individuals::default();
        assert!(
            !live.is_alive("application", "demo"),
            "★ 没成为个体 ⇒ 个体表里没有它"
        );
        live.appear(&ont, "application", "demo", "started")
            .expect("★ 类在册 ⇒ 该成为个体");
        assert!(live.is_alive("application", "demo"), "★ 成了个体");
        assert_eq!(live.state_of("application", "demo"), Some("started"));
        assert_eq!(live.present(), vec!["application/demo"]);
        assert_eq!(live.classes_present(), vec!["application"]);
        // ★★ 闸：★ **类不在册 ⇒ 不能成为个体**（desktop.rs 那条「[跳过] ghost」就是它）。
        assert!(
            live.appear(&ont, "frobnicator", "ghost", "started")
                .is_err(),
            "★ 类不在册 ⇒ 拒（不许成为个体）"
        );
        // ★ 同一个名字再成为个体一次 ⇒ 拒（不静默替换）。
        assert!(
            live.appear(&ont, "application", "demo", "started").is_err(),
            "★ 已经是个体 ⇒ 拒"
        );
        assert!(live.forget("application", "demo"), "★ 退出 ⇒ 从个体表划掉");
        assert_eq!(live.count(), 0);
        // ★ 在册表这一份【不受启动表影响】。
        assert!(
            back.get("demo.ping").is_some(),
            "★ 在册表里它还在（装过就一直留着）"
        );
    }

    #[test]
    fn another_app_cannot_take_the_name() {
        let path = temp("clash");
        let mut r = Register::load(&path).expect("空表");
        r.register(&path, reg("demo.ping", "downloader"))
            .expect("第一个该成");
        let got = r.register(&path, reg("demo.ping", "attacker"));
        assert!(got.is_err(), "★ 同名 ＋ 别人 ⇒ 必须拒（防冒充）");
        let ok = r.register(&path, reg("demo.ping", "downloader"));
        assert!(ok.is_ok(), "★ 同名 ＋ 同一个 registered_by ⇒ 允许（升级）");
    }

    #[test]
    fn retire_needs_an_issued_human_and_self_declared_is_refused() {
        let path = temp("retire");
        let mut r = Register::load(&path).expect("空表");
        r.register(&path, reg("demo.ping", "downloader"))
            .expect("该注册得上");
        let fake = Who::new("world://user/fake");
        assert!(
            r.retire("demo.ping", &fake, IdentitySource::SelfDeclared)
                .is_err(),
            "★ 自填身份 ⇒ 拒"
        );
        let human = Who::new("world://user/zhang");
        assert!(
            r.retire("demo.ping", &human, IdentitySource::Issued)
                .is_ok(),
            "★ 系统发的身份 ＋ 人 ⇒ 准"
        );
        assert!(
            r.get("demo.ping").is_none(),
            "★ 注销 ＝ 真的从在册表里删掉（★ 卸载时删）"
        );
        let _ = std::fs::remove_file(&path);
    }
}
