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

use crate::core::types::Registration;
use crate::engine::store::Store;

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

/// 一次查询（链式；最后 all／first／count 取结果）。
#[derive(Debug)]
pub struct Query<'a> {
    store: &'a Store,
    kind: Option<String>,
    wanted: Vec<Wanted>,
    order_field: Option<String>,
    take: Option<usize>,
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
        let mut hits: Vec<(&str, &'a Registration)> = self
            .store
            .keys()
            .into_iter()
            .filter_map(|key| self.store.get(key).map(|reg| (key, reg)))
            .filter(|(_, reg)| self.kind.as_deref().is_none_or(|want| reg.kind == want))
            .filter(|(_, reg)| {
                self.wanted
                    .iter()
                    .all(|want| Cell::of(reg, &want.field).matches(&want.value))
            })
            .collect();
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
    use crate::engine::store::Store;

    use super::Query;

    const ZHANG: &str = "world://user/zhang";

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
        s.create_as(&who(), "application:alpha", reg("application", "alpha", Some("running")))
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
        q.all()
            .iter()
            .map(|(key, _)| (*key).to_string())
            .collect()
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
        assert_eq!(Query::new(&s).take(10).count(), 3, "超过总数 ⇒ 有多少给多少");
    }

    /// ★★ 会红反例 5（**查询读的是现状，不是历史**）：立碑后的键不许出现。
    /// 让它红的改法：查询直接扫 Store::rows ⇒ 本用例红。
    #[test]
    fn queries_read_the_now_not_the_history() {
        let mut s = seeded();
        s.delete_as(&who(), "application:alpha", "撤")
            .expect("立碑该成");
        assert_eq!(Query::new(&s).count(), 2, "三笔现状、一块碑 ⇒ 两条");
        assert!(Query::new(&s).filter_field("name", "alpha").all().is_empty());
        assert_eq!(s.rows().len(), 4, "历史一行不少");
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
