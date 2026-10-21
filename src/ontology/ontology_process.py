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
  · world/exec            → 转发给计算机
  · world/exec/result     ← 计算机回结果
  · world/ask/result      → 回传给请求方
"""

import datetime
import json
import os
import sys
import time
from gate import identity
from gate import permit
from query import world_query
from gate import ask_path
from gate import action_contract
from gate.world_codes import reject_category

import zenoh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                      # 本原子目录（ontology_definition）
sys.path.insert(0, os.path.dirname(HERE))     # src/ 根（foundry_ontology 目录）
from law.ontology_definition import build_aios_ontology  # noqa: E402
from ingest.appear import ingest_appear  # noqa: E402
from provider_auth import ProviderAuthError, auth_enabled, verify_message  # noqa: E402
from foundry_ontology.engine.object_store import ObjectStore  # noqa: E402

# ★★★ 2026-10-17 裁（作者逐字）：「使用他全套的东西呀，包括这个 link 啥的都用呀」
#   ⇒ ABox 接上：个体不再只活在账里，而是【真的存在 ObjectStore 里】（SQLite 持久化）。
STORE_PATH = os.environ.get("AIOS_STORE_DB", "/var/lib/aios/ontology/objects.db")

# ── 话题（与 Rust 侧同一套）──
T_REGISTER = "world/register"
T_REGISTER_OK = "world/register/result"
T_APPEAR = "world/appear"
T_ALIVE = "world/alive"
T_APPEAR = "world/appear"   # ★★ 进程上报（「我起来了，我是谁」）
T_ASK = "world/ask"
T_EXEC_RESULT = "world/exec/result"
T_QUERY = "world/query"              # ★★ 查世界（★ 作者令：所有交互过本体）
T_QUERY_RESULT = "world/query/result"
T_NOTICE = "world/notice"
T_EVENT = "world/event"             # ★ 事件流：账落完 ⇒ 推给订阅者（人/agent 双向）            # ★★ 宣告入口（★ 作者裁：所有交互过本体 ⇒ 帧也过）
T_UI_FRAME = "world/ui/frame"        # 本体【转】给 GUI 的那一面   # ★ 结果先回本体（★ 所有交互过本体）
T_EXEC = "world/exec"
T_ASK_RESULT = "world/ask/result"   # ★ 请求方订这一个就够（本体拒 ⇒ 发这里；计算机跑完 ⇒ 也发这里）
# ★★★ 2026-10-17 裁：**本体不再碰结果** —— 退订 world/exec/result、不记结果、不回转。
#     ★ 原则：★ 「谁干的谁报」—— 结果由计算机直接回给请求方，本体不在那条路上。

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
        self.appeared = {}      # ★ 报过到的个体（class/name）—— 判「每报一个都要能核验」
        # ★★ 计算机报来的「我能做什么」（★ 可用性，模型要用）
        self.computer_caps = {"available": [], "unsupported": [], "at": None, "by": None}
        self._load_registry()
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        self.ledger = open(LEDGER_PATH, "a", encoding="utf-8")
        self.publish = None      # ★ 由 main 注入 session.put；stamp 后推 world/event
        # ★★ 一号一用的账【在本体】：用过哪些凭证号，从盘上读回（重启不忘）
        self.used_permits = permit.load_used(permit.ledger_path(self))
        # ★★ ABox：个体表（★ P 的 ObjectStore，SQLite 持久化）
        os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
        self.store = ObjectStore(self.ontology, db_path=STORE_PATH)
        # ★★ 报到记录从【个体表】读回（不是只活在内存里）⇒ 本体重启后不必等人家重新报到
        self.appeared = identity.load_appeared(self.ontology, self.store)
        # ★★ 每类的「提供者」（状态所有权；见 world_codes.AUTHORITY_REPORTERS）
        self.reporters = {tid: ((ot.metadata or {}).get("_authority") or {}).get("reporters") or []
                          for tid, ot in self.ontology.object_types.items()}
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
        # ★★ 2026-10-19（P8）：账落完 ⇒ 推一条【事件】（只公开字段；params/body/why 一律不带）
        _ev_ok = fields.get("kind_of") in ("ask", "reject", "result", "appear", "register") \
            or (fields.get("kind_of") == "notice" and fields.get("notice_kind") == "ui.act"
                and fields.get("ui_action"))
        # ★ 2026-10-20 实测发现：appear/register 的 family 是 "change"，原来只放 "act"
        #   ⇒ 数据管道的 appear 从不推事件，界面只能靠轮询（事件钩子等于死的）。这里放行 change。
        if self.publish and family in ("act", "change") and _ev_ok:
            ev = {"kind": "world.event", "at": at,
                  "kind_of": fields.get("kind_of"),
                  "action": fields.get("action") or fields.get("ui_action"),
                  "component": fields.get("component"),
                  "actor": fields.get("actor"), "ok": fields.get("ok"),
                  "code": fields.get("code"), "category": fields.get("category"),
                  "subject": fields.get("subject"),
                  "space": _space_of_actor(fields.get("actor"))}
            try:
                self.publish(T_EVENT, json.dumps(ev, ensure_ascii=False))
            except Exception as e:
                log("事件推送失败：%s" % e)
        return at

    def reject(self, code, action=None, actor=None, why="", **kw):
        """★ 每次拒绝都落账，带【闭集码】＋类别（借自订单样板：拒绝码是给机器看的）。

        ★ 码不在闭集 ⇒ 类别记 system 并留痕（判据 C29 会抓「谁发了不在闭集的码」）。
        """
        cat = reject_category(code) or "system"
        log("拒 %s ⇒ [%s/%s] %s" % (action or "?", code, cat, why))
        return self.stamp("act", kind_of="reject", code=code, category=cat,
                          action=action, actor=actor, why=why, **kw)

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
        """★ 本体内部数据管道的入口（接收/校验/建更新在 ingest/appear.py）。"""
        return ingest_appear(self, smp, log=log)

    # ── ★★ 执行面 ①：谁能做这个动作（T-342 真做）──
    def can_execute(self, actor, capability):
        """★ 照本体 `permissions` 判「这个主体能不能做这个动作」。

        ★ 口径：default=deny ⇒ 没条文拒；grants[cap].**scope** 不在就拒；scope 前缀匹配。
        ★★ 2026-10-19 修：原先读的是 `who` —— 借来的条文里 `who` 是**授权者**、`scope` 才是**生效许可**；
           同词两义会让「本该放行的主体」被静默拒掉（现取：presence/omarchy 查 notice.mute 被判拒）。
        ★ 返回 (True, None) 或 (False, 为什么)。
        """
        if not actor:
            return False, "没有身份（★ 请求要带 actor，或带票）"
        perms = (self.ontology.metadata or {}).get("permissions") or {}
        grants = perms.get("grants") or {}
        g = grants.get(capability)
        if g is None:
            return False, "这个动作没有许可条文（permissions.default = %r ⇒ 默认拒绝）" % perms.get("default")
        scope = g.get("scope") or []
        for w in scope:
            if actor == w or actor.startswith(w.rstrip("/") + "/"):
                return True, None
        return False, "actor=%s 不在许可里（scope：%s）" % (actor, scope)

    # ── ② 注册（安装时一次）──
    def on_register(self, smp):
        try:
            reg = json.loads(smp.payload.to_string())
        except Exception as e:
            log("注册：消息不是 JSON（%s）" % e)
            return
        if auth_enabled():
            try:
                verify_message("world/register", reg)
            except ProviderAuthError as e:
                self.reject(e.code, action="register", why=e.why)
                log("注册被拒（%s）：%s" % (e.code, e.why))
                return None
        reg.pop("_auth", None)
        name = reg.get("action") or ""
        missing = [k for k in ("action", "function", "registered_by",
                               "registered_by_kind", "required_roles")
                   if not reg.get(k)]
        ok = not missing
        why = "收下" if ok else ("缺格 " + ",".join(missing))
        if ok:
            seq = self.stamp("act", kind_of="register", actor=reg.get("registered_by", "?"),
                             action=name, ok=True, why=why, body=reg)
            self.registry[name] = reg
            self._append_registry(reg)
        else:
            seq = self.reject("REGISTER_INCOMPLETE", action=name,
                              actor=reg.get("registered_by", "?"), why=why, body=reg)
        log("注册 %s ⇒ %s（%s，在册 %d 条）" % (name or "?", why, seq, len(self.registry)))
        return seq



def _space_of_actor(actor):
    """★ 事件属于哪个空间：人/空间进程 ⇒ 自己的；agent ⇒ 当前登录人的（单用户假设）。"""
    actor = actor or ""
    if not actor.startswith("world://"):
        return ""
    cls, _, name = actor[len("world://"):].partition("/")
    if cls in ("user", "space"):
        return "space:" + name
    if cls == "agent":
        for t in (getattr(identity, "_TICKETS", {}) or {}).values():
            if (t.get("expires_at") or 0) > time.time():
                return "space:" + (t.get("user") or "")
    return ""


def main():
    w = World()
    log("③ 连总线 %s …" % ZENOH_ENDPOINT)
    conf = zenoh.Config()
    # ★★★ 实测出来的三条（2026-10-17，VM 上四种组合都试过）：
    #   ① mode=peer 时「跨进程收不到」（同进程收发正常）—— 本环境 multicast 发现坏了；
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ZENOH_ENDPOINT]))
    session = zenoh.open(conf)
    log("   连上了")
    w.publish = session.put        # ★ P8：事件流从这里推
    log("④ 订话题 …")
    session.declare_subscriber(T_REGISTER, lambda s: w.on_register(s))
    session.declare_subscriber(T_APPEAR, lambda s: w.on_appear(s))
    session.declare_subscriber(T_ASK, lambda s: ask_path.handle(s, w, session, log))
    session.declare_subscriber(T_EXEC_RESULT, lambda s: _result_and_reply(s, w, session))
    session.declare_subscriber(T_QUERY, lambda s: world_query.handle(s, w, session, log))
    session.declare_subscriber(T_NOTICE, lambda s: _notice_and_forward(s, w, session))
    # ★★ 一号一用：执行器来问「这张凭证用过没有」—— 记账在本体（见 permit.consume）
    session.declare_subscriber(permit.T_CONSUME, lambda s: permit.handle_consume(s, w, session, log))
    log("   订上了：%s ／ %s ／ %s ／ %s ／ %s ／ %s" % (T_REGISTER, T_APPEAR, T_ASK, T_EXEC_RESULT, T_QUERY, T_NOTICE))
    log("★ 本体进程起来了 —— 只认、只盖章、只转、只记")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        session.close()
        w.ledger.close()


def _result_and_reply(smp, w, session):
    """★ 计算机跑完 ⇒ 结果先回本体 ⇒ 本体记账 ⇒ 判「谁能看」⇒ 回给请求方。

    ★★ 2026-10-17 裁：**所有交互都过本体** —— 结果也不例外。
    """
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    if auth_enabled():
        try:
            verify_message("world/exec/result", msg)
        except ProviderAuthError as e:
            w.reject(e.code, action="exec/result", why=e.why)
            log("结果被拒（%s）：%s" % (e.code, e.why))
            return
    msg.pop("_auth", None)
    _code = msg.get("code")
    at = w.stamp("act", kind_of="result", rid=msg.get("id"),
                  action=msg.get("action"), ok=msg.get("ok"), body=msg.get("body"),
                  code=_code, category=(reject_category(_code) or "system") if _code else None)
    log("结果 %s（%s，ok=%s）⇒ 回请求方" % (msg.get("action"), at, msg.get("ok")))
    session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "at": at, **msg},
                                         ensure_ascii=False))


def _notice_and_forward(smp, w, session):
    """★★ 宣告过本体 —— ★ 作者令（逐字）：「**而且是要经过我的本体**」。

    ★ 谁发：★ agent ／ 任何一方想「广播一件事」。
    ★ 本体干什么：★ ① 认（有没有 kind）★ ② 盖章 ★ ③ 记账 ★ ④ 转
    ★ 本体【不】干什么：★ 不看内容（那是信纸，★ 机制只看信封）。
    """
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    kind = msg.get("kind") or ""
    if not kind:
        w.reject("BAD_MESSAGE", action="notice", why="宣告没有 kind")
        return
    # ★ 认：宣告的种类在册吗（families 里登记的）
    # ★ P8：人的动作（ui.act）要把动作名/组件带进账（事件流才能看见“人点了什么”）
    _extra = {}
    if kind == "ui.act":
        _extra = {"ui_action": msg.get("name"), "component": msg.get("component")}
    at = w.stamp("act", kind_of="notice", notice_kind=kind,
                  by=msg.get("by"), about=msg.get("about"),
                  size=len(smp.payload.to_string()), **_extra)
    # ★ notice.mute 的生效点：被静音的种类照样落账，但不再转发给界面
    if kind in (getattr(w, "muted_notice_kinds", None) or set()):
        log("通告 kind=%s 已被静音：记账但不转发" % kind)
        return
    # ★★★ 「给谁看」—— ★ 作者裁（逐字）：「这不是有票吗？票不是决定了是给哪个人的吗？
    #    发布能不能给这个人看，那肯定是能的呀。那谁登录进来，你就给谁看呀」
    #    ★ 所以：★ 从 by 推出【这张画布属于谁】⇒ 盖上 to ⇒ 呈现拿【票】来对。
    by = msg.get("by") or ""
    to = ""
    # ★★ 规则一：★ 空间发的 ⇒ 给【那个空间的主人】（★ 从 by 直接推）
    if by.startswith("world://space/"):
        to = "space:" + by[len("world://space/"):].split("/")[0]
    else:
        # ★★ 规则二：★ 别的（agent／presentation／…）⇒ 给【当前登录的人】
        #    ★ 作者裁（逐字）：「谁登录进来，你就给谁看呀」
        #    ★ 本体【记着票】⇒ 有票的人就是"登录的人"；多个票 ⇒ 每人一份（这里取第一张）。
        _who = [t for t in (list(identity._TICKETS.values())) if t["expires_at"] > time.time()]
        if _who:
            to = "space:" + _who[0]["user"]
        else:
            # ★ 没人登录 ⇒ 公开（谁都能看）；★ 这是"还没人登录"时的过渡
            to = ""
    # ★ 包一层信封：★ 本体【不碰信纸】（frame 原样），★ 但把【章】和【给谁】写在信封上
    env = {"kind": kind, "by": by, "about": msg.get("about"),
           "to": to, "stamped_at": at, "size": len(smp.payload.to_string()),
           "frame": msg.get("frame")}
    log("宣告 %s（%s，%d 字节）⇒ 转给界面（to=%s）" % (kind, at, env["size"], to or "（公开）"))
    session.put(T_UI_FRAME, json.dumps(env, ensure_ascii=False))


if __name__ == "__main__":
    main()


# ★ 判据（c3/c20/c29/c31/c32）仍在调这个名字：保留别名（实现已搬到 ask_path.py）
_ask_and_forward = ask_path.handle
