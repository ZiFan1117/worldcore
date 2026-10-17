# -*- coding: utf-8 -*-
"""AIOS 本体进程 —— ★ 世界唯一的耦合点：**只认、只盖章、只转、只记**。

★ 作者令（逐字整理）：
  ·「**这个进程很明确是要读取其他进程的，就是一些能够其他应用的注册等等这些东西**」
  ·「**本体作用就是知道这个动作，然后再传送给另一个**……**而不是我们去调**」
  ·「**谁给授权？肯定是人嘛**」

★ 它做四件，不做第五件：
  ① **认**：★ 名字在注册表里吗？谁能用？
  ② **盖章**：★ 给这条请求发一个 `seq`（`envelope.seq` 逐字「在账本中的位置，全局单增，由世界分配」）
  ③ **转**：★ 按 `registered_by_kind` 发给能做它的那一方（★ 本体【不动手】）
  ④ **记**：★ 每条进出的消息都落账（只追加）
  ✗ **不执行**、✗ **不渲染**、✗ **不碰机器**。

★ 话题（与 Rust 侧同一套）：
  · world/register        ← 安装时注册（五格）
  · world/register/result → 回话
  · world/appear          ← 成为个体
  · world/alive           ← 报到
  · world/ask             ← ★ 请求入口（只有本体订它）
  · world/exec            → 转发给载体
  · world/exec/result     ← 载体回结果
  · world/ask/result      → 回传给请求方
"""

import datetime
import json
import os
import sys
import time

import zenoh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ontology_definition import build_aios_ontology  # noqa: E402

# ── 话题（与 Rust 侧同一套）──
T_REGISTER = "world/register"
T_REGISTER_OK = "world/register/result"
T_APPEAR = "world/appear"
T_ALIVE = "world/alive"
T_APPEAR = "world/appear"   # ★★ 进程上报（「我起来了，我是谁」）
T_ASK = "world/ask"
T_EXEC = "world/exec"
T_ASK_RESULT = "world/ask/result"   # ★ 请求方订这一个就够（本体拒 ⇒ 发这里；载体跑完 ⇒ 也发这里）
# ★★★ 2026-10-17 裁：**本体不再碰结果** —— 退订 world/exec/result、不记结果、不回转。
#     ★ 原则：★ 「谁干的谁报」—— 结果由载体直接回给请求方，本体不在那条路上。

REG_PATH = os.environ.get("AIOS_REGISTRY", "/var/lib/aios/ontology/registry.jsonl")
LEDGER_PATH = os.environ.get("AIOS_LEDGER", "/var/lib/aios/ontology/ledger.jsonl")
ZENOH_ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")


def log(*a):
    print("[本体]", *a, flush=True)


