#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""socket_uid_guard.py —— 判据：**盘上那个口的属主，必须 ≡ 法律里那条的 uid**。

## 为什么有这一件
2026-10-05 实测现场（`review-tech` 读到、本席复核）：
* 盘上：`/run/world-core/omarchy.sock` **uid=963**（`omarchy`）／`world.sock` **uid=965**（`world-core`）；
* 法律：`/etc/world-core/channel.json` 的 `listeners` 里
  `('/run/world-core/omarchy.sock', 'world://presence/omarchy', **963**)` ⇒ **两条相等**。
⇒ ★ 于是「**谁能连这个口**」这件事**是自洽的**：能连上的就是 uid 963。

## 但这一格今天【对而不可复现】
那一行修复（`ExecStartPre=+/bin/chown …`）**只在机器上**，**不在仓里**：
* 仓内五件 `grep ExecStartPre` ⇒ **0 命中**；
* 而仓内 `deploy/units/world-core.service` 仍有 `User=` ＋ `RuntimeDirectory=` —— **那是把属主拉回 965 的那套机制**。
⇒ ★ 所以：**一旦从仓内重新部署/重建，属主就会走回 965，而【没有任何判据会红】**。
  这一件就是那条判据。

## 判据（三条，各自可判真假）
* **S-01 口在、法律在**：盘上每个 `/run/world-core/*.sock`，法律 `channel.json.listeners` 里必须有对应条目。
  缺 ⇒ **红**（"有个口没人认"）。
* **S-02 uid 相等**：该口的**盘上属主 uid** 必须**逐字等于**法律里那条的 `uid`。不等 ⇒ **红**。
* **S-03 法律里列的口都在盘上**：`listeners` 里每一条 `socket`，盘上必须存在。缺 ⇒ **红**
  （"法律说有个口，而它不在"——那正是 `UndeclaredListener` 那一族，方向相反）。

## 用法
    python3 tools/socket_uid_guard.py --channel /etc/world-core/channel.json --rundir /run/world-core
    python3 tools/socket_uid_guard.py --self-test

## 退出码
    0 = 全绿或 SKIP（SKIP 显式打印 `STATUS=SKIP`，**不算绿**）
    1 = 有红
    2 = 输入缺失（**不是通过**）
