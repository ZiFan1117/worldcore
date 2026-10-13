# 13-aios-worldcore

> **worldcore 语义面 ＋ AIOS 底座**（AI-Native Linux）。
> 上游：`ai-os-dot-net/AI-Native-Linux`（**Apache-2.0**）；本仓自 `babedc9e` 起，**两阶段口径**见 `AGENTS.md` §三-5。

## 东西在哪

| 想知道 | 读 |
|---|---|
| ★ **接手规矩（先读这个）** | `AGENTS.md` |
| ★ **在办的唯一登记面** | `ninedim/06-变更/2026-10-13-aios-semantic-plane/`（提案／任务／评审／改动对照／原子登记） |
| 东西在哪 ／ 该住哪 | `ninedim/_索引.md` ／ `ninedim/01-意图环/03-设计/设计-落位契约.md` |
| 上游是什么、原来怎么写的 | `git show babedc9e:CLAUDE.md`（上游说明书）＋ `upstream/main`（**451 提交全史**） |
| 上游的规格 | `001.AI-OS.NET--SPECREV.1/`（冻结）／`002.AI-OS.NET--SPECREV.2/`（现行）／`003.AI-OS.NET--SPECREV.3/` |
| 上游的发行链 | `distro/`（ISO／装机／首启／云镜像／8 道企业门） |

## 怎么跑

```bash
python verify/check.py              # 我方判据（C1–C4，宿主侧可跑）
python verify/check.py --self-test  # 各自的反例自检
```

★ **上游那四道 cargo 门只能在 VM 上跑**（宿主无 cargo）：
```bash
ssh -i D:\vm\keys\vm_ed25519 -p 2223 root@127.0.0.1
cd /root/aios && cargo check --workspace && cargo test --workspace
```
★ **已知缺口**：`/root/aios` **不是 git 仓** ⇒ 跑通**不证明**那棵树等于本仓 HEAD。

## 现在到哪了（2026-10-13）

| 项 | 状态 |
|---|---|
| **已接** | 翻译链的**动作名闸**：未登记 ⇒ 拒（`crates/aios-cognitive` ＋ 我方 `crates/aios-ontology`；VM 上 4 用例绿） |
| **判据** | `verify/` 四条（C1 上游一致性／C2 工程域只装档案／C3 未登记动作名即拒／C4 行尾一致性） |
| **未接** | 参数级校验／证据进链／**策略规则真生效**／沙箱六源／**两套词表合流** —— 见盒里 `任务.md` |
| **还没做** | 13 自有门禁接唯一入口；承诺面随迁收尾（`00-纲领/`、`CHANGELOG.md`） |

## 上游与本仓的关系（三条硬话）

1. ★ **我们永不推给上游**（`upstream` 的 push 已设为 `no_push`）；
2. ★ **改上游代码要逐笔登记**（`verify/allowed_upstream_edits.txt`；判据 C1 盯着）；
3. ★ **阶段二**要把上游代码**重梳理成我们自己的**（见 `AGENTS.md` §三-5）。
