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

import json
import os
import time
import uuid

# ★★ 票表 —— ★ 谁认过了、什么时候过期。★ 本体是【记】的那个，票记在这儿。
# ★ 2026-10-21：票落盘，本体重启不再把已登录的桌面/页面一脚踢下线。
_TICKETS = {}
_TICKETS_PATH = os.environ.get("AIOS_TICKETS", "/var/lib/aios/ontology/tickets.json")


def _load_tickets():
    try:
        with open(_TICKETS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        now = time.time()
        for tk, t in (raw or {}).items():
            if isinstance(t, dict) and (t.get("expires_at") or 0) > now:
                _TICKETS[tk] = t
    except Exception:
        pass


def _save_tickets():
    try:
        os.makedirs(os.path.dirname(_TICKETS_PATH) or ".", exist_ok=True)
        tmp = _TICKETS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_TICKETS, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _TICKETS_PATH)
        try:
            os.chmod(_TICKETS_PATH, 0o600)
        except OSError:
            pass
    except Exception:
        pass


_load_tickets()

# ★ 测试账号（★ 作者令 2026-10-18：「先设定一个测试的用户名和密码吧，密码就是一个 0 就行」）
TEST_USER = "zhang"
TEST_PASS = "0"
# ★ 第二个测试账号 —— ★ 用来验【票的隔离】（甲拿票查不到乙的东西）
USERS = {"zhang": "0", "lisi": "0"}
# ★ 票的有效期。★ 默认 8 小时；★ 测试时用环境变量 AIOS_TICKET_TTL 设成 1 秒验「过期会拒」。
import os as _os
TICKET_TTL = int(_os.environ.get("AIOS_TICKET_TTL") or (8 * 3600))


def authenticate(params, log=print):
    """★ 认人：验凭据，通过则发票。★ 返回 (ok, body)。"""
    user = str(params.get("user") or "").strip()
    secret = params.get("secret")
    if user not in USERS or (secret is not None and str(secret) != USERS[user]):
        log("认被拒：user=%s" % user)
        return False, {"why": "身份凭据不对（★ 测试账号 %s ／ %s）" % (TEST_USER, TEST_PASS)}
    now = time.time()
    tk = "tk-" + uuid.uuid4().hex[:16]
    _TICKETS[tk] = {"who": "world://user/" + user, "user": user,
                    "issued_at": now, "expires_at": now + TICKET_TTL,
                    "scope": ["space:" + user]}
    _save_tickets()
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
        _save_tickets()
        return False, {"why": "票过期了"}
    return True, {"who": t["who"], "user": t["user"],
                  "expires_at": t["expires_at"], "scope": t["scope"]}


def revoke(params, log=print):
    """★ 销票（退出）。"""
    _TICKETS.pop(params.get("ticket") or "", None)
    _save_tickets()
    return True, {"revoked": True}


# ★★ 呈现／画布没有自己的进程 ⇒ 脸归提供者：`surface/x` 由 `presentation/x` 代报（四归属）。
_ALIAS = {"surface": "presentation"}


def actor_ok(actor, has_ticket, appeared):
    """★ 核验 actor：人 ⇒ 必须凭票；其他 ⇒ 必须【报过到、成为过个体】。

    ★ 作者令（逐字整理）：「一个进程可报多个个体，但每报一个都要能核验」。
    ★ 返回 (True, None, None) 或 (False, 为什么, 拒绝码)。
    """
    if not actor or not actor.startswith("world://"):
        return False, "身份格式不对（要 world://<类>/<名>）：%r" % (actor,), "IDENTITY_FORMAT_BAD"
    cls, _, name = actor[len("world://"):].partition("/")
    if cls == "user":
        if not has_ticket:
            return False, "人要有票（★ 每报一个都要能核验：人由登录进程报）", "HUMAN_NEEDS_TICKET"
        return True, None, None
    cls = _ALIAS.get(cls, cls)
    if "%s/%s" % (cls, name) not in appeared:
        return False, "这个身份没有报到过（★ 每报一个都要能核验）：%s" % actor, "IDENTITY_NOT_REPORTED"
    return True, None, None


def authority_ok(cls, reporter, appeared, reporters_map):
    """★ 状态所有权：这个类的事实只能由它的【提供者】报（借自订单样板的权威线）。

    ★ `reporters_map` ＝ 本体里每类的 `_authority.reporters`（world://<提供者>）。
    ★ 返回 (True, None, None) 或 (False, 为什么, 拒绝码)。
    ★ 限度（如实）：总线不认证发送者 ⇒「谁报的」今天仍是自报；这挡住**报错类**，挡不住**冒充**。
    """
    if not reporter or not reporter.startswith("world://"):
        return False, "报到要带 reporter（谁报的）：%r" % (reporter,), "IDENTITY_FORMAT_BAD"
    rcls, _, rname = reporter[len("world://"):].partition("/")
    allowed = list((reporters_map or {}).get(cls) or [])
    # ★ 允许表里是【actor 前缀】（如 world://space）——按前缀判，别按类名判
    if not any(reporter == a or reporter.startswith(a.rstrip("/") + "/") for a in allowed):
        return False, "「%s」类的事实不归 world://%s 报（允许：%s）" % (cls, rcls, allowed or "无"), "AUTHORITY_NOT_OWNER"
    if cls == rcls:
        return True, None, None                 # ★ 自报：进程报自己，不要求先出现过
    if "%s/%s" % (rcls, rname) not in appeared:
        return False, "报告者自己还没报到过：%s" % reporter, "IDENTITY_NOT_REPORTED"
    return True, None, None


def load_appeared(ontology, store):
    """★ 从【个体表】读回「谁报过到」——本体重启后不必等各进程重新报到。

    ★ 个体表是持久的（ObjectStore/SQLite），报到本来就不该只活在内存里。
    """
    out = {}
    for tid in ontology.object_types:
        for inst in store.search(tid):
            name = (inst.properties or {}).get("name") or inst.instance_id
            out["%s/%s" % (tid, name)] = True
    return out


def check(params):
    """★★ 验票 —— 别人（空间／呈现）要【替某人做事】时，拿票来。
    ★ 返回 (ticket_dict, why)；成功时 why 为 None。"""
    tk = (params or {}).get("ticket") or ""
    t = _TICKETS.get(tk)
    if not t:
        return None, "没有票／票不存在（★ 先 identity.authenticate）"
    if t["expires_at"] < time.time():
        _TICKETS.pop(tk, None)
        _save_tickets()
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
