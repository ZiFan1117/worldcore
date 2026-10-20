# -*- coding: utf-8 -*-
"""★ 治理动作的**本体本地实现**（C27：一文件一块）——确认 / 委托 / 策略 / 审计回账。

★ 作者令（逐字整理）：「内核执行完了就得给本体记账……本体把这个消息发给他，他执行完了以后就要记下来」。
★ 分工：
  · `confirm.request`：本体发一条待签请求（对象）；界面把它画成 Modal 给人；
  · `confirm.resolve`：**只有人**（票里的 actor=world://user/…）能签；签完「允许一次」或写一张委托（四格）；
  · `delegate.grant/revoke/list`：委托是**世界对象**（不是字符串）；
  · `policy.apply/revoke`：改内核策略必须人批、落账（guard 后面读它编译）；
  · `audit.record`：执行者/guard 把内核事实报回来，**本体写账**（HMAC 绑定，防伪造）。
"""
import datetime
import hashlib
import hmac
import os
import time

CODE_DENY = "PERMISSION_DENIED"
CODE_BAD = "PRECONDITION_FAILED"


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _name(prefix):
    return "%s-%d" % (prefix, int(time.time() * 1000))


def _is_human(actor):
    return str(actor or "").startswith("world://user/")


def _get(w, type_id, name):
    return w.store.get(name) or next(
        iter(w.store.search(type_id, {"name": name}) or []), None)


def _audit_key():
    for env in ("AIOS_AUDIT_KEY",):
        v = os.environ.get(env)
        if v:
            return v.encode("utf-8")
    for p in ("/usr/lib/aios/permit.key",):
        try:
            with open(p, "rb") as f:
                return f.read().strip()
        except OSError:
            continue
    return None


