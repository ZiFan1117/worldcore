//! 本体（法律）：加载出厂词表，并校验一条语义事件是否合法。
//!
//! 本体是「世界的法律」——它规定"一条事件长什么样、什么算合法变更"。
//! 它**不是**代码里的硬编码常量，而是**运行时装起来的纯文本文件**（出厂设置）。
//! 依 `07/2-依据/15-世界核心的组成与职责.md` §2.3：本体是"装起来的"，
//! 方式是「运行时装 + 用内容寻址钉住版本」。

use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::fs;
use std::path::Path;

/// 校验失败的原因。**类型化**——上层按码处理，不靠散文猜失败原因。
#[derive(Debug, PartialEq)]
pub enum Violation {
    NotAnObject,
    MissingField {
        at: String,
        field: String,
    },
    BadVersion {
        expected: u64,
        got: u64,
    },
    UnknownKind {
        kind: String,
    },
    /// **类型不符**（这一格在，但形状不对——本体声明了它该是什么类型）。
    ///
    /// 与 [`Violation::MissingField`] 分开：那是"该有的格没读到"，这是"格在、形状不对"。
    /// 两者都是**可编程判定**的类别，故按码分开、不合并成一句散文。
    BadFieldType {
        at: String,
        field: String,
        want: String,
        got: String,
    },
    /// **实体没声明过**（`concepts` 里没有它）——声明以外的东西不许落账。
    ///
    /// `known` = 本体里**已声明**的实体名（有序、逗号分隔）：报错要让人当场知道
    /// "哪些是能写的"，否则这条错误只说了"不行"，没说"怎么办"。
    UndeclaredEntity {
        entity: String,
        subject: String,
        known: String,
    },
    /// **字段没声明过**（实体声明了，但这个字段不在它的字段表里）。
    UndeclaredField {
        entity: String,
        field: String,
        subject: String,
        known: String,
    },
    /// **五要素缺节**：本体里少了五要素之一（对象／关系／接口·能力／动作／函数）。
    ///
    /// 为什么是**拒启**而不是警告：五要素是这部法律的**骨架**——少一节，本体的
    /// "世界里存在什么／哪两类东西能连／这类东西能被怎样对待／怎么改／怎么算"
    /// 就有一整面没有声明面，而**没有任何东西会因此变红**（那正是"法律没写全"
    /// 被读成"什么都允许"的形状）。故缺失即 `Ontology::load` 失败（与坏 JSON 同档）。
    MissingSection {
        /// 缺的是哪一节（五要素名，人可读）。
        element: String,
        /// 装载器实际去找的顶层键。
        keys: String,
    },
    /// **对象字段的值类型不符**（`_objects` 声明了 `muted: bool`，而事件写了个整数）。
    BadFieldValueType {
        entity: String,
        field: String,
        subject: String,
        want: String,
        got: String,
    },
    /// **内嵌标记未声明**：这个类型声明了自己是**内嵌**的（`nested: true`），
    /// 而实例路径 `world://<父类型>/<父实例>/<本类型>/<本实例>` 里那一段父类型不是声明的父。
    UndeclaredEmbeddedMarker {
        entity: String,
        subject: String,
        want_parent: String,
        got_parent: String,
    },
    /// **关系端点未声明**：`_links` 的 `from`／`to` 指到一个没在 `_objects` 里声明的类型。
    UndeclaredRelationEndpoint {
        link: String,
        endpoint: String,
        side: String,
        known: String,
    },
    /// **动作引用了不存在的能力**（`_actions.<动作>.capability` 指不到 `_interfaces`）。
    ActionCapabilityUnknown {
        action: String,
        capability: String,
        known: String,
    },
    /// **函数入口表里出现了命令字面量**（命令是**硬编码在代码里**的事实，不许抄进本体）。
    FunctionLiteralNotAllowed {
        entry: String,
        why: String,
    },
    /// **许可授在具体类型／具体对象上**（授权只许授在**能力**上）。
    GrantNotOnCapability {
        granted: String,
        known: String,
    },
    /// **许可是默认允许的**（`_permissions.default` 没写、或写的不是 `deny`）。
    PermissionDefaultOpen {
        got: String,
    },
    /// **两处对象声明各说各话**：`_objects`（读路径认它）与 `concepts`（身份认它）
    /// 里**同名字段**的类型声明**逐字不一致**。
    ///
    /// 为什么要拒启：这两处**分工不同**——`_objects` 决定"读到什么语义"、
    /// `concepts` 决定"算出什么身份"。两者不一致时，**同一份本体**会同时给出
    /// 两个互相矛盾的答案（"这一格是 `enum(a,b)`"与"这一格是 `enum(a,b,c)`"），
    /// 而**没有任何东西会因此变红**。⇒ 与"法律自相矛盾"同档：拒启。
    ConceptsDrift {
        entity: String,
        field: String,
        in_objects: String,
        in_concepts: String,
    },
    /// **归属表与文件里的 `_` 分节集合不一致**（`_section_map` 是十二节归属的权威）。
    ///
    /// 为什么要拒启：`_section_map` 写死了"哪一节属五要素／属元层／属接入层"。
    /// 若文件里**新加**了一个 `_` 分节而没在表里列名（或表里声明了文件里没有的分节），
    /// 那条"归属已定"的话就当场变成假话——而**没有任何东西会因此变红**。
    SectionMapDrift {
        detail: String,
    },
    /// ★ **死入口**：`_functions.entries` 里声明了入口，而**没有任何动作引用它**。
    ///
    /// 为什么拒启：函数**不改本体**，它落地的唯一途径是**被动作引用、由该动作执行**
    /// ⇒ 一个没人引用的入口，**在这部法律里永远走不到**。它不是"暂时没用"，
    /// 是**结构上不可达**——而那与「法律的本分是先声明后使用」**不是一回事**
    /// （后者说的是"实例还没用上"，见 `world-core usage` 那份**只报告**的清单）。
    DeadFunctionEntry {
        entry: String,
        known: String,
    },
    /// ★ **悬空引用**：动作声明了它调用的函数入口，而 `_functions.entries` 里**没有这个入口**。
    DanglingFunctionRef {
        action: String,
        entry: String,
        known: String,
    },
    /// ★ **死能力**：`_interfaces` 里声明了能力，而它**既无任何动作引用、也无任何许可授予**。
    ///
    /// ## 与策略侧那条**不是同一条**（射程分开，避免重复造判据）
    ///
    /// | 判据 | 在哪 | 判什么 | 射程 |
    /// |---|---|---|---|
    /// | `ext.world.Gate.CapabilityWithoutAction` | `policy.json`／`src/gate/mod.rs` | `config`／`invoke` 能力**必须有动作** | **不看许可**；`read` **豁免** |
    /// | 本条 `DeadCapability` | `ontology.json`／本模块 | 能力**既无动作、又无许可授予** | **看两处**；**不看 `kind`** |
    ///
    /// ⇒ 两处**各判一半**：策略侧管"闸上有没有动作能走到它"，本体侧管"法律上有没有人能用它
    /// （动作或授权，二者有其一即可）"。**不许**把两处合成一条——它们读的是**两份不同的法律文件**。
    DeadCapability {
        capability: String,
        kind: String,
        known_actions: String,
    },
    /// ★ **载体专有物进了本体**（而且进的是**参与身份**的那一半）。
    ///
    /// 判据①a：本体是**世界的说法**，不是**某个载体怎么起**。
    /// `ontology.json` 里**非 `_` 前缀**的内容参与 `vocab_hash`——它是"法律"；
    /// 一旦往里写 `systemd`／`.service`／`ListenStream` 这类串，
    /// **换掉载体就得换法律**（而法律是内容寻址的 ⇒ 换一个字就换掉整个世界的身份）。
    /// ⇒ 拒启，并点名是哪个路径上的哪个串。
    ///
    /// ⚠️ **射程**（如实声明）：只扫**参与身份**的那一半（非 `_` 键，与 `vocab_hash_of`
    /// 的剔法**同源**）。`_` 键里的说明文字**不判**——它们不进身份，且本来就该能写
    /// 「这条今天落在 `policy.json` 的 `listeners`」这类**指路**的话。
    CarrierSpecificInOntology {
        path: String,
        token: String,
        found_in: String,
    },
}

