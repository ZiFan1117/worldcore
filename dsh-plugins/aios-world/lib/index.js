/**
 * ★★ AI-OS 世界插件 —— ★ DSH 只能通过【本体】做事，★ 用 A2UI 出界面。
 *
 * ★ 作者令（逐字）：「写一个 DSH 插件而且我要给他做一个 A2UI 的界面」
 *                 「这个那那就写个桥吧，写个桥吧」
 * ★ 作者裁（逐字）：「所有的交互啥的必须过这个所谓的本体……除了这个数据是那啥的」
 *
 * ★★ 传输：★ 经【桥】`/usr/lib/aios/py/world_cli.py` —— 它是总线的【正规 Python 客户端】。
 *    ★ 为什么用桥：★ Node 的 zenoh 绑定【全试死了】——
 *      · zenoh-node 只有 peer 模式（孤岛，实测收不到）
 *      · zenoh-ts 要 remote-api 插件（下不到）
 *    ★ 桥【只发 world/* 三样】，★ 不执行、★ 不判许可。
 *
 * 三个工具（★ 全过本体）：
 *   world_query  问世界    → world/query
 *   world_ask    做事      → world/ask（本体判/记/转给载体）
 *   world_ui     出 A2UI   → world/notice（本体认/记/转给 GUI ⇒ 屏幕）
 */
import { defineTool } from "@deepseek-ai/dsh-tools";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const exec = promisify(execFile);

/** Stable Loader identity. */
export const name = "aios-world";

/** Services used. */
export const inject = ["tools"];

const CLI = process.env.AIOS_WORLD_CLI || "/usr/lib/aios/py/world_cli.py";
const PY = process.env.AIOS_PYTHON || "/usr/bin/python3";
const AGENT = process.env.AIOS_AGENT_NAME || "dsh";

/** ★ 桥：一问一答，JSON 进 JSON 出。 */
async function bridge(cmd, payload, timeoutMs = 90000) {
  try {
    const { stdout } = await exec(PY, [CLI, cmd, JSON.stringify(payload)], {
      timeout: timeoutMs, maxBuffer: 8 * 1024 * 1024,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    const line = stdout.trim().split("\n").pop() || "";
    return JSON.parse(line);
  } catch (e) {
    return { ok: false, why: "桥失败：" + String(e.message || e).slice(0, 300) };
  }
}

export function apply(ctx) {
  // ── ① 问世界 ───────────────────────────────────────────────
  ctx.tools.register(defineTool({
    name: "world_query",
    description:
      "★ 问【世界】（本体）。kind=world 看有哪些类／几个个体；" +
      "kind=actions 看【我能做什么】（available 是本机真能跑的，unsupported 不要挑）；" +
      "kind=type 要 type 参数；kind=link 要 type+link；kind=one 要 instance。" +
      "★★ 做事之前【先问这个】，别凭想象挑动作。",
    parameters: {
      kind: { type: "string", required: true, description: "world | actions | types | type | one | link" },
      type: { type: "string", description: "kind=type／link 的类名（如 service）" },
      instance: { type: "string", description: "kind=one 的个体 id" },
      link: { type: "string", description: "kind=link 的关系名" },
    },
    output: {
      schema: { type: "object", additionalProperties: true },
      render: (_a, v) => [{ type: "text", text: JSON.stringify(v).slice(0, 4000) }],
    },
    execute: async (args) => {
      const m = { kind: args.kind };
      if (args.type) m.type = args.type;
      if (args.instance) m.instance = args.instance;
      if (args.link) m.link = args.link;
      return bridge("query", m, 40000);
    },
  }));

  // ── ② 做事（★ 过本体）──────────────────────────────────────
  ctx.tools.register(defineTool({
    name: "world_ask",
    description:
      "★ 请【世界】做一件事。★ 你自己不执行任何命令 —— ★ 本体认名字、判许可、盖章、记账、" +
      "转给载体执行、再把结果回给你。" +
      "★★ action 必须来自 world_query(kind=actions) 的 available 清单；清单外的会被本体拒。",
    parameters: {
      action: { type: "string", required: true, description: "动作名，如 sys.GetMemoryInfo" },
      params: { type: "object", additionalProperties: true, description: "动作参数" },
    },
    output: {
      schema: { type: "object", additionalProperties: true },
      render: (_a, v) => [{ type: "text", text: (v && v.ok ? "✓ " : "✗ ") + String((v && (v.body || v.error || v.why)) || "").slice(0, 3000) }],
    },
    execute: async (args) => bridge("ask",
      { action: args.action, params: args.params || {}, actor: "world://agent/" + AGENT }, 100000),
  }));

  // ── ③ 出界面（★ A2UI，★ 经本体）──────────────────────────
  ctx.tools.register(defineTool({
    name: "world_ui",
    description:
      "★ 把你要给人看的画成【A2UI】，★ 直接显示在屏幕上。传 components 数组（A2UI v1.0）：" +
      "Text(text，支持**粗体**)／Column(children)／Row(children)／Card(child)／List(children)／" +
      "Divider／Button(text)／Icon(name)。★ 第一个必须是 {id:'root',component:'Column',children:[…]}。" +
      "★ 一帧最多 20 个组件。★★ 这帧【经世界】（world/notice ⇒ 本体 ⇒ GUI ⇒ 屏幕）。",
    parameters: {
      components: { type: "array", required: true, items: { type: "object", additionalProperties: true },
                    description: "A2UI 组件数组" },
      title: { type: "string", description: "这一帧叫什么" },
    },
    output: {
      schema: { type: "object", additionalProperties: true },
      render: (_a, v) => [{ type: "text", text: "A2UI 帧已发出（经本体）：" + String(v && (v.note || v.why) || "") }],
    },
    execute: async (args) => {
      const frame = {
        version: "v1.0",
        name: args.title || "DSH 画的界面（★ 经本体）",
        messages: [
          { version: "v1.0", createSurface: {
              surfaceId: "agent/" + AGENT, sendDataModel: true,
              catalogId: "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json" } },
          { version: "v1.0", updateComponents: {
              surfaceId: "agent/" + AGENT,
              components: Array.isArray(args.components) ? args.components : [] } },
        ],
      };
      return bridge("frame", frame, 25000);
    },
  }));
}
