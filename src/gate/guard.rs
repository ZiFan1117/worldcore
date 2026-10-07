//! 静态防线（`M05` 的一半）—— **法律与真相的存放处，不得对被管者开放写权限**。
//!
//! ## 为什么"不可绕过"不能只靠代码里的 if
//!
//! 门禁的第一层是**决策**（`crate::gate`：这个能力允不允许、要不要加摩擦）。
//! 但只要规则本身能被改，决策层就是纸糊的：
//! 被管者只要把 `policy.json` 改成"什么都允许"，下一次启动起门禁就不存在了。
//! 同理，账本是唯一真相——**能被谁直写，真相就归谁**。
//!
//! 所以本项目把"不可绕过"拆成**两道墙**（`WC-SRS-001` REQ-F-015 / AC-05）：
//!
//! | 墙 | 在哪 | 挡什么 | 本模块？ |
//! |---|---|---|---|
//! | **静态墙** | 文件系统权限 | 被管者改规则、绕核心直写账本、替换整个文件 | ✅ 本模块 |
//! | **动态墙** | 唯一写入口的咽喉 | 进程内绕过检查改世界 | ❌ 见 `crate::World::commit` |
//!
//! ## 本模块的判据（刻意保守、可实测）
//!
//! 对"法律文件"（`policy.json`）与"真相文件"（账本）各查两件事：
//!
//! 1. **文件本身**不得对 group / other 可写（`mode & 0o022 == 0`）；
//! 2. **所在目录**不得对 group / other 可写。
//!
//! 第 2 条不是多余：文件权限挡不住"把整个文件删掉再放一个新的"——
//! 而只要目录可写，这一步就做得到。**目录权限才是"能不能换掉这条法律"的真正答案。**
//!
//! 检查失败即**拒绝启动**（fail loud）：带病运行比不运行更危险——
//! 一个"以为自己有门禁"的世界，比一个明确拒绝启动的世界危险得多。
//!
//! ⚠️ **已知局限（不假装满足）**：
//! - 本模块只看 **mode 位**，不看**属主**。若被管者恰好就是文件属主，mode 再严也没用。
//!   跨 uid 的真实隔离由 `WC-CON01-001` 的原型在 VM 上实测（root vs `agent` 用户）；
//! - 不做 **Landlock / seccomp** 自缚。那属于"第二版"：内核能力经系统调用使用，
//!   需评估可移植性与内核版本，见 `WC-SMP`/S2 设计（【TBD】）；
//! - 非 Unix 平台**跳过**这些检查（`cfg(unix)`）。本项目构建与运行都在 Linux VM 内，
//!   跳过是为了让代码在别的平台上仍能编译，不构成对 Unix 行为的放宽。

use std::path::Path;

/// 断言某条路径"不被 group / other 可写"，否则返回**拒绝启动**的理由。
///
/// `role` 用于把错误说成人话（如"门禁策略（法律）"、"账本（真相）"）。
pub fn assert_not_other_writable(path: &Path, role: &str) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;

        // ① 拒绝符号链接（2026-09-26 补，见 WC-RV-R2-001 FIND-04 / S-05）
        //
        // 为什么：`fs::metadata` 会**跟随**符号链接，于是"检查的是 A、用的是 B"
        // 成为可能——把政策文件换成指向别处的软链，静态墙照样点头。
        // 用 `symlink_metadata`（lstat 语义）直接判定路径本身是不是链接。
        assert_not_symlink(path, role)?;

        let meta = std::fs::metadata(path)
            .map_err(|e| format!("{role}：无法读取 {} 的权限：{e}", path.display()))?;
        let mode = meta.permissions().mode() & 0o777;
        if mode & 0o022 != 0 {
            return Err(format!(
                "{role} 不可绕过检查未通过：{} 的权限为 {mode:o}，对 group/other 可写。\n\
                 \x20 为什么这算致命：规则与真相的存放处若能被人改写，门禁就只是纸糊的——\n\
                 \x20 对方只要换成『什么都允许』再从下次启动生效即可。\n\
                 \x20 处置：chmod go-w {}（必要时同时收紧其所在目录）",
                path.display(),
                path.display()
            ));
        }

        if let Some(dir) = parent_dir(path) {
            if let Ok(dmeta) = std::fs::metadata(dir) {
                let dmode = dmeta.permissions().mode() & 0o777;
                if dmode & 0o022 != 0 {
                    return Err(format!(
                        "{role} 不可绕过检查未通过：所在目录 {} 的权限为 {dmode:o}，对 group/other 可写。\n\
                         \x20 为什么这算致命：**文件权限挡不住『删掉再放一个新的』**——\n\
                         \x20 目录可写就等于这条法律可以被整体换掉。\n\
                         \x20 处置：chmod go-w {}",
                        dir.display(),
                        dir.display()
                    ));
                }
            }
        }
        Ok(())
    }
    #[cfg(not(unix))]
    {
        // 非 Unix 无 POSIX 权限位；此处不做判断，也不假装做了。
        let _ = (path, role);
        Ok(())
    }
}

