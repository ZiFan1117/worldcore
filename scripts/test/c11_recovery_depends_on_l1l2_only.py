#!/usr/bin/env python3
"""C11 —— **恢复面只依赖 L1／L2**（H10 的机器判据）。

红＝下列任一条成立：
  ① 恢复出口 crates/aios-worldcore/src/engine/recovery.rs 里出现**L3+ 件**的名字
     （aios_cognitive／aios_renderer／kde／webkit／tauri／gtk／aios_ui）；
  ② 我方内核的 Cargo.toml 依赖里出现同一批名字。

为什么（口径来源）：
· ★ 来源1-⑨.1 逐字：01_object_model.md:390-400「The recovery path depends on **L1 and L2 only**.
  No L3+ services, no LLM, no Web UI, no KDE session.」；
· ★ 来源1-⑨.3 第 3 条逐字：「**一条今天就能立的总判据**：在恢复出口的依赖闭包里搜
  aios-cognitive／aios-renderer-*／kde／web，命中 ⇒ 红（★ 今天就能绿，而且**真的能红**）」。
· ★ 本判据就是那条；★ **射程**＝恢复出口的 use ＋ 内核的依赖表（不扫全 workspace）。

用法：
  python verify/c11_recovery_depends_on_l1l2_only.py              跑真仓库
  python verify/c11_recovery_depends_on_l1l2_only.py --self-test  反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RECOVERY = os.path.join("crates", "aios-worldcore", "src", "engine", "recovery.rs")
CARGO = os.path.join("crates", "aios-worldcore", "Cargo.toml")
BANNED = ("aios_cognitive", "aios-renderer", "aios_renderer", "kde", "webkit", "tauri", "gtk", "aios_ui")
NAME = "C11 恢复面只依赖 L1/L2"


def code_only(text):
    """★ 只留**代码**：注释行一律去掉。

    ★ 为什么（2026-10-15 实测踩过）：恢复出口的**件头注释里就逐字引着**那条理念，里面带
    「KDE session」那个词 ⇒ 若把注释也算进来，本判据**第一跑就假红**。
    ★ 判据的射程是**依赖闭包**（真引用了谁），不是「文件里提到过谁」。
    """
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("*") or s.startswith("#"):
            continue
        out.append(line)
    return "\n".join(out)


def deps_only(text):
    """Cargo.toml 只取 [dependencies] 那一节（别把 description 里的字也算进来）。"""
    out, inside = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            inside = s == "[dependencies]"
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def judge(sources):
    """纯函数：[(来源名, 文本)] ⇒ [(来源名, 命中的禁词)]。

    ★ 认 .rs 与 Cargo.toml 两种：前者去注释，后者只取 [dependencies]。
    """
    hits = []
    for where, text in sources:
        body = deps_only(text) if where.endswith(".toml") else code_only(text)
        low = body.lower()
        for word in BANNED:
            if word in low:
                hits.append((where, word))
    return hits


def self_test():
    cases = [
        ("反例1 恢复出口引了认知件",
         judge([("recovery.rs", "use aios_cognitive::translator_engine::Gate;")]), 1),
        ("反例2 依赖表里挂上渲染器",
         judge([("Cargo.toml", "[dependencies]\naios-renderer-voice = { path = '../aios-renderer-voice' }")]), 1),
        ("正控 只用我方两层 ⇒ 0",
         judge([("recovery.rs", "use crate::engine::store::Store;")]), 0),
        ("反例3 引用写在**注释**里不算（防假红；件头就引着那条理念）",
         judge([("recovery.rs", "//! No L3+ services, no LLM, no Web UI, no KDE session.")]), 0),
        ("反例4 Cargo.toml 的 description 里提到也不算",
         judge([("Cargo.toml", '[package]\ndescription = "无 kde"\n\n[dependencies]\nserde_json = { workspace = true }')]), 0),
    ]
    bad = [(n, len(g), w) for n, g, w in cases if len(g) != w]
    if bad:
        for n, g, w in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, w, g))
        return 1
    print("  [SELF-TEST OK] %d 条用例全部符合预期（含防假红的两条负控）" % len(cases))
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    sources = []
    try:
        for path in (RECOVERY, CARGO):
            with open(path, "r", encoding="utf-8") as fh:
                sources.append((path, fh.read()))
    except OSError as exc:
        print("  [ENV] 读不到被扫件：%s（环境问题，不是判断）" % exc)
        return 2
    hits = judge(sources)
    print("  现取：被扫 %d 件（%s）" % (len(sources), "、".join(os.path.basename(p) for p, _ in sources)))
    if hits:
        print("  [RED] 恢复面的依赖闭包里出现 L3+ 件：")
        for where, word in hits:
            print("        %s ： %s" % (where, word))
        return 1
    print("  [GREEN] 恢复面只依赖我方两层（无 LLM／渲染器／桌面／网络）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
