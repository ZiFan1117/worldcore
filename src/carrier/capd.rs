//! 执行清单（`cap.d`）的解析 —— **声明是怎么干的，不是允不允许**。
//!
//! ## 与本体的关系：同一个词表，两个用途
//!
//! 本体（`ontology.json`）规定"一条事件长什么样"；执行清单规定"一项能力在载体上怎么干"。
//! 两者都是**运行时装起来的纯文本**，都不写进代码——这是"世界的法律不硬编码"的同一纪律。
//!
//! ## 为什么不用 YAML
//!
//! 载体侧的旧实现在声明文件上用了 YAML。本工程把它换成 **JSON**，理由有两条，都是硬理由：
//!
//! 1. **零外部依赖纪律**：本工程只允许一个 JSON 库；引入 YAML 解析器就破了这条纪律，
//!    而这条纪律的用处是"**换语言 = 世界不归零**"——账本、法律、协议全是纯文本，
//!    不依赖任何语言的专有库；
//! 2. **同一门语言读同一份格式**：清单与本体、账本、策略现在都是 JSON，
//!    读它们只需要一个解析器，不需要"这一份用 A、那一份用 B"。
//!
//! ## 清单长什么样
//!
//! ```json
//! { "capability": "notice.mute",
//!   "provider":   "backlight",
//!   "verbs":      ["get", "set"],
//!   "risk":       "low",
//!   "undo":       "never",
//!   "confirm":    "never",
//!   "sandbox":    "none" }
//! ```
//!
//! ## ★ 两栏各用各的词表：`capability` 说"叫什么"，`provider` 说"怎么实现"
//!
//! **`capability` 写的是"叫什么"，不是"怎么实现"**——它是**语义层的名字**
//! （与本体 `_interfaces`、门禁策略的能力表同一套词表：`notice.mute`／`job.start`…）。
//! **设备词属于 `provider` 那一边**（`backlight`／`package`／`job` 才是"怎么实现"）。
//! 两栏**不许互换**：把 `brightness.set` 写成 `capability`，等于让本体里根本没有的名字
//! 冒充一项能力，而真正该被问到的那一栏（"谁能实现它"）永远没人问。
//!
//! 同一条口径落在执行器一侧：`Provider::capabilities()` 自报的也必须是**语义层的名字**，
//! 否则 `cap.d` 与执行器会各有一个**合法**名字、却对不上——那不是拼写错，是**两套词表撞车**。
//! 对账判据见 [`crate::carrier::providers::cross_check`]。
//!
//! **注意这里没有"允不允许"这一栏**：清单只说怎么干。允不允许由门禁裁决
//! （内核持有的门禁策略），本模块**永远不能放行**。

use serde_json::Value;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// 风险分级。**只影响本模块的处置轻重**（要不要先撤销、要不要人确认），
/// **不影响"允不允许"**——那是门禁的事。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Risk {
    Low,
    Medium,
    High,
}

/// 撤销策略（**载体撤销**，不是世界回滚）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Undo {
    /// 不撤销。
    Never,
    /// 每次动手前先做一次载体撤销点。
    BeforeEach,
}

/// 确认策略（**人**的确认，不是门禁的裁决）。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Confirm {
    /// 不需要确认。
    Never,
    /// 需要人确认；确认入口不可用或人未确认 ⇒ **拒绝执行**（默认拒绝，不是默认放行）。
    Required,
}

/// 一项能力的执行清单。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capability {
    /// 能力名——**语义层的名字**（与本体 `_interfaces`、门禁策略的能力表同一套词表）。
    ///
    /// **不是设备名**：设备词（"怎么实现"）属于 [`Capability::provider`] 那一栏。
    pub name: String,
    /// 用哪个执行器（**设备词／实现词**，如 `backlight`）。
    pub provider: String,
    /// 允许哪些动词（**本模块自己的**收窄：清单外的动词直接拒）。
    pub verbs: Vec<String>,
    /// 风险分级。
    pub risk: Risk,
    /// 撤销策略。
    pub undo: Undo,
    /// 确认策略。
    pub confirm: Confirm,
    /// 沙箱参数（v1 只登记，不实施；实施属第二版）。
    pub sandbox: String,
    /// 本项来自哪个文件（报错时能点名）。
    pub source: PathBuf,
}

impl Capability {
    /// 该能力是否放行此动词（**只回答"清单里有没有"，不回答"准不准"**）。
    pub fn allows(&self, verb: &str) -> bool {
        self.verbs.iter().any(|v| v == verb)
    }

    /// 是否需要在动手前先做载体撤销点。
    pub fn needs_undo(&self) -> bool {
        self.undo == Undo::BeforeEach && self.risk == Risk::High
    }

    /// 是否需要人确认。
    pub fn needs_confirm(&self) -> bool {
        self.confirm == Confirm::Required
    }
}

/// 执行清单（全部已加载能力的索引，键为能力名）。
#[derive(Debug, Clone, Default)]
pub struct Manifest {
    caps: BTreeMap<String, Capability>,
}

