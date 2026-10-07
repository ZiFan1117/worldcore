# -*- coding: utf-8 -*-
"""把三方数据抽成一张对照图的 JSON：你写的书 / OpenSpec / 实盘与流程侧。"""
import json, os, re, io, sys

# ★ 2026-09-28 搬进仓内（skill §九「生成链必须在仓内」）：原来在 `D:\Code\_specmap\build_specmap.py`，
#   既读仓外、又把产物写到仓外（`D:\Code\_specmap\generated/specmap.json`）⇒ **"闸在版本控制之外"**。
#   现在：**仓根按脚本自身位置推**（本文件在 `scripts/gen/` 下 ⇒ 仓根 = 上两级），产物**落回仓内** `generated/specmap.json`。
#   **生成逻辑一行未改**，只改了"它怎么找到仓、把产物写哪"。
#
# ⚠ **2026-09-28 实测：本生成器当前跑不出仓里那份产物**（149,314 B → 103,243 B），原因是**两处输入随书合并而消失**：
#   · `chapters`：原读 `语义世界-第N章-*.md`（逐章文件）⇒ 现在**一个都匹配不上**（旧产物 7 章、现在只剩"序"1 条）；
#   · `judges`：原读 `语义世界-第五章-今天做到几分.md` ⇒ 文件不存在（旧产物 17 条判据、现在 0 条）。
#   其余字段**变了是正常的**（`srs` 39→41、`tests` 4→13、`gaps_uncovered_srs` 9→11——那些是**数据变多**，不是退化）。
#   ⇒ 已加 **fail loud**：这两处输入缺失/解析为 0 时**直接报错退出**，不许静默降级（本仓纪律）。
#   ⇒ **待办**：把这两段重新对准《合订本》后重跑，使产物与生成器一致（本文件的"生成链在仓内"已成立，**只差对准**）。
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(_HERE))          # scripts/gen/ -> 仓根
SPECS = os.path.join(REPO, "ninedim", "01-意图环", "04-规格")
THEORY = os.path.join(REPO, "ninedim", "01-意图环", "01-策划")
SRS = os.path.join(REPO, "ninedim", "01-意图环", "02-需求", "需求-WC-SRS-001-v0.1.md")
TESTS = os.path.join(REPO, "scripts", "test")
OUT = os.environ.get("SPECMAP_OUT") or os.path.join(REPO, "generated", "specmap.json")
# ↑ 可用 `SPECMAP_OUT` 覆盖输出路径（判据⑫ 将来若要改成"重跑生成器逐字节比对"，靠它把产物写到临时目录）
GEN_SELF = os.path.join(REPO, "scripts", "gen", "gen_specmap.py")
with io.open(GEN_SELF, "rb") as _f:
    _GEN_SHA = __import__("hashlib").sha256(_f.read()).hexdigest()


