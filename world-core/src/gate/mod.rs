//! 门禁（`M05`）—— **不可绕过是 world 与 app 之间唯一的硬分界**。
//!
//! 依据 `07/2-依据/15-世界核心的组成与职责.md` 与 `WC-SRS-001`
//! `REQ-F-015/016/017`。
//!
//! ## 门禁不是什么
//!
//! 不是"权限系统"，也不是"登录校验"。它只回答一个问题：
//! **这一条 `act` 事件，现在能不能执行？** 并且把答案变成**可读的流水**。
//!
//! ## 三条设计口径（都是刻意的）
//!
//! 1. **默认拒绝**：`policy.json` 的 `capabilities` 里没有的能力一律不放行。
//!    理由：默认允许的系统，其安全性等于"没人写错规则"；而规则一定会写错。
//! 2. **按不可逆性分级加摩擦**：可逆的动作免检但**必须留痕**；
//!    不可逆的动作由 `irreversible_actors` 白名单主体执行，白名单外的主体走
//!    `AwaitApproval`（加摩擦）——**v1 没有审批通道**（`DEBT-07`），不是"等等就会批"。
//!    理由：不是所有事情都值得拦，但所有事情都值得记。
//! 3. **拒绝也要留痕**：被拒的动作**不写入 `act` 事件**（它没发生），
//!    但会写一条 `notice`（`gate.rejected` / `gate.awaiting-approval`）。
//!    理由：本项目的目标是"事前拦截 + 一条人能读懂的流水"，
//!    只拦不记等于把审计能力丢掉。
//!
//! ## 不可绕过的另一半
//!
//! 本模块只负责**决策**。让决策无法被绕过的，是
//! ① [`crate::World::commit`] 这一处**唯一咽喉**（进程内无第二条写路径），
//! ② [`crate::gate::guard`] 对策略文件与账本的**权限静态检查**（被管者改不动规则）。
//!
//! 三者缺一，"不可绕过"就不成立——所以它们是**一组**，不能只看其中一处。

pub mod guard;
use crate::carrier::capd::{Manifest as CarrierManifest, Risk as CarrierRisk};
use crate::gate::guard;
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// 载体执行清单所在的目录名（`policy.json` 的**同级目录**下的 `cap.d/`）。
///
/// 为什么互校要在这里找它：两处出厂配置必须能当面比对，而它们今天各在一个路径上——
/// 世界侧是 `policy.json`，载体侧是 `cap.d/*.json`。取"策略的同级 `cap.d`"这条约定，
/// 是为了让互校**在加载策略时自动发生**（不新增命令行参数、不给部署方留一个忘记打开的开关）。
pub const CARRIER_DIR: &str = "cap.d";

/// 一个**能力**的评级（**能力层**：『这类东西能被怎样对待』）。
///
/// ## 为什么现在有**两个**字段（2026-09-28 改，书第五章 §5.5 判红）
///
/// 原先这里只有一个 `reversible` 布尔，理由写在 `WC-R4-DISP-001` §三 **E-5** 裁定①：
/// 删掉那个不参与裁决的 `requires_approval`。删得对——但同一段文字里还有第三个字段
/// 从未进过闸：**风险等级**。书 §5.5 第三条逐字：
///
/// > 「这一项本来要成为闸侧的判据，而闸读不到它：闸读的那份评级里只有一个布尔值……
/// > `risk` 只被载体侧的清单解析器读。于是"低危／中危／高危"这套分级，
/// > 在"准不准做"这件事上不参与判断。」
///
/// 所以 `risk` 是**补上"闸读得到风险等级"**（它决定摩擦的**落点与轻重**，
/// 见 [`Policy::verdict`]）；`requires_approval` 不参与任何裁决
/// （v1 没有审批通道，见 `DEBT-07`）。
///
/// ## 本批再加一刀：**能力与动作分两层**（`kind` 进能力，`reversible` 出能力）
///
/// 「可不可逆」是**动作**的性质（同一项能力可以有可逆与不可逆两种动作），
/// 而「能被怎样对待」才是能力。故 `reversible` 迁到 [`ActionDecl`]，
/// 能力这一层只留 [`Capability::kind`]（可读／可配／可调）与 [`Capability::risk`]。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capability {
    /// 能力的**类别**：`read`（可读）／`config`（可配）／`invoke`（可调）。
    ///
    /// 三值取自本体 `_interfaces` 的同名字段——**两处必须同名同义**
    /// （闸侧这一格与本体那一格讲的是同一件事，见 `World::open_mode` 的互核）。
    pub kind: String,
    /// **动作的不可逆等级**（闸侧判据）：该能力在载体执行清单里声明的 `risk`。
    ///
    /// `None` = 这一项**没有**执行清单（出厂清单 8 项能力里只有 3 项有）。
    /// 缺口必须**看得见**：`None` 不得被当成 `Low` 来读——那会把"没声明"
    /// 悄悄变成"低危"，正是本项目反复判红的那种悄悄放宽。
    pub risk: Option<CarrierRisk>,
}

/// 一条**动作**（**动作层**：『怎么改』）——它必须引用一个**已声明的能力**。
///
/// ## 为什么单独立这一层（本批的判据面）
///
/// 拆分前，`policy.json` 的 `capabilities` 一个段干两件事：既当"这类东西能被怎样对待"
/// 的声明，又当 `act` 信纸里 `capability` 字段的查表。于是两件事永远无法分别判：
/// **没有能力支撑的动作**（引用了不存在的名字）与**没有动作的能力**（声明了却没有任何
/// 动作引用它）都不可见——它们长得和"正常声明"一模一样。
///
/// 拆开后：`actions.<动作>.capability` 必须指得到 `capabilities` 里的一个名字，
/// 指不到即拒启（`ext.world.Gate.ActionCapabilityUnknown`）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ActionDecl {
    /// 引用的**能力名**（必须已在 `capabilities` 里声明）。
    pub capability: String,
    /// 这次改动退不退得回来（闸的摩擦挂在它上面；`act` 信纸的 `capability` 填的是**动作名**）。
    pub reversible: bool,
}

