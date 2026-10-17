# ★★★★★★ **全 Python ＋ 四进程全 active ＋ 端到端跑通**（2026-10-17）

> ★ **作者令（逐字）**：「**不行，全改成 Python 版本吧。**」
> ★★★★★★ **改完了 —— 而且端到端跑通了**：★ **请求方 ⇒ 本体（认/盖章/转/记）⇒ 载体（执行）⇒ 结果 ⇒ 本体 ⇒ 请求方** ✓

---

## §一 ★★★★★★ 端到端实录（★ 现取）

**请求方**（Python，client）：
```
[请求方] 发了 fs.list（id=e2e-1）
[请求方] 收到 1 条结果
   {"id":"e2e-1","seq":4,"action":"fs.list","ok":true,"body":"total 0\n","error":null}
```

**本体日志**：
```
[本体] ★ 进程注册 surface/a2ui ⇒ 成为个体（seq=1）        ← ① 我起来了
[本体] ★ 进程注册 service/carrier ⇒ 成为个体（seq=2）     ← ① 我起来了
[本体] 转 fs.list（seq=3）⇒ system                        ← ② 认＋盖章＋转
[本体] 结果 fs.list（seq=4，ok=True）                      ← ③ 结果＋记账
```

**载体日志**：
```
[载体] 收到 fs.list（id=e2e-1）      ← 收到了
[载体] 回话 fs.list ⇒ ok=True        ← 真执行（ls -l /tmp ⇒ total 0）
```

**账本（★ 四笔，`seq` 全局单增）**：
```
seq=1 family=change kind_of=appear  subject=surface/a2ui
seq=2 family=change kind_of=appear  subject=service/carrier
seq=3 family=act    kind_of=ask     action=fs.list actor=world://user/zhang rid=e2e-1 params={"args":["-l","/tmp"]} route=system
seq=4 family=act    kind_of=result  rid=e2e-1 action=fs.list ok=true body="total 0\n"
```

★★★ **⇒ 三条路全通**：★ ① 任何人 → 本体 ✓ ② 本体 → 能做的那个 ✓ ③ 做完的 → 本体 → 请求方 ✓

---

## §二 ★★★★★ 四个进程全是 Python（★ 现取）

| ★ 进程 | ★ 语言 | ★ 文件 | ★ 行数 | ★ 状态 |
|---|---|---|---|---|
| ★ **总线** | ★ `zenohd`（★ 第三方） | — | — | ★ **active** ✓ |
| ★★ **本体** | ★★ **Python** | ★ `py/ontology_process.py` | ★ **258** | ★ **active** ✓ |
| ★★ **载体** | ★★ **Python** | ★ `py/carrier_process.py` | ★ **140** | ★ **active** ✓ |
| ★★ **GUI** | ★★ **Python** | ★ `py/gui_process.py` | ★ **92** | ★ **active** ✓ |
| ★ **渲染器** | ★ HTML ＋ JS | ★ `render/a2ui.html` ＋ `a2ui-renderer.mjs` | ★ 135 ＋ 80 | ★ 服务 200 ✓ |

★★★ **⇒ 四个进程【全部 Python】（★ 除第三方总线）** ✓

---

## §三 ★★★★★ 关键结论：**Python ＋ `client` 模式是【唯一能用的组合】**

| ★ 组合 | ★ 连得上 | ★ 跨进程发得到 |
|---|---|---|
| ★ Rust ＋ `peer`（systemd） | ✓ | ★★ **孤岛（到不了别人）** ✗ |
| ★ Rust ＋ `client`（systemd） | ★★ **连不上** ✗ | — |
| ★ Python ＋ `peer` | ✓ | ★★ **收不到** ✗ |
| ★★★ **Python ＋ `client`（systemd）** | ✓ | ★★ **���发能收** ✓ |

★★★ **⇒ 这就是为什么「全改 Python」是对的** ✓ ★ —— ★ **Rust 在这个环境里两种模式都不行** ✗

---

## §四 ★★★ 新增的三个件（★ 全 Python）

| ★ 件 | ★ 干什么 |
|---|---|
| ★★ `py/carrier_process.py`（140 行） | ★ 报机器（★ `service/carrier` running ＋ 11 条报到）＋ 收 `world/exec` ⇒ **`subprocess.run([program]+args)`** ⇒ 回结果 |
| ★★ `py/gui_process.py`（92 行） | ★ 成为个体（★ `surface/a2ui`）＋ 收 `world/ui/frame` ⇒ 落帧（`/run/aios/gui-frame.json`）⇒ 回 ack |
| ★★ `distro/systemd/aios-carrier.service`／`aios-gui.service` | ★ **改成 Python 版**（★ 不 After=／不 Wants=／不 Requires=） |

★★ **载体的执行**：★ `subprocess.run([program] + args, capture_output=True, timeout=30)` ★ —— ★ **不拼 shell，直接 `execve`** ✓
★★ **参数的权宜**：★ 映射表今天**没有参数格** ⇒ ★ **请求里带 `params.args` 就用它**（★ 端到端测的就是这条：`{"args":["-l","/tmp"]}`）✓

---

## §五 ★★★ 还差什么（★ 如实）

| # | ★ 缺 | ★ 影响 |
|---|---|---|
| **1** | ★★ **映射表没有参数格** | ★ 现在靠请求里带 `args`（★ 权宜）⇒ **参数形状还没进本体** ✗ |
| **2** | ★ **GUI 的帧从哪来** | ★ GUI 只会落帧；★ **没有东西给它发帧**（★ 投影 `project.rs` 没接）✗ |
| **3** | ★ **渲染器还没读真帧** | ★ 它读的是样例 `frame-sample.json`，★ **不是 `/run/aios/gui-frame.json`** ✗ |
| **4** | ★ **账还缺 `family=notice/job`** | ★ 现在只有 `change`（★ 进程注册）和 `act`（★ 请求/结果）✗ |
| **5** | ★ **应用/AI 进程** | ★ 没有（★ 现在用脚本当请求方）✗ |

---

## §六 ★ 本件不能证明的事（如实）

- ★ 四块 active／两条进程注册／`seq=1..4`／载体执行 `ls -l /tmp` 得 `total 0`／请求方收到结果 —— 都是**现取**（★ 本轮真跑）；
- ★★ **只测了【一条动作】**（`fs.list`）★ —— ★ **其它 10 条没测** ✗；
- ★★ **只测了【一条请求】**（★ `e2e-1`）★ —— ★ **没有并发、没有失败路径、没有超时** ✗；
- ★★ **「Python ＋ client ＋ systemd 能发能收」现在【验过了】** ✓ ★ —— ★ **但只在【这台 VM ＋ 一个 zenohd】上** ✗；
- ★★ **账本【旧的三笔还在】** ★ —— ★ 那是之前测试的残留（★ `appear-reject` 等）★ —— ★ **我没有清理** ⚠；
- ★ 本件**改了仓**（两个 Python ＋ 两个单元）⇒ ★ 要登记 ✓；★ 本仓判据 **C1–C26 全绿** ✓
