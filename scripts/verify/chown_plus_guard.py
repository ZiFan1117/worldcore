#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chown_plus_guard.py —— 判据：**落地用的 `chown`，必须带那个 `+`；而且盘上要有、仓里也要有**。

## 为什么有这一件
2026-10-05 真机现场（`socket-identity` 16:00:09 复核，本席复核）：
* 盘上 `/run/world-core/omarchy.sock` **uid=963**（`omarchy`），`world.sock` **uid=965**；
  而服务的 `User=world-core` ⇒ **"口的属主 ≠ 服务的身份"今天成立**。
* 让它成立的那一行：`/etc/systemd/system/world-core.service:20`
  **`ExecStartPre=+/bin/chown omarchy:omarchy /run/world-core/omarchy.sock`**（`systemctl show` 记 `status=0`）。

## 那个 `+` 为什么是命门（本席原文，逐字）
* **`ExecStartPre` 默认跑在【已降权】的服务身份下**（这里是 `world-core`）；
* 沙箱同形装置实测：**去掉 `+` ⇒ `chown` 改不动，而且被后一趟递归 chown 静默盖掉**（**而服务仍报 success**）；
* 加 `+` ⇒ 以完全权限跑 ⇒ ①改得动 ②它排在递归 chown **之后**，落在最后。
⇒ ★ **若有人"清理"这行时把 `+` 拿掉，属主会静默退回 965** —— **不报错、不告警**。

## 判据（四条，各自可判真假）
* **P-01 有 `+`**：单元文件里凡出现 `chown`（在 `ExecStartPre=` / `ExecStartPost=` 里），**该指令必须以 `+` 开头**。
  没有 ⇒ **红**（"它会静默失效"）。
* **P-02 仓里也要有**：盘上有的那一条，**仓内 `deploy/` 里也必须有一条等价物**。
  盘上有、仓里没有 ⇒ **红**（"部署漂移：下次从仓部署会丢"）。
* **P-03 仓里有、盘上也要有**：仓内声明的 `chown` 行，盘上那份必须也有。
  仓里有、盘上没有 ⇒ **红**（"仓里写了没装"）。
* **P-04 口必须被点名**：`chown` 的目标必须是**具体的口路径**（不是一个目录）——
  目录会被 `RuntimeDirectory=` 的递归再盖一次。

## 用法
    python3 tools/chown_plus_guard.py --repo /path/to/repo --live /etc/systemd/system
    python3 tools/chown_plus_guard.py --self-test

## 退出码
    0 = 全绿或 SKIP（SKIP 显式打印 `STATUS=SKIP`，**不算绿**）／1 = 有红／2 = 输入缺失（**不是通过**）