/// 门禁裁决。
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision {
    /// 放行。
    Allow,
    /// 拒绝（法律里没有这个能力、或主体不在白名单）。
    Reject(String),
    /// 加摩擦：本主体不可执行该不可逆动作。v1 **没有审批通道**，
    /// 须改由 `irreversible_actors` 白名单主体执行（`DEBT-07`）。
    AwaitApproval(String),
}

/// **摩擦**：不可逆动作必加的那一层。
///
/// ## 落点（书 §5.5 判红的那一条）
///
/// > 「摩擦本该挂在动作的不可逆等级上：可逆处放手，不可逆处加摩擦。
/// > 今天它挂在执行者的身份上。」
///
/// 本结构由**动作**决定（`reversible: false` ⇒ 必有摩擦），与"谁在请求"无关；
/// 身份只在**下一步**决定摩擦的后果：
///
/// | 动作 | 主体 | 后果 |
/// |---|---|---|
/// | 可逆 | 白名单内 | 免检（`Allow`），act 本身落账 ⇒ 留痕 |
/// | **不可逆** | 白名单内（预批） | 放行，**且事件带上摩擦旗标**（[`Friction::flag`]）⇒ 加摩擦且留可核流水 |
/// | **不可逆** | 白名单外 | `AwaitApproval`（拒绝执行）＋一条 `gate.awaiting-approval` 流水 ⇒ 加摩擦到拒绝 |
///
/// ⚠️ 一处**如实声明**的边界：v1 没有审批通道（`DEBT-07`）。所以白名单主体的摩擦
/// **不是**"停下来等人批"，而是"必留可核痕迹 + 由预批身份承担"。不得把它读成
/// "有审批环节"——那会重新承诺一个不存在的出口。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Friction {
    /// 动作的不可逆等级（载体清单的 `risk`；**没有清单 ⇒ `None`**，不得当成低危）。
    pub risk: Option<CarrierRisk>,
    /// 落账的旗标前缀（`event::FLAG_FRICTION`）。
    pub mark: &'static str,
}

impl Friction {
    /// 随事件落账的旗标全文：`gate.friction:high` / `gate.friction:unlisted`。
    pub fn flag(&self) -> String {
        let level = match self.risk {
            Some(CarrierRisk::Low) => "low",
            Some(CarrierRisk::Medium) => "medium",
            Some(CarrierRisk::High) => "high",
            None => "unlisted",
        };
        format!("{}:{level}", self.mark)
    }

    /// 人可读的等级名。
    pub fn level_name(&self) -> &'static str {
        match self.risk {
            Some(CarrierRisk::Low) => "low",
            Some(CarrierRisk::Medium) => "medium",
            Some(CarrierRisk::High) => "high",
            // 没有清单 ≠ 低危：缺口如实写出来。
            None => "未声明（没有执行清单）",
        }
    }
}

/// 一次裁决的**完整结论**：准不准 + 加不加摩擦。
///
/// 为什么要分开：`Decision` 回答"这次能不能做"，`friction` 回答"这次该不该加摩擦"。
/// 合成一个枚举会把两件事挤进一格（原先就是这样：只有 `AwaitApproval` 才像"摩擦"，
/// 于是白名单主体执行不可逆动作时**一点痕迹都没有**——书 §5.5 判的正是这一格）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Verdict {
    /// 准不准。
    pub decision: Decision,
    /// `Some` = 本次动作**不可逆** ⇒ 必加摩擦（与请求者是谁无关）。
    pub friction: Option<Friction>,
}

/// 出厂门禁策略（`policy.json` 的内存形态）。
#[derive(Debug, Clone)]
pub struct Policy {
    version: u64,
    /// **能力层**（『这类东西能被怎样对待』）：名字 → `kind` ＋ `risk`。
    caps: BTreeMap<String, Capability>,
    /// **动作层**（『怎么改』）：名字 → 它引用的能力 ＋ 可逆性。
    ///
    /// 本批新立。`act` 信纸的 `capability` 字段填的是**动作名**，而每个动作必须
    /// 引用一个[`Policy::capabilities`]里声明过的能力（[`Policy::load`] 逐条核）。
    actions: BTreeMap<String, ActionDecl>,
    allow: Vec<String>,
    /// **谁可以写哪些主体**（`change` 家族的授权）。
    ///
    /// 为什么必须有这一段（2026-09-26 由安全评审发现，见 `WC-RV-R2-001` **S-01**）：
    /// 原实现只对 `act` 裁决，而 `change` **才是真正的状态写原语**——
    /// 于是任何"被拒绝的动作"都可以用一条 `change` 静默达成，
    /// `actor` 与 `subject` 之间毫无约束。**当时"门禁不可绕过"是假的。**
    ///
    /// 默认拒绝：本映射里没有列出的主体，**不得写任何主体**。
    writes: BTreeMap<String, Vec<String>>,
    /// **谁可以执行不可逆动作**（2026-09-26 加，见 WC-RV-R2-001 FIND-12 / DEBT-07）。
    ///
    /// 为什么需要：原先 `!reversible` 一律返回 `AwaitApproval`，而 `commit` 收到即 `Err`，
    /// 仓内**没有批准命令、没有批准事件、没有消费路径** ⇒ 被判不可逆的能力
    /// 在 v1 **永远无法执行**（`policy.json` 里三个能力因此全是死号）。
    /// 文档却写"先取得批准再重试"——措辞与实现不符。
    ///
    /// v1 的处置（**明确的最小治理规则**）：不可逆动作**只允许白名单里的主体**执行
    /// （通常是世界的主人）；其他主体拿到的是"加摩擦"，且理由里**说明 v1 没有审批通道**，
    /// 不得让人以为"等等就能批"。
    irreversible_actors: Vec<String>,
    /// **载体侧的执行清单**（`cap.d/*.json`，与策略同目录）。
    ///
    /// 为什么闸要拿它（书 §5.5 三条红的第三条）：
    /// ① 闸要**读得到风险等级**（`risk` 只长在这里，见 [`Capability::risk`]）；
    /// ② 闸要能**两处互校**（世界侧 `reversible` ↔ 载体侧 `risk`/`confirm`，
    ///    见 [`cross_check_reversibility`]）。
    /// 清单本身**不裁决**——它只说"这件事在载体上怎么干"（`carrier/mod.rs` 的纪律）。
    carrier: CarrierManifest,
    /// 载体清单目录（报错点名用）。`None` = 那儿**没有** `cap.d` 目录。
    carrier_dir: Option<PathBuf>,
    path: PathBuf,
}

