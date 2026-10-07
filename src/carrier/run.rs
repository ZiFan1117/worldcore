//! 适配器的运行形态 —— **先问、再做、再报**（顺序不可交换）。
//!
//! ## 一次调用在这里走完
//!
//! ```text
//! ① 意图 ──► 内核（裁决；通过则落笔，应答带回意图事件 id）
//! ② （只有拿到"通过"才执行；本模块是唯一会"动东西"的地方）
//! ③ 结果 ──► 内核（**trace = ① 的事件 id**，因果链闭合）
//! ```
//!
//! ## 三条不许破的口径
//!
//! 1. **内核说不行 ⇒ 一次都不动。** 没有"先做了再报"、没有"本地放行"、没有"排队等内核回来"。
//! 2. **意图必须先于执行。** 先执行后落笔会留下一个窗口：东西已经动了，而世界不知道。
//!    意图先落，"崩在中间"就变成账本上一句诚实的话——**有请求、无结果**。
//! 3. **结果一定带上因果。** 结果的 `trace` 指向意图事件的 id；没有它，
//!    "为什么会变成这样"就退化成时间线。
//!
//! ## 它不做什么
//!
//! **不裁决、不写账本、不维护待办清单。** 待办（哪些活没干完）由账本折叠回答，
//! 不另立一本登记簿——否则"待办清单"就成了第二份真相。

use crate::carrier::capd::Manifest;
use crate::carrier::kernel::{KernelClient, Reply};
use crate::carrier::providers::{self, Registry};
use crate::carrier::{Invocation, Outcome};
use serde_json::{json, Value};

/// 一次端到端调用的结局（供 CLI 打印与测试断言）。
#[derive(Debug, Clone)]
pub struct Attempt {
    /// 内核是否通过了意图。
    pub admitted: bool,
    /// 意图事件的 id（结果的因果锚点）。
    pub intent_id: Option<String>,
    /// 内核拒绝时的正文。
    pub refusal: Option<String>,
    /// 实际执行的结果（`admitted == false` 时为 `None`——**因为一次都没动**）。
    pub outcome: Option<Outcome>,
    /// 结果事件的 id。
    pub result_id: Option<String>,
    /// 提交结果时内核若拒绝，记在这里。
    pub result_refusal: Option<String>,
}

impl Attempt {
    /// 人读的一行结论。
    pub fn summary(&self) -> String {
        if !self.admitted {
            return format!(
                "未获准：{}（**一次都没动**）",
                self.refusal.as_deref().unwrap_or("未说明")
            );
        }
        let o = match &self.outcome {
            Some(o) => o,
            None => return "已获准但未执行（调用方中止）".to_string(),
        };
        let mut s = format!(
            "已执行：{}（退出码 {}）｜意图 {} → 结果 {}",
            o.result,
            o.exit_code,
            self.intent_id.as_deref().unwrap_or("?"),
            self.result_id.as_deref().unwrap_or("（未能回写）")
        );
        if let Some(r) = &self.result_refusal {
            s.push_str(&format!("｜⚠️ 结果回写被拒：{r}"));
        }
        s
    }
}

/// 清单自查（**不含裁决**）：能力在不在、动词允不允许。
///
/// 它为什么独立成一个纯函数：这一步**只读清单、不碰载体、不连内核**，
/// 因此可以单独测、单独讲清——它是"我有没有这项本事"，
/// 而不是"这件事准不准"（后者只有门禁能答）。
pub fn manifest_precheck(manifest: &Manifest, inv: &Invocation) -> Result<(), String> {
    let cap = manifest.lookup(&inv.capability).ok_or_else(|| {
        format!(
            "ext.world.Carrier.UnknownCapability: 能力 `{}` 不在执行清单里（清单有：{:?}）",
            inv.capability,
            manifest.names()
        )
    })?;
    if !cap.allows(&inv.verb) {
        return Err(format!(
            "ext.world.Carrier.VerbNotAllowed: 能力 `{}` 未声明动词 `{}`（已声明：{:?}）",
            inv.capability, inv.verb, cap.verbs
        ));
    }
    Ok(())
}

