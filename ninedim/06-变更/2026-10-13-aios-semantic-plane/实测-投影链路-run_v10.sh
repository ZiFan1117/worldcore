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