/// 模式匹配：`*` 结尾表示前缀匹配，否则要求完全相等。
/// **主体模式匹配**：`*` 结尾＝前缀匹配，否则逐字相等。
///
/// `pub(crate)`（本批）：`World::check_presence_levels`（`src/lib.rs`）要拿它判
/// 「本体 `_permissions.grants.<能力>.scope` 有没有**授给**这个在场者」——
/// **不许**在别处抄第二份匹配口径（一处事实只有一个权威载体）。
pub(crate) fn pattern_matches(pattern: &str, value: &str) -> bool {
    match pattern.strip_suffix('*') {
        Some(prefix) => value.starts_with(prefix),
        None => value == pattern,
    }
}

/// 装载**载体侧执行清单**（`<策略同目录>/cap.d/*.json`）。
///
/// 三条口径（都可判真假）：
/// 1. **没有 `cap.d` 目录 ⇒ 不是错误**：载体侧什么都没声明，就没有"两处"可比。
///    返回空清单 + `None`，互校跳过（[`cross_check_reversibility`] 对空清单无事可做）。
///    为什么不拒启：拒启会把"单机只用世界侧策略"这一形态一并打死——
///    而那是今天出厂命令（`bash check.sh` 的一次性沙箱）真实使用的形态。
///    代价如实写出：**没有清单的能力，闸读不到它的风险等级**（`Capability::risk == None`）。
/// 2. 清单文件与目录同样受**静态墙**约束：它们现在参与"拒启"这个决定，
///    所以和策略一样，被管者不得能改（否则改清单就能把世界弄成起不来，或把互校糊过去）。
/// 3. 坏清单（非法 JSON、缺字段、非法分级）**即拒启**——由 `Manifest::load_dir` 报错，
///    本函数不改写它的错误码。
fn load_carrier_manifests(
    policy_path: &Path,
) -> Result<(CarrierManifest, Option<PathBuf>), String> {
    let dir = policy_path
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join(CARRIER_DIR);
    if !dir.is_dir() {
        return Ok((CarrierManifest::default(), None));
    }
    guard::assert_not_other_writable(&dir, "执行清单目录（载体侧 cap.d）")?;
    let manifest = CarrierManifest::load_dir(&dir)?;
    for cap in manifest.iter() {
        guard::assert_not_other_writable(&cap.source, "执行清单（载体侧 cap.d）")?;
    }
    Ok((manifest, Some(dir)))
}

