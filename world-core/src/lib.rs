//! 世界核心（World Core）—— **语义事件是唯一真相**。
//!
//! 本 crate 实现 `07/4-计划/04-模块清单与实现顺序.md` 的模块：
//! - [`ontology`]  —— **法律**：一条事件长什么样、什么算合法变更
//! - [`ledger`]    —— **事实**：只追加的语义事件账本（纯文本 JSON Lines）
//! - [`readmodel`] —— **状态**：`state = fold(events[0..seq])`，**派生物、可随时重算**
//! - [`gate`]      —— **门禁**：一件事现在能不能做（默认拒绝 + 按不可逆性加摩擦）
//! - [`guard`]     —— **静态防线**：法律与真相的存放处不得对被管者开放写权限
//!
//! 并且提供 [`World`] 作为**唯一的写入口**（取号 → 造事件 → 法律校验 → 门禁裁决 → 落笔）。
//!
//! 五条贯穿纪律（`07/4-计划/03` §七）：
//! 1. **一个进程**（本体/账本/读模型/运行时/门禁同进程）；
//! 2. **一个写入口**（只有 [`World::commit`] 能改世界）；
//! 3. **法律在前、落笔在后**（校验不过就绝不写账本）；
//! 4. **状态是算出来的**（不保存状态 ⇒ 不存在"状态与账本不一致"）；
//! 5. **门禁不可绕过**（决策在唯一咽喉 + 规则与真相不受被管者写入）。


pub mod agent;

pub mod bus;
pub mod carrier;
pub mod common;
pub mod gate;
pub mod gui_projection;
pub mod ledger;
pub mod ontology_definition;
pub mod ontology_instance;

use gate::{Decision, Policy};
use ledger::Ledger;
use ontology_definition::Ontology;
use ontology_instance::readmodel::State;
use serde_json::Value;
use std::collections::BTreeSet;
use std::path::Path;

/// **旗标的内核保留前缀**（`gate.`）：只许**内核依裁决结果**写。
///
/// 与 [`World::adjudicate_notice`] 里那个「通告类型的保留前缀」是**两个命名空间里的同一条纪律**
/// （一个是通告的 `type`，一个是信封的 `flags`）——两处**各写一个常量、不共用**：
/// 共用会让"改一个影响另一个"变成看不见的耦合。
const RESERVED_FLAG_PREFIX: &str = "gate.";

/// 写入入口的**可选信封字段**（`trace` 因果 ／ `to` 目的地 ／ `flags` 旗标）。
///
/// ## 为什么是一个结构体，而不是继续给 [`World::commit`] 堆位置参数（形态裁定，理由三条）
///
/// 1. **不破公开签名**：`World::commit` 在 HEAD 上 `tests/**` 有 **60 处**调用点、
///    [`World::commit_requested`] 另有 `tests/delivery.rs` **19 处**与 `src/bus/mod.rs` 的
///    `RequestSink` **1 处调用 ＋ 1 处 trait 声明**。
///    口径说明：`tests/delivery.rs` 的调用点是 **19 处**；`src/bus/mod.rs` 是 **1 处调用 ＋ 1 处 trait 声明**
///    （两者口径不同，不是同一个数）。给它们加参数要逐字改**每一个**调用点，而其中
///    `tests/ontology_ext.rs` 正由并行工区在写——那是**别人的文件**，跨过去就是事故。
/// 2. **可选信封字段是一个概念**：`trace`／`to`／`flags` 都是"信封上可选的格子"。
///    装进结构体以后，再加一个格子**不必动任何调用点**；
///    `commit_requested` 那个五参数签名已经开始痛了（每加一格就长一截）。
/// 3. **写路径仍然只有一条**：本入口与 `commit`／`commit_requested` 一样，
///    都只是 [`World::commit_verbatim`] 的薄壳——**不存在"带旗标就绕过门禁"的第二条路**。
///
/// ## 字段口径
///
/// - `trace`／`to`：`None` 或空串 ⇒ **不写该键**（不写 `null`）。"没有因果"与"因果指向空"是两件事。
/// - `flags`：按给出顺序追加，重复的**只留一个**（`common::event::with_flag` 的口径）。
///   ⚠️ `gate.` 开头的旗标**不许由调用方给**（见 [`World::commit_verbatim`] 的第二段）。
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Envelope {
    /// 因果：引发本条的那条事件的 `id`。
    pub trace: Option<String>,
    /// 目的地。空 ＝ 广播。
    pub to: Option<String>,
    /// 随事件走的**能力旗标**。
    pub flags: Vec<String>,
}

impl Envelope {
    /// 一个可选字段都不给（与 [`World::commit`] 等价）。
    pub fn new() -> Self {
        Self::default()
    }

    /// 设因果（`None` ⇒ 不设）。
    pub fn with_trace(mut self, trace: Option<&str>) -> Self {
        self.trace = trace.map(str::to_string);
        self
    }

    /// 设目的地（`None` ⇒ 不设）。
    pub fn with_to(mut self, to: Option<&str>) -> Self {
        self.to = to.map(str::to_string);
        self
    }

    /// 追加一个旗标（重复的无副作用）。
    pub fn with_flag(mut self, flag: &str) -> Self {
        self.flags.push(flag.to_string());
        self
    }

    /// 一个可选字段都没给。
    pub fn is_empty(&self) -> bool {
        self.trace.is_none() && self.to.is_none() && self.flags.is_empty()
    }
}

/// 一个最小可用的世界：**法律（本体 + 门禁策略）+ 事实（账本）**。
///
/// ⚠️ 字段**全部私有**（2026-09-26 收窄，见 `WC-RV-R2-001` **S-02 / T-02**）。
/// 原先三个字段都是 `pub`，于是任何拿到 `&mut World` 的调用方都能
/// `w.ledger.append(任意 JSON)`、甚至 `w.policy = 自备的宽松策略`——
/// "唯一写入口"当时**只是注释里的散文**，不是代码性质。
/// 现在外部只能拿到 `&` 访问器；写入只能经 [`World::commit`]。
///
/// 这不是注释里的承诺，而是**编译期事实**——下面这段代码必须**编译失败**
/// （`WC-RV-R2-001` T-02 / `DEBT-08`：此前只有散文声明，没有任何机械证据）：
///
/// ```compile_fail
/// use world_core::World;
/// fn smuggle(w: &mut World) {
///     // `ledger` 字段私有：外部拿不到可变引用，因此无法绕过 `commit`
///     let _ = &mut w.ledger;
/// }
/// ```
///
/// 另一条同类证据：`Ledger::append` 是 `pub(crate)`（外部不可见）。
#[derive(Debug)]
pub struct World {
    ontology: Ontology,
    policy: Policy,
    ledger: Ledger,
    /// ★ **写入侧核对用的折叠快照**（读模型的一次快照；**不是第二个真相**）。
    ///
    /// 只服务两道**写入侧**判据：[`World::check_before`]（旧值核对）与
    /// [`World::check_presence_levels`]（在场者有没有申报）。**任何读出口都不用它**
    /// ——`read_model()` 仍每次从账本全量重算 ⇒ "快照算错"只会让写入侧判错，
    /// **不会**让世界读到假状态。它的建立与失效时机见 [`World::folded`]。
    folded: Option<State>,
}

