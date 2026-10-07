//! 读模型（`M03`）—— **状态的唯一来源是账本**。
//!
//! 世界的真相只有一条：**语义事件账本**。状态不是被"保存"的，而是被**算出来**的：
//!
//! ```text
//! state = fold(events[0..seq])
//! ```
//!
//! 由此推出五条硬性质（`07/4-计划/03` §七、`07/2-依据/15` §三；第 4／5 条是后来补的）：
//!
//! 1. **读模型是派生物，不是真相**。它可以随时被删掉、从账本重算，
//!    结果必须逐字节一致——这是本项目的第三条专属验收测试
//!    （"删掉读模型 → 重算一致"）。本模块在 v1 **不持久化任何东西**：
//!    没有"读模型文件"需要维护一致性，也就**不存在"读模型与账本不一致"**这种经典故障。
//! 2. **回滚 = 追加补偿事件**，绝不修改历史。折叠里**没有"改写历史"的逻辑**——
//!    补偿事件本身就是一条普通的 `change`，折叠照常前进；★**撤回**同样是**追加**
//!    （账本里多一条**撤回事实**，见 [`Retraction`]），它改的是"**将来怎么折**"
//!    ——那一条的效果**不再落账**——而**不改账本里的任何一个字节**。
//! 3. **折叠必须报错而不是猜**。序号断裂、旧值不符、未知家族——一律拒绝折叠。
//!    读模型若默默容忍坏账本，那么"账本是唯一真相"就成了一句空话。
//! 4. **缺格即报错**（`REQ-F-032`）。书第五章 5.6 表 5.2 行的通过条件逐字是
//!    「每个已声明的字段至少有一份读法可读，**缺格就报错**」，当日结果逐字是「**红**。未实现」
//!    （合订本 `:737`）。本模块补的是**读模型这一侧**：一行账本少了**已声明的必填格**
//!    ⇒ 拒绝折叠，并**点名缺的那一格**（[`DeclaredCells`] ＋ [`State::apply_declared`]）。
//!    ⚠️ 它与「未知家族」**不是一回事**：不认识的家族仍旧报 `ReadModel.UnknownKind`
//!    （那是 `REQ-F-029` 对偶的另一半），两处不许互相冒充〔本 change 的 delta `REQ-F-027`／`REQ-F-029`〕。
//! 5. ★ **撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
//!    被撤回的那一条**照样占着它那个 `seq`**（跳过它会让下一条报缺号，而"缺号即拒启"
//!    是世界的既有口径），但它的**效果**不落账——见 [`State::advance_only`] 与 [`Retraction`]。
//!
//! 关于 `before` 的核对：`change` 事件按法律**必带旧值**（回滚所需信息当场留下）。
//! 本模块因此在折叠时核对"事件声称的旧值 == 账本折叠出的当前值"——
//! 这是**读模型侧的第二道墙**：即便有人手改了账本，也会在这里被拦下。
//! 该 path **首次出现**时不核对（此前无当前值可比），此时 `before` 允许为 `null`。
//!
//! ⚠️ 快照（`M08`）在 v1 **不存在**。将来若加，它只能是**带 `base_seq` 的缓存**，
//! 且必须永远可被"从账本重算"覆盖验证——否则它就从缓存悄悄变成了第二真相。
//!
//! ## ★ 撤回与规范形式／快照的关系（**本层如实声明的边界**）
//!
//! **撤回事实不进规范形式**（[`State::to_json`] **一个字不动**：它是规范形式，状态指纹
//! 由它而来——加键会让每一处 `state=…` 变成假话）。⇒ 由它推出两条边界：
//! - 快照（`Checkpoint::capture` 存的是规范形式）**带不走撤回事实**：从快照恢复出来的
//!   `State`，[`State::retracted`] 是**空的**。规范形式本身不受影响（指纹照旧），
//!   但"哪些条被撤回过"这一格，**只有账本答得出**——要那一格就重算，不要读快照；
//! - 续算（`Checkpoint::resume_unverified`）只施加 `base_seq` **之后**的事件 ⇒
//!   若一条撤回撤的是 `base_seq` **之前**那一条，续算**做不到**（那条效果已经进了快照）。
//!   本层**不在那里悄悄放行**：`checkpoint resume` 的既有守门会拿"续算 vs 全量"逐字节比对，
//!   不等即 `ext.world.Checkpoint.ResumeMismatch` **拒用**（宁可全量重算）。

use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

/// **撤回事实的落点**：一条 `change` 事件，只要它的 `body.path` 是这个名字，它就是一条撤回事实。
///
/// ## 名字的权威在哪
///
/// **在本体**：出厂本体 `_objects.notice.fields` 与 `concepts.notice.fields`（非 `_` 键 ⇒ 进词表身份）
/// **两处同批**逐字声明 `"retract_seq": "integer"`（依据与改动面见 `docs/证据/证据-EV-009.md` 的
/// 「第 10 轮增量 · 词表身份变更」一节）。读模型把名字**编译进来**，是因为
/// `M03` 生产代码**零出边**（`WC-MODREG-001` §2；`tools/module_graph.py` 判据② 逐边核对
/// 「声明集 ≡ 真实 import 集」）⇒ 读模型**不许** `use crate::ontology_definition::…`。
/// 这与"读模型认得的那三个家族"是**同一口径**：本体加了新东西，**读法要一起加**
/// （`REQ-F-027`／`scripts/test/family_readmodel.rs::h02` ③ 钉的就是这一条）。
pub const RETRACT_PATH: &str = "retract_seq";

/// **一条撤回事实**：撤哪条 `seq` ／谁撤的（`actor`）／因为什么。
///
/// ★ **撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
///
/// ## 形态（**不新增事件家族**）
///
/// 它落在**既有** `change` 家族的一条事件上——四个格子各自有主，没有一格是新造的：
///
/// | 事实 | 落在哪 | 依据 |
/// |---|---|---|
/// | **撤哪条 `seq`** | `body.after`（`body.path = RETRACT_PATH`） | `notice.fields.retract_seq: integer`（本体逐字声明） |
/// | **谁撤的** | 信封 `actor` | 信封必填格（本体逐字声明） |
/// | **因为什么** | 信封 `trace` | 本体对它的逐字定义：「因果：引发本条的那条事件的 id」 |
///
/// ⇒ **不动法律**（不新家族、不新字段）、**不动 `to_json`**、**不动账本写入语义**。
///
/// ## 它与"补偿事件"是**两件事**（不许互相冒充）
///
/// - **补偿**（既有）：再写一条方向相反的 `change`，**效果照常落账** ⇒ 状态的当前值被改到目标值；
/// - **撤回**（本条）：撤掉**某一条**的效果，**那一条不再落账** ⇒ 当前值不是"被改成什么"，
///   而是"**从来没变过**"。⇒ 判据也不同：补偿判"值对不对"，撤回判"那一条还算不算数"。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Retraction {
    /// **被撤回的账本序号**（撤回的对象是那一条的**效果**，不是那个序号本身）。
    pub target_seq: u64,
    /// **谁撤的**（撤回事件的 `actor`）。读不到就是空串——本层**不替它编一个身份**。
    pub actor: String,
    /// **因为什么**（撤回事件的信封 `trace`＝本体逐字定义的「因果：引发本条的那条事件的 id」）。
    ///
    /// `None` ＝ 这一条撤回**没说因为什么**——**不许**拿空串或 `null` 冒充"说了"
    /// （与 `event.rs` 那条「没有因果与因果指向空是两件事」同一纪律）。
    pub because: Option<String>,
}