def rl(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read().splitlines()

# ---------- 1. OpenSpec 规格 ----------
caps = []
for cap in sorted(os.listdir(SPECS)):
    d = os.path.join(SPECS, cap)
    f = os.path.join(d, "spec.md")
    if not os.path.isfile(f):
        continue
    lines = rl(f)
    purpose = []
    reqs = []
    cur = None
    scn = None
    inp = False
    for i, ln in enumerate(lines):
        if ln.startswith("## Purpose"):
            inp = True; continue
        if ln.startswith("## Requirements"):
            inp = False; continue
        if inp and ln.strip():
            purpose.append(ln.strip())
        m = re.match(r"^### Requirement:\s*(.+?)\s*$", ln)
        if m:
            cur = {"title": m.group(1), "line": i + 1, "text": [], "scenarios": []}
            reqs.append(cur); scn = None; continue
        m = re.match(r"^#### Scenario:\s*(.+?)\s*$", ln)
        if m and cur is not None:
            scn = {"title": m.group(1), "line": i + 1, "when": "", "then": "", "ev": []}
            cur["scenarios"].append(scn); continue
        if cur is not None and scn is None and ln.strip() and not ln.startswith("#"):
            cur["text"].append(ln.strip())
        if scn is not None:
            s = ln.strip()
            if s.startswith("- **WHEN**"):
                scn["when"] = s.replace("- **WHEN**", "").strip()
            elif s.startswith("- **THEN**"):
                scn["then"] = s.replace("- **THEN**", "").strip()
            elif "**证据**" in s:
                for t in re.findall(r"`([^`]+)`", s):
                    scn["ev"].append(t)
    caps.append({"cap": cap, "file": os.path.relpath(f, REPO), "purpose": " ".join(purpose), "reqs": reqs})

# ---------- 2. 流程侧 SRS ----------
srs = {}
for ln in rl(SRS):
    m = re.match(r"^\|\s*`(REQ-[A-Z]-\d{3})`\s*\|", ln)
    if not m:
        continue
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    rid = c[0].strip("`")
    if rid in srs:
        continue
    st = re.sub(r"\s+", " ", c[-1])
    if st.startswith("已实现"):
        flag = "green"
    elif st.startswith("部分实现"):
        flag = "half"
    else:
        flag = "red"
    srs[rid] = {"id": rid, "title": re.sub(r"[*`]", "", c[1]), "pri": c[2], "status": flag, "raw": st[:400]}

# ---------- 3. 书：章节（**2026-09-28 重对准合订本**） ----------
# 原来读逐章文件 `语义世界-第N章-*.md`——书合并成《合订本》之后那些文件不存在，
# 本段会**静默产出 0 章**（已加 fail loud）。现在直接从合订本的章标题取。
BOOK = os.path.join(THEORY, "策划-理论书-第一版-合订.md")
if not os.path.isfile(BOOK):
    raise SystemExit("[FAIL] 合订本不存在：%s（书章节与 5.6 判据表都由它取数）" % BOOK)
book_lines = rl(BOOK)
chapters = []
cur = None
for i, ln in enumerate(book_lines):
    # ★ 遇到**任何** H1 都要结算当前章：只有"序 / 第N章"开新章，其余 H1（`# 语义世界`／`# 附录`）**终结**当前章。
    #   为什么（实测）：合订本 `:985` 是 `# 附录`，它**不匹配**下面的章规则；若不结算，附录里的 44 个 H2
    #   会被记成"第六章"的 `六.1`–`六.44`（第六章真实只有 8 节 `6.1`–`6.8`）⇒ `counts.booksecs` 会报 90 而非 46。
    if re.match(r"^#\s+", ln):
        cur = None
    mch = re.match(r"^#\s+(序|第.+?章)\s*$", ln)
    if mch:
        cur = {"chap": mch.group(1).replace("第", "").replace("章", "").strip() or mch.group(1),
               "file": os.path.basename(BOOK), "secs": [], "line": i + 1}
        if cur["chap"] == "序":
            cur["chap"] = "序"
        chapters.append(cur)
        continue
    if cur is None:
        continue
    ms = re.match(r"^##\s+(?:(\d+\.\d+)\s+(.+?)|(.+?))\s*$", ln)
    if ms:
        if ms.group(1):
            cur["secs"].append({"num": ms.group(1), "title": ms.group(2), "line": i + 1})
        else:
            cur["secs"].append({"num": "%s.%d" % (cur["chap"], len(cur["secs"]) + 1),
                                "title": ms.group(3), "line": i + 1})
if not chapters:
    raise SystemExit("[FAIL] 合订本里一个章标题（`# 序` / `# 第N章`）都没匹配上：%s" % BOOK)

# ---------- 4. 书：第五章 5.6 判据表 ----------
judges = []
c5 = BOOK          # **2026-09-28 重对准**：原读逐章文件（不存在），现读合订本
if not os.path.isfile(c5):
    raise SystemExit(
        "[FAIL] 书第五章 5.6 判据表：源文件不存在 —— %s\n"
        "       原因：书已合并成 `语义世界-理论书-第一版-合订.md`，该逐章文件不再存在。\n"
        "       处置：同上——重新对准合订本，或显式声明本字段停用；**不许静默产出 0 条判据**。" % c5)
if os.path.isfile(c5):
    lines = book_lines          # **2026-09-28 重对准**：源＝合订本（上面已读进 book_lines）
    start = next((i for i, l in enumerate(lines) if l.startswith("## 5.6")), None)
    if start is not None:
        for i in range(start, len(lines)):
            if lines[i].startswith("#") and i > start:
                break
            if not lines[i].startswith("|"):
                continue
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if cells[0] in ("节", "检验") or "今天的结果" in cells or "怎么判" in cells:
                continue
            if len(cells) == 5 and re.match(r"^5\.\d$", cells[0]):
                sec, concl, chk, pas, res = cells[0], cells[1], cells[2], cells[3], cells[4]
            elif len(cells) == 3:
                sec, concl, chk, pas, res = "5.6附表", cells[0], cells[1], "", cells[2]
            else:
                continue
            res = re.sub(r"[*`]", "", res)
            if res.startswith("绿而无效"):
                color = "amber"
            elif res.startswith("部分红") or res.startswith("半绿"):
                color = "half"
            elif res.startswith("绿"):
                color = "green"
            else:
                color = "red"
            judges.append({"sec": sec, "conclusion": re.sub(r"[*`]", "", concl),
                           "check": re.sub(r"[*`]", "", chk),
                           "pass": re.sub(r"[*`]", "", pas),
                           "result": res[:300], "color": color, "line": i + 1})

# ---------- 5. 实盘：测试函数 ----------
tests = {}
for fn in sorted(os.listdir(TESTS)):
    if not fn.endswith(".rs"):
        continue
    src = "\n".join(rl(os.path.join(TESTS, fn)))
    fns = re.findall(r"^\s*fn\s+([A-Za-z0-9_]+)\s*\(", src, re.M)
    tests["tests/" + fn] = fns

# ---------- 6. 人工对应表 ----------
REQ_MAP = {
    "事件按序落账并可跨进程读回": ["REQ-F-003", "REQ-F-022"],
    "同一本账同时只有一个写者": [],
    "残缺的尾部被丢弃，`seq` 空洞拒绝启动": ["REQ-F-005", "REQ-F-004"],
    "账本文件恒以行边界收尾": ["REQ-F-003"],
    "摘要链检出局部篡改，并如实声明其边界": [],
    "回滚是追加补偿事件，不是改写历史": ["REQ-F-014"],
    "信封的必填字段被逐字段强制": ["REQ-F-002", "REQ-F-008"],
    "三类话之外一律被拒": ["REQ-F-008", "REQ-F-027"],
    "法律损坏或指向别处时拒绝启动": ["REQ-F-007", "REQ-N-003"],
    "事件身份在进程内唯一": [],
    "错误携带机器可读的错误码": [],
    "每一个写动作都过门禁": ["REQ-F-016", "REQ-F-015"],
    "`act` 的效果不能靠 `change` 偷渡": ["REQ-F-015", "REQ-F-016"],
    "不可逆动作只允许白名单主体并加摩擦": ["REQ-F-017"],
    "门禁配置在被管者不可写的域": ["REQ-F-015"],
    "运行中的世界不重读策略": [],
    "读模型是可丢弃的缓存": ["REQ-F-010", "REQ-F-011", "REQ-F-012"],
    "增量折叠等价于全量折叠": ["REQ-F-011"],
    "检查点是缓存，可丢弃且必须自洽": ["REQ-F-021"],
    "两份读法同源且可当场核对": ["REQ-F-020"],
    "语言投影与读模型逐项相等": ["REQ-F-018", "REQ-F-024"],
    "视觉投影的排版是可审计契约": ["REQ-F-019"],
    "身份取自内核而非请求自称": ["REQ-F-025"],
}

CAP_BOOK = {
    "ledger-integrity": ["2.5", "4.1", "5.1"],
    "envelope-validation": ["2.4", "2.7", "2.8", "2.10", "4.5"],
    "gate-enforcement": ["4.2", "5.4", "5.5"],
    "read-model": ["2.6", "4.4"],
    "projections": ["2.6", "4.4", "5.2"],
    "channel-identity": ["2.11", "4.3"],
}

# 书里讲了、规格里没有落点（"覆盖缺口"）
BOOK_GAPS = [
    {"num": "4.6", "title": "怎么把话送到", "why": "投递与订阅推送在规格里零落点", "srs": ["REQ-F-023"], "book": "第四章 4.6"},
    {"num": "2.11", "title": "说了要送到", "why": "\"送到\"这一层的规格缺失", "srs": ["REQ-F-023"], "book": "第二章 2.11"},
    {"num": "5.1", "title": "先说它做不到什么", "why": "世界外面的效果账、归责机制无规格（能力上限，不是缺陷）", "srs": [], "book": "第五章 5.1"},
    {"num": "5.3", "title": "没声明过的东西照样落账", "why": "本体 concepts 实体层：规格已写、实现零读取", "srs": ["REQ-F-030"], "book": "第五章 5.3"},
    {"num": "5.5", "title": "可不可逆，两份配置对不上", "why": "可逆性判定与两处互校无规格", "srs": ["REQ-F-017"], "book": "第五章 5.5"},
    {"num": "2.9", "title": "一个说法要回答的七个问题", "why": "\"什么单位\"这一格今天没有位置可填", "srs": ["REQ-F-028"], "book": "第二章 2.9"},
]

# 审计发现（六路核对的结论，随核对进度补）
FINDINGS = [
    # ---- envelope-validation ----
    {"cap": "envelope-validation", "sev": "严重", "n": "E1",
     "title": "错误码那条的 Scenario 与证据错位：说「四类路径」，证据里没有一条账本路径",
     "detail": "spec:78 写「触发法律、门禁、账本、读模型四类失败路径」；c15 的 7 条码来源（contract.rs:714/718/728/738/748/758/767）无一条账本路径——全仓唯一账本码断言在 scripts/test/cli.rs:155，而 check.sh 从不跑 cli.rs。且实测法律类存在无码出口：--policy pol-v2.json check → rc=2，报错是散文（gate.rs:115）。项目文档已自认：WC-IC-001:350-352「⚠ 无码」。"},
    {"cap": "envelope-validation", "sev": "严重", "n": "E2",
     "title": "t5 的证据行写「check.sh 步骤 ③」，而那一步根本不跑 t5",
     "detail": "check.sh:98 只跑 --test acceptance -- t1_ t2_ t7_（原样复跑：3 passed / 14 filtered out）；--list 确认 t5 存在但被过滤。⇒ 这条要求的唯一证据在出厂单入口里从不运行。对照 c02 标注的步骤 ③b 是真的（跑整个 contract，25 passed）。"},
    {"cap": "envelope-validation", "sev": "重要", "n": "E3",
     "title": "「法律损坏或指向别处就拒启」比证据宽三处（实现都拒，只是没有载体）",
     "detail": "① 策略文件缺失：c03 五类里没有「缺失」，全仓无载体——实测 rc=2；② 本体字段形状非法：c04 只测缺文件与空 families——实测删 envelope 段 rc=2（Ontology.NoEnvelope）；③ 本体软链：c09 只测策略（WC-HLD-001:1070 自认），实测本体软链 rc=2。"},
    {"cap": "envelope-validation", "sev": "重要", "n": "E4",
     "title": "「不存在静默接受一个畸形策略的路径」这句不成立",
     "detail": "spec:52-53 是全称；而同一用例 contract.rs:207 正面断言「多余键应被忽略，而不是拒载」，gate.rs:129-133 明说未知键一律忽略。另 Policy::load 有 12 条拒载出口，只断言了 5 条。"},
    {"cap": "envelope-validation", "sev": "一般", "n": "E5",
     "title": "t5 没有断言 Scenario 的第二句「状态未被改动」",
     "detail": "spec:30 要求状态未被改动；t5 全函数无 read_model()（对照 contract.rs:87-92 项目知道怎么写这条断言）。"},
    {"cap": "envelope-validation", "sev": "一般", "n": "E6",
     "title": "c02 里 world 字段那一轮的「报出字段名」恒真",
     "detail": "contract.rs:121 断言 msg.contains(\"MissingField\") && msg.contains(field)，而 ontology.rs:32 的前缀自带 ext.world. ⇒ field==\"world\" 时必真。其余 7 个字段不受影响。"},
    {"cap": "envelope-validation", "sev": "提示", "n": "E7",
     "title": "三条证据对 umask 敏感；另有两处静默跳过",
     "detail": "umask 000 下 c03/c04/c09 全红（rc=101），红因与主题无关（fixture mode 随 umask，报「权限为 666，对 group/other 可写」）。静默跳过两处：#![cfg(not(unix))] 使 c09 在非 Unix 上「0 项 + rc=0」；guard.rs:69-70 取不到目录属性即跳过整条目录检查。"},
    {"cap": "envelope-validation", "sev": "提示", "n": "E8",
     "title": "归档 tasks.md 给本能力列了 6 项，实物只有 5 条",
     "detail": "tasks.md:6 把「行边界」列在 envelope-validation 下，而它实际在 ninedim/01-意图环/04-规格/ledger-integrity.spec.md:67。"},

    # ---- ledger-integrity ----
    {"cap": "ledger-integrity", "sev": "严重", "n": "L1",
     "title": "规格把「v1 无链账本仍可打开」写成已成立，而项目自己把这条路径登记为【高】级自杀缺陷",
     "detail": "spec:111 与 contract.rs:1026 把「v1 兼容」写成已成立行为；WC-SCMP-001:2537「### K-3【高】在 v1（无链）账本上做一次正常 append 会把世界锁死 —— 升级路径自杀」。且归档 change 的七项排除清单从未点名 K-3（全 change 检索 K-3/K-4/K-5/SCMP = 0 命中），而 proposal.md:16-17 自称「把不成立、已知残余风险如实登记在规格里」。"},
    {"cap": "ledger-integrity", "sev": "严重", "n": "L2",
     "title": "单写者那条的措辞超出实现前提：锁只记 pid 号",
     "detail": "spec:29-30 写无条件；实现 ledger.rs:175 只写 std::process::id()，存活判据是 /proc/<pid> 存在（:182-184）⇒ 前提＝同机＋同 PID 命名空间＋/proc 可读。共享存储或独立 PID 命名空间下，存活写者的锁会被当陈旧锁回收（出现两个写者）。反向已实测：pid 号被复用时持有者已不存在却不回收（假锁死，rc=2）。"},
    {"cap": "ledger-integrity", "sev": "重要", "n": "L3",
     "title": "「解析失败的最后一行被丢弃」与实际判据不是一回事，且完整事件会被静默物理删除",
     "detail": "实现按最后一个 \\n 截断（ledger.rs:276-289，直接 set_len 落盘），不看能否解析。实测：只去掉末尾换行（该行仍是完整合法 JSON）⇒ check 报「条数=1」、rc=0，还打印「✅ 有摘要链」；随后一次 append 把该行物理删除并复用 seq。ledger.rs:385 自述「启动『截到最后一个 \\n』会静默删掉它们」——摘链那条边界要求如实声明，这条没有。"},
    {"cap": "ledger-integrity", "sev": "重要", "n": "L4",
     "title": "t2 证据层级错位：规格写「新进程」，测试是同进程 drop + reopen",
     "detail": "spec:23 写「以新进程打开」；acceptance.rs:88-104 实为同进程 drop 后 reopen。全仓只有 cli.rs:20/39 起新进程。真正合格的证据（TC-070，tools/s1_sys_probe2.sh:379-384「两次独立进程读回的事件序列逐字节相同」）没被引用。"},
    {"cap": "ledger-integrity", "sev": "重要", "n": "L5",
     "title": "t1 的「逐字段一致」没有被断言",
     "detail": "acceptance.rs:68-80 只比 len/seq/world/kind/body.before；actor、id、at、flags、body.subject、body.path、body.after 一个都没比。"},
    {"cap": "ledger-integrity", "sev": "一般", "n": "L6",
     "title": "MixedChain 在启动路径被拒，没有任何自动化断言",
     "detail": "lib.rs:105 load_chain()? 会拒，但仓库内 MixedChain 只出现在 contract.rs:845（注释）/879（c17 函数级）与两处 tools 注释；系统级证据只在 ninedim/01-意图环/01-策划/专家评审/复跑-九项保证-2026-09-27-VM.md:130-140 手工留档。与 L1 同一条路径。"},
    {"cap": "ledger-integrity", "sev": "一般", "n": "L7",
     "title": "R6 把「系统实现回滚」写成能力，而系统里没有回滚操作",
     "detail": "spec:116/120；src/ 全目录无回滚 API 或子命令（rollback_after_failed_write 是 I/O 回滚；carrier/mod.rs:32-34 明说载体撤销「不是世界状态」）；t17 由测试自己再提交一条互换 change（acceptance.rs:563-569）。SRS:257 的口径更准：「回滚通过追加一条普通 change 完成」。"},
    {"cap": "ledger-integrity", "sev": "一般", "n": "L8",
     "title": "两处低危：注释误述文档现状、check.sh 未给路径",
     "detail": "contract.rs:1039-1040 说「纯粹的 I/O 失败注入…本项目尚无工具」，而 WC-TP-001:79 已写「部分闭合（2026-09-27）…U20–U22 实测三条分支」（实跑 3 passed rc=0），且这是 R4 在写失败下最强的证据、规格未引；spec:19/25/36 只写 check.sh，而仓里有两个同名脚本（根 check.sh 完全不碰 world-core）。"},
    {"cap": "ledger-integrity", "sev": "严重", "n": "L9",
     "title": "基线自己的验证口径只有「名字存在性」——这就是 2–6 类问题从未被核过的原因",
     "detail": "tasks.md:16/17/22、design.md:121 逐字把核对写成「证据行指向真实存在的测试名」「6 份规格 / 40 条证据 / 0 条未命中」。名字存在 ≠ 断言的真是那件事。本轮六路审计抓到的正是这个差值：机械命中 40/40，而语义相符远低于此。"},

    # ---- channel-identity（判定：不通过）----
    {"cap": "channel-identity", "sev": "严重", "n": "C1",
     "title": "规格写「采用内核身份、忽略自称」，证据断言的却是「拒绝」",
     "detail": "spec:16「世界采用内核给出的身份，请求正文里的自称被忽略」；contract.rs:668-670 实为 expect_err + contains(\"Impersonation\") + last_seq 不变（即拒绝且不落笔）。SRS:266/268/383、RTM:29/31 三处都写「拒绝且不落笔」⇒ 规格与证据、文档三方差一层意思。"},
    {"cap": "channel-identity", "sev": "严重", "n": "C2",
     "title": "「从内核提供的连接元数据中取得身份」不成立：实现不取任何连接凭证",
     "detail": "spec:11 写「连接元数据」；channel.rs:256-257 自述「不需要（也无法用）peer_cred」，身份＝套接字文件的属主/权限（channel.rs:187-200）。WC-LLD-001:140、SRS:268、WC-FMT-001:1023 三处文档口径与此一致，唯独规格写成了连接元数据。"},
    {"cap": "channel-identity", "sev": "严重", "n": "C3",
     "title": "「身份取自内核」对 root 不成立，而这条边界规格通篇未登记",
     "detail": "实测（套接字 actor=world://agent/1、uid=1001、mode=600）：uid 1001 连上→落笔 agent/1；root 连上→同样落笔 agent/1。只有 root「自称」world://user 才被拒 ⇒ 该检查只抓自称、不抓谁连上。书第五章:69 已登记「最高权限的用户可以连任何套接字，这一项对它无效」。"},
    {"cap": "channel-identity", "sev": "重要", "n": "C4",
     "title": "被引证据绕过了它要验证的机制本身",
     "detail": "contract.rs:642 用 std UnixListener::bind，没走 channel::bind（main.rs:578-581 自述这一绕过）；真正执行该机制的是 tools/system_acceptance.sh:301-351（㉒–㉖），由 check.sh 步骤⑦执行——而规格引的是步骤③b。"},
    {"cap": "channel-identity", "sev": "重要", "n": "C5",
     "title": "写窄：四项已实现行为规格零落点",
     "detail": "① 缺省拒绝 ext.world.Channel.NotConfigured（main.rs:604-615，实测 rc=2）② 自称与映射一致时被接受 ③ 拒绝时先回一行 {\"ok\":false,...} 再报错（channel.rs:279；SRS REQ-F-023 反例① 明确要求它）④ 空 listeners 拒载（channel.rs:89-94）。"},
    {"cap": "channel-identity", "sev": "一般", "n": "C6",
     "title": "断言里有两处装饰性成分",
     "detail": "contract.rs:648 判据1 的请求根本没有 actor 字段 ⇒ 证明不了「自称被忽略」；libc_uid() 读不到 /proc 时静默返回 0（:685/689/693），而 expect.uid 在 serve_once 路径上从不被读 ⇒ 注释「同 uid 连接」（:644）无断言支撑。"},

    # ---- gate-enforcement（规格把书稿判红写成绿）----
    {"cap": "gate-enforcement", "sev": "严重", "n": "G1",
     "title": "规格把书稿判红的「摩擦落点」反转写成绿",
     "detail": "书稿 5.5:89 逐字「摩擦本该挂在动作的不可逆等级上…今天它挂在执行者的身份上」判红；spec:36 却写「SHALL 对声明为不可逆的能力追加摩擦」。实现 gate.rs:287-293 站书稿一边：不可逆只决定要不要看身份，加不加摩擦由身份决定。"},
    {"cap": "gate-enforcement", "sev": "严重", "n": "G2",
     "title": "「只允许白名单主体」与「加摩擦」在出厂配置下不可能同时为真",
     "detail": "policy.json:32 的 irreversible_actors 只有 world://user 一个；实测该唯一成员执行 reversible:false 的 ledger.compact ⇒ APPEND_RC=0、账本只 1 行 act、gate.* 通告 0 条（换 agent/1 才 RC=2 并落 1 条 awaiting-approval）。缺陷台账 D-20 已登记此事实。"},
    {"cap": "gate-enforcement", "sev": "严重", "n": "G3",
     "title": "书稿判红的三条依据里，两条规格完全沉默——正是基线自己排除掉的东西",
     "detail": "书稿 5.5:93 判「闸读不到风险等级」：ninedim/01-意图环/04-规格/ 下 risk|风险 零命中、gate.rs 零命中；书稿 5.6:117 判「载体可逆与世界可逆无互校」：规格通篇不提。而本基线 design.md:114 逐字把「可逆性判定的落地（两处配置对不上，判红）」列为明确不入基线，tasks.md:41-42 却用「测试函数名误报」把它对账掉了。"},
    {"cap": "gate-enforcement", "sev": "重要", "n": "G4",
     "title": "一处张冠李戴：c23_gate_notice_says_what_it_refused 走的是不可逆路径",
     "detail": "contract.rs:1152 断言的是 gate.awaiting-approval（不可逆路径，:1167），不是「保留前缀通告被拒」路径；而被引的 c23_notice_with_reserved_prefix 只查错误码、不查 refused 指纹。实测该路径流水确实带 refused=fnv1a64:a3fd5c16915cd6e1——行为是真的，但没有任何断言为它变红。"},
    {"cap": "gate-enforcement", "sev": "一般", "n": "G5",
     "title": "规格写宽：说「属主与权限」，实现只看 mode 位、且属主断言默认不跑",
     "detail": "spec:54-55「启动时检查法律与账本的属主与权限」；guard.rs:30-31 逐字「本模块只看 mode 位，不看属主」、:125-126「没人传 expected_uid 时它不会运行」。"},
    {"cap": "gate-enforcement", "sev": "一般", "n": "G6",
     "title": "漏了「通告的闸」与「门禁不可绕过的部分实现」边界",
     "detail": "lib.rs:270/280 逐字「任何主体可以写任何通告」「任何人都能替世界说」（D-13）无 Requirement 级条目；SRS:258 / RTM:16 记「部分实现…祖先链遍历、通道层与 Landlock 自缚未做」的边界规格未写。另 spec:19 的「check.sh 步骤 ③」引用错（check.sh:98 只跑 t1_ t2_ t7_）。"},

    # ---- projections（同源核对：绿而无效）----
    {"cap": "projections", "sev": "严重", "n": "P1",
     "title": "「同源」那条判据与命令实际做的事不是一件事，且近乎恒真",
     "detail": "spec:18 的 THEN 是「两份投影首行逐字一致」；证据 cli.rs:236-241 只断言 rc==0 ＋ stdout 含「同源」「✅」。而 main.rs:396/407-410 两份投影共用同一个 state 与 vocab ⇒ mod.rs:126-145 的三个不等分支在 project check 里结构上不可达，对任何输入都只会绿。"},
    {"cap": "projections", "sev": "严重", "n": "P2",
     "title": "规格把项目自评为「绿而无效／红」的能力写成了「已成立」",
     "detail": "spec:10-13 只写正向义务、一字不提边界；台账 v0.5:421/431 判「绿而无效（只比头部四项、不比内容；自己渲染两份再自己比，从未比过两份由不同一方独立生成的投影）」，第四章:192 直接判红，RTM:21 记「该用例尚未实现」。"},
    {"cap": "projections", "sev": "重要", "n": "P3",
     "title": "被引证据 cli05 不在规格并列指出的出厂步骤上",
     "detail": "spec:19 写「（check.sh 步骤 ④）」；但 check.sh 全文不跑 --test cli（:98 只跑 t1_ t2_ t7_、:103 只跑 contract）⇒ bash check.sh 全绿的那次运行里 cli05 一次都没执行。"},
    {"cap": "projections", "sev": "重要", "n": "P4",
     "title": "视觉投影「与读模型逐项相等」已实现、已测、SRS 有判据，规格里没有任何条目",
     "detail": "spec:29 只限定「语言投影 SHALL 由读模型派生」；而 acceptance.rs:674-679 的 t15 实断言视觉投影逐项相等（SRS REQ-F-019 判据④同款）。规格 Purpose 说「只能省略不能添加」，Requirement 没落。"},
    {"cap": "projections", "sev": "一般", "n": "P5",
     "title": "R2 措辞自相张力，且与 SRS 的 P0 条目口径不一",
     "detail": "spec:29-30 主句要求「完全相等」，括注说「只能省略」（互相不容）；SRS:267（REQ-F-024，P0）的口径是包含关系 P ⊆ S。同一件事三处三个强度。"},
    {"cap": "projections", "sev": "一般", "n": "P6",
     "title": "R3 只写 2 条排版规则，审计器实际执行 11 条契约 / 12 个变异",
     "detail": "spec:40-41 只列「2 空格主体行 / 6 空格字段行」两条；visual_layout_audit.py:15-32 列了契约 1–11（分隔线 44 个 U+2500、摘要行格式、空状态恰 4 行、字段行不得先于主体行…），12 个变异里多个落在规格没写的契约上。"},
    {"cap": "projections", "sev": "提示", "n": "P7",
     "title": "两条恒真断言与过时行号",
     "detail": "s1_sys_probe2.sh:372 用同一个命令替换比自身（恒等），标签却写「自报同源」；台账三处引 src/main.rs:394-397，而「check」分支现在在 :407-410（行号漂移）。"},

    # ---- read-model ----
    {"cap": "read-model", "sev": "严重", "n": "R1",
     "title": "检查点 CLI 已接线，三份受控文档仍写「v1 CLI 从不读快照」",
     "detail": "main.rs:28-30/153 已把 checkpoint write|verify|resume 接进生产 CLI；WC-RTM-001.csv:22、WC-SRS-001:921、WC-UT-001:54 仍断言不存在该路径。这条「零生产调用者」正是给 fsync 缺陷降级的唯一理由。"},
    {"cap": "read-model", "sev": "严重", "n": "R2",
     "title": "规格写宽：「账本内容损坏 ⇒ 拒绝产出」，而末尾半行是静默丢弃",
     "detail": "spec:22-23 用全称量词；ledger.rs:276-279 明确丢弃末尾半行，t3_partial_line_is_discarded 正面背书该行为。"},
    {"cap": "read-model", "sev": "重要", "n": "R3",
     "title": "「检查点必须自洽」在规格里无定义、在断言里无落点",
     "detail": "spec:37 标题承诺「自洽」，正文与两条 Scenario 零定义；checkpoint.rs 的 verify 只查 base_seq 与 digest。"},
    {"cap": "read-model", "sev": "重要", "n": "R4",
     "title": "CLI 直接暴露未核验续算路径，模块文档承诺「核验不通过即拒绝使用」",
     "detail": "main.rs:534-542 → checkpoint.rs:173 resume_unverified；checkpoint.rs:14 逐字「核验不通过即拒绝使用」，:29-30 自认「不核验的路径会吃下篡改内容」。"},
    {"cap": "read-model", "sev": "一般", "n": "R5",
     "title": "Checkpoint::FORMAT 版本不符零断言，规格未登记版本约束",
     "detail": "checkpoint.rs:94 的 BadFormat 分支存在但无测试；WC-SCMP-001:535 把版本约束列为缓存格式的唯一约束。"},
    {"cap": "read-model", "sev": "一般", "n": "R6",
     "title": "实现有、规格没有的行为至少 3 项",
     "detail": "① 确定性=逐字节可复现（readmodel.rs:40-42）② 末尾半行丢弃不算损坏 ③ 检查点格式版本约束。"},
    {"cap": "read-model", "sev": "一般", "n": "R7",
     "title": "规格 Purpose 自称「唯一自动化检验所在」，与同仓文档冲突",
     "detail": "spec:4-5；同仓另有摘要链核验（c19/c20/c21/cli02）与投影同源核对两条独立检验。"},
    {"cap": "read-model", "sev": "一般", "n": "R8",
     "title": "REQ-N-008（带检查点路径的性能目标）无任何断言，规格未作范围外声明",
     "detail": "WC-RTM-001.csv:40 状态「未实现」；scripts/test/perf.rs 三条全部 #[ignore]，无一条测带检查点续算。"},
    {"cap": "read-model", "sev": "提示", "n": "R9",
     "title": "证据链无机械门禁：改一个测试名，规格不会变红",
     "detail": "tools/doc_integrity.py 的受控清单里 openspec 零命中——正是本 change 要补的 spec_bridge.py 那一条。"},
    {"cap": "read-model", "sev": "提示", "n": "R10",
     "title": "t8 用 State::fold 直喂向量，使 SeqGap 检查在生产路径上不可达",
     "detail": "账本层 ledger.rs:304 更早拦截；不是缺陷，是防线冗余，但读者会误以为是端到端验证。"},
]

# ---------- 7. 计算缺口 ----------
gaps_missing_req = []
for c in caps:
    for r in c["reqs"]:
        if not REQ_MAP.get(r["title"]):
            gaps_missing_req.append({"cap": c["cap"], "req": r["title"], "line": r["line"], "file": c["file"]})

mapped_srs = set()
for v in REQ_MAP.values():
    mapped_srs.update(v)
gaps_uncovered_srs = [v for k, v in sorted(srs.items()) if v["status"] in ("red", "half") and k not in mapped_srs]

data = {
 "_generator_sha256": _GEN_SHA,   # 判据⑫ 核它（生成器变了而产物没重生成 ⇒ 红）
    "generated": "2026-09-27",
    "caps": caps, "srs": list(srs.values()), "chapters": chapters, "judges": judges,
    "tests": tests, "req_map": REQ_MAP, "cap_book": CAP_BOOK, "book_gaps": BOOK_GAPS,
    "findings": FINDINGS,
    "gaps_missing_req": gaps_missing_req, "gaps_uncovered_srs": gaps_uncovered_srs,
    "counts": {
        "caps": len(caps), "reqs": sum(len(c["reqs"]) for c in caps),
        "scns": sum(len(r["scenarios"]) for c in caps for r in c["reqs"]),
        "evs": sum(len(s["ev"]) for c in caps for r in c["reqs"] for s in r["scenarios"]),
        "srs": len(srs), "judges": len(judges),
        "booksecs": sum(len(c["secs"]) for c in chapters),
    },
}
# ★ 2026-09-28 修：文本模式在 Windows 上会把 `\n` 写成 `\r\n`——本仓要求 LF。
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(json.dumps(data["counts"], ensure_ascii=False))
print("缺REQ号的Requirement =", len(gaps_missing_req), [g["req"] for g in gaps_missing_req])
print("未覆盖的非绿SRS =", len(gaps_uncovered_srs), [g["id"] for g in gaps_uncovered_srs])
print("判据行 =", len(judges), "色分布 =", {c: sum(1 for j in judges if j["color"] == c) for c in ("green", "amber", "half", "red")})
print("写出:", OUT)
