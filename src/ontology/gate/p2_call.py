# -*- coding: utf-8 -*-
"""P2 call 路径（最小竖切）：caller → world/call → ontology → world/call/exec → provider。

只接 world action（fn = law action id）；外部函数仍走后续 external contributions。
旧 world/ask 路径不动；两条路并存，迁移期可回退。
"""
import json

from gate import action_contract
from gate import permit
from gate.world_codes import CONFIRM_ACTIONS
from protocol import sdk
from protocol.keys import T
from protocol.message import require_message


def _reply_error(session, caller, req_id, code, why):
    msg = sdk.build_result("world://ontology", caller, req_id, False,
                           error={"code": code, "detail": why})
    session.put(T["call_result"], sdk.encode(msg))


def handle_call(smp, w, session, log=print):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    try:
        require_message(msg)
    except Exception as exc:  # noqa: BLE001
        w.reject("BAD_MESSAGE", action="call", why="P2 call 不合法：%s" % exc)
        return
    if msg.get("type") != "call":
        w.reject("BAD_MESSAGE", action="call", why="call key 上不是 call 消息")
        return
    data = msg.get("data") or {}
    action = data.get("fn") or ""
    actor = msg.get("from") or ""
    params = data.get("args") if isinstance(data.get("args"), dict) else {}
    reg, why = w.recognize(action, None)
    if reg is None:
        _reply_error(session, actor, msg.get("id"), "UNKNOWN_ACTION", why)
        return
    at = w.ontology.action_types.get(action)
    if at is not None:
        ok, why_p, code = action_contract.validate_params(at, params)
        if not ok:
            _reply_error(session, actor, msg.get("id"), code, why_p)
            return
        okp, why_p, code_p, _declared = action_contract.check_preconditions(at, w, params)
        if not okp:
            _reply_error(session, actor, msg.get("id"), code_p, why_p)
            return
    if action in CONFIRM_ACTIONS:
        _reply_error(session, actor, msg.get("id"), "CONFIRM_REQUIRED",
                     "P2 call 尚未接人确认链；变更类动作请走 world/ask")
        return
    allowed, why_c = w.can_execute(actor, action)
    if not allowed:
        _reply_error(session, actor, msg.get("id"), "PERMISSION_DENIED", why_c)
        return
    route = action_contract.route_for(w, action, reg, params)
    if not route.get("kind"):
        _reply_error(session, actor, msg.get("id"), "PROVIDER_NOT_DECLARED", "没有可用路由")
        return
    pm = permit.issue(action, params, actor)
    pending = getattr(w, "_p2_pending", None)
    if pending is None:
        pending = {}
        w._p2_pending = pending
    pending[msg["id"]] = {"caller": actor, "action": action}
    seq = w.stamp("act", kind_of="ask", action=action, actor=actor,
                  rid=msg["id"], route=route.get("kind"), permit=(pm or {}).get("id"))
    out = sdk.build_call("world://ontology", "world://%s" % route.get("kind"),
                         action, params, msg_id=msg["id"])
    out["data"].update({"permit": pm, "route": route.get("kind"), "request_id": msg["id"]})
    session.put(T["call_exec"], sdk.encode(out))
    log("P2 转 %s（%s）⇒ %s" % (action, seq, route.get("kind")))


def handle_result(smp, w, session, log=print):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    try:
        require_message(msg)
    except Exception:
        return
    if msg.get("type") != "result":
        return
    pending = getattr(w, "_p2_pending", {}) or {}
    req = pending.pop(msg.get("id"), None)
    if req is None:
        w.reject("UNKNOWN_REQUEST", action="call/result", why="没有这个 P2 请求")
        return
    at = w.stamp("act", kind_of="result", rid=msg.get("id"), action=req["action"],
                 ok=(msg.get("data") or {}).get("ok"))
    out = sdk.build_result("world://ontology", req["caller"], msg["id"],
                           bool((msg.get("data") or {}).get("ok")),
                           result=(msg.get("data") or {}).get("result"),
                           error=(msg.get("data") or {}).get("error"))
    session.put(T["call_result"], sdk.encode(out))
    log("P2 结果 %s（%s）⇒ 回 %s" % (req["action"], at, req["caller"]))