/// 世界状态。**只能由 [`State::apply`] / [`State::fold`] 产生**。
///
/// 字段私有：外部拿不到可改的句柄，也就不可能"绕过账本改状态"。
#[derive(Debug, Clone, Default, PartialEq)]
pub struct State {
    last_seq: u64,
    seen: u64,
    acts: u64,
    notices: u64,
    /// 主体 → 字段路径 → 当前值。用 `BTreeMap` 是为了**确定性**：
    /// 键有序 ⇒ 同样的账本必然渲染出同样的字节。（`serde_json` 默认的
    /// `Map` 也是有序的，两者共同保证折叠结果可逐字节比对。）
    objects: BTreeMap<String, BTreeMap<String, Value>>,
    /// **被撤回的账本序号 → 撤回事实**（[`State::new`] 走 `Default` ⇒ 初值即空表）。
    ///
    /// 用 `BTreeMap` 的理由与 `objects` 同：键有序 ⇒ 读数确定（"第几条被撤回"不靠遍历次序）。
    ///
    /// ⚠️ 它**不进** [`State::to_json`]（规范形式＝**世界现在什么样**；撤回事实说的是
    /// "**哪一条不算数**"，那不是世界的一格）。要读它：库侧用 [`State::retracted`]，
    /// 命令侧用 `world-core state --retracted`（**只增**的输出面）。
    retracted_seqs: BTreeMap<u64, Retraction>,
}

impl State {
    pub fn new() -> Self {
        Self::default()
    }

    /// 已折叠到的账本序号（空状态为 0）。
    pub fn last_seq(&self) -> u64 {
        self.last_seq
    }

    /// 已折叠的事件条数。
    pub fn seen(&self) -> u64 {
        self.seen
    }

    /// 已折叠的 `act` 条数（动作是事实，本身就是一等事件）。
    pub fn acts(&self) -> u64 {
        self.acts
    }

    /// 已折叠的 `notice` 条数。
    pub fn notices(&self) -> u64 {
        self.notices
    }

    /// **撤回事实**：被撤回的账本序号 → [`Retraction`]（按序号有序）。
    ///
    /// 与 [`State::last_seq`]／[`State::seen`]／[`State::acts`] **同形**：只读、不改状态、
    /// 不参与规范形式（见 [`State::to_json`] 与模块文档的"撤回与规范形式／快照的关系"）。
    pub fn retracted(&self) -> &BTreeMap<u64, Retraction> {
        &self.retracted_seqs
    }

    /// 读一个字段的当前值。
    pub fn get(&self, subject: &str, path: &str) -> Option<&Value> {
        self.objects.get(subject).and_then(|m| m.get(path))
    }

    /// **按类型的实例计数**（`类型 → 实例数`）。
    ///
    /// 为什么要有这一格（第三批的判据面）：折叠层此前**没有类型这个概念**——
    /// `objects` 以 subject **字符串**为键（`"world://notice/n-1"`），
    /// 于是"这个类型现在有几个实例"这件事在读数面上**根本问不出来**，
    /// 而"声明为单实例的类型却折出多个实例"正是要判的那一格。
    ///
    /// 口径：类型 ＝ subject `world://<首段>/<实例…>` 的**首段**（与
    /// [`crate::ontology_definition::Ontology::entity_of`] 同一口径——**一个事实只有一个权威载体**）；
    /// 裸主体（`world://<名字>`，没有实例段）**不计入任何类型**（它不是某个类型的实例引用，
    /// 与 `entity_of` 的 `None` 同源）。只有**有字段写进去**的主体才出现（空主体不占位）。
    pub fn type_counts(&self) -> BTreeMap<String, u64> {
        let mut out: BTreeMap<String, u64> = BTreeMap::new();
        for subject in self.objects.keys() {
            if let Some(t) = type_of_subject(subject) {
                *out.entry(t.to_string()).or_insert(0) += 1;
            }
        }
        out
    }