class World:
    """★ 世界 —— 一个进程，四件事。"""

    def __init__(self):
        log("① 装本体 …")
        self.ontology = build_aios_ontology()
        log("   装上了：%d 类 / %d 关系 / %d 动作 / %d 函数"
            % (len(self.ontology.object_types), len(self.ontology.link_types),
               len(self.ontology.action_types), len(self.ontology.functions)))
        self.registry = {}      # ★ 注册表（名字 → 五格）
        self._load_registry()
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        self.ledger = open(LEDGER_PATH, "a", encoding="utf-8")
        log("② 注册表 %d 条；账本 %s" % (len(self.registry), LEDGER_PATH))

    # ── 注册表 ──
    def _load_registry(self):
        if not os.path.exists(REG_PATH):
            return
        with open(REG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("action"):
                    self.registry[r["action"]] = r

    def _append_registry(self, reg):
        os.makedirs(os.path.dirname(REG_PATH), exist_ok=True)
        with open(REG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    # ── 账 ──
    def stamp(self, family, **fields):
        """★★ 落账 —— ★ **按时间标签**，不用序列号（作者 2026-10-17 裁：「账本按时间标签就行，不要用这个序列号了」）。

        ★ 返回那条账的【时间标签】（调用方用它回给请求方）。
        ★★ 为什么不再要 seq：★ 时间本身就带顺序；★ 而 seq 每次重启要恢复最大号（撞号 bug 刚修过）。
        """
        at = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="microseconds")
        row = {"at": at, "family": family, **fields}
        self.ledger.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.ledger.flush()
        return at

    # ── ① 认 ──
    def recognize(self, name, roles=None):
        """查注册表：在册吗？谁能用？★ 不在册就拒。"""
        # ★★ 认名字：【两个来源】
        #   ① **注册表**（装进来的命令动作，`registry.jsonl`）
        #   ② **本体的 actions**（法里声明的动作，如 notice.mute）
        #   ★ 为什么要合：★ 现取发现【交集是 0】—— 注册表 11 条全是命令，本体 9 个全是世界动作 ✗
        reg = self.registry.get(name)
        if reg is None:
            if name in self.ontology.action_types:
                return {"action": name, "registered_by_kind": "world", "required_roles": []}, None
            return None, "不在册（注册表里没有、本体 actions 里也没有）"
        need = reg.get("required_roles") or []
        if roles is not None and need and not any(r in roles for r in need):
            return None, "角色不够（要 %s，你是 %s）" % (need, roles)
        return reg, None

    # ── ①b ★★ 进程注册（★ 作者要的那一种：进程起来 ⇒ 报「我是谁」）──
    def on_appear(self, smp):
        """★ 一个进程起来 ⇒ 照【类的字段】校验 ⇒ 成为个体 ⇒ 记账。

        ★ 作者令（逐字）：「**我们这个进程很明确是要就是读取其他进程的**」
        ★ 与「动作注册」的区别：★ 这条报的是【我这个人是谁】，★ 不是【我能干什么】。
        """
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception as e:
            log("进程上报：不是 JSON（%s）" % e)
            return
        cls = msg.get("class") or ""
        # ★ 认：类在册吗？
        ot = self.ontology.object_types.get(cls)
        if ot is None:
            why = "类不在册（世界没有「%s」这一类）" % cls
            self.stamp("act", kind_of="appear-reject", **{"class": cls, "why": why})
            log("进程上报 %s ⇒ 拒：%s" % (cls or "?", why))
            return
        # ★ 照类的字段校验：必填齐不齐、有没有多塞
        fields = {}
        for k, v in msg.items():
            if k in ("class",):
                continue
            fields[k] = v
        # ★ 兼容：上报方用 local_id，本体字段叫 name
        if "local_id" in fields and "name" not in fields:
            fields["name"] = fields.pop("local_id")
        declared = set(ot.properties.keys())
        extra = [k for k in fields if k not in declared]
        missing = [k for k, pr in ot.properties.items() if pr.required and k not in fields]
        # ★★ 取值域校验（本体声明了 options 的格，值必须在里面）
        bad_value = []
        for k, pr in ot.properties.items():
            if k in fields and pr.options and fields[k] not in pr.options:
                bad_value.append('%s=%r 不在 %s 里' % (k, fields[k], pr.options))
        if extra or missing or bad_value:
            why = []
            if extra:
                why.append("多塞了 %s（本体没声明的格）" % extra)
            if missing:
                why.append("缺必填 %s" % missing)
            if bad_value:
                why.append("取值域不对：" + "；".join(bad_value))
            why_s = "；".join(why)
            self.stamp("act", kind_of="appear-reject", **{"class": cls, "why": why_s, "body": msg})
            log("进程上报 %s ⇒ 拒：%s" % (cls, why_s))
            return
        # ★ 盖章 ＋ 落账（个体出现 ＝ 世界状态变化 ⇒ family=change）
        seq = self.stamp("change", kind_of="appear", **{"class": cls, "subject": "%s/%s" % (cls, fields.get("name", "?")), "after": fields})
        log("★ 进程注册 %s/%s ⇒ 成为个体（%s）" % (cls, fields.get("name", "?"), seq))

    # ── ★★ 执行面 ①：谁能做这个动作（T-342 真做）──
    def can_execute(self, actor, capability):
        """★ 照本体 `permissions` 判「这个主体能不能做这个动作」。

        ★ 口径（全是本体里现成的）：
          ① `permissions.default` ＝ **"deny"** ⇒ ★ 没条文的动作【一律拒】；
          ② `permissions.grants[capability].who` ＝ 主体列表 ⇒ ★ 不在里面就拒；
          ③ ★ 前缀匹配：★ `who` 里写 `world://user`，★ `actor` 是 `world://user/zhang` ⇒ **算在**。

        ★ 返回 (True, None) 或 (False, 为什么)。
        """
        perms = (self.ontology.metadata or {}).get("permissions") or {}
        grants = perms.get("grants") or {}
        g = grants.get(capability)
        if g is None:
            return False, "这个动作没有许可条文（permissions.default = %r ⇒ 默认拒绝）" % perms.get("default")
        who = g.get("who") or []
        for w in who:
            if actor == w or actor.startswith(w.rstrip("/") + "/"):
                return True, None
        return False, "actor=%s 不在许可里（谁可以：%s）" % (actor, who)

    # ── ② 注册（安装时一次）──
    def on_register(self, smp):
        try:
            reg = json.loads(smp.payload.to_string())
        except Exception as e:
            log("注册：消息不是 JSON（%s）" % e)
            return
        name = reg.get("action") or ""
        missing = [k for k in ("action", "function", "registered_by",
                               "registered_by_kind", "required_roles")
                   if not reg.get(k)]
        ok = not missing
        why = "收下" if ok else ("缺格 " + ",".join(missing))
        seq = self.stamp("act", kind_of="register", actor=reg.get("registered_by", "?"),
                         action=name, ok=ok, why=why, body=reg)
        if ok:
            self.registry[name] = reg
            self._append_registry(reg)
        log("注册 %s ⇒ %s（%s，在册 %d 条）" % (name or "?", why, seq, len(self.registry)))
        return seq



def main():
    w = World()
    log("③ 连总线 %s …" % ZENOH_ENDPOINT)
    conf = zenoh.Config()
    # ★★★ 实测出来的三条（2026-10-17，VM 上四种组合都试过）：
    #   ① mode=peer 时「跨进程收不到」（同进程收发正常）—— 本环境 multicast 发现坏了；
    #   ② mode=client 时「跨进程收得到」✓ —— 客户端只连 router，不靠发现；
    #   ③ 所以【本体必须用 client】；同时把 multicast scouting 关掉，免得它去瞎发现。
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ZENOH_ENDPOINT]))
    session = zenoh.open(conf)
    log("   连上了")
    log("④ 订话题 …")
    session.declare_subscriber(T_REGISTER, lambda s: w.on_register(s))
    session.declare_subscriber(T_APPEAR, lambda s: w.on_appear(s))
    session.declare_subscriber(T_ASK, lambda s: _ask_and_forward(s, w, session))
    log("   订上了：%s ／ %s ／ %s" % (T_REGISTER, T_APPEAR, T_ASK))
    log("★ 本体进程起来了 —— 只认、只盖章、只转、只记")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        session.close()
        w.ledger.close()


