# -*- coding: utf-8 -*-
"""载体契约门禁：把「生成关系」做成会红的判据。

判的是：`deploy/` 里的四份单元 **是不是**从设计（`deploy/README.md` 的声明 + `policy.json` 的法律）生成出来的，
以及"唯一写者 / 默认拒绝 / 单一身份"这三条不可让的约束有没有被单元文件违背。

判据（每条都配反例，见 --self-test）：
  ① 四份单元存在且非空；README 声明的套接字路径与 socket 单元里的 `ListenStream=` 一致
  ② socket 的 `SocketUser=`/`SocketGroup=` 与内核单元的 `User=`/`Group=` 是同一个身份
  ③ `ListenStream=` 与内核单元的 `RuntimeDirectory=` 同址（`/run/<名字>/…`）
  ④ **唯一写者**：只有内核单元的 `ReadWritePaths` 含状态目录；投影与载体执行器**都不得**含
  ⑤ **默认拒绝**：载体执行器单元不得出现 `--confirm`
  ⑥ **单一身份**：内核单元不得 `User=root`；socket 单元不得 `SocketMode=0666`
  ⑦ **身份映射入法（A2）**：`policy.json` 里必须有 `listeners`，且单元声明的套接字是它的一条
     ★**订正（2026-10-05）**：本条原先写着"**今天这条必红**（法律里没有它）"——那是**写下时**的实况；
     法律里**现在有** `listeners` 了，那句旧结论**已过期**。按 G9 形态 C（"当时真、现在假"）**改掉，不留假话**；
     红绿一律以**当场的原始输出**为准。
  ⑧ **渲染物 ⊆ 法律**（★2026-10-05 新增）：`--channel` 指向的渲染件里**每一条** `listeners[].socket`
     都必须能在 `policy.json` 的 `listeners` 里解析到；**多出来的口（账外口）⇒ 红**。
     ★**未给渲染物（或它不存在）⇒ 未校验，打 `STATUS=SKIP`，不是绿**——"没有输入"不等于"没有问题"。
  ⑨ **在册而渲染物里没有**（★同上新增）：**报告行，不判红**——"在册未上线"是运行态，
     法律在册**不等于**世界会受理；这一行专治"把在册读成已上线"。缺渲染物时与 ⑧ 一起未校验。

★**射程（如实声明，不假装更宽）**：
  - 本工具判的是**纸面之间**的一致性（`deploy/` 单元 ↔ `policy.json` ↔ 渲染物）；
  - **它不判运行时**：**"实际监听 ⊆ 在册"那一段的执行体在 `world-core` 二进制里**，今天
    **尚未实现**（`policy.json` 的 `_listeners_note` 自述）。⇒ 本工具绿，**不等于**"实际监听 ⊆ 在册"成立。
  - **覆盖哪几件，以 `install.sh` 的 `UNITS=` 为准**（`grep -n '^UNITS=' deploy/install.sh`）——
    ★**本行不写件数、也不写"覆盖了哪几件"**。
    （★2026-10-05 订正：原写"今天**未覆盖 `world-core-dsh.socket`**"——★那是**一句会变的事实被写进件**：
      当天 `UNITS=` 就把它加进去了 ⇒ **原句过期**。★与 `NOT_INSTALLED` 那处同一个病：
      **件里只许放【当前值 ＋ 取数命令 ＋ 时点】，不许放快照。**）

读数四要素：时点 / 命令 / 原始输出 / 结论。
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

try:                     # ★ 名字 → uid 是 **POSIX 专有**（Windows 无 `pwd`）
    import pwd
except ImportError:      # pragma: no cover —— 非 POSIX 主机
    pwd = None

HAS_PWD = pwd is not None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # world-core/
DEPLOY = os.path.join(ROOT, 'deploy')
POLICY = os.path.join(ROOT, 'src', 'gate', 'policy.json')
README = os.path.join(DEPLOY, 'README.md')
CHANNEL = '/etc/world-core/channel.json'          # 现役载体上的渲染物（可用 --channel 覆盖）
STATE_DIR = '/var/lib/world-core'

# ★ **本件不再自带一份单元清单**：自带一份 ⇒ "三处清单"（`deploy/` 目录／`install.sh`／本件）
#   永远对不齐，而且**没有任何东西会红**（实测：本件原来那份是 4 件、**不含** `world-core-dsh.socket`
#   与 `world-core-omarchy.socket`，而目录里有 6 件）。
#   ⇒ **唯一来源＝`install.sh` 的 `UNITS=`**（见 `unit_list`）。`UNITS_FALLBACK` 只在**读不到 install.sh**
#     时用一个"最保守的四件"占位，**且它一被用到 ⇒ ①a／⑪ 判红**（不是静默降级）。
UNITS_FALLBACK = ['world-core.socket', 'world-core.service', 'world-core-actd.service']

# ★ **已登记"未启用"**（在目录里、**不在清单里**）——★**每一件都必须写出原因**；★它不是"免检名单"：
#   `⑪b` 仍然对**任何未登记的**多出来的单元件判红，`⑪c` 把这几件**连原因一起报出来**（不许藏着）。
# ★★ **教训（2026-10-05，本条自己栽的）**：这里原本还登记着 `world-core-dsh.socket`，理由写的是
#   ★"**机器上没有 `dsh` 用户**（`owner` 解析为 `null`）" —— ★**那是一句【会变的机器事实】，被写进了判据**；
#   ★★ 16:08 别人把 `dsh` 用户建起来之后，**那四个短句全成了假话**，而本件**照样在打印它**
#   （更糟：`dsh.socket` 同时进了 `install.sh` 的 `UNITS=` ⇒ 出现"清单里也有它、未启用里也有它"的自相矛盾态）。
#   ⇒ ★**本条口径**：★`NOT_INSTALLED` **只登记"未启用"这个事实 ＋ 原因指针**；
#     ★★ **不许把"当前机器状态"（有没有某个用户／某个口在不在听）写死在这里** ——
#     ★那类事实**归它自己的判据（⑨／⑫ 那条「盘上属主 ≡ 映射 uid」）现取**，★不在这里复述。
#
# ★★ **2026-10-06：本表清空** —— 唯一那一件（`world-core-projectd.service`）**已退役**（工作树移除，git 历史留）。
#   退场前定案的三条（都是现取的，不是推定）：
#     ① **它的 `ExecStart` 是死子命令**：`cmd_project`（`src/main.rs:1068`）只认
#        `language`／`visual`／`surface`／`check` —— **没有 `serve`**；配上 `Restart=on-failure`＋`RestartSec=2s`
#        ⇒ 装上去就是每 2 秒抖一次（`install.sh` 原本就是这么写的，2026-10-06 复核**成立**）。
#        （★ 先前那条"待重核"到此闭合：当时看到的 `"accept" | "serve"` 属于 **`cmd_channel`**，不是 `cmd_project`。）
#     ② **它与设计要求直接矛盾**：`deploy/README.md` §四／`WC-ARCH-001`／`系统全景图` 三处都写
#        "投影服务＝**独立 uid `world-projectd`**、**零写权限**"，而单元件在 2026-10-05 被改成
#        `User=world-core`／`Group=world-core` ⇒ **一个事实两个说法**。
#     ③ **当初"不许删"的理由已消失**：它原先是**未跟踪件**（无解析根），而 2026-10-06 的收口提交
#        把它带进了版本控制（`git ls-files` 可核）⇒ 按本仓"退场件要给解析根"的口径，**现在退场合规**。
#   **解析根**：`git show deafbae:world-core/deploy/world-core-projectd.service`（退场前提交）。
#   **设计要求仍在**（未落地）：`WC-ARCH-001`／`系统全景图`／`deploy/README.md` §四 —— 本件**不替它们改口径**；
#   "设计已定·未落地"这一档按既有先例（`grant_path_guard.py` 的 G-02 那一族）**登记**。
NOT_INSTALLED = {}


def read(p):
    with io.open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def unit_list(deploy_dir):
    """单元清单 —— **唯一来源＝`install.sh` 的 `UNITS=` 那一行**。

    ★ 读不出来 ⇒ 返 `None`（＝**不可判定**）：**不是"没有单元"**。
      这两者在判据上是两个结论（G1：空集与不可判读都不许判绿）。
    """
    p = os.path.join(deploy_dir, 'install.sh')
    if not os.path.isfile(p):
        return None
    m = re.search(r'^[ \t]*UNITS="([^"]*)"', read(p), flags=re.M)
    if not m:
        return None
    return m.group(1).split()


def uids_path(deploy_dir):
    """部署面 uid 映射件 —— **路径也从 `install.sh` 取**（`UIDS=`），免得本件再造第二处说法。

    ★ 载体本身今天**未定**（`/etc/world-core/owner_uid.json` 与 `deploy/listener_uids.json` 两个候选
      同时活着，资源席已转 Lead 钉死）⇒ 本件**不写死**路径，**跟着 `install.sh` 走**。
    ★ 拿不到 ⇒ 用 `install.sh` 当前那个值，并在判据里**报出用的是哪条路径**。
    """
    p = os.path.join(deploy_dir, 'install.sh')
    default = os.path.join(deploy_dir, 'listener_uids.json')
    if not os.path.isfile(p):
        return default
    m = re.search(r'^[ \t]*UIDS="([^"]*)"', read(p), flags=re.M)
    if not m:
        return default
    v = m.group(1)
    v = v.replace('$SRC_DIR', deploy_dir)
    v = v.replace('$CONF_DIR', '/etc/world-core')
    return v


def directives(text):
    """只保留**非注释行**（单元里的 `#` 说明行不算指令）。

    ★ 血泪：判据不许"取文件里第一处字样"——注释里也会出现 `--confirm`／`ReadWritePaths`
    这样的字样；按字样搜会把说明文字当成配置，产出**假红**。
    """
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#') or s.startswith(';'):
            continue
        out.append(line)
    return '\n'.join(out)


def find_all(text, key):
    return re.findall(r'^%s=(.*)$' % re.escape(key), directives(text), flags=re.M)


def find_one(text, key):
    v = find_all(text, key)
    return v[0].strip() if v else None


def exec_lines(text):
    return [l.strip() for l in directives(text).splitlines() if l.strip().startswith('ExecStart=')]


def sockets_of(obj):
    """从一份 JSON **对象**里取 `listeners[].socket` 清单。

    ★ 认**结构**不认字样：只收 `listeners` 是数组、且每一项是对象、且 `socket` 是字符串的。
    ★ 取不到 ⇒ 返 `None`（＝**不可判读**）；**不是**空清单——"读不出来"与"一条都没有"
      是两个结论，混了就会出假绿（G1 的第二形态）。
      空数组返 `[]`（＝法律／渲染物**明说**自己没有口）。
    """
    if not isinstance(obj, dict):
        return None
    ls = obj.get('listeners')
    if not isinstance(ls, list):
        return None
    out = []
    for x in ls:
        if not isinstance(x, dict):
            return None
        s = x.get('socket')
        if not isinstance(s, str):
            return None
        out.append(s)
    return out


def load_sockets(path):
    """读一份 JSON 文件的 `listeners[].socket`；读不到／解析不了 ⇒ `None`（不可判读）。"""
    try:
        return sockets_of(json.loads(read(path)))
    except Exception:
        return None


def judge(deploy_dir, policy_path, readme_path, channel_path=None):
    """返回 (rows, reds)；rows＝每条判据的读数，reds＝红的条号。"""
    rows, reds = [], []

    def add(no, name, ok, detail):
        rows.append((no, name, 'ok' if ok else 'FAIL', detail))
        if not ok:
            reds.append(no)

    def report(no, name, verdict, detail):
        rows.append((no, name, verdict, detail))

    # ① 单元存在且非空；README 声明与 socket 单元一致
    # ★ 清单的**唯一来源**＝`install.sh` 的 `UNITS=`（见 `unit_list`）；本件不再自带一份。
    units = unit_list(deploy_dir)
    if units is None:
        add('①a', '清单里的单元存在且非空', False,
            '读不出 `deploy/install.sh` 的 `UNITS=` ⇒ **无法对账**（不是"没有单元"）')
        units = []
    else:
        missing = [u for u in units
                   if not os.path.isfile(os.path.join(deploy_dir, u))
                   or os.path.getsize(os.path.join(deploy_dir, u)) == 0]
        add('①a', '清单里的单元存在且非空', not missing,
            '清单 %d 件；缺/空：%s' % (len(units), ','.join(missing) if missing else '无'))

    sock = os.path.join(deploy_dir, 'world-core.socket')
    core = os.path.join(deploy_dir, 'world-core.service')
    # ★ 投影单元**只在清单里有它时**才当主体（今天已摘除 ⇒ ④b 记"未校验"，见下）
    proj_name = next((u for u in units if 'projectd' in u), None)
    proj = os.path.join(deploy_dir, proj_name) if proj_name else ''
    actd = os.path.join(deploy_dir, 'world-core-actd.service')
    sock_txt = read(sock) if os.path.isfile(sock) else ''
    core_txt = read(core) if os.path.isfile(core) else ''
    proj_txt = read(proj) if proj and os.path.isfile(proj) else ''
    actd_txt = read(actd) if os.path.isfile(actd) else ''

    listen = find_one(sock_txt, 'ListenStream')
    readme_txt = read(readme_path) if os.path.isfile(readme_path) else ''
    declared = re.findall(r'^ListenStream=(.*)$', readme_txt, flags=re.M)
    declared = [d.strip() for d in declared]
    consistent = bool(listen) and (not declared or listen in declared)
    add('①b', 'README 声明与 socket 单元一致', consistent,
        'unit=%r readme=%r' % (listen, declared))

    # ② 同一个身份
    su, sg = find_one(sock_txt, 'SocketUser'), find_one(sock_txt, 'SocketGroup')
    cu, cg = find_one(core_txt, 'User'), find_one(core_txt, 'Group')
    add('②', 'socket 与内核单元同一身份',
        bool(su) and su == cu and bool(sg) and sg == cg,
        'socket=%s:%s core=%s:%s' % (su, sg, cu, cg))

    # ③ 套接字路径与 RuntimeDirectory 同址
    rt = find_one(core_txt, 'RuntimeDirectory')
    same_dir = bool(listen) and bool(rt) and listen.startswith('/run/%s/' % rt)
    add('③', 'ListenStream 与 RuntimeDirectory 同址', same_dir,
        'listen=%r RuntimeDirectory=%r' % (listen, rt))

    # ④ 唯一写者
    core_w = any(STATE_DIR in p for p in find_all(core_txt, 'ReadWritePaths'))
    proj_w = any(STATE_DIR in p for p in find_all(proj_txt, 'ReadWritePaths'))
    actd_w = any(STATE_DIR in p for p in find_all(actd_txt, 'ReadWritePaths'))
    add('④a', '内核可写状态目录', core_w, 'ReadWritePaths 命中=%s' % core_w)
    if proj_name is None:
        # ★ G1：**数据面空了，不许判绿**（主体不存在 ⇒ 这条判据**未校验**，不是"通过"）
        report('④b', '投影不可写状态目录', 'SKIP',
               '清单里没有投影单元（★已从 `install.sh` 的 `UNITS=` 摘除）⇒ **未校验**，不是通过')
    else:
        add('④b', '投影不可写状态目录', not proj_w, 'ReadWritePaths 命中=%s' % proj_w)
    add('④c', '载体执行器不可写状态目录', not actd_w, 'ReadWritePaths 命中=%s' % actd_w)

    # ⑤ 默认拒绝：只看 **ExecStart 指令行**（注释里出现 `--confirm` 不算）
    confirm = any('--confirm' in l for l in exec_lines(actd_txt))
    add('⑤', '载体执行器不含 --confirm（默认拒绝）', not confirm,
        'ExecStart 行=%s' % (exec_lines(actd_txt) or '无'))

    # ⑥ 单一身份 / 明确的坏模式
    root_user = find_one(core_txt, 'User') == 'root'
    mode666 = find_one(sock_txt, 'SocketMode') == '0666'
    add('⑥a', '内核单元不用 root', not root_user, 'User=%r' % find_one(core_txt, 'User'))
    add('⑥b', 'socket 不用 0666', not mode666, 'SocketMode=%r' % find_one(sock_txt, 'SocketMode'))

    # ⑦ 身份映射入法（A2）——只判"本单元声明的那个口在不在法律里"
    if not os.path.isfile(policy_path):
        add('⑦', '法律里有 listeners 且含本套接字', False, 'policy.json 不存在')
        return rows, reds
    try:
        pol = json.loads(read(policy_path))
    except Exception as e:                                  # 法律读不出来也是红
        add('⑦', '法律里有 listeners 且含本套接字', False, 'policy.json 解析失败：%s' % e)
        return rows, reds
    listeners = pol.get('listeners')
    ok7 = bool(listeners) and any(
        (l.get('socket') == listen) for l in listeners if isinstance(l, dict))
    add('⑦', '法律里有 listeners 且含本套接字', ok7,
        'listeners=%s（要找 %r）' % ('缺少该键' if listeners is None else listeners, listen))

    # ⑪ **清单 ≡ 实际**（★"三处清单"变一处：唯一来源＝`install.sh` 的 `UNITS=`）
    files = sorted(f for f in os.listdir(deploy_dir)
                   if f.endswith('.socket') or f.endswith('.service'))
    if units is None or not units:
        add('⑪a', '清单里每个单元都有文件', False, '读不出 `install.sh` 的 `UNITS=` ⇒ **无法对账**')
        add('⑪b', '目录里每个单元都在清单里（或已登记未启用）', False, '同上')
    else:
        nofile = [u for u in units if not os.path.isfile(os.path.join(deploy_dir, u))]
        unlisted = [f for f in files if f not in units and f not in NOT_INSTALLED]
        add('⑪a', '清单里每个单元都有文件', not nofile, '清单 %d 件；缺文件=%s' % (len(units), nofile or '无'))
        add('⑪b', '目录里每个单元都在清单里（或已登记未启用）', not unlisted,
            '目录 %d 件／清单 %d 件；未登记=%s（已登记未启用=%s）'
            % (len(files), len(units), unlisted or '无', sorted(NOT_INSTALLED)))
        # ★ ⑪c：把"已登记未启用"的**连原因一起报出来** —— 报告行、不判红，
        #   但**不许被读成"已上线"**（AC-3：在册未上线必须单独报）。
        report('⑪c', '已登记未启用的单元（**报告行**）', 'WARN' if NOT_INSTALLED else 'ok',
               '；'.join('%s ＝ %s' % (k, v) for k, v in sorted(NOT_INSTALLED.items())) or '无')

    # ⑫ **盘上口的属主 ≡ 映射里那条的 uid**（★读 `stat`，★**不是**读单元、也不是读 `systemctl show`）
    #    ★为什么要有它（2026-10-05 真机现场）：★⑦⑩ 全绿，**而 `/run/world-core/omarchy.sock` 的属主是
    #      `world-core`** —— 单元里写的是 `SocketUser=omarchy`、`systemctl show` 也读得出它
    #      ⇒ ★**"映射说的 uid"与"盘上口的属主"之间以前【没有判据】**。
    #    ★比较口径：★**`os.stat(socket).st_uid` ≡ 映射那条的 `uid`**（映射里 `null` ＝ 在册未上线 ⇒ 不进本判据）。
    #    ★非 POSIX ⇒ 读不到 uid ⇒ **未校验**（★不许当通过）。
    _u12, _up = None, uids_path(deploy_dir)
    if _up and os.path.isfile(_up):
        try:
            _u12 = json.loads(read(_up)).get('uids')
        except Exception:
            _u12 = None
    if not (HAS_PWD and isinstance(_u12, dict)):
        report('⑫', '盘上口的属主 ≡ 映射 uid', 'SKIP',
               '非 POSIX（`os.stat().st_uid` 不可用）或映射件不在/读不出（%s）⇒ **未校验**，不是通过' % (_up or '无'))
    else:
        _live = [(s, u) for s, u in sorted(_u12.items()) if isinstance(u, int)]
        _bad, _absent = [], []
        for s, u in _live:
            if not os.path.exists(s):
                _absent.append(s)
                continue
            if os.stat(s).st_uid != u:
                _bad.append('%s: 盘上属主 uid=%d ／映射 uid=%d' % (s, os.stat(s).st_uid, u))
        add('⑫', '盘上口的属主 ≡ 映射 uid', not _bad,
            '在册且已上线 %d 条；不符=%s；盘上暂无=%s（★"盘上没有"记报告、不判红：在册未上线见⑨）'
            % (len(_live), '；'.join(_bad) if _bad else '无', ','.join(_absent) if _absent else '无'))

    # ⑩ **`owner`（法律里的名字）→ `uid`（部署面映射里的数字）对账**
    #    ★ 映射件路径**也跟 `install.sh` 走**（载体今天未定 ⇒ 本件不写死第二处说法）
    up = uids_path(deploy_dir)
    pairs = [(l.get('socket'), l.get('owner'))
             for l in (listeners if isinstance(listeners, list) else []) if isinstance(l, dict)]
    if not up or not os.path.isfile(up):
        report('⑩', 'owner→uid 映射对账（法律 ↔ 部署面映射）', 'SKIP',
               '映射件不存在（%s）⇒ **未校验**；它由 `install.sh` 跑 `tools/gen_owner_uid.py` 生成'
               '（★生成物，不入版本控制）' % (up or '路径取不到'))
    else:
        try:
            uu = json.loads(read(up)).get('uids')
        except Exception as e:
            uu = None
        if not isinstance(uu, dict):
            add('⑩', 'owner→uid 映射对账', False, '映射件读不出 `uids` 对象：%s' % up)
        else:
            extra = sorted(k for k in uu if k not in [s for s, _ in pairs])
            miss = sorted(s for s, _ in pairs if s not in uu)
            bad = []
            for s, o in pairs:
                want = None
                if HAS_PWD and o:
                    try:
                        want = pwd.getpwnam(o).pw_uid
                    except KeyError:
                        want = None
                got = uu.get(s)
                # ★ 非 POSIX 时**不比数值**（解析不了名字）⇒ 只比"有没有把 null 写成数字"
                if got != want and (HAS_PWD or got is not None):
                    bad.append('%s: 映射 %r ／法律侧算得 %r' % (s, got, want))
            add('⑩a', '映射里没有法律外的口', not extra, '路径=%s；账外=%s' % (up, extra or '无'))
            add('⑩b', '法律里每个口在映射里有行', not miss, '缺行=%s' % (miss or '无'))
            add('⑩c', '映射 uid ≡ 法律 owner 的解析值', not bad, '不符=%s' % (bad or '无'))

    # ⑧⑨ 渲染物 ↔ 法律（★2026-10-05 新增；判据正文见本文件顶部 docstring）
    law = sockets_of(pol)
    if law is None or not law:
        add('⑧', '渲染物 ⊆ 法律（账外口 ⇒ 红）', False,
            '法律里读不出非空 listeners（实得 %r）⇒ **无法对账**，不许当绿' % (law,))
    elif not channel_path or not os.path.isfile(channel_path):
        report('⑧', '渲染物 ⊆ 法律（账外口 ⇒ 红）', 'SKIP',
               '未给/找不到渲染物（--channel %s）⇒ **未校验**，不是通过'
               % (channel_path if channel_path else '未给'))
        report('⑨', '在册而渲染物里没有（报告行）', 'SKIP', '同上：未校验')
    else:
        rend = load_sockets(channel_path)
        if rend is None:
            add('⑧', '渲染物 ⊆ 法律（账外口 ⇒ 红）', False,
                '渲染物 %s 里读不出 listeners ⇒ **无法对账**，不许当绿' % channel_path)
        else:
            extra = [s for s in rend if s not in law]
            add('⑧', '渲染物 ⊆ 法律（账外口 ⇒ 红）', not extra,
                '渲染物 %d 条 / 法律 %d 条；账外口=%s' % (len(rend), len(law), extra or '无'))
            miss = [s for s in law if s not in rend]
            report('⑨', '在册而渲染物里没有（报告行）', 'ok' if not miss else 'WARN',
                   '在册 %d 条 / 渲染 %d 条；**在册未上线**=%s（运行态，不判红→但**不许读成"已上线"**）'
                   % (len(law), len(rend), miss or '无'))
    return rows, reds


def render(rows, reds, title):
    skipped = [r for r in rows if r[2] == 'SKIP']
    if reds:
        concl = '红'
    elif skipped:
        concl = '绿（但 %d 条**未校验**——未校验 ≠ 通过）' % len(skipped)
    else:
        concl = '绿'
    print('=' * 78)
    print(title)
    print('时点 = %s' % time.strftime('%Y-%m-%dT%H:%M:%S'))
    print('命令 = python tools/carrier_contract.py %s' % ' '.join(sys.argv[1:]))
    print('-' * 78)
    for no, name, verdict, detail in rows:
        print('  [%-4s] %-4s %-34s %s' % (verdict, no, name, detail))
    print('-' * 78)
    print('结论 = %s（红 %d 条：%s）' % (concl, len(reds), ','.join(reds) or '无'))
    if skipped:
        # ★ 与 `check.sh` 的 `run_tail` 同形：它认 `STATUS=SKIP`，据此打 ⏭ 而不是 ✅
        print('★未校验 %d 条：%s —— **未校验 ≠ 通过**' % (len(skipped), ','.join(r[0] for r in skipped)))
        print('STATUS=SKIP')
    print('=' * 78)
    return 1 if reds else 0


def self_test():
    """反例：把单元与渲染物复制到临时目录，逐个改坏，要求**每条判据都会红**。"""
    print('== 自测：每条判据都要会红（含 ⑧ 的负控／正控／未校验三档） ==')
    tmp = tempfile.mkdtemp(prefix='carrier-contract-')
    try:
        # ★ 清单的**唯一来源**＝`install.sh`（本件不再自带一份）⇒ 夹具必须把 `install.sh` 一起复制，
        #   否则 `unit_list(tmp)` 读不到 ⇒ ①a／⑪ 判红（★那不是假红，是**夹具没把法律面搬全**）。
        UNITS_T = unit_list(DEPLOY) or UNITS_FALLBACK
        for u in UNITS_T:
            shutil.copy(os.path.join(DEPLOY, u), os.path.join(tmp, u))
        shutil.copy(os.path.join(DEPLOY, 'install.sh'), os.path.join(tmp, 'install.sh'))
        # ★ 夹具里 `install.sh` 的 `UIDS=` 指到 **`/etc`**（Lead 钉死的部署面路径）⇒ 夹具必须先把它
        #   改到**夹具自己的目录里**：否则自测会去读（甚至写）`/etc` —— ★**测试绝不许碰 `/etc`**。
        _ins = os.path.join(tmp, 'install.sh')
        _t = read(_ins)
        _t2 = re.sub(r'^[ \t]*UIDS="[^"]*"', 'UIDS="$SRC_DIR/listener_uids.json"', _t, count=1, flags=re.M)
        if _t2 == _t:
            print('  ★自测前提不成立：夹具的 install.sh 里找不到 `UIDS=` 那一行')
            return 1
        with io.open(_ins, 'w', encoding='utf-8', newline='\n') as f:
            f.write(_t2)
        shutil.copy(README, os.path.join(tmp, 'README.md'))
        pol = os.path.join(tmp, 'policy.json')
        shutil.copy(POLICY, pol)
        chan = os.path.join(tmp, 'channel.json')

        law = load_sockets(pol) or []
        if not law:
            print('  ★自测前提不成立：法律里读不出 listeners ⇒ ⑧ 的自测无法进行')
            return 1

        def write_chan(socks):
            with io.open(chan, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps({'channel': 1,
                                    'listeners': [{'socket': s, 'actor': 'world://agent/t',
                                                   'uid': 0} for s in socks]}))

        # ⑧ 正控：渲染物＝法律的子集 ⇒ 不红
        write_chan(law[:1])
        _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        print('  [%s] 正控 ⑧ 渲染物＝法律子集 -> 红 %s'
              % ('绿-OK' if '⑧' not in reds else '★假红', ','.join(reds) or '无'))
        bad = 0 if '⑧' not in reds else 1

        # ⑧ 负控①：渲染物多一个**账外口** ⇒ 必须红
        write_chan(law[:1] + ['/run/world-core/evil.sock'])
        _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        hit = '⑧' in reds
        print('  [%s] 负控 ⑧a 渲染物多一条账外口 -> 红 %s'
              % ('红-OK' if hit else '★没红', ','.join(reds) or '无'))
        if not hit:
            bad += 1

        # ⑧ 负控②：法律那份读不出来 ⇒ 必须红（"读不出来"与"没有"是两个结论）
        pol_bad = os.path.join(tmp, 'policy-broken.json')
        with io.open(pol_bad, 'w', encoding='utf-8', newline='\n') as f:
            f.write('{"policy":1}')          # 没有 listeners
        write_chan(law[:1])
        _, reds = judge(tmp, pol_bad, os.path.join(tmp, 'README.md'), chan)
        hit = '⑦' in reds and '⑧' in reds
        print('  [%s] 负控 ⑧b 法律里没有 listeners -> 红 %s'
              % ('红-OK' if hit else '★没红', ','.join(reds) or '无'))
        if not hit:
            bad += 1

        # ⑧ 未校验档：未给渲染物 ⇒ 不红、但那一条必须是 SKIP（不许当绿）
        rows, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), None)
        v8 = [r[2] for r in rows if r[0] == '⑧']
        ok_skip = ('⑧' not in reds) and v8 == ['SKIP']
        out_txt = None
        if ok_skip:
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                render(rows, reds, 'self-test channel-missing')
            out_txt = buf.getvalue()
            ok_skip = 'STATUS=SKIP' in out_txt
        print('  [%s] 未校验 ⑧c 未给渲染物 -> ⑧=%s／红 %s／STATUS=SKIP=%s'
              % ('OK' if ok_skip else '★错', v8, ','.join(reds) or '无',
                 '有' if (out_txt and 'STATUS=SKIP' in out_txt) else '无'))
        if not ok_skip:
            bad += 1

        # ── 原有各条的反例（逐条改坏单元）──
        write_chan(law[:1])
        base_rows, base_reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        print('  基线（照抄的单元）：红 %d 条 -> %s' % (len(base_reds), ','.join(base_reds)))

        # ★ 反例的"原文"必须**现取**：`deploy/world-core.socket` 的 `SocketMode=` 会被**别人**改。
        #   实测（2026-10-05 T11，VM 私有镜像）：`bus` 把它从 `0660` 改成 `0600` 之后，
        #   本自测的 ⑥b 因为**找不到** `SocketMode=0660` 而 `[skip]` ⇒ **整场自测 `RC=1`**。
        #   ⇒ 锚点从**当前单元件**读出来，只把"改成坏值"这一步写死。
        #   （同族：同日 `cargo fmt` 因别人的件而红 ⇒ **判据/自测的输入也会被别人动到**；
        #     与 E22「三行其实是十行」同一个病：**"我跑的输入是谁的"**。）
        cur_mode = find_one(read(os.path.join(DEPLOY, 'world-core.socket')), 'SocketMode') or '0660'

        cases = [
            ('①a', 'world-core.socket', None, '删文件', 'rm'),
            ('①b', 'world-core.socket', 'ListenStream=/run/world-core/world.sock',
             'ListenStream=/run/other/x.sock', 'sub'),
            ('②', 'world-core.socket', 'SocketUser=world-core', 'SocketUser=someone-else', 'sub'),
            # ★ 2026-10-07 修：锚点必须**带上换行**，因为 `RuntimeDirectory=world-core`
            #   在件里第一次出现是**注释**里那句（`# \`RuntimeDirectory=world-core\` 的递归 chown…`），
            #   `replace(old,new,1)` 会改到注释 ⇒ 真指令没动 ⇒ 判据③**不会红**、
            #   而自测只报"★没红"（＝判据面是装饰）。带换行后锚点唯一命中真指令那一行。
            ('③', 'world-core.service', '\nRuntimeDirectory=world-core\n',
             '\nRuntimeDirectory=elsewhere\n', 'sub'),
            ('④a', 'world-core.service', 'ReadWritePaths=/var/lib/world-core /run/world-core',
             'ReadWritePaths=/run/world-core', 'sub'),
            ('④b', 'world-core-projectd.service', 'ReadOnlyPaths=/var/lib/world-core',
             'ReadWritePaths=/var/lib/world-core', 'sub'),
            ('④c', 'world-core-actd.service', 'ReadWritePaths=/var/lib/world-actd /run/world-actd',
             'ReadWritePaths=/var/lib/world-actd /run/world-actd /var/lib/world-core', 'sub'),
            ('⑤', 'world-core-actd.service', 'carrier serve', 'carrier serve --confirm', 'sub'),
            ('⑥a', 'world-core.service', 'User=world-core', 'User=root', 'sub'),
            ('⑥b', 'world-core.socket', 'SocketMode=%s' % cur_mode, 'SocketMode=0666', 'sub'),
        ]
        # ★ 投影单元已从清单摘除 ⇒ ④b 失去主体 ⇒ 它的反例**不再存在**（按 G1 记"未校验"，不当通过）
        if not any('projectd' in u for u in UNITS_T):
            cases = [c for c in cases if c[0] != '④b']
            print('  [SKIP] ④b 投影单元已从清单摘除 ⇒ 该条**未校验**（G1：数据面空不许判绿）')
        for no, fn, old, new, how in cases:
            # 每个反例用干净副本
            for u in UNITS_T:
                shutil.copy(os.path.join(DEPLOY, u), os.path.join(tmp, u))
            target = os.path.join(tmp, fn)
            if how == 'rm':
                os.remove(target)
            else:
                t = read(target)
                if old not in t:
                    print('  [skip] %s：找不到要改的原文 %r' % (no, old))
                    bad += 1
                    continue
                with io.open(target, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(t.replace(old, new, 1))
            _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
            hit = no in reds or (no == '①a' and '①a' in reds)
            print('  [%s] 反例 %-4s -> 红 %s' % ('红-OK' if hit else '★没红', no, ','.join(reds) or '无'))
            if not hit:
                bad += 1
        # ── ⑪b 负控：目录里塞一个**不在清单里**的单元件 ⇒ 必红
        stray = os.path.join(tmp, 'world-core-stray.socket')
        with io.open(stray, 'w', encoding='utf-8', newline='\n') as f:
            f.write('[Socket]\nListenStream=/run/world-core/stray.sock\n')
        _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        hit = '⑪b' in reds
        print('  [%s] 负控 ⑪b 目录多一个未登记单元件 -> 红 %s'
              % ('红-OK' if hit else '★没红', ','.join(reds) or '无'))
        if not hit:
            bad += 1
        os.remove(stray)

        # ── ⑩ 正控 ＋ 两负控（多口／缺行）
        up = os.path.join(tmp, 'listener_uids.json')

        def want_uid(o):
            if not (HAS_PWD and o):
                return None
            try:
                return pwd.getpwnam(o).pw_uid
            except KeyError:
                return None

        pol_obj = json.loads(read(pol))
        good = dict((x.get('socket'), want_uid(x.get('owner')))
                    for x in pol_obj.get('listeners', []) if isinstance(x, dict))
        with io.open(up, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'channel': 1, 'uids': good}, f)
        rows10, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        v10 = dict((r[0], r[2]) for r in rows10 if r[0] in ('⑩a', '⑩b', '⑩c'))
        ok10 = len(v10) == 3 and all(v == 'ok' for v in v10.values())
        print('  [%s] 正控 ⑩ 与法律一致的映射 -> %s' % ('绿-OK' if ok10 else '★假红', v10))
        if not ok10:
            bad += 1
        bad_map = dict(good)
        bad_map['/run/world-core/evil.sock'] = 0
        with io.open(up, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'channel': 1, 'uids': bad_map}, f)
        _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        hit = '⑩a' in reds
        print('  [%s] 负控 ⑩a 映射多一条账外口 -> 红 %s'
              % ('红-OK' if hit else '★没红', ','.join(reds) or '无'))
        if not hit:
            bad += 1
        with io.open(up, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'channel': 1, 'uids': {}}, f)
        _, reds = judge(tmp, pol, os.path.join(tmp, 'README.md'), chan)
        hit = '⑩b' in reds
        print('  [%s] 负控 ⑩b 映射缺行 -> 红 %s'
              % ('红-OK' if hit else '★没红', ','.join(reds) or '无'))
        if not hit:
            bad += 1
        os.remove(up)

        print('自测结论 = %s' % ('通过' if bad == 0 else '有 %d 条没红/出错' % bad))
        return 0 if bad == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def parse_args(argv):
    """`--channel <path>` 可覆盖渲染物路径；其余参数不认即报错（不静默忽略）。"""
    chan = CHANNEL
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--channel':
            if i + 1 >= len(argv):
                print('用法：python tools/carrier_contract.py [--channel <渲染物路径>]', file=sys.stderr)
                return None, 2
            chan = argv[i + 1]
            i += 2
            continue
        print('未知参数：%s\n用法：python tools/carrier_contract.py [--channel <渲染物路径>]' % a,
              file=sys.stderr)
        return None, 2
    return chan, 0


def main():
    if '--self-test' in sys.argv:
        return self_test()
    chan, rc = parse_args(sys.argv[1:])
    if rc:
        return rc
    rows, reds = judge(DEPLOY, POLICY, README, chan)
    return render(rows, reds, '载体契约门禁（deploy/ ↔ 法律 ↔ 渲染物）')


if __name__ == '__main__':
    sys.exit(main())
