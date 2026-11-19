const CALCULATORS = new Set(["days183", "schengen", "ukIlr", "presence", "spt", "multiYear", "ukSrt", "feie", "dayCount"]);
const PLACEMENTS = new Set(["standalone", "embedded"]);
const STAGES = new Set(["loaded", "started", "used", "continued", "export_dialog_opened", "qr_offered", "app_button_offered", "app_link_tapped", "csv_download_selected"]);
const ORIGIN = "https://atlasdays.app";
const response = (status, origin = false, body = null) => new Response(body, { status, headers: {
  "Cache-Control": "no-store", "Content-Type": "application/json",
  ...(origin ? { "Access-Control-Allow-Origin": ORIGIN, Vary: "Origin" } : {})
} });

export function validEvent(value) {
  return value && !Array.isArray(value) && typeof value === "object"
    && Object.keys(value).sort().join(",") === "calculator,placement,stage"
    && CALCULATORS.has(value.calculator) && PLACEMENTS.has(value.placement) && STAGES.has(value.stage);
}

async function readEvent(request) {
  if (!request.body) return null;
  const reader = request.body.getReader(), chunks = [];
  let length = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    length += value.length;
    if (length > 256) { await reader.cancel(); return null; }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  try { const event = JSON.parse(new TextDecoder().decode(bytes)); return validEvent(event) ? event : null; }
  catch { return null; }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/collect" && request.method === "POST") {
      if (url.search || request.headers.get("Origin") !== ORIGIN) return response(403);
      const event = await readEvent(request);
      if (!event) return response(400, true);
      const day = new Date().toISOString().slice(0, 10);
      const object = env.COUNTS.get(env.COUNTS.idFromName("daily-totals"));
      // Forward a clean request, without the incoming headers or URL.
      await object.fetch(new Request("https://counter/increment", { method: "POST", body: JSON.stringify({ day, ...event }) }));
      return response(204, true);
    }
    if (url.pathname === "/report" && request.method === "GET") {
      if (!env.REPORT_TOKEN || request.headers.get("Authorization") !== "Bearer " + env.REPORT_TOKEN) return response(403);
      const from = url.searchParams.get("from"), to = url.searchParams.get("to");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(from || "") || !/^\d{4}-\d{2}-\d{2}$/.test(to || "") || from > to) return response(400);
      const object = env.COUNTS.get(env.COUNTS.idFromName("daily-totals"));
      const result = await object.fetch(new Request("https://counter/report?from=" + from + "&to=" + to));
      return response(200, false, await result.text());
    }
    return response(404);
  }
};

export class UsageCounts {
  constructor(state) { this.storage = state.storage; }
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/increment") {
      const { day, ...event } = await request.json();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day || "") || !validEvent(event)) return response(400);
      await this.storage.transaction(async transaction => {
        const counts = await transaction.get(day) || {};
        const key = event.calculator + ":" + event.placement + ":" + event.stage;
        counts[key] = (counts[key] || 0) + 1;
        await transaction.put(day, counts);
      });
      return response(204);
    }
    if (url.pathname === "/report") {
      const entries = await this.storage.list({ start: url.searchParams.get("from"), end: url.searchParams.get("to") + "\uffff" });
      return response(200, false, JSON.stringify(Object.fromEntries(entries)));
    }
    return response(404);
  }
}
