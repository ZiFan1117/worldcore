#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C124 —— **宿主侧 DSH 插件只经世界薄网关进世界**（`scripts/dsh-plugins/dsh-worldcore/`）。

★ 口径：网关「只翻译、不治理」；插件「只传输、不治理」 ⇒ 判据判五件事（静态 ＋ 可选 smoke）：
  (a) 形状：四件齐（`package.json`／`cordis.patch.yml`／`lib/index.js`／`README.md`，
      另加 `lib/world_client.js` 放纯传输函数）；单文件 ≤ 800 行；
  (b) 只发两条路：注册的工具恰好 `world_query`／`world_ask`，映射恰好
      `world_query → world.query`、`world_ask → world.ask`；源码里出现的 JSON-RPC 方法字面量 ⊆ 这两个；
  (c) 不自造拒绝码：世界拒绝码闭集（读 `src/ontology/gate/world_codes.py`，不另立一张表）里的码
      **一个都不许**出现在插件里；不许写 `world_code:`／`category:` 的字面量值；不许自己写 `code: <整数>`；
  (d) 不绕过：不许 zenoh／`world_cli`／`world/exec`／`computer_process`／子进程／总线话题字面量；
  (e) 端点与超时：从 `process.env.WORLDCORE_GATEWAY` 读，默认 `http://127.0.0.1:8780`；
      `fetch(` 调用处不许带端点字面量；ask 默认 110s、query 默认 30s；
  (f) README：写明**本插件不自动安装**、SSH 隧道命令、只听环回的安全边界、默认 actor 的性质。

限度（★ 如实）：本判据判**插件这一侧**的形状 ＋ 宿主上跑一个**假网关 smoke**（本地 HTTP，
端口 18780，不占真网关 8780）。它**不连真网关、不连真总线**；`node` 不在的机器上 smoke 记「未校验」，
**不算通过**。真机读数出在世界那一侧。

用法：
  python scripts/test/c124_dsh_world_plugin.py              跑真仓库
  python scripts/test/c124_dsh_world_plugin.py --self-test  反例自检（自造码／绕过网关／写死端点 ⇒ 红）
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import _proc_helper as H  # noqa: E402

NAME = "C124 宿主侧 DSH 插件只经网关（dsh-worldcore）"
PLUGIN = os.path.join(H.ROOT, "scripts", "dsh-plugins", "dsh-worldcore")
SMOKE = os.path.join(HERE, "c124_smoke_fake_gateway.mjs")
FILES = ("package.json", "cordis.patch.yml", "lib/index.js", "lib/world_client.js", "README.md")
PKG = "dsh-plugin-dsh-worldcore"
DEFAULT_ENDPOINT = "http://127.0.0.1:8780"
ASK_TIMEOUT_MS = 110000
QUERY_TIMEOUT_MS = 30000
WANT_METHODS = {"world_query": "world.query", "world_ask": "world.ask"}
MAX_LINES = 800

# ★ 绕过网关的第二种出口（出现任何一个就红）
BANNED_BYPASS = (
    "zenoh", "world_cli.py", "world/exec", "computer_process", "ontology_process",
    "child_process", "execFile", "spawn(", "AIOS_BUS",
    "world/query/result", "world/ask/result", "world/notice",
    "declare_subscriber", "bus.put", "world/permit",
)
URL = re.compile(r"""https?://[^\s"'`\\)]+""")
CODE_INT = re.compile(r"\bcode\s*:\s*-?\d+")
ASSIGN_LITERAL = re.compile(r"""\b(world_code|category)\s*[:=]\s*["'`]""")
STR_CONST = re.compile(r"""["']([A-Za-z][A-Za-z0-9_.\-/]*)["']""")


# ── 读源码：去掉注释但**保住字符串**（★ 字符串里有 `//`，如 world://agent/dsh）──
def strip_js_comments(text):
    out = []
    i, n, quote = 0, len(text), None
    while i < n:
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    out.append("\n")      # ★ 保住行号：报红要给原文件的行，不能给剥完的行
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_codes():
    """★ 世界拒绝码闭集：只认 `src/ontology/gate/world_codes.py`（一个事实一个载体）。"""
    H.add_paths("ontology")
    from gate import world_codes
    return dict(world_codes.REJECT_CODES), tuple(world_codes.REJECT_CATEGORIES)


