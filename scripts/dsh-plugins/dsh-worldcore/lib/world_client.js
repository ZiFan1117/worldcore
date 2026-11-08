/**
 * ★ 世界薄网关的【传输层】—— 宿主侧 DSH 插件只经这一层进世界。
 *
 * ★ 口径（与 `src/gateway/README.md` 同一句话）：「只做协议翻译」的对面，就是
 *   「只做传输」：本文件**不发**总线话题、**不判**动作名／参数／许可、**不造**拒绝码。
 *   · 出去：一条 HTTP POST，JSON-RPC 2.0（`POST /`，method 只有 `world.query`／`world.ask`）；
 *   · 回来：`result` 原样交给工具；`error` 原样抛成工具错误（`world_code`／`category` 一字不改）。
 *
 * ★ 不直连总线（zenoh）、不调 `world_cli.py`、不碰执行器 —— 那三样都在世界那一侧。
 */

/** ★ 端点默认值：网关只听 VM 的环回；宿主侧靠 SSH 隧道／NAT 转发把它落到本机 8780。 */
export const DEFAULT_GATEWAY = "http://127.0.0.1:8780";
/** ★ 超时默认值（与网关自己的 ASK／QUERY 超时同量级：世界慢在总线那一侧）。 */
export const ASK_TIMEOUT_MS = 110000;
export const QUERY_TIMEOUT_MS = 30000;
/**
 * ★ actor 的【配置默认值】。★ 它不是「插件替调用方造身份」——
 *   调用方给了 actor 就用调用方的；`WORLDCORE_ACTOR=` 设成空串 ⇒ 一个都不给，
 *   让本体按 `NO_IDENTITY` 拒（这正是「actor 缺就是缺」）。
 */
export const DEFAULT_ACTOR = "world://agent/dsh";

/** ★ 工具名 → JSON-RPC 方法。只有两条路，多一条就是第二种出口。 */
export const METHOD_BY_TOOL = Object.freeze({
  world_query: "world.query",
  world_ask: "world.ask",
});

/** ★ 传输错（连不上／回话不是 JSON／没有 result）——**不带** `world_code`：不替世界说话。 */
export class TransportError extends Error {
  constructor(message, transport) {
    super(message);
    this.name = "TransportError";
    this.transport = transport || "error";
  }
}

/**
 * ★ 网关回的 JSON-RPC `error`，**原样**变成一个工具错误。
 *   · `message` ＝ `JSON.stringify(error)`（一字不改，模型看到的就是网关给的那一份）；
 *   · `world_code`／`category` 只从 `data` 里**读**，本文件不写、不改、不补。
 */
export class GatewayRpcError extends Error {
  constructor(rpcError) {
    super(JSON.stringify(rpcError));
    this.name = "GatewayRpcError";
    this.rpc = rpcError;
    const data = rpcError && rpcError.data;
    this.world_code = data && data.world_code;
    this.category = data && data.category;
  }
}

/** 读环境变量；只做 trim，不做别的解释。 */
function readEnv(env, key) {
  const raw = env && env[key];
  return typeof raw === "string" ? raw.trim() : "";
}

/**
 * ★ 端点：`WORLDCORE_GATEWAY` 优先，空则用默认。**不写死在调用处**。
 * @returns {string} 形如 `http://127.0.0.1:8780`
 */
export function gatewayUrl(env = process.env) {
  return readEnv(env, "WORLDCORE_GATEWAY") || DEFAULT_GATEWAY;
}

