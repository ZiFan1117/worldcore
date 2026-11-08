#!/usr/bin/env node
/**
 * C124 的可选件：**假网关 smoke**（本地 node HTTP，端口 18780 —— 不占真网关的 8780）。
 *
 * 它证明三件事，都是「插件这一侧」的事实：
 *   ① 工具调用发出的 JSON-RPC 形状对（`jsonrpc:"2.0"`／`method` 对／`params` 直传／POST ＋ JSON）；
 *   ② 网关回的 `error` **原样**变成工具错误（文本就是那条 JSON，`world_code`／`category` 一字不改）；
 *   ③ 连不上／超时 ⇒ 传输错，**不带** `world_code`（不替世界说话）。
 *
 * 它**不连真网关、不连真总线**：被调的是插件的 `lib/world_client.js`，对面是这台机器上的假 HTTP。
 *
 * 跑法：node scripts/test/c124_smoke_fake_gateway.mjs [插件目录]
 */
import assert from "node:assert/strict";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN = process.argv[2] || path.resolve(HERE, "..", "dsh-plugins", "dsh-worldcore");
const PORT = 18780; // ★ 固定 18780：不占真网关的 8780
const HOST = "127.0.0.1";

const seen = []; // {method, url, contentType, body}
let queue = []; // 每条请求的回话：() => ({status, body}) | null(不回话)
let checks = 0;

function reply(status, body) {
  return () => ({ status, body });
}

const server = http.createServer((req, res) => {
  let raw = "";
  req.on("data", (chunk) => { raw += chunk; });
  req.on("end", () => {
    let body = null;
    try { body = JSON.parse(raw); } catch { body = null; }
    seen.push({ method: req.method, url: req.url, contentType: req.headers["content-type"] || "", body });
    const next = queue.shift();
    const out = typeof next === "function" ? next() : null;
    if (!out) return; // 故意不回话（用来验超时）
    res.writeHead(out.status, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(out.body));
  });
});

function listen() {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(PORT, HOST, resolve);
  });
}

/** 占一个临时端口再放掉 ⇒ 一个「一定没人听」的端口（验连不上）。 */
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", reject);
    probe.listen(0, HOST, () => {
      const p = probe.address().port;
      probe.close(() => resolve(p));
    });
  });
}

function ok(name) {
  checks += 1;
  console.log("  ✓ " + name);
}

function fail(name, err) {
  console.log("  ✗ " + name + "：" + (err && err.message ? err.message : String(err)));
  throw err;
}

