# AIOS-FS 融合总表 —— 两份设计件合成一份

> **件性质**：★ 本件是**合件**，不是评审、不是结论、**不签字**（来源2 §七 逐字：「未下任何结论、未签字、未估工期」）。
> **合并纪律**：★ **只合不改** —— 下面每一条读数都能在两份来源件里找到；本件**不新增主张**。
> ★ 两份来源件**互相矛盾**处，本件**并列两处 ＋ 标「待裁」**，**不替作者选**（清单见 **末尾 · 附二**）。
> ★★ **已有更新版 v0.3**（依作者裁决「**不动本体**」重排，2026-10-15）：`设计-AIOS-FS融合总表-v0.3-不动本体.md` —— ★ 本件（v0.2）**保留为被评版之后的「评审后修版」**，**不再是最新版**。
> ★ 落点（★ **评审后修**）：原文写「D:/Code/_scratch/AIOS-FS-融合总表.md（★ **不进 ninedim/**）」—— ★ **与现取不符**：本件现存**两处、逐字节相同**（`D:/Code/_scratch/AIOS-FS-融合总表.md` 与 `ninedim/06-变更/2026-10-13-aios-semantic-plane/设计-AIOS-FS融合总表.md`），且后者**已进 git**（`f687411`）⇒ ★ **唯一权威副本是哪一处，待人裁**。
> ★ 本件**没有跑过任何构建／测试**；**没有一行实现**（见 §九）。
> **体例**：来源件里的 Markdown 反引号在本件里改成「」或直接去掉；**逐字以词为准，不改词**。
> ★ **加粗体例（评审后修 · 甲-01／甲-02）**：★ 引文里的 **加粗** **是本件所加，原文大多没有** —— 凡加粗**改变了读法**的一律去掉；本次已去掉**三处**（`05:518`／`05:522`／`evidence_emit.rs:35`）。★ **其余引文里的加粗未逐处去粗**（工作量），**如实登记为未做**。

---

> ★★ **修订块（2026-10-15 · 评审后修 · 第 1 轮）**
> ★ **本件已按《评审-五席判词汇总-设计-AIOS-FS融合总表.md》的「必闭项」逐条修**；★ 五席给的都是 **有条件通过** ⇒ ★ **本件没有被判「通过」，修完也**不是**「已通过」**（承认与否由人定，硬约束 6）。
> ★ **修后本件不再是纯「只合不改」**：凡本席（Lead）**现取复核**后改动处，一律**标席号 ＋ 写明现取读数**，**逐条对照见本件 §十**。
> ★ **被评版本**：sha256 `dadf255abee33c1055cbddaf436cd56160fa8fecfab420aa7fd80a6d7d6d3ef9`（**401 行 ／ 90,287 B**，五席冻结未破）。
> ★ **修后 sha256 与行数不写在本件里**（自指会随改而自破），改写在 `改动对照.md` §十七；★ **哪些修了、哪些没修、哪些待人裁，一并写在 §十**。

---

## §一 一句话：这份文档要干什么

把**两份已有的设计件**合成**一份**：

- **来源1** ＝ D:/Code/_scratch/aios-fs-融合设计.md（**9 条**逐条设计：「它原话／我们现在／合进来长什么样／代价／优先级」）；
- **来源2** ＝ D:/Code/_scratch/aios-fs-可借鉴.md（**三张表**：A【值得加】13 条／B【已有对应】10 条／C【不适用·故意不做】13 条）。

⇒ 产出**一份完整、可读、可裁的总表**：两份的**重叠合并成一条**（指针模型、隐私等级、快照号、事务＋证据两条链等，见 §三 行内括注），两份**各自的独有条目全部保留**（不许因为合并而丢条）。

★ 作者的原话（逐字）：「**先合在一起，给我一个完整的文档**」。

★ 作者的口径纠正（逐字）：「**不是调用已有的系统，而是把它们合在一起，把我们这个更加壮大了，他有的一些好想法我们要合进去**」。

★ 本件**不下结论、不签字**：凡要人裁的，一律进 §五。

---

## §二 来源与口径

### §二·0 ★★ 先写这条澄清（不写它，下面整张表都会被读错）

1. ★ **我们仓里本来就有整份 crates/aios-fs（25 个 .rs）** —— 来源2 §〇 逐字：「★ **我们的仓里**（D:/Code/13-aios-worldcore/crates/aios-fs/）**已经有整份外部 aios-fs crate，25 个 .rs 与 VM 逐件 md5 相同**」；同节依据列逐字：「★ **有**，25/25 与 VM 逐字节相同」。
2. ★ **我们的语义面 aios-worldcore 一个模块都不依赖它** —— 来源2 §〇 逐字：「★ **没有**，它一个模块都不依赖 aios-fs」；依据列逐字：「crates/aios-worldcore/Cargo.toml:9-13 只有 aios-ontology ＋ serde_json ＋ blake3」。
3. ⇒ **「仓里有」不等于「已吸收」** —— 来源2 §〇 逐字：「★ 下游**不许**把 ① 读成『我们已经有了』——**它不是我们的**：它是外部 vendored 件，由 C1 判据按外部一致性盯着（verify/allowed_upstream_edits.txt 全表 18 行，其中只有 crates/aios-fs/src/in_memory.rs 一行是动过它的），**且没有任何一条我们的语义面代码连到它**」。
4. ⇒ **「没吸收」不等于「不能用」** —— 来源2 §〇 逐字：「★ 也**不许**把 ② 读成『我们不能用』——**用不用是人的决定，本席不下这个结论**；本件只报事实。」
5. ★ **本件是设计，没有一行代码是实现** —— 来源1 件头逐字：「★ 本件**只出设计**。**没有动** ontology.json，**没有动**任何权威件，**没有动外部**。」
6. ★★ **评审后修 · 测试席 G-02 ＋ 本席现取**：原文写「**所有**「会红的反例」今天一条都不存在」—— ★ **口径过宽，且与同件 §六 B10 相抵**（B10 自报 `query.rs:212-221`「**且有会红反例盯着**」）。★ 现取：来源1 §10.3 那句**只管它自己那 9 节给的形状**：「每节给的『会红的反例』是**判据形状**，**不是已立好的判据**——它们**今天一条都不存在**。」；★ 而**本仓今天在册三条**：`crates/aios-worldcore/src/engine/query.rs:195`（逐字「会红反例 1」）／`:212`（「会红反例 2」）／`:223`（「会红反例 3」）。⇒ ★ 本件**照来源1 的射程收窄**；★ 这条**同件两说已登记进 附二 第 13 条**（**不替作者选**）。
7. ★ 一处**两份来源自相矛盾的读数**（并列、待裁、不选）：来源1:13 写「读的参考实现 ｜ crates/aios-fs/src/（**35 件**；行号见各行引用）」；来源2 §一 R1／R5／R6 写 src「**25 个 .rs**」「**25 行 md5**，与 R5 逐行相同」。★ 本件**照来源2 的 25 立文**（来源2 有 25 行 md5 逐行读数），但**两处并列，待裁**（见 附二 第 1 条）。
★ **评审后修 · 五席共同确认 ＋ 本席现取**：`crates/aios-fs/src` **现数 25 个 `.rs`**（顶层 22 ＋ `service/` 3）；而 `crates/aios-worldcore/src` **现数 35 个 `.rs`** ⇒ ★ 来源1 的「**35 件**」**与后者同数**，系**张冠李戴**。★ **本件照 25 立文有据**；★ **待裁项要不要据此裁为 25，仍由人定**。

### §二·1 两份来源件（路径／行数／字节／sha256）

| 件 | 路径 | 行数 | 字节 | sha256 |
|---|---|---|---|---|
| **来源1** | D:/Code/_scratch/aios-fs-融合设计.md | 556 | 45,286 | 4ecc3446af7f8183307303c5da5f80356b1afcefadd054fef69cd87e52b6df25 |
| **来源2** | D:/Code/_scratch/aios-fs-可借鉴.md | 269 | 40,591 | a91ee09e8f0ec605d34968c26fe096731de4847c3f7fdf4d8cb8ba9a3c1ffcb7 |

★ 行数／字节／sha256 为**本次现取**（两份来源件**都没有自报自己的 sha256**：来源2 §八 逐字「本表不预填 —— 一填，改这一行就同时改掉行数与 sha ⇒ **自指**」）。
★ 行数口径：末行有换行**不吃成空行**。
★ 来源2 §二 自报「六件合计 **227,206 B ／ 3,849 行**」，其中 **3,849 行**与来源1:12 的 6 件行数（44／943／897／515／421／1029）**相加自洽**；但**字节数不相符** ⇒ 见 附二 第 10 条（本件只做加法，**未读规格**）。

### §二·2 两份来源读的范围（口径）

- **来源1 读的规格**：/root/aios/002.AI-OS.NET--SPECREV.2/L2_AIOS_FS/ 6 件：00_overview.md（44 行）／01_object_model.md（943）／02_query_view_language.md（897）／03_conflict_resolution.md（515）／04_implementation_space.md（421）／05_namespace_layout.md（1029）。
- **来源1 读的参考实现**：crates/aios-fs/src/（来源1:13 写「35 件」★ 与来源2 的 25 件并列，待裁）。
- **来源1 的「我们自己」行号口径**：D:/Code/13-aios-worldcore。来源1:14 逐字：「★ 已抽查：该仓 crates/aios-worldcore/src 下 **35 件 .rs** 与 VM /root/aios/crates/aios-worldcore/src **SHA256 逐件相同（35/35）** ⇒ 两边行号可通用」。
- **来源2 读的规格**：同一批 6 件（逐件「读了」／「没读」见来源2 §二 通读清单，本件照抄进 §八·3）。
- **来源2 读的代码**：/root/aios/crates/aios-fs/src/ 25 件（全读 lib.rs／chunk.rs／lifecycle.rs／pointer.rs／version.rs／snapshot_id.rs／transaction.rs／evidence_emit.rs／quarantine.rs／gc.rs／namespace_policy.rs 与我方同源件 fs_trait.rs／namespace.rs；**未读** error.rs／id.rs／object.rs／impl_space.rs／in_memory.rs／query.rs／query_eval.rs／query_parser.rs／evidence_payloads.rs／service/）。
- ★ 两份件**都没有跑构建／测试**（来源2 §六 第 10 条逐字：「**本席未跑任何构建／测试**（VM 上没跑 cargo，宿主上没跑 python verify/check.py）⇒ 本件**没有任何「跑通了」的主张**」）；两份件都**没有一行实现**。

---

## §三 总表（核心）

★ 编号 **H01…H13** ＝ **合过之后**的编号；每行**括注它来自哪份来源件的哪条**（例：「来源1-②／来源2-A02」）。
★ 两份**重叠**的 **9 组**各并成一条（路径／指针／事务＋证据两条链／冲突／快照／隔离／生命周期／隐私／恢复）；两份**各自独有**的条目**全部保留**（来源2 的 A08／A11／A12／A13 四条在来源1 里没有对应条）。
★ 每行都有**逐字出处**；没有逐字出处的条目**不进本表**（来源2 表 B／表 C **不是缺口**，分别进 §六／§七，**不占 H 编号**）。
★ 「优先级」一栏：两份件给了不同星级的，**两处并列**，不平均、不替作者选。

| 编号 | 合什么（一句话） | 它的原话逐字（出处 文件:行/节） | 我们现在是什么样（我们自己的 文件:行） | 合进来之后长什么样 | 要动的件 | 动不动 ontology.json | 优先级 |
|---|---|---|---|---|---|---|---|
| **H01**<br>（来源1-⑦／来源2-A09） | 路径分类：闭集词表 ＋ 目录版本号 ＝ 权限类的地基 | 来源1-⑦.1：**05_namespace_layout.md:28**「**I1 — Closed top-level vocabulary.** /aios/ directly contains exactly two reserved entries: system/ and groups/. No third top-level entry is ever created.」；**05:34-35**「**I7 — Determinism.** Path-string → typed NamespacePath is deterministic given the namespace catalog version.」／「**I8 — Path traversal forbidden.** .., ., double-slashes, and segment counts > 32 are rejected at parse time.」；**05:236**「**Output:** typed NamespacePath message OR ResolutionError with closed code.」；**05:341**「Callers comparing two resolved paths across catalog versions get CATALOG_VERSION_MISMATCH」；**05:503**「The namespace catalog version is nscat_<hex_lower(BLAKE3(jcs(catalog_descriptor)))[:32]>」；**05:347**「This is a constitutional hard-deny」；**05:366-373** 恢复边界四路径（policy/／capabilities/／vault/／recovery/）＋ RecoveryModeRequired。<br>来源2-A09：同引 **05:28**／**05:34**／**05:341** 三处。 | 来源1-⑦.2「**我们根本没有「路径」这一面**」：名字是扁平的，主体是 world://<ns>/<name> 形状 —— **src/core/types.rs:13** 逐字「一个在册的名字（world://<ns>/<name> 形状）」；**types.rs:18-21** Who::new 逐字「**不做校验**；校验在 validate 那一面」，而 validate 那一面**今天没有这条校验**，唯一用到前缀的是 **validate.rs:83** s.starts_with("world://")（只判前缀、不判内容）；已在用的段名＝world://user／world://user/zhang／world://agent/dsh／world://presence/omarchy 与系统主体 _system: 前缀（**types.rs:32** is_system）；「恢复／审计主体」今天只是字符串（_system:store，**store.rs:43-45**），**没有身份语义**。<br>来源2-A09：名字空间只有 world://<ns>/<name> 一种形状（**src/core/types.rs:13** 注释），**没有「路径 → 类 → 权限类」的分层**；crates/aios-worldcore 下 grep **0 命中**。 | 来源1-⑦.3 五步：① 一份**闭集词表**（world:// 之后只允许闭集段名，首段取自我们**今天已经在用的** user／agent／presence／system，**不多造**；加名＝版本化改动）；② **目录版本号** wcat_<blake3(jcs(闭集))[:32]>（照它 nscat_，BLAKE3 与规范压平我们已都有 ⇒ **零新增依赖**），跨版本比较 ⇒ CatalogVersionMismatch；③ **解析三步**（前缀不对 ⇒ NotUnderWorld；段里出现 ..／.／空段／段数 > 32 ⇒ 拒；首段不在闭集 ⇒ InvalidTopLevel；**错误码是闭集**）；④ **默认拒的跨域**（我们没有组这一层 ⇒ 不照抄；把形状落下来：主体的域 ≠ 目标的域 ⇒ **硬拒**，_system 走恢复例外）；⑤ **恢复路径永远可解析**（world://system/recovery/... 必须可被解析出来）。<br>来源2-A09：把「名字」升格成**可解析的路径 → 闭枚举类**，每个类带 mutation_class／read_class ＋ 一个**目录版本戳**（＝本体现行版的指纹）——「这正好接我们已有的 vocab_hash（总线通行证那一格）」。 | 来源1-⑦.4：★ **core/types.rs**（签名改动：Who::new 不校验 ⇒ 加 Who::parse -> Admit<Who>，或**退一步**只加 validate_subject 口而**保留** Who::new）／**新增 core/namespace.rs**（解析 ＋ 闭集 ＋ 版本号）。<br>来源2-A09：改 **2-3 个件**（新增 namespace 面 ＋ governance 挂类），**不动外部**。 | ★ **待裁**（并列）：来源1-⑦.4「**可能**：闭集词表若写进本体 ⇒ **提案**。**可以不写**：先落在代码里当门禁（和今天 check_shape 同一层）」／来源2-A09「★ **要（写成提案）**—— 要加「名字空间类」这一节」。 | 高（来源1-⑦.5）／★★ 中（来源2-A09，★ 它 I5／§10.1「recovery-only mutation ＋ human approver」与我们「AI 不代签」同向，可一并借） |
| **H02**<br>（来源1-②／来源2-A02） | 指针搬动模型 ＝ 状态推进／回滚（账的正规化） | 来源1-②.1：**00_overview.md:13**「Pointer moves promote state; rollback moves a pointer to a previous verified version.」；**01_object_model.md:205-212**「message Pointer { string pointer_id…; string object_id…; PointerKind kind…; string current_version_id…; … last_promoted_by_transaction_id … }」；**01:214-221**「enum PointerKind { CURRENT…; STABLE…; CANDIDATE…; ROLLBACK…; QUARANTINE… }」；**01:226**「Pointer moves use **atomic compare-and-swap** on (pointer_id, expected_current_version_id)」；**01:229-238**「PromotePointer(pointer_id, expected_current_version_id, new_version_id): if pointer.current_version_id == expected_current_version_id: … else: return ConflictDetected(…)」。<br>来源2-A02：同引 **00:13**／**01:226**，另 **01:241**「The candidate version persists; only the pointer move is rejected.」 | 来源1-②.2：「对象 → 指针 → 版本」那层间接**今天只有半层**，且是我们自己写明的 —— **src/engine/store.rs:127-128** 逐字「★ 这就是「对象 → 指针 → 版本」那层间接落在本面的样子：先问现状「现行是哪一条」，再把它的 seq 写进新那一笔的 at_seq。」；承载：**store/projection.rs:69-71** last_write_seq（键 ⇒ 现行那一行的 seq）、**store/row.rs:39-41** at_seq；**没有指针对象、没有版本号**（版本＝账上的 seq）、**没有回滚** —— **row.rs:23** Tombstone 逐字只是「**不真删**，只记『这一条作废了，为什么』」，**作废 ≠ 搬回去**。<br>来源2-A02：实物只有 predecessor_of 找 last_write_seq（**store.rs:129-133**）⇒ 我们**没有**：独立的指针、expected 检查、回滚口。 | 来源1-②.3 四步：① **指针升格成显式的一格** —— 折现状多折一件 pointers: BTreeMap<键, Pointer>，Pointer { current: EventSeq, stable: EventSeq, rollback: Option<EventSeq> }（★ **不需要新造版本号**：账只追加 ⇒ EventSeq 天生是版本）；② **指针的每一动也进账** —— 追加一笔 change 族、what=pointer.promote｜pointer.rollback，params {key, from, to, expected}（⇒ 回滚也满足只追加）；③ **CAS 的口提前留好** —— 指针搬动收 expected: EventSeq，现读 ≠ expected ⇒ 拒；④ **折出现状多一个读口** —— pointer_of(key)／pointer_history(key)。<br>来源2-A02：把「键 ⇒ 现行 seq」升格成**指针实体**（pointer_id ＋ kind ∈ {CURRENT, STABLE, CANDIDATE, ROLLBACK} ＋ current_version_id）；Store 写路径加 expected_seq 形参（CAS）；补 rollback(pointer, to_version)；★ 与我们「账只追加」不冲突：「**指针搬动只改指针那一栏，正文一行不改**」。 | 来源1-②.4：engine/store/{projection,read,row}.rs／engine/store.rs／core/types.rs（加 Pointer）；**不动外部**。<br>来源2-A02：改 **3-4 个件**（新增 pointer 面／store.rs／ledger.rs），**不动外部**。 | ★ **待裁**（并列）：来源1-②.4「**不动**（指针是我们内核的读侧派生物，不是本体声明的类）★ 若要把「指针」写进本体 ⇒ **提案**，非必需」／来源2-A02「★ **要（写成提案）**—— 今天的本体没有「指针」这一类；我们的（族,序号）二级索引（**src/engine/ledger/index.rs:14-17**）只能按族扫，指不到『某一个对象的现行版』」。 | 高（来源1-②.5）／★★★ 高（来源2-A02） |
| **H03**<br>（来源1-④／来源2-A01） | 事务：一单原子 ＋ 每一次写同时挂「事务」与「证据」两条链 | 来源1-④.1：**01_object_model.md:245**「Transactions may include multiple PointerMoveOps. Either all promotions succeed (transaction commits) or none does (transaction aborts). Implementation uses a two-phase commit fence within a single AIOS-FS instance」；**01:252-262**「message Transaction { transaction_id; subject; action_id; started_at; completed_at; state; writes; pointer_moves; evidence_receipt_id }」；**01:289-290**「COMMITTING ──all CAS succeed──▶ COMMITTED」／「COMMITTING ──any CAS fails──▶ ABORTED (sibling versions persist; pointers unchanged)」；**04_implementation_space.md:97-103**「a single WalEntry … appended … with fsync=true」／「A crash at any point before step 3 leaves the WAL clean」。<br>来源2-A01：**01_object_model.md:427**「Every write has transaction and evidence linkage.」；**01:26**「Atomic write/promote unit with evidence linkage」。 | 来源1-④.2：**一次调用只落一行** —— **src/engine/store.rs:110-123** commit() 只推一行；**src/engine/instances.rs:119-173** register() 也是「成功 ⇒ 同批记**一笔**账」；次序已写死：**instances.rs:150** 逐字「**先记账、再落表**」／**src/engine/ledger.rs:87-88** 逐字「**先封存、后入链** —— 封条与链尾都算好了才动正文，被拒的那一笔在正文／链节／索引上**一处都不留**」；**没有「一单」这个对象**：**ledger.rs:89-123** 公开口只有 append，**没有「把 N 笔一起落」的口**，也**没有回滚口**。<br>来源2-A01：我们的**账**与**存储**是两条互不相干的轨 —— Store 追加 Row（**store.rs:110-123** 的 commit），Ledger 追加 Event（**ledger.rs:89-123** 的 append），**执行五步里一次都没走 Ledger**（**src/engine/execute.rs:74-102**）。 | 来源1-④.3：① **收单** Txn { txn_id, subject, started_at, ops: Vec<TxnOp> }，TxnOp ∈ { Write{key, reg, expected}, Promote{key, expected, to}, Tombstone{key, reason} } —— 收单阶段**只校验、不落任何东西**；② **落单** —— 把**整单**封成一笔（照 01:98-100 的 single WalEntry 形状），Ledger 加 append_txn(txn)：**一笔账 ＝ 一单**（★ 我们的封条**压在整笔上**，seal.rs:47-60，所以「一单里改了一处」照样断链 —— 这一点我们已经有了）；③ **状态进账** PENDING → COMMITTED｜ABORTED，aborted 的那一单也**留一笔**；④ **缓存一致** —— 现状缓存只在该单**落定之后**才失效重折（store.rs:121）。<br>来源2-A01：给 Store 的每次 commit 发一个**事务号**（复用 EventSeq 或新开 TxnSeq），并把「一次事实变更」强制展开成一对 —— 一条 Store Row ＋ 一条 Ledger Event，用同一个事务号串起来；接口层面：commit 的返回从 EventSeq 变成 (EventSeq, TxnId)，且 Ledger::append 从「可选调用」变成 Store 写路径的**必经**一步。 | 来源1-④.4：engine/{store,ledger,instances}.rs／core/types.rs（Txn 类型）；**不动外部**。<br>来源2-A01：改 **3-4 个件**（store.rs／ledger.rs／execute.rs／core/types.rs），**不动外部**。 | ★ **待裁**（并列）：来源1-④.4「★ **可能**：若要把「事务」立成一个**类**或往 families 加一族 ⇒ **提案**。**不必需**：可用 change 族 ＋ what=txn.commit」／来源2-A01「★ **要（写成提案）**—— 今天的 envelope 只有 seq／who／at／…，账的族是 change／act／notice／job 四族，**没有「事务」这一栏**」。 | 中（来源1-④.5）／★★★ 高（来源2-A01） |
| **H04**<br>（来源1-⑧／来源2-A06） | 冲突：乐观并发（CAS）＋ 冲突是一等公民 | 来源1-⑧.1：**03_conflict_resolution.md:21-23**「Concurrent writes never overwrite each other.」／「They create sibling versions.」／「Promotion decides which version becomes current.」；**03:33**「expected_current_version_id != pointer.current_version_id」；**03:36**「The runtime emits a Conflict record automatically; the calling transaction is aborted unless a merge policy allows automatic resolution」；**03:73-77**「REJECT_PROMOTION ｜ Default for unknown object kinds ｜ No data loss; user/agent must act」…「CRDT_MERGE ｜ Evidence, memory, append-only logs ｜ CRDT type declared by object kind」；**03:90**「**No object kind gets automatic merge unless its merge policy is declared.** Implicit auto-merge is forbidden.」；**03:121**「Merge policies are part of the object-kind schema. They are not invented at conflict time.」；**03:219,229**「Open conflicts have a TTL. Default: **30 days**」／「Abandonment is **not** silent data loss: the candidate version still exists in audit-readable form」；**03:239**「Same as "any CAS fails" — atomicity wins; partial commits are forbidden.」；**03:94-117** CRDT vocabulary 闭集 6 种。<br>来源2-A06：**03:20-24**／**03:26**「A failed pointer-promotion CAS produces a Conflict record. The candidate version persists in STAGED state and becomes a sibling of the version that won the race.」／**03:67**「Conflicts are first-class objects, evidence-linked, and queryable」／**01:245**。 | 来源1-⑧.2：「★ **这一面我们完全是空的**」：写口**全要 &mut self**（**engine/store.rs:110**(commit)／**144**(create_as)／**172**(update_as)／**197**(delete_as)）；唯一一处真并发防护在治理面 **governance/mod.rs:55** rulings: Mutex<Vec<Ruling>>；**instances.rs:144-149** 的唯一互斥检查是 self.rows.contains_key(&key)，它**假设只有一个写者**；**Store::update_as 拿到了 predecessor_of(key)（store.rs:173），但那只写进 at_seq 当记账，从不参与判定（store.rs:174-181）**。<br>来源2-A06：Store::create_as 只判「键已存在」（**store.rs:151-153**），**没有 expected 检查**；crates/aios-worldcore 下 grep「冲突｜conflict」＝ **0 命中**；任务书自陈「我们完全没考虑并发写」—— 核实：**对**。 | 来源1-⑧.3 **分三块砖，一次只吃一块**（★ CRDT **不引**）：**砖一（今天就能做，零新数据结构）**把「期望」升级成闸 —— update_as/delete_as 收 expected: EventSeq，现读（last_write_seq）≠ expected ⇒ 拒 worldcore.Refuse.ConflictDetected{ key, current, attempted }；**砖二** Conflict 是一等公民 —— 落成账上的一笔（notice 族／what=conflict.raise），并折出一份 Conflicts 读口（{conflict_id, key, base, current, candidate, raised_at, status}）★「候选版本**仍在**」我们**天然满足**；**砖三** 合并策略属于类，且**不声明就不许自动合并**，★ 这一步要动本体 ⇒ 提案，过渡期**只做 REJECT_PROMOTION**；**TTL／放弃** TTL **只能声明、不能执行**（我们没时钟），「放弃」只落成账上两笔（raise ＋ abandon，带理由），**不删任何候选版本**。<br>来源2-A06：CAS 的 expected 形参（与 A02 同一处）＋ **冲突不得静默丢弃** —— 失败的候选**照样留一份**，并落一条「冲突」记录 ＋ 一条账（连 A01）；★ 借它 03:26 的关键一句「The candidate version persists; only the pointer move is rejected.」—— 冲突 ≠ 数据丢失。 | 来源1-⑧.4：engine/store/*（**写口签名加 expected**）／core/types.rs（Conflict）／**新增 engine/conflicts.rs**／**所有调用点与测试** —— ★「写口签名一变，tests/ 下 **6 个面级用例**（face_d_store_query.rs 等）**全要跟着动**」；**不动外部**。<br>来源2-A06：改 **2-4 个件**。 | ★ **待裁**（并列）：来源1-⑧.4「★ **可能**（merge_policy 进类定义 ⇒ 提案）；**砖一、砖二不必动**」／来源2-A06「★ **要（写成提案）**—— 要加「冲突」这一类／这一族」。 | 中（来源1-⑧.5，★「我建议只先吃砖一」）／★★ 中-高（来源2-A06） |
| **H05**<br>（来源1-③／来源2-A05） | 读一致性 ＋ 快照号（水位线／时间旅行） | 来源1-③.1：**01_object_model.md:317**「｜ SNAPSHOT ｜ Reads a consistent snapshot across pointers as of the call's wall time. ｜」；**01:321**「Callers must not assume internal mechanism — only the consistency guarantee.」；**01:549-556**（夹具）「expected: R sees either both (ver_a1, ver_b1) or both (ver_a2, ver_b2); never a mix」；**02_query_view_language.md:234**「Time-travel queries are always evaluated under SNAPSHOT consistency」；**crates/aios-fs/src/fs_trait.rs:85-94**「SnapshotSummary { snapshot_id, at, object_count, pointer_count }」。<br>来源2-A05：**01:317**／**01:321**／**01:556**／**01:431**「Snapshot reads return a consistent view across pointers.」；并点名**读一致性三档**（SNAPSHOT／LINEARIZABLE／EVENTUAL）。 | 来源1-③.2：读**一律现折** —— **src/engine/store/read.rs:54-56** project()、**read.rs:59-61** projection()（首次折 ＋ 缓存）；**src/engine/store.rs:110-123** 任何一笔写都让缓存失效重折；**src/engine/query.rs:114-134** all() 从现状里现取 —— 一次查询内部只读一份现状，★「但**这一点今天只写在行为里，没有写成契约，也没有一个可外传的号**」；已有的「一份序列重建」只有 **read.rs:31-36** Store::replay(log)（整库级）；我们**已经有**算「状态指纹」的手艺：**projection.rs:79-90** fingerprint()。<br>来源2-A05：**src/engine/store.rs:14-15** get/count 读的是折出来的现状，**没有快照、也没有一致性声明**；crates/aios-worldcore 下 grep「snapshot」只有 2 处 CSV 导出的假命中。 | 来源1-③.3：① 折出来的现状自带一个**水位线** Projection.as_of: EventSeq；② 折给一个名字 fold_id = blake3(规范串)，规范串 ＝ as_of｜键｜类｜seq 排序拼接（照 **engine/ledger/seal.rs:63-74** 的 params_canonical；blake3 本 workspace 早就有 —— **seal.rs:90-92**，**零新增依赖**）；③ 一个历史读的口 Store::project_at(seq)（把 fold(log) 换成 fold(&log[..seq])）⇒ **时间旅行**；④ 一致性写成契约 View { as_of, fold_id, matched, suppressed }，「**永不混**」结构上成立。<br>来源2-A05：给读路径加一个 SnapshotId（＝对我们的「对象／指针／版本」三张集合排序去重后压 BLAKE3 —— 与它 transaction.rs 的 ConsistencyClass 同形）；Query::all 与 Store::get 加一个「按哪个快照读」的形参；★ **零新增依赖**（**src/engine/ledger/seal.rs:90-92**）。 | 来源1-③.4：engine/store/{projection,read}.rs／engine/query.rs；**不动外部**。<br>来源2-A05：改 **2-3 个件**（store/read.rs／ledger.rs／query.rs），**不动外部**。 | 一致「**不动**」：来源1-③.4「**不动**（水位线是我们内核自己的读法）」／来源2-A05「**不要**（读一致性是运行期参数，不是本体的格）」。 | 高（来源1-③.5）／★★★ 高（来源2-A05）<br>★ **并列（非硬矛盾）**：来源2 点名**三档**，来源1-③ 只做 SNAPSHOT 那一档（逐字「我们不需要 MVCC」）—— 待裁，见 附二 第 7 条 |
| **H06**<br>（来源1-⑤／来源2-A03） | 隔离坏版本（＋版本状态机 STAGED／VERIFIED／QUARANTINED／RETIRED_VERSION） | 来源1-⑤.1：**01_object_model.md:327-333**（★ **评审后修 · 甲-05**：原文是**五个加粗的条目**（`- **Validation failure** …`…），本件压缩成一行 ⇒ **加粗未保留**，如实标注）「A version enters QUARANTINED state when any of: Validation failure… Integrity check failure on read (chunk hash does not match content)… Policy violation detected post-commit… External attestation failure… Operator manual quarantine.」；**01:337-338**「Pointers referencing a quarantined version are atomically moved to the ROLLBACK pointer's target if one exists; otherwise pointer is set to the prior STABLE.」／「Reads of a quarantined version are denied for non-recovery subjects; recovery and audit subjects may read.」；**01:349**「A quarantined version that is never resolved becomes RETIRED_VERSION after the operator-configured quarantine TTL (default 30 days).」；**01:353**「The chain version_id → quarantine_reason → exit_subject → resolution_outcome must be reconstructible from the evidence log.」；**01:397**「Quarantine corrupt versions.」。<br>来源2-A03：**01:157-160**（★ **评审后修 · 甲-04／甲-05**：原文是**枚举行** `STAGED = 1;   // …`，原写法把它**重构成**「X = 说明」的句子 ⇒ **按枚举逐字重排**，只压缩对齐空白、**词一个不改**）「STAGED = 1; // written but not yet verified／VERIFIED = 2; // verification passed; eligible for promotion／QUARANTINED = 3; // isolated due to validation/integrity/policy failure／RETIRED_VERSION = 4; // superseded; not eligible for promotion but readable for audit」；**01:337**；**01:353**「Every quarantine entry and exit emits an evidence record.」 | 来源1-⑤.2：**能查出来，但不能处置**。查：**src/engine/ledger.rs:158-160** verify() → **src/engine/ledger/seal.rs:98-144** check_chain，逐笔重算指纹、逐节核对前驱，**第一处**对不上就返回并把**位次**写进 field（**seal.rs:96-97** 逐字「学它 verify_integrity 的报法」）；**处置没有** —— 坏的那一笔仍留在 rows／seals 里，读侧 fold **根本不看 seals**（**projection.rs:96-112** 只按 Op 折）⇒ 今天唯一后果是 verify() 返回一个 Err —— **要么全账判坏，要么什么都做不了**。<br>来源2-A03：Store 只有三种写 Create／Update／Tombstone（**src/engine/store.rs:135-215**），**没有「这一版先隔离着，等判定」这一档**；crates/aios-worldcore 下 grep「quarantine」＝ **0 命中**。 | 来源1-⑤.3：① **账多一个隔离区** quarantined: BTreeMap<EventSeq, QuarantineEntry { trigger, at_seq, who, reason, at }>，trigger 是**闭集**（取完整性失败／校验失败／人工隔离／复核驳回；「policy violation post-commit」我们**还没有 commit 后重扫**这一环，如实不取）；② **隔离也是一笔账** notice／what=quarantine.enter｜exit（不删原文、不改原文）；③ **折现状时跳过被隔离的那一笔**，现状回到它之前那一版（**指针自动搬回** STABLE／ROLLBACK）；④ **读的分档**（非恢复主体 ⇒ 拒；恢复／审计主体可读）；⑤ **出口两条**（人工复核／TTL 到期转退役；★ 我们**没有时钟**，TTL 今天**只能声明不能执行**）。<br>来源2-A03：给 Row 加一个**版本状态栏**（staged／verified／quarantined／retired），并把「立碑」与「隔离」分开 —— 碑 ＝ RETIRED 的一半，隔离 ＝ **可读但不可推进**；再加一条**进／出隔离必落一条账**（连到 A01）。 | 来源1-⑤.4：engine/ledger/{seal,index}.rs／engine/ledger.rs／engine/store/projection.rs／core/types.rs；**不动外部**。<br>来源2-A03：改 **2-3 个件**（store.rs／core/types.rs／ledger.rs），**不动外部**。 | ★ **待裁**（并列）：来源1-⑤.4「**不动**（notice 族今天**已经在册**）」／来源2-A03「★ **要（写成提案）**—— 本体的 governance 节今天只有 tombstone（碑），没有「隔离」这一档；且 record 五要素里没有版本状态」。 | 中（来源1-⑤.5）／★★★ 高（来源2-A03）<br>★ **并列（载体位置）**：来源1 放**账**（ledger 侧 quarantined: BTreeMap），来源2 放 **Row**（store 侧版本状态栏）—— 待裁，见 附二 第 6 条 |
| **H07**<br>（来源1-⑥／来源2-A10） | 对象生命周期 ACTIVE→RETIRED→PURGED ＋ 保留期 | 来源1-⑥.1：**01_object_model.md:77**「ACTIVE ───retire──▶ RETIRED ───purge_after_retention──▶ PURGED」；**01:82-84**「ACTIVE ｜ Default; reads and writes allowed per policy.」／「RETIRED ｜ Logical removal; reads allowed for audit; writes denied; pointer moves denied.」／「PURGED ｜ Physical erase scheduled or completed; chunks reference-decremented; metadata kept as audit-only stub.」；**01:86**「Retention period defaults: 90 days for retired-then-purged.」；**01:100-102** 对象记录里带 lifecycle_state／retired_at／purge_at。<br>来源2-A10：**01:77**／**01:83**／**01:86**「Operator may shorten only with policy approval; lengthening is always allowed.」 | 来源1-⑥.2：**声明面参差** —— 本体里**有些类有** state = enum(…,retired)（application／agent／service／port），**有些类没有**（surface ★ **评审后修 · 乙-01：原文写「只有 visible/order/retract_seq」**报小了**** —— 现取 `ontology.json` 的 `objects.surface.fields` ＝ **6 格**：name／role／order／visible／retract_seq／cells；ledger 只有 path/compaction_seq/entries_total/retract_seq）；**「作废」与「退役」今天混在一处** —— **src/engine/store/row.rs:23** Tombstone 是「这一条作废了」，它**其实已经**是 RETIRED 的语义（**projection.rs:129-135** retire()：从**现状**里摘掉、历史不动），但**名字叫墓碑**，而且**没有 PURGED 那一档、没有保留期**；读侧**没有状态维**（**projection.rs:33-37** 只有 current／last_write／kind_index）。<br>来源2-A10：我们有**碑**（**src/engine/store.rs:184-215** 的 delete_as，带 哪一条／谁／为什么），**碑之后的处置没有**；**store.rs:21-22** 自陈「本面无时钟」。 | 来源1-⑥.3：① **一格共同的 lifecycle**（闭集 ACTIVE／RETIRED／PURGED），**所有类都有**；★ 类自己的 state（running／stopped…）**留着**（它是**运行态**，不是**生命周期**）—— 这正是作者「**同词不许两义**」的直接落法；② **折现状多折一件** Projection.lifecycle: BTreeMap<键, Lifecycle>，get() 默认只给 ACTIVE，get_including_retired() 给审计用；③ **两个口分开** retire(key, reason)（＝今天的 delete_as，语义改准，接口可保留旧名）与 purge(key)（**必须留 audit stub** —— 照它 metadata kept as audit-only stub）；④ **保留期** —— 本体里那 90 天**今天落不了地** ⇒ purge_at 这一格**先声明、不执行**，并**明写「未执行」**。<br>来源2-A10：碑上面的三档状态；读路径加「退役对象仍可审计读、不可写」；保留期需要一个**时钟**（我们今天的 store 没有时钟）。 | 来源1-⑥.4：engine/store/{projection,read}.rs／engine/store.rs／core/types.rs（Lifecycle）；★ **过渡期**可先用「本内核最小指认格」那条既有豁免（同 name，见 **instances.rs:114**）；**不动外部**。<br>来源2-A10：改 **2-3 个件**；★ 保留期会**引入时钟**，那是新的依赖面。 | 一致「★ **要（写成提案）**」：来源1-⑥.4／来源2-A10。 | 中（来源1-⑥.5，★「若要动本体，则**并入第一条那次本体提案一起提**」）／★★ 中-高（来源2-A10） |
| **H08**<br>（来源1-①／来源2-A04） | 隐私等级 ＋ 隐私天花板（「只升不降」＋ 静默过滤只报计数） | 来源1-①.1：**01_object_model.md:62**「Every object carries a privacy_class field aligned with S1.2 §5:」；**01:72**「Routing decisions (S1.2) and policy decisions (S2.3) read this field. Privacy class can be **raised** but never lowered for a given object; downgrade requires a new object.」；**01:68**「｜ SENSITIVE ｜ Identifiable user data (default if unspecified) ｜」；**02_query_view_language.md:155**「Every query is evaluated under the caller's **privacy ceiling** — the maximum class that the calling subject is authorized to see, derived from L4 policy.」；**02:167-171**「Objects whose privacy_class exceeds the effective ceiling are **silently filtered out** … An evidence record is emitted noting "N objects filtered by privacy ceiling" — no object IDs leaked, just a count.」；**02:181**「The router never raises the ceiling.」；**01:528-531**（会红夹具形状）「result: PERMISSION_DENIED」／「reason: "privacy_class_downgrade_forbidden"」／「obj_x.privacy_class: SENSITIVE (unchanged)」。<br>来源2-A04：**01:72**／**02:159**「Without an explicit privacy <= ... predicate, the query implicitly applies privacy <= caller_ceiling.」／**02:167**／**02:181** | 来源1-①.2：本体**已经声明了分级** —— **crates/aios-ontology/data/ontology.json** 的 governance.markings.levels 有三级 PUBLIC／INTERNAL／CONFIDENTIAL，且自陈逐字「"state": "声明面：有；执行面：**无**"」；它自己把缺口写清了：不能「出口／读的时候**真按分级过滤**——**今天没有任何过滤路径**」；sensitive_fields 那两条「**只是清单、不是已标**」；我们的判定**只有一维** —— **crates/aios-worldcore/src/governance/mod.rs:118-158** can_execute 只产出 allowed: bool ＋ step（Granted／Declared／Floor），**mod.rs:160-163** can_read **就是** can_execute（注释逐字「今天与 can_execute 同阶梯」）；我们的查询**没有天花板** —— **src/engine/query.rs:114-134** all() 把命中**全给它**。<br>来源2-A04：治理只有**阶梯**（三级 Granted／Declared／Floor，**src/governance/mod.rs:29-37**），**没有「等级」这个维度**；**src/governance/mod.rs:160-163** 自己写着「今天与 can_execute **同阶梯**（read_allow 那一格未落地）」；件头 **governance/mod.rs:14-18** 更明确自陈「本体 governance.read_allow 的 default 是 allow …… 它是**缺口**，不是**决定**」；crates/aios-worldcore 下 grep「privacy」＝ **0 命中**。 | 来源1-①.3：**不照抄它的 5 级**（那是加名字＝扩本体）；**照抄的是它的四条机制**，落在我们**已经声明的 3 级**上：① 记录多一格（Registration.fields 收下 marking，取值域＝我们那三级；★ 写口比较「新一版标记」与「现行那一版标记」，**降级 ⇒ 拒**，理由码 worldcore.Refuse.MarkingDowngrade，**照它的夹具形状**：拒、原值不变）；② 判定多一维（Governance 加 ceiling_of ＋ fn can_see(&self, who, marking) -> Admit<()>；Ruling 加一格 marking: Option<Marking>）；③ 查询带天花板（Query 构造时**只接受治理面给的** ceiling；all() 先排除超天花板者，再算 count／聚合；返回值多一项 suppressed: usize，**只报计数、不泄 id**）；④ 每次过滤记一笔（notice／what=marking.filtered，params {suppressed}）。★ **一处我们做得比它细**：它把「等级」只挂在**对象**上；我们同时还有 governance.roles ⇒ ceiling_of 可以**按角色**给。<br>来源2-A04：给对象加**一格 privacy_class**（闭枚举）；can_read 从「转发 can_execute」改成**双判**（阶梯 AND 等级 ≤ 主体天花板）；查询侧加一条**不显式写就隐式套天花板**的规矩；★ 借它「**只升不降**」那条不变量 —— **降级要新建对象**。 | 来源1-①.4：governance/mod.rs（加一维 ＋ 一个口）／engine/query.rs（加天花板与 suppressed）／core/types.rs（Marking 闭集）／engine/store/*（写口比降级）；**不动外部**。<br>来源2-A04：改 **3-4 个件**（governance/mod.rs／core/types.rs／query.rs），**不动外部**。 | 一致「★ **要**（提案）」：来源1-①.4「★ **要**（给类加 marking 格、把 markings.levels 与它对齐）⇒ **属提案**」／来源2-A04「★ **要（写成提案）**—— 要加 privacy_class 栏与主体的天花板来源。★ 这正是我们自陈缺口的那一格」。 | 高（来源1-①.5）／★★★ 高（来源2-A04）<br>★ **并列（词汇）**：来源1-①.3「**不照抄它的 5 级**…落在我们**已经声明的 3 级**」（PUBLIC／INTERNAL／CONFIDENTIAL）／来源2-C06 括注「**A04 只借 PUBLIC／INTERNAL／SENSITIVE 那几档**与「只升不降」」—— 待裁，见 附二 第 8 条 |
| **H09**<br>（仅来源2-A08；★ 来源1 **无对应条**） | 闭词汇查询语言（只有 and、无 eval、无 plugin）＋ 预算 ＋ 确定性计划 | 来源2-A08：**02_query_view_language.md:37**「**Closed vocabulary.** Every keyword and operator is enumerated in §3. There is no eval, no plugin, no user-defined function.」；**02:96**「and is the only logical conjunction; or is intentionally absent. ... This bounds engine complexity.」；**02:127**「Fields outside this list are not queryable in rev.2.」；**02:254-261** 查询预算四条（5s／256MB／10MB 或 10 000 行／1 000 000 行扫描）；**02:41**「Every query has a deterministic execution plan accessible via ExplainQuery.」 | 来源2-A08：**src/engine/query.rs:12-13** **自己写着**「今天本面的谓词词汇**只有『某一格 ＝ 某个值』一种**（可查的格＝信纸上的任意字符串格）；它那套多出来的几样（范围／集合／模糊）今天**没有落点**，如实登记。」⇒ 缺：in／范围／contains／exists／聚合／时间旅行／预算／计划。 | 来源2-A08：给 Query 的谓词枚举**扩两档**（∈ 集合、范围），保持「**闭集 ＋ 多条是与**」；加一个 explain() 出确定性计划。 | 来源2-A08：改 **1-2 个件**（src/engine/query.rs 单件即可起步），**不动外部**。 | 来源2-A08：**不要**（查询词汇是引擎的）；★ 但它 02:127 那句「**可查的格必须是一张闭清单**」可落成我们 ontology 的一条 —— 那就**要**动（提案）。 | ★★ 中（来源2-A08，★「它 02:96『**or 故意不做**』与我们闭词汇同向，是最该先借的一条纪律」）<br>★ 与 H08（天花板过滤）／H05（时间旅行）**相邻**，但本条独有部分是**闭词汇 ＋ 预算 ＋ explain** |
| **H10**<br>（来源1-⑨／来源2-A07） | 恢复面：只依赖哪几层写死（把我们「核心不靠 AI」机器化） | 来源1-⑨.1：**00_overview.md:16**「Recovery can inspect objects without the Cognitive Core.」；**01_object_model.md:390-400** 恢复七件（Enumerate objects／Verify chunk hashes／Inspect pointer history／Roll a pointer back to a verified version／Rebuild semantic indexes from object metadata／Quarantine corrupt versions／Mark transactions as forcibly aborted）＋「The recovery path depends on **L1 and L2 only**. No L3+ services, no LLM, no Web UI, no KDE session.」；**01:544-545**「no_LLM_invoked: true」；**04_implementation_space.md:107-109**「Read WAL from last checkpoint.」／「For each entry … replay.」／「For pending transactions older than orphan TTL …, abort and emit evidence.」；**05_namespace_layout.md:383**「Operator workflows in normal mode are read-only and observation-grade.」；**00_overview.md:30**「05_recovery_modes.md ｜ normal / safe_readonly / repair / quarantine / reindex modes ｜ SHELL」（★ 状态是 SHELL＝**还没成规格**）。<br>来源2-A07：**01:400**／**00:16**／**01:544**。 | 来源1-⑨.2：**没有「恢复」这一面**（搜 mode 只命中 instance_mode）；★ 但**七件里我们已经能自己做三件** —— Enumerate objects：**projection.rs:47-50** Projection.keys()／**read.rs:70-73** Store::keys()；Verify chunk hashes（＝查账的完整性）：**ledger.rs:158-160**／**seal.rs:98-144**；Rebuild semantic indexes：**read.rs:53-56** Store::project()／**projection.rs:96-112**；另外四件**没有口**（Inspect pointer history／Roll a pointer back ＝ H02；Quarantine corrupt versions ＝ H06；Mark transactions as forcibly aborted ＝ H03）。<br>来源2-A07：我们口径是「**核心不靠 AI**」（书里），但**没有成文的恢复模式，也没有「恢复面只依赖哪几层」的清单**；crates/aios-worldcore 下 grep「恢复模式｜recovery_mode」＝ **0 命中**。 | 来源1-⑨.3：1. **一个模式维**（闭集，照 00:30 那五个词）Normal／SafeReadonly／Repair／Quarantine／Reindex，恢复模式下**只读**；2. **一个恢复出口** engine/recovery.rs → RecoveryReport { objects, retired, quarantined, pointers_rolled_back, txns_aborted, ledger_ok }（**纯读数**，不带 LLM、不带 UI、不依赖任何 L3+ 件）；3. ★ **一条今天就能立的总判据**：在恢复出口的依赖闭包里搜 aios-cognitive／aios-renderer-*／kde／web，命中 ⇒ 红（★ 今天就能绿，而且真的能红）★ **评审后修 · 测试席 G-06**：「**真的能红**」是**对一条尚未存在的判据的可红性断言 —— 是推的、未反向验证**；★ 立这条判据时**必须先写会红的反例**（本仓硬约束 9）；4. **恢复次序照我们的账**五步；5. Quarantine 模式接 H06；Repair 模式接 H02。<br>来源2-A07：不需要新数据结构 —— **要的是一条成文判据 ＋ 一条会红反例**（反例 ＝ 在恢复路径里插一次 LLM 调用）。 | 来源1-⑨.4：**新增 engine/recovery.rs**（一个面）＋ lib.rs 挂一行 ＋ 一条判据脚本；**不动外部**。<br>来源2-A07：★ **低**（先立判据）；要真做恢复模式则中。 | 一致「**不动**」：来源1-⑨.4「**不动**（若要把 mode 写进本体 ⇒ 提案，**不必需**）」／来源2-A07「**不要**（它是流程／判据，不是本体的格）」。 | 高（来源1-⑨.5，★「它是九条里**唯一「今天就能做、判据今天就能立」**的一条」）／★★ 高（来源2-A07）<br>★ **依赖**：RecoveryReport 的 quarantined／txns_aborted／pointers_rolled_back 三项要等 **H06／H03／H02**；**判据那一条今天就能立** |
| **H11**<br>（仅来源2-A12；★ 来源1 **无对应条**） | 每次变更都签名（★ 已知缺口，★ 受禁区约束） | 来源2-A12：**crates/aios-fs/src/evidence_emit.rs:35**「Async append-only sink for sealed, signed AIOS-FS evidence receipts.」（★ **评审后修 · 甲-02：原文无加粗**；现取逐字：`/// Async append-only sink for sealed, signed AIOS-FS evidence receipts.`）；**evidence_emit.rs:44-48**「async fn append_signed(&self, builder: ReceiptBuilder, signing_key: &SigningKey) -> Result<EvidenceReceipt, EvidenceError>;」；**evidence_emit.rs:106**「let receipt = builder.seal_signed(previous.as_ref(), signing_key)?;」；**evidence_emit.rs:148**「Return the Ed25519 verifying key for receipts emitted by this emitter.」 | 来源2-A12：★ 我们**自己写着**没接 —— **src/engine/ledger/seal.rs:10-11**「它那层 **Ed25519 签名我们没接**：签名要一套密钥主体，我们的账今天只登记『谁』（Who），没有密钥可签 —— 那一段就是没接上。」（**ledger.rs:12-16** 同）；crates/aios-worldcore 下 grep「ed25519」＝ **0 命中**，grep「signing／signature」＝ **0 命中**。 | 来源2-A12：账的封条从**纯 BLAKE3 链节**变成 **BLAKE3 链节 ＋ 一次签名**（Seal::hash 之后再过私钥）；需要一个**密钥主体**（今天的 Who 是自填字符串，本体自陈「它不证明身份」，见 **store.rs:62**）。 | 来源2-A12：★ **中-高** —— 要引入密钥设施 ＋ 一个密钥主体概念，且**动我们的账封条格式**（封条一改，旧账全断链 ⇒ 这是**换世界身份**级的改动）。 | ★ **要（写成提案）** —— 要加「密钥／主体身份」这一节（来源2-A12）。 | ★★★ 高（已知缺口，来源2-A12），但 ★★ **受禁区约束 —— 见 §七 C01／C02，这一条不许当成「顺手借进来」**；★ 见 §五·2 未裁 |
| **H12**<br>（仅来源2-A11；★ 来源1 **无对应条**） | 凡删除必留证（「GC 绝不静默」那条**纪律**，不是块） | 来源2-A11：**01_object_model.md:197**「GC is **not silent**. Each GC pass writes an evidence record (evr_<ULID>) recording chunk IDs reaped and bytes freed.」；**01:198**「Operator policy may configure scheduled GC windows or ad-hoc GC; the runtime never deletes chunks without an evidence-logged trigger.」；**01:195**「A chunk is GC-eligible when ref_count = 0 AND no staged transaction holds it.」 | 来源2-A11：我们没有块、也没有回收 —— 因为**我们只追加**（**src/engine/ledger.rs:5**「没有改一笔／删一笔／插一笔的口」）⇒ 「块」这一半**不适用**（见 §七 C03／C12 一带）；**真正值得借的是那条纪律**：**凡删除必留证**。 | 来源2-A11：不需要块结构 —— 落成**一条判据的形状**：账里任何「清除／清理」类动作都必须挂一条自己的证（连 H03）；它 01:197 那句「the runtime never deletes chunks without an evidence-logged trigger」可以直接抄成我们的一条会红判据。 | 来源2-A11：借纪律 ＝ **低**（一条判据）；真做块 ＝ **高**（且与我们只追加口径冲突）。 | 来源2-A11：**不要**（只借纪律）；若真要块结构则要（提案）。 | ★★ 中（来源2-A11，纪律高、结构低） |
| **H13**<br>（仅来源2-A13；★ 来源1 **无对应条**） | 降级必须显式、必须失败关闭（fail closed） | 来源2-A13：**05_namespace_layout.md:518**「Failure modes — all fail closed:」（★ **评审后修 · 甲-01：原文无加粗**）；**05:522**「CatalogSignatureFailure → resolver enters degraded mode (resolves only the closed enum subset; refuses any call requiring reserved-id existence check).」（★ **评审后修：原文无加粗** —— 与甲-01／甲-02 同形，本席现取补）；**05:520**「ResolverInternal → caller receives ResolutionError with empty code; engine emits alert.」 | 来源2-A13：★ 我们**已知有一处静默降级** —— **verify/allowed_upstream_edits.txt:18**「crates/aios-fs/src/in_memory.rs # ★ 静默降级的如实登记注释（2 行；**T-30 待办：改成「不登记即拒」**）」⇒ 我们**登记了**它，**还没改**。★ **评审后修 · 乙-04 ＋ 本席现取补记**：**同一件里另有 ≥2 处同形态兜底、登记面未记** —— 「crates/aios-fs/src/in_memory.rs:1016」「Some("SENSITIVE" | _) | None => PrivacyClass::Sensitive」（**未知／缺隐私级 ⇒ 落到 Sensitive**）与「:1046」「Some("SYSTEM" | _) | None => ScopeBinding { scope_kind: ScopeKind::System … }」（**未知／缺 scope ⇒ 落到 System**）⇒ ★ 原文「已知有**一处**」**报小了**；★ 这两处**要不要一并登记／一并改，待人裁**（登记 ≠ 判违规）。 | 来源2-A13：不需要新结构 —— 要的是**一条会红的判据**：「凡降级分支，必须显式返回一个码，不许静默放行」；反例 ＝ 把一个降级分支改成返回 Ok。 | 来源2-A13：★ **低**（一条判据 ＋ 修一处口）。 | 来源2-A13：**不要**。 | ★★ 中-高（来源2-A13，它是**已有欠账的形状化**） |

### §三·1 总表小计

- **13 行**（H01–H13）；**合并掉 9 组重叠**（来源1 的 9 条与来源2 表 A 的 9 条一一对应并成一条）；来源2 表 A 里**来源1 没有对应条**的 4 条（A08＝H09／A11＝H12／A12＝H11／A13＝H13）单列。
- 来源2 表 B（10 条）进 §六；表 C（13 条）进 §七 —— 两者**不占 H 编号**（它们不是缺口）。

---

## §四 建议的先后（合过之后重新排，并说明为什么这个顺序）

★ 三档口径：第①档 **今天就能做（不动权威件）**；第②档 **要提改动（动我们的件但不动 ontology.json）**；第③档 **提案（要动 ontology.json 或动对外签名）**。
★ **评审后修 · 丙-G1：「不动权威件」全文未定义「含不含外部件」** ⇒ ★ **H13 的档位无法判定**（现取：H13 要改**外部**「crates/aios-fs/src/in_memory.rs」）。★ 两种读法**并列、待人裁**：**读法甲** ＝ 「权威件」**只指我方件** ⇒ H13 属第①档；**读法乙** ＝ **含外部**（外部由 C1 判据盯着、改一笔要逐笔登记）⇒ H13 应降**第②／③档**。
★ 每档内按依赖排序；写明「谁是谁的前提」。
★ **本序是判断，不是读数**（来源1 §10.3 逐字：「**优先级是判断，不是读数**」）。

### §四·1 第①档 —— 今天就能做（不动权威件）：3 条

| 序 | 编号 | 一句话 | 谁是谁的前提 | 依据（逐字出处） |
|---|---|---|---|---|
| 1 | **H10** 恢复面依赖闭包 | 新增一个恢复出口 ＋ 一条「依赖闭包里不许有 L3+ 件」的判据 | **无前提**（判据今天就能立）；★ RecoveryReport 里 quarantined／txns_aborted／pointers_rolled_back 三项**要等 H06／H03／H02** | 来源1-⑨.5 逐字「★ **它是九条里唯一「今天就能做、判据今天就能立」的一条**」；来源2-A07 逐字「**不要**（它是流程/判据，不是本体的格）」「★ **低**（先立判据）」 |
| 2 | **H13** 降级必须失败关闭 | 一条「凡降级分支必须显式返回一个码」的判据 ＋ 修一处既有欠账 | **无前提** | 来源2-A13 逐字「★ **低**（一条判据 ＋ 修一处口）」「**不要**」 |
| 3 | **H12** 凡删除必留证 | 一条「凡清除/清理类动作必须挂一条自己的证」的判据 | **无前提**；★ 证要挂账 ⇒ 与 H03 相邻 | 来源2-A11 逐字「借纪律 ＝ **低**（一条判据）」「**不要**（只借纪律）」 |

★ 补充（来源1 §10.1 逐字）：「**第 4 名（差一点进前三）＝ ⑨ 恢复清单**：它是**唯一「今天就能立判据」**的一条，成本最低；若人力允许，**它可以和第 1 条并行**（互不碰同一批文件）」—— 那里说的「第 1 条」＝ 来源1 §10.1 第 1 名 ⑦ 路径（＝本件 **H01**）。

### §四·2 第②档 —— 要提改动（动我们的件但不动 ontology.json）：6 条

| 序 | 编号 | 谁是谁的前提 | 依据（逐字出处） |
|---|---|---|---|
| 1 | **H02** 指针搬动模型 | ★ **是 H03、H04、H06 的共同前提** | 来源1-②.5 逐字「却是第四条（事务）与第八条（冲突）**共同的前提**」；来源1-⑤.5 逐字「**依赖第二条**（没有指针就没有「搬到哪」）」 |
| 2 | **H03** 事务（一单原子 ＋ 两链） | 前提 ＝ **H02**；**同时是 H04 的前提** | 来源1-④.5 逐字「⇒ 排在第二条之后」「★ 而且**它是第八条的前提**：没有「一单」，就谈不上「一单里的多个 CAS 全成或全败」」 |
| 3 | **H04** 冲突·砖一（CAS expected 那半步） | ★ **评审后修 · 丙-G2：前提 ＝ H01 ＋ H02 ＋ H03** —— 现补 **H01**（来源1 §10.2 依赖图逐字：「⑦ 路径 ──┐」「├─► ⑧ 冲突」「② 指针 ──┤」）；★ 原文**漏记 H01**，而 §四·3 H01 栏**已写**「它同时是 H04 的一条前提」⇒ **件内两处相抵**，现补齐 | 来源1-⑧.5 逐字「⇒ **我建议只先吃砖一**（CAS 那一块，几乎零成本），完整的一套（冲突对象／合并策略／TTL）**等第二、四条落地之后再吃**」；来源1-⑧.4 逐字「**砖一、砖二不必动**」 |
| 4 | **H06** 隔离坏版本 | 前提 ＝ **H02** | 来源1-⑤.5 逐字「它是账完整性缺的**最后一段**……**依赖第二条**（没有指针就没有「搬到哪」），所以排在它之后」 |
| 5 | **H05** 快照一致读 | **无前提**（可与 H02 并行） | 来源1-③.3 逐字「fold 本来就是纯函数（projection.rs:96-112）」；来源1-③.4／来源2-A05 两处都「不动 ontology」 |
| 6 | **H09** 闭词汇查询 | **无前提**（单件起步）；★「天花板过滤」那一半与 H08 相邻 | 来源2-A08 逐字「改 **1-2 个件**（src/engine/query.rs 单件即可起步）」 |

★ **本档 5 条的档位本身有未裁**（★ **评审后修 · 丙-G4：原文写「4 条」、漏算 H09**）：**H02／H03／H04／H06／H09**。
   - **H02／H03／H04／H06**：来源2 说**要动 ontology.json**（⇒ 若按来源2 口径，这几条应升入第③档）；
   - **H09**：来源2 本行「动不动 ontology.json」栏**两说并存** —— 前半「**不要**（查询词汇是引擎的）」，同栏后半点名它「02:127」「**可查的格必须是一张闭清单**」**可落成我们 ontology 的一条 ⇒ 那就**要**动（提案）**。
★ **并列两处、待裁**，见 §五·3 与 附二 第 2／3／4／5 条。

### §四·3 第③档 —— 提案（要动 ontology.json 或动对外签名）：4 条

| 序 | 编号 | 一句话 | 前提 | 依据（逐字出处） |
|---|---|---|---|---|
| 1 | **H01** 路径分类 | ★ **唯一会动对外签名的那一条**（Who::new 要变成可失败）★ **评审后修 · 丙-G3**：「**对外签名**」全文**未定义** ⇒ **这句今天不可判**（②档三条也动 `pub` 写口／读口）。★ 本件按**来源1 的原话**读 ＝ 「`Who::new` 从**不校验**变成**可失败**」（**调用点会红**的那种改动）；★ **要不要给「对外签名」下一个定义，待人裁** | **无前提**（它是「地基」）；★ 来源1 §10.2 依赖图里 ⑦ ─► ⑧ ⇒ 它同时是 H04 的一条前提 | 来源1 §10.1 逐字「**第 1** ｜ **⑦ 路径分类（AiosPath／NamespaceClass）** ｜ ★ **地基**：world:// 后面今天**是自由字符串**……等于**名字没有法律**」「★ 而且它是九条里**唯一必须动签名**的（Who::new → 可失败），**越晚改越贵**」 |
| 2 | **H08** 隐私等级 ＋ 天花板 | 给类加 marking 格／加 privacy_class 栏与天花板来源 | **无前提**（来源1 §10.2 逐字「① 隐私（动 governance + query）─── **独立，可并行**」） | 来源1-①.4「★ **要**……⇒ **属提案**」；来源2-A04「★ **要（写成提案）**」 |
| 3 | **H07** 生命周期 | 给所有类加 lifecycle 格 | ★ **与 H08 同一次本体提案一起提** | 来源1-⑥.5 逐字「★ 若要动本体，则**并入第一条那次本体提案一起提**（同为「给类加格」）」 |
| 4 | **H11** 签名 | 加密钥／主体身份一节 ＋ 动账封条格式 | ★ **受 §七 C01／C02 未裁约束 —— 未裁前不许动** | 来源2-A12 逐字「★★★ **高（已知缺口）**，但 ★★ **受禁区约束 —— 见 C01／C02，这一条不许当成「顺手借进来」**」；来源2 §六 第 11 条逐字「本席**只报冲突，未裁**」 |

★ **特别标注：唯一会动对外签名的 ＝ H01**（来源1-⑦.5 逐字：「★ 它也是九条里**唯一必须动签名**的一条 ⇒ **越晚改越贵**（今天 Who::new 的调用点还少）」）。**越晚改越贵的理由（逐字）**：「今天 Who::new 的调用点还少」—— 即**调用点越多，改一次要动的面越大**；来源1 §10.1 把它排在第 1 名，逐字：「★ **地基**：world:// 后面今天**是自由字符串**（types.rs:18-21 逐字「不做校验」），等于**名字没有法律**。闭集词表 ＋ 目录版本号这两样，**我们已经有工具**（seal.rs 的 blake3 ＋ 规范压平）**却一次没用**。」

## §五 明确是提案、要人裁的清单

★ 本节的 **§五·1** ＝ §四 第③档**逐条**；**§五·2** ＝ 那条**已知冲突**（**只列未裁**）；**§五·3** ＝ **档位本身未裁**的 4 条；**§五·4** ＝ 来源件**自己标了「待裁」**的 3 条。

### §五·1 第③档逐条（动哪个权威件／动什么／为什么必须动／有没有替代）

**H01 路径分类（来源1-⑦／来源2-A09）**

- **动哪个权威件**：我们的件 **core/types.rs 的对外签名**（Who::new）；★ 另 ontology 侧一项（闭集词表写不写进本体）另算。
- **动什么**：来源1-⑦.4 逐字「★ core/types.rs（**签名改动**：Who::new 不校验 ⇒ 加 Who::parse -> Admit<Who>，或**退一步**只加一个 validate_subject 口而**保留** Who::new）／新增 core/namespace.rs（解析 + 闭集 + 版本号）」。
- **为什么必须动**：来源1-⑦.5 逐字「★ 这是**「一个事实一个载体」的地基**——world:// 后面今天**是自由字符串**，等于**名字没有法律**」。
- **有没有替代（不动也能做的降级路径）**：★ **有，来源件自己给了** —— 同上「**退一步**只加一个 validate_subject 口而**保留** Who::new」；★ ontology 那一项也有降级：来源1-⑦.4 逐字「**可以不写**：先落在代码里当门禁（和今天 check_shape 同一层）」。
- ★ **越晚改越贵的理由**（逐字）：来源1-⑦.5「⇒ **越晚改越贵**（今天 Who::new 的调用点还少）」；来源1 §10.1「它是九条里**唯一必须动签名**的（Who::new → 可失败），**越晚改越贵**」。

**H08 隐私等级 ＋ 天花板（来源1-①／来源2-A04）**

- **动哪个权威件**：**crates/aios-ontology/data/ontology.json**（本体）。
- **动什么**：来源1-①.4 逐字「★ **要**（给类加 marking 格、把 markings.levels 与它对齐）⇒ **属提案**」；来源2-A04 逐字「★ **要（写成提案）**—— 要加 privacy_class 栏与主体的天花板来源。★ 这正是我们自陈缺口的那一格」。
- **为什么必须动**：来源1-①.5 逐字「理由：**缺口是我们自己写着「执行面无」的那一格**——分级已经声明，却**一条过滤路径都没有**（read_allow.default 也是 allow）。合它不需要任何新依赖，且一次性给「读」立起**第一条真闸**」。
- **有没有替代（不动也能做的降级路径）**：★ 来源件**未给**「不动本体」的降级路径（来源1 只给「不照抄它的 5 级、落在我们已声明的 3 级」，**仍然是给类加格**）。**如实写：来源件未列替代。**

**H07 生命周期（来源1-⑥／来源2-A10）**

- **动哪个权威件**：**ontology.json**（本体，给所有类加 lifecycle 格）。
- **动什么**：来源1-⑥.4 逐字「★ **要**（给所有类加 lifecycle 格 ⇒ **提案**）」。
- **为什么必须动**：来源1-⑥.5 逐字「★ 它是**声明面一眼可见的参差**（9 类里 4 类有 retired、其余没有），而且**正好撞上「同词两义」**」。
- **有没有替代（不动也能做的降级路径）**：★ **有，来源件自己给了过渡期那条** —— 来源1-⑥.4 逐字「**过渡期**可先用「本内核最小指认格」那条既有豁免（同 name，见 instances.rs:114）」；★ 另来源1-⑥.5 逐字「若要动本体，则**并入第一条那次本体提案一起提**（同为「给类加格」）」。

**H11 签名（来源2-A12）**

- **动哪个权威件**：**ontology.json**（加密钥／主体身份一节）＋ **我们的账封条**（engine/ledger/seal.rs）。
- **动什么**：来源2-A12 逐字「账的封条从**纯 BLAKE3 链节**变成 **BLAKE3 链节 ＋ 一次签名**（Seal::hash 之后再过私钥）；需要一个**密钥主体**（今天的 Who 是自填字符串，本体自陈「它不证明身份」，见 store.rs:62）」。
- **为什么必须动**：来源2-A12 逐字「★★★ **高（已知缺口）**」；我们自陈未接的原文见 §三 H11 行（ledger/seal.rs:10-11）。
- **有没有替代（不动也能做的降级路径）**：★ 来源件**未给**「接签名」的替代路径；★ 但**同批**另给了两条**不依赖签名**的判据路（H12 的「凡删除必留证」纪律 ＋ H13 的 fail-closed 判据）—— 它们**可以不动封条就先立**。
- ★ **未裁**：见 §五·2。

### §五·2 ★ 已知冲突（未裁）：签名（要接）与「不接 DID／VC 密码学面」（不能借）

- **一边（要接）**：来源2-A12 逐字「★ 我们**自己写着**没接 …… ★★★ **高（已知缺口）**，但 ★★ **受禁区约束 —— 见 C01／C02，这一条不许当成「顺手借进来」**」。
- **另一边（不能借）**：来源2-C01 逐字「**07-待审 §五 第 8 条**逐字：「DID／VC 的密码学面 —— **今天没有任何签名设施**；借了就是『没做到写成做到了』」」「★ **不能借**（★ 与 A12 是一对：**A12 是缺口，C01 是不能从它那儿顺手借的那一面**；两者不许互相抵消）」。
- ★ **来源2 自己怎么标**：§六 第 11 条逐字「**A12（签名）与 C01（不能借密码学面）的关系，本席只报冲突，未裁** —— 「加一个签名密钥设施」算不算 C01 禁区，**这是人的决定**（本仓硬约束 6）」。
- ★ **本件照抄这条「只报冲突、未裁」**：**不替作者选**。（另见 §七 C01／C02 两条原文。）

### §五·3 ★ 档位本身未裁的 4 条（来源2 说**要动 ontology.json** ⇒ 若按来源2 口径应升第③档）

| 编号 | 来源1 的口径（逐字） | 来源2 的口径（逐字） | ★ **当前本体／代码的现取读数**（★ 评审后修 · 丙-G6／G7 补：原文只并了两处来源，**缺这一方**） |
|---|---|---|---|
| **H02** 指针 | 「**不动**（指针是我们内核的读侧派生物，不是本体声明的类）★ 若要把「指针」写进本体 ⇒ **提案**，非必需」 | 「★ **要（写成提案）**—— 今天的本体没有「指针」这一类」 | ★ 现取 `ontology.json:9789-9791` 逐字「"current_pointer_id": { "判": "★ 冲突：不进语义面"，"说明": "它是「指针＝事实源」；我们口径「个体由本体得出、账本只是记录」" }」 ⇒ ★ **本体自己已把「指针进不进语义面」判成「不进」** ⇒ **支持来源1 的「不动」那一侧**；★ 但**仍并列、不替作者选** |
| **H03** 事务 | 「★ **可能**：若要把「事务」立成一个**类**或往 families 加一族 ⇒ **提案**。**不必需**：可用 change 族 ＋ what=txn.commit」 | 「★ **要（写成提案）**—— 今天的 envelope 只有 seq／who／at／…，账的族是 change／act／notice／job 四族，**没有「事务」这一栏**」 | ★ 现取**本体内部不自洽**（丙-G7；本席复核：**确实如此**）：「ontology.json:21」逐字「"kind": "enum(change, act, notice)  # 三个家族"」，而 `families` **实为四族**（现取键：change／act／notice／job）⇒ ★ 「事务」这一栏**今天确实没有**（**部分支持来源2**）；★ 且**本体自己这一处「三族／四族」要先修** —— **要不要改、怎么改由人定** |
| **H04** 冲突 | 「★ **可能**（merge_policy 进类定义 ⇒ 提案）；**砖一、砖二不必动**」 | 「★ **要（写成提案）**—— 要加「冲突」这一类／这一族」 | ★ 现取本仓 `crates/aios-worldcore/src` **全树**：「conflict」／「冲突」 **0 命中** ⇒ **支持来源2 的事实前提**（我们**没有**冲突面）；★ 但「因此要不要往本体加这一类」**仍待人裁** |
| **H06** 隔离 | 「**不动**（notice 族今天**已经在册**）」 | 「★ **要（写成提案）**—— 本体的 governance 节今天只有 tombstone（碑），没有「隔离」这一档；且 record 五要素里没有版本状态」 | ★ 现取本体的 `governance` 节：**有 `tombstone`**、**无 `quarantine`／无「隔离」** ⇒ **支持来源2 的事实前提**（今天只有碑）；★ 另：来源1 说「notice 族今天已经在册」—— ★ 现取 `families` 键**确含 `notice`** ⇒ **来源1 那句有现取支持** |

★ **并列两处、标「待裁」，本件不选。**
★★ **评审后修 · 丙-G5**（本席现取复核：**评委对**）：原文写「**两条都承认**『砖一／判据那半步不必动本体』」—— ★ **不成立**。现取：**来源1**「砖」**9 处**／「不必动」**1 处**；**来源2「砖」0 处／「不必动」0 处** ⇒ ★ **只有一个来源说过**（来源1-⑧.4 逐字「砖一、砖二不必动」）。
⇒ ★ **「砖一放第②档」这条分档依据被抽掉**，本件**不再据此分档**：★ **砖一的档位（①／②／③）＝ 待裁**（★ 那是**替作者选**，本件不选）。★ 另见 附二 第 4 条（该条同一句也写错了，**一并修**）。

### §五·4 ★ 来源件自己标了「待裁」的 3 条（照抄，不重复计）

来源2 §六 第 12 条逐字：「**C03／C10／C12 三条本席标了「待裁」** —— 它们**不是**「一定不做」，而是「与我们今天的口径冲突，本件只报冲突」。」⇒ 这三条在 §七 **逐条保留**，并在 附二 第 12 条登记。

---

## §六 已有对应（不是缺口，防误读）

★ **开头（来源2 §四 逐字）**：「★ 用途：**防止下游把「已有的」写成「该加的」**。」
★ 本节 10 条**不进 §三 总表**、**没有 H 编号**（它们**不是缺口**）；对照时只当「我们已经有了」的证据。

| # | AIOS-FS 有什么（出处） | **我们的对应件／行** | 对应到什么程度（如实） |
|---|---|---|---|
| **B01** | 只追加、且**证据成链**（01_object_model.md:413「Every transaction commits an evidence record; GC, quarantine, retire all logged.」） | src/engine/ledger.rs:37-50（Ledger 结构：rows ＋ seals ＋ head ＋ **families:47** ＋ **by_family:49** —— ★ **评审后修 · 乙-02：原文漏这两格，报小了**）／src/engine/ledger/seal.rs:98-144（check_chain 逐笔重算 ＋ 逐节核对前驱，第一处就报位次）／ledger.rs:158-160（verify） | ★ **形状已对**（只追加 ＋ 链节 ＋ 第一处报错）；**差签名**（见 A12）与**持久化** |
| **B02** | 复合键二级索引（04_implementation_space.md:78-89 列族；01 §7.3 按 ref 扫） | src/engine/ledger/index.rs:14-17（FamilyIndex ＝ (族, 序号) 的 BTreeSet）／index.rs:26-32（前缀扫，扫到别族就停） | ★ **组织法已对**（复合键 ＋ 前缀扫 ＝ 追加序）；差「落在磁盘」 |
| **B03** | 默认拒（05_namespace_layout.md:31「**I4 — Default-deny cross-group access.**」；01:382「Broad host writes ... are denied by default.」） | src/governance/mod.rs:74-84（permissions.default **必须显式**写 deny，缺或别的词 ⇒ 拒）／governance/mod.rs:150-157（地板 ⇒ 拒） | ★ **已对**；且我们多一条：**法律没写全 ＝ 拒** |
| **B04** | 闭词汇、未登记即不可查（02_query_view_language.md:127；05:28 I1 闭顶层） | src/engine/execute.rs:78-80（动作不在册 ⇒ 拒）／execute.rs:94-96（函数不在册 ⇒ 拒）／src/engine/ledger.rs:97-105（族不在册 ⇒ 拒） | ★ **已对**，且落在三处（动作／函数／族） |
| **B05** | 内容寻址用**全量** BLAKE3-256、**不许截断**（01_object_model.md:46-52「Chunk IDs **are not truncated**. ... chunk IDs require full collision resistance because they are persistent storage handles.」） | src/engine/ledger/seal.rs:87-92（digest ＝ blake3::hash(...).to_hex() ⇒ 64 位小写十六进制，**全量**） | ★ **已对**（且同样零新增依赖） |
| **B06** | 已提交内容**永不原地覆盖**，写产生新版本（00_overview.md:12） | src/engine/store.rs:11-17（三条口径：唯一原件是只追加序列）／store.rs:110-123（commit：只往尾部推）／store.rs:164（「更正一条 …… **旧版不动**：追加一行，折出来才是新的」） | ★ **已对** |
| **B07** | 不真删（01_object_model.md:83 RETIRED ＝「Logical removal」；03:229「Abandonment is **not** silent data loss」） | src/engine/store.rs:184-215（delete_as：记一笔 Tombstone，带 哪一条／谁／为什么；**原因为空 ⇒ 拒**） | ★ **对了一半**：碑 ＝ RETIRED 的一半；**缺**退役可读、清除、保留期（见 A10 ⇒ 本件 H07）。★ **评审后修 · 丁-D02／D03**：这句与 §三 H07 行「它**其实已经**是 RETIRED 的语义」**同件两说、原文互不登记** ⇒ ★ 两句**各自成立、射程不同**（H07 讲**碑这一笔的语义**，本条讲**能力面缺哪几样**）⇒ ★ **已登记进 附二 第 14 条**，**不合口径、不替作者选** |
| **B08** | 视图／索引**不是身份**、可重建（00_overview.md:14-15） | src/engine/store.rs:14-15（get/count 读的是**折出来的现状**，是派生物）／store.rs:76-83（缓存可丢，下一次读会重折） | ★ **已对** |
| **B09** | 每次判定必留痕（01_object_model.md:353「Every quarantine entry and exit emits an evidence record.」） | src/governance/mod.rs:39-47（Ruling）／governance/mod.rs:180-190（note：放行与拒绝**都留**）／governance/mod.rs:118-158（每答必留一条） | ★ **已对**（且我们写明：台账是**读数**、不是裁定本身，锁坏了不许因此改结论） |
| **B10** | 确定性（05:34 I7；02:40「Same query text + same as of snapshot → same result.」） | src/engine/query.rs:**9**（无 order_by 时**按键升序** —— ★ **评审后修 · 乙-03：原文写「:8-9」，现取该句在 L9；L8 是「缺席即假」**）／query.rs:212-221（会红反例 2：候选必须次序确定） | ★ **已对**（且**现取三条会红反例在册**：`query.rs:195`／`:212`／`:223` —— ★ 评审后修 · 测试席 G-02） |

★ 来源2 §四 末尾**单列的一条「照面但不完全对应」**（**逐字保留，防误读**）：它 **02:284-295** 的 **NL→query bridge**（「Natural-language goals reach the query engine only via S1.1」）与我们**已有**的翻译链动作名闸（crates/aios-cognitive/src/translator_engine.rs 的 gate_action_name，见 AGENTS.md／CLAUDE.md 现取基线）**同向**，但**不是同一件东西**（它管查询、我们管动作名）⇒ **不列 B、也不列 A**，如实标注。

---

## §七 故意不做（不是没实现，防误读）

★ 依据（来源2 §五 开头**逐字**）：「★ 依据：**AGENTS.md §四禁区（三条）** ＋ **ninedim/07-待审/2026-10-13-融合-六路参考与现在的活.md §五的 14 条「不能借」**。★ **不许**把这里的任何一条读成「该加」。」
★ **评审后修 · 丁-D05（本件现取复核：评委对）**：★ 上面那条**是来源2 的自述**，**不等于**本节 13 条的判据都落在那两处。现取逐条核：
   - **能指到那两处的 6 条**：**C01**（07-待审 §五 第 8 条）／**C04**（§五 第 7 条）／**C08**（§五 第 6／12 条）／**C12**（逐字「同 C04」）／**C05**（与 AGENTS.md §四 第 1 条「AI 只提议不执行」**同向**，**原文未点名**）／**C13**（同上，**原文未点名**）；
   - **真判据是「它的面我们没有／形状不符」的 6 条（＝不适用）**：**C02／C03／C06／C07／C09／C11**；
   - **指到表外第三源的一条**：**C10**（07-待审 §**四** 第 3 条 —— **不在**上面那两处之内）。
⇒ ★ 本件**不改各条的判据**（那是来源2 写的），**只把「依据」的射程写实**；★ 要不要把「依据」改成**逐条标注**，**待人裁**。

★ 本件如实登记一处**依据缺口**：任务口径另给了第三条依据「**作者 T-154 否掉语音**」；本件在两份来源件里逐字搜过 —— **「T-154」0 命中、「语音」0 命中** ⇒ 本件**不把它安到任何一条 C 上**（只列来源件写了的依据），并入 §八·4。

| # | 它有什么（出处） | 判据（为什么归 C） | 归类 |
|---|---|---|---|
| **C01** | **DID／VC 的密码学面**（01_object_model.md:329「signature mismatch」；05:554「Catalog descriptor is signed by the AIOS root (Ed25519)」） | **07-待审 §五 第 8 条**逐字：「DID／VC 的密码学面 —— **今天没有任何签名设施**；借了就是『没做到写成做到了』」 | ★ **不能借**（★ 与 A12 是一对：**A12 是缺口，C01 是不能从它那儿顺手借的那一面**；两者不许互相抵消） |
| **C02** | **块级加密／每对象加密／密钥管理**（04:154「AIOS-FS **does not implement** block-level encryption.」；04:158 per-object encryption **deferred**；04:164 key management **out of scope**） | 它**自己也说**在 rev.2 之外；且我们**今天无密钥设施**（同 C01）⇒ 借了就是「把 deferred 写成 done」 | ★ **不适用 ＋ 故意不做** |
| **C03** | **RocksDB 列族 ＋ SQLite(WAL) 目录 ＋ Tantivy 词法索引**（04:59-91；04:78-89 列族布局；04:192-201 参考硬件 8 核/16GB/NVMe） | 它**绑死三样具体存储**，且参考硬件与我们不符；我们的账**今天在内存**，口径是**不引第二套事实源**（同 B08：唯一原件只有一份） | ★ **不适用**（★ 可选的是它 04:105-113 的 WAL/checkpoint **形状**，本席**未核**，见 §八·2 第 7 条）／★ **待裁** |
| **C04** | **POSIX／FUSE 投影 ＋ 应用沙箱 portal**（04:26-35 决策；01 §14 全节） | **07-待审 §五 第 7 条**（Solid 的 HTTP 动词→权限映射不能借）的口径同源：「我们的入口是**信封与账本**，不是 HTTP 动词」—— 同一条道理落在 POSIX 上；且与我们「呈现维／事实维」分家冲突 | ★ **不适用** |
| **C05** | **CRDT 自动合并 ＋ ai_auto_promote 自动提升**（03:92-117 CRDT 六型；03:146-152 三前置条件） | ★ **与我们「AI 只提议不执行」口径相反**：它允许**自动提升**。⇒ **只能借「提议记录 ＋ 提升另过闸」那一半**（已列 A06），**自动那一半不许借**。★ 这是「顺手借错」最危险的一处 | ★ **故意不做（那一半）** |
| **C06** | **CLASSIFIED／运营商分级 ＋ 运营商可调保留期/TTL**（01:70 CLASSIFIED；01:86；03:219「Default: 30 days」） | 我们的世界本体里**没有「运营商」这个角色**；分级语汇与保留期参数属运营商面 | ★ **不适用**（★ A04 只借 PUBLIC/INTERNAL/SENSITIVE 那几档与「只升不降」） |
| **C07** | **/aios 顶层只有两个保留名 ＋ groups/users 三层结构**（05:28 I1；05:39-44） | 与我们 world://<ns>/<name> 的形状**不符**，且我们的名字空间**不分 group/user** | ★ **不适用**（★ A09 只借「闭枚举 ＋ 路径→类」那条**方法**，不借它的树） |
| **C08** | **proto／gRPC 服务面**（01 Appendix A IDL；02:357-369；04:45-55） | **07-待审 §五 第 6／12 条**同向（今天**没有对外网络面**；入口是信封＋账本）；我们的总线是 **Zenoh**，不是 gRPC | ★ **不适用** |
| **C09** | **Telemetry 12 项指标**（01:561-578；01:578「Subject is **never** a metric label.」） | 我们仓**没有 metrics 面**；★ 更关键：它**刻意不把主体记进指标**，而我们的账**就是要记「谁」**（core/types.rs:10-15）—— 两者是**两类不同的东西**，混借会把「指标」与「账」搅成一锅 | ★ **不适用** |
| **C10** | **VIEW 作为 ObjectKind 的一个值**（02:355「Views are themselves Objects with kind VIEW」） | 与我们「**呈现维／事实维**」分家冲突（说明-呈现维与事实维.md:18「改了它，世界变了吗 —— **没变**」）：★ 把「一个视图」登记成**世界里的一个个体**，正是「**不许把界面换皮叫成语义面板**」（07-待审 §四第 3 条）要拦的形状 | ★ **故意不做**（★ **待裁**：本席只报冲突，不下结论） |
| **C11** | **跨实例／多主分布式事务**（01:419；03:284） | ★ **它自己也在 defer**；我们连单机事务都还没有（A01/A06）⇒ 排在后面，今天**不适用** | ★ **不适用（它自己 defer）** |
| **C12** | **POSIX → AIOS-FS 导入映射表**（04:240-250：mode/permissions 映射自陈「lossy approximation」；symlink/hardlink/xattr 映射） | 我们**今天没有 POSIX 面可导**（同 C04）；且「有损近似」与我们「判据要求类型也对」的口径相反 | ★ **不适用**／★ **待裁** |
| **C13** | **AI 参与但只提议**（05:101「never to AI subjects」是它**禁止**的；03:154-156 允许 AI **提议**；02:295 NL 只能经 S1.1） | ★ 这一条**方向与我们一致**（AI 只提议、不自动执行），因此**不是缺口**；单列是为了**防止下游把它的「AI 参与」读成「我们缺 AI 参与」** | ★ **已有同向口径**（非缺口；★ 不列 A 也不列 B，避免重复计数） |

