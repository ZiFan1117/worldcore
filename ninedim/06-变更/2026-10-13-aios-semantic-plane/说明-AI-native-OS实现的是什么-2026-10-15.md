# 说明：**AI native OS 实现的是一个什么样的东西**（2026-10-15）

> ★ **作者问（逐字）**：「**那个 AI native OS 实现的是一个什么样的东西**」。
> ★ **一句答**：★ **它是一个「AI 原生的 Linux 发行版」** —— ★ 它自己的话：「It is a Linux distribution, **not Linux + an AI assistant bolted on**」；★ **内核照旧是 Linux（执行底座）**，★ 特色层是 **认知核 ＋ 策略核 ＋ 只追加的证据日志**。
> ★ 本件**全部现取**：上游 README（`git show babedc9e:README.md`）＋ 本地全史 `D:\Code\_refs\AI-Native-Linux`（**36 个 crate**）＋ `MILESTONES.md`。

---

## §一 它自己怎么说（README 逐字）

> 「AI-Native Linux (AIOS) is an open specification for an **AI-native Linux distribution** — a real Linux distro whose distinguishing layer is **a cognitive core, a policy kernel, and an evidence log** built on top of the standard Linux substrate.」
>
> 「**Humans express goals, the system translates those goals into typed actions, the policy kernel decides what is allowed, runtime adapters execute only approved operations, and verification produces append-only evidence.** ★ **Linux remains the trusted execution substrate**（kernel, drivers, scheduler, syscalls）。」
>
> 「**Modern operating systems still treat users as command dispatchers.** AI assistants can understand intent, but most current integrations **collapse back into unsafe shell execution or isolated chat interfaces.**」

★ 它给的**五条主张**（逐字）：

1. ★ **AI plans, but does not directly run arbitrary shell commands**；
2. ★ **System actions are typed, policy-checked, executed by capability runtimes, and verified**；
3. ★ **Evidence logs make system changes auditable and reproducible**；
4. ★ **Linux remains the trusted execution substrate**；
5. ★★ **KDE, Web, CLI, voice, and mobile become renderers over the same cognitive core**。

---

## §二 它的骨架：**11 层 ＋ 一整套发行版件**

| 层 | 是什么（README 的发行版映射） |
|---|---|
| **L0** | ★ 治理／证据／安全（**24 条宪法不变式**在这） |
| **L1** | ★ **引导 ＋ 恢复**（★ 回退内核、**无 LLM 也能恢复**） |
| **L2** | ★ **AIOS-FS**：`/aios` 语义对象存储 ＋ 恢复安全的 `/` 与 `/root` |
| **L3** | ★ **SGR** 服务图运行时（服务／包管理） |
| **L4** | ★ **策略／身份／金库**（S2.3 策略核） |
| **L5** | ★ **认知核**（意图 → 翻译 → 类型化动作） |
| **L6** | ★ 应用／包／兼容（沙箱组成） |
| **L7** | ★ **渲染器**：★ **KDE Plasma ＋ Qt/QML 为默认桌面**；★ **Web／CLI／语音／移动为兄弟** |
| **L8** | ★ 网络／硬件／设备 |
| **L9** | ★ **证据日志 ＋ 验证文法**（427 种记录类型／32 个验证属性） |
| **L10** | ★ 发行／集成（仓库模型、信任链、**签名包安装**） |
| **XX** | ★ 横切（`aios-action` 的信封） |

★ `distro/` 里**真的在做发行版的件**（现取）：★ `aios-boot`／`installer`／`repo`／`secureboot`／`systemd`／`first-boot`／`update`／`desktop`／`security`／`compliance`／`cloud`／`build`。

---

## §三 它的规模与成熟度（★ 现取，别凭印象）

