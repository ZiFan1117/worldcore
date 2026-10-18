#!/usr/bin/env python3
"""C17 —— **「什么都是授权的问题」**：改世界的动作，必须说得出「谁允许的」。

红＝
  (a) 在册动作的 `required_roles` 为空（且没登记在册）⇒ 红；
  (b) `reversible: false`（**不可逆**）的动作 `required_roles` 为空 ⇒ 红。

为什么（口径来源，逐字）：
· ★ 作者 2026-10-16：「**界面类的动作可以改世界，但是这需要授权嘛，对吧？什么都是授权的问题**」；
· ★ 作者 2026-10-16（另一轮）：「**我审批了，你走总线去调用这个东西**」；
· ★ 08 逐字：「**手如果自己有写权限，世界就有了第二个权威**」
  ⇒ ★★ **所以不是「哪一类不许改世界」，而是「改世界必须被授权」。**

★ **这一条替代了 T-232 说明件 §四 那条建议**：
  · 我原先建议「界面类动作只能改显示、不得改世界」—— ★ **那是拿禁令代替授权，思路错了**（作者当场纠正）；
  · 正确口径：★ **「谁改世界」不看类别，看授权** —— ★ 按 `required_roles` ＋ 人的审批判。

★ **登记面模式照 C5／C6／C9**：★ 今天不达标的**如实登记**在 `verify/c17_known_ungranted.txt`，
  ★ **新出现的**不达标 ⇒ 红（回归守卫）。★ 为什么今天不改那五条：★ 给它们加授权＝**动本体的授权口径**，
  那是**作者的话**（判据只把现状钉住，不替人做决定）。

用法：
  python verify/c17_authorization.py              跑真仓库
  python verify/c17_authorization.py --self-test   反例自检
"""
import json
import os
import sys

# ★ 2026-10-18：判据从 verify/ 挪到 scripts/test/ —— 登记面按【本文件所在目录】找
_HERE_ = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ONT = os.path.join("crates", "aios-ontology", "data", "ontology.json")
REGISTRY = os.path.join(_HERE_, "c17_known_ungranted.txt")
NAME = "C17 授权（改世界必须说得出谁允许）"


def scan(doc):
    """返回未授权清单：[(动作名, 是否不可逆)]。"""
    out = []
    for k, v in (doc.get("actions", {}) or {}).items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        roles = v.get("required_roles")
        empty = (not isinstance(roles, list)) or len(roles) == 0
        if empty:
            out.append((k, v.get("reversible") is False))
    return out


def known():
    s = set()
    if not os.path.exists(REGISTRY):
        return s
    with open(REGISTRY, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                s.add(line.split("#")[0].strip())
    return s


def run(path=None, label="真仓库"):
    with open(path or ONT, "r", encoding="utf-8") as f:
        doc = json.load(f)
    found = scan(doc)
    reg = known()
    new = [x for x in found if x[0] not in reg]
    print("=== %s（%s）===" % (NAME, label))
    print("  现取：未授权动作 %d 条（其中不可逆 %d 条）；已登记 %d 条"
          % (len(found), len([x for x in found if x[1]]), len(reg)))
    if new:
        for k, irrev in new:
            print("  [红] %s：required_roles 为空%s" % (k, "（★ 且不可逆！）" if irrev else ""))
        print("=== 结论：红（%d 处未登记）===" % len(new))
        return 1
    print("=== 结论：绿（没有新出现的未授权动作）===")
    return 0


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    # 红例：一个未登记的新动作没有授权
    reg = known()
    red1 = {"actions": {"new.thing": {"required_roles": [], "reversible": False}}}
    n1 = [x for x in scan(red1) if x[0] not in reg]
    print("=== 红例1（新动作无授权且不可逆）⇒ 未登记命中 %d 处 ===" % len(n1))
    if not n1:
        print("[自检失败] 红例1 应当命中，却绿")
        ok = False
    # 绿例：已登记在册的五条（现状）
    green = {"actions": {k: {"required_roles": [], "reversible": True} for k in reg}}
    n2 = [x for x in scan(green) if x[0] not in reg]
    print("=== 绿例（已登记现状）⇒ 未登记命中 %d 处 ===" % len(n2))
    if n2:
        print("[自检失败] 绿例不该命中：%r" % n2)
        ok = False
    # 绿例2：有授权的动作
    green2 = {"actions": {"ok.thing": {"required_roles": ["human"], "reversible": False}}}
    n3 = [x for x in scan(green2) if x[0] not in reg]
    print("=== 绿例2（有授权）⇒ 未登记命中 %d 处 ===" % len(n3))
    if n3:
        print("[自检失败] 绿例2 不该命中：%r" % n3)
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、绿例会绿）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())