### §七·1 ★ 特别处理：CRDT 自动合并

- **它有什么**：来源2-C05 逐字「**CRDT 自动合并 ＋ ai_auto_promote 自动提升**（03:92-117 CRDT 六型；03:146-152 三前置条件）」。
- **判据（为什么归 C）**：来源2-C05 逐字「★ **与我们「AI 只提议不执行」口径相反**：它允许**自动提升**。⇒ **只能借「提议记录 ＋ 提升另过闸」那一半**（已列 A06），**自动那一半不许借**。★ 这是「顺手借错」最危险的一处」；归类逐字「★ **故意不做（那一半）**」。
- **来源1 的同一判断（一并保留）**：来源1-⑧.3 逐字「**CRDT：本批不引**，理由如实：03:94 那六种是**多副本合并**的词汇；我们**只有一个实例、账只追加**，引进来就是**空转**（还会多一份「谁是权威」的歧义）。★ 照它的纪律：**不声明就不许自动合并**——今天我们的类表里**没有任何一条声明** ⇒ **默认全拒**，这是**对的**。」
- ⇒ **本件只把「提议 ＋ 提升另过闸」那一半写进 H04**（来源2-A06 的「冲突不得静默丢弃」＋ 落一条账）；**「自动合并／自动提升」那一半不进任何 H 行**，标为**故意不做**。★ **不替作者裁**：来源件把「能不能借那一半」的判断留给下游（来源2-A06 逐字「可以只先立形状、不接调度（那是人的决定，本席不下）」）。