impl fmt::Display for Violation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Violation::NotAnObject => {
                write!(f, "ext.world.Ontology.NotAnObject: 事件必须是 JSON 对象")
            }
            Violation::MissingField { at, field } => {
                write!(
                    f,
                    "ext.world.Ontology.MissingField: {at} 缺少必填字段 `{field}`"
                )
            }
            Violation::BadVersion { expected, got } => write!(
                f,
                "ext.world.Ontology.BadVersion: 词表版本不符（期望 {expected}，实得 {got}）"
            ),
            Violation::UnknownKind { kind } => {
                write!(f, "ext.world.Ontology.UnknownKind: 未知家族 `{kind}`")
            }
            Violation::BadFieldType {
                at,
                field,
                want,
                got,
            } => write!(
                f,
                "ext.world.Ontology.BadFieldType: {at} 的 `{field}` 类型不符（本体声明 `{want}`，实得 `{got}`）"
            ),
            Violation::UndeclaredEntity {
                entity,
                subject,
                known,
            } => write!(
                f,
                "ext.world.Ontology.UndeclaredEntity: 实体 `{entity}` 未在出厂本体里声明\
                 （ontology.json 的 concepts 段）——**声明以外的东西不许落账**。\n\
                 \x20 本次写入的 subject 是 `{subject}`；已声明的实体：{known}。\n\
                 \x20 处置：改用已声明的实体，或先在出厂本体里声明它（改本体＝改法律，走评审）"
            ),
            Violation::UndeclaredField {
                entity,
                field,
                subject,
                known,
            } => write!(
                f,
                "ext.world.Ontology.UndeclaredField: 字段 `{field}` 未在实体 `{entity}` 下声明\
                 （ontology.json 的 concepts.`{entity}`.fields）——**声明以外的字段不许落账**。\n\
                 \x20 本次写入的 subject 是 `{subject}`；实体 `{entity}` 已声明的字段：{known}。\n\
                 \x20 处置：改用已声明的字段，或先在出厂本体里声明它（改本体＝改法律，走评审）"
            ),
            Violation::MissingSection { element, keys } => write!(
                f,
                "ext.world.Ontology.MissingSection: 出厂本体缺少五要素之一——**{element}**（装载器找的是顶层键 {keys}）。\n\
                 \x20 五要素是这部法律的骨架（对象／关系／接口·能力／动作／函数）：少一节，那一整面就没有\
                 **声明面**，而没有任何东西会因此变红 —— 那正是「法律没写全」被读成「什么都允许」的形状。\n\
                 \x20 处置：在出厂本体的 `_` 前缀顶层键下补齐该节（挂 `_` 键**不换词表身份**），\
                 或先在评审里把这一节的存在性口径去掉（改法律＝走评审）"
            ),
            Violation::BadFieldValueType {
                entity,
                field,
                subject,
                want,
                got,
            } => write!(
                f,
                "ext.world.Ontology.BadFieldValueType: 实体 `{entity}` 的字段 `{field}` **值类型不符**\
                 （本体声明 `{want}`，实得 `{got}`）。\n\
                 \x20 本次写入的 subject 是 `{subject}`。\n\
                 \x20 处置：写符合声明类型的值；若这一格本来就该收别的类型，改的是**本体**（改法律＝走评审）"
            ),
            Violation::UndeclaredEmbeddedMarker {
                entity,
                subject,
                want_parent,
                got_parent,
            } => write!(
                f,
                "ext.world.Ontology.UndeclaredEmbeddedMarker: `{entity}` 声明为**内嵌**类型\
                 （父类型 `{want_parent}`），但 subject `{subject}` 的父实例段是 `{got_parent}`。\n\
                 \x20 内嵌**不能靠三段式 `world://a/b/c` 表达**（三段式的首段仍是类型，见 §`entity_of`）——\
                 它靠 `_objects.<类型>` 里的**声明式内嵌标记**（`nested` ＋ `part_of`）表达，\
                 实例路径必须是 `world://<父类型>/<父实例>/<本类型>/<本实例>`。\n\
                 \x20 处置：把 subject 改成内嵌形态，或把该类型的内嵌标记去掉（改法律＝走评审）"
            ),
            Violation::UndeclaredRelationEndpoint {
                link,
                endpoint,
                side,
                known,
            } => write!(
                f,
                "ext.world.Ontology.UndeclaredRelationEndpoint: 关系 `{link}` 的 `{side}` 端\
                 指向未声明的类型 `{endpoint}`（ontology.json 的 `_objects`）。\n\
                 \x20 已声明的类型：{known}。\n\
                 \x20 处置：改用已声明的类型，或先在 `_objects` 里声明它（改法律＝走评审）"
            ),
            Violation::ActionCapabilityUnknown {
                action,
                capability,
                known,
            } => write!(
                f,
                "ext.world.Ontology.ActionCapabilityUnknown: 动作 `{action}` 引用了**不存在的能力**\
                 `{capability}`（ontology.json 的 `_interfaces`）。\n\
                 \x20 已声明的能力：{known}。\n\
                 \x20 处置：改用已声明的能力，或先在 `_interfaces` 里声明它——\
                 动作是「怎么改」，它必须挂在一个「能被怎样对待」上，否则这次改没有法律依据"
            ),
            Violation::FunctionLiteralNotAllowed { entry, why } => write!(
                f,
                "ext.world.Ontology.FunctionLiteralNotAllowed: 函数入口表里的 `{entry}` \
                 是**命令字面量**（{why}）。\n\
                 \x20 为什么不许：本表只收**入口名**（引用到底层函数）；命令今天硬编码在代码里\
                 （`src/carrier/**`），把它抄进本体等于让本体长出**第二份可执行事实**——\
                 两份一旦漂移，读本体的人会以为某条命令是法律规定的。\n\
                 \x20 处置：只写入口名；命令留在代码里（它属实现，不属法律）"
            ),
            Violation::GrantNotOnCapability { granted, known } => write!(
                f,
                "ext.world.Ontology.GrantNotOnCapability: 许可授在 `{granted}` 上——**授权只许授在能力上**\
                 （不许授在具体类型或具体对象上）。\n\
                 \x20 已声明的能力：{known}。\n\
                 \x20 处置：把许可改成对某个**能力**的授权（`_permissions.grants.<能力名>`）；\
                 对具体对象的授权是**事实**，走账本事件，不写进条文"
            ),
            Violation::PermissionDefaultOpen { got } => write!(
                f,
                "ext.world.Ontology.PermissionDefaultOpen: `_permissions.default` 是 `{got}`\
                 ——**默认允许不是安全默认，是法律没写全**。\n\
                 \x20 处置：把 `default` 显式写成 `\"deny\"`，再用 `grants` 逐条授予"
            ),
            Violation::ConceptsDrift {
                entity,
                field,
                in_objects,
                in_concepts,
            } => write!(
                f,
                "ext.world.Ontology.ConceptsDrift: 两处对象声明**各说各话**——类型 `{entity}` 的字段 `{field}`：\n\
                 \x20  · `_objects`（**读路径**认它）说 `{in_objects}`；\n\
                 \x20  · `concepts`（**身份**认它，参与 vocab_hash）说 `{in_concepts}`。\n\
                 \x20 两处分工不同（一处定「读到什么语义」、一处定「算出什么身份」），不一致时\
                 **同一份本体同时给出两个互相矛盾的答案**，而没有任何东西会因此变红。\n\
                 \x20 处置：把两处改成**逐字一致**（若这一格本来就要改语义，两处一起改；\
                 改 `concepts` 会换词表身份，属框架变更，走评审）"
            ),
            Violation::SectionMapDrift { detail } => write!(
                f,
                "ext.world.Ontology.SectionMapDrift: 十二节**归属表**与文件里的 `_` 分节集合不一致。\n\
                 \x20 {detail}\n\
                 \x20 为什么拒启：`_section_map` 写死了「哪一节属五要素／属元层／属接入层」。\
                 文件与表对不上时，那句「归属已定」当场变成假话，而**没有任何东西会因此变红**。\n\
                 \x20 处置：新加 `_` 分节 ⇒ **同时在 `_section_map.sections` 里给它归属**（不许重命名\
                 另一节去凑）；只加说明文字 ⇒ 在 `_section_map._not_domain_sections` 里列名"
            ),
            Violation::DeadFunctionEntry { entry, known } => write!(
                f,
                "ext.world.Ontology.DeadFunctionEntry: **死入口**——`_functions.entries` 里的 `{entry}` \
                 **没有任何动作引用它**。\n\
                 \x20 已声明的动作：{known}\n\
                 \x20 为什么拒启：函数**不改本体**，它落地的唯一途径是**被动作引用、由该动作执行**\
                 （书 §3.5「操作是唯一写入通道，函数也不例外」）⇒ 没人引用的入口\
                 **在这部法律里永远走不到**，它不是「暂时没用」，是**结构上不可达**。\n\
                 \x20 处置：让某条动作引用它（`_actions.<动作>.function = \"{entry}\"`），\
                 或把这一条入口从 `_functions.entries` 里去掉（改法律＝走评审）"
            ),
            Violation::DanglingFunctionRef {
                action,
                entry,
                known,
            } => write!(
                f,
                "ext.world.Ontology.DanglingFunctionRef: 动作 `{action}` 声明它调用入口 `{entry}`，\
                 而 `_functions.entries` 里**没有这个入口**（悬空引用）。\n\
                 \x20 已声明的入口：{}\n\
                 \x20 处置：改用已声明的入口，或先在 `_functions.entries` 里声明它（改法律＝走评审）",
                if known.is_empty() { "（空表）" } else { known }
            ),
            Violation::DeadCapability {
                capability,
                kind,
                known_actions,
            } => write!(
                f,
                "ext.world.Ontology.DeadCapability: **死能力**——`_interfaces` 里的 `{capability}`\
                 （kind={kind}）**既无任何动作引用、也无任何许可授予**。\n\
                 \x20 已声明的动作：{known_actions}\n\
                 \x20 为什么拒启：一项能力**没有任何人能用它**（动作走不到它、许可也没授给谁）\
                 ⇒ 它在法律上是**不可达**的声明，读法律的人却会以为它能用。\n\
                 \x20 ⚠️ 与策略侧 `ext.world.Gate.CapabilityWithoutAction` **不是同一条**：\
                 那条只管「`config`／`invoke` 必须有动作」且不看许可（`read` 豁免）；\
                 本条看**动作或许可**两处。\n\
                 \x20 处置：给它加一条动作（`_actions.<动作>.capability = \"{capability}\"`），\
                 或在 `_permissions.grants` 里授予它（二者有其一即算可达）"
            ),
            Violation::CarrierSpecificInOntology {
                path,
                token,
                found_in,
            } => write!(
                f,
                "ext.world.Ontology.CarrierSpecificInOntology: 本体里出现了**载体专有串** `{token}`\
                 （在 `{path}` 的 {found_in}）。\n\
                 \x20 为什么拒启：本体是**世界的说法**，不是**某个载体怎么起**（同级不同物——\
                 载体管资源，世界管说法）。而 `ontology.json` 的**非 `_` 键**参与 `vocab_hash`\
                 ⇒ 往里写载体专有物，等于**换掉载体就得换法律**。\n\
                 \x20 ⚠️ 射程：只扫**参与身份**的那一半（非 `_` 键，与 `vocab_hash_of` 剔法同源）；\
                 `_` 键里的说明文字不判。\n\
                 \x20 处置：把载体怎么起的话挪出本体（写进部署件或 `_` 键里的**指路**说明）；\
                 本体里只留**世界的说法**（改法律＝走评审）"
            ),
        }
    }
}

impl std::error::Error for Violation {}

#[derive(Debug)]
struct Family {
    required: Vec<String>,
    #[allow(dead_code)]
    optional: Vec<String>,
}

/// **一个对象类型**（五要素之一「对象」的单元）：`_objects.<类型>`／`concepts.<类型>`。
///
/// 三样东西都用**纯数据**装着（`Ontology` 之外的人不该拿到内部句柄）：
/// 属性表（名字 → 机器可读的**类型声明**）、内嵌标记、实例模式。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObjectType {
    /// 属性名 → 类型声明串（`bool`／`string`／`enum(a,b)`／`ref(<类型>)`／…）。
    ///
    /// ⚠️ **值不再只是"自由文本说明"**（本批改口径）：认得出来的类型词**参与校验**
    /// （[`Ontology::check_concepts`] 判值类型、`enum(...)` 按**闭集**判，
    /// **`kind` 除外**——家族名走家族查找，见 [`Ontology::validate_types`]）。
    /// **不认得的写法一律放行**——本体没声明的类型口径，判据不替它发明
    /// （要收窄，就往本体里写一条认得的声明，并配一条反例）。
    pub fields: BTreeMap<String, String>,
    /// **内嵌标记**：`Some(父类型)` ＝ 这个类型的实例必须内嵌在父类型的一个实例里。
    ///
    /// 为什么内嵌要**声明式**表达，而不是靠三段式 `world://a/b/c`：
    /// 见 [`Ontology::entity_of`] 与 [`Ontology::check_concepts`] 的口径说明。
    pub part_of: Option<String>,
    /// **实例模式**：`single`（至多一个实例）／`many`（不限）／`Some(n)`（上限 n）。
    ///
    /// `None` ＝ 这一节没声明 ⇒ **按"不限"读**，但这一格会被
    /// [`Ontology::instance_limits`] 过滤掉（没声明就不是判据）。
    pub max_instances: Option<u64>,
}

/// **一条关系**（五要素之二「关系」）：命名关系 ＋ 两端类型 ＋ 基数。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkDecl {
    /// 源端类型名（必须已在 `_objects` 里声明）。
    pub from: String,
    /// 目标端类型名（必须已在 `_objects` 里声明）。
    pub to: String,
    /// 基数：`one`（单值）／`many`（多值）／`one-to-many` 之类的自由记法今天**不解释**。
    ///
    /// 本批只把**声明**装进来（判据读得到它）；基数的运行时裁决落在读模型侧
    /// （[`crate::ontology_instance::readmodel::DeclaredCells`] 的实例上限），本批不扩。
    pub card: String,
    /// 是否双向。
    pub bidirectional: bool,
}

/// **一个能力**（五要素之三「接口·能力」）：可读／可配／可调。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapabilityDecl {
    /// `read`（可读）／`config`（可配）／`invoke`（可调）。
    pub kind: String,
    /// 这能力"是什么"的一句话（人读）。
    pub what: String,
}

/// **一个动作**（五要素之四）：它必须引用一个已声明的能力。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ActionDecl {
    /// 引用的**能力名**（必须已在 `_interfaces` 里声明）。
    pub capability: String,
    /// 这次改动退不退得回来（闸的摩擦挂在它上面）。
    pub reversible: bool,
    /// ★ **这条动作调用的函数入口**（`_functions.entries` 里的名字；`None`＝不调函数）。
    ///
    /// ## 为什么这条引用边是必须的（而不是可有可无的糖）
    ///
    /// 五要素之五「函数」的**存在方式**就是"**被动作引用**"：本表只收入口名（引用），
    /// 代码不进本体；函数自己不改本体——**要落地，唯一途径是被某个动作引用、由该动作执行**。
    /// ⇒ 没有这条边，"某个入口到底有没有人用"这件事**问不出来**，
    /// 于是「死入口」这条判据就是**空的**（要么它恒红——所有入口都死；要么它不判）。
    ///
    /// ⚠️ **射程**（如实声明，不假装更宽）：一条动作今天**最多引用一个**入口。
    /// 要"一条动作调多个函数"，作为扩展走评审（本批不扩）。
    pub function: Option<String>,
}

/// **函数入口表里的一条**（五要素之五）：**只有入口名**（引用），代码不进本体。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FunctionDecl {
    /// 入口名（引用到底层函数）；不含命令字面量。
    pub entry: String,
    /// 这函数算什么（一句话）。
    pub what: String,
}

/// **许可条文**（并入本体，但**不是**能力本身）：授权只许授在能力上。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionDecl {
    /// 谁有资格授予／收回。
    pub who: Vec<String>,
    /// 授给谁（主体模式）。
    pub scope: Vec<String>,
}

