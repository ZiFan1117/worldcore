#!/usr/bin/env bash
# check.sh —— **一条命令跑通**（S3 准出判据；REQ-N-004 / WC-SDP-001 §3.4）
#
# 为什么需要它：`REQ-N-004`（私有化部署形态）的判据是"**干净环境一条命令跑通**并打印 READY"，
# 而此前只有零散命令（cargo test / world-core check / project check），
# 没有一个**唯一的、能被人和 CI 同时调用**的入口。评审 T-22 指出该缺口；
# `WC-SCMP-001` §8.4 G-07 也把"入口脚本未入库"记为待办。
#
# 本脚本做什么（全部可复现；实跑步骤由下方 `step()` 逐条累积，**不在文案里写死条数**）：
#   ① 构建（--locked，锁依赖）
#   ② 骨架冒烟：在**一次性沙箱**里打开世界 → 必须打印 READY
#   ③ 三条专属验收测试（追加→读回 / 重启→还在 / ★删读模型→重算一致）
#   ④ 两个投影**同源**核对（同一读模型 + 同一词表身份）
#
# ⚠️ 纪律：全程只碰**一次性沙箱账本**（mktemp 目录，退出即删），
#    **绝不触碰真实账本**（依 06-swe-gb 幂等口径修订：命令幂等，数据操作天然不幂等）。
#
# 用法：bash check.sh          （在  内或任意位置均可）
# 退出码：0 = 全通过；非 0 = 任一步失败（与 CI 同为阻断式）
set -euo pipefail

cd "$(dirname "$0")"
BIN="${CARGO_TARGET_DIR:-target}/debug/world-core"   # 2026-09-27：感知 CARGO_TARGET_DIR（干净 target 下此前后 rc=127，见 R4S2-09）

# ── 步骤清单：**由脚本自身累积，不手写**（skill §八：一个事实只有一个权威载体）──────
# 为什么要有它：原结论行是**手写**的步骤名串，写它的时候只列到「规格层守卫」——
#   第 ⑨ 步（机核层守卫）落地后，那句结论就成了漏报，且没有任何东西会因此变红。
#   "手写一份步骤名"与"手写一个条数"是同一种病：加一步就过期。
# 现在：每个步骤用 `step` 声明一次，**标题与结论清单同源**；步数由 `${#STEPS[@]}` 现算。
# ⚠ 2026-10-03 增（`STEP_KIND`）：标题照旧是**裸步骤名**（判据⑮ `spec_bridge.py` 拿它跟
#   `WC-AT-001` 的清单表逐条对齐，**不许**往里塞标记）；**结局另存一列**——
#   原来结论行对每一步都打 `✅`，于是"未校验（SKIP）"的步在结论里**也长成绿的**。
STEPS=()
STEP_KIND=()      # 与 STEPS 同下标；取值 PASS／SKIP／FAIL
CUR_STEP=-1
step() { # step <步骤标题>
  STEPS+=("$1")
  STEP_KIND+=("PASS")
  CUR_STEP=$(( ${#STEPS[@]} - 1 ))
  printf '── %s\n' "$1"
}

# ── 判定助手：**显式取 rc**，不把判定交给管道语义（`W-06`）──────────────
# 为什么不用 `cmd | tail -N`：那条写法"看起来在留档、实际上把判定权交了出去"——
#   · 它只在 `set -o pipefail` 生效时才把 cmd 的 rc 传出来（换 shell、换一行写法就变恒 0）；
#   · 失败**细节**被 tail 截掉，只能看到最后几行；
#   · 真正的失败若被**工具自己**吞掉（例如命令替换里写反引号导致的
#     `command not found` 只进 stderr、不改 rc），管道这一层**看不见**。
# 现在：先跑、先取 rc、先判定，再打印尾部若干行。失败即中止（与 CI 同为阻断式）。
run_tail() { # run_tail <展示行数> <描述> [<结局>] <命令...>
  # 本步**结局**＝**可选的第 4 个位置参数**：只给"可能没跑"的步用；缺省 PASS。
  # ⚠ 但**第 3 参是不是结局，按字面探测**：**恰为** `PASS`／`SKIP`／`FAIL` 才当结局，否则当命令。
  #   为什么必须探测（2026-10-03 血泪，VM 实盘）：本函数原先**读第 3 参当结局**，而既有调用
  #   `run_tail 4 "格式检查（与 CI 同一条命令）" cargo fmt --all -- --check` 的第 3 参是 `cargo`
  #   ⇒ 报「未知步结局「cargo」」⇒ `exit 2` ⇒ **全量门禁在 ①b 当场中止、⑦b 根本没跑到**
  #   （`CHECK_RC=2`），**而当时的 `--self-test` 却是绿的**——它只喂了 `PASS`／`false`，
  #   **没有一条"既有调用的真实形态"**。⇒ 教训：**自证通过 ≠ 判据有效**；
  #   改公共函数的签名，必须拿**既有调用点的真实形态**做反例（本脚本自证里那条
  #   `跑通既有调用形态` 就是它），并到实盘跑一遍。
  # 结局渲染由 `scripts/verify/step_marker.py` 持有（唯一权威载体）：**只有 PASS 配打 ✅**；
  #   SKIP 打 `⏭`、FAIL 打 `❌`。（本探测**只认字面**，既不猜词、也不把命令名当结局。）
  local n="$1"; shift
  local what="$1"; shift
  local kind="PASS"
  case "${1:-}" in
    PASS|SKIP|FAIL) kind="$1"; shift ;;
  esac
  local mark
  case "$kind" in
    PASS) mark="$MARK_PASS" ;;
    SKIP) mark="$MARK_SKIP" ;;
    FAIL) mark="$MARK_FAIL" ;;
  esac
  local out rc=0
  # `|| rc=$?`：`set -e` 下裸赋值会因命令替换失败而当场中止，取 rc 的机会都没有；
  # 用 `||` 抑制 `set -e` 并保住真 rc（这正是"显式取 rc"的字面意思）。
  out="$("$@" 2>&1)" || rc=$?
  printf '%s\n' "$out" | tail -n "$n" | sed 's/^/  /'
  # ★ 守卫自报的 `STATUS=SKIP` 优先：rc=0 也可能是"根本没跑"
  case "$out" in *STATUS=SKIP*) mark="$MARK_SKIP"; kind="SKIP" ;; esac
  if [ "$kind" != "PASS" ] && [ "$CUR_STEP" -ge 0 ]; then
    STEP_KIND[$CUR_STEP]="$kind"      # 本步的结论行据此换标记（**FAIL 到不了这里**：下面即 exit）
  fi
  if [ "$rc" -ne 0 ]; then
    echo "  $MARK_FAIL $what 失败（rc=$rc）—— 验证留档不得吞掉失败"
    exit 1
  fi
  printf '  %s %s（rc=0）\n' "$mark" "$what"
}