/// 一个**人类确认入口**：返回 true 才动手。
///
/// 缺省实现是"从终端问一句"。**不给默认放行**：没有终端 ⇒ 拒绝
/// （高危动作不该因为"没人看着"而自动通过）。
pub trait Confirmer {
    /// 问一句，得到允许与否。
    fn confirm(&self, capability: &str, params: &Value) -> bool;
}

/// 终端确认（默认口径：只有明确回答 `y`/`yes` 才算允许，其它一律拒绝）。
pub struct TerminalConfirm;

impl Confirmer for TerminalConfirm {
    fn confirm(&self, capability: &str, params: &Value) -> bool {
        use std::io::Write;
        print!(
            "[确认] 高危动作 {capability}，参数 {}，允许？(y/N) ",
            serde_json::to_string(params).unwrap_or_else(|_| "{}".to_string())
        );
        let _ = std::io::stdout().flush();
        let mut ans = String::new();
        if std::io::stdin().read_line(&mut ans).is_err() {
            return false;
        }
        matches!(ans.trim(), "y" | "Y" | "yes" | "YES")
    }
}

/// 永不确认（无人在场时的口径：**拒绝**）。
pub struct NoConfirm;

impl Confirmer for NoConfirm {
    fn confirm(&self, _c: &str, _p: &Value) -> bool {
        false
    }
}

/// 载体适配器的**一次装配**：内核客户端 + 执行清单 + 执行器注册表 + 确认入口。
///
/// 为什么把它们打成一包：这四个是"这只手"的全部装备，缺一不可；
/// 更重要的是——**把它们绑在一起，就很难在某个分支里偷偷换掉其中一个**
/// （例如换成"不需要门禁的客户端"或"什么都放行的确认入口"）。
pub struct Adapter<'a> {
    /// 写世界的唯一通道。
    pub client: &'a KernelClient,
    /// 执行清单（只回答"怎么干"）。
    pub manifest: &'a Manifest,
    /// 执行器注册表。
    pub registry: &'a Registry,
    /// 人确认入口（需要确认而没确认 ⇒ 拒绝动手）。
    pub confirmer: &'a dyn Confirmer,
}

impl Adapter<'_> {
    /// 执行一次调用（**端到端**：问内核 → 执行 → 报结果）。
    ///
    /// 这是载体适配器的**唯一**入口。它把"顺序不可交换"这条口径写成了代码结构：
    /// 任何一条路径都不可能跳过第 ① 步直接执行。
    pub fn attempt(&self, inv: &Invocation) -> Attempt {
        let client = self.client;
        let manifest = self.manifest;
        let registry = self.registry;
        let confirmer = self.confirmer;

        // ① 意图 —— 先在清单里自查一遍（**清单外的能力根本不问内核**：
        //    省一次往返，且"我没这项能力"这件事本来就该由我拒绝）。
        if let Err(refused) = manifest_precheck(manifest, inv) {
            return Attempt {
                admitted: false,
                intent_id: None,
                refusal: Some(refused),
                outcome: None,
                result_id: None,
                result_refusal: None,
            };
        }

        let intent_body = json!({
            "capability": inv.capability,
            "verb": inv.verb,
            "request_id": inv.request_id,
            "params": inv.params,
        });
        let reply: Reply = match client.submit("act", intent_body, None) {
            Ok(r) => r,
            Err(e) => {
                // 连不上内核 / 内核不给应答 ⇒ **拒绝执行**。手没有法不许动。
                return Attempt {
                    admitted: false,
                    intent_id: None,
                    refusal: Some(e),
                    outcome: None,
                    result_id: None,
                    result_refusal: None,
                };
            }
        };
        if !reply.ok {
            return Attempt {
                admitted: false,
                intent_id: None,
                refusal: reply.error,
                outcome: None,
                result_id: None,
                result_refusal: None,
            };
        }
        let intent_id = reply.event_id().map(str::to_string);

        // ② 执行 —— 至此才允许动东西。
        //
        //    撤销点：只对"清单里要求动手前先撤销"的能力做；执行器做不到就报错，
        //    于是 `execute` 会**拒绝动手**，而不是带着"撤不回去"的风险硬上。
        let undo = |rid: &str| -> Result<Value, String> {
            // 先查这项能力属于哪个执行器，再由**那个执行器**负责做撤销点——
            // 而不是在这里按名字猜（名字猜错就会做出错误的保证）。
            let cap = manifest.lookup(&inv.capability).ok_or_else(|| {
                "ext.world.Carrier.UnknownCapability: 能力不在执行清单里".to_string()
            })?;
            let p = registry.get(&cap.provider).ok_or_else(|| {
                format!(
                    "ext.world.Carrier.UndoUnavailable: 执行器 `{}` 未注册",
                    cap.provider
                )
            })?;
            let v = p.undo_mark(rid)?;
            Ok(json!({ "kind": "carrier-undo", "detail": v }))
        };
        let outcome = providers::execute(
            manifest,
            registry,
            inv,
            &|c, p| confirmer.confirm(c, p),
            &undo,
        );

        // ③ 结果 —— 无论成败都要回写（**失败也是事实**）。
        let body = inv.result_body(
            outcome.result,
            outcome.exit_code,
            outcome.detail.clone(),
            outcome.undo_ref.clone(),
        );
        let (result_id, result_refusal) =
            match client.submit_with_trace("act", body, intent_id.as_deref()) {
                Ok(r) if r.ok => (r.event_id().map(str::to_string), None),
                Ok(r) => (None, r.error),
                Err(e) => (None, Some(e)),
            };

        Attempt {
            admitted: true,
            intent_id,
            refusal: None,
            outcome: Some(outcome),
            result_id,
            result_refusal,
        }
    }
}