---

## §八 来源件自己列的「没核到」（全部保留 · 合并不丢）

### §八·1 来源1 的（来源1 §10.3，逐条照抄）

1. 「**一处未核到**：00_overview.md:30 那份 05_recovery_modes.md 状态是 SHELL，本席**在 L2_AIOS_FS/ 目录里没有找到该件**（目录里只有 6 件：00–05）⇒ 「五个模式的正式定义」本席**只见到这一行提纲**，**未见到规格正文**。」
2. 「**没有一行代码是改过的**：本件是设计，不是实现；**没有跑过任何构建**，没有读数可给。」
3. 「**没有做有效性论证**：每节给的「会红的反例」是**判据形状**，**不是已立好的判据**——它们**今天一条都不存在**。」
4. 「**没有对照过外部其它 crate**：本件只读了 L2_AIOS_FS 那 6 件与 crates/aios-fs/src；别的 crate（aios-policy／aios-evidence／aios-capability-runtime）里可能已有更好的同类设计，**本席未读**。」
5. 「**没有送评**：按硬约束「改的人不能自评」。」
6. 「**优先级是判断，不是读数**：第 10.1 那张表的「为什么」都指得到件与行，但**排序本身是我的判断**。」

★ 其中**只有第 1 条是明确的「没核到」**；其余 5 条是「本件不能证明」—— 本件**原样并列，不合并、不删**（对外**属于** §九）。

