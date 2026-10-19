# -*- coding: utf-8 -*-
"""★ 审批凭据（Permit）—— 本体发的、**动作级**、**绑参数**、**有期限**、**一号一用**。

★ 作者口径：
  · 「**本体是唯一发许可处**」；「**执行器是只执行**」；
  · 「审批……要推送给界面，然后让人来点授权」（人确认那一步仍是**待人裁**的占位，见 README）。
★ 评审席乙给的属性（逐字整理）：「必须绑『动作＋参数』（否则可挪用）」「凭证号必须进正文」「有效期与撤销」。

★★ 为什么要有它（现取出来的洞）：
  总线（zenoh）**不认证发送者** —— 任何进程都能直接往 `world/exec` put 一条指令，
  「所有交互都过本体」就只是**约定**，不是**事实**。⇒ **执行器收指令前先验一张凭证**：
  · 本体用【共享密钥】对（动作 ＋ 参数指纹 ＋ actor ＋ 期限 ＋ 凭证号）签名；
  · 执行器（计算机／呈现／个人空间）用同一把密钥 **验签 ＋ 验期限 ＋ 验动作/参数 ＋ 记账防重放**；
  · 验不过 ⇒ **拒**（fail closed）：绕开本体的那条路就走不通了。

★ 密钥住哪：`AIOS_PERMIT_KEY`（环境变量，十六进制/任意字节）或 `/usr/lib/aios/permit.key`
  （`deploy.sh` 生成，`chmod 600`；所有单元都以 root 起，故两边都读得到）。
  ★ 没有密钥 ⇒ 发行失败（本体）／**一律拒**（执行器）—— 不降级成「没钥匙就放行」。

★ 限度（如实）：这挡的是【总线上的冒充与重放】；**挡不住已经拿到 root 的人** ——
  那一层归 OS（polkit／LSM），不在本件射程。
"""
import hashlib
import hmac
import json
import os
import time
import uuid

KEY_PATH = os.environ.get("AIOS_PERMIT_FILE", "/usr/lib/aios/permit.key")
TTL_DEFAULT = int(os.environ.get("AIOS_PERMIT_TTL") or 60)
_SEEN = set()   # ★ 一号一用（本执行器进程内记；重启会忘 —— 如实记在 README）


def log(*a):
    print("[许可]", *a, flush=True)


def _load_key():
    """★ 共享密钥：环境变量优先，其次密钥文件；都没有 ⇒ 空（调用方按验不过处理）。"""
    env = os.environ.get("AIOS_PERMIT_KEY")
    if env:
        return str(env).encode("utf-8")
    try:
        with open(KEY_PATH, "rb") as f:
            return f.read().strip()
    except OSError:
        return b""


def fingerprint(action, params):
    """★ 参数指纹：动作名 ＋ 参数（键序归一）的 sha256 —— 挪作他用就对不上。"""
    blob = json.dumps({"action": action, "params": params or {}}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _sign(key, pid, action, fp, actor, exp):
    msg = "|".join([pid, action, fp, actor or "", str(exp)]).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def issue(action, params=None, actor=None, ttl=None):
    """★ 本体发行一张凭证；没有密钥 ⇒ 返回 None（调用方必须按「发不出」处理，不许裸转发）。"""
    key = _load_key()
    if not key:
        log("★★ 没有许可密钥（%s）⇒ 发不出凭证（fail closed）" % KEY_PATH)
        return None
    pid = "pm-" + uuid.uuid4().hex[:16]
    exp = int(time.time()) + (TTL_DEFAULT if ttl is None else ttl)
    fp = fingerprint(action, params or {})
    return {"id": pid, "action": action, "fp": fp, "actor": actor or "",
            "at": int(time.time()), "exp": exp, "sig": _sign(key, pid, action, fp, actor, exp)}


def verify(permit, action, params=None):
    """★ 执行器验凭证：签名／动作／参数指纹／期限。返回 (True, None) 或 (False, 为什么)。"""
    key = _load_key()
    if not key:
        return False, "执行器没有许可密钥（%s）" % KEY_PATH
    if not isinstance(permit, dict) or not permit.get("id"):
        return False, "没有凭证（★ 这条指令不是本体转来的）"
    for k in ("id", "action", "fp", "exp", "sig"):
        if k not in permit:
            return False, "凭证缺 %s" % k
    if permit.get("action") != action:
        return False, "凭证是给动作 %r 的，不是 %r" % (permit.get("action"), action)
    if permit.get("fp") != fingerprint(action, params or {}):
        return False, "参数指纹不对（★ 凭证绑动作＋参数，不许挪用）"
    try:
        exp = int(permit.get("exp"))
    except (TypeError, ValueError):
        return False, "凭证的期限不是整数"
    if exp < int(time.time()):
        return False, "凭证过期了"
    want = _sign(key, permit["id"], permit["action"], permit["fp"], permit.get("actor"), exp)
    if not hmac.compare_digest(str(permit.get("sig")), want):
        return False, "凭证签名不对（★ 不是本体发的）"
    return True, None


def verify_and_consume(permit, action, params=None):
    """★ 验完就记账（一号一用）：同一张凭证重放 ⇒ 拒。"""
    ok, why = verify(permit, action, params)
    if not ok:
        return False, why
    pid = permit["id"]
    if pid in _SEEN:
        return False, "这张凭证已经用过（一号一用）：%s" % pid
    _SEEN.add(pid)
    return True, None


if __name__ == "__main__":
    # ★ 自检现取（不需要总线）：签发 → 验过 → 参数一改就不过 → 重放不过
    p = issue("demo.action", {"x": 1}, actor="world://user/demo", ttl=30)
    print("issue:", bool(p))
    print("verify ok:", verify(p, "demo.action", {"x": 1}))
    print("params 改了:", verify(p, "demo.action", {"x": 2}))
    print("一次:", verify_and_consume(p, "demo.action", {"x": 1}))
    print("重放:", verify_and_consume(p, "demo.action", {"x": 1}))
