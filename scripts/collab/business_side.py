#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务侧（第 4 层）最小样板 —— **点一下 ⇒ 经唯一写入口对世界说一句 `act`**。

> ★**命名依据（作者 2026-10-05 更正，逐字）**：★「**业务侧不是业务册**」——
> ★"册" ＝ 记账的东西 ⇒ **账本只有一本，它在世界里**；若叫"业务册" ⇒ 听起来像**第二本账**，
> 而那正是本项目整晚在治的病（**同一件事两个载体**）。
> ⇒ 本文件原名 `business_book.py`，同日随件改名 `business_side.py`；**旧名作废不抹**。

## 它是什么

第 4 层的**最小业务侧**：一个"业务侧"程序，替一件业务动作说话。
它**不做**三件事（这三件事都不是第 4 层的）：不裁决（准不准做问世界的闸）、不落账
（写只经**唯一写入口**那个套接字）、不持状态（每次现读，不缓存上一次的数）。

## 它发什么、收什么

发**一行**（一行一帧，UTF-8，换行结尾）：
```json
{"kind":"act","body":{"capability":"notice.mute","verb":"set","request_id":"bb-<时刻>"}}
```
★**它是 `act` 不是 `change`**：`act` 是"我要求做这件事"（意图），`change` 是"某个字段由旧值变成新值"
（世界的话）。★业务侧**没有资格**替世界写 `change` —— 那要过 `policy.json` 的 `writes`，而第 4 层不该拿它。

收**一行**：`{"ok":true,"event":{…}}` 或 `{"ok":false,"error":"…"}`。
`ok:true` 里的 `event` 就是**世界里新落的那一条**（`seq` 在世界里由账本分配）。

## 它怎么证明"点一下真的进了世界"

★**不看应答，看账本**：点一下前后各现读一次账本，数 `"kind":"act"` 的行数。
**恰好多 1** ⇒ 通；**多 0**（没进去）或**多 2**（重发／走了两条路）⇒ **判据红（rc=1）**。
★外加两次现读投影首行（`last_seq`）：**世界侧的可观测变化**在这里（第 4 层不猜、不缓存）。

## 用法

```sh
# 点一下（对已经起来的世界说一句 act），并把"进没进世界"的读数打出来
python3 scripts/collab/business_side.py --socket /run/world-core/world.sock \
    --cli /usr/bin/world-core --ontology … --ledger … --policy … click
python3 scripts/collab/business_side.py --self-test        # 只验形状，不连世界
```
输出一律 **ASCII 的 `KEY=VALUE` 行**（免得读数被控制台编码搅坏），最后一行是 `STATUS=…`。
"""

import argparse
import io
import json
import os
import socket
import subprocess
import sys
import time

# ★★ 判据的标的物就在这一行：**点一下发的是 `act`**。
#    把它改成 `"change"` ⇒ 账本里不会多出 act ⇒ 下面那条判据（恰好多 1）当场红。
KIND = "act"
CAPABILITY = "notice.mute"
VERB = "set"


def build_request(request_id):
    """业务侧要说的那一句话（一行一帧）。"""
    return {
        "kind": KIND,
        "body": {
            "capability": CAPABILITY,
            "verb": VERB,
            "request_id": request_id,
        },
    }


def send_line(sock_path, line, timeout=8.0):
    """经**唯一写入口**交一句；一行请求 → 一行应答。"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(sock_path)
        s.sendall((line + "\n").encode("utf-8"))
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        s.close()
    return buf.decode("utf-8", "replace").strip()


