# `dsh-worldcore` —— 宿主侧 DSH 插件（只经世界薄网关进世界）

宿主上的 DeepSeek Harness 用这两个工具问世界／请世界做事：

| 工具 | JSON-RPC 方法 | 做什么 |
|---|---|---|
| `world_query` | `world.query` | 问世界（`kind` 等参数**原样直传**）；只查不改 |
| `world_ask` | `world.ask` | 请世界做一件事（`action`／`params`／`actor`／可选 `ticket` **原样直传**） |

两条路都只到 `src/gateway/`（世界薄网关）为止。**网关只翻译、不治理**；本插件同理，**只传输、不治理**。

## 1. 它不做什么（边界，逐条）

- **不直连总线**：没有 zenoh，不订阅／不发布任何 `world/*` 话题；
- **不调 `world_cli.py`**：不起子进程、不跑 shell，只发一条 HTTP POST；
- **不碰执行器**：不 import 世界进程的任何代码，不认识任何动作名；
- **不校验**动作名／参数／许可／凭证 —— 未登记动作、没身份，**由本体拒**；
- **不自造拒绝码**：网关回的 JSON-RPC `error` **原样**变成工具错误（见 §4）；
- **不替调用方造 actor**：`world://agent/dsh` 只是**配置默认值**（见 §3），不是插件凭空补的身份。

## 2. 端点与超时（环境变量）

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `WORLDCORE_GATEWAY` | `http://127.0.0.1:8780` | 世界薄网关的地址。**插件不把端点写死在调用处**，每次都从这里读 |
| `WORLDCORE_ASK_TIMEOUT_MS` | `110000`（110s） | `world.ask` 的传输超时（与网关自己的 ask 超时同量级） |
| `WORLDCORE_QUERY_TIMEOUT_MS` | `30000`（30s） | `world.query` 的传输超时 |
| `WORLDCORE_ACTOR` | `world://agent/dsh` | **配置默认值**。设成空串 ⇒ 一个 actor 都不带，由本体按 `NO_IDENTITY` 拒 |

超时到了 ⇒ **传输错误**，错误里**没有** `world_code`（那是「网关／网络没回话」，不是「世界拒了你」）。

## 3. actor 的三条规则（写清楚，免得被当成「插件造身份」）

1. 调用方给了 `actor` ⇒ 用调用方的，一字不改地直传；
2. 没给 ⇒ 用**配置默认值**（`WORLDCORE_ACTOR`，未设时是 `world://agent/dsh`）；
3. 配置默认值被设成空 ⇒ 什么都不带（世界里 `actor` 缺就是缺）。

> 这个默认值只是「本插件所在宿主的配置」，**不是世界的授权**。真正认身份的仍是本体：
> 它不认识这个串，就回 `NO_IDENTITY`／`IDENTITY_NOT_REPORTED`。

## 4. 回话形状（成功与拒绝都原样）

- 成功：网关回话里的 JSON-RPC `result` **原样**作为工具结果返回；
- 被拒（本体拒）：网关回 `error`，工具抛错，错误文本就是这条 `error` 的 JSON **原文**
  （`code`／`message`／`data.world_code`／`data.category`／`data.reply` 一字不改）；
- 网关自己的传输码（如总线超时）也**原样**透传，**不带** `world_code`。

例（真实形状，读数不写死；以当天网关回话为准）：

```
Error: {"code":1201,"message":"不在册（注册表里没有、本体 actions 里也没有）","data":{"reply":{"ok":false,"code":"UNKNOWN_ACTION","why":"…"},"world_code":"UNKNOWN_ACTION","category":"business"}}
```

## 5. 本插件不自动安装（人做，三步）

> ★ **本包装不会自己装上、也不会自己启用**。`cordis.patch.yml` 在本目录里只是**给人抄的落点**，
> DSH 只读 profile 目录下那一份 `~/.dsh/profiles/<profile>/cordis.patch.yml`。

**装之前**先备份宿主的两处（这是本仓的硬规矩）：

```
.dsh/sessions   →  复制一份
.dsh/storages   →  复制一份
```

1. `dsh plugin add <本目录的绝对路径>`（＝在 profile 里 `pnpm add` 这个本地包）；
2. 把本目录 `cordis.patch.yml` 里的 `insert` 条目并入 profile 的 `cordis.patch.yml`；
3. 重启宿主 —— 之后模型才有 `world_query`／`world_ask` 两个工具。

卸载：删掉 profile `cordis.patch.yml` 里那条 `insert`，再 `dsh plugin remove dsh-plugin-dsh-worldcore`。

## 6. 宿主怎么够到网关（网关**只听环回**）

网关在 VM 里只听 `127.0.0.1:8780`（`src/gateway/world_gateway.py` 里 `HOST = "127.0.0.1"`），
所以宿主不能直接敲到它。两条路，二选一：

**① SSH 隧道（推荐）**——在宿主上开一条，把本机 8780 落到 VM 的环回：

```
ssh -i D:\vm\keys\vm_ed25519 -p 2223 -N -L 8780:127.0.0.1:8780 root@127.0.0.1
```

隧道开着的时候，插件用默认端点 `http://127.0.0.1:8780` 就能进世界。

**② VBox NAT 端口转发**——把 VM 的 `127.0.0.1:8780` 转发到宿主的 `127.0.0.1:8780`
（VirtualBox：设置 → 网络 → 高级 → 端口转发 → 主机 IP `127.0.0.1`、主机端口 `8780`、子系统端口 `8780`）。
宿主侧仍然填 `WORLDCORE_GATEWAY=http://127.0.0.1:8780`。

## 7. 安全边界（这三条别松）

1. **网关只听环回**（`127.0.0.1`）：不要把它改成 `0.0.0.0`，也不要把 8780 暴露到局域网；
2. **隧道／转发只绑宿主环回**（`-L 8780:127.0.0.1:8780` 的主机端默认就是 `127.0.0.1`）：
   写成 `-L 0.0.0.0:8780:…` 等于把「谁能调世界」交给了整个网段；
3. **本插件没有许可能力**：它不带任何授权判断，所以它被谁调用，世界就看到谁的身份（或没身份）。
   要收紧，收在世界那一侧（本体／许可），不是收在这里。

## 8. 限度（如实）

- 本包装**没有安装到任何 DSH profile**，也**没有在真宿主上连过真世界**；
  装机与真机连接留给人在 §5／§6 之后做。
- 判据 `scripts/test/c124_dsh_world_plugin.py` 判的是**插件这一侧的形状**（静态契约）
  ＋ 宿主上跑一个**假网关 smoke**（本地 HTTP，端口 18780，证明发出的 JSON-RPC 与错误码透传）；
  它**不连真网关、不连真总线**。真机读数（`world.query overview` ⇒ `ok=true`；`world.ask no.such.action`
  ⇒ `error.data.world_code=UNKNOWN_ACTION`）出在世界那一侧。
