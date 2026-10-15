//! 面⑤：**查询** —— 按条件找、排序、取前 N。
//!
//! 参考 Palantir：engine/query_engine.py 的 filter／navigate／order_by／take／all／first／count。
//!
//! ★ 干活口径另学上游那套查询求值（只学怎么干活；名字／类型全是我们的）：
//! ① **先枚举候选、再逐条求值**（它先向枚举面要一批 id，再经权威读路径逐条求值）；
//! ② 求值器是**闭词汇**的：一条判据 ＝（哪一格，要等于什么）；多条判据是**与**；
//! ③ **缺席即假**：这一格没有值 ⇒ 这条判据落空（★ 不是拿空串去比）；
//! ④ 命中按**确定性次序**给（它按 id 升序）⇒ 我们：无 order_by 时按**键升序**；
//! ⑤ 排序**之后**才取前 N（它 take 在 order_by 之后）。
//!
//! ★ 今天本面的谓词词汇**只有「某一格 ＝ 某个值」一种**（可查的格＝信纸上的任意字符串格）；
//!   它那套多出来的几样（范围／集合／模糊）今天**没有落点**，如实登记。

use crate::core::types::{Admit, Registration, Who};
use crate::engine::ledger::Ledger;
use crate::engine::store::Store;
use crate::governance::Ceiling;

/// 一条判据：**某一格 ＝ 某个值**（本面今天的谓词词汇只此一种）。
#[derive(Debug, Clone)]
struct Wanted {
    /// 哪一格。
    field: String,
    /// 要等于的值。
    value: String,
}

/// 求值那一刻，从现状里取出来的「这一格是什么」。
#[derive(Debug, Clone, Copy)]
enum Cell<'a> {
    /// 这一格有值。
    Text(&'a str),
    /// 这一格缺席。
    Absent,
}

impl<'a> Cell<'a> {
    /// 从一条现状里取一格。
    fn of(reg: &'a Registration, field: &str) -> Self {
        match reg.get_str(field) {
            Some(text) => Self::Text(text),
            None => Self::Absent,
        }
    }

    /// 这一格满足「＝ 某个值」吗 —— ★ **缺席即假**。
    fn matches(&self, want: &str) -> bool {
        match self {
            Self::Text(text) => *text == want,
            Self::Absent => false,
        }
    }
}

/// 一次查询（链式；最后 all／first／count／run 取结果）。
#[derive(Debug)]
pub struct Query<'a> {
    store: &'a Store,
    kind: Option<String>,
    wanted: Vec<Wanted>,
    order_field: Option<String>,
    take: Option<usize>,
    /// ★ H08：这一查看得见的最高一级（**只能由治理面铸**，见 `Ceiling`）。
    ceiling: Option<Ceiling>,
}

/// ★ 一次查询的**结果**（H08）：命中的那些 ＋ **被天花板挡掉几条**。
///
/// ★ 「只报计数」是照它那句 `no object IDs leaked, just a count` 落下来的：
/// 被挡掉的**一个 id 都不带出来**。
#[derive(Debug)]
pub struct QueryResult<'a> {
    /// 命中（已过天花板；次序与 `all` 同）。
    pub hits: Vec<(&'a str, &'a Registration)>,
    /// 被天花板挡掉的**条数**（★ 不带 id）。
    pub suppressed: usize,
}

impl<'a> QueryResult<'a> {
    /// ★ H08 机制 4：**每次过滤记一笔** —— 族 `notice`／`what=marking.filtered`，
    /// params `{suppressed}`（★ **不带 id**；来源1-①.3 第 4 条逐字）。
    ///
    /// ★ 没挡掉任何一条 ⇒ **不记账**（账上不落空笔）。
    pub fn record(&self, ledger: &mut Ledger, who: &Who) -> Admit<()> {
        if self.suppressed == 0 {
            return Ok(());
        }
        let mut params = serde_json::Map::new();
        params.insert("suppressed".to_string(), serde_json::json!(self.suppressed));
        ledger
            .append(who, "notice", "marking.filtered", params)
            .map(|_| ())
    }
}

impl<'a> Query<'a> {
    /// 起一个查询。
    #[must_use]
    pub fn new(store: &'a Store) -> Self {
        Self {
            store,
            kind: None,
            wanted: Vec::new(),
            order_field: None,
            take: None,
            ceiling: None,
        }
    }

    /// ★ H08：这一查**按谁的天花板看** —— 只接受治理面铸的 [`Ceiling`]。
    ///
    /// ★ 为什么是「只接受」而不是「传一个 Marking」：来源1-①.3 逐字
    /// 「`Query` 构造时**只接受治理面给的** `ceiling`（★ **不给调用方自由填**，否则绕闸）」。
    #[must_use]
    pub fn under(store: &'a Store, ceiling: Ceiling) -> Self {
        Self {
            ceiling: Some(ceiling),
            ..Self::new(store)
        }
    }

