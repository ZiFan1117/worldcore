# -*- coding: utf-8 -*-
"""provider 的 P2 exec 通用适配：world/call/exec → 本进程 dispatch → world/call/exec/result。"""
from gate import permit
from . import sdk
from .keys import T


def install(session, kind, name, dispatch):
    def on_exec(smp):
        msg = sdk.parse(smp.payload.to_string())
        if msg.get("type") != "call":
            return
        data = msg.get("data") or {}
        route = data.get("route")
        if route and route != kind:
            return
        action = data.get("fn") or ""
        params = data.get("args") if isinstance(data.get("args"), dict) else {}
        rid = msg.get("id") or ""
        ok, why = permit.verify(data.get("permit"), action, params)
        if ok:
            ok, why = permit.consume_via_ontology(session, data.get("permit"), action, params)
        if not ok:
            out = sdk.build_result("world://%s/%s" % (kind, name), "world://ontology",
                                   rid, False, error={"code": "PERMIT_DENIED", "detail": why})
            session.put(T["call_exec_result"], sdk.encode(out))
            return
        ok2, body = dispatch(action, params)
        out = sdk.build_result("world://%s/%s" % (kind, name), "world://ontology",
                               rid, ok2, result=body if ok2 else None,
                               error=None if ok2 else {"code": "EXEC_FAILED", "detail": body})
        session.put(T["call_exec_result"], sdk.encode(out))

    session.declare_subscriber(T["call_exec"], on_exec)
