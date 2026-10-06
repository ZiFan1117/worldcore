#!/usr/bin/env bash
# CON-01 原型（v2，2026-09-26 加固）：门禁不可绕过 —— 跨 uid 实测
#
# v1 的方法论缺陷（由 WC-RV-R2-001 安全评审 S-18 指出，本版逐条修）：
#   F1 v1 的 expect_denied **只断言 rc != 0** ⇒ 命令找不到/参数错/runuser 失败
#      都会被记成"被拒"。本版改为：断言 uid 自证 + stderr 含具体拒绝原因 + rc != 0。
#   F2 v1 **不断言通过数** ⇒ 删掉任意断言仍"通过"。本版断言 EXPECTED 常量。
#   F3 v1 把"二进制在 /root（0700）里 agent 进不去"算作门禁的功劳。本版把它
#      单独列为**观察项**，不计分；并**新增**真正该测的那一格：
#      「agent 能到达二进制时，仍进不去门禁」。
#   F4 v1 的 ③ 实际证明的是**目录权限**而非账本文件权限。本版如实标注范围。
#
# ⚠️ 本脚本只读地使用被测程序；破坏性操作全在一次性沙箱 /tmp/con01* 内。
set -u
LC_ALL=C
export LC_ALL

CORE=/root/world/world-core/"${CARGO_TARGET_DIR:-target}"/debug/world-core
SRC=/root/world/world-core
SANDBOX=/tmp/con01
RUNBOX=/tmp/con01-run        # agent 可进入的"运行盒"（含二进制副本与法律）
EXPECTED_PASS=14             # 期望通过数（删断言即失败）
PASS=0; FAIL=0

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# 以 agent 身份执行，并**验证失败原因**（不是只看退出码）
expect_denied() { # $1=描述 $2=命令 $3=期望出现在 stderr 的原因（默认 Permission denied）
  local desc="$1" cmd="$2" why="${3:-Permission denied}"
  local out rc uid
  out=$(runuser -u agent -- sh -c "id -u >/dev/null; $cmd" 2>&1); rc=$?
  uid=$(runuser -u agent -- id -u 2>/dev/null)
  if [ "$uid" != "1001" ]; then bad "$desc —— agent uid 不是 1001（实得 '$uid'），测试前提不成立"; return; fi
  if [ $rc -eq 0 ]; then bad "$desc —— **居然成功了**：$out"; return; fi
  if ! echo "$out" | grep -qi "$why"; then
    bad "$desc —— 失败了但原因不是 '$why'（rc=$rc）：$(echo "$out" | head -1 | cut -c1-90)"; return
  fi
  ok "$desc（rc=$rc；原因含「$why」；uid 自证 1001）"
}

expect_refuse() { # 世界核心因静态墙拒绝启动（root 运行）
  local desc="$1"; shift
  local out rc
  out=$(sh -c "$*" 2>&1); rc=$?
  if [ $rc -ne 0 ] && echo "$out" | grep -q '不可绕过检查未通过'; then ok "$desc（rc=$rc）"
  else bad "$desc —— 未被拒绝（rc=$rc）：$(echo "$out" | head -1)"; fi
}

echo "=============================================================="
echo " CON-01 v2：门禁不可绕过（跨 uid）—— 加固版"
echo " 主机: $(uname -sr)   uid(root)=$(id -u)   被测: $CORE"
echo "=============================================================="

id agent >/dev/null 2>&1 || useradd -M -s /usr/bin/nologin agent
rm -rf "$SANDBOX" "$RUNBOX"; mkdir -p "$SANDBOX" "$RUNBOX"
mkdir -p "$SANDBOX/src/ontology_definition" "$SANDBOX/src/gate"
cp "$SRC/src/ontology_definition/ontology.json" "$SANDBOX/src/ontology_definition/ontology.json"
cp "$SRC/src/gate/policy.json" "$SANDBOX/src/gate/policy.json"
chown -R root:root "$SANDBOX"; chmod 755 "$SANDBOX"
chmod 644 "$SANDBOX/src/ontology_definition/ontology.json" "$SANDBOX/src/gate/policy.json"
( cd "$SANDBOX" && "$CORE" --ledger "$SANDBOX/ledger.jsonl" --ontology "$SANDBOX/src/ontology_definition/ontology.json" \
    --policy "$SANDBOX/src/gate/policy.json" check ) | tail -1
