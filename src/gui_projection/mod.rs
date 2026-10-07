//! 投影（`M06` 语言投影 / `M07` 视觉投影）—— **同源的两张面孔**。
//!
//! ## 铁律：投影之间不交互
//!
//! 两个投影是**出口节点**，不是流水线：
//!
//! ```text
//!              ┌──────────────┐
//!   账本 ──fold─┤  读模型 State ├─┬──► 语言投影（结构化出口）  → 程序
//!              └──────────────┘ └──► 视觉投影（渲染出口）    → 人
//! ```
//!
//! 谁都不许读对方的输出，谁也不许持有状态。这就是"两投影之间不交互"
//! （`07/2-依据/15` §三）。因此本模块的两个渲染函数**只接受
//! `(&State, world, vocab_hash)`，返回 `String`**——没有共享可变缓存可挂，
//! 也就没有"两个投影各自记一份"的余地。
//!
//! ## "同源"怎么变成**可检验**的，而不是一句口号
//!
//! 每份投影的**第一行**都是同一个机器可读的**同源头**：
//!
//! ```text
//! #world-core projection=language world=1 vocab=fnv1a64:… last_seq=3 state=fnv1a64:…
//! ```
//!
//! 于是"同源"可以被机器判定（[`assert_same_source`]）：
//! - `world` 与 `vocab` 相同 ⇒ 两份投影用的是**同一份词表**（内容寻址，见
//!   [`crate::ontology_definition::Ontology::vocab_hash`]）；
//! - `last_seq` 与 `state` 相同 ⇒ 两份投影说的是**同一个状态**。
//!
//! 换了词表、或有一方落后了一个事件，`assert_same_source` 就会失败。
//! 这就是 `WC-SRS-001` REQ-F-020 的自动化检验面。
//!
//! ## 视觉投影也是可审计的
//!
//! 视觉投影是给人的，但**不是不可解析的**：它的取值行必须能被审计脚本提取
//! （`      muted = false`）。否则"同源"根本无法证明——
//! **给人看的东西也要能被机器核对**，这是本项目对"可信"的最低要求。

pub mod language;
pub mod surface;
pub mod visual;

use crate::ontology_instance::readmodel::State;
use serde_json::Value;

/// 把扁平的 `(主体, 路径, 值)` 归拢成 `(主体, [(路径, 值)])`。
///
/// `State::entries()` 已保证主体有序、路径有序，故只需顺序扫描；
/// 结果天然确定（同样的账本 ⇒ 同样的字节）。
///
/// 两个投影共用这一个归拢函数，是"同源"在**代码层**的体现：
/// 它们对"什么算一个主体、字段怎么排"不可能有分歧。
pub(crate) fn group_by_subject(state: &State) -> Vec<(String, Vec<(String, Value)>)> {
    let mut out: Vec<(String, Vec<(String, Value)>)> = Vec::new();
    for (subject, path, value) in state.entries() {
        match out.last_mut() {
            Some((cur, fields)) if cur == subject => {
                fields.push((path.to_string(), value.clone()));
            }
            _ => out.push((subject.to_string(), vec![(path.to_string(), value.clone())])),
        }
    }
    out
}

/// 同源头（两份投影共用的机器可读首行）。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Header {
    pub projection: String,
    pub world: u64,
    pub vocab: String,
    pub last_seq: u64,
    pub state: String,
}

/// 生成同源头那一行（两份投影必须**逐字一致**，只有 `projection` 不同）。
pub fn header_line(projection: &str, world: u64, vocab: &str, state: &State) -> String {
    format!(
        "#world-core projection={projection} world={world} vocab={vocab} last_seq={} state={}",
        state.last_seq(),
        state.digest()
    )
}

/// 解析同源头。
pub fn parse_header(text: &str) -> Result<Header, String> {
    let line = text
        .lines()
        .next()
        .ok_or_else(|| "投影输出为空".to_string())?;
    if !line.starts_with("#world-core ") {
        return Err(format!("投影首行不是同源头：{line}"));
    }
    let mut fields = std::collections::BTreeMap::new();
    for tok in line.trim_start_matches("#world-core ").split_whitespace() {
        if let Some((k, v)) = tok.split_once('=') {
            fields.insert(k.to_string(), v.to_string());
        }
    }
    let get = |k: &str| -> Result<String, String> {
        fields
            .get(k)
            .cloned()
            .ok_or_else(|| format!("同源头缺少字段 `{k}`：{line}"))
    };
    Ok(Header {
        projection: get("projection")?,
        world: get("world")?
            .parse()
            .map_err(|e| format!("同源头的 world 不是整数：{e}"))?,
        vocab: get("vocab")?,
        last_seq: get("last_seq")?
            .parse()
            .map_err(|e| format!("同源头的 last_seq 不是整数：{e}"))?,
        state: get("state")?,
    })
}