/// 出厂本体。加载后即为本次运行的"法律"。
#[derive(Debug)]
pub struct Ontology {
    world: u64,
    required: Vec<String>,
    optional: Vec<String>,
    /// **信封每个字段的类型声明**（`envelope.fields` 段：名字 → 声明串，如 `"integer  # 词表版本…"`）。
    ///
    /// 为什么单独存：`required` 只说明"这一格必须在"，**不说明它该是什么类型**。
    /// 缺了这一段，"类型不符"就无从判起——实测两处真实违规：`world` 写成字符串 `"1"`、`actor` 写成整数 `123`，
    /// 折叠层**都收下了**（`state` rc=0）。声明串**首词**即类型（`integer`／`string`／`array`／`object`／`enum(a, b)`）。
    env_types: BTreeMap<String, String>,
    families: BTreeMap<String, Family>,
    /// **实体与字段的声明**（五要素之一「对象」的权威读出）。
    ///
    /// 这一段的用途（书第五章 §5.3 逐字）：「它管两件事：什么算世界里存在的东西，
    /// 什么算一次说得通的改变。」⇒ 落笔前必须查它（[`Ontology::check_concepts`]）。
    ///
    /// ## 两处来源：**身份** 与 **读路径** 各认一处（本批的刻意处置）
    ///
    /// | 顶层键 | 谁认它 | 参与 `vocab_hash`？ |
    /// |---|---|---|
    /// | `_objects` | **读路径**（`check_concepts`／`declared_fields`／实例上限／内嵌标记） | **否**（`_` 前缀被 `vocab_hash_of` 剔除） |
    /// | `concepts` | **身份**（`vocab_hash` 的输入）＋ `_objects` 缺席时**退回读** | **是**（非 `_` 键） |
    ///
    /// 为什么这么分：出厂本体的 `vocab_hash` 是**内容地址**，已被
    /// `tests/family_readmodel.rs` 的 `assert_eq!(ont.vocab_hash(), "fnv1a64:6a96abfa9a969462")`
    /// 与多份文档钉死 ⇒ 改它必须**同批同步全仓**（本批已按此口径同步一次）。而五要素分节要能**独立增补**
    /// ★（2026-10-04 批注：原写「本批不许换身份」已被**两次**变更先后推翻——R5 给 `notice.fields` 加 `retract_seq`（`fnv1a64:4bf7b75573fee475`→`fnv1a64:8fd52bc278110ce8`）、本批加**统一类型** `presence`（`fnv1a64:8fd52bc278110ce8`→`fnv1a64:6a96abfa9a969462`）；**判据本身未放宽**。）
    /// （`instance_mode`／内嵌标记／实例上限）——那些增补都只能挂 `_` 键。
    ///
    /// ## ⚠️ **两份今天可能各说各话**（如实声明，不粉饰）
    ///
    /// 绝不能读成"两份必然一致"：**只改 `_objects` ⇒ 身份不变而读到的语义变了；
    /// 只改 `concepts` ⇒ 读到的语义不变而身份变了。** 这个缝本批**新补了一条判据**去闭合：
    /// [`check_frozen_mirror`] —— 两处**同名字段**的类型声明必须**逐字**一致，
    /// 不一致即拒启（`ext.world.Ontology.ConceptsDrift`）。
    ///
    /// ⚠️ 该判据的**射程**（不许被读成"两份完全等价"）：只判**两处都有**的那个字段的类型声明。
    /// - `_objects` 里**新增**、`concepts` 里没有的字段 ⇒ **不判**（新字段本该只声明一次）；
    /// - `_objects` 里有的实体、`concepts` 里整个没有 ⇒ **不判**（纯扩展的常态）；
    /// - 两处的**字段集合是否相同**、`instance_mode`／`nested`／`part_of` 是否同步 ⇒ **不判**
    ///   （那三样**只**长在 `_objects` 里，因为往 `concepts` 里加一个字就换身份）。
    objects: BTreeMap<String, ObjectType>,
    /// **命名关系**（五要素之二）：名字 → 声明。
    links: BTreeMap<String, LinkDecl>,
    /// **能力**（五要素之三）：名字 → 声明。授权只许授在这些名字上。
    interfaces: BTreeMap<String, CapabilityDecl>,
    /// **动作**（五要素之四）：名字 → 声明（每条引用一个能力）。
    actions: BTreeMap<String, ActionDecl>,
    /// **函数入口表**（五要素之五）：入口名 → 声明。**只有入口名**，没有代码。
    functions: BTreeMap<String, FunctionDecl>,
    /// **许可条文**：授权授在能力上；`default` 必须显式 `deny`。
    permissions: BTreeMap<String, PermissionDecl>,
    /// `_permissions.default` 的原文（判据读它：必须逐字 `deny`）。
    permission_default: String,
    /// 词表的**内容地址**（见 [`Ontology::vocab_hash`]），加载时算好。
    vocab_hash: String,
}

/// **解析一处对象声明**（`_objects` 或 `concepts`；两者形态相同）。
///
/// 抽成函数而不是内联两遍：两处的**形态必须完全一样**（否则镜像判据比的是两种不同的解析
/// 结果，比出来的是解析差异而不是声明差异）。抽一处 = 只有一个解析口径。
///
/// 口径（三条，都可判真假）：
/// 1. 下划线开头的键不是对象类型（`_comment` 是说明文字）；
/// 2. 字段的**值**是类型声明串（`bool`／`enum(a,b)`／`ref(x)`…）——**本轮起参与校验**；
/// 3. `instance_mode`／`max_instances`／`nested`／`part_of` **只在这里读**（那四格
///    只长在 `_objects` 里：往 `concepts` 里加一个字就换词表身份）。
fn parse_object_section(
    cs: &serde_json::Map<String, Value>,
) -> Result<BTreeMap<String, ObjectType>, String> {
    let mut out: BTreeMap<String, ObjectType> = BTreeMap::new();
    for (entity, def) in cs {
        if entity.starts_with('_') {
            continue;
        }
        let mut fields = BTreeMap::new();
        if let Some(fs_obj) = def.get("fields").and_then(Value::as_object) {
            for (name, ty) in fs_obj {
                if name.starts_with('_') {
                    continue;
                }
                fields.insert(name.clone(), ty.as_str().unwrap_or_default().to_string());
            }
        }
        // **内嵌标记**：`nested: true` ＋ `part_of: "<父类型>"`；或只给 `part_of`。
        // 两者取并集：只写 `part_of` 也算内嵌（少了 `nested` 不改变它是内嵌这件事）。
        let part_of = match def.get("part_of").and_then(Value::as_str) {
            Some(p) if !p.is_empty() => Some(p.to_string()),
            _ if def.get("nested").and_then(Value::as_bool) == Some(true) => {
                return Err(format!(
                    "ext.world.Ontology.BadField: 类型 `{entity}` 声明 `nested: true` \
                     但没给 `part_of`（父类型名）——内嵌标记必须说清**嵌在哪个类型里**"
                ))
            }
            _ => None,
        };
        // **实例模式**：`instance_mode` 三值 `single`／`many`；或直接给 `max_instances`。
        let max_instances = match def.get("instance_mode").and_then(Value::as_str) {
            Some("single") => Some(1),
            Some("many") | None => def.get("max_instances").and_then(Value::as_u64),
            Some(other) => {
                return Err(format!(
                    "ext.world.Ontology.BadField: 类型 `{entity}` 的 `instance_mode` 是 \
                     `{other}`——只认 `single`／`many`（或直接给 `max_instances: <数>`）"
                ))
            }
        };
        out.insert(
            entity.clone(),
            ObjectType {
                fields,
                part_of,
                max_instances,
            },
        );
    }
    Ok(out)
}

/// ★ **镜像判据**：`_objects`（**读路径**认它）与 `concepts`（**身份**认它）里
/// **同名字段**的类型声明必须**逐字一致** ⇒ 不一致即拒启（`ConceptsDrift`）。
///
/// ## 为什么必须有这一条
///
/// 两处**分工不同**（一处定"读到什么语义"、一处定"算出什么身份"），而本批把五要素分节
/// 全挂到了 `_` 键下 ⇒ 读路径走 `_objects`、身份走 `concepts`。若只有分工、没有一致性判据，
/// **同一份本体**就会同时给出两个互相矛盾的答案（"这一格是 `enum(a,b)`"与
/// "这一格是 `enum(a,b,c)`"），而**没有任何东西会因此变红**——本项目最贵的那一类错。
///
/// ## 射程（**不许**被读成"两处完全等价"）
///
/// | 情形 | 判不判 |
/// |---|---|
/// | 两处**都有**该类型、**都有**该字段、类型声明串**不同** | **判（拒启）** |
/// | 两处都有该字段、声明串**相同** | 放行 |
/// | `_objects` 有该字段、`concepts` 没有 | **不判**（新字段本该只声明一次） |
/// | `concepts` 有该字段、`_objects` 没有 | **不判**（`concepts` 是冻结映射，可能留有旧格） |
/// | 该类型只在一处出现 | **不判**（纯扩展的常态） |
/// | `instance_mode`／`nested`／`part_of` 两处不同步 | **不判**（那三样**只**长在 `_objects` 里） |
///
/// ⇒ 它闭合的是"**同一个字段、两处说法不一**"这一条缝；**不**闭合"两处的字段集合是否相同"。
/// 后者今天**没有**判据，如实登记在 `_pending_tables` 之外的本处文档里，不假装已闭合。
fn check_frozen_mirror(
    objects: &BTreeMap<String, ObjectType>,
    frozen: &BTreeMap<String, ObjectType>,
) -> Result<(), String> {
    for (entity, o) in objects {
        // 该类型在 `concepts` 里没有 ⇒ 纯扩展，不判（射程表第 5 行）。
        let Some(f) = frozen.get(entity) else {
            continue;
        };
        for (field, ty) in &o.fields {
            // 该字段在 `concepts` 里没有 ⇒ 新格，不判（射程表第 3 行）。
            let Some(fty) = f.fields.get(field) else {
                continue;
            };
            if fty != ty {
                return Err(Violation::ConceptsDrift {
                    entity: entity.clone(),
                    field: field.clone(),
                    in_objects: ty.clone(),
                    in_concepts: fty.clone(),
                }
                .to_string());
            }
        }
    }
    Ok(())
}

/// ★ **十二节归属表的一致性**（`_section_map` 是"哪一节挂在哪"的权威）：
/// 表里声明的 `_` 分节键集合必须**逐项等于**文件里**实际存在**的 `_` 分节键集合。
///
/// ## 判四条（都可判真假、都拒启）
///
/// | # | 判据 | 反例（必红） |
/// |---|---|---|
/// | 1 | 每一项的 `home` 必须取自 `_homes` 这张**封闭表**（归属不许自由发挥） | 把 `home` 写成表里没有的词 |
/// | 2 | 每一项的 `attach` 必须 ∈ `{full, half, out}` | 把 `attach` 写成别的 |
/// | 3 | 每一项必须**说清载体**：要么给 `keys`（承载它的 `_` 分节），要么给 `_where`（今天落在哪）——不许留空 | 既没 `keys` 也没 `_where` |
/// | 4 | ★ **集合相等**：`∪ keys`（表里声明、且文件里**真有**的分节）**==** 实际的 `_` 分节
/// （＝全部顶层 `_` 键 − `_not_domain_sections` 里列名的键） | 新加一个 `_` 分节而不在表里列名 |
///
/// ## 为什么这条判据必须存在（它就是"归属写死"的执行者）
///
/// 光把归属**写进** `_section_map` 是**装饰**：文件里新加一个 `_` 分节、或表里指错一个键，
/// 都不会有东西变红 ⇒ "归属已定"这句话会悄悄变成假话。
/// ⇒ 判据 4 是**双向**的：表里多一处、文件里多一处，**两个方向都拒启**。
///
/// ## 射程（如实声明）
///
/// - 它判**集合**，**不判**"某节的归属选得对不对"（那是人的判断：`attach: "out"` 的节
///   到底该算元层还是接入层，机器判不了）；
/// - `_not_domain_sections` 里列名的键**不进**判据 4 的集合：它们是说明／总表／登记表，
///   但它们**必须自己也在表里列名**（否则它就是"没被归属的新分节"）。
fn check_section_map(v: &Value) -> Result<(), String> {
    let drift = |d: String| Violation::SectionMapDrift { detail: d }.to_string();
    let Some(map) = v.get("_section_map").and_then(Value::as_object) else {
        return Err(drift(
            "缺 `_section_map`——十二节的归属表不存在，本判据无从成立".to_string(),
        ));
    };
    // 归属的封闭表（判据 1）。
    let homes: BTreeSet<String> = map
        .get("_homes")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();
    if homes.is_empty() {
        return Err(drift(
            "`_section_map._homes` 为空——归属的**封闭词表**是空表，判据 1 无从成立".to_string(),
        ));
    }
    // 不是分节的 `_` 键（说明／总表／登记表）。`_note` 是**本表内部**的说明格，不算一个键。
    let not_sections: BTreeSet<String> = map
        .get("_not_domain_sections")
        .and_then(Value::as_object)
        .map(|o| {
            o.keys()
                .filter(|k| k.as_str() != "_note")
                .cloned()
                .collect()
        })
        .unwrap_or_default();
    if not_sections.is_empty() {
        return Err(drift(
            "`_section_map._not_domain_sections` 为空——说明／总表／登记表键必须逐一列名，\
             否则它们会被判 4 当成'未被归属的分节'"
                .to_string(),
        ));
    }
    let Some(sections) = map.get("sections").and_then(Value::as_object) else {
        return Err(drift("`_section_map.sections` 缺失或不是对象".to_string()));
    };
    let named: Vec<&String> = sections.keys().filter(|k| !k.starts_with('_')).collect();
    if named.is_empty() {
        return Err(drift("`_section_map.sections` 里一节都没声明".to_string()));
    }

    let mut declared: BTreeSet<String> = BTreeSet::new();
    for (name, def) in sections {
        if name.starts_with('_') {
            continue; // 表内的说明键（`_comment`／`_why`／…）
        }
        // 判据 1：归属必须取自封闭表。
        let home = def.get("home").and_then(Value::as_str).unwrap_or("");
        if home.is_empty() {
            return Err(drift(format!("分节 `{name}` 没写 `home`（归属）")));
        }
        if !homes.contains(home) {
            return Err(drift(format!(
                "分节 `{name}` 的 `home` = `{home}` 不在 `_homes` 里——归属必须取自那张封闭表：{}",
                homes.iter().cloned().collect::<Vec<_>>().join("、")
            )));
        }
        // 判据 2：`attach` 三值。
        let attach = def.get("attach").and_then(Value::as_str).unwrap_or("");
        if !matches!(attach, "full" | "half" | "out") {
            return Err(drift(format!(
                "分节 `{name}` 的 `attach` = `{attach}`——只认 `full`／`half`／`out`"
            )));
        }
        // 判据 3：必须说清载体（`keys` 或 `_where`）。
        let keys: Vec<String> = def
            .get("keys")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default();
        let where_ = def.get("_where").and_then(Value::as_str).unwrap_or("");
        if keys.is_empty() && where_.is_empty() {
            return Err(drift(format!(
                "分节 `{name}` 既没给 `keys`（承载它的 `_` 分节）、也没给 `_where`（今天落在哪）\
                 ——归属表不许留空"
            )));
        }
        for k in &keys {
            if !k.starts_with('_') {
                return Err(drift(format!(
                    "分节 `{name}` 的 `keys` 里写了 `{k}`——只认 `_` 开头的分节键"
                )));
            }
            // 表里声明的键必须**真的在文件里**（否则是空指针）。
            if v.get(k).and_then(Value::as_object).is_none() {
                return Err(drift(format!(
                    "分节 `{name}` 声明由 `{k}` 承载，而文件里**没有**这个 `_` 分节"
                )));
            }
            declared.insert(k.clone());
        }
    }

    // 判据 4：集合相等（双向）。
    let actual: BTreeSet<String> = v
        .as_object()
        .map(|o| {
            o.keys()
                .filter(|k| k.starts_with('_') && !not_sections.contains(*k))
                .cloned()
                .collect()
        })
        .unwrap_or_default();
    if actual != declared {
        let uncovered: Vec<String> = actual.difference(&declared).cloned().collect();
        let phantom: Vec<String> = declared.difference(&actual).cloned().collect();
        return Err(drift(format!(
            "归属表与文件里的 `_` 分节集合**不相等**：\
             未被归属表覆盖的分节＝{uncovered:?}；归属表声明了而文件里没有的＝{phantom:?}\n\
             \x20 实际分节（全部顶层 `_` 键 − `_not_domain_sections`）：{actual:?}\n\
             \x20 表里声明的分节：{declared:?}"
        )));
    }
    Ok(())
}

