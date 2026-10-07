//! 内置执行器 —— **只有这些事需要碰到载体**，所以只有这些事在这里。
//!
//! 三个执行器各自守着自己的边界：
//!
//! | 执行器 | 它碰什么 | 它特意**不**做什么 |
//! |---|---|---|
//! | `backlight` | 读/写背光设备 | 不校验"该不该调"——调之前门禁已经裁决过 |
//! | `package` | 调包管理器；高危动词前先做载体撤销点 | 不做"要不要确认"的判断——那是清单的 `confirm` 栏 |
//! | `job` | 起长任务；完工后**回写一条结果事件** | 不自己维护"待办清单"——状态由账本折叠算出 |
//!
//! ## ★ 执行器的名字分两栏，不许混
//!
//! [`Provider::name`] 是**实现词／设备词**（`backlight`／`package`／`job`）——回答"**怎么实现**"；
//! [`Provider::capabilities`] 是**语义层的名字**（`notice.mute`／`ledger.compact`／`job.start`）——
//! 回答"**叫什么**"，与本体 `_interfaces`、`cap.d` 的 `capability` 同一套词表。
//!
//! 这两栏一旦混用，`cap.d` 与执行器就会**各有一个合法名字、却对不上**，而这一格
//! 在 2026-10-04 之前**从来没有任何调用点读过**（详见 [`cross_check`]）。

use crate::carrier::provider::{Outcome, Provider};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};

/// 背光执行器：**真设备**（sysfs）。
///
/// 它在无背光设备的机器上**不假装成功**：明确报"找不到设备"，
/// 而不是返回一个编造的亮度值。
pub struct Backlight {
    /// 背光设备根目录（默认 `/sys/class/backlight`；测试可换成临时目录）。
    pub root: PathBuf,
}

impl Default for Backlight {
    fn default() -> Self {
        Backlight {
            root: PathBuf::from("/sys/class/backlight"),
        }
    }
}

impl Backlight {
    /// 找一个可用的背光设备目录（按名字有序，故结果确定）。
    fn device(&self) -> Result<PathBuf, String> {
        let mut names: Vec<PathBuf> = std::fs::read_dir(&self.root)
            .map_err(|e| {
                format!(
                    "ext.world.Carrier.NoDevice: 读不了背光设备目录 {}：{e}",
                    self.root.display()
                )
            })?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.join("max_brightness").is_file())
            .collect();
        names.sort();
        names.into_iter().next().ok_or_else(|| {
            format!(
                "ext.world.Carrier.NoDevice: {} 下没有可用背光设备（缺 max_brightness）",
                self.root.display()
            )
        })
    }

    fn read_u64(path: &Path) -> Result<u64, String> {
        let raw = std::fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Carrier.DeviceReadFail: {}：{e}", path.display()))?;
        raw.trim().parse::<u64>().map_err(|e| {
            format!(
                "ext.world.Carrier.DeviceReadFail: {} 不是整数：{e}",
                path.display()
            )
        })
    }

    /// 把"百分比"翻译成设备刻度（**单位在参数里，不靠猜**）。
    ///
    /// 口径：`scale` 只允许 `raw`（直接给设备值）或 `percent`（0–100）；
    /// 未给时按 `raw`——**不猜**，因为"3"到底是 3% 还是第 3 档是两件完全不同的事。
    fn to_raw(level: u64, max: u64, params: &Value) -> Result<u64, String> {
        let scale = params.get("scale").and_then(Value::as_str).unwrap_or("raw");
        match scale {
            "raw" => {
                if level > max {
                    return Err(format!(
                        "ext.world.Carrier.OutOfRange: 亮度 {level} 超出设备上限 {max}（scale=raw）"
                    ));
                }
                Ok(level)
            }
            "percent" => {
                if level > 100 {
                    return Err(format!(
                        "ext.world.Carrier.OutOfRange: 百分比 {level} 超出 0–100（scale=percent）"
                    ));
                }
                Ok((level * max + 50) / 100)
            }
            other => Err(format!(
                "ext.world.Carrier.BadParam: scale=`{other}` 非法（只允许 raw/percent）"
            )),
        }
    }
}

