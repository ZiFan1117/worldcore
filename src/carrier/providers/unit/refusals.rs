use super::super::*;
use super::*;
use crate::carrier::provider::Provider;
use serde_json::json;
use std::path::PathBuf;

#[test]
fn refuses_a_capability_not_in_the_manifest() {
    let m = manifest(r#"{"capability":"a.b","provider":"p","verbs":["x"]}"#);
    let mut reg = Registry::new();
    reg.add(Box::new(Job::default()));
    let o = execute(
        &m,
        &reg,
        &inv("not.declared", "x", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(o.detail.to_string().contains("不在执行清单里"));
}

#[test]
fn refuses_a_verb_not_allowed_by_the_manifest() {
    let m = manifest(r#"{"capability":"a.b","provider":"job","verbs":["start"]}"#);
    let mut reg = Registry::new();
    reg.add(Box::new(Job::default()));
    let o = execute(
        &m,
        &reg,
        &inv("a.b", "list", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(o.detail.to_string().contains("动词未被该能力授权"));
}

#[test]
fn refuses_when_no_provider_is_registered() {
    let m = manifest(r#"{"capability":"a.b","provider":"ghost","verbs":["x"]}"#);
    let reg = Registry::new();
    let o = execute(&m, &reg, &inv("a.b", "x", json!({})), &no_confirm, &no_undo);
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(o.detail.to_string().contains("没有对应的执行器"));
}

#[test]
fn refuses_when_confirmation_is_required_but_missing() {
    let m = manifest(
        r#"{"capability":"job.start","provider":"job","verbs":["list"],"confirm":"required"}"#,
    );
    let mut reg = Registry::new();
    reg.add(Box::new(Job::default()));
    let o = execute(
        &m,
        &reg,
        &inv("job.start", "list", json!({})),
        &no_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(o.detail.to_string().contains("需要人确认"));
    // 确认给了 ⇒ 继续走到执行
    let o2 = execute(
        &m,
        &reg,
        &inv("job.start", "list", json!({})),
        &yes_confirm,
        &no_undo,
    );
    assert_eq!(o2.result, crate::carrier::outcome::OK);
}

#[test]
fn refuses_to_act_when_the_undo_point_cannot_be_made() {
    let m = manifest(
        r#"{"capability":"job.start","provider":"job","verbs":["list"],"risk":"high","undo":"before-each"}"#,
    );
    let mut reg = Registry::new();
    reg.add(Box::new(Job::default()));
    let o = execute(
        &m,
        &reg,
        &inv("job.start", "list", json!({})),
        &yes_confirm,
        &no_undo,
    );
    assert_eq!(o.result, crate::carrier::outcome::REFUSED);
    assert!(o.detail.to_string().contains("撤销点做不成"));
    // 撤销点做成了 ⇒ 结果里必须带上内容引用
    let o2 = execute(
        &m,
        &reg,
        &inv("job.start", "list", json!({})),
        &yes_confirm,
        &ok_undo,
    );
    assert_eq!(o2.result, crate::carrier::outcome::OK);
    assert!(o2.undo_ref.is_some());
}

#[test]
fn backlight_refuses_rather_than_pretending() {
    // 指向一个不存在的设备根：必须报 NoDevice，**不得**返回编造的亮度
    let b = Backlight {
        root: PathBuf::from("/definitely/not/here"),
    };
    let e = b.call("get", &json!({})).unwrap_err();
    assert!(e.contains("NoDevice"), "{e}");
}

#[test]
fn backlight_percent_scale_is_explicit_not_guessed() {
    // scale 缺失 ⇒ 按 raw；给了 percent 才换算
    assert_eq!(Backlight::to_raw(3, 100, &json!({})).unwrap(), 3);
    assert_eq!(
        Backlight::to_raw(3, 100, &json!({"scale":"percent"})).unwrap(),
        3
    );
    assert_eq!(
        Backlight::to_raw(50, 255, &json!({"scale":"percent"})).unwrap(),
        128
    );
    assert!(Backlight::to_raw(3, 100, &json!({"scale":"percent"})).is_ok());
    assert!(Backlight::to_raw(101, 255, &json!({"scale":"percent"})).is_err());
    assert!(Backlight::to_raw(300, 255, &json!({})).is_err());
    assert!(Backlight::to_raw(1, 255, &json!({"scale":"nonsense"})).is_err());
}
