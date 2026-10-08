#!/usr/bin/env python3
"""门禁工具：**纯文本审计**（`REQ-N-001` / AC-07）。

## 为什么需要它

`REQ-N-001`（语言无关）与 `AC-07`（纯文本审计）此前**没有任何会失败的检查**——
只靠"账本能被 `jq` 读"这一事实。`WC-TP-001` §五 缺口 7 正是这一条。
本脚本把它变成**可失败**的：一旦账本/词表/策略/投影里出现二进制或非法字节，即 rc=1。

## 判据（刻意保守）

对每个被审文件：
1. 必须是**合法 UTF-8**（否则 `UnicodeDecodeError` → 不合格）；
2. 不得含 **NUL**（`\\x00`）——纯文本里出现 NUL 基本可断定是二进制内容；
3. 不得含除 `\\n` `\\t` 之外的控制字符（`C0` 与 `DEL`）；
4. 每一行（非空）必须能按 JSON 解析——**仅对 `.jsonl`/`.csv` 之外的行式文件施加**；
   实际做法：对 `.jsonl` 逐行 `json.loads`。

## 用法

    python3 scripts/verify/plain_text_audit.py <文件或目录> [<更多…>]     # 目录会递归扫已知文本类型
    python3 scripts/verify/plain_text_audit.py --self-test                 # 正/反例自证（无需外部文件）

退出码：0 = 全部合格；1 = 有不合格文件；2 = 用法错误。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Iterable, List, Tuple


def make_console_encoding_safe() -> None:
    r"""让本脚本在**非 UTF-8 控制台**（Windows 默认 GBK/cp936）下**不再崩溃**。

    病灶（2026-09-27 实测）：本脚本的判据标记含 `✅`(U+2705)/`❌`(U+274C)，
    GBK 编不出 ⇒ `print()` 抛 `UnicodeEncodeError` ⇒ **rc=1 假失败**。
    修法（取题目所给两案中的 ②）：把 **`stdout`** 的 `errors` 重配为 `replace`（**不改 encoding**）
    ⇒ GBK 下中文仍按 GBK 输出、只有编不出的符号降级为 `?`，**判据文字一字不删**；UTF-8 下逐字节等价。
    ⚠ **`stderr` 不动**：Python 3.5+ 起 `sys.stderr` 默认就是 `backslashreplace`（本来就不崩、
    且保留字符身份）；改成 `replace` 反而把可复原的 `\u2705` 变成不可复原的 `?`（信息更少），故不改。
    不取 ①（逐字符换 ASCII）的理由见 `scripts/verify/trace_matrix.py` 同名函数：白名单会随新符号复发。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:  # 非 TextIOWrapper（被捕获/重定向）时跳过
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):  # pragma: no cover - 不可重配的流
        pass

TEXT_SUFFIXES = (".jsonl", ".json", ".csv", ".md", ".txt")
SKIP_DIRS = {".git", "target", "node_modules", "__pycache__"}


def audit_bytes(raw: bytes) -> Tuple[bool, str]:
    """审一段字节；返回 (是否合格, 原因)。"""

    # ★ 2026-09-28 补（cover-* 12.6 / A-6）：**放行 UTF-8 BOM 是缺陷**。
    #   BOM 是**编码标记**、不是文本内容，但它会：① 让"逐行比对"类工具把第一行读成带字节的东西；
    #   ② 让不同工具对同一份文件算出不同哈希。⇒ 一律拒。
    if raw.startswith(b"\xef\xbb\xbf"):
        return False, "带 UTF-8 BOM（\ufeff）：BOM 是编码标记、不是内容，它会让逐行比对与哈希对不上 —— 去掉即可"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return False, f"不是合法 UTF-8：{exc}"

    if "\x00" in text:
        return False, "含 NUL 字节（纯文本里出现 NUL 通常意味着二进制内容）"

    bad = [
        (i, c)
        for i, c in enumerate(text)
        if c not in "\n\t" and (ord(c) < 0x20 or ord(c) == 0x7F)
    ]
    if bad:
        pos, ch = bad[0]
        return False, f"含控制字符 U+{ord(ch):04X}（位置 {pos}）"

    return True, "ok"


def audit_jsonl(raw: bytes) -> Tuple[bool, str]:
    """逐行 JSON 校验（只用于 .jsonl）。"""
    ok, why = audit_bytes(raw)
    if not ok:
        return ok, why
    for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            return False, f"第 {n} 行不是合法 JSON：{exc}"
    return True, "ok"


def iter_targets(paths: Iterable[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in sorted(files):
                    if name.endswith(TEXT_SUFFIXES):
                        out.append(os.path.join(root, name))
        else:
            out.append(p)
    return out


def self_test() -> int:
    # ★ 反例（cover-* 12.6）：带 BOM 必须判红
    _ok, _why = audit_bytes(b"\xef\xbb\xbf# BOM title\n")
    print("[self-test/12.6] 带 UTF-8 BOM ⇒ 应判红：%s（%s）" % (not _ok, _why))
    if _ok:
        print("  ⇒ 自证失败：带 BOM 的文件竟被放行")
        return 1
    """正/反例自证：**没有反例的自测等于没测**（本项目的一条老教训）。"""
    cases = [
        (b'{"a":1}\n', True, "正常 JSONL"),
        ("世界核心\n".encode("utf-8"), True, "正常中文文本"),
        (b'{"a":1}\x00\n', False, "含 NUL"),
        (b'{"a":"\x07"}\n', False, "含控制字符"),
        (b'\xff\xfe\x00\x01', False, "非法 UTF-8"),
    ]
    failed = 0
    for raw, want_ok, desc in cases:
        got_ok, why = audit_bytes(raw)
        mark = "✅" if got_ok == want_ok else "❌"
        if got_ok != want_ok:
            failed += 1
        print(f"  {mark} {desc}: 期望合格={want_ok} 实得={got_ok}（{why}）")

    # 行式文件的额外判据
    got_ok, why = audit_jsonl(b'{"a":1}\nnot json\n')
    mark = "✅" if not got_ok else "❌"
    if got_ok:
        failed += 1
    print(f"  {mark} JSONL 坏行应被拒：实得合格={got_ok}（{why}）")

    print(f"自证结论：{'通过' if failed == 0 else f'{failed} 项不符'}")
    return 0 if failed == 0 else 1


def main(argv: List[str]) -> int:
    make_console_encoding_safe()

    if not argv:
        print(__doc__.split("## 用法")[1].strip(), file=sys.stderr)
        return 2
    if argv[0] == "--self-test":
        return self_test()

    bad: List[Tuple[str, str]] = []
    targets = iter_targets(argv)
    if not targets:
        print("[WARN] 没有匹配到任何待审文件——**未校验**不得当作通过", file=sys.stderr)
        return 1

    for path in targets:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            bad.append((path, f"无法读取：{exc}"))
            continue
        ok, why = audit_jsonl(raw) if path.endswith(".jsonl") else audit_bytes(raw)
        if not ok:
            bad.append((path, why))

    print("=" * 70)
    print("门禁校验：纯文本审计（REQ-N-001 / AC-07）")
    print("=" * 70)
    print(f"受审文件: {len(targets)}")
    if bad:
        print(f"\n不合格 {len(bad)} 个：")
        for path, why in bad:
            print(f"  [不合格] {path}\n            {why}")
        print("\n门禁结论：不通过 —— 存在非纯文本内容（语言无关性被破坏）")
        return 1
    print("\n门禁结论：通过 —— 全部为纯文本（UTF-8、无 NUL、无控制字符、JSONL 逐行可解析）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
