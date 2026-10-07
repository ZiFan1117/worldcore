//! 载体适配器（`M10`）—— **载体侧的手**：只执行、不裁决。
//!
//! ## 它为什么存在，以及它为什么不能是"另一个权威"
//!
//! 世界核心管"意义"，但它**碰不到设备、装不了包、起不了进程**——那些是载体的事。
//! 于是需要一只手。但手一旦自己有主张，世界就出现了第二个权威：
//! 两处都能决定"这件事允不允许"，两处的结论就可能不同，**"门禁不可绕过"当场失效**。
//!
//! 所以本模块的纪律只有一条，其余全部由它推出：
//!
//! > **只执行、不裁决。允许不允许一律问门禁；本模块永远不能"放行"。**
//!
//! 这条是**不对称**的，而正是这种不对称让它安全：
//!
//! | 它能做 | 它不能做 |
//! |---|---|
//! | **拒绝**（清单里没有这项能力 ⇒ 拒；连不上内核 ⇒ 拒） | **放行**（清单里有、但门禁说不行 ⇒ 一律不行） |
//!
//! ## 两层能力表，各归其位
//!
//! | 层 | 回答什么 | 载体 |
//! |---|---|---|
//! | 语义层 | 这件事在世界里叫什么、允不允许、可不可逆、谁有权写 | `policy.json`（门禁策略，内核持有） |
//! | **载体层（本模块）** | 这件事在载体上**怎么干**（用哪个执行器、允许哪些动词、要不要先撤销、要不要人确认） | `cap.d/*.json`（执行清单） |
//!
//! **两层用同一个能力名对齐。** 载体层**没有**"允不允许"这一栏——它只有"怎么干"。
//!
//! ## 撤销 ≠ 检查点（两个"快照"必须分开）
//!
//! | 名字 | 撤的是什么 | 地位 |
//! |---|---|---|
//! | **载体撤销**（本模块） | 文件系统的字节 | **不是世界状态**；只作工程兜底，**不得**用于满足"坏了能回滚" |
//! | 检查点（内核） | 什么都不撤（只是重放加速） | 缓存，不是真相 |
//! | 补偿事件（内核） | **世界状态** | 这才是"回滚"的正身 |
//!
//! 载体撤销的产物以**内容引用**（`{kind:"content", hash:…}`）作为**事件里的一个字段值**
//! 出现，而不是"另一份真相"。
//!
//! ## 跨进程：本模块跑在自己的进程里，且**对账本零写权限**
//!
//! 它必须动载体，所以它必须**以被管者身份运行**；而法律与真相必须在它写不到的地方。
//! **这不是优化，是"门禁不可绕过"能否成立的前提。**
//!
//! 它要写世界时，只能经通道向内核**提交请求**——请求走的是与其它任何主体完全相同的
//! 那条路（本体校验 → 门禁裁决 → 落笔），没有任何特权。
//!
//! ## 两半：设备的**动作**（`act`）与旧系统的**状态**（`change`）
//!
//! 书 §4.5 `:587` 逐字「设备的动作变成消息，分两步对表。」；同节 `:595` 逐字
//! 「旧系统的状态变成消息，难点在前值。」⇒ 本模块也分两半，各自守同一条纪律的字面：
//!
//! | 那一半 | 落点 | 它守的纪律 |
//! |---|---|---|
//! | 设备的**动作** → `act` | `capd`（执行清单）／`providers`（执行器）／`run`（先问、再做、再报） | **只执行、不裁决** |
//! | 旧系统的**状态** → `change` | `translate`（前值必须带上；翻不出来报错）／`writeside`（原样提交、判词原样带回） | **只写、不裁决** |
//!
//! 两半**都没有**"允不允许"这一栏（`:589` 逐字「这张执行清单里没有"允不允许"这一栏」）；
//! 两半的写权限边界都由 `boundary` 判（`:601` 逐字「以被管者身份运行，对账本与规则都没有写权限」）。

pub mod boundary;
pub mod capd;
pub mod kernel;
pub mod provider;
pub mod providers;
pub mod recover;
pub mod run;
pub mod translate;
pub mod writeside;

use serde_json::Value;

/// 一次执行的结局（在本模块根部再导出，供 `crate::carrier::Outcome` 使用）。
pub use provider::{Outcome, Provider};

/// 一次载体调用的请求（**去掉身份**：身份由内核按套接字给出，不由请求自称）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Invocation {
    /// 能力名（与门禁策略里的能力名**同名**）。
    pub capability: String,
    /// 动词（必须在该能力声明的动词表内）。
    pub verb: String,
    /// 请求号：**意图与结果的配对键**。
    pub request_id: String,
    /// 参数。
    pub params: Value,
}

impl Invocation {
    /// 从一条 `act` 事件的信纸里取出调用（跨进程时由内核转来）。
    pub fn from_act_body(body: &Value) -> Result<Self, String> {
        let capability = body
            .get("capability")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Carrier.BadRequest: act 信纸缺 capability".to_string())?;
        let verb = body
            .get("verb")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Carrier.BadRequest: act 信纸缺 verb".to_string())?;
        let request_id = body
            .get("request_id")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Carrier.BadRequest: act 信纸缺 request_id".to_string())?;
        let params = body.get("params").cloned().unwrap_or(Value::Null);
        Ok(Invocation {
            capability: capability.to_string(),
            verb: verb.to_string(),
            request_id: request_id.to_string(),
            params,
        })
    }

    /// 本次调用的**结果信纸**（回写给内核的那一条 `act`）。
    ///
    /// 口径（刻意）：
    /// - **同一 `request_id`**：这是意图与结果在业务层的配对键；
    /// - `params` 里带 `result`（`ok` / `failed` / `refused`）、`exit_code`、以及可选
    ///   `carrier_undo`（载体撤销的内容引用）；
    /// - **不写身份**：谁做的由内核按连接给出。
    pub fn result_body(
        &self,
        outcome: &str,
        exit_code: i64,
        detail: Value,
        undo_ref: Option<Value>,
    ) -> Value {
        let mut params = serde_json::json!({
            "result": outcome,
            "exit_code": exit_code,
            "detail": detail,
        });
        if let (Some(u), Some(obj)) = (undo_ref, params.as_object_mut()) {
            obj.insert("carrier_undo".to_string(), u);
        }
        serde_json::json!({
            "capability": self.capability,
            "verb": self.verb,
            "request_id": self.request_id,
            "params": params,
        })
    }
}

/// 结果三态（**受控词汇**，机器可判定）。
pub mod outcome {
    /// 执行成功。
    pub const OK: &str = "ok";
    /// 执行了但失败（载体报错、非零退出）。
    pub const FAILED: &str = "failed";
    /// **没有执行**：清单里没有、动词不允许、需要确认而确认未给、连不上内核。
    ///
    /// 与 `failed` 的区别很重要：`failed` 是"试过了、没成"，`refused` 是"根本没动手"。
    pub const REFUSED: &str = "refused";
}
