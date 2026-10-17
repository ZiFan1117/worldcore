# 裁决：**只加一个 `computer` 类；载体靠【庞大的 action】覆盖功能；不做实时状态**（2026-10-17）

> ★ 作者裁决（逐字）：「我觉得**用一个 computer 就可以了**……**有 action 的这个接口，有 action 的接口就没必要说实时显示状态啥的，这种直接用命令行查就行**，对吧，**只要告诉他有这条命令不就完事了吗**？……所以说，**你这个载体的这个 action 需要做得很庞大，很完善。补充，没有状态实时显示**这样子」

---

## §一 ★★★★★ 四条裁决

| # | ★ 裁决 |
|---|---|
| **1** | ★★ **只加【一个 `computer` 类】** —— ★ **不加 `filesystem`／`disk`／`netif`** |
| **2** | ★★★ **不做【实时状态显示】** —— ★ 状态**用动作现查**（★ `df`／`top`／`free`…） |
| **3** | ★★★ **「只要告诉他有这条命令」** —— ★ **动作本身就是【问状态的方式】** |
| **4** | ★★★ **载体的 action 要做【很庞大、很完善】** |

## §二 ★★★★★ 为什么不做实时状态 —— 逻辑链

```
★ 有 action 接口
★   ⇒ 状态可以【随时查】
★   ⇒ 不必【提前存】
★   ⇒ 不必【实时推送】
★   ⇒ ★ 本体里【不存状态】✓
```

★★★ **⇒ 一句话**：「**有命令就够了 —— 不用实时显示状态。**」

## §三 ★★★★ 那 `computer` 类【该装什么】—— 只装【别处没有的】

| ★ 字段 | ★ 为什么进本体 |
|---|---|
| `name` | ★ 主键（★ 世界里的名字） |
| `hostname` | ★ 世界里的标识 |
| ★★ **`owner`** | ★★ **这台机器【属于谁】—— ★ 别处没有** ✓ |
| ★★ **`bound_to`** | ★★ **绑给哪个人的设备 —— ★ 别处没有** ✓ |
| `state` | ★ 在役／退役（★ 世界级状态） |

★★ **【不进】的**：★ CPU／内存／磁盘／负载／温度／文件系统列表／网卡列表 ✗ ★ —— ★ **那些【系统自己记着】** ✓

## §四 ★★★★★ 判据（★ 由这条裁决得出）

> ★★★ **「有【外部权威来源】的 —— ★ 不存，★ 现查。**
> ★★★ **没有外部权威的（★ 许可、★ 因果、★ 归属）—— ★ 必须本体存。」**

| ★ 什么 | ★ 外部权威 | ★ 本体 |
|---|---|---|
| 文件系统列表 | `/proc/mounts` | **不存** ✗ |
| 磁盘／网卡 | `lsblk`／`ip link` | **不存** ✗ |
| CPU／内存／负载 | `top`／`free` | **不存** ✗ |
| 进程 | `/proc` | **不存** ✗ |
| ★★ **这台机器属于谁** | ★ **没有** | ★★ **存** ✓ |
| ★★ **谁能做什么** | ★ 没有 | ★★ **存** ✓ |
| ★★ **谁做过什么** | ★ 没有 | ★★ **存** ✓ |

---

## §五 ★★★★★ 所以【接下来要做的】—— 载体的 action 做庞大

★★ **现在只有 11 个**（★ `fs.list`／`fs.stat`／`service.start`／`service.stop`／`pkg.install`／`proc.list`／`device.eject`／`device.brightness.set`／`interface.ask_permission`／`interface.notify`／`app.download.start`）

★★★ **⇒ 要补成【覆盖老 computer 全部功能】的大清单**。按类分：

| ★ 类 | ★ 该有的动作（草案） |
|---|---|
| ★ 文件 | `fs.list`／`fs.stat`／`fs.read`／`fs.write`／`fs.rm`／`fs.mv`／`fs.cp`／`fs.mkdir`／`fs.chmod`／`fs.find` |
| ★ 进程 | `proc.list`／`proc.kill`／`proc.start`／`proc.tree`／`proc.signal` |
| ★ 服务 | `service.start`／`service.stop`／`service.status`／`service.enable`／`service.disable` |
| ★ 软件包 | `pkg.install`／`pkg.remove`／`pkg.query`／`pkg.upgrade`／`pkg.list` |
| ★ 网络 | `net.status`／`net.ping`／`net.dns`／`net.if`／`net.listen`／`net.route` |
| ★ 电源 | `power.off`／`power.reboot`／`power.sleep`／`power.status` |
| ★ 用户 | `user.list`／`user.whoami`／`user.groups` |
| ★ 硬件 | `device.list`／`device.eject`／`device.brightness.set`／`device.sensor` |
| ★ 存储 | `disk.list`／`disk.usage`／`disk.mount`／`disk.umount` |
| ★ 时间 | `time.now`／`time.set`／`time.zone` |
| ★ 日志 | `log.read`／`log.query` |
| ★ 状态（现查） | `sys.uptime`／`sys.load`／`sys.memory`／`sys.cpu`／`sys.temp` |

★★★ **⇒ 每一行动作要三样**：① 本体 `actions` 里一条定义（★ 名字／`parameters`／`not_roles`）② 映射表一条（★ `program` ＋ `args`）③ 许可一条（★ `who`）

---

## §六 ★ 本件不能证明的事（如实）

- ★ 11 个动作／9 类 —— 都是**现取**（★ 之前的 `world/query`）；
- ★★ **上面那张动作清单是【我草拟的】** ★ —— ★ **不是你的，★ 也没核对 `sysknife`**（★ 抓不到）⚠；
- ★★ **「不做实时状态」的逻辑链是【我按你的话推的】** ✓；
- ★★ **`computer` 的五个字段是【我的建议】** ✗；
- ★★ **本件【没写一行代码】** ✓ ⇒ ★ 判据 **C1–C26 全绿**
