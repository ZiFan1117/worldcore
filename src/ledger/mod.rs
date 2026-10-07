//! 账本：语义事件的**只追加**持久化。
//!
//! 形态：**纯文本 JSON Lines**（一行一条事件）。选它的三个理由：
//! ① 它同时就是**最简的分帧**（所以本体规定"内容里不得出现真实换行"）；
//! ② **语言无关**——换语言不需要重建世界（`07/2-依据/15-世界核心的组成与职责.md` §2.3）；
//! ③ 人可直接读、可 diff、可 grep。
//!
//! 三条**第一版就要守**的工程纪律（`07/4-计划/04` §2.2）：
//! 1. **`seq` 由世界分配**（启动时读最大 seq + 1，之后内存递增）；
//! 2. **写入必须原子**（一次写一整行 + flush）——崩在最坏只会留下**半行**；
//! 3. **启动读账本时末尾半行丢弃**（只追加 ⇒ 那是唯一可能残缺的位置）。
//!
//! **唯一写入口**：`file` 字段私有 ⇒ 全 crate 只有 [`Ledger::append`] 能改账本。

use crate::gate::guard;
use serde_json::{json, Value};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};

/// **落笔的 I/O 缝**——本模块**唯一**的字节级接口（替换掉原来直接持有的 `File`）。
///
/// ## 为什么要有这条缝（2026-09-27 加，闭合 `WC-RV-R2-001` 的 L3 缺口）
///
/// `append` 的加固逻辑有三条分支：①写入失败→**回滚**；②回滚也失败→**污染**；
/// ③`fsync` 失败→**污染**。这三条分支**只在真实 I/O 故障下才走到**，
/// 而"磁盘满""fsync 返回 EIO"在测试里无法可靠制造——于是它们是
/// **从来没有被执行过的代码**。对一个地基组件来说，这不可接受：
/// "一个从不失败的检查不是检查，是装饰"——同理，一条从不执行的分支不是防线。
///
/// 把字节级原语收进这一个窄接口后，测试可注入三种故障（部分写入 / fsync 失败 /
/// 截断失败），让三条分支各自拿到**实测证据**（`U20`–`U22`，见 `WC-UT-001`）。
///
/// ## 边界（防止这条缝变成绕过路径）
///
/// - 缝里**只有 I/O 原语**：长度、写入、刷盘、截断。**不含**取号、摘要链、
///   本体校验、门禁裁决——故注入故障只改变 I/O 的结果，**不改变 `append` 的决策路径**；
/// - 缝是 `pub(crate)` 且**只由 [`Ledger`] 私有字段持有**，外部无法替换（`Ledger::sink`
///   是私有字段；生产代码里没有任何 setter）；
/// - 生产实现只有一个：[`FileSink`]。测试替身 `FlakySink` 位于 `#[cfg(test)]` 内，
///   **不进发布产物**。
pub(crate) trait Sink: std::fmt::Debug {
    /// 当前文件长度（回滚基准）。
    fn byte_len(&self) -> std::io::Result<u64>;
    /// 写入并 `flush`（`flush` 失败按写入失败处理——与加固前的口径一致）。
    fn put(&mut self, bytes: &[u8]) -> std::io::Result<()>;
    /// `fsync`：确认落盘。
    fn sync(&mut self) -> std::io::Result<()>;
    /// 截断：回滚到指定长度。
    fn truncate(&mut self, len: u64) -> std::io::Result<()>;
}

/// 生产实现：直接写文件。**发布产物里只有它**。
#[derive(Debug)]
struct FileSink {
    file: File,
}

impl Sink for FileSink {
    fn byte_len(&self) -> std::io::Result<u64> {
        self.file.metadata().map(|m| m.len())
    }
    fn put(&mut self, bytes: &[u8]) -> std::io::Result<()> {
        self.file.write_all(bytes).and_then(|()| self.file.flush())
    }
    fn sync(&mut self) -> std::io::Result<()> {
        self.file.sync_data()
    }
    fn truncate(&mut self, len: u64) -> std::io::Result<()> {
        self.file.set_len(len)
    }
}

/// **打开口径**（2026-09-27 加，修 `P-01`：只读命令会写 L1）。
///
/// 为什么必须分开：原先 [`Ledger::open`] 对**任何**命令都执行"丢弃末尾半行"的
/// `set_len`，而 `state` / `read` / `project` / `check` 也走这条路径 ——
/// 于是"只读命令"在含半行的账本上会**改字节**（实测 size 480→442、sha 变化）。
/// 那与 IC 九册不变量①「只读接口不得写 L1」和 `REQ-F-012`「账本字节完全不变」**正面冲突**。
///
/// 现在：写路径（`append`）才允许截断与取锁；读路径**只读**，
/// 末尾半行只在内存里忽略（`valid_len`），**一个字节都不动**。
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OpenMode {
    /// 可写：取单写者锁、**必要时创建**（创建＝"初始化世界"这个**显式动作**）、丢弃末尾半行（截断落盘）。
    ReadWrite,
    /// 只读：**不取锁、不截断、不创建**。
    ///
    /// 账本不在场时，它读到的是**零条事件的空世界**（`valid_len = 0`），
    /// 而**盘上不留任何字节**——"读"不得有写副作用。
    /// "账本在不在"这件事由**调用侧**自己看路径（读不到就说读不到），
    /// 世界核**不替它造一个空账本**来表示"读到了"。
    ReadOnly,
}

/// 只读打开时使用的落笔实现：**任何写入都报错**。
///
/// 它存在的意义不是"防止误写"（只读命令的代码路径本来就不调 `append`），
/// 而是让"只读"成为**结构事实**：即便将来有人在只读路径上误调写入，
/// 也会立刻得到一个明确的错误，而不是悄悄改掉唯一真相。
#[derive(Debug)]
struct InertSink;

impl Sink for InertSink {
    fn byte_len(&self) -> std::io::Result<u64> {
        Ok(0)
    }
    fn put(&mut self, _bytes: &[u8]) -> std::io::Result<()> {
        Err(std::io::Error::other(
            "ext.world.Ledger.ReadOnly: 本账本以只读口径打开，禁止落笔",
        ))
    }
    fn sync(&mut self) -> std::io::Result<()> {
        Ok(())
    }
    fn truncate(&mut self, _len: u64) -> std::io::Result<()> {
        Err(std::io::Error::other(
            "ext.world.Ledger.ReadOnly: 本账本以只读口径打开，禁止截断",
        ))
    }
}