chmod 600 "$SANDBOX/ledger.jsonl"
echo "沙箱：$(ls -ld "$SANDBOX" | awk '{print $1, $3, $4}')  agent uid=$(id -u agent)"
echo

echo "── ① 被管者改配置 ──────────────────────────────────────────"
expect_denied "agent 向 policy.json 追加内容" "echo '{}' >> $SANDBOX/src/gate/policy.json"
expect_denied "agent 就地改写 policy.json"   "printf 'x' > $SANDBOX/src/gate/policy.json"
expect_denied "agent 用 sed 改 policy.json"  "sed -i 's/false/true/' $SANDBOX/src/gate/policy.json"

echo
echo "── ② 被管者替换配置（文件权限挡不住的那条路径）────────────"
expect_denied "agent 删除 policy.json"   "rm -f $SANDBOX/src/gate/policy.json"
expect_denied "agent 重命名 policy.json" "mv $SANDBOX/src/gate/policy.json $SANDBOX/policy.bak"
expect_denied "agent 在沙箱里新建文件"   "touch $SANDBOX/evil.json"

echo
echo "── ③ 被管者直写账本 ⚠️ 范围注明：本组证明的是【目录级】隔离 ──"
echo "   （沙箱目录 0755/root ⇒ agent 在目录层就要 w+x 而失败，未走到文件位判定）"
expect_denied "agent 向账本追加一行" "echo '{}' >> $SANDBOX/ledger.jsonl"
expect_denied "agent 覆写账本"       "printf '' > $SANDBOX/ledger.jsonl"
expect_denied "agent 删除账本"       "rm -f $SANDBOX/ledger.jsonl"

echo
echo "── ④ 侥幸绕过静态墙时：世界核心必须拒绝启动（第二道闸）────"
chmod 666 "$SANDBOX/src/gate/policy.json"
expect_refuse "policy.json 0666 时启动被拒" "$CORE --ontology $SANDBOX/src/ontology_definition/ontology.json --ledger $SANDBOX/ledger.jsonl --policy $SANDBOX/src/gate/policy.json check"
chmod 644 "$SANDBOX/src/gate/policy.json"
chmod 777 "$SANDBOX"
expect_refuse "沙箱目录 0777 时启动被拒" "$CORE --ontology $SANDBOX/src/ontology_definition/ontology.json --ledger $SANDBOX/ledger.jsonl --policy $SANDBOX/src/gate/policy.json check"
chmod 755 "$SANDBOX"
chmod 666 "$SANDBOX/ledger.jsonl"
expect_refuse "账本 0666 时启动被拒" "$CORE --ontology $SANDBOX/src/ontology_definition/ontology.json --ledger $SANDBOX/ledger.jsonl --policy $SANDBOX/src/gate/policy.json check"
chmod 600 "$SANDBOX/ledger.jsonl"

echo
echo "── ⑤ ★ 真正该测的一格：agent 能到达二进制时，仍进不去 ────"
echo "   做法：把二进制与法律复制到 agent 可读可执行的运行盒（0755），"
echo "         账本目录由 root 拥有（0755）、账本 0600 —— 让 agent 跑到门禁跟前。"
cp "$CORE" "$RUNBOX/world-core"
mkdir -p "$RUNBOX/src/ontology_definition" "$RUNBOX/src/gate"
cp "$SRC/src/ontology_definition/ontology.json" "$RUNBOX/src/ontology_definition/ontology.json"
cp "$SRC/src/gate/policy.json" "$RUNBOX/src/gate/policy.json"
chmod 755 "$RUNBOX/world-core"; chmod 755 "$RUNBOX"
mkdir -p "$RUNBOX/lib" && chown root:root "$RUNBOX/lib" && chmod 755 "$RUNBOX/lib"
runuser -u agent -- "$RUNBOX/world-core" --ontology "$SANDBOX/src/ontology_definition/ontology.json" \
  --ledger "$SANDBOX/ledger.jsonl" --policy "$SANDBOX/src/gate/policy.json" check >/dev/null 2>&1
