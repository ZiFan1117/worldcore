#!/usr/bin/env bash
# system_acceptance.sh —— **系统级验收用例**（L3/L4 之间的端到端），跑**真实二进制**
#
# ## 为什么需要它
#
# `WC-RTM-001.csv` 里有 4 条 P0 需求当时**只有单元/集成用例，没有系统级用例**
# （`REQ-F-001`、`REQ-F-002`、`REQ-F-010`、`REQ-N-003`），`trace_matrix.py` 为此长期报
# 4 条 WARN。而 `WC-SQAP-001` 的 S5 退出准则要求把 `RTM_STRICT` 翻成 `true`——
# ⚠ **2026-09-26 订正（原文写"一旦翻转，这 4 条就会由 WARN 变 ERROR"——该声明与实现不符）**：
#    `tools/trace_matrix.py` 的"缺少系统级/验收级测试用例"检查（约 `:352-355`）**恒为 WARN**，
#    `--strict` 只作用于**状态列**（约 `:361-362`）⇒ **`RTM_STRICT=true` 不会**让本项由 WARN 变 ERROR。
#    实测（提交 7166398）：非严格 rc=0 / ERROR=0 / WARN=31；`--strict` rc=1 / ERROR=10（**全部是状态列**）/ WARN=31。
#    ⇒ 本脚本补齐这 4 条系统级用例的价值**不因该机制而改变**（它提供的是真实证据），
#      但"翻转开关即自动变红"的**升级机制不存在**，登记见 `WC-SCMP-001` §8.4 **G-30**/**G-43**。
#
# 本脚本把"补 4 条系统级用例"落在**可执行的命令**上，而不是填进表格里的编号：
# 全部经 `"${CARGO_TARGET_DIR:-target}"/debug/world-core` 这个**真实产物**、在**一次性沙箱**账本上端到端执行。
# 与 `cargo test` 的分工：`cargo test` 验模块与接口（L1/L2），本脚本验**产物本身**（L3）：
# 只看退出码、真实文件字节与命令输出——**不 import 任何 Rust 代码**。
#
# ## 覆盖
#
# | 用例 | 需求 | 端到端断言 |
# |---|---|---|
# | `TC-037` | `REQ-F-001` 语义事件是唯一真相 | 只追加（旧行逐字节不变）、`read` 回读一致、**`state`/`project` 不改账本一个字节**（无第二条写路径） |
# | `TC-038` | `REQ-F-002` 信封字段完备且带版本 | 落盘行**逐字段**断言 8 个必填字段（对真实文件，不是内存对象）；缺必填字段的提交被拒且**原事件不落笔** |
# | `TC-039` | `REQ-F-010` 状态是账本的投影 | `state` 幂等；投影首行的 `state=`/`last_seq=` 与 `state` 一致；**反假**：追加后指纹必须变（常量状态会红） |
# | `TC-040` | `REQ-N-003` 启动即校验本体 | 缺文件 / 坏 JSON / 版本不符 **三种都拒绝启动**（rc=2），正常本体 rc=0 且打印 READY |
# | `TC-041` | 领域不变量与只读边界（R4 工作项 `W-01`/`W-02`/`W-03`/`W-04`/`P-01`） | 事件身份唯一（同 id 两行 ⇒ 拒启）／账本缺号 ⇒ 拒启／**只读命令在含半行的账本上逐字节不改 L1**／属主不符与 `--owner-uid` 非法都拒启／M08 检查点与 M09 通道在生产路径可调用且"别人连不上" |
#
# ## 纪律
#
# - 全程 `mktemp -d` 一次性沙箱，退出即删；**绝不触碰真实账本**（同 `check.sh`）；
# - 自带 `--self-test`：先证明**本脚本的判定会红**（"一个从不失败的检查不是检查，是装饰"）；
# - 不依赖网络、不依赖墙钟、不依赖执行顺序。
#
# 用法：`bash tools/system_acceptance.sh`（在 world-core/ 内或任意位置）
#       `bash tools/system_acceptance.sh --self-test`（只跑判定器自证）
# 退出码：0 = 全通过；1 = 有断言失败；2 = 前置条件不满足（缺二进制且构建失败）
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2
BIN="${CARGO_TARGET_DIR:-target}"/debug/world-core