impl World {
    /// 打开世界：加载本体（法律之形状）→ 加载门禁策略（法律之权限）→ 打开账本（事实）。
    ///
    /// 任一步失败即**拒绝启动**（`07/4-计划/03` §五：法律不对，带病跑比不跑更危险）。
    pub fn open(
        ontology_path: &Path,
        ledger_path: &Path,
        policy_path: &Path,
    ) -> Result<Self, String> {
        Self::open_mode(ontology_path, ledger_path, policy_path, false)
    }

    /// **只读**打开世界（`P-01` 修）：账本以只读口径打开 ⇒ **不取写锁、不截断半行、
    /// 不改既有字节**。只读命令（`read` / `state` / `project` / `check`）一律走这里。
    ///
    /// 为什么重要：`REQ-F-012` 与 IC 九册不变量① 都写"只读接口不得写 L1"，
    /// 而此前只读命令会在含半行的账本上执行一次 `set_len`（实测字节从 480 变 442）。
    pub fn open_readonly(
        ontology_path: &Path,
        ledger_path: &Path,
        policy_path: &Path,
    ) -> Result<Self, String> {
        Self::open_mode(ontology_path, ledger_path, policy_path, true)
    }

    fn open_mode(
        ontology_path: &Path,
        ledger_path: &Path,
        policy_path: &Path,
        readonly: bool,
    ) -> Result<Self, String> {
        let ontology = Ontology::load(ontology_path)?;
        let policy = Policy::load(policy_path)?;
        // **两处法律的一致性**（2026-09-28 补）：闸侧的 `capabilities`（能力层）与本体
        // `_interfaces`（五要素之三）说的是同一批能力——**两处的名字集必须一致**。
        // 若不许它们一致，就会出现"闸放行了一项本体里根本不存在的能力"，
        // 而那正是"两个权威各说各话"的形状（本项目最贵的一类错）。
        //
        // ⚠️ 射程（如实声明）：只核**名字集**与**kind**；不核"本体声明了能力却没有任何动作
        // 引用它"——那是 `Policy::load` 那一侧的判据（`CapabilityWithoutAction`），
        // 两边各管各的一半，不许互相冒充。
        {
            let ont_names: std::collections::BTreeSet<&str> =
                ontology.interfaces().map(|(k, _)| k).collect();
            for (name, cap) in policy.capabilities() {
                let Some((_, o)) = ontology.interfaces().find(|(k, _)| *k == name) else {
                    return Err(format!(
                        "ext.world.Gate.CapabilityNotInOntology: 门禁策略声明了能力 `{name}`，\
                         而出厂本体的 `_interfaces` 里**没有它**。\n\
                         \x20 已在本体声明的能力：{}\n\
                         \x20 两处（闸侧 `policy.json` 与本体 `ontology.json`）必须同名同义——\
                         否则闸会放行一项本体里根本不存在的能力。\n\
                         \x20 处置：补齐一侧，或把名字对齐（改法律＝走评审）",
                        ont_names.iter().copied().collect::<Vec<_>>().join(", ")
                    ));
                };
                if o.kind != cap.kind {
                    return Err(format!(
                        "ext.world.Gate.CapabilityKindMismatch: 能力 `{name}` 的 `kind` 两处不一致：\
                         本体 `_interfaces` 说 `{}`，闸侧 `policy.json` 说 `{}`。\n\
                         \x20 处置：把两处改成同一个（改法律＝走评审）",
                        o.kind, cap.kind
                    ));
                }
            }
        }
        let mut ledger = if readonly {
            Ledger::open_readonly(ledger_path)?
        } else {
            Ledger::open(ledger_path)?
        };
        // 摘要链：有链则核验（篡改即拒绝启动），无链则按 v1 放行（WC-CR-003 D2）。
        // ⚠️ 无链时"局部篡改不可检出"——调用方应打印警告（`check` 会打印链状态）。
        ledger.load_chain()?;

        // **读路径也过一遍法律**（`TC-047 ⑧` 的修法）：本体声明了每个信封字段的类型，
        // 而此前**只有写入路径**走 `validate`——账本里已有的形状不合规事件，折叠层照收。
        // 实测两处真实违规（2026-09-28，VM）：`world` 写成字符串 `"1"`、`actor` 写成整数 `123`，
        // `state` 一律 rc=0。⇒ 打开时对每条事件跑一次 `validate_types`（**只判类型**，不是整套 `validate`）：**不合规即拒绝打开**，
        // 与写入路径同一套判据（不另立第二套规矩）。
        for ev in ledger.read_from(1)? {
            // **只跑类型判据**（`Ontology::validate_types`），**不跑整套 `validate`**：
            // 读侧的"缺格"与"未知家族"**另有其主**（读模型的 `ReadModel.MissingCell`／`UnknownKind`，
            // 那是既有契约、有断言在核）⇒ 这里补的是**类型**这一处缺口，不抢别人的码。
            ontology.validate_types(&ev).map_err(|e| e.to_string())?;
        }

        // 词表版本一致性（2026-09-26 补，见 WC-RV-R2-001 S-17）：
        // 信封里的 `world` 由 `common::event::WORLD_VERSION` 写死，而本体自带 `world` 字段。
        // 两者不一致时，构造出的事件**恒被判 BadVersion**——那是自伤性故障：
        // 世界能启动、却一条事件都写不进去，而报错看起来像"事件格式错"。
        // 故在启动时刻就拒绝，把问题暴露在这里而不是每条写入上。
        if common::event::WORLD_VERSION != ontology.world() {
            return Err(format!(
                "ext.world.World.VersionMismatch: 事件构造器版本 {} 与本体声明的 world={} 不一致；\
                 拒绝启动（否则每条事件都会被判 BadVersion）",
                common::event::WORLD_VERSION,
                ontology.world()
            ));
        }

        Ok(World {
            ontology,
            policy,
            ledger,
            folded: None,
        })
    }

    /// 只读访问本体（法律·形状）。
    pub fn ontology(&self) -> &Ontology {
        &self.ontology
    }

    /// 只读访问门禁策略（法律·权限）。
    pub fn policy(&self) -> &Policy {
        &self.policy
    }

    /// 只读访问账本（事实）。**拿不到可变引用**，故无法绕过 [`World::commit`]。
    pub fn ledger(&self) -> &Ledger {
        &self.ledger
    }

    /// **唯一的写入口**。顺序固定、不可交换：
    ///
    /// 1. 取号 → 造事件；
    /// 2. **法律在前**：本体校验（形状不对，连门禁都不必问）；
    /// 3. **门禁裁决**：`act` 与 `change` **都必须过闸**；拒绝/加摩擦时
    ///    **不写原事件**，改记一条 `notice`（`gate.*`）——拦得住，也记得下；
    /// 4. **落笔在后**：只有前三步都通过才追加到账本。
    ///
    /// ## 为什么 `change` 也必须过闸（2026-09-26 修，见 `WC-RV-R2-001` S-01）
    ///
    /// 原实现只裁决 `act`，理由是"`change` 只是记录"。这个理由**站不住**：
    /// `change` 恰恰是**唯一真正改状态的写原语**（读模型里就是
    /// `objects[subject][path] = after`）。于是"被拒绝的动作"完全可以用一条
    /// `change` 静默达成——`actor` 与 `subject` 之间约束为零。
    /// **"门禁不可绕过"当时是假的**，现在由 [`crate::gate::Policy::authorize_write`] 补上。
    ///
    /// `notice` **也过闸**——另有一道**窄闸**，见 [`World::adjudicate_notice`]：
    /// 保留前缀只许内核自己写、其余通告的写信人必须先在主体名单里。
    /// ⚠️ 本句此前写的是"`notice` 仍不过闸"，那是这道窄闸补上**之前**的旧话
    /// （`WC-THEORY-DEFECT-001` **D-13**），按实改正。
    ///
    /// 可选信封字段（`trace`／`to`／`flags`）走 [`World::commit_envelope`]；
    /// 本方法等价于"一个可选字段都不给"（`Envelope::default()`）。
    pub fn commit(&mut self, kind: &str, actor: &str, body: Value) -> Result<Value, String> {
        self.commit_envelope(kind, actor, body, &Envelope::default())
    }

