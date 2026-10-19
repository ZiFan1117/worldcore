# -*- coding: utf-8 -*-
"""★ 画布的目录白名单与整帧校验（判据 C24 的事实侧）。

★ 口径（作者）：「只借 A2UI 的目录白名单 ＋ 没相容目录就不发」。
★ 权威＝目录件 `src/ontology/data/a2ui-catalog-basic.json`（A2UI basic catalog v1.0）；
  件不在时用内置同名表（★ 降级，不是第二权威；有件时以件为准，判据 C24 现取来源）。
★ 检验不过 ⇒ **整帧拒**（★ 不许静默过滤掉不认的元件 —— 过滤会把「目录不对」藏起来）。

返回的问题清单（空＝合目录）覆盖：帧不是对象／没有 messages／没有 createSurface.surfaceId／
没有 updateComponents.components／元件不在目录／组件 id 缺失或重复／child 与 children
必须是 id 字符串（★ 不许内联对象）／Button 必须带 child／引用指向不存在的 id。
"""
import json
import os

CATALOG_PATH = os.environ.get(
    "AIOS_A2UI_CATALOG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "ontology", "data", "a2ui-catalog-basic.json"))

# ★ 目录件不在时的内置表（与 A2UI basic catalog v1.0 的 18 个元件同名）。
_FALLBACK_COMPONENTS = (
    "Text", "Image", "Icon", "Video", "AudioPlayer", "Row", "Column", "List",
    "Card", "Tabs", "Modal", "Divider", "Button", "TextField", "CheckBox",
    "ChoicePicker", "Slider", "DateTimeInput",
)


def load_catalog_components():
    """★ 从目录件取元件名集合；件不在 ⇒ 内置同名表（并说清楚是降级）。"""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
        comps = doc.get("components")
        if isinstance(comps, dict) and comps:
            return set(comps.keys()), "目录件 %s" % CATALOG_PATH
    except (OSError, ValueError):
        pass
    return set(_FALLBACK_COMPONENTS), "内置表（目录件不在：%s）" % CATALOG_PATH


A2UI_COMPONENTS, A2UI_WHITELIST_FROM = load_catalog_components()


def validate_frame(frame):
    """★ 一帧画布必须【整帧】合 A2UI 基本目录：返回问题清单（空＝合目录）。"""
    bad = []
    if not isinstance(frame, dict):
        return ["帧不是对象"]
    msgs = frame.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return ["没有 messages"]
    surface_id, comps = None, None
    for m in msgs:
        if not isinstance(m, dict):
            bad.append("message 不是对象")
            continue
        cs = m.get("createSurface")
        if isinstance(cs, dict) and cs.get("surfaceId"):
            surface_id = cs["surfaceId"]
        uc = m.get("updateComponents")
        if isinstance(uc, dict):
            comps = uc.get("components")
            if surface_id and uc.get("surfaceId") != surface_id:
                bad.append("updateComponents.surfaceId 与 createSurface 不一致")
    if not surface_id:
        bad.append("没有 createSurface.surfaceId")
    if not isinstance(comps, list) or not comps:
        bad.append("没有 updateComponents.components")
        return bad
    ids = {}
    for c in comps:
        if not isinstance(c, dict):
            bad.append("组件不是对象")
            continue
        cid, name = c.get("id"), c.get("component")
        if not cid:
            bad.append("组件没 id")
            continue
        if cid in ids:
            bad.append("组件 id 重复：%s" % cid)
        ids[cid] = name
        if name not in A2UI_COMPONENTS:
            bad.append("元件不在 A2UI 基本目录：%s（%s）" % (name, cid))
        child = c.get("child")
        if child is not None and not isinstance(child, str):
            bad.append("%s.child 必须是 id 字符串（不许内联对象）" % cid)
        if name == "Button" and not isinstance(child, str):
            bad.append("Button 缺 child（要 id 字符串）：%s" % cid)
        kids = c.get("children")
        if kids is not None:
            if not isinstance(kids, list) or any(not isinstance(x, str) for x in kids):
                bad.append("%s.children 必须是 id 字符串数组（不许内联对象）" % cid)
    for c in comps:
        if not isinstance(c, dict):
            continue
        refs = []
        if isinstance(c.get("child"), str):
            refs.append(c["child"])
        if isinstance(c.get("children"), list):
            refs += [x for x in c["children"] if isinstance(x, str)]
        for r in refs:
            if r not in ids:
                bad.append("%s 指向不存在的 id：%s" % (c.get("id"), r))
    return bad