    /// 只要某一类。
    #[must_use]
    pub fn filter_kind(mut self, kind: impl Into<String>) -> Self {
        self.kind = Some(kind.into());
        self
    }

    /// 某一格等于某值（★ 多条是「与」；缺席的格一律落空）。
    #[must_use]
    pub fn filter_field(mut self, field: impl Into<String>, value: impl Into<String>) -> Self {
        self.wanted.push(Wanted {
            field: field.into(),
            value: value.into(),
        });
        self
    }

    /// 按某格排序（今天按字符串序；★ 缺席的格排在前面 —— Rust 的 None < Some；
    /// 数字格将来走类型化排序；★ 排序是**稳定**的：同值的两条保持键升序）。
    #[must_use]
    pub fn order_by(mut self, field: impl Into<String>) -> Self {
        self.order_field = Some(field.into());
        self
    }

    /// 只取前 N（★ 在排序**之后**取；N ＝ 0 ⇒ 空）。
    #[must_use]
    pub fn take(mut self, n: usize) -> Self {
        self.take = Some(n);
        self
    }

    /// 全部命中。
    ///
    /// ★ 次序：先按**键升序**枚举现状（确定性）；给了 order_by 再按该格排（稳定）；
    /// 最后取前 N。
    #[must_use]
    pub fn all(&self) -> Vec<(&str, &'a Registration)> {
        let kept = self
            .candidates()
            .into_iter()
            .filter(|(_, reg)| self.visible(reg))
            .collect();
        self.arrange(kept)
    }

    /// ★ H08：结果 ＋ **被挡掉几条**（只报计数）。
    #[must_use]
    pub fn run(&self) -> QueryResult<'a> {
        let candidates = self.candidates();
        let kept: Vec<(&'a str, &'a Registration)> = candidates
            .iter()
            .copied()
            .filter(|(_, reg)| self.visible(reg))
            .collect();
        let suppressed = candidates.len() - kept.len();
        QueryResult {
            hits: self.arrange(kept),
            suppressed,
        }
    }

    /// 候选：先按**键升序**枚举现状，再按类与判据筛（★ 还没过天花板）。
    fn candidates(&self) -> Vec<(&'a str, &'a Registration)> {
        self.store
            .keys()
            .into_iter()
            .filter_map(|key| self.store.get(key).map(|reg| (key, reg)))
            .filter(|(_, reg)| self.kind.as_deref().is_none_or(|want| reg.kind == want))
            .filter(|(_, reg)| {
                self.wanted
                    .iter()
                    .all(|want| Cell::of(reg, &want.field).matches(&want.value))
            })
            .collect()
    }

    /// ★ 这一条在**这次查询**里看不看得见：没过天花板 ⇒ 全看得见；过了 ⇒ 分级 ≤ 天花板。
    /// ★ **认不得的分级 ⇒ 看不见**（fail closed，不放行）。
    fn visible(&self, reg: &Registration) -> bool {
        let Some(ceiling) = self.ceiling else {
            return true;
        };
        matches!(reg.marking(), Ok(m) if m <= ceiling.value())
    }

    /// 排序（给了 order_by 才排）＋ 取前 N（★ 在排序**之后**取）。
    fn arrange(
        &self,
        mut hits: Vec<(&'a str, &'a Registration)>,
    ) -> Vec<(&'a str, &'a Registration)> {
        if let Some(field) = &self.order_field {
            hits.sort_by(|a, b| a.1.get_str(field).cmp(&b.1.get_str(field)));
        }
        if let Some(n) = self.take {
            hits.truncate(n);
        }
        hits
    }

    /// 第一条（★ 与 all 同一口径）。
    #[must_use]
    pub fn first(&self) -> Option<(&str, &'a Registration)> {
        self.all().into_iter().next()
    }

    /// 命中几条。
    #[must_use]
    pub fn count(&self) -> usize {
        self.all().len()
    }
}

#[cfg(test)]
mod tests {
    use crate::core::types::{Registration, Who};
    use crate::engine::ledger::Ledger;
    use crate::engine::store::Store;
    use crate::governance::Governance;

    use super::Query;

    const ZHANG: &str = "world://user/zhang";
    const ONT: &str = include_str!("../../../aios-ontology/data/ontology.json");

    /// 带分级的一封「信纸」（H08）。
    fn reg_marked(kind: &str, name: &str, marking: &str) -> Registration {
        let mut fields = serde_json::Map::new();
        fields.insert("name".to_string(), serde_json::json!(name));
        fields.insert("marking".to_string(), serde_json::json!(marking));
        Registration::new(kind, fields)
    }

