#!/bin/sh
# 世界核心 · 部署件安装脚本
#
# 它干什么：建身份与目录 → 装四份单元 → 让载体系上套接字 → 逐条核对装完的样子。
# 它不干什么：不写法律（ontology/policy/channel 由部署方提供）；不替世界做任何裁决。
#
# 用法：
#   ./install.sh --check        只核对现状，不改任何东西（安全的默认先跑这个）
#   sudo ./install.sh           安装/更新（幂等：重复跑不炸）
#   sudo ./install.sh --uninstall  停服务并移除单元（**不动账本与法律**）
#
# 判据（装完自己会跑）：见文末 verify() —— 任何一条不成立就以非零退出。

set -eu

SRC_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
UNIT_DIR=/etc/systemd/system
CONF_DIR=/etc/world-core
STATE_DIR=/var/lib/world-core
RUN_DIR=/run/world-core
ACTD_STATE=/var/lib/world-actd
ACTD_RUN=/run/world-actd

CORE_USER=world-core
# ★ 2026-10-06：原先这里还有 `PROJ_USER=world-projectd` —— **已删**。它只服务于已退役的
#   投影单元 `world-core-projectd.service`（见下面 `UNITS` 上方那段定案）；设计要求（独立 uid、
#   零写权限）仍在 `WC-ARCH-001`／`系统全景图`／`deploy/README.md` §四，属"设计已定·未落地"，
#   **不替它在这台机器上建一个用不上的用户**。
ACTD_USER=agent
# ★ 界面（Omarchy）自己的系统身份：它连的是自己的口 `/run/world-core/omarchy.sock`，
#   而那个口在法律里映射到 `world://presence/omarchy` ⇒ **口给出身份**，不靠请求体自称。
OMARCHY_USER=omarchy
# ★ DSH 自己的系统身份（与上一条**同形**）：它连的是自己的口 `/run/world-core/dsh.sock`，
#   而那个口在法律里映射到 `world://agent/dsh`（见 `policy.json.listeners`）⇒ 同上，**口给出身份**。
DSH_USER=dsh

# 装哪些单元（**这份清单是权威**：装了哪几个口＝这条机器上世界对外开了哪几个口）
#
# ★★ 2026-10-06：`world-core-projectd.service` **已退役**（工作树移除）⇒ `deploy/` 现在**正好**＝本清单 5 件。
#   三条定案（都是现取，非推定）：
#     ① 它的 `ExecStart=… project serve` 是**死子命令**（`cmd_project` 只认
#        `language`／`visual`／`surface`／`check`）＋ `Restart=on-failure`／`RestartSec=2s`
#        ⇒ 装上去每 2 秒抖一次；
#     ② 它与设计要求**直接矛盾**：设计要"独立 uid `world-projectd`、零写权限"，
#        而单元件 2026-10-05 被改成 `User=world-core`／`Group=world-core`（一个事实两个说法）；
#     ③ 当初"**不许删**"的唯一理由——它是**未跟踪件、没有解析根**——**已消失**：
#        2026-10-06 的收口提交把它带进了版本控制（`git ls-files` 可核）⇒ 退场合规。
#   **解析根**：`git show deafbae:world-core/deploy/world-core-projectd.service`。
#   设计要求仍在 `WC-ARCH-001`／`系统全景图`／`deploy/README.md` §四 —— 那三处**不改口径**，
#   "实现未落地"按既有先例（`grant_path_guard.py` 的 G-02 那一族）**登记**。
#   ⇒ 现状：**在目录里、不在清单里＝未启用**；要启用它，先把 `project serve` 落实现。
UNITS="world-core.socket world-core.service world-core-actd.service world-core-omarchy.socket world-core-dsh.socket"

MODE=install
for a in "$@"; do
  case "$a" in
    --check) MODE=check ;;
    --uninstall) MODE=uninstall ;;
    *) echo "未知参数：$a" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    say "需要 root：请用 sudo 跑（或用 --check 只核对）"; exit 1
  fi
}

