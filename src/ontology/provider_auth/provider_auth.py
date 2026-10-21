# -*- coding: utf-8 -*-
"""★ provider 消息签名（独立文件夹：`src/ontology/provider_auth/`）。

作者 2026-10-21：appear 签名/ACL「加入本体，但是要单独文件夹」。
这里放**机制**，不放语义：
  · provider → 本体：`world/appear` / `world/register` / `world/exec/result` 带 `_auth` 信封；
  · 本体 → 验签：key 按 provider kind 取（`/usr/lib/aios/provider-keys/<kind>.key`）；
  · key 不进 `world.json`（法里只留“谁能报什么”的规则）。
"""
import hashlib
import hmac
import json
import os
import time
import uuid

SIGNED_TOPICS = ("world/appear", "world/register", "world/exec/result")
DEFAULT_KEY_DIR = "/usr/lib/aios/provider-keys"
REPLAY_WINDOW = 600          # 秒；nonce 去重窗口
_SEEN = {}                   # 全局 nonce 去重（本体单进程）


class ProviderAuthError(Exception):
    def __init__(self, code, why):
        super().__init__(why)
        self.code = code
        self.why = why


def auth_enabled():
    """★ 默认开（fail closed）；宿主临时测试显式 AIOS_PROVIDER_AUTH=off 才关。"""
    return (os.environ.get("AIOS_PROVIDER_AUTH") or "on").lower() != "off"


def key_dir():
    return os.environ.get("AIOS_PROVIDER_KEY_DIR") or DEFAULT_KEY_DIR


def key_path(kind):
    return os.path.join(key_dir(), "%s.key" % kind)


def load_key(kind):
    p = key_path(kind)
    try:
        with open(p, "rb") as f:
            key = f.read().strip()
    except OSError as e:
        raise ProviderAuthError("UNKNOWN_KEY", "provider key 读不到（%s）：%s" % (kind, e))
    if not key:
        raise ProviderAuthError("UNKNOWN_KEY", "provider key 为空：%s" % kind)
    return key


def _canonical(topic, payload):
    body = {k: v for k, v in payload.items() if k != "_auth"}
    raw = json.dumps({"topic": topic, "payload": body}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":"))
    return raw.encode("utf-8")


def kind_of(payload):
    """从消息本身推断 provider kind（兼容 appear/register/result 三种形状）。"""
    rep = payload.get("reporter") or ""
    if rep.startswith("world://"):
        parts = rep[len("world://"):].split("/")
        if parts and parts[0]:
            return parts[0]
    rb = payload.get("registered_by_kind") or ""
    if rb:
        return rb
    for k in ("registered_by", "by"):
        v = payload.get(k) or ""
        if "/" in v:
            return v.split("/", 1)[0]
        if v:
            return v
    env = os.environ.get("AIOS_PROVIDER_KIND") or ""
    if env:
        return env
    raise ProviderAuthError("UNKNOWN_KEY", "推断不出 provider kind（缺 reporter/registered_by/by）")


def _kind_matches(kind, payload):
    """★ 签名 kind 必须与消息里的自称一致；防“clock 的 key 冒充 vault”。"""
    rep = payload.get("reporter") or ""
    if rep.startswith("world://"):
        got = rep[len("world://"):].split("/")[0]
        if got != kind:
            raise ProviderAuthError("REPORTER_KEY_MISMATCH",
                                    "reporter=%r 与签名 kind=%r 不符" % (rep, kind))
    rb = payload.get("registered_by_kind") or ""
    if rb and rb != kind:
        raise ProviderAuthError("REPORTER_KEY_MISMATCH",
                                "registered_by_kind=%r 与签名 kind=%r 不符" % (rb, kind))
    for k in ("registered_by", "by"):
        v = payload.get(k) or ""
        if v and v.split("/", 1)[0] != kind:
            raise ProviderAuthError("REPORTER_KEY_MISMATCH",
                                    "%s=%r 与签名 kind=%r 不符" % (k, v, kind))


def sign_message(topic, payload, kind=None):
    """返回带 `_auth` 的新 dict；payload 不改。"""
    out = {k: v for k, v in payload.items() if k != "_auth"}
    kind = kind or kind_of(out)
    key = load_key(kind)
    auth = {"kind": kind, "key_id": kind, "nonce": uuid.uuid4().hex,
            "ts": round(time.time(), 3)}
    raw = _canonical(topic, out) + b"|" + json.dumps(auth, sort_keys=True,
                                                     separators=(",", ":")).encode()
    auth["sig"] = hmac.new(key, raw, hashlib.sha256).hexdigest()
    out["_auth"] = auth
    return out


def verify_message(topic, payload, seen=None, now=None):
    """验签；返回 kind。seen 是 {nonce: ts} 的 dict，用于防重放。"""
    if seen is None:
        seen = _SEEN
    auth = payload.get("_auth")
    if not isinstance(auth, dict):
        raise ProviderAuthError("BAD_SIGNATURE", "缺 _auth 签名信封")
    kind = str(auth.get("kind") or "")
    if not kind or auth.get("key_id") != kind:
        raise ProviderAuthError("UNKNOWN_KEY", "签名 kind/key_id 不合法")
    key = load_key(kind)
    body = {k: v for k, v in payload.items() if k != "_auth"}
    _kind_matches(kind, body)
    check = dict(auth)
    sig = str(check.pop("sig", ""))
    raw = _canonical(topic, body) + b"|" + json.dumps(check, sort_keys=True,
                                                      separators=(",", ":")).encode()
    want = hmac.new(key, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, want):
        raise ProviderAuthError("BAD_SIGNATURE", "签名不符")
    try:
        ts = float(auth.get("ts"))
    except (TypeError, ValueError):
        raise ProviderAuthError("BAD_SIGNATURE", "ts 不合法")
    now = time.time() if now is None else float(now)
    if abs(now - ts) > REPLAY_WINDOW:
        raise ProviderAuthError("REPLAY", "ts 超出窗口（%r vs %r）" % (ts, now))
    nonce = str(auth.get("nonce") or "")
    if not nonce:
        raise ProviderAuthError("REPLAY", "缺 nonce")
    if seen is not None:
        old = [n for n, t in seen.items() if now - float(t) <= REPLAY_WINDOW]
        for n in list(seen):
            if n not in old:
                seen.pop(n, None)
        if nonce in seen:
            raise ProviderAuthError("REPLAY", "nonce 重复：%s" % nonce)
        seen[nonce] = ts
    return kind


class SignedSession:
    """★ 包住 zenoh session：对 SIGNED_TOPICS 自动签名，其余透传。"""

    def __init__(self, inner):
        self._inner = inner

    def put(self, topic, payload, *args, **kwargs):
        if topic in SIGNED_TOPICS:
            try:
                obj = json.loads(payload) if isinstance(payload, (str, bytes)) else dict(payload)
            except (TypeError, ValueError):
                return self._inner.put(topic, payload, *args, **kwargs)
            obj = sign_message(topic, obj)
            payload = json.dumps(obj, ensure_ascii=False)
        return self._inner.put(topic, payload, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def close(self):
        return self._inner.close()


def open_signed_session(conf):
    import zenoh
    try:
        from bus_auth import configure as _bus_configure
        conf = _bus_configure(conf)
    except Exception:                                      # noqa: BLE001
        pass
    return SignedSession(zenoh.open(conf))