# ── (c) 不自造拒绝码 ─────────────────────────────────────────
def judge_no_own_codes(files, codes):
    bad = []
    for name, text in files:
        if not name.endswith(".js"):
            continue
        code = strip_js_comments(text)
        for i, line in enumerate(code.splitlines(), 1):
            if CODE_INT.search(line):
                bad.append("%s:%d 自己写了 `code: <整数>`（★ 世界码不许自造，码只从网关回话里来）"
                           % (name, i))
            for m in ASSIGN_LITERAL.finditer(line):
                bad.append("%s:%d 给 %s 写了字面量值（★ 码／类别只许从回话里读）"
                           % (name, i, m.group(1)))
            for lit in STR_CONST.findall(line):
                if lit in codes:
                    bad.append("%s:%d 出现世界拒绝码字面量 %r（★ 自造拒绝码）" % (name, i, lit))
    return bad


# ── (d) 不绕过网关 ───────────────────────────────────────────
def judge_bypass(files, banned=BANNED_BYPASS):
    bad = []
    for name, text in files:
        if not name.endswith(".js"):
            continue
        code = strip_js_comments(text)
        for i, line in enumerate(code.splitlines(), 1):
            for tok in banned:
                if tok in line:
                    bad.append("%s:%d 出现 %r（★ 插件只许 POST 网关：不直连总线／不调 world_cli／不碰执行器）"
                               % (name, i, tok))
    return bad


# ── (e) 端点与超时 ───────────────────────────────────────────
def judge_endpoint(files, default_endpoint=DEFAULT_ENDPOINT):
    bad = []
    code_by_file = {n: strip_js_comments(t) for n, t in files if n.endswith(".js")}
    joined = "\n".join(code_by_file.values())
    readers = [n for n, c in code_by_file.items() if "WORLDCORE_GATEWAY" in c and "process.env" in c]
    if not readers:
        bad.append("插件没有从环境读端点：WORLDCORE_GATEWAY 必须经 process.env 进来（★ 端点必须可配）")
    if default_endpoint not in joined:
        bad.append("插件没有默认端点 %s（★ 隧道／NAT 转发后的默认落点）" % default_endpoint)
    elif joined.count(default_endpoint) != 1:
        bad.append("默认端点字面量出现 %d 处（★ 只许一处常量；别处一律从它来，否则就是写死端点）"
                   % joined.count(default_endpoint))
    if str(ASK_TIMEOUT_MS) not in joined or str(QUERY_TIMEOUT_MS) not in joined:
        bad.append("插件缺默认超时（ask %dms／query %dms）" % (ASK_TIMEOUT_MS, QUERY_TIMEOUT_MS))
    for name, code in code_by_file.items():
        for i, line in enumerate(code.splitlines(), 1):
            if "fetch(" in line:
                for m in URL.finditer(line):
                    bad.append("%s:%d fetch 调用处写死了端点 %r（★ 端点必须从 WORLDCORE_GATEWAY 读）"
                               % (name, i, m.group(0)))
        for m in URL.finditer(code):
            if m.group(0).rstrip("/") != default_endpoint:
                bad.append("%s 出现别的端点字面量 %r（★ 不写死端点）" % (name, m.group(0)))
    return bad


# ── (b) 工具名／方法映射 ─────────────────────────────────────
def parse_method_table(src):
    m = (re.search(r"METHOD_BY_TOOL\s*=\s*Object\.freeze\(\{([^}]*)\}\)", src)
         or re.search(r"METHOD_BY_TOOL\s*=\s*\{([^}]*)\}", src))
    if not m:
        return {}
    return {k: v for k, v in re.findall(r'(\w+)\s*:\s*"([^"]+)"', m.group(1))}


def judge_mapping(index_src, client_src):
    bad = []
    table = parse_method_table(client_src)
    if table != WANT_METHODS:
        bad.append("方法映射不是 %r，实得 %r（★ world_query→world.query，world_ask→world.ask）"
                   % (WANT_METHODS, table))
    tools = re.findall(r'defineTool\(\{\s*name:\s*"([^"]+)"', index_src)
    if sorted(tools) != sorted(WANT_METHODS):
        bad.append("注册的工具不是恰好 %r，实得 %r" % (sorted(WANT_METHODS), sorted(tools)))
    if index_src.count("ctx.tools.register(") != 2:
        bad.append("注册处不是 2 个（多一个就是多一条路）")
    used = re.findall(r"callWorld\(\s*METHOD_BY_TOOL\.(world_query|world_ask)", index_src)
    if sorted(used) != sorted(WANT_METHODS):
        bad.append("execute 没有按映射表发（实得 %r）—— 不许在这里写死方法名" % (sorted(used),))
    methods = {m for m in STR_CONST.findall(strip_js_comments(client_src))
               if m.startswith("world.")}
    methods |= {m for m in STR_CONST.findall(strip_js_comments(index_src)) if m.startswith("world.")}
    extra = methods - set(WANT_METHODS.values())
    if extra:
        bad.append("出现了别的方法字面量 %r（★ 只许 world.query／world.ask）" % (sorted(extra),))
    return bad