/// **两处出厂配置互校**（书 §5.5 第二条：两处对不上 ⇒ 拒绝启动）。
///
/// ## 互校的是什么
///
/// 同一项能力，"做完了撤不撤得回来"这句话必须**只有一个准头**：
///
/// | 处 | 文件 | 它说的那句 |
/// |---|---|---|
/// | 世界侧 | `policy.json` 的 `capabilities.<能力>.reversible` | 这件事在世界状态里退不退得回来 |
/// | 载体侧 | `cap.d/<能力>.json` 的 `risk` / `confirm` | 这件事在载体上有多不可逆 |
///
/// ## 载体侧的可逆性是怎么导出的（一条规则，可判真假）
///
/// `risk: high` **或** `confirm: required` ⇒ 载体侧判**不可逆**；否则判**可逆**。
///
/// **为什么不用 `undo`**（这一条是刻意绕开的坑）：书 §5.5 逐字——
///
/// > 「`ledger.compact` 这一项，执行清单里写 `"undo": "before-each"`（动手前先留一个撤销点），
/// > 出厂清单里写 `"reversible": false`（这件事做完回不来）。这两句问的是两件事：
/// > 载体撤销撤的是文件系统上的字节，只作工程兜底；世界可不可逆，说的是这件事在世界里
/// > 退不退得回来。**两个轴各自成立，谁也不能推出谁。**」
///
/// ⇒ 拿 `undo` 参与互校，会把"留了撤销点、世界里仍不可逆"这一**书明说的正常形态**
/// 误判成冲突（出厂三份清单里 `ledger.compact` 恰好就是这一形态）。
/// 而 `risk` 不同：书同节逐字「这一项本来要成为**闸侧的判据**」——
/// 风险等级就是载体对"这件事有多不可逆"的声明，它才配当互校的另一端。
///
/// ## 不一致时拒启
///
/// 理由与本体/策略加载失败同一条（`07/4-计划/03` §五）：**法律不对，带病跑比不跑更危险**。
/// 两处各说各话时，"要不要加摩擦、撤不撤得回来"就没有准头——
/// 与其让运行时挑一个，不如当场拒启并点名是哪一项、两处各写了什么。
fn cross_check_reversibility(
    caps: &BTreeMap<String, Capability>,
    actions: &BTreeMap<String, ActionDecl>,
    carrier: &CarrierManifest,
    policy_path: &Path,
    carrier_dir: Option<&Path>,
) -> Result<(), String> {
    for name in caps.keys() {
        // 只在**两处都声明了**的能力上比：清单里没有它 ⇒ 载体侧没说话，无从互校。
        let Some(m) = carrier.lookup(name) else {
            continue;
        };
        // 世界侧那句话现在长在**动作**上（同一项能力可以有可逆与不可逆两种动作）：
        // 互校对的是"这个名字这一件事做完了撤不撤得回来"，故取**引用它的那些动作**的结论。
        // 若没有任何动作引用它（`config` 类能力允许），这一项在世界侧**没说话** ⇒ 无可互校。
        let world_reversible = cap_of_actions(name, actions);
        let Some(world) = world_reversible else {
            continue;
        };
        let carrier_says_reversible = !(m.risk == CarrierRisk::High || m.needs_confirm());
        if carrier_says_reversible == world {
            continue;
        }
        let risk = match m.risk {
            CarrierRisk::Low => "low",
            CarrierRisk::Medium => "medium",
            CarrierRisk::High => "high",
        };
        let confirm = if m.needs_confirm() {
            "required"
        } else {
            "never"
        };
        let carrier_says = if carrier_says_reversible {
            "可逆"
        } else {
            "不可逆"
        };
        let dir = carrier_dir
            .map(|d| d.display().to_string())
            .unwrap_or_else(|| format!("{CARRIER_DIR}/（未找到目录）"));
        return Err(format!(
            "ext.world.Gate.ReversibilityMismatch: 出厂配置**两处对不上**，拒绝启动。\n\
             \x20 能力 `{name}`：\n\
             \x20  · 世界侧（{policy} 的 actions.<动作>.reversible，引用该能力）声明 reversible={world}；\n\
             \x20  · 载体侧（{manifest}，目录 {dir}）声明 risk={risk}、confirm={confirm}\
             ⇒ 推出载体侧{carrier_says}。\n\
             \x20 两处对『这件事做完了撤不撤得回来』各说各的，摩擦该不该加就没有准头——\n\
             \x20 与其让运行时挑一个，不如当场拒启（法律不对，带病跑比不跑更危险）。\n\
             \x20 口径：载体侧可逆性由 `risk: high` 或 `confirm: required` 导出；\n\
             \x20  `undo` **不参与**互校——它说的是『动手前留不留**载体**撤销点』（撤的是\n\
             \x20  文件系统上的字节），与世界可不可逆是两个轴，谁也不能推出谁。\n\
             \x20 处置：改两处之一，让它们讲同一件事，然后重启（策略只在启动时读一次）。",
            policy = policy_path.display(),
            manifest = m.source.display(),
            dir = dir,
            risk = risk,
            confirm = confirm,
            carrier_says = carrier_says
        ));
    }
    Ok(())
}

/// **引用这个能力的那些动作在世界侧说的可逆性**。
///
/// - 没有任何动作引用它 ⇒ `None`（这项能力**没在世界侧就"撤不撤得回来"说话**——
///   `config` 类能力允许这种形态，见 [`Policy::load`]）；
/// - 多个动作引用同一个能力且结论不一致 ⇒ `None`（**"这项能力可不可逆"这句话在
///   世界侧有两个说法** ⇒ 那也是"没说话"，互校不该挑一个当准头）。
fn cap_of_actions(name: &str, actions: &BTreeMap<String, ActionDecl>) -> Option<bool> {
    let mut it = actions.values().filter(|a| a.capability == name);
    let first = it.next()?.reversible;
    if it.any(|a| a.reversible != first) {
        return None;
    }
    Some(first)
}

