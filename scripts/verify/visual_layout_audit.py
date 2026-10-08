#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""visual_layout_audit.py —— 视觉投影**排版契约的独立审计器**（`TC-051` / `REQ-F-019` 判据 ④）

## 为什么需要它

`REQ-F-019` 判据 ④ 要求"提取出的 `(主体,路径,值)` 三元组集合与读模型 `State::entries()` 逐项相等"。
现有证据是 `scripts/test/acceptance.rs::t15`——但它用的是**同一模块**的 `src/project/visual.rs::parse()`
来解析自己渲染出来的文本，即**同模块自证**。本项目逐字纪律：「**反例不红视为未校验**」，
而"同模块自证"不构成校验面。

本脚本是**独立于 `visual::parse()` 的第二份解析器**（本文件不 import、不调用任何 Rust 代码，
只用行正则），对真实渲染输出做**字节级排版审计**，并自带 `--self-test`（先证明**它会红**）。

## 审计的排版契约（逐条可机械核对）

| # | 契约 | 判据 |
|---|---|---|
| 1 | 首行是同源头 | 严格匹配 `^#world-core projection=visual world=<int> vocab=<tok> last_seq=<int> state=<tok>$`（**无多余空格**） |
| 2 | 第 2 行是标题 | 逐字 `世界状态（视觉投影）` |
| 3 | 分隔线 | 第 3 行**只由** `U+2500` 组成，且长度 **= 44** |
| 4 | 摘要行 | `^  已折叠 <n> 条事件（最近序号 <n>）｜动作 <n> 条｜通告 <n> 条$`；**空状态**时为 `  （账本为空：这个世界还没有发生过任何事）` |
| 5 | 收尾分隔线 | 非空状态第 5 行同为 44 个 `U+2500`；**空状态只有 4 行**（无收尾线） |
| 6 | 主体行 | **恰好 2 个空格** ＋ `world://…` |
| 7 | 字段行 | **恰好 6 个空格** ＋ `路径 = JSON值`，且值必须能被 `json.loads` |
| 8 | 次序 | **任何字段行不得出现在首个主体行之前** |
| 9 | 封闭性 | 全部行**必须被分类**（未分类行数 = 0）——防"排版里混进没人认领的行" |
| 10 | 无裸控制字符 | 正文不得含 `\\t` / `\\r` / 其它 C0 控制字符；含换行的值**必须被转义**（否则一行变两行、排版破碎） |
| 11 | 行尾 | 文件以 **LF** 结尾且**无 CR** |

**本脚本不判断**：值的语义是否正确（那是 `TC-042` 的 `P ⊆ S`）、排版是否好看。
它只回答一个问题：**这份渲染输出的排版，是否严格符合 `REQ-F-019` 逐字声明的那份契约**。

用法：
  `python3 scripts/verify/visual_layout_audit.py --file <渲染输出>`
  `python3 scripts/verify/visual_layout_audit.py --stdin`
  `python3 scripts/verify/visual_layout_audit.py --self-test`   # 先证明判定器会红
