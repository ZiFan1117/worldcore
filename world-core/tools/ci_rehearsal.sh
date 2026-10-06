#!/usr/bin/env bash
# ci_rehearsal.sh —— 在 VM 内**本地预演** GitHub Actions 的 5 个作业
#
# 为什么需要它：
#   1. CI 在 GitHub 远端，一次往返以分钟计；本机 RTT 以秒计。
#   2. 更重要的：**"CI 绿了" 必须能被本地复现**，否则门禁就是一个不可检验的神谕。
#      本项目的地基项之一是"门禁可信"，可信的前提是**可在本地重跑**。
#   3. 2026-09-26 实测：`gh run list` 为空——CI **从未真实运行过**。
#      在那之前，本脚本是唯一的"门禁预演"证据。
#
# ⚠️ 本脚本**不替代** CI：它是同一批命令的本地副本。作业名与
#    `.github/workflows/world-core-gate.yml`（**仓库根**）一一对应，
#    若两者不一致，以工作流为准并回来改本脚本（这是一处必须人工保持同步的耦合）。
#
# 用法（在 VM 内，world-core/ 目录下）：
#   bash tools/ci_rehearsal.sh                 # 全部作业；scope 作业用 HEAD~1 当基线
#   bash tools/ci_rehearsal.sh --base origin/main
#   bash tools/ci_rehearsal.sh --only smoke,unit-test
#
#   # VM 的签出区是 **work-tree-only**（post-receive 用 --git-dir/--work-tree 签出，
#   # 不带 .git），而 CI 的 actions/checkout 是**真仓库**。所以要在本地预演 scope
#   # 作业，必须显式告诉它仓库在哪：
#   bash tools/ci_rehearsal.sh --git-dir /root/world.git --base HEAD~1
#
# 退出码：0 = 全部预演通过；1 = 至少一个作业失败（与 CI 同为阻断式）。
set -uo pipefail

BASE="HEAD~1"
ONLY=""
GITDIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --git-dir) GITDIR="$2"; shift 2 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

# 必须在 world-core 根（含 Cargo.toml）执行
if [ ! -f Cargo.toml ]; then
  echo "✗ 请在 world-core/ 目录下运行本脚本（当前：$(pwd)）" >&2
  exit 2
fi

# 显式 git 目录：让"无 .git 的签出区"也能预演 scope 作业
if [ -n "$GITDIR" ]; then
  export GIT_DIR="$GITDIR"
  export GIT_WORK_TREE="$(cd .. && pwd)"
  echo "[预演] 显式 git 目录：GIT_DIR=$GIT_DIR"
  echo "       GIT_WORK_TREE=$GIT_WORK_TREE"
  echo "       （VM 签出区无 .git；CI 的 actions/checkout 是真仓库，故这只影响本地预演）"
fi

PY=$(command -v python3 || command -v python || true)
FAILED=()
PASSED=()

should_run() {
  [ -z "$ONLY" ] && return 0
  case ",$ONLY," in *",$1,"*) return 0 ;; *) return 1 ;; esac
}

job_header() {
  echo
  echo "══════════════════════════════════════════════════════════════════════"
  echo "  作业：$1"
  echo "══════════════════════════════════════════════════════════════════════"
}

verdict() { # $1=作业名 $2=rc
  if [ "$2" -eq 0 ]; then
    echo "→ [$1] ✅ 通过"
    PASSED+=("$1")
  else
    echo "→ [$1] ❌ 失败（rc=$2）"
    FAILED+=("$1")
  fi
}

