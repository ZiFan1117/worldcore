# -*- coding: utf-8 -*-
'''生成「书 41 节 ↔ 本项目落点」对齐图（**仓外试跑版**；解冻后搬进 `scripts/gen/gen_secmap.py`）。

为什么要有这张图：目标里点名要「**41 节**逐项对齐」，但仓里今天**没有任何一件**把 41 节逐节列出来——
`generated/specmap.json` 的 `srs`（41 条）是**SRS 需求**、与书的 41 节是巧合；`judges` 只落 6 节、`book_gaps` 6 节、`cap_book` 16 节。

**口径（重要，写在图里）**：本图**只机抽四个已登记来源**，一处都不编：
 ① `cap_book`（能力 ↔ 节）② `judges`（§5.6 那张表的判据与颜色）③ `book_gaps`（书里要求、规格零落点）④ `理念条目.md` 的节题与依据栏。
**四源都没有的节，一律如实写「今天没有任何登记」**——那一列就是"逐项对齐"还没做的那一块，**不拿推断填空**。

用法：`python gen_secmap.py [--specmap <path>] [--ruler <path>] [--out <path>]`
'''
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve()


def rl(p: Path):
    return io.open(p, encoding="utf-8", errors="replace").read().split("\n")


# 「词／句边界」集合：句末标点、分句标点、破折号、空白。
# ⚠ **不含 `\`**：切在反斜杠后会把它后面的省略号吃掉（`\|` 是转义竖线，只许切在 `|` 之后）。
# ⚠ **不含 `/`／`／`**：切在斜杠后会留下半个路径 token（实测 `…／BOOK/……`），读的人以为是完整路径。
CLIP_SEPS = "。；！？，、）】》」〕〉：:—–"


