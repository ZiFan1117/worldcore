#!/usr/bin/env python3
"""C25 —— **总线与本体各是【单独一个进程】，而且它们最先起**（T-273）。

★ 作者裁（逐字整理）：
  · 「**只有这个总线和这个本体是最先起来的，是相互独立的**」；
  · 「**而且这个总线是一个单独的进程**」。

⇒ ★ 落法（可判）：
  (a) `distro/systemd/aios-bus.service` 在（★ 总线是一个单独进程）；
  (b) `distro/systemd/aios-ontology.service` 在（★ 本体是一个单独进程）；
  (c) ★★★ **总线的 unit 里【不许出现】`aios-ontology`**（★ 作者裁：「本体和总线两个不要有瓜葛」）；
  (d) ★★★ **本体的 unit 里【不许出现】`aios-bus`**（★ 同上）；
  (e) 两个单元都有 `WantedBy=multi-user.target`（★ 会被起，不是摆着）。

红例：★ 把 (c) 改成「总线 `Before=aios-ontology.service`」⇒ 红（★ 那就是瓜葛）。

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
        # ★★★ 作者裁：本体和总线【不要有瓜葛】⇒ 总线的 unit 里不该出现本体的名字。
        # ★ 只看【非注释行】—— ★ 注释里写「早先写过 …已撤」是记录，不是瓜葛。
        bus_code = "\n".join(
            l for l in bus.splitlines() if not l.strip().startswith("#")
        )
        if "aios-ontology" in bus_code:
            bad.append("aios-bus.service：出现了 aios-ontology（★ 有瓜葛 —— 总线要单独起）")
        if "WantedBy=multi-user.target" not in bus:
            bad.append("aios-bus.service：没有 WantedBy（★ 不会被起）")
    if ont is not None:
        # ★★★ 同上：本体的 unit 里不该出现总线的名字（★ 非注释行）。
        ont_code = "\n".join(
            l for l in ont.splitlines() if not l.strip().startswith("#")
        )
        if "aios-bus" in ont_code:
            bad.append("aios-ontology.service：出现了 aios-bus（★ 有瓜葛 —— 总线要单独起）")
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
    "Description=bus\n"
    "[Install]\n"
    "WantedBy=multi-user.target"
)
GOOD_ONT = (
    "[Unit]\n"
    "Description=ontology\n"
    "[Install]\n"
    "WantedBy=multi-user.target"
)


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    # 红例1：总线的 Before= 里没有本体（顺序丢了）
    b1 = scan(GOOD_BUS.replace("Description=bus", "Before=aios-ontology.service"), GOOD_ONT)
    print("=== 红例1（总线的 unit 里出现本体）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    # 红例2：本体单元不在
    b2 = scan(GOOD_BUS, None)
    print("=== 红例2（本体单元不在）⇒ 命中 %d 处 ===" % len(b2))
    if not any("aios-ontology" in x for x in b2):
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
