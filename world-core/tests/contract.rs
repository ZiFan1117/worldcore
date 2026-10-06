//! **契约与失败路径测试**（2026-09-26 新增）。
//!
//! 本文件是为 `WC-RV-R2-001` 指出的"**判据零测试却记『已实现』**"而补的：
//! 四个独立评审角色一致发现，本项目的信心高于它的证据——
//! `trace_matrix.py` 只校验用例编号的**格式**，从不校验"这条用例是否真的
//! 验证了这条需求"，于是"已实现"在 `RTM_STRICT=false` 的窗口里
//! 是一个**门禁查不出真假**的字段。
//!
//! 这里补的全是**会失败的检查**：
//! - `c01` `change` 必须过门禁（`REQ-F-015`，修 S-01 后**必须**有回归）
//! - `c02` 信封 8 个必填字段**逐字段**被拦（`REQ-F-002`，此前零覆盖）
//! - `c03` `Policy::load` 的 5 类拒启分支（此前 `Policy::load` 在测试中从未被调用）
//! - `c04` 本体缺失 / 家族为空（`REQ-N-003`，此前只测了"坏 JSON"与"缺版本"）
//! - `c05` 事件 `id` 唯一性（`QG-01` 判定项 ④ 依赖它，此前无任何测试）
//! - `c06` 增量折叠与全量折叠一致（`REQ-F-010` 的判据原本**不可判定**）

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::{common::event, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-contract-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    d
}

fn ontology() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/ontology_definition/ontology.json")
}

fn policy() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json")
}

/// 写一份**合法**的临时策略（含 `writes` 段——默认拒绝要求它必须存在）。
///
/// ⚠️ **本批起是两层**（能力层 ＋ 动作层）：`capabilities.<名字>.kind` 与
/// `actions.<动作>.capability`。夹具按两层写，与出厂 `policy.json` 同形
/// （判据见 `src/gate/mod.rs::Policy::load`）。
fn write_policy(dir: &Path, name: &str, body: &Value) -> PathBuf {
    let p = dir.join(name);
    fs::write(&p, serde_json::to_string_pretty(body).unwrap()).unwrap();
    p
}

fn valid_policy_json() -> Value {
    json!({
        "policy": 1,
        "capabilities": { "notice.mute": { "kind": "invoke" } },
        "actions": { "notice.mute": { "capability": "notice.mute", "reversible": true } },
        "subjects": { "allow": ["world://user"] },
        "writes": { "world://user": ["world://*"] }
    })
}

/// **c01**：`change` 必须过门禁——`act` 的效果不能靠 `change` 偷渡。
///
/// 这是 `WC-RV-R2-001` **FIND-01**（安全评审 S-01）的回归测试。
/// 修复前：`change` 只过本体形状校验，于是"被拒绝的动作"可以用一条
/// `change` 静默达成。修复后由 `Policy::authorize_write` 拦截。
#[test]
fn c01_change_is_gated_and_cannot_smuggle_an_act() {
    let d = tmpdir("c01");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // 主人对自己世界的直接写入：允许
    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(false)),
    )
    .unwrap();

    // agent 想用 change 达成"静音"效果：必须被拒
    let err = w
        .commit(
            "change",
            "world://agent/1",
            event::change_body("world://notice/n-1", "muted", json!(false), json!(true)),
        )
        .unwrap_err();
    assert!(err.contains("门禁拒绝写入"), "实得: {err}");

    // 判据 2：状态没有被改
    let s = w.read_model().unwrap();
    assert_eq!(
        s.get("world://notice/n-1", "muted"),
        Some(&json!(false)),
        "被拒的 change 绝不允许改状态"
    );

    // 判据 3：留下可检索的流水
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 2, "1 条合法 change + 1 条拒绝流水");
    assert_eq!(all[1]["body"]["type"], json!("gate.write-rejected"));
    assert_eq!(all[1]["body"]["subject"], json!("world://agent/1"));
}

/// 从信封错误串里**定位**「缺少必填字段 `<名字>`」点到的那个名字。
///
/// 取不到标记、或反引号没闭合 ⇒ **当场 panic**（不返回空串当通过）：
/// 一条"读不到就当成没问题"的判据正是本项目反复判红的那种装饰。
fn named_field_in(msg: &str) -> &str {
    const MARK: &str = "缺少必填字段 `";
    let start = msg
        .find(MARK)
        .unwrap_or_else(|| panic!("错误串没有点名缺失字段的标记 `{MARK}`：{msg}"))
        + MARK.len();
    let rest = &msg[start..];
    let end = rest
        .find('`')
        .unwrap_or_else(|| panic!("字段名没有闭合的反引号：{msg}"));
    &rest[..end]
}

/// **c02**：信封的 8 个必填字段**逐字段**被拦，且报出字段名。
///
/// 此前 `ontology.rs` 的信封必填循环**零覆盖**（该文件单元测试只测 `vocab_hash`），
/// 而 RTM 把 `REQ-F-002` 记为"已实现"并引用了两条不相干的用例。
///
/// ## 2.3 的反假（这一条原来是个恒真判据）
///
/// 原断言是 `msg.contains("MissingField") && msg.contains(field)`。
/// 对 `field == "world"` 而言，**前半段本身就含 `world`**——错误码前缀
/// `ext.world.Ontology.MissingField` 里那个 `world` 让后半段**恒真**：
/// 无论删的是哪个字段，`contains("world")` 都成立（本用例末尾的对照把它钉住）。
/// 现在改成**定位那个 token**：反引号之间必须逐字等于被删的字段名。
#[test]
fn c02_every_required_envelope_field_is_enforced() {
    let ont = world_core::ontology_definition::Ontology::load(&ontology()).unwrap();
    let required = ["world", "kind", "id", "seq", "at", "actor", "flags", "body"];

    for field in required {
        let mut ev = event::new_event(
            1,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(null), json!(1)),
        );
        ev.as_object_mut().unwrap().remove(field);
        let e = ont.validate(&ev).unwrap_err();
        let msg = format!("{e}");
        assert!(msg.contains("MissingField"), "实得: {msg}");
        // 2.3：**不许用 contains**——必须定位到「缺少必填字段 `<名字>`」里的那个 token。
        assert_eq!(
            named_field_in(&msg),
            field,
            "错误串点名的字段必须**逐字**是被删掉的那个，实得: {msg}"
        );
    }

    // 上面那条判据的**反假证据**：删掉 `seq`（与 `world` 无关的字段），
    // 错误串**照样**含 `world`——因为码前缀 `ext.world.` 自带它。
    // ⇒ `contains("world")` 在这一格恒真，它证明不了"报出了字段名"。
    let mut other = event::new_event(
        1,
        "change",
        "world://user",
        event::change_body("world://s", "p", json!(null), json!(1)),
    );
    other.as_object_mut().unwrap().remove("seq");
    let msg_other = format!("{}", ont.validate(&other).unwrap_err());
    assert!(
        msg_other.contains("world"),
        "本对照的前提是「码前缀里含 world」：{msg_other}"
    );
    assert_ne!(
        named_field_in(&msg_other),
        "world",
        "删的是 `seq`，点名的却是 `world` ⇒ token 定位没在读那个位置：{msg_other}"
    );
    assert_eq!(named_field_in(&msg_other), "seq", "实得: {msg_other}");

    // 对照：完整信封必须通过（否则上面的断言可能因"什么都拒"而假通过）
    let ok = event::new_event(
        1,
        "change",
        "world://user",
        event::change_body("world://s", "p", json!(null), json!(1)),
    );
    assert!(ont.validate(&ok).is_ok(), "完整信封不应被拒");

    // 顺带覆盖另两条形状分支：body 不是对象 / 未知家族
    let mut bad_body = ok.clone();
    bad_body["body"] = json!("不是对象");
    assert!(format!("{}", ont.validate(&bad_body).unwrap_err()).contains("MissingField"));

    let unknown = event::new_event(1, "guess", "world://user", json!({}));
    assert!(format!("{}", ont.validate(&unknown).unwrap_err()).contains("UnknownKind"));
}

