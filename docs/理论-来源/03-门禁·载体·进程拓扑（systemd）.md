# 03 · 门禁·载体·进程拓扑（systemd）—— 来源索引

> **本件范围**：把退役料里这一块的精华凝练成一张来源索引 —— **三进程切法与「进程边界画在权限变化处」、静态墙与属主编排（含口属主／`SocketUser=` 没落到盘上的根因）、一个口的四个坐标与许可来源、单元配置与沙箱档位（哪一档会静默失效）、可续读与失败语义、载体执行器为什么并入本工程、systemd 侧的逐字事实**。
> **边界声明**：本夹是**来源索引／来源料**，**不是契约，也不是第二权威**。它与现行件冲突时**以现行件为准** —— 冲突逐条列在《与现行件的冲突》一节。
> **本件只回答「这句话原来出自哪、现在归谁」**：它不自立规范句；凡要引规范，就明写「出处＝现行件 X §Y」。
> **出处纪律**：每条出处都是本席亲自读过的原文（件名 ＋ 节）。核不到的写「无法判定」并给原因；本件不写「逐字」去转述别人的转述。
> **不引行号**：退役料里那些 `main.rs` 行号按本件纪律不引（行号会烂），改引节名或现行件坐标。
> **坐标简写**：下表「现在归谁」里的 `S0-立项/`、`S2-设计/` 指 `docs/` 下同名目录；`deploy/`＝`deploy/`，`tools/`＝`scripts/`，`specs/`＝`ninedim/01-意图环/04-规格/`。

---

## 一、三进程切法与「进程边界画在权限变化处」

本节只收「为什么切成三个进程、按什么判」；逐进程装载哪些模块、各占什么身份，见现行件 `S2-设计/设计-WC-MODREG-001-v0.1.md` §2.4。

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **三进程＝内核／投影服务／载体执行器；切法的判据是「权限与可达面差异」，不是「功能内聚」** | 《研究-归位-2026-10-06\world-core-topology-research\world-core-进程拓扑对标调研.md》§一 结论 10；《研究-归位-2026-10-06\research\SYSTEMD_FOR_WORLD_CORE.md》§一 结论 2 | `S2-设计/设计-WC-ARCH-001-v0.1.md` §二 表、§2.1；`S2-设计/设计-WC-MODREG-001-v0.1.md` §2.4 |
| **内核／账本不拆（唯一写者，进程边界即门禁边界）；两个只读投影可拆（收益＝独立重启追赶）；载体适配器要拆（权限隔离）** | 同上（《world-core-进程拓扑对标调研.md》§一 结论 10） | `设计-WC-ARCH-001-v0.1.md` §2.1 候选切法表；`设计-WC-MODREG-001-v0.1.md` §2.4 |
| **拆分判据三条：① 需要不同的权限／capability ② 需要不同的生命周期与重启策略 ③ 需要与 PID 1 解耦以便独立崩溃重启；三条都有源码级证据** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 2 | `设计-WC-ARCH-001-v0.1.md` §2.1；`deploy/README.md` §一 |
| **核心进程「零外部资源」：逐字 `never accesses any external resources other than those passed in either via the command-line or the controller interfaces`（不含文件系统访问、不含 `nss(5)` 调用、不含外部进程通信）——这比「承诺不去访问」强一个量级** | 《world-core-进程拓扑对标调研.md》§一 结论 1（引 dbus-broker 判据原话） | `设计-WC-ARCH-001-v0.1.md` §A-5「两条经实证确认的做法」1 |
| **`systemd-executor` ＝「同一套代码、两种进程形态」的官方先例；它的配置经 memfd 序列化传递，二进制本身被 fd 钉住以防升级期间不一致** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 3、结论 4 | `设计-WC-ARCH-001-v0.1.md` §A-2 先例一、§二「三个进程都是一体两面的同一份代码」 |
| **拆进程的前置条件＝存在一个「能接得上进度」的接口；没有它，拆进程只会变成丢事件** | 《world-core-进程拓扑对标调研.md》§一 结论 5 | `设计-WC-ARCH-001-v0.1.md` §三「三条线的可续读性」 |
| **可续读位点的归属要二选一并写进契约（服务端持位点／消费端自持），它直接决定「删掉检查点无后果」能否成立** | 《world-core-进程拓扑对标调研.md》§一 结论 6 | `设计-WC-ARCH-001-v0.1.md` §三 消费线；`S2-设计/设计-WC-IC-001-v0.1.md` §5.8 |
| **投影独立的正当理由写成「删掉无后果、可独立重启追赶」，而不是「故障隔离」——两块只读投影本来就不写世界** | 《world-core-进程拓扑对标调研.md》§一 结论 5 | `设计-WC-ARCH-001-v0.1.md` §2.1 投影行、§4.4 失败语义 |
| **身份只从内核取；取不到身份时降级为只读，而不是放行**（引 Tailscale `ipnauth.go` 的 `IsReadonlyConn()`：`creds == nil` ⇒ `logf("connection from unknown peer; read-only")` 并返回只读） | 《world-core-进程拓扑对标调研.md》§一 结论 2 | `设计-WC-ARCH-001-v0.1.md` §A-5「已核实的三条对标结论」2（现行件把「降级为只读」登记为待人裁，非已定） |
| **客户端自送的「可信字段」要被显式忽略，而不是被校验**（journald 逐字 `Clients should not send them — if they do anyway, they will be ignored.`） | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 6；《world-core-进程拓扑对标调研.md》§一 结论 3 | `设计-WC-ARCH-001-v0.1.md` §三 线①「身份从哪来」 |
| **身份要用 pidfd，而不是 `(pid, start_time)`；三家独立收敛到同一结论**（D-Bus 源码注释明文禁止「先取 PID 再反查 uid」，给出 TOCTTOU／PID 复用／fd 传递三条攻击；systemd 用 `SO_PEERPIDFD` ＋ augmented mask） | 《world-core-进程拓扑对标调研.md》§一 结论 3c | `S2-设计/设计-总线该实现什么-合并清单-v0.1.md` §6（两条路显式择一，今天未择）；`S0-立项/策划-WC-SCMP-001-v0.1.md` T-21／B-6（登记为风险与处置建议，未落地） |

