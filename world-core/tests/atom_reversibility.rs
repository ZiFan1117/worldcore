//! **可逆性判定与出厂配置互校**（书第五章 §5.5 判红的三条，逐条落成会红的断言）。
//!
//! ## 这一格原来红在哪（2026-09-27 的实测，逐条可核）
//!
//! | # | 书 §5.5 的原话 | 今天的实现 | 本文件的哪条断言把它钉住 |
//! |---|---|---|---|
//! | ① | 「这一项本来要成为闸侧的判据，而**闸读不到它**」 | `gate.rs` 的评级里只有一个 `reversible` 布尔 | `a03`（闸读到的等级 == 清单写的）、`a05`（等级出现在拒绝流水里） |
//! | ② | 「载体可逆与世界可逆这两处之间**没有互校**」 | 两处各写各的，谁也核对过 | `a01`（冲突 ⇒ **拒启**）、`a02`（一致 ⇒ 正常启动） |
//! | ③ | 「摩擦本该挂在**动作的不可逆等级**上：可逆处放手，不可逆处加摩擦。**今天它挂在执行者的身份上**」 | 白名单主体执行不可逆动作 ⇒ `Allow` 且**零痕迹** | `a04`（同一主体：可逆不带摩擦 / 不可逆必带摩擦且落账） |
//!
//! ## 每条断言的"会红"条件（改坏哪一行会打红哪一条）
//!
//! - `a01` ← `src/gate/mod.rs` 的 `cross_check_reversibility` 里那句
//!   `return Err(format!("ext.world.Gate.ReversibilityMismatch: …`)：删掉它（或让它恒 `Ok`）
//!   ⇒ `a01` 变红（冲突配置竟能启动）。
//! - `a02` ← 同函数的判据取反（例如把 `carrier_says_reversible != cap.reversible`
//!   写成 `==`）⇒ 一致配置也被拒 ⇒ `a02` 变红。
//!   另一条变异：把载体侧可逆性改用 `undo` 导出（`m.undo == Undo::Never` 之类）
//!   ⇒ 出厂 `ledger.compact`（`undo: before-each` + `reversible: false`）被误判冲突
//!   ⇒ `a02`、`a03` 一起变红。**书 §5.5 逐字说过这两个轴不能互相推出**（`undo` 撤的是
//!   文件系统上的字节），所以这条变异是"改回书判红的那个读法"。
//! - `a03` ← `Policy::load` 里 `cap.risk = carrier.lookup(name).map(|m| m.risk);`：
//!   删掉它 ⇒ 闸读不到等级（`risk == None`）⇒ `a03` 变红。
//! - `a04` ← `Policy::verdict` 里 `.filter(|c| !c.reversible)` 那段：
//!   换成"看 `agent` 是不是白名单"（即书判红的旧口径：摩擦挂在执行者身份上）
//!   ⇒ 白名单主体执行不可逆动作时 `friction == None` ⇒ `a04` 变红。
//! - `a05` ← `src/gate/mod.rs` 的 `decide` 里 `level = self.level_name(c)`：
//!   去掉它 ⇒ 拒绝流水里读不到等级 ⇒ `a05` 变红。

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::carrier::capd::Risk;
use world_core::{event, World};

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-atomrev-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    // 出厂法律不得对 group/other 可写（`src/gate/guard.rs`）；umask 非 022 时
    // `create_dir_all` 可能建出 0777 的目录，那会让"拒启"的**理由**变成权限而不是互校，
    // 断言就失去了判别力。故显式收紧。
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn factory_ontology() -> PathBuf {
    manifest_dir().join("src/ontology_definition/ontology.json")
}

fn factory_policy() -> PathBuf {
    manifest_dir().join("src/gate/policy.json")
}