/// **c03**：`Policy::load` 的 6 类拒启分支（此前该方法在测试中**从未被调用**）。
///
/// 第 ⑥ 类（**策略文件缺失**）由任务 2.5 补：它此前零断言，而它正是
/// "法律读不到就不许起"这条纪律的入口。
///
/// 原第 ⑤ 类"可逆与需批准矛盾 ⇒ 拒载"已随 `WC-R4-DISP-001` §三 **E-5**
/// 裁定①（**删 `requires_approval` 字段**）一并删除；未知/多余键改为
/// **被忽略**，其回归见本用例末尾的「对照②」。
#[test]
fn c03_policy_load_rejects_every_malformed_shape() {
    use world_core::gate::{Decision, Policy};
    let d = tmpdir("c03");

    // ① 坏 JSON
    let p = d.join("bad-json.json");
    fs::write(&p, "{ not json").unwrap();
    assert!(Policy::load(&p).is_err(), "坏 JSON 必须被拒");

    // ② 缺 `policy` 版本
    let mut v = valid_policy_json();
    v.as_object_mut().unwrap().remove("policy");
    let p = write_policy(&d, "no-version.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(e.contains("policy"), "实得: {e}");

    // ③ 能力表为空（**能力层**空 ⇒ 拒启）
    let mut v = valid_policy_json();
    v["capabilities"] = json!({});
    let p = write_policy(&d, "empty-caps.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(e.contains("capabilities"), "实得: {e}");

    // ③b 动作表为空（**动作层**空 ⇒ 拒启；两层各自成判，不合并）
    let mut v = valid_policy_json();
    v["actions"] = json!({});
    let p = write_policy(&d, "empty-actions.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(e.contains("actions"), "实得: {e}");

    // ③c ★ **动作引用了不存在的能力** ⇒ 拒启（本批新立的判据）
    let mut v = valid_policy_json();
    v["actions"]["notice.mute"]["capability"] = json!("no.such.capability");
    let p = write_policy(&d, "dangling-action.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(
        e.contains("ext.world.Gate.ActionCapabilityUnknown") && e.contains("no.such.capability"),
        "悬空的动作必须被拒且点名那个能力，实得: {e}"
    );

    // ④ 白名单为空
    let mut v = valid_policy_json();
    v["subjects"] = json!({ "allow": [] });
    let p = write_policy(&d, "empty-allow.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(e.contains("subjects.allow"), "实得: {e}");

    // ⑤ 缺 `writes` 段（默认拒绝要求它必须存在）
    let mut v = valid_policy_json();
    v.as_object_mut().unwrap().remove("writes");
    let p = write_policy(&d, "no-writes.json", &v);
    let e = Policy::load(&p).unwrap_err();
    assert!(e.contains("writes"), "实得: {e}");

    // ⑥ **策略文件缺失**（任务 2.5）：`Policy::load` 的"读不到"分支此前零断言。
    //
    // 为什么要断言**理由**而不是只断言 `is_err()`：这条出口的错误**不带**
    // `ext.world.` 码（属"已知无码出口"，见 `c24`），所以能判的东西只剩"它说了什么"。
    // 只写 `is_err()` 的判据在**fail-open 变异**下是假的绿：把读取失败吞掉
    // （`unwrap_or_else(|_| "{}")` 之类）之后，加载照样会失败——只是**理由换了**，
    // 于是 `is_err()` 仍为真，而"文件缺失"这件事已经没人报了。
    let missing = d.join("no-such-policy.json");
    let e = Policy::load(&missing).unwrap_err();
    assert!(
        e.contains("无法读取") && e.contains("no-such-policy.json"),
        "策略文件缺失必须报「无法读取 <路径>」，实得: {e}"
    );

    // 对照①：合法策略必须能加载（否则"什么都拒"会假通过）
    let p = write_policy(&d, "ok.json", &valid_policy_json());
    assert!(Policy::load(&p).is_ok(), "合法策略不应被拒");

    // 对照②：能力项里的**多余/未知键被忽略**——`weird` 带的是刚被删除的
    // `requires_approval`（旧策略文件的兼容面），`odd` 带的是一个从来就不认识的键。
    //
    // 为何是"应能加载"而不是"应被拒载"（E-5 裁定①"删字段"）：
    // `Policy::load` 用 `serde_json::Value` **手工取值**——`let root: Value =
    // serde_json::from_str(..)` 之后逐键 `spec.get("kind")`（`src/gate/mod.rs`
    // 「`capabilities` 解析」段）；`gate.rs` 里**没有任何 `#[derive(Deserialize)]`
    // 结构**，也就无从施加 `deny_unknown_fields`（`grep -rn "Deserialize" world-core/src/` = 0 命中）
    // ⇒ 未知键既不导致拒载、也不参与裁决。本用例同时是"旧策略文件带着
    // `requires_approval` 仍能加载"的兼容回归。
    let mut v = valid_policy_json();
    v["capabilities"] = json!({
        "weird": { "kind": "invoke", "requires_approval": true },
        "odd": { "kind": "invoke", "totally_unknown_key": 1 }
    });
    v["actions"] = json!({
        "weird": { "capability": "weird", "reversible": true },
        "odd": { "capability": "odd", "reversible": true }
    });
    let p = write_policy(&d, "extra-keys-ignored.json", &v);
    let pol = Policy::load(&p).expect("多余键应被忽略，而不是拒载");
    // 裁决只看**动作**的 `reversible` + `irreversible_actors`：多余键不得改变结论
    // （`verb` 可省，`decide` 取不到时按 `-` 处理，见 `src/gate/mod.rs`）。
    let act = json!({ "capability": "weird", "verb": "do" });
    assert_eq!(
        pol.decide("world://user", &act),
        Decision::Allow,
        "多余键不得影响裁决"
    );
}

/// **c04**：本体"文件缺失"与"家族为空"两条拒启分支。
///
/// ⚠️ **本批改了两次夹具**，理由都是"法律多加了一条，夹具就得跟"：
/// 1. 五要素节存在性判据（`check_sections`）排在家族检查**之前** ⇒ 这份最小本体必须**五节齐备**；
/// 2. ★ **十二节归属表判据**（`check_section_map`）同样排在家族检查之前 ⇒ 它还必须有
///    `_section_map`，且表里声明的 `_` 分节键集合要**逐项等于**这份文件里实际的 `_` 分节。
///    （本夹具的"对象"只写在**冻结映射** `concepts` 里、没有 `_objects` ⇒ 那一项按
///    `keys: []` ＋ `_where` 声明——这正是该判据允许的形态。）
///
/// 两条都**不改**本用例要验的那件事：家族列表为空 ⇒ `NoFamilies`。
#[test]
fn c04_ontology_load_rejects_missing_file_and_empty_families() {
    use world_core::ontology_definition::Ontology;
    let d = tmpdir("c04");

    // ① 文件不存在
    let missing = d.join("nope.json");
    let e = Ontology::load(&missing).unwrap_err();
    assert!(e.contains("ReadFail"), "实得: {e}");

    // ② 家族为空（其余各节齐备，好让拒启的**唯一理由**是家族为空）
    let p = d.join("no-families.json");
    fs::write(
        &p,
        serde_json::to_string(&json!({
            "world": 1,
            "envelope": { "required": ["world"], "optional": [] },
            "families": {},
            "concepts": { "t": { "fields": { "f": "string" } } },
            "_links": { "r": { "from": "t", "to": "t", "card": "many" } },
            "_interfaces": { "cap": { "kind": "read" } },
            "_actions": { "act": { "capability": "cap", "reversible": true } },
            "_functions": { "entries": {} },
            "_permissions": { "default": "deny" },
            "_section_map": {
                "_homes": [
                    "对象（Object）", "关系（Link）", "接口·能力（Interface）",
                    "动作（Action）", "函数（Function）"
                ],
                "_not_domain_sections": { "_note": "夹具：说明格", "_section_map": "本表自己" },
                "sections": {
                    "类型（对象）": {
                        "home": "对象（Object）", "attach": "full",
                        "keys": [], "_where": "冻结映射 `concepts`（本夹具不设 `_objects`）"
                    },
                    "关系": { "home": "关系（Link）", "attach": "full", "keys": ["_links"] },
                    "接口·能力": {
                        "home": "接口·能力（Interface）", "attach": "full", "keys": ["_interfaces"]
                    },
                    "动作": { "home": "动作（Action）", "attach": "full", "keys": ["_actions"] },
                    "函数入口": {
                        "home": "函数（Function）", "attach": "half", "keys": ["_functions"],
                        "_why_half": "夹具：只挂引用那一半"
                    },
                    "许可条文": {
                        "home": "接口·能力（Interface）", "attach": "half", "keys": ["_permissions"],
                        "_why_half": "夹具：授权不是能力"
                    }
                }
            }
        }))
        .unwrap(),
    )
    .unwrap();
    let e = Ontology::load(&p).unwrap_err();
    assert!(e.contains("NoFamilies"), "实得: {e}");
}

/// **c05**：事件 `id` 唯一性（`WC-SQAP-001` 的 M-01 判定项 ④ 依赖它）。
///
/// `new_id()` = 纳秒 + 进程内计数器；计数器每次启动从 0 开始，
/// 故"跨重启唯一"依赖纳秒不重复——本测试覆盖**同进程内**的唯一性。
#[test]
fn c05_event_ids_are_unique_within_a_process() {
    let mut seen = std::collections::BTreeSet::new();
    for i in 0..2000u64 {
        let ev = event::new_event(
            i + 1,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(null), json!(i)),
        );
        let id = ev["id"].as_str().unwrap().to_string();
        assert!(seen.insert(id.clone()), "事件 id 重复：{id}");
    }
    assert_eq!(seen.len(), 2000);
}

/// **c06**：**增量折叠**与**全量折叠**结果一致（`REQ-F-010` 的判据）。
///
/// 此前该判据**不可判定**：判据要求"重算与增量折叠一致"，
/// 而代码没有增量路径（`read_model()` 每次全量 fold），
/// 被比较的一方不存在 ⇒ 该判据永远无法失败（`WC-RV-R2-001` FIND-10）。
/// 本测试用 `State::apply` 逐条喂入构造出真正的增量路径，
/// 于是"增量 == 全量"成为**可失败**的断言。
#[test]
fn c06_incremental_apply_equals_full_fold() {
    use world_core::ontology_instance::readmodel::State;

    let d = tmpdir("c06");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        for i in 0..5 {
            w.commit(
                "change",
                "world://user",
                event::change_body(
                    &format!("world://notice/n-{i}"),
                    "muted",
                    json!(null),
                    json!(i % 2 == 0),
                ),
            )
            .unwrap();
        }
        w.commit(
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-c06", json!({})),
        )
        .unwrap();
    }

    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let all = w.ledger().read_all().unwrap();

    // 全量：一次 fold
    let full = State::fold(&all).unwrap();

    // 增量：逐条 apply（这才是"边写边算"的真实形态）
    let mut inc = State::new();
    for ev in &all {
        inc.apply(ev).unwrap();
    }

    assert_eq!(
        inc.to_json().to_string(),
        full.to_json().to_string(),
        "增量折叠与全量折叠必须逐字节一致"
    );
    assert_eq!(inc.digest(), full.digest());

    // 反假测试：只喂前缀必须得到不同结果（否则两者相同可能只是"都没算"）
    let mut prefix = State::new();
    for ev in &all[..2] {
        prefix.apply(ev).unwrap();
    }
    assert_ne!(
        prefix.to_json().to_string(),
        full.to_json().to_string(),
        "前缀折叠竟与全量相同 ⇒ 这个断言没有在真的比什么"
    );
}

/// **c07**：**同一本账本不能有两个写者**（`WC-RV-R2-001` FIND-08 / 假设 `A-01`）。
///
/// 为什么这条是 P0 级：CLI 每条命令都是新进程，而 `next_seq` 只在内存里。
/// 两个写者各自取号 ⇒ 重号或半写交错 ⇒ 下次启动 `SeqGap` 拒启、**世界锁死**。
#[test]
fn c07_second_writer_is_refused() {
    let d = tmpdir("c07");
    let lp = d.join("ledger.jsonl");

    let first = World::open(&ontology(), &lp, &policy()).expect("第一个写者应能打开");
    let err = World::open(&ontology(), &lp, &policy()).expect_err("第二个写者必须被拒绝");
    assert!(err.contains("Ledger.Locked"), "实得: {err}");
    assert!(err.contains("单写者"), "理由里要写清为什么：{err}");

    // 释放第一个写者（Drop 删锁）后，第二个必须能拿到
    drop(first);
    assert!(
        World::open(&ontology(), &lp, &policy()).is_ok(),
        "锁随 Drop 释放后应能重新打开"
    );
}

/// **c08**：**陈旧锁可自动回收**（崩溃遗留的锁不能把世界永久锁死）。
#[test]
fn c08_stale_lock_is_reclaimed() {
    let d = tmpdir("c08");
    let lp = d.join("ledger.jsonl");
    let lock = lp.with_extension("lock");

    // 造一个"持有者已不存在"的锁：pid 用一个几乎不可能存在的值
    fs::write(&lock, "999999999\n").unwrap();
    assert!(lock.exists());

    let w = World::open(&ontology(), &lp, &policy()).expect("陈旧锁应被回收，不应永久阻塞");
    assert_eq!(w.ledger().last_seq(), 0);
    // 回收后锁文件由新持有者重建（内容是本进程 pid）
    let content = fs::read_to_string(&lock).unwrap_or_default();
    assert_eq!(
        content.trim(),
        std::process::id().to_string(),
        "锁文件应记录当前持有者 pid"
    );
}

// ────────────────── 静态墙加固（round 11：FIND-04 / A-05）──────────────────

/// **c09**：法律或真相是**符号链接**时拒绝启动（`FIND-04` / `S-05`）。
///
/// 为什么：`fs::metadata` 跟随链接 ⇒"检查的"与"真正读的"可能不是同一个文件，
/// 静态墙被绕过。
///
/// ## 2.5 补的那一半：**本体**软链
///
/// 原来只走 `policy.json`（法律之**权限**）；**本体**（法律之**形状**）软链那条路径
/// 一次都没人走过。两条路径调的是同一个 `guard::assert_not_symlink`，但
/// "同一个函数"不等于"两条调用点都在"——把 `Ontology::load` 里那次调用整行删掉，
/// 原来这个用例**照样全绿**（本文件末尾这两条断言就是为了让它变红）。
#[cfg(unix)]
#[test]
fn c09_symlinked_law_is_refused() {
    use std::os::unix::fs::symlink;
    let d = tmpdir("c09");
    let lp = d.join("ledger.jsonl");

    // 真本体放在别处，policy.json 用软链指向它
    let real = d.join("real-policy.json");
    fs::copy(policy(), &real).unwrap();
    let link = d.join("src/gate/policy.json");
    fs::create_dir_all(link.parent().unwrap()).unwrap();
    symlink(&real, &link).unwrap();

    let err = World::open(&ontology(), &lp, &link).expect_err("指向别处的策略软链必须被拒绝");
    assert!(err.contains("符号链接"), "实得: {err}");

    // 对照：真实文件不得被拒（否则上面的断言可能因"什么都拒"而假通过）
    let copy = d.join("policy-real.json");
    fs::copy(policy(), &copy).unwrap();
    assert!(
        World::open(&ontology(), &lp, &copy).is_ok(),
        "真实文件不应被拒"
    );

    // ── 2.5 的另一半：**本体**是软链也必须拒启（法律之形状，与上面策略同一条墙）──
    //
    // 专用账本：上面对照已经用过 `lp`，这里换个路径，免得"起不来"的理由
    // 与"账本被另一个写者占着"混在一起（那会让本断言失去判别力）。
    let lp2 = d.join("ledger2.jsonl");
    let real_ont = d.join("real-ontology.json");
    fs::copy(ontology(), &real_ont).unwrap();
    let ont_link = d.join("ontology-link.json");
    symlink(&real_ont, &ont_link).unwrap();

    let err = World::open(&ont_link, &lp2, &policy()).expect_err("指向别处的本体软链必须被拒绝");
    assert!(err.contains("符号链接"), "实得: {err}");
    assert!(
        err.contains("本体"),
        "理由必须点名是本体这条（法律·形状），实得: {err}"
    );
    // 对照：把内容**真放**到该路径上，同一次启动必须成功（证明上面拒的是"链接"这件事）
    let real_copy = d.join("ontology-real.json");
    fs::copy(ontology(), &real_copy).unwrap();
    assert!(
        World::open(&real_copy, &lp2, &policy()).is_ok(),
        "真实本体文件不应被拒"
    );
}

/// **c10**：**属主断言**（假设 `A-05`：静态墙只看 mode，属主必须另行断言）。
///
/// 它是**部署方的自证工具**，不是自动安全机制——没人传 `expected_uid` 时不会运行。
#[cfg(unix)]
#[test]
fn c10_owner_assertion_detects_wrong_owner() {
    use std::os::unix::fs::MetadataExt;
    use world_core::gate::guard;

    let d = tmpdir("c10");
    let f = d.join("law.json");
    fs::copy(policy(), &f).unwrap();

    let my_uid = fs::metadata(&f).unwrap().uid();
    assert!(
        guard::assert_owned_by(&f, my_uid, "法律").is_ok(),
        "属主相符应通过"
    );

    let wrong = my_uid.wrapping_add(1);
    let err = guard::assert_owned_by(&f, wrong, "法律").expect_err("属主不符必须被拒");
    assert!(err.contains("属主断言未通过"), "实得: {err}");
    assert!(
        err.contains("属主永远能"),
        "理由要说清为什么属主重要：{err}"
    );
}

/// **c11**：不可逆动作有**治理出口**，且措辞不骗人（`FIND-12` / `DEBT-07`）。
///
/// 此前 `!reversible` 一律 `AwaitApproval`，而 `commit` 收到即 `Err`，
/// 仓内没有批准命令/批准事件/消费路径 ⇒ 不可逆能力在 v1 **永远无法执行**。
/// v1 的明确规则：**只允许 `irreversible_actors` 白名单里的主体执行**；
/// 其他主体收到的理由必须**明说"没有审批通道，不要等批准"**。
#[test]
fn c11_irreversible_is_owner_only_and_the_refusal_does_not_lie() {
    let d = tmpdir("c11");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // ① 白名单主体（世界的主人）可以执行不可逆动作 —— 它不是死号
    let ok = w
        .commit(
            "act",
            "world://user",
            event::act_body("ledger.compact", "do", "r-c11a", json!({})),
        )
        .expect("主人应当能执行不可逆动作（否则该能力是死号）");
    assert_eq!(ok["kind"], json!("act"));

    // ② agent 拿到摩擦，且理由里**明说 v1 没有审批通道**
    let err = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("ledger.compact", "do", "r-c11b", json!({})),
        )
        .expect_err("agent 不得执行不可逆动作");
    assert!(err.contains("不可逆"), "实得: {err}");
    assert!(
        err.contains("没有审批通道") && err.contains("不要等批准"),
        "理由必须说清 v1 无审批通道，否则会让人以为等等就能批：{err}"
    );

    // ③ 仍然留痕（拦得住也记得下）
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 2, "1 条 act + 1 条加摩擦流水");
    assert_eq!(all[1]["body"]["type"], json!("gate.awaiting-approval"));
}