impl Policy {
    /// 加载策略。**含静态防线检查**（文件与目录不得对 group/other 可写）。
    ///
    /// 启动时**一次**读入；运行中不重读（见 `policy.json` 的 `_invariants`）。
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("门禁策略（法律）无法读取 {}：{e}", path.display()))?;
        let root: Value = serde_json::from_str(&text)
            .map_err(|e| format!("门禁策略（法律）不是合法 JSON（{}）：{e}", path.display()))?;

        let version = root
            .get("policy")
            .and_then(Value::as_u64)
            .ok_or_else(|| "门禁策略缺少 `policy` 版本号".to_string())?;
        if version != 1 {
            return Err(format!(
                "门禁策略版本不支持：期望 1，实得 {version}（法律版本不符即拒绝启动）"
            ));
        }

        // ── 能力层（本批拆出来的两层之一）：`capabilities.<名字>.kind` ──────────
        let caps_obj = root
            .get("capabilities")
            .and_then(Value::as_object)
            .ok_or_else(|| "门禁策略缺少 `capabilities` 段".to_string())?;
        let mut caps = BTreeMap::new();
        for (name, spec) in caps_obj {
            if name.starts_with('_') {
                continue;
            }
            // **能力名不许长得像具体对象**：能力是"能被怎样对待"，不是某个实例。
            // 授权授在具体对象上是从这里开始错的，故挡在入口。
            if name.starts_with("world://") {
                return Err(format!(
                    "ext.world.Gate.GrantNotOnCapability: `capabilities` 里出现了 `{name}`——\
                     能力**不落在具体对象上**（`world://…` 是实例引用，不是能力名）。\n\
                     \x20 处置：把它改成一项能力的名字（例如 `notice.mute`），\
                     对具体对象的授权是**事实**，走账本事件"
                ));
            }
            let kind = spec
                .get("kind")
                .and_then(Value::as_str)
                .ok_or_else(|| {
                    format!(
                        "能力 `{name}` 缺少 `kind`（可读 `read`／可配 `config`／可调 `invoke`）——\
                         capabilities 是**能力层**，`kind` 是它唯一的必填格"
                    )
                })?
                .to_string();
            if !matches!(kind.as_str(), "read" | "config" | "invoke") {
                return Err(format!(
                    "能力 `{name}` 的 `kind` 是 `{kind}`——只认 `read`／`config`／`invoke`"
                ));
            }
            // 本段为手工取值（`serde_json::Value`，**没有** `deny_unknown_fields`）：
            // 能力项里的多余/未知键（例如已删除的 `requires_approval`、迁移期的 `reversible`）
            // 一律**忽略**。理由（E-5 裁定①）：未知键既不该拒载，也不该影响裁决。
            //
            // `risk` 的来源**不是**这里，而是载体执行清单（下一步由 `load_carrier_manifests`
            // + `cross_check_reversibility` 填）：闸要读的风险等级必须**两处互校过**才作数，
            // 在策略里再写一个 `risk` 只会多出第三个各说各话的地方。
            caps.insert(name.clone(), Capability { kind, risk: None });
        }
        if caps.is_empty() {
            return Err(
                "门禁策略的 capabilities 为空——空策略不是『什么都不允许』的安全默认，\
                 而是『法律没写好』；请显式写出允许的能力（默认可通过不声明获得）"
                    .to_string(),
            );
        }

        // ── 动作层（本批拆出来的两层之二）：`actions.<动作>.capability` ──────────
        //
        // ★ **判据**：动作引用了不存在的能力 ⇒ 拒启。**这是本批新增的那道闸**：
        // 拆分之前，"一个动作拿什么当依据"这件事在策略里**没有声明面**——
        // `act` 信纸里填一个名字，闸只能拿它去查能力表，查不到就当场拒那条请求；
        // 而"某条动作**从写下那一刻起**就没有法律依据"这件事**没有任何人能看见**。
        let actions_obj = root
            .get("actions")
            .and_then(Value::as_object)
            .ok_or_else(|| "门禁策略缺少 `actions` 段——**动作层**（『怎么改』）".to_string())?;
        let mut actions = BTreeMap::new();
        for (name, spec) in actions_obj {
            if name.starts_with('_') {
                continue;
            }
            let capability = spec
                .get("capability")
                .and_then(Value::as_str)
                .ok_or_else(|| {
                    format!(
                        "动作 `{name}` 缺少 `capability`（它引用的能力名）——\
                         动作必须挂在一项「能被怎样对待」上，否则这次改没有法律依据"
                    )
                })?
                .to_string();
            if !caps.contains_key(&capability) {
                return Err(format!(
                    "ext.world.Gate.ActionCapabilityUnknown: 动作 `{name}` 引用了**不存在的能力**\
                     `{capability}`（`policy.json` 的 `capabilities` 里没有它）。\n\
                     \x20 已声明的能力：{}\n\
                     \x20 处置：改用已声明的能力，或先在 `capabilities` 里声明它（改法律＝走评审）",
                    caps.keys().cloned().collect::<Vec<_>>().join(", ")
                ));
            }
            let reversible = spec
                .get("reversible")
                .and_then(Value::as_bool)
                .ok_or_else(|| format!("动作 `{name}` 缺少 `reversible` 布尔值"))?;
            actions.insert(
                name.clone(),
                ActionDecl {
                    capability,
                    reversible,
                },
            );
        }
        if actions.is_empty() {
            return Err(
                "门禁策略的 actions 为空——动作是**唯一**的写入通道，一个动作都没有的世界\
                 什么都改不了；请显式写出动作（默认拒绝）"
                    .to_string(),
            );
        }
        // **反向一格**：`config`／`invoke` 类的能力**必须**有动作引用它。
        // 为什么：声明了一项能力却没有任何动作挂上去 ⇒ 那项能力在闸上**永远走不到**
        // （`act` 填的是动作名）⇒ 它是一条**死声明**：读法律的人会以为它能用。
        // `read` 不在此列——"可读"由读法（投影／`read`）兑现，不必有写动作。
        for (name, cap) in &caps {
            if cap.kind == "read" {
                continue;
            }
            if !actions.values().any(|a| &a.capability == name) {
                return Err(format!(
                    "ext.world.Gate.CapabilityWithoutAction: 能力 `{name}`（kind={}）\
                     **没有任何动作引用它** ⇒ 它在闸上永远走不到（`act` 信纸填的是动作名）。\n\
                     \x20 处置：给它加一条动作（`actions.<动作>.capability = \"{name}\"`），\
                     或把它的 `kind` 改成 `read`（可读由读法兑现，不必有写动作）",
                    cap.kind
                ));
            }
        }

        let allow = root
            .get("subjects")
            .and_then(|s| s.get("allow"))
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();
        if allow.is_empty() {
            return Err(
                "门禁策略的 subjects.allow 为空——没有主体能做事的世界等于死掉；\
                 请显式列出允许的主体（支持结尾 * 前缀匹配）"
                    .to_string(),
            );
        }

        // ── writes：change 家族的授权（S-01）──
        let writes_obj = root
            .get("writes")
            .and_then(Value::as_object)
            .ok_or_else(|| {
                "门禁策略缺少 `writes` 段——**默认拒绝**要求显式声明\
                 「谁可以写哪些主体」；缺失即拒绝加载（否则 change 可绕过一切裁决）"
                    .to_string()
            })?;
        let mut writes: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for (actor, subjects) in writes_obj {
            if actor.starts_with('_') {
                continue;
            }
            let list = subjects
                .as_array()
                .ok_or_else(|| format!("writes 的 `{actor}` 不是数组"))?
                .iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect::<Vec<_>>();
            writes.insert(actor.clone(), list);
        }
        if writes.is_empty() {
            return Err(
                "门禁策略的 writes 为空——没有任何主体能写入状态的世界等于死掉；\
                 请显式列出「主体 → 可写主体模式」（默认拒绝）"
                    .to_string(),
            );
        }

        // irreversible_actors：谁能执行不可逆动作（默认拒绝：缺省即无人）
        let irreversible_actors = root
            .get("irreversible_actors")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();

        // 静态防线：规则所在之处，被管者不得能写
        guard::assert_not_other_writable(path, "门禁策略（法律）")?;

        // ── 载体侧执行清单：闸读得到的「不可逆等级」＋**两处互校**（书 §5.5）──
        //
        // 顺序刻意放在静态墙**之后**：权限不对时先报权限（那是更基本的故障），
        // 权限对了再比对两处配置讲不讲得通。
        let (carrier, carrier_dir) = load_carrier_manifests(path)?;
        cross_check_reversibility(&caps, &actions, &carrier, path, carrier_dir.as_deref())?;
        // 把等级接进能力表：**闸从此读得到风险等级**（此前 `risk` 只被载体侧读）。
        for (name, cap) in caps.iter_mut() {
            cap.risk = carrier.lookup(name).map(|m| m.risk);
        }

        Ok(Policy {
            version,
            caps,
            actions,
            allow,
            writes,
            irreversible_actors,
            carrier,
            carrier_dir,
            path: path.to_path_buf(),
        })
    }

    /// **写入裁决**：这个 `actor` 能不能写 `subject`（`change` 家族的授权）。
    ///
    /// 这是 2026-09-26 补上的一道闸：在此之前 `change` 只过本体形状校验，
    /// 于是"被拒绝的 `act`"完全可以用一条 `change` 达成（S-01）。
    pub fn authorize_write(&self, actor: &str, subject: &str) -> Decision {
        if !self.subject_allowed(actor) {
            return Decision::Reject(format!(
                "主体 `{actor}` 不在门禁白名单内（policy.json 的 subjects.allow）"
            ));
        }
        match self.writes.get(actor) {
            None => Decision::Reject(format!(
                "主体 `{actor}` 未获写入授权（policy.json 的 writes 里没有它）——\
                 默认拒绝：状态不能被未授权的角色直接改写"
            )),
            Some(patterns) => {
                if patterns.iter().any(|p| pattern_matches(p, subject)) {
                    Decision::Allow
                } else {
                    Decision::Reject(format!(
                        "主体 `{actor}` 无权写 `{subject}`（writes 允许的是 {patterns:?}）——\
                         越界的写入一律不放行"
                    ))
                }
            }
        }
    }

    pub fn version(&self) -> u64 {
        self.version
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// 遍历已声明的能力（键有序，输出确定）。
    pub fn capabilities(&self) -> impl Iterator<Item = (&str, &Capability)> {
        self.caps.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// 遍历已声明的动作（键有序，输出确定）。
    pub fn actions(&self) -> impl Iterator<Item = (&str, &ActionDecl)> {
        self.actions.iter().map(|(k, v)| (k.as_str(), v))
    }

    /// 某条动作的声明（`None` ＝ 这个动作没声明过）。
    ///
    /// ⚠️ `act` 信纸的 `capability` 字段填的是**动作名**（见 [`Policy::decide`]）——
    /// 本方法就是"拿那个名字查声明"的唯一入口。
    pub fn action(&self, name: &str) -> Option<&ActionDecl> {
        self.actions.get(name)
    }

    pub fn allowed_subjects(&self) -> &[String] {
        &self.allow
    }

    /// 主体是否在白名单内。`*` 结尾表示前缀匹配。
    pub fn subject_allowed(&self, actor: &str) -> bool {
        self.allow.iter().any(|pat| pattern_matches(pat, actor))
    }

    /// **裁决**：这条 `act` 的信纸能不能执行。
    ///
    /// ## `capability` 字段填的是**动作名**（本批拆两层后的口径）
    ///
    /// 拆层之前，这一个名字兼任两职：既是"能被怎样对待"的能力名，又是可执行的动词。
    /// 拆层之后给它一个准头：**它是动作名**，而每条动作**必须**引用一个已声明的能力
    /// （[`Policy::load`] 逐条核过 ⇒ 动作名的声明与它引用的能力**同在 `actions` 里**）。
    ///
    /// 于是这里查两处、报两种错，**不合并**：
    /// - 动作名不在 `actions` 里 ⇒ `未在门禁策略中声明`（默认拒绝）；
    /// - 动作在、它引用的能力在 `capabilities` 里（由加载期保证）⇒ 按动作的 `reversible` 裁决。
    pub fn decide(&self, actor: &str, body: &Value) -> Decision {
        let action = match body.get("capability").and_then(Value::as_str) {
            Some(c) => c,
            None => return Decision::Reject("act 信纸缺少 capability".to_string()),
        };
        let verb = body.get("verb").and_then(Value::as_str).unwrap_or("-");

        if !self.subject_allowed(actor) {
            return Decision::Reject(format!(
                "主体 `{actor}` 不在门禁白名单内（policy.json 的 subjects.allow）"
            ));
        }

        match self.actions.get(action) {
            None => Decision::Reject(format!(
                "动作 `{action}` 未在门禁策略中声明（verb={verb}）——\
                 法律里没有的动作一律不放行（默认拒绝）"
            )),
            Some(a) if !a.reversible => {
                if self
                    .irreversible_actors
                    .iter()
                    .any(|x| pattern_matches(x, actor))
                {
                    Decision::Allow
                } else {
                    Decision::AwaitApproval(format!(
                        "动作 `{action}` **不可逆**（verb={verb}；载体清单声明的风险等级：\
                         {level}），而 `{actor}` 不在 irreversible_actors 白名单内。\n\
                         \x20 摩擦挂在**动作的不可逆等级**上（不是挂在执行者身份上）：\
                         这件动作谁来做都加摩擦，白名单只决定加完摩擦**能不能执行**。\n\
                         \x20 ⚠️ v1 **没有审批通道**（无批准命令、无批准事件）——\
                         不要等批准，它不会来。\n\
                         \x20 处置：由白名单主体（{:?}）执行该动作",
                        self.irreversible_actors,
                        level = self.level_name(a.capability.as_str())
                    ))
                }
            }
            Some(_) => Decision::Allow,
        }
    }

    /// **某个能力**声明的不可逆等级名（闸打印与流水用）。
    ///
    /// 输入取**能力名**（不是动作名）：等级来自载体执行清单，而清单是按能力名登记的。
    pub fn level_name(&self, capability: &str) -> &'static str {
        match self.caps.get(capability).and_then(|c| c.risk) {
            Some(CarrierRisk::Low) => "low",
            Some(CarrierRisk::Medium) => "medium",
            Some(CarrierRisk::High) => "high",
            // 没有执行清单 ≠ 低危：缺口如实说出来，别让它悄悄变成"低危"。
            None => "未声明（没有执行清单）",
        }
    }

    /// **一次 `act` 请求的完整裁决**：准不准 ＋ 加不加摩擦。
    ///
    /// 这是"摩擦落在动作上"的落点：`friction` 只看**动作是否可逆**，
    /// **不看请求者是谁**（看身份的是 `decision`）。
    ///
    /// 三条后果（[`Friction`] 的表）：可逆 ⇒ 免检；不可逆 + 白名单内 ⇒ 放行且事件带摩擦旗标；
    /// 不可逆 + 白名单外 ⇒ `AwaitApproval` 且流水里写明等级。
    pub fn verdict(&self, actor: &str, body: &Value) -> Verdict {
        let decision = self.decide(actor, body);
        let friction = body
            .get("capability")
            .and_then(Value::as_str)
            .and_then(|name| self.actions.get(name))
            .filter(|a| !a.reversible)
            .map(|a| Friction {
                risk: self.caps.get(&a.capability).and_then(|c| c.risk),
                mark: crate::common::event::FLAG_FRICTION,
            });
        Verdict { decision, friction }
    }

    /// 载体侧执行清单（只读）。
    pub fn carrier_manifest(&self) -> &CarrierManifest {
        &self.carrier
    }

    /// 载体清单目录（`None` = 策略同级没有 `cap.d`）。
    pub fn carrier_dir(&self) -> Option<&Path> {
        self.carrier_dir.as_deref()
    }

    /// 策略摘要（供 CLI 打印与记录归档）。
    ///
    /// **两层各自成段**（`capabilities` 与 `actions`）——摘要里也不许把两层拍平成一份。
    pub fn summary(&self) -> Value {
        let mut caps = Map::new();
        for (name, c) in &self.caps {
            caps.insert(
                name.to_string(),
                serde_json::json!({
                    // 能力层：能被怎样对待（可读／可配／可调）。
                    "kind": c.kind,
                    // 闸读得到的风险等级（`null` = 没有执行清单 ⇒ 未声明）。
                    "risk": c.risk.map(|r| match r {
                        CarrierRisk::Low => "low",
                        CarrierRisk::Medium => "medium",
                        CarrierRisk::High => "high",
                    }),
                }),
            );
        }
        let mut acts = Map::new();
        for (name, a) in &self.actions {
            acts.insert(
                name.to_string(),
                serde_json::json!({
                    "capability": a.capability,
                    "reversible": a.reversible,
                }),
            );
        }
        serde_json::json!({
            "policy": self.version,
            "path": self.path.display().to_string(),
            "capabilities": Value::Object(caps),
            "actions": Value::Object(acts),
            "subjects_allow": self.allow,
            "carrier_dir": self.carrier_dir.as_ref().map(|d| d.display().to_string()),
        })
    }
}

