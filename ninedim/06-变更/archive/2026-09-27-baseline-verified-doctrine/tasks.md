# Tasks

## 1. 规格文本

- [x] 1.1 `ledger-integrity`：一本账 / 单写者 / 残尾与空洞 / 行边界 / 摘要链（含边界声明）/ 回滚即补偿
- [x] 1.2 `envelope-validation`：8 个必填字段逐字段 / 三类之外被拒 / 法律损坏与软链拒启 / id 唯一 / 行边界 / 错误码
- [x] 1.3 `gate-enforcement`：每个写动作过闸 / `change` 不能偷渡 `act` / 不可逆加摩擦 / 不可写域 / 运行期不重读策略
- [x] 1.4 `read-model`：可丢弃缓存 / 增量等于全量 / 检查点是缓存且坏检查点被拒
- [x] 1.5 `projections`：两份读法同源 / 投影与读模型逐项相等 / 排版是可审计契约
- [x] 1.6 `channel-identity`：身份取自内核

## 2. 规格自检

- [x] 2.1 `openspec validate baseline-verified-doctrine --strict` 通过 → `Change 'baseline-verified-doctrine' is valid`
- [x] 2.2 逐条核对：每条 Requirement 至少一个 Scenario；每个 Scenario 恰好 4 个 `#`（由 validate 强制）
- [x] 2.3 逐条核对：每条 Scenario 的 `证据：` 行指向真实存在的测试名
      → 脚本核对结果：**6 份规格 / 40 条证据 / 0 条未命中**（对照 `tests/` 里 72 个测试函数与 `tools/` 下 17 个脚本）

## 3. 证据复核（在 VM 内实跑，不以文档自述为据）

- [x] 3.1 `bash check.sh` 跑通 → **退出码 0，耗时 3 秒**
- [x] 3.2 逐条把 `证据：` 行的测试名在 `tests/` 里检索确认存在（见 2.3）
- [x] 3.3 抽样单跑取证：`check.sh` 步骤 ③ 输出 `test result: ok. 3 passed; 0 failed`；
      步骤 ③b 输出 `test result: ok. 25 passed; 0 failed`
- [x] 3.4 环境指纹（2026-09-27T21:31:56+08:00 采集）

      | 项 | 值 |
      |---|---|
      | VM 内核 | `Linux 7.2.6-arch2-1` |
      | cargo / rustc | `1.98.1 (797e8a9bc 2026-08-05)` / `1.98.1 (48a229cea 2026-09-01)` |
      | nproc | 8 |
      | VM HEAD | `cb5ae648e9bb064079e1991832b2c4f1ed23014e`（工作树 4 个脏文件，已核实与主机副本逐字节相同） |
      | 产品文件 sha256(16) | `main.rs d68d2e8514065430` / `ledger.rs 30b26dd660baa829` / `gate.rs 86603fb333694223` / `readmodel.rs e27a1d1e880046f6` / `ontology.json ff4286ae115f05c5` / `policy.json f1049640b36ea9ee` / `check.sh 2e6721bfb9ae3dad` / `Cargo.toml 83245568dcbfac59` |
      | 门禁结论 | `== 结论：全通过（构建 / 冒烟 / 三条专属测试 / 契约测试 / 投影同源 / 纯文本审计 / 系统级验收 / S1 验证面补建）==` |
      | 投影同源 | `同源 : ✅ 语言投影与视觉投影一致（同一读模型 + 同一词表）`；词表 `fnv1a64:4bf7b75573fee475`（世界版本 1） |
      | 另行登记（现状为红，如实记录） | 系统级验收 4 项 + S1 验证面 2 项 = **6 项**，均非本基线主张 |

## 4. 排除清单的对账

- [x] 4.1 核对 `design.md` 排除清单的 7 项，逐项在规格里检索确认确实没有写进 Requirement
      → 脚本对账通过（首轮命中 1 处系误报：命中的是测试函数名 `t10_gate_adds_friction_for_irreversible_capability`，
      而"不可逆等级"是 `管` 的正当内容，不在排除之列；收紧关键词后 0 命中）
- [x] 4.2 在 `proposal.md` 与 `design.md` 里确认：未把本基线表述为"必要性已证"
      → 规格文件里检索 `必要性|必须存在|应当存在` 命中 0 处

## 5. 归档

- [x] 5.1 归档本 change，使 6 份 delta 合并为 `ninedim/01-意图环/04-规格/` 下的主规格
      → 首次归档时 delta 已正确合并（重跑时 CLI 自报 `Specs already in sync; no files changed`），
      但"移入 `archive/`"这一步被一个**陈旧归档锁**挡住了
      （`ninedim/06-变更/archive/.openspec-archive.lock` 里的 pid 14792 早已不存在）。
      删锁重跑后归档完成：`archived as '2026-09-27-baseline-verified-doctrine'`。
- [x] 5.2 归档后跑 `openspec list --specs` 确认 6 条能力在册
      → `channel-identity 1 / envelope-validation 5 / gate-enforcement 5 / ledger-integrity 6 / projections 3 / read-model 3`
- [x] 5.3 提交（`git commit`），提交信息写明基线源自 `61c95b0` 与 VM 实跑结论
      → `ef2c9a0`（规格基线本体）；归档收口另计一次提交

## 6. 基线之后的维护（**已于 2026-09-27 移出本件**）

> **本节两条常设维护项已移出**，落点：`ninedim/records/openspec-流程件/openspec-MAINTENANCE.md` §一 第 1、2 项。
> **移出理由**：`tasks.md` 的归档门禁要求**全勾**，而常设项天生做不完 ⇒ 它们让
> `openspec validate --archived` **永久为红**（实测 `✗ 2 incomplete tasks (18/20 completed)`）。
> 融合档 `schema.yaml:121-123` 逐字预言过这个形态：「若某条本来就做不完（常设维护项），不要留在本件里……
> 它会永久挡住 `openspec validate --archived`；常设项写进项目自己的维护清单。」
>
> **移出前的原文逐字留痕**（不是静默删除）：
> - `- [ ] 6.1 测试改名或 \`check.sh\` 步骤号变动时，同步修订对应 \`证据：\` 行`
> - `- [ ] 6.2 VM 离线期间禁止声称基线已复验`
>
> **移出人**：AI（DeepSeek Harness）｜**依据**：`fc-2026-001-openspec-into-cm` 的 task 4.2｜**时点**：2026-09-27

