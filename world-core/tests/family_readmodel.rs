//! **家族演进与向前兼容**（`REQ-F-027`）＋ **读模型侧的缺格**（`REQ-F-032`）。
//!
//! ## 这一格原来红在哪（逐字，可核）
//!
//! `WC-SRS-001-v0.1.md:82` 逐字：「`REQ-F-027` ｜ 家族演进与向前兼容 ｜ P1 ｜ 未实现
//! （仅"版本不符即拒收"已实现并由 TC-040 断言③覆盖；**演进与向前兼容的判据无实现、无用例**）」。
//! 书第五章 5.6 表 5.2 行（合订本 `:737`）逐字：「读的那一份每个格子都有人读得到 ｜
//! 每个已声明的字段至少有一份读法可读，缺格就报错 ｜ 缺格即报错 ｜ **红**。未实现」。
//! `tools/s1_sys_probe.sh` 的 `TC-047` ⑨ 把"缺格"那一格的现状登记成（逐字）：
//! 「缺必填信封字段 actor 竟**被接受**（rc=$R）：**必填字段**校验只在写入路径（本体校验）上，
//! 折叠层不校验 —— REQ-F-028 判据② 对本字段**不成立**」。
//!
//! ## 依据（逐字，六处）
//!
//! | 出处 | 逐字 |
//! |---|---|
//! | 书 §2.7（合订本 `:305`） | 「领域里的概念，诸如订单、曲目、告警、工序，都不属于这一层，各自在自己的命名空间里往上长。往上长的时候不需要全体重新商量，因为核心不动，扩展各自进行」 |
//! | 书 §2.7（合订本 `:313`） | 「核心之外由命名空间扩展，各方在自己的空间里定义自己的概念；核心之内不取交集，也不做删减」 |
//! | 书 §4.1（合订本 `:499`） | 「记录进账本只有一条路：世界先给它一个位置号，再照固定形式把它写全，然后问两件事——形式对不对、这件事准不准做。两件都过了，才落笔」 |
//! | 书 §4.1（合订本 `:503`） | 「把写入收在一处，理由只有一条：防"两本账"」 |
//! | 书 §5.6 表 5.2（合订本 `:737`） | 「每个已声明的字段至少有一份读法可读，缺格就报错」／「**红**。未实现」 |
//! | `ontology.json:9`／`:28`／`:33`／`:38` | `"required": ["world","kind","id","seq","at","actor","flags","body"]`／`["subject","path","before","after"]`／`["capability","verb","request_id"]`／`["type","subject"]` |
//!
//! ## 每条断言的"会红"条件（改坏哪一行 ⇒ 打红哪一条；逐条在 VM 上做过，原始输出见交付回执）
//!
//! | 断言 | 改坏哪一行 ⇒ 变红 |
//! |---|---|
//! | `h01` | `readmodel::DeclaredCells::missing_cell` 的家族必填格按"**全部家族**"取（不看这一行的 `kind`）⇒ 旧账本行缺 `audit` 的那两格 ⇒ `h01`／`h03` 红，而 `h04` 仍绿 |
//! | `h02` | `readmodel::State::apply` 的 `other => Err(ReadModel.UnknownKind)` 改成静默跳过 ⇒ `h02` 红（`e03`／`acceptance::t8` 同时红——同一条判据的三处载体） |
//! | `h03` | `readmodel::State::apply_change` 把信纸上**它不认识的格**也收进状态 ⇒ `h03` 红 |
//! | `h04` | `DeclaredCells::missing_cell` 的必填格核对恒不报（`if !obj.contains_key(f)` 改成 `if false`）⇒ `h04` 红、`h06` 仍绿；只把 [`MissingCell`] 的**点名**去掉 ⇒ **只** `h04` 的"点名那一格"断言红 |
//! | `h05` | 把 `src/lib.rs::read_model` 换回**无法律**的 `State::fold`（那一行就是接线点）⇒ `h05` 红，且 `tools/s1_sys_probe.sh` 的 `TC-047` ⑨ 一起红 |
//! | `h06` | `State::apply_declared` 的空表拒绝改成默默放行 ⇒ `h06` 红 |
//! | `h07` | `Ontology::family_required` 把 `optional` 也并进"必填格" ⇒ `h07` 红；`ontology.json` 被就地改动 ⇒ `h07` 的**词表身份**断言红 |
//!
//! ## ★ 3.3 撤回（`r01`–`r06`）的反例面（逐条在 VM 上做过，原始输出见交付回执）
//!
//! 口径一句话：**撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
//!
//! | 断言 | 短路它声称的那一步 ⇒ 必须红 |
//! |---|---|
//! | `r01` | 把 `State::apply_change` 的 `before` 核对改成**容错跳过**（`Some(_) => {}`）⇒ ① 的"撤回**前**必须拒"当场绿 ⇒ `r01` 红（**绝不用松校验换"能折叠"**） |
//! | `r02` | 把被撤回的那条**从账本里删掉**（而不是撤回）⇒ `r02` ① 红（账本行数变了、id 不在了）：**那是删除，不是撤回** |
//! | `r03` | 把 `State::scan_retractions` 的三条存在性／重复／对象检查短路（`if false`）⇒ `r03` 红（三条错码都没了） |
//! | `r04` | 把撤回**只放进内存**（不落账本行）⇒ `r04` ① 红（文件里没有 `retract_seq` 那一行）；② 又用**另一个进程**读回，钉住"它不是内存里的一层壳" |
//! | `r05` | 把 `fold_declared` 里的"被撤回 ⇒ `advance_only`"整段删掉 ⇒ 被撤回的那条效果照旧落账（`true`）⇒ `r05` 红 |
//! | `r06` | 往 `State::to_json` 里**加一个键**（把撤回事实塞进规范形式）⇒ `r06` 的"顶层键恰为五个"与"与改动前逐字节相同"两条**同时红** |
//!
//! ## 诚实边界（不许读成"已完备"）
//!
//! - **命令这一级也接上了**（2026-09-28）：装配处（`src/lib.rs::read_model`）把"已声明格"
//!   以**纯数据**递给读模型 ⇒ `state --json` 对缺格行 `rc=2` 并点名那一格（`h05` 端到端断言；
//!   系统级同一条在 `tools/s1_sys_probe.sh` 的 `TC-047` ⑨）。依赖方向留在装配处，
//!   读模型仍**零生产出边**（`WC-MODREG-001` §2 给 `M03` 的口径）。
//! - 读模型**不渲染**信封的 `id`／`at`／`actor`／`world`／`flags`：书那句"每个已声明的字段
//!   至少有一份读法可读"在**必填格**这一半成立（缺了即拒），另一半（每格都**读得出来**）**仍未成立**。
//! - 读模型认得的家族仍是**编译进去的三家族**（`M03` 不许 `use crate::ontology_definition::…`，
//!   见 `WC-MODREG-001` §2 给 `M03` 的口径「无（生产代码零出边）」）⇒「新家族怎么加」
//!   在读法侧的回答是"**要连读法一起加**"：只加本体的家族，读模型**拒**（`h02` ③ 即此）。

use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use world_core::ontology_definition::Ontology;
use world_core::ontology_instance::readmodel::{DeclaredCells, State, RETRACT_PATH};
use world_core::{common::event, World};

// ────────────────────────── 夹具 ──────────────────────────

fn tmpdir(tag: &str) -> PathBuf {
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-famrm-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    }
    d
}

#[cfg(unix)]
fn chmod600(p: &Path) {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(p, fs::Permissions::from_mode(0o600)).unwrap();
}

#[cfg(not(unix))]
fn chmod600(_p: &Path) {}

fn manifest_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn factory_ontology() -> PathBuf {
    manifest_dir().join("src/ontology_definition/ontology.json")
}

fn factory_policy() -> PathBuf {
    manifest_dir().join("src/gate/policy.json")
}

/// 造一份临时本体：读出厂本体 → 按 `edit` 改 → 落盘（`0600`，静态墙要求）。
fn write_ontology(dir: &Path, name: &str, edit: impl FnOnce(&mut Value)) -> PathBuf {
    let text = fs::read_to_string(factory_ontology()).unwrap();
    let mut v: Value = serde_json::from_str(&text).unwrap();
    edit(&mut v);
    let p = dir.join(name);
    let body = serde_json::to_string_pretty(&v).unwrap();
    fs::write(&p, format!("{body}\n")).unwrap();
    chmod600(&p);
    p
}

