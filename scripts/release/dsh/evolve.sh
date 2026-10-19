#!/bin/bash
# ★ AI-OS DSH「本体进化」循环 —— ★ 只提案，不落法、不改仓库、不提交、不推送。
# 由 aios-dsh-evolve.timer 定时调用；产物在 /root/aios-proposals/<stamp>.md。
set -euo pipefail
export PATH=/opt/nodejs/bin:${PATH}
if [ -f /root/.dsh/env.dsh ]; then set -a; . /root/.dsh/env.dsh; set +a; fi

WORK=${AIOS_DSH_WORK:-/root/aios-work}
OUTDIR=${AIOS_DSH_PROPOSALS:-/root/aios-proposals}
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUTDIR"
cd "$WORK"
git checkout -q -- . 2>/dev/null || true
git clean -qfd 2>/dev/null || true

TASK="你是 AI-OS 本体的『进化工程师』。只做【提案】，绝对不改仓库、不提交、不推送。
步骤：
1) 读 $WORK/src/ontology/world.json（法的全文）；
2) 读 /var/lib/aios/ontology/ledger.jsonl 的最后 300 行（只做统计，别贴票据明文）；
3) 从账里真实发生的问题出发，找 1 个最小、可验证的本体改进（缺的前置条件/接口/动作描述/参数约束）；
4) 把提案写到 $WORK/proposals/$STAMP.md，内容必须含：动机（引用账里哪几行/哪个拒绝码）、改哪个文件哪个动作、diff、风险、验证命令（python3 scripts/release/export-law.py --check）、是否触及『只有人定法』（是/否）；
不要改 $WORK 里的任何既有文件；最后只输出一行：proposal=proposals/$STAMP.md"

timeout "${AIOS_DSH_TIMEOUT:-900}" dsh --profile evolve "$TASK" > "$OUTDIR/$STAMP.log" 2>&1 || true

if [ -f "$WORK/proposals/$STAMP.md" ]; then
  mv "$WORK/proposals/$STAMP.md" "$OUTDIR/$STAMP.md"
fi
rmdir "$WORK/proposals" 2>/dev/null || true
cd "$WORK"
git checkout -q -- . 2>/dev/null || true
git clean -qfd 2>/dev/null || true
if [ -f "$OUTDIR/$STAMP.md" ]; then
  echo "proposal=$OUTDIR/$STAMP.md"
else
  echo "proposal=（本轮没产出；日志 $OUTDIR/$STAMP.log）"
fi
