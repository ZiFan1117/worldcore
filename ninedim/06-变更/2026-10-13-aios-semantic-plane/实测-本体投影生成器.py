import json, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ONT = "D:/Code/13-aios-worldcore/crates/aios-ontology/data/ontology.json"
CAT = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
d = json.load(open(ONT, encoding="utf-8"))

def nu(node): return [k for k in node if not k.startswith("_")]

FIELD_TYPE = {
    "bool": ("CheckBox", None),
    "string": ("TextField", None),
    "integer": ("TextField", "number"),
    "number": ("TextField", "number"),
}

def element_for(decl):
    """★ 本体字段声明串 ⇒ A2UI 元件（★ 也是我们的取值域校验来源）"""
    s = (decl or "").strip()
    if s.startswith("enum("):
        opts = s[5:].rstrip(")").split(",")
        return {"component": "ChoicePicker", "options": [o.strip() for o in opts]}
    if s.startswith("ref("):
        target = s[4:].rstrip(")")
        return {"component": "TextField", "hint": "ref:" + target}
    if s.startswith("array("):
        return {"component": "List", "item": element_for(s[6:].rstrip(")"))}
    base = FIELD_TYPE.get(s)
    if base: return {"component": base[0], "variant": base[1]}
    return {"component": "TextField", "hint": "free" }

# ===== 生成图 =====
surface = "world/system"
comps = []

# ① 根：Column
kids = []
ops = (d.get("objects") or {})
acts = (d.get("actions") or {})

kinds = nu(ops)
acts_n = nu(acts)

# ② 每个类 ⇒ 一张 Card（标题 + 一句说明 + 一个 List）
for k in kinds:
    o = ops[k]
    cid = "card_" + k
    kids.append(cid)
    comps.append({"id": cid, "component": "Card", "child": "col_" + k})
    inner = ["title_" + k]
    comps.append({"id": "title_" + k, "component": "Text",
                  "text": "**" + k + "**" + ("（唯一）" if o.get("instance_mode") == "one" else "")})
    fields = o.get("fields")
    if isinstance(fields, dict) and fields:
        for f in list(fields.keys()):
            fid = "f_" + k + "_" + f
            inner.append(fid)
            comps.append({"id": fid, "component": "Text", "text": f + "：" + str(fields[f])[:40]})
    inner.append("list_" + k)
    comps.append({"id": "list_" + k, "component": "List",
                  "children": {"@template": {"data": "/" + k, "item": "row_" + k}},
                  "_note": "列该类的实例"})
    comps.append({"id": "col_" + k, "component": "Column", "children": inner})

# ③ 每个动作 ⇒ 按钮（★ 只有在册的才有）
act_kids = []
for a in acts_n:
    v = acts[a]
    bid = "btn_" + a.replace(".", "_")
    act_kids.append(bid)
    comps.append({"id": bid, "component": "Button", "child": "txt_" + bid,
                  "_action": a, "_function": v.get("function")})
    comps.append({"id": "txt_" + bid, "component": "Text", "text": a})
kids.append("col_actions")
comps.append({"id": "col_actions", "component": "Column", "children": ["hdr_actions"] + act_kids})
comps.append({"id": "hdr_actions", "component": "Text", "text": "## 可以做（★ 全部来自本体在册动作）"})

comps.insert(0, {"id": "root", "component": "Column", "children": kids})

msg = {"version": "v1.0",
       "name": "worldcore 语义面板（★ 由本体投影生成，不是 agent 自由生成）",
       "messages": [
         {"version": "v1.0", "createSurface": {"surfaceId": surface, "catalogId": CAT, "sendDataModel": True}},
         {"version": "v1.0", "updateComponents": {"surfaceId": surface, "components": comps}},
       ]}

out = "D:/Code/_scratch/a2ui_generated.json"
json.dump(msg, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已生成", out)
print("  元件数 =", len(comps), "（类", len(kinds), "个 ⇒ Card+List；动作", len(acts_n), "个 ⇒ Button）")
print()
print("=== 生成物的前 60 行 ===")
for i, l in enumerate(open(out, encoding="utf-8").read().split(chr(10))[:60], 1):
    print("  " + l)