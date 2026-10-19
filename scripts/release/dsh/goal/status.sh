#!/bin/bash
# 目标状态速查（人用）：截止倒计时、定时器、最近报告、提交、进度、ALERT/DONE
set -u
G=/root/aios-goals
D=$(cat "$G/deadline.epoch" 2>/dev/null || echo 0)
now=$(date +%s)
left=$(( D - now ))
echo "=== 目标截止（epoch=$D）==="
echo "剩余：$((left / 3600))h $(((left % 3600) / 60))m（现在 $(date -Is)）"
[ -f "$G/DONE" ] && echo "★ DONE 已到点停链"
[ -f "$G/ALERT" ] && { echo "★★ ALERT：$(cat "$G/ALERT")"; }
echo "=== 定时器 ==="
for t in aios-watchdog.timer aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer aios-goal-stop.timer; do
  printf '%-26s %s/%s\n' "$t" "$(systemctl is-enabled "$t" 2>&1)" "$(systemctl is-active "$t" 2>&1)"
done
echo "=== 7 单元 ==="
for u in aios-bus aios-ontology aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do
  printf '%-26s %s\n' "$u" "$(systemctl is-active "$u" 2>&1)"
done
echo "=== 最近报告 ==="
ls -lt /root/aios-goal-reports/*.md 2>/dev/null | head -5
echo "=== 本地提交（goal/optimize）==="
git -C /root/aios-work log --oneline -8 2>/dev/null | grep -E "goal|optimize" || true
echo "=== 进度尾 ==="
tail -8 "$G/progress.md" 2>/dev/null
echo "=== 连续无进展计数 ==="
cat "$G/noprogress" 2>/dev/null || echo 0
echo "=== 看门狗最近 ==="
tail -3 /var/log/aios-watchdog.jsonl 2>/dev/null