    /// 同 [`World::commit`]，但**显式给出因果与目的地**（可选信封字段）。
    ///
    /// 为什么要这个入口（`M10` 接线，2026-09-27）：跨进程的"请求—结果"必须能配对，
    /// 而配对的依据只有两个——**同一个 `request_id`**（业务层）与 **`trace` 指回意图事件**
    /// （世界层）。此前 `trace` 在源码里**零写入路径**，于是"为什么会变成这样"
    /// 在账本里没有落点（`REQ-F-031` 记为部分实现）。
    ///
    /// 口径：
    /// - `trace`/`to` 为 `None` 或空串 ⇒ **不写该键**（不写 `null`）：没有因果与因果指向空是两件事；
    /// - `trace` **不做引用完整性校验**（`REQ-F-031` 的 v1 口径）：指向不存在的 `id` 不导致拒绝；
    /// - 除此之外与 [`World::commit`] **完全同一条路径**（取号 → 造事件 → 法律 → 门禁 → 落笔），
    ///   不存在"带因果就绕过门禁"的第二条路。
    pub fn commit_requested(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        trace: Option<&str>,
        to: Option<&str>,
    ) -> Result<Value, String> {
        self.commit_envelope(
            kind,
            actor,
            body,
            &Envelope::new().with_trace(trace).with_to(to),
        )
    }

    /// **带可选信封字段的写入入口**：`trace`（因果）、`to`（目的地）、`flags`（能力旗标）。
    ///
    /// 三者都是信封上的格子，一起装进 [`Envelope`]（为什么是结构体而不是位置参数，见该结构体文档）；
    /// 本方法与 [`World::commit`]、[`World::commit_requested`] 走的是**同一条**
    /// [`World::commit_verbatim`]（取号 → 造事件 → 法律 → 门禁 → 落笔）。
    ///
    /// ## 旗标的口径（`REQ-F-029`「未知旗标必须忽略」）
    ///
    /// - 调用方给的旗标**按序追加、重复只留一个**（`common::event::with_flag` 的口径）；
    /// - **不认得的旗标必须放行**：本入口不比对任何"已知旗标表"——出厂本体
    ///   `ontology.json` 的 `flags` 是**空数组**，"认不认得"是**读法**的事（`common::event::read_flags`），
    ///   不是写入入口的事。写入侧只做一件事：**不许替世界署名**（下一条）；
    /// - **内核保留前缀 `gate.` 不许由调用方给**：拒，且留流水。
    ///   这不是"不让你带旗标"，是"不许替世界说话"——闸的摩擦标记
    ///   （`gate.friction:<等级>`）是**世界说的话**，理由与落点见 [`World::commit_verbatim`]。
    pub fn commit_envelope(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        env: &Envelope,
    ) -> Result<Value, String> {
        self.commit_verbatim(
            kind,
            actor,
            body,
            env.trace.as_deref(),
            env.to.as_deref(),
            &env.flags,
        )
    }

    fn commit_verbatim(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        trace: Option<&str>,
        to: Option<&str>,
        flags: &[String],
    ) -> Result<Value, String> {
        let seq = self.ledger.next_seq();
        let mut ev = common::event::new_event(seq, kind, actor, body);
        common::event::with_trace(&mut ev, trace);
        common::event::with_to(&mut ev, to);
        // 调用方给的旗标：**在过法律之前**就位——法律要看到的东西，就是将要落笔的东西。
        for f in flags {
            common::event::with_flag(&mut ev, f);
        }

        // 校验与裁决的顺序（2026-09-27 订正为两段式）：
        //   ① 先校验：形状不合 ⇒ 直接拒，**不写任何东西**（连流水都不写，因为流水同样要过校验）；
        //   ② 校验过了再问门禁：门禁拒绝 ⇒ **写一条 `notice` 流水**，然后拒。
        //
        // 为什么必须两段：门禁模块的文档明写"拒绝也要留痕"，而原实现用 `?` 早退，
        // 使"该不该留痕"取决于"先校验还是先裁决"的偶然顺序。两段式把这条口径变成**结构**。
        if let Err(e) = self.ontology.validate(&ev) {
            return Err(e.to_string());
        }
        let act_body = ev.get("body").cloned().unwrap_or(Value::Null);

        // ── ①b ★ **旧值核对**（本批新立：写入侧本该拦住的那一格）────────────────
        //
        // 为什么在**落笔之前**、且属**法律那一段**（不留门禁流水）：它判的不是
        // "你有没有权限"，而是"**这条事件说的与世界的事实符不符**"——与
        // `ontology.validate` 里的 `check_concepts`（声明以外不许落账）同一类。
        //
        // 依据（真账本里的原始红）：`seq=13` 声称 `before=null`，而折叠出的当前值是
        // `false` ⇒ 那一笔 `rc=0` 落了账，**整本账本从此折不开**，只能靠 `seq=14`
        // 一条撤回把它救回来。⇒ 能在写入侧拦住的事，不许留到读侧去兜底。
        //
        // 反例（必红）：把这一段短路 ⇒ `m20` 当场变红（它会拿到 `Ok`，而它断言必须 `Err`）。
        // ⚠️ **撤回事实是唯一的例外**（本批实测逼出来的）：撤回**不写任何格子**
        //    （读模型对它走 `advance_only`），故"事件声称的旧值"这件事在它身上**不成立**；
        //    更要紧的是——撤回正是「账本已经折不开」时**唯一**还走得通的那条修法
        //    （真账本 `seq=13` 就是靠 `seq=14` 一条撤回救回来的）⇒ 对它做旧值核对
        //    会把唯一的修法也一并堵死（实测反例：`r01`／`r04` 的夹具当场红）。
        //    「是不是撤回事实」取自**读模型自己的**认定函数（`retract_target_of`），
        //    **不另立第二套**口径。
        let refusal_is_retraction = matches!(
            ontology_instance::readmodel::retract_target_of(&ev),
            Ok(Some(_))
        );
        if kind == "change" && !refusal_is_retraction {
            if let (Some(s), Some(p), Some(b)) = (
                act_body.get("subject").and_then(Value::as_str),
                act_body.get("path").and_then(Value::as_str),
                act_body.get("before"),
            ) {
                self.check_before(s, p, b)?;
            }
        }

        // ── ② 的前半：**调用方给的旗标不许占用内核保留前缀**（2026-09-28 补，工区 F）──
        //
        // 为什么这条必须有：信封的 `flags` 里**混着两种作者**——
        // 内核自己写的那一格（闸的摩擦标记 `gate.friction:<等级>`，由本函数依裁决结果加上去），
        // 与调用方带来的旗标。若调用方能随便写 `gate.` 开头的旗标，他就能**替世界说**
        // "这件事被加过摩擦"——与 `gate.*` 通告的伪造（`WC-THEORY-DEFECT-001` **D-13**）
        // **同一形状**：账本里伪造的那一格与真的那一格逐字同形，事后不可区分。
        //
        // 口径三条（与 [`World::adjudicate_notice`] 的"保留前缀"同一纪律）：
        // - 判定**只按前缀**（`gate.`），不猜语义：`gate.friction:high` 与 `gate.随便什么` 一样拒；
        // - 拒在**门禁那一段**（校验之后），并照书 §4.2「被拦下的请求也要留痕」**留流水**；
        // - 流水的理由**逐字点名那个旗标**（`refused` 指纹只覆盖"发起者＋信纸"，
        //   不含信封旗标——被拒的是哪个旗标，由 `payload.reason` 说）。
        //
        // ⚠️ 已登记的边界（不假装已闭合）：
        // - 本判定**只管前缀**，故调用方仍可写任意**非** `gate.` 前缀的旗标——
        //   那正是 `REQ-F-029`「未知旗标必须忽略」要验的那条路，**不许收窄**；
        // - 出厂本体 `ontology.json` 的 `flags` 是**空数组**（一个已声明旗标都没有）⇒
        //   "哪些旗标属于内核"这件事**在本体里没有对照面**，只能写在代码里（上面那个常量即那一处）；
        // - 旗标**不由门禁策略裁决**（`policy.json` 里没有旗标这一栏）⇒ 这是一条写在代码里的纪律，
        //   不是策略；要不要把它挪进策略属门禁强度变更，须人裁。
        for f in flags {
            if f.starts_with(RESERVED_FLAG_PREFIX) {
                return Err(self.gate_refusal(
                    "ext.world.Gate.FlagNotAllowed",
                    "gate.flag-not-allowed",
                    "门禁拒绝旗标",
                    actor,
                    &act_body,
                    &format!(
                        "旗标 `{f}` 占用**内核保留前缀**（`{RESERVED_FLAG_PREFIX}`）——\
                         它只由内核依裁决结果写（例如闸的摩擦标记 `gate.friction:<等级>`）。\n\
                         \x20 为什么必须保留：否则任何主体都能替世界说\"这件事被加过摩擦\"，\
                         而账本里伪造的旗标与真旗标**逐字同形、事后不可区分**。\n\
                         \x20 处置：换成你自己的旗标名（不要以 `{RESERVED_FLAG_PREFIX}` 开头）"
                    ),
                ));
            }
        }

        let friction = self.adjudicate(kind, actor, &act_body)?;

        // **摩擦落账**（书 §5.5：摩擦挂在动作的不可逆等级上）。
        //
        // 加摩擦不能只是裁决内存里的一个字段——它必须留下**可核的痕迹**，
        // 否则"加过摩擦"在账本里查不到，审计就无从谈起。落点选信封的 `flags`：
        // 本体纪律要求"未知旗标必须忽略" ⇒ 旧读法读到它不会坏，新读法能核出它。
        //
        // ⚠️ 加旗标发生在法律校验**之后**，所以加完必须**再过一遍法律**——
        // "法律在前、落笔在后"不许因为"我在法律之后又改了事件"而破。
        if let Some(f) = &friction {
            common::event::with_flag(&mut ev, &f.flag());
            if let Err(e) = self.ontology.validate(&ev) {
                return Err(e.to_string());
            }
        }

        let written = self.ledger.append(ev)?;
        self.note_appended(&written);
        Ok(written)
    }

