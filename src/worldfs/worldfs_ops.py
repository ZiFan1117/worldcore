# -*- coding: utf-8 -*-
"""★ worldfs 动作层（纯函数；不连总线，好测）。

动作（法里登记）：
  读：worldfs.list / stat / read / versions / state
  写：worldfs.write / mkdir / remove / restore   ← change 动作，人确认后才会有 permit
"""
from worldfs_store import WorldFSError, WorldFS

READ_ACTIONS = ("worldfs.list", "worldfs.stat", "worldfs.read",
                "worldfs.versions", "worldfs.state")
WRITE_ACTIONS = ("worldfs.write", "worldfs.mkdir", "worldfs.remove", "worldfs.restore")
ALL_ACTIONS = READ_ACTIONS + WRITE_ACTIONS


def _need_intent(params):
    intent = (params or {}).get("intent")
    if not isinstance(intent, str) or not intent.strip():
        raise WorldFSError("缺 intent（写/删/回滚必须说明意图）")
    return intent


def dispatch(store, action, params=None):
    """★ 返回 (ok, body)。失败 body 是错误字符串。"""
    params = params if isinstance(params, dict) else {}
    try:
        if action == "worldfs.list":
            return True, store.list(params.get("path") or "/worldfs", params.get("limit"))
        if action == "worldfs.stat":
            return True, store.stat(params.get("path"))
        if action == "worldfs.read":
            return True, store.read(params.get("path"), params.get("max_bytes"))
        if action == "worldfs.versions":
            return True, store.versions(params.get("path"))
        if action == "worldfs.state":
            return True, store.state()
        if action == "worldfs.write":
            return True, store.write(params.get("path"), params.get("text"),
                                     actor=params.get("_actor") or "world://worldfs/unknown",
                                     intent=_need_intent(params),
                                     base_seq=params.get("base_seq"))
        if action == "worldfs.mkdir":
            return True, store.mkdir(params.get("path"),
                                     actor=params.get("_actor") or "world://worldfs/unknown",
                                     intent=_need_intent(params))
        if action == "worldfs.remove":
            return True, store.remove(params.get("path"),
                                      actor=params.get("_actor") or "world://worldfs/unknown",
                                      intent=_need_intent(params))
        if action == "worldfs.restore":
            return True, store.restore(params.get("path"), params.get("seq"),
                                       actor=params.get("_actor") or "world://worldfs/unknown",
                                       intent=_need_intent(params))
    except WorldFSError as e:
        return False, str(e)
    except Exception as e:                                      # noqa: BLE001
        return False, "执行异常：%s" % e
    return False, "不认识的动作：%s" % action


def make_store(root=None):
    return WorldFS(root)
