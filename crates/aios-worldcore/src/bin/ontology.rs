//! **本体进程**（T-278）—— ★ 独立进程；★ 启动即装载本体；★ 收注册；★ 收「成为个体」。
//!
//! ★ 三张通行证的**第①张**在这里落：★★ **启动即装载本体，装不上 ⇒ 不许启动**（fail-fast）。
//!
//! ★ 它收两条路（★ 与演示载体同口径）：
//!   · `world/register` —— 安装时的登记：★ 校验 ⇒ 登记（落注册表）⇒ 回话；
//!   · `world/appear`   —— 启动时的「成为个体」：★ 类在册才准。
//!
//! ★ 用法（★ 要 `--features bus-zenoh`）：
//! ```text
//!   ontology <本体.json> <注册表.jsonl>
//! ```

use std::sync::{Arc, Mutex};
use std::time::Duration;

use aios_worldcore::core::command_bridge::CommandRoute;
use aios_worldcore::core::registration::{Individuals, Register, Registration};
use aios_worldcore::core::registry::Registry;
use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;
use aios_worldcore::engine::transport::Transport;

const ASK: &str = "world/register";
const REPLY: &str = "world/register/result";
const APPEAR: &str = "world/appear";

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let ont_path = args
        .first()
        .cloned()
        .unwrap_or_else(|| "ontology.json".to_string());
    let reg_path = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| "registry.jsonl".to_string());

    // ★★★ 第一张通行证：**启动即装载本体，装不上 ⇒ 不许启动**。
    let text = match std::fs::read_to_string(&ont_path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("[本体进程] ★ 装不上本体（{ont_path}）：{e} ⇒ 不许启动（第一张通行证）");
            std::process::exit(2);
        }
    };
    let ont = match Registry::load(&text) {
        Ok(r) => Arc::new(r),
        Err(e) => {
            eprintln!("[本体进程] ★ 本体装不起来：{e} ⇒ 不许启动（第一张通行证）");
            std::process::exit(2);
        }
    };
    let branch = match Register::load(&reg_path) {
        Ok(r) => Arc::new(Mutex::new(r)),
        Err(e) => {
            eprintln!("[本体进程] ★ 注册表读不回来：{e} ⇒ 不许启动");
            std::process::exit(2);
        }
    };
    let live = Arc::new(Mutex::new(Individuals::default()));
    {
        let b = branch.lock().expect("锁");
        println!(
            "[本体进程] ① 本体装上了（{} 类 ／ {} 动作）＋ 在册 {} 条 ⇒ 开工",
            ont.kinds().len(),
            ont.action_kinds().len(),
            b.actions().len()
        );
    }

    let t = match ZenohTransport::connect() {
        Ok(t) => Arc::new(t),
        Err(e) => {
            eprintln!("[本体进程] ★ 连不上总线：{e}");
            std::process::exit(2);
        }
    };
    println!("[本体进程] ② 连上总线；订 {ASK}（登记）＋ {APPEAR}（成为个体）");

    // ★ 路一：登记（★ 一条独立线程）
    {
        let t = Arc::clone(&t);
        let branch = Arc::clone(&branch);
        let reg_path = reg_path.clone();
        std::thread::spawn(move || loop {
            let Ok(msg) = t.take(ASK, Duration::from_secs(30)) else {
                continue;
            };
            let (ok, action, why) = handle_register(&branch, &reg_path, &msg);
            let n = branch.lock().map(|b| b.actions().len()).unwrap_or(0);
            println!("[本体进程] ③ 登记 {action} ⇒ ok={ok}；{why}（★ 在册 {n} 条）");
            let reply = serde_json::json!({"ok": ok, "action": action, "why": why});
            let _ = t.put(REPLY, &reply.to_string());
        });
    }

    // ★ 路二：成为个体（★ 主线程）
    loop {
        let Ok(msg) = t.take(APPEAR, Duration::from_secs(30)) else {
            continue;
        };
        let v: serde_json::Value = serde_json::from_str(&msg).unwrap_or(serde_json::Value::Null);
        let class = v["class"].as_str().unwrap_or("");
        let local_id = v["local_id"].as_str().unwrap_or("");
        let state = v["state"].as_str().unwrap_or("started");
        let mut l = live.lock().expect("锁");
        match l.appear(&ont, class, local_id, state) {
            Ok(()) => println!(
                "[本体进程] ④ {class}/{local_id} **成为个体** ⇒ {state}（★ 个体表现在 {} 个：{}）",
                l.count(),
                l.present().join(" ")
            ),
            Err(e) => println!("[本体进程] ④ {class}/{local_id} **成不了个体** ⇒ {e}"),
        }
    }
}

/// ★ 登记一条（★ 校验 ＋ 落盘 ＋ 入内存）。
fn handle_register(
    branch: &Arc<Mutex<Register>>,
    reg_path: &str,
    msg: &str,
) -> (bool, String, String) {
    let route = match CommandRoute::parse(msg) {
        Ok(r) => r,
        Err(e) => return (false, "<解析失败>".to_string(), format!("{e}")),
    };
    if let Err(e) = route.check() {
        return (false, route.action.clone(), format!("{e}"));
    }
    let reg: Registration = route.as_registration();
    let action = reg.action.clone();
    let mut b = match branch.lock() {
        Ok(b) => b,
        Err(_) => return (false, action, "<锁坏了>".to_string()),
    };
    match b.register(reg_path, reg) {
        Ok(()) => (true, action, "登记了（★ 落盘，从此一直留着）".to_string()),
        Err(e) => (false, action, format!("{e}")),
    }
}
