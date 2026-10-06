# channel-identity Specification

## Purpose
规定"谁在说话由系统给出，不由请求自称"这一层对外可核的行为。身份如果可以由请求方自己声明，
门禁、审计与归责三件事同时失效，因此这一条是 `管` 的前置条件。

## Requirements

### Requirement: 身份取自内核而非请求自称

通道 SHALL 使请求方身份由**套接字绑定**决定：每个监听套接字在创建时绑定到一个身份，
只有该身份能连上；系统 SHALL NOT 从连接元数据、对端凭证或请求正文取得身份。
请求正文里自称的身份与套接字绑定的身份不一致时，系统 SHALL 拒绝该请求且 SHALL NOT 落笔。
未被身份映射登记的套接字 SHALL 被默认拒绝，而不是降级为匿名。

#### Scenario: 请求自称的身份不生效

- **WHEN** 一个请求在正文里声明一个与内核给出的身份不同的主体
- **THEN** 该请求被**拒绝且不落笔**，错误串含 `Impersonation`，账本 `last_seq` 在拒绝前后不变
- **证据**：`tests/contract.rs::c14_channel_takes_identity_from_kernel_not_from_request`
      —— **⚠ 本证据证明的是"拒绝"，不是"采用内核身份并忽略自称"**；
      "`actor` 取自映射"由同函数 `world-core/tests/contract.rs:653-657` 的另一条断言承担。

### Requirement: 通道身份的实际保证与它的边界

通道身份 SHALL 由套接字文件的属主与权限保证：只有套接字属主能够连接，连接即代表该身份。
该系统 SHALL NOT 区分连接方是哪一进程，SHALL NOT 约束超级用户的行为。

已知边界 SHALL 被如实声明，且此边界是**能力的正式条文**而不是注意事项：
当套接字属主为 `root` 时，**任何** root 进程连接该套接字都取得该套接字的身份。
该边界由"套接字不可被他人写"这一层承担，**不由连接受理层承担**；
故"身份取自内核"这一说法 SHALL NOT 被读成"任何越权连接都会被识别出来"。

#### Scenario: 别的 uid 连不上（权限即身份）

- **WHEN** 在一个"祖先目录也不可被他人写"的位置建套接字（0600 + chown 到配置 uid），
       再由**另一个 uid** 尝试连接
- **THEN** 连接被内核拒绝（非零退出），且输出里不出现 `CONNECTED`
- **证据**：`world-core/tools/system_acceptance.sh`（断言 ㉔–㉖；由 `world-core/check.sh` 第 ⑥ 步执行
      ——`:133` 逐字 `run_tail 3 "系统级验收（TC-037–TC-040）" bash tools/system_acceptance.sh`）

#### Scenario: 未核实机制时的如实登记

- **WHEN** 运行环境缺 `setpriv` 或当前不是 root，使跨 uid 反例无法执行
- **THEN** 该步打印「未能校验」，**不得**记为通过，也**不得**使整体退出码变绿
- **证据**：`world-core/tools/system_acceptance.sh`（:346 的【未能校验】分支）

#### Scenario: 超级用户连接受理层不设防（边界固定）

- **WHEN** 由套接字属主以外的 root 进程连接该套接字
- **THEN** 连接成立并取得该套接字的身份——本断言证明的是**边界**而不是实现缺陷；
      它把"身份取自内核"限定为"**只有套接字属主能连**"，SHALL NOT 被读成"能识别越权连接"
- **证据（待补）**：**本条尚无断言**（列进 tasks）——实现侧为 `world-core/src/bus/mod.rs`:256-257
      （受理层不读对端凭证）；文档出处为 `world-core/docs/理论/语义世界-理论书-第一版-合订.md:697` 逐字
      「最高权限的用户可以连任何套接字，这一项对它无效」。
