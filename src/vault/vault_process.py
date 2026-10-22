# -*- coding: utf-8 -*-
"""★ worldcore 保险库进程（`src/vault/`，一进程一夹）—— 只读秘密【元数据】库存。

★ 借鉴 AI-OS L4 Policy/Identity/Vault 三分家：身份/凭证在 ontology+permit，秘密库单独一个提供者；
  v1 只读：列秘密的 id/提供方/拥有者/轮换时间/状态/说明；**秘密值从不进世界、从不返回**。
★ 它不是什么：不签发/不读取秘密值、不配权限；值的使用仍走 guard/permit（未来 `vault.get` 要人确认）。
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
import vault_ops  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol.keys import LEGACY as TOPIC  # noqa: E402
from protocol.registration import provider_register  # noqa: E402
from protocol.provider_p2 import install as install_p2  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
VAULT_NAME = os.environ.get("AIOS_VAULT_NAME") or "vault0"
T_APPEAR = TOPIC["appear"]
T_REGISTER = TOPIC["register"]
T_EXEC = TOPIC["exec"]
T_RESULT = TOPIC["exec_result"]

ACTIONS = [
    {"action": "vault.list", "kind": "read", "why": "列秘密库存元数据（值从不返回）"},
    {"action": "vault.state", "kind": "read", "why": "读保险库状态（条目数/active）"},
]


def log(*a):
    print("[保险库]", *a, flush=True)


def me():
    ok, st = vault_ops.state()
    d = {"name": VAULT_NAME, "state": "running"}
    if ok:
        for k in ("secrets", "active", "checked_at"):
            if st.get(k) is not None:
                d[k] = st[k]
    d["class"] = "vault"
    d["reporter"] = "world://vault/" + VAULT_NAME
    return d


def register_actions(session):
    provider_register(session, T_REGISTER, "vault", VAULT_NAME, ACTIONS)
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def report_secrets(session):
    ok, d = vault_ops.list_secrets(20)
    if not ok:
        return
    for s in (d.get("secrets") or []):
        f = {"class": "secret", "name": s.get("name"), "state": s.get("state") or "active",
             "reporter": "world://vault/" + VAULT_NAME}
        for k in ("provider", "owner", "rotated_at", "description"):
            if s.get(k) is not None:
                f[k] = s[k]
        session.put(T_APPEAR, json.dumps(f, ensure_ascii=False))
    log("② 报秘密元数据个体 %d 个（值不在其中）" % (len(d.get("secrets") or [])))


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
    log("③ 成为个体：vault/%s（index=%s）" % (VAULT_NAME, vault_ops.index_path()))
    register_actions(session)
    time.sleep(1.0)          # 身份闸：先让本体收下 vault 个体，再报秘密元数据
    report_secrets(session)

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        if msg.get("route") not in (None, "", "vault"):
            return
        action, params = msg.get("action") or "", msg.get("params") or {}
        rid = msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "vault/" + VAULT_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        ok2, body = vault_ops.dispatch(action, params)
        log("答 %s ⇒ ok=%s" % (action, ok2))
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2, "body": body if ok2 else None,
            "error": None if ok2 else body, "by": "vault/" + VAULT_NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    install_p2(session, "vault", VAULT_NAME, vault_ops.dispatch)
    log("④ 订上 %s（route=vault）＋ P2 call_exec" % T_EXEC)
    while True:
        time.sleep(300)
        session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
        report_secrets(session)


if __name__ == "__main__":
    main()
