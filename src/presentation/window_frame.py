# -*- coding: utf-8 -*-
"""★ 通用窗口壳（2026-10-19）—— 仿真实桌面的"窗口管理器"：**标题栏统一画，应用只画内容**。

★ 借鉴来源（只借形状，不借代码）：
  · 真实桌面：窗口有标题栏，右上角「缩放 / 关闭」；
  · A2UI basic catalog：窗口＝`Card`/`Column` 结构，标题栏＝`Row`，按钮＝`Button(child=Text)`；
  · 我们自己的 `layout.layers`（A2UI 之外）：窗口位置/层叠由个人空间摆，不归渲染器。
★ 用法：应用把自己的内容组件（第一个 id 必须是 `root` 的 Column）交给本函数，
  得到「窗口壳 ＋ 内容」的完整组件数组；两个按钮的事件名固定：
    `space.window_zoom`／`space.window_close`，上下文都带 `surface`。
★ 这是**约定**：以后所有应用都套这一层，桌面上的窗口才长得一样。
"""


def wrap_window(title, comps, surface, close_event="space.window_close",
                zoom_event="space.window_zoom"):
    """★ 把「内容组件」包进一扇窗口：标题栏（标题 ＋ 缩放 ＋ 关闭）＋ 内容区。

    ★ `comps`：应用自己的组件数组，其中必须有一个 `id="root"` 的 `Column`（A2UI 约定）。
    ★ 返回新的组件数组（同样以 `id="root"` 的 Column 开头）。
    """
    body_children = []
    out = []
    for c in comps:
        if isinstance(c, dict) and c.get("id") == "root":
            c = dict(c, id="win_content")
            body_children.append("win_content")
        out.append(c)
    if not body_children:                      # 没有 root ⇒ 兜一层，内容放进去
        body_children.append("win_body_inner")
        out.append({"id": "win_body_inner", "component": "Column",
                    "children": [c.get("id") for c in comps if isinstance(c, dict)]})
    ctx = {"surface": surface}
    chrome = [
        # ★ 窗口＝一张 Card（有底色/边界）⇒ 最大化时不透出桌面内容
        {"id": "root", "component": "Column", "children": ["win_card"]},
        {"id": "win_card", "component": "Card", "child": "win_inner"},
        {"id": "win_inner", "component": "Column", "children": ["win_bar", "win_body"]},
        # ★ 标题栏只列「标题 ＋ 两个按钮」；按钮的文字组件由 Button.child 引用，不单独进栏
        {"id": "win_bar", "component": "Row",
         "children": ["win_title", "win_zoom_b", "win_close_b"]},
        {"id": "win_title", "component": "Text", "text": "**" + str(title) + "**", "weight": 10},
        {"id": "win_zoom_t", "component": "Text", "text": "□"},
        {"id": "win_zoom_b", "component": "Button", "child": "win_zoom_t",
         "action": {"event": {"name": zoom_event, "context": dict(ctx)}}},
        {"id": "win_close_t", "component": "Text", "text": "×"},
        {"id": "win_close_b", "component": "Button", "child": "win_close_t",
         "action": {"event": {"name": close_event, "context": dict(ctx)}}},
        {"id": "win_body", "component": "Column", "children": body_children},
    ]
    return chrome + out
