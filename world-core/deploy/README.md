## 〇、本夹是什么（夹内分工）

> **本夹 ＝ 部署面**（一个面一个夹）：把「**三进程三身份一条总线**」落成 systemd 单元与装机脚本。
> 它**不占模块号**（登记见 `WC-MODREG-001` §2.1）。夹内四件各司其职：

| 件 | 是什么 |
|---|---|
| `README.md`（本件） | **契约文档**：部署形态的声明（单元 ↔ 法律 ↔ 渲染物三方一致的口径） |
| `units/`（5 件） | **实现**：`world-core.socket`／`world-core.service`／`world-core-actd.service`／`world-core-omarchy.socket`／`world-core-dsh.socket` |
| `install.sh` | **装机**：建身份、装单元、种出厂法律、起总线（`UNITS=` 是本面的**唯一单元清单**） |
| （判据与测试不在本夹） | 判据＝`world-core/tools/carrier_contract.py`（`check.sh` ⑥c）；测试＝`world-core/tests/carrier_boundary.rs` |

# 世界核心的部署形态 —— **三个进程，三个身份，一条总线**

> 本目录是**可直接用的部署件**：让它由载体管理器（systemd）拉起，而不是靠人手工敲命令。
> 三份单元 + 一份安装脚本。**不含任何未实测的承诺**：判据见文末"装完怎么验"。

## 一、为什么是这三份单元

| 单元 | 装什么 | 身份 | 对账本的权限 |
|---|---|---|---|
| **`world-core.socket`** | 写入总线：**监听套接字由载体持有**，不是由进程自己持有 | — | — |
| **`world-core.service`** | 内核进程：本体 · 账本 · 读模型 · 运行时 · 门禁 · 通道 | 专用身份 | **可写（唯一写者）** |
| ~~**`world-core-projectd.service`**~~ | 投影服务：语言投影 / 视觉投影（**已退役**，见下表下注） | 另一个专用身份 | **只读** |
| **`world-core-actd.service`** | 载体执行器：调载体、做撤销点、等人确认 | **被管者身份** | **无权限**（只能经总线提交请求） |

> ★ **上表那条被划掉的行＝【设计要求】，不是【现状】**（2026-10-06）：
> `world-core-projectd.service` **已退役**（工作树移除；`deploy/` 现在**正好**＝`install.sh` 的 5 件清单）。
> 三条定案：① 它的 `ExecStart=… project serve` 是**死子命令**（`cmd_project` 只认
> `language`／`visual`／`surface`／`check`）＋ `Restart=on-failure`／`RestartSec=2s` ⇒ 装上去每 2 秒抖一次；
> ② 单元件 2026-10-05 被改成 `User=world-core` ⇒ 与设计"独立 uid"**矛盾**；
> ③ 当初"不许删"的理由（未跟踪件、无解析根）已消失。**解析根**：
> `git show deafbae:world-core/deploy/world-core-projectd.service`。
> 设计要求仍在（`WC-ARCH-001`／`系统全景图`／本件 §四）⇒ 归"**设计已定·未落地**"，如实登记。

**为什么套接字单独一份单元**：这样"服务挂了请求不丢"由**内核的连接积压**保证——
进程重启期间套接字仍在，客户端拿到的是"排队"而不是"连不上"。
**不要自己在进程里造请求队列**：那等于把内核已经做好的事重做一遍，还做得更差。

## 二、`world-core.socket`

```ini
[Unit]
Description=世界核心 · 写入总线（唯一写入口的入口）
Documentation=man:systemd.socket(5)
PartOf=world-core.service

[Socket]
# 监听套接字归载体所有；内核进程通过继承的描述符拿到它（`sd_listen_fds` 语义）
ListenStream=/run/world-core/world.sock
# 一个连接一个身份 ⇒ 套接字本身用 0660 + 属组表达"谁能连"；
# **"连上能干什么"必须在服务端按角色判定**（套接字权限位表达不了"只读"）
SocketMode=0660
SocketUser=world-core
SocketGroup=world-core
# 一次往返 = 两个连接（先意图、后结果），故不限制单次连接数；
# 但同一时刻的排队长由内核控制（`Backlog=` 直接映射到 listen(2) 的 backlog）
Accept=no
# 服务重启期间**保留**排队中的请求（默认即 no = 不丢弃）
FlushPending=no
# 服务被 stop 再 start 时，已传出的描述符存储**不保留**——
# 这是刻意的：重启后由内核重新接受连接，避免持有过期描述符
FileDescriptorStorePreserve=no

[Install]
WantedBy=sockets.target
```

