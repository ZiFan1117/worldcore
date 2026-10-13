//! 门面端到端：**一条真实的路走完八个面**。
//!
//! ⓪ 门面装载 → ①注册 → ②实例 → ③校验 → ④存 → ⑤查 → ⑧治理 → ⑦执行 → ⑥账。
//!
//! ★ 本件**只用** `aios_worldcore::*` 导出的东西（八面 ＋ 共同类型 ＋ 装载入口），
//!   一个子 crate 都不点名 —— 门面漏导出一个面，这里就编不过。
//! ★ 反例在 `blocked_path_leaves_no_trace`：未登记的类型必须**在门口就被挡住**，
//!   而且实例表／存储／账三处**一处痕迹都不许留**。

use aios_worldcore::core::registry::{load_ontology, Registry};
use aios_worldcore::core::types::{EventSeq, Reason, Registration, Who};
use aios_worldcore::engine::execute::{DryRun, Exec};
use aios_worldcore::engine::instances::{register_capability, Instances, RegisterEnv};
use aios_worldcore::engine::ledger::Ledger;
use aios_worldcore::engine::query::Query;
use aios_worldcore::engine::store::Store;
use aios_worldcore::engine::validate::{check_enum, check_shape};
use aios_worldcore::governance::Governance;
use serde_json::{json, Map, Value};

const ONT: &str = include_str!("../../../crates/aios-ontology/data/ontology.json");

fn doc() -> Value {
    serde_json::from_str(ONT).expect("ontology.json 该能解析")
}

fn fields(pairs: &[(&str, Value)]) -> Map<String, Value> {
    let mut m = Map::new();
    for (k, v) in pairs {
        m.insert(k.to_string(), v.clone());
    }
    m
}

fn options_of(kind: &str, field: &str) -> Vec<String> {
    let d = doc();
    let mut out = Vec::new();
    if let Some(list) = d["objects"][kind]["_field_meta"][field]["options"].as_array() {
        for v in list {
            if let Some(s) = v.as_str() {
                out.push(s.to_string());
            }
        }
    }
    out
}

#[test]
fn one_request_walks_all_eight_faces() {
    // ⓪ 门面装载
    let ont = load_ontology(ONT).expect("门面给的装载入口该能用");
    assert!(ont.has_action("job.start"), "本体该登记 job.start");
    assert!(ont.action_names().len() >= 5, "动作名该有一批");
    // ① 注册面
    let r = Registry::load(ONT).expect("注册面该装得上本体");
    assert!(r.has_kind("application"), "application 该在册");
    // ③ 校验面：形状 ＋ 取值域（取值域选项从真实本体取）
    let opts = options_of("application", "state");
    assert!(opts.len() >= 2, "夹具失效：{opts:?}");
    let refs: Vec<&str> = opts.iter().map(String::as_str).collect();
    let row = fields(&[
        ("name", json!("htop")),
        ("state", json!("running")),
        ("did", json!("world://app/htop")),
    ]);
    let reg = Registration::new("application", row);
    let shape = check_shape(&r, &reg);
    shape.expect("形状该过");
    let domain = check_enum(&reg, "state", &refs);
    domain.expect("取值域该过");
    // ② 实例注册面（★ 三个协作面都得给：治理／本体格／账；治理默认拒 ⇒ 先授这一项）
    let who = Who::new("world://user/zhang");
    let spec = aios_worldcore::engine::validate::ObjectSpec::load(ONT).expect("本体该装得上");
    let mut gov = Governance::new();
    gov.grant(&who, register_capability("application"));
    let mut ledger = Ledger::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let seq = {
        let mut env = RegisterEnv::new(&r, &spec, &gov, &mut ledger);
        inst.register(&mut env, &who, &reg).expect("在册类型该收下")
    };
    assert_eq!(seq, EventSeq(1), "序号由账发（第一笔）");
    // ④ 存储面
    let mut store = Store::new();
    let created = store.create("application:htop", reg.clone());
    created.expect("该存得下");
    // ⑤ 查询面
    let mut q = Query::new(&store);
    q = q.filter_kind("application");
    q = q.filter_field("state", "running");
    assert_eq!(q.count(), 1);
    // ⑧ 治理面：默认拒 ⇒ 授权后放行
    let denied = gov.can_execute(&who, "job.start");
    denied.expect_err("没授过必须拒");
    gov.grant(&who, "job.start");
    let allowed = gov.can_execute(&who, "job.start");
    allowed.expect("授过该放行");
    // ⑦ 执行面：治理已授 ＋ 动作在册 ⇒ 交给执行体（今天是 dry-run）
    let ex = Exec::new(&r, &gov, DryRun);
    let ran = ex.execute("job.start", &who, &Map::new());
    let out = ran.expect("在册动作该放行");
    assert_eq!(out, "dry-run:job.start");
    // ⑥ 账：把它记下来（只追加，序号单增）—— ★ 登记面已写过一笔 change，这里就是第二笔
    let params = fields(&[
        ("subject", json!("application:htop")),
        ("result", json!(out)),
    ]);
    let es = ledger
        .append(&who, "act", "job.start", params)
        .expect("在册族该收下");
    assert_eq!(es, EventSeq(2), "第二笔：登记那笔是 1");
    assert_eq!(ledger.all().len(), 2);
    assert_eq!(ledger.query_family("change").len(), 1);
    assert!(ledger.export_csv().contains("job.start"));
}

/// ★★ 反例：**未登记的类型必须在门口就被挡住，且三处零痕迹**。
#[test]
fn blocked_path_leaves_no_trace() {
    let r = Registry::load(ONT).expect("注册面该装得上本体");
    let who = Who::new("world://user/zhang");
    let bad = Registration::new("frobnicator", fields(&[("name", json!("x"))]));
    let shape = check_shape(&r, &bad);
    let e = shape.expect_err("未登记类型必须在门口就拒");
    assert_eq!(e.reason, Reason::UnknownKind);
    // ★ 实例面：治理先问 —— 先授「frobnicator.register」，才走得到「查在册」那一条
    let spec = aios_worldcore::engine::validate::ObjectSpec::load(ONT).expect("本体该装得上");
    let mut gov = Governance::new();
    gov.grant(&who, register_capability("frobnicator"));
    let mut ledger = Ledger::load(ONT).expect("本体该装得上");
    let mut inst = Instances::new();
    let e2 = {
        let mut env = RegisterEnv::new(&r, &spec, &gov, &mut ledger);
        inst.register(&mut env, &who, &bad)
            .expect_err("实例面也必须拒")
    };
    assert_eq!(e2.reason, Reason::UnknownKind);
    let store = Store::new();
    assert_eq!(inst.count(), 0, "实例表：零痕迹");
    assert_eq!(store.count(), 0, "存储：零痕迹");
    assert_eq!(
        ledger.all().len(),
        0,
        "账：零痕迹（登记被拒 ⇒ 连账都不许写）"
    );
}
