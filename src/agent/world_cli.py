#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ DSH ↔ 世界 的【桥】—— 一条命令一问一答，JSON 进 JSON 出。

★ 作者令（逐字整理）：「所有的交互啥的必须过这个所谓的本体」；
  「这个那那就写个桥吧，写个桥吧」。
★ 它是什么：**总线的正规 Python 客户端**（DSH 插件 dsh-plugin-aios-world 用它）。
★ 它不是什么：不执行命令、不判许可、不记账——只发 `world/*` 三种。
★ 为什么要有它：Node 的 zenoh 绑定全试死了（zenoh-node 只有 peer、zenoh-ts 要 remote-api 插件），
  所以让 DSH 插件经【一个子进程】走总线；桥只按协议收发。

用法：
  python3 world_cli.py query '{"kind":"actions"}'
  python3 world_cli.py ask   '{"action":"sys.GetMemoryInfo","params":{}}'
  python3 world_cli.py frame '<A2UI frame JSON>'

★ 环境：AIOS_BUS（默认 tcp/127.0.0.1:7447）、AIOS_AGENT_NAME（默认 dsh）。
★ 回话：stdout 最后一行是 JSON（插件只读最后一行）；诊断走 stderr。
"""
import json
import os
import sys
import threading
import time
import uuid

import zenoh

BUS = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
AGENT = os.environ.get("AIOS_AGENT_NAME", "dsh")

T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_NOTICE = "world/notice"


def _session():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([BUS]))
    return zenoh.open(conf)


def _wait_for(s, topic, req_id, timeout):
    """★ 等一条带同一个 id 的回话；等到就返回对象，超时返回带 why 的对象。"""
    box, ev = {}, threading.Event()

    def _on(sample):
        try:
            d = json.loads(sample.payload.to_string())
        except Exception as e:              # 坏消息只记录、不打断（★ 不是静默：上 stderr）
            print("[world_cli] 坏回话：%s" % (str(e)[:120],), file=sys.stderr)
            return
        if d.get("id") == req_id:
            box.update(d)
            ev.set()

    sub = s.declare_subscriber(topic, _on)
    try:
        if not ev.wait(timeout):
            return {"ok": False, "why": "超时（%ss）等 %s" % (timeout, topic)}
        return box
    finally:
        try:
            sub.undeclare()
        except Exception as e:
            print("[world_cli] 退订失败：%s" % (str(e)[:120],), file=sys.stderr)


def main(argv):
    if len(argv) < 3:
        print(json.dumps({"ok": False, "why": "用法：world_cli.py <query|ask|frame> <json>"},
                         ensure_ascii=False))
        return 2
    cmd, raw = argv[1], argv[2]
    try:
        payload = json.loads(raw)
    except Exception as e:
        print(json.dumps({"ok": False, "why": "payload 不是 JSON：%s" % (str(e)[:160],)},
                         ensure_ascii=False))
        return 2
    rid = "dsh-" + uuid.uuid4().hex[:10]
    s = _session()
    try:
        if cmd == "frame":
            note = {"kind": "a2ui.frame", "by": "world://agent/" + AGENT,
                    "about": "dsh 画的界面（经本体）", "frame": payload}
            s.put(T_NOTICE, json.dumps(note, ensure_ascii=False))
            print(json.dumps({"ok": True, "note": "已发 world/notice"}, ensure_ascii=False))
            return 0
        if cmd not in ("query", "ask"):
            print(json.dumps({"ok": False, "why": "不认识的命令：%s（只 query/ask/frame）" % cmd},
                             ensure_ascii=False))
            return 2
        payload["id"] = rid
        if cmd == "query":
            payload.setdefault("actor", "world://agent/" + AGENT)
            out, res = T_QUERY, T_QUERY_RESULT
        else:
            payload.setdefault("actor", "world://agent/" + AGENT)
            out, res = T_ASK, T_ASK_RESULT
        s.put(out, json.dumps(payload, ensure_ascii=False))
        d = _wait_for(s, res, rid, 110)
        print(json.dumps(d, ensure_ascii=False))
        return 0
    finally:
        s.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
