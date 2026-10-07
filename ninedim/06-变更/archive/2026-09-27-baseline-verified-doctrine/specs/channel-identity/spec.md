# Spec Delta

## Purpose

规定"谁在说话由系统给出，不由请求自称"这一层对外可核的行为。身份如果可以由请求方自己声明，
门禁、审计与归责三件事同时失效，因此这一条是 `管` 的前置条件。

## ADDED Requirements

### Requirement: 身份取自内核而非请求自称

通道 SHALL 从内核提供的连接元数据中取得请求方身份，SHALL NOT 采信请求正文里自称的身份。

#### Scenario: 请求自称的身份不生效

- **WHEN** 一个请求在正文里声明一个与内核给出的身份不同的主体
- **THEN** 世界采用内核给出的身份，请求正文里的自称被忽略
- **证据**：`scripts/test/contract.rs::c14_channel_takes_identity_from_kernel_not_from_request`（`check.sh` 步骤 ③b）