# ── 登记型助手：**红、但不阻断全闸**（2026-10-05 新增）──────────────────
# 为什么需要它：`run_tail` 的语义是"rc≠0 ⇒ 当场 exit 1"（阻断式）。但有一档红**性质不同**——
#   【**设计已定·未落地**】：纸上写了、程序里还没有。它**该红、该被看见**，但它**不是"谁改坏了"**，
#   所以**不该让全闸停**（先例：`s1_sys_probe2.sh` 的"**另行登记**（现状为红、如实记录）"）。
# 结局取值表（`STEP_KIND`）：`PASS` 打 ✅ ／ `SKIP` 打 ⏭（未校验）／ `REG` 打 ⚠️（**登记型红**）。
# ⚠ **如实登记一处缺口**：`scripts/verify/step_marker.py` 的 `STATES` 只有 `PASS/SKIP/FAIL`（它自证"只有 PASS 配打 ✅"），
#   **没有 `REG`** ⇒ `REG` 的 ⚠️ 由**本脚本就地渲染**（**没有**第三个权威载体被发明；
#   ★ 只取用它的**不变量**：`REG` **不打 ✅**）。★ 这一处"两个渲染处"**如实登记**，不假装统一。
run_registered() { # run_registered <展示行数> <描述> <命令...>
  # rc 约定：**0 ⇒ 无事（PASS）**／**1 ⇒ 登记型红（REG，不阻断）**／**2 ⇒ 输入缺失（**失败**，阻断）**
  #   ★ 为什么 2 要阻断：工具的 `--help` 自述"2 = 输入缺失（**不是通过**）"——
  #     "读不到"**不许**被折算成"登记一下就过去了"。
  local n="$1"; shift
  local what="$1"; shift
  local out rc=0
  out="$("$@" 2>&1)" || rc=$?
  printf '%s\n' "$out" | tail -n "$n" | sed 's/^/  /'
  # ★★ 守卫自报的 `STATUS=SKIP` 优先（**与 `run_tail` 同源**）：`rc=0` 也可能是"根本没跑"。
  #   不认它 ⇒ **未校验的步会长成绿勾**（2026-10-03 实测过的假证，同族；那一次改的是 `run_tail`）。
  #   ★ 为什么写在这里而不是上面那三档注释里：注释不是判据；这里才是折算点。
  case "$out" in
    *STATUS=SKIP*)
      echo "  $MARK_SKIP $what —— **未校验**：守卫自报 \`STATUS=SKIP\`（rc=0 也可能是"根本没跑"）"
      echo "  （★ 本步 rc=$rc 已折算为 0；★ 它不是「通过」——**未校验 ≠ 通过**）"
      if [ "$CUR_STEP" -ge 0 ]; then STEP_KIND[$CUR_STEP]="SKIP"; fi
      return 0 ;;
  esac
  if [ "$rc" -eq 1 ]; then
    echo "  $MARK_REG $what —— **登记型红**：按【设计已定·未落地】登记，**该红、该被看见，但不阻断全闸**"
    echo "  （★ 本步 rc=$rc 已折算为 0；★ 它不是「未校验」、也不是「通过」——**如实红**）"
    if [ "$CUR_STEP" -ge 0 ]; then STEP_KIND[$CUR_STEP]="REG"; fi
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    echo "  $MARK_FAIL $what 失败（rc=$rc）—— 输入缺失／用法错**不是通过**，验证留档不得吞掉失败"
    exit 1
  fi
  printf '  %s %s（rc=0）\n' "$MARK_PASS" "$what"
}


# ── 步级标记（**只有 PASS 配打 ✅**）──────────────────────────────────
# 为什么单独一层：见上方 `run_tail` 的第 4 参说明。渲染规则由 `scripts/verify/step_marker.py` 持有
# （它自带 `--self-test`：反例证明"SKIP／FAIL 不打 ✅"这条不变量会红），本脚本只取用它的输出。
# ★ 2026-10-05 增 `REG`（登记型红）：**收口到 `step_marker.py`**（它是"结局 → 标记"的唯一权威载体）。
#   此前本脚本就地写过一个 ⚠️ 常量 ⇒ 「标记渲染」有了**两个处** ⇒ 按"一个事实一个权威载体"**收回来**。
if ! MARK_PASS="$(python3 scripts/verify/step_marker.py marker PASS)" \
   || ! MARK_SKIP="$(python3 scripts/verify/step_marker.py marker SKIP)" \
   || ! MARK_FAIL="$(python3 scripts/verify/step_marker.py marker FAIL)" \
   || ! MARK_REG="$(python3 scripts/verify/step_marker.py marker REG)"; then
  echo "❌ 步级标记渲染失败（scripts/verify/step_marker.py）—— 标记不可信时门禁不许继续" >&2
  exit 1
fi

