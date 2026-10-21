# -*- coding: utf-8 -*-
"""provider_auth：world/appear、world/register、world/exec/result 的签名信封。

★ 单独文件夹（本体进程内），不是新进程/单元。
"""
from .provider_auth import (  # noqa: F401
    DEFAULT_KEY_DIR,
    ProviderAuthError,
    auth_enabled,
    SIGNED_TOPICS,
    SignedSession,
    key_dir,
    load_key,
    open_signed_session,
    sign_message,
    verify_message,
)
