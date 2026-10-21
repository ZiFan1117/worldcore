# -*- coding: utf-8 -*-
"""★ 总线连接凭据（Zenoh user-password 认证）—— bus ACL 的第一层。

作者：appear 签名/ACL 的 ACL 第二层。
· router 侧：`/etc/aios/zenoh.json5` 的 `transport.auth.usrpwd.dictionary_file`；
· client 侧：本模块把 user/password 注入 zenoh.Config；
· 密码在 `/etc/aios/bus-client.secret`（root-only），不写进法/仓库；
· 单位用户名由 deploy 写进 systemd drop-in（`AIOS_BUS_USER`）；测试默认 `tests`。
"""
import json
import os

SECRET_PATH = os.environ.get("AIOS_BUS_SECRET", "/etc/aios/bus-client.secret")
DEFAULT_USER = "tests"


def load_credentials():
    user = (os.environ.get("AIOS_BUS_USER") or DEFAULT_USER).strip()
    pw = os.environ.get("AIOS_BUS_PASSWORD") or ""
    if not pw:
        try:
            with open(SECRET_PATH, "r", encoding="utf-8") as f:
                pw = f.read().strip()
        except OSError:
            pw = ""
    if not pw:
        return None
    return user, pw


def configure(conf):
    """把凭据塞进 zenoh.Config；没有凭据时原样返回（宿主静态测试用）。"""
    creds = load_credentials()
    if not creds:
        return conf
    user, pw = creds
    conf.insert_json5("transport/auth/usrpwd/user", json.dumps(user))
    conf.insert_json5("transport/auth/usrpwd/password", json.dumps(pw))
    return conf


def open_bus(conf):
    import zenoh
    return zenoh.open(configure(conf))
