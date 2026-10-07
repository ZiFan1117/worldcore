# Spec Delta

## Purpose

<!-- 仅"新能力"填这一节：一两句话（≥50 字）说明这条能力是干什么用的。
     已有能力的 delta 请删掉本节——它已有 Purpose，写在这里会被忽略。 -->

## ADDED Requirements

### Requirement: REQ-X-000 需求名

<!-- 标题必须以 REQ 号开头，号从流程侧（SRS / RTM）取，永不复用、废弃留行、写全左补零。
     REQ-F-012 不写成 REQ-F-12。

     正文用 SHALL / MUST 写规范性要求，避免 should / may。

     只装"已成立且可复现"的行为。未定的、待裁的、已知残余风险 → design.md 的排除清单。 -->

#### Scenario: 场景名

- **WHEN** <!-- 条件 -->
- **THEN** <!-- 期望结果 -->
- **证据**：<!-- `path/to/test_file::test_name` 或 `tools/x.py --self-test`
     测试名必须真实存在；由 spec_bridge.py 校验存在性 -->

## MODIFIED Requirements

<!-- 改已有能力的规格级行为时用这一节。
     ⚠ 必须贴出**完整的** Requirement 块（从 ### Requirement: 到所有 Scenario），
     只贴改动部分会在归档时丢失细节。
     标题文字须与 ninedim/01-意图环/04-规格/ 下现有 Requirement 完全一致（空白不计）。 -->

## REMOVED Requirements

<!-- 废弃能力时用这一节，必须带 Reason 与 Migration：

### Requirement: REQ-X-000 需求名
**Reason**: 为什么要移除
**Migration**: 使用方该怎么迁移
-->

## RENAMED Requirements

<!-- 只改名字时用这一节：

- FROM: `### Requirement: REQ-X-000 旧名`
- TO: `### Requirement: REQ-X-000 新名`
-->
