# -*- coding: utf-8 -*-
"""AIOS 计算机进程（Python）—— ★ 这台机器在【世界里】的代言与执行。

★ 作者裁（2026-10-17）：「**全改成 Python 版本吧**」。
★ 作者裁（2026-10-18）：「**就一个进程、一个类、一个个体**」⇒ 统一为 `computer`（计算机）。

★ 两个面：
  ① **上向（报机器）**：★ 起来 ⇒ 报 `computer/<hostname>`（成为个体）＋ 报在册动作（`world/alive`）
  ② **下向（执行）**：★ 收 `world/exec` ⇒ 查映射表 ⇒ `subprocess` 起程序 ⇒ 回 `world/exec/result`

★ 它【不做】的：★ 不裁决、★ 不记账、★ 不持身份（★ 名字永远在本体里，★ 它只说「我活着」）。

★★ 为什么是 Python：★ 现取 —— Rust 的 zenoh 在本机 `peer` 是孤岛、`client` 连不上（T-334/T-339）；
   而 **Python ＋ client 模式实测【能连、能发、能收】**。
"""

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import datetime
import sys
import time

import zenoh

# ★★ 本体发的审批凭据（permit.py 住在 src/ontology/）—— 执行器收指令前【必须验】它。
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
from permit import verify, consume_via_ontology  # noqa: E402

T_APPEAR = "world/appear"
T_ALIVE = "world/alive"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"   # ★★★ 2026-10-17 裁：**所有交互都过本体** —— 结果先回本体，本体判完再回请求方。
# ★ 作者令（逐字）：「所有的交互啥的必须过这个所谓的本体……除了这个数据是那啥的」

MAP_PATH = os.environ.get("AIOS_COMPUTER_MAP", "/usr/lib/aios/command-map.jsonl")
ZENOH_ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
COMPUTER_NAME = os.environ.get("AIOS_COMPUTER_NAME") or socket.gethostname()
ME = {"class": "computer", "name": COMPUTER_NAME, "hostname": COMPUTER_NAME,
      "state": "in-service", "reporter": "world://computer/" + COMPUTER_NAME}


def log(*a):
    print("[计算机]", *a, flush=True)


def load_map(path):
    """★ 读映射表：一行一条，每条 {action, program, args, required_roles, ...}。"""
    rows = {}
    if not os.path.exists(path):
        log("★ 映射表读不到：%s" % path)
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception as e:
                log("★★ 映射表这一行不是 JSON ⇒ 跳过（不许静默）：%s" % e)
                continue
            if r.get("action"):
                rows[r["action"]] = r
    return rows


def _subst(template, params, missing):
    """★ 把模板里的 `{x}` 用 `params[x]` 替换（★ 缺就记 missing）。"""
    def rep(m):
        k = m.group(1)
        if k not in params:
            missing.append(k)
            return ""
        v = params[k]
        return " ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else str(v)
    return re.sub(r"\{([a-z_][a-z0-9_]*)\}", rep, template)


def _expand(tok, params, missing):
    """★ 一个 token：`{x}` ⇒ params[x]（★ 列表展开成多个 token）。"""
    m = re.fullmatch(r"\{([a-z_][a-z0-9_]*)\}", tok)
    if not m:
        return [tok]
    k = m.group(1)
    if k not in params:
        missing.append(k)
        return []
    v = params[k]
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    return [str(v)]