    /// 遍历全部 `(主体, 路径, 值)`。顺序**确定**（主体、路径皆为有序键），
    /// 因此同一次折叠必然给出同一个遍历序列。
    pub fn entries(&self) -> impl Iterator<Item = (&str, &str, &Value)> + '_ {
        self.objects.iter().flat_map(|(subject, paths)| {
            paths
                .iter()
                .map(move |(path, v)| (subject.as_str(), path.as_str(), v))
        })
    }

    /// 折叠一条事件。**必须按 `seq` 顺序、且从连续前缀开始**。
    ///
    /// ⚠️ **撤回事实**在这一层是**只过户、不落账**的（见 [`State::advance_only`]）：
    /// 它是一句"**哪条不算数**"，不是世界的一格。
    /// 而被**撤回**的那一条走的是另一条路——它由 [`State::fold`]／[`State::fold_declared`]
    /// **预扫之后直接判掉**：`apply` 自己看不到"将来会不会有人撤回我"。
    pub fn apply(&mut self, ev: &Value) -> Result<(), String> {
        let seq = ev.get("seq").and_then(Value::as_u64).ok_or_else(|| {
            "ext.world.ReadModel.MissingSeq: 事件缺少 seq：账本不是合法 JSON Lines".to_string()
        })?;

        self.check_next(seq)?;

        // ★ 撤回事实**本身也不落账**。认定与解析只有一处（[`retract_target_of`]）。
        if retract_target_of(ev)?.is_some() {
            self.last_seq = seq;
            return Ok(());
        }

        let kind = ev
            .get("kind")
            .and_then(Value::as_str)
            .ok_or_else(|| missing_cell_msg(seq, "envelope", "kind"))?;

        match kind {
            "change" => self.apply_change(seq, ev)?,
            "act" => self.acts += 1,
            "notice" => self.notices += 1,
            other => {
                return Err(format!(
                    "ext.world.ReadModel.UnknownKind: 未知事件家族 `{other}`（seq={seq}）：读模型**拒绝猜测**其语义\
                     ——法律与读模型必须同源"
                ))
            }
        }

        self.last_seq = seq;
        self.seen += 1;
        Ok(())
    }

    /// **过户不落账**：把账本的序号推过这一条，**不施加任何改动**。
    ///
    /// ★ **撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
    ///
    /// ## 它做什么、不做什么（逐格，可判）
    ///
    /// | 格 | [`State::apply`] | 本方法 |
    /// |---|---|---|
    /// | 连线自检（`seq` 必须接在 `last_seq` 之后） | **做** | ★**做同一道**（[`State::check_next`]，全模块唯一一处） |
    /// | `last_seq` | 推进 | 推进（**必须**：不推进则下一条报缺号） |
    /// | `objects`（字段） | 落 | **不落** |
    /// | `acts`／`notices`（事件效果） | 落 | **不落** |
    /// | `seen`（已折叠条数） | +1 | **不加**——`seen` 数的是**折叠过**的条数，而过户的那一条**没有折叠** |
    /// | 实例上限（折叠之后的读数） | 计入 | **不计入**（它没进 `objects`） |
    ///
    /// ## 为什么**不许**用裸 `continue` 代替它
    ///
    /// 被撤回的那一条**照样占着它那个 `seq`**。用 `continue` 跳过它 ⇒ `last_seq` 停在它前面
    /// ⇒ 下一条一来就报 `SeqGap`（**缺号即拒启**是世界的既有口径：
    /// `src/ledger/mod.rs` 启动时逐行校验 `seq` 从 1 起连续）。
    /// 所以"撤回"只能表现为**过户**，不能表现为"那一条不存在"。
    pub fn advance_only(&mut self, seq: u64) -> Result<(), String> {
        self.check_next(seq)?;
        self.last_seq = seq;
        Ok(())
    }

    /// **连线自检**（全模块**唯一一处**）：这一条的 `seq` 必须接在已折叠的 `last_seq` 后面。
    ///
    /// 抽成一处是刻意的：[`State::apply`] 与 [`State::advance_only`] 必须做**同一道**自检，
    /// 抄两份迟早漂移——而"缺号即拒启"正是本模块最不能漂的一条（错误文案与实现前逐字相同）。
    fn check_next(&self, seq: u64) -> Result<(), String> {
        let expected = self.last_seq + 1;
        if seq != expected {
            return Err(format!(
                "ext.world.ReadModel.SeqGap: 事件序号不连续：已折叠到 {}，期望 {expected}，实际 {seq}\
                 （读模型只折叠**连续的账本前缀**，不猜缺口）",
                self.last_seq
            ));
        }
        Ok(())
    }

    fn apply_change(&mut self, seq: u64, ev: &Value) -> Result<(), String> {
        let body = match ev.get("body") {
            Some(Value::Object(m)) => m,
            Some(_) => return Err(bad_cell_msg(seq, "body", "对象")),
            None => return Err(missing_cell_msg(seq, "envelope", "body")),
        };
        let subject = match body.get("subject") {
            Some(Value::String(s)) => s.as_str(),
            Some(_) => return Err(bad_cell_msg(seq, "body.subject", "字符串")),
            None => return Err(missing_cell_msg(seq, "body[change]", "subject")),
        };
        let path = match body.get("path") {
            Some(Value::String(s)) => s.as_str(),
            Some(_) => return Err(bad_cell_msg(seq, "body.path", "字符串")),
            None => return Err(missing_cell_msg(seq, "body[change]", "path")),
        };
        if !body.contains_key("after") {
            return Err(missing_cell_msg(seq, "body[change]", "after"));
        }
        let after = body.get("after").cloned().unwrap_or(Value::Null);

        // 第二道墙：事件声称的旧值必须等于账本折叠出的当前值。
        if let Some(current) = self.objects.get(subject).and_then(|m| m.get(path)) {
            match body.get("before") {
                Some(before) if before == current => {}
                Some(before) => {
                    return Err(format!(
                        "ext.world.ReadModel.BeforeMismatch: 旧值不符（seq={seq}，{subject}#{path}）：事件称 before={before}，\
                         但账本折叠出的当前值是 {current}。账本与事件不符——**拒绝折叠**"
                    ))
                }
                None => return Err(missing_cell_msg(seq, "body[change]", "before")),
            }
        }

        self.objects
            .entry(subject.to_string())
            .or_default()
            .insert(path.to_string(), after);
        Ok(())
    }

    /// 从**规范形式**（[`State::to_json`] 的产物）重建状态。
    ///
    /// 用途：检查点（`M08`）从缓存恢复。字段私有 ⇒ 只有本模块能构造 `State`，
    /// 于是"从快照恢复"这件事也**必须**经过这里，不能绕过。
    pub fn from_json(v: &Value) -> Result<Self, String> {
        let u64_of = |k: &str| -> Result<u64, String> {
            v.get(k)
                .and_then(Value::as_u64)
                .ok_or_else(|| format!("ext.world.ReadModel.BadState: 缺字段 `{k}`"))
        };
        let mut objects: BTreeMap<String, BTreeMap<String, Value>> = BTreeMap::new();
        if let Some(objs) = v.get("objects") {
            let objs = objs
                .as_object()
                .ok_or_else(|| "ext.world.ReadModel.BadState: objects 不是对象".to_string())?;
            for (subject, paths) in objs {
                let paths = paths.as_object().ok_or_else(|| {
                    format!("ext.world.ReadModel.BadState: objects[{subject}] 不是对象")
                })?;
                let mut m = BTreeMap::new();
                for (p, val) in paths {
                    m.insert(p.clone(), val.clone());
                }
                objects.insert(subject.clone(), m);
            }
        }
        Ok(State {
            last_seq: u64_of("last_seq")?,
            seen: u64_of("seen")?,
            acts: u64_of("acts")?,
            notices: u64_of("notices")?,
            objects,
            // ⚠️ **撤回事实不在规范形式里** ⇒ 从这里恢复出来的状态**带不回**它们
            //    （空的，不是"猜一个"）。边界与后果逐字见模块文档那一节。
            retracted_seqs: BTreeMap::new(),
        })
    }

    /// 从零折叠一串事件。
    ///
    /// ⚠️ 这是**无法律的折叠**：它只查读模型自己就要用的那几格（`seq`／`kind`／`change` 的四处）。
    /// `World::read_model`（`src/lib.rs`）今天走的正是这一条 ⇒ **已声明的必填格缺了，
    /// 在 `state --json` 上仍是静默通过**——这条缺口在 `tools/s1_sys_probe.sh` 的
    /// `TC-047` ⑨ 里早就登记着，逐字：「缺必填信封字段 actor 竟**被接受**（rc=$R）：
    /// 必填字段校验只在写入路径（本体校验）上，折叠层不校验」。
    /// 要合上它，走 [`State::fold_declared`]（带法律的那条路）。
    pub fn fold(events: &[Value]) -> Result<Self, String> {
        let mut s = State::new();
        // ★ **循环之前先预扫**：撤回事实排在它撤回的那一条**之后**，走到那一条时
        //   "它将来会不会被撤回"只有先扫一遍才知道。见 [`State::scan_retractions`]。
        s.retracted_seqs = Self::scan_retractions(events)?;
        for ev in events {
            // ★ **被撤回的那一条：过户不落账**——注意这里**不是**裸 `continue`：
            //   裸 `continue` 会让下一条报缺号，而"缺号即拒启"是世界的既有口径。
            if let Some(seq) = ev.get("seq").and_then(Value::as_u64) {
                if s.retracted_seqs.contains_key(&seq) {
                    s.advance_only(seq)?;
                    continue;
                }
            }
            s.apply(ev)?;
        }
        Ok(s)
    }

    /// **预扫撤回事实**（[`State::fold`]／[`State::fold_declared`] 在循环**之前**各调一次）。
    ///
    /// ## 为什么必须预扫
    ///
    /// 账本只追加 ⇒ 撤回事实按 `seq` 排在它撤回的那一条**之后**；而折叠是**向前**走的
    /// ⇒ 走到被撤回的那一条时，"它将来会不会被撤回"这件事，**只有先扫一遍才知道**。
    /// 收齐之后，循环里对它走 [`State::advance_only`]（过户不落账）。
    ///
    /// ## 四条拒（都点名；都是"不许猜"）
    ///
    /// | 情形 | 错误码 | 为什么必须拒 |
    /// |---|---|---|
    /// | `body.after` 不是正整数 | `RetractMalformed`（在 [`retract_target_of`]） | 一条打错字的撤回若被静默忽略，"没撤回"与"撤回了"在读数上一样、在结论上相反 |
    /// | 撤回一条账本里**没有**的 `seq` | `RetractTargetUnknown` | 撤一条不存在的记录不是"撤回"，是一句不成立的声明 |
    /// | 同一条 `seq` 被撤回**两次** | `RetractAlreadyRetracted` | 撤回若可叠加，它就从一次断言变成可以反复拨的开关 |
    /// | 撤回的是一条**撤回事实**本身 | `RetractTargetNotAnEffect` | 撤回的对象只有"**效果**"；撤回事实不是效果 ⇒ 否则它是一个静默的空操作 |
    ///
    /// ⚠️ 这四条**只在账本里真出现撤回事实时**才可能触发 ⇒ 对不含撤回事实的既有账本，
    /// 本函数恒为 `Ok(空表)`、行为与引入它之前**逐字节相同**。
    fn scan_retractions(events: &[Value]) -> Result<BTreeMap<u64, Retraction>, String> {
        // `seq → 事件`：判"撤的那条在不在"与"它是不是一条撤回事实"都要用它。
        let by_seq: BTreeMap<u64, &Value> = events
            .iter()
            .filter_map(|e| e.get("seq").and_then(Value::as_u64).map(|s| (s, e)))
            .collect();
        let mut facts: BTreeMap<u64, Retraction> = BTreeMap::new();
        // 被撤回的 seq → 是**哪一条**（撤回事件的 seq）撤的：只为把"撤了两次"这句话说清楚。
        let mut retracted_at: BTreeMap<u64, u64> = BTreeMap::new();
        for ev in events {
            let Some(target) = retract_target_of(ev)? else {
                continue;
            };
            let at = ev.get("seq").and_then(Value::as_u64).unwrap_or(0);
            let Some(target_ev) = by_seq.get(&target) else {
                return Err(format!(
                    "ext.world.ReadModel.RetractTargetUnknown: 第 {at} 条是撤回事实，它撤的是 seq={target}，\
                     但账本里**没有这一条**（账本实有 {} 条）——撤回的对象必须是账本里真有的那一条；\
                     撤一条不存在的记录不是「撤回」，是一句不成立的声明",
                    by_seq.len()
                ));
            };
            if retract_target_of(target_ev)?.is_some() {
                return Err(format!(
                    "ext.world.ReadModel.RetractTargetNotAnEffect: 第 {at} 条是撤回事实，它撤的是 seq={target}，\
                     而那一条**本身是一条撤回事实**——撤回的对象只有「效果」，撤回事实不是效果。\
                     （撤掉一句「哪条不算数」是什么意思？本层不猜，故拒。）"
                ));
            }
            if let Some(prev) = retracted_at.get(&target) {
                return Err(format!(
                    "ext.world.ReadModel.RetractAlreadyRetracted: seq={target} 被撤回了**两次**\
                     （第 {prev} 条撤过一次，第 {at} 条又撤一次）——一条记录只能被撤回一次；\
                     若撤回可叠加，它就从一次断言变成了一个可以反复拨的开关"
                ));
            }
            retracted_at.insert(target, at);
            facts.insert(
                target,
                Retraction {
                    target_seq: target,
                    actor: ev
                        .get("actor")
                        .and_then(Value::as_str)
                        .unwrap_or("")
                        .to_string(),
                    because: ev.get("trace").and_then(Value::as_str).map(str::to_string),
                },
            );
        }
        Ok(facts)
    }

    /// **带法律的折叠**（`REQ-F-032`）：先核"已声明的必填格"（缺格即报错），再折叠。
    ///
    /// ## 这条判据管什么（逐字对书）
    ///
    /// 书第五章 5.6 表 5.2 行（合订本 `:737`）逐字：
    /// 「读的那一份每个格子都有人读得到 ｜ 每个已声明的字段至少有一份读法可读，缺格就报错
    /// ｜ 缺格即报错 ｜ **红**。未实现」。本方法把"缺格就报错"这一格补成**可执行的**：
    /// 一行账本少了[`DeclaredCells`] 里**已声明的必填格** ⇒ 返回
    /// `ext.world.ReadModel.MissingCell`，并**点名缺的那一格**（"错误可读"不是形容词：
    /// 错误里必须能读出是**哪一层**的**哪一格**，以及该层该有哪些格）。
    ///
    /// ## 与"未知家族"的分工（**不许互相冒充**）
    ///
    /// | 情形 | 判据 | 为什么不能混 |
    /// |---|---|---|
    /// | `kind` 不认识 | `ext.world.ReadModel.UnknownKind`（在 [`State::apply`] 里） | 那是**语义不认识** ⇒ 拒（`REQ-F-029` 对偶的另一半） |
    /// | `kind` 认得、但这一行少了已声明的必填格 | `ext.world.ReadModel.MissingCell`（在本方法） | 那是**该有的格没读到** ⇒ 拒；它的家族是**认得的** |
    ///
    /// 故 [`DeclaredCells::missing_cell`] 对**不认识的家族一律不看**：
    /// 让拒它的理由留在"家族不认识"那一条上，别把病因说错。
    ///
    /// ## 本层**不判**的（如实声明边界，不读作"已完备"）
    ///
    /// - **可选格**（`to`／`trace`／`params`／`payload`）不进 [`DeclaredCells`]：
    ///   本体说它们可选，"没写"是这份法律允许的形态，不是缺格；
    /// - **`concepts` 的字段**（`notice.muted`/`job.status`）归**写入侧**判
    ///   （[`crate::ontology_definition::Ontology::check_concepts`]），读模型侧不重复判；
    /// - 读模型**不渲染**信封的 `id`／`at`／`actor`／`world`／`flags`：它们现在**被读**
    ///   （缺了即拒），但**不进入状态**（`state --json` 里读不到它们）⇒ 书那句
    ///   「每个已声明的字段至少有一份读法可读」在**必填格**这一半成立，另一半仍待补。
    pub fn apply_declared(&mut self, cells: &DeclaredCells, ev: &Value) -> Result<(), String> {
        // **空表不许上电**：没有清单 ⇒ 这条判据无从成立。若在这里默默放行，
        // "一个格都没查"与"每个格都查过了"在**读数上一样**、在**结论上相反**——
        // 那正是本项目最贵的一类错（把没做读成做到了）。与门禁那条「空策略拒绝启动」同一纪律。
        if cells.is_empty() {
            return Err(
                "ext.world.ReadModel.NoDeclaredCells: 没有可比对的**已声明格清单**（空表）——\
                 缺格判据无从成立，故拒绝折叠，而不是默默放行。\n\
                 \x20 处置：把法律以数据递进来（`DeclaredCells::new(ont.envelope_required(), ont.family_required())`）"
                    .to_string(),
            );
        }
        if let Some(m) = cells.missing_cell(ev) {
            return Err(m.to_string());
        }
        self.apply(ev)
    }

    /// 从零折叠一串事件（**带法律**；缺格即报错 ＋ **按类型的实例上限**）。逐条等价于 [`State::apply_declared`]。
    ///
    /// ## 折叠**之后**还要问一遍：按类型的实例计数过没过声明上限
    ///
    /// 为什么要在**折叠之后**（而不是逐条写入时）：实例计数是**折叠的产物**
    /// （`objects` 的键），逐条时读到的是"到目前为止"的部分计数——一条回滚／补偿
    /// 可能把计数降回去。判据落在**最终状态**上，读的才是"这个世界现在有几个这类实例"。
    ///
    /// 口径：`instance_limits` 里的每一条都要满足 `实际实例数 ≤ 上限`；
    /// **没声明的类型不判**（法律没写，本层不替它发明上限）。
    pub fn fold_declared(cells: &DeclaredCells, events: &[Value]) -> Result<Self, String> {
        let mut s = State::new();
        // ★ 与 [`State::fold`] **同一处口径**：循环之前预扫撤回事实（理由逐字见那里）。
        s.retracted_seqs = Self::scan_retractions(events)?;
        for ev in events {
            // ★ 被撤回的那一条：**过户不落账**（不是裸 `continue`，理由见 [`State::advance_only`]）。
            //
            // ⚠️ 边界（如实声明）：被撤回的那一条**不再过缺格判据**——它根本不落账，
            //    也就不构成"某个已声明的格被读到／没被读到"。缺格判的是**折叠进去的那些行**。
            if let Some(seq) = ev.get("seq").and_then(Value::as_u64) {
                if s.retracted_seqs.contains_key(&seq) {
                    s.advance_only(seq)?;
                    continue;
                }
            }
            s.apply_declared(cells, ev)?;
        }
        for (entity, limit) in &cells.instance_limits {
            let n = s.type_counts().get(entity).copied().unwrap_or(0);
            if n > *limit {
                return Err(format!(
                    "ext.world.ReadModel.TooManyInstances: 类型 `{entity}` 声明为至多 {limit} 个实例\
                     （`instance_mode: \"single\"` 即上限 1），折叠后实得 **{n}** 个——**声明为单实例的类型折出了多个实例**。\n\
                     \x20 实例名（`world://{entity}/<实例…>`）：{}\n\
                     \x20 处置：把多余的实例改成别的类型／别的名字，或改本体把该类型的上限写成 `many`\
                     （改法律＝走评审）——**不许**让声明与事实各说各话",
                    s.objects
                        .keys()
                        .filter(|k| type_of_subject(k) == Some(entity.as_str()))
                        .cloned()
                        .collect::<Vec<_>>()
                        .join(", ")
                ));
            }
        }
        // ★ **每个实例必须指回定义面**（书 §5.3 的**读侧**那一半；写侧的执行体是
        //   `Ontology::check_concepts` 的 `UndeclaredEntity`）。
        //
        //   为什么必须补这一半（实测，不是推的）：**同一本账，写侧拒的、读侧收** ——
        //   拿真二进制跑过两遍：`append` 一个未声明实体的 `change` ⇒ `rc=2`、账本 0 字节；
        //   把**同一行**直接放进账本（＝恢复／迁移／手工修复那三条路）再 `state --json`
        //   ⇒ `rc=0`，那个主体**就在状态里**。那是"同一个事实两个答案"。
        //
        //   ⚠️ `None` ⇒ 这一半**没接** ⇒ 不判（见字段文档：只有装上这一半的调用方才会被判）。
        if let Some(declared) = &cells.declared_entities {
            // **空表不许上电**（与 `NoDeclaredCells` 同一纪律）：法律里一个对象类型都没有
            // ⇒ 这条判据无从成立。"一个实体都没查"与"每个实体都查过了"在读数上一样、
            // 在结论上相反 ⇒ 拒，不默默放行。
            if declared.is_empty() {
                return Err(
                    "ext.world.ReadModel.NoDeclaredEntities: 递进来的**已声明实体集**是空的\
                     ——没有可比对的实体清单，故拒绝折叠，而不是默默放行。\n\
                     \x20 处置：把法律以数据递进来（`DeclaredCells::with_declared_entities(ont.known_entities(), ont.nested_types())`）"
                        .to_string(),
                );
            }
            // 逐主体判（`objects` 的键有序 ⇒ 报哪一条是确定的）。**射程**（不许读成更宽）：
            //   · 只判**有字段写进去**的主体（空主体不占位）；
            //   · **裸主体不判**（`world://<名字>` 不是实例引用，见已登记缺口）；
            //   · **不判身份**（`actor`／`to`）——它们不是对象实例；
            //   · **不判**实例名的唯一性（那是另一条，登记在 `_pending_tables`）。
            for subject in s.objects.keys() {
                let Some(t) = instance_type_of(subject, &cells.nested_types) else {
                    continue;
                };
                if !declared.contains(t) {
                    return Err(format!(
                        "ext.world.ReadModel.EntityNotDeclared: 主体 `{subject}` 的**类型段** `{t}` \
                         未在出厂本体里声明（`_objects`）——**每个实例必须指回定义面**。\n\
                         \x20 写侧会拒这一条（`ext.world.Ontology.UndeclaredEntity`），读侧不许把它折进状态：\
                         **同一本账、同一件事，读写两侧必须一个答案**。\n\
                         \x20 已声明的类型：{}\n\
                         \x20 处置：把该主体改成已声明类型的实例，或先在 `_objects` 里声明它（改法律＝走评审）\
                         ——**不许**让读法比写法宽",
                        declared.iter().cloned().collect::<Vec<_>>().join(", ")
                    ));
                }
            }
        }
        Ok(s)
    }

    /// **规范形式**（canonical form）：键有序，可直接逐字节比对。
    pub fn to_json(&self) -> Value {
        let mut objects = Map::new();
        for (subject, paths) in &self.objects {
            let mut m = Map::new();
            for (path, v) in paths {
                m.insert(path.clone(), v.clone());
            }
            objects.insert(subject.clone(), Value::Object(m));
        }
        json!({
            "last_seq": self.last_seq,
            "seen": self.seen,
            "acts": self.acts,
            "notices": self.notices,
            "objects": Value::Object(objects),
        })
    }

    /// 读模型的**指纹**。
    ///
    /// ⚠️ **非加密用途**：只用 FNV-1a（不引入依赖）。它回答的唯一问题是
    /// "两次折叠是不是同一个结果"，用于第三条验收测试与将来的"同源"核对。
    /// **不得**用它做安全判断。
    pub fn digest(&self) -> String {
        const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
        const PRIME: u64 = 0x0000_0100_0000_01b3;
        let mut h = OFFSET;
        for b in self.to_json().to_string().as_bytes() {
            h ^= u64::from(*b);
            h = h.wrapping_mul(PRIME);
        }
        format!("fnv1a64:{h:016x}")
    }
}

