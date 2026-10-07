#!/bin/sh
# world-projection —— 界面**唯一**的读路径：读世界**自己的**投影出口
# （`world-core project visual`，M07 视觉投影；同源头四要素在首行）。
#
# 纪律（来自本体 `_subscribe.stale_forbidden`）：
#   **读不到就说读不到** —— 世界不可用时打印「离线」，**绝不回放上一次的数**。
#   ⇒ 本脚本不缓存、不落盘、不读任何「上一次」的产物；每次都重新问世界。
# 纪律二：本脚本**只读**，不写任何文件（不碰账本/投影/法律）。
set -u
CONF=/etc/world-core
LEDGER=/var/lib/world-core/ledger.jsonl
LOCK=/var/lib/ledger.lock
CLI=/usr/bin/world-core

offline() { printf '离线'; exit 0; }

# ① 世界进程活着吗？判据是**世界自己的账本锁**（不是 systemd 状态、不是套接字是否在）：
#    写入总线由 socket 单元持有，服务停了套接字仍可能在 ⇒ 套接字存在**不能**证明世界活着。
[ -r "$CONF/src/ontology_definition/ontology.json" ] || offline
[ -r "$CONF/src/gate/policy.json" ]   || offline
[ -r "$LEDGER" ]             || offline
[ -f "$LOCK" ]               || offline
pid=$(cat "$LOCK" 2>/dev/null)
case "${pid:-x}" in *[!0-9]*) offline ;; esac
[ -d "/proc/$pid" ] || offline
[ "$(cat "/proc/$pid/comm" 2>/dev/null)" = "world-core" ] || offline

# ② 读世界自己的投影出口；失败即离线（不猜、不降级）
out=$("$CLI" --ontology "$CONF/src/ontology_definition/ontology.json" --ledger "$LEDGER" --policy "$CONF/src/gate/policy.json" project visual 2>/dev/null) || offline

# ③ 守卫：首行必须是同源头，且带得出 last_seq
head1=$(printf '%s\n' "$out" | head -1)
case "$head1" in '#world-core '*) : ;; *) offline ;; esac
seq=$(printf '%s\n' "$head1" | sed -n 's/.*last_seq=\([0-9][0-9]*\).*/\1/p')
[ -n "$seq" ] || offline

# ④ 取值格：视觉投影里 6 空格缩进的 `muted = <JSON值>`
val=$(printf '%s\n' "$out" | sed -n 's/^      muted = \(.*\)$/\1/p' | tail -1)
if [ -n "$val" ]; then
  printf 'muted=%s seq=%s' "$val" "$seq"
else
  printf 'muted=-- seq=%s' "$seq"
fi
