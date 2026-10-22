# -*- coding: utf-8 -*-
"""★ worldcore 语义文件系统进程（`src/worldfs/`，一进程一夹）—— worldfs。

★ 借鉴 AI-OS L2 的形状：对象/不可变版本/内容寻址 blob/路径指针/事务；
  但只按 worldcore 的规矩：外部只能 world/ask，写必须人确认＋permit＋账；不碰宿主文件。
★ P1：自有命名空间 /worldfs、文本 ≤1MB、版本/回滚、无 FUSE。
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "src", "ontology"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import zenoh  # noqa: E402
import worldfs_ops  # noqa: E402
from worldfs_store import WorldFS  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol.registration import provider_register  # noqa: E402
from protocol.provider_p2 import install as install_p2  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
WFS_NAME = os.environ.get("AIOS_WORLDFS_NAME") or "worldfs0"
WFS_ROOT = os.environ.get("AIOS_WORLDFS_ROOT") or "/var/lib/aios/worldfs"
T_APPEAR = "world/appear"
T_REGISTER = "world/register"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"

ACTIONS = [
    {"action": "worldfs.list", "kind": "read", "why": "列目录（worldfs 命名空间）"},
    {"action": "worldfs.stat", "kind": "read", "why": "读路径元数据（对象/版本/指针）"},
    {"action": "worldfs.read", "kind": "read", "why": "读文件文本（校验 sha256）"},
    {"action": "worldfs.versions", "kind": "read", "why": "读对象版本历史"},
    {"action": "worldfs.state", "kind": "read", "why": "读 worldfs 状态"},
    {"action": "worldfs.write", "kind": "change", "why": "写文件（新版本+移指针；人确认）"},
    {"action": "worldfs.mkdir", "kind": "change", "why": "建目录（人确认）"},
    {"action": "worldfs.remove", "kind": "change", "why": "删路径（对象退休；人确认）"},
    {"action": "worldfs.restore", "kind": "change", "why": "回滚指针到旧版本（人确认）"},
    {"action": "worldfs.rename", "kind": "change", "why": "改名/移动路径指针（人确认；对象身份不变）"},
    {"action": "worldfs.snapshot", "kind": "read", "why": "读当前全局 epoch/root（只读快照）"},
    {"action": "worldfs.history", "kind": "read", "why": "读某路径的追加历史（含墓碑）"},
    {"action": "worldfs.get", "kind": "read", "why": "按 world://wfile/… 或 world://wversion/… 读对象/版本"},
]


def log(*a):
    print("[worldfs]", *a, flush=True)


def me(store):
    st = store.state()
    return {"class": "worldfs", "name": WFS_NAME, "state": "running",
            "root": st["root"], "objects": st["objects"], "paths": st["paths"],
            "epoch": st.get("epoch"), "root_sha": st.get("root_sha"),
            "reporter": "world://worldfs/" + WFS_NAME}


def register_actions(session):
    provider_register(session, T_REGISTER, "worldfs", WFS_NAME, ACTIONS)
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def _put(session, payload):
    """★ 只把非 None/非空的格放进 appear（法里 optional 的格不硬塞 None）。"""
    payload = {k: v for k, v in payload.items() if v is not None and v != ""}
    payload["reporter"] = "world://worldfs/" + WFS_NAME
    session.put(T_APPEAR, json.dumps(payload, ensure_ascii=False))


def _report_path(session, st):
    """★ 把内容/版本/路径报成本体个体；本地不存 actor/intent/时间（账在本体）。"""
    if not isinstance(st, dict) or not st.get("path"):
        return
    path = st["path"]
    seq = st.get("seq")
    if seq is None:
        seq = st.get("current_seq")
    if seq is None:
        seq = st.get("removed_seq")
    _put(session, {"class": "wpath", "path": path, "obj_id": st.get("obj_id"),
                   "seq": seq, "kind": st.get("kind"),
                   "ref": "world://wfile/" + str(st.get("obj_id") or "")})
    name = path.rsplit("/", 1)[-1] or "worldfs"
    _put(session, {"class": "wfile", "obj_id": st.get("obj_id"), "name": name,
                   "kind": st.get("kind"), "state": st.get("obj_state") or "active",
                   "current_seq": seq, "blob_sha256": st.get("blob_sha256"),
                   "size": int(st.get("size") or 0),
                   "ref": "world://wfile/" + str(st.get("obj_id") or "")})


def _report_version(session, ver):
    if not isinstance(ver, dict) or not ver.get("ver_id") or not ver.get("obj_id"):
        return
    _put(session, {"class": "wversion", "ver_id": ver["ver_id"],
                   "obj_id": ver.get("obj_id"), "seq": ver.get("seq"),
                   "name": "%s@%s" % (ver.get("obj_id"), ver.get("seq")),
                   "blob_sha256": ver.get("blob_sha256"),
                   "size": int(ver.get("size") or 0),
                   "ref": "world://wversion/" + str(ver.get("ver_id"))})


def _after_success(session, action, body):
    """★ 读/写成功后，把内容/版本/路径报成个体（供查询/事件）；不落本地账。"""
    if not isinstance(body, dict):
        return
    if action in ("worldfs.write", "worldfs.mkdir", "worldfs.restore",
                  "worldfs.remove", "worldfs.rename"):
        _report_path(session, body)
        if action in ("worldfs.write", "worldfs.restore"):
            _report_version(session, {"ver_id": body.get("ver_id"), "obj_id": body.get("obj_id"),
                                      "seq": body.get("seq"),
                                      "blob_sha256": body.get("blob_sha256"),
                                      "size": body.get("size")})
        return
    if action in ("worldfs.stat", "worldfs.read"):
        _report_path(session, body)
        _report_version(session, {"ver_id": body.get("ver_id"), "obj_id": body.get("obj_id"),
                                  "seq": body.get("seq"),
                                  "blob_sha256": body.get("blob_sha256"),
                                  "size": body.get("size")})
    elif action == "worldfs.list":
        for e in (body.get("entries") or [])[:20]:
            _report_path(session, e)
    elif action == "worldfs.versions":
        for v in (body.get("versions") or [])[:20]:
            v = dict(v)
            v.setdefault("obj_id", body.get("obj_id"))
            _report_version(session, v)


def main():
    store = WorldFS(WFS_ROOT)
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    session.put(T_APPEAR, json.dumps(me(store), ensure_ascii=False))
    log("② 成为个体：worldfs/%s（root=%s）" % (WFS_NAME, WFS_ROOT))
    register_actions(session)

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        if msg.get("route") not in (None, "", "worldfs"):
            return
        action = msg.get("action") or ""
        params = dict(msg.get("params") or {})
        rid = msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "worldfs/" + WFS_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        params["_actor"] = msg.get("actor") or "world://worldfs/unknown"
        ok2, body = worldfs_ops.dispatch(store, action, params)
        log("执行 %s ⇒ ok=%s" % (action, ok2))
        if ok2:
            try:
                _after_success(session, action, body)
            except Exception as e:                              # noqa: BLE001
                log("报个体失败：%s" % e)
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2, "body": body if ok2 else None,
            "error": None if ok2 else body, "by": "worldfs/" + WFS_NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    install_p2(session, "worldfs", WFS_NAME,
               lambda a, p: worldfs_ops.dispatch(store, a, dict(p or {})))
    log("③ 订上 %s（route=worldfs）＋ P2 call_exec" % T_EXEC)
    while True:
        time.sleep(300)
        session.put(T_APPEAR, json.dumps(me(store), ensure_ascii=False))


if __name__ == "__main__":
    main()