/// ★ **判据①a · 载体无关性**：本体里（**参与身份**的那一半）不许出现**载体专有串**。
///
/// ## 判什么
///
/// 扫 `ontology.json` 里**参与 `vocab_hash`** 的那一半（＝非 `_` 前缀键，**与
/// [`strip_comments`] 的剔法同源**——同一个函数保证"判据扫的面"与"身份算的面"**是同一面**），
/// 对每个**键名**与每个**字符串值**查载体专有串表。
///
/// ## 为什么这条该红
///
/// 本体是**世界的说法**；载体是**某个东西怎么起**。两者**同级不同物**
/// （「systemd 管资源，世界管说法」）。而本体的身份是**内容寻址**的
/// ⇒ 一旦载体专有物进了身份面，**换掉载体就得换法律**（换一个字 = 换掉整个世界的身份）。
/// 那不是"顺手写错一个字"，是把两条轴混成了一条。
///
/// ## 射程（如实声明）
///
/// - **只**扫参与身份的那一半；`_` 键里的**指路说明**（例如「接入映射今天在 `policy.json`
///   的 `listeners`」）**不判**——它们不进身份，而且本来就该能写清"落在哪"；
/// - 表是**字符串匹配**，不是语义判断：它抓的是"载体专有物被写进了法律"这一**形态**，
///   抓不到"用世界的词表达了载体的意思"这种更深的混用（那**无法判定**，见 `EV-009`）。
///
/// ## 反例（`tests/ontology_elements.rs::m15`）
///
/// 往非 `_` 键里写 `"unit": "world-core.service"` ⇒ `.service` 命中 ⇒ 拒启；
/// 去掉 ⇒ 绿。
fn check_carrier_independence(v: &Value) -> Result<(), String> {
    // 载体专有串表（**来源**：本仓 `deploy/**` 里真实出现的载体机制名与指令名）。
    // ⚠️ 加词＝改法律口径，走评审；这里刻意**只收"载体专有"的串**，
    //    不收通用词（例如不收 `unit`、不收 `socket` 这种可能出现在世界语汇里的词）。
    const TOKENS: &[&str] = &[
        "systemd",
        ".service",
        ".socket",
        "ListenStream",
        "WantedBy",
        "Requires=",
        "After=",
        "Before=",
        "PartOf=",
        "/run/",
    ];
    fn walk(v: &Value, path: &str, tokens: &[&str]) -> Result<(), Violation> {
        match v {
            Value::Object(m) => {
                for (k, val) in m {
                    // 与 `vocab_hash_of` 同源：`_` 开头的键**不进身份**，本判据也不判它。
                    if k.starts_with('_') {
                        continue;
                    }
                    let kp = format!("{path}.{k}");
                    for t in tokens {
                        if k.contains(t) {
                            return Err(Violation::CarrierSpecificInOntology {
                                path: kp.clone(),
                                token: (*t).to_string(),
                                found_in: "**键名**".to_string(),
                            });
                        }
                    }
                    walk(val, &kp, tokens)?;
                }
                Ok(())
            }
            Value::Array(a) => {
                for (i, x) in a.iter().enumerate() {
                    walk(x, &format!("{path}[{i}]"), tokens)?;
                }
                Ok(())
            }
            Value::String(s) => {
                for t in tokens {
                    if s.contains(t) {
                        return Err(Violation::CarrierSpecificInOntology {
                            path: path.to_string(),
                            token: (*t).to_string(),
                            found_in: format!("字符串值 `{}`", truncate_for_msg(s)),
                        });
                    }
                }
                Ok(())
            }
            _ => Ok(()),
        }
    }
    walk(v, "$", TOKENS).map_err(|e| e.to_string())
}

/// 报错里回显一段值（太长就截断，**不允许**把整份载荷贴进错误里）。
fn truncate_for_msg(s: &str) -> String {
    let mut out: String = s.chars().take(40).collect();
    if s.chars().count() > 40 {
        out.push('…');
    }
    out
}

/// **五要素的节名与它们各自的顶层键**（装载器与判据**同源**读这一张表）。
///
/// 为什么是一张表而不是五段复制粘贴：缺节判据要能**逐要素点名**
/// （"缺的是接口·能力，找的键是 `_interfaces`"），两侧共用一个事实。
const SECTIONS: &[(&str, &[&str])] = &[
    ("对象（Object）", &["_objects", "concepts"]),
    ("关系（Link）", &["_links"]),
    ("接口·能力（Interface）", &["_interfaces"]),
    ("动作（Action）", &["_actions"]),
    ("函数（Function）", &["_functions"]),
];

impl Ontology {
    /// 从纯文本 JSON 文件加载本体。
    ///
    /// 加载失败**必须让程序拒绝启动**——法律不对，带病跑比不跑更危险
    /// （`07/4-计划/03` §五 启动顺序第 ③ 步：本体版本对不上即拒绝启动）。
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Ontology.ReadFail: {path:?}: {e}"))?;
        let v: Value = serde_json::from_str(&text)
            .map_err(|e| format!("ext.world.Ontology.BadJson: {path:?}: {e}"))?;

        // 静态防线（2026-09-26 补，见 WC-RV-R2-001 S-06）：词表即契约，
        // 与门禁策略、账本一样必须放在被管者不可写之处。
        // ⚠️ 顺序：**先读成功、再查权限**——否则"文件不存在"会报成
        // "无法读取…的权限"，把简单故障说成权限问题（c04 实测抓到）。
        crate::gate::guard::assert_not_other_writable(path, "本体（法律·形状）")?;

        // ── **第一批判据：五要素节存在性**（缺任一要素节 ⇒ 拒启）──────────────
        //
        // 为什么放在最前（早于版本／信封／家族）：五要素是这部法律的**骨架**。
        // 少一节 ⇒ 那一整面没有声明面，而**没有任何东西会因此变红**——
        // 那正是本项目最贵的一类错（把"没写"读成"允许"）。
        // 判据面与装载面**同源**（都读 `SECTIONS` 这张表），故"补一节忘了加判据"不可能发生。
        check_sections(&v)?;
        // **紧跟一条**：十二节的**归属表**（`_section_map`）必须与文件里的 `_` 分节集合一致。
        // 为什么紧跟在"节存在性"之后：那一条管"五要素在不在"，这一条管"**每一节归属写死没有**"
        // ——两条都属"骨架级"，且都在读其余内容之前就该判（其余判据都建立在分节之上）。
        check_section_map(&v)?;
        // ★ **判据①a：载体无关性**——本体里（**参与身份**的那一半）不许出现载体专有串。
        // 紧跟在前两条"骨架级"判据之后：它判的同样是"这部法律像不像**世界的**法律"。
        check_carrier_independence(&v)?;

        let world = v
            .get("world")
            .and_then(Value::as_u64)
            .ok_or_else(|| "ext.world.Ontology.NoVersion: 缺 `world` 版本号".to_string())?;

        let envelope = v
            .get("envelope")
            .ok_or_else(|| "ext.world.Ontology.NoEnvelope: 缺 `envelope`".to_string())?;
        let required = str_list(envelope, "required")?;
        let optional = str_list(envelope, "optional")?;
        // 信封**字段的类型声明**（见 `env_types` 的说明）。缺 `fields` 段 ⇒ 空表 ⇒ 只判"在不在"、不判类型
        // （**不许凭空发明一套类型系统**：本体没声明的，本判据不管）。
        let mut env_types = BTreeMap::new();
        if let Some(fs_obj) = envelope.get("fields").and_then(Value::as_object) {
            for (k, val) in fs_obj {
                if k.starts_with('_') {
                    continue;
                }
                if let Some(decl) = val.as_str() {
                    env_types.insert(k.clone(), decl.to_string());
                }
            }
        }

        let fams = v
            .get("families")
            .and_then(Value::as_object)
            .ok_or_else(|| "ext.world.Ontology.NoFamilies: 缺 `families`".to_string())?;
        let mut families = BTreeMap::new();
        for (name, def) in fams {
            // `_comment` 之类的下划线键不是家族
            if name.starts_with('_') {
                continue;
            }
            families.insert(
                name.clone(),
                Family {
                    required: str_list(def, "required")?,
                    optional: str_list(def, "optional").unwrap_or_default(),
                },
            );
        }
        if families.is_empty() {
            return Err("ext.world.Ontology.NoFamilies: 家族列表为空".to_string());
        }

        // 两处对象声明**各自解析**（分工见 `objects` 字段的文档）：
        //   · `_objects` —— **读路径**认它（不参与身份）；
        //   · `concepts` —— **身份**认它（参与 `vocab_hash`），并在 `_objects` 缺席时**退回读**。
        // 两处**都**解析出来，是为了下面那条**镜像判据**（同名字段的类型声明必须逐字一致）。
        let modern = v.get("_objects").and_then(Value::as_object);
        let legacy = v.get("concepts").and_then(Value::as_object);
        let modern_objs = match modern {
            Some(cs) => parse_object_section(cs)?,
            None => BTreeMap::new(),
        };
        let legacy_objs = match legacy {
            Some(cs) => parse_object_section(cs)?,
            None => BTreeMap::new(),
        };
        // ★ **镜像判据**（本批补）：`_objects` 与 `concepts` 里**同名字段**的类型声明
        // 必须**逐字一致** ⇒ 不一致即拒启。理由与射程见 `Violation::ConceptsDrift` 与
        // [`check_frozen_mirror`] 的文档。
        check_frozen_mirror(&modern_objs, &legacy_objs)?;
        // 读路径**只认一处**：有 `_objects` 就用它，没有才退回 `concepts`。
        let objects: BTreeMap<String, ObjectType> = if modern.is_some() {
            modern_objs
        } else {
            legacy_objs
        };

        // `_links`：命名关系 ＋ 两端类型 ＋ 基数。**端点必须已声明**（否则拒启）。
        let mut links = BTreeMap::new();
        if let Some(ls) = v.get("_links").and_then(Value::as_object) {
            for (name, def) in ls {
                if name.starts_with('_') {
                    continue;
                }
                let from = def
                    .get("from")
                    .and_then(Value::as_str)
                    .ok_or_else(|| format!("ext.world.Ontology.BadField: 关系 `{name}` 缺 `from`"))?
                    .to_string();
                let to = def
                    .get("to")
                    .and_then(Value::as_str)
                    .ok_or_else(|| format!("ext.world.Ontology.BadField: 关系 `{name}` 缺 `to`"))?
                    .to_string();
                // ★ 裁（Lead 2026-10-05 · 选甲）：关系这一节**只许声明世界真执行的取值**。
                //   今天世界**不执行**基数约束、也**不执行**方向性 ⇒ 法律里只许出现"无约束"的
                //   那两个取值（`card` = `"many"`、`bidirectional` = `false`），或者**不写**（＝不声明）。
                //   声明别的（含**形状写错**）一律拒启 —— 理由：**"声明了没执行"比"没声明"更坏**
                //   （读者会以为这条关系真有基数／方向性约束）。
                //   ⇒ 要真做基数／方向性校验：改法律 ＋ 实现 ＋ 会红判据，走 change-surface 三张表。
                //   ⇒ 缺口**本体侧登记**（`_pending_tables`）待三张表门禁解除后补；本处先把它变成拒启。
                let card = match def.get("card") {
                    None => "many".to_string(),
                    Some(Value::String(s)) if s == "many" => s.clone(),
                    Some(Value::String(s)) => {
                        return Err(format!(
                            "ext.world.Ontology.BadField: 关系 `{name}` 声明 `card` = `{s}`，\
                             而世界今天**只执行** `many`（不执行任何基数约束）。\
                             ★**声明了没执行** 比「没声明」更坏（读者会以为这条关系有基数约束）⇒ 拒启。\
                             要真做基数校验 ⇒ 改法律＋实现，走 change-surface 三张表"
                        ))
                    }
                    Some(other) => {
                        return Err(format!(
                            "ext.world.Ontology.BadField: 关系 `{name}` 的 `card` 是 {}、不是字符串\
                             ——**不可判读**的声明不许当成「没那一项」（默认值不是挡箭牌）",
                            json_type_name(other)
                        ))
                    }
                };
                let bidirectional = match def.get("bidirectional") {
                    None => false,
                    Some(Value::Bool(false)) => false,
                    Some(Value::Bool(true)) => {
                        return Err(format!(
                            "ext.world.Ontology.BadField: 关系 `{name}` 声明 `bidirectional` = true，\
                             而世界今天**不执行**方向性。★**声明了没执行** 比「没声明」更坏 ⇒ 拒启。\
                             要真做方向性 ⇒ 改法律＋实现，走 change-surface 三张表"
                        ))
                    }
                    Some(other) => {
                        return Err(format!(
                            "ext.world.Ontology.BadField: 关系 `{name}` 的 `bidirectional` 是 {}、不是布尔\
                             ——**不可判读**的声明不许当成「没那一项」（默认值不是挡箭牌）",
                            json_type_name(other)
                        ))
                    }
                };
                for (side, endpoint) in [("from", &from), ("to", &to)] {
                    if !objects.contains_key(endpoint) {
                        return Err(Violation::UndeclaredRelationEndpoint {
                            link: name.clone(),
                            endpoint: endpoint.clone(),
                            side: side.to_string(),
                            known: objects.keys().cloned().collect::<Vec<_>>().join(", "),
                        }
                        .to_string());
                    }
                }
                links.insert(
                    name.clone(),
                    LinkDecl {
                        from,
                        to,
                        card,
                        bidirectional,
                    },
                );
            }
        }

