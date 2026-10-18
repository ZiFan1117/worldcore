# -*- coding: utf-8 -*-
"""★★ 认证 —— ★ 本体四件里的第一件【认】。

★★ 作者令（逐字，2026-10-18）：
   ·「这个密码啥的是不是在本体空间中更合适呢？登录的这个是给个人那啥吗？
     当确定登录了以后，再给这个个人空间这块留个信息吧」
   ·「这个逻辑有没有现成的可以学一下人家做得更好的，别这么笨」

★★ 学的模型（按笨→好排）：
   ① **PAM**（Linux 登录）：`login` **不验密码**，把密码交给 PAM 模块；验过了才开会话。
   ② **OIDC / OAuth2**：client 把凭据交给 authorization endpoint；**认证中心发票**；
      resource server **只看票，不碰密码**。
   ③ **Kerberos**：认一次 ⇒ TGT ⇒ 处处拿票。

★★ 所以本件的职责【只有两件】：
   · **验**身份凭据（密码【只在这里】，不外传）
   · **发/查/销**票（票是"认过了"的证据）

★★ 不做什么：
   · ★ **不管空间**（空间只收"认过了"的通知）
   · ★ **不管呈现**（呈现只出脸、交凭据、换脸）
"""

import time
import uuid

# ★★ 票表 —— ★ 谁认过了、什么时候过期。★ 本体是【记】的那个，票记在这儿。
_TICKETS = {}

# ★ 测试账号（★ 作者令 2026-10-18：「先设定一个测试的用户名和密码吧，密码就是一个 0 就行」）
TEST_USER = "zhang"
TEST_PASS = "0"
# ★ 票的有效期。★ 默认 8 小时；★ 测试时用环境变量 AIOS_TICKET_TTL 设成 1 秒验「过期会拒」。
import os as _os
TICKET_TTL = int(_os.environ.get("AIOS_TICKET_TTL") or (8 * 3600))


def authenticate(params, log=print):
    """★ 认人：验凭据，通过则发票。★ 返回 (ok, body)。"""
    user = (params.get("user") or "").strip()
    secret = params.get("secret")
    if user != TEST_USER or (secret is not None and str(secret) != TEST_PASS):
        log("认被拒：user=%s" % user)
        return False, {"why": "身份凭据不对（★ 测试账号 %s ／ %s）" % (TEST_USER, TEST_PASS)}
    now = time.time()
    tk = "tk-" + uuid.uuid4().hex[:16]
    _TICKETS[tk] = {"who": "world://user/" + user, "user": user,
                    "issued_at": now, "expires_at": now + TICKET_TTL,
                    "scope": ["space:" + user]}
    log("★ 认过 ⇒ 发票 %s（给 %s）" % (tk, user))
    return True, {"ticket": tk, "who": "world://user/" + user, "user": user,
                  "expires_at": _TICKETS[tk]["expires_at"], "scope": _TICKETS[tk]["scope"]}


def session(params, log=print):
    """★ 查票：这张票是谁、什么时候过期。"""
    tk = params.get("ticket") or ""
    t = _TICKETS.get(tk)
    if not t:
        return False, {"why": "没有这张票"}
    if t["expires_at"] < time.time():
        _TICKETS.pop(tk, None)
        return False, {"why": "票过期了"}
    return True, {"who": t["who"], "user": t["user"],
                  "expires_at": t["expires_at"], "scope": t["scope"]}


def revoke(params, log=print):
    """★ 销票（退出）。"""
    _TICKETS.pop(params.get("ticket") or "", None)
    return True, {"revoked": True}


def check(params):
    """★★ 验票 —— 别人（空间／呈现）要【替某人做事】时，拿票来。
    ★ 返回 (ticket_dict, why)；成功时 why 为 None。"""
    tk = (params or {}).get("ticket") or ""
    t = _TICKETS.get(tk)
    if not t:
        return None, "没有票／票不存在（★ 先 identity.authenticate）"
    if t["expires_at"] < time.time():
        _TICKETS.pop(tk, None)
        return None, "票过期了"
    return t, None


def dispatch(name, params, log=print):
    """★ 按动作名分派。"""
    fn = {"identity.authenticate": authenticate,
          "identity.session": session,
          "identity.revoke": revoke}.get(name)
    if fn is None:
        return False, {"why": "不认识的认证动作 " + name}
    return fn(params or {}, log=log)