PASS=0
FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

assert_eq() { # assert_eq <描述> <期望> <实际>
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1（期望 [$2]，实得 [$3]）"; fi
}
assert_ne() { # assert_ne <描述> <不该等于> <实际>
  if [ "$2" != "$3" ]; then ok "$1"; else bad "$1（不应等于 [$2]）"; fi
}
assert_rc() { # assert_rc <描述> <期望退出码> <实际退出码>
  assert_eq "$1" "$2" "$3"
}
assert_has() { # assert_has <描述> <文本> <正则>
  if printf '%s' "$2" | grep -Eq "$3"; then ok "$1"; else bad "$1（输出里找不到 /$3/：$(printf '%s' "$2" | head -3 | tr '\n' ' '))"; fi
}

# ── 判定器自证（先证明它会红）─────────────────────────────────────────
if [ "${1:-}" = "--self-test" ]; then
  echo "== system_acceptance.sh 判定器自证 =="
  before=$FAIL
  assert_eq "自证：故意断言 1=2" "1" "2"
  assert_ne "自证：故意断言 1≠1" "1" "1"
  if [ "$FAIL" -eq $((before + 2)) ]; then
    echo "  ✅ 自证通过：两个假命题都被判为失败（本判定器不是装饰）"
    exit 0
  fi
  echo "  ❌ 自证失败：假命题竟被判为通过"
  exit 1
fi

# ── 前置：二进制（缺失则构建一次；CI 的 smoke 作业此前已构建）──────────
if [ ! -x "$BIN" ]; then
  echo "[前置] 未找到 $BIN，执行一次 cargo build --locked --quiet"
  cargo build --locked --quiet || { echo "  ❌ 构建失败"; exit 2; }
fi

SB="$(mktemp -d)"
trap 'rm -rf "$SB"' EXIT
# 755 而非 700：`TC-041㉕` 要证明"**别的 uid 连不上**"，
# 若沙箱目录本身不可穿越，那条断言会因**目录权限**而通过（与套接字权限无关）——那是假绿。
# 755 与 `check.sh` 的沙箱同口径，且组/其他人仍**不可写**（guard 的静态墙不受影响）。
chmod 755 "$SB"
cp src/ontology_definition/ontology.json src/gate/policy.json "$SB"/
chmod 600 "$SB/src/ontology_definition/ontology.json" "$SB/src/gate/policy.json"
L="$SB/ledger.jsonl"

W() { "$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$L" --policy "$SB/src/gate/policy.json" "$@"; }
# 带外部本体的调用（TC-040 用）
WO() { # WO <ontology-path> [args...]
  local ont="$1"
  shift
  "$BIN" --ontology "$ont" --ledger "$L" --policy "$SB/src/gate/policy.json" "$@"
}
sha() { sha256sum "$1" | cut -d' ' -f1; }

echo "== world-core 系统级验收（真实二进制 $BIN）=="
echo "  目录 : $(pwd)"
echo "  沙箱 : $SB"
echo "  用例 : TC-037 / TC-038 / TC-039 / TC-040 / TC-041"

