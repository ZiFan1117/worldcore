# -*- coding: utf-8 -*-
"""★ worldcore 网络面进程（`src/network/`，一进程一夹）—— 只读的网络接口与计数器。

★ 借鉴 AI-OS L8 Network/Hardware/Devices：设备/接口是世界的对象；
  v1 只读：报接口（名称/类型/状态/MAC/MTU/计数器）和网络面状态；**不配网、不改路由、不起外进程**。
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
import network_ops  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol.registration import provider_register  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
NET_NAME = os.environ.get("AIOS_NETWORK_NAME") or "network0"
T_APPEAR = "world/appear"
T_REGISTER = "world/register"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"

ACTIONS = [
    {"action": "network.list", "kind": "read", "why": "列网络接口与计数器（只读）"},
    {"action": "network.state", "kind": "read", "why": "读网络面状态（接口数/up/总字节）"},
    {"action": "network.addresses", "kind": "read", "why": "只读地址（IPv4/IPv6）"},
    {"action": "network.routes", "kind": "read", "why": "只读路由（IPv4/IPv6）"},
    {"action": "network.dns", "kind": "read", "why": "只读 DNS 配置"},
    {"action": "network.connections", "kind": "read", "why": "只读 TCP/UDP 连接表"},
]


def log(*a):
    print("[网络面]", *a, flush=True)


def me():
    ok, st = network_ops.state()
    d = st if ok else {"name": NET_NAME, "state": "running"}
    d["class"] = "network"
    d["reporter"] = "world://network/" + NET_NAME
    return d


def register_actions(session):
    provider_register(session, T_REGISTER, "network", NET_NAME, ACTIONS)
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def report_links(session):
    ok, d = network_ops.interfaces()
    if not ok:
        return
    for e in (d.get("interfaces") or []):
        f = {"class": "link", "name": e.get("name"),
             "kind": e.get("kind") or "other", "state": e.get("state") or "unknown",
             "reporter": "world://network/" + NET_NAME}
        for k in ("mac", "mtu", "ifindex", "rx_bytes", "tx_bytes",
                  "rx_packets", "tx_packets", "rx_errors", "tx_errors"):
            if e.get(k) is not None:
                f[k] = e[k]
        session.put(T_APPEAR, json.dumps(f, ensure_ascii=False))
    log("② 报接口个体 %d 个（up=%d）" % (d.get("count"), d.get("up")))


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
    log("③ 成为个体：network/%s（sys=%s）" % (NET_NAME, network_ops.sys_dir()))
    register_actions(session)
    time.sleep(1.0)          # 等本体收下 network 个体，再报接口（身份闸）
    report_links(session)

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        if msg.get("route") not in (None, "", "network"):
            return
        action, params = msg.get("action") or "", msg.get("params") or {}
        rid = msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "network/" + NET_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        ok2, body = network_ops.dispatch(action, params)
        log("答 %s ⇒ ok=%s" % (action, ok2))
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2, "body": body if ok2 else None,
            "error": None if ok2 else body, "by": "network/" + NET_NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    log("④ 订上 %s（route=network）" % T_EXEC)
    while True:
        time.sleep(60)
        session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
        report_links(session)


if __name__ == "__main__":
    main()
