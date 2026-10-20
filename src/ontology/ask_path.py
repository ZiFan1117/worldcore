# -*- coding: utf-8 -*-
"""★ 请求入口（world/ask）的一整条闸路 —— 从 `ontology_process.py` 拆出（C27：一文件一块）。

★ 闸的顺序（借订单样板／借书平台，逐条落）：
  ① 名字在册 → ①.5 参数 → ①.5b 验票 → ② 身份 → ②.5 身份可核 → ③ 许可
  → ④ 前置条件（可判的真跑；声明式进账）→ 路由（多态：按对象类型选执行者）→ 发凭证 → 转发。
★ 每次拒绝都落账（`World.reject`：闭集码＋类别）；请求方的回话里也带同一个码。
"""
import json

import action_contract
import governance
import identity
import permit
from world_codes import redact_params

T_ASK_RESULT = "world/ask/result"
T_EXEC = "world/exec"
T_NOTICE = "world/notice"


def handle(smp, w, session, log=print):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        w.reject("BAD_MESSAGE", action="ask", why="ask 不是 JSON")
        return
    name = msg.get("action") or ""
    # ★★ 闸①：名字在册吗
    reg, why = w.recognize(name, msg.get("roles"))
    if reg is None:
        w.reject("UNKNOWN_ACTION", action=name, actor=msg.get("actor"), why=why)
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why,
                                              "code": "UNKNOWN_ACTION"}, ensure_ascii=False))
        return
    # ★★ 闸①.5：参数（借自订单样板：**参数不合先拒**，机器可读码；有效性先于权威）
    _at = w.ontology.action_types.get(name)
    if _at is not None:
        _p_ok, _p_why, _p_code = action_contract.validate_params(_at, msg.get("params"))
        if not _p_ok:
            w.reject(_p_code, action=name, actor=msg.get("actor"), why=_p_why)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": _p_why,
                                                  "code": _p_code}, ensure_ascii=False))
            return
    # ★★ 闸①.5b：验票（★ 票是「认过了」的证据，比请求自称的 actor 可信）
    actor = msg.get("actor")
    ticket = msg.get("ticket") or (msg.get("params") or {}).get("ticket")
    if ticket:
        t, why_t = identity.check({"ticket": ticket})
        if t is None:
            w.reject("BAD_TICKET", action=name, actor=actor, why=why_t)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why_t,
                                                  "code": "BAD_TICKET"}, ensure_ascii=False))
            return
        actor = t["who"]          # ★ 有票 ⇒ 票里的 who 覆盖 actor（★ 票是认过的证据）
    # ★★ 闸②：无 actor 且无有效票 ⇒ ★ 显式拒绝（★ 不再默默塞匿名）
    #    ★★★ 例外：★ 认证动作本该没有身份（★ 人要登录时还没身份；
    #       ★ 不放行就成了「要登录先得有身份」的死结）。
    _noid_exempt = name == "identity.authenticate"
    # ★ 审计报告：执行者/guard 报内核事实——它没有「报到个体」也不该有票，靠 HMAC 绑定身份；
    #   许可闸仍照走（scope 只含 world://guard/kernel），所以不是谁都能报。
    _audit_exempt = name.startswith("audit.")
    if not actor and not (_noid_exempt or _audit_exempt):
        why_noid = "没有身份（★ 请求要带 actor，或带票）"
        w.reject("NO_IDENTITY", action=name, why=why_noid)
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why_noid,
                                              "code": "NO_IDENTITY"}, ensure_ascii=False))
        return
    # ★★ 闸②.5：★ 每报一个都要能核验 —— 人 ⇒ 必须有票；其他 ⇒ 必须报过到、成为过个体。
    #    ★ 作者令（逐字整理）：「一个进程可报多个个体，但每报一个都要能核验」。
    if not (_noid_exempt or _audit_exempt):
        _a_ok, _a_why, _a_code = identity.actor_ok(actor, bool(ticket), w.appeared)
        if not _a_ok:
            w.reject(_a_code, action=name, actor=actor, why=_a_why)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": _a_why,
                                                  "code": _a_code}, ensure_ascii=False))
            return
    # ★★ 闸③：许可（★ 认证动作不过闸 —— 它是入口；凭据校验在 identity 里）
    allowed, why2 = (True, None) if _noid_exempt else w.can_execute(actor, name)
    if not allowed:
        w.reject("PERMISSION_DENIED", action=name, actor=actor, why=why2)
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why2,
                                              "code": "PERMISSION_DENIED"}, ensure_ascii=False))
        return
    # ★★ 闸④：前置条件（借自订单样板）—— 可判的真跑；声明式的进账/手册，不假装判过
    _at = w.ontology.action_types.get(name)
    _declared = []
    if _at is not None:
        _c_ok, _c_why, _c_code, _declared = action_contract.check_preconditions(
            _at, w, msg.get("params") or {})
        if not _c_ok:
            w.reject(_c_code, action=name, actor=actor, why=_c_why)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": _c_why,
                                                  "code": _c_code}, ensure_ascii=False))
            return

    # ★★★ 本地执行：治理类（确认/委托/策略/审计）—— 本体自己办（不外转）
    if name.startswith(("confirm.", "delegate.", "policy.", "audit.")):
        ok, body = governance.dispatch(name, msg.get("params") or {}, actor, w, log=log)
        if ok:
            w.stamp("act", kind_of="result", rid=msg.get("id"), action=name, ok=True,
                    body=body)
            if name == "confirm.request" and isinstance(body, dict):
                # ★ 推给呈现/语义浏览器：把确认请求画成弹窗（人点/说后回 confirm.resolve）
                session.put(T_NOTICE, json.dumps(
                    {"kind": "confirm.request", "by": "world://ontology",
                     "confirmation": body.get("confirmation")}, ensure_ascii=False))
        else:
            w.reject((body or {}).get("code") or "PRECONDITION_FAILED", action=name,
                     actor=actor, why=(body or {}).get("why"))
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": ok, "body": body},
                                             ensure_ascii=False))
        return

    # ★★★ 本地执行：认证类 —— 「认」本来就是本体的事（★ 不外转）
    #    ★ 学 PAM／OIDC：★ 认过 ⇒ 发票；★ 别人【只看票，不碰密码】。
    if name.startswith("identity."):
        ok, body = identity.dispatch(name, msg.get("params") or {}, log=log)
        if ok:
            w.stamp("act", kind_of="result", rid=msg.get("id"), action=name, ok=True, body=body)
        else:
            w.reject("BAD_CREDENTIAL", action=name, actor=actor,
                     why=(body or {}).get("why") if isinstance(body, dict) else str(body))
        log("认证 %s ⇒ ok=%s" % (name, ok))
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": ok, "body": body},
                                             ensure_ascii=False))
        return

    # ★★ 要票的动作：space.* 凭票（★ 作者：拿了票个人空间就能查了）
    if name.startswith("space.") and name != "space.login":
        t, why_t = identity.check({"ticket": ticket})
        if t is not None:
            # ★★ 还要验【这张票是不是这个空间的】—— ★ 票的 scope 里得有它。
            #    ★ 作者裁（逐字）：「票不是决定了是给哪个人的吗？」
            _want = "space:" + (msg.get("params") or {}).get("space", "")
            _sc = t.get("scope") or []
            if _want != "space:" and _want not in _sc:
                why_t = "票里没有 %s（★ 这张票只能看 %s）" % (_want, _sc)
                t = None
        if t is None:
            w.reject("TICKET_SCOPE_DENIED", action=name, actor=actor, why=why_t)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why_t,
                                                  "code": "TICKET_SCOPE_DENIED"}, ensure_ascii=False))
            return
    # ★★ 本体【唯一发许可处】：先签发凭证 ⇒ 再把凭证号记进【本体的账】⇒ 转发时带上凭证
    # ★★ 路由（借书平台式多态）：动作声明了 applies_to.interface ⇒ 按【对象类型】的执行者走
    _route = action_contract.route_for(w, name, reg, msg.get("params") or {})
    if not _route.get("kind"):
        w.reject("PROVIDER_NOT_DECLARED", action=name, actor=actor, why="没有可用的执行者路由")
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False,
                                              "why": "没有可用的执行者路由",
                                              "code": "PROVIDER_NOT_DECLARED"}, ensure_ascii=False))
        return
    _effects = (_at.metadata or {}).get("effects") if _at is not None else None
    pm = permit.issue(name, msg.get("params"), actor)
    seq = w.stamp("act", kind_of="ask", action=name, actor=actor,
                  rid=msg.get("id"), params=redact_params(msg.get("params")),
                  route=_route.get("kind"), permit=(pm or {}).get("id"),
                  effects=_effects,
                  declared_checks=[p.get("statement") for p in _declared if p.get("statement")],
                  subject_class=_route.get("subject_class"))
    out = {"id": msg.get("id"), "at": seq, "action": name,
           "params": msg.get("params") or {}, "actor": actor,
           "route": _route.get("kind"), "permit": pm,
           "polymorphic": bool(_route.get("polymorphic")),
           "subject_class": _route.get("subject_class")}
    log("转 %s（%s）⇒ %s" % (name, seq, _route.get("kind")))
    session.put(T_EXEC, json.dumps(out, ensure_ascii=False))
