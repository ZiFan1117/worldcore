# -*- coding: utf-8 -*-
"""★ DSH Web 对话（从 agent_llm 拆出，C27 一文件一块）。"""
import datetime
import json
import urllib.request


def ask_chat(system, history, url, key, model, max_tokens=1400):
    if not key:
        return None, "没有 AIOS_LLM_KEY"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}] + list(history),
        "temperature": 0.6,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:200])


def chat_reply(agent, message, ask_fn):
    message = str(message or "").strip()
    agent.chat_log.append({"role": "user", "content": message})
    agent.chat_log = agent.chat_log[-30:]
    sys = ("你是 DSH（DeepSeek Harness），worldcore 世界里的智能体。"
           "用中文回答，简洁、诚实；不确定就说不知道。"
           "你的动作都要经过本体，不能假装已经执行。")
    if agent.guide:
        sys += "\\n当前人的引导：" + agent.guide
    reply, err = ask_fn(sys, agent.chat_log[-16:])
    if err:
        reply = "（DSH 暂时没回上来：%s）" % err
    agent.chat_log.append({"role": "assistant", "content": reply})
    agent.chat_log = agent.chat_log[-30:]
    agent._write_heartbeat({"phase": "chat", "chat_turns": len(agent.chat_log) // 2})
    return {"reply": reply, "at": datetime.datetime.now().astimezone()
            .isoformat(timespec="seconds"), "turns": len(agent.chat_log) // 2}