"""
import argparse
import pathlib
import re
import sys

# 认 `ExecStartPre=` / `ExecStartPost=` 里带 chown 的行（含可选的前导 `+` / `-` / `!`）
# ★★ 注意这个正则里的 `([+\-!]?)` 后面**紧接** `(\S.*)` —— **中间不许有空白**。
#   为什么（2026-10-05 实测，socket-identity 沙箱判死）：`ExecStartPre=+ /bin/chown …`
#   （`+` 后带一个空格）⇒ **`LoadState=bad-setting`**，日志逐字
#   `Empty path in command line: + /bin/chown …` ⇒ `Unit configuration has fatal error, unit will not be started.`
#   ⇒ **服务起不来、口建不出来**。而 `=+/bin/chown …` 才是对的形态。
#   ⇒ 故 `P-05` 专盯"`+` 后有没有空白"：**它比"漏 `+`"更坏** ——
#     漏 `+` 是【静默退回 965】，而 `+ ` 带空格是【直接拒启】。
EXEC_CHOWN = re.compile(r"^\s*(ExecStartPre|ExecStartPost)\s*=\s*([+\-!]?)\s*(.*\bchown\b.*)$")
# `P-05` 专用：`=` 之后先是可选前缀，**若紧跟空白则坏**
BAD_PREFIX_SPACE = re.compile(r"^\s*Exec(StartPre|StartPost)\s*=\s*[+\-!]\s")
TARGET = re.compile(r"chown\s+\S+\s+(\S+)\s*$")


def scan(d: pathlib.Path):
    """扫描一个目录下的单元文件；返回 [(file, lineno, prefix, cmdline, target)]。"""
    out = []
    if not d.is_dir():
        return None
    for f in sorted(d.iterdir()):
        if not (f.is_file() and (f.suffix in (".service", ".socket", ".target") or ".service" in f.name)):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = EXEC_CHOWN.match(line)
            if not m:
                continue
            _, prefix, cmd = m.groups()
            t = TARGET.search(cmd.strip())
            bad_space = bool(BAD_PREFIX_SPACE.match(line))
            out.append((str(f), i, prefix, cmd.strip(), (t.group(1) if t else None), bad_space))
    return out


def judge(repo_units, live_units):
    """repo_units/live_units: scan() 的返回值（None＝那个目录不存在）；返回 (status, lines)"""
    lines = []
    if live_units is None and repo_units is None:
        return "SKIP", ["  [SKIP] 两个目录都不在 ⇒ 判据不适用（**未校验 ≠ 通过**）"]
    repo_units = repo_units or []
    live_units = live_units or []

    reds = 0
    # P-01 / P-04：每一条都查（仓里与盘上都查）
    for tag, units in (("仓内", repo_units), ("盘上", live_units)):
        for f, ln, prefix, cmd, target, bad_space in units:
            if bad_space:
                reds += 1
                lines.append(
                    "  [RED ] P-05 %s %s:%d 的 `+` **后面带空白** ⇒ ★**这不是「少个字符」，这是【坏单元】**：\n"
                    "         systemd 报 `LoadState=bad-setting`，日志逐字 `Empty path in command line: %s` ⇒\n"
                    "         `Unit configuration has fatal error, unit will not be started.` ⇒ **服务起不来、口建不出来**。\n"
                    "         原文：`%s`\n"
                    "         处置：写成 `ExecStartPre=+<路径>`（★ `+` 与命令之间**不许有空白**）。" % (tag, pathlib.Path(f).name, ln, cmd, cmd)
                )
            if prefix != "+":
                reds += 1
                lines.append(
                    "  [RED ] P-01 %s %s:%d 的 `chown` 没带 `+` ⇒ **它会静默失效**（跑在已降权身份下、且被递归 chown 盖掉）。\n"
                    "         原文：`%s`\n"
                    "         处置：写成 `ExecStartPre=+…`（`+` ＝ 以完全权限跑）。" % (tag, pathlib.Path(f).name, ln, cmd)
                )
            else:
                lines.append("  [ok  ] P-01 %s %s:%d 带 `+` ⇒ 以完全权限跑，落在递归 chown 之后" % (tag, pathlib.Path(f).name, ln))
            if target is None or target.endswith("/"):
                reds += 1
                lines.append("  [RED ] P-04 %s %s:%d 的 `chown` 目标不是具体文件（%r）⇒ 会被递归 chown 再盖。" % (tag, pathlib.Path(f).name, ln, target))
            else:
                lines.append("  [ok  ] P-04 %s %s:%d 点名的目标是具体口：`%s`" % (tag, pathlib.Path(f).name, ln, target))

    # P-02 / P-03：两侧条数对不上 ⇒ 漂移
    n_repo, n_live = len(repo_units), len(live_units)
    if n_live > n_repo:
        reds += 1
        lines.append(
            "  [RED ] P-02 **盘上有 %d 条 `chown`，仓里只有 %d 条** ⇒ 部署漂移：\n"
            "         下次从仓内部署会把这 %d 条丢掉（属主走回默认），而**不会有判据变红**。\n"
            "         处置：把那一条落回仓内 `deploy/`。" % (n_live, n_repo, n_live - n_repo)
        )
    elif n_repo > n_live:
        reds += 1
        lines.append("  [RED ] P-03 **仓里有 %d 条 `chown`，盘上只有 %d 条** ⇒ 仓里写了没装。" % (n_repo, n_live))
    else:
        lines.append("  [ok  ] P-02/P-03 两侧 `chown` 条数相等（仓内 %d ＝ 盘上 %d）" % (n_repo, n_live))

    return ("RED" if reds else "GREEN"), lines


def self_test() -> int:
    print("== chown_plus_guard 自证 ==")
    ok = []
    L = [("/x/w.service", 20, "+", "chown omarchy:omarchy /run/world-core/omarchy.sock", "/run/world-core/omarchy.sock", False)]
    # 正控：两侧各一条、都带 +、目标是具体文件 ⇒ GREEN
    st, _ = judge(L, L)
    ok.append(("正控（两侧各一条、带 `+`、点名文件）⇒ 应 GREEN", st == "GREEN", st))
    # 反例①：没带 `+` ⇒ RED
    st, _ = judge([], [("/x/w.service", 20, "", "chown a:a /run/a.sock", "/run/a.sock", False)])
    ok.append(("反例①（没带 `+`）⇒ 应 RED", st == "RED", st))
    # 反例②：盘上有、仓里没有 ⇒ RED
    st, _ = judge([], L)
    ok.append(("反例②（盘上有、仓里没有 ⇒ 部署漂移）⇒ 应 RED", st == "RED", st))
    # 反例③：仓里有、盘上没有 ⇒ RED
    st, _ = judge(L, [])
    ok.append(("反例③（仓里有、盘上没有）⇒ 应 RED", st == "RED", st))
    # 反例④：目标是目录 ⇒ RED
    st, _ = judge([], [("/x/w.service", 20, "+", "chown a:a /run/", "/run/", False)])
    ok.append(("反例④（目标是目录）⇒ 应 RED", st == "RED", st))
    # ★ 反例⑤：`+` 后面带空白 ⇒ 坏单元 ⇒ RED（2026-10-05 实测：bad-setting / 拒启）
    st, _ = judge([], [("/x/w.service", 20, "+", "/bin/chown a:a /run/a.sock", "/run/a.sock", True)])
    ok.append(("反例⑤（`+` 后带空白 ⇒ 坏单元）⇒ 应 RED", st == "RED", st))
    # 不适用 ⇒ SKIP
    st, _ = judge(None, None)
    ok.append(("不适用（两个目录都不在）⇒ 应 SKIP（**不是通过**）", st == "SKIP", st))

    for name, good, got in ok:
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
    allok = all(g for _, g, _ in ok)
    print("  %s 自证%s：六个假命题都被判对（本判定器不是装饰）"
          % ("✅" if allok else "❌", "通过" if allok else "**未通过**"))
    return 0 if allok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="仓内 deploy/ 目录")
    ap.add_argument("--live", help="盘上单元目录（如 /etc/systemd/system）")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.repo and not a.live:
        print("[FAIL] 至少给一个：--repo 或 --live ⇒ **不是通过**")
        return 2

    repo = scan(pathlib.Path(a.repo)) if a.repo else None
    live = scan(pathlib.Path(a.live)) if a.live else None
    if a.repo and not pathlib.Path(a.repo).is_dir():
        print("[FAIL] 输入缺失：%s ⇒ **不是通过**" % a.repo)
        return 2

    st, lines = judge(repo, live)
    print("=" * 78)
    print("chown `+` 判据（落地那一行必须带 `+`；仓内与盘上不许漂移）")
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
