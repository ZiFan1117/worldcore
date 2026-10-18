import fs from "node:fs";
import { fold, plan, outline, KNOWN } from "./a2ui-renderer.mjs";

const frame = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
console.log("帧名:", frame.name || "(无名)", "| 消息数:", (frame.messages||[]).length);
const surfaces = fold(frame);
console.log("surface 数:", surfaces.size);
for (const s of surfaces.values()) {
  const p = plan(s);
  console.log("");
  console.log("surfaceId:", p.surfaceId);
  console.log("catalogId:", p.catalogId);
  console.log("组件数:", s.components.size, "| 根:", p.roots, "| 未知:", p.unknown);
  console.log("");
  const o = outline(s);
  console.log("=== 树（前 40 行）===");
  console.log(o.lines.slice(0, 40).join("\n"));
  console.log("…（共 " + o.lines.length + " 行树）");
  // 统计组件类型
  const byType = {};
  for (const c of s.components.values()) byType[c.component] = (byType[c.component]||0)+1;
  console.log("");
  console.log("=== 组件类型分布 ===");
  for (const [k,v] of Object.entries(byType).sort((a,b)=>b[1]-a[1])) console.log("  " + k + " × " + v + (KNOWN.includes(k) ? "" : "  ★ 未知"));
}