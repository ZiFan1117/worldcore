//! 面①之补：**命令桥** —— 把底下那些传统命令**注册成我们的动作**（T-244）。
//!
//! ★ 作者令（逐字）：「我们要实现的就是底下的传统的一些命令行的这些命令全部能够接进来，
//!   而接进来的方式就是……把它底下的这些工具，然后注册为我们的 action」。
//!
//! ★★★ 本件解决的正是那个「有一个问题」：
//!   · 问题：要把**全部**命令接进来 ⇒ 不可能手工往本体那份 JSON 里写（且每写一次，
//!     C12 的行号就漂一次 —— 评审席乙 必闭5 点过这条）；
//!   · 解法：**本体一字不动** —— 命令走**注册表**（core::registration），
//!     与本体那 9 条**合成一张在册表** ⇒ 接多少条都不动本体。
//!
//! ★★★ 三条边界（不许破）：
//!   ① **命令字面量不进本体** —— 它住在这张**映射表**里（data/command-map.jsonl）；
//!      本体那条 functions._no_command_literal 与判据 C14／C22 管的就是这件事；
//!   ② **注册的是【名字与地址】，不是命令本身** —— 命令还在它原来的地方（不重造）；
//!   ③ **注册 ≠ 有权** —— 表里的 required_roles 是**声明**，判定仍在门。

use serde::{Deserialize, Serialize};

use crate::core::registration::{Register, Registration};
use crate::core::types::{Admit, Reason, Refuse};

/// 映射表里的一行：**动作 ＋ 它底下那条命令**。
///
/// ★★ 注意 program／args **只给执行器用** —— 注册时**只取那五格**（名字／函数／谁注册／哪一类／权限）。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandRoute {
    pub action: String,
    pub function: String,
    pub registered_by: String,
    pub registered_by_kind: String,
    #[serde(default)]
    pub required_roles: Vec<String>,
    pub program: String,
    #[serde(default)]
    pub args: Vec<String>,
}

impl CommandRoute {
    /// 从一行 JSON 读一条。
    pub fn parse(line: &str) -> Admit<Self> {
        serde_json::from_str(line).map_err(|_| {
            Refuse::new(
                Reason::BadValue {
                    field: "command-map".to_string(),
                    rule: "<合法 JSON，一行一条>".to_string(),
                },
                line.chars().take(40).collect::<String>(),
            )
        })
    }

    /// ★ 它注册进注册表的**那五格**（命令那两格**不进**）。
    #[must_use]
    pub fn as_registration(&self) -> Registration {
        Registration {
            action: self.action.clone(),
            function: self.function.clone(),
            registered_by: self.registered_by.clone(),
            registered_by_kind: self.registered_by_kind.clone(),
            required_roles: self.required_roles.clone(),
        }
    }

    /// ★ 五格齐不齐（缺一 ⇒ 拒 —— 与「未登记即拒」同族）。
    pub fn check(&self) -> Admit<()> {
        // ★ 界面类没有命令行 —— ★ 它注册的是**它自己的动作**（作者令：「UI 肯定也要走注册这个逻辑」）。
        let is_interface = self.registered_by_kind == "interface";
        let mut required: Vec<(&str, &String)> = vec![
            ("action", &self.action),
            ("function", &self.function),
            ("registered_by", &self.registered_by),
            ("registered_by_kind", &self.registered_by_kind),
        ];
        if !is_interface {
            required.push(("program", &self.program));
        }
        for (what, v) in required {
            if v.trim().is_empty() {
                return Err(Refuse::new(
                    Reason::MissingField {
                        field: what.to_string(),
                    },
                    self.action.clone(),
                ));
            }
        }
        if !matches!(
            self.registered_by_kind.as_str(),
            "world" | "system" | "app" | "interface"
        ) {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "registered_by_kind".to_string(),
                    rule: "world|system|app|interface".to_string(),
                },
                self.registered_by_kind.clone(),
            ));
        }
        if self.required_roles.is_empty() {
            return Err(Refuse::new(
                Reason::MissingField {
                    field: "required_roles".to_string(),
                },
                format!("<{} 没写谁能用>", self.action),
            ));
        }
        Ok(())
    }
}