if [ $? -ne 0 ]; then ok "agent 能执行二进制，但打不开账本（静态墙生效，rc≠0）"; else bad "agent 竟成功打开了世界"; fi

# ⑤b：agent 在自己的目录里造一份**它自己的法律**（对它的 mode 检查是合法的），
#      然后拿它去开**我们的账本** —— 必须在真相的边界上被挡住。
#      ⚠️ v2.1 修正：v2 的初版把这条写成"任何非零 rc 即通过"，
#      结果 agent 只是因为**写不进运行盒**（那是 root 的 0755）而失败 ——
#      与"门禁拦住了它"是两件事。现在：给它自己的可写目录，并**断言拒绝原因**。
AGENTDIR=/tmp/con01-agent
rm -rf "$AGENTDIR"; mkdir -p "$AGENTDIR"; chown agent "$AGENTDIR"; chmod 700 "$AGENTDIR"
# 由 root 把法律副本放进 agent 的目录（agent 读不到 /root，见 ⑥ 的观察项），
# 再 chown 给它 —— 这模拟"被管者拿到了自己那份法律的副本"这一真实情形。
cp "$SRC/src/gate/policy.json" "$AGENTDIR/my-policy.json"; cp "$SRC/src/ontology_definition/ontology.json" "$AGENTDIR/"
chown agent "$AGENTDIR/my-policy.json" "$AGENTDIR/src/ontology_definition/ontology.json"
chmod 644 "$AGENTDIR/my-policy.json" "$AGENTDIR/src/ontology_definition/ontology.json"
if [ ! -f "$AGENTDIR/my-policy.json" ]; then bad "⑤b 前提不成立：agent 无法准备自己的策略副本"; else
  OUT=$(runuser -u agent -- "$RUNBOX/world-core" --ontology "$AGENTDIR/src/ontology_definition/ontology.json" \
        --ledger "$SANDBOX/ledger.jsonl" --policy "$AGENTDIR/my-policy.json" check 2>&1); RC=$?
  if [ $RC -eq 0 ]; then bad "agent 竟能用自备策略打开我们的账本"
  elif echo "$OUT" | grep -qE '账本|Ledger'; then ok "agent 用自备策略仍被挡在账本边界（rc=$RC；原因指向 Ledger 子系统：锁文件或账本本身）"
  else bad "被拒了但原因与账本/Ledger 无关（rc=$RC）：$(echo "$OUT" | head -1 | cut -c1-80)"; fi
fi

echo
echo "── ⑥ 观察项（**不计分**，非门禁属性）──────────────────────"
echo "   v1 曾把"二进制在 /root（0700）内"算作门禁的功劳 —— 那是路径权限的副作用。"
echo "   本版把它移出计分：agent 直接执行 /root 下的二进制结果如下（仅供参考）："
runuser -u agent -- "$CORE" --version >/dev/null 2>&1
echo "     rc=$?（预期非 0；原因与门禁无关）"

echo
echo "=============================================================="
echo " 通过 $PASS 项 / 失败 $FAIL 项（期望通过 $EXPECTED_PASS 项）"
echo "=============================================================="
if [ "$PASS" -ne "$EXPECTED_PASS" ]; then
  echo "❌ 通过数不等于期望值 $EXPECTED_PASS —— 断言数被改动过（v1 的漏洞 F2）"
  exit 1
fi
[ "$FAIL" -eq 0 ] || exit 1
echo "✅ 通过数与期望一致，且无失败"
