# -*- coding: utf-8 -*-
"""P2 call 冒烟（VM/本机均可）：world/call → provider → world/call/result。

用法：在装了 /usr/lib/aios 的机器上：
  AIOS_BUS_USER=tests python3 scripts/release/p2_call_smoke.py
"""
import json
import sys
import time

for p in ("/usr/lib/aios/src", "/usr/lib/aios/src/ontology"):
    if p not in sys.path:
        sys.path.insert(0, p)

import zenoh  # noqa: E402
import bus_auth  # noqa: E402
from protocol import sdk  # noqa: E402
from protocol.keys import T  # noqa: E402

conf = zenoh.Config()
conf.insert_json5("mode", '"client"')
conf.insert_json5("scouting/multicast/enabled", "false")
conf.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
s = bus_auth.open_bus(conf)
got = []


def on_result(smp):
    try:
        got.append(json.loads(smp.payload.to_string()))
    except Exception:
        pass


s.declare_subscriber(T["call_result"], on_result)
msg = sdk.build_call("world://user/zhang", "world://ontology", "file.stat",
                     {"path": "/etc/aios/zenoh.json5"})
s.put(T["call"], sdk.encode(msg))
for _ in range(100):
    if got:
        break
    time.sleep(0.1)
print(json.dumps(got[-1] if got else {"ok": False, "why": "timeout"}, ensure_ascii=False))
s.close()
sys.exit(0 if got and got[-1].get("data", {}).get("ok") else 1)