#[cfg(test)]
mod unit {
    use super::*;
    use serde_json::json;

    fn test_policy() -> Policy {
        let mut caps = BTreeMap::new();
        caps.insert(
            "notice.mute".to_string(),
            Capability {
                kind: "invoke".to_string(),
                risk: Some(CarrierRisk::Low),
            },
        );
        caps.insert(
            "ledger.compact".to_string(),
            Capability {
                kind: "invoke".to_string(),
                risk: Some(CarrierRisk::High),
            },
        );
        // 两层：能力在上、动作引用它。`act` 信纸的 `capability` 填的是**动作名**。
        let mut actions = BTreeMap::new();
        for (name, reversible, capability) in [
            ("notice.mute", true, "notice.mute"),
            ("ledger.compact", false, "ledger.compact"),
        ] {
            actions.insert(
                name.to_string(),
                ActionDecl {
                    capability: capability.to_string(),
                    reversible,
                },
            );
        }
        let mut writes = BTreeMap::new();
        writes.insert("world://user".to_string(), vec!["world://*".to_string()]);
        writes.insert(
            "world://agent/*".to_string(),
            vec!["world://agent/*".to_string()],
        );
        Policy {
            version: 1,
            caps,
            actions,
            allow: vec!["world://user".to_string(), "world://agent/*".to_string()],
            writes,
            irreversible_actors: vec!["world://user".to_string()],
            carrier: CarrierManifest::default(),
            carrier_dir: None,
            path: PathBuf::from("src/gate/policy.json"),
        }
    }

