#!/bin/bash
# ★ AI-OS 限时目标的一轮：高权限自优化，带快照/验收/回滚/进度/到点停。
set -uo pipefail
export PATH=/opt/nodejs/bin:${PATH}
if [ -f /root/.dsh/env.dsh ]; then set -a; . /root/.dsh/env.dsh; set +a; fi

exec 9>/run/aios-goal.lock
flock -n 9 || { echo "another round running"; exit 0; }

WORK=${AIOS_DSH_WORK:-/root/aios-work}
GOALDIR=/root/aios-goals
OUTDIR=/root/aios-goal-reports
BACKUP_DIR=/var/backups/aios
STAMP=$(date +%Y%m%d-%H%M%S)
DEADLINE=$(cat "$GOALDIR/deadline.epoch" 2>/dev/null || echo 0)
mkdir -p "$GOALDIR" "$OUTDIR" "$BACKUP_DIR"
now=$(date +%s)

finish_all() {
  echo "$1" | tee -a "$GOALDIR/progress.md"
  systemctl stop aios-dsh-goal.timer aios-dsh-optimize.timer aios-dsh-evolve.timer 2>/dev/null || true
}

# ① 到点：必须停
if [ "$now" -ge "$DEADLINE" ]; then
  finish_all "## $(date -Is) 到点，全部停链（本轮不跑）"
  exit 0
fi

# ② 快照
cd "$WORK" || exit 1
git checkout -q -- . 2>/dev/null || true
git clean -qfd 2>/dev/null || true
git config user.name "DSH Goal Agent" 2>/dev/null || true
git config user.email "dsh-goal@aios.local" 2>/dev/null || true
SNAP="$BACKUP_DIR/pre-goal-$STAMP.tar.gz"
tar -czf "$SNAP" /root/aios/src /usr/lib/aios/src /root/.dsh/profiles \
  /etc/systemd/system/aios-*.service /etc/systemd/system/aios-*.timer >/dev/null 2>&1 || true
git tag -f "pre-goal-$STAMP" >/dev/null 2>&1 || true

# ③ 拼这一轮的任务（含上一轮进度与「没进展就诊断」）
LAST=$(tail -5 "$GOALDIR/progress.md" 2>/dev/null || true)
TASK="你在执行一个限时目标（截止 epoch=$DEADLINE，当前 $(date -Is)）。目标文件：$GOALDIR/goal.md（先读它）；
外部研究：$GOALDIR/research.md；商量板：$GOALDIR/board.md（每轮结束把你的结论/问题追加进 board）。
上一轮进度（读它，别重复）：$LAST
本轮要求：
1) 先体检：journalctl -u aios-* -n 120 的真实错误；账本最后 300 行拒绝码统计；磁盘/内存/负载；world.json 与 export-law --check；
2) 只做【一处最小、可验证】的改进；如果找不到明确收益，就只写报告、不动手（如实写为什么）；
3) 若上一轮没有实质进展：先诊断「为什么没执行/没做成」，把诊断写进报告，并修掉那个原因（这是本轮的第一优先级）；
4) 改法必须过 python3 scripts/release/export-law.py --check；改环境必须 systemctl is-active 全绿；
5) 报告写到 $WORK/reports/$STAMP.md（含：证据行号/拒绝码、改了什么、怎么验、回滚点、是否达到目标）；
6) 绝对禁止：git 推（push）、关 aios-bus、rm -rf /、改密码、删 DSH；改完提交本地 git（不 push）。
最后只输出一行：report=reports/$STAMP.md"
timeout "${AIOS_GOAL_TIMEOUT:-1800}" dsh --profile optimize "$TASK" > "$OUTDIR/$STAMP.log" 2>&1 || true

# ④ 验收
bad=""
LAW=$(PYTHONIOENCODING=utf-8 python3 /root/aios/scripts/release/export-law.py --check 2>&1 | tail -1)
echo "$LAW" | grep -q "一致" || bad="$bad law-check-failed"
for u in aios-bus aios-ontology aios-space aios-presentation aios-presentation-render aios-agent aios-computer; do
  systemctl is-active --quiet "$u" || bad="$bad $u-down"
done

if [ -n "$bad" ]; then
  echo "## $(date -Is) 验收红：$bad → 回滚并停目标链" >> "$GOALDIR/progress.md"
  cd "$WORK" && git reset --hard -q "pre-goal-$STAMP" 2>/dev/null || true
  git clean -qfd 2>/dev/null || true
  [ -f "$SNAP" ] && tar -xzf "$SNAP" -C / >/dev/null 2>&1
  systemctl daemon-reload >/dev/null 2>&1 || true
  for u in aios-ontology aios-space aios-presentation aios-presentation-render aios-agent; do
    systemctl restart "$u" >/dev/null 2>&1 || true
  done
  finish_all "## $(date -Is) INCIDENT：$bad（已回滚）"
  rm -f "$GOALDIR/ALERT"
  echo "incident=$bad stamp=$STAMP" > "$GOALDIR/ALERT"
  exit 1
fi

# ⑤ 成功：报告搬出、本地提交、记进度
[ -f "$WORK/reports/$STAMP.md" ] && mv "$WORK/reports/$STAMP.md" "$OUTDIR/$STAMP.md"
rmdir "$WORK/reports" 2>/dev/null || true
cd "$WORK"
git add -A >/dev/null 2>&1 || true
CHANGED=0
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -q -m "goal $STAMP（本地提交，未推送）" >/dev/null 2>&1 || true
  CHANGED=1
fi
echo "## $(date -Is) round=$STAMP changed=$CHANGED report=$OUTDIR/$STAMP.md" >> "$GOALDIR/progress.md"

# ⑥ 连续无进展计数（没执行/没改东西）→ 停链等人
N=$(cat "$GOALDIR/noprogress" 2>/dev/null || echo 0)
if [ "$CHANGED" -eq 0 ] && [ ! -f "$OUTDIR/$STAMP.md" ]; then
  N=$((N + 1))
else
  N=0
fi
echo "$N" > "$GOALDIR/noprogress"
if [ "$N" -ge 3 ]; then
  # ★ 作者令「不要停」：无进展也不停链，只写 ALERT，下一轮任务里会自动进入「为什么没做成」诊断
  echo "## $(date -Is) 连续 $N 轮无进展 → 继续跑（ALERT，不停链；下轮先诊断原因）" >> "$GOALDIR/progress.md"
  echo "no_progress=$N stamp=$STAMP" > "$GOALDIR/ALERT"
fi
