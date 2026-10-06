//! **写侧的身份与权限边界**（书 §4.5）—— 以被管者身份运行，对账本与规则都没有写权限。
//!
//! ## 书 §4.5 逐字（`docs/理论/语义世界-理论书-第一版-合订.md:601`）
//!
//! > 写侧这只手跑在自己的进程里，以被管者身份运行，对账本与规则都没有写权限。
//! > 它要写世界，只能经通道提交请求，走的是和别的任何主体完全相同的那条路：校验、过闸、落笔。
//! > 这一点是"唯一入口"能不能成立的前提。手如果自己有写权限，世界就有了第二个权威，
//! > 两处都能决定"这件事允不允许"，两处的结论迟早不同。
//!
//! ## 本模块回答的是哪个问题（**它不回答"我是谁"**）
//!
//! | 问题 | 谁回答 |
//! |---|---|
//! | "本进程现在到底是谁" | **部署**：一个套接字一个身份（`src/bus/mod.rs` 的 `bind`，权限即身份）、`runuser`／systemd `User=`；跨 uid 实测见 `tools/con01-no-bypass.sh` 与 `tools/carrier_acceptance.sh` 的 C-09 |
//! | "**对这个被管者身份**，账本与规则写不写得到" | **本模块**（[`assert_managed_cannot_write`]） |
//!
//! 把这两件事分开是刻意的：写侧**不能靠自证身份**来证明边界（自称谁都不算数，
//! 与 `src/carrier/mod.rs:75` 的"请求去掉身份"同一纪律）；能查的是**文件系统上的事实**。
//!
//! ## 与 `src/gate/guard.rs` 的关系：**同一纪律，两个提问，刻意不复用**
//!
//! `src/gate/guard.rs:43` 的 `assert_not_other_writable` 问的是"**这条法律／真相是否对被管者开放**"
//! （内核进程启动时判，答"开放"即拒绝启动）；本模块问的是"**对这个被管者身份**，它写不写得到"
//! （写侧自查，答"写得到"即不许动手）。两条判据在 mode 位上同源
//! （`mode & 0o022 == 0`、所在目录同判、拒符号链接），方向却相反：
//! `guard` 用 `assert_owned_by`（`src/gate/guard.rs:127`）要求属主**是**核心 uid，
//! 本模块要求属主**不是**被管者 uid（`src/gate/guard.rs:137` 逐字：「**属主永远能 chmod u+w 后写它**」）。
//!
//! ⚠️ **为什么不 `use crate::gate::guard`**：`M05 → M10` 已有一条真实 import 边
//! （`src/gate/mod.rs:32` 读载体清单），反向再连即**成环**，`WC-ATOM-001` §二 A-4 不许，
//! `tools/module_graph.py` 判据② 会红。故此处**重述判据而不复用**。
//! 这不是放宽：**两侧判据都成立**，才谈得上"写侧写不到法律与真相"。

use std::path::Path;

/// 断言"**以被管者身份 `managed_uid` 运行的这个进程**，写不到 `path`"。
///
/// 四条判据（任一不成立即返回 `Err`，并说清为什么这算致命）：
///
/// 1. `path` **不得是符号链接**：否则"检查的"与"真正用的"可能不是同一个东西；
/// 2. **属主不得是被管者**：属主永远能 `chmod u+w` 后写它，mode 再严也没用；
/// 3. 文件本身 **不得对 group/other 可写**（`mode & 0o022 == 0`）；
/// 4. **所在目录**不得对 group/other 可写、其属主也不得是被管者——
///    文件权限挡不住"删掉再放一个新的"，**目录才是"能不能换掉这条法律"的真正答案**。
///
/// `role` 把错误说成人话（如"账本（真相）"、"门禁策略（法律）"）。
pub fn assert_managed_cannot_write(
    path: &Path,
    role: &str,
    managed_uid: u32,
) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::{MetadataExt, PermissionsExt};

        let link = std::fs::symlink_metadata(path).map_err(|e| {
            format!(
                "ext.world.Carrier.BoundaryUnknown: {role}：读不到 {} 的元数据：{e}",
                path.display()
            )
        })?;
        if link.file_type().is_symlink() {
            return Err(format!(
                "ext.world.Carrier.BoundarySymlink: {role} 边界未立住：{} 是一个**符号链接**。\n\
                 \x20 为什么这算致命：权限检查会跟随链接看到目标文件，\
                 于是『检查的』与『真正读写的』可能不是同一个东西。\n\
                 \x20 处置：改成真实文件（把目标内容放到该路径）",
                path.display()
            ));
        }

        let meta = std::fs::metadata(path).map_err(|e| {
            format!(
                "ext.world.Carrier.BoundaryUnknown: {role}：读不到 {} 的权限：{e}",
                path.display()
            )
        })?;
        if meta.uid() == managed_uid {
            return Err(format!(
                "ext.world.Carrier.BoundaryOwned: {role} 边界未立住：{} 的属主就是被管者\
                 （uid={managed_uid}）。\n\
                 \x20 为什么这算致命：**属主永远能 chmod u+w 后写它**（`src/gate/guard.rs:137` 同一条口径），\n\
                 \x20 于是 mode 位再严也挡不住——法律与真相的属主必须是核心 uid。\n\
                 \x20 处置：把属主改回核心 uid（如 `chown root {}`），写侧以另一个身份运行",
                path.display(),
                path.display()
            ));
        }
        let mode = meta.permissions().mode() & 0o777;
        if mode & 0o022 != 0 {
            return Err(format!(
                "ext.world.Carrier.BoundaryWritable: {role} 边界未立住：{} 的权限为 {mode:o}，\
                 对 group/other 可写 ⇒ 写侧（uid={managed_uid}）写得到它。\n\
                 \x20 处置：chmod go-w {}",
                path.display(),
                path.display()
            ));
        }

        if let Some(dir) = parent_dir(path) {
            let dmeta = std::fs::metadata(dir).map_err(|e| {
                format!(
                    "ext.world.Carrier.BoundaryUnknown: {role}：读不到所在目录 {} 的权限：{e}",
                    dir.display()
                )
            })?;
            if dmeta.uid() == managed_uid {
                return Err(format!(
                    "ext.world.Carrier.BoundaryDirOwned: {role} 边界未立住：所在目录 {} 的属主\
                     就是被管者（uid={managed_uid}）。\n\
                     \x20 为什么这算致命：目录属主改得了目录权限，就能**删掉再放一个新的**——\n\
                     \x20 文件权限挡不住这一步。\n\
                     \x20 处置：目录属主改回核心 uid",
                    dir.display()
                ));
            }
            let dmode = dmeta.permissions().mode() & 0o777;
            if dmode & 0o022 != 0 {
                return Err(format!(
                    "ext.world.Carrier.BoundaryDirWritable: {role} 边界未立住：所在目录 {} 的权限为\
                     {dmode:o}，对 group/other 可写 ⇒ 法律／真相可以被整体换掉。\n\
                     \x20 处置：chmod go-w {}",
                    dir.display(),
                    dir.display()
                ));
            }
        }
        Ok(())
    }
    #[cfg(not(unix))]
    {
        // 非 Unix 没有 POSIX 权限位 ⇒ **"写不到"这件事不成立**。
        // 这里刻意与 `src/gate/guard.rs:86-91` 的"非 Unix 跳过"不同：guard 的调用方
        // 在别的平台上仍要能启动，而本函数的**全部意义**就是那句断言；
        // 判不了就按不通过处置（"未能校验"不等于"校验通过"）。
        Err(format!(
            "ext.world.Carrier.BoundaryUnsupported: {role} 边界无法判定：本平台没有 POSIX 权限位\
             （{}；被管者 uid={managed_uid}）——故『写不到』不成立，按不通过处置",
            path.display()
        ))
    }
}

