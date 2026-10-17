//! **GUI 进程** —— ★ 世界 ↔ 人 之间那一面（★ 类 ＝ `surface`）。
//!
//! ★★ 作者裁（2026-10-17，逐字整理）：
//!   ·「**GUI 它也是一个单独的进程**，也是同样的道理，**和载体一样**，
//!      **包括注册等等这些东西全由它来负责**」
//!   ·「**用 surface**」「**是这个所以说就是 surface 就行**」
//!   ·「它主要是一些**协议交互**嘛 —— 我 A2UI 的协议过去，然后它再返回」
//!
//! ★★★ 所以本进程【只做四件】：
//!   ① **成为个体**：★ `surface/a2ui`（★ 每次启动 —— ★ 个体表不落盘）
//!   ② **订总线**：★ 收世界发来的 A2UI 帧（★ 一次声明、长期持有）
//!   ③ **落帧**：★ 把帧写到渲染出口（★ 今天＝`/run/aios/gui-frame.json` ＋ 日志）
//!   ④ **回话**：★ 收到帧后回一声（★ 协议是双向的 —— 作者：「协议过去，然后它再返回」）
//!
//! ★★ 它【不】做的（★ 四个独立进程那条）：
//!   · **不读别人的文件** —— ★ 不读本体、不读映射表、不读注册表；
//!   · **不裁决**、**不许写账**、**不持有身份**；
//!   · **不 project** —— ★ 投影（把世界的东西投成 A2UI）是另一件事，
//!     今天的 GUI 只**收帧**、不**造帧**（★ 造帧要读本体，★ 那就违反「不读别人的文件」）。
//!
//! ★ 用法（★ 要 `--features bus-zenoh`）：
//! ```text
//!   aios-gui                      ★ 起：成为个体 ⇒ 订帧 ⇒ 落帧
//! ```

use std::time::Duration;

use aios_worldcore::engine::transport::Transport;

/// ★ 帧从哪条话题来（★ 协议的一侧）。
const FRAME: &str = "world/ui/frame";
/// ★ 回话往哪发（★ 协议的另一侧）。
const ACK: &str = "world/ui/frame/ack";
/// ★ 渲染出口（★ 今天的「屏幕」就是一个文件 —— ★ 真渲染器接它就是下一层）。
const OUT: &str = "/run/aios/gui-frame.json";

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    // ★★ **诊断口**（不是生产路径）：★ 往任意话题发一条 —— ★ 用来验「谁收得到」。
    if args.first().map(String::as_str) == Some("--pub") {
        #[cfg(feature = "bus-zenoh")]
        {
            use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;
            let topic = args.get(1).cloned().unwrap_or_default();
            let payload = args.get(2).cloned().unwrap_or_default();
            let t = ZenohTransport::connect().expect("连不上总线");
            match t.put(&topic, &payload) {
                Ok(()) => println!("[GUI --pub] 发了 {topic}（{} 字节）", payload.len()),
                Err(e) => println!("[GUI --pub] ★ 发失败：{e}"),
            }
        }
        return;
    }
    if args.iter().any(|a| a == "--self-test") {
        println!("[GUI] --self-test：★ 验「订帧 ⇒ 收帧 ⇒ 落帧 ⇒ 回话」这条协议链");
        #[cfg(feature = "bus-zenoh")]
        self_test();
        #[cfg(not(feature = "bus-zenoh"))]
        println!("★ 没开 bus-zenoh 特性");
        return;
    }
    println!("[GUI] 起来了 —— ★ 世界 ↔ 人 之间那一面（类 ＝ surface）");

    #[cfg(not(feature = "bus-zenoh"))]
    {
        println!("★ 这个二进制没开 bus-zenoh 特性 ⇒ 编的时候要 --features bus-zenoh");
    }

    #[cfg(feature = "bus-zenoh")]
    run_bus();
}

#[cfg(feature = "bus-zenoh")]
fn run_bus() {
    use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;

    let t = match ZenohTransport::connect() {
        Ok(t) => t,
        Err(e) => {
            eprintln!("[GUI] ★ 连不上总线：{e}");
            std::process::exit(2);
        }
    };
    println!("[GUI] 连上总线");

    // ★ ① 成为个体：★ 类 ＝ surface（★ 作者裁）
    let me = serde_json::json!({
        "class": "surface",
        "local_id": "a2ui",
        "state": "started"
    });
    match t.put("world/appear", &me.to_string()) {
        Ok(()) => println!("[GUI] ① 成为个体：surface/a2ui（started）"),
        Err(e) => eprintln!("[GUI] ★ 成为个体失败：{e}"),
    }

    // ★ ② 订帧（★ 先订阅、长期持有 —— 与「先订阅后发」同一条硬规矩）
    let sub = match t.subscribe(FRAME) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[GUI] ★ 订不上 {FRAME}：{e}");
            std::process::exit(2);
        }
    };
    println!("[GUI] ② 订上了 {FRAME}（★ 一次声明、长期持有）");

    // ★ ③④ 收一帧 ⇒ 落一帧 ⇒ 回一声（★ 常驻）
    loop {
        let Ok(frame) = sub.recv(Duration::from_secs(30)) else {
            continue;
        };
        println!("[GUI] 收到帧（{} 字节）", frame.len());

        // ★ 落帧：★ 先写临时、再改名（★ 不让读的人看见半截）
        let tmp = format!("{OUT}.tmp");
        let ok = std::fs::write(&tmp, &frame).is_ok() && std::fs::rename(&tmp, OUT).is_ok();
        if !ok {
            eprintln!("[GUI] ★ 落帧失败（{OUT}）—— ★ 目录在不在？");
        }

        // ★ 回话：★ 协议是双向的
        let ack = serde_json::json!({
            "by": "surface/a2ui",
            "bytes": frame.len(),
            "landed": ok
        });
        let _ = t.put(ACK, &ack.to_string());
    }
}

/// ★★ **自测**：★ 发一帧到 `world/ui/frame` ⇒ 等 `world/ui/frame/ack`。
///
/// ★ 谁来收？★ **正在跑的那个 GUI 服务**会收到帧、落帧、回 ack；★ 本自测只发帧、只等 ack。
/// ★ 所以它验的是【协议链】，★ 不是自说自话。
#[cfg(feature = "bus-zenoh")]
fn self_test() {
    use aios_worldcore::engine::transport::zenoh_impl::ZenohTransport;

    let t = match ZenohTransport::connect() {
        Ok(t) => t,
        Err(e) => {
            eprintln!("[GUI] ★ 连不上总线：{e}");
            std::process::exit(2);
        }
    };
    let frame = r#"{"messages":[{"surfaceUpdate":{"surfaceId":"selftest","components":[]}}]}"#;
    match t.request(FRAME, frame, ACK, Duration::from_secs(5)) {
        Ok(ack) => println!("[GUI] ★★ 协议链通：发了 1 帧，收到回话「{ack}」"),
        Err(e) => {
            println!("[GUI] ★ 没收到回话（{e}）⇒ ★ GUI 服务可能没起");
            std::process::exit(1);
        }
    }
}