### §八·2 来源2 §六 的 12 条（逐条照抄）

1. **05 §17 golden fixtures（05:571-929，6 个夹具）未读** —— 本件没引用它；若下游要照它建判据，**本席未核**。
2. **02 §16 golden fixtures 正文（02:419-538，9 个夹具）未读** —— 同上。
3. **03 §17 golden fixtures（03:303-409，7 个）／04 §15（04:290-375，7 个）未读** —— 同上。
4. **01 Appendix A proto IDL（01:618-943）／02 Appendix A（02:749-897）／05 Appendix A（05:742-929）／03 Appendix B（03:430-515）全部未读** —— 本件的「逐字引」**只来自正文节，不来自 IDL 附表**。
5. **05 §7「Identity formats and reserved IDs」的正则表（05:200-231）未读** —— 故本件对「ID 形状」只说「有闭正则」，**不引具体正则**。
6. **05 §12 cross-spec touch-up（05:420-492）未读** —— 它列了 S0.1/S2.1/S2.3/S2.4/S3.1/S3.2 六处改动要求，**本件未核**。
7. **04 §15.1 WAL replay 夹具（04:292-305）未读** ⇒ ★ **C03 里那条「WAL/checkpoint 形状是否值得借」，本席只说「未核」，没下判断**。
8. **我方仓的其它 35 个 crate 未通读** —— 本件对「我们有没有」的判断**只覆盖 crates/aios-worldcore ＋ crates/aios-ontology ＋ crates/aios-fs 的 md5 比对**。★ 若 crates/aios-evidence（外部证据库）或别处已有签名/事务的现成件，**本席未核** ⇒ **不排除**我们别处已有等价物。
9. **/root/aios 不是 git 仓**（R1 逐字：fatal: not a git repository）⇒ ★ **无法核「这些代码对应外部哪个提交」**；射程 ＝ VM 那一刻的盘。
10. **本席未跑任何构建／测试**（VM 上没跑 cargo，宿主上没跑 python verify/check.py）⇒ 本件**没有任何「跑通了」的主张**。
11. **A12（签名）与 C01（不能借密码学面）的关系，本席只报冲突，未裁** —— 「加一个签名密钥设施」算不算 C01 禁区，**这是人的决定**（本仓硬约束 6）。
12. **C03／C10／C12 三条本席标了「待裁」** —— 它们**不是**「一定不做」，而是「与我们今天的口径冲突，本件只报冲突」。

