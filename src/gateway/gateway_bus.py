# -*- coding: utf-8 -*-
"""★ 世界薄网关的【总线客户端】—— 一问一答，只发两样：`world/query`／`world/ask`。

★ 写法照仓里既有的两处（不发明第二套）：
  · `src/agent/world_cli.py`：先订回话话题、再 put、按同一个 `id` 等回话，超时如实返回；
  · `src/ontology/bus_auth.py`：连总线时注入 user-password（deploy 写进 systemd drop-in）。
★ 它只是一个【收发器】：没有第二个数据面，也不开第二条出向路。
"""
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))


def _ontology_dir():
    return os.path.abspath(os.path.join(HERE, "..", "ontology"))


def _bus_auth():
    """★ 延迟导入：总线凭据在 `src/ontology/bus_auth.py`（deploy 生成），不在网关里另存一份。"""
    p = _ontology_dir()
    if p not in sys.path:
        sys.path.insert(0, p)
    import bus_auth  # noqa: E402
    return bus_auth


class WorldBus:
    """★ 一问一答的总线收发器（session 由外部给，判据可注入假总线）。"""

    def __init__(self, session):
        self.s = session

    def once(self, put_topic, res_topic, msg, timeout):
        """发一条，等一条同 `id` 的回话；等到返回回话对象，超时返回 None。"""
        rid = msg.get("id")
        box, ev = {}, threading.Event()

        def _on(smp):
            try:
                d = json.loads(smp.payload.to_string())
            except Exception:          # 坏回话只丢这一条，不打断等待（上 stderr）
                print("[网关] 坏回话：不是 JSON", file=sys.stderr, flush=True)
                return
            if d.get("id") == rid:
                box.update(d)
                ev.set()

        sub = self.s.declare_subscriber(res_topic, _on)
        try:
            self.s.put(put_topic, json.dumps(msg, ensure_ascii=False))
            if not ev.wait(timeout):
                return None
            return box
        finally:
            try:
                sub.undeclare()
            except Exception:
                pass

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def connect(endpoint=None):
    """★ 连总线（client 模式，只听 / 只连，不 scouting）。"""
    import zenoh

    endpoint = endpoint or os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([endpoint]))
    return WorldBus(_bus_auth().open_bus(conf))