/// 跑一个**常驻**适配器：从标准输入逐行读请求、逐行回应答（行分隔协议）。
///
/// 甲方（内核或任何本机进程）写一行 `{"capability":…,"verb":…,"request_id":…,"params":…}`，
/// 适配器回一行 `{"ok":…,…}`。**每一行都会先问内核**，拿不到"通过"就一次都不动。
///
/// 为什么要有这个形态：这是**被载体管理器拉起的常驻件**的样子——
/// 它不主动做任何事，只在被请求时按"先问、再做、再报"走一遍。
pub fn serve(adapter: &Adapter<'_>) -> Result<(), String> {
    use std::io::{BufRead, Write};
    let stdin = std::io::stdin();
    let mut out = std::io::stdout();
    for line in stdin.lock().lines() {
        let line = line.map_err(|e| format!("ext.world.Carrier.StdinFail: {e}"))?;
        if line.trim().is_empty() {
            continue;
        }
        let v: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(e) => {
                let _ = writeln!(
                    out,
                    "{}",
                    json!({"ok":false,"error":format!("ext.world.Carrier.BadRequest: {e}")})
                );
                let _ = out.flush();
                continue;
            }
        };
        let get = |k: &str| v.get(k).and_then(Value::as_str).unwrap_or("").to_string();
        let (cap, verb, rid) = (get("capability"), get("verb"), get("request_id"));
        if cap.is_empty() || verb.is_empty() || rid.is_empty() {
            let _ = writeln!(
                out,
                "{}",
                json!({"ok":false,"error":"ext.world.Carrier.BadRequest: 需要 capability/verb/request_id 三个非空字段"})
            );
            let _ = out.flush();
            continue;
        }
        let params = v.get("params").cloned().unwrap_or(Value::Null);
        let a = adapter.attempt(&Invocation {
            capability: cap,
            verb,
            request_id: rid.clone(),
            params,
        });
        // 先把要用的东西取出来（`summary()` 借用整个 `a`，故必须在搬走字段之前算）。
        let summary = a.summary();
        let error = a.refusal.clone().or_else(|| a.result_refusal.clone());
        let payload = json!({
            "ok": a.admitted,
            "request_id": rid,
            "intent_id": a.intent_id,
            "result_id": a.result_id,
            "outcome": a.outcome.as_ref().map(|o| o.result),
            "exit_code": a.outcome.as_ref().map(|o| o.exit_code),
            "detail": a.outcome.as_ref().map(|o| o.detail.clone()),
            "error": error,
            "summary": summary,
        });
        let _ = writeln!(out, "{payload}");
        let _ = out.flush();
    }
    Ok(())
}