# ── J1 smoke：格式 / 静态检查 / 构建 / 骨架冒烟 ────────────────────────
if should_run "smoke"; then
  job_header "smoke（L0 骨架冒烟：S3 门禁）"
  cargo fmt --all -- --check; rc_fmt=$?
  echo "  fmt rc=$rc_fmt"
  cargo clippy --all-targets -- -D warnings; rc_clippy=$?
  echo "  clippy rc=$rc_clippy"
  cargo build --locked; rc_build=$?
  echo "  build rc=$rc_build"
  rm -f ci-smoke.jsonl
  out=$(cargo run --quiet -- --ledger ci-smoke.jsonl check); rc_run=$?
  echo "$out"
  echo "$out" | grep -q READY; rc_grep=$?
  echo "  smoke rc=$rc_run / READY 命中 rc=$rc_grep"
  # ── 与 gate.yml 对齐：新账本必须带摘要链（此前本预演漏了这两条，属预演/工作流漂移）──
  # ⚠ 写进世界的东西必须在出厂本体里声明过（书 §5.3；执行者 `src/ontology_definition/mod.rs::check_concepts`）。
  #   本行原写 `world://ci/probe` ＋ `p`——两个名字都没声明过 ⇒ append rc=2，
  #   下面那条 `grep -q '有摘要链'` 必失败。改成已声明的格子；判据强度不变。
  cargo run --quiet -- --ledger ci-smoke.jsonl append change \
    '{"subject":"world://notice/probe","path":"muted","before":null,"after":true}' >/dev/null 2>&1
  out2=$(cargo run --quiet -- --ledger ci-smoke.jsonl check)
  echo "$out2" | grep -q '有摘要链'; rc_chain=$?
  cargo run --quiet -- --ledger ci-smoke.jsonl --require-chain check >/dev/null 2>&1; rc_req=$?
  echo "  摘要链 rc=$rc_chain / --require-chain rc=$rc_req"
  # ── 系统级验收（TC-037–TC-040）：先自证判定器会红，再跑端到端 ──
  bash tools/system_acceptance.sh --self-test >/dev/null 2>&1; rc_selftest=$?
  bash tools/system_acceptance.sh 2>&1 | tail -4
  rc_sysacc=${PIPESTATUS[0]}
  echo "  系统级验收 自证 rc=$rc_selftest / 端到端 rc=$rc_sysacc"
  rm -f ci-smoke.jsonl ledger.lock
  rc=0
  [ $rc_fmt -ne 0 ] && rc=1
  [ $rc_clippy -ne 0 ] && rc=1
  [ $rc_build -ne 0 ] && rc=1
  [ $rc_run -ne 0 ] && rc=1
  [ $rc_grep -ne 0 ] && rc=1
  [ $rc_chain -ne 0 ] && rc=1
  [ $rc_req -ne 0 ] && rc=1
  [ $rc_selftest -ne 0 ] && rc=1
  [ $rc_sysacc -ne 0 ] && rc=1
  verdict "smoke" $rc
fi

# ── J2 unit-test ─────────────────────────────────────────────────────
if should_run "unit-test"; then
  job_header "unit-test（L1 单元 + 验收测试：S4 门禁）"
  cargo test --locked 2>&1 | tail -14
  verdict "unit-test" "${PIPESTATUS[0]}"
fi

# ── J3 gate-self-test ────────────────────────────────────────────────
if should_run "gate-self-test"; then
  job_header "gate-self-test（门禁工具自测）"
  if [ -z "$PY" ]; then
    echo "✗ 找不到 python3/python —— 与 CI（setup-python 3.12）环境不一致" >&2
    verdict "gate-self-test" 1
  else
    echo "  解释器：$PY ($($PY --version 2>&1))"
    "$PY" tools/ci_self_check.py; rc1=$?
    "$PY" -c "import json,sys; d=json.load(open('.scope-declaration.json',encoding='utf-8')); sys.exit(0 if d.get('allowed') else 1)"; rc2=$?
    echo "  范围声明 JSON 断言 rc=$rc2"
    # --sample = **显式**索取非本项目样例数据做"工具链是否可用"的自证
    #（与 gate.yml 的 gate-self-test 作业逐字一致；样例数据不得作为默认输入，
    #  未显式 --sample 而把输入指到样例目录 ⇒ 工具**直接判不通过**）。
    "$PY" tools/trace_matrix.py --sample; rc3=$?
    "$PY" tools/scope_check.py --demo >/dev/null; rc4=$?
    echo "  scope_check --demo rc=$rc4"
    rc=0
    [ $rc1 -ne 0 ] && rc=1
    [ $rc2 -ne 0 ] && rc=1
    [ $rc3 -ne 0 ] && rc=1
    [ $rc4 -ne 0 ] && rc=1
    verdict "gate-self-test" $rc
  fi
fi

