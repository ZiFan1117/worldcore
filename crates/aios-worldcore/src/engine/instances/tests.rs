//! 面②「登记」的**会红反例**与正控：先问治理 → 逐格校 → 落表＋记账，＋ 目录（名字／类）。
//!
//! ★ **如实登记**：宿主**无 cargo** ⇒ 本席**没跑过**这些测试。「会红」是按旧代码推断的：
//!   接线前的 register 不看治理、不写账、不校任何一格，也没有目录 ⇒ 除正控外每条断言在旧实现下必红。
//! ★ 本体 instance_mode（唯一性）的会红反例在**同目录的 mode_tests.rs**（本文件到 <300 行已满）。

use serde_json::{json, Map, Value};

use crate::core::registry::Registry;
use crate::core::types::{Admit, EventSeq, Reason, Refuse, Registration, Who};
use crate::engine::ledger::Ledger;
use crate::engine::validate::ObjectSpec;
use crate::governance::Governance;

use super::{register_capability, Instances, RegisterEnv};

const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

/// 一张台面：册／本体格／治理／账＋实例表（★ 省得每条测试各写一遍装配）。
struct Fixture {
    reg: Registry,
    spec: ObjectSpec,
    gov: Governance,
    led: Ledger,
    inst: Instances,
}

fn fixture() -> Fixture {
    Fixture {
        reg: Registry::load(ONT).expect("册该装得上"),
        spec: ObjectSpec::load(ONT).expect("本体该装得上"),
        gov: Governance::new(),
        led: Ledger::load(ONT).expect("本体该装得上"),
        inst: Instances::new(),
    }
}

impl Fixture {
    /// 授一项能力（★ 名字由 register_capability 一处派生，测试不自己拼字符串）。
    fn grant(&mut self, kind: &str) {
        self.gov.grant(&who(), register_capability(kind));
    }

    /// 走一次登记（★ 就是把四个协作面凑给 Instances::register）。
    fn register(&mut self, kind: &str, fields: &[(&str, Value)]) -> Admit<EventSeq> {
        let mut env = RegisterEnv::new(&self.reg, &self.spec, &self.gov, &mut self.led);
        self.inst
            .register(&mut env, &who(), &instance(kind, fields))
    }
}

fn who() -> Who {
    Who::new("world://user/zhang")
}

fn instance(kind: &str, fields: &[(&str, Value)]) -> Registration {
    let mut m = Map::new();
    for (k, v) in fields {
        m.insert((*k).to_string(), v.clone());
    }
    Registration::new(kind, m)
}

fn perm_capability(e: &Refuse) -> String {
    match &e.reason {
        Reason::NotPermitted { capability } => capability.clone(),
        other => panic!("期望 NotPermitted，实得 {other:?}"),
    }
}

fn bad_field(e: &Refuse) -> String {
    match &e.reason {
        Reason::BadValue { field, .. } => field.clone(),
        other => panic!("期望 BadValue，实得 {other:?}"),
    }
}

fn missing_field(e: &Refuse) -> String {
    match &e.reason {
        Reason::MissingField { field } => field.clone(),
        other => panic!("期望 MissingField，实得 {other:?}"),
    }
}

/// ★ 反例1：没授过 ⇒ NotPermitted（默认拒），且**不长在册上、不留账**。
#[test]
fn refused_without_grant_writes_nothing() {
    let mut f = fixture();
    let fields = [("name", json!("htop"))];
    let e = f.register("application", &fields).unwrap_err();
    assert_eq!(perm_capability(&e), register_capability("application"));
    assert_eq!(f.inst.count(), 0);
    assert_eq!(f.led.all().len(), 0, "被拒的登记不许留账");
}

/// ★ 反例2（次序）：**治理先于类型名在册** —— 未登记的类型也先给 NotPermitted。
#[test]
fn governance_is_asked_before_the_kind_check() {
    let mut f = fixture();
    let fields = [("name", json!("x"))];
    let e = f.register("frobnicator", &fields).unwrap_err();
    assert_eq!(perm_capability(&e), register_capability("frobnicator"));
    assert_eq!(f.led.all().len(), 0);
}

/// ★ 反例3：授过权、类型仍不在册 ⇒ UnknownKind。
#[test]
fn unregistered_kind_is_refused() {
    let mut f = fixture();
    f.grant("frobnicator");
    let fields = [("name", json!("x"))];
    let e = f.register("frobnicator", &fields).unwrap_err();
    assert_eq!(e.code(), Reason::UnknownKind.code());
    assert_eq!(f.inst.count(), 0);
    assert_eq!(f.led.all().len(), 0);
}

/// ★ 反例4：值类型不对 ⇒ BadValue{state}，且**校验不过就不记账**。
#[test]
fn wrong_value_type_is_refused_and_nothing_is_written() {
    let mut f = fixture();
    f.grant("application");
    let fields = [("name", json!("htop")), ("state", json!(42))];
    let e = f.register("application", &fields).unwrap_err();
    assert_eq!(bad_field(&e), "state");
    assert_eq!(f.inst.count(), 0);
    assert_eq!(f.led.all().len(), 0, "校验不过 ⇒ 不许记账");
}

/// ★ 反例5：取值域不对 ⇒ 拒。
#[test]
fn value_out_of_domain_is_refused() {
    let mut f = fixture();
    f.grant("port");
    let fields = [("name", json!("p1")), ("state", json!("bogus"))];
    let e = f.register("port", &fields).unwrap_err();
    assert_eq!(bad_field(&e), "state");
    assert_eq!(f.led.all().len(), 0);
}