        // `_interfaces`：能力（可读／可配／可调）。**能力名不许长得像具体对象**。
        let mut interfaces = BTreeMap::new();
        if let Some(is) = v.get("_interfaces").and_then(Value::as_object) {
            for (name, def) in is {
                if name.starts_with('_') {
                    continue;
                }
                if name.starts_with("world://") {
                    return Err(Violation::GrantNotOnCapability {
                        granted: name.clone(),
                        known: interfaces.keys().cloned().collect::<Vec<_>>().join(", "),
                    }
                    .to_string());
                }
                let kind = def
                    .get("kind")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        format!("ext.world.Ontology.BadField: 能力 `{name}` 缺 `kind`（read／config／invoke）")
                    })?
                    .to_string();
                let what = def
                    .get("what")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_string();
                interfaces.insert(name.clone(), CapabilityDecl { kind, what });
            }
        }

        // `_actions`：动作（怎么改）。**每条必须引用一个已声明的能力**。
        let mut actions = BTreeMap::new();
        if let Some(acts) = v.get("_actions").and_then(Value::as_object) {
            for (name, def) in acts {
                if name.starts_with('_') {
                    continue;
                }
                let capability = def
                    .get("capability")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        format!("ext.world.Ontology.BadField: 动作 `{name}` 缺 `capability`（它引用的能力名）")
                    })?
                    .to_string();
                let reversible =
                    def.get("reversible")
                        .and_then(Value::as_bool)
                        .ok_or_else(|| {
                            format!(
                                "ext.world.Ontology.BadField: 动作 `{name}` 缺 `reversible` 布尔值"
                            )
                        })?;
                // ★ **这条动作调用的函数入口**（可选）：它是"五要素之五"的**引用边**——
                // 没有它，"某个入口有没有人用"就问不出来（见 `ActionDecl::function` 的文档）。
                let function = match def.get("function").and_then(Value::as_str) {
                    Some(f) if !f.is_empty() => Some(f.to_string()),
                    _ => None,
                };
                actions.insert(
                    name.clone(),
                    ActionDecl {
                        capability,
                        reversible,
                        function,
                    },
                );
            }
        }

        // `_functions`：**只有入口名**。命令字面量 ⇒ 红（命令硬编码在代码里）。
        let mut functions = BTreeMap::new();
        let host_commands: Vec<String> = v
            .get("_functions")
            .and_then(|f| f.get("_registered_host_commands"))
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default();
        if let Some(fs_obj) = v
            .get("_functions")
            .and_then(|f| f.get("entries"))
            .and_then(Value::as_object)
        {
            for (entry, def) in fs_obj {
                if entry.starts_with('_') {
                    continue;
                }
                if let Some(why) = function_entry_literal(entry, &host_commands) {
                    return Err(Violation::FunctionLiteralNotAllowed {
                        entry: entry.clone(),
                        why,
                    }
                    .to_string());
                }
                let what = def
                    .get("what")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_string();
                functions.insert(
                    entry.clone(),
                    FunctionDecl {
                        entry: entry.clone(),
                        what,
                    },
                );
            }
        }

        // `_permissions`：默认**显式**拒绝；授权只许授在**能力**上。
        let perms = v.get("_permissions").and_then(Value::as_object);
        let permission_default = perms
            .and_then(|p| p.get("default"))
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string();
        if permission_default != "deny" {
            return Err(Violation::PermissionDefaultOpen {
                got: if permission_default.is_empty() {
                    "（缺 `default`）".to_string()
                } else {
                    permission_default.clone()
                },
            }
            .to_string());
        }
        let mut permissions = BTreeMap::new();
        if let Some(grants) = perms
            .and_then(|p| p.get("grants"))
            .and_then(Value::as_object)
        {
            for (granted, def) in grants {
                if granted.starts_with('_') {
                    continue;
                }
                // ★ 授权只许授在**能力**上：授在具体类型／具体对象上 ⇒ 红。
                if !interfaces.contains_key(granted) {
                    return Err(Violation::GrantNotOnCapability {
                        granted: granted.clone(),
                        known: interfaces.keys().cloned().collect::<Vec<_>>().join(", "),
                    }
                    .to_string());
                }
                let list = |k: &str| -> Vec<String> {
                    def.get(k)
                        .and_then(Value::as_array)
                        .map(|a| {
                            a.iter()
                                .filter_map(Value::as_str)
                                .map(str::to_string)
                                .collect()
                        })
                        .unwrap_or_default()
                };
                permissions.insert(
                    granted.clone(),
                    PermissionDecl {
                        who: list("who"),
                        scope: list("scope"),
                    },
                );
            }
        }

        // **判据②**：扩展项**不得与核心字段重名**（`REQ-F-030`；书 §2.7）。
        // 放在装载期（而不是写入期）：重名是"法律自相矛盾"，法律不对就该拒绝启动，
        // 而不是等到某一条写入路过时才报——那时读到的是"某条事件非法"，说错了病因。
        let core_fields = core_field_names(&required, &optional);
        check_extension_names(&objects, &core_fields)?;

        // **判据：动作引用的能力必须存在**（五要素之四挂在三上）。
        check_action_capabilities(&actions, &interfaces)?;
        // ★ **判据：结构性死声明与悬空引用**（本批新立）——
        //   死入口（`_functions.entries` 没人引用）／悬空入口引用（动作指向不存在的入口）／
        //   死能力（既无动作、又无许可）。
        //   放在**最后**：它是"关系面"的判据（谁引用谁），而前面各条管的是"每一节自己形不形"。
        check_structural_liveness(&actions, &interfaces, &functions, &permissions)?;

        Ok(Ontology {
            world,
            required,
            optional,
            env_types,
            families,
            objects,
            links,
            interfaces,
            actions,
            functions,
            permissions,
            permission_default,
            vocab_hash: vocab_hash_of(&v),
        })
    }

    pub fn world(&self) -> u64 {
        self.world
    }

    /// **词表的身份**：内容寻址（content-addressed）。
    ///
    /// 为什么需要它：两个投影必须**同源**——同一个读模型 + **同一份词表**
    /// （`WC-SRS-001` REQ-F-020）。若两边各读各的词表副本，"同源"就只是口号。
    /// 故词表本身必须可被内容寻址：内容相同 ⇒ hash 相同；内容一变 ⇒ hash 变，
    /// 于是"有人换了词表"这件事**能被检出**，而不是靠人去比对两份文件。
    ///
    /// 口径（两处刻意选择）：
    /// - 对**规范化 JSON**求值（解析后紧凑序列化、键有序），**不是**文件原始字节——
    ///   否则改一个空格就报"换词表"，那是假警报，会训练人忽略这个信号；
    /// - **剔除 `_` 开头的键**（`_comment` / `_source` 等说明文字）——
    ///   说明文字不是词表语义。改注释不该改变世界的身份。
    ///
    /// ⚠️ 用 FNV-1a 是**非加密**指纹（本项目零外部依赖，不引哈希库）。
    /// 它回答的唯一问题是"是不是同一份词表"，**不得**用于安全判断。
    pub fn vocab_hash(&self) -> &str {
        &self.vocab_hash
    }

    pub fn optional(&self) -> &[String] {
        &self.optional
    }

    /// **信封已声明的必填格**（`envelope.required`，出厂本体实测 8 项）。
    ///
    /// 用途：读模型侧的**缺格判据**（`REQ-F-032`）要按"本体已声明的格"来判，而读模型
    /// **不许** `use crate::ontology_definition::…`——`WC-MODREG-001` §2 给 `M03` 的依赖列逐字是
    /// 「**无**（生产代码零出边）」，机核层 `tools/module_graph.py` 判据② 逐边核对
    /// 「声明集 ≡ 真实 import 集」⇒ 读模型加一条生产边就红。故本方法只交**纯数据**
    /// （`Vec<String>`）出去，由**装配处**递给读模型：
    /// `world_core::ontology_instance::readmodel::DeclaredCells::new(ont.envelope_required(), ont.family_required())`；
    /// 依赖方向留在装配处（`M04` 同时依赖 `M01` 与 `M03`），法律与读法仍读**同一份**本体。
    pub fn envelope_required(&self) -> Vec<String> {
        self.required.clone()
    }

    /// 信封里**可选**的格（`envelope.optional`）。与 [`Ontology::envelope_required`] 同源，
    /// 供"逐格核对可读面"这类判据**从本体派生**清单用（别处不许手抄格名）。
    pub fn envelope_optional(&self) -> Vec<String> {
        self.optional.clone()
    }

    /// **各家族已声明的必填格**（`families.<家族>.required`；出厂本体实测 `change` 4／`act` 3／`notice` 2）。
    ///
    /// 与 [`Ontology::envelope_required`] 同一用途（读模型侧的缺格判据）；同样只交**纯数据**
    /// （理由逐字同上：不让读模型多出一条生产依赖边）。
    /// ⚠️ 这里**不含**各家族的 `optional`：可选格"没写"是法律允许的形态，不是缺格。
    pub fn family_required(&self) -> BTreeMap<String, Vec<String>> {
        self.families
            .iter()
            .map(|(k, f)| (k.clone(), f.required.clone()))
            .collect()
    }

    pub fn known_kinds(&self) -> Vec<&str> {
        self.families.keys().map(String::as_str).collect()
    }

    /// 已声明的实体名（有序）。
    pub fn known_entities(&self) -> Vec<&str> {
        self.objects.keys().map(String::as_str).collect()
    }

    /// 某实体已声明的字段集（`None` = 该实体**没声明过**）。
    pub fn declared_fields(&self, entity: &str) -> Option<&BTreeMap<String, String>> {
        self.objects.get(entity).map(|o| &o.fields)
    }

    /// **对象类型**（五要素之一）的完整声明。
    pub fn object_type(&self, entity: &str) -> Option<&ObjectType> {
        self.objects.get(entity)
    }

    /// 全部对象类型（有序）。
    pub fn object_types(&self) -> impl Iterator<Item = (&str, &ObjectType)> {
        self.objects.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// **命名关系**（五要素之二）。
    pub fn links(&self) -> impl Iterator<Item = (&str, &LinkDecl)> {
        self.links.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// **能力**（五要素之三）。
    pub fn interfaces(&self) -> impl Iterator<Item = (&str, &CapabilityDecl)> {
        self.interfaces.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// **动作**（五要素之四）。
    pub fn actions(&self) -> impl Iterator<Item = (&str, &ActionDecl)> {
        self.actions.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// **函数入口表**（五要素之五）：**只有入口名**。
    pub fn functions(&self) -> impl Iterator<Item = (&str, &FunctionDecl)> {
        self.functions.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// **许可条文**：授权授在哪些能力上（以及谁有资格授）。
    pub fn permissions(&self) -> impl Iterator<Item = (&str, &PermissionDecl)> {
        self.permissions.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// `_permissions.default` 的原文（判据读它：必须逐字 `deny`）。
    pub fn permission_default(&self) -> &str {
        &self.permission_default
    }

    /// **按类型的实例上限**（`_objects.<类型>.max_instances`；只交有声明的那几条）。
    ///
    /// 为什么要把它交出去（而不是在本体里判）：判据面在**折叠后**的实例计数上，
    /// 而折叠在读模型（`M03`，生产代码零出边）。⇒ 上限以**纯数据**递进去，
    /// 与「已声明必填格」同一体例（依赖方向留在装配处 `M04`）。
    /// 空表 **不是** "什么都不管"：读模型侧对空表有明确处置（见 `DeclaredCells`）。
    pub fn instance_limits(&self) -> BTreeMap<String, u64> {
        self.objects
            .iter()
            .filter_map(|(k, v)| v.max_instances.map(|n| (k.clone(), n)))
            .collect()
    }

    /// **内嵌标记**（`_objects.<类型>.part_of`；只交有声明的那几条）。
    pub fn nested_types(&self) -> BTreeMap<String, String> {
        self.objects
            .iter()
            .filter_map(|(k, v)| v.part_of.clone().map(|p| (k.clone(), p)))
            .collect()
    }

    /// **读一条事件的旗标**：认得的照常处理，**不认得的一律忽略**（`REQ-F-029`）。
    ///
    /// 依据（逐字）：`world-core/src/ontology_definition/ontology.json:20`
    /// `"flags": "array  # 能力旗标；未知旗标必须忽略"`。
    ///
    /// 为什么把它挂在**本体**上：这条纪律是**法律**的一部分（写在出厂本体的信封字段表里），
    /// 所以"读的人按哪一半继续"这件事的入口在本体侧，与 `validate` 同源。
    ///
    /// ⚠️ 本方法**没有 `Result`**：出现不认得的旗标**不是**一种校验失败——
    /// 它是"读的人按他认得的那部分继续"。哪些算"认得"由调用方给：
    /// 出厂读法用 [`crate::common::event::is_factory_flag`]，认得摩擦旗标的读法另给它自己的判据。
    pub fn read_flags<'a, F>(&self, ev: &'a Value, knows: F) -> crate::common::event::Flags<'a>
    where
        F: Fn(&str) -> bool,
    {
        crate::common::event::read_flags(ev, knows)
    }

    /// 从 `subject` 取出**实体类型**：`world://<实体>/<实例…>` ⇒ `Some("<实体>")`。
    ///
    /// 裸主体（`world://<名字>`，没有实例段）⇒ `None`：它**不是**某个实体的实例引用。
    ///
    /// ## 口径（**本批不动**，两条断言钉着它）
    ///
    /// | 输入 | 输出 | 谁在核 |
    /// |---|---|---|
    /// | `world://s` | `None` | `tests/atom_declared_only.rs`（裸主体那条登记项） |
    /// | `world://notice/n-1` | `Some("notice")` | 同上（`Some` 那半） |
    /// | `world://a/b/c` | `Some("a")` | 本表：**首段永远是类型** |
    ///
    /// ⚠️ 由此推出一条**取舍**（写清楚，不许含糊）：**内嵌不能靠三段式 `world://a/b/c` 表达**——
    /// 三段式的首段仍然被读成"类型"：`a` 若不是已声明的类型，它只落"未声明实体"；
    /// 若 `a` **是**已声明的类型，那 `b/c` 只是**同一个类型 `a`** 的两个实例名段，
    /// 表达不出"c 是嵌在 b 里的另一类东西"。
    /// ⇒ 内嵌改用**声明式内嵌标记**：`_objects.<类型>` 的 `nested: true` ＋ `part_of: "<父类型>"`，
    /// 实例路径写成 `world://<父类型>/<父实例>/<本类型>/<本实例>`（见
    /// [`Ontology::nested_parent_of`] 与 `Violation::UndeclaredEmbeddedMarker`）。
    /// **首段这一次口径因此一字未改**，上面两条断言照旧成立。
    ///
    /// ⚠️ 另一条**已登记的缺口**（本批**有意不闭合**，见 [`Ontology::check_concepts`] 的文档）：
    /// 裸主体（`world://<名字>`）不受声明面约束。
    pub fn entity_of(subject: &str) -> Option<&str> {
        let rest = subject.strip_prefix("world://")?;
        let (entity, id) = rest.split_once('/')?;
        if entity.is_empty() || id.is_empty() {
            None
        } else {
            Some(entity)
        }
    }

    /// **内嵌实例的父类型**：`world://<父>/<父实例>/<本类型>/<本实例>` ⇒ `Some("<父>")`。
    ///
    /// 只认**四段**这一种内嵌形态：第 3 段必须**逐字**是 `entity`；对不上 ⇒ `None`
    /// （由 [`Ontology::check_concepts`] 另行报"父不对"）。两段／三段形态 ⇒ `None`（不是内嵌形态）。
    pub fn nested_parent_of<'a>(entity: &str, subject: &'a str) -> Option<&'a str> {
        let rest = subject.strip_prefix("world://")?;
        let segs: Vec<&str> = rest.split('/').collect();
        if segs.len() != 4 || segs.iter().any(|s| s.is_empty()) || segs[2] != entity {
            return None;
        }
        Some(segs[0])
    }

    /// **这一条 subject 实际写的是哪个类型**——比 [`Ontology::entity_of`] 多认一种形态。
    ///
    /// | subject | `entity_of`（**静态口径，本批一字未改**） | 本方法（按本体的声明解析） |
    /// |---|---|---|
    /// | `world://notice/n-1` | `Some("notice")` | `Some("notice")` |
    /// | `world://s`（裸主体） | `None` | `None` |
    /// | `world://a/b/c` | `Some("a")` | **`Some("a")`**（第 3 段 `c` 不是已声明的类型 ⇒ 首段就是类型） |
    /// | `world://job/j-1/notice/n-1` | `Some("job")` | **`Some("notice")`**（第 3 段是已声明的**内嵌**类型 ⇒ 它才是这条写入的类型） |
    ///
    /// ## 为什么需要它（实测逼出来的）
    ///
    /// 内嵌类型的实例路径是**四段**（`world://<父>/<父实例>/<本类型>/<本实例>`）。
    /// 只按 `entity_of` 的"取首段"读，就会把这条写入读成**父类型**的字段改动 ⇒
    /// 它必然撞 `UndeclaredField`（`job` 下没有 `muted`）——**病因说错了**：
    /// 真正要判的是"内嵌实例形态对不对"，不是"父类型有没有这个字段"。
    /// ⇒ 本方法**只解析、不判**：认得出内嵌形态就返回内嵌类型；认不出就退回首段。
    fn instance_type<'s>(&self, subject: &'s str) -> Option<&'s str> {
        let rest = subject.strip_prefix("world://")?;
        let segs: Vec<&str> = rest.split('/').collect();
        if segs.len() == 4 && segs.iter().all(|s| !s.is_empty()) {
            if let Some(o) = self.objects.get(segs[2]) {
                if o.part_of.as_deref() == Some(segs[0]) {
                    return Some(segs[2]);
                }
            }
        }
        Self::entity_of(subject)
    }

    /// **声明以外的东西不许落账**（书第五章 §5.3）：按 `_objects`（退回 `concepts`）校验实体、字段与**值类型**。
    ///
    /// ## 查什么
    ///
    /// | 情形 | 结论 |
    /// |---|---|
    /// | `world://<未声明的实体>/<实例>` | **拒**，错误点名那个实体（`UndeclaredEntity`） |
    /// | `world://<已声明的实体>/<实例>` + 未声明的 `path` | **拒**，错误点名那个字段（`UndeclaredField`） |
    /// | 同上 ＋ `after` 的**值类型**与声明不符（含 `enum(...)` **闭集**，**`kind` 除外**） | **拒**，点名那一格与两侧类型（`BadFieldValueType`） |
    /// | 该类型声明为**内嵌**（`part_of`）而 subject 不是内嵌形态／父类型不对 | **拒**（`UndeclaredEmbeddedMarker`） |
    /// | `world://<已声明的实体>/<实例>` + 已声明的 `path` + 类型相符 | 放行 |
    ///
    /// ## 值类型这一格的口径（**本批升级**）
    ///
    /// 原先字段的**值**只是自由文本说明（"这一格是 bool"写在文件里，落笔时没人读它）⇒
    /// "类型不符"无从判起。本批把它升级成**机器可读**：
    /// - **认得的类型词**：`bool`／`string`／`integer`／`number`／`array`／`object`／
    ///   `ref(<类型>)`／`enum(a,b,…)` ⇒ **参与校验**，不符即拒；
    /// - **`enum(...)` 是闭集**：值不在枚举内 ⇒ 拒（`BadFieldValueType`）。
    ///   ⚠️ 出厂本体的 `concepts.job.fields.status` 逐字是 `enum(todo,doing,done)`，
    ///   故它今天是一个**真实的闭集**（三个值）——这是本批**加强**的判据；
    /// - ★ **`kind` 除外**（**字段限定，不是通例**）：`envelope.kind` 那一格的
    ///   `enum(change, act, notice)` **不进本判据**——它是**家族名**，而家族是**可扩展**的，
    ///   它的执行者是**家族查找**（`ext.world.Ontology.UnknownKind`，并**点名那个值**），
    ///   不是枚举闭集。依据：`openspec/specs/envelope-validation/spec.md` 逐字
    ///   「**枚举值**另有其主（**家族查找报 `ext.world.Ontology.UnknownKind` 并点名**）」
    ///   与 `world-core/docs/理论/冲突总账.md` 逐字「`enum(...)` 明确豁免」。
    ///   理由与出处写在 [`Ontology::validate_types`] 的文档里（本处只指路）。
    /// - **不认得的写法一律放行**：本体没声明的类型口径，判据**不替它发明**
    ///   （要收窄就往本体里写一条认得的声明，并配一条反例）。
    ///
    /// ## 只查 `change`
    ///
    /// 三家族里只有 `change` 改状态（读模型里就是 `objects[subject][path] = after`）——
    /// 所以"什么是世界里的东西"只在它这里判。`act` / `notice` 的信纸由家族必填项管；
    /// 且 `notice.subject` 的语义是"这条通告关于谁"，不是"改了哪一格"，拿字段表去查它
    /// 是查错了对象。
    ///
    /// ## 一处**已登记的缺口**（本批**有意不闭合**，不假装已闭合）
    ///
    /// **裸主体**（`world://<名字>`，没有实例段）**不受**本段约束——`world://s` 这类槽位
    /// 今天照样能落账。留下它的原因不是口径，而是**代价**：既有出厂用例
    /// （`tests/cli.rs:100/230`、`tests/contract.rs:257` 等多处、`tests/acceptance.rs:296`）
    /// 都以这种形态写槽位，一律拒绝会把它们打红，而那些用例不许改。
    /// ⇒ 书 §5.3 要的"世界的边界由声明定"在**实体引用**这一半成立，
    /// 在**裸主体**那一半**仍未成立**（已在 `tests/atom_declared_only.rs` 里立成登记项）。
    ///
    /// ⚠️ 另一半（`world://check/probe`、`world://sys/a` 这类**带实例段**的未声明实体）
    /// 已经被拒。代价是出厂门禁脚本 `world-core/check.sh` 第 89 行与 `tools/` 下的探针
    /// 会非零退出：它们写的是"未声明的实体"，而本段正是要拦这个。
    /// 那些文件不属本次改动范围，已在交付说明里逐条列出（含建议的最小改法）。
    pub fn check_concepts(&self, kind: &str, body: &Value) -> Result<(), Violation> {
        if kind != "change" {
            return Ok(());
        }
        // 必填项缺失由家族必填检查负责报（这里不抢它的错误码）。
        let Some(subject) = body.get("subject").and_then(Value::as_str) else {
            return Ok(());
        };
        // **这一条写入实际是哪个类型**（内嵌形态认出来的内嵌类型；否则首段）。
        let Some(entity) = self.instance_type(subject) else {
            return Ok(()); // 裸主体：见上文「已登记的缺口」
        };
        let known = || self.known_entities().join(", ");
        let Some(obj) = self.objects.get(entity) else {
            return Err(Violation::UndeclaredEntity {
                entity: entity.to_string(),
                subject: subject.to_string(),
                known: known(),
            });
        };
        // **内嵌标记的判据**：声明为内嵌的类型，其 subject 必须是内嵌形态且父类型正确。
        if let Some(want_parent) = &obj.part_of {
            let got = Self::nested_parent_of(entity, subject).unwrap_or("");
            if got != want_parent.as_str() {
                return Err(Violation::UndeclaredEmbeddedMarker {
                    entity: entity.to_string(),
                    subject: subject.to_string(),
                    want_parent: want_parent.clone(),
                    got_parent: got.to_string(),
                });
            }
        }
        let Some(path) = body.get("path").and_then(Value::as_str) else {
            return Ok(());
        };
        let Some(decl) = obj.fields.get(path) else {
            let declared = obj.fields.keys().cloned().collect::<Vec<_>>().join(", ");
            return Err(Violation::UndeclaredField {
                entity: entity.to_string(),
                field: path.to_string(),
                subject: subject.to_string(),
                known: declared,
            });
        };
        // **值类型**：本体声明了机器可读的类型 ⇒ 这一格的值必须符合（含 `enum` 闭集；
        // `kind` 是**信封**那一格、不在这里——它走家族查找，见 `validate_types` 的文档）。
        if let Some(after) = body.get("after") {
            let want = declared_type_word(decl);
            if type_is_declared(want) && !type_ok(decl, after) {
                return Err(Violation::BadFieldValueType {
                    entity: entity.to_string(),
                    field: path.to_string(),
                    subject: subject.to_string(),
                    want: want.to_string(),
                    got: json_type_name(after).to_string(),
                });
            }
        }
        Ok(())
    }

    /// 校验一条事件是否合法：信封必填 → 版本 → 家族存在 → 信纸必填 → **声明以内**。
    pub fn validate(&self, ev: &Value) -> Result<(), Violation> {
        let obj = ev.as_object().ok_or(Violation::NotAnObject)?;

        for f in &self.required {
            if !obj.contains_key(f) {
                return Err(Violation::MissingField {
                    at: "envelope".to_string(),
                    field: f.clone(),
                });
            }
        }

        let got = obj.get("world").and_then(Value::as_u64).unwrap_or(0);
        if got != self.world {
            return Err(Violation::BadVersion {
                expected: self.world,
                got,
            });
        }

        let kind = obj.get("kind").and_then(Value::as_str).unwrap_or("");
        let fam = self
            .families
            .get(kind)
            .ok_or_else(|| Violation::UnknownKind {
                kind: kind.to_string(),
            })?;

        let body =
            obj.get("body")
                .and_then(Value::as_object)
                .ok_or_else(|| Violation::MissingField {
                    at: "envelope".to_string(),
                    field: "body".to_string(),
                })?;
        for f in &fam.required {
            if !body.contains_key(f) {
                return Err(Violation::MissingField {
                    at: format!("body[{kind}]"),
                    field: f.clone(),
                });
            }
        }

        // **在不在／版本／家族／信纸必填**都问过了，最后问**类型对不对**（`TC-047 ⑧` 的修法）。
        // 为什么排在既有各道**之后**（实现时先排在前面，被既有断言当场纠正）：
        // `c02` 逐字把 `body` 设成字符串并期望 `MissingField`、`world` 写成字符串则由版本那道报 `BadVersion` ——
        // 那两条都是**既有契约**。本判据**只接手没人管的那一处**（如 `actor`＝整数），**不抢既有码**。
        self.validate_types(ev)?;

        // **最后一道**：声明以外的东西不许落账（书 §5.3）。
        // 放在形状检查之后：形状不对时先报形状（那是更基本的问题），
        // 形状对了再问"这个名字世界里有没有"——两道错的报错顺序不该靠偶然。
        self.check_concepts(kind, obj.get("body").unwrap_or(&Value::Null))?;

        Ok(())
    }

    /// **只判类型**：本体声明过类型的信封字段，值必须符合声明。
    ///
    /// 与 [`Ontology::validate`] 分开的**理由（实测逼出来的）**：读路径此前跑的是整套 `validate`，
    /// 于是"**缺 `actor`**"这类事件被报成 `ext.world.Ontology.MissingField`（**写侧那条**），
    /// 而读侧的契约是 [`readmodel`] 的 `ext.world.ReadModel.MissingCell`（**它自己那条**，有断言在核）。
    /// ⇒ **补缺口（类型）不动别人的契约**：读路径只调本方法；写路径照旧跑整套 `validate`。
    ///
    /// 范围：只判 `self.env_types` 里**声明过**且**值在场**的字段。
    ///
    /// ## `enum(...)` 这一格（**本批改口径**；★ 别处凡说"`enum(...)` 是闭集"的，**都以本段为限定**）
    ///
    /// 原先这里有一句"`enum` 声明一律 `continue` 跳过"，理由是"值不在枚举里由家族查找报
    /// `UnknownKind` 并点名那个值"。**那个理由只对 `kind` 这一格成立**（`kind` 的值是**家族名**，
    /// 家族查找就是它的执行者，而且家族是**可扩展**的——本体新增一个家族时，
    /// 信封上那句 `enum(change, act, notice)` **本来就该跟着变宽**；拿它当闭集会把
    /// 「只加扩展 ⇒ 照常可读」这条既有判据打红，**红得没道理**）。
    /// ⇒ `kind` **留原样**（交给家族查找），**别的** enum 字段（如 `status`）进 [`type_ok`]
    /// 的**闭集**判据。
    ///
    /// **依据（逐字，上位规格）**：`openspec/specs/envelope-validation/spec.md` ——
    /// 「**枚举值**另有其主（**家族查找报 `ext.world.Ontology.UnknownKind` 并点名**）」；
    /// `world-core/docs/理论/冲突总账.md` ——「`enum(...)` 明确豁免」。
    /// ⇒ 口径是「**`enum` 闭集，`kind` 除外**」，**不是**「`enum` 一律闭集」。
    /// ⚠️ **不许**把 `kind` 改成闭集：那会让 `tests/family_readmodel.rs` 的 `h02`
    /// （只加扩展的家族必须照常可读）变红，并换掉 `e03`／`h02` 的错误码
    /// （`UnknownKind` → `BadFieldType`）——那是行为变更，不是措辞。
    pub fn validate_types(&self, ev: &Value) -> Result<(), Violation> {
        let obj = match ev.as_object() {
            Some(o) => o,
            None => return Ok(()), // 不是对象：交给 validate 的 NotAnObject，本方法不越界
        };
        for (f, decl) in &self.env_types {
            // `kind` 是**家族名**那一格：它的判据是家族查找（可扩展），不是枚举闭集。
            if f == "kind" {
                continue;
            }
            if let Some(v) = obj.get(f) {
                if !type_ok(decl, v) {
                    return Err(Violation::BadFieldType {
                        at: "envelope".to_string(),
                        field: f.clone(),
                        want: declared_type_word(decl).to_string(),
                        got: json_type_name(v).to_string(),
                    });
                }
            }
        }
        Ok(())
    }
}

