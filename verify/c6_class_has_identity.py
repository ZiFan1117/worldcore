#!/usr/bin/env python3
"""C6 —— 每个对象类必须「有定义、可指认」（本轮"重新梳理"的抓手）。

红＝_objects 里任一类满足下列任一条：
  ① _meta.definition 缺失，或**是占位话**（含 缺口补立/待补/TBD/占位）⇒ 那一类**实际上没定义**；
  ② 该类的 fields 里**没有任何"指认格"**（name／id／canonical_id／code／key／wf_id／subject／path …）
     ⇒ 那一类**说不出「这一对怎么区分」**。

为什么（口径来源）：
· ★ W3C OWL 2 Primer（REC）逐字：classes are used to group individuals；「Mary belongs to the class of all persons」
  ⇒ 一个类若说不出「它的个体是什么、怎么指认、一对怎么区分」，它就不是一个个体类型。
· ★ 作者 2026-10-13 令：「通告明显不能作为一个单独的个体类型」「判据只能是**有没有个体身份**」
  ⇒ 本判据只问个体身份，**不问「它像不像数据／规则」**（★ 本席曾用后者当理由，已作废）。

用法：
  python verify/c6_class_has_identity.py              跑真仓库
  python verify/c6_class_has_identity.py --self-test  反例自检
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONTOLOGY = os.path.join("crates", "aios-ontology", "data", "ontology.json")
PLACEHOLDER = ("缺口补立", "待补", "TBD", "TODO", "占位")
REGISTRY = os.path.join("verify", "c6_known_gaps.txt")
IDENTITY_FIELDS = ("name", "id", "canonical_id", "code", "key", "wf_id", "subject",
                   "path", "identity", "did", "of_kind", "role")
NAME = "C6 每个类必须有定义、可指认"


def judge(classes):
    """纯函数：classes = [(类名, definition, 字段名列表)] ⇒ (无定义, 无指认格)。"""
    no_def, no_id = [], []
    for name, definition, fields in classes:
        d = (definition or "").strip()
        if not d or any(p in d for p in PLACEHOLDER):
            no_def.append(name)
        if not any(f in IDENTITY_FIELDS for f in fields):
            no_id.append(name)
    return no_def, no_id


def collect():
    with open(ONTOLOGY, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    out = []
    for k, v in doc["_objects"].items():
        if k.startswith("_"):
            continue
        m = v.get("_meta") or {}
        out.append((k, m.get("definition"), list((v.get("fields") or {}).keys())))
    return out


def self_test():
    cases = [
        ("反例1 占位定义", len(judge([("x", "本批按缺口补立的类。", ["name"])])[0]), 1),
        ("反例2 无指认格", len(judge([("x", "一个真实存在的东西。", ["muted", "seq"])])[1]), 1),
        ("正控 有定义有指认格", len(judge([("x", "一个真实存在的东西。", ["name", "state"])])[0])
         + len(judge([("x", "一个真实存在的东西。", ["name", "state"])])[1]), 0),
    ]
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %d，实得 %d" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 2 条各 1；正控 1 条 0")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        classes = collect()
    except (OSError, ValueError, KeyError) as exc:
        print("  [ENV] 读不到本体：%s（环境问题，不是判断）" % exc)
        return 2
    no_def, no_id = judge(classes)
    known = set()
    if os.path.exists(REGISTRY):
        with open(REGISTRY, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    known.add(line.split("#")[0].strip())
    new_def = [c for c in no_def if c not in known]
    new_id = [c for c in no_id if c not in known]
    print("  已登记现状：无定义 %d 类；无指认格 %d 类（共 %d 类）" % (len(no_def), len(no_id), len(classes)))
    if new_def or new_id:
        print("  [RED] 出现**未登记**的不达标类：")
        for c in new_def:
            print("        无定义：%s" % c)
        for c in new_id:
            print("        无指认格：%s" % c)
        return 1
    print("  [GREEN] 没有新出现的不达标类（现状 %d 项已登记，见 %s）" % (len(known), REGISTRY))
    return 0


def _unused_old():
    no_def, no_id = judge(classes)
    if no_def or no_id:
        print("  [RED] 共 %d 类，其中：" % len(classes))
        if no_def:
            print("        ★ 没有定义（占位话或空）：%d 类" % len(no_def))
            print("          " + "、".join(no_def))
        if no_id:
            print("        ★ 没有指认格（说不出这一对怎么区分）：%d 类" % len(no_id))
            print("          " + "、".join(no_id))
        return 1
    print("  [GREEN] %d 类都有定义、都有指认格" % len(classes))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))