## 三、`world-core.service`（内核进程）

```ini
[Unit]
Description=世界核心 · 内核进程（唯一写者）
Documentation=man:systemd.service(5) man:systemd.exec(5)
Requires=world-core.socket
After=world-core.socket
# 内核要独立升级时，用 `systemctl restart world-core.service` ——
# 套接字不重启，故排队中的请求不丢

[Service]
Type=notify
NotifyAccess=main
# 就绪门槛：**先自检再对外可用**。四条件不齐 ⇒ 不发 READY ⇒ 载体不认为它起来了
ExecStart=/usr/bin/world-core --ontology /etc/world-core/src/ontology_definition/ontology.json \
                              --ledger /var/lib/world-core/ledger.jsonl \
                              --policy /etc/world-core/src/gate/policy.json \
                              --channel /etc/world-core/channel.json \
                              --cap-dir /etc/world-core/src/carrier/cap.d \
                              --owner-uid world-core \
                              serve
# 常驻接受者由套接字激活提供描述符；本单元只负责"活着且就绪"
Restart=on-failure
RestartSec=2s
# 看门狗：进程必须周期性报到，否则视为卡死并重启
WatchdogSec=30s

# ── 身份与权限：法律与真相必须在这个身份之下 ──
User=world-core
Group=world-core
# 状态目录（账本）：只有本进程可写
StateDirectory=world-core
StateDirectoryMode=0700
# 运行目录（套接字、锁）：模式交给 socket 单元控制
RuntimeDirectory=world-core
RuntimeDirectoryMode=0755
# **配置目录不 chown 给本用户**（它是唯一"配置与状态权限分离"的落点）：
# 法律必须由部署方写，进程只能读
ConfigurationDirectory=world-core
ConfigurationDirectoryMode=0755

# ── 内核语义类约束（内核强制，不依赖"尽力而为"档）──
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
RestrictRealtime=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
SystemCallArchitectures=native
# 只允许必要的地址族（本机 IPC 即可；不要开网络族）
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
# 只读挂载之外，仅允许写状态目录与运行目录
ReadWritePaths=/var/lib/world-core /run/world-core
# ⚠️ 注意：`ProtectSystem=`/`ReadOnlyPaths=` **不能**用来限制"谁能连上本机套接字"。
#     套接字的可达面由 `world-core.socket` 的属主/属组/模式决定。
# ⚠️ 注意：`MemoryDenyWriteExecute=` 与"用 memfd 传递描述符"会互相打架——
#     若将来要用 memfd 交接本体，必须先显式取舍（本版不用 memfd，故保持开启）。

# ── 资源 ──
MemoryMax=2G
CPUQuota=100%
TasksMax=64

# ── 停机：先把该落的落完，再退 ──
KillSignal=SIGTERM
TimeoutStopSec=15s
# 本进程不故意留残余：被杀时最多留一个残缺末行，由下次启动丢弃

[Install]
WantedBy=multi-user.target
```

## 四、`world-core-projectd.service`（投影服务，只读）——★ **本节是「设计要求」，今天没有执行体**

> **实现状态（2026-10-06，现取）**：单元件**已退役**（工作树移除、git 历史留；
> 解析根 `git show deafbae:world-core/deploy/world-core-projectd.service`）。三条定案：
> ① `ExecStart=… project serve` 是**死子命令**（`cmd_project` 只认 `language`／`visual`／`surface`／`check`）
> ＋ `Restart=on-failure`／`RestartSec=2s` ⇒ 装上去每 2 秒抖一次；
> ② 单元件 2026-10-05 被改成 `User=world-core`／`Group=world-core` ⇒ 与**本节下面的设计**（独立 uid、只读）**矛盾**；
> ③ 当初"不许删"的理由（未跟踪件、无解析根）已消失 —— 收口提交把它带进了版本控制。
> ⇒ **本节以下照旧是设计要求**（"独立 uid、零写权限"）；它属**设计已定·未落地**这一档，**如实登记**，
> 不因为一个坏实现退场而把要求也删掉。下面这段 `ini` 是**设计示意**，不是现役件。