async function main() {
  await listen().catch((err) => {
    console.log("[ENV] 端口 " + PORT + " 起不来（" + err.code + "）—— 换一台机器或先放掉该端口");
    process.exit(2);
  });
  const client = await import(pathToFileURL(path.join(PLUGIN, "lib", "world_client.js")).href);
  const endpoint = "http://" + HOST + ":" + PORT;
  process.env.WORLDCORE_GATEWAY = endpoint;
  const env = { WORLDCORE_GATEWAY: endpoint };

  // ── ① 端点读环境变量、默认值不写死在调用处 ─────────────────────
  assert.equal(client.gatewayUrl(env), endpoint);
  ok("端点取自 WORLDCORE_GATEWAY");
  assert.equal(client.gatewayUrl({}), client.DEFAULT_GATEWAY);
  ok("没有 WORLDCORE_GATEWAY 时用默认 " + client.DEFAULT_GATEWAY);

  // ── ② world_query → world.query，params 原样直传 ─────────────
  queue = [reply(200, { jsonrpc: "2.0", id: 1, result: { ok: true, kind: "overview", counts: { classes: 27 } } })];
  const qres = await client.callWorld(client.METHOD_BY_TOOL.world_query, client.queryParams({ kind: "overview" }), { env });
  const q0 = seen[seen.length - 1];
  assert.equal(q0.method, "POST");
  assert.equal(q0.url, "/");
  assert.match(q0.contentType, /application\/json/);
  assert.equal(q0.body.jsonrpc, "2.0");
  assert.equal(q0.body.method, "world.query");
  assert.deepEqual(q0.body.params, { kind: "overview" });
  assert.equal(typeof q0.body.id, "string");
  assert.deepEqual(qres, { ok: true, kind: "overview", counts: { classes: 27 } });
  ok("world_query 发的是 world.query，params 直传，result 原样回");

  // ── ③ world_ask → world.ask：actor 用【配置默认值】，params 直传 ─
  queue = [reply(200, { jsonrpc: "2.0", id: 2, result: { ok: true, action: "sys.GetMemoryInfo", body: { ok: true } } })];
  await client.callWorld(client.METHOD_BY_TOOL.world_ask, client.askParams({ action: "sys.GetMemoryInfo" }, { WORLDCORE_ACTOR: "" }), { env });
  const a0 = seen[seen.length - 1];
  assert.equal(a0.body.method, "world.ask");
  assert.deepEqual(a0.body.params, { action: "sys.GetMemoryInfo" });
  ok("world_ask 发的是 world.ask；WORLDCORE_ACTOR 设空 ⇒ 一个 actor 都不带");

  queue = [reply(200, { jsonrpc: "2.0", id: 3, result: { ok: true } })];
  await client.callWorld(client.METHOD_BY_TOOL.world_ask,
    client.askParams({ action: "sys.GetMemoryInfo", params: { p: 1 }, actor: "world://agent/tester", ticket: "tk-1" }, env), { env });
  const a1 = seen[seen.length - 1];
  assert.deepEqual(a1.body.params,
    { action: "sys.GetMemoryInfo", params: { p: 1 }, actor: "world://agent/tester", ticket: "tk-1" });
  ok("调用方给的 actor／ticket／params 一字不改地直传");

  queue = [reply(200, { jsonrpc: "2.0", id: 4, result: { ok: true } })];
  await client.callWorld(client.METHOD_BY_TOOL.world_ask, client.askParams({ action: "sys.GetMemoryInfo" }, env), { env });
  const a2 = seen[seen.length - 1];
  assert.equal(a2.body.params.actor, client.DEFAULT_ACTOR);
  ok("没给 actor ⇒ 用配置默认值 " + client.DEFAULT_ACTOR);

  // ── ④ 本体拒 ⇒ error 原样变工具错误（码／类别一字不改）──────
  const reject = {
    code: 1201,
    message: "不在册（注册表里没有、本体 actions 里也没有）",
    data: {
      reply: { ok: false, code: "UNKNOWN_ACTION", why: "不在册" },
      world_code: "UNKNOWN_ACTION",
      category: "business",
    },
  };
  queue = [reply(200, { jsonrpc: "2.0", id: 5, error: reject })];
  let caught = null;
  try {
    await client.callWorld(client.METHOD_BY_TOOL.world_ask, client.askParams({ action: "no.such.action" }, env), { env });
  } catch (err) { caught = err; }
  assert.ok(caught, "本体拒了，插件却当成功");
  assert.equal(caught.name, "GatewayRpcError");
  assert.equal(caught.message, JSON.stringify(reject)); // ★ 一字不改
  assert.equal(caught.world_code, "UNKNOWN_ACTION");
  assert.equal(caught.category, "business");
  assert.deepEqual(caught.rpc, reject);
  ok("本体拒 ⇒ 工具错误文本 = 网关那条 error 的 JSON 原文（world_code／category 原样）");

  // ── ⑤ 网关自己的传输码也原样透传，但【不带】world_code ──────
  const busTimeout = { code: 1202, message: "总线没有回话（超时）", data: { transport: "timeout" } };
  queue = [reply(200, { jsonrpc: "2.0", id: 6, error: busTimeout })];
  caught = null;
  try { await client.callWorld(client.METHOD_BY_TOOL.world_ask, client.askParams({ action: "x" }, env), { env }); }
  catch (err) { caught = err; }
  assert.ok(caught);
  assert.equal(caught.message, JSON.stringify(busTimeout));
  assert.equal(caught.world_code, undefined);
  assert.equal(caught.category, undefined);
  ok("网关传输码原样透传，且不冒充世界码");

  // ── ⑥ 连不上 ⇒ 传输错，不带 world_code ─────────────────────
  const dead = await freePort();
  caught = null;
  try {
    await client.callWorld(client.METHOD_BY_TOOL.world_query, { kind: "overview" },
      { baseUrl: "http://" + HOST + ":" + dead, timeoutMs: 3000, env });
  } catch (err) { caught = err; }
  assert.ok(caught, "连不上却没报错");
  assert.equal(caught.name, "TransportError");
  assert.equal(caught.transport, "unreachable");
  assert.equal(caught.world_code, undefined);
  ok("连不上 ⇒ TransportError（无 world_code）");

  // ── ⑦ 超时 ⇒ 传输错，不带 world_code ──────────────────────
  queue = [() => null]; // 故意不回话
  caught = null;
  try {
    await client.callWorld(client.METHOD_BY_TOOL.world_query, { kind: "overview" }, { timeoutMs: 300, env });
  } catch (err) { caught = err; }
  assert.ok(caught, "超时却没报错");
  assert.equal(caught.name, "TransportError");
  assert.equal(caught.world_code, undefined);
  ok("超时 ⇒ TransportError（无 world_code）");

  console.log("=== smoke 绿：%d 项断言／%d 条假网关请求（端口 %d）===", checks, seen.length, PORT);
  return 0;
}

function shutdown(code) {
  // ★ 先掐掉所有连接再关服务，最后用 exitCode 自然退出（直接 process.exit 会在 Windows 上踩 libuv 断言）
  try { server.closeAllConnections(); } catch { /* 老 node 没这个 API */ }
  server.close();
  process.exitCode = code;
}

main().then(shutdown).catch((err) => {
  console.log("=== smoke 红：%s ===", err && err.message ? err.message : String(err));
  shutdown(1);
});
