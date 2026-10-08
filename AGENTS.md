# AGENTS.md

## 开工前必读

1. 先读仓根 `README.md`（东西在哪）与 `ninedim/01-意图环/03-设计/设计-落位契约.md`（东西该住哪）。
2. 一条规矩的权威文本在 **NineDim 标准**里；**这里只引不复述**（标准的《工程域的结构与命名》见 `ninedim/_索引-工程域结构与命名.md`）。
3. 改任何东西之前，先跑 `bash check.sh` 拿到基线读数。⚠️ **本机（Windows）无 `cargo`、无 `bash`** ⇒ 这一步只能在 Linux／VM 侧跑；宿主侧能跑的是 `scripts/verify/*.py` 里那几个纯 Python 判据（本机 `python3` 是 WindowsApps 别名，**rc=9009**，要用 `D:\package\venv\Scripts\python.exe`）。

## 硬约束（本仓）

| # | 约束 |
|---|---|
| 1 | 一个原子一个夹：`src/<原子>/` 只放实现、单元测试、数据边车（本仓 `src/` 下 **9 个夹原子**；**名单与口径的唯一出处是 `ninedim/config.json` 的 `atoms`**，本句不复述名单） |
| 2 | 承诺写进 `ninedim/01-意图环/04-规格/<能力>.spec.md`（需求＋场景＋证据行），实现写进 `src/` |
| 3 | 正文（`README.md`、`ninedim/01-意图环/`、`ninedim/**/规格`）里不许写过程；过程进 `ninedim/06-变更/<变更号>/`，记录进 `ninedim/records/` |
| 4 | 改完同批更新 `CHANGELOG.md` 与 `ninedim/06-变更/<变更号>/` |
| 5 | 生成物（`ninedim/records/生成物/`）只改输入、重跑生成器，不许手编 |
| 6 | 正式结论与签字只有人能下；智能体只出发现清单 |
| 7 | 提交前跑 `check.sh`；**红了不许绕过**（禁改判据强度换绿） |
| 8 | 判据脚本放 `scripts/verify/`，可执行脚本按用途放 `scripts/` 对应子目录；工程域（`ninedim/`）**只装档案**，不许放脚本 |
| 9 | 加判据时**先写会红的反例**，再写判据本身 |

## 本仓专属（与标准不同之处，逐条写明）

- 产品是 **Rust**（crate 在仓根：`Cargo.toml` ＋ `src/`）；单测随实现在 `src/<原子>/`，**集成测试在 `scripts/test/`**（cargo 需 `[[test]] path=` 显式指路，故 `check.sh` 不许删、不许改名）。
- 判据件数**不写死**（写死的数必然过期，且"40 件"从来没有口径）：**以命令现取为准**——`Get-ChildItem scripts/verify -File`；入口 `check.sh` 跑 22 步（步数以脚本自己打印的 `STEPS` 现算为准）；判据自带 `--self-test`（**不会红的判据只配当返工项**）。
- 料（上游源码快照／标准料库／退役料）不属九维九项：统一住 `.refs/`，**不入版本控制**。
