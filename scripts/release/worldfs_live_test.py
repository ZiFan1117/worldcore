#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM 上的 worldfs 验收（真总线、真动作、真账、真存储）。

用法（VM）：
  python3 /root/aios/scripts/release/worldfs_live_test.py
"""
import sys
import json
import subprocess
import time

import zenoh
sys.path.insert(0, "/usr/lib/aios/src/ontology")
from bus_auth import open_bus  # noqa: E402

T_ASK = "world/ask"
T_ASK_RESULT = "world/ask/result"
T_QUERY = "world/query"
T_QUERY_RESULT = "world/query/result"


class Bus:
    def __init__(self):
        conf = zenoh.Config()
        conf.insert_json5("mode", '"client"')
        conf.insert_json5("scouting/multicast/enabled", "false")
        conf.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
        self.z = open_bus(conf)
        self.asks, self.queries = {}, {}
        self.z.declare_subscriber(T_ASK_RESULT, lambda m: self._on(m, self.asks))
        self.z.declare_subscriber(T_QUERY_RESULT, lambda m: self._on(m, self.queries))

    def _on(self, m, box):
        try:
            d = json.loads(m.payload.to_string())
        except Exception:
            return
        box[d.get("id")] = d

    def _wait(self, box, rid, timeout=10):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if rid in box:
                return box[rid]
            time.sleep(0.05)
        return {"ok": False, "why": "timeout"}

    def ask(self, rid, action, params, ticket=None, actor=None, timeout=15):
        msg = {"id": rid, "action": action, "params": params or {}}
        if ticket:
            msg["ticket"] = ticket
        if actor:
            msg["actor"] = actor
        self.z.put(T_ASK, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.asks, rid, timeout)

    def query(self, rid, kind, ticket=None, timeout=15, **extra):
        msg = {"id": rid, "kind": kind}
        msg.update(extra)
        if ticket:
            msg["ticket"] = ticket
        self.z.put(T_QUERY, json.dumps(msg, ensure_ascii=False))
        return self._wait(self.queries, rid, timeout)

    def close(self):
        try:
            self.z.close()
        except Exception:
            pass


def led_count(action):
    try:
        out = subprocess.run(["grep", "-a", action, "/var/lib/aios/ontology/ledger.jsonl"],
                             capture_output=True, text=True).stdout.splitlines()
        return len([ln for ln in out if '"ok": true' in ln or '"ok":true' in ln])
    except Exception:                                      # noqa: BLE001
        return 0


def main():
    bus = Bus()
    out = {"checks": []}
    base = "/worldfs/notes"
    fname = "hello-live-%d.txt" % int(time.time())

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:220]})
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:180] if detail else ""))

    try:
        a = bus.ask("wfs-auth", "identity.authenticate", {"user": "zhang", "secret": "0"})
        tk = ((a.get("body") or {}).get("ticket") or "") if a.get("ok") else ""
        check("登录拿票", bool(tk), tk[:14])
        actor = "world://user/zhang"

        st = bus.ask("wfs-state", "worldfs.state", {}, ticket=tk, actor=actor)
        sb = st.get("body") or {}
        check("worldfs.state 可读", bool(st.get("ok")) and "root" in sb,
              "root=%r objects=%r" % (sb.get("root"), sb.get("objects")))
        blobs0 = sb.get("blobs")

        mk = bus.ask("wfs-mkdir", "worldfs.mkdir",
                     {"path": base, "intent": "live test: 建 notes 目录"}, ticket=tk, actor=actor)
        _mker = str(mk.get("error") or mk.get("body") or "")
        check("worldfs.mkdir", bool(mk.get("ok")) or "已存在" in _mker, _mker[:120])

        w1 = bus.ask("wfs-write1", "worldfs.write",
                     {"path": base + "/" + fname, "text": "hello world",
                      "intent": "live test: 写第一版"}, ticket=tk, actor=actor)
        b1 = w1.get("body") or {}
        check("worldfs.write 第一版", bool(w1.get("ok")) and b1.get("seq") == 1,
              "seq=%r sha=%s…" % (b1.get("seq"), str(b1.get("blob_sha256"))[:12]))
        check("写入返回 blob/版本", len(str(b1.get("blob_sha256") or "")) == 64
              and bool(b1.get("ver_id")), "ver=%r" % (b1.get("ver_id"),))
        obj_id = b1.get("obj_id")

        r1 = bus.ask("wfs-read1", "worldfs.read",
                     {"path": base + "/" + fname}, ticket=tk, actor=actor)
        check("worldfs.read 内容", bool(r1.get("ok")) and (r1.get("body") or {}).get("text") == "hello world",
              "text=%r" % ((r1.get("body") or {}).get("text"),))

        st1 = bus.ask("wfs-stat1", "worldfs.stat",
                      {"path": base + "/" + fname}, ticket=tk, actor=actor)
        check("stat 对象身份稳定（读前）", (st1.get("body") or {}).get("obj_id") == obj_id,
              "obj=%r" % ((st1.get("body") or {}).get("obj_id"),))

        w2 = bus.ask("wfs-write2", "worldfs.write",
                     {"path": base + "/" + fname, "text": "hello world v2",
                      "intent": "live test: 覆盖第二版"}, ticket=tk, actor=actor)
        b2 = w2.get("body") or {}
        check("覆盖产生 seq+1 且对象身份不变",
              bool(w2.get("ok")) and b2.get("seq") == 2 and b2.get("obj_id") == obj_id,
              "seq=%r obj=%r" % (b2.get("seq"), b2.get("obj_id")))

        vs = bus.ask("wfs-vers", "worldfs.versions",
                     {"path": base + "/" + fname}, ticket=tk, actor=actor)
        seqs = [v.get("seq") for v in ((vs.get("body") or {}).get("versions") or [])]
        check("版本历史 [1,2]", seqs == [1, 2], "seqs=%r" % (seqs,))

        rs = bus.ask("wfs-restore", "worldfs.restore",
                     {"path": base + "/" + fname, "seq": 1,
                      "intent": "live test: 回滚到第一版"}, ticket=tk, actor=actor)
        r2 = bus.ask("wfs-read2", "worldfs.read",
                     {"path": base + "/" + fname}, ticket=tk, actor=actor)
        check("回滚到旧版本且内容恢复",
              bool(rs.get("ok")) and (r2.get("body") or {}).get("text") == "hello world",
              "seq=%r text=%r" % ((rs.get("body") or {}).get("seq"),
                                  (r2.get("body") or {}).get("text")))

        # 去重：同内容写另一个路径，state.blobs 不应增加
        st2 = bus.ask("wfs-state2", "worldfs.state", {}, ticket=tk, actor=actor)
        blobs1 = (st2.get("body") or {}).get("blobs")
        wd = bus.ask("wfs-dup", "worldfs.write",
                     {"path": base + "/dup.txt", "text": "hello world",
                      "intent": "live test: 同内容去重"}, ticket=tk, actor=actor)
        st3 = bus.ask("wfs-state3", "worldfs.state", {}, ticket=tk, actor=actor)
        blobs2 = (st3.get("body") or {}).get("blobs")
        check("同内容去重（blob 数不变）",
              bool(wd.get("ok")) and (wd.get("body") or {}).get("dedup") is True
              and blobs1 == blobs2,
              "blobs %r → %r dedup=%r" % (blobs1, blobs2, (wd.get("body") or {}).get("dedup")))

        ls = bus.ask("wfs-list", "worldfs.list",
                     {"path": base}, ticket=tk, actor=actor)
        names = [e.get("name") for e in ((ls.get("body") or {}).get("entries") or [])]
        check("list 含 hello/dup", {fname, "dup.txt"} <= set(names), sorted(names))

        rm = bus.ask("wfs-rm", "worldfs.remove",
                     {"path": base + "/dup.txt", "intent": "live test: 删 dup"}, ticket=tk, actor=actor)
        r3 = bus.ask("wfs-read3", "worldfs.read",
                     {"path": base + "/dup.txt"}, ticket=tk, actor=actor)
        check("删除后不可读", bool(rm.get("ok")) and r3.get("ok") is False,
              str(r3.get("error") or r3.get("code"))[:120])

        bad = bus.ask("wfs-bad", "worldfs.write",
                      {"path": base + "/no-intent.txt", "text": "x"}, ticket=tk, actor=actor)
        check("缺 intent 被拒", bad.get("ok") is False,
              str(bad.get("error") or bad.get("code"))[:120])

        # 重启持久化
        subprocess.run(["systemctl", "restart", "aios-worldfs"], check=False)
        time.sleep(4)
        r4 = bus.ask("wfs-read4", "worldfs.read",
                     {"path": base + "/" + fname}, ticket=tk, actor=actor)
        check("重启后数据仍在", bool(r4.get("ok")) and (r4.get("body") or {}).get("text") == "hello world",
              "text=%r" % ((r4.get("body") or {}).get("text"),))

        ty = bus.query("wfs-type", "type", ticket=tk, type="wpath")
        raw = ty.get("data")
        rows = (raw.get("individuals") if isinstance(raw, dict) else raw) or []
        check("world/query kind=type 能查到 wpath", len(rows) >= 1, "wpath=%d" % len(rows))
        check("账里有 worldfs.write 成功记录", led_count("worldfs.write") >= 2,
              "hits=%d" % led_count("worldfs.write"))

        ok = all(c["ok"] for c in out["checks"])
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
