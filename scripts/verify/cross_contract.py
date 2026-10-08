#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""cross_contract.py —— **两件不许互相矛盾**（`ontology.json` × `policy.json`）。

## 为什么需要它

本仓的法律今天**分布在两件**里：`ontology.json`（法律·形状，自述「世界的『法律』（出厂设置）」）
与 `policy.json`（法律·权限，自述「世界『法律』的**另一半**」）。
两件**自称是同一份东西的两半** ⇒ ★ 它们**必须不互相矛盾**；而此前**只有一半**被判：

| 分条 | 判什么 | 此前谁判 |
|---|---|---|
| C-01 | `policy.capabilities` ⊆ `ontology._interfaces` | `World::open`（`ext.world.Gate.CapabilityNotInOntology`） |
| C-02 | 同名能力的 `kind` 两处一致 | `World::open`（`ext.world.Gate.CapabilityKindMismatch`） |
| C-03 | **反向**：`ontology._interfaces` ⊆ `policy.capabilities` | ★ **无人判** |
| C-04 | `ontology._actions` ≡ `policy.actions`（**名字集／`capability` 指向／`reversible` 三样**） | ★ **无人判** |
| C-05 | `_permissions.grants` 的**键**是已声明能力 | ★ **无人判** |
| C-06 | `policy.writes` 的每个键能被 `subjects.allow` 放行 | ★ **无人判** |
| C-07 | `policy.listeners[].actor` 能被 `subjects.allow` 放行 | ★ **无人判** |
| C-08 | 实例地址只许落在**实例位键**下（口径①） | ★ **无人判**（见下"本闸不判什么"） |

★ "无人判"这一栏不是推测：C-01／C-02 的射程在 `src/lib.rs` 的 `World::open` 里**逐字自述**
（「⚠️ 射程（如实声明）：只核**名字集**与 `kind`」）⇒ **反向与其余四条**确实没有执行者。
★ 而"没有执行者"的代价是**具体的**：`policy.json` `subjects._why_core` **自己记着**
「`world://core` 是 `writes` 里唯一被授权可写任意主体的主体，却不在本白名单内
⇒ **出厂策略自身不自洽**」（2026-09-27 补）。**那条不自洽就是 C-06 今天要抓的形态** ——
它当时是**被人读出来的**，不是被闸抓出来的。

## 本闸**不判**什么（如实登记，别当已覆盖）

1. **C-08 今天判不了，而且本闸不会报绿**：口径① 的标的物是
   `ontology._permissions._instance_keys`（`标准-语义世界-本体与协议-v0.1.md` §5 第 2 条说它「**必填**」），
   而该键**在 `world-core` 全树零命中** ⇒ 本闸报 `UNDECIDABLE` 并打 `STATUS=SKIP`
   （**⏭，不是 ✅**）——★ "没有标的物"**只报无法判定，不许报绿**。
2. **不判"说明书写的对不对"**：只判**结构**（名字集／取值／归属），不判 `_comment` 一类文字是否过时。
3. **不判第二对"两件"**：仓里另有一对同形的两件并存（`对外语义协议-v0.1-草案` 与
   `对外语义协议-v1-单册`，都自报"不是最终标准"、无一处写明哪份为准）。★ 那对在**架构夹**、
   不在 `check.sh` 的输入面里，本闸**读不到**，故**不声称覆盖**。

## ★ 与既有判据的重叠（不许当"第二权威"读）

C-01／C-02 与 `World::open` 的判据**判的是同一个谓词、同一批取值**。
本闸**仍然判它们**，理由是**判据的射程不同、读者只需看一处**：
`World::open` 判的是"**这个世界能不能开**"（拒启），本闸判的是"**这两件对不对得上**"（一份报告里八条并列）。
★ 重叠**不构成两套规矩**：两处**结论必须一致**；若某次出现不一致，那本身就是缺陷。
★ **不靠 `World::open` 兜底**：本闸必须在**没有二进制**时也跑得起来（VM／干净机器上先看法律面）。

## 判据的三种结局（★ 三分不许混）