// ────────────────── M08 检查点（round 15：REQ-F-021）──────────────────

/// **c12**：快照是**缓存**——删掉它必须没有任何后果。
///
/// 四条判据一起成立，才叫"缓存"而不是"第二真相"：
/// 1. **续算 == 全量**：有快照的快路径与无快照的全量折叠**逐字节相同**；
/// 2. **删掉无后果**：把快照文件删掉再算，结果仍相同（第三条专属测试的加强形态）；
/// 3. **必须带 `base_seq`**：快照声明折叠到哪一条为止；
/// 4. **可被核验**：`verify` 拿账本重算，指纹一致才通过。
#[test]
fn c12_checkpoint_is_a_cache_and_disposable() {
    use world_core::ontology_instance::checkpoint::{read_model_with_checkpoint, Checkpoint};

    let d = tmpdir("c12");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        for i in 0..4 {
            w.commit(
                "change",
                "world://user",
                event::change_body(
                    &format!("world://notice/n-{i}"),
                    "muted",
                    json!(null),
                    json!(i % 2 == 0),
                ),
            )
            .unwrap();
        }
        w.commit(
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-c12", json!({})),
        )
        .unwrap();
    }

    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let all = w.ledger().read_all().unwrap();
    let full = read_model_with_checkpoint(&all, None).unwrap();

    // 在第 2 条处截一张快照
    let prefix = world_core::ontology_instance::readmodel::State::fold(&all[..2]).unwrap();
    let cp = Checkpoint::capture(&prefix);
    assert_eq!(cp.base_seq(), 2, "快照必须声明它折叠到哪一条");

    // 判据 1：续算 == 全量（逐字节）
    let resumed = read_model_with_checkpoint(&all, Some(&cp)).unwrap();
    assert_eq!(
        resumed.to_json().to_string(),
        full.to_json().to_string(),
        "有快照的续算必须与全量折叠逐字节相同"
    );

    // 判据 4：核验通过
    cp.verify(&all).expect("快照应当能通过账本核验");

    // 判据 2：落盘 → 重新载入 → 结果不变；**删掉文件**再算仍不变
    let cp_path = d.join("checkpoint.json");
    cp.write(&cp_path).unwrap();
    let reloaded = Checkpoint::load(&cp_path).unwrap();
    assert_eq!(reloaded.base_seq(), 2);
    assert_eq!(reloaded.digest(), cp.digest());
    let from_disk = read_model_with_checkpoint(&all, Some(&reloaded)).unwrap();
    assert_eq!(from_disk.to_json().to_string(), full.to_json().to_string());

    fs::remove_file(&cp_path).unwrap();
    assert!(!cp_path.exists());
    let after_delete = read_model_with_checkpoint(&all, None).unwrap();
    assert_eq!(
        after_delete.to_json().to_string(),
        full.to_json().to_string(),
        "删掉快照后重算必须与有快照时一致——否则快照就是第二真相"
    );
}

/// **c13**：坏快照必须被**拒绝使用**，而不是被默默吞下。
///
/// 三类坏法：① 指纹被篡改（缓存与账本不符）② `base_seq` 超过账本长度（陈旧/伪造）
/// ③ 文件不是合法 JSON。
#[test]
fn c13_bad_checkpoints_are_refused() {
    use world_core::ontology_instance::checkpoint::Checkpoint;

    let d = tmpdir("c13");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
        )
        .unwrap();
    }
    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let all = w.ledger().read_all().unwrap();

    // ① 篡改指纹
    let mut doc: serde_json::Value = serde_json::from_str(
        &serde_json::to_string(&json!({
            "checkpoint": 1,
            "base_seq": 1,
            "digest": "fnv1a64:0000000000000000",
            "state": world_core::ontology_instance::readmodel::State::fold(&all).unwrap().to_json(),
        }))
        .unwrap(),
    )
    .unwrap();
    let tampered_path = d.join("tampered.json");
    fs::write(&tampered_path, serde_json::to_string(&doc).unwrap()).unwrap();
    let bad = Checkpoint::load(&tampered_path).unwrap();
    let e = bad.verify(&all).unwrap_err();
    assert!(e.contains("DigestMismatch"), "实得: {e}");
    assert!(e.contains("以账本为准"), "理由必须说清谁说了算：{e}");

    // ② base_seq 超过账本长度
    doc["base_seq"] = json!(99);
    doc["digest"] = json!("fnv1a64:1111111111111111");
    let stale_path = d.join("stale.json");
    fs::write(&stale_path, serde_json::to_string(&doc).unwrap()).unwrap();
    let stale = Checkpoint::load(&stale_path).unwrap();
    let e = stale.verify(&all).unwrap_err();
    assert!(e.contains("Stale"), "实得: {e}");

    // ③ 不是合法 JSON / 缺 base_seq
    let junk = d.join("junk.json");
    fs::write(&junk, "{ not json").unwrap();
    assert!(Checkpoint::load(&junk).is_err());
    let nobase = d.join("nobase.json");
    fs::write(
        &nobase,
        json!({"checkpoint":1,"digest":"x","state":{}}).to_string(),
    )
    .unwrap();
    let e = Checkpoint::load(&nobase).unwrap_err();
    assert!(e.contains("base_seq"), "实得: {e}");
}

// ────────────────── 项目 Step 6 通道（round 16：IF-006 / FIND-06）──────────────────

/// **c14**：通道的身份来自**内核**，请求自称无效。
///
/// 四条判据：
/// 1. 同 uid 连接 → 落笔成功，且事件的 `actor` 取自**套接字映射**（不是请求里的字符串）；
/// 2. 请求**自称**别的 actor → 拒绝，且**没有落笔**；
/// 3. 请求未声明 actor → 允许（身份本就由内核给出，无需自称）；
/// 4. **受理路径不读对端凭证**（任务 2.1）：`Listener.uid` 只在 `bind()` 里用
///
///   （"权限即身份"：套接字 `chown` + `0600` ⇒ 只有那个 uid 连得上），
///    `serve_once` 一处都不读它。
#[cfg(unix)]
#[test]
fn c14_channel_takes_identity_from_kernel_not_from_request() {
    use std::io::{BufRead, BufReader, Write};
    use std::os::unix::net::{UnixListener, UnixStream};
    use world_core::bus::{serve_once, Listener};

    let d = tmpdir("c14");
    let lp = d.join("ledger.jsonl");
    let sock = d.join("w.sock");
    let me = libc_uid();

    let expect = Listener {
        socket: sock.clone(),
        actor: "world://agent/1".to_string(),
        uid: me,
    };
    let listener = UnixListener::bind(&sock).unwrap();

    // 判据 1：同 uid（本进程）→ 成功，且 actor 取自映射
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
    let mut c = UnixStream::connect(&sock).unwrap();
    c.write_all(
        br#"{"kind":"act","body":{"capability":"notice.mute","verb":"do","request_id":"r-c14"}}"#,
    )
    .unwrap();
    c.write_all(b"\n").unwrap();
    let ev = serve_once(&mut w, &listener, &expect).unwrap();
    assert_eq!(
        ev["actor"],
        json!("world://agent/1"),
        "actor 必须取自内核身份映射，而不是请求"
    );
    // 读回应答
    let mut reply = String::new();
    BufReader::new(&c).read_line(&mut reply).unwrap();
    assert!(reply.contains("\"ok\":true"), "应答: {reply}");

    // 判据 2：自称 world://user（冒充最高权主体）→ 拒绝且不落笔
    let before = w.ledger().last_seq();
    let mut c2 = UnixStream::connect(&sock).unwrap();
    c2.write_all(br#"{"kind":"act","actor":"world://user","body":{"capability":"notice.mute","verb":"do","request_id":"r-c14b"}}"#).unwrap();
    c2.write_all(b"\n").unwrap();
    let e = serve_once(&mut w, &listener, &expect).expect_err("冒充必须被拒");
    assert!(e.contains("Impersonation"), "实得: {e}");
    assert_eq!(w.ledger().last_seq(), before, "冒充被拒后不得落笔");

    // 判据 3：未自称 → 允许
    let mut c3 = UnixStream::connect(&sock).unwrap();
    c3.write_all(
        br#"{"kind":"act","body":{"capability":"notice.mute","verb":"do","request_id":"r-c14c"}}"#,
    )
    .unwrap();
    c3.write_all(b"\n").unwrap();
    serve_once(&mut w, &listener, &expect).expect("未自称 actor 应当被允许");

    // 判据 4（2.1）：**受理路径不读对端凭证**。
    //
    // 怎么断言到"不读"这件事本身（而不是只断言"收到了一条"）：把映射里的 `uid`
    // 换成**绝不等于本进程 uid** 的值，再走一次完整受理。若受理层哪天被改成
    // "取对端凭证再与 uid 比对"，对端 uid 必然对不上 ⇒ 这条当场变红
    // （变异：在 `serve_once` 里加一句对端 uid 比对，实测见任务回报）。
    //
    // 为什么这条要紧：`uid` 一旦被受理层读，两处口径就分叉了——
    // `bind()` 靠**文件权限**在 `connect()` 时就挡住别人（更早、更硬），
    // 而受理层再比一次，等于把"身份"重新变成一次**运行时可被绕过的判断**。
    let alien = Listener {
        socket: sock.clone(),
        actor: "world://agent/1".to_string(),
        uid: me.wrapping_add(12345),
    };
    assert_ne!(
        alien.uid, me,
        "夹具前提：这个 uid 必须与本进程 uid 不同，否则本判据恒真"
    );
    let mut c4 = UnixStream::connect(&sock).unwrap();
    c4.write_all(
        br#"{"kind":"act","body":{"capability":"notice.mute","verb":"do","request_id":"r-c14d"}}"#,
    )
    .unwrap();
    c4.write_all(b"\n").unwrap();
    let ev4 = serve_once(&mut w, &listener, &alien)
        .expect("受理路径不得读对端凭证：uid 对不上也必须受理（uid 只在 bind() 用）");
    assert_eq!(
        ev4["actor"],
        json!("world://agent/1"),
        "身份仍取自套接字映射，而不是别处"
    );
}

/// 取本进程 uid（不引 libc：用 /proc/self/status）。
#[cfg(unix)]
fn libc_uid() -> u32 {
    let s = fs::read_to_string("/proc/self/status").unwrap_or_default();
    for line in s.lines() {
        if let Some(rest) = line.strip_prefix("Uid:") {
            if let Some(first) = rest.split_whitespace().next() {
                return first.parse().unwrap_or(0);
            }
        }
    }
    0
}

// ────────────────── 错误码契约（round 18：DEBT-01）──────────────────

/// **c15**：凡**可编程判定**的错误都必须带 `ext.world.<域>.<原因>` 前缀。
///
/// 为什么这条测试才是 `DEBT-01` 的实质：光有 `code_of()` 只是"能解析"，
/// **有人新加一个不带码的错误**照样能过。本测试逐条走真实失败路径，
/// 把"错误码契约"从**声明**变成**会失败的检查**。
///
/// 来源共 **9 条**（任务 2.7 补了 ⑧ 缺号账本 / ⑨ 无链账本）：
/// 前七条覆盖本体、门禁三条、法律、通道、读模型，**账本路径原先一条都没有**。
#[test]
fn c15_errors_carry_machine_readable_codes() {
    use world_core::common::error::{code_of, has_code};

    let d = tmpdir("c15");
    let lp = d.join("ledger.jsonl");
    let mut codes: Vec<String> = Vec::new();

    // ① 本体错误
    let bad = d.join("bad.json");
    fs::write(&bad, "{ not json").unwrap();
    codes.push(World::open(&bad, &lp, &policy()).unwrap_err());

    // ② 门禁：未声明的能力
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
    codes.push(
        w.commit(
            "act",
            "world://agent/1",
            event::act_body("world.hack", "do", "r-c15a", json!({})),
        )
        .unwrap_err(),
    );

    // ③ 门禁：未授权的写入（change）
    codes.push(
        w.commit(
            "change",
            "world://agent/1",
            event::change_body("world://s", "p", json!(null), json!(1)),
        )
        .unwrap_err(),
    );

    // ④ 门禁：不可逆加摩擦
    codes.push(
        w.commit(
            "act",
            "world://agent/1",
            event::act_body("ledger.compact", "do", "r-c15b", json!({})),
        )
        .unwrap_err(),
    );

    // ⑤ 法律：违反本体的信纸
    codes.push(
        w.commit(
            "change",
            "world://user",
            json!({"subject": "world://s", "path": "p"}),
        )
        .unwrap_err(),
    );

    // ⑥ 通道：坏请求
    codes.push(world_core::bus::parse_request("不是 JSON").unwrap_err());

    // ⑦ 读模型：坏账本
    let gap = vec![event::new_event(
        5,
        "change",
        "world://user",
        event::change_body("world://s", "p", json!(null), json!(1)),
    )];
    codes.push(world_core::ontology_instance::readmodel::State::fold(&gap).unwrap_err());

    // ⑧ 账本路径：**缺号账本**（seq 从 1 跳到 3）⇒ 拒绝启动，且码属账本域。
    //    2.7：原七条来源里**没有一条**走账本路径——"账本也会拒启"这件事
    //    在错误码契约这一格上一直没人走过。
    let gap_ledger = d.join("gap.jsonl");
    fs::write(
        &gap_ledger,
        concat!(
            r#"{"world":1,"kind":"notice","id":"g1","seq":1,"at":1,"actor":"world://user","#,
            r#""flags":[],"body":{"type":"t","subject":"world://s"}}"#,
            "\n",
            r#"{"world":1,"kind":"notice","id":"g3","seq":3,"at":1,"actor":"world://user","#,
            r#""flags":[],"body":{"type":"t","subject":"world://s"}}"#,
            "\n"
        ),
    )
    .unwrap();
    let gap_err = World::open(&ontology(), &gap_ledger, &policy()).unwrap_err();
    assert_eq!(
        code_of(&gap_err),
        Some("ext.world.Ledger.SeqGap"),
        "缺号账本必须报账本域的点名码，实得: {gap_err}"
    );
    codes.push(gap_err);

    // ⑨ 账本路径：**无链账本** ⇒ `ext.world.Ledger.NoChain`。
    //    与 `tests/cli.rs:155`（`--require-chain` 拒启）断言的是**同一个码**：
    //    那条走 CLI、这条走库内核验，两处合起来才说明这个码不是某一层的私货。
    let chainless = vec![event::new_event(
        1,
        "notice",
        "world://user",
        event::notice_body("t", "world://s", json!({})),
    )];
    let noc = world_core::ledger::verify_chain(&chainless).unwrap_err();
    assert_eq!(
        code_of(&noc),
        Some("ext.world.Ledger.NoChain"),
        "无链账本必须报 `ext.world.Ledger.NoChain`（与 tests/cli.rs:155 同码），实得: {noc}"
    );
    codes.push(noc);

    // 全部必须带码
    for c in &codes {
        assert!(has_code(c), "错误缺少 `ext.world.<域>.<原因>` 前缀：{c}");
    }
    // 码互不相同（否则"判定种类"这件事名不副实）
    let unique: std::collections::BTreeSet<&str> =
        codes.iter().filter_map(|c| code_of(c)).collect();
    assert!(unique.len() >= 6, "错误码区分度不足，只拿到 {unique:?}");

    // 2.7：**账本路径**必须有自己的码（`ext.world.Ledger.*`）。
    // 今天这条路径在原七条来源里**一条都没有**，而 `tests/cli.rs:155` 恰恰断言的是
    // 同族的 `ext.world.Ledger.NoChain`：库侧与 CLI 侧不能一边有一边没有。
    let ledger_codes: std::collections::BTreeSet<&str> = codes
        .iter()
        .filter_map(|c| code_of(c))
        .filter(|c| c.starts_with("ext.world.Ledger."))
        .collect();
    assert!(
        ledger_codes.len() >= 2,
        "账本路径至少要有两个可判定的码（缺号 / 无链），实得 {ledger_codes:?}"
    );
    assert!(
        ledger_codes.contains("ext.world.Ledger.NoChain"),
        "`tests/cli.rs:155` 断言的那个码必须与库侧**同一个**：{ledger_codes:?}"
    );

    // 反例：散文式错误**必须**判为不符合契约（防契约被悄悄放宽）
    assert_eq!(code_of("门禁拒绝：能力未声明"), None);
}

// ────────────────── 摘要链验证侧（round 23：WC-CR-003 的验证部分）──────────────────

/// 造一串**带链**的事件（手工构造，因为**写入侧尚未实现**——`WC-CR-003` 待批准）。
fn chained(events: &mut [serde_json::Value]) {
    use world_core::ledger::{event_chain, CHAIN_GENESIS};
    let mut prev = CHAIN_GENESIS.to_string();
    for ev in events.iter_mut() {
        let c = event_chain(&prev, ev).unwrap();
        ev.as_object_mut()
            .unwrap()
            .insert("chain".to_string(), json!(c));
        prev = ev["chain"].as_str().unwrap().to_string();
    }
}

fn three_events() -> Vec<serde_json::Value> {
    vec![
        event::new_event(
            1,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(null), json!(1)),
        ),
        event::new_event(
            2,
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(1), json!(2)),
        ),
        event::new_event(
            3,
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-c", json!({})),
        ),
    ]
}