    fn who() -> Who {
        Who::new(ZHANG)
    }

    fn reg(kind: &str, name: &str, state: Option<&str>) -> Registration {
        let mut fields = serde_json::Map::new();
        fields.insert("name".to_string(), serde_json::json!(name));
        if let Some(state) = state {
            fields.insert("state".to_string(), serde_json::json!(state));
        }
        Registration::new(kind, fields)
    }

    /// 三条现状：两条 application（有 state）＋ 一条 surface（**没有** state 这一格）。
    fn seeded() -> Store {
        let mut s = Store::new();
        s.create_as(
            &who(),
            "application:alpha",
            reg("application", "alpha", Some("running")),
        )
        .expect("该成");
        s.create_as(
            &who(),
            "application:beta",
            reg("application", "beta", Some("installed")),
        )
        .expect("该成");
        s.create_as(&who(), "surface:gamma", reg("surface", "gamma", None))
            .expect("该成");
        s
    }

    fn keys_of(q: &Query<'_>) -> Vec<String> {
        q.all().iter().map(|(key, _)| (*key).to_string()).collect()
    }

    /// ★★ 会红反例 1（**缺席即假**）：格没有值 ⇒ 判据必须落空。
    /// 让它红的改法：把 Cell::Absent 当空串（或抽掉 Absent 那一档）⇒ 本用例红。
    #[test]
    fn an_absent_field_never_matches() {
        let s = seeded();
        assert_eq!(
            Query::new(&s).filter_field("state", "").count(),
            0,
            "缺席的格不许拿空串去比"
        );
        assert_eq!(
            Query::new(&s).filter_field("name", "gamma").count(),
            1,
            "有值的格照常命中"
        );
    }

    /// ★★ 会红反例 2（**候选按键升序**）：不排序时命中也必须次序确定。
    /// 让它红的改法：候选改从无序容器／哈希表来 ⇒ 本用例红。
    #[test]
    fn candidates_come_in_key_order() {
        let s = seeded();
        assert_eq!(
            keys_of(&Query::new(&s)),
            ["application:alpha", "application:beta", "surface:gamma"]
        );
    }

    /// ★★ 会红反例 3（**多条判据是「与」**）。
    #[test]
    fn predicates_are_joined_by_and() {
        let s = seeded();
        assert_eq!(Query::new(&s).filter_field("state", "running").count(), 1);
        let both = Query::new(&s)
            .filter_field("state", "running")
            .filter_field("name", "beta")
            .count();
        assert_eq!(both, 0, "两条要同时满足才算命中");
        let kind_and_field = Query::new(&s)
            .filter_kind("application")
            .filter_field("state", "installed")
            .count();
        assert_eq!(kind_and_field, 1);
    }

    /// ★★ 会红反例 4（**先排后取**）：take(0) 必须空；take 超过总数有多少给多少。
    /// 让它红的改法：把 take(0) 当「没设」（旧形状的一种写法）⇒ 本用例红。
    #[test]
    fn take_applies_after_ordering() {
        let s = seeded();
        assert_eq!(Query::new(&s).order_by("name").take(0).count(), 0);
        assert_eq!(
            keys_of(&Query::new(&s).order_by("name").take(2)),
            ["application:alpha", "application:beta"],
            "取排序后的前 N"
        );
        assert_eq!(
            Query::new(&s).take(10).count(),
            3,
            "超过总数 ⇒ 有多少给多少"
        );
    }

    /// ★★ 会红反例 5（**查询读的是现状，不是历史**）：立碑后的键不许出现。
    /// 让它红的改法：查询直接扫 Store::rows ⇒ 本用例红。
    #[test]
    fn queries_read_the_now_not_the_history() {
        let mut s = seeded();
        s.delete_as(&who(), "application:alpha", "撤")
            .expect("立碑该成");
        assert_eq!(Query::new(&s).count(), 2, "三笔现状、一块碑 ⇒ 两条");
        assert!(Query::new(&s)
            .filter_field("name", "alpha")
            .all()
            .is_empty());
        assert_eq!(s.rows().len(), 4, "历史一行不少");
    }

