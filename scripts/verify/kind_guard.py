#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""kind 守卫（架构件里的"三类话 vs 帧上方法"口径 vs 代码结构）。

为什么要它：本仓口径「**闸在版本控制之外等于没有闸**」。此前这三条判据**只活在一份仓外的一次性脚本**
（`D:\Code\_kind_guard_check.py`，不在版本控制、不在任何门禁里）⇒ 它在与不在，门禁一样绿。
本件把它搬进仓（`scripts/`）并由 `check.sh` 的 ⑦b 步调用，于是"红"这件事有了执行体。

判据（**三条，条条会红**；`--self-test` 每条各造反例验证）：

  G1  架构件里**断言** `kind` 是"七个取值／七选一／共七个"一族 ⇒ 红。
      带否定标记（旧稿／错误说法／不是／相反／已改…）的行**不算**——那是在**改正**它。
      ——口径依据（书正文，逐字）：`ninedim/01-意图环/01-策划/策划-理论书-第一版-合订.md`
      「三类话合起来，才刚好装下各方要说的事。**留着备用的类别不必再加**」；
      「**三类之外的话今天一律被拒**」。（行号是移动靶，故此处**不写行号**。）

  G2  **表头就是 `kind`** 的表里，出现账本家族以外的家族名（`read`／`subscribe`／`describe`／`retract`）
      ⇒ 红。这就是"把**帧上方法名**与**账本三类家族**并成同一个 `kind` 取值清单"的原形，
      也正是 G1 那句错话的结构形态。账本家族的权威声明面是 `ontology.json`
      （`kind` = `enum(change, act, notice)`），**本件不重述它**。

  G3  "**四类不回行**"被**断言**（不带否定标记）⇒ 红。
      依据是**代码结构**而非字样：`src/channel.rs` 读行失败分支**有 `writeln`** ⇒ 今天**会回一行**；
      真正**不回行**的是**三类**（空请求／非法 JSON／缺 `kind`）。故"四类不回行"与代码**相反**。

★ **认结构，不认字样**（本项目踩过的坑「**搜字样 ≠ 认结构**」）：
  ① 先**剥掉引号内字样**（`"…"`／`“…”`／`「…」`／`『…』`／`` `…` ``）再匹配——引它是**引用**，不是**断言**；
  ② G2 按**表头单元格**判，不按"文件里第一处 `kind`"判，且**表体逐行逐格**看，有几处报几处。

★ **本件不能证明的事**：见文件末尾 §不能证明。

用法：
  python3 tools/kind_guard.py [根目录...]   # 缺省根＝本仓的兄弟目录「语义世界-架构」（见 default_root）
  python3 tools/kind_guard.py --self-test   # 每条判据各造反例，反例不红即判该守卫是装饰 ⇒ rc=1
  python3 tools/kind_guard.py --allow-missing  # 根目录不存在时**显式跳过**（rc=0，且打印"未校验"）
退出码：0 = 无红项且正控全在；1 = 有红项／有反例没红／正控缺；2 = 用法错（根目录不存在且未 --allow-missing）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))  # scripts/ ->  -> 仓库根

# 缺省扫描根：按序取第一个**存在**的候选。
# 为什么要"存在"才算：架构夹是**独立于仓的工作料**（设计件＋评审件＋研究料，**故意不进版本控制**）。
# 真实布局变过两次，两次都记在这儿：
#   · 2026-10-05 之前：`<仓父>/语义世界-架构`（`D:\Code\08-worldcore-openspec\world-core\tools\` → `D:\Code\语义世界-架构`）
#   · 2026-10-06 起：**并入本仓**（`.gitignore` 挡着）→ `<仓>/语义世界-架构`；同日作者指示
#     "这些文档不需要了、放到相应的地方" ⇒ 整夹退役到归档 `<语义世界-架构>`
#     ⇒ **候选里必须有它**，否则本条判据会静默变成"未校验"（实测：不加这一格时，
#        `python tool/kind_guard.py --allow-missing` 打印"未找到架构件目录…**未校验**"）。
DEFAULT_CANDIDATES = (
    os.environ.get("WC_ARCH_DIR") or "",
    os.path.join(os.path.dirname(REPO_ROOT), "语义世界-架构"),
    os.path.join(REPO_ROOT, "语义世界-架构"),
    os.path.join(REPO_ROOT, "docs", "架构"),
    # ↓ 2026-10-06 退役后的落点（**绝对路径**：归档在仓外）
    r"语义世界-架构",
)

