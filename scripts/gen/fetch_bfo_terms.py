#!/usr/bin/env python3
"""**BFO 术语薄层生成器** —— 把 BFO 那把"尺"派生成一张**机器可读的类集**。

## 这一件是什么
把 BFO 2020 的**类集**（具名 `owl:Class`）从**本地整包**里取出来，
落成 `scripts/gen/bfo-terms.json` —— 供 **U8** 判「`class ∈ 类集`」。

## 为什么是"派生"而不是"下载"
整包（`.refs/bfo-2020/`）**由 `.refs/` 的写主落**（那是一件独立活，`.refs/` 不入版本控制）；
本件只做**薄层**：**读本地件 → 抽类集 → 落一个 JSON**。⇒ 两件分开，各有一个权威载体。

## 正源（**为什么不是那份 `bfo-2020-terms.csv`**）
现取（2026-10-05）：Lead 原先指的 `documentation/bfo-2020-terms.csv` **不存在**；
真件在 `…/profiles/temporal extensions/temporalized relations/documentation/bfo-2020-terms.csv`
（37268 B／125 行），而它是 **temporalized relations 分册**的表 ——
★**`Site`／`Quality`／`Disposition`／`Role`／`Process` 五个在里面各 0 命中** ⇒
**拿它当"类集"会得出"五个类都不存在"的假结论（假红）**。
⇒ 正源 ＝ **`21838-2/owl/bfo-core.owl`**（BFO 2020 核心，36 个具名 `owl:Class`）。

## ★★ 两条口径（本件最重要的两格）
### ① 名字的比较口径：`casefold_trim`（默认）／`exact`
**同一批名字，两种比法给两个答案**（现取：`Site`…五个按**逐字**比 ⇒ 5/5 不命中；按**大小写归一** ⇒ 5/5 命中，
因为本体里的 label **全是小写**）。⇒ **口径不写下来，同一条判据就有两个答案。**
⇒ 本件把口径 **写进生成物**（`comparison` 段，**声明面**），**不留代码里、更不留信里**；
★**两个口径都进生成物**（`probe` 段各一份）—— 免得读者只看到一个答案。

### ② ★★ 身份口径：**以 IRI 为键，不以 label 为键**（现取逼出来的）
本件交叉核对 OLS4 时现取到：**同一个类在两边有两个 label** ——
```
BFO_0000142  本地 label「fiat line」      ／ OLS4 label「one-dimensional continuant fiat boundary」
BFO_0000146  本地 label「fiat surface」   ／ OLS4 label「two-dimensional continuant fiat boundary」
BFO_0000147  本地 label「fiat point」     ／ OLS4 label「zero-dimensional continuant fiat boundary」
```
⇒ ★**label 不是身份**（它会变、会换措辞）；**IRI 才是**（BFO 的 ID 稳定、且有 OBO 标准形态）。
⇒ 并且 **IRI 本身有兩種写法**：本地 `BFO_0000142`（下划线）↔ OLS4 `BFO:0000142`（冒号）——
**同物异写** ⇒ 比较前**必须归一**（本件 `iri_key()`：取尾段、`:`→`_`、`casefold`）。
⇒ 生成物里因此同时给：**按 label 的差** 与 **按归一 IRI 的差**（两组结论不同 ⇒ **都要给**）。

## 生成物不许手编
要换源／换口径 ⇒ **改本件再重跑**；`bfo-terms.json` 是**生成物**。
用法：
```
python3 scripts/gen/fetch_bfo_terms.py                  # 默认：读本地整包 ＋ 联网交叉核对 OLS4
python3 scripts/gen/fetch_bfo_terms.py --no-network      # 离线：交叉核对记为"未做（原因）"
```
退出码：`0` ＝ 生成成功；`2` ＝ 正源缺失／解析失败（**不静默降级**：没有类集就绝不写一个空的出来）。
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"

# 正源（**本地整包**里的那一个文件）。上游料库不入版本控制 ⇒ 它是外部料、不是交付物。
# ★ 2026-10-06：上游料库已**搬出仓库**（作者指示：这些夹子挡在代码旁边很突兀、且无用）
#   —— `.refs/` 现落 `D:\Code\heavy-archive\worldcore-上游料-2026-10-06\refs\`。
#   本常量随之改为**归档里的绝对位置**；`--owl` 仍可覆盖（例如你把整包放回仓内时）。
DEFAULT_OWL_ABS = os.path.join(
    r"D:\Code\heavy-archive\worldcore-上游料-2026-10-06",
    "refs", "bfo-2020", "21838-2", "owl", "bfo-core.owl")
# 兼容旧写法：仓内相对路径（若整包被放回仓内，这个仍然指得到）。
DEFAULT_OWL_REL = os.path.join("refs", "bfo-2020", "21838-2", "owl", "bfo-core.owl")
# 整包的上游（★逐字记进生成物：这是"这个字节从哪来"的那一半）。
UPSTREAM_URL = "https://codeload.github.com/BFO-ontology/BFO-2020/tar.gz/.refs/heads/master"
# 交叉核对用的镜像（OLS4）。★它不是正源：正源是本地件（可算 sha）；它是**第二坐标**。
OLS4_URL = "https://www.ebi.ac.uk/ols4/api/ontologies/bfo/terms?size=500&page=0"

# ★ 要逐个判的那五个类（Lead 点名）。**大小写按下标给的写法写**——
#   它们**故意**与本体里的 label 大小写不同，好让"口径"这件事**当场显形**。
PROBE_NAMES = ["Site", "Quality", "Disposition", "Role", "Process"]


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def safe_rel(path, base):
    """**安全的相对路径**：不同盘符时 `os.path.relpath` 会抛 `ValueError`（实测踩过）⇒ 退回绝对路径。

    ★ 血泪：第一版直接 `os.path.relpath(out, repo)`，而"输出落在 C: 临时目录、仓在 D:"时
    抛 `ValueError: path is on mount 'C:', start on mount 'D:'` ⇒ **整个生成器崩在最后一行打印上**
    （文件已写成功，却以 rc=1 结束）。⇒ 路径换算**不是**核心逻辑，**不许**让它决定成败。
    """
    try:
        return os.path.relpath(path, base).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def iri_key(iri):
    """**IRI 的归一形态**——用作"身份"的键。

    ★ 为什么必须归一：现取到**同物异写** —— 本地 `BFO_0000142`（下划线）／OLS4 `BFO:0000142`（冒号）。
    ★ 口径：取最后一段 → `:`／`#` 一律换成 `_` → `casefold()`。
    """
    if not iri:
        return ""
    tail = iri.replace("#", "/").rsplit("/", 1)[-1]
    return tail.replace(":", "_").strip().casefold()


def parse_owl(path):
    """从 RDF/XML 里取**具名** `owl:Class` 的 `{iri: label}`（并数一数属性）。

    ★ **不用正则**：第一版试过正则，`rdfs:label` 嵌在不同层级 ⇒ **取到 0 条**
    （而"0 条"最容易被读成"本体里没有"）。⇒ 走 `xml.etree` 正规解析。
    """
    root = ET.parse(path).getroot()
    by_iri = {}
    props = 0
    for el in root.iter():
        about = el.get(RDF + "about")
        if not about:
            continue
        if el.tag == OWL + "Class":
            lab = el.find(RDFS + "label")
            if lab is not None and lab.text:
                by_iri[about] = lab.text
        elif el.tag in (OWL + "ObjectProperty", OWL + "DatatypeProperty"):
            props += 1
    return by_iri, props


def probe(names, label_to_iri, mode):
    """按 `mode` 口径逐个判「在不在类集里」。`mode` ∈ {`exact`, `casefold_trim`}。

    ★ 两条口径**都要给读数**：只给一条，读者就永远不知道另一条会怎么说。
    """
    table = {}
    for iri, lab in label_to_iri.items():
        key = lab if mode == "exact" else lab.strip().casefold()
        table[key] = (lab, iri)
    out = {}
    for n in names:
        key = n if mode == "exact" else n.strip().casefold()
        got = table.get(key)
        out[n] = {"hit": got is not None,
                  "label": got[0] if got else None,
                  "iri": got[1] if got else None}
    return out


def ols4_cross_check(names):
    """**第二坐标**：问 OLS4（逐字记 URL／时点／HTTP 状态；**取不到就如实记取不到**）。

    ★ 为什么要它：同一批判定在**两个来源**上各给一遍 —— 若结论不同，那是**发现**，不是噪声。
    ★ **不许**静默跳过：网络不可达 ⇒ `http_status` 记"不可达（原因）"，**不写成 0 条**。
    """
    rec = {
        "url": OLS4_URL, "at": datetime.datetime.now().astimezone().isoformat(),
        "http_status": None, "count": None, "note": "",
        "by_iri": None, "probe": None, "probe_casefold_trim": None,
    }
    try:
        req = urllib.request.Request(OLS4_URL, headers={"User-Agent": "bfo-terms"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            rec["http_status"] = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
        by_iri = {t["obo_id"]: t["label"] for t in payload.get("_embedded", {}).get("terms", [])
                  if t.get("obo_id") and t.get("label")}
        rec["count"] = len(by_iri)
        rec["by_iri"] = dict(sorted(by_iri.items()))
        rec["probe"] = probe(names, by_iri, "exact")
        rec["probe_casefold_trim"] = probe(names, by_iri, "casefold_trim")
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["note"] = "HTTP 错误：%s" % e.reason
    except Exception as e:  # 网络不可达／超时／非 JSON
        rec["http_status"] = "不可达"
        rec["note"] = "%s: %s" % (type(e).__name__, e)
    return rec


def main():
    ap = argparse.ArgumentParser(description="生成 BFO 类集薄层（bfo-terms.json）")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    help="仓库根（默认：本文件的上两级目录）")
    ap.add_argument("--owl", default=None, help="正源 owl 文件（缺省：先看仓内 .refs/…，再看归档 worldcore-上游料-2026-10-06/.refs/…）")
    ap.add_argument("--out", default=None, help="生成物路径（默认 scripts/gen/bfo-terms.json）")
    ap.add_argument("--no-network", action="store_true", help="跳过 OLS4 交叉核对（如实记'未做'）")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    # 缺省正源：先看**仓内**旧位置（整包被放回仓内时仍适用），没有就落到**归档**里那份。
    _in_repo = os.path.join(repo, DEFAULT_OWL_REL)
    owl = a.owl or (_in_repo if os.path.isfile(_in_repo) else DEFAULT_OWL_ABS)
    out = a.out or os.path.join(repo, "scripts", "gen", "bfo-terms.json")

    if not os.path.isfile(owl):
        print("[FAIL] 正源不存在：%s" % owl, file=sys.stderr)
        print("       处置：先让 `.refs/` 的写主落整包（本件只做薄层，不下载）。", file=sys.stderr)
        return 2
    try:
        by_iri, props = parse_owl(owl)
    except ET.ParseError as e:
        # ★ **不静默降级**：源不是 OWL ⇒ 明确失败，**绝不**写一个空类集出来。
        print("[FAIL] 正源不是可解析的 RDF/XML（拿错文件了？）：%s" % owl, file=sys.stderr)
        print("       原始错误：%s" % e, file=sys.stderr)
        print("       处置：正源应是 `21838-2/owl/bfo-core.owl`；说明文字／对照表（如分册的 terms csv）不是类集。",
              file=sys.stderr)
        return 2
    if not by_iri:
        # ★ 空集不许写成"没有类"：**不静默降级**。
        print("[FAIL] 正源里一个带 label 的具名 owl:Class 都没取到：%s" % owl, file=sys.stderr)
        print("       处置：核源文件——'取到 0 条'最容易被误读成'本体里没有'。", file=sys.stderr)
        return 2

    local_norm = {iri_key(k): v for k, v in by_iri.items()}
    cross = {"skipped": True, "why": "命令行给了 --no-network"}
    if not a.no_network:
        full = ols4_cross_check(PROBE_NAMES)
        cross = {k: v for k, v in full.items() if k != "by_iri"}
        if isinstance(full.get("by_iri"), dict):
            ols_norm = {iri_key(k): v for k, v in full["by_iri"].items()}
            # ★ 两组结论**都给**：按 label 的差 与 按归一 IRI 的差 —— 它们不是同一件事。
            cross["diff_by_label"] = {
                "only_in_local": sorted(set(by_iri.values()) - set(full["by_iri"].values())),
                "only_in_ols4": sorted(set(full["by_iri"].values()) - set(by_iri.values())),
            }
            cross["diff_by_iri"] = {
                "only_in_local": sorted(set(local_norm) - set(ols_norm)),
                "only_in_ols4": sorted(set(ols_norm) - set(local_norm)),
                "same_iri_different_label": sorted(
                    [{"iri_key": k, "local_label": local_norm[k], "ols4_label": ols_norm[k]}
                     for k in set(local_norm) & set(ols_norm) if local_norm[k] != ols_norm[k]],
                    key=lambda x: x["iri_key"]),
            }
            same = cross["diff_by_iri"]["same_iri_different_label"]
            cross["verdict"] = (
                "按归一 IRI 看：两边**逐条相同**" if not cross["diff_by_iri"]["only_in_local"]
                and not cross["diff_by_iri"]["only_in_ols4"] and not same
                else "★**两个来源不同**：`diff_by_label` 与 `diff_by_iri` **都要看** —— "
                     "★尤其 `same_iri_different_label`（**同一个类、两个 label**）⇒ ★**label 不是身份，IRI 才是**")
            cross["by_iri"] = full["by_iri"]

    doc = {
        "schema": "bfo-terms/1",
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "generator": "scripts/gen/fetch_bfo_terms.py",
        "taken_from": "本地整包 .refs/bfo-2020/21838-2/owl/bfo-core.owl@%s" % sha256_file(owl)[:12],
        "source": {
            "kind": "local_package",
            "path": safe_rel(owl, repo),
            "bytes": os.path.getsize(owl),
            "sha256": sha256_file(owl),
            "upstream_url": UPSTREAM_URL,
            "why_this_source": (
                "选 `bfo-core.owl` 作正源：它是 BFO 2020 的**核心类集**（具名 `owl:Class`，只有类、没有关系）。"
            ),
            "the_other_candidate": (
                "另一处 `21838-2/owl/profiles/temporal extensions/temporalized relations/documentation/bfo-2020-terms.csv`"
                "（37268 B／122 行／121 个 distinct term）是【分册】的文档表，**类与关系混在一起**"
                "（56 个像关系的 term：`is a`／`continuant part of`／…）。"
                "★★ 更正（2026-10-05）：本席**曾据【大小写敏感】的搜索**误判它"
                "『`Site`/`Quality`/… 各 0 命中』——**那句是错的**：该表里的 term 是**全小写**"
                "（`site`/`quality`/`disposition`/`role`/`process` 都在）。"
                "⇒ 两种源是**两个不同的宇宙**（36 个纯类 ↔ 122 行类＋关系），**取哪个必须声明**。"
            ),
        },
        # ★ 取数端点与 HTTP 状态：本地件**不经 HTTP** ⇒ 如实写"不适用"，不写一个 0 或 200 冒充。
        "endpoint": {"kind": "local_file", "http_status": "不适用（本地件，不经 HTTP）"},
        "comparison": {
            "name_mode_default": "casefold_trim",
            "name_mode_definition": "比较名字前先 `str.strip()`、再 `str.casefold()`（大小写不敏感）；另一条口径是 `exact`（逐字）。",
            "name_mode_why": "同一批名字两种比法给两个答案（本体 label 全小写）⇒ 口径不写下来＝判据没写全。",
            "name_mode_alternatives": ["exact"],
            "identity_key": "iri_key",
            "identity_definition": "身份用 IRI 的归一形态：取尾段 → `:`／`#` 换 `_` → `casefold`（例：`BFO:0000142` 与 `BFO_0000142` 是**同一个**）。",
            "identity_why": "现取逼出来的：**同一个类在两个来源上 label 不同**（见 `cross_check.diff_by_iri.same_iri_different_label`）"
                            "⇒ ★**label 不是身份**；按 label 当键，遇到「同物异名」就会判成两个东西。",
        },
        "class_count": len(by_iri),
        "property_count": props,
        "classes": dict(sorted(by_iri.items())),
        "classes_by_iri_key": dict(sorted(local_norm.items())),
        "probe": {
            "names": PROBE_NAMES,
            "exact": probe(PROBE_NAMES, by_iri, "exact"),
            "casefold_trim": probe(PROBE_NAMES, by_iri, "casefold_trim"),
        },
        "cross_check": cross,
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")

    print("OK  正源 %s（%d 字节，sha256 %s…）" % (doc["source"]["path"], doc["source"]["bytes"], doc["source"]["sha256"][:12]))
    print("    类集 %d 个（属性 %d 个）→ %s" % (doc["class_count"], doc["property_count"], safe_rel(out, repo)))
    for n in PROBE_NAMES:
        e = doc["probe"]["exact"][n]
        c = doc["probe"]["casefold_trim"][n]
        print("    %-12s exact=%-5s casefold_trim=%-5s iri=%s" % (n, e["hit"], c["hit"], c["iri"] or "-"))
    if not cross.get("skipped"):
        print("    交叉核对 OLS4：http=%s count=%s" % (cross.get("http_status"), cross.get("count")))
        if "diff_by_iri" in cross:
            d = cross["diff_by_iri"]
            print("      only_in_local(iri)=%s" % d["only_in_local"])
            print("      only_in_ols4(iri) =%s" % d["only_in_ols4"])
            print("      same_iri_diff_label=%d 组" % len(d["same_iri_different_label"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