/// 取一条路径"所在目录"，用于「目录不得对 group/other 可写」这一步。
///
/// ⚠️ 与 `src/gate/guard.rs:168-173` 同一处 `D-31` 修正：相对路径（默认调用形态里的
/// `ledger.jsonl`）其 `parent()` 是**空串**，若过滤掉就**静默跳过**目录检查——
/// 而目录权限恰恰是"能不能换掉这条法律"的真正答案。空 parent ⇒ 按 `.`（当前目录）判。
fn parent_dir(path: &Path) -> Option<&Path> {
    match path.parent() {
        Some(d) if d.as_os_str().is_empty() => Some(Path::new(".")),
        other => other,
    }
}

#[cfg(test)]
mod unit {
    use super::*;

    /// 测试用的"被管者 uid"：一个**不是**本进程属主的固定值（nobody）。
    const MANAGED: u32 = 65534;

    fn tmp(tag: &str) -> std::path::PathBuf {
        use std::time::{SystemTime, UNIX_EPOCH};
        let n = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let d = std::env::temp_dir().join(format!("wc-boundary-{tag}-{n}"));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o700)).unwrap();
        }
        d
    }

    /// 本进程 uid（不引 libc：读 `/proc/self/status`，与 `tests/cli.rs:23-37` 同法）。
    #[cfg(unix)]
    fn this_uid() -> u32 {
        let s = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
        for line in s.lines() {
            if let Some(rest) = line.strip_prefix("Uid:") {
                if let Some(first) = rest.split_whitespace().next() {
                    return first.parse().unwrap_or(0);
                }
            }
        }
        0
    }

    #[cfg(unix)]
    #[test]
    fn a_well_placed_file_passes_and_every_relaxation_is_caught() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("ok");
        let f = d.join("ledger.jsonl");
        std::fs::write(&f, b"").unwrap();
        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o644)).unwrap();
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();

        // 正控：布置合规 ⇒ 通过（这条钉住"不该红的"）
        assert!(
            assert_managed_cannot_write(&f, "账本（真相）", MANAGED).is_ok(),
            "属主非被管者、0644、目录 0755 ⇒ 边界成立"
        );

        // ① 文件对 other 可写 ⇒ 拒
        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o646)).unwrap();
        let e = assert_managed_cannot_write(&f, "账本（真相）", MANAGED).unwrap_err();
        assert!(e.contains("BoundaryWritable"), "{e}");
        std::fs::set_permissions(&f, std::fs::Permissions::from_mode(0o644)).unwrap();

        // ② 属主就是被管者 ⇒ 拒（mode 再严也没用）
        let e = assert_managed_cannot_write(&f, "账本（真相）", this_uid()).unwrap_err();
        assert!(e.contains("BoundaryOwned"), "{e}");

        // ③ 所在目录可写 ⇒ 拒（可整体换掉）
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o777)).unwrap();
        let e = assert_managed_cannot_write(&f, "账本（真相）", MANAGED).unwrap_err();
        assert!(e.contains("BoundaryDirWritable"), "{e}");
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();

        // ④ 符号链接 ⇒ 拒（检查的与用的可能不是同一个东西）
        let link = d.join("link.jsonl");
        std::os::unix::fs::symlink(&f, &link).unwrap();
        let e = assert_managed_cannot_write(&link, "账本（真相）", MANAGED).unwrap_err();
        assert!(e.contains("BoundarySymlink"), "{e}");

        let _ = std::fs::remove_dir_all(&d);
    }

    /// `D-31` 回归：相对路径必须查**当前目录**，不得被静默跳过。
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
    }
}
