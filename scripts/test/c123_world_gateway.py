#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C123 —— **世界薄网关只翻译、不治理**（外部进世界的那道门）。

★ 口径：「网关只做协议翻译」 ⇒ 判据判四件事（真调翻译层 ＋ 静态检查 ＋ 真 HTTP）：
  (a) 形状：`src/gateway/world_gateway.py` 在；只听 `127.0.0.1:8780`；HTTP ＋ JSON-RPC 2.0；
  (b) 只翻译：出向话题**恰好** `world/query` ＋ `world/ask`；总线消息 ＝ 调用方 params 原样
      （只多一个关联号 id，不补 actor、不改字段）；本体回话**原样**进 result；
  (c) 不自造拒绝码：`world_code` 必须＝本体回话里的码，且在本体闭集里、类别对得上；
      本体没给码（含超时）⇒ 回话里**不许**出现 `world_code`；应用层码不占 JSON-RPC 保留区间；
  (d) 不绕过：静态依赖检查——网关不许 import 执行器/本体流程（只许 `bus_auth` 与 `gate.world_codes`），
      不许出现 `world/exec` 这类第二种出口、不许起子进程、不许自己记账；
  (e) 部署：`aios-gateway.service` 在；`deploy.sh` 四处清单都带 `aios-gateway`；
  (f) 真 HTTP：起临时端口 ＋ 假总线，POST 一条 JSON-RPC，回话是合法 JSON-RPC。

限度（★ 如实）：判的是【网关这一侧的翻译】；真连总线、真连宿主插件要在 VM 上跑，本判据不连真总线。

用法：
  python scripts/test/c123_world_gateway.py              跑真仓库
  python scripts/test/c123_world_gateway.py --self-test  反例自检（自造码／绕过 world/ask ⇒ 红）