/// 写一份合法的临时策略（含 `writes` 段——默认拒绝要求它必须存在）。
///
/// ## 本批起是**两层**（夹具的输入形态随之变了）
///
/// 入参 `caps` 的每一项带 `kind`（能力层）与 `reversible`（动作层）；本函数把它
/// **拆成两层**落盘：`capabilities.<名字>.kind` ＋ `actions.<名字>.capability/reversible`
/// （出厂 `policy.json` 同形；判据见 `src/gate/mod.rs::Policy::load`）。
/// ⇒ 调用点的夹具**没变宽**（仍是"一项能力一条动作"这个最小形态），
/// 变的是它落到哪一层——两层的拆法在**这里**写一次。
fn write_policy(dir: &Path, caps: Value) -> PathBuf {
    let mut capabilities = serde_json::Map::new();
    let mut actions = serde_json::Map::new();
    for (name, spec) in caps.as_object().expect("caps 必须是对象") {
        capabilities.insert(
            name.clone(),
            json!({ "kind": spec.get("kind").cloned().unwrap_or(json!("invoke")) }),
        );
        actions.insert(
            name.clone(),
            json!({
                "capability": name,
                "reversible": spec.get("reversible").cloned().unwrap_or(json!(true)),
            }),
        );
    }
    let p = dir.join("src/gate/policy.json");
    fs::write(
        &p,
        serde_json::to_string_pretty(&json!({
            "policy": 1,
            "capabilities": Value::Object(capabilities),
            "actions": Value::Object(actions),
            "subjects": { "allow": ["world://user", "world://agent/*"] },
            "writes": { "world://user": ["world://*"] },
            "irreversible_actors": ["world://user"]
        }))
        .unwrap(),
    )
    .unwrap();
    p
}

/// **本文件专用的测试本体**：出厂本体 ＋ 追加若干**能力**（`_interfaces`）与
/// 对应的**动作**（`_actions`）。
///
/// 为什么必须有它（本批新）：`World::open` 会核「闸侧的能力 ⊆ 本体的 `_interfaces`」
/// （`ext.world.Gate.CapabilityNotInOntology`）⇒ 一份**只改策略**的夹具再也起不来。
/// 本函数按与 `write_policy` **同一个入参**（`caps` 的键集）补本体那一侧，
/// 于是"两处同名"这件事在夹具里是**构造出来的**，不是顺手写对的。
fn write_ontology(dir: &Path, caps: &Value) -> PathBuf {
    let text = fs::read_to_string(manifest_dir().join("src/ontology_definition/ontology.json")).unwrap();
    let mut v: Value = serde_json::from_str(&text).unwrap();
    for (name, spec) in caps.as_object().expect("caps 必须是对象") {
        let kind = spec.get("kind").cloned().unwrap_or(json!("invoke"));
        v["_interfaces"][name] = json!({ "kind": kind, "what": "夹具：本文件专用" });
        v["_actions"][name] = json!({
            "capability": name,
            "reversible": spec.get("reversible").cloned().unwrap_or(json!(true))
        });
    }
    let p = dir.join("ontology-with-fixture-caps.json");
    fs::write(
        &p,
        format!("{}\n", serde_json::to_string_pretty(&v).unwrap()),
    )
    .unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&p, fs::Permissions::from_mode(0o600)).unwrap();
    }
    p
}

/// 写一份载体执行清单（`cap.d/<name>.json`）。
fn write_manifest(dir: &Path, name: &str, risk: &str, undo: &str, confirm: &str) {
    let d = dir.join("cap.d");
    fs::create_dir_all(&d).unwrap();
    fs::write(
        d.join(format!("{name}.json")),
        serde_json::to_string_pretty(&json!({
            "capability": name,
            "provider": "package",
            "verbs": ["do", "list"],
            "risk": risk,
            "undo": undo,
            "confirm": confirm,
            "sandbox": "none"
        }))
        .unwrap(),
    )
    .unwrap();
}

