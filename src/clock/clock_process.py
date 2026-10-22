# -*- coding: utf-8 -*-
"""★ worldcore 时间面进程（`src/clock/`，一进程一夹）—— 只读的「世界时间」。

★ 借鉴 AI-OS S28「Constitutional Time Plane」：时间面是宪法级——
  单调、不可回拨、可审计。我们 v1 只做**只读**：报当前时刻/时区/偏移/单调秒/开机 id；
  **不改系统钟**（没有 clock.set 动作）。
★ 它做什么：报个体（clock）→ 注册 clock.now/clock.state → 订 world/exec（route=clock）
  → 验 permit + 核销 → 答时间/状态 → 回 world/exec/result；每 60s 更新一次自己的 now。
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import zenoh  # noqa: E402
import clock_ops  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol.keys import LEGACY as TOPIC  # noqa: E402
from protocol.registration import provider_register  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
CLOCK_NAME = os.environ.get("AIOS_CLOCK_NAME") or "clock0"
T_APPEAR = TOPIC["appear"]
T_REGISTER = TOPIC["register"]
T_EXEC = TOPIC["exec"]
T_RESULT = TOPIC["exec_result"]

ACTIONS = [
    {"action": "clock.now", "kind": "read", "why": "读世界当前时间（时区/偏移/单调秒/开机 id）"},
    {"action": "clock.state", "kind": "read", "why": "读时间面进程状态"},
]


def log(*a):
    print("[时间面]", *a, flush=True)


def me():
    d = clock_ops.now()
    d["class"] = "clock"
    d["reporter"] = "world://clock/" + CLOCK_NAME
    return d


def register_actions(session):
    provider_register(session, T_REGISTER, "clock", CLOCK_NAME, ACTIONS)
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    clock_ops.write_state()
    session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
    log("② 成为个体：clock/%s（now=%s boot=%s）"
        % (CLOCK_NAME, clock_ops.now().get("now"), clock_ops.boot_id()[:8]))
    register_actions(session)

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        if msg.get("route") not in (None, "", "clock"):
            return
        action = msg.get("action") or ""
        params = msg.get("params") or {}
        rid = msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "clock/" + CLOCK_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        ok2, body = clock_ops.dispatch(action, params)
        log("答 %s ⇒ ok=%s" % (action, ok2))
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2, "body": body if ok2 else None,
            "error": None if ok2 else body, "by": "clock/" + CLOCK_NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    log("③ 订上 %s（route=clock）" % T_EXEC)
    tick = 0
    while True:
        time.sleep(1)
        tick += 1
        clock_ops.write_state()          # ★ 每秒更新时钟权威快照（本体 ledger 读它）
        if tick % 60 == 0:
            session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
            log("④ 报时：%s（单调 %ss）" % (clock_ops.now().get("now"),
                                            clock_ops.now().get("monotonic_seconds")))


if __name__ == "__main__":
    main()
