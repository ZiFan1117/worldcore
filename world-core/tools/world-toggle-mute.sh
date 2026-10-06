#!/bin/sh
# world-toggle-mute.sh —— 界面**唯一**的写路径：点一下 ⇒ 世界的**一条 `act`**。
#
# ## 壳与脑子分开（★ Omarchy 那套是"壳"，世界是"脑子"）
# - **壳**（状态栏那一格、图标、提示怎么摆）：`tools/omarchy/world-notice-cell.json`；
# - **脑子**（这次点击在世界里是什么）：本件。它**不列**"界面上有哪些可点项"——那是世界说的。
#
# ## 作者（"谁点的"）★ 第一条
# 身份由**口**给出。本件默认经 **界面自己的口** `/run/world-core/omarchy.sock`
# （该口在 `policy.json.listeners` 里绑 `world://presence/omarchy`）
# ⇒ 账本里这条 `act` 的作者**就是界面自己**，不再叫 `world://core`。
# ★ 不许经 `/run/world-core/world.sock`：那个口的作者是 `world://core`，"谁点的"从此查不出来。
# ★ 请求体里**不许自称** actor（`src/bus/mod.rs` 逐字"身份由内核给出，不由请求自称"）。
#
# ## 为什么发 `act`（不是 `change`）
# `change` 是另一条路：只走 `authorize_write`，**不过能力层与动作层、不产生 request/trace/回执**。
# 而"点一下"在世界里的正身是**请求**（规格逐字：人｜在界面上操作 → 翻译成 `act`）。
#
# ## 三件不许做的事
# 1. **不猜**"点了会发生什么"：动词与参数必须**显式给出**（`--verb`／`--params`）；
#    世界侧没有"能力 ⇒ 动词/参数"的声明面时**拒发**（界面替世界猜＝界面在裁决）。
# 2. **不自己列可点项**：发之前先问世界——`world-core describe` 里列不列这个能力；
#    不在册 ∩ 已授 ⇒ **拒发**（"有哪些可点项"来自世界，不来自外壳配置）。
# 3. **不碰文件**：不落盘、不缓存、不读账本字节；前值**从世界的投影现读**（`world-projection`）。
#
# ## 用法
#   world-toggle-mute.sh --verb <动词> [--params <JSON对象>]
# ## 环境
#   WORLD_SOCK（缺省 `/run/world-core/omarchy.sock`）
set -u

SOCK="${WORLD_SOCK:-/run/world-core/omarchy.sock}"
CONF=/etc/world-core
CLI=/usr/bin/world-core
SUB=/usr/local/lib/world-ui/wc_submit.py
READ=/usr/local/bin/world-projection

say() { printf '%s\n' "$*"; }

VERB=""
PARAMS="{}"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --verb)   VERB="${2:-}";   shift 2 ;;
        --params) PARAMS="${2:-}"; shift 2 ;;
        *) say "用法: $0 --verb <动词> [--params <JSON对象>]"; exit 2 ;;
    esac
done

# ① 前值**从世界现读**（不缓存、不记位点：位点在投影首行）
cur=$("$READ")
case "$cur" in
    *"muted=true"*)  CAP="notice.unmute" ;;
    *"muted=false"*) CAP="notice.mute"   ;;
    *) say "世界不可用（界面当前显示：${cur}）——拒绝发事件（手没有法不许动）"; exit 3 ;;
esac

# ② "有哪些可点项"**问世界**：这个能力在不在册 ∩ 已授
desc=$("$CLI" --ontology "$CONF/src/ontology_definition/ontology.json" --ledger /var/lib/world-core/ledger.jsonl \
        --policy "$CONF/src/gate/policy.json" describe 2>/dev/null) || {
    say "读不到世界的 describe —— 拒绝发事件（问不到世界，就不动）"; exit 3; }
case "$desc" in
    *"$CAP"*) : ;;
    *) say "世界没把 \`$CAP\` 列在册 ∩ 已授里（describe）——拒绝发事件"; exit 4 ;;
esac

# ③ 动词/参数不许界面编：世界没声明 ⇒ 拒发（等世界侧那条声明面落地）
if [ -z "$VERB" ]; then
    say "不发送：世界没有声明 \`$CAP\` 该发什么动词（本体 \`_actions\` 只有 capability/reversible）"
    say "  界面不许替世界猜『点了会发生什么』。要给就显式给：--verb <动词> [--params <JSON对象>]"
    exit 2
fi

RID="omarchy-$(date +%s)-$$"
REQ=$(printf '{"kind":"act","body":{"capability":"%s","verb":"%s","request_id":"%s","params":%s}}' \
      "$CAP" "$VERB" "$RID" "$PARAMS")

# ④ 经界面层**唯一写入口**交给世界，把世界的应答原样打出来
reply=$(python3 "$SUB" "$SOCK" "$REQ" 2>&1) || { say "提交失败：$reply"; exit 3; }
say "请求：$REQ"
say "应答：$reply"
case "$reply" in
    *'"ok":true'*) exit 0 ;;
    *) say "世界拒绝了这条 act（未改任何东西）"; exit 5 ;;
esac