#[derive(Debug)]
pub struct Ledger {
    path: PathBuf,
    /// 私有：外部拿不到落笔能力，所以"一个写入口"是**类型级**保证，不靠约定。
    /// 类型是 [`Sink`] 而非 `File`，是为了留一条**可注入故障**的窄缝（见 [`Sink`]）。
    sink: Box<dyn Sink>,
    /// **完整行的字节前缀长度**（`P-01` 修）：末尾半行不进这个长度，
    /// 故 [`Ledger::read_from`] 只读这一段——读路径不必先截断文件就能忽略半行。
    valid_len: u64,
    /// 已落笔事件的 `id` 全集（**去重判据**，`W-01`）。
    ids: std::collections::HashSet<String>,
    next_seq: u64,
    /// **污染标记**（2026-09-26 加，见 WC-RV-R2-001 S-08）：写入失败**且回滚也失败**、
    /// 或 fsync 失败后，文件末尾状态不再可知，继续写可能造成行粘连。
    /// 故标记污染并拒绝后续写入：宁可停下，也不带着不确定的历史继续走。
    poisoned: Option<String>,
    /// **单写者锁**（2026-09-26 加，见 `WC-RV-R2-001` FIND-08 / 假设 `A-01`）。
    ///
    /// 为什么必须有：CLI **每条命令都是一个新进程**，而 `next_seq` 只活在内存里。
    /// 两个命令窗口重叠 ⇒ 各自从同一个 `next_seq` 取号 ⇒ 重号或半写交错 ⇒
    /// 下次启动 `SeqGap` 拒绝启动、**整个世界锁死**（`WC-SQAP-001` 列为 P0）。
    /// 此前只把它当"将来多进程才需要考虑"的事——其实今天就能发生。
    /// `None` = 只读口径打开（不取锁；见 [`OpenMode`]）。
    _lock: Option<LockGuard>,
    /// 链上最后一条的值（写入下一条时作为 `prev`）。见 `WC-CR-003`。
    last_chain: String,
    /// 本账本是否**带链**（启动时由 `load_chain` 判定）。见 `WC-CR-003` D2/D3。
    chained: bool,
}

/// 账本独占锁（用"创建即独占"的兄弟文件实现，**不引入 libc/flock**）。
///
/// 为什么不用 `flock`：本项目零外部依赖（`REQ-N-002`），而 `flock` 要 `libc`。
/// `OpenOptions::create_new(true)` 的原子性足以实现"同一时刻只有一个写者"：
/// 创建成功=拿到锁；已存在=被别人持有（或上次崩溃留下的陈旧锁）。
///
/// ⚠️ 已知局限：陈旧锁判定依赖 `/proc/<pid>`（Linux）。非 Linux 平台上
/// "持有者是否存活"恒判为否，即**陈旧锁总会被回收**——那会削弱互斥强度，
/// 但不会造成数据损坏（本项目的构建与运行环境都是 Linux，见 `WC-SDP-001` §4.1）。
#[derive(Debug)]
struct LockGuard {
    path: PathBuf,
}

impl Drop for LockGuard {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}

/// 取锁：先试创建；已存在则判断持有者是否还活着，死了就清理后重试一次。
fn acquire_lock(ledger_path: &Path) -> Result<LockGuard, String> {
    let lock = ledger_path.with_extension("lock");
    for attempt in 0..2 {
        match OpenOptions::new().write(true).create_new(true).open(&lock) {
            Ok(mut f) => {
                let _ = writeln!(f, "{}", std::process::id());
                return Ok(LockGuard { path: lock });
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
                let pid = std::fs::read_to_string(&lock)
                    .ok()
                    .and_then(|s| s.trim().parse::<u32>().ok());
                let alive = pid
                    .map(|p| Path::new(&format!("/proc/{p}")).exists())
                    .unwrap_or(false);
                if !alive && attempt == 0 {
                    let _ = std::fs::remove_file(&lock);
                    continue;
                }
                return Err(format!(
                    "ext.world.Ledger.Locked: 账本已被另一个世界核心占用（锁文件 {}，持有者 pid={:?} 仍存活）。\n\
                     \x20 为什么拒绝启动：单写者是硬要求——两个写者各自从内存取号，会造成重号或半写交错，\n\
                     \x20 而下次启动会因 SeqGap 拒启、世界锁死。\n\
                     \x20 处置：等另一个实例结束；若确认它已崩溃，删除该锁文件后重启",
                    lock.display(),
                    pid
                ));
            }
            Err(e) => {
                return Err(format!(
                    "ext.world.Ledger.LockFail: 无法创建锁文件 {}：{e}",
                    lock.display()
                ))
            }
        }
    }
    Err(format!(
        "ext.world.Ledger.LockFail: 锁文件反复出现，放弃（{}）",
        lock.display()
    ))
}

impl Ledger {
    /// 打开（必要时创建）账本；**丢弃末尾半行**；校验 seq 连续；恢复 `next_seq`。
    ///
    /// 并执行**静态防线检查**：账本文件与其所在目录不得对 group/other 可写。
    /// 理由见 [`crate::gate::guard`]：账本是唯一真相——**能被谁直写，真相就归谁**。
    ///
    /// ⚠️ 本函数是**可写**口径（会取锁、会截断末尾半行）。只读命令一律用
    /// [`Ledger::open_readonly`]，否则"只读"就会改字节（`P-01`）。
    pub fn open(path: &Path) -> Result<Self, String> {
        Self::open_mode(path, OpenMode::ReadWrite)
    }

    /// **只读**打开：不取单写者锁、不截断、不修改**既有**字节（`P-01` / `REQ-F-012`）。
    pub fn open_readonly(path: &Path) -> Result<Self, String> {
        Self::open_mode(path, OpenMode::ReadOnly)
    }

