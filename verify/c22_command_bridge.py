#!/usr/bin/env python3
"""C22 —— 传统命令能接进来，但命令字面量不许进本体（T-244 命令桥）。

★ 作者令（逐字）：「我们要实现的就是底下的传统的一些命令行的这些命令全部能够接进来，
  而接进来的方式就是……把它底下的这些工具，然后注册为我们的 action」。

红＝
  (a) 没有映射表 crates/aios-ontology/data/command-map.jsonl ⇒ 红；
  (b) 表里有行缺五格（action／function／registered_by／registered_by_kind／required_roles）⇒ 红；
  (c) 表里的 registered_by_kind 一条 system 都没有 ⇒ 红；
  (d) ★★ 表里某个 program（命令名）出现在了 ontology.json 里 ⇒ 红
      —— 那是本体那条 functions._no_command_literal 的【跨件版】：命令住映射表，本体只住名字；
  (e) 没有 register_from_map（批量接进来的口）⇒ 红。

限度（★ 如实）：判文本 ⇒ 证不了运行时行为（那要靠 VM 的 cargo test）。

用法：
  python verify/c22_command_bridge.py              跑真仓库
  python verify/c22_command_bridge.py --self-test   反例自检
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MAP = os.path.join("crates", "aios-ontology", "data", "command-map.jsonl")
ONT = os.path.join("crates", "aios-ontology", "data", "ontology.json")
BRIDGE = os.path.join("crates", "aios-worldcore", "src", "core", "command_bridge.rs")
NAME = "C22 命令桥（命令能接进来，字面量不进本体）"
FIVE = ("action", "function", "registered_by", "registered_by_kind", "required_roles")
GOOD = '{"action":"fs.list","function":"fn.fs.list","registered_by":"b","registered_by_kind":"system","required_roles":["human"],"program":"ls","args":[]}'


def entries_text(ont_text):
    """只取 functions.entries 那一段（★ 表级的 _registered_host_commands 是黑名单，故意列命令名 —— 别误判）。"""
    try:
        doc = json.loads(ont_text)
    except Exception:
        return ont_text
    entries = (doc.get("functions", {}) or {}).get("entries", {}) or {}
    return json.dumps(entries, ensure_ascii=False)


def scan(map_text, ont_text, bridge_text):
    bad = []
    if map_text is None:
        return ["没有映射表 %s" % MAP]
    rows = []
    for i, line in enumerate(map_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            bad.append("映射表第 %d 行不是合法 JSON：%s" % (i, e))
    if not rows:
        bad.append("映射表是空的")
    kinds = set()
    for r in rows:
        for k in FIVE:
            if k not in r or r[k] in ("", None, []):
                bad.append("映射表 %s：缺 %s" % (r.get("action", "?"), k))
        kinds.add(r.get("registered_by_kind", ""))
        prog = r.get("program", "")
        if prog and ('"' + prog + '"') in entries_text(ont_text):
            bad.append("★ 命令 %r 出现在 ontology.json 的 functions.entries 里（命令住映射表，本体只住名字）" % prog)
    if rows and "system" not in kinds:
        bad.append("表里一条 system 都没有（接进来的传统命令该是 system 类）")
    if "pub fn register_from_map(" not in bridge_text:
        bad.append("command_bridge.rs：没有 register_from_map（批量接进来的口）")
    return bad


def run(label="真仓库"):
    mt = None
    if os.path.exists(MAP):
        with open(MAP, "r", encoding="utf-8") as f:
            mt = f.read()
    with open(ONT, "r", encoding="utf-8") as f:
        ot = f.read()
    with open(BRIDGE, "r", encoding="utf-8") as f:
        bt = f.read()
    bad = scan(mt, ot, bt)
    print("=== %s（%s）===" % (NAME, label))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    bad_ont = '{"functions": {"entries": {"fn.bad": {"program": "ls"}}}}'
    b1 = scan(GOOD, bad_ont, "pub fn register_from_map(")
    print("=== 红例1（命令名进了本体 entries）⇒ 命中 %d 处 ===" % len(b1))
    if not any("ontology.json" in x for x in b1):
        print("[自检失败] 红例1 该命中本体那条")
        ok = False
    b2 = scan(GOOD.replace('["human"]', "[]"), "{}", "pub fn register_from_map(")
    print("=== 红例2（缺 required_roles）⇒ 命中 %d 处 ===" % len(b2))
    if not any("required_roles" in x for x in b2):
        print("[自检失败] 红例2 该命中缺格那条")
        ok = False
    b3 = scan(GOOD.replace("system", "app"), "{}", "pub fn register_from_map(")
    print("=== 红例3（一条 system 都没有）⇒ 命中 %d 处 ===" % len(b3))
    if not any("system" in x for x in b3):
        print("[自检失败] 红例3 该命中 system 那条")
        ok = False
    b4 = scan(GOOD, "{}", "fn other() {}")
    print("=== 红例4（没有 register_from_map）⇒ 命中 %d 处 ===" % len(b4))
    if not any("register_from_map" in x for x in b4):
        print("[自检失败] 红例4 该命中那条")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