impl Provider for Backlight {
    fn name(&self) -> &'static str {
        "backlight"
    }

    /// **语义层的名字**（**不是**设备名）：它在本体 `_interfaces` 里叫 `notice.mute`。
    /// 设备词（"怎么实现"）写在 [`Provider::name`] 那一栏（`backlight`）。
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["notice.mute"]
    }

    fn call(&self, verb: &str, params: &Value) -> Result<Value, String> {
        let dev = self.device()?;
        let max = Self::read_u64(&dev.join("max_brightness"))?;
        match verb {
            "get" => {
                let cur = Self::read_u64(&dev.join("brightness"))?;
                Ok(json!({
                    "device": dev.file_name().and_then(|s| s.to_str()).unwrap_or("?"),
                    "level": cur,
                    "max": max,
                    "percent": (cur * 100 + max / 2).checked_div(max).unwrap_or(0),
                }))
            }
            "set" => {
                let level = params.get("level").and_then(Value::as_u64).ok_or_else(|| {
                    "ext.world.Carrier.BadParam: set 需要整数参数 level".to_string()
                })?;
                let raw = Self::to_raw(level, max, params)?;
                std::fs::write(dev.join("brightness"), format!("{raw}\n")).map_err(|e| {
                    format!(
                        "ext.world.Carrier.DeviceWriteFail: 写 {} 失败：{e}",
                        dev.join("brightness").display()
                    )
                })?;
                Ok(json!({
                    "device": dev.file_name().and_then(|s| s.to_str()).unwrap_or("?"),
                    "level": raw,
                    "max": max,
                }))
            }
            other => Err(format!(
                "ext.world.Carrier.UnknownVerb: 背光执行器不认识动词 `{other}`"
            )),
        }
    }
}

/// 包管理执行器：调包管理器；**高危动词前先做载体撤销点**。
pub struct Package {
    /// 包管理器可执行文件（默认 `pacman`；测试可换成任意命令）。
    pub program: String,
    /// 载体撤销点目录（本轮载体撤销的落点）。
    pub undo_dir: PathBuf,
}

impl Default for Package {
    fn default() -> Self {
        Package {
            program: "pacman".to_string(),
            undo_dir: PathBuf::from("/run/undo"),
        }
    }
}

impl Package {
    /// 记一份"包清单"到撤销点目录（**先用可判定的最小动作**：
    /// 记下当前已装包清单，将来可据此判断"多装了哪些"）。
    ///
    /// 为什么不做全盘快照：载体撤销是工程兜底，**不是世界回滚**；
    /// 这里刻意只做"可判定、可复现、可解释"的那一小步，不假装有全盘原子撤销。
    fn mark(&self, request_id: &str) -> Result<Value, String> {
        std::fs::create_dir_all(&self.undo_dir).map_err(|e| {
            format!(
                "ext.world.Carrier.UndoFail: 建不了撤销点目录 {}：{e}",
                self.undo_dir.display()
            )
        })?;
        let path = self.undo_dir.join(format!("pre-{request_id}.list"));
        let out = Command::new(&self.program)
            .arg("-Qq")
            .output()
            .map_err(|e| {
                format!(
                    "ext.world.Carrier.UndoFail: 撤销点无法取得包清单（{}）：{e}",
                    self.program
                )
            })?;
        std::fs::write(&path, &out.stdout).map_err(|e| {
            format!(
                "ext.world.Carrier.UndoFail: 写不了撤销点 {}：{e}",
                path.display()
            )
        })?;
        let n = String::from_utf8_lossy(&out.stdout).lines().count();
        Ok(json!({
            "kind": "carrier-undo",
            "path": path.display().to_string(),
            "packages": n,
        }))
    }
}

