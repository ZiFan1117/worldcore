# 裁决：**抄 sysknife 的 178 个动作（Python 实现）；风险分级归本体**（2026-10-17）

> ★ 作者裁决（逐字）：「这个，**风险分级不能自动批。这个东西是本体里头批不批，和我们没关系**，我们他这不是有 **176 个**吗？那**我们全部做成 A（action）**，**并且它的代码实现我们也可以抄一下，但是我们用 Python 实现就可以了**」

---

## §一 ★★★★★ 三条裁决

| # | ★ 裁决 |
|---|---|
| **1** | ★★ **「风险分级/自动批」归【本体】—— ★ 不抄 sysknife 的 `MaxRisk`** ✗ |
| **2** | ★★★ **它的 178 个动作【全部做成 action】** ✓ |
| **3** | ★★ **代码实现【抄它的】，★ 但用【Python】重写** ✓ |

★★★ **⇒ 第 1 条的意思**：★ **「批不批」是【世界的事】—— ★ 由本体的 `permissions` ＋ 人确认来决定**，★ **不是【动作自带的风险等级】** ✓

---

## §二 ★★★★★ 已落：178 个动作名（★ 现取）

★ **拉包过程（★ 全部在 VM 上做成）**：
| ★ 步 | ★ 现取 |
|---|---|
| ★ GitHub clone | ★ **失败**（`Connection reset by peer`）✗ |
| ★ Tsinghua crates 镜像 | ★ **失败**（153 字节，★ 是错误页）✗ |
| ★★ **static.crates.io** | ★★ **成功** ✓ |
| ★ `sysknife-cli-0.16.0.crate` | ★ **150,120 字节** ✓ |
| ★ `sysknife-brain-0.16.0.crate` | ★ **172,902 字节** ✓ |
| ★ `sysknife-daemon-0.16.0.crate` | ★ **411,536 字节** ✓ |
| ★★ `sysknife-types-0.16.0.crate` | ★ **17,267 字节** ✓ ★ ← **动作名在这** |

★ **权威清单的位置（★ 逐字）**：
```
sysknife-types-0.16.0/src/lib.rs:88:  pub const KNOWN_ACTION_NAMES: &[&str] = &[ ... ]
```

★★ **落盘**：★ `distro/carrier/sysknife-actions.json`（★ **178 条**，★ 名字 ＋ 来源 ＋ `status: pending`）✓

---

## §三 ★★★★★ 它的架构（★ 现取，全抄的依据）

| ★ 件 | ★ 现取 |
|---|---|
| ★★ **`sysknife-daemon/src/actions/`** | ★ **42 个文件**（每个一个动作域） |
| ★★ **`sysknife-types` 的 `KNOWN_ACTION_NAMES`** | ★★ **178 个动作名，PascalCase** |
| ★★ **`sysknife-types` 的 `ActionName` 类型** | ★★ **只认清单里的名字**（★ 拿不到就发不出请求） |
| ★ **`sysknife-brain/planning_tools/`** | ★ **5 个工具**（`get_state`／`propose_plan`／`query_tools`／`preferences`／`refuse`） |
| ★ **`sysknife-cli` 的 `Command`** | ★ **6 个**（`Doctor`／`History`／`Approve`／`Completions`／`McpServer`／`Audit`／`Intent`） |

★ **42 个动作域（★ 逐字）**：
```
apparmor apt apt_preferences auditd certbot cloudinit containers deployment
distrobox fail2ban filesystem flatpak grub identity journald layering
livepatch logging lvm mod mounts multipass netplan network package_repos
pam ppa processes reboot release_upgrade resolvectl services snap ssh
sudoers sysctl system_info toolbox ubuntu_pro ufw users validate
```

★ **178 个的分类（★ 我粗计）**：
| ★ 类 | ★ 数量 |
|---|---|
| ★ `Apt*`（★ 包管理） | ★ 13 |
| ★ `Snap*`／`Flatpak*` | ★ 23 |
| ★ `Get*`（★ 只读） | ★ 30 |
| ★ `List*` | ★ 12 |
| ★ `Set*`／`Configure*` | ★ 19 |
| ★ `*Service*` | ★ 12 |
| ★ Container／Toolbox／Distrobox | ★ 12 |
| ★ 用户／身份 | ★ 19 |
| ★ 网络／防火墙 | ★ 20 |
| ★ 存储／LVM | ★ 10 |
| ★ 内核／GRUB | ★ 6 |

---

## §四 ★★★ 抄它的三条【要抄的】

| # | ★ 它怎么做的 | ★ 逐字／现取 |
|---|---|---|
| **1** | ★★★ **动作名【只有一处权威】** ＋ `ActionName` 类型 | ★ 「`ActionName::parse` … `KNOWN_ACTION_NAMES.contains`」 ★ —— ★ **类型保证** ✓ |
| **2** | ★★★ **「不许跑 shell」是【测出来的】** | ★ `assert_eq!(err.0, "RunShellCommand")` ★ —— ★ **反例在测试里** ✓ |
| **3** | ★★ **每个动作一个文件**（`actions/<域>.rs`） | ★ 42 个文件 ✓ |

---

## §五 ★★★ 要做的（★ 按裁决）

| # | ★ 做什么 | ★ 规模 |
|---|---|---|
| **1** | ★★ **178 个动作写进本体 `actions`** | ★ 每个要：★ 名字／参数／映射表／许可 |
| **2** | ★★ **映射表 `command-map.jsonl` 加 178 行** | ★ 动作 → `program` ＋ `args` |
| **3** | ★★★ **每条的 Python 实现** | ★★ **`subprocess.run`** ★ —— ★ 但★ **178 个，★ 巨大** ⚠ |
| **4** | ★ **许可条文 178 条** | ★ 谁能做 |

★★ **而★ 命名口径要定**：★ 它用 `PascalCase`（`AptInstall`），★ 我们用 `点分层`（`fs.list`）⚠
| ★ 选项 | ★ 例子 |
|---|---|
| **A** ★ 照抄 PascalCase | ★ `AptInstall` |
| **B** ★ 转成点分层 | ★ `pkg.apt.install` |

---

## §六 ★ 本件不能证明的事（如实）

- ★ 178 个名字／42 个域／`KNOWN_ACTION_NAMES` 的行号／四个包的字节数／三组镜像的成败 —— 都是**现取**（★ VM 上真拉真读）；
- ★★ **「178」不是 176** ★ —— ★ 我从 `KNOWN_ACTION_NAMES` 数出 **178**（★ 作者说 176，★ 可能他记的是别的版本）⚠；
- ★★★ **它的 Python 实现【一行都没写】** ✗ ★ —— ★ 而且**我【没读】它任何一个 `actions/*.rs` 的实现内容** ⚠；
- ★★ **命名口径（★ PascalCase vs 点分层）【没定】** ⚠；
- ★★ **LACS 协议规范【没拿到】** ✗；
- ★ **本件改了仓**（新增 `distro/carrier/sysknife-actions.json`）⇒ ★ 要登记 ✓；★ 判据要重跑 ⚠
