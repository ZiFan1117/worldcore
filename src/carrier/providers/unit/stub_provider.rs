use super::super::*;
use super::*;
use crate::carrier::capd::Manifest;
use crate::carrier::provider::Provider;
use serde_json::{json, Value};
use std::path::Path;

/// 测试替身：只自报能力、不动手——用它把"**两套词表**"这一格单独钉住。
struct Stub {
    who: &'static str,
    caps: Vec<&'static str>,
}

impl Provider for Stub {
    fn name(&self) -> &'static str {
        self.who
    }
    fn capabilities(&self) -> Vec<&'static str> {
        self.caps.clone()
    }
    fn call(&self, _verb: &str, _params: &Value) -> Result<Value, String> {
        Ok(json!({"stub": true}))
    }
}

/// ★ **会红**：两套词表**各有一个合法名字**、却不是同一个（**不是拼写错**）。
///
/// `notice.mute` 在本体 `_interfaces` 里合法；`brightness.set` 在背光那套词表里**也合法**。
/// 这一格在 2026-10-04 之前**零调用点** ⇒ 两句话可以永远并存、没有任何东西会红。
#[test]
fn red_when_the_two_vocabularies_name_different_things() {
    let m = manifest(r#"{"capability":"notice.mute","provider":"backlight","verbs":["get"]}"#);
    let mut reg = Registry::new();
    reg.add(Box::new(Stub {
        who: "backlight",
        caps: vec!["brightness.set"],
    }));

    // ① 对账函数：点名是哪一项、两边各叫什么。
    let bad = cross_check(&m, &reg).unwrap_err();
    assert_eq!(bad.len(), 1, "两套词表撞车必须被点出来：{bad:?}");
    assert!(bad[0].contains("notice.mute"), "{}", bad[0]);
    assert!(bad[0].contains("brightness.set"), "{}", bad[0]);

    // ② 同一条清单走执行路径 ⇒ **拒绝**（根本不动手），理由与"没注册"分开。
    let o = execute(
        &m,
        &reg,
        &inv("notice.mute", "get", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(
        o.detail.to_string().contains("自报的能力里没有这一项"),
        "{}",
        o.detail
    );
}

/// ★ **正控**：对得上的那一对 ⇒ **绿**（不许把不该红的也判红）。
#[test]
fn green_when_the_provider_claims_that_capability() {
    let m = manifest(r#"{"capability":"notice.mute","provider":"backlight","verbs":["get"]}"#);
    let mut reg = Registry::new();
    reg.add(Box::new(Stub {
        who: "backlight",
        caps: vec!["notice.mute"],
    }));

    assert!(cross_check(&m, &reg).is_ok(), "对得上的那一对不许红");
    let o = execute(
        &m,
        &reg,
        &inv("notice.mute", "get", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(
        o.result,
        crate::carrier::outcome::OK,
        "正控：对账过了就该走到执行：{}",
        o.detail
    );
}

/// **出厂那一对**：`cap.d/` 的清单在出厂注册表上必须**全部对得上**。
///
/// ★ 第二句是必需的**正控**：空清单会让第一句**恒真**——那就成了装饰。
#[test]
fn the_factory_manifest_and_the_factory_registry_agree() {
    let m = Manifest::load_dir(Path::new("src/carrier/cap.d")).unwrap();
    let reg = Registry::builtin();
    assert!(
        cross_check(&m, &reg).is_ok(),
        "出厂 cap.d 与出厂执行器对不上：{:?}",
        cross_check(&m, &reg)
    );
    assert_eq!(m.names().len(), 3, "三份清单都要被读到：{:?}", m.names());
}

/// 执行器**没注册**不属对账这一条（**两条判据不互相冒充**）。
#[test]
fn an_unregistered_provider_is_not_a_vocabulary_mismatch() {
    let m = manifest(r#"{"capability":"notice.mute","provider":"ghost","verbs":["get"]}"#);
    let reg = Registry::new();
    assert!(
        cross_check(&m, &reg).is_ok(),
        "没注册由第 3 步回答，对账对它跳过"
    );
    let o = execute(
        &m,
        &reg,
        &inv("notice.mute", "get", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(
        o.detail.to_string().contains("没有对应的执行器"),
        "{}",
        o.detail
    );
}
