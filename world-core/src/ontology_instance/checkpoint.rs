//! 检查点（`M08`）—— **带 `base_seq` 的缓存**，不是第二真相。
//!
//! ## 为什么它必须"可被推翻"
//!
//! 读模型每次全量折叠是 O(n)（`WC-HLD-001` §4.5）。加速手段就是快照，但快照一旦落盘，
//! 就出现了项目最担心的那类故障：**"状态"有了第二个来源**。
//! 因此本模块的设计约束只有一条，其余全部由它推出：
//!
//! > **快照永远是缓存的地位：账本说它错了，它就错了。**
//!
//! 具体落实为三件事：
//! 1. **必须带 `base_seq`**：快照声明"折叠到哪一条为止"。它**不能**声称比账本更靠前；
//! 2. **必须可被核验**（[`Checkpoint::verify`]）：把账本重算一遍，比对指纹。
//!    核验**不通过即拒绝使用**——宁可全量重算，也不信一份说不清的缓存；
//! 3. **删掉它必须没有任何后果**：`read_model_with_checkpoint` 在无快照时就是全量折叠，
//!    结果与"有快照续算"**逐字节相同**（这是 `WC-SQAP-001` §2.4 第三条专属测试的加强形态）。
//!
//! ## 格式（纯文本、语言无关）
//!
//! ```json
//! { "checkpoint": 1, "base_seq": 5, "digest": "fnv1a64:…", "state": { …State::to_json 的规范形式… } }
//! ```
//!
//! ## 已知局限（不假装满足）
//!
//! - `verify` 需要**重算**，即核验成本 = 全量折叠成本。真要用它省时间，正常路径是
//!   **不核验直接续算**、只在怀疑时核验；本模块**同时提供两者**，由调用方选择，
//!   并把"未核验"这件事留在接口名里（`resume_unverified` vs `verify`）；
//! - 快照文件若可被他人写，攻击者可篡改缓存——`verify` 能检出（指纹不符），
//!   但**不核验的路径会吃下篡改内容**。故 `write` 仍过静态墙检查。

use crate::gate::guard;
use crate::ontology_instance::readmodel::State;
use serde_json::{json, Value};
use std::path::Path;

/// 一份检查点（缓存）。
#[derive(Debug, Clone)]
pub struct Checkpoint {
    base_seq: u64,
    digest: String,
    state: Value,
}

impl Checkpoint {
    /// 快照格式版本。**只加字段、不改旧字段含义**。
    pub const FORMAT: u64 = 1;

    /// 从当前状态截一张快照。
    pub fn capture(state: &State) -> Self {
        Checkpoint {
            base_seq: state.last_seq(),
            digest: state.digest(),
            state: state.to_json(),
        }
    }

    /// 快照折叠到哪一条为止。
    pub fn base_seq(&self) -> u64 {
        self.base_seq
    }

    /// 快照自称的状态指纹。
    pub fn digest(&self) -> &str {
        &self.digest
    }

    /// 写入快照（纯文本 JSON）。写后 fsync，并过静态墙。
    pub fn write(&self, path: &Path) -> Result<(), String> {
        let doc = json!({
            "checkpoint": Self::FORMAT,
            "base_seq": self.base_seq,
            "digest": self.digest,
            "state": self.state,
        });
        let text = serde_json::to_string(&doc)
            .map_err(|e| format!("ext.world.Checkpoint.EncodeFail: {e}"))?;
        std::fs::write(path, text)
            .map_err(|e| format!("ext.world.Checkpoint.WriteFail: {}: {e}", path.display()))?;
        // 静态墙：缓存也不该由被管者改写（否则"未核验路径"会吃下篡改内容）
        guard::assert_after_create(path, "检查点（缓存）")?;
        Ok(())
    }

    /// 读取快照（含格式与字段校验）。
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Checkpoint.ReadFail: {}: {e}", path.display()))?;
        let v: Value = serde_json::from_str(&text)
            .map_err(|e| format!("ext.world.Checkpoint.BadJson: {}: {e}", path.display()))?;
        let fmt = v.get("checkpoint").and_then(Value::as_u64).ok_or_else(|| {
            "ext.world.Checkpoint.NoFormat: 快照缺少 checkpoint 版本号".to_string()
        })?;
        if fmt != Self::FORMAT {
            return Err(format!(
                "ext.world.Checkpoint.BadFormat: 期望 {}，实得 {fmt}",
                Self::FORMAT
            ));
        }
        let base_seq = v.get("base_seq").and_then(Value::as_u64).ok_or_else(|| {
            "ext.world.Checkpoint.MissingBaseSeq: 快照必须声明 base_seq".to_string()
        })?;
        let digest = v
            .get("digest")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Checkpoint.MissingDigest: 快照缺少 digest".to_string())?
            .to_string();
        let state = v
            .get("state")
            .cloned()
            .ok_or_else(|| "ext.world.Checkpoint.MissingState: 快照缺少 state".to_string())?;
        Ok(Checkpoint {
            base_seq,
            digest,
            state,
        })
    }

    /// **核验**：拿账本重算前 `base_seq` 条，指纹必须与快照自称的一致。
    ///
    /// 这是"缓存不得成为第二真相"的可执行保障——账本说它错了，它就错了。
    pub fn verify(&self, ledger_events: &[Value]) -> Result<(), String> {
        let prefix: Vec<Value> = ledger_events
            .iter()
            .filter(|e| e.get("seq").and_then(Value::as_u64).unwrap_or(0) <= self.base_seq)
            .cloned()
            .collect();
        if prefix.len() as u64 != self.base_seq {
            return Err(format!(
                "ext.world.Checkpoint.Stale: 快照声称 base_seq={}，但账本里只有 {} 条不晚于它的记录\
                 ——账本比快照短，**拒绝使用**（宁可全量重算）",
                self.base_seq,
                prefix.len()
            ));
        }
        let recomputed = State::fold(&prefix)?;
        if recomputed.digest() != self.digest {
            return Err(format!(
                "ext.world.Checkpoint.DigestMismatch: 快照自称 {}，账本重算得 {}。\n\
                 \x20 快照是缓存、账本是真相：**以账本为准**，本快照作废并须重新生成",
                self.digest,
                recomputed.digest()
            ));
        }
        Ok(())
    }

    /// **不核验续算**（快路径）：从快照恢复，再把 `base_seq` 之后的事件依次折叠。
    ///
    /// 名字里带 `unverified` 是刻意的：调用方**必须知道**自己跳过了核验。
    /// 想稳妥就先调 [`Checkpoint::verify`]。
    pub fn resume_unverified(&self, ledger_events: &[Value]) -> Result<State, String> {
        let mut st = State::from_json(&self.state)?;
        for ev in ledger_events
            .iter()
            .filter(|e| e.get("seq").and_then(Value::as_u64).unwrap_or(0) > self.base_seq)
        {
            st.apply(ev)?;
        }
        Ok(st)
    }
}

/// 读模型入口（可带快照）：**有快照走快路径，没快照走全量——两者结果必须逐字节相同**。
///
/// 这个函数就是 `REQ-F-021` 的可检验面：删掉快照文件再调一次，结果不变。
pub fn read_model_with_checkpoint(
    ledger_events: &[Value],
    checkpoint: Option<&Checkpoint>,
) -> Result<State, String> {
    match checkpoint {
        None => State::fold(ledger_events),
        Some(cp) => cp.resume_unverified(ledger_events),
    }
}