/// **同源判定**：两份投影必须说同一件事。
///
/// 只比较"身份"三项（`world` / `vocab` / `last_seq` + `state` 指纹），
/// **不比较排版**——语言投影与视觉投影本来就长得不一样，
/// 强求文本一致是把"同源"错解成"同一份文件"。
pub fn assert_same_source(a: &str, b: &str) -> Result<(), String> {
    let (ha, hb) = (parse_header(a)?, parse_header(b)?);
    if ha.world != hb.world {
        return Err(format!(
            "不同源：世界版本不同（{} vs {}）",
            ha.world, hb.world
        ));
    }
    if ha.vocab != hb.vocab {
        return Err(format!(
            "不同源：**词表不同**（{} 的 vocab={}，{} 的 vocab={}）——\
             这说明两份投影读的不是同一份法律，必须停下来查清",
            ha.projection, ha.vocab, hb.projection, hb.vocab
        ));
    }
    if ha.last_seq != hb.last_seq || ha.state != hb.state {
        return Err(format!(
            "不同源：状态不同（{}: last_seq={} state={}；{}: last_seq={} state={}）——\
             有一方落后或读的不是同一本账",
            ha.projection, ha.last_seq, ha.state, hb.projection, hb.last_seq, hb.state
        ));
    }
    Ok(())
}

#[cfg(test)]
mod unit {
    use super::*;
    use crate::common::event;
    use crate::ontology_instance::readmodel::State;
    use serde_json::json;

    fn state_with_one_event() -> State {
        let evs = vec![event::new_event(
            1,
            "change",
            "world://test",
            event::change_body("world://s", "p", json!(null), json!(1)),
        )];
        State::fold(&evs).unwrap()
    }

    #[test]
    fn same_state_is_same_source() {
        let s = state_with_one_event();
        let a = language::render(&s, 1, "fnv1a64:aaaa");
        let b = visual::render(&s, 1, "fnv1a64:aaaa");
        assert!(assert_same_source(&a, &b).is_ok());
        // 首行除 projection 外必须一致
        let (la, lb) = (a.lines().next().unwrap(), b.lines().next().unwrap());
        assert!(la.contains("projection=language"));
        assert!(la.contains("world=1"));
        assert!(la.contains("vocab=fnv1a64:aaaa"));
        assert!(la.contains("last_seq=1"));
        assert_eq!(
            la.replace("projection=language", "projection=X"),
            lb.replace("projection=visual", "projection=X"),
            "同源头应逐字一致（仅 projection 字段不同）"
        );
    }

    #[test]
    fn different_vocab_is_detected() {
        let s = state_with_one_event();
        let a = language::render(&s, 1, "fnv1a64:aaaa");
        let b = visual::render(&s, 1, "fnv1a64:bbbb");
        let e = assert_same_source(&a, &b).unwrap_err();
        assert!(e.contains("词表不同"), "实得: {e}");
    }

    #[test]
    fn lagging_projection_is_detected() {
        let s1 = state_with_one_event();
        let evs = vec![
            event::new_event(
                1,
                "change",
                "world://test",
                event::change_body("world://s", "p", json!(null), json!(1)),
            ),
            event::new_event(
                2,
                "change",
                "world://test",
                event::change_body("world://s", "p", json!(1), json!(2)),
            ),
        ];
        let s2 = State::fold(&evs).unwrap();
        let a = language::render(&s1, 1, "fnv1a64:aaaa");
        let b = visual::render(&s2, 1, "fnv1a64:aaaa");
        let e = assert_same_source(&a, &b).unwrap_err();
        assert!(e.contains("状态不同"), "实得: {e}");
    }

    #[test]
    fn malformed_header_is_rejected() {
        assert!(assert_same_source("随便一段文本", "x").is_err());
    }
}
