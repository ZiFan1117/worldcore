# -*- coding: utf-8 -*-
"""★ 请求入口（world/ask）的一整条闸路 —— 从 `ontology_process.py` 拆出（C27：一文件一块）。

★ 闸的顺序（借订单样板／借书平台，逐条落）：
  ① 名字在册 → ①.5 参数 → ①.5b 验票 → ② 身份 → ②.5 身份可核 → ③ 许可
  → ④ 前置条件（可判的真跑；声明式进账）→ 路由（多态：按对象类型选执行者）→ 发凭证 → 转发。
★ 每次拒绝都落账（`World.reject`：闭集码＋类别）；请求方的回话里也带同一个码。
"""
import json

import datetime

from gate import action_contract
from govern import governance
from gate import identity
from gate import permit
from gate.world_codes import CONFIRM_ACTIONS, redact_params
import ontology_builtins  # noqa: E402  本体内建动作（notice/job/presence/不支持）

T_ASK_RESULT = "world/ask/result"
T_EXEC = "world/exec"
T_NOTICE = "world/notice"


def _actor_class(actor):
    a = str(actor or "")
    if not a.startswith("world://"):
        return ""
    return a[len("world://"):].split("/", 1)[0]


def _valid_delegation(w, actor, action):
    """★ 有效委托（四格）：active + 动作匹配 + 未过期 + 次数没用完。"""
    try:
        now = datetime.datetime.now().astimezone()
        for inst in w.store.search("delegation") or []:
            p = inst.properties
            if p.get("to") != actor or p.get("action") != action:
                continue
            if p.get("state") != "active":
                continue
            try:
                exp = datetime.datetime.fromisoformat(str(p.get("expires")))
            except Exception:
                continue
            if exp.tzinfo is None:
                exp = exp.astimezone()
            if exp <= now:
                continue
            if int(p.get("used") or 0) >= int(p.get("max_uses") or 0):
                continue
            return inst
    except Exception:
        return None
    return None


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
    # ★★ 闸③：许可 ＋ guard 弹窗（变更类：agent 请求 ⇒ 需人确认；人签的委托 ⇒ 放行）
    # ★ 明确不支持的动作：在权限之前就回 UNSUPPORTED（它们没有副作用，不该被“路由不存在”糊住）
    if name in ontology_builtins.UNSUPPORTED:
        why_u = ontology_builtins.UNSUPPORTED[name]
        w.stamp("act", kind_of="ask", action=name, actor=actor,
                rid=msg.get("id"), params=redact_params(msg.get("params") or {}),
                route="ontology")
        at_u = w.reject("UNSUPPORTED", action=name, actor=actor, why=why_u)
        session.put(T_ASK_RESULT, json.dumps({
            "id": msg.get("id"), "at": at_u, "action": name, "ok": False,
            "body": None, "code": "UNSUPPORTED", "why": why_u}, ensure_ascii=False))
        return

    _ac = _actor_class(actor)
    _dele = None
    _confirmish = (name in CONFIRM_ACTIONS and _ac in ("agent", "presence")
                   and not _noid_exempt)
    if _confirmish:
        _dele = _valid_delegation(w, actor, name)
        if _dele is None:
            # ★ guard 的意见：不是静默拒绝，而是请人确认 → 界面弹窗；人签后才走委托
            _okc, _bodyc = governance.dispatch("confirm.request", {
                "action": name,
                "summary": "guard：%s 是变更类动作，需要你在场确认" % name,
                "params": json.dumps(redact_params(msg.get("params") or {}),
                                     ensure_ascii=False),
            }, actor, w)
            _conf = ((_bodyc or {}).get("confirmation") or {})
            _cname = _conf.get("name") or ""
            if _okc:
                session.put(T_NOTICE, json.dumps(
                    {"kind": "confirm.request", "by": "world://guard",
                     "confirmation": _conf}, ensure_ascii=False))
            _why = ("guard：变更类动作需要人在场确认（confirmation=%s）" % _cname)
            w.reject("CONFIRM_REQUIRED", action=name, actor=actor, why=_why)
            session.put(T_ASK_RESULT, json.dumps(
                {"id": msg.get("id"), "ok": False, "why": _why,
                 "code": "CONFIRM_REQUIRED", "confirmation": _cname},
                ensure_ascii=False))
            return
        allowed = True
        why2 = "委托放行（%s）" % _dele.instance_id
        w.store.update(_dele.instance_id,
                       {"used": int(_dele.properties.get("used") or 0) + 1},
                       updated_by=actor)
    else:
        allowed, why2 = (True, None) if _noid_exempt else w.can_execute(actor, name)
        if not allowed:
            w.reject("PERMISSION_DENIED", action=name, actor=actor, why=why2)
            session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False,
                                                  "why": why2,
                                                  "code": "PERMISSION_DENIED"},
                                                 ensure_ascii=False))
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
    # ★ 本体内建动作（notice/job/presence）与显式不支持的动作：不转给提供者
    if ontology_builtins.handled(name):
        _b_ok, _b_body = ontology_builtins.dispatch(
            w, name, msg.get("params") or {}, actor)
        w.stamp("act", kind_of="ask", action=name, actor=actor,
                rid=msg.get("id"), params=redact_params(msg.get("params") or {}),
                route="ontology")
        if _b_ok:
            at = w.stamp("act", kind_of="result", rid=msg.get("id"),
                         action=name, ok=True, body=_b_body)
            out_body = _b_body
            code = None
        else:
            code = (_b_body or {}).get("code") or "REJECTED"
            why_b = (_b_body or {}).get("why") or str(_b_body)
            at = w.reject(code, action=name, actor=actor, why=why_b)
            out_body, why_msg = None, why_b
        session.put(T_ASK_RESULT, json.dumps({
            "id": msg.get("id"), "at": at, "action": name, "ok": _b_ok,
            "body": out_body, "code": code,
            "why": None if _b_ok else why_msg}, ensure_ascii=False))
        return

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
                  delegation=(_dele.instance_id if _dele is not None else None),
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