---

## 二、门禁不可绕过：静态墙、属主编排与口属主

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **口属主没落到盘上的根因＝`world-core.service` 有 `RuntimeDirectory=world-core`，而口路径 `/run/world-core/omarchy.sock` 正好在该目录【里面】；systemd 以 root（降权前）把该目录【以下】一切递归 chown 成服务的 `User=`——后一趟是成功路径，不报错** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§6.1 | `deploy/README.md` §八 1；`tools/socket_uid_guard.py` 件头 S-01…S-03 |
| **沙箱直读：口 965→963、inode 前后不变、mode 仍 600、ctime 变而 mtime 不变 ⇒ 是就地 chown，不是 unlink＋rebind** | 同上件 §四 | `tools/chown_plus_guard.py` 件头；`tools/socket_uid_guard.py` 判据 S-02 |
| **能兑现身份的三种写法：(a) 把口挪出 `RuntimeDirectory=` 目录＝成立；(b) 普通 `ExecStartPre` 自己 chown＝不成立（跑在已降权身份下、被后一趟递归 chown 静默盖掉、服务仍报 success）；(c) `ExecStartPre=+/bin/chown …`＝成立（以完全权限跑、排在递归 chown 之后）** | 同上件 §6.3 | `tools/chown_plus_guard.py` 判据 P-01…P-04 |
| **字符级的坑：`+` 与命令之间多一个空格 ⇒ `LoadState=bad-setting`、整单元拒启、口根本建不出来；而 `systemd-analyze verify` 那两次退出码都是 `0` ⇒ 判据要认字样、不许认 rc** | 同上件 §6.3 末（两个字符级的坑） | `tools/chown_plus_guard.py` 判据 P-01（认 `+` 前缀） |
| **两类要分开读：一类会喊（键不认，逐字 `Unknown key …, ignoring.`）／一类不喊（配了不生效）；`SocketUser=` 属后者，systemd 一句警告都没打** | 同上件 §五；`deploy/README.md` §八 两条形态登记 | `deploy/README.md` §八 末两条形态登记 |
| **口在同目录内 ⇒ 最终属主由服务的 `User=` 决定，不由 socket 单元的 `SocketUser=` 决定；且 `SocketUser=` 只在 `[Socket]` 上、`SocketPort` 没有该字段 ⇒「一单元多条 `ListenStream=` 各口不同属主」机制上堵死** | 同上件 §6.2 | `deploy/world-core-omarchy.socket` 的 `Service=`；`tools/carrier_contract.py` 判据② |
| **申报 ≠ 授权：法律里写了 `owner` 名字、或单元件里写了 `SocketUser=`，都不产生任何通行；真正产生「只有它能连」的是套接字文件的属主与模式** | 《规程-接入载体.md》§3 第 3 条 | `设计-WC-ARCH-001-v0.1.md` §4.3 表；`specs/gate-enforcement/spec.md` §「门禁配置在被管者不可写的域」 |
| **一个口一个系统用户：已裁「要」；在改完之前口只是标签 —— 身份区分靠「协议自称 ＋ 许可」，不是内核强制的隔离** | 《规程-接入载体.md》§3 第 5 条 | `tools/socket_uid_guard.py` 判据 S-02；`deploy/README.md` §八 1 |
| **AC-1：受理路径的许可来源不是法律 —— 不在法律里、但在渲染物里的口 ⇒ 实得 `rc=0` 且套接字被建立；对偶反例：在法律里、但不在渲染物里 ⇒ `rc=2` `ext.world.Channel.NotConfigured`** | 《规程-接入载体.md》§5 AC-1；《证据-接入载体-2026-10-05.md》§3 反例现取（A／B 两例） | `tools/carrier_contract.py` 件头「射程」；`specs/gate-enforcement/spec.md` §「门禁配置在被管者不可写的域」 |
| **静态读数：`policy.json` 的 `listeners` 在 `src/**` 里零读者；受理路径读的是 `--channel` 渲染物；`owner` 那一格零命中（死格）** | 《证据-接入载体-2026-10-05.md》§2 表 2.1／2.2／2.3 | `tools/render_channel.py` 件头；`src/gate/policy.json` 的 `_listeners_note`；`设计-WC-IC-001-v0.1.md` §5.9 |
| **`owner`（名字）→ `uid`（数字）之间没有权威解析者；机器上没有 `dsh` 用户 ⇒ 没有 uid 可填 ⇒ 渲染物里就少一条** | 《规程-接入载体.md》§3 第 4 条 | `tools/gen_owner_uid.py`（生产者）；`tools/render_channel.py`（消费者） |
| **AC-6 三条硬口径：映射里多一条法律没有的 socket ⇒ 红；法律里的口没有行 ⇒ 红；`null` ＝「在册未上线」（合法、不红、但报出来）；把「查不到」写成 `0` 不在允许之列 —— chown 到 root 是提权** | 《规程-接入载体.md》§8.3 | `tools/gen_owner_uid.py` 件头「口径」1–4（含负控自测） |
| **「唯一载体」＝`deploy/listener_uids.json`，形状 `{"channel":1,"uids":{"<socket 绝对路径>":<uid 整数或 null>}}`，法律里不存这个数（uid 是部署面的数）** | 《规程-接入载体.md》§8.3 | `tools/gen_owner_uid.py` 件头；`tools/render_channel.py` §「`deploy/listener_uids.json` 的形状」 |
| **AC-2 渲染物 ⊆ 法律：执行体＝判据⑧／⑨；两条弱化要同写 —— ① 该工具是否在那条唯一门禁命令里 ② 覆盖面只到纸面（`deploy/` ↔ 法律 ↔ 渲染物），不覆盖 systemd 单元在位与 `ss` 实际监听** | 《规程-接入载体.md》§5 AC-2、§7 末 | `tools/carrier_contract.py` 判据⑧／⑨ 与件头「射程」；`check.sh` 的 `run_tail 14 "载体契约（部署面单元 ≡ 设计＋法律）"` |
| **AC-4 弱化不许粉饰：只要某条口的 `uid` 那一格没有权威来源，凡是把「身份是内核强制的」写进描述该口的件里，就是 AC-4 的反例；今天的强度＝自称 ＋ 许可** | 《规程-接入载体.md》§5 AC-4、§3 第 5 条 | `deploy/README.md` §八 1 |
| **三处「在册」要分清：法律（唯一在册）／渲染物（下游生成物，不是第二权威）／单元件（下游生成物，既不是「在册」也不是「已上线」）；当时三处清单不同步不会红** | 《规程-接入载体.md》§1.1、§4 第 2 条 | `tools/carrier_contract.py` 判据⑪／⑪c；`deploy/README.md` §七 判据表 |
| **清单的唯一来源＝`deploy/install.sh` 的 `UNITS=` 变量；「清单 ≡ 实际」那条判据在退役料写作时尚未写** | 《规程-接入载体.md》§8.4 | `deploy/install.sh` 的 `UNITS=` 变量；`tools/carrier_contract.py` 判据⑪（见《与现行件的冲突》） |
| **安装脚本不把「没装」读成「合规」：缺文件时的内容类判据显式不判** | 《规程-接入载体.md》§4 第 5 条 | `deploy/install.sh` 的 `verify()` |
| **部署面与仓面不一致时以仓面为准并上报，不许擅自同步** | 《规程-接入载体.md》§0 末、§4 第 4 条 | `deploy/README.md` §八 5；`tools/chown_plus_guard.py` P-02／P-03 |