/// **这一条事件是不是撤回事实？** 是 ⇒ `Ok(Some(被撤回的 seq))`；不是 ⇒ `Ok(None)`。
///
/// ## 认定口径（**只有这一处**）
///
/// `kind == "change"` 且 `body.path == RETRACT_PATH`；`body.after` 就是被撤回的那个 `seq`。
/// [`State::apply`] 与 [`State::scan_retractions`] **共用**它——两处若各写一份，
/// "什么算撤回"迟早变成两种说法。
///
/// ## 三处**刻意返回 `Ok(None)`**（判了就会把病因说错）
///
/// - **不是 `change` 家族** ⇒ 不是撤回事实（撤回事实落在 `change` 上，见 [`Retraction`]）；
/// - **没有 `body`／`body` 不是对象／没有 `path`** ⇒ 不是：那是**形状**问题，
///   由 [`State::apply`] 报它自己那一族（`BadCell`／`MissingCell`），本函数**不抢**；
/// - **`path` 是别的字段** ⇒ 不是。
///
/// ## 一处**必须报错**
///
/// **`path` 就是 `RETRACT_PATH`，但 `after` 不是正整数**（缺失、`null`、0、字符串、小数）
/// ⇒ `ext.world.ReadModel.RetractMalformed`。**不许**降级成"那就当它不是撤回事实"：
/// 一条打错字的撤回若被静默忽略，世界会**照旧折叠**、而那条被指的记录**照旧生效**——
/// "没撤回"与"撤回了"在读数上一样、在结论上相反（本项目最贵的一类错）。
/// `after = 0` 也算坏：账本的 `seq` **从 1 起**（`src/ledger/mod.rs` 启动即逐行校验）。
pub fn retract_target_of(ev: &Value) -> Result<Option<u64>, String> {
    if ev.get("kind").and_then(Value::as_str) != Some("change") {
        return Ok(None);
    }
    let Some(body) = ev.get("body").and_then(Value::as_object) else {
        return Ok(None);
    };
    if body.get("path").and_then(Value::as_str) != Some(RETRACT_PATH) {
        return Ok(None);
    }
    match body.get("after").and_then(Value::as_u64) {
        Some(t) if t > 0 => Ok(Some(t)),
        _ => Err(format!(
            "ext.world.ReadModel.RetractMalformed: seq={} 声称是一次撤回（`path={RETRACT_PATH}`），\
             但 `after` 不是正整数（实得 {}）——撤回必须说清**撤哪一条**；说不清就拒，不猜。\n\
             \x20 口径：`after` ＝ 被撤回的那条事件的 `seq`（账本的 `seq` 从 1 起）",
            ev.get("seq").and_then(Value::as_u64).unwrap_or(0),
            body.get("after").cloned().unwrap_or(Value::Null)
        )),
    }
}

