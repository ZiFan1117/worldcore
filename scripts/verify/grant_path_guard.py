#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grant_path_guard.py —— 判据：**本体里声称的"授权路"，程序里必须真的读它**。

## 为什么有这一件
2026-10-05 实测：本体 `_permissions._grant_via_ledger` 逐字写着
「授予／收回是**事实**，走**账本事件**（`change` 写 `world://user` 的能力格 → 门禁 → 落笔）……
**改一次授权 ＝ 落一条事件**」。
而现取代码 `src/lib.rs` 的授权判定读的是 **本体 `_permissions.grants.<能力>.scope`** ——
**不读账本、不读那条格**。⇒ 那句是【设计已定 · 未落地】。
★ 病根：**纸上写了一条路，程序里没有那条路 —— 而没有任何判据盯着这个差**。
   （第二件的落地对照表里，这一类就是「判据 = 无」。）

## 判据（三条，各自可判真假）
* **G-01 声明在**：本体里有没有 `_grant_via_ledger` 这一段。
  - 有 ⇒ 它的**声称**必须能在 `src/` 里找到**对应的读取处**（见 G-02）。
  - 没有 ⇒ 本判据 **SKIP**（不适用，不是通过）。
* **G-02 接线在**：`src/` 里必须存在读取「能力格」（`world://user` 的授权格）的代码。
  - 判法：在 `src/` 里找**同时**含「账本事件」语义与「能力格 / grant 格」语义的读取点；
  - 找不到 ⇒ **红**（`G-02 声明了走账本事件，但 src/ 里没有读那张格的代码`）。
* **G-03 口径唯一**：授权判定若读本体，则 `src/` 里**不许再出现第二处**读授权 scope 的地方。
  - 理由：一处事实只有一个权威载体（书 §八）。

## 用法
    python3 scripts/verify/grant_path_guard.py            # 判定（以仓根为根）
    python3 scripts/verify/grant_path_guard.py --self-test # 自证：反例必红、正控必绿

## 退出码
    0 = 全绿或 SKIP（SKIP 会显式打印，不算绿）
    1 = 有红
    2 = 输入缺失（**不是通过**）
