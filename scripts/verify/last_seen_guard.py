#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""last_seen_guard.py —— 判据：**`presence list` 印出来的 `last_seen`，必须有【账本出处】**。

## 为什么有这一件
2026-10-05 实测现场：
* `presence list` 逐字：`world://presence/omarchy name="omarchy" category="shell" state="running" **last_seen=--**`
* 账本里 `path="last_seen"` 的 `change` 共 **80 条，全部 actor 是 `world://core`**；
  而**没有任何一条** `subject=world://presence/omarchy` 的 `last_seen`。

★ 由此更正一条**我自己先前的错口径**：我曾把「被见过」的凭据当成
  **「被观测者自己发过 `act`」** —— **错**。现取事实是：`last_seen` 由 **`world://core` 落一条 `change`** 写进去。
  ⇒ ★ `--` 的语义 ＝ **「无人写过这一格」**，**不是**「它没说过话」。

## 判据（四条，各自可判真假）
* **L-01 有值必须有出处**：`presence list` 里某在场者的 `last_seen` 是**数字** ⇒
  账本里必须存在一条 `change`（`path="last_seen"`、`subject=该在场者`）。找不到 ⇒ **红**。
* **L-02 无出处不许印值**：`--`（无人写过）⇒ 账本里**不许**存在写它的 `change`。存在 ⇒ **红**。
* **L-03 必须逐字相符**：数字必须**逐字**等于**最后一条**写它的 `change` 的 `after`（按 `seq` 取最后）。不等 ⇒ **红**。
* **L-04 不许凭空多出在场者**：`presence list` 里的每个 subject，账本里必须有**它的格**。
  没有 ⇒ **红**（"名册里有人，账本里没有"）。

## 用法
    python3 scripts/verify/last_seen_guard.py --ledger <账本路径> --presence <presence list 输出文件>
    python3 scripts/verify/last_seen_guard.py --self-test

## 退出码
    0 = 全绿或 SKIP（SKIP 显式打印，**不算绿**）／1 = 有红／2 = 输入缺失（**不是通过**）
