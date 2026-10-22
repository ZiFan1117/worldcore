# -*- coding: utf-8 -*-
"""★ worldcore 文件进程（`src/fs/`，一进程一夹）—— **语义文件的只读服务 v1**。

★ 借鉴 AI-OS L2「AIOS-FS」的形状：文件＝语义对象、路径是视图；
  v1 只做**只读**（stat/list/hash/read_text）；写路径（版本/指针/证据）二期。
★ 它做什么：报个体（fs）→ 注册动作（file.* / fs.state）→ 订 world/exec（route=fs）
  → 验 permit + 核销 → 执行（白名单根、防符号链接逃逸、秘密文件拒读）→ 回 world/exec/result
  → 把读到的文件也报成 file 个体（供世界查询/事件）。
★ 它不是什么：不写文件、不裁决许可、不记账；出向仍只许 computer。
"""
import json
import os
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import zenoh  # noqa: E402
import fs_ops  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol import sdk as protocol_sdk  # noqa: E402
from protocol.keys import LEGACY as TOPIC  # noqa: E402
from protocol.keys import T as P2_TOPIC  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
FS_NAME = os.environ.get("AIOS_FS_NAME") or "fs0"
T_APPEAR = TOPIC["appear"]
T_REGISTER = TOPIC["register"]
T_EXEC = TOPIC["exec"]
T_RESULT = TOPIC["exec_result"]

ME = {"class": "fs", "name": FS_NAME, "state": "running",
      "roots": ":".join(fs_ops.roots()),
      "reporter": "world://fs/" + FS_NAME}

ACTIONS = [
    {"action": "file.stat", "kind": "read", "why": "读文件/目录元数据（只读、白名单根）"},
    {"action": "file.list", "kind": "read", "why": "列目录（只读、白名单根）"},
    {"action": "file.hash", "kind": "read", "why": "算普通文件 sha256（只读）"},
    {"action": "file.read_text", "kind": "read", "why": "读文本（截断/拒秘密文件）"},
    {"action": "fs.state", "kind": "read", "why": "读文件进程状态（白名单根）"},
]
REPORT_ACTIONS = ("file.stat", "file.hash", "file.read_text")


def log(*a):
    print("[文件进程]", *a, flush=True)


def register_actions(session):
    bindings = [{
        "action": a["action"],
        "function": a["action"].split(".", 1)[-1],
        "required_roles": ["fs"],
        "registered_by_kind": "fs",
    } for a in ACTIONS]
    msg = protocol_sdk.build_register(
        "world://fs/" + FS_NAME,
        "world://ontology",
        {"id": "world://fs/" + FS_NAME, "object_type": "fs"},
        bindings=bindings,
    )
    session.put(T_REGISTER, protocol_sdk.encode(msg))
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def report_file(session, action, body):
    """★ 读到的文件也报成 file 个体（世界可查；只报元数据，不报正文）。"""
    if not isinstance(body, dict) or not body.get("path"):
        return
    fields = {"class": "file", "path": str(body["path"]),
              "name": str(body.get("name") or os.path.basename(str(body["path"]))),
              "kind": str(body.get("kind") or "file"),
              "reporter": "world://fs/" + FS_NAME}
    for k in ("size", "mtime", "sha256", "root"):
        if body.get(k) is not None:
            fields[k] = body[k]
    if fields.get("kind") == "link":
        fields.pop("sha256", None)
    session.put(T_APPEAR, json.dumps(fields, ensure_ascii=False))


def execute(action, params):
    ok, body = fs_ops.dispatch(action, params or {}, FS_NAME)
    return ok, body


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    session.put(T_APPEAR, json.dumps(ME, ensure_ascii=False))
    log("② 成为个体：fs/%s（roots=%s）" % (FS_NAME, ME["roots"]))
    register_actions(session)

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        route = msg.get("route")
        if route not in (None, "", "fs"):
            return
        action, params, rid = msg.get("action") or "", msg.get("params") or {}, msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            log("拒 %s（%s）：没有本体许可" % (action, rid))
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "fs/" + FS_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        ok2, body = execute(action, params)
        if ok2 and action in REPORT_ACTIONS:
            try:
                report_file(session, action, body)
            except Exception as e:                          # noqa: BLE001
                log("报文件个体失败：%s" % e)
        log("执行 %s ⇒ ok=%s" % (action, ok2))
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2,
            "body": body if ok2 else None,
            "error": None if ok2 else body,
            "by": "fs/" + FS_NAME}, ensure_ascii=False))

    def on_p2_exec(smp):
        """P2 call 路径：ontology → world/call/exec → fs → world/call/exec/result。"""
        try:
            msg = protocol_sdk.parse(smp.payload.to_string())
        except Exception:
            return
        if msg.get("type") != "call":
            return
        data = msg.get("data") or {}
        action = data.get("fn") or ""
        params = data.get("args") if isinstance(data.get("args"), dict) else {}
        rid = msg.get("id") or ""
        ok, why = verify(data.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, data.get("permit"), action, params)
        if not ok:
            out = protocol_sdk.build_result("world://fs/" + FS_NAME, "world://ontology",
                                            rid, False, error={"code": "PERMIT_DENIED", "detail": why})
            session.put(P2_TOPIC["call_exec_result"], protocol_sdk.encode(out))
            return
        ok2, body = execute(action, params)
        out = protocol_sdk.build_result("world://fs/" + FS_NAME, "world://ontology",
                                        rid, ok2, result=body if ok2 else None,
                                        error=None if ok2 else {"code": "EXEC_FAILED", "detail": body})
        session.put(P2_TOPIC["call_exec_result"], protocol_sdk.encode(out))
        log("P2 执行 %s ⇒ ok=%s" % (action, ok2))

    session.declare_subscriber(T_EXEC, on_exec)
    session.declare_subscriber(P2_TOPIC["call_exec"], on_p2_exec)
    log("③ 订上 %s（route=fs）＋ P2 call_exec" % T_EXEC)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