    /// 按 [`OpenMode`] 打开账本。
    pub fn open_mode(path: &Path, mode: OpenMode) -> Result<Self, String> {
        // 单写者锁：只在**可写**口径下取（FIND-08 / A-01）。
        // 只读口径不取锁：读者与写者互不阻塞，且"读"不产生任何文件副作用。
        let lock = match mode {
            OpenMode::ReadWrite => Some(acquire_lock(path)?),
            OpenMode::ReadOnly => None,
        };
        if !path.exists() {
            // ★ **创建只发生在可写口径**（创建 ＝ "初始化世界"这个**显式动作**）。
            //
            // 症状（两个席从两个方向独立摸到、结论一致，2026-10-05）：
            // 拿一个**不存在的** `--ledger` 路径跑一条**只读**命令 ⇒ **rc=0**，
            // 而**盘上多出一个 0 字节账本**。⇒ 那次"读"有了写副作用，它就不是读；
            // 而它恰恰会被人**当成读**来用（`check` / `state` / `read` / `project` 都在这条路上）——
            // 与 `P-01`（只读命令会截断半行）是同一族：**"只读"当时只是进程内的约定。**
            //
            // 现在：只读口径在账本不在场时**一个字节都不落盘**，读到的是**零条事件的空世界**。
            // ⚠️ 它不是错误、也不另报一个码：**"账本不在场"与"账本是空的"在世界状态上同一件事**
            //    （都没有事件），而"要不要把『不在场』说给用户"是**调用侧**的事（它自己看路径）。
            //    代价（如实登记）：世界核**不再**用"造一个空账本"来表示"读到了"，
            //    故**只读命令不再创建文件**——依赖那次创建的调用方必须自己初始化。
            let file = if mode == OpenMode::ReadWrite {
                let f = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .read(true)
                    .open(path)
                    .map_err(|e| format!("ext.world.Ledger.CreateFail: {path:?}: {e}"))?;
                // 刚创建的账本也要过静态防线（否则"新建一个宽松账本"就是绕过路径）
                guard::assert_after_create(path, "账本（真相）")?;
                Some(f)
            } else {
                None
            };
            return Ok(Ledger {
                path: path.to_path_buf(),
                sink: match file {
                    Some(f) => Box::new(FileSink { file: f }),
                    None => Box::new(InertSink),
                },
                valid_len: 0,
                ids: std::collections::HashSet::new(),
                next_seq: 1,
                poisoned: None,
                _lock: match mode {
                    OpenMode::ReadWrite => Some(lock.expect("可写口径必有锁")),
                    OpenMode::ReadOnly => None,
                },
                last_chain: CHAIN_GENESIS.to_string(),
                chained: false,
            });
        }

        // 静态防线：真相的存放处不得对被管者开放写权限
        guard::assert_not_other_writable(path, "账本（真相）")?;

        // ── 第一步：算出"完整行前缀"长度 ──
        // 可写口径：截断落盘（让"末尾永远是完整行"重新成立）；
        // 只读口径：**不动文件**，只把 `valid_len` 记下来当读边界。
        let mut raw = Vec::new();
        File::open(path)
            .and_then(|mut f| f.read_to_end(&mut raw))
            .map_err(|e| format!("ext.world.Ledger.ReadFail: {path:?}: {e}"))?;

        let keep = match raw.iter().rposition(|b| *b == b'\n') {
            Some(pos) => pos + 1, // 保留到最后一个换行（含）
            None => 0,            // 一个换行都没有 ⇒ 整个文件都是半行
        };
        if keep != raw.len() {
            if mode == OpenMode::ReadWrite {
                OpenOptions::new()
                    .write(true)
                    .open(path)
                    .and_then(|f| f.set_len(keep as u64))
                    .map_err(|e| format!("ext.world.Ledger.TruncateFail: {path:?}: {e}"))?;
            }
            raw.truncate(keep);
        }

        // ── 第二步：逐行校验 seq 连续（缺号即损坏，拒绝启动）＋ 收 `id` 去重集（`W-01`）──
        let mut last = 0u64;
        let mut ids = std::collections::HashSet::new();
        for (i, line) in raw.split(|b| *b == b'\n').enumerate() {
            if line.is_empty() {
                continue;
            }
            let v: Value = serde_json::from_slice(line)
                .map_err(|e| format!("ext.world.Ledger.Corrupt: 第 {} 行: {e}", i + 1))?;
            let seq = v
                .get("seq")
                .and_then(Value::as_u64)
                .ok_or_else(|| format!("ext.world.Ledger.MissingSeq: 第 {} 行", i + 1))?;
            if seq != last + 1 {
                return Err(format!(
                    "ext.world.Ledger.SeqGap: 第 {} 行 seq={seq}，期望 {}",
                    i + 1,
                    last + 1
                ));
            }
            last = seq;
            // **同 id 出现两次** ⇒ 账本违反"事件身份唯一"，拒绝启动。
            // 为什么在启动侧也要判：只判写入侧挡不住"账本被外部拼出来"的情形，
            // 而事件身份是读模型/复盘/幂等的锚点（`W-01`）。
            //
            // ⚠️ 口径（刻意）：这里只判**重复**，**不**强制"每行都必须有 `id`"。
            // 理由是错误**优先级**：`id` 缺失是信封契约问题（写入侧 `append` 与本体校验
            // 已经拦住），而"缺号"是账本损坏——若在这里把"缺 id"判在前面，
            // 一本**缺号**的账本会被报成 `MissingId`，把真正的损坏理由盖掉（实测抓到）。
            if let Some(id) = v.get("id").and_then(Value::as_str) {
                if !ids.insert(id.to_string()) {
                    return Err(format!(
                        "ext.world.Ledger.DuplicateId: 第 {} 行 id={id} 与更早的行重复——\
                         事件身份必须唯一（同 id 再提交即为重复提交），拒绝启动",
                        i + 1
                    ));
                }
            }
        }

        // ★ **只读口径不许要求写权限**（2026-10-05 修）：
        //   原先这里对**两种口径**都用 `append(true).read(true)` 打开，于是"只读"只是
        //   **进程内的约定**——它仍然向内核要了写权限。后果实测（零写沙箱：只读挂载的账本，
        //   或属主之外只读的账本）：`O_APPEND` 当场 `EROFS`／`EACCES` ⇒ `read`／`state`／
        //   `subscribe`／`project check`／`check` **五条命令全部 rc=2**，码是 `Ledger.OpenFail`。
        //   即：**账本写不了的时候，世界连读都读不成**——而"读"恰恰是最该在只读世界里活着的那件事。
        //   现在：写口径才 `append(true)`；只读口径只要**读权限**（打不开仍报 `OpenFail`，
        //   错误码与处置不变，改的只是"向内核要什么权限"）。
        let file = match mode {
            OpenMode::ReadWrite => OpenOptions::new().append(true).read(true).open(path),
            OpenMode::ReadOnly => OpenOptions::new().read(true).open(path),
        }
        .map_err(|e| format!("ext.world.Ledger.OpenFail: {path:?}: {e}"))?;
        Ok(Ledger {
            path: path.to_path_buf(),
            sink: match mode {
                OpenMode::ReadWrite => Box::new(FileSink { file }),
                OpenMode::ReadOnly => Box::new(InertSink),
            },
            valid_len: keep as u64,
            ids,
            next_seq: last + 1,
            poisoned: None,
            _lock: match mode {
                OpenMode::ReadWrite => Some(lock.expect("可写口径必有锁")),
                OpenMode::ReadOnly => None,
            },
            last_chain: CHAIN_GENESIS.to_string(),
            chained: false,
        })
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// 下一个将被分配的 seq（= 当前日志长度 + 1）。
    pub fn next_seq(&self) -> u64 {
        self.next_seq
    }

    /// 已落笔的最后一条事件的 seq（空账本为 0）。
    pub fn last_seq(&self) -> u64 {
        self.next_seq - 1
    }

    /// **唯一的写入口**：追加一条事件。
    ///
    /// 传入的事件的 `seq` **必须**等于 [`Ledger::next_seq`]（由调用者取号），
    /// 否则拒绝——这防止"取号与落笔脱节"。
    ///
    /// ## 可见性（2026-09-26 收窄，见 WC-RV-R2-001 S-02/T-02）
    ///
    /// 本函数是 `pub(crate)`，**不再是公开 API**。原先它是 `pub`，
    /// 于是任何拿到 `&mut Ledger` 的使用方都能"自己取号 + append 任意 kind"，
    /// 完全绕过 `World::commit` 与门禁——**"唯一写入口"就只是一句声明**。
    ///
    /// ## 写入的完整性（2026-09-26 加固，见 S-08）
    ///
    /// 原实现只有 `write_all + flush`，于是有三处真实缺口：
    /// ① **短写/中途失败**会留下半行，而 `next_seq` 不前进——下一条成功写入会
    ///    紧贴半行落下造成**两行粘连**；重启读到坏 JSON 后**整个账本拒绝启动**；
    /// ② 若粘连处含此前已 ack 的事件，启动时"截到最后一个 `\n`"会**静默删掉**它们；
    /// ③ `flush` 只把数据交给内核，**掉电仍可能丢已 ack 的事件**。
    ///
    /// 现在的做法：写入前记下文件长度；**任何写入/刷盘失败都回滚到该长度**
    /// （保证"末尾永远是完整行"这个前提重新成立）；回滚失败则把账本标记为
    /// **已污染**并拒绝后续写入（宁可停，也不要带着不确定的账本继续走）；
    /// 成功路径追加 `sync_data`（fsync）后才推进 `next_seq`。
    pub(crate) fn append(&mut self, ev: Value) -> Result<Value, String> {
        if let Some(why) = &self.poisoned {
            return Err(format!(
                "ext.world.Ledger.Poisoned: 账本已被标记为不可再用（{why}）；\
                 拒绝继续写入以免产生不确定的历史。请人工检查 {} 后重启",
                self.path.display()
            ));
        }

        let seq = ev
            .get("seq")
            .and_then(Value::as_u64)
            .ok_or_else(|| "ext.world.Ledger.MissingSeq".to_string())?;
        if seq != self.next_seq {
            return Err(format!(
                "ext.world.Ledger.SeqMismatch: 传入 seq={seq}，账本期望 {}",
                self.next_seq
            ));
        }

        // **同 id 再提交 ⇒ 拒绝**（`W-01` 的写入侧判据）。
        // 为什么在落笔前判：事件身份是复盘、幂等重试与读模型锚点的共同前提；
        // 恒同 id 会让"两条不同的历史"在身份上不可区分（可复现的突变实验：
        // 把 `event::new_id()` 改成返回常量，本条即报红）。
        let id = ev
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Ledger.MissingId: 事件缺 `id`".to_string())?
            .to_string();
        if self.ids.contains(&id) {
            return Err(format!(
                "ext.world.Ledger.DuplicateId: id={id} 已在本账本中——\
                 事件身份必须唯一（同 id 再提交即为重复提交），拒绝落笔"
            ));
        }

        // 摘要链（`WC-CR-003` D1）：写入前把 `chain` 记进事件本身。
        // 纯文本十六进制字符串，仍在同一行 JSON 里 ⇒ 语言无关（REQ-N-001 不受影响）。
        let chain = event_chain(&self.last_chain, &ev)?;
        let mut ev = ev;
        ev.as_object_mut()
            .expect("事件必须是对象")
            .insert("chain".to_string(), Value::String(chain.clone()));

        let mut line =
            serde_json::to_string(&ev).map_err(|e| format!("ext.world.Ledger.EncodeFail: {e}"))?;
        line.push('\n');

        let pre_len = self
            .sink
            .byte_len()
            .map_err(|e| format!("ext.world.Ledger.StatFail: {e}"))?;

        if let Err(e) = self.sink.put(line.as_bytes()) {
            return Err(self.rollback_after_failed_write(pre_len, &e.to_string()));
        }

        if let Err(e) = self.sink.sync() {
            // 数据已写进内核缓冲，但**无法确认落盘**；此时回滚与前进都不安全
            // （回滚可能让已可见的字节消失，前进则可能在掉电后缺号）。
            // 按 fail loud 处理：污染账本、拒绝后续写入。
            self.poisoned = Some(format!("sync_data 失败：{e}"));
            return Err(format!(
                "ext.world.Ledger.SyncFail: {e}（无法确认 seq={seq} 已落盘；\
                 账本已标记为不可再用，请人工检查后重启）"
            ));
        }

        self.next_seq += 1;
        self.last_chain = chain;
        self.ids.insert(id);
        self.valid_len += line.len() as u64;
        Ok(ev)
    }

    /// 写入失败后的回滚：把文件截回写入前的长度，让"末尾永远是完整行"重新成立。
    ///
    /// 回滚失败（例如磁盘已满到连截断都做不到）→ **污染账本**：
    /// 此时文件末尾状态未知，继续写入就可能制造粘连行。
    fn rollback_after_failed_write(&mut self, pre_len: u64, cause: &str) -> String {
        match self.sink.truncate(pre_len) {
            Ok(()) => {
                let _ = self.sink.sync();
                format!(
                    "ext.world.Ledger.WriteFail: {cause}\
                     （已回滚到写入前的 {pre_len} 字节，末行完整性保持；seq 未前进，可重试）"
                )
            }
            Err(e) => {
                self.poisoned = Some(format!("写入失败且回滚失败：{cause} / {e}"));
                format!(
                    "ext.world.Ledger.WriteFail: {cause}\
                     （⚠️ 回滚亦失败：{e} —— 账本已被标记为不可再用，\
                     因为末尾可能残留半行，继续写会造成行粘连）"
                )
            }
        }
    }

    /// **载入并核验摘要链**（`WC-CR-003` D2 的启动侧）。
    ///
    /// - 全链合法 ⇒ 记住链尾，返回 `true`；
    /// - **无链** ⇒ 允许（v1 账本），返回 `false` —— **调用方须打印警告**（未校验要说出来）；
    /// - 篡改/重排/插入/混用 ⇒ `Err`，**拒绝启动**。
    pub fn load_chain(&mut self) -> Result<bool, String> {
        let events = self.read_from(1)?;
        match verify_chain(&events) {
            Ok(()) => {
                if let Some(last) = events
                    .last()
                    .and_then(|e| e.get("chain"))
                    .and_then(Value::as_str)
                {
                    self.last_chain = last.to_string();
                    self.chained = true;
                    Ok(true)
                } else {
                    Ok(false)
                }
            }
            Err(e) if e.contains("NoChain") => Ok(false),
            Err(e) => Err(e),
        }
    }

    /// 本账本是否带摘要链（无链 ⇒ **局部篡改不可检出**，见 `WC-CR-003` §三）。
    pub fn is_chained(&self) -> bool {
        self.chained
    }

    /// 从 `from_seq` 起按序读回事件（含 `from_seq`）。
    ///
    /// **只读 `valid_len` 字节**（`P-01` 修）：末尾半行不进读边界，故读路径
    /// 既不必、也不许先把文件截断。
    pub fn read_from(&self, from_seq: u64) -> Result<Vec<Value>, String> {
        // ★ **账本不在场 ⇒ 零条事件**（不是错误）：只读口径在路径不存在时**不创建**它
        // （见 [`Ledger::open_mode`]），而"世界还没写过东西"与"世界是空的"在世界状态上同一件事。
        // ⚠️ 射程：这一格只对**文件不在**成立；**文件在但读不动**仍旧报 `ReadFail`（不许混）。
        let mut f = match File::open(&self.path) {
            Ok(f) => f,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(e) => return Err(format!("ext.world.Ledger.ReadFail: {:?}: {e}", self.path)),
        };
        let mut buf = Vec::new();
        std::io::Read::take(&mut f, self.valid_len)
            .read_to_end(&mut buf)
            .map_err(|e| format!("ext.world.Ledger.ReadFail: {e}"))?;
        let mut out = Vec::new();
        for line in BufReader::new(std::io::Cursor::new(buf)).lines() {
            let line = line.map_err(|e| format!("ext.world.Ledger.ReadFail: {e}"))?;
            if line.trim().is_empty() {
                continue;
            }
            let v: Value = serde_json::from_str(&line)
                .map_err(|e| format!("ext.world.Ledger.Corrupt: {e}"))?;
            if v.get("seq").and_then(Value::as_u64).unwrap_or(0) >= from_seq {
                out.push(v);
            }
        }
        Ok(out)
    }

    /// 全量读回（= `read_from(1)`）。
    pub fn read_all(&self) -> Result<Vec<Value>, String> {
        self.read_from(1)
    }
}

/// 摘要链的**创世种子**（首条事件的 `chain` 由它起算）。
pub const CHAIN_GENESIS: &str = "genesis";

/// 计算某条事件在链上的值：`fnv1a64(前值 + "\n" + 去除 chain 后的规范形式)`。
///
/// 口径与 `WC-CR-003` §二 D1 一致：**纯文本十六进制字符串**，语言无关。
/// 见 `WC-CR-003`（该变更**待人工批准**；本函数是**只读的验证侧**，
/// 不改变账本写入格式，故不依赖批准即可使用）。
pub fn event_chain(prev: &str, ev: &Value) -> Result<String, String> {
    let mut bare = ev.clone();
    if let Some(o) = bare.as_object_mut() {
        o.remove("chain");
    }
    let canon =
        serde_json::to_string(&bare).map_err(|e| format!("ext.world.Ledger.EncodeFail: {e}"))?;
    const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;
    let mut h = OFFSET;
    for b in prev.as_bytes().iter().chain(b"\n").chain(canon.as_bytes()) {
        h ^= u64::from(*b);
        h = h.wrapping_mul(PRIME);
    }
    Ok(format!("fnv1a64:{h:016x}"))
}

/// **只读**摘要链核验（`WC-CR-003` §二 D2 的验证侧）。
///
/// 判定：
/// - 全部行都有 `chain` ⇒ 逐环核验；**任一环断裂即 `Err`**；
/// - **全部行都没有** ⇒ `Err(NoChain)`——**调用方**自行决定是"警告后继续"还是拒启
///   （`WC-CR-003` D2：默认警告，`--require-chain` 时拒启）；
/// - **混用** ⇒ `Err(MixedChain)`——半链比无链更危险（看起来受保护）。
///
/// ⚠️ **边界（必须说清，见 `WC-CR-003` §三）**：无密钥的链**挡不住"整文件重写"**——
/// 能重算整条链的对手可以让核验通过。`c19` 就是把这个极限**写成测试**。
pub fn verify_chain(events: &[Value]) -> Result<(), String> {
    let has: Vec<bool> = events.iter().map(|e| e.get("chain").is_some()).collect();
    if has.is_empty() {
        return Ok(());
    }
    if has.iter().all(|b| !b) {
        return Err(
            "ext.world.Ledger.NoChain: 账本全部无 `chain` 字段——局部篡改**不可检出**".to_string(),
        );
    }
    if !has.iter().all(|b| *b) {
        return Err(
            "ext.world.Ledger.MixedChain: 部分事件有 `chain`、部分没有——\
             前半受保护容易让人误以为整本受保护（比无链更危险），拒绝使用"
                .to_string(),
        );
    }
    let mut prev = CHAIN_GENESIS.to_string();
    for (i, ev) in events.iter().enumerate() {
        let want = event_chain(&prev, ev)?;
        let got = ev
            .get("chain")
            .and_then(Value::as_str)
            .ok_or_else(|| "ext.world.Ledger.MissingChain".to_string())?;
        if got != want {
            return Err(format!(
                "ext.world.Ledger.ChainMismatch: 第 {} 条（seq={}）的 chain 不符——\
                 账本内容被改动、被重排或被插入。账本是唯一真相，拒绝使用",
                i + 1,
                ev.get("seq").and_then(Value::as_u64).unwrap_or(0)
            ));
        }
        prev = got.to_string();
    }
    Ok(())
}

/// 便利函数：把一条事件序列化成一行（不含换行）。供测试与工具复用。
pub fn encode_line(ev: &Value) -> Result<String, String> {
    serde_json::to_string(ev).map_err(|e| format!("ext.world.Ledger.EncodeFail: {e}"))
}

/// 便利函数：把 `seq` 单独取出来（测试与门禁用）。
pub fn seq_of(ev: &Value) -> u64 {
    ev.get("seq").and_then(Value::as_u64).unwrap_or(0)
}

/// 便利函数：造一个最小合法事件（测试用，避免测试里重复样板）。
pub fn minimal_change(subject: &str, path: &str) -> Value {
    json!({ "subject": subject, "path": path, "before": false, "after": true })
}

/// **故障注入测试**（`U20`–`U22`，见 `WC-UT-001` / `WC-TS-001`）。
///
/// 放在 crate 内的理由：替身要替换 [`Ledger::sink`] 这个**私有字段**。
/// 若把它做成公开 API（哪怕 `#[doc(hidden)]`），生产代码就多了一条"换掉存储"的路，
/// 与"一个写入口"直接冲突。故替身只活在 `#[cfg(test)]` 里，**不进发布产物**。
#[cfg(test)]
mod fault_injection {
    use super::*;
    use std::cell::RefCell;
    use std::io;
    use std::rc::Rc;

