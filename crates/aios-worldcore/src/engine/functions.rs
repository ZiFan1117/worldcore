//! 面⑤：**函数** —— 本体 `functions.entries` 里那 9 条「**动作的实现面**」。
//!
//! 参考 Palantir：`foundry_ontology/core/function.py` 的 `OntologyFunction`
//! （`function_id`／`display_name`／`description`／`inputs`／`output_type` ＋ 两个口：
//! `describe()` 出「给人／工具列单」的 JSON；`execute(**kwargs)` 转发给 implementation）。
//!
//! ★ 学它两样，**只用我们的名字重写**（不引它的 crate、不抄它的文件）：
//! · **装法**：AIOS 侧那件装载器（`crates/aios-ontology/src/lib.rs`）把 `functions.entries`
//!   装成一张「名字 ⇒ 声明」的表，**装的时候就**给每个入口名过一道**命令字面量**审查
//!   （含空格／`/`／`"`，或是本体 `functions._registered_host_commands` 里已登记的宿主命令名 ⇒ 拒）；
//!   本件 `Functions::load` 照这条**同口径**重写。
//! · **调用**：它把 `describe()`（声明）与 `execute()`（干活）**分两件**。
//!   本件落成三步：① 查在册 ⇒ ② 逐条校入参 ⇒ ③ 才交给「干活的」。
//! ★ 它还教了一样**数据怎么组织**：表以 `function_id` 为键；`inputs` 是「名 ⇒ 类型声明串」的
//!   一张**小表**（不是位置参数）⇒ 本件照这个形状存、校的时候**逐名对**。
//!
//! ★ 本体的口径（逐字）：`functions._comment` ——「函数**不改本体** —— 要落地只能被某个动作引用、
//!   由该动作执行。本表**只收入口名**：它是一张**引用表**，代码不进本体。」
//!   ⇒ 本件**不装实现**：真代码由注进来的 `Doer` 担（默认 `DryDoer` 只报不干活）。
//!
//! ★ 三处**如实登记**（是本体现取的缺口，不是本件发明的规矩）：
//! ① `inputs` **没有 `required` 标记** ⇒ 少给一个入参**不拒**（只判「给了的那些对不对」）；
//! ② `fn.ledger.compact`／`fn.world.rekey`／`fn.world.migrate` 的 `output_type` 是**空串**
//!    （各自 `_note` 逐字「output_type 未定：前置名 ledger／world 不在 objects 里」）⇒
//!    照原样收下、**不替它发明**出参类型；本件也**不拿出参挡路**（照 P 的 `execute` 只转发）；
//! ③ **许可不在这里定** —— 本体 `fn.presence.report.display_name` 逐字「『有没有许可』不在这里定，
//!    由 `permissions.grants` ＋ `default: deny` 决定」⇒ 本面**不查治理**（治理在执行面⑦）。
//!
//! ★ **「动作 → 函数」的映射不在本件**：本体 `actions.<动作>.function` 那一项由面①
//!   （`Registry::function_of_action`）读；本件只管「给一个函数名，它是不是在册、入参对不对」。

/// 一条函数：本体那五格 ＋ 逐条校入参（`Function::load`／`check_args`／`describe`）。
mod entry;
/// 函数表与「干活的」那一层（`Functions::load`／`get`／`ids`／`call`）。
mod table;

pub use entry::Function;
pub use table::{Called, Doer, DryDoer, Functions};

#[cfg(test)]
mod tests;
