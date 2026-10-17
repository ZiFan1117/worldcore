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
T_ASK = "world/ask"
T_EXEC = "world/exec"
T_EXEC_RESULT = "world/exec/result"
T_ASK_RESULT = "world/ask/result"

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
        self.seq = 0            # ★ 号源，只有它能发
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
        """★★ 盖号 ＋ 落账 —— 这是【同一个动作】。返回 seq。"""
        self.seq += 1
        row = {"seq": self.seq, "family": family,
               "at": int(time.time()), **fields}
        self.ledger.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.ledger.flush()
        return self.seq

    # ── ① 认 ──
    def recognize(self, name, roles=None):
        """查注册表：在册吗？谁能用？★ 不在册就拒。"""
        reg = self.registry.get(name)
        if reg is None:
            return None, "不在册（世界不认识这个名字）"
        need = reg.get("required_roles") or []
        if roles is not None and need and not any(r in roles for r in need):
            return None, "角色不够（要 %s，你是 %s）" % (need, roles)
        return reg, None

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
        log("注册 %s ⇒ %s（seq=%d，在册 %d 条）" % (name or "?", why, seq, len(self.registry)))
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
    session.declare_subscriber(T_ASK, lambda s: _ask_and_forward(s, w, session))
    session.declare_subscriber(T_EXEC_RESULT, lambda s: _result_and_reply(s, w, session))
    log("   订上了：%s ／ %s ／ %s" % (T_REGISTER, T_ASK, T_EXEC_RESULT))
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
    reg, why = w.recognize(name, msg.get("roles"))
    if reg is None:
        w.stamp("act", kind_of="reject", action=name, actor=msg.get("actor"), why=why)
        log("拒 %s ⇒ %s" % (name, why))
        session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "ok": False, "why": why},
                                             ensure_ascii=False))
        return
    seq = w.stamp("act", kind_of="ask", action=name, actor=msg.get("actor"),
                  rid=msg.get("id"), params=msg.get("params"),
                  route=reg.get("registered_by_kind"))
    out = {"id": msg.get("id"), "seq": seq, "action": name,
           "params": msg.get("params") or {}, "actor": msg.get("actor"),
           "route": reg.get("registered_by_kind")}
    log("转 %s（seq=%d）⇒ %s" % (name, seq, reg.get("registered_by_kind")))
    session.put(T_EXEC, json.dumps(out, ensure_ascii=False))


def _result_and_reply(smp, w, session):
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception:
        return
    seq = w.stamp("act", kind_of="result", rid=msg.get("id"),
                  action=msg.get("action"), ok=msg.get("ok"), body=msg.get("body"))
    log("结果 %s（seq=%d，ok=%s）" % (msg.get("action"), seq, msg.get("ok")))
    session.put(T_ASK_RESULT, json.dumps({"id": msg.get("id"), "seq": seq, **msg},
                                         ensure_ascii=False))


if __name__ == "__main__":
    main()
