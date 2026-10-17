#!/usr/bin/env python3
"""C25 —— **总线与本体各是【单独一个进程】，而且它们最先起**（T-273）。

★ 作者裁（逐字整理）：
  · 「**只有这个总线和这个本体是最先起来的，是相互独立的**」；
  · 「**而且这个总线是一个单独的进程**」。

⇒ ★ 落法（可判）：
  (a) `distro/systemd/aios-bus.service` 在（★ 总线是一个单独进程）；
  (b) `distro/systemd/aios-ontology.service` 在（★ 本体是一个单独进程）；
  (c) ★★ **总线的 `Before=` 里有本体**（★ 「总线最先起」）；
  (d) ★★ **本体的 `After=` 里有总线**（★ 「本体第二个起」）；
  (e) 两个单元都有 `WantedBy=multi-user.target`（★ 会被起，不是摆着）。

红例：★ 把 (c) 的 `Before=` 删掉 ⇒ 红。

限度（★ 如实）：判**文本** ⇒ 「真按这个顺序起」要靠 systemd 本身（★ 本判据只是**文本**）。

用法：
  python verify/c25_bus_and_ontology_units.py              跑真仓库
  python verify/c25_bus_and_ontology_units.py --self-test   反例自检
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BUS = os.path.join("distro", "systemd", "aios-bus.service")
ONT = os.path.join("distro", "systemd", "aios-ontology.service")
NAME = "C25 总线与本体各是单独进程且最先起"


def scan(bus, ont):
    bad = []
    if bus is None:
        bad.append("aios-bus.service：不在（★ 总线应当是一个单独的进程）")
    if ont is None:
        bad.append("aios-ontology.service：不在（★ 本体应当是一个单独的进程）")
    if bus is not None:
        if "Before=" in bus and "aios-ontology.service" not in bus:
            bad.append("aios-bus.service：Before= 里没有本体（★ 总线最先起）")
        if "Before=" not in bus:
            bad.append("aios-bus.service：没有 Before=（★ 总线最先起）")
        if "WantedBy=multi-user.target" not in bus:
            bad.append("aios-bus.service：没有 WantedBy（★ 不会被起）")
    if ont is not None:
        if "After=" in ont and "aios-bus.service" not in ont:
            bad.append("aios-ontology.service：After= 里没有总线（★ 本体第二个起）")
        if "WantedBy=multi-user.target" not in ont:
            bad.append("aios-ontology.service：没有 WantedBy（★ 不会被起）")
    return bad


def run(label="真仓库"):
    def read(p):
        return open(p, "r", encoding="utf-8").read() if os.path.exists(p) else None

    bad = scan(read(BUS), read(ONT))
    print("=== %s（%s）===" % (NAME, label))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0


GOOD_BUS = (
    "[Unit]\n"
    "Before=aios-ontology.service\n"
    "[Install]\n"
    "WantedBy=multi-user.target"
)
GOOD_ONT = (
    "[Unit]\n"
    "After=aios-bus.service\n"
    "[Install]\n"
    "WantedBy=multi-user.target"
)


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    # 红例1：总线的 Before= 里没有本体（顺序丢了）
    b1 = scan(GOOD_BUS.replace("Before=aios-ontology.service", "Before=other.service"), GOOD_ONT)
    print("=== 红例1（总线 Before 里没有本体）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    # 红例2：本体单元不在
    b2 = scan(GOOD_BUS, None)
    print("=== 红例2（本体单元不在）⇒ 命中 %d 处 ===" % len(b2))
    if not any("本体" in x for x in b2):
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