/// 从文件创建之后立即复核（用于账本这类"可能刚被创建"的文件）。
/// 拒绝**符号链接**的法律/真相文件。
///
/// `fs::metadata` 跟随链接，而"规则所在之处"必须是**那个文件本身**。
/// 一个指向别处的软链足以让"静态墙检查的"与"运行时真正读的"不是同一个东西
/// （`WC-RV-R2-001` FIND-04 / S-05）。故用 `symlink_metadata`（lstat）判定。
pub fn assert_not_symlink(path: &Path, role: &str) -> Result<(), String> {
    match std::fs::symlink_metadata(path) {
        Ok(m) if m.file_type().is_symlink() => Err(format!(
            "{role} 不可绕过检查未通过：{} 是一个**符号链接**。\n\
             \x20 为什么这算致命：权限检查会跟随链接看到目标文件，\n\
             \x20 于是『检查的』与『真正读的』可能不是同一个东西——静态墙被绕过。\n\
             \x20 处置：改为真实文件（把目标内容放到该路径）",
            path.display()
        )),
        Ok(_) => Ok(()),
        Err(e) => Err(format!(
            "{role}：无法判定 {} 是否为链接：{e}",
            path.display()
        )),
    }
}

/// **属主断言**：该路径必须属于 `expected_uid`。
///
/// 为什么需要它（`WC-RV-R2-001` 假设 **A-05** / FIND-04）：
/// 静态墙只看 **mode 位**，对**属主**无效——若被管者恰是法律或账本的属主，
/// 它自己 `chmod u+w` 就能写，mode 再严也没用。
/// 此前这条只写在部署文档里（"属主须为核心 uid"），**代码零强制**。
/// 现在可以由部署方显式断言：`--owner-uid <uid>`。
///
/// ⚠️ 它是**部署方的自证工具**，不是自动安全机制：没人传 `expected_uid` 时它不会运行
/// （因为没有"被管者的 uid"这一信息可用）。这一点必须说清，不得当成默认可绕过。
pub fn assert_owned_by(path: &Path, expected_uid: u32, role: &str) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let meta = std::fs::metadata(path)
            .map_err(|e| format!("{role}：无法读取 {} 的属主：{e}", path.display()))?;
        let uid = meta.uid();
        if uid != expected_uid {
            return Err(format!(
                "{role} 属主断言未通过：{} 的属主 uid={uid}，期望 {expected_uid}。\n\
                 \x20 为什么这算致命：静态墙只看 mode 位——**属主永远能 chmod u+w 后写它**。\n\
                 \x20 故法律与真相的属主必须是核心 uid（部署要求，见 WC-HLD-001 §7.3）。",
                path.display()
            ));
        }
        Ok(())
    }
    #[cfg(not(unix))]
    {
        let _ = (path, expected_uid, role);
        Ok(())
    }
}

