# -*- coding: utf-8 -*-
"""C110 · provider_auth 能识别 P2 信封的 provider kind，且拒冒充。

为什么：fs 的 P2 register 在 VM 上曾因 provider_auth.kind_of 只认旧形状而崩；
本判据钉住：P2 信封的 bindings.registered_by_kind 能被推导，且 _kind_matches 会拒不一致。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "src", "ontology"))

from provider_auth.provider_auth import ProviderAuthError, _kind_matches, kind_of  # noqa: E402


def envelope(kind):
    return {
        "protocol": "world.message.v1",
        "v": 1,
        "type": "register",
        "id": "m1",
        "from": "world://fs/fs0",
        "to": "world://ontology",
        "data": {
            "individual": {"id": "world://fs/fs0", "object_type": "fs"},
            "bindings": [{"action": "file.stat", "function": "stat",
                          "registered_by_kind": kind}],
        },
    }


def main():
    bad = []
    got = kind_of(envelope("fs"))
    if got != "fs":
        bad.append("kind_of(P2)=%r，期望 fs" % got)

    try:
        _kind_matches("clock", envelope("fs"))
        bad.append("_kind_matches 应拒 clock vs fs")
    except ProviderAuthError:
        pass

    try:
        _kind_matches("fs", envelope("fs"))
    except ProviderAuthError as exc:
        bad.append("_kind_matches 合法也拒：%s" % exc)

    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（provider_auth 能推 P2 信封 kind；clock 冒充 fs 被拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
