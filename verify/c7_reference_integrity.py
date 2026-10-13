#!/usr/bin/env python3
"""C7 —— 本体内部**引用完整性**（射程已扩到「所有指向类名的地方」）。

红＝本体里任何**指向类名的引用**，其类名**不在 `objects` 里**，且**未登记在 `verify/c7_known_pending.txt`**。

射程（2026-10-13 扩，承总迁移方案 §四 第 0 步）：
  ① `_storage_class_map.entries.*.ours`
  ② `_property_types.types.*.used_by`（形如 `<类名>.<字段>`）
  ③ `_property_types._P无对应而我方在用的[].字段`
  ④ ★ `_links.<边>.from` / `.to`（★ `_links._comment` 逐字：两端的类型必须已在 `objects` 里声明）
  ⑤ ★ `_actions.<动作>.parameters[].param_type` 里的 `ref(<类名>)`
  ⑥ ★ `_functions.entries.*.inputs.*` 与 `.output_type` 里的 `ref(<类名>)` / 裸类名
  ⑦ ★ `_governance.markings.by_class` 的键
  ⑧ ★ `_modules.assignment._objects._by_entry` 的键
  ⑨ ★ `_standards._adopted` 里形如 `_objects.<类名>` 的键

为什么（来历）：
· 三席评审现取：`_property_types.used_by` 曾有 **24 条**指着已撤回的 6 个类 ⇒ **撤回不彻底，且 C1–C6 没有一条盯它**。
· ★ 初版只盯两张派生表 ⇒ 撤类时**报不全遗漏**；本笔按总迁移方案 §四 把射程扩到九路。
· ★ 本判据**不判「类 vs 值域」**（三席已证三条候选全废）；它只判一件机械可判的事：**引用不许指向不存在的类**。

用法：
  python verify/c7_reference_integrity.py              跑真仓库
  python verify/c7_reference_integrity.py --self-test  反例自检
"""
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONTOLOGY = os.path.join("crates", "aios-ontology", "data", "ontology.json")
PENDING = os.path.join("verify", "c7_known_pending.txt")
NAME = "C7 本体内部引用完整性"
REF_PATTERN = re.compile(r"^ref\(([^)]+)\)$")
BARE_CLASS = re.compile(r"^[a-z][a-z0-9_]*$")


def _from_ref(text):
    """ref(X) ⇒ X；否则 None。"""
    if not isinstance(text, str):
        return None
    m = REF_PATTERN.match(text.strip())
    return m.group(1).strip() if m else None


def _sec(doc, name):
    """取一个节：★ 先看 notes 下、再看顶层（两处都认 —— 名字不决定位置）。"""
    n = doc.get("notes") or {}
    if isinstance(n, dict) and name in n:
        return n[name]
    return doc.get(name)


def refs_of(doc):
    """抽出所有「指向类名」的结构化引用 ⇒ [(引用来源, 类名)]。"""
    out = []
    sm = _sec(doc, "_storage_class_map") or {}
    for k, v in (sm.get("entries") or {}).items():
        ours = (v or {}).get("ours")
        if isinstance(ours, str) and ours:
            out.append(("_storage_class_map." + k, ours))

    pt = _sec(doc, "_property_types") or {}
    for tname, tv in (pt.get("types") or {}).items():
        for entry in ((tv or {}).get("used_by") or []):
            out.append(("_property_types." + tname, str(entry).split(".")[0]))
    for item in (pt.get("_P无对应而我方在用的") or []):
        f = str((item or {}).get("字段", ""))
        if f:
            out.append(("_property_types._P无对应", f.split(".")[0]))

    for edge, body in (doc.get("links") or {}).items():
        if edge.startswith("_") or not isinstance(body, dict):
            continue
        for end in ("from", "to"):
            v = body.get(end)
            if isinstance(v, str) and v:
                out.append(("_links." + edge + "." + end, v))

    for act, body in (doc.get("actions") or {}).items():
        if act.startswith("_") or not isinstance(body, dict):
            continue
        for pm in (body.get("parameters") or []):
            t = _from_ref((pm or {}).get("param_type"))
            if t:
                out.append(("_actions." + act + ".param_type", t))

    for fn, body in ((doc.get("functions") or {}).get("entries") or {}).items():
        for key, val in ((body or {}).get("inputs") or {}).items():
            t = _from_ref(val)
            if t:
                out.append(("_functions." + fn + ".inputs." + str(key), t))
        raw_out = (body or {}).get("output_type")
        t = _from_ref(raw_out)
        if t is None and isinstance(raw_out, str) and BARE_CLASS.match(raw_out.strip()):
            t = raw_out.strip()   # ★ output_type 允许是裸类名（本仓现取即是）
        if t:
            out.append(("_functions." + fn + ".output_type", t))

    for cls in ((doc.get("_governance") or {}).get("markings") or {}).get("by_class") or {}:
        out.append(("_governance.markings.by_class", cls))

    for cls in (((_sec(doc, "_modules") or {}).get("assignment") or {}).get("objects") or {}).get("_by_entry") or {}:
        out.append(("_modules._by_entry", cls))

    for key in (_sec(doc, "_standards") or {}).get("_adopted") or {}:
        if key.startswith("_objects."):
            out.append(("_standards._adopted", key.split(".", 1)[1]))
    return out