# ── 判定器自证（`W-06`：先证明"必失败"真的会失败）─────────────────────
if [ "${1:-}" = "--self-test" ]; then
  echo "== check.sh 判定器自证（W-06 验证留档管道不吞错）=="
  # ⚠ 这两条**显式写 PASS**：`run_tail` 现在把第 3 个位置参数当"结局"，不写就会把命令名 `false`
  #   当成结局吃掉（同一段代码里 `run_tail … false` 会变成"没有命令可跑"）。
  if ( run_tail 1 "注入的必失败命令" false ) >/dev/null 2>&1; then
    echo "  ❌ 自证失败：注入的必失败命令竟被判为通过（判定器是装饰）"
    exit 1
  fi
  if ( run_tail 1 "注入的必失败命令（藏在管道左端）" sh -c 'echo boom; exit 3' ) >/dev/null 2>&1; then
    echo "  ❌ 自证失败：管道左端的失败竟被判为通过"
    exit 1
  fi
  echo "  ✅ 自证通过：两条注入的必失败命令都被判为失败（rc 显式判定，不依赖 pipefail）"
  # ── 步级标记自证：**未校验的步不许长成绿勾**（2026-10-03 实测的假证）──────────
  # ⚠ 判"有没有打 ✅"，只看**标记位**上那两个字符（`  ✅ `），**不**在整段输出里 grep `✅`：
  #   后者有假阳：失败话术里为指认那个勾而写了 `✅`，`grep -q '✅'` 会把"报错"读成"打了勾"。
  #   （这正是本项目那条"搜字样 ≠ 认结构"的又一次现形。）
  echo "== check.sh 步级标记自证（SKIP 不许被读成 ✅）=="
  _skipout="$( run_tail 3 "假 SKIP 步（命令自报 STATUS=SKIP）" PASS sh -c 'echo STATUS=SKIP; exit 0' 2>&1 )"
  if printf '%s\n' "$_skipout" | grep -qE '^  ✅ '; then
    echo "  ❌ 自证失败：未校验的步在标记位上打出了绿勾（只看勾的人会把它读成「过了」）"
    echo "$_skipout" | sed 's/^/     /'
    exit 1
  fi
  if ! printf '%s\n' "$_skipout" | grep -q "$MARK_SKIP"; then
    echo "  ❌ 自证失败：未校验的步没有打出 SKIP 标记（$MARK_SKIP）"
    exit 1
  fi
  _passout="$( run_tail 3 "假 PASS 步（真通过）" PASS sh -c 'echo boom; exit 0' 2>&1 )"
  if ! printf '%s\n' "$_passout" | grep -qE '^  ✅ '; then
    echo "  ❌ 自证失败：真通过（rc=0）的步竟没在标记位上打绿勾"
    exit 1
  fi
  # ── ★ 反例：**既有调用点的真实形态**（2026-10-03 血泪）──────────────────────
  # 上面两条反例喂的是 `run_tail … PASS <命令>`——那验的是**函数本身**，**不验**"既有调用点与
  # 新签名相不相容"。VM 实盘就是这么倒的：既有 `run_tail 4 "…" cargo fmt --all -- --check`
  # 的第 3 参 `cargo` 被当成结局 ⇒ `exit 2` ⇒ 全量在 ①b 中止，**而那时的自证是绿的**。
  #
  # ⚠ 形态要点（不许"顺手改漂亮"，这几处都是踩过的）：
  #   ① 探针**必须与实盘调用同形**：不给结局参数、第 3 参就是命令名；
  #   ② 跑一条**必定不存在**的命令（不是 `cargo`）——`cargo` 在不在是本条**测不到**的事
  #      （那是 ①b 的事）；拿它当探针会把"环境缺 cargo"误判成签名错；
  #   ③ **两次运行两个读数，一次都不能吞掉 rc**：
  #        · 病态实现（把 `cargo` 当结局）⇒ rc=**2** 且 stderr 有「未知步结局」；
  #        · 正确实现 ⇒ 命令跑不起来 ⇒ rc=**非 0**（127），且**没有**那句话。
  #      只喂"合法结局"那种写法**永远抓不到这个分歧**——那正是当时自证全绿的原因。
  _shape_rc=0
  _shape_out="$( run_tail 4 "格式检查（与 CI 同一条命令）" cargo fmt --all -- --check 2>&1 )" || _shape_rc=$?
  _err1=0
  _err_out="$( run_tail 4 "格式检查（与 CI 同一条命令）" cargo-no-such-command-xyz fmt --all -- --check 2>&1 )" || _err1=$?
  if printf '%s\n' "$_err_out" | grep -q '未知步结局'; then
    echo "  ❌ 自证失败：既有调用形态（第 3 参＝命令名）被当成「未知步结局」"
    printf '%s\n' "$_err_out" | sed 's/^/     /'
    exit 1
  fi
  if [ "$_err1" -eq 0 ]; then
    echo "  ❌ 自证失败：跑不起来的命令竟判为通过（判不了 ≠ 过了）"
    exit 1
  fi
  if ! printf '%s\n' "$_shape_out" | grep -q '格式检查（与 CI 同一条命令）'; then
    echo "  ❌ 自证失败：实盘同形那条**根本没走到判定**（run_tail 把命令名吃掉了）"
    exit 1
  fi
  echo "  ✅ 自证通过：SKIP 步出 $MARK_SKIP 且标记位上**无** ✅；PASS 步标记位上是 ✅；"
  echo "     既有调用形态（第 3 参＝命令名）**未被当成结局**（同形探针 rc=$_shape_rc，"
  echo "     缺席命令探针 rc=$_err1 —— 两者都如实非零，且都没有「未知步结局」）"
  exit 0
fi

echo "== world-core check.sh =="
echo "  目录 : $(pwd)"
echo "  主机 : $(uname -sr)"
echo "  工具 : $(cargo --version 2>/dev/null || echo 'cargo 缺失')"

# ── ① 构建 ───────────────────────────────────────────────────────────
echo
step "① 构建（--locked）"
cargo build --locked --quiet
echo "  ✅ 构建通过"

# ── ② 骨架冒烟（一次性沙箱）─────────────────────────────────────────
SB="$(mktemp -d)"
trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB/src/ontology_definition" "$SB/src/gate"
cp src/ontology_definition/ontology.json "$SB/src/ontology_definition/ontology.json"
cp src/gate/policy.json "$SB/src/gate/policy.json"
chmod 755 "$SB"; chmod 644 "$SB/src/ontology_definition/ontology.json" "$SB/src/gate/policy.json"

echo
echo
step "①b 格式检查（rustfmt）"
# 为什么在这一步：CI workflow 跑 `cargo fmt --all -- --check`（`.github/workflows/world-core-gate.yml`），
# 而本脚本此前**从不跑** ⇒ 本地十步全绿、**CI 每次 push 都红**（2026-09-28 实测：最近 5 次 run 全 failure，
# 红的正是"格式检查"：65 处 diff、10 个文件）。格式是最便宜、最先该过的一关，故紧挨 ① 构建。
run_tail 4 "格式检查（与 CI 同一条命令）" cargo fmt --all -- --check

step "①c 静态检查（clippy，警告即失败，与 CI 同一条命令）"
# 为什么要有这一步：**①b 那条病的同形第二次**——同一个判定存在两处（CI 一处、本地预演一处），
#   而"唯一入口"那处没有它。现取（2026-10-06，三处原文各一）：
#   · CI smoke 作业 `.github/workflows/world-core-gate.yml:98-100`：步名逐字「静态检查（警告即失败）」，
#     命令逐字 `cargo clippy --all-targets -- -D warnings`；
#   · 本地预演 `scripts/test/ci_rehearsal.sh:87`：逐字同一条命令；
#   · 而出厂门禁 `check.sh` 此前**从不跑** ⇒ 本地全绿、**CI 每次 push 都红**
#     （本步落地前的真实读数：唯一 error `src/bus/mod.rs:653:21 unused_mut`，rc=101）。
#   ⇒ 本步存在的唯一理由是"**本地能提前撞到 CI 撞到的那面墙**"，故命令**逐字对齐 CI 那一行**
#     （上引 `world-core-gate.yml:100`）：`cargo clippy --all-targets -- -D warnings`。
#   ★ 本步**不加** `--locked`：CI 那一行没有它（`ci_rehearsal.sh:87` 也没有）——
#     加了会造出"CI 不红而本步红"的差，而"与 CI 同一条命令"指的就是上引那一行；
#     依赖锁定纪律由 ① 的 `cargo build --locked` 承担。
#     ★ 且 ① 已在 ①c **之前**跑过 `cargo build --locked` ⇒ 锁文件在 ①c 之前就已被证明自洽 ⇒
#       ①c 不带 `--locked` 也**不会**出现"clippy 顺手改写 `Cargo.lock`"这种"闸自己动树"的副作用。
run_tail 6 "静态检查（clippy，警告即失败，与 CI 同一条命令）" cargo clippy --all-targets -- -D warnings

