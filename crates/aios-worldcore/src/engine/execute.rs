//! 面⑦：**执行** —— 真的去做（装包／跑代码／起进程）。
//!
//! ★ 干活口径学 AIOS 的能力运行时（crates/aios-capability-runtime）：
//! · `dispatcher.rs` 的**封闭决策表** —— 那六条规则的**次序是死的**，第一条命中就短路，
//!   后面的规则**根本看不到**；
//! · 它那条**相位次序**：先问许可／治理，再派发，最后才交给适配器。
//! ★ 学它两样：① **次序是死的、封闭的**（每一步只做一件事，命中即定，后面的看不到）；
//!   ② **未登记即拒**（它 `RETIRED` 的适配器直接报 `UnknownAdapter`）—— 本仓把这条
//!   落在**动作名**与**函数名**两处。
//! ★ 数据组织学的也是它：`ActionDispatchKind` 是**闭集枚举**、`AdapterManifest` 是一张
//!   **声明表** ⇒ 本仓对应的是：**动作到函数的映射从本体读**
//!   （`actions.<动作>.function`，见 `Registry::function_of_action`），
//!   **不许用 `fn.<动作名>` 这条拼接约定** —— 约定会随本体改而悄悄失效，读本体那一项不会。
//!
//! ★ 本面今天五步（次序是死的，每一步命中即定）：
//!   ① **先问治理**（没授过 ⇒ `NotPermitted`）；② 查**动作在册**（不在册 ⇒ `UnknownKind`）；
//!   ③ 找它**对应的函数**（本体没给 ⇒ `MissingField{function}`）；
//!   ④ 查**函数在册**（不在册 ⇒ `UnknownKind`）；⑤ **才**交给执行体（`Executor`）。
//! ★ **「真的动手」那一段不在这里**（它是底层内核）—— 本面只留一个 `Executor` 口。
//!
//! ★★ 第④步**已接满**（2026-10-13 Lead 落）：★ `Registry::source() -> &str` 给出本体原文（`rw-functions` 加，`core/registry.rs:76`）⇒ 本面现建函数面
//!   `Functions::load(self.registry.source())` ⇒ **真调** `functions.call(function_id, params)`
//!   ⇒ **逐条校入参**那一步也在这里做了。
//! ★ 仍**不猜**：不拼 `fn.<动作名>`（③ 从本体读），也不自带第二份本体（④ 用册里那份原文）。
//! ★ 函数面返回的 `Called.value` **今天丢弃** —— ★ 交给调用方的那句结果仍由 `Executor` 出
//!   （`DryRun` 的 `dry-run:<动作>` 不许改，`tests/face_c_governance_execute.rs:112` 断言它）。

use serde_json::{Map, Value};

use crate::core::registry::Registry;
use crate::core::types::{Admit, Reason, Refuse, Who};
use crate::engine::functions::Functions;
use crate::governance::Governance;

/// 干活的执行体（将来接底层内核：装包／起进程／写文件）。
pub trait Executor {
    /// 真的去做；返回一句可记进账的结果。
    fn run(&self, action: &str, who: &Who, params: &Map<String, Value>) -> Admit<String>;
}

/// 只记账不干活的执行体（本仓默认；★ 别读成「已经会装了」）。
#[derive(Debug, Default)]
pub struct DryRun;

impl Executor for DryRun {
    fn run(&self, action: &str, _who: &Who, _params: &Map<String, Value>) -> Admit<String> {
        Ok(format!("dry-run:{action}"))
    }
}

/// ★★ **真跑命令的执行体**（T-245 贯通）：★ 按映射表里的 `program` ＋ `args` 起进程。
///
/// ★★ 三条边界（不许破）：
///   ① **不拼 shell 字符串** —— 用 `Command::new(program).args(args)`；★ 参数逐个 `arg` 追加，
///      ★ **不经过任何解释器**（★ 外部先例 SysKnife 那条：`ActionMechanism::Command{program,args}`，
///      ★ 以及「别把危险的语言给它」）；
///   ② **不在册 ⇒ 拒**（★ 与其余各面同口径）；
///   ③ **注册 ≠ 有权** —— 权限仍在 `Exec` 的门那一步判（★ 这个执行体只被交给它之后才跑）。
#[derive(Debug, Default)]
pub struct CommandRunner {
    routes: std::collections::BTreeMap<String, (String, Vec<String>)>,
}

