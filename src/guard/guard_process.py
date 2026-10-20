#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ worldcore 权限进程（guard）—— **单独一个进程**的「政策决定点（PDP）」。

★ 作者（逐字整理）：「做一个权限……我说的那个 LSM，它有接口吗？做个权限，单独做个进程」。
★ 现实（写清楚，不糊人）：
  - **LSM 是内核框架**（SELinux／AppArmor／Landlock／eBPF-LSM 都挂在它下面），**用户态进程不能自己注册一个 LSM**；
  - 用户态能用的接口：**Landlock**（进程给自己/子进程限文件访问，内核 ≥5.13）、
    **eBPF-LSM**（特权进程用 bpf() 把程序挂到 LSM 钩子上）、
    **AppArmor／SELinux 策略**（用户态生成/加载 profile，内核执行）、**fanotify 许可事件**（CAP_SYS_ADMIN）。
  - 所以本进程先做【决定】：拿本体（法）回答「谁能不能做某个动作」；执行（Landlock/AppArmor/eBPF）是下一步。

★ 它是什么：**独立进程** `src/guard/`，Unix socket（默认 `/run/aios/guard.sock`）一行一 JSON：
  `{"op":"ping"}` → `{"ok":true,...}`
  `{"op":"check","actor":"world://user/zhang","action":"sys.GetMemoryInfo"}` → `{"ok":true|false,"why":...}`
  `{"op":"describe"}` → 法里动作数/许可条文数
★ 它不是什么：不执行动作、不记账、不转发——记账仍只在本体。
"""
import datetime
import json
import os
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # repo 根（src/guard ⇒ 根）
LAW = os.environ.get("AIOS_LAW_JSON", os.path.join(ROOT, "src", "ontology", "world.json"))
SOCK = os.environ.get("AIOS_GUARD_SOCK", "/run/aios/guard.sock")


def _actor_class(actor):
    a = actor or ""
    if not a.startswith("world://"):
        return ""
    return a[len("world://"):].split("/", 1)[0]


class Guard:
    """★ 与本体同口径装载（law_loader＋sysknife＋契约＋许可归一），只读、做决定。"""

    def __init__(self, law_path=None):
        self.law_path = law_path or LAW
        self.actions = {}
        self.grants = {}
        try:
            for _p in (os.path.join(ROOT, "src", "ontology"), os.path.join(ROOT, "src")):
                if _p not in sys.path:
                    sys.path.insert(0, _p)
            from ontology_definition import build_aios_ontology  # noqa: E402
            o = build_aios_ontology()
            self.actions = dict(o.action_types)
            self.grants = (((o.metadata or {}).get("permissions") or {})
                           .get("grants") or {})
            self.loaded = "ontology_definition"
        except Exception as e:
            print("[guard] 装载本体失败，退回读法文件：%s" % e, file=sys.stderr)
            with open(self.law_path, encoding="utf-8") as f:
                law = json.load(f)
            self.actions = {a.get("id"): a for a in law.get("actions") or []}
            self.grants = (((law.get("metadata") or {}).get("permissions") or {})
                           .get("grants") or {})
            self.loaded = "law.json"

    def describe(self):
        try:
            import world_codes
            n_confirm = len(world_codes.CONFIRM_ACTIONS)
        except Exception:
            n_confirm = 0
        return {"actions": len(self.actions), "grants": len(self.grants),
                "confirm_actions": n_confirm,
                "law": self.law_path, "loaded": getattr(self, "loaded", "?")}

    def check(self, actor, action):
        ac = _actor_class(actor)
        if not ac:
            return {"ok": False, "why": "身份格式不对（要 world://<类>/<名>）",
                    "code": "IDENTITY_FORMAT_BAD"}
        if action not in self.actions:
            return {"ok": False, "why": "动作不在法里：%s" % action,
                    "code": "UNKNOWN_ACTION"}
        # ★ guard 弹窗：变更类动作由 agent 请求 ⇒ 不是静默放行/拒绝，而是「需人确认」
        if ac in ("agent", "presence"):
            try:
                import world_codes
                if world_codes.needs_confirm(action):
                    return {"ok": False, "decision": "confirm",
                            "why": "变更类动作需要人确认（guard 弹窗）",
                            "code": "CONFIRM_REQUIRED"}
            except Exception:
                pass
        g = self.grants.get(action) or {}
        scope = g.get("scope") or []
        if not scope:
            return {"ok": False, "why": "动作没有许可条文（变更类默认拒）",
                    "code": "PERMIT_DENIED"}
        for w in scope:
            if actor == w or actor.startswith(str(w).rstrip("/") + "/"):
                return {"ok": True, "why": "在 scope 里", "code": None}
        return {"ok": False,
                "why": "%s 不在 %s 的 scope 里（scope：%s）" % (actor, action, scope),
                "code": "PERMIT_DENIED"}


def handle_request(guard, req):
    """★ 协议一层（纯函数，好测）：一行 JSON 请求 → 一行 JSON 回答。"""
    if not isinstance(req, dict):
        return {"ok": False, "why": "请求不是对象"}
    op = req.get("op") or ""
    if op == "ping":
        out = {"ok": True, "what": "worldcore-guard"}
    elif op == "describe":
        out = {"ok": True, **guard.describe()}
    elif op == "check":
        out = guard.check(req.get("actor") or "", req.get("action") or "")
    else:
        out = {"ok": False, "why": "不认识的 op：%s" % op}
    out["at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return out


def _conn_loop(conn, guard):
    try:
        f = conn.makefile("rwb")
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line.decode("utf-8"))
            except Exception:
                req = None
            out = handle_request(guard, req)
            f.write((json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8"))
            f.flush()
    except Exception as e:
        print("[guard] 连接结束：%s" % e, file=sys.stderr)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def serve(guard, sock_path):
    """★ 生产：Unix socket（Linux）。测试可直接测 handle_request，无需启服务。"""
    if not hasattr(socket, "AF_UNIX"):
        raise RuntimeError("本机没有 AF_UNIX；guard 的生产 socket 只在 Linux 上跑")
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    os.makedirs(os.path.dirname(sock_path) or ".", exist_ok=True)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    os.chmod(sock_path, 0o660)
    srv.listen(16)
    print("[guard] ★ 权限进程起来了 —— 决定在它，执行另算；socket=%s" % sock_path, flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_conn_loop, args=(conn, guard), daemon=True).start()


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--check" in argv:
        i = argv.index("--check")
        actor = argv[i + 1] if len(argv) > i + 1 else ""
        action = argv[i + 2] if len(argv) > i + 2 else ""
        print(json.dumps(Guard().check(actor, action), ensure_ascii=False))
        return 0
    serve(Guard(), SOCK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