fn flags_of(ev: &Value) -> Vec<String> {
    ev.get("flags")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

/// **a01**：两处配置互校冲突 ⇒ **拒绝启动**，且不落笔。
///
/// 冲突是刻意造出来的、可逐字核：世界侧说 `ledger.compact` **不可逆**，
/// 载体清单说它 `risk=low`、`confirm=never`（⇒ 载体侧判**可逆**）。
/// 这正是书 §5.5 要的那道互校：两处对不上就不许起。
#[test]
fn a01_conflicting_reversibility_refuses_to_start() {
    let d = tmpdir("a01");
    let pol = write_policy(
        &d,
        json!({
            "ledger.compact": { "reversible": false },
            "notice.mute":    { "reversible": true }
        }),
    );
    // 载体侧与上面那句相反：低危、不需确认 ⇒ 载体侧判「可逆」。
    write_manifest(&d, "ledger.compact", "low", "never", "never");

    let lp = d.join("ledger.jsonl");
    // ⚠ 用 `expect_err` 而不是 `.err().expect(…)`：后者会触发 clippy 的 `err_expect`
    //   （`cargo clippy --all-targets -- -D warnings` 下是硬错，smoke 作业会因此变红）。
    let e = World::open(&factory_ontology(), &lp, &pol)
        .expect_err("两处配置冲突时必须拒绝启动，实得：启动成功");

    assert!(
        e.contains("ext.world.Gate.ReversibilityMismatch"),
        "拒绝理由必须带点名错误码，实得：{e}"
    );
    assert!(e.contains("ledger.compact"), "必须点名是哪个能力：{e}");
    assert!(
        e.contains("reversible=false"),
        "必须写出世界侧写了什么：{e}"
    );
    assert!(e.contains("risk=low"), "必须写出载体侧写了什么：{e}");
    assert!(
        e.contains("拒绝启动"),
        "必须说清后果是拒启，而不是警告：{e}"
    );
    // 拒启发生在打开账本之前 ⇒ **一个字节都没落**
    assert!(!lp.exists(), "拒启时不得创建账本：{}", lp.display());
}

/// **a02**：两处一致 ⇒ **正常启动**（防"恒红"：没有这条，a01 可能是因为"什么都拒"而通过）。
///
/// 同一份策略、同一项能力，只把载体清单改成与它同向（`risk=high`、`confirm=required`
/// ⇒ 载体侧也判不可逆）⇒ 必须起得来。
///
/// 顺带钉住**一条口径**：`undo` **不参与**互校。第三项 `job.start` 世界侧说**可逆**，
/// 载体清单里却留了撤销点（`undo: before-each`）——它必须照样启动。
/// 依据是书 §5.5 逐字：「这两句问的是两件事……**两个轴各自成立，谁也不能推出谁**」。
/// 变异：把"留了撤销点"当成"载体侧不可逆"（正是书判红的那个读法）⇒ 第三项被误判冲突
/// ⇒ 本条变红。
#[test]
fn a02_consistent_reversibility_starts_normally() {
    let d = tmpdir("a02");
    let pol = write_policy(
        &d,
        json!({
            "ledger.compact": { "reversible": false },
            "notice.mute":    { "reversible": true },
            "job.start":      { "reversible": true }
        }),
    );
    write_manifest(&d, "ledger.compact", "high", "before-each", "required");
    // `notice.mute` 两侧同向：可逆 ↔ 低危、不需确认。
    write_manifest(&d, "notice.mute", "low", "never", "never");
    // `undo` 不参与互校：世界侧可逆 + 载体侧留了撤销点 = **正常**，不是冲突。
    write_manifest(&d, "job.start", "low", "before-each", "never");

    let lp = d.join("ledger.jsonl");
    let w = World::open(&factory_ontology(), &lp, &pol).expect("两处一致时必须能启动");
    assert_eq!(w.policy().version(), 1);
    assert!(w.policy().carrier_dir().is_some(), "互校过的目录要能读出来");
}

/// **a03**：出厂配置本身互校通过，且**闸读得到风险等级**。
///
/// 这一条同时是"出厂配置到底一不一致"的机械答案：出厂的 `policy.json` 与
/// `cap.d/*.json` 若哪天对不上，这里会**拒启**（`World::open` 返回 `Err`），测试变红。
#[test]
fn a03_gate_reads_the_risk_level_of_the_factory_config() {
    let d = tmpdir("a03");
    let lp = d.join("ledger.jsonl");
    let w = World::open(&factory_ontology(), &lp, &factory_policy())
        .expect("出厂配置两处必须一致（否则世界起不来）");

    // ⚠ 本批起**两层**：`risk`（闸读到的等级）在**能力层**，`reversible` 在**动作层**
    // （同一项能力可以有可逆与不可逆两种动作 ⇒ 可逆性不是能力的性质）。
    let caps: Vec<(String, Option<Risk>)> = w
        .policy()
        .capabilities()
        .map(|(n, c)| (n.to_string(), c.risk))
        .collect();
    let find = |name: &str| {
        caps.iter()
            .find(|(n, _)| n == name)
            .unwrap_or_else(|| panic!("出厂策略里应有能力 `{name}`：{caps:?}"))
    };
    let rev_of = |name: &str| {
        w.policy()
            .action(name)
            .unwrap_or_else(|| panic!("出厂策略里应有动作 `{name}`"))
            .reversible
    };

    // 有执行清单的三项：等级必须与 `cap.d/*.json` 里写的一致。
    assert_eq!(find("ledger.compact").1, Some(Risk::High));
    assert!(!rev_of("ledger.compact"));
    assert_eq!(find("notice.mute").1, Some(Risk::Low));
    assert!(rev_of("notice.mute"));
    assert_eq!(find("job.start").1, Some(Risk::Low));

    // 没有执行清单的能力：等级**读不到**（`None`），不得被当成低危。
    assert_eq!(
        find("world.rekey").1,
        None,
        "没有清单 ⇒ 等级未声明；把它当 low 是悄悄放宽"
    );
}

/// **a04**：摩擦挂在**动作的不可逆等级**上——同一个主体，两种动作，两种结论。
///
/// 这条是"摩擦不挂在身份上"的判别性断言：**主体恒为 `world://user`（不可逆白名单里
/// 唯一的那一个）**，只换动作——
///
/// - 可逆动作（`notice.mute`）⇒ 免检（`Allow`），事件**不带**摩擦旗标，但照样落账（留痕）；
/// - 不可逆动作（`ledger.compact`）⇒ **必加摩擦**：事件带上 `gate.friction:high`，
///   且这条旗标随事件**落进账本**（可核流水）。
///
/// 旧口径（摩擦看身份）下，第二句拿不到任何痕迹 ⇒ 本测试变红。
#[test]
fn a04_same_actor_reversible_is_free_and_irreversible_always_carries_friction() {
    let d = tmpdir("a04");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();

    // ① 可逆动作：免检但留痕
    let rev = w
        .commit(
            "act",
            "world://user",
            event::act_body("notice.mute", "do", "r-a04-rev", json!({})),
        )
        .expect("可逆动作应当免检");
    assert_eq!(rev["kind"], json!("act"));
    assert!(
        flags_of(&rev).is_empty(),
        "可逆动作不得带摩擦旗标，实得 {:?}",
        flags_of(&rev)
    );

    // ② 不可逆动作、**同一个主体**：必加摩擦，且摩擦随事件落账
    let irr = w
        .commit(
            "act",
            "world://user",
            event::act_body("ledger.compact", "do", "r-a04-irr", json!({})),
        )
        .expect("白名单主体仍应能执行不可逆动作（v1 无审批通道，否则它是死号）");
    let flags = flags_of(&irr);
    assert!(
        flags.iter().any(|f| f == "gate.friction:high"),
        "不可逆动作**必加摩擦**且要带上不可逆等级，实得 flags={flags:?}"
    );

    // ③ 留流水：从**账本**读回同一条事件，旗标仍在（不是内存里的一次性字段）
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 2, "两条 act 都落账：{all:?}");
    let back = all
        .iter()
        .find(|ev| ev["id"] == irr["id"])
        .expect("带摩擦的那条 act 必须在账本里");
    assert!(
        flags_of(back).iter().any(|f| f == "gate.friction:high"),
        "摩擦痕迹必须随事件落账（可核流水），实得 {:?}",
        flags_of(back)
    );
    // 可逆那条也在账本里（免检 ≠ 不记）
    assert!(
        all.iter().any(|ev| ev["id"] == rev["id"]),
        "可逆动作免检但必须留痕"
    );
}

