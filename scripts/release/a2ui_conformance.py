#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ A2UI 跟版一致性（P5）—— 我们用的组件对 **basic catalog** 与两个渲染器（Flutter/genui、Web/voice.html）核对。

★ 作者令（逐字整理）：「界面就是消息」；A2UI 要跟版（同一帧，Flutter 和浏览器都能画）。
★ 判据式用法：`python3 a2ui_conformance.py --check` ⇒ rc 1 表示有「法外组件」或「浏览器画不出」。

限度（★ 如实）：basic catalog 的组件名是我们对 v1.0 的**可控子集**；Flutter 走 genui 包（视为支持 basic），
  Web 支持集从 `src/web/voice.html` 的 `case "X"` 现取。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# A2UI v1.0 basic catalog（我们核对用；多出来的名字先算「法外」，等确认）
BASIC = {
    "Text", "Column", "Row", "Card", "Button", "Icon", "Divider", "List",
    "Image", "Tabs", "Modal", "CheckBox", "TextField", "DateTimeInput",
    "MultipleChoice", "Slider", "AudioPlayer", "Video",
}


def web_supported():
    """★ 从 voice.html 的 switch case 现取浏览器真正支持的组件名。"""
    p = os.path.join(ROOT, "src", "web", "voice.html")
    try:
        html = open(p, encoding="utf-8").read()
    except OSError:
        return set()
    return set(re.findall(r'case\s+"([A-Za-z]+)"', html))


def used_from_sources(root=None):
    """★ 扫 Python 里写死的组件名。"""
    root = root or os.path.join(ROOT, "src")
    used = set()
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            try:
                txt = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            except OSError:
                continue
            used |= set(re.findall(r'"component"\s*:\s*"([A-Za-z]+)"', txt))
    return used


def used_from_frames(frames):
    used = set()
    for f in frames or []:
        for m in (f.get("messages") or []) if isinstance(f, dict) else []:
            upd = m.get("updateComponents") or {}
            for c in upd.get("components") or []:
                if c.get("component"):
                    used.add(c["component"])
    return used


def judge(used, web=None):
    """★ 返回问题清单（空＝过）。"""
    web = web_supported() if web is None else web
    unknown = sorted(set(used) - BASIC)
    unsupported = sorted(set(used) - set(web))
    bad = []
    for c in unknown:
        bad.append("法外组件（basic catalog 没有）：%s" % c)
    for c in unsupported:
        bad.append("浏览器画不出：%s（voice.html 没这个 case）" % c)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="A2UI conformance")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    used = used_from_sources()
    bad = judge(used)
    out = {"used": sorted(used), "unknown": sorted(used - BASIC),
           "web_unsupported": sorted(used - web_supported()),
           "ok": not bad}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("used=%s" % ",".join(sorted(used)))
        print("unknown=%s" % ",".join(out["unknown"]) or "（无）")
        print("web_unsupported=%s" % (",".join(out["web_unsupported"]) or "（无）"))
        for b in bad:
            print("  [红] " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
