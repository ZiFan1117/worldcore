// A2UI v1.0 渲染核心 —— ★ 纯函数：输入一帧，输出一棵组件树（不碰 DOM）。
// 用途：① 浏览器里用（a2ui.html 引入）② Node 里单测（test-node.mjs）。

export const KNOWN = [
  "Text", "Image", "Icon", "Video", "AudioPlayer",
  "Row", "Column", "List", "Card", "Tabs", "Modal", "Divider",
  "Button", "TextField", "CheckBox", "ChoicePicker", "Slider", "DateTimeInput",
];

/** ★ 从 messages 里折出「surface」：{ surfaceId, catalogId, components: Map<id, comp>, roots: [] } */
export function fold(frame) {
  const surfaces = new Map();
  const messages = (frame && frame.messages) || [];
  for (const m of messages) {
    if (m.createSurface) {
      const s = m.createSurface;
      surfaces.set(s.surfaceId, {
        surfaceId: s.surfaceId, catalogId: s.catalogId || "",
        sendDataModel: !!s.sendDataModel, components: new Map(), order: [],
      });
    }
    if (m.updateComponents) {
      const u = m.updateComponents;
      let s = surfaces.get(u.surfaceId);
      if (!s) { s = { surfaceId: u.surfaceId, catalogId: "", components: new Map(), order: [] }; surfaces.set(u.surfaceId, s); }
      for (const c of (u.components || [])) {
        if (!s.components.has(c.id)) s.order.push(c.id);
        s.components.set(c.id, c);
      }
    }
  }
  return surfaces;
}

/** ★ 哪些组件被别处引用（children / child / trigger / content）—— 用来找根 */
export function referencedIds(components) {
  const ref = new Set();
  const add = (v) => { if (typeof v === "string") ref.add(v); else if (Array.isArray(v)) v.forEach(add); };
  for (const c of components.values()) {
    add(c.children); add(c.child); add(c.trigger); add(c.content);
    if (Array.isArray(c.tabs)) for (const t of c.tabs) { add(t.componentId || t.child); add(t.id); }
  }
  return ref;
}

/** ★ 把一帧折成「渲染计划」：根 + 每个组件的子关系（只做解析，不画） */
export function plan(surface) {
  const comps = surface.components;
  const ref = referencedIds(comps);
  let roots = [];
  for (const id of surface.order) if (!ref.has(id)) roots.push(id);
  if (roots.length === 0 && surface.order.length) roots = [surface.order[0]];
  const kids = {};
  for (const [id, c] of comps) {
    const k = [];
    if (Array.isArray(c.children)) k.push(...c.children);
    else if (typeof c.child === "string") k.push(c.child);
    kids[id] = k.filter((x) => comps.has(x));
  }
  const unknown = [];
  for (const [id, c] of comps) if (!KNOWN.includes(c.component)) unknown.push(id + ":" + c.component);
  return { surfaceId: surface.surfaceId, catalogId: surface.catalogId, roots, kids, unknown };
}

/** ★ 一行字：把一帧摘要成可读的树（Node 单测/日志都用它） */
export function outline(surface) {
  const p = plan(surface);
  const comps = surface.components;
  const lines = [];
  const walk = (id, depth) => {
    const c = comps.get(id);
    if (!c) return;
    const label = c.component === "Text" ? ("Text: " + String(c.text || "").slice(0, 40)) : c.component;
    lines.push("  ".repeat(depth) + "· " + id + "  [" + label + "]");
    for (const k of (p.kids[id] || [])) walk(k, depth + 1);
  };
  for (const r of p.roots) walk(r, 0);
  return { surfaceId: p.surfaceId, roots: p.roots, unknown: p.unknown, lines };
}
