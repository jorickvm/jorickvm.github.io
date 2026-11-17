import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import worker, { validEvent, UsageCounts } from "./worker.mjs";

const client = fs.readFileSync(new URL("../../assets/js/calculator-usage.js", import.meta.url), "utf8");
const good = { calculator: "ukSrt", placement: "embedded", stage: "used" };

function page(overrides = {}) {
  const sent = [];
  const context = { window: {}, URLSearchParams,
    document: { currentScript: { getAttribute: () => "https://counter.example/collect" } },
    location: { hostname: "atlasdays.app", protocol: "https:", search: "" }, navigator: {},
    localStorage: { getItem: () => null }, fetch: (url, options) => { sent.push({ url, ...options }); return Promise.resolve(); }, ...overrides };
  vm.runInNewContext(client, context);
  return { sent, usage: context.window.AtlasDaysCalculatorUsage };
}

test("only three fixed fields are sent, once per stage and page visit", () => {
  const p = page(), record = p.usage.create("ukSrt", "embedded");
  assert.equal(p.sent.length, 0);
  for (let i = 0; i < 5; i++) for (const stage of ["started", "used", "continued"]) record(stage);
  p.usage.create("ukSrt", "embedded")("used");
  record("2026-08-14"); record({ country: "US-CA" });
  assert.equal(p.sent.length, 3);
  for (const request of p.sent) {
    assert.equal(request.credentials, "omit"); assert.equal(request.referrerPolicy, "no-referrer");
    assert.deepEqual(Object.keys(JSON.parse(request.body)).sort(), ["calculator", "placement", "stage"]);
  }
  p.usage.create("US-CA", "embedded")("used");
  assert.equal(p.sent.length, 3);
  p.usage.create("ukSrt", "standalone")("started"); assert.equal(p.sent.length, 4);
  const another = page(); another.usage.create("ukSrt", "embedded")("used"); assert.equal(another.sent.length, 1);
});

test("opt-outs, local previews, disabled configuration and blocked storage send nothing", () => {
  for (const overrides of [
    { location: { hostname: "localhost", protocol: "http:", search: "" } },
    { location: { hostname: "atlasdays.app", protocol: "https:", search: "?notrack" } },
    { localStorage: { getItem: () => "1" } },
    { localStorage: { getItem: () => { throw Error("unavailable"); } } },
    { navigator: { globalPrivacyControl: true } }, { navigator: { doNotTrack: "1" } },
    { document: { currentScript: { getAttribute: () => "" } } }
  ]) {
    const p = page(overrides); p.usage.create("days183", "standalone")("used"); assert.equal(p.sent.length, 0);
  }
  const p = page({ fetch: () => { throw Error("offline"); } });
  assert.doesNotThrow(() => p.usage.create("days183", "standalone")("used"));
});

function environment() {
  const rows = new Map(); let queue = Promise.resolve();
  const storage = {
    transaction(fn) { const result = queue.then(() => fn({ get: async key => structuredClone(rows.get(key)), put: async (key, value) => rows.set(key, structuredClone(value)) })); queue = result.catch(() => {}); return result; },
    list: async ({ start, end }) => new Map([...rows].filter(([key]) => key >= start && key < end))
  };
  const object = new UsageCounts({ storage });
  return { rows, COUNTS: { idFromName: name => { assert.equal(name, "daily-totals"); return name; }, get: () => object }, REPORT_TOKEN: "fixture-report-secret" };
}
function collect(event, headers = {}) {
  return new Request("https://counter.example/collect", { method: "POST", headers: { Origin: "https://atlasdays.app", ...headers }, body: JSON.stringify(event) });
}

test("collector rejects extra data and preserves only aggregate totals under concurrent requests", async () => {
  const env = environment();
  for (const payload of [null, [], { ...good, date: "2026-09-01" }, { ...good, country: "CA" },
    { ...good, visitor: "fixture-person" }, { ...good, stage: "click" }, { ...good, calculator: "US-NY" }]) {
    assert.ok(!validEvent(payload)); assert.equal((await worker.fetch(collect(payload), env)).status, 400);
  }
  assert.equal((await worker.fetch(collect(good, { Origin: "https://elsewhere.example" }), env)).status, 403);
  const oversized = new Request("https://counter.example/collect", { method: "POST", headers: { Origin: "https://atlasdays.app" }, body: "a".repeat(1024) });
  assert.equal((await worker.fetch(oversized, env)).status, 400);
  const results = await Promise.all(Array.from({ length: 50 }, () => worker.fetch(collect(good, {
    "CF-Connecting-IP": "192.0.2.1", Cookie: "fixture-cookie", Referer: "https://atlasdays.app/?private=fixture"
  }), env)));
  assert.ok(results.every(r => r.status === 204));
  const stored = Object.fromEntries(env.rows); const day = new Date().toISOString().slice(0, 10);
  assert.deepEqual(stored, { [day]: { "ukSrt:embedded:used": 50 } });
});

test("reports require a secret and contain only date-bucketed counts", async () => {
  const env = environment(); await worker.fetch(collect(good), env);
  const url = "https://counter.example/report?from=2020-01-01&to=2099-12-31";
  assert.equal((await worker.fetch(new Request(url), env)).status, 403);
  const response = await worker.fetch(new Request(url, { headers: { Authorization: "Bearer fixture-report-secret" } }), env);
  assert.equal(response.status, 200); assert.equal(response.headers.get("Access-Control-Allow-Origin"), null);
  assert.deepEqual(await response.json(), Object.fromEntries(env.rows));
});