---

## 三、接入载体：一个口的四个坐标与许可来源

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **一个口有四个坐标：在册（`policy.json.listeners`）／渲染（`--channel` 指向的件）／单元（systemd）／实际监听（内核 `ss -xl`）；四个都要取，少一个就会读错** | 《规程-接入载体.md》§2 | `tools/carrier_contract.py` 判据⑦⑧⑨⑩；`deploy/README.md` §六 判据表 |
| **缺坐标 1 ⇒ 把「没声明过」读成「合法」；缺坐标 2 ⇒ 把「法律写了」读成「世界会受理」；缺坐标 3 ⇒ 把「单元件在仓里」读成「上了线」；缺坐标 4 ⇒ 把「在册」读成「在跑」** | 《规程-接入载体.md》§2 表「缺它会把什么读错」列 | `deploy/README.md` §六；`tools/carrier_contract.py` 判据⑨（报告行、不判红） |
| **读坐标 4 的纪律：`ps`／`pgrep` 不许按命令行字样匹配（观测行为会进入被观测面）；对策＝按可执行名，或显式排除自身 PID 与祖先** | 《规程-接入载体.md》§2 末；《证据-接入载体-2026-10-05.md》§4 两处失手 | 未定（原因：本席在 `` 扫描面内未见承载该纪律的会红判据，见《无法判定与未取到的》第 3 行） |
| **唯有法律那一处是在册的权威；渲染物与单元件只许作为下游被核对，不许作为权威被读** | 《规程-接入载体.md》§1.1 | `tools/carrier_contract.py` 判据⑧；`src/gate/policy.json` 的 `_listeners_note` |
| **法理面（宿主工作区的 `policy.json` 的 `listeners`）与现役面（`/etc/` ＋ systemd ＋ `/run/`）要分开问；两问答案不同时判据红，而退役料当时只登记、不修这个差** | 《规程-接入载体.md》§1 | `deploy/README.md` §六、§八 5（「部署件 ≡ 仓」无执行体） |
| **服务端当时只能接一个口：`cmd_serve` 只取 fd 3；`fds.n > 1` 时打一行 `ext.world.Serve.ExtraListenFds` 登记、不静默忽略、也不受理** | 《证据-接入载体-2026-10-05.md》§2 表 2.6 | `deploy/README.md` §八 2、3 |
| **门禁当时不核渲染物、对 `dsh` 那条口完全沉默（当时 `UNITS` 4 份、不含 `world-core-dsh.socket`）** | 《证据-接入载体-2026-10-05.md》§2 表 2.4／2.5 | `deploy/install.sh` 的 `UNITS=`（现含 `world-core-dsh.socket`，见《与现行件的冲突》）；`tools/carrier_contract.py` 判据⑧ |
| **AC-3：「在册未上线」要单独报出，不许被读成「已上线」；退役料时点读数＝在册 2／渲染 1 ⇒ 报出 `/run/world-core/dsh.sock`** | 《规程-接入载体.md》§5 AC-3 | `tools/carrier_contract.py` 判据⑨（报告行、不判红） |
| **宿主没有 `bash`／`sh`／`cargo`／`rustc`／`rustfmt` ⇒ 门禁只能在 VM 跑；且不许碰 `/etc`，改 systemd 单元属现役载体、须部署方动手** | 《规程-接入载体.md》§6 第 3、4 条；§0 末 | `check.sh`（机核入口）；`deploy/install.sh`；`deploy/README.md` §六 |
| **本件不能证明的：现役二进制与哪一份源码对应（VM 树不是 git 仓 ⇒ 取不到提交号）；别的机器上也这样；「实际监听 ⊆ 在册」在所有时刻成立；`check.sh` 今天是绿的** | 《证据-接入载体-2026-10-05.md》§5 第 1–3、5 条 | 未定（原因：这些是射程声明，不是可交付结论） |