    /// ★ **写入侧 `before` 核对**（本批新立）：事件声称的旧值必须等于账本折叠出的当前值。
    ///
    /// ## 为什么这条判据必须在**写入侧**（它是那条坏行的真源头）
    ///
    /// 读模型早就有这道墙（`State::apply_change` ⇒ `ext.world.ReadModel.BeforeMismatch`），
    /// 但**写入侧不过它** ⇒ 一条「谎称旧值」的 `change` 照旧 `rc=0` 落笔，
    /// 而它一出账本、**整本账本就折不开了**。
    /// 实测（真账本 `seq=13`）：事件称 `before=null`，而折叠出的当前值是 `false`；
    /// 那一笔落账之后，只能靠再写一条撤回（`seq=14`，`path=retract_seq`）把账本救回来。
    /// ⇒ **能在写入侧拦住的事，不许留到读侧去兜底。**
    ///
    /// ## 口径（与读侧**同一口径**，不是第二套规矩）
    ///
    /// - **格子还不存在** ⇒ 没有可比对的旧值 ⇒ **放行**（读侧 `apply_change` 也只在
    ///   **已有当前值**时比对 ⇒ 两处同一口径，"首写"这件事两侧读法一致）；
    /// - **格子已有当前值** ⇒ `before` 必须与它**逐字相等**，否则拒
    ///   （`ext.world.World.BeforeMismatch`），并**点名三样**：`subject#path`、
    ///   事件声称的 `before`、账本折叠出的当前值。
    ///
    /// 反例（必红）：把本函数短路成恒 `Ok(())` ⇒ `m20` 变红（它断言这一笔必须 `Err`）。
    fn check_before(&mut self, subject: &str, path: &str, before: &Value) -> Result<(), String> {
        let current = self.folded()?.get(subject, path).cloned();
        match current {
            None => Ok(()),
            Some(cur) if cur == *before => Ok(()),
            Some(cur) => Err(format!(
                "ext.world.World.BeforeMismatch: 旧值不符（{subject}#{path}）：\
                 事件声称 before={before}，但账本折叠出的当前值是 {cur}。\n\
                 \x20 为什么写入侧必须拦：这条事件与账本的事实不符——放过它，账本从此**折不开**\
                 （读模型报 `ext.world.ReadModel.BeforeMismatch`），而「账本折不开」当时只有\
                 靠**再写一条撤回**才救得回来（真账本 `seq=13` 就是这么来的）。\n\
                 \x20 处置：先读当前值（`world-core state`），把它填进 `before` 再提交"
            )),
        }
    }