impl Provider for Package {
    fn name(&self) -> &'static str {
        "package"
    }

    /// **语义层的名字**（**不是**设备名）：它在本体 `_interfaces` 里叫 `ledger.compact`。
    /// 设备词（"怎么实现"）写在 [`Provider::name`] 那一栏（`package`）。
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["ledger.compact"]
    }

    /// 载体撤销点：记下当前包清单。做不到就报错（**不假装撤得回去**）。
    fn undo_mark(&self, request_id: &str) -> Result<Value, String> {
        self.mark(request_id)
    }

    fn call(&self, verb: &str, params: &Value) -> Result<Value, String> {
        match verb {
            "list" => {
                let out = Command::new(&self.program)
                    .arg("-Qq")
                    .output()
                    .map_err(|e| format!("ext.world.Carrier.ProviderFailed: {e}"))?;
                if !out.status.success() {
                    return Err(format!(
                        "ext.world.Carrier.ProviderFailed: {} -Qq 退出码 {:?}",
                        self.program,
                        out.status.code()
                    ));
                }
                let list: Vec<String> = String::from_utf8_lossy(&out.stdout)
                    .lines()
                    .map(str::to_string)
                    .collect();
                Ok(json!({ "count": list.len(), "packages": list }))
            }
            "install" => {
                let pkg = params
                    .get("package")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        "ext.world.Carrier.BadParam: install 需要参数 package".to_string()
                    })?;
                let out = Command::new(&self.program)
                    .arg("-S")
                    .arg("--noconfirm")
                    .arg(pkg)
                    .output()
                    .map_err(|e| format!("ext.world.Carrier.ProviderFailed: {e}"))?;
                let code = out.status.code().unwrap_or(-1) as i64;
                let detail = json!({
                    "package": pkg,
                    "stdout_tail": tail(&out.stdout, 8),
                    "stderr_tail": tail(&out.stderr, 8),
                });
                if out.status.success() {
                    Ok(detail)
                } else {
                    Err(format!(
                        "ext.world.Carrier.ProviderFailed: 装包失败（退出码 {code}）：{}",
                        tail(&out.stderr, 3).join(" | ")
                    ))
                }
            }
            other => Err(format!(
                "ext.world.Carrier.UnknownVerb: 包执行器不认识动词 `{other}`"
            )),
        }
    }
}

fn tail(raw: &[u8], n: usize) -> Vec<String> {
    let text = String::from_utf8_lossy(raw);
    let lines: Vec<&str> = text.lines().collect();
    let start = lines.len().saturating_sub(n);
    lines[start..].iter().map(|s| s.to_string()).collect()
}

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

/// 执行器注册表：能力名 → 执行器。
///
/// **注册表为空不是"什么都不允许"的安全默认，而是"没装执行器"**——
/// 与门禁策略的空能力表同一条口径：空即拒绝服务，且要说清是"没配好"。
pub struct Registry {
    providers: BTreeMap<String, Box<dyn Provider + Send + Sync>>,
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    /// 空注册表。
    pub fn new() -> Self {
        Registry {
            providers: BTreeMap::new(),
        }
    }

    /// 内置三个执行器（背光 / 包 / 任务）。
    pub fn builtin() -> Self {
        let mut r = Self::new();
        r.add(Box::new(Backlight::default()));
        r.add(Box::new(Package::default()));
        r.add(Box::new(Job::default()));
        r
    }

    /// 注册一个执行器。
    pub fn add(&mut self, p: Box<dyn Provider + Send + Sync>) {
        self.providers.insert(p.name().to_string(), p);
    }

    /// 按名字取执行器。
    pub fn get(&self, name: &str) -> Option<&(dyn Provider + Send + Sync)> {
        self.providers.get(name).map(|b| b.as_ref())
    }

    /// 已注册的执行器名（有序）。
    pub fn names(&self) -> Vec<&str> {
        self.providers.keys().map(String::as_str).collect()
    }
}

