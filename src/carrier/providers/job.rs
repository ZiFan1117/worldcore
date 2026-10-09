use crate::carrier::provider::Provider;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::io::BufRead;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};

/// 长任务执行器：起任务 → **完工后回写一条结果事件**。
///
/// ## 它与旧实现的关键差别
///
/// 旧实现在载体侧**自己维护一本"完工铃登记簿"**（落盘、重启后标记丢失）。
/// 现在**不再需要那本登记簿**：登记簿要回答的问题——"哪些活还没干完"——
/// 由**账本折叠**回答：一条有意图、无结果的请求就是"还没干完"。
/// 这样"待办清单"不会成为第二份真相。
///
/// 完工本身仍然要有人去等：本执行器 spawn 一个**等待者进程**（就是它自己，
/// 用 `job wait` 形态），由它等子进程结束后把结果事件提交给内核。
pub struct Job {
    /// 运行期状态目录（记录活着的工作者）。
    pub state_dir: PathBuf,
    /// 在内存里登记的活跃任务（工作者 pid）。
    jobs: Arc<Mutex<BTreeMap<String, Value>>>,
}

impl Default for Job {
    fn default() -> Self {
        Job {
            state_dir: PathBuf::from("/run/jobs"),
            jobs: Arc::new(Mutex::new(BTreeMap::new())),
        }
    }
}

impl Job {
    /// 完工台账（工作者写下的一行一条 JSONL）。
    pub fn ledger_path(&self) -> PathBuf {
        self.state_dir.join("completed.jsonl")
    }

    /// 读完工台账。
    pub fn completed(&self) -> Vec<Value> {
        let p = self.ledger_path();
        let f = match std::fs::File::open(&p) {
            Ok(f) => f,
            Err(_) => return Vec::new(),
        };
        BufReader::new(f)
            .lines()
            .map_while(Result::ok)
            .filter_map(|l| serde_json::from_str::<Value>(&l).ok())
            .collect()
    }

    /// 登记一个已启动的任务。
    pub fn remember(&self, job_id: &str, rec: Value) {
        if let Ok(mut m) = self.jobs.lock() {
            m.insert(job_id.to_string(), rec);
        }
    }

    /// 任务是否还活着（按工作者 pid 判断；pid 不在了即"丢了"）。
    pub fn alive(&self, job_id: &str) -> Option<bool> {
        let m = self.jobs.lock().ok()?;
        let rec = m.get(job_id)?;
        let pid = rec.get("waiter_pid").and_then(Value::as_i64)?;
        Some(Path::new(&format!("/proc/{pid}")).exists())
    }
}

impl Provider for Job {
    fn name(&self) -> &'static str {
        "job"
    }

    /// **语义层的名字**（**不是**设备名）：与 `cap.d/job.start.json` 的 `capability` 同名。
    /// 设备词（"怎么实现"）写在 [`Provider::name`] 那一栏（`job`）。
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["job.start"]
    }

    fn call(&self, verb: &str, params: &Value) -> Result<Value, String> {
        match verb {
            "start" => {
                let cmd = params
                    .get("command")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        "ext.world.Carrier.BadParam: start 需要参数 command".to_string()
                    })?
                    .to_string();
                let args: Vec<String> = params
                    .get("args")
                    .and_then(Value::as_array)
                    .map(|a| {
                        a.iter()
                            .filter_map(Value::as_str)
                            .map(str::to_string)
                            .collect()
                    })
                    .unwrap_or_default();
                let job_id = params
                    .get("job_id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        "ext.world.Carrier.BadParam: start 需要参数 job_id（由请求号派生）"
                            .to_string()
                    })?
                    .to_string();

                std::fs::create_dir_all(&self.state_dir).map_err(|e| {
                    format!(
                        "ext.world.Carrier.JobFail: 建不了任务状态目录 {}：{e}",
                        self.state_dir.display()
                    )
                })?;

                let child = Command::new(&cmd)
                    .args(&args)
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn()
                    .map_err(|e| format!("ext.world.Carrier.JobFail: 起不了任务 `{cmd}`：{e}"))?;
                let pid = child.id();

                self.remember(
                    &job_id,
                    json!({ "job_id": job_id, "command": cmd, "args": args, "waiter_pid": pid }),
                );
                Ok(json!({
                    "job_id": job_id,
                    "command": cmd,
                    "args": args,
                    "status": "running",
                    "pid": pid,
                    "completed_ledger": self.ledger_path().display().to_string(),
                }))
            }
            "status" => {
                let job_id = params
                    .get("job_id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        "ext.world.Carrier.BadParam: status 需要参数 job_id".to_string()
                    })?;
                // 先看完工台账（**完工是事实**），再看进程是否还活着。
                if let Some(rec) = self
                    .completed()
                    .into_iter()
                    .rev()
                    .find(|r| r.get("job_id").and_then(Value::as_str) == Some(job_id))
                {
                    return Ok(rec);
                }
                match self.alive(job_id) {
                    Some(true) => Ok(json!({ "job_id": job_id, "status": "running" })),
                    // 没完工、进程也不在 ⇒ **丢了**（机器断电/被杀）：如实报，不猜。
                    Some(false) => Ok(json!({ "job_id": job_id, "status": "lost" })),
                    None => Ok(json!({ "job_id": job_id, "status": "unknown" })),
                }
            }
            "list" => {
                let m = self.jobs.lock().map_err(|_| {
                    "ext.world.Carrier.JobFail: 任务表被毒化（上一次持锁线程崩了）".to_string()
                })?;
                let running: Vec<Value> = m.values().cloned().collect();
                Ok(json!({ "running": running, "completed": self.completed() }))
            }
            "wait" => {
                // 等待者形态：等一个已经起好的进程结束，然后把结果写成台账一行。
                // 由 `run` 子命令以本形态拉起，故这里只返回"该怎么等"的说明，
                // 真正的等待在 `crate::carrier::run` 里做（它需要网络与账本）。
                Err(
                    "ext.world.Carrier.Internal: wait 由 run 形态处理，不经 provider 调用"
                        .to_string(),
                )
            }
            other => Err(format!(
                "ext.world.Carrier.UnknownVerb: 任务执行器不认识动词 `{other}`"
            )),
        }
    }
}
