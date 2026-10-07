# Spec Delta

## ADDED Requirements

### Requirement: 〔无号·待流程侧增补〕通告的闸

**通告 SHALL 与变更、动作一样过门禁**：主体只能发它被允许发的通告；不该由它发的通告 SHALL 被拒，拒绝 SHALL 留下可核的流水。
（两条纪律已在实现里落地：① 带保留前缀（`gate.`）的通告类型只许内核自己写；② 非保留前缀的通告，其 `actor` 必须在主体白名单内——执行者是 `src/lib.rs::adjudicate_notice`。）
**仍在册的缺口**：非保留前缀的通告**不检查 `writes` 授权表**、只检查主体白名单（通告按主体收窄授权属门禁强度变更，须人裁）。

#### Scenario: 越权通告被拒且留痕

- **WHEN** 一个未被允许的主体提交一条本不该由它发的通告
- **THEN** 提交被拒、不落笔，且账本里留下一条说明**拒绝了什么**的流水
- **证据**：`scripts/test/contract.rs::c23_notice_from_unlisted_actor_is_refused`
      （不在册主体被拒且错误码为 `ext.world.Gate.NoticeRejected`；同用例带在册主体的正例对照）
      与 `scripts/test/contract.rs::c23_notice_with_reserved_prefix_is_refused_for_outsiders`
      （保留前缀路径）
      —— **⚠ 两条都不查 `refused` 指纹、也不查"伪造通告不落笔"**：前者只查错误码，
      后者的"不落笔"由 `src/lib.rs::gate_refusal` 的写法承担而无断言
      ⇒ **本条的这两句今天尚无断言**（列进 tasks）。

### Requirement: 〔无号·待流程侧增补〕可逆性判定与出厂配置互校

闸 SHALL 读得到动作的风险等级，并按**动作的不可逆等级**决定是否加摩擦；载体层的撤销点与世界状态的可逆性 SHALL **各自成立且互不冒充**，两处出厂配置冲突时 SHALL 拒绝启动。
（书第五章 5.5 判红的三件事今天已逐条落地：闸读得到风险等级（`src/gate.rs:73` 逐字 `pub risk: Option<CarrierRisk>,`，等级由 `src/gate.rs:445` 逐字 `cap.risk = carrier.lookup(name).map(|m| m.risk);` 接进能力表）；两处出厂配置互校、不一致即拒启（`src/gate.rs::cross_check_reversibility`，其调用在 `src/gate.rs:442`）；摩擦挂在**动作的不可逆等级**上、不挂在执行者身份上（`src/gate.rs:578` 逐字 `.filter(|c| !c.reversible)`）。）

#### Scenario: 同一个主体对不可逆动作必加摩擦

- **WHEN** 白名单内的主体对一件声明为不可逆的动作提交请求
- **THEN** **加摩擦**（在账本上留下可核痕迹：事件带 `gate.friction:<等级>` 旗标）；对可逆动作则免检但留痕
- **证据**：`scripts/test/atom_reversibility.rs::a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction`
      （同一主体 `world://user`：可逆不带旗标、不可逆带 `gate.friction:high` 且随事件落账）
      —— **本条的"有待批或确认环节"措辞已按实现改正**：v1 **没有审批通道**，白名单主体的摩擦是
      "必留可核痕迹 ＋ 由预批身份承担"，不是"停下来等人批"。
