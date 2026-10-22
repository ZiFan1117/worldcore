# -*- coding: utf-8 -*-
"""worldcore protocol v1 SDK —— 进程只通过这里构造/解析消息，不许手写 topic/字段。

注意：本 SDK 不直接连 Zenoh；调用方传入自己的 session 和 C1 topic。
"""
import json
import os
import sys
import uuid

from .message import require_message
from .keys import T


def _new_id(prefix):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def _msg(mtype, src, dst, data, msg_id=None):
    msg = {
        "protocol": "world.message.v1",
        "v": 1,
        "type": mtype,
        "id": msg_id or _new_id(mtype),
        "from": src,
        "to": dst,
        "data": data,
    }
    require_message(msg)
    return msg


def build_register(src, dst, individual, functions=None, actions=None, data_sources=None,
                   bindings=None):
    data = {
        "individual": individual,
        "functions": list(functions or []),
        "actions": list(actions or []),
        "data_sources": list(data_sources or []),
    }
    if bindings is not None:
        data["bindings"] = list(bindings)
    return _msg("register", src, dst, data)


def build_registered(src, dst, req_id, ok, why=None):
    data = {"ok": bool(ok)}
    if why:
        data["why"] = str(why)
    return _msg("registered", src, dst, data, msg_id=req_id)


def build_call(src, dst, fn, args, msg_id=None):
    args_value = dict(args) if isinstance(args, dict) else list(args)
    return _msg("call", src, dst, {"fn": fn, "args": args_value}, msg_id=msg_id)


def build_result(src, dst, req_id, ok, result=None, error=None, state_changes=None):
    data = {"ok": bool(ok)}
    if ok:
        data["result"] = result
    else:
        data["error"] = error or {"code": "FAILED", "detail": "未给错误"}
    if state_changes is not None:
        if not ok:
            raise ValueError("失败结果不能带 state_changes")
        data["state_changes"] = state_changes
    return _msg("result", src, dst, data, msg_id=req_id)


def build_state_report(src, dst, individual, rev, changes, cause=None):
    data = {"individual": individual, "rev": int(rev), "changes": dict(changes)}
    if cause:
        data["cause"] = dict(cause)
    return _msg("state_report", src, dst, data)


def build_state_apply(src, dst, individual, rev, changes, cause=None):
    data = {"individual": individual, "rev": int(rev), "changes": dict(changes)}
    if cause:
        data["cause"] = dict(cause)
    return _msg("state_apply", src, dst, data)


def build_state_ack(src, dst, req_id, rev, ok, why=None):
    data = {"rev": int(rev), "ok": bool(ok)}
    if why:
        data["why"] = str(why)
    return _msg("state_ack", src, dst, data, msg_id=req_id)


def build_event(src, dst, kind, **fields):
    data = {"kind": kind}
    data.update(fields)
    return _msg("event", src, dst, data)


def encode(msg):
    require_message(msg)
    return json.dumps(msg, ensure_ascii=False)


def parse(payload):
    raw = payload
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        raw = json.loads(raw)
    require_message(raw)
    return raw


def topic(name):
    if name not in T:
        raise KeyError("未登记的 key：%s" % name)
    return T[name]


def send_call(session, src, fn, args, *, dest=None, timeout_ms=30000):
    """只负责构造并发到 C1 的 call key；等待回包由调用方订阅 call_result。"""
    dst = dest or "world://ontology"
    msg = build_call(src, dst, fn, args)
    session.put(topic("call"), encode(msg))
    return msg["id"]