### §八·3 来源2 §二 逐件的「没读哪儿」（照抄，一字不动）

| 件 | 字节 | 行 | **读了** | **没读**（如实） |
|---|---|---|---|---|
| 00_overview.md | 2,494 | 44 | ★ **全文（44/44）** | — |
| 01_object_model.md | 41,866 | 943 | **1-617** | **618-943**（Appendix A 完整 proto IDL，325 行） |
| 02_query_view_language.md | 44,090 | 897 | **35-420** | **1-34**（§1 Purpose）／**421-897**（§16 fixtures 正文、§17 telemetry 表、§18–§20 三处 cross-spec touch-up、Appendix A IDL） |
| 03_conflict_resolution.md | 25,799 | 515 | **18-303** | **1-17**（§1 Purpose）／**303-515**（§17 fixtures、§18 telemetry 正文、Appendix B IDL） |
| 04_implementation_space.md | 21,346 | 421 | **15-290** | **1-14**（§1 Purpose）／**290-421**（§15 fixtures、§16–§19） |
| 05_namespace_layout.md | 71,611 | 1,029 | **26-200**／**231-420**／**492-570**／**929-1019** | **1-25**（§1）／**200-231**（§7 身份正则表）／**420-492**（§12 cross-spec touch-up）／**571-929**（§17 fixtures ＋ §18–§20 ＋ Appendix A，358 行）／**1019-1029**（See also） |
| 代码 /root/aios/crates/aios-fs/src/ | — | 25 件 | ★ **全读** 11 件 ＋ 我方同源 2 件 | **未读**：error.rs／id.rs／object.rs／impl_space.rs／in_memory.rs（37KB）／query.rs／query_eval.rs／query_parser.rs／evidence_payloads.rs／service/ |