/// **a05**：摩擦的**另一面**——白名单外的主体拿到的是"加摩擦到拒绝执行"，
/// 且流水里读得到**动作的风险等级**（书 §5.5 第三条：闸读不到风险等级）。
#[test]
fn a05_non_whitelisted_actor_gets_friction_and_the_level_shows_in_the_flow() {
    let d = tmpdir("a05");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();

    let err = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("ledger.compact", "do", "r-a05", json!({})),
        )
        .expect_err("白名单外的主体不得执行不可逆动作");
    assert!(err.contains("门禁加摩擦"), "实得：{err}");
    assert!(err.contains("不可逆"), "实得：{err}");
    assert!(
        err.contains("风险等级") && err.contains("high"),
        "闸必须**读得到**风险等级，并把它写进拒绝理由（否则这一格仍是红的）：{err}"
    );
    assert!(
        err.contains("没有审批通道") && err.contains("不要等批准"),
        "v1 没有审批通道，措辞不许骗人：{err}"
    );

    // 加摩擦也要留痕：一条 `gate.awaiting-approval` 流水，理由里同样带等级
    let all = w.ledger().read_all().unwrap();
    assert_eq!(all.len(), 1, "被拒的 act 不落笔，只留一条流水：{all:?}");
    assert_eq!(all[0]["body"]["type"], json!("gate.awaiting-approval"));
    let reason = all[0]["body"]["payload"]["reason"].as_str().unwrap_or("");
    assert!(
        reason.contains("high"),
        "流水里要读得到等级，实得：{reason}"
    );
}

