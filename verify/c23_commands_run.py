#!/usr/bin/env python3
"""C23 —— **命令真的接进来了、并且真的能跑**（T-245 贯通）。

★ 作者令（逐字）：「我们要实现的就是底下的传统的一些命令行的这些命令全部能够接进来，
  而接进来的方式就是……把它底下的这些工具，然后注册为我们的 action」。

红＝
  (a) registry.rs 里没有 load_with_registration（在册表 ＝ 本体 ＋ 注册表，合不起来）⇒ 红；
  (b) execute.rs 里没有 CommandRunner（没有真跑命令的执行体）⇒ 红；
  (c) CommandRunner 里不是 Command::new(program).args(...)（★ 那就可能在拼 shell）⇒ 红；
  (d) ★★ src 下出现「给语言」的写法（sh -c ／ bash -c）⇒ 红
      —— ★ 那是外部先例那条「别把危险的语言给它」；本仓一律 program+args；
  (e) registration.rs 里没有 kinds_present（三方同构的读数取不到）⇒ 红。

限度（★ 如实）：判文本 ⇒ 行为要靠 VM 的 cargo test。

用法：
  python verify/c23_commands_run.py              跑真仓库
  python verify/c23_commands_run.py --self-test   反例自检
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WS = os.path.join("crates", "aios-worldcore", "src")
REG = os.path.join(WS, "core", "registry.rs")
EXEC = os.path.join(WS, "engine", "execute.rs")
REGI = os.path.join(WS, "core", "registration.rs")
NAME = "C23 命令真的接进来了、真的能跑"


def walk(root):
    out = []
    for base, _d, files in os.walk(root):
        for f in files:
            if f.endswith(".rs"):
                out.append(os.path.join(base, f))
    return out


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def scan(reg_text, exec_text, regi_text, all_texts):
    bad = []
    if "pub fn load_with_registration(" not in reg_text:
        bad.append("registry.rs：没有 load_with_registration（在册表合不起来）")
    if "pub struct CommandRunner" not in exec_text:
        bad.append("execute.rs：没有 CommandRunner（没有真跑命令的执行体）")
    elif ("Command::new(" not in exec_text) or (".args(" not in exec_text):
        bad.append("execute.rs：CommandRunner 不是 Command::new(program).args(...)（可能在拼 shell）")
    if "pub fn kinds_present(" not in regi_text:
        bad.append("registration.rs：没有 kinds_present（三方同构的读数取不到）")
    for p, text in all_texts:
        # ① 拼成字符串那种
        for m in re.finditer(r"(sh|bash|cmd)\s+-\s*c", text):
            bad.append("%s：出现【给语言】的写法（%s）—— 本仓一律 program+args" % (p, m.group(0)))
        # ② 真实写法：Command::new("bash").arg("-c")
        if re.search(r"Command::new\(\s*\"(sh|bash|cmd)\"", text) and re.search(r"arg\(\s*\"[-/]c\"", text):
            bad.append("%s：起了 shell 并给它 -c —— 本仓一律 program+args" % p)
    return bad


def run(label="真仓库"):
    all_texts = [(p, read(p)) for p in walk(WS)]
    bad = scan(read(REG), read(EXEC), read(REGI), all_texts)
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
    good_exec = "pub struct CommandRunner {}\nCommand::new(p)\n.args(a)"
    b1 = scan("x", "pub struct CommandRunner {}", "pub fn kinds_present(&self)", [])
    print("=== 红例1（执行器不按 program+args）⇒ 命中 %d 处 ===" % len(b1))
    if not any("args" in x for x in b1):
        print("[自检失败] 红例1 该命中")
        ok = False
    b2 = scan("pub fn load_with_registration(", good_exec, "pub fn kinds_present(", [("a.rs", 'Command::new("bash").arg("-c")')])
    print("=== 红例2（出现 bash -c）⇒ 命中 %d 处 ===" % len(b2))
    if not any(("给语言" in x) or ("shell" in x) for x in b2):
        print("[自检失败] 红例2 该命中")
        ok = False
    print("=== 自检结论：%s ===" % ("全绿" if ok else "有失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