/// **subject 的类型段**：`world://<类型>/<实例…>` ⇒ `Some("<类型>")`；裸主体 ⇒ `None`。
///
/// 与 [`crate::ontology_definition::Ontology::entity_of`] **同一口径**（本模块生产代码零出边 ⇒
/// 不 `use` 那边；口径一致这件事由两侧各自的用例钉住，不由"共用一行代码"钉住）。
pub fn type_of_subject(subject: &str) -> Option<&str> {
    let rest = subject.strip_prefix("world://")?;
    let (entity, id) = rest.split_once('/')?;
    if entity.is_empty() || id.is_empty() {
        None
    } else {
        Some(entity)
    }
}

/// **主体的"类型段"，且认得内嵌形态**：两段 ⇒ 第 1 段；四段内嵌 ⇒ 第 3 段；其余 ⇒ `None`。
///
/// | 输入 | 输出 | 为什么 |
/// |---|---|---|
/// | `world://s`（裸主体） | `None` | **不是实例引用**（与 `entity_of` 的 `None` 同源） |
/// | `world://notice/n-1` | `Some("notice")` | 两段：类型 ＝ 第 1 段 |
/// | `world://job/j-1/notice/n-1` | `Some("notice")`（当 `notice` 的 `part_of` 逐字是 `job`） | **内嵌四段**：类型 ＝ **第 3 段** |
/// | `world://a/b/c` | `Some("a")` | 三段**不是**内嵌形态；首段永远是类型（与 `entity_of` 同口径） |
/// | `world://a//c`（空段） | `None` | 形状坏 ⇒ 本判据不抢（`apply` 那一族会报） |
///
/// 与 [`crate::ontology_definition::Ontology::entity_of`]／`instance_type` **同一口径**（本模块生产代码零出边
/// ⇒ 不 `use` 那边；一致性由两侧各自的用例钉住）。
fn instance_type_of<'a>(subject: &'a str, nested: &'a BTreeMap<String, String>) -> Option<&'a str> {
    let rest = subject.strip_prefix("world://")?;
    let segs: Vec<&str> = rest.split('/').collect();
    if segs.iter().any(|s| s.is_empty()) {
        return None;
    }
    if segs.len() == 4 && nested.get(segs[2]).map(String::as_str) == Some(segs[0]) {
        return Some(segs[2]);
    }
    if segs.len() >= 2 {
        return Some(segs[0]);
    }
    None
}