/// **c16**：改动 / 重排 / 中间插入 —— 链**必须**检出（`WC-CR-003` §三 的上半）。
#[test]
fn c16_chain_detects_local_tampering() {
    use world_core::ledger::verify_chain;

    // 基线：合法链必须通过（否则下面的断言可能因"什么都拒"而假通过）
    let mut ok = three_events();
    chained(&mut ok);
    verify_chain(&ok).expect("合法链应通过");

    // ① 改中间某条的内容（chain 不动）
    let mut tampered = ok.clone();
    tampered[1]["body"]["after"] = json!(999);
    let e = verify_chain(&tampered).unwrap_err();
    assert!(e.contains("ChainMismatch"), "实得: {e}");

    // ② 重排相邻两条
    let mut reordered = ok.clone();
    reordered.swap(1, 2);
    assert!(verify_chain(&reordered)
        .unwrap_err()
        .contains("ChainMismatch"));

    // ③ 在中间插入一条（带一个"看似合理"的 chain）
    //  ⚠️ 注入的事件必须带一个"攻击者为该位置算好的" chain——否则它只是"混用"，
    //     测的是 MixedChain 而**不是**插入检测（第一版就是这么写错的，被自己抓到）。
    let mut inserted = ok.clone();
    let mut extra = event::new_event(
        99,
        "act",
        "world://user",
        event::act_body("notice.mute", "do", "r-injected", json!({})),
    );
    let prev_chain = ok[1]["chain"].as_str().unwrap().to_string();
    let injected_chain = world_core::ledger::event_chain(&prev_chain, &extra).unwrap();
    extra
        .as_object_mut()
        .unwrap()
        .insert("chain".to_string(), json!(injected_chain));
    inserted.insert(2, extra);
    assert!(verify_chain(&inserted)
        .unwrap_err()
        .contains("ChainMismatch"));
}

/// **c17**：无链 / 混用 —— 必须被**显式区分**，不得静默通过（`WC-CR-003` D2）。
#[test]
fn c17_chain_distinguishes_absent_and_mixed() {
    use world_core::ledger::verify_chain;

    let plain = three_events();
    let e = verify_chain(&plain).unwrap_err();
    assert!(e.contains("NoChain"), "无链要说清是「不可检出」，实得: {e}");
    assert!(e.contains("不可检出"), "实得: {e}");

    let mut mixed = three_events();
    chained(&mut mixed);
    mixed[2].as_object_mut().unwrap().remove("chain");
    let e = verify_chain(&mixed).unwrap_err();
    assert!(e.contains("MixedChain"), "实得: {e}");
    assert!(e.contains("比无链更危险"), "理由要说清为什么：{e}");
}

/// **c18 = `WC-CR-003` 的 `c19`**：**整文件重写（连链重算）→ 按设计"检不出"**。
///
/// 这条测试的存在本身是设计的一部分：**一个只证明自己有效的机制，
/// 不如一个同时证明自己边界在哪里的机制**。若将来有人以为链能防住全知攻击者，
/// 这条测试会告诉他不能。
#[test]
fn c18_chain_cannot_detect_a_full_rewrite() {
    use world_core::ledger::verify_chain;

    // 攻击者把第 2 条改成 999，然后**把链整条重算**（他知道算法与创世种子）
    let mut forged = three_events();
    forged[1]["body"]["after"] = json!(999);
    chained(&mut forged);

    // 结论：核验**通过** —— 这就是无密钥链的极限，不是实现的缺陷
    verify_chain(&forged)
        .expect("无密钥的链挡不住整文件重写；此断言在证明**边界**，不是在证明实现有 bug");
    // 而局部篡改（不重算链）仍会被检出——两句话一起才完整
    let mut local = three_events();
    chained(&mut local);
    local[1]["body"]["after"] = json!(999);
    assert!(verify_chain(&local).is_err(), "局部篡改必须仍被检出");
}

// ────────────────── 摘要链写入侧（round 25：WC-CR-003 实施）──────────────────

/// **c19**：写出的账本**每条都带链**，且链自洽。
#[test]
fn c19_written_ledger_carries_a_verifiable_chain() {
    let d = tmpdir("c19");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        for i in 0..3 {
            w.commit(
                "change",
                "world://user",
                event::change_body(&format!("world://s{i}"), "p", json!(null), json!(i)),
            )
            .unwrap();
        }
    }
    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 3);
    assert!(
        all.iter().all(|e| e.get("chain").is_some()),
        "写入侧应给每条事件带上 chain"
    );
    world_core::ledger::verify_chain(&all).expect("写出的链必须自洽");
    // 链不影响状态：读模型不认 chain，指纹与"无链时代"一致
    assert_eq!(w.read_model().unwrap().last_seq(), 3);
}

/// **c20**：链的核验**接在启动路径上**——篡改一行即**拒绝启动**。
///
/// 这条才是"链有用"的证据：`c16`–`c18` 只证明核验函数会判，
/// 本用例证明**世界真的会因此拒绝打开**。
#[test]
fn c20_startup_refuses_a_tampered_ledger() {
    let d = tmpdir("c20");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        for i in 0..3 {
            w.commit(
                "change",
                "world://user",
                event::change_body(&format!("world://s{i}"), "p", json!(null), json!(i)),
            )
            .unwrap();
        }
    }
    // 篡改中间一行（保留原 chain）：改一个值，其余一切不动
    let text = fs::read_to_string(&lp).unwrap();
    let mut lines: Vec<String> = text.lines().map(str::to_string).collect();
    let mut v: serde_json::Value = serde_json::from_str(&lines[1]).unwrap();
    v["body"]["after"] = json!(999);
    lines[1] = v.to_string();
    fs::write(&lp, format!("{}\n", lines.join("\n"))).unwrap();

    let err = World::open(&ontology(), &lp, &policy()).expect_err("被篡改的账本必须拒绝启动");
    assert!(err.contains("ChainMismatch"), "实得: {err}");
    assert!(err.contains("唯一真相"), "理由要说清为什么拒绝：{err}");
}

// ────────────────── 链状态判定（round 27：把 round 26 的 bug 变成会失败的检查）──────────────────

/// **c21**：`is_chained()` 必须**如实反映账本现实**。
///
/// 为什么补这条：第 26 轮 CLI 实测发现"刚写好、带链的账本被报告为无链"——
/// 根因是 `load_chain` 里 `self.chained = true;` 漏了。
/// 当时 **57 项测试全绿**，因为 `c19`/`c20` 断言的是"链写出且自洽""篡改被拒"，
/// **从没断言过状态位本身**。本用例把这个洞堵上。
#[test]
fn c21_is_chained_reflects_reality() {
    // ① 新账本：写入即带链 ⇒ 启动判定必须为 true
    let d = tmpdir("c21");
    let lp = d.join("ledger.jsonl");
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        w.commit(
            "change",
            "world://user",
            event::change_body("world://s", "p", json!(null), json!(1)),
        )
        .unwrap();
    }
    let w = World::open(&ontology(), &lp, &policy()).unwrap();
    assert!(
        w.ledger().is_chained(),
        "账本已带链，is_chained() 却为 false —— 状态位没被置上（第 26 轮真实踩过）"
    );

    // ② 空账本（没有任何事件）⇒ 无链可言，应为 false
    let empty = d.join("empty.jsonl");
    {
        let _w = World::open(&ontology(), &empty, &policy()).unwrap();
    }
    let w2 = World::open(&ontology(), &empty, &policy()).unwrap();
    assert!(
        !w2.ledger().is_chained(),
        "空账本不应声称有链（那会让人以为它受保护）"
    );

    // ③ 手工造的无链账本 ⇒ false，且**能打开**（v1 兼容：无链须放行但可被警示）
    let legacy = d.join("legacy.jsonl");
    let ev = event::new_event(
        1,
        "notice",
        "world://user",
        event::notice_body("t", "world://s", json!({})),
    );
    fs::write(
        &legacy,
        format!("{}\n", serde_json::to_string(&ev).unwrap()),
    )
    .unwrap();
    let w3 = World::open(&ontology(), &legacy, &policy()).unwrap();
    assert!(
        !w3.ledger().is_chained(),
        "无链账本必须被判为 false（未校验要说出来）"
    );
    assert_eq!(w3.ledger().last_seq(), 1, "无链账本仍应能打开（v1 兼容）");
}

