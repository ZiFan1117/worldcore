# Spec Delta

## MODIFIED Requirements

### Requirement: 读模型是可丢弃的缓存

"现在是什么样" SHALL 由账本重算得出，SHALL NOT 作为与账本并行的第二份原件存在。
删掉读模型（及其持久形态）之后 SHALL 能从账本重算出完全一致的结果。

系统 SHALL NOT 声称"账本内容损坏一律拒绝产出"这一全称命题。
已实测的拒绝面 SHALL 被逐类写明：① 序号断裂、② 旧值说谎（`change` 的 `before` 与当前值不符）、
③ 未知事件家族。
**边界 SHALL 被如实声明**：末尾半行在进入折叠**之前**就已被账本层截掉
（`src/ledger.rs:276-289`），故它**不是**读模型的拒绝面；
读模型对"解析失败的行"不承担拒绝责任。

#### Scenario: 删掉读模型后重算结果一致

- **WHEN** 记录当前读模型，删除其持久形态，再由账本重算
- **THEN** 重算结果与删除前逐项一致
- **证据**：`scripts/test/acceptance.rs::t7_read_model_is_disposable_and_reproducible`
      —— **⚠ 原证据行括注的"（`check.sh` 步骤 ③）"写法有歧义**：仓里有两个同名脚本，
      仓根 `check.sh` 完全不碰 `world-core`（`audit.md` **L8** 后半）
      ⇒ 本 change 一律写全 **`check.sh.new`** 并注明步骤号；
      本节该步确实执行 `t7`（`check.sh.new:98` 逐字
      `cargo test --locked --test acceptance -- t1_ t2_ t7_`）。

#### Scenario: 坏账本不得产出"看起来正常"的读模型

- **WHEN** 账本内容损坏（序号断裂／旧值说谎／未知事件家族）
- **THEN** 读模型拒绝产出，而不是给出部分结果
- **证据**：`scripts/test/acceptance.rs::t8_read_model_refuses_broken_ledger`
      —— **⚠ 本证据今天只覆盖上述三类**；"末尾半行"由账本层在折叠前截掉，**不属于**本拒绝面。

### Requirement: 增量折叠等价于全量折叠

系统 SHALL 保证"逐条增量应用"与"从头全量折叠"得到同一个结果，
否则读模型就成了一本会漂移的第二本账。

#### Scenario: 增量与全量结果相同

- **WHEN** 对同一批事件分别做增量应用与全量折叠
- **THEN** 两者结果相同
- **证据**：`scripts/test/contract.rs::c06_incremental_apply_equals_full_fold`（由 `check.sh.new` 第 ③b 步执行）
      —— **⚠ 本条是防线冗余的**：生产路径上缺号由账本层 `src/ledger.rs:304` 先拒，
      故本断言**不构成**端到端证明。

### Requirement: 检查点是缓存，可丢弃且必须自洽

检查点 SHALL 只作为重放的加速形态存在；它 SHALL 可被丢弃而不影响正确性；
坏检查点 SHALL 被拒绝而不是被静默采用。

系统 SHALL 明确声明"自洽"的可判定含义，SHALL NOT 留作未定义词：
检查点的**核验**判据只有两项——① 快照自称的 `base_seq` 能对上账本前若干条；
② 用账本重算前 `base_seq` 条得到的指纹等于快照自称的 `digest`。

系统 SHALL 另外声明：CLI 的 `checkpoint resume` 走的是**未核验**续算路径，
其"缓存未成为第二真相"由**事后**的"续算 ≡ 全量"逐字节比对承担
（不一致即 `ResumeMismatch` 拒用），**不是**由使用前的 `verify` 承担。

检查点格式版本不符时 SHALL 拒绝使用；该约束 SHALL 有断言。

#### Scenario: 检查点可丢弃

- **WHEN** 生成检查点后再丢弃它，由账本重新重放
- **THEN** 结果与使用检查点时一致
- **证据**：`scripts/test/contract.rs::c12_checkpoint_is_a_cache_and_disposable`