---

## 四、单元配置与沙箱档位（哪一档会静默失效）

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **「尽力而为」档的沙箱设置，在底层安全机制不可用时会被静默关掉**（逐字 `Note that many of these sandboxing features are gracefully turned off on systems where the underlying security mechanism is not available.`） | 《根报告-归位-2026-10-06\systemd-verbatim-facts.md》§C0、§C14 | `deploy/world-core.service`「内核语义类约束」段注释；`设计-WC-ARCH-001-v0.1.md` §A-5 |
| **「门禁不可绕过」不建立在这一档设置上，而建立在内核语义类设置（身份、权限、系统调用过滤）与进程边界上** | 同上件 §C0；《world-core-进程拓扑对标调研.md》§一 结论 1 | `设计-WC-ARCH-001-v0.1.md` §A-5 末段（反面教训两条） |
| **`ProtectSystem=`／`ReadOnlyPaths=`／`InaccessiblePaths=` 不能用来锁「谁能连本机套接字」；套接字的可达面由 socket 单元的属主／属组／模式决定** | 《研究-归位-2026-10-06\systemd-research\REPORT.md》§7 第 6 条 | `deploy/world-core.service` 的 ⚠️ 注释；`deploy/world-core.socket` |
| **`SocketMode=` 默认 `0666`（逐字 `Defaults to 0666.`）；`SocketUser=`／`SocketGroup=` 逐字 `all AF_UNIX sockets, FIFO nodes, and message queues are owned by the specified user and group`（version 214）——默认组合是「谁都能连」，收窄来自属组与父目录权限** | 《根报告-归位-2026-10-06\readonly-truth-consumption-report.md》§5；《systemd-research\REPORT.md》§8 表 | `deploy/world-core.socket`；`tools/carrier_contract.py` 判据⑥ |
| **「文档是否警告这是唯一访问控制」＝**未能核实／不存在**：作者自述通读 `systemd.socket.html` 全文无任何安全警告；最接近的风险提示只出现在消费方（Docker／Podman）文档里** | 《readonly-truth-consumption-report.md》§5「诚实的回答」与「核实程度」 | 未定（原因：本席未独立 fetch 该页复核，见《无法判定与未取到的》第 6 行） |
| **`SocketMode=` 在创建文件节点时生效，避免「先创建再 chmod」之间的竞态窗口；这比应用自己 chmod 更不容易出 TOCTOU** | 《readonly-truth-consumption-report.md》§5「能从它抄什么」第 1 条 | `deploy/world-core.socket`；`设计-WC-ARCH-001-v0.1.md` §4.3「通道套接字文件」行（见《与现行件的冲突》） |
| **`Accept=` 默认 `no`（所有连接交给同一个服务实例）；`PassCredentials=`／`PassSecurity=` 默认 `false`，而 journald 出厂 unit 把它们显式打开为 `yes`** | 《systemd-research\REPORT.md》§8 表 | `deploy/world-core.socket`（`Accept=no`） |
| **依赖与顺序正交往**（逐字 `those settings are independent of and orthogonal to the requirement dependencies`）：`After=`／`Before=` 是顺序，`Requires=`／`Wants=`／`BindsTo=` 是需求 | 《systemd-verbatim-facts.md》§D「The orthogonality statement」 | `deploy/README.md` §一、§三；`deploy/world-core.service` 的 `Requires=`／`After=` |
| **`Type=notify` 让服务自己决定「我准备好了」的时刻；官方实际说的是 `Type=exec` 更适合长驻服务 —— 退役料明确标注「`notify` 优于 `simple`」那一句未能核实** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 10（含措辞澄清） | `deploy/world-core.service`（`Type=notify`／`NotifyAccess=main`） |
| **`WatchdogSec=` 的值会经 `$WATCHDOG_USEC` 传给服务；进程侧不报到会被反复重启** | 《systemd-verbatim-facts.md》§F | `deploy/world-core.service`（`WatchdogSec=30s`）；`deploy/README.md` §八 4 |
| **状态目录与配置目录的属主分野**（逐字 `Except in case of ConfigurationDirectory=, the innermost specified directories will be owned by the user and group specified in User=`） | 《systemd-verbatim-facts.md》§A3 | `deploy/world-core.service`（`StateDirectory=`／`ConfigurationDirectory=` 及其注释） |
| **`DynamicUser=` 的 UID 回收不用于需要长期身份的场景**（回收后同一数字在不同时间指向不同主体 ⇒ 重放不再唯一） | 《SYSTEMD_FOR_WORLD_CORE.md》§4.5；《world-core-进程拓扑对标调研.md》§一 结论 2 | `deploy/README.md` §八 6；`设计-WC-ARCH-001-v0.1.md` §4.3「主体的身份」行 |
| **`RuntimeDirectory=` 的递归 chown 会静默覆盖 `SocketUser=`；兑现写法＝`ExecStartPre=+/bin/chown …`** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§6.3；`deploy/README.md` §八 形态二 | `deploy/world-core.service` 的 `[Service]` 段 `ExecStartPre=` 两条；`tools/chown_plus_guard.py` |
| **socket activation：「服务挂了但请求不丢」是内核在扛 —— bind＋listen 由服务管理器完成并在服务重启期间保持打开，未 accept 的连接由内核 backlog 排队；服务管理器不实现自己的请求队列** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 5 | `deploy/world-core.socket`；`deploy/README.md` §一「为什么套接字单独一份单元」 |
| **varlink 故意不做 fd 传递，账本 fd 交接要走 `SCM_RIGHTS`／`sd_listen_fds`，不能用 varlink** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 9 ⚠️ | `设计-WC-ARCH-001-v0.1.md` §三；`deploy/world-core.socket` |
| **journald 的防篡改是「检测」不是「防止」，而且默认没开**（要手工 `journalctl --setup-keys` 才有密钥，`Seal=` 才生效） | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 7 | `specs/ledger-integrity/spec.md` §「摘要链检出局部篡改，并如实声明其边界」 |
| **`FileDescriptorStorePreserve=` 在本机 systemd 上键不认（逐字 `Unknown key …, ignoring.`）；而 `Restart=` 触发的重启保留 fdstore、`systemctl stop`＋`start` 不保留** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§五；《SYSTEMD_FOR_WORLD_CORE.md》§附 单元文件模板 | `deploy/README.md` §二、§八 末「形态一」；`deploy/world-core.socket`（`FileDescriptorStorePreserve=no`） |

