# Spec Delta

## Purpose

<!-- 仅"新能力"填这一节：一两句话（≥50 字）说明这条能力是干什么用的。
     已有能力的 delta 请删掉本节——它已有 Purpose，写在这里会被忽略。 -->

## ADDED Requirements

### Requirement: REQ-X-000 需求名

<!-- 标题从流程侧取号开头，号从流程侧（SRS / RTM）取，永不复用、废弃留行、写全左补零。
     REQ-F-012 不写成 REQ-F-12。取不到号 ⇒ 写「无号·待增补」，不许自造、不许拿相近号硬凑。

     正文用 SHALL / MUST 写规范性要求，避免 should / may。

     只装"已成立且可复现"的行为。未定的、待裁的、已知残余风险 → design.md 的排除清单。 -->

#### Scenario: 场景名

- **WHEN** <!-- 条件 -->
- **THEN** <!-- 期望结果 -->
- **证据**：`path/to/test_file::test_name` <!-- 或 tools/x.py --self-test
     两条形态硬规矩（spec_bridge.py 判据② 会红）：
       · 本行**必须自带反引号包起来的 token**；还没有断言的条目改用
         `- **证据（待补）**：` 并写明落点——用「证据」这个标记而不给 token，形态上等于声称存在；
       · 长得像位置的 token（带 `/` 或 `.rs` / `.py` / `.sh` / `.md` 后缀或 `::`）
         会被**核存在性**：要么给可解析的路径，要么别写成路径样。 -->

## MODIFIED Requirements

<!-- 改已有能力的规格级行为时用这一节。
     ⚠ 必须贴出**完整的** Requirement 块（从 ### Requirement: 到所有 Scenario），
     只贴改动部分会在归档时丢失细节。
     标题文字须与 ninedim/01-意图环/04-规格/ 下现有 Requirement 完全一致（空白不计）。
     ⚠ ADDED 的标题**不得**与主规格里已有的标题撞车（撞了该 change 永远归不了档，
     守卫判据⑩ 抓这一条）。 -->

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

<!-- ═══════════════════════════════════════════════════════════════════════
     ★ 改完规格之后的连带动作（本档硬约束，经验 §八／§九）
     ——漏掉任何一条，守卫会红，而且**红得对**：

     1. 重跑生成链（**三步，顺序不能错**）：
          python scripts/gen/gen_specmap.py
          python scripts/gen/gen_secmap.py
          python scripts/gen/gen_bridge_md.py
        ⚠ **中间那步 `gen_secmap.py` 不许省**：判据⑬ 核的是 `generated/节对齐.md` 首部
        记下的 `generated/specmap.json` 哈希是否＝当前值 ⇒「specmap 重跑过、secmap 没跟着重跑」一律红，
        而**只补跑 bridge 不消除它**（补跑 secmap 才转绿）。实测两种错序都 rc=1：
        ①先 secmap 再 specmap；②先 bridge 再 specmap。
        （不跑 ⇒ `spec_bridge.py` 判据⑪ 报「generated/BRIDGE.md 与生成器的当前输出不一致」）
     2. 新增 / 改名的 Requirement 必须进 `generated/BRIDGE.md` 的**在册面**：
        判据④ 按**标题逐字**核规格树下的每一条；漏一条即红。
        新能力的 delta 若尚未并入主规格（change 未归档），走 `generated/BRIDGE.md` 的
        「由 change 引入、归档时并入主规格」那一节登记，**不许**为了让它"看起来成立"
        而手动塞进 `ninedim/01-意图环/04-规格/`（那会让归档报 `ADDED already exists`）。
     3. 单行加一格 / 减一格都要按表头列数重建，改完跑
        `python scripts/verify/table_width_audit.py <file>`。
     4. 编码 UTF-8 **无 BOM**、行尾 LF；中文串里用「」不用 ASCII 双引号。
     ═══════════════════════════════════════════════════════════════════════ -->