# ══ TC-037 · REQ-F-001 语义事件是唯一真相 ═══════════════════════════
echo
echo "── TC-037 · REQ-F-001 语义事件是唯一真相（只追加 + 无第二条写路径）──"
# ⚠ 本脚本以下所有 `append change` 的**主体与字段都取出厂本体里已声明的格子**
#   （`ontology.json` 的 `concepts`：`notice.muted` ／ `job.status`）——
#   书 §5.3「声明以外的东西不许落账」的执行者是 `src/ontology_definition/mod.rs::check_concepts`，
#   原先的 `world://sys/*#p` 两个名字都没声明过 ⇒ 这些写入当场 rc=2、断言整片变红。
#   换的是**落笔的格子**，不是判据：条数／seq／逐字节不变／指纹必变这些断言一字未动。
W append change '{"subject":"world://notice/a","path":"muted","before":null,"after":true}' >/dev/null 2>&1
assert_rc "① 首次追加成功（rc=0）" 0 $?
assert_eq "② 账本恰有 1 行" 1 "$(wc -l <"$L" | tr -d ' ')"
assert_eq "③ read 回读 1 条" 1 "$(W read | wc -l | tr -d ' ')"
assert_eq "④ 首条 seq=1" 1 "$(W read | head -1 | python3 -c 'import json,sys; print(json.load(sys.stdin)["seq"])')"

cp "$L" "$SB/snapshot.jsonl"
W state >/dev/null 2>&1
W project language >/dev/null 2>&1
W project check >/dev/null 2>&1
assert_eq "⑤ state/project 执行后账本**逐字节**不变（无第二条写路径）" "$(sha "$SB/snapshot.jsonl")" "$(sha "$L")"

W append change '{"subject":"world://notice/b","path":"muted","before":null,"after":false}' >/dev/null 2>&1
assert_rc "⑥ 第二次追加成功（rc=0）" 0 $?
assert_eq "⑦ 账本只增：2 行" 2 "$(wc -l <"$L" | tr -d ' ')"
assert_eq "⑧ 旧行未被改写（逐字节）" "$(head -1 "$SB/snapshot.jsonl")" "$(head -1 "$L")"
assert_eq "⑨ seq 连续（1,2）" "1 2" "$(W read | python3 -c 'import json,sys; print(" ".join(str(json.loads(l)["seq"]) for l in sys.stdin))')"

# ══ TC-038 · REQ-F-002 信封字段完备且带版本 ══════════════════════════
echo
echo "── TC-038 · REQ-F-002 事件信封字段完备且带版本 ──────────────"
LAST="$(tail -1 "$L")"
ENVFIELDS="$(printf '%s' "$LAST" | python3 -c '
import json,sys
ev = json.load(sys.stdin)
need = ["world","kind","id","seq","at","actor","flags","body"]
missing = [k for k in need if k not in ev]
print("MISSING=" + ",".join(missing))
print("WORLD=" + str(ev["world"]))
')"
assert_eq "① 落盘行含全部 8 个必填信封字段" "MISSING=" "$(printf '%s' "$ENVFIELDS" | grep '^MISSING=')"
assert_eq "② 落盘行的 world 版本 = 1" "WORLD=1" "$(printf '%s' "$ENVFIELDS" | grep '^WORLD=')"

BEFORE_LINES="$(wc -l <"$L" | tr -d ' ')"
# 为什么主体也换成已声明的：本条要验的是"**缺必填字段** ⇒ 拒且不落笔"。
# 主体若用未声明的名字，拒绝就变成"两个理由都成立"（缺 before ∧ 实体没声明）——
# 那时 `④ 点名 before` 过了也说明不了是缺字段拦下的。用已声明的 `notice/c` ＋ 已声明的 `muted`，
# 唯一的拒绝理由就只剩"缺 before"，判据强度只增不减。
OUT="$(W append change '{"subject":"world://notice/c","path":"muted","after":true}' 2>&1)"
RC=$?
assert_rc "③ 缺必填字段（change 缺 before）被拒（rc=2）" 2 "$RC"
assert_has "④ 拒绝理由**点名**缺失字段" "$OUT" 'before'
assert_eq "⑤ 被拒事件**不落笔**（账本行数不变）" "$BEFORE_LINES" "$(wc -l <"$L" | tr -d ' ')"
if grep -q 'world://notice/c' "$L"; then bad "⑥ 被拒事件的内容不得出现在账本里"; else ok "⑥ 被拒事件的内容不得出现在账本里"; fi

