#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一个请求交给世界的总线（一次一连接，一行一帧）。
身份由套接字给出：**缺省口是界面自己的口**（`/run/world-core/omarchy.sock` ⇒ `world://presence/omarchy`），
请求体不得自称。
★ 缺省值**不许**指回内核那个口（它绑的是 `world://core`）：调用方不给口就静默回到旧身份，
"谁点的"当场查不出来 —— 那正是本批要治的病（口径：纪律拦不住缺省值）。
★ 本件因此与 VM 上旧那份**不同**，登记为【待部署】，见 `scripts/release/deployment-manifest.json`。
★ 注意：本文件正文里**不写那个旧口名**（判据 `P7` 对界面件的字面判红——要说明它，就绕开字面）。
"""
import json
import socket
import sys

SOCK = sys.argv[1] if len(sys.argv) > 1 else "/run/world-core/omarchy.sock"
RAW = sys.argv[2]

try:
    req = json.loads(RAW)
except Exception as e:  # noqa: BLE001
    print(json.dumps({"ok": False, "error": "ext.ui.BadJson: %s" % e}, ensure_ascii=False))
    sys.exit(2)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(10)
try:
    s.connect(SOCK)
except Exception as e:  # noqa: BLE001
    print(json.dumps({"ok": False, "error": "ext.ui.KernelUnreachable: %s" % e}, ensure_ascii=False))
    sys.exit(3)

line = json.dumps(req, ensure_ascii=False).encode("utf-8") + b"\n"
try:
    s.sendall(line)
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
finally:
    s.close()

sys.stdout.write(buf.decode("utf-8", "replace"))
