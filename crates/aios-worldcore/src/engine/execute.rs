//! 面⑦：**执行** —— 真的去做（装包／跑代码／起进程）。
//!
//! 参考 Palantir：`engine/action_executor.py` 的 `ActionExecutor.execute`
//! （★ 它的次序：先判在册与许可，再交给「干活的」）。
//!
//! ★ 2026-10-13 接线：本面做三件事 —— ① **先问治理**（没授过 ⇒ `NotPermitted`）；
//! ② 查动作名在册（不在册 ⇒ `UnknownKind`）；③ 把活交给注进来的执行体。
//! ★ **「真的动手」那一段不在这里**（它是底层内核）—— 本面只留一个 `Executor` 口。
//! ★ 这一处将来接 **AIOS 的**哪一件：① 那一段接 `crates/aios-capability-runtime`
//!   （能力运行时的动作派发）；② 「先问治理」那一段接 `crates/aios-policy` 的写闸。

use crate::core::registry::Registry;
use crate::core::types::{Admit, Reason, Refuse, Who};
use crate::governance::Governance;

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

/// 执行器：① 先问治理 ② 查在册 ③ 交给执行体。
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

    /// ★ 执行一条动作：① 治理没授过 ⇒ 拒；② 未登记 ⇒ 拒（「未登记即拒」在动作面的落法）。
    pub fn execute(
        &self,
        action: &str,
        who: &Who,
        params: &serde_json::Map<String, serde_json::Value>,
    ) -> Admit<String> {
        // ① 先问治理：没授过就不许做（★ 先问人，再问在册）。
        self.governance.can_execute(who, action)?;
        // ② 动作名在册吗。
        if !self.registry.action_kinds().contains(&action) {
            return Err(Refuse::new(Reason::UnknownKind, action));
        }
        self.executor.run(action, who, params)
    }
}
