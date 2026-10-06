//! 公共模块 —— 被多方调用的机制（协议与契约的封装）。
//!
//! 判据：**"是不是只有某一个业务内部才需要它？"** —— 是则进那个业务的夹，否则进本夹。
//! 本夹四件分属：信封与信纸（`event`）、一条记录给谁（`delivery`）、
//! 请求与应答配对（`pairing`）、错误码契约（`error`）。
//! 它们**不占模块号**（`WC-MODREG-001` §2.1），被三个以上模块共用，故不属任何单一业务。

pub mod delivery;
pub mod error;
pub mod event;
pub mod pairing;
