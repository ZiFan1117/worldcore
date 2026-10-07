#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUI 侧（最小）：**世界说什么，就画什么** —— 它不认识"第几步""下一步是什么"。

## 它凭什么不认识业务

它只做三件事（作者定的：**"不是 GUI 自动渲染出下一步"**）：
1. **读**：从账本里取**最新一条** `notice(type=case.step)` 的 `payload`（那才是"下一步"）；
2. **画**：把 `payload` 里的 `step`／`label`／`actions` 印出来（终端读法）；
3. **点的传回世界**：把点中的那个 `action` 里的 **`capability`／`verb`／`params`** 原样装进一条 `act`，
   经**唯一写入口**发出去 —— ★**连"该调哪个能力"都是读来的**，不是写死在 GUI 里。

## ★"换一套案例、GUI 一个字不改"怎么算成立（判据 G1）

**读数**：拿**另一份 `--case` 文件**（步数不同、label 不同、action 的 capability 不同）跑同一个 GUI ⇒
它照样把每一步画出来 ⇒ ★成立；★若它画不出（或需要改这个文件）⇒ **决定权做进 GUI 了，不合格**。

## 三条不许破

- **壳不持状态**：每次现读（`render` 每次都重新读账本；`click` 之后**重新读**，不看本地计数）；
- **不许乐观更新**：`click` 只发请求，**画什么等世界回了再说**；
- **唯一写入口**：只走 AF_UNIX 那一个套接字。
"""

import argparse
import io
import json
import os
import socket
import sys
import time

STEP_TYPE = "case.step"
DONE_TYPE = "case.finished"


def read_events(ledger):
    out = []
    with io.open(ledger, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def latest_case_event(events):
    """取**最新一条**案例通告（`case.step` 或 `case.finished`）——世界说的那一步。"""
    for ev in reversed(events):
        if ev.get("kind") == "notice" and ev.get("body", {}).get("type") in (STEP_TYPE, DONE_TYPE):
            return ev
    return None


def render(ledger):
    ev = latest_case_event(read_events(ledger))
    if ev is None:
        # ★ 读不到就说读不到（不许回退旧值、不许猜一个默认步）
        print("STEP=none")
        print("NOTE=世界里还没有案例通告（没人发 case）")
        return 0
    b = ev["body"]
    p = b.get("payload") or {}
    print("NOTICE_SEQ=%s" % ev.get("seq"))
    print("NOTICE_TYPE=%s" % b.get("type"))
    print("SUBJECT=%s" % b.get("subject"))
    print("STEP=%s" % p.get("step", "?"))
    print("LABEL=%s" % p.get("label", ""))
    acts = p.get("actions") or []
    print("ACTIONS=%s" % ",".join("%s:%s" % (a.get("id"), a.get("label")) for a in acts))
    for a in acts:
        print("ACTION_%s_CAPABILITY=%s" % (a.get("id"), a.get("capability")))
        print("ACTION_%s_VERB=%s" % (a.get("id"), a.get("verb")))
    return 0


def step_of(ledger):
    ev = latest_case_event(read_events(ledger))
    if ev is None:
        return None, None
    b = ev["body"]
    return b.get("type"), (b.get("payload") or {}).get("step")


def send_line(sock_path, line, timeout=8.0):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(sock_path)
        s.sendall((line + "\n").encode("utf-8"))
        buf = b""
        while not buf.endswith(b"\n"):
            ch = s.recv(65536)
            if not ch:
                break
            buf += ch
    finally:
        s.close()
    return buf.decode("utf-8", "replace").strip()


def click(a):
    before_type, before_step = step_of(a.ledger)
    print("STEP_BEFORE=%s" % before_step)
    ev = latest_case_event(read_events(a.ledger))
    if ev is None:
        print("STATUS=RED")
        print("REASON=世界里没有案例通告 ⇒ 没有可点项（不确定要发什么）")
        return 1
    acts = (ev["body"].get("payload") or {}).get("actions") or []
    hit = [x for x in acts if x.get("id") == a.action]
    if not hit:
        print("STATUS=RED")
        print("REASON=世界说的可点项里没有 `%s`（可点项由世界给，不由界面编）" % a.action)
        return 1
    spec = hit[0]
    # ★ 发什么，全从世界里读来（含 capability／verb／params）
    body = {
        "capability": spec.get("capability"),
        "verb": spec.get("verb", "set"),
        "request_id": "click-%d" % int(time.time() * 1000),
    }
    if spec.get("params") is not None:
        body["params"] = spec["params"]
    req = json.dumps({"kind": "act", "body": body}, ensure_ascii=False, sort_keys=True)
    print("REQUEST=%s" % req)
    try:
        reply = send_line(a.socket, req)
    except Exception as e:
        print("REPLY_SEND_FAILED=%s" % e)
        print("STATUS=RED")
        print("REASON=连不上唯一写入口——点一下没进世界")
        return 2
    print("REPLY=%s" % reply)
    # ★ 不许乐观更新：画什么**等世界回了再说**（这里再读一次账本）
    for _ in range(a.wait_tries):
        after_type, after_step = step_of(a.ledger)
        if after_type == DONE_TYPE or after_step != before_step:
            break
        time.sleep(a.wait_interval)
    print("STEP_AFTER=%s" % after_step)
    print("AFTER_TYPE=%s" % after_type)
    if '"ok":true' not in reply.replace(" ", ""):
        print("STATUS=RED")
        print("REASON=世界拒绝了这一句")
        return 1
    if after_type == DONE_TYPE:
        print("STATUS=GREEN")
        print("REASON=点一下 ⇒ 世界说这一步走完了（case.finished）")
        return 0
    if after_step == before_step:
        print("STATUS=RED")
        print("REASON=点了但世界说的步没变（%s ⇒ %s）——下一步必须由世界给" % (before_step, after_step))
        return 1
    print("STATUS=GREEN")
    print("REASON=点一下 ⇒ 世界落进下一步（%s ⇒ %s）" % (before_step, after_step))
    return 0


def self_test():
    """形状自检（不连世界）：正控 ＋ 反例，全部对着**合成账本**。"""
    import tempfile
    rc = 0
    d = tempfile.mkdtemp(prefix="case-shell-")
    led = os.path.join(d, "ledger.jsonl")

    def w(events):
        io.open(led, "w", encoding="utf-8").write(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n")

    # 正控 A：有一条第 1 步的 case.step ⇒ 必须画得出
    w([{"kind": "notice", "seq": 1, "body": {"type": STEP_TYPE, "subject": "world://notice/case1",
       "payload": {"step": 1, "label": "开始", "actions": [
           {"id": "next", "label": "下一步", "capability": "job.start", "verb": "set"}]}}}])
    ev = latest_case_event(read_events(led))
    ok_a = ev is not None and (ev["body"]["payload"] or {}).get("step") == 1
    print("  [%s] 正控 A · 有 case.step ⇒ 取得到那一步" % ("ok  " if ok_a else "FAIL"))
    rc |= 0 if ok_a else 1

    # 正控 B：**换一套案例**（步号与 label 都不同、action 的 capability 也不同）⇒ 同一个函数照样取得到
    w([{"kind": "notice", "seq": 9, "body": {"type": STEP_TYPE, "subject": "world://notice/case2",
       "payload": {"step": 7, "label": "第七步·审阅", "actions": [
           {"id": "ok", "label": "通过", "capability": "notice.unmute", "verb": "set"}]}}}])
    t, s = step_of(led)
    ok_b = (t == STEP_TYPE and s == 7)
    print("  [%s] 正控 B · 换一套案例（步号 7／label 不同／capability 不同）⇒ 同一函数取得到" % ("ok  " if ok_b else "FAIL"))
    rc |= 0 if ok_b else 1

    # 反例 C：账本里**没有**案例通告 ⇒ 必须说"读不到"（STEP=none），不许猜一个默认步
    w([{"kind": "change", "seq": 1, "body": {"subject": "world://notice/x", "path": "muted",
       "before": False, "after": True}}])
    ok_c = latest_case_event(read_events(led)) is None
    print("  [%s] 反例 C · 没有案例通告 ⇒ 判「读不到」（不猜默认步）" % ("ok  " if ok_c else "FAIL"))
    rc |= 0 if ok_c else 1

    # 反例 D：最新一条是【最后一拍】⇒ 取到的是 finished，不是前一步
    w([{"kind": "notice", "seq": 1, "body": {"type": STEP_TYPE, "subject": "s",
       "payload": {"step": 1, "label": "开始", "actions": []}}},
       {"kind": "notice", "seq": 2, "body": {"type": DONE_TYPE, "subject": "s", "payload": {"steps": 1}}}])
    t2, _ = step_of(led)
    ok_d = (t2 == DONE_TYPE)
    print("  [%s] 反例 D · 最新一条是 finished ⇒ 取到 finished（不取前一步当现在）" % ("ok  " if ok_d else "FAIL"))
    rc |= 0 if ok_d else 1

    import shutil
    shutil.rmtree(d, ignore_errors=True)
    print("  ---- 自测结论：%s ----" % ("全通过" if rc == 0 else "有红"))
    return rc


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--ledger", default="/var/lib/world-core/ledger.jsonl")
    ap.add_argument("--socket", default="/run/world-core/world.sock")
    ap.add_argument("--wait-tries", type=int, default=20)
    ap.add_argument("--wait-interval", type=float, default=0.25)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("cmd", nargs="?", default="render", choices=["render", "click"])
    ap.add_argument("action", nargs="?", default="")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.cmd == "render":
        return render(a.ledger)
    return click(a)


if __name__ == "__main__":
    sys.exit(main())
