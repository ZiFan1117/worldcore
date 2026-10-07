//! **写侧的提交路径**（书 §4.5）—— **只写，不裁决**。
//!
//! ## 它做的事只有三件
//!
//! ```text
//! ① 翻（`crate::carrier::translate`）：外面的一处变化 → 一条 `change` 信纸
//! ② 交（本模块）：**原样**经通道提交给内核——不给自己身份、不改一个字段、不加一句判词
//! ③ 转述（本模块）：内核说通过就是通过、说拒就是拒，**写侧不重判**
//! ```
//!
//! ## 书 §4.5 逐字（`docs/理论/语义世界-理论书-第一版-合订.md:585`）
//!
//! > 它们与世界要的形式之间隔着一只手，这只手在写侧，它的纪律只有一条：
//! > 只写，不裁决。准不准做，一律问 4.2 那道闸。
//!
//! 同节 `:601` 逐字：
//!
//! > 写侧这只手跑在自己的进程里，以被管者身份运行，对账本与规则都没有写权限。
//! > 它要写世界，只能经通道提交请求，走的是和别的任何主体完全相同的那条路：校验、过闸、落笔。
//! > 这一点是"唯一入口"能不能成立的前提。
//!
//! ## 这条纪律在本模块里怎么变成**结构**
//!
//! | 做法 | 反着做会怎样 |
//! |---|---|
//! | 提交用的就是 [`crate::carrier::kernel::KernelClient`]：**请求体不含身份**，身份由内核按套接字给出 | 写侧给自己挑一个身份 ⇒ 世界出现第二个权威 |
//! | 内核拒绝时返回 [`Submitted::Refused`]，**把内核的判词原样带回** | 写侧自己造一句"我不允许" ⇒ 裁决权跑到写侧 |
//! | 连不上内核 ⇒ `Err`（**不降级、不排队、不先做了再报**） | "手没有法也能动" ⇒ 唯一入口失效 |
//!
//! ⚠️ 本模块**没有**、也不许有"允不允许"的判断：它能返回的只有
//! "内核说通过"与"内核说拒"。与 `act` 那一半同一条纪律，逐字见
//! `src/carrier/providers.rs:512-513`（「本函数不做"允不允许"的裁决：它能做的只有"拒绝"，
//! 永远不能"放行"」）与 `src/carrier/mod.rs:15-17` 的那张不对称表。

use crate::carrier::kernel::KernelClient;
use crate::carrier::translate::{translate, Declared, ExternalChange};
use serde_json::Value;

/// 一次提交的结局（**只有两种**：内核收下了，或内核拒了）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Submitted {
    /// 内核放行并落笔。
    Admitted {
        /// 落笔那条事件的 id（复盘时的锚点）。
        event_id: Option<String>,
    },
    /// **内核拒绝**：写侧的事到此为止——它没有裁决权，只有**转述**。
    Refused {
        /// 内核给的判词（**逐字带回**，带 `ext.world.<域>.<原因>` 错误码）。
        verdict: String,
    },
}

impl Submitted {
    /// 世界收下了吗。
    pub fn admitted(&self) -> bool {
        matches!(self, Submitted::Admitted { .. })
    }

    /// 内核的判词（通过时为 `None`）。
    pub fn verdict(&self) -> Option<&str> {
        match self {
            Submitted::Refused { verdict } => Some(verdict),
            Submitted::Admitted { .. } => None,
        }
    }

    /// 人读的一行。
    pub fn summary(&self) -> String {
        match self {
            Submitted::Admitted { event_id } => format!(
                "世界已收下（事件 {}）",
                event_id.as_deref().unwrap_or("（内核未给 id）")
            ),
            Submitted::Refused { verdict } => format!("内核拒绝（写侧不重判）：{verdict}"),
        }
    }
}

/// 提交**一处外部变化**：翻（[`translate`]）→ 原样交内核 → 把判词原样带回。
///
/// 翻不出来时**根本不提交**（返回 `Err`）：这是"账本条数不变"的结构性保证——
/// 不是"提交了但被拒"，而是**一次都没有交出去**。
pub fn submit_external_change(
    client: &KernelClient,
    ext: &ExternalChange,
    declared: &dyn Declared,
) -> Result<Submitted, String> {
    let body = translate(ext, declared)?;
    submit_change_body(client, &body)
}

/// 把一条**已经翻好**的 `change` 信纸原样交内核（本函数**不看**它准不准）。
///
/// 为什么把"翻"与"交"分成两个函数：翻是**写侧自己的事**（前值与名字），
/// 交是**世界的事**（校验、过闸、落笔）。混在一起，迟早会有人在"交"这一步顺手加一句判断。
pub fn submit_change_body(client: &KernelClient, body: &Value) -> Result<Submitted, String> {
    // `claimed_actor = None`：**不给自己身份**（身份由内核按套接字给出）。
    match client.submit("change", body.clone(), None) {
        Ok(r) if r.ok => Ok(Submitted::Admitted {
            event_id: r.event_id().map(str::to_string),
        }),
        Ok(r) => Ok(Submitted::Refused {
            verdict: r
                .error
                .unwrap_or_else(|| "ext.world.Carrier.BadReply: 内核拒绝但没给理由".to_string()),
        }),
        // 连不上内核 / 内核不给应答 ⇒ **拒绝执行**（手没有法不许动，见 `src/carrier/kernel.rs:92-93`）。
        Err(e) => Err(e),
    }
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;
    use std::path::Path;

    #[test]
    fn a_refusal_is_carried_back_verbatim_never_re_judged() {
        let s = Submitted::Refused {
            verdict: "ext.world.Gate.WriteRejected: 门禁拒绝写入：越界的写入一律不放行".to_string(),
        };
        assert!(!s.admitted());
        assert_eq!(
            crate::common::error::code_of(s.verdict().unwrap()),
            Some("ext.world.Gate.WriteRejected")
        );
        // 转述时逐字保留内核的判词，不改写成写侧自己的话
        assert!(s.summary().contains("越界的写入一律不放行"));
    }

    #[test]
    fn an_unreachable_kernel_refuses_instead_of_degrading() {
        // 手没有法不许动：连不上内核 ⇒ `Err`，**不**本地放行、**不**本地落盘
        let c = KernelClient::new(Path::new("/definitely/not/here.sock"));
        let e = submit_change_body(&c, &json!({"subject":"world://x","path":"p"})).unwrap_err();
        assert!(e.contains("KernelUnreachable"), "{e}");
        assert!(e.contains("拒绝执行"), "{e}");
    }
}
