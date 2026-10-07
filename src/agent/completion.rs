//! **完工通告**（不是登记簿）—— 活儿结束了，世界得说得出"它结束了"。
//!
//! ## 一条**不许违反**的口径（本项目已裁定，写在 `M10` 的代码里）
//!
//! 旧 Go 实现在载体侧**自己维护一本完工铃登记簿**（落盘、重启后标记"丢了"）。
//! 本项目**明确拒绝**那本登记簿，逐字见 `crate::carrier::recover` 与
//! `crate::carrier::providers::Job` 两处的头注：
//! 登记簿要回答的「哪些活还没干完」，**由账本折叠回答**——
//! 否则「待办清单」会成为**第二份真相**：账本说一件事，登记簿说另一件，
//! 而没有任何东西能判定谁对。
//!
//! ⇒ 本模块只做两件事，**都不落第二本账**：
//!
//! | 做 | 不做 |
//! |---|---|
//! | 把一次结束**造**成一条 `notice` 事件的 body／事件（[`Completion::notice_body`]／[`Completion::to_event`]） | **不自己写账本**——写只能走唯一写入口 `World::commit`（`src/lib.rs` 头注第 2 条） |
//! | 从**账本事件**里折叠出"哪些活还没干完"（[`pending`]） | **不读、不写任何"登记簿"文件** |
//!
//! ## 为什么"发通告"而不是"响铃"
//!
//! 旧实现在进程内维护订阅通道，于是有一个"铃响在订阅之前 ⇒ 听铃人永久挂起"的竞态
//! （仓里留了它的教训：`scripts/test/acceptance.rs` 头注逐字「教训来自 `07-agent-native-os` 的
//! "完工铃丢铃"竞态」）。**本模块用通告消掉这个竞态**：
//! 完工是**账本上的一条事实**，谁来读、什么时候来读，都读得到同一条——
//! **"来得晚"不再是丢铃的原因**。
//!
//! ## 边界（如实声明）
//!
//! 本模块**只造事件与折叠**：它**不判断"该不该干这个活"**（那是门禁），
//! **不执行命令**（那是 `crate::carrier::providers` 的 `Job` 执行器）。

use crate::common::event::{new_event, notice_body};
use serde_json::{json, Value};

/// 通告的类型（写进 `notice.type`）。
pub const NOTICE_TYPE: &str = "job.completed";

/// 活儿主体（写进 `notice.subject` 的那个主体）。
pub fn job_subject(job_id: &str) -> String {
    format!("world://job/{job_id}")
}

/// 一个活儿的终态。**取值与载体侧 `job.status` 的口径对齐**
/// （`crate::carrier::providers::Job` 的 `status` 动词报的就是这几个词）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    /// 还在跑。
    Running,
    /// 正常结束（退出码 0）。
    Done,
    /// 非零退出，或**启动即失败**。
    Failed,
    /// 没完工、进程也不在了（机器断电／被杀）——**如实报，不猜**。
    Lost,
}

impl Status {
    /// 这个名字**是对外口径**（与 `job.status` 一致），不许随意改。
    pub fn as_str(&self) -> &'static str {
        match self {
            Status::Running => "running",
            Status::Done => "done",
            Status::Failed => "failed",
            Status::Lost => "lost",
        }
    }

    /// 从一次真实等待的结果定终态。
    ///
    /// `None` ＝ **没能等到**（启动就失败／等不到进程）⇒ `Failed`
    /// ——**不许**把它读成"还在跑"（那会让待办永远不消）。
    pub fn from_wait(exit_code: Option<i32>) -> Self {
        match exit_code {
            Some(0) => Status::Done,
            Some(_) => Status::Failed,
            None => Status::Failed,
        }
    }

    /// 从**对外口径里的那个词**解出终态；不是口径里的词 ⇒ `None`（**不猜**）。
    ///
    /// ⚠ **本方法刻意不叫 `from_str`、也刻意不 `impl std::str::FromStr`**，理由两条：
    /// 1. 它**不是**一次通用解析：只认**我们自己那四个词**（`running`／`done`／`failed`／`lost`），
    ///    认不出即 `None`——这是"**按对外的固定口径取值**"，不是"把字符串解析成 Status"；
    /// 2. 名字叫 `from_str` 时 clippy 会以 `should_implement_trait` 判红（CI 逐字：
    ///    `method from_str can be confused for the standard trait method std::str::FromStr::from_str`
    ///    ⇒ `-D warnings` 下构建失败），而为了消 lint 去 `impl FromStr` 又得硬造一个 `Err` 类型
    ///    ——那是"**为了骗过 lint 而改结构**"，比改名坏得多。
    /// 3. ⇒ 取一个说得出它干什么的名字：`from_word`。
    pub fn from_word(s: &str) -> Option<Self> {
        match s {
            "running" => Some(Status::Running),
            "done" => Some(Status::Done),
            "failed" => Some(Status::Failed),
            "lost" => Some(Status::Lost),
            _ => None,
        }
    }
}

/// 一条完工事实。
#[derive(Debug, Clone, PartialEq)]
pub struct Completion {
    /// 活儿标识。
    pub job_id: String,
    /// 终态。
    pub status: Status,
    /// 退出码（**启动失败记 -1**，与旧实现同口径：负值表示"没能跑起来"）。
    pub exit_code: i32,
}

impl Completion {
    /// 从一次真实等待的结果构造。
    pub fn from_wait(job_id: &str, exit_code: Option<i32>) -> Self {
        Completion {
            job_id: job_id.to_string(),
            status: Status::from_wait(exit_code),
            exit_code: exit_code.unwrap_or(-1),
        }
    }