/// ★ 反例6：本体没声明的格 ⇒ 拒。
#[test]
fn undeclared_field_is_refused() {
    let mut f = fixture();
    f.grant("application");
    let fields = [("name", json!("htop")), ("sneaky", json!(1))];
    let e = f.register("application", &fields).unwrap_err();
    assert_eq!(bad_field(&e), "sneaky");
    assert_eq!(f.led.all().len(), 0);
}

/// ★ 反例7：缺本内核最小指认格 name ⇒ MissingField{name}。
#[test]
fn missing_name_is_refused() {
    let mut f = fixture();
    f.grant("application");
    let e = f.register("application", &[]).unwrap_err();
    assert_eq!(missing_field(&e), "name");
    assert_eq!(f.led.all().len(), 0);
}

/// ★ 反例8：同名不许重复登记；第一笔账留着，第二笔不记。
#[test]
fn duplicate_name_is_refused() {
    let mut f = fixture();
    f.grant("application");
    let fields = [("name", json!("htop"))];
    assert!(f.register("application", &fields).is_ok());
    let e = f.register("application", &fields).unwrap_err();
    assert_eq!(e.code(), "worldcore.Refuse.DanglingRef");
    assert_eq!(f.inst.count(), 1);
    assert_eq!(f.led.all().len(), 1);
}

/// 正控：登记成功 ⇒ **同批一笔账**：族 change／what <类>.register／参数带 name／记着谁。
#[test]
fn admitted_register_writes_exactly_one_change_line() {
    let mut f = fixture();
    f.grant("application");
    let fields = [("name", json!("htop"))];
    let seq = f.register("application", &fields).expect("该收下");
    assert_eq!(f.inst.count(), 1);
    assert_eq!(f.led.all().len(), 1, "成功登记必须同批记一笔账");
    let e = f.led.get(seq).expect("账上该有这一笔");
    assert_eq!(e.family, "change");
    assert_eq!(e.what, "application.register");
    assert_eq!(e.param("name").and_then(Value::as_str), Some("htop"));
    assert_eq!(e.who.name(), "world://user/zhang");
}

/// 正控：序号**由账发**（全局单增）⇒ 两笔登记拿到 1、2。
#[test]
fn seqs_come_from_the_ledger() {
    let mut f = fixture();
    f.grant("application");
    f.grant("service");
    let a = f
        .register("application", &[("name", json!("htop"))])
        .expect("第一笔");
    let b = f
        .register("service", &[("name", json!("sshd"))])
        .expect("第二笔");
    assert_eq!((a.0, b.0), (1, 2));
    assert_eq!(f.led.query_family("change").len(), 2);
    assert!(f.led.get(a).is_some());
    assert!(f.led.get(b).is_some());
}

// ==== 新规矩（目录：名字／类）—— 每条一条会红反例 ============================

/// ★★ 会红反例 A（名字目录）：目录必须**服务全键**。
/// 让它红的改法：register 只插主目录、忘了插名字目录 ⇒ get 取不到 ⇒ 红。
#[test]
fn the_name_index_serves_every_key_in_the_catalog() {
    let mut f = fixture();
    f.grant("application");
    f.grant("service");
    f.register("application", &[("name", json!("htop"))])
        .expect("该收下");
    f.register("service", &[("name", json!("sshd"))])
        .expect("该收下");
    let keys: Vec<String> = f.inst.keys().iter().map(|k| (*k).to_string()).collect();
    assert_eq!(keys, ["application:htop", "service:sshd"], "★ 键按全键升序");
    for key in &keys {
        let name = key.split(':').nth(1).expect("键形如 类:名字");
        let got = f.inst.get(name).expect("名字目录里该有这一条");
        assert_eq!(format!("{}:{}", got.0, name), *key, "目录该指回同一个键");
    }
}

/// ★★ 会红反例 B（同名跨类）：名字目录只记「先登记的那一条」⇒ 先登记 surface ⇒ 红。
#[test]
fn a_shared_name_resolves_to_the_smallest_key() {
    let mut f = fixture();
    f.grant("surface");
    f.grant("application");
    f.register("surface", &[("name", json!("x"))])
        .expect("该收下");
    f.register("application", &[("name", json!("x"))])
        .expect("该收下");
    let (kind, _) = f.inst.get("x").expect("同名两条都在册");
    assert_eq!(
        kind, "application",
        "★ 全键序最小：application:x < surface:x"
    );
    assert_eq!(f.inst.count(), 2, "同名跨类是两条（键不同）");
}

/// ★★ 会红反例 C（拒绝不留痕）：被拒的登记不许在目录里留下半条。
#[test]
fn a_refused_register_leaves_no_trace_in_the_index() {
    let mut f = fixture();
    let fields = [("name", json!("htop"))];
    f.register("application", &fields).expect_err("没授过 ⇒ 拒");
    assert!(f.inst.get("htop").is_none(), "被拒的不许进名字目录");
    f.grant("application");
    f.register("application", &fields).expect("授过 ⇒ 收下");
    assert_eq!(f.inst.get("htop").map(|(k, _)| k), Some("application"));
    assert_eq!(f.inst.count(), 1);
    assert_eq!(f.led.all().len(), 1, "只留成功那一笔账");
}