    /// ★ **在场者的两级分开**（本批新立）：① **申报**（依据）→ ② **授权**（许可）。
    ///
    /// ## 口径（逐字，作者定的设计；别处引用**不复述**）
    ///
    /// > **申报给的是“依据”，授权给的是“许可”。二者不许合并——一旦合并，等于在场者
    /// > 自己给自己发许可证，世界就不再管着它。报得再全，也不自动拿到任何能力；
    /// > 开放只由许可决定（`_permissions.grants` ＋ `default: deny`）。**
    ///
    /// ## 三级（顺序是死的，三条各判真假）
    ///
    /// | # | 情形 | 结局 |
    /// |---|---|---|
    /// | ① | **没申报**的在场者调用**任何**能力 | **拒**（`ext.world.World.PresenceNotDeclared`，点名「该在场者未在世界里申报」） |
    /// | ② | **申报了但没被授予** | **拒**（`ext.world.Gate.CapabilityNotGranted`）——**声明存在 ≠ 你有许可**，**不许**做成「自报即通行」 |
    /// | ③ | **申报了且被授予** | **通**（正控；交回既有门禁裁决，本函数**不**替它裁决） |
    ///
    /// ## 三个词的判据（都可判真假）
    ///
    /// - **在场者** ＝ `actor` 形如 `world://presence/<实例>`；
    /// - **申报** ＝ 折叠出的世界里**这个主体有自己的格**（`presence` 的五格写在它名下）；
    /// - **被授予** ＝ 本体 `_permissions.grants.<能力>.scope` 里有模式命中该主体
    ///   （该能力不在 `grants` 里、或 scope 不命中 ⇒ **不授予**，即 `default: deny`）。
    ///
    /// ## 射程（如实声明，不许被读成"全体主体都要逐能力授权"）
    ///
    /// **只对在场者生效**。其余主体（`world://user`／`world://core`／`world://agent/*`）
    /// 的口径**一字未动**——给它们逐能力判 `grants` 是**门禁强度变更**，须人裁，本批不扩。
    ///
    /// 反例（必红）：把本函数短路成恒 `Ok(())` ⇒ `m22` 的两条反例当场变红。
    fn check_presence_levels(&mut self, actor: &str, body: &Value) -> Result<(), String> {
        /// 在场者主体的前缀（本体声明的类型名是 `presence`，实例形态 `world://presence/<实例>`）。
        const PRESENCE_PREFIX: &str = "world://presence/";
        if !actor.starts_with(PRESENCE_PREFIX) || actor.len() == PRESENCE_PREFIX.len() {
            return Ok(());
        }

        // ① 申报（依据）：这个世界里有没有它自己的格。
        let declared = {
            let st = self.folded()?;
            st.entries().any(|(s, _, _)| s == actor)
        };
        if !declared {
            return Err(self.gate_refusal(
                "ext.world.World.PresenceNotDeclared",
                "gate.presence-not-declared",
                "门禁拒绝在场者的请求",
                actor,
                body,
                &format!(
                    "该在场者未在世界里申报：`{actor}` 名下一格都没有——\
                     **没申报的在场者不许调用任何能力**。\n\
                     \x20 两级是分开的、顺序是死的：**先申报（依据），再授权（许可）**。\n\
                     \x20 申报给的是“依据”，授权给的是“许可”，二者不许合并——\
                     一旦合并，等于在场者自己给自己发许可证，世界就不再管着它。\n\
                     \x20 处置：先把它的格写进世界（一次完整申报＝逐格一条 `change`）"
                ),
            ));
        }

        // ② 授权（许可）：`_permissions.grants` 的 `scope` 有没有命中它；没有 ⇒ 默认拒绝。
        let capability = body.get("capability").and_then(Value::as_str).unwrap_or("");
        let granted = self
            .ontology
            .permissions()
            .find(|(name, _)| *name == capability)
            .map(|(_, p)| p.scope.iter().any(|pat| gate::pattern_matches(pat, actor)))
            .unwrap_or(false);
        if !granted {
            return Err(self.gate_refusal(
                "ext.world.Gate.CapabilityNotGranted",
                "gate.capability-not-granted",
                "门禁拒绝在场者的请求",
                actor,
                body,
                &format!(
                    "`{actor}` 已申报，但**没有**能力 `{capability}` 的许可——\
                     **声明存在 ≠ 你有许可**。\n\
                     \x20 开放只由许可决定（本体 `_permissions.grants` ＋ `default: deny`）：\
                     `{capability}` 的 `scope` 里没有 `{actor}`。\n\
                     \x20 报得再全，也不自动拿到任何能力。处置：由有资格者先把它授给这个在场者"
                ),
            ));
        }
        // ③ 两级都过 ⇒ 交回既有门禁（本函数**不**替它裁决）。
        Ok(())
    }

    /// 取（必要时先建）**写入侧核对用的折叠快照**（见 `World::folded` 字段的文档）。
    ///
    /// ## 为什么需要它（而不是每次现折）
    ///
    /// 核对要求"账本折叠出的当前值"，而**每次写入都全量折叠一遍**是 O(n²)——
    /// `World::commit` 的调用点里有 10 000 条量级的度量用例（`tests/perf.rs::qg01`）。
    ///
    /// ## 它**不**推翻纪律④「状态是算出来的」
    ///
    /// 读出口一个都不用它（`read_model()` 每次从账本全量重算）；建立是**懒的**
    /// （第一次要用才折一次）；失效是**窄的**（只在撤回落笔与侧路写入两处整块作废，
    /// 见 [`World::note_appended`] 与 [`World::record_gate_notice`]）。
    fn folded(&mut self) -> Result<&State, String> {
        if self.folded.is_none() {
            let evs = self.ledger.read_all()?;
            self.folded = Some(State::fold(&evs)?);
        }
        Ok(self.folded.as_ref().expect("上一行刚建好"))
    }

    /// 落笔之后的**快照维护**（唯一维护点：只由 [`World::commit_verbatim`] 调用）。
    ///
    /// 三条口径：
    /// 1. **撤回事实 ⇒ 整块作废**：撤回说的是「某一条**已经算过的**事件不算数」，
    ///    而增量施加会把那一条的效果留下 ⇒ 只能下次重新全折
    ///    （`State::fold` 的**撤回预扫**正是为了这件事）；
    /// 2. **还没有快照 ⇒ 什么都不做**（下次要用时自然从账本全量重建）；
    /// 3. **增量施加失败 ⇒ 作废**（宁可下次重折，也不留一个说不清的快照）。
    fn note_appended(&mut self, ev: &Value) {
        let is_retraction = ev.get("kind").and_then(Value::as_str) == Some("change")
            && ev
                .get("body")
                .and_then(|b| b.get("path"))
                .and_then(Value::as_str)
                == Some(ontology_instance::readmodel::RETRACT_PATH);
        if is_retraction || self.folded.is_none() {
            self.folded = None;
            return;
        }
        if let Some(st) = self.folded.as_mut() {
            if st.apply(ev).is_err() {
                self.folded = None;
            }
        }
    }

    /// 门禁裁决（`act` 与 `change` **都必须过闸**），拒绝时**留痕并返回点名错误码**。
    ///
    /// 返回 `Ok(Some(摩擦))` = 这次动作**不可逆**：放行，但摩擦必须随事件落账
    /// （由 [`World::commit_verbatim`] 落到 `flags` 上）。
    ///
    /// 抽成独立函数是因为两条拒绝路径必须说同样的话、留同样的痕——
    /// 复制两份迟早漂移成两种口径。
    fn adjudicate(
        &mut self,
        kind: &str,
        actor: &str,
        body: &Value,
    ) -> Result<Option<gate::Friction>, String> {
        match kind {
            "act" => {
                // ★ **在场者两级分开**（本批新立）：**先申报（依据）、再授权（许可）**。
                //   排在这里（`policy.verdict` **之前**）是刻意的：没申报的在场者
                //   连"为什么被拒"都该听到**它自己那一级的理由**，而不是被白名单那句
                //   "不在门禁白名单内"顶掉（那样判据①点到名的就不是它该听的那句话了）。
                self.check_presence_levels(actor, body)?;
                let verdict = self.policy.verdict(actor, body);
                match verdict.decision {
                    // 准了：把摩擦交回给落笔那一步（不可逆 ⇒ `Some`，可逆 ⇒ `None`）。
                    Decision::Allow => Ok(verdict.friction),
                    Decision::Reject(reason) => Err(self.gate_refusal(
                        "ext.world.Gate.Rejected",
                        "gate.rejected",
                        "门禁拒绝",
                        actor,
                        body,
                        &reason,
                    )),
                    Decision::AwaitApproval(reason) => Err(self.gate_refusal(
                        "ext.world.Gate.AwaitingApproval",
                        "gate.awaiting-approval",
                        "门禁加摩擦",
                        actor,
                        body,
                        &reason,
                    )),
                }
            }
            "change" => {
                let subject = body
                    .get("subject")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_string();
                // `authorize_write` 现只返回 Allow/Reject（不可逆分级只作用于 `act`）；
                // 万一将来它返回"加摩擦"，按**默认拒绝**处理，而不是默默放行。
                match self.policy.authorize_write(actor, &subject) {
                    Decision::Allow => Ok(None),
                    Decision::Reject(reason) | Decision::AwaitApproval(reason) => Err(self
                        .gate_refusal(
                            "ext.world.Gate.WriteRejected",
                            "gate.write-rejected",
                            "门禁拒绝写入",
                            actor,
                            body,
                            &reason,
                        )),
                }
            }
            "notice" => {
                self.adjudicate_notice(actor, body)?;
                Ok(None)
            }
            _ => Ok(None),
        }
    }