- `RED` —— **两件对同一件事说了不同的话** ⇒ 计入红，**rc=1**。
- `WARN` —— 可疑但**不是"两件矛盾"**（例：同一件里同一个写法两义）⇒ **打印、不红**（不擅自升级）。
- `UNDECIDABLE` —— **判不了**（缺标的物）⇒ 打印并**不许报绿**（本步打 `STATUS=SKIP`）。

## ★★ 两套判据（**一件事一个读数**；2026-10-05 Lead 裁）

| 套 | 判据 | 今天 | `check.sh` |
|---|---|---|---|
| `--set cross` | **C-01…C-07**（两件不许互相矛盾） | ★ **判得了** ⇒ `STATUS=PASS` ⇒ **该步 ✅** | **⑦c** |
| `--set instance` | **C-08**（实例地址只许落在实例位键下，口径①） | ★ **判不了**（缺标的物 `_instance_keys`）⇒ `STATUS=SKIP` ⇒ **该步 ⏭** | **⑦d** |
| `--set all` | 两套合计（缺省） | 随其中较差的一套 | —— |

★ **为什么必须拆**：**"7 条判过且对"与"1 条判不了"是两件事**。混在一步里，
**那 7 条的绿会被那 1 条的 ⏭ 吞掉**；反过来 **⏭ 又可能被人读成 ❌** —— **两个方向的误读都会发生**。
★ 硬底线：**"判不了"不许显示成 ✅**。

用法：
  python3 scripts/verify/cross_contract.py                        # 缺省读 ./ontology.json 与 ./policy.json（--set all）
  python3 scripts/verify/cross_contract.py --set cross            # 只判 C-01…C-07
  python3 scripts/verify/cross_contract.py --set instance         # 只判 C-08
  python3 scripts/verify/cross_contract.py --ontology <p> --policy <p>
  python3 scripts/verify/cross_contract.py --self-test            # 每条判据各造反例＋正控＋短路验红

退出码：0 = 无红（**可能带 UNDECIDABLE**，那时自报 `STATUS=SKIP`）；1 = 有红／自证失败；
       2 = 输入读不到或形状不认识（fail-closed：**读不到不许当成"没问题"**）。
★ 本仓口径「**闸在版本控制之外等于没有闸**」：本件在 `scripts/`（进版本控制）
  并由 `check.sh` 的 ⑦c 步调用。
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile

# ── 判据编号（短路验红要按编号关掉单条判据）────────────────────────────
SET_CROSS = ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07")
SET_INSTANCE = ("C-08",)
CRITERIA = SET_CROSS + SET_INSTANCE
# ★★ 为什么分两套（2026-10-05 Lead 裁）：
#   `C-01…C-07` **今天判得了**（判过且对 ⇒ 该步 ✅）；`C-08` **今天判不了**（缺标的物 ⇒ 该步 ⏭）。
#   ★ 这是**两件事**，混在一步里会**两个方向都误读**：7 条的绿被 1 条的 ⏭ 吞掉；而 ⏭ 又会被读成 ❌。
#   ⇒ 一件事一个读数：`--set cross` 与 `--set instance` 各报各的。
SETS = {"cross": SET_CROSS, "instance": SET_INSTANCE, "all": CRITERIA}
DISABLED = set()        # 只给 --self-test 的"短路验红"用；正跑时恒为空


# ══════════════════════════════════════════════════════════════════════
# 读入面
# ══════════════════════════════════════════════════════════════════════

def load_json(path):
    """读一份 JSON。★ 读不到必须**显式报错**（fail-closed），不许静默跳过。"""
    if not os.path.isfile(path):
        raise IOError("读不到：%s" % path)
    with io.open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def names(d):
    """取一个段的**条文名**集合（`_` 开头的键是说明文字，不是条文）。"""
    if not isinstance(d, dict):
        return set()
    return set(k for k in d.keys() if not k.startswith("_"))


