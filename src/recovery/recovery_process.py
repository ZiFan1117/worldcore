# -*- coding: utf-8 -*-
"""★ worldcore 恢复边界进程（`src/recovery/`，一进程一夹）—— 世界快照的**只读**视察。

★ 借鉴 AI-OS L1「Recovery boundary」：恢复面能独立 inspect、可回滚、可隔离；
  v1 只做**只读**：列快照/分叉、读每份 meta（at/账行数/法 hash/字节数），把快照报成世界个体。
★ 它不是什么：不写快照、不恢复、不起外进程（这些走 scripts/release/world_snapshot.py 或后续动作）。
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
import recovery_ops  # noqa: E402
from gate.permit import verify, consume_via_ontology  # noqa: E402
from provider_auth import open_signed_session  # noqa: E402
from protocol.registration import provider_register  # noqa: E402

ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
REC_NAME = os.environ.get("AIOS_RECOVERY_NAME") or "recovery0"
T_APPEAR = "world/appear"
T_REGISTER = "world/register"
T_EXEC = "world/exec"
T_RESULT = "world/exec/result"

ACTIONS = [
    {"action": "recovery.list", "kind": "read", "why": "列世界快照/分叉（meta 现取，只读）"},
    {"action": "recovery.state", "kind": "read", "why": "读恢复边界状态（快照根/数量/最新）"},
]


def log(*a):
    print("[恢复边界]", *a, flush=True)


def me():
    """★ 只带法里声明的格（多塞会被 APPEAR_FIELDS_INVALID 拒；state() 里的 at 不进来）。"""
    ok, st = recovery_ops.state()
    st = st if ok else {}
    d = {"name": st.get("name") or REC_NAME,
         "state": st.get("state") or "running",
         "root": st.get("root") or recovery_ops.root()}
    for k in ("snapshots", "forks", "latest"):
        if st.get(k) is not None:
            d[k] = st[k]
    d["class"] = "recovery"
    d["reporter"] = "world://recovery/" + REC_NAME
    return d


def register_actions(session):
    provider_register(session, T_REGISTER, "recovery", REC_NAME, ACTIONS)
    log("① 注册动作 %d 个：%s" % (len(ACTIONS), "／".join(a["action"] for a in ACTIONS)))


def report_snapshots(session, limit=5):
    ok, d = recovery_ops.list_snapshots(limit)
    if not ok:
        return
    for e in (d.get("entries") or []):
        f = {"class": "snapshot", "path": e.get("path"), "name": e.get("name"),
             "kind": e.get("kind") or "snapshot",
             "reporter": "world://recovery/" + REC_NAME}
        for k in ("at", "ledger_rows", "law_sha256", "bytes", "files_count"):
            if e.get(k) is not None:
                f[k] = e[k]
        session.put(T_APPEAR, json.dumps(f, ensure_ascii=False))


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ENDPOINT]))
    session = open_signed_session(conf)
    log("连上总线 %s" % ENDPOINT)
    session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
    log("② 成为个体：recovery/%s（root=%s）" % (REC_NAME, recovery_ops.root()))
    register_actions(session)
    # ★ 身份闸要求报告者先被本体收下；appear 与 snapshot 同一发布者但可能被并行处理，
    #   这里等一拍再报快照（并在下面 60s 周期里重报，最终一致）。
    time.sleep(1.0)
    report_snapshots(session)
    log("③ 已报快照个体（最近 5 份）")

    def on_exec(smp):
        try:
            msg = json.loads(smp.payload.to_string())
        except Exception:
            return
        if msg.get("route") not in (None, "", "recovery"):
            return
        action, params = msg.get("action") or "", msg.get("params") or {}
        rid = msg.get("id") or ""
        ok, why = verify(msg.get("permit"), action, params)
        if ok:
            ok, why = consume_via_ontology(session, msg.get("permit"), action, params)
        if not ok:
            session.put(T_RESULT, json.dumps({
                "id": rid, "action": action, "ok": False, "body": None,
                "by": "recovery/" + REC_NAME, "code": "PERMIT_DENIED",
                "error": "没有本体的许可（凭据校验不过）：%s" % why}, ensure_ascii=False))
            return
        ok2, body = recovery_ops.dispatch(action, params)
        log("答 %s ⇒ ok=%s" % (action, ok2))
        session.put(T_RESULT, json.dumps({
            "id": rid, "action": action, "ok": ok2, "body": body if ok2 else None,
            "error": None if ok2 else body, "by": "recovery/" + REC_NAME},
            ensure_ascii=False))

    session.declare_subscriber(T_EXEC, on_exec)
    log("④ 订上 %s（route=recovery）" % T_EXEC)
    while True:
        time.sleep(60)
        session.put(T_APPEAR, json.dumps(me(), ensure_ascii=False))
        report_snapshots(session)
        log("⑤ 刷新：%s" % me().get("latest"))


if __name__ == "__main__":
    main()