/// 「只加扩展」= **纯加法**：新增一个家族 ＋ 在同一个名下新增一个概念
/// （与 `tools/s1_sys_probe.sh` 的 `ontology-ext.json`、`tests/ontology_ext.rs` 的夹具同形态）。
fn add_pure_extension(v: &mut Value) {
    v["families"]["audit"] = json!({
        "_comment": "纯加法扩展家族：不得影响既有三家族的语义",
        "required": ["scope", "result"],
        "optional": []
    });
    v["_objects"]["audit"] = json!({ "fields": { "result": "enum(pass,fail)" } });
}

/// 出厂法律的"已声明必填格"清单——读模型侧要的那份**纯数据**（`REQ-F-032`）。
///
/// 这里刻意**不**把 `Ontology` 递给读模型（`readmodel` 不许 `use crate::ontology_definition::…`）：
/// 装配处取数据、读模型吃数据，依赖方向留在装配处。
fn declared_cells(ont: &Ontology) -> DeclaredCells {
    DeclaredCells::new(ont.envelope_required(), ont.family_required())
}

/// 落一本基础账（**真账本文件**）：一条 `change` ＋ 一条 `act`，再原样读回两行。
fn base_ledger(dir: &Path) -> Vec<Value> {
    let lp = dir.join("base.jsonl");
    let mut w = World::open(&factory_ontology(), &lp, &factory_policy()).unwrap();
    w.commit(
        "change",
        "world://user",
        event::change_body("world://notice/n-1", "muted", json!(null), json!(true)),
    )
    .unwrap();
    w.commit(
        "act",
        "world://user",
        event::act_body("notice.mute", "do", "r-h01", json!({})),
    )
    .unwrap();
    let lines = w.ledger().read_all().unwrap();
    assert_eq!(lines.len(), 2, "夹具：一条 change ＋ 一条 act");
    assert_eq!(lines[0]["kind"], json!("change"));
    assert_eq!(lines[1]["kind"], json!("act"));
    lines
}

/// 把内存里的账本行写成真文件。
///
/// ⚠️ **去掉 `chain`**：改一个字节而留着摘要，账本会以 `ext.world.Ledger.ChainMismatch` 拒开——
/// 那拒的是"摘要不符"，不是本文件要判的那件事；拿它当红会**判错病因**
/// （与 `tools/s1_sys_probe.sh` 的 `mk_bad` 同口径）。
fn write_ledger(p: &Path, lines: &[Value]) {
    let mut out = lines.to_vec();
    for ev in &mut out {
        if let Some(o) = ev.as_object_mut() {
            o.remove("chain");
        }
    }
    let text = out
        .iter()
        .map(|e| serde_json::to_string(e).unwrap())
        .collect::<Vec<_>>()
        .join("\n");
    fs::write(p, format!("{text}\n")).unwrap();
    chmod600(p);
}

// ══════════ 3.1／3.2 家族演进的三层（新家族怎么加／旧读法读新账本／新读法读旧账本）══════════

/// **h01｜新家族怎么加 ＋ 新读法怎么读旧账本**（`REQ-F-027` 判据②）。
///
/// 「加法」这件事有三个可核面，缺一个，这句话就是口号：
/// ① 本体**确实**换了（内容寻址：hash 必须变，否则"换本体"没发生）；
/// ② 新家族**确实**加上了，且**既有三家族的必填格一格未变**（纯加法）；
/// ③ 同一本**旧账本**在新旧两套读法下折叠结果**逐字节相同**（`REQ-F-027` 判据② 逐字：
///    「新增家族/字段后，**旧账本必须仍可折叠**（旧账本 + 新本体跑 `state`，结果与旧本体一致）」）。
#[test]
fn h01_a_new_family_is_added_by_addition_and_the_new_reader_reads_the_old_ledger() {
    let dir = tmpdir("h01");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let pure = write_ontology(&dir, "pure-ext.json", add_pure_extension);
    let ont_ext = Ontology::load(&pure).unwrap();

    // ① 反同义反复：本体确实换了
    assert_ne!(
        ont.vocab_hash(),
        ont_ext.vocab_hash(),
        "只加家族/概念也会换词表身份——两值相等说明'换本体'根本没发生"
    );

    // ② 新家族真的加上了；既有三家族与信封的必填格一格未动
    assert!(
        ont_ext.known_kinds().contains(&"audit"),
        "新法律必须认得新家族，实得 {:?}",
        ont_ext.known_kinds()
    );
    assert!(!ont.known_kinds().contains(&"audit"), "旧法律里没有它");
    let cells_ext = declared_cells(&ont_ext);
    let cells_old = declared_cells(&ont);
    assert_eq!(
        cells_ext.family_required("audit"),
        Some(&["scope".to_string(), "result".to_string()][..]),
        "新家族的必填格必须来自本体（不是读模型猜的）"
    );
    assert_eq!(
        cells_old.family_required("audit"),
        None,
        "旧法律里没有这个家族"
    );
    for k in ["change", "act", "notice"] {
        assert_eq!(
            cells_ext.family_required(k),
            cells_old.family_required(k),
            "纯加法**不得**改既有家族的必填格（{k}）"
        );
    }
    assert_eq!(cells_ext.envelope_required(), cells_old.envelope_required());

    // ③ 新法律照读旧账本的每一行
    for ev in &lines {
        ont_ext
            .validate(ev)
            .expect("只加扩展的法律必须照读旧账本（判据② 的另一半）");
    }

    // ④ 新旧读法折叠同一本旧账本 ⇒ 逐字节相同
    let before = State::fold_declared(&cells_old, &lines)
        .unwrap()
        .to_json()
        .to_string();
    let after = State::fold_declared(&cells_ext, &lines)
        .unwrap()
        .to_json()
        .to_string();
    assert!(
        !before.is_empty() && before.len() > 2,
        "折叠结果不能是空的（否则『逐字节相同』是同义反复）：{before}"
    );
    assert_eq!(before, after, "新读法读旧账本 ⇒ 折叠结果必须逐字节相同");
}

/// **h02｜旧读法怎么读新账本**（`REQ-F-027` ＋ `REQ-F-029` 的对偶）。
///
/// 账本里出现**读法没有语义的家族**时，两个方向都必须是**拒**，而且**拒得可读**：
/// ① 旧**法律**拒（`ext.world.Ontology.UnknownKind`，点名那个家族）——写入/校验侧；
/// ② 读模型拒（`ext.world.ReadModel.UnknownKind`，同样点名）——折叠侧；
/// ③ 拒它的理由**只能是"家族不认识"**，不许被写成"缺格"（两种情形不许互相冒充）；
/// ④ 反假：把那一行去掉，新旧读法**都照读**（否则"什么都拒"也能让上面全绿）。
#[test]
fn h02_a_reader_refuses_a_ledger_that_uses_a_family_it_does_not_know() {
    let dir = tmpdir("h02");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let pure = write_ontology(&dir, "pure-ext.json", add_pure_extension);
    let ont_ext = Ontology::load(&pure).unwrap();
    let cells_ext = declared_cells(&ont_ext);
    let cells_old = declared_cells(&ont);

    // 新账本 = 旧账本 ＋ 一条**新家族**的行
    let audit = event::new_event(
        3,
        "audit",
        "world://user",
        json!({"scope": "world://notice/n-1", "result": "pass"}),
    );
    let mut new_lines = lines.clone();
    new_lines.push(audit.clone());

    // ① 新法律认得它（证明这条家族真的"加上了"）
    ont_ext
        .validate(&audit)
        .expect("新法律必须认得新家族 audit（否则下面拒的是别的东西）");

    // ② 旧法律拒，并点名
    let e = ont
        .validate(&audit)
        .expect_err("旧法律不得收下它不认识的家族");
    assert!(
        e.to_string().contains("ext.world.Ontology.UnknownKind"),
        "写入侧要有自己的码，实得：{e}"
    );
    assert!(e.to_string().contains("audit"), "错误要点名是哪个家族：{e}");

    // ③ 读模型也拒：**它自己的码**、也点名，且**不许**说成"缺格"
    let f = State::fold_declared(&cells_ext, &new_lines)
        .expect_err("读模型不得收下一个它没有语义的家族（拒绝猜测其语义）");
    assert!(
        f.contains("ext.world.ReadModel.UnknownKind"),
        "折叠侧要有自己的码（与写入侧不混写成一句话），实得：{f}"
    );
    assert!(f.contains("audit"), "读模型同样要点名：{f}");
    assert!(
        !f.contains("MissingCell"),
        "病因不许说错：拒它的理由是**家族不认识**，不是缺格（REQ-F-029 的对偶）：{f}"
    );
    // 旧读法（旧法律清单）同一个方向
    let f2 = State::fold_declared(&cells_old, &new_lines).expect_err("旧读法同样拒");
    assert!(f2.contains("ext.world.ReadModel.UnknownKind") && f2.contains("audit"));

    // ④ 反假：去掉那条新家族的行 ⇒ 新旧读法都照读，且逐字节相同
    let ok_ext = State::fold_declared(&cells_ext, &lines).expect("少了那条新家族行就必须照读");
    let ok_old = State::fold_declared(&cells_old, &lines).expect("同上");
    assert_eq!(ok_ext.seen(), lines.len() as u64, "每一行都折进去了");
    assert_eq!(ok_ext.to_json().to_string(), ok_old.to_json().to_string());
}