# ══ TC-039 · REQ-F-010 状态是账本的投影 ═════════════════════════════
echo
echo "── TC-039 · REQ-F-010 状态是账本的投影 ─────────────────────"
S1="$(W state --json)"
S2="$(W state --json)"
assert_eq "① state 是纯函数（两次调用逐字节相同）" "$S1" "$S2"
assert_eq "② state 的 last_seq = 账本条数" "2" "$(printf '%s' "$S1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["last_seq"])')"

PC="$(W project check)"
FP1="$(printf '%s' "$PC" | sed -n 's/.*指纹=\([^ ]*\).*/\1/p')"
HDR_STATE="$(W project language | head -1 | sed -n 's/.*state=\([^ ]*\).*/\1/p')"
HDR_SEQ="$(W project language | head -1 | sed -n 's/.*last_seq=\([0-9]*\).*/\1/p')"
assert_eq "③ 投影首行的 state= 与 project check 的指纹一致（同一个读模型）" "$FP1" "$HDR_STATE"
assert_eq "④ 投影首行的 last_seq 与账本条数一致" "2" "$HDR_SEQ"

W append change '{"subject":"world://notice/d","path":"muted","before":null,"after":true}' >/dev/null 2>&1
FP2="$(W project check | sed -n 's/.*指纹=\([^ ]*\).*/\1/p')"
assert_ne "⑤ 反假：追加一条后状态指纹**必须变**（常量状态会在此变红）" "$FP1" "$FP2"

# ══ TC-040 · REQ-N-003 启动即校验本体 ═══════════════════════════════
echo
echo "── TC-040 · REQ-N-003 启动即校验本体（缺失/损坏/版本不符均拒启）──"
printf 'this is not json\n' >"$SB/bad.json"
OUT="$(WO "$SB/bad.json" check 2>&1)"
assert_rc "① 坏 JSON 本体 → 拒绝启动（rc=2）" 2 "$?"
OUT="$(WO "$SB/does-not-exist.json" check 2>&1)"
assert_rc "② 本体文件缺失 → 拒绝启动（rc=2）" 2 "$?"

python3 - "$SB/src/ontology_definition/ontology.json" "$SB/version2.json" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    doc = json.load(f)
doc["world"] = 2
with open(dst, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False)
PY
chmod 600 "$SB/version2.json"
OUT="$(WO "$SB/version2.json" check 2>&1)"
assert_rc "③ 本体版本不符（world=2）→ 拒绝启动（rc=2）" 2 "$?"
assert_has "④ 版本不符的理由里点出问题（版本/世界版本）" "$OUT" '版本|world'

OUT="$(W check 2>&1)"
assert_rc "⑤ 对照：正常本体 → rc=0" 0 "$?"
assert_has "⑥ 对照：正常本体打印 READY" "$OUT" 'READY'

# ══ TC-041 · 领域不变量与只读边界（W-01 / W-02 / W-04 / P-01 / W-03）════
# 为什么加这一段：审查实测「7 个突变里 26 项只捕获 1 个」——
# 把 `new_id()` 改成常量、关掉 SeqGap 校验、把默认拒绝改成 Allow，本套用例**全部仍 26/26 全绿**。
# 「一个抓不住故障的验收面不是验收面，是装饰」。以下每条都把相应的不变量做成**会红的断言**。
echo
echo "── TC-041 · 事件身份唯一（W-01）／缺号拒启（W-02）／只读不写 L1（P-01）／属主断言（W-04）／M08·M09 接线（W-03）──"