退出码：0 = 无违反；1 = 有违反；2 = 用法错误。
"""

import argparse
import json
import re
import sys

RULE_CHAR = "\u2500"
RULE_LEN = 44
TITLE = "世界状态（视觉投影）"

HEADER_RE = re.compile(
    r"^#world-core projection=visual world=\d+ vocab=\S+ last_seq=\d+ state=\S+$"
)
SUMMARY_RE = re.compile(
    r"^ {2}已折叠 \d+ 条事件（最近序号 \d+）｜动作 \d+ 条｜通告 \d+ 条$"
)
EMPTY_RE = re.compile(r"^ {2}（账本为空：这个世界还没有发生过任何事）$")
BODY_RE = re.compile(r"^ {2}(world://\S+)$")
FIELD_RE = re.compile(r"^ {6}(\S.*?) = (.+)$")


def split_lines(text):
    """按 LF 切行；返回 (行列表, 是否以 LF 结尾, 是否含 CR)。"""
    has_cr = "\r" in text
    ends_lf = text.endswith("\n")
    body = text[:-1] if ends_lf else text
    lines = body.split("\n") if body else []
    return lines, ends_lf, has_cr


def audit(text):
    """返回违反项列表；空列表 = 通过。"""
    v = []
    lines, ends_lf, has_cr = split_lines(text)

    if has_cr:
        v.append("行尾：正文含 CR（本投影必须是纯 LF）")
    if not ends_lf:
        v.append("行尾：文件未以 LF 结尾")

    if len(lines) < 4:
        v.append("结构：行数 %d < 4（至少需 首行/标题/分隔线/摘要行）" % len(lines))
        return v

    if not HEADER_RE.match(lines[0]):
        v.append("契约 1：首行不是合法的同源头（实得 %r）" % lines[0][:120])
    if lines[1] != TITLE:
        v.append("契约 2：第 2 行应为 %r，实得 %r" % (TITLE, lines[1]))

    def check_rule(idx, label):
        ln = lines[idx]
        if set(ln) != {RULE_CHAR} or len(ln) != RULE_LEN:
            v.append(
                "契约 3/5：%s（第 %d 行）应为 %d 个 U+2500，实得长度 %d、"
                "非该字符数 %d" % (label, idx + 1, RULE_LEN, len(ln),
                                   sum(1 for c in ln if c != RULE_CHAR))
            )

    check_rule(2, "分隔线")

    empty = bool(EMPTY_RE.match(lines[3]))
    if empty:
        if len(lines) != 4:
            v.append("契约 5：空状态应恰有 4 行（无收尾分隔线），实得 %d 行" % len(lines))
        if not EMPTY_RE.match(lines[3]):
            v.append("契约 4：空状态摘要行不合契约（实得 %r）" % lines[3])
        return v

    if not SUMMARY_RE.match(lines[3]):
        v.append("契约 4：摘要行不合契约（实得 %r）" % lines[3])
    if len(lines) < 5:
        v.append("契约 5：非空状态缺少收尾分隔线（第 5 行）")
        return v
    check_rule(4, "收尾分隔线")

    seen_body = False
    n_body = 0
    n_field = 0
    for i, ln in enumerate(lines[5:], start=6):
        if ln == "":
            v.append("契约 9：第 %d 行为空行（非空状态的正文不得有空行）" % i)
            continue
        m = FIELD_RE.match(ln)
        if m:
            if not seen_body:
                v.append("契约 8：第 %d 行是字段行，但它出现在**任何主体行之前**" % i)
            n_field += 1
            try:
                json.loads(m.group(2))
            except Exception as e:  # noqa: BLE001
                v.append("契约 7：第 %d 行的值不是合法 JSON（%s）：%r" % (i, e, m.group(2)))
            continue
        m2 = BODY_RE.match(ln)
        if m2:
            seen_body = True
            n_body += 1
            continue
        v.append("契约 6/9：第 %d 行无法归类（既非恰好 2 空格的主体行，"
                 "也非恰好 6 空格的字段行）：%r" % (i, ln[:80]))

    if n_body == 0:
        v.append("契约 6：非空状态却**没有任何主体行**")
    if n_field == 0:
        v.append("契约 7：非空状态却**没有任何字段行**")

    # 契约 10：正文不得含裸控制字符（除作为行分隔的 LF 外）
    for i, ln in enumerate(lines, start=1):
        bad = [c for c in ln if ord(c) < 0x20 or ord(c) == 0x7F]
        if bad:
            v.append("契约 10：第 %d 行含裸控制字符 %r（值必须被转义）"
                     % (i, [hex(ord(c)) for c in bad]))
    return v


# ── 三份**字节级期望样本**（对应 P-06 要求的三种情形）────────────────────
_H = "#world-core projection=visual world=1 vocab=fnv1a64:6a96abfa9a969462 " \
     "last_seq=2 state=fnv1a64:057b92d9ea7b8091"
_R = RULE_CHAR * RULE_LEN

SAMPLES = {
    "normal": "\n".join([
        _H, TITLE, _R,
        "  已折叠 2 条事件（最近序号 2）｜动作 0 条｜通告 0 条", _R,
        "  world://sys/a", "      p = 1",
        "  world://sys/b", "      q = \"x\"",
        "",
    ]),
    "newline": "\n".join([
        _H, TITLE, _R,
        "  已折叠 2 条事件（最近序号 2）｜动作 0 条｜通告 0 条", _R,
        "  world://sys/nl", "      esc = \"a\\nb\\tc\"",
        "",
    ]),
    "empty": "\n".join([
        _H, TITLE, _R,
        "  （账本为空：这个世界还没有发生过任何事）",
        "",
    ]),
}


def self_test():
    """先证明**判定器会红**，再证明三份期望样本全绿。"""
    fail = 0

    def case(name, text, want_violations, must_mention=None):
        nonlocal fail
        got = audit(text)
        if want_violations:
            if not got:
                print("  ❌ 自证失败：[%s] 应当报违反，实得 0 项（判定器是装饰）" % name)
                fail += 1
                return
            if must_mention and not any(must_mention in x for x in got):
                print("  ❌ 自证失败：[%s] 违反项未点名 %r：%s"
                      % (name, must_mention, got))
                fail += 1
                return
            print("  ✅ 自证：[%s] 报出 %d 项违反 —— %s" % (name, len(got), got[0]))
        else:
            if got:
                print("  ❌ 自证失败：[%s] 应当全绿，实得 %d 项违反：%s"
                      % (name, len(got), got))
                fail += 1
                return
            print("  ✅ 自证：[%s] 全绿（判定器非恒红）" % name)

    print("== visual_layout_audit.py 判定器自证 ==")
    # 三份期望样本必须全绿
    for k in ("normal", "newline", "empty"):
        case("样本-" + k, SAMPLES[k], want_violations=False)

    # 变异样本必须红
    good = SAMPLES["normal"]
    case("M1 字段行出现在主体行之前",
         good.replace("  world://sys/a\n      p = 1", "      p = 1\n  world://sys/a"),
         True, "契约 8")
    case("M2 字段行缩进 4 空格（应 6）",
         good.replace("      p = 1", "    p = 1"), True, "契约 6/9")
    case("M3 分隔线只有 43 个 U+2500",
         good.replace(_R, RULE_CHAR * (RULE_LEN - 1)), True, "契约 3/5")
    case("M4 首行缺 state= 字段",
         good.replace(" state=fnv1a64:057b92d9ea7b8091", ""), True, "契约 1")
    case("M5 摘要行少了尾部字段",
         good.replace("｜动作 0 条｜通告 0 条", ""), True, "契约 4")
    case("M6 值里出现**裸制表符**（未转义）",
         good.replace('"x"', '"x\ty"'), True, "契约 10")
    case("M7 空状态却多出第 5 行",
         SAMPLES["empty"].rstrip("\n") + "\n" + _R + "\n", True, "契约 5")
    case("M8 非空状态却没有主体行",
         "\n".join([_H, TITLE, _R,
                    "  已折叠 2 条事件（最近序号 2）｜动作 0 条｜通告 0 条", _R, ""]),
         True, "契约 6")
    case("M9 文件未以 LF 结尾",
         good.rstrip("\n"), True, "行尾")
    case("M10 混入 CRLF",
         good.replace("\n", "\r\n"), True, "行尾")
    case("M11 混进一行没人认领的文本",
         good.rstrip("\n") + "\n这是一行不属于任何契约的文本\n", True, "契约 6/9")
    case("M12 字段值不是合法 JSON",
         good.replace("      p = 1", "      p = [1,"), True, "契约 7")

    print()
    if fail == 0:
        print("  ✅ 自证通过：12 个变异全部报红、3 份期望样本全部全绿")
        return 0
    print("  ❌ 自证失败：%d 项" % fail)
    return 1


def main():
    ap = argparse.ArgumentParser(description="视觉投影排版契约的独立审计器")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file", help="渲染输出文件路径")
    src.add_argument("--stdin", action="store_true", help="从标准输入读")
    src.add_argument("--self-test", action="store_true", help="先证明判定器会红")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    if a.file:
        with open(a.file, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    elif a.stdin:
        text = sys.stdin.read()
    else:
        ap.error("必须给 --file / --stdin / --self-test 之一")

    v = audit(text)
    if v:
        print("visual_layout_audit：不通过 —— %d 项排版契约违反" % len(v))
        for x in v:
            print("  ❌ " + x)
        sys.exit(1)
    if not a.quiet:
        lines, _, _ = split_lines(text)
        n_body = sum(1 for x in lines if BODY_RE.match(x))
        n_field = sum(1 for x in lines if FIELD_RE.match(x))
        print("visual_layout_audit：通过 —— 行数 %d，主体行 %d，字段行 %d（独立解析器，"
              "未调用 visual::parse）" % (len(lines), n_body, n_field))
    sys.exit(0)


if __name__ == "__main__":
    main()