    /// **通告的闸**（2026-09-27 补，`WC-THEORY-DEFECT-001` **D-13**）。
    ///
    /// ## 为什么通告也必须过闸（这条以前是缺的，而且缺得很危险）
    ///
    /// 此前 `notice` 落在 `adjudicate` 的 `_ => Ok(())` 分支里——**任何主体可以写任何通告**。
    /// 后果不是"多了几条噪声"，而是**整套审计可被一行伪造**：
    ///
    /// ```text
    /// world-core append notice \
    ///   '{"type":"gate.rejected","subject":"world://user","payload":{"reason":"伪造"}}' \
    ///   world://stranger
    /// ⇒ rc=0，账本里出现一条与内核真流水**逐字同形**的 notice
    /// ```
    ///
    /// 也就是说："世界拒绝过这件事"这句话，**任何人都能替世界说**。
    /// 审计的价值全在"这句话不是你说的，是世界说的"——这条一破，审计等于没有。
    ///
    /// ## 修法（两条纪律，各自可单独判真假）
    ///
    /// | # | 纪律 | 反例（必须被拒） |
    /// |---|---|---|
    /// | **① 保留前缀** | `gate.` 开头的通告类型**只许内核自己写**（内核的拒绝/加摩擦流水），外部提交一律拒 | 外部主体提交 `type=gate.rejected` |
    /// | **② 主体须在册** | 非保留前缀的通告，其 `actor` **必须已在主体白名单内** | 不在册的主体提交任意通告 |
    ///
    /// ## 为什么"内核的流水"不受 ① 之限
    ///
    /// 内核写 `gate.*` 流水**不是为了记录"某主体做了什么"**，而是为了记录
    /// **"世界对某次请求的裁决"**——那件事发生的位置就是内核自己。
    /// 而"内核对谁裁决过"已经由 `decide`/`authorize_write` 的**白名单与授权表**限定了；
    /// 被拒的主体虽然写不了别的，但**它的这次被拒必须留痕**（否则丢掉了审计信息）。
    /// 两件事不冲突：**外部不能冒充世界，世界必须记得拒绝过谁。**
    ///
    /// ## 一处诚实的不对称（登记，不假装已解决）
    ///
    /// 非保留前缀的通告**不检查 `writes` 授权表**，只检查主体白名单。理由：现实现里
    /// `writes` 的默认形状（`world://agent/* → []`）会让**所有** agent 通告被拒，
    /// 而那会顺手打断载体侧已有的状态通告路径。**本次只堵"可伪造审计"这个洞**，
    /// 通告要不要按主体收窄授权**属门禁强度变更，须人裁**。
    fn adjudicate_notice(&mut self, actor: &str, body: &Value) -> Result<(), String> {
        /// 保留前缀：只许内核自己写。
        const RESERVED_PREFIX: &str = "gate.";

        let notice_type = body.get("type").and_then(Value::as_str).unwrap_or("");

        if notice_type.starts_with(RESERVED_PREFIX) {
            return Err(self.gate_refusal(
                "ext.world.Gate.NoticeNotAllowed",
                "gate.notice-not-allowed",
                "门禁拒绝通告",
                actor,
                body,
                &format!(
                    "通告类型 `{notice_type}` 是**内核保留前缀**（`{RESERVED_PREFIX}`）——\
                     它只由内核自己写（记录'世界对某次请求的裁决'）。\n\
                     \x20 为什么必须保留：否则任何人都能替世界说\"我拒绝过这件事\"，\
                     而账本里的伪造流水与真流水**逐字同形、事后不可区分** ⇒ 审计等于没有。\n\
                     \x20 处置：换成你自己的通告类型（不要以 `{RESERVED_PREFIX}` 开头）"
                ),
            ));
        }

        if !self.policy.subject_allowed(actor) {
            return Err(self.gate_refusal(
                "ext.world.Gate.NoticeRejected",
                "gate.notice-rejected",
                "门禁拒绝通告",
                actor,
                body,
                &format!(
                    "主体 `{actor}` 不在门禁白名单内（policy.json 的 subjects.allow）——\
                     通告同样要过闸：世界允许谁说话，就得先在册"
                ),
            ));
        }
        Ok(())
    }

    /// 门禁拒绝的统一出口：**写流水 + 返回点名错误码**。
    ///
    /// 流水写失败**不得吞掉拒绝理由**：调用方收到的是"为什么被拒"，
    /// 流水失败作为附注（`WC-RV-R2-001` S-10）。
    ///
    /// ## 流水必须点名"它在拒绝什么"（2026-09-27 补，`D-14`）
    ///
    /// `gate.*` 前缀是**内核保留**的（见 [`World::adjudicate_notice`]），但保留只解决了
    /// "谁能写"，没解决"**写的是什么**"。实测发现的歧义：一次**外部提交**被拒时，
    /// 内核留的流水与内核**自己发起**的裁决流水**同样是 `gate.*` 类型**，
    /// 于是读账本的人分不清：
    ///
    /// - 这条 `gate.notice-rejected` 是"**内核拒绝了某个主体的通告**"（内核发起的裁决），还是
    /// - "某个主体的请求**被拒了**，这是它的流水"（对外部尝试的记录）？
    ///
    /// 修法：流水里带上**它在拒绝什么**——`refused` 字段，内容是"被拒对象的规范形式"的指纹与摘要：
    ///
    /// - 外部尝试被拒 ⇒ `refused` 指向**那条没落笔的事件**（kind / actor / body 的指纹）；
    /// - 内核自身发起的裁决（如某主体的通告被拒）⇒ `refused` 说明"无被拒事件"，
    ///   因为**没有一条外部事件被拒**，被拒的是内部那条流水本身。
    ///
    /// 这样：**流水与它记录的那次尝试之间有可复核的对应关系**，而不是"一堆同样类型的行"。
    /// ⚠️ 登记一处局限（不假装已解决）：本字段**不含被拒事件的全部内容**（只含指纹），
    /// 因此"拒绝一条超大载荷的请求"时，被拒载荷本身**不入账本**——这是刻意的
    /// （否则任何主体都能靠"提交垃圾再被拒"无限撑大账本）。
    fn gate_refusal(
        &mut self,
        code: &str,
        notice_type: &str,
        headline: &str,
        actor: &str,
        body: &Value,
        reason: &str,
    ) -> String {
        match self.record_gate_notice(notice_type, actor, body, reason) {
            Ok(()) => format!("{code}: {headline}：{reason}"),
            Err(notify_err) => format!(
                "{code}: {headline}：{reason}（⚠️ 且流水写入失败：{notify_err} —— \
                 本次拒绝**未能留痕**，调用方务必自行记录）"
            ),
        }
    }