step "② 骨架冒烟（沙箱账本：$SB）"
OUT="$("$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/ledger.jsonl" --policy "$SB/src/gate/policy.json" check)"
echo "$OUT" | sed 's/^/  /'
echo "$OUT" | grep -q READY || { echo "  ❌ 未打印 READY"; exit 1; }
echo "  ✅ READY（本体/门禁/账本三项都开得起来）"
# 新账本必须带摘要链（WC-SCMP-001《软件配置管理计划》变更请求台账 · 记录 WC-CR-003）：
#   写一条再断言"有链"且 --require-chain 通过。
# 若写入侧哪天不再产链，这一步会当场红——把"默认受保护"变成入口断言。
W0() { "$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/ledger.jsonl" --policy "$SB/src/gate/policy.json" "$@"; }
# 为什么写 `world://notice/probe` ＋ `muted`：这一步要的只是"写一条，再断言账本带链"，
# 而**写进世界的东西必须在出厂本体里声明过**（书 §5.3「声明以外的东西不许落账」；
# 执行者 `src/ontology_definition/mod.rs::check_concepts`）。原先写 `world://check/probe#p`——`check` 与 `p`
# 都没声明过 ⇒ 这一行把第②步打成 rc=2。改的只是落笔的**格子**（换成 `concepts` 里真有的
# 那一格，值 true 是 `muted: bool` 该有的形状），判据强度不变：仍然"写一条 → 有链 → --require-chain 过"。
W0 append change '{"subject":"world://notice/probe","path":"muted","before":null,"after":true}' >/dev/null
OUT2="$(W0 check)"
echo "$OUT2" | grep -q '有摘要链' || { echo "  ❌ 新账本应带摘要链（WC-SCMP-001 变更请求台账 · WC-CR-003），实得：$(echo "$OUT2" | grep '链')"; exit 1; }
W0 --require-chain check >/dev/null || { echo "  ❌ --require-chain 未通过"; exit 1; }
echo "  ✅ 摘要链：新账本带链，--require-chain 通过"

# ── ③ 三条专属验收测试 ──────────────────────────────────────────────
echo
step "③ 三条专属验收测试（WC-SQAP-001 §2.4）"
cargo test --locked --test acceptance -- t1_ t2_ t7_ 2>&1 | grep -E 'running [0-9]+ tests|test result:' | sed 's/^/  /'
echo "  ✅ 追加→读回 / 重启→还在 / ★删读模型→重算一致"

echo
step "③b 契约测试（覆盖 M05 门禁 / M08 检查点 / M09 通道）"
cargo test --locked --test contract 2>&1 | grep -E 'running [0-9]+ tests|test result:' | sed 's/^/  /'
echo "  ✅ 门禁失败路径 / 静态墙 / 单写者 / 检查点 / 通道身份 / 错误码契约"

# ── ④ 两个投影同源 ──────────────────────────────────────────────────
echo
echo
step "③c 其余测试二进制（**全量，不写死清单**——任何新加的测试文件自动进闸）"
# 为什么要有这一步（2026-09-28 实测）：`check.sh` 原只跑 `acceptance`（挑 t1_/t2_/t7_ 三个用例）与 `contract`，
# 而仓里**实有 13 个测试二进制** ⇒ 其余 11 个（含 `family_readmodel`／`atom_reversibility`／`atom_declared_only`／
# `write_side`／`channel_bounds`／`projection_leaf`／`ontology_ext`／`trace_notice`／`cli`／`delivery`／`perf`）
# **从不被出厂门禁执行**。⇒ "每条要求都要有会红的断言"这句话，会被"门禁不跑它"削掉一大半。
# 本步**不写死清单**（写死就会烂）：跑整棵 `cargo test --locked`，新文件自动进闸。
cargo test --locked 2>&1 | grep -E 'running [0-9]+ tests|test result:' | sed 's/^/  /'   # 与 ③／③b 同形：每个 target 的结果都进日志

step "④ 投影与同源核对（REQ-F-018/019/020）"
W() { "$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/ledger.jsonl" --policy "$SB/src/gate/policy.json" "$@"; }
W append change '{"subject":"world://notice/n-1","path":"muted","before":null,"after":true}' >/dev/null
W append act '{"capability":"notice.mute","verb":"do","request_id":"r-check","params":{}}' >/dev/null
# ⚠️ 这两行**不是展示行**：其退出码已参与判定——`set -euo pipefail` 下，赋值语句里的管道失败
#    （含 head 的 SIGPIPE）会使整个 check.sh 非零退出。原先写成 echo "... $(W ... | head -1)"，
#    失败被吞在 echo 的实参里、不参与判定。2026-09-27 按三评委判词改为"先赋值再 echo"（只增不减）。
L1="$(W project language | head -1)"
L2="$(W project visual | head -1)"
echo "  语言投影首行: $L1"
echo "  视觉投影首行: $L2"
W project check | sed 's/^/  /'

echo
echo
step "⑤ 纯文本审计（REQ-N-001 / AC-07）"
run_tail 2 "纯文本审计" python3 scripts/verify/plain_text_audit.py src/ontology_definition/ontology.json src/gate/policy.json "$SB/ledger.jsonl"
echo "  ✅ 账本/词表/策略均为纯文本（UTF-8、无 NUL、无可疑控制字符、逐行可解析）"

echo
echo
step "⑤b 需求追溯矩阵（RTM：需求 → 设计模块 → 测试用例，双向）"
# 为什么放这里：这一步量的是**文档面的一致性**（`docs/S1-需求/WC-RTM-001.csv` ↔ `WC-SRS-001` ↔ 模块登记表），
# 与 ⑤ 同族（都是"纸面"层面的门禁）；它**不碰**代码与账本，故放在 ⑥（真实二进制）之前。
run_tail 6 "追溯矩阵判定器自证（造一对坏的/好的输入，**反例必红、正控必绿**）" python3 scripts/verify/trace_matrix.py --self-test
run_tail 12 "需求追溯矩阵（RTM）" python3 scripts/verify/trace_matrix.py

step "⑥ 系统级验收（TC-037–TC-040，真实二进制端到端）"
# 为什么放在这里：`cargo test` 验模块与接口（L1/L2），本步验**产物本身**（L3）——
# 只看退出码、真实文件字节与命令输出。它同时是 S5 起 `RTM_STRICT=true` 的
# 系统级/验收级证据（见 WC-SCMP-001 §8.4 G-16）。
run_tail 1 "系统级验收判定器自证" bash scripts/test/system_acceptance.sh --self-test
run_tail 3 "系统级验收（TC-037–TC-040）" bash scripts/test/system_acceptance.sh

