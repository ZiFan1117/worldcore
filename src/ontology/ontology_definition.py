"""AIOS 世界的本体定义 —— ★ 按 P（foundry-ontology-open，MIT）的格式写。

★ 【全部】来自 `src/ontology/data/ontology.json`（★ 那是【法】，人审定）。
★ 这里把它完整映射成 P 的形态：
★   ① 12 类 → ObjectType（9 原类 ＋ space／presentation／computer）；② 10 关系 → LinkType（3 原 ＋ 7 人侧）；③ 9 动作 → ActionType；④ 9 函数 → OntologyFunction；
★   ⑤ 世界机制（envelope／families／permissions／governance／value_types／flags／world）→ Ontology.metadata。
★★ 不映射 `notes`（89% 体量）—— 那是【知识库】，不是本体机制。
★ ★ 改动本体：先改 `ontology.json`（要人审），再同步这一份。
"""

import os  # ★ sysknife 映射表路径
import json

from foundry_ontology.core import (
    Ontology, ObjectType, Property, LinkType, Cardinality,
    ActionType, ActionParameter, ValidationRule, OntologyFunction,
)
from foundry_ontology.core.data_types import PropertyType


def build_aios_ontology() -> Ontology:
    o = Ontology("aios_world", "AIOS 世界本体", str(1))

    # ── 世界机制 → Ontology.metadata（P 没有这些格，我们加的 metadata 那一格）──
    o.metadata = {"world":1,"flags":[],"envelope":{"_comment":"一条事件的外壳（信封）—— 机制只看这一层，不看信纸","required":["world","kind","id","seq","at","actor","flags","body"],"optional":["to","trace"],"fields":{"world":"integer  # 词表版本；只加 flags，永不改这个数的含义","kind":"enum(change, act, notice)  # 三个家族","id":"string  # 事件自身身份（去重）","seq":"integer  # 在账本中的位置，全局单增，由世界分配","at":"integer  # 时间戳，Unix 秒。顺序由 seq 决定，at 只作辅助","actor":"string  # 世界内身份，如 world://user","to":"string  # 目的地；空 = 广播","trace":"string  # 因果：引发本条的那条事件的 id","flags":"array  # 能力旗标；未知旗标必须忽略","body":"object  # 三个家族各自的信纸"}},"families":{"change":{"_comment":"变更：世界状态发生了变化。★ **未实现**（判词 · 形式本体 Y-2）：本条名字取的是它所关于的那一过程（occurrent），而家族在实现上是账本里的一行记录（信息内容实体）；本体的『记录／信息内容』这一类**今天不存在**（`objects` 六类里无 event／record），『这条记录**关于**哪件事』在声明面上**无落点**。真修＝往 `objects` 加『记录／信息内容』一类（`_` 键）⇒ **零身份代价**（`src/ontology_definition/mod.rs:2149-2164` 整枝剔除；`:637` 射程表第 5 行「该类型只在一处出现 ⇒ 不判」）；★ 会换身份的是动**非 `_` 顶层键**——现取 `sorted(k for k in d if not k.startswith('_'))` ＝ `['concepts','envelope','families','flags','world']`（**5 类**）；本条修法**不碰它们**。本批只写提案，见 `ninedim/06-变更/2026-10-08-ontology-decl-fix/提案.md`。","required":["subject","path","before","after"],"optional":[]},"act":{"_comment":"动作：请求 → 结果（结果本身也是事件）。★ **未实现**（同 Y-2）：名字取的是那一过程，实现上是账本行（无『记录』类）；且这条『请求→结果』因果边**只有 `trace`**，而 `trace` **不做引用完整性校验**（指向不存在的 `id` 不导致拒绝；`ledger-integrity.spec.md` 的 v1 口径）。","required":["capability","verb","request_id"],"optional":["params"]},"notice":{"_comment":"通告：发生了什么（完工铃等）。★ **未实现**（判词 · 形式本体 Y-2 ＋ 安全与授权 题 2 串 B）：`payload` 的形状本体**不声明**（见 `_subscribe._declared_gaps`）；且 `notice` 家族过闸时**不查能力许可**（只判『非 `gate.` 前缀 ＋ 在册』）⇒ 任一在册主体可伪造 `job.completed`，而读法不认作者。","required":["type","subject"],"optional":["payload"]},"job":{"_comment":"作业：一次由主体请求、由载体执行、留下起止与结果的发生。★ 2026-10-13 撤并：`job` 不再是独立的类（它答不出三问：零指认格）；它是本族之一。","required":["status","subject"],"optional":["step","steps_total","step_label"]}},"permissions":{"_element":"许可条文（**不是**能力本身：授权授在**能力**上）","_comment":"『谁能把某个能力授给谁／从谁收回』。条文并入本体，但**授权对象只能是 `interfaces` 里已声明的能力**——授在**具体类型**或**具体对象**上 ⇒ 红（`ext.world.Ontology.GrantNotOnCapability`）。★★ **本段不是世界的总闸**（现取口径，判词 · 安全与授权 题 1）：真正决定『谁能改世界』的写闸是 `src/gate/policy.json` 的 `writes`，它**按对象地址前缀**授权（`authorize_write`）；本段的 `grants` **只在 `act` 家族**被判（`src/lib.rs` 的 `check_presence_levels` 读 `scope`），**`change` 与 `notice` 两个家族根本不经过本段**。⇒ 读『授权只授在能力上』这句话时，**不许**把它读成『世界只有这一个授权面』。","_default_closed":"★ 判据：`default` 必须**显式**写 `\"deny\"`。缺 `default` 或写成别的词 ⇒ 红（`ext.world.Ontology.PermissionDefaultOpen`）——默认允许不是安全默认，是法律没写全。","_declared_gaps":"★ **未实现／未接入**（判词 · 安全与授权；**本批没做（不是做不到）**：VM `newworld` 一直有 `cargo 1.98.1`＋`bash`（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立） ⇒ 下列是**判词读数，未在真二进制上跑过**）：① **`who` 无读者**——它被装载器解析进 `PermissionDecl.who`，而**没有任何生产消费者读它**（判『许可』只读 `scope`）⇒ 该格**只作条文、无执行体**，写与不写在程序上等价。② **`_grant_via_ledger` 声称的路没有执行体**——`scripts/verify/grant_path_guard.py` 的 G-02 **现取红**（登记型红，接在 `check.sh` 上不阻断全闸）。③ **撤回没有授权面**——`change` ＋ `retract_seq` 能取消任意一条已生效的 `change`，而撤回**不是**本节的能力、不是 `actions` 的动作，`change` 分支**不读本节、也不查两级**。④ **`notice` 家族不查能力**——只判『非 `gate.` 前缀 ＋ 在册』⇒ 任一在册主体可伪造 `job.completed`。⑤ **『一条 grant ＋ 一次重启』即可放宽一项能力**：全程**无判据会红、无账本事件、无签字要求**；『谁有资格改本段』今天**只有流程答案**（『改本段＝改法律（走评审）』），**没有机器答案**。⑥ `ledger.compact` 的 `scope` ＝ `[\"world://*\"]` 把一项**不可逆**能力授给了**每一个**主体（纵深只剩 `policy.json.irreversible_actors` 一层）。⑦ `who`／`scope` 里的 `world://user`／`world://agent/dsh` 的**类型在 `objects` 里不存在**（见 `objects._declared_gaps`）。⇒ 真修③④要动代码（`src/lib.rs`／`src/agent/**`）；⑤要动流程（判据＋签字要求）；**⑥⑦的声明面修法反而是零身份代价**（`permissions`／`objects` 都是 `_` 键）⇒ 本批**只写提案**（法律口径取舍待批）。","default":"deny","grants":{"job.start":{"who":["world://user","world://agent/dsh"],"scope":["world://user","world://agent/dsh","world://presence/omarchy"]},"job.finish":{"who":["world://user","world://agent/dsh"],"scope":["world://user","world://agent/dsh","world://presence/omarchy"]},"job.cancel":{"who":["world://user","world://agent/dsh"],"scope":["world://user","world://agent/dsh","world://presence/omarchy"]},"world.rekey":{"who":["world://user"],"scope":["world://*"]},"world.migrate":{"who":["world://user"],"scope":["world://*"]},"notice.mute":{"who":["world://user","world://agent/dsh"],"scope":["world://user","world://agent/dsh","world://presence/omarchy"]},"notice.unmute":{"who":["world://agent/dsh"],"scope":["world://agent/dsh","world://presence/omarchy"]},"ledger.compact":{"who":["world://user"],"scope":["world://*"]},"presence.report":{"who":["world://user"],"scope":["world://presence/pcmanfm","world://presence/omarchy"]},"_omarchy_note":"★ 新身份 `world://presence/omarchy`（界面自己的口 `/run/world-core/omarchy.sock`）：**只动 `scope`，不动 `who`**。理由可核——`src/lib.rs::check_presence_levels` 判「许可」时逐字读的是 `p.scope`（`gate::pattern_matches(pat, actor)`），**不读 `who`**；而本段自己的口径写着 `who` ＝『谁能把某个能力授给谁／从谁收回』⇒ 把界面写进 `who` 就是**另外给它一份「发许可证」的权力**，本批**不给**。★ **更正（判词 · 安全与授权 题 1）**：这条论证的**前提今天是假的**——`who` 被装载器读进结构体，而**没有任何生产读者**（判『许可』只读 `scope`）⇒ 写与不写在程序上**完全等价**，『把界面写进 `who` 等于给它发许可证的权力』**不成立**（结论无害，理由是空的）。**现取事实**：本批只动 `scope`，因为 `scope` 才是生效许可；`who` 今天**只作条文、无执行体**（见 `_declared_gaps`）。★ 授权只授在**能力**上（`notice.mute`／`notice.unmute`／`presence.report`），**没有一条授在具体对象上**。★ 拿到许可 ≠ 能说话：`world://presence/*` 还要过第①级**申报**（它名下要有格），两级都过才交回门禁。","_omarchy_scope_why":"为什么这三条：界面的「点一下」是**一条 `act`**（家族 act，能力＝动作名），不是直接改字段；它今天要用的能力就是「静音／解除静音」，另加它自己报在场状态用的 `presence.report`。★ 与本项目既有口径一致：**能力清单不在这里发明**——名字都取自 `policy.json.capabilities` ∩ 本文件 `interfaces`。★ **现取更正**（判词 · 安全与授权 题 4 附带）：『两处同集』**在运行期只兑现一半**——`World::open` 只做**单向**（policy ⊆ ontology）；**反向**由 Python 判据 `scripts/verify/cross_contract.py` 的 C-03 承担，**不是拒启**。"},"_presence_report_note":"★ 在场者两级分开（顺序是死的）：①**申报**给的是“依据”（该在场者有没有在世界里申报过——判据＝折叠出的状态里这个主体有没有格）；②**授权**给的是“许可”（`grants.<能力>.scope` 命中该主体；`default: deny`）。**二者不许合并**——一旦合并，等于在场者自己给自己发许可证，世界就不再管着它。报得再全，也不自动拿到任何能力；开放只由许可决定。★ **现取更正（射程）**（判词 · 安全与授权 题 4）：这两级**只在 `act` 分支成立**（申报在前、授权在后）；对 `change` 与 `notice` 两个家族**不成立**——同一主体改走那两个家族即可**绕过**本节的能力许可。「两级都过才交回门禁」这句**只对 `act` 为真**。","_grant_via_ledger":"★ **设计已定·未落地**（判词 · 安全与授权 改法③ 乙）：下面这条路**今天在程序里不存在**——`src/` 里**没有**读『能力格』的代码（`scripts/verify/grant_path_guard.py` 的 G-02 **现取红**）；**今天的授权判定读本段 `grants.<能力>.scope`，不读账本**。⇒ 在落地前，**不许**把下句读成『授予／收回已经在走账本事件』。**设计口径（保留供对照）**：授予／收回是**事实**，走账本事件（`change` 写 `world://user` 的能力格 → 门禁 `authorize_write` 裁决 → 落笔）。本段只是**条文的声明面**：谁**有资格**授予、授给谁。改本段＝改法律（走评审）；改一次授权＝落一条事件（**这句是设计口径，未落地**）。★ 处置两条（判词③）：甲＝落地（让 G-02 有真命中）／乙＝本句改标『设计已定·未落地』。⇒ 本席取**如实登记、不单方面改法律口径**，故 G-02 **仍红**（如实），处置权交评审与法律主人。","_2026-10-12_理由更正":"★ 本栏原写「本机**无 cargo** ⇒ 下列是判词读数，**未在真二进制上跑过**」——**那句只对 Windows 宿主成立**（VM `newworld` 一直有 `cargo 1.98.1`）。⇒ 下列各条该改的性质是「**本批没做**」，**不是「跑不了」**。"},"governance":{"_comment":"**治理面四格**（DYNAMIC 层那一族）。照 Palantir 开源复刻件的三层切法，治理面 ＝ `Roles • Markings • Permissions • Audit Trail`。★ **2026-10-12 改准**：本行原写「我们**只有 Permissions 与账本**，另两格（Roles／Markings）**一格都没有**」——**与本文件下面的 `roles`／`markings` 两格自相矛盾**（它们 ⑧o 已建）。**现取实况：四格【声明面全建】**（`markings` 7 键／`roles` 10 键／`read_allow` 9 键／`tombstone` 7 键），各有判据（`check_governance.py`／`check_roles.py` 各 rc=0）；**四格的【执行面】都未做**（要 Rust）。★ 每格**必须写清「今天有没有执行体、在哪」**——凡写「有」的，判据 `check_governance.py` 会**回盘核**。","_source":"① `.refs/依赖料/foundry-ontology-open/docs/architecture.md`「Roles • Markings • Permissions • Audit Trail」与「Data classification (PUBLIC, INTERNAL, CONFIDENTIAL)」；② `.refs/依赖仓/axn-identifiers/limits/index.html`「errors corrected by amendment and tombstone, never silence」；③ 我们上一代 `.refs/语义世界-架构/理念总图.md` 与 `读许可` 那条自认缺口。","markings":{"_what":"**数据分级**：一份数据**能不能给出去**——与「谁能改」**两回事**。","_照谁":"Palantir 开源复刻件逐字「**Data classification (PUBLIC, INTERNAL, CONFIDENTIAL)**」","levels":{"PUBLIC":"可对外——★ 本仓今天**一件都没有**（出口桥导出的是本体形状，不含任何账本数据）。","INTERNAL":"仓内可读——**今天所有类都落这一档**（见 `by_class`）。","CONFIDENTIAL":"受控——**今天一件都没有**；★ 但 **`objects.port.owner_uid`／`objects.cell.owner` 这两个字段按其性质**该在这一档**（见 `sensitive_fields`），**今天未标**。"},"by_class":{"port":"INTERNAL"},"ceiling_by_role":{"_what":"★ 主体的**可见天花板**（读侧真闸）：按**角色**给，不一个个主体地给。学的是 aios-fs 02_query_view_language.md:155 那句「Every query is evaluated under the caller's privacy ceiling」**那条理念**，落在我们**已有的角色面**（governance.roles）上 —— ★ 不是搬它的代码，是把它那条理念写成我们的格。","_依据":"角色名取自同节 roster（human／agent）与 subject_to_role 里已在用的第三个（presence）；级名取自同节 levels（闭集三级）。","_本批（2026-10-15 · T-162）":"★ 本格是**新加**的（加之前该节没有天花板的落点）；★ **加格不动任何既有键**（加法，不是改写）。","_缺角色怎么办":"★ **没在这儿写天花板，就按最低级（PUBLIC）判**（运行期口径：法律没写全 ＝ 最保守）；★ 但「角色在册却漏写天花板」这件事**由判据 C8 判红**，不许静默。","human":"CONFIDENTIAL","agent":"INTERNAL","presence":"INTERNAL"},"sensitive_fields":{"port.owner_uid":"**CONFIDENTIAL**（★ **未标，只是清单**）——它是**载体侧 uid**，按性质不该随便给出去。","cell.owner":"**CONFIDENTIAL**（★ **未标，只是清单**）——同上。"},"_★能做与不能做（分开写清）":{"能":"**声明面**：每个类都有分级；分级取自闭集；敏感字段清单里的字段**真存在**（判据 `Mk-1`／`Mk-2`／`Mk-3` 核）。","不能":"**执行面**：出口／读的时候**真按分级过滤**——**今天没有任何过滤路径**（出口桥导出的是本体形状，不是账本数据）；★ 且 **`sensitive_fields` 那两条只是清单、不是已标**，**不许读成「已经控住了」**。"},"state":"声明面：有；执行面：**无**"},"roles":{"_what":"**角色面**：谁能做什么**按角色**给，而不是一个个主体地给。（照 Palantir DYNAMIC 层的 `Roles`。）","_照谁":"Palantir 开源复刻件 DYNAMIC 层逐字 `Roles • Markings • Permissions • Audit Trail`；并照席I 现取点名的缺口：「有 `who` 没有角色面，且 `who` 本身也没人读」。","_为什么建":"`permissions._declared_gaps` ① 逐字：「**`who` 无读者**……该格**只作条文、无执行体**，写与不写在程序上等价。」⇒ 本批把角色面建出来，并配判据 `scripts/verify/check_roles.py`——**那条判据读 `who`**，★ **这就给了 `who` 一个读者**。","roster":{"human":{"名字":"人","说明":"**人**——硬约束 6：**正式结论与签字只有人能下**；本角色是**唯一**能落正式结论的角色。","能做什么":["下正式结论","签字","批准／驳回"],"不许做什么":["被机器代替签字（★ 硬约束 6：**AI 不代签**）"]},"agent":{"名字":"智能体","说明":"**智能体**——**只出发现清单**，**不落正式结论**。","能做什么":["读","出发现清单","按已授能力行动"],"不许做什么":["下正式结论","签字","批准／驳回（★ 硬约束 6）"]}},"subject_to_role":{"world://user":"human","world://agent/dsh":"agent","world://presence/omarchy":"presence","world://presence/pcmanfm":"presence"},"未归":{},"_★射程（如实，不许读成「已接入」）":"本格是**声明面 ＋ 判据面**。★ **生产侧**的读者（让内核真按角色判）**要有 Rust 改动**，而****本批没做**（不是做不到）——执行面要改 Rust；VM `newworld` 有 `cargo 1.98.1`＋`bash`，该条件**一直成立**（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立）** ⇒ **未做**，照 `G4`：**不许写成「已接入」**。","_判据":"`scripts/verify/check_roles.py`：`R-1` 每个 `grants[*].who` 里的主体**必须有归属**（或明写在 `未归`）；`R-2` `roster` 不许空；`R-3` `subject_to_role` 指向的角色**必须在 `roster` 里**。","_今天":{"有执行体（声明面）":True,"在哪（声明面）":"`scripts/verify/check_roles.py`（接 `check.sh` ⑧o，自证 6/6）——★ **它真读 `who`**。","有执行体（生产侧）":False,"在哪（生产侧）":None,"缺口（生产侧）":"让内核真按角色判**要有 Rust 改动**，而****本批没做**（不是做不到）——执行面要改 Rust；VM `newworld` 有 `cargo 1.98.1`＋`bash`，该条件**一直成立**（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立）** ⇒ **未做**。照 `G4`：**不许写成「已接入」**。","★ 本批补上了什么":"`permissions._declared_gaps` ①「**`who` 无读者**」——**在声明面这一层被接住**：判据 `check_roles.py` 的 `R-1` **真去读每一个 `who`**。★ 但**生产侧仍无读者**，那一条**未闭**。"},"state":"声明面：有（⑧o）；生产侧：无——★ **本批没做（不是做不到）**：执行面要改 Rust，而 **VM `newworld` 一直有 `cargo 1.98.1`＋`bash`**（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立）。","_state_更正说明":"★ 2026-10-12：本栏原写「要 Rust，**本机无 cargo**」——那句**只对 Windows 宿主成立**，而**执行面本来就该在 VM 上做** ⇒ **那个理由不成立**。同格的 `_★射程` 与 `_今天` 两栏**当时已更正**、**只有本摘要栏漏了**，⇒ 同一格里摘要与详情**自相矛盾**。**现已改齐**（照「现取读数不许编」）。"},"read_allow":{"_what":"**读许可**：读**也要**授权（上一代总纲逐字「**读也要授权**」）。","_照谁":"我们上一代 `理念总图.md` §四 的四句总纲 ＋ 席I 现取「`读许可`／`read_allow`／`readers` **全 0 命中**」。","default":"allow","_default_为什么是 allow（★ 说清，免得被读成「已经安全了」）":"今天**没有任何读闸**——`default: allow` 是**对实况的如实描述**，**不是**一个「已定好的安全默认」。照本仓口径：**默认允许不是安全默认，是法律没写全**（`permissions._default_closed` 逐字）。⇒ 它是**缺口**，不是**决定**。","rules":{},"shape（以后每条 rule 要长什么样）":{"who":"主体或角色（★ 角色要能在 `governance.roles.roster` 里查到）","what":"★ **必须是在册能力**（照 `permissions` 的口径：**授权只授在能力上**）","why":"为什么要给这一条（不许是「先给着」）"},"_★能做与不能做（分开写清）":{"能":"**声明面**：`default` 显式写出来；`rules` 为空**明写为空**；每条 rule 的形态写死（判据 `RA-1`／`RA-2` 核）。　★ **2026-10-12 追加**：**执行面**——内核**真按读许可拦读**了（`read --as`；两级：在册 → 读许可）。现取实证见 `_2026-10-12_执行面落地`。","不能":"**执行面**：本格今天**有**了（2026-10-12，见 `state` 那栏与 `_★能做与不能做.能`）；**仍未做的**是：① **按 `markings` 过滤读出去的内容**（另一格，本件不碰）；② **逐条配规则的现成判据**（今天 `rules` 为空，判据 `RA-1`／`RA-2` 只核形态）。★ 所以本格今天的价值是「**闸在了、法律还开着**」，**不是**「读已经受控」。"},"state":"声明面：有（**明写今天无闸**——那是**建格当时**的实况）；★ **执行面：有**（2026-10-12 落：在册 ＋ 读许可两级；出厂法律放行在册主体）","_default_bold_note":"★ 本格原写成 `**allow**`（带 Markdown 粗体）⇒ 判据 `RA-1` 当场红。**闭集值不许带修饰**——已改回纯值。**判据抓对了，改的是数据、不是判据。**","_2026-10-12_执行面落地":"★ **2026-10-12：执行面落了**——`World::check_read_levels`（`src/runtime/world/check.rs`）＋ `world-core read --as <主体>`（`src/runtime/cmd/cmd_read.rs`）＋ 法律读出面 `src/ontology_definition/gov.rs`（新建）。**两级**：① **在册**（`governance.roles.subject_to_role` 的键 ∪ `未归`）② **读许可**（`rules` 非空 ⇒ 白名单即闭集；空 ⇒ 看 `default`）。**现取实证**（VM `/root/world-s39`，2026-10-12T10:56:51Z）：`read` 缺省 ⇒ **rc=0**；`read --as world://nobody` ⇒ **rc=1** 且逐字报 `ext.world.Gate.ReadNotOnRoster`。**四条单元测试**（`src/ontology_definition/unit.rs` 的 `r01`…`r04`，1 正控 ＋ 3 反例）全过，`cargo test --locked` **312 passed／0 FAILED**。★ **射程（如实，不许读成「读已经受控」）**：① 只判「在册 ＋ 读许可」两层，**判不了**读出去的内容该不该按 `markings` 过滤（那是另一格，本件不碰）；② **拒绝读不落账**（刻意：若落账，等于任何主体能用反复读把账本填满＝**把拒绝变成写入权**）；③ 出厂法律今天 `default: allow` ＋ `rules: {}` ⇒ **在册主体一律通**、**行为与改动前逐字节相同**（既有调用方一字不用改）——本件的价值是**这条路真的存在了**。"},"tombstone":{"_what":"**墓碑**：更正**不只**「再写一条」，还要**给被更正的那条立碑**——「**错误靠修正与墓碑，绝不靠沉默**」。","_照谁":"AXN 设计法则逐字「errors corrected by amendment and **tombstone**, never silence」","when":["**更正**一条已落账的记录时","**撤回**（`retract_seq`）一条已生效的 `change` 时"],"shape（碑上要写什么）":["**哪一条**被更正（原记录的 id）","**为什么**（原因，不许写「笔误」了事）","**谁**改的（主体，要能在角色面里查到）","**什么时候**（时点）","**改成了什么**（新记录指向）"],"_today":{"有执行体":"部分","在哪":"账本面的 `retract_seq`（**只有撤回**，**没有墓碑**）","缺口":"★ 本仓 `retract`／`retract_seq` 能取消一条 `change`，但**「更正」没有落点**：被更正的那条**不立碑、不留痕**。★ 而且 **`when` 那两个触发条件今天都没有执行体**——真立碑要有 Rust 改动，****本批没做**（不是做不到）——执行面要改 Rust；VM `newworld` 有 `cargo 1.98.1`＋`bash`，该条件**一直成立**（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立）**。"},"_★能做与不能做（分开写清）":{"能":"**声明面**：触发条件（2 条）与碑形（5 样）**逐条列名**，且都非空（判据 `T-1` 核）。","不能":"**执行面**：真在更正时立碑——**未做**（要 Rust）。"},"state":"声明面：有；执行面：**部分**（只有撤回、没有墓碑）"},"_gaps_found":{"① Markings":"**声明面建了**（每类有分级、分级取自闭集、敏感字段清单可核）；**执行面没有**（无任何按分级过滤的路径）。","② Roles":"**声明面建了**（⑧o，roster 3 个角色，判据真读 `who`）；**生产侧读者没有**（要 Rust）。","③ 读许可":"**声明面建了**（`default` 显式 ＋ 明写理由 ＋ 明写今天无闸）；**执行面没有**（要 Rust）。","④ 墓碑":"**声明面建了**（触发条件 2 条 ＋ 碑形 5 样）；**执行面只有一半**（只有撤回、没有墓碑；要 Rust）。","★ 一句总话":"治理面四格**今天全部只到声明面 ＋ 判据面**；**执行面要 Rust，**本批没做**（不是做不到）——执行面要改 Rust；VM `newworld` 有 `cargo 1.98.1`＋`bash`，该条件**一直成立**（`AGENTS.md` 2026-10-12 已更正「本机无 cargo」那句只对宿主成立）** ⇒ **四格都如实写着「执行面未做」**，**不许读成已落地**。"}},"value_types":{"_what":"P 的 ValueType：name／base_type／constraints／description ＋ validate()。","_本仓今天":"★ 一条都没有 —— 本仓没有任何具名值类型面。","_要加":"在 _ 键下加 types.value_types 的条目＋配会红判据；本批只建面。","record_kind":{"base_type":"string","options":["change","act","notice","job"],"_依据":"★ 2026-10-13：撤 record 后，`ref(record)` 的 10 处改为本取值域（作者裁定「取值域」）；★ 四值＝`families` 四键。","_照谁":"P 的 `ValueType`（name + base_type + constraints）"},"_本仓今天（2026-10-13 更正）":"★ **2026-10-13 更正**：本格**已有 1 条**（`record_kind`）—— 原文写「一条都没有」是**加它之前**的现取。★ 全仓带取值域的格子共 **20 个**：对象字段 5（`presence/port/agent/application/service` 的 `state`）、动作参数 5、函数出入 10。","_要加（现取）":"★ 原写「在 `_` 键下加 `types.value_types` 的条目＋配会红判据；本批只建面」。★★ **现取**：条目已加 1 条（`record_kind`）；★ 但**会红判据仍未配** —— 判据 C7 的九路射程**不读 `types.value_types`** ⇒ ★ **本格今天无人守**（待人裁是否补射程）。"},"base_types":{"string":{"本仓写法":"string","状态":"已对应","_说明":"本仓的 fields 值就是这类类型声明串；P 的 PropertyType 是枚举，本仓是自由记法（ObjectType.fields 注释逐字「不认得的写法一律放行」）。"},"integer":{"本仓写法":"integer","状态":"已对应","_说明":"本仓的 fields 值就是这类类型声明串；P 的 PropertyType 是枚举，本仓是自由记法（ObjectType.fields 注释逐字「不认得的写法一律放行」）。"},"float":{"本仓写法":"number","状态":"已对应","_说明":"本仓的 fields 值就是这类类型声明串；P 的 PropertyType 是枚举，本仓是自由记法（ObjectType.fields 注释逐字「不认得的写法一律放行」）。"},"decimal":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"boolean":{"本仓写法":"bool","状态":"已对应","_说明":"本仓的 fields 值就是这类类型声明串；P 的 PropertyType 是枚举，本仓是自由记法（ObjectType.fields 注释逐字「不认得的写法一律放行」）。"},"date":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"datetime":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"timestamp":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"geohash":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"geoshape":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"attachment":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"marking":{"本仓写法":None,"状态":"★ 非原子（今天没有对应写法）","_说明":"★ P 有、本仓今天没有。明标非原子（原子化七条 A-7）。要加：在 fields 里给一个认得的写法 ＋ 配一条会红的反例。"},"object_reference":{"本仓写法":"ref(<类型>)","状态":"已对应","_说明":"本仓的 fields 值就是这类类型声明串；P 的 PropertyType 是枚举，本仓是自由记法（ObjectType.fields 注释逐字「不认得的写法一律放行」）。"}}}

    # ── 对象类型（9 类）──
    o.register_object_type(ObjectType(
        type_id="port", display_name="端口",
        description="一个独立的持续体（independent continuant）：它有 `path` 与身份，并在 `declared→listening→retired` 之间迁移——它是跨进程进出的那一处。", primary_key="name",
        metadata={"wc_id":"wc:ont00000006","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "path": Property("path", "path", PropertyType.STRING),
            "identity": Property("identity", "identity", PropertyType.STRING),
            "mode": Property("mode", "mode", PropertyType.STRING),
            "owner_uid": Property("owner_uid", "owner_uid", PropertyType.INTEGER),
            "state": Property("state", "state", PropertyType.STRING, options=["declared","listening","retired"], description="enum"),
            "retract_seq": Property("retract_seq", "retract_seq", PropertyType.INTEGER),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="human", display_name="人",
        description="人——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000007","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "last_seen": Property("last_seen", "last_seen", PropertyType.INTEGER, description="UNIX 秒"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="agent", display_name="智能体",
        description="智能体——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000008","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "manifest": Property("manifest", "manifest", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["installed","running","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="application", display_name="应用",
        description="应用——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000009","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "did": Property("did", "did", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["installed","running","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="service", display_name="系统服务",
        description="系统服务——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000010","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "unit": Property("unit", "unit", PropertyType.STRING),
            "state": Property("state", "state", PropertyType.STRING, options=["running","stopped","retired"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="device", display_name="设备",
        description="设备——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000011","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "cert": Property("cert", "cert", PropertyType.STRING),
            "bound_to": Property("bound_to", "bound_to", PropertyType.OBJECT_REFERENCE, description="ref(human)"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="workflow", display_name="工作流",
        description="工作流——本批（2026-10-12）按 `objects._declared_gaps` 点名的缺口补立的类。", primary_key="name",
        metadata={"wc_id":"wc:ont00000012","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "wf_id": Property("wf_id", "wf_id", PropertyType.STRING),
            "parent_action": Property("parent_action", "parent_action", PropertyType.STRING),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="ledger", display_name="账本",
        description="★ 2026-10-13 **作者裁定补立**：世界里那**唯一的一处**系统性记录 —— 只追加的语义事件文件。★ 依据（作者原话逐字）：「**你要说是账本，可以说是单独的一个类，这个可以**……可能最后**整个计算机里头只有这么一处**」。★ 素材：`envelope.fields.seq` 逐", primary_key="path",
        metadata={"wc_id":"wc:ont00000030","instance_mode":"one"},
        properties={
            "path": Property("path", "path", PropertyType.STRING, required=True, is_primary_key=True),
            "compaction_seq": Property("compaction_seq", "compaction_seq", PropertyType.INTEGER),
            "entries_total": Property("entries_total", "entries_total", PropertyType.INTEGER),
            "retract_seq": Property("retract_seq", "retract_seq", PropertyType.INTEGER),
        },
    ))

    # ── ★ 2026-10-18 人侧模型（提案-人侧呈现模型-呈现与画布-待裁）──
    #   ★ 作者口径：「呈现不归人、按屏计数」「空间一人一份、在册≠激活」。
    #   ★ 本轮只加【类/关系】；动作（ActionType）由提供者进程注册进注册表（见 _load_human_side_grants）。
    o.register_object_type(ObjectType(
        type_id="space", display_name="个人空间",
        description="人的地盘（归属与激活状态）。★ 一人一份、在册≠激活：登录只把当前人的空间置 active；布局/壁纸/偏好等【细节不进本体】。",
        primary_key="name",
        metadata={"wc_id":"wc:ont20261018_01","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "owner": Property("owner", "owner", PropertyType.OBJECT_REFERENCE, description="ref(human)"),
            "state": Property("state", "state", PropertyType.STRING, required=True,
                              options=["inactive","active","closed"], description="enum"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="presentation", display_name="呈现",
        description="一块显示输出的呈现设施（渲染器＋合成器）。★ 不归人、不记人/空间；一块屏一个；只合“此刻 shown 的画布”。",
        primary_key="name",
        metadata={"wc_id":"wc:ont20261018_02","instance_mode":"many"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "host": Property("host", "host", PropertyType.OBJECT_REFERENCE, description="ref(computer)"),
            "state": Property("state", "state", PropertyType.STRING, required=True,
                              options=["awaiting-human","active","locked"], description="enum"),
            "compositor_kind": Property("compositor_kind", "compositor_kind", PropertyType.STRING,
                                        options=["browser","gtk3","flutter","none"],
                                        description="实现（个人化偏好不在这里）"),
        },
    ))
    o.register_object_type(ObjectType(
        type_id="computer", display_name="计算机",
        description="这台机器在世界里的代言与执行（计算机；一个进程／一个类／一个个体）。★ 10-17 裁：只加一个计算机类，不立 filesystem/disk/netif 类；状态不做实时存储，用动作现查。",
        primary_key="name",
        metadata={"wc_id":"wc:ont20261018_03","instance_mode":"one"},
        properties={
            "name": Property("name", "name", PropertyType.STRING, required=True, is_primary_key=True),
            "hostname": Property("hostname", "hostname", PropertyType.STRING),
            "owner": Property("owner", "owner", PropertyType.OBJECT_REFERENCE, description="ref(human)"),
            "bound_to": Property("bound_to", "bound_to", PropertyType.OBJECT_REFERENCE, description="ref(human)"),
            "state": Property("state", "state", PropertyType.STRING, options=["in-service","retired"], description="enum"),
        },
    ))

    # ── 关系类型（3 条）──
    o.register_link_type(LinkType("device-bound-to-human", "device-bound-to-human",
        source_type="device", target_type="human", cardinality=Cardinality.ONE_TO_MANY))
    o.register_link_type(LinkType("service-runs-on-device", "service-runs-on-device",
        source_type="service", target_type="device", cardinality=Cardinality.ONE_TO_MANY))
    o.register_link_type(LinkType("application-speaks-on-port", "application-speaks-on-port",
        source_type="application", target_type="port", cardinality=Cardinality.ONE_TO_MANY))

    # ── ★ 2026-10-18 人侧模型：关系（7 条）──
    o.register_link_type(LinkType("human-has-space", "human-has-space",
        source_type="human", target_type="space", cardinality=Cardinality.ONE_TO_ONE))
    o.register_link_type(LinkType("presentation-hosted-on-computer", "presentation-hosted-on-computer",
        source_type="presentation", target_type="computer", cardinality=Cardinality.ONE_TO_MANY))

    # ── 动作类型（9 个）──
    # ★ effects=[] 与 validation_rules=[] 【故意留空】：我们的动作用「转」（本体只认/盖章/转/记）；
    #   且我们裁定「要形式可判，不是能推理」⇒ 不抄 P 的 eval() 规则。
    o.register_action_type(ActionType(
        action_id="notice.mute", description="把一条通告静音",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不删除那条通告","不替别的通告静音"],"implemented":"has_entry","reversible":True},
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="notice.unmute", description="解除静音",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不删除那条通告","不撤销撤回（`retract_seq` 是另一条路）"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":True},
        required_roles=["agent"],
    ))
    o.register_action_type(ActionType(
        action_id="job.start", description="起一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不自行放行（准不准做由门禁判）","不代替载体执行作业"],"implemented":"has_entry","reversible":True},
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="job.finish", description="结束一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不删除作业记录","不代替载体执行作业"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":True},
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="job.cancel", description="取消一个作业",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不删除作业记录","不把已发生的载体动作变成没发生"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":True},
        required_roles=["agent","human"],
    ))
    o.register_action_type(ActionType(
        action_id="ledger.compact", description="压实账本（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不自行放行（准不准做由门禁判）","不可逆——本能力没有撤销路径"],"implemented":"has_entry","reversible":False},
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="world.rekey", description="换世界的钥匙材料（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"config","not_roles":["不改写已落账的事件","不给自己发许可","不可逆——本能力没有撤销路径"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":False},
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="world.migrate", description="迁移世界（不可逆）",
        parameters=[
            ActionParameter("subject", PropertyType.OBJECT_REFERENCE, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"config","not_roles":["不改写已落账的事件","不自行放行（准不准做由门禁判）","不可逆——本能力没有撤销路径"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":False},
        required_roles=["human"],
    ))
    o.register_action_type(ActionType(
        action_id="presence.report", description="在场者报告自己的状态（**申报面**；「有没有许可」不在这里定，由 `permissions.grants` ＋ `default: deny` 决定）",
        parameters=[
            ActionParameter("subject", PropertyType.STRING, required=True),
        ],
        validation_rules=[], effects=[],
        metadata={"kind":"invoke","not_roles":["不改写已落账的事件","不代表别人报告","不裁定自己有没有许可（由 `permissions.grants` ＋ `default: deny` 决定）"],"implemented":"未定（原因＝按名在 `src/**` 里 0 命中，可能以别的名字实现）","reversible":True},
        required_roles=["human"],
    ))

    # ── 函数（9 个入口）→ OntologyFunction ──
    # ★ 我们的函数只有【入口名】，代码不进本体（判据 _no_command_literal）；endpoint 走总线。
    o.register_function(OntologyFunction(
        function_id="fn.notice.mute",
        display_name="把一条通告静音",
        description="动作 notice.mute 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.notice.mute","inputs_raw":{"subject":"enum(change,act,notice,job)"},"output_raw":"enum(change,act,notice,job)"},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.notice.unmute",
        display_name="解除静音",
        description="动作 notice.unmute 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.notice.unmute","inputs_raw":{"subject":"enum(change,act,notice,job)"},"output_raw":"enum(change,act,notice,job)"},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.job.start",
        display_name="起一个作业",
        description="动作 job.start 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.job.start","inputs_raw":{"subject":"enum(change,act,notice,job)"},"output_raw":"enum(change,act,notice,job)"},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.job.finish",
        display_name="结束一个作业",
        description="动作 job.finish 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.job.finish","inputs_raw":{"subject":"enum(change,act,notice,job)"},"output_raw":"enum(change,act,notice,job)"},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.job.cancel",
        display_name="取消一个作业",
        description="动作 job.cancel 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.job.cancel","inputs_raw":{"subject":"enum(change,act,notice,job)"},"output_raw":"enum(change,act,notice,job)"},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.ledger.compact",
        display_name="压实账本（不可逆）",
        description="动作 ledger.compact 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.OBJECT_REFERENCE},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.ledger.compact","inputs_raw":{"subject":"ref(ledger)"},"output_raw":""},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.world.rekey",
        display_name="换世界的钥匙材料（不可逆）",
        description="动作 world.rekey 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.OBJECT_REFERENCE},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.world.rekey","inputs_raw":{"subject":"ref(world)"},"output_raw":""},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.world.migrate",
        display_name="迁移世界（不可逆）",
        description="动作 world.migrate 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.OBJECT_REFERENCE},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.world.migrate","inputs_raw":{"subject":"ref(world)"},"output_raw":""},
    ))
    o.register_function(OntologyFunction(
        function_id="fn.presence.report",
        display_name="在场者报告自己的状态（**申报面**；「有没有许可」不在这里定，由 `permissions.grants` ＋ `default: deny` 决定）",
        description="动作 presence.report 的实现面（照 P 的 OntologyFunction.describe 形状；★ 不抄 implementation、不抄 effects）",
        input_types={"subject": PropertyType.STRING},
        output_type="STRING",
        metadata={"transport":"bus","endpoint":"bus:world.fn.presence.report","inputs_raw":{"subject":"enum(human,agent,application,service,device,workflow)"},"output_raw":"enum(human,agent,application,service,device,workflow)"},
    ))
    # ── ★★★ 2026-10-17 裁：抄 sysknife 的 178 个动作（载体 action 做庞大）──
    #   作者令（逐字）：「我们他这不是有 176 个吗？那我们全部做成 action……」
    #   ★ 名字／程序／参数从 sysknife 的 ActionSpec 抽出来（MIT，见 distro/carrier/）。
    #   ★ 风险等级【不抄】—— 作者裁：「风险分级不能自动批，这个东西是本体里头批不批」。
    # ── ★ 2026-10-18：人侧动作的【许可条文】（动作由提供者进程注册，不在此建 ActionType）──
    _load_human_side_grants(o)
    _load_sysknife_actions(o)
    return o