/// **h03｜已知家族里"新字段"的两半**：加**可选**格 ⇒ 旧账本照读；加**必填**格 ⇒ 旧账本读不过去。
///
/// 这一条把"演进必须是加法"里最容易被含糊过去的一格钉死：
/// **"加法"不等于"任何加法都无害"**——加一个**可选**格无害（不认识的附加信息忽略），
/// 把某一格改成/加成**必填**则是**破坏性**的（旧账本行读不过去）。
/// 两半都要有断言，否则"加法演进"这句话没有会红的判据。
#[test]
fn h03_a_new_optional_cell_is_ignored_while_a_new_required_cell_is_refused() {
    let dir = tmpdir("h03");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let cells_old = declared_cells(&ont);

    // 新法律甲：给**已知家族** change 加一格**可选**
    let opt_law = write_ontology(&dir, "add-optional.json", |v| {
        v["families"]["change"]["optional"] = json!(["memo"]);
    });
    let ont_opt = Ontology::load(&opt_law).unwrap();
    let cells_opt = declared_cells(&ont_opt);

    // ① 账本里出现那一格 ⇒ 新旧法律**都接受**（"不认识的附加信息忽略"）
    let mut with_memo = lines.clone();
    with_memo[0]["body"]["memo"] = json!("新法律这一版才有的格");
    for ev in &with_memo {
        ont.validate(ev)
            .unwrap_or_else(|e| panic!("旧法律必须接受带附加格的旧家族行：{e}"));
        ont_opt
            .validate(ev)
            .unwrap_or_else(|e| panic!("新法律必须接受它声明的可选格：{e}"));
    }

    // ② 折叠结果**逐字节相同**：多出来的那一格**不得**进入状态
    let base = State::fold_declared(&cells_old, &lines)
        .unwrap()
        .to_json()
        .to_string();
    let memo_old = State::fold_declared(&cells_old, &with_memo)
        .unwrap()
        .to_json()
        .to_string();
    let memo_new = State::fold_declared(&cells_opt, &with_memo)
        .unwrap()
        .to_json()
        .to_string();
    assert!(!base.is_empty() && base.len() > 2, "折叠结果不能是空的");
    assert_eq!(base, memo_old, "附加格不得进入状态（旧读法）");
    assert_eq!(base, memo_new, "附加格不得进入状态（新读法）");
    // 反假：那一格**确实**在账本行里（否则上面比的是两条一模一样的行）
    assert_eq!(with_memo[0]["body"]["memo"], json!("新法律这一版才有的格"));

    // ③ 负控：把 memo 加成**必填** ⇒ 旧账本行必须读不过去，且点名缺的那一格
    let req_law = write_ontology(&dir, "add-required.json", |v| {
        v["families"]["change"]["required"]
            .as_array_mut()
            .unwrap()
            .push(json!("memo"));
    });
    let ont_req = Ontology::load(&req_law).unwrap();
    let e = ont_req
        .validate(&lines[0])
        .expect_err("加了必填格之后，旧账本行必须读不过去（否则本判据恒绿）");
    assert!(
        e.to_string().contains("ext.world.Ontology.MissingField"),
        "写入侧的理由要可判定，实得：{e}"
    );
    assert!(e.to_string().contains("memo"), "要点名缺的那一格：{e}");

    // ④ 同一条负控在**读模型侧**：带法律折叠也必须拒，并点名那一格与那一层
    let cells_req = declared_cells(&ont_req);
    let f = State::fold_declared(&cells_req, &lines).expect_err("读模型侧同样必须拒");
    assert!(
        f.contains("ext.world.ReadModel.MissingCell"),
        "折叠侧的码要可判定，实得：{f}"
    );
    assert!(
        f.contains("memo") && f.contains("body[change]"),
        "要点名缺的那一格与它所在的层：{f}"
    );

    // ⑤ 正控：把那一格补上 ⇒ 又能读（证明④不是恒红）
    let mut fixed = lines.clone();
    fixed[0]["body"]["memo"] = json!("补上");
    State::fold_declared(&cells_req, &fixed).expect("补上那一格就必须能读");
}

// ══════════════════════ 9.2 读模型侧的缺格（缺格即报错）══════════════════════

/// **h04｜缺格即报错**（`REQ-F-032` 判据②）：已声明的必填格读不到 ⇒ 拒，并**点名那一格**。
///
/// 五件事各自可判：
/// ① 缺信封必填格（`actor`——正是 `TC-047` ⑨ 登记的那一格）⇒ 拒 ＋ 点名 ＋ 说出"该层该有哪些格"＋ 点到哪一行；
/// ② 反假：补回那一格 ⇒ 能读，且与基线**逐字节相同**（不是"什么都拒"）；
/// ③ 家族信纸的缺格同判（`act` 的信纸今天**完全没人读**：`State::apply` 里只 `acts += 1`）；
/// ④ **对偶**：不认识的家族**不**在这里报（它的判据是 `ReadModel.UnknownKind`，两处不许互相冒充）；
/// ⑤ 可选格**不是**缺格：整行没有 `to`／`trace`／`params`／`payload` 照样能读。
#[test]
fn h04_a_missing_declared_cell_is_refused_with_that_cell_named() {
    let dir = tmpdir("h04");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let cells = declared_cells(&ont);
    let base = State::fold_declared(&cells, &lines)
        .expect("原账本必须能读")
        .to_json()
        .to_string();

    // ① 手写一条缺必填信封字段 `actor` 的账本行
    let mut missing_actor = lines.clone();
    missing_actor[0].as_object_mut().unwrap().remove("actor");
    let e = State::fold_declared(&cells, &missing_actor).expect_err("缺格必须拒（不得静默通过）");
    assert!(
        e.contains("ext.world.ReadModel.MissingCell"),
        "错误码要可判定，实得：{e}"
    );
    assert!(e.contains("`actor`"), "必须**点名**缺的那一格，实得：{e}");
    assert!(e.contains("envelope"), "要点名缺在哪一层，实得：{e}");
    assert!(
        e.contains("kind") && e.contains("body") && e.contains("flags"),
        "要列出该层已声明的必填格（否则只说了不行、没说怎么办），实得：{e}"
    );
    assert!(e.contains("seq=1"), "要点到**哪一行**，实得：{e}");

    // ② 反假：补回 actor ⇒ 能读，且与基线逐字节相同
    let back = State::fold_declared(&cells, &lines).expect("补回 actor 后必须能读");
    assert_eq!(
        back.to_json().to_string(),
        base,
        "补回那一格后结论必须与基线逐字节相同"
    );

    // ③ 家族信纸的缺格同判（act 的 request_id）
    let mut missing_rid = lines.clone();
    missing_rid[1]["body"]
        .as_object_mut()
        .unwrap()
        .remove("request_id");
    let e2 = State::fold_declared(&cells, &missing_rid).expect_err("act 缺 request_id 同样必须拒");
    assert!(e2.contains("ext.world.ReadModel.MissingCell"), "实得：{e2}");
    assert!(e2.contains("`request_id`"), "要点名那一格：{e2}");
    assert!(e2.contains("body[act]"), "要点名缺在哪一层：{e2}");

    // ④ 对偶：不认识的家族不在这里报（病因不许说错）
    let mut bogus = lines.clone();
    bogus[0]["kind"] = json!("bogus");
    let e3 = State::fold_declared(&cells, &bogus).expect_err("未知家族必须拒");
    assert!(
        e3.contains("ext.world.ReadModel.UnknownKind") && e3.contains("bogus"),
        "未知家族走它自己那条判据，实得：{e3}"
    );
    assert!(
        !e3.contains("MissingCell"),
        "『家族不认识』不许被写成『缺格』（REQ-F-029 的对偶）：{e3}"
    );

    // ⑤ 可选格不是缺格
    for ev in &lines {
        assert!(ev.get("to").is_none(), "夹具不应带 to");
        assert!(ev.get("trace").is_none(), "夹具不应带 trace");
    }
    assert_eq!(
        State::fold_declared(&cells, &lines).unwrap().seen(),
        lines.len() as u64
    );
}

