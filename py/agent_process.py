# -*- coding: utf-8 -*-
"""★★ 小 agent —— ★ 试验「一个 agent 注册进本体，★ 通过本体做事，★ 并把结果画成 A2UI」。

★ 作者令（逐字）：「用它来生成界面，就是**他要注册到这个本体里面**，**小的这个 Agent 来试验一下**，
  **让他通过本体来做一些事情**」

★ 它做四件（★ 全是【通过本体】，★ 不直连任何服务）：
  ① 注册：★ 发 `world/appear`（类 agent）⇒ 成为个体
  ② 问世界：★ 发 `world/query`（kind=world）⇒ 知道有什么
  ③ 做事：★ 发 `world/ask`（sys.GetServiceStatus / sys.GetMemoryInfo …）⇒ 本体转给载体执行
  ④ 出界面：★ 把结果拼成 A2UI 帧 ⇒ 发 `world/ui/frame` ⇒ GUI 落盘 ⇒ 渲染器画

★ 它不做：不执行命令（★ 载体执行）、不判许可（★ 本体判）、不画（★ 渲染器画）。
"""

import json
import os
import time
import uuid

import zenoh

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
NAME = os.environ.get("AIOS_AGENT_NAME", "dsh")
DID = os.environ.get("AIOS_AGENT_DID", "did:aios:agent:" + NAME)
ROUND_SECS = int(os.environ.get("AIOS_AGENT_ROUND", "30"))

T_APPEAR = "world/appear"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"
T_NOTICE = "world/notice"           # ★★ 帧也【过本体】（作者令）


def log(*a):
    print("[agent/%s]" % NAME, *a, flush=True)


class Agent:
    def __init__(self, session):
        self.s = session
        self.ask_results = {}
        self.query_results = {}

    # ── ① 注册 ──
    def appear(self):
        me = {"class": "agent", "name": NAME, "did": DID,
              "manifest": "py/agent_process.py（小 agent，通过本体做事）", "state": "running"}
        self.s.put(T_APPEAR, json.dumps(me, ensure_ascii=False))
        log("① 发 appear：agent/%s ⇒ 等本体认" % NAME)

    # ── ② 问世界 ──
    def query(self, **kw):
        rid = "a-" + uuid.uuid4().hex[:8]
        kw["id"] = rid
        self.s.put(T_QUERY, json.dumps(kw, ensure_ascii=False))
        for _ in range(100):
            if rid in self.query_results:
                return self.query_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "查询超时"}

    # ── ③ 做事（★ 走本体 ⇒ 本体转给载体）──
    def act(self, action, params=None, timeout=20):
        rid = "a-" + uuid.uuid4().hex[:8]
        msg = {"id": rid, "action": action, "actor": "world://agent/" + NAME,
               "params": params or {}}
        self.s.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        for _ in range(int(timeout * 10)):
            if rid in self.ask_results:
                return self.ask_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "动作超时"}

    # ── ④ 出界面 ──
    def emit_frame(self, world, probes):
        comps, n = [], [0]

        def nid(p):
            n[0] += 1
            return "%s_%d" % (p, n[0])

        items = []
        t = nid("t")
        comps.append({"id": t, "component": "Text",
                      "text": "**AIOS 小 agent 面板** —— 由 agent/%s 通过本体问来" % NAME})
        items.append(t)
        d = nid("d")
        comps.append({"id": d, "component": "Divider"})
        items.append(d)

        # 世界概览
        inst = (world.get("data") or {}).get("instances") or {}
        c = nid("c")
        col = nid("cc")
        comps.append({"id": c, "component": "Card", "child": col})
        comps.append({"id": col, "component": "Column", "children": []})
        colchildren = []
        tt = nid("t")
        comps.append({"id": tt, "component": "Text", "text": "**世界里的个体**（本体 ABox）"})
        colchildren.append(tt)
        for k, v in inst.items():
            x = nid("t")
            comps.append({"id": x, "component": "Text", "text": "%s：%s 个" % (k, v)})
            colchildren.append(x)
        comps[[i for i, z in enumerate(comps) if z["id"] == col][0]]["children"] = colchildren
        items.append(c)

        # 探测结果
        if probes:
            d2 = nid("d")
            comps.append({"id": d2, "component": "Divider"})
            items.append(d2)
            c2 = nid("c")
            col2 = nid("cc")
            comps.append({"id": c2, "component": "Card", "child": col2})
            comps.append({"id": col2, "component": "Column", "children": []})
            kids = []
            t2 = nid("t")
            comps.append({"id": t2, "component": "Text",
                          "text": "**通过本体做的事**（world/ask ⇒ 本体 ⇒ 载体）"})
            kids.append(t2)
            for p in probes:
                x = nid("t")
                ok = "✓" if p.get("ok") else "✗"
                body = (p.get("body") or p.get("error") or p.get("why") or "")
                body = str(body).replace("\n", " ")[:70]
                comps.append({"id": x, "component": "Text",
                              "text": "%s `%s` %s" % (ok, p.get("action"), body)})
                kids.append(x)
            comps[[i for i, z in enumerate(comps) if z["id"] == col2][0]]["children"] = kids
            items.append(c2)

        frame = {"version": "v1.0",
                 "name": "小 agent 面板（★ agent/%s 通过本体生成）" % NAME,
                 "messages": [
                     {"version": "v1.0",
                      "createSurface": {"surfaceId": "agent/%s" % NAME,
                                        "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
                                        "sendDataModel": True}},
                     {"version": "v1.0",
                      "updateComponents": {"surfaceId": "agent/%s" % NAME,
                                           "components": [{"id": "root", "component": "Column",
                                                           "children": items}] + comps}},
                 ]}
        self.s.put(T_NOTICE, json.dumps({"kind": "a2ui.frame", "by": "world://agent/" + NAME,
                                        "about": "界面", "frame": frame}, ensure_ascii=False))
        log("④ 发了一帧（★ 经本体 world/notice）：%d 个组件" % (len(comps) + 1))


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = zenoh.open(conf)
    log("连上总线 %s" % ENDPOINT)
    a = Agent(session)
    session.declare_subscriber(T_ASK_RESULT,
                               lambda m: a.ask_results.__setitem__(json.loads(m.payload.to_string()).get("id"), json.loads(m.payload.to_string())))
    session.declare_subscriber(T_QUERY_RESULT,
                               lambda m: a.query_results.__setitem__(json.loads(m.payload.to_string()).get("id"), json.loads(m.payload.to_string())))
    time.sleep(1.5)
    a.appear()
    time.sleep(2.0)
    probe_actions = ["sys.GetMemoryInfo", "sys.GetDiskUsage", "sys.ListServices"]
    while True:
        w = a.query(kind="world")
        log("② 问世界：ok=%s  instance=%s" % (w.get("ok"), (w.get("data") or {}).get("instances")))
        probes = []
        for act in probe_actions:
            r = a.act(act)
            log("③ 做事 %s ⇒ ok=%s" % (act, r.get("ok")))
            r["action"] = act
            probes.append(r)
        a.emit_frame(w, probes)
        time.sleep(ROUND_SECS)


if __name__ == "__main__":
    main()