// ────────────────── 行边界不变量（round 31：为 FIND-03 的前提上锁）──────────────────

/// **c22**：**每次成功追加后，文件必须以 `\n` 结尾**，且每行都是完整 JSON。
///
/// 为什么单独立一条：`Ledger::append` 的整套加固（写入前记长度、失败回滚、
/// 回滚再失败则标记污染）**全部建立在同一个前提上**——
/// "**文件末尾永远是完整行**"。前提若不成立：
/// ① 半行会与下一条成功写入**粘连**成坏行；② 重启读到坏 JSON 会**拒绝启动**（整世界锁死）；
/// ③ 若粘连处含此前已 ack 的事件，启动"截到最后一个 `\n`"会**静默删掉它们**。
///
/// 纯粹的 I/O 失败注入（ENOSPC/EINTR）本项目**尚无工具**（`WC-TP-001` §五 缺口 2，
/// 照实登记）。本用例守的是那条路径**可被检测**的前提——前提没了，加固就无从谈起。
#[test]
fn c22_file_always_ends_on_a_line_boundary() {
    let d = tmpdir("c22");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    for i in 0..5u64 {
        w.commit(
            "change",
            "world://user",
            event::change_body(&format!("world://s{i}"), "p", json!(null), json!(i)),
        )
        .unwrap();

        // 判据 ①：末尾必须是换行
        let raw = fs::read(&lp).unwrap();
        assert_eq!(
            raw.last().copied(),
            Some(b'\n'),
            "第 {} 次追加后文件未以 \\n 结尾——末尾可能残留半行",
            i + 1
        );

        // 判据 ②：每一行都必须是完整 JSON（粘连会立刻表现为某行解析失败）
        let text = String::from_utf8(raw).expect("账本必须是合法 UTF-8");
        for (n, line) in text.lines().enumerate() {
            serde_json::from_str::<serde_json::Value>(line)
                .unwrap_or_else(|e| panic!("第 {} 行不是完整 JSON（行粘连？）：{e}", n + 1));
        }
    }

    // 判据 ③：条数与追加次数一致（没有静默丢失）
    // ⚠️ 必须先释放第一个写者——否则会被**单写者锁**挡下（第一版就是这样写错的，
    //    而它恰好证明了那把锁是真的在工作）。
    drop(w);
    let w2 = World::open(&ontology(), &lp, &policy()).unwrap();
    assert_eq!(w2.ledger().read_all().unwrap().len(), 5);
    assert_eq!(w2.ledger().last_seq(), 5);
}

// ═══════════════════════════════════════════════════════════════════════════
// c23 —— **通告也必须过闸**（`D-13` / `D-14`；专家席 C 发现，实测复现后修）
//
// 修前的病：`adjudicate` 的 `_ => Ok(())` 让 `notice` 族完全不过闸 ⇒
// 任何主体可往账本写任意通告，**包括与内核真流水逐字同形的伪造 `gate.rejected`**
// ⇒ 整套审计可被一行伪造。实测复现：不在白名单的 `world://stranger` 提交
// `type=gate.rejected` 得到 rc=0 且进账本，而同一主体写 `change` 得 rc=2。
// ═══════════════════════════════════════════════════════════════════════════

/// 反例 ①：**保留前缀**不许外部主体写。
///
/// 为什么这条最要紧：`gate.*` 是"世界对某次请求的裁决"的流水。若外部可写，
/// 则任何人都能**替世界说"我拒绝过这件事"**，而伪造行与真行逐字同形、事后不可区分。
#[test]
fn c23_notice_with_reserved_prefix_is_refused_for_outsiders() {
    let d = tmpdir("c23a");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    let e = w.commit(
        "notice",
        "world://stranger",
        event::notice_body("gate.rejected", "world://user", json!({ "reason": "伪造" })),
    );
    let msg = e.expect_err("保留前缀 `gate.` 必须拒绝外部主体");
    assert!(
        msg.contains("ext.world.Gate.NoticeNotAllowed"),
        "拒绝理由必须点名错误码，实得：{msg}"
    );
    assert!(msg.contains("内核保留前缀"), "理由必须说清为什么：{msg}");

    // 判据②：**被拒的伪造通告不得落笔**（拒绝也要留痕，但留的是内核对这次拒绝的流水）
    let evs = w.ledger().read_all().unwrap();
    let forged = evs
        .iter()
        .filter(|ev| ev["body"]["type"] == json!("gate.rejected"))
        .count();
    assert_eq!(forged, 0, "伪造的 gate.rejected 绝不允许进账本");

    // 判据③（任务 3.2）：**这条路径写下的流水也带 `refused` 指纹**。
    //
    // 为什么单列：`c23_gate_notice_says_what_it_refused` 走的是不可逆加摩擦那条
    // （`gate.awaiting-approval`，`lib.rs` 的 `Decision::AwaitApproval` 分支）；
    // 保留前缀这条走的是另一个分支（`adjudicate_notice`）——同一个字段、
    // 两条不同的拒绝路径。只测一条时，另一条可以整段失效而全绿。
    let flow = evs
        .iter()
        .find(|ev| ev["body"]["type"] == json!("gate.notice-not-allowed"))
        .expect("保留前缀被拒必须留下内核自己的流水（拦得住，也记得下）");
    let refused = flow["body"]["payload"]["refused"]
        .as_str()
        .expect("保留前缀拒绝流水同样必须带 `refused` 字段（D-14）");
    assert!(
        refused.starts_with("fnv1a64:"),
        "`refused` 必须是可复算的规范形式指纹，实得：{refused}"
    );
    assert_eq!(
        flow["body"]["payload"]["refused_subject"],
        json!("world://user"),
        "流水要点名它在拒绝**哪一次尝试**（被拒信纸的 subject），实得：{flow}"
    );
    // 可复算：同一次尝试（同 actor + 同信纸）⇒ 同一指纹
    let e2 = w
        .commit(
            "notice",
            "world://stranger",
            event::notice_body("gate.rejected", "world://user", json!({ "reason": "伪造" })),
        )
        .expect_err("第二次同样必须被拒");
    assert!(e2.contains("NoticeNotAllowed"), "实得：{e2}");
    let refused2 = w
        .ledger()
        .read_all()
        .unwrap()
        .iter()
        .filter(|ev| ev["body"]["type"] == json!("gate.notice-not-allowed"))
        .nth(1)
        .expect("第二条保留前缀拒绝流水")["body"]["payload"]["refused"]
        .as_str()
        .unwrap()
        .to_string();
    assert_eq!(
        refused, refused2,
        "同一次尝试的指纹必须可复算（同输入同输出）"
    );
}

/// 反例 ②：**不在册的主体**不许写普通通告。
#[test]
fn c23_notice_from_unlisted_actor_is_refused() {
    let d = tmpdir("c23b");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    let e = w.commit(
        "notice",
        "world://stranger",
        event::notice_body("my.own.notice", "world://user", json!({})),
    );
    let msg = e.expect_err("不在白名单的主体不得写通告");
    assert!(msg.contains("ext.world.Gate.NoticeRejected"), "{msg}");

    // 正例对照：在册主体写同样形状的通告必须通过（否则修法把正常路径打死了）
    w.commit(
        "notice",
        "world://agent/1",
        event::notice_body("my.own.notice", "world://job/1", json!({})),
    )
    .expect("在册主体写普通通告应当通过");
}

/// `D-14`：门禁流水必须点名"它在拒绝什么"。
///
/// 只保留前缀是不够的——那解决了"谁能写"，没解决"写的是什么"：
/// 外部提交被拒时的流水与内核自己发起的裁决流水**类型相同**，
/// 读账本的人分不清"内核在裁别人"还是"别人的尝试被裁了"。
/// 修法：流水 payload 带 `refused`（被拒对象的规范形式指纹）。
#[test]
fn c23_gate_notice_says_what_it_refused() {
    let d = tmpdir("c23c");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    // 触发一条真实的内核裁决流水：agent 请求不可逆动作 ⇒ 加摩擦
    let _ = w.commit(
        "act",
        "world://agent/1",
        event::act_body("ledger.compact", "do", "r-9", json!({})),
    );

    let evs = w.ledger().read_all().unwrap();
    let gate = evs
        .iter()
        .find(|ev| ev["body"]["type"] == json!("gate.awaiting-approval"))
        .expect("应当有一条门禁流水");
    let refused = gate["body"]["payload"]["refused"]
        .as_str()
        .expect("流水必须带 `refused` 字段（D-14）");
    assert!(
        refused.starts_with("fnv1a64:"),
        "`refused` 必须是可复算的规范形式指纹，实得：{refused}"
    );

    // 可复算：同一 actor + 同一信纸 ⇒ 同一指纹（跨进程、跨时间都一样）
    let again = w.commit(
        "act",
        "world://agent/1",
        event::act_body("ledger.compact", "do", "r-9", json!({})),
    );
    assert!(again.is_err(), "第二次同样会被加摩擦");
    let evs2 = w.ledger().read_all().unwrap();
    let refused2 = evs2
        .iter()
        .filter(|ev| ev["body"]["type"] == json!("gate.awaiting-approval"))
        .nth(1)
        .expect("第二条门禁流水")["body"]["payload"]["refused"]
        .as_str()
        .unwrap()
        .to_string();
    assert_eq!(
        refused, refused2,
        "同一次尝试的指纹必须可复算（同输入同输出）"
    );
}

// ═══════════════════════════════════════════════════════════════════════════
// c24 —— **已知无码出口**（任务 2.6）：把"没有 `ext.world.` 码"钉成边界
// ═══════════════════════════════════════════════════════════════════════════

