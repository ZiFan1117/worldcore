#!/bin/bash
# ★ 判据护栏（VM 侧）—— 跑本机 scripts/test/check.py（★ 判据不推：这是 VM 本地副本，不入 git）。
# 用法：bash aios-gate.sh [工作副本]；退出码 = 判据退出码（0 绿 / 1 红 / 2 环境）。
set -u
W=${1:-${AIOS_DSH_WORK:-/root/aios-work}}
cd "$W" || exit 1
if [ ! -f scripts/test/check.py ]; then
  echo "no-tests: $W/scripts/test/check.py 不在（本机拷一份；判据不推）" >&2
  exit 2
fi
# ★ VM 的 /usr/lib/aios 有 sysknife map，host 判据环境没有；为与 host 判定一致，显式清空。
#   （此变量只影响【代码本体是否收 sys 动作】；sys 动作的 required_roles 是另一个真实议题，不在此处改法。）
export AIOS_SYSKNIFE_MAP=""
PYTHONIOENCODING=utf-8 timeout "${AIOS_GATE_TIMEOUT:-600}" \
  python3 scripts/test/check.py > /tmp/aios-gate.log 2>&1
rc=$?
echo "gate_rc=$rc"
tail -3 /tmp/aios-gate.log
grep -a '^\[RED' /tmp/aios-gate.log | head -10
exit "$rc"
