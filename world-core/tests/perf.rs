//! **L3 性能、可靠性与崩溃恢复度量**（`WC-SQAP-001` 度量规程 **M-01**（写入可靠性）/
//! **M-02**（恢复）/ **M-05**（重放）；质量目标 `QG-01` / `QG-02` / `QG-05`）。
//!
//! ## 为什么单独一个文件、且默认 `#[ignore]`
//!
//! 1. **它不断言墙钟**。`WC-TP-001` §二-2 的硬约束是"不依赖墙钟"——
//!    因为墙钟随机器负载抖动，断言它会把测试变成"随机红"。本文件的立场是：
//!    **测量**与**判定**分开——本文件只产出原始数值（命令 + 输出 + 提交号），
//!    `QG-05` 的判据（`【候选】≤ 2 s（P95）`）是否成立**由人裁定**；
//! 2. 100 000 条事件的合成 + 20 次冷启动若进常规 `cargo test`，会让 CI 从秒级变成分钟级，
//!    并使"确定性"这一条失效。故 `#[ignore]`，只在度量时显式运行。
//!
//! ## 运行方式（VM 内）
//!
//! ```text
//! cd /root/world/world-core
//! cargo test --release --test perf -- --ignored --nocapture
//! # 可调：WC_PERF_N（事件条数，默认 100000）、WC_PERF_SAMPLES（样本数，默认 20）、
//! #       WC_PERF_APPEND_N（真实追加条数，默认 10000）
//! ```
//!
//! ## 口径（与 `M-05` 一致）
//!
//! - **账本是合成的**：直接按"信封 + 摘要链"规则写出 N 行 JSON Lines
//!   （含真实 `chain`，故启动时的 `load_chain` 全链核验也在计时范围内）；
//!   之所以不经 `World::commit`：那样每条事件要 `fsync` 一次，合成本身会成为瓶颈，
//!   测的就不是"重放"了。**合成只是夹具，不是写入路径**；
//! - **冷启动全量 fold**：`World::open`（含静态墙、单写者锁、逐行 seq 校验、
//!   全链核验）+ `read_model()`（全量折叠）；
//! - **样本数** ≥ 20（`M-05` 要求），报 **P50 / P95 / min / max**；
//! - `change` 事件的 `before` 必须**自洽**（否则折叠会以 `BeforeMismatch` 拒收）——
//!   合成器按"同一 (主体, 字段) 的第 k 次出现"递推，故这是**真实的折叠路径**，
//!   不是"全是 notice 的空转"。
//!
//! ## `M-01` 走的是**真实写入路径**
//!
//! 与 M-05 相反：`QG-01` 度量的就是"追加不丢不重"，故它**必须**经 `World::commit`
//! （每条一次 `fsync`）。这也意味着它比 M-05 慢得多——那正是它默认 `#[ignore]` 的原因之一。

use serde_json::{json, Value};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use world_core::{common::event, ledger, World};

const DEFAULT_N: usize = 100_000;
const DEFAULT_SAMPLES: usize = 20;

fn env_usize(key: &str, default: usize) -> usize {
    std::env::var(key)
        .ok()
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(default)
}

fn ontology() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/ontology_definition/ontology.json")
}

fn policy() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/gate/policy.json")
}

/// 一次性沙箱目录（0700：账本的静态防线要求所在目录不得对 group/other 可写）。
fn sandbox(tag: &str) -> PathBuf {
    use std::os::unix::fs::PermissionsExt;
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let d = std::env::temp_dir().join(format!("wc-perf-{tag}-{n}"));
    fs::create_dir_all(&d).unwrap();
    fs::set_permissions(&d, fs::Permissions::from_mode(0o700)).unwrap();
    d
}