    /// 记一条门禁流水。
    ///
    /// 走的是与 `commit` 同一套"校验 → 落笔"路径（**不绕过法律**），
    /// 只是主体取"被拦下的那个 actor"、类型是 `notice`。
    ///
    /// **流水里必须能看出"它在拒绝什么"**（`D-14`，见 [`World::gate_refusal`] 的文档）：
    /// `refused` 字段给出"被拒对象"的**规范形式指纹**，于是"内核发起的裁决"与
    /// "对外部尝试的记录"在账本里**可区分、可复核**，而不是一堆同样类型的行。
    fn record_gate_notice(
        &mut self,
        notice_type: &str,
        actor: &str,
        act_body: &Value,
        reason: &str,
    ) -> Result<(), String> {
        let seq = self.ledger.next_seq();
        // `refused` = 被拒对象的规范形式指纹。
        //
        // 口径：**指纹只覆盖"这次尝试是什么"**（kind / actor / 信纸），
        // 不覆盖载荷的全文——理由见 `gate_refusal` 的文档（防"提交垃圾再被拒"撑大账本）。
        let refused = Self::refused_digest(actor, act_body);
        let payload = serde_json::json!({
            "capability": act_body.get("capability").cloned().unwrap_or(Value::Null),
            "verb": act_body.get("verb").cloned().unwrap_or(Value::Null),
            "request_id": act_body.get("request_id").cloned().unwrap_or(Value::Null),
            // 被拒对象是谁（`change` 是它要写的那个主体，`act` 是发起者自己）。
            //
            // ⚠️ 字段名刻意**不叫 `subject`**（2026-09-27 改）：`notice` 家族的**信纸本身**
            // 就有一个必填的 `subject`（"这条通告是关于谁的"）。若流水里再放一个同名的
            // `subject`，就会出现"两个 subject、指两个不同的东西"的歧义——实测它把一条
            // 既有断言弄红了（脚本按字符串找被拒主体，结果捞到了内核的流水）。
            // 命名口径：**信纸字段名归本体；payload 内不得复用信纸字段名。**
            "refused_subject": act_body.get("subject").cloned().unwrap_or(Value::Null),
            "refused": refused,
            "reason": reason,
        });
        let ev = common::event::new_event(
            seq,
            "notice",
            actor,
            common::event::notice_body(notice_type, actor, payload),
        );
        self.ontology.validate(&ev).map_err(|e| e.to_string())?;
        self.ledger.append(ev)?;
        // ★ **侧路写入 ⇒ 折叠快照整块作废**：门禁流水**不**走 `commit_verbatim`
        //   （它要能记下"一条被拒的事件"，而那条事件过不了校验），故这里自己作废，
        //   下次要用时从账本重折——宁可重折一次，也不留一个说不清的快照。
        self.folded = None;
        Ok(())
    }

    /// "被拒对象"的**规范形式指纹**（`D-14`）。
    ///
    /// 为什么需要它：`gate.*` 前缀保留只解决了"**谁能写**"，没解决"**写的是什么**"。
    /// 一次外部提交被拒时，内核留的流水与内核自己发起的裁决流水**类型相同**——
    /// 读账本的人分不清"这是内核在裁别人"还是"这是别人的尝试被裁了"。
    ///
    /// 口径（三条，都可判真假）：
    /// 1. **覆盖"这次尝试是什么"**：发起者 + 信纸的规范化 JSON（键有序）；
    /// 2. **不覆盖载荷全文**：否则任何主体都能靠"提交垃圾再被拒"无限撑大账本；
    /// 3. **可复算**：给定同一次尝试，任何人事后都能算出同一个值。
    fn refused_digest(actor: &str, body: &Value) -> String {
        // 规范化：`serde_json` 的 `Value::to_string` 对 `Map` 按键有序输出
        //（本项目全程依赖这一性质保证"同输入同字节"，见读模型与投影的确定性口径）。
        let canon = format!("{actor}\u{1}{body}");
        format!("fnv1a64:{:016x}", Self::fnv1a64(canon.as_bytes()))
    }

    /// FNV-1a 64 位（**非加密**指纹；全项目同一实现口径）。
    fn fnv1a64(bytes: &[u8]) -> u64 {
        let mut h: u64 = 0xcbf2_9ce4_8422_2325;
        for b in bytes {
            h ^= *b as u64;
            h = h.wrapping_mul(0x0000_0100_0000_01b3);
        }
        h
    }

    /// **从账本重算状态**（读模型入口）。
    ///
    /// 这个方法**不缓存、不写盘、不记住上次结果**——每次调用都是"把账本从头折叠一遍"。
    /// 慢是它的缺点，也是它的全部价值：**它不可能与账本不一致**。
    /// 将来若加快照（`M08`），必须先证明"从快照续算"与"从这里重算"结果相同。
    ///
    /// ## 为什么在这里把**法律**递给读模型（`REQ-F-032` 的缺格判据）
    ///
    /// 读模型侧的缺格判据要按"本体**已声明**的必填格"来判（书第五章 5.6 表 5.2 行逐字
    /// 「每个已声明的字段至少有一份读法可读，缺格就报错」），而读模型**不许**
    /// `use crate::ontology_definition::…`——`WC-MODREG-001` §2 给 `M03` 的口径是「**无**（生产代码零出边）」，
    /// 机核层 `tools/module_graph.py` 判据② 逐边核对「声明集 ≡ 真实 import 集」。
    /// ⇒ 依赖方向留在**装配处**：本处（`M04`，依赖列本就含 `M01` 与 `M03`）把法律以**纯数据**
    /// 递进去（[`Ontology::envelope_required`]／[`Ontology::family_required`]），
    /// 两边读的是**同一份**出厂本体——同源，且不新增任何模块边。
    ///
    /// ⚠️ 这一行让**命令这一级**也变严：`state`／`project` 对"缺已声明必填格"的账本行
    /// 从"静默通过"变成"拒"（`ext.world.ReadModel.MissingCell`，点名缺的那一格）。
    /// `tools/s1_sys_probe.sh` 的 `TC-047` ⑨ 登记的就是这一格（逐字：「缺必填信封字段 `actor`
    /// 竟**被接受**…折叠层不校验」），它**同日改为断言**。
    pub fn read_model(&self) -> Result<State, String> {
        let cells = ontology_instance::readmodel::DeclaredCells::new(
            self.ontology.envelope_required(),
            self.ontology.family_required(),
        )
        // **按类型的实例上限**（第三批的判据面）：`_objects.<类型>.instance_mode: "single"`
        // ⇒ 上限 1。同样以**纯数据**递进去（理由逐字同上：读模型生产代码零出边），
        // 判据落在**折叠之后**的实例计数上（`State::type_counts` 是那一面的读数）。
        .with_instance_limits(self.ontology.instance_limits())
        // ★ **每个实例必须指回定义面**（书 §5.3 的**读侧**那一半；写侧在 `Ontology::check_concepts`）。
        //   同样以**纯数据**递进去（不新增模块边：`known_entities`／`nested_types` 与上面两处
        //   同源，都是 `M01` 已有的只读出口）。判据也落在**折叠之后**——实例集是折叠的产物。
        //   ⚠️ 这一行是**接线点**：不接 ⇒ 读侧不判（`DeclaredCells::declared_entities` 为 `None`），
        //   于是"读法比写法宽"。⇒ `tests/ontology_instance.rs` 有一条端到端断言钉着它。
        .with_declared_entities(
            self.ontology
                .known_entities()
                .into_iter()
                .map(str::to_string)
                .collect(),
            self.ontology.nested_types(),
        );
        State::fold_declared(&cells, &self.ledger.read_all()?)
    }
}

