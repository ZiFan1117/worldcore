#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 把当前本体（已从声明件装出来的）导回声明件 —— **生成物／一致性检查**（2026-10-19）。

★ 定义方式抄借书平台之后：**`src/ontology/world.json` 是唯一权威载体**，本件不再"引导"定义；
  它只做两件事：
  · 导出当前装载出来的法（生成物，供复核／diff）；
  · `--check`：**声明件 ≡ 运行中的法**（不一致 ⇒ rc=1；说明有人手改了代码或法没同步）。

用法：
  python scripts/release/export-law.py            # 写 src/ontology/world.json（生成物）
  python scripts/release/export-law.py --check    # 只比对，不写
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "src", "ontology", "world.json")
for _p in (os.path.join(ROOT, "src", "ontology"), os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from law.ontology_definition import build_aios_ontology  # noqa: E402
from law.law_dump import dump_law  # noqa: E402


def main(argv):
    if os.environ.get("AIOS_SYSKNIFE_MAP") is None:
        cand = os.path.join(ROOT, "scripts", "release", "computer", "sysknife-command-map.json")
        if os.path.exists(cand):
            os.environ["AIOS_SYSKNIFE_MAP"] = cand
    law = dump_law(build_aios_ontology())
    text = json.dumps(law, ensure_ascii=False, indent=2) + "\n"
    if "--check" in argv:
        cur = open(OUT, "r", encoding="utf-8").read()
        ok = cur == text
        print("=== 声明件 ≡ 运行中的法：%s ===" % ("一致" if ok else "不一致"))
        if not ok:
            print("  （跑 `python scripts/release/export-law.py` 重新导出；先确认法是人改过的）")
        return 0 if ok else 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("★ 写出 %s（%.1f KB；类 %d／接口 %d／关系 %d／动作 %d／函数 %d）"
          % (OUT, len(text.encode("utf-8")) / 1024.0, len(law["object_types"]),
             len(law["interfaces"]), len(law["links"]), len(law["actions"]),
             len(law["functions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