def count_kind(ledger, kind):
    """现读账本：数某个家族有多少条。**权威载体是账本，不是应答。**"""
    n = 0
    total = 0
    needle = '"kind":"%s"' % kind
    try:
        with io.open(ledger, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                if needle in line:
                    n += 1
    except Exception as e:
        raise SystemExit("ext.world.BusinessBook.LedgerUnreadable: %s: %s" % (ledger, e))
    return n, total


def projection_header(cli, ontology, ledger, policy, which="visual"):
    """现读投影首行的位点（世界侧的可观测变化）。"""
    try:
        p = subprocess.run(
            [cli, "--ontology", ontology, "--ledger", ledger, "--policy", policy,
             "project", which],
            capture_output=True)
    except Exception as e:
        return None, "投影跑不动：%s" % e
    if p.returncode != 0:
        return None, "投影 rc=%d：%s" % (p.returncode, p.stderr.decode("utf-8", "replace").strip())
    first = p.stdout.decode("utf-8", "replace").splitlines()
    return (first[0] if first else ""), ""


def last_seq_of(header):
    if not header:
        return None
    for tok in header.split():
        if tok.startswith("last_seq="):
            return tok.split("=", 1)[1]
    return None


def cmd_click(a):
    rid = "bb-%d" % int(time.time() * 1000)
    acts_before, lines_before = count_kind(a.ledger, "act")
    head_before, _ = projection_header(a.cli, a.ontology, a.ledger, a.policy)
    req = json.dumps(build_request(rid), ensure_ascii=False, sort_keys=True)
    print("REQUEST=%s" % req)
    try:
        reply = send_line(a.socket, req)
    except Exception as e:
        print("REPLY_SEND_FAILED=%s" % e)
        print("STATUS=RED")
        print("REASON=连不上唯一写入口（世界没起来？）——点一下没进世界")
        return 2
    print("REPLY=%s" % reply)
    acts_after, lines_after = count_kind(a.ledger, "act")
    head_after, herr = projection_header(a.cli, a.ontology, a.ledger, a.policy)
    print("LEDGER_LINES_BEFORE=%d" % lines_before)
    print("LEDGER_LINES_AFTER=%d" % lines_after)
    print("ACTS_BEFORE=%d" % acts_before)
    print("ACTS_AFTER=%d" % acts_after)
    print("LAST_SEQ_BEFORE=%s" % last_seq_of(head_before))
    print("LAST_SEQ_AFTER=%s" % last_seq_of(head_after))
    if herr:
        print("PROJECTION_WARN=%s" % herr)

    ok_reply = '"ok":true' in reply.replace(" ", "")
    # ★ 判据（会红）：点一下 ⇒ 账本恰好多 **一条** `act`。
    #    多 0（没进去：把 KIND 改成 change 就是这个形态）／多 2（重发或走了两条路）⇒ 红。
    delta = acts_after - acts_before
    if not ok_reply:
        print("STATUS=RED")
        print("REASON=世界拒绝了这一句（应答不是 ok:true）——点一下没进世界")
        return 1
    if delta != 1:
        print("STATUS=RED")
        print("REASON=账本里 act 的增量是 %d，**必须恰好 1**（0＝没进世界／2＝重发或两条路）" % delta)
        return 1
    print("STATUS=GREEN")
    print("REASON=点一下 ⇒ 账本恰好多一条 act；投影首行位点 %s ⇒ %s（世界侧可观测）"
          % (last_seq_of(head_before), last_seq_of(head_after)))
    return 0


def cmd_self_test():
    """形状自检：正控必有 ＋ 反例必红（不连世界）。"""
    rc = 0
    req = build_request("bb-selftest")
    line = json.dumps(req, ensure_ascii=False, sort_keys=True)
    # 正控 A：形状必须是 act ＋ 三个必填格
    ok_a = (req["kind"] == "act" and set(req["body"]) == {"capability", "verb", "request_id"})
    print("  [%s] 正控 A · 请求形状＝act ＋ capability/verb/request_id" % ("ok  " if ok_a else "FAIL"))
    rc |= 0 if ok_a else 1
    # 正控 B：一行一帧（不含换行）
    ok_b = "\n" not in line
    print("  [%s] 正控 B · 一行一帧（请求里不许有换行）" % ("ok  " if ok_b else "FAIL"))
    rc |= 0 if ok_b else 1
    # 反例 C：把 kind 改坏 ⇒ 形状自检必须红
    try:
        bad = dict(req)
        bad["kind"] = "change"
        ok_c = not (bad["kind"] == "act" and set(bad["body"]) == {"capability", "verb", "request_id"})
    except Exception:
        ok_c = False
    print("  [%s] 反例 C · kind 改成 change ⇒ 形状自检判红" % ("ok  " if ok_c else "FAIL"))
    rc |= 0 if ok_c else 1
    # 反例 D：账本数不上（路径不存在）⇒ 必须报错而不是"数成 0 然后绿"（G1：空集不许判绿）
    try:
        count_kind("/nonexistent/ledger.jsonl", "act")
        ok_d = False
    except SystemExit:
        ok_d = True
    print("  [%s] 反例 D · 账本读不出来 ⇒ 报错（不许把'没读到'读成'0 条'）" % ("ok  " if ok_d else "FAIL"))
    rc |= 0 if ok_d else 1
    print("  ---- 自测结论：%s ----" % ("全通过" if rc == 0 else "有红"))
    return rc


def load_case(path):
    """读案例文件：**「下一步是什么」长在这里**（业务侧的数据，不是 GUI 的知识）。"""
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:
        raise SystemExit("ext.world.BusinessSide.BadCase: %s：%s" % (path, e))
    steps = d.get("steps")
    if not isinstance(steps, list) or not steps:
        raise SystemExit("ext.world.BusinessSide.BadCase: %s 里没有 `steps`（或它是空的）" % path)
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or "label" not in s:
            raise SystemExit("ext.world.BusinessSide.BadCase: 第 %d 步缺 `label`" % (i + 1))
        for act in s.get("actions") or []:
            if not act.get("id") or not act.get("label") or not act.get("capability"):
                raise SystemExit("ext.world.BusinessSide.BadCase: 第 %d 步的某个 action 缺 id/label/capability" % (i + 1))
    return d


def step_notice(subject, idx, step):
    """一条**通告**（`notice` 家族，`type` 非 `gate.` 前缀 ⇒ 过闸只需主体在册）。

    ★ 为什么用 `notice.payload` 承载步骤数据：今天本体里**没有"界面步骤"这一类**
    （已声明的格只有 `notice{muted,retract_seq}`／`job{status}`／`presence{…}`）；
    而 `notice` 家族的 `payload` 是**已声明的可选格**（自由对象）⇒ 借它承载**不需要改本体**。
    ★ 这是**借来的形态**，缺口已登记为"(乙) 世界缺『流程/步骤』这一类"（见件）。
    """
    return {
        "kind": "notice",
        "body": {
            "type": "case.step",
            "subject": subject,
            "payload": {"step": idx + 1, "label": step["label"],
                        "actions": step.get("actions") or []},
        },
    }


def done_notice(subject, total):
    return {"kind": "notice", "body": {"type": "case.finished", "subject": subject,
                                       "payload": {"steps": total}}}


def count_clicks(ledger):
    """数"点一下"（`request_id` 以 `click-` 开头的那族 `act`）——**读账本，不问界面**。"""
    n = 0
    try:
        with io.open(ledger, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("kind") != "act":
                    continue
                rid = (d.get("body") or {}).get("request_id") or ""
                if rid.startswith("click-"):
                    n += 1
    except Exception as e:
        raise SystemExit("ext.world.BusinessSide.LedgerUnreadable: %s: %s" % (ledger, e))
    return n


def cmd_case(a):
    """**业务模拟软件**：发一个案例进世界；之后每看到一次"点一下"，就发下一步。"""
    if not a.case:
        print("STATUS=RED")
        print("REASON=必须给 --case <案例文件>（案例是业务侧的数据）")
        return 1
    case = load_case(a.case)
    steps = case["steps"]
    name = a.case_name or case.get("name") or "case"
    subject = "world://notice/%s" % name
    base = count_clicks(a.ledger)
    idx = 0
    line = json.dumps(step_notice(subject, idx, steps[idx]), ensure_ascii=False, sort_keys=True)
    print("PUBLISH_STEP=%d" % (idx + 1))
    print("PUBLISH_REQUEST=%s" % line)
    try:
        reply = send_line(a.socket, line)
    except Exception as e:
        print("PUBLISH_SEND_FAILED=%s" % e)
        print("STATUS=RED")
        print("REASON=连不上唯一写入口——案例没进世界")
        return 2
    print("PUBLISH_REPLY=%s" % reply)
    if '"ok":true' not in reply.replace(" ", ""):
        print("STATUS=RED")
        print("REASON=世界拒绝了第 1 步的通告")
        return 1
    deadline = time.time() + a.max_seconds
    while time.time() < deadline:
        time.sleep(a.poll)
        now = count_clicks(a.ledger)
        if now <= base:
            continue
        base = now
        idx += 1
        if idx >= len(steps):
            line = json.dumps(done_notice(subject, len(steps)), ensure_ascii=False, sort_keys=True)
            print("PUBLISH_REQUEST=%s" % line)
            try:
                reply = send_line(a.socket, line)
            except Exception as e:
                print("PUBLISH_SEND_FAILED=%s" % e)
            print("PUBLISH_REPLY=%s" % reply)
            print("STATUS=GREEN")
            print("REASON=案例走完 %d 步（世界说了 case.finished）" % len(steps))
            return 0
        line = json.dumps(step_notice(subject, idx, steps[idx]), ensure_ascii=False, sort_keys=True)
        print("PUBLISH_STEP=%d" % (idx + 1))
        print("PUBLISH_REQUEST=%s" % line)
        try:
            reply = send_line(a.socket, line)
        except Exception as e:
            print("PUBLISH_SEND_FAILED=%s" % e)
            print("STATUS=RED")
            return 2
        print("PUBLISH_REPLY=%s" % reply)
    print("STATUS=RED")
    print("REASON=等点击超时（%ss 内没看到新的 click-*）" % a.max_seconds)
    return 1


def cmd_case_self_test():
    """形状自检（不连世界）：案例文件的正控与反例。"""
    import tempfile
    rc = 0
    d = tempfile.mkdtemp(prefix="bs-case-")

    def w(name, obj):
        p = os.path.join(d, name)
        io.open(p, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False))
        return p

    good = w("good.json", {"name": "c1", "steps": [
        {"label": "开始", "actions": [{"id": "next", "label": "下一步", "capability": "job.start"}]},
        {"label": "第二", "actions": [{"id": "next", "label": "下一步", "capability": "job.start"}]},
        {"label": "完", "actions": []}]})
    ok_a = len(load_case(good)["steps"]) == 3
    print("  [%s] 正控 A · 三案例文件读得进（步数＝3）" % ("ok  " if ok_a else "FAIL"))
    rc |= 0 if ok_a else 1

    # 反例 B：action 缺 capability ⇒ 必须拒（"点了发什么"不许留空）
    bad = w("bad.json", {"steps": [{"label": "x", "actions": [{"id": "next", "label": "下一步"}]}]})
    try:
        load_case(bad)
        ok_b = False
    except SystemExit:
        ok_b = True
    print("  [%s] 反例 B · action 缺 capability ⇒ 拒" % ("ok  " if ok_b else "FAIL"))
    rc |= 0 if ok_b else 1

    # 反例 C：没有 steps ⇒ 拒（空案例不许当"没有下一步"静默放过）
    empty = w("empty.json", {"name": "c"})
    try:
        load_case(empty)
        ok_c = False
    except SystemExit:
        ok_c = True
    print("  [%s] 反例 C · 没有 steps ⇒ 拒" % ("ok  " if ok_c else "FAIL"))
    rc |= 0 if ok_c else 1

    # 正控 D：通告形状＝notice 家族 ＋ 三格齐（type/subject/payload）
    n = step_notice("world://notice/c1", 0, {"label": "开始", "actions": []})
    ok_d = (n["kind"] == "notice" and set(n["body"]) == {"type", "subject", "payload"}
            and not n["body"]["type"].startswith("gate."))
    print("  [%s] 正控 D · 通告形状＝notice 家族三格齐，且 type 不带保留前缀 gate." % ("ok  " if ok_d else "FAIL"))
    rc |= 0 if ok_d else 1

    import shutil
    shutil.rmtree(d, ignore_errors=True)
    print("  ---- 案例自测结论：%s ----" % ("全通过" if rc == 0 else "有红"))
    return rc


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--socket", default="/run/world-core/world.sock")
    ap.add_argument("--cli", default="target/debug/world-core")
    ap.add_argument("--ontology", default="/etc/world-core/ontology.json")
    ap.add_argument("--ledger", default="/var/lib/world-core/ledger.jsonl")
    ap.add_argument("--policy", default="/etc/world-core/policy.json")
    ap.add_argument("--case", default="", help="案例文件（JSON）：『下一步是什么』长在里面")
    ap.add_argument("--case-name", default="", help="案例名（用作 notice 的 subject 后缀）")
    ap.add_argument("--poll", type=float, default=0.25)
    ap.add_argument("--max-seconds", type=float, default=60.0)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("cmd", nargs="?", default="click", choices=["click", "case", "case-self-test"])
    a = ap.parse_args(argv)
    if a.self_test:
        return cmd_self_test()
    if a.cmd == "case-self-test":
        return cmd_case_self_test()
    if a.cmd == "case":
        return cmd_case(a)
    return cmd_click(a)


if __name__ == "__main__":
    sys.exit(main())