def allowed(actor, patterns):
    """`policy.json.subjects.allow` 的匹配口径：**末尾 `*` 是前缀模式**。

    ★ 与 `writes` **不是同一套口径**：`src/gate.rs::authorize_write` 取 `writes` 的键是
    **按字面**（`self.writes.get(actor)`，**不做前缀匹配**）—— 那一处由 W-01 报出。
    """
    for p in patterns or []:
        if not isinstance(p, str):
            continue
        if p.endswith("*"):
            if actor.startswith(p[:-1]):
                return True
        elif p == actor:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
# 判据本体（**纯函数**：吃两份字典，吐 reds／warns／undecidables）
# ══════════════════════════════════════════════════════════════════════

def judge(ont, pol, only=None):
    """返回 (reds, warns, undecidables)；每项是一个**可读的判决句**。

    `only`：只判**这一套**判据（`SETS` 里的一个元组）；`None` ＝ 全判。
    ★ 过滤**在入口做**（不是事后筛）：这样 `--set cross` 跑出来**根本不会**有 C-08 的"无法判定"，
      于是那一步的绿**不会**被另一件事的 ⏭ 吞掉。
    """
    only = set(CRITERIA if only is None else only)
    reds, warns, undec = [], [], []

    def red(cid, msg):
        if cid in only and cid not in DISABLED:
            reds.append((cid, msg))

    def warn(cid, msg):
        # ★ WARN 是**登记**，不是某一套里的判据 ⇒ 它**绕开 `only` 过滤**：
        #   若按套过滤，`--set cross` 一跑，`policy.writes` 里那条"死条文"就会**从报告里消失**
        #   —— 那是把一条**已登记的隐患**弄成看不见（比不报更坏）。
        if cid not in DISABLED:
            warns.append((cid, msg))

    def und(cid, msg):
        if cid in only and cid not in DISABLED:
            undec.append((cid, msg))

    # ── 输入面：缺段即拒（fail-closed；缺段不许被读成"没有矛盾"）────────
    for label, key, who in (("ontology", "_interfaces", "src/ontology_definition/ontology.json"),
                            ("ontology", "_actions", "src/ontology_definition/ontology.json"),
                            ("policy", "capabilities", "src/gate/policy.json"),
                            ("policy", "actions", "src/gate/policy.json")):
        d = ont if label == "ontology" else pol
        if not isinstance(d.get(key), dict):
            # ★ 输入面是**前置条件**，不是某一条判据 ⇒ 它**故意绕开 `only` 过滤**：
            #   任何一套（含 `--set cross`）在输入面读不懂时都必须**显式报"判不了"**，
            #   不许因为"这一套里没有这条判据"而被悄悄丢掉（那会变成 rc=0 的假绿）。
            undec.append(("输入面", "%s 里没有 `%s` 段（或它不是对象）⇒ 本闸**判不了**，"
                                  "**不许**读成「没有矛盾」" % (who, key)))
            return reds, warns, undec

    ont_if = names(ont.get("_interfaces"))
    pol_caps = names(pol.get("capabilities"))
    ont_act = names(ont.get("_actions"))
    pol_act = names(pol.get("actions"))
    objs = names(ont.get("_objects")) or names(ont.get("concepts"))

    # ── C-01／C-02：闸侧声明的能力必须在本体里，且 kind 一致（重叠 World::open）──
    for n in sorted(pol_caps - ont_if):
        red("C-01", "能力 `%s` 在 policy.capabilities 里有、在 ontology._interfaces 里**没有** "
                    "（闸会放行一项本体里根本不存在的能力）" % n)
    for n in sorted(ont_if & pol_caps):
        ko = ont["_interfaces"][n].get("kind")
        kp = pol["capabilities"][n].get("kind")
        if ko != kp:
            red("C-02", "能力 `%s` 的 `kind` 两处不一致：ontology 说 `%s`，policy 说 `%s`" % (n, ko, kp))

    # ── C-03：反向（**此前无人判**）────────────────────────────────────
    for n in sorted(ont_if - pol_caps):
        red("C-03", "能力 `%s` 在 ontology._interfaces 里声明了，而 policy.capabilities 里**没有登记** "
                    "（闸不认识它 ⇒ 它永远走不到裁决）" % n)

    # ── C-04：动作两层三样逐项（**此前无人判**）────────────────────────
    _C4 = "C-04"
    for n in sorted(ont_act - pol_act):
        red(_C4, "动作 `%s` 在 ontology._actions 里有、policy.actions 里**没有**" % n)
    for n in sorted(pol_act - ont_act):
        red(_C4, "动作 `%s` 在 policy.actions 里有、ontology._actions 里**没有**" % n)
    for n in sorted(ont_act & pol_act):
        a, b = ont["_actions"][n], pol["actions"][n]
        if a.get("capability") != b.get("capability"):
            red(_C4, "动作 `%s` 引用的能力两处不一致：ontology 说 `%s`，policy 说 `%s`"
                     % (n, a.get("capability"), b.get("capability")))
        if a.get("reversible") != b.get("reversible"):
            red(_C4, "动作 `%s` 的 `reversible` 两处不一致：ontology 说 `%s`，policy 说 `%s`"
                     "（**闸的摩擦挂在动作的不可逆等级上** ⇒ 这一格漂了，闸的松紧就漂了）"
                     % (n, a.get("reversible"), b.get("reversible")))

    # ── C-05：许可条文的**键**必须是已声明能力（**此前无人判**）────────
    perms = ont.get("_permissions") or {}
    grants = perms.get("grants") or {}
    for g in sorted(names(grants)):
        if g not in ont_if:
            red("C-05", "许可条文 `_permissions.grants.%s` 的键**不是**已声明能力"
                        "（授权只许授在**能力**上）" % g)

    # ── C-06：`writes` 的每个键都要能被 `subjects.allow` 放行（**此前无人判**）──
    allow = (pol.get("subjects") or {}).get("allow") or []
    for w in sorted(names(pol.get("writes"))):
        if not allowed(w, allow):
            red("C-06", "`policy.writes` 的键 `%s` **不在** `subjects.allow` 里能被放行"
                        "（它被授权写世界，却连上总线说话的资格都没有 ⇒ **出厂策略自身不自洽**；"
                        "`policy.json` 自己记着 `world://core` 曾是这个形态）" % w)

    # ── C-07：口给出的身份必须能说话（**此前无人判**）──────────────────
    for l in (pol.get("listeners") or []):
        a = (l or {}).get("actor")
        if isinstance(a, str) and not allowed(a, allow):
            red("C-07", "`policy.listeners` 的 `actor` `%s` **不在** `subjects.allow` 里"
                        "（口给了它身份，而白名单不放它说话）" % a)

    # ── C-08：实例地址只许落在实例位键下（口径①）──────────────────────
    inst_keys = perms.get("_instance_keys")
    addr = re.compile(r"^world://([^/\s]+)/([^/\s]+)$")
    declared = objs

    def instance_addrs(seq):
        out = []
        for v in seq or []:
            if not isinstance(v, str):
                continue
            m = addr.match(v)
            if m and m.group(1) in declared:
                out.append(v)
        return out

    if not isinstance(inst_keys, list):
        und("C-08",
            "**判不了**：口径① 的标的物 `ontology._permissions._instance_keys` **不在**"
            "（`标准-语义世界-本体与协议-v0.1.md` §5 第 2 条说它「必填」；"
            "现取：该键在 `world-core` 全树零命中）⇒ 实例地址**该不该**只落在实例位键下，"
            "本闸**无从判起** —— ★ 报无法判定，**不报绿**")
    else:
        ik = set(inst_keys)
        scan = []
        for g in sorted(names(grants)):
            gd = grants.get(g) or {}
            for k in sorted(gd.keys()):
                if k.startswith("_") or k in ik:
                    continue
                scan.append(("_permissions.grants.%s.%s" % (g, k), gd.get(k)))
        scan.append(("policy.writes（键）", sorted(names(pol.get("writes")))))
        scan.append(("policy.subjects.allow", allow))
        scan.append(("policy.listeners[].actor",
                     [l.get("actor") for l in (pol.get("listeners") or []) if isinstance(l, dict)]))
        for where, seq in scan:
            hits = instance_addrs(seq)
            if hits:
                red("C-08", "实例地址出现在**非实例位键** `%s` 上：%s（口径①：实例位键由 "
                            "`_instance_keys` 声明，**定义面没有「身份位」豁免**）" % (where, hits))

    # ── W-01：同一件里同一个写法两义（**不是"两件矛盾"⇒ 只报 WARN**）────
    star = sorted(k for k in names(pol.get("writes")) if "*" in k)
    if star:
        warn("W-01", "`policy.writes` 里有含 `*` 的键：%s —— 同一个写法（末尾 `/*`）在两处**两义**："
                     "`writes` 取键是**按字面**（`src/gate.rs::authorize_write` 的 `self.writes.get(actor)`，"
                     "**不做前缀匹配**），而 `subjects.allow` 的末尾 `*` **是**前缀模式。"
                     "⇒ 这些键**永不命中任何主体**（死条文）。"
                     "★ 本闸**不判它红**：`policy.json._lookup` 已逐字声明过这个口径，"
                     "且它**不构成「两件说了不同的话」** —— 只登记，处置权在法律主人。" % star)

    return reds, warns, undec