"""
import argparse
import json
import os
import pathlib
import stat as statmod
import sys


def read_channel(p: pathlib.Path):
    """返回 ({socket_path: uid}, 法律里【有没有】`listeners` 这一段)。"""
    d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    out = {}
    lst = d.get("listeners")
    if lst is None:
        return out, False
    if isinstance(lst, list):
        for e in lst:
            if isinstance(e, dict) and isinstance(e.get("socket"), str):
                out[e["socket"]] = e.get("uid")
    elif isinstance(lst, dict):
        for k, v in lst.items():
            out[k] = v.get("uid") if isinstance(v, dict) else v
    return out, True


def scan_rundir(rundir: pathlib.Path):
    """返回 {socket_path: uid}（只收 socket）。"""
    out = {}
    if not rundir.is_dir():
        return None
    for f in sorted(rundir.iterdir()):
        try:
            st = f.stat()
        except OSError:
            continue
        if statmod.S_ISSOCK(st.st_mode):
            out[str(f)] = st.st_uid
    return out


def judge(channel, on_disk, law_present=True):
    """channel/on_disk: {path: uid}；law_present: 法律里【有没有 `listeners` 这一段】。
    返回 (status, lines)。

    ★ 区分两件事（本判据第一版把这两件混成一个，被自证反例②抓住）：
      - **法律整段缺失**（`listeners` 根本不在）⇒ SKIP（不适用，不是通过）；
      - **法律有这一段、但没有这一条** ⇒ **RED**（盘上有口没人认）。
    """
    lines = []
    if on_disk is None:
        return "SKIP", ["  [SKIP] 运行目录不存在 ⇒ 判据不适用（**未校验 ≠ 通过**）"]
    if not law_present:
        return "SKIP", ["  [SKIP] 法律里没有 `listeners` 这一段 ⇒ 判据不适用（**未校验 ≠ 通过**）"]

    reds = 0
    for path, uid_disk in sorted(on_disk.items()):
        if path not in channel:
            reds += 1
            lines.append("  [RED ] S-01 %s：盘上有这个口，而法律 `listeners` 里没有它 ⇒ 有个口没人认。" % path)
            continue
        uid_law = channel[path]
        if uid_law is None:
            reds += 1
            lines.append("  [RED ] S-02 %s：法律那一条没写 `uid` ⇒ 无从比对（未校验要说不出来）。" % path)
            continue
        if int(uid_law) != int(uid_disk):
            reds += 1
            lines.append(
                "  [RED ] S-02 %s：**盘上属主 uid=%s，法律写 uid=%s** ⇒ 不等。\n"
                "         这一格就是『谁能连这个口』的凭据；不等 ⇒ 记成某个身份，而连上来的是另一个。\n"
                "         处置：让盘上落成法律写的那个 uid（本机可用的写法＝服务单元里 "
                "`ExecStartPre=+/bin/chown <身份>:<身份> <口>`），或改法律（走评审）。" % (path, uid_disk, uid_law)
            )
        else:
            lines.append("  [ok  ] %s：盘上 uid=%s ≡ 法律 uid=%s ⇒ 一致" % (path, uid_disk, uid_law))

    for path in sorted(channel):
        if path not in on_disk:
            reds += 1
            lines.append("  [RED ] S-03 %s：法律里写着这个口，而盘上【没有】它。" % path)

    return ("RED" if reds else "GREEN"), lines


def self_test() -> int:
    print("== socket_uid_guard 自证 ==")
    A, B = "/run/x/a.sock", "/run/x/b.sock"
    ok = []
    # 反例①：uid 不等 ⇒ RED
    st, _ = judge({A: 963}, {A: 965})
    ok.append(("反例①（盘上 965 vs 法律 963）⇒ 应 RED", st == "RED", st))
    # 反例②：盘上有口、法律没有 ⇒ RED
    st, _ = judge({}, {A: 963})
    ok.append(("反例②（盘上有口、法律没有）⇒ 应 RED", st == "RED", st))
    # 反例③：法律有口、盘上没有 ⇒ RED
    st, _ = judge({A: 963}, {})
    ok.append(("反例③（法律有口、盘上没有）⇒ 应 RED", st == "RED", st))
    # 反例④：法律那条没写 uid ⇒ RED
    st, _ = judge({A: None}, {A: 963})
    ok.append(("反例④（法律没写 uid）⇒ 应 RED", st == "RED", st))
    # 正控：两个口都相等 ⇒ GREEN
    st, _ = judge({A: 963, B: 965}, {A: 963, B: 965})
    ok.append(("正控（两口径都相等）⇒ 应 GREEN", st == "GREEN", st))
    # 不适用 ⇒ SKIP
    st, _ = judge({}, None)
    ok.append(("不适用（运行目录不存在）⇒ 应 SKIP（**不是通过**）", st == "SKIP", st))

    for name, good, got in ok:
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
    allok = all(g for _, g, _ in ok)
    print("  %s 自证%s：六个假命题都被判对（本判定器不是装饰）"
          % ("✅" if allok else "❌", "通过" if allok else "**未通过**"))
    return 0 if allok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel")
    ap.add_argument("--rundir")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.channel or not a.rundir:
        print("[FAIL] 需要 --channel 与 --rundir ⇒ **不是通过**")
        return 2
    cp, rd = pathlib.Path(a.channel), pathlib.Path(a.rundir)
    if not cp.is_file():
        print("[FAIL] 输入缺失：%s ⇒ **不是通过**" % cp)
        return 2

    law, law_present = read_channel(cp)
    st, lines = judge(law, scan_rundir(rd), law_present)
    print("=" * 78)
    print("口属主判据（盘上那个口的属主 ≡ 法律那条的 uid）")
    print("-" * 78)
    for l in lines:
        print(l)
    print("-" * 78)
    if st == "SKIP":
        print("STATUS=SKIP")
        print("结论 = SKIP（不适用；**未校验 ≠ 通过**）")
        return 0
    print("STATUS=%s" % ("PASS" if st == "GREEN" else "FAIL"))
    print("结论 = %s" % ("绿" if st == "GREEN" else "**红**（见上）"))
    return 0 if st == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