step "⑥b 载体适配器系统级验收（M10：真实二进制／真实内核／真实账本）"
# 为什么要有这一步（现取，2026-10-06）：`scripts/test/carrier_acceptance.sh` 是**载体适配器（M10）的系统级验收**
#   （C-01…C-09b 九组判据，真实二进制／真实内核／真实账本）；机器席在 VM 上真跑 ⇒ rc=0、
#   `== 汇总：通过 28 项，失败 0 项 ==` ＋ `carrier_acceptance: PASS`，0 条 ❌。
#   **但它在任何门禁里都不被调用**（`check.sh`／`.github/workflows/world-core-gate.yml`／
#   `scripts/test/ci_rehearsal.sh`／`scripts/test/system_acceptance.sh` 四处**各 0 次**）⇒ **缺口是【接线】不是【能力】**：
#   它今天真绿，而**回归了没有任何门禁会变红**。★ 与 ①b／①c 同一条病："闸不在门禁里等于没有闸"。
# ★ 必须**显式传 `$BIN`**（① 刚构建的那个）：该脚本默认先找 `release/` 再找 `debug/`，
#   而它自带 D-33「被测二进制比源码旧就拒跑」（`StaleBinary`，rc=2）⇒ 传显式路径才不误取陈旧产物。
# ★ 非 root ⇒ **显式 SKIP**（照 ⑦g 的既有形态；不阻断、也不许读成绿）：C-09 组要
#   `runuser -u agent`（需 root），缺它时脚本**不是**打 SKIP，而是走 `bad(...)` ⇒ 汇总 rc=1
#   ——照 `run_tail` 会把"这一步没跑成"当场判成全闸失败。⇒ 前置分岔：有 root 且 `runuser` 在 ⇒ 真跑；否则打 ⏭。
if [ "$(id -u)" -eq 0 ] && command -v runuser >/dev/null 2>&1; then
  run_tail 6 "载体适配器系统级验收（M10：真实二进制／真实内核／真实账本）" bash scripts/test/carrier_acceptance.sh "$BIN"
else
  echo "  $MARK_SKIP 载体适配器系统级验收（M10：真实二进制／真实内核／真实账本）—— **未校验**：本机非 root 或缺 runuser（C-09 组要 runuser -u agent）"
  echo "  （★ 这一步**没跑**；★ **未校验 ≠ 通过**。有 root 的机器上它会真跑：绿 ⇒ ✅、红 ⇒ 当场阻断）"
  if [ "$CUR_STEP" -ge 0 ]; then STEP_KIND[$CUR_STEP]="SKIP"; fi
fi

echo
step "⑥c 载体契约（部署面单元 ≡ 设计＋法律）"
# 为什么要有这一步（现取，2026-10-06）：`scripts/verify/carrier_contract.py` 是**判 `deploy/` 那条守卫**
#   （12 条判据：单元 ⊆ 清单／清单 ⊆ 目录／`User=` 不许 root／`SocketMode` 不许 0666／
#   `ExecStart` 不许带 `--confirm`／单元 ∧ 法律 `listeners`／渲染物 ⊆ 法律／owner→uid 映射对账…）。
#   **但它在任何门禁里都不被调用**：`check.sh` 0 处、`.github/workflows/world-core-gate.yml` 0 处
#   （现取：`Select-String -SimpleMatch 'carrier_contract'` 两处都是 0）⇒ **有守卫、没人跑**
#   —— 与 ①b／①c／⑥b 同一条病："闸不在门禁里等于没有闸"。
# ★ 它自带 `STATUS=SKIP`：宿主机缺 POSIX 元数据／部署件（`/etc/world-core/owner_uid.json`／`channel.json`）时，
#   它会**显式打印未校验**并 rc=0 —— `run_tail` 认这一行 ⇒ 那一步会正确显示 ⏭（未校验 ≠ 通过），
#   不需要像 ⑥b 那样另写前置分岔。
# ⚠ 射程（如实写）：**本步在 VM 上的颜色今天是【未取到】**——2026-10-06 收口时 VM（`192.168.56.10:22`）
#   连接超时，取不到读数；宿主机现取为「绿（红 0 条）＋ 5 条未校验」、rc=0。
run_tail 14 "载体契约（部署面单元 ≡ 设计＋法律）" python3 scripts/verify/carrier_contract.py

echo
step "⑦ S1 需求验证面补建（第一轮 TC-042/046–052；第二轮 TC-053–TC-075）"
# 为什么放在这里：R1 的九席独立评审实测指出，SRS §五 声明的一批用例**从未实存**，
# 而若干 `REQ-F-*` 的「应当失败」反例**只挂在这些不存在的用例上**——
# 按本项目逐字纪律「反例不红视为未校验」，那些条目当时**不可校验**。
# 本步把其中**不需要改产品代码即可执行**的部分补建成真实断言，并**显式计数**「现状为红」的登记项
# （登记项不影响退出码，但必须每轮复算 —— 防"把已知缺陷藏进绿灯里"）。
run_tail 1 "S1 验证面补建①判定器自证" bash scripts/test/s1_sys_probe.sh --self-test
run_tail 4 "S1 验证面补建①（TC-042/046–052）" bash scripts/test/s1_sys_probe.sh
run_tail 1 "S1 验证面补建②判定器自证" bash scripts/test/s1_sys_probe2.sh --self-test
run_tail 4 "S1 验证面补建②（TC-053–TC-076）" bash scripts/test/s1_sys_probe2.sh
run_tail 1 "排版审计判定器自证" python3 scripts/verify/visual_layout_audit.py --self-test
run_tail 1 "契约分册门禁判定器自证" python3 scripts/verify/ic_books_check.py --self-test
run_tail 8 "契约分册门禁（九册齐·要点齐·依赖列逐边一致）" python3 scripts/verify/ic_books_check.py
# 表块行宽审计（**转义感知**）：`\|` 是单元格内的**字面竖线**，朴素的 `s.count("|")` 会把
# **本来就正确**的行报成「体行行窄」（R1 三轮席 S-07 的 `G-20` 即此类误报；本轮 8 处复算 = 0）。
# 该行**不过滤退出码**：真有不符 ⇒ 本步直接失败（既防误报、也防漏报）。
run_tail 1 "表块行宽审计判定器自证" python3 scripts/verify/table_width_audit.py --self-test
run_tail 20 "表块行宽审计（转义感知）" python3 scripts/verify/table_width_audit.py "docs/S1-需求/需求-WC-IRS-001-v0.1.md" "docs/S1-需求/需求-WC-SRS-001-v0.1.md" "docs/评审/评审-前置-WC-RV-R1-001-v0.1.md"

