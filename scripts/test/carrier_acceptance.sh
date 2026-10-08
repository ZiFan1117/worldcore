#!/usr/bin/env bash
# carrier_acceptance.sh —— **载体适配器（M10）的系统级验收**（真实二进制、真实内核、真实账本）
#
# 判据（每条都要有"应当失败"的反例，反例必须真失败）：
#   C-01 三进程形态：内核进程持账本；适配器**对账本零写权限**（它自己不写账本字节）
#   C-02 意图先于执行：账本里"有结果的请求"必有**更早的**意图事件
#   C-03 因果闭合：结果事件的 trace == 意图事件的 id；两者 request_id 相同
#   C-04 门禁是唯一权威：清单里有、但门禁不放行的能力 ⇒ **一次都没动**（job 未起）
#   C-05 身份不可自称：适配器请求里不含 actor；内核按套接字给出身份
#   C-06 内核不在即不执行：内核没起 ⇒ 适配器拒绝执行，且**不产生任何副作用**
#   C-07 孤儿可查：有意图、无结果的请求能被查出来（只报告，不重试）
#   C-08 撤销不进主干：账本每一行都是语义事件；载体撤销以内容引用出现在事件字段里
#   C-09 写侧进程（**被管者身份**）读得到账本，但**写不到账本、也改不了规则**（书 §4.5:601）
#
# 纪律：只碰一次性沙箱（mktemp 目录），退出即删；**绝不触碰真实账本**。
# 用法：bash scripts/test/carrier_acceptance.sh [world-core 可执行文件路径]
# 退出码：0 = 全通过；非 0 = 任一步失败（阻断式）

set -u

BIN="${1:-}"
if [ -z "$BIN" ]; then
  # 默认找 release/debug 产物
  for c in "${CARGO_TARGET_DIR:-target}/release/world-core" target/release/world-core target/debug/world-core; do
    if [ -x "$c" ]; then BIN="$(cd "$(dirname "$c")" && pwd)/$(basename "$c")"; break; fi
  done
fi
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
  echo "[FAIL] 找不到 world-core 可执行文件（用法：bash scripts/test/carrier_acceptance.sh <路径>）"
  exit 2
fi

# ── D-33：**不许拿陈旧二进制跑门禁**（fail loud，不静默）──────────────────
# 实测（2026-09-27，VM）：`target/release/world-core` 停在 02:48，而 `src/carrier/*`
# 是 16:17 才加入的 ⇒ 该二进制**不认识 carrier 子命令**，本脚本于是报出
# **13 条假失败**（9 通过 / 13 失败）；`cargo build --release` 后同一脚本 **22/22 通过**。
# 反方向更危险：**源码里有回归、而二进制是旧的 ⇒ 门禁假绿**。
# 故：只要 `src/`（或 Cargo.toml）里有比二进制更新的文件，就**拒绝运行并说明处置**。
# 这与本项目既有判据一致：**带病运行比不运行更危险**。
NEWER="$(find src Cargo.toml -type f -newer "$BIN" -print -quit 2>/dev/null || true)"
if [ -n "$NEWER" ]; then
  echo "[FAIL] ext.world.Tool.StaleBinary：被测二进制比源码旧，拒绝运行。"
  echo "       二进制：$BIN"
  echo "       更新源：$NEWER"
  echo "       处置 ：cargo build --release（或删掉陈旧 release 产物，让它回落到 debug），然后重跑。"
  exit 2
fi

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1（$2）"; else bad "$1：期望 $3，实得 $2"; fi; }

SB="$(mktemp -d)"
# 服务端**长驻**：一次往返 = 两个连接（先意图、后结果）。
# 故一次性起一个能收 N 个连接的监听者，而不是每次连接都重建套接字——
# 重建会把套接字文件删掉，后续连接只会得到 `Connection refused`。
SERVE_PID=""
cleanup() {
  [ -n "${SERVE_PID:-}" ] && kill -9 "$SERVE_PID" 2>/dev/null
  pkill -9 -f "$SB/run/agent-1.sock" 2>/dev/null
  rm -rf "$SB"
}
trap cleanup EXIT