def judge(doc, registered=frozenset()):
    """纯函数：返回 [(来源, 类名)] —— 指向 objects 里不存在的类（且未登记）。"""
    known = set(k for k in (doc.get("objects") or {}) if not k.startswith("_"))
    return [(src, cls) for src, cls in refs_of(doc)
            if cls and cls not in known and cls not in registered]


def self_test():
    base = {"objects": {"human": {}, "agent": {}, "record": {}}}
    cases = []
    d1 = dict(base); d1["_storage_class_map"] = {"entries": {"H": {"ours": "human"}, "G": {"ours": "nowhere"}}}
    cases.append(("反例1 映射表", len(judge(d1)), 1))
    d2 = dict(base); d2["_property_types"] = {"types": {"STRING": {"used_by": ["human.name", "gone.field"]}}}
    cases.append(("反例2 派生表", len(judge(d2)), 1))
    d3 = dict(base); d3["links"] = {"part-of": {"from": "notice", "to": "record"}}
    cases.append(("反例3 边端点", len(judge(d3)), 1))
    d4 = dict(base); d4["actions"] = {"notice.mute": {"parameters": [{"param_type": "ref(notice)"}]}}
    cases.append(("反例4 动作参数", len(judge(d4)), 1))
    d5 = dict(base); d5["functions"] = {"entries": {"f": {"inputs": {"s": "ref(notice)"}, "output_type": "notice"}}}
    cases.append(("反例5 函数出入（2 条：inputs 是 ref()，output_type 是裸类名）", len(judge(d5)), 2))
    d6 = dict(base); d6["_governance"] = {"markings": {"by_class": {"notice": "INTERNAL"}}}
    cases.append(("反例6 密级按类", len(judge(d6)), 1))
    d7 = dict(base); d7["_modules"] = {"assignment": {"objects": {"_by_entry": {"notice": ["发生"]}}}}
    cases.append(("反例7 归目", len(judge(d7)), 1))
    d8 = dict(base); d8["_standards"] = {"_adopted": {"_objects.notice": {}}}
    cases.append(("反例8 标准采纳", len(judge(d8)), 1))
    good = dict(base); good["links"] = {"part-of": {"from": "record", "to": "agent"}}
    cases.append(("正控1 边端点都在", len(judge(good)), 0))
    cases.append(("正控2 登记在册可放行", len(judge(d3, frozenset({"notice"}))), 0))
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 8 条（各 1，除第 5 条为 2）；正控 2 条各 0")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        with open(ONTOLOGY, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        print("  [ENV] 读不到本体：%s（环境问题，不是判断）" % exc)
        return 2
    registered = set()
    if os.path.exists(PENDING):
        with open(PENDING, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    registered.add(line.split("#")[0].strip())
    bad = judge(doc, frozenset(registered))
    total = len(refs_of(doc))
    if bad:
        print("  [RED] 共 %d 条结构化引用中，**%d 条指向 objects 里不存在的类**（且未登记）：" % (total, len(bad)))
        for src, cls in bad[:14]:
            print("        %s -> %s" % (src, cls))
        return 1
    print("  [GREEN] %d 条结构化引用（九路射程）全部指向 objects 里存在的类（或已登记）" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))