//! 错误码（`DEBT-01`）—— 让错误**可被程序判定**，而不只是给人读。
//!
//! ## 问题
//!
//! 本项目此前所有错误都是 `String`，且正文是中文散文。机器要判断"这是缺号还是权限问题"，
//! 只能匹配中文子串（测试里确实这么干过：`assert!(err.contains("门禁拒绝"))`）。
//! 那与 `REQ-N-001`"给程序读"的精神不符，也让**错误契约**无法冻结：
//! 改一句措辞就可能悄悄破坏调用方的判断。
//!
//! ## 口径（**稳定契约**）
//!
//! 凡**可编程判定**的错误，消息必须以
//!
//! ```text
//! ext.world.<域>.<原因>: <人话说明>
//! ```
//!
//! 开头。即：**冒号之前是机器读的，冒号之后是给人读的**。
//! 两个字段都只含 ASCII 字母/点号，故解析不依赖编码。
//!
//! 域（`<域>`）取值：`Ontology` / `Ledger` / `ReadModel` / `Gate` / `Guard` / `Channel` /
//! `Checkpoint` / `Project` / `World`。完整清单见 `WC-IC-001` §三。
//!
//! ## 为什么不一次改成强类型
//!
//! 把全仓 `Err(String)` 换成 `enum Error` 是**接口级破坏性变更**（触及每个模块与全部测试），
//! 而它换来的主要收益——"机器能判定错误种类"——用**稳定前缀**就能拿到。
//! 故本版先立契约与断言，强类型化登记为后续变更（走 R5）。
//!
//! ## 已知局限（不假装满足）
//!
//! - 前缀**不是编译期保证**：靠 [`code_of`] 与测试来守，写错仍可能漏过；
//! - 人话部分仍是中文散文，**不得**被程序依赖；
//! - 尚无用例编号到错误码的**双向**映射表（只有 `WC-IC-001` §三 的清单）。

/// 错误码前缀。
pub const PREFIX: &str = "ext.world.";

/// 从消息里取出错误码；不符合契约则返回 `None`。
///
/// 只认"以 `PREFIX` 开头、且在第一个 `:` 之前形如 `域.原因`"这一种形态。
/// **不猜、不修剪**——拿不到就是不符合契约（宁可在测试里红，也不要在生产里猜）。
pub fn code_of(msg: &str) -> Option<&str> {
    let head = msg.split(&[':', '\n'][..]).next()?.trim();
    let rest = head.strip_prefix(PREFIX)?;
    let (domain, reason) = rest.split_once('.')?;
    let ascii_ident =
        |s: &str| !s.is_empty() && s.chars().all(|c| c.is_ascii_alphanumeric() || c == '_');
    if ascii_ident(domain) && ascii_ident(reason) {
        Some(head)
    } else {
        None
    }
}

/// 该消息是否符合错误码契约。
pub fn has_code(msg: &str) -> bool {
    code_of(msg).is_some()
}

#[cfg(test)]
mod unit {
    use super::*;

    #[test]
    fn extracts_wellformed_codes() {
        assert_eq!(
            code_of("ext.world.Ledger.SeqGap: 缺号"),
            Some("ext.world.Ledger.SeqGap")
        );
        assert_eq!(
            code_of("ext.world.Gate.Rejected: 门禁拒绝：xxx"),
            Some("ext.world.Gate.Rejected")
        );
        // 多行也应只看第一行
        assert!(has_code("ext.world.ReadModel.BadState: 缺字段\n第二行"));
    }

    #[test]
    fn refuses_nonconforming_messages() {
        assert_eq!(code_of("门禁拒绝：能力未声明"), None, "无前缀 ⇒ 不符合契约");
        assert_eq!(code_of("ext.world.Ledger: 缺原因"), None);
        assert_eq!(code_of("ext.world..SeqGap: 空域"), None);
        assert_eq!(code_of("ext.world.Ledger.缺号: 非 ASCII"), None);
        assert_eq!(code_of(""), None);
    }
}
