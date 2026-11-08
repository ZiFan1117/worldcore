# -*- coding: utf-8 -*-
"""★ 世界薄网关的【协议翻译层】—— JSON-RPC 2.0 信封 ⇄ 世界总线消息（纯函数，好测）。

★ 它只干三件：
  ① 把 JSON-RPC 请求拆成 (method, params, id)；
  ② 把 params **原样**装进总线消息（只加一个关联号 `id`），定出该发哪个话题、该等哪个回话；
  ③ 把总线回话**原样**装回 JSON-RPC：成功进 `result`；带码的拒绝进 `error.data`，
     码与类别一字不改（码取自回话，类别照本体闭集表抄）。

★ 它【不】干的事（口径「只翻译，不治理」）：
  ✗ 不校验动作名／参数／许可／凭证；✗ 不自己记账；✗ 不自造拒绝码。
  ⇒ 本文件里**没有任何世界拒绝码的字面量**；`world_code` 一律来自回话。
  ⇒ 字段一个不改：`actor` 缺就是缺（不替调用方造身份），由本体拒。
"""
import json

# ── JSON-RPC 保留码（-32768..-32000）只用于【协议层】；世界拒绝码不许占这里 ──
RESERVED = range(-32768, -31999)        # 含两端 -32768 与 -32000
CODE_PARSE = -32700                     # 请求体不是 JSON
CODE_INVALID_REQUEST = -32600           # 不是 JSON-RPC 2.0 请求
CODE_METHOD_NOT_FOUND = -32601          # 没有这个方法
# ── 应用层码（★ 都不在保留区间）：只表示【传输怎样】，不表示世界拒了什么 ──
CODE_WORLD_REJECT = 1201                # 本体拒了（真码在 data.world_code）
CODE_BUS_TIMEOUT = 1202                 # 总线没有回话
CODE_BUS_ERROR = 1203                   # 总线／会话出错

# ★ 方法 ⇒ (发的话题, 等的话题)。只有两条路：问世界、请世界做事。
METHODS = {
    "world.query": ("world/query", "world/query/result"),
    "world.ask": ("world/ask", "world/ask/result"),
}
PUT_TOPICS = tuple(sorted({v[0] for v in METHODS.values()}))   # ★ 网关只会发这两个话题


def error(req_id, code, message, data=None):
    """JSON-RPC 2.0 错误响应。"""
    body = {"code": int(code), "message": str(message)}
    if data is not None:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": body}


def success(req_id, result):
    """JSON-RPC 2.0 成功响应。"""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def parse_request(raw):
    """→ (req, err)。

    req = {"id", "method", "params", "notification"}；err = 一份协议层错误响应（此时 req 为 None）。
    ★ 只判「像不像 JSON-RPC 2.0 请求」；**不判世界的任何东西**。
    """
    try:
        obj = json.loads(raw)
    except Exception:
        return None, error(None, CODE_PARSE, "请求不是 JSON")
    if isinstance(obj, list):
        return None, error(None, CODE_INVALID_REQUEST, "不支持批量请求（一条一条发）")
    if not isinstance(obj, dict):
        return None, error(None, CODE_INVALID_REQUEST, "请求不是对象")
    if obj.get("jsonrpc") != "2.0":
        return None, error(obj.get("id"), CODE_INVALID_REQUEST, "不是 JSON-RPC 2.0 请求")
    method = obj.get("method")
    if not isinstance(method, str) or not method:
        return None, error(obj.get("id"), CODE_INVALID_REQUEST, "没有 method")
    if method not in METHODS:
        return None, error(obj.get("id"), CODE_METHOD_NOT_FOUND,
                           "不认识的 method：%s（只有 world.query／world.ask）" % method)
    params = obj.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return None, error(obj.get("id"), CODE_INVALID_REQUEST, "params 必须是对象")
    return {"id": obj.get("id"), "method": method, "params": params,
            "notification": "id" not in obj}, None


def to_bus_message(method, params, rid):
    """→ (发的话题, 等的话题, 总线消息)。

    ★ 消息 = params 原样 ＋ 关联号 `id`；`action`／`actor`／`ticket` 等字段一个不改、一个不补。
    """
    put_topic, res_topic = METHODS[method]
    msg = dict(params)
    msg["id"] = rid
    return put_topic, res_topic, msg


def _reject_data(reply, category_of):
    """本体拒绝 ⇒ error.data：真码原样；类别照本体闭集表抄，码不认识就【不写】类别（不猜）。"""
    code = reply.get("code")
    data = {"reply": reply}
    if code:
        data["world_code"] = code
        cat = category_of(code) if category_of else None
        if cat:
            data["category"] = cat
    return data


def to_response(method, req_id, reply, category_of=None):
    """总线回话 ⇒ JSON-RPC 响应。

    · `world.ask` 被本体拒（ok=false）⇒ error，真码进 `data.world_code`，类别进 `data.category`；
    · `world.query` 回话原样进 `result`（查世界没有「拒绝码」这一说，ok=false 也是一个答案）；
    · 没回话（超时）⇒ 传输错误，**不带 world_code**（不替世界说话）。
    """
    if reply is None:
        return error(req_id, CODE_BUS_TIMEOUT, "总线没有回话（超时）", {"transport": "timeout"})
    if method == "world.query":
        return success(req_id, reply)
    if reply.get("ok") is True:
        return success(req_id, reply)
    return error(req_id, CODE_WORLD_REJECT, reply.get("why") or "本体拒绝（没有给出 why）",
                 _reject_data(reply, category_of))