def _run_file_mechanism(reg, params):
    """★ 文件类机制（★ 从 sysknife 的 FileScan/FileWrite/FilePatch/FileDelete 来）。

    ★★ 这类动作【不是跑命令】—— ★ 是【直接读写文件】。★ 计算机代劳。
    """
    mech = reg.get("mechanism") or ""
    missing = []
    path = _subst(reg.get("path") or "", params, missing)
    if missing:
        return False, "缺参数 %s（这个动作要 %s）" % (sorted(set(missing)), sorted((reg.get("params") or [])))
    if not path:
        return False, "路径为空"
    if mech == "FileScan":
        if not os.path.isdir(path):
            return False, "没有这个目录：%s" % path
        names = sorted(os.listdir(path))
        return True, "\n".join(names)
    if mech == "FileWrite":
        content = _subst(reg.get("content") or "", params, [])
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, "写了 %s（%d 字节）" % (path, len(content))
    if mech == "FileDelete":
        # ★★★ 2026-10-19 判据 C10（凡清除必留证）：删除必须【写理由】——
        #   ★ 理由随结果回本体 ⇒ 进账（`kind_of=result` 那一笔把 body 一起记）⇒ 这一笔可被任何人复核。
        #   ★ 不许「笔误了事」：没有理由 ⇒ 拒，不删。
        reason = (params.get("reason") or "").strip()
        if not reason:
            return False, "删除要写理由（★ 凡清除必留证：params.reason 不能空）"
        if not os.path.exists(path):
            return False, "没有这个文件：%s" % path
        os.remove(path)
        return True, "删了 %s（理由：%s）" % (path, reason)
    if mech == "FilePatch":
        search = reg.get("search") or ""
        replace = reg.get("replace") or ""
        if not os.path.exists(path):
            return False, "没有这个文件：%s" % path
        with open(path, "r", encoding="utf-8") as f:
            body = f.read()
        if search not in body:
            return False, "文件里没有要改的那段：%r" % search
        body = body.replace(search, replace, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return True, "改了 %s（%r → %r）" % (path, search, replace)
    return False, "不认识的机制：%s" % mech


def run_action(rows, action, params):
    """★ 查表 ⇒ 起程序 / 读写文件 ⇒ 收输出。★ 不拼 shell。

    ★★ 2026-10-17：
      ① `{x}` ← `params[x]`（★ 缺参就拒，不静默）；`{args}` 是【整体参数】
      ② 映射表的 `env` 作为环境变量
      ③ **执行时重新探测程序在不在**（★ 不只在启动时探）
      ④ 文件类机制（FileScan/Write/Patch/Delete）由计算机代劳
    """
    reg = rows.get(action)
    if reg is None:
        return False, "计算机侧不认识 %s（映射表里没有）" % action
    params = params if isinstance(params, dict) else {}
    mech = reg.get("mechanism") or "Command"
    if mech != "Command":
        return _run_file_mechanism(reg, params)
    program = reg.get("program") or ""
    if not program:
        return False, "%s 没有程序" % action
    # ★★ 执行时探测（★ 第 5 条缺口）
    if not shutil.which(program):
        return False, "本发行版没有 %s（这个动作可能需要别的发行版）" % program
    raw_args = list(reg.get("args") or [])
    if isinstance(params.get("args"), list):
        cmd_args = [str(x) for x in params["args"]]
    else:
        cmd_args, missing = [], []
        for tok in raw_args:
            if tok == "{args}":
                v = params.get("args")
                if isinstance(v, (list, tuple)):
                    cmd_args.extend(str(x) for x in v)
                elif v is not None:
                    cmd_args.append(str(v))
                else:
                    missing.append("args")
                continue
            cmd_args.extend(_expand(tok, params, missing))
        if missing:
            return False, "缺参数 %s（这个动作要 %s）" % (sorted(set(missing)), sorted((reg.get("params") or [])))
    env = dict(os.environ)
    for k, v in (reg.get("env") or {}).items():
        env[str(k)] = str(v)
    cmd = [program] + cmd_args
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=30, env=env)
    except FileNotFoundError:
        return False, "本发行版没有 %s（这个动作可能需要别的发行版）" % program
    except subprocess.TimeoutExpired:
        return False, "超时（30 秒）：%s" % " ".join(cmd)
    except Exception as e:
        return False, "起不来：%s" % e
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        return False, "%s 退出码 %s\n%s" % (program, p.returncode, err.strip()[:500])
    return True, out