/// **五要素节存在性**（第一批判据）：`SECTIONS` 里每一节都必须在场、且是对象。
///
/// 为什么放在 `load` 的最前（早于版本／信封／家族）：五要素是这部法律的**骨架**——
/// 少一节 ⇒ 那一整面没有声明面，而**没有任何东西会因此变红**。
/// 与"空策略不许上电"（`gate::Policy::load`）、"空表不许读成宽松"
/// （`readmodel::State::apply_declared`）同一纪律。
///
/// 口径三条（都可判真假）：
/// 1. 判据面与装载面**同源**：两边都读 [`SECTIONS`] ⇒ "加一节忘了加判据"不可能发生；
/// 2. **对象这一节的键有两个**（`_objects` 优先、`concepts` 退回）——**任一在场即算在场**，
///    `concepts` 保住的是出厂身份（见 `Ontology::objects` 的文档）；
/// 3. 只在装"场"不在"空"：本节判**存在性**，不判内容多少
///    （内容判据各有其主：字段类型、关系端点、能力引用、实例上限…）。
fn check_sections(v: &Value) -> Result<(), String> {
    for (element, keys) in SECTIONS {
        let present = keys
            .iter()
            .any(|k| v.get(*k).and_then(Value::as_object).is_some());
        if !present {
            return Err(Violation::MissingSection {
                element: (*element).to_string(),
                keys: keys
                    .iter()
                    .map(|k| format!("`{k}`"))
                    .collect::<Vec<_>>()
                    .join(" ／ "),
            }
            .to_string());
        }
    }
    Ok(())
}