def clip(s: str, n: int) -> str:
    """按**词／句边界**截断，截断处**一律加省略号**；找不到边界就不切（**宁长不破词**）。

    为什么不用 `[:n]`：硬切会**断在半句中间**（实测 `节对齐.md` 的「逐节调查」列在
    第 56 字处断在半句中间，读的人拿不到完整意思，也看不出这里被切过）。
    规矩（可机核）：凡是切过的，`……` 前面那个字符**必须是 `CLIP_SEPS` 里的一个**——
    先往左找最近的边界；左边找不到（或太靠前）就往右找到下一个边界；两边都没有就整句留着。
    **不许 `rstrip`**：边界本身是空白时，`rstrip` 会把它抹掉、又把半截词留在末尾（踩过）。
    """
    if len(s) <= n:
        return s
    left = -1
    for k in range(min(n, len(s)) - 1, 0, -1):
        if s[k] in CLIP_SEPS:
            left = k
            break
    if left >= max(1, n // 3):
        return s[: left + 1] + "……"
    for k in range(n, len(s)):
        if s[k] in CLIP_SEPS:
            return s[: k + 1] + "……"
    return s                                       # 通篇没有边界：不切


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--specmap", default=None)
    ap.add_argument("--ruler", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--landing-dir", default=None, help="逐节调查数据目录（`ninedim/01-意图环/03-设计/设计-落点/`）")
    a = ap.parse_args()
    # ★ 仓根按**脚本自身位置**推（本文件在 `scripts/gen/` ⇒ 上两级）
    repo = HERE.parent.parent.parent
    sm_p = Path(a.specmap) if a.specmap else repo / "generated/specmap.json"
    ru_p = Path(a.ruler) if a.ruler else repo / "ninedim/01-意图环/01-策划/策划-尺子-理念条目.md"
    out_p = Path(a.out) if a.out else repo / "generated/节对齐.md"
    land_d = Path(a.landing_dir) if a.landing_dir else repo / "ninedim/01-意图环/01-策划/落点"

    # 逐节调查（**与机抽四源分开**）：从 `节落点/*.md` 里抽每节的 `**判定**：…`
    landing = {}
    if land_d.is_dir():
        for f in sorted(land_d.glob("*.md")):
            cur = None
            for ln in rl(f):
                m = re.match(r"^###\s*(\d+\.\d+)\s", ln)
                if m:
                    cur = m.group(1)
                    continue
                m2 = re.match(r"^-\s*\*\*判定\*\*：(.+)$", ln.strip())
                if m2 and cur:
                    landing[cur] = m2.group(1).strip()

    sm = json.load(io.open(sm_p, encoding="utf-8"))
    sm_sha = hashlib.sha256(sm_p.read_bytes()).hexdigest()
    gen_sha = hashlib.sha256(HERE.read_bytes()).hexdigest()

    # ① 书的节（六章正文章节；序不计入 41）
    secs = []
    for ch in sm["chapters"]:
        if ch["chap"] == "序":
            continue
        for s in ch["secs"]:
            secs.append((ch["chap"], s["num"], s["title"], s.get("line")))

    # ② 尺子：41 节的节题与依据栏（`| 节号 | 这一节只讲一件事 | 依据（核过） |`）
    ruler = {}
    for ln in rl(ru_p):
        m = re.match(r"^\|\s*(\d+\.\d+)\s*\|(.+?)\|(.+?)\|\s*$", ln)
        if m:
            ruler[m.group(1)] = (m.group(2).strip(), m.group(3).strip())

    # ③ 四源
    judges = {}
    for j in sm["judges"]:
        judges.setdefault(j["sec"], j)
    gaps = {g["num"]: g for g in sm["book_gaps"]}
    capbook = {}
    for cap, ss in sm["cap_book"].items():
        for s in ss:
            capbook.setdefault(s, []).append(cap)

    # ④ 出图
    L = []
    L.append("# 书 41 节 ↔ 本项目落点（**机抽**，不手编）")
    L.append("")
    L.append("> **这张图是什么**：把《语义世界》六章正文的 **41 节**逐节列出，并写下**今天已登记的落点**。")
    L.append("> **它不做什么**：**不做推断**。四源（能力映射／§5.6 判据／书里要求但规格零落点／尺子的依据栏）都没有的节，")
    L.append("> 一律写「**今天没有任何登记**」——那一列就是「逐项对齐」**还没做**的那一块。")
    L.append("> **另有一列「逐节调查」**，它来自 `ninedim/01-意图环/03-设计/设计-落点/` 的人工/调查结论，**与机抽四源分开**：")
    L.append("> **机抽的归机抽、调查的归调查，两者不许互相冒充**；调查没做的节写「**未调查**」。")
    L.append(">")
    L.append("> **为什么需要它**：目标里点名要「41 节逐项对齐」，而仓里此前**没有任何一件**逐节列出。")
    L.append("> `generated/specmap.json` 的 `srs`（41 条）是 **SRS 需求**、与书的 41 节是**巧合**；`judges` 落 6 节、`book_gaps` 6 节、`cap_book` 16 节。")
    L.append("")
    L.append("**来源与坐标**：`generated/specmap.json` 的 sha256 `%s…`｜生成器 `scripts/gen/gen_secmap.py` 的 sha256 `%s…`"
             % (sm_sha[:16], gen_sha[:16]))
    L.append("")
    L.append("| 节 | 这一节只讲一件事（尺子） | 能力映射（`cap_book`） | §5.6 判据（`judges`） | "
             "书里要求·规格零落点（`book_gaps`） | **逐节调查**（`ninedim/01-意图环/03-设计/设计-落点/`） | 依据栏（尺子） |")
    L.append("|---|---|---|---|---|---|---|")
    none_n = 0
    for _chap, num, title, _line in secs:
        rt, re_ = ruler.get(num, (title, "—"))
        caps = "、".join(capbook.get(num, [])) or "—"
        j = judges.get(num)
        jt = ("%s：%s" % (j.get("color", ""), j.get("conclusion", ""))) if j else "—"
        g = gaps.get(num)
        gt = g.get("why", "—") if g else "—"
        if caps == "—" and jt == "—" and gt == "—":
            none_n += 1
        land = landing.get(num, "**未调查**")
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            num, rt.replace("|", "\\|")[:52], caps,
            jt.replace("|", "\\|")[:34], gt.replace("|", "\\|")[:26],
            clip(land.replace("|", "\\|"), 100), re_.replace("|", "\\|")[:30]))
    L.append("")
    L.append("**★ 四源都没有登记的节数 = %d / %d**（这些节今天既没有能力映射、也没有 §5.6 判据、也没有登记为缺口）。"
             % (none_n, len(secs)))
    L.append("⇒ 「41 节逐项对齐」**尚未完成的部分就是这些节**：要给它们逐节写下「落在哪、凭什么」，"
             "**不能靠推断**——那需要逐节去看那一节的正文与项目产物。")
    L.append("")

    out_p.parent.mkdir(parents=True, exist_ok=True)
    io.open(out_p, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("写出：%s" % out_p)
    print("节数 = %d（六章正文）｜四源全无登记的 = %d" % (len(secs), none_n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