/// **a06**（任务 3.3，按实现改写后的措辞）：`risk` 的**实际角色**——
/// 它**不**单独决定放行/拒绝（那由 `reversible` 与 `irreversible_actors` 裁决），
/// 但**决定摩擦的轻重与拒绝流水里的等级**（`gate.friction:low/medium/high/unlisted`）。
///
/// ## 判别性夹具（三格，逐格可核）
///
/// | 能力 | 世界侧 `reversible` | 清单 `risk`/`confirm` | 载体侧推出 | `world://user` | `world://agent/1` |
/// |---|---|---|---|---|---|
/// | `notice.mute` | `true` | **low** / never | 可逆 | Allow、**无**摩擦 | Allow（可逆 ⇒ 免检） |
/// | `ledger.compact` | `false` | **low** / required | 不可逆 | Allow ＋ `gate.friction:low` | AwaitApproval，流水写 **low** |
/// | `world.migrate` | `false` | **high** / never | 不可逆 | Allow ＋ `gate.friction:high` | AwaitApproval，流水写 **high** |
///
/// 两句合起来才说明"`risk` 不决定放行"：
/// - `notice.mute` 与 `ledger.compact` 的 **`risk` 相同（都 low）而结论相反** ⇒ 差别只能来自 `reversible`；
/// - `ledger.compact` 与 `world.migrate` 的 **`reversible` 相同（都不可逆）而等级不同** ⇒ 差别只能来自 `risk`。
///
/// ## 变异
///
/// 把 `gate.rs` 里 `decide` 的 `level = self.level_name(c)` 换成常量
/// ⇒ 流水里的等级不再随 `risk` 变 ⇒ 本条变红（"闸读得到风险等级"就没有对外痕迹了）。
#[test]
fn a06_risk_sets_friction_weight_but_not_the_verdict() {
    use world_core::gate::Decision;

    let d = tmpdir("a06");
    let caps = json!({
        "notice.mute":    { "reversible": true },
        "ledger.compact": { "reversible": false },
        "world.migrate":  { "reversible": false }
    });
    let pol = write_policy(&d, caps.clone());
    // 本体的 `_interfaces`／`_actions` 必须与策略**同名同义**（`World::open` 逐项核）
    let ont = write_ontology(&d, &caps);
    // 可逆 + 低危：与下面那项 **risk 相同**，用来证明"risk 不决定放行"。
    write_manifest(&d, "notice.mute", "low", "never", "never");
    // 不可逆 + 低危（`confirm: required` ⇒ 载体侧同判不可逆，互校一致）。
    write_manifest(&d, "ledger.compact", "low", "never", "required");
    // 不可逆 + 高危：与上面那项 **reversible 相同**，用来证明"等级来自 risk"。
    write_manifest(&d, "world.migrate", "high", "never", "never");

    let lp = d.join("ledger.jsonl");
    let mut w =
        World::open(&ont, &lp, &pol).expect("夹具两处必须互校一致，否则本用例测的是拒启而不是等级");

    {
        let p = w.policy();

        // ① 摩擦的**轻重**由动作的 risk 决定
        let rev = p.verdict(
            "world://user",
            &json!({"capability": "notice.mute", "verb": "do"}),
        );
        assert_eq!(rev.decision, Decision::Allow);
        assert!(
            rev.friction.is_none(),
            "可逆动作免检：不得带摩擦，实得 {:?}",
            rev.friction
        );
        let low = p.verdict(
            "world://user",
            &json!({"capability": "ledger.compact", "verb": "do"}),
        );
        assert_eq!(
            low.decision,
            Decision::Allow,
            "白名单主体仍放行——**放行不吃 risk 这一档**"
        );
        assert_eq!(
            low.friction.as_ref().map(|f| f.flag()),
            Some("gate.friction:low".to_string()),
            "摩擦轻重来自动作的 risk=low"
        );
        let high = p.verdict(
            "world://user",
            &json!({"capability": "world.migrate", "verb": "do"}),
        );
        assert_eq!(high.decision, Decision::Allow);
        assert_eq!(
            high.friction.as_ref().map(|f| f.flag()),
            Some("gate.friction:high".to_string()),
            "同一主体、同一「不可逆」档，只因 risk 不同 ⇒ 旗标不同"
        );

        // ② **risk 不决定放行/拒绝**（同一个 risk=low，两项结论相反）
        assert_eq!(
            p.decide(
                "world://agent/1",
                &json!({"capability": "notice.mute", "verb": "do"})
            ),
            Decision::Allow,
            "可逆 ⇒ 白名单外也放行（risk 相同的那一项却不行，差别只能来自 reversible）"
        );

        // ③ **等级出现在拒绝流水里**，且是这一项自己的等级
        let m_low = match p.decide(
            "world://agent/1",
            &json!({"capability": "ledger.compact", "verb": "do"}),
        ) {
            Decision::AwaitApproval(m) => m,
            other => panic!("不可逆 + 白名单外 ⇒ 加摩擦到拒绝，实得 {other:?}"),
        };
        let m_high = match p.decide(
            "world://agent/1",
            &json!({"capability": "world.migrate", "verb": "do"}),
        ) {
            Decision::AwaitApproval(m) => m,
            other => panic!("不可逆 + 白名单外 ⇒ 加摩擦到拒绝，实得 {other:?}"),
        };
        assert!(m_low.contains("风险等级：low"), "实得：{m_low}");
        assert!(
            !m_low.contains("high"),
            "等级必须来自**这一项**的 risk，不许混进别人的：{m_low}"
        );
        assert!(m_high.contains("风险等级：high"), "实得：{m_high}");
        assert!(
            !m_high.contains("low"),
            "等级必须来自**这一项**的 risk，不许混进别人的：{m_high}"
        );
    }

    // ④ 等级要**落进账本**（不只是内存里的一个字段）
    let e_low = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("ledger.compact", "do", "r-a06-low", json!({})),
        )
        .unwrap_err();
    assert!(e_low.contains("风险等级：low"), "实得：{e_low}");
    let e_high = w
        .commit(
            "act",
            "world://agent/1",
            event::act_body("world.migrate", "do", "r-a06-high", json!({})),
        )
        .unwrap_err();
    assert!(e_high.contains("风险等级：high"), "实得：{e_high}");

    let all = w.ledger().read_all().unwrap();
    let flows: Vec<String> = all
        .iter()
        .filter(|ev| ev["body"]["type"] == json!("gate.awaiting-approval"))
        .map(|ev| format!("{}", ev["body"]["payload"]["reason"]))
        .collect();
    assert_eq!(flows.len(), 2, "两次加摩擦各留一条流水：{all:?}");
    assert!(
        flows[0].contains("low") && !flows[0].contains("high"),
        "第一条流水的等级必须是 low：{}",
        flows[0]
    );
    assert!(
        flows[1].contains("high") && !flows[1].contains("low"),
        "第二条流水的等级必须是 high：{}",
        flows[1]
    );
}

