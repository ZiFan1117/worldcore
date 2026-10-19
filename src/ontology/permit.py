# -*- coding: utf-8 -*-
"""★ 审批凭据（Permit）—— 本体发的、**动作级**、**绑参数**、**有期限**、**一号一用**。

★ 作者口径：
  · 「**本体是唯一发许可处**」；「**执行器是只执行**」；
  · ★ 作者更正（2026-10-19 逐字整理）：「**这不是我们记账，是记本体的账呀……是在本体都自己记账呀。
    怎么和执行器有什么关系？**」⇒ **一号一用的账在本体**（落盘、重启不忘）；**执行器不记账**，
    它只做两件：① 本地验签名/期限/动作参数（挡伪造与挪用）；② 问本体「这张凭证用过没有」。
  · 「审批……要推送给界面，然后让人来点授权」（人确认那一步仍是**待人裁**的占位，见 README）。
★ 评审席乙给的属性（逐字整理）：「必须绑『动作＋参数』（否则可挪用）」「凭证号必须进正文」「有效期与撤销」。

★★ 为什么要有它（现取出来的洞）：
  总线（zenoh）**不认证发送者** —— 任何进程都能直接往 `world/exec` put 一条指令，
  「所有交互都过本体」就只是**约定**，不是**事实**。⇒ **执行器收指令前先验一张凭证**，验不过就拒。

★★ 分工（★ 作者更正的落法）：
  · **本体**：签发凭证；**记账**——每一张用过的凭证都进本体的账（`permits.jsonl` 落盘 ＋ 账本一行
    `kind_of=permit-use`）；对「这张能执行吗」作出裁决（`world/permit/consume` → `…/result`）。
  · **执行器**：本地验签名／期限／动作＋参数；然后**只用一句话问本体**；本体说行才执行。
    ★ 执行器**不保存任何账**（它重启不丢任何东西——账本来就不在它那儿）。

★ 密钥住哪：`AIOS_PERMIT_KEY`（环境变量）或 `/usr/lib/aios/permit.key`
  （`deploy.sh` 生成，`chmod 600`；所有单元都以 root 起，故两边都读得到）。
  ★ 没有密钥 ⇒ 发行失败（本体）／**一律拒**（执行器）—— 不降级成「没钥匙就放行」。

★ 限度（如实）：这挡的是【总线上的冒充与重放】；**挡不住已经拿到 root 的人** ——
  那一层归 OS（polkit／LSM），不在本件射程。
"""
import hashlib
import hmac
import json
import os
import threading
import time
import uuid

KEY_PATH = os.environ.get("AIOS_PERMIT_FILE", "/usr/lib/aios/permit.key")
TTL_DEFAULT = int(os.environ.get("AIOS_PERMIT_TTL") or 60)
T_CONSUME = "world/permit/consume"          # ★ 执行器问：这张凭证能执行吗
T_CONSUME_RESULT = "world/permit/consume/result"


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
    """★ 验凭证（**无状态**）：签名／动作／参数指纹／期限。返回 (True, None) 或 (False, 为什么)。"""
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


# ─────────────── 本体的账：一号一用（落盘；★ 执行器不碰） ───────────────

def ledger_path(world):
    """★ 本体记「用过哪些凭证」的那本账：跟本体账本同目录（可用 AIOS_PERMIT_LEDGER 改）。"""
    env = os.environ.get("AIOS_PERMIT_LEDGER")
    if env:
        return env
    base = os.path.dirname(getattr(getattr(world, "ledger", None), "name", "") or "")
    return os.path.join(base, "permits.jsonl")


def load_used(path):
    """★ 从盘上读回「已用过的凭证号」—— 本体重启不忘。"""
    used = {}
    if not os.path.exists(path):
        return used
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("permit"):
                used[r["permit"]] = r.get("at")
    return used


def consume(world, permit_id):
    """★ 一号一用 —— **本体的账**：第一次来 ⇒ 记账（落盘 ＋ 账本一行）；第二次 ⇒ 拒。"""
    if not permit_id:
        return False, "凭证没有号"
    used = getattr(world, "used_permits", None)
    if used is None:
        used = world.used_permits = {}
    if permit_id in used:
        return False, "这张凭证已经用过（一号一用）：%s" % permit_id
    at = world.stamp("act", kind_of="permit-use", permit=permit_id)
    path = ledger_path(world)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": at, "permit": permit_id}, ensure_ascii=False) + "\n")
        f.flush()
    used[permit_id] = at
    return True, None


def handle_consume(smp, world, session, log_fn=print):
    """★ 本体侧：回「这张凭证能执行吗」—— 验签（无状态）＋ 一号一用（本体的账）。"""
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    p = msg.get("permit") or {}
    ok, why = verify(p, msg.get("action") or "", msg.get("params") or {})
    if ok:
        ok, why = consume(world, p.get("id"))
    session.put(T_CONSUME_RESULT, json.dumps({"id": msg.get("id"), "ok": ok, "why": why},
                                             ensure_ascii=False))
    if not ok:
        log_fn("凭证拒 %s ⇒ %s" % (msg.get("action"), why))


# ─────────────── 执行器侧：只问一句话（★ 不记账） ───────────────

def consume_via_ontology(session, permit, action, params=None, timeout=3.0):
    """★ 执行器【不记账】：问本体「这张能执行吗」，本体说行才执行。

    ★ 这是作者更正后的分工：账是本体记的；执行器重启不丢账（账不在它那儿）。
    ★ 本体不回话（超时）⇒ 拒（fail closed）—— 不许「没人管就当行」。
    """
    rid = "pc-" + uuid.uuid4().hex[:12]
    box, ev = {}, threading.Event()

    def _on(smp):
        try:
            d = json.loads(smp.payload.to_string())
        except Exception:
            return
        if d.get("id") == rid:
            box.update(d)
            ev.set()

    sub = session.declare_subscriber(T_CONSUME_RESULT, _on)
    session.put(T_CONSUME, json.dumps({"id": rid, "permit": permit, "action": action,
                                       "params": params or {}}, ensure_ascii=False))
    ok_wait = ev.wait(timeout)
    try:
        sub.undeclare()
    except Exception:
        pass
    if not ok_wait:
        return False, "本体没回话（%.1fs 超时）⇒ 不执行（fail closed）" % timeout
    return bool(box.get("ok")), box.get("why")


if __name__ == "__main__":
    # ★ 自检现取（不需要总线）：签发 → 验过 → 参数一改就不过 → 换了动作不过
    p = issue("demo.action", {"x": 1}, actor="world://user/demo", ttl=30)
    print("issue:", bool(p))
    print("verify ok:", verify(p, "demo.action", {"x": 1}))
    print("params 改了:", verify(p, "demo.action", {"x": 2}))
    print("action 换了:", verify(p, "other.action", {"x": 1}))