if __name__ == "__main__":
    o = build_aios_ontology()
    print("对象类型:", len(o.object_types), list(o.object_types))
    print("关系类型:", len(o.link_types), list(o.link_types))
    print("动作类型:", len(o.action_types), list(o.action_types))
    print("函数    :", len(o.functions), list(o.functions))
    print("机制(metadata):", list(o.metadata))

def _load_human_side_grants(o):
    """★ 2026-10-18：人侧动作的【许可条文】。

    ★ 口径（书 §4.2）：没条文 ⇒ `permissions.default = deny` ⇒ **默认拒绝**。
    ★ 这些动作的 ActionType 不写进 `actions`——由【提供者进程】注册（`registered_by_kind` 决定转给谁）；
      这里只补许可条文，否则 `can_execute` 一律拒。
    ★ 登录 / Permit 未实现 ⇒ 目前是【占位条文】（标“占位”），待人裁后收紧。
    """
    # ★★ 2026-10-18：呈现对外四个动作 ＋ 个人空间三个动作（画布已进呈现内部）
    for _aid, _desc, _params, _roles in [
        ("presentation.show_surface", "给一帧 A2UI ⇒ 画布出现/更新（同一 surfaceId 覆盖）",
         [("surface", PropertyType.STRING, True), ("frame", PropertyType.STRING, True)],
         ["user", "agent", "presence"]),
        ("presentation.retract_surface", "撤下一张画布",
         [("surface", PropertyType.STRING, True)], ["user", "agent"]),
        ("presentation.list_surfaces", "查此刻有哪几张画布（只读）",
         [], ["user", "agent"]),
        ("presentation.get_surface", "查某一张的画布内容（只读）",
         [("surface", PropertyType.STRING, True)], ["user", "agent"]),
        # ★★★ 认证 ＝ 本体的事（★ 本体四件第一件就是「认」）
        #    ★ 作者令（逐字）：「这个密码啥的是不是在本体空间中更合适呢？登录的这个是给个人那啥吗？
        #      当确定登录了以后，再给这个个人空间这块留个信息吧」
        #    ★ 模型学 PAM／OIDC：★ 认证（你是谁）和授权（你能干什么）分开；
        #      ★ 认过 ⇒ 发【票】；★ 别人【只看票，不碰密码】。
        ("identity.authenticate", "认人：验身份凭据，通过则发一张票（★ 密码归本体，不归空间）",
         [("user", PropertyType.STRING, True), ("secret", PropertyType.STRING, False)],
         ["user", "presence"]),
        ("identity.session", "查票：这张票是谁、什么时候过期（只读）",
         [("ticket", PropertyType.STRING, True)], ["user", "agent", "presence"]),
        ("identity.revoke", "销票：主动作废（比如退出）",
         [("ticket", PropertyType.STRING, True)], ["user"]),
        ("space.login", "凭【票】进空间：认过了才给开（★ 不再验密码 —— 密码归本体）",
         [("ticket", PropertyType.STRING, True)], ["user", "presence"]),
        ("space.set_layout", "改布局（摆放归个人空间）",
         [("layout", PropertyType.STRING, True)], ["user", "agent"]),
        ("space.get_layout", "读布局（只读）", [], ["user", "agent"]),
    ]:
        o.register_action_type(ActionType(
            action_id=_aid, description=_desc,
            parameters=[ActionParameter(n, t, required=r) for n, t, r in _params],
            validation_rules=[], effects=[],
            metadata={"kind": "invoke", "implemented": "presentation_process.py / space_process.py",
                      "reversible": True},
            required_roles=_roles,
        ))

    grants = o.metadata.setdefault("permissions", {}).setdefault("grants", {})
    rows = {
        "space.status":         {"who": ["world://user", "world://agent"], "why": "只读状态（占位）"},
        "space.activate":       {"who": ["world://user"], "why": "登录/切换时由接入触发（登录未实现，占位）"},
        "space.deactivate":     {"who": ["world://user"], "why": "登出/切换（登录未实现，占位）"},
        "space.set_wallpaper":  {"who": ["world://user"], "why": "改自己的地盘（占位）"},
        # ★★ 2026-10-18 作者令「撤销画布这个类」⇒ 画布进【呈现内部的一张表】，
        #    ★ 对外只开四个动作（同一 surfaceId 覆盖 ＝ 改）。
        "presentation.show_surface":    {"who": ["world://user", "world://agent", "world://presence", "world://surface"],
                                         "why": "给一帧 A2UI ⇒ 画布出现/更新（占位）"},
        "presentation.retract_surface": {"who": ["world://user", "world://agent"],
                                         "why": "撤下一张画布（占位）"},
        "presentation.list_surfaces":   {"who": ["world://user", "world://agent"],
                                         "why": "查此刻有哪几张（只读；占位）"},
        "presentation.get_surface":     {"who": ["world://user", "world://agent"],
                                         "why": "查某一张的画布内容（只读；占位）"},
        # ★ 个人空间：登录入口 ＋ 布局（摆放归它）
        # ★★★ 认证：★ 谁都能【试图】认（不然登不进去）；★ 但【认过才发票】。
        "identity.authenticate": {"who": ["world://user", "world://presence", "world://surface"],
                                  "why": "认人（★ 谁都可能来认；★ 通过才发票）"},
        "identity.session":      {"who": ["world://user", "world://agent", "world://presence"],
                                  "why": "查票（只读）"},
        "identity.revoke":       {"who": ["world://user"], "why": "销票（退出）"},
        # ★ 进空间要【票】—— ★ 空间【不碰密码】
        "space.login":          {"who": ["world://user", "world://presence", "world://surface"],
                                 "why": "凭票进空间（★ 票由 identity.authenticate 发）"},
        "space.set_layout":     {"who": ["world://user", "world://agent"],
                                 "why": "改布局（摆放归个人空间；占位）"},
        "space.get_layout":     {"who": ["world://user", "world://agent"],
                                 "why": "读布局（只读；占位）"},
        "presentation.retract": {"who": ["world://user", "world://agent"], "why": "撤自己的表达（占位）"},
        "presentation.notify":  {"who": ["world://user", "world://agent"], "why": "向人通知（占位）"},
        "presentation.confirm": {"who": ["world://user"], "why": "人确认（占位）"},
    }
    for name, g in rows.items():
        grants.setdefault(name, g)