/// **a07**（任务 3.4）：**载体撤销点（`undo: before-each`）不参与互校，
/// 也不被当作世界可逆的依据**。
///
/// ## 夹具
///
/// 同一项能力、同一份世界侧声明（`job.start` 世界侧 `reversible: true`），
/// 两份载体清单**只差 `undo` 一个字段**（`before-each` / `never`）。
///
/// ## 三件事一起断言
///
/// 1. 两份夹具的 `undo` 字段**确实不同**（否则"结论相同"可能只是因为两份一样）；
/// 2. 两份**都能启动**——`undo` 不参与互校：留了撤销点**不等于**"载体侧判不可逆"；
/// 3. 两份给出的世界侧等级与裁决**完全相同**，都等于 `policy.json` 里写的那句——
///    `undo` **不是**"世界可不可逆"的依据。
///
/// 依据：`src/carrier/mod.rs:32` 的表格逐字——载体撤销撤的是**文件系统上的字节**，
/// 「不是世界状态；只作工程兜底，**不得**用于满足『坏了能回滚』」；
/// 书 §5.5 逐字「两个轴各自成立，谁也不能推出谁」。
///
/// ## 变异
///
/// 把 `cross_check_reversibility` 的判据从 `risk`/`confirm` 换成读 `undo`
/// ⇒ 两份夹具里必有一份被判冲突 ⇒ 那一份**拒启** ⇒ 本条变红（同族的 `a02` 亦红）。
#[test]
fn a07_carrier_undo_is_neither_cross_checked_nor_a_proof_of_world_reversibility() {
    use world_core::carrier::capd::Undo;
    use world_core::gate::Decision;

    let mk = |tag: &str, undo: &str| -> (PathBuf, PathBuf, PathBuf) {
        let d = tmpdir(tag);
        let caps = json!({ "job.start": { "reversible": true } });
        let pol = write_policy(&d, caps.clone());
        let ont = write_ontology(&d, &caps);
        write_manifest(&d, "job.start", "low", undo, "never");
        (d, pol, ont)
    };
    let (da, pol_a, ont_a) = mk("a07-undo-before-each", "before-each");
    let (db, pol_b, ont_b) = mk("a07-undo-never", "never");

    fn undo_of(w: &World) -> Undo {
        w.policy()
            .carrier_manifest()
            .iter()
            .find(|c| c.name == "job.start")
            .expect("清单里必须有 job.start")
            .undo
    }

    let wa = World::open(&ont_a, &da.join("ledger.jsonl"), &pol_a).expect(
        "世界侧可逆 + 载体侧留了撤销点 = **书明说的正常形态**，必须能启动（undo 不参与互校）",
    );
    let wb = World::open(&ont_b, &db.join("ledger.jsonl"), &pol_b)
        .expect("世界侧可逆 + 载体侧不留撤销点 ⇒ 同样必须能启动");

    assert_eq!(undo_of(&wa), Undo::BeforeEach, "夹具 A 的 undo 字段");
    assert_eq!(undo_of(&wb), Undo::Never, "夹具 B 的 undo 字段");
    assert_ne!(
        undo_of(&wa),
        undo_of(&wb),
        "两份夹具必须**只差** undo 这一格，否则第 2/3 条断言证明不了任何事"
    );

    for (tag, w) in [("undo=before-each", &wa), ("undo=never", &wb)] {
        let cap = w
            .policy()
            .carrier_manifest()
            .iter()
            .find(|c| c.name == "job.start")
            .expect("清单里必须有 job.start");
        assert_eq!(cap.risk, Risk::Low, "{tag}：等级仍取自清单的 risk");
        let v = w.policy().verdict(
            "world://user",
            &json!({"capability": "job.start", "verb": "do"}),
        );
        assert_eq!(
            v.decision,
            Decision::Allow,
            "{tag}：世界侧说可逆 ⇒ 免检放行（世界可不可逆由 policy.json 说了算，不由 undo 推出）"
        );
        assert!(
            v.friction.is_none(),
            "{tag}：可逆动作不得带摩擦旗标，实得 {:?}",
            v.friction
        );
    }
}