/// **c24**：四条**已知无码出口**的错误串**不含** `ext.world.` 前缀——这是**边界**，不是缺陷。
///
/// | # | 出口 | 实现 | 今天的话 |
/// |---|---|---|---|
/// | ① | 静态墙·**符号链接** | `guard::assert_not_symlink` | 「…是一个**符号链接**」 |
/// | ② | 静态墙·**mode 位** | `guard::assert_not_other_writable` | 「…对 group/other 可写」 |
/// | ③ | 静态墙·**属主** | `guard::assert_owned_by` | 「…属主断言未通过」 |
/// | ④ | 策略**版本不符** | `Policy::load` | 「门禁策略版本不支持：期望 1，实得 2」 |
///
/// ## 为什么"没有码"也要有断言
///
/// `c15` 断言的是"**可编程判定**的错误都必须带码"，它**只走带码的那几条路径**。
/// 于是"哪些出口**还没有**码"在仓里没有落点：谁哪天给某条出口加一个码，
/// 或者把某条出口的码删掉，**两边都不会红**——而"哪些错误可编程判定"这件事
/// 是 `WC-IC-001` §三 的契约面，不能靠没人看。
///
/// ## 这条断言红的时候该怎么办（2.6 的验收口径）
///
/// 它红 **≠** 实现错了：`ext.world.` 前缀多出来只会让契约更严。红的意思是
/// **"边界形状变了"**——那时按实际情况改规格/清单，而不是把断言改绿了事。
///
/// ## 变异（把边界形状改掉）
///
/// 给任一条出口加上 `ext.world.<域>.<原因>` 前缀 ⇒ 对应那一条断言变红
///（实测见任务回报：只加 ④ 的前缀，①②③ 仍绿，④ 红）。
#[cfg(unix)]
#[test]
fn c24_known_codeless_outlets_carry_no_ext_world_prefix() {
    use std::os::unix::fs::{symlink, MetadataExt, PermissionsExt};
    use world_core::common::error::has_code;
    use world_core::gate::guard;

    let d = tmpdir("c24");
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();

    // ① 符号链接：内容真放一份在别处，法律用一个指向它的软链
    let real = d.join("real-policy.json");
    fs::copy(policy(), &real).unwrap();
    let link = d.join("policy-link.json");
    symlink(&real, &link).unwrap();
    let e_symlink = world_core::gate::Policy::load(&link).unwrap_err();
    assert!(e_symlink.contains("符号链接"), "实得：{e_symlink}");

    // ② mode 位：内容合法，只是对 group/other 可写
    let writable = write_policy(&d, "writable-policy.json", &valid_policy_json());
    fs::set_permissions(&writable, fs::Permissions::from_mode(0o666)).unwrap();
    let e_mode = world_core::gate::Policy::load(&writable).unwrap_err();
    assert!(
        e_mode.contains("对 group/other 可写"),
        "必须走到 mode 这条（不是别的失败），实得：{e_mode}"
    );

    // ③ 属主：断言一个**不是本进程**的 uid
    let mine = fs::metadata(&real).unwrap().uid();
    let e_owner = guard::assert_owned_by(&real, mine.wrapping_add(1), "门禁策略（法律）")
        .expect_err("属主不符必须被拒");
    assert!(e_owner.contains("属主断言未通过"), "实得：{e_owner}");

    // ④ 策略版本不符：其余一切都合法，只有 `policy` 不是 1
    let mut v = valid_policy_json();
    v["policy"] = json!(2);
    let badver = write_policy(&d, "bad-version-policy.json", &v);
    let e_badver = world_core::gate::Policy::load(&badver).unwrap_err();
    assert!(e_badver.contains("版本不支持"), "实得：{e_badver}");

    // ── 断言：四条都**没有** `ext.world.` 码（这是当前的边界形状）──
    for (what, msg) in [
        ("① 静态墙·符号链接", &e_symlink),
        ("② 静态墙·mode 位", &e_mode),
        ("③ 静态墙·属主", &e_owner),
        ("④ 策略版本不符", &e_badver),
    ] {
        assert!(
            !msg.trim().is_empty(),
            "{what} 的理由不得为空——空串会让「没有码」这条断言变成假绿"
        );
        assert!(
            !has_code(msg),
            "{what} 今天**不带** `ext.world.` 码（已知无码出口，任务 2.6）。\
             若它现在带了码，说明边界形状已变：请按实际情况订正规格/清单，而不是把这条断言改绿。实得：{msg}"
        );
        assert!(
            !msg.contains("ext.world."),
            "{what} 连字面都不该出现 `ext.world.`（半截前缀不算带码，但仍是形状变化）。实得：{msg}"
        );
    }

    // 对照（防"什么都判成无码"）：同一次运行里，**带码**的出口必须仍被判为带码。
    // 没有这条，"四条都无码"可能只是因为 `has_code` 坏了。
    let mut w = World::open(&ontology(), &d.join("l.jsonl"), &policy()).unwrap();
    let e_coded = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("world.hack", "do", "r-c24", json!({})),
        )
        .unwrap_err();
    assert!(
        e_coded.contains("ext.world.Gate.Rejected"),
        "对照项必须是带码出口，实得：{e_coded}"
    );
    assert!(has_code(&e_coded), "带码出口必须被判为带码：{e_coded}");
}

// ═══════════════════════════════════════════════════════════════════════════
// c29–c33 —— **账本与证据链**（`fc-2026-004-assertions` 组 4）
//
// 五条各自固定**一件事**，且各自有一个「改坏哪一行 ⇒ 它变红」的变异点：
// - `c29`（4.1）`K-3` 的**修复判据**：无链账本做一次合法 append 后**仍可被打开**
//   ⇒ 当下**必然为红**，故取 `#[ignore]` ＋ 理由（选择理由见该用例的文档）
// - `c30`（4.2）`K-3` 的**当下边界**：无链账本 ＋ 一次合法 append ⇒ 下次打开报 `MixedChain`
// - `c31`（4.3）无链账本的「能打开」**只到只读为止**：打开后写入必败，且字节不动
// - `c32`（4.6）行边界：末行是**完整合法 JSON 但缺末尾换行** ⇒ **被截掉**且 `seq` 被复用
// - `c33`（4.7）单写者锁的**反向失效**：pid 号被复用（号活着、持有者已不在）⇒ 陈锁**不回收**
// ═══════════════════════════════════════════════════════════════════════════

/// 造一份 **v1 无链账本**：`n` 条合法 `notice` 事件逐行落盘，**一行 `chain` 都没有**。
///
/// 手工造的理由：今天**没有任何生产路径**能写出无链账本（`append` 无条件加链），
/// 而 v1 兼容路径要的正是这种历史账本。
fn write_v1_ledger(path: &Path, n: u64) {
    let mut text = String::new();
    for seq in 1..=n {
        let ev = event::new_event(
            seq,
            "notice",
            "world://user",
            event::notice_body("probe.v1", "world://s", json!({ "seq": seq })),
        );
        text.push_str(&serde_json::to_string(&ev).unwrap());
        text.push('\n');
    }
    if let Some(d) = path.parent() {
        std::fs::create_dir_all(d).unwrap();
    }
    fs::write(path, text).unwrap();
}

/// 把一批**手写**事件写成一行的 JSONL（无链、v1 形态）。
///
/// 为什么就地写而不复用 `write_v1_ledger`：那个助手只会造**合规**事件（走 `event::new_event`），
/// 而 `c34` 要的正是**形状不合规**的事件——本体的类型判据就是冲它来的。
fn write_raw_jsonl(path: &Path, events: &[Value]) {
    let mut text = String::new();
    for ev in events {
        text.push_str(&serde_json::to_string(ev).unwrap());
        text.push('\n');
    }
    if let Some(d) = path.parent() {
        std::fs::create_dir_all(d).unwrap();
    }
    fs::write(path, text).unwrap();
}

/// 一次**合法**的 `change`：`world://user` 写自己世界里的 `world://notice/n-1#muted`
/// （主体与字段都在出厂本体与出厂策略里声明过 ⇒ 法律与门禁都放行）。
fn legal_change(w: &mut World) -> Result<Value, String> {
    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    )
}

/// **c29**（`4.1`）：`K-3` 的**修复判据** —— 在**无链（v1）账本**上做一次**合法** `append`
/// 之后，账本**仍可被打开**。
///
/// ## 为什么取 `#[ignore] ＋ 理由`，而不是把它改写成「当下边界」
///
/// `4.1` 的验收逐字是「该断言当前**必然为红**」。而「当下边界」（混用 ⇒ `MixedChain`）
/// 已由 `c30` **单独**钉住，且它是绿的。若把 `c29` 也写成「断言 `MixedChain`」，
/// 则「**修复后应当能打开**」这条判据**没有任何东西在看**：修复落地那天不会有任何断言
/// 由红转绿，`K-3` 的修复判据就退化成一句散文。故这里**保留判据原样**
/// （去掉 `#[ignore]` 即应转绿），而「它当下确实是红的」用 `--ignored` 现场证明：
///
/// ```text
/// cargo test --locked --test contract -- --ignored c29_     ⇒ 1 failed（读数见交付说明）
/// ```
///
/// ## 会红的根因（实测，非推测）
///
/// `Ledger::append` 给**每一条**新事件加 `chain`（`src/ledger/mod.rs:430-434`），
/// 而它读的 `last_chain` 在无链账本上仍是创世种子；`chained`（`src/ledger/mod.rs:146`）
/// **只被 `load_chain` 写、从不被 `append` 读**（`4.1` 出处 `src/ledger/mod.rs:506` 同族）
/// ⇒ v1 账本追加一条后变成「前半无链、后半有链」，下次打开 `verify_chain` 报 `MixedChain`、
/// `load_chain` 视之为 `Err` ⇒ **世界拒启**。这就是 `K-3`。
#[test]
#[ignore = "K-3 未修（src/ledger/mod.rs:146 的 chained 只写不读）：无链账本 append 一条后被判 MixedChain、世界拒启；修复落地后去掉本 ignore 即应转绿"]
fn c29_k3_chainless_ledger_survives_one_legal_append() {
    let d = tmpdir("c29-k3");
    let lp = d.join("legacy.jsonl");
    write_v1_ledger(&lp, 1);

    // ① 前提：v1 无链账本今天**能**打开 —— 否则下面测的不是 `K-3` 而是别的
    let mut w = World::open(&ontology(), &lp, &policy()).expect("v1 无链账本应能打开");
    assert!(
        !w.ledger().is_chained(),
        "v1 账本必须被判为无链（未校验要说出来）"
    );

    // ② 前提：这一次 append 是**合法**的（法律与门禁都放行，且真的落了笔）
    let ev = legal_change(&mut w).expect("world://user 写 world://notice/n-1#muted 应当合法");
    assert_eq!(ev["seq"], json!(2), "v1 账本上的第 2 条应当取到 seq=2");
    drop(w); // ← 必须释放单写者锁：否则第 ③ 步会被锁挡下，掩盖本条的判据

    // ③ `K-3` 判据：**仍可被打开**
    if let Err(e) = World::open(&ontology(), &lp, &policy()) {
        panic!("K-3 未修：无链账本做一次合法 append 之后，账本**仍应可被打开**；实得拒绝：{e}");
    }
}

/// **c30**（`4.2`）：固定 `K-3` 的**当下边界** —— 无链账本 ＋ 一次合法 `append`
/// ⇒ 下次打开报 `ext.world.Ledger.MixedChain`。
///
/// 这条**在修复落地前为绿**：它证明的是**边界形状**，不是缺陷。与 `c29` 的分工写死在
/// 两边的文档里：修复落地时，**`c30` 应当变红、`c29` 应当变绿**；若只有一条变色，
/// 说明修复方向与判据不一致 —— 那本身就是发现。
///
/// 判据不止比错误串：还要**逐行看账本文件**，确认「半链」这个机制成立
/// （第 1 行无 `chain`、第 2 行有 `chain`）—— 否则「报 MixedChain」可能出自别的原因。
#[test]
fn c30_k3_boundary_chainless_ledger_plus_one_append_reports_mixed_chain() {
    let d = tmpdir("c30-k3-boundary");
    let lp = d.join("legacy.jsonl");
    write_v1_ledger(&lp, 1);
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        assert!(!w.ledger().is_chained(), "v1 账本必须被判为无链");
        legal_change(&mut w)
            .expect("这一条 append 必须成功 —— 否则下面的 MixedChain 就不是「追加造成的」");
    }

    // 机制：盘上第 1 行无 chain、第 2 行有 chain —— 半链就是这么来的
    let text = fs::read_to_string(&lp).unwrap();
    let lines: Vec<&str> = text.lines().collect();
    assert_eq!(lines.len(), 2, "应当是 1 条 v1 事件 ＋ 1 条 append 事件");
    let l0: Value = serde_json::from_str(lines[0]).unwrap();
    let l1: Value = serde_json::from_str(lines[1]).unwrap();
    assert!(l0.get("chain").is_none(), "v1 那一行不得带 chain");
    assert!(
        l1.get("chain").is_some(),
        "append 写入的那一行必须带 chain（半链由此而来）"
    );

    // 判据：下次打开 ⇒ 拒启，且点名 MixedChain、理由说清为什么半链更危险
    let err = World::open(&ontology(), &lp, &policy())
        .expect_err("无链账本 ＋ 一次合法 append ⇒ 修复落地前必须报 MixedChain 并拒启");
    assert!(err.contains("ext.world.Ledger.MixedChain"), "实得: {err}");
    assert!(
        err.contains("比无链更危险"),
        "理由必须说清为什么半链更危险：{err}"
    );
}

/// **c31**（`4.3`）：`c21` 的「无链账本仍能打开」**只到只读为止** —— 打开之后**写入必败**。
///
/// 与 `c30` 是同一件事的两侧：`c30` 说「追加会把账本变成半链，下次打开拒启」；
/// 本条说「**在本进程内**，从只读口径打开的无链账本上写入，不是悄悄成功，而是当场失败」。
/// 三条判据一起才成立：① 写入返回错误且点名 `ext.world.Ledger.ReadOnly`；
/// ② 账本字节**一个都不变**（`REQ-F-012`）；③ `seq` 不被消耗。
/// 出处：`tests/contract.rs` 的 `c21` ③「无链账本仍应能打开（v1 兼容）」。
#[test]
fn c31_chainless_ledger_opens_readonly_and_refuses_writes() {
    let d = tmpdir("c31-readonly");
    let lp = d.join("legacy.jsonl");
    write_v1_ledger(&lp, 1);
    let before = fs::read(&lp).unwrap();

    let mut w =
        World::open_readonly(&ontology(), &lp, &policy()).expect("无链账本只读口径应能打开");
    assert!(!w.ledger().is_chained(), "无链账本必须被判为 false");
    assert_eq!(w.ledger().last_seq(), 1, "无链账本仍应能**读**（v1 兼容）");

    // ★ 判据：只到只读为止 —— 写入必败
    let e = legal_change(&mut w).expect_err("只读口径打开的账本上写入必须失败");
    assert!(
        e.contains("ext.world.Ledger.ReadOnly"),
        "错误必须点名「只读口径」这件事：{e}"
    );
    assert!(e.contains("禁止落笔"), "理由必须说清是「禁止落笔」：{e}");
    assert_eq!(
        fs::read(&lp).unwrap(),
        before,
        "只读口径下被拒的写入**不得改动任何一个字节**（REQ-F-012）"
    );
    assert_eq!(
        w.ledger().last_seq(),
        1,
        "被拒的写入不得消耗 seq（否则只读路径会「吃掉」一个号）"
    );
}

