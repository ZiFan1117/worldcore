use crate::carrier::provider::Provider;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

/// 背光执行器：**真设备**（sysfs）。
///
/// 它在无背光设备的机器上**不假装成功**：明确报"找不到设备"，
/// 而不是返回一个编造的亮度值。
pub struct Backlight {
    /// 背光设备根目录（默认 `/sys/class/backlight`；测试可换成临时目录）。
    pub root: PathBuf,
}

impl Default for Backlight {
    fn default() -> Self {
        Backlight {
            root: PathBuf::from("/sys/class/backlight"),
        }
    }
}

impl Backlight {
    /// 找一个可用的背光设备目录（按名字有序，故结果确定）。
    fn device(&self) -> Result<PathBuf, String> {
        let mut names: Vec<PathBuf> = std::fs::read_dir(&self.root)
            .map_err(|e| {
                format!(
                    "ext.world.Carrier.NoDevice: 读不了背光设备目录 {}：{e}",
                    self.root.display()
                )
            })?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.join("max_brightness").is_file())
            .collect();
        names.sort();
        names.into_iter().next().ok_or_else(|| {
            format!(
                "ext.world.Carrier.NoDevice: {} 下没有可用背光设备（缺 max_brightness）",
                self.root.display()
            )
        })
    }

    fn read_u64(path: &Path) -> Result<u64, String> {
        let raw = std::fs::read_to_string(path)
            .map_err(|e| format!("ext.world.Carrier.DeviceReadFail: {}：{e}", path.display()))?;
        raw.trim().parse::<u64>().map_err(|e| {
            format!(
                "ext.world.Carrier.DeviceReadFail: {} 不是整数：{e}",
                path.display()
            )
        })
    }

    /// 把"百分比"翻译成设备刻度（**单位在参数里，不靠猜**）。
    ///
    /// 口径：`scale` 只允许 `raw`（直接给设备值）或 `percent`（0–100）；
    /// 未给时按 `raw`——**不猜**，因为"3"到底是 3% 还是第 3 档是两件完全不同的事。
    pub(crate) fn to_raw(level: u64, max: u64, params: &Value) -> Result<u64, String> {
        let scale = params.get("scale").and_then(Value::as_str).unwrap_or("raw");
        match scale {
            "raw" => {
                if level > max {
                    return Err(format!(
                        "ext.world.Carrier.OutOfRange: 亮度 {level} 超出设备上限 {max}（scale=raw）"
                    ));
                }
                Ok(level)
            }
            "percent" => {
                if level > 100 {
                    return Err(format!(
                        "ext.world.Carrier.OutOfRange: 百分比 {level} 超出 0–100（scale=percent）"
                    ));
                }
                Ok((level * max + 50) / 100)
            }
            other => Err(format!(
                "ext.world.Carrier.BadParam: scale=`{other}` 非法（只允许 raw/percent）"
            )),
        }
    }
}

impl Provider for Backlight {
    fn name(&self) -> &'static str {
        "backlight"
    }

    /// **语义层的名字**（**不是**设备名）：它在本体 `_interfaces` 里叫 `notice.mute`。
    /// 设备词（"怎么实现"）写在 [`Provider::name`] 那一栏（`backlight`）。
    fn capabilities(&self) -> Vec<&'static str> {
        vec!["notice.mute"]
    }

    fn call(&self, verb: &str, params: &Value) -> Result<Value, String> {
        let dev = self.device()?;
        let max = Self::read_u64(&dev.join("max_brightness"))?;
        match verb {
            "get" => {
                let cur = Self::read_u64(&dev.join("brightness"))?;
                Ok(json!({
                    "device": dev.file_name().and_then(|s| s.to_str()).unwrap_or("?"),
                    "level": cur,
                    "max": max,
                    "percent": (cur * 100 + max / 2).checked_div(max).unwrap_or(0),
                }))
            }
            "set" => {
                let level = params.get("level").and_then(Value::as_u64).ok_or_else(|| {
                    "ext.world.Carrier.BadParam: set 需要整数参数 level".to_string()
                })?;
                let raw = Self::to_raw(level, max, params)?;
                std::fs::write(dev.join("brightness"), format!("{raw}\n")).map_err(|e| {
                    format!(
                        "ext.world.Carrier.DeviceWriteFail: 写 {} 失败：{e}",
                        dev.join("brightness").display()
                    )
                })?;
                Ok(json!({
                    "device": dev.file_name().and_then(|s| s.to_str()).unwrap_or("?"),
                    "level": raw,
                    "max": max,
                }))
            }
            other => Err(format!(
                "ext.world.Carrier.UnknownVerb: 背光执行器不认识动词 `{other}`"
            )),
        }
    }
}