    /// 故障配置（测试可**在运行中**改它，故与 sink 共享 `Rc<RefCell<_>>`）。
    #[derive(Debug, Default, Clone, Copy)]
    struct Fault {
        /// 先落 N 字节再报错——**正是"崩在行中间"的形状**（短写/中途失败）。
        fail_put_after: Option<usize>,
        /// `fsync` 失败（无法确认落盘）。
        fail_sync: bool,
        /// 截断失败 ⇒ 回滚也做不到。
        fail_truncate: bool,
    }

    /// 可注入故障的 [`Sink`]：除故障点外**行为与 [`FileSink`] 完全一致**，
    /// 故它测的是**真实的 `append` 逻辑**，而不是另一个仿真实现。
    #[derive(Debug)]
    struct FlakySink {
        file: File,
        fault: Rc<RefCell<Fault>>,
    }

    impl Sink for FlakySink {
        fn byte_len(&self) -> io::Result<u64> {
            self.file.metadata().map(|m| m.len())
        }
        fn put(&mut self, bytes: &[u8]) -> io::Result<()> {
            let f = *self.fault.borrow();
            if let Some(n) = f.fail_put_after {
                let n = n.min(bytes.len());
                self.file.write_all(&bytes[..n])?;
                self.file.flush()?;
                return Err(io::Error::other(format!(
                    "注入的写入故障（已落 {n} 字节后失败）"
                )));
            }
            self.file.write_all(bytes).and_then(|()| self.file.flush())
        }
        fn sync(&mut self) -> io::Result<()> {
            if self.fault.borrow().fail_sync {
                return Err(io::Error::other("注入的 fsync 故障"));
            }
            self.file.sync_data()
        }
        fn truncate(&mut self, len: u64) -> io::Result<()> {
            if self.fault.borrow().fail_truncate {
                return Err(io::Error::other("注入的截断故障"));
            }
            self.file.set_len(len)
        }
    }