# ── 判据 ①②③ 的字样（判据正文见文件头）────────────────────────────────
G1 = re.compile(r"七选一|七个取值|七个值|七类取值|共七个")
G3 = re.compile(r"四类不回行|四类原本就不回|读行[^\n]{0,12}不回行")
# 否定标记：出现这些词的行是在**改正**那句话，不是在断言它 ⇒ 放行。
NOT = re.compile(r"旧稿|错误说法|不成立|相反|为假|不是|已改|不许|不得|作废|纠正|改正|不实")
# ★ 结构判据的前提：**引号内的字样是在"引它"，不是"断言它"** ⇒ 先剥掉再匹配。
QUOTED = re.compile(r"“[^”]*”|\"[^\"]*\"|「[^」]*」|『[^』]*』|`[^`]*`")
# 账本家族（权威声明面是 ontology.json：`kind` = enum(change, act, notice)）
LEDGER_FAMILY = ("change", "act", "notice")
# **帧上方法名**：它们**不是**账本家族 ⇒ 与家族并进同一张 `kind` 表即是违规原形
FRAME_METHOD = ("read", "subscribe", "describe", "retract")
TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
# 短路开关（**只给 --self-test 用**：把某条判据关掉，证明"红"确实是那条判据给的）
DISABLED = set()
# 短路开关（**只给 --self-test 用**：把步级结局一律报成 PASS，证明"未校验不许长成绿勾"不是装饰）
FORCE_STATE = None


def _capture(argv):
    """在**同进程**里再跑一次本工具（argv[0] 只是名字），把 stdout 抓回来。

    为什么不用 `subprocess`：那是**另一个进程**，会掩盖"同一次运行里状态如何流转"这件事；
    这里要验的正是"分支→状态→标记"这条同进程内的链。
    """
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv[1:])
    return rc, buf.getvalue()

# 正控阈值：钉住"不该红的"，证明本判据不是"永远绿"。
# ⚠ 这是**本件的阈值**，不是外部标准要求；读数**现取**（由现场 blob 计数得来）。
CONTROLS = (
    ("帧上方法", 2, "P1 架构件里「帧上方法」这个结构词不见了（判据失去了它要区的对象）"),
    ("账本家族", 2, "P1 架构件里「账本家族」这个结构词不见了"),
    ("SectionMapDrift", 3, "P2 结构件里的同一个事实的两个名字不见了"),
)


def strip_quoted(line):
    """剥掉引号内的字样（引它是引用，不是断言）。"""
    return QUOTED.sub("□", line)


def norm_tokens(cell):
    """把一个单元格切成"标识符样"的 token，并与原格整体一起返回（供 FRAME 整体匹配）。"""
    bare = cell.replace("`", " ").replace("*", " ").strip()
    toks = set()
    if TOKEN.match(bare):
        toks.add(bare.lower())
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", bare):
        toks.add(w.lower())
    return toks


def tables(lines):
    """yield (start_lineno, rows)；rows 为连续的 `| ... |` 行块。"""
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            yield i + 1, lines[i:j]
            i = j
        else:
            i += 1


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def scan_markdown(root):
    """扫一棵树里的 .md，返回 (reds, files, blob)。

    reds 元素：(判据号, 相对路径, 行号, 说明)
    """
    reds = []
    files = []
    parts = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            if not fn.lower().endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            files.append(path)
            with open(path, "r", encoding="utf-8", newline="") as fh:
                text = fh.read()
            parts.append(text)
            lines = text.split("\n")
            rel = os.path.relpath(path, root).replace("\\", "/")
            for i, ln in enumerate(lines, 1):
                bare = strip_quoted(ln)
                if "G1" not in DISABLED and G1.search(bare) and not NOT.search(bare):
                    reds.append(("G1", rel, i, ln.strip()[:150]))
                if "G3" not in DISABLED and G3.search(bare) and not NOT.search(bare):
                    reds.append(("G3", rel, i, ln.strip()[:150]))
            if "G2" in DISABLED:
                continue
            for start, rows in tables(lines):
                if len(rows) < 3:
                    continue
                head = cells(rows[0])
                if not any(h.replace("`", "").replace("*", "").strip().lower() == "kind" for h in head):
                    continue
                # ★ 表体逐行逐格：有几处报几处（不"取第一处字样"）
                for off, row in enumerate(rows[2:]):
                    lineno = start + 2 + off
                    cs = cells(row)
                    fam = sorted({f for c in cs for f in LEDGER_FAMILY if f in norm_tokens(c)})
                    frame = sorted({f for c in cs for f in FRAME_METHOD if f in norm_tokens(c)})
                    if frame and not fam:
                        reds.append(("G2", rel, lineno,
                                     "表头=kind 的表里出现账本家族以外的家族（帧上方法名）："
                                     + "／".join("`%s`" % f for f in frame)
                                     + "  ｜ 该行：" + row.strip()[:110]))
                    elif frame and fam:
                        reds.append(("G2", rel, lineno,
                                     "表头=kind 的表把帧上方法名与账本家族并成同一取值清单："
                                     + "／".join("`%s`" % f for f in frame)
                                     + "  ｜ 该行：" + row.strip()[:110]))
    blob = "\n".join(parts)
    return reds, files, blob