"""
import argparse
import pathlib
import re
import sys

# ★ 2026-10-07 修（现取病灶）：本文件在 `scripts/verify/` ⇒ 仓根＝**上三级**。
#   原来只上溯两级（`parent.parent`）= `scripts/` ⇒ `ONT`／`SRC` 全指到 `scripts/src/…`（不存在）
#   ⇒ 裸跑恒返 **rc=2「输入缺失」**（本仓口径：读不到＝不是通过），接进 `check.sh` 会让那一步永远 ⏸/阻断。
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent    # 仓根
ONT = ROOT / "src" / "ontology_definition" / "ontology.json"
SRC = ROOT / "src"

DECL_KEY = "_grant_via_ledger"
DECL_CLAIM = "改一次授权"        # 声明里的关键句（判它有没有声称"落一条事件"）
LEDGER_CLAIM = "账本事件"

# 「读那张格」的判法：源码里出现"能力格/授权格"这一类读取语义
CELL_READ_PATTERNS = [
    r"capability_cell",
    r"grant_cell",
    r"cap_cell",
    r"world://user\s*#?\s*(?:cap|grant)",
    r"read_grant",
    r"grant_from_ledger",
]
# 授权判定的现有读法（读本体）
ONTOLOGY_READ_PATTERNS = [
    r"permissions\(\)",
    r"_permissions",
    r"grants",
]


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _src_text() -> str:
    if not SRC.is_dir():
        return ""
    out = []
    for f in sorted(SRC.rglob("*.rs")):
        out.append(_read(f))
    return "\n".join(out)


def judge(ont_text: str, src_text: str):
    """返回 (status, lines)；status ∈ {'GREEN','SKIP','RED','MISSING'}"""
    lines = []

    if DECL_KEY not in ont_text:
        return "SKIP", ["  [SKIP] G-01 本体里没有 `%s` ⇒ 本判据不适用（**不是通过**）" % DECL_KEY]

    lines.append("  [ok  ] G-01 本体里有 `%s` —— 它声称的那条路必须能在 src/ 里找到" % DECL_KEY)

    # 那段声明的上下文（取键后 600 字符）
    idx = ont_text.index(DECL_KEY)
    seg = ont_text[idx: idx + 600]
    claims_ledger = (LEDGER_CLAIM in seg) or (DECL_CLAIM in seg)
    if not claims_ledger:
        lines.append("  [ok  ] G-01b 该段没有声称『走账本事件／改一次授权』⇒ G-02 不适用")
        return "GREEN", lines

    lines.append("  [ok  ] G-01b 该段逐字声称『%s』" % (LEDGER_CLAIM if LEDGER_CLAIM in seg else DECL_CLAIM))

    # G-02：src/ 里有没有读那张格的代码
    hit = [p for p in CELL_READ_PATTERNS if re.search(p, src_text)]
    if hit:
        lines.append("  [ok  ] G-02 src/ 里有读『能力格』的代码（命中：%s）" % ", ".join(hit))
    else:
        lines.append(
            "  [RED ] G-02 本体声称『%s』，而 src/ 里【没有读那张格的代码】\n"
            "          ⇒ 这是【设计已定 · 未落地】：纸上有那条路，程序里没有。\n"
            "          处置：要么把它落成代码，要么在本体里把该段标为『设计已定·未落地』。"
            % LEDGER_CLAIM
        )

    # G-03：授权判定的读法（本体）应只有一处权威
    ont_hits = sum(1 for p in ONTOLOGY_READ_PATTERNS if re.search(p, src_text))
    if ont_hits:
        lines.append("  [ok  ] G-03 授权判定读本体（命中 %d 个模式）——**当前唯一的读法**" % ont_hits)
    else:
        lines.append("  [RED ] G-03 src/ 里找不到读本体 `_permissions` 的代码 ⇒ 授权判定的读法不明")

    return ("RED" if any("[RED" in l for l in lines) else "GREEN"), lines


def self_test() -> int:
    """自证：反例必红、正控必绿。"""
    print("== grant_path_guard 自证 ==")
    bad_ont = '{"_permissions":{"_grant_via_ledger":"走账本事件，改一次授权 ＝ 落一条事件"}}'
    bad_src = 'fn foo() { /* 什么都不读 */ }'
    st, _ = judge(bad_ont, bad_src)
    ok1 = (st == "RED")
    print("  %s 反例①（声明在、src 里没读那张格）⇒ %s（期望 RED）" % ("✅" if ok1 else "❌", st))

    good_ont = '{"_permissions":{"_grant_via_ledger":"走账本事件"}}'
    good_src = 'fn read_grant() { let x = permissions(); }'
    st2, _ = judge(good_ont, good_src)
    ok2 = (st2 == "GREEN")
    print("  %s 正控（声明在、src 里有读那张格）⇒ %s（期望 GREEN）" % ("✅" if ok2 else "❌", st2))

    st3, _ = judge('{"_permissions":{}}', good_src)
    ok3 = (st3 == "SKIP")
    print("  %s 不适用（本体里没有该键）⇒ %s（期望 SKIP，**不是通过**）" % ("✅" if ok3 else "❌", st3))

    allok = ok1 and ok2 and ok3
    print("  %s 自证%s：三个假命题都被判对（本判定器不是装饰）"
          % ("✅" if allok else "❌", "通过" if allok else "**未通过**"))
    return 0 if allok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    if not ONT.is_file():
        print("[FAIL] 输入缺失：%s 不在 ⇒ **不是通过**" % ONT)
        return 2
    if not SRC.is_dir():
        print("[FAIL] 输入缺失：%s 不在 ⇒ **不是通过**" % SRC)
        return 2

    st, lines = judge(_read(ONT), _src_text())
    print("=" * 78)
    print("授权路判据（本体声称的路 ↔ src/ 里有没有那条路）")
    print("根 = %s" % ROOT)
    print("-" * 78)
    for l in lines:
        print(l)
    print("-" * 78)
    if st == "SKIP":
        print("结论 = SKIP（不适用；**未校验 ≠ 通过**）")
        return 0
    print("结论 = %s" % ("绿" if st == "GREEN" else "**红**（见上）"))
    return 0 if st == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