★ 来源2 §二 末尾逐字：「★ 未读部分里，**若下游要照它们的夹具建判据**，本席**没核过**：05 §17（571-929）、02 §16（419-538）、03 §17（303-409）、04 §15（290-375）。」

### §八·4 本件另外核过、但两份来源件里都没有的一条依据

- 「**作者 T-154 否掉语音**」：本件在**两份来源件**里逐字搜「T-154」「语音」—— **各 0 命中** ⇒ 这**不是**来源件给的依据，本件**未核到**，**不采信、也不安到任何一条 C 上**（见 §七 开头）。

---

### §八·5 ★ 评审补记（本件原来没有 · 评审席现取核出的读数）

★ 本节**不是两份来源件给的**，是**评审席**在评审轮里现取核出、而两份来源件与本件**都没登记**的读数（★ 评审后修 · 丁-D04／乙-04／测试席 G-02）。★ **一并登记，不改口径**。

| # | 读数（现取） | 出处 | 性质 |
|---|---|---|---|
| 1 | ★ **立碑之后，写没被拒** —— `retire()` 只从**现状**里摘掉键（`current.remove`）＋ 改索引，**不动** `last_write`（`:126` 写的 `last_write.insert` 在 `retire()` 之前、**碑后不再清**）⇒ 同一键**碑后仍可写**、**不触发**「已立碑」的拒绝 | `crates/aios-worldcore/src/engine/store/projection.rs:126` vs `:129-135`；`crates/aios-worldcore/src/engine/store/tests.rs:79-92` | ★ **读码推定（未跑）** |
| 2 | ★ **同件另有 ≥2 处静默降级、登记面未记** —— `:1016`（未知／缺隐私级 ⇒ `PrivacyClass::Sensitive`）／`:1046`（未知／缺 scope ⇒ `ScopeKind::System`） | `crates/aios-fs/src/in_memory.rs:1016／1046` | ★ **现取直读源码** |
| 3 | ★ **本仓在册的「会红反例」三条** —— `query.rs:195`／`:212`／`:223`（逐字带「会红反例 1／2／3」） | `crates/aios-worldcore/src/engine/query.rs` | ★ **现取直读源码**（与 §二·0 第 6 条**收窄后**的射程不冲突，见 附二 第 13 条） |

