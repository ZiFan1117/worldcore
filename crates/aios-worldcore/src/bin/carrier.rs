//! **载体（carrier）**（T-270 建，T-294 定名）—— ★ 世界 ↔ 机器之间的承载体，**两个面**：
//!
//! ★ **下向（invoke 面）**：★ 收一条 action ⇒ 查映射表 ⇒ 真起进程 ⇒ 回一条结果；
//! ★ **上向（catalog 面）**：★ 采机器上的工具 ⇒ 提名 ⇒ 等人批 ⇒ 代注册（★ 今天只有 `--install` 的雏形）。
//!
//! ★★ **名字是作者 2026-10-17 裁的**（逐字：「**我觉得叫个载体吧，好吧，就叫个载体**」）。
//!   ★ 不叫「执行体」的理由：★ 那个名字只覆盖【下向】一面，★ 而它**两个方向都干**。
//!
//! ★ 作者令（逐字整理）：★「**把底层的这个载体，写完，然后注册进来**」。
//!
//! ★★ 它在 13 里的位置：★ **`crates/aios-worldcore` 的一支 bin**（★ 不再是演示载体里的散件）。
//!   ★ 逻辑全是 13 已有的：★ `CommandRunner`（查映射表 ⇒ `program+args` ⇒ 不拼 shell）＋ `Executor`。
//!   ★ 新加的只有**【和外面说话的入口】** —— ★ 而它只走 `Transport` 那个口（★ 总线选型没定，故不写死）。
//!
//! ★★ 三种用法（★ 前两种今天就跑得起来；★ 第三种等总线定了接上）：
//! ```text
//!   carrier --once fs.list                  ★ 直接跑一条（★ 不经过口 —— 今天就能验）
//!   carrier --list                          ★ 列出映射表里所有动作（★ 只读）
//!   carrier <话题>                          ★ 从口上收一条跑一条（★ 用 LocalTransport，同进程）
//!   carrier --bus <话题>                    ★★ **真走 zenoh 总线**（★ 要 `--features bus-zenoh`）
//!   carrier --install                       ★★★ **安装时跑一次**：发 11 条登记（★ 启动【不注册】）
//! ```

use std::time::Duration;

use aios_worldcore::core::types::Who;
use aios_worldcore::engine::execute::{CommandRunner, Executor};
use aios_worldcore::engine::transport::{LocalTransport, Transport};

