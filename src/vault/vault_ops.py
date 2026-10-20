# -*- coding: utf-8 -*-
"""★ 保险库（只读元数据）纯函数（借鉴 AI-OS L4 Policy/Identity/Vault 三分家）。

★ 读什么：`/var/lib/aios/vault/index.json`（秘密【库存】，只有 id/提供方/拥有者/轮换时间/状态/说明）。
★ 绝不读什么：秘密值本身（不打开任何秘密值文件）；值也不返回。
"""
import datetime
import json
import os

DEFAULT_INDEX = "/var/lib/aios/vault/index.json"
NAME = os.environ.get("AIOS_VAULT_NAME") or "vault0"
ALLOWED_FIELDS = ("provider", "owner", "rotated_at", "state", "description")
STATES = ("active", "rotated", "revoked")


def index_path():
    return os.environ.get("AIOS_VAULT_INDEX") or DEFAULT_INDEX


def _load():
    path = index_path()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return [], {"index": path, "missing": True}
    except (OSError, ValueError) as e:
        return [], {"index": path, "error": str(e)[:200]}
    items = raw if isinstance(raw, list) else (raw.get("secrets") if isinstance(raw, dict) else [])
    if not isinstance(items, list):
        items = []
    return items, {"index": path}


def _clean(it):
    if not isinstance(it, dict):
        return None
    name = str(it.get("id") or it.get("name") or "").strip()
    if not name:
        return None
    state = str(it.get("state") or "active")
    if state not in STATES:
        state = "active"
    d = {"name": name, "state": state}
    for k in ALLOWED_FIELDS:
        if k == "state":
            continue
        if it.get(k) is not None:
            d[k] = str(it.get(k))[:200]
    return d


def list_secrets(limit=50):
    items, info = _load()
    try:
        lim = max(1, min(int(limit or 50), 200))
    except (TypeError, ValueError):
        lim = 50
    out, bad = [], 0
    for it in items:
        c = _clean(it)
        if c is None:
            bad += 1
            continue
        out.append(c)
        if len(out) >= lim:
            break
    return True, {**info, "count": len(out), "bad": bad, "secrets": out}


def state():
    ok, d = list_secrets(200)
    active = sum(1 for s in (d.get("secrets") or []) if s.get("state") == "active")
    return True, {"name": NAME, "state": "running", "secrets": d.get("count", 0),
                  "active": active,
                  "checked_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}


def dispatch(action, params=None):
    if action == "vault.list":
        return list_secrets((params or {}).get("limit"))
    if action == "vault.state":
        return state()
    return False, "不认识的动作：%s" % action
