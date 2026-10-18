# -*- coding: utf-8 -*-
"""★★ 真 agent —— ★ 模型在环里：★ 它【自己决定】做什么、★ 自己决定画什么。

★ 作者令（逐字）：「我现在就是要一个智能体，然后让他渲染界面用 A2UI」「而且是要经过我的本体」
「我现在需要把这模型填进去」

★ 一轮四步（★ 每步都过本体，★ 一步都不绕过）：
  ① 问本体：★ `world/query` ⇒ 「世界有什么」（类／个体数／动作清单）
  ② 问模型：★ 「看着这个世界，你下一步要做什么？」⇒ 返回 `{"action": ..., "params": {...}}`
  ③ 做事：★ `world/ask` ⇒ 本体 ⇒ 计算机 ⇒ 结果
  ④ 问模型：★ 「结果是这样，画成 A2UI」⇒ 返回组件 JSON ⇒ `world/notice` ⇒ 本体 ⇒ GUI

★ 安全：★ 模型【只能】从【本体给的动作清单】里挑 ⇒ 挑了不在册的 ⇒ 本体拒（★ 有实测）。
★ 它不执行任何命令（★ 计算机执行）、不判许可（★ 本体判）、不自己发帧（★ 经 world/notice）。
"""

import json
import os
import time
import urllib.request
import uuid

import zenoh

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
NAME = os.environ.get("AIOS_AGENT_NAME", "dsh")
DID = os.environ.get("AIOS_AGENT_DID", "did:aios:agent:" + NAME)
ROUND = int(os.environ.get("AIOS_AGENT_ROUND", "45"))

LLM_URL = os.environ.get("AIOS_LLM_URL", "https://api.deepseek.com/chat/completions")
LLM_MODEL = os.environ.get("AIOS_LLM_MODEL", "deepseek-chat")
LLM_KEY = os.environ.get("AIOS_LLM_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""

T_APPEAR = "world/appear"
T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"
T_NOTICE = "world/notice"


def log(*a):
    print("[agent/llm]", *a, flush=True)


def ask_llm(system, user, max_tokens=900):
    """★ 调模型。★ 只认 JSON 回来。"""
    if not LLM_KEY:
        return None, "没有 AIOS_LLM_KEY"
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(LLM_URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + LLM_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        txt = data["choices"][0]["message"]["content"]
        return json.loads(txt), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:200])


class Agent:
    def __init__(self, session):
        self.s = session
        self.ask_results = {}
        self.query_results = {}

    def appear(self):
        self.s.put(T_APPEAR, json.dumps({
            "class": "agent", "name": NAME, "did": DID,
            "manifest": "src/agent/agent_llm.py（模型驱动；★ 全走本体）", "state": "running"}))
        log("① 发 appear：agent/%s" % NAME)

    def query(self, **kw):
        rid = "l-" + uuid.uuid4().hex[:8]
        kw["id"] = rid
        self.s.put(T_QUERY, json.dumps(kw, ensure_ascii=False))
        for _ in range(100):
            if rid in self.query_results:
                return self.query_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "查询超时"}

    def act(self, action, params=None, timeout=25):
        rid = "l-" + uuid.uuid4().hex[:8]
        self.s.put(T_ASK, json.dumps({
            "id": rid, "action": action, "actor": "world://agent/" + NAME,
            "params": params or {}}, ensure_ascii=False))
        for _ in range(int(timeout * 10)):
            if rid in self.ask_results:
                return self.ask_results.pop(rid)
            time.sleep(0.1)
        return {"ok": False, "why": "动作超时"}

    def notice(self, frame, about):
        self.s.put(T_NOTICE, json.dumps({
            "kind": "a2ui.frame", "by": "world://agent/" + NAME,
            "about": about, "frame": frame}, ensure_ascii=False))


SYS_PLAN = (
    "你是 AI-OS 世界里的【机器之眼】—— 一台 openSUSE 机器上的 agent。\n"
    "你的使命：★ 每轮【查一件对人有用的系统状态】，★ 并把它讲清楚。\n"
    "例：内存够不够、磁盘满不满、服务有没有挂、进程有没有失控。\n"
    "★ 你【不执行命令】—— 只能通过【世界】做事：从 available_actions 里挑一个。\n"
    "★ available_actions 是【完整且已核实】的清单（本机真能跑的）；清单外的不要挑。\n"
    "★ 只读动作（Get*／List*）随时可做；变更类会被人确认拦下。\n"
    "★ 别每轮都挑同一个：换着查不同的面。\n"
    "★ 严格输出 JSON：{\"action\": \"动作名\", \"params\": {…}, \"why\": \"一句话\"}\n"
    "★ 实在没有可用动作时，输出 {\"action\": \"\"}。"
)