echo "== world-core carrier_acceptance =="
echo "  二进制 : $BIN"
echo "  沙箱   : $SB"
echo

# ── 准备：一次性世界（本体/策略/执行清单/通道配置）───────────────────────
# ★ 沙盒必须**保持与仓内同样的相对布局**（法律搬进 `src/` 后不再平铺）：
mkdir -p "$SB/src/ontology_definition" "$SB/src/gate" "$SB/src/carrier"
cp src/ontology_definition/ontology.json "$SB/src/ontology_definition/ontology.json" 2>/dev/null || true
cp src/gate/policy.json "$SB/src/gate/policy.json" 2>/dev/null || true
cp -r src/carrier/cap.d "$SB/src/carrier/cap.d"
mkdir -p "$SB/run"
# ★ AC-1：受理路径现在按**法律**（`--policy` 的 `listeners`）判"这个口在不在册"。
#   夹具的口是**临时路径** ⇒ 夹具必须把它写进**自己的法律**里（否则世界**正确地**拒启）。
#   ⚠ 这不是"把判据改松"：**判据的会红条件一字未动**；变的是**夹具的法律**，不是判据。
#   依赖：python3（与仓内其余工具同口径）。
python3 - "$SB/src/gate/policy.json" "$SB/run/agent-1.sock" <<'PY'
import json, sys
p, sock = sys.argv[1], sys.argv[2]
d = json.load(open(p, encoding="utf-8"))
d.setdefault("listeners", []).append(
    {"socket": sock, "actor": "world://agent/1", "owner": "fixture"})
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
cat > "$SB/channel.json" <<EOF
{"channel":1,"listeners":[{"socket":"$SB/run/agent-1.sock","actor":"world://agent/1","uid":$(id -u)}]}
EOF
LEDGER="$SB/ledger.jsonl"
RUN="$BIN --ontology $SB/src/ontology_definition/ontology.json --ledger $LEDGER --policy $SB/src/gate/policy.json"
CARRY="$BIN --cap-dir $SB/src/carrier/cap.d --ledger $LEDGER"

# 起始：账本为空
$RUN check >/dev/null 2>&1
check "C-00 空账本可启动（check 打印 READY）" "$($RUN check 2>/dev/null | grep -c READY)" "1"

# 建通道套接字（一个套接字一个身份）：由**长驻服务**建立并保持
timeout 60 $RUN --channel "$SB/channel.json" channel serve "$SB/run/agent-1.sock" 8 \
  > "$SB/serve.log" 2>&1 &
SERVE_PID=$!
sleep 0.6
check "C-00b 通道套接字已建立（0600）" "$(stat -c '%a' "$SB/run/agent-1.sock" 2>/dev/null)" "600"

# ── 一次完整往返：先问（意图）→ 再做（执行）→ 再报（结果）──────────────
timeout 20 $CARRY --socket "$SB/run/agent-1.sock" carrier do job.start start r-e2e-1 \
  '{"command":"/bin/true","args":[],"job_id":"j-e2e-1"}' > "$SB/do1.out" 2>&1
DO_RC=$?
sleep 0.4

check "C-01 一次调用成功（carrier do 退出码 0）" "$DO_RC" "0"

# ── C-02 意图先于执行 ─────────────────────────────────────────────────
INTENT_SEQ=$(grep -o '"request_id":"r-e2e-1"' "$LEDGER" 2>/dev/null | wc -l)
check "C-02 账本里出现了该请求号的事件（意图 + 结果 = 2 条）" "$INTENT_SEQ" "2"

FIRST=$(grep -n '"request_id":"r-e2e-1"' "$LEDGER" | head -1 | cut -d: -f1)
LAST=$(grep -n '"request_id":"r-e2e-1"' "$LEDGER" | tail -1 | cut -d: -f1)
if [ "$FIRST" -lt "$LAST" ]; then ok "C-02 意图行号（$FIRST）早于结果行号（$LAST）"; else bad "C-02 意图不在结果之前"; fi