| 项 | 现取 |
|---|---|
| **规格** | ★ **11 层／52 份子规格／24 条不变式／427 种记录类型（闭枚举）／32 个验证属性／70 份 md ／ 52,000+ 行** |
| **代码** | ★★ **36 个 crate ／ 约 224,100 行 `.rs`** |
| **最大的几件** | ★ `aios-capability-runtime` 37,129 行｜`aios-evidence` 14,606 行｜`aios-fleet` 13,903 行｜`aios-apps` 12,546 行｜`aios-distribution` 11,955 行 |
| ★ **里程碑** | ★★ **19/19 全关 ＋ M20 清尾**；★ 徽标逐字「**Rev.2 implemented · 19 crates**」 |
| ★ **测试** | ★★ 逐字「**19 crates, 4475 workspace tests (0 failed), all four cargo gates green**」；★ 状态标 **FULL-REAL** |
| ★ **还没做的** | ★ 逐字：★ 剩的是**产品化** ——「**bootable ISO, CI, production StateProbe adapters**」 |

---

## §四 ★★ 它跟我们是什么关系（这条最要紧）

| # | 关系 | 依据 |
|---|---|---|
| **1** | ★★ **它是我们这个仓的上游** | ★ `13-aios-worldcore` fork 自它；★ 本地全史 `D:\Code\_refs\AI-Native-Linux`（451 提交）；★ 我们的 `crates/` 就是它那 36 个 crate |
| **2** | ★★★ **它已经把「一个认知核、多个渲染器」写成主张** | ★ 逐字第 5 条：★「**KDE, Web, CLI, voice, and mobile become renderers over the same cognitive core**」⇒ ★★ **这跟我们要做的事正面撞上** |
| **3** | ★★★ **但它缺「语义那一层」** | ★ 它链路里那一步叫「**translates those goals into typed actions**」—— ★ 而「**哪些动作算数**」它**没有权威来源**：★ 动作名是**提示词里的自由字符串**；★ 上一会话实测：`TBox`／`ABox`／`ontology`／`RDF`／`OWL` **全 0**；★ 它自己的 `L7.2` 写着「This spec is purely structural」 |
| **4** | ★★★ **两句话的分工** | ★★ **它是「把 AI 装进操作系统」；★ 我们做的是「把世界装进操作系统」**（同盒 `说明-本体空间的意义与相对AIOS的位置.md` 的口径） |

---

## §五 ★ 诚实的对比（不许含糊）

| | AI native OS | ★ 我们（今天） |
|---|---|---|
| 规模 | ★ **36 crate ／ 224,100 行** | ★ `crates/aios-worldcore` **36 件 ／ 6,569 行**（我们自己那一块） |
| 测试 | ★ **4,475 个，0 失败**（它自述） | ★ 我方 `verify/check.py` **C1–C13 绿**；★ VM 上 `aios-worldcore` **115 passed** |
| 产品成熟度 | ★ **19／19 里程碑 ＋ 发行版件齐全**；★ 剩 ISO／CI | ★ **只有一条 VM 上的闭环**（点按钮 ⇒ 过本体 ⇒ 受理；★ 且「执行」是**一行打印**） |
| 语义权威 | ★★ **没有这一层** | ★★ **有这一层，但极小**（9 类 ／ 9 动作） |

⇒ ★★★ **结论**：★ **它不是要取代的东西，是我们要补那一格的那个系统** —— ★ 而且**它自己把那一格的位置留出来了**（认知核 ＋ 渲染器那张图）。

---

## §六 本件不能证明的事（如实）

- ★ **我没跑上游任何测试** —— ★ 「4,475 个测试 0 失败」是**它 README／MILESTONES 的自述**（`git show babedc9e:` 取到）；★ 我**只数了 crate 与行数**（现取），★ **没编译**；
- ★ **`MILESTONES.md` 只读了前 24 行** 与状态快照，★ 其余 19 个里程碑的逐条明细**未读**；
- ★ 「它缺语义那一层」引的是**上一会话的实测件**（同盒 `说明-本体空间…md`），★ **本件没重跑**那些实测；
- ★ **52 份子规格我一份都没读**（★ 只读了 README ＋ crate 的 `description` ＋ 里程碑头部）；
- ★ 本件**没改代码、没跑构建**。