def controls(blob):
    """正控：返回 (读数列表, 缺失列表)。读数现取，阈值见 CONTROLS。"""
    readings = []
    missing = []
    for word, floor, why in CONTROLS:
        c = blob.count(word)
        readings.append((word, c, floor))
        if c < floor:
            missing.append("%s（现取 %d < %d）：%s" % (word, c, floor, why))
    return readings, missing


def report(tag, root, reds, files, readings, missing):
    print("== kind 守卫（%s）==" % tag)
    print("扫描根：%s" % root)
    print("扫过的 .md 文件数：%d" % len(files))
    print("红项：%d" % len(reds))
    for rid, rel, lineno, why in reds:
        print("  RED %s %s:%d  %s" % (rid, rel, lineno, why))
    print("正控（读数现取）：" + "  ".join("%s=%d(>=%d)" % (w, c, f) for w, c, f in readings))
    for m in missing:
        print("  正控红：%s" % m)
    state = "FAIL" if (reds or missing) else "PASS"
    print("rc=%d" % (1 if (reds or missing) else 0))


# ── 自证：每条判据各造一个反例（反例不红 ⇒ 判该守卫是装饰）──────────────────
BASELINE = "\n".join((
    "# 自证样本（正控：以下每一行都**不该红**）",
    "",
    "**帧上有方法，账本里只有三类话。**",
    "账本家族只有 `change`／`act`／`notice`；`read`／`subscribe`／`describe`／`retract` 是帧上的方法名。",
    "帧上方法与账本家族是两件事：帧上方法不进账本，账本家族只在账本里。",
    "旧稿写过“`kind` 共七个取值”，那是错误说法，已按代码改正。",
    "旧稿写“四类不回行”与代码相反，此处按代码改正。",
    "`SectionMapDrift` 是那件事在别处的名字；`SectionMapDrift` 与 `SectionMapDrift` 同一事实同一名字。",
    "",
    "| kind | 干什么 |",
    "|---|---|",
    "| `change` | 改一个字段 |",
    "| `act` | 请求做一件事 |",
    "| `notice` | 记一条通告 |",
    "",
    "| 方法 | 类型 |",
    "|---|---|",
    "| `read` | query |",
    "| `subscribe` | procedure |",
    "",
))

MUT_G1 = BASELINE.replace(
    "旧稿写过“`kind` 共七个取值”，那是错误说法，已按代码改正。",
    "**`kind` 七个取值**：`change`／`act`／`notice`／`retract`／`read`／`subscribe`／`describe`。",
)
MUT_G2A = BASELINE.replace(
    "| `notice` | 记一条通告 |",
    "| `notice` | 记一条通告 |\n| `read` | 读 |",
)
MUT_G2B = BASELINE.replace(
    "| `notice` | 记一条通告 |",
    "| `notice` | 记一条通告 |\n| `change` + `describe` | 混着写 |",
)
MUT_G3 = BASELINE.replace(
    "旧稿写“四类不回行”与代码相反，此处按代码改正。",
    "六类结局里**四类不回行**（读行失败／空请求／非法 JSON／缺 `kind`）。",
)

# 每条反例的期望：**必须恰好红出这些判据号**（多红=误报、少红=漏报，都算反例无效）
SELFTEST = (
    ("基线（正控：不该红）", BASELINE, set()),
    ("G1 反例：断言 kind 七个取值", MUT_G1, {"G1"}),
    ("G2 反例 a：表头=kind 的表里出现帧上方法名", MUT_G2A, {"G2"}),
    ("G2 反例 b：表头=kind 的表把方法名与账本家族并列", MUT_G2B, {"G2"}),
    ("G3 反例：断言四类不回行", MUT_G3, {"G3"}),
)