/// **读模型侧的"已声明格"清单**（`REQ-F-032` 判据①：「逐格可枚举」）。
///
/// 它只装**必填**格，且只装本体逐字声明的那两处：
/// `envelope.required`（出厂本体 8 项）与 `families.<家族>.required`（出厂本体 4／3／2）。
/// 可选格（`to`／`trace`／`params`／`payload`）**不进这张表**——本体说它们可选，
/// "没写"是这份法律允许的形态，不是缺格（理由见 [`State::apply_declared`] 的边界一节）。
///
/// ## 为什么它是**数据**，而不是一个"法律"类型（这一条是刻意的）
///
/// 读模型**不许**在生产代码里 `use crate::ontology_definition::…`：`WC-MODREG-001` §2 给 `M03` 的
/// 依赖列逐字是「**无**（生产代码零出边）」，而机核层 `tools/module_graph.py` 判据②
/// 逐边核对「声明集 ≡ 真实 import 集」——读模型加一条生产边就会让它变红。
/// 故法律以**数据**递进来，依赖方向留在**装配处**（`M04` 同时依赖 `M01` 与 `M03`）：
/// 谁递 = `World::read_model` 的调用点；数据从 [`crate::ontology_definition::Ontology`] 取
/// （`envelope_required`／`family_required`），**同一份出厂本体** ⇒ 同源。
///
/// ⚠️ 递进来的若是空表（[`DeclaredCells::is_empty`]），[`State::apply_declared`] **拒绝折叠**：
/// 没有清单＝这条判据无从成立，"一个格都没查"不许被读成"检查通过"
/// （与门禁那条「空策略拒绝启动」同一纪律）。
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DeclaredCells {
    envelope_required: Vec<String>,
    family_required: BTreeMap<String, Vec<String>>,
    /// **按类型的实例上限**（`类型 → 上限`）。空表 ＝ 法律**没声明**任何上限
    /// ⇒ 本层不判（**这不等于"实例可以无限"**：它等于"这件事法律没写"，
    /// 属于 `_pending_tables` 里如实登记的缺口，不属本层的判据面）。
    instance_limits: BTreeMap<String, u64>,
    /// **已声明的实体集**（对象类型名；装配处 `M04` 从本体取）。
    ///
    /// ★ 为什么是 `Option` 而不是"空表即不判"：**"这一半没接进来"与"法律里一个类型都没有"
    /// 是两件事** —— 前者是这一层没接上线（调用方没递），后者是法律本身空。
    /// 混成一个，就把"**没接**"读成了"**没问题**"（本项目最贵的那类错）。
    /// - `None` ⇒ 这一半**没接** ⇒ 本层**不判**（既有调用点直接 `DeclaredCells::new` 的都在这一档）；
    /// - `Some(空集)` ⇒ 法律里**一个对象类型都没有** ⇒ [`State::fold_declared`] **拒绝折叠**（G1 形态）。
    declared_entities: Option<BTreeSet<String>>,
    /// **内嵌类型 → 父类型**（`_objects.<类型>.part_of`；装配处 `M04` 给）。
    ///
    /// 只在判"主体属于哪个类型"时用：四段形态 `world://<父>/<父实例>/<内嵌类型>/<内嵌实例>`
    /// 的类型是**第 3 段**（且第 3 段必须正是按 `part_of` 声明的那个内嵌类型）。
    nested_types: BTreeMap<String, String>,
}