/** ★ 超时：按方法取，`WORLDCORE_ASK_TIMEOUT_MS`／`WORLDCORE_QUERY_TIMEOUT_MS` 可覆盖。 */
export function timeoutFor(method, env = process.env) {
  const isAsk = method === METHOD_BY_TOOL.world_ask;
  const fallback = isAsk ? ASK_TIMEOUT_MS : QUERY_TIMEOUT_MS;
  const n = Number(readEnv(env, isAsk ? "WORLDCORE_ASK_TIMEOUT_MS" : "WORLDCORE_QUERY_TIMEOUT_MS"));
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

/** ★ 配置默认 actor：`WORLDCORE_ACTOR` 设了就用它（空串＝不给）。 */
export function defaultActor(env = process.env) {
  const raw = env && env.WORLDCORE_ACTOR;
  if (typeof raw !== "string") return DEFAULT_ACTOR;
  return raw.trim();
}

/**
 * 查世界的 params：`kind` 等**原样直传**（只丢掉 undefined／null，一个字不改、一个不补）。
 * @param {object} args 工具参数
 * @returns {object} JSON-RPC params
 */
export function queryParams(args = {}) {
  const out = {};
  for (const [k, v] of Object.entries(args || {})) {
    if (v === undefined || v === null) continue;
    out[k] = v;
  }
  return out;
}

/**
 * 请世界做事的 params：`action`／`params`／`actor`／`ticket` **原样直传**。
 * ★ actor 的规则只有三条：调用方给了用调用方的；没给用配置默认值；配置默认值为空就不给。
 * @param {object} args 工具参数
 * @param {object} env 环境（默认 process.env）
 * @returns {object} JSON-RPC params
 */
export function askParams(args = {}, env = process.env) {
  const a = args || {};
  const out = {};
  if (a.action !== undefined && a.action !== null) out.action = a.action;
  if (a.params !== undefined && a.params !== null) out.params = a.params;
  const actor = a.actor !== undefined && a.actor !== null ? a.actor : defaultActor(env);
  if (actor) out.actor = actor;
  if (a.ticket !== undefined && a.ticket !== null) out.ticket = a.ticket;
  return out;
}

/** 短摘要：错误信息里不塞长文（原文仍在 `error.rpc`）。 */
function brief(value, limit = 300) {
  const text = typeof value === "string" ? value : String(value && value.message ? value.message : value);
  return text.length > limit ? text.slice(0, limit) + "…" : text;
}

let _seq = 0;

/** 关联号：只用于把回话对上，不携带任何世界语义。 */
export function nextRequestId() {
  _seq += 1;
  return "dsh-" + _seq;
}

/**
 * ★ 唯一的一条出口：POST 一条 JSON-RPC 到网关，把 `result` 原样交回。
 *
 * @param {"world.query"|"world.ask"} method 方法名（只有两个）
 * @param {object} params 已构造好的 JSON-RPC params（本函数不再动它）
 * @param {object} [options] `{ baseUrl, timeoutMs, id, env, fetchImpl }`（判据／smoke 可注入）
 * @returns {Promise<any>} 网关回话里的 `result`，原样
 * @throws {GatewayRpcError} 网关回了 JSON-RPC `error`（含本体拒绝、网关传输码）
 * @throws {TransportError} 连不上／回话不是 JSON／没有 result —— **不带** `world_code`
 */
export async function callWorld(method, params, options = {}) {
  const env = options.env || process.env;
  const baseUrl = options.baseUrl || gatewayUrl(env);
  const timeoutMs = options.timeoutMs || timeoutFor(method, env);
  const doFetch = options.fetchImpl || fetch;
  const request = {
    jsonrpc: "2.0",
    id: options.id || nextRequestId(),
    method,
    params: params || {},
  };

  let response;
  try {
    response = await doFetch(baseUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    // ★ 连不上／超时：这是【传输】不是【世界的拒绝】 ⇒ 一个世界码都不许出现
    throw new TransportError(
      "连不上世界薄网关（" + baseUrl + "，超时 " + timeoutMs + "ms）：" + brief(err),
      "unreachable",
    );
  }

  let text = "";
  try {
    text = await response.text();
  } catch (err) {
    throw new TransportError("读不到网关回话：" + brief(err), "read-failed");
  }

  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new TransportError(
      "网关回话不是 JSON（HTTP " + response.status + "）：" + brief(text),
      "not-json",
    );
  }

  if (body && body.error) throw new GatewayRpcError(body.error); // ★ 原样，一字不改
  if (!body || !("result" in body)) {
    throw new TransportError(
      "网关回话既没有 result 也没有 error（HTTP " + response.status + "）：" + brief(text),
      "no-result",
    );
  }
  return body.result;
}
