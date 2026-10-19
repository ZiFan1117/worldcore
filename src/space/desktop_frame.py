# -*- coding: utf-8 -*-
"""★ 桌面画布 —— 个人空间出的一张脸（壁纸/顶栏/图标；★ 布局不进本体）。"""
import time

ICONS = [
    {"id": "ic_ontology", "label": "本体", "emoji": "🗂️"},
    {"id": "ic_agent", "label": "智能体", "emoji": "🧠"},
    {"id": "ic_computer", "label": "这台机器", "emoji": "🖥️"},
    {"id": "ic_actions", "label": "能做什么", "emoji": "📋"},
    {"id": "ic_logout", "label": "退出", "emoji": "🚪"},
]


def desktop_frame(surface_id, user, n_members, guests=None):
    now = time.strftime("%Y-%m-%d %H:%M")
    # ★★ 仿真实桌面：图标网格（两列）。★ 图标＝emoji＋名字；按钮动作统一 space.icon_clicked。
    cols = [ICONS[i::2] for i in range(2)]
    comps = [
        {"id": "root", "component": "Column",
         "children": ["dk_t", "dk_bar", "dk_d", "dk_grid", "dk_d2", "dk_note"]},
        {"id": "dk_t", "component": "Text", "text": "**AI-OS · " + user + " 的个人空间**"},
        {"id": "dk_bar", "component": "Row", "children": ["dk_u", "dk_ts", "dk_w"]},
        {"id": "dk_u", "component": "Text", "text": "我：" + user},
        {"id": "dk_ts", "component": "Text", "text": now},
        {"id": "dk_w", "component": "Text", "text": "世界：" + str(n_members) + " 个成员"},
        {"id": "dk_d", "component": "Divider"},
        {"id": "dk_grid", "component": "Row",
         "children": ["dk_c%d" % i for i in range(len(cols))]},
        {"id": "dk_d2", "component": "Divider"},
        {"id": "dk_note", "component": "Text",
         "text": "★ 桌面（图标网格）由个人空间出；点图标 ⇒ 经本体 ⇒ 提供者出窗口 ⇒ 空间摆位"},
    ]
    for _ci, _icons in enumerate(cols):
        comps.append({"id": "dk_c%d" % _ci, "component": "Column",
                      "children": [ic["id"] + "_b" for ic in _icons]})
        for ic in _icons:
            comps.append({"id": ic["id"] + "_t", "component": "Text",
                          "text": ic["emoji"] + "  " + ic["label"]})
            comps.append({"id": ic["id"] + "_b", "component": "Button",
                          "child": ic["id"] + "_t",
                          # ★★ A2UI 的 Action 格式：{"event": {"name", "context"}}
                          "action": {"event": {"name": "space.icon_clicked",
                                               "context": {"icon": ic["id"]}}}})
    # ★★ 摆放归个人空间：桌面是第 0 层；别的提供者给的画布（客画布）由空间【摆】上去（附 rect）。
    #    rect 是渲染器认的 [x, y, w, h]；矩形由空间给 —— 渲染器不布局。
    layers = [{"surface": surface_id, "z": 0, "active": True}]
    for i, g in enumerate(guests or []):
        layers.append({"surface": g.get("surface"), "z": 10 + i, "active": True,
                       "rect": g.get("rect") or [640, 40, 620, 500]})
    return {
        "version": "v1.0",
        "name": user + " 的桌面",
        "role": "desktop",
        # ★★★ 同 login_frame：layout 是【我们的扩展】，A2UI 不管多 surface 叠。
        "layout": {"layers": layers},
        "messages": [
            {"version": "v1.0", "createSurface": {
                "surfaceId": surface_id, "sendDataModel": True,
                "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"}},
            {"version": "v1.0", "updateComponents": {
                "surfaceId": surface_id, "components": comps}},
        ],
    }