/// `M09`（通道）对内核提出的窄接口：**纯转发**到 [`World::commit_requested`]。
///
/// 为什么要在这里写这个 `impl`（而不是让 `src/bus/mod.rs` 直接 `use crate::World`）：
/// `WC-ATOM-001` §二 A-4 要求模块号依赖**单向 DAG**，而通道与运行时互相 `use` 会成环。
/// 依赖的真实方向只有一个——**运行时驱动通道**（`src/main.rs:622`）；通道需要的是
/// "谁能收下这条请求"，不是"世界长什么样"。把这条事实写成窄接口后：
/// `M09 → M04` 这条边**从源码里消失**，而**行为一字未改**（转发，不复制任何逻辑）。
///
/// ⚠️ 这里**不许**出现第二条写路径：转发目标就是 [`World::commit_requested`] 本身，
/// "取号 → 造事件 → 法律 → 门禁 → 落笔"仍然只有那一条（`M04` 的唯一写入口不变）。
impl crate::bus::RequestSink for World {
    fn commit_requested(
        &mut self,
        kind: &str,
        actor: &str,
        body: Value,
        trace: Option<&str>,
        to: Option<&str>,
    ) -> Result<Value, String> {
        World::commit_requested(self, kind, actor, body, trace, to)
    }
}

/// **写侧的"声明面"由谁来答**（书 §4.5 的第二条：前值必须带上、翻不出来就报错、不许猜）。
///
/// 写侧（`M10`）只需要知道**一件事**：某个 (主体, 字段) 在出厂声明里吗。
/// 这一层知识属于**这部法律**，所以由 [`Ontology`] 来答——装配点在这里（`M04`），
/// 与上面那条 [`crate::bus::RequestSink`] 同理：**接口窄到只回答一个问题**，
/// 装配关系只出现在 `M04` 这一处，`M10` 自己不反向依赖 `M01`／`M03`（那会成环，A-4 不许）。
impl crate::carrier::translate::Declared for Ontology {
    fn is_declared(&self, subject: &str, path: &str) -> bool {
        // 主体 → 实体名（`world://notice/n-1` ⇒ `notice`）→ 该实体已声明的字段集。
        Ontology::entity_of(subject)
            .and_then(|e| self.declared_fields(e))
            .is_some_and(|fields| fields.contains_key(path))
    }
}

// ─────────────────────────── 声明面 → 实例面 ───────────────────────────
//
// **"声明了，就必须在实例面上看得见。"** 本批两条判据共用这一处实现：
//   ① **实例位的可见形态**：`_permissions.grants.<能力>.instances` 里点名的在场者，
//      **必须真的在世界里有格**（否则"授权授给了一个世界上不存在的在场者"）；
//   ② **投影的可达性**：投影**声明面**里点名的每一份投影，**必须真的出得来**
//      （否则"世界里有哪些投影"这句话是空的 —— 声明集 ≡ 可达集，恒真）。

/// **判读结论：三态。** ★"未校验"是**一等状态**，不许被读成绿。
///
/// ## 为什么必须有第三态（G1 的落法，不是洁癖）
/// **声明面为空／不存在**时，"声明集 ⊆ 可达集"这句话**恒真** —— 一条都没声明，当然一条都不缺。
/// 那不是"通过了"，是"**这条判据无从成立**"。
/// ⇒ 本项目最贵的一类错是"**因为什么也没读到而绿**"（且它不报错、不留痕）
/// ⇒ 所以这里**在类型上**就不给绿的机会：判不了 ⇒ [`Coverage::NotVerified`]。
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coverage {
    /// 声明集**非空**，且其中每一条在实例面上都有可见形态。
    Green,
    /// 有声明在实例面上**找不到**（点名它们）。
    Red { missing: Vec<String> },
    /// ★**判不了**：声明面不存在／为空 ⇒ 判据无从成立。**它不是绿。**
    NotVerified { why: String },
}

/// **声明面 → 实例面：每一条声明都必须兑现**（本批两条判据的同一个形状）。
///
/// ## 两侧各是什么（调用方给纯数据，理由同 `DeclaredCells`：读模型不许反向依赖本体）
/// | 用途 | `declared` | `covered` |
/// |---|---|---|
/// | **实例位的可见形态** | `_permissions.grants.<能力>.instances` 点名的在场者 | 世界里**真有格**的 `world://presence/*` |
/// | **投影的可达性** | 投影**声明面**点名的投影名 | `project <名>` **真的出得来**的那些 |
///
/// ## 三态口径（逐条可判真假）
/// 1. `declared == None`（**声明面不存在**）⇒ [`Coverage::NotVerified`]
/// 2. `declared == Some(空集)`（**声明面为空**）⇒ [`Coverage::NotVerified`] ← ★**G1：空集不许判绿**
/// 3. 否则：`declared − covered` **非空** ⇒ [`Coverage::Red`]（**点名**缺哪几条）；为空 ⇒ [`Coverage::Green`]
///
/// ## 只判**单向**（`声明 ⊆ 可达`），反向**不判**
/// "世界上有、但没被声明"是**另一条判据**的事（写侧的 `UndeclaredEntity` 管"落账必须已声明"）。
/// ⇒ **两半不许互相冒充**（同一体例：读模型的 `UnknownKind` 与 `MissingCell` 不许互相冒充）。
///
/// ## 今天它是"骨架"（如实声明，不许读成已生效）
/// 两个 `declared` 侧今天**都还没有装配点**（投影声明面与 `instances` 字段在定义面，
/// 归 `M01`）。⇒ 今天它跑起来必然走 `NotVerified`；**等定义面落地，接上装配点，它才真判。**
/// ★**"没接"这件事由 `NotVerified` 显式表达**，不许由"绿"冒充。
pub fn declaration_coverage(
    declared: Option<&BTreeSet<String>>,
    covered: &BTreeSet<String>,
) -> Coverage {
    let Some(declared) = declared else {
        return Coverage::NotVerified {
            why: "声明面不存在 —— 这条判据无从成立（\"一个都没声明\"与\"一个都不缺\"在读数上一样、在结论上相反）".to_string(),
        };
    };
    if declared.is_empty() {
        return Coverage::NotVerified {
            why: "声明面为空 —— 这条判据无从成立（G1：空集不许判绿）".to_string(),
        };
    }
    let mut missing: Vec<String> = declared.difference(covered).cloned().collect();
    missing.sort();
    if missing.is_empty() {
        Coverage::Green
    } else {
        Coverage::Red { missing }
    }
}
