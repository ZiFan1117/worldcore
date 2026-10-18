# -*- coding: utf-8 -*-
"""★ 登录画布 —— 呈现出的一张脸（文档 §一：「登录屏……或由接入进程发一块 login 画布」）。

★★ 测试账号（作者令 2026-10-18）：「先设定一个测试的用户名和密码吧，密码就是一个 0 就行」
   ⇒ 用户名 zhang ／ 密码 0（★ 由个人空间的 space.login 验）。
"""

# ★★ 测试账号（★ 现在写死；接入做了以后由接入/登录验）
TEST_USER = "zhang"
TEST_PASS = "0"


def login_frame(surface_id, screen_name):
    import time
    now = time.strftime("%Y-%m-%d %H:%M")
    comps = [
        {"id": "root", "component": "Column",
         "children": ["lg_t", "lg_s", "lg_d", "lg_u", "lg_p", "lg_bt", "lg_b", "lg_d2", "lg_note"]},
        {"id": "lg_t", "component": "Text", "text": "**AI-OS**"},
        {"id": "lg_s", "component": "Text", "text": "请登录 —— " + now},
        {"id": "lg_d", "component": "Divider"},
        # ★★ TextField 的 value 必须【绑到 dataModel 路径】，否则打字只在本地、拿不到值
        #    （★ 现取：作者「我在界面上输入东西，没办法显示」⇒ 除了 controller 缓存，
        #      还要让 value 走 {path}，这样输入才会写回 dataModel 并被 onSubmit 带出）
        {"id": "lg_u", "component": "TextField", "label": "用户名",
         "value": {"path": "/login/user"}},
        {"id": "lg_p", "component": "TextField", "label": "密码",
         "value": {"path": "/login/pass"}},
        {"id": "lg_bt", "component": "Text", "text": "登录"},
        # ★★ A2UI 的 Action 格式（★ genui embedded_schemas 逐字）：
        #    {"event": {"name": <动作名>, "context": {<参数>}}}
        {"id": "lg_b", "component": "Button", "child": "lg_bt",
         # ★★ context 里给【路径】⇒ 点击时 genui 自动解析成 dataModel 里的值
         #    （★ 比在 Dart 里读 DataModel 干净 —— 全部走帧）
         "action": {"event": {"name": "presentation.login",
                              "context": {"user": {"path": "/login/user"},
                                          "pass": {"path": "/login/pass"}}}}},
        {"id": "lg_d2", "component": "Divider"},
        {"id": "lg_note", "component": "Text",
         "text": "★ 测试账号：" + TEST_USER + " ／ 密码 " + TEST_PASS +
                 "（★ 登录界面由【呈现】出；接入未做，先代）"},
    ]
    return {
        "version": "v1.0",
        "name": "AI-OS 登录",
        "role": "login",
        # ★★★ layout 是【我们的扩展】—— A2UI v0.9.1 规范【没有】多 surface 叠的概念
        #    （现取：createSurface 只有 surfaceId/catalogId/theme/sendDataModel 四字段；
        #     消息只有 createSurface/updateComponents/updateDataModel/deleteSurface 四种）。
        #    它放在帧顶层、不塞进 A2UI 的 message ⇒ 不污染协议；别人的渲染器可以忽略它。
        #    见 ninedim/06-变更/…/说明-画布合成层-A2UI不管的那一层-2026-10-18.md
        "layout": {"layers": [
            {"surface": surface_id, "z": 0, "active": True, "modal": True}]},
        "messages": [
            {"version": "v1.0", "createSurface": {
                "surfaceId": surface_id, "sendDataModel": True,
                "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"}},
            {"version": "v1.0", "updateComponents": {
                "surfaceId": surface_id, "components": comps}},
            # ★★ 初始值（★ TextField.value 绑了 {path}，这里给初值）
            {"version": "v1.0", "updateDataModel": {
                "surfaceId": surface_id,
                "data": {"login": {"user": TEST_USER, "pass": ""}}}},
        ],
    }
