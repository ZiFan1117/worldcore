#!/bin/bash
# ★★ 本体进程的【起法】（T-284）—— ★ 测试阶段用它；★ 服务化是终态（见注释）。
#
# ★★★ 现状（如实）：
#   · ★ **systemd 起本体 ⇒ 连不上总线**（★ 而★ 同一个二进制手工起 ⇒ 连得上）；
#   · ★ 故障侧已定位（★ 本体侧）、★ 失败点已定位（★ zenoh 协议握手，★ TCP 已建立）：
#     ★ `strace` 加持时【能连上】⇒ ★ 是**进程内部时序**问题；
#   · ★ 已排除 10 项：PrivateTmp／全部沙箱／XDG_RUNTIME_DIR／配置读不到／总线没起／
#     启动顺序瓜葛／HOME／PWD／scouting／LimitNOFILE；★ 也排除了「等总线」（sleep 1/3 都不行）。
#
# ★★ 本脚本做的就是把「手工起」固定下来：★ 参数、环境、日志位置都写死 ⇒ 可复现。
# ★ 服务化时：★ 把 `aios-ontology.service` 的 `ExecStart` 指向本脚本【也不行】——
#   因为是 **systemd 的环境** 本身有问题，★ **必须把那个时序问题查清**。
set -u

ONT=${1:-/usr/lib/aios/ontology.json}
REG=${2:-/var/lib/aios/ontology/registry.jsonl}
BIN=${BIN:-/usr/lib/aios/aios-ontology}
LOG=${LOG:-/var/log/aios-ontology.log}

export ZENOH_CONFIG=${ZENOH_CONFIG:-/etc/aios/zenoh.json5}
export HOME=${HOME:-/root}

mkdir -p "$(dirname "$REG")" "$(dirname "$LOG")"

echo "[起] $BIN $ONT $REG"
echo "[起] ZENOH_CONFIG=$ZENOH_CONFIG"
echo "[起] 日志：$LOG"

# ★ 已在跑就先停（★ 同名进程）
pkill -f "$BIN" 2>/dev/null || true
sleep 1

setsid nohup "$BIN" "$ONT" "$REG" > "$LOG" 2>&1 < /dev/null &
sleep 3

if pgrep -f "$BIN" > /dev/null; then
  echo "[起] 起来了（pid $(pgrep -f "$BIN" | head -1)）"
  echo "[起] 头三行日志："
  head -3 "$LOG"
else
  echo "[起] ★ 没起来 —— 看日志：$LOG"
  tail -5 "$LOG"
  exit 1
fi