impl CommandRunner {
    /// ★ 从映射表建（★ 表里坏一行 ⇒ 整份拒）。
    pub fn from_map(map_path: &str) -> Admit<Self> {
        let body = std::fs::read_to_string(map_path).map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: map_path.to_string(),
                },
                "<读不到映射表>",
            )
        })?;
        let mut routes = std::collections::BTreeMap::new();
        for (i, line) in body.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let r = crate::core::command_bridge::CommandRoute::parse(line)
                .map_err(|e| Refuse::new(e.reason, format!("<第 {} 行>{}", i + 1, e.what)))?;
            r.check()?;
            routes.insert(r.action.clone(), (r.program.clone(), r.args.clone()));
        }
        Ok(Self { routes })
    }

    /// ★ 这条动作背后是哪条命令（★ 给读数用）。
    #[must_use]
    pub fn route_of(&self, action: &str) -> Option<&(String, Vec<String>)> {
        self.routes.get(action)
    }
}

impl Executor for CommandRunner {
    fn run(&self, action: &str, _who: &Who, params: &Map<String, Value>) -> Admit<String> {
        let (program, args) = self
            .routes
            .get(action)
            .ok_or_else(|| Refuse::new(Reason::UnknownKind, action))?;
        let mut cmd = std::process::Command::new(program);
        cmd.args(args);
        // ★ 参数逐个追加（★ 仍不给语言：不拼 shell、不过解释器）。
        for (k, v) in params {
            let rendered = v.as_str().map_or_else(|| v.to_string(), str::to_string);
            cmd.arg(format!("--{k}"));
            cmd.arg(rendered);
        }
        let out = cmd.output().map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: program.clone(),
                },
                "<起不了这个程序>",
            )
        })?;
        if !out.status.success() {
            return Err(Refuse::new(
                Reason::BadValue {
                    field: "exit".to_string(),
                    rule: "0".to_string(),
                },
                format!("<{program} 退出码 {:?}>", out.status.code()),
            ));
        }
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    }
}

/// 执行器：① 先问治理 ② 查动作在册 ③ 找函数 ④ 查函数在册 ⑤ 交给执行体。
///
/// ★ 为什么治理要从执行器自己身上过一遍（★ 同登记面那条道理）：不这么办，
/// 「没授过也能执行」—— 调用点只要不喊治理，路就绕过去了。
pub struct Exec<'a, E: Executor> {
    registry: &'a Registry,
    governance: &'a Governance,
    executor: E,
}

impl<'a, E: Executor> Exec<'a, E> {
    /// 装三个协作面：册／治理／执行体。
    pub fn new(registry: &'a Registry, governance: &'a Governance, executor: E) -> Self {
        Self {
            registry,
            governance,
            executor,
        }
    }