SYS_DRAW = (
    "你是 AI-OS 世界的界面作者。给你【世界状态】和【刚做的那件事的结果】，\n"
    "请输出一帧 A2UI v1.0 的【组件数组】—— 只输出数组本身，不要外层包裹。\n"
    "可用组件：Text(text, 支持 **粗体**)、Column(children)、Row(children)、Card(child)、"
    "List(children)、Divider、Button(text)、Icon(name)。\n"
    "★ 第一个组件必须是 {\"id\":\"root\",\"component\":\"Column\",\"children\":[…]}\n"
    "★ 每个组件必须有唯一 id（root 除外用别的）。★ 简洁、最多 15 个组件。\n"
    '★ 严格输出 JSON：{"components": [...]}'
)


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = zenoh.open(conf)
    log("连上总线 %s" % ENDPOINT)
    if not LLM_KEY:
        log("★★ 没有 AIOS_LLM_KEY ⇒ 起不来（★ 设环境变量再试）")
        return
    log("★ 模型：%s @ %s" % (LLM_MODEL, LLM_URL))
    a = Agent(session)

    def on_ask(m):
        d = json.loads(m.payload.to_string())
        a.ask_results[d.get("id")] = d

    def on_query(m):
        d = json.loads(m.payload.to_string())
        a.query_results[d.get("id")] = d

    session.declare_subscriber(T_ASK_RESULT, on_ask)
    session.declare_subscriber(T_QUERY_RESULT, on_query)
    time.sleep(1.5)
    a.appear()
    time.sleep(2.0)
    rnd = 0
    while True:
        rnd += 1
        log("———— 第 %d 轮 ————" % rnd)
        world = a.query(kind="world")
        acts = a.query(kind="actions")
        log("① 问世界：ok=%s" % world.get("ok"))
        acts_data = acts.get("data") or {}
        # ★★★ 只把【本机可用】的动作给模型（★ 不截断！截断了它会以为清单不全而拒绝动手）
        avail = acts_data.get("available") or []
        world_data = world.get("data") or {}
        ctx_obj = {
            "world": {
                "types": world_data.get("types"),
                "instances": world_data.get("instances"),
                "registry_count": world_data.get("registry"),
            },
            "available_actions": avail,
            "unsupported_count": len(acts_data.get("unsupported") or []),
        }
        ctx = json.dumps(ctx_obj, ensure_ascii=False)
        plan, err = ask_llm(SYS_PLAN, ctx)
        if err:
            log("② 模型失手：%s" % err)
            time.sleep(ROUND)
            continue
        action = (plan or {}).get("action") or ""
        log("② 模型决定：%s  params=%s  why=%s" % (action, plan.get("params"), plan.get("why")))
        result = None
        if action:
            result = a.act(action, plan.get("params") or {})
            log("③ 做了 %s ⇒ ok=%s" % (action, result.get("ok")))
        payload = json.dumps({"world": world.get("data"),
                              "did": action, "params": plan.get("params"),
                              "ok": (result or {}).get("ok"),
                              "body": str((result or {}).get("body") or (result or {}).get("error") or (result or {}).get("why") or "")[:600]},
                             ensure_ascii=False)[:6000]
        draw, err2 = ask_llm(SYS_DRAW, payload)
        if err2 or not isinstance(draw, dict) or not isinstance(draw.get("components"), list):
            log("④ 模型画不出：%s" % (err2 or "返回不是 components 数组"))
            time.sleep(ROUND)
            continue
        comps = draw["components"]
        frame = {"version": "v1.0",
                 "name": "模型画的界面（★ agent/%s 经本体）" % NAME,
                 "messages": [
                     {"version": "v1.0", "createSurface": {
                         "surfaceId": "agent/%s" % NAME,
                         "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
                         "sendDataModel": True}},
                     {"version": "v1.0", "updateComponents": {
                         "surfaceId": "agent/%s" % NAME, "components": comps}},
                 ]}
        a.notice(frame, "模型画的界面")
        log("④ 发帧（★ 经本体 world/notice）：%d 个组件" % len(comps))
        time.sleep(ROUND)


if __name__ == "__main__":
    main()
