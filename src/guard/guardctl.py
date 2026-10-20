#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ guardctl —— 问权限进程（guard）的**命令行客户端**。

用法：
  python3 guardctl.py ping
  python3 guardctl.py describe
  python3 guardctl.py check world://user/zhang sys.GetMemoryInfo
退出码：0 允许/成功；3 拒绝；2 用法/连不上。
★ 只问决定，不执行；执行是 guard-exec（Landlock）。
"""
import json
import os
import socket
import sys

SOCK = os.environ.get("AIOS_GUARD_SOCK", "/run/aios/guard.sock")


def ask(req, timeout=5.0):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(SOCK)
    f = s.makefile("rwb")
    f.write((json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))
    f.flush()
    line = f.readline().decode("utf-8", "replace").strip()
    s.close()
    return json.loads(line) if line else {"ok": False, "why": "没有回答"}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法：guardctl.py ping|describe|check <actor> <action>", file=sys.stderr)
        return 2
    op = argv[0]
    if op in ("ping", "describe"):
        req = {"op": op}
    elif op == "check" and len(argv) >= 3:
        req = {"op": "check", "actor": argv[1], "action": argv[2]}
    else:
        print("用法：guardctl.py ping|describe|check <actor> <action>", file=sys.stderr)
        return 2
    try:
        out = ask(req)
    except Exception as e:
        print("连不上 guard（%s）：%s" % (SOCK, e), file=sys.stderr)
        return 2
    if out.get("decision") == "confirm":
        out["meaning"] = "需人确认（界面弹窗；人签后走委托）"
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
