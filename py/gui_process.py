# -*- coding: utf-8 -*-
"""AIOS GUI 进程（Python）—— ★ 世界 ↔ 人 之间那一面（类 ＝ surface）。

★ 作者裁（2026-10-17）：「**全改成 Python 版本吧**」。

★ 它做四件（和 Rust 版一致，只是换了语言）：
  ① **成为个体**：★ `surface/a2ui`（★ 照本体 `surface` 类的字段）
  ② **收帧**：★ 订 `world/ui/frame`（★ 一次声明、长期持有）
  ③ **落帧**：★ 写 `/run/aios/gui-frame.json`（★ 先临时再改名）
  ④ **回话**：★ 发 `world/ui/frame/ack`（★ 协议是双向的）

★ 它【不做】的：★ 不造帧（★ 投影是别人的事）、★ 不读别人的文件、★ 不渲染（★ 渲染器是下一个进程）。
"""

import json
import os
import time

import zenoh

T_APPEAR = "world/appear"
T_FRAME = "world/ui/frame"
T_ACK = "world/ui/frame/ack"
OUT = os.environ.get("AIOS_GUI_FRAME_OUT", "/run/aios/gui-frame.json")
ZENOH_ENDPOINT = os.environ.get("AIOS_BUS", "tcp/127.0.0.1:7447")

# ★ 照本体 `surface` 类的字段（name／role／order／visible／retract_seq／cells）
ME = {
    "class": "surface",
    "name": "a2ui",
    "role": "screen",
    "order": 1,
    "visible": True,
    "retract_seq": 0,
    "cells": "[]",
}


def log(*a):
    print("[GUI]", *a, flush=True)


def land(frame_text):
    """★ 先临时、再改名（★ 不让读的人看见半截）。"""
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        tmp = OUT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(frame_text)
        os.replace(tmp, OUT)
        return True
    except Exception as e:
        log("★ 落帧失败（%s）：%s" % (OUT, e))
        return False


def main():
    conf = zenoh.Config()
    conf.insert_json5("mode", '"client"')
    conf.insert_json5("scouting/multicast/enabled", "false")
    conf.insert_json5("connect/endpoints", json.dumps([ZENOH_ENDPOINT]))
    session = zenoh.open(conf)
    log("连上总线 %s" % ZENOH_ENDPOINT)

    # ★ ① 成为个体
    session.put(T_APPEAR, json.dumps(ME, ensure_ascii=False))
    log("① 成为个体：surface/a2ui（role=%s）" % ME["role"])

    # ★②③④ 收帧 ⇒ 落帧 ⇒ 回话
    def on_frame(smp):
        text = smp.payload.to_string()
        ok = land(text)
        ack = {"by": "surface/a2ui", "bytes": len(text), "landed": ok}
        session.put(T_ACK, json.dumps(ack, ensure_ascii=False))
        log("收到帧（%d 字节）⇒ 落帧=%s ⇒ 回了 ack" % (len(text), ok))

    session.declare_subscriber(T_FRAME, on_frame)
    log("② 订上了 %s（★ 一次声明、长期持有）" % T_FRAME)
    log("★ GUI 起来了 —— 世界 ↔ 人 之间那一面（不造帧、不渲染）")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断，关")
    finally:
        session.close()


if __name__ == "__main__":
    main()