---

## §九 本件不能证明的事

- **没有跑过任何构建／测试；没有一行实现** —— 本件是合件，不是实现（来源2 §六 第 10 条、§七 第 3 条；来源1 §10.3 第 2／3 条）。
- **/root/aios 不是 git 仓 ⇒ 无法核对应外部哪个提交** —— 来源2 §一 R1 逐字「git rev-parse ⇒ fatal: not a git repository」；§六 第 9 条逐字「★ **无法核「这些代码对应外部哪个提交」**；射程 ＝ VM 那一刻的盘」。
- **我方其余 35 个 crate 未通读 ⇒ 不排除别处已有现成件** —— 来源2 §六 第 8 条逐字：「★ 若 crates/aios-evidence（外部证据库）或别处已有签名/事务的现成件，**本席未核** ⇒ **不排除**我们别处已有等价物」。
- **优先级／顺序是判断，不是读数** —— 来源1 §10.3 第 6 条逐字：「**优先级是判断，不是读数**：第 10.1 那张表的「为什么」都指得到件与行，但**排序本身是我的判断**。」（§四 的三档与档内次序同此性质。）
- **本件未跑任何门禁、未送评** —— 来源2 §七 逐条：「未改任何文件（除本件自身）」「未下任何结论、未签字、未估工期」「未跑构建／测试／门禁」「本件不进 ninedim/」「本席**不是评审席**，也未受命送评审」。★ **评审后修 · 测试席 G-07（时点缺口）**：本条以**合件时点**为限；★ 现取：本件**此后已送评**（五席；提交 `f687411` ＋ 席位表 `6e1640d`）⇒ 「**未送评**」在评审之后**已过期**。★ 另 · **测试席 G-08**：**评审有效性本仓今天没有机器判据**（本仓 `verify/check.py` 现取只有 **C1–C7**；**没有** `check_panel`／`check_division`／`check_team`）⇒ 五席的「评委不是写者」「写入范围零重叠」**只能人工核** —— ★ **登记 ≠ 判违规**。
- **两份来源件的「没核到」原样保留在 §八**：本件**没有**替它们补核（补核会引入新主张，违「只合不改」）。

---

## 末尾 · 交叉核对表

### （a）来源1 的 9 条 → 总表编号

| 来源1 | 主题 | 总表编号 |
|---|---|---|
| ① | PrivacyClass 隐私等级 | **H08** |
| ② | Pointer 搬动模型 | **H02** |
| ③ | SnapshotId 快照一致读 | **H05** |
| ④ | Transaction 事务 | **H03** |
| ⑤ | Quarantine 隔离坏版本 | **H06** |
| ⑥ | LifecycleState 对象生命周期 | **H07** |
| ⑦ | AiosPath／NamespaceClass 路径分类 | **H01** |
| ⑧ | 冲突解决（乐观并发／CRDT 范围／合并） | **H04** |
| ⑨ | 恢复清单 | **H10** |

⇒ **9／9 全部有落点**，无漏条。

### （b）来源2 表 A 的 13 条 → 总表编号

| 来源2 | 总表编号 | 是否与来源1 并成一条 |
|---|---|---|
| A01 每一次写都必须同时挂「事务」与「证据」两条链 | **H03** | ★ 并（来源1-④） |
| A02 指针搬动 ＝ 状态推进／回滚 | **H02** | ★ 并（来源1-②） |
| A03 版本状态机 ＋ 隔离坏版本 | **H06** | ★ 并（来源1-⑤） |
| A04 隐私等级 ＋ 隐私天花板 | **H08** | ★ 并（来源1-①） |
| A05 读一致性三档 ＋ 快照号 | **H05** | ★ 并（来源1-③） |
| A06 并发写：乐观并发 ＋ 冲突是一等公民 | **H04** | ★ 并（来源1-⑧） |
| A07 恢复面「只依赖哪几层」写死 | **H10** | ★ 并（来源1-⑨） |
| A08 闭词汇查询语言 | **H09** | 独有（来源1 无对应条） |
| A09 名字空间「路径分类 ＝ 权限类」 | **H01** | ★ 并（来源1-⑦） |
| A10 生命周期 ACTIVE→RETIRED→PURGED ＋ 保留期 | **H07** | ★ 并（来源1-⑥） |
| A11 内容寻址块 ＋ GC「绝不静默」 | **H12** | 独有 |
| A12 每次变更都签名 | **H11** | 独有（★ 与来源1 的「签名」**不同义**，见 附二 第 11 条） |
| A13 降级必须显式、必须失败关闭 | **H13** | 独有 |

⇒ **13／13 全部有落点**；**合并掉 9 组**（上表 9 个「★ 并」）⇒ 9 ＋ 13 － 9 ＝ **13 行 H01…H13**。

### （c）来源2 表 B 的 10 条 → §六（不是缺口，没有 H 编号）

| 来源2 | 落点 | 备注 |
|---|---|---|
| B01 | §六 B01 | 与 **H11**（差签名）／**H03**（事务＋证据链）**相邻**，但**不是缺口** |
| B02 | §六 B02 | 与 **H02**（复合键／前缀扫）相邻 |
| B03 | §六 B03 | 与 **H08**（治理面）相邻；且我们多一条「法律没写全 ＝ 拒」 |
| B04 | §六 B04 | 与 **H09**（闭词汇）**同向**，但**已对** |
| B05 | §六 B05 | 与 **H05／H01** 的「零新增依赖（blake3）」相邻 |
| B06 | §六 B06 | 与 **H02**（正文一行不改）相邻 |
| B07 | §六 B07 | **对了一半**；缺的那半 ⇒ **H07** |
| B08 | §六 B08 | 与 **H05**（视图是派生物、可重折）相邻 |
| B09 | §六 B09 | 与 **H03**（证据链）／**H04**（冲突留痕）相邻 |
| B10 | §六 B10 | 与 **H05**（同一快照同结果）／**H09**（确定性计划）相邻 |

### （d）来源2 表 C 的 13 条 → §七（故意不做／不适用）

| 来源2 | 落点 | 备注 |
|---|---|---|
| C01 | §七 C01 | ★ 与 **H11** 是**未裁冲突**（见 §五·2） |
| C02 | §七 C02 | 与 **H11**／C01 同一面 |
| C03 | §七 C03 | ★ **待裁**；与 **H12**「不引块结构」相邻 |
| C04 | §七 C04 | 与 **H01**（我们自己的名字空间面）相邻 |
| C05 | §七 C05 ＋ §七·1 | ★ 只可借「提议 ＋ 提升另过闸」那一半 ⇒ **已在 H04** |
| C06 | §七 C06 | 与 **H08** 的**词汇并列**（见 附二 第 8 条） |
| C07 | §七 C07 | 与 **H01** 相邻（只借方法、不借树） |
| C08 | §七 C08 | 与 **H10**（恢复面不外引）无涉，独立 |
| C09 | §七 C09 | 与 **H03**（账要记「谁」）相邻 |
| C10 | §七 C10 | ★ **待裁**；与**呈现维／事实维**分家冲突 |
| C11 | §七 C11 | 与 **H03／H04** 相邻（它自己 defer） |
| C12 | §七 C12 | ★ **待裁**；与 **H12** 相邻 |
| C13 | §七 C13 | 与 **H04**（AI 只提议）同向，**非缺口** |

### （e）合计与漏条核查

- 来源1 **9 条** ＋ 来源2 表 A **13 条** ＝ **22 条**；**9 组重叠各并成一条** ⇒ 总表 **H01…H13，共 13 行**。
- 来源2 表 B **10 条** ⇒ §六（逐条列全）；来源2 表 C **13 条** ⇒ §七（逐条列全）。
- ★ **漏条核查结果：无漏条**（a／b／c／d 四张表逐条对上）。
- ★ **有意不列 A 也不列 B** 的一条：来源2 §四 末尾的 **NL→query bridge**（「照面但不完全对应」）—— 来源件**逐字说明**「不列 B、也不列 A，如实标注」，本件照办（见 §六 末尾）。

---

## 末尾 · 附二 两份来源并列／矛盾清单（逐条 · 待裁）

★ 本清单**只并列两处原文 ＋ 标「待裁」**，**不选、不裁、不折中**。