/// ★ **执行清单声明的能力 ↔ 执行器自报的能力：对账**（2026-10-04 立）。
///
/// ## 它补的是哪一格（**"从来没人读过的那一格"**）
///
/// [`Provider::capabilities`] 自契约建立起就在，但**在 `src/**` 里零调用点**——
/// 当时 `.capabilities()` 的全部命中都是 `policy.capabilities()`（门禁那一份），
/// **不是执行器这一份**。后果是：清单说"这项能力交给 `backlight` 干"，
/// 而 `backlight` 自己说"我能干的是另一件事"，**两句话可以永远并存，没有任何东西会因此变红**。
///
/// ## 判据（**会红**）
///
/// `cap.d` 里 `provider = P` 的那一项，其 `capability`（**语义层的名字**）必须出现在
/// `P.capabilities()` 里。两边**各有一个合法名字、却不是同一个** ⇒ 红。
///
/// ★ **反例的形态是"两套词表撞车"，不是拼写错**：`notice.mute` 在本体 `_interfaces` 里合法，
/// `brightness.set` 在背光执行器那套词表里**也合法**——可它们不是同一个名字。
/// 拼写错（`brightnes.set`）谁都看得出来；**两套各自合法的词表撞车，只有把这一格接上才看得见**。
///
/// ## 边界（**两条判据不互相冒充**）
///
/// 执行器**根本没注册**不属本条：那是 [`execute`] 第 3 步的"没有对应的执行器"，
/// 本条对它**跳过、不报**——否则同一件事会有两个说法。
///
/// ## 返回
///
/// 全部不一致（**不是第一处**）：有几项就报几项，一项一个字符串，便于一次改完。
pub fn cross_check(
    manifest: &crate::carrier::capd::Manifest,
    registry: &Registry,
) -> Result<(), Vec<String>> {
    let mut bad = Vec::new();
    for cap in manifest.iter() {
        let Some(p) = registry.get(&cap.provider) else {
            // 没注册 ⇒ 第 3 步正面回答它，本条不冒充那条判据。
            continue;
        };
        if !p.capabilities().iter().any(|c| *c == cap.name) {
            bad.push(format!(
                "`{}`：清单把它交给执行器 `{}`，而 `{}` 自报的能力是 {:?} \
                 —— 两边各有一个合法名字，却不是同一个（不是拼写错）",
                cap.name,
                cap.provider,
                cap.provider,
                p.capabilities()
            ));
        }
    }
    if bad.is_empty() {
        Ok(())
    } else {
        Err(bad)
    }
}

