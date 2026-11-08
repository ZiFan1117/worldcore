/**
 * ★★ `dsh-worldcore` —— 宿主侧 DSH 插件：让宿主上的 DeepSeek Harness 经【世界薄网关】进世界。
 *
 * ★ 只发两条路（别的一律不发）：
 *   world_query（工具）→ `world.query`（JSON-RPC）→ 网关 → 世界总线 `world/query`
 *   world_ask  （工具）→ `world.ask`  （JSON-RPC）→ 网关 → 世界总线 `world/ask`
 *
 * ★ 本插件【只做传输】：
 *   · 不校验动作名／参数／许可／凭证 —— 那是本体的事（未登记动作由本体回 `UNKNOWN_ACTION`）；
 *   · 不自造拒绝码 —— 网关回的 JSON-RPC `error` **原样**抛成工具错误，`world_code`／`category` 一字不改；
 *   · 不直连总线、不调 `world_cli.py`、不碰执行器 —— 只 POST 到网关。
 *   · 不替调用方造 actor：`world://agent/dsh` 只是**配置默认值**（`WORLDCORE_ACTOR` 可改，设空即不给）。
 *
 * ★ 端点：`WORLDCORE_GATEWAY`（默认 `http://127.0.0.1:8780`）；
 *   超时：ask 默认 110s、query 默认 30s（`WORLDCORE_ASK_TIMEOUT_MS`／`WORLDCORE_QUERY_TIMEOUT_MS`）。
 */
import { defineTool } from "@deepseek-ai/dsh-tools";
import {
  DEFAULT_ACTOR,
  DEFAULT_GATEWAY,
  METHOD_BY_TOOL,
  askParams,
  callWorld,
  queryParams,
} from "./world_client.js";

/** Stable Loader identity. */
export const name = "dsh-worldcore";

/** Services used. */
export const inject = ["tools"];

const MAX_TEXT = 4000;

/** 工具结果原样给模型看（不裁剪字段，只裁剪长度）。 */
function renderJson(_args, value) {
  let text;
  try {
    text = JSON.stringify(value);
  } catch {
    text = String(value);
  }
  if (typeof text !== "string") text = String(text);
  return [{ type: "text", text: text.slice(0, MAX_TEXT) }];
}

export function apply(ctx) {
  // ── ① 问世界（只查，不改）────────────────────────────────────
  ctx.tools.register(defineTool({
    name: "world_query",
    description:
      "★ 问【世界】。经世界薄网关发 JSON-RPC `world.query`，params **原样直传**（kind 等一个不改）。" +
      "kind=overview 看世界概况；kind=actions 看能做什么；kind=type 要 type；" +
      "kind=one 要 instance；kind=link 要 type＋link。" +
      "★★ 做事之前先问这个，别凭想象挑动作。" +
      "★★ 只查不改；世界拒了什么、为什么拒，都以世界里那本账为准（本插件不判）。",
    parameters: {
      kind: { type: "string", required: true, description: "world | overview | actions | types | type | one | link" },
      type: { type: "string", description: "kind=type／link 的类名（如 service）" },
      instance: { type: "string", description: "kind=one 的个体 id" },
      link: { type: "string", description: "kind=link 的关系名" },
      actor: { type: "string", description: "可选：调用方自己的身份（不给就一个都不带，由世界决定）" },
      ticket: { type: "string", description: "可选：票（原样直传）" },
    },
    output: {
      schema: { type: "object", additionalProperties: true },
      render: renderJson,
    },
    execute: async (args) => callWorld(METHOD_BY_TOOL.world_query, queryParams(args)),
  }));

  // ── ② 请世界做事（★ 世界认名字／判许可／记账／转给载体）──────────
  ctx.tools.register(defineTool({
    name: "world_ask",
    description:
      "★ 请【世界】做一件事，经世界薄网关发 JSON-RPC `world.ask`。" +
      "★ 你自己不执行任何命令：世界认动作名、判许可、盖章、记账，再转给载体执行。" +
      "`action` 必须来自 world_query 查到的可用清单（清单外的会由【世界】拒，码原样回来）。" +
      "★★ 本工具不替你做任何校验与许可判断；被拒时错误里就是世界给的 `world_code`／`category`。",
    parameters: {
      action: { type: "string", required: true, description: "动作名，如 sys.GetMemoryInfo" },
      params: { type: "object", additionalProperties: true, description: "动作参数（原样直传）" },
      actor: { type: "string", description: "可选：调用方自己的身份；不给则用插件配置的默认 actor" },
      ticket: { type: "string", description: "可选：票（原样直传）" },
    },
    output: {
      schema: { type: "object", additionalProperties: true },
      render: renderJson,
    },
    execute: async (args) => callWorld(METHOD_BY_TOOL.world_ask, askParams(args)),
  }));
}

/** 供 README／判据取用的现取值（★ 都取自本插件的常量，不另立一份）。 */
export const config = {
  defaultGateway: DEFAULT_GATEWAY,
  defaultActor: DEFAULT_ACTOR,
};