---

## 五、可续读与失败语义

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **「能接得上进度」是拆进程的前置条件；没有它，拆进程只会变成丢事件** | 《world-core-进程拓扑对标调研.md》§一 结论 5 | `设计-WC-ARCH-001-v0.1.md` §三「三条线的可续读性」 |
| **位点归属二选一要先定、再定进程数；它决定「删掉检查点无后果」能否成立** | 同上件 §一 结论 6 | `设计-WC-ARCH-001-v0.1.md` §三 消费线；`设计-WC-IC-001-v0.1.md` §5.8 |
| **取不到身份时降级为只读，而不是放行**（Tailscale 模板：`creds.UserID()` 失败同样返回只读；只读被定义为 `IsUnprivileged`） | 同上件 §一 结论 2 | `设计-WC-ARCH-001-v0.1.md` §A-5「已核实的三条对标结论」2（登记为待人裁） |
| **身份一次钉住、之后就信这一份**：连接建立时取一次 `SO_PEERCRED` 存进结构体，后续授权读缓存；peer 声称的 uid 只允许与 kernel uid 相等（逐字 `if (!b->anonymous_auth && u != b->ucred.uid) return 0;`） | 《systemd-research\REPORT.md》§6 第 1、2 条 | `设计-WC-ARCH-001-v0.1.md` §A-5「已核实」2；`设计-WC-IC-001-v0.1.md` §5.9「跨进程时的身份」 |
| **`SCM_CREDENTIALS` 在 wire 上不可信**（sd-bus 接收侧根本不解析它，只处理 `SCM_RIGHTS`／`SCM_PIDFD`）；除非 socket 上明确开了 `SO_PASSCRED`，此时内核会覆盖并保证其真实性 | 《systemd-research\REPORT.md》§7 第 3 条 | 未定（原因：本席在现行仓受理路径未见承接，见《无法判定与未取到的》第 5 行） |
| **不能用 `/proc/` 补齐的字段做授权**（`sd_bus_creds_get_augmented_mask` 文档已明文禁止；逐字 `augmented fields are unsuitable for authorization decisions`） | 《systemd-research\REPORT.md》§7 第 4 条；《world-core-进程拓扑对标调研.md》§一 结论 3c | 未定（原因：同「身份要用 pidfd」一行，属已登记未落地） |
| **「世界不能处于半成品状态」的答案是 `Type=notify` ＋ 显式 `After=`／`Requires=` 分离** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 10 | `deploy/README.md` §三；`设计-WC-ARCH-001-v0.1.md` §4.1 |
| **`journald` 的可信字段靠「下划线前缀由接收侧隐式添加」，且与「唯一写入口＋字段可信性」同形：把「谁说的」和「说了什么」在协议层就分开** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 6 | `specs/envelope-validation/spec.md` §「信封的必填字段被逐字段强制」；`设计-WC-ARCH-001-v0.1.md` §三 线① |
| **「先请求、后执行、再报结果」是带副作用动作的通行三段式；本工程在纯事件溯源下的实现＝意图先落账本、结果后落账本** | 《world-core-进程拓扑对标调研.md》§三 第二家（Tailscale ＋ journald）；`shell-最小样板-2026-10-05\README-最小样板.md` §二 图（点击 → 唯一写入口 → 世界裁决落账 → 重读 → 才重画） | `设计-WC-ARCH-001-v0.1.md` §3.1；`设计-WC-IC-001-v0.1.md` §5.10 不变量⑤ |
| **样例实测：点一下「应被接」的那一颗 ⇒ 口通了、世界接了，但门禁判否 `ext.world.World.PresenceNotDeclared`，并把这个拒绝本身落成了一条 `notice`（`act` 计数 28→28，`notice` 6→7）** | 《shell-最小样板-2026-10-05\README-最小样板.md》§四 表「点（应被接）」行、两条已成立事实 | `specs/gate-enforcement/spec.md` §「每一个写动作都过门禁」；`设计-WC-ARCH-001-v0.1.md` §3.1（拒绝也要留痕） |
| **样例实测：把账本指到一个不存在的路径 ⇒ rc=3、stdout 0 B、stderr「离线：账本不在」、且没有造出真相文件** | 同上件 §四 表「读失败」行 | `设计-WC-ARCH-001-v0.1.md` §4.4（投影服务报「读不到真相」） |
| **三条不许破 —— ① 壳不持状态 ② 不许先改界面再传回去（不乐观更新）③ 唯一写入口（绝不 `open(ledger,'a')`）；破任一条，投影就变套壳** | 同上件 §三 | `specs/projections/spec.md` §「读法是叶子」；`设计-WC-ARCH-001-v0.1.md` §三 线①③ |
| **「界面以自己的身份说话」在账本上成立：那条新事件的 `actor` 逐字是 `world://presence/omarchy`（不是 `world://core`）** | 同上件 §四 两条已成立事实 1 | `设计-WC-ARCH-001-v0.1.md` §三 线①；`设计-WC-IC-001-v0.1.md` §5.9 |
| **「界面自己的身份」也不能靠乐观更新撑：点一下只发请求，世界回执之前什么都不算数** | 同上件 §三 ② | `specs/write-side-adaptation/spec.md` §「写侧只写，不裁决」；`设计-WC-ARCH-001-v0.1.md` §3.1 |

