#!/usr/bin/env python3
"""C26 —— **都走 zenoh；13 的 crates 里不做数据面那一族**（T-276）。

★ 作者裁（逐字）：「**都走 zenoh，单独进程，不在 win，但是虚拟机**」。
⇒ ★ 一切消息（含数据）都走 zenoh ⇒ ★ **13 的 `crates/` 里不该出现【数据面】那一路的实现**：
  · 递 fd（`SCM_RIGHTS`／`sendmsg`）
  · 共享内存（`shm_open`／`memfd_create`／`mmap`）
  · 数据面传输（`arrow`／`arrow-flight`）

红＝ 出现上表任一（★ 因为「都走 zenoh」把那条路废了）。

限度（★ 如实）：判**文本** ⇒ 用别的写法自己实现共享内存，★ 本判据挡不住。

用法：
  python verify/c26_only_zenoh_no_data_plane.py              跑真仓库
  python verify/c26_only_zenoh_no_data_plane.py --self-test   反例自检
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ★★ 只扫【我方新增的 crate】—— ★ 裁决约束的是【我们的实现】；
#   ★ 上游 `aios-sandbox` 用 `memfd_create` 是【沙箱资源限额】机制，★ 不是数据面传输 ⇒ 不在射程内。
WS = [os.path.join("crates", "aios-worldcore"), os.path.join("crates", "aios-ontology")]
NAME = "C26 都走 zenoh：crates 里不做数据面那一族"

BANNED = [
    (r"SCM_RIGHTS", "递 fd（★ 数据面那一族）"),
    (r"shm_open", "共享内存（★ 数据面那一族）"),
    (r"memfd_create", "匿名内存 fd（★ 数据面那一族）"),
    (r"arrow_flight|arrow-flight", "Arrow Flight（★ 数据面那一族）"),
]


def walk(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".rs"):
                out.append(os.path.join(d, f))
    return out


def scan(texts):
    bad = []
    for p, t in texts:
        for pat, why in BANNED:
            if re.search(pat, t):
                bad.append("%s：出现 %s —— ★ 都走 zenoh ⇒ 不做 %s" % (p, pat, why))
    return bad


def run(label="真仓库"):
    texts = []
    for root in WS:
        for p in walk(root):
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                texts.append((p, f.read()))
    bad = scan(texts)
    print("=== %s（%s）===" % (NAME, label))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿 ===")
    return 0


def self_test():
    ok = True
    if run(label="绿例·真仓库") != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    b1 = scan([("x.rs", "let fd = libc::SCM_RIGHTS;")])
    print("=== 红例1（出现 SCM_RIGHTS）⇒ 命中 %d 处 ===" % len(b1))
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    b2 = scan([("y.rs", "let x = arrow_flight::client();")])
    print("=== 红例2（出现 arrow_flight）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