/// ★★★ **载体的数据在哪**（T-310）—— ★ **运行期找，不能写死编译期路径**。
///
/// ★ 为什么改（现取出来的真故障）：★ 原先用 `env!("CARGO_MANIFEST_DIR")` —— 那是**编译期**的建机路径
///   （`/root/aios/...`）；★ 二进制一旦装到 `/usr/lib/aios/`，★ 它**还去读建机目录** ⇒ ★ 崩（`status=101`）。
///
/// ★ 找法（按序，★ 第一个读得到的就用）：
///   ① 环境变量 `AIOS_CARRIER_MAP`；
///   ② **安装位置** `/usr/lib/aios/command-map.jsonl`；
///   ③ 开发位置（★ 本仓 `crates/aios-worldcore/data/command-map.jsonl`，★ 用编译期路径**仅作兜底**）。
fn map_path() -> String {
    if let Ok(p) = std::env::var("AIOS_CARRIER_MAP") {
        if std::path::Path::new(&p).is_file() {
            return p;
        }
    }
    let installed = "/usr/lib/aios/command-map.jsonl";
    if std::path::Path::new(installed).is_file() {
        return installed.to_string();
    }
    concat!(env!("CARGO_MANIFEST_DIR"), "/data/command-map.jsonl").to_string()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let runner = CommandRunner::from_map(&map_path()).expect("映射表该读得上");
    let who = Who::new("world://user/zhang");

    match args.first().map(String::as_str) {
        // ★ ① 直接跑一条：★ 今天就能验（★ 不依赖总线）。
        Some("--once") => {
            let Some(action) = args.get(1) else {
                println!("用法: carrier --once <动作名>");
                return;
            };
            let params = serde_json::Map::new();
            match runner.run(action, &who, &params) {
                Ok(out) => println!("[载体] --once {action} ⇒ OK（{} 字节）\n{out}", out.len()),
                Err(e) => println!("[载体] --once {action} ⇒ 拒：{e}"),
            }
        }
        // ★ ② 列一下（★ 只读）。
        Some("--list") => {
            let text = std::fs::read_to_string(map_path()).expect("映射表该读得上");
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
            println!("[载体] 映射表里 {n} 条");
        }
        // ★★★ **安装时跑一次**（T-289）：★ 发 11 条登记 ⇒ 等本体回话 ⇒ 名字从此留在本体里。
        #[cfg(feature = "bus-zenoh")]
        Some("--install") => {
            use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;
            let t = ZenohTransport::connect().expect("该连得上总线（★ 先起 zenohd）");
            let map_text = std::fs::read_to_string(map_path()).expect("映射表该读得上");
            let mut sent = 0usize;
            let mut ok = 0usize;
            for line in map_text.lines().filter(|l| !l.trim().is_empty()) {
                sent += 1;
                match t.request(
                    "world/register",
                    line,
                    "world/register/result",
                    Duration::from_secs(3),
                ) {
                    Ok(reply) => {
                        let v: serde_json::Value =
                            serde_json::from_str(&reply).unwrap_or(serde_json::Value::Null);
                        if v["ok"].as_bool().unwrap_or(false) {
                            ok += 1;
                        } else {
                            println!("[安装] ★ 被本体拒：{}", v["why"]);
                        }
                    }
                    Err(e) => {
                        println!("[安装] ★ 本体没回话（{e}）⇒ 装不上；★ 本体要先起");
                        break;
                    }
                }
            }
            println!("[安装] 注册完成：发出 {sent} 条，本体收下 {ok} 条");
            println!("[安装] ★ 这些名字从此【一直留在本体里】，★ 启动时不必再注册（卸载时才删）");
        }
        #[cfg(not(feature = "bus-zenoh"))]
        Some("--install") => {
            println!("★ 这个二进制没开 bus-zenoh 特性 ⇒ 编的时候要 --features bus-zenoh")
        }

        // ★★ ③' **真走 zenoh 总线**（★ 要编译时开 `--features bus-zenoh`）。
        #[cfg(feature = "bus-zenoh")]
        Some("--bus") => {
            use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;
            let Some(topic) = args.get(1) else {
                println!("用法: carrier --bus <话题>（★ 要 --features bus-zenoh）");
                return;
            };
            let t = ZenohTransport::connect().expect("该连得上总线（★ 先起 zenohd）");
            println!("[载体] 连上 **zenoh 总线**，看着 {topic}（★ 真总线，不是内存队列）");
            // ★★★ **先订阅** world/exec（★ 一次声明、长期持有）—— ★ 与「先订阅后发」同一条规矩。
            let exec_sub = match t.subscribe("world/exec") {
                Ok(s) => s,
                Err(e) => {
                    println!("[载体] ★ 订不上 world/exec：{e}");
                    return;
                }
            };
            println!("[载体] ★ 已订阅 world/exec（★ 一次声明、长期持有）");

            // ★★★ **启动时【不注册】**（T-289 修正）—— ★ 只**报到**。
            //   ★ 作者口径（逐字）：「**它不需要每次在启动的时候往本体里头注册，是在安装的时候一次性注册就可以了。
            //     然后这个本体里头一直会有相关的内容，卸载的时候在删除**」。
            //   ⇒ ★ 注册在【安装时】做（★ 见 `--install`）；★ 启动这里只报「我活着」。
            let map_text = std::fs::read_to_string(map_path()).expect("映射表该读得上");
            let mut n = 0usize;
            for line in map_text.lines().filter(|l| !l.trim().is_empty()) {
                if let Ok(route) = aios_worldcore::core::command_bridge::CommandRoute::parse(line) {
                    let msg = serde_json::json!({"action": route.action, "by": "carrier"});
                    match t.put("world/alive", &msg.to_string()) {
                        Ok(()) => n += 1,
                        Err(e) => println!("[载体] ★ 报到失败：{e}"),
                    }
                }
            }
            println!(
                "[载体] ① 报到完成：{n} 条（★ 启动【不注册】—— 注册在安装时做过了，名字一直留在本体里）"
            );
            // ★★ 「成为个体」是另一件（★ 一个说「我成了个体」，★ 一个说「这些名字我活着」）。
            let me =
                serde_json::json!({"class": "service", "local_id": "carrier", "state": "started"});
            let _ = t.put("world/appear", &me.to_string());
            println!("[载体] ② 报了：service/carrier 状态 started");

            // ★★ 真总线往返（★ 先订阅、再发、再收 —— zenoh 的硬规矩）。
            match t.round_trip("world/probe", "hello-zenoh", Duration::from_secs(3)) {
                Ok(v) => println!("[载体] ★★ zenoh 真通：world/probe 往返收到「{v}」"),
                Err(e) => println!("[载体] zenoh 往返失败：{e}"),
            }
            // ★★★ **常驻循环**（T-310）—— ★ 载体是【服务】，★ 不是「收一条就退出」。
            //   ★ 作者令：「先把这些都 4 个进程先全写完了、全弄起来」。
            //   ★ 收到一条 ⇒ 执行一条 ⇒ 回一条 ⇒ 继续等（★ 超时不算错，★ 那是「暂时没人派活」）。
            loop {
                let Ok(msg) = exec_sub.recv(Duration::from_secs(30)) else {
                    continue;
                };
                println!("[载体] 收到：{msg}");
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
                println!("[载体] 回话：{out}");
                let _ = t.put("world/exec/result", &out.to_string());
            }
        }
        #[cfg(not(feature = "bus-zenoh"))]
        Some("--bus") => {
            println!("★ 这个二进制没开 bus-zenoh 特性 ⇒ 编的时候要 --features bus-zenoh")
        }
        // ★ ③ 从口上收一条跑一条（★ 同进程内存队列）。
        Some(topic) => {
            let t = LocalTransport::new();
            println!(
                "[载体] 起来了，看着口上的话题 {topic}（★ 今天用 LocalTransport —— 总线选型由人定）"
            );
            match t.take(topic, Duration::from_secs(3)) {
                Ok(msg) => {
                    println!("[载体] 收到：{msg}");
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
                    println!("[载体] 回话：{out}");
                    let _ = t.put("world/exec/result", &out.to_string());
                }
                Err(e) => println!("[载体] 口上没有消息：{e}"),
            }
        }
        None => println!("用法: carrier --once <动作名> | --list | <话题>"),
    }
}
