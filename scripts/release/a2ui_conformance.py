#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ A2UI 跟版一致性（P5）＋版本钉住 —— 组件对 basic catalog／两个渲染器；帧对 v1.0。

★ 权威＝目录件 `src/ontology/data/a2ui-catalog-basic.json`（现取 protocolVersion=1.0、
  catalogId=https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json、18 个元件）。
  ★ 件不在 ⇒ 内置同名表（降级，不是第二权威；「来源是不是件」由判据 C24 另盯）。
★ 判据①（组件）：源码／动态帧用到的组件必须在 basic catalog 内，且 Web 渲染器
  （`src/web/browser.html` 的 `case "X"`）都有 case。
★ 判据②（版本钉住）：帧里的 `"version"` 必须是 v1.0（接受 `"v1.0"`／`"1.0"`）；
  `"catalogId"` 必须指 `.../v1_0/...`（★ 不许悄悄退回 v0.9）。
  ★ 桌面渲染器（Flutter genui 0.10.4）只到 A2UI v0.9 ⇒ 它在 `render_main.dart` 里
    【显式降级】（把喂给 genui 的每帧改成 v0.9）；那是**渲染器侧的能力降级**，不是帧的
    生产口径 —— 本判据只扫 `.py`（Dart 不算帧生产）。
★ 用法：`python3 a2ui_conformance.py --check`（rc 1 ＝ 有红）；`--json` 机读。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CATALOG_PATH = os.path.join(ROOT, "src", "ontology", "data", "a2ui-catalog-basic.json")

# A2UI v1.0 允许的帧版本写法（wire 口径是 '1.0'；我方历史写法是 'v1.0'，两者都认）。
ALLOWED_VERSIONS = {"v1.0", "1.0"}

# ★ 目录件不在时的内置表（与 A2UI basic catalog v1.0 的 18 个元件同名）。
#   ★ 现取 v1.0 目录件里是 `ChoicePicker`、**没有** `MultipleChoice`；内置表照目录件写，
#     免得「目录件的名字」和「内置换算的名字」两套口径。
_FALLBACK_COMPONENTS = (
    "Text", "Image", "Icon", "Video", "AudioPlayer", "Row", "Column", "List",
    "Card", "Tabs", "Modal", "Divider", "Button", "TextField", "CheckBox",
    "ChoicePicker", "Slider", "DateTimeInput",
)


def load_catalog():
    """★ 从目录件取（doc, 来源说明）；件不在／坏 ⇒ (None, 原因)。"""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        return None, "目录件不可用（%s）：%s" % (CATALOG_PATH, e)
    comps = doc.get("components")
    if not isinstance(comps, dict) or not comps:
        return None, "目录件没有 components：%s" % CATALOG_PATH
    return doc, "目录件 %s（protocolVersion=%s）" % (CATALOG_PATH, doc.get("protocolVersion"))


CATALOG_DOC, CATALOG_SOURCE = load_catalog()

if CATALOG_DOC:
    BASIC = set(CATALOG_DOC["components"].keys())
    EXPECTED_PROTOCOL = str(CATALOG_DOC.get("protocolVersion") or "1.0")
    EXPECTED_CATALOG_ID = CATALOG_DOC.get("catalogId") or ""
else:
    BASIC = set(_FALLBACK_COMPONENTS)
    EXPECTED_PROTOCOL = "1.0"
    EXPECTED_CATALOG_ID = ""

VERSION_RE = re.compile(r'"version"\s*:\s*"([^"]+)"')
CATALOG_ID_RE = re.compile(r'"catalogId"\s*:\s*"([^"]+)"')


def _rel(path):
    try:
        return os.path.relpath(path, ROOT).replace("\\", "/")
    except ValueError:
        return path


def web_supported():
    """★ 从 browser.html 的 switch case 现取浏览器真正支持的组件名。"""
    p = os.path.join(ROOT, "src", "web", "browser.html")
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
    """★ 从帧里取组件：`updateComponents.components` ＋ v1.0 的 `createSurface.components`。"""
    used = set()
    for f in frames or []:
        if not isinstance(f, dict):
            continue
        for m in (f.get("messages") or []):
            if not isinstance(m, dict):
                continue
            uc = m.get("updateComponents") or {}
            for c in (uc.get("components") or []):
                if isinstance(c, dict) and c.get("component"):
                    used.add(c["component"])
            cs = m.get("createSurface") or {}
            for c in (cs.get("components") or []):
                if isinstance(c, dict) and c.get("component"):
                    used.add(c["component"])
    return used


def version_issues(root=None):
    """★ 帧的版本口径：返回 [{file,line,kind,value}]；kind ∈ version／catalogId。"""
    root = root or os.path.join(ROOT, "src")
    issues = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for m in VERSION_RE.finditer(line):
                    v = m.group(1)
                    if v not in ALLOWED_VERSIONS:
                        issues.append({"file": _rel(p), "line": i,
                                       "kind": "version", "value": v})
                for m in CATALOG_ID_RE.finditer(line):
                    url = m.group(1)
                    if "/v1_0/" not in url:
                        issues.append({"file": _rel(p), "line": i,
                                       "kind": "catalogId", "value": url})
    return issues


def judge(used, web=None):
    """★ 判据①：返回问题清单（空＝过）。"""
    web = web_supported() if web is None else web
    unknown = sorted(set(used) - BASIC)
    unsupported = sorted(set(used) - set(web))
    bad = []
    for c in unknown:
        bad.append("法外组件（basic catalog 没有）：%s" % c)
    for c in unsupported:
        bad.append("浏览器画不出：%s（browser.html 没这个 case）" % c)
    return bad


def judge_versions(issues):
    """★ 判据②：把 version_issues() 的条目译成人话（空＝过）。"""
    bad = []
    for it in issues or []:
        kind = it.get("kind")
        where = "%s:%s" % (it.get("file"), it.get("line"))
        if kind == "catalogId":
            bad.append("catalogId 不是 v1.0 目录：%s（%s）" % (it.get("value"), where))
        else:
            bad.append("帧版本不是 v1.0：%s（%s）" % (it.get("value"), where))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="A2UI conformance")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    used = used_from_sources()
    vissues = version_issues()
    bad = judge(used) + judge_versions(vissues)
    out = {"catalog": CATALOG_SOURCE, "protocol_version": EXPECTED_PROTOCOL,
           "used": sorted(used), "unknown": sorted(used - BASIC),
           "web_unsupported": sorted(used - web_supported()),
           "version_issues": vissues,
           "ok": not bad}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("catalog=%s" % CATALOG_SOURCE)
        print("used=%s" % ",".join(sorted(used)))
        print("unknown=%s" % (",".join(out["unknown"]) or "（无）"))
        print("web_unsupported=%s" % (",".join(out["web_unsupported"]) or "（无）"))
        print("version_issues=%d" % len(vissues))
        for b in bad:
            print("  [红] " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
