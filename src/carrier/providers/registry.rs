use super::Backlight;
use super::Job;
use super::Package;
use crate::carrier::provider::Provider;
use std::collections::BTreeMap;

/// 执行器注册表：能力名 → 执行器。
///
/// **注册表为空不是"什么都不允许"的安全默认，而是"没装执行器"**——
/// 与门禁策略的空能力表同一条口径：空即拒绝服务，且要说清是"没配好"。
pub struct Registry {
    providers: BTreeMap<String, Box<dyn Provider + Send + Sync>>,
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    /// 空注册表。
    pub fn new() -> Self {
        Registry {
            providers: BTreeMap::new(),
        }
    }

    /// 内置三个执行器（背光 / 包 / 任务）。
    pub fn builtin() -> Self {
        let mut r = Self::new();
        r.add(Box::new(Backlight::default()));
        r.add(Box::new(Package::default()));
        r.add(Box::new(Job::default()));
        r
    }

    /// 注册一个执行器。
    pub fn add(&mut self, p: Box<dyn Provider + Send + Sync>) {
        self.providers.insert(p.name().to_string(), p);
    }

    /// 按名字取执行器。
    pub fn get(&self, name: &str) -> Option<&(dyn Provider + Send + Sync)> {
        self.providers.get(name).map(|b| b.as_ref())
    }

    /// 已注册的执行器名（有序）。
    pub fn names(&self) -> Vec<&str> {
        self.providers.keys().map(String::as_str).collect()
    }
}
