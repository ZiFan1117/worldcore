use crate::carrier::provider::Provider;
use serde_json::{json, Value};
use std::path::PathBuf;
use std::process::Command;

/// 包管理执行器：调包管理器；**高危动词前先做载体撤销点**。
pub struct Package {
    /// 包管理器可执行文件（默认 `pacman`；测试可换成任意命令）。
    pub program: String,
    /// 载体撤销点目录（本轮载体撤销的落点）。
    pub undo_dir: PathBuf,
}

impl Default for Package {
    fn default() -> Self {
        Package {
            program: "pacman".to_string(),
            undo_dir: PathBuf::from("/run/undo"),
        }
    }
}

impl Package {
    /// 记一份"包清单"到撤销点目录（**先用可判定的最小动作**：
    /// 记下当前已装包清单，将来可据此判断"多装了哪些"）。
    ///
    /// 为什么不做全盘快照：载体撤销是工程兜底，**不是世界回滚**；
    /// 这里刻意只做"可判定、可复现、可解释"的那一小步，不假装有全盘原子撤销。
    fn mark(&self, request_id: &str) -> Result<Value, String> {
        std::fs::create_dir_all(&self.undo_dir).map_err(|e| {
            format!(
                "ext.world.Carrier.UndoFail: 建不了撤销点目录 {}：{e}",
                self.undo_dir.display()
            )
        })?;
        let path = self.undo_dir.join(format!("pre-{request_id}.list"));
        let out = Command::new(&self.program)
            .arg("-Qq")
            .output()
            .map_err(|e| {
                format!(
                    "ext.world.Carrier.UndoFail: 撤销点无法取得包清单（{}）：{e}",
                    self.program
                )
            })?;
        std::fs::write(&path, &out.stdout).map_err(|e| {
            format!(
                "ext.world.Carrier.UndoFail: 写不了撤销点 {}：{e}",
                path.display()
            )
        })?;
        let n = String::from_utf8_lossy(&out.stdout).lines().count();
        Ok(json!({
            "kind": "carrier-undo",
            "path": path.display().to_string(),
            "packages": n,
        }))
    }
}

impl Provider for Package {
    fn name(&self) -> &'static str {
        "package"
    }

    /// **语义层的名字**（**不是**设备名）：它在本体 `_interfaces` 里叫 `ledger.compact`。
    /// 设备词（"怎么实现"）写在 [`Provider::name`] 那一栏（`package`）。
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["ledger.compact"]
    }

    /// 载体撤销点：记下当前包清单。做不到就报错（**不假装撤得回去**）。
    fn undo_mark(&self, request_id: &str) -> Result<Value, String> {
        self.mark(request_id)
    }

    fn call(&self, verb: &str, params: &Value) -> Result<Value, String> {
        match verb {
            "list" => {
                let out = Command::new(&self.program)
                    .arg("-Qq")
                    .output()
                    .map_err(|e| format!("ext.world.Carrier.ProviderFailed: {e}"))?;
                if !out.status.success() {
                    return Err(format!(
                        "ext.world.Carrier.ProviderFailed: {} -Qq 退出码 {:?}",
                        self.program,
                        out.status.code()
                    ));
                }
                let list: Vec<String> = String::from_utf8_lossy(&out.stdout)
                    .lines()
                    .map(str::to_string)
                    .collect();
                Ok(json!({ "count": list.len(), "packages": list }))
            }
            "install" => {
                let pkg = params
                    .get("package")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        "ext.world.Carrier.BadParam: install 需要参数 package".to_string()
                    })?;
                let out = Command::new(&self.program)
                    .arg("-S")
                    .arg("--noconfirm")
                    .arg(pkg)
                    .output()
                    .map_err(|e| format!("ext.world.Carrier.ProviderFailed: {e}"))?;
                let code = out.status.code().unwrap_or(-1) as i64;
                let detail = json!({
                    "package": pkg,
                    "stdout_tail": tail(&out.stdout, 8),
                    "stderr_tail": tail(&out.stderr, 8),
                });
                if out.status.success() {
                    Ok(detail)
                } else {
                    Err(format!(
                        "ext.world.Carrier.ProviderFailed: 装包失败（退出码 {code}）：{}",
                        tail(&out.stderr, 3).join(" | ")
                    ))
                }
            }
            other => Err(format!(
                "ext.world.Carrier.UnknownVerb: 包执行器不认识动词 `{other}`"
            )),
        }
    }
}

fn tail(raw: &[u8], n: usize) -> Vec<String> {
    let text = String::from_utf8_lossy(raw);
    let lines: Vec<&str> = text.lines().collect();
    let start = lines.len().saturating_sub(n);
    lines[start..].iter().map(|s| s.to_string()).collect()
}
