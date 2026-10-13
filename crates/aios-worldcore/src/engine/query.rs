//! 面⑤：**查询** —— 按条件找、排序、取前 N。
//!
//! 参考 Palantir：`engine/query_engine.py` 的 `filter`／`navigate`／`order_by`／`take`／`all`／`first`／`count`。

use crate::core::types::Registration;
use crate::engine::store::Store;

/// 一次查询（链式；最后 `all`／`first`／`count` 取结果）。
#[derive(Debug)]
pub struct Query<'a> {
    store: &'a Store,
    kind: Option<String>,
    field_equals: Vec<(String, String)>,
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
            field_equals: Vec::new(),
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

    /// 某一格等于某值。
    #[must_use]
    pub fn filter_field(mut self, field: impl Into<String>, value: impl Into<String>) -> Self {
        self.field_equals.push((field.into(), value.into()));
        self
    }

    /// 按某格排序（今天按字符串序；数字格将来走类型化排序）。
    #[must_use]
    pub fn order_by(mut self, field: impl Into<String>) -> Self {
        self.order_field = Some(field.into());
        self
    }

    /// 只取前 N。
    #[must_use]
    pub fn take(mut self, n: usize) -> Self {
        self.take = Some(n);
        self
    }

    /// 全部命中（升序键；给定 `order_by` 则按该格排）。
    #[must_use]
    pub fn all(&self) -> Vec<(&str, &'a Registration)> {
        let mut hits: Vec<(&str, &'a Registration)> = self
            .store
            .keys()
            .into_iter()
            .filter_map(|k| self.store.get(k).map(|r| (k, r)))
            .filter(|(_, r)| self.kind.as_deref().is_none_or(|kk| r.kind == kk))
            .filter(|(_, r)| {
                self.field_equals
                    .iter()
                    .all(|(f, v)| r.get_str(f).is_some_and(|s| s == v))
            })
            .collect();
        if let Some(of) = &self.order_field {
            hits.sort_by(|a, b| a.1.get_str(of).cmp(&b.1.get_str(of)));
        }
        if let Some(n) = self.take {
            hits.truncate(n);
        }
        hits
    }

    /// 第一条。
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
