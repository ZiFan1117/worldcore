# -*- coding: utf-8 -*-
"""P2 state 通道（最小）：provider 报状态 → ontology 校验 → 缓存 + 账 + ack。"""
import json

from protocol import sdk
from protocol.keys import T
from protocol.message import require_message
from protocol.state import validate_state


def handle_report(smp, w, session, log=print):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    try:
        require_message(msg)
    except Exception as exc:  # noqa: BLE001
        w.reject("BAD_MESSAGE", action="state_report", why=str(exc))
        return
    if msg.get("type") != "state_report":
        return
    errs = validate_state(msg, None)
    if errs:
        w.reject("BAD_STATE", action="state_report", why="；".join(errs))
        return
    data = msg.get("data") or {}
    ind = data.get("individual") or ""
    rev = data.get("rev")
    changes = data.get("changes") or {}
    cache = getattr(w, "_state_cache", None)
    if cache is None:
        cache = {}
        w._state_cache = cache
    cache.setdefault(ind, {}).update(changes)
    seq = w.stamp("state", kind_of="state", actor=msg.get("from"), individual=ind,
                  rev=rev, changes=changes)
    ack = sdk.build_state_ack("world://ontology", msg.get("from"), msg.get("id"), rev, True)
    session.put(T["state_ack"], sdk.encode(ack))
    log("P2 state %s rev=%s ⇒ %s（%s）" % (ind, rev, seq, "；".join(errs) or "ok"))
