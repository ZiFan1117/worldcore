# 变更说明

> ## ⚠️ PR = 一次正式评审（B 档）
>
> 本仓库及任何走 GitHub PR 流程的项目**一律按 B 档要求**。
> PR 即 **R0–R8 中的对应评审**，本模板即**评审记录**。
>
> **六条必满足，缺一不可**（出处 `.refs/_料/process-source/06-swe-gb/docs/附件/附件八-责任时间与阶段分解.md` §六——
> **该件是退役料：在仓内留档、不入版本控制**，故不在 `git ls-files` 面；本仓的同类硬约定见
> `ninedim/records/openspec-流程件/schemas/README.md` §三（R5 前置闸／R4 后置闸）与
> `ninedim/02-枢纽A-前置闸/`・`ninedim/04-枢纽B-后置闸/`）：
>
> - [ ] **1. 变更说明写清「不改的后果」**——不是"优化""完善"
> - [ ] **2. 变更类型正确标注**（下方勾选）
> - [ ] **3. 追溯信息完整**（需求 / 模块 / 用例 / 缺陷 / 变更编号）
> - [ ] **4. 变更范围声明与 `.scope-declaration.json` 一致**
> - [ ] **5. R4 检查单逐项确认**（下方四组）
> - [ ] **6. 触及框架或敏感路径时，附影响分析与 R5 结论**
>
> **作者不能自己 Approve 自己的 PR**（RACI：执行者与批准者必须分离）。
> **CI 八个作业全部阻断式**（`.github/workflows/gate.yml`）——
> `smoke` / `unit-test` / `gate-self-test` / `traceability` / `scope` /
> `openspec-validate` / `spec-bridge` / `module-graph`，任一失败不予合入。
> ⚠️ 其中 `spec-bridge`（判据⑥ 归档件未签）与 `module-graph`（工具在建）今天是**如实红**：
> 已知状态的台账与处置权见 `ninedim/01-意图环/01-策划/策划-冲突总账.md` §五。
> **不得**用 `continue-on-error`、注释掉步骤、或放宽判据来换绿。

---

## 不改的后果（必填）

> **写不出"不改的后果"，这个变更就不该提。**
> 这一栏用来过滤"顺手改一下"——❌ "优化体验" / ✅ "甲方新增要求：单笔上限从 5 万调到 10 万，因业务扩展"

```
<在这里写>
```

## 变更类型

- [ ] `feat` 新功能（MINOR）
- [ ] `fix` 缺陷修复（PATCH）
- [ ] `framework` **框架变更**（必须附 R5 变更评审结论）
- [ ] `refactor` 重构（不改行为）
- [ ] `docs` 文档
- [ ] `test` 测试
- [ ] `chore` 构建/工具
- [ ] `BREAKING CHANGE` 不兼容变更（MAJOR）

## 追溯信息

| 项 | 内容 |
|---|---|
| 关联需求编号 | `REQ-F-xxx` / `REQ-N-xxx` |
| 涉及模块号 | `Mxx` |
| 关联测试用例 | `TC-xxx` / `TC-F-xxx` 等带类型前缀亦可 |
| 关联缺陷 | `BUG-xxx` |
| **变更申请编号** | `CR-xxx`（一般变更）；`FC-YYYY-NNN`（**框架变更必填**） |

> **框架变更不走 CR-**：敏感路径的**权威清单**是 `scripts/verify/scope_check.py` 的
> `SENSITIVE_PATHS`（现取 `:130-142`）：`src/ontology_definition/ontology.json`、`src/gate/policy.json`、
> `src/lib.rs`、`src/common/event.rs`、`src/ontology_definition/mod.rs`、`src/ledger/mod.rs`、
> `scripts/test/`、`scripts/`、`.github/workflows/`、`.github/PULL_REQUEST_TEMPLATE.md`、
> `ninedim/02-枢纽A-前置闸/`。触及它们一律按框架变更处理，**必须走 R5**。
> ⚠️ 旧写法里的 `skeleton/`、`docs/02-评审与门禁/`、`tests/`、`tools/`、`docs/评审/` 在本仓**不存在**
> （前三者随 2026-10-07 结构迁移改名/并位：`tests/`→`scripts/test/`、`tools/`→`scripts/`、
> `docs/评审/`→两个枢纽夹），已按上面的现取清单改正。

## 变更范围声明

本次改动**声明覆盖的路径**（供 `scripts/verify/scope_check.py` 判定是否越界）：

```
<例如：src/ledger/mod.rs, scripts/test/acceptance.rs>
```

- [ ] 改动未超出上述声明范围
- [ ] 若超出，已更新 `.scope-declaration.json` 或走变更评审批准扩展范围

---

## R4 模块评审检查单（门禁，逐项确认）

### 契约与设计
- [ ] 模块行为符合其**接口契约**（见 `ninedim/records/模板/03-设计类/03-模块接口契约.md`）
- [ ] 未新增循环依赖；分层方向正确（低层不依赖高层）
- [ ] **框架适配性回判已执行**——若不适配，已提 R5 框架变更评审
- [ ] 设计文档已同步更新（**文档与代码无漂移**）

### 测试
- [ ] 单元测试全部通过
- [ ] 覆盖率达标：行 ≥80%，核心逻辑分支 ≥90%
- [ ] 覆盖四类路径：正常 / 边界 / 异常 / 空值
- [ ] 无遗留 P0/P1 缺陷

### 追溯与配置
- [ ] 需求追溯矩阵（RTM）已更新
- [ ] 无密钥/凭据入库
- [ ] 版本号按语义化规范递增
- [ ] 若为框架变更：变更申请 + 影响分析 + 回归范围已明确

### 评审
- [ ] 至少 1 名同级开发完成代码走查
- [ ] 评审意见全部闭环

---

## 影响分析（框架变更 / 结构性改动必填）

| 项 | 内容 |
|---|---|
| 受影响模块 | |
| 受影响需求 | |
| 受影响接口/契约 | |
| 需重跑的测试范围 | |
| 回归策略（R-A/R-B/R-C/R-D） | |
| 风险与回滚方案 | |

## 备注

<!-- 其他需要评审人知道的信息 -->