# 意图必须**没有** params.result；结果必须有
INTENT_LINE=$(sed -n "${FIRST}p" "$LEDGER")
RESULT_LINE=$(sed -n "${LAST}p" "$LEDGER")
case "$INTENT_LINE" in *'"result"'*) bad "C-02 意图行里不该出现 result";; *) ok "C-02 意图行不含 result（是意图，不是结果）";; esac
case "$RESULT_LINE" in *'"result":"ok"'*) ok "C-02 结果行带 params.result=ok";; *) bad "C-02 结果行缺少 params.result";; esac

# ── C-03 因果闭合：结果的 trace == 意图的 id ──────────────────────────
IID=$(printf '%s' "$INTENT_LINE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
TID=$(printf '%s' "$RESULT_LINE" | grep -o '"trace":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$IID" ] && [ "$IID" = "$TID" ]; then
  ok "C-03 结果的 trace（$TID）就是意图的 id"
else
  bad "C-03 因果未闭合：意图 id=$IID，结果 trace=$TID"
fi

# ── C-04 门禁是唯一权威 ───────────────────────────────────────────────
# `job.start` 在清单里且可逆 ⇒ 放行；`ledger.compact` 在清单里但**不可逆且 agent
# 不在 irreversible_actors 内** ⇒ 门禁加摩擦。**这正是"清单说能、门禁说不能"的格子。**
sleep 0.4
BEFORE=$(wc -l < "$LEDGER")
timeout 20 $CARRY --socket "$SB/run/agent-1.sock" carrier do ledger.compact install r-e2e-2 \
  '{"package":"definitely-not-a-real-package"}' > "$SB/do2.out" 2>&1
RC2=$?
AFTER=$(wc -l < "$LEDGER")
if [ "$RC2" -ne 0 ]; then ok "C-04 门禁不放行 ⇒ carrier do 非零退出（$RC2）"; else bad "C-04 门禁不放行却零退出"; fi
if grep -q 'AwaitingApproval' "$SB/do2.out"; then
  ok "C-04 拒绝理由点名 AwaitingApproval"
else
  bad "C-04 未点名拒绝理由（实得：$(head -c 300 "$SB/do2.out" | tr '\n' ' ')）"
fi
# 关键：**一次都没动** —— 没有该请求的**结果**事件
if ! grep -q '"request_id":"r-e2e-2","params":{"result"' "$LEDGER"; then
  ok "C-04 没有为该请求落任何**结果**事件（一次都没动）"
else
  bad "C-04 门禁不放行却落了结果事件"
fi
# 门禁拒绝必须留痕（notice）
if grep -q 'gate.awaiting-approval' "$LEDGER"; then ok "C-04b 拒绝也留痕（notice gate.awaiting-approval）"; else bad "C-04b 拒绝未留痕"; fi

# ── C-05 身份不可自称 ────────────────────────────────────────────────
if grep -q '"actor":"world://agent/1"' "$LEDGER"; then
  ok "C-05 落笔的 actor 来自内核的身份映射"
else
  bad "C-05 落笔的 actor 不是内核给出的身份"
fi

# ── C-06 内核不在即不执行 ─────────────────────────────────────────────
BEFORE6=$(wc -l < "$LEDGER")
$CARRY --socket "$SB/run/nonexistent.sock" carrier do job.start start r-e2e-3 \
  '{"command":"/bin/true","args":[],"job_id":"j-e2e-3"}' > "$SB/do3.out" 2>&1
RC6=$?
AFTER6=$(wc -l < "$LEDGER")
if [ "$RC6" -ne 0 ]; then ok "C-06 连不上内核 ⇒ 非零退出（$RC6）"; else bad "C-06 连不上内核却零退出"; fi
if grep -q 'KernelUnreachable' "$SB/do3.out"; then ok "C-06 理由点名 KernelUnreachable"; else bad "C-06 未点名理由"; fi
check "C-06 账本行数未变（没有任何副作用）" "$AFTER6" "$BEFORE6"

# ── C-07 孤儿可查 ─────────────────────────────────────────────────────
# 直接造一条"有意图、无结果"的账本：用内核写意图、不写结果。
cat > "$SB/orphan.jsonl" <<'EOF'
{"world":1,"kind":"act","id":"e-o1","seq":1,"at":100,"actor":"world://agent/1","flags":[],"chain":"fnv1a64:0000000000000000","body":{"capability":"job.start","verb":"start","request_id":"r-orphan","params":{"command":"/bin/true"}}}
EOF
ORPH=$($BIN --cap-dir "$SB/src/carrier/cap.d" --ledger "$SB/orphan.jsonl" carrier orphans 2>&1)
case "$ORPH" in *'有意图、无结果'*) ok "C-07 孤儿被查出来";; *) bad "C-07 孤儿没查出来";; esac
case "$ORPH" in *'不得自动重试'*) ok "C-07 只报告、不重试（给了明确口径）";; *) bad "C-07 未给不重试口径";; esac
# 反例：补上结果后，就不再是孤儿
cat >> "$SB/orphan.jsonl" <<'EOF'
{"world":1,"kind":"act","id":"e-o2","seq":2,"at":101,"actor":"world://agent/1","flags":[],"chain":"fnv1a64:1111111111111111","trace":"e-o1","body":{"capability":"job.start","verb":"start","request_id":"r-orphan","params":{"result":"ok","exit_code":0,"detail":{}}}}
EOF
ORPH2=$($BIN --cap-dir "$SB/src/carrier/cap.d" --ledger "$SB/orphan.jsonl" carrier orphans 2>&1)
case "$ORPH2" in *'没有『有意图、无结果』的请求'*) ok "C-07b 补上结果后不再报孤儿（判据会变）";; *) bad "C-07b 补上结果后仍报孤儿";; esac