/// **c32**（`4.6`）：行边界 —— 末行是**完整合法 JSON 但缺末尾换行** ⇒ **被截掉**，
/// 且 `seq` 被复用。
///
/// ## 为什么这条边界必须写成断言
///
/// 启动口径是「**截到最后一个 `\n`**」（`src/ledger/mod.rs:276-289`），而 `append` 的整套加固
/// 都建立在「末尾永远是完整行」这个前提上（`src/ledger/mod.rs:385` 的自述）。
/// 代价是：一条**内容完全合法**、只是**没来得及写末尾换行**的事件会被当成「半行」**删掉**，
/// 它的 `seq` 会被下一条复用。这不是要辩解的事，而是要**固定成断言**的当下边界：
/// 谁将来把 `keep` 改成「整文件」，本用例立刻变红（见变异证明）。
#[test]
fn c32_last_line_without_trailing_newline_is_cut_and_seq_is_reused() {
    let d = tmpdir("c32-line-boundary");
    let lp = d.join("ledger.jsonl");
    // ── 夹具：第 1 行带换行；第 2 行**完整合法 JSON**、但**没有末尾换行** ──
    let l1 = serde_json::to_string(&event::new_event(
        1,
        "notice",
        "world://user",
        event::notice_body("probe.n1", "world://s", json!({})),
    ))
    .unwrap();
    let l2 = serde_json::to_string(&event::new_event(
        2,
        "notice",
        "world://user",
        event::notice_body("probe.n2", "world://s", json!({})),
    ))
    .unwrap();
    fs::write(&lp, format!("{l1}\n{l2}")).unwrap();

    // 夹具自证：两行**都是完整合法 JSON**，只是缺末尾换行（否则本用例测的是别的事）
    assert!(
        !fs::read(&lp).unwrap().ends_with(b"\n"),
        "夹具必须缺末尾换行"
    );
    for (idx, line) in [l1.as_str(), l2.as_str()].into_iter().enumerate() {
        let v: Value = serde_json::from_str(line)
            .unwrap_or_else(|e| panic!("夹具第 {} 行不是完整 JSON：{e}", idx + 1));
        assert_eq!(
            v["seq"],
            json!(idx as u64 + 1),
            "夹具第 {} 行的 seq 应为 {}",
            idx + 1,
            idx + 1
        );
    }

    // ── 判据 ①：可写口径打开 ⇒ 第 2 行**被截掉**（不是「读不到」，是**盘上没了**） ──
    {
        let w = World::open(&ontology(), &lp, &policy()).unwrap();
        assert_eq!(
            w.ledger().last_seq(),
            1,
            "完整但缺末尾换行的末行被截掉 ⇒ 只剩 1 条"
        );
        assert_eq!(
            w.ledger().next_seq(),
            2,
            "那一号未落笔 ⇒ 必须可复用（next_seq 回到 2）"
        );
    }
    assert_eq!(
        fs::read(&lp).unwrap(),
        format!("{l1}\n").as_bytes(),
        "「截到最后一个换行」必须**落到盘上**（逐字节等于第 1 行加换行）"
    );

    // ── 判据 ②：复用确实发生在**账本**上（不只是内存里的 next_seq） ──
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        let ev = legal_change(&mut w).unwrap();
        assert_eq!(
            ev["seq"],
            json!(2),
            "被截掉的那一号必须被下一条合法事件复用"
        );
    }
    let after = fs::read_to_string(&lp).unwrap();
    assert_eq!(after.lines().count(), 2, "复用后仍应是 2 条完整行");
    assert!(after.ends_with('\n'), "追加之后末行必须回到「以换行结尾」");

    // ── 判据 ③（对照）：**只读**口径下同一个文件**一个字节都不动**，只是读边界停在完整行 ──
    let lp2 = d.join("readonly.jsonl");
    fs::write(&lp2, format!("{l1}\n{l2}")).unwrap();
    let before = fs::read(&lp2).unwrap();
    {
        let r = World::open_readonly(&ontology(), &lp2, &policy()).unwrap();
        assert_eq!(r.ledger().last_seq(), 1, "只读口径同样只认完整行");
        assert_eq!(r.ledger().next_seq(), 2);
        assert_eq!(r.ledger().read_all().unwrap().len(), 1, "读回也只有 1 条");
    }
    assert_eq!(
        fs::read(&lp2).unwrap(),
        before,
        "只读口径**不得**截断文件（P-01 / REQ-F-012）：截断是写路径的特权"
    );
}

/// **c33**（`4.7`）：单写者锁的**反向失效** —— pid 号被复用时，持有者已不存在却**不会被回收**。
///
/// ## 这条固定的是「锁的失效方向」，不是「锁有效」
///
/// `acquire_lock` 判「陈锁」只看 `/proc/<pid>` 存不存在（`src/ledger/mod.rs:182-184`）。
/// 于是有**反向**的一格：原来的写者早已结束，但它的 **pid 号被另一个无关进程复用**
/// ⇒ 锁文件被判为「仍被持有」⇒ **世界永远起不来**，而账本本身是好的。
/// 这一格今天的处置只有人工（`Locked` 的理由串里就写着「确认它已崩溃则删除锁文件」），
/// 本用例把它钉成断言：**不许**有人在没有替代判据（例如 pid ＋ 启动时间 ＋ 锁内写者标识）
/// 之前，把「陈锁判定」改成「一律回收」（那会让两个写者并存），
/// 也**不许**假装这一格不存在。
///
/// 正控（同一判据的另一侧）：pid 号**确实不存在**时，陈锁**必须**被回收、世界**必须**能开。
#[test]
fn c33_stale_lock_with_a_reused_live_pid_is_never_reclaimed() {
    let d = tmpdir("c33-lock");
    let lp = d.join("ledger.jsonl");
    // 先把账本本身做成「好的」：有内容、带链 —— 使「拒启」只可能出自锁
    {
        let mut w = World::open(&ontology(), &lp, &policy()).unwrap();
        legal_change(&mut w).unwrap();
    }
    let lock = lp.with_extension("lock");
    assert!(
        !lock.exists(),
        "正常释放后不得留下锁文件（否则下面的反例不成立）"
    );

    // ★ 反例：锁文件里的 pid 号**活着**，而持有者早已不在 —— 这正是「pid 被复用」的形状
    let me = std::process::id();
    fs::write(&lock, format!("{me}\n")).unwrap();
    let err = World::open(&ontology(), &lp, &policy())
        .expect_err("锁文件声称持有者仍存活 ⇒ 世界必须拒启（这就是本条的边界形状）");
    assert!(err.contains("ext.world.Ledger.Locked"), "实得: {err}");
    assert!(
        err.contains("仍存活"),
        "拒启理由必须说清它认为持有者还活着：{err}"
    );
    assert!(
        err.contains(&format!("pid=Some({me})")),
        "理由里必须报出它认的持有者 pid（否则人工无法处置）：{err}"
    );
    assert!(
        lock.exists(),
        "陈锁**不得**被自动回收：本条的边界正是「世界起不来，需人工删锁」"
    );

    // 正控：同一个锁文件、一个**确实已不存在**的 pid ⇒ 必须回收陈锁并放行
    let mut child = std::process::Command::new("true")
        .spawn()
        .expect("无法启动 `true`（正控需要一个已结束的真 pid）");
    let dead = child.id();
    child.wait().expect("等待子进程结束");
    fs::write(&lock, format!("{dead}\n")).unwrap();
    let w = World::open(&ontology(), &lp, &policy())
        .expect("持有者确实不存在时，陈锁必须被回收、世界必须能打开（否则判据变成「一律拒启」）");
    assert_eq!(
        w.ledger().last_seq(),
        1,
        "回收陈锁之后应当看到原有的那 1 条事件"
    );
}

// ── c34 ── **信封字段的类型**：本体声明了类型，读路径也必须判（`TC-047 ⑧` 的修法）──────
//
// 为什么单列一条：`c15` 判的是"可编程判定的错误都带码"，`c24` 判的是"已知无码出口"，
// 两条都**只管写入路径**。而账本里**已有的**事件由折叠层直接读——实测（2026-09-28，VM）
// 把 `world` 写成字符串 `"1"`、把 `actor` 写成整数 `123`，`state` 一律 **rc=0**：
// 声明写了类型，读的人却没判。这一条把"读路径也判类型"钉住。
//
// **反例（必须红）**：上面那两处真实违规形状 ⇒ 打开即拒，码为 `ext.world.Ontology.BadFieldType`，且**点名那一格**。
// **正控（不得红）**：同一条账本，把两格改回声明类型 ⇒ 打开成功。
#[test]
fn c34_envelope_field_types_are_checked_on_the_read_path() {
    let d = tmpdir("c34-types");
    let on = ontology(); // 出厂本体（`world` 声明 integer、`actor` 声明 string）
    let base = serde_json::json!({
        "world": 1,
        "kind": "change",
        "id": "e1-0",
        "seq": 1,
        "at": 1_790_540_855u64,
        "actor": "world://user",
        "flags": [],
        "body": { "subject": "world://notice/n", "path": "muted", "before": false, "after": true }
    });

    // 反例①：`world` 写成**字符串**（本体声明 integer）
    let mut a = base.clone();
    a["world"] = serde_json::json!("1");
    // 反例②：`actor` 写成**整数**（本体声明 string）
    let mut b = base.clone();
    b["actor"] = serde_json::json!(123);

    // `world` 那条**只要求"被拒 ＋ 带类型化码"**：它既有的版本那道会报 `BadVersion`（**既有契约，不抢**）。
    // `actor` 那条**没有人管**（版本/家族/信纸必填都碰不到它）⇒ 必须由本判据报，且**点名那一格**。
    for (name, ev, must_be_bad_field_type) in
        [("world-as-string", a, false), ("actor-as-int", b, true)]
    {
        let lp = d.join(format!("{name}.jsonl"));
        write_raw_jsonl(&lp, &[ev]);
        let err = World::open_readonly(&on, &lp, &policy())
            .err()
            .unwrap_or_else(|| panic!("{name}：读路径必须拒绝类型不符的信封，实得打开成功"));
        assert!(
            err.contains("ext.world."),
            "{name}：拒绝理由须是**类型化**错误码（不是一句泛泛的解析失败），实得：{err}"
        );
        if must_be_bad_field_type {
            assert!(
                err.contains("ext.world.Ontology.BadFieldType"),
                "{name}：这一格**没有别的判据管**，必须由类型判据报，实得：{err}"
            );
            assert!(
                err.contains("`actor`"),
                "{name}：报错须**点名那一格** `actor`，实得：{err}"
            );
        }
    }

    // 正控：同样的形状、类型改回声明 ⇒ 必须打开成功（否则这条判据是"见谁拒谁"）
    let lp_ok = d.join("ok.jsonl");
    write_raw_jsonl(&lp_ok, &[base]);
    assert!(
        World::open_readonly(&on, &lp_ok, &policy()).is_ok(),
        "正控：类型合规的同形账本必须打得开"
    );
}