/// 执行一次调用：**清单 → 动词 → 执行器 → 结果**。
///
/// 顺序固定，且**每一步失败都不进入下一步**：
///
/// 1. 清单里没有这项能力 ⇒ **拒绝**（根本不动手）；
/// 2. 清单里没有这个动词 ⇒ **拒绝**；
/// 3. 没有对应执行器 ⇒ **拒绝**（并点名"注册表里没有"）；
/// 4. **执行器自报的能力里没有这一项 ⇒ 拒绝**（`cap.d` 与执行器两套词表对不上，见 [`cross_check`]）；
/// 5. 需要人确认 ⇒ 问确认入口；确认未给或入口不可用 ⇒ **拒绝**；
/// 6. 需要载体撤销点 ⇒ 先做撤销点；做不成 ⇒ **拒绝**（不带着"撤不回去"的风险动手）；
/// 7. 执行；
/// 8. 组装结果（成功/失败）。
///
/// ⚠️ **本函数不做"允不允许"的裁决**：它能做的只有"拒绝"，永远不能"放行"——
/// 放行由调用方在**问过门禁之后**才走到这里。
pub fn execute(
    manifest: &crate::carrier::capd::Manifest,
    registry: &Registry,
    inv: &crate::carrier::Invocation,
    confirm: &dyn Fn(&str, &Value) -> bool,
    undo_marker: &dyn Fn(&str) -> Result<Value, String>,
) -> Outcome {
    let cap = match manifest.lookup(&inv.capability) {
        Some(c) => c,
        None => {
            return Outcome::refused(json!({
                "reason": "能力不在执行清单里",
                "capability": inv.capability,
                "manifest": manifest.names(),
            }))
        }
    };
    if !cap.allows(&inv.verb) {
        return Outcome::refused(json!({
            "reason": "动词未被该能力授权",
            "capability": inv.capability,
            "verb": inv.verb,
            "allowed": cap.verbs,
        }));
    }
    let provider = match registry.get(&cap.provider) {
        Some(p) => p,
        None => {
            return Outcome::refused(json!({
                "reason": "没有对应的执行器",
                "provider": cap.provider,
                "registered": registry.names(),
            }))
        }
    };
    // ★ 第 4 步：**执行器自报的能力里必须有这一项**（2026-10-04 接上那一格）。
    //   与第 3 步分开写是刻意的：**"没注册"与"注册了但不会这个"是两件事**，
    //   拒绝的理由要各说各的，否则复盘时分不清是"没装"还是"装错了"。
    if !provider.capabilities().iter().any(|c| *c == cap.name) {
        return Outcome::refused(json!({
            "reason": "执行器自报的能力里没有这一项（两套词表对不上）",
            "capability": cap.name,
            "provider": cap.provider,
            "provider_capabilities": provider.capabilities(),
        }));
    }
    if cap.needs_confirm() && !confirm(&inv.capability, &inv.params) {
        return Outcome::refused(json!({
            "reason": "需要人确认而未获确认（默认拒绝）",
            "capability": inv.capability,
        }));
    }
    let mut undo_ref = None;
    if cap.needs_undo() {
        match undo_marker(&inv.request_id) {
            Ok(u) => undo_ref = Some(u),
            Err(e) => {
                return Outcome::refused(json!({
                    "reason": "撤销点做不成，故不动手",
                    "error": e,
                }))
            }
        }
    }
    match provider.call(&inv.verb, &inv.params) {
        Ok(data) => {
            let o = Outcome::ok(data);
            match undo_ref {
                Some(u) => o.with_undo(u),
                None => o,
            }
        }
        Err(e) => {
            let code =
                crate::common::error::code_of(&e).unwrap_or("ext.world.Carrier.ProviderFailed");
            if code.ends_with("UnknownVerb") || code.ends_with("BadParam") {
                // 参数/动词层面的错属于"根本没动手"。
                let mut o = Outcome::refused(json!({ "reason": e }));
                if let Some(u) = undo_ref {
                    o = o.with_undo(u);
                }
                o
            } else {
                let mut o = Outcome::failed(-1, json!({ "reason": e }));
                if let Some(u) = undo_ref {
                    o = o.with_undo(u);
                }
                o
            }
        }
    }
}

#[cfg(test)]
mod unit {
    use super::*;
    use crate::carrier::capd::Manifest;
    use crate::carrier::Invocation;

    fn manifest(raw: &str) -> Manifest {
        let c = Manifest::parse(raw, Path::new("t.json")).unwrap();
        Manifest::from_caps(vec![c])
    }

    fn inv(cap: &str, verb: &str, params: Value) -> Invocation {
        Invocation {
            capability: cap.to_string(),
            verb: verb.to_string(),
            request_id: "r-1".to_string(),
            params,
        }
    }

    fn no_confirm(_: &str, _: &Value) -> bool {
        false
    }
    fn yes_confirm(_: &str, _: &Value) -> bool {
        true
    }
    fn no_undo(_: &str) -> Result<Value, String> {
        Err("测试：未配置撤销点".to_string())
    }
    fn ok_undo(_: &str) -> Result<Value, String> {
        Ok(json!({"kind":"carrier-undo","path":"/tmp/x"}))
    }