echo
step "⑦b kind 守卫（架构件里的三类话 vs 帧上方法名）"
# 为什么放在这里：与 ⑦（文档面／规格面）同族——它判的是**架构件里的说法与代码结构是否一致**，
#   不碰账本、不碰二进制。此前这三条判据**只活在一份仓外的一次性脚本**里
#   （`D:\Code\_kind_guard_check.py`：不在版本控制、不在任何门禁里）——
#   按本仓口径「**闸在版本控制之外等于没有闸**」，它红与不红，门禁一样绿。
# 现在把它搬进仓（`scripts/verify/kind_guard.py`，带 `--self-test`）并由本步调用。
# 判据（三条，条条会红）：①架构件里断言 `kind` 是"七个取值"一族 ⇒ 红；
#   ②**表头就是 `kind`** 的表里出现账本家族以外的家族（帧上方法名）⇒ 红；
#   ③断言"四类不回行" ⇒ 红（**认结构不认字样**：先剥掉引号内字样再匹配）。
# 扫描根＝架构工作夹「语义世界-架构」（脚本自解析候选；`WC_ARCH_DIR` 可覆盖）。
#   ★ 2026-10-06：该夹已按作者指示退役到归档 `语义世界-架构\`，
#     `scripts/verify/kind_guard.py` 的候选里**已含这个归档位置** ⇒ 宿主机上本条判据**仍会真跑**（实测 184 篇／0 红）。
# ⚠ 那个目录**在 VM 上不存在**（架构夹在工作区、不进仓）⇒ 本步在 VM 上以 `--allow-missing`
#   **显式打印"未校验"并 rc=0**——不是"通过"，是"没跑"。它不是本步独有的毛病：
#   仓里凡依赖 VM 上没有的文件的判据，在 VM 上都只是"没跑"。
run_tail 1 "kind 守卫自证（每条判据各造反例，反例必红；短路判据必红）" python3 scripts/verify/kind_guard.py --self-test
# 结局由守卫自己报（`STATUS=`）：根不在 ⇒ SKIP（打 ⏭，**不打 ✅**），根在且无红 ⇒ PASS
run_tail 12 "kind 守卫（架构件：三类话 vs 帧上方法名）" SKIP python3 scripts/verify/kind_guard.py --allow-missing

# 2026-09-27 修（W-06）：本步原先登记的三类噪声里，(c) `WC-SQAP-001: command not found`
#   已**在源头消除**（`s1_sys_probe2.sh` 描述串内的反引号改成字面词，不再做命令替换）；
#   (a)(b) 两类仍属无害噪声、**不改判据强度**，故保留。

echo
step "⑦c 两件一致性守卫（ontology.json × policy.json：C-01…C-07）"
# 为什么放在这里：与 ⑦b 同族——都判**仓内的静态件**（不碰账本、不碰二进制）；
#   ⑦b 判"架构件里的说法与代码结构一不一致"，⑦c 判"**两件法律彼此对不对得上**"。
# 为什么不是重复造闸：`src/lib.rs` 的 `World::open` **自己逐字声明了射程**——
#   「⚠️ 射程（如实声明）：只核**名字集**与 `kind`」⇒ 它只判**两向里的一向**（policy → ontology）。
#   反向（C-03）／动作两层三样（C-04）／许可条文的键（C-05）／`writes` 与 `subjects.allow`（C-06）／
#   `listeners` 与 `subjects.allow`（C-07）**此前全无人判**。
#   代价是具体的：`policy.json` `subjects._why_core` **自己记着**「`world://core` 是 `writes` 里唯一
#   被授权可写任意主体的主体，却不在本白名单内 ⇒ **出厂策略自身不自洽**」——那条不自洽当时是
#   **被人读出来的**，不是被闸抓出来的。本步就是把那一类变成**会红**。
# 判据面：见 `scripts/verify/cross_contract.py` 文件头；`--self-test` 每条各造反例＋正控＋短路验红。
# ★ 结局由守卫自己报（`STATUS=`）：三条不许混 ——
#   · 有红 ⇒ rc=1，本步失败（失败信息**点名是哪两件在哪一格矛盾**）；
#   · 无红但有**判不了的**（缺标的物）⇒ `STATUS=SKIP`（打 ⏭，**不是 ✅**）——★ 不许报绿；
#   · 本套都可判且全绿 ⇒ `STATUS=PASS`。
# ★★ **本步的 ✅ 是"判过且对"，不是"没人判"**（2026-10-05 Lead 裁后拆套；下方 ⑦d 是另一件事）：
#   C-01…C-07 **七条今天全部判得了**，现跑 **0 红**，且每条都有反例证明**它会红**（`--self-test`）。
run_tail 1 "两件一致性守卫自证（每条判据各造反例，反例必红；短路判据必红）" python3 scripts/verify/cross_contract.py --self-test
run_tail 16 "两件一致性守卫（C-01…C-07：两件不许互相矛盾）" python3 scripts/verify/cross_contract.py --set cross

echo
step "⑦d 实例地址归属（口径①：实例地址只许落在实例位键下，C-08）"
# 为什么与 ⑦c **分两步**（2026-10-05 Lead 裁）：
#   ★ "7 条【判过且对】"与"1 条【判不了】"**是两件事**。混在一步里 ⇒ **那 7 条的绿会被那 1 条的 ⏭ 吞掉**；
#     反过来，**⏭ 也可能被人读成 ❌** ⇒ **两个方向的误读都会发生**。
#   ⇒ **一件事一个读数**：⑦c 报 7 条，⑦d 报 1 条。
# ★ 硬底线：**"判不了"不许显示成 ✅** —— 所以本步今天**恒为 ⏭**。
# ⚠ **现取（2026-10-05）：本步 ⏭，不是 ✅** —— 标的物 `ontology._permissions._instance_keys` **今天不在**
#   （`标准-语义世界-本体与协议-v0.1.md` §5 第 2 条说它"必填"；`world-core` 全树零命中）
#   ⇒ 那是"**判不了**"，**不许**算通过。★ 标的一落地，本步**自动转 ✅**（无需改本步）。
# 判据 C-08 的反例已证"标的一在、它就红"（`--self-test` 里那条 + ⑦c 的自证步）。
run_tail 12 "实例地址归属（口径①，C-08）" python3 scripts/verify/cross_contract.py --set instance

echo
step "⑦e 授权路判据（本体声称的路 ↔ src/ 里有没有那条路）"
# 为什么放在这里：与 ⑦c／⑦d 同族——都判"**纸上写的与程序里做的**一不一致"；
#   ⑦c 判"两件法律彼此对不对得上"，⑦d 判"实例地址归属"，⑦e 判"**本体声称的授权路，程序里有没有**"。
# 它盯的那件事（逐字）：本体 `_permissions._grant_via_ledger` 说"**改一次授权 ＝ 落一条事件**"
#   （逐字见 `ontology.json` 该键），而 `src/lib.rs` 的判定**读的是本体** ⇒ **那条路纸上有、程序里没有**。
# 判据（`scripts/verify/grant_path_guard.py`，三条，可自证）：G-01 声明在不在（不在 ⇒ **SKIP，不算绿**）／
#   G-01b 有没有声称"走账本事件"／G-02 `src/` 里有没有读那张格的代码（**没有 ⇒ 红**）／
#   G-03 授权判定的读法是否唯一。
# ★★ 接法是【**登记型**】：红了 ⇒ 打 ⚠️ ＋ **不阻断全闸**（用 `run_registered`，不是 `run_tail`）。
#   理由：它红的原因是【**设计已定·未落地**】—— **不是"谁改坏了"** ⇒ 该红、该被看见，但不该让全闸停
#   （先例：`s1_sys_probe2.sh` 的"另行登记（现状为红、如实记录）"）。★ 若日后要它阻断，改回 `run_tail` 即可。
# ★ 退出码约定（工具自述）：`0` 绿／SKIP（**SKIP 会显式打印，不算绿**）；`1` 有红；`2` **输入缺失＝不是通过**
#   ⇒ ★ `run_registered` 只对 **rc=1** 折算为登记；**rc=2 仍然阻断**。
run_registered 14 "授权路判据（本体声称的路 ↔ src/ 里有没有那条路）" python3 scripts/verify/grant_path_guard.py