def handle_exec(msg, rows, session):
    """★ 收一条 world/exec：**先验本体凭证，再问本体准不准** ⇒ 才执行。返回回话（回 world/exec/result）。

    ★★ 判据 C21：凭证绑「动作＋参数」、有期限；`一号一用` 的账在【本体】——
      执行器【不记账】，只问一句 `world/permit/consume`；本体说行才执行（验不过／超时都拒）。
    ★ 这就是「本体是唯一发许可处」在【执行器这一侧】的兑现：绕开本体直接往总线发指令，
      没有本体签的凭证 ⇒ 一条也执行不了。
    """
    action = msg.get("action") or ""
    params = msg.get("params") or {}
    rid = msg.get("id") or ""
    ok, why = verify(msg.get("permit"), action, params)
    if ok:
        ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
    if not ok:
        log("拒 %s（id=%s）⇒ 没有本体的许可：%s" % (action, rid, why))
        return {"id": rid, "action": action, "ok": False, "body": None,
                "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}
    log("收到 %s（id=%s，凭证过）" % (action, rid))
    if action == "object.retire":          # ★ 多态动作：路由到 computer 的那一支
        return _retire_self(session, msg)
    if action == "app.open_url":           # ★ 桌面「语义浏览器」图标：执行归计算机
        ok2, body = _open_url(params)
        return {"id": rid, "action": action, "ok": ok2,
                "body": body if ok2 else None, "error": None if ok2 else body}
    ok2, body = run_action(rows, action, params)
    return {"id": rid, "action": action, "ok": ok2,
            "body": body if ok2 else None, "error": None if ok2 else body}


def _open_url(params):
    """★ 打开一个 URL（桌面「语义浏览器」图标）：起浏览器窗口；**出向只许这里**（C19）。"""
    url = str((params or {}).get("url") or "")
    if not url.startswith(("http://", "https://")):
        return False, "url 不合法（只许 http/https）：%r" % url
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XAUTHORITY", "/run/lightdm/root/:0")
    prog = "firefox" if shutil.which("firefox") else ("xdg-open" if shutil.which("xdg-open") else "")
    if not prog:
        return False, "本机没有 firefox/xdg-open"
    try:
        if prog == "firefox":
            # ★ 专用 profile ＋ no-remote：不和别的 Firefox 实例抢锁（截图里那次是「已在运行但无响应」）
            prof = "/tmp/worldcore-browser"
            reason = "打开语义浏览器前清掉旧 profile 锁（旧实例已不在；不是删世界状态）"
            os.makedirs(prof, exist_ok=True)
            for f in ("lock", ".parentlock"):
                try:
                    os.unlink(os.path.join(prof, f))
                    log("★ app.open_url：清 %s（reason=%s）" % (f, reason))
                except OSError:
                    pass
            cmd = [prog, "--no-remote", "--new-instance", "--profile", prof,
                   "--new-window", url]
        else:
            cmd = [prog, url]
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        log("★ app.open_url ⇒ %s %s" % (" ".join(cmd), ""))
        return True, "已打开：%s" % url
    except Exception as e:                                  # noqa: BLE001
        return False, "起不来：%s" % e


def _retire_self(session, msg):
    """★ 多态动作 object.retire 的【计算机执行者】：只退休自己（computer/<名>）。

    ★ 效果：把自己的 state 置 retired，并【重新报到】——★ 状态的所有权在提供者，本体只记账。
    """
    rid, params = msg.get("id") or "", msg.get("params") or {}
    subject = params.get("subject") or ""
    me = "computer/%s" % COMPUTER_NAME
    if subject != me:
        return {"id": rid, "action": "object.retire", "ok": False, "body": None,
                "error": "不是我的对象（我只管 %s）：%s" % (me, subject)}
    ME["state"] = "retired"
    session.put(T_APPEAR, json.dumps(ME, ensure_ascii=False))
    log("★ object.retire ⇒ %s 置 retired（多态动作，路由到计算机）" % me)
    return {"id": rid, "action": "object.retire", "ok": True,
            "body": {"effect": "retired", "class": "computer", "subject": me}}


def probe_availability(rows):
    """★ 启动时报一次【哪些动作本机可用】（★ 执行时还会再探一次）。

    ★★ 2026-10-17：抄了 sysknife 的 156 个动作，其中大量是 Debian/Fedora 专有的
    （apt-*／dnf-*／rpm-ostree／ufw…）。★★ openSUSE 上没有 ⇒ 启动时就报清楚。
    """
    ok, missing = [], {}
    for name, reg in rows.items():
        mech = reg.get("mechanism") or "Command"
        if mech != "Command":
            ok.append(name)   # ★ 文件类机制不依赖外部程序
            continue
        prog = reg.get("program") or ""
        if not prog:
            missing[name] = "没有程序"
            continue
        if shutil.which(prog):
            ok.append(name)
        else:
            missing[name] = "本发行版没有 %s" % prog
    return ok, missing

def collect_metrics():
    """★ 底层事实（数据管道的采集端）：uptime/load/mem/cpu/os；读不到就留空。"""
    m = {}
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            m["uptime_seconds"] = int(float(f.read().split()[0]))
    except Exception as e:                                  # noqa: BLE001
        log("采集 uptime 失败：%s" % e)
    try:
        with open("/proc/loadavg", encoding="utf-8") as f:
            p = f.read().split()
            m["load1"] = float(p[0])
            m["load5"] = float(p[1])
    except Exception as e:                                  # noqa: BLE001
        log("采集 loadavg 失败：%s" % e)
    try:
        info = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                k, _, rest = line.partition(":")
                info[k] = int(rest.strip().split()[0])   # kB
        m["mem_total_mb"] = int(info["MemTotal"] / 1024)
        m["mem_available_mb"] = int(info.get("MemAvailable", 0) / 1024)
    except Exception as e:                                  # noqa: BLE001
        log("采集 meminfo 失败：%s" % e)
    m["cpu_count"] = os.cpu_count() or 0
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    m["os_name"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception as e:                                  # noqa: BLE001
        log("采集 os-release 失败：%s" % e)
    return m


# ★ 变化上报口径：uptime 是单调量、不参与「值变没变」的判定；
#   负载变化 > 0.1、可用内存变化 ≥ 64MB、其余属性变了才算「真有变化」。
SIG_KEYS = ("state", "hostname", "cpu_count", "os_name",
            "load1", "load5", "mem_total_mb", "mem_available_mb")


def metrics_sig(m):
    return {"state": m.get("state"), "hostname": m.get("hostname"),
            "cpu_count": m.get("cpu_count"), "os_name": m.get("os_name"),
            "load1": round(float(m.get("load1") or 0.0), 2),
            "load5": round(float(m.get("load5") or 0.0), 2),
            "mem_total_mb": m.get("mem_total_mb"),
            "mem_available_mb": m.get("mem_available_mb")}


def metrics_changed(prev, cur):
    """★ 值变了吗？（阈值防抖：负载 0.1／内存 64MB）"""
    if prev is None:
        return True
    for k in SIG_KEYS:
        a, b = prev.get(k), cur.get(k)
        if k in ("load1", "load5"):
            if abs(float(b or 0) - float(a or 0)) > 0.1:
                return True
        elif k == "mem_available_mb":
            if abs(int(b or 0) - int(a or 0)) >= 64:
                return True
        elif a != b:
            return True
    return False


def should_report(prev, cur, since_last, heartbeat=300.0):
    """★ 只有【值变了】或【心跳到点】才上报（心跳用来证明还活着）。"""
    if prev is None:
        return True
    if metrics_changed(prev, cur):
        return True
    return float(since_last) >= float(heartbeat)


def metrics_loop(session, every=10):
    """★ 数据管道的【上报端】：值变了才上报；300 秒心跳兜底。"""
    last_sig, last_at = None, 0.0
    while True:
        try:
            ME.update(collect_metrics())
            sig = metrics_sig(ME)
            now = time.time()
            since = now - last_at
            if should_report(last_sig, sig, since):
                ME["metrics_at"] = datetime.datetime.now().astimezone().isoformat(
                    timespec="seconds")
                ME["reporter"] = "world://computer/" + COMPUTER_NAME
                session.put(T_APPEAR, json.dumps(ME, ensure_ascii=False))
                log("★ 上报本体（%s）：uptime=%ss load1=%s mem=%s/%sMB"
                    % ("变化" if last_sig is not None and metrics_changed(last_sig, sig)
                       else "心跳", ME.get("uptime_seconds"), ME.get("load1"),
                       ME.get("mem_available_mb"), ME.get("mem_total_mb")))
                last_sig, last_at = sig, now
        except Exception as e:                              # noqa: BLE001
            log("★ 上报本体失败：%s" % e)
        time.sleep(every)



def main():
    rows = load_map(MAP_PATH)
    ok, missing = probe_availability(rows)
    # ★★ 报到时带上「我能做什么」（★ 模型据此只挑能跑的）
    ME["actions_available"] = ok
    ME["actions_unsupported"] = sorted(missing.keys())
    log("★ 可用动作 %d 个；本发行版不支持 %d 个" % (len(ok), len(missing)))
    for n in sorted(missing)[:8]:
        log("   ✗ %s（%s）" % (n, missing[n]))
    if len(missing) > 8:
        log("   … 还有 %d 个" % (len(missing) - 8))
    log("① 映射表 %d 条（%s）" % (len(rows), MAP_PATH))

    conf = zenoh.Config()
    # ★★★ 三条实测出来的（T-334/T-339）：peer 是孤岛、client 才跨进程通、关掉 multicast 免得瞎发现
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ZENOH_ENDPOINT]))
    session = zenoh.open(conf)
    log("② 连上总线 %s" % ZENOH_ENDPOINT)

    # ★★ 上向 ①：成为个体（★ 照本体 `service` 类的字段）
    session.put(T_APPEAR, json.dumps(ME, ensure_ascii=False))
    log("③ 成为个体：computer/%s（%s）" % (COMPUTER_NAME, ME["state"]))

    # ★★ 上向 ②：报到（★ 说「这些名字我活着」；★ 启动【不注册】）
    for name in rows:
        session.put(T_ALIVE, json.dumps({"action": name, "by": COMPUTER_NAME}, ensure_ascii=False))
    log("④ 报到完成：%d 条（★ 启动【不注册】）" % len(rows))

    # ★★ 下向：收请求
    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception as e:
            log("请求不是 JSON（%s）" % e)
            return
        # ★★ 只接【自己那一类】（本体广播 world/exec，带 route=注册者 kind）
        #    ★ 现取：sys.* 的 route 是 "world"（本体内置加载，不经 world/register）；
        #    所以 computer 接 ["computer", "world", None, ""]，只拒【明确是别人的】。
        route = msg.get("route")
        if route not in (None, "", "computer", "world"):
            return
        out = handle_exec(msg, rows, session)
        log("回话 %s ⇒ ok=%s（★ 先回本体 %s）" % (out.get("action"), out.get("ok"), T_RESULT))
        session.put(T_RESULT, json.dumps(out, ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    # ★ 数据管道：底层事实每 10 秒上报本体（采集 → 映射 → 上报）
    threading.Thread(target=metrics_loop, args=(session,), daemon=True).start()
    log("⑤ 订上了 %s（★ 一次声明、长期持有）" % T_EXEC)
    log("★ 计算机起来了 —— 报机器 ＋ 执行 ＋ 回话（★ 不裁决、不记账、不持身份）")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        session.close()


if __name__ == "__main__":
    main()