---

## 六、载体执行器为什么并入本工程

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **载体适配器要拆进程：权限隔离是第一理由**（调研原文把 kubelet 需特权列为反面） | 《world-core-进程拓扑对标调研.md》§一 结论 10 | `设计-WC-ARCH-001-v0.1.md` §2.1 载体执行器行、§五；`设计-WC-MODREG-001-v0.1.md` §2.4 |
| **不能借鉴、要自己写的四件：帧面／说法面／撤回语义／许可裁决**（理由：引入别人的封套＝两套必填属性＝两个权威；许可裁决的权威在世界，判定搬到总线或外部服务的方案出局） | 《落实程序-可借鉴实现与落点.md》§5 | `设计-WC-ARCH-001-v0.1.md` §五；`设计-WC-IC-001-v0.1.md` §5.10 |
| **已有可直接接的落点**：`src\channel.rs`（帧面、消息模型、口径身份 `0600`＋`chown`、`Impersonation` 拒绝）／`src\guard.rs`（载体侧限制，Landlock 等）／`src\lib.rs`（唯一写入口 `commit`） | 同上件 §3.1 | `S2-设计/设计-WC-MODREG-001-v0.1.md` §2（M05／M09／M10） |
| **要新增／要改的落点**：`describe.rs`／`subscription.rs`／`channel.rs` 加分派／`base_seq` 强制／`retract` 独立成方法；每一步的「会红」判据逐条给出 | 同上件 §3.2、§4 | `specs/write-side-adaptation/spec.md`；`设计-WC-IC-001-v0.1.md` §5.10 |
| **分阶段的真正阻塞被写死为两条：「读许可」与「身份映射入法」** | 同上件 §4 阶段三、附录 B 第 3 条 | `tools/gen_owner_uid.py`；`tools/render_channel.py`；`src/gate/policy.json` 的 `_listeners_note` |
| **本件不能证明任何一条已实现**：§3.2 那张表全是「要新增／要改」；本机无 `cargo`／`rustc`，没跑过一次构建；行数是现取的，但「抄过来能编译」没人验过 | 同上件 附录 B 第 1、2 条 | `check.sh`；`deploy/README.md` §八 3 |
| **`agentd` 的门禁／沙箱逻辑可以先做成「同一个二进制的第二个入口」，成熟后再决定是否物理拆进程** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 3 | `设计-WC-ARCH-001-v0.1.md` §二（同一可执行文件按子命令进入不同形态）；`deploy/world-core-actd.service`（`carrier serve`） |

---

## 七、systemd 侧逐字事实（上游参考，不作本项目结论）

本节只登记**外部事实的字面**与它的现行落点。这些字面取自退役料里的核实报告，而核实报告读的是上游 systemd 手册与源码；**上游手册副本**（`研究-归位-2026-10-06\research\src\docs\*.md`）本席**未逐件通读，故不据它们立任何结论**。

| 结论（一句话，加粗） | 出处（退役料件名 ＋ 节） | 现在归谁（现行仓载体） |
|---|---|---|
| **`SocketMode=` 默认 `0666`；`SocketUser=`／`SocketGroup=` 管「所有 AF_UNIX socket、FIFO 节点与消息队列」的属主** | 《systemd-research\REPORT.md》§8 表 | `deploy/world-core.socket` |
| **「很多沙箱特性会在底层安全机制不可用时被优雅关掉」** | 《systemd-verbatim-facts.md》§C0、§C14 | `deploy/world-core.service` |
| **「除 `ConfigurationDirectory=` 外，最内层指定目录归 `User=` 与 `Group=`」** | 同上件 §A3 | `deploy/world-core.service` |
| **「顺序设置与需求依赖相互独立、正交」** | 同上件 §D「The orthogonality statement」 | `deploy/world-core.service` 的 `Requires=`／`After=` |
| **「套接字在重启期间保持绑定可达，而所有请求在守护进程无法处理时被排队」** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 5 | `deploy/world-core.socket` |
| **「以 `_` 开头的键……客户端不该发它们——若发了，它们会被忽略。」** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 6 | `设计-WC-ARCH-001-v0.1.md` §三 线① |
| **「augmented 字段不适合用于授权决定」** | 《systemd-research\REPORT.md》§7 第 4 条；《world-core-进程拓扑对标调研.md》§一 结论 3c | 未定（原因：现行仓受理路径未见承接） |
| **「允许服务程序代码精确安排何时认为服务已成功启动、何时继续后续单元」** | 《SYSTEMD_FOR_WORLD_CORE.md》§一 结论 10 | `deploy/world-core.service`（`Type=notify`） |
| **「未知键……忽略。」——这是「会喊」那一类的逐字样态；与之相对的是「配了不生效且沉默」** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§五；`deploy/README.md` §八 两条形态登记 | `deploy/README.md` §八 末 |
| **systemd 把「快照／状态」的服务对象定义为「程序」而非「语义对象」——语义对象不在它的模型里** | 《SYSTEMD_FOR_WORLD_CORE.md》§4.8 | `设计-WC-ARCH-001-v0.1.md` §五（语义层与载体层两层能力表） |
| **「转发即降级」的 stdout／stderr 路径不要抄进可信层** | 《SYSTEMD_FOR_WORLD_CORE.md》§4.4 | `设计-WC-ARCH-001-v0.1.md` §5.2（结构化日志并入账本，系统日志只留镜像） |

---

## 与现行件的冲突

本节只写「退役料如此、现行件如此 ⇒ **以现行件为准**」；现行件坐标逐个给出。本席**未跑**任何现行仓门禁，故下列「现行件如此」是**读件的字面**，不是运行态读数；运行态现值以对应工具现取为准。