def _sign(params):
    key = _audit_key()
    if not key:
        return None
    payload = "|".join(str(params.get(k) or "") for k in
                       ("engine", "subject", "op", "result", "path", "policy"))
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def dispatch(name, params, actor, w, log=print):
    """★ 返回 (ok, body)。失败时 body 带 why/code（码用闭集里的）。"""
    params = params or {}
    try:
        if name == "delegate.grant":
            if not _is_human(actor):
                return False, {"why": "委托只有人能签（actor=%s）" % actor, "code": CODE_DENY}
            for k in ("to", "action", "expires", "max_uses"):
                if not params.get(k):
                    return False, {"why": "缺参数 %s" % k, "code": CODE_BAD}
            inst = w.store.create("delegation", {
                "name": _name("del"), "owner": actor, "to": str(params["to"]),
                "action": str(params["action"]), "expires": str(params["expires"]),
                "max_uses": int(params["max_uses"]), "used": 0, "state": "active",
            }, created_by=actor)
            return True, {"delegation": dict(inst.properties)}
        if name == "delegate.revoke":
            inst = _get(w, "delegation", params.get("name"))
            if inst is None or inst.properties.get("state") != "active":
                return False, {"why": "没有有效的委托：%r" % params.get("name"), "code": CODE_BAD}
            if inst.properties.get("owner") != actor:
                return False, {"why": "只有授权人能撤（owner=%s）" % inst.properties.get("owner"),
                               "code": CODE_DENY}
            if not params.get("reason"):
                return False, {"why": "撤委托必须写 reason", "code": CODE_BAD}
            w.store.update(inst.instance_id, {"state": "revoked"}, updated_by=actor)
            return True, {"delegation": inst.instance_id, "state": "revoked"}
        if name == "delegate.list":
            want_to = params.get("to") or ""
            rows = []
            for inst in w.store.search("delegation") or []:
                p = inst.properties
                if p.get("state") != "active":
                    continue
                if want_to and p.get("to") != want_to:
                    continue
                if not want_to and p.get("owner") != actor and p.get("to") != actor:
                    continue
                rows.append(dict(p))
            return True, {"count": len(rows), "delegations": rows}
        if name == "confirm.request":
            if not params.get("action"):
                return False, {"why": "缺参数 action", "code": CODE_BAD}
            inst = w.store.create("confirmation", {
                "name": _name("cf"), "for_actor": str(actor),
                "action": str(params["action"]),
                "summary": str(params.get("summary") or ""),
                "state": "pending", "at": _now_iso(),
            }, created_by=actor)
            return True, {"confirmation": dict(inst.properties)}
        if name == "confirm.resolve":
            if not _is_human(actor):
                return False, {"why": "确认只有人能签（actor=%s）" % actor, "code": CODE_DENY}
            inst = _get(w, "confirmation", params.get("name"))
            if inst is None:
                return False, {"why": "没有这条确认请求：%r" % params.get("name"),
                               "code": CODE_BAD}
            if inst.properties.get("state") != "pending":
                return False, {"why": "这条请求已处理（state=%s）"
                                      % inst.properties.get("state"), "code": CODE_BAD}
            decision = params.get("decision")
            if decision not in ("allow_once", "allow_delegation", "deny"):
                return False, {"why": "decision 不合法：%r" % decision, "code": CODE_BAD}
            if not params.get("reason"):
                return False, {"why": "签/拒必须写 reason", "code": CODE_BAD}
            w.store.update(inst.instance_id, {
                "state": "denied" if decision == "deny" else "allowed",
                "resolved_by": actor, "reason": str(params["reason"]),
            }, updated_by=actor)
            body = {"confirmation": inst.instance_id, "decision": decision}
            if decision == "allow_delegation":
                expires = params.get("expires") or (
                    datetime.datetime.now().astimezone() +
                    datetime.timedelta(hours=1)).isoformat(timespec="seconds")
                d = w.store.create("delegation", {
                    "name": _name("del"), "owner": actor,
                    "to": str(inst.properties.get("for_actor")),
                    "action": str(inst.properties.get("action")),
                    "expires": str(expires),
                    "max_uses": int(params.get("max_uses") or 1),
                    "used": 0, "state": "active",
                }, created_by=actor)
                body["delegation"] = dict(d.properties)
            return True, body
        if name == "policy.apply":
            if not _is_human(actor):
                return False, {"why": "改内核策略必须人批（actor=%s）" % actor, "code": CODE_DENY}
            for k in ("subject", "engine", "rules", "expires", "reason"):
                if not params.get(k):
                    return False, {"why": "缺参数 %s" % k, "code": CODE_BAD}
            inst = w.store.create("policy", {
                "name": _name("pol"), "owner": actor, "subject": str(params["subject"]),
                "engine": str(params["engine"]), "rules": str(params["rules"]),
                "expires": str(params["expires"]), "state": "active",
                "applied_at": _now_iso(),
            }, created_by=actor)
            return True, {"policy": dict(inst.properties)}
        if name == "policy.revoke":
            if not _is_human(actor):
                return False, {"why": "撤策略必须人批（actor=%s）" % actor, "code": CODE_DENY}
            inst = _get(w, "policy", params.get("name"))
            if inst is None:
                return False, {"why": "没有这条策略：%r" % params.get("name"), "code": CODE_BAD}
            w.store.update(inst.instance_id, {"state": "revoked"}, updated_by=actor)
            return True, {"policy": inst.instance_id, "state": "revoked"}
        if name == "audit.record":
            if not str(actor or "").startswith("world://guard/"):
                return False, {"why": "只有 guard 能报告内核事实", "code": CODE_DENY}
            got = params.get("sig") or ""
            want = _sign(params)
            if not want or not hmac.compare_digest(str(got), want):
                return False, {"why": "审计报告签名不对（HMAC）", "code": CODE_DENY}
            path = str(params.get("path") or "")
            w.stamp("act", kind_of="security", action="audit.record", actor=actor,
                    ok=(params.get("result") == "allow"),
                    engine=params.get("engine"), subject=params.get("subject"),
                    op=params.get("op"), result=params.get("result"),
                    path_hash=hashlib.sha256(path.encode("utf-8")).hexdigest()[:16],
                    policy=params.get("policy"))
            return True, {"recorded": True}
        return False, {"why": "不认识的动作：%s" % name, "code": CODE_BAD}
    except Exception as e:                                  # noqa: BLE001
        log("[governance] %s 失败：%s" % (name, e))
        return False, {"why": "治理动作异常：%s" % e, "code": CODE_BAD}