/// 合成一本 N 条事件、**带完整摘要链**的账本。
///
/// 事件构成（刻意混合三家族，让折叠不是空转）：
/// - 主体 `world://obj/{seq%1000}`，字段 `field-{seq%8}`，故同一 (主体,字段)
///   每 1000 条复现一次，第 k 次出现的值 = `k % 2 == 0`（**前后自洽**）；
/// - 每 100 条中：1 条 `act`、1 条 `notice`，其余为 `change`。
///
/// ⚠️ 这里的主体/字段名**故意不改成出厂本体里声明过的那两个**（`notice.muted` / `job.status`），
/// 理由两条，都是可核的：
/// 1. 本函数**不经过写入路径**——它直接把 JSON Lines 写进文件，是"夹具"而不是"世界的写入"；
///    按 `concepts` 校验实体与字段的那道闸在写入侧（`src/ontology_definition/mod.rs::check_concepts`），
///    折叠侧只查 seq 连续／家族存在／`before` 自洽（`src/ontology_instance/readmodel.rs:92-149`），故本夹具过得去；
/// 2. 要保住的是"**同一主体下 8 个不同字段**、每个字段每 1000 条复现一次"这个构造——
///    出厂本体只声明了 2 格字段，改成声明过的名字就得把 8 个字段压成 2 个，
///    测的就不再是"多字段、多主体的重放"了。**改它=把度量对象改小**，故不改。
fn synthesize(dir: &Path, n: usize) -> PathBuf {
    let path = dir.join("ledger.jsonl");
    let f = fs::File::create(&path).unwrap();
    let mut w = std::io::BufWriter::new(f);
    let mut prev = ledger::CHAIN_GENESIS.to_string();

    for seq in 1..=n as u64 {
        let subject = format!("world://obj/{:04}", seq % 1000);
        let (kind, actor, body) = if seq % 100 == 0 {
            (
                "act",
                "world://user",
                event::act_body("notice.mute", "do", &format!("r-{seq}"), json!({})),
            )
        } else if seq % 100 == 50 {
            (
                "notice",
                "world://core",
                event::notice_body("job.done", &subject, json!({ "exit": 0 })),
            )
        } else {
            // 第 k 次出现（k = (seq-1)/1000）：before = 上一次写入的值，after = 本次的值
            let k = (seq - 1) / 1000;
            let before = k % 2 == 1; // k=0 时无当前值，折叠不核 before（自洽检查）
            let after = k % 2 == 0;
            (
                "change",
                "world://user",
                event::change_body(
                    &subject,
                    &format!("field-{:02}", seq % 8),
                    json!(before),
                    json!(after),
                ),
            )
        };

        let mut ev = event::new_event(seq, kind, actor, body);
        let chain = ledger::event_chain(&prev, &ev).unwrap();
        ev.as_object_mut()
            .unwrap()
            .insert("chain".to_string(), Value::String(chain.clone()));
        prev = chain;
        w.write_all(ledger::encode_line(&ev).unwrap().as_bytes())
            .unwrap();
        w.write_all(b"\n").unwrap();
    }
    w.flush().unwrap();
    path
}

/// 排好序后取分位数（`p` ∈ (0,1]）：`ceil(p*len)` 处的值。
fn percentile(sorted: &[Duration], p: f64) -> Duration {
    let idx = ((p * sorted.len() as f64).ceil() as usize).clamp(1, sorted.len()) - 1;
    sorted[idx]
}

fn ms(d: Duration) -> f64 {
    d.as_secs_f64() * 1000.0
}

/// 打印一行统计（**只测量、不判定**）。
fn report(label: &str, mut samples: Vec<Duration>) {
    samples.sort();
    let sum: f64 = samples.iter().map(|d| ms(*d)).sum();
    println!(
        "[{label}] 样本={} min={:.2}ms P50={:.2}ms P95={:.2}ms max={:.2}ms mean={:.2}ms",
        samples.len(),
        ms(samples[0]),
        ms(percentile(&samples, 0.50)),
        ms(percentile(&samples, 0.95)),
        ms(*samples.last().unwrap()),
        sum / samples.len() as f64
    );
    println!(
        "[{label}] 全部样本(ms, 升序)：{}",
        samples
            .iter()
            .map(|d| format!("{:.2}", ms(*d)))
            .collect::<Vec<_>>()
            .join(" ")
    );
    println!(
        "[{label}] ⚠️ 判据（QG-05/QG-02 的目标值）仍为【候选】，**本行不作达标判定**——\
         是否达标须由人依 WC-SQAP-001 §2.1 裁定"
    );
}

