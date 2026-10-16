//! **执行体**（T-270）—— ★ 那只手：★ 收一条 action ⇒ 查映射表 ⇒ 真起进程 ⇒ 回一条结果。
//!
//! ★ 作者令（逐字整理）：★「**把底层的这个执行体，写完，然后注册进来**」。
//!
//! ★★ 它在 13 里的位置：★ **`crates/aios-worldcore` 的一支 bin**（★ 不再是演示载体里的散件）。
//!   ★ 逻辑全是 13 已有的：★ `CommandRunner`（查映射表 ⇒ `program+args` ⇒ 不拼 shell）＋ `Executor`。
//!   ★ 新加的只有**【和外面说话的入口】** —— ★ 而它只走 `Transport` 那个口（★ 总线选型没定，故不写死）。
//!
//! ★★ 三种用法（★ 前两种今天就跑得起来；★ 第三种等总线定了接上）：
//! ```text
//!   executor --once fs.list                  ★ 直接跑一条（★ 不经过口 —— 今天就能验）
//!   executor --list                          ★ 列出映射表里所有动作（★ 只读）
//!   executor <话题>                          ★ 从口上收一条跑一条（★ 今天用 LocalTransport 演示）
//! ```

use std::time::Duration;

use aios_worldcore::core::types::Who;
use aios_worldcore::engine::execute::{CommandRunner, Executor};
use aios_worldcore::engine::transport::{LocalTransport, Transport};

const MAP: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../aios-ontology/data/command-map.jsonl"
);

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let runner = CommandRunner::from_map(MAP).expect("映射表该读得上");
    let who = Who::new("world://user/zhang");

    match args.first().map(String::as_str) {
        // ★ ① 直接跑一条：★ 今天就能验（★ 不依赖总线）。
        Some("--once") => {
            let Some(action) = args.get(1) else {
                println!("用法: executor --once <动作名>");
                return;
            };
            let params = serde_json::Map::new();
            match runner.run(action, &who, &params) {
                Ok(out) => println!("[执行体] --once {action} ⇒ OK（{} 字节）\n{out}", out.len()),
                Err(e) => println!("[执行体] --once {action} ⇒ 拒：{e}"),
            }
        }
        // ★ ② 列一下（★ 只读）。
        Some("--list") => {
            let text = std::fs::read_to_string(MAP).expect("映射表该读得上");
            let mut n = 0usize;
            for line in text.lines().filter(|l| !l.trim().is_empty()) {
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
                    println!(
                        "  {}  ⇒  {} {:?}",
                        v["action"].as_str().unwrap_or("?"),
                        v["program"].as_str().unwrap_or("?"),
                        v["args"]
                    );
                    n += 1;
                }
            }
            println!("[执行体] 映射表里 {n} 条");
        }
        // ★ ③ 从口上收一条跑一条（★ 总线选型未定 ⇒ 今天用 LocalTransport 演示）。
        Some(topic) => {
            let t = LocalTransport::new();
            println!(
                "[执行体] 起来了，看着口上的话题 {topic}（★ 今天用 LocalTransport —— 总线选型由人定）"
            );
            match t.take(topic, Duration::from_secs(3)) {
                Ok(msg) => {
                    println!("[执行体] 收到：{msg}");
                    let v: serde_json::Value =
                        serde_json::from_str(&msg).unwrap_or(serde_json::Value::Null);
                    let action = v["action"].as_str().unwrap_or("");
                    let params = v["params"].as_object().cloned().unwrap_or_default();
                    let out = match runner.run(action, &who, &params) {
                        Ok(o) => serde_json::json!({ "action": action, "ok": true, "body": o }),
                        Err(e) => {
                            serde_json::json!({ "action": action, "ok": false, "body": format!("{e}") })
                        }
                    };
                    println!("[执行体] 回话：{out}");
                    let _ = t.put("world/exec/result", &out.to_string());
                }
                Err(e) => println!("[执行体] 口上没有消息：{e}"),
            }
        }
        None => println!("用法: executor --once <动作名> | --list | <话题>"),
    }
}