def self_test():
    print("== kind 守卫自证（每条判据各造反例；反例不红即判该守卫是装饰）==")
    bad = 0
    import tempfile
    for name, text, want in SELFTEST:
        tmp = tempfile.mkdtemp(prefix="kindguard-selftest-")
        with open(os.path.join(tmp, "sample.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        reds, files, blob = scan_markdown(tmp)
        got = {r[0] for r in reds}
        readings, missing = controls(blob)
        ok_red = got == want
        # 正控：只对 G1／G3／G2 三组样本统一要求"锚词在"（证明判据不是"永远绿"）
        ok_ctrl = not missing
        verdict = "OK" if (ok_red and ok_ctrl) else "失败"
        if not (ok_red and ok_ctrl):
            bad += 1
        print("  [%s] %s：红出 %s，应 %s；正控%s"
              % (verdict, name, sorted(got) or "无", sorted(want) or "无",
                 "全在" if ok_ctrl else "缺 " + "；".join(missing)))
        for r in reds:
            print("        RED %s %s:%d  %s" % (r[0], r[1], r[2], r[3][:90]))
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    # 反向：把每条判据轮流短路 ⇒ 它自己的反例必须不再红
    # （证明"红"是那条判据给的，不是别处冒出来的；也证明反例与判据一一对应）
    short_cases = (
        ("G1", MUT_G1, "G1", "G1 反例"),
        ("G2", MUT_G2A, "G2", "G2 反例 a"),
        ("G2", MUT_G2B, "G2", "G2 反例 b"),
        ("G3", MUT_G3, "G3", "G3 反例"),
    )
    import shutil as _sh
    import tempfile as _tf
    for jump, sample, rid, label in short_cases:
        tmp = _tf.mkdtemp(prefix="kindguard-shortcircuit-")
        with open(os.path.join(tmp, "sample.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(sample)
        saved = set(DISABLED)
        DISABLED.add(jump)                      # 短路这条判据
        try:
            reds, _files, _blob = scan_markdown(tmp)
        finally:
            DISABLED.clear()
            DISABLED.update(saved)
        got = {r[0] for r in reds}
        ok = rid not in got
        if not ok:
            bad += 1
        print("  [%s] 短路 %s 后，%s 红出 %s（应不含 %s）——判据与反例确有一一对应"
              % ("OK" if ok else "失败", jump, label, sorted(got) or "无", rid))
        _sh.rmtree(tmp, ignore_errors=True)
    # 附：根不在时的两条分支（根的名字里带上探测标记：若它真存在 ⇒ 这组自证无效，报红）
    fake = os.path.join(tempfile.gettempdir(), "kindguard-NOT-EXIST-根")
    probe = os.path.join(fake, "自评-逐字与引用核验.md")
    fake_absent = not os.path.exists(probe)
    # 这两次调用会打印各自的分支说明；自证时不混进主报告 ⇒ 先吞掉（内容已由下面的判词概括）
    import contextlib as _cl
    import io as _io
    with _cl.redirect_stdout(_io.StringIO()):
        rc_skip = main([fake, "--allow-missing"])
        rc_hard = main([fake, os.devnull])   # 后半句的"根不存在"是**故意**造的，别让它混进主报告
    ok_branch = fake_absent and rc_skip == 0 and rc_hard == 2
    if not ok_branch:
        bad += 1
    print("  [%s] 根不在时：带 --allow-missing ⇒ rc=%d（应 0＝跳过并打印\"未校验\"）；不带 ⇒ rc=%d（应 2）"
          % ("OK" if ok_branch else "失败", rc_skip, rc_hard))
    # ★★ 步级标记的反例（三条；这是本次专修：**未校验的步不许长成绿勾**）
    #  ①根不存在 ⇒ 该步输出里**必须没有 ✅**，且**必须**带 STATUS=SKIP
    out_missing = _capture(["kind_guard.py", fake, "--allow-missing"])[1]
    ok_a = ("✅" not in out_missing) and ("STATUS=SKIP" in out_missing)
    if not ok_a:
        bad += 1
    print("  [%s] ①根不存在：输出里无 ✅ = %s；带 STATUS=SKIP = %s（都应 True）"
          % ("OK" if ok_a else "失败", "✅" not in out_missing, "STATUS=SKIP" in out_missing))
    #  ②根存在 ⇒ 该步输出里**必须有 ✅ 级证据**（STATUS=PASS 且无 RED）；根不在则本条跳过（不静默当通过）
    real = default_root()
    if real:
        out_real = _capture(["kind_guard.py", real])[1]
        ok_b = ("STATUS=PASS" in out_real) and ("RED " not in out_real)
        if not ok_b:
            bad += 1
        print("  [%s] ②根存在（%s）：STATUS=PASS = %s；无 RED = %s（都应 True）"
              % ("OK" if ok_b else "失败", real, "STATUS=PASS" in out_real, "RED " not in out_real))
    else:
        print("  [—] ②根不在本机，**本条跳过**（不是「通过」；真件上由 check.sh ⑦b 现场给读数）")
    #  ③短路：状态一律报 PASS ⇒ ①的反例必须红（证明"没有 ✅"这条不是装饰）
    saved_sf = FORCE_STATE
    globals()["FORCE_STATE"] = "PASS"
    out_forced = _capture(["kind_guard.py", fake, "--allow-missing"])[1]
    globals()["FORCE_STATE"] = saved_sf
    broke = not (("✅" not in out_forced) and ("STATUS=SKIP" in out_forced))
    ok_c = broke
    if not ok_c:
        bad += 1
    print("  [%s] ③短路成「恒 PASS」后，①的反例被破（STATUS=SKIP 不再出现）= %s（应 True）——反例不是装饰"
          % ("OK" if ok_c else "失败", broke))
    print("自证%s（失败 %d 项）" % ("通过" if bad == 0 else "失败", bad))
    return 1 if bad else 0


def default_root():
    for c in DEFAULT_CANDIDATES:
        if c and os.path.isdir(c):
            return c
    return ""


def emit_status(state):
    """打印机器可读的步级结局——**唯一出口**（所有 return 前都要过这里）。"""
    print("STATUS=%s" % (FORCE_STATE or state))


def main(argv):
    if "--self-test" in argv:
        return self_test()
    allow_missing = "--allow-missing" in argv
    roots = [a for a in argv if not a.startswith("--")]
    if not roots:
        r = default_root()
        if not r:
            msg = ("未找到架构件目录（候选：" + "；".join(c for c in DEFAULT_CANDIDATES if c) + "）")
            if allow_missing:
                print("== kind 守卫（SKIP）==\n%s\n本步**未校验**（不是「通过」）\nrc=0" % msg)
                emit_status("SKIP")
                return 0
            print("== kind 守卫（调用错误）==\n%s\n用法：kind_guard.py <根目录> ｜ --allow-missing ｜ --self-test" % msg)
            emit_status("FAIL")
            return 2
        roots = [r]
    total_reds = 0
    missing_roots = []
    ctrl_missing = []
    no_marker = []
    for root in roots:
        if not os.path.isdir(root):
            missing_roots.append(root)
            continue
        # ★ 目录在、但它**不是**架构夹（缺探测标记件）⇒ 报红，**不许**降级成"扫了 0 个文件"的假绿。
        #   为什么要有这条：若把"标记件不在"也并进 SKIP，那么把架构夹改名／挪走就会**静默变成没跑**——
        #   那是把"找不到证据"读成"没有证据"。
        if not os.path.exists(os.path.join(root, "自评-逐字与引用核验.md")):
            no_marker.append(root)
            continue
        reds, files, blob = scan_markdown(root)
        readings, missing = controls(blob)
        report("扫描", root, reds, files, readings, missing)
        total_reds += len(reds)
        ctrl_missing.extend(missing)
    if missing_roots:
        if allow_missing:
            print("== kind 守卫（SKIP）==")
            for m in missing_roots:
                print("  扫描根不存在：%s" % m)
            print("  本步**未校验**（不是「通过」）——依赖的架构夹不在这里，本步只是没跑")
        else:
            for m in missing_roots:
                print("  ❌ 扫描根不存在：%s" % m)
    for r in no_marker:
        print("  ❌ 目录在、但不是架构夹（缺探测标记件「自评-逐字与引用核验.md」）：%s" % r)
    for m in ctrl_missing:
        print("  ❌ %s" % m)
    # ★ 正控缺 = 判据失去它要区的对象 ⇒ 一律红（不因 --allow-missing 放行）
    if total_reds or ctrl_missing or no_marker:
        emit_status("FAIL")
        return 1
    if missing_roots:
        emit_status("SKIP" if allow_missing else "FAIL")
        return 0 if allow_missing else 2
    emit_status("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