// ── c35 ── **带着全部历史离开并独立复算**（`TC-078`）────────────────────────────
//
// 判据逐字（`WC-SRS-001` §五 `TC-078`）：「换一台机器、**只带账本** ⇒ 独立复算出同一状态」。
//
// **做法与它的射程（不冒充）**：折叠（`State::fold`）只吃**事件的字节**，不吃任何机器状态、
// 进程状态或外部文件 ⇒ 本用例在同一台机器上**换目录**（不同绝对路径）＋**只读账本**复算，
// 作为"换机器"的**可判代理**。**它不证明**"跨架构/跨字节序也一致"（那要真换机器，本用例管不到）。
//
// 四件事各自可判：
// ① 甲地建账（真落盘）⇒ 记下状态；
// ② **只把账本文件**搬到乙地（另一目录）⇒ 在那里复算，**不带甲地的任何东西**；
// ③ **正控**：复算出来的状态**非空**（否则"两边都空"也会相等，那是假绿）；
// ④ **反假**：把账本改一个字节 ⇒ 复算结果**必须变**（否则"相同"可能只是"它根本没读"）。
#[test]
fn c35_the_ledger_alone_reproduces_the_same_state_elsewhere() {
    let here = tmpdir("c35-here");
    let there = tmpdir("c35-there");
    let lp_a = here.join("history.jsonl");
    let on = ontology();
    let po = policy();

    // ① 甲地：建一本**有内容**的账（change ＋ act ＋ notice 三条）
    {
        let mut w = World::open(&on, &lp_a, &po).expect("甲地开世界");
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
        )
        .expect("change");
        w.commit(
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-c35", json!({})),
        )
        .expect("act");
        w.commit(
            "notice",
            "world://user",
            event::notice_body("probe.v1", "world://s", json!({ "c35": true })),
        )
        .expect("notice");
    }

    // ② **只带账本**：把账本文件复制到乙地（另一个目录、另一个绝对路径），甲地不参与
    let lp_b = there.join("history.jsonl");
    fs::copy(&lp_a, &lp_b).expect("复制账本");

    let read_lines = |p: &Path| -> Vec<Value> {
        fs::read_to_string(p)
            .expect("读账本")
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(|l| serde_json::from_str::<Value>(l).expect("账本行必须是 JSON"))
            .collect()
    };
    let state_a = world_core::ontology_instance::readmodel::State::fold(&read_lines(&lp_a))
        .expect("甲地复算")
        .to_json()
        .to_string();
    let state_b = world_core::ontology_instance::readmodel::State::fold(&read_lines(&lp_b))
        .expect("乙地复算（只带账本）")
        .to_json()
        .to_string();

    // ③ 正控：状态非空（防"两边都空"的假绿）
    assert!(
        !state_a.trim().is_empty() && state_a != "{}" && state_a != "null",
        "甲地状态是空的 ⇒ 本用例证明不了'能复算出同一状态'（假绿），实得：{state_a}"
    );
    assert!(
        state_a.contains("world://notice/n") || state_a.contains("muted"),
        "状态里看不到那三条事件留下的东西 ⇒ 复算可能没真读账本，实得：{state_a}"
    );

    // ② 的断言：乙地复算的结果与甲地**逐字节相同**
    assert_eq!(
        state_a, state_b,
        "只带账本换到另一个目录，复算出的状态**不同** ⇒ 账本不是自足的历史"
    );

    // ⑤ **本机依赖不许漏进状态**（SRS 的 `TC-078` 行里那条反例的**可判面**）：
    //    那条反例逐字是「注入一个只在本机存在的依赖（缓存／检查点／绝对路径）后仍判『相同』⇒ 判据失效」。
    //    本用例不伪造"注入"，而是**直接钉住它的反面**：状态 JSON 里**不得**出现甲地/乙地的目录，
    //    也**不得**出现账本文件名——只要状态里没有本机路径，那条反例就**无从立足**；
    //    哪天有人把本机路径（或缓存/检查点路径）写进状态，**这一条会红**。
    let here_s = here.to_string_lossy().to_string();
    let there_s = there.to_string_lossy().to_string();
    for (tag, s) in [
        ("甲地目录", here_s.as_str()),
        ("乙地目录", there_s.as_str()),
    ] {
        assert!(
            !state_b.contains(s),
            "状态里出现了{tag} `{s}` ⇒ 复算结果**依赖本机路径**（本机依赖漏进来了），实得：{state_b}"
        );
    }
    assert!(
        !state_b.contains("history.jsonl"),
        "状态里出现了账本文件名 ⇒ 复算结果**依赖本机文件名**，实得：{state_b}"
    );

    // ⑤ **进程维**（`REQ-N-009` 的口径逐字含「另一个目录／另一台机器／**另一个独立进程**」）：
    //    上面 ② 的两次复算是**同一个测试进程内直调** `State::fold` —— 它抓得到"进程内的非确定性"，
    //    **抓不到"本机文件依赖"**。所以这里补三段：独立进程跑、甲地放**本机缓存**（`checkpoint write`，
    //    CLI 自己说它是「缓存，非真相」）、再**毒化对照**。
    let bin = env!("CARGO_BIN_EXE_world-core");
    let run_state = |ledger: &Path| -> String {
        let out = Command::new(bin)
            .arg("--ontology")
            .arg(&on)
            .arg("--ledger")
            .arg(ledger)
            .arg("--policy")
            .arg(&po)
            .arg("state")
            .arg("--json")
            .output()
            .expect("跑真二进制");
        assert!(
            out.status.success(),
            "`state --json` 必须成功，实得 rc={:?}；stderr={}",
            out.status.code(),
            String::from_utf8_lossy(&out.stderr)
        );
        String::from_utf8(out.stdout).expect("stdout 必须是 UTF-8")
    };

    // 甲地：先落一份**本机缓存**（检查点）
    let ckpt = here.join("cache.checkpoint.json");
    let ck = Command::new(bin)
        .arg("--ontology")
        .arg(&on)
        .arg("--ledger")
        .arg(&lp_a)
        .arg("--policy")
        .arg(&po)
        .arg("checkpoint")
        .arg("write")
        .arg(&ckpt)
        .output()
        .expect("跑 checkpoint write");
    assert!(
        ck.status.success(),
        "`checkpoint write` 必须成功，实得 rc={:?}；stderr={}",
        ck.status.code(),
        String::from_utf8_lossy(&ck.stderr)
    );
    assert!(
        ckpt.is_file(),
        "甲地的本机缓存（检查点）必须真落盘 —— 没有它，下面那段「毒化对照」就无从谈起"
    );

    let proc_a = run_state(&lp_a);
    let proc_b = run_state(&lp_b);
    assert_eq!(
        proc_a, proc_b,
        "**两个独立进程**、乙地只带账本：`state --json` 的输出必须逐字节相同"
    );
    // ★ 2026-09-28（承评审席建议）：同样三条检查**也施加到 CLI 的输出** `proc_b` ——
    // 这样"状态里带了本机路径/文件名"这一类，**⑤ 自己也抓得到**，
    // 不必只靠下面那处"甲/乙两进程输出逐字节相同"的比对（评审席的变异 B 就是这一类）。
    for (tag, s) in [
        ("甲地目录", here_s.as_str()),
        ("乙地目录", there_s.as_str()),
    ] {
        assert!(
            !proc_b.contains(s),
            "CLI 的 `state --json` 输出里出现了{tag} `{s}` ⇒ **本机路径漏进了输出**，实得：{proc_b}"
        );
    }
    assert!(
        !proc_b.contains("history.jsonl"),
        "CLI 的 `state --json` 输出里出现了账本文件名 ⇒ **本机文件名漏进了输出**，实得：{proc_b}"
    );

    // **毒化对照**：把甲地那份本机缓存改坏 ⇒ 甲地再跑，结果**必须不变**
    fs::write(&ckpt, b"{ \"poisoned\": true }").expect("毒化缓存");
    let proc_a2 = run_state(&lp_a);
    assert_eq!(
        proc_a, proc_a2,
        "本机缓存被改坏之后，甲地的 `state --json` **变了** ⇒ 状态是从**缓存**来的，不是从账本重算的（本机依赖成立 ✗）"
    );
    // 而"核验检查点"这条判据**必须**对坏缓存失败（否则它也是装饰）
    let bad = Command::new(bin)
        .arg("--ontology")
        .arg(&on)
        .arg("--ledger")
        .arg(&lp_a)
        .arg("--policy")
        .arg(&po)
        .arg("checkpoint")
        .arg("verify")
        .arg(&ckpt)
        .output()
        .expect("跑 checkpoint verify");
    assert!(
        !bad.status.success(),
        "被毒化的检查点，`checkpoint verify` 竟判通过 ⇒ 那条核验是装饰"
    );

    // ④ 反假：改账本一个字节 ⇒ 结果必须变
    let mut tampered = read_lines(&lp_b);
    // 动**状态追踪的那个东西**：`change` 那条的 `body.after` 从 `true` 翻成 `false`
    // （★ 第一次我改的是 `at`，而状态 JSON 里根本没有 `at` ⇒ 反假当场红，是**我自己选的字段选错了**；
    //  教训：反假要动"被追踪的量"，不是随便动一个字节。）
    tampered[0]["body"]["after"] = json!(false);
    let state_t = world_core::ontology_instance::readmodel::State::fold(&tampered)
        .expect("改一个字段后仍应能折叠")
        .to_json()
        .to_string();
    assert_ne!(
        state_a, state_t,
        "把账本里 `change` 的 `body.after` 翻了面，复算结果却**没变** ⇒ '相同'可能是'它根本没读账本'"
    );
}

// ── c36 ── **已声明的信封格，至少有一份读法读得到**（`REQ-F-032` 的另一半 / `1.1`）──────
//
// `c34` 管的是"类型符不符"，`c35` 管的是"历史带不带得走"，`h08` 管的是"缺格即拒"与"覆盖表承重"。
// **本用例管的是**：法律声明的那几个信封格——`world` / `id` / `at` / `actor` / `flags`——
// **每一格都有一份读法读得到**（书那句「每个已声明的字段至少有一份读法可读」）。
//
// 逐格的**可读面**（现取事实，不是推测）：
// · `world` ⇒ **投影头部**（`project language` 的首行含 `world=`；见 `src/gui_projection/mod.rs::header_line`）；
// · `id`／`at`／`actor`／`flags` ⇒ **逐条读事件**（CLI `read` 把账本行原样打印成 JSON Lines）。
//
// **同时钉住"取舍"那一面**：这几格**不进** `state --json`（读模型是**折叠产物**，
// 世界状态按 `(主体, 路径)` 折叠 ⇒ 逐事件的 `id`／`at`／`actor`／`flags` 无处安放）。
// 那是**取舍**，不是缺口 —— 所以本用例**既断言"读得到"，也断言"状态里没有"**，两句一起才说得清。
#[test]
fn c36_every_declared_envelope_cell_is_readable_from_some_read_view() {
    let dir = tmpdir("c36");
    let lp = dir.join("history.jsonl");
    let on = ontology();
    let po = policy();
    {
        let mut w = World::open(&on, &lp, &po).expect("开世界");
        w.commit(
            "change",
            "world://user",
            event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
        )
        .expect("change");
    }
    let bin = env!("CARGO_BIN_EXE_world-core");
    let run = |args: &[&str]| -> String {
        let out = Command::new(bin)
            .arg("--ontology")
            .arg(&on)
            .arg("--ledger")
            .arg(&lp)
            .arg("--policy")
            .arg(&po)
            .args(args)
            .output()
            .expect("跑真二进制");
        assert!(
            out.status.success(),
            "`{args:?}` 必须成功，实得 rc={:?}；stderr={}",
            out.status.code(),
            String::from_utf8_lossy(&out.stderr)
        );
        String::from_utf8(out.stdout).expect("stdout 是 UTF-8")
    };

    // ① **逐格从本体派生**（`required ∪ optional`）——**不手抄格名**（新加一格自动进判据）；
    //    判据是**值**不是字样：把 `read` 的每一行**解析成 JSON**，与**账本那一行**逐键比。
    //    （评审席的对抗探针正是这一条的证据：让 `read` 打印 `"actor":null`（键在、值毁）时，
    //      "找字样"的写法仍然全绿——那是 skill §五「搜字样 ≠ 认结构」。）
    let ont_obj = world_core::ontology_definition::Ontology::load(&on).expect("加载本体");
    let mut declared = ont_obj.envelope_required();
    for f in ont_obj.envelope_optional() {
        if !declared.contains(&f) {
            declared.push(f);
        }
    }
    let raw = run(&["read"]);
    let ev: Value = serde_json::from_str(raw.lines().next().expect("`read` 必须有输出"))
        .expect("`read` 的首行必须是 JSON");
    let disk: Value = serde_json::from_str(
        fs::read_to_string(&lp)
            .expect("读账本")
            .lines()
            .next()
            .expect("账本必须有行"),
    )
    .expect("账本首行必须是 JSON");
    // **前提**：必填格必须都在账本里（否则下面的"逐格比"是空的）
    for f in &ont_obj.envelope_required() {
        assert!(
            disk.get(f).is_some(),
            "账本里连必填格 `{f}` 都没有 ⇒ 本用例的逐格比对无从谈起"
        );
    }
    let mut compared = 0usize;
    for f in &declared {
        if let Some(want) = disk.get(f) {
            assert_eq!(
                ev.get(f),
                Some(want),
                "`read` 里 `{f}` 的值与账本不一致（键在、值不对 ⇒ 读法退化），实得：{:?}",
                ev.get(f)
            );
            compared += 1;
        }
    }
    assert!(
        compared >= ont_obj.envelope_required().len(),
        "逐格比对只覆盖了 {compared} 格，少于必填格数 ⇒ 读法面没有查全"
    );

    // ② 投影头部 ⇒ `world` 以**本体声明的那个真实值**露出（不是找 `world=` 字样）
    let lang = run(&["project", "language"]);
    let head = lang.lines().next().unwrap_or("");
    assert!(
        head.contains(&format!("world={}", ont_obj.world())),
        "投影头部里读不到 `world={}`（本体的真值），实得首行：{head}",
        ont_obj.world()
    );

    // ③ **取舍那一面**：`state --json` 的**顶层键集合恰为**这五个
    //    （结构判据，不找字样：否则世界里真有一条名为 `actor` 的**路径**时会**假红**）
    let st: Value =
        serde_json::from_str(&run(&["state", "--json"])).expect("`state --json` 必须是 JSON");
    let mut keys: Vec<String> = st
        .as_object()
        .expect("`state --json` 必须是对象")
        .keys()
        .cloned()
        .collect();
    keys.sort();
    let mut want: Vec<String> = ["acts", "last_seq", "notices", "objects", "seen"]
        .iter()
        .map(|s| s.to_string())
        .collect();
    want.sort();
    assert_eq!(
        keys, want,
        "`state --json` 的顶层键集合不符 ⇒ 要么漏了状态面，要么把**逐事件格**混了进来（层间混淆）"
    );
}