    /// 一次性沙箱目录（0700：账本的静态防线要求所在目录不得对 group/other 可写）。
    fn sandbox(tag: &str) -> PathBuf {
        use std::os::unix::fs::PermissionsExt;
        let n = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let d = std::env::temp_dir().join(format!("wc-ledger-fault-{tag}-{n}"));
        std::fs::create_dir_all(&d).unwrap();
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o700)).unwrap();
        d
    }

    /// 把账本的落笔换成可注入故障的实现；返回与它共享的故障配置。
    ///
    /// 注意：替换的是**同一个路径上的另一个句柄**（append 模式，与原句柄等效），
    /// 故被测文件、锁文件、静态防线都不受影响。
    fn inject(l: &mut Ledger, dir: &Path, name: &str) -> Rc<RefCell<Fault>> {
        let file = OpenOptions::new()
            .append(true)
            .read(true)
            .open(dir.join(name))
            .unwrap();
        let fault = Rc::new(RefCell::new(Fault::default()));
        l.sink = Box::new(FlakySink {
            file,
            fault: Rc::clone(&fault),
        });
        fault
    }

    fn ev(seq: u64) -> Value {
        // ⚠️ 2026-09-27 修（`W-01` 的同族问题）：原实现所有 seq 共用 `"id": "n-fault"`，
        // 即**事件身份恒同**。加了写入侧去重判据后，这条"恒同 id"当场暴露为
        // `DuplicateId`（而不是测试期望的 `WriteFail`）——也就是说：**测试夹具本身
        // 一直在制造"两条不同历史、同一个身份"的账本**。改成按 seq 唯一。
        json!({
            "world": 1, "kind": "notice", "id": format!("n-fault-{seq}"), "seq": seq, "at": "t0",
            "actor": "world://core", "flags": [],
            "body": { "type": "fault.injected", "subject": "world://test" }
        })
    }

    /// `U20`：**部分写入失败 ⇒ 回滚到写入前的字节，seq 不前进，可重试**。
    ///
    /// 这是"短写会留下半行"这个真实缺口的正面证据：断言的是**文件逐字节等于写入前**，
    /// 而不是"相信代码会回滚"。
    #[test]
    fn u20_partial_write_failure_rolls_back_and_allows_retry() {
        let d = sandbox("rollback");
        let mut l = Ledger::open(&d.join("ledger.jsonl")).unwrap();

        // 基线：先正常写一条，制造"已有内容"（回滚错的基准不能是空文件）
        l.append(ev(1)).unwrap();
        let before = std::fs::read(l.path()).unwrap();
        assert!(before.ends_with(b"\n"), "基线必须以完整行结尾");

        let fault = inject(&mut l, &d, "ledger.jsonl");
        fault.borrow_mut().fail_put_after = Some(20); // 落 20 字节后失败

        let e = l.append(ev(2)).unwrap_err();
        assert!(
            e.starts_with("ext.world.Ledger.WriteFail:"),
            "错误码须是 WriteFail；实得: {e}"
        );
        assert!(e.contains("已回滚"), "错误须说明**是否已回滚**；实得: {e}");

        // ★ 实测证据 1：文件**逐字节**回到写入前（半行不存在了）
        assert_eq!(
            std::fs::read(l.path()).unwrap(),
            before,
            "回滚必须把文件还原到写入前的字节（否则残留半行）"
        );
        // ★ 实测证据 2：seq 不得前进（前进就会造成重号）
        assert_eq!(l.next_seq(), 2, "写入失败后 seq 不得前进，否则重号");
        // ★ 实测证据 3：账本未被污染 ⇒ 修好故障后**重试必须成功**
        fault.borrow_mut().fail_put_after = None;
        l.append(ev(2)).unwrap();

        let text = std::fs::read_to_string(l.path()).unwrap();
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(
            lines.len(),
            2,
            "必须是两条完整行（粘连行会让下次启动整本拒启）"
        );
        for line in &lines {
            serde_json::from_str::<Value>(line).expect("每行都必须是完整 JSON");
        }
        assert_eq!(l.next_seq(), 3);
    }

    /// `U21`：**回滚也失败 ⇒ 污染账本并拒绝后续写入**（宁可停下）。
    ///
    /// 并且**如实记录**：此时盘上确实留着半行——本测试断言它**没有**被清掉，
    /// 以免有人误以为"污染标记"等于"已经收拾干净了"。
    #[test]
    fn u21_failed_rollback_poisons_ledger() {
        let d = sandbox("poison");
        let lp = d.join("ledger.jsonl");
        let mut l = Ledger::open(&lp).unwrap();
        l.append(ev(1)).unwrap();
        let before_len = std::fs::read(l.path()).unwrap().len() as u64;

        let fault = inject(&mut l, &d, "ledger.jsonl");
        fault.borrow_mut().fail_put_after = Some(7);
        fault.borrow_mut().fail_truncate = true;

        let e = l.append(ev(2)).unwrap_err();
        assert!(
            e.starts_with("ext.world.Ledger.WriteFail:"),
            "错误码须是 WriteFail；实得: {e}"
        );
        assert!(e.contains("回滚亦失败"), "须点明回滚失败；实得: {e}");

        // 如实记录：半行**留在盘上**（没能回滚就是没能回滚）
        let raw = std::fs::read(l.path()).unwrap();
        assert!(
            raw.len() > before_len as usize && !raw.ends_with(b"\n"),
            "注入的 7 字节应残留且不以换行结尾（本用例记录真实残留，不粉饰）"
        );

        // ★ 即使故障解除，也必须拒绝继续写（带着不确定的末尾继续走才危险）
        fault.borrow_mut().fail_truncate = false;
        let e2 = l.append(ev(2)).unwrap_err();
        assert!(
            e2.starts_with("ext.world.Ledger.Poisoned:"),
            "污染后必须拒绝写入；实得: {e2}"
        );
        assert_eq!(l.next_seq(), 2, "拒绝写入后 seq 不得前进");
    }

    /// `U22`：**`fsync` 失败 ⇒ 污染账本**（无法确认落盘时既不能回滚也不能前进）。
    #[test]
    fn u22_fsync_failure_poisons_ledger() {
        let d = sandbox("sync");
        let mut l = Ledger::open(&d.join("ledger.jsonl")).unwrap();

        let fault = inject(&mut l, &d, "ledger.jsonl");
        fault.borrow_mut().fail_sync = true;

        let e = l.append(ev(1)).unwrap_err();
        assert!(
            e.starts_with("ext.world.Ledger.SyncFail:"),
            "错误码须是 SyncFail；实得: {e}"
        );
        assert_eq!(l.next_seq(), 1, "无法确认落盘时不得推进 seq");
        assert_eq!(
            l.last_chain, CHAIN_GENESIS,
            "未成功落笔的事件不得改动链尾（否则下一条的 prev 指向不存在的环）"
        );

        fault.borrow_mut().fail_sync = false;
        let e2 = l.append(ev(1)).unwrap_err();
        assert!(
            e2.starts_with("ext.world.Ledger.Poisoned:"),
            "fsync 失败后必须拒绝写入；实得: {e2}"
        );
    }
}