/// **h05｜命令这一级也拒**（`REQ-F-032` 判据② 的端到端形态）。
///
/// 三件事一起断言：
/// ① `state --json`（CLI；`World::read_model` → `State::fold_declared`）对"缺已声明必填格
///    信封字段 `actor`"的账本行**拒**，`rc=2`，且错误里**点名**那一格；
/// ② 反假：把 `actor` 补回去 ⇒ `rc=0`（不是"什么都拒"）；
/// ③ 库侧同一条口径（`World::read_model` 直接调用）也拒。
///
/// ## 这条用例的前身是一条**登记项**，它已经兑现，故按登记时写下的处置改写
///
/// 2026-09-28 上午它断言的是"CLI 读路径仍是无法律折叠 ⇒ 缺格被静默接受（`rc=0`）"，
/// 并写明"谁把 `World::read_model` 接到带法律的折叠上，本条先红"。同日装配处接上了
/// （`src/lib.rs::read_model` ⇒ `State::fold_declared` ＋ `Ontology::{envelope_required,family_required}`）
/// ⇒ 该断言**如期变红**，于是按登记时的处置改成**端到端断言**——
/// 登记项不是用来长期挂着的：合上它的那次改动会打红它，就是它存在的全部意义。
///
/// 系统级同一条：`tools/s1_sys_probe.sh` 的 `TC-047` ⑨（它此前正是把这一格登记成
/// 「缺必填信封字段 `actor` 竟**被接受**（rc=$R）：必填字段校验只在写入路径（本体校验）上，
/// 折叠层不校验」）。
#[test]
fn h05_the_cli_read_path_refuses_a_missing_declared_cell_end_to_end() {
    let dir = tmpdir("h05");
    let lines = base_ledger(&dir);
    let good = dir.join("good.jsonl");
    write_ledger(&good, &lines);
    let mut missing_actor = lines.clone();
    missing_actor[0].as_object_mut().unwrap().remove("actor");
    let lp = dir.join("missing-actor.jsonl");
    write_ledger(&lp, &missing_actor);

    let bin = env!("CARGO_BIN_EXE_world-core");
    let state_json = |ledger: &Path| {
        Command::new(bin)
            .args([
                "--ontology",
                &factory_ontology().display().to_string(),
                "--policy",
                &factory_policy().display().to_string(),
                "--ledger",
                &ledger.display().to_string(),
                "state",
                "--json",
            ])
            .output()
            .expect("无法启动被测二进制")
    };

    // ① 缺格 ⇒ 命令这一级拒，rc=2，且点名那一格
    let out = state_json(&lp);
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert_eq!(
        out.status.code(),
        Some(2),
        "缺已声明必填格的账本行，`state` 必须拒（rc=2）；stderr={stderr}"
    );
    assert!(
        stderr.contains("ext.world.ReadModel.MissingCell"),
        "拒绝理由要带读模型侧的缺格码，实得：{stderr}"
    );
    assert!(
        stderr.contains("actor"),
        "拒绝理由必须**点名**缺的那一格，实得：{stderr}"
    );

    // ② 反假：补回那一格 ⇒ rc=0（证明 ① 不是"什么都拒"）
    let back = state_json(&good);
    let back_out = String::from_utf8_lossy(&back.stdout);
    assert_eq!(
        back.status.code(),
        Some(0),
        "补回 actor 后必须能读；stderr={}",
        String::from_utf8_lossy(&back.stderr)
    );
    assert!(
        back_out.contains("\"last_seq\":2"),
        "两条都要折进去，实得：{back_out}"
    );

    // ③ 库侧同一条口径
    let w = World::open_readonly(&factory_ontology(), &lp, &factory_policy()).unwrap();
    let e = w
        .read_model()
        .expect_err("World::read_model 必须拒（它就是 CLI 那条路）");
    assert!(
        e.contains("ext.world.ReadModel.MissingCell") && e.contains("actor"),
        "库侧的拒绝理由同样要点名那一格，实得：{e}"
    );
}

/// **h06｜空表不许被读成宽松**：没有"已声明格清单"时，缺格判据无从成立 ⇒ 拒绝折叠。
///
/// 为什么不默默放行：**"一个格都没查"与"每个格都查过了"在读数上一样、在结论上相反**——
/// 那正是本项目最贵的一类错。与门禁那条「空策略拒绝启动」同一纪律。
#[test]
fn h06_an_empty_declared_cell_list_is_not_read_as_lenient() {
    let dir = tmpdir("h06");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();

    let empty = DeclaredCells::default();
    assert!(empty.is_empty());
    let mut st = State::new();
    let e = st
        .apply_declared(&empty, &lines[0])
        .expect_err("空表不许被读成宽松");
    assert!(
        e.contains("ext.world.ReadModel.NoDeclaredCells"),
        "空表的拒绝理由要可判定，实得：{e}"
    );

    // 正控：真法律的清单不是空的，且同一批行必须能读（否则上面那条恒绿）
    let cells = declared_cells(&ont);
    assert!(
        !cells.is_empty(),
        "出厂本体声明了 8 ＋ 4／3／2 格，清单不许为空"
    );
    assert_eq!(
        State::fold_declared(&cells, &lines).unwrap().seen(),
        lines.len() as u64
    );
}

/// **h07｜逐格可枚举**（`REQ-F-032` 判据①）：已声明清单能机械枚举，且与出厂本体**原文逐字一致**。
///
/// 这一条独立读文件、独立比对（不与 `Ontology::load` 共用那一次解析），
/// 于是"清单从哪来"这件事有两个独立来源对得上；顺带把**出厂本体的身份**钉住
/// （它的 `fnv1a64:6a96abfa9a969462` 被多份文档写死 ⇒ 就地从改它＝契约变更，须人批）。
#[test]
fn h07_the_declared_inventory_is_mechanically_enumerable() {
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let raw: Value =
        serde_json::from_str(&fs::read_to_string(factory_ontology()).unwrap()).unwrap();

    let strs = |v: &Value| -> Vec<String> {
        v.as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_str().unwrap().to_string())
            .collect()
    };

    // ① 信封：必填 8 项、可选 2 项，逐字与原文一致
    let raw_req = strs(&raw["envelope"]["required"]);
    let raw_opt = strs(&raw["envelope"]["optional"]);
    assert_eq!(
        ont.envelope_required(),
        raw_req,
        "信封必填格必须与本体原文逐字一致"
    );
    assert_eq!(ont.optional(), raw_opt.as_slice());
    assert_eq!(ont.envelope_required().len(), 8, "出厂本体：信封必填 8 项");
    assert_eq!(
        ont.optional().len(),
        2,
        "出厂本体：信封可选 2 项（to／trace）"
    );

    // ② 三家族：必填格逐字一致；**可选格不在清单里**（可选 ≠ 缺格）
    let fams = ont.family_required();
    for (k, def) in raw["families"].as_object().unwrap() {
        if k.starts_with('_') {
            continue;
        }
        let want = strs(&def["required"]);
        assert_eq!(
            fams.get(k.as_str()).map(Vec::as_slice),
            Some(want.as_slice()),
            "家族 {k} 的必填格必须与原文逐字一致"
        );
        for f in &want {
            assert!(
                !strs(&def["optional"]).contains(f),
                "家族 {k} 的 `{f}` 同时出现在 required 与 optional 里（本体自相矛盾）"
            );
        }
    }
    let mut got: Vec<(String, usize)> = fams.iter().map(|(k, v)| (k.clone(), v.len())).collect();
    got.sort();
    assert_eq!(
        got,
        vec![
            ("act".to_string(), 3),
            ("change".to_string(), 4),
            ("notice".to_string(), 2)
        ],
        "出厂本体：三家族必填格 3／4／2"
    );

    // ③ 对象（世界里的类型与字段）同样可枚举
    // ★ **有意更新的断言**（与上面那句身份字面量同族，**不是放宽**）：本批给本体加了
    //   **统一类型** `presence`（在场者：`name`／`category`／`state`／`did`／`last_seen`）
    //   ⇒ 声明清单**确实变宽了**；判据一字未改，仍是"清单能机械枚举、且与出厂本体原文逐字一致"。
    // ★ **同族，再一次**：本批又加了 `surface`（面）／`cell`（格）／`port`（口）三类……
    //   ⇒ 清单**又**变宽了（`right` 一侧跟着走），**判据仍一字未改**。
    //   ⚠ 如实登记：本条与上面那条一样，**只钉"清单能机械枚举"**；它**不证明**新类型
    //   有任何执行体（`world://surface|cell|port` 在 `src/**/*.rs` 里 0 命中，
    //   见 `评审-切面-渲染协议-2026-10-05.md`）—— **"声明了"与"在用"是两件事。**
    assert_eq!(
        ont.known_entities(),
        vec!["cell", "job", "notice", "port", "presence", "surface"]
    );
    // ★ **有意更新的断言**（与上面那句身份字面量同族，**不是放宽**）：
    //   `notice` 的**声明清单**多了 `retract_seq: integer` —— **"清单条目数"是与"身份"并列的
    //   另一种「派生量」**：改本体（法律面）会同时挪动两者，**每一种都在自己的地方被钉着**。
    //   ⇒ 这里跟着新清单走（清单确实变宽了，判据仍是"清单能机械枚举、且与出厂本体原文逐字一致"）。
    assert_eq!(
        ont.declared_fields("notice"),
        Some(&BTreeMap::from([
            ("muted".to_string(), "bool".to_string()),
            ("retract_seq".to_string(), "integer".to_string())
        ])),
        "书 §5.3 逐字『世界的边界由声明定』：世界里有什么，由对象节定"
    );
    // ★ **同族，再一次**：`job` 的声明清单多了「**当前这一步**」那一族
    //   （`step`／`steps_total`／`step_label`）＋ `retract_seq`
    //   —— 依据：那一格**已经被重复使用**（`case.step` 借 `notice.payload` 用过 7 次），
    //   按书·总则第八节「本体**只应收下已被重复使用的东西**」⇒ **该收**。
    //   而它**必须有一个已声明的载体**才读得出来（`notice.payload` 只计数不折叠，读不出来）。
    //   ⇒ 清单变宽，**判据仍一字未改**。
    assert_eq!(
        ont.declared_fields("job"),
        Some(&BTreeMap::from([
            ("status".to_string(), "enum(todo,doing,done)".to_string()),
            ("step".to_string(), "integer".to_string()),
            ("steps_total".to_string(), "integer".to_string()),
            ("step_label".to_string(), "string".to_string()),
            ("retract_seq".to_string(), "integer".to_string())
        ]))
    );
    assert_eq!(
        ont.declared_fields("presence"),
        Some(&BTreeMap::from([
            ("name".to_string(), "string".to_string()),
            ("category".to_string(), "string".to_string()),
            (
                "state".to_string(),
                "enum(installed,registered,running,stopped,retired)".to_string()
            ),
            ("did".to_string(), "array(string)".to_string()),
            ("last_seen".to_string(), "integer  # UNIX 秒".to_string())
        ])),
        "在场者（本批新增的统一类型）也必须能从本体原文逐格枚举"
    );

    // ④ 出厂本体的**身份**（改本体＝改法律＝契约变更，须人批）
    assert_eq!(
        ont.vocab_hash(),
        "fnv1a64:6a96abfa9a969462",
        "出厂本体的词表身份被多份文档写死；就地改它必须走契约变更"
    );
}

