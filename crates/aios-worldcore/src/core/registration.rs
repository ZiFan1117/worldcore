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

/// ★★★ **启动表**（T-259）—— ★ 与「在册表」**分开的第二张表**。
///
/// ★ 作者口径（逐字整理）：「**它启动的时候，我们就不需要这个注册表了，启动的时候是启动表，
///   就是谁在／谁起来了**」。
///
/// | | ★ 在册表（`Register`） | ★★ 启动表（本结构） |
/// |---|---|---|
/// | ★ 什么时候 | ★ **安装时一次** | ★ **每次启动** |
/// | ★ 管什么 | ★ **这东西存在吗** | ★ **它现在在跑吗** |
/// | ★ 落盘吗 | ★★ **落**（★ 持久） | ★★ **不落**（★ 瞬时：重启后重新报到） |
#[derive(Debug, Default)]
pub struct Alive {
    /// ★ 报到过的名字 ⇒ 报到序号。
    seen: BTreeMap<String, u64>,
    next: u64,
}

impl Alive {
    /// ★ **报到**：★ 记下「它现在在」，★ 返回报到序号。
    /// ★ 它**不管在册**（★ 那是另一张表的事）—— ★ 两张表分开的意义就在这。
    pub fn mark(&mut self, action: &str) -> u64 {
        self.next += 1;
        self.seen.insert(action.to_string(), self.next);
        self.next
    }

    /// ★ **它现在在跑吗**。
    #[must_use]
    pub fn is_alive(&self, action: &str) -> bool {
        self.seen.contains_key(action)
    }

    /// ★ **谁在**（★ 排序了，便于读数与比对）。
    #[must_use]
    pub fn present(&self) -> Vec<&str> {
        self.seen.keys().map(String::as_str).collect()
    }

    /// ★ 在跑的有几个。
    #[must_use]
    pub fn count(&self) -> usize {
        self.seen.len()
    }

    /// ★ **退出**：★ 从启动表里划掉。
    pub fn forget(&mut self, action: &str) -> bool {
        self.seen.remove(action).is_some()
    }
}

#[cfg(test)]
mod tests {
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
    fn registration_survives_a_reopen_and_the_alive_table_is_a_second_one() {
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
        // ★★ **两张表分开**：★ 在册表落盘且重开后还在；★ 启动表是【另一张】，★ 不落盘。
        let mut alive = Alive::default();
        assert!(!alive.is_alive("demo.ping"), "★ 没报到过 ⇒ 启动表里没有它");
        let seq = alive.mark("demo.ping");
        assert_eq!(seq, 1, "★ 报到序号从 1 起");
        assert!(alive.is_alive("demo.ping"), "★ 报到过 ⇒ 启动表里有它");
        assert_eq!(alive.present(), vec!["demo.ping"]);
        assert!(alive.forget("demo.ping"), "★ 退出 ⇒ 从启动表里划掉");
        assert_eq!(alive.count(), 0);
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