/// ★★ **把一张映射表整批注册进来**（返回注册成功的条数）。
///
/// ★ 表里**坏一行 ⇒ 整批拒**（与账／注册表同口径：跳过＝把坏东西藏起来）。
pub fn register_from_map(map_path: &str, registry_path: &str) -> Admit<usize> {
    let body = std::fs::read_to_string(map_path).map_err(|_| {
        Refuse::new(
            Reason::StorageUnavailable {
                path: map_path.to_string(),
            },
            "<读不到映射表>",
        )
    })?;
    let mut reg = Register::load(registry_path)?;
    let mut n = 0usize;
    for (i, line) in body.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let route = CommandRoute::parse(line)
            .map_err(|e| Refuse::new(e.reason, format!("<第 {} 行>{}", i + 1, e.what)))?;
        route.check()?;
        reg.register(registry_path, route.as_registration())?;
        n += 1;
    }
    Ok(n)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::types::Who;

    const MAP: &str = include_str!("../../../aios-ontology/data/command-map.jsonl");
    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    fn temp(tag: &str) -> String {
        let p = std::env::temp_dir().join(format!("worldcore-cmd-{tag}.jsonl"));
        let _ = std::fs::remove_file(&p);
        p.to_string_lossy().to_string()
    }

    fn write_map(tag: &str, s: &str) -> String {
        let p = std::env::temp_dir().join(format!("worldcore-map-{tag}.jsonl"));
        std::fs::write(&p, s).expect("映射表该写得下去");
        p.to_string_lossy().to_string()
    }

    #[test]
    fn the_whole_map_registers_and_lands_in_the_registry() {
        let reg_path = temp("all");
        let n = register_from_map(&write_map("all", MAP), &reg_path).expect("整批该注册得上");
        assert!(n >= 8, "★ 传统命令该一条条接进来（现取 {n} 条）");
        let back = Register::load(&reg_path).expect("该装得回来");
        assert!(
            back.get("fs.list").is_some(),
            "★ ls 该以 fs.list 这个名字在册"
        );
        assert_eq!(
            back.get("service.start")
                .map(|r| r.registered_by_kind.as_str()),
            Some("system"),
            "★ 命令是 system 类"
        );
        let _ = std::fs::remove_file(&reg_path);
    }

    #[test]
    fn the_command_literal_stays_out_of_the_registration() {
        let r = CommandRoute::parse(MAP.lines().next().expect("表里该有行")).expect("该解析得了");
        let reg = r.as_registration();
        let as_text = format!("{reg:?}");
        assert!(as_text.contains("fs.list"));
        // ★ 用 raw string 避开转义（★ 本件栽过一次：拼字符串丢了一层反斜杠）
        assert!(
            !as_text.contains(r#""ls""#),
            "★ 命令字面量【不进】在册那一份（它只给执行器）"
        );
    }

    #[test]
    fn a_row_without_roles_is_refused() {
        let bad = r#"{"action":"x.y","function":"fn.x.y","registered_by":"b","registered_by_kind":"system","required_roles":[],"program":"ls","args":[]}"#;
        let r = CommandRoute::parse(bad).expect("该解析得了");
        assert!(r.check().is_err(), "★ 没写谁能用 ⇒ 拒（与 C17 同口径）");
    }

    #[test]
    fn a_row_with_a_bad_kind_is_refused() {
        let bad = r#"{"action":"x.y","function":"fn.x.y","registered_by":"b","registered_by_kind":"magic","required_roles":["human"],"program":"ls","args":[]}"#;
        let r = CommandRoute::parse(bad).expect("该解析得了");
        assert!(r.check().is_err(), "★ 类别不在闭集 ⇒ 拒（与 C16 同口径）");
    }
    #[test]
    fn a_command_action_can_be_registered_then_found_then_run() {
        // ① 一张临时映射表：program 用 /bin/echo（一定存在，且无害）。
        let row = r#"{"action":"demo.say","function":"fn.demo.say","registered_by":"builtin-commands","registered_by_kind":"system","required_roles":["human"],"program":"/bin/echo","args":["hello"]}"#;
        let map = write_map("run", row);
        let reg = temp("run");
        // ② 注册（走命令桥）。
        let n = register_from_map(&map, &reg).expect("该注册得上");
        assert_eq!(n, 1);
        // ③ ★★ **两份各是各的**（作者裁：「★ 不是这些东西就各是各的，你不要混在一起」）：
        //    ★ 本体那份【看不到】注册进来的动作；★ 注册那份【看不到】本体自带的动作。
        let ont = crate::core::registry::Registry::load(ONT).expect("本体该装得上");
        let book = crate::core::registration::Register::load(&reg).expect("注册那份该装得上");
        assert!(
            !ont.has_action("demo.say"),
            "★ 本体那一份里【没有】注册进来的动作（各是各的）"
        );
        assert!(!ont.action_kinds().contains(&"fs.list"), "★ 本体里本来就没有它");
        assert!(book.get("demo.say").is_some(), "★ 注册那一份里【有】它");
        assert!(
            book.get("job.start").is_none(),
            "★ 注册那一份里【没有】本体自带的动作（各是各的）"
        );
        // ④ 真的跑（走执行体；★ 不拼 shell）。
        let runner = crate::engine::execute::CommandRunner::from_map(&map).expect("执行体该建得上");
        let out = crate::engine::execute::Executor::run(
            &runner,
            "demo.say",
            &Who::new("world://user/zhang"),
            &serde_json::Map::new(),
        )
        .expect("该跑得起来");
        assert!(out.contains("hello"), "★ 命令真的跑了：{out}");
        // ⑤ 不在册的动作 ⇒ 拒。
        assert!(
            crate::engine::execute::Executor::run(
                &runner,
                "nope.nope",
                &Who::new("world://user/zhang"),
                &serde_json::Map::new()
            )
            .is_err(),
            "★ 不在册 ⇒ 拒"
        );
        let _ = std::fs::remove_file(&reg);
    }

    #[test]
    fn the_registry_reports_which_kinds_are_present() {
        let reg = temp("kinds");
        let _ = register_from_map(&write_map("kinds", MAP), &reg).expect("该注册得上");
        let back = Register::load(&reg).expect("该装得回来");
        assert!(
            back.kinds_present().iter().any(|k| k == "system"),
            "★ 接进来的传统命令是 system 类（★ 本体那份 JSON 只看得到 world）"
        );
        let _ = std::fs::remove_file(&reg);
    }

    #[test]
    fn an_interface_registers_without_a_command_and_all_four_kinds_appear() {
        // ★ 作者令：「UI 肯定也要走注册这个逻辑，都要走」⇒ 界面【也走这张表】，只是它没有命令行。
        let reg = temp("iface");
        let _ = register_from_map(&write_map("iface", MAP), &reg).expect("该注册得上");
        let back = Register::load(&reg).expect("该装得回来");
        let kinds = back.kinds_present();
        assert!(
            kinds.iter().any(|k| k == "system"),
            "★ 传统命令是 system 类"
        );
        assert!(kinds.iter().any(|k| k == "app"), "★ 上层应用是 app 类");
        assert!(
            kinds.iter().any(|k| k == "interface"),
            "★ 界面也走注册（作者令：UI 也要走注册）"
        );
        assert!(
            back.get("interface.ask_permission").is_some(),
            "★ 界面那个「问人」的动作在册"
        );
        // ★★ 两张表分开（T-260）：★ 在册了【不等于】成了个体 —— ★ 个体是【启动】才有的。
        let ont = crate::core::registry::Registry::load(ONT).expect("本体该装得上");
        let mut table = crate::core::registration::Individuals::default();
        assert!(
            !table.is_alive("service", "sshd"),
            "★ 没启动 ⇒ 个体表里没有它（★ 注册了也没有）"
        );
        // ★★ 个体化的对象是【本体的类】—— 用 service（本体里真有这个类）。
        table
            .appear(&ont, "service", "sshd", "started")
            .expect("★ 类在册 ⇒ 该成为个体");
        assert!(table.is_alive("service", "sshd"), "★ 启动 ⇒ 成了个体");
        assert_eq!(table.state_of("service", "sshd"), Some("started"));
        // ★★★ 真发现（登记在案）：★ **interface 不是本体的类** ⇒ 界面【注册得上、却成不了个体】。
        assert!(
            table.appear(&ont, "interface", "a2ui", "started").is_err(),
            "★ interface 不在本体的 objects 里 ⇒ 它成不了个体（★ 这条要立类才能解）"
        );
        let _ = std::fs::remove_file(&reg);
    }
}
