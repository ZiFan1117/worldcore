#!/bin/bash
# ★ worldcore「自优化」agent 的一轮 —— 给 DSH 高权限，但**先快照、后验收、坏了回滚**。
# 每 12 小时一轮；产物：/root/aios-optimize-reports/<stamp>.md；改动只 commit 在本地仓，绝不 push。
set -euo pipefail
export PATH=/opt/nodejs/bin:${PATH}
if [ -f /root/.dsh/env.dsh ]; then set -a; . /root/.dsh/env.dsh; set +a; fi

WORK=${AIOS_DSH_WORK:-/root/aios-work}
OUTDIR=${AIOS_OPTIMIZE_REPORTS:-/root/aios-optimize-reports}
BACKUP_DIR=/var/backups/aios
STAMP=$(date +%Y%m%d-%H%M%S)
SNAP="$BACKUP_DIR/pre-optimize-$STAMP.tar.gz"
mkdir -p "$OUTDIR" "$BACKUP_DIR"
cd "$WORK"
git checkout -q -- . 2>/dev/null || true
git clean -qfd 2>/dev/null || true
git config user.name "DSH Optimizer" 2>/dev/null || true
git config user.email "dsh-optimizer@aios.local" 2>/dev/null || true
git tag -f "pre-optimize-$STAMP" >/dev/null 2>&1 || true

# ① 快照（被改的东西：部署代码、仓、profile、单元）
tar -czf "$SNAP" \
  /root/aios/src /usr/lib/aios/src /root/.dsh/profiles \
  /etc/systemd/system/aios-*.service /etc/systemd/system/aios-*.timer \
  >/dev/null 2>&1 || true

TASK="你是 worldcore 的『环境自优化工程师』，拥有本机 root 权限。目标：让这个世界更稳、更省、更可维护。
★ 铁律（违反即失败）：
- 绝不 git push；绝不关 aios-bus；绝不 rm -rf /；不动 /etc/passwd、/etc/shadow；不把自己（DSH）删掉。
- 一次只做【一处最小、可验证】的改进；没有明确收益就【只写报告、不动手】。
- 改完必须跑：python3 scripts/release/export-law.py --check（改法时）和 systemctl is-active aios-*（改环境时）。
- 所有改动提交到本地 git（不 push）；报告写到 $WORK/reports/$STAMP.md，最后只输出一行 report=reports/$STAMP.md。
体检顺序：① systemctl status aios-* 与 journalctl -u aios-* 最近错误；② 账本 /var/lib/aios/ontology/ledger.jsonl 最近 300 行的拒绝码；
③ 磁盘/内存/负载；④ /root/.dsh 的 profile 与脚本；⑤ 本体 world.json 的一致性。"
timeout "${AIOS_OPTIMIZE_TIMEOUT:-1800}" dsh --profile optimize "$TASK" > "$OUTDIR/$STAMP.log" 2>&1 || true

# ② 验收
bad=""
LAW=$(PYTHONIOENCODING=utf-8 python3 /root/aios/scripts/release/export-law.py --check 2>&1 | tail -1)
echo "$LAW" | grep -q "一致" || bad="$bad law-check-failed"
for u in aios-bus aios-ontology aios-space aios-presentation aios-presentation-render aios-agent aios-computer; do
  systemctl is-active --quiet "$u" || bad="$bad $u-down"
done

if [ -n "$bad" ]; then
  echo "验收红：$bad → 回滚" | tee -a "$OUTDIR/$STAMP.log"
  cd "$WORK" && git reset --hard -q "pre-optimize-$STAMP" 2>/dev/null || true
  git clean -qfd 2>/dev/null || true
  if [ -f "$SNAP" ]; then tar -xzf "$SNAP" -C / >/dev/null 2>&1 || true; fi
  systemctl daemon-reload >/dev/null 2>&1 || true
  for u in aios-ontology aios-space aios-presentation aios-presentation-render aios-agent; do
    systemctl restart "$u" >/dev/null 2>&1 || true
  done
  systemctl stop aios-dsh-optimize.timer >/dev/null 2>&1 || true
  echo "incident=$bad at=$STAMP; optimize timer 已停，等人看" | tee -a "$OUTDIR/$STAMP.log"
  exit 1
fi

# ③ 成功：报告搬出工作区；本地提交（绝不 push）
if [ -f "$WORK/reports/$STAMP.md" ]; then mv "$WORK/reports/$STAMP.md" "$OUTDIR/$STAMP.md"; fi
rmdir "$WORK/reports" 2>/dev/null || true
cd "$WORK"
git add -A >/dev/null 2>&1 || true
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -q -m "dsh optimize $STAMP（本地提交，未推送）" >/dev/null 2>&1 || true
fi
echo "optimize=$STAMP report=$OUTDIR/$STAMP.md backup=$SNAP"
