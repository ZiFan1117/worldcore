#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spec_shape.py —— 规格形态判据（承接原 `openspec validate --all --strict` 的**形态**那一层）。

为什么有它：NineDim 的顶层不含 `openspec/`（那是 openspec CLI 的固定根），
规格的**唯一正文**落在 `ninedim/01-意图环/04-规格/<能力>.spec.md` ⇒ 原 CLI 的形态校验
（Requirement／Scenario／WHEN／THEN 齐备）改由本判据承接，**不降强度**：它同样会红，且自带反例。

判据（每条都必须会红）：
  ① 每份 `*.spec.md` 有 `## Requirements` 标题
  ② 每份至少一条 `### Requirement:`
  ③ 每条 Requirement 至少一个 `#### Scenario:`
  ④ 每个 Scenario 同时有 `**WHEN**` 与 `**THEN**`（openspec 的最小形态）
  ⑤ 能力名与文件名一致（`<能力>.spec.md`，能力名过 `^[a-z0-9]+(?:-[a-z0-9]+)*$`）

用法：`python spec_shape.py [--specs <dir>]`｜`--self-test`（正控全绿 ＋ 每条各一个反例必红）
"""
import argparse
import io
import os
import re
import sys
import tempfile

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HDR = re.compile(r"^###\s+Requirement:\s*(.+?)\s*$", re.M)
SCEN = re.compile(r"^####\s+Scenario:\s*(.+?)\s*$", re.M)
WHEN = re.compile(r"\*\*WHEN\*\*", re.I)
THEN = re.compile(r"\*\*THEN\*\*", re.I)


def check_one(path):
    """返回该 spec 的失败清单（空＝过）。"""
    bad = []
    t = io.open(path, encoding="utf-8").read()
    base = os.path.basename(path)
    cap = base[:-len(".spec.md")]
    if not NAME_RE.match(cap):
        bad.append("%s：能力名不合规（%r）" % (base, cap))
    if not re.search(r"^##\s+Requirements\s*$", t, re.M):
        bad.append("%s：缺 `## Requirements`" % base)
    reqs = HDR.findall(t)
    if not reqs:
        bad.append("%s：没有任何 `### Requirement:`" % base)
    for m in HDR.finditer(t):
        seg = t[m.end():]
        nxt = HDR.search(seg)
        body = seg[:nxt.start()] if nxt else seg
        title = m.group(1)[:40]
        scens = SCEN.findall(body)
        if not scens:
            bad.append("%s：Requirement「%s」没有 `#### Scenario:`" % (base, title))
        for sm in SCEN.finditer(body):
            sseg = body[sm.end():]
            nxt2 = SCEN.search(sseg)
            sbody = sseg[:nxt2.start()] if nxt2 else sseg
            stitle = sm.group(1)[:30]
            if not WHEN.search(sbody):
                bad.append("%s：Scenario「%s」缺 `**WHEN**`" % (base, stitle))
            if not THEN.search(sbody):
                bad.append("%s：Scenario「%s」缺 `**THEN**`" % (base, stitle))
    return bad


def run(specs_dir):
    if not os.path.isdir(specs_dir):
        print("   ★ 规格夹不在：%s（读不到＝判不了，rc=2）" % specs_dir)
        return 2
    files = sorted(f for f in os.listdir(specs_dir) if f.endswith(".spec.md"))
    if not files:
        print("   ★ 规格夹里没有 `*.spec.md`（空集不许判绿，rc=2）")
        return 2
    bad = []
    for f in files:
        bad += check_one(os.path.join(specs_dir, f))
    print("   规格 %d 份；Requirement 合计 %d 条" % (
        len(files), sum(len(HDR.findall(io.open(os.path.join(specs_dir, f), encoding="utf-8").read())) for f in files)))
    if bad:
        for b in bad[:20]:
            print("   [FAIL] %s" % b)
        print("   —— 失败 %d 条 ——" % len(bad))
        return 1
    print("   —— 通过 %d / 失败 0 ——" % len(files))
    return 0


def self_test():
    """正控（完好规格 ⇒ 全绿）＋ 每条判据一个反例（⇒ 必红）。"""
    good = ("## Requirements\n\n### Requirement: 做事\n系统 SHALL 做事。\n\n"
            "#### Scenario: 做成\n- **WHEN** 请求到达\n- **THEN** 返回结果\n")
    cases = [
        ("正控", {"demo-capability.spec.md": good}, 0),
        ("反例①缺 Requirements 标题", {"demo-capability.spec.md": good.replace("## Requirements\n\n", "")}, 1),
        ("反例②无 Requirement", {"demo-capability.spec.md": "## Requirements\n\n啥也没有\n"}, 1),
        ("反例③无 Scenario", {"demo-capability.spec.md": "## Requirements\n\n### Requirement: 做事\n系统 SHALL 做事。\n"}, 1),
        ("反例④缺 THEN", {"demo-capability.spec.md": good.replace("**THEN** 返回结果", "返回结果")}, 1),
        ("反例⑤能力名不合规", {"Demo Cap.spec.md": good}, 1),
        ("反例（空集）", {}, 2),
    ]
    ok = 0
    for name, files, want in cases:
        with tempfile.TemporaryDirectory(prefix="specshape-") as d:
            for fn, body in files.items():
                io.open(os.path.join(d, fn), "w", encoding="utf-8", newline="\n").write(body)
            rc = run(d)
        mark = "OK " if rc == want else "★错"
        if rc == want:
            ok += 1
        print("   [%s] %-22s rc=%d（期望 %d）" % (mark, name, rc, want))
    print("   自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", default=os.path.join("ninedim", "01-意图环", "04-规格"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    return run(a.specs)


if __name__ == "__main__":
    sys.exit(main())
