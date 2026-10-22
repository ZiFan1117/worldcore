# -*- coding: utf-8 -*-
"""worldcore protocol v1 · C1 key/路由/ACL 唯一出处。

所有进程必须 import 这里的常量；不许各自手写 `world/...` 字符串。
部署层用同一份 TOPICS 生成 Zenoh ACL。
"""
ROLES = ("caller", "provider", "ontology", "subscriber")

TOPICS = {
    "register": {
        "topic": "world/register",
        "publish": ["provider"],
        "subscribe": ["ontology"],
    },
    "register_result": {
        "topic": "world/register/result",
        "publish": ["ontology"],
        "subscribe": ["provider"],
    },
    "call": {
        "topic": "world/call",
        "publish": ["caller"],
        "subscribe": ["ontology"],
    },
    "call_exec": {
        "topic": "world/call/exec",
        "publish": ["ontology"],
        "subscribe": ["provider"],
    },
    "call_exec_result": {
        "topic": "world/call/exec/result",
        "publish": ["provider"],
        "subscribe": ["ontology"],
    },
    "call_result": {
        "topic": "world/call/result",
        "publish": ["ontology"],
        "subscribe": ["caller"],
    },
    "state_report": {
        "topic": "world/state/report",
        "publish": ["provider"],
        "subscribe": ["ontology"],
    },
    "state_apply": {
        "topic": "world/state/apply",
        "publish": ["ontology"],
        "subscribe": ["provider"],
    },
    "state_ack": {
        "topic": "world/state/ack",
        "publish": ["provider"],
        "subscribe": ["ontology"],
    },
    "event": {
        "topic": "world/event",
        "publish": ["ontology"],
        "subscribe": ["subscriber"],
    },
    "permit_consume": {
        "topic": "world/permit/consume",
        "publish": ["provider"],
        "subscribe": ["ontology"],
    },
    "permit_consume_result": {
        "topic": "world/permit/consume/result",
        "publish": ["ontology"],
        "subscribe": ["provider"],
    },
}

T = {name: spec["topic"] for name, spec in TOPICS.items()}


def validate_topics(topics: dict) -> list:
    """返回错误码列表；空列表＝合法。"""
    errors = []
    seen = set()
    for name, spec in (topics or {}).items():
        if not isinstance(spec, dict):
            errors.append("BAD_TOPIC_SPEC:%s" % name)
            continue
        topic = spec.get("topic")
        if not isinstance(topic, str) or not topic.startswith("world/") or topic != topic.lower():
            errors.append("BAD_TOPIC:%s" % topic)
        if topic in seen:
            errors.append("DUPLICATE_TOPIC:%s" % topic)
        seen.add(topic)
        pub = spec.get("publish")
        sub = spec.get("subscribe")
        if not isinstance(pub, list) or not pub:
            errors.append("MISSING_PUBLISH:%s" % name)
        if not isinstance(sub, list) or not sub:
            errors.append("MISSING_SUBSCRIBE:%s" % name)
        for role in (pub or []) + (sub or []):
            if role not in ROLES:
                errors.append("BAD_ROLE:%s" % role)
        if topic == "world/call/exec" and pub != ["ontology"]:
            errors.append("EXEC_PUBLISH_NOT_ONTOLOGY")
    return errors
