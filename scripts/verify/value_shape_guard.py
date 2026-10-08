#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""value_shape_guard.py —— 判据 J1：**世界里的每一个值，都必须落在一个【已声明的格】上。**

## 为什么有这一件

2026-10-05 边界评审（`D:\\Code\\heavy-archive\\语义世界-架构-退役-2026-10-06\\评审-边界-结构与内容-2026-10-05.md`）判：

> 这条线**不该划在"字在不在世界里"**，该划在【**这个字有没有一个已声明的形状载体**】。

同一批业务字，**分属两类**（逐字依据见该件）：

| 落点 | 机制 | 判 |
|---|---|---|
| `cell.label` / `cell.value` | 本体**已声明** `string`；走 `change`（`readmodel.rs:219`） | ★ **折得进状态、读得出 ⇒ 该留** |
| `notice.payload` | 本体**不声明形状**（`ontology.json:267` 逐字「本体今天不声明它」）＋**可选格连格都不算**（`readmodel.rs:480/722`）＋**只计数不折叠**（`:221`） | ★★ **读不出来、漂了不会红 ＝ 套壳最容易回来的地方** |

⇒ **判据：`notice` 家族的值不许携带"界面/内容"这类必须可读的东西；必须可读的东西一律走 `change` 落【已声明的格】。**

## 四条判据

* **J1-01 不落无名格**：每条 `change` 的 `subject` 必须解析到一个**已声明的对象类型**（`world://<类型>/<实例>`）。
  类型未声明 ⇒ **红**（这条世界已经会拦，`ext.world.Ontology.UndeclaredRelationEndpoint` / 未声明实体落账；本判据是**离线**复核那一半）。
* **J1-02 字段必须已声明**：`change.body.path` 必须在 `_objects.<类型>.fields` 里。没声明 ⇒ **红**。
* **J1-03 值类型必须合声明**：按 `_objects` 的字段类型（`bool`/`integer`/`string`/`enum(...)`/`array(...)`/`ref(...)`）判。
  不合 ⇒ **红**。
* **J1-04 ★ 通告不许当口袋**：`notice` 家族里出现 `payload`，且 `payload` 里带**非空**字段 ⇒ **红**
  —— 因为 `payload` 的形状**本体不声明**、读模型**不折叠**，那是"谁都能塞、没人判形状"的口袋。
  ★ 例外要**显式**：`payload` 若已在 `_subscribe` / `_meta_layers` 里被声明过形状，则不红（今天没有）。

## 用法

    python3 scripts/verify/value_shape_guard.py --ontology <path> --ledger <path> [--limit N]
    python3 scripts/verify/value_shape_guard.py --self-test

## 退出码
    0 = 全绿或 SKIP（SKIP 显式打印 `STATUS=SKIP`，**不算绿**）／1 = 有红／2 = 输入缺失（**不是通过**）
"""
import argparse
import json
import pathlib
import re
import sys


# ───────────────────────── 类型判定 ─────────────────────────
def type_ok(decl, val):
    """decl 是本体里的类型声明字符串；val 是 JSON 值。"""
    d = (decl or "").strip()
    if not d or " " in d or "#" in d:      # 本体允许自由文字注释 ⇒ 不判（判据不替它发明）
        return True, "自由文字（不判）"
    if d == "bool":
        return isinstance(val, bool), "bool"
    if d == "integer":
        return isinstance(val, int) and not isinstance(val, bool), "integer"
    if d == "number":
        return isinstance(val, (int, float)) and not isinstance(val, bool), "number"
    if d == "string":
        return isinstance(val, str), "string"
    if d == "object":
        return isinstance(val, dict), "object"
    if d == "array":
        return isinstance(val, list), "array"
    m = re.match(r"^array\((\w+)\)$", d)
    if m:
        inner = m.group(1)
        if not isinstance(val, list):
            return False, d
        for v in val:
            ok, _ = type_ok(inner, v)
            if not ok:
                return False, d
        return True, d
    m = re.match(r"^enum\(([^)]*)\)$", d)
    if m:
        allowed = [x.strip() for x in m.group(1).split(",") if x.strip()]
        return isinstance(val, str) and val in allowed, "enum(%s)" % ",".join(allowed)
    m = re.match(r"^ref\((\w+)\)$", d)
    if m:
        return isinstance(val, str) and val.startswith("world://"), "ref(%s)" % m.group(1)
    return True, "未知声明（放行）"


def declared(ont):
    objs = ont.get("_objects") or {}
    out = {}
    for k, v in objs.items():
        if k.startswith("_"):
            continue
        out[k] = (v or {}).get("fields") or {}
    return out


def type_of_subject(subj):
    """world://<类型>/<实例>  →  <类型>；四段形态取第 3 段（内嵌）。"""
    if not subj.startswith("world://"):
        return None
    parts = subj[len("world://"):].split("/")
    if len(parts) >= 4:
        return parts[2]
    return parts[0] if parts else None


def subject_ok(subj):
    p = subj[len("world://"):].split("/") if subj.startswith("world://") else []
    # 两段（或更多）＝ 有实例名；一段（world://core 这类主体）不是对象实例，跳过
    return len(p) >= 2