pub fn assert_after_create(path: &Path, role: &str) -> Result<(), String> {
    assert_not_other_writable(path, role)
}

/// 取一条路径"所在目录"，用于「目录不得对 group/other 可写」这一步。
///
/// ⚠️ **`D-31`（实测缺陷，2026-09-27 修复）**：相对路径（如默认调用形态里的
/// `ledger.jsonl`）其 `parent()` 是**空串**。旧写法是
/// `path.parent().filter(|d| !d.as_os_str().is_empty())`，于是空串被过滤成 `None`、
/// 目录检查**被静默跳过**——而紧随其后的 `.` 回退分支因此是**死代码**。
/// 后果：**默认调用形态（不带任何路径参数）缺失了这一条防线**，而本模块文档恰恰把
/// 目录权限写成"能不能换掉这条法律的真正答案"。
///
/// 实测对照（VM，`/srv/b6x` 由 0755 改 0777，账本已有一条事件）：
/// - 修复前 `world-core check`（默认相对路径）→ `rc=0 READY`（**漏检**）；
///   显式绝对路径 `--ledger /srv/b6x/ledger.jsonl ... check` → `rc=2`（正确拒启）；
/// - 修复后**两种形态都是 `rc=2`**，回归用例见本文件 `mod unit`。
fn parent_dir(path: &Path) -> Option<&Path> {
    match path.parent() {
        Some(d) if d.as_os_str().is_empty() => Some(Path::new(".")),
        other => other,
    }
}

#[cfg(test)]
mod unit {
    use super::*;

    #[cfg(unix)]
    #[test]
    fn refuses_group_or_other_writable_file() {
        use std::io::Write as _;
        use std::os::unix::fs::PermissionsExt;

        let dir = std::env::temp_dir().join(format!("wc-guard-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o700)).unwrap();
        let f = dir.join("law.json");
        let mut fh = std::fs::File::create(&f).unwrap();
        fh.write_all(b"{}").unwrap();
        drop(fh);

        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o644)).unwrap();
        assert!(
            assert_not_other_writable(&f, "法律").is_ok(),
            "0644 应当通过"
        );

        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o666)).unwrap();
        let e = assert_not_other_writable(&f, "法律").unwrap_err();
        assert!(e.contains("对 group/other 可写"), "实得: {e}");

        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o646)).unwrap();
        assert!(
            assert_not_other_writable(&f, "法律").is_err(),
            "other 可写也应被拒"
        );

        // 目录可写 → 也必须拒绝（否则可整体换掉文件）
        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o644)).unwrap();
        std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o777)).unwrap();
        let e = assert_not_other_writable(&f, "法律").unwrap_err();
        assert!(e.contains("所在目录"), "实得: {e}");

        std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o700)).unwrap();
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// `D-31` 回归：相对路径必须**查当前目录**，不得被静默跳过。
    ///
    /// 为什么必须有这一条：上面那个用例只用**绝对路径**（`temp_dir().join(..)`），
    /// 而默认调用形态用的是**相对路径** —— **一个从不失败的检查不是检查，是装饰**：
    /// 旧代码在默认形态下漏检，测试却全绿。
    #[test]
    fn relative_path_maps_to_current_dir() {
        assert_eq!(parent_dir(Path::new("ledger.jsonl")), Some(Path::new(".")));
        assert_eq!(
            parent_dir(Path::new("./ledger.jsonl")),
            Some(Path::new("."))
        );
        assert_eq!(parent_dir(Path::new("a/b.jsonl")), Some(Path::new("a")));
        assert_eq!(parent_dir(Path::new("/a/b")), Some(Path::new("/a")));
        assert_eq!(parent_dir(Path::new("/")), None);
        // 旧写法（错误实现）的等价形式：空 parent 会被过滤掉 —— 显式钉住它不再是行为。
        assert!(
            parent_dir(Path::new("ledger.jsonl")).is_some(),
            "相对路径的所在目录必须是 `.`，不能是 None（D-31）"
        );
    }
}