    /// 从账本里的一条 `notice` 事件解回来。不是完工通告 ⇒ `None`。
    pub fn from_event(ev: &Value) -> Option<Self> {
        if ev.get("kind").and_then(Value::as_str) != Some("notice") {
            return None;
        }
        let body = ev.get("body")?;
        if body.get("type").and_then(Value::as_str) != Some(NOTICE_TYPE) {
            return None;
        }
        let payload = body.get("payload")?;
        let job_id = payload.get("job_id").and_then(Value::as_str)?.to_string();
        let status = Status::from_word(payload.get("status").and_then(Value::as_str)?)?;
        let exit_code = payload
            .get("exit_code")
            .and_then(Value::as_i64)
            .unwrap_or(-1) as i32;
        Some(Completion {
            job_id,
            status,
            exit_code,
        })
    }

    /// 转成一条 `notice` 事件的 **body**。
    ///
    /// `payload` 的键名与载体侧 `job.status` 报的口径对齐（`job_id`／`status`／`exit_code`）。
    pub fn notice_body(&self) -> Value {
        notice_body(
            NOTICE_TYPE,
            &job_subject(&self.job_id),
            json!({
                "job_id": self.job_id,
                "status": self.status.as_str(),
                "exit_code": self.exit_code,
            }),
        )
    }

    /// 这条完工事实的**稳定 JSON 形态**（用来做"折叠两次逐字节相同"这类判据）。
    ///
    /// 为什么要单独给一个方法：本模块**不引 serde 派生**（依赖纪律只允许 `serde_json`），
    /// 而 `assert_eq!(serde_json::to_string(&x))` 需要 `Serialize`
    /// ⇒ 把"稳定形态"这一件事**显式**写在一个地方，比给结构体加派生更好读、也更少依赖。
    pub fn stable_json(&self) -> Value {
        json!({
            "job_id": self.job_id,
            "status": self.status.as_str(),
            "exit_code": self.exit_code,
        })
    }

    /// 造一条**完整事件**（交给唯一写入口去落笔）。
    pub fn to_event(&self, seq: u64, actor: &str) -> Value {
        new_event(seq, "notice", actor, self.notice_body())
    }
}

/// **待办**：哪些活还没干完。
///
/// 判据只有一句：**有意图、但没有完工通告** ⇒ 还没干完。
/// `intents` 是已见过的意图（`(job_id, request_id)`），`completions` 是已见过的完工通告。
///
/// ⚠ **本函数不读任何文件**——这是"没有第二本登记簿"在结构上的落点：
/// 把载体侧所有"登记簿"删掉，**答案不变**。
pub fn pending(intents: &[(String, String)], completions: &[Completion]) -> Vec<String> {
    let done: std::collections::BTreeSet<&str> =
        completions.iter().map(|c| c.job_id.as_str()).collect();
    let mut out: Vec<String> = intents
        .iter()
        .map(|(job_id, _rid)| job_id.clone())
        .filter(|id| !done.contains(id.as_str()))
        .collect();
    out.sort();
    out.dedup();
    out
}

/// 从**账本事件**里挑出全部完工通告（读法是叶子：不写盘、不取锁、不改一个字节）。
pub fn completions_in(events: &[Value]) -> Vec<Completion> {
    events.iter().filter_map(Completion::from_event).collect()
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn status_follows_the_exit_code() {
        assert_eq!(Status::from_wait(Some(0)), Status::Done);
        assert_eq!(Status::from_wait(Some(3)), Status::Failed);
        assert_eq!(
            Status::from_wait(None),
            Status::Failed,
            "没等到 ⇒ 失败，不许读成【还在跑】"
        );
        assert_eq!(Completion::from_wait("j1", None).exit_code, -1);
    }

    #[test]
    fn stale_bookkeeping_does_not_decide_pending() {
        // 三个意图，其中两个有完工通告
        let intents = vec![
            ("j1".to_string(), "r1".to_string()),
            ("j2".to_string(), "r2".to_string()),
            ("j3".to_string(), "r3".to_string()),
        ];
        let done = vec![
            Completion::from_wait("j1", Some(0)),
            Completion::from_wait("j3", Some(9)),
        ];
        assert_eq!(pending(&intents, &done), vec!["j2".to_string()]);
        // 全部完工 ⇒ 空（**不靠任何文件**）
        let all = vec![
            Completion::from_wait("j1", Some(0)),
            Completion::from_wait("j2", Some(0)),
            Completion::from_wait("j3", Some(0)),
        ];
        assert!(pending(&intents, &all).is_empty());
    }

    #[test]
    fn a_notice_round_trips_and_a_foreign_kind_is_ignored() {
        let c = Completion::from_wait("j7", Some(2));
        let ev = c.to_event(5, "world://agent/1");
        assert_eq!(ev.get("kind").and_then(Value::as_str), Some("notice"));
        assert_eq!(
            ev.get("body")
                .and_then(|b| b.get("subject"))
                .and_then(Value::as_str),
            Some("world://job/j7")
        );
        assert_eq!(Completion::from_event(&ev), Some(c));

        // 非通告 / 别人的通告 ⇒ 一律不认（不猜）
        assert_eq!(Completion::from_event(&json!({ "kind": "change" })), None);
        assert_eq!(
            Completion::from_event(&json!({
                "kind": "notice",
                "body": notice_body("something.else", "world://x", json!({}))
            })),
            None
        );
    }
}