# ══════════════════════════════════════════════════════════════════════
# 报告
# ══════════════════════════════════════════════════════════════════════

def report(ont_path, pol_path, reds, warns, undec, set_name="all", quiet=False):
    if not quiet:
        print("== 两件一致性守卫（ontology.json × policy.json）==")
        print("  ontology: %s" % ont_path)
        print("  policy  : %s" % pol_path)
        print("  判据面  : %s（本套＝`--set %s`；逐条见 scripts/verify/cross_contract.py 文件头）"
              % ("／".join(SETS[set_name]), set_name))
        for cid, msg in reds:
            print("  RED  %s  %s" % (cid, msg))
        for cid, msg in warns:
            print("  WARN %s  %s" % (cid, msg))
        for cid, msg in undec:
            print("  UNDECIDABLE %s  %s" % (cid, msg))
        print("  红 %d ／ 告警 %d ／ 无法判定 %d（★ 条数现取，本处不复述）"
              % (len(reds), len(warns), len(undec)))
    return reds, warns, undec


def emit_status(reds, undec):
    """★ 步级结局由本件**自己报**（`check.sh` 的 `run_tail` 认 `STATUS=`）：

    - 有红            ⇒ 不报 PASS（由 rc=1 让该步失败）
    - 无红但有"判不了" ⇒ `STATUS=SKIP`（打 ⏭，**不是 ✅**）——★ 不许报绿
    - 全判据都可判且绿 ⇒ `STATUS=PASS`
    """
    if reds:
        return
    print("STATUS=%s" % ("SKIP" if undec else "PASS"))