# ── (f) README 的硬要求 ─────────────────────────────────────
README_TOKENS = (
    ("不自动安装", "没写明「本插件不自动安装」"),
    ("ssh -i D:\\vm\\keys\\vm_ed25519 -p 2223 -N -L 8780:127.0.0.1:8780 root@127.0.0.1",
     "没给 SSH 隧道命令"),
    ("127.0.0.1", "没写网关只听环回"),
    ("VBox", "没提 VBox NAT 转发这条路"),
    ("WORLDCORE_GATEWAY", "没写端点环境变量"),
    ("world://agent/dsh", "没写默认 actor"),
    (".dsh/sessions", "没写装前备份 .dsh/sessions"),
    (".dsh/storages", "没写装前备份 .dsh/storages"),
)


def judge_readme(text):
    return ["README %s" % why for tok, why in README_TOKENS if tok not in text]


# ── (a) 形状 ───────────────────────────────────────────────
def judge_shape(files, pkg_text, patch_text):
    bad = []
    for rel in FILES:
        if rel not in files:
            bad.append("缺 %s" % rel)
    try:
        pkg = json.loads(pkg_text or "{}")
    except ValueError:
        bad.append("package.json 不是合法 JSON")
        pkg = {}
    if pkg.get("name") != PKG:
        bad.append("package.json 的 name 不是 %r（实得 %r）" % (PKG, pkg.get("name")))
    if pkg.get("type") != "module":
        bad.append("package.json 的 type 不是 \"module\"")
    if pkg.get("main") != "lib/index.js":
        bad.append("package.json 的 main 不是 lib/index.js")
    peers = pkg.get("peerDependencies") or {}
    if "@deepseek-ai/dsh-tools" not in peers:
        bad.append("package.json 没声明 peerDependencies @deepseek-ai/dsh-tools（★ 不新增依赖）")
    if "insert:" not in (patch_text or "") or PKG not in (patch_text or ""):
        bad.append("cordis.patch.yml 没给出 insert 落点（id／包名）")
    if "不自动" not in (patch_text or "") and "不会自动" not in (patch_text or ""):
        bad.append("cordis.patch.yml 没写明本文件不会被自动加载")
    for rel, text in files.items():
        n = len(text.splitlines())
        if n > MAX_LINES:
            bad.append("%s 有 %d 行（★ 单文件 ≤ %d 行）" % (rel, n, MAX_LINES))
    return bad


def read_files():
    files, missing = {}, []
    for rel in FILES:
        path = os.path.join(PLUGIN, rel)
        if not os.path.isfile(path):
            missing.append(rel)
            continue
        with open(path, "r", encoding="utf-8") as f:
            files[rel] = f.read()
    return files, missing