# 用**另一本账本**跑子用例（原件 $L 不许被这些反例污染）
WL() { # WL <ledger> [args...]
  local lg="$1"
  shift
  "$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$lg" --policy "$SB/src/gate/policy.json" "$@"
}
mk_torn() { # mk_torn <src> <dst>  —— 复制账本并追加一行**半行**（无换行结尾）
  cp "$1" "$2"
  chmod 600 "$2"
  printf '{"world":1,"kind":"change","id":"torn-tail"' >>"$2"
}

# —— W-01 写入侧：事件身份必须唯一 ——
IDN="$(W read | python3 -c 'import json,sys; print(len({json.loads(l)["id"] for l in sys.stdin}))')"
LN="$(W read | wc -l | tr -d ' ')"
assert_eq "① 账本内**互异**事件身份个数 == 事件条数（恒同 id 的突变在此变红）" "$LN" "$IDN"
ID1="$(W read | sed -n 1p | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
ID2="$(W read | sed -n 2p | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
assert_ne "② 前两条事件的身份互不相同（同 id 再提交即重复提交）" "$ID1" "$ID2"

cp "$L" "$SB/dup.jsonl"
python3 - "$SB/dup.jsonl" <<'PY'
import json, sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines()
a = json.loads(lines[0]); b = json.loads(lines[1])
b["id"] = a["id"]                       # 注入：第二行**冒用**第一行的 id
lines[1] = json.dumps(b, ensure_ascii=False, separators=(",", ":"))
open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
chmod 600 "$SB/dup.jsonl"
OUT="$(WL "$SB/dup.jsonl" check 2>&1)"
assert_rc "③ 账本出现同 id 两行 ⇒ 拒绝启动（rc=2）" 2 "$?"
assert_has "④ 拒绝理由**点名** DuplicateId（不是笼统的「损坏」）" "$OUT" 'DuplicateId'

# —— W-02 启动侧：缺号即拒启（关掉 SeqGap 校验 ⇒ 本断言必红）——
cp "$L" "$SB/gap.jsonl"
python3 - "$SB/gap.jsonl" <<'PY'
import json, sys
p = sys.argv[1]
L = open(p, encoding="utf-8").read().splitlines()
del L[1]                                # 注入：删中间一行 ⇒ 后面的 seq 跳号
open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
PY
chmod 600 "$SB/gap.jsonl"
OUT="$(WL "$SB/gap.jsonl" check 2>&1)"
assert_rc "⑤ 账本缺号（删中间一行）⇒ 拒绝启动（rc=2）" 2 "$?"
assert_has "⑥ 拒绝理由**点名** SeqGap（不是笼统的「损坏」）" "$OUT" 'SeqGap'

# —— P-01 只读边界：只读命令不得改 L1 一个字节（**在含半行的账本上**验）——
mk_torn "$L" "$SB/torn.jsonl"
B4="$(sha "$SB/torn.jsonl")"
S4="$(stat -c%s "$SB/torn.jsonl")"
for sub in "state" "read" "project language" "check"; do
  WL "$SB/torn.jsonl" $sub >/dev/null 2>&1 || true
done
assert_eq "⑦ 四个只读命令后账本**逐字节**不变（P-01：只读接口不得写 L1）" "$B4" "$(sha "$SB/torn.jsonl")"
assert_eq "⑧ 且**长度**不变（末尾半行未被截断）" "$S4" "$(stat -c%s "$SB/torn.jsonl")"
WL "$L" append change '{"subject":"world://notice/tc041","path":"muted","before":null,"after":true}' >/dev/null 2>&1
assert_rc "⑨ 对照：**可写**路径（append）仍会丢弃半行 ⇒ 走的是另一条口径（此账本无半行，故 rc=0）" 0 "$?"