# ══════════════════════════════════════════════════════════════════════
# 自证：反例必红 ／ 正控必绿 ／ 短路验红
# ══════════════════════════════════════════════════════════════════════

def _base_ont():
    return {
        "world": 1,
        "concepts": {},
        "envelope": {"required": ["world", "kind"], "optional": []},
        "families": {"change": {"required": ["subject"], "optional": []}},
        "_objects": {"notice": {"fields": {"muted": "bool"}, "instance_mode": "many"}},
        "_interfaces": {"notice.mute": {"kind": "invoke"}},
        "_actions": {"notice.mute": {"capability": "notice.mute", "reversible": True}},
        "_permissions": {
            "default": "deny",
            "grants": {"notice.mute": {"scope": ["world://user"]}},
            "_instance_keys": ["scope"],
        },
    }


def _base_pol():
    return {
        "policy": 1,
        "capabilities": {"notice.mute": {"kind": "invoke"}},
        "actions": {"notice.mute": {"capability": "notice.mute", "reversible": True}},
        "writes": {"world://user": ["world://*"]},
        "subjects": {"allow": ["world://user"]},
        "listeners": [{"socket": "/tmp/a.sock", "actor": "world://user"}],
        "irreversible_actors": ["world://user"],
    }


def _mut(fn):
    o, p = _base_ont(), _base_pol()
    fn(o, p)
    return o, p


