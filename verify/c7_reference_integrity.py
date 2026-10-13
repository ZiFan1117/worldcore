#!/usr/bin/env python3
"""C7 —— 本体内部**引用完整性**（承三席：C1–C6 没有一条盯派生表）。

红＝本体里任何**指向类名的结构化引用**，其类名**既不在 `_objects` 里、也不在 `_proposed_objects` 里**：
  ① `_storage_class_map.entries.*.ours`（映射表说"我们对应哪个类"）
  ② `_property_types.types.*.used_by` 的条目（形如 `<类名>.<字段名>`）
  ③ `_property_types._P无对应而我方在用的[].字段` 的条目
  ④ `_proposed_objects.entries` 的键（提案里的类名，**允许**存在但要能被点名）

为什么（来历）：
· ★ 三席评审（专家-判据-乙／专家-分层-甲）现取：`_property_types.used_by` **90 条里有 24 条**指着已撤回的
  6 个类（project/file/memory/model/package/config）—— ★ **撤回不彻底，且 C1–C6 没有一条盯它**。
· ★ 本判据**不判「类 vs 值域」**（三席已证三条候选全废：恒真／补边即绕／改名即穿）；
  它只判一件**机械可判**的事：**本体的引用不许指向不存在的类**。
· ★ 这是「认结构」而不是「搜字样」：它比对的是**引用与被引方是否存在**，不是名字长什么样。

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


def refs_of(doc):
    """抽出所有"指向类名"的结构化引用 ⇒ [(引用来源, 类名)]。"""
    out = []
    sm = doc.get("_storage_class_map") or {}
    for k, v in (sm.get("entries") or {}).items():
        ours = (v or {}).get("ours")
        if isinstance(ours, str) and ours:
            out.append(("_storage_class_map." + k, ours))
    pt = doc.get("_property_types") or {}
    for tname, tv in (pt.get("types") or {}).items():
        for entry in ((tv or {}).get("used_by") or []):
            out.append(("_property_types." + tname, str(entry).split(".")[0]))
    for item in (pt.get("_P无对应而我方在用的") or []):
        f = str((item or {}).get("字段", ""))
        if f:
            out.append(("_property_types._P无对应", f.split(".")[0]))
    return out


def judge(doc, registered=frozenset()):
    """纯函数：返回 [(来源, 类名)] —— 指向了**_objects 里不存在**的类。

    ★ _objects 是**唯一合法目标**。
    ★ 指向提案（_proposed_objects）或别处的引用，**必须逐条登记在 c7_known_pending.txt**，
      否则判红 —— 这正是本判据要抓的案子（★ 初版曾把 _proposed_objects 也算"存在"，
      结果把"撤回不彻底"那条 24 条残留**全放过去了**：实测放回一条 package.name 仍为绿）。
    """
    known = set(k for k in (doc.get("_objects") or {}) if not k.startswith("_"))
    return [(src, cls) for src, cls in refs_of(doc)
            if cls and cls not in known and cls not in registered]


def self_test():
    base = {"_objects": {"human": {}, "agent": {}}, "_proposed_objects": {"entries": {"file": {}}}}
    cases = []
    d1 = dict(base); d1["_storage_class_map"] = {"entries": {"HUMAN": {"ours": "human"}, "GHOST": {"ours": "nowhere"}}}
    cases.append(("反例1 映射表指向不存在的类", len(judge(d1)), 1))
    d2 = dict(base); d2["_property_types"] = {"types": {"STRING": {"used_by": ["human.name", "gone.field"]}}}
    cases.append(("反例2 派生表指向不存在的类", len(judge(d2)), 1))
    d3 = dict(base); d3["_property_types"] = {"types": {"STRING": {"used_by": ["human.name"]}}}
    cases.append(("正控 指向存在的类", len(judge(d3)), 0))
    d4 = dict(base); d4["_property_types"] = {"types": {"STRING": {"used_by": ["file.path"]}}}
    cases.append(("反例3 ★仅提案里的类也算缺（初版的洞）", len(judge(d4)), 1))
    cases.append(("正控2 登记在册后可放行", len(judge(d4, frozenset({"file"}))), 0))
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 3 条各 1；正控 2 条各 0")
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
        print("  [RED] 共 %d 条结构化引用中，**%d 条指向 _objects 里不存在的类**（且未登记）：" % (total, len(bad)))
        for src, cls in bad[:12]:
            print("        %s -> %s" % (src, cls))
        return 1
    print("  [GREEN] %d 条结构化引用全部指向 _objects 里存在的类（或已登记）" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))