# —— W-04 属主断言（`--owner-uid`）＋ P-16 强制化（打错 uid 不得静默失效）——
cp "$L" "$SB/owned.jsonl"
chmod 600 "$SB/owned.jsonl"
if [ "$(id -u)" = "0" ]; then
  OUT="$("$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/owned.jsonl" --policy "$SB/src/gate/policy.json" --owner-uid 0 check 2>&1)"
  assert_rc "⑩ 属主断言相符（uid=0）⇒ 正常启动 rc=0（对照）" 0 "$?"
  OUT="$("$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/owned.jsonl" --policy "$SB/src/gate/policy.json" --owner-uid 1000 check 2>&1)"
  assert_rc "⑪ 属主**不符**（断言 1000、实为 0）⇒ 拒启 rc=2（W-04 判据）" 2 "$?"
  OUT="$("$BIN" --ontology "$SB/src/ontology_definition/ontology.json" --ledger "$SB/owned.jsonl" --policy "$SB/src/gate/policy.json" --owner-uid abc check 2>&1)"
  assert_rc "⑫ --owner-uid 非法 ⇒ 拒启 rc=1（P-16：不得静默变成「不做断言」）" 1 "$?"
  assert_has "⑬ 拒绝理由点名 BadOwnerUid" "$OUT" 'BadOwnerUid'
else
  echo "  【未能校验】属主断言三格（当前 uid=$(id -u) ≠ 0，无法 chown/跨 uid 验证）"
fi

# —— W-03 接线：M08 检查点（生产路径可调用）——
H="$(W --help 2>&1)"
assert_has "⑭ CLI 暴露 M08 检查点入口（接线判据①：生产路径可调用）" "$H" 'checkpoint write'
assert_has "⑮ CLI 暴露 M09 通道入口（接线判据①：生产路径可调用）" "$H" 'channel bind'
OUT="$(W checkpoint write "$SB/cp.json" 2>&1)"
assert_rc "⑯ M08 capture+write 可调用（rc=0）" 0 "$?"
OUT="$(W checkpoint verify "$SB/cp.json" 2>&1)"
assert_rc "⑰ M08 verify：快照与账本前 base_seq 条一致（rc=0）" 0 "$?"
FP_FAST="$(W checkpoint resume "$SB/cp.json" 2>&1 | sed -n 's/.*快路径指纹 : //p')"
FP_FULL="$(W state 2>&1 | sed -n 's/.*指纹 : //p')"
assert_eq "⑱ M08 resume：从快照续算 == 全量重算（缓存不是第二真相）" "$FP_FULL" "$FP_FAST"
printf '{"checkpoint":1,"base_seq":999,"digest":"bogus","state":{}}\n' >"$SB/badcp.json"
chmod 600 "$SB/badcp.json"
OUT="$(W checkpoint verify "$SB/badcp.json" 2>&1)"
assert_ne "⑲ M08 反例：坏快照**必须**被拒（rc≠0）" 0 "$?"
rm -f "$SB/cp.json"
OUT="$(W state 2>&1)"
assert_rc "⑳ M08：删掉快照后 state 仍 rc=0（缓存可删、结论不变）" 0 "$?"
assert_eq "㉑ 且删快照前后指纹不变" "$FP_FULL" "$(printf '%s' "$OUT" | sed -n 's/.*指纹 : //p')"

# —— W-03 接线：M09 通道（权限即身份）——
# ⚠ 套接字**不能放在 `/tmp` 下**：`guard::assert_not_other_writable` 会同时看**所在目录**，
#   而 `/tmp` 是 1777 —— `channel bind` 会（正确地）拒绝。故另开一个"祖先目录也不可被他人写"的目录。
SOCKDIR="$(mktemp -d -p /root wc-ch.XXXXXX 2>/dev/null || true)"
if [ -n "$SOCKDIR" ]; then
  printf '{"channel":1,"listeners":[{"socket":"%s","actor":"world://agent/tc041","uid":0}]}\n' "$SOCKDIR/ch.sock" >"$SOCKDIR/channel.json"
  chmod 600 "$SOCKDIR/channel.json"
  # ★ T1／AC-1：受理路径按**法律**（`--policy` 的 `listeners`）判在不在册 ⇒
  #   夹具必须把这条**临时口**写进**自己的法律**（判据的会红条件一字未动）。
  python3 - "$SB/src/gate/policy.json" "$SOCKDIR/ch.sock" <<'PY'