echo
step "⑦f 值形状判据（落进账本的每一个值，必须有【已声明的形状载体】）"
# 为什么放在这里：与 ⑦c／⑦d／⑦e 同族——都判"**纸上写的与程序里做的**一不一致"；
#   ⑦f 判的是"**值**落在哪儿"：它必须落在 `_objects.<类型>.fields` 声明过的那一格上。
# 它盯的那件事（逐字）：`ontology.json` 的 `_objects.notice` 只说「`payload` 的形状**本体今天不声明它**」；
#   而 `src/ontology_instance/readmodel.rs` 对通告是 `"notice" => self.notices += 1,` ⇒ **只计数、不折叠**；
#   同件文档另写「**可选格**（`to`/`trace`/`params`/`payload`）**不进** `DeclaredCells`」⇒ **借它连"格"都不算**。
#   ⇒ **谁都能塞、没人判形状** ⇒ 那是"**套壳最容易回来的地方**"。
# 判据（`scripts/verify/value_shape_guard.py`，四条，可自证）：J1-01 类型已声明／J1-02 字段已声明／
#   J1-03 值合声明类型（含 `enum(...)` 越界）／J1-04 **通告不许带非空 `payload`**。
# ★★ 接法是【**登记型**】：红了 ⇒ 打 ⚠️ ＋ **不阻断全闸**（用 `run_registered`，不是 `run_tail`）。
#   理由与 ⑦e 同：存量红的原因是【**设计已定·未落地**】——那批值本来就借在没形状的口袋里，
#   **不是"谁改坏了"** ⇒ 该红、该被看见，但不该让全闸停。
# ★ 退出码约定（工具自述）：`0` 绿／SKIP（**SKIP 会显式打印 `STATUS=SKIP`，不算绿**）；`1` 有红；`2` **输入缺失＝不是通过**
#   ⇒ ★ `run_registered` 只对 **rc=1** 折算为登记；**rc=2 仍然阻断**。
run_tail 1 "值形状判据自证（五个反例必红、两个正控必绿、不适用必 SKIP）" python3 scripts/verify/value_shape_guard.py --self-test
run_registered 20 "值形状判据（值必须有已声明的形状载体；通告不许当口袋）" python3 scripts/verify/value_shape_guard.py --ontology src/ontology_definition/ontology.json --ledger "$SB/ledger.jsonl"

echo
step "⑦g 口属主判据（盘上那个口的属主 ↔ 法律里那条的 uid）"
# 为什么放在这里：与 ⑦e／⑦f 同族——都判"**纸上写的与机器上做的**一不一致"。
# 它盯的那件事（逐字，见 `scripts/verify/socket_uid_guard.py` 件头）：
#   `RuntimeDirectory=` 的**递归 chown** 会把 `/run/*.sock` 的属主**盖回**服务的 `User=`，
#   而法律 `channel.json` 的 `listeners` 说那个口属于别的 uid（如 `world://presence/omarchy` ⇒ 963）。
#   ⇒ 兑现的写法是 `ExecStartPre=+/bin/chown …`；而**"配了"不等于"生效"**，
#   且**最狠的一种是沉默**——法律写一个属主、盘上是另一个，链路一句警告都不打。
# 判据（三条，可自证）：S-01 盘上的口在法律里有人认／S-02 uid **逐字相等**／S-03 法律列的口都在盘上。
# ★★ 接法是【**登记型**】（与 ⑦e／⑦f 同）：该红、该被看见，但**不阻断全闸**。
# ★ 退出码约定（工具自述）：`0` 绿／SKIP（**SKIP 会显式打印，不算绿**）；`1` 有红；`2` **输入缺失＝不是通过**
#   ⇒ ★ `run_registered` 只对 **rc=1** 折算为登记；**rc=2 仍然阻断**（读不到不许折算成通过）。
run_tail 1 "口属主判据自证" python3 scripts/verify/socket_uid_guard.py --self-test
# ★★ 本步的输入是【机器面】的（`/etc/world-core/channel.json` ＋ `/run/world-core`），
#   而 `check.sh` 自己只用一次性 `mktemp` 沙箱（**沙箱里没有 `/etc`**）。
#   ⇒ 不设前置就喂机器路径：在没有渲染物的机器上守卫返 **rc=2**，
#   而 `run_registered` 对 rc=2 是**阻断**（"读不到不许折算成通过"）⇒ **全闸当场中止、结论行都打不出来**。
#   ★ 实测撞到过（审计 `G-03`）。处置＝**显式分岔**：
#     有机器面 ⇒ 真跑（登记型）；没有 ⇒ **打 ⏭ 并写明"未校验"**，**不阻断**。
#   ★ 两条路都不许把"没跑"读成"过了"：前者 rc=1 打 ⚠️，后者打 ⏭；**只有 rc=0 才是 ✅**。
if [ -r /etc/world-core/channel.json ] && [ -d /run/world-core ]; then
  run_registered 12 "口属主判据（盘上那个口 ↔ 法律里那条 uid）" python3 scripts/verify/socket_uid_guard.py --channel /etc/world-core/channel.json --rundir /run/world-core
else
  echo "  $MARK_SKIP 口属主判据（盘上那个口 ↔ 法律里那条 uid）—— **未校验**：本机没有 /etc/world-core/channel.json 或 /run/world-core"
  echo "  （★ 这一步**没跑**；★ **未校验 ≠ 通过**。有渲染物的机器上它会真跑，红了打 ⚠️、不阻断）"
  if [ "$CUR_STEP" -ge 0 ]; then STEP_KIND[$CUR_STEP]="SKIP"; fi
fi

