//! 面⑦：**执行** —— 真的去做（装包／跑代码／起进程）。
//!
//! 参考 Palantir：`engine/action_executor.py` 的 `ActionExecutor.execute`
//! （先判在册与许可，再交给「干活的」）。
//!
//! ★ 本面只做两件事：① 查动作名在册；② 把活交给注进来的执行体。
//! ★ **「真的动手」那一段不在这里**（它是底层内核）—— 本面只留一个 `Executor` 口。

use aios_worldcore_registry::Registry;
use aios_worldcore_shared::{Admit, Reason, Refuse, Who};

/// 干活的执行体（将来接底层内核：装包／起进程／写文件）。
pub trait Executor {
    /// 真的去做；返回一句可记进账的结果。
    fn run(
        &self,
        action: &str,
        who: &Who,
        params: &serde_json::Map<String, serde_json::Value>,
    ) -> Admit<String>;
}

/// 只记账不干活的执行体（本仓默认；★ 别读成「已经会装了」）。
#[derive(Debug, Default)]
pub struct DryRun;

impl Executor for DryRun {
    fn run(
        &self,
        action: &str,
        _who: &Who,
        _params: &serde_json::Map<String, serde_json::Value>,
    ) -> Admit<String> {
        Ok(format!("dry-run:{action}"))
    }
}

/// 执行器：查在册 ⇒ 交给执行体。
pub struct Exec<'a, E: Executor> {
    registry: &'a Registry,
    executor: E,
}

impl<'a, E: Executor> Exec<'a, E> {
    /// 装一个执行体。
    pub fn new(registry: &'a Registry, executor: E) -> Self {
        Self { registry, executor }
    }

    /// ★ 执行一条动作：未登记 ⇒ 拒（「未登记即拒」在动作面的落法）。
    pub fn execute(
        &self,
        action: &str,
        who: &Who,
        params: &serde_json::Map<String, serde_json::Value>,
    ) -> Admit<String> {
        if !self.registry.action_kinds().contains(&action) {
            return Err(Refuse::new(Reason::UnknownKind, action));
        }
        self.executor.run(action, who, params)
    }
}