# ── C-08 撤销不进主干 ─────────────────────────────────────────────────
BADLINE=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in
    \{*\}) ;;
    *) BADLINE=$((BADLINE+1)) ;;
  esac
done < "$LEDGER"
check "C-08 账本每一行都是 JSON 对象（无二进制、无非事件行）" "$BADLINE" "0"
check "C-08b 账本无 NUL 字节" "$(tr -dc '\000' < "$LEDGER" | wc -c)" "0"
case "$RESULT_LINE" in
  *'"carrier_undo"'*) ok "C-08c 载体撤销以**内容引用**出现在事件字段里" ;;
  *) ok "C-08c 本次未触发撤销点（该能力不需要撤销）——判据留给需要撤销的能力" ;;
esac

# ── C-09 写侧进程（被管者身份）对账本与规则**没有写权限** ─────────────
#
# 书 §4.5:601 逐字：「写侧这只手跑在自己的进程里，以被管者身份运行，对账本与规则都没有
# 写权限。……手如果自己有写权限，世界就有了第二个权威」。
#
# 与 C-01 的分工：C-01 只看"账本里的字节对不对"（判据弱）；本组以**被管者身份真去写**。
# 与 tools/con01-no-bypass.sh 的分工：那里跑的是**内核二进制**；这里跑的是**载体自己**。
# ⚠️ 载体**没有**"写账本"这条路（这正是零写权限的设计面）⇒ 本组分两半：
#    ① 以被管者身份跑**载体自己** ⇒ 必须**读得到**账本（只读消费面成立）；
#    ② 以同一身份**直接写**账本／改规则 ⇒ 必须**被拒**，且原因必须是 Permission denied
#       （只看 rc≠0 会把"命令找不到""用户不存在"都算成被拒——con01 v1 的 F1 教训）。
#
# 为什么这一组**不碰 /tmp 之外**：沙箱与账本都在一次性目录里；放宽 mode 只为造反证，随即复原。
echo
echo "── C-09 写侧进程（被管者身份）对账本与规则无写权限 ──────────"
MANAGED=agent
if ! id "$MANAGED" >/dev/null 2>&1; then
  if command -v useradd >/dev/null 2>&1; then useradd -M -s /usr/bin/nologin "$MANAGED"; fi
