# Spec Delta

## Purpose

规定"规格这一层自己对外承诺什么"：一个 change 的产物链必须完整、归档必须有闸、每条证据必须指向真实存在的测试、每条新增需求必须带流程侧号、规格树必须覆盖全部已知能力。**这一层同样是被审计对象**——它的规矩必须可机核，不散在几份说明里。

> **本能力的 Requirement 号**：按本轮立的新规矩（Requirements 第 4 条），新写的 Requirement 必须带流程侧号；而流程侧今天没有对应需求 ⇒ **逐条登记为「无号·待流程侧增补」**，不造号、不拿相近号硬凑。这是新规矩的第一次适用。

## ADDED Requirements

### Requirement: 〔无号·待流程侧增补〕默认走融合档

`ninedim/records/openspec-流程件/openspec-config.yaml` 声明的 schema SHALL 为融合档 `opsx-swe-gb`；被改回默认档 `spec-driven` 时，守卫 SHALL 以非零退出码失败。理由：不写死默认档时，"忘了加 `--schema`"会**静默**走回默认档，而静默回退正是这条能力要消灭的东西。

#### Scenario: 默认档被改回即失败

- **WHEN** 有人把 `ninedim/records/openspec-流程件/openspec-config.yaml` 的 `schema:` 改回 `spec-driven`
- **THEN** `spec_bridge.py` 报出该文件与行号并**非零退出**，且输出里写明"默认档被改回"
- **证据**：`scripts/verify/spec_bridge.py --self-test`

### Requirement: 〔无号·待流程侧增补〕一个 change 的产物链完整，归档硬前置

一个 change SHALL 具备完整产物：`proposal` → `specs` ∥ `design` → `tasks` → **`review`**；`review.md` 缺失时 SHALL 拒绝归档。**不得以任何流程理由裁件**（例如"这次改动小，不写影响分析"）。

#### Scenario: 缺 review 的 change 不许归档

- **WHEN** 一个 change 目录缺少 `review.md`（或它只是空壳）而试图归档
- **THEN** 守卫**非零退出**并指出缺件；补上后同一命令转绿
- **证据**：`scripts/verify/spec_bridge.py --self-test`

### Requirement: 〔无号·待流程侧增补〕证据行必须指向真实存在的测试或脚本

规格里每条 `- **证据**：<路径>::<函数名>` 或 `- **证据**：<脚本> --self-test` SHALL 指向**真实存在**的函数或脚本；不存在时 SHALL 非零退出。理由：`openspec validate` **不校验这一项**，不校验就会随时间静默失效（改名即失锚）。

#### Scenario: 改一个测试名即变红

- **WHEN** 规格里引用的测试函数被改名或删除
- **THEN** 守卫报出该证据行所在文件与行号并**非零退出**
- **证据**：`scripts/verify/spec_bridge.py --self-test`

### Requirement: 〔无号·待流程侧增补〕新增需求必须带流程侧号

新写的 Requirement SHALL 带流程侧需求号（`REQ-<类>-<三位流水>`）；**取不到号时 SHALL 登记为「无号·待流程侧增补」，SHALL NOT 自造号、SHALL NOT 拿相近号硬凑**。既有的无号 Requirement SHALL 在编号桥映射表里逐条在册。
机核判据：编号桥映射表 SHALL 覆盖规格树下**全部** Requirement——每条要么挂到号，要么显式标"无号"。

#### Scenario: 有需求没进映射表即失败

- **WHEN** 规格树里存在一条 Requirement，而编号桥映射表里既没给它号、也没标"无号"
- **THEN** 守卫**非零退出**并列出该条 Requirement 的文件与行号
- **证据**：`scripts/verify/spec_bridge.py --self-test`

### Requirement: 〔无号·待流程侧增补〕能力覆盖完整，未实现的在册不停工

规格树 SHALL 覆盖世界核心的**全部已知能力**。尚未实现的能力 SHALL 以 delta ＋ tasks 的形式停留在**未归档的 change** 里（在册、可见），SHALL NOT 以"还没实现"为由排除在 OpenSpec 之外，也 SHALL NOT 写进主规格冒充"已成立"。
机核判据：仓内 SHALL 存在至少一个未归档的覆盖 change，且其 `tasks.md` 里存在未勾项（即：未实现的东西确实留在未归档态）。

#### Scenario: 覆盖 change 不在册即失败

- **WHEN** 承载未实现能力的 change 不存在、或它已被归档（等于把未实现当已成立）
- **THEN** 守卫**非零退出**并说明"覆盖缺口失去落点"
- **证据**：`scripts/verify/spec_bridge.py --self-test`
