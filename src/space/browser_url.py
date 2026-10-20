# -*- coding: utf-8 -*-
"""★ 语义浏览器地址（C27 拆分；这里【不】起进程——出向只许计算机做，C19）。"""
import os

DEFAULT_BROWSER_URL = os.environ.get(
    "AIOS_BROWSER_URL", "http://127.0.0.1:8765/?user=zhang&secret=0")