#### Scenario: 坏检查点被拒

- **WHEN** 检查点内容被破坏
- **THEN** 被拒绝
- **证据**：`scripts/test/contract.rs::c13_bad_checkpoints_are_refused`
      —— **⚠ 其覆盖面不含"格式版本不符"这一分支**（`src/checkpoint.rs:94-99`）
      ⇒ 需补断言（列进 tasks）。

## ADDED Requirements

### Requirement: 读模型是"一个真相"的检验面之一

读模型 SHALL 是可丢弃的缓存，"现在是什么样"由账本重算得出。

本能力 SHALL NOT 被表述为"一个真相"这条纪律的**唯一**自动化检验面：
同仓另有**摘要链核验**一条独立检验（`c19`/`c20`/`c21`/`cli02`）。
⚠ **投影同源核对（`t16`）不计入本能力的检验面**：它属 `projections` 能力，且**只证同源、证不了"两份记录说的是同一件事"**（书第五章判它红）——与本能力 Purpose 的 ⚠ 行同一口径。

系统 SHALL 声明检查点路径**已接入生产 CLI**（`checkpoint write|verify|resume`），
SHALL NOT 被表述为"v1 CLI 从不读快照"。

证据链的机械门禁 SHALL 声明其覆盖边界：`scripts/verify/doc_integrity.py` 的受控清单里
`**` **零命中**，故"改一个测试名，规格不会变红"。
该缺口 SHALL 由 `spec_bridge.py` 的对应检查承担，SHALL NOT 被读成"证据链已被机核"。

#### Scenario: 检查点路径已接入生产 CLI

- **WHEN** 查阅 CLI 的用法串与分发分支
- **THEN** 其中列出 `checkpoint write` / `checkpoint verify` / `checkpoint resume` 三条子命令，
      且 `checkpoint` 分支在 CLI 分发表里有对应项
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `src/main.rs:28-30` 与 `src/main.rs:153`；
      三份仍写相反陈述的受控文档为 `ninedim/03-执行环/02-实现/实现-WC-UT-001-v0.1.md:54`、
      `ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md:921`、`ninedim/01-意图环/02-需求/WC-RTM-001.csv` 第 22 行。

#### Scenario: 证据链的机械门禁不覆盖 openspec

- **WHEN** 改动 `ninedim/01-意图环/04-规格/` 下某条 Scenario 的证据行所指的测试名
- **THEN** 受控文档一致性脚本**不会变红**（`openspec` 在其受控清单里零命中）；
      该改名的**可核判据由另一件承担**——见下两行的证据行
- **证据**：`scripts/verify/spec_bridge.py`
      —— 判据②（`scripts/verify/spec_bridge.py::j2_evidence`）全称判定证据行指向的函数名是否真实存在，
      其反例在 `scripts/verify/spec_bridge.py --self-test` 的反例②（证据指向 `::no_such_fn` ⇒ 必红）；
      另一半边界由 `scripts/verify/doc_integrity.py` 的受控清单里 `openspec` 零命中承担。

### Requirement: 带检查点路径的性能目标不在本基线的承诺范围内

系统 SHALL 明确声明**范围外**事项，SHALL NOT 被读成已成立：
带检查点路径的性能目标（`REQ-N-008`：走检查点续算 ≤ 全量重算的 1/2，样本 ≥ 20 次取 P95）
在本基线内**未实现、无断言**；`scripts/test/perf.rs` 的全部用例默认 `#[ignore]`，
只在显式度量时运行。

#### Scenario: 性能目标不在本基线的承诺范围内

- **WHEN** 查阅本能力的覆盖声明
- **THEN** 写明 `REQ-N-008` 未实现、无断言，且 `scripts/test/perf.rs` 三条用例默认不跑
- **证据**：`ninedim/01-意图环/02-需求/需求-WC-SRS-001-v0.1.md:112`（状态列"未实现"）
      —— 本条**今天没有断言**（"未实现"不可被断言），其载体是流程侧登记与本 change 的 `tasks.md` 范围声明。