/// **h08｜读法覆盖核对**（`TC-077` ／ `REQ-F-032`）——**逐字段**两条 ＋ **反假**一条。
///
/// ① **法律声明的必填格 ⊆ 读法覆盖表**（**结构不变式 ＋ 装配那根线**）。
///    ⚠ **它的射程到此为止**：覆盖表是**从本体派生**的（`declared_cells` 走 `DeclaredCells::new(ont.envelope_required(), …)`，
///    而 `new` 恒等传递）⇒ ①**只在"装配那根线被改坏"时会红**（实测：把 `new` 改成过滤掉 `actor` ⇒ ① 立刻红）；
///    **它证明不了**「那一格**读得出来**」——那是 `REQ-F-032` 的**另一半**（读模型的**渲染面**），**仍未落**，
///    见后继件 `1.1` 与 `WC-RTM-001.csv` 的 `REQ-F-032` 行。**不许把 ① 读成"每格都有人读得到"。**
///    **（2026-09-28 订正，承独立评审席：本条初版的注释与断言消息写成"那一格没人读（`REQ-F-032` 的缺口）"，把构造不变式说成了判据——已按实收窄。）**
/// ② **缺格即报错**：把每一格**逐个**从账本行里拿掉 ⇒ 必须**被拒**、且**点名那一格**（逐字段，不是挑一个代表）。
/// ③ **反假**（这条是"判据必须会红"的正向证据）：把覆盖表里的某一格**去掉** ⇒
///    那一格缺失的行**就不再被拒** ⇒ 证明**覆盖表是承重的**；否则上面两条可能只是"什么都拒"的假绿。
///
/// 为什么单列一条而不是并进 `h04`：`h04` 钉的是"缺格被拒"的**机制**（含对偶与可选格的边界）；
/// 本条钉的是**覆盖面**——法律声明的**每一格**都在覆盖里、且覆盖表**不能少一格**。
#[test]
fn h08_every_declared_envelope_field_is_covered_and_the_coverage_is_load_bearing() {
    let dir = tmpdir("h08");
    let lines = base_ledger(&dir);
    let ont = Ontology::load(&factory_ontology()).unwrap();
    let cells = declared_cells(&ont);
    let declared = ont.envelope_required();

    assert!(
        !declared.is_empty(),
        "法律声明的必填格为空 ⇒ 本用例无从判（不许把'没得查'读成'通过'）"
    );

    // ① 逐字段：法律声明的每一格，读法覆盖里都有它
    for f in &declared {
        assert!(
            cells.envelope_required().iter().any(|c| c == f),
            "法律声明了 `{f}`，而读法覆盖表（DeclaredCells）里没有它 ⇒ **装配那根线断了**（**本断言只钉结构不变式**：覆盖表由本体派生；它**不证明**那一格读得出来——那见 `1.1`）"
        );
    }

    // ② 逐字段：每一格缺了都必须被拒、且点名它
    for f in &declared {
        let mut bad = lines.clone();
        bad[0].as_object_mut().unwrap().remove(f);
        match State::fold_declared(&cells, &bad) {
            Err(e) => assert!(
                e.contains(&format!("`{f}`")),
                "缺 `{f}` 被拒了，但报错**没有点名那一格**，实得：{e}"
            ),
            Ok(_) => panic!("缺 `{f}` 的账本行**静默通过**了 —— 缺格即报错这条没兜住"),
        }
    }

    // ③ 反假：把覆盖表里的某一格去掉 ⇒ 那一格的缺格**不再被拒** ⇒ 覆盖表承重
    let victim = declared
        .iter()
        .find(|f| f.as_str() == "actor")
        .cloned()
        .unwrap_or_else(|| declared[0].clone());
    let reduced: Vec<String> = declared.iter().filter(|f| **f != victim).cloned().collect();
    let cells_reduced = DeclaredCells::new(reduced, ont.family_required());
    let mut bad = lines.clone();
    bad[0].as_object_mut().unwrap().remove(&victim);
    assert!(
        State::fold_declared(&cells_reduced, &bad).is_ok(),
        "覆盖表里已经**去掉**了 `{victim}`，而缺它的行**仍被拒** ⇒ 这条反假证明不了'覆盖表承重'（判据可能是别的东西在拦）"
    );
    // 同一条行、**完整**覆盖表 ⇒ 必须被拒（与上面构成对照：差别只在覆盖表）
    assert!(
        State::fold_declared(&cells, &bad).is_err(),
        "同一条行在**完整**覆盖表下必须被拒（否则①②的对照不成立）"
    );
}

// ══════════════════════════════════════════════════════════════════════════
// 3.3 ★ **撤回**（过户不落账）—— `r01`–`r06`
//
// ★ 一句话口径：**撤回＝过户不落账；序号是账本的，效果才是撤回的对象。**
//
// ## 撤回事实长什么样（不新增事件家族、不动法律、不动 `to_json`）
//
// 它就是一条**普通的 `change`**：`body.path = retract_seq`（出厂本体在 `notice.fields` 里
// 逐字声明过这一格）、`body.after` ＝ **被撤回的那条账本序号**、信封 `actor` ＝ 谁撤的、
// 信封 `trace` ＝ 因为什么（本体对 `trace` 的逐字定义是「因果：引发本条的那条事件的 id」）。
//
// ## 语料分两种（**两条都是踩出来的教训**）
//
// - **"能读、只是折叠不了"**（`r01`–`r04`）：先一条正常 `change`，再一条**谎称旧值**的 `change`。
//   ★ **第 13 轮起，第二条再也进不来**：写入侧新增旧值核对
//   （`ext.world.World.BeforeMismatch`，`src/lib.rs::World::check_before`）⇒ 走唯一写入口会被当场拒。
//   故夹具改为**手造一行并补上正确的摘要链**（`append_raw_with_chain`）——它模拟的正是
//   「账本被写入侧之外的东西改过」这一种形态，也就是读侧那道墙**今天唯一的对手**。
//   ⚠️ **不许**图省事写一行不带 `chain` 的裸 JSON：那会让账本变成"部分有链、部分没有"，
//   `open` 先以 `ext.world.Ledger.MixedChain` 拒开 ⇒ "折叠不了"这个病因**根本没被量到**，
//   判据就成了装饰（`tests/ontology_elements.rs::m20` 上一版就是这么倒的）。
// - **全部可折叠**（`r05`／`r06`）：一条**真发生过**的改动（`false→true`）被撤回
//   ⇒ 世界现在的值是 `false`，而"撤回前"的值是 `true` ⇒ 判据锋利。
// ══════════════════════════════════════════════════════════════════════════