# ── J4 traceability（与 gate.yml 同一套分支逻辑）──────────────────────
if should_run "traceability"; then
  job_header "traceability（RTM 追溯门禁：S1/S5/S6）"
  SRS="docs/S1-需求/WC-SRS-001-v0.1.md"
  RTM="docs/S1-需求/WC-RTM-001.csv"

  # 阶段开关**从工作流本身读取**，不在这里另写一份。
  # 教训（2026-09-26 实测踩到）：本脚本原先把 --strict 硬编码在 J4 里，
  # 工作流改成阶段开关 RTM_STRICT 后本脚本没跟着改 —— 于是**预演红、CI 绿**，
  # 预演脚本自己变成了"说两种话"的那一个。凡是"同一个判定"，就必须只有一个来源。
  WF="../.github/workflows/world-core-gate.yml"
  RTM_STRICT=$(grep -E '^[[:space:]]*RTM_STRICT:' "$WF" 2>/dev/null | head -1 |
               sed -E 's/.*RTM_STRICT:[[:space:]]*"?([A-Za-z]+)"?.*/\1/')
  if [ -z "$RTM_STRICT" ]; then
    echo "[告警] 无法从 $WF 读到 RTM_STRICT —— 按非严格模式预演。"
    echo "        （该常量缺失本身应由 gate-self-test 的 check_phase_switch 拦下）"
    RTM_STRICT="false"
  fi
  STRICT=""
  [ "$RTM_STRICT" = "true" ] && STRICT="--strict"
  echo "  追溯门禁强度：RTM_STRICT=${RTM_STRICT}（STRICT='${STRICT}'）"

  if [ -z "$PY" ]; then
    verdict "traceability" 1
  elif [ -f "$RTM" ]; then
    "$PY" tools/trace_matrix.py --matrix "$RTM" --srs "$SRS" $STRICT; rc=$?
    verdict "traceability" $rc
  elif [ -f "$SRS" ]; then
    echo "::error::SRS 已存在但 RTM 缺失 —— S1 未完成，追溯门禁不通过"
    verdict "traceability" 1
  else
    echo "[告警] S1 尚未开始（无 SRS/RTM）—— 追溯门禁在 S1 前不适用。"
    echo "        S1 产出 WC-RTM-001.csv 后本作业自动强制生效；不得改为静默跳过。"
    verdict "traceability" 0
  fi
fi

# ── J5 scope（CI 里仅 PR 触发；本地用 --base 模拟）────────────────────
if should_run "scope"; then
  job_header "scope（改动范围门禁；CI 中仅 PR 触发）"
  echo "  模拟基线：$BASE"
  if [ -z "$PY" ]; then
    verdict "scope" 1
  else
    "$PY" tools/scope_check.py --base "$BASE" --scope .scope-declaration.json; rc=$?
    if [ $rc -eq 2 ] && [ -z "$GITDIR" ]; then
      echo
      echo "  提示：rc=2 表示 *未能校验*（不是通过）。此目录没有 .git，"
      echo "        而 VM 的签出区本就是 work-tree-only —— 加 --git-dir /root/world.git 重跑，"
      echo "        即可真正预演 CI 里 scope 作业（CI 的 actions/checkout 是真仓库）。"
    fi
    verdict "scope" $rc
  fi
fi

# ── 汇总 ─────────────────────────────────────────────────────────────
echo
echo "══════════════════════════════════════════════════════════════════════"
echo "  预演汇总"
echo "══════════════════════════════════════════════════════════════════════"
echo "  通过 ${#PASSED[@]} 项：${PASSED[*]:-（无）}"
echo "  失败 ${#FAILED[@]} 项：${FAILED[*]:-（无）}"
echo
echo "  ⚠️ 本预演与 GitHub Actions **共用同一批命令，但不是同一个环境**："
echo "     CI 为 ubuntu-latest + setup-python 3.12；此处为 VM ($(uname -sr)) + $($PY --version 2>&1)。"
echo "     两者结论不一致时，以真实 CI 为准，并把差异登记为环境类风险。"
if [ ${#FAILED[@]} -ne 0 ]; then
  echo
  echo "  结论：❌ 不通过 —— 修好再推送（推送后 CI 只会更晚告诉你同一件事）"
  exit 1
fi
echo
echo "  结论：✅ 全部预演通过"
exit 0