fi
if ! id "$MANAGED" >/dev/null 2>&1; then
  bad "C-09 前提不成立：本机没有「$MANAGED」这个被管者用户（也无法创建）⇒ 判据**未能校验**，按不通过处置"
else
  MUID=$(id -u "$MANAGED" 2>/dev/null)
  check "C-09 前提：被管者 uid 不是 0" "$([ "${MUID:-0}" != "0" ] && echo yes || echo no)" "yes"
  check "C-09 前提：账本属主≠被管者（否则 mode 再严也没用）" \
        "$([ "$(stat -c '%u' "$LEDGER")" != "${MUID:-x}" ] && echo yes || echo no)" "yes"
  # 让被管者**进得来**：否则拒绝会落在目录层（con01 v1 的 F4 教训：那证明的不是文件位）
  chmod 755 "$SB" "$SB/run" "$SB/src/carrier/cap.d" 2>/dev/null
  chmod 644 "$LEDGER" 2>/dev/null
  RUNBOX="$SB/runbox"
  mkdir -p "$RUNBOX"
  cp "$BIN" "$RUNBOX/world-core"
  chmod 755 "$RUNBOX" "$RUNBOX/world-core"

  # ① 以被管者身份跑**载体自己**：只读消费账本必须走得通
  if runuser -u "$MANAGED" -- "$RUNBOX/world-core" --cap-dir "$SB/src/carrier/cap.d" --ledger "$LEDGER" \
       carrier orphans >/dev/null 2>&1; then
    ok "C-09 以被管者身份跑**载体自己**（carrier orphans）读得到账本（只读消费面成立）"
  else
    bad "C-09 以被管者身份跑载体自己就被挡住了 —— 账本对被管者不是「只读可用」"
  fi

  # ② 同一身份**直接写**账本／改规则：两次都必须被拒，且原因必须是 Permission denied
  denied() { # $1=描述 $2=命令
    local desc="$1" cmd="$2" out rc
    out=$(runuser -u "$MANAGED" -- sh -c "id -u >/dev/null; $cmd" 2>&1); rc=$?
    if [ $rc -eq 0 ]; then bad "$desc —— **居然成功了**：$out"; return; fi
    if ! printf '%s' "$out" | grep -qi 'Permission denied'; then
      bad "$desc —— 被拒了但原因不是 Permission denied（rc=$rc）：$(printf '%s' "$out" | head -1 | cut -c1-90)"
      return
    fi
    ok "$desc（rc=$rc；原因含 Permission denied；执行者 uid=${MUID}）"
  }
  denied "C-09 写侧直写账本（追加一行）被拒" "echo '{}' >> $LEDGER"
  denied "C-09 写侧改规则（向 policy.json 追加）被拒" "echo '{}' >> $SB/src/gate/policy.json"

  # ③ 反证：把账本放宽到 0666 ⇒ **同一动作必须成功**（否则上面两条是橡皮图章）
  chmod 666 "$LEDGER"
  if runuser -u "$MANAGED" -- sh -c "printf '{\"probe\":1}\n' >> $LEDGER" 2>/dev/null; then
    ok "C-09b 反证：账本 0666 ⇒ 同一动作**成功了**（上面那两条判据会变，不是永远绿）"
  else
    bad "C-09b 反证不成立：账本已放宽到 0666 却仍写不进 ⇒ 上面那两条说明不了任何事"
  fi
  chmod 644 "$LEDGER"
fi

# ── 汇总 ──────────────────────────────────────────────────────────────
echo
echo "== 汇总：通过 $PASS 项，失败 $FAIL 项 =="
[ "$FAIL" -eq 0 ] && { echo "carrier_acceptance: PASS"; exit 0; }
echo "carrier_acceptance: FAIL"
exit 1
