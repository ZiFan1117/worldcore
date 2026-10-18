# 旧代码（★ 归档在这里，不参与运行）

★★ 作者令（逐字，2026-10-18）：「这些代码，这于旧代码该清理的先清理了，或者是统一放到一个地方，而且没啥用了」

## 这里面是什么

| 件 | 原来在哪 | 为什么挪过来 |
|---|---|---|
| `ledger_process.py` | `src/legacy/` | 旧账本进程 —— 账本已进本体（`ontology_process.py` 的 stamp）。 |
| `agent_process.py` | `src/agent/` | ★ 旧 agent（★ 只「试验一下」的那版）—— 已被 `agent_llm.py`（真 agent，模型在环）替代。 |
| `world_cli.py` | `src/agent/` | 命令行调试工具 —— 不在跑。 |
| `polkit_gen.py` | `src/ontology/` | 生成 polkit 条文 —— ★ **现取：全仓无人引用**，没接上。 |

★ **`gui_process.py` 【已删】**（★ 作者令：「aios-gui 删除」）—— ★ 它报 `surface` 类被本体拒，★ 功能并由 `src/presentation/` 接管。

## 规矩

★ **本目录的 .py 【不进 `distro/deploy.sh` 的部署清单】**，★ 也不被任何 systemd 单元引用。
★ 要复活某一个，★ 就把它**挪回**对应目录 ＋ 加单元 ＋ 登记进 C1。