# 每条判据各一个**同形态反例**（改坏哪一处 ⇒ 哪条红）
SELFTEST = (
    ("C-01 反例：闸侧多一项本体没有的能力",
     lambda o, p: p["capabilities"].__setitem__("ghost.cap", {"kind": "invoke"}), "C-01"),
    ("C-02 反例：同名能力 kind 两处不一致",
     lambda o, p: p["capabilities"]["notice.mute"].__setitem__("kind", "config"), "C-02"),
    ("C-03 反例：本体声明了能力、闸侧没登记",
     lambda o, p: o["_interfaces"].__setitem__("ghost.cap", {"kind": "invoke"}), "C-03"),
    ("C-04 反例 a：动作名两层对不上",
     lambda o, p: p["actions"].__setitem__("ghost.act", {"capability": "notice.mute", "reversible": True}), "C-04"),
    ("C-04 反例 b：动作引用的能力两处不一致",
     lambda o, p: p["actions"]["notice.mute"].__setitem__("capability", "notice.unmute"), "C-04"),
    ("C-04 反例 c：动作的 reversible 两处不一致",
     lambda o, p: p["actions"]["notice.mute"].__setitem__("reversible", False), "C-04"),
    ("C-05 反例：许可条文的键不是能力",
     lambda o, p: o["_permissions"]["grants"].__setitem__("ghost.cap", {"scope": ["world://user"]}), "C-05"),
    ("C-06 反例：writes 的键不被 subjects.allow 放行",
     lambda o, p: p["writes"].__setitem__("world://ghost/x", []), "C-06"),
    ("C-07 反例：口给出的身份不放它说话",
     lambda o, p: p["listeners"].append({"socket": "/tmp/b.sock", "actor": "world://ghost/x"}), "C-07"),
    ("C-08 反例：实例地址跑到非实例位键（who）上",
     lambda o, p: o["_permissions"]["grants"]["notice.mute"].__setitem__(
         "who", ["world://notice/a-1"]), "C-08"),
)


