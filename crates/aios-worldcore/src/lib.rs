//! `aios-worldcore` — worldcore **最小内核**的门面。
//!
//! 八个面（各一个 crate，各自成为一个"原子"）：
//!
//! | # | 面 | crate | 参考 Palantir |
//! |---|---|---|---|
//! | ① | 注册（本体里有哪些类型） | `aios-worldcore-registry` | `core/ontology.py` 的 `register_*` |
//! | ② | 实例注册（装了啥／哪块界面） | `aios-worldcore-instances` | `engine/object_store.py` 的 `create` |
//! | ③ | 校验（进门安检） | `aios-worldcore-validate` | `validate_instance`／`validate_value` |
//! | ④ | 实例存储 | `aios-worldcore-store` | `ObjectStore` |
//! | ⑤ | 查询 | `aios-worldcore-query` | `engine/query_engine.py` |
//! | ⑥ | 账 | `aios-worldcore-ledger` | `engine/audit_log.py` |
//! | ⑦ | 执行 | `aios-worldcore-execute` | `engine/action_executor.py` |
//! | ⑧ | 治理 | `aios-worldcore-governance` | `governance/` |
//!
//! ★ **共同类型**在 `aios-worldcore-shared`（谁／拒／为什么／要登记的东西／一件事）—— 八面共用。
//! ★ **本体的唯一权威**是 `aios-ontology` 装载的那份 JSON；★ **八面都不许自带类型清单**。

pub use aios_ontology::{Ontology, Reject};

/// 装载本体（转发 `Ontology::load_str`；门面只给一个入口）。
pub fn load_ontology(text: &str) -> Result<Ontology, Reject> {
    Ontology::load_str(text)
}

pub use aios_worldcore_execute::{DryRun, Exec, Executor};
pub use aios_worldcore_governance::Governance;
pub use aios_worldcore_instances::Instances;
pub use aios_worldcore_ledger::Ledger;
pub use aios_worldcore_query::Query;
pub use aios_worldcore_registry::Registry;
pub use aios_worldcore_shared::{Admit, Event, EventSeq, Reason, Refuse, Registration, Who};
pub use aios_worldcore_store::Store;
pub use aios_worldcore_validate::{check_enum, check_refs, check_required, check_shape};