def _load_sysknife_actions(o):
    """★ 从 sysknife 抽出的映射表动态建 ActionType（★ 名字用 sys.<PascalName>）。

    文件：AIOS_SYSKNIFE_MAP（默认 /usr/lib/aios/sysknife-command-map.json）
    缺文件 ⇒ 静默跳过（★ 不阻断本体起）。
    """
    path = os.environ.get("AIOS_SYSKNIFE_MAP", "/usr/lib/aios/sysknife-command-map.json")
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0
    n = 0
    grants = o.metadata.setdefault("permissions", {}).setdefault("grants", {})
    for a in data.get("actions", []):
        name = a.get("action") or ""
        if not name or name in o.action_types:
            continue
        try:
            at = ActionType(
                name,
                name,
                description="从 sysknife 抄的动作（MIT）—— 载体执行 %s %s"
                            % (a.get("program", "?"), " ".join(a.get("args") or [])),
                parameters=[],
                effects=[],
                validation_rules=[],
                metadata={
                    "what": "%s" % name,
                    "not_roles": [],
                    "implemented": "sysknife",
                    "program": a.get("program"),
                    "args": a.get("args") or [],
                },
            )
            o.register_action_type(at)
            # ★★ 只读动作（Get*/List*）默认放行：不用人确认（作者裁：批不批归本体）
            # ★ 只读（Get*/List*）免确认；变更类【不给许可】⇒ 默认拒绝 ⇒ 要走人确认
            if name.startswith("sys.Get") or name.startswith("sys.List"):
                grants.setdefault(name, {"who": ["world://user", "world://agent/dsh"],
                                        "why": "只读查询（从 sysknife 抄，MIT）"})
            n += 1
        except Exception:
            continue
    return n