def self_test():
    print("== 两件一致性守卫自证（每条判据各造反例；反例不红即判该判据是装饰）==")
    bad = 0

    # ① 判据层：纯函数造反例 ⇒ 该条必须红
    for name, mut, want in SELFTEST:
        o, p = _mut(mut)
        reds, _w, _u = judge(o, p)
        got = {cid for cid, _ in reds}
        ok = want in got
        if not ok:
            bad += 1
        print("  [%s] %s：红出 %s，应含 %s"
              % ("OK" if ok else "失败", name, sorted(got) or "无", want))

    # ② 正控：同一个夹具（不造任何反例）⇒ **必须无红**（证明判据不是"永远红"）
    reds, warns, undec = judge(_base_ont(), _base_pol())
    ok = not reds
    if not ok:
        bad += 1
    print("  [%s] 正控（无变异夹具）：红 = %s（应无）；告警 = %s；无法判定 = %s"
          % ("OK" if ok else "失败", sorted(c for c, _ in reds) or "无",
             sorted(c for c, _ in warns) or "无", sorted(c for c, _ in undec) or "无"))

    # ③ ★ 短路验红：把每条判据轮流关掉 ⇒ 它自己的反例必须**不再红**
    #    （证明"红"是那条判据给的，不是别处冒出来的；也证明反例与判据一一对应）
    for name, mut, want in SELFTEST:
        o, p = _mut(mut)
        saved = set(DISABLED)
        DISABLED.add(want)
        try:
            reds, _w, _u = judge(o, p)
        finally:
            DISABLED.clear()
            DISABLED.update(saved)
        got = {cid for cid, _ in reds}
        ok = want not in got
        if not ok:
            bad += 1
        print("  [%s] 短路 %s 后，该反例红出 %s（应不含 %s）——判据与反例确有一一对应"
              % ("OK" if ok else "失败", want, sorted(got) or "无", want))

    # ④ ★ 结局分支（`STATUS=`）的三条：
    #    a) 缺标的物 ⇒ **必须** STATUS=SKIP（⏭，不是 ✅），且**必须**打出 UNDECIDABLE
    #    b) 有标的物且全绿 ⇒ **必须** STATUS=PASS
    #    c) 有红 ⇒ **必须不报** PASS／SKIP（由 rc=1 让该步失败）
    tmp = tempfile.mkdtemp(prefix="xcontract-selftest-")
    try:
        o, p = _base_ont(), _base_pol()
        del o["_permissions"]["_instance_keys"]
        pa, pb = _write_pair(tmp, "a", o, p)
        rc_a, out_a = _run(pa, pb)
        ok_a = (rc_a == 0) and ("STATUS=SKIP" in out_a) and ("STATUS=PASS" not in out_a) \
               and ("UNDECIDABLE C-08" in out_a)
        if not ok_a:
            bad += 1
        print("  [%s] a) 缺 `_instance_keys` ⇒ rc=%d（应 0）／自报 SKIP=%s（应 True）／"
              "自报 PASS=%s（应 False）／UNDECIDABLE C-08=%s（应 True）"
              % ("OK" if ok_a else "失败", rc_a, "STATUS=SKIP" in out_a,
                 "STATUS=PASS" in out_a, "UNDECIDABLE C-08" in out_a))

        pa, pb = _write_pair(tmp, "b", _base_ont(), _base_pol())
        rc_b, out_b = _run(pa, pb)
        ok_b = (rc_b == 0) and ("STATUS=PASS" in out_b) and ("RED " not in out_b)
        if not ok_b:
            bad += 1
        print("  [%s] b) 标的全在且绿 ⇒ rc=%d（应 0）／自报 PASS=%s（应 True）／无 RED=%s（应 True）"
              % ("OK" if ok_b else "失败", rc_b, "STATUS=PASS" in out_b, "RED " not in out_b))

        o, p = _mut(lambda o, p: p["capabilities"].__setitem__("ghost.cap", {"kind": "invoke"}))
        pa, pb = _write_pair(tmp, "c", o, p)
        rc_c, out_c = _run(pa, pb)
        ok_c = (rc_c == 1) and ("STATUS=PASS" not in out_c) and ("STATUS=SKIP" not in out_c)
        if not ok_c:
            bad += 1
        print("  [%s] c) 有红 ⇒ rc=%d（应 1）／不报 PASS=%s／不报 SKIP=%s（都应 True）"
              % ("OK" if ok_c else "失败", rc_c, "STATUS=PASS" not in out_c, "STATUS=SKIP" not in out_c))

        # ★★ 拆套后的两条（Lead 2026-10-05 裁）：**同一份夹具**（缺标的物）在两套里的读数必须**不同**
        #    e) `--set cross` ⇒ C-08 被排除 ⇒ **无"判不了"** ⇒ STATUS=PASS（该步配 ✅）
        #    f) `--set instance` ⇒ 只有 C-08 ⇒ STATUS=SKIP（该步配 ⏭，**不是 ✅**）
        #    ⇒ 证明"两件事各自有读数"不是一句口号。
        o, p = _base_ont(), _base_pol()
        del o["_permissions"]["_instance_keys"]
        pa, pb = _write_pair(tmp, "e", o, p)
        rc_e, out_e = _run(pa, pb, ["--set", "cross"])
        ok_e = (rc_e == 0) and ("STATUS=PASS" in out_e) and ("UNDECIDABLE" not in out_e)
        if not ok_e:
            bad += 1
        print("  [%s] e) --set cross（缺标的物也判得了）⇒ rc=%d（应 0）／自报 PASS=%s（应 True）／"
              "无 UNDECIDABLE=%s（应 True）"
              % ("OK" if ok_e else "失败", rc_e, "STATUS=PASS" in out_e, "UNDECIDABLE" not in out_e))

        rc_f, out_f = _run(pa, pb, ["--set", "instance"])
        ok_f = (rc_f == 0) and ("STATUS=SKIP" in out_f) and ("UNDECIDABLE C-08" in out_f) \
               and ("STATUS=PASS" not in out_f)
        if not ok_f:
            bad += 1
        print("  [%s] f) --set instance（缺标的物）⇒ rc=%d（应 0）／自报 SKIP=%s（应 True）／"
              "UNDECIDABLE C-08=%s（应 True）／自报 PASS=%s（应 False）"
              % ("OK" if ok_f else "失败", rc_f, "STATUS=SKIP" in out_f,
                 "UNDECIDABLE C-08" in out_f, "STATUS=PASS" in out_f))

        # ⑤ 输入面 fail-closed：文件不存在 ⇒ rc=2（**读不到不许当成"没问题"**）
        rc_d, out_d = _run(os.path.join(tmp, "NOT-EXIST.json"), os.path.join(tmp, "NOT-EXIST.json"))
        ok_d = rc_d == 2
        if not ok_d:
            bad += 1
        print("  [%s] d) 输入读不到 ⇒ rc=%d（应 2＝fail-closed，不许 rc=0）" % ("OK" if ok_d else "失败", rc_d))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print("自证%s（失败 %d 项）" % ("通过" if bad == 0 else "失败", bad))
    # ★★ 自证这一步**自己的结局**：通过才自报 PASS ⇒ `check.sh` 那一步才配打 ✅。
    #    ★ 本段不可省：本件内部会**故意**跑出 `STATUS=SKIP` 的分支；
    #      若把那些字样原样打在输出里，外层 `run_tail` 会把"自证"这一步**误标成 ⏭**
    #      （2026-10-05 在 VM 全闸上**实测到**：`⏭ 两件一致性守卫自证…（rc=0）`）。
    #      故本函数输出的**诊断文字一律不写 `STATUS=` 字面**，只在此处报一次结局。
    if bad == 0:
        print("STATUS=PASS")
    return 1 if bad else 0