"""
import argparse
import json
import pathlib
import re
import sys

LINE_RE = re.compile(r"(world://presence/[A-Za-z0-9_./-]+)")
SEEN_RE = re.compile(r"last_seen\s*[=:]\s*([^\s,|]+)")
DASH = ("--", "-", "None", "null", "")


def scan_ledger(ledger_path: pathlib.Path):
    """返回 (seen_writes, subjects)
    seen_writes: {subject: [(seq, after_as_written_str)]}  按 seq 升序
    subjects   : set(subject)  —— 账本里出现过的所有 presence 主体
    """
    writes, subjects = {}, set()
    with ledger_path.open(encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                o = json.loads(raw)
            except Exception:
                continue
            b = o.get("body") or {}
            subj = b.get("subject")
            if isinstance(subj, str) and subj.startswith("world://presence/"):
                subjects.add(subj)
                if o.get("kind") == "change" and b.get("path") == "last_seen":
                    writes.setdefault(subj, []).append((o.get("seq", 0), b.get("after")))
    for k in writes:
        writes[k].sort(key=lambda t: t[0])
    return writes, subjects


def parse_presence(text: str):
    out = {}
    for line in text.splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        s = SEEN_RE.search(line)
        out[m.group(1)] = (s.group(1).strip() if s else None)
    return out


def _as_str(v):
    return json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v


def judge(writes, subjects, pres):
    """返回 (status, lines)"""
    lines = []
    if not pres:
        return "SKIP", ["  [SKIP] 没解析到任何在场者行 ⇒ 判据不适用（**不是通过**；请检查输入形态）"]

    reds = 0
    for subj, seen in sorted(pres.items()):
        w = writes.get(subj, [])
        is_dash = seen in DASH

        # L-04
        if subj not in subjects:
            reds += 1
            lines.append("  [RED ] L-04 %s：名册里有它，**账本里没有任何一格** ⇒ 名册凭空多出。" % subj)
            continue

        if not is_dash:
            if not w:
                reds += 1
                lines.append(
                    "  [RED ] L-01 %s：last_seen=%r（有值），而账本里**没有一条**写它的 `change`（path=last_seen）⇒\n"
                    "         这是『印了一个没有出处的值』。处置：要么补那条 `change`，要么置回 `--`。" % (subj, seen)
                )
                continue
            last_seq, last_after = w[-1]
            if _as_str(last_after) != seen:
                reds += 1
                lines.append(
                    "  [RED ] L-03 %s：印的是 %r，而账本最后一条（seq=%s）写的是 %r ⇒ 不符。"
                    % (subj, seen, last_seq, _as_str(last_after))
                )
                continue
            lines.append("  [ok  ] %s：last_seen=%s ⇐ 账本 seq=%s ⇒ 有出处、逐字相符" % (subj, seen, last_seq))
        else:
            if w:
                reds += 1
                lines.append(
                    "  [RED ] L-02 %s：印 `--`（无人写过），而账本里有 %d 条写它的 `change`（最后 seq=%s）⇒ 有出处却印空。"
                    % (subj, len(w), w[-1][0])
                )
            else:
                lines.append("  [ok  ] %s：last_seen=-- ⇐ 账本里确实没有人写过它 ⇒ 一致" % subj)

    return ("RED" if reds else "GREEN"), lines


def self_test() -> int:
    print("== last_seen_guard 自证 ==")
    P = "world://presence/x"
    ok = []
    # 反例①：有值、无出处 ⇒ RED
    st, _ = judge({}, {P}, {P: "123"})
    ok.append(("反例①（有值 ＋ 无出处）⇒ 应 RED", st == "RED", st))
    # 反例②：印 `--`、却有出处 ⇒ RED
    st, _ = judge({P: [(9, 123)]}, {P}, {P: "--"})
    ok.append(("反例②（印 `--` ＋ 有出处）⇒ 应 RED", st == "RED", st))
    # 反例③：有值、有出处、但逐字不符 ⇒ RED
    st, _ = judge({P: [(9, 123)]}, {P}, {P: "124"})
    ok.append(("反例③（有出处 ＋ 逐字不符）⇒ 应 RED", st == "RED", st))
    # 反例④：名册有人、账本没有 ⇒ RED
    st, _ = judge({}, set(), {P: "--"})
    ok.append(("反例④（名册有人 ＋ 账本没有）⇒ 应 RED", st == "RED", st))
    # 正控①：有值、有出处、相符 ⇒ GREEN
    st, _ = judge({P: [(9, 123)]}, {P}, {P: "123"})
    ok.append(("正控①（有值 ＋ 有出处 ＋ 相符）⇒ 应 GREEN", st == "GREEN", st))
    # 正控②：`--`、确实无出处 ⇒ GREEN
    st, _ = judge({}, {P}, {P: "--"})
    ok.append(("正控②（`--` ＋ 无出处）⇒ 应 GREEN", st == "GREEN", st))
    # 不适用 ⇒ SKIP
    st, _ = judge({}, set(), {})
    ok.append(("不适用（没有在场者行）⇒ 应 SKIP（**不是通过**）", st == "SKIP", st))

    for name, good, got in ok:
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
    allok = all(g for _, g, _ in ok)
    print("  %s 自证%s：七个假命题都被判对（本判定器不是装饰）"
          % ("✅" if allok else "❌", "通过" if allok else "**未通过**"))
    return 0 if allok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger")
    ap.add_argument("--presence")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.ledger or not a.presence:
        print("[FAIL] 需要 --ledger 与 --presence ⇒ **不是通过**")
        return 2
    lp, pp = pathlib.Path(a.ledger), pathlib.Path(a.presence)
    if not lp.is_file() or not pp.is_file():
        print("[FAIL] 输入缺失：%s / %s ⇒ **不是通过**" % (lp, pp))
        return 2

    writes, subjects = scan_ledger(lp)
    pres = parse_presence(pp.read_text(encoding="utf-8", errors="replace"))
    st, lines = judge(writes, subjects, pres)
    print("=" * 78)
    print("last_seen 判据（印出来的值必须有账本出处）")
    print("-" * 78)
    for l in lines:
        print(l)
    print("-" * 78)
    if st == "SKIP":
        # ★ 必须逐字吐 `STATUS=SKIP`：`run_tail` 只按这一行把该步降成 ⏭（未校验）。
        #   不吐 ⇒ 该步会被渲染成 ✅ —— 而本工具自己明明印着「未校验 ≠ 通过」⇒ 那就是一个假绿。
        #   （与 `kind_guard.py` 同形；2026-10-05 由件主补，来源＝protocol-arbiter 的拒绝盲接。）
        print("STATUS=SKIP")
        print("结论 = SKIP（不适用；**未校验 ≠ 通过**）")
        return 0
    print("STATUS=%s" % ("PASS" if st == "GREEN" else "FAIL"))
    print("结论 = %s" % ("绿" if st == "GREEN" else "**红**（见上）"))
    return 0 if st == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