impl DeclaredCells {
    /// 用**纯数据**装配（调用方从本体取；见类型文档的"为什么是数据"）。
    pub fn new(
        envelope_required: Vec<String>,
        family_required: BTreeMap<String, Vec<String>>,
    ) -> Self {
        Self {
            envelope_required,
            family_required,
            instance_limits: BTreeMap::new(),
            declared_entities: None,
            nested_types: BTreeMap::new(),
        }
    }

    /// 追加**按类型的实例上限**（`_objects.<类型>.instance_mode` 派生；装配处 `M04` 给）。
    pub fn with_instance_limits(mut self, limits: BTreeMap<String, u64>) -> Self {
        self.instance_limits = limits;
        self
    }

    /// 追加**已声明的实体集** ＋ **内嵌标记**（装配处 `M04` 给；同 [`Self::with_instance_limits`] 的体例）。
    ///
    /// ★ **调用它就是"把这一半接上了"**：此后 [`State::fold_declared`] 会判
    /// "**每个实例必须指回定义面**"（书 §5.3 的读侧那一半）。**不调用＝这一半没接**，
    /// 且"没接"这一点由 [`DeclaredCells::declared_entities`] 的 `None` **显式**表达，不靠空表冒充。
    pub fn with_declared_entities(
        mut self,
        entities: BTreeSet<String>,
        nested_types: BTreeMap<String, String>,
    ) -> Self {
        self.declared_entities = Some(entities);
        self.nested_types = nested_types;
        self
    }

    /// 已声明的实体集（`None` ＝ 这一半**没接**，见字段文档）。
    pub fn declared_entities(&self) -> Option<&BTreeSet<String>> {
        self.declared_entities.as_ref()
    }

    /// 声明过实例上限的类型（`None` ＝ 这一类型没声明上限）。
    pub fn instance_limit(&self, entity: &str) -> Option<u64> {
        self.instance_limits.get(entity).copied()
    }

    /// 一个格都没有 ⇒ 本层无从判（**不许**读成"检查通过"）。
    pub fn is_empty(&self) -> bool {
        self.envelope_required.is_empty() && self.family_required.is_empty()
    }

    /// 信封已声明的必填格（原顺序）。
    pub fn envelope_required(&self) -> &[String] {
        &self.envelope_required
    }

    /// 某家族已声明的必填格（`None` ＝ 法律里没有这个家族）。
    pub fn family_required(&self, kind: &str) -> Option<&[String]> {
        self.family_required.get(kind).map(Vec::as_slice)
    }