```ini
[Unit]
Description=世界核心 · 投影服务（只读消费者）
Documentation=man:systemd.service(5)
# 用 Wants（不用 Requires）：投影没起来，世界照常读写
Wants=world-core.service
After=world-core.service

[Service]
Type=exec
ExecStart=/usr/bin/world-core --ontology /etc/world-core/src/ontology_definition/ontology.json \
                              --ledger /var/lib/world-core/ledger.jsonl \
                              --policy /etc/world-core/src/gate/policy.json \
                              project serve
Restart=on-failure
RestartSec=2s

# **只读身份**：它对账本目录没有写权限
User=world-projectd
Group=world-projectd
SupplementaryGroups=world-core-read

# 只允许读：把自己能看见的东西缩到最小
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
NoNewPrivileges=yes
RestrictAddressFamilies=AF_UNIX
# 只读挂载状态目录（不给自己写的机会；真实拦阻来自文件属主与模式）
ReadOnlyPaths=/var/lib/world-core

MemoryMax=1G
CPUQuota=50%
TasksMax=32

[Install]
WantedBy=multi-user.target
```

## 五、`world-core-actd.service`（载体执行器，被管者身份）

```ini
[Unit]
Description=世界核心 · 载体执行器（只执行、不裁决）
Documentation=man:systemd.service(5)
# 它必须能连上总线才有意义；总线没起来就不该起
Requires=world-core.service
After=world-core.service

[Service]
Type=exec
# 它是一个**客户端**：从标准输入逐行读请求、先问内核、再执行、再回写结果
ExecStart=/usr/bin/world-core --cap-dir /etc/world-core/src/carrier/cap.d \
                              --ledger /var/lib/world-core/ledger.jsonl \
                              --socket /run/world-core/world.sock \
                              carrier serve
# ⚠️ 高危动作需要人确认时：不带 `--confirm` ⇒ 需要确认的动作**一律拒绝**（默认拒绝）。
#     要允许终端确认，须显式加 `--confirm`，并自行承担"没人看着时的后果"。

# **被管者身份**：与内核、投影都不同
User=agent
Group=agent

# 它要动设备/装包，所以不能像内核那样把自己焊死；
# 但仍然不给它任何能碰到法律与真相的权限。
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=yes
NoNewPrivileges=yes
# 载体执行器需要的地址族（本机 IPC）
RestrictAddressFamilies=AF_UNIX
# 只允许写它自己的工作目录；账本目录**不在**此列 ⇒ 它对真相零写权限
ReadWritePaths=/var/lib/world-actd /run/world-actd
StateDirectory=world-actd
StateDirectoryMode=0700
RuntimeDirectory=world-actd

MemoryMax=2G
CPUQuota=150%
TasksMax=128

[Install]
WantedBy=multi-user.target
```

## 六、装完怎么验（逐条可机械核对）

| # | 判据 | 命令 | 期望 |
|---|---|---|---|
| 1 | 在跑的是**清单里的**单元（★今天＝内核 ＋ 载体执行器；**投影单元已摘除未启用**） | `systemctl list-units --type=service --state=running 'world-core*'` | **以命令输出为准**（本表不复述现状） |
| 2 | 内核**就绪**（不是"进程活着"） | `systemctl show -p ActiveState,SubState world-core` | `active` / `running`，且日志里有 `READY=1` |
| 3 | 总线套接字在，且只对指定身份可连 | `ls -l /run/world-core/world.sock` | 属主/属组为本核心身份，**模式以 `world-core.socket` 的 `SocketMode=` 为准**（★今天是 `0600`；本表不复述） |
| 4 | 唯一写者 | `lsof /var/lib/world-core/ledger.jsonl` | **只有一个**进程持有可写描述符 |
| 5 | 消费者对真相零写权限 | 以投影身份执行一次读取后比对账本摘要 | 摘要不变；尝试写入时**系统调用返回拒绝** |
| 6 | 世界不会半成品 | `systemctl stop world-core && echo 一条请求 \| nc -U /run/world-core/world.sock` | 不产生任何副作用（请求排队或连接被拒，**绝不静默执行**） |
| 7 | 内核重启不丢请求（长驻化后） | 重启 `world-core.service` 期间持续发请求 | 请求排队而非丢失（由内核积压保证） |

