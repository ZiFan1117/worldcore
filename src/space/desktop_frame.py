# -*- coding: utf-8 -*-
"""★ 桌面画布 —— 个人空间出的一张脸（壁纸/顶栏/图标；★ 布局不进本体）。"""
import time

ICONS = [
    {"id": "ic_agent", "label": "智能体"},
    {"id": "ic_actions", "label": "能做什么"},
    {"id": "ic_computer", "label": "这台机器"},
    {"id": "ic_logout", "label": "退出"},
]


def desktop_frame(surface_id, user, n_members):
    now = time.strftime("%Y-%m-%d %H:%M")
    comps = [
        {"id": "root", "component": "Column",
         "children": ["dk_t", "dk_bar", "dk_d", "dk_grid", "dk_d2", "dk_note"]},
        {"id": "dk_t", "component": "Text", "text": "**AI-OS · " + user + " 的个人空间**"},
        {"id": "dk_bar", "component": "Row", "children": ["dk_u", "dk_ts", "dk_w"]},
        {"id": "dk_u", "component": "Text", "text": "我：" + user},
        {"id": "dk_ts", "component": "Text", "text": now},
        {"id": "dk_w", "component": "Text", "text": "世界：" + str(n_members) + " 个成员"},
        {"id": "dk_d", "component": "Divider"},
        {"id": "dk_grid", "component": "Column",
         "children": [ic["id"] + "_b" for ic in ICONS]},
        {"id": "dk_d2", "component": "Divider"},
        {"id": "dk_note", "component": "Text",
         "text": "★ 这一帧由【呈现进程的 space 面】出，经本体 ⇒ 呈现 ⇒ 屏"},
    ]
    for ic in ICONS:
        comps.append({"id": ic["id"] + "_t", "component": "Text", "text": ic["label"]})
        comps.append({"id": ic["id"] + "_b", "component": "Button",
                      "child": ic["id"] + "_t",
                      # ★★ A2UI 的 Action 格式：{"event": {"name", "context"}}
                      "action": {"event": {"name": "space.icon_clicked",
                                           "context": {"icon": ic["id"]}}}})
    return {
        "version": "v1.0",
        "name": user + " 的桌面",
        "role": "desktop",
        # ★★★ 同 login_frame：layout 是【我们的扩展】，A2UI 不管多 surface 叠。
        "layout": {"layers": [{"surface": surface_id, "z": 0, "active": True}]},
        "messages": [
            {"version": "v1.0", "createSurface": {
                "surfaceId": surface_id, "sendDataModel": True,
                "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"}},
            {"version": "v1.0", "updateComponents": {
                "surfaceId": surface_id, "components": comps}},
        ],
    }