/// `QG-05` / `M-05`：**10 万条事件冷启动全量重放**。
///
/// 断言只有"结构正确"（折叠出的事件数、状态指纹跨样本一致）——**不断言耗时**。
#[test]
#[ignore = "L3 度量：用 cargo test --release --test perf -- --ignored --nocapture 显式运行"]
fn qg05_full_replay_of_100k_events() {
    let n = env_usize("WC_PERF_N", DEFAULT_N);
    let samples_n = env_usize("WC_PERF_SAMPLES", DEFAULT_SAMPLES);
    let d = sandbox("qg05");
    let t_syn = Instant::now();
    let lp = synthesize(&d, n);
    let syn = t_syn.elapsed();
    let bytes = fs::metadata(&lp).unwrap().len();

    println!(
        "== QG-05 冷启动全量重放 ==\n事件数={n} 文件={} 字节 合成耗时={:.2}ms 样本数={samples_n}",
        bytes,
        ms(syn)
    );

    let mut samples = Vec::with_capacity(samples_n);
    let mut digests = Vec::with_capacity(samples_n);
    for i in 0..samples_n {
        let t = Instant::now();
        let w = World::open(&ontology(), &lp, &policy()).unwrap();
        let st = w.read_model().unwrap();
        let dt = t.elapsed();
        assert_eq!(st.last_seq(), n as u64, "第 {i} 次样本：必须折叠出全部事件");
        digests.push(st.digest());
        samples.push(dt);
        drop(w); // 释放单写者锁，下一次样本才能重新打开
    }

    // 结构不变量（与机器快慢无关）：跨样本状态指纹必须完全一致 ⇒ 重放是确定性的
    assert!(
        digests.windows(2).all(|p| p[0] == p[1]),
        "同一账本的重放结果必须逐字节一致（否则'状态=折叠账本'不成立）"
    );
    println!("状态指纹（全部样本一致）：{}", digests[0]);
    report("QG-05 冷启动+全量fold", samples);
}

/// `QG-02` / `M-02`：**崩溃恢复**——账本末尾留半行时，启动必须**丢弃半行**并照常工作。
///
/// 造法：复制一本干净账本，每次样本先追加一段**不含换行的半行**再启动
/// （正是"崩在行中间"的形状）；启动后文件必须回到干净账本的**精确长度**。
#[test]
#[ignore = "L3 度量：用 cargo test --release --test perf -- --ignored --nocapture 显式运行"]
fn qg02_crash_recovery_with_a_torn_tail() {
    let n = env_usize("WC_PERF_N", DEFAULT_N);
    let samples_n = env_usize("WC_PERF_SAMPLES", DEFAULT_SAMPLES);
    let d = sandbox("qg02");
    let clean = synthesize(&d, n);
    let clean_len = fs::metadata(&clean).unwrap().len();
    let lp = d.join("crashed.jsonl");
    fs::create_dir_all(lp.parent().unwrap()).unwrap();
    fs::copy(&clean, &lp).unwrap();

    // 半行：被截断的 JSON，且**不含换行**
    let torn = br#"{"world":1,"kind":"notice","id":"n-torn","seq":100001,"at":"t0","actor":"world://core","flags":[],"body":{"type":"x","subjec"#;

    println!(
        "== QG-02 崩溃恢复（末尾半行）==\n干净账本={clean_len} 字节 事件数={n} 半行={} 字节 样本数={samples_n}",
        torn.len()
    );

    let mut samples = Vec::with_capacity(samples_n);
    for i in 0..samples_n {
        // 复位到干净长度后追加半行（等价于"每次都是一次新的崩溃现场"）
        fs::OpenOptions::new()
            .write(true)
            .open(&lp)
            .unwrap()
            .set_len(clean_len)
            .unwrap();
        fs::OpenOptions::new()
            .append(true)
            .open(&lp)
            .unwrap()
            .write_all(torn)
            .unwrap();

        let t = Instant::now();
        let w = World::open(&ontology(), &lp, &policy()).unwrap();
        let st = w.read_model().unwrap();
        let dt = t.elapsed();
        assert_eq!(
            st.last_seq(),
            n as u64,
            "第 {i} 次样本：恢复后必须只保留完整行"
        );
        assert_eq!(
            fs::metadata(&lp).unwrap().len(),
            clean_len,
            "第 {i} 次样本：半行必须被截掉，文件长度回到干净账本"
        );
        samples.push(dt);
        drop(w);
    }
    report("QG-02 崩溃恢复", samples);
    println!(
        "⚠️ 本用例只覆盖「末尾半行」这一种崩溃尾迹；**掉电丢 fsync 后已 ack 事件**\
         属于文件系统/硬件层，未在内（见 WC-TS-001 §三）"
    );
    let _ = fs::remove_dir_all(&d);
}

