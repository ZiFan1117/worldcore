//! `Transport` 的 **zenoh 实现**（T-271）—— ★ 总线就是 zenoh（作者确认）。
//!
//! ★ 为什么这样写：
//!   · `Transport` 口是**同步**的（★ 执行体那支 bin 是 `fn main()`，不想把异步传染进去）；
//!   · zenoh 是**异步**的 ⇒ ★ 这里**自己持一个 runtime**，每个方法 `block_on`。
//!   · ★ `block_on` 不能在异步上下文里调 ⇒ ★ 本实现只能用在**同步**的调用方（★ 那正是执行体）。
//!
//! ★ 开关：★ `--features bus-zenoh`（★ 默认关 —— 不开时内核不拉网络栈）。
//! ★ 配置：★ 从环境变量 `ZENOH_CONFIG` 读（★ 与演示载体同法）；★ 没有就用默认。

use std::time::Duration;

use crate::core::types::{Admit, Reason, Refuse};
use crate::engine::transport::{Subscription, Transport};

/// ★ **真总线**（zenoh）上的那条口。
pub struct ZenohTransport {
    rt: std::sync::Arc<tokio::runtime::Runtime>,
    session: zenoh::Session,
}

impl ZenohTransport {
    /// ★ 连上总线。★ 配置读 `ZENOH_CONFIG`（★ 与演示载体同法）。
    pub fn connect() -> Admit<Self> {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh runtime>".to_string(),
                    },
                    format!("{e}"),
                )
            })?;
        let session = rt.block_on(async {
            // ★★ `from_env` 在【没有 ZENOH_CONFIG 环境变量】时会报错（★ systemd 单元里就没有）。
            //   ⇒ ★ 回退到默认配置（★ 默认就是 `mode: peer` + 本机发现），★ 不让它把进程打死。
            let cfg = zenoh::Config::from_env().unwrap_or_default();
            zenoh::open(cfg).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh open>".to_string(),
                    },
                    format!("{e}"),
                )
            })
        })?;
        Ok(Self { rt: std::sync::Arc::new(rt), session })
    }

    /// ★★ **真总线往返自测**：★ **先订阅、再发、再收** —— ★ 这个顺序是 zenoh 的硬规矩
    /// （★ 默认不持久：★ 发布时没人订阅 ⇒ 消息就丢了；★ 我第一次就是照「先发后订」跑，收不回来）。
    pub fn round_trip(&self, topic: &str, payload: &str, timeout: Duration) -> Admit<String> {
        let topic = topic.to_string();
        let payload = payload.to_string();
        let s = self.session.clone();
        self.rt.block_on(async move {
            // ★ ① 先订阅
            let sub = s.declare_subscriber(&topic).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh sub>".to_string(),
                    },
                    format!("{e}"),
                )
            })?;
            // ★ ② 再发
            s.put(&topic, payload).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh put>".to_string(),
                    },
                    format!("{e}"),
                )
            })?;
            // ★ ③ 再收
            match tokio::time::timeout(timeout, sub.recv_async()).await {
                Ok(Ok(sample)) => {
                    Ok(String::from_utf8_lossy(&sample.payload().to_bytes()).into_owned())
                }
                Ok(Err(e)) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh recv>".to_string(),
                    },
                    format!("{e}"),
                )),
                Err(_) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh timeout>".to_string(),
                    },
                    "<超时：发出去的那条没回来>",
                )),
            }
        })
    }
}

/// ★ `ZenohTransport` 上的订阅：★ **subscriber 一直持有** ⇒ 没有「返回一条再重订」的空窗。
struct ZenohSubscription {
    rt: std::sync::Arc<tokio::runtime::Runtime>,
    sub: zenoh::pubsub::Subscriber<zenoh::handlers::FifoChannelHandler<zenoh::sample::Sample>>,
}