| 冲突点 | 退役料如此（件 ＋ 节） | 现行件如此（坐标）⇒ **以现行件为准** |
|---|---|---|
| **`tools/carrier_contract.py` 在不在那条唯一门禁命令里** | 《规程-接入载体.md》§5 AC-2 第②条弱化、§7 末：「该工具不在 `check.sh` 里（`grep -n carrier check.sh.new` 零命中）⇒ 它的红绿不影响那条唯一的门禁命令」 | 现行件 `check.sh.new` 已有那一步：`run_tail 14 "载体契约（部署面单元 ≡ 设计＋法律）" python3 tools/carrier_contract.py` ⇒ **以现行件为准** |
| **投影服务单元 `world-core-projectd.service` 的处置** | 《规程-接入载体.md》§8.4：「单元件本体保留不删：它是未跟踪件（无 git 历史 ⇒ 没有解析根）⇒ 现状＝在目录里、不在清单里＝未启用；要启用它，先把 `project serve` 落实现」 | 现行件 `deploy/README.md` §一、§四：「**已退役**（工作树移除）」，并给出解析根 `git show deafbae:deploy/world-core-projectd.service`；现行 `deploy/` 目录里已无该单元件 ⇒ **以现行件为准**（设计要求仍在，属「设计已定·未落地」） |
| **盘上口属主的现值** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§11.2（时点 `2026-10-05T16:00:09`，VM 钟）：`/run/world-core/omarchy.sock` 属主＝`omarchy:omarchy`(963) | 现行件 `deploy/README.md` §八 1 记 T29 现取＝`world-core:world-core`，并据此写「单元级 `SocketUser=` 这条路今天做不到每口各自的属主」⇒ **以现行件为准**；两读数**时点不同**，现值以 `tools/socket_uid_guard.py` 判据 S-02 现取为准 |
| **`ExecStartPre=+/bin/chown …` 在不在仓内** | 《根因-口属主-SocketUser未落到盘上-2026-10-05.md》§11.5：「仓内 `deploy/world-core.service` 现取【没有】这一行 ⇒ 盘上漂移」 | 现行件 `deploy/world-core.service` 的 `[Service]` 段现有两条 `ExecStartPre=+/bin/chown …`（`omarchy:omarchy` 与 `dsh:dsh`）⇒ **以现行件为准**；盘↔仓双向一致性以 `tools/chown_plus_guard.py` 判据 P-02／P-03 现取为准 |
| **「清单 ≡ 实际」那条判据写没写** | 《规程-接入载体.md》§8.4：「`carrier_contract.py` 的 `UNITS` 尚未改成从 `install.sh` 派生，『清单 ≡ 实际』判据（⑪）尚未写 ⇒ 今天三处仍不一致，不许写成『已统一』」 | 现行件 `deploy/README.md` §七 判据表已有 ⑪「清单 ≡ 实际」与 ⑪c「已登记未启用」⇒ **以现行件为准** |
| **「不在法律里的口被建立」这条漏洞的现状** | 《证据-接入载体-2026-10-05.md》§3 反例现取：`RC_A=0`，账外口被建立（时点 `2026-10-05T02:20:49+08:00`，那个二进制） | 现行件 `src/gate/policy.json` 的 `_listeners_note` 记受理期执行体＝`ChannelConfig::load_checked`（账外口拒启 `ext.world.Channel.UndeclaredListener`）；`deploy/README.md` §七 判据⑦ 同向 ⇒ **以现行件为准**；实际红绿以 `tools/carrier_contract.py` 现取为准 |
| **`deploy/listener_uids.json` 在不在盘上** | 《规程-接入载体.md》§8.3 立它为 `owner`→`uid` 映射的**唯一载体**（形状 `{"channel":1,"uids":{…}}`） | 现行件 `tools/gen_owner_uid.py` 件头与 `tools/render_channel.py` 件头承接了同一形状与生产者／消费者分工，但 `deploy/listener_uids.json` **今天不在盘上**（本席 glob `**/listener_uids.json` 零命中）⇒ **以现行件现状为准**：载体已由工具声明、实物未落 |
| **取不到身份时「降级为只读」的地位** | 《world-core-进程拓扑对标调研.md》§一 结论 2：取不到身份 ⇒ 降级为只读，不放行 | 现行件 `设计-WC-ARCH-001-v0.1.md` §A-5「已核实的三条对标结论」2 把「后一条（降级为只读）」登记为**待人裁** ⇒ **以现行件为准**（现为待人裁，非已定） |
| **`SocketMode=` 这条机制怎么用** | 《readonly-truth-consumption-report.md》§5「能从它抄什么」1：抄「服务自己不 chmod，由 supervisor 创建节点时就带上权限」——因为它在**创建节点时**生效、能避掉「先创建再 chmod」的竞态 | 现行件 `设计-WC-ARCH-001-v0.1.md` §4.3「通道套接字文件」行写的是「建后立刻收紧到 0600 并改属主到该身份」⇒ **以现行件为准**（退役料给的是机制层面的更优写法，是否采纳未见现行件明文） |

---

## 无法判定与未取到的