/// `QG-01` / `M-01`：**追加 10 000 条事件——丢 0 条、重 0 条**。
///
/// 这里经**真实写入路径**（`World::commit`，每条一次 `fsync`），与 `M-05` 的合成夹具相反：
/// 要度量的正是写入可靠性本身。断言的都是**数据事实**（条数、`seq` 连续、`id` 去重、
/// 逐行可解析），不是墙钟；耗时只作旁证打印。
#[test]
#[ignore = "L3 度量：用 cargo test --release --test perf -- --ignored --nocapture 显式运行"]
fn qg01_append_10k_without_loss_or_duplication() {
    use std::collections::HashSet;

    let n = env_usize("WC_PERF_APPEND_N", 10_000);
    let d = sandbox("qg01");
    let lp = d.join("ledger.jsonl");
    let mut w = World::open(&ontology(), &lp, &policy()).unwrap();

    let mut ids: HashSet<String> = HashSet::new();
    let t = Instant::now();
    for i in 0..n {
        // 同一 (主体, 字段) 每 500 条复现一次；第 k 次出现的 before 必须等于上一次的 after
        let occ = i / 500;
        // 主体必须是**出厂本体里已声明的实体**：本用例走的是真实写入路径（`World::commit`），
        // 而写入侧现在按 `ontology.json` 的 `concepts` 校验实体与字段（书 §5.3「声明以外的东西
        // 不许落账」，执行者 `src/ontology_definition/mod.rs::check_concepts`）。原先写 `world://obj/{i}`——
        // `obj` 没声明过 ⇒ 第 0 条就被拒、`unwrap_or_else` 当场 panic（rc=101）。
        // 字段 `muted` 本来就是 `notice` 声明过的那一格（`concepts.notice.fields`），
        // 故**只换实体名**：`world://obj/…` → `world://notice/…`（其余构造一字未动）。
        let subject = format!("world://notice/{:04}", i % 500);
        let ev = w
            .commit(
                "change",
                "world://user",
                event::change_body(&subject, "muted", json!(occ % 2 == 1), json!(occ % 2 == 0)),
            )
            .unwrap_or_else(|e| panic!("第 {i} 条追加被拒（不该发生）：{e}"));
        assert_eq!(
            ev["seq"].as_u64(),
            Some(i as u64 + 1),
            "第 {i} 条：seq 必须连续分配"
        );
        ids.insert(ev["id"].as_str().unwrap().to_string());
    }
    let append_elapsed = t.elapsed();

    // ── 全量读回比对（M-01 的判据）──
    let t = Instant::now();
    let all = w.ledger().read_all().unwrap();
    let readback_elapsed = t.elapsed();

    let mut seq_ok = true;
    for (i, ev) in all.iter().enumerate() {
        seq_ok &= ev["seq"].as_u64() == Some(i as u64 + 1);
    }
    let st = w.read_model().unwrap();

    println!("== QG-01 追加可靠性 ==");
    println!(
        "追加条数={n} 读回条数={} 唯一 id 数={} seq 连续={} 账本={} 字节",
        all.len(),
        ids.len(),
        seq_ok,
        fs::metadata(&lp).unwrap().len()
    );
    println!(
        "耗时旁证（非判据）：追加 {:.2}ms（{:.0} 条/秒，每条含 fsync）/ 全量读回 {:.2}ms",
        ms(append_elapsed),
        n as f64 / append_elapsed.as_secs_f64(),
        ms(readback_elapsed)
    );
    println!(
        "[QG-01] ⚠️ 判据（QG-01 的目标值）仍为【候选】，**本行不作达标判定**——\
         是否达标须由人依 WC-SQAP-001 §2.1 裁定"
    );

    assert_eq!(all.len(), n, "丢事件：读回条数 {n} → {}", all.len());
    assert_eq!(ids.len(), n, "重事件：唯一 id 数 {n} → {}", ids.len());
    assert!(seq_ok, "seq 必须 1..=N 连续无缺号无重号");
    assert_eq!(st.last_seq(), n as u64);
    let _ = fs::remove_dir_all(&d);
}