    /// ★ 执行一条动作，走完五步（次序不许倒）：
    /// ① 治理没授过 ⇒ 拒；② 动作未登记 ⇒ 拒；③ 本体没给它函数 ⇒ 拒；
    /// ④ 那条函数不在入口表里 ⇒ 拒；⑤ 五步全过 ⇒ 才交给执行体。
    pub fn execute(&self, action: &str, who: &Who, params: &Map<String, Value>) -> Admit<String> {
        // ① 先问治理：没授过就不许做（★ 先问人，再问在册）。
        self.governance.can_execute(who, action)?;
        // ② 动作名在册吗（「未登记即拒」在动作面的落法）。
        if !self.registry.has_action(action) {
            return Err(Refuse::new(Reason::UnknownKind, action));
        }
        // ③ 找它对应的函数 —— ★ 读本体 `actions.<动作>.function`，**不拼 `fn.<动作名>`**。
        let Some(function_id) = self.registry.function_of_action(action) else {
            return Err(Refuse::new(
                Reason::MissingField {
                    field: "function".to_string(),
                },
                action,
            ));
        };
        // ④ 这条函数在入口表里在册吗（悬空引用 ⇒ 拒，不替它猜）＋ **逐条校入参**。
        // ★ 函数面每次现建：`Exec::new` 三参不动（函数表就在册里那份原文，不另给构造器）。
        let functions = Functions::load(self.registry.source())
            .map_err(|_| Refuse::new(Reason::OntologyNotLoaded, action))?;
        if functions.get(function_id).is_none() {
            return Err(Refuse::new(Reason::UnknownKind, function_id));
        }
        // ★ **真调函数面**：查在册 + 逐条校入参（入参不合 ⇒ 它自己拒，原样透出）。
        //   ★ 返回值**丢弃**：交给调用方的那句仍由 executor 出（DryRun 口径不许改）。
        functions.call(function_id, params)?;
        // ⑤ 五步全过 ⇒ 才交给执行体。
        self.executor.run(action, who, params)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    fn who() -> Who {
        Who::new("world://user/zhang")
    }

    /// 只授这一项（★ 治理默认拒；不先授连第②步都走不到）。
    fn gov_with(action: &str) -> Governance {
        let mut gov = Governance::new();
        gov.grant(&who(), action);
        gov
    }

    /// ★ 拿真本体改一处：把某个动作指向的函数名换掉（其余一字不动）。
    fn ont_with_function(action: &str, function: &str) -> String {
        let mut doc: serde_json::Value = serde_json::from_str(ONT).expect("本体该能解析");
        doc["actions"][action]["function"] = Value::String(function.to_string());
        doc.to_string()
    }

    /// ★ 拿真本体改一处：把某个动作的 `function` 那一格**拿掉**。
    fn ont_without_function(action: &str) -> String {
        let mut doc: serde_json::Value = serde_json::from_str(ONT).expect("本体该能解析");
        doc["actions"][action]["function"].take();
        doc.to_string()
    }

    /// ★★ 反例①：**执行前先问治理**。让它红的改法：删掉第①步 ⇒ 本用例红。
    #[test]
    fn governance_is_asked_first() {
        let r = Registry::load(ONT).expect("本体该装得上");
        let gov = Governance::new();
        let ex = Exec::new(&r, &gov, DryRun);
        let got = ex.execute("job.start", &who(), &Map::new());
        let want = Reason::NotPermitted {
            capability: "job.start".to_string(),
        };
        assert_eq!(got.expect_err("没授过不许执行").reason, want);
    }

    /// ★★ 反例②：**未登记的动作即拒**（治理先过，才轮到查在册）。
    #[test]
    fn unknown_action_is_refused() {
        let r = Registry::load(ONT).expect("本体该装得上");
        let gov = gov_with("frobnicate");
        let ex = Exec::new(&r, &gov, DryRun);
        let got = ex.execute("frobnicate", &who(), &Map::new());
        assert_eq!(got.expect_err("未登记该拒").reason, Reason::UnknownKind);
    }

    /// ★★ 反例③：**动作→函数从本体读，不许拼约定**。
    /// 让它红的改法：第③步改成 `format!("fn.{action}")` —— 拼出来的 `fn.job.start` 在册，
    /// 于是本用例红。
    #[test]
    fn a_dangling_function_reference_is_refused() {
        let text = ont_with_function("job.start", "fn.job.nope");
        let r = Registry::load(&text).expect("本体该装得上");
        let fid = r.function_of_action("job.start");
        assert_eq!(fid, Some("fn.job.nope"), "夹具失效");
        let gov = gov_with("job.start");
        let ex = Exec::new(&r, &gov, DryRun);
        let got = ex.execute("job.start", &who(), &Map::new());
        let e = got.expect_err("悬空引用该拒");
        assert_eq!(e.reason, Reason::UnknownKind);
        assert_eq!(e.what, "fn.job.nope");
    }

    /// ★★ 反例④：**动作在册而本体没给它函数 ⇒ 拒**（不替它猜一条）。
    #[test]
    fn an_action_without_a_function_is_refused() {
        let text = ont_without_function("job.start");
        let r = Registry::load(&text).expect("本体该装得上");
        assert_eq!(r.function_of_action("job.start"), None, "夹具失效");
        let gov = gov_with("job.start");
        let ex = Exec::new(&r, &gov, DryRun);
        let got = ex.execute("job.start", &who(), &Map::new());
        let want = Reason::MissingField {
            field: "function".to_string(),
        };
        assert_eq!(got.expect_err("没函数该拒").reason, want);
    }

    /// ★ 正控：五步全过 ⇒ 才交给执行体（今天交出的是 dry-run，不是「已经会做了」）。
    #[test]
    fn registered_action_reaches_the_executor() {
        let r = Registry::load(ONT).expect("本体该装得上");
        let gov = gov_with("job.start");
        let ex = Exec::new(&r, &gov, DryRun);
        let mut params = Map::new();
        // ★ Lead 代改（2026-10-13）：原夹具写 `"application:htop"`，**不合本体**
        //   `fn.job.start.inputs.subject = enum(change,act,notice,job)` ⇒ ④ 接入函数面后必红。
        //   （发现者＝实现席 rw-exec-gov —— 它在接最后一跳时先撞到了这个。）
        params.insert("subject".to_string(), json!("job"));
        let got = ex.execute("job.start", &who(), &params);
        assert_eq!(got.expect("在册该放行"), "dry-run:job.start");
    }

    /// ★ 正控：**每一条在册动作都指得到一条在册函数**（本体自洽，不靠拼接）。
    #[test]
    fn every_action_points_at_a_registered_function() {
        let r = Registry::load(ONT).expect("本体该装得上");
        for action in r.action_kinds() {
            let fid = r.function_of_action(action).expect("动作该有函数");
            assert!(
                r.functions().contains(&fid),
                "{action} 未指到在册函数：{fid}"
            );
        }
    }
}