/// **只读口径不许要求写权限**（2026-10-05 修）——标的物是「**本进程写不了的账本**」。
///
/// ## 为什么这条判据必须存在
///
/// `open_mode` 的只读口径若仍以 `append(true)` 打开账本，"只读"就只是**进程内的约定**：
/// 它照样向内核要写权限。后果不是推的，是实测的——零写沙箱（只读挂载的账本）里
/// `read`／`state`／`subscribe`／`project check`／`check` **全部** `Ledger.OpenFail`（rc=2）：
/// **账本写不了的时候，世界连读都读不成。**
///
/// ## 标的物怎么造（**这条是 root 也绕不过的**）
///
/// `chmod` 对 root 无效（root 有 `CAP_DAC_OVERRIDE`），故**不许**拿"去掉写位"造这一格。
/// 本用例用 `chattr +i`（immutable）：内核对**任何**进程——含 root——都拒绝写它，
/// 于是"这个文件写不了"是**内核级事实**，不是权限位里的一句话。
///
/// ## 四关
///
/// | 关 | 本用例怎么满足 |
/// |---|---|
/// | ① 会红 | 把只读口径短路回 `append(true).read(true)` ⇒ 本条当场红（本席实测） |
/// | ② 正控 | **同一夹具**上写口径 `Ledger::open` 必须失败（证明"这文件真写不了"），且读回的事件**非空** |
/// | ③ 反例与真实违规同形态 | 反例就是**修复前那一行**本身，不是另造一个形状 |
/// | ④ 锚唯一 | 只落在"只读口径打得开／打不开"这一个可观测事实上 |
///
/// ## 如实声明的边界（**不许读成"已覆盖一切只读环境"**）
///
/// - 标的物是「**文件**不可写」；它**不覆盖**「**整个文件系统**只读（`EROFS`）」那种形态
///   ——那一种的实测读数在本席 2026-10-05 的零写沙箱记录里（只读 bind 挂载），**不在本用例内**；
/// - **不支持 `chattr +i` 的文件系统**（如 `tmpfs`）上造不出标的物 ⇒ 本用例**打印
///   「未能校验」并返回**——**那一步的绿不是通过**。故夹具落在**本仓 `target/`**
///   （`btrfs`／`ext4` 支持 immutable），**不落 `/tmp`**。
#[cfg(test)]
mod readonly_open {
    use super::*;