    #[test]
    fn declares_default_deny() {
        let p = test_policy();
        match p.decide("world://user", &json!({"capability": "nope", "verb": "do"})) {
            Decision::Reject(m) => assert!(m.contains("未在门禁策略中声明"), "{m}"),
            other => panic!("期望拒绝，实得 {other:?}"),
        }
    }

    #[test]
    fn allows_reversible_and_adds_friction_for_irreversible() {
        let p = test_policy();
        assert_eq!(
            p.decide(
                "world://user",
                &json!({"capability": "notice.mute", "verb": "do"})
            ),
            Decision::Allow
        );
        // 不可逆动作：v1 规则 = 只允许 irreversible_actors 白名单里的主体执行
        // （2026-09-26 起；此前一律 AwaitApproval，等于该能力是死号 —— 见 DEBT-07）
        assert_eq!(
            p.decide(
                "world://user",
                &json!({"capability": "ledger.compact", "verb": "do"})
            ),
            Decision::Allow,
            "白名单主体应能执行不可逆动作，否则该能力是死号"
        );
        match p.decide(
            "world://agent/1",
            &json!({"capability": "ledger.compact", "verb": "do"}),
        ) {
            Decision::AwaitApproval(m) => {
                assert!(m.contains("不可逆"), "{m}");
                assert!(
                    m.contains("没有审批通道"),
                    "拒绝理由必须明说 v1 无审批通道，别让人以为等等就能批：{m}"
                );
            }
            other => panic!("期望加摩擦，实得 {other:?}"),
        }
    }

