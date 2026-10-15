#!/usr/bin/env python3
"""C8 —— **每个在册角色必须有可见天花板**（H08 读侧那条真闸的声明面判据）。

红＝下列任一条成立：
  ① 某个**在册角色**（`governance.roles.roster` 的键 ∪ `roles.subject_to_role` 的值）
     **没有** `governance.markings.ceiling_by_role` 里的天花板 ⇒ 那个角色「谁能看哪一级」没写；
  ② 天花板的值**不在** `governance.markings.levels` 的闭集里 ⇒ 天花板指向一个不存在的级；
  ③ `levels` 或 `ceiling_by_role` 整个缺 ⇒ 读侧没有法律可依。

为什么（口径来源）：
· ★ 来源1-①.3 逐字：「`Governance` 加 `ceiling_of`（主体／角色 ⇒ 最高可见级）」；
  ★ 缺天花板时**按最低级判**是运行期的口径（法律没写全＝最保守），
  但**「角色在册却没写天花板」这件事本身要红** —— 否则「没写」会静默变成「按最低级」而没人知道。
· ★ 本仓 `permissions.default` 那条同源：默认允许不是安全默认，是**法律没写全**。

用法：
  python verify/c8_role_has_ceiling.py              跑真仓库
  python verify/c8_role_has_ceiling.py --self-test  反例自检
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONTOLOGY = os.path.join("crates", "aios-ontology", "data", "ontology.json")
NAME = "C8 每个在册角色必须有天花板"


def judge(roster, subject_to_role, levels, ceilings):
    """纯函数：四个 dict ⇒ (缺天花板的角色, 指向不存在级的天花板, 缺整节)。

    ★ 只认**非 `_` 前缀**的键（`_` 键是注记，不是法律）。
    """
    roles = set(k for k in (roster or {}) if not k.startswith("_"))
    roles |= set(v for v in (subject_to_role or {}).values() if isinstance(v, str))
    lv = set(k for k in (levels or {}) if not k.startswith("_"))
    ce = {k: v for k, v in (ceilings or {}).items() if not k.startswith("_")}
    missing = sorted(r for r in roles if r not in ce)
    bad = sorted(k for k, v in ce.items() if v not in lv)
    absent = 1 if (not lv or not ce) else 0
    return missing, bad, absent


def collect():
    with open(ONTOLOGY, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    gov = doc.get("governance") or {}
    roles = gov.get("roles") or {}
    markings = gov.get("markings") or {}
    return (roles.get("roster") or {}, roles.get("subject_to_role") or {},
            markings.get("levels") or {}, markings.get("ceiling_by_role") or {})


def self_test():
    cases = [
        ("反例1 角色在册却没有天花板",
         judge({"human": {}}, {"world://user": "human"}, {"PUBLIC": "", "INTERNAL": ""}, {"human": "PUBLIC"})[0], []),
        ("反例1' 一个角色缺天花板",
         judge({"human": {}, "agent": {}}, {"world://user": "human"}, {"PUBLIC": ""}, {"human": "PUBLIC"})[0], ["agent"]),
        ("反例2 天花板指向不存在的级",
         judge({"human": {}}, {}, {"PUBLIC": ""}, {"human": "CLASSIFIED"})[1], ["human"]),
        ("反例3 整节缺",
         judge({"human": {}}, {}, {}, {})[2], 1),
        ("正控 角色齐、级在闭集内",
         judge({"human": {}, "agent": {}}, {"world://user": "human"},
               {"PUBLIC": "", "INTERNAL": "", "CONFIDENTIAL": ""},
               {"human": "CONFIDENTIAL", "agent": "INTERNAL"})[0], []),
    ]
    bad = [(n, got, want) for n, got, want in cases if got != want]
    if bad:
        for n, got, want in bad:
            print("  [SELF-TEST FAIL] %s：期望 %r，实得 %r" % (n, want, got))
        return 1
    print("  [SELF-TEST OK] 反例 4 条（含 2 个变体）＋ 正控 1 条")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    try:
        roster, s2r, levels, ceilings = collect()
    except (OSError, ValueError, KeyError) as exc:
        print("  [ENV] 读不到本体：%s（环境问题，不是判断）" % exc)
        return 2
    missing, bad, absent = judge(roster, s2r, levels, ceilings)
    print("  现取：在册角色 %s；天花板 %s"
          % (sorted(set(list(roster) + list(s2r.values()))), sorted(ceilings)))
    if absent:
        print("  [RED] 读侧没有法律可依：levels 或 ceiling_by_role 缺")
        return 1
    if missing or bad:
        print("  [RED] 天花板不齐：")
        for r in missing:
            print("        角色在册却没有天花板：%s" % r)
        for r in bad:
            print("        天花板指向不存在的级：%s" % r)
        return 1
    real = [k for k in ceilings if not k.startswith("_")]
    print("  [GREEN] %d 个在册角色都有天花板（%s），且级都在闭集内" % (len(real), "、".join(sorted(real))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
