#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 单向导出：本体 → **OWL（Turtle）＋ SHACL**（2026-10-19；借自小模型的「语义导出桥」）。

★ 借来的两件事（`_scratch/palantir-open-source/code-notes/02-cloudbadal.md` §F）：
  · `OWLExporter`：ObjectType→`owl:Class`、Property→`owl:DatatypeProperty`、LinkType→`owl:ObjectProperty`；
  · `SHACLGenerator`：required→`sh:minCount 1`。
★ 我们的边界（B-3）：**不接 RDF/OWL 运行时（只导出、不推理）** —— 本件就是「只导出」。
★ 产物是**构建产物**：`world.owl.ttl` ＋ `world.shacl.ttl`，不手改、不进运行链。
★ 限度（如实，照抄他们的缺口清单）：不表达 required 的 OWL 约束、不表达链接基数、不导出实例、不可回读；
  导出 ≠ 语义对齐的证明（形状取自不等于符合某个上位本体）。
用法：
  python scripts/release/export-owl.py                  # 写到 ./导出本体/
  python scripts/release/export-owl.py --out-dir D:/x
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src", "ontology"), os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from law.ontology_definition import build_aios_ontology  # noqa: E402

NS = "http://ai-os.net/ns/world#"
XSD = {"STRING": "xsd:string", "INTEGER": "xsd:integer", "FLOAT": "xsd:double",
       "BOOLEAN": "xsd:boolean", "OBJECT_REFERENCE": "xsd:string"}


def _id(s):
    """★ 把类型/属性名变成合法的 URI 片段（`device-bound-to-human` → `device_bound_to_human`）。"""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(s))


def export_owl(ontology):
    """★ 本体 → OWL Turtle 字符串（类＋数据属性＋对象属性；不导实例）。"""
    lines = [
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix ent: <%s> ." % NS,
        "",
        "ent:_ontology a owl:Ontology ;",
        '    rdfs:label "AIOS 世界本体（生成物）" ;',
        '    rdfs:comment "由 scripts/release/export-owl.py 从代码导出；不手改；不接 RDF 运行时。" .',
        "",
    ]
    for tid, ot in sorted(ontology.object_types.items()):
        label = (getattr(ot, "display_name", "") or tid).replace('"', "'")
        lines += ["ent:%s a owl:Class ;" % _id(tid),
                  '    rdfs:label "%s" .' % label, ""]
        for pname, prop in sorted((getattr(ot, "properties", None) or {}).items()):
            pt = getattr(getattr(prop, "property_type", None), "name", "STRING")
            lines += ["ent:%s_%s a owl:DatatypeProperty ;" % (_id(tid), _id(pname)),
                      "    rdfs:domain ent:%s ;" % _id(tid),
                      "    rdfs:range %s ;" % XSD.get(pt, "xsd:string"),
                      '    rdfs:label "%s" .' % pname, ""]
    for lid, lt in sorted(ontology.link_types.items()):
        lines += ["ent:%s a owl:ObjectProperty ;" % _id(lid),
                  "    rdfs:domain ent:%s ;" % _id(getattr(lt, "source_type", "")),
                  "    rdfs:range ent:%s ;" % _id(getattr(lt, "target_type", "")),
                  '    rdfs:label "%s" .' % lid, ""]
    return "\n".join(lines).rstrip() + "\n"


def export_shacl(ontology):
    """★ 本体 → SHACL Shapes 字符串（每类一个 NodeShape；required → sh:minCount 1）。"""
    lines = [
        "@prefix sh: <http://www.w3.org/ns/shacl#> .",
        "@prefix ent: <%s> ." % NS,
        "",
    ]
    for tid, ot in sorted(ontology.object_types.items()):
        props = getattr(ot, "properties", None) or {}
        shape = "ent:%sShape" % _id(tid)
        lines.append("%s a sh:NodeShape ;" % shape)
        lines.append("    sh:targetClass ent:%s%s" % (_id(tid), " ." if not props else " ;"))
        req = [(n, p) for n, p in sorted(props.items()) if getattr(p, "required", False)]
        for i, (pname, _p) in enumerate(req):
            last = (i == len(req) - 1)
            lines.append("    sh:property [ sh:path ent:%s_%s ; sh:minCount 1 ]%s"
                         % (_id(tid), _id(pname), " ." if last else " ;"))
        if not req:
            lines.append("    .")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv):
    out_dir = os.path.join(ROOT, "导出本体")
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    os.makedirs(out_dir, exist_ok=True)
    o = build_aios_ontology()
    owl, shacl = export_owl(o), export_shacl(o)
    with open(os.path.join(out_dir, "world.owl.ttl"), "w", encoding="utf-8") as f:
        f.write(owl)
    with open(os.path.join(out_dir, "world.shacl.ttl"), "w", encoding="utf-8") as f:
        f.write(shacl)
    print("★ 导出 %s（类 %d / 关系 %d / 数据属性 %d）"
          % (out_dir, len(o.object_types), len(o.link_types),
             sum(len(getattr(ot, "properties", None) or {}) for ot in o.object_types.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
