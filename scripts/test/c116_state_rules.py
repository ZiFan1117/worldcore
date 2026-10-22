# -*- coding: utf-8 -*-
"""C116 · state 同步规则：report 只能 software，apply 只能 ontology+mutable，未知属性拒。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from protocol.state import validate_state  # noqa: E402

META = {
    "state": {"mutable": True, "authority": "ontology"},
    "last_result": {"mutable": True, "authority": "software"},
    "version": {"mutable": False, "authority": "software"},
}


def msg(t, changes, rev=1):
    return {"protocol": "world.message.v1", "v": 1, "type": t,
            "id": "m1", "from": "world://app/calculator",
            "to": "world://ontology", "data": {"individual": "world://app/calculator",
                                               "rev": rev, "changes": changes}}


def main():
    bad = []
    if validate_state(msg("state_report", {"last_result": 2}), META):
        bad.append("合法 report 被拒")
    if validate_state(msg("state_apply", {"state": "reset"}), META):
        bad.append("合法 apply 被拒")
    cases = [
        ("state_report", {"state": "x"}, "REPORT_NOT_SOFTWARE"),
        ("state_apply", {"last_result": 2}, "APPLY_NOT_ONTOLOGY"),
        ("state_apply", {"version": "2"}, "APPLY_NOT_ONTOLOGY"),
        ("state_report", {"nope": 1}, "UNKNOWN_PROPERTY"),
    ]
    for t, ch, needle in cases:
        why = validate_state(msg(t, ch), META)
        if needle not in " ".join(why):
            bad.append("%s %r：%s" % (t, ch, why))
    if bad:
        print("=== 结论：红（%d 条）===" % len(bad))
        for line in bad:
            print("  - " + line)
        return 1
    print("=== 结论：绿（state：report/apply authority 与 mutable 校验，未知属性拒）===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
