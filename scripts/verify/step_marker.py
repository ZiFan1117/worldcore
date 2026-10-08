# -*- coding: utf-8 -*-
r"""步级标记渲染（**只给门禁脚本用**：把一步的结局渲染成一个人眼可读的标记）。

为什么要它：`check.sh` 原来**无论结局是什么都打绿勾 `✅`**——于是 `kind_guard.py` 因扫描根
不在而打印 `本步**未校验**` 时，左边那个勾**还是绿的**。只看勾不看正文的人会把 SKIP 读成"过了"。
这正是本项目最忌的一种假证：**"没跑"被读成"跑过且通过"**。
⇒ 本件把"结局 → 标记"这层单独拿出来，并**钉住一条不变量**：

> **只有 `PASS` 配打 `✅`；`SKIP`／`FAIL`／`REG` 一律不打 `✅`。**

★ **2026-10-05 增 `REG`（登记型红）**：`check.sh` 的 `run_registered` 用它表达
「**跑了、判了、如实红**，但按【设计已定·未落地】**登记**、**不阻断全闸**」那一档。
★ 为什么收进本件（而不让 `check.sh` 就地写一个 ⚠️）：那样"**标记渲染就有了两个处**"，
  与「**一个事实只有一个权威载体**」相冲 —— 本件就是那个权威载体，**所以它归这里**。
★★ 三档**不许混**：`⏭`＝**没跑**（未校验）／`⚠️`＝**跑了、判了、如实红**（登记型）／`✅`＝**通过**。

用法（`check.sh` 用）：
  python3 scripts/verify/step_marker.py marker PASS     # -> ✅
  python3 scripts/verify/step_marker.py marker SKIP     # -> ⏭
  python3 scripts/verify/step_marker.py marker FAIL     # -> ❌
  python3 scripts/verify/step_marker.py marker REG      # -> ⚠️（**登记型红**；★ 绝不出 ✅）
  python3 scripts/verify/step_marker.py --self-test     # 自证：反例逐条，缺一条即红
  python3 scripts/verify/step_marker.py --self-test --break-markers   # 把逻辑短路成"恒 ✅" ⇒ 自证必红
退出码：0 = 正常；1 = 自证失败（含不变量被短路）；2 = 用法错。
"""
import sys

# 结局枚举（**唯一权威载体**；消费方 `check.sh` 只认这三个字符串）
PASS = "PASS"
SKIP = "SKIP"
FAIL = "FAIL"
REG = "REG"          # ★ 登记型红：跑了、判了、如实红；**不阻断全闸**（2026-10-05 增）
STATES = (PASS, SKIP, FAIL, REG)
EXPECT = {PASS: "✅", SKIP: "⏭", FAIL: "❌", REG: "⚠️"}
GREEN = "✅"
# 短路开关：只为 `--self-test` 证明"不变量真的会红"而存在（正常路径永不置位）
BREAK_MARKERS = False


def marker(state):
    """把结局渲染成标记。未知结局**显式报错**，不猜（不许静默当成通过）。"""
    if state not in STATES:
        raise ValueError("未知步结局：%r（只认 %s）" % (state, "／".join(STATES)))
    if BREAK_MARKERS:
        return GREEN          # ← 短路：恒绿勾（自证必须因此变红）
    return EXPECT[state]


def invariant_ok():
    """不变量：PASS 打 ✅；SKIP／FAIL／**REG** **不打** ✅。"""
    bad = [s for s in STATES if s != PASS and GREEN in marker(s)]
    if GREEN not in marker(PASS):
        bad.append("PASS 竟没打 ✅")
    return (not bad), bad


def self_test():
    print("== step_marker 自证（不变量：只有 PASS 配打 ✅）==")
    bad = 0
    for s in STATES:
        print("  %-4s -> %s" % (s, marker(s)))
    ok, bad_states = invariant_ok()
    print("  [%s] 不变量（SKIP／FAIL 不打 ✅）：%s"
          % ("OK" if ok else "失败", "成立" if ok else "破了 —— %s" % bad_states))
    if not ok:
        bad += 1
    # 反例①：未知结局必须显式报错，不许静默当通过
    try:
        marker("MAYBE")
        print("  [失败] 未知结局 'MAYBE' 竟被渲染成 %s（应显式报错）" % marker("MAYBE"))
        bad += 1
    except ValueError as e:
        print("  [OK] 未知结局显式报错：%s" % e)
    # 反例②：三种结局的标记必须互不相同（否则"人眼可读"这句就是空话）
    ms = [marker(s) for s in STATES]
    ok2 = len(set(ms)) == len(ms)
    print("  [%s] 三条结局标记互不相同：%s" % ("OK" if ok2 else "失败", ms))
    if not ok2:
        bad += 1
    # 反例③：短路成"恒 ✅"时，本自证**必须**红（证明不变量不是装饰）
    global BREAK_MARKERS
    saved = BREAK_MARKERS
    BREAK_MARKERS = True
    ok3, broken = invariant_ok()
    BREAK_MARKERS = saved
    broken_ok = not ok3           # 短路下不变量**应当**被破
    print("  [%s] 短路成恒 ✅ 时，不变量被破（%s）= %s（应 True）——不变量不是装饰"
          % ("OK" if broken_ok else "失败", broken or "无", broken_ok))
    if not broken_ok:
        bad += 1
    # 反例④（★ 2026-10-05 增，`REG`＝登记型红）：**故意给 `REG` ⇒ 必须不出 ✅**
    #   为什么**单列一条**而不靠上面那条循环顺带覆盖：`REG` 的语义是"红但不阻断"，
    #   而消费方把它的 `rc` 折算成 0 ⇒ 它**是全套结局里最容易被读成"过了"的那一个**。
    #   ⇒ **点名**给它一条反例，否则这个档位就是装饰（本仓口径：一判据一反例）。
    reg_mark = marker(REG)
    ok4 = (GREEN not in reg_mark) and (reg_mark == EXPECT[REG])
    print("  [%s] 反例④ REG ⇒ %s（应 %s，且**不含** %s）——登记型红不是绿勾"
          % ("OK" if ok4 else "失败", reg_mark, EXPECT[REG], GREEN))
    if not ok4:
        bad += 1
    print("自证%s（失败 %d 项）" % ("通过" if bad == 0 else "失败", bad))
    return 1 if bad else 0


def main(argv):
    global BREAK_MARKERS
    if "--break-markers" in argv:
        BREAK_MARKERS = True
    if "--self-test" in argv:
        return self_test()
    args = [a for a in argv if not a.startswith("--")]
    if len(args) == 2 and args[0] == "marker":
        try:
            sys.stdout.write(marker(args[1]) + "\n")
        except ValueError as e:
            sys.stderr.write("%s\n" % e)
            return 2
        return 0
    sys.stderr.write("用法：step_marker.py marker <PASS|SKIP|FAIL|REG> ｜ --self-test [--break-markers]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