have_user() { id -u "$1" >/dev/null 2>&1; }

ensure_user() {
  u=$1
  if have_user "$u"; then
    say "  身份已存在：$u"
  else
    # 系统身份、无家目录、不可登录：它只用来"当进程的身份"，不是给人登的
    useradd --system --no-create-home --shell /usr/sbin/nologin "$u"
    say "  已建身份：$u"
  fi
}

ensure_dir() {
  d=$1; mode=$2; owner=$3
  if [ ! -d "$d" ]; then mkdir -p "$d"; say "  已建目录：$d"; fi
  chmod "$mode" "$d"
  chown "$owner" "$d"
}

install_units() {
  for f in $UNITS; do
    if [ ! -f "$SRC_DIR/$f" ]; then say "缺单元文件：$SRC_DIR/$f" >&2; exit 1; fi
    install -m 0644 "$SRC_DIR/$f" "$UNIT_DIR/$f"
    say "  已装单元：$f"
  done
}

seed_config() {
  # 法律与本体必须由部署方提供；这里只把仓内的样例放过去（**不覆盖已有**）
  for f in src/ontology_definition/ontology.json src/gate/policy.json; do
    # ★ 装到配置目录时**摊平**（只取文件名）：服务单元的 `ExecStart` 读的是
    #   `/etc/world-core/ontology.json` 与 `/etc/world-core/policy.json`，
    #   仓内那份在 `src/` 下是**源码布局**，不是装机布局（2026-10-07 结构迁移后订正）。
    for_base="$(basename "$f")"
    if [ -f "$SRC_DIR/../$f" ] && [ ! -f "$CONF_DIR/$for_base" ]; then
      install -m 0644 "$SRC_DIR/../$f" "$CONF_DIR/$for_base"
      # ★ 法律属主：A-05（`src/gate/guard.rs::assert_owned_by`）在服务路径上判的就是这两份
      #   （调用点实参＝本体／门禁策略／账本三件；`channel.json` 与 `cap.d/` **不在其中**，故不 chown）。
      #   目录维持 root（有意为之）：目录归 root ⇒ 核心用户不能"替换"法律；
      #   文件归核心 uid ⇒ 只能改内容，而改动会过门禁、会落账。
      chown "$CORE_USER:$CORE_USER" "$CONF_DIR/$f"
      say "  已放初始 $f（部署方须复核）"
    fi
  done
  # ── 身份映射的**渲染链**（"法律 → 渲染物"这一跳的主人）──
  #
  # 为什么必须有这一步：受理路径**只读渲染物** `channel.json`（`serve` 从继承来的 fd 取路径
  # → `ChannelConfig::load` → `listener_for`），而法律那份 `listeners` 在运行路径上零读者。
  # 这两个件之间以前**没有生成器、没有门禁、不在版本控制**里 ⇒ 渲染物事实上是**第二在册**。
  # 现在链路是：法律（policy.json.listeners）＋ 部署面 uid 映射 ⇒ 渲染物，两个工具都是仓内件：
  #   ① tools/gen_owner_uid.py   读 listeners[].owner ＋ 本机用户库 ⇒ /etc/world-core/owner_uid.json
  #   ② tools/render_channel.py  读法律 ＋ 那份映射 ⇒ /etc/world-core/channel.json
  #
  # ★ 为什么映射**住在 `/etc`、不住在仓里**（Lead 2026-10-05 钉死）：★**它含本机事实**
  #   （`uid` 每台机不同）⇒ ★**含本机事实的产物，不入版本控制，也不住在仓内路径。**
  #   （对照：`openspec/BRIDGE.md` 是**文档派生量、不含本机事实** ⇒ 它入仓。）
  UIDS="$CONF_DIR/owner_uid.json"
  GEN="$SRC_DIR/../tools/gen_owner_uid.py"
  RENDER="$SRC_DIR/../tools/render_channel.py"
  if [ -f "$GEN" ]; then
    if python3 "$GEN" --policy "$SRC_DIR/../src/gate/policy.json" --out "$UIDS" >/dev/null 2>&1; then
      say "  已生成 uid 映射：$UIDS（由 tools/gen_owner_uid.py 读本机用户库）"
    else
      say "  ⚠ tools/gen_owner_uid.py 跑不动（看它的用法：--policy/--out）——"
      say "    uid 映射必须先有，渲染物才渲得出来"
    fi
  else
    say "  ⚠ 缺 $GEN（uid 映射的生产者）——渲染链缺一环"
  fi
  if [ -f "$RENDER" ] && [ -f "$UIDS" ]; then
    if python3 "$RENDER" --policy "$SRC_DIR/../src/gate/policy.json" --uids "$UIDS" \
         --out "$CONF_DIR/channel.json" >/dev/null 2>&1; then
      chmod 0644 "$CONF_DIR/channel.json"
      say "  已渲染身份映射：$CONF_DIR/channel.json（$RENDER 从法律生成，勿手改）"
    else
      say "  ⚠ 渲染失败：$RENDER --policy … --uids … --out …（手工跑一次看它点名哪一条）"
    fi
  elif [ ! -f "$CONF_DIR/channel.json" ]; then
    say "  ⚠ 缺 $CONF_DIR/channel.json（身份映射）——内核单元会引用它，缺了它服务起不来；"
    say "    渲染链：$CONF_DIR/owner_uid.json ＋ tools/render_channel.py（本脚本不伪造）"
  fi
}

