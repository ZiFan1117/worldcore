#!/usr/bin/env python3
"""C13 —— **一套词表**：我方内核的代码里不许出现**它方词表的标识符**。

红＝ `crates/aios-worldcore/src/**/*.rs` 的**代码**里（注释不算）出现下列任一标识符：
  privacy_class／PointerKind／VersionState／ResolutionError／NamespacePath／FsEvidenceLog／
  ReceiptBuilder／QuarantineEntry／ObjectKind／PointerMoveOp／WalEntry／ConsistencyClass／
  FsSnapshot／ChunkId／EvidenceReceipt／NamespaceCatalog。

为什么（口径来源）：
· ★ 作者 2026-10-15 逐字：「**我们的本体里头的命名体系…都是一致的呀，或者是没有交集**」；
· ★ 这正是我们一直在做的：**学它的理念、用我们的名字**（Marking／Ceiling／Lifecycle／Pointer／
  RecoveryMode…），★ **不引第二套词表** ⇒ 也就不需要别名表、不需要对照表。
· ★ 引它的「原话」写在**注释**里是允许的（那是引文）；★ 拿它的**名字**当类型用不行。
  ⇒ 本判据只扫**代码**（去注释）—— ★ 这条是照 C11 那次**假红**的教训定的。

用法：
  python verify/c13_one_vocabulary.py              跑真仓库
  python verify/c13_one_vocabulary.py --self-test  反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.join("crates", "aios-worldcore", "src")
BANNED = ("privacy_class", "PointerKind", "VersionState", "ResolutionError", "NamespacePath",
          "FsEvidenceLog", "ReceiptBuilder", "QuarantineEntry", "ObjectKind", "PointerMoveOp",
          "WalEntry", "ConsistencyClass", "FsSnapshot", "ChunkId", "EvidenceReceipt",
          "NamespaceCatalog")
NAME = "C13 一套词表"


def code_only(text):
    """★ 只留**代码**（注释行去掉）—— 引它的原话在注释里是允许的。"""
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith(("//", "*", "/*"))
    )


def judge(sources):
    """纯函数：[(件名, 文本)] ⇒ [(件名, 命中的它方标识符)]。"""
    hits = []
    for where, text in sources:
        body = code_only(text)
        for word in BANNED:
            if word in body:
                hits.append((where, word))
    return hits


def self_test():
    cases = [
        ("反例1 代码里用了它的类型名",
         len(judge([("a.rs", "let k = PointerKind::Current;")])), 1),
        ("反例2 代码里用了它的字段名",
         len(judge([("a.rs", 'let x = obj["privacy_class"];')])), 1),
        ("负控 引文写在注释里 ⇒ 不算",
         len(judge([("a.rs", "// 它原话：message Pointer { PointerKind kind; }")])), 0),
        ("正控 用我们自己的名字 ⇒ 不算",
         len(judge([("a.rs", "pub enum Marking { Public, Internal, Confidential }")])), 0),
    ]
    bad = [(n, g, w) for n, g, w in cases if g != w]
    if bad:
        for n, g, w in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, w, g))
        return 1
    print("  [SELF-TEST OK] 反例 2 条；负控 1 条；正控 1 条")
    return 0


def collect():
    out = []
    for base, _dirs, files in os.walk(ROOT):
        for name in sorted(files):
            if not name.endswith(".rs"):
                continue
            path = os.path.join(base, name)
            with open(path, "r", encoding="utf-8") as fh:
                out.append((path, fh.read()))
    return out


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        sources = collect()
    except OSError as exc:
        print("  [ENV] 读不到源码：%s（环境问题，不是判断）" % exc)
        return 2
    hits = judge(sources)
    print("  现取：扫 %d 件；它方词表标识符出现在代码里 %d 处" % (len(sources), len(hits)))
    if hits:
        print("  [RED] 我方代码里出现了它方词表的标识符（引了第二套词表）：")
        for where, word in hits:
            print("        %s ： %s" % (where, word))
        return 1
    print("  [GREEN] 只有一套词表：我方代码里 0 处它方标识符")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
