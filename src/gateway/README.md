# 世界薄网关（`src/gateway/`）

外部（宿主上的 DSH 插件）进入世界的**唯一门**。它**只做协议翻译，不做任何治理**。

## 接口

`127.0.0.1:8780`，HTTP ＋ JSON-RPC 2.0（`POST /`）。

| method | params | 世界总线 |
|---|---|---|
| `world.query` | `kind` 等，**原样直传** | `world/query`，等 `world/query/result` |
| `world.ask` | `action`、`params`、`actor`（调用方给）、可选 `ticket` | `world/ask`，等 `world/ask/result` |

请求（示例，不写死读数）：

```json
{"jsonrpc": "2.0", "id": 1, "method": "world.ask",
 "params": {"action": "sys.GetMemoryInfo", "params": {}, "actor": "world://agent/dsh"}}
```

回话：`world.ask` 成功 ⇒ `result` 是本体回话**原样**；本体拒绝 ⇒ JSON-RPC `error`，
`error.data.world_code` 是本体给的码，`error.data.category` 照本体闭集表
（`src/ontology/gate/world_codes.py`）抄，`error.data.reply` 是回话**原样**。
`world.query` 一律进 `result`（查世界没有「拒绝码」这一说，`ok=false` 也是答案）。

## 它不做什么

- 不校验动作名／参数／许可／凭证 —— 未登记动作、没有身份由**本体**拒；
- 不自己记账（没有第二本账）；
- 不自造拒绝码：`world_code` 只取自本体回话；超时这类**传输**错误用 `1201`–`1203`
  之外的语义（`data.transport`），**不带** `world_code`；
- 不替调用方造 `actor`：`actor` 缺就是缺，本体回 `NO_IDENTITY`。

## 与仓里既有件的关系

- 总线收发写法照 `src/agent/world_cli.py`／`src/web/web_process.py`；
- 总线凭据用 `src/ontology/bus_auth.py`（deploy 写 drop-in），不另存一份；
- 拒绝码→类别只读 `src/ontology/gate/world_codes.py` 的闭集表（不在这里另立一张）。

## 文件

| 件 | 干什么 |
|---|---|
| `world_gateway.py` | 入口：HTTP 传输层 ＋ `App`（翻译） |
| `gateway_rpc.py` | JSON-RPC 2.0 信封 ⇄ 总线消息（纯函数） |
| `gateway_bus.py` | 总线收发（一问一答，超时如实返回） |

## 部署

单元的 repo 侧在 `scripts/release/systemd/aios-gateway.service`；`scripts/release/deploy.sh`
的 `BUS_UNITS`、单元安装、重启、状态四处都带它。网关**不是** provider
（不往总线发受保护话题），所以在总线 ACL 里走 nonprovider 那一档。