impl Subscription for ZenohSubscription {
    fn recv(&self, timeout: Duration) -> Admit<String> {
        let sub = self.sub.clone();
        self.rt.block_on(async move {
            match tokio::time::timeout(timeout, sub.recv_async()).await {
                Ok(Ok(sample)) => {
                    Ok(String::from_utf8_lossy(&sample.payload().to_bytes()).into_owned())
                }
                Ok(Err(e)) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh recv>".to_string(),
                    },
                    format!("{e}"),
                )),
                Err(_) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh timeout>".to_string(),
                    },
                    "<超时：订着但没消息>",
                )),
            }
        })
    }
}

impl Transport for ZenohTransport {
    fn subscribe(&self, topic: &str) -> Admit<Box<dyn Subscription>> {
        // ★★ 订一次、一直用 —— ★ 这里就 `declare_subscriber` 一次（★ 不再每次 take 都订）。
        let topic = topic.to_string();
        let s = self.session.clone();
        let handle = self.rt.block_on(async move { s.declare_subscriber(&topic).await });
        match handle {
            Ok(sub) => Ok(Box::new(ZenohSubscription {
                rt: std::sync::Arc::clone(&self.rt),
                sub,
            })),
            Err(e) => Err(Refuse::new(
                Reason::StorageUnavailable {
                    path: "<zenoh subscribe>".to_string(),
                },
                format!("{e}"),
            )),
        }
    }

    fn request(
        &self,
        ask_topic: &str,
        payload: &str,
        reply_topic: &str,
        timeout: Duration,
    ) -> Admit<String> {
        let ask = ask_topic.to_string();
        let reply = reply_topic.to_string();
        let payload = payload.to_string();
        let s = self.session.clone();
        self.rt.block_on(async move {
            // ★ ① 先订阅回话
            let sub = s.declare_subscriber(&reply).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: format!("<zenoh sub {reply}>"),
                    },
                    format!("{e}"),
                )
            })?;
            // ★ ② 再发请求
            s.put(&ask, payload).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: format!("<zenoh put {ask}>"),
                    },
                    format!("{e}"),
                )
            })?;
            // ★ ③ 再收回话
            match tokio::time::timeout(timeout, sub.recv_async()).await {
                Ok(Ok(sample)) => {
                    Ok(String::from_utf8_lossy(&sample.payload().to_bytes()).into_owned())
                }
                Ok(Err(e)) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: format!("<zenoh recv {reply}>"),
                    },
                    format!("{e}"),
                )),
                Err(_) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: format!("<zenoh timeout {reply}>"),
                    },
                    "<超时：请求发出去了，回话没回来>",
                )),
            }
        })
    }

    fn put(&self, topic: &str, payload: &str) -> Admit<()> {
        let topic = topic.to_string();
        let payload = payload.to_string();
        let s = self.session.clone();
        self.rt
            .block_on(async move { s.put(&topic, payload).await })
            .map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh put>".to_string(),
                    },
                    format!("{e}"),
                )
            })?;
        Ok(())
    }

    fn take(&self, topic: &str, timeout: Duration) -> Admit<String> {
        let topic = topic.to_string();
        let s = self.session.clone();
        let got = self.rt.block_on(async move {
            let sub = s.declare_subscriber(&topic).await.map_err(|e| {
                Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh sub>".to_string(),
                    },
                    format!("{e}"),
                )
            })?;
            match tokio::time::timeout(timeout, sub.recv_async()).await {
                Ok(Ok(sample)) => {
                    Ok(String::from_utf8_lossy(&sample.payload().to_bytes()).into_owned())
                }
                Ok(Err(e)) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh recv>".to_string(),
                    },
                    format!("{e}"),
                )),
                Err(_) => Err(Refuse::new(
                    Reason::StorageUnavailable {
                        path: "<zenoh timeout>".to_string(),
                    },
                    "<超时：那个话题上没有消息>",
                )),
            }
        });
        got
    }
}