# ───────────────────────── 主判 ─────────────────────────
def judge(ont, events, limit=None):
    decls = declared(ont)
    lines, reds = [], 0
    n_chg = n_ntc = 0
    for i, ev in enumerate(events):
        if limit and i >= limit:
            break
        kind = ev.get("kind")
        b = ev.get("body") or {}
        seq = ev.get("seq")
        if kind == "change":
            n_chg += 1
            subj = str(b.get("subject") or "")
            path = str(b.get("path") or "")
            if not subject_ok(subj):
                continue                      # 主体不是对象实例（如 world://core） ⇒ 不在本判据面
            t = type_of_subject(subj)
            if t not in decls:
                reds += 1
                lines.append("  [RED ] J1-01 seq=%s 主体 `%s` 的类型 `%s` **本体没声明**" % (seq, subj, t))
                continue
            fields = decls[t]
            if path not in fields:
                reds += 1
                lines.append("  [RED ] J1-02 seq=%s `%s#%s` 这一格 **本体没声明**（`_objects.%s.fields` 里没有）"
                             % (seq, subj, path, t))
                continue
            ok, tn = type_ok(fields[path], b.get("after"))
            if not ok:
                reds += 1
                lines.append("  [RED ] J1-03 seq=%s `%s#%s` 值 %s 不合声明类型 `%s`"
                             % (seq, subj, path, json.dumps(b.get("after"), ensure_ascii=False)[:40], tn))
        elif kind == "notice":
            n_ntc += 1
            p = b.get("payload")
            if isinstance(p, dict) and p:
                reds += 1
                lines.append("  [RED ] J1-04 seq=%s 通告 `%s` 带了**非空 payload**（%d 个字段）⇒ "
                             "★ 那是**本体不声明形状、读模型不折叠**的口袋；要可读的东西必须走 `change` 落已声明的格"
                             % (seq, b.get("type"), len(p)))
    stat = "RED" if reds else ("GREEN" if (n_chg or n_ntc) else "SKIP")
    if not (n_chg or n_ntc):
        lines.append("  [SKIP] 账本里既没有 change 也没有 notice ⇒ 判据不适用（**未校验 ≠ 通过**）")
    lines.append("  —— change %d 条 / notice %d 条 ⇒ 红 %d 条" % (n_chg, n_ntc, reds))
    return stat, lines


def self_test():
    print("== value_shape_guard 自证 ==")
    ont = {"_objects": {"cell": {"fields": {"label": "string", "order": "integer",
                                            "style": "enum(a,b)", "shown": "bool"}},
                        "notice": {"fields": {"muted": "bool"}}}}
    ok = []

    def ev(kind, body, seq=1):
        return {"kind": kind, "seq": seq, "body": body}

    # 正控：全部合规 ⇒ GREEN
    st, _ = judge(ont, [ev("change", {"subject": "world://cell/c1", "path": "label", "after": "hi"})])
    ok.append(("正控（已声明格 + 合类型）⇒ 应 GREEN", st == "GREEN", st))
    # 反例①：类型未声明 ⇒ RED
    st, _ = judge(ont, [ev("change", {"subject": "world://widget/w1", "path": "label", "after": "x"})])
    ok.append(("反例①（类型没声明）⇒ 应 RED", st == "RED", st))
    # 反例②：字段没声明 ⇒ RED
    st, _ = judge(ont, [ev("change", {"subject": "world://cell/c1", "path": "colour", "after": "red"})])
    ok.append(("反例②（字段没声明）⇒ 应 RED", st == "RED", st))
    # 反例③：值类型不合 ⇒ RED
    st, _ = judge(ont, [ev("change", {"subject": "world://cell/c1", "path": "order", "after": "三"})])
    ok.append(("反例③（值类型不合声明）⇒ 应 RED", st == "RED", st))
    # 反例④：enum 越界 ⇒ RED
    st, _ = judge(ont, [ev("change", {"subject": "world://cell/c1", "path": "style", "after": "chart"})])
    ok.append(("反例④（enum 越界）⇒ 应 RED", st == "RED", st))
    # 反例⑤：通告带非空 payload ⇒ RED
    st, _ = judge(ont, [ev("notice", {"type": "case.step", "payload": {"step": 1}})])
    ok.append(("反例⑤（通告带非空 payload）⇒ 应 RED", st == "RED", st))
    # 正控：通告空 payload ⇒ GREEN
    st, _ = judge(ont, [ev("notice", {"type": "x", "payload": {}})])
    ok.append(("正控（通告空 payload）⇒ 应 GREEN", st == "GREEN", st))
    # 不适用 ⇒ SKIP
    st, _ = judge(ont, [])
    ok.append(("不适用（账本空）⇒ 应 SKIP（**不是通过**）", st == "SKIP", st))

    for name, good, got in ok:
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
    allok = all(g for _, g, _ in ok)
    print("  %s 自证%s：八个假命题都被判对（本判定器不是装饰）"
          % ("✅" if allok else "❌", "通过" if allok else "**未通过**"))
    return 0 if allok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ontology")
    ap.add_argument("--ledger")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.ontology or not a.ledger:
        print("[FAIL] 需要 --ontology 与 --ledger ⇒ **不是通过**")
        return 2
    try:
        ont = json.loads(pathlib.Path(a.ontology).read_text(encoding="utf-8"))
    except Exception as e:
        print("[FAIL] 本体读不了：%s ⇒ **不是通过**" % e)
        return 2
    try:
        events = []
        with open(a.ledger, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
    except OSError as e:
        print("[FAIL] 账本读不了：%s ⇒ **不是通过**" % e)
        return 2

    st, lines = judge(ont, events, a.limit)
    print("=" * 78)
    print("J1 判据：世界里的每一个值，必须落在一个【已声明的格】上")
    print("-" * 78)
    for l in lines:
        print(l)
    print("-" * 78)
    if st == "SKIP":
        print("STATUS=SKIP")
        print("结论 = SKIP（不适用；**未校验 ≠ 通过**）")
        return 0
    print("STATUS=%s" % ("PASS" if st == "GREEN" else "FAIL"))
    print("结论 = %s" % ("绿" if st == "GREEN" else "**红**（见上）"))
    return 0 if st == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