def run_smoke():
    """(可选) 假网关 smoke：node 在就跑，不在就如实记「未校验」。"""
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        return None, "node 不在 ⇒ 假网关 smoke 未校验（★ 不算通过）"
    try:
        p = subprocess.run([node, SMOKE, PLUGIN], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120, cwd=H.ROOT,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except OSError as exc:
        return None, "node 起不来：%s（未校验）" % exc
    out = (p.stdout or "").strip()
    return (p.returncode, out), None


def run():
    files, missing = read_files()
    codes, _cats = load_codes()
    bad = list("缺 %s" % m for m in missing)
    pkg_text = files.get("package.json", "")
    patch_text = files.get("cordis.patch.yml", "")
    js_files = [(rel, t) for rel, t in files.items() if rel.startswith("lib/") and rel.endswith(".js")]
    bad += judge_shape(files, pkg_text, patch_text)
    bad += judge_no_own_codes(js_files, codes)
    bad += judge_bypass(js_files)
    bad += judge_endpoint(js_files)
    bad += judge_mapping(files.get("lib/index.js", ""), files.get("lib/world_client.js", ""))
    bad += judge_readme(files.get("README.md", ""))

    smoke, note = run_smoke()
    if note:
        print("  [未校验] " + note)
    elif smoke[0] == 1:
        bad.append("假网关 smoke 红了：\n" + "\n".join("        " + ln for ln in smoke[1].splitlines()[-6:]))
    elif smoke[0] != 0:
        print("  [未校验] 假网关 smoke 环境问题（rc=%d）" % (smoke[0],))
        print("\n".join("        " + ln for ln in smoke[1].splitlines()[-6:]))
    else:
        tail = [ln for ln in smoke[1].splitlines() if ln.strip()]
        print("  " + (tail[-1] if tail else ""))

    print("=== %s（真仓库·静态 ＋ 假网关 smoke）===" % NAME)
    print("  现取：插件 %d 件；闭集码 %d 个；映射 %s；smoke %s"
          % (len(files), len(codes),
             "／".join("%s→%s" % kv for kv in sorted(parse_method_table(files.get("lib/world_client.js", "")).items())),
             "未校验" if note else ("rc=%d" % (smoke[0],))))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿（只发两条路／码原样透传／不绕过网关／端点可配／README 齐）===")
    return 0


def self_test():
    ok = True
    if run() != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    codes, _cats = load_codes()

    # 红例1：插件自造世界拒绝码（自己写 code 与 world_code／category）
    b1 = judge_no_own_codes([("bad.js",
        'throw new Error(JSON.stringify({code: 1201, data: {world_code: "GATEWAY_DENIED", category: "system"}}));')], codes)
    print("=== 红例1（插件自造世界拒绝码）⇒ 命中 %d 处 ===" % len(b1))
    for x in b1:
        print("      " + x)
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    # 红例1b：把闭集里的码搬进插件（自造的第二形态）
    b1b = judge_no_own_codes([("bad2.js", 'const DENY = "PERMISSION_DENIED";\nreturn {ok: false, code: DENY};')], codes)
    print("=== 红例1b（插件里写死世界码字面量）⇒ 命中 %d 处 ===" % len(b1b))
    if not b1b:
        print("[自检失败] 红例1b 该命中")
        ok = False
    # 红例2：插件绕过网关（zenoh／world_cli／world/exec／computer_process）
    b2 = judge_bypass([("bad.js",
        'import zenoh from "zenoh";\n'
        'const { execFile } = require("node:child_process");\n'
        'execFile(PY, ["world_cli.py", "ask"]);\n'
        'session.put("world/exec", msg);\n'
        'import computer_process\n')])
    print("=== 红例2（插件绕过网关）⇒ 命中 %d 处 ===" % len(b2))
    for x in b2:
        print("      " + x)
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False
    # 红例2b：fetch 调用处写死端点
    b2b = judge_endpoint([("bad.js", 'fetch("http://127.0.0.1:8780/", {method: "POST"});')])
    print("=== 红例2b（fetch 调用处写死端点）⇒ 命中 %d 处 ===" % len(b2b))
    if not b2b:
        print("[自检失败] 红例2b 该命中")
        ok = False
    # 正控1：端点从 WORLDCORE_GATEWAY 读 ⇒ 不许红
    good = [("good.js",
             'export const DEFAULT_GATEWAY = "http://127.0.0.1:8780";\n'
             'export function gatewayUrl(env = process.env) {\n'
             '  return env.WORLDCORE_GATEWAY || DEFAULT_GATEWAY;\n'
             '}\n'
             'async function send() { return fetch(gatewayUrl(), { method: "POST" }); }\n'
             'const ASK = 110000;\nconst QUERY = 30000;\n')]
    g1 = judge_endpoint(good)
    print("=== 正控1（端点从 WORLDCORE_GATEWAY 读）⇒ 命中 %d 处 ===" % len(g1))
    for x in g1:
        print("      " + x)
    if g1:
        print("[自检失败] 正控1 不该红")
        ok = False
    # 红例3：方法映射被调换
    b3 = judge_mapping('defineTool({ name: "world_query" })\ndefineTool({ name: "world_ask" })\n'
                       'callWorld(METHOD_BY_TOOL.world_query)\ncallWorld(METHOD_BY_TOOL.world_ask)\n',
                       'export const METHOD_BY_TOOL = Object.freeze({world_query: "world.ask", world_ask: "world.query"});')
    print("=== 红例3（方法映射调换）⇒ 命中 %d 处 ===" % len(b3))
    for x in b3:
        print("      " + x)
    if not b3:
        print("[自检失败] 红例3 该命中")
        ok = False
    # 正控2：映射正确 ⇒ 不许红
    g2 = judge_mapping(
        'ctx.tools.register(defineTool({ name: "world_query", execute: (a) => callWorld(METHOD_BY_TOOL.world_query, a) }));\n'
        'ctx.tools.register(defineTool({ name: "world_ask", execute: (a) => callWorld(METHOD_BY_TOOL.world_ask, a) }));\n',
        'export const METHOD_BY_TOOL = Object.freeze({world_query: "world.query", world_ask: "world.ask"});')
    print("=== 正控2（工具名／方法映射正确）⇒ 命中 %d 处 ===" % len(g2))
    if g2:
        for x in g2:
            print("      " + x)
        print("[自检失败] 正控2 不该红")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、正控不红）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
