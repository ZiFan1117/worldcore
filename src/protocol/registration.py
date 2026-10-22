# -*- coding: utf-8 -*-
"""provider 注册的 P2 信封构造：所有 provider 用同一形状，不手写五格。"""
from . import sdk


def provider_register(session, topic, kind, name, actions):
    """actions: [{"action","kind","why"}]；只登记 law 已有动作的绑定。"""
    bindings = []
    for a in actions:
        bindings.append({
            "action": a["action"],
            "function": a["action"].split(".", 1)[-1],
            "required_roles": [kind],
            "registered_by_kind": kind,
        })
    msg = sdk.build_register(
        "world://%s/%s" % (kind, name),
        "world://ontology",
        {"id": "world://%s/%s" % (kind, name), "object_type": kind},
        bindings=bindings,
    )
    session.put(topic, sdk.encode(msg))