## 七、机核：载体契约门禁（`tools/carrier_contract.py`）

`deploy/` 里**清单（`install.sh` 的 `UNITS=`）内的**单元的**不是手写的设计稿，而是"从法律生成"的产物**——这条关系由门禁守。
★**清单里有几件、是哪几件，以 `UNITS=` 那行为准**（取法：`grep -n '^UNITS=' deploy/install.sh`）——★**本处不写件数**（2026-10-05 订正：原写"今天清单 4 份"，而当天清单变成 5 件、**这句就成了假话**；★写死的数会烂，见 §八 第 8 条）。★目录里另有**已登记未启用**的件（`⑪c` 连原因报出，不藏着）：

| 判据 | 内容 | 反例（自测会给） |
|---|---|---|
| ① | **清单（`install.sh` 的 `UNITS=`）里的**单元存在且非空；README 声明的套接字路径与 `ListenStream=` 一致 | 删单元／改路径 |
| ② | socket 的 `SocketUser=`/`SocketGroup=` 与内核单元 `User=`/`Group=` **同一身份** | 换属主 |
| ③ | `ListenStream=` 与内核 `RuntimeDirectory=` **同址** | 改 RuntimeDirectory |
| ④ | **唯一写者**：只有内核单元的 `ReadWritePaths` 含状态目录 | 给投影／执行器开写 |
| ⑤ | **默认拒绝**：执行器的 `ExecStart` 不含 `--confirm`（**只看指令行，注释不算**） | 加 `--confirm` |
| ⑥ | 内核不用 `User=root`；socket 不用 `SocketMode=0666` | 改成 root／0666 |
| ⑦ | **身份映射入法**：`policy.json` 的 `listeners` 里有本套接字 | 抽掉 `listeners` |
| ⑧ | **渲染物 ⊆ 法律**：`--channel` 指向的渲染件**每一条**都在法律里（账外口一律拒） | 渲染物多一条账外口 |
| ⑨ | **在册而渲染物里没有**（**报告行**，不判红）——专治"把在册读成已上线" | 把它写成"已上线" |
| ⑩ | **`owner`→`uid` 对账**：映射里没有法律外的口／法律里的口都有行／`uid` ≡ `owner` 的解析值 | 映射多口／缺行／uid 不符 |
| ⑪ | **清单 ≡ 实际**：`UNITS=` ↔ `deploy/` 里的单元件（目录里每件都要在清单里，**或**在⑪c 登记） | 目录里多一个未登记单元件 |
| ⑪c | **已登记未启用**（**报告行**）：连**原因**报出，不许读成"已上线" | ——（报告行，不判红） |

命令：`python tools/carrier_contract.py [--channel <渲染物路径>]`（★**`rc=0` 且**没有 `STATUS=SKIP` **才算全校验**；有 SKIP ⇒ 那几条是**未校验**，不是通过）｜`--self-test`（把单元复制到临时目录逐个改坏，**每条判据都必须红**）。

> **为什么要有它**：单元文件是"**生成物**"——手改输出而不改法律，正是本项目在别处栽过的坑。
> ★门禁把"① 生成关系"与"⑧ 渲染物 ⊆ 法律"做成会红的；★**「实际监听 ⊆ 在册」的运行态枚举仍未实现**（受理期只判"渲染物每一条都在法律里"，不枚举内核真在听哪些口）。
> ★**判据与单元清单都只有一个来源**：清单＝`install.sh` 的 `UNITS=`；★本表**只索引**，权威是 `tools/carrier_contract.py` 的输出。

