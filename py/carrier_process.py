# -*- coding: utf-8 -*-
"""AIOS 载体进程（Python）—— ★ 这台计算机在【世界里】的代言。

★ 作者裁（2026-10-17）：「**全改成 Python 版本吧**」。

★ 两个面：
  ① **上向（报机器）**：★ 起来 ⇒ 报 `service/carrier`（成为个体）＋ 报在册动作（`world/alive`）
  ② **下向（执行）**：★ 收 `world/exec` ⇒ 查映射表 ⇒ `subprocess` 起程序 ⇒ 回 `world/exec/result`

★ 它【不做】的：★ 不裁决、★ 不记账、★ 不持身份（★ 名字永远在本体里，★ 它只说「我活着」）。

★★ 为什么是 Python：★ 现取 —— Rust 的 zenoh 在本机 `peer` 是孤岛、`client` 连不上（T-334/T-339）；
   而 **Python ＋ client 模式实测【能连、能发、能收】**。
"""

import json
import os
import subprocess
import sys
import time

import zenoh

T_APPEAR = "world/appear"
T_ALIVE = "world/alive"
T_EXEC = "world/exec"
T_RESULT = "world/ask/result"   # ★★ 2026-10-17 裁：**载体直接回给请求方**（★ 本体不在结果这条路上）
# ★ 「谁干的谁报」—— 载体是干的那个，★ 它回的才是第一手事实。

MAP_PATH = os.environ.get("AIOS_CARRIER_MAP", "/usr/lib/aios/command-map.jsonl")
ZENOH_ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
ME = {"class": "service", "name": "carrier", "unit": "aios-carrier", "state": "running"}


def log(*a):
    print("[载体]", *a, flush=True)


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
            except Exception:
                continue
            if r.get("action"):
                rows[r["action"]] = r
    return rows


def run_action(rows, action, params):
    """★ 查表 ⇒ 起程序 ⇒ 收输出。★ 不拼 shell（直接 execve）。"""
    reg = rows.get(action)
    if reg is None:
        return False, "载体侧不认识 %s（映射表里没有）" % action
    program = reg.get("program") or ""
    if not program:
        return False, "%s 没有程序（可能是界面类动作）" % action
    args = list(reg.get("args") or [])
    # ★ 请求里带了 args 就用请求的（★ 映射表今天没有参数格 —— 这是权宜）
    if isinstance(params, dict) and isinstance(params.get("args"), list):
        args = [str(x) for x in params["args"]]
    cmd = [program] + args
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=30)
    except FileNotFoundError:
        return False, "本机没有这个程序：%s" % program
    except subprocess.TimeoutExpired:
        return False, "超时（30 秒）：%s" % " ".join(cmd)
    except Exception as e:
        return False, "起不来：%s" % e
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        return False, "%s 退出码 %s\n%s" % (program, p.returncode, err.strip()[:500])
    return True, out


def main():
    rows = load_map(MAP_PATH)
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
    log("③ 成为个体：service/carrier（%s）" % ME["state"])

    # ★★ 上向 ②：报到（★ 说「这些名字我活着」；★ 启动【不注册】）
    for name in rows:
        session.put(T_ALIVE, json.dumps({"action": name, "by": "carrier"}, ensure_ascii=False))
    log("④ 报到完成：%d 条（★ 启动【不注册】）" % len(rows))

    # ★★ 下向：收请求
    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception as e:
            log("请求不是 JSON（%s）" % e)
            return
        action = msg.get("action") or ""
        params = msg.get("params") or {}
        rid = msg.get("id") or ""
        log("收到 %s（id=%s）" % (action, rid))
        ok, body = run_action(rows, action, params)
        out = {"id": rid, "action": action, "ok": ok,
               "body": body if ok else None,
               "error": None if ok else body}
        log("回话 %s ⇒ ok=%s（★ 直接回请求方 %s）" % (action, ok, T_RESULT))
        session.put(T_RESULT, json.dumps(out, ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    log("⑤ 订上了 %s（★ 一次声明、长期持有）" % T_EXEC)
    log("★ 载体起来了 —— 报机器 ＋ 执行 ＋ 回话（★ 不裁决、不记账、不持身份）")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        session.close()


if __name__ == "__main__":
    main()
