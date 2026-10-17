//! 总线那一层：**收成一个口**（T-270）—— ★ 作者令「把底层的执行体写完，然后注册进来」。
//!
//! ★★★ 为什么先做这个口：
//!   · 执行体要成为【独立进程】⇒ 它得和本体说话；
//!   · ★ **而 13 今天没有总线**（现取：`crates/` 里 `zenoh` 0 命中、`Cargo.lock` 里 0 行）；
//!   · ⇒ 若直接把某个总线写进执行体，★ **换总线就要改执行体**（✗）。
//!
//! ★★ 所以：★ **总线只以【这个口】出现在内核里** —— ★ 换总线时只改实现，不改执行体。
//!   ★ 今天带一个 **`LocalTransport`**（★ 同进程内存队列）⇒ ★ 执行体**能编、能跑、能测**；
//!   ★ 总线的选型（zenoh 还是别的、住哪个 crate）**由人定**（硬约束 6）—— 定了之后加一个实现即可。
//!
//! ★ 口上只有两件事：**发一条**（`put`）／**收一条**（`take`，带超时）。
//!   ★ 不用「请求-应答」那种花活 —— ★ 本仓的消息是**一条一条的**（与账同口径）。

/// ★★ **zenoh 实现**（★ 总线就是 zenoh —— 作者确认）—— ★ 开关 `--features bus-zenoh`。
#[cfg(feature = "bus-zenoh")]
pub mod zenoh_impl;

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use crate::core::types::{Admit, Reason, Refuse};

/// ★★ **发一条／收一条** —— ★ 内核里出现总线的【唯一】地方。
pub trait Transport: Send + Sync {
    /// ★ 往一个话题发一条（★ 话题名由调用方给，★ 不在这里拼）。
    fn put(&self, topic: &str, payload: &str) -> Admit<()>;
    /// ★ 从一个话题收一条（★ 带超时；★ 超时 ⇒ 拒，不返回空串 —— 空串不是「没有」）。
    fn take(&self, topic: &str, timeout: Duration) -> Admit<String>;
}

/// ★ **同进程的内存队列**（★ 今天用它让执行体跑起来；★ 不是总线选型）。
#[derive(Clone, Default)]
pub struct LocalTransport {
    queues: Arc<Mutex<std::collections::BTreeMap<String, VecDeque<String>>>>,
}

impl LocalTransport {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// ★ 这个口上现在等着几条（★ 读数的用）。
    #[must_use]
    pub fn waiting(&self, topic: &str) -> usize {
        self.queues
            .lock()
            .map(|q| q.get(topic).map_or(0, VecDeque::len))
            .unwrap_or(0)
    }
}

impl Transport for LocalTransport {
    fn put(&self, topic: &str, payload: &str) -> Admit<()> {
        let mut q = self.queues.lock().map_err(|_| {
            Refuse::new(
                Reason::StorageUnavailable {
                    path: topic.to_string(),
                },
                "<队列锁坏了>",
            )
        })?;
        q.entry(topic.to_string())
            .or_default()
            .push_back(payload.to_string());
        Ok(())
    }

    fn take(&self, topic: &str, timeout: Duration) -> Admit<String> {
        let deadline = std::time::Instant::now() + timeout;
        loop {
            {
                let mut q = self.queues.lock().map_err(|_| {
                    Refuse::new(
                        Reason::StorageUnavailable {
                            path: topic.to_string(),
                        },
                        "<队列锁坏了>",
                    )
                })?;
                if let Some(v) = q.get_mut(topic).and_then(VecDeque::pop_front) {
                    return Ok(v);
                }
            }
            if std::time::Instant::now() >= deadline {
                // ★ 超时 ⇒ 拒（★ 与「账没写成就拒」同口径）。
                return Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: topic.to_string(),
                    },
                    "<超时：那个话题上没有消息>",
                ));
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn put_then_take_round_trips_and_empty_times_out() {
        let t = LocalTransport::new();
        t.put("world/exec", "{\"action\":\"fs.list\"}")
            .expect("发得出去");
        assert_eq!(t.waiting("world/exec"), 1);
        let got = t
            .take("world/exec", Duration::from_millis(50))
            .expect("收得到");
        assert!(got.contains("fs.list"));
        // ★ 空话题 ⇒ 超时 ⇒ 拒（★ 不是返回空串）。
        assert!(t.take("world/exec", Duration::from_millis(20)).is_err());
    }
}