/// 跑一次 `world-core`（被测二进制），返回 `(rc, stdout, stderr)`。
fn run_wc(args: &[String]) -> (i32, String, String) {
    let bin = env!("CARGO_BIN_EXE_world-core");
    let out = Command::new(bin)
        .args(args)
        .output()
        .expect("跑得起来 world-core");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).to_string(),
        String::from_utf8_lossy(&out.stderr).to_string(),
    )
}

/// 夹具的公共参数：`--ontology … --policy … --ledger …`。
fn base_args(ledger: &Path) -> Vec<String> {
    vec![
        "--ontology".into(),
        factory_ontology().display().to_string(),
        "--policy".into(),
        factory_policy().display().to_string(),
        "--ledger".into(),
        ledger.display().to_string(),
    ]
}

/// `world-core append <kind> <body> [actor] [--trace <id>]`：**走唯一写入口**落一条事件。
///
/// 返回落笔的那条事件（`append` 的 stdout 就是它）。
fn cli_append(ledger: &Path, kind: &str, body: Value, actor: &str, trace: Option<&str>) -> Value {
    let mut a = base_args(ledger);
    a.push("append".into());
    a.push(kind.into());
    a.push(serde_json::to_string(&body).unwrap());
    a.push(actor.into());
    if let Some(t) = trace {
        a.push("--trace".into());
        a.push(t.into());
    }
    let (rc, out, err) = run_wc(&a);
    assert_eq!(rc, 0, "夹具：`append {kind}` 必须成功；stderr={err}");
    serde_json::from_str(out.trim())
        .unwrap_or_else(|e| panic!("`append` 的 stdout 必须是那条事件的 JSON：{e}\n{out}"))
}

/// `world-core state [--json] [--retracted]`。
fn cli_state(ledger: &Path, extra: &[&str]) -> (i32, String, String) {
    let mut a = base_args(ledger);
    a.push("state".into());
    for x in extra {
        a.push((*x).into());
    }
    run_wc(&a)
}

/// 一条 `change` 的信纸（`muted` 那格；夹具里反复用）。
fn muted(before: Value, after: Value) -> Value {
    event::change_body("world://notice/n-1", "muted", before, after)
}

/// 一条**撤回事实**的信纸：`path = retract_seq`、`after = 被撤回的 seq`。
fn retract_body(target: u64) -> Value {
    event::change_body(
        "world://notice/n-1",
        RETRACT_PATH,
        json!(null),
        json!(target),
    )
}

/// 从账本文件里读回全部事件（**与 CLI 同一条路**：`World::open_readonly` → `read_all`）。
fn read_back(ledger: &Path) -> Vec<Value> {
    let w = World::open_readonly(&factory_ontology(), ledger, &factory_policy()).unwrap();
    w.ledger().read_all().unwrap()
}

/// 往账本**末尾**追加一条**手造**的原始行，并给它算一条**正确的摘要链**。
///
/// 摘要算法取自 [`world_core::ledger::event_chain`]（**与写入侧同源**，不是抄一份）。
/// 为什么必须算链：手写一行而不补链 ⇒ 账本"部分有链、部分没有" ⇒ `open` 先以
/// `ext.world.Ledger.MixedChain` 拒开 ⇒ **判错了病因**（本文件的 `write_ledger` 干脆全行去链，
/// 那是"整本无链"的合法形态；此处既有的行**有**链，故必须补）。
fn append_raw_with_chain(lp: &Path, mut ev: Value) {
    let prev = fs::read_to_string(lp)
        .ok()
        .and_then(|t| t.lines().last().map(str::to_string))
        .and_then(|l| serde_json::from_str::<Value>(&l).ok())
        .and_then(|v| v.get("chain").and_then(Value::as_str).map(str::to_string))
        .unwrap_or_else(|| world_core::ledger::CHAIN_GENESIS.to_string());
    let chain = world_core::ledger::event_chain(&prev, &ev).unwrap();
    ev.as_object_mut()
        .unwrap()
        .insert("chain".into(), json!(chain));
    let mut text = fs::read_to_string(lp).unwrap();
    if !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(&serde_json::to_string(&ev).unwrap());
    text.push('\n');
    fs::write(lp, text).unwrap();
}

/// **手造一条"谎称旧值"的 `change`**（★**第 13 轮起不再走唯一写入口**：写入侧会当场拒它）。
///
/// 为什么这个夹具必须存在：读侧那道墙（`ext.world.ReadModel.BeforeMismatch`）的对手，
/// 今天**只剩**"账本被写入侧之外的东西改过"这一种形态（真实账本 `seq=13` 就是当年那一格：
/// 事件称 `before=null`，而折叠出的当前值是 `false`）。
/// 手造就必须**补上正确的摘要链**（否则先以 `MixedChain` 拒开 ⇒ 判错病因）。
fn append_lying_before(lp: &Path, seq: u64, id: &str) -> String {
    let mut bad = event::new_event(
        seq,
        "change",
        "world://core",
        muted(json!(true), json!(true)), // 谎称旧值是 true（真旧值是 false）
    );
    bad.as_object_mut().unwrap().insert("id".into(), json!(id));
    append_raw_with_chain(lp, bad);
    id.to_string()
}

/// **"能读、只是折叠不了"那一格**：一条正常 `change` ＋ 一条**谎称旧值**的 `change`。
///
/// ★ 第一条走唯一写入口（带链）；第二条**手造 ＋ 补链**——理由见上。
///
/// 返回 `(账本路径, 坏行的 id)`。
fn ledger_with_a_lying_before(dir: &Path) -> (PathBuf, String) {
    let lp = dir.join("bad.jsonl");
    cli_append(
        &lp,
        "change",
        muted(json!(null), json!(false)),
        "world://core",
        None,
    );
    let id = append_lying_before(&lp, 2, "e-lying-before-2");
    (lp, id)
}

/// **r01｜追加一条撤回指向坏 `seq` ⇒ 重新折叠成功**。
///
/// ★ **反例**：把 `before` 校验改成"容错跳过"也能折叠 ⇒ 本用例 ① 当场红
/// （**绝不用松校验换"能折叠"**：那两条在结论上是相反的——一条是"这条不算数"，
/// 另一条是"这条算数，只是我不查了"）。
#[test]
fn r01_a_retraction_of_the_bad_seq_makes_the_ledger_foldable_again() {
    let dir = tmpdir("r01");
    let (lp, bad_id) = ledger_with_a_lying_before(&dir);

    // ① 撤回**之前**：拒折叠，且**病因必须是 `BeforeMismatch`**（不是摘要、不是缺格）
    let (rc0, _o0, e0) = cli_state(&lp, &["--json"]);
    assert_eq!(rc0, 2, "坏账本必须拒折叠（rc=2）；stderr={e0}");
    assert!(
        e0.contains("ext.world.ReadModel.BeforeMismatch"),
        "拒绝的**病因**必须是「旧值不符」，实得：{e0}"
    );

    // ② 追加一条**撤回事实**指向那条坏 `seq`（走唯一写入口；账本里的旧行**一个字节都没动**）
    cli_append(
        &lp,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id),
    );

    // ③ 撤回**之后**：同一本账本**折得开**了，且值是"**从来没变过**"的那个 `false`
    let (rc1, o1, e1) = cli_state(&lp, &["--json"]);
    assert_eq!(
        rc1, 0,
        "撤回之后必须折得开（rc=0）；stderr={e1}\nstdout={o1}"
    );
    let v: Value = serde_json::from_str(o1.trim()).expect("`state --json` 必须是 JSON");
    assert_eq!(
        v["objects"]["world://notice/n-1"]["muted"],
        json!(false),
        "撤回撤的是那条的**效果** ⇒ 当前值回到 `seq=1` 之后的 `false`：{o1}"
    );
    assert_eq!(
        v["last_seq"],
        json!(3),
        "**序号是账本的**：撤回让 `last_seq` 推到 3（被撤回的那条**没有被跳过**）：{o1}"
    );
    assert_eq!(
        v["seen"],
        json!(1),
        "**效果才是撤回的对象**：3 条里只有 1 条的效果落了账：{o1}"
    );

    // ④ 反假：撤回**不许**截断账本
    assert_eq!(
        fs::read_to_string(&lp).unwrap().lines().count(),
        3,
        "撤回**不许**截断账本（禁的那条作弊路）"
    );
}