| 无法判定／未取到的事 | 退役料出处（件 ＋ 节） | 原因与归属 |
|---|---|---|
| **本件所有「现行件现状」都是读件的字面，不是运行态读数** | 本件自述 | 本席**未跑**任何现行仓门禁。运行态现值以命令现取为准：`python scripts/verify/carrier_contract.py --channel /etc/world-core/channel.json`；`python scripts/verify/socket_uid_guard.py --channel /etc/world-core/channel.json --rundir /run/world-core`；`python scripts/verify/chown_plus_guard.py --repo . --live /etc/systemd/system` |
| **坐标 3／4（systemd 单元在位、`ss` 实际监听）与坐标 1 的对账** | 《规程-接入载体.md》§6 第 1b、6 条：只能在**有现役载体**的机器上取，属运行态；本机取不到，且不许拿本机读数替代别机 | 未定（原因：本席无现役载体机器）。落点：`tools/carrier_contract.py` 件头已声明「实际监听 ⊆ 在册」的执行体不在该工具里 |
| **`ps`／`pgrep` 不许按命令行字样匹配这条纪律** | 《规程-接入载体.md》§2 末；《证据-接入载体-2026-10-05.md》§4 两处失手（`ps -eo … \| grep -E 'world-core\|…'` 匹配到了自己那条 `grep`） | 未定（原因：本席 grep `` 全文未见 `pgrep` 字样，即未见承载该纪律的会红判据；不写成「已防护」） |
| **身份用 pidfd 而不是 `(pid, start_time)`** | 《world-core-进程拓扑对标调研.md》§一 结论 3c | 已登记·未落地：`S2-设计/设计-总线该实现什么-合并清单-v0.1.md` §6 给出两条路（甲「文件权限就是判据」／乙「上对端凭据」）并自述要显式择一，今天**未择**；`S0-立项/策划-WC-SCMP-001-v0.1.md` T-21／B-6 把它登记为风险与处置建议。⇒ 不判「已落地」 |
| **`SCM_CREDENTIALS` 在 wire 上不可信这条** | 《systemd-research\REPORT.md》§7 第 3 条 | 未定（原因：本席在现行仓受理路径未读到承接它的代码，`` 内 `SO_PEERCRED`／`SCM_CREDENTIALS` 字样只出现在 S0 与本清单的登记里） |
| **「systemd 文档有没有警告这是唯一访问控制」** | 《readonly-truth-consumption-report.md》§5「诚实的回答」与原件的「核实程度」：作者结论是**文档中不存在此类警告**（自述通读过该页全文） | 无法判定（原因：本席**未独立 fetch** `systemd.socket.html` 复核这一句；按「不许把别处的转述当原件结论」，本件只登记作者的自述结论与其射程） |
| **上游 systemd 手册副本（约 130 份）里的规范** | 目录 `研究-归位-2026-10-06\research\src\docs\*.md` | 无法判定（原因：本席**未逐件通读**，只把它们当上游参考；本件所有 systemd 字面都经由上列几份核实报告转引，并已在《七、》一节标明） |
| **退役料里的 `main.rs` 行号** | 《规程-接入载体.md》§5 AC-1、《证据-接入载体-2026-10-05.md》§2 等（形如 `:441`／`:1283`／`:1333`） | 不引（本件纪律：引件名 ＋ 节名，不引行号）。现行件坐标改引 `src/gate/policy.json` 的 `_listeners_note` 里逐字给出的 `src/bus/mod.rs` 的 `ChannelConfig::load_checked` |
| **退役料自己声明「不能证明」的几条** | 《证据-接入载体-2026-10-05.md》§5：现役二进制对应哪一份源码（VM 树不是 git 仓，取不到提交号）／别的机器上也这样／「实际监听 ⊆ 在册」在所有时刻成立／`check.sh` 今天是绿的 | 无法判定（原因：这几条在退役料时点即已声明为射程之外，本席无现役载体机器可复取） |

---

## 扫描面

**本件读过的退役料**（全部经 Python `encoding="utf-8"` 或 read/grep 工具读入）：`规程-接入载体.md`（全文 220 行）；`根因-口属主-SocketUser未落到盘上-2026-10-05.md`（§三–§十一）；`证据-接入载体-2026-10-05.md`（全部标题 ＋ §2／§3／§4b／§5／§6）；`shell-最小样板-2026-10-05\README-最小样板.md`（§二–§六）；`落实程序-可借鉴实现与落点.md`（§3–§5 ＋ 附录 A／B）；`研究-归位-2026-10-06\systemd-research\REPORT.md`（§6–§8）；`根报告-归位-2026-10-06\systemd-verbatim-facts.md`（全部标题 ＋ §A3／§C0／§C14／§D 命中行）；`研究-归位-2026-10-06\world-core-topology-research\world-core-进程拓扑对标调研.md`（§一 结论 10 条 ＋ 全部标题）；`研究-归位-2026-10-06\research\SYSTEMD_FOR_WORLD_CORE.md`（§一 结论 10 条 ＋ 全部标题）；`根报告-归位-2026-10-06\readonly-truth-consumption-report.md`（§5、§6 开头 ＋ 全部标题）。

**本件读过的现行仓件**：`ninedim/01-意图环/03-设计/设计-WC-ARCH-001-v0.1.md`（全文 401 行）；`设计-WC-MODREG-001-v0.1.md`（§2.4–§3）；`设计-WC-IC-001-v0.1.md`（§5.9／§5.10）；`deploy/README.md`（全文 286 行）；`deploy/install.sh`（`UNITS=` 变量）；`deploy/world-core.service`、`deploy/world-core-omarchy.socket`（grep 命中行）；`check.sh.new`（grep 命中行）；`scripts/`（`carrier_contract.py`／`socket_uid_guard.py`／`chown_plus_guard.py`／`admission_evidence.py`／`cross_contract.py`／`gen_owner_uid.py`／`render_channel.py` 的件头，`plain_text_audit.py`／`table_width_audit.py` 全文）；`ninedim/01-意图环/04-规格/gate-enforcement.spec.md`（§「门禁配置在被管者不可写的域」附近）；`ninedim/01-意图环/04-规格/ledger-integrity.spec.md` 与 `ninedim/01-意图环/04-规格/` 各件的标题面；`src/gate/policy.json` 的 `_listeners_note`。

**本件未开**（如实登记）：`研究-归位-2026-10-06\research\src\docs\*.md`（上游 systemd 手册副本，未逐件通读）；退役料 `90-retired-2026-10-06\` 与 `worldcore-上游料-2026-10-06\`（任务书划为垃圾／上游参考，本席未打开）。**未读即未读，不假装读过。**
