# `` · 目录分工

> **一句话**：这里是**承诺与流程**的家；`` 是**实现与判据**的家。
> 本页把"哪样东西放哪"写成口径——**新件按此落，别往别处塞**。

## 一、四条线（源 ／ 生成物 ／ 生成器 ／ 工作区）

| 线 | 在哪 | 是什么 | 规矩 |
|---|---|---|---|
| **源①：承诺** | `specs/` | 49 条 Requirement（10 个能力域），**对外承诺的唯一权威** | 改它＝改对外承诺；每条要能指到会红的测试（`scripts/verify/spec_bridge.py` ②） |
| **源②：在飞变更** | `changes/`（＋ `changes/archive/`） | 未归档的 change（proposal／design／tasks／spec delta）与已归档的历史 | 归档件**不改写**；`archive/` 是历史，只读 |
| **生成物** | **`generated/`** | `BRIDGE.md`（编号桥）・`specmap.json`（规格对照图）・`节对齐.md`（书 41 节对齐图） | **不许手编**；由 ⑪⑫⑬ 判"是否等于生成器当前输出"；改源⇒重跑生成器 |
| **生成器** | **`gen/`** | `gen_bridge_md.py`・`gen_specmap.py`・`gen_secmap.py`・`collect_evidence.py`・`audit_checked_refs.py` | 只读源、写 `generated/`；**与 `scripts/` 不是一回事**（那是判据） |
| **工作区** | **`work/`** | 草稿与过程件（工区-*、待人裁三格-备料、06-swe-gb 废止与三者融合收敛） | 不是契约；定案后并入正式件或退场 |
| **流程配置** | `schemas/`・`config.yaml`・`MAINTENANCE.md` | OpenSpec 的 schema／默认档／规格层维护清单 | `config.yaml` 的 `schema` 必须为 `opsx-swe-gb-atom`（判据③） |

## 二、书与对照表在哪（**不在本夹**）

书的正件与"书↔仓"的对照表已合并到 **`ninedim/01-意图环/01-策划/`**：
正件＝`语义世界-理论书-第一版-合订.md`；对照表＝`落点/`＋`尺子-理念条目.md`＋`冲突总账.md`。
**书的 41 节对齐图**（机生）在 `generated/节对齐.md`。

## 三、上游过程料（**仓内留档，不入库**）

原 `process-source/`（06-swe-gb 那套国标/国际标准流程料，48 件／1.1 MB）现在放在 **`refs/refs/_料/process-source/`**：
**在仓内**（作者 2026-10-07 裁定：「我们所有内容都放在自己的 08 这个仓里」），但按本仓既有规矩**不入版本控制**
（`.gitignore` 的 `refs/refs/_料/`）——其中 `00-标准依据/29110原文提取.md` 一类有**版权／密级**，本仓两个远端都是 PUBLIC。
**它是料，不是本项目的过程证据**；**只读、不改写**；引用就按 `refs/refs/_料/process-source/…` 写。

## 四、与 `` 的三条边（**别混**）

| 谁 | 判什么 | 例 |
|---|---|---|
| `src/**` | 世界的**实现**（Rust） | 本体／账本／读模型／门禁／总线／载体／投影 |
| `scripts/**` | **判据**（门禁）：查结构、依赖、证据、契约 | `module_graph.py`・`spec_bridge.py`・`carrier_contract.py`・`scope_check.py` |
| `scripts/gen/**` | **生成器**：把承诺与书索引派生成可核对的件 | `gen_bridge_md.py`・`gen_secmap.py` |

**缝在一起的判据**：`spec_bridge.py` **②**（规格的证据行必须指到真实存在的函数/脚本）把 `specs/` 钉到 `src|tests`；
**⑪⑫⑬**（生成物 ＝ 生成器当前输出）把 `gen/` 钉到 `generated/`。

## 五、怎么跑（现取口吻）

```bash
# 重生成三件（改过 specs/ 或书/对照表之后）
python scripts/gen/gen_specmap.py     # → generated/specmap.json
python scripts/gen/gen_bridge_md.py   # → generated/BRIDGE.md
python scripts/gen/gen_secmap.py      # → generated/节对齐.md
# 判它们是否同步（外加每条的会红性）
python scripts/verify/spec_bridge.py
python scripts/verify/spec_bridge.py --self-test
```