echo
step "⑧ 规格层守卫（OpenSpec 层）"
# 为什么放在这里：`openspec validate` 只判**形态**（结构、每个 Scenario 恰好 4 个 `#`、delta 语法），
# 它**不查**那几件核心的事：证据行指向的测试是否真的存在（改名即失锚，且不会变红）、归档目录有没有
# `review.md`、默认档是不是融合档、编号桥有没有覆盖规格树下每条 Requirement、承载覆盖缺口的 change
# 还在不在。这些此前**只写在 schema 的文字里，没有任何执行者**——实测：一个**没有** `review.md` 的
# change `openspec archive --yes` 照样 rc=0 归档。`scripts/verify/spec_bridge.py` 就是它们的执行者。
# **判据条数与逐条结论一律以 `spec_bridge.py --json` 的 `passed`/`failed` 为准**，
# 本处文案不复述条数（skill §八：一个事实只有一个权威载体，数值一律现算）。
# 它自己也要能自证会红（`--self-test`：**每条**判据各造一个反例，反例不变红即判该守卫是装饰）。
# 仓库根由脚本自身位置向上定位（scripts/ → 仓库根）；VM 上已同步 `` 层，故两边都能跑。
run_tail 2 "规格层守卫自证（每条判据各造反例，反例必红）" python3 scripts/verify/spec_bridge.py --self-test
run_tail 8 "规格层守卫" python3 scripts/verify/spec_bridge.py
# 承接原 CI 里 `openspec validate --all --strict` 的**形态**面（NineDim 顶层不含 `openspec/`，
# 那个 CLI 的固定根没了 ⇒ 规格形态改由本仓判据判，**同样会红、且自带反例**）。
run_tail 1 "规格形态判据自证（正控＋每条一个反例）" python3 scripts/verify/spec_shape.py --self-test
run_tail 3 "规格形态判据（Requirement／Scenario／WHEN／THEN 齐备）" python3 scripts/verify/spec_shape.py

echo
step "⑨ 机核层守卫（WC-ATOM-001 §二 A-1／A-2／A-4：单意图／四件同夹／deps==import 且无环）"
# 为什么放在这里：`WC-ATOM-001`（原子化编程约定，本项目**强制**）§二 的六条约定里，
# A-1／A-2／A-4 这三条此前**没有执行者**——§四 那份机核清单自己逐条写着「未建」/「未建闸」。
# ⚠ **出处订正（2026-09-28）**：本步原写「§四 机核清单第 1–3 条」——
#   **§四 是"机核清单"（记谁在管、今天什么状态），判据正文在 §二**；且 §四 第 1 行
#   **没有**"（≤30 字）"这五个字。三条判据的真实出处如下：
#   ① A-1（§二）：每个模块有且只有一句 `intent`；出现并列两事（与／和／及）即报可疑。
#      ⚠ **「≤30 字」是本项目自定的阈值**（`WC-ATOM-001:24` 逐字声明"参照仓无此数、
#      不许说成参照仓的要求"）⇒ **不许**把它写成外部标准的要求。
#   ② A-4（§二）：从 `src/**/*.rs` 抽 `mod`／`use crate::`／根级裸名 `use <mod>::` 建模块图，
#      声明依赖集必须**逐模块逐边等于**真实 import 集，且图必须无环（拓扑排序失败即红）；
#   ③ A-2（§二）：每模块的实现／测试／契约三件都要有落点（本仓 `tests/` 与 `src/` 不同夹，
#      故按"可指认"判：实现＝登记表源码路径真实存在；测试＝`tests/` 里有用例能指到它；
#      契约＝规格里一条 Requirement 的证据行）。
# ⚠ **本节另一处过期陈述（2026-09-28 删）**：原写「今天这三条**应该是红的**（本项目尚未按
#   原子化组织）——红就如实报红」。那句在写下时属实；此后机核工区把三条判据清理到转绿
#   （`world-core-gate.yml` 的 `module-graph` 作业注有该轮读数），**故不再预判红绿**：
#   **红绿一律以本步当场的原始输出为准**（skill §八：读数现取，不写死）。
run_tail 12 "机核层守卫（WC-ATOM-001 §二 A-1／A-2／A-4：单意图／四件同夹／deps==import 且无环）" python3 scripts/verify/module_graph.py

# ── 结论行：**由步骤清单生成**，不手写 ────────────────────────────────
# 为什么搬到这里、为什么是生成的：原结论行**手写在检查中途**（第 ⑧ 步之后、第 ⑨ 步之前），
#   于是第 ⑨ 步若失败，"全通过"四个字**已经先打印出去了**——那正是本项目最忌的
#   "把没做到写成做到了"。且它手写的步骤名串只列到「规格层守卫」，第 ⑨ 步落地即漏报。
# 现在：① 位置在**全部步骤之后**；② 清单来自 `step()` 累积的 `STEPS`——加一步自动进清单；
#   ③ 步数由 `${#STEPS[@]}` 现算，不写死（skill §八：一个事实只有一个权威载体，数值一律现算）。
echo
# 结论行原来对每一步都打 `✅`——**SKIP 的步因此在结论里也长成绿的**（2026-10-03 实测的假证）。
# 现在：标记由 `STEP_KIND` 现取（`step_marker.py` 渲染），**只有 PASS 配打 ✅**；
#   ⏭ 的步如实带一句"**未校验**"。
# ⚠ 首行文案**不改**（`docs/证据/证据-EV-009.md` 等件逐字抄过它；改了那些抄件当场过期）——
#   与既有步的判据/文案"一字不动"同一条纪律；**新增的信息一律另起一行**。
echo "== 结论：全通过（本脚本实跑的步骤，逐条如下）=="
_skipped=0
_registered=0
for _i in "${!STEPS[@]}"; do
  case "${STEP_KIND[$_i]}" in
    SKIP) printf '   %s %s（**未校验**——这一步只是没跑）\n' "$MARK_SKIP" "${STEPS[$_i]}"; _skipped=$((_skipped + 1)) ;;
    REG)  printf '   %s %s（**登记型红**——该红、该被看见；按【设计已定·未落地】登记，**不阻断全闸**）\n' "$MARK_REG" "${STEPS[$_i]}"; _registered=$((_registered + 1)) ;;
    *)    printf '   %s %s\n' "$MARK_PASS" "${STEPS[$_i]}" ;;
  esac
done
printf '   共 %d 步（由 STEPS 长度现算，不写死）\n' "${#STEPS[@]}"
if [ "$_skipped" -gt 0 ]; then
  printf '   其中**未校验** %d 步 ⇒ 本行的"全通过"**不含**它们（未校验 ≠ 通过）\n' "$_skipped"
fi
# ★ 2026-10-05 增：**登记型红**单独报一行（★ 新增信息一律另起一行，首行文案一字不动）。
#   为什么必须单独报：登记型红的 `rc` 被折算成 0 ⇒ 若不单列，读者会把它读成"这一步过了"。
#   ★ 三档**不许混**：⏭＝**没跑**（未校验）／⚠️＝**跑了、判了、如实红**（设计已定·未落地）／✅＝**通过**。
if [ "$_registered" -gt 0 ]; then
  printf '   其中**登记型红** %d 步（⚠️）⇒ 本行的"全通过"**不含**它们（如实红 ≠ 通过；它们是【设计已定·未落地】，不是"谁改坏了"）\n' "$_registered"
fi