    /// ★★ 会红反例 7（H08 · **天花板挡得住**）：一条 `CONFIDENTIAL`，在 `agent`
    /// （本体天花板 `INTERNAL`）眼下**必须看不见**，且**只报计数**（`suppressed ＝ 1`，不带 id）。
    ///
    /// 依据（来源1-①.3 逐字）：「查询带天花板：`Query` 构造时**只接受治理面给的** `ceiling`；
    /// `all()` 先排除超天花板者，再算 `count`／聚合；返回值多一项 `suppressed`
    /// （**只报计数、不泄 id**）」；天花板表＝本体 `governance.markings.ceiling_by_role`。
    ///
    /// 让它红的改法：去掉 `run()` 里的 `visible` 过滤 ⇒ 第一条断言红。
    #[test]
    fn a_confidential_row_is_invisible_under_an_agent_ceiling() {
        let gov = Governance::from_ontology(ONT).expect("出厂本体该装得上");
        let mut s = seeded();
        s.create_as(
            &who(),
            "surface:delta",
            reg_marked("surface", "delta", "CONFIDENTIAL"),
        )
        .expect("该成");
        let agent = Who::new("world://agent/dsh");

        let r = Query::under(&s, gov.ceiling_of(&agent)).run();
        assert_eq!(r.hits.len(), 3, "四条里 CONFIDENTIAL 那一条不许出来");
        assert!(
            r.hits.iter().all(|(key, _)| *key != "surface:delta"),
            "★ 被挡掉的那一条一个 id 都不许带出来"
        );
        assert_eq!(r.suppressed, 1, "★ 只报计数");
    }

    /// ★ 正控（同一条规矩的另一半）：同一条 `CONFIDENTIAL`，在 `human`（天花板 `CONFIDENTIAL`）
    /// 眼下**看得见**。若为了挡 agent 把所有人一起挡了，本用例红。
    #[test]
    fn a_confidential_row_is_visible_under_a_human_ceiling() {
        let gov = Governance::from_ontology(ONT).expect("出厂本体该装得上");
        let mut s = seeded();
        s.create_as(
            &who(),
            "surface:delta",
            reg_marked("surface", "delta", "CONFIDENTIAL"),
        )
        .expect("该成");
        let human = Who::new("world://user/zhang");

        let r = Query::under(&s, gov.ceiling_of(&human)).run();
        assert_eq!(r.hits.len(), 4, "human 的天花板够高 ⇒ 看得见");
        assert_eq!(r.suppressed, 0, "没挡掉就不报计数");
    }

    /// ★ H08 机制 4：**每次过滤记一笔** —— 族 `notice`／`what=marking.filtered`，
    /// params **只有** `suppressed`（★ 不带 id）。没挡掉 ⇒ **账上不落空笔**。
    #[test]
    fn the_suppressed_count_is_recorded_as_a_notice_without_ids() {
        let gov = Governance::from_ontology(ONT).expect("出厂本体该装得上");
        let mut s = seeded();
        s.create_as(
            &who(),
            "surface:delta",
            reg_marked("surface", "delta", "CONFIDENTIAL"),
        )
        .expect("该成");
        let agent = Who::new("world://agent/dsh");
        let mut ledger = Ledger::load(ONT).expect("族的权威清单从本体来");

        let r = Query::under(&s, gov.ceiling_of(&agent)).run();
        r.record(&mut ledger, &agent).expect("记一笔该成");
        let rows = ledger.query_family("notice");
        assert_eq!(rows.len(), 1, "挡掉一次 ⇒ 记一笔");
        assert_eq!(rows[0].what, "marking.filtered");
        assert_eq!(rows[0].params.len(), 1, "★ 只带 suppressed，不带 id");
        assert_eq!(rows[0].param("suppressed"), Some(&serde_json::json!(1)));

        // ★ 没挡掉 ⇒ 不记（账上不落空笔）。
        let human = Who::new("world://user/zhang");
        Query::under(&s, gov.ceiling_of(&human))
            .run()
            .record(&mut ledger, &human)
            .expect("不记也该成");
        assert_eq!(ledger.query_family("notice").len(), 1, "没挡掉 ⇒ 不加笔");
    }

    /// ★ H08：**不传天花板** ⇒ 口径与从前一样（全给）—— 本批不动旧行为。
    #[test]
    fn without_a_ceiling_the_query_behaves_as_before() {
        let mut s = seeded();
        s.create_as(
            &who(),
            "surface:delta",
            reg_marked("surface", "delta", "CONFIDENTIAL"),
        )
        .expect("该成");
        assert_eq!(Query::new(&s).count(), 4, "没天花板 ⇒ 不分级地全给");
        assert_eq!(Query::new(&s).run().suppressed, 0);
    }

    /// ★★ 会红反例 6（**排序口径**）：缺席的格排在**最前**，不是排到最后。
    /// 让它红的改法：把缺席当最大值（或干脆跳过缺席的行）⇒ 本用例红。
    #[test]
    fn absent_fields_sort_first() {
        let s = seeded();
        assert_eq!(
            keys_of(&Query::new(&s).order_by("state")),
            ["surface:gamma", "application:beta", "application:alpha"],
            "缺席在前；有值的按值升序：installed < running"
        );
    }
}
