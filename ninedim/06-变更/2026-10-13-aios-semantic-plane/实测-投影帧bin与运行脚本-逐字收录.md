# 实测：**把本体投影出的 v1.0 帧发到总线的那支 bin**（逐字收录 · 2026-10-17）

> ★ **为什么用 .md 收而不放 .rs／.sh**：★ **硬约束 8 —— 工程域 ninedim/ 只装档案，不许脚本／二进制**。
> ★ 本件是**档案**（逐字收录那份源码与运行脚本，供人核）；★ **可执行的那一份在载体 B**（VM 的 /root/bus/src/bin/）。

| 项 | 值 |
|---|---|
| ★ 件名（载体 B） | /root/bus/src/bin/project_frame.rs |
| ★ 编译 | cargo build --bin project_frame（CARGO_TARGET_DIR=/root/.ct-bus）⇒ Finished in 7.02s；可执行件 296,098,000 字节 |
| ★ 跑出来的读数 | 「[投影] 帧 7691 字节；元件 84 个；在册类 9 动作 9」⇒ 渲染器「收到第 1／2／3 帧（7691 字节）」⇒「② 已渲染 HTML：/root/bus/frame_1.html（**2694 字节**）」 |
| ★ 为什么要有它 | ★ gui_renderer.rs:77 要的是 **A2UI 的完整消息包**（v["messages"][1]["updateComponents"]["components"]）；★ 而 desktop 发的是「裸帧」（v0.9，没有 messages）⇒ 渲染出来 body 是空的（292 字节） |

## 一、project_frame.rs（逐字）

```rust
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

```

## 二、run_v10.sh（逐字 · 运行脚本）

```bash
#!/bin/bash
set -u
cd /root/bus || exit 1
export ZENOH_CONFIG=/root/bus/cfg.json5
export CARGO_TARGET_DIR=/root/.ct-bus

echo "=== 0. 总线 ==="
pgrep -a zenohd >/dev/null || { setsid nohup /root/.cargo/bin/zenohd --listen tcp/127.0.0.1:7447 > zenohd4.log 2>&1 < /dev/null & }
sleep 2
pgrep -a zenohd | head -1

echo "=== 1. 先起渲染器（订阅） ==="
pkill -f gui_renderer 2>/dev/null
sleep 1
rm -f /root/bus/v10_frame_*.html
setsid nohup ./target/debug/gui_renderer > gui3.log 2>&1 < /dev/null &
sleep 2
cat gui3.log

echo "=== 2. 发【本体投影出的 v1.0 帧】 ==="
/root/.ct-bus/debug/project_frame
echo "PROJECT_RC=$?"

echo "=== 3. 等渲染 ==="
sleep 5
echo "--- gui3.log ---"
cat gui3.log
echo "=== 4. 产物（★ 关键读数）==="
ls -la frame_*.html | tail -6
echo "--- frame_1.html 全文 ---"
cat frame_1.html
echo "--- 它含不含 button data-action ---"
grep -c 'data-action' frame_1.html || true
pkill -f gui_renderer 2>/dev/null
echo CLEANED

```
