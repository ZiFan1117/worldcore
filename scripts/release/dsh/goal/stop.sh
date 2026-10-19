#!/bin/bash
# ★ 到点强制停链（独立于单轮脚本，防它自己忘了停）
set -u
systemctl stop aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer 2>/dev/null || true
echo "## $(date -Is) 到点（06:00 Asia/Shanghai）→ 已强制停止 目标/自优化/进化 三条定时器" >> /root/aios-goals/progress.md
echo "stopped" > /root/aios-goals/DONE