/// **动作引用的能力必须存在**（五要素之四挂在三上）。
///
/// 为什么是加载期（而不是某次 `act` 路过时）：`_actions.<动作>.capability` 指不到
/// `_interfaces` 里的任何一个名字 ⇒ 这条动作**从写下那一刻起就没有法律依据**
/// （它要改的东西"能被怎样对待"没声明过）。那是"法律自相矛盾"，与坏 JSON 同档：
/// 拒启，而不是等某条请求路过时才报（那时读到的是"某条事件非法"，说错了病因）。
fn check_action_capabilities(
    actions: &BTreeMap<String, ActionDecl>,
    interfaces: &BTreeMap<String, CapabilityDecl>,
) -> Result<(), String> {
    let known = || interfaces.keys().cloned().collect::<Vec<_>>().join(", ");
    for (name, a) in actions {
        if !interfaces.contains_key(&a.capability) {
            return Err(Violation::ActionCapabilityUnknown {
                action: name.clone(),
                capability: a.capability.clone(),
                known: known(),
            }
            .to_string());
        }
    }
    Ok(())
}

/// ★ **结构性"死声明"与"悬空引用"**（本批新立；落在装载期 ⇒ 不合法即**拒启**）。
///
/// ## 判三条（都可判真假）
///
/// | # | 判据 | 码 | 反例（必红） |
/// |---|---|---|---|
/// | 1 | `_functions.entries` 里的入口**必须被至少一条动作引用**（`_actions.<动作>.function`） | `DeadFunctionEntry` | 声明一个入口，没有任何动作引用它 |
/// | 2 | 动作声明的 `function` **必须真的在** `_functions.entries` 里 | `DanglingFunctionRef` | 动作写 `"function": "no.such.entry"` |
/// | 3 | `_interfaces` 里的能力**必须至少被动作或许可之一引用** | `DeadCapability` | 声明一个能力，既无动作、又不在 `_permissions.grants` |
///
/// ## ★ 为什么这三条该红，而「声明了但账本里零使用」**不该红**（口径分界，写死在这里）
///
/// **这一条分界是本判据的全部要害**：
///
/// - **结构性不可达**（本函数判的）：一项声明**没有任何引用边**⇒ 它在这部法律里
///   **永远走不到**。「函数要落地只能被动作引用」（书 §3.5）、「能力要能被用，得有人能做它
///   或有人被授予它」——这些是**结构事实**，与"有没有人用过"无关 ⇒ **拒启**。
/// - **实例还没用上**（`world-core usage` 那份**只报告**的清单）：类型/字段声明了，
///   而**账本里还没有实例写过它**。这不叫死——**法律的本分就是「先声明、后使用」**：
///   一条能力、一个类型可以先被法律允许，再等第一次真实使用。把它判红
///   **等于禁止"先声明"**，会毁掉「往上是领域概念各自生长」这条既有口径
///   ⇒ **只报告、绝不红**（见 `cmd_usage`）。
///
/// ⇒ 一句记法：**"没人能走到它"是缺陷；"还没人走到它"是常态。**
///
/// ## 与既有各条**不重叠**（避免重复造判据）
///
/// - `check_action_capabilities`：动作 → 能力**必须存在**（悬空动作）。本函数**不判**它。
/// - `check_section_map`：分节集合一致。本函数**不判**它。
/// - 策略侧 `ext.world.Gate.CapabilityWithoutAction`：`config`／`invoke` 能力必须有动作
///   （**不看许可**、`read` 豁免）。本函数判的是**本体侧**的"动作 **或** 许可有其一"
///   ⇒ 两处**各判一半**，读的是**两份不同的法律文件**（`policy.json` vs `ontology.json`）。
fn check_structural_liveness(
    actions: &BTreeMap<String, ActionDecl>,
    interfaces: &BTreeMap<String, CapabilityDecl>,
    functions: &BTreeMap<String, FunctionDecl>,
    permissions: &BTreeMap<String, PermissionDecl>,
) -> Result<(), String> {
    let action_names = || actions.keys().cloned().collect::<Vec<_>>().join(", ");
    let entry_names = || functions.keys().cloned().collect::<Vec<_>>().join(", ");

    // 判据 2：动作引用入口 ⇒ 入口必须存在（悬空引用）。
    for (name, a) in actions {
        if let Some(f) = &a.function {
            if !functions.contains_key(f) {
                return Err(Violation::DanglingFunctionRef {
                    action: name.clone(),
                    entry: f.clone(),
                    known: entry_names(),
                }
                .to_string());
            }
        }
    }
    // 判据 1：入口 ⇒ 至少一条动作引用它（死入口）。
    for entry in functions.keys() {
        let referenced = actions
            .values()
            .any(|a| a.function.as_deref() == Some(entry.as_str()));
        if !referenced {
            return Err(Violation::DeadFunctionEntry {
                entry: entry.clone(),
                known: action_names(),
            }
            .to_string());
        }
    }
    // 判据 3：能力必须"动作或许可有其一"（死能力）。
    //   ⚠️ 候选集必须取自**能力表本身**（`_interfaces`）——**不能**从"动作 ∪ 许可"倒推：
    //   一个**既无动作、又无许可**的能力恰恰**不在**那个并集里，倒推就**正好漏掉要抓的那一格**
    //   （那是"判据看起来在判、其实永远抓不到真违规"的形态）。
    for (name, c) in interfaces {
        let by_action = actions.values().any(|a| &a.capability == name);
        let by_permission = permissions.contains_key(name);
        if !by_action && !by_permission {
            return Err(Violation::DeadCapability {
                capability: name.clone(),
                kind: c.kind.clone(),
                known_actions: action_names(),
            }
            .to_string());
        }
    }
    Ok(())
}
///
/// 三条形态（都可机械判定，`tools/` 里那条反例逐条试过）：
/// 1. 含**空白**（`"pacman -S"` 这类命令行）；
/// 2. 含**路径分隔**或**引号**（`"/usr/bin/pacman"`／`"sh -c 'x'"`）——那是外壳，不是入口名；
/// 3. **逐字等于一条已登记的宿主命令**（`_functions._registered_host_commands`，出厂本体里写着
///    `pacman`／`apt`／`systemctl` …）。
///
/// 为什么"已登记命令名"要写在**本体**里而不是代码里：判据要能被人复算——
/// 名单在本体里，谁都能读、能改（改它＝改法律，走评审）。
fn function_entry_literal(entry: &str, host_commands: &[String]) -> Option<String> {
    if entry.chars().any(|c| c.is_whitespace()) {
        return Some("含空白（那是一条命令行，不是一个入口名）".to_string());
    }
    if entry.contains('/') || entry.contains('\\') || entry.contains('\'') || entry.contains('"') {
        return Some("含路径分隔或引号（那是宿主上的可执行路径，不是一个入口名）".to_string());
    }
    if host_commands.iter().any(|c| c == entry) {
        return Some("逐字等于一条已登记的宿主命令（命令属实现，不属法律）".to_string());
    }
    None
}