    #[test]
    fn rejects_subject_outside_whitelist() {
        let p = test_policy();
        match p.decide(
            "world://stranger",
            &json!({"capability": "notice.mute", "verb": "do"}),
        ) {
            Decision::Reject(m) => assert!(m.contains("不在门禁白名单内"), "{m}"),
            other => panic!("期望拒绝，实得 {other:?}"),
        }
    }

    #[test]
    fn prefix_pattern_matches_all_agents() {
        let p = test_policy();
        assert!(p.subject_allowed("world://agent/1"));
        assert!(p.subject_allowed("world://agent/anything"));
        assert!(!p.subject_allowed("world://agentX"));
    }

    /// **摩擦挂在动作的不可逆等级上**，不挂在执行者身份上（书 §5.5）。
    ///
    /// 判据：同一个主体（`world://user`）对两种动作的结论——
    /// 可逆动作**不带**摩擦，不可逆动作**必带**摩擦且带上等级。
    /// 变异：若把 `verdict` 里的 `!c.reversible` 换成"看 actor 是不是白名单"，
    /// 第二条断言当场变红（白名单主体会被判"免检"）。
    #[test]
    fn friction_is_decided_by_the_action_not_the_actor() {
        let p = test_policy();
        let reversible = p.verdict(
            "world://user",
            &json!({"capability": "notice.mute", "verb": "do"}),
        );
        assert_eq!(reversible.decision, Decision::Allow);
        assert!(
            reversible.friction.is_none(),
            "可逆动作免检：不得带摩擦，实得 {:?}",
            reversible.friction
        );

        let irreversible = p.verdict(
            "world://user",
            &json!({"capability": "ledger.compact", "verb": "do"}),
        );
        assert_eq!(
            irreversible.decision,
            Decision::Allow,
            "白名单主体仍放行（预批，v1 无审批通道）"
        );
        let f = irreversible
            .friction
            .expect("不可逆动作**必加摩擦**，与请求者是谁无关");
        assert_eq!(f.flag(), "gate.friction:high", "摩擦要带上不可逆等级");
        assert_eq!(f.level_name(), "high");
    }

    /// 不可逆动作的**流水里必须读得到风险等级**（书 §5.5 第三条：闸读不到它）。
    ///
    /// 变异：把 `decide` 里 AwaitApproval 的 `level = self.level_name(c)` 去掉，
    /// 这条断言变红——"闸读得到风险等级"就没有可核的对外痕迹。
    #[test]
    fn refusal_reason_carries_the_risk_level() {
        let p = test_policy();
        match p.decide(
            "world://agent/1",
            &json!({"capability": "ledger.compact", "verb": "do"}),
        ) {
            Decision::AwaitApproval(m) => {
                assert!(m.contains("风险等级"), "流水要写清等级：{m}");
                assert!(m.contains("high"), "等级要具体到 high：{m}");
                assert!(
                    m.contains("摩擦挂在**动作的不可逆等级**上"),
                    "口径要写在流水里，否则读流水的人仍以为摩擦看身份：{m}"
                );
            }
            other => panic!("期望加摩擦，实得 {other:?}"),
        }
    }
}