    #[test]
    fn refuses_a_capability_not_in_the_manifest() {
        let m = manifest(r#"{"capability":"a.b","provider":"p","verbs":["x"]}"#);
        let mut reg = Registry::new();
        reg.add(Box::new(Job::default()));
        let o = execute(
            &m,
            &reg,
            &inv("not.declared", "x", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(o.detail.to_string().contains("不在执行清单里"));
    }

    #[test]
    fn refuses_a_verb_not_allowed_by_the_manifest() {
        let m = manifest(r#"{"capability":"a.b","provider":"job","verbs":["start"]}"#);
        let mut reg = Registry::new();
        reg.add(Box::new(Job::default()));
        let o = execute(
            &m,
            &reg,
            &inv("a.b", "list", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(o.detail.to_string().contains("动词未被该能力授权"));
    }

    #[test]
    fn refuses_when_no_provider_is_registered() {
        let m = manifest(r#"{"capability":"a.b","provider":"ghost","verbs":["x"]}"#);
        let reg = Registry::new();
        let o = execute(&m, &reg, &inv("a.b", "x", json!({})), &no_confirm, &no_undo);
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(o.detail.to_string().contains("没有对应的执行器"));
    }

    #[test]
    fn refuses_when_confirmation_is_required_but_missing() {
        let m = manifest(
            r#"{"capability":"job.start","provider":"job","verbs":["list"],"confirm":"required"}"#,
        );
        let mut reg = Registry::new();
        reg.add(Box::new(Job::default()));
        let o = execute(
            &m,
            &reg,
            &inv("job.start", "list", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(o.detail.to_string().contains("需要人确认"));
        // 确认给了 ⇒ 继续走到执行
        let o2 = execute(
            &m,
            &reg,
            &inv("job.start", "list", json!({})),
            &yes_confirm,
            &no_undo,
        );
        assert_eq!(o2.result, crate::carrier::outcome::OK);
    }

    #[test]
    fn refuses_to_act_when_the_undo_point_cannot_be_made() {
        let m = manifest(
            r#"{"capability":"job.start","provider":"job","verbs":["list"],"risk":"high","undo":"before-each"}"#,
        );
        let mut reg = Registry::new();
        reg.add(Box::new(Job::default()));
        let o = execute(
            &m,
            &reg,
            &inv("job.start", "list", json!({})),
            &yes_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(o.detail.to_string().contains("撤销点做不成"));
        // 撤销点做成了 ⇒ 结果里必须带上内容引用
        let o2 = execute(
            &m,
            &reg,
            &inv("job.start", "list", json!({})),
            &yes_confirm,
            &ok_undo,
        );
        assert_eq!(o2.result, crate::carrier::outcome::OK);
        assert!(o2.undo_ref.is_some());
    }

    #[test]
    fn backlight_refuses_rather_than_pretending() {
        // 指向一个不存在的设备根：必须报 NoDevice，**不得**返回编造的亮度
        let b = Backlight {
            root: PathBuf::from("/definitely/not/here"),
        };
        let e = b.call("get", &json!({})).unwrap_err();
        assert!(e.contains("NoDevice"), "{e}");
    }

    #[test]
    fn backlight_percent_scale_is_explicit_not_guessed() {
        // scale 缺失 ⇒ 按 raw；给了 percent 才换算
        assert_eq!(Backlight::to_raw(3, 100, &json!({})).unwrap(), 3);
        assert_eq!(
            Backlight::to_raw(3, 100, &json!({"scale":"percent"})).unwrap(),
            3
        );
        assert_eq!(
            Backlight::to_raw(50, 255, &json!({"scale":"percent"})).unwrap(),
            128
        );
        assert!(Backlight::to_raw(3, 100, &json!({"scale":"percent"})).is_ok());
        assert!(Backlight::to_raw(101, 255, &json!({"scale":"percent"})).is_err());
        assert!(Backlight::to_raw(300, 255, &json!({})).is_err());
        assert!(Backlight::to_raw(1, 255, &json!({"scale":"nonsense"})).is_err());
    }

    /// 测试替身：只自报能力、不动手——用它把"**两套词表**"这一格单独钉住。
    struct Stub {
        who: &'static str,
        caps: Vec<&'static str>,
    }

    impl Provider for Stub {
        fn name(&self) -> &'static str {
            self.who
        }
        fn capabilities(&self) -> Vec<&'static str> {
            self.caps.clone()
        }
        fn call(&self, _verb: &str, _params: &Value) -> Result<Value, String> {
            Ok(json!({"stub": true}))
        }
    }

    /// ★ **会红**：两套词表**各有一个合法名字**、却不是同一个（**不是拼写错**）。
    ///
    /// `notice.mute` 在本体 `_interfaces` 里合法；`brightness.set` 在背光那套词表里**也合法**。
    /// 这一格在 2026-10-04 之前**零调用点** ⇒ 两句话可以永远并存、没有任何东西会红。
    #[test]
    fn red_when_the_two_vocabularies_name_different_things() {
        let m = manifest(r#"{"capability":"notice.mute","provider":"backlight","verbs":["get"]}"#);
        let mut reg = Registry::new();
        reg.add(Box::new(Stub {
            who: "backlight",
            caps: vec!["brightness.set"],
        }));

        // ① 对账函数：点名是哪一项、两边各叫什么。
        let bad = cross_check(&m, &reg).unwrap_err();
        assert_eq!(bad.len(), 1, "两套词表撞车必须被点出来：{bad:?}");
        assert!(bad[0].contains("notice.mute"), "{}", bad[0]);
        assert!(bad[0].contains("brightness.set"), "{}", bad[0]);

        // ② 同一条清单走执行路径 ⇒ **拒绝**（根本不动手），理由与"没注册"分开。
        let o = execute(
            &m,
            &reg,
            &inv("notice.mute", "get", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(
            o.detail.to_string().contains("自报的能力里没有这一项"),
            "{}",
            o.detail
        );
    }

    /// ★ **正控**：对得上的那一对 ⇒ **绿**（不许把不该红的也判红）。
    #[test]
    fn green_when_the_provider_claims_that_capability() {
        let m = manifest(r#"{"capability":"notice.mute","provider":"backlight","verbs":["get"]}"#);
        let mut reg = Registry::new();
        reg.add(Box::new(Stub {
            who: "backlight",
            caps: vec!["notice.mute"],
        }));

        assert!(cross_check(&m, &reg).is_ok(), "对得上的那一对不许红");
        let o = execute(
            &m,
            &reg,
            &inv("notice.mute", "get", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(
            o.result,
            crate::carrier::outcome::OK,
            "正控：对账过了就该走到执行：{}",
            o.detail
        );
    }

    /// **出厂那一对**：`cap.d/` 的清单在出厂注册表上必须**全部对得上**。
    ///
    /// ★ 第二句是必需的**正控**：空清单会让第一句**恒真**——那就成了装饰。
    #[test]
    fn the_factory_manifest_and_the_factory_registry_agree() {
        let m = Manifest::load_dir(Path::new("src/carrier/cap.d")).unwrap();
        let reg = Registry::builtin();
        assert!(
            cross_check(&m, &reg).is_ok(),
            "出厂 cap.d 与出厂执行器对不上：{:?}",
            cross_check(&m, &reg)
        );
        assert_eq!(m.names().len(), 3, "三份清单都要被读到：{:?}", m.names());
    }

    /// 执行器**没注册**不属对账这一条（**两条判据不互相冒充**）。
    #[test]
    fn an_unregistered_provider_is_not_a_vocabulary_mismatch() {
        let m = manifest(r#"{"capability":"notice.mute","provider":"ghost","verbs":["get"]}"#);
        let reg = Registry::new();
        assert!(
            cross_check(&m, &reg).is_ok(),
            "没注册由第 3 步回答，对账对它跳过"
        );
        let o = execute(
            &m,
            &reg,
            &inv("notice.mute", "get", json!({})),
            &no_confirm,
            &no_undo,
        );
        assert_eq!(o.result, crate::carrier::outcome::REFUSED);
        assert!(
            o.detail.to_string().contains("没有对应的执行器"),
            "{}",
            o.detail
        );
    }
}
