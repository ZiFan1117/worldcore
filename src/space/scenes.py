# -*- coding: utf-8 -*-
"""★ P3 场景文件化 —— 把空间的画布（A2UI 帧）落成 JSON 文件（C27：一个文件一块）。"""
import json
import os
import time

SCENES = os.environ.get("AIOS_SCENES_DIR", "/var/lib/aios/scenes")


def save_scene(surface_id, frame):
    """★ 人能读、能 diff、能备份；写失败打日志（不阻断画布）。"""
    try:
        os.makedirs(SCENES, exist_ok=True)
        name = str(surface_id).replace("/", "_") + ".json"
        with open(os.path.join(SCENES, name), "w", encoding="utf-8") as f:
            json.dump({"surface": surface_id,
                       "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                       "frame": frame}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[个人空间] ⚠ 场景写失败：%s" % e, flush=True)
