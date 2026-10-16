//! 把【本体投影出的 A2UI 帧】发到总线（T-248）。
//!
//! ★ 为什么要有这个 bin：★ 渲染器（gui_renderer.rs:77）读的是
//!   v["messages"][1]["updateComponents"]["components"] —— ★ 即 **A2UI 的完整消息包**；
//!   ★ 而 desktop 发的是「裸帧」（没有 messages）⇒ ★ 渲染出来是**空 body**（292 字节）。
//! ★★ 本 bin 直接用 aios_worldcore::engine::project::project —— ★ 它的形状**正好是渲染器要的**。
use std::time::Duration;

const ONT: &str = "/root/aios/crates/aios-ontology/data/ontology.json";
const CAT: &str = "/root/aios/crates/aios-ontology/data/a2ui-catalog-basic.json";
const FRAMES: &str = "world/system/gui/frames";

fn main() {
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(run());
}

async fn run() {
    let text = std::fs::read_to_string(ONT).expect("read ontology");
    let cat = std::fs::read_to_string(CAT).expect("read catalog");
    let reg = aios_worldcore::core::registry::load_ontology(&text).expect("load ontology");
    let frame =
        aios_worldcore::engine::project::project(&reg, &text, &cat).expect("project");
    let payload = frame.to_string();
    let comps = frame["messages"][1]["updateComponents"]["components"]
        .as_array()
        .map_or(0, Vec::len);
    println!(
        "[投影] 帧 {} 字节；元件 {} 个；在册类 {} 动作 {}",
        payload.len(),
        comps,
        reg.kinds().len(),
        reg.action_kinds().len()
    );
    let s = zenoh::open(zenoh::Config::from_env().expect("cfg"))
        .await
        .expect("open");
    for _ in 0..3 {
        let _ = s.put(FRAMES, payload.clone()).await;
        tokio::time::sleep(Duration::from_millis(300)).await;
    }
    println!("[投影] 已发到 {}（3 次）", FRAMES);
    tokio::time::sleep(Duration::from_millis(500)).await;
}
