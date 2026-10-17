# -*- coding: utf-8 -*-
"""AIOS 账房进程（Python）—— ★ 世界发生过的【人事记录】。

★ 作者话（逐字）：「**那在哪儿有这个完整的账呢？就是说来回的他们运行了什么怎么回事，
   这个账怎么能记下呢？怎么能形成这个账呢？是不是这个总线得时常要记录一些东西了**」

★★★ **⇒ 对。账房订阅【全部话题】（`**`），把每一次【调用】整理成一行账。**

★ 它和【本体】的分工（不能混）：
   · **本体**：★ 记【它自己判的事】—— 谁起来了、谁准了/拒了
   · **账房**：★ 记【所有进程之间发生了什么】—— 谁调谁、什么参数、什么时候

★ 它和【总线】的分工：
   · **总线**：★ 只是通道（发完就忘）
   · **账房**：★ ★ 站在通道旁边【抄一份】

★ 它【不做】的：不裁决、不转发，只记。
"""

import datetime
import json
import os
import time

import zenoh

LEDGER = os.environ.get("AIOS_WORLD_LEDGER", "/var/lib/aios/world/traffic.jsonl")
ZENOH_ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")

# ★ 哪些话题值得记 —— 只记【调用类】，不记心跳/探测（免得账被淹）
RECORD_PREFIXES = ("world/ask", "world/exec", "world/register", "world/appear", "world/ui/frame")
SKIP_PREFIXES = ("world/probe", "world/alive")


def log(*a):
    print("[账房]", *a, flush=True)


def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="microseconds")


def should_record(topic):
    if any(topic.startswith(p) for p in SKIP_PREFIXES):
        return False
    return any(topic.startswith(p) for p in RECORD_PREFIXES)


def main():
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    f = open(LEDGER, "a", encoding="utf-8")

    conf = zenoh.Config()
    # ★★★ 三条实测出来的（T-334/T-339）：peer 是孤岛、client 才跨进程通、关 multicast
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ZENOH_ENDPOINT]))
    session = zenoh.open(conf)
    log("连上总线 %s" % ZENOH_ENDPOINT)

    n = [0]

    def on_any(smp):
        topic = str(smp.key_expr)
        if not should_record(topic):
            return
        raw = smp.payload.to_string()
        row = {"at": now(), "topic": topic, "bytes": len(raw)}
        # ★ 能解析成 JSON 就把关键格提出来（谁/做什么/参数/票号）
        try:
            m = json.loads(raw)
            if isinstance(m, dict):
                for k in ("id", "action", "actor", "by", "class", "name",
                          "subject", "params", "route", "ok", "why", "trace"):
                    if k in m:
                        row[k] = m[k]
        except Exception:
            row["raw"] = raw[:300]
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        n[0] += 1
        if n[0] % 20 == 0:
            log("已记 %d 条" % n[0])

    session.declare_subscriber("**", on_any)
    log("订上了 ** 全通配 —— 站在总线旁边抄一份")
    log("账本：%s" % LEDGER)
    log("★ 账房起来了 —— 只记，不裁决、不转发")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        f.close()
        session.close()


if __name__ == "__main__":
    main()