## 八、已知缺口（如实登记，不假装已做）

| # | 缺口 | 说明 |
|---|---|---|
| 1 | **多口同一属主**（(甲-e) 的弱化） | ★**机制成立**：2026-10-05 T29 真机现取 —— `/run/world-core/` 两个口都在 ＋ `ss -xl` 两条都在听 ＋ `LISTEN_FDS=2` ＋ 重启连续性成立（账本跑前＝跑后逐字节相同）。★★**而"一个口一个系统身份"【没有被这条路径兑现】**：`world-core-omarchy.socket` 写着 `SocketUser=omarchy`、`systemctl show` 也读得出它，**而盘上 `omarchy.sock` 的属主是 `world-core:world-core`** ⇒ ★**"单元级 `SocketUser=`"这条路今天做不到每口各自的属主**。★**两句都要写，不许只写前一句。** ★**口径**：★**不许对外声称"身份是内核强制的"**——今天"谁在说话"只剩「协议自称 ＋ 许可」（与 `world-core-dsh.socket` 那条登记同形）。★"为什么没落下去"＝**查不出**（已排除"世界自己 `bind()`"：口的 `ctime` 晚于装单元时刻且与 `world.sock` 同瞬） |
| 2 | **第二个口没人受理** | ★现取（T29）：服务日志 `[登记] ext.world.Serve.ExtraListenFds: LISTEN_FDS=2 … 而 serve 今天只接第一个（fd 3）` ⇒ ★**口建出来了、第二个口没人受理**（"起了 ≠ 受理得到"）。落在 `cmd_serve`（`bus` 的件） |
| 3 | **`world-core serve` / `project serve` 两个子命令尚未实现** | 现形态是 `channel serve <socket> <n>` 与一次性 `carrier serve`；★`LISTEN_FDS` 语义**已接**（现取 `LISTEN_FDS=2` 读得到），**但只受理第一个 fd** |
| 4 | 看门狗报到（`WATCHDOG=1`）尚未实现 | `WatchdogSec=` 已写在单元里；进程侧未接 ⇒ 实装时须先做，否则会被反复重启 |
| 5 | **部署件 ≡ 仓：今天【一致】；但 ⑫ 仍无执行体** | ★现取：`/etc/systemd/system/world-core.service` 与 `deploy/units/world-core.service` **同 sha256、同 5773 B**（17:14:15 装的），`grep -n '^Sockets='` 两处皆 rc=1（`Sockets` 只出现在注释）⇒ **本条已不成立**（曾记"仍是含 `Sockets=` 的旧版"——**那是当时的读数，现取已否**）。★ **仍成立的一半**：⑫「部署件 ≡ 仓」**没有判据盯着**（机件与仓件各自漂了不会红）⇒ 这一条要留着，但记的是**执行体缺位**，不是"两处不同" |
| 6 | 动态身份的**明确禁止** | 见"主体身份必须稳定"：任何会被回收的动态身份都不得用于长期出现在事件里的主体 |
| 7 | `world-projection` 的**停机段读数**未验 | 口径＝"世界停着那一段必须印【离线】"；★**未验·原因＝窗口太短**（世界只停约 1 秒）⇒ ★下次重启类动作**在重启前**先把那个循环挂起来 |

> **两条形态登记**（2026-10-05，真机现场，见 `world-core-omarchy.socket` 的注释）：
> ★**形态一 · 键不认**：`FileDescriptorStorePreserve=`（本机 systemd 逐字 `Unknown key …, ignoring.`）／`Sockets=`（逐字 `Unknown key 'Sockets' in section [Unit], ignoring.`）。
> ★★**形态二 · 配了 ≠ 生效，且沉默**：`SocketUser=omarchy` **在单元里、`systemctl show` 读得出**，**而盘上那个口是 `world-core:world-core`，★systemd 一句警告都没打**。
> ⇒ ★**不生效可以【不报错】**；★所以"写在单元里"既不是"键被认"，也不是"已生效"。