import json, sys
p, sock = sys.argv[1], sys.argv[2]
d = json.load(open(p, encoding="utf-8"))
d.setdefault("listeners", []).append(
    {"socket": sock, "actor": "world://agent/tc041", "owner": "fixture"})
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
  OUT="$(W --channel "$SOCKDIR/channel.json" channel bind "$SOCKDIR/ch.sock" 2>&1)"
  assert_rc "㉒ M09 bind 可调用（rc=0）" 0 "$?"
  MOD_UID="$(stat -c '%a %u' "$SOCKDIR/ch.sock" 2>/dev/null)"
  assert_eq "㉓ M09「权限即身份」：套接字为 0600 且属主 == 配置 uid" "600 0" "$MOD_UID"
  # 「别人连不上」：同一条连接，root 通得过、非 root 被内核拒（EACCES）。
  # 这是 P-10 指出**从未被执行过**的那条路径——原来的用例用 UnixListener::bind 绕过了 bind()。
  if command -v setpriv >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
    W --channel "$SOCKDIR/channel.json" channel accept "$SOCKDIR/ch.sock" >"$SOCKDIR/acc.out" 2>&1 &
    ACC=$!
    ROOT_RC=1
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
      if python3 - "$SOCKDIR/ch.sock" >"$SOCKDIR/root_conn.txt" 2>&1 <<'PY'
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sys.argv[1])
# 为什么通告的主体也换成已声明的：这是**检查用数据**，按同一条规矩（检查用的数据必须是已声明的）
# 不该拿未声明的名字当主体。功能上无差别——`concepts` 只管 `change`（`notice.subject` 的语义是
# "这条通告关于谁"，不是"改了哪一格"，见 `src/ontology_definition/mod.rs::check_concepts` 的文档），
# 但探针数据里不留未声明的名字，读的人就不必去分辨"这个 `sys` 到底该不该在册"。
s.sendall(b'{"kind":"notice","body":{"type":"tc041","subject":"world://notice/tc041","payload":{}}}\n')
print(s.recv(65536).decode("utf-8", "replace").strip())
PY
      then
        ROOT_RC=0
        break
      fi
      ROOT_RC=$?
      sleep 0.25
    done
    OUTB="$(setpriv --reuid=65534 --regid=65534 --clear-groups python3 - "$SOCKDIR/ch.sock" 2>&1 <<'PY'
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sys.argv[1])
print("CONNECTED")
PY
)"
    OUTB_RC=$?
    wait "$ACC" 2>/dev/null || true
    assert_rc "㉔ M09 正例：身份 uid 的连接可建立并落笔（rc=0）" 0 "$ROOT_RC"
    assert_ne "㉕ M09 反例：**别的 uid 连不上**（内核在 connect 处拒绝）" 0 "$OUTB_RC"
    assert_ne "㉖ 且失败理由不是「连接成功」（输出里不得出现 CONNECTED）" "CONNECTED" "$(printf '%s' "$OUTB" | tail -1)"
  else
    echo "  【未能校验】跨 uid 连接反例（缺 setpriv 或非 root）"
  fi
  rm -rf "$SOCKDIR"
else
  echo "  【未能校验】M09 通道接线（无法在「祖先目录不可被他人写」的位置建套接字目录）"
fi

# ══ 汇总 ═══════════════════════════════════════════════════════════
echo
echo "== 汇总：通过 $PASS 项，失败 $FAIL 项 =="
if [ "$FAIL" -ne 0 ]; then
  echo "== 结论：不通过（系统级验收用例有红灯）=="
  exit 1
fi
echo "== 结论：全通过（TC-037 / TC-038 / TC-039 / TC-040 / TC-041 端到端）=="