fn parse_risk(s: &str, who: &str) -> Result<Risk, String> {
    match s {
        // 未声明风险 = **低危**（不是高危，也不是"非法"）。
        // 口径：清单的必填项只有三项（能力名、执行器、动词表）；风险/撤销/确认是可选增强，
        // 缺省时取**最轻**的处置——**但这绝不等于"更容易被放行"**：
        // 允不允许与 risk 无关，那由门禁裁决。
        "" | "low" => Ok(Risk::Low),
        "medium" => Ok(Risk::Medium),
        "high" => Ok(Risk::High),
        other => Err(format!(
            "ext.world.Carrier.BadManifest: 能力 `{who}` 的 risk=`{other}` 非法（只允许 low/medium/high）"
        )),
    }
}

fn parse_undo(s: &str, who: &str) -> Result<Undo, String> {
    match s {
        "" | "never" => Ok(Undo::Never),
        "before-each" => Ok(Undo::BeforeEach),
        other => Err(format!(
            "ext.world.Carrier.BadManifest: 能力 `{who}` 的 undo=`{other}` 非法（只允许 never/before-each）"
        )),
    }
}

fn parse_confirm(s: &str, who: &str) -> Result<Confirm, String> {
    match s {
        "" | "never" => Ok(Confirm::Never),
        "required" => Ok(Confirm::Required),
        other => Err(format!(
            "ext.world.Carrier.BadManifest: 能力 `{who}` 的 confirm=`{other}` 非法（只允许 never/required）"
        )),
    }
}

impl Manifest {
    /// 解析一份清单文件的内容。
    pub fn parse(raw: &str, source: &Path) -> Result<Capability, String> {
        let v: Value = serde_json::from_str(raw).map_err(|e| {
            format!(
                "ext.world.Carrier.BadManifest: 执行清单不是合法 JSON（{}）：{e}",
                source.display()
            )
        })?;
        let name = v
            .get("capability")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                format!(
                    "ext.world.Carrier.BadManifest: {} 缺 capability",
                    source.display()
                )
            })?
            .to_string();
        let provider = v
            .get("provider")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                format!(
                    "ext.world.Carrier.BadManifest: 能力 `{name}` 缺 provider（{}）",
                    source.display()
                )
            })?
            .to_string();
        let verbs: Vec<String> = v
            .get("verbs")
            .and_then(Value::as_array)
            .ok_or_else(|| format!("ext.world.Carrier.BadManifest: 能力 `{name}` 缺 verbs 数组"))?
            .iter()
            .filter_map(Value::as_str)
            .map(str::to_string)
            .collect();
        if verbs.is_empty() {
            return Err(format!(
                "ext.world.Carrier.BadManifest: 能力 `{name}` 的 verbs 为空——\
                 空动词表不是『什么都不允许』的安全默认，而是『清单没写好』"
            ));
        }
        let risk = parse_risk(v.get("risk").and_then(Value::as_str).unwrap_or(""), &name)?;
        let undo = parse_undo(v.get("undo").and_then(Value::as_str).unwrap_or(""), &name)?;
        let confirm = parse_confirm(
            v.get("confirm").and_then(Value::as_str).unwrap_or(""),
            &name,
        )?;
        let sandbox = v
            .get("sandbox")
            .and_then(Value::as_str)
            .unwrap_or("none")
            .to_string();

        Ok(Capability {
            name,
            provider,
            verbs,
            risk,
            undo,
            confirm,
            sandbox,
            source: source.to_path_buf(),
        })
    }

    /// 从目录加载全部 `.json` 清单；同名能力后加载者覆盖前者（按文件名有序，故结果确定）。
    pub fn load_dir(dir: &Path) -> Result<Self, String> {
        let mut entries: Vec<PathBuf> = std::fs::read_dir(dir)
            .map_err(|e| {
                format!(
                    "ext.world.Carrier.ManifestDirFail: 读取执行清单目录 {}：{e}",
                    dir.display()
                )
            })?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.is_file())
            .filter(|p| {
                p.extension()
                    .and_then(|s| s.to_str())
                    .map(|s| s.eq_ignore_ascii_case("json"))
                    .unwrap_or(false)
            })
            .collect();
        entries.sort();

        let mut caps = BTreeMap::new();
        for p in entries {
            let raw = std::fs::read_to_string(&p).map_err(|e| {
                format!(
                    "ext.world.Carrier.ManifestReadFail: 读不了 {}：{e}",
                    p.display()
                )
            })?;
            let c = Self::parse(&raw, &p)?;
            caps.insert(c.name.clone(), c);
        }
        Ok(Manifest { caps })
    }

    /// 从一组内存清单构建（测试与内嵌默认用）。
    pub fn from_caps(caps: Vec<Capability>) -> Self {
        let mut m = BTreeMap::new();
        for c in caps {
            m.insert(c.name.clone(), c);
        }
        Manifest { caps: m }
    }

    /// 查一项能力（键有序，故遍历确定）。
    pub fn lookup(&self, name: &str) -> Option<&Capability> {
        self.caps.get(name)
    }

    /// 全部能力名（有序）。
    pub fn names(&self) -> Vec<&str> {
        self.caps.keys().map(String::as_str).collect()
    }

    /// 遍历全部能力（有序）。
    pub fn iter(&self) -> impl Iterator<Item = &Capability> {
        self.caps.values()
    }

    /// 清单是否为空（空清单**不是**"什么都不允许"的安全默认，而是"没装清单"）。
    pub fn is_empty(&self) -> bool {
        self.caps.is_empty()
    }
}