    /// 夹具目录：**本仓 `target/`**（不走 `/tmp`——`tmpfs` 不支持 `chattr +i`）。
    fn sandbox(tag: &str) -> PathBuf {
        use std::os::unix::fs::PermissionsExt;
        let n = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let d = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!("wc-ledger-ro-{tag}-{n}"));
        std::fs::create_dir_all(&d).unwrap();
        // 账本的静态防线要求所在目录不得对 group/other 可写。
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o700)).unwrap();
        d
    }

    fn ev(seq: u64) -> Value {
        json!({
            "world": 1, "kind": "notice", "id": format!("n-ro-{seq}"), "seq": seq, "at": "t0",
            "actor": "world://core", "flags": [],
            "body": { "type": "ro.open", "subject": "world://test" }
        })
    }

    /// `chattr <flag> <path>`：成功 ⇒ `true`（没有 `chattr` 或文件系统不支持 ⇒ `false`）。
    fn chattr(flag: &str, p: &Path) -> bool {
        std::process::Command::new("chattr")
            .arg(flag)
            .arg(p)
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }

    /// **夹具的守护**：`Drop` 里撤掉 immutable 再删目录——**panic 时也必须跑**。
    ///
    /// 为什么不能只写一句顺序代码：本用例的判据**失败时要 panic**，而那句 `chattr -i`
    /// 若排在断言之后，就**永远跑不到** ⇒ 盘上留下一个**谁也删不掉的**夹具
    /// （实测：把修复短路回去跑一次，随后的 `rm -rf` 报 `Operation not permitted`）。
    /// `Drop` 在栈展开里执行，故反例**跑红之后也不会污染后续夹具**。
    struct Sandbox {
        dir: PathBuf,
        file: PathBuf,
    }

    impl Drop for Sandbox {
        fn drop(&mut self) {
            let _ = chattr("-i", &self.file);
            let _ = std::fs::remove_dir_all(&self.dir);
        }
    }

    #[test]
    fn readonly_open_does_not_require_write_permission() {
        let d = sandbox("open");
        let lp = d.join("ledger.jsonl");
        // ★ 守护必须在**任何**可能 panic 的语句之前建好（含下面那次 `chattr +i` 的早退路径）。
        let _sb = Sandbox {
            dir: d.clone(),
            file: lp.clone(),
        };
        {
            let mut l = Ledger::open(&lp).unwrap();
            l.append(ev(1)).unwrap();
        } // 写句柄在这里关掉：后面只读打开时，不能有别人替它拿着写权限。

        if !chattr("+i", &lp) {
            eprintln!(
                "【未能校验】readonly_open_does_not_require_write_permission：\
                 本环境造不出标的物（`chattr +i` 不可用：缺 chattr，或文件系统不支持 immutable）\
                 ⇒ 本用例**没有跑**，这一处的绿**不是通过**。"
            );
            return;
        }

        // ② 正控（同夹具、必红）：写口径在**同一个文件**上必须失败。
        //    它证明"这个文件真的写不了"——否则下面那条"只读口径打得开"是**恒真**的。
        let werr = match Ledger::open(&lp) {
            Ok(_) => panic!("正控失败：写口径竟在一个 immutable 的账本上打开了——标的物没造出来"),
            Err(e) => e,
        };
        assert!(
            werr.contains("ext.world.Ledger.OpenFail"),
            "写口径的拒绝须是类型化错误码；实得: {werr}"
        );

        // ① 判据：只读口径必须打得开，且**读得到内容**（不是"打开了个空壳"）。
        let l = Ledger::open_readonly(&lp).expect("只读口径在写不了的账本上必须打得开");
        assert_eq!(l.last_seq(), 1, "只读口径必须认到已有的那一条");
        assert_eq!(
            l.read_from(1).unwrap().len(),
            1,
            "只读口径必须**读得到**账本内容（正控：非空）"
        );
        // 清理由 `_sb` 的 `Drop` 承担（写在断言之后就会在跑红时漏掉）。
    }

    /// ★ **只读口径不许创建账本**（"读"不得有写副作用）。
    ///
    /// ## 标的物与症状
    ///
    /// 拿一个**不存在的**路径跑一次**只读**打开。症状是：**rc=0**，而**盘上多出一个 0 字节账本**。
    /// 而它恰恰会被人**当成读**来用（`check`／`state`／`read`／`project` 全走这条路）——
    /// "读"若有写副作用，它就不是读。
    ///
    /// ## 四关
    ///
    /// | 关 | 本用例怎么满足 |
    /// |---|---|
    /// | ① 会红 | 让只读那一支也走创建（把 `if mode == OpenMode::ReadWrite` 短路成 `if true`）⇒ ② 当场红 |
    /// | ② 正控 | **同夹具**上**写**口径**必须**把账本建出来——否则②是**恒真**的（路径本来就该不存在时，"不存在"什么也说明不了） |
    /// | ③ 反例与真实违规同形态 | 反例就是**修复前那一支**（两种口径共用同一段 `create(true)`），不是另造一个形状 |
    /// | ④ 锚唯一 | 只落在"这次打开之后路径还在不在"这一个可观测事实上 |
    ///
    /// ⚠️ 与 [`readonly_open_does_not_require_write_permission`] **是两条判据**（不许互相冒充）：
    /// 那条管"**已有的**账本写不了时读还读不读得成"，本条管"**不存在的**账本不许被读出来"。
    #[test]
    fn readonly_open_never_creates_a_ledger() {
        let d = sandbox("nocreate");
        let lp = d.join("ledger.jsonl");
        let _sb = Sandbox {
            dir: d.clone(),
            file: lp.clone(),
        };
        assert!(!lp.exists(), "夹具前提：这个路径一开始必须不存在");

        // ① 只读口径必须打得开：**新世界也要能 `check`**（`check.sh` ② 就是在空沙箱上跑 `check`）。
        let l = Ledger::open_readonly(&lp).expect("只读口径在一个不存在的账本上也必须打得开");
        // ② ★ 判据：**一个字节都不许落盘**
        assert!(
            !lp.exists(),
            "只读口径**不得创建**账本——盘上那个 0 字节文件就是这次『读』留下的副作用"
        );
        // ③ 它读到的是**零条事件的空世界**（不是"打开了个坏东西"）
        assert_eq!(l.last_seq(), 0, "账本不在场 ⇒ 零条事件");
        assert!(
            l.read_from(1).unwrap().is_empty(),
            "账本不在场 ⇒ 读回必须是空的"
        );

        // ④ 正控（同夹具、必红）：**写**口径在**同一个路径**上必须把它建出来。
        {
            let mut w = Ledger::open(&lp).expect("写口径（初始化动作）必须能创建账本");
            assert!(lp.exists(), "正控：写口径必须建出账本（否则②恒真）");
            w.append(ev(1)).unwrap();
        }
        let l2 = Ledger::open_readonly(&lp).expect("建出来之后只读口径必须打得开");
        assert_eq!(l2.last_seq(), 1, "建出来之后，只读口径必须读到那一条");
    }
}
