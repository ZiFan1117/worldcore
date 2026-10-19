#!/bin/bash
# 装「限时目标」链（幂等）。★ 到点停靠 aios-goal-stop.timer；单轮脚本也会自检截止。
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
install -d /root/aios-goals /root/aios-goal-reports
install -m 755 "$HERE/run.sh" /usr/local/bin/aios-goal-run.sh
install -m 755 "$HERE/stop.sh" /usr/local/bin/aios-goal-stop.sh
install -m 755 "$HERE/status.sh" /usr/local/bin/aios-goal-status.sh
# 截止时刻：2026-10-20 06:00 Asia/Shanghai（绝对 epoch，与 VM 时区无关）
date -d '2026-10-20 06:00 +0800' +%s > /root/aios-goals/deadline.epoch
install -m 644 "$HERE/goal.md" /root/aios-goals/goal.md
install -m 644 "$HERE/research.md" /root/aios-goals/research.md
install -m 644 "$HERE/board.md" /root/aios-goals/board.md
install -m 644 "$HERE/aios-dsh-goal.service" "$HERE/aios-dsh-goal.timer" \
               "$HERE/aios-goal-stop.service" "$HERE/aios-goal-stop.timer" \
               /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now aios-dsh-goal.timer aios-goal-stop.timer
echo "deadline=$(cat /root/aios-goals/deadline.epoch) => $(date -d @"$(cat /root/aios-goals/deadline.epoch)" -Is)"
systemctl list-timers 'aios-dsh-goal.timer' 'aios-goal-stop.timer' --no-pager | head -4
