# -*- coding: utf-8 -*-
"""★ 给 DSH 插件用的【总线桥】：只发 world/* 三样，★ 不碰别的。

   ★ 一次一问，JSON 进出：
     python3 world_cli.py query  '{"kind":"world"}'
     python3 world_cli.py ask    '{"action":"sys.GetMemoryInfo","params":{}}'
     python3 world_cli.py frame  '<A2UI 帧 JSON>'

   ★ 它【不执行】、不判许可 —— 那是本体和载体的事。
"""
import json
import sys
import time
import uuid

import zenoh

BUS = "tcp/127.0.0.1:7447"


def open_s():
    c = zenoh.Config()
    c.insert_json5("mode", '"client"')
    c.insert_json5("scouting/multicast/enabled", "false")
    c.insert_json5("connect/endpoints", json.dumps([BUS]))
    return zenoh.open(c)


def wait(sub, key, rid, maxs=40):
    for _ in range(int(maxs * 10)):
        if rid in sub:
            return sub.pop(rid)
        time.sleep(0.1)
    return {"ok": False, "why": "超时（%d 秒）" % maxs}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
    s = open_s()
    got = {}

    def on(m):
        d = json.loads(m.payload.to_string())
        got[d.get("id")] = d

    if cmd == "query":
        s.declare_subscriber("world/query/result", on)
        time.sleep(1.0)
        rid = "dc-" + uuid.uuid4().hex[:8]
        msg = json.loads(raw)
        msg["id"] = rid
        s.put("world/query", json.dumps(msg, ensure_ascii=False))
        out = wait(got, "world/query/result", rid)
    elif cmd == "ask":
        s.declare_subscriber("world/ask/result", on)
        time.sleep(1.0)
        rid = "da-" + uuid.uuid4().hex[:8]
        msg = json.loads(raw)
        msg.setdefault("actor", "world://agent/dsh")
        msg["id"] = rid
        s.put("world/ask", json.dumps(msg, ensure_ascii=False))
        out = wait(got, "world/ask/result", rid, 60)
    elif cmd == "frame":
        rid = "df-" + uuid.uuid4().hex[:8]
        s.put("world/notice", json.dumps({
            "kind": "a2ui.frame", "by": "world://agent/dsh",
            "about": "界面", "frame": json.loads(raw)}, ensure_ascii=False))
        time.sleep(0.6)
        out = {"ok": True, "note": "已发 world/notice（★ 经本体）"}
    else:
        out = {"ok": False, "why": "不认识的命令：%s" % cmd}
    s.close()
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
