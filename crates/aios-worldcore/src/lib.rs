//! `aios-worldcore` — worldcore 最小内核。
//!
//! ★ 结构照 Palantir foundry-ontology 的三个目录：
//! - `core/` 定义层（共同类型 ＋ 面① 注册）
//! - `engine/` 运行层（面②③④⑤⑥⑦）
//! - `governance/` 治理（面⑧）
//!
//! ★ 不设门面：路径照文件夹走（`aios_worldcore::engine::store::Store`）。

pub mod core;
pub mod engine;
pub mod governance;