/// **声明串的类型词**：本体里写的是 `"integer  # 词表版本；只加 flags…"` 这种形态 ⇒ 取**首词**。
///
/// `enum(change, act, notice)` 整体算一个词（首个空白之前即它）；
/// `ref(job)`／`array(string)`（本批新加的**数组元素形态**）同理。
fn declared_type_word(decl: &str) -> &str {
    let s = decl.trim_start();
    // `enum(a, b, c)` / `ref(x)` / `array(string)` **括号里可能有空白** ⇒ 不能按空白取首词。
    // 取到**配对的那个 `)`** 为止；没有 `)` 就退回"取首词"。
    // ⚠️ **不做嵌套**：`array(ref(job))` 会取到第一个 `)` 为止（与既有 `enum(`／`ref(` 同一射程）。
    for head in ["enum(", "ref(", "array("] {
        if let Some(rest) = s.strip_prefix(head) {
            if let Some(i) = rest.find(')') {
                return &s[..head.len() + i + 1];
            }
        }
    }
    s.split(|c: char| c.is_whitespace()).next().unwrap_or("")
}

/// **这是不是一个本体"声明过口径"的类型词**（即：本判据要不要管它）。
///
/// 认得的：`bool`／`string`／`integer`／`number`／`array`／`object`／`ref(<类型>)`／
/// `enum(…)`／`array(<类型>)`（**数组元素形态**，本批新加）。
/// **不认得的一律不管**——本体里那句写在值是"说明文字"时（例如今天 `envelope.fields`
/// 里的 `"integer  # 词表版本；…"` 取首词仍是 `integer`，那是认得的；而
/// `"枚举三值，见需求"` 取首词是 `枚举三值，见需求`，不认得 ⇒ 放行）。
///
/// ⚠️ 这条函数就是"**要收窄就往本体里写一条认得的声明**"的落点：判据永远是
/// 「本体说了什么」的函数，不是"判据自己发明了一套类型系统"。
fn type_is_declared(word: &str) -> bool {
    matches!(
        word,
        "bool" | "string" | "integer" | "number" | "array" | "object"
    ) || word.starts_with("enum(")
        || word.starts_with("ref(")
        || word.starts_with("array(")
}

/// `enum(a, b, c)` 的成员（按 `,` 切、两侧去空白；空串成员被丢弃）。
fn enum_members(decl: &str) -> Vec<String> {
    let w = declared_type_word(decl);
    let inner = w
        .strip_prefix("enum(")
        .and_then(|x| x.strip_suffix(')'))
        .unwrap_or("");
    inner
        .split(',')
        .map(|m| m.trim().to_string())
        .filter(|m| !m.is_empty())
        .collect()
}

/// **JSON 值的类型名**（报错用；与本体声明里的词同一套写法）。
fn json_type_name(v: &Value) -> &'static str {
    match v {
        Value::Null => "null",
        Value::Bool(_) => "bool",
        Value::Number(n) => {
            if n.is_i64() || n.is_u64() {
                "integer"
            } else {
                "number"
            }
        }
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

/// **这一格的值符不符合本体声明的类型**。
///
/// 认得的类型词：`integer`／`number`／`string`／`array`／`object`／`bool`／
/// `ref(<类型>)`／`enum(a, b, …)`。
///
/// | 声明 | 判据 |
/// |---|---|
/// | `bool`／`string`／`integer`／`number`／`array`／`object` | JSON 类型逐词对 |
/// | `enum(a,b,…)` | **闭集**：值必须在成员里（字符串逐字比；数字与布尔的字面量比）。★ **`kind` 那一格除外**：它由调用方（[`Ontology::validate_types`]）跳过，走**家族查找**报 `UnknownKind`——理由与上位规格引文见该方法的文档 |
/// | `ref(<类型>)` | 值必须是**字符串**且形如 `world://<类型>/<实例…>`（**指向已声明的那个类型**） |
/// | `array(<类型>)` | 值必须是**数组**，且**每一个元素**都符合 `<类型>`（本批新加：数组的**元素形态**也进判据） |
/// | **不认得的词** | 一律放行（`_ => true`）——本体没声明的类型口径，本判据不替它发明 |
///
/// ⚠️ `enum` 从"放行"改成"闭集"是本批的**加强**：原先值不在枚举内**什么都不报**
/// （`validate_types` 里有一句 `continue` 跳过 enum 声明）。加强的代价已如实登记在
/// `_pending_tables`（值的类型与单位仍缺一整套口径），但"闭集"这一半今天就有声明面
/// （`concepts.job.fields.status` 逐字列了三个值），故它今天就能判。
fn type_ok(decl: &str, v: &Value) -> bool {
    match declared_type_word(decl) {
        "integer" => v.is_i64() || v.is_u64(),
        "number" => v.is_number(),
        "string" => v.is_string(),
        "array" => v.is_array(),
        "object" => v.is_object(),
        "bool" => v.is_boolean(),
        w if w.starts_with("enum(") => {
            let members = enum_members(decl);
            match v {
                Value::String(s) => members.iter().any(|m| m == s),
                // 非字符串：拿它的 JSON 字面量与成员逐字比（`enum(1,2,3)` 这类数值枚举才有意义）。
                other => members.iter().any(|m| m == &other.to_string()),
            }
        }
        w if w.starts_with("ref(") => {
            // `ref(<类型>)`：值必须是 `world://<类型>/<实例…>`，且类型**逐字**是声明的那个。
            let want = w
                .strip_prefix("ref(")
                .and_then(|x| x.strip_suffix(')'))
                .unwrap_or("")
                .trim();
            match v {
                Value::String(s) => Ontology::entity_of(s) == Some(want),
                _ => false,
            }
        }
        // ★ `array(<类型>)`：**数组的元素形态**（本批新加）。
        //   为什么是加强而不是新发明：本体原先只能写 `array`——"是不是数组"判得了，
        //   "数组里装的是什么"判不了；`presence.did` 的**元素形态**（世界主体 ／
        //   宿主可执行文件 ／ 发行版包坐标）正是要靠这一格才进得了判据。
        w if w.starts_with("array(") => {
            let want = w
                .strip_prefix("array(")
                .and_then(|x| x.strip_suffix(')'))
                .unwrap_or("")
                .trim();
            match v {
                // 空数组：没有元素可判 ⇒ 放行（判的是"元素形态"，不是"至少一个"）。
                Value::Array(items) => items.iter().all(|it| type_ok(want, it)),
                _ => false,
            }
        }
        _ => true,
    }
}

/// **核心字段名** = `envelope.required` ∪ `envelope.optional`（出厂本体逐字给出的 10 项）。
///
/// ## 为什么**只**算信封字段、不算家族信纸字段（这一条是刻意的）
///
/// 家族（`families`）**本身是可扩展的**：一份"只加扩展"的本体会新增一个家族，
/// 并在同一个名下新增一个概念——出厂门禁脚本 `tools/s1_sys_probe.sh` 的
/// `ontology-ext.json` 就是"新增家族 `audit` ＋ 新增概念 `audit.result`"。
/// 若把"全部家族的必填／可选字段"也算进核心，这份**纯加法**的本体会被判成"重名"而拒启，
/// 而 `REQ-F-030` 判据③ 恰恰要求纯加法**必须照常可读**（换一份只加扩展的本体 ⇒ 折叠结果不变）。
/// ⇒ 核心 = **信封**字段：它由本体逐字列出，不随扩展变动。
fn core_field_names(required: &[String], optional: &[String]) -> BTreeSet<String> {
    required.iter().chain(optional.iter()).cloned().collect()
}

/// **判据②**：扩展项（对象类型的名字与字段名）**SHALL NOT 与核心字段重名**。
///
/// 依据（逐字）：书 §2.7「核心之外由命名空间扩展，各方在自己的空间里定义自己的概念；
/// 核心之内不取交集，也不做删减」；本 change 的 delta `REQ-F-030`：
/// 「扩展项 SHALL 落在命名空间内，**SHALL NOT 与核心字段重名**」。
///
/// 为什么必须**拒启**、而不是打个警告继续跑：重名的扩展项与核心字段**共用一个名字**，
/// 而"核心字段的含义永不因扩展而变"是这一结构的全部价值 ⇒ 一旦叠上，
/// 读的人再也分不清 `body` 指的是哪一个。**改本体＝改法律；法律自相矛盾时不许带病运行**
/// （与 `load` 的其余错误同一处置）。
///
/// ⚠️ 只查对象类型（类型名与字段名）：家族的信纸字段落在 `body` **里面**，
/// 与信封字段不在同一层，同名不构成"改掉核心那一格的含义"。
fn check_extension_names(
    objects: &BTreeMap<String, ObjectType>,
    core: &BTreeSet<String>,
) -> Result<(), String> {
    for (entity, o) in objects {
        if core.contains(entity) {
            return Err(core_collision(
                &format!("对象类型名 `{entity}`"),
                entity,
                core,
            ));
        }
        for f in o.fields.keys() {
            if core.contains(f) {
                return Err(core_collision(
                    &format!("类型 `{entity}` 的字段名 `{f}`"),
                    f,
                    core,
                ));
            }
        }
    }
    Ok(())
}

/// 重名的拒绝理由：**点名**撞上的那一项，并列出全部核心字段（否则只说了"不行"、没说"怎么办"）。
fn core_collision(at: &str, name: &str, core: &BTreeSet<String>) -> String {
    let list = core.iter().cloned().collect::<Vec<_>>().join(", ");
    format!(
        "ext.world.Ontology.CoreCollision: 扩展项与核心字段重名：{at} 与信封字段 `{name}` 同名——\
         本体采用**极小核心 ＋ 命名空间扩展**（书 §2.7 逐字「核心之外由命名空间扩展，\
         各方在自己的空间里定义自己的概念；核心之内不取交集，也不做删减」），\
         扩展项 SHALL NOT 与核心字段重名。\n\
         \x20 核心字段（`envelope.required` ∪ `envelope.optional`，共 {n} 项）：{list}\n\
         \x20 处置：把扩展项换到自己的名字上（出厂本体已声明的两格是 `notice.muted` 与 `job.status`）",
        n = core.len()
    )
}

fn str_list(v: &Value, key: &str) -> Result<Vec<String>, String> {
    let arr = v
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("ext.world.Ontology.BadField: 缺数组字段 `{key}`"))?;
    let mut out = Vec::with_capacity(arr.len());
    for x in arr {
        out.push(
            x.as_str()
                .ok_or_else(|| format!("ext.world.Ontology.BadField: `{key}` 含非字符串项"))?
                .to_string(),
        );
    }
    Ok(out)
}

/// 递归剔除 `_` 开头的键（说明性文字不是词表语义）。
fn strip_comments(v: &Value) -> Value {
    match v {
        Value::Object(m) => {
            let mut out = serde_json::Map::new();
            for (k, val) in m {
                if k.starts_with('_') {
                    continue;
                }
                out.insert(k.clone(), strip_comments(val));
            }
            Value::Object(out)
        }
        Value::Array(a) => Value::Array(a.iter().map(strip_comments).collect()),
        other => other.clone(),
    }
}

/// 词表的内容地址（口径见 [`Ontology::vocab_hash`]）。
pub fn vocab_hash_of(raw: &Value) -> String {
    const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;
    let canonical = strip_comments(raw).to_string();
    let mut h = OFFSET;
    for b in canonical.as_bytes() {
        h ^= u64::from(*b);
        h = h.wrapping_mul(PRIME);
    }
    format!("fnv1a64:{h:016x}")
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    #[test]
    fn vocab_hash_ignores_comments_but_detects_semantic_change() {
        let a = json!({
            "world": 1,
            "_comment": "第一版说明",
            "envelope": {"required": ["world", "kind"], "optional": []},
            "families": {"change": {"required": ["subject"], "optional": []}}
        });
        let b = json!({
            "world": 1,
            "_comment": "**改过措辞的**说明文字",
            "envelope": {"required": ["world", "kind"], "optional": []},
            "families": {"change": {"required": ["subject"], "optional": []}}
        });
        assert_eq!(vocab_hash_of(&a), vocab_hash_of(&b), "改注释不该换词表");

        let c = json!({
            "world": 1,
            "envelope": {"required": ["world", "kind"], "optional": []},
            "families": {"change": {"required": ["subject", "path"], "optional": []}}
        });
        assert_ne!(vocab_hash_of(&a), vocab_hash_of(&c), "改语义必须换词表");
    }

    #[test]
    fn vocab_hash_is_formatting_insensitive() {
        // 同一个对象，直接构造 vs 经过一次 JSON 文本往返 → 必须同 hash
        let a = json!({"world": 2, "families": {"act": {"required": ["capability"]}}});
        let round: Value = serde_json::from_str(&a.to_string()).unwrap();
        assert_eq!(vocab_hash_of(&a), vocab_hash_of(&round));
    }
}