def _write_pair(tmp, tag, ont, pol):
    pa = os.path.join(tmp, "ontology-%s.json" % tag)
    pb = os.path.join(tmp, "policy-%s.json" % tag)
    for path, data in ((pa, ont), (pb, pol)):
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return pa, pb


def _run(ont_path, pol_path, extra=()):
    """按**真实命令行**跑一次本件（自证要验的是 CLI 面，不是内部函数）。"""
    import subprocess
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"   # ★ 子进程按 UTF-8 写，父进程才解得对
    cmd = [sys.executable, os.path.abspath(__file__),
           "--ontology", ont_path, "--policy", pol_path] + list(extra)
    o = subprocess.run(cmd, capture_output=True, env=env)
    return o.returncode, o.stdout.decode("utf-8", "replace")


# ══════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════

def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--ontology", default="src/ontology_definition/ontology.json")
    ap.add_argument("--policy", default="src/gate/policy.json")
    ap.add_argument("--self-test", action="store_true", dest="self_test")
    ap.add_argument("--set", dest="set_name", default="all", choices=sorted(SETS),
                    help="只判这一套：cross＝C-01…C-07（两件不许互相矛盾）／"
                         "instance＝C-08（实例地址归属，口径①）／all＝两套都判")
    args, rest = ap.parse_known_args(argv)

    if args.self_test:
        return self_test()
    if rest:
        print("用法错误：不认识的参数 %s" % rest, file=sys.stderr)
        return 2

    try:
        ont = load_json(args.ontology)
        pol = load_json(args.policy)
    except Exception as e:
        # ★ fail-closed：读不到就是 rc=2，**不许**当成"没有矛盾"
        print("输入面读不到 ⇒ 本闸**判不了**（rc=2，fail-closed）：%s" % e, file=sys.stderr)
        return 2
    if not isinstance(ont, dict) or not isinstance(pol, dict):
        print("输入面不是 JSON 对象 ⇒ 本闸**判不了**（rc=2）", file=sys.stderr)
        return 2

    reds, warns, undec = judge(ont, pol, SETS[args.set_name])
    report(args.ontology, args.policy, reds, warns, undec, set_name=args.set_name)
    emit_status(reds, undec)
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