def _ask_and_forward(smp, w, session):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    name = msg.get("action") or ""
    # ★★ 闸①：名字在册吗
    reg, why = w.recognize(name, msg.get("roles"))
    if reg is None:
        w.stamp("act", kind_of="reject", action=name, actor=msg.get("actor"), why=why)
        log("拒 %s ⇒ %s" % (name, why))
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why}, ensure_ascii=False))
        return
    # ★★ 闸②：这个主体获准做吗（照本体 permissions；默认拒绝）
    actor = msg.get("actor") or "world://anonymous"
    allowed, why2 = w.can_execute(actor, name)
    if not allowed:
        w.stamp("act", kind_of="reject-permit", action=name, actor=actor, why=why2)
        log("拒 %s ⇒ %s" % (name, why2))
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why2},
                                             ensure_ascii=False))
        return
    seq = w.stamp("act", kind_of="ask", action=name, actor=msg.get("actor"),
                  rid=msg.get("id"), params=msg.get("params"),
                  route=reg.get("registered_by_kind"))
    out = {"id": msg.get("id"), "at": seq, "action": name,
           "params": msg.get("params") or {}, "actor": msg.get("actor"),
           "route": reg.get("registered_by_kind")}
    log("转 %s（%s）⇒ %s" % (name, seq, reg.get("registered_by_kind")))
    session.put(T_EXEC, json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