enable_units() {
  systemctl daemon-reload
  # ★ **只 enable 清单里的**（单一来源＝`$UNITS`）。★旧写法在这里挂了**第二份硬编码清单**，
  #   里面还留着 `world-core-projectd.service` ⇒ ★**"从清单摘掉"会被这一步当场推翻**
  #   （那个单元的 `project serve` 不存在 ＋ `RestartSec=2s` ⇒ 装上每 2 秒抖一次）。
  #   ⇒ socket 类用 `--now`（口要立刻建起来）；服务类只 `enable`（由 socket 激活，不主动起）。
  for f in $UNITS; do
    case "$f" in
      *.socket) systemctl enable --now "$f"; say "  已启用：$f（套接字归载体持有）" ;;
      *)        systemctl enable "$f";      say "  已 enable：$f" ;;
    esac
  done
}

verify() {
  rc=0
  installed=0
  say ""
  say "== 装完核对（任一条不成立即非零退出） =="

  for f in $UNITS; do
    if [ -f "$UNIT_DIR/$f" ]; then say "  [ok] 单元在：$f"; else say "  [FAIL] 单元缺：$f"; rc=1; fi
  done
  # ★ 一条纪律：**"文件不在"不得被读成"合规"**。
  #   下面几条判据都靠 grep 单元内容；若单元根本没装，grep 必然失败——
  #   若不加这道门，缺文件会被静默算成"没有违规项"（假绿）。实测踩过。
  if [ -f "$UNIT_DIR/world-core.service" ] && [ -f "$UNIT_DIR/world-core.socket" ]; then
    installed=1
  fi

  if [ -S "$RUN_DIR/world.sock" ]; then
    say "  [ok] 套接字在：$RUN_DIR/world.sock"
    say "       实际权限：$(stat -c '%a %U %G' "$RUN_DIR/world.sock" 2>/dev/null || echo '取不到')"
  else
    say "  [--] 套接字尚未出现（socket 单元未启动，或载体系不在此机）"
  fi

  if [ "$installed" -eq 0 ]; then
    say "  [--] 单元未装 ⇒ 内容类判据**不判**（避免把'文件不在'读成'合规'）"
    return 1
  fi

  # ★ 法律属主：A-05 在**服务路径**上判的就是这两份（`src/gate/guard.rs::assert_owned_by`，
  #   调用点实参＝本体／门禁策略／账本）。属主不对 ⇒ **服务一上服务路径就起不来**。
  #   ⚠️ `channel.json` 与 `cap.d/` **不在 A-05 的判定范围内** ⇒ 本判据**不判**它们。
  core_uid="$(id -u "$CORE_USER" 2>/dev/null || echo '')"
  for f in src/ontology_definition/ontology.json src/gate/policy.json; do
    if [ -f "$CONF_DIR/$f" ]; then
      got="$(stat -c '%u' "$CONF_DIR/$f" 2>/dev/null || echo '取不到')"
      if [ "$got" = "$core_uid" ]; then
        say "  [ok] 法律属主正确：$CONF_DIR/$f（uid=$got）"
      else
        say "  [FAIL] 法律属主不符：$CONF_DIR/$f 实得 uid=$got，期望 uid=$core_uid（$CORE_USER）"; rc=1
      fi
    fi
  done

  # 唯一写者：只有内核单元的 ReadWritePaths 允许写状态目录
  if grep -q "ReadWritePaths=.*$STATE_DIR" "$UNIT_DIR/world-core.service" 2>/dev/null; then
    say "  [ok] 内核进程可写状态目录"
  else
    say "  [FAIL] 内核单元的 ReadWritePaths 未含 $STATE_DIR"; rc=1
  fi
    # ★ "文件不在"不得读成"合规"（本脚本开头就立过这条纪律）：投影单元**已退役**（2026-10-06，
    #   见 `UNITS` 上方定案）⇒ **本项无对象**，故**不判**：既不打 `[ok]`、也不打"未校验"
    #   （它不在清单里、也不该在），只留这一句说明。设计要求仍在架构件里（"实现未落地"）。
  if grep -q "ReadWritePaths=.*$STATE_DIR" "$UNIT_DIR/world-core-actd.service" 2>/dev/null; then
    say "  [FAIL] 载体执行器竟然可写状态目录"; rc=1
  else
    say "  [ok] 载体执行器对真相零写权限"
  fi

  # 默认拒绝：载体执行器不带 --confirm（只看指令行，注释里出现不算）
  if grep -E '^[[:space:]]*ExecStart=.*--confirm' "$UNIT_DIR/world-core-actd.service" >/dev/null 2>&1; then
    say "  [FAIL] 载体执行器的 ExecStart 带了 --confirm（高危动作会被自动放行）"; rc=1
  else
    say "  [ok] 载体执行器默认拒绝高危动作"
  fi

  # ★ 套接字权限：**三处口径统一为 0600**（单元／`src/bus/mod.rs::bind()`／盘上）。
  #   为什么判：生产走 socket activation ⇒ 单元给的就是盘上那个值，而它此前是 0660 而
  #   代码文档写 0600 ⇒ 同一个事实两个取值、都不红。这里只看**指令行**（注释里出现不算）。
  for u in world-core.socket world-core-omarchy.socket world-core-dsh.socket; do
    if [ -f "$UNIT_DIR/$u" ]; then
      if grep -qE '^[[:space:]]*SocketMode=0600' "$UNIT_DIR/$u"; then
        say "  [ok] $u 的 SocketMode=0600（一个口一个身份，不靠属组）"
      else
        say "  [FAIL] $u 的 SocketMode 不是 0600（实得：$(grep -E '^[[:space:]]*SocketMode=' "$UNIT_DIR/$u" || echo 无)）"; rc=1
      fi
    fi
  done

  # ★ 渲染链：**渲染物必须逐条解析到法律**（权威落点＝tools/render_channel.py --check）。
  #   机器契约：STATUS=PASS 记绿／FAIL 记红／**SKIP 记"未校验"，不许记绿**（文件不在≠合规）。
  RENDER="$SRC_DIR/../tools/render_channel.py"
  if [ -f "$RENDER" ] && [ -f "$CONF_DIR/policy.json" ]; then
    st="$(python3 "$RENDER" --check "$CONF_DIR/channel.json" --policy "$CONF_DIR/policy.json" 2>&1 \
          | sed -n 's/^STATUS=//p' | tail -n 1)"
    case "${st:-}" in
      PASS) say "  [ok] 渲染物 ⊆ 法律（$CONF_DIR/channel.json 每一条都在册）" ;;
      SKIP) say "  [⏭] 渲染物未校验：$CONF_DIR/channel.json 不存在——**未校验不是通过**" ;;
      FAIL) say "  [FAIL] 渲染物里有账外口（法律里解析不到）——见 $RENDER --check 的点名"; rc=1 ;;
      *)    say "  [FAIL] 渲染链跑不出结论（该工具没印 STATUS=；不许当成通过）"; rc=1 ;;
    esac
  elif [ -f "$RENDER" ]; then
    say "  [⏭] 渲染物未校验：缺 $CONF_DIR/policy.json"
  else
    say "  [⏭] 渲染物未校验：缺 $RENDER"
  fi

  return $rc
}