    /// **这一行缺了哪一格？** `None` ＝ 已声明的必填格齐备。
    ///
    /// 三处**刻意不判**（判了就会把病因说错）：
    /// - **不认识的家族** ⇒ 一律返回 `None`：拒它的判据是
    ///   [`State::apply`] 的 `UnknownKind`（`REQ-F-029` 对偶的另一半），不是"缺格"；
    /// - **非对象的事件**、**非对象的 `body`** ⇒ 返回 `None`：那是**形状**问题，
    ///   由 [`State::apply`] 报（`NotAnObject` 那一族的语义），缺格判据不抢它的错；
    /// - **可选格**：它们根本不在表里（见类型文档）。
    pub fn missing_cell(&self, ev: &Value) -> Option<MissingCell> {
        let obj = ev.as_object()?;
        let seq = obj.get("seq").and_then(Value::as_u64);
        for f in &self.envelope_required {
            if !obj.contains_key(f) {
                return Some(MissingCell {
                    at: "envelope".to_string(),
                    field: f.clone(),
                    declared: self.envelope_required.join(", "),
                    seq,
                });
            }
        }
        let kind = obj.get("kind").and_then(Value::as_str).unwrap_or("");
        let req = self.family_required.get(kind)?;
        // 信纸不是对象 ⇒ 形状问题，交给 `apply`（见上文"三处刻意不判"）。
        let body = obj.get("body").and_then(Value::as_object)?;
        for f in req {
            if !body.contains_key(f) {
                return Some(MissingCell {
                    at: format!("body[{kind}]"),
                    field: f.clone(),
                    declared: req.join(", "),
                    seq,
                });
            }
        }
        None
    }
}

/// 读模型侧的**缺格**（`REQ-F-032`）：一格"该在而不在"。
///
/// 为什么不复用 `Option<&Value>` 的"没读到就是 `None`"：那正是**静默通过**的形状。
/// 缺格是一个**有名字的事实**，它必须能被打印、被点名、被断言——
/// 否则"缺格即报错"只是一句口号（书第五章 5.6 表 5.2 行判的就是这一格）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MissingCell {
    /// 缺在哪一层：`envelope`，或 `body[<家族>]`。
    pub at: String,
    /// 缺的那一格的名字（**错误可读**的判据就在这个字段上：不许只说"有缺格"）。
    pub field: String,
    /// 这一层**已声明的必填格**（逗号分隔）——报错要让人当场知道"该有哪些"，
    /// 否则这条错误只说了"不行"、没说"怎么办"（与 `ontology.rs` 的 `UndeclaredEntity` 同一体例）。
    pub declared: String,
    /// 这一行的 `seq`（读不到就是 `None`——那本身也是一种缺格）。
    pub seq: Option<u64>,
}

impl fmt::Display for MissingCell {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let seq = match self.seq {
            Some(s) => s.to_string(),
            None => "?".to_string(),
        };
        write!(
            f,
            "ext.world.ReadModel.MissingCell: 缺格：{} 少了**已声明的必填格** `{}`（seq={seq}）——\
             读模型**不猜**\"没有就是空\"：已声明的格读不到，就拒绝折叠。\n\
             \x20 该层已声明的必填格：{}\n\
             \x20 处置：把这一格补进那一行再读；若它本就该是可选格，改的是**本体**（改法律＝走评审）",
            self.at, self.field, self.declared
        )
    }
}

/// **无法律折叠**那条路上的缺格文案（[`State::apply`]／[`State::apply_change`] 用）。
///
/// 与 [`MissingCell`] 同一个错误码（`ext.world.ReadModel.MissingCell`）——"缺格"这件事
/// 全项目一种说法；差别只在**能不能列出"该层已声明的必填格"**：无法律时列不出来，
/// 故这里如实写明"只查读模型自己要用的那几格"，不假装手里有一份法律。
fn missing_cell_msg(seq: u64, at: &str, field: &str) -> String {
    format!(
        "ext.world.ReadModel.MissingCell: 缺格：{at} 少了 `{field}`（seq={seq}）\
         ——（无法律折叠：读模型只查它自己要用的那几格；\"该层已声明的必填格\"要由带法律的那条路给出，\
         见 `State::apply_declared`）"
    )
}

/// 「在，但不是那个形状」——**与"缺格"分开**（`BadCell` ≠ `MissingCell`）。
///
/// 为什么抽成函数而不是内联 `format!`：那两处的文案里有**跨行的字符串续行**，其缩进属于字符串内容、
/// 会参与 rustfmt 的行长计算 ⇒ 内联时 **rustfmt 的结论会来回翻**（2026-09-28 实测：先要块形式、
/// 改成块形式后又要回非块形式，`cargo fmt --all -- --check` 永远差 1 处）。抽出来结构就定了。
fn bad_cell_msg(seq: u64, what: &str, want: &str) -> String {
    format!(
        "ext.world.ReadModel.BadCell: change 事件 seq={seq} 的 {what} **不是{want}**\
         ——它不是缺格，是形状不对（读模型不猜、也不修补）"
    )
}

#[cfg(test)]
mod unit {
    use super::*;
    use crate::common::event;

    fn change(seq: u64, subject: &str, path: &str, before: Value, after: Value) -> Value {
        event::new_event(
            seq,
            "change",
            "world://test",
            event::change_body(subject, path, before, after),
        )
    }

    #[test]
    fn folds_contiguous_prefix_and_applies_last_write() {
        let evs = vec![
            change(1, "world://a", "n", json!(1), json!(2)),
            change(2, "world://a", "n", json!(2), json!(3)),
            event::new_event(
                3,
                "notice",
                "world://test",
                event::notice_body("muted", "world://a", json!({})),
            ),
        ];
        let s = State::fold(&evs).unwrap();
        assert_eq!(s.last_seq(), 3);
        assert_eq!(s.seen(), 3);
        assert_eq!(s.notices(), 1);
        assert_eq!(s.get("world://a", "n"), Some(&json!(3)));
    }

    #[test]
    fn refuses_seq_gap() {
        let evs = vec![change(2, "world://a", "n", json!(null), json!(1))];
        assert!(State::fold(&evs).unwrap_err().contains("不连续"));
    }

    #[test]
    fn refuses_lying_before() {
        let evs = vec![
            change(1, "world://a", "n", json!(1), json!(2)),
            change(2, "world://a", "n", json!(99), json!(3)), // 谎称旧值是 99
        ];
        assert!(State::fold(&evs).unwrap_err().contains("旧值不符"));
    }

    #[test]
    fn refuses_unknown_family() {
        let evs = vec![event::new_event(1, "guess", "world://test", json!({}))];
        assert!(State::fold(&evs).unwrap_err().contains("未知事件家族"));
    }
}