/// **r02｜坏 `seq` 仍可见，并带「已撤回」标记**。
///
/// ★ **反例**：它从账本消失 ⇒ 红（**那是删除，不是撤回**）。
#[test]
fn r02_the_retracted_seq_stays_in_the_ledger_and_carries_a_retracted_mark() {
    let dir = tmpdir("r02");
    let (lp, bad_id) = ledger_with_a_lying_before(&dir);
    cli_append(
        &lp,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id),
    );

    // ① **账本里那条一个字节都没少**：`seq=2` 与它的 `id` 都还在
    let raw = fs::read_to_string(&lp).unwrap();
    assert!(
        raw.contains("\"seq\":2"),
        "被撤回的那条必须仍在账本里（撤回不是删除）：\n{raw}"
    );
    assert!(
        raw.contains(&bad_id),
        "**同一条**（按 `id`）必须还在账本里：\n{raw}"
    );
    assert_eq!(raw.lines().count(), 3, "账本只许追加：\n{raw}");

    // ② 事件面（`read`）也不隐藏它——"可见"不是靠新读法挑着给
    let mut a = base_args(&lp);
    a.push("read".into());
    a.push("2".into());
    let (rc_r, out_r, err_r) = run_wc(&a);
    assert_eq!(rc_r, 0, "`read` 必须成功；stderr={err_r}");
    assert!(
        out_r.contains(&bad_id) && out_r.contains("\"seq\":2"),
        "`read` 必须照样打印被撤回的那条：\n{out_r}"
    );

    // ③ **撤回标记**：`state --retracted` 点名它（序号 ＋ 撤的人 ＋ 因为什么）
    let (rc_s, out_s, err_s) = cli_state(&lp, &["--retracted"]);
    assert_eq!(rc_s, 0, "`state --retracted` 必须成功；stderr={err_s}");
    assert!(
        out_s.contains("已撤回") && out_s.contains("seq=2"),
        "`state --retracted` 必须点名「seq=2 已撤回」：\n{out_s}"
    );
    assert!(
        out_s.contains("world://core") && out_s.contains(&bad_id),
        "标记里必须带得出**谁撤的**与**因为什么**：\n{out_s}"
    );
}

/// **r03｜撤回不存在的 `seq` ／ 撤回已撤回的 ⇒ 红**（＋本层另立的两条边界）。
///
/// ★ **反例**：把这三条检查短路 ⇒ 这里三条错码全不见 ⇒ 红。
#[test]
fn r03_retracting_a_missing_or_already_retracted_seq_is_refused_by_name() {
    // ① 撤回一条账本里**没有**的 `seq`
    let d1 = tmpdir("r03a");
    let lp1 = d1.join("l.jsonl");
    cli_append(
        &lp1,
        "change",
        muted(json!(null), json!(false)),
        "world://core",
        None,
    );
    cli_append(&lp1, "change", retract_body(99), "world://core", None);
    let (rc1, _o1, e1) = cli_state(&lp1, &["--json"]);
    assert_eq!(rc1, 2, "撤回不存在的 seq 必须拒（rc=2）；stderr={e1}");
    assert!(
        e1.contains("ext.world.ReadModel.RetractTargetUnknown"),
        "必须点名 `RetractTargetUnknown`，实得：{e1}"
    );

    // ② 撤回**已撤回**的（同一条 `seq` 撤两次）
    let d2 = tmpdir("r03b");
    let (lp2, bad_id) = ledger_with_a_lying_before(&d2);
    cli_append(
        &lp2,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id),
    );
    cli_append(&lp2, "change", retract_body(2), "world://core", None);
    let (rc2, _o2, e2) = cli_state(&lp2, &["--json"]);
    assert_eq!(rc2, 2, "撤回已撤回的必须拒（rc=2）；stderr={e2}");
    assert!(
        e2.contains("ext.world.ReadModel.RetractAlreadyRetracted"),
        "必须点名 `RetractAlreadyRetracted`，实得：{e2}"
    );

    // ③（本层另立的边界）撤回的是一条**撤回事实**本身
    let d3 = tmpdir("r03c");
    let (lp3, bad_id3) = ledger_with_a_lying_before(&d3);
    cli_append(
        &lp3,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id3),
    );
    cli_append(&lp3, "change", retract_body(3), "world://core", None); // seq=3 是那条撤回事实
    let (rc3, _o3, e3) = cli_state(&lp3, &["--json"]);
    assert_eq!(rc3, 2, "撤回一条**撤回事实**必须拒（rc=2）；stderr={e3}");
    assert!(
        e3.contains("ext.world.ReadModel.RetractTargetNotAnEffect"),
        "必须点名 `RetractTargetNotAnEffect`，实得：{e3}"
    );

    // ④（本层另立的边界）`after` 不是正整数 ⇒ `RetractMalformed`，**不许**降级成"当它不是撤回事实"。
    //    这一格写入侧会按本体声明的 `integer` 拦住（`after=null` ⇒ `BadFieldValueType`）
    //    ⇒ 只能**手造**那一行；手造就必须**补上正确的摘要链**（否则先以 `MixedChain` 拒开 ⇒ 判错病因）。
    let d4 = tmpdir("r03d");
    let lp4 = d4.join("l.jsonl");
    cli_append(
        &lp4,
        "change",
        muted(json!(null), json!(false)),
        "world://core",
        None,
    );
    let mut malformed = event::new_event(
        2,
        "change",
        "world://core",
        event::change_body("world://notice/n-1", RETRACT_PATH, json!(null), Value::Null),
    );
    malformed
        .as_object_mut()
        .unwrap()
        .insert("id".into(), json!("e-malformed-2"));
    append_raw_with_chain(&lp4, malformed);
    let (rc4, _o4, e4) = cli_state(&lp4, &["--json"]);
    assert_eq!(rc4, 2, "形状坏的撤回必须拒（rc=2）；stderr={e4}");
    assert!(
        e4.contains("ext.world.ReadModel.RetractMalformed"),
        "必须点名 `RetractMalformed`——**不许**静默读成「它不是撤回事实」，实得：{e4}"
    );
}

/// **r04｜撤回本身也进账本**。
///
/// ★ **反例**：只改内存／只改投影（账本里没有那一行）⇒ ① 红；
/// ② 再从**另一个进程**读回同一份账本，钉住"它不是内存里的一层壳"。
#[test]
fn r04_the_retraction_itself_is_in_the_ledger_not_only_in_memory() {
    let dir = tmpdir("r04");
    let lp = dir.join("l.jsonl");
    // 第一条与那条**撤回事实**走唯一写入口（都带链）；中间那条**谎称旧值**的只能手造 ＋ 补链
    // （第 13 轮起写入侧会拒它——见 `append_lying_before` 的文档）。
    cli_append(
        &lp,
        "change",
        muted(json!(null), json!(false)),
        "world://core",
        None,
    );
    let bad_id = append_lying_before(&lp, 2, "e-lying-before-2");
    cli_append(
        &lp,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id),
    );

    // ① **账本文件里真有一条撤回事实**（`path=retract_seq` 且 `after=2`）
    let raw = fs::read_to_string(&lp).unwrap();
    assert_eq!(
        raw.lines().count(),
        3,
        "撤回本身也进账本：3 条（2 条效果 ＋ 1 条撤回事实）：\n{raw}"
    );
    assert!(
        raw.contains(RETRACT_PATH) && raw.contains("\"after\":2"),
        "撤回事实必须落在**账本**里：\n{raw}"
    );

    // ② **换一个进程**（新的一次 CLI 调用）照样折得出来 ⇒ 它读的是账本，不是内存
    let (rc, out, err) = cli_state(&lp, &["--json"]);
    assert_eq!(rc, 0, "stderr={err}");
    let v: Value = serde_json::from_str(out.trim()).unwrap();
    assert_eq!(
        v["seen"],
        json!(1),
        "撤回事实**不进 `seen`**（它不是被折叠的那一条）：{out}"
    );
    assert_eq!(
        v["last_seq"],
        json!(3),
        "但**序号照旧推到 3**（过户）：{out}"
    );
    // ③ 库侧同一条口径（`World::read_model` 就是 CLI 那条路）
    let w = World::open_readonly(&factory_ontology(), &lp, &factory_policy()).unwrap();
    let st = w.read_model().unwrap();
    assert_eq!(
        st.retracted().keys().copied().collect::<Vec<u64>>(),
        vec![2],
        "库侧必须答得出「哪一条被撤回」"
    );
}

