#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 验收：DSH 完整 Web 界面（/dsh + /cmd；对话全走本体）。"""
import json
import urllib.request


BASE = "http://127.0.0.1:8765"


def get(path, raw=False):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        b = r.read()
        return r.status, (b.decode("utf-8", "replace") if raw else json.loads(b))


def post(payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + "/cmd", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "why": "%s: %s" % (type(e).__name__, str(e)[:200])}


def main():
    out = {"checks": []}

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:200] if detail else ""))

    st, html = get("/dsh", raw=True)
    check("GET /dsh", st == 200 and "DeepSeek" in html and "<textarea" in html,
          "status=%s bytes=%d" % (st, len(html)))
    check("页面含对话/状态/引导", all(x in html for x in
          ("agent.chat", "agent.state", "agent.guide", 'fetch("/cmd"')))
    check("页面接世界事件", 'EventSource("/events")' in html)
    ping = post({"op": "ping"})
    check("web ping", bool(ping.get("ok")), ping.get("what"))
    login = post({"op": "login", "user": "zhang", "secret": "0"})
    check("web 登录", bool(login.get("ok")), str(login.get("why"))[:100])
    st1 = post({"op": "ask", "action": "agent.state", "params": {}})
    body = ((st1.get("result") or {}).get("body") or {}) if st1.get("ok") else {}
    check("agent.state 经 web", bool(st1.get("ok")) and bool(body.get("name")),
          "state=%r" % body.get("state"))
    chat = post({"op": "ask", "action": "agent.chat",
                 "params": {"message": "你好，用一句话介绍你自己。"}})
    rbody = ((chat.get("result") or {}).get("body") or {}) if chat.get("ok") else {}
    reply = rbody.get("reply") or ""
    check("agent.chat 经 web 有回复", bool(chat.get("ok")) and bool(reply),
          "reply=%r" % reply[:120])
    check("回复不是异常栈", "Traceback" not in reply,
          "len=%d" % len(reply))
    st2 = post({"op": "ask", "action": "agent.state", "params": {}})
    b2 = ((st2.get("result") or {}).get("body") or {}) if st2.get("ok") else {}
    check("对话后状态仍可读", bool(st2.get("ok")) and bool(b2.get("name")),
          "guide=%r" % str(b2.get("guide"))[:60])
    out["ok"] = all(c["ok"] for c in out["checks"])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
