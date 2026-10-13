//! 面②「登记」的本体口径**唯一性**（instance_mode）—— 会红反例与正控。
//!
//! ★ 为什么单开一件：instances/tests.rs 已接近「每文件 < 300 行」的硬上限。
//! ★ **如实登记**：宿主**无 cargo** ⇒ 本席**没跑过**这些测试；「会红」是按旧实现推断的。

use serde_json::{json, Value};

use crate::core::registry::Registry;
use crate::core::types::{Admit, EventSeq, Reason, Refuse, Registration, Who};
use crate::engine::ledger::Ledger;
use crate::engine::validate::ObjectSpec;
use crate::governance::Governance;

use super::{register_capability, Instances, RegisterEnv};

const ONT: &str = include_str!("../../../../../crates/aios-ontology/data/ontology.json");

/// ★ 合成本体：一个 one 类（widget）＋ 一个 many 类（thing），两类的格都声明了 name。
/// ★ 为什么用合成件：真本体的唯一类 ledger **没声明 name 格**（见最后那条现状钉子）。
const SYNTH: &str = r#"{
  "objects": {
    "widget": {"fields": {"name": "string"}, "instance_mode": "one"},
    "thing": {"fields": {"name": "string"}, "instance_mode": "many"}
  },
  "links": {}, "interfaces": {}, "actions": {}, "functions": {},
  "families": {"change": {}}
}"#;

/// 一张台面：册／本体格／治理／账＋实例表（★ 本体文本由调用方给）。
struct Fixture {
    reg: Registry,
    spec: ObjectSpec,
    gov: Governance,
    led: Ledger,
    inst: Instances,
}

fn fixture_of(text: &str) -> Fixture {
    Fixture {
        reg: Registry::load(text).expect("册该装得上"),
        spec: ObjectSpec::load(text).expect("本体该装得上"),
        gov: Governance::new(),
        led: Ledger::load(text).expect("本体该装得上"),
        inst: Instances::new(),
    }
}

impl Fixture {
    /// 授一项能力（★ 名字由 register_capability 一处派生）。
    fn grant(&mut self, kind: &str) {
        self.gov.grant(&who(), register_capability(kind));
    }

    /// 走一次登记（★ 四个协作面凑给 Instances::register）。
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
    let mut m = serde_json::Map::new();
    for (k, v) in fields {
        m.insert((*k).to_string(), v.clone());
    }
    Registration::new(kind, m)
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

/// ★★ 会红反例 D（唯一性）：one 的类**第二个 ⇒ 拒**，且**不长在册、不留账**。
/// 让它红的改法：register 不读 instance_mode（旧实现就是）⇒ 第二个也收下 ⇒ 红。
#[test]
fn a_second_instance_of_a_unique_kind_is_refused() {
    let mut f = fixture_of(SYNTH);
    f.grant("widget");
    f.register("widget", &[("name", json!("only"))])
        .expect("第一个该收下");
    let e = f
        .register("widget", &[("name", json!("second"))])
        .unwrap_err();
    assert_eq!(e.reason, Reason::OverInstanceLimit { limit: 1 });
    assert_eq!(f.inst.count(), 1, "被拒的不许进册");
    assert_eq!(f.led.all().len(), 1, "被拒的不许留账");
}

/// 正控（D 的另一半）：many 的类第二个照收（★ 证明 many 不受影响）。
#[test]
fn a_second_instance_of_a_many_kind_is_admitted() {
    let mut f = fixture_of(SYNTH);
    f.grant("thing");
    f.register("thing", &[("name", json!("a"))])
        .expect("第一个");
    f.register("thing", &[("name", json!("b"))])
        .expect("第二个（many 不限）");
    assert_eq!(f.inst.count(), 2);
    assert_eq!(f.led.all().len(), 2);
}

/// ★ 读本体口径的钉子：ObjectSpec 必须把 instance_mode 读出来。
/// 让它红的改法：去掉 spec.rs 里 modes 那一栏 ⇒ 本用例红（编译不过）。
#[test]
fn the_spec_reads_instance_mode_from_the_ontology() {
    let spec = ObjectSpec::load(ONT).expect("本体该装得上");
    assert_eq!(
        spec.instance_mode("ledger"),
        Some("one"),
        "本体说 ledger 唯一"
    );
    assert_eq!(
        spec.instance_mode("application"),
        Some("many"),
        "本体说它多例"
    );
    assert_eq!(
        spec.instance_mode("frobnicator"),
        None,
        "不在册 ⇒ 没有 mode"
    );
}

/// ★ 现状钉子（真本体缺口，**接不上**）：ledger 唯一，可本体没给它 name 格 ⇒ **第一个都进不去**。
/// ★ 本体一旦给 ledger 补上 name 格（或「最小指认格」改成本体声明里能指认的那一格）
///   ⇒ 本用例红 ⇒ 那时把 D 换回真本体跑。
#[test]
fn the_real_unique_kind_cannot_be_registered_today() {
    let mut f = fixture_of(ONT);
    f.grant("ledger");
    let named = f
        .register("ledger", &[("name", json!("main"))])
        .unwrap_err();
    assert_eq!(bad_field(&named), "name", "本体没给 ledger 声明 name 格");
    let unnamed = f.register("ledger", &[]).unwrap_err();
    assert_eq!(missing_field(&unnamed), "name", "本内核最小指认格缺");
    assert_eq!(f.inst.count(), 0, "两条路都进不去");
    assert_eq!(f.led.all().len(), 0, "两条路都不留账");
}
