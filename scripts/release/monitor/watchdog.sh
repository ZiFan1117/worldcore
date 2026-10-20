#!/bin/bash
# ★ AI-OS 看门狗 —— 只做一件事：别让（自优化的）系统自己跑崩。
# 每 3 分钟一次：
#   ① 9 个单元都活着（掉了就重启，记下来；2026-10-20 加 guard/web）
#   ② 本体还能装起来（export-law --check；坏了就用 last-good 快照恢复）
#   ③ 磁盘/内存/负载不越线
#   ④ 进化/自优化定时器没连环失败（失败就停 timer，等人看）
# 输出：/var/log/aios-watchdog.log（人看）＋ /var/log/aios-watchdog.jsonl（一行一读数）
set -uo pipefail

UNITS="aios-bus aios-ontology aios-guard aios-web aios-computer aios-presentation aios-presentation-render aios-space aios-agent aios-fs aios-clock aios-recovery aios-network aios-vault"
LOG=/var/log/aios-watchdog.log
JSONL=/var/log/aios-watchdog.jsonl
BACKUP_DIR=/var/backups/aios
SNAP="$BACKUP_DIR/lastgood.tar.gz"
TS=$(date -Is)
fail=0
notes=""

say() { echo "[$(date -Is)] $*" | tee -a "$LOG" >>/dev/null; }
mark() { notes="$notes; $*"; fail=1; }

# ① 单元（★ 掉线被拉起 = 记一笔但【不算失败】；只有拉不起来才算红）
for u in $UNITS; do
  if ! systemctl is-active --quiet "$u"; then
    say "单元 $u 不活 → 重启"
    systemctl restart "$u" >/dev/null 2>&1 || true
    sleep 3
    if systemctl is-active --quiet "$u"; then
      notes="$notes; 已拉起 $u"
    else
      mark "unit $u 重启后仍不活"
    fi
  fi
done

# ② 本体还装得起来
LAW_OUT=$(PYTHONIOENCODING=utf-8 python3 /root/aios/scripts/release/export-law.py --check 2>&1 | tail -1)
if ! echo "$LAW_OUT" | grep -q "一致"; then
  mark "law check FAILED: $LAW_OUT"
  say "本体装不起来 → 用 last-good 快照恢复（$SNAP）"
  if [ -f "$SNAP" ]; then
    tar -xzf "$SNAP" -C / >/dev/null 2>&1 || mark "快照恢复失败"
    systemctl daemon-reload >/dev/null 2>&1 || true
    for u in aios-ontology aios-guard aios-web aios-space aios-presentation aios-presentation-render aios-agent aios-fs; do
      systemctl restart "$u" >/dev/null 2>&1 || true
    done
    sleep 3
    systemctl is-active --quiet aios-ontology || mark "恢复后本体仍不活"
  else
    mark "没有 last-good 快照，无法恢复"
  fi
fi

# ②b ★ 目标脚本完整性（2026-10-20 事故）：agent 自改可能把 goal-run 写坏 ⇒ bash -n 不过就从 /root/aios 恢复
if ! bash -n /usr/local/bin/aios-goal-run.sh 2>/dev/null; then
  say "goal-run 语法坏了 → 从 /root/aios 恢复"
  if [ -f /root/aios/scripts/release/dsh/goal/run.sh ]; then
    cp /root/aios/scripts/release/dsh/goal/run.sh /usr/local/bin/aios-goal-run.sh
    chmod 755 /usr/local/bin/aios-goal-run.sh
    restorecon /usr/local/bin/aios-goal-run.sh 2>/dev/null || true
    bash -n /usr/local/bin/aios-goal-run.sh 2>/dev/null && notes="$notes; goal-run 已恢复" || mark "goal-run 恢复后语法仍坏"
  else
    mark "goal-run 语法坏且没有恢复源"
  fi
fi
if ! bash -n /usr/local/bin/aios-gate.sh 2>/dev/null; then
  say "gate 语法坏了 → 从 /root/aios 恢复"
  if [ -f /root/aios/scripts/release/dsh/goal/gate.sh ]; then
    cp /root/aios/scripts/release/dsh/goal/gate.sh /usr/local/bin/aios-gate.sh
    chmod 755 /usr/local/bin/aios-gate.sh
    restorecon /usr/local/bin/aios-gate.sh 2>/dev/null || true
    notes="$notes; gate 已恢复"
  else
    mark "gate 语法坏且没有恢复源"
  fi
fi

# ③ 资源
DISK=$(df --output=pcent / | tail -1 | tr -dc '0-9')
MEM=$(free -m | awk '/^Mem:/{print $7}')
if [ "${DISK:-100}" -ge 95 ]; then mark "disk ${DISK}%"; fi
if [ "${MEM:-0}" -lt 200 ]; then mark "mem avail ${MEM}MB"; fi

# ④ 定时器失败（连续失败 = 别让它继续跑）
for t in aios-dsh-evolve.timer aios-dsh-optimize.timer aios-dsh-goal.timer; do
  if systemctl is-enabled --quiet "$t" 2>/dev/null; then
    svc=${t%.timer}.service
    st=$(systemctl show -p ActiveState --value "$svc" 2>/dev/null || echo "")
    rc=$(systemctl show -p ExecMainStatus --value "$svc" 2>/dev/null || echo "")
    if [ "$st" = "failed" ] && [ "${rc:-0}" != "0" ]; then
      mark "timer $t 的上一轮失败 rc=$rc"
      say "停掉 $t（等人看）"
      systemctl stop "$t" >/dev/null 2>&1 || true
    fi
  fi
done

# 成功 → 每小时刷新一次 last-good 快照
if [ "$fail" -eq 0 ]; then
  mkdir -p "$BACKUP_DIR"
  if [ ! -f "$SNAP" ] || [ $(( $(date +%s) - $(stat -c %Y "$SNAP" 2>/dev/null || echo 0) )) -gt 3600 ]; then
    tar -czf "$SNAP" \
      /root/aios/src /usr/lib/aios/src /root/.dsh/profiles \
      /etc/systemd/system/aios-*.service /etc/systemd/system/aios-*.timer \
      >/dev/null 2>&1 || mark "快照失败"
  fi
fi

if [ "$fail" -ne 0 ]; then
  say "红：$notes → 停掉进化/自优化定时器，等人看"
  systemctl stop aios-dsh-evolve.timer aios-dsh-optimize.timer >/dev/null 2>&1 || true
fi
printf '{"at":"%s","fail":%d,"notes":%s,"units_ok":%d,"disk":%s,"mem_avail":%s,"law":"%s"}\n' \
  "$TS" "$fail" "$(printf '%s' "$notes" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')" \
  "$(for u in $UNITS; do systemctl is-active --quiet "$u" && echo 1; done | wc -l)" \
  "${DISK:-?}" "${MEM:-?}" "$(echo "$LAW_OUT" | sed 's/"/\\"/g')" >> "$JSONL"
[ -s "$LOG" ] && tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
exit "$fail"