#[cfg(test)]
mod unit {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("wc-capd-{}-{}", tag, std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn parses_a_wellformed_manifest() {
        let raw = r#"{"capability":"notice.mute","provider":"backlight",
                      "verbs":["get","set"],"risk":"low","undo":"never",
                      "confirm":"never","sandbox":"none"}"#;
        let c = Manifest::parse(raw, Path::new("t.json")).unwrap();
        assert_eq!(c.name, "notice.mute");
        assert_eq!(c.provider, "backlight");
        assert!(c.allows("set"));
        assert!(!c.allows("uninstall"));
        assert!(!c.needs_undo());
        assert!(!c.needs_confirm());
    }

    #[test]
    fn high_risk_with_before_each_needs_undo() {
        let raw = r#"{"capability":"ledger.compact","provider":"package",
                      "verbs":["install"],"risk":"high","undo":"before-each",
                      "confirm":"required"}"#;
        let c = Manifest::parse(raw, Path::new("p.json")).unwrap();
        assert!(c.needs_undo());
        assert!(c.needs_confirm());
        assert_eq!(c.sandbox, "none");
    }

    #[test]
    fn a_manifest_may_omit_the_optional_columns() {
        // 必填只有三项；其余缺省取最轻处置（且与"允不允许"无关）
        let c = Manifest::parse(
            r#"{"capability":"a.b","provider":"p","verbs":["x"]}"#,
            Path::new("x"),
        )
        .unwrap();
        assert_eq!(c.risk, Risk::Low);
        assert_eq!(c.undo, Undo::Never);
        assert_eq!(c.confirm, Confirm::Never);
        assert_eq!(c.sandbox, "none");
    }

    #[test]
    fn rejects_every_malformed_shape() {
        // 非 JSON
        assert!(Manifest::parse("{", Path::new("x")).is_err());
        // 缺 capability
        assert!(Manifest::parse(r#"{"provider":"p","verbs":["a"]}"#, Path::new("x")).is_err());
        // 缺 provider
        assert!(Manifest::parse(r#"{"capability":"c","verbs":["a"]}"#, Path::new("x")).is_err());
        // verbs 缺失
        assert!(Manifest::parse(r#"{"capability":"c","provider":"p"}"#, Path::new("x")).is_err());
        // verbs 空
        assert!(Manifest::parse(
            r#"{"capability":"c","provider":"p","verbs":[]}"#,
            Path::new("x")
        )
        .is_err());
        // 非法风险分级
        assert!(Manifest::parse(
            r#"{"capability":"c","provider":"p","verbs":["a"],"risk":"critical"}"#,
            Path::new("x")
        )
        .is_err());
        // 非法撤销策略
        assert!(Manifest::parse(
            r#"{"capability":"c","provider":"p","verbs":["a"],"undo":"sometimes"}"#,
            Path::new("x")
        )
        .is_err());
        // 非法确认策略
        assert!(Manifest::parse(
            r#"{"capability":"c","provider":"p","verbs":["a"],"confirm":"maybe"}"#,
            Path::new("x")
        )
        .is_err());
    }

    #[test]
    fn loads_a_directory_deterministically() {
        let d = tmp("dir");
        std::fs::write(
            d.join("b.json"),
            r#"{"capability":"job.start","provider":"job","verbs":["start"]}"#,
        )
        .unwrap();
        std::fs::write(
            d.join("a.json"),
            r#"{"capability":"notice.mute","provider":"backlight","verbs":["get","set"]}"#,
        )
        .unwrap();
        // 非 .json 一律忽略
        std::fs::write(d.join("README.md"), "ignore me").unwrap();
        let m = Manifest::load_dir(&d).unwrap();
        assert_eq!(m.names(), vec!["job.start", "notice.mute"]);
        assert!(m.lookup("job.start").is_some());
        assert!(m.lookup("nope").is_none());
        assert!(!m.is_empty());
    }

    #[test]
    fn refuses_a_directory_that_is_not_there() {
        let m = Manifest::load_dir(Path::new("/definitely/not/here"));
        assert!(m.is_err());
        assert!(m.unwrap_err().contains("ManifestDirFail"));
    }

    #[test]
    fn an_empty_directory_is_an_empty_manifest_not_an_error() {
        let d = tmp("empty");
        let m = Manifest::load_dir(&d).unwrap();
        assert!(m.is_empty());
        assert!(m.names().is_empty());
    }
}
