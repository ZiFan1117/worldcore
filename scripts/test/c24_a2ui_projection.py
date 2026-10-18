#!/usr/bin/env python3
"""C24 —— **界面由本体投影出来，且元件必须全在 A2UI 的白名单里**（T-247）。

★ 作者口径（逐字）：
  · 「按照他们的理念，我们要生成这个，就是 GUI，按照他们的理念」；
  · 「不是说是把本体变为 A2UI 这个生成器……软件会执行动作、函数，它会生成 A2UI」⇒ 运行时的产出。

★ 本仓「不许借」第 13 条（逐字）：只借 A2UI 的「目录白名单 ＋ 没相容目录就不发」。

红＝
  (a) engine/project.rs 没有 project(（没有投影面）⇒ 红；
  (b) 它没有从 catalog 取元件清单（components／catalogId）⇒ 红；
  (c) ★★ 白名单外不是【拒】而是【静默过滤】⇒ 红
      —— 过滤会把「目录不对」藏起来；本仓要求整帧拒；
  (d) catalog 数据件不在（crates/aios-ontology/data/a2ui-catalog-basic.json）⇒ 红。

限度（★ 如实）：判文本 ⇒ 行为靠 VM 的 cargo test。

用法：
  python verify/c24_a2ui_projection.py              跑真仓库
  python verify/c24_a2ui_projection.py --self-test   反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJ = os.path.join("crates", "aios-worldcore", "src", "engine", "project.rs")
CAT = os.path.join("crates", "aios-ontology", "data", "a2ui-catalog-basic.json")
NAME = "C24 本体投影到 A2UI（元件必须在白名单里）"


def scan(proj_text, cat_exists):
    bad = []
    if proj_text is None:
        return ["engine/project.rs：不在"]
    if "pub fn project(" not in proj_text:
        bad.append("project.rs：没有 project(（没有投影面）")
    if "catalogId" not in proj_text or "\"components\"" not in proj_text:
        bad.append("project.rs：没有从 catalog 取元件清单（components／catalogId）")
    if "白名单" not in proj_text:
        bad.append("project.rs：没有白名单这一格")
    if "return Err(" not in proj_text:
        bad.append("project.rs：没有【拒】的路径（可能在静默过滤）")
    if not cat_exists:
        bad.append("catalog 数据件不在：" + CAT)
    return bad


def run(label="真仓库"):
    text = None
    if os.path.exists(PROJ):
        with open(PROJ, "r", encoding="utf-8") as f:
            text = f.read()
    bad = scan(text, os.path.exists(CAT))
    print("=== %s（%s）===" % (NAME, label))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0


GOOD = (
    "pub fn project(\n"
    "  let allowed = whitelist(catalog_json);  // 白名单\n"
    "  let cid = catalogId;\n"
    "  let comps = \"components\";\n"
    "  if !allowed { return Err(x); }\n"
    ")"
)


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    b1 = scan(GOOD.replace("return Err(x);", "// 什么都不做"), True)
    print("=== 红例1（白名单外不拒）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    b2 = scan(GOOD, False)
    print("=== 红例2（catalog 不在）⇒ 命中 %d 处 ===" % len(b2))
    if not any("catalog" in x for x in b2):
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
