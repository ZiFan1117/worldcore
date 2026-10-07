//! 执行器契约（provider）—— **一项能力在载体上到底怎么干**。
//!
//! ## 契约只有三个词
//!
//! **入参无歧义、返回结构化、失败类型化。** 不允许"调一条命令、从人话里猜结果"——
//! 那是把载体当黑箱，而世界要的是可判定的结果。
//!
//! ## 执行器能做什么，不能做什么
//!
//! | 能做 | 不能做 |
//! |---|---|
//! | 读写设备、调包管理器、起进程、做载体撤销点、等人确认 | **裁决**（允不允许问门禁）、**写账本**（只能请求内核追加） |
//!
//! 执行器**不持有身份**：它写的每一条结果都由内核按连接给出身份，
//! 请求体里没有任何地方可以自称。

use serde_json::Value;

/// 一次执行的结局。
#[derive(Debug, Clone, PartialEq)]
pub struct Outcome {
    /// 三态之一（见 [`crate::carrier::outcome`]）。
    pub result: &'static str,
    /// 退出码；不适用时为 0。
    pub exit_code: i64,
    /// 结构化明细（**给人也给人看，但字段是机器可判定的**）。
    pub detail: Value,
    /// 载体撤销的内容引用（若本次动手前做了撤销点）。
    pub undo_ref: Option<Value>,
}

impl Outcome {
    /// 成功。
    pub fn ok(detail: Value) -> Self {
        Outcome {
            result: crate::carrier::outcome::OK,
            exit_code: 0,
            detail,
            undo_ref: None,
        }
    }

    /// 执行了但失败。
    pub fn failed(exit_code: i64, detail: Value) -> Self {
        Outcome {
            result: crate::carrier::outcome::FAILED,
            exit_code,
            detail,
            undo_ref: None,
        }
    }

    /// **根本没动手**（清单里没有、动词不允许、确认未给、连不上内核）。
    ///
    /// 与"失败"分开是刻意的：**"试过了没成"与"根本没动"是两件事**，
    /// 前者产生了副作用、后者没有；混成一个词会让复盘时无法判断"要不要善后"。
    pub fn refused(detail: Value) -> Self {
        Outcome {
            result: crate::carrier::outcome::REFUSED,
            exit_code: 0,
            detail,
            undo_ref: None,
        }
    }

    /// 带上载体撤销的内容引用。
    pub fn with_undo(mut self, undo_ref: Value) -> Self {
        self.undo_ref = Some(undo_ref);
        self
    }
}

/// 执行器。
pub trait Provider {
    /// 执行器名（与执行清单里的 `provider` 字段对应）。
    fn name(&self) -> &'static str;

    /// 该执行器提供的**语义层能力名**——与本体 `_interfaces`、`cap.d` 的 `capability`
    /// **同一套词表**。
    ///
    /// ★ **不是设备名**：设备词（"怎么实现"）是 [`Provider::name`] 那一栏的事。
    /// ★ 本方法的返回值**会被读**：`cap.d` 里 `provider = 我` 的每一项，其 `capability`
    /// 必须在下面这个清单里找得到，否则拒不动手——判据见
    /// [`crate::carrier::providers::cross_check`]。
    ///
    /// （旧注写"启动期自检用"，而当时它在 `src/**` 里**零调用点**：
    /// 那句描述的是一个**没有发生过的事**，2026-10-04 订正。）
    fn capabilities(&self) -> Vec<&'static str>;

    /// 执行一个动词。实现**必须**：入参无歧义、返回结构化、失败类型化。
    fn call(&self, verb: &str, params: &Value) -> Result<Value, String>;

    /// 做一次**载体撤销点**（只对"动手前要先撤销"的能力有意义）。
    ///
    /// 缺省实现是**明确报"做不成"**，而不是默默返回成功——
    /// 返回成功会让调用方以为"撤得回去"，从而带着风险动手。
    /// **做不到就说做不到**，是这里唯一可接受的行为。
    fn undo_mark(&self, _request_id: &str) -> Result<Value, String> {
        Err(format!(
            "ext.world.Carrier.UndoUnavailable: 执行器 `{}` 没有撤销点能力",
            self.name()
        ))
    }
}