/// **r05｜撤回后不许回放旧数**。
///
/// 语料**全部可折叠**：一条**真发生过**的改动（`false→true`）被撤回 ⇒
/// 世界现在的值是 `false`——**不是** `true`（那不叫"回放旧数"，那叫"撤回没生效"）。
#[test]
fn r05_a_retracted_effect_is_not_replayed_as_the_current_value() {
    let dir = tmpdir("r05");
    let lp = dir.join("l.jsonl");
    cli_append(
        &lp,
        "change",
        muted(json!(null), json!(false)),
        "world://core",
        None,
    );
    let second = cli_append(
        &lp,
        "change",
        muted(json!(false), json!(true)),
        "world://core",
        None,
    );

    // 正控：撤回**之前**那条改动**是生效的**（否则下面那条红说明不了什么）
    let (rc0, out0, _e0) = cli_state(&lp, &["--json"]);
    assert_eq!(rc0, 0);
    let v0: Value = serde_json::from_str(out0.trim()).unwrap();
    assert_eq!(
        v0["objects"]["world://notice/n-1"]["muted"],
        json!(true),
        "正控：撤回前那条改动必须**生效**：{out0}"
    );

    // 撤回它
    cli_append(
        &lp,
        "change",
        retract_body(2),
        "world://core",
        Some(second["id"].as_str().unwrap()),
    );

    // ① `state`（人读形态）不许回放被撤回的那个值
    let (rc1, out1, err1) = cli_state(&lp, &[]);
    assert_eq!(rc1, 0, "stderr={err1}");
    assert!(
        out1.contains("world://notice/n-1#muted = false"),
        "撤回后**当前的**值必须是 `false`：\n{out1}"
    );
    assert!(
        !out1.contains("#muted = true"),
        "被撤回的 `true` 不许出现在「现在的值」那一行：\n{out1}"
    );

    // ② 界面唯一读路径（视觉投影）也不许回放
    let mut a = base_args(&lp);
    a.push("project".into());
    a.push("visual".into());
    let (rc2, out2, err2) = run_wc(&a);
    assert_eq!(rc2, 0, "`project visual` 必须成功；stderr={err2}");
    assert!(
        out2.contains("muted = false"),
        "投影必须给**撤回后**的值：\n{out2}"
    );
    assert!(
        !out2.contains("muted = true"),
        "投影不许回放被撤回的值：\n{out2}"
    );
}

/// **r06｜★正控：撤回不改变世界现在什么样，且撤回事实不进规范形式**。
///
/// ## 这一条钉的是两件事
///
/// ① **撤回不改变世界现在什么样**：被撤回的那条效果不落账 ⇒ 世界现在的样子
///    ＝「**那条记录从没写进来过**」的样子。可判形态：`objects` ＋ `acts`／`notices`／`seen`
///    与被撤回那条之前的前缀**逐字节相同**（差**只有** `last_seq` 一格）。
/// ② **撤回事实不进规范形式**：把"谁撤的／因为什么"换掉（同一个目标 `seq`）⇒
///    规范形式与状态指纹**一字不变**。
///
/// ## ⚠️ 一处**如实登记的读法差异**（不许把没做到写成做到）
///
/// 任务书的字面是「**撤回前后，`state --json` 的规范形式与状态指纹逐字节相同**」。
/// **字面照读不可能成立**，理由是可核的：`to_json` 的规范形式含 `last_seq` 与 `seen`，
/// 而**追加任何一条事件**都必须过连线自检（[`State::check_next`]）并把 `last_seq` 推上去
/// ⇒ 两本"相差一条事件"的账本**不可能**给出逐字节相同的规范形式。
/// ⇒ 本用例落的是它**最强的可判真形态**：**除 `last_seq`（那一格是"账本的"）之外逐字节相同**，
/// 另加②那条独立断言把"撤回事实不进规范形式"钉死。
/// ③ **与改动前逐字节相同**（金标）：金标值是**本批改动前**的部署件在同一个夹具上的
///    原始输出（`state --json` ＋ 指纹），钉住"`to_json`／`digest` 一个字未动"。
#[test]
fn r06_retraction_does_not_change_the_world_now_and_stays_out_of_the_canonical_form() {
    // ── ① 撤回不改变世界现在什么样 ────────────────────────────────────────
    let d1 = tmpdir("r06a");
    let (lp1, bad_id) = ledger_with_a_lying_before(&d1);
    cli_append(
        &lp1,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id),
    );
    let evs = read_back(&lp1);
    assert_eq!(
        evs.len(),
        3,
        "夹具：3 条（1 条有效 ＋ 1 条坏 ＋ 1 条撤回事实）"
    );
    let now = State::fold(&evs).expect("撤回之后必须折得开");
    // "那条坏记录还没写进来时，世界现在什么样"——它就是这条撤回要恢复的样子
    let reference = State::fold(&evs[..1]).expect("前缀必须折得开");
    assert_eq!(
        now.get("world://notice/n-1", "muted"),
        reference.get("world://notice/n-1", "muted"),
        "撤回不改变世界现在什么样"
    );
    let (mut a, mut b) = (now.to_json(), reference.to_json());
    assert_eq!(
        b["objects"], a["objects"],
        "效果面（objects）必须逐字节相同"
    );
    assert_eq!(b["seen"], a["seen"], "`seen`（已折叠条数）必须相同");
    assert_eq!(b["acts"], a["acts"], "`acts` 必须相同");
    assert_eq!(b["notices"], a["notices"], "`notices` 必须相同");
    // ★ 只归一化 `last_seq`——**序号是账本的**，它不是"世界现在什么样"那一半。
    b["last_seq"] = json!(0);
    a["last_seq"] = json!(0);
    assert_eq!(b, a, "除 `last_seq`（账本的）之外，规范形式必须逐字节相同");

    // ── ② 撤回事实不进规范形式：换掉"谁撤的／因为什么" ⇒ 一字不变 ────────────
    let d2 = tmpdir("r06b");
    let (lp2, bad_id2) = ledger_with_a_lying_before(&d2);
    cli_append(
        &lp2,
        "change",
        retract_body(2),
        "world://core",
        Some(&bad_id2),
    );
    let (_, o1, _) = cli_state(&lp1, &["--json"]);
    let (_, o2, _) = cli_state(&lp2, &["--json"]);
    assert_eq!(
        o1, o2,
        "两本**只差撤回事实的 actor／trace**的账本，`state --json` 必须一字不差"
    );

    // ── ③ 与**改动前**逐字节相同（金标）──────────────────────────────────
    let d3 = tmpdir("r06c");
    let lp3 = d3.join("l.jsonl");
    cli_append(
        &lp3,
        "change",
        muted(json!(null), json!(false)),
        "world://user",
        None,
    );
    cli_append(
        &lp3,
        "act",
        event::act_body("notice.mute", "do", "r1", json!({})),
        "world://user",
        None,
    );
    cli_append(
        &lp3,
        "notice",
        event::notice_body("muted", "world://notice/n-1", json!({})),
        "world://user",
        None,
    );
    let (rc, out, err) = cli_state(&lp3, &["--json"]);
    assert_eq!(rc, 0, "stderr={err}");
    assert_eq!(
        out.trim(),
        GOLDEN_STATE_JSON,
        "`state --json` 的规范形式必须与**本批改动前**的部署件逐字节相同（`to_json` 一个字未动）"
    );
    let (_, human, _) = cli_state(&lp3, &[]);
    assert!(
        human.contains("指纹 : fnv1a64:0a7540b3bdf42d6b"),
        "状态指纹也必须与改动前逐字节相同：\n{human}"
    );
    // 规范形式里**没有**撤回字样，且顶层键集合恰为那五个
    let v: Value = serde_json::from_str(out.trim()).unwrap();
    let keys: Vec<String> = v
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .map(str::to_string)
        .collect();
    assert_eq!(
        keys,
        vec!["acts", "last_seq", "notices", "objects", "seen"],
        "撤回事实不进规范形式 ⇒ 顶层键集合恰为这五个：{out}"
    );
    assert!(
        !out.contains("retract"),
        "规范形式里不许出现撤回字样：{out}"
    );
}

/// **本批改动前**的部署件（`/usr/bin/world-core`，2026-10-03 17:59 那一个）在
/// 「一条 `change`（`muted`：首见 → `false`）＋ 一条 `act` ＋ 一条 `notice`」上的
/// `state --json` **原始输出**（逐字节抄回，未做任何推算）。
///
/// 为什么把它冻成字面量：**"撤回没改规范形式"这句话要能红**——把 `to_json` 加一个键，
/// 或者把 `digest` 的输入换掉，这里当场不等。
const GOLDEN_STATE_JSON: &str = r#"{"acts":1,"last_seq":3,"notices":1,"objects":{"world://notice/n-1":{"muted":false}},"seen":3}"#;