"""
import ast
import json
import os
import sys
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import _proc_helper as H  # noqa: E402

NAME = "C123 世界薄网关只翻译、不治理"
ROOT = H.ROOT
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
UNIT = os.path.join(ROOT, "scripts", "release", "systemd", "aios-gateway.service")
DEPLOY = os.path.join(ROOT, "scripts", "release", "deploy.sh")

# ★ 网关只许借两样本体件：总线凭据（bus_auth）与拒绝码闭集表（gate.world_codes）。
ALLOWED_LOCAL = {"bus_auth", "gate.world_codes"}
LOCAL_ROOTS = {"gate", "bus_auth", "computer_process", "ontology_process", "protocol",
               "presentation_process", "space_process", "agent_llm", "world_functions",
               "foundry_ontology", "guard_process", "web_process", "fs_process",
               "world_query"}
# ★ 只许出现这四个话题字面量（请求两个、回话两个）；别的一律是第二种出口。
ALLOWED_TOPICS = {"world/query", "world/ask", "world/query/result", "world/ask/result"}
PROCESS_TOKENS = ("subprocess", "os.system", "os.popen", "shell=True",
                  "computer_process", "ontology_process", "gate.ask_path",
                  "p2_call", "ledger")


# ── 假总线：记下 put，并按主题投一条预设回话（同一 id）──
class _Sub:
    def __init__(self, subs, item):
        self.subs, self.item = subs, item

    def undeclare(self):
        try:
            self.subs.remove(self.item)
        except ValueError:
            pass


class FakeBus:
    def __init__(self, replies=None):
        self.puts, self.subs, self.last_reply = [], [], None
        self.replies = replies or {}

    def declare_subscriber(self, topic, cb, *a, **k):
        item = [str(topic), cb]
        self.subs.append(item)
        return _Sub(self.subs, item)

    def put(self, topic, payload, **kw):
        self.puts.append((str(topic), payload))
        fn = self.replies.get(str(topic))
        if fn is None:
            return
        d = fn(json.loads(payload))
        self.last_reply = d
        if d is None:
            return
        for t, cb in list(self.subs):
            if t == str(topic) + "/result":
                cb(H.Sample(d))


# ── 纯函数判据（自带红例可喂）──
def imports_of(text):
    mods = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.append(node.module)
    return mods


def topic_literals(text):
    """源码里出现的 `world/*` 字符串常量（AST 取常量；注释与散文不算）。"""
    out = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("world/"):
                out.add(node.value)
    return out


def judge_source(files, allowed=ALLOWED_LOCAL, topics=ALLOWED_TOPICS, banned=PROCESS_TOKENS):
    """(d) 网关源码不许有第二种出口、不许 import 执行器/本体流程。"""
    bad = []
    for name, text in files:
        for mod in imports_of(text):
            if mod.split(".")[0] in LOCAL_ROOTS and mod not in allowed:
                bad.append("%s import 了 %s（★ 只许 %s）" % (name, mod, sorted(allowed)))
        for topic in sorted(topic_literals(text) - topics):
            bad.append("%s 出现话题字面量 %r（★ 网关只发 world/query＋world/ask）"
                       % (name, topic))
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):       # ★ 注释不执行，不算违规
                continue
            for tok in banned:
                if tok in line:
                    bad.append("%s:%d 出现禁项 %r（★ 网关只许翻译）" % (name, i, tok))
    return bad


def judge_shape(gw):
    """(a) 只听环回、端口 8780、方法就两个、出口就两个。"""
    bad = []
    if gw.HOST != "127.0.0.1":
        bad.append("HOST=%r（★ 只听环回）" % (gw.HOST,))
    if gw.DEFAULT_PORT != 8780:
        bad.append("DEFAULT_PORT=%r（★ 要 8780）" % (gw.DEFAULT_PORT,))
    if set(gw.rpc.METHODS) != {"world.query", "world.ask"}:
        bad.append("方法集不是 world.query／world.ask：%r" % (sorted(gw.rpc.METHODS),))
    if set(gw.rpc.PUT_TOPICS) != {"world/query", "world/ask"}:
        bad.append("出向话题不是恰好两个：%r（★ 多一个就是第二条路）" % (sorted(gw.rpc.PUT_TOPICS),))
    if not hasattr(gw, "ThreadingHTTPServer"):
        bad.append("没有 HTTP 服务（应当走 http.server）")
    return bad


def judge_app_codes(mod):
    """(c) 应用层码不许占 JSON-RPC 保留区间（-32768..-32000）。"""
    bad = []
    for name in ("CODE_WORLD_REJECT", "CODE_BUS_TIMEOUT", "CODE_BUS_ERROR"):
        code = getattr(mod, name, None)
        if not isinstance(code, int):
            bad.append("%s 不是整数：%r" % (name, code))
        elif -32768 <= code <= -32000:
            bad.append("%s=%d 落在 JSON-RPC 保留区间（★ 世界拒绝码不许占这里）" % (name, code))
    return bad


def judge_topics(puts, allowed):
    return ["网关发了 %s（★ 只许 %s）" % (t, "／".join(sorted(allowed)))
            for t, _ in puts if t not in allowed]


def judge_passthrough(params, msg):
    """(b) 总线消息 ＝ 调用方 params ＋ 关联号 id；别的一字不加、一字不改。"""
    got = dict(msg)
    rid = got.pop("id", None)
    bad = []
    if not rid:
        bad.append("总线消息没有关联号 id")
    if got == params:
        return bad
    missing, extra = set(params) - set(got), set(got) - set(params)
    if missing:
        bad.append("总线消息丢了字段：%s" % sorted(missing))
    if extra:
        bad.append("总线消息多出字段：%s（★ 不许替调用方造）" % sorted(extra))
    if not missing and not extra:
        bad.append("总线消息的字段值被改了：%r ≠ %r" % (got, params))
    return bad


def _judge_code_space(err, bad):
    code = (err or {}).get("code")
    if not isinstance(code, int):
        bad.append("error.code 不是整数：%r" % (code,))
    elif -32768 <= code <= -32000:
        bad.append("error.code=%d 落在 JSON-RPC 保留区间" % code)


def judge_echo(method, reply, envelope, codes):
    """(c) 网关回话 vs 本体回话：码不许改、不许丢、不许自造。"""
    bad = []
    err = envelope.get("error")
    if reply is not None and reply.get("ok") is True:
        if err is not None:
            bad.append("本体说 ok=true，网关却回了 error")
        elif envelope.get("result") != reply:
            bad.append("本体回话没有原样进 result")
        return bad
    if method == "world.query":
        if envelope.get("result") != reply:
            bad.append("world.query 的回话没有原样进 result")
        return bad
    if reply is None:
        if err is None:
            bad.append("总线没回话，网关却没回 error")
        else:
            _judge_code_space(err, bad)
            if "world_code" in (err.get("data") or {}):
                bad.append("超时也回了 world_code（★ 那是替世界说话）")
        return bad
    if err is None:
        bad.append("本体拒了（ok=false），网关却回了 result")
        return bad
    _judge_code_space(err, bad)
    data = err.get("data") or {}
    got, want = data.get("world_code"), reply.get("code")
    if want:
        if got != want:
            bad.append("世界码被改／丢了：本体给 %r，回话 world_code=%r" % (want, got))
        elif want not in codes:
            bad.append("本体给的码不在闭集：%r（★ 这条是本体的问题，C29 会抓）" % (want,))
        elif data.get("category") != codes.get(want):
            bad.append("%s 的 category=%r ≠ 闭集 %r"
                       % (want, data.get("category"), codes.get(want)))
    elif got:
        bad.append("本体没给码，网关却写了 world_code=%r（★ 自造）" % (got,))
    if data.get("reply") != reply:
        bad.append("data.reply 不是本体回话原样")
    return bad


def judge_deploy(unit, deploy_src):
    bad = []
    if not unit:
        bad.append("缺 scripts/release/systemd/aios-gateway.service")
    else:
        for tok in ("ExecStart=/usr/bin/python3 /usr/lib/aios/src/gateway/world_gateway.py",
                    "AIOS_GATEWAY_PORT=8780", "127.0.0.1", "WantedBy=multi-user.target"):
            if tok not in unit:
                bad.append("单元缺 %r" % tok)
    hits = [ln for ln in (deploy_src or "").splitlines() if "aios-gateway" in ln]
    if len(hits) < 4:
        bad.append("deploy.sh 带 aios-gateway 的行只有 %d 处（BUS_UNITS／安装／重启／状态四处都要）"
                   % len(hits))
    return bad


# ── 回话夹具（本体的真实信封形状）──
QUERY_PARAMS = {"kind": "overview", "actor": "world://agent/dsh", "ticket": "tk-c123"}
ASK_PARAMS = {"action": "sys.GetMemoryInfo", "params": {"p": 1}, "actor": "world://agent/dsh"}


def reply_query(msg):
    return {"id": msg.get("id"), "kind": msg.get("kind"), "ok": True,
            "data": {"counts": {"classes": 27}}}


def reply_ask_ok(msg):
    return {"id": msg.get("id"), "at": "2026-11-08T00:00:00+08:00",
            "action": msg.get("action"), "ok": True, "body": {"ok": True}}


def reply_ask_unknown(msg):
    return {"id": msg.get("id"), "ok": False,
            "why": "不在册（注册表里没有、本体 actions 里也没有）", "code": "UNKNOWN_ACTION"}


def reply_ask_no_identity(msg):
    return {"id": msg.get("id"), "ok": False,
            "why": "没有身份（★ 请求要带 actor，或带票）", "code": "NO_IDENTITY"}


def reply_ask_no_code(msg):
    """本体拒了、但这一支没给码（真身：本地治理/认证失败那几支）。"""
    return {"id": msg.get("id"), "ok": False, "why": "前置条件不成立"}


def reply_none(msg):
    return None


def call_once(gw, codes, method, params, reply_fn, caller_id=1, timeout=2.0):
    topic = "world/query" if method == "world.query" else "world/ask"
    bus = FakeBus({topic: reply_fn})
    app = gw.App(gw.gateway_bus.WorldBus(bus), category_of=codes.get,
                 ask_timeout=timeout, query_timeout=timeout)
    body = {"jsonrpc": "2.0", "method": method, "params": params}
    if caller_id is not None:
        body["id"] = caller_id
    return app.call(json.dumps(body, ensure_ascii=False)), bus


def probe_http(gw, codes):
    """(f) 真起 HTTP（临时端口）＋ 假总线，POST 一条 JSON-RPC。"""
    bus = FakeBus({"world/query": reply_query})
    app = gw.App(gw.gateway_bus.WorldBus(bus), category_of=codes.get,
                 ask_timeout=2, query_timeout=2)
    server = gw.ThreadingHTTPServer(("127.0.0.1", 0), gw.Handler)
    server.app = app
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        port = server.server_address[1]
        body = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "world.query",
                           "params": {"kind": "overview"}}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:%d/" % port, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            got = json.loads(r.read().decode("utf-8"))
        return got, bus, None
    except Exception as e:              # noqa: BLE001
        return None, bus, "HTTP 往返失败：%s" % e
    finally:
        server.shutdown()
        server.server_close()


def read_unit_deploy():
    unit = ""
    if os.path.exists(UNIT):
        with open(UNIT, encoding="utf-8") as f:
            unit = f.read()
    deploy_src = ""
    if os.path.exists(DEPLOY):
        with open(DEPLOY, encoding="utf-8") as f:
            deploy_src = f.read()
    return unit, deploy_src


def import_gateway():
    H.utf8_stdout()
    H.add_paths("gateway", "ontology")
    import world_gateway
    return world_gateway


def load_codes():
    H.add_paths("ontology")
    from gate import world_codes
    return dict(world_codes.REJECT_CODES)


def run():
    gw = import_gateway()
    codes = load_codes()
    unit, deploy_src = read_unit_deploy()
    files, bad = [], []
    if not os.path.isdir(GATEWAY_DIR):
        bad.append("缺 src/gateway/（一进程一夹）")
    else:
        for fn in sorted(os.listdir(GATEWAY_DIR)):
            if fn.endswith(".py"):
                with open(os.path.join(GATEWAY_DIR, fn), encoding="utf-8") as f:
                    files.append(("src/gateway/" + fn, f.read()))
        if not any(n.endswith("world_gateway.py") for n, _ in files):
            bad.append("缺入口 src/gateway/world_gateway.py")
    bad += judge_source(files)
    bad += judge_shape(gw)
    bad += judge_app_codes(gw.rpc)
    bad += judge_deploy(unit, deploy_src)

    allowed = set(gw.rpc.PUT_TOPICS)
    # (1) 正常查询：原样直传、结果原样回
    env, bus = call_once(gw, codes, "world.query", QUERY_PARAMS, reply_query, caller_id=11)
    bad += judge_topics(bus.puts, allowed)
    if not bus.puts:
        bad.append("查询没有发到总线上")
    else:
        bad += judge_passthrough(QUERY_PARAMS, json.loads(bus.puts[-1][1]))
    bad += judge_echo("world.query", bus.last_reply, env, codes)
    # (2) 正常动作
    env, bus = call_once(gw, codes, "world.ask", ASK_PARAMS, reply_ask_ok, caller_id=12)
    bad += judge_topics(bus.puts, allowed)
    if bus.puts:
        bad += judge_passthrough(ASK_PARAMS, json.loads(bus.puts[-1][1]))
    bad += judge_echo("world.ask", bus.last_reply, env, codes)
    # (3) 未登记动作：本体拒 ⇒ 真码进 error.data
    env, bus = call_once(gw, codes, "world.ask",
                         {"action": "c123.no.such.action", "params": {},
                          "actor": "world://agent/dsh"}, reply_ask_unknown, caller_id=13)
    bad += judge_echo("world.ask", bus.last_reply, env, codes)
    # (3b) 本体拒了但没给码：网关不许自己补一个（★ 自造）
    env, bus = call_once(gw, codes, "world.ask",
                         {"action": "c123.x", "params": {}, "actor": "world://agent/dsh"},
                         reply_ask_no_code, caller_id=17)
    bad += judge_echo("world.ask", bus.last_reply, env, codes)
    # (4) 没有身份：网关不许自己拦（消息照样发），码是本体给的
    env, bus = call_once(gw, codes, "world.ask", {"action": "c123.x", "params": {}},
                         reply_ask_no_identity, caller_id=14)
    if not bus.puts:
        bad.append("没有 actor 的请求被网关自己拦下了（★ 该由本体拒）")
    elif "actor" in json.loads(bus.puts[-1][1]):
        bad.append("网关替调用方补了 actor（★ 不许造身份）")
    bad += judge_echo("world.ask", bus.last_reply, env, codes)
    # (5) 超时：传输错，不带世界码
    env, bus = call_once(gw, codes, "world.ask", ASK_PARAMS, reply_none, caller_id=15, timeout=0.2)
    bad += judge_echo("world.ask", None, env, codes)
    if (env or {}).get("error", {}).get("code") != gw.rpc.CODE_BUS_TIMEOUT:
        bad.append("超时没用传输码 CODE_BUS_TIMEOUT：%r" % (env,))
    # (6) 通知（没有 id）：照样发，不回话
    out, bus = call_once(gw, codes, "world.ask", ASK_PARAMS, reply_ask_ok, caller_id=None)
    if out is not None:
        bad.append("通知却回了话：%r" % (out,))
    if not bus.puts:
        bad.append("通知没有发到总线上")
    # (7) 不认识的 method：协议层拒，不许发总线
    quiet = FakeBus()
    app = gw.App(gw.gateway_bus.WorldBus(quiet), category_of=codes.get,
                 ask_timeout=1, query_timeout=1)
    env = app.call(json.dumps({"jsonrpc": "2.0", "id": 16, "method": "world.exec",
                               "params": {}}))
    if (env or {}).get("error", {}).get("code") != gw.rpc.CODE_METHOD_NOT_FOUND:
        bad.append("不认识的 method 没回 -32601：%r" % (env,))
    if quiet.puts:
        bad.append("不认识的 method 也被发上了总线")
    # (8) 真 HTTP
    got, bus, why = probe_http(gw, codes)
    if why:
        bad.append(why)
    elif got is None or got.get("error") or got.get("result", {}).get("ok") is not True:
        bad.append("HTTP 往返没回一份正常 JSON-RPC 结果：%r" % (got,))
    else:
        bad += judge_passthrough({"kind": "overview"}, json.loads(bus.puts[-1][1]))

    print("=== %s（真仓库·Python）===" % NAME)
    print("  现取：方法 %s；出向话题 %s；网关码 %d/%d/%d；最后一次假总线 put %d 次；部署行 %d 处"
          % ("／".join(sorted(gw.rpc.METHODS)), "／".join(sorted(gw.rpc.PUT_TOPICS)),
             gw.rpc.CODE_WORLD_REJECT, gw.rpc.CODE_BUS_TIMEOUT, gw.rpc.CODE_BUS_ERROR,
             len(bus.puts), len([ln for ln in deploy_src.splitlines() if "aios-gateway" in ln])))
    if bad:
        for b in bad:
            print("  [红] " + b)
        print("=== 结论：红（%d 处）===" % len(bad))
        return 1
    print("=== 结论：绿（只发 world/query＋world/ask／回话原样／码照抄／不绕过／部署齐）===")
    return 0


def self_test():
    ok = True
    if run() != 0:
        print("[自检失败] 真仓库应当是绿的，却红了")
        ok = False
    codes = load_codes()
    # 红例1：网关自造拒绝码（本体没给码，网关却写了一个不在闭集的码）
    env = {"jsonrpc": "2.0", "id": 1,
           "error": {"code": 1201, "message": "x",
                     "data": {"world_code": "GATEWAY_DENIED", "category": "system"}}}
    b1 = judge_echo("world.ask", {"id": 1, "ok": False, "why": "x"}, env, codes)
    print("=== 红例1（网关自造拒绝码）⇒ 命中 %d 处 ===" % len(b1))
    for x in b1:
        print("      " + x)
    if not b1:
        print("[自检失败] 红例1 该命中")
        ok = False
    # 红例2：本体给了码，网关把码改了／类别写错
    reply = {"id": 1, "ok": False, "why": "x", "code": "UNKNOWN_ACTION"}
    env2 = {"error": {"code": 1201, "data": {"world_code": "PERMISSION_DENIED",
                                             "category": "permission", "reply": reply}}}
    b2 = judge_echo("world.ask", reply, env2, codes)
    print("=== 红例2（世界码被改）⇒ 命中 %d 处 ===" % len(b2))
    if not b2:
        print("[自检失败] 红例2 该命中")
        ok = False
    # 红例3：绕过 world/ask 直连执行器（依赖检查）
    b3 = judge_source([("bad.py", "from gate import ask_path\nimport computer_process\n")])
    print("=== 红例3（绕过 world/ask 直连执行器）⇒ 命中 %d 处 ===" % len(b3))
    for x in b3:
        print("      " + x)
    if not b3:
        print("[自检失败] 红例3 该命中")
        ok = False
    # 红例4：网关自己往 world/exec 发（第二种出口）
    b4 = judge_source([("bad2.py", 's.put("world/exec", m)\n')])
    print("=== 红例4（自己发 world/exec）⇒ 命中 %d 处 ===" % len(b4))
    if not b4:
        print("[自检失败] 红例4 该命中")
        ok = False
    # 红例5：部署清单漏网关
    b5 = judge_deploy("", "aios-bus aios-ontology")
    print("=== 红例5（单元／部署清单漏网关）⇒ 命中 %d 处 ===" % len(b5))
    if not b5:
        print("[自检失败] 红例5 该命中")
        ok = False
    # 正控：真码照抄的电封不许红；装置齐的部署不许红
    good = {"error": {"code": 1201, "message": "不在册",
                      "data": {"world_code": "UNKNOWN_ACTION", "category": "business",
                               "reply": reply}}}
    if judge_echo("world.ask", reply, good, codes):
        print("[自检失败] 正控1（码照抄）不该红：%r" % (judge_echo("world.ask", reply, good, codes),))
        ok = False
    unit, deploy_src = read_unit_deploy()
    if judge_deploy(unit, deploy_src):
        print("[自检失败] 正控2（真单元＋真 deploy）不该红")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿（红例会红、正控不红）" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