1. **crates/aios-fs/src 的件数**：来源1:13「读的参考实现 ｜ crates/aios-fs/src/（**35 件**；行号见各行引用）」 ⟷ 来源2 §一 R1「src **25 个 .rs**」／R5／R6「**25 行 md5，与 R5 逐行相同**」。⇒ **待裁**（本件照来源2 的 25 立文）。★ **评审后修 · 五席共同确认 ＋ 本席现取**：`crates/aios-fs/src` **现数 25 个 `.rs`**（顶层 22 ＋ `service/` 3）；`crates/aios-worldcore/src` **现数 35 个 `.rs`** ⇒ 来源1 的「35 件」**系张冠李戴**。★ **要不要据此裁为 25，由人定**。
2. **H02 指针 动不动 ontology.json**：来源1-②.4「**不动**」 ⟷ 来源2-A02「★ **要（写成提案）**」。⇒ **待裁**。
3. **H03 事务 动不动 ontology.json**：来源1-④.4「**不必需**：可用 change 族 ＋ what=txn.commit」 ⟷ 来源2-A01「★ **要（写成提案）**—— 没有「事务」这一栏」。⇒ **待裁**。
4. **H04 冲突 动不动 ontology.json**：来源1-⑧.4「**砖一、砖二不必动**」（merge_policy 才要） ⟷ 来源2-A06「★ **要（写成提案）**」。⇒ **待裁**（★ **评审后修 · 丙-G5**：原文写「**两条都承认**『砖一不必动本体』，本件据此把砖一放第②档」—— ★ **不成立**：现取**来源1「砖」9 处／「不必动」1 处**，**来源2「砖」0 处／「不必动」0 处** ⇒ **只有一个来源说过**。★ **砖一的档位 = 待裁**，本件**不据此分档**）。
5. **H06 隔离 动不动 ontology.json**：来源1-⑤.4「**不动**（notice 族今天已经在册）」 ⟷ 来源2-A03「★ **要（写成提案）**」。⇒ **待裁**。
6. **H06 的载体位置**：来源1-⑤.3 把隔离区放**账**（ledger 侧 quarantined: BTreeMap<EventSeq, QuarantineEntry>） ⟷ 来源2-A03 把版本状态栏放 **Row**（store 侧 staged／verified／quarantined／retired）。⇒ **并列，待裁**。
7. **H05 的范围**：来源2-A05 点名**读一致性三档**（SNAPSHOT／LINEARIZABLE／EVENTUAL） ⟷ 来源1-③ 只做 SNAPSHOT 那一档（逐字「我们不需要 MVCC」）。⇒ **并列，待裁**。
8. **H08 的等级词汇**：来源1-①.3「**不照抄它的 5 级**……落在我们**已经声明的 3 级**」（PUBLIC／INTERNAL／CONFIDENTIAL） ⟷ 来源2-C06 括注「**A04 只借 PUBLIC／INTERNAL／SENSITIVE 那几档**与「只升不降」」。⇒ **并列，待裁**（SENSITIVE ⟷ CONFIDENTIAL）。
9. **H01 接哪一格**：来源2-A09「★ 这正好接我们已有的 **vocab_hash**（总线通行证那一格）」 ⟷ 来源1-⑦ 只说我们**已有**的是 **blake3 ＋ 规范压平**（ledger/seal.rs:90-92／seal.rs:63-74），**未提 vocab_hash**。⇒ **并列（不是硬矛盾），待裁**。
10. **来源2 内部的字节数不自洽**（本件只做加法，未读规格）：来源2 §一 R1 六个字节数 2,494／41,866／44,090／25,799／21,346／71,611 **相加 ＝ 207,206 B**，而来源2 §二 自报「六件合计 **227,206 B** ／ 3,849 行」⇒ **差 20,000 B**；其中 **3,849 行**与来源1 的 6 件行数相加**自洽**。★ **评审后修 · 五席共同确认**：VM 实盘六件字节 ＝ 2,494／41,866／44,090／25,799／21,346／71,611 ⇒ **相加 ＝ 207,206 B** ⇒ ★ **227,206 是来源2 自己写错**。⇒ **待裁**。
11. **「签名」一词两份不同义**（★ 本件据此**不当作重叠合并**）：来源1 的「签名」＝ **Who::new 的接口签名**（来源1:374「**签名改动**：Who::new 不校验……」／来源1:384「九条里**唯一必须动签名**的一条」）；来源2-A12 的「签名」＝ **Ed25519 密码学签名**（evidence_emit.rs:44-48 append_signed）。⇒ H01（接口签名）与 H11（密码学签名）**分列两行**，**待裁**（是否要用同一个词）。
12. **来源件自己标了「待裁」的条目**（照抄，不重复计）：来源2 §六 第 11 条「A12 与 C01 的关系，本席只报冲突，未裁」（见 §五·2）；来源2 §六 第 12 条「C03／C10／C12 三条本席标了「待裁」」（见 §七）。

13. ★ **「会红的反例」到底有没有**（★ 评审后修 · 测试席 G-02）：**来源1 §10.3**「每节给的『会红的反例』是**判据形状**……它们**今天一条都不存在**」（★ 射程 ＝ **它那 9 节**） ⟷ **来源2 §四 B10**「`query.rs:212-221`（会红反例 2）……**且有会红反例盯着**」（★ 本席现取：本仓 `query.rs:195`／`:212`／`:223` **三条在册**）。⇒ ★ **两处并列、待裁**（本件把 §二·0 第 6 条**收窄到来源1 的射程**，**不替作者选**）。
14. ★ **「碑」的语义 同件两说**（★ 评审后修 · 丁-D02／D03）：**§六 B07**「碑 ＝ RETIRED 的一半」 ⟷ **§三 H07**「它**其实已经**是 RETIRED 的语义」。⇒ ★ **并列、待裁**（本件**两句都留、不合口径**）。

★ 另：本件**未发现**其它形式的互相矛盾；上列 **14 条**全部并列两处原文，**未替作者选**（★ **第 13／14 条系评审后补**，逐条见 §十）。

---

## 末尾 · §十 评审后修 · 逐条对照（五席「必闭项」→ 本件改了什么）

★ **本表是「改了哪几处」的登记**，不是「评审通过」；★ **五席结论一律是「有条件通过」**（无人给通过、无人给退回）。
★ **被评版本** sha256 `dadf255abee33c1055cbddaf436cd56160fa8fecfab420aa7fd80a6d7d6d3ef9`（401 行／90,287 B）；★ **修后 sha256／行数写在 `改动对照.md` §十七**（写在本件里会自指）。
★ 凡本席**现取**得出的读数，一律写出**文件:行**；★ 凡**没修**的，一律写在 §十·2（**如实登记未做**）。

### §十·1 已修（逐条：哪一席 ｜ 必闭项 ｜ 怎么修 ｜ 现取读数 ｜ 落在本件哪一处）

| # | 席（编号） | 必闭项（判词摘要） | 本件怎么修 | 现取读数（本席复核） | 落点 |
|---|---|---|---|---|---|
| 1 | 丙-G5 | 「两条都承认砖一不必动本体」**不成立**（据此分档＝替作者选） | 改为「**只有一个来源说过**」，并**撤掉据此分档**：**砖一档位 = 待裁** | 来源1「砖」**9**／「不必动」**1**；来源2「砖」**0**／「不必动」**0** | §五·3 注 ＋ 附二 第 4 条 |
| 2 | 测试席 G-02（主件自相矛盾 a） | §二·0 第 6 条「**所有**会红反例都不存在」 ↔ §六 B10「有会红反例盯着」 | 第 6 条**收窄到来源1 的射程**（只管它那 9 节），并补「本仓三条在册」；同件两说登记 **附二 第 13 条** | `crates/aios-worldcore/src/engine/query.rs:195／212／223`（逐字带「会红反例 1／2／3」） | §二·0 第 6 条 |
| 3 | 丁-D02／D03（主件自相矛盾 b） | §六 B07「对了一半」 ↔ §三 H07「其实已经是 RETIRED 的语义」 | **两句都留**、说明各自射程，登记 **附二 第 14 条**（**不合口径**） | 同件两处原文（不涉新读数） | §六 B07 |
| 4 | 丁-D05 | §七「依据」口径**过宽**（13 条并非都指那两处） | 「依据」**射程写实**：能指到那两处 **6 条**／「面我们没有」**6 条**／表外第三源 **1 条（C10）** | 逐条现取（见 §七 该段） | §七 开头 |
| 5 | 甲-01 | H13 引 `05:518` 的加粗**原文没有** | **去加粗** | `05_namespace_layout.md:518` 逐字 `Failure modes — all fail closed:` | §三 H13 行 |
| 6 | 甲-02 | H11 引 `evidence_emit.rs:35` 的加粗**原文没有** | **去加粗** | `crates/aios-fs/src/evidence_emit.rs:35` 逐字 `/// Async append-only sink for sealed, signed AIOS-FS evidence receipts.` | §三 H11 行 |
| 7 | 甲-03 | H02 引 `01:230-238` **起行差 1** | 改 **`01:229-238`** | `01_object_model.md:229` 逐字 `PromotePointer(pointer_id, expected_current_version_id, new_version_id):` | §三 H02 行 |
| 8 | 甲-04／甲-05 | H06 把**枚举行重构成句子**；五个触发器**加粗全丢** | 枚举行**按原文逐字重排**（只压空白）；触发器**标注「压缩、加粗未保留」** | `01:155-161` 枚举逐字；`01:329-333` 五个加粗条目 | §三 H06 行 |
| 9 | 本席现取补（甲-01／02 同形） | H13 引 `05:522` 的加粗**原文也没有**（评委未点，本席现取补） | **去加粗** | `05:522` 逐字 `- CatalogSignatureFailure → resolver enters degraded mode (…)` | §三 H13 行 |
| 10 | 乙-01 | H07「surface 只有 3 格」**报小了** | 改 **6 格** | `crates/aios-ontology/data/ontology.json` 的 `objects.surface.fields` ＝ name／role／order／visible／retract_seq／cells | §三 H07 行 |
| 11 | 乙-02 | §六 B01 漏 `families:47`／`by_family:49` | 补两格 | `crates/aios-worldcore/src/engine/ledger.rs:47／49` | §六 B01 |
| 12 | 乙-03 | §六 B10 行号 `:8` 应为 `:9` | 改 **`:9`**（并注明 L8 是「缺席即假」） | `query.rs:9`「无 order_by 时按**键升序**」 | §六 B10 |
| 13 | 乙-04 | H13「已知**一处**静默降级」**报小了** | 补 **≥2 处**（并标「登记面未记」） | `crates/aios-fs/src/in_memory.rs:1016`（未知隐私级⇒Sensitive）／`:1046`（未知 scope⇒System） | §三 H13 行 ＋ §八·5 |
| 14 | 丁-D04 | §六／§七**都漏登**「立碑后写没被拒」 | 新增 **§八·5 评审补记**（含性质标注） | `store/projection.rs:126` vs `:129-135`；`store/tests.rs:79-92`（★ **读码推定、未跑**） | §八·5 |
| 15 | 丙-G1 | ①档「不动权威件」**含不含外部未定义** ⇒ H13 档位**不可判** | 写出**两种读法**；**H13 档位待裁** | H13 要动**外部** `crates/aios-fs/src/in_memory.rs` | §四 三档口径 |
| 16 | 丙-G2 | 漏依赖 **⑦→⑧（H01→H04）**；件内两处相抵 | §四·2 **H04 前提补 H01**（＝H01＋H02＋H03） | 来源1 §10.2 依赖图逐字（`⑦ 路径 ──┐ ├─► ⑧ 冲突`／`② 指针 ──┤`） | §四·2 |
| 17 | 丙-G3 | 「唯一会动对外签名」**不可判**（「对外签名」未定义） | 标「不可判」＋按来源1 原话读（`Who::new` ⇒ 可失败）；**要不要定义待人裁** | 来源1 原话（`Who::new → 可失败`） | §四·3 H01 行 |
| 18 | 丙-G4 | §四·2「未裁 4 条」**漏算 H09** | 改 **5 条**（H02／H03／H04／H06／**H09**） | 来源2-A08 同栏**两说并存**（「不要」＋「那就**要**动（提案）」） | §四·2 注 |
| 19 | 丙-G6／G7 | §五·3 **只并两列**、缺「当前本体／代码读数」一方 | **加第三列**（4 行现取） | `ontology.json:9789-9791`（指针「★ 冲突：不进语义面」）／`:21`（`enum(change, act, notice)  # 三个家族`）vs `families` **四族**／`governance` **有 tombstone、无 quarantine**／`crates/aios-worldcore/src` 全树 **conflict 0 命中** | §五·3 |
| 20 | 测试席 G-06 | H10「今天就能绿、真的能红」是**对尚未存在判据**的可红性断言 | 标注「**是推的、未反向验证**」＋「立判据先写会红的反例」 | 本仓硬约束 9 | §三 H10 行 |
| 21 | 测试席 G-07 | §九「未跑门禁、未送评」**在评审后已过期** | 加**时点更正**（本件此后已送评：`f687411` ＋ 席位表 `6e1640d`） | git 提交号 | §九 |
| 22 | 测试席 G-08 | 评审有效性**无机器判据** | 如实登记；★ **登记 ≠ 判违规** | 本仓 `verify/check.py` 现取只有 **C1–C7**，无 `check_panel`／`check_division`／`check_team` | §九 |
| 23 | 五席共同确认 | 「`crates/aios-fs/src` = 35 件」**张冠李戴** | 补现取：**aios-fs/src ＝ 25**、**aios-worldcore/src ＝ 35** | 现数（顶层 22 ＋ `service/` 3 ＝ 25；worldcore/src 树 35） | §二·0 第 7 条／附二 第 1 条 |
| 24 | 五席共同确认 | 来源2 自报「227,206 B」**自相矛盾** | 补现取：**六件相加 ＝ 207,206 B** ⇒ 227,206 系来源2 自错 | VM 实盘 2,494／41,866／44,090／25,799／21,346／71,611 | §二·1 注／附二 第 10 条 |
| 25 | 本席现取补 | 件头「落点」写「**不进 ninedim/**」，**与现取不符** | 更正为**两处并存、逐字节相同**；唯一权威副本**待人裁** | 两处 sha256 同为 `dadf255a…` | 件头 |

### §十·2 ★ 没修的（如实 · 不许读成「都修完了」）

| # | 没修的 | 为什么 |
|---|---|---|
| 1 | **甲-06：全表逐处「句中截断未标 `…`」** | ★ **未逐处补标**（工作量）；★ 本次只在**被点名**的四处动了引文（#5–#9）。★ 彻底落法 ＝ **全表引文回原文逐字复核一遍**，**待人裁**（要另开一刀） |
| 2 | **引文里的加粗** | ★ 只去掉了**被点名的两处 ＋ 本席现取的第三处**；★ **其余引文里的加粗未去**（★ 已在件头「加粗体例」里**声明**：加粗＝本件所加，原文大多没有） |
| 3 | **交人裁的 6 件** | ★ 见《评审-五席判词汇总》§三（评审够不够格／砖一档位／「权威件」含不含外部／§五 四条提案／H11 与 C01 冲突／本体三族-四族不自洽）—— ★ **智能体不代裁**（硬约束 6） |
| 4 | **§五·3 第三列的「要不要因此改本体」** | ★ 现取读数**只报事实**，★ 结论**留给人** |
| 5 | **本件没有跑任何构建／测试** | ★ 只跑了本仓 `verify/check.py`（C1–C7，rc=0，见 `改动对照.md` §十七）；★ **四道 cargo 门只能在 VM 跑**，本件未跑 |
| 6 | **修后没有重新送评** | ★ 修后版本**未经任何席位复审**；★ **要不要送复审、由谁送，是人定的**（硬约束 6） |

★ **一句话**：★ 本件**按必闭项逐条修了 25 处、如实登记没修 6 条**；★ **它仍然不是「已通过」** —— ★ 正式结论与签字**只有人能下**。