case "$MODE" in
  check)
    say "== 只核对（不改动） =="
    verify || true
    say ""
    say "（--check 不因缺失而失败；要当门禁用，请跑 tools/carrier_contract.py）"
    ;;
  uninstall)
    need_root
    systemctl disable --now world-core.socket world-core-omarchy.socket world-core-dsh.socket world-core.service world-core-actd.service 2>/dev/null || true
    rm -f "$UNIT_DIR"/world-core*.service "$UNIT_DIR"/world-core*.socket
    systemctl daemon-reload
    say "已移除单元；账本（$STATE_DIR）与法律（$CONF_DIR）**未动**"
    ;;
  install)
    need_root
    say "== 1/5 身份 =="
    # ★ 界面自己的系统身份：它的口 SocketUser=omarchy ⇒ 没有这个用户，那个 socket 单元起不来。
    #   「一个口一个身份」要落到系统上，就得**一个口一个系统用户**。
    ensure_user "$CORE_USER"; ensure_user "$ACTD_USER"; ensure_user "$OMARCHY_USER"
    # ★ DSH 同形：没有 `dsh` 这个用户 ⇒ `/etc/world-core/owner_uid.json` 里那条只能是 `null`
    #   （`tools/gen_owner_uid.py` 的口径③：查不到 ⇒ `null`，**绝不写 0**），渲染物里就没有它的口。
    ensure_user "$DSH_USER"
    say "== 2/5 目录 =="
    ensure_dir "$CONF_DIR" 0755 root:root
    ensure_dir "$STATE_DIR" 0700 "$CORE_USER:$CORE_USER"
    ensure_dir "$RUN_DIR" 0755 "$CORE_USER:$CORE_USER"
    ensure_dir "$CONF_DIR/cap.d" 0755 root:root
    ensure_dir "$ACTD_STATE" 0700 "$ACTD_USER:$ACTD_USER"
    ensure_dir "$ACTD_RUN" 0755 "$ACTD_USER:$ACTD_USER"
    say "== 3/5 单元 =="
    install_units
    say "== 4/5 法律与本体 =="
    seed_config
    say "== 5/5 启用 =="
    enable_units
    verify
    say ""
    say "下一步（由部署方做）："
    say "  1) 复核 $CONF_DIR/ontology.json 与 policy.json"
    say "  2) 身份映射已由 render_channel.py 渲染到 $CONF_DIR/channel.json（缺则先跑 seed_config 那两个工具）"
    say "  3) systemctl start world-core.service，再跑 tools/carrier_contract.py 复核单元与法律"
    say "  4) ★ 让界面真的能以它自己的身份说话，还差【申报】这一步——"
    say "     新身份走的是两级：①**申报**（账本里它名下要有格）②**授权**（本体 _permissions.grants 的 scope 命中它）。"
    say "     grants 一步已在法律里（ontology.json），申报是**账本事实**，要落五条 change（presence 的五格）："
    say "       name / category / state / did / last_seen，subject=world://presence/omarchy，"
    say "       作者用 world://core（经 world.sock 这条唯一写入口投递，**不许直接改账本文件**）。"
    say "     ★ 缺这一步的症状是**一次明确的拒**（ext.world.World.PresenceNotDeclared），不是静默失效；"
    say "       报得再全也不自动拿到任何能力——开放只由许可决定。"
    ;;
esac
